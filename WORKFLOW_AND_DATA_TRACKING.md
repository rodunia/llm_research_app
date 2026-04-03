# Complete Workflow and Data Tracking Documentation

**Date**: 2026-03-31
**For**: Fellow researchers
**Purpose**: Comprehensive documentation of actual workflow, research questions, and data tracking

---

## Research Questions (RQs)

### RQ1: People-Pleasing Bias
**Question**: Do LLMs generate overly positive marketing content that violates compliance rules?

**Hypothesis**: LLMs trained on helpful/harmless/honest principles may avoid negative information, leading to:
- Omission of mandatory warnings (e.g., FDA side effects)
- Overstatement of benefits
- Suppression of risks and limitations

**Measurement**:
- Compliance violations detected by Glass Box Audit
- Missing mandatory warnings vs product YAMLs
- Unauthorized positive claims

---

### RQ2: Induced Errors and Hallucinations
**Question**: How frequently do LLMs introduce factual inaccuracies in marketing materials?

**Hypothesis**: LLMs may fabricate claims when:
- Product specifications are incomplete
- Temperature is high (more creative)
- Marketing pressure conflicts with factual accuracy

**Measurement**:
- Hallucinated claims (not in product YAML)
- Contradicted specifications (detected by NLI model)
- False product features, capabilities, or certifications

---

### RQ3: Temporal Unreliability
**Question**: Do LLMs produce inconsistent outputs across different sessions and times of day?

**Hypothesis**: API-based LLMs may show variability due to:
- Model updates/version drift
- Server-side load balancing
- Time-of-day effects on API infrastructure

**Measurement**:
- Within-condition variance (3 replications per condition)
- Cross-session consistency
- Time-of-day effects (morning/afternoon/evening)
- Day-of-week patterns

---

## Experimental Design

### Pre-Registered Protocol
- **Total runs**: 1,620
- **Seed**: 42 (locked)
- **Mode**: stratified_7day_balanced
- **Date range**: March 17-23, 2026 (7 days)
- **Generated once**: Matrix is immutable after generation

### Factors (Independent Variables)

1. **Product** (3 levels):
   - `smartphone_mid`: Mid-range consumer electronics
   - `cryptocurrency_corecoin`: Digital currency trading
   - `supplement_melatonin`: Health supplement (3mg tablets)
   - **Why these?**: Different regulatory domains (FTC, SEC/CFTC, FDA)

2. **Material Type** (3 levels tracked for statistics):
   - `faq.j2`: Frequently Asked Questions
   - `digital_ad.j2`: Paid digital advertisements
   - `blog_post_promo.j2`: Promotional blog content
   - **Why these?**: Different content formats with varying compliance requirements

3. **Engine** (3 levels):
   - `openai`: GPT-4o (upgraded from gpt-4o-mini)
   - `google`: Gemini Flash (latest)
   - `mistral`: Mistral Large 2407
   - **Balance**: 540 runs per engine (exact)

4. **Temperature** (3 levels):
   - `0.2`: Low - deterministic, conservative
   - `0.6`: Medium - balanced creativity
   - `1.0`: High - maximum creativity
   - **Hypothesis**: Higher temperature → more hallucinations
   - **Balance**: 537-542 runs per temperature (±5)

5. **Time of Day** (3 levels):
   - `morning`: 7am-12pm
   - `afternoon`: 12pm-5pm
   - `evening`: 5pm-10pm
   - **Balance**: 540 runs per time slot (exact)

6. **Repetition** (3 levels):
   - Rep 1, Rep 2, Rep 3
   - **Purpose**: Measure within-condition reliability

7. **Day of Week** (7 levels):
   - Monday through Sunday
   - **Balance**: 231-232 runs per day

### Statistical Balance

**Perfect balance** (±0):
- Engine: 540/540/540
- Time slot: 540/540/540
- Engine×Time: 179-181 per cell

**Near balance**:
- Temperature: 537-542 (±5)
- Product: 528-546 (±20)
- Day of week: 231-232 (±1)

---

## Complete Workflow (Actual Implementation)

### Phase 1: Pre-Experiment Setup (ONE TIME ONLY)

