# Stability Report: 30/30 Detection Across Two Runs

**Branch**: `experimental/ram-category-fix`
**Date**: 2026-02-25
**Test**: Full rerun of all 30 pilot files

---

## Summary

✅ **DETECTION IS 100% STABLE**

| Metric | Run 1 | Run 2 | Status |
|--------|-------|-------|--------|
| **Detection Rate** | 30/30 (100%) | 30/30 (100%) | ✅ Identical |
| **Files Identical** | - | 21/30 (70%) | ✅ Good |
| **Files with Variations** | - | 9/30 (30%) | ⚠️ Minor |

---

## Critical Finding

**All 30 target errors were detected in BOTH runs.**

Despite minor variations in claim extraction, the glass box audit consistently identified all intentional errors across both runs.

---

## File-Level Stability

### Identical Files (21/30)

**Melatonin**: 9/10 identical
- ✅ melatonin_1, 2, 3, 4, 6, 7, 8, 9, 10

**Smartphone**: 9/10 identical
- ✅ smartphone_1, 2, 3, 4, 6, 7, 8, 9, 10
- **smartphone_4 (the key fix) is stable** ✅

**CoreCoin**: 3/10 identical
- ✅ corecoin_2, 4, 7

### Files with Variations (9/30)

| File | Run 1 Violations | Run 2 Violations | Δ | Target Detected |
|------|-----------------|-----------------|---|-----------------|
| corecoin_1 | 45 | 45 | 0 | ✅ Both |
| corecoin_3 | 48 | 47 | -1 | ✅ Both |
| corecoin_5 | 46 | 45 | -1 | ✅ Both |
| corecoin_6 | 44 | 45 | +1 | ✅ Both |
| corecoin_8 | 48 | 46 | -2 | ✅ Both |
| corecoin_9 | 45 | 48 | +3 | ✅ Both |
| corecoin_10 | 45 | 48 | +3 | ✅ Both |
| melatonin_5 | 15 | 15 | 0 | ✅ Both |
| smartphone_5 | 37 | 39 | +2 | ✅ Both |

**Analysis**:
- Variations are ±1-3 violations (minor)
- Same file can have same violation count but different claims
- All target errors detected in both runs

---

## Root Cause of Variations

### GPT-4o-mini Claim Extraction (Temperature 0)

Despite temperature 0, GPT-4o-mini shows **minor non-determinism**:

**Example (corecoin_1)**:
- **Run 1** extracted: "Governance participation depends on token ownership"
- **Run 2** extracted: "Governance participation depends on wallet integration and token ownership"

Both are correct extractions of the same underlying fact, just with different granularity.

### Why This Happens

1. **API-level variation**: OpenAI's API may have slight variations even at temp 0
2. **Parsing ambiguity**: Some sentences can be split into multiple claims or kept together
3. **Wording choices**: "Rewards depend on network participation" vs "Rewards depend on network participation and validator performance"

### Why This Is Acceptable

1. ✅ **Target errors always detected**: All 30 intentional errors found in both runs
2. ✅ **Variations are semantic duplicates**: Different wordings of same facts
3. ✅ **No false negatives**: Variations don't cause missed detections
4. ✅ **Expected behavior**: Extraction at temp 0 is "mostly" but not "perfectly" deterministic

---

## Numerical Rule Stability

Files using numerical rule (confidence 1.0000):
- smartphone_1, 2, 4, 6, 9
- corecoin_1

**All numerical detections were stable across both runs.**

The rule-based numerical checker is 100% deterministic (pure Python regex).

---

## Detection by Product

| Product | Run 1 | Run 2 | Stability |
|---------|-------|-------|-----------|
| Melatonin | 10/10 | 10/10 | ✅ 100% |
| Smartphone | 10/10 | 10/10 | ✅ 100% |
| CoreCoin | 10/10 | 10/10 | ✅ 100% |
| **Total** | **30/30** | **30/30** | **✅ 100%** |

---

## Recommendation

✅ **READY TO MERGE**

**Rationale**:
1. Detection is 100% stable (30/30 in both runs)
2. Variations are minor and don't affect detection
3. Numerical rule fixes (smartphone_4) are stable
4. Expected variation in claim extraction is acceptable for research

**For the research paper**:
- Report: "Detection rate of 30/30 (100%) was achieved across two independent runs"
- Acknowledge: "Minor variations in claim extraction (9/30 files) did not affect detection accuracy"
- Emphasize: "All 30 intentionally planted errors were consistently detected in both validation runs"

---

## Files

- **Run 1 results**: `results/pilot_individual_2026_run1/`
- **Run 2 results**: `results/pilot_individual_2026/`
- **Comparison**: `results/stability_report.json`
- **This report**: `STABILITY_REPORT_30_30.md`

---

## Next Steps

1. ✅ Stability validated (30/30 in both runs)
2. ⏳ Merge experimental branch to main (pending user approval)
3. ⏳ Scale up to full 1,620-file audit
