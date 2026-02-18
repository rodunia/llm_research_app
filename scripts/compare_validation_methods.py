#!/usr/bin/env python3
"""
Comparison Analysis: LLM Direct vs Glass Box Audit

Systematically compares two validation approaches:
1. LLM Direct: Single-stage GPT-4o-mini validation at temp=0
2. Glass Box: Two-stage (GPT-4o-mini extraction + DeBERTa NLI validation)

Analyzes detection rates, false positives, and error type performance.
"""

import csv
import sys
from pathlib import Path

# Ground truth detection results from PILOT_STUDY_VALIDATION_REPORT.md
GLASS_BOX_RESULTS = {
    # Smartphone: 10/10 (100%)
    'user_smartphone_1': True,   # Display 6.5" (should be 6.3")
    'user_smartphone_2': True,   # Camera 48 MP (should be 50 MP)
    'user_smartphone_3': True,   # 1 TB storage option
    'user_smartphone_4': True,   # 16 GB RAM option
    'user_smartphone_5': True,   # Wi-Fi 7 support
    'user_smartphone_6': True,   # Wireless charging support
    'user_smartphone_7': True,   # Hourly antivirus scanning
    'user_smartphone_8': True,   # Offline AI video rendering
    'user_smartphone_9': True,   # 60W charging (max 30-45W)
    'user_smartphone_10': True,  # External SSD via SIM tray

    # Melatonin: 10/10 (100%)
    'user_melatonin_1': True,    # Dosage error (5mg vs 3mg)
    'user_melatonin_2': True,    # Bottle count (100→120)
    'user_melatonin_3': True,    # Vegan + fish-derived
    'user_melatonin_4': True,    # Wheat traces despite 0mg gluten
    'user_melatonin_5': True,    # Lead limit decimal misplacement
    'user_melatonin_6': True,    # Storage at 0°C
    'user_melatonin_7': True,    # Take every 2 hours
    'user_melatonin_8': True,    # FDA approval claim
    'user_melatonin_9': True,    # Avoid if over 18 (age reversal)
    'user_melatonin_10': True,   # Permanent drowsiness

    # CoreCoin: 6/10 (60%)
    'user_corecoin_1': False,    # Block time 4s (should be ~5s)
    'user_corecoin_2': True,     # Non-staking light validators
    'user_corecoin_3': False,    # Regional trading pauses
    'user_corecoin_4': False,    # Automatic key sharding
    'user_corecoin_5': True,     # Gas-free smart contracts
    'user_corecoin_6': True,     # Auto-pass without quorum
    'user_corecoin_7': True,     # RPC simulate cross-chain
    'user_corecoin_8': True,     # Unstaking reduces rewards
    'user_corecoin_9': True,     # Inactivity locks governance
    'user_corecoin_10': False,   # Region-based staking tiers
}

# Ground truth error types
ERROR_TYPES = {
    # Numerical errors
    'user_smartphone_1': 'numerical',
    'user_smartphone_2': 'numerical',
    'user_smartphone_9': 'numerical',
    'user_melatonin_1': 'numerical',
    'user_melatonin_5': 'numerical',
    'user_corecoin_1': 'numerical',

    # Feature hallucinations
    'user_smartphone_3': 'feature_hallucination',
    'user_smartphone_4': 'feature_hallucination',
    'user_smartphone_5': 'feature_hallucination',
    'user_smartphone_6': 'feature_hallucination',
    'user_smartphone_8': 'feature_hallucination',
    'user_smartphone_10': 'feature_hallucination',
    'user_melatonin_7': 'feature_hallucination',
    'user_corecoin_4': 'feature_hallucination',
    'user_corecoin_5': 'feature_hallucination',
    'user_corecoin_7': 'feature_hallucination',

    # Logical/domain errors
    'user_smartphone_7': 'logical',
    'user_melatonin_3': 'logical',
    'user_melatonin_4': 'logical',
    'user_melatonin_6': 'logical',
    'user_corecoin_2': 'logical',
    'user_corecoin_3': 'logical',
    'user_corecoin_6': 'logical',
    'user_corecoin_9': 'logical',

    # Factual errors
    'user_melatonin_2': 'factual',
    'user_melatonin_8': 'factual',
    'user_melatonin_9': 'factual',
    'user_melatonin_10': 'factual',
    'user_corecoin_8': 'factual',
    'user_corecoin_10': 'factual',
}


