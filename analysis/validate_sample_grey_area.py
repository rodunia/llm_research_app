#!/usr/bin/env python3
"""
Sample Grey Area Validation
Validates a random sample of NLI violations using GPT-4o judge to estimate false positive rate.
"""

import csv
import json
import random
import argparse
from pathlib import Path
from typing import List, Dict
from gpt4o_grey_area_judge import judge_claim_grey_area

# Paths
RESULTS_DIR = Path(__file__).parent.parent / "results"
AUDIT_RESULTS_PATH = RESULTS_DIR / "final_audit_results.csv"
SAMPLE_OUTPUT_PATH = RESULTS_DIR / "grey_area_sample_validation.jsonl"
SUMMARY_OUTPUT_PATH = RESULTS_DIR / "grey_area_sample_summary.txt"


def load_audit_results() -> List[Dict]:
    """Load all violations from glass box audit."""
    if not AUDIT_RESULTS_PATH.exists():
        raise FileNotFoundError(f"Audit results not found: {AUDIT_RESULTS_PATH}")

    with open(AUDIT_RESULTS_PATH) as f:
        reader = csv.DictReader(f)
        return list(reader)


def validate_sample(sample_size: int = 100, seed: int = 42) -> List[Dict]:
    """
    Validate a random sample of violations using GPT-4o judge.

    Args:
        sample_size: Number of violations to validate
        seed: Random seed for reproducibility

    Returns:
        List of validation results with verdicts
    """
    print("=" * 80)
    print(f"GREY AREA VALIDATION - SAMPLE SIZE: {sample_size}")
    print("=" * 80)

    # Load audit results
    print(f"\nLoading audit results from {AUDIT_RESULTS_PATH}...")
    audit_results = load_audit_results()
    print(f"✓ Loaded {len(audit_results)} violations")

    # Random sample
    random.seed(seed)
    if sample_size > len(audit_results):
        print(f"⚠ Sample size ({sample_size}) larger than available violations ({len(audit_results)})")
        sample_size = len(audit_results)

    sample = random.sample(audit_results, sample_size)
    print(f"✓ Selected random sample of {sample_size} violations (seed={seed})")
    print()

    # Validate each violation
    results = []
    for i, row in enumerate(sample, 1):
        print(f"[{i}/{sample_size}] Analyzing claim from run {row['run_id'][:12]}...")

        try:
            result = judge_claim_grey_area(
                claim=row['claim_text'],
                product_id=row['product_id']
            )

            # Merge with original audit data
            result['run_id'] = row['run_id']
            result['engine'] = row['engine']
            result['temperature'] = row['temperature']
            result['product_id'] = row['product_id']
            result['nli_contradiction_score'] = row['contradiction_score']

            results.append(result)

            # Log verdict
            verdict = result.get('verdict', 'UNKNOWN')
            severity = result.get('severity', 'UNKNOWN')
            print(f"  → {verdict} (severity: {severity})")

        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            results.append({
                'run_id': row['run_id'],
                'claim': row['claim_text'],
                'verdict': 'ERROR',
                'severity': 'NONE',
                'reasoning': str(e),
                'confidence': 0.0
            })

        print()

    return results


def analyze_results(results: List[Dict]) -> Dict:
    """Calculate summary statistics from validation results."""
    total = len(results)

    # Count by verdict
    verdicts = [r.get('verdict', 'UNKNOWN') for r in results]
    compliant_count = verdicts.count('COMPLIANT')
    grey_area_count = verdicts.count('GREY_AREA')
    violation_count = verdicts.count('VIOLATION')
    error_count = verdicts.count('ERROR')

    # Count by severity (for violations only)
    violations = [r for r in results if r.get('verdict') == 'VIOLATION']
    severities = [r.get('severity', 'UNKNOWN') for r in violations]
    critical_count = severities.count('CRITICAL')
    high_count = severities.count('HIGH')
    medium_count = severities.count('MEDIUM')
    low_count = severities.count('LOW')

    return {
        'total': total,
        'compliant': compliant_count,
        'grey_area': grey_area_count,
        'violation': violation_count,
        'error': error_count,
        'false_positive_rate': compliant_count / total * 100,
        'true_positive_rate': violation_count / total * 100,
        'grey_area_rate': grey_area_count / total * 100,
        'severity_breakdown': {
            'critical': critical_count,
            'high': high_count,
            'medium': medium_count,
            'low': low_count
        }
    }


