#!/usr/bin/env python3
"""
Analyze pilot results for hypothesis testing.

Research Questions:
1. People-pleasing bias: Do LLMs generate overly positive content that violates compliance?
2. Induced errors: How frequently do LLMs introduce factual inaccuracies?
3. Temporal unreliability: Do LLMs produce inconsistent outputs across repetitions?
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats
import glob

def load_violations():
    """Load all violation CSVs from pilot_analysis."""
    violations = []

    for csv_path in glob.glob('results/pilot_analysis/*_violations.csv'):
        run_id = Path(csv_path).stem.replace('_violations', '')
        df_viol = pd.read_csv(csv_path)
        df_viol['run_id'] = run_id
        violations.append(df_viol)

    if not violations:
        return pd.DataFrame()

    return pd.concat(violations, ignore_index=True)


def main():
    # Load data
    df_exp = pd.read_csv('results/experiments.csv')
    df_summary = pd.read_csv('results/pilot_analysis/pilot_violations_summary.csv')
    df_violations = load_violations()

    print("=" * 80)
    print("PILOT STUDY HYPOTHESIS TESTING")
    print("=" * 80)

    # =========================================================================
    # HYPOTHESIS 1: PEOPLE-PLEASING BIAS
    # =========================================================================
    print("\n" + "=" * 80)
    print("H1: PEOPLE-PLEASING BIAS")
    print("=" * 80)
    print("\nHypothesis: LLMs generate overly positive marketing content that violates")
    print("compliance rules at a rate significantly greater than 0%")

    # Overall violation rate
    total_files = len(df_summary)
    files_with_violations = len(df_summary[df_summary['violation_count'] > 0])
    violation_rate = files_with_violations / total_files * 100

    print(f"\nOverall Results:")
    print(f"  Files analyzed: {total_files}")
    print(f"  Files with violations: {files_with_violations}")
    print(f"  Violation rate: {violation_rate:.1f}%")
    print(f"  Total violations: {df_summary['violation_count'].sum()}")
    print(f"  Mean violations per file: {df_summary['violation_count'].mean():.2f}")
    print(f"  Median violations per file: {df_summary['violation_count'].median():.0f}")

    # One-sample t-test (H0: violation rate = 0%)
    t_stat, p_value = stats.ttest_1samp(df_summary['violation_count'], 0)
    print(f"\nOne-sample t-test (H0: mean violations = 0):")
    print(f"  t-statistic: {t_stat:.4f}")
    print(f"  p-value: {p_value:.6f}")
    print(f"  Result: {'REJECT H0 (violations > 0)' if p_value < 0.05 else 'FAIL TO REJECT H0'}")

    # By engine
    print(f"\nBy Engine:")
    engine_stats = df_summary.groupby('engine')['violation_count'].agg(['count', 'sum', 'mean', 'std'])
    print(engine_stats.to_string())

    # Kruskal-Wallis test (non-parametric ANOVA)
    openai_viols = df_summary[df_summary['engine'] == 'openai']['violation_count']
    google_viols = df_summary[df_summary['engine'] == 'google']['violation_count']
    mistral_viols = df_summary[df_summary['engine'] == 'mistral']['violation_count']

    h_stat, kw_p = stats.kruskal(openai_viols, google_viols, mistral_viols)
    print(f"\nKruskal-Wallis test (engine effect):")
    print(f"  H-statistic: {h_stat:.4f}")
    print(f"  p-value: {kw_p:.6f}")
    print(f"  Result: {'Significant engine effect' if kw_p < 0.05 else 'No significant engine effect'}")

    # =========================================================================
    # HYPOTHESIS 2: INDUCED ERRORS & HALLUCINATIONS
    # =========================================================================
    print("\n" + "=" * 80)
    print("H2: INDUCED ERRORS & HALLUCINATIONS")
    print("=" * 80)
    print("\nHypothesis: LLMs introduce factual inaccuracies when generating marketing content")

    if len(df_violations) > 0:
        # Error type distribution
        print(f"\nViolation Type Distribution:")
        violation_types = df_violations['Violated_Rule'].value_counts()
        print(violation_types.head(10).to_string())

        # High-confidence violations (severe errors)
        high_conf = df_violations[df_violations['Confidence_Score'] > 0.95]
        print(f"\nHigh-Confidence Violations (>0.95):")
        print(f"  Count: {len(high_conf)}/{len(df_violations)} ({len(high_conf)/len(df_violations)*100:.1f}%)")
        print(f"  Mean confidence: {df_violations['Confidence_Score'].mean():.4f}")

        # Top severe violation types
        print(f"\nTop 5 High-Confidence Violation Types:")
        print(high_conf['Violated_Rule'].value_counts().head(5).to_string())
    else:
        print("\n  No violations found (unlikely - check data)")

    # By product (regulatory domain)
    print(f"\nBy Product (Regulatory Domain):")
    product_stats = df_summary.groupby('product_id')['violation_count'].agg(['count', 'sum', 'mean', 'std'])
    print(product_stats.to_string())

    # Kruskal-Wallis test (product effect)
    smartphone_viols = df_summary[df_summary['product_id'] == 'smartphone_mid']['violation_count']
    crypto_viols = df_summary[df_summary['product_id'] == 'cryptocurrency_corecoin']['violation_count']
    melatonin_viols = df_summary[df_summary['product_id'] == 'supplement_melatonin']['violation_count']

    h_stat_prod, kw_p_prod = stats.kruskal(smartphone_viols, crypto_viols, melatonin_viols)
    print(f"\nKruskal-Wallis test (product effect):")
    print(f"  H-statistic: {h_stat_prod:.4f}")
    print(f"  p-value: {kw_p_prod:.6f}")
    print(f"  Result: {'Significant product effect' if kw_p_prod < 0.05 else 'No significant product effect'}")

    # =========================================================================
    # HYPOTHESIS 3: TEMPORAL UNRELIABILITY
    # =========================================================================
    print("\n" + "=" * 80)
    print("H3: TEMPORAL UNRELIABILITY")
    print("=" * 80)
    print("\nHypothesis: LLMs produce inconsistent outputs across repetitions")

    # Within-condition variance (group by product × engine × material)
    df_summary['condition'] = (df_summary['product_id'] + '_' +
                                df_summary['engine'] + '_' +
                                df_summary['material_type'])

    print(f"\nWithin-Condition Variance (across 3 repetitions):")
    variance_stats = df_summary.groupby('condition')['violation_count'].agg(['mean', 'std', 'var'])
    variance_stats['cv'] = variance_stats['std'] / variance_stats['mean']  # Coefficient of variation

    print(f"\nCoefficient of Variation (CV) Statistics:")
    print(f"  Mean CV: {variance_stats['cv'].mean():.4f}")
    print(f"  Median CV: {variance_stats['cv'].median():.4f}")
    print(f"  Max CV: {variance_stats['cv'].max():.4f}")

    print(f"\nTop 5 Most Variable Conditions:")
    print(variance_stats.nlargest(5, 'cv')[['mean', 'std', 'cv']].to_string())

    print(f"\nTop 5 Most Stable Conditions:")
    print(variance_stats.nsmallest(5, 'cv')[['mean', 'std', 'cv']].to_string())

    # Check if any condition has perfect consistency (CV = 0)
    perfect_consistency = variance_stats[variance_stats['cv'] == 0]
    print(f"\nPerfectly Consistent Conditions (CV = 0): {len(perfect_consistency)}/{len(variance_stats)}")

    # =========================================================================
    # SUMMARY FOR PAPER
    # =========================================================================
    print("\n" + "=" * 80)
    print("SUMMARY FOR PAPER")
    print("=" * 80)

    print(f"""
