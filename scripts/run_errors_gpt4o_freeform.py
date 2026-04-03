#!/usr/bin/env python3
"""
Run GPT-4o Free-Form detection on errors/ folder files.
"""

import sys
import os
import yaml
import json
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def validate_with_llm(marketing_text: str, specs_text: str, run_id: str) -> dict:
    """
    Validate marketing text using GPT-4o with free-form prompts.

    Returns dict with:
        - errors_found: bool
        - error_count: int
        - response_text: str
    """

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    prompt = f"""You are a fact-checking assistant. Your task is to identify any factual errors, contradictions, or unsupported claims in marketing text by comparing it to product specifications.

# Product Specifications:
{specs_text}

# Marketing Text to Validate:
{marketing_text}

# Instructions:
1. Carefully read the marketing text
2. Compare each factual claim against specifications
3. Identify any errors, contradictions, or unsupported claims
4. For each error found, provide:
   - The incorrect claim
   - What it should be according to specifications
   - Why this is an error
   - Your confidence level (High/Medium/Low)
5. If you find NO errors, clearly state "NO ERRORS FOUND"

# Your Analysis:
"""

    try:
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {"role": "system", "content": "You are a precise fact-checking assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=2000
        )

        response_text = response.choices[0].message.content

        # Parse response (heuristic - count bullet points or look for "NO ERRORS")
        errors_found = "NO ERRORS FOUND" not in response_text.upper()

        # Count errors (rough heuristic)
        error_count = 0
        if errors_found:
            # Count numbered items or bullet points
            for line in response_text.split('\n'):
                if line.strip().startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.', '-', '*', '•')):
                    error_count += 1

        return {
            'errors_found': errors_found,
            'error_count': error_count,
            'response_text': response_text
        }

    except Exception as e:
        logger.error(f"API error for {run_id}: {e}")
        return {
            'errors_found': False,
            'error_count': 0,
            'response_text': f"ERROR: {e}"
        }

def main():
    """Run GPT-4o Free-Form on all 30 error files."""

    # File mapping
    files = []
    for i in range(1, 11):
        files.append(('smartphone_mid', f'errors_smartphone_{i}'))
        files.append(('supplement_melatonin', f'errors_melatonin_{i}'))
        files.append(('cryptocurrency_corecoin', f'errors_corecoin_{i}'))

    # Output directory
    output_dir = Path('results/errors_analysis/gpt4o_freeform')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process each file
    results = []
    for idx, (product_id, file_prefix) in enumerate(files, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing {idx}/30: {file_prefix}")
        logger.info(f"{'='*60}")

        # Paths
        input_file = Path(f'outputs/{file_prefix}.txt')
        product_yaml = Path(f'products/{product_id}.yaml')

        if not input_file.exists():
            logger.error(f"Input file not found: {input_file}")
            continue

        if not product_yaml.exists():
            logger.error(f"Product YAML not found: {product_yaml}")
            continue

        # Load product spec
        with open(product_yaml, 'r') as f:
            product_spec = yaml.safe_load(f)

        # Convert YAML to text
        specs_text = yaml.dump(product_spec, default_flow_style=False, sort_keys=False)

        # Load marketing text
        with open(input_file, 'r') as f:
            marketing_text = f.read()

        # Run GPT-4o Free-Form
        result = validate_with_llm(marketing_text, specs_text, file_prefix)

        # Save individual response
        response_file = output_dir / f'{file_prefix}.txt'
        with open(response_file, 'w') as f:
            f.write(result['response_text'])

        logger.info(f"✓ {file_prefix}: Errors detected = {result['errors_found']} ({result['error_count']} violations)")

        results.append({
            'file': file_prefix,
            'product': product_id,
            'errors_detected': result['errors_found'],
            'error_count': result['error_count'],
            'response_file': str(response_file)
        })

    # Save summary
    summary_file = output_dir / 'summary.json'
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)

    logger.info(f"\n{'='*60}")
    logger.info(f"GPT-4O FREE-FORM ANALYSIS COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Processed: {len(results)}/30 files")
    logger.info(f"Detected errors: {sum(1 for r in results if r['errors_detected'])}/30")
    logger.info(f"Summary saved: {summary_file}")

if __name__ == '__main__':
    main()
