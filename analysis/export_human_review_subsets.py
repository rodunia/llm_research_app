#!/usr/bin/env python3
"""
Export Human Review Subsets from GPT-4o Audit Results

Creates two CSVs for manual validation:
1. ALL HIGH/CRITICAL violations
2. Random sample of 100 other materials (compliant + LOW/MEDIUM)
"""

import csv
import json
import random
import argparse
from pathlib import Path
from typing import List, Dict

# Paths
RESULTS_DIR = Path(__file__).parent.parent / "results"
CHECKPOINT_FILE = RESULTS_DIR / "gpt4o_audit_checkpoint.jsonl"
HIGH_CRITICAL_CSV = RESULTS_DIR / "high_critical_review.csv"
RANDOM_SAMPLE_CSV = RESULTS_DIR / "random_sample_review.csv"


def load_audit_results() -> List[Dict]:
    """Load all audit results from checkpoint file."""
    if not CHECKPOINT_FILE.exists():
        raise FileNotFoundError(
            f"Audit checkpoint not found: {CHECKPOINT_FILE}\n"
            "Run 'python analysis/gpt4o_direct_audit.py' first"
        )

    results = []
    with open(CHECKPOINT_FILE) as f:
        for line in f:
            results.append(json.loads(line))

    return results


def flatten_violations(results: List[Dict]) -> List[Dict]:
    """
    Flatten audit results to one row per violation.
    Includes full material text in each row.
    """
    rows = []

    for result in results:
        run_id = result['run_id']
        product_id = result['product_id']
        engine = result.get('engine', 'unknown')
        temperature = result.get('temperature', 'unknown')
        material_type = result.get('material_type', 'unknown')
        time_of_day = result.get('time_of_day_label', 'unknown')
        compliant = result.get('compliant', None)
        violation_count = result.get('violation_count', 0)
        overall_severity = result.get('overall_severity', 'NONE')
        material_text = result.get('material_text', '')
        summary = result.get('summary', '')

        violations = result.get('violations', [])

        if not violations:
            # Compliant material - still include for random sampling
            rows.append({
                'run_id': run_id,
                'product_id': product_id,
                'engine': engine,
                'temperature': temperature,
                'material_type': material_type,
                'time_of_day': time_of_day,
                'compliant': compliant,
                'violation_count': 0,
                'overall_severity': overall_severity,
                'gpt4o_summary': summary,
                'claim_text': '',
                'violation_type': '',
                'severity': 'NONE',
                'rule_violated': '',
                'reasoning': '',
                'suggested_fix': '',
                'material_text': material_text,
                'human_verdict': '',  # For manual review
                'human_notes': ''      # For manual review
            })
        else:
            # Include each violation as a separate row
            for v in violations:
                rows.append({
                    'run_id': run_id,
                    'product_id': product_id,
                    'engine': engine,
                    'temperature': temperature,
                    'material_type': material_type,
                    'time_of_day': time_of_day,
                    'compliant': compliant,
                    'violation_count': violation_count,
                    'overall_severity': overall_severity,
                    'gpt4o_summary': summary,
                    'claim_text': v.get('claim_text', ''),
                    'violation_type': v.get('violation_type', ''),
                    'severity': v.get('severity', ''),
                    'rule_violated': v.get('rule_violated', ''),
                    'reasoning': v.get('reasoning', ''),
                    'suggested_fix': v.get('suggested_fix', ''),
                    'material_text': material_text,
                    'human_verdict': '',  # AGREE / DISAGREE / UNSURE
                    'human_notes': ''      # Free text notes
                })

    return rows


def export_high_critical(all_rows: List[Dict]):
    """Export all HIGH and CRITICAL violations for manual review."""
    high_critical = [
        row for row in all_rows
        if row['severity'] in ['HIGH', 'CRITICAL']
    ]

    if not high_critical:
        print("⚠ No HIGH or CRITICAL violations found")
        return

    # Write to CSV
    with open(HIGH_CRITICAL_CSV, 'w', newline='', encoding='utf-8') as f:
        fieldnames = high_critical[0].keys()
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(high_critical)

    print(f"✓ Exported {len(high_critical)} HIGH/CRITICAL violations to:")
    print(f"  {HIGH_CRITICAL_CSV}")

    # Breakdown by severity
    critical = sum(1 for r in high_critical if r['severity'] == 'CRITICAL')
    high = sum(1 for r in high_critical if r['severity'] == 'HIGH')
    print(f"    CRITICAL: {critical}")
    print(f"    HIGH: {high}")


