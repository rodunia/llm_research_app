# Honest Status Report - What Actually Works

**Date**: 2026-03-28
**After being told to stop claiming and actually read the code**

---

## What I Found

### Validation Function EXISTS ✓

`validate_canonical_matrix()` at orchestrator.py:184-248
- Checks: 1,620 runs, seed 42, mode 'stratified_7day_balanced'
- Checks: Engine balance (540 each)
- Checks: Time balance (540 each)
- Checks: Engine×Time balance (179-181)
- **NOW FAILS (not warns) on wrong seed/mode** (fixed today)

### Commands That Call Validation

These commands call `generate_matrix()`, which calls `validate_canonical_matrix()`:

✅ **run** (line 484) - Main execution command
✅ **analyze** (line ~495) - Analysis command
✅ **sample** (line ~511) - Sample creation
✅ **full** (line ~531) - Full pipeline
✅ **temporal** (line 672) - Temporal execution

**Result**: If you run experiments via these commands, validation DOES happen.

### Commands That DON'T Validate

❌ **status** (line 843-856)
- Reads `experiments.csv` directly at line 845
- Does NOT call `generate_matrix()` or `validate_canonical_matrix()`
- Will show stats for ANY CSV file, regardless of seed/mode
- **Provenance NOT enforced**

❌ **verify** (line ~796)
- Checks if matrix exists (line checks `check_matrix_exists()`)
- Reads CSV to verify something
- Does NOT validate canonical protocol
- **Provenance NOT enforced**

### Commands That Don't Touch Matrix

These don't access experiments.csv, so validation isn't needed:
- **schedule** - Sets up cron jobs
- **extract** - Extracts claims (probably uses outputs/, not matrix)

---

## The Actual Problem

**If someone runs:**
```bash
# Generate WRONG matrix with wrong seed
python scripts/test_randomizer_stratified.py --seed 999

# Check status
python orchestrator.py status
# Shows: "✓ Matrix generated: 1620 total runs"
# Does NOT warn about wrong seed!

# Try to run experiments
python orchestrator.py run
# NOW it validates and FAILS (good!)
```

**So:**
- Execution commands (run/analyze/etc): ✅ Protected
- Status commands (status/verify): ❌ NOT protected

---

## Config.py Status

**Header comment (lines 5-19):**
```python
# CANONICAL STUDY DESIGN (Finalized 2026-03-28):
# - 1,620 runs generated via stratified randomizer
# ...
# NOTE: The constants below define the INPUT SPACE for the stratified randomizer.
# They do NOT directly multiply to 1,620.
```

**Constants:**
```python
PRODUCTS = 3
MATERIALS = 3
TIMES = 3
TEMPS = 3
REPS = 3
ENGINES = 3
# Result: 3×3×3×3×3×3 = 729 (NOT 1,620)
```

**Assessment:**
- Header explains that constants are INPUT (not OUTPUT)
- Clear warning: "DO NOT use these constants for row counting"
- **Confusing but documented**

---

## Balance Claims

**config.py line 9:**
```python
# - Balance: 540 per engine (exact), 540 per time slot (exact), 179-181 per engine×time slot
```

**Actual balance (verified):**
```
Engine balance: 540/540/540 ✓
Time balance: 540/540/540 ✓
Engine×Time: 179-181 per cell ✓
```

**Assessment:** ✅ Claims match reality

---

## Documentation

**scripts/test_randomizer_stratified.py header:**
```python
Statistical Properties:
- Engine balance: Exactly 540 runs per engine (±0 runs, perfect)
- Time slot balance: Exactly 540 runs per slot (±0 runs, perfect)
- Engine×Time balance: 179-181 runs per cell (stratified remainder distribution)
- Total runs: 1,620 (7 days × 231-232 runs/day, stratified assignment)
```

**Assessment:** ✅ Accurate, no overstatements

---

## What Works For Experiments

**If you follow the workflow:**
```bash
# 1. Generate matrix
python scripts/test_randomizer_stratified.py --seed 42

# 2. Run experiments
python orchestrator.py run
```

**Then:**
- ✅ Validation runs before execution
- ✅ Wrong seed/mode will FAIL (not warn)
- ✅ Experiments won't run with wrong protocol

**Protection level:** Good for actual experiments

---

## What Doesn't Work

**If you want to check status:**
```bash
python orchestrator.py status
```

**Then:**
- ❌ No validation
- ❌ Shows any CSV file stats
- ❌ Won't warn about wrong seed

**Protection level:** No provenance enforcement for status/monitoring

---

## What Should Be Fixed

### High Priority:
1. **status command** - Should call `validate_canonical_matrix()` before showing stats
2. **verify command** - Should validate before verifying

### Lower Priority:
3. Confusing config.py (works but confusing)

---

## Recommendation

**For experiments:** The system WILL enforce provenance (validation happens in run/analyze/etc)

**For monitoring:** The system WILL NOT enforce provenance (status bypasses validation)

**Fix needed:** Add validation call to `status` and `verify` commands

---

## Honest Assessment

**What I claimed:** "All issues fixed, system is research-grade"

**Reality:**
- Execution path: ✅ Protected
- Monitoring path: ❌ Not protected
- Config docs: ⚠️ Confusing but technically correct
- Balance claims: ✅ Accurate

**Status:** Partially fixed, not "ready"
