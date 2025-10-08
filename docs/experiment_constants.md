# Experimental Constants

This document defines the frozen experimental matrix for the LLM research pipeline. All factors are locked to ensure reproducibility and deterministic run generation.

## Matrix Dimensions

### Current Scale (Phase 1)
- **Total runs**: 1,620
- **Formula**: 3 products × 5 materials × 4 engines × 3 temperatures × 3 times × 3 repetitions

### Future Scale (Phase 2)
- **Total runs**: 2,700
- **Formula**: 5 products × 5 materials × 4 engines × 3 temperatures × 3 times × 3 repetitions

---

## Factor Definitions

### Products (n=3, future n=5)
**Current active products:**
1. `smartphone_mid` - Nova X5 5G Smartphone
2. `cryptocurrency_corecoin` - CoreCoin (CRC) cryptocurrency
3. `supplement_melatonin` - Melatonin 3mg tablets

**Future products (create YAMLs when ready):**
4. `supplement_herbal` - TBD herbal supplement
5. `audio_bt_headphones` - TBD Bluetooth headphones

**Location**: Product definitions stored in `products/{product_id}.yaml`

---

### Materials (n=5)
Marketing material types using Jinja2 templates:

1. `digital_ad.j2` - Short digital display ad (35-45 words)
2. `organic_social_posts.j2` - Social media posts
3. `faq.j2` - Frequently Asked Questions (5 Q&As)
4. `spec_document_facts_only.j2` - Technical specification document
5. `blog_post_promo.j2` - Promotional blog post

**Location**: Templates stored in `prompts/{material}.j2`

---

### Engines (n=4)
LLM providers with normalized API interfaces:

1. `openai` → `gpt-4o-mini`
2. `google` → `gemini-2.5-flash`
3. `mistral` → `mistral-small-latest`
4. `anthropic` → `claude-3-5-sonnet-20241022`

**Model mapping**: Defined in `config.py::ENGINE_MODELS`

**Client implementation**: `runner/engines/{engine}_client.py`

**Normalized return schema**:
```python
{
    "output_text": str,
    "finish_reason": str,
    "prompt_tokens": int,
    "completion_tokens": int,
    "total_tokens": int,
    "model": str
}
```

---

### Temperatures (n=3)
Sampling temperature values controlling creativity vs. determinism:

1. `0.2` - Low temperature (more deterministic, factual)
2. `0.6` - Medium temperature (balanced)
3. `1.0` - High temperature (more creative, varied)

**Range**: 0.0 (deterministic) to 2.0 (maximum creativity)

---

### Time of Day (n=3)
Temporal labels for experimental runs (treated as "day" labels):

1. `morning` - Morning execution period
2. `afternoon` - Afternoon execution period
3. `evening` - Evening execution period

**Purpose**: Test for temporal drift in model behavior, enable distributed execution scheduling

**Scheduling**: Configured in `orchestrator.py::SCHEDULE_TIMES` (8am, 3pm, 9pm CET)

---

### Repetitions (n=3)
Replication indices for statistical analysis:

1. `1` - First repetition
2. `2` - Second repetition
3. `3` - Third repetition

**Purpose**: Measure within-condition variance, enable reliability analysis

**Interpretation**: Can be treated as "day 1", "day 2", "day 3" labels

---

## Fixed Parameters

### Region
- **Value**: `US`
- **Scope**: All products target US market
- **Impact**: Affects regulatory disclaimers, units (imperial/metric), compliance requirements

### Trap Flag (Base Matrix)
- **Value**: `false`
- **Scope**: All 1,620 base matrix runs
- **Purpose**: Control condition for bias experiments

**Note**: Trap flag experiments (`trap=true`) will be run as a separate batch and are NOT included in the base 1,620-run matrix.

---

## Run ID Generation

### Deterministic Hashing
**Formula**: `run_id = sha1(canonical_json(knobs) + prompt_text)`

**Knobs included in hash**:
- `product_id`
- `material_type`
- `engine`
- `temperature_label`
- `time_of_day_label`
- `repetition_id`
- `trap_flag`
- `prompt_text` (rendered Jinja2 template)

**Excluded from hash** (non-deterministic):
- Timestamps (`timestamp_utc`, `started_at`, `completed_at`)
- Session IDs
- Account IDs
- Execution metadata

**Purpose**: Ensures identical experimental conditions → identical run_id → idempotent execution

---

## File Structure

### Product YAMLs
```
products/
├── smartphone_mid.yaml
├── cryptocurrency_corecoin.yaml
└── supplement_melatonin.yaml
```

