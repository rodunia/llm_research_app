# Experimental Metrics - Team Overview

**Date**: 2026-03-26
**Experiment**: LLM Marketing Content Generation - Reliability Study
**Total Runs**: 1,620 (across 7 days)

---

## Executive Summary for Colleagues

We're running a **systematic experiment** to test whether LLMs can reliably generate compliant marketing content, or if they introduce errors and inconsistencies over time.

### **Why These Metrics Matter**

This experiment tests **3 critical research questions**:

1. **Do LLMs make systematic errors?** (People-pleasing bias)
   - Do they exaggerate benefits?
   - Do they violate regulatory compliance?

2. **How reliable are LLMs over time?** (Temporal unreliability)
   - Do outputs change across different days/times?
   - Are morning outputs different from evening outputs?

3. **Which LLM provider is most reliable?** (Provider comparison)
   - OpenAI GPT-4o-mini vs Google Gemini vs Mistral

---

## Metrics We Will Measure

### **Category 1: Operational Metrics** (Keep Experiment Running)

#### **1.1 Completion Rate**
**What**: Percentage of runs that successfully complete
**Why**: Ensures we get enough data for statistical analysis
**Target**: ≥98% success rate (≤32 failures out of 1,620)

**Formula**: `(completed_runs / total_runs) × 100`

**Example**:
```
Completed: 1,590 / 1,620 = 98.1% ✓ Good
Completed: 1,520 / 1,620 = 93.8% ⚠ Concerning
```

---

#### **1.2 API Response Time**
**What**: How long each LLM takes to respond
**Why**:
- Slow responses → experiment takes too long
- Very slow → may indicate API issues

**Target**:
- OpenAI: 2-10 seconds
- Google: 3-15 seconds
- Mistral: 2-8 seconds

**Formula**: `actual_end_time - actual_start_time`

**Why it matters**: If responses suddenly slow down (>30s), API may be degraded or rate-limited.

---

#### **1.3 Cost per Run**
**What**: API cost for each LLM call
**Why**: Budget management, cost comparison between providers

**Target Total**: ~$124
- OpenAI: ~$27 (540 runs)
- Google: ~$16 (540 runs)
- Mistral: ~$81 (540 runs)

**Formula**:
```
OpenAI:  (prompt_tokens × $0.00015 + completion_tokens × $0.0006) / 1000
Google:  (prompt_tokens × $0.000075 + completion_tokens × $0.0003) / 1000
Mistral: (prompt_tokens × $0.003 + completion_tokens × $0.009) / 1000
```

**Why it matters**: Mistral is 5x more expensive per run - if cost exceeds $200, something is wrong.

---

#### **1.4 Output Data Completeness**
**What**: Do we have all the data we need?
**Why**: Missing data = missing analysis

**Check**:
- ✓ All completed runs have output files
- ✓ All output files are non-empty (>100 bytes)
- ✓ All runs have token counts
- ✓ All runs have timestamps

**Target**: 100% completeness for all metrics

---

### **Category 2: Research Metrics** (Answer Scientific Questions)

#### **2.1 Error Detection Rate by LLM** ⭐ PRIMARY RESEARCH METRIC
**What**: How many generated materials contain factual errors or compliance violations
**Why**: Answers "Are LLMs reliable for marketing content?"

**Measured by**: Glass Box Audit (post-run analysis)
- Extracts all factual claims from generated content
- Cross-checks against product specifications
- Flags contradictions, exaggerations, prohibited claims

**Expected**:
- If LLMs are reliable: 0-5% error rate
- If LLMs are unreliable: 20-50% error rate

**Comparison**: Which LLM has lowest error rate?
- Hypothesis: GPT-4o-mini < Gemini < Mistral (based on model size)

---

#### **2.2 Temporal Consistency** ⭐ PRIMARY RESEARCH METRIC
**What**: Do outputs vary by time of day?
**Why**: Tests "temporal unreliability" hypothesis

**How we measure**:
```
Morning outputs (7-12am):   X errors
Afternoon outputs (12-5pm): Y errors
Evening outputs (5-10pm):   Z errors

Are X, Y, Z significantly different? (ANOVA test)
```

**Hypothesis**:
- If LLMs are consistent: No time-of-day effect (p > 0.05)
- If LLMs are inconsistent: Significant variation (p < 0.05)

**Why it matters**: If outputs vary by time, LLMs are unreliable for production use.

---

#### **2.3 Temperature Effect on Reliability**
**What**: Does creativity (temperature) increase errors?
**Why**: Tests creativity vs. compliance tradeoff

**Settings tested**:
- temp=0.2 (Low): Deterministic, conservative
- temp=0.6 (Medium): Balanced
- temp=1.0 (High): Creative, varied

**Hypothesis**: Higher temperature → more errors

**How we measure**:
```
Error rate at temp=0.2: X%
Error rate at temp=0.6: Y%
Error rate at temp=1.0: Z%

Is Z > Y > X? (trend test)
```

---

#### **2.4 Output Length Consistency**
**What**: How much do output lengths vary?
**Why**: High variance = unpredictable behavior

**Metric**: Coefficient of Variation (CV)
```
CV = (standard_deviation / mean) × 100%
```

**Expected**:
- temp=0.2: CV < 15% (very consistent)
- temp=0.6: CV = 15-25% (moderately consistent)
- temp=1.0: CV > 25% (high variance)

**By engine**:
- Which engine has lowest CV? → Most predictable

---

