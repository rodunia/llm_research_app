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
- **`main.py`**: Interactive CLI application orchestrating:
  1. API key initialization from `.env` (via `python-dotenv`)
  2. Session setup (session_id, account_id)
  3. Multi-provider LLM query dispatcher (`query_llm()` routes to `query_openai()`, `query_google()`, or `query_anthropic()`)
  4. Interactive conversation loop with temperature overrides
  5. CSV logging with detailed metadata (`results.csv`)

### Batch Processing System
- **`orchestrator.py`**: Automated job scheduler for running experimental batches
- **`runner/`**: Batch processing modules with robust retry logic and error handling
  - `runner/engines/`: Provider-specific clients (OpenAI, Google, Anthropic, Mistral)
  - `runner/run_job.py`: Batch execution with progress tracking
  - `runner/generate_matrix.py`: Experimental matrix generation
- **`core/storage.py`**: SQLite database for storing experiment results with ACID guarantees

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

# Run interactive CLI
python main.py

# Run test script
python test_run.py

# Run batch processing
python orchestrator.py
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

- **Dual System Architecture**: The project has two separate systems:
  - **Interactive CLI** (`main.py`): For manual experimentation with CSV logging
  - **Batch System** (`orchestrator.py` + `runner/`): For automated batch processing with SQLite storage
- **API key validation**: App filters available model configurations based on loaded API keys
- **Provider field**: Every model configuration MUST include `"provider"` field ("openai", "google", "anthropic", or "mistral")
- **Parameter overrides**: Use `get_model_config(model_key, **overrides)` for runtime temperature/token limit changes
- **Storage**: Interactive CLI uses CSV; batch system uses SQLite (`core/storage.py`)
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
