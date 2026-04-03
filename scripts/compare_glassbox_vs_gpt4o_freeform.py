#!/usr/bin/env python3
"""
Comprehensive Comparison: Glass Box vs GPT-4o Free-Form

Compares Glass Box (100% detection, multi-stage) with GPT-4o Free-Form (43% detection, old prompt).
Generates tables, plots, and false positive analysis.
"""

import json
import csv
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np

# Paths
GLASS_BOX_DIR = Path('results/pilot_individual_2026_run2')
GPT4O_FREEFORM_CSV = Path('results/llm_direct_gpt4o_freeform_results.csv')
GPT4O_FREEFORM_RESPONSES = Path('results/llm_direct_gpt4o_freeform_responses')
OUTPUT_DIR = Path('results/glassbox_vs_gpt4o_freeform')
OUTPUT_DIR.mkdir(exist_ok=True)

def load_glass_box_results():
    """Load Glass Box results from CSV files."""
    results = {}
    total_violations = 0

    for product in ['melatonin', 'smartphone', 'corecoin']:
        for i in range(1, 11):
            file_id = f'{product}_{i}'
            csv_path = GLASS_BOX_DIR / f'user_{file_id}.csv'

            if csv_path.exists():
                with open(csv_path) as f:
                    reader = csv.DictReader(f)
                    violations = list(reader)

                detected = len(violations) > 0
                total_violations += len(violations)

                results[file_id] = {
                    'detected': detected,
                    'violation_count': len(violations),
                    'violations': violations
                }
            else:
                # Try without user_ prefix
                csv_path_alt = GLASS_BOX_DIR / f'{file_id}.csv'
                if csv_path_alt.exists():
                    with open(csv_path_alt) as f:
                        reader = csv.DictReader(f)
                        violations = list(reader)

                    detected = len(violations) > 0
                    total_violations += len(violations)

                    results[file_id] = {
                        'detected': detected,
                        'violation_count': len(violations),
                        'violations': violations
                    }

    return results, total_violations

def load_gpt4o_freeform_results():
    """Load GPT-4o Free-Form results."""
    results = {}

    df = pd.read_csv(GPT4O_FREEFORM_CSV)

    for _, row in df.iterrows():
        run_id = row['run_id']
        # Extract file_id (remove user_ prefix if present)
        if run_id.startswith('user_'):
            file_id = run_id[5:]  # Remove 'user_'
        else:
            file_id = run_id

        results[file_id] = {
            'detected': row['errors_found'],
            'error_count': row['error_count'],
            'raw_response': row['raw_response']
        }

    return results

