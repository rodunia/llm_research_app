#!/usr/bin/env python3
"""
Run Glass Box audit on errors/ folder files (30 files with progressive corruption).
"""

import sys
import os
import yaml
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.glass_box_audit import audit_single_file, NLIJudge
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

    # Initialize NLI judge once (reuse for all files)
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

        # Run Glass Box audit
        try:
            violations = audit_single_file(
                marketing_text=marketing_text,
                product_spec=product_spec,
                nli_judge=nli_judge,
                output_csv=output_csv,
                file_identifier=file_prefix
            )

            # Count violations
            violation_count = len(violations) if violations else 0
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
            logger.error(f"Error processing {file_prefix}: {e}")
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
