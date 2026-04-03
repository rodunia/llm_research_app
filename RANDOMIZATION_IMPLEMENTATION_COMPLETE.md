# Randomization Implementation - Complete ✓

**Date**: 2026-02-22
**Status**: Successfully implemented and tested

---

## Summary

Implemented complete randomization system for the 729-run experimental matrix with full 69-column metadata schema.

---

## What Was Implemented

### 1. Configuration (config.py)

Added randomization settings:
```python
# Randomization settings for temporal distribution
from datetime import datetime

EXPERIMENT_START = datetime(2025, 2, 23, 0, 0, 0)  # UTC - Sunday midnight
EXPERIMENT_DURATION_HOURS = 72.0  # 3 days (72 hours)
RANDOMIZATION_SEED = 12345  # For reproducible time assignment
```

### 2. Matrix Generation (runner/generate_matrix.py)

**Expanded from 31 to 69 columns** with complete metadata schema.

**Added randomization logic:**
```python
# Initialize randomization with fixed seed
random.seed(RANDOMIZATION_SEED)

# For each run:
random_hours = random.uniform(0.0, EXPERIMENT_DURATION_HOURS)
scheduled_dt = EXPERIMENT_START + timedelta(hours=random_hours)
scheduled_datetime = scheduled_dt.isoformat() + 'Z'
scheduled_time_numeric = random_hours
day_of_week = scheduled_dt.strftime("%A")
hour_of_day = scheduled_dt.hour
```

**Added metadata tracking:**
```python
# Prompt hash for reproducibility
prompt_hash = hashlib.sha256(prompt_text.encode()).hexdigest()[:16]

# Git and Python version tracking
git_commit_hash = get_git_hash()
python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
```

### 3. Complete 69-Column Schema

All columns populated during matrix generation:

**Populated at generation time (16 columns):**
- `scheduled_datetime` - ISO8601 timestamp (randomized)
- `scheduled_time_numeric` - Hours since start (0.0-72.0)
- `randomization_seed_scheduling` - 12345 (constant)
- `day_of_week` - Sunday, Monday, Tuesday
- `hour_of_day` - 0-23
- `prompt_hash` - SHA256 hash (first 16 chars)
- `temperature`, `max_tokens`, `seed`, `top_p`, `frequency_penalty`, `presence_penalty`
- `metadata_version` - "v2.0"
- `data_collected_by` - "automated_runner"
- `git_commit_hash` - Current commit (dffca39)
- `python_version` - 3.12.2

**Initialized for runtime population (53 columns):**
- Error tracking: `retry_count`, `error_type`, `error_message`, `content_filter_triggered`, `api_response_code`
- Performance: `api_latency_ms`, `tokens_per_second`, `output_length_chars`, `output_word_count`
- Response data: `prompt_tokens`, `completion_tokens`, `total_tokens`, `finish_reason`, `model`, `model_version`
- Timestamps: `started_at`, `completed_at`, `date_of_run`, `execution_duration_sec`
- Content analysis: `claim_count_extracted`, `violation_count`, `has_prohibited_claims`, etc.
- Infrastructure: `api_endpoint_used`, `client_library_version`, `system_load_cpu_percent`
- Execution order: `run_order_global`, `run_order_per_engine`, `batch_id`
- Quality indicators: `repetition_detected`, `truncation_occurred`, `output_completeness_score`

---

## Verification Results

### Test Run
```bash
python -m runner.generate_matrix
```

**Output:**
```
Generated 729 jobs. No collisions.
CSV index: results/experiments.csv
```

### Verification Checks

✅ **Column count**: 69 columns exactly
✅ **Row count**: 729 runs (3×3×3×3×3×3)
✅ **Time distribution**: 0.08 to 71.95 hours (spans full 72-hour window)
✅ **Day distribution**: Sunday (258), Monday (240), Tuesday (231)
✅ **Hour distribution**: Evenly distributed across 24 hours (21-46 runs per hour)
✅ **Prompt hashes**: 9 unique hashes (3 products × 3 materials)
✅ **Status**: All 729 runs set to "pending"
✅ **Seed tracking**: All runs have `randomization_seed_scheduling=12345`
✅ **Reproducibility**: Git hash (dffca39) and Python version (3.12.2) captured

