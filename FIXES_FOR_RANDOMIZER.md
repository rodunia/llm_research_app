# How to Fix Randomizer Issues

## Problem 1: Saturday is Missing

**Location**: `scripts/test_randomizer_stratified.py`, line 36

**Current code**:
```python
DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Sunday']
```

**Fix**: Add Saturday back
```python
DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
```

**Consequence**: This changes from 6 days → 7 days
- Runs per day: 270 → ~231 (1620 / 7 = 231.43)
- Need to recalculate RUNS_PER_DAY

**Update line 47**:
```python
# Old:
RUNS_PER_DAY = 270  # 1620 / 6

# New:
NUM_DAYS = len(DAYS_OF_WEEK)  # 7 days
RUNS_PER_DAY = 1620 // NUM_DAYS  # 1620 / 7 = 231
REMAINDER_RUNS = 1620 % NUM_DAYS  # 1620 % 7 = 3 extra runs
```

**Note**: 1620 / 7 = 231 remainder 3
- You'll need to distribute 3 extra runs across some days
- Option A: 4 days get 232 runs, 3 days get 231 runs
- Option B: Round to 1610 runs (7 × 230) or 1617 runs (7 × 231)

---

## Problem 2: Engine Balance is Off

**Root cause**: The stratified randomization doesn't guarantee perfect engine balance because it randomizes within each (day, product×material) cell.

**Current logic** (lines 119-200):
1. Stratify by day (6 days)
2. Within each day: stratify by product×material (9 groups)
3. Within each group: fully cross temp×engine (3 temps × 3 engines = 9 combos)
4. Assign ~3-4 reps per combo

**Why engines are imbalanced**:
- 30 runs per group / 9 combos = 3.33 reps per combo
- Some combos get 3 reps, some get 4 reps (randomly)
- Over 270 combos across the experiment, small imbalances accumulate

**Fix Option A: Force Perfect Balance (Recommended)**

Add constraint to ensure exactly 540 runs per engine (1620 / 3 = 540):

```python
def create_stratified_matrix_balanced(seed: int = RANDOM_SEED) -> List[Dict]:
    """
    Create stratified experimental matrix with GUARANTEED engine balance.
    """
    random.seed(seed)

    # Track engine usage globally
    engine_counts = {engine: 0 for engine in ENGINES}

    all_runs = []

    # LEVEL 1: Iterate over days
    for day_idx, day_name in enumerate(DAYS_OF_WEEK):
        day_runs = []

        # LEVEL 2: Iterate over product×material groups
        for product_id, material_type in itertools.product(PRODUCTS, MATERIALS):

            # LEVEL 3: Create all temp×engine combinations
            combos = list(itertools.product(TEMPS, ENGINES))

            # Calculate how many reps per combo (with remainder)
            runs_needed = RUNS_PER_GROUP  # e.g., 30
            reps_per_combo = runs_needed // len(combos)  # 30 / 9 = 3
            remainder = runs_needed % len(combos)  # 30 % 9 = 3

            # Distribute remainder: some combos get +1 rep
            # BUT prioritize engines that are under-represented
            combo_reps = []
            for temp, engine in combos:
                base_reps = reps_per_combo

                # Give extra rep if engine is below target count
                target_per_engine = 540  # 1620 / 3
                if remainder > 0 and engine_counts[engine] < target_per_engine:
                    base_reps += 1
                    remainder -= 1

                combo_reps.append((temp, engine, base_reps))

            # Create runs for this group
            for temp, engine, num_reps in combo_reps:
                for rep in range(num_reps):
                    run = {
                        'product_id': product_id,
                        'material_type': material_type,
                        'engine': engine,
                        'temperature': temp,
                        'repetition': rep + 1,
                        'scheduled_day_of_week': day_name,
                        # ... rest of fields
                    }
                    day_runs.append(run)
                    engine_counts[engine] += 1

        # LEVEL 4: Randomize time slots within day
        random.shuffle(day_runs)
        for run in day_runs:
            time_slot = random.choice(list(TIME_SLOTS.keys()))
            run['scheduled_time_slot'] = time_slot
            # ... assign timestamp

        all_runs.extend(day_runs)

    # Verify balance
    final_counts = {engine: 0 for engine in ENGINES}
    for run in all_runs:
        final_counts[run['engine']] += 1

    print("\n✓ Final engine distribution:")
    for engine, count in final_counts.items():
        print(f"  {engine}: {count}")

    return all_runs
```

