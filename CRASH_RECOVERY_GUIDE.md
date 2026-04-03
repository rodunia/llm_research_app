# Experimental Run - Crash Recovery Guide

**Date**: 2026-03-26
**Purpose**: How to restart if the experimental run crashes or stops

---

## Understanding the System Design

### **Good News**: The system is **crash-resistant by design**

**Why**: All progress is tracked in `results/experiments.csv`
- Each run has a `status` field: pending/running/completed/failed
- When a run completes, status changes to 'completed'
- If system crashes, uncompleted runs stay 'pending' or 'running'
- **Restart picks up where it left off automatically**

---

## Common Crash Scenarios

### **Scenario 1: Python Script Crashes** 🔴
**Symptoms**:
- Script stops with error message
- Terminal shows exception/traceback
- No runs are executing

**What happened**:
- Code bug, memory error, or unexpected exception
- Some runs may be partially complete

**Recovery**:
```bash
# Step 1: Check how many runs completed
python -c "import pandas as pd; df = pd.read_csv('results/experiments.csv'); print(f'Completed: {(df[\"status\"]==\"completed\").sum()}/1620')"

# Step 2: Check for runs stuck in 'running' status
python -c "import pandas as pd; df = pd.read_csv('results/experiments.csv'); print(f'Stuck running: {(df[\"status\"]==\"running\").sum()}')"

# Step 3: Reset stuck runs to pending
python scripts/reset_stuck_runs.py

# Step 4: Restart the experiment
python orchestrator.py run
```

---

### **Scenario 2: API Rate Limit Hit** ⏸️
**Symptoms**:
- Errors mentioning "rate_limit" or "429"
- Script pauses or fails repeatedly
- Many runs showing 'failed' status

**What happened**:
- Too many requests to API in short time
- Need to slow down request rate

**Recovery**:
```bash
# Step 1: Check which engine hit rate limit
grep "rate_limit" logs/experimental_run.log | tail -20

# Step 2: Wait 5-10 minutes for rate limit to reset

# Step 3: Restart with slower batch size
python orchestrator.py run --batch-size 5 --delay 10
# (Send 5 runs at a time, wait 10 seconds between batches)
```

---

### **Scenario 3: Internet Connection Lost** 🌐
**Symptoms**:
- Timeout errors
- Connection refused
- All APIs unreachable

**What happened**:
- Network disconnected
- Runs will show as 'failed' or stuck in 'running'

**Recovery**:
```bash
# Step 1: Restore internet connection

# Step 2: Check failed runs due to timeout
python -c "import pandas as pd; df = pd.read_csv('results/experiments.csv'); print(f'Failed: {(df[\"status\"]==\"failed\").sum()}')"

# Step 3: Reset failed runs to pending
python scripts/reset_failed_runs.py --reason "timeout"

# Step 4: Restart
python orchestrator.py run
```

---

### **Scenario 4: Power Outage / Computer Shutdown** 💻
**Symptoms**:
- Computer turned off unexpectedly
- Script not running when you return
- Last runs incomplete

**What happened**:
- System lost power mid-run
- Runs were interrupted

**Recovery**:
```bash
# Step 1: Check experiments.csv status
python -c "import pandas as pd; df = pd.read_csv('results/experiments.csv'); print(df['status'].value_counts())"

# Step 2: Reset runs stuck in 'running' status
# These were interrupted by shutdown
python scripts/reset_stuck_runs.py

# Step 3: Verify no data corruption
python scripts/verify_data_integrity.py

# Step 4: Resume experiment
python orchestrator.py run
```

---

### **Scenario 5: API Key Expired or Invalid** 🔑
**Symptoms**:
- Authentication errors
- 401 Unauthorized
- All runs for one engine failing

**What happened**:
- API key expired, revoked, or mistyped

