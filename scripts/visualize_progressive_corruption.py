#!/usr/bin/env python3
"""
Generate visualization graphs for progressive corruption analysis.
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Load summary data
with open('results/errors_analysis/glass_box/summary.json', 'r') as f:
    glass_box_data = json.load(f)

with open('results/errors_analysis/gpt4o_freeform/summary.json', 'r') as f:
    gpt4o_data = json.load(f)

# Organize by corruption level and product
corruption_levels = {i: {'smartphone': {}, 'melatonin': {}, 'corecoin': {}} for i in range(1, 11)}

for gb_result in glass_box_data:
    file_name = gb_result['file']
    parts = file_name.split('_')
    product = parts[1]
    level = int(parts[2])

    corruption_levels[level][product]['glass_box'] = {
        'detected': gb_result['errors_detected'],
        'count': gb_result['violation_count']
    }

for gpt_result in gpt4o_data:
    file_name = gpt_result['file']
    parts = file_name.split('_')
    product = parts[1]
    level = int(parts[2])

    corruption_levels[level][product]['gpt4o'] = {
        'detected': gpt_result['errors_detected'],
        'count': gpt_result['error_count']
    }

# Create output directory
output_dir = Path('results/errors_analysis/visualizations')
output_dir.mkdir(parents=True, exist_ok=True)

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
colors = {'glass_box': '#2E86AB', 'gpt4o': '#A23B72'}

# ============================================================
# GRAPH 1: Detection Rate by Corruption Level
# ============================================================
fig, ax = plt.subplots(figsize=(12, 6))

levels = list(range(1, 11))
gb_detection = [sum(1 for p in ['smartphone', 'melatonin', 'corecoin'] if corruption_levels[level][p]['glass_box']['detected']) for level in levels]
gpt_detection = [sum(1 for p in ['smartphone', 'melatonin', 'corecoin'] if corruption_levels[level][p]['gpt4o']['detected']) for level in levels]

x = np.arange(len(levels))
width = 0.35

bars1 = ax.bar(x - width/2, gb_detection, width, label='Glass Box', color=colors['glass_box'])
bars2 = ax.bar(x + width/2, gpt_detection, width, label='GPT-4o', color=colors['gpt4o'])

ax.set_xlabel('Corruption Level (Number of Cumulative Errors)', fontsize=12, fontweight='bold')
ax.set_ylabel('Files with Errors Detected (out of 3)', fontsize=12, fontweight='bold')
ax.set_title('Detection Rate by Corruption Level\nGlass Box vs GPT-4o Free-Form', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(levels)
ax.set_ylim(0, 3.5)
ax.legend(fontsize=11)
ax.grid(axis='y', alpha=0.3)

# Add value labels on bars
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}/3',
                ha='center', va='bottom', fontsize=9)

plt.tight_layout()
plt.savefig(output_dir / 'detection_rate_by_level.png', dpi=300, bbox_inches='tight')
print(f"✓ Saved: {output_dir / 'detection_rate_by_level.png'}")
plt.close()

# ============================================================
# GRAPH 2: Average Violations by Corruption Level
# ============================================================
fig, ax = plt.subplots(figsize=(12, 6))

gb_avg_violations = []
gpt_avg_violations = []

for level in levels:
    gb_counts = [corruption_levels[level][p]['glass_box']['count'] for p in ['smartphone', 'melatonin', 'corecoin']]
    gpt_counts = [corruption_levels[level][p]['gpt4o']['count'] for p in ['smartphone', 'melatonin', 'corecoin']]

    gb_avg_violations.append(np.mean(gb_counts))
    gpt_avg_violations.append(np.mean(gpt_counts))

ax.plot(levels, gb_avg_violations, marker='o', linewidth=2.5, markersize=8,
        label='Glass Box', color=colors['glass_box'])
ax.plot(levels, gpt_avg_violations, marker='s', linewidth=2.5, markersize=8,
        label='GPT-4o', color=colors['gpt4o'])

ax.set_xlabel('Corruption Level (Number of Cumulative Errors)', fontsize=12, fontweight='bold')
ax.set_ylabel('Average Violations Flagged', fontsize=12, fontweight='bold')
ax.set_title('Average Violations Flagged by Corruption Level\nGlass Box vs GPT-4o Free-Form', fontsize=14, fontweight='bold')
ax.set_xticks(levels)
ax.legend(fontsize=11)
ax.grid(alpha=0.3)

plt.tight_layout()
plt.savefig(output_dir / 'avg_violations_by_level.png', dpi=300, bbox_inches='tight')
print(f"✓ Saved: {output_dir / 'avg_violations_by_level.png'}")
plt.close()

# ============================================================
# GRAPH 3: Product-Specific Detection Rates
# ============================================================
fig, axes = plt.subplots(1, 3, figsize=(16, 5))

products = {
    'smartphone': 'Smartphone (Nova X5)',
    'melatonin': 'Melatonin Supplement',
    'corecoin': 'CoreCoin (Crypto)'
}

for idx, (product_key, product_name) in enumerate(products.items()):
    ax = axes[idx]

    gb_product = [corruption_levels[level][product_key]['glass_box']['detected'] for level in levels]
    gpt_product = [corruption_levels[level][product_key]['gpt4o']['detected'] for level in levels]

    # Convert boolean to int
    gb_product = [1 if x else 0 for x in gb_product]
    gpt_product = [1 if x else 0 for x in gpt_product]

    x = np.arange(len(levels))
    width = 0.35

    ax.bar(x - width/2, gb_product, width, label='Glass Box', color=colors['glass_box'])
    ax.bar(x + width/2, gpt_product, width, label='GPT-4o', color=colors['gpt4o'])

    ax.set_xlabel('Corruption Level', fontsize=10, fontweight='bold')
    ax.set_ylabel('Detected (1) / Missed (0)', fontsize=10, fontweight='bold')
    ax.set_title(product_name, fontsize=11, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(levels)
    ax.set_ylim(0, 1.2)
    ax.legend(fontsize=9)
    ax.grid(axis='y', alpha=0.3)

plt.suptitle('Product-Specific Detection by Corruption Level', fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig(output_dir / 'product_specific_detection.png', dpi=300, bbox_inches='tight')
print(f"✓ Saved: {output_dir / 'product_specific_detection.png'}")
plt.close()

# ============================================================
# GRAPH 4: Overall Detection Summary (Bar Chart)
# ============================================================
fig, ax = plt.subplots(figsize=(10, 6))

categories = ['Smartphone\n(10 files)', 'Melatonin\n(10 files)', 'CoreCoin\n(10 files)', 'OVERALL\n(30 files)']

gb_detected = [
    sum(1 for level in levels if corruption_levels[level]['smartphone']['glass_box']['detected']),
    sum(1 for level in levels if corruption_levels[level]['melatonin']['glass_box']['detected']),
    sum(1 for level in levels if corruption_levels[level]['corecoin']['glass_box']['detected']),
    30
]

gpt_detected = [
    sum(1 for level in levels if corruption_levels[level]['smartphone']['gpt4o']['detected']),
    sum(1 for level in levels if corruption_levels[level]['melatonin']['gpt4o']['detected']),
    sum(1 for level in levels if corruption_levels[level]['corecoin']['gpt4o']['detected']),
    sum(1 for r in gpt4o_data if r['errors_detected'])
]

gb_total = [10, 10, 10, 30]

x = np.arange(len(categories))
width = 0.35

bars1 = ax.bar(x - width/2, gb_detected, width, label='Glass Box', color=colors['glass_box'])
bars2 = ax.bar(x + width/2, gpt_detected, width, label='GPT-4o', color=colors['gpt4o'])

ax.set_ylabel('Files with Errors Detected', fontsize=12, fontweight='bold')
ax.set_title('Detection Rate Comparison: Glass Box vs GPT-4o Free-Form', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(categories)
ax.legend(fontsize=11)
ax.grid(axis='y', alpha=0.3)

# Add value labels
for i, (bar1, bar2) in enumerate(zip(bars1, bars2)):
    height1 = bar1.get_height()
    height2 = bar2.get_height()
    total = gb_total[i]

    ax.text(bar1.get_x() + bar1.get_width()/2., height1,
            f'{int(height1)}/{total}\n(100%)',
            ha='center', va='bottom', fontsize=9, fontweight='bold')

    pct = int(height2)/total*100
    ax.text(bar2.get_x() + bar2.get_width()/2., height2,
            f'{int(height2)}/{total}\n({pct:.0f}%)',
            ha='center', va='bottom', fontsize=9, fontweight='bold')

plt.tight_layout()
plt.savefig(output_dir / 'overall_detection_summary.png', dpi=300, bbox_inches='tight')
print(f"✓ Saved: {output_dir / 'overall_detection_summary.png'}")
plt.close()

# ============================================================
# GRAPH 5: Heatmap - Violation Counts
# ============================================================
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

# Prepare data
products_list = ['Smartphone', 'Melatonin', 'CoreCoin']
gb_matrix = np.zeros((3, 10))
gpt_matrix = np.zeros((3, 10))

for i, product in enumerate(['smartphone', 'melatonin', 'corecoin']):
    for j, level in enumerate(range(1, 11)):
        gb_matrix[i, j] = corruption_levels[level][product]['glass_box']['count']
        gpt_matrix[i, j] = corruption_levels[level][product]['gpt4o']['count']

# Glass Box heatmap
im1 = ax1.imshow(gb_matrix, cmap='Blues', aspect='auto')
ax1.set_xticks(np.arange(10))
ax1.set_yticks(np.arange(3))
ax1.set_xticklabels(range(1, 11))
ax1.set_yticklabels(products_list)
ax1.set_xlabel('Corruption Level', fontsize=11, fontweight='bold')
ax1.set_title('Glass Box: Violations Flagged', fontsize=12, fontweight='bold')

# Add text annotations
for i in range(3):
    for j in range(10):
        text = ax1.text(j, i, int(gb_matrix[i, j]),
                       ha="center", va="center", color="black", fontsize=9, fontweight='bold')

plt.colorbar(im1, ax=ax1, label='Violation Count')

# GPT-4o heatmap
im2 = ax2.imshow(gpt_matrix, cmap='RdPu', aspect='auto')
ax2.set_xticks(np.arange(10))
ax2.set_yticks(np.arange(3))
ax2.set_xticklabels(range(1, 11))
ax2.set_yticklabels(products_list)
ax2.set_xlabel('Corruption Level', fontsize=11, fontweight='bold')
ax2.set_title('GPT-4o Free-Form: Violations Flagged', fontsize=12, fontweight='bold')

# Add text annotations
for i in range(3):
    for j in range(10):
        color = "white" if gpt_matrix[i, j] > 20 else "black"
        text = ax2.text(j, i, int(gpt_matrix[i, j]),
                       ha="center", va="center", color=color, fontsize=9, fontweight='bold')

plt.colorbar(im2, ax=ax2, label='Violation Count')

plt.suptitle('Violation Counts by Product and Corruption Level', fontsize=14, fontweight='bold', y=1.00)
plt.tight_layout()
plt.savefig(output_dir / 'violation_heatmap.png', dpi=300, bbox_inches='tight')
print(f"✓ Saved: {output_dir / 'violation_heatmap.png'}")
plt.close()

# ============================================================
# Summary
# ============================================================
print(f"\n{'='*60}")
print(f"VISUALIZATION COMPLETE")
print(f"{'='*60}")
print(f"Output directory: {output_dir}")
print(f"\nGenerated 5 visualizations:")
print(f"  1. detection_rate_by_level.png - Detection rate comparison")
print(f"  2. avg_violations_by_level.png - Average violations trend")
print(f"  3. product_specific_detection.png - Per-product detection")
print(f"  4. overall_detection_summary.png - Overall summary bars")
print(f"  5. violation_heatmap.png - Violation count heatmaps")
print(f"{'='*60}")
