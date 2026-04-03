# Addressing All Review Concerns

**Date**: 2026-03-28
**Reviewer Concerns**: 2 HIGH, 3 MEDIUM, 2 Open Questions

---

## Status Summary

| Concern | Priority | Current State | Action Needed |
|---------|----------|---------------|---------------|
| Orchestrator validation incomplete | HIGH | PARTIALLY FIXED | Add fingerprint/checksum |
| config.py contradictory constants | HIGH | DOCUMENTED but CONFUSING | Clarify or remove |
| Randomizer doc inconsistent | MEDIUM | INCORRECT | Fix documentation |
| Temporal command obsolete params | MEDIUM | DOCUMENTED as obsolete | No action needed |
| "Perfect balance" overstatement | MEDIUM | CORRECTED in some files | Fix remaining files |
| config.py design constants | OPEN | Answer needed | Provide guidance |
| Machine-checkable verification | OPEN | MISSING | Create verification tool |

---

## HIGH Priority #1: Orchestrator Validation Incomplete

### The Concern
> orchestrator.py (line 184) treats any existing results/experiments.csv as valid and returns success without verifying provenance, schema version, or fingerprint. The previous guardrails are commented out starting at orchestrator.py (line 223).

### Current State

**What IS validated** (orchestrator.py:184-258):
- ✅ Total runs = 1,620
- ✅ Seed = 42
- ✅ Mode = 'stratified_7day_balanced'
- ✅ Engine balance = 540/540/540
- ✅ Time balance = 540/540/540
- ✅ Engine×Time balance = 179-181

**What is NOT validated**:
- ❌ Matrix fingerprint/checksum
- ❌ Schema version
- ❌ Generation timestamp
- ❌ Canonical matrix hash

### Why This Matters

**Risk**: Someone could:
1. Generate matrix with seed 42 (passes validation)
2. Manually edit 10 rows (still 1,620 runs, still balanced)
3. Run experiments with modified matrix
4. Results don't match pre-registration

**Current protection**:
- Balance checks would catch most edits (hard to maintain 540/540/540 + 179-181 by hand)
- But targeted edits (changing product on a few runs) wouldn't be caught

### Proposed Fix

Add fingerprint validation to orchestrator.py:

```python
def validate_canonical_matrix() -> bool:
    # ... existing checks ...

    # Check 6: Matrix fingerprint (SHA256 of canonical matrix)
    if 'config_fingerprint' in df.columns:
        actual_fingerprint = compute_matrix_fingerprint(df)
        stored_fingerprint = df['config_fingerprint'].iloc[0]

        if actual_fingerprint != stored_fingerprint:
            console.print(f"[red]✗ Matrix fingerprint mismatch[/red]")
            console.print(f"[red]  Matrix may have been edited after generation[/red]")
            return False
    else:
        console.print("[yellow]⚠ Warning: Matrix fingerprint column missing[/yellow]")
        # Don't fail - backward compatibility with old matrices

    return True
```

Where fingerprint is computed as:
```python
def compute_matrix_fingerprint(df: pd.DataFrame) -> str:
    """Compute SHA256 hash of core matrix columns for integrity check."""
    import hashlib

    # Hash only the randomization-defining columns
    core_cols = ['run_id', 'product_id', 'material_type', 'engine',
                 'temperature', 'time_of_day_label', 'repetition_id',
                 'scheduled_datetime', 'scheduled_day_of_week']

    # Sort by run_id for deterministic hashing
    core_data = df[core_cols].sort_values('run_id')

    # Compute hash
    data_str = core_data.to_csv(index=False)
    return hashlib.sha256(data_str.encode()).hexdigest()
```

**Action**: Implement fingerprint validation

---

## HIGH Priority #2: config.py Contradictory Constants

### The Concern
> config.py (line 6) claims the canonical study is a 1,620-run stratified design, but the active constants at config.py (line 21-41) still define a 729-run Cartesian design. That leaves the repo with two contradictory "sources of truth."

### Current State

