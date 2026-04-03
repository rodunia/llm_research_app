# Research Design Decision: Temporal Unreliability Study

**Date:** February 22, 2026
**To:** Research Team
**From:** [Your Name]
**Re:** Experimental design for LLM temporal unreliability testing

---

## Background

We're investigating **temporal unreliability** in LLM-generated marketing materials - whether error rates and compliance violations vary by date/time of execution. Prior literature suggests LLM outputs can vary with temporal factors (time of day, day of week, API load patterns).

**Current status:** We have 729 experimental runs ready (3 products × 3 materials × 3 engines × 3 temperatures × 3 repetitions × 3 time-of-day labels). The code is complete and tested.

**Decision needed:** How to schedule execution to properly test temporal effects.

---

## The Core Issue

We need to decide between **two fundamentally different experimental approaches:**

### Option A: True Temporal Distribution (3-day execution)
- Runs scheduled at randomized times across 72-hour window
- Example: Run 1 executes Sunday 2am, Run 2 executes Monday 5pm, etc.
- Takes **3 days** to complete

### Option B: Sequential Execution (same-day execution)
- All 729 runs execute sequentially as fast as possible
- Records actual execution timestamps
- Takes **6-12 hours** to complete

**The critical question:** Does our research question require Option A, or is Option B sufficient?

---

## Detailed Comparison

| Criterion | Option A: True Temporal | Option B: Sequential |
|-----------|------------------------|---------------------|
| **Duration** | 3 days (72 hours) | 6-12 hours |
| **Can test time-of-day effects** | ✅ Yes (0-23 hours) | ❌ No (all runs in narrow window) |
| **Can test day-of-week effects** | ✅ Yes (Sun/Mon/Tue) | ❌ No (likely single day) |
| **Can test continuous time effects** | ✅ Yes (0-72 hour gradient) | ❌ No |
| **Controls for execution order bias** | ✅ Yes (randomized) | ⚠️ Partial (need to shuffle) |
| **Separates time from order effects** | ✅ Yes (orthogonal) | ❌ No (confounded) |
| **Captures API load variations** | ✅ Yes (peak/off-peak) | ⚠️ Limited |
| **Detects model updates** | ✅ Possible (3-day span) | ❌ Unlikely (same day) |
| **Technical complexity** | Higher (needs scheduler) | Lower (batch script) |
| **Risk of incomplete data** | Higher (3-day failure window) | Lower (single session) |
| **Publication strength** | Strong for temporal claims | Weak for temporal claims |

---

## Statistical Power

### Option A (True Temporal)
- **Temporal variables:** 24 hours × 3 days = 72 unique timepoints
- **Statistical tests enabled:**
  - Continuous time effect: `lm(violations ~ hours_since_start)`
  - Hourly patterns: `anova(lm(violations ~ hour_of_day))`
  - Daily patterns: `anova(lm(violations ~ day_of_week))`
  - Peak vs off-peak: `t.test(violations ~ peak_hours)`