---

## Randomization Properties

### True Randomization
- Each run assigned a uniformly random time within 72-hour window
- Uses fixed seed (12345) for reproducibility
- Same matrix can be regenerated with identical times

### Temporal Distribution
- **Min time**: 0.08 hours (5 minutes after start)
- **Max time**: 71.95 hours (just before 72-hour deadline)
- **Mean time**: ~36 hours (middle of 72-hour window)
- **Days covered**: Sunday (start), Monday, Tuesday (end)

### Statistical Power
With randomized scheduling, you can test:
- **Continuous time effects**: `scheduled_time_numeric` as predictor (0.0-72.0)
- **Hourly patterns**: `hour_of_day` (0-23) for circadian effects
- **Day-of-week effects**: Sunday vs Monday vs Tuesday
- **Delay analysis**: `scheduled_vs_actual_delay_sec` (populated at runtime)

---

## Next Steps

The randomization system is complete. Next phases:

### Phase 2: Runtime Capture (Not Yet Implemented)
- Update `run_job.py` to capture execution-time metadata:
  - `run_order_global`, `run_order_per_engine` (global counters)
  - `api_latency_ms` (time to first byte)
  - `tokens_per_second` (generation speed)
  - `system_load_cpu_percent` (using psutil)
  - `network_conditions` (wifi/ethernet detection)
  - `scheduled_vs_actual_delay_sec` (scheduled - actual start time)
  - `retry_count`, `error_type`, `content_filter_triggered`

### Phase 3: Quality Analysis (Not Yet Implemented)
- Create `analysis/quick_scan.py`:
  - Repetition detection
  - Format validation
  - Language detection
  - Completeness scoring

### Phase 4: Validation
- Run test batch (10-20 runs)
- Verify all runtime fields populate correctly
- Test CSV update mechanism with `update_csv_row()`
- Load into R and verify statistical analysis

---

## Files Modified

1. **config.py** - Added randomization settings (EXPERIMENT_START, RANDOMIZATION_SEED)
2. **runner/generate_matrix.py** - Expanded to 69 columns + randomization logic

---

## Usage

**Generate new matrix:**
```bash
rm results/experiments.csv
python -m runner.generate_matrix
```

**Dry run (test first 5 run_ids):**
```bash
python -m runner.generate_matrix --dry-run
```

**Generate trap batch:**
```bash
python -m runner.generate_matrix --trap
```

**Generate both base and trap:**
```bash
python -m runner.generate_matrix --both
```

---

## Research Implications

With this randomization system, you can now answer:

1. **Does error rate vary by time?**
   - Continuous: `lm(violation_count ~ scheduled_time_numeric)`
   - Hourly: `anova(lm(violation_count ~ hour_of_day))`
   - Daily: `anova(lm(violation_count ~ day_of_week))`

2. **Are outputs consistent across repetitions?**
   - Same prompt at different random times
   - Measure coefficient of variation across repetitions

3. **Do scheduling delays predict quality?**
   - `cor.test(scheduled_vs_actual_delay_sec, violation_count)`

4. **Are there temporal patterns in API errors?**
   - `glm(error_type ~ hour_of_day + engine, family=multinomial)`

5. **Does generation speed correlate with quality?**
   - `cor.test(tokens_per_second, violation_count)`

---

## Reproducibility Guarantee

✅ Fixed `RANDOMIZATION_SEED = 12345`
✅ Deterministic run_id generation (SHA1 of knobs + prompt)
✅ Git commit hash captured (dffca39)
✅ Python version captured (3.12.2)
✅ Prompt hash captured (SHA256 of rendered text)

**This means**: Deleting and regenerating the matrix will produce **identical** run_ids and **identical** scheduled times.
