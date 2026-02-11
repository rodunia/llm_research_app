"""Glass Box Audit Pipeline: Atomic Claim Extraction + NLI-based Verification.

This module implements a two-step audit process:
1. STEP 1 (Atomizer): Extract atomic claims using Google Gemini
2. STEP 2 (Judge): Verify claims using cross-encoder/nli-roberta-base

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
import google.generativeai as genai

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
PRODUCTS_DIR = PROJECT_ROOT / "products"
RESULTS_DIR = PROJECT_ROOT / "results"
EXPERIMENTS_CSV = RESULTS_DIR / "experiments.csv"
AUDIT_OUTPUT_CSV = RESULTS_DIR / "final_audit_results.csv"

# Google Gemini Configuration
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
EXTRACTION_MODEL = "gemini-2.0-flash-001"
EXTRACTION_TEMPERATURE = 0

# NLI Configuration
NLI_MODEL_NAME = "cross-encoder/nli-roberta-base"
VIOLATION_THRESHOLD = 0.90  # Contradiction score threshold

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


# ==================== STEP 1: ATOMIC CLAIM EXTRACTION ====================

ATOMIZER_SYSTEM_PROMPT = """You are a forensic claim extraction system for marketing compliance audits.

TASK: Extract EVERY verifiable fact, technical specification, and safety warning from the marketing material.

EXTRACTION RULES:
1. Split compound sentences into atomic facts
   - Example: "6.3 inch OLED display" → ["Screen is 6.3 inches", "Screen is OLED"]
   - Example: "Contains 3mg melatonin, non-habit-forming" → ["Contains 3mg melatonin", "Non-habit-forming"]

2. Maintain original terminology (do not over-paraphrase)
   - Keep exact numbers, units, brand names, technical terms

3. Extract factual claims only:
   - Product features (e.g., "Has 128GB storage")
   - Technical specifications (e.g., "Powered by Snapdragon 888")
   - Safety warnings (e.g., "Consult physician before use")
   - Quantitative statements (e.g., "Provides 7 years of updates")
   - Comparative statements (e.g., "Faster than previous generation")

4. Ignore subjective marketing fluff:
   - Do NOT extract: "stunning", "amazing", "revolutionary", "incredible"
   - Do NOT extract vague claims like: "enhances your experience", "transforms your life"

5. If the material is entirely vague/subjective/fluff, return an empty list []

OUTPUT FORMAT (strict JSON):
{
  "claims": [
    "atomic claim 1",
    "atomic claim 2",
    "atomic claim 3"
  ]
}

IMPORTANT: Return ONLY valid JSON. No markdown, no explanation.
"""


def extract_atomic_claims(material_content: str, product_name: str, material_type: str) -> List[str]:
    """
    Extract atomic claims using Google Gemini (Forensic Extraction).

    Args:
        material_content: Marketing material text
        product_name: Product name for context
        material_type: Type of material (e.g., 'faq', 'digital_ad')

    Returns:
        List of atomic claim strings (empty list if all fluff)
    """
    full_prompt = f"""{ATOMIZER_SYSTEM_PROMPT}

PRODUCT: {product_name}
MATERIAL TYPE: {material_type}

MARKETING MATERIAL:
{material_content}

