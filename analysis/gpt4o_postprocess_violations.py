#!/usr/bin/env python3
"""
GPT-4o Post-Processing for RoBERTa Violations

Reads violations from glass_box_audit.py results and runs GPT-4o analysis
to filter false positives and add severity/explanations.

This DOES NOT replace the existing pipeline - it's an optional post-processing step.

Usage:
    python analysis/gpt4o_postprocess_violations.py --input results/final_audit_results.csv
"""

import os
import csv
import json
import argparse
from pathlib import Path
from typing import Dict, List
from openai import OpenAI
import yaml
from dotenv import load_dotenv
from collections import defaultdict

# Load environment
load_dotenv()

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Model configuration
MODEL = "gpt-4o"
TEMPERATURE = 0

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"
PRODUCTS_DIR = PROJECT_ROOT / "products"
RESULTS_DIR = PROJECT_ROOT / "results"

# System prompt for post-processing
SYSTEM_PROMPT = """You are an expert regulatory compliance analyst reviewing potential violations flagged by an automated system.

Your task is to FILTER false positives while keeping genuine compliance risks.

The automated system (RoBERTa NLI) has high recall but also flags semantic mismatches. Your job is to determine:
1. Is this a REAL compliance violation?
2. Or is it a false positive (e.g., different contexts, harmless variation)?

Be STRICT but FAIR. Only keep genuine compliance risks.
"""

ANALYSIS_TEMPLATE = """PRODUCT: {product_name}
REGULATORY DOMAIN: {regulatory_domain}

MARKETING MATERIAL (full context):
{material_text}

POTENTIAL VIOLATION FLAGGED BY AUTOMATED SYSTEM:

Extracted Claim: "{claim}"
Violated Rule: "{violated_rule}"
NLI Confidence: {confidence}

REGULATORY CONTEXT:

PROHIBITED CLAIMS:
{prohibited_claims}

AUTHORIZED CLAIMS:
{authorized_claims}

PRODUCT SPECIFICATIONS:
{specs}

CLARIFICATIONS:
{clarifications}

---

TASK: Determine if this is a REAL violation or a FALSE POSITIVE.

Consider:
1. **Context**: Does the full material context change the interpretation?
2. **Semantic Match**: Is this claim actually contradicting the rule, or just similar wording?
3. **Materiality**: Would this actually mislead consumers or violate regulations?
4. **Regulatory Risk**: Is this a genuine compliance concern?

OUTPUT FORMAT (JSON):

{{
  "verdict": "TRUE_VIOLATION" | "FALSE_POSITIVE" | "GREY_AREA",
  "severity": "NONE" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
  "reasoning": "<detailed explanation>",
  "recommended_action": "REMOVE" | "REVISE" | "ADD_DISCLAIMER" | "REVIEW" | "IGNORE",
  "suggested_fix": null | "<compliant alternative>",
  "confidence": 0.0-1.0
}}

VERDICT DEFINITIONS:
- TRUE_VIOLATION: Genuine compliance violation, must be addressed
- FALSE_POSITIVE: Automated system error, safe to ignore
- GREY_AREA: Borderline case, needs human review

SEVERITY (for TRUE_VIOLATION only):
- LOW: Minor concern, unlikely enforcement risk
- MEDIUM: Moderate risk, should be reviewed
- HIGH: Likely violation, enforcement risk
- CRITICAL: Serious violation, immediate action required
"""