**Fix Option B: Post-hoc Balancing (Simpler)**

After generating the full matrix, swap engines to achieve perfect balance:

```python
def balance_engines(runs: List[Dict]) -> List[Dict]:
    """Post-hoc engine balancing via minimal swaps."""
    target = len(runs) // len(ENGINES)  # 1620 / 3 = 540

    engine_counts = {e: 0 for e in ENGINES}
    for run in runs:
        engine_counts[run['engine']] += 1

    print(f"\nBefore balancing: {engine_counts}")

    # Find over/under-represented engines
    over = [e for e in ENGINES if engine_counts[e] > target]
    under = [e for e in ENGINES if engine_counts[e] < target]

    # Swap runs from over → under
    for over_engine in over:
        excess = engine_counts[over_engine] - target

        for under_engine in under:
            deficit = target - engine_counts[under_engine]
            swaps_needed = min(excess, deficit)

            # Find runs to swap
            swap_count = 0
            for run in runs:
                if run['engine'] == over_engine and swap_count < swaps_needed:
                    run['engine'] = under_engine
                    swap_count += 1
                    engine_counts[over_engine] -= 1
                    engine_counts[under_engine] += 1

            excess -= swap_count
            if excess == 0:
                break

    print(f"After balancing: {engine_counts}")
    return runs
```

---

## Recommended Actions

### 1. Add Saturday + Perfect Engine Balance

Edit `scripts/test_randomizer_stratified.py`:

**Line 36** (add Saturday):
```python
DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
```

**Line 47** (recalculate runs per day):
```python
NUM_DAYS = len(DAYS_OF_WEEK)  # 7
RUNS_PER_DAY = 1620 // NUM_DAYS  # 231
EXTRA_RUNS = 1620 % NUM_DAYS  # 3
```

**Line 108-109** (update day mapping):
```python
# Old (skip Saturday):
day_mapping = [0, 1, 2, 3, 4, 6]  # Skip day 5 (Saturday)

# New (include all days):
day_mapping = list(range(NUM_DAYS))  # [0, 1, 2, 3, 4, 5, 6]
```

**After line 200** (add engine balancing):
```python
# Balance engines post-hoc
all_runs = balance_engines(all_runs)
```

### 2. Handle 1620 / 7 = 231 remainder 3

**Option A**: Distribute 3 extra runs to first 3 days
```python
# In day loop:
if day_idx < EXTRA_RUNS:
    runs_for_this_day = RUNS_PER_DAY + 1  # 232
else:
    runs_for_this_day = RUNS_PER_DAY  # 231
```

**Option B**: Adjust total to 1617 (7 × 231) - drop 3 runs
- Remove 1 run from each of 3 randomly selected (product×material×temp×engine) combos

---

## Quick Fix Commands

```bash
# 1. Edit the file
nano scripts/test_randomizer_stratified.py

# 2. Update line 36:
DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

# 3. Update line 47:
NUM_DAYS = len(DAYS_OF_WEEK)
RUNS_PER_DAY = 1620 // NUM_DAYS  # 231

# 4. Update line 108:
day_mapping = list(range(NUM_DAYS))

# 5. Add balancing function after the main generation loop

# 6. Regenerate:
python scripts/test_randomizer_stratified.py --seed 42
```

---

## Verification

After regenerating, verify with:

```python
import pandas as pd

df = pd.read_csv('results/randomizer_stratified_1620.csv')

# Check days
print("Days:", df['scheduled_day_of_week'].value_counts().sort_index())

# Check engines
print("\nEngines:", df['engine'].value_counts())

# Check time slots
print("\nTime slots:", df['scheduled_time_slot'].value_counts())

# Check balance
engine_counts = df['engine'].value_counts()
print(f"\nBalance ratio: {engine_counts.max() / engine_counts.min():.4f}")
print("✓ Perfect balance" if len(set(engine_counts.values)) == 1 else "⚠️ Still imbalanced")
```

---

## Expected Results After Fix

```
Days:
  Monday: 232 runs
  Tuesday: 232 runs
  Wednesday: 232 runs
  Thursday: 231 runs
  Friday: 231 runs
  Saturday: 231 runs
  Sunday: 231 runs

Engines:
  openai: 540 runs
  google: 540 runs
  mistral: 540 runs

Time slots:
  morning: ~540 runs
  afternoon: ~540 runs
  evening: ~540 runs

Balance ratio: 1.0000
✓ Perfect balance
```
