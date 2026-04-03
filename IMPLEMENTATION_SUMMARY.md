# Implementation Summary - 5 Metadata Fields Added

**Date**: 2026-03-31
**Status**: ✅ PHASE 1 COMPLETE (CSV + OpenAI), PHASE 2 IN PROGRESS

---

## What's Been Done ✅

### 1. CSV Enhancement (COMPLETE)
- ✅ Backed up: `results/experiments_backup_2026-03-31_before_5_fields.csv`
- ✅ Added 5 columns to `results/experiments.csv`
- ✅ CSV now has 41 columns (was 36)
- ✅ All 1,620 rows have new fields with default values

**New columns**:
1. content_filter_triggered (bool, default: False)
2. prompt_hash (str, default: "")
3. retry_count (int, default: 0)
4. error_type (str, default: "")
5. scheduled_vs_actual_delay_sec (float, default: 0.0)

### 2. OpenAI Client (COMPLETE)
- ✅ Modified `runner/engines/openai_client.py`
- ✅ Tracks retry_count (increments on each retry attempt)
- ✅ Tracks error_type (rate_limit, timeout, api_error, none)
- ✅ Checks content_filter_triggered (finish_reason == "content_filter")
- ✅ Measures api_latency_ms (time.time() around API call)
- ✅ Returns 4 new fields in response dict
- ✅ Updated docstring

**Changes**:
- Lines 76-78: Added retry_count = 0, error_type = "none"
- Lines 102-105: Added API latency measurement
- Lines 111-114: Check content filter
- Lines 133-136: Return 4 new fields
- Lines 139-167: Increment retry_count and set error_type in exception handlers

---

## What Needs To Be Done ⏳

### 3. Google Client (PENDING)
**File**: `runner/engines/google_client.py`

**Needed changes** (same pattern as OpenAI):
```python
# At start of loop:
retry_count = 0
error_type = "none"

# Around API call:
api_start = time.time()
response = model.generate_content(...)
api_latency_ms = int((time.time() - api_start) * 1000)

# Check content filter (Google-specific):
content_filter_triggered = hasattr(response, 'prompt_feedback') and \
    response.prompt_feedback.block_reason != 0

# In return dict:
"retry_count": retry_count,
"error_type": error_type,
"content_filter_triggered": content_filter_triggered,
"api_latency_ms": api_latency_ms,

# In exception handlers:
except <GoogleAPIError>:
    retry_count += 1
    error_type = "..." # (rate_limit, timeout, api_error)
```

---

### 4. Mistral Client (PENDING)
**File**: `runner/engines/mistral_client.py`

**Needed changes** (same pattern):
- Add retry_count, error_type tracking
- Measure api_latency_ms
- Check content_filter_triggered (Mistral: check finish_reason or response status)
- Return 4 new fields
- Increment retry_count in exception handlers

---

### 5. run_job.py (PENDING)
**File**: `runner/run_job.py`

**Needed changes**:
```python
# In run_single_job() function:

# After rendering prompt (around line 86):
import hashlib
prompt_hash = hashlib.sha256(prompt_text.encode()).hexdigest()[:16]

# Before calling engine (need scheduled_datetime parameter):
def run_single_job(
    run_id: str,
    product_id: str,
    material_type: str,
    engine: str,
    temperature: float,
    scheduled_datetime: str = None,  # NEW parameter
    ...
):

# After start_time but before calling engine:
scheduled_vs_actual_delay_sec = 0.0
if scheduled_datetime:
    scheduled_dt = datetime.fromisoformat(scheduled_datetime.replace('Z', '+00:00'))
    scheduled_vs_actual_delay_sec = (start_time - scheduled_dt).total_seconds()

# In return dict (around line 115-128):
return {
    # ... existing fields ...
    "retry_count": response.get("retry_count", 0),
    "error_type": response.get("error_type", "none"),
    "content_filter_triggered": response.get("content_filter_triggered", False),
    "api_latency_ms": response.get("api_latency_ms", 0),
    "prompt_hash": prompt_hash,
    "scheduled_vs_actual_delay_sec": scheduled_vs_actual_delay_sec,
}
```