def save_results(results: List[Dict], summary: Dict):
    """Save validation results and summary to files."""
    # Save detailed results (JSONL)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    with open(SAMPLE_OUTPUT_PATH, 'w') as f:
        for result in results:
            f.write(json.dumps(result) + '\n')

    print(f"✓ Saved detailed results to {SAMPLE_OUTPUT_PATH}")

    # Save summary (text)
    with open(SUMMARY_OUTPUT_PATH, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("GREY AREA VALIDATION - SAMPLE SUMMARY\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"Total violations analyzed: {summary['total']}\n\n")

        f.write("VERDICT BREAKDOWN:\n")
        f.write(f"  COMPLIANT (false positive): {summary['compliant']} ({summary['false_positive_rate']:.1f}%)\n")
        f.write(f"  GREY_AREA (needs review):   {summary['grey_area']} ({summary['grey_area_rate']:.1f}%)\n")
        f.write(f"  VIOLATION (true positive):  {summary['violation']} ({summary['true_positive_rate']:.1f}%)\n")
        f.write(f"  ERROR:                      {summary['error']}\n\n")

        if summary['violation'] > 0:
            f.write("SEVERITY BREAKDOWN (violations only):\n")
            f.write(f"  CRITICAL: {summary['severity_breakdown']['critical']}\n")
            f.write(f"  HIGH:     {summary['severity_breakdown']['high']}\n")
            f.write(f"  MEDIUM:   {summary['severity_breakdown']['medium']}\n")
            f.write(f"  LOW:      {summary['severity_breakdown']['low']}\n\n")

        # Extrapolation
        f.write("EXTRAPOLATION TO FULL DATASET:\n")
        f.write(f"  If false positive rate holds ({summary['false_positive_rate']:.1f}%):\n")

        # Load total violations for extrapolation
        try:
            with open(AUDIT_RESULTS_PATH) as csv_f:
                total_violations = sum(1 for _ in csv_f) - 1  # Subtract header

            estimated_true_violations = int(total_violations * summary['true_positive_rate'] / 100)
            estimated_false_positives = int(total_violations * summary['false_positive_rate'] / 100)

            f.write(f"    Total NLI violations:      {total_violations}\n")
            f.write(f"    Estimated true violations: {estimated_true_violations}\n")
            f.write(f"    Estimated false positives: {estimated_false_positives}\n")
        except Exception as e:
            f.write(f"    (Unable to calculate: {e})\n")

    print(f"✓ Saved summary to {SUMMARY_OUTPUT_PATH}")


def print_summary(summary: Dict):
    """Print summary statistics to console."""
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print()
    print(f"Total violations analyzed: {summary['total']}")
    print()
    print("VERDICT BREAKDOWN:")
    print(f"  COMPLIANT (false positive): {summary['compliant']:>3} ({summary['false_positive_rate']:>5.1f}%)")
    print(f"  GREY_AREA (needs review):   {summary['grey_area']:>3} ({summary['grey_area_rate']:>5.1f}%)")
    print(f"  VIOLATION (true positive):  {summary['violation']:>3} ({summary['true_positive_rate']:>5.1f}%)")
    print(f"  ERROR:                      {summary['error']:>3}")
    print()

    if summary['violation'] > 0:
        print("SEVERITY BREAKDOWN (violations only):")
        print(f"  CRITICAL: {summary['severity_breakdown']['critical']:>3}")
        print(f"  HIGH:     {summary['severity_breakdown']['high']:>3}")
        print(f"  MEDIUM:   {summary['severity_breakdown']['medium']:>3}")
        print(f"  LOW:      {summary['severity_breakdown']['low']:>3}")
        print()

    print("=" * 80)
    print()
    print("INTERPRETATION:")
    if summary['false_positive_rate'] < 10:
        print("  ✓ LOW false positive rate - NLI results are highly reliable")
        print("  → Recommendation: Use NLI results directly for analysis")
    elif summary['false_positive_rate'] < 30:
        print("  ⚠ MODERATE false positive rate - Some NLI violations are not genuine")
        print("  → Recommendation: Consider filtering by NLI confidence threshold (>0.8)")
    else:
        print("  ✗ HIGH false positive rate - Many NLI violations are false alarms")
        print("  → Recommendation: Run full grey area validation on all violations")
    print()


def main():
    parser = argparse.ArgumentParser(description='Validate NLI violations using GPT-4o grey area judge')
    parser.add_argument('--sample-size', type=int, default=100, help='Number of violations to validate (default: 100)')
    parser.add_argument('--seed', type=int, default=42, help='Random seed for reproducibility (default: 42)')
    args = parser.parse_args()

    # Validate sample
    results = validate_sample(sample_size=args.sample_size, seed=args.seed)

    # Analyze results
    summary = analyze_results(results)

    # Save results
    save_results(results, summary)

    # Print summary
    print_summary(summary)

    print(f"Cost estimate: ~${args.sample_size * 0.0025:.2f} (GPT-4o API calls)")
    print()


if __name__ == "__main__":
    main()
