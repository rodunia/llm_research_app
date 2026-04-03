#!/usr/bin/env python3
"""
3-Way Comparison: Glass Box vs GPT-4o Run 1 vs GPT-4o Run 2

Analyzes:
1. Glass Box stability (already validated in STABILITY_REPORT_30_30.md)
2. GPT-4o stability (Run 1 vs Run 2)
3. Glass Box vs GPT-4o (both runs)
"""

import json
import csv
from pathlib import Path
from collections import defaultdict
import matplotlib.pyplot as plt

# Paths
GLASS_BOX_DIR = Path('results/pilot_individual_2026')
GPT4O_RUN1_DIR = Path('results/gpt4o_baseline_run1')
GPT4O_RUN2_DIR = Path('results/gpt4o_baseline')
OUTPUT_DIR = Path('results/comparison_analysis')
OUTPUT_DIR.mkdir(exist_ok=True)

def load_glass_box_results():
    """Load Glass Box audit results."""
    results = {}
    for product in ['melatonin', 'smartphone', 'corecoin']:
        for i in range(1, 11):
            file_id = f'{product}_{i}'
            csv_path = GLASS_BOX_DIR / f'{file_id}.csv'
            if not csv_path.exists():
                continue
            with open(csv_path) as f:
                reader = csv.DictReader(f)
                violations = list(reader)
            results[file_id] = {
                'detected': len(violations) > 0,
                'count': len(violations)
            }
    return results

def load_gpt4o_run(run_dir):
    """Load GPT-4o results from a run directory."""
    results = {}
    with open(run_dir / 'all_results.json') as f:
        all_results = json.load(f)
    for file_id, data in all_results.items():
        if data.get('status') != 'success':
            continue
        results[file_id] = {
            'detected': data.get('errors_detected', False),
            'count': data.get('error_count', 0),
            'errors': data.get('errors', [])
        }
    return results

def compare_gpt4o_stability(run1, run2):
    """Compare GPT-4o Run 1 vs Run 2 for stability."""
    identical = []
    different_detection = []
    different_count = []

    all_files = sorted(set(run1.keys()) | set(run2.keys()))

    for file_id in all_files:
        r1 = run1.get(file_id, {})
        r2 = run2.get(file_id, {})

        r1_detected = r1.get('detected', False)
        r2_detected = r2.get('detected', False)
        r1_count = r1.get('count', 0)
        r2_count = r2.get('count', 0)

        if r1_detected != r2_detected:
            different_detection.append(file_id)
        elif r1_count != r2_count:
            different_count.append((file_id, r1_count, r2_count))
        else:
            # Check if actual errors are identical
            r1_errors = [e['claim'] for e in r1.get('errors', [])]
            r2_errors = [e['claim'] for e in r2.get('errors', [])]
            if sorted(r1_errors) == sorted(r2_errors):
                identical.append(file_id)
            else:
                different_count.append((file_id, r1_count, r2_count))

    return {
        'identical': identical,
        'different_detection': different_detection,
        'different_count': different_count
    }

def three_way_comparison(glass_box, gpt4o_r1, gpt4o_r2):
    """Compare detection across all three runs."""

    comparison = {
        'all_three': [],
        'glass_box_only': [],
        'gpt4o_both': [],
        'gpt4o_r1_only': [],
        'gpt4o_r2_only': [],
        'none': []
    }

    all_files = sorted(set(glass_box.keys()) | set(gpt4o_r1.keys()) | set(gpt4o_r2.keys()))

    for file_id in all_files:
        gb = glass_box.get(file_id, {}).get('detected', False)
        g1 = gpt4o_r1.get(file_id, {}).get('detected', False)
        g2 = gpt4o_r2.get(file_id, {}).get('detected', False)

        if gb and g1 and g2:
            comparison['all_three'].append(file_id)
        elif gb and not g1 and not g2:
            comparison['glass_box_only'].append(file_id)
        elif not gb and g1 and g2:
            comparison['gpt4o_both'].append(file_id)
        elif not gb and g1 and not g2:
            comparison['gpt4o_r1_only'].append(file_id)
        elif not gb and not g1 and g2:
            comparison['gpt4o_r2_only'].append(file_id)
        elif not gb and not g1 and not g2:
            comparison['none'].append(file_id)

    return comparison

