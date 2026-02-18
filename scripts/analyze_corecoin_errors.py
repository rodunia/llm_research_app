#!/usr/bin/env python3
"""Analyze CoreCoin intentional errors vs Glass Box detections."""

import csv
from pathlib import Path
from collections import defaultdict

# Ground truth: Your 10 intentional errors
GROUND_TRUTH = {
    '1.txt': {
        'error': 'Block time 4s (should be ~5s)',
        'type': 'Numerical drift',
        'keywords': ['4 second', '4s', 'block time']
    },
    '2.txt': {
        'error': 'Light validators (non-staking)',
        'type': 'Consensus misunderstanding',
        'keywords': ['light validator', 'light-validator', 'non-staking', 'do not stake']
    },
    '3.txt': {
        'error': 'Regional trading pauses',
        'type': 'Domain transfer error',
        'keywords': ['trading pause', 'regional', 'trading hours', 'market hours']
    },
    '4.txt': {
        'error': 'Automatic key sharding backup',
        'type': 'Feature hallucination',
        'keywords': ['key shard', 'sharding', 'automatic backup', 'distributed key']
    },
    '5.txt': {
        'error': 'EVM execution without gas fees',
        'type': 'Technical impossibility',
        'keywords': ['without gas', 'no gas', 'gas-free', 'EVM', 'free execution']
    },
    '6.txt': {
        'error': 'Proposals auto-pass without quorum',
        'type': 'Governance logic error',
        'keywords': ['auto pass', 'without quorum', 'automatic approval', 'no quorum']
    },
    '7.txt': {
        'error': 'RPC simulates cross-chain calls',
        'type': 'Architecture confusion',
        'keywords': ['RPC', 'cross-chain', 'simulate', 'cross chain']
    },
    '8.txt': {
        'error': 'Early unstaking reduces historical rewards',
        'type': 'Reward model hallucination',
        'keywords': ['unstaking', 'historical reward', 'early', 'reduce']
    },
    '9.txt': {
        'error': 'Validator inactivity locks governance rights',
        'type': 'Overextension of protocol logic',
        'keywords': ['inactivity', 'lock', 'governance', 'validator']
    },
    '10.txt': {
        'error': 'Region-based fixed rate staking tiers',
        'type': 'Regulatory/financial fabrication',
        'keywords': ['region', 'fixed rate', 'staking tier', 'geographic']
    }
}

def load_audit_results():
    """Load Glass Box audit results for CoreCoin files."""
    results = defaultdict(list)
    csv_path = Path("results/final_audit_results.csv")

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            filename = row['Filename']

            # Map various filename formats to standardized format
            if 'corecoin' in filename.lower():
                # Extract file number
                if filename.endswith('.txt'):
                    base = filename.replace('.txt', '')
                    if base.startswith('user_corecoin_'):
                        num = base.replace('user_corecoin_', '')
                        standard_name = f"{num}.txt"
                    elif base.isdigit():
                        standard_name = f"{base}.txt"
                    else:
                        continue
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

    # Check if any extracted claim contains error keywords
    extracted_claims = [v['claim'] for v in violations]

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
    print("CORECOIN INTENTIONAL ERRORS - DETECTION ANALYSIS")
    print("="*80)

    detection_summary = []

    for file_num in range(1, 11):
        filename = f"{file_num}.txt"
        print(f"\n{'='*80}")
        print(f"File {file_num}: {GROUND_TRUTH[filename]['error']}")
        print(f"Error Type: {GROUND_TRUTH[filename]['type']}")
        print(f"{'='*80}")

        if filename not in results:
            print("❌ NOT AUDITED (file not found in results)")
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
    print(f"Average violations per file: {sum(d['total_violations'] for d in detection_summary) / total:.1f}")

    print(f"\n\nDetection by file:")
    for d in detection_summary:
        status = "✅ DETECTED" if d['detected'] else "❌ MISSED"
        print(f"  File {d['file']:2d}: {status:15s} - {d['error']} ({d['total_violations']} violations)")

    # False positive analysis
    print(f"\n\nFALSE POSITIVE ANALYSIS")
    print(f"{'='*80}")
    avg_violations = sum(d['total_violations'] for d in detection_summary) / total
    print(f"Average violations per file: {avg_violations:.1f}")
    print(f"Expected: 1 real error per file")
    print(f"False positive rate: ~{(avg_violations - 1) / avg_violations * 100:.0%}")

if __name__ == '__main__':
    main()
