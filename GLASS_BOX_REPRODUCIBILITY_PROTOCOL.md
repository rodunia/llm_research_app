# Glass Box Audit: Reproducibility Protocol

**Version:** 2.0
**Date:** February 24, 2026
**Purpose:** Ensure 98%+ consistent detection across runs

---

## What Was Fixed

###  **Critical Bug: Disclaimer Claims Not Validated**

**Problem:** Extraction separated claims into `core_claims` and `disclaimers`, but validation only checked `core_claims`.

**Impact:** Any error in disclaimer sections (storage instructions, dosage warnings, age restrictions) was automatically missed.

**Fix Applied:**
- `glass_box_standalone.py` line 201: Now validates `all_claims = core_claims + disclaimers`
- `glass_box_audit.py` line 674: Already had this fix (standalone was missing it)

**Result:** Detection rate expected to improve from 73% → ~90%+

---

## System Architecture

### **Step 1: Claim Extraction**
- **Model:** GPT-4o-mini (temp=0, deterministic)
- **Prompt:** `ATOMIZER_SYSTEM_PROMPT` (analysis/glass_box_audit.py:131-183)
- **Output:** JSON with `core_claims` and `disclaimers`
- **Both are now validated** (critical fix)

### **Step 2: NLI Validation**
- **Model:** cross-encoder/nli-roberta-base (125M params)
- **Device:** MPS (Apple Silicon) or CUDA
- **Threshold:** 90% contradiction confidence
- **Validates against:** authorized_claims, specifications, prohibited_claims, clarifications

---

## Reproducibility Checklist

### **Before Running Audit:**

- [ ] Python 3.9+ with venv activated
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] OPENAI_API_KEY set in `.env`
- [ ] Models version-locked in config:
  - Extraction: `gpt-4o-mini` (via ENGINE_MODELS)
  - NLI: `cross-encoder/nli-roberta-base`
- [ ] Product YAMLs have correct structure:
  - `authorized_claims`: dict or list (auto-flattened)
  - `specifications`: dict (converted to "key: value" strings)
  - `prohibited_claims`: list
  - `clarifications`: dict or list (auto-flattened)

### **Running Audit:**

```bash
# Activate environment
source .venv/bin/activate
export PYTHONPATH=.

# Run standalone audit (for pilot files)
python3 analysis/glass_box_standalone.py \
  --input pilot_study/ \
  --ground-truth GROUND_TRUTH_ERRORS.md \
  --output pilot_results/

# Or run main audit (for experiment files)
python3 analysis/glass_box_audit.py --run-id <run_id>
```

### **Validation:**

- [ ] Check `pilot_results/validation_report.md` for detection rate
- [ ] Verify total claims validated includes disclaimers:
  - Log should show: "Extracted X core claims, Y disclaimers"
  - Log should show: "Validating Z total claims" (where Z = X + Y)
- [ ] Spot-check violations CSV to ensure disclaimer claims appear
- [ ] Compare with ground truth keywords

---

## Expected Performance

### **Target Detection Rates** (with disclaimer fix):

| Product | Expected Detection | Acceptable Range |
|---------|-------------------|------------------|
| CoreCoin | 90%+ (9/10) | 8-10/10 |
| Smartphone | 80%+ (8/10) | 7-10/10 |
| Melatonin | 70%+ (7/10) | 6-8/10 |
| **Overall** | **80%+ (24/30)** | **22-28/30** |

### **Variance Sources:**

1. **GPT-4o-mini extraction (temp=0):** Near-deterministic (~1% variance)
2. **NLI model:** Fully deterministic on same hardware
3. **Ground truth keyword matching:** Exact string matching (deterministic)

**Total expected variance: ≤2%**

---

## Known Limitations

### **What Glass Box CAN'T Detect:**

1. **Context-dependent errors:**
   - Example: "1TB storage" is wrong if spec says max 512GB, but GPT may not extract storage options as separate claims

2. **Implicit contradictions:**
   - Example: "FDA approved" is wrong for supplements, but needs explicit prohibited_claims entry

3. **Subtle numerical errors:**
   - GPT extraction may round or normalize numbers (e.g., "~5 seconds" → "5 seconds")

4. **Errors requiring domain knowledge:**
   - Example: Cryptocurrency governance mechanisms may be too technical for generic NLI model

### **Error Types by Detection Rate:**

| Error Type | Detection Rate | Why |
|------------|----------------|-----|
| Numerical drift | 100% (2/2) | Specs contain exact numbers |
| Feature hallucination | 100% (1/1) | Prohibited claims list prevents |
| Spec substitution | 100% (1/1) | Contradicts specifications |
| Future spec hallucination | 100% (1/1) | Prohibited claims list |
| Unsafe dosage | ~50% (varies) | May appear in disclaimers (now fixed) |
| Regulatory claims | ~50% (varies) | Requires explicit prohibited_claims |
| Hallucinated features | ~50% (varies) | Requires complete specifications list |

---

## Debugging Failed Detections

### **If detection rate < 80%:**

1. **Check disclaimer extraction:**
   ```bash
   grep "Extracted.*disclaimers" pilot_fix_test.log
   # Should show: "Extracted X core claims, Y disclaimers"
   ```

2. **Verify all_claims validation:**
   ```bash
   grep "Validating.*total claims" pilot_fix_test.log
   # Should show: "Validating Z total claims" (Z = core + disclaimers)
   ```

3. **Check extraction quality:**
   - Read `pilot_results/violations/user_<product>_<N>.csv`
   - Verify claims include both main content AND disclaimer content
   - Example: Should see "store at" claims for melatonin files

4. **Check ground truth matching:**
   - Verify run_id format: `user_<product>_<number>` (NOT `<product>_<number>`)
   - Check keywords in GROUND_TRUTH_ERRORS.md match actual error text

5. **Check YAML structure:**
   - Ensure clarifications/authorized_claims are properly nested
   - Test flattening logic handles both dict and list formats

---

## Automated Test Suite (TODO)

Create `tests/test_glass_box_reproducibility.py`:

```python
def test_disclaimer_validation():
    """Ensure disclaimers are validated, not just core_claims"""
    # Extract claims from test file
    # Assert len(all_claims) == len(core) + len(disclaimers)
    # Assert violations include disclaimer-based errors

def test_yaml_flattening():
    """Ensure dict/list YAML structures flatten correctly"""
    # Test authorized_claims dict → list
    # Test clarifications dict → list

def test_known_errors_detection():
    """Ensure 8 previously missed errors are now detected"""
    # melatonin_6, 7, 8, 9, 10
    # smartphone_3, 4
    # corecoin_10
```

Run: `pytest tests/test_glass_box_reproducibility.py -v`

---

## Version Control

### **Key Files:**
- `analysis/glass_box_audit.py` - Main NLI validation
- `analysis/glass_box_standalone.py` - Pilot file validator
- `GROUND_TRUTH_ERRORS.md` - Ground truth for validation
- `products/*.yaml` - Product specifications

### **Git Workflow:**
```bash
# Before making changes
git status
git diff

# After changes
git add analysis/glass_box_*.py
git commit -m "fix: validate disclaimers in glass box audit

- Add disclaimers to all_claims validation loop
- Fix YAML flattening for nested dict structures
- Expected improvement: 73% → 80%+ detection"
```

---

## Contact / Issues

If detection rate deviates >2% from expected:
1. Check this protocol step-by-step
2. Review git diff for unintended changes
3. Verify API keys and model versions
4. Check logs for extraction/validation counts
5. Document issue in `GLASS_BOX_CURRENT_STATUS_2026.md`
