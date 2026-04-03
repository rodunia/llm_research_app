#!/usr/bin/env python3
"""
Compare Glass Box Audit vs GPT-4o Direct Detection

Analyzes detection rates, error types, and cost across two methods:
1. Glass Box: GPT-4o-mini extraction + RoBERTa NLI + numerical rules
2. GPT-4o Direct: GPT-4o (temp 0) direct error detection
"""

import json
import csv
from pathlib import Path
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# Paths
GLASS_BOX_DIR = Path('results/pilot_individual_2026')
GPT4O_DIR = Path('results/gpt4o_baseline')
OUTPUT_DIR = Path('results/comparison_analysis')
OUTPUT_DIR.mkdir(exist_ok=True)

def load_glass_box_results():
    """Load Glass Box audit results from CSV files."""
    results = {}

    for product in ['melatonin', 'smartphone', 'corecoin']:
        for i in range(1, 11):
            file_id = f'{product}_{i}'
            csv_path = GLASS_BOX_DIR / f'{file_id}.csv'

            if not csv_path.exists():
                print(f"⚠️  Missing Glass Box result: {file_id}")
                continue

            with open(csv_path) as f:
                reader = csv.DictReader(f)
                violations = list(reader)

            # Check if error detected (has violations)
            detected = len(violations) > 0

            results[file_id] = {
                'detected': detected,
                'violation_count': len(violations),
                'violations': violations,
                'method': 'glass_box'
            }

    return results

def load_gpt4o_results():
    """Load GPT-4o baseline results from JSON files."""
    results = {}

    with open(GPT4O_DIR / 'all_results.json') as f:
        all_results = json.load(f)

    for file_id, data in all_results.items():
        if data.get('status') != 'success':
            print(f"⚠️  GPT-4o error on {file_id}: {data.get('error_message', 'Unknown')}")
            continue

        results[file_id] = {
            'detected': data.get('errors_detected', False),
            'error_count': data.get('error_count', 0),
            'errors': data.get('errors', []),
            'tokens': data.get('total_tokens', 0),
            'method': 'gpt4o'
        }

    return results

def compare_detection_rates(glass_box, gpt4o):
    """Compare detection rates between two methods."""

    comparison = {
        'both_detected': [],
        'only_glass_box': [],
        'only_gpt4o': [],
        'both_missed': []
    }

    all_files = set(glass_box.keys()) | set(gpt4o.keys())

    for file_id in sorted(all_files):
        gb_detected = glass_box.get(file_id, {}).get('detected', False)
        g4_detected = gpt4o.get(file_id, {}).get('detected', False)

        if gb_detected and g4_detected:
            comparison['both_detected'].append(file_id)
        elif gb_detected and not g4_detected:
            comparison['only_glass_box'].append(file_id)
        elif not gb_detected and g4_detected:
            comparison['only_gpt4o'].append(file_id)
        else:
            comparison['both_missed'].append(file_id)

    return comparison

def analyze_by_product(glass_box, gpt4o):
    """Analyze detection rates by product category."""

    products = {
        'melatonin': [f'melatonin_{i}' for i in range(1, 11)],
        'smartphone': [f'smartphone_{i}' for i in range(1, 11)],
        'corecoin': [f'corecoin_{i}' for i in range(1, 11)]
    }

    product_stats = {}

    for product_name, file_ids in products.items():
        gb_detected = sum(1 for fid in file_ids if glass_box.get(fid, {}).get('detected', False))
        g4_detected = sum(1 for fid in file_ids if gpt4o.get(fid, {}).get('detected', False))

        product_stats[product_name] = {
            'glass_box': gb_detected,
            'gpt4o': g4_detected,
            'total': len(file_ids)
        }

    return product_stats

def calculate_cost_analysis(gpt4o):
    """Calculate cost comparison (Glass Box uses GPT-4o-mini, GPT-4o Direct uses GPT-4o)."""

    # Pricing per 1M tokens
    GPT4O_MINI_INPUT = 0.150  # $0.15/1M tokens
    GPT4O_MINI_OUTPUT = 0.600  # $0.60/1M tokens
    GPT4O_INPUT = 2.50  # $2.50/1M tokens
    GPT4O_OUTPUT = 10.00  # $10.00/1M tokens

    # GPT-4o Direct total tokens
    total_tokens_gpt4o = sum(data.get('tokens', 0) for data in gpt4o.values())

    # Estimate: GPT-4o-mini uses ~3500 prompt + ~500 completion per file (based on logs)
    # Glass Box also uses RoBERTa (free, local)
    num_files = len(gpt4o)
    glass_box_prompt_tokens = num_files * 3500
    glass_box_completion_tokens = num_files * 500

    # Calculate costs
    cost_gpt4o_direct = (total_tokens_gpt4o / 2 * GPT4O_INPUT / 1_000_000) + \
                        (total_tokens_gpt4o / 2 * GPT4O_OUTPUT / 1_000_000)

    cost_glass_box = (glass_box_prompt_tokens * GPT4O_MINI_INPUT / 1_000_000) + \
                     (glass_box_completion_tokens * GPT4O_MINI_OUTPUT / 1_000_000)

    return {
        'gpt4o_direct': {
            'cost': cost_gpt4o_direct,
            'total_tokens': total_tokens_gpt4o
        },
        'glass_box': {
            'cost': cost_glass_box,
            'prompt_tokens': glass_box_prompt_tokens,
            'completion_tokens': glass_box_completion_tokens
        },
        'cost_ratio': cost_gpt4o_direct / cost_glass_box if cost_glass_box > 0 else 0
    }

