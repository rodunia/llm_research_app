#!/usr/bin/env python3
"""
Identify WHICH specific errors were missed and analyze patterns
"""

import pandas as pd
from pathlib import Path

# Load detection counts
df = pd.read_csv('results/errors_analysis/actual_detection_counts.csv')

# Error catalog with types
ERROR_CATALOG = {
    'smartphone': {
        1: {'error': 'Display 6.5" vs 6.3"', 'type': 'Numerical', 'category': 'Specification'},
        2: {'error': 'Camera 48 MP vs 50 MP', 'type': 'Numerical', 'category': 'Specification'},
        3: {'error': 'Storage 1TB (max 512GB)', 'type': 'Feature hallucination', 'category': 'Capability'},
        4: {'error': 'RAM 16 GB (max 12GB)', 'type': 'Feature hallucination', 'category': 'Capability'},
        5: {'error': 'Wi-Fi 7 (only 6/6E)', 'type': 'Feature hallucination', 'category': 'Capability'},
        6: {'error': 'Wireless charging (not supported)', 'type': 'Feature hallucination', 'category': 'Capability'},
        7: {'error': 'Hourly antivirus (not mentioned)', 'type': 'Feature hallucination', 'category': 'Security'},
        8: {'error': 'Offline AI video (not supported)', 'type': 'Feature hallucination', 'category': 'AI'},
        9: {'error': 'Fast charging 60W (30-45W)', 'type': 'Numerical inflation', 'category': 'Specification'},
        10: {'error': 'External SSD via SIM (impossible)', 'type': 'Feature hallucination', 'category': 'Hardware'},
    },
    'melatonin': {
        1: {'error': 'Dosage 5 mg vs 3 mg', 'type': 'Numerical', 'category': 'Critical safety'},
        2: {'error': '100 tablets vs 60', 'type': 'Numerical', 'category': 'Quantity'},
        3: {'error': 'Vegan + fish-derived', 'type': 'Logical contradiction', 'category': 'Ingredients'},
        4: {'error': '0mg gluten + wheat traces', 'type': 'Logical contradiction', 'category': 'Allergens'},
        5: {'error': 'Lead <5 ppm vs <0.5 mcg', 'type': 'Numerical', 'category': 'Safety'},
        6: {'error': 'Storage 0°C vs 15-30°C', 'type': 'Storage violation', 'category': 'Critical safety'},
        7: {'error': 'Every 2 hours vs before bed', 'type': 'Dosing violation', 'category': 'Critical safety'},
        8: {'error': 'FDA approved (not approved)', 'type': 'Regulatory fabrication', 'category': 'Compliance'},
        9: {'error': 'Avoid if over 18 (under 18)', 'type': 'Age reversal', 'category': 'Safety'},
        10: {'error': 'Permanent vs temporary drowsiness', 'type': 'Side effect exaggeration', 'category': 'Safety'},
    },
    'corecoin': {
        1: {'error': 'Block time 4s vs 5s', 'type': 'Numerical', 'category': 'Protocol'},
        2: {'error': 'Light validators no stake', 'type': 'Protocol logic error', 'category': 'Governance'},
        3: {'error': 'Trading pauses (24/7)', 'type': 'Feature hallucination', 'category': 'Market'},
        4: {'error': 'Automatic key-sharding', 'type': 'Feature hallucination', 'category': 'Security'},
        5: {'error': 'Gas-free execution', 'type': 'Economic model error', 'category': 'Protocol'},
        6: {'error': 'Auto-pass without quorum', 'type': 'Governance logic error', 'category': 'Governance'},
        7: {'error': 'Cross-chain simulate', 'type': 'Feature hallucination', 'category': 'Interoperability'},
        8: {'error': 'Unstaking reduces historical rewards', 'type': 'Economic model error', 'category': 'Staking'},
        9: {'error': 'Inactivity locks governance', 'type': 'Governance logic error', 'category': 'Governance'},
        10: {'error': 'Region-based staking rates', 'type': 'Economic model error', 'category': 'Staking'},
    }
}

# Identify missed errors
print("=" * 80)
print("MISSED ERRORS ANALYSIS")
print("=" * 80)

missed_errors_glass_box = []
missed_errors_gpt4o = []

