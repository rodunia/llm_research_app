#!/usr/bin/env python3
"""Add 5 new metadata columns to existing experiments.csv

Adds:
1. content_filter_triggered (bool)
2. prompt_hash (str)
3. retry_count (int)
4. error_type (str)
5. scheduled_vs_actual_delay_sec (float)
"""

import pandas as pd
from pathlib import Path
import sys

def add_metadata_columns():
    csv_path = Path("results/experiments.csv")

    if not csv_path.exists():
        print(f"✗ ERROR: {csv_path} not found")
        return False

    # Read CSV
    print(f"Reading {csv_path}...")
    df = pd.read_csv(csv_path)
    print(f"✓ Loaded {len(df)} rows, {len(df.columns)} columns")

    # Check current columns
    original_cols = len(df.columns)

    # Add 5 new columns with defaults
    new_columns = {
        'content_filter_triggered': False,
        'prompt_hash': '',
        'retry_count': 0,
        'error_type': '',
        'scheduled_vs_actual_delay_sec': 0.0
    }

    added_count = 0
    for col, default in new_columns.items():
        if col not in df.columns:
            df[col] = default
            print(f"✓ Added column: {col} (default: {repr(default)})")
            added_count += 1
        else:
            print(f"⚠ Column already exists: {col} (skipped)")

    new_total = len(df.columns)
    expected_total = original_cols + len(new_columns)

    # Verify
    print(f"\n=== Verification ===")
    print(f"Original columns: {original_cols}")
    print(f"Added columns: {added_count}")
    print(f"New total: {new_total}")
    print(f"Expected: {expected_total}")

    if new_total != expected_total:
        print(f"✗ ERROR: Column count mismatch")
        return False

    # Check all new columns exist
    missing = [col for col in new_columns.keys() if col not in df.columns]
    if missing:
        print(f"✗ ERROR: Missing columns: {missing}")
        return False

    print(f"✓ All {len(new_columns)} columns present")

    # Save
    print(f"\nSaving to {csv_path}...")
    df.to_csv(csv_path, index=False)
    print(f"✓ Saved successfully")

    # Final verification
    df_verify = pd.read_csv(csv_path)
    print(f"\n=== Final Check ===")
    print(f"Rows: {len(df_verify)}")
    print(f"Columns: {len(df_verify.columns)}")
    print(f"New columns present: {all(col in df_verify.columns for col in new_columns.keys())}")

    # Show sample
    print(f"\n=== Sample Row (new fields) ===")
    for col in new_columns.keys():
        print(f"{col}: {df_verify[col].iloc[0]}")

    return True

if __name__ == "__main__":
    success = add_metadata_columns()
    sys.exit(0 if success else 1)
