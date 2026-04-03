# Stratified Randomizer Integration Plan

**Date**: 2026-03-28
**Status**: Proposed (awaiting user approval)

---

## Current State

### Two Separate Systems:

**System 1: Main Pipeline** (`config.py` → `runner/generate_matrix.py` → `orchestrator.py`)
- Formula: 3 products × 3 materials × 3 times × 3 temps × 3 reps × 3 engines
- **Result: 729 runs**
- Used by: `python orchestrator.py run`
- Location: config.py:10-43, runner/generate_matrix.py:183-186

**System 2: Stratified Randomizer** (`scripts/test_randomizer_stratified.py`)
- Formula: 3 products × 3 materials × 3 temps × 3 engines × ~6.67 temporal reps × 3 time-of-day labels
- **Result: 1,620 runs**
- Used by: `python scripts/test_randomizer_stratified.py`
- Location: scripts/test_randomizer_stratified.py:1-925
- Output: results/randomizer_stratified_1620.csv

### The Gap:

Documentation claims 1,620 runs, but running `orchestrator.py` would generate only 729 runs.

---

## Integration Options

### Option 1: Simple Replication Factor (EASIEST)

**Change:** Increase REPS in config.py from 3 to 20

```python
# config.py line 37
REPS = tuple(range(1, 21))  # 20 replications (instead of 3)
```

**Result:**
- 3 × 3 × 3 × 3 × **20** × 3 = 1,620 runs
- Simple Cartesian product (no sophisticated balancing)
- All 20 reps of each condition run sequentially (unless randomized)

**Pros:**
- 5-minute implementation
- Minimal code changes
- Maintains existing pipeline architecture

**Cons:**
- **Loses sophisticated statistical balancing** from stratified randomizer
- No day-based stratification (all 1,620 runs treated equally)
- No 180-per-engine-per-time-slot guarantee
- Less elegant statistical design

**When to use:** If you just need 1,620 runs and don't care about advanced stratification.

---

### Option 2: Integrate Stratified Randomizer (RECOMMENDED)

**Change:** Replace `runner/generate_matrix.py` to use stratified randomization logic

**Approach:**
1. Copy stratified randomizer functions into `runner/generate_matrix.py`
2. Replace Cartesian product (lines 183-186) with `create_stratified_matrix()`
3. Include balancing phases:
   - Global time slot balancing (540 per slot)
   - Engine balancing (540 per engine)
   - Engine × time slot stratification (180 per engine per slot)
4. Keep same CSV output format (maintain compatibility with orchestrator)

**Result:**
- 1,620 runs with statistical guarantees:
  - Exactly 540 runs per engine (OpenAI, Google, Mistral)
  - Exactly 540 runs per time-of-day (morning, afternoon, evening)
  - Exactly 180 runs per engine per time-of-day (no confounding)
  - Balanced across 7 days (231-232 runs/day)

**Pros:**
- **Preserves sophisticated statistical design** from randomizer
- Perfect balance across engines and time-of-day
- Controls for weekly temporal effects
- Publishable randomization methodology

**Cons:**
- 2-3 hours implementation time
- More complex code (but well-tested)
- Requires understanding stratification logic

**When to use:** If you want a rigorous, peer-reviewable statistical design.

---

## Recommended Approach: **Option 2 (Stratified Integration)**

### Why?

1. **Statistical rigor**: The stratified randomizer was carefully designed with:
   - 5-level stratification hierarchy
   - Perfect balance guarantees (0% deviation for engines and time slots)
   - Controls for day-of-week effects

2. **Already validated**: The randomizer has been tested and outputs 1,620 runs with correct balance

3. **Research credibility**: For publication, you can describe a sophisticated randomization protocol:
   > "We employed stratified randomization with 5 levels: day-of-week (7 strata), product×material (9 strata per day), temperature×engine (fully crossed), time-of-day (balanced within-day), and post-hoc engine stratification. This design guarantees exactly 540 runs per engine and per time slot, with 180 runs per engine×time slot cell, eliminating confounding between temporal and provider factors."

4. **Matches existing dry-run**: `results/randomizer_dry_run_2026-03-25.csv` is the ground truth

---

## Implementation Steps (Option 2)

### Step 1: Extract Stratified Logic

Move from `scripts/test_randomizer_stratified.py` to `runner/generate_matrix.py`:
- `create_stratified_matrix()` (lines 189-323)
- `balance_time_slots_globally()` (lines 326-397)
- `balance_engines()` (lines 400-467)
- `balance_engines_within_time_slots()` (lines 470-611)

### Step 2: Modify `generate_full_matrix()` Function