Extract all atomic claims as JSON.
"""

    try:
        model = genai.GenerativeModel(
            model_name=EXTRACTION_MODEL,
            generation_config={
                "temperature": EXTRACTION_TEMPERATURE,
                "response_mime_type": "application/json"
            }
        )

        response = model.generate_content(full_prompt)
        result = json.loads(response.text)
        claims = result.get('claims', [])

        logger.debug(f"Extracted {len(claims)} atomic claims")

        # Rate limiting to avoid 429 errors
        time.sleep(0.5)

        return claims

    except Exception as e:
        logger.error(f"Atomic extraction failed: {e}")
        # If rate limited, wait longer before continuing
        if "429" in str(e) or "Resource exhausted" in str(e):
            logger.warning("Rate limit hit, waiting 5 seconds...")
            time.sleep(5)
        return []


# ==================== STEP 2: CLAIM VERIFICATION ====================

class NLIJudge:
    """NLI-based claim verification using cross-encoder/nli-roberta-base."""

    def __init__(self):
        logger.info(f"Loading NLI model: {NLI_MODEL_NAME}")
        self.tokenizer = AutoTokenizer.from_pretrained(NLI_MODEL_NAME)
        self.model = AutoModelForSequenceClassification.from_pretrained(NLI_MODEL_NAME)
        self.model.to(DEVICE)
        self.model.eval()

        # Label mapping: [contradiction, entailment, neutral]
        self.label_names = ['contradiction', 'entailment', 'neutral']

    def verify_claim(self, claim: str, authorized_claims: List[str]) -> Dict:
        """
        Verify if a claim contradicts any authorized claims.

        Args:
            claim: Extracted atomic claim
            authorized_claims: List of authorized claims from YAML

        Returns:
            {
                'is_violation': bool,
                'violated_rule': str or None,
                'contradiction_score': float,
                'best_match_rule': str,
                'best_match_type': str (entailment/neutral/contradiction)
            }
        """
        if not authorized_claims:
            return {
                'is_violation': False,
                'violated_rule': None,
                'contradiction_score': 0.0,
                'best_match_rule': None,
                'best_match_type': 'no_rules'
            }

        max_contradiction_score = 0.0
        violated_rule = None
        best_match_rule = None
        best_match_type = None
        best_match_score = 0.0

        for auth_claim in authorized_claims:
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

def load_material(run_id: str) -> str:
    """Load generated marketing material from outputs/."""
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
            'atomic_claims': List[str],
            'violations': List[Dict],
            'violation_count': int
        }
    """
    try:
        # Load material
        material_content = load_material(run_id)

        # Load product YAML
        product_id = run_metadata['product_id']
        product_yaml = load_product_yaml(product_id)
        product_name = product_yaml.get('name', product_id)
        authorized_claims = flatten_authorized_claims(product_yaml)

        # STEP 1: Extract atomic claims
        atomic_claims = extract_atomic_claims(
            material_content,
            product_name,
            run_metadata['material_type']
        )

        # Handle empty list (all fluff) → PASS
        if not atomic_claims:
            return {
                'run_id': run_id,
                'filename': f"{run_id}.txt",
                'product_id': product_id,
                'material_type': run_metadata['material_type'],
                'status': 'PASS',
                'atomic_claims': [],
                'violations': [],
                'violation_count': 0
            }

        # STEP 2: Verify each claim
        violations = []
        for claim in atomic_claims:
            verification = judge.verify_claim(claim, authorized_claims)

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
            'atomic_claims': atomic_claims,
            'violations': violations,
            'violation_count': len(violations)
        }

    except Exception as e:
        logger.error(f"Audit failed for {run_id}: {e}")
        return {
            'run_id': run_id,
            'filename': f"{run_id}.txt",
            'product_id': run_metadata.get('product_id', 'unknown'),
            'material_type': run_metadata.get('material_type', 'unknown'),
            'status': 'ERROR',
            'atomic_claims': [],
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
    parser = argparse.ArgumentParser(description='Glass Box Audit Pipeline')
    parser.add_argument('--limit', type=int, help='Limit number of runs to audit')
    parser.add_argument('--run-id', type=str, help='Audit specific run_id only')
    args = parser.parse_args()

    # Initialize NLI Judge
    logger.info("Initializing NLI Judge...")
    judge = NLIJudge()

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
        runs = runs_df.to_dict('records')

        if args.limit:
            runs = runs[:args.limit]

    logger.info(f"Auditing {len(runs)} runs...")

    # Run audit pipeline
    audit_results = []
    for run_metadata in tqdm(runs, desc="Auditing runs"):
        run_id = run_metadata['run_id']
        result = audit_single_run(run_id, run_metadata, judge)
        audit_results.append(result)

    # Save results
    save_audit_results(audit_results, AUDIT_OUTPUT_CSV)

    # Print summary
    print_summary(audit_results)


if __name__ == "__main__":
    main()
