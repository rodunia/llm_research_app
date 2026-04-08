# Temporal Execution Guide

## Overview

This experiment uses **stratified 7-day temporal design** with 1,620 runs scheduled across:
- **7 days** (March 17-23, 2026)
- **3 time slots per day** (morning, afternoon, evening)
- **21 time windows total** (~77 runs per window)

The temporal design is critical for testing **RQ3: Temporal Unreliability** - whether LLMs produce inconsistent outputs across different sessions and times of day.

---

## Execution Options

### Option A: SCHEDULED EXECUTION ✅ Recommended

**Preserves temporal validity** by executing runs at their scheduled times over 7 days.

#### Automated Scheduling (Recommended)

Start the orchestrator scheduler to run experiments automatically:

```bash
# Activate environment
source .venv/bin/activate

# Start scheduler (runs in background)
python orchestrator.py schedule
```

**Schedule:**
- **Morning:** 8:00 AM CET (daily) - executes 540 "morning" runs over 7 days
- **Afternoon:** 3:00 PM CET (daily) - executes 540 "afternoon" runs over 7 days
- **Evening:** 9:00 PM CET (daily) - executes 540 "evening" runs over 7 days

**How it works:**
1. Scheduler triggers at configured times (8:00, 15:00, 21:00 CET)
2. Orchestrator filters `experiments.csv` by `time_of_day_label`
3. Executes ~77 runs per session (one time slot per day)
4. Repeats across all 7 days
5. `scheduled_vs_actual_delay_sec` will be small (< 1 hour)

**To stop:** Press `Ctrl+C`

#### Manual Execution

Alternatively, trigger each time slot manually:

```bash
# Morning runs (8:00 AM CET)
python orchestrator.py run --time-of-day morning

# Afternoon runs (3:00 PM CET)
python orchestrator.py run --time-of-day afternoon

# Evening runs (9:00 PM CET)
python orchestrator.py run --time-of-day evening
```

Run these commands at the appropriate times each day for 7 days.

#### Pros
- ✅ **Full temporal validity** for RQ3 (temporal unreliability testing)
- ✅ **Small `scheduled_vs_actual_delay_sec`** (< 1 hour) - high data quality
- ✅ **Runs distributed across real 7-day window** - captures actual temporal variation
- ✅ **Time-of-day effects properly captured** - tests morning vs afternoon vs evening differences
- ✅ **Adheres to pre-registered protocol** - maintains research integrity

#### Cons
- ⏱ **Takes 7 days** to complete all 1,620 runs
- ⚠️ **Must keep orchestrator running** continuously (or remember to trigger manually)

---

### Option B: BATCH EXECUTION ⚠️ Not Recommended

**Ignores temporal design** by running all 1,620 experiments immediately in sequence.

```bash
source .venv/bin/activate
python runner/run_job.py batch --csv-path results/experiments.csv
```

#### Pros
- ✅ **Fastest completion** (~9.7 hours total)
- ✅ **No multi-day orchestration** needed
- ✅ **Simple execution** - single command

#### Cons
- ❌ **Large `scheduled_vs_actual_delay_sec`** (~17 days) - poor data quality
- ❌ **All runs execute at same actual time** - no temporal variation captured
- ❌ **Cannot test RQ3** temporal unreliability hypothesis
- ❌ **Violates pre-registered 7-day temporal design** - compromises research integrity

---

## Monitoring Progress

### Check experiment status:

```bash
python orchestrator.py status
```

### View progress during execution:

```bash
python -c "
import pandas as pd
df = pd.read_csv('results/experiments.csv')
completed = len(df[df['status']=='completed'])
pending = len(df[df['status']=='pending'])
failed = len(df[df['status']=='failed'])

print(f'Completed: {completed}/1620')
print(f'Pending: {pending}')
print(f'Failed: {failed}')

# Progress by time slot
print('\nBy time slot:')
for time in ['morning', 'afternoon', 'evening']:
    time_df = df[df['time_of_day_label'] == time]
    time_completed = len(time_df[time_df['status'] == 'completed'])
    print(f'  {time}: {time_completed}/540 completed')
"
```

---

## Technical Details

### How Orchestrator Filters by Time Slot

From `orchestrator.py:383-411` and `run_job.py:153-185`:

1. **Orchestrator** calls `runner/run_job.py batch --time-of-day morning`
2. **run_job.py** reads `experiments.csv` and filters rows where:
   - `status == 'pending'`
   - `time_of_day_label == 'morning'` (or afternoon/evening)
3. **Executes** filtered runs in sequence
4. **Updates** each row in `experiments.csv` with:
   - `status='completed'`
   - `scheduled_vs_actual_delay_sec` (computed from `scheduled_datetime`)
   - All Stage 1 metadata fields (6 fields)

### Scheduled vs Actual Delay Calculation

From `run_job.py:97-105`:

```python
scheduled_vs_actual_delay_sec = (actual_start_time - scheduled_datetime).total_seconds()
```

**Examples:**
- **Option A (scheduled):** Run scheduled for March 17, 8:00 AM, executed March 17, 8:05 AM
  - `scheduled_vs_actual_delay_sec = 300` (5 minutes)

- **Option B (batch):** Run scheduled for March 17, 8:00 AM, executed April 3, 2:00 PM
  - `scheduled_vs_actual_delay_sec = 1,468,800` (17 days)

---

## Recommendation

**Use Option A (Scheduled Execution)** to:

1. ✅ **Test RQ3 hypothesis** on temporal unreliability
2. ✅ **Preserve pre-registered experimental protocol** (stratified_7day_balanced)
3. ✅ **Collect high-quality temporal metadata** (`scheduled_vs_actual_delay_sec` < 1 hour)
4. ✅ **Capture genuine time-of-day effects** across 7-day window

The orchestrator scheduler automates this entire process - just run `python orchestrator.py schedule` and let it execute over 7 days.

---

## Crash Recovery

If the orchestrator crashes mid-execution:

```bash
# Restart scheduler - it will skip completed runs automatically
python orchestrator.py schedule
```

The scheduler is **idempotent** - it only executes runs where `status='pending'`, so you can safely restart it.

---

## After Completion

Once all 1,620 runs are complete, proceed to Glass Box audit:

```bash
# Run Glass Box audit on all completed runs
python analysis/glass_box_audit.py --limit 1620

# This will add 6 Stage 2 metadata fields to results/final_audit_results.csv
```

Total metadata: **12 fields** (6 from Stage 1 marketing generation + 6 from Stage 2 claim extraction)

---

## Execution Timeline

**Option A (Scheduled):**
- Day 1-7: Execute 3 sessions per day (morning/afternoon/evening)
- Total time: 7 days
- Sessions per day: ~3.2 hours per session (77 runs × 2.5 min/run)
- Daily time commitment: ~9.7 hours total across 3 sessions

**Option B (Batch):**
- Single execution: ~9.7 hours continuous
- Total time: 1 day
- ⚠️ **Not recommended** - violates temporal design
