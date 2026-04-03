# Randomization Workflow - Complete Integration Guide

**Date**: 2026-03-28
**Status**: ✅ **INTEGRATED AND OPERATIONAL**

---

## Overview

The research application now uses a **pre-registered stratified randomization protocol** for generating the 1,620 experimental runs. This ensures:

1. **Statistical rigor** - Perfect balance across engines and time-of-day conditions
2. **Reproducibility** - Fixed seed ensures identical randomization
3. **Pre-registration** - Randomization locked before experiments execute
4. **Temporal validity** - Controls for day-of-week and time-slot effects

---

## How It Works

### Step 1: Generate Randomization Protocol (Pre-Registration)

```bash
# Generate locked randomization schedule
python scripts/test_randomizer_stratified.py --seed 42
```

**What this does:**
- Creates `results/experiments.csv` with 1,620 runs
- Each run has assigned:
  - Product, material, engine, temperature, repetition
  - Scheduled day-of-week (Monday-Sunday)
  - Scheduled time slot (morning/afternoon/evening)
  - Scheduled exact timestamp
- Validates statistical balance:
  - ✅ 540 runs per engine (perfect balance)
  - ✅ 540 runs per time slot (perfect balance)
  - ✅ 180 runs per engine×time slot (no confounding)
  - ✅ 231-232 runs per day (excellent balance)

**Output:**
```
======================================================================
TOTAL RUNS GENERATED: 1620
======================================================================

Engine balance: 540 openai, 540 google, 540 mistral ✅
Time slot balance: 540 morning, 540 afternoon, 540 evening ✅
Day balance: 231-232 runs per day ✅
```

### Step 2: Execute According to Protocol

```bash
# Check status
python orchestrator.py status

# Execute all pending runs
python orchestrator.py run

# Or execute specific time slot
python orchestrator.py run --time-of-day morning
```

**What this does:**
- Reads `results/experiments.csv`
- Executes runs in randomized order
- Fills in runtime metadata:
  - `started_at`, `completed_at`
  - `model`, `model_version`
  - `prompt_tokens`, `completion_tokens`
  - `finish_reason`, `status`
- Updates CSV after each run

---

## Statistical Properties

### Stratification Levels

The randomizer uses **5-level stratification**:

1. **Day stratification** (7 days)
   - 231-232 runs per day
   - Covers full week (Monday-Sunday)
   - Controls for weekly temporal patterns

2. **Product × Material stratification** (9 groups per day)
   - ~26 runs per group
   - Prevents confounding between content types

3. **Temperature × Engine full crossing** (9 combinations)
   - ~3 replications per combo
   - Enables 2-way ANOVA

4. **Time slot stratification** (balanced within day)
   - Exactly 540 per time slot globally
   - Morning (7am-12pm), Afternoon (12pm-5pm), Evening (5pm-10pm)

5. **Engine × Time slot stratification** (post-hoc balancing)
   - Exactly 180 per engine per time slot
   - Eliminates confounding

### Balance Guarantees

| Factor | Target | Actual | Deviation |
|--------|--------|--------|-----------|
| Runs per engine | 540 | 540 | ±0% ✅ |
| Runs per time slot | 540 | 540 | ±0% ✅ |
| Runs per engine×time slot | 180 | 180 | ±0% ✅ |
| Runs per day | 231.4 | 231-232 | ±0.4% ✅ |
| Runs per product | 540 | 528-546 | ±2.2% ✅ |
| Runs per temperature | 540 | 537-542 | ±0.6% ✅ |

---

## Reproducibility

### Fixed Seeds

The randomization uses **deterministic seeding**:

```python
RANDOM_SEED = 42  # Main randomization seed
```

**What's seeded:**
- Order of runs
- Time slot assignments
- Day-of-week distribution
- Exact timestamps

**Not seeded (LLM API behavior):**
- Model responses (controlled via per-run `seed` parameter in API calls)

### Verification

To verify the randomization is reproducible:

```bash
# Generate matrix twice with same seed
python scripts/test_randomizer_stratified.py --seed 42 > /tmp/run1.txt
mv results/experiments.csv /tmp/experiments1.csv

python scripts/test_randomizer_stratified.py --seed 42 > /tmp/run2.txt
mv results/experiments.csv /tmp/experiments2.csv

# Compare (should be identical)
diff /tmp/experiments1.csv /tmp/experiments2.csv
# No output = identical ✅
```

---

## Workflow Comparison

### ❌ Old Workflow (729 runs, not stratified)

```bash
python -m runner.generate_matrix --force
python orchestrator.py run
```

**Issues:**
- Only 729 runs (not 1,620)
- Simple Cartesian product (no sophisticated balancing)
- No day-of-week stratification
- No engine×time slot balance guarantee

### ✅ New Workflow (1,620 runs, stratified)

```bash
python scripts/test_randomizer_stratified.py --seed 42
python orchestrator.py run
```

