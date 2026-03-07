# Baseline Violation Rate for Glass Box Audit System
**Date Established**: 2026-03-07
**Purpose**: Reference baseline for statistical analysis of LLM-induced errors

---

## Summary Statistics

**Dataset**: `results/pilot_individual_2026_run1/` (30 clean pilot files)
**Analysis Date**: February 25, 2026 (run date)
**Glass Box Version**: v2.1 (GPT-4o-mini extraction + RoBERTa-base NLI)

### Violation Counts
- **Total files**: 30 (10 per product: corecoin, melatonin, smartphone)
- **Total violations detected**: 1,002
- **Mean violations per file**: 33.4
- **Violation rate**: ~33-34 violations/file

---

## Product Breakdown

Based on file inspection (`corecoin_1.csv`), typical violations include:
- Smart contract gas fee claims
- Protocol governance claims
- Regulatory compliance statements
- Marketing language (urgency, exclusivity)
- Documentation and custody claims

**Interpretation**: These are "normal" false positives from Glass Box when applied to standard LLM-generated marketing content.

---

## Comparison with Corrupted Data

| Dataset | Files | Intentional Errors | Glass Box Violations | Violations/File |
|---------|-------|-------------------|---------------------|----------------|
| **Pilot (baseline)** | 30 | 0 | 1,002 | 33.4 |
| **Errors folder** | 30 | 30 (progressive 1-10 per product) | 821 | 27.4 |

**Key Finding**: Pilot files have MORE violations than corrupted files (33.4 vs 27.4), indicating high baseline false positive rate.

---

## Statistical Interpretation

### For Full Experiment Analysis:

When analyzing 1,620-run experiment results, use this baseline:

**Expected violations on clean content**: ~33 violations/file

**Deviation from baseline**:
- If experiment shows 33 ± 5 violations/file: Normal LLM behavior
- If experiment shows >40 violations/file: Possible increased error rate
- If experiment shows <25 violations/file: Possible improved quality or different content patterns

**Delta calculation**:
```
Induced_Violations = Observed_Violations - Baseline_Violations
Induced_Violations = Observed - 33.4
```

---

## Important Notes for Statistical Analysis

1. **High False Positive Rate**: Baseline of 33.4 violations/file indicates Glass Box is very sensitive
2. **Product-Specific Baselines**: May need separate baselines per product (corecoin, melatonin, smartphone)
3. **Material Type**: Baseline may vary by material type (FAQ, digital ad, blog post, etc.)
4. **Temperature Effects**: Unknown if baseline changes with temperature settings (0.2, 0.6, 1.0)

---

## Recommendations for Analysis

### Statistical Tests:
- Use **paired t-test** to compare experiment violations against baseline (33.4)
- Calculate **effect size (Cohen's d)** to measure practical significance
- Report violations as **delta from baseline**, not absolute counts

### Filtering:
- Consider semantic pre-filtering to reduce baseline from 33.4 → ~7-10 violations/file
- Use confidence score thresholds (e.g., only violations with NLI score > 0.95)

### Reporting:
- Always report baseline alongside experiment results
- State: "LLM-generated content shows X violations above baseline of 33.4"
- NOT: "LLMs generated X violations" (misleading without baseline context)

---

## Data Provenance

**Source files**: `pilot_study/{corecoin,melatonin,smartphone}/files/*.txt`
**Analysis results**: `results/pilot_individual_2026_run1/*.csv`
**Total CSV lines**: 1,032 (30 files × 1 header + 1,002 violation rows)

**Validation**:
```bash
# Reproduce this calculation:
find results/pilot_individual_2026_run1 -name "*.csv" -exec wc -l {} + | tail -1
# Expected output: 1032 total

# Calculate violations:
# 1,032 lines - 30 headers = 1,002 violations
# 1,002 ÷ 30 files = 33.4 violations/file
```

---

## Future Work

- [ ] Calculate per-product baselines (corecoin vs melatonin vs smartphone)
- [ ] Calculate per-material baselines (FAQ vs digital ad vs blog post)
- [ ] Test if baseline differs with semantic pre-filtering enabled
- [ ] Establish confidence intervals for baseline (±X violations)
- [ ] Compare baseline across multiple runs (run1 vs run2)

---

**Last Updated**: 2026-03-07
**Updated By**: Statistical readiness assessment
**Version**: 1.0
