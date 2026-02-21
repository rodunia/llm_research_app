# AI Agent Guidelines for LLM Research Application

This file provides instructions for AI coding assistants (GitHub Copilot, Cursor, etc.) working on this repository.

## Project Overview

**Purpose**: Research application for systematic LLM compliance testing via Glass Box Audit.

**Key capabilities:**
1. Batch generation of marketing materials using multiple LLM providers (OpenAI, Google, Mistral, Anthropic)
2. Compliance auditing via two-stage pipeline (GPT-4o-mini extraction + RoBERTa NLI validation)
3. 100% detection of compliance violations (validated on 30-file pilot study)

## Project Structure

```
llm_research_app/
├── config.py                  # Central configuration (models, products, experiments)
├── orchestrator.py            # Master workflow CLI (run, analyze, status)
├── runner/                    # Batch LLM generation
│   ├── engines/              # Provider-specific clients (openai, google, mistral, anthropic)
│   ├── run_job.py            # Execute LLM jobs
│   └── generate_matrix.py   # Create experimental matrix
├── analysis/                  # Compliance auditing
│   ├── glass_box_audit.py   # Main audit pipeline (GPT-4o + RoBERTa)
│   └── semantic_filter.py   # Pre-filtering (74% FP reduction)
├── scripts/                   # Analysis and utilities
│   ├── detection_analysis_robust.py  # Verify detection rates
│   ├── rerun_pilot_audits.sh         # Reproduce pilot study
│   └── add_pilot_to_experiments.py   # Setup helper
├── products/                  # Product specifications (YAML)
│   ├── cryptocurrency_corecoin.yaml
│   ├── smartphone_mid.yaml
│   └── supplement_melatonin.yaml
├── pilot_study/              # 30 validation files with intentional errors
│   ├── corecoin/files/
│   ├── smartphone/files/
│   └── melatonin/files/
├── templates/                # Jinja2 templates for marketing materials
├── outputs/                  # LLM-generated materials (gitignored)
└── results/
    ├── experiments.csv       # Single source of truth (all runs)
    ├── pilot_individual/     # 30 audit CSVs (tracked for reproducibility)
    └── PILOT_STUDY_FINAL_100PCT.md  # Final validation report
```

## Key Workflows

### 1. Running LLM Experiments

```bash
# Generate experimental matrix (1,620 runs)
python -m runner.generate_matrix

# Check status
python orchestrator.py status

# Run batch experiments
python orchestrator.py run --time-of-day morning

# Test single run
python test_run.py
```

### 2. Running Glass Box Audit

```bash
# Audit a single file
python3 analysis/glass_box_audit.py --run-id <run_id>

# Batch audit with semantic filtering
python3 analysis/glass_box_audit.py --limit 100 --use-semantic-filter

# Resume from checkpoint
python3 analysis/glass_box_audit.py --resume
```

### 3. Reproducing Pilot Study (100% Detection)

```bash
# Copy pilot files to outputs/
cp pilot_study/*/files/*.txt outputs/

# Add to experiments.csv
python3 scripts/add_pilot_to_experiments.py

# Run all 30 audits
bash scripts/rerun_pilot_audits.sh

# Verify detection rate
python3 scripts/detection_analysis_robust.py
# Expected: 30/30 (100%)
```

## Configuration Files

### config.py
- **Location**: Root directory
- **Purpose**: Central configuration for experiments
- **Key sections**:
  - `PRODUCTS`: Product IDs
  - `ENGINES`: LLM providers
  - `ENGINE_MODELS`: Model mappings (e.g., openai → gpt-4o-mini)
  - `MATERIALS`: Jinja2 template names
  - `TEMPS`: Temperature values (0.2, 0.6, 1.0)

**Important**: All engine clients read models from `ENGINE_MODELS` - no hardcoded model names.

### Product YAMLs (products/*.yaml)
- **Structure**:
  - `specs`: Technical specifications
  - `authorized_claims`: Pre-approved marketing claims
  - `prohibited_or_unsupported_claims`: Claims that must NOT appear
  - `mandatory_statements`: Required disclaimers
  - `safety_warnings`: Required warnings

