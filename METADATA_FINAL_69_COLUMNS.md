# Final Metadata Schema: 69 Columns for Temporal Unreliability Research

**Research Goal**: Temporal unreliability - Do LLMs produce inconsistent/unreliable outputs across different times?

**Total Columns**: 69 (47 base + 22 additional)

---

## Complete 69-Column Schema

### CORE IDENTIFIERS (4)
1. `run_id` - Unique identifier
2. `product_id` - Product being marketed
3. `material_type` - Template type (faq.j2, etc.)
4. `engine` - LLM provider (openai, google, mistral)

### PROMPT INFO (3)
5. `prompt_id` - Prompt version identifier
6. `prompt_text_path` - Path to saved prompt
7. `system_prompt` - System prompt if used

### MODEL SETUP (8)
8. `model` - Model name
9. `model_version` - API snapshot ID
10. `temperature` - Sampling temperature
11. `max_tokens` - Max completion tokens
12. `seed` - Random seed for reproducibility
13. `top_p` - Nucleus sampling
14. `frequency_penalty` - Repetition penalty
15. `presence_penalty` - Token diversity penalty

### RANDOMIZATION & SCHEDULING (6)
16. `scheduled_datetime` - When run should execute (ISO 8601 UTC)
17. `scheduled_time_numeric` - Hours since experiment start (0.0-72.0)
18. `scheduled_vs_actual_delay_sec` - Delay between scheduled and actual
19. `randomization_seed_scheduling` - Seed for time randomization
20. `day_of_week` - Monday-Sunday
21. `hour_of_day` - Hour 0-23

### RUN CONTEXT (6)
22. `session_id` - Session/batch identifier
23. `account_id` - User account
24. `time_of_day_label` - Categorical time (morning/afternoon/evening)
25. `repetition_id` - Repetition number (1, 2, 3)
26. `started_at` - Actual start time (ISO 8601 UTC)
27. `completed_at` - Actual completion time (ISO 8601 UTC)

### ERROR & RELIABILITY TRACKING (5)
28. `retry_count` - Number of API retries (0 = first-try success)
29. `error_type` - Classification (rate_limit, timeout, content_filter, api_error, none)
30. `error_message` - Full error text if failed
31. `content_filter_triggered` - Safety filter blocked output
32. `api_response_code` - HTTP status code (200, 429, 500, etc.)

### QUALITY & PERFORMANCE INDICATORS (5)
33. `api_latency_ms` - Time to first response byte
34. `tokens_per_second` - Generation speed
35. `prompt_hash` - SHA256 hash of prompt (detect changes)
36. `output_length_chars` - Character count
37. `output_word_count` - Word count

### RESPONSE DATA (5)
38. `prompt_tokens` - Input tokens
39. `completion_tokens` - Output tokens
40. `total_tokens` - Total tokens
41. `finish_reason` - Stop reason (stop, length, etc.)
42. `output_path` - Path to generated text file

### COMPUTED/DERIVED (3)
43. `date_of_run` - Date only (YYYY-MM-DD)
44. `execution_duration_sec` - Time to complete
45. `status` - Run state (pending, completed, failed)

### EXPERIMENTAL DESIGN (1)
46. `trap_flag` - Trap batch flag

### **NEW: CONTENT ANALYSIS & COMPLIANCE (6)**
47. `claim_count_extracted` - Number of claims in output
48. `violation_count` - Number of violations found
49. `has_prohibited_claims` - Contains prohibited content
50. `has_missing_disclaimers` - Missing mandatory statements
51. `output_language_detected` - Language code (en, es, etc.)
52. `output_format_valid` - Follows template structure

### **NEW: API & INFRASTRUCTURE (4)**
53. `api_endpoint_used` - API endpoint URL
54. `client_library_version` - Library version (e.g., openai==1.12.0)
55. `system_load_cpu_percent` - CPU usage during run
56. `network_conditions` - Network type/quality

### **NEW: EXPERIMENTAL CONTROL (5)**
57. `run_order_global` - Global execution order (1-1620)
58. `run_order_per_engine` - Execution order within engine
59. `batch_id` - Batch grouping identifier
60. `was_rerun` - Is this a retry of failed run
61. `original_run_id` - Original run_id if rerun

### **NEW: MODEL BEHAVIOR INDICATORS (4)**
62. `repetition_detected` - Output has repetition
63. `truncation_occurred` - Hit max_tokens limit
64. `stop_reason_abnormal` - Unexpected stop reason
65. `output_completeness_score` - Task completion (0.0-1.0)

### **NEW: METADATA ABOUT METADATA (3)**
66. `metadata_version` - Schema version (v2.0)
67. `data_collected_by` - Collection method (automated_runner, manual_upload)
68. `git_commit_hash` - Code version used
69. `python_version` - Python version (e.g., 3.11.5)

---

