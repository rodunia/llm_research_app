# Research Value Analysis: 13 Proposed Metadata Fields

**Question**: Are these 13 additional fields necessary for research validity?

**Date**: 2026-03-31

---

## Your Research Questions (RQs)

### RQ1: People-Pleasing Bias
Do LLMs generate overly positive marketing content that violates compliance rules?

**Measured by**: Glass Box Audit (violations detected)

**Needs**: Product outputs, compliance violations

### RQ2: Induced Errors and Hallucinations
How frequently do LLMs introduce factual inaccuracies?

**Measured by**: Glass Box Audit (hallucinations, contradictions)

**Needs**: Product outputs, NLI judgments

### RQ3: Temporal Unreliability
Do LLMs produce inconsistent outputs across sessions and time?

**Measured by**: Within-condition variance, cross-session comparison

**Needs**: Multiple replications, timestamps, output similarity

---

## Field-by-Field Research Value Assessment

### ERROR TRACKING FIELDS (5 fields)

#### 1. retry_count
**Value**: ⭐⭐⭐ MEDIUM-HIGH

**Research relevance**:
- Measures API reliability by engine (OpenAI vs Google vs Mistral)
- Detects if certain conditions trigger more errors (high temp? specific products?)
- **RQ3 relevance**: API instability contributes to temporal unreliability

**Publication value**:
- Shows transparency: "We tracked all retry attempts"
- Can report: "OpenAI required retries on X% of calls vs Google Y%"
- Demonstrates experimental rigor

**Can we do without it?**: YES - Not critical for main RQs, but strengthens methods section

---

#### 2. error_type
**Value**: ⭐⭐⭐ MEDIUM-HIGH

**Research relevance**:
- Classify failures: rate_limit vs timeout vs content_filter
- **Important**: Content filter triggers = safety system blocked output
- **RQ1 relevance**: If Google filters more than OpenAI, suggests different safety thresholds
- **RQ3 relevance**: Pattern in errors over time/day

**Publication value**:
- "No runs were blocked by content filters" = transparency
- "X% failed due to rate limits" = experimental conditions documentation
- Shows all runs were "fair" (no censorship)

**Can we do without it?**: MAYBE - If no failures occur, we won't know why. If failures occur, we need to explain them.

---

#### 3. error_message
**Value**: ⭐ LOW

**Research relevance**:
- Debugging only
- Not used in statistical analysis
- Helps explain anomalies in results

**Publication value**:
- Supplement/appendix only: "Full error logs available"
- Not in main paper

**Can we do without it?**: YES - Nice to have for debugging, not essential

---

#### 4. api_response_code
**Value**: ⭐⭐ LOW-MEDIUM

**Research relevance**:
- HTTP status codes (200 OK, 429 rate limit, 500 server error)
- Similar to error_type but more technical
- Useful for reproducibility: "All runs returned 200 OK"

**Publication value**:
- Methods: "All API calls succeeded (HTTP 200)"
- Shows no systematic server-side issues

**Can we do without it?**: YES - error_type is more interpretable

---

#### 5. content_filter_triggered
**Value**: ⭐⭐⭐⭐ HIGH

**Research relevance**:
- **CRITICAL for RQ1**: If safety filters block marketing content, this affects bias analysis
- **Example**: "Google blocked 5% of supplement claims as medical advice" vs "OpenAI blocked 0%"
- Shows engine-specific safety policies affect output
- **RQ3**: If filtering varies by time/day, temporal unreliability

**Publication value**:
- **Must report**: "No outputs were filtered by safety systems" OR "X% were filtered"
- Reviewer will ask: "How do you know outputs weren't censored?"
- **Critical for validity**: Filtered outputs = selection bias

**Can we do without it?**: NO - This is important for research integrity

---

### PERFORMANCE FIELDS (3 fields)

#### 6. api_latency_ms
**Value**: ⭐⭐ LOW-MEDIUM

**Research relevance**:
- Time from request to first response
- Detects provider speed differences
- **RQ3**: If latency varies by time-of-day, might correlate with server load → quality differences

**Statistical potential**:
- Correlation: api_latency vs compliance_violations?
- Hypothesis: Rushed processing → more errors?

**Publication value**:
- Methods: "Average API latency: OpenAI 2.3s, Google 1.8s, Mistral 3.1s"
- Shows no outlier runs (e.g., 60s timeout suggests incomplete output)

**Can we do without it?**: YES - Interesting but not essential for main RQs

---

#### 7. tokens_per_second
**Value**: ⭐ LOW

