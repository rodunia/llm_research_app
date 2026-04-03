#!/usr/bin/env python3
"""
Simple error detection analysis: Which errors were caught vs missed?
Creates clear visualizations and tables for researchers.
"""

import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path

# Load summary data
with open('results/errors_analysis/glass_box/summary.json', 'r') as f:
    glass_box_data = json.load(f)

with open('results/errors_analysis/gpt4o_freeform/summary.json', 'r') as f:
    gpt4o_data = json.load(f)

# Ground truth: 30 errors (10 per product)
# Each file has cumulative errors: file 1 = error 1, file 2 = errors 1-2, ..., file 10 = errors 1-10

# Build detection matrix
products = {
    'smartphone': 'Smartphone',
    'melatonin': 'Melatonin',
    'corecoin': 'CoreCoin'
}

# For each product, track which error levels were detected
detection_data = []

for product_key, product_name in products.items():
    for error_level in range(1, 11):
        file_name = f'errors_{product_key}_{error_level}'

        # Find Glass Box result
        gb_result = next((r for r in glass_box_data if r['file'] == file_name), None)
        gb_detected = gb_result['errors_detected'] if gb_result else False

        # Find GPT-4o result
        gpt_result = next((r for r in gpt4o_data if r['file'] == file_name), None)
        gpt_detected = gpt_result['errors_detected'] if gpt_result else False

        detection_data.append({
            'Product': product_name,
            'Error_Level': error_level,
            'File': file_name,
            'Glass_Box': 'Caught' if gb_detected else 'Missed',
            'GPT4o': 'Caught' if gpt_detected else 'Missed',
            'Glass_Box_Binary': 1 if gb_detected else 0,
            'GPT4o_Binary': 1 if gpt_detected else 0
        })

df = pd.DataFrame(detection_data)

# Create output directory
output_dir = Path('results/errors_analysis/simple_visualizations')
output_dir.mkdir(parents=True, exist_ok=True)

# ============================================================
# TABLE 1: Simple Detection Table
# ============================================================
print("\n" + "="*80)
print("ERROR DETECTION TABLE")
print("="*80)

table_data = []
for product_key, product_name in products.items():
    for error_level in range(1, 11):
        row_data = df[(df['Product'] == product_name) & (df['Error_Level'] == error_level)].iloc[0]

        gb_status = "✓ CAUGHT" if row_data['Glass_Box'] == 'Caught' else "✗ MISSED"
        gpt_status = "✓ CAUGHT" if row_data['GPT4o'] == 'Caught' else "✗ MISSED"

        table_data.append({
            'Product': product_name,
            'Error': error_level,
            'Glass Box': gb_status,
            'GPT-4o': gpt_status
        })

table_df = pd.DataFrame(table_data)

# Save to CSV
table_df.to_csv(output_dir / 'error_detection_table.csv', index=False)
print("\n✓ Saved: error_detection_table.csv")
print(table_df.to_string(index=False))

# ============================================================
# GRAPH 1: Simple Caught vs Missed Bar Chart
# ============================================================
fig, ax = plt.subplots(figsize=(10, 6))

# Count caught vs missed
gb_caught = df['Glass_Box_Binary'].sum()
gb_missed = 30 - gb_caught
gpt_caught = df['GPT4o_Binary'].sum()
gpt_missed = 30 - gpt_caught

categories = ['Glass Box', 'GPT-4o']
caught = [gb_caught, gpt_caught]
missed = [gb_missed, gpt_missed]

x = np.arange(len(categories))
width = 0.6

# Stacked bar chart
bars1 = ax.bar(x, caught, width, label='Caught', color='#2ecc71')
bars2 = ax.bar(x, missed, width, bottom=caught, label='Missed', color='#e74c3c')

