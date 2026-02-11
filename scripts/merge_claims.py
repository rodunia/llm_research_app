"""Merge all individual claim review CSVs into a single consolidated file."""

import pandas as pd
from pathlib import Path
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
RESULTS_DIR = PROJECT_ROOT / "results"

def merge_claims():
    """Merge all *_claims_review.csv files into results/all_claims_review.csv."""

    # Find all claims review CSVs
    csv_files = list(OUTPUTS_DIR.glob("*_claims_review.csv"))

    if not csv_files:
        print("No claims review CSV files found in outputs/")
        return

    print(f"Found {len(csv_files)} claims review CSV files")

    # Read and concatenate all CSVs
    dfs = []
    for csv_file in tqdm(csv_files, desc="Reading CSV files"):
        df = pd.read_csv(csv_file)
        dfs.append(df)

    # Concatenate all dataframes
    merged_df = pd.concat(dfs, ignore_index=True)

    # Save merged file
    output_path = RESULTS_DIR / "all_claims_review.csv"
    merged_df.to_csv(output_path, index=False)

    print(f"\n✓ Merged {len(csv_files)} CSV files")
    print(f"✓ Total claims: {len(merged_df):,}")
    print(f"✓ Saved to: {output_path}")

    # Print summary statistics
    print(f"\nSummary:")
    print(f"  - Total runs: {merged_df['run_id'].nunique()}")
    print(f"  - Products: {merged_df['product_id'].nunique()}")
    print(f"  - Material types: {merged_df['material_type'].nunique()}")
    print(f"  - Match types:")
    for match_type, count in merged_df['match_type'].value_counts().items():
        print(f"    - {match_type}: {count:,}")
    print(f"  - Claims needing review: {merged_df['needs_review'].sum():,}")

if __name__ == "__main__":
    merge_claims()
