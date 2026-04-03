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
EXTRACTION_MODEL = "gpt-4o"  # Upgraded from gpt-4o-mini for better extraction accuracy
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
   - Safety warnings (e.g., "Consult physician before use", "Avoid if over 18")
   - **Storage instructions** (e.g., "Store at 15-30°C", "Store at exactly 0°C", "Keep in cool dry place")
   - **Dosing/usage instructions** (e.g., "Take before bed", "Take every 2 hours", "Do not exceed 3mg daily")
   - Quantitative statements (e.g., "Provides 7 years of updates")
   - Comparative statements (e.g., "Faster than previous generation")
   - Governance mechanisms (e.g., "Proposals auto-pass without quorum")

4. CRITICAL: Extract ALL parts of compound sentences
   - If a sentence contains multiple distinct facts or policies, extract EACH one separately
   - Do NOT omit secondary clauses, conditions, or exceptions
   - Example: "Available 24/7 except during regional maintenance windows" → ["Available 24/7", "Except during regional maintenance windows"]
   - Example: "Store at room temperature and keep out of reach of children" → ["Store at room temperature", "Keep out of reach of children"]

5. CRITICAL: Extract claims from BOTH main content AND disclaimer/warning sections
   - Disclaimer sections often contain verifiable storage instructions, dosing instructions, and age restrictions
   - These MUST be extracted as core_claims if they are verifiable facts
   - Only extract as "disclaimers" if they are hedging language like "may vary", "not guaranteed", "results may differ"

6. Ignore subjective marketing fluff:
   - Do NOT extract: "stunning", "amazing", "revolutionary", "incredible"
   - Do NOT extract vague claims like: "enhances your experience", "transforms your life"

7. If the material is entirely vague/subjective/fluff, return empty lists

OUTPUT FORMAT (strict JSON - FLAT STRING ARRAYS ONLY):
{
  "core_claims": [
    "atomic core claim 1",
    "atomic core claim 2",
    "Store at exactly 0°C",
    "Take melatonin every 2 hours"
  ],
  "disclaimers": [
    "Results may vary",
    "Consult a healthcare professional"
  ]
}

INCORRECT FORMAT (DO NOT USE NESTED OBJECTS):
{
  "core_claims": [
    {"storage": "Store at 0°C"}  ← WRONG! Must be flat string
  ]
}

IMPORTANT:
- Return ONLY valid JSON with FLAT STRING ARRAYS
- Each claim must be a simple string, NOT a nested object
- No markdown, no explanation
"""


def extract_atomic_claims(material_content: str, product_name: str, material_type: str) -> Dict:
    """
    Extract atomic claims using OpenAI GPT-4o (Forensic Extraction).
    Returns both core claims and disclaimers separately, plus metadata.

    Automatically retries up to 3 times on transient API errors with exponential backoff.

    Args:
        material_content: Marketing material text
        product_name: Product name for context
        material_type: Type of material (e.g., 'faq', 'digital_ad')

    Returns:
        Dict with:
            - core_claims: List[str]
            - disclaimers: List[str]
            - extraction_retry_count: int
            - extraction_error_type: str
            - extraction_api_latency_ms: int
            - extraction_prompt_tokens: int
            - extraction_completion_tokens: int
            - extraction_model_version: str
    """
    import hashlib

    user_prompt = f"""PRODUCT: {product_name}
MATERIAL TYPE: {material_type}

MARKETING MATERIAL:
{material_content}

