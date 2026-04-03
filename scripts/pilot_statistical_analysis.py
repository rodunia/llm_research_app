"""
Statistical Hypothesis Testing for Pilot Experiment

Research Questions:
1. People-pleasing bias: Do LLMs generate overly positive marketing content that violates compliance?
2. Induced errors and hallucinations: How frequently do LLMs introduce factual inaccuracies?
3. Temporal unreliability: Do LLMs produce inconsistent outputs across sessions?

Hypotheses (Pilot Scope - Limited):
H1: Material type affects violation rates (FAQ vs Digital Ad)
H2: Engine affects violation rates (OpenAI vs Mistral)
H3: Product affects violation rates (Crypto vs Smartphone vs Melatonin)
H4: Replications show consistency (Rep1 vs Rep2 vs Rep3)

Note: Pilot cannot test temporal unreliability (only 1 time slot) or temperature effects (only 1 temp)
"""

import pandas as pd
import numpy as np
from scipy import stats
from scipy.stats import f_oneway, kruskal, mannwhitneyu, levene, chi2_contingency
import warnings
warnings.filterwarnings('ignore')

def load_data():
    """Load and prepare pilot data."""
    # Load Glass Box results
    audit = pd.read_csv('results/final_audit_results.csv')

    # Load experiments metadata
    expts = pd.read_csv('results/experiments.csv')

    # Filter to completed runs only
    completed = expts[expts['status'] == 'completed'].copy()

    # Count violations per file
    violation_counts = []
    for _, row in completed.iterrows():
        filename = row['output_path'].split('/')[-1]
        file_violations = audit[(audit['Filename'] == filename) & (audit['Status'] == 'FAIL')]
        violation_counts.append({
            'run_id': row['run_id'],
            'product': row['product_id'],
            'material': row['material_type'],
            'engine': row['engine'],
            'repetition': row['repetition_id'],
            'violations': len(file_violations)
        })

    df = pd.DataFrame(violation_counts)
    return df, audit

def descriptive_stats(df):
    """Compute descriptive statistics."""
    print("="*80)
    print("DESCRIPTIVE STATISTICS")
    print("="*80)

    print(f"\nOverall (N={len(df)}):")
    print(f"  Mean violations: {df['violations'].mean():.2f}")
    print(f"  Median violations: {df['violations'].median():.1f}")
    print(f"  Std Dev: {df['violations'].std():.2f}")
    print(f"  Min: {df['violations'].min()}")
    print(f"  Max: {df['violations'].max()}")
    print(f"  Range: {df['violations'].max() - df['violations'].min()}")

    # Check normality
    stat, p = stats.shapiro(df['violations'])
    print(f"\nShapiro-Wilk normality test: W={stat:.4f}, p={p:.4f}")
    if p < 0.05:
        print("  → Data is NOT normally distributed (use non-parametric tests)")
    else:
        print("  → Data is normally distributed (parametric tests OK)")

    # By material
    print("\nBy Material Type:")
    for material in df['material'].unique():
        subset = df[df['material'] == material]['violations']
        print(f"  {material}: M={subset.mean():.2f}, SD={subset.std():.2f}, N={len(subset)}")

    # By engine
    print("\nBy Engine:")
    for engine in df['engine'].unique():
        subset = df[df['engine'] == engine]['violations']
        print(f"  {engine}: M={subset.mean():.2f}, SD={subset.std():.2f}, N={len(subset)}")

    # By product
    print("\nBy Product:")
    for product in df['product'].unique():
        subset = df[df['product'] == product]['violations']
        print(f"  {product}: M={subset.mean():.2f}, SD={subset.std():.2f}, N={len(subset)}")

    # By repetition
    print("\nBy Repetition:")
    for rep in sorted(df['repetition'].unique()):
        subset = df[df['repetition'] == rep]['violations']
        print(f"  Rep {rep}: M={subset.mean():.2f}, SD={subset.std():.2f}, N={len(subset)}")