**Recovery**:
```bash
# Step 1: Check which engine is failing
python -c "import pandas as pd; df = pd.read_csv('results/experiments.csv'); print(df[df['status']=='failed'].groupby('engine').size())"

# Step 2: Verify API keys
python scripts/test_api_keys.py

# Step 3: Update .env file with correct keys
nano .env

# Step 4: Reset failed runs for that engine
python scripts/reset_failed_runs.py --engine openai

# Step 5: Restart
python orchestrator.py run
```

---

### **Scenario 6: Disk Full** 💾
**Symptoms**:
- "No space left on device"
- Output files not saving
- Script crashes with write errors

**What happened**:
- Output files (1,620 × ~2KB = 3.2MB) filled disk
- Or logs grew too large

**Recovery**:
```bash
# Step 1: Check disk space
df -h

# Step 2: Free up space
# Option A: Compress old logs
gzip logs/*.log.old

# Option B: Move outputs to external drive
mv outputs /external/drive/outputs
ln -s /external/drive/outputs outputs

# Step 3: Resume experiment
python orchestrator.py run
```

---

## Recovery Scripts

### **Script 1: Reset Stuck Runs**
```python
# scripts/reset_stuck_runs.py

import pandas as pd
from datetime import datetime, timedelta

df = pd.read_csv('results/experiments.csv')

# Find runs stuck in 'running' for >1 hour
stuck_mask = (df['status'] == 'running')
if 'actual_start_time' in df.columns:
    df['start_time_parsed'] = pd.to_datetime(df['actual_start_time'])
    now = datetime.now()
    stuck_mask &= (now - df['start_time_parsed'] > timedelta(hours=1))

stuck_count = stuck_mask.sum()
print(f"Resetting {stuck_count} stuck runs to 'pending'")

df.loc[stuck_mask, 'status'] = 'pending'
df.loc[stuck_mask, 'actual_start_time'] = None
df.loc[stuck_mask, 'actual_end_time'] = None

df.to_csv('results/experiments.csv', index=False)
print(f"✓ Reset complete. Run 'python orchestrator.py run' to continue.")
```

---

### **Script 2: Reset Failed Runs**
```python
# scripts/reset_failed_runs.py

import pandas as pd
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--engine', help='Reset only this engine')
parser.add_argument('--reason', help='Reset only if error contains this')
args = parser.parse_args()

df = pd.read_csv('results/experiments.csv')

failed_mask = (df['status'] == 'failed')

if args.engine:
    failed_mask &= (df['engine'] == args.engine)

if args.reason:
    # Filter by error message (if you have an 'error' column)
    if 'error_message' in df.columns:
        failed_mask &= df['error_message'].str.contains(args.reason, na=False)

reset_count = failed_mask.sum()
print(f"Resetting {reset_count} failed runs to 'pending'")

df.loc[failed_mask, 'status'] = 'pending'
df.loc[failed_mask, 'actual_start_time'] = None
df.loc[failed_mask, 'actual_end_time'] = None

df.to_csv('results/experiments.csv', index=False)
print(f"✓ Reset complete.")
```

---

### **Script 3: Verify Data Integrity**
```python
# scripts/verify_data_integrity.py

import pandas as pd
import os

df = pd.read_csv('results/experiments.csv')

print("Data Integrity Check")
print("="*60)

# Check 1: Total runs
total = len(df)
expected = 1620
print(f"\n1. Total runs: {total} (expected: {expected})")
if total != expected:
    print(f"   ⚠️ WARNING: Row count mismatch!")

# Check 2: Duplicate run_ids
duplicates = df['run_id'].duplicated().sum()
print(f"\n2. Duplicate run_ids: {duplicates}")
if duplicates > 0:
    print(f"   ❌ ERROR: Found {duplicates} duplicate run IDs!")

# Check 3: Completed runs have output files
completed_df = df[df['status'] == 'completed']
missing_outputs = 0
for idx, row in completed_df.iterrows():
    if 'output_file' in row and pd.notna(row['output_file']):
        if not os.path.exists(row['output_file']):
            missing_outputs += 1

print(f"\n3. Missing output files: {missing_outputs}/{len(completed_df)}")
if missing_outputs > 0:
    print(f"   ⚠️ WARNING: {missing_outputs} completed runs missing outputs!")

# Check 4: Status distribution
print(f"\n4. Status distribution:")
print(df['status'].value_counts())

print("\n" + "="*60)
if duplicates == 0 and missing_outputs == 0:
    print("✓ Data integrity OK")
else:
    print("⚠️ Issues found - review above")
```

