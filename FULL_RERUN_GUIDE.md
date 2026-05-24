# Full Experiment Rerun Guide (May 25-31, 2026)

## What Went Wrong

On May 18-20, 2026, attempted to rerun Gemini runs with `max_tokens=10000`, but **forgot to update the `max_tokens` column in experiments.csv**.

**Root Cause:** The `max_tokens` value is stored in experiments.csv at generation time (not read from config.py at runtime). Result: 421/540 (78%) of Gemini runs were truncated with `finish_reason: MAX_TOKENS`.

## Solution: Full Rerun with max_tokens=20000

Regenerate the entire 1,620-run matrix with:
- **max_tokens = 20000** (Gemini will cap at 8,192 automatically)
- **Start date: May 25, 2026** (Sunday)
- **End date: May 31, 2026** (Saturday)
- **Same randomization**: Seed 42 preserves experimental design

## Why Regenerate Instead of Modify CSV?

**Regeneration is cleaner and safer:**
- ✅ Script reads `DEFAULT_MAX_TOKENS` from config.py directly
- ✅ One command vs three separate scripts
- ✅ No risk of missing a column or leaving stale data
- ✅ Fresh start with correct parameters

**Trade-off:**
- ❌ run_ids will change (but randomization pattern stays identical)
- ✅ Not a problem since we're starting fresh anyway

## Step-by-Step Instructions

### Prerequisites

```bash
# Ensure you're in the project directory
cd ~/llm_research_app

# Activate virtual environment
source .venv/bin/activate

# Verify you have the latest code
git pull
```

### Step 1: Update config.py

Edit `config.py` line 105:

```python
DEFAULT_MAX_TOKENS = 20000  # Was 2000, then 10000
```

**Why 20000?**
- Gemini Flash output limit: 8,192 tokens (hard API cap)
- Setting 20K gives headroom but API will cap at 8,192
- Cost based on actual tokens used, not limit requested
- Ensures we get full outputs without truncation

### Step 2: Backup Current Data

```bash
# Create backup directory
mkdir -p results/backups

# Backup experiments.csv
cp results/experiments.csv results/backups/experiments_before_full_rerun_$(date +%Y%m%d).csv

# Backup outputs (optional, if you want to keep failed runs)
tar -czf results/backups/outputs_before_rerun_$(date +%Y%m%d).tar.gz outputs/
```

### Step 3: Regenerate Matrix

```bash
# Generate new matrix with seed 42 and May 25 start date
python scripts/test_randomizer_stratified.py --seed 42 --start-date 2026-05-25
```

**Expected output:**
```
STRATIFIED RANDOMIZATION
========================================================================
Random seed: 42
Days: 7 (full week)
Start date: 2026-05-25
...
✓ Generated 1620 runs
✓ Perfect engine balance achieved!
✓ Perfect time slot balance achieved!
💾 Results saved to: results/experiments.csv
```

**What this does:**
- Generates 1,620 runs (3 engines × 3 products × 3 temps × 3 materials × 3 times × 3 reps)
- Assigns scheduled_datetime from May 25-31 (Sunday-Saturday)
- Uses `DEFAULT_MAX_TOKENS = 20000` from config.py
- Preserves day-of-week and time-of-day patterns (stratified randomization)
- Ensures exact balance: 540 runs per engine, 540 per time slot

### Step 4: Verify max_tokens

```bash
# Check max_tokens column for Google runs
grep "google" results/experiments.csv | head -1 | cut -d',' -f11

# Expected output: 20000
```

**If it shows 2000 or 10000:**
- ❌ You forgot to update config.py
- Go back to Step 1 and regenerate

### Step 5: Verify Matrix Statistics

```bash
# Count total runs
wc -l results/experiments.csv
# Expected: 1621 lines (1620 runs + 1 header)

# Count by engine
grep "openai" results/experiments.csv | wc -l   # Expected: 540
grep "google" results/experiments.csv | wc -l   # Expected: 540
grep "mistral" results/experiments.csv | wc -l  # Expected: 540

# Check date range
grep "google" results/experiments.csv | cut -d',' -f18 | sort | head -1  # First date
grep "google" results/experiments.csv | cut -d',' -f18 | sort | tail -1  # Last date
# Expected: 2026-05-25T... to 2026-05-31T...

# Verify all status=pending
grep -v "pending" results/experiments.csv | grep -v "status" | wc -l
# Expected: 0 (only header contains non-pending)
```