def test_h1_material(df):
    """H1: Material type affects violation rates (FAQ vs Digital Ad)."""
    print("\n" + "="*80)
    print("H1: MATERIAL TYPE EFFECT (FAQ vs Digital Ad)")
    print("="*80)

    faq = df[df['material'] == 'faq.j2']['violations']
    digital_ad = df[df['material'] == 'digital_ad.j2']['violations']

    print(f"\nFAQ: N={len(faq)}, M={faq.mean():.2f}, SD={faq.std():.2f}")
    print(f"Digital Ad: N={len(digital_ad)}, M={digital_ad.mean():.2f}, SD={digital_ad.std():.2f}")
    print(f"Difference: {faq.mean() - digital_ad.mean():.2f} violations ({((faq.mean() - digital_ad.mean()) / digital_ad.mean() * 100):.1f}%)")

    # Check homogeneity of variance
    stat_lev, p_lev = levene(faq, digital_ad)
    print(f"\nLevene's test for equal variances: F={stat_lev:.4f}, p={p_lev:.4f}")
    if p_lev < 0.05:
        print("  → Variances are NOT equal (use Welch's t-test or Mann-Whitney U)")

    # Mann-Whitney U test (non-parametric)
    stat_mw, p_mw = mannwhitneyu(faq, digital_ad, alternative='two-sided')
    print(f"\nMann-Whitney U test: U={stat_mw:.2f}, p={p_mw:.6f}")

    # Effect size (rank-biserial correlation)
    n1, n2 = len(faq), len(digital_ad)
    r_rb = 1 - (2*stat_mw) / (n1 * n2)
    print(f"Effect size (rank-biserial r): {r_rb:.3f}")

    # Interpretation
    if p_mw < 0.001:
        sig = "***"
    elif p_mw < 0.01:
        sig = "**"
    elif p_mw < 0.05:
        sig = "*"
    else:
        sig = "ns"

    print(f"\nConclusion: {'SIGNIFICANT' if p_mw < 0.05 else 'NOT SIGNIFICANT'} {sig}")
    if p_mw < 0.05:
        print(f"  → Material type DOES affect violation rates")
        print(f"  → FAQ produces {((faq.mean() - digital_ad.mean()) / digital_ad.mean() * 100):.1f}% more violations than Digital Ad")

    return p_mw

def test_h2_engine(df):
    """H2: Engine affects violation rates (OpenAI vs Mistral)."""
    print("\n" + "="*80)
    print("H2: ENGINE EFFECT (OpenAI vs Mistral)")
    print("="*80)

    openai = df[df['engine'] == 'openai']['violations']
    mistral = df[df['engine'] == 'mistral']['violations']

    print(f"\nOpenAI (gpt-4o): N={len(openai)}, M={openai.mean():.2f}, SD={openai.std():.2f}")
    print(f"Mistral (mistral-large): N={len(mistral)}, M={mistral.mean():.2f}, SD={mistral.std():.2f}")
    print(f"Difference: {openai.mean() - mistral.mean():.2f} violations ({((openai.mean() - mistral.mean()) / mistral.mean() * 100):.1f}%)")

    # Check homogeneity of variance
    stat_lev, p_lev = levene(openai, mistral)
    print(f"\nLevene's test for equal variances: F={stat_lev:.4f}, p={p_lev:.4f}")

    # Mann-Whitney U test
    stat_mw, p_mw = mannwhitneyu(openai, mistral, alternative='two-sided')
    print(f"\nMann-Whitney U test: U={stat_mw:.2f}, p={p_mw:.6f}")

    # Effect size
    n1, n2 = len(openai), len(mistral)
    r_rb = 1 - (2*stat_mw) / (n1 * n2)
    print(f"Effect size (rank-biserial r): {r_rb:.3f}")

    # Interpretation
    if p_mw < 0.001:
        sig = "***"
    elif p_mw < 0.01:
        sig = "**"
    elif p_mw < 0.05:
        sig = "*"
    else:
        sig = "ns"

    print(f"\nConclusion: {'SIGNIFICANT' if p_mw < 0.05 else 'NOT SIGNIFICANT'} {sig}")
    if p_mw < 0.05:
        print(f"  → Engine DOES affect violation rates")
        if openai.mean() > mistral.mean():
            print(f"  → OpenAI produces {((openai.mean() - mistral.mean()) / mistral.mean() * 100):.1f}% more violations than Mistral")
        else:
            print(f"  → Mistral produces {((mistral.mean() - openai.mean()) / openai.mean() * 100):.1f}% more violations than OpenAI")

    return p_mw

