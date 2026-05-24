#!/usr/bin/env python3
"""
Real-time Experiment Health Monitor

Checks experiment progress and health during temporal execution.
Can be run anytime during the 7-day experiment window.

Features:
- Overall progress (completed/pending/failed)
- Token usage statistics (detect truncation early)
- Completion rates by engine/product/temperature
- Recent failures and error types
- Token limit warnings (>90% of max_tokens)

Usage:
  python scripts/monitor_experiment.py              # Full report
  python scripts/monitor_experiment.py --engine google  # Google only
  python scripts/monitor_experiment.py --watch      # Auto-refresh every 60s
"""

import csv
import argparse
import time
import os
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict
from typing import Dict, List

EXPERIMENTS_CSV = Path("results/experiments.csv")
GEMINI_OUTPUT_LIMIT = 8192  # Gemini Flash hard limit


def clear_screen():
    """Clear terminal screen."""
    os.system('clear' if os.name == 'posix' else 'cls')


def load_experiments() -> List[Dict]:
    """Load experiments.csv."""
    if not EXPERIMENTS_CSV.exists():
        print(f"❌ Error: {EXPERIMENTS_CSV} not found")
        return []

    with open(EXPERIMENTS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


def analyze_progress(experiments: List[Dict], engine_filter: str = None) -> Dict:
    """Analyze overall progress."""
    if engine_filter:
        experiments = [e for e in experiments if e.get('engine') == engine_filter]

    total = len(experiments)
    if total == 0:
        return {}

    status_counts = Counter(e.get('status', 'unknown') for e in experiments)

    completed = status_counts.get('completed', 0)
    pending = status_counts.get('pending', 0)
    failed = status_counts.get('failed', 0)

    progress_pct = (completed / total * 100) if total > 0 else 0

    return {
        'total': total,
        'completed': completed,
        'pending': pending,
        'failed': failed,
        'progress_pct': progress_pct,
        'status_counts': status_counts,
    }


def analyze_tokens(experiments: List[Dict], engine_filter: str = None) -> Dict:
    """Analyze token usage and detect truncation."""
    if engine_filter:
        experiments = [e for e in experiments if e.get('engine') == engine_filter]

    completed = [e for e in experiments if e.get('status') == 'completed']

    if not completed:
        return {'completed_count': 0}

    # Extract token counts
    prompt_tokens = []
    completion_tokens = []
    max_tokens_used = []

    for exp in completed:
        try:
            pt = int(exp.get('prompt_tokens', 0))
            ct = int(exp.get('completion_tokens', 0))
            mt = int(exp.get('max_tokens', 20000))

            prompt_tokens.append(pt)
            completion_tokens.append(ct)
            max_tokens_used.append(mt)
        except (ValueError, TypeError):
            continue

    if not completion_tokens:
        return {'completed_count': len(completed), 'no_token_data': True}

    # Detect MAX_TOKENS finish reason
    max_tokens_count = sum(1 for e in completed if e.get('finish_reason') == 'MAX_TOKENS')

    # Flag high token usage (>90% of limit for Gemini)
    high_token_runs = []
    for exp in completed:
        try:
            ct = int(exp.get('completion_tokens', 0))
            engine = exp.get('engine')

            if engine == 'google' and ct > GEMINI_OUTPUT_LIMIT * 0.9:
                high_token_runs.append({
                    'run_id': exp['run_id'][:16],
                    'product': exp.get('product_id'),
                    'tokens': ct,
                    'pct': ct / GEMINI_OUTPUT_LIMIT * 100
                })
        except (ValueError, TypeError):
            continue

    return {
        'completed_count': len(completed),
        'prompt_tokens': {
            'min': min(prompt_tokens),
            'max': max(prompt_tokens),
            'mean': sum(prompt_tokens) / len(prompt_tokens),
        },
        'completion_tokens': {
            'min': min(completion_tokens),
            'max': max(completion_tokens),
            'mean': sum(completion_tokens) / len(completion_tokens),
        },
        'max_tokens_truncated': max_tokens_count,
        'high_token_runs': high_token_runs,
    }


def analyze_by_dimension(experiments: List[Dict], dimension: str, engine_filter: str = None) -> Dict:
    """Analyze completion rates by dimension (engine, product, temperature)."""
    if engine_filter:
        experiments = [e for e in experiments if e.get('engine') == engine_filter]

    breakdown = defaultdict(lambda: {'total': 0, 'completed': 0, 'failed': 0})

    for exp in experiments:
        key = exp.get(dimension, 'unknown')
        breakdown[key]['total'] += 1

        status = exp.get('status')
        if status == 'completed':
            breakdown[key]['completed'] += 1
        elif status == 'failed':
            breakdown[key]['failed'] += 1

    # Calculate completion rates
    for key in breakdown:
        total = breakdown[key]['total']
        completed = breakdown[key]['completed']
        breakdown[key]['completion_rate'] = (completed / total * 100) if total > 0 else 0

    return dict(breakdown)


def analyze_failures(experiments: List[Dict], engine_filter: str = None, limit: int = 10) -> List[Dict]:
    """Analyze recent failures."""
    if engine_filter:
        experiments = [e for e in experiments if e.get('engine') == engine_filter]

    failed = [e for e in experiments if e.get('status') == 'failed']

    # Sort by completed_at (most recent first)
    failed.sort(key=lambda x: x.get('completed_at', ''), reverse=True)

    recent_failures = []
    for exp in failed[:limit]:
        recent_failures.append({
            'run_id': exp['run_id'][:16],
            'product': exp.get('product_id', 'unknown'),
            'engine': exp.get('engine', 'unknown'),
            'error_type': exp.get('error_type', 'unknown'),
            'completed_at': exp.get('completed_at', 'unknown'),
        })

    # Count error types
    error_types = Counter(e.get('error_type', 'unknown') for e in failed)

    return {
        'count': len(failed),
        'recent': recent_failures,
        'error_types': dict(error_types),
    }


def print_report(experiments: List[Dict], engine_filter: str = None):
    """Print comprehensive health report."""
    print("\n" + "=" * 80)
    print("EXPERIMENT HEALTH MONITOR")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if engine_filter:
        print(f"Filter: engine={engine_filter}")

    print()

    # Overall Progress
    progress = analyze_progress(experiments, engine_filter)

    if not progress:
        print("❌ No experiments found")
        return

    print("📊 OVERALL PROGRESS")
    print("-" * 80)
    print(f"Total runs:      {progress['total']:,}")
    print(f"Completed:       {progress['completed']:,} ({progress['progress_pct']:.1f}%)")
    print(f"Pending:         {progress['pending']:,}")
    print(f"Failed:          {progress['failed']:,}")
    print()

    # Progress bar
    bar_width = 50
    completed_width = int(progress['progress_pct'] / 100 * bar_width)
    bar = "█" * completed_width + "░" * (bar_width - completed_width)
    print(f"[{bar}] {progress['progress_pct']:.1f}%")
    print()

    # Token Analysis
    print("🪙 TOKEN USAGE")
    print("-" * 80)
    token_stats = analyze_tokens(experiments, engine_filter)

    if token_stats.get('no_token_data'):
        print("⚠️  No token data available yet")
    elif token_stats['completed_count'] == 0:
        print("⚠️  No completed runs yet")
    else:
        print(f"Completed runs analyzed: {token_stats['completed_count']}")
        print()

        print("Prompt tokens:")
        print(f"  Min:  {token_stats['prompt_tokens']['min']:,}")
        print(f"  Max:  {token_stats['prompt_tokens']['max']:,}")
        print(f"  Mean: {token_stats['prompt_tokens']['mean']:.0f}")
        print()

        print("Completion tokens:")
        print(f"  Min:  {token_stats['completion_tokens']['min']:,}")
        print(f"  Max:  {token_stats['completion_tokens']['max']:,}")
        print(f"  Mean: {token_stats['completion_tokens']['mean']:.0f}")
        print()

        # Truncation warning
        if token_stats['max_tokens_truncated'] > 0:
            print(f"⚠️  WARNING: {token_stats['max_tokens_truncated']} runs hit MAX_TOKENS")
        else:
            print("✅ No MAX_TOKENS truncation detected")

        # High token usage warning
        if token_stats['high_token_runs']:
            print()
            print(f"⚠️  WARNING: {len(token_stats['high_token_runs'])} runs used >90% of Gemini limit:")
            for run in token_stats['high_token_runs'][:5]:
                print(f"  {run['run_id']}... | {run['product']} | {run['tokens']} tokens ({run['pct']:.1f}%)")

    print()

    # Completion by Engine
    print("🤖 COMPLETION BY ENGINE")
    print("-" * 80)
    engine_breakdown = analyze_by_dimension(experiments, 'engine', engine_filter)

    for engine, stats in sorted(engine_breakdown.items()):
        rate = stats['completion_rate']
        status = "✅" if rate > 90 else "⚠️" if rate > 50 else "❌"
        print(f"{status} {engine:10s}: {stats['completed']:4d}/{stats['total']:4d} ({rate:5.1f}%)  [failed: {stats['failed']}]")

    print()

    # Completion by Product
    print("📦 COMPLETION BY PRODUCT")
    print("-" * 80)
    product_breakdown = analyze_by_dimension(experiments, 'product_id', engine_filter)

    for product, stats in sorted(product_breakdown.items()):
        rate = stats['completion_rate']
        status = "✅" if rate > 90 else "⚠️" if rate > 50 else "❌"
        print(f"{status} {product:25s}: {stats['completed']:4d}/{stats['total']:4d} ({rate:5.1f}%)")

    print()

    # Recent Failures
    failures = analyze_failures(experiments, engine_filter, limit=10)

    if failures['count'] > 0:
        print("❌ RECENT FAILURES")
        print("-" * 80)
        print(f"Total failed: {failures['count']}")
        print()

        print("Error types:")
        for error_type, count in sorted(failures['error_types'].items(), key=lambda x: -x[1]):
            print(f"  {error_type:20s}: {count:4d}")
        print()

        print("Recent failures (last 10):")
        for fail in failures['recent']:
            print(f"  {fail['run_id']}... | {fail['engine']:8s} | {fail['product']:25s} | {fail['error_type']}")
    else:
        print("✅ NO FAILURES")
        print("-" * 80)
        print("All runs completed successfully!")

    print()
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description='Monitor experiment health')
    parser.add_argument('--engine', type=str, help='Filter by engine (openai/google/mistral)')
    parser.add_argument('--watch', action='store_true', help='Auto-refresh every 60 seconds')
    parser.add_argument('--interval', type=int, default=60, help='Refresh interval in seconds (default: 60)')
    args = parser.parse_args()

    try:
        while True:
            if args.watch:
                clear_screen()

            experiments = load_experiments()

            if not experiments:
                print("❌ Could not load experiments.csv")
                break

            print_report(experiments, engine_filter=args.engine)

            if not args.watch:
                break

            print(f"\n🔄 Auto-refreshing every {args.interval}s... (Ctrl+C to stop)")
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n\n✋ Monitoring stopped")


if __name__ == "__main__":
    main()