**Benefits:**
- 1,620 runs (matches documentation)
- Perfect statistical balance
- Pre-registered randomization protocol
- Controls for temporal confounds
- Publishable methodology

---

## Common Operations

### Generate Fresh Matrix (Reset Experiments)

```bash
# WARNING: This will delete all previous experiment results
python scripts/test_randomizer_stratified.py --seed 42
```

### Change Randomization (Sensitivity Analysis)

```bash
# Use different seed for sensitivity analysis
python scripts/test_randomizer_stratified.py --seed 999
```

### Check Current Matrix

```bash
# View matrix statistics
python orchestrator.py status

# Verify balance
python3 -c "
import pandas as pd
df = pd.read_csv('results/experiments.csv')
print('Engine balance:', df['engine'].value_counts().to_dict())
print('Time balance:', df['time_of_day_label'].value_counts().to_dict())
"
```

### Resume Interrupted Experiments

```bash
# Orchestrator automatically skips completed runs
python orchestrator.py run
```

---

## Integration Details

### Modified Files

1. **scripts/test_randomizer_stratified.py**
   - Line 95: Changed output path to `results/experiments.csv`
   - Lines 704-803: Modified `save_results_to_csv()` to output full orchestrator schema
   - Now generates experiments.csv with all 36 required columns

2. **config.py**
   - Lines 5-10: Updated study design comment to reference stratified randomizer
   - Lines 57-61: Added note about how to generate matrix

### No Changes Needed

- ✅ **orchestrator.py** - Already reads `results/experiments.csv`, no changes needed
- ✅ **runner/run_job.py** - Already handles CSV updates, no changes needed
- ✅ **runner/engines/** - Already work with experiments.csv format

---

## Pre-Registration Workflow

For maximum research rigor:

### Phase 1: Pre-Registration (Before Experiments)

```bash
# 1. Generate randomization protocol
python scripts/test_randomizer_stratified.py --seed 42

# 2. Backup the locked protocol
cp results/experiments.csv preregistration/experiments_protocol_2026-03-28.csv

# 3. Document in OSF/repository
# Upload experiments_protocol_2026-03-28.csv to OSF
# Record: date, seed, total runs, balance statistics

# 4. Commit to version control
git add results/experiments.csv preregistration/
git commit -m "Pre-register 1,620-run randomization protocol (seed=42)"
```

### Phase 2: Execution (Follow Protocol)

```bash
# 5. Execute according to locked protocol
python orchestrator.py run

# 6. Never regenerate the matrix during execution
# (Would invalidate pre-registration)
```

### Phase 3: Analysis (After Experiments)

```bash
# 7. Verify protocol was followed
python scripts/verify_protocol_adherence.py  # (if created)

# 8. Analyze results
python orchestrator.py analyze
```

---

## Verification Checklist

Before running experiments:

- [ ] Stratified randomizer outputs 1,620 runs
- [ ] Engine balance: 540 ± 0 per engine
- [ ] Time slot balance: 540 ± 0 per time slot
- [ ] Engine×time slot: 180 ± 0 per cell
- [ ] Day balance: 231-232 per day
- [ ] experiments.csv has 36 columns
- [ ] All runs have `status='pending'`
- [ ] Orchestrator recognizes 1,620 runs
- [ ] Randomization seed documented (42)
- [ ] Protocol backed up for pre-registration

---

## FAQ

### Q: Can I change the randomization after starting experiments?

**A:** No, this would invalidate the pre-registration. If you need to change parameters:
1. Complete current experiments (or discard results)
2. Generate new randomization protocol with different seed
3. Start fresh experiments

### Q: What if I need to add more runs later?

**A:** The stratified randomizer generates a fixed 1,620-run protocol. To add runs:
1. Document why additional runs are needed
2. Generate supplementary randomization (use different seed)
3. Clearly mark them as "supplementary batch" in analysis

### Q: How do I verify the randomization worked correctly?

```bash
# Check balance statistics
python scripts/validate_randomizer_anova.py  # Verify no confounding
python scripts/analyze_randomizer_distribution.py  # Visual inspection
```

### Q: Can I run experiments out of order?

**A:** The orchestrator executes in the randomized order specified by the CSV. The `--time-of-day` filter is for practical execution (e.g., only run morning sessions), but within each time slot, the randomized order is preserved.

---

## Next Steps

**For immediate use:**

```bash
# 1. Generate locked protocol
python scripts/test_randomizer_stratified.py --seed 42

# 2. Verify it looks correct
python orchestrator.py status

# 3. Start experiments
python orchestrator.py run
```

**For peer review:**

- Protocol is locked: `results/experiments.csv`
- Seed documented: `RANDOM_SEED = 42`
- Balance validated: See summary statistics above
- Reproducible: Same seed = identical randomization

---

**Status: ✅ Fully operational and ready for experiments**
