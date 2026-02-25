"""Glass Box Audit Pipeline: Atomic Claim Extraction + NLI-based Verification.

This module implements a two-step audit process:
1. STEP 1 (Atomizer): Extract atomic claims using GPT-4o-mini
2. STEP 2 (Judge): Verify claims using cross-encoder/nli-roberta-base (NLI)

Output: results/final_audit_results.csv
"""

import argparse
import csv
import json
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import torch
import yaml
from dotenv import load_dotenv
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from openai import OpenAI, APIError, RateLimitError, APIConnectionError
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

# Load environment
load_dotenv()

# Setup logging (MUST be before importing semantic_filter)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import semantic filter (optional, for pre-filtering)
try:
    from semantic_filter import SemanticFilter  # Import from same directory
    SEMANTIC_FILTER_AVAILABLE = True
except ImportError:
    SEMANTIC_FILTER_AVAILABLE = False
    logger.warning("Semantic filter not available (install sentence-transformers)")

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
PRODUCTS_DIR = PROJECT_ROOT / "products"
RESULTS_DIR = PROJECT_ROOT / "results"
EXPERIMENTS_CSV = RESULTS_DIR / "experiments.csv"
AUDIT_OUTPUT_CSV = RESULTS_DIR / "final_audit_results.csv"
CHECKPOINT_FILE = RESULTS_DIR / "audit_checkpoint.jsonl"
ERROR_LOG_FILE = RESULTS_DIR / "audit_errors.json"

# OpenAI Configuration
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
EXTRACTION_MODEL = "gpt-4o-mini"
EXTRACTION_TEMPERATURE = 0

# NLI Configuration
NLI_MODEL_NAME = "cross-encoder/nli-roberta-base"  # DeBERTa-v3-large tested but rejected (10x worse FP rate)
VIOLATION_THRESHOLD = 0.90  # Contradiction score threshold

# Semantic Filter Configuration (optional pre-filtering)
USE_SEMANTIC_FILTER = False  # Set via --use-semantic-filter flag
SEMANTIC_FILTER_TOP_K = 5  # Number of top similar rules to compare
SEMANTIC_FILTER_THRESHOLD = 0.3  # Minimum similarity to include rule

# Device detection
if torch.cuda.is_available():
    DEVICE = torch.device("cuda")
    logger.info("Using CUDA")
elif torch.backends.mps.is_available():
    DEVICE = torch.device("mps")
    logger.info("Using MPS (Apple Silicon)")
else:
    DEVICE = torch.device("cpu")
    logger.info("Using CPU")


# ==================== CHECKPOINT & ERROR TRACKING ====================

# Global error log
error_log = []

def save_checkpoint(result: Dict):
    """Append single audit result to checkpoint file."""
    with open(CHECKPOINT_FILE, 'a') as f:
        json.dump(result, f)
        f.write('\n')

def load_completed_run_ids() -> set:
    """Load run_ids that have already been completed from checkpoint."""
    completed = set()
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            for line in f:
                try:
                    result = json.loads(line)
                    completed.add(result['run_id'])
                except:
                    continue
    if completed:
        logger.info(f"Loaded {len(completed)} completed runs from checkpoint")
    return completed

def log_error(run_id: str, run_metadata: dict, error: Exception):
    """Log error details for troubleshooting."""
    error_info = {
        'run_id': run_id,
        'product_id': run_metadata.get('product_id', 'unknown'),
        'material_type': run_metadata.get('material_type', 'unknown'),
        'error': str(error),
        'error_type': type(error).__name__,
        'timestamp': time.time()
    }
    error_log.append(error_info)
    logger.error(f"Error auditing {run_id[:12]}: {error}")

def save_error_log():
    """Save all errors to JSON file."""
    if error_log:
        with open(ERROR_LOG_FILE, 'w') as f:
            json.dump(error_log, f, indent=2)
        logger.warning(f"Saved {len(error_log)} errors to {ERROR_LOG_FILE}")


# ==================== STEP 1: ATOMIC CLAIM EXTRACTION ====================