```bash
# Step 1: Generate experimental matrix (DONE - March 28, 2026)
python scripts/test_randomizer_stratified.py --seed 42

# This creates:
# - results/experiments.csv (1,620 rows, all status='pending')
# - Columns: run_id, product_id, material_type, engine, temperature,
#           time_of_day_label, repetition_id, scheduled_datetime, etc.

# Step 2: Validate matrix (statistical checks)
python scripts/verify_canonical_matrix.py
# Exit code 0 = valid

# Step 3: Run R statistical validation (optional)
Rscript scripts/validate_matrix_r_stats.R
# Checks: balance, daily distribution, engine×time interaction
```

**IMPORTANT**: Matrix is generated ONCE and locked. Do NOT regenerate during experiments.

---

### Phase 2: Execute Experiments (ONGOING)

#### Workflow Per Run:

```
For each row in experiments.csv where status='pending':

1. READ row from CSV:
   - run_id (unique identifier)
   - product_id (e.g., 'smartphone_mid')
   - material_type (e.g., 'faq.j2')
   - engine (e.g., 'openai')
   - temperature (e.g., 0.6)
   - time_of_day_label (e.g., 'morning')
   - scheduled_datetime (e.g., '2026-03-17T10:09:00')

2. LOAD product specification:
   - Path: products/{product_id}.yaml
   - Contains: specs, authorized_claims, prohibited_claims, safety_warnings

3. RENDER prompt:
   - Template: prompts/{material_type} (Jinja2)
   - Input: product YAML data
   - Output: Final prompt text
   - Save to: outputs/prompts/{run_id}.txt

4. CALL LLM API:
   - Engine client (openai_client.py / google_client.py / mistral_client.py)
   - Parameters: temperature, max_tokens=2000, seed=12345
   - Record: started_at timestamp

5. RECEIVE response:
   - Extract: output_text, model, prompt_tokens, completion_tokens
   - Record: completed_at timestamp
   - Calculate: execution_duration_sec

6. SAVE output:
   - Path: outputs/{run_id}.txt
   - Content: Raw LLM-generated marketing material

7. UPDATE CSV row:
   - status: 'pending' → 'completed'
   - started_at, completed_at, date_of_run
   - model, model_version (actual model used)
   - prompt_tokens, completion_tokens, total_tokens
   - finish_reason (e.g., 'stop', 'length')
   - execution_duration_sec
   - output_path: outputs/{run_id}.txt

8. MOVE TO NEXT ROW
```

#### Execution Commands:

```bash
# Manual execution (filter by time of day)
python orchestrator.py run --time-of-day morning    # Runs 540 morning jobs
python orchestrator.py run --time-of-day afternoon  # Runs 540 afternoon jobs
python orchestrator.py run --time-of-day evening    # Runs 540 evening jobs

# Check status
python orchestrator.py status
# Shows: total runs, completed, pending, by engine, by product

# Resume incomplete runs (e.g., after API errors)
python orchestrator.py resume --time-of-day morning
```

---

### Phase 3: Glass Box Audit (POST-EXECUTION)

**After all 1,620 runs complete**, audit each output:

```bash
# Audit single file
python3 analysis/glass_box_audit.py --run-id {run_id}

# Batch audit (all files)
python3 analysis/glass_box_audit.py

# With semantic pre-filtering (recommended, 74% FP reduction)
python3 analysis/glass_box_audit.py --use-semantic-filter
```

#### Glass Box Workflow Per File:

```
For each outputs/{run_id}.txt:

1. EXTRACT claims:
   - Model: GPT-4o-mini (temperature=0)
   - Prompt: "Extract ALL verifiable facts, operational policies, restrictions"
   - Output: JSON list of atomic claims
   - Example: ["Product contains 3mg melatonin per tablet",
              "Suitable for vegans", "FDA approved"]

2. SEMANTIC FILTER (optional):
   - Embed claims + product YAML sentences (all-MiniLM-L6-v2)
   - Compute cosine similarity
   - Keep only claims with similarity > 0.3 (likely relevant)
   - Effect: 74% false positive reduction

3. NLI VERIFICATION:
   - Model: RoBERTa-base cross-encoder
   - For each claim, check against product YAML
   - Output: 'entailment', 'contradiction', 'neutral'
   - Threshold: contradiction score > 0.5 = violation

4. CLASSIFY violations:
   - Hallucination (not in YAML)
   - Contradiction (conflicts with YAML)
   - Missing warning (required but omitted)
   - Unauthorized claim (in prohibited_claims)

5. SAVE results:
   - results/final_audit_results.csv
   - Columns: run_id, claim, violation_type, confidence, severity
```

