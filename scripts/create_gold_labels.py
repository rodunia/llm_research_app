"""Create golden dataset for DeBERTa fine-tuning using LLM-assisted labeling.

This script samples claims from all_claims_review.csv and uses Gemini to label them
as Contradiction (0), Entailment (1), or Neutral (2) for NLI training.
"""

import argparse
import json
import os
import random
from pathlib import Path
from typing import Dict, List

import pandas as pd
import yaml
from dotenv import load_dotenv
from tqdm import tqdm
import google.generativeai as genai

# Load environment
load_dotenv()

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
PRODUCTS_DIR = PROJECT_ROOT / "products"
RESULTS_DIR = PROJECT_ROOT / "results"
ALL_CLAIMS_CSV = RESULTS_DIR / "all_claims_review.csv"
OUTPUT_CSV = RESULTS_DIR / "deberta_gold_train.csv"

# Gemini Configuration
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
LABELING_MODEL = "gemini-2.0-flash-001"
LABELING_TEMPERATURE = 0

# Cost estimation (Gemini 2.0 Flash pricing as of 2025)
COST_PER_1M_INPUT_TOKENS = 0.075  # USD
COST_PER_1M_OUTPUT_TOKENS = 0.30  # USD
AVG_TOKENS_PER_CALL = 800  # Estimate: 600 input + 200 output
ESTIMATED_COST_PER_CALL = (600 * COST_PER_1M_INPUT_TOKENS + 200 * COST_PER_1M_OUTPUT_TOKENS) / 1_000_000


LABELING_SYSTEM_PROMPT = """You are a precise data labeling system for Natural Language Inference (NLI) training.

TASK: Classify the relationship between AUTHORIZED RULES (premise) and EXTRACTED CLAIM (hypothesis).

LABEL DEFINITIONS:

LABEL 0 (CONTRADICTION/HALLUCINATION):
- The claim directly contradicts the rules
- The claim invents specific features/specs NOT present in the rules (e.g., "Waterproof" when rules are silent)
- The claim makes quantitative statements that differ from the rules (e.g., "10GB storage" vs "8GB storage")

LABEL 1 (ENTAILMENT):
- The claim is explicitly supported by the rules
- The claim is a paraphrase or logical consequence of the rules
- All facts in the claim are verifiable from the rules

LABEL 2 (NEUTRAL):
- The claim is vague marketing fluff that doesn't make verifiable factual assertions
- Examples: "Buy now", "Amazing value", "Future of finance", "Transform your life"
- The claim is about something the rules don't address (but doesn't contradict)

IMPORTANT GUIDELINES:
- Be strict about LABEL 1: Only use if the claim is clearly supported by rules
- If rules are silent on a specific feature and claim asserts it → LABEL 0 (hallucination)
- If claim is purely subjective/emotional → LABEL 2 (neutral)
- Focus on factual content, not marketing tone

OUTPUT FORMAT (strict JSON):
{
  "label": 0 or 1 or 2,
  "reasoning": "brief explanation (1-2 sentences)"
}

IMPORTANT: Return ONLY valid JSON. No markdown, no explanation outside JSON.
"""


def load_product_rules(product_id: str) -> str:
    """Load product YAML and format authorized claims as premise text."""
    yaml_path = PRODUCTS_DIR / f"{product_id}.yaml"

    if not yaml_path.exists():
        raise FileNotFoundError(f"Product YAML not found: {yaml_path}")

    with open(yaml_path, 'r', encoding='utf-8') as f:
        product_yaml = yaml.safe_load(f)

    # Extract authorized claims
    authorized = product_yaml.get('authorized_claims', {})

    if isinstance(authorized, dict):
        # Nested structure: flatten by category
        all_claims = []
        for category, claims in authorized.items():
            if isinstance(claims, list):
                all_claims.extend(claims)
    elif isinstance(authorized, list):
        all_claims = authorized
    else:
        all_claims = []

    # Format as premise text
    if all_claims:
        premise = "AUTHORIZED CLAIMS:\n" + "\n".join([f"- {claim}" for claim in all_claims])
    else:
        premise = "AUTHORIZED CLAIMS: (No specific claims authorized for this product)"

    return premise


