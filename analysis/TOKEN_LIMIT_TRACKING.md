# Tracking Google Gemini Token Limit Errors

## Current Status (May 2026)

**No token limit issues detected** in the completed experiment (1,618/1,620 runs).

### Diagnostic Results

```bash
python analysis/diagnose_gemini_tokens.py
```

**Key Findings:**
- **540 Google runs** (1 completed, 539 pending)
- **Max prompt**: 3,341 tokens (0.3% of 1M limit)
- **Max completion**: 139 tokens (1.7% of 8K limit)
- **No errors**: Zero token limit failures
- **No content filtering**: All runs passed safety checks

### Token Limits (Google Gemini 1.5)

| Model | Input Limit | Output Limit |
|-------|-------------|--------------|
| gemini-1.5-flash | 1,000,000 tokens | 8,192 tokens |
| gemini-1.5-pro | 2,000,000 tokens | 8,192 tokens |

## How to Track Token Limit Errors

### 1. Check Experiments CSV

The `experiments.csv` file tracks all token-related metadata:

```bash
# Check for any failed Google runs
grep "google" results/experiments.csv | grep -E "failed|pending"

# Get token statistics for Google runs
grep "google" results/experiments.csv | cut -d',' -f25-27 | head -20
```

**Relevant columns:**
- `prompt_tokens`: Input token count
- `completion_tokens`: Output token count
- `total_tokens`: Sum of both
- `error_type`: Error classification (`token_limit`, `rate_limit`, `api_error`, etc.)
- `finish_reason`: Completion status
- `retry_count`: Number of retry attempts

### 2. Run Diagnostic Script

```bash
# Full diagnostic report
python analysis/diagnose_gemini_tokens.py

# Show top 10 largest prompts
python analysis/diagnose_gemini_tokens.py --show-prompts

# Analyze different engine (e.g., OpenAI)
python analysis/diagnose_gemini_tokens.py --engine openai
```

**What it checks:**
- Status breakdown (completed/failed/pending)
- Error type distribution
- Token usage statistics (min/max/mean/median)
- High token runs (>90% of limit)
- Content filtering incidents

### 3. Error Handling in Code

**Location:** `runner/engines/google_client.py:221-241`

The Google client now explicitly catches token limit errors:

```python
except exceptions.InvalidArgument as e:
    error_msg = str(e).lower()
    if "token" in error_msg or "length" in error_msg or "context" in error_msg:
        error_type = "token_limit"
    else:
        error_type = "invalid_argument"
    raise
```

**Error types logged:**
- `token_limit`: Exceeded input/output token limits
- `rate_limit`: API quota exceeded
- `timeout`: Request timeout
- `invalid_argument`: Bad API parameters
- `api_error`: Generic API failure

### 4. Manual Investigation

If a run fails with `error_type=token_limit`:

```bash
# Find the run_id from experiments.csv
RUN_ID="abc123..."

# Check prompt size
wc -w outputs/prompts/${RUN_ID}.txt

# Read the prompt
cat outputs/prompts/${RUN_ID}.txt | head -50

# Check product YAML (may have large specs)
cat products/$(grep $RUN_ID results/experiments.csv | cut -d',' -f2).yaml
```

### 5. Prevention Strategies

If token limits become an issue:

**Option 1: Truncate prompts**
```python
# In runner/run_job.py
prompt_text = prompt_text[:50000]  # Limit to ~10K tokens
```

**Option 2: Use smaller product YAMLs**
```yaml
# In products/*.yaml - reduce specs and claims lists
authorized_claims:
  structure_function:
    - "Supports sleep quality"  # Keep top 10 only
```

**Option 3: Switch to Gemini Pro**
```python
# In config.py
ENGINE_MODELS = {
    "google": "gemini-1.5-pro",  # 2M input tokens
}
```

**Option 4: Use different engine**
```bash
# Run with OpenAI instead
python orchestrator.py run --engine openai
```

## Comparison Across Engines

| Engine | Model | Input Limit | Output Limit | Max Observed (This Study) |
|--------|-------|-------------|--------------|---------------------------|
| Google | gemini-1.5-flash | 1M tokens | 8K tokens | 3.3K prompt, 139 completion |
| OpenAI | gpt-4o-mini | 128K tokens | 16K tokens | ~4K prompt, ~2K completion |
| Mistral | mistral-large-latest | 128K tokens | 8K tokens | ~4K prompt, ~2K completion |

**Conclusion**: Google Gemini has the highest input limit (1M tokens) and is unlikely to hit token limits with current prompt sizes (~3-4K tokens).

## Future Monitoring

Add to regular workflow:

```bash
# After each batch of runs
python analysis/diagnose_gemini_tokens.py

# Check for new error types
grep -v "none" results/experiments.csv | cut -d',' -f40 | sort | uniq -c
```

## References

- Google AI documentation: https://ai.google.dev/gemini-api/docs/tokens
- Error handling code: `runner/engines/google_client.py:221-241`
- Diagnostic script: `analysis/diagnose_gemini_tokens.py`
- Experiments CSV: `results/experiments.csv`