**config.py header (lines 5-19)**:
```python
# CANONICAL STUDY DESIGN (Finalized 2026-03-28):
# - 1,620 runs generated via stratified randomizer
# - Balance: 540 per engine (exact), 540 per time slot (exact), 179-181 per engine×time slot
# ...
# NOTE: The constants below define the INPUT SPACE for the stratified randomizer.
# They do NOT directly multiply to 1,620.
```

**config.py constants (lines 21-51)**:
```python
PRODUCTS = (3 items)
MATERIALS = (3 items)
TIMES = (3 items)
TEMPS = (3 items)
REPS = (3 items)
ENGINES = (3 items)

# 3×3×3×3×3×3 = 729 (NOT 1,620)
```

### The Problem

**Two interpretations**:
1. **Naive reading**: "If I multiply these constants, I get 729 runs"
2. **Careful reading**: "The comment says these are INPUT to randomizer, not OUTPUT"

**Result**: Confusion for reviewers, potential for misuse

### Why This Exists

The constants ARE used by the stratified randomizer:
- To define product space (3 products)
- To define material types (3 materials)
- To define experimental factors (temps, engines, etc.)

But the randomizer creates 1,620 runs through:
- 7-day temporal structure
- Stratified assignment within days
- Post-hoc balancing

So: `3×3×3×3×3×3 ≠ final run count`

### Options

#### Option A: Keep constants, improve documentation
```python
# CANONICAL STUDY DESIGN (Finalized 2026-03-28):
# - 1,620 runs generated via stratified randomizer (NOT Cartesian product)
# - Generation command: python scripts/test_randomizer_stratified.py --seed 42
#
# ⚠️ WARNING: The constants below DO NOT multiply to 1,620 runs.
# They define the INPUT SPACE. The randomizer creates 1,620 runs via:
#   - 7-day temporal structure (not simple time-of-day factor)
#   - Stratified product×material groups within each day
#   - Engine and time slot balancing (540 each)
#   - This results in 1,620 runs, NOT 3×3×3×3×3×3 = 729
#
# DO NOT COMPUTE: PRODUCTS × MATERIALS × ... to get run count
# DO COMPUTE: len(pd.read_csv('results/experiments.csv'))
```

#### Option B: Remove constants from config.py
```python
# CANONICAL STUDY DESIGN (Finalized 2026-03-28):
# - 1,620 runs generated via stratified randomizer
# - Generation: python scripts/test_randomizer_stratified.py --seed 42
# - All experimental factors defined in the randomizer, not here
#
# NOTE: This file no longer defines PRODUCTS, MATERIALS, etc.
# The canonical design is encoded in results/experiments.csv
# To see experimental factors, read the matrix or randomizer code.

# Only runtime configuration remains:
ENGINE_MODELS = {
    "openai": "gpt-4o",
    "google": "models/gemini-flash-latest",
    "mistral": "mistral-large-2407",
}
```

#### Option C: Metadata-only constants
```python
# EXPERIMENTAL FACTORS (for documentation only, not used for generation)
# The canonical 1,620-run matrix is pre-generated.
# These constants document what's IN the matrix, not how to create it.

PRODUCTS_IN_MATRIX = 3  # smartphone, crypto, supplement
MATERIALS_IN_MATRIX = 3  # faq, digital_ad, blog_post
ENGINES_IN_MATRIX = 3  # openai, google, mistral
...
TOTAL_RUNS = 1620  # Stratified design, not Cartesian product
```

### Recommendation

**Option A** with very clear warnings is best because:
- Constants ARE used by other parts of codebase (validation, scripts)
- Removing them breaks existing code
- Clear documentation prevents misinterpretation

**Action**: Enhance config.py comments with explicit warnings

---

## MEDIUM Priority #3: Inconsistent Randomization Documentation

### The Concern
> scripts/test_randomizer_stratified.py (line 24) describes the design as ... × 20 time slots, but the script itself uses a 7-day, 3-slot structure and the checked-in matrix reflects 21 day-by-slot cells.

### Current State

Looking at the stratified randomizer documentation...

**Line 24 claim** (needs verification): "× 20 time slots"

**Actual design**:
- 7 days (Monday-Sunday)
- 3 time slots (morning/afternoon/evening)
- 21 day×slot combinations (7×3)