def generate_plots(comparison, product_stats, cost_analysis):
    """Generate comparison plots."""

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Plot 1: Venn Diagram (Detection Overlap)
    ax1 = axes[0, 0]
    both = len(comparison['both_detected'])
    only_gb = len(comparison['only_glass_box'])
    only_g4 = len(comparison['only_gpt4o'])
    missed = len(comparison['both_missed'])

    categories = ['Both\nDetected', 'Only\nGlass Box', 'Only\nGPT-4o', 'Both\nMissed']
    values = [both, only_gb, only_g4, missed]
    colors = ['#2ecc71', '#3498db', '#e74c3c', '#95a5a6']

    ax1.bar(categories, values, color=colors, alpha=0.8, edgecolor='black')
    ax1.set_ylabel('Number of Files', fontsize=11, fontweight='bold')
    ax1.set_title('Detection Overlap (30 Files Total)', fontsize=12, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)

    for i, v in enumerate(values):
        ax1.text(i, v + 0.5, str(v), ha='center', fontweight='bold')

    # Plot 2: Detection Rate by Product
    ax2 = axes[0, 1]
    products = list(product_stats.keys())
    gb_rates = [product_stats[p]['glass_box'] for p in products]
    g4_rates = [product_stats[p]['gpt4o'] for p in products]

    x = range(len(products))
    width = 0.35

    ax2.bar([i - width/2 for i in x], gb_rates, width, label='Glass Box', color='#3498db', alpha=0.8, edgecolor='black')
    ax2.bar([i + width/2 for i in x], g4_rates, width, label='GPT-4o Direct', color='#e74c3c', alpha=0.8, edgecolor='black')

    ax2.set_xlabel('Product Category', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Files Detected (out of 10)', fontsize=11, fontweight='bold')
    ax2.set_title('Detection Rate by Product', fontsize=12, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels([p.title() for p in products])
    ax2.legend(fontsize=10)
    ax2.grid(axis='y', alpha=0.3)
    ax2.set_ylim(0, 11)

    # Add value labels on bars
    for i in range(len(products)):
        ax2.text(i - width/2, gb_rates[i] + 0.3, str(gb_rates[i]), ha='center', fontweight='bold', fontsize=9)
        ax2.text(i + width/2, g4_rates[i] + 0.3, str(g4_rates[i]), ha='center', fontweight='bold', fontsize=9)

    # Plot 3: Cost Comparison
    ax3 = axes[1, 0]
    methods = ['Glass Box\n(GPT-4o-mini\n+ RoBERTa)', 'GPT-4o Direct\n(temp 0)']
    costs = [cost_analysis['glass_box']['cost'], cost_analysis['gpt4o_direct']['cost']]
    colors_cost = ['#2ecc71', '#e74c3c']

    bars = ax3.bar(methods, costs, color=colors_cost, alpha=0.8, edgecolor='black')
    ax3.set_ylabel('Cost (USD) for 30 Files', fontsize=11, fontweight='bold')
    ax3.set_title('Cost Comparison', fontsize=12, fontweight='bold')
    ax3.grid(axis='y', alpha=0.3)

    for i, (bar, cost) in enumerate(zip(bars, costs)):
        ax3.text(i, cost + 0.01, f'${cost:.2f}', ha='center', fontweight='bold', fontsize=10)

    # Add cost ratio text
    ratio = cost_analysis['cost_ratio']
    ax3.text(0.5, max(costs) * 0.8, f'GPT-4o Direct is {ratio:.1f}x\nmore expensive',
             ha='center', fontsize=10, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # Plot 4: Overall Summary
    ax4 = axes[1, 1]
    ax4.axis('off')

    total_files = 30
    gb_total = sum(product_stats[p]['glass_box'] for p in product_stats)
    g4_total = sum(product_stats[p]['gpt4o'] for p in product_stats)

    summary_text = f"""
    SUMMARY STATISTICS

    Total Files Analyzed: {total_files}

    Glass Box Detection:
      • Files detected: {gb_total}/{total_files} ({gb_total/total_files*100:.0f}%)
      • Cost: ${cost_analysis['glass_box']['cost']:.2f}
      • Method: Multi-stage pipeline

    GPT-4o Direct Detection:
      • Files detected: {g4_total}/{total_files} ({g4_total/total_files*100:.0f}%)
      • Cost: ${cost_analysis['gpt4o_direct']['cost']:.2f}
      • Method: Single-stage (temp 0)

    Detection Overlap:
      • Both detected: {both} files
      • Only Glass Box: {only_gb} files
      • Only GPT-4o: {only_g4} files
      • Both missed: {missed} files

    Cost Efficiency:
      • GPT-4o is {ratio:.1f}x more expensive
      • Glass Box uses GPT-4o-mini + RoBERTa
    """

    ax4.text(0.1, 0.9, summary_text, transform=ax4.transAxes,
             fontsize=10, verticalalignment='top', family='monospace',
             bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.3))

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'comparison_plots.png', dpi=300, bbox_inches='tight')
    print(f"✅ Plots saved to {OUTPUT_DIR / 'comparison_plots.png'}")

    return fig

def save_comparison_csv(comparison, glass_box, gpt4o):
    """Save detailed comparison to CSV."""

    csv_path = OUTPUT_DIR / 'detection_comparison.csv'

    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['File', 'Glass_Box_Detected', 'GPT4o_Detected', 'Glass_Box_Violations', 'GPT4o_Errors', 'Overlap'])

        all_files = sorted(set(glass_box.keys()) | set(gpt4o.keys()))

        for file_id in all_files:
            gb_detected = glass_box.get(file_id, {}).get('detected', False)
            g4_detected = gpt4o.get(file_id, {}).get('detected', False)
            gb_count = glass_box.get(file_id, {}).get('violation_count', 0)
            g4_count = gpt4o.get(file_id, {}).get('error_count', 0)

            if gb_detected and g4_detected:
                overlap = 'Both'
            elif gb_detected:
                overlap = 'Glass Box Only'
            elif g4_detected:
                overlap = 'GPT-4o Only'
            else:
                overlap = 'Neither'

            writer.writerow([file_id, gb_detected, g4_detected, gb_count, g4_count, overlap])

    print(f"✅ Comparison CSV saved to {csv_path}")

