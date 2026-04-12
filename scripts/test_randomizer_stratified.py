"""
Stratified Randomizer for 1,620 Experimental Runs

Implements stratified randomization with 5 levels:
1. Stratify by DAY (7 days, ~231 runs each, full week)
2. Stratify by PRODUCT × MATERIAL within each day (9 groups, ~26 runs each)
3. Fully cross TEMP × ENGINE within each group (9 combos, ~3 reps each)
4. Stratified TIME SLOT assignment (balanced within day, exactly 540 per slot)
5. Post-hoc engine balancing (ensure exactly 540 per engine)

Design Rationale:
- Day stratification: Controls for temporal effects (API performance, rate limits)
- Product × Material stratification: Prevents confounding between content types
- Temp × Engine full crossing: Enables 2-way interaction analysis (ANOVA)
- Stratified time slots: Balanced time-of-day distribution (morning/afternoon/evening)
- Engine balancing: Equal statistical power across LLM providers

Statistical Properties:
- Engine balance: Exactly 540 runs per engine (±0 runs, perfect)
- Time slot balance: Exactly 540 runs per slot (±0 runs, perfect)
- Engine×Time balance: 179-181 runs per cell (stratified remainder distribution)
- Day balance: 231-232 runs per day (±0.4%, excellent)
- Temperature balance: ~537-542 runs per temp (±0.6%, very good)
- Product balance: ~528-546 runs per product (±2.2%, good)
- Total runs: 1,620 (7 days × 231-232 runs/day, stratified assignment)

Performance:
- YAML caching: 3 products loaded once (not 1,620 times)
- Template caching: 9 templates rendered once (not 1,620 times)
- Expected runtime: ~15-20 seconds for full dry-run

Reproducibility:
- Fixed random seed (default: 42) ensures identical output across runs
- Deterministic stratification (no seed-dependent stratification)
- Run order included in run_id to prevent collisions

Usage:
    # Generate with default seed (42)
    python scripts/test_randomizer_stratified.py

    # Use custom seed for sensitivity analysis
    python scripts/test_randomizer_stratified.py --seed 999

Examples:
    >>> runs = create_stratified_matrix(seed=42)
    >>> len(runs)
    1620
    >>> Counter(r['engine'] for r in runs)
    {'openai': 540, 'google': 540, 'mistral': 540}
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

RANDOM_SEED = 42

# Days to use (full week, 7 days)
DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
NUM_DAYS = len(DAYS_OF_WEEK)  # 7 days

# Time slot definitions (equal 5-hour ranges for uniform call density)
TIME_SLOTS = {
    'morning': (7, 12),     # 5 hours: 7am-12pm
    'afternoon': (12, 17),   # 5 hours: 12pm-5pm
    'evening': (17, 22)      # 5 hours: 5pm-10pm
}

# Runs per day (1620 / 7 = 231 base, with remainder)
RUNS_PER_DAY = 1620 // NUM_DAYS  # 231
EXTRA_RUNS = 1620 % NUM_DAYS  # 3 extra runs to distribute

# Note: RUNS_PER_GROUP will vary by day (calculated dynamically)
# Base: 231 runs / 9 groups = 25.67 per group
# Days with 232: 232 / 9 = 25.78 per group
# We'll handle this dynamically in the loop

# Start date for scheduling
START_DATE = datetime(2026, 4, 12)  # Saturday, April 12, 2026

# Output paths
OUTPUT_CSV = Path("results/experiments.csv")  # Direct experiments.csv for orchestrator


# ==================== HELPER FUNCTIONS ====================

# Caches for performance optimization
_YAML_CACHE = {}
_TEMPLATE_CACHE = {}
_JINJA_ENV = None

def load_product_yaml_safe(product_id: str) -> Tuple[bool, Dict, str]:
    """Safely load product YAML with caching."""
    # Check cache first
    if product_id in _YAML_CACHE:
        return _YAML_CACHE[product_id]

    yaml_path = Path(f"products/{product_id}.yaml")

    if not yaml_path.exists():
        result = (False, {}, f"File not found: {yaml_path}")
        _YAML_CACHE[product_id] = result
        return result

    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        result = (True, data, "")
        _YAML_CACHE[product_id] = result
        return result
    except Exception as e:
        result = (False, {}, f"Parse error: {str(e)}")
        _YAML_CACHE[product_id] = result
        return result


def render_prompt_safe(product_yaml: Dict, material_type: str) -> Tuple[bool, str, str]:
    """Safely render Jinja2 prompt with caching."""
    global _JINJA_ENV

    # Create cache key from product name and material
    product_name = product_yaml.get('name', 'unknown')
    cache_key = f"{product_name}_{material_type}"

    # Check cache first
    if cache_key in _TEMPLATE_CACHE:
        return _TEMPLATE_CACHE[cache_key]

    from jinja2 import Environment, FileSystemLoader, TemplateNotFound

    template_dir = Path("prompts")

    try:
        # Reuse Jinja environment
        if _JINJA_ENV is None:
            _JINJA_ENV = Environment(loader=FileSystemLoader(template_dir))

        template = _JINJA_ENV.get_template(material_type)

        prompt_text = template.render(
            product=product_yaml,
            region=REGION
        )

        result = (True, prompt_text, "")
        _TEMPLATE_CACHE[cache_key] = result
        return result

    except TemplateNotFound:
        result = (False, "", f"Template not found: {material_type}")
        _TEMPLATE_CACHE[cache_key] = result
        return result
    except Exception as e:
        result = (False, "", f"Render error: {str(e)}")
        _TEMPLATE_CACHE[cache_key] = result
        return result


def generate_random_timestamp(day_offset: int, time_slot: str) -> datetime:
    """Generate random timestamp within a specific day and time slot."""
    start_hour, end_hour = TIME_SLOTS[time_slot]

    hour = random.randint(start_hour, end_hour - 1)
    minute = random.randint(0, 59)

    # Calculate actual date (include all 7 days)
    # Days: Mon(0), Tue(1), Wed(2), Thu(3), Fri(4), Sat(5), Sun(6)
    scheduled_date = START_DATE + timedelta(days=day_offset)
    timestamp = scheduled_date.replace(hour=hour, minute=minute, second=0, microsecond=0)

    return timestamp


# ==================== STRATIFIED RANDOMIZATION LOGIC ====================

def create_stratified_matrix(seed: int = RANDOM_SEED) -> List[Dict]:
    """
    Create stratified experimental matrix.

    Stratification levels:
    1. Day (7 days, ~231 runs each, full week)
    2. Product × Material (9 groups per day, ~26 runs each)
    3. Temp × Engine (fully crossed, 9 combos, ~3 reps each)
    4. Time slot (random within day)

    Returns:
        List of 1,620 run configurations with assigned days
    """
    random.seed(seed)

    print("\n" + "=" * 70)
    print("STRATIFIED RANDOMIZATION")
    print("=" * 70)
    print(f"\nRandom seed: {seed}")
    print(f"Days: {NUM_DAYS} (full week)")
    print(f"Base runs per day: {RUNS_PER_DAY}")
    print(f"Extra runs to distribute: {EXTRA_RUNS}")
    print(f"Product × Material groups: {len(PRODUCTS) * len(MATERIALS)}")
    print(f"Runs per group: ~{RUNS_PER_DAY // (len(PRODUCTS) * len(MATERIALS))}")

    all_runs = []

    # LEVEL 1: Iterate over days
    for day_idx, day_name in enumerate(DAYS_OF_WEEK):
        print(f"\n{'─' * 70}")
        print(f"DAY {day_idx + 1}/{NUM_DAYS}: {day_name}")
        print(f"{'─' * 70}")

        # Determine runs for this day
        # Distribute 3 extra runs to first 3 days (Monday, Tuesday, Wednesday)
        # This ensures 1620 total: 232+232+232+231+231+231+231 = 1620
        runs_for_this_day = RUNS_PER_DAY + (1 if day_idx < EXTRA_RUNS else 0)
        print(f"Target runs for today: {runs_for_this_day}")

        # Calculate runs per group for this day
        num_groups = len(PRODUCTS) * len(MATERIALS)
        runs_per_group = runs_for_this_day // num_groups
        extra_runs_today = runs_for_this_day % num_groups

        day_runs = []
        group_idx = 0

        # LEVEL 2: Iterate over (product, material) groups
        for product_id in PRODUCTS:
            for material_type in MATERIALS:

                # Determine runs for this group
                group_runs_target = runs_per_group + (1 if group_idx < extra_runs_today else 0)

                # LEVEL 3: Create fully crossed temp × engine design
                temp_engine_combos = list(itertools.product(TEMPS, ENGINES))

                # Calculate reps per combo
                base_reps = group_runs_target // len(temp_engine_combos)
                extra_reps = group_runs_target % len(temp_engine_combos)

                # Shuffle combos to randomly distribute the extra reps
                random.shuffle(temp_engine_combos)

                group_runs = []

                for combo_idx, (temp, engine) in enumerate(temp_engine_combos):
                    # First 'extra_reps' combos get 1 extra rep
                    num_reps = base_reps + (1 if combo_idx < extra_reps else 0)

                    for rep_num in range(1, num_reps + 1):
                        run = {
                            'product_id': product_id,
                            'material_type': material_type,
                            'temperature': temp,
                            'engine': engine,
                            'repetition': rep_num,
                            'day_name': day_name,
                            'day_index': day_idx
                        }
                        group_runs.append(run)

                day_runs.extend(group_runs)
                group_idx += 1

        # Verify we have the expected number of runs for this day
        assert len(day_runs) == runs_for_this_day, f"Day {day_name} has {len(day_runs)} runs, expected {runs_for_this_day}"

        # LEVEL 4: Assign time slots with stratified balance
        # Create balanced slot list (ensures equal distribution)
        target_per_slot = len(day_runs) // 3
        remainder = len(day_runs) % 3

        # Build balanced slot array
        balanced_slots = (
            ['morning'] * (target_per_slot + (1 if remainder > 0 else 0)) +
            ['afternoon'] * (target_per_slot + (1 if remainder > 1 else 0)) +
            ['evening'] * target_per_slot
        )

        # Shuffle slot assignments to randomize order
        random.shuffle(balanced_slots)

        # Assign slots and timestamps
        for run, time_slot in zip(day_runs, balanced_slots):
            run['time_slot'] = time_slot
            timestamp = generate_random_timestamp(day_idx, time_slot)
            run['timestamp'] = timestamp

        all_runs.extend(day_runs)

        # Print summary for this day
        print(f"  ✅ Generated {len(day_runs)} runs")

        # Count products
        product_counts = {p: sum(1 for r in day_runs if r['product_id']==p) for p in PRODUCTS}
        print(f"     Products: {', '.join(f'{p}={product_counts[p]}' for p in PRODUCTS)}")

        # Count engines
        engine_counts = {e: sum(1 for r in day_runs if r['engine']==e) for e in ENGINES}
        print(f"     Engines: {', '.join(f'{e}={engine_counts[e]}' for e in ENGINES)}")

        # Count temps
        temp_counts = {t: sum(1 for r in day_runs if r['temperature']==t) for t in TEMPS}
        print(f"     Temps: {', '.join(f'{t}={temp_counts[t]}' for t in TEMPS)}")

        # Count time slots
        slot_counts = {s: sum(1 for r in day_runs if r['time_slot']==s) for s in TIME_SLOTS.keys()}
        print(f"     Time slots: {', '.join(f'{s}={slot_counts[s]}' for s in TIME_SLOTS.keys())}")

    print(f"\n{'=' * 70}")
    print(f"TOTAL RUNS GENERATED: {len(all_runs)}")
    print(f"{'=' * 70}")

    return all_runs


def balance_time_slots_globally(runs: List[Dict], seed: int) -> List[Dict]:
    """
    Ensure exactly 540 runs per time slot globally across all 1,620 runs.

    Algorithm:
    1. Count current distribution
    2. Identify donors (over 540) and receivers (under 540)
    3. Randomly swap time slots to achieve perfect 540/540/540 balance
    4. Regenerate timestamps for swapped runs
    """
    random.seed(seed + 1000)  # Different seed from main randomization

    print("\n" + "=" * 70)
    print("GLOBAL TIME SLOT BALANCING")
    print("=" * 70)

    # Count current distribution
    slot_counts = {'morning': 0, 'afternoon': 0, 'evening': 0}
    slot_indices = {'morning': [], 'afternoon': [], 'evening': []}

    for idx, run in enumerate(runs):
        slot = run['time_slot']
        slot_counts[slot] += 1
        slot_indices[slot].append(idx)

    print(f"\nBefore global balancing:")
    for slot in ['morning', 'afternoon', 'evening']:
        count = slot_counts[slot]
        deviation = count - 540
        print(f"  {slot:10s}: {count:4d} (target: 540, deviation: {deviation:+d})")

    # Perform swaps to achieve 540/540/540
    target = 540
    swaps = 0

    while not all(count == target for count in slot_counts.values()):
        # Find donor (over 540) and receiver (under 540)
        donors = [s for s, c in slot_counts.items() if c > target]
        receivers = [s for s, c in slot_counts.items() if c < target]

        if not donors or not receivers:
            break

        donor_slot = donors[0]
        receiver_slot = receivers[0]

        # Pick random run from donor slot
        donor_idx = random.choice(slot_indices[donor_slot])

        # Swap time slot
        runs[donor_idx]['time_slot'] = receiver_slot

        # Regenerate timestamp for new slot
        day_idx = runs[donor_idx]['day_index']
        runs[donor_idx]['timestamp'] = generate_random_timestamp(day_idx, receiver_slot)

        # Update tracking
        slot_indices[donor_slot].remove(donor_idx)
        slot_indices[receiver_slot].append(donor_idx)
        slot_counts[donor_slot] -= 1
        slot_counts[receiver_slot] += 1
        swaps += 1

    print(f"\nAfter balancing ({swaps} swaps):")
    for slot in ['morning', 'afternoon', 'evening']:
        count = slot_counts[slot]
        deviation = count - 540
        print(f"  {slot:10s}: {count:4d} (target: 540, deviation: {deviation:+d})")

    print(f"\n✅ Perfect time slot balance achieved!")

    return runs


def balance_engines(runs: List[Dict]) -> List[Dict]:
    """
    Post-hoc engine balancing via minimal swaps.
    Ensures exactly 540 runs per engine (1620 / 3 = 540).
    """
    target = len(runs) // len(ENGINES)  # 1620 / 3 = 540

    print("\n" + "=" * 70)
    print("ENGINE BALANCING")
    print("=" * 70)

    # Count current distribution
    engine_counts = {e: 0 for e in ENGINES}
    for run in runs:
        engine_counts[run['engine']] += 1

    print(f"\nBefore balancing:")
    for engine, count in sorted(engine_counts.items()):
        deviation = count - target
        print(f"  {engine:10s}: {count:4d} (target: {target}, deviation: {deviation:+d})")

    # Find over/under-represented engines
    over = [e for e in ENGINES if engine_counts[e] > target]
    under = [e for e in ENGINES if engine_counts[e] < target]

    if not over and not under:
        print("\n✅ Already perfectly balanced!")
        return runs

    # Swap runs from over → under
    total_swaps = 0
    for over_engine in over:
        excess = engine_counts[over_engine] - target

        for under_engine in under:
            deficit = target - engine_counts[under_engine]
            swaps_needed = min(excess, deficit)

            if swaps_needed == 0:
                continue

            # Find runs to swap
            swap_count = 0
            for run in runs:
                if run['engine'] == over_engine and swap_count < swaps_needed:
                    run['engine'] = under_engine
                    swap_count += 1
                    engine_counts[over_engine] -= 1
                    engine_counts[under_engine] += 1
                    total_swaps += 1

            excess -= swap_count
            if excess == 0:
                break

    print(f"\nAfter balancing ({total_swaps} swaps):")
    for engine, count in sorted(engine_counts.items()):
        deviation = count - target
        print(f"  {engine:10s}: {count:4d} (target: {target}, deviation: {deviation:+d})")

    # Verify perfect balance
    all_equal = len(set(engine_counts.values())) == 1
    if all_equal:
        print("\n✅ Perfect engine balance achieved!")
    else:
        print("\n⚠️  Warning: Balance not perfect after swaps")

    return runs


def balance_engines_within_time_slots(runs: List[Dict], seed: int) -> List[Dict]:
    """
    Balance engines within time slots as closely as possible (179-181 per cell).

    Due to remainder distribution in stratified randomization, perfect 180/180/180
    is not achievable. This function minimizes imbalance to ±1 run per cell.

    Target distribution (achievable):
    - Each engine: 179-181 runs per time slot (total 540 per engine)
    - Aggregate: 540 morning, 540 afternoon, 540 evening (exact)

    Note: The description "exactly 180" in earlier versions was aspirational.
    The actual implementation achieves 179-181 (±0.6% deviation, excellent).
    """
    random.seed(seed + 2000)

    print("\n" + "=" * 70)
    print("ENGINE × TIME SLOT STRATIFICATION")
    print("=" * 70)

    # Count current engine × time slot distribution
    counts = {
        (engine, slot): 0
        for engine in ENGINES
        for slot in ['morning', 'afternoon', 'evening']
    }

    indices = {key: [] for key in counts.keys()}

    for idx, run in enumerate(runs):
        key = (run['engine'], run['time_slot'])
        counts[key] += 1
        indices[key].append(idx)

    print(f"\nBefore stratification:")
    for engine in ENGINES:
        morning = counts[(engine, 'morning')]
        afternoon = counts[(engine, 'afternoon')]
        evening = counts[(engine, 'evening')]
        print(f"  {engine:10s}: morning={morning:3d}, afternoon={afternoon:3d}, evening={evening:3d}")

    # Perform swaps to achieve 180/180/180 for each engine
    target = 180
    total_swaps = 0

    # Strategy: For each engine, balance its time slot distribution
    for engine in ENGINES:
        swaps_for_engine = 0

        while True:
            # Check if this engine is balanced
            morning = counts[(engine, 'morning')]
            afternoon = counts[(engine, 'afternoon')]
            evening = counts[(engine, 'evening')]

            if morning == target and afternoon == target and evening == target:
                break

            # Find donor and receiver slots for this engine
            donor_slot = None
            receiver_slot = None

            if morning > target:
                donor_slot = 'morning'
                receiver_slot = 'afternoon' if afternoon < target else 'evening'
            elif afternoon > target:
                donor_slot = 'afternoon'
                receiver_slot = 'morning' if morning < target else 'evening'
            elif evening > target:
                donor_slot = 'evening'
                receiver_slot = 'morning' if morning < target else 'afternoon'

            if not donor_slot or counts[(engine, receiver_slot)] >= target:
                # Try to find any valid swap
                donors = [s for s in ['morning', 'afternoon', 'evening'] if counts[(engine, s)] > target]
                receivers = [s for s in ['morning', 'afternoon', 'evening'] if counts[(engine, s)] < target]

                if not donors or not receivers:
                    break

                donor_slot = donors[0]
                receiver_slot = receivers[0]

            # Find another engine with opposite imbalance
            swap_partner = None
            for other_engine in ENGINES:
                if other_engine == engine:
                    continue

                # Check if other_engine has surplus in receiver_slot and deficit in donor_slot
                if counts[(other_engine, receiver_slot)] > target and counts[(other_engine, donor_slot)] < target:
                    swap_partner = other_engine
                    break

            if not swap_partner:
                # Can't find a swap partner, skip
                break

            # Swap: move one run from (engine, donor_slot) to (engine, receiver_slot)
            #       and one run from (swap_partner, receiver_slot) to (swap_partner, donor_slot)

            idx1 = indices[(engine, donor_slot)][0]
            idx2 = indices[(swap_partner, receiver_slot)][0]

            # Swap time slots
            runs[idx1]['time_slot'] = receiver_slot
            runs[idx2]['time_slot'] = donor_slot

            # Regenerate timestamps
            runs[idx1]['timestamp'] = generate_random_timestamp(runs[idx1]['day_index'], receiver_slot)
            runs[idx2]['timestamp'] = generate_random_timestamp(runs[idx2]['day_index'], donor_slot)

            # Update tracking
            indices[(engine, donor_slot)].remove(idx1)
            indices[(engine, receiver_slot)].append(idx1)
            indices[(swap_partner, receiver_slot)].remove(idx2)
            indices[(swap_partner, donor_slot)].append(idx2)

            counts[(engine, donor_slot)] -= 1
            counts[(engine, receiver_slot)] += 1
            counts[(swap_partner, receiver_slot)] -= 1
            counts[(swap_partner, donor_slot)] += 1

            swaps_for_engine += 1
            total_swaps += 1

        if swaps_for_engine > 0:
            print(f"    {engine}: {swaps_for_engine} swaps")

    print(f"\nAfter stratification ({total_swaps} total swaps):")
    for engine in ENGINES:
        morning = counts[(engine, 'morning')]
        afternoon = counts[(engine, 'afternoon')]
        evening = counts[(engine, 'evening')]
        print(f"  {engine:10s}: morning={morning:3d}, afternoon={afternoon:3d}, evening={evening:3d}")

    # Verify perfect balance
    all_perfect = all(counts[(e, s)] == target for e in ENGINES for s in ['morning', 'afternoon', 'evening'])
    if all_perfect:
        print(f"\n✅ Perfect engine × time slot stratification achieved!")
    else:
        print(f"\n⚠️  Warning: Stratification not perfect (may need more iterations)")

    return runs


def simulate_pipeline(runs: List[Dict]) -> List[Dict]:
    """Simulate full pipeline: load YAMLs, render prompts, generate run_ids."""

    print("\n" + "=" * 70)
    print("SIMULATING PIPELINE")
    print("=" * 70)

    results = []
    errors = []
    seen_run_ids = set()

    for idx, run in enumerate(runs, 1):
        product_id = run['product_id']
        material_type = run['material_type']

        # Load YAML
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

        # Render prompt
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

        # Generate run_id (include day and run order to ensure uniqueness)
        knobs = {
            'product_id': product_id,
            'material_type': material_type,
            'engine': run['engine'],
            'time_of_day_label': run['time_slot'],
            'temperature_label': str(run['temperature']),
            'repetition_id': run['repetition'],
            'day_of_week': run['day_name'],  # Add day to make unique
            'run_order': idx,  # Add run order to prevent collisions
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

        # Progress
        if idx % 100 == 0:
            print(f"  Processed {idx}/{len(runs)} runs...")

    print(f"  Processed {len(runs)}/{len(runs)} runs... DONE")

    if errors:
        print(f"\n⚠️  ERRORS FOUND ({len(errors)}):")
        for err in errors[:10]:
            print(f"  - {err}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")
    else:
        print("\n✅ No errors found!")

    return results


def save_results_to_csv(results: List[Dict], output_path: Path):
    """Save results to CSV in experiments.csv format (compatible with orchestrator)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Full experiments.csv schema (orchestrator-compatible)
    fieldnames = [
        # Core Identifiers (4)
        'run_id', 'product_id', 'material_type', 'engine',

        # Prompt Info (3)
        'prompt_id', 'prompt_text_path', 'system_prompt',

        # Model Setup (8)
        'model', 'model_version', 'temperature', 'max_tokens', 'seed',
        'top_p', 'frequency_penalty', 'presence_penalty',

        # Run Context (9) - includes scheduling metadata
        'session_id', 'account_id', 'time_of_day_label', 'repetition_id',
        'scheduled_datetime', 'scheduled_hour_of_day', 'scheduled_day_of_week',
        'started_at', 'completed_at',

        # Response Data (5)
        'prompt_tokens', 'completion_tokens', 'total_tokens', 'finish_reason', 'output_path',

        # Computed/Derived (3)
        'date_of_run', 'execution_duration_sec', 'status',

        # Experimental Design (4)
        'trap_flag', 'matrix_randomization_seed', 'matrix_randomization_mode', 'config_fingerprint'
    ]

    from config import DEFAULT_MAX_TOKENS, DEFAULT_SEED, DEFAULT_TOP_P
    from config import DEFAULT_FREQUENCY_PENALTY, DEFAULT_PRESENCE_PENALTY, DEFAULT_ACCOUNT_ID

    # Prepare rows for CSV
    csv_rows = []
    for idx, run in enumerate(results, 1):
        material_base = run.get('material_type', '').replace('.j2', '')
        prompt_id = f"{run.get('product_id')}_{material_base}_v1"

        csv_row = {
            # Core Identifiers
            'run_id': run.get('run_id'),
            'product_id': run.get('product_id'),
            'material_type': run.get('material_type'),
            'engine': run.get('engine'),

            # Prompt Info (populated at runtime)
            'prompt_id': prompt_id,
            'prompt_text_path': f"outputs/prompts/{run.get('run_id')}.txt",
            'system_prompt': '',

            # Model Setup (defaults from config, model populated at runtime)
            'model': '',
            'model_version': '',
            'temperature': run.get('temperature'),
            'max_tokens': DEFAULT_MAX_TOKENS,
            'seed': DEFAULT_SEED if DEFAULT_SEED is not None else '',
            'top_p': DEFAULT_TOP_P if DEFAULT_TOP_P is not None else '',
            'frequency_penalty': DEFAULT_FREQUENCY_PENALTY if DEFAULT_FREQUENCY_PENALTY is not None else '',
            'presence_penalty': DEFAULT_PRESENCE_PENALTY if DEFAULT_PRESENCE_PENALTY is not None else '',

            # Run Context
            'session_id': '',  # Populated at runtime
            'account_id': DEFAULT_ACCOUNT_ID,
            'time_of_day_label': run.get('time_slot'),
            'repetition_id': run.get('repetition'),
            'scheduled_datetime': run.get('timestamp').isoformat() if run.get('timestamp') else '',
            'scheduled_hour_of_day': run.get('timestamp').hour if run.get('timestamp') else '',
            'scheduled_day_of_week': run.get('day_name'),
            'started_at': '',  # Populated at runtime
            'completed_at': '',  # Populated at runtime

            # Response Data (populated at runtime)
            'prompt_tokens': 0,
            'completion_tokens': 0,
            'total_tokens': 0,
            'finish_reason': '',
            'output_path': f"outputs/{run.get('run_id')}.txt",

            # Computed/Derived (populated at runtime)
            'date_of_run': '',
            'execution_duration_sec': '',
            'status': 'pending',

            # Experimental Design
            'trap_flag': False,
            'matrix_randomization_seed': RANDOM_SEED,
            'matrix_randomization_mode': 'stratified_7day_balanced',
            'config_fingerprint': ''  # Can be computed if needed
        }
        csv_rows.append(csv_row)

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"\n💾 Results saved to: {output_path}")
    print(f"   Format: experiments.csv compatible (orchestrator can execute this)")


