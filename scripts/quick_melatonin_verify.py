#!/usr/bin/env python3
"""Quick script to collect ~100 melatonin claims and run DeBERTa verification."""

import json
import glob
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.premise_builder import build_premise
from analysis.deberta_nli import DebertaNliVerifier
import yaml


def load_product_yaml(product_id, products_dir="products"):
    """Load product YAML file."""
    yaml_path = Path(products_dir) / f"{product_id}.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"Product YAML not found: {yaml_path}")

    with open(yaml_path, 'r') as f:
        return yaml.safe_load(f)


def collect_melatonin_claims(limit=100):
    """Collect up to `limit` melatonin claims from outputs/*.json files."""
    claims = []
    claim_files = glob.glob("outputs/*_claims.json")

    for claim_file in claim_files:
        if len(claims) >= limit:
            break

        try:
            with open(claim_file, 'r') as f:
                data = json.load(f)

            # Check if this is melatonin
            product_id = data.get('extraction_metadata', {}).get('product_id')
            if product_id != 'supplement_melatonin':
                continue

            # Extract claims
            extracted_claims = data.get('extracted_claims', [])

            for claim in extracted_claims:
                if len(claims) >= limit:
                    break

                # Get claim text from various possible field names
                claim_text = claim.get('claim_text') or claim.get('sentence') or claim.get('text') or ''

                # Add claim with metadata
                claims.append({
                    'run_id': data.get('run_id'),
                    'product_id': product_id,
                    'material_type': data.get('extraction_metadata', {}).get('material_type'),
                    'generation_engine': data.get('extraction_metadata', {}).get('generation_engine'),
                    'claim_text': claim_text,
                    'claim_kind': claim.get('claim_kind') or claim.get('claim_type') or 'unknown',
                    'original_claim': claim
                })

        except Exception as e:
            print(f"Warning: Error processing {claim_file}: {e}", file=sys.stderr)
            continue

    return claims


def verify_claims(claims, verifier, product_yaml):
    """Verify claims using DeBERTa."""
    premise = build_premise(product_yaml)

    results = []
    for i, claim_record in enumerate(claims, 1):
        claim_text = claim_record['claim_text']

        # Run NLI
        nli_result = verifier.verify(premise, claim_text)

        # Store result
        result = {
            'claim_id': i,
            'run_id': claim_record['run_id'],
            'material_type': claim_record['material_type'],
            'generation_engine': claim_record['generation_engine'],
            'claim_text': claim_text,
            'claim_kind': claim_record['claim_kind'],
            'deberta_label': nli_result['label'],
            'deberta_probs': nli_result['probs'],
            'deberta_model': nli_result['model']
        }

        results.append(result)

        # Progress indicator
        if i % 10 == 0:
            print(f"Processed {i}/{len(claims)} claims...", file=sys.stderr)

    return results


def main():
    print("=" * 80)
    print("DeBERTa Verification - Melatonin Claims Sample")
    print("=" * 80)

    # Collect claims
    print("\n[1/4] Collecting melatonin claims...")
    claims = collect_melatonin_claims(limit=100)
    print(f"Collected {len(claims)} claims")

    if len(claims) == 0:
        print("ERROR: No claims found. Exiting.")
        return

    # Load product YAML
    print("\n[2/4] Loading product YAML...")
    product_yaml = load_product_yaml('supplement_melatonin')
    print(f"Loaded product: {product_yaml.get('product_name', 'Unknown')}")

    # Initialize verifier
    print("\n[3/4] Initializing DeBERTa verifier (this may download model on first run)...")
    verifier = DebertaNliVerifier(
        model_name="cross-encoder/nli-deberta-v3-small",
        device="cpu"
    )
    print("Verifier ready")

    # Verify claims
    print(f"\n[4/4] Verifying {len(claims)} claims...")
    results = verify_claims(claims, verifier, product_yaml)

    # Save results
    output_file = "results/melatonin_deberta_sample.jsonl"
    Path("results").mkdir(exist_ok=True)

    with open(output_file, 'w') as f:
        for result in results:
            f.write(json.dumps(result) + '\n')

    print(f"\n✅ Results saved to: {output_file}")

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    label_counts = {}
    for result in results:
        label = result['deberta_label']
        label_counts[label] = label_counts.get(label, 0) + 1

    print(f"\nTotal claims verified: {len(results)}")
    print("\nLabel distribution:")
    for label in ['entailment', 'neutral', 'contradiction']:
        count = label_counts.get(label, 0)
        pct = (count / len(results) * 100) if results else 0
        print(f"  {label:15s}: {count:3d} ({pct:5.1f}%)")

    # Show some examples
    print("\n" + "=" * 80)
    print("SAMPLE RESULTS (First 5)")
    print("=" * 80)

    for i, result in enumerate(results[:5], 1):
        print(f"\n[{i}] {result['claim_text'][:100]}...")
        print(f"    Label: {result['deberta_label']}")
        print(f"    Probs: {result['deberta_probs']}")
        print(f"    Engine: {result['generation_engine']}, Material: {result['material_type']}")

    print("\n" + "=" * 80)
    print(f"Full results available at: {output_file}")
    print("=" * 80)


if __name__ == '__main__':
    main()
