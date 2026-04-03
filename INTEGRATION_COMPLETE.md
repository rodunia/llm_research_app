# Stratified Randomizer Integration - Complete

**Date**: 2026-03-28
**Status**: ✅ **INTEGRATED - Research-Grade Workflow Active**

---

## Summary

The application now enforces **pre-registered randomization protocol** for academic research integrity.

### What Changed:

1. **Matrix generation disabled in orchestrator** - `orchestrator.py:208-233`
   - On-the-fly generation blocked (prevents p-hacking)
   - Clear error message guides users to pre-registration workflow

2. **Locked protocol established** - `preregistration/locked_protocol_2026-03-28_seed42.csv`
   - 1,620 runs with seed=42
   - Perfect statistical balance validated
   - Timestamped and archived for peer review

3. **Active matrix validated** - `results/experiments.csv`
   - Generated from stratified randomizer
   - 540 runs per engine (perfect balance) ✅
   - 540 runs per time slot (perfect balance) ✅
   - All runs status='pending', ready to execute

---

## The Workflow (Now Enforced)

### Before Experiments (Pre-Registration)

```bash
# 1. Generate locked randomization protocol
python scripts/test_randomizer_stratified.py --seed 42

# 2. Verify balance
python orchestrator.py status
# Should show: 1620 total runs, 540/540/540 engines

# 3. Archive for pre-registration
cp results/experiments.csv preregistration/locked_protocol_$(date +%Y-%m-%d).csv
git add preregistration/
git commit -m "Pre-register randomization protocol"
```

### During Experiments (Execute Protocol)

```bash
# Execute all runs according to locked protocol
python orchestrator.py run

# Or execute by time slot
python orchestrator.py run --time-of-day morning
python orchestrator.py run --time-of-day afternoon
python orchestrator.py run --time-of-day evening
```

### What You CANNOT Do Anymore

```bash
# This is now BLOCKED ❌
python orchestrator.py generate

# Output:
# ERROR: Matrix generation disabled for research integrity.
# The experimental matrix must be pre-generated using:
#   python scripts/test_randomizer_stratified.py --seed 42
```

---

## Validation

### Current Matrix Properties

**File**: `results/experiments.csv`
**Generated**: 2026-03-28 (today)
**Method**: Stratified randomizer with seed 42

**Balance verification:**
```python
import pandas as pd
df = pd.read_csv('results/experiments.csv')

# Engine balance
assert df['engine'].value_counts().to_dict() == {'openai': 540, 'google': 540, 'mistral': 540}

# Time slot balance
assert df['time_of_day_label'].value_counts().to_dict() == {'morning': 540, 'afternoon': 540, 'evening': 540}

# All pending
assert (df['status'] == 'pending').all()

print("✅ All validation checks passed")
```

**Result**: ✅ Perfect balance confirmed

---

## Addressing Previous Issues

### Issue #1: config.py constants ≠ 1,620 ✅ RESOLVED

**Before:**
- config.py claimed 1,620 runs
- Constants multiplied to 729

**After:**
- config.py lines 5-10 now document that 1,620 comes from stratified randomizer
- config.py lines 57-61 explain how to generate the matrix
- Constants (PRODUCTS, MATERIALS, etc.) are still used by randomizer internally

### Issue #2: Orchestrator bypassed stratified randomizer ✅ RESOLVED

**Before:**
- orchestrator.py called `runner.generate_matrix` (simple Cartesian product)
- Would generate 729 runs, not 1,620

**After:**
- orchestrator.py:208-233 now **blocks** on-the-fly generation
- Forces users to pre-generate via stratified randomizer
- Enforces research integrity workflow

### Issue #3: "Perfect balance" claim ✅ VERIFIED

**Validation report concern:**
- Old validation report (March 16) showed imbalances
- That was from earlier randomizer version

**Current state:**
- New matrix (March 28, seed 42) has **perfect** balance
- 540/540/540 engines (±0%)
- 540/540/540 time slots (±0%)
- Verified programmatically above

---

## File Manifest

### Pre-Registration Archive
- `preregistration/locked_protocol_2026-03-28_seed42.csv` - Canonical locked protocol
- Git-tracked for peer review and reproducibility

### Active Execution
- `results/experiments.csv` - Active matrix (orchestrator reads this)
- Generated from `scripts/test_randomizer_stratified.py --seed 42`
- 1,620 rows (all status='pending')

### Documentation
- `RANDOMIZATION_WORKFLOW.md` - Complete workflow guide
- `INTEGRATION_COMPLETE.md` - This file (integration summary)
- `config.py` - Updated with stratified randomizer instructions