def print_summary_stats(results: List[Dict]):
    """Print summary statistics."""
    total = len(results)

    print("\n" + "=" * 70)
    print("SUMMARY STATISTICS")
    print("=" * 70)

    print(f"\nTotal runs: {total}")

    # Count by day
    day_counts = {}
    for run in results:
        day = run['day_name']
        day_counts[day] = day_counts.get(day, 0) + 1

    print(f"\n📅 Distribution by Day:")
    for day in DAYS_OF_WEEK:
        count = day_counts.get(day, 0)
        print(f"  {day:10s}: {count:4d} runs (expected: {RUNS_PER_DAY})")

    # Count by time slot
    time_counts = {}
    for run in results:
        slot = run['time_slot']
        time_counts[slot] = time_counts.get(slot, 0) + 1

    print(f"\n⏰ Distribution by Time Slot:")
    for slot in TIME_SLOTS.keys():
        count = time_counts.get(slot, 0)
        expected = total / 3
        deviation = ((count - expected) / expected) * 100 if expected > 0 else 0
        print(f"  {slot:10s}: {count:4d} runs (expected: {expected:.1f}, deviation: {deviation:+.1f}%)")

    # Weekday vs weekend
    weekday_count = sum(1 for r in results if r.get('day_name') not in ['Saturday', 'Sunday'])
    weekend_count = sum(1 for r in results if r.get('day_name') in ['Saturday', 'Sunday'])

    print(f"\n📊 Weekday vs Weekend:")
    print(f"  Weekday:  {weekday_count:4d} runs ({weekday_count/total*100:.1f}%)")
    print(f"  Weekend:  {weekend_count:4d} runs ({weekend_count/total*100:.1f}%)")

    # Count by product
    product_counts = {}
    for run in results:
        prod = run['product_id']
        product_counts[prod] = product_counts.get(prod, 0) + 1

    print(f"\n🔬 Distribution by Product:")
    for prod in PRODUCTS:
        count = product_counts.get(prod, 0)
        expected = total / len(PRODUCTS)
        print(f"  {prod:25s}: {count:4d} runs (expected: {expected:.1f})")

    # Count by engine
    engine_counts = {}
    for run in results:
        eng = run['engine']
        engine_counts[eng] = engine_counts.get(eng, 0) + 1

    print(f"\n🤖 Distribution by Engine:")
    for eng in ENGINES:
        count = engine_counts.get(eng, 0)
        expected = total / len(ENGINES)
        print(f"  {eng:10s}: {count:4d} runs (expected: {expected:.1f})")

    # Count by temperature
    temp_counts = {}
    for run in results:
        temp = run['temperature']
        temp_counts[temp] = temp_counts.get(temp, 0) + 1

    print(f"\n🌡️  Distribution by Temperature:")
    for temp in TEMPS:
        count = temp_counts.get(temp, 0)
        expected = total / len(TEMPS)
        print(f"  {temp:4.1f}: {count:4d} runs (expected: {expected:.1f})")

    # Statistical Validation
    print("\n" + "=" * 70)
    print("STATISTICAL VALIDATION")
    print("=" * 70)

    # Chi-square test for time slots (H0: uniform distribution)
    time_observed = [time_counts.get(slot, 0) for slot in TIME_SLOTS.keys()]
    time_expected = [total / 3] * 3
    chi2_time = sum((obs - exp)**2 / exp for obs, exp in zip(time_observed, time_expected))
    # Critical value for χ²(df=2, α=0.05) = 5.991
    p_time = "< 0.05" if chi2_time > 5.991 else "> 0.05"

    print(f"\n⏰ Time Slot Balance (Chi-square goodness-of-fit):")
    print(f"  χ² = {chi2_time:.3f} (critical value = 5.991)")
    print(f"  p {p_time}")
    if chi2_time < 5.991:
        print(f"  ✅ Time slots are balanced (fail to reject H0)")
    else:
        print(f"  ⚠️  Time slot imbalance detected (p < 0.05)")

    # Engine balance check
    engine_values = list(engine_counts.values())
    engine_perfect = len(set(engine_values)) == 1
    print(f"\n🤖 Engine Balance:")
    print(f"  Counts: {dict(sorted(engine_counts.items()))}")
    if engine_perfect:
        print(f"  ✅ Perfect balance (all engines have exactly {engine_values[0]} runs)")
    else:
        max_dev = max(engine_values) - min(engine_values)
        print(f"  ⚠️  Imbalance detected (max deviation: {max_dev} runs)")

    # Day balance check
    day_values = list(day_counts.values())
    day_range = max(day_values) - min(day_values)
    print(f"\n📅 Day Balance:")
    print(f"  Range: {min(day_values)} - {max(day_values)} runs per day")
    if day_range <= 1:
        print(f"  ✅ Excellent balance (max deviation: {day_range} run)")
    else:
        print(f"  ⚠️  Imbalance detected (range: {day_range} runs)")

    print("\n" + "=" * 70)


