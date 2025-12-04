---
title: LLM Research App
emoji: 🔬
colorFrom: red
colorTo: purple
sdk: streamlit
sdk_version: 1.40.1
app_file: app.py
pinned: false
license: mit
---

# LLM Research Application

Systematic experimentation platform for comparing LLM outputs across multiple providers (OpenAI, Google Gemini, Anthropic Claude, Mistral) with controlled parameters and comprehensive logging.

## Quick Start

###1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

Create `.env` file:

```bash
OPENAI_API_KEY="your_key_here"
GOOGLE_API_KEY="your_key_here"
MISTRAL_API_KEY="your_key_here"
```

### 3. Generate Experimental Matrix

```bash
python -m runner.generate_matrix
```

This creates 1,215 experimental runs (3 products × 5 templates × 3 times × 3 temps × 3 reps × 3 engines).

### 4. Run Experiments

**Option A: Manual execution (recommended for first run)**

```bash
# Run morning subset (405 runs)
python orchestrator.py run --time-of-day morning

# Check status
python orchestrator.py status

# Run afternoon subset
python orchestrator.py run --time-of-day afternoon

# Run evening subset
python orchestrator.py run --time-of-day evening
```

**Option B: Full pipeline**

```bash
python orchestrator.py full --time-of-day morning
```

**Option C: Automated scheduling**

```bash
# Start scheduler (runs automatically at 8 AM, 3 PM, 9 PM CET)
python orchestrator.py schedule
```

### 5. Analyze Results

```bash
# Run evaluation and analytics
python orchestrator.py analyze

# Generate validation sample
python orchestrator.py sample
```

---

## Application Workflow

### 1. Matrix Generation

The application automatically generates all combinations:

- **3 products**: `smartphone_mid`, `cryptocurrency_corecoin`, `supplement_melatonin`
- **5 materials**: digital_ad, organic_social_posts, faq, spec_document_facts_only, blog_post_promo
- **3 times**: morning, afternoon, evening
- **3 temperatures**: 0.2, 0.6, 1.0
- **3 repetitions**: 1, 2, 3 (representing different days)
- **3 engines**: openai, google, mistral

**Total**: 1,215 runs (scales to 2,025 with 5 products)

### 2. Prompt Rendering

For each combination:
- Loads product YAML (specs, authorized claims, disclaimers)
- Loads Jinja2 template
- Renders final prompt text
- Saves to `outputs/prompts/{run_id}.txt`

### 3. Deterministic IDs

Every run gets a unique `run_id` (SHA1 hash of parameters + prompt text).
**Idempotent**: Same inputs → same ID → skip if already completed.

### 4. LLM Execution

Sends prompts to engines with configured parameters.
Records:
- Output text (`outputs/{run_id}.txt`)
- Token counts, finish reason
- Execution timestamps
- Model configuration

### 5. Evaluation (LLM-Free)

Automatic evaluator checks outputs against verified product data:
- **Supported** (factually correct)
- **Contradicted**
- **Unsupported**
- **Ambiguous**

Also detects:
- Numeric/unit errors
- Overclaim rate
- Exaggeration bias

### 6. Analytics

Generates reports:
- `analysis/engine_comparison.csv` - Accuracy and bias by engine
- `analysis/drift_analysis.csv` - Consistency over repetitions
- `analysis/temperature_effects.csv` - Temperature sensitivity
- `analysis/product_breakdown.csv` - Performance by product × material

### 7. Manual Validation

Stratified sample (~198 runs, ~22 per engine × product) for QA review:
- `validation/labels_to_fill.csv`

---

## Architecture

```
orchestrator.py          # Master pipeline controller
├── runner/
│   ├── generate_matrix.py   # Create experimental matrix
│   ├── run_job.py            # Execute LLM calls
│   ├── render.py             # Jinja2 template rendering
│   └── engines/              # Provider clients (OpenAI, Google, Mistral)
├── analysis/
│   ├── evaluate.py           # LLM-free claim screening
│   ├── bias_screen.py        # Bias detection
│   ├── metrics.py            # Metric calculations
│   └── reporting.py          # Analytics reports
├── validation/
│   └── make_sample.py        # Stratified sampling
├── config.py             # Central configuration
└── products/             # Product YAML files
```

---

## Commands Reference

### Orchestrator