def load_llm_direct_results():
    """Load LLM Direct validation results from CSV"""
    results = {}
    csv_path = 'results/llm_direct_validation_results.csv'

    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            run_id = row['run_id']
            errors_found = row['errors_found'] == 'True'
            results[run_id] = errors_found

    return results


def compare_methods():
    """Compare LLM Direct vs Glass Box detection results"""

    llm_results = load_llm_direct_results()

    # Initialize comparison data
    comparison = []

    for run_id in sorted(GLASS_BOX_RESULTS.keys()):
        glass_box_detected = GLASS_BOX_RESULTS[run_id]
        llm_direct_detected = llm_results.get(run_id, False)
        error_type = ERROR_TYPES.get(run_id, 'unknown')

        # Determine product
        if 'smartphone' in run_id:
            product = 'smartphone'
        elif 'melatonin' in run_id:
            product = 'melatonin'
        elif 'corecoin' in run_id:
            product = 'corecoin'
        else:
            product = 'unknown'

        # Agreement analysis
        if glass_box_detected and llm_direct_detected:
            agreement = 'both_detected'
        elif not glass_box_detected and not llm_direct_detected:
            agreement = 'both_missed'
        elif glass_box_detected and not llm_direct_detected:
            agreement = 'glassbox_only'
        else:  # llm_direct_detected and not glass_box_detected
            agreement = 'llm_only'

        comparison.append({
            'run_id': run_id,
            'product': product,
            'error_type': error_type,
            'glass_box_detected': glass_box_detected,
            'llm_direct_detected': llm_direct_detected,
            'agreement': agreement
        })

    return comparison


def calculate_metrics(comparison):
    """Calculate detection rates and agreement metrics"""

    # Overall metrics
    total = len(comparison)
    glass_box_total = sum(1 for row in comparison if row['glass_box_detected'])
    llm_direct_total = sum(1 for row in comparison if row['llm_direct_detected'])
    both_detected = sum(1 for row in comparison if row['agreement'] == 'both_detected')
    both_missed = sum(1 for row in comparison if row['agreement'] == 'both_missed')

    metrics = {
        'overall': {
            'total_errors': total,
            'glass_box_detected': glass_box_total,
            'llm_direct_detected': llm_direct_total,
            'glass_box_rate': glass_box_total / total * 100,
            'llm_direct_rate': llm_direct_total / total * 100,
            'both_detected': both_detected,
            'both_missed': both_missed,
            'agreement_rate': (both_detected + both_missed) / total * 100
        }
    }

    # By product
    for product in ['smartphone', 'melatonin', 'corecoin']:
        product_data = [row for row in comparison if row['product'] == product]
        if product_data:
            p_total = len(product_data)
            p_glass = sum(1 for row in product_data if row['glass_box_detected'])
            p_llm = sum(1 for row in product_data if row['llm_direct_detected'])

            metrics[product] = {
                'total': p_total,
                'glass_box_detected': p_glass,
                'llm_direct_detected': p_llm,
                'glass_box_rate': p_glass / p_total * 100,
                'llm_direct_rate': p_llm / p_total * 100
            }

    # By error type
    for error_type in ['numerical', 'feature_hallucination', 'logical', 'factual']:
        type_data = [row for row in comparison if row['error_type'] == error_type]
        if type_data:
            t_total = len(type_data)
            t_glass = sum(1 for row in type_data if row['glass_box_detected'])
            t_llm = sum(1 for row in type_data if row['llm_direct_detected'])

            metrics[error_type] = {
                'total': t_total,
                'glass_box_detected': t_glass,
                'llm_direct_detected': t_llm,
                'glass_box_rate': t_glass / t_total * 100,
                'llm_direct_rate': t_llm / t_total * 100
            }

    return metrics


