# How Randomization Actually Works

**Date**: 2026-03-28
**Question**: How does the code use the 1,620-run matrix from March 25th?

---

## Simple Answer

**The orchestrator reads the pre-generated matrix from `results/experiments.csv` and executes runs in the order they appear in that file.**

That's it. No re-randomization, no re-ordering, no generation.

---

## Step-by-Step Workflow

### Step 1: Pre-Generate Matrix (Done Once, Before Experiments)

```bash
python scripts/test_randomizer_stratified.py --seed 42
```

**What this does**:
- Creates `results/experiments.csv` with 1,620 rows
- Each row is ONE run with:
  - product_id (smartphone/crypto/supplement)
  - material_type (faq.j2/digital_ad.j2/blog_post_promo.j2)
  - engine (openai/google/mistral)
  - temperature (0.2/0.6/1.0)
  - time_of_day_label (morning/afternoon/evening)
  - repetition_id (1/2/3)
  - scheduled_datetime (exact timestamp when to run)
  - status = "pending"
- **Order is randomized** during generation with seed 42
- **Order is fixed** after generation (locked in CSV)

**Current matrix**:
- Total runs: 1,620
- Seed: 42
- Mode: stratified_7day_balanced
- File date: March 28, 2026 13:04 (modified today)
- First scheduled date: March 17, 2026

---

### Step 2: Execute Runs (What `orchestrator.py run` Does)

```bash
python orchestrator.py run --time-of-day morning
```

**What happens**:

1. **orchestrator.py:484**: Calls `generate_matrix()`
   - Does NOT generate new matrix
   - Only VALIDATES existing matrix
   - Checks: 1,620 runs, seed 42, mode stratified_7day_balanced
   - Fails if matrix is wrong

2. **orchestrator.py:488**: Calls `execute_runs(time_of_day="morning")`
   - Calls `runner.run_job batch --time-of-day morning`

3. **runner/run_job.py:269**: Calls `read_pending_jobs()`
   - Opens `results/experiments.csv`
   - Reads ALL rows where `status == "pending"`
   - Filters by `time_of_day == "morning"` (if specified)
   - Returns list of pending jobs **in CSV order**

4. **runner/run_job.py:305**: Loops through pending jobs
   - For each job:
     - Reads run parameters from CSV row
     - Calls LLM with those parameters
     - Updates CSV row: `status = "completed"`, adds timestamps, tokens
     - Saves output to `outputs/{run_id}.txt`

**Key point**: The order of execution is determined by the ORDER OF ROWS in experiments.csv, filtered by status and time_of_day.

---

## The Randomization

**When does randomization happen?**
- ✅ During matrix generation (stratified_randomizer.py)
- ❌ NOT during execution (orchestrator just reads CSV in order)

**What gets randomized?**
- Order of rows in experiments.csv
- Assignment of engines to products/materials/temps
- Assignment of time slots to products/materials
- Scheduled timestamps

**What controls the randomization?**
- Seed = 42 (fixed)
- Mode = stratified_7day_balanced
- Algorithm in `scripts/test_randomizer_stratified.py`

**Can you change the randomization during experiments?**
- ❌ NO - the CSV is locked
- To change, you must:
  1. Stop experiments
  2. Generate NEW matrix with different seed
  3. Start experiments from scratch

---

## Example: How a Run Gets Executed

**CSV row** (simplified):
```
run_id,product_id,material_type,engine,temperature,time_of_day_label,status
abc123,smartphone_mid,faq.j2,openai,0.6,morning,pending
```

**When you run** `python orchestrator.py run --time-of-day morning`:

1. Read CSV, find all rows where:
   - status == "pending"
   - time_of_day_label == "morning"

2. For row abc123:
   - Load product: `products/smartphone_mid.yaml`
   - Load template: `prompts/faq.j2`
   - Render prompt with product specs
   - Call OpenAI with temperature=0.6
   - Save output to `outputs/abc123.txt`
   - Update CSV: `status=completed`, add tokens, timestamps

