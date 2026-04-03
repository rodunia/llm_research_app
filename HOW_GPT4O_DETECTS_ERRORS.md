# How GPT-4o Freeform Detects Errors

**Comparison**: Glass Box (Multi-stage) vs GPT-4o Freeform (Single-stage)

---

## GPT-4o Freeform Approach

### 1. Input

**Prompt Structure**:
```
You are a fact-checking assistant. Your task is to identify any factual errors,
contradictions, or unsupported claims in marketing text by comparing it to
product specifications.

# Product Specifications:
[Full YAML dump of product specs - includes specs, authorized_claims,
prohibited_claims, clarifications]

# Marketing Text to Validate:
[The marketing material to check]

# Instructions:
1. Carefully read the marketing text
2. Compare each factual claim against specifications
3. Identify any errors, contradictions, or unsupported claims
4. For each error found, provide:
   - The incorrect claim
   - What it should be according to specifications
   - Why this is an error
   - Your confidence level (High/Medium/Low)
5. If you find NO errors, clearly state "NO ERRORS FOUND"
```

**Model**: GPT-4o at temperature 0.0

### 2. Processing

**Single LLM Call**:
- GPT-4o reads both specs and marketing text
- Uses free-form reasoning to compare
- Identifies discrepancies
- Generates natural language explanation

**No intermediate steps** - all reasoning happens inside the model's context window.

### 3. Output Example

```
Upon reviewing the marketing text against the product specifications,
I have identified several errors and contradictions:

1. **Incorrect Claim**: "The serving size is 1 tablet, which contains 5 mg
   of melatonin per serving."
   - **Correction**: The serving size is 1 tablet, which contains 3 mg
     of melatonin per serving.
   - **Reason**: The product specifications clearly state that each tablet
     contains 3 mg of melatonin.
   - **Confidence Level**: High

2. **Incorrect Claim**: "Each bottle contains 100 tablets."
   - **Correction**: Each bottle contains 120 tablets.
   - **Reason**: The product specifications indicate that each bottle
     contains 120 tablets.
   - **Confidence Level**: High

3. **Incorrect Claim**: "Store at exactly 0°C."
   - **Correction**: Store at room temperature (15-30°C / 59-86°F) and
     do not store at 0°C or below.
   - **Reason**: The product specifications clearly state that the product
     should not be stored at 0°C or below.
   - **Confidence Level**: High

Overall, the marketing text contains several factual inaccuracies when
compared to the product specifications.
```

### 4. Strengths

✅ **Holistic reasoning**: GPT-4o considers context and semantic meaning
✅ **Natural explanations**: Human-readable justifications for each error
✅ **Confidence levels**: Explicit uncertainty quantification
✅ **Simple architecture**: Single API call, no pipeline complexity
✅ **Contextual understanding**: Can detect nuanced contradictions (e.g., "vegan" + "fish-derived")

### 5. Weaknesses

⚠️ **Parsing challenges**: Free-text output requires heuristic parsing
⚠️ **Inconsistent format**: Response structure varies slightly between runs
⚠️ **No structured data**: Have to count numbered items to get error count
⚠️ **Opaque reasoning**: Can't see intermediate steps or extracted claims
⚠️ **Higher cost**: ~1,200 tokens per file vs 800 for Glass Box extraction only

---

## Glass Box Approach

### 1. Input (Stage 1: Extraction)

**Prompt Structure**:
```
You are a forensic claim extraction system for marketing compliance audits.

TASK: Extract EVERY verifiable fact, technical specification, operational
policy, restriction, and safety warning from the marketing material.
SEPARATE disclaimers from core claims.

EXTRACTION RULES:
1. Split compound sentences into atomic facts
2. Maintain original terminology (do not over-paraphrase)
3. Extract ALL verifiable claims including:
   - Storage instructions (e.g., "Store at exactly 0°C")
   - Dosing/usage instructions (e.g., "Take every 2 hours")
4. CRITICAL: Extract claims from BOTH main content AND disclaimer/warning sections
5. Disclaimer sections often contain verifiable storage/dosing instructions

OUTPUT FORMAT (strict JSON - FLAT STRING ARRAYS ONLY):
{
  "core_claims": [
    "atomic core claim 1",
    "Store at exactly 0°C",
    "Contains 5 mg of melatonin per serving"
  ],
  "disclaimers": ["Results may vary"]
}
```

**Model**: GPT-4o at temperature 0.0

### 2. Processing (Stage 1: Extraction)

**First LLM Call** (GPT-4o):
- Extracts atomic claims from marketing text
- Returns structured JSON with claim lists
- No validation yet - just extraction

**Example Output**:
```json
{
  "core_claims": [
    "The serving size is 1 tablet",
    "Contains 5 mg of melatonin per serving",
    "Each bottle contains 100 tablets",
    "These tablets are suitable for vegans",
    "These tablets are suitable for vegetarians",
    "Contain natural fish-derived ingredients",
    "Store at exactly 0°C"
  ],
  "disclaimers": [
    "Results may vary",
    "Consult healthcare professional if pregnant"
  ]
}
```

### 3. Processing (Stage 2: NLI Validation)

