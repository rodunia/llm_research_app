#!/usr/bin/env python3
"""
Run Glass Box audit on all 54 pilot materials using existing audit infrastructure.
Save results to results/pilot_analysis/.
"""

import sys
import os
from pathlib import Path
import pandas as pd
import csv

# Add parent directory
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import Glass Box
from analysis.glass_box_audit import (
    audit_single_run,
    get_completed_runs,
    load_completed_run_ids
)
from analysis.nli_judge import NLIJudge

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    # Create output directory
    output_dir = Path('results/pilot_analysis')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize NLI judge
    logger.info("Initializing NLI judge...")
    judge = NLIJudge()

    # Get all completed runs
    logger.info("Loading completed runs...")
    df_runs = get_completed_runs()
    logger.info(f"Found {len(df_runs)} completed runs")

    # Process each run
    results = []
    all_violations = []

    for idx, row in df_runs.iterrows():
        run_id = row['run_id']
        logger.info(f"[{idx+1}/{len(df_runs)}] Auditing {run_id[:8]}... ({row['product_id']}, {row['engine']})")

        try:
            # Audit this run
            result = audit_single_run(run_id, row.to_dict(), judge)

            # Save violations CSV for this run
            if result['violations']:
                violations_df = pd.DataFrame(result['violations'])
                csv_path = output_dir / f"{run_id}_violations.csv"
                violations_df.to_csv(csv_path, index=False)

                # Add run_id to violations for later analysis
                for viol in result['violations']:
                    viol['run_id'] = run_id
                all_violations.extend(result['violations'])

            # Track summary
            results.append({
                'run_id': run_id,
                'product_id': row['product_id'],
                'engine': row['engine'],
                'material_type': row['material_type'],
                'repetition_id': row['repetition_id'],
                'violation_count': len(result['violations']),
                'total_claims': result['total_claims'],
                'csv_path': str(output_dir / f"{run_id}_violations.csv") if result['violations'] else None
            })

            logger.info(f"  ✓ {len(result['violations'])} violations / {result['total_claims']} claims")

        except Exception as e:
            logger.error(f"  ✗ Error: {e}")
            results.append({
                'run_id': run_id,
                'product_id': row['product_id'],
                'engine': row['engine'],
                'material_type': row['material_type'],
                'repetition_id': row['repetition_id'],
                'violation_count': 0,
                'total_claims': 0,
                'csv_path': None
            })

    # Save summary
    df_summary = pd.DataFrame(results)
    summary_path = output_dir / 'pilot_violations_summary.csv'
    df_summary.to_csv(summary_path, index=False)
    logger.info(f"\n✓ Saved summary: {summary_path}")

    # Save all violations combined
    if all_violations:
        df_all_violations = pd.DataFrame(all_violations)
        all_viols_path = output_dir / 'all_violations.csv'
        df_all_violations.to_csv(all_viols_path, index=False)
        logger.info(f"✓ Saved all violations: {all_viols_path}")

    # Print quick stats
    print("\n" + "=" * 80)
    print("PILOT AUDIT SUMMARY")
    print("=" * 80)
    print(f"\nCompleted: {len(results)}/{len(df_runs)} audits")
    print(f"Total violations: {df_summary['violation_count'].sum()}")
    print(f"Total claims: {df_summary['total_claims'].sum()}")
    print(f"Violation rate: {df_summary['violation_count'].sum() / df_summary['total_claims'].sum() * 100:.2f}%")
    print(f"\nMean violations per file: {df_summary['violation_count'].mean():.2f}")
    print(f"Median violations per file: {df_summary['violation_count'].median():.0f}")

    print("\n" + "-" * 80)
    print("BY ENGINE")
    print("-" * 80)
    print(df_summary.groupby('engine')['violation_count'].agg(['count', 'sum', 'mean']).to_string())

    print("\n" + "-" * 80)
    print("BY PRODUCT")
    print("-" * 80)
    print(df_summary.groupby('product_id')['violation_count'].agg(['count', 'sum', 'mean']).to_string())

    print("\n" + "-" * 80)
    print("BY MATERIAL TYPE")
    print("-" * 80)
    print(df_summary.groupby('material_type')['violation_count'].agg(['count', 'sum', 'mean']).to_string())


if __name__ == '__main__':
    main()
