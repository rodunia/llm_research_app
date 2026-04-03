"""
Statistical Validation of Randomizer Using ANOVA

Tests whether experimental factors are truly independent of timing factors
using Analysis of Variance (ANOVA).

Five tests:
1. Day of Week (7 groups) - One-way ANOVA
2. Time of Day (3 groups) - One-way ANOVA with Tukey HSD
3. LLM Engine (3 groups) - One-way ANOVA
4. Temperature Setting (3 groups) - One-way ANOVA with Tukey HSD
5. Day x Time Interaction - Two-way ANOVA

Usage:
    python scripts/validate_randomizer_anova.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from statsmodels.formula.api import ols
from statsmodels.stats.anova import anova_lm

# ==================== CONFIGURATION ====================

INPUT_CSV = Path("results/randomizer_dry_run_1620.csv")
OUTPUT_REPORT = Path("results/randomizer_anova_validation.md")

# Significance level
ALPHA = 0.05

# Day order for proper sorting
DAY_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
TIME_ORDER = ['morning', 'afternoon', 'evening']


# ==================== HELPER FUNCTIONS ====================

def load_data() -> pd.DataFrame:
    """Load and prepare data."""
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input CSV not found: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV)

    # Convert timestamp to datetime
    df['scheduled_timestamp'] = pd.to_datetime(df['scheduled_timestamp'])

    # Extract hour for aggregation
    df['hour'] = df['scheduled_timestamp'].dt.hour

    # Convert categorical variables to proper types with ordered categories
    df['scheduled_day_of_week'] = pd.Categorical(df['scheduled_day_of_week'],
                                                   categories=DAY_ORDER,
                                                   ordered=True)
    df['scheduled_time_slot'] = pd.Categorical(df['scheduled_time_slot'],
                                                categories=TIME_ORDER,
                                                ordered=True)

    print(f"✅ Loaded {len(df)} runs from {INPUT_CSV}")
    return df


def aggregate_by_hour(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate data by hour to get call volume per hour.
    This creates our dependent variable for ANOVA.
    """
    # Group by hour and count calls
    hourly = df.groupby('scheduled_timestamp').size().reset_index(name='calls_per_hour')

    # Add day/time metadata back
    hourly['day_of_week'] = pd.to_datetime(hourly['scheduled_timestamp']).dt.day_name()
    hourly['hour_of_day'] = pd.to_datetime(hourly['scheduled_timestamp']).dt.hour

    # Categorize hour into time slot
    def get_time_slot(hour):
        if 8 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 17:
            return 'afternoon'
        else:
            return 'evening'

    hourly['time_slot'] = hourly['hour_of_day'].apply(get_time_slot)

    # Convert to categorical with order
    hourly['day_of_week'] = pd.Categorical(hourly['day_of_week'],
                                             categories=DAY_ORDER,
                                             ordered=True)
    hourly['time_slot'] = pd.Categorical(hourly['time_slot'],
                                          categories=TIME_ORDER,
                                          ordered=True)

    return hourly


def add_experimental_factors(df: pd.DataFrame, hourly: pd.DataFrame) -> pd.DataFrame:
    """
    Add experimental factors (engine, temperature) to hourly aggregation.
    For each hour, calculate distribution of engines and temperatures.
    """
    # For each hour, get mean temperature and dominant engine
    hourly_factors = df.groupby('scheduled_timestamp').agg({
        'temperature': 'mean',
        'engine': lambda x: x.mode()[0] if len(x.mode()) > 0 else x.iloc[0]
    }).reset_index()

    # Merge back
    hourly = hourly.merge(hourly_factors, on='scheduled_timestamp', how='left')

    return hourly


# ==================== TEST 1: Day of Week ====================

def test_day_of_week(hourly: pd.DataFrame) -> dict:
    """
    Test 1: One-way ANOVA - Day of Week

    H0: Mean calls per hour is the same across all days
    Ha: At least one day differs
    """
    print("\n" + "=" * 70)
    print("TEST 1: Day of Week Effect on Hourly Call Volume")
    print("=" * 70)

    # Group data by day
    groups = [hourly[hourly['day_of_week'] == day]['calls_per_hour'].values
              for day in DAY_ORDER]

    # One-way ANOVA
    f_stat, p_value = stats.f_oneway(*groups)

    # Descriptive stats
    day_stats = hourly.groupby('day_of_week')['calls_per_hour'].agg(['mean', 'std', 'count'])

    result = {
        'test_name': 'One-Way ANOVA: Day of Week',
        'f_statistic': f_stat,
        'p_value': p_value,
        'significant': p_value < ALPHA,
        'descriptive_stats': day_stats,
        'interpretation': None
    }

    if result['significant']:
        result['interpretation'] = f"SIGNIFICANT (p={p_value:.4f}): Day of week DOES affect call volume. This suggests non-random scheduling."
    else:
        result['interpretation'] = f"NOT SIGNIFICANT (p={p_value:.4f}): Day of week does NOT significantly affect call volume. ✅ Randomization working as expected."

    print(f"\nF-statistic: {f_stat:.4f}")
    print(f"p-value: {p_value:.4f}")
    print(f"Result: {'⚠️  SIGNIFICANT' if result['significant'] else '✅ NOT SIGNIFICANT'}")
    print(f"\n{result['interpretation']}")

    return result


