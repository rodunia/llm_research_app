"""
Validate that Glass Box detected the EXACT ground truth errors
(not just any violations, but the specific intentional errors)
"""
import pandas as pd
import glob
from pathlib import Path

# Ground truth errors from GROUND_TRUTH_ERRORS.md
GROUND_TRUTH = {
    'smartphone': {
        1: ['6.5"', 'Display size'],  # Should be 6.3"
        2: ['48 MP', 'camera'],  # Should be 50 MP
        3: ['1TB', '1 TB', 'storage'],
        4: ['16 GB', 'RAM'],
        5: ['Wi-Fi 7'],
        6: ['wireless charging', '10W'],
        7: ['antivirus', 'hourly'],
        8: ['offline AI', 'video rendering'],
        9: ['60W', 'charging'],
        10: ['external SSD', 'SIM tray'],
    },
    'melatonin': {
        1: ['5 mg', '5mg'],  # Should be 3 mg
        2: ['100 tablets'],  # Should be 60
        3: ['fish-derived', 'vegan'],
        4: ['wheat', 'gluten'],
        5: ['<5 ppm', '5 ppm', 'lead'],
        6: ['0°C', '0 °C'],
        7: ['every 2 hours', '2 hours'],
        8: ['FDA approved'],
        9: ['over 18', 'avoid if over'],
        10: ['permanent drowsiness'],
    },
    'corecoin': {
        1: ['~4 seconds', '4 seconds', 'block time'],  # Should be ~5 seconds
        2: ['light validators', "don't stake", 'without staking'],
        3: ['trading pauses', 'maintenance', 'regional'],
        4: ['automatic key-sharding', 'key backup'],
        5: ['gas-free', 'zero-fee'],
        6: ['without quorum', 'auto-pass'],
        7: ['cross-chain', 'simulate'],
        8: ['unstaking penalty', 'historical rewards'],
        9: ['locks governance', 'inactivity'],
        10: ['region-based', 'fixed rates', 'staking tiers'],
    }
}

def check_ground_truth_detection(product, file_num, df_violations):
    """Check if ground truth error keywords appear in detected violations"""
    if file_num not in GROUND_TRUTH[product]:
        return False, "No ground truth defined"

    keywords = GROUND_TRUTH[product][file_num]
    violations_text = ' '.join(df_violations['Extracted_Claim'].astype(str).tolist()).lower()

    # Check if ANY keyword is found in violations
    found_keywords = [kw for kw in keywords if kw.lower() in violations_text]

    return len(found_keywords) > 0, found_keywords

# Analyze all files
glass_box_files = glob.glob('results/errors_analysis/glass_box/errors_*.csv')

results = []
for f in sorted(glass_box_files):
    filename = Path(f).stem
    parts = filename.replace('errors_', '').split('_')
    product = parts[0]
    file_num = int(parts[1])

    df = pd.read_csv(f)
    df_violations = df[df['Status'] == 'FAIL']

    detected, keywords = check_ground_truth_detection(product, file_num, df_violations)

    results.append({
        'file': filename,
        'expected_errors': file_num,
        'total_violations': len(df_violations),
        'ground_truth_detected': '✓' if detected else '✗',
        'matched_keywords': ', '.join(keywords) if detected else 'NONE'
    })

df_results = pd.DataFrame(results)
print(df_results.to_string(index=False))

print(f"\n\n=== SUMMARY ===")
detected_count = (df_results['ground_truth_detected'] == '✓').sum()
print(f"Ground truth errors detected: {detected_count}/30")
print(f"Detection rate: {detected_count/30*100:.1f}%")

# Show failures
failures = df_results[df_results['ground_truth_detected'] == '✗']
if len(failures) > 0:
    print(f"\n=== MISSED ERRORS ===")
    print(failures.to_string(index=False))
