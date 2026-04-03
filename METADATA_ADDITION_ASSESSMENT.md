# Metadata Addition Assessment - Complete Analysis

**Date**: 2026-03-31
**Status**: Assessment complete, ready for implementation plan
**Risk**: LOW (if done correctly)

---

## Executive Summary

We need to add **13 missing metadata fields** to track errors, performance, and quality metrics. This assessment identifies exactly where changes are needed without breaking the existing workflow.

**Critical constraint**: Matrix is already generated (1,620 rows). We CANNOT regenerate. All changes must be backward-compatible.

---

## Missing Fields to Add

### Priority 1: Error Tracking (5 fields)
1. `retry_count` - int - How many API retries happened (0 = first try success)
2. `error_type` - str - Classification: rate_limit, timeout, content_filter, api_error, none
3. `error_message` - text - Full error text if failed (empty if success)
4. `api_response_code` - int - HTTP status (200, 429, 500, etc.)
5. `content_filter_triggered` - bool - Safety filter blocked output?

### Priority 2: Performance Metrics (3 fields)
6. `api_latency_ms` - int - Time from request to first response (network + queue)
7. `tokens_per_second` - float - Generation speed (can compute from existing data)
8. `scheduled_vs_actual_delay_sec` - float - Scheduled time vs actual start time

### Priority 3: Quality Indicators (3 fields)
9. `prompt_hash` - str - SHA256 of rendered prompt (detect template changes)
10. `output_length_chars` - int - Character count (can compute post-hoc)
11. `output_word_count` - int - Word count (can compute post-hoc)

### Can Compute Later (2 fields)
12. `scheduled_time_numeric` - float - Hours since experiment start (compute from scheduled_datetime)
13. `randomization_seed_scheduling` - int - We have matrix_randomization_seed=42 (redundant)

---

## Current Workflow (MUST NOT BREAK)

### Phase 1: Matrix Generation (ALREADY DONE)
```
scripts/test_randomizer_stratified.py --seed 42
  ↓
results/experiments.csv (1,620 rows, status='pending')
```

**Columns set**: run_id, product_id, material_type, engine, temperature, time_of_day_label, scheduled_datetime, matrix_randomization_seed, matrix_randomization_mode

**New columns**: EMPTY (NULL/default values)

### Phase 2: Execution (UPCOMING)
```
orchestrator.py run --time-of-day morning
  ↓
runner/run_job.py:run_single_job()
  ↓
runner/engines/{engine}_client.py:call_{engine}()
  ↓
Update CSV row: tokens, timestamps, model, status='completed'
```

**Current flow**:
1. Read row from CSV (status='pending')
2. Load product YAML
3. Render prompt → save to outputs/prompts/{run_id}.txt
4. Call LLM API → capture response
5. Save output → outputs/{run_id}.txt
6. Update CSV row with metadata
7. Move to next row

**Critical points where we capture metadata**:
- Before API call: started_at
- During API call: retry logic, errors
- After API call: completed_at, tokens, model version
- From response: output_text, finish_reason

---

## File-by-File Analysis

### 1. runner/generate_matrix.py (480 lines)

**Purpose**: Generate initial CSV matrix with all runs

**Current column creation**: Lines ~200-250 (estimated)
- Creates CSV with headers
- Writes 1,620 rows with immutable columns
- Sets all runtime columns to empty/NULL

**Changes needed**:
- Add 13 new column headers to CSV generation
- Set default values for new columns:
  - retry_count: 0
  - error_type: "" (empty)
  - error_message: "" (empty)
  - api_response_code: 0
  - content_filter_triggered: False
  - api_latency_ms: 0
  - tokens_per_second: 0.0
  - scheduled_vs_actual_delay_sec: 0.0
  - prompt_hash: "" (compute during execution)
  - output_length_chars: 0
  - output_word_count: 0

**Risk**: LOW - Just adding columns with defaults

**Files to modify**:
- `runner/generate_matrix.py` - Add column headers

---

### 2. runner/run_job.py (346 lines)

**Purpose**: Execute single LLM run and return metadata

**Current function**: `run_single_job()` (lines 55-128)
- Loads product, renders prompt, calls engine
- Returns dict with metadata for CSV update

**Current return dict** (lines 115-128):
```python
return {
    "status": "completed",
    "started_at": started_at,
    "completed_at": completed_at,
    "date_of_run": date_of_run,
    "execution_duration_sec": execution_duration_sec,
    "session_id": session_id or "",
    "model": response.get("model", ""),
    "model_version": response.get("model_version", ""),
    "prompt_tokens": response.get("prompt_tokens", 0),
    "completion_tokens": response.get("completion_tokens", 0),
    "total_tokens": response.get("total_tokens", 0),
    "finish_reason": response.get("finish_reason", ""),
}
```

**Changes needed**:

1. **Compute prompt_hash** (after line 86):
   ```python
   import hashlib
   prompt_hash = hashlib.sha256(prompt_text.encode()).hexdigest()[:16]
   ```

2. **Compute scheduled_vs_actual_delay** (needs scheduled_datetime from CSV row):
   - Add `scheduled_datetime` parameter to function
   - Compute: actual_start - scheduled_datetime