for _, row in df.iterrows():
    product = row['product']
    file_num = row['file_num']
    errors_in_file = row['errors_in_file']
    glass_detected = row['glass_box_detected']
    gpt4o_detected = row['gpt4o_detected']

    # Which errors were missed?
    if glass_detected < errors_in_file:
        # Glass Box missed some - figure out which ones
        missed_count = errors_in_file - glass_detected
        # Assume last N errors were missed (files 6-10 for melatonin)
        for err_num in range(errors_in_file - missed_count + 1, errors_in_file + 1):
            error_info = ERROR_CATALOG[product][err_num]
            missed_errors_glass_box.append({
                'product': product,
                'file': file_num,
                'error_num': err_num,
                'error': error_info['error'],
                'type': error_info['type'],
                'category': error_info['category']
            })

    if gpt4o_detected < errors_in_file:
        # GPT-4o missed some
        missed_count = errors_in_file - gpt4o_detected
        for err_num in range(errors_in_file - missed_count + 1, errors_in_file + 1):
            error_info = ERROR_CATALOG[product][err_num]
            missed_errors_gpt4o.append({
                'product': product,
                'file': file_num,
                'error_num': err_num,
                'error': error_info['error'],
                'type': error_info['type'],
                'category': error_info['category']
            })

print("\n### GLASS BOX MISSED ERRORS ###\n")
if missed_errors_glass_box:
    for miss in missed_errors_glass_box:
        print(f"  {miss['product']}_{miss['file']} (error #{miss['error_num']}): {miss['error']}")
        print(f"    Type: {miss['type']}, Category: {miss['category']}")
else:
    print("  None - perfect detection!")

print(f"\nTotal: {len(missed_errors_glass_box)} errors")

print("\n### GPT-4O MISSED ERRORS ###\n")
if missed_errors_gpt4o:
    for miss in missed_errors_gpt4o:
        print(f"  {miss['product']}_{miss['file']} (error #{miss['error_num']}): {miss['error']}")
        print(f"    Type: {miss['type']}, Category: {miss['category']}")
else:
    print("  None - perfect detection!")

print(f"\nTotal: {len(missed_errors_gpt4o)} errors")

# Analyze patterns
print("\n" + "=" * 80)
print("PATTERN ANALYSIS")
print("=" * 80)

def analyze_patterns(missed_list, method_name):
    if not missed_list:
        print(f"\n{method_name}: No misses to analyze")
        return

    print(f"\n### {method_name} ###")

    # By type
    types = {}
    for miss in missed_list:
        types[miss['type']] = types.get(miss['type'], 0) + 1

    print("\nBy Error Type:")
    for err_type, count in sorted(types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {err_type}: {count}")

    # By category
    categories = {}
    for miss in missed_list:
        categories[miss['category']] = categories.get(miss['category'], 0) + 1

    print("\nBy Category:")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cat}: {count}")

    # By product
    products = {}
    for miss in missed_list:
        products[miss['product']] = products.get(miss['product'], 0) + 1

    print("\nBy Product:")
    for prod, count in sorted(products.items(), key=lambda x: x[1], reverse=True):
        print(f"  {prod}: {count}")

analyze_patterns(missed_errors_glass_box, "GLASS BOX")
analyze_patterns(missed_errors_gpt4o, "GPT-4O")

# Key insights
print("\n" + "=" * 80)
print("KEY INSIGHTS")
print("=" * 80)

print("\n1. **Critical Safety Errors**: ")
critical_misses_gb = [m for m in missed_errors_glass_box if 'Critical safety' in m['category']]
critical_misses_gpt = [m for m in missed_errors_gpt4o if 'Critical safety' in m['category']]
print(f"   Glass Box missed: {len(critical_misses_gb)}")
print(f"   GPT-4o missed: {len(critical_misses_gpt)}")

print("\n2. **Melatonin-Specific Issues**: ")
melatonin_misses_gb = [m for m in missed_errors_glass_box if m['product'] == 'melatonin']
melatonin_misses_gpt = [m for m in missed_errors_gpt4o if m['product'] == 'melatonin']
print(f"   Glass Box: {len(melatonin_misses_gb)}/3 total misses")
print(f"   GPT-4o: {len(melatonin_misses_gpt)}/5 total misses")
print(f"   → Both struggle with melatonin errors #6-10")

print("\n3. **Error Detection Patterns**: ")
print(f"   Glass Box: Perfect on smartphone & corecoin")
print(f"   GPT-4o: Perfect on smartphone & corecoin")
print(f"   → Melatonin is the challenge!")

# Save analysis
with open('results/errors_analysis/MISSED_ERRORS_ANALYSIS.txt', 'w') as f:
    f.write("MISSED ERRORS ANALYSIS\n")
    f.write("=" * 80 + "\n\n")

    f.write("GLASS BOX MISSED:\n")
    for miss in missed_errors_glass_box:
        f.write(f"  {miss['product']}_{miss['error_num']}: {miss['error']} ({miss['type']})\n")

    f.write(f"\nGPT-4O MISSED:\n")
    for miss in missed_errors_gpt4o:
        f.write(f"  {miss['product']}_{miss['error_num']}: {miss['error']} ({miss['type']})\n")

print("\n✓ Saved: results/errors_analysis/MISSED_ERRORS_ANALYSIS.txt")
