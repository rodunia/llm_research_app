# DeBERTa Verification Layer Specification

**Version:** 1.0 (Inference-Only)
**Date:** 2026-01-14
**Status:** Implemented

---

## Overview

The DeBERTa verification layer provides automated Natural Language Inference (NLI) based verification of extracted marketing claims against product ground truth. This is a **zero-LLM** evaluation approach using pretrained DeBERTa models fine-tuned on MNLI (Multi-Genre Natural Language Inference).

### Research Alignment

- **Engines:** OpenAI GPT-4o-mini, Google Gemini-2.5-flash, Mistral-small-latest
- **No Traps:** Induced errors are explicit IE-CLAIMS in ground truth (not trap scenarios)
- **NLI-Style Verification:** Premise (ground truth) vs Hypothesis (extracted claim)
- **Three-Way Classification:** Entailment, Contradiction, Neutral

---

## Architecture

### V1 Scope: Inference-Only

```
claim_extractor.py  →  claim_records[]  →  deberta_verify_claims.py  →  enriched_claim_records[]
                                                      ↓
                                             premise_builder.py (deterministic)
                                                      ↓
                                             deberta_nli.py (inference)
```

**Not in V1:**
- DeBERTa finetuning (scaffold provided for future work)
- Integration into orchestrator.py workflow (remains optional standalone)
- Human-in-the-loop review interface

---

## Components

### 1. Premise Builder (`analysis/premise_builder.py`)

**Purpose:** Construct deterministic premise from product YAML.

**Input:** Product YAML dictionary (`products/{product_id}.yaml`)

**Output:** Structured premise string with sections:
```
AUTHORIZED:
- <authorized claim 1>
- <authorized claim 2>
...

PROHIBITED:
- <prohibited claim 1>
- <prohibited claim 2>
...

SPECS:
- <spec 1>
- <spec 2>
...

DISCLAIMERS:
- <disclaimer 1>
- <disclaimer 2>
...
```

**Key Properties:**
- **Deterministic:** Same YAML → Same premise
- **Order-Preserving:** YAML list order maintained
- **Stable Sections:** Always AUTHORIZED → PROHIBITED → SPECS → DISCLAIMERS
- **No Interpretation:** Only extracts text, no transformations

**Functions:**
- `build_premise(product_yaml_dict) -> str`: Build premise from dict
- `load_product_yaml(product_id, products_dir) -> dict`: Load product YAML
- `hash_text(text) -> str`: Generate 12-char SHA256 prefix for deduplication

---

### 2. DeBERTa NLI Verifier (`analysis/deberta_nli.py`)

**Purpose:** Run pretrained DeBERTa NLI inference on premise-hypothesis pairs.

**Model Selection:**
- **Default:** `cross-encoder/nli-deberta-v3-small` (fast, CPU-friendly)
- **Alternatives:**
  - `microsoft/deberta-v3-base` (larger, more accurate)
  - `microsoft/deberta-v3-small-mnli` (MNLI-specific)
  - `cross-encoder/nli-deberta-v3-base` (cross-encoder architecture)

**Input:**
- `premise`: Ground truth text (from premise_builder)
- `hypothesis`: Claim sentence (from claim_extractor)

**Output:** Verification result dict
```json
{
  "model": "cross-encoder/nli-deberta-v3-small",
  "label": "entailment",
  "probs": {
    "entailment": 0.85,
    "neutral": 0.10,
    "contradiction": 0.05
  },
  "premise_hash": "a1b2c3d4e5f6",
  "hypothesis_hash": "9z8y7x6w5v4u"
}
```

**Label Mapping:**
- **Model outputs** may vary in index order (different checkpoints use different orderings)
- **Robust mapping:** Checks `model.config.id2label` to map correctly
- **Canonical labels:** `entailment`, `neutral`, `contradiction` (lowercase)

**Research Interpretation:**
| NLI Label      | Research Meaning        | Implication                    |
|----------------|------------------------|--------------------------------|
| `entailment`   | Supported/Authorized    | Claim matches ground truth     |
| `neutral`      | Unsupported/Unknown     | Claim not mentioned            |
| `contradiction`| Contradicted/Violation  | Claim conflicts with truth     |

