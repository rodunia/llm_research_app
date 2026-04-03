"""
Test randomizer with multiple seeds to verify balance and detect systematic biases.

Usage:
    python scripts/test_randomizer_seeds.py --num-seeds 10
"""

import subprocess
import re
import sys
from pathlib import Path
from collections import defaultdict
import statistics

def run_randomizer(seed: int) -> dict:
    """Run randomizer with specific seed and extract statistics."""

    # Run the randomizer
    result = subprocess.run(
        ['python', 'scripts/test_randomizer_stratified.py', '--seed', str(seed)],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )

    output = result.stdout

    # Parse time slot distribution
    time_pattern = r'(\w+)\s+:\s+(\d+) runs \(expected: ([\d.]+), deviation: ([+\-][\d.]+)%\)'
    time_matches = re.findall(time_pattern, output)

    time_slots = {}
    for slot, count, expected, deviation in time_matches:
        time_slots[slot] = {
            'count': int(count),
            'expected': float(expected),
            'deviation': float(deviation)
        }

    # Parse engine distribution
    engine_pattern = r'(openai|google|mistral)\s+:\s+(\d+) runs'
    engine_matches = re.findall(engine_pattern, output)

    engines = {}
    for engine, count in engine_matches:
        engines[engine] = int(count)

    # Parse day distribution
    day_pattern = r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+:\s+(\d+) runs'
    day_matches = re.findall(day_pattern, output)

    days = {}
    for day, count in day_matches:
        days[day] = int(count)

    return {
        'seed': seed,
        'time_slots': time_slots,
        'engines': engines,
        'days': days
    }


def analyze_results(results: list) -> dict:
    """Analyze results across multiple seeds."""

    # Collect time slot deviations
    morning_devs = [r['time_slots']['morning']['deviation'] for r in results]
    afternoon_devs = [r['time_slots']['afternoon']['deviation'] for r in results]
    evening_devs = [r['time_slots']['evening']['deviation'] for r in results]

    # Collect engine counts
    openai_counts = [r['engines']['openai'] for r in results]
    google_counts = [r['engines']['google'] for r in results]
    mistral_counts = [r['engines']['mistral'] for r in results]

    # Collect day counts
    monday_counts = [r['days']['Monday'] for r in results]
    saturday_counts = [r['days']['Saturday'] for r in results]
    sunday_counts = [r['days']['Sunday'] for r in results]

    return {
        'time_slots': {
            'morning': {
                'mean_deviation': statistics.mean(morning_devs),
                'stdev_deviation': statistics.stdev(morning_devs) if len(morning_devs) > 1 else 0,
                'min_deviation': min(morning_devs),
                'max_deviation': max(morning_devs)
            },
            'afternoon': {
                'mean_deviation': statistics.mean(afternoon_devs),
                'stdev_deviation': statistics.stdev(afternoon_devs) if len(afternoon_devs) > 1 else 0,
                'min_deviation': min(afternoon_devs),
                'max_deviation': max(afternoon_devs)
            },
            'evening': {
                'mean_deviation': statistics.mean(evening_devs),
                'stdev_deviation': statistics.stdev(evening_devs) if len(evening_devs) > 1 else 0,
                'min_deviation': min(evening_devs),
                'max_deviation': max(evening_devs)
            }
        },
        'engines': {
            'openai': {
                'mean': statistics.mean(openai_counts),
                'stdev': statistics.stdev(openai_counts) if len(openai_counts) > 1 else 0,
                'all_equal': len(set(openai_counts)) == 1,
                'target': 540
            },
            'google': {
                'mean': statistics.mean(google_counts),
                'stdev': statistics.stdev(google_counts) if len(google_counts) > 1 else 0,
                'all_equal': len(set(google_counts)) == 1,
                'target': 540
            },
            'mistral': {
                'mean': statistics.mean(mistral_counts),
                'stdev': statistics.stdev(mistral_counts) if len(mistral_counts) > 1 else 0,
                'all_equal': len(set(mistral_counts)) == 1,
                'target': 540
            }
        },
        'days': {
            'monday': statistics.mean(monday_counts),
            'saturday': statistics.mean(saturday_counts),
            'sunday': statistics.mean(sunday_counts)
        }
    }


