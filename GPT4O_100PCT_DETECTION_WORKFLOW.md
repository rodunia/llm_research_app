# GPT-4o 100% Detection Workflow
## Structured JSON Prompt Design for Error Detection

**Date Created**: 2026-02-25
**Status**: Validated on 30-file pilot (3 runs × 30 files = 90 evaluations, 100% detection)
**Cost**: ~$0.025 per file (GPT-4o)

---

## Overview

This workflow achieved **100% detection rate** on the 30-file pilot study using GPT-4o with structured JSON output enforcement. This approach was validated across 3 independent runs with perfect stability.

**Key Insight**: The 100% detection came from **prompt engineering (structured JSON)**, NOT from using GPT-4o instead of GPT-4o-mini. See `PROMPT_ENGINEERING_IMPACT_ANALYSIS.md` for full analysis showing that model upgrade alone had zero impact (43% → 43%).

---

## Architecture

**Single-Stage Detection**:
```
Marketing Text + Product YAML → GPT-4o (JSON enforced) → Structured Error Report
```

**Components**:
1. **Input**: Marketing text + Product specifications (YAML)
2. **LLM**: GPT-4o at temperature 0
3. **Output**: JSON with enforced schema
4. **Validation**: JSON parsing + error count extraction

**No NLI Required**: Unlike Glass Box (multi-stage), this approach uses a single LLM call with structured output.

---

## Implementation

### Script Location
`analysis/gpt4o_baseline.py`

### Key Functions

```python
def create_detection_prompt(marketing_text: str, product_spec: dict) -> str:
    """
    Create structured JSON prompt for error detection.

    Args:
        marketing_text: The generated marketing material to audit
        product_spec: Product YAML loaded as dict

    Returns:
        Formatted prompt string with YAML specs and JSON schema
    """

    # Convert product spec to YAML string for prompt
    specs_yaml = yaml.dump(product_spec, default_flow_style=False, sort_keys=False)

    prompt = f"""You are a compliance auditor analyzing marketing materials for factual errors.

TASK: Identify ALL factual errors, contradictions, and unsupported claims.

PRODUCT SPECIFICATIONS:
```yaml
{specs_yaml}
```

MARKETING TEXT:
{marketing_text}

INSTRUCTIONS:
1. Compare EVERY claim in the marketing text against product specifications
2. Flag any claim that:
   - Contradicts the specifications
   - Includes information not in the specifications
   - Contains numerical errors (wrong numbers, units, ranges)
   - Makes unsupported promises or guarantees

OUTPUT FORMAT (JSON):
{{
  "errors_detected": true/false,
  "error_count": <number>,
  "errors": [
    {{
      "claim": "exact text from marketing material",
      "error_type": "numerical|factual|logical|hallucination",
      "explanation": "why this is an error",
      "correct_value": "what it should be (if applicable)"
    }}
  ]
}}

Be thorough and precise. Only flag genuine errors - do not flag stylistic choices.
"""

    return prompt


def validate_with_gpt4o(marketing_text: str, product_spec: dict) -> dict:
    """
    Run GPT-4o validation with JSON output enforcement.

    Args:
        marketing_text: Marketing text to validate
        product_spec: Product YAML as dict

    Returns:
        dict with:
            - errors_detected: bool
            - error_count: int
            - errors: list of error dicts
            - raw_response: str (JSON string)
    """

    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    prompt = create_detection_prompt(marketing_text, product_spec)

    response = client.chat.completions.create(
        model='gpt-4o',
        temperature=0,  # Deterministic for reproducibility
        messages=[
            {
                "role": "system",
                "content": "You are a precise compliance auditor. Output valid JSON only."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={'type': 'json_object'}  # *** CRITICAL: JSON enforcement ***
    )

    # Parse JSON response
    raw_json = response.choices[0].message.content
    result = json.loads(raw_json)

    return {
        'errors_detected': result.get('errors_detected', False),
        'error_count': result.get('error_count', 0),
        'errors': result.get('errors', []),
        'raw_response': raw_json
    }
```

---

## Critical Prompt Design Elements

### 1. Role Authority ✅
```python
system_message = "You are a precise compliance auditor. Output valid JSON only."
```
- **Why**: "Compliance auditor" is more authoritative than "fact-checking assistant"
- **Impact**: Increases confidence in flagging errors
- **Alternative Roles**: "inspector", "validator", "quality analyst"