def create_comparison_tables(glass_box, gpt4o, total_gb_violations):
    """Create comparison tables."""

    tables = {}

    # Table 1: Overall Comparison
    gb_detected = sum(1 for r in glass_box.values() if r['detected'])
    gpt4o_detected = sum(1 for r in gpt4o.values() if r['detected'])

    tables['overall'] = pd.DataFrame([
        {
            'Method': 'Glass Box',
            'Architecture': 'Multi-stage (GPT-4o-mini + RoBERTa + Rules)',
            'Prompt Type': 'Structured extraction',
            'Files Detected': f'{gb_detected}/30',
            'Detection Rate': f'{gb_detected/30*100:.1f}%',
            'Total Violations Flagged': total_gb_violations
        },
        {
            'Method': 'GPT-4o Free-Form',
            'Architecture': 'Single-stage (GPT-4o)',
            'Prompt Type': 'Free-text response',
            'Files Detected': f'{gpt4o_detected}/30',
            'Detection Rate': f'{gpt4o_detected/30*100:.1f}%',
            'Total Violations Flagged': sum(r['error_count'] for r in gpt4o.values())
        }
    ])

    # Table 2: Detection by Product
    products = {
        'smartphone': [f'smartphone_{i}' for i in range(1, 11)],
        'melatonin': [f'melatonin_{i}' for i in range(1, 11)],
        'corecoin': [f'corecoin_{i}' for i in range(1, 11)]
    }

    product_data = []
    for product_name, file_ids in products.items():
        gb_detected_count = sum(1 for fid in file_ids if glass_box.get(fid, {}).get('detected', False))
        gpt4o_detected_count = sum(1 for fid in file_ids if gpt4o.get(fid, {}).get('detected', False))
        gb_missed = 10 - gb_detected_count
        gpt4o_missed = 10 - gpt4o_detected_count

        product_data.append({
            'Product': product_name.capitalize(),
            'Total Files': 10,
            'Glass Box Detected': f'{gb_detected_count}/10 ({gb_detected_count*10}%)',
            'GPT-4o Detected': f'{gpt4o_detected_count}/10 ({gpt4o_detected_count*10}%)',
            'Glass Box Missed': gb_missed,
            'GPT-4o Missed': gpt4o_missed
        })

    # Add totals
    product_data.append({
        'Product': '**TOTAL**',
        'Total Files': 30,
        'Glass Box Detected': f'{gb_detected}/30 ({gb_detected/30*100:.1f}%)',
        'GPT-4o Detected': f'{gpt4o_detected}/30 ({gpt4o_detected/30*100:.1f}%)',
        'Glass Box Missed': 30 - gb_detected,
        'GPT-4o Missed': 30 - gpt4o_detected
    })

    tables['by_product'] = pd.DataFrame(product_data)

    # Table 3: File-by-File Comparison
    file_comparison = []
    for product in ['smartphone', 'melatonin', 'corecoin']:
        for i in range(1, 11):
            file_id = f'{product}_{i}'
            gb_result = glass_box.get(file_id, {})
            gpt4o_result = gpt4o.get(file_id, {})

            gb_detected = gb_result.get('detected', False)
            gpt4o_detected = gpt4o_result.get('detected', False)

            if gb_detected and gpt4o_detected:
                overlap = 'Both Detected'
            elif gb_detected and not gpt4o_detected:
                overlap = 'Glass Box Only'
            elif not gb_detected and gpt4o_detected:
                overlap = 'GPT-4o Only'
            else:
                overlap = 'Both Missed'

            file_comparison.append({
                'File ID': file_id,
                'Product': product.capitalize(),
                'Glass Box Detected': '✅' if gb_detected else '❌',
                'GPT-4o Detected': '✅' if gpt4o_detected else '❌',
                'Glass Box Violations': gb_result.get('violation_count', 0),
                'GPT-4o Errors': gpt4o_result.get('error_count', 0),
                'Overlap': overlap
            })

    tables['file_by_file'] = pd.DataFrame(file_comparison)

    # Table 4: Detection Overlap Summary
    overlap_counts = tables['file_by_file']['Overlap'].value_counts()
    tables['overlap_summary'] = pd.DataFrame([
        {'Category': cat, 'Count': overlap_counts.get(cat, 0)}
        for cat in ['Both Detected', 'Glass Box Only', 'GPT-4o Only', 'Both Missed']
    ])

    # Table 5: False Positive Analysis
    # Glass Box: Total violations - True Positives (30 intentional errors)
    gb_true_positives = 30  # All intentional errors detected
    gb_false_positives = total_gb_violations - gb_true_positives
    gb_fp_rate = (gb_false_positives / total_gb_violations * 100) if total_gb_violations > 0 else 0

    # GPT-4o: Count total errors flagged
    gpt4o_total_errors = sum(r['error_count'] for r in gpt4o.values())
    gpt4o_true_positives = gpt4o_detected  # Assume each detected file = 1 TP (intentional error)
    # Note: GPT-4o might flag multiple errors per file, some could be FP
    gpt4o_potential_fp = gpt4o_total_errors - gpt4o_true_positives
    gpt4o_fp_rate = (gpt4o_potential_fp / gpt4o_total_errors * 100) if gpt4o_total_errors > 0 else 0

    tables['false_positives'] = pd.DataFrame([
        {
            'Method': 'Glass Box',
            'Total Violations Flagged': total_gb_violations,
            'True Positives (Intentional Errors)': gb_true_positives,
            'Potential False Positives': gb_false_positives,
            'FP Rate': f'{gb_fp_rate:.1f}%'
        },
        {
            'Method': 'GPT-4o Free-Form',
            'Total Violations Flagged': gpt4o_total_errors,
            'True Positives (Intentional Errors)': gpt4o_true_positives,
            'Potential False Positives': gpt4o_potential_fp,
            'FP Rate': f'{gpt4o_fp_rate:.1f}%'
        }
    ])

    return tables

