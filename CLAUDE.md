# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an LLM Research Application for conducting systematic experiments with multiple LLM providers (OpenAI, Google Gemini, Anthropic Claude, Mistral AI). The app provides automated batch processing for running product marketing material generation across different LLMs with controlled parameters, logging all results to CSV for analysis.

## Research Context

**Paper**: "Critical Risks and Reliability Challenges of Using ChatGPT for Marketing Content Generation"

**Research Questions**:
1. **People-pleasing bias**: Do LLMs generate overly positive marketing content that violates compliance rules?
2. **Induced errors and hallucinations**: How frequently do LLMs introduce factual inaccuracies in marketing materials?
3. **Temporal unreliability**: Do LLMs produce inconsistent outputs across different sessions and times of day?

**Why marketing content?**: AI marketing has the highest legal and social risk for companies:
- Incorrect medical claims (health supplements) → FDA violations
- Misleading financial claims (cryptocurrency) → SEC/CFTC violations
- False product specifications (consumer electronics) → FTC violations
- Regulatory non-compliance across multiple domains

**Experimental Design Rationale**:
- **3 products** (smartphone, cryptocurrency, health supplement): Different regulatory domains to test cross-industry reliability
- **Temperature variations** (0.2, 0.6, 1.0): Test deterministic vs creative outputs - does higher creativity increase hallucinations?
- **Time-of-day runs** (morning/afternoon/evening × 3 days = 9 time slots): Measure temporal consistency across sessions
- **Multiple engines** (OpenAI, Google, Anthropic, Mistral): Compare provider reliability and bias patterns
- **3 replications**: Statistical validation of consistency within same conditions
- **5 material types**: FAQ, digital ads, blog posts, social media, email - different content formats

**Glass Box Audit Role**: Systematically detect and quantify induced errors and compliance violations across 1,620 generated marketing materials (3 products × 5 materials × 3 temps × 3 reps × 4 engines × 3 time slots).

## Architecture

### Configuration-Driven Design
- **`config.py`**: Central configuration hub defining:
  - `PRODUCTS`: Product identifiers (smartphone_mid, cryptocurrency_corecoin, supplement_melatonin)
  - `MATERIALS`: Jinja2 template names (digital_ad.j2, organic_social_posts.j2, faq.j2, etc.)
  - `ENGINES`: LLM providers (openai, google, mistral, anthropic)
  - `ENGINE_MODELS`: Engine-to-model mapping (e.g., openai → gpt-4o-mini)
  - `TEMPS`: Temperature values for experimentation (0.2, 0.6, 1.0)
  - `TIMES`, `REPS`, `REGION`: Experimental factors

### Batch Processing System
- **`orchestrator.py`**: Master workflow orchestrator with CLI commands:
  - `run`: Execute pending LLM runs (filtered by time-of-day)
  - `analyze`: Run evaluation and analytics
  - `status`: Show pipeline statistics
  - `schedule`: Automated scheduling at configured times
- **`runner/`**: Core batch processing modules
  - `runner/generate_matrix.py`: Generate experimental matrix (creates experiments.csv)
  - `runner/run_job.py`: Execute LLM jobs with progress tracking
  - `runner/render.py`: Jinja2 template rendering with product YAMLs
  - `runner/engines/`: Provider-specific clients with retry logic
    - `openai_client.py`: OpenAI GPT models
    - `google_client.py`: Google Gemini models
    - `mistral_client.py`: Mistral AI models
    - `anthropic_client.py`: Anthropic Claude models

### Provider Integration
Each provider has a dedicated client handling API-specific schemas:
- **OpenAI**: Uses `openai.chat.completions.create()`, supports `max_completion_tokens`
- **Google**: Uses `genai.GenerativeModel()`, manually counts tokens
- **Mistral**: Uses `mistralai.Mistral().chat.complete()`
- **Anthropic**: Uses `anthropic.Anthropic().messages.create()`, extracts text from content blocks

All clients read model names from `ENGINE_MODELS` config and return normalized response dict: `output_text`, `finish_reason`, `prompt_tokens`, `completion_tokens`, `total_tokens`, `model`.

### Data Storage (CSV-First)
- **`results/experiments.csv`**: Single source of truth for all experimental runs
  - Tracks: run_id, product_id, engine, temperature, status, tokens, timestamps
  - CSV format for easy Excel/Google Sheets analysis
- **`outputs/{run_id}.txt`**: LLM-generated marketing materials
- **`outputs/prompts/{run_id}.txt`**: Rendered prompts sent to LLMs
- **Analysis outputs**: Also exported as CSV files

## Development Commands

### Setup
```bash
# Create virtual environment
python -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Activate venv
source .venv/bin/activate

# Test single run
python test_run.py

# Test comprehensive (all materials × all engines)
python test_comprehensive.py

# Generate experimental matrix (1,620 runs)
python -m runner.generate_matrix

# Check pipeline status
python orchestrator.py status

# Run batch experiments
python orchestrator.py run --time-of-day morning

# View results
cat results/experiments.csv | head -10
```

### Environment Configuration
Create `.env` file in project root with API keys:
```
OPENAI_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
MISTRAL_API_KEY=your_key_here
```

## Coding Conventions

