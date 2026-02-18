#!/usr/bin/env python3
"""Register uploaded test files in experiments.csv"""

import csv
from pathlib import Path

# Define file mappings
file_mappings = []

# CoreCoin files (1.txt - 10.txt)
for i in range(1, 11):
    file_mappings.append({
        'filename': f'{i}.txt',
        'product_id': 'cryptocurrency_corecoin',
        'run_id': f'user_corecoin_{i}'
    })

# Smartphone files (s1.txt - s10.txt)
for i in range(1, 11):
    file_mappings.append({
        'filename': f's{i}.txt',
        'product_id': 'smartphone_mid',
        'run_id': f'user_smartphone_{i}'
    })

# Melatonin FAQ files
melatonin_files = [
    'FAQ for Melatonin Tablets 3 mg 1.txt',
    'FAQ for Melatonin Tablets 3 mg  2.txt',  # Note: extra space in filename
    'FAQ for Melatonin Tablets 3 mg 3.txt',
    'FAQ for Melatonin Tablets 3 mg 4.txt',
    'FAQ for Melatonin Tablets 3 mg 5.txt',
    'FAQ for Melatonin Tablets 3 mg 6.txt',
    'FAQ for Melatonin Tablets 3 mg 7.txt',
    'FAQ for Melatonin Tablets 3 mg 8.txt',
    'FAQ for Melatonin Tablets 3 mg 9.txt',
    'FAQ for Melatonin Tablets 3 mg 10.txt',
]

for i, filename in enumerate(melatonin_files, 1):
    file_mappings.append({
        'filename': filename,
        'product_id': 'supplement_melatonin',
        'run_id': f'user_melatonin_{i}'
    })

# Read existing experiments.csv
experiments_csv = Path('results/experiments.csv')
existing_run_ids = set()

with open(experiments_csv, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        existing_run_ids.add(row['run_id'])

# Add new entries
added = 0
skipped = 0

with open(experiments_csv, 'a') as f:
    for mapping in file_mappings:
        run_id = mapping['run_id']

        if run_id in existing_run_ids:
            print(f"⊘ Skipped (already exists): {run_id}")
            skipped += 1
            continue

        # Check if file exists
        file_path = Path('outputs') / mapping['filename']
        if not file_path.exists():
            print(f"✗ File not found: {mapping['filename']}")
            continue

        # Write CSV row
        f.write(f"{run_id},{mapping['product_id']},faq.j2,user_upload,manual,0.0,1,False,outputs/{mapping['filename']},completed,,,,0,0,0,\n")
        print(f"✓ Added: {run_id} → {mapping['filename']}")
        added += 1

print(f"\n{'='*60}")
print(f"Summary: {added} files added, {skipped} skipped")
print(f"{'='*60}")
