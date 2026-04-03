#!/usr/bin/env python3
"""Prepare experiments.csv for R statistical analysis.

Converts current matrix format to match R script expectations:
- scheduled_datetime → scheduled_date + scheduled_time_slot
- time_of_day_label → scheduled_time_slot
- Validates all required columns exist
"""

import pandas as pd
from pathlib import Path

def prepare_matrix_for_r():
    """Convert experiments.csv to R-compatible format."""

    # Read current matrix
    matrix_path = Path("results/experiments.csv")
    df = pd.read_csv(matrix_path)

    print(f"✓ Loaded matrix: {len(df)} rows")

    # Extract scheduled_date from scheduled_datetime
    df['scheduled_date'] = pd.to_datetime(df['scheduled_datetime']).dt.date

    # Rename time_of_day_label to scheduled_time_slot (R script expects this)
    df['scheduled_time_slot'] = df['time_of_day_label']

    # Verify required columns for R script
    required_cols = [
        'scheduled_date',
        'scheduled_day_of_week',
        'scheduled_time_slot',
        'product_id',
        'engine',
        'temperature'
    ]

    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        print(f"✗ Missing required columns: {missing}")
        return False

    print(f"✓ All required columns present")

    # Show summary statistics
    print(f"\n=== Matrix Summary ===")
    print(f"Total runs: {len(df)}")
    print(f"Seed: {df['matrix_randomization_seed'].iloc[0]}")
    print(f"Mode: {df['matrix_randomization_mode'].iloc[0]}")
    print(f"\nProducts: {sorted(df['product_id'].unique())}")
    print(f"Engines: {sorted(df['engine'].unique())}")
    print(f"Temperatures: {sorted(df['temperature'].unique())}")
    print(f"Time slots: {sorted(df['scheduled_time_slot'].unique())}")
    print(f"Days: {sorted(df['scheduled_day_of_week'].unique())}")

    # Count by factors
    print(f"\n=== Balance Check ===")
    print(f"Runs per product:")
    print(df['product_id'].value_counts().sort_index())
    print(f"\nRuns per engine:")
    print(df['engine'].value_counts().sort_index())
    print(f"\nRuns per temperature:")
    print(df['temperature'].value_counts().sort_index())
    print(f"\nRuns per time slot:")
    print(df['scheduled_time_slot'].value_counts().sort_index())

    # Engine × Time slot crosstab
    print(f"\n=== Engine × Time Slot Crosstab ===")
    crosstab = pd.crosstab(df['engine'], df['scheduled_time_slot'])
    print(crosstab)
    print(f"\nRange: {crosstab.min().min()} - {crosstab.max().max()}")

    # Save R-compatible version
    output_path = Path("results/experiments_for_r.csv")
    df.to_csv(output_path, index=False)
    print(f"\n✓ Saved R-compatible matrix: {output_path}")

    return True

if __name__ == "__main__":
    success = prepare_matrix_for_r()
    exit(0 if success else 1)
