# Complete Metadata Schema Implementation Plan

**Date**: 2025-02-21
**Purpose**: Define and implement full metadata tracking for statistical validity

---

## Complete experiments.csv Schema (31 columns)

### Column List (in order)

```csv
# Core Identifiers (4)
run_id,
product_id,
material_type,
engine,

# Prompt Info (3)
prompt_id,
prompt_text_path,
system_prompt,

# Model Setup (8)
model,
model_version,
temperature,
max_tokens,
seed,
top_p,
frequency_penalty,
presence_penalty,

# Run Context (6)
session_id,
account_id,
time_of_day_label,
repetition_id,
started_at,
completed_at,

# Response Data (5)
prompt_tokens,
completion_tokens,
total_tokens,
finish_reason,
output_path,

# Computed/Derived (3)
date_of_run,
execution_duration_sec,
status,

# Experimental Design (1)
trap_flag
```

---

## Field Definitions

### Core Identifiers

| Field | Type | Example | Source | When Populated |
|-------|------|---------|--------|----------------|
| `run_id` | str | `d69a2921...` | generate_matrix.py | Matrix generation |
| `product_id` | str | `smartphone_mid` | config.PRODUCTS | Matrix generation |
| `material_type` | str | `faq.j2` | config.MATERIALS | Matrix generation |
| `engine` | str | `openai` | config.ENGINES | Matrix generation |

### Prompt Info

| Field | Type | Example | Source | When Populated |
|-------|------|---------|--------|----------------|
| `prompt_id` | str | `smartphone_faq_v1` | Computed: `{product}_{material}_v1` | Matrix generation |
| `prompt_text_path` | str | `outputs/prompts/{run_id}.txt` | Computed | Run execution |
| `system_prompt` | str/NULL | `"You are a helpful..."` or NULL | Template (if used) | Run execution |

### Model Setup

| Field | Type | Example | Source | When Populated |
|-------|------|---------|--------|----------------|
| `model` | str | `gpt-4o` | API response | Run execution |
| `model_version` | str | `gpt-4o-2024-05-13` | API response (if available) | Run execution |
| `temperature` | float | `0.6` | config.TEMPS | Matrix generation |
| `max_tokens` | int | `2000` | config.DEFAULT_MAX_TOKENS | Matrix generation |
| `seed` | int/NULL | `12345` or NULL | config.DEFAULT_SEED | Matrix generation |
| `top_p` | float/NULL | `1.0` or NULL | config (optional) | Matrix generation |
| `frequency_penalty` | float/NULL | `0.0` or NULL | config (optional) | Matrix generation |
| `presence_penalty` | float/NULL | `0.0` or NULL | config (optional) | Matrix generation |

### Run Context

| Field | Type | Example | Source | When Populated |
|-------|------|---------|--------|----------------|
| `session_id` | str | `main_exp_2025_02_21` | CLI argument or generated | Run execution |
| `account_id` | str | `researcher_primary` | config.USER_ACCOUNTS[0] | Matrix generation |
| `time_of_day_label` | str | `morning` | config.TIMES | Matrix generation |
| `repetition_id` | int | `1` | config.REPS | Matrix generation |
| `started_at` | datetime | `2025-02-21T14:35:12Z` | run_job.py | Run execution |
| `completed_at` | datetime | `2025-02-21T14:35:47Z` | run_job.py | Run execution |

### Response Data

| Field | Type | Example | Source | When Populated |
|-------|------|---------|--------|----------------|
| `prompt_tokens` | int | `1250` | API response | Run execution |
| `completion_tokens` | int | `750` | API response | Run execution |
| `total_tokens` | int | `2000` | API response | Run execution |
| `finish_reason` | str | `stop` | API response | Run execution |
| `output_path` | str | `outputs/{run_id}.txt` | Computed | Run execution |

### Computed/Derived

| Field | Type | Example | Source | When Populated |
|-------|------|---------|--------|----------------|
| `date_of_run` | date | `2025-02-21` | Extracted from `started_at` | Run execution |
| `execution_duration_sec` | float | `35.2` | `completed_at - started_at` | Run execution |
| `status` | str | `completed` | run_job.py | Run execution |

### Experimental Design

| Field | Type | Example | Source | When Populated |
|-------|------|---------|--------|----------------|
| `trap_flag` | bool | `False` | config (default) | Matrix generation |

---

## Default Values (config.py additions)

```python
# --- METADATA AND REPRODUCIBILITY SETTINGS ---

# Default values for new metadata fields
DEFAULT_MAX_TOKENS = 2000
DEFAULT_SEED = 12345  # Fixed seed for reproducibility
DEFAULT_TOP_P = None  # Use API default (usually 1.0)
DEFAULT_FREQUENCY_PENALTY = None  # Use API default (usually 0.0)
DEFAULT_PRESENCE_PENALTY = None  # Use API default (usually 0.0)

# Session tracking
DEFAULT_SESSION_ID = "main_experiment"  # Can be overridden via CLI

# Account for single-user study
DEFAULT_ACCOUNT_ID = USER_ACCOUNTS[0]  # "researcher_primary"
```

---

## Implementation Steps

### Step 1: Update config.py
Add default values for all new metadata fields.

### Step 2: Update experiments.csv header
Add 14 new columns to the CSV schema.

### Step 3: Update generate_matrix.py
Populate all matrix-generation fields:
- prompt_id
- max_tokens
- seed
- top_p, frequency_penalty, presence_penalty
- account_id
- prompt_text_path (placeholder)

### Step 4: Update run_job.py
Capture all runtime fields:
- started_at, completed_at
- session_id
- date_of_run
- execution_duration_sec
- Save prompt_text to file

### Step 5: Update engine clients
Support new parameters:
- seed
- top_p
- frequency_penalty
- presence_penalty
- Capture model_version from API

### Step 6: Test on single run
Verify all 31 columns populate correctly.

---

## Example Row (complete metadata)

```csv
d69a29213f96e9478c92fbc65229d65ff02b24bd,smartphone_mid,faq.j2,openai,smartphone_faq_v1,outputs/prompts/d69a2921.txt,NULL,gpt-4o,gpt-4o-2024-05-13,0.6,2000,12345,NULL,NULL,NULL,main_exp_2025_02_21,researcher_primary,morning,1,2025-02-21T09:15:32Z,2025-02-21T09:16:08Z,1250,750,2000,stop,outputs/d69a2921.txt,2025-02-21,36.0,completed,False
```

---

## Validation Checklist

Before running experiments:

- [ ] All 31 columns defined in CSV header
- [ ] config.py has default values for seed, max_tokens, etc.
- [ ] generate_matrix.py populates all matrix fields
- [ ] run_job.py captures all runtime fields
- [ ] All 4 engine clients support seed parameter
- [ ] model_version captured from API responses
- [ ] prompt_text saved to outputs/prompts/ directory
- [ ] Test run shows all 31 fields populated
- [ ] No NULL values where they shouldn't be
- [ ] Timestamps in correct ISO 8601 format

---

## Notes

**NULL vs Empty String**:
- Use `NULL` for: top_p, frequency_penalty, presence_penalty, system_prompt (when not used)
- Use empty string `""` for: error cases where model_version not available

**Timestamps**:
- Always UTC (append 'Z')
- Format: ISO 8601 (`2025-02-21T14:35:12Z`)
- Use Python: `datetime.utcnow().isoformat() + 'Z'`

**prompt_id versioning**:
- Currently: `{product}_{material}_v1`
- If templates change, increment version: `v2`, `v3`
- Track template changes in git commits
