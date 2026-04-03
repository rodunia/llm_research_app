#!/usr/bin/env python3
"""
Run Gemini Free-Form detection on errors/ folder files.
"""

import sys
import os
import yaml
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def validate_with_gemini(marketing_text: str, specs_text: str, run_id: str) -> dict:
    """
    Validate marketing text using Gemini with free-form prompts.

    Returns dict with:
        - errors_found: bool
        - error_count: int
        - response_text: str
    """

    genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
    model = genai.GenerativeModel('gemini-1.5-flash')

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
   - What the correct information should be
   - Why it's problematic

If you find NO errors, respond with exactly: "NO ERRORS FOUND"

If you find errors, list them numbered like:
1. [Error description]
2. [Error description]
etc.
"""

    try:
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,
                max_output_tokens=2048
            )
        )

        response_text = response.text
        errors_found = "NO ERRORS FOUND" not in response_text.upper() or any(
            response_text.strip().startswith(f"{i}.") for i in range(1, 11)
        )

        # Count numbered errors
        error_count = 0
        for line in response_text.split('\n'):
            stripped = line.strip()
            if any(stripped.startswith(f"{i}.") for i in range(1, 11)):
                error_count += 1

        logger.info(f"{run_id}: Gemini found {error_count} errors")

        return {
            'errors_found': errors_found,
            'error_count': error_count,
            'response_text': response_text
        }

    except Exception as e:
        logger.error(f"Gemini API error for {run_id}: {e}")
        return {
            'errors_found': False,
            'error_count': 0,
            'response_text': f"ERROR: {str(e)}"
        }


def main():
    """Process all error files with Gemini."""

    errors_dir = Path('errors')
    output_dir = Path('results/errors_analysis/gemini_freeform')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get all error files
    error_files = sorted(errors_dir.glob('errors_*.txt'))

    logger.info(f"Found {len(error_files)} error files to process")

    for error_file in error_files:
        run_id = error_file.stem  # e.g., "errors_smartphone_1"

        # Determine product
        if 'smartphone' in run_id:
            product_id = 'smartphone_mid'
        elif 'melatonin' in run_id:
            product_id = 'supplement_melatonin'
        elif 'corecoin' in run_id:
            product_id = 'cryptocurrency_corecoin'
        else:
            logger.warning(f"Unknown product for {run_id}, skipping")
            continue

        # Load marketing text
        with open(error_file, 'r') as f:
            marketing_text = f.read()

        # Load product specs
        product_yaml_path = Path(f'products/{product_id}.yaml')
        if not product_yaml_path.exists():
            logger.error(f"Product YAML not found: {product_yaml_path}")
            continue

        with open(product_yaml_path, 'r') as f:
            product_data = yaml.safe_load(f)

        # Convert product specs to text
        specs_text = yaml.dump(product_data, default_flow_style=False)

        # Run Gemini validation
        logger.info(f"Processing {run_id} with Gemini...")
        result = validate_with_gemini(marketing_text, specs_text, run_id)

        # Save result
        output_file = output_dir / f"{run_id}.txt"
        with open(output_file, 'w') as f:
            f.write(result['response_text'])

        logger.info(f"  Saved: {output_file}")

    logger.info("Gemini processing complete!")


if __name__ == '__main__':
    main()
