#!/usr/bin/env python3
"""Run DeBERTa verification on all FAQ outputs for all products."""

import sys
import csv
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.premise_builder import build_premise, load_product_yaml
from analysis.deberta_nli import DebertaNliVerifier
import json


def extract_faq_qa_pairs(faq_text):
    """Extract Q&A pairs from FAQ text.

    Returns list of (question, answer) tuples.
    """
    pairs = []
    lines = faq_text.split('\n')

    current_q = None
    current_a = []

    for line in lines:
        line = line.strip()

        # Skip empty lines and separators
        if not line or line.startswith('===') or line.startswith('---'):
            continue

        # Skip disclaimer section
        if 'Disclaimer' in line or 'DISCLAIMER' in line:
            break

        # Detect question patterns
        if (line.startswith('Q:') or line.startswith('**Q:') or
            line.startswith('Q1:') or line.startswith('**Q1:') or
            line.startswith('**What') or line.startswith('**How') or
            line.startswith('**Is') or line.startswith('**Are') or
            line.startswith('**Does') or line.startswith('**Can')):

            # Save previous Q&A if exists
            if current_q and current_a:
                pairs.append((current_q, ' '.join(current_a)))

            # Start new question
            current_q = line.replace('**', '').replace('Q:', '').replace('Q1:', '').replace('Q2:', '').replace('Q3:', '').replace('Q4:', '').replace('Q5:', '').strip()
            current_a = []

        # Detect answer patterns
        elif (line.startswith('A:') or line.startswith('**A:') or
              line.startswith('A1:') or line.startswith('**A1:')):
            current_a.append(line.replace('**', '').replace('A:', '').replace('A1:', '').replace('A2:', '').replace('A3:', '').replace('A4:', '').replace('A5:', '').strip())

        # Continue answer
        elif current_q and not line.startswith('#'):
            current_a.append(line)

    # Add last Q&A
    if current_q and current_a:
        pairs.append((current_q, ' '.join(current_a)))

    return pairs


def verify_product_faqs(product_id):
    """Verify all FAQ outputs for a product using DeBERTa."""

    print(f"\n{'='*80}")
    print(f"Verifying FAQs for: {product_id}")
    print(f"{'='*80}")

    # Load product YAML and build premise
    product_yaml = load_product_yaml(product_id, products_dir=Path('products'))
    premise = build_premise(product_yaml)

    print(f"Loaded product YAML: {product_yaml.get('name', 'Unknown')}")
    print(f"Premise length: {len(premise)} characters\n")

    # Initialize DeBERTa verifier
    print("Initializing DeBERTa verifier...")
    verifier = DebertaNliVerifier(
        model_name="cross-encoder/nli-deberta-v3-small",
        device="cpu"
    )
    print("Verifier ready\n")

    # Read experiments.csv to find FAQ runs
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

    print(f"Found {len(faq_runs)} FAQ runs to verify")

    # Collect all claims from all FAQs
    all_claims = []

    for run in faq_runs:
        output_path = Path(run['output_path'])

        if not output_path.exists():
            continue

        with open(output_path, 'r') as f:
            faq_content = f.read()

        # Extract Q&A pairs
        qa_pairs = extract_faq_qa_pairs(faq_content)

        # Add each answer as a claim to verify
        for question, answer in qa_pairs:
            all_claims.append({
                'run_id': run['run_id'],
                'engine': run['engine'],
                'temperature': run['temperature'],
                'question': question,
                'answer': answer,
                'claim_text': answer  # Use answer as the claim to verify
            })

    print(f"Extracted {len(all_claims)} Q&A answers to verify\n")

    if len(all_claims) == 0:
        print("No claims to verify. Exiting.")
        return

    # Verify all claims
    print("Verifying claims...")
    results = []

    for i, claim in enumerate(all_claims, 1):
        if i % 50 == 0:
            print(f"  Processed {i}/{len(all_claims)} claims...")

        # Run NLI
        nli_result = verifier.verify(premise, claim['claim_text'])

        # Store result
        result = {
            'claim_id': i,
            'run_id': claim['run_id'],
            'engine': claim['engine'],
            'temperature': claim['temperature'],
            'question': claim['question'],
            'answer': claim['answer'],
            'deberta_label': nli_result['label'],
            'deberta_probs': nli_result['probs'],
            'deberta_model': nli_result['model']
        }

        results.append(result)

    # Save results
    output_file = f"results/{product_id}_faq_deberta_verification.jsonl"
    with open(output_file, 'w') as f:
        for result in results:
            f.write(json.dumps(result) + '\n')

    print(f"\n✅ Verification complete!")
    print(f"Results saved to: {output_file}")

    # Print summary
    label_counts = {}
    for result in results:
        label = result['deberta_label']
        label_counts[label] = label_counts.get(label, 0) + 1

    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Total claims verified: {len(results)}")
    print(f"\nLabel distribution:")
    for label in ['entailment', 'neutral', 'contradiction']:
        count = label_counts.get(label, 0)
        pct = (count / len(results) * 100) if results else 0
        print(f"  {label:15s}: {count:4d} ({pct:5.1f}%)")

    return results


def main():
    """Run DeBERTa verification on all products' FAQ outputs."""

    products = [
        'supplement_melatonin',
        'smartphone_mid',
        'cryptocurrency_corecoin'
    ]

    print("=" * 80)
    print("DeBERTa Verification - All FAQ Outputs")
    print("=" * 80)

    all_results = {}

    for product_id in products:
        results = verify_product_faqs(product_id)
        all_results[product_id] = results

    print("\n" + "=" * 80)
    print("ALL VERIFICATIONS COMPLETE")
    print("=" * 80)
    print(f"\nResults saved in results/ directory:")
    for product_id in products:
        print(f"  - {product_id}_faq_deberta_verification.jsonl")


if __name__ == '__main__':
    main()