- **Used by**: NLI judge in `analysis/glass_box_audit.py` for contradiction detection

### experiments.csv
- **Location**: `results/experiments.csv`
- **Purpose**: Single source of truth for all LLM runs
- **Schema**: run_id, product_id, engine, temperature, material_type, status, tokens, timestamps
- **Format**: CSV (Excel/Google Sheets compatible)

## Critical Code Sections

### 1. Glass Box Audit Pipeline (analysis/glass_box_audit.py)

**ATOMIZER_SYSTEM_PROMPT** (lines ~131-183):
- **Critical for 100% detection**: Instructs GPT-4o-mini to extract operational policies and ALL parts of compound sentences
- **Do NOT modify** without validation - this prompt achieved 90% → 100% detection improvement
- Key instruction: "Extract ALL parts of compound sentences - do NOT omit secondary clauses"

**NLIJudge.verify_claim()** (lines ~260-392):
- Cross-encoder NLI model (RoBERTa-base) detects contradictions
- Uses semantic similarity pre-filtering when enabled
- Returns violation + confidence score (threshold: 0.90)

### 2. Provider Clients (runner/engines/)

All clients must implement:
```python
def generate(prompt: str, temperature: float, max_tokens: int) -> dict:
    """Returns: {output_text, finish_reason, prompt_tokens, completion_tokens, total_tokens, model}"""
```

**OpenAI**: Uses `max_completion_tokens` (not `max_tokens`)
**Google**: Manually counts tokens
**Mistral**: Standard API
**Anthropic**: Extracts text from content blocks

### 3. Detection Analysis (scripts/detection_analysis_robust.py)

**GROUND_TRUTH dictionary** (lines ~21-177):
- Maps file_key → intentional error + search_terms
- **Update when adding new pilot files**
- Uses fuzzy matching (not exact strings) to prevent false negatives

**fuzzy_search()** (lines ~200-231):
- Handles unit conversions (5 mcg → 5 ppm)
- Word order variations ("16 GB RAM" → "RAM configurations of 16 GB")
- Hyphenation ("light validator" → "light-validator")

## Coding Conventions

