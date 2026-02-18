#!/usr/bin/env python3
"""Test DeBERTa reproducibility - run same verification 5 times."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.deberta_nli import DebertaNliVerifier

# Initialize verifier
print("Initializing DeBERTa verifier...")
verifier = DebertaNliVerifier(
    model_name="cross-encoder/nli-deberta-v3-small",
    device="cpu"
)

# Test premise and hypothesis
premise = "This product contains 3 mg melatonin and supports healthy sleep patterns when used as directed."
hypothesis = "This supplement helps you fall asleep faster."

print("\n" + "="*80)
print("Testing DeBERTa Reproducibility")
print("="*80)
print(f"\nPremise: {premise}")
print(f"Hypothesis: {hypothesis}")
print("\nRunning verification 5 times...\n")

# Run 5 times
results = []
for i in range(1, 6):
    result = verifier.verify(premise, hypothesis)
    results.append(result)
    print(f"Run {i}:")
    print(f"  Label: {result['label']}")
    print(f"  Probs: {result['probs']}")
    print(f"  Hashes: premise={result['premise_hash']}, hypothesis={result['hypothesis_hash']}")
    print()

# Check if all results are identical
all_same = all(
    r['label'] == results[0]['label'] and
    r['probs'] == results[0]['probs'] and
    r['premise_hash'] == results[0]['premise_hash'] and
    r['hypothesis_hash'] == results[0]['hypothesis_hash']
    for r in results
)

print("="*80)
if all_same:
    print("✅ REPRODUCIBLE: All 5 runs produced identical results!")
else:
    print("❌ NOT REPRODUCIBLE: Results differ across runs")
print("="*80)
