#!/usr/bin/env python3
"""
Diagnose Google Gemini token limit issues

Analyzes experiments.csv to identify Gemini runs with token-related failures,
high token counts, or content filtering.

Usage:
  python analysis/diagnose_gemini_tokens.py
  python analysis/diagnose_gemini_tokens.py --engine google
  python analysis/diagnose_gemini_tokens.py --show-prompts
"""

import csv
import argparse
from pathlib import Path
from typing import List, Dict

# Paths
RESULTS_DIR = Path(__file__).parent.parent / "results"
EXPERIMENTS_CSV = RESULTS_DIR / "experiments.csv"
OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"
PROMPTS_DIR = OUTPUTS_DIR / "prompts"

# Google Gemini token limits (as of 2024)
# gemini-1.5-flash: 1M input, 8K output
# gemini-1.5-pro: 2M input, 8K output
GEMINI_INPUT_LIMIT = 1_000_000  # Conservative estimate
GEMINI_OUTPUT_LIMIT = 8_192


def load_experiments(engine_filter: str = None) -> List[Dict]:
    """Load experiments from CSV with optional engine filter."""
    if not EXPERIMENTS_CSV.exists():
        raise FileNotFoundError(f"experiments.csv not found: {EXPERIMENTS_CSV}")

    experiments = []
    with open(EXPERIMENTS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Filter by engine if specified
            if engine_filter and row.get('engine') != engine_filter:
                continue
            experiments.append(row)

    return experiments


def analyze_token_usage(experiments: List[Dict]) -> Dict:
    """Analyze token usage patterns and identify potential issues."""

    results = {
        'total_runs': len(experiments),
        'by_status': {},
        'by_error_type': {},
        'high_token_runs': [],
        'content_filtered': [],
        'token_stats': {
            'prompt_tokens': [],
            'completion_tokens': [],
            'total_tokens': []
        }
    }

    for exp in experiments:
        status = exp.get('status', 'unknown')
        error_type = exp.get('error_type', 'none')

        # Count by status
        results['by_status'][status] = results['by_status'].get(status, 0) + 1

        # Count by error type
        if error_type != 'none':
            results['by_error_type'][error_type] = results['by_error_type'].get(error_type, 0) + 1

        # Check for content filtering
        if exp.get('content_filter_triggered', '').lower() == 'true':
            results['content_filtered'].append({
                'run_id': exp['run_id'],
                'product_id': exp.get('product_id', 'unknown'),
                'material_type': exp.get('material_type', 'unknown'),
                'finish_reason': exp.get('finish_reason', 'unknown'),
                'prompt_tokens': int(exp.get('prompt_tokens', 0) or 0),
                'completion_tokens': int(exp.get('completion_tokens', 0) or 0),
            })

        # Track token usage
        try:
            prompt_tokens = int(exp.get('prompt_tokens', 0) or 0)
            completion_tokens = int(exp.get('completion_tokens', 0) or 0)
            total_tokens = int(exp.get('total_tokens', 0) or 0)

            results['token_stats']['prompt_tokens'].append(prompt_tokens)
            results['token_stats']['completion_tokens'].append(completion_tokens)
            results['token_stats']['total_tokens'].append(total_tokens)

            # Flag high token runs (>90% of limit)
            if prompt_tokens > 0.9 * GEMINI_INPUT_LIMIT or completion_tokens > 0.9 * GEMINI_OUTPUT_LIMIT:
                results['high_token_runs'].append({
                    'run_id': exp['run_id'],
                    'product_id': exp.get('product_id', 'unknown'),
                    'material_type': exp.get('material_type', 'unknown'),
                    'prompt_tokens': prompt_tokens,
                    'completion_tokens': completion_tokens,
                    'total_tokens': total_tokens,
                    'status': status,
                    'error_type': error_type,
                })
        except (ValueError, TypeError):
            pass

    return results


def calculate_stats(values: List[int]) -> Dict:
    """Calculate basic statistics for a list of values."""
    if not values:
        return {'min': 0, 'max': 0, 'mean': 0, 'median': 0}

    values = sorted(values)
    return {
        'min': values[0],
        'max': values[-1],
        'mean': sum(values) / len(values),
        'median': values[len(values) // 2],
    }


def print_report(results: Dict, engine: str):
    """Print diagnostic report."""

    print("=" * 80)
    print(f"GOOGLE GEMINI TOKEN DIAGNOSTICS - {engine.upper()}")
    print("=" * 80)
    print()

    # Overall stats
    print(f"Total runs analyzed:  {results['total_runs']}")
    print()

    # Status breakdown
    print("Status Breakdown:")
    for status, count in sorted(results['by_status'].items()):
        pct = count / results['total_runs'] * 100
        print(f"  {status:12s}: {count:4d} ({pct:5.1f}%)")
    print()

    # Error type breakdown
    if results['by_error_type']:
        print("Error Type Breakdown:")
        for error_type, count in sorted(results['by_error_type'].items()):
            print(f"  {error_type:20s}: {count:4d}")
        print()
    else:
        print("✓ No errors detected\n")

    # Token usage statistics
    print("Token Usage Statistics:")
    print()

    token_types = [
        ('Prompt Tokens', 'prompt_tokens', GEMINI_INPUT_LIMIT),
        ('Completion Tokens', 'completion_tokens', GEMINI_OUTPUT_LIMIT),
        ('Total Tokens', 'total_tokens', GEMINI_INPUT_LIMIT + GEMINI_OUTPUT_LIMIT),
    ]

    for label, key, limit in token_types:
        stats = calculate_stats(results['token_stats'][key])
        print(f"  {label}:")
        print(f"    Min:    {stats['min']:8,} tokens")
        print(f"    Max:    {stats['max']:8,} tokens ({stats['max']/limit*100:5.1f}% of limit)")
        print(f"    Mean:   {stats['mean']:8,.0f} tokens")
        print(f"    Median: {stats['median']:8,} tokens")
        print(f"    Limit:  {limit:8,} tokens")
        print()

    # High token runs
    if results['high_token_runs']:
        print("⚠️  HIGH TOKEN USAGE (>90% of limit):")
        print()
        for run in results['high_token_runs']:
            print(f"  Run ID: {run['run_id'][:12]}...")
            print(f"    Product:    {run['product_id']}")
            print(f"    Material:   {run['material_type']}")
            print(f"    Prompt:     {run['prompt_tokens']:,} tokens ({run['prompt_tokens']/GEMINI_INPUT_LIMIT*100:.1f}%)")
            print(f"    Completion: {run['completion_tokens']:,} tokens ({run['completion_tokens']/GEMINI_OUTPUT_LIMIT*100:.1f}%)")
            print(f"    Status:     {run['status']}")
            if run['error_type'] != 'none':
                print(f"    Error:      {run['error_type']}")
            print()
    else:
        print("✓ No high token usage detected (all runs <90% of limit)")
        print()

    # Content filtered runs
    if results['content_filtered']:
        print(f"⚠️  CONTENT FILTERED ({len(results['content_filtered'])} runs):")
        print()
        for run in results['content_filtered'][:10]:  # Show first 10
            print(f"  {run['run_id'][:12]}... | {run['product_id']:20s} | {run['material_type']:20s} | {run['finish_reason']}")

        if len(results['content_filtered']) > 10:
            print(f"  ... and {len(results['content_filtered']) - 10} more")
        print()
    else:
        print("✓ No content filtering detected")
        print()

    print("=" * 80)


def show_prompt_sizes(experiments: List[Dict], top_n: int = 10):
    """Show prompts with largest token counts."""

    runs_with_tokens = []
    for exp in experiments:
        try:
            prompt_tokens = int(exp.get('prompt_tokens', 0) or 0)
            if prompt_tokens > 0:
                prompt_path = PROMPTS_DIR / f"{exp['run_id']}.txt"
                prompt_size = 0
                if prompt_path.exists():
                    prompt_size = len(prompt_path.read_text(encoding='utf-8'))

                runs_with_tokens.append({
                    'run_id': exp['run_id'],
                    'product_id': exp.get('product_id', 'unknown'),
                    'material_type': exp.get('material_type', 'unknown'),
                    'prompt_tokens': prompt_tokens,
                    'prompt_chars': prompt_size,
                    'chars_per_token': prompt_size / prompt_tokens if prompt_tokens > 0 else 0,
                })
        except (ValueError, TypeError):
            pass

    # Sort by token count
    runs_with_tokens.sort(key=lambda x: x['prompt_tokens'], reverse=True)

    print("=" * 80)
    print(f"TOP {top_n} LARGEST PROMPTS (by token count)")
    print("=" * 80)
    print()

    for i, run in enumerate(runs_with_tokens[:top_n], 1):
        print(f"{i}. {run['run_id'][:12]}...")
        print(f"   Product:        {run['product_id']}")
        print(f"   Material:       {run['material_type']}")
        print(f"   Prompt Tokens:  {run['prompt_tokens']:,}")
        print(f"   Prompt Chars:   {run['prompt_chars']:,}")
        print(f"   Chars/Token:    {run['chars_per_token']:.1f}")
        print(f"   % of Limit:     {run['prompt_tokens']/GEMINI_INPUT_LIMIT*100:.2f}%")
        print()


def main():
    parser = argparse.ArgumentParser(description='Diagnose Google Gemini token issues')
    parser.add_argument(
        '--engine',
        default='google',
        help='Engine to analyze (default: google)'
    )
    parser.add_argument(
        '--show-prompts',
        action='store_true',
        help='Show top 10 largest prompts by token count'
    )
    args = parser.parse_args()

    # Load experiments
    experiments = load_experiments(engine_filter=args.engine)

    if not experiments:
        print(f"No experiments found for engine: {args.engine}")
        return

    # Analyze token usage
    results = analyze_token_usage(experiments)

    # Print report
    print_report(results, args.engine)

    # Show prompt sizes if requested
    if args.show_prompts:
        show_prompt_sizes(experiments, top_n=10)


if __name__ == "__main__":
    main()