### Style
- **PEP 8**: 4-space indent, max line 100 characters
- **Naming**:
  - Functions/modules: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`
- **Type hints**: Required for public functions
- **Docstrings**: Required with Args/Returns sections

### File Organization
- **No `src/` directory** - modules at root level
- **Scripts**: Place utilities in `scripts/` (not `src/`)
- **Analysis**: Place audit-related code in `analysis/`
- **Tests**: Use `pytest` framework (if added)

### Configuration Management
- **Single source**: `config.py` for all experimental parameters
- **No hardcoding**: Read models from `ENGINE_MODELS`, not string literals
- **Secrets**: Use `.env` file (gitignored) loaded via `python-dotenv`
- **Provider params**: Use `get_model_config()` for provider-specific mappings

## Git Workflow

### Commits
- **Format**: `<type>: <description>` (e.g., "feat: add semantic filtering")
- **Types**: feat, fix, docs, refactor, test, chore
- **Scope**: Keep focused (one logical change per commit)
- **Body**: Explain "why" not "what" (code shows what)

### Pull Requests
- **Description**: Clear problem statement + solution approach
- **Verification**: Include commands to test changes
- **Config changes**: Document any `config.py` or YAML updates
- **Research impact**: Note if changes affect reproducibility

### Before Committing
1. Run linters (if configured)
2. Update `requirements.txt` if dependencies changed
3. Test changes locally
4. Ensure `.env` not committed

## Security & Best Practices

### Secrets Management
- **API keys**: Store in `.env` (never commit)
- **Required keys**: OPENAI_API_KEY (minimum for audit pipeline)
- **Optional keys**: GOOGLE_API_KEY, ANTHROPIC_API_KEY, MISTRAL_API_KEY
- **Loading**: Use `python-dotenv` in scripts

### Data Privacy
- **Never commit**: Raw datasets, credentials, PII
- **Gitignored**: `outputs/*.txt`, `results/*.jsonl`, `.env`
- **Tracked for reproducibility**: `results/pilot_individual/*.csv` (no PII)

### Performance
- **Batch processing**: Use `orchestrator.py run` for multiple files
- **Checkpointing**: Use `--resume` flag for long audits
- **Rate limits**: Scripts include retry logic with exponential backoff
- **Semantic filtering**: Enable with `--use-semantic-filter` (3x faster, 74% FP reduction)

## Testing

### Framework
- **Primary**: `pytest` (add as dev dependency if needed)
- **Location**: Root or `tests/` directory
- **Naming**: `test_*.py` files, `test_*` functions

### Critical Tests
1. **Provider integration**: All 4 engines return normalized response
2. **Claim extraction**: Prompt extracts compound sentences correctly
3. **NLI validation**: Detects contradictions at 90%+ threshold
4. **Detection analysis**: Fuzzy matching catches all variations

### Running Tests
```bash
pytest -q                # Run all tests
pytest -q --maxfail=1   # Stop on first failure
pytest tests/test_audit.py -v  # Verbose output for specific file
```

## Reproducibility Requirements

**For research integrity**, maintain:
1. ✅ All pilot files tracked (`pilot_study/*/files/*.txt`)
2. ✅ All audit results tracked (`results/pilot_individual/*.csv`)
3. ✅ Ground truth documented (`pilot_study/GROUND_TRUTH_ERRORS.md`)
4. ✅ Verification scripts (`scripts/detection_analysis_robust.py`)
5. ✅ Reproducibility guide (`REPRODUCIBILITY.md`)

**When modifying audit pipeline:**
1. Re-run pilot study (30 files)
2. Verify 100% detection maintained
3. Update `PILOT_STUDY_FINAL_100PCT.md` if metrics change
4. Document changes in commit message

## Common Tasks

### Adding a New Product
1. Create YAML: `products/<product_id>.yaml`
2. Update `config.py`: Add to `PRODUCTS` list
3. Create template variables if needed
4. Re-run matrix generation: `python -m runner.generate_matrix`

### Adding a New LLM Provider
1. Create client: `runner/engines/<provider>_client.py`
2. Implement `generate()` method
3. Update `config.py`: Add to `ENGINES` and `ENGINE_MODELS`
4. Test: `python test_run.py`

### Modifying Extraction Prompt
⚠️ **High risk** - affects detection rate
1. Edit `ATOMIZER_SYSTEM_PROMPT` in `analysis/glass_box_audit.py`
2. Test on pilot: `bash scripts/rerun_pilot_audits.sh`
3. Verify: `python3 scripts/detection_analysis_robust.py`
4. **Must maintain 100% detection** or document degradation

### Improving Detection Rate
1. Check missed errors: `scripts/detection_analysis_robust.py`
2. Analyze root cause (extraction failure vs. rule matching)
3. If extraction: Enhance prompt with examples
4. If matching: Expand product YAML prohibited_claims
5. Validate: Re-run pilot study

## Documentation

### For Users
- `README.md`: Project overview (if exists)
- `REPRODUCIBILITY.md`: How to reproduce 100% detection
- `results/PILOT_STUDY_FINAL_100PCT.md`: Research findings

### For Developers
- `CLAUDE.md`: Architecture and commands (this file's companion)
- `PROCESS_DETECTION_ANALYSIS.md`: Verification protocol
- `ANALYSIS_SECURITY_CHECKLIST.md`: Research readiness

### For Research
- `results/PILOT_STUDY_FINAL_100PCT.md`: Published results
- `pilot_study/GROUND_TRUTH_ERRORS.md`: All intentional errors
- `RECOMMENDATIONS_DETECTION_IMPROVEMENT.md`: Future work

## Key Metrics (Current)

- **Detection rate**: 30/30 (100%) on pilot
- **Processing time**: ~75 seconds per file
- **False positive rate**: 97% baseline, 26% with semantic filtering
- **Model**: RoBERTa-base (125M params) - optimal for speed/accuracy
- **Rejected**: DeBERTa-v3-large (304M params) - 10x worse FP rate

## Questions?

- See `CLAUDE.md` for detailed architecture
- See `REPRODUCIBILITY.md` for step-by-step validation
- See `PROCESS_DETECTION_ANALYSIS.md` for analysis protocol
