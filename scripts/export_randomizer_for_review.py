"""
Export Randomizer Results for Manual Review

Creates simple CSV files for manual inspection in Excel/Google Sheets.

Usage:
    python scripts/export_randomizer_for_review.py
"""

import pandas as pd
import random
from pathlib import Path

# ==================== CONFIGURATION ====================

INPUT_CSV = Path("results/randomizer_dry_run_1620.csv")
OUTPUT_DIR = Path("results")

SUMMARY_CSV = OUTPUT_DIR / "randomizer_review_summary.csv"
SAMPLE_CSV = OUTPUT_DIR / "randomizer_review_sample_50.csv"
FIRST_LAST_CSV = OUTPUT_DIR / "randomizer_review_first_last_10.csv"

SAMPLE_SIZE = 50
RANDOM_SEED = 42


# ==================== FUNCTIONS ====================

def load_data() -> pd.DataFrame:
    """Load dry-run results."""
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input CSV not found: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV)
    print(f"✅ Loaded {len(df)} runs from {INPUT_CSV}")
    return df


def create_summary_table(df: pd.DataFrame) -> pd.DataFrame:
    """Create summary table with counts by day and time slot."""

    # Summary by day
    day_summary = df.groupby('scheduled_day_of_week').agg({
        'run_id': 'count',
        'product_id': lambda x: ' | '.join(f"{val}:{sum(x==val)}" for val in sorted(x.unique())),
        'engine': lambda x: ' | '.join(f"{val}:{sum(x==val)}" for val in sorted(x.unique())),
        'material_type': lambda x: ' | '.join(f"{val}:{sum(x==val)}" for val in sorted(x.unique()))
    }).reset_index()

    day_summary.columns = ['Day', 'Total_Runs', 'Products', 'Engines', 'Materials']

    # Reorder days
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_summary['Day'] = pd.Categorical(day_summary['Day'], categories=day_order, ordered=True)
    day_summary = day_summary.sort_values('Day').reset_index(drop=True)

    return day_summary


def create_timeslot_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Create summary table by time slot."""

    timeslot_summary = df.groupby('scheduled_time_slot').agg({
        'run_id': 'count',
        'is_weekend': lambda x: sum(x),  # Count weekend runs
    }).reset_index()

    timeslot_summary['weekday_runs'] = timeslot_summary['run_id'] - timeslot_summary['is_weekend']
    timeslot_summary.columns = ['Time_Slot', 'Total_Runs', 'Weekend_Runs', 'Weekday_Runs']

    # Reorder columns
    timeslot_summary = timeslot_summary[['Time_Slot', 'Total_Runs', 'Weekday_Runs', 'Weekend_Runs']]

    # Reorder rows
    slot_order = ['morning', 'afternoon', 'evening']
    timeslot_summary['Time_Slot'] = pd.Categorical(timeslot_summary['Time_Slot'], categories=slot_order, ordered=True)
    timeslot_summary = timeslot_summary.sort_values('Time_Slot').reset_index(drop=True)

    return timeslot_summary


def create_combined_summary(day_summary: pd.DataFrame, timeslot_summary: pd.DataFrame) -> pd.DataFrame:
    """Combine day and timeslot summaries into single table."""

    # Add separator row
    separator = pd.DataFrame([{
        'Day': '--- TIME SLOTS ---',
        'Total_Runs': '',
        'Products': '',
        'Engines': '',
        'Materials': ''
    }])

    # Convert timeslot summary to match day summary columns
    timeslot_for_concat = timeslot_summary.copy()
    timeslot_for_concat.columns = ['Day', 'Total_Runs', 'Products', 'Engines']
    timeslot_for_concat['Materials'] = ''

    # Concatenate
    combined = pd.concat([day_summary, separator, timeslot_for_concat], ignore_index=True)

    return combined


def create_random_sample(df: pd.DataFrame, n: int, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Create random sample of runs for spot-checking."""

    random.seed(seed)
    sample = df.sample(n=n, random_state=seed)

    # Select relevant columns
    cols = [
        'run_id', 'run_order', 'product_id', 'engine', 'material_type',
        'temperature', 'repetition',
        'scheduled_day_of_week', 'scheduled_time_slot', 'scheduled_timestamp',
        'is_weekend'
    ]

    sample = sample[cols].sort_values('run_order').reset_index(drop=True)

    return sample


def create_first_last_sample(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """Create sample with first N and last N runs."""

    df_sorted = df.sort_values('run_order')

    first_n = df_sorted.head(n)
    last_n = df_sorted.tail(n)

    # Combine
    combined = pd.concat([first_n, last_n]).reset_index(drop=True)

    # Select relevant columns
    cols = [
        'run_id', 'run_order', 'product_id', 'engine', 'material_type',
        'temperature', 'repetition',
        'scheduled_day_of_week', 'scheduled_time_slot', 'scheduled_timestamp',
        'is_weekend'
    ]

    combined = combined[cols]

    return combined


def save_csv(df: pd.DataFrame, path: Path, description: str):
    """Save DataFrame to CSV."""
    df.to_csv(path, index=False)
    print(f"  ✅ Saved: {path} ({description})")


# ==================== MAIN ====================

def main():
    """Export all review files."""
    print("=" * 70)
    print("EXPORTING RANDOMIZER RESULTS FOR MANUAL REVIEW")
    print("=" * 70)

    # Load data
    df = load_data()

    print("\n" + "=" * 70)
    print("CREATING SUMMARY TABLES")
    print("=" * 70)

    # Create summaries
    day_summary = create_summary_table(df)
    timeslot_summary = create_timeslot_summary(df)
    combined_summary = create_combined_summary(day_summary, timeslot_summary)

    # Save summary
    save_csv(combined_summary, SUMMARY_CSV, "Summary by day and time slot")

    print("\n" + "=" * 70)
    print("CREATING SAMPLE DATASETS")
    print("=" * 70)

    # Create random sample
    random_sample = create_random_sample(df, SAMPLE_SIZE, RANDOM_SEED)
    save_csv(random_sample, SAMPLE_CSV, f"Random sample of {SAMPLE_SIZE} runs")

    # Create first/last sample
    first_last_sample = create_first_last_sample(df, 10)
    save_csv(first_last_sample, FIRST_LAST_CSV, "First 10 + Last 10 runs")

    print("\n" + "=" * 70)
    print("✅ Export complete!")
    print("=" * 70)
    print(f"\nOutputs:")
    print(f"  1. {SUMMARY_CSV}")
    print(f"  2. {SAMPLE_CSV}")
    print(f"  3. {FIRST_LAST_CSV}")
    print(f"\nYou can open these files in Excel or Google Sheets for manual review.")


if __name__ == "__main__":
    main()
