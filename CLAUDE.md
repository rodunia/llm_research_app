# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an LLM Research Application for conducting systematic experiments with multiple LLM providers (OpenAI, Google Gemini, Anthropic Claude). The app provides an interactive CLI for running standardized prompts across different models with controlled parameters, logging all results to CSV for analysis.

## Architecture

### Configuration-Driven Design
- **`config.py`**: Central configuration hub defining:
  - `USER_ACCOUNTS`: Researcher account identifiers
  - `MODEL_CONFIGURATIONS`: Provider-specific model presets with generation parameters
  - `STANDARDIZED_PROMPTS`: Reusable prompt templates with IDs
  - `get_model_config()`: Helper for runtime parameter overrides with provider-specific parameter mapping

### Main Application Flow
- **`.venv/main.py`**: Interactive CLI application orchestrating:
  1. API key initialization from `.env` (via `python-dotenv`)
  2. Session setup (session_id, account_id)
  3. Multi-provider LLM query dispatcher (`query_llm()` routes to `query_openai()`, `query_google()`, or `query_anthropic()`)
  4. Interactive conversation loop with temperature overrides
  5. CSV logging with detailed metadata (`results.csv`)

### Provider Integration
Each provider has a dedicated query function handling API-specific schemas:
- **OpenAI**: Uses `openai.chat.completions.create()`, supports `max_completion_tokens`
- **Google**: Uses `genai.GenerativeModel()`, manually counts tokens
- **Anthropic**: Uses `anthropic.Anthropic().messages.create()`, extracts text from content blocks

All providers return normalized response dict: `output_text`, `finish_reason`, `prompt_tokens`, `completion_tokens`, `total_tokens`.

### Data Collection
Results saved to CSV with fields: session_id, account_id, run_timestamp, repetition_id, prompt_id, model parameters (temperature, max_tokens, etc.), output_text, token usage, tags, researcher_notes.

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

# Run main script
python .venv/main.py
```

### Environment Configuration
Create `.venv/.env` with API keys:
```
OPENAI_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
```

## Coding Conventions

- Follow PEP 8: 4-space indent, max line length 100
- Naming: `snake_case` for functions/modules, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants
- Type hints and docstrings for public functions
- Keep all configuration in `config.py` (single source of truth)
- Provider-specific parameter handling: `get_model_config()` maps between generic and provider-specific names (e.g., `max_tokens` → `max_completion_tokens` for OpenAI)

## Important Notes

- **main.py location**: Currently located in `.venv/main.py` (unconventional but functional)
- **API key validation**: App filters available model configurations based on loaded API keys
- **Provider field**: Every model configuration MUST include `"provider"` field ("openai", "google", or "anthropic")
- **Parameter overrides**: Use `get_model_config(model_key, **overrides)` for runtime temperature/token limit changes
- **Results file**: Auto-created on first run with predefined CSV schema
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
