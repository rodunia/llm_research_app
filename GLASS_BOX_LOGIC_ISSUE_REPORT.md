# Glass Box Logic Issue Report

**Date**: March 11, 2026
**Status**: ⚠️ CRITICAL - Affects pilot study results validity

---

## Executive Summary

Glass Box has a fundamental logical flaw in how it verifies claims against YAML rules. The code correctly implements NLI matching, but the **YAML structure mixes different types of rules** that require different verification logic.

**Impact**: Current pilot results show 1,099 violations, but estimated **50-70% are false positives**.

---

## Root Cause Analysis

### Problem 1: YAML Specs Contain Two Types of Statements

Example from `products/supplement_melatonin.yaml`:

```yaml
specs:
  formulation:
    - "No herbal extracts or proprietary blends"  # FACTUAL (product attribute)
    - "Vegan, Non-GMO, and free from gluten"      # FACTUAL

clarifications:
    - "Melatonin does not modify REM/deep-sleep architecture"  # NEGATIVE STATEMENT
    - "No habit formation when used according to directions"   # NEGATIVE STATEMENT
```

**Issue**: Both types are treated as "factual references" to check for CONTRADICTION.

### Problem 2: Incorrect NLI Logic Application

**Current (WRONG) logic after attempted fix:**
```python
# CHECK 1: Does claim CONTRADICT factual references?
for spec in specs + authorized + clarifications:
    if NLI(claim, spec) == 'contradiction' and score > 0.90:
        flag_violation()
```

**Why this fails:**
- Claim: "The formulation is vegan"
- Spec: "No herbal extracts or proprietary blends"
- NLI returns: HIGH CONTRADICTION (0.98)
- Reason: "vegan" doesn't directly mention "herbal extracts", so NLI sees mismatch

**But this is WRONG!** "Vegan" and "No herbal extracts" are **compatible facts**, not contradictions.

---

## The Deeper Issue: Positive vs Negative Statements

### Type A: Positive Factual Specs
These describe what the product **IS** or **HAS**:
- "Vegan, Non-GMO, and free from gluten"
- "Each tablet contains 3 mg melatonin"
- "120 tablets per bottle"

**Verification logic**: Marketing claims should **ENTAIL** (match/support) these.
- Claim "vegan" vs Spec "Vegan, non-GMO" → ENTAILMENT = ✅ GOOD

### Type B: Negative Clarifications
These describe what the product **IS NOT** or **DOES NOT**:
- "No herbal extracts"
- "Does not modify REM architecture"
- "Not FDA-approved"

**Verification logic**: Marketing claims should NOT **CONTRADICT** these.
- Claim "contains herbal blend" vs Clarification "No herbal extracts" → CONTRADICTION = ❌ VIOLATION

### Type C: Prohibited Claims
These are statements marketing **SHOULD NOT MAKE**:
- "Claims about modifying REM architecture"
- "Guarantees of next-day alertness"
- "Claims it treats insomnia"

**Verification logic**: Marketing claims should NOT **ENTAIL** (match) these.
- Claim "improves REM sleep" vs Prohibited "Claims about modifying REM" → ENTAILMENT = ❌ VIOLATION

---

## Why Current Fix Didn't Fully Work

The 3/11 fix separated prohibited claims (CHECK 2: entailment) from specs (CHECK 1: contradiction).

**Progress**: Reduced violations from 34 → 26 (24% reduction).

**Remaining issue**: Specs still contain MIX of:
1. Positive facts ("Vegan") - should check ENTAILMENT
2. Negative facts ("No herbal extracts") - should check CONTRADICTION
3. Clarifications moved to wrong category

---

## Correct Solution Options

### Option A: Restructure YAMLs (Recommended)
Split specs into positive and negative categories:

```yaml
specs_positive:  # Product HAS these attributes
  - "Vegan, Non-GMO, gluten-free"
  - "3 mg melatonin per tablet"
  - "120 tablets per bottle"

specs_negative:  # Product DOES NOT have these
  - "No herbal extracts"
  - "Not extended-release"
  - "Not gummies or chewables"

clarifications:  # Regulatory/safety statements
  - "Does not modify REM architecture"
  - "Not FDA-approved as drug"
```

**Then verify**:
- Positive specs → Check ENTAILMENT (claim should match)
- Negative specs → Check NON-CONTRADICTION (claim should not contradict)
- Prohibited → Check NON-ENTAILMENT (claim should not match)

### Option B: Smarter NLI Logic (Workaround)
Detect "No X" / "Not X" patterns in specs and invert the logic:

```python
if "no " in spec.lower() or "not " in spec.lower():
    # Negative spec: check for contradiction
    if contradiction_score > 0.90:
        flag_violation()
else:
    # Positive spec: check for entailment
    if entailment_score < 0.50:  # Claim doesn't support spec
        flag_violation()
```

**Risk**: Hacky, error-prone.

### Option C: Manual Rule Validation (Quick Fix for Pilot)
Manually review all 1,099 violations and mark true vs false positives.

**Pros**: Gets accurate pilot results.
**Cons**: Time-consuming, doesn't fix underlying issue.

---

## Recommendation

**For pilot study publication**:
1. Use Option C: Manual validation of 50-100 random violations
2. Calculate true false positive rate
3. Report adjusted violation counts with confidence intervals

**For full 1,620-run study**:
1. Implement Option A: Restructure all 3 product YAMLs
2. Re-run Glass Box on pilot data to validate fix
3. Proceed with full experiment once accuracy confirmed >95%

---

## Current Pilot Results Status

- **Total violations detected**: 1,099
- **Estimated false positive rate**: 50-70%
- **True violations (estimated)**: 330-550
- **Action required**: Manual validation before publishing

---

## Next Steps

**Immediate (today)**:
1. Decision: Manual validation OR YAML restructure?
2. If manual: Sample 50 violations, classify true/false
3. If restructure: Update 3 product YAMLs, re-run pilot Glass Box

**Before full experiment**:
1. Validate Glass Box accuracy >95% on known ground truth
2. Document verification logic in paper methodology
3. Include false positive analysis in limitations section

---

## Files Affected

- `analysis/glass_box_audit.py` (lines 345-525) - NLI verification logic
- `products/supplement_melatonin.yaml` - Mixed spec types
- `products/smartphone_mid.yaml` - Mixed spec types
- `products/cryptocurrency_corecoin.yaml` - Mixed spec types
- `results/pilot_analysis/all_violations.csv` - Contains false positives

---

**Report generated**: 2026-03-11 12:33 PST
**Priority**: URGENT - Blocks pilot study publication
