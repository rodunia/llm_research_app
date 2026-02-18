#!/usr/bin/env python3
"""Collect all FAQ marketing outputs for each product into separate text files."""

import csv
from pathlib import Path


def collect_faq_outputs_for_product(product_id, output_file):
    """Collect all FAQ outputs for a specific product."""

    # Read experiments.csv to find FAQ runs for this product
    faq_runs = []
    with open('results/experiments.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if (row.get('product_id') == product_id and
                row.get('material_type') == 'faq.j2' and
                row.get('status') == 'completed' and
                row.get('output_path')):
                faq_runs.append({
                    'run_id': row['run_id'],
                    'engine': row['engine'],
                    'temperature': row.get('temperature_label', 'unknown'),
                    'output_path': row['output_path']
                })

    if not faq_runs:
        return 0

    # Write all outputs to a single file
    with open(output_file, 'w') as out:
        out.write("=" * 80 + "\n")
        out.write(f"All FAQ Marketing Outputs - {product_id}\n")
        out.write("=" * 80 + "\n")
        out.write(f"Total runs: {len(faq_runs)}\n")
        out.write("=" * 80 + "\n\n")

        for i, run in enumerate(faq_runs, 1):
            # Read the output file
            output_path = Path(run['output_path'])

            if not output_path.exists():
                continue

            with open(output_path, 'r') as f:
                content = f.read()

            # Write separator and metadata
            out.write("\n" + "=" * 80 + "\n")
            out.write(f"FAQ #{i} of {len(faq_runs)}\n")
            out.write("=" * 80 + "\n")
            out.write(f"Run ID:      {run['run_id']}\n")
            out.write(f"Engine:      {run['engine']}\n")
            out.write(f"Temperature: {run['temperature']}\n")
            out.write(f"Output Path: {run['output_path']}\n")
            out.write("-" * 80 + "\n\n")

            # Write the actual FAQ content
            out.write(content)
            out.write("\n\n")

    return len(faq_runs)


def main():
    """Generate FAQ collections for all products."""

    products = [
        'smartphone_mid',
        'cryptocurrency_corecoin',
        'supplement_melatonin'
    ]

    output_dir = Path('docs/faq_outputs')
    output_dir.mkdir(exist_ok=True)

    print("=" * 80)
    print("Collecting All FAQ Marketing Outputs")
    print("=" * 80)

    for product_id in products:
        print(f"\n[{product_id}]")

        output_file = output_dir / f"{product_id}_all_faq_outputs.txt"
        count = collect_faq_outputs_for_product(product_id, output_file)

        if count > 0:
            print(f"  ✓ Collected {count} FAQ outputs")
            print(f"  ✓ Saved to: {output_file}")
        else:
            print(f"  ✗ No completed FAQ runs found")

    print("\n" + "=" * 80)
    print(f"All FAQ collections saved to: {output_dir}/")
    print("=" * 80)


if __name__ == '__main__':
    main()
