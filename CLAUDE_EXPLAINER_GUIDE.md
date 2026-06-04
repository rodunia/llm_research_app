# Claude Explainer Layer - Usage Guide

**Added**: 2026-06-04
**Location**: `analysis/glass_box_audit.py`

---

## Overview

The old system (glass_box_audit.py) now includes an **optional Claude explainer layer** that adds human-readable explanations to violations **WITHOUT filtering them**.

**Key principle**: Claude does NOT remove or filter violations - it only adds context to help human reviewers prioritize and understand compliance issues.

---

## How It Works

### 3-Step Pipeline (with optional Claude)

1. **Extraction (GPT-4o)**: Extract ALL atomic claims using forensic prompt
2. **Verification (RoBERTa NLI)**: Detect violations with cross-encoder (score > 0.90)
3. **Explanation (Claude)** [OPTIONAL]: Add human-readable explanations + severity + recommendations

**All violations from RoBERTa are kept** - Claude only adds:
- `claude_explanation`: Why this violation matters (2-3 sentences)
- `severity_assessment`: LOW | MEDIUM | HIGH | CRITICAL
- `recommended_action`: REMOVE | REVISE | ADD_DISCLAIMER | REVIEW

---

## Usage

### Basic (without Claude)
```bash
# Run without explanations (faster, cheaper)
python analysis/glass_box_audit.py --limit 100
```

### With Claude Explainer
```bash
# Add Claude explanations to violations
python analysis/glass_box_audit.py --limit 100 --use-claude-explainer
```

### Full Options
```bash
# All features enabled
python analysis/glass_box_audit.py \
  --limit 1620 \
  --use-semantic-filter \
  --use-claude-explainer \
  --resume
```

---

## Output Format

### CSV Export (`results/final_audit_results.csv`)

Without Claude:
```csv
Filename,Status,Violated_Rule,Extracted_Claim,Confidence_Score,Claude_Explanation,Severity,Recommended_Action
melatonin_1.txt,FAIL,"The product does NOT contain 5 mg of melatonin","Contains 5 mg of melatonin per serving",0.9982,,,
```

With Claude:
```csv
Filename,Status,Violated_Rule,Extracted_Claim,Confidence_Score,Claude_Explanation,Severity,Recommended_Action
melatonin_1.txt,FAIL,"The product does NOT contain 5 mg of melatonin","Contains 5 mg of melatonin per serving",0.9982,"The material claims 5 mg of melatonin per serving when the product actually contains 3 mg. This is a critical labeling error that misrepresents the active ingredient amount, violating FDA labeling requirements and potentially causing consumer harm through incorrect dosing expectations.",CRITICAL,REMOVE
```

---

## Test Results (5 pilot files)

| File | Violations | Critical | Example |
|------|-----------|----------|---------|
| melatonin_1 | 9 | 1 | **5mg dosage error** → CRITICAL (FDA labeling violation) |
| melatonin_7 | 10 | 0 | "Every 2 hours" → HIGH (unsafe dosage) |
| smartphone_1 | 13 | 1 | **6.5" display error** → CRITICAL (factual misrepresentation) |
| corecoin_1 | 10 | 2 | Block time error → CRITICAL (technical misrepresentation) |
| smartphone_2 | 19 | 0 | 16GB RAM error → HIGH |

**Total**: 61 violations, 4 CRITICAL, 11 HIGH

---

## Example: Critical Violation with Explanation

**Claim**: "Contains 5 mg of melatonin per serving"
**Violated Rule**: "The product does NOT contain 5 mg of melatonin"
**NLI Score**: 0.998

**Claude Explanation**:
> The material claims 5 mg of melatonin per serving when the product actually contains 3 mg. This is a critical labeling error that misrepresents the active ingredient amount, violating FDA labeling requirements and potentially causing consumer harm through incorrect dosing expectations.

**Severity**: CRITICAL
**Recommended Action**: REMOVE

---

## Cost & Performance

### API Costs (per 1,000 materials)

**Without Claude**:
- GPT-4o extraction: ~$20 (avg 2,000 tokens/material)
- RoBERTa NLI: $0 (local inference)
- **Total: ~$20**

