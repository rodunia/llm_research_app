"""
Deep dive analysis: Check if time slot bias is correlated with specific factors.

Investigates:
1. Weekend vs Weekday time slot distribution
2. Product × time slot patterns
3. Engine × time slot patterns
4. Material × time slot patterns
5. Temperature × time slot patterns
"""

import pandas as pd
from pathlib import Path
from collections import Counter
import numpy as np

# Load the CSV
csv_path = Path("results/randomizer_stratified_1620.csv")
df = pd.read_csv(csv_path)

print("=" * 80)
print("DEEP DIVE: TIME SLOT BIAS ANALYSIS")
print("=" * 80)

# Overall distribution
print("\n### Overall Time Slot Distribution")
time_counts = df['scheduled_time_slot'].value_counts()
total = len(df)
print(f"Total runs: {total}")
for slot in ['morning', 'afternoon', 'evening']:
    count = time_counts.get(slot, 0)
    pct = count / total * 100
    deviation = (count - 540) / 540 * 100
    print(f"  {slot:10s}: {count:4d} ({pct:5.2f}%, deviation: {deviation:+.2f}%)")

# Weekend vs Weekday
print("\n### Weekend vs Weekday Breakdown")

weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
weekends = ['Saturday', 'Sunday']

df_weekday = df[df['scheduled_day_of_week'].isin(weekdays)]
df_weekend = df[df['scheduled_day_of_week'].isin(weekends)]

print(f"\nWeekday time slots (n={len(df_weekday)}):")
weekday_counts = df_weekday['scheduled_time_slot'].value_counts()
for slot in ['morning', 'afternoon', 'evening']:
    count = weekday_counts.get(slot, 0)
    pct = count / len(df_weekday) * 100
    print(f"  {slot:10s}: {count:4d} ({pct:5.2f}%)")

print(f"\nWeekend time slots (n={len(df_weekend)}):")
weekend_counts = df_weekend['scheduled_time_slot'].value_counts()
for slot in ['morning', 'afternoon', 'evening']:
    count = weekend_counts.get(slot, 0)
    pct = count / len(df_weekend) * 100
    print(f"  {slot:10s}: {count:4d} ({pct:5.2f}%)")

# Chi-square test for weekend vs weekday
from scipy.stats import chi2_contingency

contingency = pd.crosstab(df['is_weekend'], df['scheduled_time_slot'])
chi2, p_value, dof, expected = chi2_contingency(contingency)

print(f"\n**Chi-square test (Weekend vs Weekday time slots):**")
print(f"  χ² = {chi2:.3f}, p = {p_value:.4f}")
if p_value < 0.05:
    print(f"  ❌ SIGNIFICANT DIFFERENCE between weekend and weekday time slots")
else:
    print(f"  ✅ No significant difference (p > 0.05)")

# Per-day breakdown
print("\n### Time Slots by Day of Week")
print(f"{'Day':<12} {'Morning':<10} {'Afternoon':<12} {'Evening':<10} {'Total'}")
print("-" * 60)

for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
    day_df = df[df['scheduled_day_of_week'] == day]
    day_counts = day_df['scheduled_time_slot'].value_counts()

    morning = day_counts.get('morning', 0)
    afternoon = day_counts.get('afternoon', 0)
    evening = day_counts.get('evening', 0)
    total = len(day_df)

    print(f"{day:<12} {morning:<10} {afternoon:<12} {evening:<10} {total}")

# Product analysis
print("\n### Time Slots by Product")
print(f"{'Product':<30} {'Morning':<10} {'Afternoon':<12} {'Evening'}")
print("-" * 70)

for product in df['product_id'].unique():
    prod_df = df[df['product_id'] == product]
    prod_counts = prod_df['scheduled_time_slot'].value_counts()

    morning = prod_counts.get('morning', 0)
    afternoon = prod_counts.get('afternoon', 0)
    evening = prod_counts.get('evening', 0)

    print(f"{product:<30} {morning:<10} {afternoon:<12} {evening}")

# Engine analysis
print("\n### Time Slots by Engine")
print(f"{'Engine':<12} {'Morning':<10} {'Afternoon':<12} {'Evening'}")
print("-" * 50)

for engine in df['engine'].unique():
    eng_df = df[df['engine'] == engine]
    eng_counts = eng_df['scheduled_time_slot'].value_counts()

    morning = eng_counts.get('morning', 0)
    afternoon = eng_counts.get('afternoon', 0)
    evening = eng_counts.get('evening', 0)

    print(f"{engine:<12} {morning:<10} {afternoon:<12} {evening}")