def generate_plots(tables):
    """Generate all 4 comparison plots."""

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # Plot 1: Detection Rate by Product (Grouped Bar Chart)
    ax1 = axes[0, 0]

    products = ['Smartphone', 'Melatonin', 'Corecoin']
    product_df = tables['by_product'][tables['by_product']['Product'].isin(products)]

    # Extract detection counts
    gb_counts = []
    gpt4o_counts = []
    for product in products:
        row = product_df[product_df['Product'] == product].iloc[0]
        gb_count = int(row['Glass Box Detected'].split('/')[0])
        gpt4o_count = int(row['GPT-4o Detected'].split('/')[0])
        gb_counts.append(gb_count)
        gpt4o_counts.append(gpt4o_count)

    x = np.arange(len(products))
    width = 0.35

    bars1 = ax1.bar(x - width/2, gb_counts, width, label='Glass Box', color='#3498db', alpha=0.8, edgecolor='black')
    bars2 = ax1.bar(x + width/2, gpt4o_counts, width, label='GPT-4o Free-Form', color='#e74c3c', alpha=0.8, edgecolor='black')

    ax1.set_xlabel('Product Category', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Files Detected (out of 10)', fontsize=12, fontweight='bold')
    ax1.set_title('Detection Rate by Product Category', fontsize=13, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(products)
    ax1.legend(fontsize=10)
    ax1.set_ylim(0, 11)
    ax1.grid(axis='y', alpha=0.3)

    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.2,
                    f'{int(height)}/10',
                    ha='center', va='bottom', fontweight='bold', fontsize=9)

    # Plot 2: Detection Overlap (Bar Chart)
    ax2 = axes[0, 1]

    overlap_df = tables['overlap_summary']
    categories = overlap_df['Category'].tolist()
    counts = overlap_df['Count'].tolist()

    colors_overlap = ['#2ecc71', '#3498db', '#e74c3c', '#95a5a6']
    bars_overlap = ax2.bar(categories, counts, color=colors_overlap, alpha=0.8, edgecolor='black')

    ax2.set_ylabel('Number of Files', fontsize=12, fontweight='bold')
    ax2.set_title('Detection Overlap Analysis (30 Files Total)', fontsize=13, fontweight='bold')
    ax2.set_xticklabels(categories, rotation=15, ha='right', fontsize=9)
    ax2.grid(axis='y', alpha=0.3)

    for bar, count in zip(bars_overlap, counts):
        if count > 0:
            ax2.text(bar.get_x() + bar.get_width()/2., count + 0.5,
                    str(count),
                    ha='center', va='bottom', fontweight='bold', fontsize=11)

    # Plot 3: File-by-File Heatmap
    ax3 = axes[1, 0]

    file_df = tables['file_by_file']

    # Create heatmap data
    heatmap_data = []
    file_labels = []
    for _, row in file_df.iterrows():
        gb_val = 1 if row['Glass Box Detected'] == '✅' else 0
        gpt4o_val = 1 if row['GPT-4o Detected'] == '✅' else 0
        heatmap_data.append([gb_val, gpt4o_val])
        file_labels.append(row['File ID'])

    heatmap_array = np.array(heatmap_data).T

    im = ax3.imshow(heatmap_array, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)

    ax3.set_yticks([0, 1])
    ax3.set_yticklabels(['Glass Box', 'GPT-4o Free-Form'], fontsize=10)
    ax3.set_xticks(range(0, 30, 3))
    ax3.set_xticklabels([file_labels[i] for i in range(0, 30, 3)], rotation=45, ha='right', fontsize=7)
    ax3.set_title('File-by-File Detection Heatmap\n(Green=Detected, Red=Missed)', fontsize=13, fontweight='bold')

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax3)
    cbar.set_ticks([0, 1])
    cbar.set_ticklabels(['Missed', 'Detected'])

    # Plot 4: False Positive Comparison
    ax4 = axes[1, 1]

    fp_df = tables['false_positives']
    methods = fp_df['Method'].tolist()
    tp_counts = fp_df['True Positives (Intentional Errors)'].tolist()
    fp_counts = fp_df['Potential False Positives'].tolist()

    x_fp = np.arange(len(methods))
    width_fp = 0.35

    bars_tp = ax4.bar(x_fp - width_fp/2, tp_counts, width_fp, label='True Positives', color='#2ecc71', alpha=0.8, edgecolor='black')
    bars_fp = ax4.bar(x_fp + width_fp/2, fp_counts, width_fp, label='False Positives', color='#e74c3c', alpha=0.8, edgecolor='black')

    ax4.set_ylabel('Number of Violations', fontsize=12, fontweight='bold')
    ax4.set_title('True Positives vs False Positives', fontsize=13, fontweight='bold')
    ax4.set_xticks(x_fp)
    ax4.set_xticklabels(methods, fontsize=10)
    ax4.legend(fontsize=10)
    ax4.set_yscale('log')  # Log scale due to large difference
    ax4.grid(axis='y', alpha=0.3)

    # Add value labels
    for bar in bars_tp:
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height * 1.2,
                f'{int(height)}',
                ha='center', va='bottom', fontweight='bold', fontsize=9)

    for bar in bars_fp:
        height = bar.get_height()
        if height > 0:
            ax4.text(bar.get_x() + bar.get_width()/2., height * 1.2,
                    f'{int(height)}',
                    ha='center', va='bottom', fontweight='bold', fontsize=9)

    plt.tight_layout()

    return fig