def generate_plots(glass_box, gpt4o_r1, gpt4o_r2, stability, three_way):
    """Generate 3-way comparison plots."""

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # Plot 1: Detection Rates (All Three Methods)
    ax1 = axes[0, 0]
    methods = ['Glass Box', 'GPT-4o Run 1', 'GPT-4o Run 2']
    gb_detected = sum(1 for v in glass_box.values() if v['detected'])
    g1_detected = sum(1 for v in gpt4o_r1.values() if v['detected'])
    g2_detected = sum(1 for v in gpt4o_r2.values() if v['detected'])

    detection_rates = [gb_detected, g1_detected, g2_detected]
    colors = ['#3498db', '#e74c3c', '#e67e22']

    bars = ax1.bar(methods, detection_rates, color=colors, alpha=0.8, edgecolor='black')
    ax1.set_ylabel('Files Detected (out of 30)', fontsize=12, fontweight='bold')
    ax1.set_title('Detection Rates: Glass Box vs GPT-4o (2 Runs)', fontsize=13, fontweight='bold')
    ax1.set_ylim(0, 32)
    ax1.axhline(y=30, color='green', linestyle='--', linewidth=2, alpha=0.5, label='Target: 30/30')
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)

    for bar, rate in zip(bars, detection_rates):
        ax1.text(bar.get_x() + bar.get_width()/2, rate + 0.5, f'{rate}/30\n({rate/30*100:.0f}%)',
                ha='center', fontweight='bold', fontsize=11)

    # Plot 2: GPT-4o Stability (Run 1 vs Run 2)
    ax2 = axes[0, 1]
    categories = ['Identical', 'Different\nCount', 'Different\nDetection']
    values = [
        len(stability['identical']),
        len(stability['different_count']),
        len(stability['different_detection'])
    ]
    colors_stab = ['#2ecc71', '#f39c12', '#e74c3c']

    bars2 = ax2.bar(categories, values, color=colors_stab, alpha=0.8, edgecolor='black')
    ax2.set_ylabel('Number of Files', fontsize=12, fontweight='bold')
    ax2.set_title('GPT-4o Stability (Run 1 vs Run 2)', fontsize=13, fontweight='bold')
    ax2.grid(axis='y', alpha=0.3)

    for bar, v in zip(bars2, values):
        ax2.text(bar.get_x() + bar.get_width()/2, v + 0.5, str(v),
                ha='center', fontweight='bold', fontsize=11)

    # Plot 3: Detection Overlap (Venn-style)
    ax3 = axes[1, 0]
    overlap_cats = ['All 3\nDetected', 'Glass Box\nOnly', 'GPT-4o\nBoth Runs', 'GPT-4o\nRun 1 Only', 'GPT-4o\nRun 2 Only', 'None']
    overlap_vals = [
        len(three_way['all_three']),
        len(three_way['glass_box_only']),
        len(three_way['gpt4o_both']),
        len(three_way['gpt4o_r1_only']),
        len(three_way['gpt4o_r2_only']),
        len(three_way['none'])
    ]
    colors_overlap = ['#2ecc71', '#3498db', '#e74c3c', '#f39c12', '#e67e22', '#95a5a6']

    bars3 = ax3.bar(overlap_cats, overlap_vals, color=colors_overlap, alpha=0.8, edgecolor='black')
    ax3.set_ylabel('Number of Files', fontsize=12, fontweight='bold')
    ax3.set_title('Detection Overlap (3-Way Comparison)', fontsize=13, fontweight='bold')
    ax3.grid(axis='y', alpha=0.3)
    ax3.tick_params(axis='x', labelsize=9)

    for bar, v in zip(bars3, overlap_vals):
        if v > 0:
            ax3.text(bar.get_x() + bar.get_width()/2, v + 0.5, str(v),
                    ha='center', fontweight='bold', fontsize=10)

    # Plot 4: Summary Statistics
    ax4 = axes[1, 1]
    ax4.axis('off')

    identical_pct = len(stability['identical']) / 30 * 100
    detection_stable = 30 - len(stability['different_detection'])

    summary_text = f"""
    STABILITY ANALYSIS

    Glass Box Stability (from previous validation):
      • Run 1: 30/30 detected (100%)
      • Run 2: 30/30 detected (100%)
      • Identical detection: 30/30 files
      • File-level variations: 9/30 (minor)

    GPT-4o Stability (temp 0):
      • Run 1: {g1_detected}/30 detected ({g1_detected/30*100:.0f}%)
      • Run 2: {g2_detected}/30 detected ({g2_detected/30*100:.0f}%)
      • Identical files: {len(stability['identical'])}/30 ({identical_pct:.0f}%)
      • Different counts: {len(stability['different_count'])} files
      • Different detection: {len(stability['different_detection'])} files

    Detection Overlap:
      • All 3 detected: {len(three_way['all_three'])} files
      • Glass Box only: {len(three_way['glass_box_only'])} files
      • GPT-4o both runs: {len(three_way['gpt4o_both'])} files

    Verdict:
      • Glass Box: 100% stable detection
      • GPT-4o: {detection_stable}/30 stable detection
    """

    ax4.text(0.05, 0.95, summary_text, transform=ax4.transAxes,
            fontsize=10, verticalalignment='top', family='monospace',
            bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.3))

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'three_way_comparison.png', dpi=300, bbox_inches='tight')
    print(f"✅ 3-way plots saved to {OUTPUT_DIR / 'three_way_comparison.png'}")

