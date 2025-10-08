# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an LLM Research Application for conducting systematic experiments with multiple LLM providers (OpenAI, Google Gemini, Anthropic Claude, Mistral AI). The app provides automated batch processing for running product marketing material generation across different LLMs with controlled parameters, logging all results to CSV for analysis.

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

## Git Workflow

- Commit style: Concise, imperative, scoped (e.g., "feat: add prompt registry")
- Before committing: Run linters/tests, update `requirements.txt` if dependencies changed
- PRs: Include clear description, verification steps, document any `config.py` changes