### Code Changes
- `scripts/test_randomizer_stratified.py:95` - Output path changed to `results/experiments.csv`
- `scripts/test_randomizer_stratified.py:704-803` - Modified to output full orchestrator schema
- `orchestrator.py:208-233` - Matrix generation disabled with helpful error

---

## Next Steps

### Immediate: Ready to Execute

```bash
# Verify matrix is ready
python orchestrator.py status

# Start experiments
python orchestrator.py run
```

### For Peer Review

When submitting for publication:

1. **Include pre-registered protocol**
   - File: `preregistration/locked_protocol_2026-03-28_seed42.csv`
   - Date: 2026-03-28
   - Seed: 42
   - Total runs: 1,620

2. **Document randomization method**
   - Stratified randomization (7-day × 9 product-material groups)
   - Perfect balance guarantees (540 per engine, 540 per time slot)
   - Reproducible (fixed seed)

3. **Provide verification script**
   ```python
   # verify_protocol.py
   import pandas as pd
   df = pd.read_csv('results/experiments.csv')

   # Check balance
   assert df['engine'].value_counts().to_dict() == {'openai': 540, 'google': 540, 'mistral': 540}
   assert df['time_of_day_label'].value_counts().to_dict() == {'morning': 540, 'afternoon': 540, 'evening': 540}

   # Check randomization mode
   assert df['matrix_randomization_mode'].iloc[0] == 'stratified_7day_balanced'
   assert df['matrix_randomization_seed'].iloc[0] == 42

   print("✅ Protocol verified")
   ```

---

## FAQ

### Q: Can I regenerate the matrix if needed?

**A:** Only in exceptional circumstances (e.g., discovering a critical bug before any runs execute).

To regenerate:
```bash
# 1. Document why regeneration is needed
echo "Reason: [describe critical issue]" > preregistration/regeneration_justification.txt

# 2. Backup old protocol
mv results/experiments.csv preregistration/abandoned_protocol_$(date +%Y-%m-%d).csv

# 3. Generate new protocol with DIFFERENT seed (to distinguish from original)
python scripts/test_randomizer_stratified.py --seed 999

# 4. Document in git
git add preregistration/
git commit -m "Emergency protocol regeneration: [reason]"
```

### Q: What if the March 25th protocol had different balance?

**A:** The March 25th CSV (`results/randomizer_dry_run_2026-03-25.csv`) was from an earlier randomizer version.

The **current canonical protocol** is:
- File: `results/experiments.csv`
- Generated: 2026-03-28
- Seed: 42
- Balance: Perfect (540/540/540 engines, 540/540/540 time slots)

The March 25th file is kept for historical reference but is not the active protocol.

### Q: How do I verify the protocol wasn't changed after experiments started?

**A:** Use git history:

```bash
# Check when experiments.csv was last modified
git log -1 --format="%ai %s" -- results/experiments.csv

# Verify no changes after pre-registration
git diff preregistration/locked_protocol_2026-03-28_seed42.csv results/experiments.csv
# Should show: no differences (or only runtime metadata like started_at, status)
```

---

## Technical Notes

### Why Disable On-The-Fly Generation?

**Research integrity reasons:**

1. **Prevents p-hacking** - Can't regenerate randomization to get "better" results
2. **Ensures pre-registration** - Protocol must be locked before experiments
3. **Enables verification** - Reviewers can check you followed the protocol
4. **Standard practice** - Clinical trials use this approach

### Schema Compatibility

The stratified randomizer now outputs the **full orchestrator schema** (36 columns):

- Core identifiers: run_id, product_id, material_type, engine
- Prompt info: prompt_id, prompt_text_path, system_prompt
- Model setup: temperature, max_tokens, seed, top_p, frequency_penalty, presence_penalty
- Run context: time_of_day_label, repetition_id, scheduled_datetime, scheduled_day_of_week
- Response data: prompt_tokens, completion_tokens, finish_reason, output_path, status
- Metadata: matrix_randomization_seed, matrix_randomization_mode

This ensures seamless execution by orchestrator with no conversion needed.

---

## Status: ✅ Ready for Experiments

**Pre-registration**: Complete
**Protocol locked**: Yes (`preregistration/locked_protocol_2026-03-28_seed42.csv`)
**Active matrix**: Validated (`results/experiments.csv`, 1,620 runs, perfect balance)
**Execution path**: Research-grade workflow enforced
**Documentation**: Complete

**You can now run experiments with confidence in the statistical rigor and reproducibility of the design.**