### 2. Comprehensive Coverage Instruction ✅
```
INSTRUCTIONS:
1. Compare EVERY claim in the marketing text against product specifications
2. Flag ANY claim that...
```
- **Why**: Explicit instruction to be exhaustive (not superficial scanning)
- **Impact**: Forces systematic review of ALL claims
- **Key Words**: "EVERY", "ALL", "Compare each", "Review all"

### 3. Explicit Error Taxonomy ✅
```
"error_type": "numerical|factual|logical|hallucination"
```
- **Why**: Ensures all error classes are considered
- **Impact**: Prevents category blindness (e.g., only looking for numerical errors)
- **Categories**: numerical, factual, logical, hallucination, unsupported, contradictory

### 4. Exact Claim Quoting Requirement ✅
```json
{
  "claim": "exact text from marketing material",
  ...
}
```
- **Why**: Forces precise claim extraction (not paraphrasing)
- **Impact**: Ensures the model actually reads and quotes the text
- **Alternative**: Could also require "location": "line number" or "sentence number"

### 5. JSON Schema Enforcement ✅
```python
response_format={'type': 'json_object'}  # API-level enforcement
```
- **Why**: Guarantees structured output (no free-form text escape)
- **Impact**: Model MUST provide `errors_detected`, `error_count`, and `errors` list
- **Result**: No parsing ambiguity (unlike counting bullet points in free text)

### 6. YAML Specifications in Prompt ✅
```
PRODUCT SPECIFICATIONS:
```yaml
{full_yaml_specs}
```
```
- **Why**: Provides complete context (specs, authorized claims, prohibited claims)
- **Impact**: Model can cross-reference every claim against ground truth
- **Format**: YAML is human-readable and preserves structure

---

## What Made This Work vs Free-Form Prompts

### OLD Prompt (43% Detection)
```python
# System message
"You are a precise fact-checking assistant."

# User prompt (free-form)
"""
You are a fact-checking assistant. Your task is to identify any factual errors...

# Instructions:
1. Carefully read the marketing text
2. Compare each factual claim against specifications
3. Identify any errors...
4. For each error found, provide:
   - The incorrect claim
   - What it should be
   - Why this is an error
   - Your confidence level (High/Medium/Low)
5. If you find NO errors, clearly state "NO ERRORS FOUND"

# Your Analysis:
"""

# No JSON enforcement - free text response
# Result: 43% detection (13/30 files)
```

**Problems with OLD Prompt**:
- ❌ Passive "assistant" role (not authoritative)
- ❌ Optional error reporting ("if you find...")
- ❌ No structured output enforcement
- ❌ Easy to skip analysis and say "NO ERRORS FOUND"
- ❌ Parsing ambiguity (count bullet points? numbered lists? paragraphs?)

### NEW Prompt (100% Detection)
```python
# System message
"You are a precise compliance auditor. Output valid JSON only."

# User prompt (structured JSON)
"""
You are a compliance auditor analyzing marketing materials for factual errors.

TASK: Identify ALL factual errors, contradictions, and unsupported claims.

PRODUCT SPECIFICATIONS:
```yaml
{full_yaml_specs}
```

INSTRUCTIONS:
1. Compare EVERY claim in the marketing text against product specifications
2. Flag any claim that:
   - Contradicts the specifications
   - Includes information not in the specifications
   - Contains numerical errors (wrong numbers, units, ranges)
   - Makes unsupported promises or guarantees

OUTPUT FORMAT (JSON):
{
  "errors_detected": true/false,
  "error_count": <number>,
  "errors": [...]
}

Be thorough and precise. Only flag genuine errors - do not flag stylistic choices.
"""

# JSON enforcement via API
response_format={'type': 'json_object'}

# Result: 100% detection (30/30 files)
```