3. Move to next pending morning run

**Result**: Runs execute in the order they appear in CSV (filtered by time_of_day).

---

## The Matrix File

**Location**: `results/experiments.csv`

**Schema** (36 columns):
- Core identifiers: run_id, product_id, material_type, engine
- Model setup: temperature, max_tokens, seed, top_p, etc.
- Run context: time_of_day_label, repetition_id, scheduled_datetime
- Response data: status, prompt_tokens, completion_tokens, output_path
- Metadata: matrix_randomization_seed, matrix_randomization_mode

**Status field**:
- `pending` = Not executed yet
- `completed` = Successfully executed
- `failed` = Execution failed

**Idempotency**:
- If you run `orchestrator.py run` twice, it only executes `pending` runs
- Already `completed` runs are skipped
- This makes execution crash-resistant

---

## Validation (Research Integrity)

**Before ANY execution**, orchestrator validates the matrix:

```python
def validate_canonical_matrix():
    # Check 1: Total runs
    assert len(df) == 1620

    # Check 2: Randomization metadata
    assert df['matrix_randomization_seed'].iloc[0] == 42
    assert df['matrix_randomization_mode'].iloc[0] == 'stratified_7day_balanced'

    # Check 3: Balance
    assert all engine has 540 runs
    assert all time_of_day has 540 runs
    assert all engine×time_of_day has 179-181 runs

    # If any check fails: REJECT matrix, STOP execution
```

**Why?**
- Prevents running experiments with wrong protocol
- Prevents accidental re-randomization
- Ensures published methodology matches actual execution

---

## Timeline (Your Question About March 25th)

**March 25, 2026** (or earlier):
- Generated matrix with stratified randomizer
- File: `results/experiments.csv`
- 1,620 runs, seed 42, all status=pending

**March 28, 2026 (today) 13:04**:
- Matrix file modified (probably by running some experiments)
- Some runs may have status=completed
- Randomization NOT changed (seed still 42, order still same)

**Current state**:
- Same 1,620-run matrix
- Same randomization (seed 42)
- Same order of rows
- Only difference: some runs are completed, some are pending

---

## What Does NOT Change During Execution

❌ Order of rows in CSV
❌ Assignment of engines to products
❌ Assignment of time slots
❌ Scheduled timestamps
❌ Run IDs
❌ Randomization seed

**These are FIXED when matrix is generated.**

---

## What DOES Change During Execution

✅ `status` field (pending → completed)
✅ `started_at` timestamp
✅ `completed_at` timestamp
✅ `prompt_tokens`, `completion_tokens`, `total_tokens`
✅ `finish_reason`
✅ `model`, `model_version` (actual model used by API)
✅ Output files created in `outputs/`

**These are FILLED IN when runs execute.**

---

## Key Insight

**The randomization is in the CSV file itself (the order of rows).**

The orchestrator is NOT a randomizer. It's a CSV reader/executor.

**Flow**:
1. Randomizer creates CSV with randomized order
2. Orchestrator reads CSV and executes in that order
3. No re-randomization during execution

**Analogy**:
- Randomizer = shuffles a deck of cards once
- CSV file = the shuffled deck
- Orchestrator = deals cards from the deck in order

---

## Summary

**Your question**: "How does the code run the 1,620 runs from March 25th?"

**Answer**:
1. You generated a matrix on/before March 25th: `python scripts/test_randomizer_stratified.py --seed 42`
2. This created `results/experiments.csv` with 1,620 runs in randomized order
3. When you run `python orchestrator.py run`, it:
   - Validates the matrix (checks seed=42, 1,620 runs, balance)
   - Reads CSV row by row (in order)
   - Executes pending runs
   - Updates CSV with results
4. The randomization happened ONCE (during generation)
5. Execution just follows the CSV order

**No re-randomization. No re-ordering. Just: read CSV → execute → update CSV.**
