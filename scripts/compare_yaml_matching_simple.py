#!/usr/bin/env python3
"""
Simple comparison of OLD vs NEW YAML matching using direct string comparison.
"""

import sys
from pathlib import Path
import yaml
import pandas as pd
import re

project_root = Path(__file__).parent.parent


def normalize_text(text):
    """Normalize text for comparison."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    return text


def simple_match(claim, yaml_claims_list):
    """Simple match: exact or partial containment."""
    norm_claim = normalize_text(claim)

    for yaml_claim in yaml_claims_list:
        norm_yaml = normalize_text(yaml_claim)

        # Exact match
        if norm_claim == norm_yaml:
            return 'exact'

        # Partial match (containment)
        if norm_claim in norm_yaml or norm_yaml in norm_claim:
            shorter = min(len(norm_claim), len(norm_yaml))
            longer = max(len(norm_claim), len(norm_yaml))
            if shorter / longer > 0.6:  # At least 60% overlap
                return 'partial'

    return 'none'


def load_yaml_claims(yaml_path):
    """Load claims from YAML - handle both old dict format and new list format."""
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)

    claims_list = []
    if 'authorized_claims' in data:
        for category, claim_items in data['authorized_claims'].items():
            if isinstance(claim_items, list):
                for item in claim_items:
                    if isinstance(item, dict) and 'text' in item:
                        claims_list.append(item['text'])
                    elif isinstance(item, str):
                        claims_list.append(item)

    return claims_list


def main():
    yaml_dir = project_root / "products"
    merged_csv = project_root / "results" / "all_claims_review.csv"

    # Load YAMLs
    products = ['smartphone_mid', 'supplement_melatonin', 'cryptocurrency_corecoin']
    old_yamls = {}
    new_yamls = {}

    for product in products:
        old_yamls[product] = load_yaml_claims(yaml_dir / f"{product}.yaml.backup")
        new_yamls[product] = load_yaml_claims(yaml_dir / f"{product}.yaml")

    print("=" * 80)
    print("YAML EXPANSION SUMMARY")
    print("=" * 80)
    for product in products:
        old_count = len(old_yamls[product])
        new_count = len(new_yamls[product])
        expansion = new_count / old_count if old_count > 0 else 0
        print(f"{product:30s}: {old_count:3d} → {new_count:3d} ({expansion:.1f}x)")

    # Load claims
    df = pd.read_csv(merged_csv)
    df = df[df['extracted_claim'].notna()]
    df = df[df['extracted_claim'].str.strip() != '']

    # Sample claims
    sample_size = 100
    sample_claims = []
    for product in products:
        product_df = df[df['product_id'] == product]
        for _, row in product_df.head(sample_size // 3).iterrows():
            sample_claims.append({
                'product': row['product_id'],
                'claim': row['extracted_claim'],
                'old_match': row['match_type']
            })

    print(f"\n✅ Sampled {len(sample_claims)} claims\n")

    # Test matching
    old_results = {'exact': 0, 'partial': 0, 'none': 0}
    new_results = {'exact': 0, 'partial': 0, 'none': 0}
    improvements = []

    for item in sample_claims:
        product = item['product']
        claim = item['claim']
        old_match_csv = item['old_match']

        # Test with NEW YAML
        new_match = simple_match(claim, new_yamls[product])

        # Count
        if old_match_csv in old_results:
            old_results[old_match_csv] += 1
        if new_match in new_results:
            new_results[new_match] += 1

        # Track improvements
        match_quality = {'exact': 3, 'partial': 2, 'none': 1}
        if match_quality.get(new_match, 0) > match_quality.get(old_match_csv, 0):
            improvements.append({
                'product': product,
                'claim': claim[:70] + '...' if len(claim) > 70 else claim,
                'old': old_match_csv,
                'new': new_match
            })

    # Report
    print("=" * 80)
    print("MATCHING COMPARISON")
    print("=" * 80)

    total_old = sum(old_results.values())
    total_new = sum(new_results.values())

    print(f"\nOLD YAML (Pre-Expansion) - {total_old} claims:")
    for match_type in ['exact', 'partial', 'none']:
        count = old_results[match_type]
        pct = (count / total_old * 100) if total_old > 0 else 0
        print(f"  {match_type.upper():8s}: {count:3d} ({pct:5.1f}%)")

    print(f"\nNEW YAML (Post-Expansion) - {total_new} claims:")
    for match_type in ['exact', 'partial', 'none']:
        count = new_results[match_type]
        pct = (count / total_new * 100) if total_new > 0 else 0
        print(f"  {match_type.upper():8s}: {count:3d} ({pct:5.1f}%)")

    print("\n" + "=" * 80)
    print("IMPROVEMENT METRICS")
    print("=" * 80)

    old_match_rate = (old_results['exact'] + old_results['partial']) / total_old * 100
    new_match_rate = (new_results['exact'] + new_results['partial']) / total_new * 100
    improvement = new_match_rate - old_match_rate

    print(f"\nOLD Match Rate (exact+partial): {old_match_rate:.1f}%")
    print(f"NEW Match Rate (exact+partial): {new_match_rate:.1f}%")
    print(f"Absolute Improvement: {improvement:+.1f} percentage points")

    if old_match_rate > 0:
        relative = (new_match_rate / old_match_rate - 1) * 100
        print(f"Relative Improvement: {relative:+.1f}%")

    print(f"\n✨ {len(improvements)} claims upgraded")

    if improvements:
        print(f"\nSample improvements (first 10):")
        for i, imp in enumerate(improvements[:10], 1):
            print(f"\n  {i}. [{imp['product']}]")
            print(f"     {imp['claim']}")
            print(f"     {imp['old']} → {imp['new']}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
