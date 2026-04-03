# Complete Testing Plan: 5 Metadata Fields

**Date**: 2026-03-31
**Fields to add**: content_filter_triggered, prompt_hash, retry_count, error_type, scheduled_vs_actual_delay_sec

---

## Critical Question: Will Adding Columns to CSV Solve Everything?

**Answer**: NO - Just adding columns is not enough. Here's why:

### What Needs to Happen (Complete Chain)

```
1. CSV has 5 new columns with default values
   ↓
2. Engine clients (openai_client.py) capture new metadata during API calls
   ↓
3. run_job.py receives new metadata from engine clients
   ↓
4. run_job.py returns dict with new fields
   ↓
5. update_csv_row() writes new fields to CSV
   ↓
6. CSV now has populated values (not empty defaults)
```

**EACH STEP MUST WORK** or the whole chain breaks.

---

## Data Flow Analysis

### Current Working Flow:

```python
# 1. Read job from CSV
job = {'run_id': 'abc123', 'product_id': 'smartphone_mid', 'engine': 'openai', ...}

# 2. Execute job
result = run_single_job(
    run_id='abc123',
    product_id='smartphone_mid',
    engine='openai',
    temperature=0.6,
    ...
)
# run_single_job() calls:
#   - render_prompt() → prompt_text
#   - call_engine() → response dict
#   - returns metadata dict

# 3. Update CSV
update_csv_row('abc123', result)  # result = {'status': 'completed', 'model': 'gpt-4o', ...}
```

### Key Insight from Code Analysis:

**Line 204 in run_job.py**:
```python
update_csv_row(run_id, result, csv_path)
```

This means `result` dict from `run_single_job()` is DIRECTLY written to CSV.

**Line 115-128 in run_job.py** (current return):
```python
return {
    "status": "completed",
    "started_at": started_at,
    "model": response.get("model", ""),
    ...
}
```

**SO**: If we add new fields to the return dict, `update_csv_row()` will write them to CSV.

### Critical Function: `update_csv_row()` (utils.py:85-123)

```python
def update_csv_row(run_id: str, updates: dict, path: str = "results/experiments.csv") -> bool:
    # Read all rows
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames  # ← Reads existing column names from CSV
        rows = list(reader)

    # Find and update the row
    for row in rows:
        if row.get("run_id") == run_id:
            row.update(updates)  # ← Updates dict with new values
            break

    # Write back all rows
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)  # ← Uses same fieldnames
        writer.writeheader()
        writer.writerows(rows)
```

**KEY OBSERVATION**:
- `fieldnames` is read from existing CSV header
- If CSV has 5 new columns, `DictWriter` will preserve them
- If `updates` dict has new fields NOT in `fieldnames`, they will be IGNORED

**CRITICAL**: New columns MUST exist in CSV BEFORE we try to write to them.

---

## What Could Go Wrong?

### Problem 1: Column Mismatch
**Scenario**: We add fields to engine response but forget to add columns to CSV

**Result**:
```python
# CSV has: run_id, product_id, engine, temperature, status
# updates dict has: status='completed', retry_count=2, prompt_hash='abc123'

# DictWriter ignores retry_count and prompt_hash (not in fieldnames)
# Only 'status' is written
```

**Solution**: Add columns to CSV FIRST, then modify code

---

### Problem 2: Field Name Typo
**Scenario**: CSV has `retry_count`, code returns `retries`

**Result**: Value never written (silent failure)

**Solution**: Use constants for field names

---

### Problem 3: Missing Field in Engine Response
**Scenario**: OpenAI client returns `retry_count`, Google client doesn't

**Result**: Google runs have empty `retry_count` in CSV

**Solution**: All 3 engine clients must return same fields with defaults

---

### Problem 4: Type Mismatch
**Scenario**: CSV expects int, code writes string

**Result**: CSV has `"2"` instead of `2`

**Solution**: Explicit type conversion in engine clients

---

### Problem 5: Existing Matrix Has Wrong Columns
**Scenario**: We regenerate matrix but forget to add new columns

