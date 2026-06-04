# Glass Box Audit System Validation Results

**Date**: 2026-06-04
**Validation dataset**: 30 pilot files with ground truth errors (10 per product)
**Tested systems**: Old system (glass_box_audit.py) vs New 4-stage pipeline

---

## 📊 Detection Results

| System | Detected | Detection Rate | False Positives |
|--------|----------|----------------|-----------------|
| **Old System** (glass_box_audit.py) | **30/30** | **100%** ✅ | High (multiple per file) |
| **New System** (4-stage pipeline) | 2/30 | 6.7% ❌ | 0% (Claude filtered all) |

---

## ✅ Old System Validation - PASSED

**System**: `analysis/glass_box_audit.py`

### Architecture
- **Extraction**: GPT-4o with forensic prompt ("Extract EVERY verifiable fact")
- **Verification**: RoBERTa NLI cross-encoder (single decision point)
- **Threshold**: Contradiction score > 0.90

### Performance
- ✅ **100% detection rate** (30/30 ground truth errors)
- ✅ Detected critical errors:
  - melatonin_1: 5mg dosage error (score: 0.998)
  - smartphone_1: 6.5" display error (score: 0.997)
  - melatonin_7: Unsafe "every 2 hours" dosage (score: 0.973)
  - corecoin violations: Multiple regulatory/technical errors
- ⚠️  High false positive rate (332 total violations across 30 files)
- ⚠️  Requires human review to filter false positives

### Validation Verdict
**PASSED** - Ready to run on full 1,620 materials dataset.

**Recommendation**: Use old system for production audit. Accept high FP rate as tradeoff for 100% recall. Human review will filter false positives.

---

## ❌ New System Validation - FAILED

**System**: 4-stage pipeline (saved to branch `pipeline-v2-conservative-4stage`)

### Architecture
- **Stage 1**: GPT-4o with conservative prompt ("DO NOT search aggressively")
- **Stage 2**: RoBERTa NLI validation with semantic pre-filtering
- **Stage 3**: Disagreement detection and routing
- **Stage 4**: Claude review as arbitrator

### Performance
- ❌ **6.7% detection rate** (2/30 ground truth errors)
- ❌ GPT-4o missed 28/30 errors due to conservative prompt
- ❌ Claude filtered ALL 27 disagreements as false positives (100% FP rate)
- ❌ Would allow 28/30 dangerous errors to reach production

### Root Causes
1. **Conservative extraction prompt**: "DO NOT search aggressively" → 93% miss rate
2. **Multi-stage filtering**: 3 decision points = 3 opportunities to filter real violations
3. **Claude over-filtering**: Classified all violations as false positives, including:
   - "Take melatonin every 2 hours" (dangerous dosage)
   - "5mg vs 3mg" dosage error
   - "6.5\" vs 6.3\"" display error

### Validation Verdict
**FAILED** - Not safe for production use.

**Disposition**: Saved to branch for future improvement. Do NOT use for full audit.

---

## Ground Truth Sample (10/30 errors)

| File | Product | Ground Truth Error | Old System | New System |
|------|---------|-------------------|------------|------------|
| melatonin_1 | Supplement | 5mg dosage (should be 3mg) | ✅ Detected (0.998) | ❌ Missed |
| melatonin_7 | Supplement | "Every 2 hours" unsafe dosage | ✅ Detected (0.973) | ✅ Detected (filtered by Claude) |
| melatonin_8 | Supplement | "Store at 0°C" error | ✅ Detected | ✅ Detected (filtered by Claude) |
| smartphone_1 | Electronics | 6.5" display (should be 6.3") | ✅ Detected (0.997) | ❌ Missed |
| smartphone_2 | Electronics | 16GB RAM (should be 8/12GB) | ✅ Detected | ❌ Missed |
| corecoin_1 | Crypto | 4s block time (should be ~5s) | ✅ Detected | ❌ Missed |
| corecoin_4 | Crypto | "Guaranteed returns" claim | ✅ Detected | ❌ Missed |
| corecoin_5 | Crypto | "SEC approval" claim | ✅ Detected | ❌ Missed |
| corecoin_9 | Crypto | "Risk-free investment" claim | ✅ Detected | ❌ Missed |
| corecoin_10 | Crypto | "Tax-free earnings" claim | ✅ Detected | ❌ Missed |

---

## Next Steps

1. ✅ **Run old system on 1,620 materials** (full dataset)
   ```bash
   cd analysis
   python glass_box_audit.py --limit 1620 --use-semantic-filter
   ```

2. ✅ **Export results for human review**
   - Output: `results/final_audit_results.csv`
   - Format: One row per violation with confidence scores

3. 🔮 **Future improvement** (optional, after full audit)
   - Implement Solution 3: Old extraction + RoBERTa + Claude triage (not filter)
   - Test on smaller batch (100 materials)
   - Validate detection rate remains ≥60%

---

## Files

- **Old system**: `analysis/glass_box_audit.py` (main branch, untouched)
- **New system**: Branch `pipeline-v2-conservative-4stage`
- **Validation script**: `run_old_system_on_pilot.py`
- **Results**:
  - Old system: `results/pilot/old_system_audit/*.json`
  - New system: `results/pilot/gpt4o_compliance/*.json`

---

## Conclusion

The old system (glass_box_audit.py) is **validated and ready for production** use on the full 1,620 materials dataset. It achieved 100% detection rate on ground truth errors, significantly outperforming the new conservative 4-stage pipeline (6.7% detection).

The high false positive rate is an acceptable tradeoff for ensuring no dangerous errors slip through. Human reviewers can efficiently filter false positives from the CSV export.

**Decision**: Proceed with old system for full audit.
