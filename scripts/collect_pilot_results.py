#!/usr/bin/env python3
"""
Collect results from individual pilot file audits and analyze detection rates.
Reads results/final_audit_results.csv which gets overwritten by each audit.
"""

import csv
import subprocess
import time
from pathlib import Path
from collections import defaultdict

# Ground truth errors with keywords for detection
GROUND_TRUTH = {
    # Smartphone
    "user_smartphone_1": ("Display 6.5\" (should be 6.3\")", ["6.5", "6.5 inch", "6.5\""]),
    "user_smartphone_2": ("Camera 48 MP (should be 50 MP)", ["48 mp", "48mp", "48 megapixel"]),
    "user_smartphone_3": ("1 TB storage (not available)", ["1 tb", "1tb", "1000 gb", "1 terabyte"]),
    "user_smartphone_4": ("16 GB RAM (not available)", ["16 gb ram", "16gb ram"]),
    "user_smartphone_5": ("Wi-Fi 7 (should be 6/6E)", ["wi-fi 7", "wifi 7", "802.11be"]),
    "user_smartphone_6": ("Wireless charging (not supported)", ["wireless charging", "qi charging"]),
    "user_smartphone_7": ("Hourly antivirus scanning", ["hourly", "antivirus scan", "every hour"]),
    "user_smartphone_8": ("Offline AI video rendering", ["offline", "ai video", "render"]),
    "user_smartphone_9": ("60W charging (should be 30-45W)", ["60w", "60 watt"]),
    "user_smartphone_10": ("External SSD via SIM tray", ["external ssd", "sim tray", "external storage"]),

    # Melatonin
    "user_melatonin_1": ("Dosage 5 mg (should be 3 mg)", ["5 mg", "5mg per tablet", "five milligram"]),
    "user_melatonin_2": ("100 tablets (should be 120)", ["100 tablet", "100-tablet"]),
    "user_melatonin_3": ("Vegan + fish ingredients", ["fish", "fish-derived", "marine", "fish oil"]),
    "user_melatonin_4": ("Wheat traces despite 0 mg gluten", ["wheat", "traces of wheat"]),
    "user_melatonin_5": ("Lead 5 mcg (should be <0.5 mcg)", ["5 mcg", "5.0 mcg lead"]),
    "user_melatonin_6": ("Storage 0°C (too cold)", ["0°c", "32°f", "freezing", "0 degrees"]),
    "user_melatonin_7": ("Take every 2 hours (unsafe)", ["every 2 hour", "2-hour interval", "every two hour"]),
    "user_melatonin_8": ("FDA approved (supplements aren't)", ["fda approved", "fda-approved", "approved by fda"]),
    "user_melatonin_9": ("Avoid if over 18 (age reversal)", ["over 18", "above 18", "18+"]),
    "user_melatonin_10": ("Permanent drowsiness", ["permanent", "lasting drowsiness", "permanently"]),
}


def check_detection_in_csv(run_id: str, csv_path: Path) -> tuple:
    """Check if error was detected in CSV results."""
    if run_id not in GROUND_TRUTH:
        return False, 0

    error_desc, keywords = GROUND_TRUTH[run_id]

    if not csv_path.exists():
        return False, 0

    violations = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            filename = row.get('Filename', '')
            if run_id in filename or filename.startswith(run_id):
                violations.append(row)

    # Check if any violation matches keywords
    detected = False
    for v in violations:
        claim = v.get('Extracted_Claim', '').lower()
        rule = v.get('Violated_Rule', '').lower()
        combined = claim + " " + rule

        if any(kw.lower() in combined for kw in keywords):
            detected = True
            break

    return detected, len(violations)