**Result**: All new runs fail with column mismatch error

**Solution**: Script to add columns to existing CSV (backward compatibility)

---

## Complete Testing Strategy

### Phase 0: Preparation (BEFORE ANY CODE CHANGES)

#### Test 0.1: Backup Current State
```bash
# Backup current matrix
cp results/experiments.csv results/experiments_backup_2026-03-31_before_metadata.csv

# Verify backup
diff results/experiments.csv results/experiments_backup_2026-03-31_before_metadata.csv
# Should show no differences

# Count columns
head -1 results/experiments.csv | tr ',' '\n' | wc -l
# Current: 36 columns
```

#### Test 0.2: Document Current Column Order
```bash
# Save current columns
head -1 results/experiments.csv > /tmp/original_columns.txt

# Show all columns
cat /tmp/original_columns.txt | tr ',' '\n' | nl
```

---

### Phase 1: Add Columns to Existing CSV

#### Step 1.1: Create Column Addition Script

**File**: `scripts/add_5_metadata_columns.py`

```python
#!/usr/bin/env python3
"""Add 5 new metadata columns to existing experiments.csv"""

import pandas as pd
from pathlib import Path

def add_metadata_columns():
    csv_path = Path("results/experiments.csv")

    # Backup
    backup_path = Path("results/experiments_backup_before_columns.csv")
    import shutil
    shutil.copy(csv_path, backup_path)
    print(f"✓ Backed up to {backup_path}")

    # Read CSV
    df = pd.read_csv(csv_path)
    print(f"✓ Loaded {len(df)} rows, {len(df.columns)} columns")

    # Add 5 new columns with defaults
    new_columns = {
        'content_filter_triggered': False,
        'prompt_hash': '',
        'retry_count': 0,
        'error_type': '',
        'scheduled_vs_actual_delay_sec': 0.0
    }

    for col, default in new_columns.items():
        if col not in df.columns:
            df[col] = default
            print(f"✓ Added column: {col} (default: {default})")
        else:
            print(f"⚠ Column already exists: {col}")

    # Verify
    print(f"\n✓ New column count: {len(df.columns)}")
    print(f"✓ Expected: 41 (36 + 5)")

    if len(df.columns) != 41:
        print(f"✗ ERROR: Expected 41 columns, got {len(df.columns)}")
        return False

    # Save
    df.to_csv(csv_path, index=False)
    print(f"\n✓ Saved to {csv_path}")

    return True

if __name__ == "__main__":
    success = add_metadata_columns()
    exit(0 if success else 1)
```

#### Test 1.1: Add Columns
```bash
# Run script
python scripts/add_5_metadata_columns.py

# Expected output:
# ✓ Backed up to results/experiments_backup_before_columns.csv
# ✓ Loaded 1620 rows, 36 columns
# ✓ Added column: content_filter_triggered (default: False)
# ✓ Added column: prompt_hash (default: )
# ✓ Added column: retry_count (default: 0)
# ✓ Added column: error_type (default: )
# ✓ Added column: scheduled_vs_actual_delay_sec (default: 0.0)
# ✓ New column count: 41
# ✓ Expected: 41 (36 + 5)
# ✓ Saved to results/experiments.csv
```

#### Test 1.2: Verify CSV Structure
```bash
# Count columns
head -1 results/experiments.csv | tr ',' '\n' | wc -l
# Should show: 41

# Show new columns
head -1 results/experiments.csv | tr ',' '\n' | tail -5
# Should show:
# content_filter_triggered
# prompt_hash
# retry_count
# error_type
# scheduled_vs_actual_delay_sec

# Check a data row
head -2 results/experiments.csv | tail -1 | tr ',' '\n' | tail -5
# Should show:
# False
# (empty)
# 0
# (empty)
# 0.0
```

