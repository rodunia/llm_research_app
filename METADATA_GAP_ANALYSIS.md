# Metadata Gap Analysis: Current vs Required for Statistical Analysis

**Date**: 2025-02-21
**Purpose**: Compare current implementation metadata against research paper's required metadata schema

---

## Summary

**Current implementation captures**: 10/22 fields (45%)
**Missing critical fields**: 12 fields for reproducibility and statistical analysis

---

## Field-by-Field Comparison

### ✅ Currently Captured (10 fields)

| Category | Field | experiments.csv Column | Source | Notes |
|----------|-------|------------------------|--------|-------|
| **Response data** | output_text | (separate file) | `outputs/{run_id}.txt` | Stored as file, not in CSV |
| **Response data** | finish_reason | `finish_reason` | Engine response | ✅ Captured |
| **Response data** | prompt_tokens | `prompt_tokens` | Engine response | ✅ Captured |
| **Response data** | completion_tokens | `completion_tokens` | Engine response | ✅ Captured |
| **Response data** | total_tokens | `total_tokens` | Engine response | ✅ Captured |
| **Model setup** | model | `model` | Engine response | ✅ Captured (actual model used) |
| **Model setup** | temperature | `temperature_label` | config.py | ✅ Captured |
| **Run context** | timestamp | `started_at`, `completed_at` | run_job.py | ✅ Captured (both start and end) |
| **Run context** | repetition_id | `repetition_id` | experiments.csv | ✅ Captured (1, 2, 3) |
| **Prompt info** | prompt_text | (separate file) | `outputs/prompts/{run_id}.txt` | ⚠️ NOT currently saved |

### ❌ Missing Critical Fields (12 fields)

| Category | Field | Why Missing | Impact | Recommended Fix |
|----------|-------|-------------|--------|-----------------|
| **Prompt info** | prompt_id | No unique ID assigned | Can't track prompt versions over time | Add hash of template+product as `prompt_id` |
| **Prompt info** | system_prompt | Not separated from user prompt | Can't analyze system prompt impact | Save system_prompt separately if used |
| **Model setup** | model_version | API doesn't return snapshot ID | Can't reproduce exact model behavior | Save `model_version` from API if available (OpenAI returns model snapshot) |
| **Model setup** | max_tokens | Hardcoded in engine clients | Can't analyze token limit impact | Add `max_tokens` to experiments.csv |
| **Model setup** | top_p | Not configured | Can't analyze nucleus sampling | Add `top_p` to config.py and experiments.csv (currently using defaults) |
| **Model setup** | frequency_penalty | Not configured | Can't analyze repetition penalties | Add to config.py if testing (OpenAI, Anthropic support this) |
| **Model setup** | presence_penalty | Not configured | Can't analyze token diversity | Add to config.py if testing (OpenAI, Anthropic support this) |
| **Model setup** | seed | Not configured | Can't guarantee exact reproducibility | Add `seed` to config.py for deterministic runs (OpenAI, Anthropic support) |
| **Run context** | account_id | Not tracked | Can't separate multi-user experiments | Add `account_id` column (currently single user) |
| **Run context** | session_id | Optional in CLI, not saved | Can't group runs by session | Make `session_id` required and save to CSV |
| **Response data** | (metadata) | No error details captured | Can't analyze failure modes | Save error type, message for failed runs |
| **Additional** | time_of_day_slot | Only label, not slot # | Can't analyze temporal patterns numerically | Add `time_slot_id` (1-9) for statistical analysis |

---

## Critical Gaps for Statistical Analysis

### 1. **Reproducibility** (HIGH PRIORITY)

**Missing**:
- `seed`: Without seed, can't reproduce exact outputs (even at temp=0)
- `model_version`: Model snapshots change - need to track which snapshot was used
- `system_prompt`: If system prompts vary, can't isolate impact

**Impact**: Peer reviewers can't reproduce results exactly

**Fix**:
```python
# In engine clients, add:
response = client.chat.completions.create(
    model=model,
    temperature=temperature,
    seed=12345,  # NEW: Fixed seed for reproducibility
    # ...
)

# Save in experiments.csv:
# seed, model_version, system_prompt_hash
```

### 2. **Statistical Significance Testing** (HIGH PRIORITY)

