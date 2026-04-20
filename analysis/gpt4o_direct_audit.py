#!/usr/bin/env python3
"""
GPT-4o Direct Compliance Audit
Analyzes all marketing materials directly with GPT-4o (no NLI pre-filtering).
"""

import os
import csv
import json
import argparse
from pathlib import Path
from typing import List, Dict
from openai import OpenAI
import yaml
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Paths
RESULTS_DIR = Path(__file__).parent.parent / "results"
EXPERIMENTS_CSV = RESULTS_DIR / "experiments.csv"
OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"
PRODUCTS_DIR = Path(__file__).parent.parent / "products"

# Output paths
CHECKPOINT_FILE = RESULTS_DIR / "gpt4o_audit_checkpoint.jsonl"
FINAL_RESULTS_CSV = RESULTS_DIR / "gpt4o_compliance_audit.csv"
SUMMARY_FILE = RESULTS_DIR / "gpt4o_audit_summary.txt"

# OpenAI config
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
MODEL = "gpt-4o"
TEMPERATURE = 0  # Deterministic

# Compliance analysis prompt
SYSTEM_PROMPT = """You are an expert regulatory compliance analyst specializing in:
- FDA regulations for dietary supplements (DSHEA, 21 CFR Part 111)
- FTC guidelines for consumer electronics advertising
- SEC/CFTC regulations for cryptocurrency disclosures

Analyze marketing materials for compliance violations. Focus on:
1. Disease claims (prohibited for supplements)
2. Absolute guarantees without substantiation
3. Misleading omissions of risks/limitations
4. Factual inaccuracies vs product specifications
5. Prohibited claims per regulatory domain

Be STRICT but FAIR. Flag genuine compliance risks, not stylistic preferences.
"""

ANALYSIS_TEMPLATE = """
PRODUCT: {product_name}
REGULATORY DOMAIN: {regulatory_domain}

MARKETING MATERIAL TO ANALYZE:
{material_text}

REGULATORY CONTEXT:

PROHIBITED CLAIMS (MUST NOT appear in marketing):
{prohibited_claims}

AUTHORIZED CLAIMS (CAN appear in marketing):
{authorized_claims}

PRODUCT SPECIFICATIONS:
{specs}

CLARIFICATIONS:
{clarifications}

---

TASK: Identify ALL compliance violations in this marketing material.

For each violation found, specify:
1. Exact text that violates regulations
2. Which rule it violates (reference prohibited claim or regulatory principle)
3. Severity: LOW / MEDIUM / HIGH / CRITICAL
4. Why it's a violation
5. Suggested compliant alternative

OUTPUT FORMAT (JSON):

{{
  "compliant": true/false,
  "violations": [
    {{
      "claim_text": "<exact violating text>",
      "violation_type": "disease_claim" | "absolute_language" | "misleading_omission" | "factual_error" | "prohibited_claim",
      "severity": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
      "rule_violated": "<specific prohibited claim or regulatory principle>",
      "reasoning": "<why this is a violation>",
      "suggested_fix": "<compliant alternative>"
    }}
  ],
  "violation_count": <number>,
  "overall_severity": "NONE" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
  "summary": "<brief compliance assessment>"
}}

If material is fully compliant, return: {{"compliant": true, "violations": [], "violation_count": 0, "overall_severity": "NONE", "summary": "No violations detected"}}
"""


def load_product_yaml(product_id: str) -> dict:
    """Load product YAML specification."""
    yaml_path = PRODUCTS_DIR / f"{product_id}.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"Product YAML not found: {yaml_path}")

    with open(yaml_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def format_product_context(product_yaml: dict) -> Dict[str, str]:
    """Extract regulatory context from product YAML."""
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
        'authorized_claims': '\n'.join(f"  - {c}" for c in auth_list[:30]),
        'prohibited_claims': '\n'.join(f"  - {c}" for c in prohib_list[:30]),
        'specs': '\n'.join(f"  - {s}" for s in specs_list[:40]),
        'clarifications': '\n'.join(f"  - {c}" for c in clarifications[:20])
    }