def load_product_yaml(product_id: str) -> dict:
    """Load product YAML specification."""
    yaml_path = PRODUCTS_DIR / f"{product_id}.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"Product YAML not found: {yaml_path}")

    with open(yaml_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def format_product_context(product_yaml: dict) -> Dict[str, str]:
    """Extract and format regulatory context from product YAML."""

    # Flatten authorized claims
    authorized = product_yaml.get('authorized_claims', {})
    auth_list = []
    if isinstance(authorized, dict):
        for category, claims in authorized.items():
            if isinstance(claims, list):
                auth_list.extend(claims)

    # Flatten prohibited claims
    prohibited = product_yaml.get('prohibited_or_unsupported_claims', {})
    prohib_list = []
    if isinstance(prohibited, dict):
        for category, claims in prohibited.items():
            if isinstance(claims, list):
                prohib_list.extend(claims)

    # Flatten specs
    specs = product_yaml.get('specs', {})
    specs_list = []
    def extract_strings(data):
        if isinstance(data, str):
            return [data]
        elif isinstance(data, list):
            result = []
            for item in data:
                result.extend(extract_strings(item))
            return result
        elif isinstance(data, dict):
            result = []
            for value in data.values():
                result.extend(extract_strings(value))
            return result
        return []
    specs_list = extract_strings(specs)

    # Get clarifications
    clarifications = product_yaml.get('clarifications', [])
    if not isinstance(clarifications, list):
        clarifications = []

    return {
        'product_name': product_yaml.get('name', 'Unknown Product'),
        'regulatory_domain': product_yaml.get('regulatory_classification', 'Unknown'),
        'authorized_claims': '\n'.join(f"  - {c}" for c in auth_list) or '  (none provided)',
        'prohibited_claims': '\n'.join(f"  - {c}" for c in prohib_list) or '  (none provided)',
        'specs': '\n'.join(f"  - {s}" for s in specs_list[:50]) or '  (none provided)',
        'clarifications': '\n'.join(f"  - {c}" for c in clarifications) or '  (none provided)'
    }


def review_violation(
    claim: str,
    violated_rule: str,
    confidence: float,
    material_text: str,
    product_id: str
) -> Dict:
    """
    Use GPT-4o to review a single violation flagged by RoBERTa.

    Returns:
        Dict with verdict, severity, reasoning, etc.
    """
    # Load product context
    product_yaml = load_product_yaml(product_id)
    context = format_product_context(product_yaml)

    # Format prompt
    user_prompt = ANALYSIS_TEMPLATE.format(
        claim=claim,
        violated_rule=violated_rule,
        confidence=f"{confidence:.4f}",
        material_text=material_text[:8000],  # Limit to avoid token overflow
        **context
    )

    try:
        response = openai_client.chat.completions.create(
            model=MODEL,
            temperature=TEMPERATURE,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        # Add metadata
        result['claim'] = claim
        result['violated_rule'] = violated_rule
        result['nli_confidence'] = confidence

        return result

    except Exception as e:
        return {
            'verdict': 'ERROR',
            'severity': 'NONE',
            'reasoning': f'Error during GPT-4o review: {str(e)}',
            'recommended_action': 'REVIEW',
            'suggested_fix': None,
            'confidence': 0.0,
            'claim': claim,
            'violated_rule': violated_rule,
            'nli_confidence': confidence,
            'error': str(e)
        }


def load_violations_from_csv(csv_path: Path) -> Dict[str, List[Dict]]:
    """
    Load violations from glass_box_audit CSV results.
    Groups violations by run_id.

    Returns:
        Dict mapping run_id -> list of violation dicts
    """
    violations_by_material = defaultdict(list)

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip PASS rows
            if row['Status'] != 'FAIL':
                continue

            run_id = row['Filename'].replace('.txt', '')

            violations_by_material[run_id].append({
                'claim': row['Extracted_Claim'],
                'violated_rule': row['Violated_Rule'],
                'confidence': float(row['Confidence_Score']),
                'product_id': row.get('product_id', 'unknown'),
                'material_type': row.get('material_type', 'unknown'),
                'engine': row.get('engine', 'unknown'),
                'temperature': row.get('temperature', 'unknown')
            })

    return dict(violations_by_material)


def load_material(run_id: str) -> str:
    """Load marketing material text from outputs/."""
    txt_file = OUTPUTS_DIR / f"{run_id}.txt"
    if not txt_file.exists():
        raise FileNotFoundError(f"Material not found: {txt_file}")

    with open(txt_file, 'r', encoding='utf-8') as f:
        return f.read()


def main():
    parser = argparse.ArgumentParser(
        description='GPT-4o post-processing for RoBERTa violations'
    )
    parser.add_argument(
        '--input',
        type=str,
        default='results/final_audit_results.csv',
        help='Path to glass_box_audit results CSV'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='results/gpt4o_filtered_violations.csv',
        help='Path to output CSV with GPT-4o filtering'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of materials to process (for testing)'
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        return

    print("="*70)
    print("GPT-4O POST-PROCESSING FOR ROBERTA VIOLATIONS")
    print("="*70)
    print(f"\nInput: {input_path}")
    print(f"Output: {output_path}\n")

    # Load violations
    print("Loading violations from CSV...")
    violations_by_material = load_violations_from_csv(input_path)

    total_materials = len(violations_by_material)
    total_violations = sum(len(v) for v in violations_by_material.values())

    print(f"Found {total_violations} violations across {total_materials} materials")

    # Apply limit if specified
    if args.limit:
        materials_to_process = dict(list(violations_by_material.items())[:args.limit])
        print(f"Processing first {args.limit} materials (test mode)")
    else:
        materials_to_process = violations_by_material

    # Process each material
    results = []
    true_violations = 0
    false_positives = 0
    grey_areas = 0
    errors = 0

    for i, (run_id, violations) in enumerate(materials_to_process.items(), 1):
        print(f"\n[{i}/{len(materials_to_process)}] Processing {run_id} ({len(violations)} violations)...")

        try:
            # Load material text
            material_text = load_material(run_id)

            # Review each violation with GPT-4o
            for v in violations:
                review = review_violation(
                    claim=v['claim'],
                    violated_rule=v['violated_rule'],
                    confidence=v['confidence'],
                    material_text=material_text,
                    product_id=v['product_id']
                )

                # Count verdicts
                verdict = review.get('verdict', 'ERROR')
                if verdict == 'TRUE_VIOLATION':
                    true_violations += 1
                    print(f"  ✓ TRUE_VIOLATION ({review.get('severity', 'UNKNOWN')}): {v['claim'][:60]}...")
                elif verdict == 'FALSE_POSITIVE':
                    false_positives += 1
                    print(f"  ✗ FALSE_POSITIVE: {v['claim'][:60]}...")
                elif verdict == 'GREY_AREA':
                    grey_areas += 1
                    print(f"  ? GREY_AREA: {v['claim'][:60]}...")
                else:
                    errors += 1
                    print(f"  ! ERROR: {v['claim'][:60]}...")

                # Add to results
                results.append({
                    'Run_ID': run_id,
                    'Product_ID': v['product_id'],
                    'Material_Type': v['material_type'],
                    'Engine': v['engine'],
                    'Temperature': v['temperature'],
                    'Claim': v['claim'],
                    'Violated_Rule': v['violated_rule'],
                    'NLI_Confidence': f"{v['confidence']:.4f}",
                    'GPT4o_Verdict': review.get('verdict', 'ERROR'),
                    'GPT4o_Severity': review.get('severity', 'NONE'),
                    'GPT4o_Reasoning': review.get('reasoning', ''),
                    'Recommended_Action': review.get('recommended_action', 'REVIEW'),
                    'Suggested_Fix': review.get('suggested_fix', ''),
                    'GPT4o_Confidence': f"{review.get('confidence', 0.0):.4f}"
                })

        except Exception as e:
            print(f"  ERROR processing {run_id}: {str(e)}")
            errors += 1

    # Save results
    print(f"\nSaving results to {output_path}...")
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        if results:
            fieldnames = list(results[0].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total violations reviewed: {total_violations}")
    print(f"  ✓ TRUE_VIOLATION:  {true_violations} ({100*true_violations/total_violations:.1f}%)")
    print(f"  ✗ FALSE_POSITIVE:  {false_positives} ({100*false_positives/total_violations:.1f}%)")
    print(f"  ? GREY_AREA:       {grey_areas} ({100*grey_areas/total_violations:.1f}%)")
    print(f"  ! ERROR:           {errors}")
    print(f"\nFalse positive reduction: {100*false_positives/total_violations:.1f}%")
    print(f"Results saved to: {output_path}")
    print("="*70)


if __name__ == "__main__":
    main()
