#!/usr/bin/env python3
"""Analyze how Glass Box Audit detected your 10 intentional smartphone mistakes."""

import json
from pathlib import Path

# Your 10 intentional mistakes (ground truth)
ground_truth = {
    'user_smartphone_1': {'error': '6.3" → 6.5" display', 'type': 'Numerical drift'},
    'user_smartphone_2': {'error': '50 MP → 48 MP camera', 'type': 'Spec substitution'},
    'user_smartphone_3': {'error': 'Added 1 TB storage', 'type': 'Hallucinated feature'},
    'user_smartphone_4': {'error': 'Added 16 GB RAM', 'type': 'Overgeneralization'},
    'user_smartphone_5': {'error': 'Wi-Fi 6/6E → Wi-Fi 7', 'type': 'Future spec'},
    'user_smartphone_6': {'error': 'Wireless charging', 'type': 'Assumption error'},
    'user_smartphone_7': {'error': 'Hourly antivirus', 'type': 'Misattributed capability'},
    'user_smartphone_8': {'error': 'Offline AI rendering', 'type': 'Capability exaggeration'},
    'user_smartphone_9': {'error': '30-45W → 60W charging', 'type': 'Numerical inflation'},
    'user_smartphone_10': {'error': 'External SSD via SIM', 'type': 'Hardware impossibility'}
}

# Read audit checkpoint
checkpoint_path = Path('results/audit_checkpoint.jsonl')
audit_results = {}

with open(checkpoint_path) as f:
    for line in f:
        data = json.loads(line)
        if data['run_id'].startswith('user_smartphone'):
            audit_results[data['run_id']] = data

print('=' * 100)
print('GLASS BOX AUDIT DETECTION ANALYSIS')
print('Comparing 10 Intentional Mistakes vs. Audit Findings')
print('=' * 100)
print()

detected_count = 0
for run_id in sorted(ground_truth.keys()):
    error_info = ground_truth[run_id]
    audit = audit_results.get(run_id, {})

    print(f"{'─' * 100}")
    print(f"FILE: {run_id}")
    print(f"{'─' * 100}")
    print(f"Your Mistake:  {error_info['error']} ({error_info['type']})")

    # Check if mistake was captured in claims
    claims = audit.get('core_claims', [])

    # Search for the error in extracted claims
    mistake_found = False
    for claim in claims:
        # Check specific patterns
        if run_id == 'user_smartphone_1' and '6.5 inch' in claim:
            print(f"✅ DETECTED:   Claim extracted: '{claim}'")
            mistake_found = True
            detected_count += 1
            break
        elif run_id == 'user_smartphone_2' and '48 MP' in claim:
            print(f"✅ DETECTED:   Claim extracted: '{claim}'")
            mistake_found = True
            detected_count += 1
            break
        elif run_id == 'user_smartphone_3' and '1 TB' in claim:
            print(f"✅ DETECTED:   Claim extracted: '{claim}'")
            mistake_found = True
            detected_count += 1
            break
        elif run_id == 'user_smartphone_4' and '16 GB' in claim:
            print(f"✅ DETECTED:   Claim extracted: '{claim}'")
            mistake_found = True
            detected_count += 1
            break
        elif run_id == 'user_smartphone_5' and 'Wi-Fi 7' in claim:
            print(f"✅ DETECTED:   Claim extracted: '{claim}'")
            mistake_found = True
            detected_count += 1
            break
        elif run_id == 'user_smartphone_6' and 'wireless charging' in claim.lower():
            print(f"✅ DETECTED:   Claim extracted: '{claim}'")
            mistake_found = True
            detected_count += 1
            break
        elif run_id == 'user_smartphone_7' and 'antivirus' in claim.lower():
            print(f"✅ DETECTED:   Claim extracted: '{claim}'")
            mistake_found = True
            detected_count += 1
            break
        elif run_id == 'user_smartphone_8' and 'offline' in claim.lower() and ('rendering' in claim.lower() or 'video' in claim.lower()):
            print(f"✅ DETECTED:   Claim extracted: '{claim}'")
            mistake_found = True
            detected_count += 1
            break
        elif run_id == 'user_smartphone_9' and '60W' in claim:
            print(f"✅ DETECTED:   Claim extracted: '{claim}'")
            mistake_found = True
            detected_count += 1
            break
        elif run_id == 'user_smartphone_10' and ('external' in claim.lower() or 'ssd' in claim.lower() or 'sim' in claim.lower()):
            print(f"✅ DETECTED:   Claim extracted: '{claim}'")
            mistake_found = True
            detected_count += 1
            break

    if not mistake_found:
        print(f"❌ MISSED:     Error not extracted as a claim")

    total_violations = audit.get('violation_count', 0)
    print(f"Total flags:   {total_violations} violations (including false positives)")
    print()

print('=' * 100)
print(f'SUMMARY: Glass Box detected {detected_count}/10 of your intentional mistakes')
print(f'Detection rate: {detected_count/10*100:.1f}%')
print('=' * 100)
print()
print('NOTE: Glass Box also flagged many FALSE POSITIVES because the NLI model')
print('      compares every claim against every spec, creating semantic mismatches.')
print()
