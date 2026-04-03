"""
Filter 258 Glass Box violations through GPT-4o grey area judge.
Identifies TRUE violations vs NLI false positives.
"""

import csv
import json
import sys
import os
from pathlib import Path
from collections import defaultdict, Counter
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.gpt4o_grey_area_judge import judge_claim_grey_area

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
RESULTS_CSV = PROJECT_ROOT / "results" / "final_audit_results.csv"
EXPERIMENTS_CSV = PROJECT_ROOT / "results" / "experiments.csv"
OUTPUT_JSON = PROJECT_ROOT / "results" / "gpt4o_filtered_violations.json"
OUTPUT_CSV = PROJECT_ROOT / "results" / "gpt4o_filtered_violations.csv"

def load_experiments_metadata():
    """Load run metadata from experiments.csv."""
    metadata = {}
    with open(EXPERIMENTS_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            run_id = row['run_id']
            metadata[run_id] = {
                'product_id': row['product_id'],
                'material_type': row['material_type'].replace('.j2', ''),
                'engine': row['engine'],
                'temperature': float(row['temperature'])
            }
    return metadata

def load_violations():
    """Load all violations from Glass Box audit."""
    violations = []
    with open(RESULTS_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Status'] == 'FAIL':
                violations.append({
                    'filename': row['Filename'].replace('.txt', ''),
                    'violated_rule': row['Violated_Rule'],
                    'claim': row['Extracted_Claim'],
                    'confidence': float(row['Confidence_Score'])
                })
    return violations

def filter_violations_with_gpt4o(violations, metadata, limit=None):
    """
    Filter violations through GPT-4o judge.

    Args:
        violations: List of violation dicts from Glass Box
        metadata: Run metadata dict
        limit: Optional limit for testing (e.g., 20)

    Returns:
        List of filtered violations with GPT-4o verdicts
    """
    results = []

    total = len(violations) if limit is None else min(limit, len(violations))

    print(f"\n{'='*80}")
    print(f"FILTERING {total} VIOLATIONS THROUGH GPT-4O JUDGE")
    print(f"{'='*80}\n")

    for i, violation in enumerate(violations[:total], 1):
        run_id = violation['filename']
        claim = violation['claim']

        # Get product_id from metadata
        if run_id not in metadata:
            print(f"WARNING: {run_id} not in metadata, skipping")
            continue

        product_id = metadata[run_id]['product_id']

        print(f"[{i}/{total}] Analyzing claim from {product_id}...")
        print(f"  Claim: {claim[:80]}...")

        # Call GPT-4o judge
        gpt4o_result = judge_claim_grey_area(claim, product_id)

        # Combine with original violation data
        combined = {
            **violation,
            'product_id': product_id,
            'engine': metadata[run_id]['engine'],
            'material_type': metadata[run_id]['material_type'],
            'gpt4o_verdict': gpt4o_result.get('verdict'),
            'gpt4o_severity': gpt4o_result.get('severity'),
            'gpt4o_reasoning': gpt4o_result.get('reasoning'),
            'gpt4o_confidence': gpt4o_result.get('confidence'),
            'gpt4o_violation_type': gpt4o_result.get('violation_type'),
            'gpt4o_recommended_fix': gpt4o_result.get('recommended_fix'),
        }

        results.append(combined)

        # Log verdict
        verdict = gpt4o_result.get('verdict', 'UNKNOWN')
        severity = gpt4o_result.get('severity', 'UNKNOWN')
        print(f"  → {verdict} (severity: {severity})\n")

    return results

def save_results(results):
    """Save filtered results to JSON and CSV."""

    # Save JSON (full data)
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"✅ Saved full results to: {OUTPUT_JSON}")

    # Save CSV (flattened)
    with open(OUTPUT_CSV, 'w', newline='') as f:
        if results:
            fieldnames = list(results[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

    print(f"✅ Saved CSV results to: {OUTPUT_CSV}")

def analyze_filtered_results(results):
    """Analyze and summarize GPT-4o filtered results."""

    print(f"\n{'='*80}")
    print(f"GPT-4O FILTERING RESULTS")
    print(f"{'='*80}\n")

    total = len(results)
    verdicts = Counter(r['gpt4o_verdict'] for r in results)
    severities = Counter(r['gpt4o_severity'] for r in results)

    print(f"### Overall Summary")
    print(f"Total violations analyzed: {total}")
    print(f"\n### By Verdict")
    print(f"{'Verdict':<20} {'Count':<10} {'Percentage'}")
    print("-" * 50)
    for verdict, count in verdicts.most_common():
        pct = count / total * 100
        print(f"{verdict:<20} {count:<10} {pct:>5.1f}%")

    print(f"\n### By Severity")
    print(f"{'Severity':<20} {'Count':<10} {'Percentage'}")
    print("-" * 50)
    for severity, count in severities.most_common():
        pct = count / total * 100
        print(f"{severity:<20} {count:<10} {pct:>5.1f}%")

    # True violations (HIGH or CRITICAL severity)
    true_violations = [r for r in results if r['gpt4o_severity'] in ['HIGH', 'CRITICAL']]
    print(f"\n### True Violations (HIGH or CRITICAL severity)")
    print(f"Count: {len(true_violations)} ({len(true_violations)/total*100:.1f}%)")

    if true_violations:
        print(f"\nSample True Violations:")
        for i, v in enumerate(true_violations[:5], 1):
            print(f"\n{i}. {v['claim'][:80]}...")
            print(f"   Verdict: {v['gpt4o_verdict']} | Severity: {v['gpt4o_severity']}")
            print(f"   Reasoning: {v['gpt4o_reasoning'][:120]}...")

    # False positives (COMPLIANT verdict)
    false_positives = [r for r in results if r['gpt4o_verdict'] == 'COMPLIANT']
    print(f"\n### False Positives (NLI errors)")
    print(f"Count: {len(false_positives)} ({len(false_positives)/total*100:.1f}%)")

    # Grey area (needs human review)
    grey_area = [r for r in results if r['gpt4o_verdict'] == 'GREY_AREA']
    print(f"\n### Grey Area (Needs Human Review)")
    print(f"Count: {len(grey_area)} ({len(grey_area)/total*100:.1f}%)")

    # By product
    print(f"\n### By Product")
    by_product = defaultdict(lambda: {'total': 0, 'violations': 0, 'false_positives': 0})
    for r in results:
        product = r['product_id']
        by_product[product]['total'] += 1
        if r['gpt4o_verdict'] == 'VIOLATION':
            by_product[product]['violations'] += 1
        if r['gpt4o_verdict'] == 'COMPLIANT':
            by_product[product]['false_positives'] += 1

    print(f"{'Product':<30} {'Total':<8} {'Violations':<12} {'False Positives'}")
    print("-" * 70)
    for product, stats in sorted(by_product.items()):
        print(f"{product:<30} {stats['total']:<8} {stats['violations']:<12} {stats['false_positives']}")

    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Filter Glass Box violations through GPT-4o')
    parser.add_argument('--limit', type=int, default=None, help='Limit number of violations to process (for testing)')
    args = parser.parse_args()

    # Load data
    metadata = load_experiments_metadata()
    violations = load_violations()

    print(f"Loaded {len(violations)} violations from Glass Box audit")

    # Filter through GPT-4o
    results = filter_violations_with_gpt4o(violations, metadata, limit=args.limit)

    # Save results
    save_results(results)

    # Analyze
    analyze_filtered_results(results)

    print(f"✅ GPT-4o filtering complete!")
