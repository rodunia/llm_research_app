#!/usr/bin/env python3
"""Analyze Melatonin intentional errors vs Glass Box detections."""

import csv
from pathlib import Path
from collections import defaultdict

# Ground truth: 10 intentional errors from GROUND_TRUTH_ERRORS.md
GROUND_TRUTH = {
    'user_melatonin_1.txt': {
        'error': 'Dosage error (mg/tablet mismatch)',
        'type': 'Numerical hallucination',
        'keywords': ['5 mg', '5mg', 'dosage', 'serving']
    },
    'user_melatonin_2.txt': {
        'error': 'Bottle count changed from 120 → 100 tablets',
        'type': 'Factual inconsistency',
        'keywords': ['100 tablets', '100 tablet', 'bottle contains 100']
    },
    'user_melatonin_3.txt': {
        'error': 'Claims vegan product contains fish-derived ingredients',
        'type': 'Logical contradiction',
        'keywords': ['fish', 'fish-derived', 'fish oil', 'gelatin']
    },
    'user_melatonin_4.txt': {
        'error': 'Adds wheat traces despite "0 mg gluten" specification',
        'type': 'Domain misunderstanding',
        'keywords': ['wheat', 'traces', 'trace amount', 'wheat trace']
    },
    'user_melatonin_5.txt': {
        'error': 'Lead limit changed (decimal misplacement)',
        'type': 'Decimal misplacement',
        'keywords': ['5 ppm', 'lead', 'heavy metal', '10 mcg']
    },
    'user_melatonin_6.txt': {
        'error': 'Recommends storage at 0°C',
        'type': 'Over-literal interpretation',
        'keywords': ['0°C', 'zero degree', 'exactly 0', 'freeze', '0 degree']
    },
    'user_melatonin_7.txt': {
        'error': 'Suggests taking melatonin every 2 hours',
        'type': 'Unsafe dosage hallucination',
        'keywords': ['every 2 hours', 'every 2 hour', 'hourly', 'frequent']
    },
    'user_melatonin_8.txt': {
        'error': 'Claims FDA approval for supplement',
        'type': 'Regulatory misunderstanding',
        'keywords': ['FDA approved', 'FDA approval', 'approved by FDA', 'FDA-approved']
    },
    'user_melatonin_9.txt': {
        'error': 'Says avoid use if over 18 (age reversal)',
        'type': 'Reversal error',
        'keywords': ['over 18', 'above 18', 'if you are over 18']
    },
    'user_melatonin_10.txt': {
        'error': 'Claims permanent drowsiness side effect',
        'type': 'Overgeneralization / hallucinated risk',
        'keywords': ['permanent', 'permanent drowsiness', 'forever', 'irreversible']
    }
}

def load_audit_results():
    """Load Glass Box audit results for Melatonin files."""
    results = defaultdict(list)
    csv_path = Path("results/final_audit_results.csv")

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            filename = row['Filename']

            # Match user_melatonin_X.txt format
            if 'melatonin' in filename.lower() and filename.startswith('user_melatonin_'):
                results[filename].append({
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
    print("MELATONIN INTENTIONAL ERRORS - DETECTION ANALYSIS")
    print("="*80)

    detection_summary = []

    for file_num in range(1, 11):
        filename = f"user_melatonin_{file_num}.txt"
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