---

## Restart Decision Tree

```
Did the run crash?
│
├─ YES → Check experiments.csv status
│         │
│         ├─ Many 'failed' → Which engine?
│         │                  └─ Reset that engine, check API key
│         │
│         ├─ Many 'running' → How long stuck?
│         │                   └─ Reset stuck runs
│         │
│         └─ All 'pending' → Just restart (nothing lost)
│
└─ NO → Run is still active
         └─ Use 'tail -f logs/*.log' to monitor
```

---

## Prevention Best Practices

### **1. Run in Screen or Tmux Session**
```bash
# Start screen session
screen -S llm_experiment

# Run experiment
python orchestrator.py run

# Detach: Ctrl+A, then D
# Reattach: screen -r llm_experiment
```

**Why**: If SSH disconnects, experiment keeps running

---

### **2. Enable Auto-Restart on Failure**
```bash
# Create restart wrapper
cat > run_with_retry.sh << 'EOF'
#!/bin/bash
MAX_RETRIES=3
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    python orchestrator.py run
    EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ]; then
        echo "✓ Experiment completed successfully"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo "⚠️ Attempt $RETRY_COUNT failed, retrying in 60s..."
        sleep 60
    fi
done
EOF

chmod +x run_with_retry.sh
./run_with_retry.sh
```

---

### **3. Set Up Monitoring Alerts**
```bash
# Send email if failure rate >5%
python scripts/monitor_and_alert.py --email your@email.com --threshold 5
```

---

### **4. Checkpoint Progress**
```bash
# Save backup every hour
while true; do
    cp results/experiments.csv results/experiments_backup_$(date +%Y%m%d_%H%M).csv
    sleep 3600
done &
```

---

## Emergency Contact Plan

**If you can't resolve the issue**:

1. **Save current state**:
   ```bash
   tar -czf emergency_backup_$(date +%Y%m%d_%H%M).tar.gz \
       results/experiments.csv \
       outputs/ \
       logs/
   ```

2. **Document what happened**:
   - What were you doing when it crashed?
   - What error message appeared?
   - How many runs completed?

3. **Check logs**:
   ```bash
   tail -100 logs/experimental_run.log > crash_log.txt
   ```

4. **Contact team** with:
   - `experiments.csv` current state
   - Last 100 lines of log
   - Error message screenshot

---

## Quick Recovery Checklist

When experiment crashes:

- [ ] Don't panic - progress is saved in experiments.csv
- [ ] Check completion count: `python -c "import pandas as pd; print((pd.read_csv('results/experiments.csv')['status']=='completed').sum())"`
- [ ] Check for stuck runs: `python scripts/reset_stuck_runs.py`
- [ ] Check for failed runs: `python scripts/reset_failed_runs.py`
- [ ] Verify data integrity: `python scripts/verify_data_integrity.py`
- [ ] Check API keys: `python scripts/test_api_keys.py`
- [ ] Check disk space: `df -h`
- [ ] Restart: `python orchestrator.py run`
- [ ] Monitor: `tail -f logs/experimental_run.log`

---

## Success Criteria for Recovery

After recovery, verify:
- ✓ experiments.csv has no duplicates
- ✓ No runs stuck in 'running' status
- ✓ Completed runs have output files
- ✓ New runs are executing
- ✓ Failure rate returns to <2%

---

## Key Principle

**The system is designed to be restartable**:
- Progress is saved after every run
- Restarting just continues from where it stopped
- No data is lost unless files are deleted
- You can restart as many times as needed

**Bottom line**: If it crashes, just reset stuck/failed runs and restart. The system will pick up automatically.
