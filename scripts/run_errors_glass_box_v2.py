#!/usr/bin/env python3
"""
Run Glass Box audit on errors/ folder files using direct function calls.
"""

import sys
import os
import yaml
import json
import pandas as pd
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.glass_box_audit import (
    NLIJudge,
    extract_atomic_claims,
    flatten_authorized_claims,
    flatten_specs,
    flatten_prohibited_claims,
    flatten_clarifications,
    classify_claim_category
)

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def audit_file(marketing_text: str, product_spec: dict, file_id: str, nli_judge: NLIJudge) -> pd.DataFrame:
    """
    Audit a single marketing file using Glass Box methodology.

    Returns DataFrame with violations.
    """

    # Extract atomic claims
    logger.info(f"  Extracting claims...")
    claims_result = extract_atomic_claims(
        material_content=marketing_text,
        product_name=product_spec.get('product_name', 'Unknown'),
        material_type='FAQ'
    )

    core_claims = claims_result.get('core_claims', [])
    disclaimers = claims_result.get('disclaimers', [])

    logger.info(f"  Found {len(core_claims)} core claims, {len(disclaimers)} disclaimers")

    # Flatten product spec
    authorized_claims = flatten_authorized_claims(product_spec)
    specs = flatten_specs(product_spec)
    prohibited_claims = flatten_prohibited_claims(product_spec)
    clarifications = flatten_clarifications(product_spec)

    # Verify claims
    logger.info(f"  Verifying {len(core_claims)} claims...")
    violations = []

    for claim in core_claims:
        result = nli_judge.verify_claim(
            claim=claim,
            authorized_claims=authorized_claims,
            specs=specs,
            prohibited_claims=prohibited_claims,
            clarifications=clarifications
        )

        if result['is_violation']:
            violations.append({
                'Filename': file_id,
                'Status': 'FAIL',
                'Violated_Rule': result['violated_rule'],
                'Extracted_Claim': claim,
                'Confidence_Score': result['contradiction_score']
            })

    # Return as DataFrame
    return pd.DataFrame(violations)

def main():
    """Run Glass Box on all 30 error files."""

    # File mapping
    files = []
    for i in range(1, 11):
        files.append(('smartphone_mid', f'errors_smartphone_{i}'))
        files.append(('supplement_melatonin', f'errors_melatonin_{i}'))
        files.append(('cryptocurrency_corecoin', f'errors_corecoin_{i}'))

    # Output directory
    output_dir = Path('results/errors_analysis/glass_box')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize NLI judge once
    logger.info("Initializing NLI Judge...")
    nli_judge = NLIJudge(use_semantic_filter=False)

    # Process each file
    results = []
    for idx, (product_id, file_prefix) in enumerate(files, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing {idx}/30: {file_prefix}")
        logger.info(f"{'='*60}")

        # Paths
        input_file = Path(f'outputs/{file_prefix}.txt')
        product_yaml = Path(f'products/{product_id}.yaml')
        output_csv = output_dir / f'{file_prefix}.csv'

        if not input_file.exists():
            logger.error(f"Input file not found: {input_file}")
            continue

        if not product_yaml.exists():
            logger.error(f"Product YAML not found: {product_yaml}")
            continue

        # Load product spec
        with open(product_yaml, 'r') as f:
            product_spec = yaml.safe_load(f)

        # Load marketing text
        with open(input_file, 'r') as f:
            marketing_text = f.read()

        # Run audit
        try:
            violations_df = audit_file(marketing_text, product_spec, file_prefix, nli_judge)

            # Save CSV
            violations_df.to_csv(output_csv, index=False)

            # Count violations
            violation_count = len(violations_df)
            has_errors = violation_count > 0

            logger.info(f"✓ {file_prefix}: {violation_count} violations detected")

            results.append({
                'file': file_prefix,
                'product': product_id,
                'errors_detected': has_errors,
                'violation_count': violation_count,
                'output_csv': str(output_csv)
            })

        except Exception as e:
            logger.error(f"Error processing {file_prefix}: {e}", exc_info=True)
            results.append({
                'file': file_prefix,
                'product': product_id,
                'errors_detected': False,
                'violation_count': 0,
                'error': str(e)
            })

    # Save summary
    summary_file = output_dir / 'summary.json'
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"\n{'='*60}")
    logger.info(f"GLASS BOX ANALYSIS COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Processed: {len(results)}/30 files")
    logger.info(f"Detected errors: {sum(1 for r in results if r['errors_detected'])}/30")
    logger.info(f"Summary saved: {summary_file}")

if __name__ == '__main__':
    main()
