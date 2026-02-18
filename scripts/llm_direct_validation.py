#!/usr/bin/env python3
"""
LLM Direct Validation: Single-stage error detection using GPT-4o-mini

Compares marketing text directly against product YAML specifications
to identify factual errors without the two-stage Glass Box approach.
"""

import os
import sys
import csv
import yaml
import time
from openai import OpenAI
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ENGINE_MODELS

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

PRODUCT_YAMLS = {
    "smartphone": "products/smartphone_mid.yaml",
    "melatonin": "products/supplement_melatonin.yaml",
    "corecoin": "products/cryptocurrency_corecoin.yaml",
}


def load_yaml_specs(product_type):
    """Load product YAML specifications"""
    yaml_path = PRODUCT_YAMLS[product_type]
    with open(yaml_path, 'r') as f:
        return yaml.safe_load(f)


def load_marketing_text(run_id):
    """Load marketing text from outputs directory using experiments.csv"""
    # Read experiments.csv to get output_path
    with open('results/experiments.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['run_id'] == run_id:
                output_path = row['output_path']
                with open(output_path, 'r') as text_file:
                    return text_file.read()

    raise ValueError(f"run_id not found in experiments.csv: {run_id}")


def format_yaml_for_prompt(specs):
    """Format YAML specs into readable text for LLM prompt"""
    sections = []

    # Specifications
    if 'specifications' in specs:
        sections.append("## Technical Specifications:")
        for key, value in specs['specifications'].items():
            sections.append(f"- {key}: {value}")

    # Authorized claims
    if 'authorized_claims' in specs:
        sections.append("\n## Authorized Marketing Claims:")
        for claim in specs['authorized_claims']:
            sections.append(f"- {claim}")

    # Prohibited claims
    if 'prohibited_claims' in specs:
        sections.append("\n## Prohibited Claims (Must NOT appear):")
        for claim in specs['prohibited_claims']:
            sections.append(f"- {claim}")

    # Clarifications
    if 'clarifications' in specs:
        sections.append("\n## Important Clarifications:")
        if isinstance(specs['clarifications'], list):
            for clarification in specs['clarifications']:
                sections.append(f"- {clarification}")
        elif isinstance(specs['clarifications'], dict):
            for key, values in specs['clarifications'].items():
                sections.append(f"\n{key}:")
                for value in values:
                    sections.append(f"  - {value}")

    return "\n".join(sections)


def validate_with_llm(marketing_text, specs_text, run_id):
    """
    Use GPT-4o-mini to directly identify factual errors by comparing
    marketing text against product specifications.
    """

    prompt = f"""You are a fact-checking assistant. Your task is to identify any factual errors or contradictions in the marketing text below by comparing it against the official product specifications.

# Official Product Specifications:

{specs_text}

# Marketing Text to Verify:

{marketing_text}

# Instructions:

1. Carefully read the marketing text
2. Compare each factual claim against the official specifications
3. Identify any errors, including:
   - Numerical inaccuracies (wrong dosage, dimensions, specs)
   - Feature hallucinations (claiming features not in specs)
   - Logical contradictions (e.g., "vegan" but contains fish)
   - Prohibited claims that violate regulations
   - Factual inconsistencies with specifications

4. For each error found, provide:
   - The incorrect claim from the marketing text
   - What it should be according to specifications
   - Why this is an error
   - Your confidence level (High/Medium/Low)

5. If you find NO errors, clearly state "NO ERRORS FOUND"

# Your Analysis:
"""

    try:
        response = client.chat.completions.create(
            model=ENGINE_MODELS['openai'],  # gpt-4o-mini
            messages=[
                {"role": "system", "content": "You are a precise fact-checking assistant. Be thorough but only flag genuine factual errors."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=2000
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"Error validating {run_id}: {str(e)}")
        return f"ERROR: {str(e)}"


def parse_llm_response(response_text):
    """
    Parse LLM response to extract:
    - Whether any errors were found
    - List of errors detected
    - Confidence levels
    """

    if "NO ERRORS FOUND" in response_text.upper():
        return {
            'errors_found': False,
            'error_count': 0,
            'errors': [],
            'raw_response': response_text
        }

    # Simple heuristic: count bullet points or numbered items in response
    lines = response_text.split('\n')
    error_indicators = [
        line for line in lines
        if any(marker in line for marker in ['- ', '1.', '2.', '3.', '* ', 'Error:', 'Incorrect:'])
    ]

    return {
        'errors_found': len(error_indicators) > 0,
        'error_count': len(error_indicators),
        'errors': error_indicators,
        'raw_response': response_text
    }


def main():
    """Run LLM Direct validation on all 30 pilot study files"""

    # Define the 30 files to test (only the ground truth error files)
    test_files = (
        [f"user_smartphone_{i}" for i in range(1, 11)] +
        [f"user_melatonin_{i}" for i in range(1, 11)] +
        [f"user_corecoin_{i}" for i in range(1, 11)]
    )

    results = []

    print("=" * 80)
    print("LLM DIRECT VALIDATION - GPT-4o-mini @ temp=0")
    print("=" * 80)
    print(f"Testing {len(test_files)} files with intentional errors")
    print()

    for i, run_id in enumerate(test_files, 1):
        print(f"[{i}/{len(test_files)}] Processing {run_id}...")

        # Determine product type
        if 'smartphone' in run_id:
            product_type = 'smartphone'
        elif 'melatonin' in run_id:
            product_type = 'melatonin'
        elif 'corecoin' in run_id:
            product_type = 'corecoin'
        else:
            print(f"  ⚠️  Unknown product type for {run_id}, skipping")
            continue

        try:
            # Load data
            marketing_text = load_marketing_text(run_id)
            specs = load_yaml_specs(product_type)
            specs_text = format_yaml_for_prompt(specs)

            # Run LLM validation
            start_time = time.time()
            llm_response = validate_with_llm(marketing_text, specs_text, run_id)
            elapsed = time.time() - start_time

            # Parse response
            parsed = parse_llm_response(llm_response)

            # Store result
            results.append({
                'run_id': run_id,
                'product_type': product_type,
                'errors_found': parsed['errors_found'],
                'error_count': parsed['error_count'],
                'elapsed_time': round(elapsed, 2),
                'raw_response': parsed['raw_response']
            })

            # Print summary
            if parsed['errors_found']:
                print(f"  ✓ Found {parsed['error_count']} potential error(s) ({elapsed:.1f}s)")
            else:
                print(f"  ✗ No errors detected ({elapsed:.1f}s)")

        except Exception as e:
            print(f"  ❌ ERROR: {str(e)}")
            results.append({
                'run_id': run_id,
                'product_type': product_type,
                'errors_found': False,
                'error_count': 0,
                'elapsed_time': 0,
                'raw_response': f"EXCEPTION: {str(e)}"
            })

        # Rate limiting (avoid hitting OpenAI rate limits)
        if i < len(test_files):
            time.sleep(2)  # 2 second delay between calls

    # Save results
    output_file = "results/llm_direct_validation_results.csv"
    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['run_id', 'product_type', 'errors_found',
                                                'error_count', 'elapsed_time', 'raw_response'])
        writer.writeheader()
        writer.writerows(results)

    # Summary statistics
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    total_files = len(results)
    errors_detected = sum(1 for r in results if r['errors_found'])
    detection_rate = (errors_detected / total_files * 100) if total_files > 0 else 0

    print(f"Total files tested: {total_files}")
    print(f"Errors detected: {errors_detected}/{total_files} ({detection_rate:.1f}%)")
    print(f"No errors detected: {total_files - errors_detected}/{total_files}")
    print()
    print(f"Results saved to: {output_file}")
    print()

    # Breakdown by product
    for product in ['smartphone', 'melatonin', 'corecoin']:
        product_results = [r for r in results if r['product_type'] == product]
        if product_results:
            detected = sum(1 for r in product_results if r['errors_found'])
            total = len(product_results)
            rate = (detected / total * 100) if total > 0 else 0
            print(f"{product.capitalize()}: {detected}/{total} ({rate:.1f}%)")


if __name__ == "__main__":
    main()
