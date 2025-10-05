# Usage Guide

## Interactive Research App (main.py)

### Setup

1. **Create virtual environment** (if not exists):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure API keys**:
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

### Running the Interactive CLI

```bash
python main.py
```

**Workflow:**
1. Enter a session ID (e.g., `test_run_jan_2025`)
2. Select a user account from the list
3. Choose `[n]` for New Conversation
4. Select a model configuration (filtered by available API keys)
5. Set temperature (or press Enter for default)
6. Select a prompt from standardized prompts
7. Confirm and send
8. View response and metrics
9. Add tags and notes for annotation
10. Data saved to SQLite database (`data/results.db`)

**Menu Options:**
- `[n]` - Start a new conversation
- `[e]` - Export current session to CSV
- `[q]` - Quit

---

## Batch Processing Tools

### 1. Validate Products

```bash
python -m validation.validate_products
```

Validates all product YAML files for schema compliance and unit notation.

### 2. Render Prompts (Simple)

```bash
# Generate 15 prompts (3 products × 5 templates)
python -m runner.store_prompts

# Generate with trap flag enabled
python -m runner.store_prompts --trap
```

Output: `outputs/prompts/{hash}__{product_id}__{template}.txt`

### 3. Generate Smoke Test Matrix (Recommended)

```bash
# Dry run - preview run IDs
python -m runner.generate_matrix --dry-run

# Generate 15 normal prompts
python -m runner.generate_matrix

# Generate 15 trap prompts
python -m runner.generate_matrix --trap

# Generate both (30 prompts total)
python -m runner.generate_matrix --both
```

Output:
- Prompts: `outputs/prompts/{run_id}__{product_id}__{template}.txt`
- Index: `results/prompts_index.csv`

---

## Project Bootstrap

```bash
# Create directory structure and constants
./bootstrap_project.sh
```

Creates:
- 9 directories (products, prompts, runner, outputs, results, analysis, validation, lexicons, docs)
- `docs/experiment_constants.md` with frozen experimental parameters

---

## Database Management

### View Results

```bash
# Interactive SQL
sqlite3 data/results.db
sqlite> SELECT session_id, model_name, success, total_tokens FROM experiment_results;
sqlite> .quit
```

### Export to CSV

From Python:
```python
from core.storage import ExperimentDB
from pathlib import Path

db = ExperimentDB()
db.export_to_csv(Path("exports/my_results.csv"), session_id="my_session_id")
```

Or use the CLI `[e]` option during interactive session.

---

## Configuration

### Edit Experiment Constants

Edit `config.py`:

```python
# Add new model configuration
MODEL_CONFIGURATIONS = {
    "my-custom-model": {
        "provider": "openai",  # or "google" or "anthropic"
        "model_name": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 2048,
        # ... other params
    }
}

# Add new standardized prompt
STANDARDIZED_PROMPTS.append({
    "prompt_id": "MY-1",
    "prompt_text": "Your prompt here",
    "system_prompt": "System instructions",
})
```

### Add New Products

1. Create `products/my_product.yaml`:
   ```yaml
   product_id: my_product_id
   name: My Product Name
   region: US

   specs:
     - "Spec 1 with units (mg)."
     - "Spec 2 with units (GB)."

   authorized_claims:
     - Claim 1
     - Claim 2

   prohibited_or_unsupported_claims:
     - Not allowed claim

   disclaimers:
     - Disclaimer text
   ```

2. Validate:
   ```bash
   python -m validation.validate_products
   ```

### Add New Templates

1. Create `prompts/my_template.j2`:
   ```jinja2
   Create content for {{ name }} in {{ region }}.

   Use ONLY:
   - Specs: {{ specs | join('; ') }}
   - Claims: {{ authorized_claims | join('; ') }}

   {% if trap_flag %}
   [TRAP]: Add misleading content
   {% endif %}

   Disclaimers:
   {{ disclaimers | join('\n') }}
   ```

2. Use in generation:
   ```bash
   python -m runner.generate_matrix
   ```

---

## Troubleshooting

### API Key Issues
```
ERROR: No API keys found
```
→ Make sure `.env` file exists and contains valid API keys

### Import Errors
```
ModuleNotFoundError: No module named 'openai'
```
→ Activate venv: `source .venv/bin/activate`
→ Install deps: `pip install -r requirements.txt`

### Database Locked
```
sqlite3.OperationalError: database is locked
```
→ Close other connections to `data/results.db`
→ Only one write operation at a time

### Template Not Found
```
jinja2.TemplateNotFound: my_template.j2
```
→ Make sure template exists in `prompts/` directory
→ Check filename spelling

---

## Quick Reference

| Command | Description |
|---------|-------------|
| `python main.py` | Interactive research CLI |
| `python -m validation.validate_products` | Validate product YAMLs |
| `python -m runner.generate_matrix --both` | Generate full smoke matrix |
| `./bootstrap_project.sh` | Initialize project structure |
| `sqlite3 data/results.db` | Open database |

## Data Locations

- **Database**: `data/results.db` (SQLite)
- **CSV Exports**: `data/results_export.csv` (via CLI)
- **Prompts**: `outputs/prompts/` (generated prompts)
- **Index**: `results/prompts_index.csv` (experiment tracking)