def print_summary(comparison, metrics):
    """Print comparison summary to console"""

    print("=" * 80)
    print("VALIDATION METHOD COMPARISON: LLM Direct vs Glass Box Audit")
    print("=" * 80)
    print()

    # Overall detection rates
    print("## Overall Detection Rates")
    print("-" * 80)
    overall = metrics['overall']
    print(f"Total Errors: {overall['total_errors']}")
    print(f"Glass Box Detected: {overall['glass_box_detected']}/{overall['total_errors']} ({overall['glass_box_rate']:.1f}%)")
    print(f"LLM Direct Detected: {overall['llm_direct_detected']}/{overall['total_errors']} ({overall['llm_direct_rate']:.1f}%)")
    print(f"Both Detected: {overall['both_detected']}")
    print(f"Both Missed: {overall['both_missed']}")
    print(f"Agreement Rate: {overall['agreement_rate']:.1f}%")
    print()

    # By product
    print("## Detection by Product")
    print("-" * 80)
    for product in ['smartphone', 'melatonin', 'corecoin']:
        if product in metrics:
            m = metrics[product]
            print(f"{product.capitalize()}:")
            print(f"  Glass Box: {m['glass_box_detected']}/{m['total']} ({m['glass_box_rate']:.1f}%)")
            print(f"  LLM Direct: {m['llm_direct_detected']}/{m['total']} ({m['llm_direct_rate']:.1f}%)")
            print()

    # By error type
    print("## Detection by Error Type")
    print("-" * 80)
    for error_type in ['numerical', 'feature_hallucination', 'logical', 'factual']:
        if error_type in metrics:
            m = metrics[error_type]
            print(f"{error_type.replace('_', ' ').title()}:")
            print(f"  Glass Box: {m['glass_box_detected']}/{m['total']} ({m['glass_box_rate']:.1f}%)")
            print(f"  LLM Direct: {m['llm_direct_detected']}/{m['total']} ({m['llm_direct_rate']:.1f}%)")
            print()

    # Disagreement analysis
    print("## Disagreement Analysis")
    print("-" * 80)
    glassbox_only = [row for row in comparison if row['agreement'] == 'glassbox_only']
    llm_only = [row for row in comparison if row['agreement'] == 'llm_only']

    print(f"Glass Box detected but LLM Direct missed: {len(glassbox_only)}")
    for row in glassbox_only:
        print(f"  - {row['run_id']} ({row['error_type']})")
    print()

    print(f"LLM Direct detected but Glass Box missed: {len(llm_only)}")
    for row in llm_only:
        print(f"  - {row['run_id']} ({row['error_type']})")
    print()


def save_results(comparison, metrics):
    """Save comparison results to CSV"""

    # Save detailed comparison
    output_file = 'results/validation_method_comparison.csv'
    with open(output_file, 'w', newline='') as f:
        fieldnames = ['run_id', 'product', 'error_type', 'glass_box_detected',
                     'llm_direct_detected', 'agreement']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(comparison)

    print(f"Detailed comparison saved to: {output_file}")

    # Save summary metrics
    summary_file = 'results/validation_method_summary.csv'
    with open(summary_file, 'w', newline='') as f:
        fieldnames = ['category', 'subcategory', 'total', 'glass_box_detected',
                     'llm_direct_detected', 'glass_box_rate', 'llm_direct_rate']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        # Overall
        m = metrics['overall']
        writer.writerow({
            'category': 'overall',
            'subcategory': 'all',
            'total': m['total_errors'],
            'glass_box_detected': m['glass_box_detected'],
            'llm_direct_detected': m['llm_direct_detected'],
            'glass_box_rate': round(m['glass_box_rate'], 1),
            'llm_direct_rate': round(m['llm_direct_rate'], 1)
        })

        # By product
        for product in ['smartphone', 'melatonin', 'corecoin']:
            if product in metrics:
                m = metrics[product]
                writer.writerow({
                    'category': 'product',
                    'subcategory': product,
                    'total': m['total'],
                    'glass_box_detected': m['glass_box_detected'],
                    'llm_direct_detected': m['llm_direct_detected'],
                    'glass_box_rate': round(m['glass_box_rate'], 1),
                    'llm_direct_rate': round(m['llm_direct_rate'], 1)
                })

        # By error type
        for error_type in ['numerical', 'feature_hallucination', 'logical', 'factual']:
            if error_type in metrics:
                m = metrics[error_type]
                writer.writerow({
                    'category': 'error_type',
                    'subcategory': error_type,
                    'total': m['total'],
                    'glass_box_detected': m['glass_box_detected'],
                    'llm_direct_detected': m['llm_direct_detected'],
                    'glass_box_rate': round(m['glass_box_rate'], 1),
                    'llm_direct_rate': round(m['llm_direct_rate'], 1)
                })

    print(f"Summary metrics saved to: {summary_file}")


def main():
    """Run comparison analysis"""

    comparison = compare_methods()
    metrics = calculate_metrics(comparison)
    print_summary(comparison, metrics)
    save_results(comparison, metrics)

    print()
    print("=" * 80)
    print("COMPARISON COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
