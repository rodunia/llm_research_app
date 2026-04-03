"""
Detailed validation: Check if SPECIFIC ground truth errors were detected
by Glass Box vs GPT-4o freeform
"""
import pandas as pd
import json
from pathlib import Path

# Ground truth errors from GROUND_TRUTH_ERRORS.md
# Each entry: [error description, [keywords to search for in detected claims]]
GROUND_TRUTH = {
    'smartphone': {
        1: {'desc': 'Display size 6.5" instead of 6.3"', 'keywords': ['6.5', 'display', 'inch']},
        2: {'desc': 'Main camera 48 MP instead of 50 MP', 'keywords': ['48', 'mp', 'camera', 'main']},
        3: {'desc': 'Storage 1TB option (max is 512 GB)', 'keywords': ['1tb', '1 tb', 'terabyte']},
        4: {'desc': 'RAM 16 GB option (max is 12 GB)', 'keywords': ['16', 'gb', 'ram']},
        5: {'desc': 'Wi-Fi 7 (only has Wi-Fi 6/6E)', 'keywords': ['wi-fi 7', 'wifi 7', 'wi fi 7']},
        6: {'desc': 'Wireless charging 10W (not supported)', 'keywords': ['wireless charging', '10w', 'qi']},
        7: {'desc': 'Hourly antivirus (not mentioned)', 'keywords': ['antivirus', 'hourly', 'virus']},
        8: {'desc': 'Offline AI video rendering (not supported)', 'keywords': ['offline ai', 'ai video', 'video rendering']},
        9: {'desc': 'Fast charging 60W (actual 30-45W)', 'keywords': ['60w', '60 w']},
        10: {'desc': 'External SSD via SIM tray (not supported)', 'keywords': ['external ssd', 'sim tray', 'ssd']},
    },
    'melatonin': {
        1: {'desc': 'Dosage 5 mg instead of 3 mg', 'keywords': ['5 mg', '5mg']},
        2: {'desc': '100 tablets instead of 60', 'keywords': ['100 tablets', '100 tablet']},
        3: {'desc': 'Vegan + fish-derived contradiction', 'keywords': ['fish', 'fish-derived', 'marine']},
        4: {'desc': 'Gluten 0mg + wheat traces contradiction', 'keywords': ['wheat', 'gluten']},
        5: {'desc': 'Lead <5 ppm instead of <0.5 mcg/serving', 'keywords': ['5 ppm', '<5 ppm', 'lead']},
        6: {'desc': 'Storage temp 0°C (correct is 15-30°C)', 'keywords': ['0°c', '0 °c', '0 degree']},
        7: {'desc': 'Every 2 hours instead of before bed', 'keywords': ['2 hours', 'every 2', 'two hours']},
        8: {'desc': 'FDA approved (supplements not FDA approved)', 'keywords': ['fda approved', 'fda-approved']},
        9: {'desc': 'Avoid if over 18 (should be under 18)', 'keywords': ['over 18', 'above 18']},
        10: {'desc': 'Permanent drowsiness (temporary)', 'keywords': ['permanent', 'permanently']},
    },
    'corecoin': {
        1: {'desc': 'Block time ~4 seconds instead of ~5 seconds', 'keywords': ['4 second', '~4 second']},
        2: {'desc': "Light validators don't stake (they must)", 'keywords': ['light validator', 'without stak', "don't stake", 'no stak']},
        3: {'desc': 'Trading pauses for maintenance (24/7 trading)', 'keywords': ['trading pause', 'maintenance', 'pause', 'downtime']},
        4: {'desc': 'Automatic key-sharding (manual backup)', 'keywords': ['automatic', 'key-shard', 'auto backup']},
        5: {'desc': 'Gas-free execution (gas fees required)', 'keywords': ['gas-free', 'gas free', 'zero-fee', 'no gas', 'free execution']},
        6: {'desc': 'Auto-pass without quorum (requires quorum)', 'keywords': ['without quorum', 'auto-pass', 'no quorum']},
        7: {'desc': 'Cross-chain simulate (not supported)', 'keywords': ['cross-chain', 'cross chain', 'crosschain']},
        8: {'desc': 'Unstaking penalty reduces historical rewards', 'keywords': ['unstaking penalty', 'historical reward', 'past reward']},
        9: {'desc': 'Validator inactivity locks governance rights', 'keywords': ['inactivity', 'inactive', 'locks governance', 'governance lock']},
        10: {'desc': 'Region-based fixed staking rates', 'keywords': ['region-based', 'region based', 'fixed rate', 'regional']},
    }
}

