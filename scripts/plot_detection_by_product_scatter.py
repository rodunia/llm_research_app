#!/usr/bin/env python3
"""
Create 3 separate scatter plots (one per product) showing:
X-axis: Real Error (number induced per file: 1, 2, 3...10)
Y-axis: Detected Error (number detected)

Based on current Mar 7 ground truth validation results:
- Glass Box (GPT-4o): 28/30 errors (93.3%)
- GPT-4o Freeform: 28/30 errors (93.3%)
"""

import matplotlib.pyplot as plt
import numpy as np

# Current results (Mar 7) - ERROR-LEVEL detection
# From ground truth validation

# Smartphone: Both methods 10/10 (perfect)
SMARTPHONE_GLASS_BOX = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]  # All 10 detected
SMARTPHONE_GPT4O = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]      # All 10 detected

# Melatonin: Both methods 10/10 (perfect)
MELATONIN_GLASS_BOX = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]   # All 10 detected
MELATONIN_GPT4O = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]       # All 10 detected

# CoreCoin: Both methods 8/10 (miss #2 and #9)
CORECOIN_GLASS_BOX = [1, 0, 1, 1, 1, 1, 1, 1, 0, 1]    # Miss 2, 9
CORECOIN_GPT4O = [1, 0, 1, 1, 1, 1, 1, 1, 0, 1]        # Miss 2, 9

# Create figure with 3 subplots
fig, axes = plt.subplots(1, 3, figsize=(18, 5))
fig.suptitle('Error Detection by Product (Mar 7, 2026)\nGlass Box vs GPT-4o Freeform',
             fontsize=16, fontweight='bold', y=1.02)

products = [
    ('Smartphone', SMARTPHONE_GLASS_BOX, SMARTPHONE_GPT4O, '#2E86AB'),
    ('Melatonin', MELATONIN_GLASS_BOX, MELATONIN_GPT4O, '#A23B72'),
    ('CoreCoin', CORECOIN_GLASS_BOX, CORECOIN_GPT4O, '#F18F01')
]

for idx, (product_name, glass_box_detected, gpt4o_detected, color) in enumerate(products):
    ax = axes[idx]

    # Real errors (1 to 10)
    real_errors = np.arange(1, 11)

    # Detected errors (accumulate: if file i detected, add i to cumulative)
    glass_box_cumulative = []
    gpt4o_cumulative = []

    for i, (gb, gpt) in enumerate(zip(glass_box_detected, gpt4o_detected), 1):
        glass_box_cumulative.append(i if gb else 0)
        gpt4o_cumulative.append(i if gpt else 0)

    # Plot perfect detection line
    perfect_line = np.arange(0, 11)
    ax.plot(perfect_line, perfect_line, 'k--', linewidth=1.5, alpha=0.3, label='Perfect')

    # Plot Glass Box
    ax.scatter(real_errors, glass_box_cumulative,
              s=120, alpha=0.8, color=color, marker='o',
              edgecolors='black', linewidth=1.5, label='Glass Box', zorder=3)

    # Plot GPT-4o
    ax.scatter(real_errors, gpt4o_cumulative,
              s=120, alpha=0.8, color='#E63946', marker='s',
              edgecolors='black', linewidth=1.5, label='GPT-4o Freeform', zorder=2)

    # Styling
    ax.set_xlabel('Real Error (File Number)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Detected Error', fontsize=12, fontweight='bold')
    ax.set_title(f'{product_name}', fontsize=14, fontweight='bold')

    ax.set_xlim(0, 11)
    ax.set_ylim(0, 11)
    ax.set_xticks(range(0, 12, 2))
    ax.set_yticks(range(0, 12, 2))
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    ax.set_axisbelow(True)
    ax.legend(loc='upper left', fontsize=10, framealpha=0.9)

    # Add detection summary
    glass_total = sum(glass_box_detected)
    gpt4o_total = sum(gpt4o_detected)

    summary = f'Glass Box: {glass_total}/10\nGPT-4o: {gpt4o_total}/10'
    ax.text(0.98, 0.15, summary, transform=ax.transAxes,
           fontsize=10, verticalalignment='bottom', horizontalalignment='right',
           bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
           family='monospace')

plt.tight_layout()

# Save
output_path = 'results/errors_analysis/detection_by_product_scatter.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f'✓ Saved: {output_path}')

print('\n=== Detection Summary ===')
for product_name, glass_box_detected, gpt4o_detected, _ in products:
    glass_total = sum(glass_box_detected)
    gpt4o_total = sum(gpt4o_detected)
    print(f'{product_name}: Glass Box {glass_total}/10, GPT-4o {gpt4o_total}/10')

print(f'\nOverall:')
total_glass = sum(sum(d[1]) for d in products)
total_gpt4o = sum(sum(d[2]) for d in products)
print(f'  Glass Box: {total_glass}/30 ({total_glass/30*100:.1f}%)')
print(f'  GPT-4o: {total_gpt4o}/30 ({total_gpt4o/30*100:.1f}%)')