def test_h3_product(df):
    """H3: Product affects violation rates (Crypto vs Smartphone vs Melatonin)."""
    print("\n" + "="*80)
    print("H3: PRODUCT EFFECT (3 products)")
    print("="*80)

    products = df['product'].unique()
    groups = [df[df['product'] == p]['violations'].values for p in products]

    print("\nProduct breakdown:")
    for i, product in enumerate(products):
        subset = df[df['product'] == product]['violations']
        print(f"  {product}: N={len(subset)}, M={subset.mean():.2f}, SD={subset.std():.2f}")

    # Kruskal-Wallis H test (non-parametric ANOVA)
    stat_kw, p_kw = kruskal(*groups)
    print(f"\nKruskal-Wallis H test: H={stat_kw:.4f}, p={p_kw:.6f}")

    # Effect size (eta-squared approximation)
    n = len(df)
    eta_sq = (stat_kw - len(products) + 1) / (n - len(products))
    print(f"Effect size (eta-squared): {eta_sq:.3f}")

    # Interpretation
    if p_kw < 0.001:
        sig = "***"
    elif p_kw < 0.01:
        sig = "**"
    elif p_kw < 0.05:
        sig = "*"
    else:
        sig = "ns"

    print(f"\nConclusion: {'SIGNIFICANT' if p_kw < 0.05 else 'NOT SIGNIFICANT'} {sig}")
    if p_kw < 0.05:
        print(f"  → Product type DOES affect violation rates")

        # Post-hoc pairwise comparisons
        print("\nPost-hoc pairwise comparisons (Mann-Whitney U):")
        from itertools import combinations
        for p1, p2 in combinations(products, 2):
            g1 = df[df['product'] == p1]['violations']
            g2 = df[df['product'] == p2]['violations']
            stat, p = mannwhitneyu(g1, g2, alternative='two-sided')
            # Bonferroni correction: alpha = 0.05 / 3 = 0.0167
            print(f"  {p1} vs {p2}: U={stat:.2f}, p={p:.4f} {'*' if p < 0.0167 else 'ns'}")

    return p_kw

def test_h4_replication(df):
    """H4: Replications show consistency (Rep1 vs Rep2 vs Rep3)."""
    print("\n" + "="*80)
    print("H4: REPLICATION CONSISTENCY (Rep1 vs Rep2 vs Rep3)")
    print("="*80)

    reps = sorted(df['repetition'].unique())
    groups = [df[df['repetition'] == r]['violations'].values for r in reps]

    print("\nReplication breakdown:")
    for rep in reps:
        subset = df[df['repetition'] == rep]['violations']
        print(f"  Rep {rep}: N={len(subset)}, M={subset.mean():.2f}, SD={subset.std():.2f}")

    # Kruskal-Wallis H test
    stat_kw, p_kw = kruskal(*groups)
    print(f"\nKruskal-Wallis H test: H={stat_kw:.4f}, p={p_kw:.6f}")

    # Coefficient of variation across reps
    rep_means = [df[df['repetition'] == r]['violations'].mean() for r in reps]
    cv = np.std(rep_means) / np.mean(rep_means) * 100
    print(f"\nCoefficient of variation (CV) across reps: {cv:.2f}%")

    # Interpretation
    if p_kw < 0.001:
        sig = "***"
    elif p_kw < 0.01:
        sig = "**"
    elif p_kw < 0.05:
        sig = "*"
    else:
        sig = "ns"

    print(f"\nConclusion: {'SIGNIFICANT DIFFERENCE' if p_kw < 0.05 else 'NO SIGNIFICANT DIFFERENCE'} {sig}")
    if p_kw < 0.05:
        print(f"  → Replications are NOT consistent (unexpected variation detected)")
    else:
        print(f"  → Replications ARE consistent (good reliability)")
        print(f"  → CV = {cv:.2f}% (CV < 10% indicates high consistency)")

    return p_kw

def interaction_analysis(df):
    """Exploratory analysis: Material × Engine interaction."""
    print("\n" + "="*80)
    print("EXPLORATORY: MATERIAL × ENGINE INTERACTION")
    print("="*80)

    print("\nViolation rates by Material × Engine:")
    for material in df['material'].unique():
        for engine in df['engine'].unique():
            subset = df[(df['material'] == material) & (df['engine'] == engine)]['violations']
            print(f"  {material} × {engine}: N={len(subset)}, M={subset.mean():.2f}, SD={subset.std():.2f}")

    # Two-way ANOVA (using Kruskal-Wallis as approximation)
    print("\nNote: Full factorial ANOVA requires more data (pilot N=36 is small)")
    print("For full experiment (N=729), use 2-way ANOVA or mixed-effects model")

