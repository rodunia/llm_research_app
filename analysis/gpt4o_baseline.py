#!/usr/bin/env python3
"""
GPT-4o Baseline Detection System

Direct error detection using GPT-4o (temp 0) to compare against Glass Box audit.
"""

import os
import json
import yaml
from pathlib import Path
from openai import OpenAI

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

PILOT_FILES = Path('pilot_study')
PRODUCTS_DIR = Path('products')
OUTPUT_DIR = Path('results/gpt4o_baseline')
OUTPUT_DIR.mkdir(exist_ok=True)

def load_product_yaml(product_id: str) -> dict:
    """Load product specification YAML."""
    yaml_path = PRODUCTS_DIR / f'{product_id}.yaml'
    with open(yaml_path) as f:
        return yaml.safe_load(f)

def create_detection_prompt(marketing_text: str, product_spec: dict) -> str:
    """Create prompt for GPT-4o to detect errors."""

    # Format product specs as readable text
    specs_text = yaml.dump(product_spec, default_flow_style=False, sort_keys=False)

    prompt = f"""You are a compliance auditor analyzing marketing materials for factual errors.

TASK: Identify ALL factual errors, contradictions, and unsupported claims in the marketing text below.

PRODUCT SPECIFICATIONS:
```yaml
{specs_text}
```

MARKETING TEXT:
{marketing_text}

INSTRUCTIONS:
1. Compare every claim in the marketing text against the product specifications
2. Flag any claim that:
   - Contradicts the specifications
   - Includes information not in the specifications
   - Contains numerical errors (wrong numbers, units, ranges)
   - Makes unsupported promises or guarantees

OUTPUT FORMAT (JSON):
{{
  "errors_detected": true/false,
  "error_count": <number>,
  "errors": [
    {{
      "claim": "exact text from marketing material",
      "error_type": "numerical|factual|logical|hallucination",
      "explanation": "why this is an error",
      "correct_value": "what it should be (if applicable)"
    }}
  ]
}}

Be thorough and precise. Only flag genuine errors - do not flag stylistic choices or marketing tone.
"""
    return prompt

def detect_errors_gpt4o(marketing_text: str, product_spec: dict) -> dict:
    """Use GPT-4o to detect errors in marketing text."""

    prompt = create_detection_prompt(marketing_text, product_spec)

    response = client.chat.completions.create(
        model='gpt-4o',
        temperature=0,  # Deterministic
        messages=[
            {'role': 'system', 'content': 'You are a precise compliance auditor. Output valid JSON only.'},
            {'role': 'user', 'content': prompt}
        ],
        response_format={'type': 'json_object'}
    )

    result = json.loads(response.choices[0].message.content)

    return {
        'errors_detected': result.get('errors_detected', False),
        'error_count': result.get('error_count', 0),
        'errors': result.get('errors', []),
        'model': 'gpt-4o',
        'temperature': 0,
        'prompt_tokens': response.usage.prompt_tokens,
        'completion_tokens': response.usage.completion_tokens,
        'total_tokens': response.usage.total_tokens
    }

def run_gpt4o_on_pilot():
    """Run GPT-4o detection on all 30 pilot files."""

    # Map of pilot files to product IDs
    file_mapping = {}

    # Melatonin
    for i in range(1, 11):
        file_mapping[f'melatonin_{i}'] = {
            'path': PILOT_FILES / 'melatonin' / 'files' / f'melatonin_{i}.txt',
            'product_id': 'supplement_melatonin'
        }

    # Smartphone
    for i in range(1, 11):
        file_mapping[f'smartphone_{i}'] = {
            'path': PILOT_FILES / 'smartphone' / 'files' / f'smartphone_{i}.txt',
            'product_id': 'smartphone_mid'
        }

    # CoreCoin
    for i in range(1, 11):
        file_mapping[f'corecoin_{i}'] = {
            'path': PILOT_FILES / 'corecoin' / 'files' / f'corecoin_{i}.txt',
            'product_id': 'cryptocurrency_corecoin'
        }

    results = {}

    for file_id, info in sorted(file_mapping.items()):
        print(f"Processing {file_id}...")

        # Load marketing text
        with open(info['path']) as f:
            marketing_text = f.read()

        # Load product spec
        product_spec = load_product_yaml(info['product_id'])

        # Detect errors with GPT-4o
        try:
            result = detect_errors_gpt4o(marketing_text, product_spec)
            results[file_id] = {
                **result,
                'product_id': info['product_id'],
                'status': 'success'
            }

            print(f"  ✓ {result['error_count']} errors detected")

        except Exception as e:
            results[file_id] = {
                'status': 'error',
                'error_message': str(e),
                'product_id': info['product_id']
            }
            print(f"  ✗ Error: {e}")

        # Save individual result
        output_file = OUTPUT_DIR / f'{file_id}.json'
        with open(output_file, 'w') as f:
            json.dump(results[file_id], f, indent=2)

    # Save combined results
    with open(OUTPUT_DIR / 'all_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Complete! Results saved to {OUTPUT_DIR}/")

    # Quick summary
    detected_count = sum(1 for r in results.values() if r.get('errors_detected', False))
    print(f"\nQuick summary: {detected_count}/30 files had errors detected by GPT-4o")

    return results

if __name__ == '__main__':
    print("="*70)
    print("GPT-4o BASELINE DETECTION (Temperature 0)")
    print("="*70)
    print()

    results = run_gpt4o_on_pilot()
