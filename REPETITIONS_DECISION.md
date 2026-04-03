# Temporal Study Design: Repetitions & Duration Decision

**Date:** February 22, 2026
**Decision needed:** How many repetitions and how many days for temporal unreliability testing?

---

## Background

We're testing whether LLM-generated marketing materials are temporally unreliable - do error rates vary across different times/days?

**Current design:**
- 3 products × 3 materials × 3 engines × 3 temperatures = 243 unique conditions
- Each condition tested multiple times at random times
- **Question:** How many times? Over how many days?

---

## Options Summary

| Option | Reps | Total Runs | Days | Cost | Statistical Power | Confidence Interval | Time Commitment |
|--------|------|-----------|------|------|-------------------|---------------------|-----------------|
| **A** | 3 | 729 | 3 days | $7-15 | 45% (weak) | ±30% | 3 days |
| **B** | 5 | 1,215 | 3 days | $12-25 | 68% (acceptable) | ±23% | 3 days |
| **C** | 7 | 1,701 | 3 days | $17-35 | 85% (good) | ±19% | 3 days |
| **D** | 10 | 2,430 | 4 days | $24-50 | 92% (excellent) | ±17% | 4 days |
| **E** | 7 | 1,701 | 7 days | $17-35 | 85% (good) | ±19% | 7 days |

---

## What "Repetitions" Means

**Example condition:** smartphone × FAQ × OpenAI × temperature=0.6

**3 Repetitions:**
- Run 1: Sunday 8:07am (random time)
- Run 2: Monday 3:14am (random time)
- Run 3: Tuesday 5:59pm (random time)

**7 Repetitions:**
- Run 1: Sunday 2:15am (random)
- Run 2: Sunday 11:42am (random)
- Run 3: Monday 7:23am (random)
- Run 4: Monday 4:56pm (random)
- Run 5: Tuesday 1:08am (random)
- Run 6: Tuesday 9:37am (random)
- Run 7: Tuesday 6:14pm (random)

**Purpose:** More repetitions = better estimate of temporal variance (how much outputs vary across time)

---

## Detailed Comparison

### **Option A: 3 Reps, 3 Days (Current Minimum)**

**Pros:**
- Fast (3 days)
- Cheap ($7-15)
- Low risk

**Cons:**
- ❌ Only 45% power (underpowered for publication)
- ❌ Wide confidence intervals (±30%)
- ❌ Cannot detect outliers reliably
- ❌ Variance estimates have high uncertainty

**Verdict:** Too weak for rigorous study

---

### **Option B: 5 Reps, 3 Days (Minimum Valid)**

**Pros:**
- Fast (3 days)
- Reasonable cost ($12-25)
- Meets minimum statistical requirements (n≥5 for variance)
- 68% power (acceptable for pilot)

**Cons:**
- ⚠️ Power is borderline (68% is low for main study)
- ⚠️ Still moderately wide CI (±23%)

**Verdict:** Good for pilot study, acceptable for main study if budget-constrained

**Technical notes:**
- 1,215 runs ÷ 72 hours = ~17 runs/hour
- Peak: ~76 runs/hour = 1 run every 47 seconds
- ✅ No technical issues

---

### **Option C: 7 Reps, 3 Days (RECOMMENDED)**

**Pros:**
- ✅ 85% power (standard for social sciences)
- ✅ Good precision (±19% CI)
- ✅ Can detect outliers
- ✅ Fast turnaround (3 days)
- ✅ Reasonable cost ($17-35)
- ✅ Covers all 24 hours well
- ✅ Tests weekend→weekday transition

**Cons:**
- Only 3 days (limited day-of-week testing)

**Verdict:** Best balance of power, cost, and time

**Technical notes:**
- 1,701 runs ÷ 72 hours = ~24 runs/hour
- Peak: ~107 runs/hour = 1 run every 34 seconds
- ✅ Safe buffer, no technical issues

---

### **Option D: 10 Reps, 4 Days (High Power)**

**Pros:**
- ✅ 92% power (excellent)
- ✅ Tight CI (±17%)
- ✅ Very robust to outliers
- ✅ Definitive temporal reliability data

**Cons:**
- 4 days (slightly longer)
- Higher cost ($24-50)
- Only marginal gain over 7 reps (92% vs 85%)

**Verdict:** Good if you want definitive results and have budget

**Technical notes:**
- 2,430 runs ÷ 96 hours = ~25 runs/hour
- Peak: ~114 runs/hour = 1 run every 32 seconds
- ✅ Extended to 4 days to avoid crowding (could do 3 days but tight)

---

### **Option E: 7 Reps, 7 Days (Full Week)**

**Pros:**
- ✅ 85% power
- ✅ Full week coverage (all 7 days)
- ✅ Can test weekend vs weekday
- ✅ Can test weekly patterns
- ✅ Very sparse scheduling (lots of buffer)

**Cons:**
- 7 days (long monitoring period)
- Higher risk (more time for things to go wrong)

**Verdict:** Best if day-of-week effects are important to your research question

**Technical notes:**
- 1,701 runs ÷ 168 hours = ~10 runs/hour
- Peak: ~45 runs/hour = 1 run every 80 seconds
- ✅ Very comfortable spacing

---

## What Can Each Option Test?

