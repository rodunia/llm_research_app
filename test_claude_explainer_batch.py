"""
Test Claude explainer on 5 pilot files (one from each product category + 2 extra)
"""
import json
from pathlib import Path
from analysis.glass_box_audit import NLIJudge, audit_single_run

# Test files with known ground truth errors
test_files = [
    ('pilot_study/melatonin/files/melatonin_1.txt', 'supplement_melatonin', 'melatonin_1', '5mg dosage error'),
    ('pilot_study/melatonin/files/melatonin_7.txt', 'supplement_melatonin', 'melatonin_7', 'Unsafe "every 2 hours" dosage'),
    ('pilot_study/smartphone/files/smartphone_1.txt', 'smartphone_mid', 'smartphone_1', '6.5" display error'),
    ('pilot_study/corecoin/files/corecoin_1.txt', 'cryptocurrency_corecoin', 'corecoin_1', 'Block time 4s error'),
    ('pilot_study/smartphone/files/smartphone_2.txt', 'smartphone_mid', 'smartphone_2', '16GB RAM error'),
]

print("Initializing NLI Judge...")
judge = NLIJudge(use_semantic_filter=False)

output_dir = Path('results/pilot/claude_explainer_test')
output_dir.mkdir(parents=True, exist_ok=True)

print(f"\nTesting Claude explainer on {len(test_files)} pilot files...")
print(f"{'='*80}\n")

total_violations = 0
total_critical = 0

for txt_file, product_id, material_id, ground_truth in test_files:
    run_metadata = {
        'run_id': material_id,
        'product_id': product_id,
        'material_type': 'pilot_material',
        'output_path': txt_file,
        'use_claude_explainer': True
    }

    print(f"Processing {material_id} (Ground truth: {ground_truth})...")
    result = audit_single_run(material_id, run_metadata, judge)

    # Save full result
    with open(output_dir / f'{material_id}.json', 'w') as f:
        json.dump(result, f, indent=2)

    # Count violations by severity
    violations = result.get('violations', [])
    critical_count = sum(1 for v in violations if v.get('severity_assessment') == 'CRITICAL')
    high_count = sum(1 for v in violations if v.get('severity_assessment') == 'HIGH')

    total_violations += len(violations)
    total_critical += critical_count

    print(f"  ✓ {len(violations)} violations ({critical_count} CRITICAL, {high_count} HIGH)")

    # Show most critical violation
    critical_violations = [v for v in violations if v.get('severity_assessment') == 'CRITICAL']
    if critical_violations:
        v = critical_violations[0]
        print(f"    CRITICAL: {v['claim'][:60]}...")
        print(f"    Explanation: {v.get('claude_explanation', '')[:100]}...")
    print()

print(f"{'='*80}")
print(f"SUMMARY:")
print(f"  Total violations: {total_violations}")
print(f"  Critical violations: {total_critical}")
print(f"  Output: {output_dir}")
print(f"{'='*80}")