### Step 6: Start Temporal Execution

```bash
# Run in background with nohup (recommended for 7-day run)
nohup python orchestrator.py temporal \
  --experiment-start 2026-05-25T00:00:00 \
  --session-id full_rerun_20k \
  > temporal_execution.log 2>&1 &

# Save PID for later
echo $! > temporal_pid.txt

# Check it's running
ps aux | grep orchestrator
```

**What this does:**
- Waits for each run's `scheduled_datetime`
- Executes runs one at a time in chronological order
- Runs continuously for 7 days (May 25-31)
- Logs all output to `temporal_execution.log`

### Step 7: Monitor Progress

#### Option A: Quick Status Check

```bash
# Overall progress
python scripts/monitor_experiment.py

# Google only
python scripts/monitor_experiment.py --engine google

# OpenAI only
python scripts/monitor_experiment.py --engine openai
```

#### Option B: Live Monitoring (Auto-refresh)

```bash
# Auto-refresh every 60 seconds
python scripts/monitor_experiment.py --watch

# Custom interval (e.g., every 5 minutes)
python scripts/monitor_experiment.py --watch --interval 300
```

**Monitor Output Includes:**
- 📊 Overall progress (completed/pending/failed)
- 🪙 Token usage statistics (min/max/mean)
- ⚠️ MAX_TOKENS truncation warnings
- 🤖 Completion rates by engine
- 📦 Completion rates by product
- ❌ Recent failures and error types

#### Option C: Check Logs

```bash
# Tail live execution log
tail -f temporal_execution.log

# Check for errors
grep -i error temporal_execution.log

# Check for MAX_TOKENS
grep MAX_TOKENS results/experiments.csv
```

### Step 8: Stop/Resume If Needed

#### Stop Execution

```bash
# Find PID
cat temporal_pid.txt

# Kill process
kill $(cat temporal_pid.txt)

# Verify stopped
ps aux | grep orchestrator
```

#### Resume Execution

```bash
# Just restart - it will skip completed runs automatically
nohup python orchestrator.py temporal \
  --experiment-start 2026-05-25T00:00:00 \
  --session-id full_rerun_20k \
  > temporal_execution_resumed.log 2>&1 &

echo $! > temporal_pid.txt
```

**Important:** Temporal mode automatically:
- Skips runs with `status=completed`
- Retries runs with `status=failed`
- Waits for future `scheduled_datetime`

## Monitoring Strategy

### Daily Checks (Recommended)

```bash
# Morning check (9am)
python scripts/monitor_experiment.py

# Evening check (9pm)
python scripts/monitor_experiment.py
```

**Look for:**
- ✅ Progress increasing steadily (~231 runs/day)
- ✅ No MAX_TOKENS warnings
- ✅ Completion tokens <8,000 (Gemini)
- ✅ Low failure rate (<5%)

**Red flags:**
- ❌ MAX_TOKENS appearing in finish_reason
- ❌ High failure rate (>10%)
- ❌ Completion tokens consistently >7,500 (Gemini near limit)
- ❌ Progress stalled (same number of completed runs for 2+ hours)

### Mid-Experiment Check (May 28)

After 3 days (~972 runs completed), do a thorough check:

```bash
# Full report
python scripts/monitor_experiment.py > mid_experiment_report.txt

# Verify no truncation
grep MAX_TOKENS results/experiments.csv | wc -l
# Expected: 0

# Check token distribution
python analysis/diagnose_gemini_tokens.py

# If issues found, stop and investigate
kill $(cat temporal_pid.txt)
```

## Expected Timeline

| Date | Day | Runs | Cumulative | Progress |
|------|-----|------|------------|----------|
| May 25 | Sun | 232 | 232 | 14.3% |
| May 26 | Mon | 232 | 464 | 28.6% |
| May 27 | Tue | 232 | 696 | 43.0% |
| May 28 | Wed | 231 | 927 | 57.2% |
| May 29 | Thu | 231 | 1158 | 71.5% |
| May 30 | Fri | 231 | 1389 | 85.7% |
| May 31 | Sat | 231 | 1620 | 100.0% |

**Run distribution:**
- 3 days with 232 runs (Mon, Tue, Wed get +1 extra run)
- 4 days with 231 runs (Thu-Sun)
- Total: 1,620 runs

## Cost Estimates

