"""
Run old glass_box_audit.py system on 30 pilot files.
This validates the old system still achieves 60-70% detection rate.
"""
import os
import json
import sys
from pathlib import Path
from analysis.glass_box_audit import NLIJudge, audit_single_run

# Pilot directories
pilot_dirs = [
    ('pilot_study/melatonin/files', 'supplement_melatonin'),
    ('pilot_study/corecoin/files', 'cryptocurrency_corecoin'),
    ('pilot_study/smartphone/files', 'smartphone_mid')
]

# Output directory
output_dir = Path('results/pilot/old_system_audit')
output_dir.mkdir(parents=True, exist_ok=True)

# Initialize NLI Judge (old system)
print("Initializing old system (glass_box_audit.py)...")
judge = NLIJudge(use_semantic_filter=False)

# Process all 30 pilot files
total_processed = 0
total_violations = 0
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

        # Create run metadata (mimicking experiments.csv structure)
        run_metadata = {
            'run_id': material_id,
            'product_id': product_id,
            'material_type': 'pilot_material',
            'output_path': str(txt_file)  # Pass explicit path
        }

        try:
            print(f"  Auditing {material_id}...", end=' ', flush=True)

            # Run old system audit
            result = audit_single_run(material_id, run_metadata, judge)

            # Save result
            output_path = output_dir / f"{material_id}.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)

            status = result.get('status', 'UNKNOWN')
            violations = result.get('violation_count', 0)
            claims = len(result.get('core_claims', []))

            print(f"✓ {status} ({claims} claims, {violations} violations)")

            total_processed += 1
            total_violations += violations

        except Exception as e:
            print(f"✗ Error: {str(e)[:100]}")
            total_errors += 1

print(f"\n{'='*60}")
print(f"Total processed: {total_processed}")
print(f"Total violations detected: {total_violations}")
print(f"Total errors: {total_errors}")
print(f"Detection rate: {total_violations}/30 = {100*total_violations/30:.1f}%")
print(f"Output directory: {output_dir}")
print(f"\n{'='*60}")
print("VALIDATION:")
print(f"  Expected: 60-70% detection (18-21 violations)")
print(f"  Actual: {total_violations}/30 = {100*total_violations/30:.1f}%")
if total_violations >= 18:
    print(f"  ✅ PASSED - Old system validated")
else:
    print(f"  ⚠️  FAILED - Detection rate below 60%")