**Research relevance**:
- Generation speed
- Can be computed from: completion_tokens / execution_duration_sec
- **Already have these columns**, so this is redundant

**Publication value**:
- Supplement only: "Generation speeds ranged from X to Y tokens/sec"

**Can we do without it?**: YES - Can compute post-hoc from existing data

---

#### 8. scheduled_vs_actual_delay_sec
**Value**: ⭐⭐⭐ MEDIUM-HIGH

**Research relevance**:
- Measures queue delay: scheduled 10:00am, actually ran 10:05am = 300 sec delay
- **RQ3 relevance**: If delays accumulate over experiment, late runs ≠ intended time slots
- Validates temporal randomization worked correctly

**Publication value**:
- Methods: "Runs executed within X minutes of scheduled time (mean delay: Y sec)"
- Shows adherence to pre-registered protocol
- **Important for reproducibility**: "Time-of-day effects are real, not artifacts of queueing"

**Can we do without it?**: MAYBE - If delays are small (<5 min), probably fine. But we won't know unless we measure.

---

### QUALITY FIELDS (3 fields)

#### 9. prompt_hash
**Value**: ⭐⭐⭐⭐ HIGH

**Research relevance**:
- SHA256 of rendered prompt
- **Critical for reproducibility**: Detects if prompts changed mid-experiment
- Validates: "All runs used identical prompts (hash: abc123...)"

**Publication value**:
- **Methods section**: "Prompt integrity verified via SHA256 hashing"
- **Reproducibility**: Reviewers can verify no prompt drift
- **Pre-registration**: Proves we didn't modify prompts after seeing results

**Can we do without it?**: NO - This is important for research integrity. We need to prove prompts didn't change.

---

#### 10. output_length_chars
**Value**: ⭐⭐⭐⭐ MEDIUM-HIGH

**Research relevance**:
- Character count of generated text
- **RQ2 relevance**: Longer outputs → more opportunity for errors?
- **Engine comparison**: Does OpenAI generate longer/shorter responses than Google?
- **Temperature effect**: Does high temp → longer outputs?

**Statistical potential**:
- DV: output_length_chars ~ engine + temperature + product
- Correlation: length vs violations?

**Publication value**:
- Results: "OpenAI generated longer outputs (mean: 1,847 chars) than Google (1,423 chars)"
- Shows output consistency or variability

