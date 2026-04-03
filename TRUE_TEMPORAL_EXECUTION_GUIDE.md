# True Temporal Execution Guide

**Status**: ✅ Implemented and ready to use
**Date**: 2026-02-22

---

## What Is This?

This guide explains how to run your 729 LLM experiments with **true temporal distribution** - meaning each run executes at its randomly assigned time across a 72-hour window, enabling rigorous testing of temporal unreliability.

---

## Quick Start

### Step 1: Set Your Start Time

Edit `config.py` and set `EXPERIMENT_START` to when you want the 72-hour window to begin:

```python
# For real study starting Sunday Feb 23, 2026 at midnight UTC:
EXPERIMENT_START = datetime(2026, 2, 23, 0, 0, 0)

# For testing (starts in 1 hour):
from datetime import datetime, timedelta
EXPERIMENT_START = datetime.now() + timedelta(hours=1)
```

### Step 2: Generate Matrix

```bash
# Delete old matrix if it exists
rm results/experiments.csv

# Generate new matrix with randomized times
python -m runner.generate_matrix
```

This creates 729 runs, each with a random `scheduled_datetime` between your start time and start time + 72 hours.

### Step 3: Preview the Schedule (Dry Run)

```bash
python orchestrator.py temporal --dry-run
```

**Output:**
```
Found 729 pending runs
First run: 2026-02-23T00:04:57+00:00
Last run:  2026-02-25T23:56:56+00:00

Past due: 0 runs (will execute immediately)
Future: 729 runs (will wait)

DRY RUN - Schedule Preview:
1. 2026-02-23T00:04:57+00:00 - 5c593482b11444e9... (google)
2. 2026-02-23T00:10:12+00:00 - f5b36c034ee3149a... (google)
...
```

### Step 4: Start the Temporal Scheduler

```bash
# Full 72-hour run
python orchestrator.py temporal --session-id temporal_v1

# The scheduler will:
# 1. Execute any past-due runs immediately
# 2. Wait for future runs and execute at their scheduled times
# 3. Save progress as it goes (CSV updated after each run)
# 4. Run for 72 hours total
```

**Output during execution:**
```
Scheduler started with 729 jobs
Press Ctrl+C to stop (will save progress)

→ Executing 5c593482b11444e9c5f9e420da9603b5f72d4569
   Product: smartphone_mid
   Engine: google
   Temperature: 0.6
   Scheduled: 2026-02-23T00:04:57+00:00
   Actual: 2026-02-23T00:04:58+00:00
✓ 5c593482... completed (1/729)

... (waits until next scheduled time) ...

→ Executing f5b36c034ee3149ac9b84f0ba76ac6c1e8739456
...
```

### Step 5: Monitor Progress

In another terminal:
```bash
python orchestrator.py status
```

**Output:**
```
Pipeline Status

✓ Matrix generated: 729 total runs
  • Pending: 450
  • Completed: 279

✓ Outputs: 279 files
```

---

## How It Works

### Randomization

1. **Matrix generation** assigns each run a random `scheduled_datetime`:
   - Uses fixed seed (12345) for reproducibility
   - Uniform distribution across 72 hours
   - Each run gets unique timestamp

2. **Scheduler reads CSV** and creates 729 scheduled jobs:
   - Past-due runs execute immediately
   - Future runs wait until their scheduled time
   - Executes runs one at a time

3. **Progress is saved automatically**:
   - CSV updated after each run completes
   - If you stop (Ctrl+C), progress is saved
   - Re-running resumes from where you left off

### Resume Capability

If the scheduler stops (crash, Ctrl+C, power failure):

```bash
# Simply re-run the same command
python orchestrator.py temporal --session-id temporal_v1
```

It will:
- Skip runs already marked as "completed" in CSV
- Only schedule remaining "pending" runs
- Continue from where it left off

---

## Advanced Usage

### Testing with Small Window

For a 24-hour pilot test:

```python
# config.py
EXPERIMENT_START = datetime.now() + timedelta(hours=1)
EXPERIMENT_DURATION_HOURS = 24.0  # 1 day instead of 3
```

Then reduce the matrix size temporarily:
```python
# config.py - for pilot only
PRODUCTS = ("smartphone_mid",)  # Just 1 product
MATERIALS = ("faq.j2", "digital_ad.j2", "blog_post_promo.j2")  # 3 materials
ENGINES = ("openai", "google", "mistral")  # 3 engines
TEMPS = (0.2, 0.6, 1.0)  # 3 temps
REPS = (1, 2, 3)  # 3 reps
# Total: 1×3×3×3×3 = 81 runs across 24 hours
```

### Background Execution (Screen/Tmux)

For 72-hour runs, use `screen` or `tmux` to keep it running if you disconnect:

```bash
# Using screen
screen -S temporal_study
python orchestrator.py temporal --session-id temporal_v1
# Press Ctrl+A then D to detach

# Re-attach later
screen -r temporal_study

# Using tmux
tmux new -s temporal_study
python orchestrator.py temporal --session-id temporal_v1
# Press Ctrl+B then D to detach

# Re-attach later
tmux attach -t temporal_study
```

### Logging Output

Capture all output to a log file:

```bash
python orchestrator.py temporal --session-id temporal_v1 2>&1 | tee temporal_execution.log
```

---

## What Gets Tracked

### During Execution

