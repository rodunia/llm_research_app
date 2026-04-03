"""
Analyze Glass Box results for 54 LLM-generated marketing files.
"""

import csv
from pathlib import Path
from collections import defaultdict, Counter

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

def analyze_audit_results():
    """Analyze final_audit_results.csv."""

    metadata = load_experiments_metadata()

    # Data structures
    violations_by_file = defaultdict(list)
    stats = {
        'total_files': 0,
        'files_with_violations': 0,
        'files_clean': 0,
        'total_violations': 0,
        'by_product': defaultdict(lambda: {'violations': 0, 'files': set()}),
        'by_engine': defaultdict(lambda: {'violations': 0, 'files': set()}),
        'by_material': defaultdict(lambda: {'violations': 0, 'files': set()}),
        'by_temperature': defaultdict(lambda: {'violations': 0, 'files': set()}),
        'violation_types': Counter()
    }

    # Read audit results
    with open(RESULTS_CSV, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            filename = row['Filename'].replace('.txt', '')
            status = row['Status']

            if status == 'FAIL':
                violations_by_file[filename].append({
                    'rule': row['Violated_Rule'],
                    'claim': row['Extracted_Claim'],
                    'confidence': float(row['Confidence_Score'])
                })

    # Calculate stats
    all_files = set(metadata.keys())
    stats['total_files'] = len(all_files)
    stats['files_with_violations'] = len(violations_by_file)
    stats['files_clean'] = stats['total_files'] - stats['files_with_violations']

    for run_id in all_files:
        violations = violations_by_file.get(run_id, [])
        num_violations = len(violations)
        stats['total_violations'] += num_violations

        if run_id in metadata:
            meta = metadata[run_id]
            product = meta['product_id']
            engine = meta['engine']
            material = meta['material_type']
            temp = meta['temperature']

            # Aggregate stats
            stats['by_product'][product]['violations'] += num_violations
            stats['by_product'][product]['files'].add(run_id)

            stats['by_engine'][engine]['violations'] += num_violations
            stats['by_engine'][engine]['files'].add(run_id)

            stats['by_material'][material]['violations'] += num_violations
            stats['by_material'][material]['files'].add(run_id)

            stats['by_temperature'][temp]['violations'] += num_violations
            stats['by_temperature'][temp]['files'].add(run_id)

    return stats, violations_by_file, metadata


if __name__ == "__main__":
    stats, violations_by_file, metadata = analyze_audit_results()

    print("=" * 80)
    print("GLASS BOX AUDIT RESULTS: 54 LLM-GENERATED MARKETING FILES")
    print("=" * 80)

    print(f"\n## Overall Summary")
    print(f"Total files analyzed: {stats['total_files']}")
    print(f"Files with violations: {stats['files_with_violations']} ({stats['files_with_violations']/stats['total_files']*100:.1f}%)")
    print(f"Files clean (PASS): {stats['files_clean']} ({stats['files_clean']/stats['total_files']*100:.1f}%)")
    print(f"Total violations: {stats['total_violations']}")
    print(f"Average violations per file: {stats['total_violations']/stats['total_files']:.1f}")

    print(f"\n## By Product")
    print(f"{'Product':<30} {'Files':<8} {'Violations':<12} {'Avg/File'}")
    print("-" * 70)
    for product, data in sorted(stats['by_product'].items()):
        num_files = len(data['files'])
        avg = data['violations'] / num_files if num_files > 0 else 0
        print(f"{product:<30} {num_files:<8} {data['violations']:<12} {avg:.1f}")

    print(f"\n## By Engine (LLM Provider)")
    print(f"{'Engine':<30} {'Files':<8} {'Violations':<12} {'Avg/File'}")
    print("-" * 70)
    for engine, data in sorted(stats['by_engine'].items()):
        num_files = len(data['files'])
        avg = data['violations'] / num_files if num_files > 0 else 0
        print(f"{engine:<30} {num_files:<8} {data['violations']:<12} {avg:.1f}")

    print(f"\n## By Material Type")
    print(f"{'Material':<30} {'Files':<8} {'Violations':<12} {'Avg/File'}")
    print("-" * 70)
    for material, data in sorted(stats['by_material'].items()):
        num_files = len(data['files'])
        avg = data['violations'] / num_files if num_files > 0 else 0
        print(f"{material:<30} {num_files:<8} {data['violations']:<12} {avg:.1f}")

    print(f"\n## By Temperature")
    print(f"{'Temperature':<30} {'Files':<8} {'Violations':<12} {'Avg/File'}")
    print("-" * 70)
    for temp, data in sorted(stats['by_temperature'].items()):
        num_files = len(data['files'])
        avg = data['violations'] / num_files if num_files > 0 else 0
        print(f"{temp:<30} {num_files:<8} {data['violations']:<12} {avg:.1f}")

    # Top violating files
    print(f"\n## Top 10 Files by Violation Count")
    print(f"{'Run ID (first 12 chars)':<25} {'Product':<25} {'Engine':<12} {'Temp':<6} {'Violations'}")
    print("-" * 90)
    sorted_files = sorted(violations_by_file.items(), key=lambda x: len(x[1]), reverse=True)[:10]
    for run_id, violations in sorted_files:
        meta = metadata.get(run_id, {})
        product = meta.get('product_id', 'unknown')[:24]
        engine = meta.get('engine', 'unknown')
        temp = meta.get('temperature', 0)
        print(f"{run_id[:24]:<25} {product:<25} {engine:<12} {temp:<6.1f} {len(violations)}")

    # Clean files
    clean_files = [run_id for run_id in metadata.keys() if run_id not in violations_by_file]
    if clean_files:
        print(f"\n## Clean Files (0 Violations)")
        print(f"{'Run ID (first 12 chars)':<25} {'Product':<25} {'Engine':<12} {'Material':<15}")
        print("-" * 90)
        for run_id in clean_files:
            meta = metadata[run_id]
            product = meta['product_id'][:24]
            engine = meta['engine']
            material = meta['material_type'][:14]
            print(f"{run_id[:24]:<25} {product:<25} {engine:<12} {material:<15}")

    print(f"\n{'='*80}")
    print(f"Analysis complete!")
    print(f"{'='*80}")
