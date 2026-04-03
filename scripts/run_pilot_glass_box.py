#!/usr/bin/env python3
"""
Run Glass Box audit on all 54 pilot materials.
Save results to results/pilot_analysis/ (separate from main experiment).
"""

import sys
import os
import pandas as pd
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.glass_box_audit import audit_marketing_material

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    # Load experiments
    df = pd.read_csv('results/experiments.csv')
    completed = df[df['status'] == 'completed'].copy()

    logger.info(f"Found {len(completed)} completed runs to audit")

    # Create output directory
    output_dir = Path('results/pilot_analysis')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Track results
    results = []

    for idx, row in completed.iterrows():
        run_id = row['run_id']
        product_id = row['product_id']
        engine = row['engine']
        material_type = row['material_type']

        logger.info(f"[{idx+1}/{len(completed)}] Processing {run_id[:8]}... ({product_id}, {engine}, {material_type})")

        # Get paths
        marketing_file = Path(f"outputs/{run_id}.txt")
        product_yaml = Path(f"products/{product_id}.yaml")

        if not marketing_file.exists():
            logger.warning(f"  ✗ Marketing file not found: {marketing_file}")
            continue

        if not product_yaml.exists():
            logger.warning(f"  ✗ Product YAML not found: {product_yaml}")
            continue

        # Run Glass Box audit
        try:
            df_violations = audit_marketing_material(
                marketing_file=str(marketing_file),
                product_yaml_path=str(product_yaml),
                output_csv=None  # Don't save individual CSVs
            )

            violation_count = len(df_violations)
            logger.info(f"  ✓ Found {violation_count} violations")

            # Save individual CSV to pilot_analysis
            csv_path = output_dir / f"{run_id}_violations.csv"
            df_violations.to_csv(csv_path, index=False)

            # Track summary
            results.append({
                'run_id': run_id,
                'product_id': product_id,
                'engine': engine,
                'material_type': material_type,
                'repetition_id': row['repetition_id'],
                'violation_count': violation_count,
                'csv_path': str(csv_path)
            })

        except Exception as e:
            logger.error(f"  ✗ Error auditing {run_id}: {e}")
            continue

    # Save summary
    df_summary = pd.DataFrame(results)
    summary_path = output_dir / 'pilot_violations_summary.csv'
    df_summary.to_csv(summary_path, index=False)

    logger.info(f"\n✓ Completed {len(results)}/{len(completed)} audits")
    logger.info(f"✓ Saved summary: {summary_path}")

    # Print quick stats
    print("\n" + "=" * 80)
    print("PILOT AUDIT SUMMARY")
    print("=" * 80)
    print(f"\nTotal violations: {df_summary['violation_count'].sum()}")
    print(f"Mean violations per file: {df_summary['violation_count'].mean():.2f}")
    print(f"Median violations per file: {df_summary['violation_count'].median():.0f}")

    print("\nBy engine:")
    print(df_summary.groupby('engine')['violation_count'].agg(['count', 'sum', 'mean']).to_string())

    print("\nBy product:")
    print(df_summary.groupby('product_id')['violation_count'].agg(['count', 'sum', 'mean']).to_string())

    print("\nBy material type:")
    print(df_summary.groupby('material_type')['violation_count'].agg(['count', 'sum', 'mean']).to_string())


if __name__ == '__main__':
    main()
