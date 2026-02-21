#!/usr/bin/env python3
"""
Add pilot study files to experiments.csv for reproducibility.

This script appends metadata entries for the 30 pilot files so that
glass_box_audit.py can find them in experiments.csv.
"""

import csv
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
EXPERIMENTS_CSV = PROJECT_ROOT / "results" / "experiments.csv"

# Pilot file metadata
PILOT_FILES = []

# CoreCoin (10 files)
for i in range(1, 11):
    PILOT_FILES.append({
        "run_id": f"user_corecoin_{i}",
        "product_id": "cryptocurrency_corecoin",
        "engine": "openai",
        "temperature": 0.6,
        "material_type": "faq.j2",
        "time_slot": 1,
        "rep": 1,
        "date": "2026-02-21",
        "time_of_day": "morning",
        "status": "completed",
        "trap_flag": "FALSE",
        "output_path": f"outputs/user_corecoin_{i}.txt"
    })

# Smartphone (10 files)
for i in range(1, 11):
    PILOT_FILES.append({
        "run_id": f"user_smartphone_{i}",
        "product_id": "smartphone_mid",
        "engine": "openai",
        "temperature": 0.6,
        "material_type": "faq.j2",
        "time_slot": 1,
        "rep": 1,
        "date": "2026-02-21",
        "time_of_day": "morning",
        "status": "completed",
        "trap_flag": "FALSE",
        "output_path": f"outputs/user_smartphone_{i}.txt"
    })

# Melatonin (10 files)
for i in range(1, 11):
    PILOT_FILES.append({
        "run_id": f"user_melatonin_{i}",
        "product_id": "supplement_melatonin",
        "engine": "openai",
        "temperature": 0.6,
        "material_type": "faq.j2",
        "time_slot": 1,
        "rep": 1,
        "date": "2026-02-21",
        "time_of_day": "morning",
        "status": "completed",
        "trap_flag": "FALSE",
        "output_path": f"outputs/user_melatonin_{i}.txt"
    })


def main():
    """Add pilot files to experiments.csv."""

    # Read existing CSV
    existing_run_ids = set()
    rows = []

    if EXPERIMENTS_CSV.exists():
        with open(EXPERIMENTS_CSV, 'r') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                existing_run_ids.add(row['run_id'])
                rows.append(row)
    else:
        print(f"Error: {EXPERIMENTS_CSV} not found")
        return

    # Add new pilot files
    added_count = 0
    for pilot_file in PILOT_FILES:
        if pilot_file['run_id'] not in existing_run_ids:
            rows.append(pilot_file)
            added_count += 1
            print(f"Added: {pilot_file['run_id']}")

    if added_count == 0:
        print("All pilot files already in experiments.csv")
        return

    # Write back to CSV
    with open(EXPERIMENTS_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n✓ Added {added_count} pilot files to {EXPERIMENTS_CSV}")
    print(f"Total entries: {len(rows)}")


if __name__ == "__main__":
    main()