```bash
# Execute runs for specific time of day
python orchestrator.py run --time-of-day morning

# Full pipeline (generate → execute → analyze)
python orchestrator.py full --time-of-day evening

# Analysis only
python orchestrator.py analyze

# Validation sampling
python orchestrator.py sample

# Check pipeline status
python orchestrator.py status

# Start scheduler (automatic 3x/day)
python orchestrator.py schedule
```

### Individual Components

```bash
# Matrix generation
python -m runner.generate_matrix
python -m runner.generate_matrix --dry-run  # Preview first 5 runs

# Execution
python -m runner.run_job batch
python -m runner.run_job batch --engine openai  # Filter by engine

# Evaluation
python -m analysis.evaluate

# Analytics
python -m analysis.reporting
python -m analysis.reporting --plots  # Include visualizations

# Validation sampling
python -m validation.make_sample --n-per-stratum 22
```

---

## Scheduling (Automatic Execution)

### Option 1: APScheduler (Recommended)

```bash
python orchestrator.py schedule
```

Runs automatically at:
- **Morning**: 8:00 AM CET
- **Afternoon**: 3:00 PM CET
- **Evening**: 9:00 PM CET

### Option 2: Cron (Linux/Mac)

```bash
crontab -e
```

Add:

```cron
# Morning run (8 AM CET = 7 AM UTC in winter, 6 AM UTC in summer)
0 7 * * * cd /path/to/app && /path/to/python orchestrator.py run --time-of-day morning

# Afternoon run (3 PM CET)
0 14 * * * cd /path/to/app && /path/to/python orchestrator.py run --time-of-day afternoon

# Evening run (9 PM CET)
0 20 * * * cd /path/to/app && /path/to/python orchestrator.py run --time-of-day evening
```

**Note**: Adjust UTC offset for CET/CEST timezone changes.

### Option 3: systemd timers (Linux)

Create service file: `/etc/systemd/system/llm-morning.service`

```ini
[Unit]
Description=LLM Research Morning Run

[Service]
Type=oneshot
WorkingDirectory=/path/to/app
ExecStart=/path/to/python orchestrator.py run --time-of-day morning
User=your_user
```

Create timer file: `/etc/systemd/system/llm-morning.timer`

```ini
[Unit]
Description=LLM Research Morning Timer

[Timer]
OnCalendar=*-*-* 08:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable:

```bash
sudo systemctl enable --now llm-morning.timer
```

---

## Data Structure

### results/results.csv

Main results table with columns:

```
timestamp_utc, product_id, material_type, engine, time_of_day_label,
temperature_label, repetition_id, trap_flag, run_id, output_path,
prompt_len, output_len, status, model, prompt_tokens, completion_tokens,
total_tokens, finish_reason, completed_at
```

### analysis/ Directory

- `per_run.json` - Individual run evaluations
- `engine_comparison.csv` - Engine performance metrics
- `drift_analysis.csv` - Consistency analysis
- `temperature_effects.csv` - Temperature sensitivity
- `product_breakdown.csv` - Product × material performance

### validation/ Directory

- `labels_to_fill.csv` - Manual QA sample

---

## Configuration

### config.py

Central configuration defining:
- Products, materials, times, temperatures, repetitions, engines
- Model configurations (provider-specific parameters)
- User accounts

### Product YAMLs (products/)

Each product file contains:
- `product_id`
- `specs` (verified facts)
- `authorized_claims`
- `prohibited_or_unsupported_claims`

---

## Troubleshooting

### "Matrix not found"

```bash
python -m runner.generate_matrix
```

### "No completed runs"

Ensure LLM execution completed:

```bash
python orchestrator.py status
python orchestrator.py run --time-of-day morning
```

### "Evaluation failed"

Check that output files exist in `outputs/`:

```bash
ls -l outputs/ | head
```

### API errors

Verify API keys in `.env` and check provider quotas.

---

## Extending the App

### Adding a New Product

1. Create `products/new_product.yaml`
2. Add product ID to `config.PRODUCTS`
3. Regenerate matrix: `python -m runner.generate_matrix`

### Adding a New Template

1. Create `prompts/new_template.j2`
2. Add filename to `config.MATERIALS`
3. Regenerate matrix

### Adding a New Engine

1. Create `runner/engines/new_engine_client.py`
2. Add to `runner/run_job.py::call_engine()`
3. Add to `config.ENGINES`
4. Add API key to `.env`

---

## License

Internal research tool.