#### Test 1.3: Validate All Rows Have New Columns
```python
import pandas as pd
df = pd.read_csv('results/experiments.csv')

# Check all new columns exist
required_cols = ['content_filter_triggered', 'prompt_hash', 'retry_count',
                 'error_type', 'scheduled_vs_actual_delay_sec']
missing = [c for c in required_cols if c not in df.columns]
print(f"Missing columns: {missing if missing else 'None ✓'}")

# Check default values
print(f"content_filter_triggered all False: {(df.content_filter_triggered == False).all()}")
print(f"prompt_hash all empty: {(df.prompt_hash == '').all()}")
print(f"retry_count all 0: {(df.retry_count == 0).all()}")
print(f"error_type all empty: {(df.error_type == '').all()}")
print(f"scheduled_vs_actual_delay_sec all 0.0: {(df.scheduled_vs_actual_delay_sec == 0.0).all()}")
```

**STOP HERE IF ANY TEST FAILS** - CSV must be correct before code changes

---

### Phase 2: Modify Engine Clients (OpenAI First)

#### Step 2.1: Modify openai_client.py

**Changes**:
1. Track `retry_count` in loop
2. Measure `api_latency_ms`
3. Capture `error_type` on exceptions
4. Check `content_filter_triggered` from finish_reason
5. Return 5 new fields in response dict

**Modified function** (lines 76-146):
```python
def call_openai(...):
    # ... existing code ...

    retry_count = 0
    error_type = "none"

    for attempt in range(max_retries):
        try:
            logger.debug(f"Attempt {attempt+1}/{max_retries}")

            # Measure API latency
            import time
            api_start = time.time()

            response = client.chat.completions.create(**params)

            api_latency_ms = int((time.time() - api_start) * 1000)

            # Check content filter
            content_filter_triggered = (
                response.choices[0].finish_reason == "content_filter"
            )

            # Extract response data
            message = response.choices[0].message
            usage = response.usage

            logger.info(...)

            return {
                # Existing fields
                "output_text": message.content or "",
                "finish_reason": response.choices[0].finish_reason,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "model": response.model,
                "model_version": response.model,

                # NEW: 5 metadata fields
                "retry_count": retry_count,
                "error_type": error_type,
                "content_filter_triggered": content_filter_triggered,
                "api_latency_ms": api_latency_ms,
            }

        except RateLimitError as e:
            retry_count += 1
            error_type = "rate_limit"
            logger.warning(...)
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            # Last attempt failed - return error metadata
            return {
                "output_text": "",
                "finish_reason": "error",
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "model": "",
                "model_version": "",
                "retry_count": retry_count,
                "error_type": error_type,
                "content_filter_triggered": False,
                "api_latency_ms": 0,
            }

        except APITimeoutError as e:
            retry_count += 1
            error_type = "timeout"
            logger.warning(...)
            # ... similar error return ...
```

#### Test 2.1: Test OpenAI Client Directly
```python
# Test successful call
from runner.engines.openai_client import call_openai

response = call_openai(
    prompt="What is 2+2?",
    temperature=0.6,
    max_tokens=100
)

# Check new fields
print(f"retry_count: {response.get('retry_count')}")  # Should be 0
print(f"error_type: {response.get('error_type')}")  # Should be 'none'
print(f"content_filter_triggered: {response.get('content_filter_triggered')}")  # Should be False
print(f"api_latency_ms: {response.get('api_latency_ms')}")  # Should be > 0 (e.g., 1200)

# Verify all required fields present
required = ['retry_count', 'error_type', 'content_filter_triggered', 'api_latency_ms']
missing = [f for f in required if f not in response]
print(f"Missing fields: {missing if missing else 'None ✓'}")
```

#### Test 2.2: Test Error Handling (Simulate Rate Limit)
```python
# Temporarily break API key
import os
os.environ['OPENAI_API_KEY'] = 'invalid_key_for_testing'

try:
    response = call_openai(prompt="Test", temperature=0.6, max_tokens=100)
except Exception as e:
    print(f"Error (expected): {e}")
    # Should raise APIError after retries

# Restore API key
os.environ['OPENAI_API_KEY'] = 'your_real_key'
```

---

### Phase 3: Modify run_job.py

#### Step 3.1: Compute prompt_hash and scheduled_vs_actual_delay