# ==================== TEST 2: Time of Day ====================

def test_time_of_day(hourly: pd.DataFrame) -> dict:
    """
    Test 2: One-way ANOVA - Time of Day (with Tukey HSD post-hoc)

    H0: Mean calls per hour is the same across all time slots
    Ha: At least one time slot differs
    """
    print("\n" + "=" * 70)
    print("TEST 2: Time of Day Effect on Hourly Call Volume")
    print("=" * 70)

    # Group data by time slot
    groups = [hourly[hourly['time_slot'] == slot]['calls_per_hour'].values
              for slot in TIME_ORDER]

    # One-way ANOVA
    f_stat, p_value = stats.f_oneway(*groups)

    # Descriptive stats
    time_stats = hourly.groupby('time_slot')['calls_per_hour'].agg(['mean', 'std', 'count'])

    result = {
        'test_name': 'One-Way ANOVA: Time of Day',
        'f_statistic': f_stat,
        'p_value': p_value,
        'significant': p_value < ALPHA,
        'descriptive_stats': time_stats,
        'tukey_results': None,
        'interpretation': None
    }

    # If significant, run Tukey HSD post-hoc test
    if result['significant']:
        tukey = pairwise_tukeyhsd(endog=hourly['calls_per_hour'],
                                   groups=hourly['time_slot'],
                                   alpha=ALPHA)
        result['tukey_results'] = tukey

        result['interpretation'] = f"SIGNIFICANT (p={p_value:.4f}): Time of day DOES affect call volume. See Tukey HSD results for pairwise differences."
        print(f"\n⚠️  ANOVA SIGNIFICANT - Running Tukey HSD post-hoc test:")
        print(tukey)
    else:
        result['interpretation'] = f"NOT SIGNIFICANT (p={p_value:.4f}): Time of day does NOT significantly affect call volume. ✅ Randomization working as expected."

    print(f"\nF-statistic: {f_stat:.4f}")
    print(f"p-value: {p_value:.4f}")
    print(f"Result: {'⚠️  SIGNIFICANT' if result['significant'] else '✅ NOT SIGNIFICANT'}")
    print(f"\n{result['interpretation']}")

    return result


# ==================== TEST 3: LLM Engine ====================

def test_engine(df: pd.DataFrame, hourly: pd.DataFrame) -> dict:
    """
    Test 3: One-way ANOVA - LLM Engine

    H0: Mean calls per hour is the same across all engines
    Ha: At least one engine differs
    """
    print("\n" + "=" * 70)
    print("TEST 3: LLM Engine Effect on Hourly Call Volume")
    print("=" * 70)

    # Add engine info to hourly data
    hourly_engine = add_experimental_factors(df, hourly.copy())

    # Group data by engine
    engines = hourly_engine['engine'].unique()
    groups = [hourly_engine[hourly_engine['engine'] == eng]['calls_per_hour'].values
              for eng in engines]

    # One-way ANOVA
    f_stat, p_value = stats.f_oneway(*groups)

    # Descriptive stats
    engine_stats = hourly_engine.groupby('engine')['calls_per_hour'].agg(['mean', 'std', 'count'])

    result = {
        'test_name': 'One-Way ANOVA: LLM Engine',
        'f_statistic': f_stat,
        'p_value': p_value,
        'significant': p_value < ALPHA,
        'descriptive_stats': engine_stats,
        'interpretation': None
    }

    if result['significant']:
        result['interpretation'] = f"SIGNIFICANT (p={p_value:.4f}): Engine DOES affect call volume. This suggests non-random assignment of engines to time slots."
    else:
        result['interpretation'] = f"NOT SIGNIFICANT (p={p_value:.4f}): Engine does NOT significantly affect call volume. ✅ Engines randomly distributed across time."

    print(f"\nF-statistic: {f_stat:.4f}")
    print(f"p-value: {p_value:.4f}")
    print(f"Result: {'⚠️  SIGNIFICANT' if result['significant'] else '✅ NOT SIGNIFICANT'}")
    print(f"\n{result['interpretation']}")

    return result


