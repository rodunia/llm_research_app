#!/usr/bin/env python3
"""Analyze Glass Box detection against ground truth errors."""

import pandas as pd
from pathlib import Path
import json

# Ground truth errors (from GROUND_TRUTH_ERRORS.md)
GROUND_TRUTH = {
    # Melatonin
    'user_melatonin_1': {'error': 'Dosage error (mg mismatch)', 'type': 'Numerical', 'keywords': ['mg', 'dosage', '5mg', '3mg']},
    'user_melatonin_2': {'error': 'Bottle count 120→100', 'type': 'Factual', 'keywords': ['120', '100', 'bottle']},
    'user_melatonin_3': {'error': 'Vegan + fish-derived', 'type': 'Logical', 'keywords': ['vegan', 'fish']},
    'user_melatonin_4': {'error': 'Wheat traces despite 0mg gluten', 'type': 'Logical', 'keywords': ['wheat', 'gluten']},
    'user_melatonin_5': {'error': 'Lead limit decimal error', 'type': 'Numerical', 'keywords': ['lead', 'mcg', 'ppb']},
    'user_melatonin_6': {'error': 'Storage at 0°C', 'type': 'Logical', 'keywords': ['0°C', 'freezing']},
    'user_melatonin_7': {'error': 'Take every 2 hours', 'type': 'Feature Hallucination', 'keywords': ['every 2 hours', 'hourly']},
    'user_melatonin_8': {'error': 'FDA approval claim', 'type': 'Factual', 'keywords': ['FDA approved']},
    'user_melatonin_9': {'error': 'Avoid if over 18 (age reversal)', 'type': 'Factual', 'keywords': ['over 18', 'above 18']},
    'user_melatonin_10': {'error': 'Permanent drowsiness', 'type': 'Factual', 'keywords': ['permanent', 'drowsiness']},

    # Smartphone
    'user_smartphone_1': {'error': 'Display 6.5" (should be 6.3")', 'type': 'Numerical', 'keywords': ['6.5', '6.3']},
    'user_smartphone_2': {'error': 'Camera 48 MP (should be 50 MP)', 'type': 'Numerical', 'keywords': ['48 MP', '50 MP']},
    'user_smartphone_3': {'error': '1 TB storage option', 'type': 'Feature Hallucination', 'keywords': ['1 TB', 'terabyte']},
    'user_smartphone_4': {'error': '16 GB RAM option', 'type': 'Feature Hallucination', 'keywords': ['16 GB RAM']},
    'user_smartphone_5': {'error': 'Wi-Fi 7 support', 'type': 'Feature Hallucination', 'keywords': ['Wi-Fi 7']},
    'user_smartphone_6': {'error': 'Wireless charging', 'type': 'Feature Hallucination', 'keywords': ['wireless charging']},
    'user_smartphone_7': {'error': 'Hourly antivirus scanning', 'type': 'Logical', 'keywords': ['hourly', 'antivirus']},
    'user_smartphone_8': {'error': 'Offline AI video rendering', 'type': 'Feature Hallucination', 'keywords': ['offline AI', 'video rendering']},
    'user_smartphone_9': {'error': 'Fast charging 60W (max 45W)', 'type': 'Numerical', 'keywords': ['60W', '45W']},
    'user_smartphone_10': {'error': 'External SSD via SIM tray', 'type': 'Feature Hallucination', 'keywords': ['SIM tray', 'external SSD']},

    # CoreCoin
    'user_corecoin_1': {'error': 'Block time 4s (should be ~5s)', 'type': 'Numerical', 'keywords': ['4 second', '4s', '5s']},
    'user_corecoin_2': {'error': 'Non-staking light validators', 'type': 'Logical', 'keywords': ['light validator', 'non-staking']},
    'user_corecoin_3': {'error': 'Regional trading pauses', 'type': 'Logical', 'keywords': ['regional pause', 'trading pause']},
    'user_corecoin_4': {'error': 'Automatic key sharding', 'type': 'Feature Hallucination', 'keywords': ['automatic', 'key sharding']},
    'user_corecoin_5': {'error': 'Gas-free smart contracts', 'type': 'Feature Hallucination', 'keywords': ['gas-free', 'zero gas']},
    'user_corecoin_6': {'error': 'Auto-pass without quorum', 'type': 'Logical', 'keywords': ['auto-pass', 'without quorum']},
    'user_corecoin_7': {'error': 'RPC simulate cross-chain', 'type': 'Logical', 'keywords': ['RPC', 'cross-chain', 'simulate']},
    'user_corecoin_8': {'error': 'Unstaking reduces rewards', 'type': 'Factual', 'keywords': ['unstaking', 'reduce', 'reward']},
    'user_corecoin_9': {'error': 'Inactivity locks governance', 'type': 'Logical', 'keywords': ['inactivity', 'lock', 'governance']},
    'user_corecoin_10': {'error': 'Region-based staking tiers', 'type': 'Factual', 'keywords': ['region-based', 'regional', 'tier']},
}