3. **Extract new fields from engine response**:
   - retry_count
   - error_type
   - error_message
   - api_response_code
   - content_filter_triggered
   - api_latency_ms

4. **Compute quality metrics** (after line 112):
   ```python
   output_length_chars = len(response["output_text"])
   output_word_count = len(response["output_text"].split())
   tokens_per_second = completion_tokens / execution_duration_sec if execution_duration_sec > 0 else 0.0
   ```

5. **Add to return dict** (lines 115-128):
   ```python
   return {
       # ... existing fields ...
       "retry_count": response.get("retry_count", 0),
       "error_type": response.get("error_type", "none"),
       "error_message": response.get("error_message", ""),
       "api_response_code": response.get("api_response_code", 200),
       "content_filter_triggered": response.get("content_filter_triggered", False),
       "api_latency_ms": response.get("api_latency_ms", 0),
       "tokens_per_second": tokens_per_second,
       "scheduled_vs_actual_delay_sec": scheduled_vs_actual_delay_sec,
       "prompt_hash": prompt_hash,
       "output_length_chars": output_length_chars,
       "output_word_count": output_word_count,
   }
   ```

**Risk**: MEDIUM - Modifying execution logic, need to test carefully

**Files to modify**:
- `runner/run_job.py` - Add metadata computation and return fields

---

### 3. runner/engines/openai_client.py (146 lines)

**Purpose**: OpenAI API client with retry logic

**Current function**: `call_openai()` (lines 20-146)

**Current retry logic** (lines 76-146):
- Try up to `max_retries` times
- Catches: RateLimitError, APITimeoutError, APIError
- Returns dict with: output_text, finish_reason, tokens, model

**Current return dict** (lines 111-119):
```python
return {
    "output_text": message.content or "",
    "finish_reason": response.choices[0].finish_reason,
    "prompt_tokens": usage.prompt_tokens,
    "completion_tokens": usage.completion_tokens,
    "total_tokens": usage.total_tokens,
    "model": response.model,
    "model_version": response.model,
}
```

**Changes needed**:

1. **Track retry count**:
   - Initialize `retry_count = 0` before loop
   - Increment on each retry: `retry_count += 1`

2. **Measure API latency**:
   ```python
   import time
   api_start = time.time()
   response = client.chat.completions.create(**params)
   api_latency_ms = int((time.time() - api_start) * 1000)
   ```

3. **Capture errors**:
   ```python
   except RateLimitError as e:
       error_type = "rate_limit"
       error_message = str(e)
       api_response_code = 429
       retry_count += 1
       # ... retry logic ...

   except APITimeoutError as e:
       error_type = "timeout"
       error_message = str(e)
       api_response_code = 408
       retry_count += 1
       # ... retry logic ...
   ```

4. **Check content filter** (OpenAI-specific):
   ```python
   content_filter_triggered = (
       response.choices[0].finish_reason == "content_filter"
   )
   ```

5. **Add to return dict**:
   ```python
   return {
       # ... existing fields ...
       "retry_count": retry_count,
       "error_type": "none",
       "error_message": "",
       "api_response_code": 200,
       "content_filter_triggered": content_filter_triggered,
       "api_latency_ms": api_latency_ms,
   }
   ```

**Risk**: MEDIUM - Modifying error handling, need to preserve existing retry behavior

**Files to modify**:
- `runner/engines/openai_client.py`
- `runner/engines/google_client.py` (similar changes)
- `runner/engines/mistral_client.py` (similar changes)

---

### 4. runner/utils.py (266 lines)

**Purpose**: CSV utilities (update_csv_row, append_row)

**Function**: `update_csv_row()` - Updates specific CSV row

**Changes needed**:
- Should work automatically (writes all dict keys to CSV)
- VERIFY: Handles new columns gracefully

**Risk**: LOW - Utility function, should be flexible

**Files to check**:
- `runner/utils.py` - Verify update_csv_row handles new columns

---

## Implementation Strategy

### Step 1: Add Columns to Matrix Generation (SAFE)

**File**: `runner/generate_matrix.py`

**Action**: Add 13 new column headers with default values

**When to run**: NOT NOW (matrix already generated)

**Workaround for existing matrix**:
1. Add columns to CSV header row
2. Fill all 1,620 rows with default values
3. Script: `scripts/add_metadata_columns.py`

**Risk**: LOW - Just adding empty columns

---

### Step 2: Modify Engine Clients (MODERATE RISK)

**Files**:
- `runner/engines/openai_client.py`
- `runner/engines/google_client.py`
- `runner/engines/mistral_client.py`

**Action**: Track retry_count, error_type, api_latency_ms, content_filter_triggered

**Testing**:
1. Test with mock API (simulate errors)
2. Test with real API (1 run each engine)
3. Verify error handling still works

**Risk**: MEDIUM - Error handling is critical

---

### Step 3: Modify run_job.py (MODERATE RISK)

**File**: `runner/run_job.py`

**Action**: Compute prompt_hash, output_length_chars, tokens_per_second, scheduled_vs_actual_delay

