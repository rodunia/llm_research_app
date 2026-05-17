#!/usr/bin/env python3
"""
Reschedule Google/Gemini runs from March 17-23 to May 19-25, 2026.

Preserves exact day-of-week and time-of-day, just shifts the calendar week.

Usage:
  python scripts/reschedule_gemini_to_may.py --dry-run   # preview
  python scripts/reschedule_gemini_to_may.py --execute   # apply
"""

import csv
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# Paths
EXPERIMENTS_CSV = Path("results/experiments.csv")
BACKUP_CSV = Path("results/experiments_backup_before_may_reschedule.csv")

# Date mapping: April 13-19 → May 18-24
# Sunday April 13 → Sunday May 18
# Monday April 14 → Monday May 19
# etc.
DATE_SHIFT_DAYS = 35  # Number of days between April 13 and May 18


def parse_scheduled_datetime(dt_str):
    """Parse scheduled_datetime string."""
    if not dt_str or dt_str == '':
        return None
    # Format: 2026-03-17T19:38:00
    return datetime.fromisoformat(dt_str)


def shift_datetime(dt_str, days_shift):
    """Shift datetime by N days."""
    if not dt_str or dt_str == '':
        return ''

    dt = parse_scheduled_datetime(dt_str)
    if dt is None:
        return dt_str

    new_dt = dt + timedelta(days=days_shift)
    return new_dt.isoformat()


def reschedule_google_runs(experiments, dry_run=True):
    """Reschedule Google runs from March to May."""

    updated_count = 0
    updated_experiments = []

    for exp in experiments:
        if exp.get('engine') == 'google':
            old_datetime = exp.get('scheduled_datetime', '')

            if old_datetime:
                new_datetime = shift_datetime(old_datetime, DATE_SHIFT_DAYS)

                if not dry_run:
                    exp['scheduled_datetime'] = new_datetime

                updated_count += 1

                if updated_count <= 5:
                    old_dt = parse_scheduled_datetime(old_datetime)
                    new_dt = parse_scheduled_datetime(new_datetime)
                    print(f"  {exp['run_id'][:16]}...")
                    print(f"    Old: {old_dt.strftime('%A %Y-%m-%d %H:%M') if old_dt else 'None'}")
                    print(f"    New: {new_dt.strftime('%A %Y-%m-%d %H:%M') if new_dt else 'None'}")
                    print()

        updated_experiments.append(exp)

    return updated_experiments, updated_count


def main():
    parser = argparse.ArgumentParser(
        description='Reschedule Google runs from March to May'
    )
    parser.add_argument('--dry-run', action='store_true', help='Preview changes')
    parser.add_argument('--execute', action='store_true', help='Apply changes')
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        print("Error: Must specify --dry-run or --execute")
        return

    # Load experiments
    with open(EXPERIMENTS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        experiments = list(reader)

    print(f"✓ Loaded {len(experiments)} experiments")
    print()

    # Count Google runs
    google_runs = [e for e in experiments if e.get('engine') == 'google']
    print(f"Found {len(google_runs)} Google runs")
    print()

    if args.dry_run:
        print("[DRY RUN MODE - No changes will be made]")
        print()

    print("Rescheduling from April 13-19 → May 18-24 (shifted by 35 days)")
    print()
    print("Sample updates (first 5):")
    print()

    # Reschedule
    updated_experiments, updated_count = reschedule_google_runs(
        experiments,
        dry_run=args.dry_run
    )

    if updated_count > 5:
        print(f"... and {updated_count - 5} more")
    print()

    print(f"Total Google runs rescheduled: {updated_count}")
    print()

    # Save if executing
    if args.execute:
        print("=" * 80)
        print("⚠️  WARNING: This will modify experiments.csv")
        print("=" * 80)
        print()
        response = input("Continue? [y/N]: ")

        if response.lower() != 'y':
            print("Aborted.")
            return

        # Create backup
        import shutil
        shutil.copy2(EXPERIMENTS_CSV, BACKUP_CSV)
        print(f"✓ Backup created: {BACKUP_CSV}")

        # Save updated CSV
        fieldnames = list(updated_experiments[0].keys())
        with open(EXPERIMENTS_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(updated_experiments)

        print(f"✓ Updated experiments saved: {EXPERIMENTS_CSV}")
        print()
        print("✓ RESCHEDULE COMPLETE")
        print()
        print("Next step:")
        print("  python orchestrator.py run --time-of-day morning   # Tomorrow 8am")
    else:
        print("⚠️  DRY RUN - No files were modified")


if __name__ == "__main__":
    main()