ATOMIZER_SYSTEM_PROMPT = """You are a forensic claim extraction system for marketing compliance audits.

TASK: Extract EVERY verifiable fact, technical specification, operational policy, restriction, and safety warning from the marketing material. SEPARATE disclaimers from core claims.

EXTRACTION RULES:
1. Split compound sentences into atomic facts
   - Example: "6.3 inch OLED display" → ["Screen is 6.3 inches", "Screen is OLED"]
   - Example: "Contains 3mg melatonin, non-habit-forming" → ["Contains 3mg melatonin", "Non-habit-forming"]
   - Example: "24/7 trading with regional pauses during maintenance" → ["Trading is 24/7", "Regional trading pauses during maintenance"]

2. Maintain original terminology (do not over-paraphrase)
   - Keep exact numbers, units, brand names, technical terms
   - Preserve policy language exactly as stated

3. Extract ALL verifiable claims including:
   - Product features (e.g., "Has 128GB storage")
   - Technical specifications (e.g., "Powered by Snapdragon 888")
   - Operational policies (e.g., "Trading pauses during maintenance", "Automatic key backup enabled")
   - Restrictions and conditions (e.g., "Regional limitations", "Requires quorum for voting")
   - Safety warnings (e.g., "Consult physician before use")
   - Quantitative statements (e.g., "Provides 7 years of updates")
   - Comparative statements (e.g., "Faster than previous generation")
   - Governance mechanisms (e.g., "Proposals auto-pass without quorum")

4. CRITICAL: Extract ALL parts of compound sentences
   - If a sentence contains multiple distinct facts or policies, extract EACH one separately
   - Do NOT omit secondary clauses, conditions, or exceptions
   - Example: "Available 24/7 except during regional maintenance windows" → ["Available 24/7", "Except during regional maintenance windows"]

5. SEPARATE disclaimers (hedging/legal statements):
   - Disclaimers include: "may vary", "depends on", "not guaranteed", "consult", "results may differ"
   - Disclaimers modify or hedge other claims (e.g., "Battery life may vary")

6. Ignore subjective marketing fluff:
   - Do NOT extract: "stunning", "amazing", "revolutionary", "incredible"
   - Do NOT extract vague claims like: "enhances your experience", "transforms your life"

7. If the material is entirely vague/subjective/fluff, return empty lists

OUTPUT FORMAT (strict JSON):
{
  "core_claims": [
    "atomic core claim 1",
    "atomic core claim 2"
  ],
  "disclaimers": [
    "disclaimer 1",
    "disclaimer 2"
  ]
}

IMPORTANT: Return ONLY valid JSON. No markdown, no explanation.
"""


