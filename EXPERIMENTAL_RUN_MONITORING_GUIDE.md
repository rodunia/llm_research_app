# Experimental Run Monitoring Guide

**Date**: 2026-03-26
**Purpose**: What data to monitor during the 1,620-run experimental execution
**Randomization**: Frozen in commit `9d16713`

---

## Executive Summary

During the experimental run (executing all 1,620 LLM calls), you should monitor:

1. **Real-time progress**: Runs completed, success/failure rate
2. **API health**: Response times, rate limits, errors
3. **Data quality**: Token counts, output completeness
4. **Balance verification**: Actual vs planned distribution
5. **Cost tracking**: API usage and expenses

---

## 1. Primary Data Source: `results/experiments.csv`

This is your **single source of truth** for all experimental data.

### Key Columns to Monitor:

#### **A. Run Identification**
```csv
run_id                 - Unique identifier for each run
product_id             - Which product (smartphone/crypto/supplement)
material_type          - Which material (faq/digital_ad/blog/social/email)
engine                 - Which LLM (openai/google/mistral)
temperature            - Temperature setting (0.2/0.6/1.0)
```

#### **B. Scheduling Data (from randomizer)**
```csv
scheduled_date         - Planned execution date (2026-03-17 to 2026-03-23)
scheduled_day_of_week  - Day name (Monday-Sunday)
scheduled_time_slot    - Time slot (morning/afternoon/evening)
hour                   - Planned hour (7-22)
scheduled_timestamp    - Exact planned execution time
```

#### **C. Execution Status** ⚠️ **CRITICAL TO MONITOR**
```csv
status                 - Current state: pending/running/completed/failed
actual_start_time      - When execution actually started
actual_end_time        - When execution actually finished
```

**What to watch**:
- ✅ `status = 'completed'` → Success
- ❌ `status = 'failed'` → Error (investigate immediately)
- ⏳ `status = 'running'` → Currently executing
- ⏸️  `status = 'pending'` → Not yet started

#### **D. API Response Metadata**
```csv
model                  - Actual model used (gpt-4o-mini/gemini-1.5-flash/etc)
prompt_tokens          - Input tokens consumed
completion_tokens      - Output tokens consumed
total_tokens           - Sum of prompt + completion
finish_reason          - Why generation stopped (stop/length/error)
```

**What to watch**:
- `finish_reason = 'stop'` → Normal completion ✅
- `finish_reason = 'length'` → Hit max tokens (may be truncated) ⚠️
- `finish_reason = 'error'` → API error ❌
- Missing token counts → API didn't return metadata ⚠️

#### **E. Output Location**
```csv
output_file            - Path to generated text (outputs/{run_id}.txt)
prompt_file            - Path to prompt used (outputs/prompts/{run_id}.txt)
```

**What to watch**:
- Files exist → Data saved ✅
- Files missing → Write error ❌
- Empty files → Generation error ⚠️

---

## 2. Real-Time Monitoring Dashboard

### **A. Progress Tracking**

**Command** (run periodically):
```bash
python scripts/monitor_progress.py
```

**Expected output**:
```
===============================================
EXPERIMENTAL RUN PROGRESS
===============================================

Total runs:        1,620
Completed:         847 (52.3%)
Failed:            3 (0.2%)
Running:           1 (0.1%)
Pending:           769 (47.5%)

Estimated completion: 2026-03-23 21:45:00

Recent failures:
  - Run #456: OpenAI rate limit (retry scheduled)
  - Run #789: Google timeout (retry scheduled)
  - Run #1023: Mistral 503 error (retry scheduled)
```

### **B. Real-Time Status Check**

**Command**:
```bash
tail -f logs/experimental_run.log
```

**What to look for**:
```
✅ [2026-03-17 09:23:15] Run #47 completed (openai, smartphone_mid, faq)
⚠️  [2026-03-17 09:24:32] Run #48 rate limited (openai), retrying in 60s
✅ [2026-03-17 09:25:40] Run #49 completed (google, crypto, digital_ad)
❌ [2026-03-17 09:26:12] Run #50 FAILED (mistral, 500 error), marked for manual review
```

