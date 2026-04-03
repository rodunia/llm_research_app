"""
Dry-Run Randomizer for 1,620 Experimental Runs

Simulates full experimental pipeline WITHOUT API calls or file writes.
Tests randomization across 7 days × 3 time slots for temporal validity.

Usage:
    python scripts/test_randomizer_dry_run.py [--seed 42]
"""

import random
import itertools
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import csv
import yaml

# Import config
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import PRODUCTS, MATERIALS, TEMPS, ENGINES, REGION
from runner.utils import make_run_id


# ==================== CONFIGURATION ====================

TOTAL_REPS = 20  # Number of repetitions per unique condition
RANDOM_SEED = 42  # For reproducibility

# Time slot definitions
DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
TIME_SLOTS = {
    'morning': (8, 12),    # 8 AM - 12 PM
    'afternoon': (12, 17),  # 12 PM - 5 PM
    'evening': (17, 22)     # 5 PM - 10 PM
}

# Start date for scheduling (arbitrary, for timestamp generation)
START_DATE = datetime(2026, 3, 17)  # Monday, March 17, 2026

# Output paths
OUTPUT_CSV = Path("results/randomizer_dry_run_1620.csv")


# ==================== HELPER FUNCTIONS ====================

def load_product_yaml_safe(product_id: str) -> Tuple[bool, Dict, str]:
    """
    Safely load product YAML.

    Returns:
        (success: bool, yaml_data: dict, error_msg: str)
    """
    yaml_path = Path(f"products/{product_id}.yaml")

    if not yaml_path.exists():
        return False, {}, f"File not found: {yaml_path}"

    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return True, data, ""
    except Exception as e:
        return False, {}, f"Parse error: {str(e)}"


def render_prompt_safe(product_yaml: Dict, material_type: str) -> Tuple[bool, str, str]:
    """
    Safely render Jinja2 prompt.

    Returns:
        (success: bool, prompt_text: str, error_msg: str)
    """
    from jinja2 import Environment, FileSystemLoader, TemplateNotFound

    template_dir = Path("prompts")

    try:
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template(material_type)

        # Render with product context
        prompt_text = template.render(
            product=product_yaml,
            region=REGION
        )

        return True, prompt_text, ""

    except TemplateNotFound:
        return False, "", f"Template not found: {material_type}"
    except Exception as e:
        return False, "", f"Render error: {str(e)}"


def generate_random_timestamp(day_offset: int, time_slot: str) -> datetime:
    """
    Generate random timestamp within a specific day and time slot.

    Args:
        day_offset: Days from START_DATE (0-6 for week)
        time_slot: 'morning', 'afternoon', or 'evening'

    Returns:
        datetime object with randomized hour and minute
    """
    start_hour, end_hour = TIME_SLOTS[time_slot]

    # Random hour within slot
    hour = random.randint(start_hour, end_hour - 1)

    # Random minute
    minute = random.randint(0, 59)

    # Build timestamp
    scheduled_date = START_DATE + timedelta(days=day_offset)
    timestamp = scheduled_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

    return timestamp


# ==================== MAIN DRY-RUN LOGIC ====================

def generate_experimental_matrix() -> List[Dict]:
    """
    Generate full experimental matrix (1,620 runs).

    Returns:
        List of run configurations (dicts)
    """
    # Generate all unique conditions
    # 3 products × 3 materials × 3 temps × 3 engines = 81 unique conditions
    unique_conditions = list(itertools.product(
        PRODUCTS, MATERIALS, TEMPS, ENGINES
    ))

    print(f"Unique conditions: {len(unique_conditions)}")

    # Expand with repetitions (81 × 20 = 1,620)
    all_runs = []
    for product_id, material, temp, engine in unique_conditions:
        for rep in range(1, TOTAL_REPS + 1):
            all_runs.append({
                'product_id': product_id,
                'material_type': material,
                'engine': engine,
                'temperature': temp,
                'repetition': rep
            })

    print(f"Total runs: {len(all_runs)}")
    return all_runs


