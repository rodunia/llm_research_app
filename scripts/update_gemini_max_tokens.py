#!/usr/bin/env python3
"""
Update max_tokens to 10000 for all Google/Gemini runs in experiments.csv

Usage:
  python scripts/update_gemini_max_tokens.py --dry-run   # preview
  python scripts/update_gemini_max_tokens.py --execute   # apply
"""

import csv
import argparse
from pathlib import Path

EXPERIMENTS_CSV = Path("results/experiments.csv")
BACKUP_CSV = Path("results/experiments_backup_before_token_update.csv")
NEW_MAX_TOKENS = 10000


def main():
    parser = argparse.ArgumentParser(description='Update max_tokens for Google runs')
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

    # Find Google runs and update max_tokens
    updated_count = 0
    for exp in experiments:
        if exp.get('engine') == 'google':
            old_max_tokens = exp.get('max_tokens', 'unknown')

            if not args.dry_run:
                exp['max_tokens'] = str(NEW_MAX_TOKENS)

            updated_count += 1

            if updated_count <= 5:
                print(f"  {exp['run_id'][:16]}... | {exp['product_id']}")
                print(f"    Old max_tokens: {old_max_tokens}")
                print(f"    New max_tokens: {NEW_MAX_TOKENS}")
                print()

    if updated_count > 5:
        print(f"... and {updated_count - 5} more")
    print()

    print(f"Total Google runs updated: {updated_count}")
    print()

    if args.dry_run:
        print("⚠️  DRY RUN - No files were modified")
        return

    # Execute
    print("=" * 80)
    print("⚠️  WARNING: This will modify experiments.csv")
    print("=" * 80)
    print()
    response = input("Continue? [y/N]: ")

    if response.lower() != 'y':
        print("Aborted.")
        return

    # Backup
    import shutil
    shutil.copy2(EXPERIMENTS_CSV, BACKUP_CSV)
    print(f"✓ Backup created: {BACKUP_CSV}")

    # Save
    fieldnames = list(experiments[0].keys())
    with open(EXPERIMENTS_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(experiments)

    print(f"✓ Updated experiments saved: {EXPERIMENTS_CSV}")
    print()
    print("✓ UPDATE COMPLETE")
    print()
    print("Next step:")
    print("  python orchestrator.py temporal --experiment-start 2026-05-18T00:00:00 --session-id gemini_rerun")


if __name__ == "__main__":
    main()
