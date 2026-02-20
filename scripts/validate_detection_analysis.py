#!/usr/bin/env python3
"""
VALIDATION SCRIPT: Verify "missed" errors are actually missed.
This script MUST be run before reporting detection results to catch false negatives.
"""

import csv
from pathlib import Path
from typing import List, Tuple

GROUND_TRUTH = {
    "smartphone_4": {"error": "16 GB RAM", "full_desc": "Adds 16 GB RAM option (not available)"},
    "melatonin_5": {"error": "Lead limit", "full_desc": "Lead limit changed (decimal misplacement)"},
    "melatonin_8": {"error": "FDA approved", "full_desc": "Claims FDA approval for supplement"},
}


def verify_missed_error(file_key: str, csv_path: Path) -> Tuple[bool, List[str]]:
    """
    Manually verify if an error was truly missed by inspecting ALL violations.

    Returns:
        (truly_missed: bool, relevant_violations: List[str])
    """
    if not csv_path.exists():
        return True, ["CSV file not found"]

    error_info = GROUND_TRUTH.get(file_key)
    if not error_info:
        return True, ["Not in ground truth"]

    # Read all violations
    violations = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            claim = row.get('Extracted_Claim', '')
            rule = row.get('Violated_Rule', '')
            conf = row.get('Confidence_Score', '')
            violations.append(f"{claim} | {rule} | {conf}")

    # Search for ANY mention of the error concept
    error_keywords = {
        "smartphone_4": ["16", "gb", "ram", "memory"],
        "melatonin_5": ["lead", "5", "mcg", "ppm", "heavy metal"],
        "melatonin_8": ["fda", "food and drug", "approved", "administration"],
    }

    keywords = error_keywords.get(file_key, [])
    relevant_violations = []

    for violation in violations:
        violation_lower = violation.lower()
        # If violation mentions ANY keyword, it might be the error
        if any(kw in violation_lower for kw in keywords):
            relevant_violations.append(violation)

    # If we found violations mentioning the error, it was NOT missed
    truly_missed = len(relevant_violations) == 0

    return truly_missed, relevant_violations


def main():
    print("\n" + "="*80)
    print("VALIDATION: Verifying 'Missed' Errors")
    print("="*80 + "\n")

    results_dir = Path("results/pilot_individual")

    false_negatives = []  # Errors I reported as "missed" but were actually detected

    for file_key, error_info in GROUND_TRUTH.items():
        csv_path = results_dir / f"{file_key}.csv"

        print(f"Checking {file_key}: {error_info['full_desc']}")

        truly_missed, relevant_violations = verify_missed_error(file_key, csv_path)

        if truly_missed:
            print(f"  ✅ CONFIRMED MISSED - No violations found mentioning this error")
        else:
            print(f"  ❌ FALSE NEGATIVE - Error WAS detected!")
            print(f"     Found {len(relevant_violations)} relevant violations:")
            for v in relevant_violations[:3]:  # Show top 3
                print(f"       - {v[:120]}...")
            false_negatives.append(file_key)

        print()

    # Summary
    print("="*80)
    print("VALIDATION SUMMARY")
    print("="*80)

    if false_negatives:
        print(f"\n⚠️  FALSE NEGATIVES DETECTED: {len(false_negatives)}")
        print("These errors were reported as 'missed' but were actually detected:")
        for key in false_negatives:
            print(f"  - {key}: {GROUND_TRUTH[key]['full_desc']}")
        print("\n🔧 ACTION REQUIRED: Fix keyword matching before reporting results!")
    else:
        print("\n✅ All 'missed' errors are confirmed as truly missed")
        print("   Safe to report detection results")

    print("="*80 + "\n")

    return len(false_negatives) == 0


if __name__ == "__main__":
    is_valid = main()
    exit(0 if is_valid else 1)
