# Team Briefing - LLM Marketing Experiment

**Quick Reference for Colleagues**

---

## What We're Testing

**Research Question**: Are LLMs reliable for generating marketing content, or do they make errors and vary over time?

**Setup**: 1,620 runs across 7 days
- 3 LLMs (OpenAI, Google, Mistral)
- 3 products (Smartphone, Crypto, Supplement)
- 3 materials (FAQ, Digital Ad, Blog Post)
- 3 time-of-day conditions (Morning, Afternoon, Evening)
- 3 temperatures (0.2, 0.6, 1.0)

---

## Key Metrics (What We Measure)

### **Primary Research Metrics** (Answer the Question):

1. **Error Detection Rate**: How many outputs contain factual errors? (Target: <5% if reliable)
2. **Temporal Consistency**: Do outputs vary by time of day? (Target: No variation if reliable)
3. **Reproducibility**: Same prompt = same output? (Target: >90% similarity if reliable)

### **Operational Metrics** (Keep Running):

1. **Completion Rate**: Target ≥98% (≤32 failures)
2. **Response Time**: OpenAI 2-10s, Google 3-15s, Mistral 2-8s
3. **Cost**: ~$124 total (OpenAI $27, Google $16, Mistral $81)

### **Comparison Metrics**:

1. **LLM Comparison**: Which provider has lowest error rate?
2. **Temperature Effect**: Does creativity (temp=1.0) increase errors?
3. **Product Complexity**: Do supplements (FDA) have more errors than smartphones (FTC)?

---

## Timeline

| Week | Phase | Activity |
|------|-------|----------|
| 1 (Now) | Setup | ✅ Randomization complete, metrics defined |
| 2 | Data Collection | Run 1,620 experiments, monitor in real-time |
| 3 | Analysis | Glass Box Audit: detect errors in all outputs |
| 4 | Reporting | Statistical analysis, write paper |

---

## If the Run Crashes

**Good News**: System is crash-resistant by design
- All progress saved in `results/experiments.csv`
- Restart picks up where it left off automatically

**Quick Recovery**:
```bash
# 1. Check progress
python -c "import pandas as pd; print((pd.read_csv('results/experiments.csv')['status']=='completed').sum())"

# 2. Reset stuck runs
python scripts/reset_stuck_runs.py

# 3. Restart
python orchestrator.py run
```

**Common Issues**:
- API rate limit → Wait 5 min, restart with `--batch-size 5 --delay 10`
- Internet lost → Restore connection, reset failed runs
- API key expired → Update `.env`, reset failed runs for that engine

**Prevention**: Run in `screen` session so it survives disconnection

---

## Data We'll Share

**During Run** (Real-Time):
- Progress: X/1620 completed (Y%)
- Failure rate: Z%
- Current cost

**After Run** (Summary):
- Error rate by LLM
- Time-of-day effects
- Temperature effects
- Cost breakdown

**For Paper** (Statistical):
- ANOVA for temporal consistency
- T-tests for LLM comparison
- Regression for temperature
- Compliance violation types

---

## Key Files

| File | Purpose |
|------|---------|
| `results/experiments.csv` | Single source of truth for all runs |
| `outputs/*.txt` | Generated marketing materials (1,620 files) |
| `logs/experimental_run.log` | Execution log |
| `EXPERIMENTAL_METRICS_FOR_TEAM.md` | Full metrics documentation |
| `CRASH_RECOVERY_GUIDE.md` | Detailed recovery procedures |

---

## Expected Outcomes

**If LLMs are RELIABLE**:
- Error rate <5%
- No time-of-day variation
- High reproducibility (>90%)
- Consistent across temperatures

**If LLMs are UNRELIABLE**:
- Error rate >20%
- Significant time-of-day effects
- Low reproducibility (<70%)
- Higher temp = more errors

**Our hypothesis**: LLMs are unreliable (based on pilot study showing compliance issues)

---

## Questions?

- **Metrics**: See `EXPERIMENTAL_METRICS_FOR_TEAM.md`
- **Monitoring**: See `EXPERIMENTAL_RUN_MONITORING_GUIDE.md`
- **Recovery**: See `CRASH_RECOVERY_GUIDE.md`
- **Quick Reference**: See `MONITORING_QUICK_REFERENCE.md`

**Contact**: [Your name/email]