- Follow PEP 8: 4-space indent, max line length 100
- Naming: `snake_case` for functions/modules, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants
- Type hints and docstrings for public functions
- Keep all configuration in `config.py` (single source of truth)
- Provider-specific parameter handling: `get_model_config()` maps between generic and provider-specific names (e.g., `max_tokens` → `max_completion_tokens` for OpenAI)

## Important Notes

- **Single System Architecture**: Uses batch-only workflow via `orchestrator.py` + `runner/`
  - **Deprecated**: `main.py` (interactive CLI) archived - use `test_run.py` for manual testing
  - **Deprecated**: `core/storage.py` (SQLite) archived - CSV-first approach for non-programmer accessibility
- **Configuration-driven**: All experimental parameters defined in `config.py`
  - Models controlled via `ENGINE_MODELS` mapping
  - Engine clients automatically read from config (no hardcoded models)
- **CSV-first storage**: `results/experiments.csv` is single source of truth
  - Easy to analyze in Excel/Google Sheets
  - Tracks status (pending/completed), timestamps, tokens, models
- **Experimental matrix**: Currently 1,620 runs (3 products × 5 materials × 3 temps × 3 reps × 4 engines)
- **Security**: Never commit `.env`, credentials, or raw datasets

## Testing

Framework: `pytest` (add as dev dependency if not present)
```bash
# Run tests
pytest -q

# Run with early exit on failure
pytest -q --maxfail=1
```

## Glass Box Audit System (v2.1)

The project includes a compliance auditing pipeline for evaluating LLM-generated marketing materials.

### Architecture
- **Two-stage pipeline**: GPT-4o-mini extraction + RoBERTa-base NLI validation
- **Location**: `analysis/glass_box_audit.py`
- **Input**: Marketing materials in `outputs/` (referenced via `experiments.csv`)
- **Output**: `results/final_audit_results.csv` with violations and confidence scores

### Key Features
- **Atomic claim extraction**: Extracts ALL verifiable facts, operational policies, restrictions (including ALL parts of compound sentences)
- **NLI verification**: Cross-encoder model detects contradictions against product YAMLs
- **100% pilot detection**: Validated on 30 files with intentional errors
- **Semantic pre-filtering** (optional): 74% FP reduction via sentence embeddings

### Model Choice Rationale

**Why GPT-4o-mini for extraction?**
- **Cost-effective**: ~$0.002/file vs $0.10/file for GPT-4 (50x cheaper)
- **Sufficient performance**: Achieved 100% detection on 30-file pilot study
- **Prompt > Model**: Key insight - 90% → 100% detection improvement came from prompt engineering (adding "extract ALL parts of compound sentences"), not from using larger models
- **Not empirically validated**: No A/B testing against GPT-4, Claude, or Gemini for extraction task
- **Temperature 0**: Deterministic extraction ensures reproducibility across all 1,620 analyses

**Why RoBERTa-base for NLI validation?**
- **Optimal tradeoff**: 125M params, fast inference (~75 sec/file)
- **Empirically validated**: A/B tested against DeBERTa-v3-large (304M params)
- **DeBERTa rejected**: 10x worse false positive rate despite larger size
- **Key finding**: Architecture + prompt design > parameter scaling

**Design philosophy**: Prioritize cost, speed, and reproducibility over theoretical "state-of-the-art" without empirical justification. The 100% detection validates this approach.

### Running Glass Box Audit

```bash
# Audit a single file
python3 analysis/glass_box_audit.py --run-id <run_id>

# Audit with semantic filtering (recommended for production)
python3 analysis/glass_box_audit.py --run-id <run_id> --use-semantic-filter

# Batch audit (skip first N, limit to M files)
python3 analysis/glass_box_audit.py --skip 100 --limit 50

# Resume from checkpoint
python3 analysis/glass_box_audit.py --resume
```

### Pilot Study Validation

**Location**: `pilot_study/` contains 30 files with intentional errors for validation
- **Detection rate**: 30/30 (100%) ✅
- **Documentation**: `results/PILOT_STUDY_FINAL_100PCT.md`
- **Reproducibility**: `REPRODUCIBILITY.md` - full guide for peer review

**Key improvement (v2.1)**: Enhanced extraction prompt to capture operational policies and compound sentence clauses → 90% → 100% detection.

### Analysis Scripts

Located in `scripts/`:
- `detection_analysis_robust.py`: Verify detection rates with fuzzy matching
- `rerun_pilot_audits.sh`: Reproduce pilot study (30 files)
- `add_pilot_to_experiments.py`: Add pilot files to experiments.csv

### Product Specifications

**Location**: `products/*.yaml`
- Each product YAML contains: specs, authorized_claims, prohibited_claims, safety_warnings
- Used by NLI judge to detect contradictions
- Example: `products/cryptocurrency_corecoin.yaml` (most comprehensive)

## Git Workflow

- Commit style: Concise, imperative, scoped (e.g., "feat: add prompt registry")
- Before committing: Run linters/tests, update `requirements.txt` if dependencies changed
- PRs: Include clear description, verification steps, document any `config.py` changes

## Research Artifacts

For reproducibility and peer review:
- `REPRODUCIBILITY.md`: Complete guide for reproducing 100% detection
- `ANALYSIS_SECURITY_CHECKLIST.md`: Research readiness checklist
- `PROCESS_DETECTION_ANALYSIS.md`: Verification protocol (prevents false reporting)
- `results/pilot_individual/*.csv`: All 30 audit results (tracked in git)