def assign_random_timeslots(runs: List[Dict], seed: int = RANDOM_SEED) -> List[Dict]:
    """
    Randomly assign each run to a day and time slot.

    Args:
        runs: List of run configurations
        seed: Random seed for reproducibility

    Returns:
        List of runs with assigned timestamps
    """
    random.seed(seed)

    # Generate all possible time slots (7 days × 3 times = 21 slots)
    all_slots = []
    for day_idx, day_name in enumerate(DAYS_OF_WEEK):
        for time_slot in TIME_SLOTS.keys():
            all_slots.append((day_idx, day_name, time_slot))

    print(f"Total time slots: {len(all_slots)}")

    # Assign runs to slots
    enriched_runs = []
    for run_idx, run in enumerate(runs, 1):
        # Randomly pick a slot
        day_idx, day_name, time_slot = random.choice(all_slots)

        # Generate random timestamp within that slot
        timestamp = generate_random_timestamp(day_idx, time_slot)

        # Enrich run with scheduling info
        run['run_order'] = run_idx
        run['scheduled_day_of_week'] = day_name
        run['scheduled_day_index'] = day_idx + 1  # 1-7
        run['is_weekend'] = day_name in ['Saturday', 'Sunday']
        run['scheduled_time_slot'] = time_slot
        run['scheduled_timestamp'] = timestamp
        run['scheduled_date'] = timestamp.strftime('%Y-%m-%d')
        run['hour'] = timestamp.hour
        run['minute'] = timestamp.minute

        enriched_runs.append(run)

    return enriched_runs


def simulate_pipeline(runs: List[Dict]) -> List[Dict]:
    """
    Simulate full pipeline: load YAMLs, render prompts, generate run_ids.

    NO API calls, NO file writes.

    Returns:
        List of runs with pipeline validation results
    """
    print("\nSimulating pipeline for each run...")
    print("=" * 70)

    results = []
    errors = []
    seen_run_ids = set()

    for idx, run in enumerate(runs, 1):
        product_id = run['product_id']
        material_type = run['material_type']

        # STEP 1: Load YAML
        yaml_ok, product_yaml, yaml_error = load_product_yaml_safe(product_id)

        if not yaml_ok:
            errors.append(f"Run {idx}: YAML error - {yaml_error}")
            run['yaml_loaded'] = False
            run['prompt_rendered'] = False
            run['prompt_length'] = 0
            run['run_id'] = f"ERROR_{idx}"
            run['error'] = yaml_error
            results.append(run)
            continue

        run['yaml_loaded'] = True

        # STEP 2: Render prompt
        prompt_ok, prompt_text, prompt_error = render_prompt_safe(product_yaml, material_type)

        if not prompt_ok:
            errors.append(f"Run {idx}: Prompt error - {prompt_error}")
            run['prompt_rendered'] = False
            run['prompt_length'] = 0
            run['run_id'] = f"ERROR_{idx}"
            run['error'] = prompt_error
            results.append(run)
            continue

        run['prompt_rendered'] = True
        run['prompt_length'] = len(prompt_text)

        # STEP 3: Generate run_id
        knobs = {
            'product_id': product_id,
            'material_type': material_type,
            'engine': run['engine'],
            'time_of_day_label': run['scheduled_time_slot'],
            'temperature_label': str(run['temperature']),
            'repetition_id': run['repetition'],
            'trap_flag': False
        }

        run_id = make_run_id(knobs, prompt_text)

        # Check collision
        if run_id in seen_run_ids:
            errors.append(f"Run {idx}: run_id collision - {run_id}")
            run['run_id'] = f"COLLISION_{run_id}"
            run['error'] = "run_id collision"
        else:
            seen_run_ids.add(run_id)
            run['run_id'] = run_id
            run['error'] = None

        results.append(run)

        # Progress indicator
        if idx % 100 == 0:
            print(f"  Processed {idx}/{len(runs)} runs...")

    print(f"  Processed {len(runs)}/{len(runs)} runs... DONE")
    print("=" * 70)

    # Print errors
    if errors:
        print(f"\n⚠️  ERRORS FOUND ({len(errors)}):")
        for err in errors[:10]:  # Show first 10
            print(f"  - {err}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")
    else:
        print("\n✅ No errors found!")

    return results