---

## 3. API Health Monitoring

### **A. Response Time Tracking**

**What to monitor**:
```python
# Calculate from experiments.csv
response_time = actual_end_time - actual_start_time
```

**Healthy ranges**:
- OpenAI GPT-4o-mini: 2-10 seconds
- Google Gemini: 3-15 seconds
- Mistral: 2-8 seconds

**Alerts**:
- ⚠️ > 30 seconds: Slow response (API degradation?)
- ❌ > 60 seconds: Timeout likely

### **B. Rate Limit Tracking**

**What to watch**:
- Errors with "rate_limit" in message
- 429 status codes
- Exponential backoff triggers

**Command**:
```bash
grep "rate_limit" logs/experimental_run.log | wc -l
```

**Expected**: < 5% of requests hit rate limits

### **C. Error Rate by Engine**

**Query experiments.csv**:
```python
import pandas as pd
df = pd.read_csv('results/experiments.csv')

# Error rate by engine
error_rate = df.groupby('engine')['status'].apply(
    lambda x: (x == 'failed').sum() / len(x) * 100
)
print(error_rate)
```

**Expected**:
- < 1% failure rate for all engines
- If any engine > 5% → Investigate API issues

---

## 4. Data Quality Checks

### **A. Token Count Validation**

**What to check**:
```python
# Load experiments.csv
df = pd.read_csv('results/experiments.csv')

# Check for missing token counts
missing_tokens = df[df['total_tokens'].isna()]
print(f"Missing token data: {len(missing_tokens)} runs")

# Check for unusually low/high token counts
low_tokens = df[df['completion_tokens'] < 50]  # Too short
high_tokens = df[df['completion_tokens'] > 2000]  # Too long

print(f"Unusually short outputs: {len(low_tokens)}")
print(f"Unusually long outputs: {len(high_tokens)}")
```

**Expected**:
- Missing tokens: 0% (all APIs should return this)
- Completion tokens: 200-800 (typical for marketing materials)
- < 5% outside normal range

### **B. Output File Integrity**

**Check**:
```bash
# Verify all output files exist
python scripts/verify_outputs.py
```

**What to check**:
```python
import os
df = pd.read_csv('results/experiments.csv')

# Check file existence
for idx, row in df[df['status'] == 'completed'].iterrows():
    output_path = row['output_file']
    if not os.path.exists(output_path):
        print(f"❌ Missing output: {row['run_id']}")
    elif os.path.getsize(output_path) == 0:
        print(f"⚠️ Empty output: {row['run_id']}")
```

**Expected**: 100% of completed runs have non-empty output files

### **C. Finish Reason Distribution**

**Query**:
```python
finish_reasons = df[df['status'] == 'completed']['finish_reason'].value_counts()
print(finish_reasons)
```

**Expected**:
```
stop      1580 (97.5%)  ✅ Normal completion
length      30 (1.9%)   ⚠️ Hit max tokens (acceptable)
error       10 (0.6%)   ❌ Errors (investigate)
```

---

## 5. Balance Verification

### **A. Verify Randomization Was Followed**

**Critical**: Check that actual execution matches planned schedule

**Query**:
```python
# Load experiments.csv
df = pd.read_csv('results/experiments.csv')

# Compare scheduled vs actual
df['actual_date'] = pd.to_datetime(df['actual_start_time']).dt.date
df['scheduled_date_parsed'] = pd.to_datetime(df['scheduled_date']).dt.date

# Check if runs executed on scheduled day
mismatched = df[df['actual_date'] != df['scheduled_date_parsed']]
print(f"Runs executed on wrong day: {len(mismatched)}")

# Acceptable: < 5% (due to late-night runs crossing midnight)
```

**Expected**: > 95% of runs execute on scheduled day