@retry(
    retry=retry_if_exception_type((APIError, RateLimitError, APIConnectionError)),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(3),
    before_sleep=lambda retry_state: logger.warning(
        f"Retry attempt {retry_state.attempt_number} after API error"
    )
)
def extract_atomic_claims(material_content: str, product_name: str, material_type: str) -> Dict:
    """
    Extract atomic claims using OpenAI GPT-4o-mini (Forensic Extraction).
    Returns both core claims and disclaimers separately.

    Automatically retries up to 3 times on transient API errors with exponential backoff.

    Args:
        material_content: Marketing material text
        product_name: Product name for context
        material_type: Type of material (e.g., 'faq', 'digital_ad')

    Returns:
        Dict with 'core_claims' and 'disclaimers' lists
    """
    user_prompt = f"""PRODUCT: {product_name}
MATERIAL TYPE: {material_type}

MARKETING MATERIAL:
{material_content}

Extract all atomic claims as JSON with core_claims and disclaimers separated.
"""

    response = openai_client.chat.completions.create(
        model=EXTRACTION_MODEL,
        temperature=EXTRACTION_TEMPERATURE,
        messages=[
            {"role": "system", "content": ATOMIZER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)

    core_claims = result.get('core_claims', [])
    disclaimers = result.get('disclaimers', [])

    logger.debug(f"Extracted {len(core_claims)} core claims, {len(disclaimers)} disclaimers")

    return {
        'core_claims': core_claims,
        'disclaimers': disclaimers
    }


# ==================== STEP 2: CLAIM VERIFICATION ====================

# Numerical Contradiction Checking (Option B)
def extract_numbers_with_units(text: str) -> List[Tuple[str, str]]:
    """
    Extract numbers with their units from text.

    Returns:
        List of (number, unit) tuples, e.g., [("16", "GB"), ("6.5", "inch")]
    """
    import re
    # Pattern: number (with optional decimal) + optional space + unit
    # Units: GB, MB, TB, inch, ", mAh, MP, Hz, W, mm, grams, etc.
    pattern = r'(\d+(?:\.\d+)?)\s*(GB|MB|TB|inch|"|mAh|MP|Hz|W|mm|grams?|kg|℃|°C|C)\b'
    matches = re.findall(pattern, text, re.IGNORECASE)
    # Normalize units (e.g., "gram" → "grams", "C" → "℃")
    normalized = []
    for num, unit in matches:
        unit_lower = unit.lower()
        if unit_lower in ['gram', 'grams']:
            unit_lower = 'grams'
        elif unit_lower in ['c', '°c', '℃']:
            unit_lower = '°c'
        normalized.append((num, unit_lower))
    return normalized


def check_numerical_contradiction(claim: str, spec: str) -> Tuple[bool, str]:
    """
    Check if claim contains numerical values that contradict spec.

    Args:
        claim: Extracted claim (e.g., "Nova X5 has RAM configurations of 16 GB")
        spec: Product spec (e.g., "RAM configurations: 8 GB or 12 GB LPDDR5X")

    Returns:
        (is_contradiction, explanation)
        - is_contradiction: True if numerical mismatch found
        - explanation: Human-readable reason
    """
    import re

    claim_nums = extract_numbers_with_units(claim)
    spec_nums = extract_numbers_with_units(spec)

    if not claim_nums or not spec_nums:
        return False, ""  # No numbers to compare

    # Check each claim number against spec numbers with same unit
    for claim_val, claim_unit in claim_nums:
        # Find all spec numbers with matching unit
        matching_spec_vals = [val for val, unit in spec_nums if unit == claim_unit]

        if matching_spec_vals:
            # If claim number not in spec's allowed values, it's a contradiction
            if claim_val not in matching_spec_vals:
                return True, f"Numerical mismatch: {claim_val} {claim_unit} not in spec values {matching_spec_vals} {claim_unit}"

    return False, ""


class NLIJudge:
    """NLI-based claim verification using cross-encoder/nli-roberta-base."""

    def __init__(self, use_semantic_filter: bool = False):
        logger.info(f"Loading NLI model: {NLI_MODEL_NAME}")
        self.tokenizer = AutoTokenizer.from_pretrained(NLI_MODEL_NAME)
        self.model = AutoModelForSequenceClassification.from_pretrained(NLI_MODEL_NAME)
        self.model.to(DEVICE)
        self.model.eval()

        # Label mapping for cross-encoder models: [contradiction, entailment, neutral]
        # Same as roberta-base (consistent cross-encoder format)
        self.label_names = ['contradiction', 'entailment', 'neutral']

        # Semantic filter (optional pre-filtering)
        self.use_semantic_filter = use_semantic_filter
        self.semantic_filter = None
        if use_semantic_filter and SEMANTIC_FILTER_AVAILABLE:
            self.semantic_filter = SemanticFilter(
                top_k=SEMANTIC_FILTER_TOP_K,
                similarity_threshold=SEMANTIC_FILTER_THRESHOLD
            )
            logger.info("✅ Semantic pre-filtering ENABLED")
        elif use_semantic_filter and not SEMANTIC_FILTER_AVAILABLE:
            logger.warning("⚠️  Semantic filter requested but not available (install sentence-transformers)")
            self.use_semantic_filter = False

    def verify_claim(self, claim: str, authorized_claims: List[str], specs: List[str] = None, prohibited_claims: List[str] = None, clarifications: List[str] = None) -> Dict:
        """
        Verify if a claim contradicts any authorized claims, factual specs, prohibited claims, or clarifications.

        Args:
            claim: Extracted atomic claim
            authorized_claims: List of authorized claims from YAML
            specs: Optional list of factual specs from YAML (for fact-checking)
            prohibited_claims: Optional list of prohibited claims that should NOT appear
            clarifications: Optional list of clarifications, usage_instructions, safety_warnings (direct contradictions like "NOT FDA-approved")

        Returns:
            {
                'is_violation': bool,
                'violated_rule': str or None,
                'contradiction_score': float,
                'best_match_rule': str,
                'best_match_type': str (entailment/neutral/contradiction)
            }
        """
        # OPTION B: Pre-check for numerical contradictions (fast, rule-based)
        # This catches cases like "16 GB RAM" vs "8 GB or 12 GB RAM" that NLI misses
        # Category-aware: only check specs in the same category to avoid false matches
        if specs:
            # Classify claim category first
            claim_category = classify_claim_category(claim)

            for spec in specs:
                # Classify spec category
                spec_category = classify_claim_category(spec)

                # Only check numerical contradiction if same category or spec is 'general'
                if spec_category == claim_category or spec_category == 'general':
                    is_contradiction, explanation = check_numerical_contradiction(claim, spec)
                    if is_contradiction:
                        logger.debug(f"Numerical contradiction detected: {explanation}")
                        return {
                            'is_violation': True,
                            'violated_rule': spec,
                            'contradiction_score': 1.0,  # Rule-based detection (perfect confidence)
                            'best_match_rule': spec,
                            'best_match_type': 'numerical_rule'
                        }

        # Combine authorized claims, specs, prohibited claims, and clarifications for verification
        all_reference_claims = authorized_claims.copy() if authorized_claims else []
        if specs:
            all_reference_claims.extend(specs)
        if prohibited_claims:
            all_reference_claims.extend(prohibited_claims)
        if clarifications:
            # Handle clarifications (can be list or dict with nested lists)
            if isinstance(clarifications, dict):
                # Flatten nested dict: {category: [claims]} -> [claims]
                for category_claims in clarifications.values():
                    if isinstance(category_claims, list):
                        all_reference_claims.extend(category_claims)
            elif isinstance(clarifications, (list, tuple)):
                all_reference_claims.extend(clarifications)
            else:
                logger.warning(f"Unexpected clarifications type: {type(clarifications)}")

        if not all_reference_claims:
            return {
                'is_violation': False,
                'violated_rule': None,
                'contradiction_score': 0.0,
                'best_match_rule': None,
                'best_match_type': 'no_rules'
            }

        # Pre-filtering: Semantic (embedding) or Category (keyword-based)
        if self.use_semantic_filter and self.semantic_filter:
            # Semantic filtering: Use embeddings to find most similar rules
            relevant_rules = self.semantic_filter.filter_rules(
                claim,
                all_reference_claims,
                cache_key=None  # Could cache by product_id for speed
            )
            filtered_reference_claims = [rule_text for _, rule_text, _ in relevant_rules]

            if not filtered_reference_claims:
                return {
                    'is_violation': False,
                    'violated_rule': None,
                    'contradiction_score': 0.0,
                    'best_match_rule': None,
                    'best_match_type': 'semantic_filtered'
                }
        else:
            # Category-based filtering (fallback/original method)
            claim_category = classify_claim_category(claim)
            filtered_reference_claims = []
            for rule in all_reference_claims:
                rule_category = classify_claim_category(rule)
                # Compare if same category or if either is 'general' (regulatory, disclaimers, etc.)
                if rule_category == claim_category or rule_category == 'general' or claim_category == 'general':
                    filtered_reference_claims.append(rule)

            # If no matching category rules, skip validation (avoids comparing camera to display)
            if not filtered_reference_claims:
                return {
                    'is_violation': False,
                    'violated_rule': None,
                    'contradiction_score': 0.0,
                    'best_match_rule': None,
                    'best_match_type': 'category_filtered'
                }

        max_contradiction_score = 0.0
        violated_rule = None
        best_match_rule = None
        best_match_type = None
        best_match_score = 0.0

        for auth_claim in filtered_reference_claims:
            # Prepare input for cross-encoder
            inputs = self.tokenizer(
                claim,
                auth_claim,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=512
            ).to(DEVICE)

            # Get predictions
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=1)[0]

            # Extract scores
            contradiction_score = probs[0].item()
            entailment_score = probs[1].item()
            neutral_score = probs[2].item()

            # Track highest contradiction
            if contradiction_score > max_contradiction_score:
                max_contradiction_score = contradiction_score
                violated_rule = auth_claim

            # Track best match overall (highest score among all labels)
            all_scores = {
                'contradiction': contradiction_score,
                'entailment': entailment_score,
                'neutral': neutral_score
            }
            current_best_label = max(all_scores, key=all_scores.get)
            current_best_score = all_scores[current_best_label]

            if current_best_score > best_match_score:
                best_match_score = current_best_score
                best_match_rule = auth_claim
                best_match_type = current_best_label

        # Determine if violation
        is_violation = max_contradiction_score > VIOLATION_THRESHOLD

        return {
            'is_violation': is_violation,
            'violated_rule': violated_rule if is_violation else None,
            'contradiction_score': max_contradiction_score,
            'best_match_rule': best_match_rule,
            'best_match_type': best_match_type
        }


# ==================== UTILITIES ====================

def load_material(run_id: str, output_path: str = None) -> str:
    """Load generated marketing material from outputs/.

    Args:
        run_id: Run identifier
        output_path: Optional explicit path from CSV (e.g., outputs/1.txt)
    """
    if output_path:
        # Use explicit path from CSV (for custom uploaded files)
        file_path = Path(output_path)
    else:
        # Default: construct path from run_id
        file_path = OUTPUTS_DIR / f"{run_id}.txt"

    if not file_path.exists():
        raise FileNotFoundError(f"Material not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def load_product_yaml(product_id: str) -> dict:
    """Load product YAML file."""
    file_path = PRODUCTS_DIR / f"{product_id}.yaml"
    if not file_path.exists():
        raise FileNotFoundError(f"Product YAML not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def flatten_authorized_claims(product_yaml: dict) -> List[str]:
    """
    Flatten nested authorized_claims structure into list of strings.

    Returns:
        List of claim text strings
    """
    authorized = product_yaml.get('authorized_claims', {})

    if isinstance(authorized, dict):
        claims = []
        for category, claim_list in authorized.items():
            if isinstance(claim_list, list):
                claims.extend(claim_list)
        return claims
    elif isinstance(authorized, list):
        return authorized
    else:
        return []


def flatten_specs(product_yaml: dict) -> List[str]:
    """
    Flatten nested specs structure into list of factual spec strings.
    This extracts technical specifications that can be fact-checked.

    Returns:
        List of spec text strings
    """
    specs = product_yaml.get('specs', {})
    spec_list = []

    def extract_strings(data):
        """Recursively extract all string values from nested dict/list."""
        if isinstance(data, str):
            return [data]
        elif isinstance(data, list):
            result = []
            for item in data:
                result.extend(extract_strings(item))
            return result
        elif isinstance(data, dict):
            result = []
            for value in data.values():
                result.extend(extract_strings(value))
            return result
        else:
            return []

    spec_list = extract_strings(specs)
    return spec_list


def flatten_prohibited_claims(product_yaml: dict) -> List[str]:
    """
    Flatten prohibited_or_unsupported_claims into list of strings.
    These are claims that should NOT appear in marketing materials.

    Returns:
        List of prohibited claim text strings
    """
    prohibited = product_yaml.get('prohibited_or_unsupported_claims', {})
    prohibited_list = []

    def extract_strings(data):
        """Recursively extract all string values from nested dict/list."""
        if isinstance(data, str):
            return [data]
        elif isinstance(data, list):
            result = []
            for item in data:
                result.extend(extract_strings(item))
            return result
        elif isinstance(data, dict):
            result = []
            for value in data.values():
                result.extend(extract_strings(value))
            return result
        else:
            return []

    prohibited_list = extract_strings(prohibited)
    return prohibited_list


def flatten_clarifications(product_yaml: dict) -> List[str]:
    """
    Flatten clarifications, usage_instructions, and safety_warnings into list of strings.
    These sections contain direct contradiction statements (e.g., "NOT FDA-approved").

    Returns:
        List of clarification/instruction text strings
    """
    clarifications = []

    # Extract clarifications section
    clarifications_section = product_yaml.get('clarifications', [])
    if isinstance(clarifications_section, list):
        clarifications.extend(clarifications_section)

    # Extract usage_instructions section
    usage_section = product_yaml.get('usage_instructions', [])
    if isinstance(usage_section, list):
        clarifications.extend(usage_section)

    # Extract safety_warnings section
    safety_section = product_yaml.get('safety_warnings', [])
    if isinstance(safety_section, list):
        clarifications.extend(safety_section)

    return clarifications


def classify_claim_category(claim: str) -> str:
    """
    Classify a claim into a semantic category using keyword matching.
    This enables category-based filtering to reduce false positive comparisons.

    Args:
        claim: The claim text to classify

    Returns:
        Category name (e.g., 'display', 'camera', 'storage', 'dosage', etc.)
    """
    claim_lower = claim.lower()

    # Category keyword mappings (order matters - more specific first)
    CATEGORY_KEYWORDS = {
        # Electronics/Smartphone categories
        'display': ['display', 'screen', 'inch', '"', 'oled', 'lcd', 'amoled', 'refresh rate', 'hz', 'resolution', 'brightness', 'nits'],
        'camera': ['camera', 'mp', 'megapixel', 'photo', 'lens', 'zoom', 'aperture', 'ois', 'image stabilization', 'ultrawide', 'telephoto', 'video recording'],
        'storage': ['storage', 'gb', 'tb', 'memory', 'space', 'ufs', 'expandable', 'microsd'],
        'ram': ['ram', 'lpddr', 'memory'],
        'battery': ['battery', 'mah', 'charging', 'power', 'watt', 'fast charging', 'wireless charging'],
        'processor': ['processor', 'cpu', 'chipset', 'ghz', 'core', 'gpu', 'npu', 'tensor', 'snapdragon', 'exynos'],
        'network': ['5g', '4g', 'lte', 'wifi', 'wi-fi', 'bluetooth', 'cellular', 'connectivity', 'nfc', 'sub-6'],

        # Supplement categories
        'dosage': ['mg', 'dose', 'dosage', 'serving', 'tablet', 'capsule', 'pill', 'take', 'consume'],
        'ingredients': ['contain', 'ingredient', 'gluten', 'soy', 'dairy', 'allergen', 'vegan', 'vegetarian', 'non-gmo', 'fish'],
        'safety': ['safe', 'side effect', 'drowsiness', 'warning', 'caution', 'pregnant', 'children', 'adult', 'age'],
        'manufacturing': ['manufactured', 'facility', 'gmp', 'tested', 'quality', 'certified', 'third-party'],
        'regulatory': ['fda', 'approved', 'evaluated', 'regulated', 'drug', 'supplement', 'dshea'],
        'efficacy': ['help', 'support', 'promote', 'improve', 'enhance', 'treat', 'cure', 'prevent', 'reduce'],
        'storage_temp': ['store', 'storage', 'temperature', '°c', 'degrees', 'room temperature', 'cool', 'dry'],

        # Cryptocurrency categories
        'consensus': ['proof of stake', 'pos', 'validator', 'staking', 'consensus', 'block'],
        'supply': ['supply', 'coin', 'token', 'issuance', 'inflation', 'deflationary'],
        'transaction': ['transaction', 'tps', 'per second', 'speed', 'throughput', 'latency'],
        'security': ['security', 'encryption', 'hash', 'cryptographic', 'secure'],
        'energy': ['energy', 'power', 'consumption', 'efficient', 'green', 'carbon']
    }

    # Find matching category
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in claim_lower for keyword in keywords):
            return category

    return 'general'  # Fallback for uncategorized claims


def get_completed_runs() -> pd.DataFrame:
    """Load completed runs from experiments.csv."""
    if not EXPERIMENTS_CSV.exists():
        raise FileNotFoundError(f"Experiments CSV not found: {EXPERIMENTS_CSV}")

    df = pd.read_csv(EXPERIMENTS_CSV)

    # Filter: completed runs, no trap products
    mask = (df['status'] == 'completed') & (df['trap_flag'] == False)
    return df[mask]


# ==================== MAIN AUDIT PIPELINE ====================

def audit_single_run(run_id: str, run_metadata: Dict, judge: NLIJudge) -> Dict:
    """
    Run full Glass Box audit on a single marketing material.

    Returns:
        {
            'run_id': str,
            'filename': str,
            'product_id': str,
            'material_type': str,
            'status': 'PASS' | 'FAIL',
            'core_claims': List[str],
            'disclaimers': List[str],
            'violations': List[Dict],
            'violation_count': int
        }
    """
    try:
        # Load material (use output_path from CSV if available)
        output_path = run_metadata.get('output_path')
        material_content = load_material(run_id, output_path=output_path)

        # Load product YAML
        product_id = run_metadata['product_id']
        product_yaml = load_product_yaml(product_id)
        product_name = product_yaml.get('name', product_id)
        authorized_claims = flatten_authorized_claims(product_yaml)
        specs = flatten_specs(product_yaml)
        prohibited_claims = flatten_prohibited_claims(product_yaml)
        clarifications = flatten_clarifications(product_yaml)

        # STEP 1: Extract atomic claims (separated into core + disclaimers)
        extraction_result = extract_atomic_claims(
            material_content,
            product_name,
            run_metadata['material_type']
        )

        core_claims = extraction_result.get('core_claims', [])
        disclaimers = extraction_result.get('disclaimers', [])

        # Combine core claims and disclaimers for validation
        # Disclaimers can contain critical errors (FDA claims, unsafe dosage, etc.)
        all_claims = core_claims + disclaimers

        # Handle empty list (all fluff) → PASS
        if not all_claims:
            return {
                'run_id': run_id,
                'filename': f"{run_id}.txt",
                'product_id': product_id,
                'material_type': run_metadata['material_type'],
                'status': 'PASS',
                'core_claims': [],
                'disclaimers': disclaimers,
                'violations': [],
                'violation_count': 0
            }

        # STEP 2: Verify ALL claims (core + disclaimers) against authorized_claims, specs, prohibited_claims, and clarifications
        violations = []
        for claim in all_claims:
            verification = judge.verify_claim(claim, authorized_claims, specs, prohibited_claims, clarifications)

            if verification['is_violation']:
                violations.append({
                    'claim': claim,
                    'violated_rule': verification['violated_rule'],
                    'contradiction_score': verification['contradiction_score']
                })

        # Determine status
        status = 'FAIL' if violations else 'PASS'

        return {
            'run_id': run_id,
            'filename': f"{run_id}.txt",
            'product_id': product_id,
            'material_type': run_metadata['material_type'],
            'status': status,
            'core_claims': core_claims,
            'disclaimers': disclaimers,
            'violations': violations,
            'violation_count': len(violations)
        }

    except Exception as e:
        log_error(run_id, run_metadata, e)
        return {
            'run_id': run_id,
            'filename': f"{run_id}.txt",
            'product_id': run_metadata.get('product_id', 'unknown'),
            'material_type': run_metadata.get('material_type', 'unknown'),
            'status': 'ERROR',
            'core_claims': [],
            'disclaimers': [],
            'violations': [],
            'violation_count': 0,
            'error': str(e)
        }


def save_audit_results(audit_results: List[Dict], output_path: Path):
    """Save audit results to CSV."""
    rows = []

    for result in audit_results:
        if result['status'] == 'PASS' or result['status'] == 'ERROR':
            # One row for PASS/ERROR
            rows.append({
                'Filename': result['filename'],
                'Status': result['status'],
                'Violated_Rule': '',
                'Extracted_Claim': '',
                'Confidence_Score': ''
            })
        else:
            # One row per violation
            for violation in result['violations']:
                rows.append({
                    'Filename': result['filename'],
                    'Status': 'FAIL',
                    'Violated_Rule': violation['violated_rule'],
                    'Extracted_Claim': violation['claim'],
                    'Confidence_Score': f"{violation['contradiction_score']:.4f}"
                })

    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False)
    logger.info(f"Saved audit results to {output_path}")


def print_summary(audit_results: List[Dict]):
    """Print summary table to console."""
    total_runs = len(audit_results)
    passed = sum(1 for r in audit_results if r['status'] == 'PASS')
    failed = sum(1 for r in audit_results if r['status'] == 'FAIL')
    errors = sum(1 for r in audit_results if r['status'] == 'ERROR')
    total_violations = sum(r['violation_count'] for r in audit_results)

    print("\n" + "=" * 70)
    print("GLASS BOX AUDIT PIPELINE - SUMMARY")
    print("=" * 70)
    print(f"Total runs audited:     {total_runs}")
    print(f"  ✓ PASS:               {passed} ({passed/total_runs*100:.1f}%)")
    print(f"  ✗ FAIL:               {failed} ({failed/total_runs*100:.1f}%)")
    print(f"  ! ERROR:              {errors} ({errors/total_runs*100:.1f}%)")
    print(f"\nTotal violations:       {total_violations}")
    print("=" * 70)

    # Breakdown by product
    print("\nBreakdown by Product:")
    product_stats = {}
    for result in audit_results:
        pid = result['product_id']
        if pid not in product_stats:
            product_stats[pid] = {'total': 0, 'pass': 0, 'fail': 0}
        product_stats[pid]['total'] += 1
        if result['status'] == 'PASS':
            product_stats[pid]['pass'] += 1
        elif result['status'] == 'FAIL':
            product_stats[pid]['fail'] += 1

    for pid, stats in product_stats.items():
        print(f"  {pid:30s} {stats['pass']:3d} PASS / {stats['fail']:3d} FAIL / {stats['total']:3d} total")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description='Glass Box Audit Pipeline (GPT-4o-mini + NLI)')
    parser.add_argument('--limit', type=int, help='Limit number of runs to audit')
    parser.add_argument('--skip', type=int, default=0, help='Skip first N runs')
    parser.add_argument('--run-id', type=str, help='Audit specific run_id only')
    parser.add_argument('--resume', action='store_true', help='Resume from checkpoint (skip completed runs)')
    parser.add_argument('--clean', action='store_true', help='Clear checkpoint and start fresh')
    parser.add_argument('--use-semantic-filter', action='store_true', help='Enable semantic pre-filtering (80% FP reduction)')
    args = parser.parse_args()

    # Clear checkpoint if requested
    if args.clean:
        if CHECKPOINT_FILE.exists():
            CHECKPOINT_FILE.unlink()
            logger.info("✓ Cleared checkpoint file")
        if ERROR_LOG_FILE.exists():
            ERROR_LOG_FILE.unlink()
            logger.info("✓ Cleared error log")

    # Initialize NLI Judge with optional semantic filtering
    logger.info("Initializing NLI Judge...")
    judge = NLIJudge(use_semantic_filter=args.use_semantic_filter)

    # Load runs
    if args.run_id:
        logger.info(f"Auditing single run: {args.run_id}")
        # Load metadata from experiments.csv
        df = pd.read_csv(EXPERIMENTS_CSV)
        run_row = df[df['run_id'] == args.run_id]
        if run_row.empty:
            logger.error(f"Run ID not found: {args.run_id}")
            return
        runs = run_row.to_dict('records')
    else:
        logger.info("Loading completed runs from experiments.csv...")
        runs_df = get_completed_runs()

        # Resume from checkpoint if requested
        if args.resume:
            completed_run_ids = load_completed_run_ids()
            runs_df = runs_df[~runs_df['run_id'].isin(completed_run_ids)]
            logger.info(f"Resuming: {len(runs_df)} runs remaining")

        runs = runs_df.to_dict('records')

        # Apply skip and limit
        if args.skip:
            runs = runs[args.skip:]
            logger.info(f"Skipped first {args.skip} runs")

        if args.limit:
            runs = runs[:args.limit]

    logger.info(f"Auditing {len(runs)} runs...")

    # Run audit pipeline with checkpoints
    audit_results = []
    total_violations = 0

    with tqdm(total=len(runs), desc="Auditing runs", unit="run") as pbar:
        for i, run_metadata in enumerate(runs, 1):
            run_id = run_metadata['run_id']
            result = audit_single_run(run_id, run_metadata, judge)
            audit_results.append(result)

            # Save checkpoint immediately after each run
            save_checkpoint(result)

            # Track violations
            total_violations += result.get('violation_count', 0)

            # Update progress bar with stats
            pbar.set_postfix({
                'violations': total_violations,
                'errors': len(error_log)
            })
            pbar.update(1)

            # Periodic CSV export every 50 runs
            if i % 50 == 0:
                save_audit_results(audit_results, AUDIT_OUTPUT_CSV)
                logger.info(f"Progress checkpoint: {i}/{len(runs)} runs completed")

    # Save final results
    save_audit_results(audit_results, AUDIT_OUTPUT_CSV)
    save_error_log()

    # Print summary
    print_summary(audit_results)


if __name__ == "__main__":
    main()