def label_claim_with_llm(premise: str, hypothesis: str) -> Dict:
    """
    Use Gemini to label the claim.

    Args:
        premise: Authorized rules/claims from YAML
        hypothesis: Extracted claim to classify

    Returns:
        {'label': int, 'reasoning': str}
    """
    user_prompt = f"""AUTHORIZED RULES (PREMISE):
{premise}

EXTRACTED CLAIM (HYPOTHESIS):
{hypothesis}

Classify the relationship and return JSON with label (0/1/2) and reasoning.
"""

    try:
        model = genai.GenerativeModel(
            model_name=LABELING_MODEL,
            generation_config={
                "temperature": LABELING_TEMPERATURE,
                "response_mime_type": "application/json"
            }
        )

        full_prompt = f"{LABELING_SYSTEM_PROMPT}\n\n{user_prompt}"
        response = model.generate_content(full_prompt)
        result = json.loads(response.text)

        return {
            'label': int(result.get('label', 2)),  # Default to neutral if parsing fails
            'reasoning': result.get('reasoning', '')
        }

    except Exception as e:
        print(f"Labeling error: {e}")
        # Default to neutral on error
        return {'label': 2, 'reasoning': f'Error: {str(e)}'}


def create_golden_dataset(sample_size: int = 500, random_seed: int = 42, skip_confirm: bool = False):
    """Create golden dataset for DeBERTa fine-tuning."""

    # Load claims
    print(f"Loading claims from {ALL_CLAIMS_CSV}...")
    df = pd.read_csv(ALL_CLAIMS_CSV)
    print(f"Total claims available: {len(df):,}")

    # Sample rows
    random.seed(random_seed)
    if len(df) > sample_size:
        sampled_df = df.sample(n=sample_size, random_state=random_seed)
        print(f"Sampled {sample_size} claims for labeling")
    else:
        sampled_df = df
        print(f"Using all {len(df)} claims (less than sample size)")

    # Estimate cost
    estimated_cost = len(sampled_df) * ESTIMATED_COST_PER_CALL
    print(f"\nEstimated cost: ${estimated_cost:.4f} USD")
    print(f"  - Model: {LABELING_MODEL}")
    print(f"  - Calls: {len(sampled_df)}")
    print(f"  - Est. tokens per call: {AVG_TOKENS_PER_CALL}")

    # Confirm
    if not skip_confirm:
        response = input("\nProceed with labeling? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("Aborted.")
            return
    else:
        print("\nSkipping confirmation (--yes flag)")

    # Process each claim
    labeled_data = []

    for idx, row in tqdm(sampled_df.iterrows(), total=len(sampled_df), desc="Labeling claims"):
        product_id = row['product_id']
        extracted_claim = row['extracted_claim']

        # Load product rules (premise)
        try:
            premise = load_product_rules(product_id)
        except FileNotFoundError as e:
            print(f"\n⚠️  {e}")
            continue

        # Label with LLM
        result = label_claim_with_llm(premise, extracted_claim)

        labeled_data.append({
            'premise_rules': premise,
            'hypothesis_claim': extracted_claim,
            'label': result['label'],
            'reasoning': result['reasoning'],
            'product_id': product_id,
            'run_id': row['run_id']
        })

    # Create output dataframe
    output_df = pd.DataFrame(labeled_data)

    # Save to CSV
    output_df.to_csv(OUTPUT_CSV, index=False)
    print(f"\n✓ Golden dataset saved to {OUTPUT_CSV}")

    # Print statistics
    print(f"\nDataset Statistics:")
    print(f"  Total labeled: {len(output_df):,}")
    print(f"  Label distribution:")
    label_counts = output_df['label'].value_counts().sort_index()
    label_names = {0: 'CONTRADICTION', 1: 'ENTAILMENT', 2: 'NEUTRAL'}
    for label, count in label_counts.items():
        pct = (count / len(output_df)) * 100
        print(f"    {label} ({label_names.get(label, 'UNKNOWN')}): {count:,} ({pct:.1f}%)")

    print(f"\n✓ Ready for HuggingFace training!")
    print(f"  Columns: {list(output_df.columns)}")


def main():
    parser = argparse.ArgumentParser(description='Create golden dataset for DeBERTa fine-tuning')
    parser.add_argument('--sample-size', type=int, default=500,
                        help='Number of claims to sample and label (default: 500)')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed for sampling (default: 42)')
    parser.add_argument('--yes', '-y', action='store_true',
                        help='Skip confirmation prompt')
    args = parser.parse_args()

    create_golden_dataset(sample_size=args.sample_size, random_seed=args.seed, skip_confirm=args.yes)


if __name__ == "__main__":
    main()
