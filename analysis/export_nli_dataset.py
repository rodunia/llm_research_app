"""Export NLI dataset for DeBERTa finetuning (readiness scaffold).

Reads verified claims JSONL and product YAMLs, exports dataset in format
suitable for human annotation and future finetuning.

Output format (JSONL):
{
  "premise": "<premise_text>",
  "hypothesis": "<claim_sentence>",
  "label": null,  # For human annotation
  "product_id": "...",
  "engine": "...",
  "material": "...",
  "temperature": ...,
  "time_of_day": "...",
  "repetition": ...,
  "claim_id": "...",
  "predicted_label": "...",  # From DeBERTa inference (if available)
  "policy_violation": false
}

Usage:
    python -m analysis.export_nli_dataset \\
        --claims analysis/claims/*.json \\
        --products products/ \\
        --out results/deberta_nli_dataset.jsonl
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict, Any
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.premise_builder import build_premise, load_product_yaml


def export_claim_to_nli_record(
    claim_record: Dict[str, Any],
    product_yaml: Dict[str, Any],
    premise: str
) -> Dict[str, Any]:
    """Convert claim record to NLI dataset record.

    Args:
        claim_record: Claim record from extraction
        product_yaml: Product YAML dict
        premise: Prebuilt premise string

    Returns:
        NLI dataset record dict
    """
    # Extract metadata
    product_id = claim_record.get('product_id') or claim_record.get('product', 'unknown')
    engine = claim_record.get('engine', 'unknown')
    material = claim_record.get('material_type', 'unknown')
    temperature = claim_record.get('temperature', None)
    time_of_day = claim_record.get('time_of_day', 'unknown')
    repetition = claim_record.get('repetition_id', None)

    # Extract claim sentence
    hypothesis = claim_record.get('sentence', '')

    # Extract predicted label from deberta (if available)
    deberta_result = claim_record.get('deberta', {})
    predicted_label = deberta_result.get('label') if isinstance(deberta_result, dict) else None
    policy_violation = deberta_result.get('policy_violation', False) if isinstance(deberta_result, dict) else False

    # Build NLI record
    nli_record = {
        "premise": premise,
        "hypothesis": hypothesis,
        "label": None,  # For human annotation
        "product_id": product_id,
        "engine": engine,
        "material": material,
        "temperature": temperature,
        "time_of_day": time_of_day,
        "repetition": repetition,
        "claim_id": claim_record.get('claim_id', ''),
        "claim_kind": claim_record.get('claim_kind', 'product_claim'),
        "predicted_label": predicted_label,
        "policy_violation": policy_violation
    }

    return nli_record


def export_nli_dataset(
    claims_files: List[Path],
    products_dir: Path,
    output_file: Path,
    only_product_claims: bool = True
):
    """Export NLI dataset from claims.

    Args:
        claims_files: List of claim JSON files
        products_dir: Directory containing product YAMLs
        output_file: Output JSONL file
        only_product_claims: If True, only export product_claims (skip disclaimers)
    """
    print("NLI Dataset Exporter")
    print("=" * 60)
    print(f"Input claims: {len(claims_files)}")
    print(f"Products dir: {products_dir}")
    print(f"Output: {output_file}")
    print(f"Only product claims: {only_product_claims}")
    print()

    # Load all claims
    print("Loading claims...")
    claims = []
    for claims_file in claims_files:
        try:
            with open(claims_file, 'r', encoding='utf-8') as f:
                claim_record = json.load(f)
                claims.append(claim_record)
        except Exception as e:
            print(f"  ✗ Error loading {claims_file.name}: {e}")

    print(f"✓ Loaded {len(claims)} claims")
    print()

    # Filter to product claims if requested
    if only_product_claims:
        claims = [c for c in claims if c.get('claim_kind') == 'product_claim']
        print(f"✓ Filtered to {len(claims)} product claims")
        print()

    # Group by product_id and build premises
    print("Building premises for each product...")
    products_cache = {}
    premises_cache = {}

    for claim in claims:
        product_id = claim.get('product_id') or claim.get('product', 'unknown')

        if product_id not in products_cache:
            try:
                product_yaml = load_product_yaml(product_id, products_dir)
                premise = build_premise(product_yaml)

                products_cache[product_id] = product_yaml
                premises_cache[product_id] = premise

                print(f"  ✓ Loaded {product_id}")
            except Exception as e:
                print(f"  ✗ Error loading {product_id}: {e}")

    print(f"✓ Built premises for {len(products_cache)} products")
    print()

    # Export NLI records
    print("Exporting NLI dataset...")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    nli_records = []
    skipped = 0

    for claim in claims:
        product_id = claim.get('product_id') or claim.get('product', 'unknown')

        if product_id not in products_cache:
            skipped += 1
            continue

        nli_record = export_claim_to_nli_record(
            claim_record=claim,
            product_yaml=products_cache[product_id],
            premise=premises_cache[product_id]
        )

        nli_records.append(nli_record)

    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        for record in nli_records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

    print(f"✓ Exported {len(nli_records)} NLI records to {output_file}")
    if skipped > 0:
        print(f"  (Skipped {skipped} claims due to missing products)")
    print()

    # Summary statistics
    print("=" * 60)
    print("Dataset Summary:")
    print(f"  Total records: {len(nli_records)}")

    # Group by product
    product_counts = {}
    for record in nli_records:
        product_id = record['product_id']
        product_counts[product_id] = product_counts.get(product_id, 0) + 1

    print(f"\n  Records by product:")
    for product_id, count in sorted(product_counts.items()):
        print(f"    {product_id}: {count}")

    # Group by engine
    engine_counts = {}
    for record in nli_records:
        engine = record['engine']
        engine_counts[engine] = engine_counts.get(engine, 0) + 1

    print(f"\n  Records by engine:")
    for engine, count in sorted(engine_counts.items()):
        print(f"    {engine}: {count}")

    # Predicted labels distribution (if available)
    predicted_counts = {}
    for record in nli_records:
        pred = record.get('predicted_label')
        if pred:
            predicted_counts[pred] = predicted_counts.get(pred, 0) + 1

    if predicted_counts:
        print(f"\n  Predicted labels (from DeBERTa inference):")
        for label, count in sorted(predicted_counts.items()):
            print(f"    {label}: {count}")

    # Policy violations
    policy_violations = sum(1 for r in nli_records if r.get('policy_violation', False))
    if policy_violations > 0:
        print(f"\n  ⚠ Policy violations: {policy_violations}")

    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Human annotators label records (fill 'label' field)")
    print("  2. Split dataset with group-aware strategy (see docs/deberta_verification_spec.md)")
    print("  3. Run finetuning with scripts/train_deberta_nli.py (not implemented yet)")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Export NLI dataset for DeBERTa finetuning"
    )

    parser.add_argument(
        '--claims',
        required=True,
        help='Claims JSON files (glob pattern, e.g., analysis/claims/*.json)'
    )

    parser.add_argument(
        '--products',
        default='products',
        help='Products directory (default: products/)'
    )

    parser.add_argument(
        '--out',
        default='results/deberta_nli_dataset.jsonl',
        help='Output JSONL file (default: results/deberta_nli_dataset.jsonl)'
    )

    parser.add_argument(
        '--include-disclaimers',
        action='store_true',
        help='Include disclaimer claims (default: only product_claims)'
    )

    args = parser.parse_args()

    # Resolve claims files
    claims_pattern = Path(args.claims)

    if '*' in str(claims_pattern):
        parts = list(claims_pattern.parts)
        glob_idx = next(i for i, p in enumerate(parts) if '*' in p)
        base_dir = Path(*parts[:glob_idx])
        pattern = '/'.join(parts[glob_idx:])
        claims_files = sorted(base_dir.glob(pattern))
    else:
        claims_files = [claims_pattern]

    if not claims_files:
        print(f"Error: No claims files found matching: {args.claims}")
        return 1

    # Export dataset
    export_nli_dataset(
        claims_files=claims_files,
        products_dir=Path(args.products),
        output_file=Path(args.out),
        only_product_claims=not args.include_disclaimers
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
