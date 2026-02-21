#!/usr/bin/env python3
"""
Comprehensive analysis of all 30 pilot study files.
Analyzes detection rates across CoreCoin, Smartphone, and Melatonin.
"""

import csv
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Ground truth: intentional errors for all 30 files
GROUND_TRUTH = {
    # CoreCoin (10 files)
    "user_corecoin_1": {
        "error": "Block time 4s (should be ~5s)",
        "keywords": ["block time", "4 second", "4s", "four second"],
    },
    "user_corecoin_2": {
        "error": "Light validators (non-staking)",
        "keywords": ["light validator", "non-staking", "without staking"],
    },
    "user_corecoin_3": {
        "error": "Regional trading pauses",
        "keywords": ["regional", "trading pause", "geographic"],
    },
    "user_corecoin_4": {
        "error": "Automatic key sharding backup",
        "keywords": ["automatic", "key sharding", "auto-shard"],
    },
    "user_corecoin_5": {
        "error": "EVM execution without gas fees",
        "keywords": ["without gas", "no gas fee", "gasless", "gas-free"],
    },
    "user_corecoin_6": {
        "error": "Proposals auto-pass without quorum",
        "keywords": ["auto-pass", "automatic pass", "without quorum"],
    },
    "user_corecoin_7": {
        "error": "RPC simulates cross-chain calls",
        "keywords": ["RPC", "simulate", "cross-chain"],
    },
    "user_corecoin_8": {
        "error": "Early unstaking reduces historical rewards",
        "keywords": ["early unstaking", "reduce", "historical reward"],
    },
    "user_corecoin_9": {
        "error": "Validator inactivity locks governance rights",
        "keywords": ["inactivity", "lock", "governance"],
    },
    "user_corecoin_10": {
        "error": "Region-based fixed rate staking tiers",
        "keywords": ["region", "fixed rate", "staking tier"],
    },

    # Smartphone (10 files)
    "user_smartphone_1": {
        "error": "Display size 6.5\" (should be 6.3\")",
        "keywords": ["6.5", "6.5 inch", "6.5\""],
    },
    "user_smartphone_2": {
        "error": "Camera 48 MP (should be 50 MP)",
        "keywords": ["48 MP", "48MP", "48 megapixel"],
    },
    "user_smartphone_3": {
        "error": "1 TB storage option (not available)",
        "keywords": ["1 TB", "1TB", "1000 GB"],
    },
    "user_smartphone_4": {
        "error": "16 GB RAM option (not available)",
        "keywords": ["16 GB RAM", "16GB RAM"],
    },
    "user_smartphone_5": {
        "error": "Wi-Fi 7 (should be Wi-Fi 6/6E)",
        "keywords": ["Wi-Fi 7", "WiFi 7", "802.11be"],
    },
    "user_smartphone_6": {
        "error": "Wireless charging (not supported)",
        "keywords": ["wireless charging", "Qi charging"],
    },
    "user_smartphone_7": {
        "error": "Hourly antivirus scanning",
        "keywords": ["hourly", "antivirus scan"],
    },
    "user_smartphone_8": {
        "error": "Offline AI video rendering",
        "keywords": ["offline", "AI video", "render"],
    },
    "user_smartphone_9": {
        "error": "60W fast charging (should be 30-45W)",
        "keywords": ["60W", "60 watt"],
    },
    "user_smartphone_10": {
        "error": "External SSD via SIM tray (impossible)",
        "keywords": ["external SSD", "SIM tray", "external storage"],
    },

    # Melatonin (10 files)
    "user_melatonin_1": {
        "error": "Dosage mismatch (mg/tablet)",
        "keywords": ["5 mg", "5mg per tablet"],
    },
    "user_melatonin_2": {
        "error": "100 tablets per bottle (should be 120)",
        "keywords": ["100 tablet", "100-tablet"],
    },
    "user_melatonin_3": {
        "error": "Vegan but contains fish-derived ingredients",
        "keywords": ["fish", "fish-derived", "marine"],
    },
    "user_melatonin_4": {
        "error": "Wheat traces despite 0 mg gluten",
        "keywords": ["wheat", "traces of wheat"],
    },
    "user_melatonin_5": {
        "error": "Lead limit decimal error",
        "keywords": ["5 mcg", "5.0 mcg lead"],
    },
    "user_melatonin_6": {
        "error": "Storage at 0°C (too cold)",
        "keywords": ["0°C", "32°F", "freezing"],
    },
    "user_melatonin_7": {
        "error": "Take every 2 hours (unsafe dosage)",
        "keywords": ["every 2 hour", "2-hour interval"],
    },
    "user_melatonin_8": {
        "error": "FDA approved (supplements aren't)",
        "keywords": ["FDA approved", "FDA-approved", "approved by FDA"],
    },
    "user_melatonin_9": {
        "error": "Avoid if over 18 (age reversal)",
        "keywords": ["over 18", "above 18", "18+"],
    },
    "user_melatonin_10": {
        "error": "Permanent drowsiness side effect",
        "keywords": ["permanent", "lasting drowsiness"],
    },
}