### **B. Actual Engine Distribution**

**Query**:
```python
# Check actual engine balance
actual_engine_dist = df[df['status'] == 'completed']['engine'].value_counts()
print(actual_engine_dist)
```

**Expected**:
```
openai:  ~540 (±10 if some failed)
google:  ~540 (±10 if some failed)
mistral: ~540 (±10 if some failed)
```

**Alert**: If any engine < 520 or > 560 → Imbalance occurred

### **C. Actual Time Slot Distribution**

**Query**:
```python
# Extract hour from actual_start_time
df['actual_hour'] = pd.to_datetime(df['actual_start_time']).dt.hour

# Categorize into time slots
def get_time_slot(hour):
    if 7 <= hour < 12:
        return 'morning'
    elif 12 <= hour < 17:
        return 'afternoon'
    elif 17 <= hour < 22:
        return 'evening'
    else:
        return 'other'

df['actual_time_slot'] = df['actual_hour'].apply(get_time_slot)

# Compare scheduled vs actual
actual_slot_dist = df[df['status'] == 'completed']['actual_time_slot'].value_counts()
scheduled_slot_dist = df[df['status'] == 'completed']['scheduled_time_slot'].value_counts()

print("Scheduled:", scheduled_slot_dist)
print("Actual:", actual_slot_dist)
```

**Expected**: > 95% match between scheduled and actual time slots

---

## 6. Cost Tracking

### **A. Real-Time Cost Calculation**

**Formula**:
```python
# OpenAI pricing (GPT-4o-mini)
OPENAI_INPUT_COST = 0.00015 / 1000   # $0.15 per 1M tokens
OPENAI_OUTPUT_COST = 0.0006 / 1000   # $0.60 per 1M tokens

# Google pricing (Gemini 1.5 Flash)
GOOGLE_INPUT_COST = 0.000075 / 1000  # $0.075 per 1M tokens
GOOGLE_OUTPUT_COST = 0.0003 / 1000   # $0.30 per 1M tokens

# Mistral pricing (mistral-large-2407)
MISTRAL_INPUT_COST = 0.003 / 1000    # $3 per 1M tokens
MISTRAL_OUTPUT_COST = 0.009 / 1000   # $9 per 1M tokens

def calculate_cost(row):
    engine = row['engine']
    prompt_tokens = row['prompt_tokens']
    completion_tokens = row['completion_tokens']

    if engine == 'openai':
        return (prompt_tokens * OPENAI_INPUT_COST +
                completion_tokens * OPENAI_OUTPUT_COST)
    elif engine == 'google':
        return (prompt_tokens * GOOGLE_INPUT_COST +
                completion_tokens * GOOGLE_OUTPUT_COST)
    elif engine == 'mistral':
        return (prompt_tokens * MISTRAL_INPUT_COST +
                completion_tokens * MISTRAL_OUTPUT_COST)

df['cost_usd'] = df.apply(calculate_cost, axis=1)
total_cost = df['cost_usd'].sum()
print(f"Total cost so far: ${total_cost:.2f}")
```

**Expected total cost** (1,620 runs):
- OpenAI (540 runs × $0.05): ~$27
- Google (540 runs × $0.03): ~$16
- Mistral (540 runs × $0.15): ~$81
- **Total: ~$124**

### **B. Cost Alerts**

**Set up alerts**:
```python
# Per-run cost thresholds
if df[df['engine'] == 'openai']['cost_usd'].max() > 0.20:
    print("⚠️ OpenAI cost spike detected")

if df[df['engine'] == 'mistral']['cost_usd'].max() > 0.50:
    print("⚠️ Mistral cost spike detected")
```

---

## 7. Critical Alerts (Stop Execution If...)

### 🚨 **STOP CONDITIONS** 🚨

Stop the experimental run immediately if:

1. **> 10% failure rate** for any engine
   - Indicates API outage or configuration error

2. **> 50 runs on wrong day**
   - Randomization schedule broken