ax.set_ylabel('Number of Errors (out of 30)', fontsize=13, fontweight='bold')
ax.set_title('Error Detection: Caught vs Missed\nGlass Box vs GPT-4o Free-Form', fontsize=15, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(categories, fontsize=12)
ax.set_ylim(0, 35)
ax.legend(fontsize=12)

# Add value labels
for i, (bar1, bar2) in enumerate(zip(bars1, bars2)):
    height1 = bar1.get_height()
    height2 = bar2.get_height()

    # Caught label
    ax.text(bar1.get_x() + bar1.get_width()/2., height1/2,
            f'{int(height1)} caught\n({int(height1/30*100)}%)',
            ha='center', va='center', fontsize=11, fontweight='bold', color='white')

    # Missed label
    if height2 > 0:
        ax.text(bar2.get_x() + bar2.get_width()/2., height1 + height2/2,
                f'{int(height2)} missed\n({int(height2/30*100)}%)',
                ha='center', va='center', fontsize=11, fontweight='bold', color='white')

plt.tight_layout()
plt.savefig(output_dir / 'caught_vs_missed.png', dpi=300, bbox_inches='tight')
print(f"\n✓ Saved: caught_vs_missed.png")
plt.close()

# ============================================================
# GRAPH 2: Error-by-Error Detection Grid
# ============================================================
fig, axes = plt.subplots(1, 3, figsize=(18, 6))

for idx, (product_key, product_name) in enumerate(products.items()):
    ax = axes[idx]

    product_df = df[df['Product'] == product_name]

    errors = list(range(1, 11))
    gb_detection = [product_df[product_df['Error_Level'] == e]['Glass_Box_Binary'].values[0] for e in errors]
    gpt_detection = [product_df[product_df['Error_Level'] == e]['GPT4o_Binary'].values[0] for e in errors]

    x = np.arange(len(errors))
    width = 0.35

    bars1 = ax.bar(x - width/2, gb_detection, width, label='Glass Box', color='#3498db')
    bars2 = ax.bar(x + width/2, gpt_detection, width, label='GPT-4o', color='#9b59b6')

    ax.set_xlabel('Error Number', fontsize=11, fontweight='bold')
    ax.set_ylabel('Detected (1) / Missed (0)', fontsize=11, fontweight='bold')
    ax.set_title(product_name, fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([f'#{e}' for e in errors])
    ax.set_ylim(0, 1.3)
    ax.legend(fontsize=10)
    ax.grid(axis='y', alpha=0.3)

    # Add detection indicators
    for i, (gb, gpt) in enumerate(zip(gb_detection, gpt_detection)):
        if gb == 1:
            ax.text(i - width/2, gb + 0.05, '✓', ha='center', va='bottom',
                   fontsize=14, fontweight='bold', color='green')
        else:
            ax.text(i - width/2, 0.05, '✗', ha='center', va='bottom',
                   fontsize=14, fontweight='bold', color='red')

        if gpt == 1:
            ax.text(i + width/2, gpt + 0.05, '✓', ha='center', va='bottom',
                   fontsize=14, fontweight='bold', color='green')
        else:
            ax.text(i + width/2, 0.05, '✗', ha='center', va='bottom',
                   fontsize=14, fontweight='bold', color='red')

plt.suptitle('Error-by-Error Detection: Which Errors Were Caught?', fontsize=15, fontweight='bold', y=1.00)
plt.tight_layout()
plt.savefig(output_dir / 'error_by_error_detection.png', dpi=300, bbox_inches='tight')
print(f"✓ Saved: error_by_error_detection.png")
plt.close()

# ============================================================
# GRAPH 3: Simple Heatmap - Red = Missed, Green = Caught
# ============================================================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 5))

# Prepare matrices
products_list = ['Smartphone', 'Melatonin', 'CoreCoin']
gb_matrix = np.zeros((3, 10))
gpt_matrix = np.zeros((3, 10))

for i, product in enumerate(products_list):
    product_df = df[df['Product'] == product]
    for j, level in enumerate(range(1, 11)):
        gb_matrix[i, j] = product_df[product_df['Error_Level'] == level]['Glass_Box_Binary'].values[0]
        gpt_matrix[i, j] = product_df[product_df['Error_Level'] == level]['GPT4o_Binary'].values[0]

# Glass Box heatmap
im1 = ax1.imshow(gb_matrix, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)
ax1.set_xticks(np.arange(10))
ax1.set_yticks(np.arange(3))
ax1.set_xticklabels([f'Error {i}' for i in range(1, 11)], rotation=45, ha='right')
ax1.set_yticklabels(products_list)
ax1.set_title('Glass Box Detection\n(Green = Caught, Red = Missed)', fontsize=12, fontweight='bold')

# Add text annotations
for i in range(3):
    for j in range(10):
        symbol = '✓' if gb_matrix[i, j] == 1 else '✗'
        color = 'white' if gb_matrix[i, j] == 1 else 'black'
        ax1.text(j, i, symbol, ha="center", va="center", color=color, fontsize=16, fontweight='bold')

# GPT-4o heatmap
im2 = ax2.imshow(gpt_matrix, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)
ax2.set_xticks(np.arange(10))
ax2.set_yticks(np.arange(3))
ax2.set_xticklabels([f'Error {i}' for i in range(1, 11)], rotation=45, ha='right')
ax2.set_yticklabels(products_list)
ax2.set_title('GPT-4o Free-Form Detection\n(Green = Caught, Red = Missed)', fontsize=12, fontweight='bold')

# Add text annotations
for i in range(3):
    for j in range(10):
        symbol = '✓' if gpt_matrix[i, j] == 1 else '✗'
        color = 'white' if gpt_matrix[i, j] == 1 else 'black'
        ax2.text(j, i, symbol, ha="center", va="center", color=color, fontsize=16, fontweight='bold')

plt.suptitle('Error Detection Heatmap: Caught (✓) vs Missed (✗)', fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(output_dir / 'detection_heatmap.png', dpi=300, bbox_inches='tight')
print(f"✓ Saved: detection_heatmap.png")
plt.close()

# ============================================================
# SUMMARY STATS
# ============================================================
print("\n" + "="*80)
print("SUMMARY STATISTICS")
print("="*80)

print("\nGlass Box:")
print(f"  Caught: {gb_caught}/30 ({gb_caught/30*100:.0f}%)")
print(f"  Missed: {gb_missed}/30 ({gb_missed/30*100:.0f}%)")

print("\nGPT-4o Free-Form:")
print(f"  Caught: {gpt_caught}/30 ({gpt_caught/30*100:.0f}%)")
print(f"  Missed: {gpt_missed}/30 ({gpt_missed/30*100:.0f}%)")

print("\nMissed Errors by Product (GPT-4o):")
for product_name in products_list:
    product_df = df[df['Product'] == product_name]
    missed_errors = product_df[product_df['GPT4o'] == 'Missed']['Error_Level'].tolist()
    if missed_errors:
        print(f"  {product_name}: Errors {', '.join(map(str, missed_errors))}")
    else:
        print(f"  {product_name}: None (all caught)")

print("\n" + "="*80)
print(f"SIMPLE VISUALIZATIONS COMPLETE")
print("="*80)
print(f"Output directory: {output_dir}")
print(f"\nGenerated:")
print(f"  1. error_detection_table.csv - Simple table")
print(f"  2. caught_vs_missed.png - Bar chart comparison")
print(f"  3. error_by_error_detection.png - Which errors caught")
print(f"  4. detection_heatmap.png - Visual heatmap")
print("="*80)