---

## Data Tracking (What We Capture)

### Immutable Columns (From Matrix Generation)
These are set ONCE during matrix generation and NEVER change:

1. **run_id**: Unique identifier (SHA1 hash)
2. **product_id**: Product identifier
3. **material_type**: Marketing material template
4. **engine**: LLM provider
5. **temperature**: Sampling temperature
6. **time_of_day_label**: Time slot (morning/afternoon/evening)
7. **repetition_id**: Replication number (1, 2, or 3)
8. **scheduled_datetime**: When run should execute
9. **scheduled_hour_of_day**: Hour (0-23)
10. **scheduled_day_of_week**: Day name
11. **matrix_randomization_seed**: 42
12. **matrix_randomization_mode**: 'stratified_7day_balanced'
13. **trap_flag**: False (no traps in main experiment)

### Runtime Metadata (Updated During Execution)
These are EMPTY initially and filled during experiment runs:

14. **status**: 'pending' → 'completed' (or 'failed')
15. **started_at**: ISO timestamp when API call started
16. **completed_at**: ISO timestamp when API call completed
17. **date_of_run**: Date (YYYY-MM-DD)
18. **execution_duration_sec**: Seconds taken for API call
19. **session_id**: Optional session identifier
20. **model**: Actual model used (e.g., 'gpt-4o-2024-08-06')
21. **model_version**: Model version string
22. **prompt_tokens**: Tokens in prompt
23. **completion_tokens**: Tokens in response
24. **total_tokens**: Sum of prompt + completion tokens
25. **finish_reason**: Why generation stopped ('stop', 'length', etc.)
26. **output_path**: Path to output file (outputs/{run_id}.txt)

### Configuration Snapshot (Updated During Execution)

27. **prompt_id**: Prompt template identifier
28. **prompt_text_path**: Path to rendered prompt
29. **max_tokens**: 2000 (fixed)
30. **seed**: 12345 (API reproducibility seed)
31. **top_p**: None (use API default)
32. **frequency_penalty**: None (use API default)
33. **presence_penalty**: None (use API default)
34. **account_id**: 'researcher_primary'
35. **config_fingerprint**: SHA256 of config.py at execution time
36. **system_prompt**: Empty (templates use single-turn prompts)

---

## File Structure

```
llm_research_app/
│
├── results/
│   ├── experiments.csv              # Master tracking CSV (1,620 rows)
│   ├── experiments_for_r.csv        # R-compatible export
│   └── final_audit_results.csv      # Glass Box audit results
│
├── outputs/
│   ├── {run_id}.txt                 # LLM-generated materials (1,620 files)
│   └── prompts/
│       └── {run_id}.txt             # Rendered prompts (1,620 files)
│
├── products/
│   ├── smartphone_mid.yaml          # Product specifications
│   ├── cryptocurrency_corecoin.yaml
│   └── supplement_melatonin.yaml
│
├── prompts/
│   ├── faq.j2                       # Jinja2 templates
│   ├── digital_ad.j2
│   └── blog_post_promo.j2
│
├── orchestrator.py                   # Master workflow controller
├── config.py                         # Experimental parameters
│
├── runner/
│   ├── generate_matrix.py           # Matrix generation
│   ├── run_job.py                   # Execute single run
│   ├── render.py                    # Prompt rendering
│   └── engines/
│       ├── openai_client.py         # OpenAI API
│       ├── google_client.py         # Google Gemini API
│       └── mistral_client.py        # Mistral API
│
└── analysis/
    └── glass_box_audit.py           # Compliance auditing
```

---

## Statistical Analysis Variables

### Dependent Variables (DVs)

1. **Compliance violations** (count)
   - Hallucinations
   - Contradictions
   - Missing warnings
   - Unauthorized claims

2. **Token usage**
   - prompt_tokens
   - completion_tokens
   - total_tokens

3. **Generation duration**
   - execution_duration_sec

4. **Within-condition reliability**
   - Variance across 3 replications
   - Semantic similarity between reps

