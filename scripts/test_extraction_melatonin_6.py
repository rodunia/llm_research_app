#!/usr/bin/env python3
"""Test extraction on melatonin_6 to debug why storage temp wasn't extracted"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.glass_box_audit import extract_atomic_claims

# Load melatonin_6 content
with open('outputs/errors_melatonin_6.txt', 'r') as f:
    content = f.read()

# Extract claims
result = extract_atomic_claims(content, "Melatonin Tablets 3 mg", "faq")

print("=== CORE CLAIMS ===")
for i, claim in enumerate(result['core_claims'], 1):
    print(f"{i}. {claim}")

print(f"\n=== DISCLAIMERS ({len(result['disclaimers'])}) ===")
for i, disclaimer in enumerate(result['disclaimers'], 1):
    print(f"{i}. {disclaimer}")

# Search for missing claims
missing_keywords = ["0°C", "2 hours", "every 2"]
print("\n=== SEARCH FOR MISSING CLAIMS ===")
for keyword in missing_keywords:
    found_in_core = any(keyword.lower() in claim.lower() for claim in result['core_claims'])
    found_in_disclaimers = any(keyword.lower() in d.lower() for d in result['disclaimers'])
    if found_in_core:
        print(f"✓ '{keyword}' found in CORE CLAIMS")
    elif found_in_disclaimers:
        print(f"✓ '{keyword}' found in DISCLAIMERS")
    else:
        print(f"✗ '{keyword}' NOT EXTRACTED")
