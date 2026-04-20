#!/usr/bin/env python3
"""
Statistical Analysis of GPT-4o Compliance Audit Results

Generates comprehensive statistics and hypothesis tests for research questions:
- RQ1: People-pleasing bias (overall violation rate)
- RQ2: Cross-engine comparison
- RQ3: Temporal unreliability
- Temperature effects
- Product-specific patterns
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats
from collections import Counter
import argparse

# Paths
RESULTS_DIR = Path(__file__).parent.parent / "results"
AUDIT_CSV = RESULTS_DIR / "gpt4o_compliance_audit.csv"
EXPERIMENTS_CSV = RESULTS_DIR / "experiments.csv"

# Output paths
SUMMARY_TXT = RESULTS_DIR / "statistical_summary.txt"
ENGINE_STATS_CSV = RESULTS_DIR / "engine_stats.csv"
TEMP_STATS_CSV = RESULTS_DIR / "temperature_stats.csv"
PRODUCT_STATS_CSV = RESULTS_DIR / "product_stats.csv"
TIME_STATS_CSV = RESULTS_DIR / "time_of_day_stats.csv"
DAY_OF_WEEK_STATS_CSV = RESULTS_DIR / "day_of_week_stats.csv"
MATERIAL_STATS_CSV = RESULTS_DIR / "material_type_stats.csv"
STATISTICAL_TESTS_TXT = RESULTS_DIR / "statistical_tests.txt"


def load_data():
    """Load audit results and merge with experiment metadata."""
    if not AUDIT_CSV.exists():
        raise FileNotFoundError(f"Audit CSV not found: {AUDIT_CSV}")

    # Load audit results
    audit_df = pd.read_csv(AUDIT_CSV)

    # Load experiments.csv for day-of-week data
    if EXPERIMENTS_CSV.exists():
        experiments_df = pd.read_csv(EXPERIMENTS_CSV)
        # Merge to add scheduled_day_of_week
        audit_df = audit_df.merge(
            experiments_df[['run_id', 'scheduled_day_of_week']],
            on='run_id',
            how='left'
        )

    # Deduplicate by run_id (keep first row per run for compliance status)
    runs_df = audit_df.drop_duplicates(subset='run_id', keep='first')

    return audit_df, runs_df


def calculate_overall_stats(runs_df):
    """Calculate overall compliance statistics."""
    total_runs = len(runs_df)
    compliant = (runs_df['compliant'] == True).sum()
    non_compliant = (runs_df['compliant'] == False).sum()

    total_violations = runs_df['violation_count'].sum()
    avg_violations = runs_df['violation_count'].mean()

    return {
        'total_runs': total_runs,
        'compliant': compliant,
        'non_compliant': non_compliant,
        'compliant_pct': compliant / total_runs * 100,
        'non_compliant_pct': non_compliant / total_runs * 100,
        'total_violations': total_violations,
        'avg_violations_per_run': avg_violations
    }


def calculate_engine_stats(runs_df):
    """Calculate violation rates by engine."""
    engine_stats = runs_df.groupby('engine').agg({
        'run_id': 'count',
        'compliant': lambda x: (x == False).sum(),
        'violation_count': ['sum', 'mean', 'std']
    }).round(2)

    engine_stats.columns = ['total_runs', 'non_compliant_runs', 'total_violations',
                            'avg_violations', 'std_violations']
    engine_stats['non_compliant_pct'] = (
        engine_stats['non_compliant_runs'] / engine_stats['total_runs'] * 100
    ).round(1)

    return engine_stats.reset_index()


def calculate_temperature_stats(runs_df):
    """Calculate violation rates by temperature."""
    temp_stats = runs_df.groupby('temperature').agg({
        'run_id': 'count',
        'compliant': lambda x: (x == False).sum(),
        'violation_count': ['sum', 'mean', 'std']
    }).round(2)

    temp_stats.columns = ['total_runs', 'non_compliant_runs', 'total_violations',
                          'avg_violations', 'std_violations']
    temp_stats['non_compliant_pct'] = (
        temp_stats['non_compliant_runs'] / temp_stats['total_runs'] * 100
    ).round(1)

    return temp_stats.reset_index()


def calculate_product_stats(runs_df):
    """Calculate violation rates by product."""
    product_stats = runs_df.groupby('product_id').agg({
        'run_id': 'count',
        'compliant': lambda x: (x == False).sum(),
        'violation_count': ['sum', 'mean', 'std']
    }).round(2)

    product_stats.columns = ['total_runs', 'non_compliant_runs', 'total_violations',
                             'avg_violations', 'std_violations']
    product_stats['non_compliant_pct'] = (
        product_stats['non_compliant_runs'] / product_stats['total_runs'] * 100
    ).round(1)

    return product_stats.reset_index()


def calculate_time_of_day_stats(runs_df):
    """Calculate violation rates by time of day."""
    time_stats = runs_df.groupby('time_of_day').agg({
        'run_id': 'count',
        'compliant': lambda x: (x == False).sum(),
        'violation_count': ['sum', 'mean', 'std']
    }).round(2)

    time_stats.columns = ['total_runs', 'non_compliant_runs', 'total_violations',
                          'avg_violations', 'std_violations']
    time_stats['non_compliant_pct'] = (
        time_stats['non_compliant_runs'] / time_stats['total_runs'] * 100
    ).round(1)

    return time_stats.reset_index()


def calculate_material_type_stats(runs_df):
    """Calculate violation rates by material type."""
    material_stats = runs_df.groupby('material_type').agg({
        'run_id': 'count',
        'compliant': lambda x: (x == False).sum(),
        'violation_count': ['sum', 'mean', 'std']
    }).round(2)

    material_stats.columns = ['total_runs', 'non_compliant_runs', 'total_violations',
                              'avg_violations', 'std_violations']
    material_stats['non_compliant_pct'] = (
        material_stats['non_compliant_runs'] / material_stats['total_runs'] * 100
    ).round(1)

    return material_stats.reset_index()


def calculate_day_of_week_stats(runs_df):
    """Calculate violation rates by day of week."""
    if 'scheduled_day_of_week' not in runs_df.columns:
        print("⚠ Warning: scheduled_day_of_week not found in data")
        return pd.DataFrame()

    # Order days properly
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    runs_df['scheduled_day_of_week'] = pd.Categorical(
        runs_df['scheduled_day_of_week'],
        categories=day_order,
        ordered=True
    )

    day_stats = runs_df.groupby('scheduled_day_of_week', observed=False).agg({
        'run_id': 'count',
        'compliant': lambda x: (x == False).sum(),
        'violation_count': ['sum', 'mean', 'std']
    }).round(2)

    day_stats.columns = ['total_runs', 'non_compliant_runs', 'total_violations',
                         'avg_violations', 'std_violations']
    day_stats['non_compliant_pct'] = (
        day_stats['non_compliant_runs'] / day_stats['total_runs'] * 100
    ).round(1)

    return day_stats.reset_index()


def calculate_severity_breakdown(audit_df):
    """Calculate severity distribution."""
    # Count violations by severity (excluding compliant materials with severity=NONE)
    violations_only = audit_df[audit_df['severity'].isin(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'])]
    severity_counts = violations_only['severity'].value_counts()

    return severity_counts


def run_statistical_tests(runs_df):
    """Run hypothesis tests for research questions."""
    results = []

    # RQ1: One-sample t-test - Are violations significantly > 0?
    violation_counts = runs_df['violation_count']
    t_stat, p_value = stats.ttest_1samp(violation_counts, 0, alternative='greater')
    results.append({
        'test': 'RQ1: People-pleasing bias (violations > 0)',
        'method': 'One-sample t-test',
        'statistic': f't = {t_stat:.3f}',
        'p_value': f'{p_value:.4e}',
        'result': 'SIGNIFICANT (p < 0.001)' if p_value < 0.001 else f'p = {p_value:.4f}'
    })

    # RQ2: Chi-square - Does engine affect compliance?
    contingency_engine = pd.crosstab(runs_df['engine'], runs_df['compliant'])
    chi2, p_value, dof, _ = stats.chi2_contingency(contingency_engine)
    results.append({
        'test': 'RQ2: Engine effect on compliance',
        'method': 'Chi-square test',
        'statistic': f'χ² = {chi2:.3f} (df={dof})',
        'p_value': f'{p_value:.4e}',
        'result': 'SIGNIFICANT (p < 0.001)' if p_value < 0.001 else f'p = {p_value:.4f}'
    })

    # RQ2: ANOVA - Does engine affect violation count?
    engines = runs_df['engine'].unique()
    engine_groups = [runs_df[runs_df['engine'] == e]['violation_count'].values for e in engines]
    f_stat, p_value = stats.f_oneway(*engine_groups)
    results.append({
        'test': 'RQ2: Engine effect on violation count',
        'method': 'One-way ANOVA',
        'statistic': f'F = {f_stat:.3f}',
        'p_value': f'{p_value:.4e}',
        'result': 'SIGNIFICANT (p < 0.001)' if p_value < 0.001 else f'p = {p_value:.4f}'
    })

    # Temperature effect on compliance
    contingency_temp = pd.crosstab(runs_df['temperature'], runs_df['compliant'])
    chi2, p_value, dof, _ = stats.chi2_contingency(contingency_temp)
    results.append({
        'test': 'Temperature effect on compliance',
        'method': 'Chi-square test',
        'statistic': f'χ² = {chi2:.3f} (df={dof})',
        'p_value': f'{p_value:.4e}',
        'result': 'SIGNIFICANT (p < 0.001)' if p_value < 0.001 else f'p = {p_value:.4f}'
    })

    # Temperature effect on violation count
    temps = sorted(runs_df['temperature'].unique())
    temp_groups = [runs_df[runs_df['temperature'] == t]['violation_count'].values for t in temps]
    f_stat, p_value = stats.f_oneway(*temp_groups)
    results.append({
        'test': 'Temperature effect on violation count',
        'method': 'One-way ANOVA',
        'statistic': f'F = {f_stat:.3f}',
        'p_value': f'{p_value:.4e}',
        'result': 'SIGNIFICANT (p < 0.001)' if p_value < 0.001 else f'p = {p_value:.4f}'
    })

    # RQ3: Time-of-day effect (temporal consistency)
    contingency_time = pd.crosstab(runs_df['time_of_day'], runs_df['compliant'])
    chi2, p_value, dof, _ = stats.chi2_contingency(contingency_time)
    results.append({
        'test': 'RQ3: Time-of-day effect on compliance',
        'method': 'Chi-square test',
        'statistic': f'χ² = {chi2:.3f} (df={dof})',
        'p_value': f'{p_value:.4e}',
        'result': 'SIGNIFICANT (p < 0.001)' if p_value < 0.001 else f'p = {p_value:.4f}'
    })

    # Product effect
    contingency_product = pd.crosstab(runs_df['product_id'], runs_df['compliant'])
    chi2, p_value, dof, _ = stats.chi2_contingency(contingency_product)
    results.append({
        'test': 'Product effect on compliance',
        'method': 'Chi-square test',
        'statistic': f'χ² = {chi2:.3f} (df={dof})',
        'p_value': f'{p_value:.4e}',
        'result': 'SIGNIFICANT (p < 0.001)' if p_value < 0.001 else f'p = {p_value:.4f}'
    })

    # Day-of-week effect (7-day temporal drift)
    if 'scheduled_day_of_week' in runs_df.columns:
        contingency_day = pd.crosstab(runs_df['scheduled_day_of_week'], runs_df['compliant'])
        chi2, p_value, dof, _ = stats.chi2_contingency(contingency_day)
        results.append({
            'test': 'RQ3: Day-of-week effect on compliance (7-day drift)',
            'method': 'Chi-square test',
            'statistic': f'χ² = {chi2:.3f} (df={dof})',
            'p_value': f'{p_value:.4e}',
            'result': 'SIGNIFICANT (p < 0.001)' if p_value < 0.001 else f'p = {p_value:.4f}'
        })

    return pd.DataFrame(results)


def generate_summary_report(overall, engine_stats, temp_stats, product_stats,
                           time_stats, day_stats, severity_counts, test_results):
    """Generate comprehensive text summary."""
    report = []
    report.append("=" * 80)
    report.append("GPT-4O COMPLIANCE AUDIT - STATISTICAL ANALYSIS")
    report.append("=" * 80)
    report.append("")

    # Overall statistics
    report.append("OVERALL STATISTICS")
    report.append("-" * 80)
    report.append(f"Total runs analyzed:        {overall['total_runs']}")
    report.append(f"  Compliant:                {overall['compliant']} ({overall['compliant_pct']:.1f}%)")
    report.append(f"  Non-compliant:            {overall['non_compliant']} ({overall['non_compliant_pct']:.1f}%)")
    report.append(f"Total violations:           {overall['total_violations']}")
    report.append(f"Average violations/run:     {overall['avg_violations_per_run']:.2f}")
    report.append("")

    # Severity breakdown
    report.append("SEVERITY BREAKDOWN")
    report.append("-" * 80)
    for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        count = severity_counts.get(severity, 0)
        report.append(f"  {severity:<10} {count:>6}")
    report.append("")

    # Engine comparison
    report.append("VIOLATION RATE BY ENGINE")
    report.append("-" * 80)
    for _, row in engine_stats.iterrows():
        report.append(f"  {row['engine']:<15} {row['non_compliant_pct']:>6.1f}% "
                     f"({row['non_compliant_runs']}/{row['total_runs']} runs, "
                     f"avg {row['avg_violations']:.2f} violations)")
    report.append("")

    # Temperature comparison
    report.append("VIOLATION RATE BY TEMPERATURE")
    report.append("-" * 80)
    for _, row in temp_stats.iterrows():
        report.append(f"  Temp {row['temperature']:<8} {row['non_compliant_pct']:>6.1f}% "
                     f"({row['non_compliant_runs']}/{row['total_runs']} runs, "
                     f"avg {row['avg_violations']:.2f} violations)")
    report.append("")

    # Product comparison
    report.append("VIOLATION RATE BY PRODUCT")
    report.append("-" * 80)
    for _, row in product_stats.iterrows():
        report.append(f"  {row['product_id']:<30} {row['non_compliant_pct']:>6.1f}% "
                     f"({row['non_compliant_runs']}/{row['total_runs']} runs, "
                     f"avg {row['avg_violations']:.2f} violations)")
    report.append("")

    # Time of day comparison
    report.append("VIOLATION RATE BY TIME OF DAY")
    report.append("-" * 80)
    for _, row in time_stats.iterrows():
        report.append(f"  {row['time_of_day']:<15} {row['non_compliant_pct']:>6.1f}% "
                     f"({row['non_compliant_runs']}/{row['total_runs']} runs, "
                     f"avg {row['avg_violations']:.2f} violations)")
    report.append("")

    # Day of week comparison
    if not day_stats.empty:
        report.append("VIOLATION RATE BY DAY OF WEEK (7-DAY TEMPORAL DRIFT)")
        report.append("-" * 80)
        for _, row in day_stats.iterrows():
            report.append(f"  {row['scheduled_day_of_week']:<15} {row['non_compliant_pct']:>6.1f}% "
                         f"({row['non_compliant_runs']}/{row['total_runs']} runs, "
                         f"avg {row['avg_violations']:.2f} violations)")
        report.append("")

    # Statistical tests
    report.append("STATISTICAL HYPOTHESIS TESTS")
    report.append("-" * 80)
    for _, test in test_results.iterrows():
        report.append(f"\n{test['test']}")
        report.append(f"  Method:     {test['method']}")
        report.append(f"  Statistic:  {test['statistic']}")
        report.append(f"  P-value:    {test['p_value']}")
        report.append(f"  Result:     {test['result']}")
    report.append("")

    report.append("=" * 80)
    report.append("END OF REPORT")
    report.append("=" * 80)

    return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description='Statistical analysis of GPT-4o audit results')
    parser.add_argument(
        '--day-of-week-only',
        action='store_true',
        help='Only calculate and display day-of-week analysis'
    )
    args = parser.parse_args()

    print("=" * 80)
    print("GPT-4O STATISTICAL ANALYSIS")
    print("=" * 80)
    print()

    # Load data
    print("Loading audit results...")
    audit_df, runs_df = load_data()
    print(f"✓ Loaded {len(runs_df)} runs ({len(audit_df)} total rows)")
    print()

    # Day-of-week only mode
    if args.day_of_week_only:
        print("Running day-of-week analysis only...")
        print()
        day_stats = calculate_day_of_week_stats(runs_df)

        if day_stats.empty:
            print("⚠ No day-of-week data available")
            return

        print("VIOLATION RATE BY DAY OF WEEK (7-DAY TEMPORAL DRIFT)")
        print("=" * 80)
        for _, row in day_stats.iterrows():
            print(f"  {row['scheduled_day_of_week']:<15} {row['non_compliant_pct']:>6.1f}% "
                  f"({int(row['non_compliant_runs'])}/{int(row['total_runs'])} runs, "
                  f"avg {row['avg_violations']:.2f} violations)")
        print()

        # Chi-square test
        from scipy import stats as sp_stats
        contingency = pd.crosstab(runs_df['scheduled_day_of_week'], runs_df['compliant'])
        chi2, p_value, dof, _ = sp_stats.chi2_contingency(contingency)
        print("Statistical Test:")
        print(f"  Chi-square: χ² = {chi2:.3f} (df={dof})")
        print(f"  P-value: {p_value:.4f}")
        print(f"  Result: {'SIGNIFICANT (p < 0.05)' if p_value < 0.05 else 'NOT SIGNIFICANT'}")
        print()

        # Save
        day_stats.to_csv(DAY_OF_WEEK_STATS_CSV, index=False)
        print(f"✓ Saved to {DAY_OF_WEEK_STATS_CSV}")
        return

    # Calculate statistics
    print("Calculating statistics...")
    overall = calculate_overall_stats(runs_df)
    engine_stats = calculate_engine_stats(runs_df)
    temp_stats = calculate_temperature_stats(runs_df)
    product_stats = calculate_product_stats(runs_df)
    time_stats = calculate_time_of_day_stats(runs_df)
    day_stats = calculate_day_of_week_stats(runs_df)
    material_stats = calculate_material_type_stats(runs_df)
    severity_counts = calculate_severity_breakdown(audit_df)
    print("✓ Statistics calculated")
    print()

    # Run statistical tests
    print("Running hypothesis tests...")
    test_results = run_statistical_tests(runs_df)
    print("✓ Tests complete")
    print()

    # Generate summary report
    print("Generating summary report...")
    summary = generate_summary_report(
        overall, engine_stats, temp_stats, product_stats,
        time_stats, day_stats, severity_counts, test_results
    )

    # Save outputs
    print("Saving results...")
    with open(SUMMARY_TXT, 'w') as f:
        f.write(summary)
    print(f"✓ Summary: {SUMMARY_TXT}")

    engine_stats.to_csv(ENGINE_STATS_CSV, index=False)
    print(f"✓ Engine stats: {ENGINE_STATS_CSV}")

    temp_stats.to_csv(TEMP_STATS_CSV, index=False)
    print(f"✓ Temperature stats: {TEMP_STATS_CSV}")

    product_stats.to_csv(PRODUCT_STATS_CSV, index=False)
    print(f"✓ Product stats: {PRODUCT_STATS_CSV}")

    time_stats.to_csv(TIME_STATS_CSV, index=False)
    print(f"✓ Time-of-day stats: {TIME_STATS_CSV}")

    if not day_stats.empty:
        day_stats.to_csv(DAY_OF_WEEK_STATS_CSV, index=False)
        print(f"✓ Day-of-week stats: {DAY_OF_WEEK_STATS_CSV}")

    material_stats.to_csv(MATERIAL_STATS_CSV, index=False)
    print(f"✓ Material type stats: {MATERIAL_STATS_CSV}")

    test_results.to_csv(STATISTICAL_TESTS_TXT.with_suffix('.csv'), index=False)
    print(f"✓ Statistical tests: {STATISTICAL_TESTS_TXT.with_suffix('.csv')}")
    print()

    # Print summary to console
    print(summary)
    print()
    print("=" * 80)
    print("✓ ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