**Missing**:
- `time_slot_id`: Currently "morning" (string) not analyzable numerically
- Error metadata: Can't calculate error rates by model/temp/time

**Impact**: Can't run ANOVA, t-tests, regression on temporal patterns

**Fix**:
```python
# Add to experiments.csv:
# time_slot_id (1-9), date_of_run, error_type, error_message

# Enables statistical tests:
# - ANOVA: Does time_slot_id significantly affect violation rate?
# - Regression: violation_rate ~ temperature + time_slot_id
```

### 3. **Prompt Engineering Analysis** (MEDIUM PRIORITY)

**Missing**:
- `prompt_id`: Can't track when prompts change
- `prompt_tokens` breakdown: System vs user tokens not separated

**Impact**: Can't analyze which prompt changes improved results

**Fix**:
```python
# Add prompt versioning:
prompt_id = f"{material_type}_{hash(template_content)[:8]}"

# Track in experiments.csv:
# prompt_id, prompt_version, prompt_hash
```

### 4. **Model Parameter Exploration** (LOW PRIORITY for current study)

**Missing**:
- `top_p`, `frequency_penalty`, `presence_penalty`

**Impact**: Can't test if these parameters reduce hallucinations

**Note**: Current study uses defaults - OK for now, but future work should vary these

---

## Recommended Implementation Priority

### Phase 1: Minimal Reproducibility (URGENT)
Add these fields NOW before running full 1,620-file experiment:

```python
# experiments.csv new columns:
- seed (int)
- model_version (str)
- max_tokens (int)
- session_id (str)
- time_slot_id (int, 1-9)
- date_of_run (YYYY-MM-DD)
```

**Effort**: 2-3 hours
**Impact**: Enables peer review reproducibility

### Phase 2: Statistical Analysis Support (HIGH)
Add after pilot validation complete:

```python
# experiments.csv new columns:
- prompt_id (str)
- prompt_hash (str, first 8 chars of SHA256)
- error_type (str, NULL if completed)
- error_message (str, NULL if completed)
```

**Effort**: 1-2 hours
**Impact**: Enables statistical significance testing

### Phase 3: Advanced Parameter Testing (FUTURE)
Add only if testing these parameters:

```python
# experiments.csv new columns:
- top_p (float, NULL if not set)
- frequency_penalty (float, NULL if not set)
- presence_penalty (float, NULL if not set)
- system_prompt_text (text, NULL if not used)
```

**Effort**: 2-3 hours
**Impact**: Enables future parameter optimization studies

---

## Example: Enhanced experiments.csv Schema

```csv
run_id,product_id,material_type,engine,model,model_version,temperature,seed,max_tokens,top_p,frequency_penalty,presence_penalty,
time_of_day_label,time_slot_id,date_of_run,repetition_id,session_id,account_id,
prompt_id,prompt_hash,
status,started_at,completed_at,
prompt_tokens,completion_tokens,total_tokens,finish_reason,
error_type,error_message,
output_path,trap_flag
```

**Current**: 17 columns
**Proposed**: 31 columns (+14 for reproducibility and statistical analysis)

---

## Code Changes Required

### 1. Update `runner/run_job.py`

**Before**:
```python
def run_single_job(run_id, product_id, material_type, engine, temperature, trap_flag):
    # ...
    response = call_engine(engine=engine, prompt=prompt_text, temperature=temperature)
```

**After**:
```python
def run_single_job(run_id, product_id, material_type, engine, temperature, trap_flag,
                   seed=12345, max_tokens=2000, session_id=None):
    # ...
    # Calculate prompt_id
    prompt_id = f"{material_type}_{hashlib.sha256(prompt_text.encode()).hexdigest()[:8]}"

    # Call engine with additional params
    response = call_engine(
        engine=engine,
        prompt=prompt_text,
        temperature=temperature,
        seed=seed,  # NEW
        max_tokens=max_tokens  # NEW
    )

    # Return enhanced metadata
    result = {
        "status": "completed",
        "started_at": started_at,
        "completed_at": completed_at,
        "model": response.get("model", ""),
        "model_version": response.get("model_version", ""),  # NEW
        "seed": seed,  # NEW
        "max_tokens": max_tokens,  # NEW
        "prompt_id": prompt_id,  # NEW
        "prompt_hash": hashlib.sha256(prompt_text.encode()).hexdigest()[:8],  # NEW
        # ... rest of fields
    }
```

