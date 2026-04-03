"""
Calculate research hypotheses from 54 LLM-generated files.
Tests the three main research questions from the paper.
"""

import csv
from pathlib import Path
from collections import defaultdict
from scipy import stats
import numpy as np

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
RESULTS_CSV = PROJECT_ROOT / "results" / "final_audit_results.csv"
EXPERIMENTS_CSV = PROJECT_ROOT / "results" / "experiments.csv"

def load_experiments_metadata():
    """Load run metadata from experiments.csv."""
    metadata = {}
    with open(EXPERIMENTS_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            run_id = row['run_id']
            metadata[run_id] = {
                'product_id': row['product_id'],
                'material_type': row['material_type'].replace('.j2', ''),
                'engine': row['engine'],
                'temperature': float(row['temperature'])
            }
    return metadata

def load_violations():
    """Load violations from final_audit_results.csv."""
    violations_by_file = defaultdict(list)
    with open(RESULTS_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Status'] == 'FAIL':
                filename = row['Filename'].replace('.txt', '')
                violations_by_file[filename].append({
                    'rule': row['Violated_Rule'],
                    'claim': row['Extracted_Claim'],
                    'confidence': float(row['Confidence_Score'])
                })
    return violations_by_file

def calculate_violations_per_file(violations_by_file, metadata):
    """Calculate violation counts per file with metadata."""
    data = []
    for run_id in metadata.keys():
        num_violations = len(violations_by_file.get(run_id, []))
        meta = metadata[run_id]
        data.append({
            'run_id': run_id,
            'violations': num_violations,
            'product': meta['product_id'],
            'engine': meta['engine'],
            'material': meta['material_type'],
            'temperature': meta['temperature']
        })
    return data

def hypothesis_1_people_pleasing(data):
    """
    H1: People-pleasing bias - Do LLMs generate overly positive content that violates rules?

    Prediction: If people-pleasing bias exists, ALL engines should have >0 avg violations
    AND violation rate should be significantly higher than random baseline.
    """
    print("\n" + "="*80)
    print("HYPOTHESIS 1: PEOPLE-PLEASING BIAS")
    print("="*80)
    print("\nResearch Question: Do LLMs generate overly positive marketing content")
    print("that violates compliance rules?")

    # Overall statistics
    violations = [d['violations'] for d in data]
    total_files = len(violations)
    files_with_violations = sum(1 for v in violations if v > 0)

    print(f"\n### Overall Detection")
    print(f"Files with violations: {files_with_violations}/{total_files} ({files_with_violations/total_files*100:.1f}%)")
    print(f"Total violations detected: {sum(violations)}")
    print(f"Mean violations per file: {np.mean(violations):.2f} (SD={np.std(violations):.2f})")
    print(f"Median violations per file: {np.median(violations):.1f}")

    # By engine
    print(f"\n### By Engine (LLM Provider)")
    print(f"{'Engine':<15} {'Files':<8} {'Mean Violations':<18} {'Files w/ Violations'}")
    print("-" * 70)

    engine_stats = {}
    for engine in ['openai', 'google', 'mistral', 'anthropic']:
        engine_data = [d['violations'] for d in data if d['engine'] == engine]
        if engine_data:
            engine_files_with_violations = sum(1 for v in engine_data if v > 0)
            engine_stats[engine] = {
                'mean': np.mean(engine_data),
                'sd': np.std(engine_data),
                'files': len(engine_data),
                'files_with_violations': engine_files_with_violations,
                'pct_with_violations': engine_files_with_violations / len(engine_data) * 100
            }
            print(f"{engine:<15} {len(engine_data):<8} {np.mean(engine_data):.2f} ± {np.std(engine_data):.2f}      {engine_files_with_violations}/{len(engine_data)} ({engine_files_with_violations/len(engine_data)*100:.1f}%)")

    # Statistical test: One-sample t-test against H0: mean = 0
    t_stat, p_value = stats.ttest_1samp(violations, 0)

    print(f"\n### Statistical Test: One-sample t-test")
    print(f"H0: Mean violations = 0 (no people-pleasing bias)")
    print(f"H1: Mean violations > 0 (people-pleasing bias exists)")
    print(f"t-statistic: {t_stat:.3f}")
    print(f"p-value: {p_value:.6f} (one-tailed: {p_value/2:.6f})")

    if p_value/2 < 0.001:
        print(f"✅ RESULT: STRONG EVIDENCE for people-pleasing bias (p < 0.001)")
    elif p_value/2 < 0.05:
        print(f"✅ RESULT: SIGNIFICANT EVIDENCE for people-pleasing bias (p < 0.05)")
    else:
        print(f"❌ RESULT: INSUFFICIENT EVIDENCE for people-pleasing bias")

    # ANOVA: Test if engines differ significantly
    engine_groups = [[d['violations'] for d in data if d['engine'] == e] for e in ['openai', 'google', 'mistral']]
    f_stat, p_anova = stats.f_oneway(*engine_groups)

    print(f"\n### Engine Comparison: One-way ANOVA")
    print(f"H0: All engines have same mean violations")
    print(f"H1: At least one engine differs")
    print(f"F-statistic: {f_stat:.3f}")
    print(f"p-value: {p_anova:.6f}")

    if p_anova < 0.05:
        print(f"✅ RESULT: Engines differ significantly (p < 0.05)")
    else:
        print(f"❌ RESULT: No significant difference between engines")

    return {
        'overall_mean': np.mean(violations),
        'overall_sd': np.std(violations),
        't_stat': t_stat,
        'p_value': p_value,
        'engine_stats': engine_stats,
        'anova_f': f_stat,
        'anova_p': p_anova
    }

def hypothesis_2_induced_errors(data):
    """
    H2: Induced errors and hallucinations

    Prediction: If LLMs introduce errors, violation rate should vary by:
    - Product complexity (crypto > smartphone > supplement)
    - Material type (FAQ > blog > digital_ad)
    """
    print("\n" + "="*80)
    print("HYPOTHESIS 2: INDUCED ERRORS AND HALLUCINATIONS")
    print("="*80)
    print("\nResearch Question: How frequently do LLMs introduce factual inaccuracies?")

    # By product
    print(f"\n### By Product (Regulatory Domain)")
    print(f"{'Product':<30} {'Files':<8} {'Mean Violations':<18} {'Median'}")
    print("-" * 80)

    product_stats = {}
    for product in ['cryptocurrency_corecoin', 'smartphone_mid', 'supplement_melatonin']:
        product_data = [d['violations'] for d in data if d['product'] == product]
        if product_data:
            product_stats[product] = {
                'mean': np.mean(product_data),
                'median': np.median(product_data),
                'sd': np.std(product_data),
                'files': len(product_data)
            }
            print(f"{product:<30} {len(product_data):<8} {np.mean(product_data):.2f} ± {np.std(product_data):.2f}      {np.median(product_data):.1f}")

    # By material type
    print(f"\n### By Material Type (Content Format)")
    print(f"{'Material':<30} {'Files':<8} {'Mean Violations':<18} {'Median'}")
    print("-" * 80)

    material_stats = {}
    for material in ['digital_ad', 'faq']:
        material_data = [d['violations'] for d in data if d['material'] == material]
        if material_data:
            material_stats[material] = {
                'mean': np.mean(material_data),
                'median': np.median(material_data),
                'sd': np.std(material_data),
                'files': len(material_data)
            }
            print(f"{material:<30} {len(material_data):<8} {np.mean(material_data):.2f} ± {np.std(material_data):.2f}      {np.median(material_data):.1f}")

    # Statistical test: Product comparison
    product_groups = [[d['violations'] for d in data if d['product'] == p]
                      for p in ['cryptocurrency_corecoin', 'smartphone_mid', 'supplement_melatonin']]
    f_product, p_product = stats.f_oneway(*product_groups)

    print(f"\n### Product Comparison: One-way ANOVA")
    print(f"H0: All products have same mean violations")
    print(f"H1: At least one product differs")
    print(f"F-statistic: {f_product:.3f}")
    print(f"p-value: {p_product:.6f}")

    if p_product < 0.05:
        print(f"✅ RESULT: Products differ significantly (p < 0.05)")
    else:
        print(f"❌ RESULT: No significant difference between products")

    # Material comparison (t-test: FAQ vs digital_ad)
    faq_data = [d['violations'] for d in data if d['material'] == 'faq']
    ad_data = [d['violations'] for d in data if d['material'] == 'digital_ad']

    if faq_data and ad_data:
        t_material, p_material = stats.ttest_ind(faq_data, ad_data)

        print(f"\n### Material Comparison: Independent t-test (FAQ vs Digital Ad)")
        print(f"H0: FAQ and Digital Ad have same mean violations")
        print(f"H1: FAQ and Digital Ad differ")
        print(f"t-statistic: {t_material:.3f}")
        print(f"p-value: {p_material:.6f}")

        if p_material < 0.05:
            print(f"✅ RESULT: Materials differ significantly (p < 0.05)")
            if np.mean(faq_data) > np.mean(ad_data):
                print(f"   → FAQs have significantly MORE violations than Digital Ads")
            else:
                print(f"   → Digital Ads have significantly MORE violations than FAQs")
        else:
            print(f"❌ RESULT: No significant difference between materials")

    return {
        'product_stats': product_stats,
        'material_stats': material_stats,
        'anova_product_f': f_product,
        'anova_product_p': p_product,
        't_material': t_material if faq_data and ad_data else None,
        'p_material': p_material if faq_data and ad_data else None
    }

def hypothesis_3_temperature_effect(data):
    """
    H3: Temperature effect on hallucinations

    Prediction: Higher temperature → more creative → more violations
    """
    print("\n" + "="*80)
    print("HYPOTHESIS 3: TEMPERATURE EFFECT ON HALLUCINATIONS")
    print("="*80)
    print("\nResearch Question: Does higher creativity (temperature) increase violations?")

    print(f"\n### By Temperature")
    print(f"{'Temperature':<15} {'Files':<8} {'Mean Violations':<18} {'Median'}")
    print("-" * 70)

    # Note: All 54 files use temperature 0.6
    temp_unique = set(d['temperature'] for d in data)
    print(f"\nNOTE: All 54 files use temperature = {list(temp_unique)}")
    print(f"Cannot test temperature hypothesis with single temperature value.")
    print(f"\n⚠️  RESULT: INSUFFICIENT DATA - need files with temp 0.2 and 1.0")

    return {'note': 'All files use temp=0.6, cannot test hypothesis'}

def save_results(h1_results, h2_results, h3_results):
    """Save hypothesis test results to markdown."""
    output_file = PROJECT_ROOT / "results" / "HYPOTHESIS_TESTS_54_FILES.md"

    with open(output_file, 'w') as f:
        f.write("# Research Hypothesis Tests - 54 LLM-Generated Files\n\n")
        f.write("**Date**: 2026-03-22\n")
        f.write("**Dataset**: 54 completed LLM-generated marketing files\n")
        f.write("**Analysis**: Glass Box audit with ground truth YAMLs\n\n")

        f.write("---\n\n")

        f.write("## H1: People-Pleasing Bias\n\n")
        f.write(f"**Overall mean violations**: {h1_results['overall_mean']:.2f} ± {h1_results['overall_sd']:.2f}\n\n")
        f.write(f"**t-test against H0 (mean=0)**: t={h1_results['t_stat']:.3f}, p={h1_results['p_value']:.6f}\n\n")

        if h1_results['p_value']/2 < 0.001:
            f.write(f"**✅ CONCLUSION**: STRONG evidence for people-pleasing bias (p < 0.001)\n\n")
        elif h1_results['p_value']/2 < 0.05:
            f.write(f"**✅ CONCLUSION**: SIGNIFICANT evidence for people-pleasing bias (p < 0.05)\n\n")
        else:
            f.write(f"**❌ CONCLUSION**: INSUFFICIENT evidence for people-pleasing bias\n\n")

        f.write("### Engine Comparison\n\n")
        f.write("| Engine | Mean Violations | SD | Files with Violations |\n")
        f.write("|--------|-----------------|----|-----------------------|\n")
        for engine, stats_dict in h1_results['engine_stats'].items():
            f.write(f"| {engine} | {stats_dict['mean']:.2f} | {stats_dict['sd']:.2f} | {stats_dict['files_with_violations']}/{stats_dict['files']} ({stats_dict['pct_with_violations']:.1f}%) |\n")

        f.write(f"\n**ANOVA**: F={h1_results['anova_f']:.3f}, p={h1_results['anova_p']:.6f}\n\n")

        f.write("---\n\n")

        f.write("## H2: Induced Errors and Hallucinations\n\n")
        f.write("### Product Comparison\n\n")
        f.write("| Product | Mean Violations | Median | SD |\n")
        f.write("|---------|-----------------|--------|----|  \n")
        for product, stats_dict in h2_results['product_stats'].items():
            f.write(f"| {product} | {stats_dict['mean']:.2f} | {stats_dict['median']:.1f} | {stats_dict['sd']:.2f} |\n")

        f.write(f"\n**ANOVA**: F={h2_results['anova_product_f']:.3f}, p={h2_results['anova_product_p']:.6f}\n\n")

        if h2_results['anova_product_p'] < 0.05:
            f.write("**✅ CONCLUSION**: Products differ significantly in violation rates\n\n")
        else:
            f.write("**❌ CONCLUSION**: No significant difference between products\n\n")

        f.write("### Material Type Comparison\n\n")
        f.write("| Material | Mean Violations | Median | SD |\n")
        f.write("|----------|-----------------|--------|----|  \n")
        for material, stats_dict in h2_results['material_stats'].items():
            f.write(f"| {material} | {stats_dict['mean']:.2f} | {stats_dict['median']:.1f} | {stats_dict['sd']:.2f} |\n")

        if h2_results['t_material'] is not None:
            f.write(f"\n**t-test (FAQ vs Digital Ad)**: t={h2_results['t_material']:.3f}, p={h2_results['p_material']:.6f}\n\n")

            if h2_results['p_material'] < 0.05:
                f.write("**✅ CONCLUSION**: FAQs have significantly MORE violations than Digital Ads\n\n")
            else:
                f.write("**❌ CONCLUSION**: No significant difference between materials\n\n")

        f.write("---\n\n")

        f.write("## H3: Temperature Effect\n\n")
        f.write("**⚠️ INSUFFICIENT DATA**: All 54 files use temperature=0.6\n\n")
        f.write("Cannot test hypothesis without files at temp=0.2 and temp=1.0\n\n")

    print(f"\n\n✅ Hypothesis test results saved to: {output_file}")

if __name__ == "__main__":
    metadata = load_experiments_metadata()
    violations = load_violations()
    data = calculate_violations_per_file(violations, metadata)

    print("="*80)
    print("RESEARCH HYPOTHESIS TESTING - 54 LLM-GENERATED FILES")
    print("="*80)
    print(f"\nDataset: {len(data)} files")
    print(f"Total violations: {sum(d['violations'] for d in data)}")

    # Test hypotheses
    h1_results = hypothesis_1_people_pleasing(data)
    h2_results = hypothesis_2_induced_errors(data)
    h3_results = hypothesis_3_temperature_effect(data)

    # Save results
    save_results(h1_results, h2_results, h3_results)

    print("\n" + "="*80)
    print("HYPOTHESIS TESTING COMPLETE")
    print("="*80)