**Also need to update execute_job_record()** to pass scheduled_datetime from CSV row to run_single_job().

---

## Testing Plan ⏳

### Test 1: Verify CSV Structure
```bash
python -c "
import pandas as pd
df = pd.read_csv('results/experiments.csv')
print(f'Columns: {len(df.columns)} (expected: 41)')
required = ['content_filter_triggered', 'prompt_hash', 'retry_count',
            'error_type', 'scheduled_vs_actual_delay_sec']
missing = [c for c in required if c not in df.columns]
print(f'Missing: {missing if missing else \"None ✓\"}')"
```

### Test 2: Single OpenAI Run (After completing google/mistral/run_job)
```bash
# Pick first pending morning run
python -c "
import pandas as pd
df = pd.read_csv('results/experiments.csv')
morning_openai = df[(df.time_of_day_label=='morning') & (df.engine=='openai')].iloc[0]
print(f'Run ID: {morning_openai.run_id}')"

# Execute it
python orchestrator.py run --time-of-day morning --engine openai --max-jobs 1

# Check new fields
python -c "
import pandas as pd
df = pd.read_csv('results/experiments.csv')
completed = df[df.status=='completed'].iloc[0]
print(f'retry_count: {completed.retry_count}')
print(f'error_type: {completed.error_type}')
print(f'content_filter_triggered: {completed.content_filter_triggered}')
print(f'api_latency_ms: {completed.api_latency_ms}')
print(f'prompt_hash: {completed.prompt_hash}')
print(f'scheduled_vs_actual_delay_sec: {completed.scheduled_vs_actual_delay_sec}')"
```

### Test 3: All 3 Engines
```bash
# Run 1 from each engine
python orchestrator.py run --time-of-day morning --engine openai --max-jobs 1
python orchestrator.py run --time-of-day morning --engine google --max-jobs 1
python orchestrator.py run --time-of-day morning --engine mistral --max-jobs 1

# Verify all have metadata
python -c "
import pandas as pd
df = pd.read_csv('results/experiments.csv')
completed = df[df.status=='completed']
for engine in ['openai', 'google', 'mistral']:
    e_runs = completed[completed.engine==engine]
    if len(e_runs) > 0:
        r = e_runs.iloc[0]
        print(f'{engine}: retry={r.retry_count}, error={r.error_type}, latency={r.api_latency_ms}ms')"
```

### Test 4: R Statistical Validation
```bash
python scripts/prepare_matrix_for_r_stats.py
Rscript scripts/validate_matrix_r_stats.R
# Should still pass (new columns don't affect balance checks)
```

---

## Rollback Plan (If Needed)

```bash
# Restore original CSV
cp results/experiments_backup_2026-03-31_before_5_fields.csv results/experiments.csv

# Revert code changes
git checkout runner/engines/openai_client.py
git checkout runner/engines/google_client.py  # (if modified)
git checkout runner/engines/mistral_client.py  # (if modified)
git checkout runner/run_job.py  # (if modified)

# Verify restoration
python -c "
import pandas as pd
df = pd.read_csv('results/experiments.csv')
print(f'Columns: {len(df.columns)} (should be 36)')"
```

---

## Next Steps

1. ✅ DONE: Add 5 columns to CSV
2. ✅ DONE: Modify openai_client.py
3. ⏳ TODO: Modify google_client.py (same pattern as OpenAI)
4. ⏳ TODO: Modify mistral_client.py (same pattern as OpenAI)
5. ⏳ TODO: Modify run_job.py (compute prompt_hash, scheduled_delay)
6. ⏳ TODO: Test single run (each engine)
7. ⏳ TODO: Verify R stats script still works

**Estimated remaining time**: 1-1.5 hours

---

## Current State

**CSV**: ✅ Ready (41 columns, 1,620 rows)
**OpenAI**: ✅ Ready (tracks 4 metadata fields)
**Google**: ❌ Not modified yet
**Mistral**: ❌ Not modified yet
**run_job.py**: ❌ Not modified yet

**Can run experiments now?**: NO - need to finish google, mistral, run_job first

**Risk of breaking**: LOW - if tests pass, workflow will work correctly