def save_results_to_csv(results: List[Dict], output_path: Path):
    """Save results to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        'run_id', 'run_order', 'product_id', 'material_type', 'engine',
        'temperature', 'repetition',
        'scheduled_day_of_week', 'scheduled_day_index', 'is_weekend',
        'scheduled_date', 'scheduled_time_slot', 'scheduled_timestamp',
        'hour', 'minute',
        'yaml_loaded', 'prompt_rendered', 'prompt_length', 'error'
    ]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\n💾 Results saved to: {output_path}")


def print_summary_stats(results: List[Dict]):
    """Print summary statistics."""
    total = len(results)

    # Count by day
    day_counts = {}
    for run in results:
        day = run['scheduled_day_of_week']
        day_counts[day] = day_counts.get(day, 0) + 1

    # Count by time slot
    time_counts = {}
    for run in results:
        slot = run['scheduled_time_slot']
        time_counts[slot] = time_counts.get(slot, 0) + 1

    # Count by product
    product_counts = {}
    for run in results:
        prod = run['product_id']
        product_counts[prod] = product_counts.get(prod, 0) + 1

    # Count by engine
    engine_counts = {}
    for run in results:
        eng = run['engine']
        engine_counts[eng] = engine_counts.get(eng, 0) + 1

    # Count weekday vs weekend
    weekday_count = sum(1 for r in results if not r['is_weekend'])
    weekend_count = sum(1 for r in results if r['is_weekend'])

    # Count errors
    error_count = sum(1 for r in results if r['error'] is not None)

    print("\n" + "=" * 70)
    print("SUMMARY STATISTICS")
    print("=" * 70)

    print(f"\nTotal runs: {total}")
    print(f"  ✅ Successful: {total - error_count}")
    print(f"  ❌ Errors: {error_count}")

    print(f"\n📅 Distribution by Day of Week:")
    for day in DAYS_OF_WEEK:
        count = day_counts.get(day, 0)
        expected = total / 7
        deviation = ((count - expected) / expected) * 100 if expected > 0 else 0
        print(f"  {day:10s}: {count:4d} runs (expected: {expected:.1f}, deviation: {deviation:+.1f}%)")

    print(f"\n⏰ Distribution by Time Slot:")
    for slot in TIME_SLOTS.keys():
        count = time_counts.get(slot, 0)
        expected = total / 3
        deviation = ((count - expected) / expected) * 100 if expected > 0 else 0
        print(f"  {slot:10s}: {count:4d} runs (expected: {expected:.1f}, deviation: {deviation:+.1f}%)")

    print(f"\n📊 Weekday vs Weekend:")
    print(f"  Weekday:  {weekday_count:4d} runs ({weekday_count/total*100:.1f}%)")
    print(f"  Weekend:  {weekend_count:4d} runs ({weekend_count/total*100:.1f}%)")

    print(f"\n🔬 Distribution by Product:")
    for prod in PRODUCTS:
        count = product_counts.get(prod, 0)
        expected = total / len(PRODUCTS)
        print(f"  {prod:25s}: {count:4d} runs (expected: {expected:.1f})")

    print(f"\n🤖 Distribution by Engine:")
    for eng in ENGINES:
        count = engine_counts.get(eng, 0)
        expected = total / len(ENGINES)
        print(f"  {eng:10s}: {count:4d} runs (expected: {expected:.1f})")

    print("\n" + "=" * 70)


# ==================== MAIN ====================

def main(seed: int = RANDOM_SEED):
    """Run dry-run randomizer test."""
    print("=" * 70)
    print("DRY-RUN RANDOMIZER TEST (1,620 RUNS)")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  Products: {len(PRODUCTS)}")
    print(f"  Materials: {len(MATERIALS)}")
    print(f"  Temperatures: {len(TEMPS)}")
    print(f"  Engines: {len(ENGINES)}")
    print(f"  Repetitions per condition: {TOTAL_REPS}")
    print(f"  Random seed: {seed}")
    print(f"  Days: {len(DAYS_OF_WEEK)} (full week)")
    print(f"  Time slots per day: {len(TIME_SLOTS)}")
    print(f"  Total time slots: {len(DAYS_OF_WEEK) * len(TIME_SLOTS)}")

    # Step 1: Generate experimental matrix
    print("\n" + "=" * 70)
    print("STEP 1: Generating experimental matrix...")
    print("=" * 70)
    runs = generate_experimental_matrix()

    # Step 2: Assign random timeslots
    print("\n" + "=" * 70)
    print("STEP 2: Assigning random time slots...")
    print("=" * 70)
    runs = assign_random_timeslots(runs, seed=seed)

    # Step 3: Simulate pipeline
    print("\n" + "=" * 70)
    print("STEP 3: Simulating pipeline (NO API calls)...")
    print("=" * 70)
    results = simulate_pipeline(runs)

    # Step 4: Save results
    print("\n" + "=" * 70)
    print("STEP 4: Saving results...")
    print("=" * 70)
    save_results_to_csv(results, OUTPUT_CSV)

    # Step 5: Print summary
    print_summary_stats(results)

    print("\n✅ Dry-run complete!")
    print(f"\nNext steps:")
    print(f"  1. Run: python scripts/analyze_randomizer_distribution.py")
    print(f"  2. Run: python scripts/export_randomizer_for_review.py")
    print(f"  3. Review plots in results/randomizer_plots/")
    print(f"  4. Review validation report in results/randomizer_validation_report.md")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Dry-run randomizer test")
    parser.add_argument('--seed', type=int, default=RANDOM_SEED, help='Random seed')
    args = parser.parse_args()

    main(seed=args.seed)