Replace lines 183-186 (Cartesian product):
```python
# OLD:
all_combinations = list(itertools.product(
    PRODUCTS, MATERIALS, TIMES, TEMPS, REPS, ENGINES
))

# NEW:
runs = create_stratified_matrix(seed=seed)
runs = balance_time_slots_globally(runs, seed=seed)
runs = balance_engines(runs)
runs = balance_engines_within_time_slots(runs, seed=seed)

# Convert stratified runs to combination tuples
all_combinations = [
    (r['product_id'], r['material_type'], r['time_slot'],
     r['temperature'], r['repetition'], r['engine'])
    for r in runs
]
```

### Step 3: Add Scheduled Metadata to CSV

The stratified randomizer already generates:
- `scheduled_datetime` (exact timestamp)
- `scheduled_time_slot` (morning/afternoon/evening)
- `day_of_week` (Monday-Sunday)
- `day_index` (0-6)

These should be written to `experiments.csv` (already supported in schema).

### Step 4: Update config.py

**IMPORTANT:** With stratified randomizer, `TIMES` is no longer a simple list for Cartesian product.

Two options:

**Option A: Keep TIMES but note it's metadata**
```python
# config.py lines 25-29
TIMES = (
    "morning",    # 7am-12pm: 540 runs
    "afternoon",  # 12pm-5pm: 540 runs
    "evening",    # 5pm-10pm: 540 runs
)
# NOTE: With stratified randomizer, these are assigned via balancing, not Cartesian product
```

**Option B: Remove TIMES from factorial constants**
```python
# Remove TIMES from config.py (stratified randomizer handles it)
# Update comment:
# - 3 products × 3 materials × 3 temps × 20 temporal reps × 3 engines = 1,620 runs
#   (temporal reps are stratified across 7 days with balanced time-of-day assignment)
```

I recommend **Option A** (keep TIMES for documentation clarity).

### Step 5: Test Integration

```bash
# Generate matrix with stratified randomizer
python -m runner.generate_matrix --force --seed 42

# Verify output
wc -l results/experiments.csv  # Should be 1,621 (header + 1,620 runs)

# Check balance
python -c "
import pandas as pd
df = pd.read_csv('results/experiments.csv')
print('Total runs:', len(df))
print('\\nEngine balance:')
print(df['engine'].value_counts())
print('\\nTime-of-day balance:')
print(df['time_of_day_label'].value_counts())
"
```

Expected output:
```
Total runs: 1620

Engine balance:
openai     540
google     540
mistral    540

Time-of-day balance:
morning      540
afternoon    540
evening      540
```

---

## Verification Checklist

After integration:

- [ ] `python -m runner.generate_matrix` produces exactly 1,620 runs
- [ ] Engine balance: 540 runs per engine (±0)
- [ ] Time slot balance: 540 runs per time slot (±0)
- [ ] Engine × time slot balance: 180 per cell (±0)
- [ ] Day balance: 231-232 runs per day
- [ ] CSV schema unchanged (compatible with orchestrator)
- [ ] All YAML files load correctly
- [ ] All prompts render correctly
- [ ] No run_id collisions
- [ ] Randomization seed documented
- [ ] `experiments.meta.json` contains stratification metadata

---

## Migration Timeline

**Total time: 2-3 hours**

1. **Backup current state** (5 min)
   ```bash
   cp config.py config.py.backup.729runs
   cp runner/generate_matrix.py runner/generate_matrix.py.backup
   ```

2. **Code changes** (1.5 hours)
   - Extract stratification functions
   - Modify generate_full_matrix()
   - Update config.py comments

3. **Testing** (30 min)
   - Generate test matrix
   - Verify balance
   - Check CSV compatibility

4. **Documentation** (30 min)
   - Update CLAUDE.md
   - Update README.md
   - Document randomization protocol

---

## Rollback Plan

If integration fails:
```bash
# Restore original 729-run design
cp config.py.backup.729runs config.py
cp runner/generate_matrix.py.backup runner/generate_matrix.py

# Regenerate 729-run matrix
python -m runner.generate_matrix --force
```

---

## Decision Required

**Which option do you prefer?**

1. **Option 1 (Simple):** Increase REPS to 20 → 1,620 runs (5 minutes, no stratification)
2. **Option 2 (Recommended):** Integrate stratified randomizer → 1,620 runs (2-3 hours, full statistical rigor)

**My recommendation:** Option 2, because:
- You already have a working stratified randomizer
- The sophisticated design is more publishable
- Independent reviewers will appreciate the rigor
- It matches the existing dry-run CSV

---

## Next Steps

**After user approval:**

1. I will implement the chosen option
2. Generate test matrix
3. Verify all balances
4. Update all documentation to reflect canonical design
5. Create final verification report

**User: Please confirm which option you prefer, and I'll proceed with implementation.**