## Field Definitions & Population Strategy

### Populated During Matrix Generation

```python
# In generate_matrix.py
import random
import hashlib
from datetime import datetime, timedelta

EXPERIMENT_START = datetime(2025, 2, 23, 0, 0, 0)  # UTC
RANDOMIZATION_SEED = 12345

random.seed(RANDOMIZATION_SEED)

for run in experimental_matrix:
    # Randomization
    random_hours = random.uniform(0.0, 72.0)
    scheduled_dt = EXPERIMENT_START + timedelta(hours=random_hours)

    run['scheduled_datetime'] = scheduled_dt.isoformat() + 'Z'
    run['scheduled_time_numeric'] = random_hours
    run['randomization_seed_scheduling'] = RANDOMIZATION_SEED
    run['day_of_week'] = scheduled_dt.strftime("%A")
    run['hour_of_day'] = scheduled_dt.hour

    # Prompt tracking
    run['prompt_hash'] = hashlib.sha256(prompt_text.encode()).hexdigest()[:16]

    # Metadata
    run['metadata_version'] = "v2.0"
    run['data_collected_by'] = "automated_runner"
    run['git_commit_hash'] = get_git_hash()
    run['python_version'] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.minor}"

    # Initialize empty fields
    run['run_order_global'] = 0  # Will be set during execution
    run['run_order_per_engine'] = 0
    run['batch_id'] = ""
    run['was_rerun'] = False
    run['original_run_id'] = ""
    run['retry_count'] = 0
    run['error_type'] = "none"
    run['error_message'] = ""
    run['content_filter_triggered'] = False
    # ... etc
```

### Populated During Execution

```python
# In run_job.py
import psutil  # For system metrics

def run_single_job(...):
    # Track execution order
    global GLOBAL_RUN_COUNTER, ENGINE_RUN_COUNTERS
    run_order_global = GLOBAL_RUN_COUNTER
    GLOBAL_RUN_COUNTER += 1

    run_order_per_engine = ENGINE_RUN_COUNTERS[engine]
    ENGINE_RUN_COUNTERS[engine] += 1

    # System metrics
    system_load_cpu_percent = psutil.cpu_percent(interval=0.1)
    network_conditions = detect_network_type()  # wifi_stable, ethernet, etc.

    # API call with detailed tracking
    start_time = datetime.utcnow()
    retry_count = 0
    error_type = "none"
    error_message = ""
    content_filter_triggered = False
    api_response_code = 200

    try:
        response, latency_ms = call_engine_with_timing(...)
        api_latency_ms = latency_ms

        # Check for content filter
        if response.get("finish_reason") in ["content_filter", "safety"]:
            content_filter_triggered = True

    except RateLimitError as e:
        error_type = "rate_limit"
        error_message = str(e)
        api_response_code = 429
        retry_count += 1
        # ... retry logic

    # Output analysis
    output_text = response["output_text"]
    output_length_chars = len(output_text)
    output_word_count = len(output_text.split())

    # Quick quality checks
    repetition_detected = detect_repetition(output_text)
    truncation_occurred = (finish_reason == "length")
    stop_reason_abnormal = (finish_reason not in ["stop", "length"])
    output_format_valid = validate_format(output_text, material_type)
    output_language_detected = detect_language(output_text)

    # Completeness score (simple heuristic)
    expected_length = get_expected_length(material_type)
    output_completeness_score = min(1.0, output_length_chars / expected_length)

    # Calculate delays
    actual_start = datetime.utcnow()
    scheduled_vs_actual_delay_sec = (actual_start - scheduled_datetime).total_seconds()

    # Tokens per second
    tokens_per_second = completion_tokens / execution_duration_sec if execution_duration_sec > 0 else 0

    # Library versions
    import openai, google.generativeai, mistralai
    if engine == "openai":
        client_library_version = f"openai=={openai.__version__}"
    elif engine == "google":
        client_library_version = f"google-generativeai=={google.generativeai.__version__}"
    # ...

    return {
        # ... all 69 fields
    }
```

### Populated After Audit (Optional Quick Analysis)

```python
# After generation, before full Glass Box Audit
# Quick compliance scan

from analysis.quick_scan import scan_for_violations

output_text = read_output(run_id)
product_yaml = load_product_yaml(product_id)

quick_scan = scan_for_violations(output_text, product_yaml)

update_csv_row(run_id, {
    'claim_count_extracted': quick_scan['claim_count'],
    'violation_count': quick_scan['violation_count'],
    'has_prohibited_claims': quick_scan['has_prohibited'],
    'has_missing_disclaimers': quick_scan['missing_disclaimers']
})
```

---

## Temporal Unreliability Analysis Enabled

### Primary Research Questions

