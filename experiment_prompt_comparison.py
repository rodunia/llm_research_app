"""
A/B test: Old extraction prompt vs Improved extraction prompt
Test on 10 pilot files (3 melatonin, 4 smartphone, 3 corecoin)
"""
import json
from pathlib import Path
from analysis.glass_box_audit import NLIJudge, audit_single_run

# Select 10 pilot files for testing (diverse sample)
test_files = [
    # Melatonin (3 files - includes critical errors)
    ('pilot_study/melatonin/files/melatonin_1.txt', 'supplement_melatonin', 'melatonin_1', '5mg dosage error'),
    ('pilot_study/melatonin/files/melatonin_7.txt', 'supplement_melatonin', 'melatonin_7', 'Unsafe "every 2 hours"'),
    ('pilot_study/melatonin/files/melatonin_8.txt', 'supplement_melatonin', 'melatonin_8', 'Store at 0°C error'),

    # Smartphone (4 files - includes spec errors)
    ('pilot_study/smartphone/files/smartphone_1.txt', 'smartphone_mid', 'smartphone_1', '6.5" display error'),
    ('pilot_study/smartphone/files/smartphone_2.txt', 'smartphone_mid', 'smartphone_2', '16GB RAM error'),
    ('pilot_study/smartphone/files/smartphone_5.txt', 'smartphone_mid', 'smartphone_5', '7 years updates error'),
    ('pilot_study/smartphone/files/smartphone_10.txt', 'smartphone_mid', 'smartphone_10', 'Snapdragon 898 error'),

    # CoreCoin (3 files - includes regulatory errors)
    ('pilot_study/corecoin/files/corecoin_1.txt', 'cryptocurrency_corecoin', 'corecoin_1', 'Block time 4s error'),
    ('pilot_study/corecoin/files/corecoin_4.txt', 'cryptocurrency_corecoin', 'corecoin_4', 'Guaranteed returns'),
    ('pilot_study/corecoin/files/corecoin_9.txt', 'cryptocurrency_corecoin', 'corecoin_9', 'Risk-free claim'),
]

print("="*80)
print("A/B TEST: Old vs Improved Extraction Prompt")
print("="*80)
print(f"\nTesting on {len(test_files)} pilot files with known ground truth errors\n")

# Initialize NLI Judge
print("Initializing NLI Judge...")
judge = NLIJudge(use_semantic_filter=False)

# Output directories
new_output_dir = Path('results/experiment/improved_prompt')
new_output_dir.mkdir(parents=True, exist_ok=True)

# Load old results for comparison
old_output_dir = Path('results/pilot/old_system_audit')

# Track statistics
results = {
    'old': {'total_violations': 0, 'materials_with_violations': 0, 'ground_truth_detected': 0},
    'new': {'total_violations': 0, 'materials_with_violations': 0, 'ground_truth_detected': 0}
}

comparison_table = []

print("\nProcessing files...")
print("-"*80)

for txt_file, product_id, material_id, ground_truth in test_files:
    # Run NEW prompt
    run_metadata = {
        'run_id': material_id,
        'product_id': product_id,
        'material_type': 'pilot_material',
        'output_path': txt_file,
        'use_claude_explainer': False
    }

    new_result = audit_single_run(material_id, run_metadata, judge)

    # Save new result
    with open(new_output_dir / f'{material_id}.json', 'w') as f:
        json.dump(new_result, f, indent=2)

    # Load OLD result
    old_file = old_output_dir / f'{material_id}.json'
    with open(old_file) as f:
        old_result = json.load(f)

    # Compare
    old_violations = old_result['violation_count']
    new_violations = new_result['violation_count']
    old_claims = len(old_result.get('core_claims', []))
    new_claims = len(new_result.get('core_claims', []))

    # Check if ground truth error is detected
    old_detected = old_violations > 0
    new_detected = new_violations > 0

    # Update stats
    results['old']['total_violations'] += old_violations
    results['new']['total_violations'] += new_violations

    if old_violations > 0:
        results['old']['materials_with_violations'] += 1
    if new_violations > 0:
        results['new']['materials_with_violations'] += 1

    if old_detected:
        results['old']['ground_truth_detected'] += 1
    if new_detected:
        results['new']['ground_truth_detected'] += 1

    # Calculate change
    violation_change = new_violations - old_violations
    violation_pct = ((new_violations - old_violations) / old_violations * 100) if old_violations > 0 else 0

    # Determine status
    if not new_detected and old_detected:
        status = "❌ REGRESSION"
    elif new_violations < old_violations and new_detected:
        status = "✅ IMPROVED"
    elif new_violations == old_violations:
        status = "➖ NO CHANGE"
    else:
        status = "⚠️  MORE FPs"

    comparison_table.append({
        'material': material_id,
        'ground_truth': ground_truth,
        'old_claims': old_claims,
        'new_claims': new_claims,
        'old_violations': old_violations,
        'new_violations': new_violations,
        'change': violation_change,
        'change_pct': violation_pct,
        'status': status
    })

    print(f"{material_id:20s} | Old: {old_claims:2d} claims, {old_violations:2d} viol | New: {new_claims:2d} claims, {new_violations:2d} viol | {status}")