### Independent Variables (IVs)

1. **product_id** (3 levels)
2. **engine** (3 levels)
3. **temperature** (3 levels)
4. **time_of_day_label** (3 levels)
5. **scheduled_day_of_week** (7 levels)
6. **material_type** (3 levels)

### Interaction Effects to Test

- Engine × Temperature
- Engine × Product
- Temperature × Time of Day
- Engine × Time of Day (test temporal unreliability hypothesis)

---

## Key Invariants (MUST NOT CHANGE)

1. **Matrix is immutable**: Once generated, never regenerate during experiments
2. **Seed is fixed**: matrix_randomization_seed = 42 (reproducibility)
3. **Balance is locked**: Engine and time slot counts must stay 540/540/540
4. **Product YAMLs are frozen**: Changes invalidate audit results
5. **Templates are locked**: Changes invalidate comparisons

---

## Quality Checks

### Before Running Experiments:
```bash
# 1. Validate matrix structure
python scripts/verify_canonical_matrix.py

# 2. Validate statistical balance
Rscript scripts/validate_matrix_r_stats.R

# 3. Check product YAMLs exist
ls products/*.yaml  # Should show 3 files

# 4. Check templates exist
ls prompts/*.j2     # Should show 3 files

# 5. Test single run
python orchestrator.py run --time-of-day morning --max-jobs 1
```

### During Experiments:
```bash
# Check progress
python orchestrator.py status

# Monitor for failures
grep -c "completed" results/experiments.csv
grep -c "failed" results/experiments.csv

# Check output files
ls outputs/*.txt | wc -l  # Should grow toward 1,620
```

### After Experiments:
```bash
# Verify all runs completed
python -c "
import pandas as pd
df = pd.read_csv('results/experiments.csv')
print(f'Completed: {(df.status == \"completed\").sum()}/1620')
print(f'Failed: {(df.status == \"failed\").sum()}')
"

# Run Glass Box Audit
python3 analysis/glass_box_audit.py --use-semantic-filter

# Check audit results
wc -l results/final_audit_results.csv
```

---

## Important Notes for Researchers

1. **CSV is single source of truth**: All experiment tracking is in `results/experiments.csv`

2. **Files are separate**: LLM outputs are saved to `outputs/` directory, NOT in CSV

3. **Matrix is pre-generated**: Randomization happens ONCE before experiments, not during execution

4. **Execution updates CSV**: When runs complete, CSV rows are updated with metadata (tokens, timestamps, model versions)

5. **API keys required**: Set in `.env` file (OPENAI_API_KEY, GOOGLE_API_KEY, MISTRAL_API_KEY)

6. **Temperature caveat**: LLM temperature (0.2/0.6/1.0) controls creativity. Extraction uses temperature=0 (deterministic).

7. **Temporal scheduling**: Can filter by time_of_day to run morning/afternoon/evening batches separately

8. **Replication**: Each condition has 3 repetitions for within-condition reliability analysis

9. **Glass Box is post-hoc**: Compliance audit runs AFTER experiments complete (not during)

10. **Model versions matter**: We track actual model versions (e.g., gpt-4o-2024-08-06) for reproducibility

---

## Reproducibility Checklist

To reproduce this experiment:

- [ ] Clone repository
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Set API keys in `.env`
- [ ] Verify matrix: `python scripts/verify_canonical_matrix.py`
- [ ] Run experiments: `python orchestrator.py run --time-of-day morning/afternoon/evening`
- [ ] Check all 1,620 runs completed
- [ ] Run Glass Box Audit: `python3 analysis/glass_box_audit.py`
- [ ] Analyze: `results/final_audit_results.csv`

**Expected runtime**:
- LLM generation: ~10-15 hours (1,620 API calls @ 20-30 sec/call)
- Glass Box Audit: ~30-40 hours (1,620 files @ 60-90 sec/file)

**Expected cost**:
- GPT-4o: ~$200 (540 runs)
- Gemini Flash: ~$10 (540 runs)
- Mistral Large: ~$50 (540 runs)
- **Total**: ~$260

---

## Questions?

For clarifications, contact the research team or check:
- CLAUDE.md (project overview)
- REPRODUCIBILITY.md (detailed replication guide)
- config.py (all experimental parameters)
