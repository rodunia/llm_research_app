#!/usr/bin/env python3
"""
Plot error detection comparison by product: Glass Box vs GPT-4o Freeform
Shows expected errors vs detected errors for each product category
"""

import matplotlib.pyplot as plt
import numpy as np

# Ground truth: 10 errors per product
EXPECTED_ERRORS = {
    'Smartphone': 10,
    'Melatonin': 10,
    'CoreCoin': 10
}

# Detected errors (from ground truth validation)
GLASS_BOX_DETECTED = {
    'Smartphone': 10,
    'Melatonin': 10,
    'CoreCoin': 8
}

GPT4O_DETECTED = {
    'Smartphone': 10,
    'Melatonin': 10,
    'CoreCoin': 8
}

# Create figure with 3 subplots (one per product)
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.suptitle('Error Detection Comparison: Glass Box vs GPT-4o Freeform\n(Ground Truth Validation)',
             fontsize=16, fontweight='bold', y=1.02)

products = ['Smartphone', 'Melatonin', 'CoreCoin']
colors = ['#2E86AB', '#A23B72', '#F18F01']

for idx, (ax, product, color) in enumerate(zip(axes, products, colors)):
    expected = EXPECTED_ERRORS[product]
    glass_box = GLASS_BOX_DETECTED[product]
    gpt4o = GPT4O_DETECTED[product]

    # Bar positions
    x = np.arange(3)
    width = 0.6

    # Create bars (create them individually to set different alphas)
    bar1 = ax.bar(x[0], expected, width, color=color, alpha=0.3, edgecolor='black', linewidth=1.5)
    bar2 = ax.bar(x[1], glass_box, width, color=color, alpha=0.8, edgecolor='black', linewidth=1.5)
    bar3 = ax.bar(x[2], gpt4o, width, color=color, alpha=0.8, edgecolor='black', linewidth=1.5)

    bars = [bar1[0], bar2[0], bar3[0]]

    # Add pattern for detection methods
    bars[1].set_hatch('//')
    bars[2].set_hatch('\\\\')

    # Labels and values on bars
    for i, (bar, val) in enumerate(zip(bars, [expected, glass_box, gpt4o])):
        height = bar.get_height()
        label = f'{val}/{expected}' if i > 0 else str(val)
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.3,
                label, ha='center', va='bottom', fontsize=12, fontweight='bold')

    # Add detection percentage for methods
    glass_pct = (glass_box / expected * 100)
    gpt4o_pct = (gpt4o / expected * 100)

    ax.text(1, -1.5, f'{glass_pct:.0f}%', ha='center', fontsize=11,
            fontweight='bold', color='green' if glass_pct == 100 else 'orange')
    ax.text(2, -1.5, f'{gpt4o_pct:.0f}%', ha='center', fontsize=11,
            fontweight='bold', color='green' if gpt4o_pct == 100 else 'orange')

    # Styling
    ax.set_ylabel('Number of Errors', fontsize=11, fontweight='bold')
    ax.set_title(f'{product}', fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(['Expected\nErrors', 'Glass Box\nDetected', 'GPT-4o\nDetected'],
                       fontsize=10)
    ax.set_ylim(0, 12)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    # Add perfect/partial detection indicator
    if glass_box == expected and gpt4o == expected:
        ax.text(0.5, 11, '✓ Both Perfect', ha='center', fontsize=10,
                color='green', fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.3))
    elif glass_box == expected or gpt4o == expected:
        ax.text(0.5, 11, '⚠ Partial Detection', ha='center', fontsize=10,
                color='orange', fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.3))

plt.tight_layout()

# Save figure
output_path = 'results/errors_analysis/error_detection_by_product.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f'✓ Saved: {output_path}')

# Also create a summary bar chart
fig2, ax2 = plt.subplots(figsize=(10, 6))

products_list = ['Smartphone', 'Melatonin', 'CoreCoin']
x = np.arange(len(products_list))
width = 0.25

# Expected, Glass Box, GPT-4o
expected_vals = [EXPECTED_ERRORS[p] for p in products_list]
glass_vals = [GLASS_BOX_DETECTED[p] for p in products_list]
gpt4o_vals = [GPT4O_DETECTED[p] for p in products_list]

bars1 = ax2.bar(x - width, expected_vals, width, label='Expected Errors',
                color='lightgray', edgecolor='black', linewidth=1.5, alpha=0.7)
bars2 = ax2.bar(x, glass_vals, width, label='Glass Box Detected',
                color='#2E86AB', edgecolor='black', linewidth=1.5, hatch='//')
bars3 = ax2.bar(x + width, gpt4o_vals, width, label='GPT-4o Detected',
                color='#A23B72', edgecolor='black', linewidth=1.5, hatch='\\\\')

# Add value labels
for bars in [bars1, bars2, bars3]:
    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 0.2,
                f'{int(height)}', ha='center', va='bottom', fontsize=11, fontweight='bold')

ax2.set_xlabel('Product Category', fontsize=12, fontweight='bold')
ax2.set_ylabel('Number of Errors', fontsize=12, fontweight='bold')
ax2.set_title('Error Detection Comparison: Expected vs Detected\nGlass Box vs GPT-4o Freeform',
             fontsize=14, fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels(products_list)
ax2.legend(loc='upper right', fontsize=11)
ax2.set_ylim(0, 12)
ax2.grid(axis='y', alpha=0.3, linestyle='--')
ax2.set_axisbelow(True)

# Add summary text
total_expected = sum(expected_vals)
total_glass = sum(glass_vals)
total_gpt4o = sum(gpt4o_vals)

summary_text = f'Overall Detection:\nGlass Box: {total_glass}/{total_expected} ({total_glass/total_expected*100:.1f}%)\nGPT-4o: {total_gpt4o}/{total_expected} ({total_gpt4o/total_expected*100:.1f}%)'
ax2.text(0.02, 0.98, summary_text, transform=ax2.transAxes,
        fontsize=10, verticalalignment='top',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.tight_layout()

output_path2 = 'results/errors_analysis/error_detection_summary.png'
plt.savefig(output_path2, dpi=300, bbox_inches='tight')
print(f'✓ Saved: {output_path2}')

print('\n=== Summary ===')
print(f'Total Expected: {total_expected}')
print(f'Glass Box Detected: {total_glass}/{total_expected} ({total_glass/total_expected*100:.1f}%)')
print(f'GPT-4o Detected: {total_gpt4o}/{total_expected} ({total_gpt4o/total_expected*100:.1f}%)')
print('\nBy Product:')
for product in products_list:
    print(f'  {product}: Expected={EXPECTED_ERRORS[product]}, Glass Box={GLASS_BOX_DETECTED[product]}, GPT-4o={GPT4O_DETECTED[product]}')
