# Complete Metadata Schema with Randomization Support

**Purpose**: Track everything needed for statistical analysis of LLM marketing material generation, including randomization, error analysis, and quality indicators.

---

## Total Columns: 47 (31 current + 16 new)

---

## NEW FIELDS (16 Added)

### A. Randomization & Scheduling (6 fields)

| Field | Type | Example | Why Track This |
|-------|------|---------|----------------|
| `scheduled_datetime` | datetime | `2025-02-22T14:35:00Z` | When run was SUPPOSED to execute (for randomization verification) |
| `scheduled_time_numeric` | float | `38.583` | Hours since experiment start (0.0-72.0) - for regression analysis |
| `scheduled_vs_actual_delay_sec` | float | `12.5` | Delay between scheduled and actual start (queue/system lag) |
| `randomization_seed_scheduling` | int | `98765` | Seed used to randomize run times (reproducibility) |
| `day_of_week` | str | `Saturday` | Weekday name (API behavior might vary) |
| `hour_of_day` | int | `14` | Hour 0-23 (for circadian/usage pattern analysis) |

**Why**: Verify randomization worked, detect time-based patterns, measure system delays

### B. Error & Reliability Tracking (5 fields)

| Field | Type | Example | Why Track This |
|-------|------|---------|----------------|
| `retry_count` | int | `2` | How many API retries happened (0 = success first try) |
| `error_type` | str | `rate_limit` | Classification: rate_limit, timeout, content_filter, api_error, none |
| `error_message` | text | `Rate limit exceeded...` | Full error message if failed |
| `content_filter_triggered` | bool | `True` | Did safety filters block output? (Google/OpenAI) |
| `api_response_code` | int | `200` | HTTP status code (200, 429, 500, etc.) |

**Why**: Understand failure modes, detect provider-specific issues, identify problematic prompts/products

### C. Quality & Performance Indicators (5 fields)

| Field | Type | Example | Why Track This |
|-------|------|---------|----------------|
| `api_latency_ms` | int | `3452` | Time from API request to first response (network + processing) |
| `tokens_per_second` | float | `28.3` | Generation speed (completion_tokens / execution_duration_sec) |
| `prompt_hash` | str | `a3f8b2e1` | SHA256 hash of prompt (detect template changes) |
| `output_length_chars` | int | `1847` | Character count of generated text |
| `output_word_count` | int | `312` | Word count of generated text |

**Why**: Detect quality degradation over time, identify slow/fast providers, track output consistency

---

## EXISTING FIELDS (31 from previous work)

### Core Identifiers (4)
run_id, product_id, material_type, engine

### Prompt Info (3)
prompt_id, prompt_text_path, system_prompt

### Model Setup (8)
model, model_version, temperature, max_tokens, seed, top_p, frequency_penalty, presence_penalty

### Run Context (6)
session_id, account_id, time_of_day_label, repetition_id, started_at, completed_at

### Response Data (5)
prompt_tokens, completion_tokens, total_tokens, finish_reason, output_path

### Computed/Derived (3)
date_of_run, execution_duration_sec, status

### Experimental Design (1)
trap_flag

---

## Complete 47-Column Schema

```csv
# CORE IDENTIFIERS (4)
run_id,
product_id,
material_type,
engine,

# PROMPT INFO (3)
prompt_id,
prompt_text_path,
system_prompt,

# MODEL SETUP (8)
model,
model_version,
temperature,
max_tokens,
seed,
top_p,
frequency_penalty,
presence_penalty,

# RANDOMIZATION & SCHEDULING (6) **NEW**
scheduled_datetime,
scheduled_time_numeric,
scheduled_vs_actual_delay_sec,
randomization_seed_scheduling,
day_of_week,
hour_of_day,

# RUN CONTEXT (6)
session_id,
account_id,
time_of_day_label,
repetition_id,
started_at,
completed_at,

# ERROR & RELIABILITY (5) **NEW**
retry_count,
error_type,
error_message,
content_filter_triggered,
api_response_code,

# QUALITY & PERFORMANCE (5) **NEW**
api_latency_ms,
tokens_per_second,
prompt_hash,
output_length_chars,
output_word_count,

# RESPONSE DATA (5)
prompt_tokens,
completion_tokens,
total_tokens,
finish_reason,
output_path,

# COMPUTED/DERIVED (3)
date_of_run,
execution_duration_sec,
status,

# EXPERIMENTAL DESIGN (1)
trap_flag
```

---

## Randomization Strategy

### How to Schedule Runs

**Option 1: Random within windows** (RECOMMENDED)
```python
import random
from datetime import datetime, timedelta

EXPERIMENT_START = datetime(2025, 2, 23, 0, 0, 0)  # Sunday midnight
EXPERIMENT_END = EXPERIMENT_START + timedelta(hours=72)  # 3 days

randomization_seed = 12345
random.seed(randomization_seed)

for run_id in experimental_matrix:
    # Random time within 72-hour window
    random_hours = random.uniform(0.0, 72.0)
    scheduled_datetime = EXPERIMENT_START + timedelta(hours=random_hours)

    # Calculate numeric time for analysis
    scheduled_time_numeric = random_hours

    # Extract date/time components
    day_of_week = scheduled_datetime.strftime("%A")
    hour_of_day = scheduled_datetime.hour
```

**Benefits**:
- True randomization (avoids time-based confounds)
- Can still filter/stratify by time windows in analysis
- Detects temporal unreliability (not just morning vs evening)

