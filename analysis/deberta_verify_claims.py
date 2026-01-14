"""Batch DeBERTa verification for extracted claims.

Reads claims JSONL, verifies each product_claim against premise built from
product YAML, and outputs enriched JSONL with deberta verification results.

Usage:
    python -m analysis.deberta_verify_claims \\
        --in analysis/claims/*.json \\
        --out results/claims_deberta.jsonl \\
        --products-dir products/ \\
        --model cross-encoder/nli-deberta-v3-small

    # Or in-place update
    python -m analysis.deberta_verify_claims \\
        --in analysis/claims/*.json \\
        --inplace \\
        --products-dir products/
"""

import json
import argparse
from pathlib import Path
from typing import Dict, Any, List
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.premise_builder import build_premise, load_product_yaml
from analysis.deberta_nli import DebertaNliVerifier


def check_policy_violation(hypothesis: str, prohibited_claims: List[str]) -> bool:
    """Check if hypothesis matches any prohibited claim (simple substring match).

    Args:
        hypothesis: Claim sentence to check
        prohibited_claims: List of prohibited statement strings

    Returns:
        True if hypothesis contains a prohibited claim substring (case-insensitive)
    """
    hypothesis_lower = hypothesis.lower()

    for prohibited in prohibited_claims:
        prohibited_lower = prohibited.lower()

        # Exact match or substring match
        if prohibited_lower in hypothesis_lower or hypothesis_lower in prohibited_lower:
            return True

    return False


def extract_prohibited_claims(product_yaml: Dict[str, Any]) -> List[str]:
    """Extract list of prohibited claim strings from product YAML.

    Args:
        product_yaml: Parsed product YAML dictionary

    Returns:
        List of prohibited claim statements
    """
    prohibited = []
    prohibited_claims = product_yaml.get('prohibited_claims', [])

    for claim in prohibited_claims:
        if isinstance(claim, dict):
            statement = claim.get('statement', '')
        elif isinstance(claim, str):
            statement = claim
        else:
            continue

        if statement:
            prohibited.append(statement)

    return prohibited


def verify_claim_record(
    claim_record: Dict[str, Any],
    verifier: DebertaNliVerifier,
    products_cache: Dict[str, Dict[str, Any]],
    products_dir: Path,
    skip_disclaimers: bool = True
) -> Dict[str, Any]:
    """Verify a single claim record and populate deberta field.

    Args:
        claim_record: Claim record dict with fields:
            - product (or product_id)
            - claim_kind
            - sentence
            - deberta (to be populated)
        verifier: DeBERTa NLI verifier instance
        products_cache: Dict of {product_id: product_yaml} for caching
        products_dir: Path to products directory
        skip_disclaimers: If True, skip verification for disclaimers (V1 default)

    Returns:
        Updated claim record with populated deberta field
    """
    # Get product_id (handle both 'product' and 'product_id' keys)
    product_id = claim_record.get('product_id') or claim_record.get('product')

    if not product_id:
        # Skip if no product_id
        claim_record['deberta'] = {"skipped": "no_product_id"}
        return claim_record

    # Get claim kind and sentence
    claim_kind = claim_record.get('claim_kind', 'product_claim')
    sentence = claim_record.get('sentence', '')

    if not sentence:
        claim_record['deberta'] = {"skipped": "no_sentence"}
        return claim_record

    # Skip disclaimers in V1 (to avoid ambiguity)
    if skip_disclaimers and claim_kind == 'disclaimer':
        claim_record['deberta'] = {"skipped": "disclaimer"}
        return claim_record

    # Load product YAML (with caching)
    if product_id not in products_cache:
        try:
            products_cache[product_id] = load_product_yaml(product_id, products_dir)
        except FileNotFoundError as e:
            claim_record['deberta'] = {"error": str(e)}
            return claim_record

    product_yaml = products_cache[product_id]

    # Build premise
    premise = build_premise(product_yaml)

    # Run NLI verification
    nli_result = verifier.verify(premise, sentence)

    # Check for policy violations (simple substring match)
    prohibited_claims = extract_prohibited_claims(product_yaml)
    policy_violation = check_policy_violation(sentence, prohibited_claims)

    # Populate deberta field with canonical schema
    claim_record['deberta'] = {
        "model": nli_result["model"],
        "label": nli_result["label"],
        "probs": nli_result["probs"],
        "premise_hash": nli_result["premise_hash"],
        "hypothesis_hash": nli_result["hypothesis_hash"],
        "policy_violation": policy_violation
    }

    # Set severity based on policy violation (simple rule for V1)
    if policy_violation:
        claim_record['severity'] = "high"
    elif nli_result["label"] == "contradiction":
        claim_record['severity'] = "medium"
    else:
        claim_record['severity'] = None

    return claim_record