def collect_results_from_individual_csvs():
    """
    Since each audit overwrites final_audit_results.csv, we need to
    save each one immediately after it completes.
    """
    results_dir = Path("results/pilot_individual")
    results_dir.mkdir(exist_ok=True)

    all_run_ids = list(GROUND_TRUTH.keys())

    print("Waiting for audits to complete and collecting results...")
    print("(This will poll every 10 seconds for up to 20 minutes)")

    collected = set()
    timeout = time.time() + 1200  # 20 minutes

    while time.time() < timeout and len(collected) < len(all_run_ids):
        # Check final_audit_results.csv
        csv_path = Path("results/final_audit_results.csv")
        if csv_path.exists():
            # Try to identify which run_id this is for
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                if rows:
                    # Get filename from first row
                    first_file = rows[0].get('Filename', '')

                    # Find matching run_id
                    for run_id in all_run_ids:
                        if run_id in first_file and run_id not in collected:
                            # Save this result
                            save_path = results_dir / f"{run_id}.csv"
                            subprocess.run(['cp', str(csv_path), str(save_path)])
                            collected.add(run_id)
                            print(f"  ✓ Collected {run_id} ({len(collected)}/{len(all_run_ids)})")
                            break

        time.sleep(10)

    print(f"\nCollected {len(collected)}/{len(all_run_ids)} results")
    return results_dir


def analyze_collected_results(results_dir: Path):
    """Analyze all collected results."""
    smartphone_ids = [f"user_smartphone_{i}" for i in range(1, 11)]
    melatonin_ids = [f"user_melatonin_{i}" for i in range(1, 11)]

    results = {}

    for run_id in smartphone_ids + melatonin_ids:
        csv_path = results_dir / f"{run_id}.csv"
        detected, violations = check_detection_in_csv(run_id, csv_path)
        results[run_id] = (detected, violations)

    # Analyze Smartphone
    print("\n" + "="*80)
    print("SMARTPHONE DETECTION ANALYSIS")
    print("="*80)

    smartphone_detected = 0
    smartphone_violations = 0

    for i, run_id in enumerate(smartphone_ids, 1):
        detected, violations = results.get(run_id, (False, 0))
        error_desc = GROUND_TRUTH[run_id][0]
        status = "✅ DETECTED" if detected else "❌ MISSED"
        print(f"File {i:2d}: {status:15s} - {error_desc} ({violations} violations)")
        if detected:
            smartphone_detected += 1
        smartphone_violations += violations

    print(f"\nDetection Rate: {smartphone_detected}/10 ({smartphone_detected/10*100:.0f}%)")
    print(f"Average violations: {smartphone_violations/10:.1f}")

    # Analyze Melatonin
    print("\n" + "="*80)
    print("MELATONIN DETECTION ANALYSIS")
    print("="*80)

    melatonin_detected = 0
    melatonin_violations = 0

    for i, run_id in enumerate(melatonin_ids, 1):
        detected, violations = results.get(run_id, (False, 0))
        error_desc = GROUND_TRUTH[run_id][0]
        status = "✅ DETECTED" if detected else "❌ MISSED"
        print(f"File {i:2d}: {status:15s} - {error_desc} ({violations} violations)")
        if detected:
            melatonin_detected += 1
        melatonin_violations += violations

    print(f"\nDetection Rate: {melatonin_detected}/10 ({melatonin_detected/10*100:.0f}%)")
    print(f"Average violations: {melatonin_violations/10:.1f}")

    # Overall summary
    print("\n" + "="*80)
    print("OVERALL SUMMARY (Smartphone + Melatonin)")
    print("="*80)
    total_detected = smartphone_detected + melatonin_detected
    total_files = 20
    total_violations = smartphone_violations + melatonin_violations

    print(f"Detection Rate: {total_detected}/20 ({total_detected/20*100:.0f}%)")
    print(f"Average violations: {total_violations/20:.1f}")
    print(f"\nSmartphone: {smartphone_detected}/10 ({smartphone_detected/10*100:.0f}%)")
    print(f"Melatonin:  {melatonin_detected}/10 ({melatonin_detected/10*100:.0f}%)")

    return {
        'smartphone_detected': smartphone_detected,
        'smartphone_violations': smartphone_violations,
        'melatonin_detected': melatonin_detected,
        'melatonin_violations': melatonin_violations
    }


if __name__ == "__main__":
    print("Pilot Study Results Collector")
    print("="*80)

    # Wait for audits and collect results
    results_dir = collect_results_from_individual_csvs()

    # Analyze
    results = analyze_collected_results(results_dir)

    print("\n" + "="*80)
    print("Collection complete. Results saved in", results_dir)
    print("="*80)
