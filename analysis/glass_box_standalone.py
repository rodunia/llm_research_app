#!/usr/bin/env python3
"""
Standalone Glass Box Audit with Ground Truth Validation.

Usage:
    python3 analysis/glass_box_standalone.py \
        --input pilot_study/ \
        --ground-truth GROUND_TRUTH_ERRORS.md \
        --output pilot_results/

This script:
1. Audits marketing files without requiring experiments.csv
2. Validates detections against ground truth errors
3. Generates detection rate reports
"""

import argparse
import csv
import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Tuple
import yaml

# Import Glass Box core components
from glass_box_audit import (
    extract_atomic_claims,
    NLIJudge,
    EXTRACTION_MODEL,
    NLI_MODEL_NAME,
    VIOLATION_THRESHOLD
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ==================== GROUND TRUTH PARSER ====================

def parse_ground_truth(ground_truth_path: Path) -> Dict[str, Dict]:
    """Parse GROUND_TRUTH_ERRORS.md to extract expected errors per file."""

    ground_truth = {}

    with open(ground_truth_path) as f:
        content = f.read()

    # Extract keyword sections
    melatonin_section = re.search(r'MELATONIN_KEYWORDS = \{(.*?)\}', content, re.DOTALL)
    smartphone_section = re.search(r'SMARTPHONE_KEYWORDS = \{(.*?)\}', content, re.DOTALL)
    corecoin_section = re.search(r'CORECOIN_KEYWORDS = \{(.*?)\}', content, re.DOTALL)

    # Parse error descriptions from tables
    # Melatonin table
    melatonin_table = re.search(
        r'## Melatonin Supplement.*?\| File \| Error Description.*?\n(.*?)(?=\n---|\n##|$)',
        content,
        re.DOTALL
    )
    if melatonin_table:
        for line in melatonin_table.group(1).strip().split('\n'):
            if '|' not in line or line.startswith('|---'):
                continue
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 4:
                file_id = parts[1]
                error_desc = parts[2]
                error_type = parts[3]
                if file_id.startswith('user_melatonin_'):
                    run_id = file_id
                    ground_truth[run_id] = {
                        'error': error_desc,
                        'type': error_type,
                        'keywords': []  # Will populate from KEYWORDS dict
                    }

    # Smartphone table
    smartphone_table = re.search(
        r'## Smartphone \(Mid-Range\).*?\| File \| Error Description.*?\n(.*?)(?=\n---|\n##|$)',
        content,
        re.DOTALL
    )
    if smartphone_table:
        for line in smartphone_table.group(1).strip().split('\n'):
            if '|' not in line or line.startswith('|---'):
                continue
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 4:
                file_id = parts[1]
                error_desc = parts[2]
                error_type = parts[3]
                if file_id.startswith('user_smartphone_'):
                    run_id = file_id
                    ground_truth[run_id] = {
                        'error': error_desc,
                        'type': error_type,
                        'keywords': []
                    }

    # CoreCoin table
    corecoin_table = re.search(
        r'## CoreCoin Cryptocurrency.*?\| File \| Error Description.*?\n(.*?)(?=\n---|\n##|$)',
        content,
        re.DOTALL
    )
    if corecoin_table:
        for line in corecoin_table.group(1).strip().split('\n'):
            if '|' not in line or line.startswith('|---'):
                continue
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 4:
                file_id = parts[1]
                error_desc = parts[2]
                error_type = parts[3]
                if file_id.startswith('user_corecoin_'):
                    run_id = file_id
                    ground_truth[run_id] = {
                        'error': error_desc,
                        'type': error_type,
                        'keywords': []
                    }

    # Parse keywords from code blocks
    if melatonin_section:
        keywords_text = melatonin_section.group(1)
        for match in re.finditer(r"(\d+):\s*\[(.*?)\]", keywords_text):
            file_num = int(match.group(1))
            keywords = [k.strip().strip("'\"") for k in match.group(2).split(',')]
            run_id = f"user_melatonin_{file_num}"
            if run_id in ground_truth:
                ground_truth[run_id]['keywords'] = keywords

    if smartphone_section:
        keywords_text = smartphone_section.group(1)
        for match in re.finditer(r"(\d+):\s*\[(.*?)\]", keywords_text):
            file_num = int(match.group(1))
            keywords = [k.strip().strip("'\"") for k in match.group(2).split(',')]
            run_id = f"user_smartphone_{file_num}"
            if run_id in ground_truth:
                ground_truth[run_id]['keywords'] = keywords

    if corecoin_section:
        keywords_text = corecoin_section.group(1)
        for match in re.finditer(r"(\d+):\s*\[(.*?)\]", keywords_text):
            file_num = int(match.group(1))
            keywords = [k.strip().strip("'\"") for k in match.group(2).split(',')]
            run_id = f"user_corecoin_{file_num}"
            if run_id in ground_truth:
                ground_truth[run_id]['keywords'] = keywords

    logger.info(f"Loaded ground truth for {len(ground_truth)} files")
    return ground_truth


# ==================== STANDALONE AUDIT ====================

def audit_single_file(
    file_path: Path,
    product_yaml_path: Path,
    nli_judge: NLIJudge,
    output_dir: Path
) -> Tuple[str, List[Dict]]:
    """
    Audit a single marketing file against product YAML.

    Returns:
        (run_id, violations_list)
    """
    # Generate run_id with user_ prefix to match ground truth naming
    base_name = file_path.stem  # e.g., "melatonin_1"
    run_id = f"user_{base_name}"  # e.g., "user_melatonin_1"

    # Read marketing content
    with open(file_path) as f:
        material_content = f.read()

    # Read product YAML
    with open(product_yaml_path) as f:
        product_yaml = yaml.safe_load(f)

    product_name = product_yaml.get('product_name', 'Unknown Product')

    # STEP 1: Extract claims
    print(f"\n{'='*70}")
    print(f"📄 Processing: {run_id}")
    print(f"{'='*70}")
    print(f"[1/3] Extracting claims with GPT-4o-mini...", flush=True)
    extraction_result = extract_atomic_claims(
        material_content,
        product_name,
        'faq'  # Default material type
    )

    core_claims = extraction_result['core_claims']
    disclaimers = extraction_result.get('disclaimers', [])
    print(f"      ✓ Extracted {len(core_claims)} core claims + {len(disclaimers)} disclaimers = {len(core_claims) + len(disclaimers)} total")

    # STEP 2: Validate ALL claims (core + disclaimers)
    # CRITICAL: Must validate disclaimers too - errors can appear anywhere in the text
    all_claims = core_claims + disclaimers
    print(f"[2/3] Validating {len(all_claims)} claims with NLI model...", flush=True)

    # Handle authorized_claims (can be list or dict with nested lists)
    authorized_claims_raw = product_yaml.get('authorized_claims', [])
    if isinstance(authorized_claims_raw, dict):
        # Flatten nested dict structure: {category: [claims]} -> [claims]
        authorized_claims = []
        for category_claims in authorized_claims_raw.values():
            if isinstance(category_claims, list):
                authorized_claims.extend(category_claims)
    elif isinstance(authorized_claims_raw, list):
        authorized_claims = authorized_claims_raw
    else:
        authorized_claims = []

    # Load specs (YAML uses 'specs' key with nested structure)
    specs_raw = product_yaml.get('specs', {})
    specs = []
    if isinstance(specs_raw, dict):
        # Flatten nested specs: {category: [specs]} -> [specs]
        for category, category_specs in specs_raw.items():
            if isinstance(category_specs, list):
                specs.extend(category_specs)
            elif isinstance(category_specs, dict):
                # Further nested structure
                for subcat_specs in category_specs.values():
                    if isinstance(subcat_specs, list):
                        specs.extend(subcat_specs)
    elif isinstance(specs_raw, list):
        specs = specs_raw
    prohibited_claims = product_yaml.get('prohibited_claims', [])

    # Handle clarifications (can be list or dict with nested lists)
    clarifications_raw = product_yaml.get('clarifications', [])
    if isinstance(clarifications_raw, dict):
        # Flatten nested dict structure: {category: [claims]} -> [claims]
        clarifications = []
        for category_claims in clarifications_raw.values():
            if isinstance(category_claims, list):
                clarifications.extend(category_claims)
    elif isinstance(clarifications_raw, list):
        clarifications = clarifications_raw
    else:
        clarifications = []  # Fallback to empty list

    violations = []
    for idx, claim in enumerate(all_claims, 1):
        # Show progress every 5 claims or at the end
        if idx % 5 == 0 or idx == len(all_claims):
            print(f"      Processing claim {idx}/{len(all_claims)}...", end='\r', flush=True)

        result = nli_judge.verify_claim(
            claim,
            authorized_claims=authorized_claims,
            specs=specs,
            prohibited_claims=prohibited_claims,
            clarifications=clarifications
        )

        if result['is_violation']:
            violations.append({
                'run_id': run_id,
                'claim': claim,
                'violated_rule': result['violated_rule'],
                'confidence': result['contradiction_score']
            })

    print(f"      ✓ Completed {len(all_claims)} claims - Found {len(violations)} violations{' '*20}")

    # STEP 3: Save results
    print(f"[3/3] Saving results...", flush=True)
    # Save violations CSV
    if violations:
        violations_csv = output_dir / 'violations' / f"{run_id}.csv"
        violations_csv.parent.mkdir(parents=True, exist_ok=True)

        with open(violations_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['run_id', 'claim', 'violated_rule', 'confidence'])
            writer.writeheader()
            writer.writerows(violations)

    return run_id, violations


def validate_detection(
    run_id: str,
    violations: List[Dict],
    ground_truth: Dict[str, Dict]
) -> Dict:
    """
    Check if detected violations match ground truth error.

    Returns:
        {
            'run_id': str,
            'ground_truth_error': str,
            'error_type': str,
            'detected': bool,
            'matched_keywords': List[str],
            'matched_claim': str or None,
            'confidence': float or None,
            'violation_count': int
        }
    """
    if run_id not in ground_truth:
        return {
            'run_id': run_id,
            'ground_truth_error': 'Unknown',
            'error_type': 'Unknown',
            'detected': False,
            'matched_keywords': [],
            'matched_claim': None,
            'confidence': None,
            'violation_count': len(violations)
        }

    gt = ground_truth[run_id]
    keywords = gt['keywords']

    # Check if any violation contains ground truth keywords
    matched_keywords = []
    matched_claim = None
    matched_confidence = None

    for violation in violations:
        claim_text = violation['claim'].lower()
        rule_text = violation['violated_rule'].lower()
        combined_text = claim_text + ' ' + rule_text

        for keyword in keywords:
            if keyword.lower() in combined_text:
                matched_keywords.append(keyword)
                if matched_claim is None:
                    matched_claim = violation['claim']
                    matched_confidence = violation['confidence']

    detected = len(matched_keywords) > 0

    return {
        'run_id': run_id,
        'ground_truth_error': gt['error'],
        'error_type': gt['type'],
        'detected': detected,
        'matched_keywords': list(set(matched_keywords)),
        'matched_claim': matched_claim,
        'confidence': matched_confidence,
        'violation_count': len(violations)
    }


# ==================== MAIN EXECUTION ====================

def main():
    parser = argparse.ArgumentParser(
        description='Standalone Glass Box Audit with Ground Truth Validation'
    )
    parser.add_argument('--input', type=Path, required=True,
                       help='Input directory with pilot files (e.g., pilot_study/)')
    parser.add_argument('--ground-truth', type=Path, required=True,
                       help='Ground truth errors file (GROUND_TRUTH_ERRORS.md)')
    parser.add_argument('--output', type=Path, required=True,
                       help='Output directory for results')
    parser.add_argument('--use-semantic-filter', action='store_true',
                       help='Enable semantic pre-filtering (74%% FP reduction)')

    args = parser.parse_args()

    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)

    # Load ground truth
    logger.info(f"Loading ground truth from {args.ground_truth}")
    ground_truth = parse_ground_truth(args.ground_truth)

    # Initialize NLI Judge
    logger.info(f"Initializing NLI Judge ({NLI_MODEL_NAME})...")
    nli_judge = NLIJudge(use_semantic_filter=args.use_semantic_filter)

    # Find all pilot files
    pilot_files = []
    for product_dir in args.input.iterdir():
        if not product_dir.is_dir():
            continue
        files_dir = product_dir / 'files'
        if files_dir.exists():
            pilot_files.extend(files_dir.glob('*.txt'))

    logger.info(f"Found {len(pilot_files)} pilot files")

    # Map files to product YAMLs
    product_yaml_map = {
        'melatonin': Path('products/supplement_melatonin.yaml'),
        'smartphone': Path('products/smartphone_mid.yaml'),
        'corecoin': Path('products/cryptocurrency_corecoin.yaml')
    }

    # Audit all files
    detection_results = []

    print(f"\n{'='*70}")
    print(f"🚀 Starting Glass Box Audit on {len(pilot_files)} files")
    print(f"{'='*70}\n")

    for idx, file_path in enumerate(sorted(pilot_files), 1):
        print(f"\n[File {idx}/{len(pilot_files)}] {file_path.name}")

        # Determine product from filename
        product = None
        for p in ['melatonin', 'smartphone', 'corecoin']:
            if p in file_path.stem:
                product = p
                break

        if product is None:
            logger.warning(f"Could not determine product for {file_path.name}")
            continue

        product_yaml_path = product_yaml_map[product]
        if not product_yaml_path.exists():
            logger.error(f"Product YAML not found: {product_yaml_path}")
            continue

        # Audit file
        run_id, violations = audit_single_file(
            file_path,
            product_yaml_path,
            nli_judge,
            args.output
        )

        # Validate against ground truth
        detection = validate_detection(run_id, violations, ground_truth)
        detection_results.append(detection)

        # Show detection result
        if detection['detected']:
            print(f"      ✅ DETECTED: {detection['ground_truth_error'][:60]}...")
        else:
            print(f"      ❌ MISSED: {detection['ground_truth_error'][:60]}...")

        print(f"      Progress: {idx}/{len(pilot_files)} ({idx*100//len(pilot_files)}%)")

    # Save detection summary
    summary_csv = args.output / 'detection_summary.csv'
    with open(summary_csv, 'w', newline='') as f:
        fieldnames = [
            'run_id', 'ground_truth_error', 'error_type', 'detected',
            'matched_keywords', 'matched_claim', 'confidence', 'violation_count'
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for result in detection_results:
            result_copy = result.copy()
            result_copy['matched_keywords'] = ', '.join(result['matched_keywords'])
            writer.writerow(result_copy)

    logger.info(f"Saved detection summary to {summary_csv}")

    # Generate validation report
    generate_validation_report(detection_results, args.output)

    # Print final summary
    total = len(detection_results)
    detected = sum(1 for r in detection_results if r['detected'])
    missed = total - detected
    detection_rate = (detected / total * 100) if total > 0 else 0

    print(f"\n{'='*70}")
    print(f"📊 FINAL RESULTS")
    print(f"{'='*70}")
    print(f"Total files: {total}")
    print(f"Detected: {detected}/{total} ({detection_rate:.1f}%)")
    print(f"Missed: {missed}/{total} ({100-detection_rate:.1f}%)")
    print(f"\n✅ Results saved to: {args.output}/")
    print(f"   - violations/: Individual violation CSVs")
    print(f"   - detection_summary.csv: Detection vs ground truth")
    print(f"   - validation_report.md: Full statistical report")
    print(f"{'='*70}\n")


def generate_validation_report(detection_results: List[Dict], output_dir: Path):
    """Generate validation report with detection statistics."""

    total = len(detection_results)
    detected = sum(1 for r in detection_results if r['detected'])
    detection_rate = (detected / total * 100) if total > 0 else 0

    # By product
    products = {}
    for result in detection_results:
        for product in ['melatonin', 'smartphone', 'corecoin']:
            if product in result['run_id']:
                if product not in products:
                    products[product] = {'total': 0, 'detected': 0}
                products[product]['total'] += 1
                if result['detected']:
                    products[product]['detected'] += 1
                break

    # By error type
    error_types = {}
    for result in detection_results:
        et = result['error_type']
        if et not in error_types:
            error_types[et] = {'total': 0, 'detected': 0}
        error_types[et]['total'] += 1
        if result['detected']:
            error_types[et]['detected'] += 1

    # Missed errors
    missed = [r for r in detection_results if not r['detected']]

    # Generate report
    report = f"""# Glass Box Audit Validation Report

**Date:** {Path().resolve()}
**Configuration:**
- Extraction Model: {EXTRACTION_MODEL}
- NLI Model: {NLI_MODEL_NAME}
- Violation Threshold: {VIOLATION_THRESHOLD}

---

## Overall Detection Rate

**Total files:** {total}
**Detected:** {detected}/{total} ({detection_rate:.1f}%)
**Missed:** {len(missed)}/{total} ({100-detection_rate:.1f}%)

---

## Detection by Product

"""

    for product, stats in sorted(products.items()):
        rate = (stats['detected'] / stats['total'] * 100) if stats['total'] > 0 else 0
        status = "✅" if rate == 100 else "⚠️" if rate >= 80 else "❌"
        report += f"- **{product.capitalize()}:** {stats['detected']}/{stats['total']} ({rate:.0f}%) {status}\n"

    report += "\n---\n\n## Detection by Error Type\n\n"

    for error_type, stats in sorted(error_types.items()):
        rate = (stats['detected'] / stats['total'] * 100) if stats['total'] > 0 else 0
        report += f"- **{error_type}:** {stats['detected']}/{stats['total']} ({rate:.0f}%)\n"

    if missed:
        report += "\n---\n\n## Missed Errors\n\n"
        for result in missed:
            report += f"- **{result['run_id']}:** {result['ground_truth_error']} ({result['error_type']})\n"

    report += "\n---\n\n## Detailed Results\n\n"
    report += "| Run ID | Ground Truth Error | Detected | Matched Keywords | Confidence |\n"
    report += "|--------|-------------------|----------|------------------|------------|\n"

    for result in sorted(detection_results, key=lambda x: x['run_id']):
        status = "✅" if result['detected'] else "❌"
        keywords = ', '.join(result['matched_keywords']) if result['matched_keywords'] else '-'
        conf = f"{result['confidence']:.2f}" if result['confidence'] else '-'
        error_short = result['ground_truth_error'][:40] + '...' if len(result['ground_truth_error']) > 40 else result['ground_truth_error']
        report += f"| {result['run_id']} | {error_short} | {status} | {keywords} | {conf} |\n"

    # Save report
    report_path = output_dir / 'validation_report.md'
    report_path.write_text(report)
    logger.info(f"Generated validation report: {report_path}")


if __name__ == '__main__':
    main()