### 2. Update `config.py`

**Add**:
```python
# --- REPRODUCIBILITY SETTINGS ---
DEFAULT_SEED = 12345  # Fixed seed for reproducibility
DEFAULT_MAX_TOKENS = 2000  # Max completion tokens

# Optional: Parameter sweep (for future studies)
PARAMETER_SWEEP = {
    "top_p": [0.9, 0.95, 1.0],  # Nucleus sampling
    "frequency_penalty": [0.0, 0.5, 1.0],  # Repetition penalty
}
```

### 3. Update engine clients (e.g., `openai_client.py`)

**Before**:
```python
def call_openai(prompt, temperature, max_tokens=2000):
    response = client.chat.completions.create(
        model=ENGINE_MODELS["openai"],
        temperature=temperature,
        max_completion_tokens=max_tokens,
        # ...
    )
```

**After**:
```python
def call_openai(prompt, temperature, max_tokens=2000, seed=None, top_p=None,
                frequency_penalty=None, presence_penalty=None):
    params = {
        "model": ENGINE_MODELS["openai"],
        "temperature": temperature,
        "max_completion_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }

    # Add optional params if specified
    if seed is not None:
        params["seed"] = seed
    if top_p is not None:
        params["top_p"] = top_p
    if frequency_penalty is not None:
        params["frequency_penalty"] = frequency_penalty
    if presence_penalty is not None:
        params["presence_penalty"] = presence_penalty

    response = client.chat.completions.create(**params)

    return {
        "output_text": response.choices[0].message.content,
        "finish_reason": response.choices[0].finish_reason,
        "model": response.model,
        "model_version": response.model,  # NEW: OpenAI returns snapshot ID
        # ...
    }
```

### 4. Update `runner/generate_matrix.py`

**Add time_slot_id calculation**:
```python
# Map time_of_day to numeric slot
TIME_SLOT_MAP = {
    "morning": 1,
    "afternoon": 2,
    "evening": 3,
}

# When generating rows:
for date_idx in range(1, 4):  # 3 days
    for time_of_day in TIMES:
        time_slot_id = TIME_SLOT_MAP[time_of_day] + (date_idx - 1) * 3  # 1-9
        # Add to CSV:
        # ..., time_slot_id=time_slot_id, date_of_run=f"2025-02-{21+date_idx}", ...
```

---

## Validation Checklist

Before running full experiment, verify:

- [ ] `seed` is set and saved for all runs
- [ ] `model_version` is captured from API responses
- [ ] `max_tokens` is configurable and tracked
- [ ] `time_slot_id` (1-9) is assigned correctly
- [ ] `prompt_id` uniquely identifies template version
- [ ] `session_id` is assigned (e.g., "pilot_study_2025_02_21")
- [ ] Failed runs save `error_type` and `error_message`
- [ ] All 31 columns export correctly to experiments.csv

---

## Impact on Current Pilot Study

**Good news**: Pilot study (30 files) already complete and validated (100% detection)

**Action needed**:
1. **Re-run pilot with enhanced metadata** (optional, for consistency)
2. **Use enhanced schema for full 1,620-file experiment** (required)

**Cost**: ~$0.06 to re-run pilot with new metadata (if desired)

---

## Questions for Discussion

1. **Seed strategy**: Use same seed for all runs, or different seeds per repetition?
   - Same seed: Easier to reproduce, but less statistical power
   - Different seeds: More variance, better for significance testing

2. **System prompts**: Are system prompts used in any templates?
   - If yes, need to track separately
   - If no, can skip `system_prompt` field

3. **Parameter sweep**: Should we vary `top_p`, `frequency_penalty` now or future?
   - Now: Expands experimental matrix significantly
   - Future: Keep current design focused on temperature + time

4. **Backwards compatibility**: Keep existing pilot results or re-run with new schema?
   - Keep: Faster, but inconsistent metadata
   - Re-run: Clean, but costs time/money

---

## References

- **Current schema**: `results/experiments.csv` (17 columns)
- **Engine clients**: `runner/engines/*.py`
- **Matrix generation**: `runner/generate_matrix.py`
- **Research metadata spec**: (provided by user, this document)