Each run captures:
- **Actual execution timestamp**: `started_at`, `completed_at`
- **Delay from schedule**: `scheduled_vs_actual_delay_sec` (calculated at runtime)
- **Model metadata**: `model`, `model_version`
- **Tokens**: `prompt_tokens`, `completion_tokens`, `total_tokens`
- **Performance**: `execution_duration_sec`, `api_latency_ms`
- **Errors**: `retry_count`, `error_type`, `content_filter_triggered`

### Post-Execution Analysis

After all runs complete, you can analyze:

```python
# In R or Python
import pandas as pd
df = pd.read_csv("results/experiments.csv")

# Time-of-day effects
df.groupby('hour_of_day')['violation_count'].mean()

# Day-of-week effects
df.groupby('day_of_week')['violation_count'].mean()

# Continuous time effects
import statsmodels.formula.api as smf
model = smf.ols('violation_count ~ scheduled_time_numeric', data=df).fit()
print(model.summary())

# Temporal consistency (variance across 3 reps)
df.groupby(['product_id', 'material_type', 'engine', 'temperature'])['violation_count'].std()
```

---

## Comparison: Temporal vs Sequential

### Sequential (Old Way)
```bash
python orchestrator.py run
# Runs all 729 as fast as possible (6-12 hours)
# All runs happen in narrow time window
# Cannot test temporal effects
```

### Temporal (New Way)
```bash
python orchestrator.py temporal
# Runs 729 across 72 hours at scheduled times
# True temporal distribution
# Can test time-of-day, day-of-week effects
```

---

## Troubleshooting

### All Runs Show "Past Due"

**Problem**: All 729 runs execute immediately instead of waiting.

**Cause**: `EXPERIMENT_START` is in the past.

**Fix**: Set `EXPERIMENT_START` to future date in `config.py`, then regenerate matrix:
```bash
rm results/experiments.csv
python -m runner.generate_matrix
python orchestrator.py temporal --dry-run  # Verify schedule
```

### Scheduler Stops or Crashes

**Problem**: Process killed, computer restarted, etc.

**Fix**: Simply re-run the same command:
```bash
python orchestrator.py temporal --session-id temporal_v1
```

It will resume from where it left off (completed runs are skipped).

### Runs Failing with API Errors

**Problem**: Individual runs fail with API errors.

**Check**:
```bash
# View failed runs
grep ',failed,' results/experiments.csv

# View error details
grep 'error_type' results/experiments.csv
```

**Fix**: The scheduler will continue with remaining runs. Failed runs stay as "pending" and can be re-run later.

### Want to Stop Early

**Problem**: Need to stop before 72 hours complete.

**Solution**: Press `Ctrl+C` - progress is saved automatically.

**Resume later**:
```bash
python orchestrator.py temporal --session-id temporal_v1
```

---

## Performance Expectations

### Execution Pattern

- **729 runs across 72 hours** = ~10 runs/hour average
- Actual execution varies due to randomization
- Some hours may have 0 runs, others may have 20+
- This variance is intentional (true randomization)

### API Rate Limits

With randomization, you're unlikely to hit rate limits:
- Average: 10 runs/hour = 1 run every 6 minutes
- Peak: Even if 20 runs scheduled in same hour = 1 run every 3 minutes
- Most APIs allow 60+ requests/minute

### Time Required

- **Full 72-hour study**: Start Sunday → Complete Wednesday
- **24-hour pilot**: Start Monday morning → Complete Tuesday morning
- **Testing (past-due runs)**: All execute immediately (6-12 hours)

---

## Verification Checklist

Before starting your real 72-hour study:

- [ ] Set `EXPERIMENT_START` to correct future date in `config.py`
- [ ] Set `EXPERIMENT_DURATION_HOURS = 72.0` in `config.py`
- [ ] Delete old matrix: `rm results/experiments.csv`
- [ ] Generate new matrix: `python -m runner.generate_matrix`
- [ ] Verify schedule: `python orchestrator.py temporal --dry-run`
- [ ] Check first/last run times are correct
- [ ] Check "Future: 729 runs" (not past due)
- [ ] Verify API keys in `.env` file
- [ ] Test with pilot study first (24 hours, 81 runs)
- [ ] Use screen/tmux for background execution
- [ ] Enable logging: `2>&1 | tee temporal_execution.log`

---

## Next Steps After Implementation

1. **Run 24-hour pilot** (81 runs) to validate:
   - Scheduler works correctly
   - API calls succeed
   - Metadata populates properly
   - No crashes over extended period

2. **Analyze pilot data**:
   - Check for temporal patterns
   - Verify data quality
   - Ensure all fields populated

3. **If pilot successful**, run full 72-hour study (729 runs)

4. **Post-execution**:
   - Run glass box audit: `python3 analysis/glass_box_audit.py`
   - Generate final results CSV
   - Load into R for statistical analysis

---

## Support

**Questions?**
- Check this guide first
- Review `TEMPORAL_STUDY_DESIGN_DECISION.md` for research rationale
- Review `RANDOMIZATION_IMPLEMENTATION_COMPLETE.md` for technical details

**Files to reference**:
- `config.py` - Experimental parameters and start time
- `runner/generate_matrix.py` - Matrix generation with randomization
- `orchestrator.py` - Temporal scheduler implementation
- `results/experiments.csv` - Single source of truth for all runs