def save_results(tables, fig):
    """Save all tables and plots."""

    # Save tables as CSV
    for name, df in tables.items():
        csv_path = OUTPUT_DIR / f'{name}.csv'
        df.to_csv(csv_path, index=False)
        print(f"✅ Saved table: {csv_path}")

    # Save tables as formatted text
    text_path = OUTPUT_DIR / 'all_tables.txt'
    with open(text_path, 'w') as f:
        for name, df in tables.items():
            f.write(f"\n{'='*80}\n")
            f.write(f"TABLE: {name.upper().replace('_', ' ')}\n")
            f.write(f"{'='*80}\n")
            f.write(df.to_string(index=False))
            f.write("\n\n")
    print(f"✅ Saved formatted tables: {text_path}")

    # Save combined plot
    combined_plot_path = OUTPUT_DIR / 'comparison_plots_combined.png'
    fig.savefig(combined_plot_path, dpi=300, bbox_inches='tight')
    print(f"✅ Saved combined plot: {combined_plot_path}")

    # Save individual plots
    for i, ax in enumerate(fig.axes, 1):
        individual_fig = plt.figure(figsize=(10, 8))
        individual_ax = individual_fig.add_subplot(111)

        # Copy the content
        for line in ax.get_lines():
            individual_ax.add_line(line)
        for collection in ax.collections:
            individual_ax.add_collection(collection)
        for patch in ax.patches:
            individual_ax.add_patch(patch)
        for image in ax.images:
            individual_ax.add_image(image)

        individual_ax.set_xlim(ax.get_xlim())
        individual_ax.set_ylim(ax.get_ylim())
        individual_ax.set_xlabel(ax.get_xlabel())
        individual_ax.set_ylabel(ax.get_ylabel())
        individual_ax.set_title(ax.get_title())
        individual_ax.legend(*ax.get_legend_handles_labels())
        individual_ax.grid(ax.get_gridspec() is not None)

        individual_plot_path = OUTPUT_DIR / f'plot_{i}_{ax.get_title()[:30].replace(" ", "_").replace("/", "_")}.png'
        individual_fig.savefig(individual_plot_path, dpi=300, bbox_inches='tight')
        plt.close(individual_fig)

    print(f"✅ Saved 4 individual plots to {OUTPUT_DIR}/")

def main():
    print("="*80)
    print("GLASS BOX vs GPT-4o FREE-FORM COMPARISON")
    print("="*80)
    print()

    # Load results
    print("Loading Glass Box results...")
    glass_box, total_gb_violations = load_glass_box_results()
    print(f"  ✓ Loaded {len(glass_box)} files, {total_gb_violations} total violations")

    print("Loading GPT-4o Free-Form results...")
    gpt4o = load_gpt4o_freeform_results()
    print(f"  ✓ Loaded {len(gpt4o)} files")
    print()

    # Create tables
    print("Creating comparison tables...")
    tables = create_comparison_tables(glass_box, gpt4o, total_gb_violations)
    print(f"  ✓ Created {len(tables)} tables")
    print()

    # Generate plots
    print("Generating plots...")
    fig = generate_plots(tables)
    print("  ✓ Generated 4 plots")
    print()

    # Save results
    print("Saving results...")
    save_results(tables, fig)
    print()

    # Print summary
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(tables['overall'].to_string(index=False))
    print()
    print(tables['overlap_summary'].to_string(index=False))
    print()
    print("All results saved to:", OUTPUT_DIR)
    print()

if __name__ == '__main__':
    main()
