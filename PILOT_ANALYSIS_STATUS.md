# Pilot Analysis Status

**Date**: March 11, 2026
**Status**: ✅ Gemini runs completed, 🔄 Glass Box analysis in progress

---

## 1. COMPLETED TASKS

### ✅ Marketing Material Generation
- **Total runs**: 54/54 completed (100%)
- **Engines**: OpenAI (GPT-4o), Google (Gemini Flash), Mistral (Mistral Large)
- **Breakdown**:
  - OpenAI: 18/18 ✅
  - Google (Gemini): 18/18 ✅ (just completed today after fixing model name)
  - Mistral: 18/18 ✅

### ✅ Experimental Design Documentation
- **File**: `PILOT_EXPERIMENTAL_DESIGN.md`
- **Contents**:
  - Material locations (`outputs/*.txt`)
  - Randomization workflow (seed=42)
  - Variable tracking → statistical measures mapping
  - Verification that design aligns with research outline

### ✅ Analysis Scripts Created
- `scripts/run_pilot_glass_box_batch.py` - Batch Glass Box audit
- `scripts/analyze_pilot_hypotheses.py` - Hypothesis testing with statistics

---

## 2. IN PROGRESS

### 🔄 Glass Box Compliance Audit
- **Status**: Running in background (process ID: a29816)
- **Files to process**: 54 marketing materials
- **Estimated time**: ~20-30 minutes (depends on API speed)
- **Output location**: `results/final_audit_results.csv`

**Progress monitoring**:
```bash
tail -f /tmp/pilot_glasbox_full.log
```

**What Glass Box does**:
1. Extract atomic claims from each marketing material (GPT-4o, temp=0)
2. Validate claims against product YAMLs (RoBERTa NLI)
3. Flag compliance violations with confidence scores
4. Save individual CSVs: `outputs/{run_id}_claims_review.csv`

---

## 3. NEXT STEPS (After Glass Box Completes)

### Step 1: Copy Results to Pilot Directory
```bash
# Move Glass Box results to pilot_analysis
cp results/final_audit_results.csv results/pilot_analysis/
cp outputs/*_claims_review.csv results/pilot_analysis/
```

### Step 2: Run Hypothesis Testing
```bash
python scripts/analyze_pilot_hypotheses.py
```

**This will generate**:
- H1 (People-Pleasing Bias): Violation rate statistics, one-sample t-test
- H2 (Induced Errors): Error type distribution, Chi-square tests
- H3 (Temporal Unreliability): Within-condition variance, coefficient of variation

### Step 3: Generate Summary Report
Output file: `results/pilot_analysis/HYPOTHESIS_TESTING_RESULTS.txt`

**Contains**:
- Statistical test results (t-statistics, p-values)
- Effect sizes by engine and product
- Temporal stability metrics
- Recommendation for scale-up to full study

---

## 4. EXPECTED PILOT RESULTS

### Research Questions

**RQ1: Do LLMs generate overly positive content that violates compliance?**
- **Measure**: Violation rate per file
- **Hypothesis**: Rate significantly > 0%
- **Test**: One-sample t-test + Kruskal-Wallis (by engine)

**RQ2: How frequently do LLMs introduce factual inaccuracies?**
- **Measure**: Violation types, high-confidence violations
- **Hypothesis**: Significant variation across products/engines
- **Test**: Chi-square (error distribution), ANOVA (severity)

**RQ3: Do LLMs produce inconsistent outputs across repetitions?**
- **Measure**: Within-condition variance (3 repetitions)
- **Hypothesis**: High coefficient of variation (CV)
- **Test**: CV statistics, Cohen's Kappa (violation consistency)

---

## 5. DATA ORGANIZATION

### Pilot Analysis Directory Structure
```
results/pilot_analysis/
├── pilot_violations_summary.csv        # Summary of all 54 audits
├── all_violations.csv                  # All violations combined
├── {run_id}_violations.csv             # Individual audit results (54 files)
└── HYPOTHESIS_TESTING_RESULTS.txt      # Statistical analysis output
```

