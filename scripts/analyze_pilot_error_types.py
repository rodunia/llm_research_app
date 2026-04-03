"""
Analyze pilot study results: error counts, types, and patterns.
Compares detected violations against ground truth errors.
"""

import csv
import json
from pathlib import Path
from collections import defaultdict, Counter
import re

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
PILOT_RUN1 = PROJECT_ROOT / "results" / "pilot_individual_2026_run1"
PILOT_RUN2 = PROJECT_ROOT / "results" / "pilot_individual_2026_run2"
GROUND_TRUTH_MD = PROJECT_ROOT / "GROUND_TRUTH_ERRORS.md"

# Ground truth structure (from GROUND_TRUTH_ERRORS.md)
GROUND_TRUTH = {
    'smartphone': {
        1: {'error': 'Display size', 'type': 'Numerical', 'incorrect': '6.5"', 'correct': '6.3"'},
        2: {'error': 'Main camera', 'type': 'Numerical', 'incorrect': '48 MP', 'correct': '50 MP'},
        3: {'error': 'Storage options', 'type': 'Feature hallucination', 'incorrect': '1TB option', 'correct': 'Max 512 GB'},
        4: {'error': 'RAM configurations', 'type': 'Feature hallucination', 'incorrect': '16 GB option', 'correct': 'Max 12 GB'},
        5: {'error': 'Wi-Fi support', 'type': 'Feature hallucination', 'incorrect': 'Wi-Fi 7', 'correct': 'Wi-Fi 6/6E'},
        6: {'error': 'Wireless charging', 'type': 'Feature hallucination', 'incorrect': '10W Qi wireless', 'correct': 'Not supported'},
        7: {'error': 'Security feature', 'type': 'Feature hallucination', 'incorrect': 'Hourly antivirus', 'correct': 'Not mentioned'},
        8: {'error': 'AI capability', 'type': 'Feature hallucination', 'incorrect': 'Offline AI video rendering', 'correct': 'Not supported'},
        9: {'error': 'Fast charging', 'type': 'Numerical', 'incorrect': '60W USB-C', 'correct': '30-45W'},
        10: {'error': 'Storage expansion', 'type': 'Feature hallucination', 'incorrect': 'External SSD via SIM tray', 'correct': 'Not supported'},
    },
    'melatonin': {
        1: {'error': 'Dosage per tablet', 'type': 'Numerical', 'incorrect': '5 mg', 'correct': '3 mg'},
        2: {'error': 'Bottle count', 'type': 'Factual', 'incorrect': '100 tablets', 'correct': '60 tablets'},
        3: {'error': 'Vegan claim', 'type': 'Logical contradiction', 'incorrect': 'Vegan + fish-derived', 'correct': 'Vegan only'},
        4: {'error': 'Allergen claim', 'type': 'Logical contradiction', 'incorrect': '0mg gluten + wheat traces', 'correct': 'No wheat'},
        5: {'error': 'Lead limit', 'type': 'Numerical', 'incorrect': '<5 ppm', 'correct': '<0.5 mcg/serving'},
        6: {'error': 'Storage temp', 'type': 'Logical', 'incorrect': 'Exactly 0°C', 'correct': '15-30°C'},
        7: {'error': 'Dosing frequency', 'type': 'Factual', 'incorrect': 'Every 2 hours', 'correct': 'Before bed'},
        8: {'error': 'FDA approval', 'type': 'Factual', 'incorrect': 'FDA approved', 'correct': 'Not FDA approved'},
        9: {'error': 'Age restriction', 'type': 'Factual', 'incorrect': 'Avoid if over 18', 'correct': 'If under 18 consult'},
        10: {'error': 'Side effect', 'type': 'Factual', 'incorrect': 'Permanent drowsiness', 'correct': 'Temporary'},
    },
    'corecoin': {
        1: {'error': 'Block time', 'type': 'Numerical', 'incorrect': '~4 seconds', 'correct': '~5 seconds'},
        2: {'error': 'Light validators', 'type': 'Logical', 'incorrect': "Don't stake", 'correct': 'Must stake'},
        3: {'error': 'Trading pauses', 'type': 'Feature hallucination', 'incorrect': 'Regional maintenance', 'correct': '24/7 trading'},
        4: {'error': 'Key backup', 'type': 'Feature hallucination', 'incorrect': 'Automatic key-sharding', 'correct': 'Manual backup'},
        5: {'error': 'Smart contracts', 'type': 'Factual', 'incorrect': 'Gas-free execution', 'correct': 'Gas fees required'},
        6: {'error': 'Governance', 'type': 'Logical', 'incorrect': 'Auto-pass without quorum', 'correct': 'Requires quorum'},
        7: {'error': 'Cross-chain', 'type': 'Feature hallucination', 'incorrect': 'RPC simulate cross-chain', 'correct': 'Not supported'},
        8: {'error': 'Unstaking penalty', 'type': 'Factual', 'incorrect': 'Reduces historical rewards', 'correct': 'Standard rules'},
        9: {'error': 'Validator inactivity', 'type': 'Factual', 'incorrect': 'Locks governance rights', 'correct': 'Standard rules'},
        10: {'error': 'Staking tiers', 'type': 'Factual', 'incorrect': 'Region-based fixed rates', 'correct': 'Performance-based'},
    }
}