Extract all atomic claims as JSON with core_claims and disclaimers separated.
"""

    # Track retry metadata
    retry_count = 0
    error_type = "none"

    for attempt in range(3):  # Max 3 attempts
        try:
            # Measure API latency
            api_start = time.time()
            response = openai_client.chat.completions.create(
                model=EXTRACTION_MODEL,
                temperature=EXTRACTION_TEMPERATURE,
                messages=[
                    {"role": "system", "content": ATOMIZER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )
            api_latency_ms = int((time.time() - api_start) * 1000)

            # Extract claims
            result = json.loads(response.choices[0].message.content)
            core_claims = result.get('core_claims', [])
            disclaimers = result.get('disclaimers', [])

            logger.debug(f"Extracted {len(core_claims)} core claims, {len(disclaimers)} disclaimers")

            # Capture metadata
            return {
                'core_claims': core_claims,
                'disclaimers': disclaimers,
                'extraction_retry_count': retry_count,
                'extraction_error_type': error_type,
                'extraction_api_latency_ms': api_latency_ms,
                'extraction_prompt_tokens': response.usage.prompt_tokens,
                'extraction_completion_tokens': response.usage.completion_tokens,
                'extraction_model_version': response.model,
            }

        except RateLimitError as e:
            retry_count += 1
            error_type = "rate_limit"
            if attempt < 2:  # Retry if not last attempt
                wait_time = 2 ** attempt
                logger.warning(f"Rate limit hit (attempt {attempt+1}/3), retrying in {wait_time}s")
                time.sleep(wait_time)
                continue
            logger.error("Max retries exceeded for rate limit")
            raise

        except APIConnectionError as e:
            retry_count += 1
            error_type = "timeout"
            if attempt < 2:
                wait_time = 2 ** attempt
                logger.warning(f"Connection error (attempt {attempt+1}/3), retrying in {wait_time}s")
                time.sleep(wait_time)
                continue
            logger.error("Max retries exceeded for connection error")
            raise

        except APIError as e:
            retry_count += 1
            error_type = "api_error"
            logger.error(f"API error (non-retryable): {e}")
            raise

    raise APIError("Max retries exceeded")


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
        Verify if a claim violates compliance rules using correct NLI logic:
        - SPECS/AUTHORIZED: Check for CONTRADICTION (claim contradicts facts = violation)
        - PROHIBITED: Check for ENTAILMENT (claim matches forbidden statement = violation)

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

        # CORRECTED LOGIC: Separate handling for different rule types
        # 1. Build factual reference claims (specs + authorized + clarifications)
        #    - These should NOT be contradicted by marketing claims
        factual_references = []
        if authorized_claims:
            factual_references.extend(authorized_claims)
        if specs:
            factual_references.extend(specs)
        if clarifications:
            # Handle clarifications (can be list or dict with nested lists)
            if isinstance(clarifications, dict):
                for category_claims in clarifications.values():
                    if isinstance(category_claims, list):
                        factual_references.extend(category_claims)
            elif isinstance(clarifications, (list, tuple)):
                factual_references.extend(clarifications)
            else:
                logger.warning(f"Unexpected clarifications type: {type(clarifications)}")

        # 2. Build prohibited claims list (things marketing should NOT say)
        #    - These should NOT be entailed/matched by marketing claims
        prohibited_references = prohibited_claims if prohibited_claims else []

        # Category-based filtering
        claim_category = classify_claim_category(claim)

        # Filter factual references by category
        # FIXED: Only compare if EXACT category match (exclude 'general' to prevent false positives)
        filtered_factual = []
        for rule in factual_references:
            rule_category = classify_claim_category(rule)
            # Compare only if same category AND neither is 'general'
            if rule_category == claim_category and rule_category != 'general':
                filtered_factual.append(rule)

        # Filter prohibited references by category
        # Ground truth prohibited statements are actual statements (not meta-descriptions)
        # Can now use NLI entailment checking directly
        filtered_prohibited = []
        for rule in prohibited_references:
            rule_category = classify_claim_category(rule)
            # Compare only if same category AND neither is 'general'
            if rule_category == claim_category and rule_category != 'general':
                filtered_prohibited.append(rule)

        # Track violations
        max_violation_score = 0.0
        violated_rule = None
        best_match_rule = None
        best_match_type = None
        best_match_score = 0.0

        # CHECK 1: Does claim CONTRADICT factual references (specs/authorized)?
        for fact_claim in filtered_factual:
            inputs = self.tokenizer(
                claim,
                fact_claim,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=512
            ).to(DEVICE)

            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=1)[0]

            contradiction_score = probs[0].item()
            entailment_score = probs[1].item()
            neutral_score = probs[2].item()

            # Violation if claim CONTRADICTS factual reference
            if contradiction_score > max_violation_score:
                max_violation_score = contradiction_score
                violated_rule = fact_claim

            # Track best match overall
            all_scores = {
                'contradiction': contradiction_score,
                'entailment': entailment_score,
                'neutral': neutral_score
            }
            current_best_label = max(all_scores, key=all_scores.get)
            current_best_score = all_scores[current_best_label]

            if current_best_score > best_match_score:
                best_match_score = current_best_score
                best_match_rule = fact_claim
                best_match_type = current_best_label

        # CHECK 2: Does claim MATCH/ENTAIL prohibited claims?
        for prohibited_claim in filtered_prohibited:
            inputs = self.tokenizer(
                claim,
                prohibited_claim,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=512
            ).to(DEVICE)

            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=1)[0]

            contradiction_score = probs[0].item()
            entailment_score = probs[1].item()
            neutral_score = probs[2].item()

            # Violation if claim ENTAILS (matches) prohibited statement
            if entailment_score > max_violation_score:
                max_violation_score = entailment_score
                violated_rule = prohibited_claim

            # Track best match overall
            all_scores = {
                'contradiction': contradiction_score,
                'entailment': entailment_score,
                'neutral': neutral_score
            }
            current_best_label = max(all_scores, key=all_scores.get)
            current_best_score = all_scores[current_best_label]

            if current_best_score > best_match_score:
                best_match_score = current_best_score
                best_match_rule = prohibited_claim
                best_match_type = current_best_label

        # Determine if violation
        is_violation = max_violation_score > VIOLATION_THRESHOLD

        return {
            'is_violation': is_violation,
            'violated_rule': violated_rule if is_violation else None,
            'contradiction_score': max_violation_score,
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


def load_ground_truth_yaml(product_id: str) -> dict:
    """
    Load ground truth YAML file for NLI verification.
    Ground truth YAMLs contain factual specs and prohibited statements
    optimized for NLI checking (separate from generation-optimized YAMLs).

    Returns:
        Ground truth dict with factual_specs, prohibited_statements, etc.
        Returns None if ground truth file doesn't exist.
    """
    file_path = PRODUCTS_DIR / f"{product_id}_GROUND_TRUTH.yaml"
    if not file_path.exists():
        logger.warning(f"Ground truth YAML not found: {file_path}, falling back to regular YAML")
        return None

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


def flatten_ground_truth_specs(ground_truth: dict) -> List[str]:
    """
    Flatten ground truth factual_specs into list of strings.
    Ground truth specs are already formatted as atomic statements.

    Returns:
        List of factual spec strings
    """
    factual_specs = ground_truth.get('factual_specs', {})
    spec_list = []

    # Extract all values from nested categories
    def extract_strings(data):
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

    spec_list = extract_strings(factual_specs)
    return spec_list


def flatten_ground_truth_prohibited(ground_truth: dict) -> List[str]:
    """
    Flatten ground truth prohibited_statements into list of strings.
    These are actual statements (not meta-descriptions) for NLI entailment checking.

    Returns:
        List of prohibited statement strings
    """
    prohibited_statements = ground_truth.get('prohibited_statements', {})
    prohibited_list = []

    # Extract all values from nested categories
    def extract_strings(data):
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

    prohibited_list = extract_strings(prohibited_statements)
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
        'ram': ['ram', 'lpddr'],  # Check RAM before storage (more specific)
        'storage': ['storage', 'ufs', 'expandable', 'microsd'],  # Removed 'gb', 'memory' to avoid conflicts
        'battery': ['battery', 'mah', 'charging', 'power', 'watt', 'fast charging', 'wireless charging'],
        'processor': ['processor', 'cpu', 'chipset', 'ghz', 'core', 'gpu', 'npu', 'tensor', 'snapdragon', 'exynos'],
        'network': ['5g', '4g', 'lte', 'wifi', 'wi-fi', 'bluetooth', 'cellular', 'connectivity', 'nfc', 'sub-6'],

        # Supplement categories
        'dosage': ['mg', 'dose', 'dosage', 'serving', 'tablet', 'capsule', 'pill', 'take', 'consume'],
        'ingredients': ['contain', 'ingredient', 'gluten', 'soy', 'dairy', 'allergen', 'vegan', 'vegetarian', 'non-gmo', 'fish', 'formulation', 'extract', 'blend'],
        'safety': ['safe', 'side effect', 'drowsiness', 'warning', 'caution', 'pregnant', 'children', 'adult', 'age', 'habit', 'addictive', 'dependency'],
        'manufacturing': ['manufactured', 'facility', 'gmp', 'tested', 'quality', 'certified', 'third-party', 'purity', 'potency'],
        'regulatory': ['fda', 'approved', 'evaluated', 'regulated', 'drug', 'supplement', 'dshea', 'clinically', 'proven'],
        'efficacy': ['help', 'support', 'promote', 'improve', 'enhance', 'treat', 'cure', 'prevent', 'reduce', 'sleep', 'insomnia', 'rest', 'relax', 'wake', 'rhythm', 'cycle', 'pattern', 'onset'],
        'storage_temp': ['store', 'storage', 'temperature', '°c', 'degrees', 'room temperature', 'cool', 'dry', 'freeze', 'heat', 'light'],

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

        # Try to load ground truth YAML (fallback to regular YAML if not available)
        ground_truth = load_ground_truth_yaml(product_id)

        if ground_truth:
            # Use ground truth for verification
            logger.debug(f"Using ground truth YAML for {product_id}")
            specs = flatten_ground_truth_specs(ground_truth)
            prohibited_claims = flatten_ground_truth_prohibited(ground_truth)
            # Authorized claims still from regular YAML (not needed for verification)
            authorized_claims = []
            clarifications = []
        else:
            # Fallback to regular YAML
            logger.debug(f"Using regular YAML for {product_id}")
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

        # Capture extraction metadata
        extraction_metadata = {
            'extraction_retry_count': extraction_result.get('extraction_retry_count', 0),
            'extraction_error_type': extraction_result.get('extraction_error_type', 'none'),
            'extraction_api_latency_ms': extraction_result.get('extraction_api_latency_ms', 0),
            'extraction_prompt_tokens': extraction_result.get('extraction_prompt_tokens', 0),
            'extraction_completion_tokens': extraction_result.get('extraction_completion_tokens', 0),
            'extraction_model_version': extraction_result.get('extraction_model_version', ''),
        }

        # Combine core claims and disclaimers for validation
        # Disclaimers can contain critical errors (FDA claims, unsafe dosage, etc.)
        all_claims = core_claims + disclaimers

        # Handle empty list (all fluff) → PASS
        if not all_claims:
            result = {
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
            result.update(extraction_metadata)
            return result

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

        result = {
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
        result.update(extraction_metadata)
        return result

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
    """Save audit results to CSV with extraction metadata."""
    rows = []

    for result in audit_results:
        # Base metadata common to all rows for this result
        base_metadata = {
            'run_id': result.get('run_id', ''),
            'product_id': result.get('product_id', ''),
            'material_type': result.get('material_type', ''),
            'extraction_retry_count': result.get('extraction_retry_count', 0),
            'extraction_error_type': result.get('extraction_error_type', ''),
            'extraction_api_latency_ms': result.get('extraction_api_latency_ms', 0),
            'extraction_prompt_tokens': result.get('extraction_prompt_tokens', 0),
            'extraction_completion_tokens': result.get('extraction_completion_tokens', 0),
            'extraction_model_version': result.get('extraction_model_version', ''),
        }

        if result['status'] == 'PASS' or result['status'] == 'ERROR':
            # One row for PASS/ERROR
            row = {
                'Filename': result['filename'],
                'Status': result['status'],
                'Violated_Rule': '',
                'Extracted_Claim': '',
                'Confidence_Score': ''
            }
            row.update(base_metadata)
            rows.append(row)
        else:
            # One row per violation
            for violation in result['violations']:
                row = {
                    'Filename': result['filename'],
                    'Status': 'FAIL',
                    'Violated_Rule': violation['violated_rule'],
                    'Extracted_Claim': violation['claim'],
                    'Confidence_Score': f"{violation['contradiction_score']:.4f}"
                }
                row.update(base_metadata)
                rows.append(row)

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