**Pilot Study Results (N=54 marketing materials)**

**H1: People-Pleasing Bias**
- {violation_rate:.1f}% of materials contained compliance violations
- Mean: {df_summary['violation_count'].mean():.2f} violations per file (SD={df_summary['violation_count'].std():.2f})
- One-sample t-test: t={t_stat:.2f}, p<{p_value:.4f} {'✓ SIGNIFICANT' if p_value < 0.05 else '✗ NOT SIGNIFICANT'}
- Engine effect: H={h_stat:.2f}, p={kw_p:.4f} {'✓ SIGNIFICANT' if kw_p < 0.05 else '✗ NOT SIGNIFICANT'}

**H2: Induced Errors**
- Total violations: {df_summary['violation_count'].sum()}
- High-confidence violations (>0.95): {len(high_conf) if len(df_violations) > 0 else 0}
- Product effect: H={h_stat_prod:.2f}, p={kw_p_prod:.4f} {'✓ SIGNIFICANT' if kw_p_prod < 0.05 else '✗ NOT SIGNIFICANT'}

**H3: Temporal Unreliability**
- Mean coefficient of variation: {variance_stats['cv'].mean():.4f}
- Perfectly consistent conditions: {len(perfect_consistency)}/{len(variance_stats)}
- Result: {'✓ EVIDENCE OF TEMPORAL INSTABILITY' if variance_stats['cv'].mean() > 0.1 else '✗ STABLE ACROSS REPETITIONS'}

**Recommendation**: {'Scale to full study (1,620 runs)' if p_value < 0.05 else 'Refine methodology before scaling'}
""")

    # Save detailed results
    output_path = Path('results/pilot_analysis/HYPOTHESIS_TESTING_RESULTS.txt')
    with open(output_path, 'w') as f:
        f.write("PILOT STUDY HYPOTHESIS TESTING RESULTS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"H1 p-value: {p_value}\n")
        f.write(f"H1 engine effect p-value: {kw_p}\n")
        f.write(f"H2 product effect p-value: {kw_p_prod}\n")
        f.write(f"H3 mean CV: {variance_stats['cv'].mean()}\n")

    print(f"\n✓ Saved: {output_path}")


if __name__ == '__main__':
    main()