**Changes to run_single_job()** (lines 55-128):
```python
def run_single_job(
    run_id: str,
    product_id: str,
    material_type: str,
    engine: str,
    temperature: float,
    scheduled_datetime: str = None,  # NEW parameter
    trap_flag: bool = False,
    ...
) -> Dict[str, Any]:
    # ... existing code ...

    # Render prompt (line 76-80)
    prompt_text = render_prompt(...)

    # NEW: Compute prompt hash
    import hashlib
    prompt_hash = hashlib.sha256(prompt_text.encode()).hexdigest()[:16]

    # Save prompt (line 82-86)
    prompt_path.write_text(prompt_text, encoding="utf-8")

    # Call engine (line 88-101)
    start_time = datetime.utcnow()
    started_at = start_time.isoformat() + 'Z'

    # NEW: Compute scheduled delay
    scheduled_vs_actual_delay_sec = 0.0
    if scheduled_datetime:
        scheduled_dt = datetime.fromisoformat(scheduled_datetime.replace('Z', '+00:00'))
        scheduled_vs_actual_delay_sec = (start_time - scheduled_dt).total_seconds()

    response = call_engine(...)

    # ... rest of existing code ...

    # Return metadata (line 115-128)
    return {
        # Existing fields
        "status": "completed",
        "started_at": started_at,
        ...,

        # NEW: Add 5 fields from engine response + prompt_hash + scheduled_delay
        "retry_count": response.get("retry_count", 0),
        "error_type": response.get("error_type", "none"),
        "content_filter_triggered": response.get("content_filter_triggered", False),
        "api_latency_ms": response.get("api_latency_ms", 0),
        "prompt_hash": prompt_hash,
        "scheduled_vs_actual_delay_sec": scheduled_vs_actual_delay_sec,
    }
```

#### Test 3.1: Test run_single_job() Directly
```python
from runner.run_job import run_single_job
from datetime import datetime, timedelta

# Test with scheduled_datetime
scheduled_dt = (datetime.utcnow() - timedelta(minutes=5)).isoformat() + 'Z'

result = run_single_job(
    run_id="test_run_12345",
    product_id="smartphone_mid",
    material_type="faq.j2",
    engine="openai",
    temperature=0.6,
    scheduled_datetime=scheduled_dt
)

# Check new fields
print(f"retry_count: {result.get('retry_count')}")
print(f"error_type: {result.get('error_type')}")
print(f"content_filter_triggered: {result.get('content_filter_triggered')}")
print(f"api_latency_ms: {result.get('api_latency_ms')}")
print(f"prompt_hash: {result.get('prompt_hash')}")
print(f"scheduled_vs_actual_delay_sec: {result.get('scheduled_vs_actual_delay_sec')}")
# Should show ~300 sec delay (5 minutes)
```

---

### Phase 4: Integration Test (End-to-End)

#### Test 4.1: Single Run Through Orchestrator
```bash
# Pick a specific run from CSV
python -c "
import pandas as pd
df = pd.read_csv('results/experiments.csv')
pending = df[df.status == 'pending'].iloc[0]
print(f'Run ID: {pending.run_id}')
print(f'Product: {pending.product_id}')
print(f'Engine: {pending.engine}')
print(f'Scheduled: {pending.scheduled_datetime}')
"

# Execute single run
python orchestrator.py run --time-of-day morning --engine openai --max-jobs 1

# Verify CSV was updated
python -c "
import pandas as pd
df = pd.read_csv('results/experiments.csv')
completed = df[df.status == 'completed'].iloc[0]

print('=== New Metadata Fields ===')
print(f'retry_count: {completed.retry_count}')
print(f'error_type: {completed.error_type}')
print(f'content_filter_triggered: {completed.content_filter_triggered}')
print(f'api_latency_ms: {completed.api_latency_ms}')
print(f'prompt_hash: {completed.prompt_hash}')
print(f'scheduled_vs_actual_delay_sec: {completed.scheduled_vs_actual_delay_sec}')

# Validate types
assert isinstance(completed.retry_count, (int, float))
assert isinstance(completed.error_type, str)
assert isinstance(completed.content_filter_triggered, bool)
assert isinstance(completed.api_latency_ms, (int, float))
assert isinstance(completed.prompt_hash, str)
assert isinstance(completed.scheduled_vs_actual_delay_sec, float)

print('\n✓ All fields have correct types')
"
```

