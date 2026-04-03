# Progressive Error Analysis: Status Report
## errors/ Folder Glass Box + GPT-4o Comparison

**Date**: 2026-03-07
**Status**: Setup Complete - Ready to Run Analysis

---

## ✅ Completed Tasks

### 1. Error Documentation Extracted

Read and cataloged all 30 intentional errors from `errors/` folders:

**Smartphone (10 errors)**: Display size, camera MP, storage options, RAM, Wi-Fi 7, wireless charging, antivirus, AI rendering, fast charging, SSD expansion

**Melatonin (10 errors)**: Dosage (5mg vs 3mg), bottle count, vegan+fish contradiction, wheat+gluten, lead limit, storage temp (0°C), dosing frequency, FDA approval, age restriction, permanent drowsiness

**CoreCoin (10 errors)**: Block time, light validators, trading pauses, key-sharding, gas-free, auto-pass governance, cross-chain RPC, unstaking penalty, validator locks, regional fixed rates

### 2. Error Structure Mapped

**Progressive corruption pattern confirmed**:
- `1.txt` = 1 error (first error only)
- `2.txt` = 2 errors (errors 1-2 cumulative)
- ...
- `10.txt` = 10 errors (all errors cumulative)

### 3. Files Prepared

✅ **30 files copied to outputs/**:
- `outputs/errors_smartphone_1.txt` through `errors_smartphone_10.txt`
- `outputs/errors_melatonin_1.txt` through `errors_melatonin_10.txt`
- `outputs/errors_corecoin_1.txt` through `errors_corecoin_10.txt`

---

## ⏳ Pending Tasks

### Task 1: Run Glass Box Audit (30 files)

**Estimated time**: 30-45 minutes

**Method**: Create custom analysis script that:
1. Loads each file from `outputs/errors_*.txt`
2. Loads corresponding product YAML
3. Runs Glass Box audit (claim extraction → NLI verification)
4. Saves results to `results/errors_analysis/`

**Expected output**:
- Detection rate per file (1-10 errors)
- Which specific errors were caught/missed
- Confidence scores
- False positive analysis

### Task 2: Run GPT-4o Free-Form (30 files)

**Estimated time**: 30 minutes

**Method**: Use `scripts/llm_direct_gpt4o_freeform.py` adapted for errors/ files

**Expected output**:
- Detection rate per file
- Comparison with Glass Box

### Task 3: Analysis & Report Generation

**Deliverables**:
1. **Detection by Corruption Level**:
   ```
   | File Level | Errors | Glass Box Detected | GPT-4o Detected |
   |------------|--------|-------------------|-----------------|
   | 1          | 1      | ?/1               | ?/1             |
   | 2          | 2      | ?/2               | ?/2             |
   | ...        | ...    | ...               | ...             |
   | 10         | 10     | ?/10              | ?/10            |
   ```

2. **Progressive Corruption Analysis**:
   - Does detection rate improve/degrade with more errors?
   - Which errors are consistently caught vs missed?
   - False positive trends

3. **Comparison Report**:
   - Glass Box vs GPT-4o Free-Form
   - Similar to `COMPARISON_GLASSBOX_VS_GPT4O_FREEFORM.md`

---

## 📋 Ground Truth Reference

**Created**: `GROUND_TRUTH_ERRORS.md`

Contains complete catalog of all 30 errors with:
- Error number
- Incorrect vs correct values
- Error type (Numerical/Factual/Logical/Hallucination)
- Expected detection difficulty

---

## 🚀 Next Steps (When Ready)

### Option A: Run Full Analysis Now (~1.5-2 hours)

```bash
# 1. Create and run Glass Box batch script
python scripts/run_errors_glass_box.py

# 2. Create and run GPT-4o Free-Form script
python scripts/run_errors_gpt4o_freeform.py

# 3. Generate comparison report
python scripts/analyze_errors_comparison.py
```

### Option B: Run Sample First (Test on 3 files)

Test on one file from each product to verify workflow:
```bash
# Test smartphone file 5 (has 5 cumulative errors)
# Test melatonin file 5
# Test corecoin file 5

# Verify detection, then scale to all 30
```

---

## 💡 Key Questions This Analysis Will Answer

1. **Progressive Detection**: Does Glass Box detection improve or degrade as errors accumulate?
   - Hypothesis A: More errors = more signals = better detection
   - Hypothesis B: More errors = noise/confusion = worse detection
   - Hypothesis C: Detection rate constant (independent errors)

2. **Method Comparison**: How does Glass Box compare to GPT-4o Free-Form on progressive corruption?
   - Which method handles cumulative errors better?
   - Do both methods miss the same errors?

3. **Error Difficulty**: Which errors are hardest to detect?
   - Numerical mismatches (easy?)
   - Feature hallucinations (medium?)
   - Logical contradictions (context-dependent?)

4. **False Positive Trends**: Do false positives increase with more errors?

---

## 📊 Expected Results Format

### Per-File Detection Table:

| File | Product | Errors | Glass Box Found | GPT-4o Found | Glass Box % | GPT-4o % |
|------|---------|--------|----------------|--------------|-------------|----------|
| errors_smartphone_1 | Smartphone | 1 | ?/1 | ?/1 | ?% | ?% |
| errors_smartphone_2 | Smartphone | 2 | ?/2 | ?/2 | ?% | ?% |
| ... | ... | ... | ... | ... | ... | ... |

### Aggregate Analysis:

```
Overall Detection:
  Glass Box: X/165 total errors (Y%)
  GPT-4o:    Z/165 total errors (W%)

By Corruption Level:
  Files 1-3 (low):    Glass Box ?% vs GPT-4o ?%
  Files 4-7 (medium): Glass Box ?% vs GPT-4o ?%
  Files 8-10 (high):  Glass Box ?% vs GPT-4o ?%
```

---

## ⏱️ Time Estimate Breakdown

| Task | Duration | Notes |
|------|---------|-------|
| Setup (✅ DONE) | 30 min | Error mapping, file prep |
| Glass Box audit (30 files) | 30-45 min | ~1-1.5 min per file |
| GPT-4o Free-Form (30 files) | 30 min | API calls |
| Analysis & report | 20-30 min | Tables, plots, report |
| **TOTAL** | **~2 hours** | Can run overnight if needed |

---

## 🎯 Current Status

**Phase**: Setup Complete ✅
**Next**: Run Glass Box + GPT-4o analysis
**Output**: Comprehensive comparison report

**Ready to proceed when you confirm!**

---

**Last Updated**: 2026-03-07 09:25
**Files Ready**: 30/30 in `outputs/errors_*.txt`
**Documentation**: `GROUND_TRUTH_ERRORS.md`
