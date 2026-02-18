#!/usr/bin/env python3
"""Batch audit user-uploaded files only."""

import sys
import subprocess
import pandas as pd
from pathlib import Path

# Read experiments.csv
csv_path = Path("results/experiments.csv")
df = pd.read_csv(csv_path)

# Filter user-uploaded files
user_files = df[df['run_id'].str.startswith('user_')]

print(f"Found {len(user_files)} user-uploaded files to audit\n")

# Run Glass Box Audit with all user files
# Create a temp CSV with just user files
temp_csv = Path("results/experiments_user_only.csv")
user_files.to_csv(temp_csv, index=False)

print("Running Glass Box Audit on user files...")
print("This will take approximately 5-10 minutes\n")

# Run audit
result = subprocess.run(
    [sys.executable, "-m", "analysis.glass_box_audit", "--clean"],
    env={'PYTHONPATH': '.', 'EXPERIMENTS_CSV_OVERRIDE': str(temp_csv), **subprocess.os.environ},
    cwd='/Users/dorotajaguscik/PycharmProjects/llm_research_app'
)

# Clean up temp file
temp_csv.unlink()

if result.returncode == 0:
    print("\n✅ User file audit complete!")
    print("\nView violations:")
    print("  grep '^user_' results/final_audit_results.csv")
else:
    print(f"\n❌ Audit failed with code {result.returncode}")
    sys.exit(1)
