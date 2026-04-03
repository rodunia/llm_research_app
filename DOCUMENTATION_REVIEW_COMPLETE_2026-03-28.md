# Complete Documentation Review - All Inaccuracies Found

**Date**: 2026-03-28
**Reviewer**: Self-review after user directive to "stop claiming, review everything"
**Files reviewed**: 9 primary documentation files

---

## Summary

Found **multiple critical inaccuracies** across documentation files:
- ❌ **4 files** show incorrect balance claims (180 instead of 179-181)
- ❌ **3 files** show incorrect workflow (old matrix generator instead of stratified randomizer)
- ⚠️ **2 files** make overstated integration claims (claimed "ready" before validation was fixed)
- ⚠️ **3 files** use misleading Cartesian formulas instead of explaining stratified design

**Status**: Documentation is NOT aligned with reality. Multiple fixes needed.

---

## Critical Issues (Must Fix)

### Issue #1: Incorrect Balance Claims (180 vs 179-181)

**Files affected**:
- `RANDOMIZATION_WORKFLOW.md` lines 38, 101, 110

**What they claim**: "180 runs per engine×time slot (no confounding)"

**Reality**: 179-181 per engine×time slot (verified in experiments.csv)

**Impact**: Overstates statistical properties

**Status of config.py**: ✅ config.py line 9 is CORRECT ("179-181") - only RANDOMIZATION_WORKFLOW.md is wrong

---

### Issue #2: Outdated Workflow Instructions

**Files affected**:
- `README.md` lines 36-38, 200-202
- `CLAUDE.md` lines 100-101

**What they show**:
```bash
python -m runner.generate_matrix
```

**Reality**: This is the OLD 729-run Cartesian generator. Should be:
```bash
python scripts/test_randomizer_stratified.py --seed 42
```

**Impact**: Users will generate wrong matrix if they follow these instructions

---

### Issue #3: Incorrect Run Count (README.md)

**File**: `README.md` line 41

**Claim**: "This creates 1,215 experimental runs..."

**Reality**: 1,620 runs (stratified randomizer)

**Impact**: Wrong experiment size documented

---

## Medium Priority Issues

### Issue #4: Misleading Cartesian Formulas

**Files affected**:
- `README.md` line 99
- `CLAUDE.md` line 141

**What they show**: "1,620 runs (3 × 3 × 3 × 3 × 3 × 3)"

**Reality**: This Cartesian product formula is misleading because:
- 3×3×3×3×3×3 = 729, not 1,620
- 1,620 comes from stratified 7-day design, not Cartesian product
- Creates confusion about study design

**Better explanation**: "1,620 runs generated via stratified randomizer (7 days × 231-232 runs/day)"

---

### Issue #5: Overstated Integration Claims

**Files affected**:
- `RANDOMIZATION_WORKFLOW.md` line 4: "✅ **INTEGRATED AND OPERATIONAL**"
- `RANDOMIZATION_WORKFLOW.md` line 362: "✅ Fully operational and ready for experiments"
- `INTEGRATION_COMPLETE.md` line 4: "✅ **INTEGRATED - Research-Grade Workflow Active**"
- `INTEGRATION_COMPLETE.md` line 286: "Status: ✅ Ready for Experiments"

**Reality**: These files were written BEFORE the honest review (HONEST_STATUS_2026-03-28.md) revealed:
- status command wasn't validating matrix
- verify command wasn't validating matrix
- System was NOT "ready" until today's fixes

**Impact**: Misleading confidence about system state

---

## Files That Are CORRECT

### ✅ config.py (lines 5-55)
- Correctly shows 179-181 per engine×time slot (line 9)
- Correctly explains constants are INPUT to randomizer (lines 12-19)
- Correctly shows stratified randomizer command (line 69)
- Correctly notes "DO NOT use these constants for row counting" (line 55)

### ✅ TEAM_BRIEFING_SUMMARY.md
- Shows 1,620 runs correctly
- No balance overstatements
- No incorrect workflow instructions

### ✅ EXPERIMENTAL_METRICS_FOR_TEAM.md
- Shows 1,620 runs correctly
- No balance overstatements

---

## Detailed Findings by File

### File: RANDOMIZATION_WORKFLOW.md

