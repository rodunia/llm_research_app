"""Smoke test for DeBERTa verification layer.

Quick CPU-only test (<30 seconds) to verify:
- Premise builder works
- DeBERTa NLI inference works
- Output schema is correct
- Labels are valid
- Probabilities sum to ~1

Usage:
    python scripts/smoke_deberta_verify.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.premise_builder import build_premise, hash_text
from analysis.deberta_nli import DebertaNliVerifier


def run_smoke_test():
    """Run quick smoke test for DeBERTa verification."""
    print("=" * 70)
    print("DeBERTa Verification Layer - Smoke Test")
    print("=" * 70)
    print()

    # Test 1: Premise Builder
    print("Test 1: Premise Builder")
    print("-" * 70)

    mock_product = {
        "product_id": "test_supplement",
        "name": "Melatonin 3mg",
        "authorized_claims": [
            {"statement": "Each tablet contains 3 mg melatonin."},
            {"statement": "May help with occasional sleeplessness."}
        ],
        "prohibited_claims": [
            "Guaranteed to work for all users.",
            "Cures insomnia permanently.",
            "Best sleep aid ever made."
        ],
        "technical_specs": [
            {"category": "Active Ingredient", "value_with_units": "Melatonin 3 mg"},
            {"category": "Form", "value_with_units": "Tablet"}
        ],
        "mandatory_disclaimers": [
            {"statement": "This product is not intended to diagnose, treat, cure, or prevent any disease."},
            {"statement": "Consult a healthcare professional before use."}
        ]
    }

    premise = build_premise(mock_product)
    premise_hash = hash_text(premise)

    print(f"✓ Premise built successfully")
    print(f"  Length: {len(premise)} chars")
    print(f"  Hash: {premise_hash}")
    print()

    # Verify sections
    required_sections = ["AUTHORIZED:", "PROHIBITED:", "SPECS:", "DISCLAIMERS:"]
    all_present = all(section in premise for section in required_sections)

    if all_present:
        print(f"✓ All required sections present: {required_sections}")
    else:
        print(f"✗ Missing sections!")
        return False

    print()
    print("Premise:")
    print(premise)
    print()

    # Test 2: DeBERTa NLI Verifier
    print("Test 2: DeBERTa NLI Verifier")
    print("-" * 70)

    # Initialize verifier (CPU-only, small model)
    print("Loading DeBERTa model (this may take 10-20 seconds on first run)...")
    verifier = DebertaNliVerifier(
        model_name="cross-encoder/nli-deberta-v3-small",  # Smallest model
        device="cpu"
    )
    print("✓ Model loaded successfully")
    print()

    # Test case 1: ENTAILMENT (hypothesis matches authorized claim)
    hypothesis_entail = "Each tablet contains 3 mg of melatonin."

    print(f"Test 2a: Expected ENTAILMENT")
    print(f"  Hypothesis: {hypothesis_entail}")

    result_entail = verifier.verify(premise, hypothesis_entail)

    print(f"  Predicted: {result_entail['label']}")
    print(f"  Probs: {result_entail['probs']}")
    print()

    # Test case 2: CONTRADICTION (hypothesis matches prohibited claim)
    hypothesis_contra = "Guaranteed to work for all users without exception."

    print(f"Test 2b: Expected CONTRADICTION")
    print(f"  Hypothesis: {hypothesis_contra}")

    result_contra = verifier.verify(premise, hypothesis_contra)

    print(f"  Predicted: {result_contra['label']}")
    print(f"  Probs: {result_contra['probs']}")
    print()

    # Test case 3: NEUTRAL (hypothesis not mentioned in premise)
    hypothesis_neutral = "This product is available in multiple flavors."

    print(f"Test 2c: Expected NEUTRAL")
    print(f"  Hypothesis: {hypothesis_neutral}")

    result_neutral = verifier.verify(premise, hypothesis_neutral)

    print(f"  Predicted: {result_neutral['label']}")
    print(f"  Probs: {result_neutral['probs']}")
    print()

    # Test 3: Output Schema Validation
    print("Test 3: Output Schema Validation")
    print("-" * 70)

    required_keys = {"model", "label", "probs", "premise_hash", "hypothesis_hash"}
    results_to_check = [result_entail, result_contra, result_neutral]

    all_valid = True

    for i, result in enumerate(results_to_check, 1):
        # Check keys
        if not required_keys.issubset(result.keys()):
            print(f"✗ Result {i}: Missing keys {required_keys - set(result.keys())}")
            all_valid = False
            continue

        # Check label is valid
        valid_labels = {"entailment", "neutral", "contradiction"}
        if result['label'] not in valid_labels:
            print(f"✗ Result {i}: Invalid label '{result['label']}'")
            all_valid = False
            continue

        # Check probs sum to ~1
        prob_sum = sum(result['probs'].values())
        if abs(prob_sum - 1.0) > 0.01:
            print(f"✗ Result {i}: Probs don't sum to 1 (sum={prob_sum:.4f})")
            all_valid = False
            continue

        # Check probs has all 3 labels
        if set(result['probs'].keys()) != valid_labels:
            print(f"✗ Result {i}: Probs missing labels")
            all_valid = False
            continue

        # Check hashes are 12 chars
        if len(result['premise_hash']) != 12 or len(result['hypothesis_hash']) != 12:
            print(f"✗ Result {i}: Hash length incorrect")
            all_valid = False
            continue

    if all_valid:
        print("✓ All results have valid schema:")
        print(f"  - Required keys: {required_keys}")
        print(f"  - Valid labels: {valid_labels}")
        print(f"  - Probs sum to ~1.0")
        print(f"  - Hashes are 12 chars")
    else:
        print("✗ Some schema validations failed")
        return False

    print()

    # Final summary
    print("=" * 70)
    print("Smoke Test Summary")
    print("=" * 70)
    print("✓ Premise builder: PASS")
    print("✓ DeBERTa NLI verifier: PASS")
    print("✓ Output schema: PASS")
    print()
    print("All smoke tests PASSED!")
    print()
    print("Next steps:")
    print("  1. Run full test suite: pytest -q")
    print("  2. Verify claims: python -m analysis.deberta_verify_claims --help")
    print("=" * 70)

    return True


if __name__ == "__main__":
    try:
        success = run_smoke_test()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Smoke test failed with error:")
        print(f"  {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