**With Claude**:
- GPT-4o extraction: ~$20
- RoBERTa NLI: $0
- Claude explanations: ~$30 (avg 10 violations/material, 300 tokens/explanation)
- **Total: ~$50** (2.5x more expensive)

### Processing Time (per 1,000 materials)

**Without Claude**: ~2-3 hours (extraction + NLI)
**With Claude**: ~4-5 hours (+ 1.5-2 hours for explanations)

**Recommendation**: Use Claude selectively:
- Run full audit WITHOUT Claude first
- Filter to materials with violations (FAIL status)
- Re-run with `--use-claude-explainer` on FAIL subset only

---

## Configuration

**Location**: `analysis/glass_box_audit.py`

```python
# Claude Configuration
CLAUDE_MODEL = "claude-sonnet-4-20250514"
CLAUDE_TEMPERATURE = 0
```

**Environment**:
```bash
# .env file
ANTHROPIC_API_KEY=your_key_here
```

---

## Architecture Comparison

### Old System (without Claude)
```
GPT-4o (forensic extraction)
    ↓
RoBERTa NLI (verification)
    ↓
CSV export (violations + confidence scores)
    ↓
Human review (manual prioritization)
```

### Enhanced System (with Claude)
```
GPT-4o (forensic extraction)
    ↓
RoBERTa NLI (verification)
    ↓
Claude (add explanations, DOES NOT FILTER)
    ↓
CSV export (violations + explanations + severity)
    ↓
Human review (with AI-assisted prioritization)
```

**Key difference**: Claude is an **augmentation**, not a filter. All RoBERTa violations are kept.

---

## CLI Reference

```bash
# Basic audit
python analysis/glass_box_audit.py

# With Claude explanations
python analysis/glass_box_audit.py --use-claude-explainer

# With semantic pre-filtering (74% FP reduction)
python analysis/glass_box_audit.py --use-semantic-filter

# Limit to N materials
python analysis/glass_box_audit.py --limit 100

# Skip first N materials
python analysis/glass_box_audit.py --skip 500 --limit 100

# Resume from checkpoint
python analysis/glass_box_audit.py --resume

# Single material
python analysis/glass_box_audit.py --run-id melatonin_1

# Full production run
python analysis/glass_box_audit.py --limit 1620 --use-semantic-filter --resume
```

---

## Severity Levels Explained

| Severity | Meaning | Examples |
|----------|---------|----------|
| **CRITICAL** | Regulatory violation, consumer harm risk, factual misrepresentation | FDA labeling errors, dosage errors, spec errors |
| **HIGH** | Significant compliance issue, potential legal exposure | Misleading claims, safety warnings, unclear policies |
| **MEDIUM** | Compliance concern, needs review | Minor inconsistencies, ambiguous phrasing |
| **LOW** | Potential false positive, technical mismatch | Formatting issues, semantic mismatches |

---

## Validation

**Test dataset**: 5 pilot files with ground truth errors
**Detection rate**: 100% (all ground truth errors detected by RoBERTa)
**Claude accuracy**: 4/5 critical errors correctly labeled as CRITICAL
**False filtering**: 0% (Claude added explanations but did NOT remove any violations)

**Conclusion**: Claude explainer is safe to use - it enhances human review without reducing detection rate.

---

## Troubleshooting

### Claude not available
```
WARNING - Claude not available (install anthropic)
```
**Solution**: `pip install anthropic` or run without `--use-claude-explainer`

### Claude timeout
**Solution**: Claude is only called once per material (not per violation). If timeouts occur, disable Claude and run explanations separately on FAIL subset.

### Empty explanations
**Solution**: Check ANTHROPIC_API_KEY in `.env` file. Claude should return explanations for all violations.

---

## Next Steps

1. ✅ Run full audit on 1,620 materials WITHOUT Claude
2. ✅ Export results to CSV
3. 🔄 Filter to FAIL status (materials with violations)
4. 🔄 Re-run with `--use-claude-explainer` on FAIL subset only
5. 🔄 Human review with AI-assisted prioritization (start with CRITICAL)

---

## See Also

- `VALIDATION_RESULTS.md` - Old system validation (100% detection rate)
- `test_claude_explainer.py` - Single file test
- `test_claude_explainer_batch.py` - Batch test on 5 files
- `results/pilot/claude_explainer_test/` - Test outputs
