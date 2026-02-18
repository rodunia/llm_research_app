#!/usr/bin/env python3
"""Helper script to test Glass Box Audit on custom marketing materials.

Usage:
    python scripts/test_manual_claim.py --product smartphone_mid --file my_test.txt
    python scripts/test_manual_claim.py --product supplement_melatonin --content "Your marketing text here"
"""

import argparse
import subprocess
import sys
from pathlib import Path
import uuid
import csv

def main():
    parser = argparse.ArgumentParser(description='Test Glass Box Audit on custom marketing content')
    parser.add_argument('--product', required=True, choices=['smartphone_mid', 'cryptocurrency_corecoin', 'supplement_melatonin'],
                       help='Product ID to test against')
    parser.add_argument('--file', type=str, help='Path to text file with marketing content')
    parser.add_argument('--content', type=str, help='Direct marketing content (alternative to --file)')
    parser.add_argument('--material', default='digital_ad.j2', help='Material type (default: digital_ad.j2)')

    args = parser.parse_args()

    # Validate inputs
    if not args.file and not args.content:
        print("Error: Must provide either --file or --content")
        sys.exit(1)

    if args.file and args.content:
        print("Error: Cannot provide both --file and --content")
        sys.exit(1)

    # Read content
    if args.file:
        content_path = Path(args.file)
        if not content_path.exists():
            print(f"Error: File not found: {args.file}")
            sys.exit(1)
        content = content_path.read_text(encoding='utf-8')
        test_name = f"test_{content_path.stem}"
    else:
        content = args.content
        test_name = f"test_{uuid.uuid4().hex[:8]}"

    # Create output file
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(exist_ok=True)
    output_file = outputs_dir / f"{test_name}.txt"
    output_file.write_text(content, encoding='utf-8')

    print(f"Created test file: {output_file}")

    # Add to experiments.csv
    experiments_csv = Path("results/experiments.csv")

    # Check if already exists
    with open(experiments_csv, 'r') as f:
        reader = csv.DictReader(f)
        existing_ids = {row['run_id'] for row in reader}

    if test_name not in existing_ids:
        with open(experiments_csv, 'a') as f:
            f.write(f"{test_name},{args.product},{args.material},manual,manual,0.0,1,False,{output_file},completed,,,,0,0,0,\n")
        print(f"Added to experiments.csv: {test_name}")
    else:
        print(f"Already in experiments.csv: {test_name}")

    # Run Glass Box Audit
    print(f"\nRunning Glass Box Audit on {test_name}...\n")
    result = subprocess.run(
        [sys.executable, "-m", "analysis.glass_box_audit", "--run-id", test_name],
        env={'PYTHONPATH': '.', **subprocess.os.environ}
    )

    if result.returncode == 0:
        print(f"\n✅ Audit complete! Check results/final_audit_results.csv for violations")
        print(f"\nTo see violations:")
        print(f"  grep '{test_name}' results/final_audit_results.csv")
    else:
        print(f"\n❌ Audit failed with exit code {result.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    main()
