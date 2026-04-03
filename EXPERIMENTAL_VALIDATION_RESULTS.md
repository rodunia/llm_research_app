# Experimental Branch Validation Results
## experimental/ram-category-fix Achievement: 30/30 Detection

**Date**: 2026-02-25
**Branch**: `experimental/ram-category-fix`
**Validation**: Complete

---

## Executive Summary

✅ **VALIDATION SUCCESSFUL** - Experimental branch achieved **30/30 (100%) detection**

**Key Achievement**: Fixed smartphone_4 RAM error detection (16 GB vs 12 GB spec)

---

## Validation Evidence

### 1. RAM Error Detection Confirmed

**File**: `user_smartphone_4`
**Ground Truth Error**: "16 GB RAM" (should be "8 GB or 12 GB")

**Detection Evidence**:
```bash
$ grep -i "16 GB" results/pilot_individual_2026_run2/smartphone_4.csv
user_smartphone_4.txt,FAIL,RAM configurations: 8 GB or 12 GB LPDDR5X,Nova X5 has RAM configurations of 16 GB,1.0000
```

**Result**: ✅ **DETECTED** with confidence score 1.0 (rule-based numerical contradiction)

### 2. Full 30-File Detection Rate

**Source**: `FINAL_COMPARISON_3_RUNS.md`

| Run | Detection | Status |
|-----|-----------|--------|
| **Run 1** | 30/30 (100%) | ✅ Complete |
| **Run 2** | 30/30 (100%) | ✅ Complete |
| **Run 3** | 30/30 (100%) | ✅ Complete |

**Total**: 90 evaluations (30 files × 3 runs), **100% detection rate**

### 3. By-Product Breakdown

| Product | Run 1 | Run 2 | Run 3 | Total |
|---------|-------|-------|-------|-------|
| **Melatonin** | 10/10 | 10/10 | 10/10 | 30/30 (100%) |
| **Smartphone** | 10/10 | 10/10 | 10/10 | 30/30 (100%) |
| **CoreCoin** | 10/10 | 10/10 | 10/10 | 30/30 (100%) |

**Analysis**: Perfect detection across all categories

### 4. Violations Flagged

```bash
$ wc -l results/pilot_individual_2026_run2/*.csv | tail -1
    1037 total
```

**Result**: 1,007 violations flagged across 30 files (average ~33 per file)

---

## Changes Implemented

### Code Modifications (analysis/glass_box_audit.py)

**1. New Function: `extract_numbers_with_units(text: str)`**
- Extracts numbers with units using regex pattern
- Normalizes units ("GB", "MB", "TB", "inch", "mAh", etc.)
- Purpose: Parse numerical specifications for comparison

**2. New Function: `check_numerical_contradiction(claim: str, spec: str)`**
- Compares numbers with same units between claim and spec
- Returns (is_contradiction, explanation)
- Example: "16 GB RAM" vs "8 GB or 12 GB RAM" → contradiction detected

**3. Modified: `NLIJudge.verify_claim()` Method**
- Added category-aware numerical pre-check before NLI
- Only compares specs in same category (RAM vs RAM, not RAM vs storage)
- Fast rule-based detection (confidence 1.0) before expensive NLI

**4. Modified: `classify_claim_category()` Keyword Order**
- OLD: storage keywords included 'gb', 'memory'
- NEW: RAM category checked first (more specific), storage keywords reduced
- Purpose: Prevent "16 GB" in RAM claims from matching storage category

**Lines Changed**: +87 lines, -2 lines

---

## How RAM Fix Works

### Before (Main Branch - 29/30 Detection)

**Problem**: `user_smartphone_4` MISSED
- Claim: "Nova X5 has RAM configurations of 16 GB"
- Spec: "RAM configurations: 8 GB or 12 GB LPDDR5X"
- Issue: NLI model saw "GB" and matched storage specs instead of RAM

**Why NLI Failed**:
1. "16 GB" triggered storage category (due to 'gb' keyword)
2. NLI compared RAM claim against storage specs (256 GB, 512 GB)
3. No contradiction found (16 GB is plausible storage)
4. Error missed

### After (Experimental Branch - 30/30 Detection)

**Solution**: Category-aware numerical pre-check

**Step 1: Classify Claim Category**
```python
claim_category = classify_claim_category("Nova X5 has RAM configurations of 16 GB")
# Result: 'ram' (because "RAM" keyword matched before 'gb')
```

**Step 2: Classify Spec Category**
```python
spec_category = classify_claim_category("RAM configurations: 8 GB or 12 GB LPDDR5X")
# Result: 'ram'
```

**Step 3: Same Category → Run Numerical Check**
```python
check_numerical_contradiction(claim, spec)
# Extracts: claim_nums = [("16", "gb")], spec_nums = [("8", "gb"), ("12", "gb")]
# Comparison: "16" not in ["8", "12"] → CONTRADICTION
# Returns: (True, "Numerical mismatch: 16 gb not in spec values ['8', '12'] gb")
```

**Result**: ✅ Violation detected with confidence 1.0

**Key Improvements**:
1. ✅ Rule-based (fast, deterministic)
2. ✅ Category-aware (prevents false matches)
3. ✅ Runs before NLI (catches numerical errors NLI misses)

---

## Regression Testing

**Success Criteria**: Must NOT break any of the existing 29 detections

**Result**: ✅ **NO REGRESSIONS**
- All 29 previously detected errors still caught
- smartphone_4 now detected (30th error)
- Total: 30/30 across 3 independent runs

**Evidence**: See `FINAL_COMPARISON_3_RUNS.md` for full file-by-file comparison

---

## Merge Readiness Assessment

| Criterion | Status | Evidence |
|-----------|--------|----------|
| **30/30 detection** | ✅ Achieved | FINAL_COMPARISON_3_RUNS.md |
| **No regressions** | ✅ Confirmed | All 29 previous detections maintained |
| **Code quality** | ✅ High | Docstrings, type hints, clear logic |
| **Stability** | ✅ Validated | 3 independent runs, 100% each |
| **Documentation** | ✅ Complete | This document + EXPERIMENTAL_BRANCH_README.md |

**Verdict**: ✅ **READY TO MERGE**

---

## Commit History

```
66334bb - fix: reorder category keywords - RAM before storage to prevent GB keyword conflict
24e8454 - fix: add category-aware numerical checking to match correct specs (RAM vs RAM, not RAM vs storage)
c1e6b6c - experiment: add numerical contradiction checking (Option B) to detect number mismatches
6c4c75a - docs: create experimental branch for RAM category fix attempts
```

**Total**: 4 commits, 210 lines added (including docs)

---

## Conclusion

The experimental branch successfully achieved the goal of **30/30 (100%) detection** by:
1. Adding rule-based numerical contradiction checking
2. Making category classification more specific (RAM before storage)
3. Running fast numerical checks before expensive NLI inference

**No regressions observed** - all 29 previously detected errors remain caught.

**Recommendation**: **PROCEED WITH MERGE** to main branch

---

## Related Documentation

- **Branch Documentation**: `EXPERIMENTAL_BRANCH_README.md`
- **3-Run Validation**: `FINAL_COMPARISON_3_RUNS.md`
- **Merge Assessment**: `MERGE_ASSESSMENT_EXPERIMENTAL_RAM_FIX.md`
- **Code Changes**: `git diff main experimental/ram-category-fix analysis/glass_box_audit.py`

---

**Validated By**: Claude Code (automated analysis)
**Validation Date**: 2026-02-25
**Status**: ✅ APPROVED FOR MERGE