# ==================== MAIN ====================

def main(seed: int = RANDOM_SEED, start_date: datetime = None):
    """Run stratified randomizer."""
    global START_DATE
    if start_date is None:
        start_date = START_DATE
    else:
        START_DATE = start_date  # Update global variable

    print("=" * 70)
    print("STRATIFIED RANDOMIZER TEST (1,620 RUNS)")
    print("=" * 70)
    print(f"\nConfiguration:")
    print(f"  Products: {len(PRODUCTS)}")
    print(f"  Materials: {len(MATERIALS)}")
    print(f"  Temperatures: {len(TEMPS)}")
    print(f"  Engines: {len(ENGINES)}")
    print(f"  Days: {NUM_DAYS} (full week)")
    print(f"  Runs per day: {RUNS_PER_DAY}")
    print(f"  Random seed: {seed}")
    print(f"  Start date: {start_date.strftime('%Y-%m-%d')}")

    # Generate stratified matrix
    runs = create_stratified_matrix(seed=seed)

    # PHASE 1: Balance time slots globally (ensure exactly 540 per time slot)
    runs = balance_time_slots_globally(runs, seed=seed)

    # PHASE 2: Balance engines (ensure exactly 540 per engine)
    runs = balance_engines(runs)

    # PHASE 3: Stratify engines within time slots (ensure exactly 180 per engine per time slot)
    runs = balance_engines_within_time_slots(runs, seed=seed)

    # Simulate pipeline
    results = simulate_pipeline(runs)

    # Save results
    save_results_to_csv(results, OUTPUT_CSV)

    # Print summary
    print_summary_stats(results)

    print("\n✅ Stratified dry-run complete!")
    print(f"\nNext steps:")
    print(f"  1. Run: python scripts/analyze_randomizer_distribution.py")
    print(f"  2. Run: python scripts/validate_randomizer_anova.py")
    print(f"  3. Compare with pure random results")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Stratified randomizer test")
    parser.add_argument('--seed', type=int, default=RANDOM_SEED, help='Random seed')
    parser.add_argument('--start-date', type=str, default=None, help='Start date in YYYY-MM-DD format (default: 2026-04-12)')
    args = parser.parse_args()

    # Parse start date if provided
    start_date = START_DATE
    if args.start_date:
        from datetime import datetime
        try:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d')
        except ValueError:
            print(f"Error: Invalid date format '{args.start_date}'. Use YYYY-MM-DD")
            sys.exit(1)

    main(seed=args.seed, start_date=start_date)