def load_pilot_csv(csv_path: Path) -> list:
    """Load violations from a pilot CSV file."""
    violations = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('Status') == 'FAIL':
                violations.append({
                    'violated_rule': row.get('Violated_Rule', ''),
                    'claim': row.get('Extracted_Claim', ''),
                    'confidence': float(row.get('Confidence_Score', 0))
                })
    return violations


def extract_product_and_number(filename: str) -> tuple:
    """
    Extract product name and error number from filename.
    Example: 'smartphone_5.csv' -> ('smartphone', 5)
    """
    match = re.match(r'([a-z]+)_(\d+)\.csv', filename)
    if match:
        return match.group(1), int(match.group(2))
    return None, None


def categorize_violation_type(violated_rule: str, claim: str) -> str:
    """
    Categorize violation into types based on content.
    """
    text = (violated_rule + " " + claim).lower()

    # Numerical patterns
    if any(pattern in text for pattern in ['gb', 'mp', 'mg', 'tablets', 'seconds', 'ppm', '°c', 'w ']):
        return 'Numerical'

    # Feature hallucination patterns
    if any(pattern in text for pattern in ['not supported', 'not mentioned', 'cannot', 'does not']):
        return 'Feature hallucination'

    # Logical contradiction patterns
    if any(pattern in text for pattern in ['contradicts', 'cannot be both', 'mutually exclusive']):
        return 'Logical contradiction'

    # Factual error patterns (default)
    return 'Factual'


def analyze_pilot_run(run_dir: Path, run_name: str) -> dict:
    """Analyze a single pilot run."""
    print(f"\n{'='*80}")
    print(f"ANALYZING: {run_name}")
    print(f"{'='*80}")

    results = {
        'run_name': run_name,
        'total_files': 0,
        'total_violations': 0,
        'by_product': defaultdict(lambda: {'files': 0, 'violations': 0, 'by_file': {}}),
        'by_error_type': Counter(),
        'ground_truth_detection': defaultdict(list),
    }

    csv_files = sorted(run_dir.glob("*.csv"))
    results['total_files'] = len(csv_files)

    for csv_path in csv_files:
        product, file_num = extract_product_and_number(csv_path.name)
        if not product:
            continue

        violations = load_pilot_csv(csv_path)
        num_violations = len(violations)

        results['total_violations'] += num_violations
        results['by_product'][product]['files'] += 1
        results['by_product'][product]['violations'] += num_violations
        results['by_product'][product]['by_file'][file_num] = num_violations

        # Categorize violation types
        for v in violations:
            vtype = categorize_violation_type(v['violated_rule'], v['claim'])
            results['by_error_type'][vtype] += 1

        # Check ground truth detection (files 1-10 should have cumulative errors)
        if 1 <= file_num <= 10:
            expected_errors = file_num  # Progressive corruption
            detected = num_violations > 0  # At least 1 violation detected
            results['ground_truth_detection'][product].append({
                'file_num': file_num,
                'expected_errors': expected_errors,
                'detected_violations': num_violations,
                'detected': detected
            })

    return results