**Formula issue**:
- `3×3×3×3×3 × 20` would be 4,860 runs (wrong)
- Actual is 1,620 runs from stratified 7-day design

### Fix Required

Change scripts/test_randomizer_stratified.py line 24 from:
```python
# - Total runs: 1,620 (3 products × 3 materials × 3 temps × 3 engines × 20 time slots)
```

To:
```python
# - Total runs: 1,620 (7 days × 231-232 runs/day, stratified assignment)
#   NOT a simple Cartesian product - uses stratified randomization
```

**Action**: Fix randomizer documentation (already identified in DOCUMENTATION_REVIEW_COMPLETE_2026-03-28.md)

---

## MEDIUM Priority #4: Temporal Command Obsolete Parameters

### The Concern
> The user-facing temporal command still requires --experiment-start at orchestrator.py (line 586), even though matrix generation is disabled and the canonical workflow says scheduling is already baked into results/experiments.csv.

### Current State

**orchestrator.py lines 261-277** (generate_matrix function):
```python
def generate_matrix(
    *,
    force: bool = False,
    temporal: Optional[bool] = None,
    experiment_start_iso: Optional[str] = None,
    duration_hours: Optional[float] = None,
) -> bool:
    """Validate pre-registered matrix (generation disabled for research integrity).

    Parameters:
        force, temporal, experiment_start_iso, duration_hours: OBSOLETE
            These parameters are retained for API compatibility but are not used.
            The pre-registered matrix already contains the temporal schedule.
    """
```

### Assessment

**Status**: ✅ ALREADY DOCUMENTED AS OBSOLETE

The parameters:
- Are marked as OBSOLETE in docstring
- Are not used in function body
- Are kept for backward compatibility

### Why This is OK

**Temporal workflow**:
- OLD: Pass --experiment-start to generate matrix on-the-fly
- NEW: Matrix is pre-generated with scheduled_datetime already in CSV
- Parameters are ignored but kept so old scripts don't break

**CLI impact**:
- If someone passes --experiment-start, it's silently ignored
- No error, no misleading behavior
- Matrix validation happens regardless

### Potential Improvement

Could add deprecation warning:
```python
def generate_matrix(...):
    if experiment_start_iso or duration_hours or temporal is not None:
        console.print("[yellow]⚠ Warning: Temporal parameters are obsolete and ignored[/yellow]")
        console.print("[yellow]  The pre-registered matrix already contains scheduling[/yellow]")
```

**Action**: Consider adding deprecation warning (low priority)

---

## MEDIUM Priority #5: "Perfect Balance" Overstatement

### The Concern
> The "perfect balance" claim in config.py (line 9) is overstated. The checked-in 1,620-row matrix is balanced at the top level, but engine-by-time cells are not literally identical; they distribute as 179/180/181 due to remainders.

### Current State

**config.py line 9** (CORRECT):
```python
# - Balance: 540 per engine (exact), 540 per time slot (exact), 179-181 per engine×time slot
```

**Other files** (from DOCUMENTATION_REVIEW_COMPLETE_2026-03-28.md):
- ❌ RANDOMIZATION_WORKFLOW.md lines 38, 101, 110: Claims "180" (should be 179-181)
- ❌ README.md: May have overstatements
- ✅ config.py: Already correct

### Assessment

**Status**: ✅ config.py IS CORRECT (says 179-181)

**Problem**: Other documentation files say "180" or "perfect"

**Already identified in**: DOCUMENTATION_REVIEW_COMPLETE_2026-03-28.md

**Action**: Fix documentation files (separate from config.py, which is already correct)

---

## Open Question #1: Should config.py Contain Executable Design Constants?

### The Question
> If results/experiments.csv is now the canonical preregistered artifact, should config.py still contain executable design constants at all, or should it become metadata-only for the run phase?

### Analysis

**Current use of constants**:

1. **stratified randomizer** (scripts/test_randomizer_stratified.py):
   ```python
   from config import PRODUCTS, MATERIALS, ENGINES, TEMPS, REPS, TIMES
   # Uses these to generate 1,620-run matrix
   ```

2. **validation scripts** (potentially):
   ```python
   from config import ENGINES
   # Checks that CSV contains these 3 engines
   ```