- **Power:** >95% to detect medium effect (Cohen's d = 0.5, α=0.05)

### Option B (Sequential)
- **Temporal variables:** ~10-20 unique timepoints (compressed window)
- **Statistical tests enabled:**
  - Execution order: `lm(violations ~ run_order)`
  - (Cannot test hour, day, or true temporal effects)
- **Power:** Adequate for order effects, **zero for temporal effects**

---

## Methodological Concerns

### For Option B (Sequential):

**Reviewer Challenge 1:**
*"You claim to test temporal unreliability but all experiments ran within 8 hours on the same day. Where is the temporal variation?"*

**Reviewer Challenge 2:**
*"Your metadata shows 'scheduled_datetime' and 'hour_of_day' fields, but these are just random labels, not actual execution times. This is misleading."*

**Reviewer Challenge 3:**
*"Execution order effects (Run 1 vs Run 729) are confounded with 'time'. You cannot separate whether differences are due to chronological time or API fatigue."*

### For Option A (True Temporal):

**Reviewer Challenge 1:**
*"3-day execution window introduces risk of confounding events (model updates, API changes). How did you control for this?"*

**Response:** We tracked `model_version`, `api_response_code`, `git_commit_hash` to detect infrastructure changes. Randomization distributes confounds evenly across conditions.

---

## Research Question Alignment

**Our stated research question:**
*"Do LLMs produce temporally unreliable outputs with varying error rates across different times?"*

**Does Option B answer this?**
❌ **No.** Without temporal variation, we cannot test temporal effects.

**What CAN Option B answer?**
- Do error rates vary by product, material, engine, or temperature? ✅
- Do error rates change with execution order? ✅
- Are there systematic biases in LLM outputs? ✅

**If we choose Option B, we should:**
- Reframe research question to focus on product/engine factors
- Remove or de-emphasize temporal unreliability claims
- Treat temporal metadata as documentation-only

---

## Practical Considerations

### Option A Implementation
**Technical requirements:**
- Job scheduler (cron, APScheduler, or orchestrator)
- Monitoring system (detect stalled jobs)
- Error recovery (re-run failed jobs)

**Estimated effort:** 4-8 hours to implement scheduler

**Risk mitigation:**
- Run 24-hour pilot first (81 runs)
- Implement watchdog to detect failures
- Keep backup of completed runs

### Option B Implementation
**Technical requirements:**
- Random shuffle of execution order
- Current `run_job.py` batch runner (already working)

**Estimated effort:** <1 hour (minimal changes)

**Risk mitigation:**
- Run 50-run test batch first
- Monitor API rate limits

---

## Recommended Decision Framework

### Choose Option A if:
- ✅ Temporal unreliability is central to research contribution
- ✅ Publication target is Q1 journal requiring rigorous methods
- ✅ 3-day execution timeline is acceptable
- ✅ Team has bandwidth for scheduler implementation

### Choose Option B if:
- ✅ Primary focus is product/engine comparison (temporal is secondary)
- ✅ Fast turnaround needed (conference deadline, pilot study)
- ✅ Prefer lower technical risk
- ✅ Temporal effects can be tested in future follow-up study

---

## Hybrid Option (Pilot + Scale)

**Compromise approach:**

**Phase 1 (Pilot):** Run 81 experiments (3×3×3×3) across 24 hours with true temporal distribution
- Tests feasibility of scheduler
- Provides preliminary temporal data
- Low risk (1 day commitment)

**Phase 2 (Decision):** Based on pilot results:
- If temporal effects found → Full 729-run study with Option A
- If no temporal effects → Proceed with Option B for remaining factors
- If technical issues → Revise approach

---

## Questions for Team Discussion

1. **Research priority:** Is temporal unreliability central or secondary to our contribution?

2. **Publication target:** Q1 journal (requires Option A) or conference/lower-tier (Option B acceptable)?

3. **Timeline constraints:** Do we have 3 days for data collection, or is same-day turnaround needed?

4. **Technical capacity:** Who can implement/monitor the scheduler for Option A?

5. **Risk tolerance:** Comfortable with 3-day failure window (Option A) or prefer single-session safety (Option B)?

6. **Pilot study:** Should we run 24-hour pilot before committing to full design?

---

## My Recommendation

**For rigorous temporal unreliability study:**
→ **Option A** (true temporal distribution)

**Rationale:**
- Research question explicitly states temporal unreliability
- Literature gap is in temporal testing (novel contribution)
- Methodology section will be stronger
- Separates temporal from order effects cleanly
- 3-day timeline is reasonable for this scale

**With:** 24-hour pilot study first to validate technical approach

---

## Next Steps (Pending Team Decision)

**If Option A chosen:**
1. Implement job scheduler in orchestrator
2. Run 24-hour pilot (81 runs)
3. Analyze pilot results
4. Execute full 729-run study (72 hours)

**If Option B chosen:**
1. Add execution order randomization
2. Run 50-run test batch
3. Execute full 729 runs (6-12 hours)
4. De-emphasize temporal claims in paper

**If Hybrid chosen:**
1. Execute 24-hour pilot
2. Team meeting to review pilot data
3. Decide on full-scale approach

---

## Decision Deadline

**Please respond by:** [DATE]

**Discussion meeting:** [DATE/TIME] if needed

**Required:** Consensus on Option A vs B vs Hybrid before proceeding with data collection

---

## Contact

Questions or concerns? Reply to this thread or contact me directly.

**Technical details available in:**
- `RANDOMIZATION_IMPLEMENTATION_COMPLETE.md` (current implementation)
- `METADATA_FINAL_69_COLUMNS.md` (metadata schema)
- `config.py` (experimental parameters)