def process_claims_jsonl(
    input_files: List[Path],
    output_file: Path,
    products_dir: Path,
    model_name: str,
    device: str,
    inplace: bool,
    skip_disclaimers: bool
):
    """Process claims from JSONL files and add DeBERTa verification.

    Args:
        input_files: List of input JSON files (one claim per file)
        output_file: Output JSONL file (one claim per line)
        products_dir: Directory containing product YAMLs
        model_name: HuggingFace model name
        device: 'cpu' or 'cuda'
        inplace: If True, update input files directly
        skip_disclaimers: If True, skip disclaimer verification
    """
    print(f"DeBERTa Claim Verification")
    print("=" * 60)
    print(f"Input files: {len(input_files)}")
    print(f"Output: {output_file if not inplace else 'IN-PLACE'}")
    print(f"Products: {products_dir}")
    print(f"Model: {model_name}")
    print(f"Device: {device}")
    print(f"Skip disclaimers: {skip_disclaimers}")
    print()

    # Initialize verifier
    print("Loading DeBERTa model...")
    verifier = DebertaNliVerifier(model_name=model_name, device=device)
    print()

    # Products cache
    products_cache = {}

    # Process claims
    verified_claims = []
    skipped = 0
    errors = 0

    print("Processing claims...")
    for i, input_file in enumerate(input_files, 1):
        # Load claim record
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                claim_record = json.load(f)
        except Exception as e:
            print(f"  [{i}/{len(input_files)}] ✗ Error loading {input_file.name}: {e}")
            errors += 1
            continue

        # Verify claim
        claim_record = verify_claim_record(
            claim_record=claim_record,
            verifier=verifier,
            products_cache=products_cache,
            products_dir=products_dir,
            skip_disclaimers=skip_disclaimers
        )

        # Check if skipped
        deberta_result = claim_record.get('deberta', {})
        if 'skipped' in deberta_result or 'error' in deberta_result:
            skipped += 1

        verified_claims.append(claim_record)

        # Progress indicator
        if i % 10 == 0 or i == len(input_files):
            print(f"  Processed {i}/{len(input_files)} claims", end='\r')

    print()  # New line after progress
    print()

    # Write output
    if inplace:
        print("Updating input files in-place...")
        for claim_record, input_file in zip(verified_claims, input_files):
            with open(input_file, 'w', encoding='utf-8') as f:
                json.dump(claim_record, f, indent=2, ensure_ascii=False)
        print(f"✓ Updated {len(input_files)} files")
    else:
        print(f"Writing output to {output_file}...")
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            for claim_record in verified_claims:
                f.write(json.dumps(claim_record, ensure_ascii=False) + '\n')
        print(f"✓ Wrote {len(verified_claims)} claims to {output_file}")

    # Summary
    print()
    print("=" * 60)
    print("Summary:")
    print(f"  Total claims: {len(input_files)}")
    print(f"  Verified: {len(verified_claims) - skipped - errors}")
    print(f"  Skipped: {skipped}")
    print(f"  Errors: {errors}")

    # Label distribution
    label_counts = {}
    for claim in verified_claims:
        label = claim.get('deberta', {}).get('label')
        if label:
            label_counts[label] = label_counts.get(label, 0) + 1

    if label_counts:
        print()
        print("Label distribution:")
        for label, count in sorted(label_counts.items()):
            print(f"  {label}: {count}")

    # Policy violations
    policy_violations = sum(
        1 for c in verified_claims
        if c.get('deberta', {}).get('policy_violation', False)
    )
    if policy_violations > 0:
        print()
        print(f"⚠ Policy violations detected: {policy_violations}")

    print("=" * 60)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Batch DeBERTa verification for extracted claims"
    )

    parser.add_argument(
        '--in',
        dest='input_pattern',
        required=True,
        help='Input claims JSON files (glob pattern, e.g., analysis/claims/*.json)'
    )

    parser.add_argument(
        '--out',
        dest='output_file',
        help='Output JSONL file (one claim per line). Required unless --inplace.'
    )

    parser.add_argument(
        '--inplace',
        action='store_true',
        help='Update input files in-place (ignores --out)'
    )

    parser.add_argument(
        '--products-dir',
        default='products',
        help='Directory containing product YAML files (default: products/)'
    )

    parser.add_argument(
        '--model',
        default='cross-encoder/nli-deberta-v3-small',
        help='HuggingFace model name (default: cross-encoder/nli-deberta-v3-small)'
    )

    parser.add_argument(
        '--device',
        default='cpu',
        choices=['cpu', 'cuda'],
        help='Device to run inference on (default: cpu)'
    )

    parser.add_argument(
        '--verify-disclaimers',
        action='store_true',
        help='Verify disclaimer claims (V1 default is to skip)'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.inplace and not args.output_file:
        parser.error("Either --out or --inplace must be specified")

    # Resolve input files
    input_pattern = Path(args.input_pattern)

    # If pattern contains glob, expand it
    if '*' in str(input_pattern):
        # Split into directory and pattern
        parts = list(input_pattern.parts)
        glob_idx = next(i for i, p in enumerate(parts) if '*' in p)
        base_dir = Path(*parts[:glob_idx])
        pattern = '/'.join(parts[glob_idx:])

        input_files = sorted(base_dir.glob(pattern))
    else:
        # Single file
        input_files = [input_pattern]

    if not input_files:
        print(f"Error: No files found matching pattern: {args.input_pattern}")
        return 1

    # Resolve output file
    output_file = Path(args.output_file) if args.output_file else None

    # Resolve products directory
    products_dir = Path(args.products_dir)

    # Run verification
    process_claims_jsonl(
        input_files=input_files,
        output_file=output_file,
        products_dir=products_dir,
        model_name=args.model,
        device=args.device,
        inplace=args.inplace,
        skip_disclaimers=not args.verify_disclaimers
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