#### Test 4.2: Test All 3 Engines
```bash
# OpenAI
python orchestrator.py run --time-of-day morning --engine openai --max-jobs 1

# Google
python orchestrator.py run --time-of-day morning --engine google --max-jobs 1

# Mistral
python orchestrator.py run --time-of-day morning --engine mistral --max-jobs 1

# Verify all have new fields
python -c "
import pandas as pd
df = pd.read_csv('results/experiments.csv')
completed = df[df.status == 'completed']

for engine in ['openai', 'google', 'mistral']:
    engine_runs = completed[completed.engine == engine]
    if len(engine_runs) > 0:
        run = engine_runs.iloc[0]
        print(f'\n{engine.upper()}:')
        print(f'  retry_count: {run.retry_count}')
        print(f'  error_type: {run.error_type}')
        print(f'  prompt_hash: {run.prompt_hash[:16]}...')
        print(f'  api_latency_ms: {run.api_latency_ms}')
"
```

#### Test 4.3: Verify Prompt Hash Consistency
```bash
# Run same product/material combination twice
# Prompt hash should be IDENTICAL (deterministic)

python -c "
import pandas as pd
df = pd.read_csv('results/experiments.csv')
completed = df[df.status == 'completed']

# Group by product+material
for (product, material), group in completed.groupby(['product_id', 'material_type']):
    hashes = group['prompt_hash'].unique()
    print(f'{product} × {material}: {len(hashes)} unique hash(es)')
    if len(hashes) == 1:
        print(f'  ✓ Consistent: {hashes[0][:16]}...')
    else:
        print(f'  ✗ INCONSISTENT: {hashes}')
"
```

---

### Phase 5: Backward Compatibility Test

#### Test 5.1: Verify Old Rows Still Work
```bash
# Check that rows with default values (0, '', False) still work
python -c "
import pandas as pd
df = pd.read_csv('results/experiments.csv')

# Pending rows should have default values
pending = df[df.status == 'pending']
print(f'Pending rows: {len(pending)}')
print(f'All have retry_count=0: {(pending.retry_count == 0).all()}')
print(f'All have error_type=\"\": {(pending.error_type == \"\").all()}')
print(f'All have content_filter_triggered=False: {(pending.content_filter_triggered == False).all()}')
"
```

#### Test 5.2: Verify R Statistical Script Still Works
```bash
# Run R validation (should still pass with 41 columns)
python scripts/prepare_matrix_for_r_stats.py
Rscript scripts/validate_matrix_r_stats.R

# Should show:
# ✓ MATRIX VALIDATION PASSED
```

---

### Phase 6: Error Simulation Tests

#### Test 6.1: Simulate Rate Limit Error
```python
# Manually trigger rate limit by rapid calls
import time
from runner.engines.openai_client import call_openai

for i in range(10):
    try:
        response = call_openai(prompt=f"Test {i}", temperature=0.6, max_tokens=10)
        print(f"Run {i}: retry_count={response['retry_count']}, error_type={response['error_type']}")
        time.sleep(0.1)  # Very short delay to trigger rate limit
    except Exception as e:
        print(f"Run {i}: FAILED - {e}")
```

#### Test 6.2: Verify Error Metadata Captured
```bash
# After simulating errors, check CSV
python -c "
import pandas as pd
df = pd.read_csv('results/experiments.csv')

# Show error distribution
print('Error types:')
print(df['error_type'].value_counts())

# Show retry counts
print('\nRetry count distribution:')
print(df['retry_count'].value_counts())

# Show runs with errors
errors = df[df.error_type != 'none']
if len(errors) > 0:
    print(f'\n{len(errors)} runs with errors:')
    print(errors[['run_id', 'engine', 'error_type', 'retry_count']])
"
```