# Temperature analysis
print("\n### Time Slots by Temperature")
print(f"{'Temp':<8} {'Morning':<10} {'Afternoon':<12} {'Evening'}")
print("-" * 45)

for temp in sorted(df['temperature'].unique()):
    temp_df = df[df['temperature'] == temp]
    temp_counts = temp_df['scheduled_time_slot'].value_counts()

    morning = temp_counts.get('morning', 0)
    afternoon = temp_counts.get('afternoon', 0)
    evening = temp_counts.get('evening', 0)

    print(f"{temp:<8.1f} {morning:<10} {afternoon:<12} {evening}")

# Material analysis
print("\n### Time Slots by Material Type")
print(f"{'Material':<20} {'Morning':<10} {'Afternoon':<12} {'Evening'}")
print("-" * 55)

for material in df['material_type'].unique():
    mat_df = df[df['material_type'] == material]
    mat_counts = mat_df['scheduled_time_slot'].value_counts()

    morning = mat_counts.get('morning', 0)
    afternoon = mat_counts.get('afternoon', 0)
    evening = mat_counts.get('evening', 0)

    print(f"{material:<20} {morning:<10} {afternoon:<12} {evening}")

# Check for systematic pattern: Does hour of day correlate with anything?
print("\n### Hour Distribution by Time Slot")
print(f"{'Time Slot':<12} {'Mean Hour':<12} {'Hour Range'}")
print("-" * 40)

for slot in ['morning', 'afternoon', 'evening']:
    slot_df = df[df['scheduled_time_slot'] == slot]
    mean_hour = slot_df['hour'].mean()
    min_hour = slot_df['hour'].min()
    max_hour = slot_df['hour'].max()

    print(f"{slot:<12} {mean_hour:>6.2f}       [{min_hour:2d} - {max_hour:2d}]")

# Final summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

# Calculate expected vs observed for each slot
expected = 540
observed = {
    'morning': time_counts.get('morning', 0),
    'afternoon': time_counts.get('afternoon', 0),
    'evening': time_counts.get('evening', 0)
}

deviations = {slot: (count - expected) / expected * 100 for slot, count in observed.items()}

print(f"\n### Deviations from Expected (540 per slot)")
for slot, dev in sorted(deviations.items(), key=lambda x: abs(x[1]), reverse=True):
    print(f"  {slot:10s}: {dev:+.2f}% ({observed[slot]:4d} runs)")

# Check if any factor shows systematic correlation
print(f"\n### Potential Systematic Biases")

# Weekend check
weekend_morning_pct = weekend_counts.get('morning', 0) / len(df_weekend) * 100
weekday_morning_pct = weekday_counts.get('morning', 0) / len(df_weekday) * 100
morning_diff = abs(weekend_morning_pct - weekday_morning_pct)

if p_value < 0.05:
    print(f"  ❌ Weekend vs Weekday: p={p_value:.4f} (SIGNIFICANT)")
else:
    print(f"  ✅ Weekend vs Weekday: p={p_value:.4f} (not significant)")

# Product check
product_imbalances = []
for product in df['product_id'].unique():
    prod_df = df[df['product_id'] == product]
    prod_counts = prod_df['scheduled_time_slot'].value_counts()

    for slot in ['morning', 'afternoon', 'evening']:
        count = prod_counts.get(slot, 0)
        expected_prod = len(prod_df) / 3
        deviation = abs(count - expected_prod) / expected_prod * 100
        product_imbalances.append(deviation)

max_product_imbalance = max(product_imbalances)
if max_product_imbalance > 15:
    print(f"  ⚠️  Product imbalance: max {max_product_imbalance:.2f}%")
else:
    print(f"  ✅ Product distribution: max imbalance {max_product_imbalance:.2f}%")

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)

if max(abs(d) for d in deviations.values()) < 7:
    print("\n✅ Time slot variance is within acceptable range (<7%)")
    print("✅ No evidence of systematic bias in randomization algorithm")

    if p_value >= 0.05:
        print("✅ Weekend/weekday distribution is statistically equivalent")

    print("\n**Verdict**: Random variance only, no algorithmic bias detected.")
else:
    print("\n⚠️  Time slot variance exceeds 7% - requires investigation")
    print("Check randomization algorithm for potential bugs")

print("\n" + "=" * 80)
