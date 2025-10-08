# Quick Start Guide

## Pre-Flight Checklist

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Test Engine Connectivity

**IMPORTANT**: Run this before executing the full pipeline to verify all API keys work:

```bash
python test_engines.py
```

You should see:

```
✓ All engines working correctly!
You can proceed with the experimental pipeline.
```

If any engine fails, check your `.env` file and API keys.

---

## First Run (Step-by-Step)

### Step 1: Generate Experimental Matrix

```bash
python -m runner.generate_matrix
```

**What happens:**
- Creates `results/results.csv` with 1,215 experimental runs
- Each run is a unique combination of: product × template × time × temperature × repetition × engine
- All runs start with `status="pending"`

**Expected output:**
```
Matrix size: 1215 runs (3 × 5 × 3 × 3 × 3 × 3)
Generated 1215 jobs. No collisions.
```

### Step 2: Check Status

```bash
python orchestrator.py status
```

**Expected output:**
```
✓ Matrix generated: 1215 total runs
  • Pending: 1215
  • Completed: 0
```

### Step 3: Run Morning Subset (405 runs)

```bash
python orchestrator.py run --time-of-day morning
```

**What happens:**
- Filters 405 runs where `time_of_day_label="morning"`
- Sends prompts to LLM engines (OpenAI, Google, Mistral)
- Saves outputs to `outputs/{run_id}.txt`
- Updates `results/results.csv` with `status="completed"`

**Progress display:**
```
Run 1/405 | openai | smartphone_mid | d10dea468878 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 0% • 0/405 • 0:00:03 • 0:02:15
```

**Expected duration:** ~30-60 minutes (depends on API rate limits)

### Step 4: Verify Completion

```bash
python orchestrator.py status
```

**Expected output:**
```
✓ Matrix generated: 1215 total runs
  • Pending: 810
  • Completed: 405
✓ Outputs: 405 files
```

### Step 5: Run Evaluation

```bash
python orchestrator.py analyze
```

**What happens:**
1. **Evaluation** (`analysis/evaluate.py`):
   - Screens each output against product YAML (authorized claims, prohibited claims)
   - Labels: Supported, Contradicted, Unsupported, Ambiguous
   - Detects numeric/unit errors
   - Saves to `analysis/per_run.json`

2. **Analytics** (`analysis/reporting.py`):
   - Aggregates metrics by engine × product
   - Drift analysis (consistency over repetitions)
   - Temperature effects
   - Saves CSVs to `analysis/`

**Expected output:**
```
→ Evaluating outputs
✓ Evaluating outputs completed

→ Generating analytics reports
✓ Generating analytics reports completed

✓ Analysis complete
```

### Step 6: Review Results

```bash
# View engine comparison
cat analysis/engine_comparison.csv

# View per-run details
head -20 analysis/per_run.json
```

---

## Running Afternoon and Evening

```bash
# Afternoon (3:00 PM CET equivalent)
python orchestrator.py run --time-of-day afternoon

# Evening (9:00 PM CET equivalent)
python orchestrator.py run --time-of-day evening

# Check final status
python orchestrator.py status
```

**Expected final status:**
```
✓ Matrix generated: 1215 total runs
  • Pending: 0
  • Completed: 1215
✓ Outputs: 1215 files
✓ Analysis complete
```

---

## Full Pipeline (All-in-One)

After verifying the first manual run works, you can use the full pipeline:

```bash
python orchestrator.py full --time-of-day morning
```

This runs:
1. Generate matrix (if needed)
2. Execute runs
3. Evaluate outputs
4. Generate analytics
5. Create validation sample

---

## Automated Scheduling

### Start Scheduler

```bash
python orchestrator.py schedule
```

**What happens:**
- Runs automatically 3 times per day:
  - **Morning**: 8:00 AM CET
  - **Afternoon**: 3:00 PM CET
  - **Evening**: 9:00 PM CET
- Idempotent: Re-running same config produces same results
- Safe: Skips already-completed runs

**Console output:**
```
Scheduler started

Scheduled runs:
  Morning:   08:00 CET
  Afternoon: 15:00 CET
  Evening:   21:00 CET

Press Ctrl+C to stop
```

### Keep Running in Background

**Option 1: tmux/screen (recommended for development)**

```bash
tmux new -s llm-scheduler
python orchestrator.py schedule
# Press Ctrl+B then D to detach
```

**Option 2: nohup**

```bash
nohup python orchestrator.py schedule > scheduler.log 2>&1 &
```

**Option 3: systemd service (production)**

See `README.md` for systemd configuration.

---

## Progress Indicators

### During Execution

You'll see a rich progress bar showing:

```
Run 127/405 | google | cryptocurrency_corecoin | be65aa13237 ━━━━━━━━━━━━━━━━━━ 31% • 127/405 • 0:05:23 • 0:12:14
```

- **Current run**: 127 of 405
- **Engine**: google (Gemini)
- **Product**: cryptocurrency_corecoin
- **Run ID**: be65aa13237 (first 12 chars)
- **Progress**: 31%
- **Completed/Total**: 127/405
- **Time elapsed**: 5 minutes 23 seconds
- **Time remaining**: ~12 minutes 14 seconds

### Execution Summary

After completion:

```
Execution Summary
✓ Completed: 405
✗ Failed: 0
⏱ Total time: 1234.5s (3.0s per run)
📊 Success rate: 100.0%
```

---

## Common Issues

### "Matrix not found"

**Solution:**
```bash
python -m runner.generate_matrix
```

### "No pending jobs"

All runs already completed. Check status:
```bash
python orchestrator.py status
```

To re-run everything:
```bash
# Archive old results
mv results/results.csv results/results_backup_$(date +%Y%m%d).csv

# Regenerate matrix
python -m runner.generate_matrix

# Run again
python orchestrator.py run --time-of-day morning
```

### API Rate Limits

If you hit rate limits, the engine clients have automatic retry logic with exponential backoff. You may see:

```
[yellow]Retrying due to rate limit (attempt 2/3)...[/yellow]
```

If persistent, reduce concurrency or add delays between runs.

### "Module not found" errors

Make sure you're in the project directory and dependencies are installed:

```bash
cd /Users/dorotajaguscik/PycharmProjects/llm_research_app
pip install -r requirements.txt
```

---

## Next Steps

1. **Manual Validation**: Review `validation/labels_to_fill.csv` and fill in manual QA decisions

2. **Custom Analysis**: Use pandas to analyze `results/results.csv`:
   ```python
   import pandas as pd
   df = pd.read_csv('results/results.csv')
   df.groupby('engine')['total_tokens'].mean()
   ```

3. **Extend Products**: Add new product YAMLs to `products/` and regenerate matrix

4. **Custom Templates**: Add Jinja2 templates to `prompts/` for new content types

---

## Support

If you encounter issues, check:
1. API keys in `.env`
2. `python test_engines.py` passes
3. `python orchestrator.py status` shows expected state
4. Log files in project directory

For questions, see `README.md` for detailed documentation.