def check_detection(run_id: str, csv_path: Path) -> dict:
    """Check if Glass Box detected the ground truth error."""

    if not csv_path.exists():
        return {'detected': False, 'violation_count': 0, 'matched_keywords': []}

    df = pd.read_csv(csv_path)

    if df.empty:
        return {'detected': False, 'violation_count': 0, 'matched_keywords': []}

    violation_count = len(df)

    # Check if any violation text contains ground truth keywords
    ground_truth = GROUND_TRUTH[run_id]
    matched_keywords = []

    for _, row in df.iterrows():
        claim_text = str(row.get('claim', '')).lower()
        rule_text = str(row.get('rule', '')).lower()
        combined_text = claim_text + ' ' + rule_text

        for keyword in ground_truth['keywords']:
            if keyword.lower() in combined_text:
                matched_keywords.append(keyword)

    detected = len(matched_keywords) > 0

    return {
        'detected': detected,
        'violation_count': violation_count,
        'matched_keywords': list(set(matched_keywords))
    }

def main():
    results_dir = Path('results/pilot_individual_2026')

    results = []

    for product in ['melatonin', 'smartphone', 'corecoin']:
        print(f"\n=== {product.upper()} ===")

        for i in range(1, 11):
            run_id = f'user_{product}_{i}'
            csv_path = results_dir / f'{product}_{i}.csv'

            detection = check_detection(run_id, csv_path)
            ground_truth = GROUND_TRUTH[run_id]

            result = {
                'run_id': run_id,
                'product': product,
                'file_num': i,
                'error_description': ground_truth['error'],
                'error_type': ground_truth['type'],
                'detected': detection['detected'],
                'violation_count': detection['violation_count'],
                'matched_keywords': ', '.join(detection['matched_keywords'])
            }

            results.append(result)

            status = "✅ DETECTED" if detection['detected'] else "❌ MISSED"
            print(f"  {run_id}: {status} ({detection['violation_count']} violations)")

    # Save results
    df = pd.DataFrame(results)
    df.to_csv('results/pilot_detection_analysis.csv', index=False)

    # Summary statistics
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    total_detected = df['detected'].sum()
    total_files = len(df)
    detection_rate = (total_detected / total_files) * 100

    print(f"\nOverall Detection: {total_detected}/{total_files} ({detection_rate:.1f}%)")

    # By product
    print("\nBy Product:")
    for product in ['melatonin', 'smartphone', 'corecoin']:
        product_df = df[df['product'] == product]
        detected = product_df['detected'].sum()
        total = len(product_df)
        rate = (detected / total) * 100
        print(f"  {product.capitalize()}: {detected}/{total} ({rate:.0f}%)")

    # By error type
    print("\nBy Error Type:")
    for error_type in df['error_type'].unique():
        type_df = df[df['error_type'] == error_type]
        detected = type_df['detected'].sum()
        total = len(type_df)
        rate = (detected / total) * 100 if total > 0 else 0
        print(f"  {error_type}: {detected}/{total} ({rate:.0f}%)")

    # Missed errors
    missed_df = df[~df['detected']]
    if not missed_df.empty:
        print("\nMissed Errors:")
        for _, row in missed_df.iterrows():
            print(f"  {row['run_id']}: {row['error_description']}")

    print(f"\n✅ Results saved to: results/pilot_detection_analysis.csv")

if __name__ == '__main__':
    main()