---

### 3. Batch Claim Verifier (`analysis/deberta_verify_claims.py`)

**Purpose:** Process all extracted claims and populate `deberta` field.

**Input:**
- Claims JSON files (`analysis/claims/*.json`)
- Products directory (`products/`)

**Output:**
- Updated claims JSONL (one claim per line) OR in-place update

**CLI Usage:**
```bash
# Basic usage
python -m analysis.deberta_verify_claims \
    --in analysis/claims/*.json \
    --out results/claims_deberta.jsonl \
    --products-dir products/

# In-place update
python -m analysis.deberta_verify_claims \
    --in analysis/claims/*.json \
    --inplace \
    --products-dir products/

# Custom model
python -m analysis.deberta_verify_claims \
    --in analysis/claims/*.json \
    --out results/claims_deberta.jsonl \
    --model microsoft/deberta-v3-base \
    --device cuda
```

**Processing Logic:**
1. Load claim record
2. Skip if `claim_kind == "disclaimer"` (V1 default, configurable with `--verify-disclaimers`)
3. Load product YAML (cached)
4. Build premise
5. Run NLI verification
6. Check for policy violations (simple substring match)
7. Populate `claim_record["deberta"]` field
8. Set `claim_record["severity"]` based on rules

**Claim Record Schema (Enriched):**
```json
{
  "run_id": "abc123...",
  "claim_id": "abc123::sent001",
  "sentence": "Experience 120 Hz display...",
  "char_span": [0, 133],
  "trigger_types": ["numeric"],
  "block_kind": "ad_primary",
  "claim_kind": "product_claim",
  "block_span": [0, 250],
  "extractor_version": "v2.0",

  // NEW: DeBERTa verification result
  "deberta": {
    "model": "cross-encoder/nli-deberta-v3-small",
    "label": "entailment",
    "probs": {
      "entailment": 0.85,
      "neutral": 0.10,
      "contradiction": 0.05
    },
    "premise_hash": "a1b2c3d4e5f6",
    "hypothesis_hash": "9z8y7x6w5v4u",
    "policy_violation": false  // Simple substring match
  },

  // NEW: Severity score (rule-based)
  "severity": "high" | "medium" | null
}
```

**Severity Rules (V1 - Simple):**
- `severity="high"`: Policy violation detected (substring match with PROHIBITED)
- `severity="medium"`: NLI label = contradiction (but not policy violation)
- `severity=null`: NLI label = entailment or neutral

---

### 4. Policy Violation Detection

**Problem:** PROHIBITED claims are policy violations, not necessarily logical contradictions.