def analyze_material(material_text: str, product_id: str, run_id: str) -> Dict:
    """
    Analyze a marketing material for compliance violations using GPT-4o.

    Returns:
        Dict with compliance assessment and violations
    """
    # Load product context
    product_yaml = load_product_yaml(product_id)
    context = format_product_context(product_yaml)

    # Format prompt
    user_prompt = ANALYSIS_TEMPLATE.format(
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
        result['run_id'] = run_id
        result['product_id'] = product_id
        result['model'] = MODEL
        result['temperature'] = TEMPERATURE

        return result

    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        return {
            'run_id': run_id,
            'product_id': product_id,
            'compliant': None,
            'violations': [],
            'violation_count': 0,
            'overall_severity': 'ERROR',
            'summary': f'Analysis error: {str(e)}',
            'error': str(e)
        }


def load_completed_runs() -> set:
    """Load run_ids already processed from checkpoint."""
    if not CHECKPOINT_FILE.exists():
        return set()

    completed = set()
    with open(CHECKPOINT_FILE) as f:
        for line in f:
            try:
                result = json.loads(line)
                completed.add(result['run_id'])
            except:
                pass
    return completed


def save_checkpoint(result: Dict):
    """Append result to checkpoint file."""
    with open(CHECKPOINT_FILE, 'a') as f:
        json.dump(result, f)
        f.write('\n')


def audit_all_materials(resume: bool = True, limit: int = None):
    """
    Audit all completed experimental runs.

    Args:
        resume: Skip runs already in checkpoint
        limit: Limit number of runs to process (for testing)
    """
    print("=" * 80)
    print("GPT-4O DIRECT COMPLIANCE AUDIT")
    print("=" * 80)
    print()

    # Load experiments
    if not EXPERIMENTS_CSV.exists():
        raise FileNotFoundError(f"experiments.csv not found: {EXPERIMENTS_CSV}")

    with open(EXPERIMENTS_CSV) as f:
        reader = csv.DictReader(f)
        experiments = [r for r in reader if r['status'] == 'completed']

    print(f"✓ Loaded {len(experiments)} completed runs")

    # Resume from checkpoint
    completed_runs = set()
    if resume:
        completed_runs = load_completed_runs()
        if completed_runs:
            print(f"✓ Resuming: {len(completed_runs)} runs already processed")
            experiments = [e for e in experiments if e['run_id'] not in completed_runs]

    if limit:
        experiments = experiments[:limit]
        print(f"⚠ Limiting to first {limit} runs")

    print(f"✓ Processing {len(experiments)} runs")
    print(f"✓ Estimated cost: ~${len(experiments) * 0.015:.2f} (${0.015}/run)")
    print(f"✓ Estimated time: ~{len(experiments) * 10 / 60:.1f} minutes")
    print()

    # Process each run
    results = []
    for i, exp in enumerate(experiments, 1):
        run_id = exp['run_id']
        product_id = exp['product_id']
        output_path = OUTPUTS_DIR / f"{run_id}.txt"

        print(f"[{i}/{len(experiments)}] Analyzing {run_id[:12]} ({product_id})...")

        # Load material
        if not output_path.exists():
            print(f"  ✗ Output file not found: {output_path}")
            continue

        with open(output_path, 'r', encoding='utf-8') as f:
            material_text = f.read()

        # Analyze
        result = analyze_material(material_text, product_id, run_id)

        # Add experiment metadata
        result['engine'] = exp.get('engine', 'unknown')
        result['temperature'] = exp.get('temperature', 'unknown')
        result['material_type'] = exp.get('material_type', 'unknown')
        result['time_of_day_label'] = exp.get('time_of_day_label', 'unknown')

        # Log result
        compliant = result.get('compliant')
        violation_count = result.get('violation_count', 0)
        severity = result.get('overall_severity', 'UNKNOWN')

        if compliant is True:
            print(f"  ✓ COMPLIANT")
        elif compliant is False:
            print(f"  ✗ {violation_count} violations (severity: {severity})")
        else:
            print(f"  ! ERROR")

        # Save checkpoint
        save_checkpoint(result)
        results.append(result)

        print()

    # Generate summary
    generate_summary(results)

    # Export to CSV
    export_to_csv()

    print("=" * 80)
    print("✓ AUDIT COMPLETE")
    print("=" * 80)


def generate_summary(results: List[Dict]):
    """Generate summary statistics."""
    total = len(results)
    compliant = sum(1 for r in results if r.get('compliant') is True)
    non_compliant = sum(1 for r in results if r.get('compliant') is False)
    errors = sum(1 for r in results if r.get('compliant') is None)

    total_violations = sum(r.get('violation_count', 0) for r in results)

    # Severity breakdown
    critical = sum(1 for r in results if r.get('overall_severity') == 'CRITICAL')
    high = sum(1 for r in results if r.get('overall_severity') == 'HIGH')
    medium = sum(1 for r in results if r.get('overall_severity') == 'MEDIUM')
    low = sum(1 for r in results if r.get('overall_severity') == 'LOW')

    summary = f"""
================================================================================
GPT-4O COMPLIANCE AUDIT - SUMMARY
================================================================================
Total runs analyzed:     {total}
  ✓ COMPLIANT:           {compliant} ({compliant/total*100:.1f}%)
  ✗ NON-COMPLIANT:       {non_compliant} ({non_compliant/total*100:.1f}%)
  ! ERROR:               {errors}

Total violations found:  {total_violations}
Average per run:         {total_violations/total:.1f}

Severity breakdown:
  CRITICAL:              {critical}
  HIGH:                  {high}
  MEDIUM:                {medium}
  LOW:                   {low}
================================================================================
"""

    print(summary)

    with open(SUMMARY_FILE, 'w') as f:
        f.write(summary)

    print(f"✓ Summary saved to {SUMMARY_FILE}")


def export_to_csv():
    """Export checkpoint results to CSV format."""
    if not CHECKPOINT_FILE.exists():
        print("⚠ No checkpoint file found")
        return

    # Load all results
    results = []
    with open(CHECKPOINT_FILE) as f:
        for line in f:
            results.append(json.loads(line))

    # Flatten to CSV rows (one row per violation)
    csv_rows = []
    for result in results:
        run_id = result['run_id']
        product_id = result['product_id']
        engine = result.get('engine', 'unknown')
        temperature = result.get('temperature', 'unknown')
        material_type = result.get('material_type', 'unknown')
        time_of_day = result.get('time_of_day_label', 'unknown')
        compliant = result.get('compliant', None)
        overall_severity = result.get('overall_severity', 'NONE')

        violations = result.get('violations', [])

        if not violations:
            # Still include compliant runs
            csv_rows.append({
                'run_id': run_id,
                'product_id': product_id,
                'engine': engine,
                'temperature': temperature,
                'material_type': material_type,
                'time_of_day': time_of_day,
                'compliant': compliant,
                'violation_count': 0,
                'overall_severity': overall_severity,
                'claim_text': '',
                'violation_type': '',
                'severity': '',
                'rule_violated': '',
                'reasoning': '',
                'suggested_fix': ''
            })
        else:
            for v in violations:
                csv_rows.append({
                    'run_id': run_id,
                    'product_id': product_id,
                    'engine': engine,
                    'temperature': temperature,
                    'material_type': material_type,
                    'time_of_day': time_of_day,
                    'compliant': compliant,
                    'violation_count': len(violations),
                    'overall_severity': overall_severity,
                    'claim_text': v.get('claim_text', ''),
                    'violation_type': v.get('violation_type', ''),
                    'severity': v.get('severity', ''),
                    'rule_violated': v.get('rule_violated', ''),
                    'reasoning': v.get('reasoning', ''),
                    'suggested_fix': v.get('suggested_fix', '')
                })

    # Write CSV
    if csv_rows:
        with open(FINAL_RESULTS_CSV, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['run_id', 'product_id', 'engine', 'temperature', 'material_type',
                         'time_of_day', 'compliant', 'violation_count', 'overall_severity',
                         'claim_text', 'violation_type', 'severity', 'rule_violated',
                         'reasoning', 'suggested_fix']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)

        print(f"✓ CSV exported to {FINAL_RESULTS_CSV} ({len(csv_rows)} rows)")


def main():
    parser = argparse.ArgumentParser(description='GPT-4o direct compliance audit')
    parser.add_argument('--resume', action='store_true', default=True, help='Resume from checkpoint')
    parser.add_argument('--clean', action='store_true', help='Start fresh (clear checkpoint)')
    parser.add_argument('--limit', type=int, help='Limit number of runs (for testing)')
    args = parser.parse_args()

    if args.clean and CHECKPOINT_FILE.exists():
        CHECKPOINT_FILE.unlink()
        print("✓ Cleared checkpoint")

    audit_all_materials(resume=args.resume, limit=args.limit)


if __name__ == "__main__":
    main()