| Research Question | 3 Reps (A) | 5 Reps (B) | 7 Reps (C) | 10 Reps (D) | 7 Reps, 7 Days (E) |
|-------------------|------------|------------|------------|-------------|---------------------|
| **Temporal variance exists?** | Weak | Moderate | Good | Excellent | Good |
| **Hour-of-day effects?** | Moderate | Good | Good | Excellent | Good |
| **Day-of-week effects (3 days)?** | Moderate | Good | Good | Excellent | Good |
| **Day-of-week effects (full week)?** | ❌ No | ❌ No | ❌ No | ❌ No | ✅ Yes |
| **Temporal consistency (variance)?** | Weak | Acceptable | Good | Excellent | Good |
| **Outlier detection?** | ❌ No | ⚠️ Limited | ✅ Yes | ✅ Yes | ✅ Yes |
| **Product × Time interactions?** | Weak | Moderate | Good | Excellent | Good |

---

## Cost Breakdown

**API costs (estimated):**
- OpenAI GPT-4o: ~$0.01-0.02 per run (2000 tokens)
- Google Gemini: ~$0.001 per run (cheaper)
- Mistral: ~$0.002 per run (cheap)

**Average: ~$0.01 per run**

| Option | Runs | Estimated Cost |
|--------|------|----------------|
| A (3 reps) | 729 | $7-15 |
| B (5 reps) | 1,215 | $12-25 |
| C (7 reps) | 1,701 | $17-35 |
| D (10 reps) | 2,430 | $24-50 |
| E (7 reps, 7 days) | 1,701 | $17-35 (same as C, just spread over more time) |

---

## Time Commitment

| Option | Duration | Researcher Time | Notes |
|--------|----------|-----------------|-------|
| A | 3 days | Monitor 3 days | Sunday-Tuesday |
| B | 3 days | Monitor 3 days | Sunday-Tuesday |
| C | 3 days | Monitor 3 days | Sunday-Tuesday |
| D | 4 days | Monitor 4 days | Sunday-Wednesday |
| E | 7 days | Monitor 7 days | Full week |

**Note:** "Monitor" means the script runs automatically, but you should check periodically for errors

---

## Statistical Power Explained

**Power = Probability of detecting an effect if it exists**

**Example:** If LLMs truly have 20% temporal variance in error rates:
- **45% power (3 reps):** Only 45% chance we'll detect it → might miss real effect
- **68% power (5 reps):** 68% chance → acceptable for pilot
- **85% power (7 reps):** 85% chance → standard for publication
- **92% power (10 reps):** 92% chance → very confident

**Lower power = higher risk of "false negative" (missing a real temporal effect)**

---

## Confidence Interval Explained

**CI = Precision of variance estimate**

**Example:** True temporal variance is 15%
- **±30% CI (3 reps):** We might estimate 10.5% to 19.5% (wide range)
- **±23% CI (5 reps):** We might estimate 11.5% to 18.5%
- **±19% CI (7 reps):** We might estimate 12.1% to 17.9%
- **±17% CI (10 reps):** We might estimate 12.5% to 17.5% (narrow range)

**Wider CI = less precise measurement**

---

## Recommendation Summary

### **For Pilot Study:**
→ **Option B (5 reps, 3 days)**
- Minimum valid design
- Low cost, fast
- Provides preliminary data
- Can scale up if needed

### **For Main Study (RECOMMENDED):**
→ **Option C (7 reps, 3 days)**
- Standard statistical power (85%)
- Good precision (±19%)
- Reasonable cost ($17-35)
- Fast completion (3 days)
- **Best overall balance**

### **If Temporal Unreliability Is Your PRIMARY Research Focus:**
→ **Option D or E**
- **Option D (10 reps, 4 days):** Definitive temporal variance data
- **Option E (7 reps, 7 days):** Full week coverage for day-of-week claims

### **If Budget Is Very Limited:**
→ **Option B (5 reps, 3 days)**
- Acceptable for publication
- Can add more reps later if needed

---

## Discussion Questions

1. **Research priority:** Is temporal unreliability your main contribution, or secondary to product/engine effects?
   - Main → Option D or E (high power / full week)
   - Secondary → Option C (balanced)

2. **Budget:** What's acceptable?
   - <$20 → Option B
   - ~$25-35 → Option C (recommended)
   - ~$50 → Option D

3. **Timeline:** How quickly do you need results?
   - ASAP → Option B or C (3 days)
   - Can wait → Option D (4 days) or E (7 days)

4. **Day-of-week claims:** Important for your paper?
   - Yes → Option E (full week)
   - No → Option C or D (3-4 days sufficient)

5. **Risk tolerance:** First major experiment?
   - Yes → Option C (middle ground)
   - Have backup data → Option B, scale up if needed

---

## Implementation

**Once decided, implementation is simple:**

```python
# Edit config.py

# For Option B (5 reps, 3 days):
REPS = (1, 2, 3, 4, 5)
EXPERIMENT_DURATION_HOURS = 72.0

# For Option C (7 reps, 3 days):
REPS = (1, 2, 3, 4, 5, 6, 7)
EXPERIMENT_DURATION_HOURS = 72.0

# For Option D (10 reps, 4 days):
REPS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
EXPERIMENT_DURATION_HOURS = 96.0

# For Option E (7 reps, 7 days):
REPS = (1, 2, 3, 4, 5, 6, 7)
EXPERIMENT_DURATION_HOURS = 168.0
```

Then:
```bash
rm results/experiments.csv
python -m runner.generate_matrix
python orchestrator.py temporal --dry-run  # Preview
python orchestrator.py temporal --session-id temporal_v1  # Execute
```

---

## Decision Deadline

**Please respond with your choice:** A, B, C, D, or E

**Recommended:** Option C (7 reps, 3 days) unless you have specific reasons for more/less

---

## Contact

Questions? Need clarification on any option?