**Testing**:
1. Test single run
2. Verify CSV update includes new fields
3. Check backward compatibility (existing columns unchanged)

**Risk**: MEDIUM - Main execution logic

---

### Step 4: Backward Compatibility for Existing Matrix (CRITICAL)

**Problem**: Matrix already has 36 columns, we're adding 13 more

**Solution**: Add columns to existing CSV

**Script**: `scripts/add_metadata_columns.py`

**Actions**:
1. Read existing experiments.csv
2. Add 13 new columns with default values
3. Write back to experiments.csv
4. Backup original to experiments_backup.csv

**Risk**: LOW - Simple CSV manipulation

---

## Testing Plan

### Test 1: Add Columns to Existing Matrix
```bash
# Backup current matrix
cp results/experiments.csv results/experiments_backup_2026-03-31.csv

# Run column addition script
python scripts/add_metadata_columns.py

# Verify
python -c "
import pandas as pd
df = pd.read_csv('results/experiments.csv')
print(f'Columns: {len(df.columns)}')  # Should be 49 (36 + 13)
print('New columns:', [c for c in df.columns if c in [
    'retry_count', 'error_type', 'api_latency_ms', 'prompt_hash'
]])
"
```

### Test 2: Single Run with New Metadata
```bash
# Test OpenAI
python orchestrator.py run --time-of-day morning --engine openai --max-jobs 1

# Check CSV for new fields
python -c "
import pandas as pd
df = pd.read_csv('results/experiments.csv')
completed = df[df.status == 'completed'].iloc[0]
print(f'retry_count: {completed.retry_count}')
print(f'api_latency_ms: {completed.api_latency_ms}')
print(f'prompt_hash: {completed.prompt_hash}')
print(f'output_length_chars: {completed.output_length_chars}')
"
```

### Test 3: Error Handling (Simulate Rate Limit)
```bash
# Temporarily set wrong API key to trigger error
export OPENAI_API_KEY="invalid_key_test"

# Run single job (should fail gracefully)
python orchestrator.py run --time-of-day morning --engine openai --max-jobs 1

# Check error tracking
python -c "
import pandas as pd
df = pd.read_csv('results/experiments.csv')
failed = df[df.status == 'failed'].iloc[0]
print(f'error_type: {failed.error_type}')
print(f'error_message: {failed.error_message}')
print(f'retry_count: {failed.retry_count}')
"
```

---

## Risks and Mitigation

### Risk 1: Breaking Existing Workflow
**Likelihood**: LOW
**Impact**: HIGH
**Mitigation**:
- Test with single run before batch
- Backup CSV before changes
- Keep original matrix as experiments_backup.csv

### Risk 2: CSV Column Mismatch
**Likelihood**: MEDIUM
**Impact**: MEDIUM
**Mitigation**:
- Verify update_csv_row() handles new columns
- Test with pandas to ensure column alignment
- Use DictWriter (preserves column order)

### Risk 3: Engine Client Errors Not Captured
**Likelihood**: LOW
**Impact**: MEDIUM
**Mitigation**:
- Test all 3 engines (OpenAI, Google, Mistral)
- Simulate errors (rate limit, timeout, API error)
- Verify retry logic still works

### Risk 4: Performance Degradation
**Likelihood**: LOW
**Impact**: LOW
**Mitigation**:
- New fields are simple computations (hash, len(), split())
- No network calls added
- Latency measurement is low overhead (time.time())

---

## Files to Modify (Summary)

### Core Files (4):
1. `runner/generate_matrix.py` - Add column headers
2. `runner/run_job.py` - Compute new metadata
3. `runner/engines/openai_client.py` - Track errors/latency
4. `runner/engines/google_client.py` - Track errors/latency
5. `runner/engines/mistral_client.py` - Track errors/latency

### Utility Scripts (2):
1. `scripts/add_metadata_columns.py` - NEW - Add columns to existing matrix
2. `scripts/test_metadata_tracking.py` - NEW - Test new fields

### Total Lines to Modify: ~200-300 lines across 5 files

---

## Implementation Order

1. **Write add_metadata_columns.py** (add columns to existing CSV)
2. **Test column addition** (verify CSV structure)
3. **Modify engine clients** (openai_client.py, google_client.py, mistral_client.py)
4. **Modify run_job.py** (compute new fields)
5. **Test single run** (verify metadata captured)
6. **Test error handling** (simulate failures)
7. **Run full validation** (ensure workflow intact)

---

## Approval Checklist

Before implementation:
- [ ] Backup current matrix: `results/experiments_backup_2026-03-31.csv`
- [ ] Review all file modifications
- [ ] Write test scripts
- [ ] Verify no breaking changes to workflow
- [ ] Test single run before batch
- [ ] Validate R statistical script still works

---

## Next Step

Awaiting decision:
1. **Proceed with implementation** (I'll create detailed plan + scripts)
2. **Modify approach** (change which fields to track)
3. **Defer** (keep current 36 columns, compute metrics post-hoc)

**Recommendation**: Proceed with implementation. These fields are valuable for error analysis and quality control. Risk is manageable with proper testing.