def main():
    print("="*70)
    print("GLASS BOX vs GPT-4o DIRECT DETECTION COMPARISON")
    print("="*70)
    print()

    # Load results
    print("Loading Glass Box results...")
    glass_box = load_glass_box_results()
    print(f"  ✓ Loaded {len(glass_box)} files")

    print("Loading GPT-4o results...")
    gpt4o = load_gpt4o_results()
    print(f"  ✓ Loaded {len(gpt4o)} files")
    print()

    # Compare detection rates
    print("Comparing detection rates...")
    comparison = compare_detection_rates(glass_box, gpt4o)
    print(f"  ✓ Both detected: {len(comparison['both_detected'])} files")
    print(f"  ✓ Only Glass Box: {len(comparison['only_glass_box'])} files")
    print(f"  ✓ Only GPT-4o: {len(comparison['only_gpt4o'])} files")
    print(f"  ✓ Both missed: {len(comparison['both_missed'])} files")
    print()

    # Analyze by product
    print("Analyzing by product...")
    product_stats = analyze_by_product(glass_box, gpt4o)
    for product, stats in product_stats.items():
        print(f"  {product.title()}:")
        print(f"    Glass Box: {stats['glass_box']}/{stats['total']}")
        print(f"    GPT-4o:    {stats['gpt4o']}/{stats['total']}")
    print()

    # Cost analysis
    print("Calculating cost analysis...")
    cost_analysis = calculate_cost_analysis(gpt4o)
    print(f"  Glass Box cost: ${cost_analysis['glass_box']['cost']:.2f}")
    print(f"  GPT-4o cost:    ${cost_analysis['gpt4o_direct']['cost']:.2f}")
    print(f"  Cost ratio:     {cost_analysis['cost_ratio']:.1f}x")
    print()

    # Generate plots
    print("Generating plots...")
    generate_plots(comparison, product_stats, cost_analysis)
    print()

    # Save CSV
    print("Saving comparison CSV...")
    save_comparison_csv(comparison, glass_box, gpt4o)
    print()

    # Summary
    print("="*70)
    print("SUMMARY")
    print("="*70)
    gb_total = sum(product_stats[p]['glass_box'] for p in product_stats)
    g4_total = sum(product_stats[p]['gpt4o'] for p in product_stats)
    print(f"Glass Box:  {gb_total}/30 detected ({gb_total/30*100:.0f}%)")
    print(f"GPT-4o:     {g4_total}/30 detected ({g4_total/30*100:.0f}%)")
    print(f"Cost ratio: GPT-4o is {cost_analysis['cost_ratio']:.1f}x more expensive")
    print()

if __name__ == '__main__':
    main()