**1. Does violation rate vary by time?**
```r
# Continuous time effect
model1 <- lm(violation_count ~ scheduled_time_numeric, data=results)

# Hour of day effect
model2 <- lm(violation_count ~ hour_of_day, data=results)

# Day of week effect
anova(lm(violation_count ~ day_of_week, data=results))
```

**2. Are outputs consistent across repetitions?**
```r
# Same prompt at different times
repetitions <- results %>%
  group_by(product_id, material_type, engine, temperature) %>%
  filter(n() == 3)  # All 3 reps present

# Variance in violation counts
repetitions %>%
  summarise(
    mean_violations = mean(violation_count),
    sd_violations = sd(violation_count),
    cv = sd_violations / mean_violations  # Coefficient of variation
  )

# Correlation between repetitions
cor.test(repetitions$violation_count[repetition_id==1],
         repetitions$violation_count[repetition_id==2])
```

**3. Do error rates vary by time?**
```r
# Error rate over time
glm(content_filter_triggered ~ scheduled_time_numeric + engine,
    data=results, family=binomial)

# API errors by hour
table(results$hour_of_day, results$error_type != "none")
```

**4. Does generation quality degrade over time?**
```r
# Quality metrics over time
cor.test(results$scheduled_time_numeric, results$output_completeness_score)
cor.test(results$scheduled_time_numeric, results$tokens_per_second)

# Latency patterns
ggplot(results, aes(x=hour_of_day, y=api_latency_ms, color=engine)) +
  geom_boxplot()
```

**5. Are there execution order effects?**
```r
# Quota exhaustion?
model <- lm(error_type == "rate_limit" ~ run_order_per_engine, data=results)

# Does quality degrade with fatigue?
cor.test(results$run_order_global, results$violation_count)
```

---

## CSV Column Order (69 Total)

```csv
run_id,product_id,material_type,engine,
prompt_id,prompt_text_path,system_prompt,
model,model_version,temperature,max_tokens,seed,top_p,frequency_penalty,presence_penalty,
scheduled_datetime,scheduled_time_numeric,scheduled_vs_actual_delay_sec,randomization_seed_scheduling,day_of_week,hour_of_day,
session_id,account_id,time_of_day_label,repetition_id,started_at,completed_at,
retry_count,error_type,error_message,content_filter_triggered,api_response_code,
api_latency_ms,tokens_per_second,prompt_hash,output_length_chars,output_word_count,
prompt_tokens,completion_tokens,total_tokens,finish_reason,output_path,
date_of_run,execution_duration_sec,status,
trap_flag,
claim_count_extracted,violation_count,has_prohibited_claims,has_missing_disclaimers,output_language_detected,output_format_valid,
api_endpoint_used,client_library_version,system_load_cpu_percent,network_conditions,
run_order_global,run_order_per_engine,batch_id,was_rerun,original_run_id,
repetition_detected,truncation_occurred,stop_reason_abnormal,output_completeness_score,
metadata_version,data_collected_by,git_commit_hash,python_version
```

---

## Implementation Checklist

### Phase 1: Schema & Randomization
- [ ] Update config.py with EXPERIMENT_START, RANDOMIZATION_SEED
- [ ] Update generate_matrix.py to assign scheduled times
- [ ] Test: Generate matrix with 69 columns, all randomization fields populated

### Phase 2: Runtime Capture
- [ ] Update run_job.py to track execution order (global counters)
- [ ] Add system metrics capture (psutil for CPU)
- [ ] Add network detection
- [ ] Add retry tracking to engine clients
- [ ] Add latency measurement to engine clients
- [ ] Test: Run single job, verify all runtime fields populated

### Phase 3: Quality Analysis
- [ ] Create quick_scan.py for immediate violation detection
- [ ] Add repetition detection function
- [ ] Add format validation function
- [ ] Add language detection
- [ ] Add completeness scoring
- [ ] Test: Run + quick scan, verify content analysis fields

### Phase 4: Validation
- [ ] Generate test matrix (10 runs)
- [ ] Execute all 10 runs
- [ ] Verify all 69 columns populated correctly
- [ ] Load into R and verify statistical analysis works
- [ ] Document any missing/empty fields (with justification)

---

## Benefits for Temporal Unreliability Research

**Granular Time Tracking**:
- Scheduled vs actual times (detect system delays)
- Hour-level precision (not just morning/afternoon/evening)
- Continuous time variable (0-72 hours) for regression

**Error Causation**:
- Link errors to time of day
- Detect quota exhaustion patterns
- Identify provider-specific temporal issues

**Quality Consistency**:
- Track if quality degrades over time
- Detect if certain hours have more violations
- Measure output consistency across repetitions

**Complete Reproducibility**:
- Git hash tracks code version
- Randomization seed enables exact replication
- All environmental factors documented

---

## Next Step

Should I start implementing:
1. **Phase 1** (randomization + matrix generation) first, or
2. All phases at once?

I recommend Phase 1 first, test it, then move to Phase 2-4.
