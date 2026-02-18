"""Expand YAML authorized_claims with common paraphrases using LLM.

This script uses Gemini to generate semantically equivalent paraphrases
for each authorized claim, improving match rates in claim extraction.
"""

import argparse
import json
import os
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment
load_dotenv()

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
PRODUCTS_DIR = PROJECT_ROOT / "products"

# Gemini Configuration
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
PARAPHRASE_MODEL = "gemini-2.0-flash-001"
PARAPHRASE_TEMPERATURE = 0.3  # Some creativity, but controlled

PARAPHRASE_PROMPT = """You are a marketing paraphrase generator.

TASK: Generate 3-5 semantically equivalent paraphrases for the given authorized claim.

RULES:
1. Maintain the EXACT meaning and factual content
2. Vary sentence structure and word choice naturally
3. Keep the same level of specificity (don't add or remove details)
4. Include both formal and casual phrasing variations
5. Preserve numbers, brand names, and technical terms exactly

EXAMPLES:
Input: "Provides guaranteed OS and security updates for seven years"
Output:
- Guarantees 7 years of OS and security updates
- Delivers seven years of guaranteed OS updates
- Offers guaranteed software and security patches for 7 years
- Commits to 7 years of OS and security update support

INPUT CLAIM:
{claim}

Generate 3-5 paraphrases as a JSON list:
{{"paraphrases": ["paraphrase 1", "paraphrase 2", "paraphrase 3"]}}

Return ONLY valid JSON.
"""


def generate_paraphrases(claim: str) -> list:
    """Generate paraphrases for a single claim using Gemini."""
    prompt = PARAPHRASE_PROMPT.format(claim=claim)

    try:
        model = genai.GenerativeModel(
            model_name=PARAPHRASE_MODEL,
            generation_config={
                "temperature": PARAPHRASE_TEMPERATURE,
                "response_mime_type": "application/json"
            }
        )

        response = model.generate_content(prompt)
        result = json.loads(response.text)
        paraphrases = result.get('paraphrases', [])

        # Rate limiting
        time.sleep(0.3)

        return paraphrases

    except Exception as e:
        print(f"  ⚠️  Paraphrase generation failed: {e}")
        if "429" in str(e):
            time.sleep(5)
        return []


def expand_yaml_paraphrases(product_id: str, dry_run: bool = False):
    """Expand authorized_claims in product YAML with paraphrases."""
    yaml_path = PRODUCTS_DIR / f"{product_id}.yaml"

    if not yaml_path.exists():
        print(f"❌ Product YAML not found: {yaml_path}")
        return

    # Load current YAML
    with open(yaml_path, 'r', encoding='utf-8') as f:
        product_yaml = yaml.safe_load(f)

    authorized_claims = product_yaml.get('authorized_claims', {})

    if not isinstance(authorized_claims, dict):
        print(f"❌ authorized_claims is not a dict structure")
        return

    print(f"\n📝 Processing: {product_id}")
    print(f"   Current categories: {list(authorized_claims.keys())}")

    # Expand each category
    expanded_claims = {}
    total_original = 0
    total_added = 0

    for category, claims in authorized_claims.items():
        if not isinstance(claims, list):
            continue

        print(f"\n  Category: {category}")
        print(f"  Original claims: {len(claims)}")

        expanded = []
        for claim in claims:
            # Keep original
            expanded.append(claim)
            total_original += 1

            # Generate paraphrases
            print(f"    Generating paraphrases for: {claim[:60]}...")
            paraphrases = generate_paraphrases(claim)

            if paraphrases:
                print(f"      + {len(paraphrases)} paraphrases added")
                expanded.extend(paraphrases)
                total_added += len(paraphrases)
            else:
                print(f"      ! No paraphrases generated")

        expanded_claims[category] = expanded

    # Update YAML
    product_yaml['authorized_claims'] = expanded_claims

    # Save or preview
    if dry_run:
        print(f"\n🔍 DRY RUN - Would have saved:")
        print(f"   Original claims: {total_original}")
        print(f"   Paraphrases added: {total_added}")
        print(f"   Total claims: {total_original + total_added}")
    else:
        # Backup original
        backup_path = yaml_path.with_suffix('.yaml.backup')
        with open(backup_path, 'w', encoding='utf-8') as f:
            yaml.dump(product_yaml, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
        print(f"\n💾 Backup saved: {backup_path}")

        # Save expanded YAML
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(product_yaml, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

        print(f"\n✅ Expanded YAML saved: {yaml_path}")
        print(f"   Original claims: {total_original}")
        print(f"   Paraphrases added: {total_added}")
        print(f"   Total claims: {total_original + total_added}")


def main():
    parser = argparse.ArgumentParser(description='Expand YAML authorized_claims with paraphrases')
    parser.add_argument('--product', type=str, required=True,
                        help='Product ID (e.g., smartphone_mid, cryptocurrency_corecoin)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without saving')
    args = parser.parse_args()

    expand_yaml_paraphrases(args.product, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
