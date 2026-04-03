#!/usr/bin/env python3
"""
Count how many SPECIFIC ground truth errors were detected in each file
by checking if Glass Box/GPT-4o outputs contain the error keywords
"""

import csv
from pathlib import Path

# Ground truth errors with keywords for matching
GROUND_TRUTH = {
    'smartphone': {
        1: {'desc': 'Display 6.5"', 'keywords': ['6.5', 'display', 'inch']},
        2: {'desc': 'Camera 48 MP', 'keywords': ['48', 'mp', 'camera']},
        3: {'desc': 'Storage 1TB', 'keywords': ['1 tb', '1tb']},
        4: {'desc': 'RAM 16 GB', 'keywords': ['16', 'gb', 'ram']},
        5: {'desc': 'Wi-Fi 7', 'keywords': ['wi-fi 7', 'wifi 7', 'wifi7']},
        6: {'desc': 'Wireless charging', 'keywords': ['wireless charging', 'qi']},
        7: {'desc': 'Hourly antivirus', 'keywords': ['hourly', 'antivirus']},
        8: {'desc': 'Offline AI video', 'keywords': ['offline ai', 'video rendering']},
        9: {'desc': 'Fast charging 60W', 'keywords': ['60w', '60 w']},
        10: {'desc': 'External SSD', 'keywords': ['external ssd', 'sim tray', 'ssd']},
    },
    'melatonin': {
        1: {'desc': 'Dosage 5 mg', 'keywords': ['5 mg', '5mg']},
        2: {'desc': '100 tablets', 'keywords': ['100 tablets', '100 tablet']},
        3: {'desc': 'Vegan + fish', 'keywords': ['fish', 'fish-derived']},
        4: {'desc': 'Gluten + wheat', 'keywords': ['wheat', 'gluten']},
        5: {'desc': 'Lead 5 ppm', 'keywords': ['5 ppm', 'lead']},
        6: {'desc': 'Storage 0°C', 'keywords': ['0°c', '0 °c', '0 degree', 'freeze']},
        7: {'desc': 'Every 2 hours', 'keywords': ['2 hours', 'every 2', 'two hours']},
        8: {'desc': 'FDA approved', 'keywords': ['fda-approved', 'fda approved', 'approved by the fda']},
        9: {'desc': 'Over 18', 'keywords': ['over 18', 'over eighteen']},
        10: {'desc': 'Permanent drowsiness', 'keywords': ['permanent drowsiness', 'cause permanent']},
    },
    'corecoin': {
        1: {'desc': 'Block time 4s', 'keywords': ['4 second', '~4 second', '4s']},
        2: {'desc': 'Light validators', 'keywords': ['light validator', 'light-validator']},
        3: {'desc': 'Trading pauses', 'keywords': ['trading pause', 'maintenance', 'pause']},
        4: {'desc': 'Automatic key-sharding', 'keywords': ['automatic', 'key-shard']},
        5: {'desc': 'Gas-free', 'keywords': ['gas-free', 'zero-fee', 'without gas']},
        6: {'desc': 'Auto-pass quorum', 'keywords': ['auto-pass', 'automatically pass']},
        7: {'desc': 'Cross-chain', 'keywords': ['cross-chain', 'cross chain']},
        8: {'desc': 'Unstaking penalty', 'keywords': ['historical reward', 'unstaking']},
        9: {'desc': 'Validator inactivity', 'keywords': ['inactivity', 'governance', 'lock']},
        10: {'desc': 'Region-based staking', 'keywords': ['regional', 'region-based']},
    }
}

def check_glass_box_file(product, file_num):
    """Check how many errors Glass Box detected in this file"""
    csv_path = Path(f'results/errors_analysis/glass_box/errors_{product}_{file_num}.csv')
    if not csv_path.exists():
        return 0

    detected_count = 0
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        all_claims = ' '.join([row['Extracted_Claim'].lower() for row in reader])

    # Check each error that should be in this file (errors 1 to file_num)
    for error_num in range(1, file_num + 1):
        error_info = GROUND_TRUTH[product][error_num]
        keywords = error_info['keywords']

        # Check if any keyword matches
        if any(kw.lower() in all_claims for kw in keywords):
            detected_count += 1

    return detected_count

def check_gpt4o_file(product, file_num):
    """Check how many errors GPT-4o detected in this file"""
    txt_path = Path(f'results/errors_analysis/gpt4o_freeform/errors_{product}_{file_num}.txt')
    if not txt_path.exists():
        return 0

    with open(txt_path, 'r') as f:
        response_text = f.read().lower()

    detected_count = 0
    # Check each error that should be in this file (errors 1 to file_num)
    for error_num in range(1, file_num + 1):
        error_info = GROUND_TRUTH[product][error_num]
        keywords = error_info['keywords']

        # Check if any keyword matches
        if any(kw.lower() in response_text for kw in keywords):
            detected_count += 1

    return detected_count

# Analyze all files
results = []

for product in ['smartphone', 'melatonin', 'corecoin']:
    for file_num in range(1, 11):
        errors_in_file = file_num  # File N has N cumulative errors
        glass_box_detected = check_glass_box_file(product, file_num)
        gpt4o_detected = check_gpt4o_file(product, file_num)

        results.append({
            'product': product,
            'file_num': file_num,
            'errors_in_file': errors_in_file,
            'glass_box_detected': glass_box_detected,
            'gpt4o_detected': gpt4o_detected
        })

        print(f'{product}_{file_num}: {errors_in_file} errors → Glass Box: {glass_box_detected}, GPT-4o: {gpt4o_detected}')

# Save results
output_csv = Path('results/errors_analysis/actual_detection_counts.csv')
with open(output_csv, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['product', 'file_num', 'errors_in_file',
                                            'glass_box_detected', 'gpt4o_detected'])
    writer.writeheader()
    writer.writerows(results)

print(f'\n✓ Saved: {output_csv}')

# Calculate totals
total_errors = sum(r['errors_in_file'] for r in results)
total_glass_box = sum(r['glass_box_detected'] for r in results)
total_gpt4o = sum(r['gpt4o_detected'] for r in results)

print(f'\n=== Summary ===')
print(f'Total errors in 30 files: {total_errors}')
print(f'Glass Box detected: {total_glass_box}/{total_errors} ({total_glass_box/total_errors*100:.1f}%)')
print(f'GPT-4o detected: {total_gpt4o}/{total_errors} ({total_gpt4o/total_errors*100:.1f}%)')