def load_audit_results(run_id: str) -> List[Dict]:
    """Load audit results for a specific run from final_audit_results.csv"""
    results = []
    csv_path = Path("results/final_audit_results.csv")

    if not csv_path.exists():
        return results

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            filename = row.get('Filename', '')
            # Match either "user_X_Y.txt" or just the run_id
            if filename.startswith(run_id):
                results.append(row)

    return results


def check_detection(run_id: str) -> Tuple[bool, int, List[str]]:
    """
    Check if intentional error was detected for this run.
    Returns: (detected: bool, violation_count: int, top_violations: List[str])
    """
    if run_id not in GROUND_TRUTH:
        return False, 0, []

    truth = GROUND_TRUTH[run_id]
    keywords = [k.lower() for k in truth['keywords']]

    # Load violations
    violations = load_audit_results(run_id)
    violation_count = len(violations)

    # Check if any violation matches the keywords
    detected = False
    top_violations = []

    for violation in violations[:10]:  # Check top 10
        claim = violation.get('Extracted_Claim', '').lower()
        rule = violation.get('Violated_Rule', '').lower()
        combined = claim + " " + rule

        # Check if any keyword appears in claim or rule
        if any(keyword in combined for keyword in keywords):
            detected = True
            top_violations.append(f"{claim[:80]}... ({float(violation.get('Confidence_Score', 0)):.2%})")

    # Get top 5 violations for inspection
    if not top_violations:
        for violation in violations[:5]:
            claim = violation.get('Extracted_Claim', '')
            conf = float(violation.get('Confidence_Score', 0))
            top_violations.append(f"{claim[:80]}... ({conf:.2%})")

    return detected, violation_count, top_violations


def analyze_product(product: str, run_ids: List[str]):
    """Analyze detection rate for a specific product"""
    print(f"\n{'='*80}")
    print(f"{product.upper()} DETECTION ANALYSIS")
    print(f"{'='*80}\n")

    detected_count = 0
    total_violations = 0
    results = []

    for run_id in run_ids:
        detected, violations, top = check_detection(run_id)
        total_violations += violations

        file_num = run_id.split('_')[-1]
        error_desc = GROUND_TRUTH[run_id]['error']

        status = "✅ DETECTED" if detected else "❌ MISSED"

        if detected:
            detected_count += 1

        results.append({
            'file_num': file_num,
            'detected': detected,
            'error_desc': error_desc,
            'violations': violations,
            'top': top,
        })

        print(f"File {file_num:2s}: {status:15s} - {error_desc} ({violations} violations)")

    # Summary
    total = len(run_ids)
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Detection Rate: {detected_count}/{total} ({detected_count/total*100:.0f}%)")
    print(f"Average violations per file: {total_violations/total:.1f}")
    print(f"Total violations: {total_violations}")

    return detected_count, total, total_violations


def main():
    # Run audits for all 30 files
    print("Running Glass Box Audit on all 30 pilot files...")
    print("(This will take ~10-15 minutes)\n")

    import subprocess
    import os

    all_run_ids = list(GROUND_TRUTH.keys())

    # Run audits
    for i, run_id in enumerate(all_run_ids, 1):
        print(f"[{i:2d}/30] Auditing {run_id}...")
        subprocess.run(
            ["python3", "analysis/glass_box_audit.py", "--run-id", run_id],
            env={**os.environ, "PYTHONPATH": "."},
            capture_output=True,
            cwd=Path.cwd()
        )

    print("\n" + "="*80)
    print("COMPLETE PILOT STUDY ANALYSIS (30 FILES)")
    print("="*80)

    # Analyze each product
    corecoin_ids = [f"user_corecoin_{i}" for i in range(1, 11)]
    smartphone_ids = [f"user_smartphone_{i}" for i in range(1, 11)]
    melatonin_ids = [f"user_melatonin_{i}" for i in range(1, 11)]

    corecoin_detected, corecoin_total, corecoin_violations = analyze_product("CoreCoin", corecoin_ids)
    smartphone_detected, smartphone_total, smartphone_violations = analyze_product("Smartphone", smartphone_ids)
    melatonin_detected, melatonin_total, melatonin_violations = analyze_product("Melatonin", melatonin_ids)

    # Overall summary
    total_detected = corecoin_detected + smartphone_detected + melatonin_detected
    total_files = 30
    total_violations = corecoin_violations + smartphone_violations + melatonin_violations

    print(f"\n{'='*80}")
    print(f"OVERALL PILOT STUDY RESULTS")
    print(f"{'='*80}")
    print(f"Total Detection Rate: {total_detected}/{total_files} ({total_detected/total_files*100:.0f}%)")
    print(f"Average violations per file: {total_violations/total_files:.1f}")
    print(f"Total violations: {total_violations}")
    print(f"\nBreakdown by product:")
    print(f"  CoreCoin:    {corecoin_detected}/10 ({corecoin_detected/10*100:.0f}%) - {corecoin_violations} violations")
    print(f"  Smartphone:  {smartphone_detected}/10 ({smartphone_detected/10*100:.0f}%) - {smartphone_violations} violations")
    print(f"  Melatonin:   {melatonin_detected}/10 ({melatonin_detected/10*100:.0f}%) - {melatonin_violations} violations")


if __name__ == "__main__":
    main()