def save_detailed_csv(glass_box, gpt4o_r1, gpt4o_r2):
    """Save detailed 3-way comparison CSV."""

    csv_path = OUTPUT_DIR / 'three_way_comparison.csv'

    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            'File',
            'Glass_Box_Detected', 'Glass_Box_Count',
            'GPT4o_R1_Detected', 'GPT4o_R1_Count',
            'GPT4o_R2_Detected', 'GPT4o_R2_Count',
            'GPT4o_Stable', 'All_Three_Detected'
        ])

        all_files = sorted(set(glass_box.keys()) | set(gpt4o_r1.keys()) | set(gpt4o_r2.keys()))

        for file_id in all_files:
            gb = glass_box.get(file_id, {})
            g1 = gpt4o_r1.get(file_id, {})
            g2 = gpt4o_r2.get(file_id, {})

            gb_detected = gb.get('detected', False)
            g1_detected = g1.get('detected', False)
            g2_detected = g2.get('detected', False)

            gb_count = gb.get('count', 0)
            g1_count = g1.get('count', 0)
            g2_count = g2.get('count', 0)

            gpt4o_stable = (g1_detected == g2_detected and g1_count == g2_count)
            all_three = (gb_detected and g1_detected and g2_detected)

            writer.writerow([
                file_id,
                gb_detected, gb_count,
                g1_detected, g1_count,
                g2_detected, g2_count,
                gpt4o_stable, all_three
            ])

    print(f"✅ 3-way CSV saved to {csv_path}")

def main():
    print("="*70)
    print("3-WAY COMPARISON: GLASS BOX vs GPT-4o (RUN 1) vs GPT-4o (RUN 2)")
    print("="*70)
    print()

    # Load all results
    print("Loading results...")
    glass_box = load_glass_box_results()
    gpt4o_r1 = load_gpt4o_run(GPT4O_RUN1_DIR)
    gpt4o_r2 = load_gpt4o_run(GPT4O_RUN2_DIR)
    print(f"  ✓ Glass Box: {len(glass_box)} files")
    print(f"  ✓ GPT-4o Run 1: {len(gpt4o_r1)} files")
    print(f"  ✓ GPT-4o Run 2: {len(gpt4o_r2)} files")
    print()

    # Compare GPT-4o stability
    print("Analyzing GPT-4o stability...")
    stability = compare_gpt4o_stability(gpt4o_r1, gpt4o_r2)
    print(f"  ✓ Identical: {len(stability['identical'])} files")
    print(f"  ✓ Different count: {len(stability['different_count'])} files")
    print(f"  ✓ Different detection: {len(stability['different_detection'])} files")
    print()

    # 3-way comparison
    print("Performing 3-way comparison...")
    three_way = three_way_comparison(glass_box, gpt4o_r1, gpt4o_r2)
    print(f"  ✓ All 3 detected: {len(three_way['all_three'])} files")
    print(f"  ✓ Glass Box only: {len(three_way['glass_box_only'])} files")
    print(f"  ✓ GPT-4o both runs: {len(three_way['gpt4o_both'])} files")
    print(f"  ✓ GPT-4o Run 1 only: {len(three_way['gpt4o_r1_only'])} files")
    print(f"  ✓ GPT-4o Run 2 only: {len(three_way['gpt4o_r2_only'])} files")
    print()

    # Generate plots
    print("Generating 3-way comparison plots...")
    generate_plots(glass_box, gpt4o_r1, gpt4o_r2, stability, three_way)
    print()

    # Save CSV
    print("Saving detailed comparison CSV...")
    save_detailed_csv(glass_box, gpt4o_r1, gpt4o_r2)
    print()

    # Summary
    print("="*70)
    print("SUMMARY")
    print("="*70)
    gb_detected = sum(1 for v in glass_box.values() if v['detected'])
    g1_detected = sum(1 for v in gpt4o_r1.values() if v['detected'])
    g2_detected = sum(1 for v in gpt4o_r2.values() if v['detected'])

    print(f"Glass Box:      {gb_detected}/30 ({gb_detected/30*100:.0f}%)")
    print(f"GPT-4o Run 1:   {g1_detected}/30 ({g1_detected/30*100:.0f}%)")
    print(f"GPT-4o Run 2:   {g2_detected}/30 ({g2_detected/30*100:.0f}%)")
    print(f"GPT-4o Stability: {len(stability['identical'])}/30 identical ({len(stability['identical'])/30*100:.0f}%)")
    print()

if __name__ == '__main__':
    main()