**Example:**
- **Prohibited:** "Guaranteed to work for all users."
- **Hypothesis:** "Guaranteed results in all conditions."
- **NLI Prediction:** May be `neutral` (hypothesis doesn't directly contradict premise facts)
- **Policy Reality:** VIOLATION (uses prohibited language "guaranteed")

**V1 Solution (Simple):**
- Extract all `prohibited_claims` from product YAML
- For each hypothesis, check if it contains a prohibited claim substring (case-insensitive)
- If match: set `deberta["policy_violation"] = true`
- This is independent of NLI label

**Future Enhancement:**
- Semantic similarity scoring (SBERT embeddings)
- Trigger word detection (from claim_extractor lexicons)
- Trained policy classifier

---

### 5. Disclaimer Handling

**V1 Approach:** **Skip disclaimers by default**

**Rationale:**
- Disclaimers are compliance statements, not marketing claims
- Verifying them against AUTHORIZED/PROHIBITED creates ambiguity:
  - Is a disclaimer "supported" if it matches DISCLAIMERS section?
  - Is it "contradicted" if missing from DISCLAIMERS?
- Better to handle separately in future work

**Override:**
```bash
python -m analysis.deberta_verify_claims \
    --in analysis/claims/*.json \
    --out results/claims_deberta.jsonl \
    --verify-disclaimers  # Include disclaimers
```

**Skipped Claims:**
```json
{
  "claim_kind": "disclaimer",
  "deberta": {
    "skipped": "disclaimer"
  },
  "severity": null
}
```

---

## Finetuning Readiness (V2 - Not Implemented Yet)

### Dataset Exporter (`analysis/export_nli_dataset.py`)

**Purpose:** Export claims in format suitable for human annotation and finetuning.

**Usage:**
```bash
python -m analysis.export_nli_dataset \
    --claims analysis/claims/*.json \
    --products products/ \
    --out results/deberta_nli_dataset.jsonl
```

**Output Format (JSONL):**
```json
{
  "premise": "AUTHORIZED:\n- 120 Hz display...",
  "hypothesis": "Experience 120 Hz display.",
  "label": null,  // For human annotation
  "product_id": "smartphone_mid",
  "engine": "openai",
  "material": "digital_ad.j2",
  "temperature": 0.6,
  "time_of_day": "morning",
  "repetition": 1,
  "claim_id": "abc123::sent001",
  "claim_kind": "product_claim",
  "predicted_label": "entailment",  // From inference
  "policy_violation": false
}
```

**Human Annotation Workflow:**
1. Export dataset
2. Human annotators fill `label` field with gold labels
3. Split dataset (group-aware, see below)
4. Run finetuning (future)

### Group-Aware Splitting

**Problem:** Prevent data leakage across splits.

**Strategy:**
- **Primary split key:** `product_id` (no product in both train/test)
- **Optional:** Also split by `engine` or `material` to test generalization

**Example Split:**
```
Train products:      smartphone_mid, supplement_melatonin
Validation products: cryptocurrency_corecoin
Test products:       <future products: herbal_supplement, bt_headphones>
```

**Ratios:**
- 70% train
- 15% validation
- 15% test

**Implementation:** See `scripts/train_deberta_nli.py` (skeleton only)

### Training Skeleton (`scripts/train_deberta_nli.py`)

**Status:** **NOT IMPLEMENTED** (scaffold for future work)

**Planned Features:**
- Load labeled JSONL dataset
- Group-aware split by product_id
- Fine-tune DeBERTa on 3-way NLI
- Evaluation metrics: accuracy, per-class F1, confusion matrix
- Save best checkpoint to `models/deberta_nli_finetuned/`

**Usage (Future):**
```bash
python scripts/train_deberta_nli.py \
    --dataset results/deberta_nli_dataset_labeled.jsonl \
    --output models/deberta_nli_finetuned \
    --split-by product_id \
    --epochs 3 \
    --batch-size 16
```

---

## Testing & Validation

### Unit Tests

**Run all tests:**
```bash
pytest tests/ -v
```

**Test Coverage:**
- `tests/test_premise_builder.py`: Premise construction, determinism, ordering
- `tests/test_deberta_nli_shape.py`: Output schema validation, label validity, prob sums

**Fast tests only (skip slow model loading):**
```bash
pytest tests/test_premise_builder.py -v
```

### Smoke Test

**Quick CPU-only test (<30 seconds):**
```bash
python scripts/smoke_deberta_verify.py
```

**What it checks:**
- Premise builder works
- DeBERTa model loads
- Inference produces valid output
- Schema validation passes

**Expected output:**
```
======================================================================
DeBERTa Verification Layer - Smoke Test
======================================================================

Test 1: Premise Builder
----------------------------------------------------------------------
✓ Premise built successfully
  Length: 387 chars
  Hash: a1b2c3d4e5f6
✓ All required sections present: ['AUTHORIZED:', 'PROHIBITED:', 'SPECS:', 'DISCLAIMERS:']

Test 2: DeBERTa NLI Verifier
----------------------------------------------------------------------
Loading DeBERTa model (this may take 10-20 seconds on first run)...
✓ Model loaded successfully

Test 2a: Expected ENTAILMENT
  Hypothesis: Each tablet contains 3 mg of melatonin.
  Predicted: entailment
  Probs: {'entailment': 0.85, 'neutral': 0.10, 'contradiction': 0.05}

Test 2b: Expected CONTRADICTION
  Hypothesis: Guaranteed to work for all users without exception.
  Predicted: contradiction
  Probs: {'entailment': 0.05, 'neutral': 0.10, 'contradiction': 0.85}

Test 2c: Expected NEUTRAL
  Hypothesis: This product is available in multiple flavors.
  Predicted: neutral
  Probs: {'entailment': 0.10, 'neutral': 0.80, 'contradiction': 0.10}

Test 3: Output Schema Validation
----------------------------------------------------------------------
✓ All results have valid schema:
  - Required keys: {'model', 'label', 'probs', 'premise_hash', 'hypothesis_hash'}
  - Valid labels: {'entailment', 'neutral', 'contradiction'}
  - Probs sum to ~1.0
  - Hashes are 12 chars

======================================================================
Smoke Test Summary
======================================================================
✓ Premise builder: PASS
✓ DeBERTa NLI verifier: PASS
✓ Output schema: PASS

All smoke tests PASSED!
======================================================================
```

---

## Usage Examples

### Example 1: Verify All Claims

```bash
# Step 1: Extract claims (existing workflow)
python -m analysis.evaluate

# Step 2: Verify with DeBERTa
python -m analysis.deberta_verify_claims \
    --in analysis/claims/*.json \
    --out results/claims_deberta.jsonl \
    --products-dir products/

# Step 3: Analyze results
python -c "
import json
with open('results/claims_deberta.jsonl') as f:
    claims = [json.loads(line) for line in f]

# Count by label
from collections import Counter
labels = [c.get('deberta', {}).get('label') for c in claims]
print(Counter(labels))

# Policy violations
violations = [c for c in claims if c.get('deberta', {}).get('policy_violation')]
print(f'Policy violations: {len(violations)}')
"
```

### Example 2: In-Place Update

```bash
# Update claim files directly (no separate output)
python -m analysis.deberta_verify_claims \
    --in analysis/claims/*.json \
    --inplace \
    --products-dir products/
```

### Example 3: Custom Model

```bash
# Use larger, more accurate model (slower)
python -m analysis.deberta_verify_claims \
    --in analysis/claims/*.json \
    --out results/claims_deberta.jsonl \
    --model microsoft/deberta-v3-base \
    --device cpu  # or 'cuda' if available
```

### Example 4: Export for Annotation

```bash
# Export NLI dataset for human labeling
python -m analysis.export_nli_dataset \
    --claims analysis/claims/*.json \
    --products products/ \
    --out results/deberta_nli_dataset.jsonl

# Annotators fill 'label' field manually
# Then use for finetuning (future work)
```

---

## Limitations & Future Work

### V1 Limitations

1. **Pretrained Model Only:** Uses off-the-shelf MNLI checkpoint, not domain-adapted
2. **Simple Policy Detection:** Substring matching for prohibited claims (not semantic)
3. **No Disclaimers:** Skips disclaimer verification to avoid ambiguity
4. **No LLM Integration:** Standalone module, not integrated into orchestrator workflow
5. **CPU-Only Focus:** Optimized for CPU inference (GPU optional but not required)

### Future Enhancements (V2+)

1. **Domain Finetuning:**
   - Human-annotated dataset (exported via `export_nli_dataset.py`)
   - Group-aware split (no product leakage)
   - Fine-tune DeBERTa on marketing claims NLI

2. **Semantic Policy Violation:**
   - Use SBERT for semantic similarity to prohibited claims
   - Trigger word detection (leverage claim_extractor lexicons)
   - Trained policy classifier

3. **Disclaimer Verification:**
   - Separate verification logic for disclaimers
   - Check against DISCLAIMERS section only
   - Handle mandatory vs optional disclaimers

4. **Orchestrator Integration:**
   - Add DeBERTa verification as optional step in `orchestrator.py`
   - CLI flag: `python orchestrator.py run --verify-claims`

5. **Human-in-the-Loop:**
   - Streamlit interface for reviewing high-severity claims
   - Batch approval/rejection workflow
   - Export corrected labels for continuous finetuning

---

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements_deberta.txt
```

This installs:
- `torch>=2.0.0`
- `transformers>=4.35.0`
- `pyyaml>=6.0`
- `pytest>=7.0.0`
- And other utilities

### 2. Download Model (First Run)

First run will download DeBERTa model from HuggingFace (~300MB):

```bash
# Smoke test downloads model
python scripts/smoke_deberta_verify.py
```

### 3. Run Tests

```bash
pytest tests/ -v
```

---

## Troubleshooting

### Model Download Slow

**Problem:** First run downloads ~300MB model from HuggingFace.

**Solution:**
- Be patient (one-time download)
- Or pre-download manually:
  ```python
  from transformers import AutoTokenizer, AutoModelForSequenceClassification
  AutoTokenizer.from_pretrained("cross-encoder/nli-deberta-v3-small")
  AutoModelForSequenceClassification.from_pretrained("cross-encoder/nli-deberta-v3-small")
  ```

### Out of Memory (CPU)

**Problem:** Large batch of claims causes OOM on CPU.

**Solution:**
- Process in smaller batches (modify script to batch-process)
- Use smaller model: `cross-encoder/nli-deberta-v3-small` (default)
- Close other applications

### Label Mapping Mismatch

**Problem:** Model outputs unexpected label indices.

**Solution:**
- Robust label mapping implemented (checks `model.config.id2label`)
- If issues persist, verify model checkpoint is NLI-trained
- Check model card on HuggingFace

### Policy Violations Not Detected

**Problem:** Known prohibited claims not flagged.

**Solution:**
- V1 uses simple substring match (case-insensitive)
- Check exact phrasing in `prohibited_claims` YAML
- Future: Use semantic similarity (V2+)

---

## File Structure

```
llm_research_app/
├── analysis/
│   ├── claim_extractor.py          # Existing (DO NOT MODIFY)
│   ├── evaluate.py                 # Existing (DO NOT MODIFY)
│   ├── premise_builder.py          # NEW: Build NLI premises
│   ├── deberta_nli.py              # NEW: DeBERTa NLI inference
│   ├── deberta_verify_claims.py    # NEW: Batch claim verifier
│   └── export_nli_dataset.py       # NEW: Dataset exporter
│
├── scripts/
│   ├── smoke_deberta_verify.py     # NEW: Quick smoke test
│   └── train_deberta_nli.py        # NEW: Training skeleton (not implemented)
│
├── tests/
│   ├── test_premise_builder.py    # NEW: Premise builder tests
│   └── test_deberta_nli_shape.py   # NEW: NLI output schema tests
│
├── docs/
│   └── deberta_verification_spec.md # NEW: This file
│
├── requirements_deberta.txt         # NEW: DeBERTa dependencies
│
└── products/                        # Existing (DO NOT MODIFY)
    ├── smartphone_mid.yaml
    ├── cryptocurrency_corecoin.yaml
    └── supplement_melatonin.yaml
```

---

## Research Alignment Summary

✅ **Engines:** OpenAI, Google Gemini, Mistral (no Anthropic mentioned)
✅ **No Traps:** IE-CLAIMS are explicit in ground truth
✅ **NLI Verification:** Premise (ground truth) vs Hypothesis (claim)
✅ **Three-Way Labels:** Entailment → Supported, Contradiction → Violated, Neutral → Unsupported
✅ **Zero-LLM Evaluation:** Uses pretrained DeBERTa, no LLM calls
✅ **Deterministic Premise:** Same YAML → Same premise
✅ **Policy-Aware:** Separate detection for prohibited claims

---

## Quick Start Checklist

- [ ] Install dependencies: `pip install -r requirements_deberta.txt`
- [ ] Run smoke test: `python scripts/smoke_deberta_verify.py`
- [ ] Run unit tests: `pytest tests/ -v`
- [ ] Verify claims: `python -m analysis.deberta_verify_claims --help`
- [ ] Export dataset: `python -m analysis.export_nli_dataset --help`
- [ ] Read limitations and plan V2 enhancements

---

**End of Specification**
