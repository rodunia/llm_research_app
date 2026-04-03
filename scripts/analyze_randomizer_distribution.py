"""
Analyze Randomizer Distribution

Validates randomness of dry-run results with plots and statistical tests.

Usage:
    python scripts/analyze_randomizer_distribution.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats
from typing import Dict, Tuple

# Import matplotlib
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns

# ==================== CONFIGURATION ====================

INPUT_CSV = Path("results/randomizer_dry_run_1620.csv")
OUTPUT_DIR = Path("results/randomizer_plots")
REPORT_PATH = Path("results/randomizer_validation_report.md")

# Expected values (will be auto-detected from data)
TOTAL_DAYS = 7
TOTAL_TIME_SLOTS = 3
TOTAL_DAY_TIME_CELLS = TOTAL_DAYS * TOTAL_TIME_SLOTS  # 21

# These will be set after loading data
TOTAL_RUNS = None
EXPECTED_PER_DAY = None
EXPECTED_PER_TIME = None
EXPECTED_PER_CELL = None

# Tolerance thresholds
DAY_TOLERANCE_PCT = 0.05  # ±5%
TIME_TOLERANCE_PCT = 0.05  # ±5%
CELL_TOLERANCE_PCT = 0.10  # ±10%

CHI_SQUARE_ALPHA = 0.05  # Significance level


# ==================== HELPER FUNCTIONS ====================

def load_data() -> pd.DataFrame:
    """Load dry-run results and set expected values."""
    global TOTAL_RUNS, EXPECTED_PER_DAY, EXPECTED_PER_TIME, EXPECTED_PER_CELL

    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input CSV not found: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV)

    # Auto-detect total runs
    TOTAL_RUNS = len(df)
    EXPECTED_PER_DAY = TOTAL_RUNS / TOTAL_DAYS
    EXPECTED_PER_TIME = TOTAL_RUNS / TOTAL_TIME_SLOTS
    EXPECTED_PER_CELL = TOTAL_RUNS / TOTAL_DAY_TIME_CELLS

    print(f"✅ Loaded {TOTAL_RUNS} runs from {INPUT_CSV}")
    print(f"   Expected per day: {EXPECTED_PER_DAY:.1f}")
    print(f"   Expected per time slot: {EXPECTED_PER_TIME:.1f}")
    print(f"   Expected per day×time cell: {EXPECTED_PER_CELL:.1f}")

    return df


def chi_square_uniformity_test(observed: np.ndarray, expected: float, name: str) -> Tuple[float, float, bool]:
    """
    Perform chi-square test for uniform distribution.

    Returns:
        (chi2_stat, p_value, passes)
    """
    expected_arr = np.full(len(observed), expected)
    chi2_stat, p_value = stats.chisquare(f_obs=observed, f_exp=expected_arr)

    passes = p_value > CHI_SQUARE_ALPHA

    print(f"\n{name}:")
    print(f"  χ² statistic: {chi2_stat:.2f}")
    print(f"  p-value: {p_value:.4f}")
    print(f"  Result: {'✅ PASS' if passes else '❌ FAIL'} (α={CHI_SQUARE_ALPHA})")

    return chi2_stat, p_value, passes


def chi_square_independence_test(df: pd.DataFrame, var1: str, var2: str) -> Tuple[float, float, bool]:
    """
    Test independence between two categorical variables.

    Returns:
        (chi2_stat, p_value, passes)
    """
    contingency_table = pd.crosstab(df[var1], df[var2])
    chi2_stat, p_value, dof, expected = stats.chi2_contingency(contingency_table)

    passes = p_value > CHI_SQUARE_ALPHA

    print(f"\nIndependence Test: {var1} × {var2}:")
    print(f"  χ² statistic: {chi2_stat:.2f}")
    print(f"  p-value: {p_value:.4f}")
    print(f"  Result: {'✅ PASS (independent)' if passes else '❌ FAIL (dependent)'}")

    return chi2_stat, p_value, passes


# ==================== ANALYSIS FUNCTIONS ====================

def analyze_day_distribution(df: pd.DataFrame) -> Dict:
    """Analyze distribution by day of week."""
    print("\n" + "=" * 70)
    print("ANALYSIS: Distribution by Day of Week")
    print("=" * 70)

    day_counts = df['scheduled_day_of_week'].value_counts().sort_index()

    # Expected count per day
    expected = EXPECTED_PER_DAY

    # Check each day within tolerance
    all_pass = True
    results = []

    for day, count in day_counts.items():
        deviation = ((count - expected) / expected) * 100
        within_tolerance = abs(deviation) <= (DAY_TOLERANCE_PCT * 100)

        results.append({
            'day': day,
            'count': count,
            'expected': expected,
            'deviation_pct': deviation,
            'within_tolerance': within_tolerance
        })

        status = "✅" if within_tolerance else "❌"
        print(f"  {day:10s}: {count:4d} runs (expected: {expected:.1f}, deviation: {deviation:+.1f}%) {status}")

        if not within_tolerance:
            all_pass = False

    # Chi-square test
    chi2, p_value, chi_pass = chi_square_uniformity_test(
        day_counts.values,
        expected,
        "Chi-square test (days)"
    )

    return {
        'results': results,
        'all_within_tolerance': all_pass,
        'chi2_stat': chi2,
        'p_value': p_value,
        'chi2_pass': chi_pass
    }


def analyze_timeslot_distribution(df: pd.DataFrame) -> Dict:
    """Analyze distribution by time slot."""
    print("\n" + "=" * 70)
    print("ANALYSIS: Distribution by Time Slot")
    print("=" * 70)

    time_counts = df['scheduled_time_slot'].value_counts().sort_index()

    # Expected count per time slot
    expected = EXPECTED_PER_TIME

    # Check each slot within tolerance
    all_pass = True
    results = []

    for slot, count in time_counts.items():
        deviation = ((count - expected) / expected) * 100
        within_tolerance = abs(deviation) <= (TIME_TOLERANCE_PCT * 100)

        results.append({
            'slot': slot,
            'count': count,
            'expected': expected,
            'deviation_pct': deviation,
            'within_tolerance': within_tolerance
        })

        status = "✅" if within_tolerance else "❌"
        print(f"  {slot:10s}: {count:4d} runs (expected: {expected:.1f}, deviation: {deviation:+.1f}%) {status}")

        if not within_tolerance:
            all_pass = False

    # Chi-square test
    chi2, p_value, chi_pass = chi_square_uniformity_test(
        time_counts.values,
        expected,
        "Chi-square test (time slots)"
    )

    return {
        'results': results,
        'all_within_tolerance': all_pass,
        'chi2_stat': chi2,
        'p_value': p_value,
        'chi2_pass': chi_pass
    }


def analyze_day_time_distribution(df: pd.DataFrame) -> Dict:
    """Analyze distribution by day × time combination."""
    print("\n" + "=" * 70)
    print("ANALYSIS: Distribution by Day × Time Slot")
    print("=" * 70)

    # Cross-tabulation
    crosstab = pd.crosstab(df['scheduled_day_of_week'], df['scheduled_time_slot'])

    # Expected count per cell
    expected = EXPECTED_PER_CELL

    # Flatten and check tolerance
    all_pass = True
    results = []

    for day in crosstab.index:
        for slot in crosstab.columns:
            count = crosstab.loc[day, slot]
            deviation = ((count - expected) / expected) * 100
            within_tolerance = abs(deviation) <= (CELL_TOLERANCE_PCT * 100)

            results.append({
                'day': day,
                'slot': slot,
                'count': count,
                'expected': expected,
                'deviation_pct': deviation,
                'within_tolerance': within_tolerance
            })

            if not within_tolerance:
                all_pass = False

    # Print summary
    print(f"  Total cells: {len(results)}")
    print(f"  Expected per cell: {expected:.1f}")
    print(f"  Cells within tolerance (±{CELL_TOLERANCE_PCT*100:.0f}%): {sum(r['within_tolerance'] for r in results)}/{len(results)}")

    # Chi-square test on flattened cells
    observed = crosstab.values.flatten()
    chi2, p_value, chi_pass = chi_square_uniformity_test(
        observed,
        expected,
        "Chi-square test (day×time cells)"
    )

    return {
        'crosstab': crosstab,
        'results': results,
        'all_within_tolerance': all_pass,
        'chi2_stat': chi2,
        'p_value': p_value,
        'chi2_pass': chi_pass
    }


def analyze_experimental_factors(df: pd.DataFrame) -> Dict:
    """Analyze distribution by experimental factors (should be exact)."""
    print("\n" + "=" * 70)
    print("ANALYSIS: Distribution by Experimental Factors")
    print("=" * 70)

    factors = {
        'product_id': 3,
        'engine': 3,
        'material_type': 3,
        'temperature': 3
    }

    results = {}

    for factor, expected_count_groups in factors.items():
        counts = df[factor].value_counts().sort_index()
        expected_per_group = TOTAL_RUNS / expected_count_groups

        print(f"\n{factor}:")
        all_exact = True
        for value, count in counts.items():
            exact = (count == expected_per_group)
            status = "✅" if exact else "❌"
            value_str = str(value)
            print(f"  {value_str:30s}: {count:4d} runs (expected: {expected_per_group:.0f}) {status}")

            if not exact:
                all_exact = False

        results[factor] = {
            'counts': counts.to_dict(),
            'all_exact': all_exact
        }

    return results


def test_independence(df: pd.DataFrame) -> Dict:
    """Test independence between experimental factors and timing."""
    print("\n" + "=" * 70)
    print("ANALYSIS: Independence Tests")
    print("=" * 70)

    tests = [
        ('product_id', 'scheduled_day_of_week'),
        ('product_id', 'scheduled_time_slot'),
        ('engine', 'scheduled_day_of_week'),
        ('engine', 'scheduled_time_slot'),
        ('material_type', 'scheduled_day_of_week'),
        ('material_type', 'scheduled_time_slot'),
    ]

    results = {}

    for var1, var2 in tests:
        chi2, p_value, passes = chi_square_independence_test(df, var1, var2)
        results[f"{var1}_x_{var2}"] = {
            'chi2_stat': chi2,
            'p_value': p_value,
            'passes': passes
        }

    return results


# ==================== PLOTTING FUNCTIONS ====================

def plot_day_distribution(df: pd.DataFrame, output_dir: Path):
    """Plot distribution by day of week."""
    day_counts = df['scheduled_day_of_week'].value_counts().reindex([
        'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'
    ])

    plt.figure(figsize=(10, 6))
    ax = day_counts.plot(kind='bar', color='steelblue', edgecolor='black')
    plt.axhline(y=EXPECTED_PER_DAY, color='red', linestyle='--', linewidth=2, label=f'Expected ({EXPECTED_PER_DAY:.1f})')
    plt.xlabel('Day of Week', fontsize=12)
    plt.ylabel('Number of Runs', fontsize=12)
    plt.title('Distribution of Runs by Day of Week', fontsize=14, fontweight='bold')
    plt.xticks(rotation=45, ha='right')
    plt.legend()
    plt.tight_layout()

    output_path = output_dir / 'distribution_by_day.png'
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"  📊 Saved: {output_path}")


def plot_timeslot_distribution(df: pd.DataFrame, output_dir: Path):
    """Plot distribution by time slot."""
    time_counts = df['scheduled_time_slot'].value_counts().reindex(['morning', 'afternoon', 'evening'])

    plt.figure(figsize=(8, 6))
    ax = time_counts.plot(kind='bar', color='coral', edgecolor='black')
    plt.axhline(y=EXPECTED_PER_TIME, color='red', linestyle='--', linewidth=2, label=f'Expected ({EXPECTED_PER_TIME:.1f})')
    plt.xlabel('Time Slot', fontsize=12)
    plt.ylabel('Number of Runs', fontsize=12)
    plt.title('Distribution of Runs by Time Slot', fontsize=14, fontweight='bold')
    plt.xticks(rotation=0)
    plt.legend()
    plt.tight_layout()

    output_path = output_dir / 'distribution_by_timeslot.png'
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"  📊 Saved: {output_path}")


def plot_heatmap_day_time(df: pd.DataFrame, output_dir: Path):
    """Plot heatmap of day × time distribution."""
    crosstab = pd.crosstab(df['scheduled_day_of_week'], df['scheduled_time_slot'])

    # Reorder rows (days)
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    crosstab = crosstab.reindex(day_order)

    # Reorder columns (times)
    time_order = ['morning', 'afternoon', 'evening']
    crosstab = crosstab[time_order]

    plt.figure(figsize=(8, 7))
    sns.heatmap(crosstab, annot=True, fmt='d', cmap='YlGnBu', cbar_kws={'label': 'Number of Runs'}, linewidths=0.5)
    plt.xlabel('Time Slot', fontsize=12)
    plt.ylabel('Day of Week', fontsize=12)
    plt.title(f'Heatmap: Day × Time Slot\n(Expected per cell: {EXPECTED_PER_CELL:.1f})', fontsize=14, fontweight='bold')
    plt.tight_layout()

    output_path = output_dir / 'heatmap_day_x_time.png'
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"  📊 Saved: {output_path}")


def plot_experimental_factors(df: pd.DataFrame, output_dir: Path):
    """Plot distributions for experimental factors."""
    factors = ['product_id', 'engine', 'material_type', 'temperature']

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    for idx, factor in enumerate(factors):
        counts = df[factor].value_counts().sort_index()
        expected = TOTAL_RUNS / len(counts)

        ax = axes[idx]
        counts.plot(kind='bar', ax=ax, color='lightgreen', edgecolor='black')
        ax.axhline(y=expected, color='red', linestyle='--', linewidth=2, label=f'Expected ({expected:.0f})')
        ax.set_xlabel(factor.replace('_', ' ').title(), fontsize=11)
        ax.set_ylabel('Number of Runs', fontsize=11)
        ax.set_title(f'Distribution by {factor.replace("_", " ").title()}', fontsize=12, fontweight='bold')
        ax.legend()
        ax.tick_params(axis='x', rotation=45)

    plt.tight_layout()

    output_path = output_dir / 'distribution_by_experimental_factors.png'
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"  📊 Saved: {output_path}")


def plot_scatter_order_vs_time(df: pd.DataFrame, output_dir: Path):
    """Scatter plot: run order vs timestamp (should show no pattern)."""
    df_sorted = df.sort_values('run_order')

    # Convert timestamp to numeric (hours since start)
    df_sorted['timestamp_dt'] = pd.to_datetime(df_sorted['scheduled_timestamp'])
    start_time = df_sorted['timestamp_dt'].min()
    df_sorted['hours_since_start'] = (df_sorted['timestamp_dt'] - start_time).dt.total_seconds() / 3600

    plt.figure(figsize=(12, 6))
    plt.scatter(df_sorted['run_order'], df_sorted['hours_since_start'], alpha=0.5, s=10, color='purple')
    plt.xlabel('Run Order', fontsize=12)
    plt.ylabel('Hours Since Start', fontsize=12)
    plt.title('Scatter Plot: Run Order vs Scheduled Time\n(Should show no pattern if truly random)', fontsize=14, fontweight='bold')
    plt.grid(alpha=0.3)
    plt.tight_layout()

    output_path = output_dir / 'scatter_order_vs_time.png'
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"  📊 Saved: {output_path}")


# ==================== REPORT GENERATION ====================

def generate_markdown_report(
    day_analysis: Dict,
    time_analysis: Dict,
    daytime_analysis: Dict,
    factor_analysis: Dict,
    independence_analysis: Dict,
    output_path: Path
):
    """Generate markdown validation report."""

    report = []

    report.append("# Randomizer Dry-Run Validation Report\n")
    report.append(f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append("---\n")

    # Summary
    report.append("## Summary\n")
    report.append(f"- **Total runs:** {TOTAL_RUNS}\n")
    report.append(f"- **Days:** {TOTAL_DAYS} (full week)\n")
    report.append(f"- **Time slots:** {TOTAL_TIME_SLOTS} per day\n")
    report.append(f"- **Total time cells:** {TOTAL_DAY_TIME_CELLS}\n")
    report.append("\n")

    # Day distribution
    report.append("## Distribution by Day of Week\n")
    report.append(f"**Expected per day:** {EXPECTED_PER_DAY:.1f} runs\n\n")
    report.append("| Day       | Runs | Expected | Deviation | Status |\n")
    report.append("|-----------|------|----------|-----------|--------|\n")
    for r in day_analysis['results']:
        status = "✅ PASS" if r['within_tolerance'] else "❌ FAIL"
        report.append(f"| {r['day']:10s} | {r['count']:4d} | {r['expected']:.1f} | {r['deviation_pct']:+.1f}% | {status} |\n")
    report.append("\n")
    report.append(f"**Chi-square test:** χ²={day_analysis['chi2_stat']:.2f}, p={day_analysis['p_value']:.4f} ")
    report.append(f"({'✅ PASS' if day_analysis['chi2_pass'] else '❌ FAIL'})\n\n")

    # Time slot distribution
    report.append("## Distribution by Time Slot\n")
    report.append(f"**Expected per slot:** {EXPECTED_PER_TIME:.1f} runs\n\n")
    report.append("| Time Slot  | Runs | Expected | Deviation | Status |\n")
    report.append("|------------|------|----------|-----------|--------|\n")
    for r in time_analysis['results']:
        status = "✅ PASS" if r['within_tolerance'] else "❌ FAIL"
        report.append(f"| {r['slot']:10s} | {r['count']:4d} | {r['expected']:.1f} | {r['deviation_pct']:+.1f}% | {status} |\n")
    report.append("\n")
    report.append(f"**Chi-square test:** χ²={time_analysis['chi2_stat']:.2f}, p={time_analysis['p_value']:.4f} ")
    report.append(f"({'✅ PASS' if time_analysis['chi2_pass'] else '❌ FAIL'})\n\n")

    # Day × Time distribution
    report.append("## Distribution by Day × Time Slot\n")
    report.append(f"**Expected per cell:** {EXPECTED_PER_CELL:.1f} runs\n\n")
    report.append(f"**Cells within tolerance (±{CELL_TOLERANCE_PCT*100:.0f}%):** ")
    report.append(f"{sum(r['within_tolerance'] for r in daytime_analysis['results'])}/{len(daytime_analysis['results'])}\n\n")
    report.append(f"**Chi-square test:** χ²={daytime_analysis['chi2_stat']:.2f}, p={daytime_analysis['p_value']:.4f} ")
    report.append(f"({'✅ PASS' if daytime_analysis['chi2_pass'] else '❌ FAIL'})\n\n")

    # Experimental factors
    report.append("## Experimental Factors (Should be Exact)\n")
    for factor, data in factor_analysis.items():
        status = "✅ PASS" if data['all_exact'] else "❌ FAIL"
        report.append(f"**{factor}:** {status}\n")
    report.append("\n")

    # Independence tests
    report.append("## Independence Tests\n")
    report.append("Testing if experimental factors are independent of timing:\n\n")
    report.append("| Test | χ² | p-value | Result |\n")
    report.append("|------|-----|---------|--------|\n")
    for test_name, data in independence_analysis.items():
        status = "✅ PASS" if data['passes'] else "❌ FAIL"
        report.append(f"| {test_name.replace('_x_', ' × ')} | {data['chi2_stat']:.2f} | {data['p_value']:.4f} | {status} |\n")
    report.append("\n")

    # Overall verdict
    report.append("---\n")
    report.append("## Overall Verdict\n")

    all_pass = (
        day_analysis['chi2_pass'] and
        time_analysis['chi2_pass'] and
        daytime_analysis['chi2_pass'] and
        all(data['all_exact'] for data in factor_analysis.values()) and
        all(data['passes'] for data in independence_analysis.values())
    )

    if all_pass:
        report.append("### ✅ ALL TESTS PASSED\n")
        report.append("Randomizer is working correctly. Ready to proceed with experiment.\n")
    else:
        report.append("### ❌ SOME TESTS FAILED\n")
        report.append("Review failures above and fix randomizer before proceeding.\n")

    # Write report
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(report)

    print(f"\n📝 Validation report saved to: {output_path}")


# ==================== MAIN ====================

def main():
    """Run full analysis pipeline."""
    print("=" * 70)
    print("RANDOMIZER DISTRIBUTION ANALYSIS")
    print("=" * 70)

    # Load data
    df = load_data()

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Run analyses
    day_analysis = analyze_day_distribution(df)
    time_analysis = analyze_timeslot_distribution(df)
    daytime_analysis = analyze_day_time_distribution(df)
    factor_analysis = analyze_experimental_factors(df)
    independence_analysis = test_independence(df)

    # Generate plots
    print("\n" + "=" * 70)
    print("GENERATING PLOTS")
    print("=" * 70)
    plot_day_distribution(df, OUTPUT_DIR)
    plot_timeslot_distribution(df, OUTPUT_DIR)
    plot_heatmap_day_time(df, OUTPUT_DIR)
    plot_experimental_factors(df, OUTPUT_DIR)
    plot_scatter_order_vs_time(df, OUTPUT_DIR)

    # Generate report
    print("\n" + "=" * 70)
    print("GENERATING VALIDATION REPORT")
    print("=" * 70)
    generate_markdown_report(
        day_analysis,
        time_analysis,
        daytime_analysis,
        factor_analysis,
        independence_analysis,
        REPORT_PATH
    )

    print("\n" + "=" * 70)
    print("✅ Analysis complete!")
    print("=" * 70)
    print(f"\nOutputs:")
    print(f"  - Plots: {OUTPUT_DIR}/")
    print(f"  - Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
