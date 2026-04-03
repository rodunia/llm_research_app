"""
Create 3 scatter plots comparing Glass Box vs GPT-4o freeform detection
One plot per product
"""
import pandas as pd
import matplotlib.pyplot as plt

# Read validation results
df = pd.read_csv('results/errors_analysis/ground_truth_validation_detailed.csv')

# Convert checkmarks to counts (1 for detected, 0 for missed)
df['glass_box_count'] = (df['glass_box_detected'] == '✓').astype(int)
df['gpt4o_count'] = (df['gpt4o_detected'] == '✓').astype(int)

# Create figure with 3 subplots (one per product)
fig, axes = plt.subplots(1, 3, figsize=(15, 5))

products = ['smartphone', 'melatonin', 'corecoin']
titles = ['Smartphone (Nova X5)', 'Melatonin Supplement', 'CoreCoin Cryptocurrency']

for idx, (product, title) in enumerate(zip(products, titles)):
    ax = axes[idx]
    df_prod = df[df['product'] == product]

    # Aggregate detections by file_num (cumulative ground truth errors)
    # File 1 has 1 error, file 2 has 2 errors, etc.
    # We count how many were detected per file

    # For each file, count total ground truth errors UP TO that file
    # and total detected errors UP TO that file
    file_nums = []
    glass_box_cumulative = []
    gpt4o_cumulative = []

    for file_num in range(1, 11):
        df_subset = df_prod[df_prod['file_num'] <= file_num]
        file_nums.append(file_num)
        glass_box_cumulative.append(df_subset['glass_box_count'].sum())
        gpt4o_cumulative.append(df_subset['gpt4o_count'].sum())

    # Plot
    ax.scatter(file_nums, glass_box_cumulative, color='#1f77b4', s=80, label='Glass Box', zorder=3)
    ax.scatter(file_nums, gpt4o_cumulative, color='#ff7f0e', s=80, label='GPT-4o freeform', zorder=3)

    # Add ideal diagonal line (y = x)
    ax.plot([0, 10], [0, 55], 'k--', alpha=0.3, linewidth=1, label='Perfect detection')

    # Formatting
    ax.set_xlabel('Real Error', fontsize=11)
    ax.set_ylabel('Determined Error', fontsize=11)
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 11)
    ax.set_ylim(0, max(max(glass_box_cumulative), max(gpt4o_cumulative)) + 2)
    ax.legend(loc='upper left', fontsize=9)

plt.tight_layout()
plt.savefig('results/errors_analysis/detection_comparison_cumulative.png', dpi=300, bbox_inches='tight')
print("✓ Saved: results/errors_analysis/detection_comparison_cumulative.png")
plt.close()

# Also create NON-cumulative version (as shown in reference image)
# X-axis: Expected errors per file (1, 2, 3, ..., 10)
# Y-axis: Actual count of that specific error detected (0 or 1)

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

for idx, (product, title) in enumerate(zip(products, titles)):
    ax = axes[idx]
    df_prod = df[df['product'] == product].sort_values('file_num')

    # X = file_num (which equals expected error count)
    # Y = detection count for that specific file
    x = df_prod['file_num'].values
    y_glass_box = df_prod['glass_box_count'].values
    y_gpt4o = df_prod['gpt4o_count'].values

    # Plot
    ax.scatter(x, y_glass_box, color='#1f77b4', s=80, label='Glass Box', zorder=3, alpha=0.7)
    ax.scatter(x, y_gpt4o, color='#ff7f0e', s=80, label='GPT-4o freeform', zorder=3, alpha=0.7)

    # Add reference line at y=1 (perfect detection)
    ax.axhline(y=1, color='green', linestyle='--', alpha=0.3, linewidth=1, label='Perfect (all detected)')
    ax.axhline(y=0, color='red', linestyle='--', alpha=0.3, linewidth=1, label='None detected')

    # Formatting
    ax.set_xlabel('Real Error (File Number)', fontsize=11)
    ax.set_ylabel('Detected (0=missed, 1=found)', fontsize=11)
    ax.set_title(title, fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, 11)
    ax.set_ylim(-0.2, 1.3)
    ax.set_yticks([0, 1])
    ax.legend(loc='upper left', fontsize=9)

plt.tight_layout()
plt.savefig('results/errors_analysis/detection_comparison_per_file.png', dpi=300, bbox_inches='tight')
print("✓ Saved: results/errors_analysis/detection_comparison_per_file.png")
plt.close()

print("\nSummary:")
print(f"Glass Box: {df['glass_box_count'].sum()}/30 ({df['glass_box_count'].sum()/30*100:.1f}%)")
print(f"GPT-4o:    {df['gpt4o_count'].sum()}/30 ({df['gpt4o_count'].sum()/30*100:.1f}%)")
