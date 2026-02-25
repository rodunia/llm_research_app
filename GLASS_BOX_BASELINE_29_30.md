# Glass Box Audit - Baseline Detection Rate: 29/30 (96.7%)

**Date**: 2026-02-24
**Commit**: `fadccdc`
**Status**: Production-ready baseline

---

## Detection Summary

| Metric | Value |
|--------|-------|
| **Total files** | 30 |
| **Detected** | 29 |
| **Missed** | 1 |
| **Detection rate** | 96.7% |

---

## Detection by Product

- **CoreCoin** (cryptocurrency): 10/10 (100%) ✅
- **Melatonin** (supplement): 10/10 (100%) ✅
- **Smartphone**: 9/10 (90%) ⚠️

---

## Missed Detection

### **user_smartphone_4**
- **Ground truth error**: "Adds 16 GB RAM option (not available)"
- **Error type**: Overgeneralization
- **Expected spec**: RAM configurations: 8 GB or 12 GB LPDDR5X
- **Actual claim**: "Nova X5 has RAM configurations of 16 GB"

### **Root Cause Analysis**

**Issue**: RAM keyword pollution in category-based filtering

1. **Keyword substring matching**:
   - Keyword `'ram'` matches substrings: 'f**ram**e', 'g**ram**s', 'prog**ram**'

2. **Category pollution**:
   - Claim "16 GB RAM" categorized correctly as 'ram' ✅
   - But reference pool includes:
     - ✅ "RAM configurations: 8 GB or 12 GB LPDDR5X" (correct)
     - ❌ "Aluminum frame construction" (false match)
     - ❌ "Weight: ~190 grams" (false match)
     - ❌ "Multi-frame computational photography" (false match)
     - ❌ 5× "Advanced multi-frame processing..." (false matches)

3. **NLI comparison failure**:
   - Highest contradiction score: 0.9915 against "Experience Android in its purest form, with absolutely zero bloatware"
   - Correct spec "RAM: 8 GB or 12 GB" did not trigger high enough contradiction

**Status**: Claim WAS flagged as violation, but matched against wrong rule (bloatware instead of RAM spec mismatch).

---

## Attempted Fixes

### **Option 3: Word Boundaries + Remove 'memory' Keyword**

**Commit**: `ff9737f` (reverted)

**Changes**:
```python
# Before:
'ram': ['ram', 'lpddr', 'memory']  # Substring matching

# After:
'ram': [r'\bram\b', r'\blpddr\b']  # Word boundaries, removed 'memory'
```

**Result**:
- ✅ Reduced RAM category pollution (1 spec vs 8+)
- ✅ No 'frame'/'grams' false matches
- ❌ Still matched against bloatware (NLI limitation)
- **Reverted**: Didn't solve root issue

**Why it failed**: Category filtering only applies to specs, not authorized claims. NLI model still compares against ALL authorized claims regardless of category.

---

## Production Baseline Decision

**Accepted 29/30 (96.7%)** as production baseline because:

1. ✅ **High detection rate** - 96.7% is excellent
2. ✅ **Stable and tested** - known safe commit (`fadccdc`)
3. ✅ **Transparent** - missed case documented and understood
4. ✅ **Ready for scale-up** - can proceed with 1,620-file audit
5. ⚠️ **One known limitation** - RAM keyword pollution (documented)

---

## Future Work (Experimental Branch)

**Branch**: `experimental/ram-category-fix`

Potential improvements to test:
1. Apply category filtering to authorized claims (not just specs)
2. Test semantic filtering (`--use-semantic-filter`)
3. Adjust NLI threshold or use different models
4. Improve keyword matching with word boundaries

**Merge criteria**: Must achieve ≥30/30 without breaking any of the 29 current detections.

---

## Files and Commits

- **Baseline commit**: `fadccdc` - "checkpoint: glass_box_audit.py achieving 29/30 detection (96.7%)"
- **Audit script**: `analysis/glass_box_audit.py`
- **Results**: `pilot_results_verification/`
- **Ground truth**: `GROUND_TRUTH_ERRORS.md`

---

## Reproducibility

To reproduce 29/30 baseline:

```bash
# Checkout baseline commit
git checkout fadccdc

# Run pilot validation script
bash scripts/rerun_pilot_audits_fixed.sh

# Check detection summary
cat pilot_results_verification/validation_report.md
```

---

**Status**: ✅ PRODUCTION READY - Safe to proceed with full 1,620-file audit