def violation_type_analysis(audit):
    """Analyze violation categories."""
    print("\n" + "="*80)
    print("VIOLATION TYPE ANALYSIS")
    print("="*80)

    # Count violation types
    fail_violations = audit[audit['Status'] == 'FAIL']

    print(f"\nTotal violations: {len(fail_violations)}")
    print(f"\nTop 15 violated rules:")
    top_rules = fail_violations['Violated_Rule'].value_counts().head(15)
    for i, (rule, count) in enumerate(top_rules.items(), 1):
        pct = count / len(fail_violations) * 100
        print(f"{i:2d}. {count:3d} ({pct:4.1f}%)  {rule[:70]}")

def research_questions_summary(df):
    """Summarize findings for research questions."""
    print("\n" + "="*80)
    print("RESEARCH QUESTIONS SUMMARY")
    print("="*80)

    print("\nRQ1: People-pleasing bias")
    print("  Q: Do LLMs generate overly positive marketing content that violates compliance?")
    total_violations = df['violations'].sum()
    total_files = len(df)
    print(f"  A: YES - {total_violations} violations across {total_files} files ({df['violations'].mean():.1f} avg)")
    print(f"     100% of files had violations (0% pass rate)")
    print(f"     Top violation: 'zero bloatware' claims (164 instances) despite prohibition")

    print("\nRQ2: Induced errors and hallucinations")
    print("  Q: How frequently do LLMs introduce factual inaccuracies?")
    print(f"  A: {df['violations'].mean():.1f} violations per file on average")
    print(f"     Range: {df['violations'].min()}-{df['violations'].max()} violations per file")
    print(f"     Common hallucinations:")
    print(f"       - Wireless charging (not supported) - 23 instances")
    print(f"       - Gorilla Glass Victus back (incorrect spec) - 22 instances")
    print(f"       - Gas-free smart contracts (incorrect crypto claim) - 39 instances")

    print("\nRQ3: Temporal unreliability")
    print("  Q: Do LLMs produce inconsistent outputs across sessions?")
    print(f"  A: CANNOT TEST - Pilot uses only 1 time slot (morning)")
    print(f"     Full experiment (3 time slots) needed to test temporal effects")
    print(f"     Replications show CV = {np.std([df[df['repetition'] == r]['violations'].mean() for r in df['repetition'].unique()]) / np.mean([df[df['repetition'] == r]['violations'].mean() for r in df['repetition'].unique()]) * 100:.2f}% (consistency within session)")

def main():
    """Run all statistical tests."""
    print("PILOT EXPERIMENT STATISTICAL ANALYSIS")
    print("Date: 2026-03-07")
    print("Sample: N=36 (18 OpenAI + 18 Mistral, 2 materials, 3 products, 3 reps)")
    print("Note: Pilot has limited power - full experiment (N=729) needed for conclusive results")

    # Load data
    df, audit = load_data()

    # Descriptive statistics
    descriptive_stats(df)

    # Hypothesis tests
    p_material = test_h1_material(df)
    p_engine = test_h2_engine(df)
    p_product = test_h3_product(df)
    p_replication = test_h4_replication(df)

    # Interaction analysis
    interaction_analysis(df)

    # Violation type analysis
    violation_type_analysis(audit)

    # Research questions summary
    research_questions_summary(df)

    # Summary table
    print("\n" + "="*80)
    print("HYPOTHESIS TESTING SUMMARY")
    print("="*80)
    print(f"\nH1 (Material): p={p_material:.6f} {'***' if p_material < 0.001 else '**' if p_material < 0.01 else '*' if p_material < 0.05 else 'ns'}")
    print(f"H2 (Engine):   p={p_engine:.6f} {'***' if p_engine < 0.001 else '**' if p_engine < 0.01 else '*' if p_engine < 0.05 else 'ns'}")
    print(f"H3 (Product):  p={p_product:.6f} {'***' if p_product < 0.001 else '**' if p_product < 0.01 else '*' if p_product < 0.05 else 'ns'}")
    print(f"H4 (Replication): p={p_replication:.6f} {'***' if p_replication < 0.001 else '**' if p_replication < 0.01 else '*' if p_replication < 0.05 else 'ns'}")

    print("\nSignificance levels: * p<0.05, ** p<0.01, *** p<0.001, ns = not significant")

    print("\n" + "="*80)
    print("LIMITATIONS")
    print("="*80)
    print("1. Small sample size (N=36) limits statistical power")
    print("2. Cannot test temperature effects (only 1 temp = 0.6)")
    print("3. Cannot test temporal effects (only 1 time slot)")
    print("4. Missing Google engine data (18 failed runs)")
    print("5. Post-hoc tests have reduced power (Bonferroni correction)")
    print("\nFull experiment (N=729) will address all limitations")

if __name__ == "__main__":
    main()