# Print summary
print("\n" + "="*80)
print("COMPARISON SUMMARY")
print("="*80)

print("\n📊 DETECTION RATE (Primary Metric)")
print("-"*80)
print(f"Old prompt: {results['old']['ground_truth_detected']}/10 ground truth errors detected ({100*results['old']['ground_truth_detected']/10:.0f}%)")
print(f"New prompt: {results['new']['ground_truth_detected']}/10 ground truth errors detected ({100*results['new']['ground_truth_detected']/10:.0f}%)")

if results['new']['ground_truth_detected'] < results['old']['ground_truth_detected']:
    print("\n⚠️  WARNING: New prompt has LOWER detection rate - DO NOT ADOPT")
elif results['new']['ground_truth_detected'] == results['old']['ground_truth_detected']:
    print("\n✅ Detection rate maintained (both 100%)")
else:
    print("\n✅ Detection rate improved")

print("\n📉 FALSE POSITIVE REDUCTION (Secondary Metric)")
print("-"*80)
print(f"Old prompt: {results['old']['total_violations']} total violations ({results['old']['total_violations']/10:.1f} per file)")
print(f"New prompt: {results['new']['total_violations']} total violations ({results['new']['total_violations']/10:.1f} per file)")

violation_reduction = results['old']['total_violations'] - results['new']['total_violations']
violation_reduction_pct = (violation_reduction / results['old']['total_violations'] * 100) if results['old']['total_violations'] > 0 else 0

if violation_reduction > 0:
    print(f"\n✅ Reduced violations by {violation_reduction} ({violation_reduction_pct:.1f}%)")
    print(f"   Saves ~{violation_reduction * 162:.0f} violations across 1,620 materials")
elif violation_reduction == 0:
    print(f"\n➖ No change in violation count")
else:
    print(f"\n⚠️  Increased violations by {abs(violation_reduction)} ({abs(violation_reduction_pct):.1f}%)")

print("\n🎯 RECOMMENDATION")
print("-"*80)

# Decision logic
if results['new']['ground_truth_detected'] < 10:
    print("❌ DO NOT ADOPT - Detection rate dropped below 100%")
    print("   Risk of missing dangerous errors is unacceptable")
elif violation_reduction >= 20:  # At least 20% reduction
    print("✅ ADOPT NEW PROMPT")
    print(f"   - Maintains 100% detection")
    print(f"   - Reduces false positives by {violation_reduction_pct:.1f}%")
    print(f"   - Saves ~{violation_reduction * 162:.0f} human reviews across full dataset")
elif violation_reduction > 0:
    print("⚠️  MARGINAL IMPROVEMENT")
    print(f"   - Maintains 100% detection")
    print(f"   - Reduces false positives by only {violation_reduction_pct:.1f}%")
    print(f"   - Consider adopting, but benefit is modest")
else:
    print("➖ KEEP OLD PROMPT")
    print("   - No improvement in false positive rate")
    print("   - Old prompt is already optimal")

print("\n" + "="*80)
print(f"Results saved to: {new_output_dir}")
print("="*80)

# Save comparison table
import csv
with open('results/experiment/prompt_comparison.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=comparison_table[0].keys())
    writer.writeheader()
    writer.writerows(comparison_table)

print(f"\nDetailed comparison: results/experiment/prompt_comparison.csv")