**For each extracted claim**:

Load product YAML with:
- `specifications`: Ground truth specs
- `prohibited_claims`: List of forbidden claim types
- `authorized_claims`: List of allowed claims
- `clarifications`: Important context

**NLI Cross-Encoder** (RoBERTa-base):
```python
# For each claim, check against prohibited claims
hypothesis = "Contains 5 mg of melatonin per serving"
premise = "Verified to contain 3 mg melatonin per serving"  # From YAML

nli_result = model.predict([
    (premise, hypothesis)
])
# Returns: {label: "contradiction", score: 0.996}
```

**Contradiction Detection**:
- If NLI score > 0.95 for contradiction → Flag as violation
- Store: claim, violated rule, confidence score

### 4. Output Example

**CSV Format**:
```csv
Filename,Status,Violated_Rule,Extracted_Claim,Confidence_Score
errors_melatonin_6,FAIL,Verified to contain 3 mg melatonin per serving,Contains 5 mg of melatonin per serving,0.9964653253555298
errors_melatonin_6,FAIL,120 tablets per bottle,Each bottle contains 100 tablets,0.9640686511993408
errors_melatonin_6,FAIL,Claims about modifying REM or deep-sleep architecture,Contain natural fish-derived ingredients,0.9954078793525696
errors_melatonin_6,FAIL,Do NOT store at 0°C or below (do not freeze),Store at exactly 0°C,0.9871138334274292
```

### 5. Strengths

✅ **Structured output**: CSV with exact claims and confidence scores
✅ **Explainable**: Can trace each violation to specific claim + rule
✅ **Reproducible**: NLI model deterministic, same input = same output
✅ **Atomic granularity**: Each claim validated independently
✅ **Lower cost per file**: Extraction only, NLI is local (no API cost)
✅ **Comprehensive**: Extracts ALL claims, not just errors

### 6. Weaknesses

⚠️ **Complex pipeline**: Two-stage architecture (extraction + validation)
⚠️ **Extraction failures**: If GPT-4o-mini misses a claim, NLI can't catch it
⚠️ **Context loss**: Atomic claims lose surrounding context
⚠️ **False positives**: NLI may flag correct claims as contradictions
⚠️ **Requires YAML specs**: Needs well-defined prohibited_claims list

---

## Key Differences

| Aspect | GPT-4o Freeform | Glass Box |
|--------|----------------|-----------|
| **Architecture** | Single-stage | Two-stage (extraction + NLI) |
| **Model** | GPT-4o only | GPT-4o + RoBERTa |
| **Output** | Free-text explanations | Structured CSV |
| **Reasoning** | Holistic | Atomic (per-claim) |
| **Explainability** | Natural language | Claim + rule + score |
| **Cost** | ~$0.06/file | ~$0.04/file |
| **Parsing** | Heuristic (buggy) | Direct (structured) |
| **Confidence** | Subjective (High/Med/Low) | Numerical (0-1 score) |

---

## Which is Better?

### For Error Detection Performance: **TIE**

Both achieve:
- **File-level**: 100% (30/30 files)
- **Error-level**: 93.3% (28/30 specific errors)
- **Same misses**: CoreCoin errors #2 and #9

### For Production Use: **Glass Box**

Reasons:
1. **Structured output**: CSV easier to analyze than free text
2. **Reproducibility**: Deterministic NLI vs probabilistic LLM reasoning
3. **Traceability**: Can trace each violation to specific claim + rule
4. **Confidence scores**: Numerical scores enable filtering (e.g., flag only >0.99)
5. **Lower cost**: $64.80 vs $97.20 for 1,620 files

### For Rapid Prototyping: **GPT-4o Freeform**

Reasons:
1. **Simpler**: Single API call vs multi-stage pipeline
2. **Faster to implement**: No NLI model, no YAML engineering
3. **Natural explanations**: Human-readable justifications
4. **No false positive tuning**: Don't need to optimize NLI threshold

---

## Example Comparison: Melatonin Storage Error

### Input
**Marketing text**: "Store at exactly 0°C"
**Product spec**: "Store at room temperature (15-30°C). Do NOT store at 0°C or below."

### GPT-4o Freeform Output

```
5. **Incorrect Claim**: "Store at exactly 0°C."
   - **Correction**: Store at room temperature (15-30°C / 59-86°F) and
     do not store at 0°C or below.
   - **Reason**: The product specifications clearly state that the product
     should not be stored at 0°C or below.
   - **Confidence Level**: High
```

**Pros**: Clear explanation, contextual correction
**Cons**: Requires parsing, subjective confidence

### Glass Box Output

```csv
errors_melatonin_6,FAIL,Do NOT store at 0°C or below (do not freeze),Store at exactly 0°C,0.9871138334274292
```

**Pros**: Structured, numerical confidence, traceable
**Cons**: Less intuitive, requires looking up violated rule

---

## Conclusion

Both methods are **equivalent in detection performance** (93.3%) but serve different purposes:

- **GPT-4o Freeform**: Best for exploratory analysis, human review, rapid iteration
- **Glass Box**: Best for production compliance audits, systematic analysis, reproducible research

The choice depends on use case, not performance.