**Why NEW Prompt Works**:
- ✅ Authoritative "auditor" role
- ✅ Mandatory coverage ("EVERY claim", "ALL errors")
- ✅ JSON schema enforcement (can't skip analysis)
- ✅ Explicit error taxonomy (forces systematic review)
- ✅ Exact claim quoting required
- ✅ No escape hatch (must provide error_count even if 0)

---

## Validation Results

### 3-Run Stability Test

| Run | Files Tested | Errors Detected | Detection Rate | Notes |
|-----|-------------|-----------------|----------------|-------|
| **Run 1** | 30 | 30/30 | **100%** | Baseline validation |
| **Run 2** | 30 | 30/30 | **100%** | Stability test |
| **Run 3** | 30 | 30/30 | **100%** | Final confirmation |

**Total Evaluations**: 90 (30 files × 3 runs)
**Perfect Detection**: 90/90 (100%)
**Failed Detection**: 0

### Detection by Product Category

| Product | Files | Run 1 | Run 2 | Run 3 | Stability |
|---------|-------|-------|-------|-------|-----------|
| **Smartphone** | 10 | 10/10 | 10/10 | 10/10 | ✅ 100% |
| **Melatonin** | 10 | 10/10 | 10/10 | 10/10 | ✅ 100% |
| **CoreCoin** | 10 | 10/10 | 10/10 | 10/10 | ✅ 100% |

**Result**: Perfect detection across all product categories in all 3 runs.

### Non-Determinism Analysis (Temperature 0)

Despite `temperature=0` setting:
- **File-level variations**: 40% of files showed error count differences (±1-2 errors) between runs
- **Detection stability**: 100% - all 30 intentional errors caught in all 3 runs
- **Root cause**: OpenAI API documentation states "Temperature 0 makes outputs mostly but not perfectly deterministic"

**Implication**: Minor non-determinism affects error counts but not binary detection (errors found: yes/no).

---

## Cost Analysis

### Per-File Cost
- **Model**: GPT-4o (gpt-4o-2024-08-06)
- **Average tokens**: ~1500 prompt + ~500 completion = 2000 total
- **Cost**: $0.025 per file (approximate)

### Research Scale Cost (1,620 files)
- **Single run**: 1,620 × $0.025 = **$40.50**
- **Three runs**: 1,620 × 3 × $0.025 = **$121.50**

### Comparison to Glass Box
- **Glass Box cost**: ~$0.002 per file (GPT-4o-mini extraction + RoBERTa NLI)
- **Cost ratio**: GPT-4o Direct is **12.5x more expensive**
- **Detection rate**: Both achieve 100% (see FINAL_COMPARISON_3_RUNS.md)

**Tradeoff**: GPT-4o Direct costs 12.5x more but:
- ✅ Simpler architecture (single LLM call vs 3-stage pipeline)
- ✅ Lower false positive rate (varies by run, but generally fewer violations flagged)
- ✅ Better contextual reasoning (can explain nuanced errors)
- ❌ Same detection rate (100% vs 100%)
- ❌ Higher cost ($121.50 vs $3.24 for 3 runs)

---

## Usage Guide

### Basic Usage
```bash
# Run on single file
python analysis/gpt4o_baseline.py --run-id user_smartphone_1

# Run on all 30 pilot files
python analysis/gpt4o_baseline.py --batch

# Run with custom output directory
python analysis/gpt4o_baseline.py --batch --output-dir results/gpt4o_validation_run4
```

### Output Format
Each file generates a JSON result:
```json
{
  "run_id": "user_smartphone_1",
  "product_id": "smartphone_mid",
  "errors_detected": true,
  "error_count": 5,
  "errors": [
    {
      "claim": "16 GB RAM",
      "error_type": "numerical",
      "explanation": "Product specification lists 12 GB RAM, not 16 GB",
      "correct_value": "12 GB"
    },
    ...
  ],
  "timestamp": "2026-02-25T10:30:45",
  "model": "gpt-4o"
}
```

### Integration with Experiments
To use with full research pipeline:
```python
# In orchestrator.py or analysis script
from analysis.gpt4o_baseline import validate_with_gpt4o

# Load marketing text and product YAML
marketing_text = open(f"outputs/{run_id}.txt").read()
product_spec = yaml.safe_load(open(f"products/{product_id}.yaml"))

# Run validation
result = validate_with_gpt4o(marketing_text, product_spec)

# Store result
if result['errors_detected']:
    print(f"✓ Errors detected: {result['error_count']}")
else:
    print(f"✗ No errors detected")
```

---

## Limitations and Considerations

### Known Limitations

1. **Cost**: 12.5x more expensive than Glass Box (~$0.025 vs ~$0.002 per file)
2. **Single Model Dependency**: Relies entirely on GPT-4o (no ensemble validation)
3. **Temperature 0 Non-Determinism**: Error counts vary slightly between runs (±1-2)
4. **No Claim-Level Tracing**: Doesn't extract atomic claims separately (unlike Glass Box)
5. **Black Box**: Less explainable than Glass Box (no NLI scores or violated rules)

### When to Use This Workflow

✅ **Use GPT-4o Structured (JSON) When**:
- Budget allows (~$40 per 1,620-file run)
- Need simple architecture (single LLM call)
- Want lower false positive rate (fewer violations flagged)
- Contextual reasoning is important (nuanced error explanations)
- Don't need claim-level extraction (just error detection)

❌ **Don't Use When**:
- Cost is primary constraint (use Glass Box - 12.5x cheaper)
- Need comprehensive auditing (Glass Box flags 23x more violations)
- Want explainability (need violated rules + NLI scores)
- Scalability is critical (thousands of files)

### Recommended Use Cases

1. **Validation/Spot-Checking**: Run GPT-4o on 5-10% sample to validate Glass Box results
2. **High-Value Content**: Use for critical marketing materials requiring manual review
3. **Hybrid Approach**: Glass Box for bulk detection + GPT-4o for contextual explanations
4. **Research Comparison**: Use as baseline to compare against Glass Box performance

---

## Prompt Variations to Test

### Potential Improvements

1. **Add Severity Scoring**:
```json
{
  "claim": "...",
  "error_type": "numerical",
  "severity": "high|medium|low",
  "explanation": "..."
}
```

2. **Require Confidence Scores**:
```json
{
  "claim": "...",
  "confidence": 0.95,
  "explanation": "..."
}
```

3. **Add Location Metadata**:
```json
{
  "claim": "...",
  "location": "Paragraph 3, Sentence 2",
  "explanation": "..."
}
```

4. **Multi-Stage Reasoning** (Chain-of-Thought):
```
STEP 1: Extract all factual claims from marketing text.
STEP 2: For each claim, check against specifications.
STEP 3: Identify contradictions or unsupported claims.
OUTPUT: JSON with errors found.
```

---

## Related Documentation

- **Prompt Engineering Analysis**: `PROMPT_ENGINEERING_IMPACT_ANALYSIS.md` - Shows why JSON enforcement achieved 100%
- **3-Run Comparison**: `FINAL_COMPARISON_3_RUNS.md` - Glass Box vs GPT-4o Structured (both 100%)
- **Free-Form Comparison**: `COMPARISON_GLASSBOX_VS_GPT4O_FREEFORM.md` - Glass Box vs GPT-4o Free-Form (100% vs 43%)
- **Glass Box Architecture**: `CLAUDE.md` (section: Glass Box Audit System v2.1)
- **Pilot Study Results**: `results/PILOT_STUDY_FINAL_100PCT.md`

---

## Quick Reference

| Element | Value | Notes |
|---------|-------|-------|
| **Model** | gpt-4o | NOT gpt-4o-mini |
| **Temperature** | 0 | Deterministic (mostly) |
| **System Message** | "You are a precise compliance auditor. Output valid JSON only." | Authoritative role |
| **JSON Enforcement** | `response_format={'type': 'json_object'}` | Critical for 100% detection |
| **Cost** | ~$0.025/file | ~$40.50 for 1,620 files |
| **Detection Rate** | 100% (30/30) | Validated across 3 runs |
| **Architecture** | Single-stage | One LLM call per file |
| **Output** | JSON with errors array | Structured, parseable |
| **Script** | `analysis/gpt4o_baseline.py` | Production-ready |

---

## Summary

**This workflow achieved 100% detection** on the 30-file pilot study through:
1. ✅ JSON schema enforcement at API level
2. ✅ Authoritative "compliance auditor" role
3. ✅ Explicit "EVERY claim" coverage requirements
4. ✅ Error taxonomy (numerical/factual/logical/hallucination)
5. ✅ Exact claim quoting requirements
6. ✅ Temperature 0 for reproducibility

**Key Lesson**: Prompt engineering (structured JSON) had 2.3x more impact than model selection (GPT-4o-mini → GPT-4o had zero impact with old prompt).

**Recommendation**: Use Glass Box for primary detection (12.5x cheaper, same 100% detection), optionally validate with GPT-4o Structured on a random sample for confidence.

---

**Last Updated**: 2026-02-25
**Status**: Production-ready (validated on 90 evaluations)
**Maintainer**: Research team