3. **ENGINE_MODELS mapping**:
   ```python
   from config import ENGINE_MODELS
   # Used by runner to know which API model to call
   ```

**If we remove constants**:
- ❌ Randomizer can't import them (need to hardcode)
- ❌ Validation scripts break
- ✅ Can't accidentally regenerate matrix with wrong parameters

**If we keep constants**:
- ✅ Randomizer can use them
- ✅ Single source of truth for experimental factors
- ❌ Someone might think they can change them

### Recommendation

**Keep constants BUT change their role**:

```python
# config.py

# ===============================================================
# CANONICAL STUDY DESIGN - PRE-REGISTERED (Do Not Modify)
# ===============================================================
# The 1,620-run matrix is pre-generated and locked.
# These constants document the pre-registered design.
# Modifying them will NOT change the experiment (matrix is already generated).
#
# To regenerate matrix (ONLY for sensitivity analysis or new study):
#   python scripts/test_randomizer_stratified.py --seed 42
#
# WARNING: Regenerating the matrix invalidates pre-registration.
# ===============================================================

# Experimental factors (pre-registered, do not modify)
PRODUCTS = ("smartphone_mid", "cryptocurrency_corecoin", "supplement_melatonin")
MATERIALS = ("faq.j2", "digital_ad.j2", "blog_post_promo.j2")
ENGINES = ("openai", "google", "mistral")
TEMPS = (0.2, 0.6, 1.0)
REPS = (1, 2, 3)
TIMES = ("morning", "afternoon", "evening")

# Note: These define the INPUT SPACE for randomization.
# The stratified randomizer creates 1,620 runs (not 3×3×3×3×3×3 = 729).
# Run count comes from 7-day temporal structure + stratified balancing.

# ===============================================================
# RUNTIME CONFIGURATION (can be modified)
# ===============================================================

# Engine-to-model mapping (can be updated if models change)
ENGINE_MODELS = {
    "openai": "gpt-4o",
    "google": "models/gemini-flash-latest",
    "mistral": "mistral-large-2407",
}
```

**Answer**: YES, keep constants, but clearly separate "pre-registered design" (read-only) from "runtime config" (modifiable).

---

## Open Question #2: Machine-Checkable Matrix Verification

### The Question
> If the stratified CSV is authoritative, the repo still needs one machine-checkable way to prove the current file is the expected locked matrix.

### Proposed Solution

Create `scripts/verify_canonical_matrix.py`:

```python
#!/usr/bin/env python3
"""Verify that results/experiments.csv is the canonical pre-registered matrix.

Usage:
    python scripts/verify_canonical_matrix.py

Exit codes:
    0 = Valid canonical matrix
    1 = Invalid or missing matrix
"""

import sys
import hashlib
import pandas as pd
from pathlib import Path

# Canonical matrix properties (pre-registered 2026-03-28)
CANONICAL_TOTAL_RUNS = 1620
CANONICAL_SEED = 42
CANONICAL_MODE = 'stratified_7day_balanced'
CANONICAL_FINGERPRINT = "abc123..."  # SHA256 hash of canonical matrix

def compute_fingerprint(df: pd.DataFrame) -> str:
    """Compute SHA256 fingerprint of matrix core columns."""
    core_cols = ['run_id', 'product_id', 'material_type', 'engine',
                 'temperature', 'time_of_day_label', 'repetition_id']
    core_data = df[core_cols].sort_values('run_id')
    data_str = core_data.to_csv(index=False)
    return hashlib.sha256(data_str.encode()).hexdigest()

def verify_matrix():
    """Verify canonical matrix."""
    matrix_path = Path("results/experiments.csv")

    if not matrix_path.exists():
        print("✗ Matrix not found at results/experiments.csv")
        return False

    df = pd.read_csv(matrix_path)

    # Check 1: Total runs
    if len(df) != CANONICAL_TOTAL_RUNS:
        print(f"✗ Wrong run count: {len(df)} (expected {CANONICAL_TOTAL_RUNS})")
        return False
    print(f"✓ Total runs: {len(df)}")

    # Check 2: Seed
    if df['matrix_randomization_seed'].iloc[0] != CANONICAL_SEED:
        print(f"✗ Wrong seed: {df['matrix_randomization_seed'].iloc[0]}")
        return False
    print(f"✓ Seed: {CANONICAL_SEED}")

    # Check 3: Mode
    if df['matrix_randomization_mode'].iloc[0] != CANONICAL_MODE:
        print(f"✗ Wrong mode: {df['matrix_randomization_mode'].iloc[0]}")
        return False
    print(f"✓ Mode: {CANONICAL_MODE}")

    # Check 4: Fingerprint
    actual_fp = compute_fingerprint(df)
    if actual_fp != CANONICAL_FINGERPRINT:
        print(f"✗ Matrix fingerprint mismatch")
        print(f"  Expected: {CANONICAL_FINGERPRINT[:16]}...")
        print(f"  Actual:   {actual_fp[:16]}...")
        print(f"  → Matrix may have been edited or regenerated")
        return False
    print(f"✓ Fingerprint: {actual_fp[:16]}...")

    # Check 5: Balance
    engine_counts = df['engine'].value_counts()
    if not all(c == 540 for c in engine_counts.values):
        print(f"✗ Engine imbalance: {engine_counts.to_dict()}")
        return False
    print(f"✓ Engine balance: 540/540/540")

    time_counts = df['time_of_day_label'].value_counts()
    if not all(c == 540 for c in time_counts.values):
        print(f"✗ Time slot imbalance: {time_counts.to_dict()}")
        return False
    print(f"✓ Time slot balance: 540/540/540")

    print("\n✓ Matrix is the canonical pre-registered protocol")
    return True

if __name__ == "__main__":
    sys.exit(0 if verify_matrix() else 1)
```

**Usage**:
```bash
# Verify matrix
python scripts/verify_canonical_matrix.py

# Use in CI/CD
python scripts/verify_canonical_matrix.py || exit 1
python orchestrator.py run
```

**Answer**: Create `scripts/verify_canonical_matrix.py` with fingerprint checking

---

## Action Plan

### Immediate (Before Running Experiments):

1. ✅ **Add fingerprint validation** to orchestrator.py
   - Compute SHA256 of core matrix columns
   - Check against stored fingerprint
   - Prevent execution with modified matrix

2. ✅ **Enhance config.py documentation**
   - Add prominent warnings about constants vs run count
   - Separate "pre-registered design" from "runtime config"
   - Make it impossible to misinterpret

3. ✅ **Fix randomizer documentation**
   - Remove misleading "× 20 time slots" formula
   - Use "7 days × 231-232 runs/day" explanation
   - Already identified in previous review

4. ✅ **Create verification script**
   - `scripts/verify_canonical_matrix.py`
   - Machine-checkable proof of canonical matrix
   - Can be run by independent reviewers

### Lower Priority (Before Publication):

5. **Fix remaining balance claims** in documentation
   - Already identified in DOCUMENTATION_REVIEW_COMPLETE_2026-03-28.md
   - Change "180" → "179-181" in RANDOMIZATION_WORKFLOW.md

6. **Add deprecation warning** for temporal parameters
   - Low priority (parameters already documented as obsolete)

---

## Summary Table

| Concern | Valid? | Current Status | Fix Priority | Action |
|---------|--------|----------------|--------------|---------|
| Validation incomplete | ✅ YES | Seed/balance checked, fingerprint missing | HIGH | Add fingerprint check |
| config.py contradictory | ✅ YES | Documented but confusing | HIGH | Enhance warnings |
| Randomizer doc wrong | ✅ YES | "× 20 slots" formula incorrect | MEDIUM | Fix documentation |
| Temporal params obsolete | ⚠️ PARTIAL | Documented but could warn | LOW | Add deprecation warning |
| "Perfect balance" claim | ✅ YES | config.py correct, others wrong | MEDIUM | Fix other docs |
| config.py constants needed? | N/A | Decision needed | N/A | Keep with clear role |
| Machine verification | ✅ YES | Missing | HIGH | Create verify script |

---

**Next steps**: Implement the 4 immediate fixes (fingerprint, config docs, randomizer docs, verify script).