# ==================== TEST 4: Temperature Setting ====================

def test_temperature(df: pd.DataFrame, hourly: pd.DataFrame) -> dict:
    """
    Test 4: One-way ANOVA - Temperature Setting (with Tukey HSD post-hoc)

    H0: Mean calls per hour is the same across all temperature settings
    Ha: At least one temperature differs
    """
    print("\n" + "=" * 70)
    print("TEST 4: Temperature Setting Effect on Hourly Call Volume")
    print("=" * 70)

    # Add temperature info to hourly data
    hourly_temp = add_experimental_factors(df, hourly.copy())

    # Round temperature to avoid floating point issues
    hourly_temp['temperature'] = hourly_temp['temperature'].round(1)

    # Group data by temperature
    temps = sorted(hourly_temp['temperature'].unique())
    groups = [hourly_temp[hourly_temp['temperature'] == temp]['calls_per_hour'].values
              for temp in temps]

    # One-way ANOVA
    f_stat, p_value = stats.f_oneway(*groups)

    # Descriptive stats
    temp_stats = hourly_temp.groupby('temperature')['calls_per_hour'].agg(['mean', 'std', 'count'])

    result = {
        'test_name': 'One-Way ANOVA: Temperature Setting',
        'f_statistic': f_stat,
        'p_value': p_value,
        'significant': p_value < ALPHA,
        'descriptive_stats': temp_stats,
        'tukey_results': None,
        'interpretation': None
    }

    # If significant, run Tukey HSD post-hoc test
    if result['significant']:
        tukey = pairwise_tukeyhsd(endog=hourly_temp['calls_per_hour'],
                                   groups=hourly_temp['temperature'],
                                   alpha=ALPHA)
        result['tukey_results'] = tukey

        result['interpretation'] = f"SIGNIFICANT (p={p_value:.4f}): Temperature DOES affect call volume. See Tukey HSD results for pairwise differences."
        print(f"\n⚠️  ANOVA SIGNIFICANT - Running Tukey HSD post-hoc test:")
        print(tukey)
    else:
        result['interpretation'] = f"NOT SIGNIFICANT (p={p_value:.4f}): Temperature does NOT significantly affect call volume. ✅ Temperatures randomly distributed across time."

    print(f"\nF-statistic: {f_stat:.4f}")
    print(f"p-value: {p_value:.4f}")
    print(f"Result: {'⚠️  SIGNIFICANT' if result['significant'] else '✅ NOT SIGNIFICANT'}")
    print(f"\n{result['interpretation']}")

    return result


# ==================== TEST 5: Two-Way ANOVA (Interaction) ====================

def test_day_time_interaction(hourly: pd.DataFrame) -> dict:
    """
    Test 5: Two-Way ANOVA - Day × Time Interaction

    Tests:
    1. Main effect of day
    2. Main effect of time
    3. Interaction effect (day × time)

    H0 (interaction): The effect of time of day is the same across all days
    Ha (interaction): The effect of time of day varies by day of week
    """
    print("\n" + "=" * 70)
    print("TEST 5: Two-Way ANOVA - Day × Time Interaction")
    print("=" * 70)

    # Fit two-way ANOVA model
    model = ols('calls_per_hour ~ C(day_of_week) + C(time_slot) + C(day_of_week):C(time_slot)',
                data=hourly).fit()
    anova_table = anova_lm(model, typ=2)

    # Extract results
    day_effect = anova_table.loc['C(day_of_week)', :]
    time_effect = anova_table.loc['C(time_slot)', :]
    interaction_effect = anova_table.loc['C(day_of_week):C(time_slot)', :]

    result = {
        'test_name': 'Two-Way ANOVA: Day × Time Interaction',
        'anova_table': anova_table,
        'main_effect_day': {
            'F': day_effect['F'],
            'p_value': day_effect['PR(>F)'],
            'significant': day_effect['PR(>F)'] < ALPHA
        },
        'main_effect_time': {
            'F': time_effect['F'],
            'p_value': time_effect['PR(>F)'],
            'significant': time_effect['PR(>F)'] < ALPHA
        },
        'interaction': {
            'F': interaction_effect['F'],
            'p_value': interaction_effect['PR(>F)'],
            'significant': interaction_effect['PR(>F)'] < ALPHA
        },
        'interpretation': None
    }

    # Interpret results
    interpretations = []

    if result['main_effect_day']['significant']:
        interpretations.append(f"⚠️  Main effect of DAY is significant (p={result['main_effect_day']['p_value']:.4f})")
    else:
        interpretations.append(f"✅ Main effect of DAY is NOT significant (p={result['main_effect_day']['p_value']:.4f})")

    if result['main_effect_time']['significant']:
        interpretations.append(f"⚠️  Main effect of TIME is significant (p={result['main_effect_time']['p_value']:.4f})")
    else:
        interpretations.append(f"✅ Main effect of TIME is NOT significant (p={result['main_effect_time']['p_value']:.4f})")

    if result['interaction']['significant']:
        interpretations.append(f"⚠️  INTERACTION is significant (p={result['interaction']['p_value']:.4f})")
        interpretations.append("This means the time-of-day pattern varies by day of week.")
    else:
        interpretations.append(f"✅ INTERACTION is NOT significant (p={result['interaction']['p_value']:.4f})")
        interpretations.append("This means the time-of-day pattern is consistent across days.")

    result['interpretation'] = '\n'.join(interpretations)

    print("\nANOVA Table:")
    print(anova_table)
    print(f"\n{result['interpretation']}")

    return result