**Option 2: Stratified random** (more structured)
```python
# Assign each run to one of 3 time-of-day conditions (morning/afternoon/evening)
# Then randomize execution across 7-day window with jitter

TIME_SLOTS = [
    ("morning_day1", 6, 12),   # Day 1: 6am-12pm
    ("afternoon_day1", 12, 18), # Day 1: 12pm-6pm
    ("evening_day1", 18, 24),   # Day 1: 6pm-12am
    # ... (9 slots total)
]

for run_id in experimental_matrix:
    slot_name, slot_start, slot_end = assign_time_slot(run_id)

    # Random time within slot ± 30min jitter
    base_time = random.uniform(slot_start, slot_end)
    jitter_minutes = random.uniform(-30, 30)
    scheduled_datetime = EXPERIMENT_START + timedelta(hours=base_time, minutes=jitter_minutes)
```

**Benefits**:
- Balanced across time periods
- Still has randomness (jitter)
- Easier to ensure coverage

---

## Statistical Analysis Enabled

### With Complete Metadata, You Can Answer:

**1. Temporal Unreliability**
```r
# Does violation rate vary by time of day?
model <- lm(violation_count ~ scheduled_time_numeric + hour_of_day + day_of_week, data=results)

# Are outputs consistent across repetitions at different times?
cor.test(results$output_length_chars[rep==1], results$output_length_chars[rep==2])
```

**2. Provider Reliability**
```r
# Which engine has highest error rate?
table(results$engine, results$error_type)

# Does latency correlate with errors?
cor.test(results$api_latency_ms, results$violation_count)
```

**3. Temperature Effects**
```r
# Does higher temperature → more hallucinations?
anova(lm(violation_count ~ temperature + engine, data=results))

# Does temperature affect output length?
ggplot(results, aes(x=temperature, y=output_word_count, color=engine)) + geom_point()
```

**4. Product-Specific Issues**
```r
# Which product triggers most content filters?
table(results$product_id, results$content_filter_triggered)

# Do certain products have slower generation?
aggregate(tokens_per_second ~ product_id + engine, data=results, mean)
```

**5. Time-Based Degradation**
```r
# Does quality degrade over experiment duration?
cor.test(results$scheduled_time_numeric, results$violation_count)

# Are there time-of-day effects on API performance?
boxplot(api_latency_ms ~ hour_of_day, data=results)
```

**6. Error Causation**
```r
# What predicts content filter blocks?
glm(content_filter_triggered ~ product_id + temperature + engine + hour_of_day,
    data=results, family=binomial)

# What predicts API errors?
table(results$error_type, results$engine)
```

---

## Implementation Notes

### populate during matrix generation:
- `scheduled_datetime` - Assign random time
- `scheduled_time_numeric` - Calculate hours since start
- `randomization_seed_scheduling` - Same for all runs (reproducibility)
- `day_of_week`, `hour_of_day` - Extract from scheduled_datetime
- `prompt_hash` - Hash of rendered prompt

### Capture during execution:
- `started_at` - Actual start time
- `scheduled_vs_actual_delay_sec` - started_at - scheduled_datetime
- `retry_count` - Increment on each retry
- `error_type`, `error_message` - From exception
- `content_filter_triggered` - Check finish_reason
- `api_response_code` - From API response
- `api_latency_ms` - Time to first response byte
- `tokens_per_second` - completion_tokens / execution_duration_sec
- `output_length_chars`, `output_word_count` - From generated text

### Leave empty if not applicable:
- `error_type`, `error_message` - Empty for successful runs
- `retry_count` - 0 for first-try success
- `scheduled_vs_actual_delay_sec` - 0 if run immediately

---

## Validation Checklist

Before running experiments:

- [ ] All 47 columns defined in CSV header
- [ ] Randomization seed set and documented
- [ ] Scheduled times assigned to all runs
- [ ] scheduled_time_numeric calculated correctly (0.0-72.0)
- [ ] prompt_hash generated for all runs
- [ ] Error tracking implemented in engine clients
- [ ] Retry counting implemented
- [ ] Content filter detection implemented
- [ ] Latency measurement implemented
- [ ] Output metrics calculated (length, word count)
- [ ] Test single run populates all 47 fields

---

## Example Complete Row

```csv
abc123...,smartphone_mid,faq.j2,openai,smartphone_faq_v1,outputs/prompts/abc123.txt,NULL,gpt-4o,gpt-4o-2024-05-13,0.6,2000,12345,NULL,NULL,NULL,2025-02-23T14:35:00Z,38.583,12.5,98765,Saturday,14,main_exp_2025_02_22,researcher_primary,afternoon,2,2025-02-23T14:35:12Z,2025-02-23T14:35:47Z,0,none,NULL,False,200,3452,28.3,a3f8b2e1,1847,312,1250,750,2000,stop,outputs/abc123.txt,2025-02-23,35.0,completed,False
```

---

## Benefits for Research Paper

With this complete metadata, you can write:

**Methods Section**:
- "Runs were randomly scheduled across 72 hours using seed 12345 for reproducibility"
- "We tracked 47 metadata fields including API latency, retry counts, and content filter triggers"

**Results Section**:
- "API errors occurred in X% of runs, primarily rate_limit (Y%) and timeout (Z%)"
- "Mean generation speed: OpenAI 28.3 tok/s, Google 31.2 tok/s, Mistral 24.1 tok/s"
- "Content filters blocked X% of cryptocurrency prompts vs Y% of smartphone prompts"

**Discussion Section**:
- "Violation rates showed no significant correlation with time of day (r=0.03, p=0.45)"
- "Higher temperature settings correlated with increased output length (r=0.62, p<0.001)"
- "Latency did not predict violation rate, suggesting quality is independent of API load"

---

## Next Steps

1. Update `config.py` with randomization settings
2. Update `generate_matrix.py` to assign scheduled times
3. Update `run_job.py` to capture error/quality metrics
4. Update engine clients to track retries and latency
5. Test on single run to validate all 47 fields