---

## Test Checklist (Execute in Order)

### Phase 0: Preparation
- [ ] Backup current experiments.csv
- [ ] Document current 36 columns
- [ ] Verify CSV has 1,620 rows, all status='pending'

### Phase 1: Add Columns
- [ ] Write add_5_metadata_columns.py script
- [ ] Run script → verify exit code 0
- [ ] Check CSV has 41 columns (36 + 5)
- [ ] Verify new columns have default values
- [ ] Verify all 1,620 rows have new columns

### Phase 2: Engine Client (OpenAI)
- [ ] Modify openai_client.py
- [ ] Test call_openai() directly → verify 5 new fields in response
- [ ] Check retry_count=0, error_type='none' for successful call
- [ ] Check api_latency_ms > 0
- [ ] Simulate error → verify error_type captured

### Phase 3: run_job.py
- [ ] Modify run_single_job()
- [ ] Add scheduled_datetime parameter
- [ ] Compute prompt_hash
- [ ] Compute scheduled_vs_actual_delay_sec
- [ ] Add 5 fields to return dict
- [ ] Test run_single_job() directly

### Phase 4: Integration
- [ ] Run single job via orchestrator
- [ ] Verify CSV updated with 5 new fields
- [ ] Check field types (int, str, bool, float)
- [ ] Test all 3 engines (OpenAI, Google, Mistral)
- [ ] Verify prompt_hash consistency

### Phase 5: Backward Compatibility
- [ ] Verify pending rows have default values
- [ ] Run R statistical validation → should pass
- [ ] Check old validation scripts still work

### Phase 6: Error Handling
- [ ] Simulate rate limit error
- [ ] Verify error_type and retry_count captured
- [ ] Check CSV has error metadata

---

## Success Criteria

All these must be TRUE:

1. ✅ CSV has 41 columns (36 old + 5 new)
2. ✅ All 1,620 rows have new columns
3. ✅ Completed runs have populated values (not defaults)
4. ✅ prompt_hash is consistent for same product/material
5. ✅ retry_count = 0 for successful runs
6. ✅ error_type = 'none' for successful runs
7. ✅ content_filter_triggered = False (unless actually triggered)
8. ✅ api_latency_ms > 0 for completed runs
9. ✅ scheduled_vs_actual_delay_sec is reasonable (<600 sec)
10. ✅ R statistical validation still passes
11. ✅ All 3 engines work correctly
12. ✅ Error handling captures metadata

---

## Rollback Plan (If Tests Fail)

```bash
# Restore original CSV
cp results/experiments_backup_2026-03-31_before_metadata.csv results/experiments.csv

# Verify restoration
python -c "
import pandas as pd
df = pd.read_csv('results/experiments.csv')
print(f'Columns: {len(df.columns)}')  # Should be 36
print(f'Rows: {len(df)}')  # Should be 1,620
print(f'Status: {df.status.value_counts()}')  # All should be 'pending'
"

# Revert code changes
git checkout runner/engines/openai_client.py
git checkout runner/run_job.py
```

---

## Estimated Time

- Phase 0 (Preparation): 10 min
- Phase 1 (Add columns): 20 min
- Phase 2 (Engine client): 45 min
- Phase 3 (run_job.py): 30 min
- Phase 4 (Integration): 30 min
- Phase 5 (Backward compat): 15 min
- Phase 6 (Error handling): 20 min

**Total**: ~2.5-3 hours

---

## Answer to Your Question

**"Are you sure adding it to CSV would solve everything?"**

**NO** - Adding columns to CSV is only STEP 1 of 6.

**What solves everything**:
1. Add columns to CSV ✓
2. Modify engine clients to capture metadata ✓
3. Modify run_job.py to compute fields ✓
4. Ensure update_csv_row() writes new fields ✓
5. Test end-to-end ✓
6. Verify error handling ✓

**All 6 steps must work** for the system to function correctly.

This testing plan ensures we validate each step before moving to the next.