### Main Outputs Directory
```
outputs/
├── {run_id}.txt                        # Marketing materials (54 files)
├── {run_id}_claims.json                # Extracted claims (54 files)
└── {run_id}_claims_review.csv          # Violations (54 files)
```

---

## 6. TIMELINE

| Task | Status | Time |
|------|--------|------|
| Generate experimental matrix | ✅ Complete | - |
| Run OpenAI (18 materials) | ✅ Complete | Dec 29 |
| Run Mistral (18 materials) | ✅ Complete | Dec 29 |
| Fix Gemini model name | ✅ Complete | Mar 11, 10:30 |
| Run Gemini (18 materials) | ✅ Complete | Mar 11, 11:00 |
| Create documentation | ✅ Complete | Mar 11, 11:03 |
| Run Glass Box audit (54 files) | 🔄 In Progress | Mar 11, 11:05 (ETA 20-30 min) |
| Hypothesis testing | ⏳ Pending | After Glass Box |
| Generate summary report | ⏳ Pending | After hypothesis testing |

---

## 7. VERIFICATION CHECKLIST

### ✅ Pre-Analysis
- [x] All 54 marketing materials generated
- [x] Materials saved in `outputs/*.txt`
- [x] Experiments tracked in `results/experiments.csv`
- [x] Randomization applied (seed=42)
- [x] All engines completed (OpenAI, Google, Mistral)

### 🔄 Analysis Phase
- [ ] Glass Box audit completed (54/54 files)
- [ ] No API errors or failures
- [ ] All violations saved to CSVs
- [ ] Summary file generated

### ⏳ Post-Analysis
- [ ] Hypothesis testing completed
- [ ] Statistical significance determined
- [ ] Effect sizes calculated
- [ ] Summary report generated
- [ ] Results documented for paper

---

## 8. TROUBLESHOOTING

### If Glass Box Fails
```bash
# Check error log
tail -100 /tmp/pilot_glasbox_full.log

# Check if API key is set
echo $OPENAI_API_KEY

# Resume from checkpoint
python analysis/glass_box_audit.py --resume
```

### If Hypothesis Testing Fails
```bash
# Verify data files exist
ls results/pilot_analysis/*.csv

# Check for missing violations
python -c "
import pandas as pd
df = pd.read_csv('results/final_audit_results.csv')
print(f'Total runs: {len(df)}')
print(f'Runs with violations: {len(df[df[\"Status\"] == \"FAIL\"])}')
"
```

---

## 9. NEXT FULL STUDY SCALE-UP

After pilot validation, scale to **1,620 runs**:

| Factor | Pilot | Full Study |
|--------|-------|------------|
| Materials | 2 (digital_ad, faq) | 5 (+ blog, social, email) |
| Temperature | 1 (0.6) | 3 (0.2, 0.6, 1.0) |
| Time-of-day | 1 (morning) | 3 (morning, afternoon, evening) |
| Engines | 3 | 3 (same) |
| Repetitions | 3 | 3 (same) |
| **Total runs** | **54** | **1,620** |

**Estimated costs** (full study):
- OpenAI GPT-4o: ~$500 (540 runs)
- Google Gemini: ~$50 (540 runs)
- Mistral Large: ~$200 (540 runs)
- Glass Box audit: ~$1,600 (GPT-4o extraction for 1,620 files)
- **Total**: ~$2,350

---

## 10. CONTACT & SUPPORT

**Monitoring Glass Box**:
```bash
# Check progress
watch -n 10 "tail -3 /tmp/pilot_glasbox_full.log"

# Count completed audits
ls outputs/*_claims_review.csv | wc -l
```

**When analysis completes, run**:
```bash
python scripts/analyze_pilot_hypotheses.py
```

This will generate the full statistical report with p-values and effect sizes ready for your research presentation.