**Can we do without it?**: MAYBE - Can compute from outputs/*.txt files post-hoc, but easier to track now

---

#### 11. output_word_count
**Value**: ⭐⭐⭐ MEDIUM

**Research relevance**:
- Word count (more interpretable than chars)
- Similar to output_length_chars but for linguistic analysis
- **RQ2**: Verbosity correlates with hallucinations?

**Publication value**:
- Results: "Average word count: FAQ 312 words, Ads 187 words"
- Shows content length by material type

**Can we do without it?**: MAYBE - Can compute from outputs/*.txt files post-hoc

---

### ALREADY HAVE (2 fields)

#### 12. scheduled_time_numeric
**Value**: ⭐ LOW (redundant)

**Why**: Can compute from scheduled_datetime (hours since experiment start)

**Can we do without it?**: YES - Derived field, compute during analysis

---

#### 13. randomization_seed_scheduling
**Value**: ⭐ LOW (redundant)

**Why**: We already have matrix_randomization_seed = 42

**Can we do without it?**: YES - Already tracked

---

## Summary: Research Validity Assessment

### CRITICAL for Research Validity (Must Add):
1. **content_filter_triggered** ⭐⭐⭐⭐ HIGH
   - **Why**: Proves no selection bias from safety filtering
   - **RQ impact**: RQ1 (bias), RQ3 (temporal)
   - **Reviewer will ask**: "Were any outputs censored?"

2. **prompt_hash** ⭐⭐⭐⭐ HIGH
   - **Why**: Proves prompt integrity (no mid-experiment changes)
   - **RQ impact**: All RQs (reproducibility)
   - **Reviewer will ask**: "How do you know prompts didn't drift?"

### IMPORTANT for Stronger Methods (Should Add):
3. **retry_count** ⭐⭐⭐ MEDIUM-HIGH
   - **Why**: API reliability by engine
   - **RQ impact**: RQ3 (temporal unreliability)
   - **Publication**: Demonstrates experimental rigor

4. **error_type** ⭐⭐⭐ MEDIUM-HIGH
   - **Why**: Classify failure modes
   - **RQ impact**: RQ3 (temporal), RQ1 (if content filters vary)
   - **Publication**: Transparency in methods

5. **scheduled_vs_actual_delay_sec** ⭐⭐⭐ MEDIUM-HIGH
   - **Why**: Validates temporal randomization
   - **RQ impact**: RQ3 (temporal unreliability)
   - **Publication**: Adherence to pre-registered protocol

6. **output_length_chars** ⭐⭐⭐ MEDIUM-HIGH
   - **Why**: Output consistency analysis
   - **RQ impact**: RQ2 (hallucinations), RQ3 (consistency)
   - **Publication**: Engine comparisons
   - **Can defer**: Compute from outputs/*.txt post-hoc

### NICE TO HAVE (Optional):
7. **output_word_count** ⭐⭐⭐ MEDIUM
   - Can compute from outputs/*.txt post-hoc

8. **api_latency_ms** ⭐⭐ LOW-MEDIUM
   - Interesting but not essential

9. **api_response_code** ⭐⭐ LOW-MEDIUM
   - Similar to error_type

### SKIP (Low Value):
10. **error_message** ⭐ LOW - Debugging only
11. **tokens_per_second** ⭐ LOW - Derived field
12. **scheduled_time_numeric** ⭐ LOW - Derived field
13. **randomization_seed_scheduling** ⭐ LOW - Redundant

---

## Final Recommendation

### Tier 1: MUST ADD (2 fields) - Critical for validity
- **content_filter_triggered**
- **prompt_hash**

**Why**: These prove research integrity (no censorship, no prompt drift). Reviewers WILL ask about these.

**Effort**: Low - Simple boolean and SHA256 hash

---

### Tier 2: SHOULD ADD (3 fields) - Strengthens paper
- **retry_count**
- **error_type**
- **scheduled_vs_actual_delay_sec**

**Why**: Demonstrates experimental rigor, validates temporal protocol, enables failure analysis

**Effort**: Medium - Requires tracking in engine clients

---

### Tier 3: CAN DEFER (2 fields) - Compute post-hoc
- **output_length_chars**
- **output_word_count**

**Why**: Useful for analysis but can compute from saved outputs/*.txt files

**Effort**: Zero now (compute later)

---

### Tier 4: SKIP (6 fields) - Low research value
- error_message, api_response_code, api_latency_ms, tokens_per_second, scheduled_time_numeric, randomization_seed_scheduling

**Why**: Debugging/supplemental only, not essential for main RQs

---

## Conservative Recommendation (Tier 1 + 2)

**Add 5 fields now**:
1. content_filter_triggered (CRITICAL)
2. prompt_hash (CRITICAL)
3. retry_count (IMPORTANT)
4. error_type (IMPORTANT)
5. scheduled_vs_actual_delay_sec (IMPORTANT)

**Compute post-hoc**:
- output_length_chars (from outputs/*.txt)
- output_word_count (from outputs/*.txt)
- tokens_per_second (from completion_tokens / execution_duration_sec)

**Skip**:
- error_message, api_response_code, api_latency_ms, scheduled_time_numeric, randomization_seed_scheduling

---

## Answer to Your Question

**Is it important for research validity?**

**YES, but only 2 fields are critical**:
1. **content_filter_triggered** - Proves no selection bias
2. **prompt_hash** - Proves prompt integrity

**3 more fields strengthen the paper** (retry_count, error_type, scheduled_vs_actual_delay_sec) but aren't strictly required for validity.

**The remaining 8 fields** are nice-to-have or can be computed later.

---

## Minimal Implementation (If Time-Constrained)

If you want to minimize changes:

**Add only 2 critical fields**:
- content_filter_triggered
- prompt_hash

**Compute post-hoc**:
- output_length_chars (from files)
- output_word_count (from files)
- tokens_per_second (from existing CSV columns)

**Skip the rest**

**Effort**: ~50 lines of code (vs 200-300 for all 13 fields)

**Result**: Research validity preserved, minimal workflow changes

---

## My Recommendation

**Add 5 fields** (Tier 1 + Tier 2):
1. content_filter_triggered ⭐⭐⭐⭐
2. prompt_hash ⭐⭐⭐⭐
3. retry_count ⭐⭐⭐
4. error_type ⭐⭐⭐
5. scheduled_vs_actual_delay_sec ⭐⭐⭐

**Why**: Good balance between research rigor and implementation effort. These 5 directly support your RQs and show experimental transparency.

**Effort**: ~100-150 lines across 5 files

**Time**: 2-3 hours implementation + testing

**Value**: High - Reviewers will appreciate the thoroughness