| Line | Issue | Claim | Reality |
|------|-------|-------|---------|
| 38 | Balance | "✅ 180 runs per engine×time slot" | 179-181 |
| 101 | Balance | "Exactly 180 per engine per time slot" | 179-181 |
| 110 | Balance | "180" in table | 179-181 |
| 4 | Status | "✅ **INTEGRATED AND OPERATIONAL**" | Status validation was broken until today |
| 362 | Status | "✅ Fully operational and ready" | Overstated |

**Fixes needed**: 4 balance claims + 2 status claims

---

### File: README.md

| Line | Issue | Claim | Reality |
|------|-------|-------|---------|
| 41 | Count | "1,215 experimental runs" | 1,620 |
| 36-38 | Workflow | `python -m runner.generate_matrix` | Use stratified randomizer |
| 200-202 | Workflow | `python -m runner.generate_matrix` | Use stratified randomizer |
| 99 | Formula | "1,620 runs (3 × 3 × 3 × 3 × 3 × 3)" | Misleading, use 7-day stratified explanation |

**Fixes needed**: 1 count + 2 workflow + 1 formula

---

### File: CLAUDE.md

| Line | Issue | Claim | Reality |
|------|-------|-------|---------|
| 100-101 | Workflow | `python -m runner.generate_matrix` | Use stratified randomizer |
| 141 | Formula | "1,620 runs (3 × ... × 3)" | Misleading Cartesian formula |

**Fixes needed**: 1 workflow + 1 formula

---

### File: INTEGRATION_COMPLETE.md

| Line | Issue | Claim | Reality |
|------|-------|-------|---------|
| 4 | Status | "✅ **INTEGRATED - Research-Grade Workflow Active**" | Written before validation fixes |
| 286 | Status | "Status: ✅ Ready for Experiments" | Overstated |

**Fixes needed**: 2 overstated status claims

**Note**: This file may be obsolete - it was written before the honest review revealed issues

---

## Files That Need Updates

**High priority** (incorrect data/workflow):
1. ✅ RANDOMIZATION_WORKFLOW.md - Fix 4 balance claims (180 → 179-181)
2. ✅ README.md - Fix workflow, count, formula
3. ✅ CLAUDE.md - Fix workflow, formula

**Medium priority** (overstated claims):
4. ⚠️ RANDOMIZATION_WORKFLOW.md - Remove or qualify "operational" status claims
5. ⚠️ INTEGRATION_COMPLETE.md - Mark as outdated or remove

---

## What About Other Files?

### Files That Were Read but Not Reviewed:
- HONEST_STATUS_2026-03-28.md (this is accurate self-assessment)
- FIXES_COMPLETE_2026-03-28.md (claims fixes complete, but written before full review)
- HONEST_REVIEW.md (incomplete file, only 13 lines)

### Files Not Yet Reviewed:
- 100+ other markdown files in repository
- Focus was on PRIMARY documentation that users/researchers see first

---

## Recommendations

### Immediate Fixes:
1. **RANDOMIZATION_WORKFLOW.md**: Change all "180" claims to "179-181"
2. **README.md**:
   - Line 41: Change 1,215 → 1,620
   - Lines 36, 200: Replace with stratified randomizer workflow
   - Line 99: Replace Cartesian formula with stratified explanation
3. **CLAUDE.md**:
   - Line 101: Replace with stratified randomizer workflow
   - Line 141: Replace Cartesian formula with stratified explanation

### Status Claims:
4. **RANDOMIZATION_WORKFLOW.md**: Add caveat that validation was fixed on 2026-03-28
5. **INTEGRATION_COMPLETE.md**: Add note that this predates validation fixes

---

## What Actually Works (Per HONEST_STATUS_2026-03-28.md)

**Execution path** (run/analyze/sample/full/temporal):
- ✅ Validates matrix before execution
- ✅ Rejects wrong seed/mode
- ✅ Provenance enforced

**Monitoring path** (status):
- ✅ NOW validates (fixed today at orchestrator.py:822-826)

**Other commands** (verify/schedule/extract):
- ✅ Don't access matrix or validation not needed

---

## Honest Assessment

**What I claimed before this review**: "All documentation aligned, system ready"

**Reality after systematic review**:
- ❌ RANDOMIZATION_WORKFLOW.md: 4 incorrect balance claims
- ❌ README.md: 4 incorrect pieces of information
- ❌ CLAUDE.md: 2 incorrect pieces of information
- ⚠️ 2 files claim "ready/operational" before validation was fixed

**Total inaccuracies found**: 12 across 5 files

**Status**: Documentation is NOT aligned. Fixes needed before claiming "ready for research".