### Per Run (Average)
- GPT-4o: ~$0.03/run
- Gemini Flash: ~$0.001/run
- Mistral Large: ~$0.02/run

### Full Experiment (1,620 runs)
- OpenAI (540 runs): ~$16
- Google (540 runs): ~$0.50
- Mistral (540 runs): ~$11
- **Total: ~$27.50**

**With max_tokens=20000:**
- Cost based on actual tokens generated (not limit)
- Gemini caps at 8,192 automatically (no overage)
- Estimate assumes ~2K completion tokens average

## Troubleshooting

### Issue: All runs showing MAX_TOKENS

**Cause:** config.py not updated before regeneration

**Fix:**
```bash
# Stop execution
kill $(cat temporal_pid.txt)

# Update config.py: DEFAULT_MAX_TOKENS = 20000
# Regenerate matrix
python scripts/test_randomizer_stratified.py --seed 42 --start-date 2026-05-25

# Restart
nohup python orchestrator.py temporal --experiment-start 2026-05-25T00:00:00 --session-id full_rerun_20k > temporal_execution.log 2>&1 &
```

### Issue: Temporal execution stopped unexpectedly

**Cause:** Server reboot, SSH disconnect, or Python crash

**Fix:**
```bash
# Check if process running
ps aux | grep orchestrator

# If not running, resume
nohup python orchestrator.py temporal --experiment-start 2026-05-25T00:00:00 --session-id full_rerun_20k > temporal_execution_resumed.log 2>&1 &
```

### Issue: High failure rate (>10%)

**Cause:** API rate limits, network issues, or bad API keys

**Fix:**
```bash
# Check error types
python scripts/monitor_experiment.py | grep -A 10 "Error types"

# If rate_limit errors, add delay in orchestrator
# If api_error, check API keys in .env
# If timeout, check network connection
```

### Issue: Gemini runs using >8,000 tokens

**Cause:** Prompts too long or product YAMLs too large

**Fix:**
```bash
# Identify which products
python scripts/monitor_experiment.py --engine google

# Check prompt sizes
python analysis/diagnose_gemini_tokens.py --show-prompts

# If needed, truncate prompts in runner/run_job.py (line 160)
```

## Post-Experiment Validation

### After Completion (June 1, 2026)

```bash
# 1. Verify all runs completed
python scripts/monitor_experiment.py

# 2. Check for truncation
grep MAX_TOKENS results/experiments.csv | wc -l
# Expected: 0

# 3. Run statistical analysis
python analysis/gpt4o_statistical_analysis.py

# 4. Create human review samples
python analysis/export_human_review_subsets.py --sample-size 100 --seed 42

# 5. Backup final results
cp results/experiments.csv results/experiments_full_rerun_complete_$(date +%Y%m%d).csv
tar -czf results/outputs_full_rerun_$(date +%Y%m%d).tar.gz outputs/
```

## Success Criteria

✅ **All 1,620 runs completed**
✅ **Zero MAX_TOKENS truncation**
✅ **Failure rate <5%**
✅ **Completion tokens: min=100, max=8000, mean=2000-3000**
✅ **Exactly 540 runs per engine**
✅ **Date range: May 25-31, 2026**
✅ **All outputs >100 tokens** (no truncated materials)

## Quick Reference Commands

```bash
# Start experiment
nohup python orchestrator.py temporal --experiment-start 2026-05-25T00:00:00 --session-id full_rerun_20k > temporal_execution.log 2>&1 &

# Monitor progress
python scripts/monitor_experiment.py

# Live monitoring
python scripts/monitor_experiment.py --watch

# Check logs
tail -f temporal_execution.log

# Stop experiment
kill $(cat temporal_pid.txt)

# Resume experiment
nohup python orchestrator.py temporal --experiment-start 2026-05-25T00:00:00 --session-id full_rerun_20k > temporal_execution_resumed.log 2>&1 &
```

## Contact

If issues arise during the 7-day run:
1. Run monitoring script: `python scripts/monitor_experiment.py > issue_report.txt`
2. Check logs: `tail -100 temporal_execution.log > recent_logs.txt`
3. Share both files for diagnosis

---

**Last Updated:** May 24, 2026
**Experiment Window:** May 25-31, 2026 (7 days)
**Total Runs:** 1,620
**Estimated Cost:** ~$27.50
**max_tokens:** 20,000 (Gemini caps at 8,192)