3. **> 100 missing output files**
   - Storage or write permission issue

4. **Cost > $200**
   - Pricing changed or token counts miscalculated

5. **> 500 runs with finish_reason = 'error'**
   - Systematic prompt or API issue

### ⚠️ **WARNING CONDITIONS** ⚠️

Investigate (but don't stop) if:

1. **5-10% failure rate** for any engine
2. **10-50 runs on wrong day**
3. **10-100 missing outputs**
4. **Cost > $150**
5. **100-500 runs with errors**

---

## 8. Post-Run Validation Checklist

After all 1,620 runs complete, verify:

- [ ] Total completed runs = 1,620 (or 1,600+ if <20 failures)
- [ ] Engine distribution: 520-560 per engine
- [ ] Time slot distribution: 520-560 per slot
- [ ] All output files exist and non-empty
- [ ] Token counts present for all completed runs
- [ ] Total cost < $150
- [ ] No systematic bias in failures (check by engine/product/time)
- [ ] Actual vs scheduled time matches > 95%

---

## 9. Monitoring Scripts

### **A. Create Progress Monitor** (recommended)

```python
# scripts/monitor_experimental_run.py

import pandas as pd
from datetime import datetime

def print_progress():
    df = pd.read_csv('results/experiments.csv')

    total = len(df)
    completed = (df['status'] == 'completed').sum()
    failed = (df['status'] == 'failed').sum()
    running = (df['status'] == 'running').sum()
    pending = (df['status'] == 'pending').sum()

    print(f"\n{'='*60}")
    print(f"EXPERIMENTAL RUN PROGRESS - {datetime.now()}")
    print(f"{'='*60}")
    print(f"\nTotal:     {total:4d}")
    print(f"Completed: {completed:4d} ({completed/total*100:5.1f}%)")
    print(f"Failed:    {failed:4d} ({failed/total*100:5.1f}%)")
    print(f"Running:   {running:4d} ({running/total*100:5.1f}%)")
    print(f"Pending:   {pending:4d} ({pending/total*100:5.1f}%)")

    # Engine breakdown
    print(f"\n{'Engine':<10} {'Completed':<12} {'Failed':<8} {'Rate'}")
    print(f"{'-'*50}")
    for engine in ['openai', 'google', 'mistral']:
        eng_df = df[df['engine'] == engine]
        eng_completed = (eng_df['status'] == 'completed').sum()
        eng_failed = (eng_df['status'] == 'failed').sum()
        eng_rate = eng_completed / len(eng_df) * 100 if len(eng_df) > 0 else 0
        print(f"{engine:<10} {eng_completed:<12} {eng_failed:<8} {eng_rate:5.1f}%")

if __name__ == "__main__":
    print_progress()
```

**Run periodically**:
```bash
watch -n 60 python scripts/monitor_experimental_run.py
```

---

## 10. Data Files to Archive

After experimental run completes, archive:

1. **`results/experiments.csv`** - Complete run metadata
2. **`outputs/*.txt`** - All generated marketing materials (1,620 files)
3. **`outputs/prompts/*.txt`** - All prompts used (1,620 files)
4. **`logs/experimental_run.log`** - Execution log
5. **`results/randomizer_dry_run_2026-03-25.csv`** - Original randomization plan
6. **Cost report** - Final cost breakdown by engine

---

## Summary: What to Monitor

### **Real-Time (Every 15-30 min)**:
- [ ] Progress percentage
- [ ] Failure rate
- [ ] Recent errors

### **Hourly**:
- [ ] Engine distribution
- [ ] Time slot adherence
- [ ] Cost tracking

### **Daily**:
- [ ] Data quality checks
- [ ] Output file integrity
- [ ] Balance verification

### **Post-Run**:
- [ ] Complete validation checklist
- [ ] Archive all data
- [ ] Generate final report

---

**Key File**: `results/experiments.csv` is your single source of truth for all monitoring.
