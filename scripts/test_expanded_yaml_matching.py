#!/usr/bin/env python3
"""
Test claim matching improvements after YAML paraphrase expansion.

Compares OLD matching (using .backup YAMLs) vs NEW matching (using expanded YAMLs)
on a sample of existing extracted claims to measure improvement.
"""

import sys
from pathlib import Path
import yaml
import pandas as pd
from typing import Dict, List
import re

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from runner.extract_claims import normalize_text, find_yaml_match


def load_yaml_claims(yaml_path: Path) -> List[str]:
    """Load authorized claims from a YAML file."""
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)

    claims = []
    if 'authorized_claims' in data:
        for category, claim_list in data['authorized_claims'].items():
            if isinstance(claim_list, list):
                claims.extend(claim_list)

    return claims


def test_matching(claim_text: str, yaml_claims: List[str]) -> Dict:
    """Test claim matching against a set of YAML claims."""
    match_type = find_yaml_match(normalize_text(claim_text), yaml_claims)
    return {
        'claim': claim_text,
        'match_type': match_type
    }


def analyze_sample(sample_size: int = 100):
    """Analyze a sample of existing claim files to compare OLD vs NEW matching."""

    outputs_dir = project_root / "outputs"
    claim_files = sorted(outputs_dir.glob("*_claims_review.csv"))

    if not claim_files:
        print("❌ No claim files found in outputs/")
        return

    print(f"📊 Found {len(claim_files)} claim files")
    print(f"🔍 Analyzing first {sample_size} claims...")

    # Load OLD YAMLs (backups)
    yaml_dir = project_root / "products"
    old_yamls = {
        'smartphone_mid': load_yaml_claims(yaml_dir / "smartphone_mid.yaml.backup"),
        'supplement_melatonin': load_yaml_claims(yaml_dir / "supplement_melatonin.yaml.backup"),
        'cryptocurrency_corecoin': load_yaml_claims(yaml_dir / "cryptocurrency_corecoin.yaml.backup")
    }

    # Load NEW YAMLs (expanded)
    new_yamls = {
        'smartphone_mid': load_yaml_claims(yaml_dir / "smartphone_mid.yaml"),
        'supplement_melatonin': load_yaml_claims(yaml_dir / "supplement_melatonin.yaml"),
        'cryptocurrency_corecoin': load_yaml_claims(yaml_dir / "cryptocurrency_corecoin.yaml")
    }

    print(f"\n📋 YAML Stats:")
    for product in old_yamls.keys():
        print(f"  {product}: {len(old_yamls[product])} → {len(new_yamls[product])} claims "
              f"({len(new_yamls[product]) / len(old_yamls[product]):.1f}x expansion)")

    # Use merged claims CSV if it exists
    merged_csv = project_root / "results" / "all_claims_review.csv"
    if merged_csv.exists():
        print(f"✅ Using merged claims file: {merged_csv.name}")
        df = pd.read_csv(merged_csv)

        # Filter out empty claims
        df = df[df['extracted_claim'].notna()]
        df = df[df['extracted_claim'].str.strip() != '']

        # Sample evenly across products
        sample_claims = []
        for product_id in old_yamls.keys():
            product_df = df[df['product_id'] == product_id]
            sample_count = min(len(product_df), sample_size // 3)

            for _, row in product_df.head(sample_count).iterrows():
                sample_claims.append({
                    'product_id': row['product_id'],
                    'claim': row['extracted_claim'],
                    'old_match': row['match_type']
                })

        print(f"✅ Sampled {len(sample_claims)} claims from merged CSV")
    else:
        # Fallback to individual files
        print("⚠️  Merged CSV not found, using individual files...")
        sample_claims = []
        for claim_file in claim_files[:20]:  # Limit to first 20 files
            if len(sample_claims) >= sample_size:
                break

            try:
                df = pd.read_csv(claim_file)

                # Skip empty CSVs
                if df.empty or 'extracted_claim' not in df.columns:
                    continue

                # Extract product_id from CSV
                if 'product_id' in df.columns:
                    product_id = df['product_id'].iloc[0]
                else:
                    continue

                for _, row in df.iterrows():
                    if len(sample_claims) >= sample_size:
                        break

                    if pd.notna(row.get('extracted_claim')):
                        sample_claims.append({
                            'product_id': product_id,
                            'claim': row['extracted_claim'],
                            'old_match': row.get('match_type', 'none')
                        })

            except Exception as e:
                continue

    if not sample_claims:
        print("❌ No claims could be extracted from files")
        return

    print(f"\n✅ Collected {len(sample_claims)} claims for testing\n")

    # Test matching
    results = {
        'old': {'exact': 0, 'partial': 0, 'none': 0},
        'new': {'exact': 0, 'partial': 0, 'none': 0}
    }

    improvements = []

    for item in sample_claims:
        product_id = item['product_id']
        claim = item['claim']
        old_match = item['old_match']

        # Test with NEW YAML
        new_match = find_yaml_match(normalize_text(claim), new_yamls[product_id])

        # Count OLD matches (from CSV)
        if old_match in results['old']:
            results['old'][old_match] += 1

        # Count NEW matches
        if new_match in results['new']:
            results['new'][new_match] += 1

        # Track improvements
        match_quality = {'exact': 3, 'partial': 2, 'none': 1}
        if match_quality.get(new_match, 0) > match_quality.get(old_match, 0):
            improvements.append({
                'product': product_id,
                'claim': claim[:80] + '...' if len(claim) > 80 else claim,
                'old': old_match,
                'new': new_match
            })

    # Report results
    print("=" * 80)
    print("CLAIM MATCHING COMPARISON (OLD vs NEW YAMLs)")
    print("=" * 80)

    print(f"\n📊 Sample Size: {len(sample_claims)} claims\n")

    print("OLD YAML (Pre-Expansion) Matching:")
    total_old = sum(results['old'].values())
    for match_type, count in results['old'].items():
        pct = (count / total_old * 100) if total_old > 0 else 0
        print(f"  {match_type.upper():8s}: {count:3d} ({pct:5.1f}%)")

    print("\nNEW YAML (Post-Expansion) Matching:")
    total_new = sum(results['new'].values())
    for match_type, count in results['new'].items():
        pct = (count / total_new * 100) if total_new > 0 else 0
        print(f"  {match_type.upper():8s}: {count:3d} ({pct:5.1f}%)")

    print("\n📈 IMPROVEMENT METRICS:")
    old_match_rate = (results['old']['exact'] + results['old']['partial']) / total_old * 100
    new_match_rate = (results['new']['exact'] + results['new']['partial']) / total_new * 100
    improvement = new_match_rate - old_match_rate

    print(f"  OLD Match Rate (exact+partial): {old_match_rate:.1f}%")
    print(f"  NEW Match Rate (exact+partial): {new_match_rate:.1f}%")
    print(f"  Absolute Improvement: {improvement:+.1f} percentage points")

    if old_match_rate > 0:
        relative_improvement = (new_match_rate / old_match_rate - 1) * 100
        print(f"  Relative Improvement: {relative_improvement:+.1f}%")

    # Show sample improvements
    if improvements:
        print(f"\n✨ SAMPLE IMPROVEMENTS ({len(improvements)} claims upgraded):")
        for i, imp in enumerate(improvements[:10], 1):
            print(f"\n  {i}. [{imp['product']}]")
            print(f"     Claim: {imp['claim']}")
            print(f"     {imp['old']} → {imp['new']}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    analyze_sample(sample_size=100)