def print_report(analysis: dict, num_seeds: int):
    """Print analysis report."""

    print("\n" + "=" * 80)
    print(f"RANDOMIZER MULTI-SEED ANALYSIS ({num_seeds} seeds)")
    print("=" * 80)

    print("\n### TIME SLOT BALANCE")
    print(f"{'Slot':<12} {'Mean Dev':<12} {'StDev':<12} {'Range':<20} {'Status'}")
    print("-" * 80)

    for slot in ['morning', 'afternoon', 'evening']:
        stats = analysis['time_slots'][slot]
        mean_dev = stats['mean_deviation']
        stdev = stats['stdev_deviation']
        min_dev = stats['min_deviation']
        max_dev = stats['max_deviation']

        # Check if systematic bias (mean significantly different from 0)
        if abs(mean_dev) < 1.0:
            status = "✅ BALANCED"
        elif abs(mean_dev) < 3.0:
            status = "⚠️  SLIGHT BIAS"
        else:
            status = "❌ SYSTEMATIC BIAS"

        print(f"{slot:<12} {mean_dev:>+6.2f}%     {stdev:>6.2f}%     [{min_dev:>+6.2f}%, {max_dev:>+6.2f}%]  {status}")

    print("\n### ENGINE BALANCE")
    print(f"{'Engine':<12} {'Mean Count':<12} {'StDev':<12} {'Target':<12} {'Status'}")
    print("-" * 80)

    for engine in ['openai', 'google', 'mistral']:
        stats = analysis['engines'][engine]
        mean_count = stats['mean']
        stdev = stats['stdev']
        target = stats['target']
        all_equal = stats['all_equal']

        if all_equal and mean_count == target:
            status = "✅ PERFECT"
        elif abs(mean_count - target) < 1.0:
            status = "✅ EXCELLENT"
        else:
            status = "⚠️  VARIANCE"

        print(f"{engine:<12} {mean_count:>6.1f}       {stdev:>6.2f}       {target:<12} {status}")

    print("\n### DAY BALANCE")
    print(f"Monday avg:    {analysis['days']['monday']:.1f} runs")
    print(f"Saturday avg:  {analysis['days']['saturday']:.1f} runs")
    print(f"Sunday avg:    {analysis['days']['sunday']:.1f} runs")

    print("\n" + "=" * 80)
    print("INTERPRETATION")
    print("=" * 80)

    # Check for systematic time slot bias
    time_biases = [abs(analysis['time_slots'][s]['mean_deviation']) for s in ['morning', 'afternoon', 'evening']]
    max_time_bias = max(time_biases)

    if max_time_bias < 1.0:
        print("\n✅ TIME SLOTS: No systematic bias detected")
        print("   Random variance is within acceptable range (±1%)")
    elif max_time_bias < 3.0:
        print(f"\n⚠️  TIME SLOTS: Slight bias detected (max {max_time_bias:.2f}%)")
        print("   Variance is acceptable for stratified randomization")
    else:
        print(f"\n❌ TIME SLOTS: Systematic bias detected (max {max_time_bias:.2f}%)")
        print("   Time slot assignment may have a bug")

    # Check engine balance
    engine_perfect = all(analysis['engines'][e]['all_equal'] for e in ['openai', 'google', 'mistral'])

    if engine_perfect:
        print("\n✅ ENGINES: Perfect balance across all seeds")
        print("   Engine balancing algorithm working correctly")
    else:
        print("\n⚠️  ENGINES: Some variance detected across seeds")
        print("   Check if engine balancing is seed-dependent")

    print("\n" + "=" * 80)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Test randomizer with multiple seeds")
    parser.add_argument('--num-seeds', type=int, default=10, help='Number of seeds to test')
    parser.add_argument('--start-seed', type=int, default=1, help='Starting seed value')
    args = parser.parse_args()

    print(f"Testing randomizer with {args.num_seeds} seeds...")
    print("This may take several minutes...\n")

    results = []
    for i in range(args.num_seeds):
        seed = args.start_seed + i
        print(f"Running seed {seed}... ", end='', flush=True)

        try:
            result = run_randomizer(seed)
            results.append(result)
            print("✅")
        except Exception as e:
            print(f"❌ Error: {e}")

    if not results:
        print("No successful runs!")
        sys.exit(1)

    # Analyze results
    analysis = analyze_results(results)

    # Print report
    print_report(analysis, len(results))


if __name__ == "__main__":
    main()
