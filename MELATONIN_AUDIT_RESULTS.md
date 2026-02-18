# Glass Box Audit Results: Smartphone vs Melatonin

## Summary

| Product | Extraction Rate | NLI Validation Rate | Disclaimer Filtering Issue |
|---------|----------------|---------------------|---------------------------|
| **Smartphone** | 10/10 (100%) | 10/10 (100%) | No disclaimers affected |
| **Melatonin** | 10/10 (100%) | 5/10 (50%) | 5/10 skipped as disclaimers |

## Key Findings

### 1. Claim Extraction Performance (GPT-4o-mini)
- ✅ **Perfect extraction: 20/20 mistakes detected (100%)**
- GPT-4o-mini successfully identified all intentional errors across both products
- Extraction works equally well for technical specs and regulatory claims

### 2. Critical Issue: Disclaimer Filtering
**Problem**: Glass Box Audit skips NLI validation for claims classified as "disclaimers"

**Melatonin Mistakes Missed by NLI Validation:**
1. **Store at 0°C** (Over-literal interpretation) - classified as disclaimer
2. **Take every 2 hours** (Unsafe dosage) - classified as disclaimer
3. **FDA approval claim** (Regulatory error) - classified as disclaimer
4. **Avoid if over 18** (Age reversal) - classified as disclaimer
5. **Permanent drowsiness** (Overgeneralized risk) - classified as disclaimer

**Why this matters**: Critical safety and regulatory errors are being extracted but not validated because they appear in disclaimer sections.

### 3. Smartphone Results (Perfect Performance)

All 10 mistakes detected and validated:
1. ✅ 6.5" display (should be 6.3")
2. ✅ 48 MP camera (should be 50 MP)
3. ✅ 1 TB storage (not available)
4. ✅ 16 GB RAM (max is 12 GB)
5. ✅ Wi-Fi 7 (only supports Wi-Fi 6/6E)
6. ✅ Wireless charging (not supported)
7. ✅ Hourly antivirus scanning (not a feature)
8. ✅ Offline AI rendering (requires cloud)
9. ✅ 60W charging (max is 30-45W)
10. ✅ External SSD via SIM tray (hardware impossibility)

**Why 100% success?** All smartphone errors were in core product claims, not disclaimers.

### 4. Melatonin Results (Mixed Performance)

**Detected and Validated (5/10):**
1. ✅ 5 mg dosage (should be 3 mg)
2. ✅ 100 tablets (should be 120)
3. ✅ Fish ingredients in vegan product
4. ✅ Wheat traces despite 0 mg gluten
5. ✅ Lead < 5 ppm (should be < 0.5 ppm)

**Extracted but Skipped (5/10):**
6. ⚠️ Store at 0°C
7. ⚠️ Take every 2 hours
8. ⚠️ FDA approval claim
9. ⚠️ Avoid if over 18
10. ⚠️ Permanent drowsiness

## False Positive Analysis

Both products showed high false positive rates:
- **Smartphone**: 28-31 violations per file (1 actual mistake each)
- **Melatonin**: 10-11 violations per file (1 actual mistake each)

**Root Cause**: NLI model compares every extracted claim against every spec/rule, creating semantic mismatches between unrelated features.

Example false positive:
- Claim: "50 MP camera with OIS"
- Rule: "6.3 inch Actua OLED display"
- NLI Result: CONTRADICTION (99.47% confidence)
- Actual: These are unrelated specs, not contradictory

## Recommendations

### High Priority
1. **Validate disclaimers**: Critical safety/regulatory claims in disclaimer sections must be validated
2. **Smarter rule matching**: Only compare claims against semantically related specs to reduce false positives
3. **Category filtering**: Group specs by category (display, camera, storage) and only cross-check within categories

### Medium Priority
4. **Confidence thresholding**: Experiment with higher contradiction thresholds (currently using any contradiction score)
5. **Semantic similarity pre-filter**: Use embeddings to filter out unrelated claim-rule pairs before NLI

### Low Priority
6. **Fine-tune NLI model**: Consider domain-specific fine-tuning for product marketing validation
7. **Add context awareness**: Claims about different product features should not be compared

## Technical Details

**Glass Box Audit Pipeline:**
1. **Claim Extraction**: GPT-4o-mini @ temp=0 → 100% accuracy
2. **Disclaimer Classification**: Pattern-based filtering → caused 50% of melatonin errors to be skipped
3. **NLI Verification**: DeBERTa cross-encoder → high false positive rate due to broad comparison

**Enhancement Applied:**
- Added `flatten_specs()` to extract factual specs from YAML
- Modified `verify_claim()` to validate against both `authorized_claims` and `specs`
- Successfully detected technical spec violations (display size, camera MP, storage options)

## Conclusion

Glass Box Audit demonstrates **excellent claim extraction** (100% detection rate) but has two critical issues:

1. **Disclaimer filtering blind spot**: Safety and regulatory errors in disclaimer sections are not validated
2. **False positive noise**: Unrelated spec comparisons create 10-30x more violations than actual errors

The smartphone audit showed perfect performance because errors were in core claims, while melatonin audit revealed the disclaimer filtering issue.

**Next Steps:** Fix disclaimer validation and implement semantic filtering to reduce false positives.
