# Experimental Run Monitoring - Quick Reference

**Randomization Frozen**: Commit `9d16713` (2026-03-26)
**CSV**: `results/randomizer_dry_run_2026-03-25.csv`

---

## What to Monitor During Experimental Run

### 📊 **PRIMARY DATA SOURCE**
**File**: `results/experiments.csv`

This single CSV tracks everything:
- Run status (pending/completed/failed)
- Execution timestamps
- Token counts
- API responses
- Output file paths

---

## ⚡ Quick Monitoring Commands

### 1. Check Progress
```bash
python scripts/monitor_experimental_run.py
```

### 2. Watch Real-Time Log
```bash
tail -f logs/experimental_run.log
```

### 3. Count Completed Runs
```bash
python -c "import pandas as pd; df = pd.read_csv('results/experiments.csv'); print(f'Completed: {(df.status==\"completed\").sum()}/1620')"
```

### 4. Check Failure Rate
```bash
python -c "import pandas as pd; df = pd.read_csv('results/experiments.csv'); print(f'Failed: {(df.status==\"failed\").sum()} ({(df.status==\"failed\").sum()/len(df)*100:.1f}%)')"
```

### 5. Engine Balance Check
```bash
python -c "import pandas as pd; df = pd.read_csv('results/experiments.csv'); print(df[df.status=='completed']['engine'].value_counts())"
```

---

## 🚨 Critical Alerts (STOP if...)

- ❌ **> 10% failure rate** for any engine
- ❌ **> 50 runs on wrong day**
- ❌ **> 100 missing output files**
- ❌ **Cost > $200**
- ❌ **> 500 runs with errors**

---

## ⚠️ Warning Conditions (Investigate)

- ⚠️ **5-10% failure rate**
- ⚠️ **10-50 runs on wrong day**
- ⚠️ **Cost > $150**
- ⚠️ **Slow API responses (> 30s)**

---

## 📋 Key Columns in experiments.csv

### Status Tracking
- `status`: pending/running/completed/failed
- `actual_start_time`: When run started
- `actual_end_time`: When run finished

### API Response
- `model`: Actual model used
- `prompt_tokens`: Input tokens
- `completion_tokens`: Output tokens
- `finish_reason`: stop/length/error

### Output Files
- `output_file`: Path to generated text
- `prompt_file`: Path to prompt used

### Randomization (should match plan)
- `scheduled_date`: Planned date
- `scheduled_time_slot`: morning/afternoon/evening
- `engine`: openai/google/mistral

---

## 📊 Expected Distributions (1,620 runs)

### Time Slots
- Morning: 540 runs (108 calls/hour)
- Afternoon: 540 runs (108 calls/hour)
- Evening: 540 runs (108 calls/hour)

### Engines
- OpenAI: 540 runs
- Google: 540 runs
- Mistral: 540 runs

### Days
- Each day: 231-232 runs

---

## 💰 Expected Costs

- **OpenAI**: ~$27 (540 runs × ~$0.05)
- **Google**: ~$16 (540 runs × ~$0.03)
- **Mistral**: ~$81 (540 runs × ~$0.15)
- **TOTAL**: ~$124

---

## ✅ Post-Run Validation Checklist

- [ ] Completed runs ≥ 1,600 (< 20 failures acceptable)
- [ ] Engine distribution: 520-560 per engine
- [ ] Time slot distribution: 520-560 per slot
- [ ] All output files exist and non-empty
- [ ] Token counts present for all runs
- [ ] Total cost < $150
- [ ] > 95% runs on scheduled day
- [ ] Failure rate < 2% per engine

---

## 📁 Files to Archive After Run

1. `results/experiments.csv` - Complete metadata
2. `outputs/*.txt` - Generated materials (1,620 files)
3. `outputs/prompts/*.txt` - Prompts (1,620 files)
4. `logs/experimental_run.log` - Execution log
5. `results/randomizer_dry_run_2026-03-25.csv` - Original plan

---

## 📖 Full Documentation

See `EXPERIMENTAL_RUN_MONITORING_GUIDE.md` for complete details.