def export_random_sample(all_rows: List[Dict], sample_size: int = 100, seed: int = 42):
    """
    Export random sample of non-HIGH/CRITICAL materials.
    Stratified by compliant vs non-compliant.
    """
    # Exclude HIGH/CRITICAL
    other_materials = [
        row for row in all_rows
        if row['severity'] not in ['HIGH', 'CRITICAL']
    ]

    # Group by run_id (deduplicate - one row per material)
    materials_by_run = {}
    for row in other_materials:
        run_id = row['run_id']
        if run_id not in materials_by_run:
            materials_by_run[run_id] = row

    materials = list(materials_by_run.values())

    # Stratify by compliant vs non-compliant
    compliant = [m for m in materials if m['compliant'] is True]
    non_compliant = [m for m in materials if m['compliant'] is False]

    print(f"\nAvailable for random sampling:")
    print(f"  Compliant: {len(compliant)}")
    print(f"  Non-compliant (LOW/MEDIUM): {len(non_compliant)}")

    # Sample proportionally (aim for 50/50 split if possible)
    random.seed(seed)

    if len(materials) < sample_size:
        print(f"⚠ Requested sample size ({sample_size}) exceeds available materials ({len(materials)})")
        sample_size = len(materials)

    # Target: 50 compliant, 50 non-compliant (adjust if not enough)
    target_compliant = min(sample_size // 2, len(compliant))
    target_non_compliant = min(sample_size - target_compliant, len(non_compliant))

    # Adjust if non-compliant is insufficient
    if target_non_compliant < sample_size // 2:
        target_compliant = min(sample_size - target_non_compliant, len(compliant))

    sample_compliant = random.sample(compliant, target_compliant)
    sample_non_compliant = random.sample(non_compliant, target_non_compliant)

    sample = sample_compliant + sample_non_compliant
    random.shuffle(sample)  # Randomize order

    # Write to CSV
    with open(RANDOM_SAMPLE_CSV, 'w', newline='', encoding='utf-8') as f:
        fieldnames = sample[0].keys()
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sample)

    print(f"\n✓ Exported random sample of {len(sample)} materials to:")
    print(f"  {RANDOM_SAMPLE_CSV}")
    print(f"    Compliant: {len(sample_compliant)}")
    print(f"    Non-compliant: {len(sample_non_compliant)}")
    print(f"    Seed: {seed} (for reproducibility)")


def main():
    parser = argparse.ArgumentParser(
        description='Export human review subsets from GPT-4o audit results'
    )
    parser.add_argument(
        '--sample-size',
        type=int,
        default=100,
        help='Random sample size (default: 100)'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed for reproducibility (default: 42)'
    )
    args = parser.parse_args()

    print("=" * 80)
    print("EXPORTING HUMAN REVIEW SUBSETS")
    print("=" * 80)
    print()

    # Load audit results
    print("Loading GPT-4o audit results...")
    results = load_audit_results()
    print(f"✓ Loaded {len(results)} audit results")

    # Flatten to rows
    all_rows = flatten_violations(results)
    print(f"✓ Flattened to {len(all_rows)} rows")
    print()

    # Export HIGH/CRITICAL subset
    print("=" * 80)
    print("SUBSET A: HIGH/CRITICAL VIOLATIONS")
    print("=" * 80)
    export_high_critical(all_rows)

    # Export random sample
    print()
    print("=" * 80)
    print("SUBSET B: RANDOM SAMPLE")
    print("=" * 80)
    export_random_sample(all_rows, sample_size=args.sample_size, seed=args.seed)

    print()
    print("=" * 80)
    print("✓ EXPORT COMPLETE")
    print("=" * 80)
    print()
    print("Next steps:")
    print("1. Open CSVs in Excel/Google Sheets")
    print("2. Review 'material_text' column")
    print("3. Fill 'human_verdict' column: AGREE / DISAGREE / UNSURE")
    print("4. Add notes to 'human_notes' column")
    print("5. Calculate inter-rater reliability (GPT-4o vs human)")


if __name__ == "__main__":
    main()