#### **2.5 Compliance Violation Types**
**What**: What kinds of errors do LLMs make?
**Why**: Understand failure modes for mitigation

**Categories**:
1. **Exaggeration**: "Best smartphone ever" (no substantiation)
2. **Prohibited claims**: "Cures insomnia" (medical claim)
3. **False specifications**: "5000 mAh battery" (actual: 4500 mAh)
4. **Missing disclaimers**: Omits required safety warnings
5. **Contradictions**: Claims contradict product specs

**Analysis**: Which types are most common per LLM?

---

#### **2.6 Product-Specific Error Rates**
**What**: Do certain products have more errors?
**Why**: Regulatory complexity may affect LLM behavior

**Products tested**:
- **Smartphone** (FTC): Consumer electronics, moderate complexity
- **Cryptocurrency** (SEC/CFTC): Financial product, high regulatory risk
- **Health Supplement** (FDA): Medical claims, very strict rules

**Hypothesis**: Supplement > Cryptocurrency > Smartphone (error rates)

---

#### **2.7 Material Type Effects**
**What**: Do certain content types have more errors?
**Why**: Different formats may be harder/easier for LLMs

**Material types**:
- **FAQ**: Q&A format, factual
- **Digital Ad**: Short, persuasive
- **Blog Post**: Long-form narrative

**Question**: Which format has highest error rate?

---

#### **2.8 Same-Prompt Reproducibility** (temp=0.2 only)
**What**: With deterministic temperature, do we get identical outputs?
**Why**: Tests if LLMs are truly reproducible

**How we measure**:
- Compare outputs from same product/material/engine/temp=0.2
- Run at different times (morning vs evening)
- Calculate similarity score (e.g., BLEU, edit distance)

**Expected**:
- temp=0.2: >90% similarity (highly reproducible)
- If <70% similarity: LLMs are NOT reproducible even with deterministic settings

---

### **Category 3: Metadata Metrics** (For Paper Methods Section)

#### **3.1 Actual vs Scheduled Execution**
**What**: Did runs execute on planned schedule?
**Why**: Validates randomization was followed

**Check**:
- % of runs executed on scheduled day: >95%
- % of runs in correct time slot: >95%

**Why it matters**: If execution doesn't match schedule, randomization is broken.

---

#### **3.2 Engine Balance Verification**
**What**: Did each LLM get exactly 540 runs?
**Why**: Ensures fair comparison

**Target**:
- OpenAI: 540 ± 10 (allowing for <2% failures)
- Google: 540 ± 10
- Mistral: 540 ± 10

**If imbalanced**: Analysis may be biased toward one provider.

---

#### **3.3 Time Slot Balance Verification**
**What**: Did each time slot get exactly 540 runs?
**Why**: Ensures temporal analysis is valid

**Target**:
- Morning: 540 ± 10
- Afternoon: 540 ± 10
- Evening: 540 ± 10

---

#### **3.4 Model Version Tracking**
**What**: Did the LLM model version change during experiment?
**Why**: Version changes invalidate comparison

**Check**:
- All OpenAI runs use same model (e.g., gpt-4o-mini-2024-07-18)
- All Google runs use same model (e.g., gemini-1.5-flash)
- All Mistral runs use same model (e.g., mistral-large-2407)

**If version changes**: Flag runs and analyze separately.

---

## Why We Chose These Metrics

### **Primary Hypothesis**: "LLMs are unreliable for marketing content"

**Supporting evidence needed**:
1. **High error rate** (>20%) → Metric 2.1
2. **Temporal inconsistency** (outputs vary by time) → Metric 2.2
3. **Temperature-error correlation** (creativity increases errors) → Metric 2.3
4. **Low reproducibility** (same prompt ≠ same output) → Metric 2.8

### **Alternative Hypothesis**: "LLMs are reliable"

**Would show**:
1. Low error rate (<5%)
2. No time-of-day effects
3. Consistent outputs across temperatures
4. High reproducibility

---

## Data We'll Share with Team

### **During Run** (Real-Time Dashboard):
- Completion progress: X/1620 (Y%)
- Current failure rate: Z%
- Estimated completion time
- Current cost

### **After Run** (Summary Report):
- Error rate by LLM provider
- Temporal consistency analysis
- Temperature effect analysis
- Cost breakdown
- Compliance violation categories

### **For Paper** (Statistical Results):
- ANOVA results for time-of-day effects
- T-tests for LLM comparisons
- Regression analysis for temperature effects
- Descriptive statistics for all metrics

---

## Timeline

**Week 1** (Current): Setup and validation
- ✅ Randomization complete
- ✅ Metrics defined
- ⏳ Ready to launch

**Week 2** (Experimental Run): Data collection
- Day 1-7: Execute 1,620 runs (monitoring active)
- Real-time tracking of operational metrics

**Week 3** (Analysis): Run Glass Box Audit
- Analyze all 1,620 outputs for errors
- Calculate research metrics
- Statistical tests

**Week 4** (Reporting): Write up results
- Generate figures
- Statistical analysis
- Draft paper sections

---

## Key Takeaway for Colleagues

**We're measuring**:
1. **Operational**: Did the experiment run successfully?
2. **Research**: Are LLMs reliable or unreliable?
3. **Metadata**: Can we trust the randomization?

**The answer to "Are LLMs reliable?" comes from**:
- Error detection rate (Metric 2.1)
- Temporal consistency (Metric 2.2)
- Reproducibility (Metric 2.8)

Everything else supports these primary findings.
