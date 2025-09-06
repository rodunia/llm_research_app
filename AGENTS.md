# Repository Guidelines

## Project Structure & Module Organization
- Root config: `config.py` centralizes model presets, prompts, and users. Keep this as the single source of truth for experiment settings.
- Dependencies: `requirements.txt` (Python 3.9+). Local env lives in `.venv/` (do not commit).
- IDE metadata: `.idea/` (ignore for code changes).
- Recommended when adding code: place Python sources under `src/llm_research_app/` and tests under `tests/`.

## Build, Test, and Development Commands
- Create venv: `python -m venv .venv && source .venv/bin/activate`
- Install deps: `pip install -r requirements.txt`
- Run scripts: create entry points under `src/` or `scripts/` that import from `config.py` (e.g., `python -m src.llm_research_app.run_experiment`).
- Lint/format (optional): use `ruff` and `black` if added to your dev environment.

## Coding Style & Naming Conventions
- Follow PEP 8; 4‑space indent; max line length 100.
- Names: modules and functions `snake_case`, classes `PascalCase`, constants `UPPER_SNAKE_CASE` (see `USER_ACCOUNTS`, `MODEL_CONFIGURATIONS`).
- Prefer type hints and docstrings for public functions.
- Keep configuration in `config.py`; avoid hardcoding API keys or parameters in code.

## Testing Guidelines
- Framework: `pytest` (add as a dev dependency).
- Naming: files `test_*.py`; functions `test_*`.
- Run: `pytest -q` (optionally `pytest -q --maxfail=1`).
- Aim for coverage on critical data paths (prompt selection, model routing, parameter merging).

## Commit & Pull Request Guidelines
- Commits: concise, imperative, scoped (e.g., "feat: add prompt registry"). Group related changes.
- PRs: include a clear description, linked issue, reproduction/verification steps, and any config changes (diffs to `config.py`). Add screenshots or logs if behavior changes.
- Before opening: run linters, tests, and ensure `requirements.txt` is updated when necessary.

## Security & Configuration Tips
- Secrets: store in `.env` (git‑ignored) and load via `python-dotenv`. Required keys typically include `OPENAI_API_KEY` and/or `GOOGLE_API_KEY`.
- Never commit credentials, tokens, or raw datasets. Redact sensitive output in examples.
- `MODEL_CONFIGURATIONS` must include a `provider` field ("openai" or "google"); keep names stable to preserve experiment reproducibility.

## Agent-Specific Instructions
- Do not modify `.venv/` or `.idea/`.
- Keep changes minimal and focused; update documentation when touching `config.py`.
