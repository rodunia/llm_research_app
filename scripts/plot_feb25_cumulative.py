#!/usr/bin/env python3
"""
Create cumulative scatter plot for Feb 25, 2026 data
Shows: Induced Errors (X) vs Detected Errors (Y)
Based on file-level detection (if detected, count all induced errors; if missed, count 0)
"""

import matplotlib.pyplot as plt
import numpy as np

# Feb 25 Results - which files were detected
# Glass Box: 30/30 (all detected)
# GPT-4o: 13/30 detected
# From COMPARISON_GLASSBOX_VS_GPT4O_FREEFORM.md:

# Smartphone (files 1-10)
GPT4O_DETECTED_SMARTPHONE = [
    False,  # 1: missed
    False,  # 2: missed
    False,  # 3: missed
    False,  # 4: missed
    False,  # 5: missed
    False,  # 6: missed
    True,   # 7: detected (only one!)
    False,  # 8: missed
    False,  # 9: missed
    False,  # 10: missed
]

# Melatonin (files 1-10)
GPT4O_DETECTED_MELATONIN = [
    False,  # 1: missed
    True,   # 2: detected
    True,   # 3: detected
    False,  # 4: missed
    False,  # 5: missed
    True,   # 6: detected
    True,   # 7: detected
    True,   # 8: detected
    False,  # 9: missed
    True,   # 10: detected
]

# CoreCoin (files 1-10)
GPT4O_DETECTED_CORECOIN = [
    True,   # 1: detected
    False,  # 2: missed
    True,   # 3: detected
    True,   # 4: detected
    False,  # 5: missed
    True,   # 6: detected
    True,   # 7: detected
    False,  # 8: missed
    False,  # 9: missed
    True,   # 10: detected
]

# Glass Box detected all 30
GLASS_BOX_DETECTED_ALL = [True] * 30

# Create cumulative data
def create_cumulative_data(detected_lists):
    """
    For each file i (1-10 per product):
    - Induced errors: i (file 1 has 1 error, file 2 has 2 errors, etc.)
    - Detected errors: i if detected, 0 if missed
    """
    induced = []
    detected = []

    file_num = 1
    for product_detected in detected_lists:
        for i, was_detected in enumerate(product_detected, 1):
            induced.append(i)
            detected.append(i if was_detected else 0)

    return np.array(induced), np.array(detected)

# Create data for both methods
glass_box_induced, glass_box_detected = create_cumulative_data(
    [[True]*10, [True]*10, [True]*10]  # All detected
)

gpt4o_induced, gpt4o_detected = create_cumulative_data([
    GPT4O_DETECTED_SMARTPHONE,
    GPT4O_DETECTED_MELATONIN,
    GPT4O_DETECTED_CORECOIN
])

# Create plot
fig, ax = plt.subplots(figsize=(10, 8))

# Plot perfect detection line
perfect_line = np.arange(0, 11)
ax.plot(perfect_line, perfect_line, 'k--', linewidth=2, alpha=0.3,
        label='Perfect Detection', zorder=1)

# Plot Glass Box (all detected = on the perfect line)
ax.scatter(glass_box_induced, glass_box_detected,
          s=100, alpha=0.7, color='#2E86AB', marker='o',
          edgecolors='black', linewidth=1.5, label='Glass Box', zorder=3)

# Plot GPT-4o (many at y=0 for missed files)
ax.scatter(gpt4o_induced, gpt4o_detected,
          s=100, alpha=0.7, color='#E63946', marker='s',
          edgecolors='black', linewidth=1.5, label='GPT-4o Freeform', zorder=2)

# Styling
ax.set_xlabel('Number of Induced Errors per File', fontsize=13, fontweight='bold')
ax.set_ylabel('Number of Detected Errors per File', fontsize=13, fontweight='bold')
ax.set_title('Cumulative Error Detection (Feb 25, 2026)\nGlass Box vs GPT-4o Freeform',
            fontsize=15, fontweight='bold')

ax.set_xlim(-0.5, 10.5)
ax.set_ylim(-0.5, 10.5)
ax.set_xticks(range(0, 11))
ax.set_yticks(range(0, 11))
ax.grid(True, alpha=0.3, linestyle='--')
ax.set_axisbelow(True)
ax.legend(loc='upper left', fontsize=12, framealpha=0.9)

# Add summary statistics
glass_box_total = np.sum(glass_box_detected)
gpt4o_total = np.sum(gpt4o_detected)
total_induced = 30 * 10 // 2  # Sum of 1+2+...+10 = 55 per product * 3 = 165

# Actually, total induced = sum(1 to 10) * 3 products
total_induced_correct = sum(range(1, 11)) * 3  # 55 * 3 = 165

summary_text = f'''Feb 25, 2026 Results:

Total Errors Induced: {total_induced_correct}

Glass Box Detected: {int(glass_box_total)}
  → Detection Rate: {glass_box_total/total_induced_correct*100:.1f}%

GPT-4o Detected: {int(gpt4o_total)}
  → Detection Rate: {gpt4o_total/total_induced_correct*100:.1f}%

Files Analyzed: 30 (3 products × 10 files)'''

ax.text(0.98, 0.35, summary_text, transform=ax.transAxes,
       fontsize=10, verticalalignment='top', horizontalalignment='right',
       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
       family='monospace')

# Add annotation for missed files
ax.annotate('GPT-4o missed 17 files\n(17 points at y=0)',
           xy=(5, 0), xytext=(7, 2.5),
           arrowprops=dict(arrowstyle='->', color='red', lw=2),
           fontsize=10, color='red', fontweight='bold',
           bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

plt.tight_layout()

# Save
output_path = 'results/errors_analysis/feb25_cumulative_detection.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f'✓ Saved: {output_path}')

print(f'\n=== Cumulative Statistics ===')
print(f'Total Errors Induced: {total_induced_correct}')
print(f'Glass Box Detected: {int(glass_box_total)} ({glass_box_total/total_induced_correct*100:.1f}%)')
print(f'GPT-4o Detected: {int(gpt4o_total)} ({gpt4o_total/total_induced_correct*100:.1f}%)')
print(f'\nFiles Detected:')
print(f'  Glass Box: 30/30')
print(f'  GPT-4o: 13/30')
