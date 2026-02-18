#!/usr/bin/env python3
"""Analyze how Glass Box Audit detected CoreCoin intentional mistakes."""

import csv
import json
from pathlib import Path
from collections import defaultdict

# Result files
AUDIT_CSV = Path("results/final_audit_results.csv")
OUTPUT_DIR = Path("docs/corecoin_analysis")
OUTPUT_DIR.mkdir(exist_ok=True)

def load_audit_results():
    """Load Glass Box audit results."""
    results = defaultdict(list)

    with open(AUDIT_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            filename = row['Filename']
            if 'corecoin' not in filename.lower():
                continue

            # Extract run number (e.g., "1.txt" -> "user_corecoin_1")
            if filename.endswith('.txt'):
                # Could be "1.txt" or "user_corecoin_1.txt"
                base = filename.replace('.txt', '')
                if base.isdigit():
                    run_id = f"user_corecoin_{base}"
                else:
                    run_id = base
            else:
                run_id = filename

            results[run_id].append({
                'violated_rule': row['Violated_Rule'],
                'claim': row['Extracted_Claim'],
                'confidence': float(row['Confidence_Score'])
            })

    return results

def analyze_file(run_id, violations):
    """Analyze a single CoreCoin file."""
    print(f"\n{'='*80}")
    print(f"File: {run_id}")
    print(f"{'='*80}")
    print(f"Total violations: {len(violations)}\n")

    # Group by violated rule
    by_rule = defaultdict(list)
    for v in violations:
        by_rule[v['violated_rule']].append(v)

    print("Violations by rule:")
    for rule, vlist in sorted(by_rule.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"\n  [{len(vlist)}] {rule}")
        for v in vlist[:3]:  # Show first 3 claims
            print(f"      - {v['claim'][:80]}... ({v['confidence']:.2%})")
        if len(vlist) > 3:
            print(f"      ... and {len(vlist)-3} more")

    return len(violations), by_rule

def main():
    results = load_audit_results()

    if not results:
        print("No CoreCoin audit results found. Run Glass Box Audit on user_corecoin_* files first.")
        return

    print("\n" + "="*80)
    print("CORECOIN DETECTION ANALYSIS")
    print("="*80)

    total_violations = 0
    all_rules = defaultdict(int)

    for run_id in sorted(results.keys()):
        violations = results[run_id]
        count, by_rule = analyze_file(run_id, violations)
        total_violations += count

        for rule in by_rule.keys():
            all_rules[rule] += len(by_rule[rule])

    print(f"\n\n{'='*80}")
    print("OVERALL SUMMARY")
    print(f"{'='*80}")
    print(f"Total files analyzed: {len(results)}")
    print(f"Total violations: {total_violations}")
    print(f"Average violations per file: {total_violations / len(results):.1f}")

    print(f"\n\nMost frequently violated rules:")
    for rule, count in sorted(all_rules.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  [{count:3d}] {rule[:70]}")

    # Save detailed results
    output_file = OUTPUT_DIR / "detection_summary.json"
    with open(output_file, 'w') as f:
        json.dump({
            'total_files': len(results),
            'total_violations': total_violations,
            'avg_per_file': total_violations / len(results),
            'by_file': {k: len(v) for k, v in results.items()},
            'rule_frequency': dict(all_rules)
        }, f, indent=2)

    print(f"\n\nDetailed results saved to: {output_file}")

if __name__ == '__main__':
    main()
