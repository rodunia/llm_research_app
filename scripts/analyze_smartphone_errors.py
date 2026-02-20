#!/usr/bin/env python3
"""Analyze Smartphone intentional errors vs Glass Box detections."""

import csv
from pathlib import Path
from collections import defaultdict

# Ground truth: 10 intentional errors from GROUND_TRUTH_ERRORS.md
GROUND_TRUTH = {
    's1.txt': {
        'error': 'Display size changed from 6.3" → 6.5"',
        'type': 'Numerical drift',
        'keywords': ['6.5', '6.5"', '6.5-inch', '6.5 inch']
    },
    's2.txt': {
        'error': 'Camera changed from 50 MP → 48 MP',
        'type': 'Spec substitution',
        'keywords': ['48 MP', '48MP', '48-megapixel', '48 megapixel']
    },
    's3.txt': {
        'error': 'Adds 1 TB storage option (not available)',
        'type': 'Hallucinated feature',
        'keywords': ['1 TB', '1TB', 'terabyte', '1024 GB']
    },
    's4.txt': {
        'error': 'Adds 16 GB RAM option (not available)',
        'type': 'Overgeneralization',
        'keywords': ['16 GB RAM', '16GB RAM', '16 GB memory', '16 GB']
    },
    's5.txt': {
        'error': 'Wi-Fi 6/6E → Wi-Fi 7',
        'type': 'Future spec hallucination',
        'keywords': ['Wi-Fi 7', 'WiFi 7', '802.11be', 'wifi 7']
    },
    's6.txt': {
        'error': 'Claims wireless charging support (not supported)',
        'type': 'Assumption error',
        'keywords': ['wireless charging', 'Qi charging', 'wireless charge', 'qi']
    },
    's7.txt': {
        'error': 'Adds hourly antivirus scanning',
        'type': 'Misattributed capability',
        'keywords': ['hourly', 'antivirus scan', 'every hour', 'scans apps']
    },
    's8.txt': {
        'error': 'Claims offline AI video rendering',
        'type': 'Capability exaggeration',
        'keywords': ['offline AI', 'offline video rendering', 'on-device rendering', 'offline.*rendering']
    },
    's9.txt': {
        'error': 'Fast charging changed from 30-45W → 60W',
        'type': 'Numerical inflation',
        'keywords': ['60W', '60 watt', '60-watt', '60 W']
    },
    's10.txt': {
        'error': 'Claims external SSD support via SIM tray',
        'type': 'Hardware impossibility',
        'keywords': ['SIM tray', 'external SSD', 'SSD via SIM', 'storage.*SIM']
    }
}

def load_audit_results():
    """Load Glass Box audit results for Smartphone files."""
    results = defaultdict(list)
    csv_path = Path("results/final_audit_results.csv")

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            filename = row['Filename']

            # Map user_smartphone_X to sX.txt format
            if 'smartphone' in filename.lower() or filename.startswith('s') and filename.endswith('.txt'):
                # Extract file number
                if filename.startswith('user_smartphone_'):
                    num = filename.replace('user_smartphone_', '').replace('.txt', '')
                    standard_name = f"s{num}.txt"
                elif filename.startswith('s') and filename[1:].replace('.txt', '').isdigit():
                    standard_name = filename
                else:
                    continue

                results[standard_name].append({
                    'violated_rule': row['Violated_Rule'],
                    'claim': row['Extracted_Claim'],
                    'confidence': float(row['Confidence_Score'])
                })

    return results

def check_error_detected(file, ground_truth, violations):
    """Check if the intentional error was extracted and flagged."""
    keywords = ground_truth['keywords']

    detected = False
    matched_claim = None
    matched_rule = None
    confidence = 0.0

    for v in violations:
        claim_lower = v['claim'].lower()
        if any(kw.lower() in claim_lower for kw in keywords):
            detected = True
            matched_claim = v['claim']
            matched_rule = v['violated_rule']
            confidence = v['confidence']
            break

    return {
        'detected': detected,
        'matched_claim': matched_claim,
        'matched_rule': matched_rule,
        'confidence': confidence
    }

def main():
    results = load_audit_results()

    print("\n" + "="*80)
    print("SMARTPHONE INTENTIONAL ERRORS - DETECTION ANALYSIS")
    print("="*80)

    detection_summary = []

    for file_num in range(1, 11):
        filename = f"s{file_num}.txt"
        print(f"\n{'='*80}")
        print(f"File {file_num}: {GROUND_TRUTH[filename]['error']}")
        print(f"Error Type: {GROUND_TRUTH[filename]['type']}")
        print(f"{'='*80}")

        if filename not in results:
            print("❌ NOT AUDITED (file not found in results)")
            detection_summary.append({
                'file': file_num,
                'error': GROUND_TRUTH[filename]['error'],
                'detected': False,
                'total_violations': 0
            })
            continue

        violations = results[filename]
        print(f"Total violations flagged: {len(violations)}")

        # Check if intentional error was detected
        detection = check_error_detected(filename, GROUND_TRUTH[filename], violations)

        if detection['detected']:
            print(f"✅ INTENTIONAL ERROR DETECTED")
            print(f"\nExtracted claim:")
            print(f"  \"{detection['matched_claim']}\"")
            print(f"\nMatched rule:")
            print(f"  \"{detection['matched_rule']}\"")
            print(f"\nConfidence: {detection['confidence']:.2%}")
        else:
            print(f"❌ INTENTIONAL ERROR NOT DETECTED")
            print(f"\nSearched for keywords: {GROUND_TRUTH[filename]['keywords']}")
            print(f"\nTop 5 violations flagged:")
            for v in violations[:5]:
                print(f"  - {v['claim'][:80]}... ({v['confidence']:.2%})")

        detection_summary.append({
            'file': file_num,
            'error': GROUND_TRUTH[filename]['error'],
            'detected': detection['detected'],
            'total_violations': len(violations)
        })

    # Overall summary
    print(f"\n\n{'='*80}")
    print("OVERALL SUMMARY")
    print(f"{'='*80}")

    detected_count = sum(1 for d in detection_summary if d['detected'])
    total = len(detection_summary)

    print(f"\nDetection Rate: {detected_count}/{total} ({detected_count/total*100:.0%})")
    audited_files = [d for d in detection_summary if d['total_violations'] > 0]
    if audited_files:
        print(f"Average violations per file: {sum(d['total_violations'] for d in audited_files) / len(audited_files):.1f}")

    print(f"\n\nDetection by file:")
    for d in detection_summary:
        status = "✅ DETECTED" if d['detected'] else "❌ MISSED"
        print(f"  File {d['file']:2d}: {status:15s} - {d['error']} ({d['total_violations']} violations)")

    # False positive analysis
    if audited_files:
        print(f"\n\nFALSE POSITIVE ANALYSIS")
        print(f"{'='*80}")
        avg_violations = sum(d['total_violations'] for d in audited_files) / len(audited_files)
        print(f"Average violations per file: {avg_violations:.1f}")
        print(f"Expected: 1 real error per file")
        print(f"False positive rate: ~{(avg_violations - 1) / avg_violations * 100:.0%}")

if __name__ == '__main__':
    main()
