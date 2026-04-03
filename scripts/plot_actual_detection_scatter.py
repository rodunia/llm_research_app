#!/usr/bin/env python3
"""
Plot actual error detection counts (like image 11)
X = Real errors in file (1-10)
Y = Detected errors
Separate plots for each product
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load the data
df = pd.read_csv('results/errors_analysis/actual_detection_counts.csv')

# Create 3-panel figure
fig, axes = plt.subplots(1, 3, figsize=(18, 5))
fig.suptitle('Actual Error Detection Per File (Mar 7, 2026)\nGlass Box vs GPT-4o Freeform',
             fontsize=16, fontweight='bold', y=1.02)

products = [
    ('smartphone', 'Smartphone', '#2E86AB'),
    ('melatonin', 'Melatonin', '#A23B72'),
    ('corecoin', 'CoreCoin', '#F18F01')
]

for idx, (product_id, product_name, color) in enumerate(products):
    ax = axes[idx]

    # Filter data for this product
    product_data = df[df['product'] == product_id]

    # Extract data
    real_errors = product_data['errors_in_file'].values
    glass_box_detected = product_data['glass_box_detected'].values
    gpt4o_detected = product_data['gpt4o_detected'].values

    # Plot perfect detection line
    perfect_line = np.arange(0, 11)
    ax.plot(perfect_line, perfect_line, 'k--', linewidth=1.5, alpha=0.3, label='Perfect')

    # Plot Glass Box
    ax.scatter(real_errors, glass_box_detected,
              s=120, alpha=0.8, color=color, marker='o',
              edgecolors='black', linewidth=1.5, label='Glass Box', zorder=3)

    # Plot GPT-4o
    ax.scatter(real_errors, gpt4o_detected,
              s=120, alpha=0.8, color='#E63946', marker='s',
              edgecolors='black', linewidth=1.5, label='GPT-4o', zorder=2)

    # Styling
    ax.set_xlabel('Real Error (Errors in File)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Detected Error', fontsize=12, fontweight='bold')
    ax.set_title(f'{product_name}', fontsize=14, fontweight='bold')

    ax.set_xlim(0, 11)
    ax.set_ylim(0, 11)
    ax.set_xticks(range(0, 12, 2))
    ax.set_yticks(range(0, 12, 2))
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    ax.set_axisbelow(True)
    ax.legend(loc='upper left', fontsize=10, framealpha=0.9)

    # Calculate totals
    glass_total = glass_box_detected.sum()
    gpt4o_total = gpt4o_detected.sum()
    total_errors = real_errors.sum()

    summary = f'Glass Box: {glass_total}/{total_errors}\nGPT-4o: {gpt4o_total}/{total_errors}'
    ax.text(0.98, 0.15, summary, transform=ax.transAxes,
           fontsize=10, verticalalignment='bottom', horizontalalignment='right',
           bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
           family='monospace')

plt.tight_layout()

# Save
output_path = 'results/errors_analysis/actual_detection_scatter_by_product.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f'✓ Saved: {output_path}')

# Print summary
print('\n=== Detection Summary ===')
for product_id, product_name, _ in products:
    product_data = df[df['product'] == product_id]
    glass_total = product_data['glass_box_detected'].sum()
    gpt4o_total = product_data['gpt4o_detected'].sum()
    total = product_data['errors_in_file'].sum()
    print(f'{product_name}: Glass Box {glass_total}/{total} ({glass_total/total*100:.1f}%), GPT-4o {gpt4o_total}/{total} ({gpt4o_total/total*100:.1f}%)')

print(f'\nOverall:')
total_errors = df['errors_in_file'].sum()
total_glass = df['glass_box_detected'].sum()
total_gpt4o = df['gpt4o_detected'].sum()
print(f'  Glass Box: {total_glass}/{total_errors} ({total_glass/total_errors*100:.1f}%)')
print(f'  GPT-4o: {total_gpt4o}/{total_errors} ({total_gpt4o/total_errors*100:.1f}%)')
