"""
Quick script to run GPT-4o on 30 existing pilot materials
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Import after env is loaded
from analysis.gpt4o_grey_area_judge import judge_marketing_material

# Pilot directories
pilot_dirs = [
    ('pilot_study/melatonin/files', 'supplement_melatonin'),
    ('pilot_study/corecoin/files', 'cryptocurrency_corecoin'),
    ('pilot_study/smartphone/files', 'smartphone_mid')
]

# Output directory
output_dir = Path('results/pilot/gpt4o_compliance')
output_dir.mkdir(parents=True, exist_ok=True)

total_processed = 0
total_errors = 0

for dir_path, product_id in pilot_dirs:
    files_dir = Path(dir_path)

    if not files_dir.exists():
        print(f"Directory not found: {files_dir}")
        continue

    txt_files = sorted(files_dir.glob('*.txt'))
    print(f"\nProcessing {len(txt_files)} files from {product_id}...")

    for txt_file in txt_files:
        material_id = txt_file.stem

        try:
            # Read material
            with open(txt_file, 'r', encoding='utf-8') as f:
                material_text = f.read()

            # Run GPT-4o analysis
            print(f"  Analyzing {material_id}...", end=' ', flush=True)
            result = judge_marketing_material(
                material_text=material_text,
                product_id=product_id,
                material_id=material_id
            )

            # Save result
            output_path = output_dir / f"{material_id}.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)

            status = result.get('overall_status', 'UNKNOWN')
            findings = result.get('finding_count', 0)
            claims = len(result.get('extracted_claims', []))

            print(f"✓ {status} ({claims} claims, {findings} findings)")
            total_processed += 1

        except Exception as e:
            print(f"✗ Error: {str(e)[:100]}")
            total_errors += 1

print(f"\n{'='*60}")
print(f"Total processed: {total_processed}")
print(f"Total errors: {total_errors}")
print(f"Output directory: {output_dir}")
