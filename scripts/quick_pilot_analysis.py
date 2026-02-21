#!/usr/bin/env python3
"""
Quick analysis of pilot study using existing final_audit_results.csv files.
Manually audits each file and checks detection.
"""

import csv
import subprocess
import os
from pathlib import Path

# Ground truth
GROUND_TRUTH = {
    # CoreCoin
    "user_corecoin_1": ("Block time 4s", ["block time", "4 second", "4s"]),
    "user_corecoin_2": ("Light validators", ["light validator", "non-staking"]),
    "user_corecoin_3": ("Regional trading", ["regional", "trading pause"]),
    "user_corecoin_4": ("Key sharding", ["automatic", "key shard"]),
    "user_corecoin_5": ("No gas fees", ["without gas", "gasless", "gas-free"]),
    "user_corecoin_6": ("Auto-pass proposals", ["auto-pass", "without quorum"]),
    "user_corecoin_7": ("RPC cross-chain", ["rpc", "simulate", "cross-chain"]),
    "user_corecoin_8": ("Early unstaking", ["early unstaking", "historical reward"]),
    "user_corecoin_9": ("Inactivity locks", ["inactivity", "lock", "governance"]),
    "user_corecoin_10": ("Region-based staking", ["region", "fixed rate", "staking tier"]),

    # Smartphone
    "user_smartphone_1": ("Display 6.5\"", ["6.5", "6.5 inch"]),
    "user_smartphone_2": ("Camera 48 MP", ["48 mp", "48mp", "48 megapixel"]),
    "user_smartphone_3": ("1 TB storage", ["1 tb", "1tb", "1000 gb"]),
    "user_smartphone_4": ("16 GB RAM", ["16 gb ram", "16gb ram"]),
    "user_smartphone_5": ("Wi-Fi 7", ["wi-fi 7", "wifi 7", "802.11be"]),
    "user_smartphone_6": ("Wireless charging", ["wireless charging", "qi charging"]),
    "user_smartphone_7": ("Hourly antivirus", ["hourly", "antivirus scan"]),
    "user_smartphone_8": ("Offline AI rendering", ["offline", "ai video", "render"]),
    "user_smartphone_9": ("60W charging", ["60w", "60 watt"]),
    "user_smartphone_10": ("External SSD", ["external ssd", "sim tray", "external storage"]),

    # Melatonin
    "user_melatonin_1": ("Dosage 5 mg", ["5 mg", "5mg per tablet"]),
    "user_melatonin_2": ("100 tablets", ["100 tablet"]),
    "user_melatonin_3": ("Fish ingredients", ["fish", "fish-derived"]),
    "user_melatonin_4": ("Wheat traces", ["wheat", "traces of wheat"]),
    "user_melatonin_5": ("Lead 5 mcg", ["5 mcg", "5.0 mcg lead"]),
    "user_melatonin_6": ("Storage 0°C", ["0°c", "32°f", "freezing"]),
    "user_melatonin_7": ("Every 2 hours", ["every 2 hour", "2-hour interval"]),
    "user_melatonin_8": ("FDA approved", ["fda approved", "fda-approved", "approved by fda"]),
    "user_melatonin_9": ("Avoid if over 18", ["over 18", "above 18", "18+"]),
    "user_melatonin_10": ("Permanent drowsiness", ["permanent", "lasting drowsiness"]),
}


def audit_and_check(run_id: str) -> tuple:
    """Audit a single run and check if error was detected."""
    error_desc, keywords = GROUND_TRUTH[run_id]

    # Run audit
    result = subprocess.run(
        ["python3", "analysis/glass_box_audit.py", "--run-id", run_id],
        env={**os.environ, "PYTHONPATH": "."},
        capture_output=True,
        cwd=Path.cwd(),
        text=True
    )

    # Load results
    csv_path = Path("results/final_audit_results.csv")
    if not csv_path.exists():
        return False, 0

    violations = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if run_id in row['Filename']:
                violations.append(row)

    # Check detection
    detected = False
    for v in violations:
        claim = v.get('Extracted_Claim', '').lower()
        rule = v.get('Violated_Rule', '').lower()
        combined = claim + " " + rule

        if any(kw.lower() in combined for kw in keywords):
            detected = True
            break

    return detected, len(violations)


def main():
    print("\n" + "="*80)
    print("COMPLETE PILOT STUDY ANALYSIS (30 FILES)")
    print("="*80)

    products = {
        'CoreCoin': [f"user_corecoin_{i}" for i in range(1, 11)],
        'Smartphone': [f"user_smartphone_{i}" for i in range(1, 11)],
        'Melatonin': [f"user_melatonin_{i}" for i in range(1, 11)],
    }

    overall_detected = 0
    overall_total = 0
    overall_violations = 0

    for product, run_ids in products.items():
        print(f"\n{'='*80}")
        print(f"{product.upper()} DETECTION ANALYSIS")
        print(f"{'='*80}\n")

        detected_count = 0
        total_violations = 0

        for run_id in run_ids:
            file_num = run_id.split('_')[-1]
            error_desc, _ = GROUND_TRUTH[run_id]

            print(f"[{file_num:2s}/10] Auditing {run_id}...", end=' ', flush=True)
            detected, violations = audit_and_check(run_id)

            status = "✅ DETECTED" if detected else "❌ MISSED"
            print(f"{status} - {error_desc} ({violations} violations)")

            if detected:
                detected_count += 1
            total_violations += violations

        # Summary
        total = len(run_ids)
        print(f"\n{'-'*80}")
        print(f"Detection Rate: {detected_count}/{total} ({detected_count/total*100:.0f}%)")
        print(f"Average violations per file: {total_violations/total:.1f}")
        print(f"Total violations: {total_violations}")

        overall_detected += detected_count
        overall_total += total
        overall_violations += total_violations

    # Overall summary
    print(f"\n{'='*80}")
    print(f"OVERALL RESULTS")
    print(f"{'='*80}")
    print(f"Total Detection Rate: {overall_detected}/{overall_total} ({overall_detected/overall_total*100:.0f}%)")
    print(f"Average violations per file: {overall_violations/overall_total:.1f}")
    print(f"Total violations: {overall_violations}")
    print(f"\nBreakdown by product:")
    print(f"  CoreCoin:    7/10 (70%) [from previous analysis]")
    print(f"  Smartphone: ?/10 (?%)")
    print(f"  Melatonin:   ?/10 (?%)")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    # Need to activate venv first
    if not Path(".venv").exists():
        print("ERROR: Virtual environment not found. Run: python -m venv .venv")
        exit(1)

    main()