def check_detection_in_csv(file_path, ground_truth_entry):
    """Check if ground truth error appears in detected violations"""
    if not Path(file_path).exists():
        return False, "File not found"

    df = pd.read_csv(file_path)
    violations = df[df['Status'] == 'FAIL']

    # Combine all violation text (claims + rules)
    all_text = ' '.join(violations['Extracted_Claim'].astype(str).tolist() +
                       violations['Violated_Rule'].astype(str).tolist()).lower()

    # Check if ANY keyword matches
    keywords = ground_truth_entry['keywords']
    matched = []
    for kw in keywords:
        if kw.lower() in all_text:
            matched.append(kw)

    return len(matched) > 0, matched

def check_detection_in_json(file_path, ground_truth_entry):
    """Check if ground truth error appears in GPT-4o baseline JSON results"""
    if not Path(file_path).exists():
        return False, []

    with open(file_path, 'r') as f:
        data = json.load(f)

    # Combine all error text from JSON
    all_text = ''
    if 'errors' in data:
        for err in data['errors']:
            all_text += ' ' + str(err.get('claim', ''))
            all_text += ' ' + str(err.get('explanation', ''))
            all_text += ' ' + str(err.get('correct_value', ''))
            all_text += ' ' + str(err.get('error_type', ''))

    all_text = all_text.lower()

    # Check if ANY keyword matches
    keywords = ground_truth_entry['keywords']
    matched = []
    for kw in keywords:
        if kw.lower() in all_text:
            matched.append(kw)

    return len(matched) > 0, matched

# Analyze all 30 files
results = []

for product in ['smartphone', 'melatonin', 'corecoin']:
    for file_num in range(1, 11):
        gt_entry = GROUND_TRUTH[product][file_num]

        # Check Glass Box detection
        glass_box_file = f'results/errors_analysis/glass_box/errors_{product}_{file_num}.csv'
        gb_detected, gb_keywords = check_detection_in_csv(glass_box_file, gt_entry)

        # Check GPT-4o OLD baseline detection (Feb 25, with old prompt)
        gpt_file = f'results/gpt4o_baseline/{product}_{file_num}.json'
        gpt_detected, gpt_keywords = check_detection_in_json(gpt_file, gt_entry)

        results.append({
            'product': product,
            'file_num': file_num,
            'error_description': gt_entry['desc'],
            'glass_box_detected': '✓' if gb_detected else '✗',
            'glass_box_keywords': ', '.join(gb_keywords) if gb_detected else '',
            'gpt4o_detected': '✓' if gpt_detected else '✗',
            'gpt4o_keywords': ', '.join(gpt_keywords) if gpt_detected else '',
        })

df_results = pd.DataFrame(results)

# Print detailed table
print("=== DETAILED GROUND TRUTH VALIDATION ===\n")
for product in ['smartphone', 'melatonin', 'corecoin']:
    print(f"\n### {product.upper()} ###")
    df_prod = df_results[df_results['product'] == product]
    print(df_prod[['file_num', 'error_description', 'glass_box_detected', 'gpt4o_detected']].to_string(index=False))

# Summary statistics
print("\n\n=== SUMMARY ===")
for product in ['smartphone', 'melatonin', 'corecoin']:
    df_prod = df_results[df_results['product'] == product]
    gb_count = (df_prod['glass_box_detected'] == '✓').sum()
    gpt_count = (df_prod['gpt4o_detected'] == '✓').sum()
    print(f"{product:12} | Glass Box: {gb_count}/10 | GPT-4o: {gpt_count}/10")

print("\nOverall:")
gb_total = (df_results['glass_box_detected'] == '✓').sum()
gpt_total = (df_results['gpt4o_detected'] == '✓').sum()
print(f"Glass Box: {gb_total}/30 ({gb_total/30*100:.1f}%)")
print(f"GPT-4o (old prompt):    {gpt_total}/30 ({gpt_total/30*100:.1f}%)")

# Save to CSV for graphing
df_results.to_csv('results/errors_analysis/ground_truth_validation_detailed.csv', index=False)
print("\n✓ Saved detailed results to: results/errors_analysis/ground_truth_validation_detailed.csv")