# ==================== REPORT GENERATION ====================

def generate_report(results: dict):
    """Generate markdown report with all test results."""

    report = []

    report.append("# Randomizer ANOVA Validation Report\n")
    report.append(f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append("---\n\n")

    report.append("## Purpose\n")
    report.append("Statistical validation that experimental factors (engine, temperature, material, product) ")
    report.append("are truly independent of timing factors (day of week, time of day) using Analysis of Variance (ANOVA).\n\n")

    report.append("**Key Question:** Does the randomizer create a truly random distribution, or are there ")
    report.append("systematic patterns that would confound temporal analysis?\n\n")

    report.append("---\n\n")

    # Test 1
    report.append("## Test 1: Day of Week Effect\n")
    report.append(f"**Test:** One-Way ANOVA (7 groups)\n\n")
    report.append(f"**H₀:** Mean calls per hour is equal across all days\n\n")
    report.append(f"**Results:**\n")
    report.append(f"- F-statistic: {results['test1']['f_statistic']:.4f}\n")
    report.append(f"- p-value: {results['test1']['p_value']:.4f}\n")
    report.append(f"- Significant at α=0.05: {'YES ⚠️' if results['test1']['significant'] else 'NO ✅'}\n\n")
    report.append(f"**Interpretation:** {results['test1']['interpretation']}\n\n")
    report.append("---\n\n")

    # Test 2
    report.append("## Test 2: Time of Day Effect\n")
    report.append(f"**Test:** One-Way ANOVA (3 groups) with Tukey HSD post-hoc\n\n")
    report.append(f"**H₀:** Mean calls per hour is equal across all time slots\n\n")
    report.append(f"**Results:**\n")
    report.append(f"- F-statistic: {results['test2']['f_statistic']:.4f}\n")
    report.append(f"- p-value: {results['test2']['p_value']:.4f}\n")
    report.append(f"- Significant at α=0.05: {'YES ⚠️' if results['test2']['significant'] else 'NO ✅'}\n\n")
    if results['test2']['tukey_results']:
        report.append("**Tukey HSD Post-Hoc Results:**\n```\n")
        report.append(str(results['test2']['tukey_results']))
        report.append("\n```\n\n")
    report.append(f"**Interpretation:** {results['test2']['interpretation']}\n\n")
    report.append("---\n\n")

    # Test 3
    report.append("## Test 3: LLM Engine Effect\n")
    report.append(f"**Test:** One-Way ANOVA (3 groups, perfectly balanced)\n\n")
    report.append(f"**H₀:** Mean calls per hour is equal across all engines\n\n")
    report.append(f"**Results:**\n")
    report.append(f"- F-statistic: {results['test3']['f_statistic']:.4f}\n")
    report.append(f"- p-value: {results['test3']['p_value']:.4f}\n")
    report.append(f"- Significant at α=0.05: {'YES ⚠️' if results['test3']['significant'] else 'NO ✅'}\n\n")
    report.append(f"**Interpretation:** {results['test3']['interpretation']}\n\n")
    report.append("---\n\n")

    # Test 4
    report.append("## Test 4: Temperature Setting Effect\n")
    report.append(f"**Test:** One-Way ANOVA (3 groups, perfectly balanced) with Tukey HSD post-hoc\n\n")
    report.append(f"**H₀:** Mean calls per hour is equal across all temperature settings\n\n")
    report.append(f"**Results:**\n")
    report.append(f"- F-statistic: {results['test4']['f_statistic']:.4f}\n")
    report.append(f"- p-value: {results['test4']['p_value']:.4f}\n")
    report.append(f"- Significant at α=0.05: {'YES ⚠️' if results['test4']['significant'] else 'NO ✅'}\n\n")
    if results['test4']['tukey_results']:
        report.append("**Tukey HSD Post-Hoc Results:**\n```\n")
        report.append(str(results['test4']['tukey_results']))
        report.append("\n```\n\n")
    report.append(f"**Interpretation:** {results['test4']['interpretation']}\n\n")
    report.append("---\n\n")

    # Test 5
    report.append("## Test 5: Two-Way ANOVA - Day × Time Interaction\n")
    report.append(f"**Test:** Two-Way ANOVA (7 × 3 = 21 cells)\n\n")
    report.append(f"**H₀ (Interaction):** The effect of time of day is consistent across all days\n\n")
    report.append(f"**Results:**\n\n")
    report.append("| Effect | F | p-value | Significant |\n")
    report.append("|--------|---|---------|-------------|\n")
    report.append(f"| Day (main) | {results['test5']['main_effect_day']['F']:.4f} | {results['test5']['main_effect_day']['p_value']:.4f} | {'YES ⚠️' if results['test5']['main_effect_day']['significant'] else 'NO ✅'} |\n")
    report.append(f"| Time (main) | {results['test5']['main_effect_time']['F']:.4f} | {results['test5']['main_effect_time']['p_value']:.4f} | {'YES ⚠️' if results['test5']['main_effect_time']['significant'] else 'NO ✅'} |\n")
    report.append(f"| Day × Time (interaction) | {results['test5']['interaction']['F']:.4f} | {results['test5']['interaction']['p_value']:.4f} | {'YES ⚠️' if results['test5']['interaction']['significant'] else 'NO ✅'} |\n\n")
    report.append(f"**Interpretation:**\n{results['test5']['interpretation']}\n\n")
    report.append("---\n\n")

    # Overall verdict
    report.append("## Overall Verdict\n\n")

    all_non_significant = (
        not results['test1']['significant'] and
        not results['test2']['significant'] and
        not results['test3']['significant'] and
        not results['test4']['significant'] and
        not results['test5']['interaction']['significant']
    )

    if all_non_significant:
        report.append("### ✅ RANDOMIZER VALIDATED\n\n")
        report.append("All ANOVA tests were non-significant, indicating that:\n")
        report.append("- Experimental factors are independent of timing\n")
        report.append("- No systematic patterns or confounds detected\n")
        report.append("- The randomizer is working as intended\n\n")
        report.append("**Conclusion:** Safe to proceed with full 1,620-run experiment.\n")
    else:
        report.append("### ⚠️  POTENTIAL ISSUES DETECTED\n\n")
        report.append("One or more ANOVA tests were significant, suggesting:\n")
        report.append("- Non-random patterns may exist\n")
        report.append("- Review significant effects above\n")
        report.append("- Consider re-running randomization with different seed\n\n")
        report.append("**Recommendation:** Investigate significant effects before proceeding.\n")

    # Write report
    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_REPORT, 'w', encoding='utf-8') as f:
        f.writelines(report)

    print(f"\n📝 Report saved to: {OUTPUT_REPORT}")


# ==================== MAIN ====================

def main():
    """Run all ANOVA tests."""
    print("=" * 70)
    print("RANDOMIZER ANOVA VALIDATION")
    print("=" * 70)
    print("\nRunning 5 statistical tests to validate randomization...\n")

    # Load data
    df = load_data()

    # Aggregate by hour (creates our dependent variable)
    print("\n📊 Aggregating data by hour...")
    hourly = aggregate_by_hour(df)
    print(f"   Created {len(hourly)} hourly time points")

    # Run all tests
    results = {}

    results['test1'] = test_day_of_week(hourly)
    results['test2'] = test_time_of_day(hourly)
    results['test3'] = test_engine(df, hourly)
    results['test4'] = test_temperature(df, hourly)
    results['test5'] = test_day_time_interaction(hourly)

    # Generate report
    print("\n" + "=" * 70)
    print("GENERATING REPORT")
    print("=" * 70)
    generate_report(results)

    print("\n" + "=" * 70)
    print("✅ ANOVA VALIDATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