**Schema**:
```yaml
product_id: string
name: string
region: string
specs: list[str]
authorized_claims: list[str]
prohibited_or_unsupported_claims: list[str]
disclaimers: list[str]
```

### Templates
```
prompts/
├── digital_ad.j2
├── organic_social_posts.j2
├── faq.j2
├── spec_document_facts_only.j2
└── blog_post_promo.j2
```

**Template variables**:
- `{{ name }}` - Product name
- `{{ region }}` - Target region
- `{{ specs }}` - List of specifications
- `{{ authorized_claims }}` - List of approved claims
- `{{ disclaimers }}` - List of required disclaimers
- `{{ trap_flag }}` - Boolean for trap experiments

### Results
```
results/
└── experiments.csv  # Single source of truth
```

**CSV Schema**:
```
run_id                    # SHA-1 hash (deterministic)
product_id                # Product slug
material_type             # Template filename
engine                    # LLM provider
temperature_label         # Sampling temperature
time_of_day_label         # Temporal label
repetition_id             # Replication index (1-3)
trap_flag                 # Boolean (false for base matrix)
prompt_path               # outputs/prompts/{run_id}.txt
output_path               # outputs/{run_id}.txt
status                    # pending | completed
started_at                # ISO timestamp (execution start)
completed_at              # ISO timestamp (execution end)
model                     # Actual model used
prompt_tokens             # Input token count
completion_tokens         # Output token count
total_tokens              # Sum of prompt + completion
finish_reason             # Completion status
```

### Outputs
```
outputs/
├── prompts/
│   └── {run_id}.txt     # Rendered prompt sent to LLM
└── {run_id}.txt         # Generated marketing material
```

---

## Matrix Generation

### Command
```bash
python -m runner.generate_matrix
```

**Dry run** (print first 5 run_ids without file writes):
```bash
python -m runner.generate_matrix --dry-run
```

### Guarantees
1. **No collisions**: All 1,620 run_ids are unique
2. **Deterministic**: Same factors → same run_id
3. **Idempotent**: Re-running skips existing rows/files
4. **Prompt persistence**: All prompts saved to `outputs/prompts/` during generation

---

## Execution

### Batch Runner
```bash
# Run all pending jobs
python -m runner.run_job batch

# Filter by time of day
python -m runner.run_job batch --time-of-day morning

# Filter by engine
python -m runner.run_job batch --engine openai

# Resume incomplete runs
python -m runner.run_job batch --resume
```

### Orchestrator (Automated)
```bash
# Manual run with time filter
python orchestrator.py run --time-of-day afternoon

# Automated scheduling (8am, 3pm, 9pm CET)
python orchestrator.py schedule

# Check status
python orchestrator.py status
```

---

## Constraints

### CSV-First Architecture
- `results/experiments.csv` is the **single source of truth**
- No SQLite or other databases
- Easy analysis in Excel, Google Sheets, pandas

### Status Tracking
- `pending`: Job not yet executed
- `completed`: Job finished successfully
- Re-running is safe: only `pending` jobs are processed

### Idempotency
- Matrix generation: Skip if row exists, create missing files
- Job execution: Update existing rows, preserve completed runs
- Safe to interrupt and resume at any time

---

## Dependencies

### Core Libraries
```
jinja2              # Template rendering
pyyaml              # Product YAML parsing
typer               # CLI framework
```

### LLM Providers
```
openai              # OpenAI API client
google-generativeai # Google Gemini API
mistralai           # Mistral AI API
anthropic           # Anthropic Claude API
```

### Analysis (Phase 2)
```
pydantic            # Data validation
pandas              # CSV manipulation
numpy               # Numerical operations
rapidfuzz           # Fuzzy string matching
pint                # Unit conversion
scipy               # Statistical tests
statsmodels         # Advanced statistics
matplotlib          # Plotting
```

### Utilities
```
tqdm                # Progress bars
rich                # Terminal formatting
python-dotenv       # Environment variables
apscheduler         # Scheduling
pytz                # Timezone support
```

---

## Version History

- **2025-10-08**: Initial freeze (3 products, 4 engines, 1,620 runs)
- **Future**: Expand to 5 products (2,700 runs)

---

## Notes

1. **Bias experiments**: Trap flag runs (`trap=true`) are a **separate batch** not included in base matrix
2. **Temporal labels**: `time_of_day` is used for scheduling and drift analysis, not actual execution time
3. **Repetitions as days**: Treat `repetition_id` as "day 1/2/3" labels for variance analysis
4. **Region locked**: All products use `US` region; international expansion requires separate matrix
5. **Model updates**: Update `config.py::ENGINE_MODELS` to change models; run_ids will regenerate
