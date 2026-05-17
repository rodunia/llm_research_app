#!/usr/bin/env python3
"""
Reset Google/Gemini runs to pending status for rerun with higher token limit.

This script:
- Finds all rows where engine == 'google'
- Sets status = 'pending'
- Clears execution metadata (tokens, timestamps)
- Preserves ALL matrix randomization (run_id, product_id, temperature, etc.)

Usage:
  # DRY RUN - show what will be reset (does NOT modify CSV)
  python scripts/reset_gemini_runs.py --dry-run

  # EXECUTE - actually reset the runs
  python scripts/reset_gemini_runs.py --execute
"""

import csv
import argparse
from pathlib import Path
from typing import List, Dict

# Paths
EXPERIMENTS_CSV = Path("results/experiments.csv")
BACKUP_CSV = Path("results/experiments_backup_before_gemini_rerun.csv")

# Columns to clear (execution metadata only)
COLUMNS_TO_CLEAR = [
    'started_at',
    'completed_at',
    'date_of_run',
    'execution_duration_sec',
    'prompt_tokens',
    'completion_tokens',
    'total_tokens',
    'finish_reason',
    'retry_count',
    'error_type',
    'api_latency_ms',
    'content_filter_triggered',
    'scheduled_vs_actual_delay_sec',
    'prompt_hash',
]

# Columns to PRESERVE (matrix randomization - DO NOT TOUCH)
COLUMNS_TO_PRESERVE = [
    'run_id',
    'product_id',
    'material_type',
    'engine',
    'temperature',
    'repetition_id',
    'time_of_day_label',
    'scheduled_datetime',
    'scheduled_hour_of_day',
    'scheduled_day_of_week',
    'matrix_randomization_seed',
    'matrix_randomization_mode',
    'max_tokens',
    'seed',
    'top_p',
    'frequency_penalty',
    'presence_penalty',
    'trap_flag',
]


def load_experiments() -> List[Dict]:
    """Load experiments.csv."""
    if not EXPERIMENTS_CSV.exists():
        raise FileNotFoundError(f"experiments.csv not found: {EXPERIMENTS_CSV}")

    with open(EXPERIMENTS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


def find_google_runs(experiments: List[Dict]) -> List[Dict]:
    """Find all Google/Gemini runs."""
    return [exp for exp in experiments if exp.get('engine') == 'google']


def analyze_google_runs(google_runs: List[Dict]):
    """Show summary of what will be reset."""
    print("=" * 80)
    print("GOOGLE/GEMINI RUNS ANALYSIS")
    print("=" * 80)
    print()

    total = len(google_runs)
    print(f"Total Google runs: {total}")
    print()

    # Count by status
    status_counts = {}
    for run in google_runs:
        status = run.get('status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1

    print("Current status breakdown:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status:12s}: {count:4d}")
    print()

    # Show sample of what will be reset
    print("Sample runs that will be reset (first 5):")
    for i, run in enumerate(google_runs[:5], 1):
        print(f"\n{i}. Run ID: {run['run_id'][:16]}...")
        print(f"   Product:    {run.get('product_id', 'unknown')}")
        print(f"   Material:   {run.get('material_type', 'unknown')}")
        print(f"   Temperature: {run.get('temperature', 'unknown')}")
        print(f"   Status:     {run.get('status', 'unknown')}")
        print(f"   Tokens:     {run.get('total_tokens', '0')}")
        print(f"   Day:        {run.get('scheduled_day_of_week', 'unknown')}")
        print(f"   Time:       {run.get('time_of_day_label', 'unknown')}")

    if total > 5:
        print(f"\n... and {total - 5} more Google runs")

    print()
    print("=" * 80)


def reset_google_runs(experiments: List[Dict], dry_run: bool = True) -> List[Dict]:
    """Reset Google runs to pending.

    Args:
        experiments: All experiments from CSV
        dry_run: If True, don't modify data (just show what would happen)

    Returns:
        Updated experiments list (if not dry_run)
    """
    if dry_run:
        print("\n[DRY RUN MODE - No changes will be made]")
        print()

    reset_count = 0
    updated_experiments = []

    for exp in experiments:
        if exp.get('engine') == 'google':
            # This is a Google run - reset it
            reset_count += 1

            # Set status to pending
            exp['status'] = 'pending'

            # Clear execution metadata
            for col in COLUMNS_TO_CLEAR:
                if col in exp:
                    exp[col] = ''

            if not dry_run and reset_count <= 3:
                print(f"Reset: {exp['run_id'][:16]}... | {exp['product_id']} | {exp['material_type']}")

        updated_experiments.append(exp)

    print()
    print(f"Total Google runs reset: {reset_count}")
    print()

    if dry_run:
        print("⚠️  DRY RUN - No files were modified")
        print("Run with --execute to actually reset the runs")
    else:
        print("✓ Google runs have been reset to pending")

    return updated_experiments


def save_experiments(experiments: List[Dict], backup: bool = True):
    """Save updated experiments.csv.

    Args:
        experiments: Updated experiments list
        backup: If True, create backup first
    """
    if backup:
        # Create backup
        import shutil
        shutil.copy2(EXPERIMENTS_CSV, BACKUP_CSV)
        print(f"✓ Backup created: {BACKUP_CSV}")

    # Write updated CSV
    if not experiments:
        print("⚠️  No experiments to save")
        return

    # Get fieldnames from first row
    fieldnames = list(experiments[0].keys())

    with open(EXPERIMENTS_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(experiments)

    print(f"✓ Updated experiments saved: {EXPERIMENTS_CSV}")


def main():
    parser = argparse.ArgumentParser(
        description='Reset Google/Gemini runs to pending for rerun'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what will be reset without making changes'
    )
    parser.add_argument(
        '--execute',
        action='store_true',
        help='Actually reset the runs (creates backup first)'
    )
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("Error: Must specify either --dry-run or --execute")
        print()
        print("Usage:")
        print("  python scripts/reset_gemini_runs.py --dry-run    # Preview changes")
        print("  python scripts/reset_gemini_runs.py --execute    # Apply changes")
        return

    # Load experiments
    experiments = load_experiments()
    print(f"✓ Loaded {len(experiments)} experiments from {EXPERIMENTS_CSV}")
    print()

    # Find Google runs
    google_runs = find_google_runs(experiments)

    # Show analysis
    analyze_google_runs(google_runs)

    # Ask for confirmation if executing
    if args.execute:
        print()
        print("=" * 80)
        print("⚠️  WARNING: This will modify experiments.csv")
        print("=" * 80)
        print()
        print(f"- {len(google_runs)} Google runs will be reset to 'pending'")
        print(f"- Execution metadata will be cleared (tokens, timestamps, etc.)")
        print(f"- Matrix randomization will be preserved (run_id, product, temp, etc.)")
        print(f"- Backup will be created: {BACKUP_CSV}")
        print()
        response = input("Continue? [y/N]: ")

        if response.lower() != 'y':
            print("Aborted.")
            return

    # Reset runs
    updated_experiments = reset_google_runs(experiments, dry_run=args.dry_run)

    # Save if executing
    if args.execute:
        print()
        save_experiments(updated_experiments, backup=True)
        print()
        print("=" * 80)
        print("✓ RESET COMPLETE")
        print("=" * 80)
        print()
        print("Next steps:")
        print("1. Update config.py: DEFAULT_MAX_TOKENS = 10000")
        print("2. Run: python -m runner.run_job batch --engine google")


if __name__ == "__main__":
    main()