def print_analysis_summary(results: dict):
    """Print formatted analysis summary."""
    print(f"\n## Summary: {results['run_name']}")
    print(f"Total files analyzed: {results['total_files']}")
    print(f"Total violations flagged: {results['total_violations']}")
    print(f"Average violations per file: {results['total_violations'] / results['total_files']:.1f}")

    print(f"\n### Violations by Product")
    print(f"{'Product':<15} {'Files':<8} {'Total Violations':<20} {'Avg per File':<15}")
    print("-" * 70)
    for product, data in sorted(results['by_product'].items()):
        avg = data['violations'] / data['files'] if data['files'] > 0 else 0
        print(f"{product:<15} {data['files']:<8} {data['violations']:<20} {avg:<15.1f}")

    print(f"\n### Violations by Type")
    print(f"{'Type':<30} {'Count':<10} {'Percentage'}")
    print("-" * 60)
    total = sum(results['by_error_type'].values())
    for vtype, count in results['by_error_type'].most_common():
        pct = (count / total * 100) if total > 0 else 0
        print(f"{vtype:<30} {count:<10} {pct:>5.1f}%")

    print(f"\n### Ground Truth Detection (Files 1-10 with Progressive Errors)")
    for product in sorted(results['ground_truth_detection'].keys()):
        detections = results['ground_truth_detection'][product]
        detected_count = sum(1 for d in detections if d['detected'])
        print(f"\n**{product.upper()}**: {detected_count}/10 files had violations detected")

        print(f"{'File':<8} {'Expected Errors':<18} {'Detected Violations':<22} {'Status'}")
        print("-" * 70)
        for d in sorted(detections, key=lambda x: x['file_num']):
            status = "✅" if d['detected'] else "❌"
            print(f"{d['file_num']:<8} {d['expected_errors']:<18} {d['detected_violations']:<22} {status}")


def compare_runs(run1_results: dict, run2_results: dict):
    """Compare two pilot runs."""
    print(f"\n{'='*80}")
    print(f"COMPARISON: Run 1 vs Run 2")
    print(f"{'='*80}")

    print(f"\n### Total Violations")
    print(f"Run 1: {run1_results['total_violations']}")
    print(f"Run 2: {run2_results['total_violations']}")
    diff = run2_results['total_violations'] - run1_results['total_violations']
    print(f"Difference: {diff:+d} ({diff / run1_results['total_violations'] * 100:+.1f}%)")

    print(f"\n### By Product")
    print(f"{'Product':<15} {'Run 1':<10} {'Run 2':<10} {'Difference':<15}")
    print("-" * 60)
    for product in sorted(run1_results['by_product'].keys()):
        v1 = run1_results['by_product'][product]['violations']
        v2 = run2_results['by_product'][product]['violations']
        diff = v2 - v1
        print(f"{product:<15} {v1:<10} {v2:<10} {diff:+d}")

    print(f"\n### Ground Truth Detection Consistency")
    for product in sorted(run1_results['ground_truth_detection'].keys()):
        d1 = {d['file_num']: d['detected'] for d in run1_results['ground_truth_detection'][product]}
        d2 = {d['file_num']: d['detected'] for d in run2_results['ground_truth_detection'][product]}

        consistent = sum(1 for fn in range(1, 11) if d1.get(fn) == d2.get(fn))
        print(f"{product}: {consistent}/10 files had consistent detection across runs")


if __name__ == "__main__":
    # Analyze Run 1
    run1_results = analyze_pilot_run(PILOT_RUN1, "Pilot Run 1")
    print_analysis_summary(run1_results)

    # Analyze Run 2
    run2_results = analyze_pilot_run(PILOT_RUN2, "Pilot Run 2")
    print_analysis_summary(run2_results)

    # Compare runs
    compare_runs(run1_results, run2_results)

    # Save results
    output_file = PROJECT_ROOT / "results" / "pilot_error_type_analysis.json"
    with open(output_file, 'w') as f:
        json.dump({
            'run1': run1_results,
            'run2': run2_results,
        }, f, indent=2, default=str)

    print(f"\n✅ Analysis saved to: {output_file}")
