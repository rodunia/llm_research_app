# Pattern Analysis: Why NLI Fails to Match Correct Rules

## Discovery

**Status:** ✅ **All 10/10 intentional errors ARE being detected**
**Problem:** ❌ **But matched against WRONG rules (universal false positive rules)**

## The Pattern

### What's Happening

Every error is being flagged, but against the SAME generic rule:

| Error | Correct Rule Exists? | Actual Rule Matched | Score |
|-------|---------------------|-------------------|-------|
| **5 mg instead of 3 mg** | ✅ "Provides 3 mg dose" | ❌ "Not a gummy form" | 99.72% |
| **FDA approval** | ✅ "Not FDA-approved" | ❌ "Not a gummy form" | 99.03% |
| **Take every 2 hours** | ✅ "Claims to take every 2 hours" (prohibited) | ❌ "Not a gummy form" | 99.76% |
| **Store at 0°C** | ✅ "Store at freezing temps" (prohibited) | ❌ "Not a gummy form" | 98.56% |
| **Over 18 restriction** | ✅ (missing explicit rule) | ❌ "Universal effectiveness" | 97.10% |

### Root Cause: Universal Contradiction Rules

Certain rules trigger high contradiction scores against EVERYTHING:

**Problem Rule #1:**
```yaml
specs:
  form_factor:
    - "Not a gummy, chewable, or sublingual form"
```

Why it's problematic:
- Negative statement ("Not X") confuses NLI
- NLI sees any positive claim about tablets/dosage as contradicting this negative
- Triggers 95-99% contradiction scores universally

**Problem Rule #2:**
```yaml
prohibited_or_unsupported_claims:
  guarantees_absolutes:
    - "Universal effectiveness claims (e.g., 'works for everyone', '100% cure')"
```

Why it's problematic:
- Meta-statement about claims, not an actual claim
- NLI doesn't understand "claims about X" as a validation rule
- Matches incorrectly against safety disclaimers

## NLI Behavior Analysis

### Why NLI Matches Wrong Rules

The DeBERTa NLI model prioritizes:
1. **Syntactic patterns** over semantic meaning
2. **High-confidence mismatches** over lower-confidence correct matches
3. **Negative statements** as universal contradictions

**Example:**

```
Claim: "This product is approved by the FDA"
```

NLI compares against ALL rules:

| Rule | Semantic Relevance | NLI Contradiction Score | Selected? |
|------|-------------------|------------------------|-----------|
| **"Claims that product is FDA-approved"** (prohibited) | ✅ Perfect match | 65% (too low!) | ❌ No |
| **"Not a gummy form"** | ❌ Completely unrelated | 99% | ✅ **Yes** |

The NLI model is choosing the WRONG rule because:
- Negative rule "Not X" triggers higher contradiction scores
- Prohibited rule is meta-statement ("Claims that...") which NLI doesn't match well

## The Fix: Rewrite Rules as Positive Statements

### Principle

**❌ Don't write:** "Not X" or "Claims about X" or "Should not Y"
**✅ Do write:** "This product IS X" or "Product contains Y"

### Specific Fixes Needed

#### 1. Form Factor Rule

```yaml
# ❌ Current (universal contradiction):
specs:
  form_factor:
    - "Not a gummy, chewable, or sublingual form"

# ✅ Fixed (positive statement):
specs:
  form_factor:
    - "Solid oral tablet (immediate-release only)"
    - "Comes in tablet form"
```

#### 2. FDA Prohibition

```yaml
# ❌ Current (meta-statement):
prohibited_or_unsupported_claims:
  regulatory_authority:
    - "Claims that the product is FDA-approved or approved by any regulatory authority"

# ✅ Fixed (direct contradiction):
clarifications:
  - "This product is NOT FDA-approved"
  - "Melatonin is regulated as a dietary supplement, not approved as a drug"
  - "This product has NOT received FDA approval for any medical purpose"
```

#### 3. Dosage Frequency

```yaml
# ❌ Current (meta-statement):
prohibited_or_unsupported_claims:
  dosage_safety:
    - "Claims to take every 2 hours or at frequent intervals"

# ✅ Fixed (direct instruction):
usage_instructions:
  - "Take ONCE per 24 hours only"
  - "Do NOT take more frequently than once daily"
  - "Do NOT take every 2 hours"
```

#### 4. Storage Temperature

```yaml
# ❌ Current (negative statement):
prohibited_or_unsupported_claims:
  storage_handling:
    - "Claims to store at freezing temperatures (0°C or below)"

# ✅ Fixed (positive statement):
specs:
  storage:
    - "Store at room temperature (15-30°C)"
    - "Do NOT store at 0°C or below"
    - "Do NOT freeze"
```

#### 5. Age Restrictions

```yaml
# ❌ Current (incomplete):
prohibited_or_unsupported_claims:
  age_restrictions:
    - "Claims that adults over 18 should avoid the product"

# ✅ Fixed (positive statement):
clarifications:
  - "Intended for adults 18 years and older"
  - "Do NOT avoid if you are an adult over 18"
  - "Suitable for healthy adults"
```

## Implementation Strategy

### Phase 1: Rewrite Core Rules (High Priority)

1. Convert all "Not X" rules to "IS X" format
2. Move prohibited claims to `clarifications` section with "NOT" statements
3. Remove meta-statements like "Claims that..."

### Phase 2: Test with One File

1. Update melatonin YAML with fixes
2. Re-audit user_melatonin_8 (FDA error)
3. Verify it matches correct rule ("NOT FDA-approved") instead of "Not a gummy"

### Phase 3: Validate All Products

1. Apply same fixes to smartphone_mid.yaml
2. Apply same fixes to cryptocurrency_corecoin.yaml
3. Re-audit all files

## Expected Impact

| Metric | Current | After Fix | Improvement |
|--------|---------|-----------|-------------|
| **Correct rule matching** | 0/10 (0%) | 8/10 (80%)* | **+80%** |
| **False positives** | ~16/file | ~3/file | **-81%** |
| **Detection confidence** | 65-75% | 95-99% | **+30%** |

*Estimated based on fixing negative statements and meta-statements

## Why This Will Work

1. **Positive statements match better:** "Store at 15-30°C" will semantically contradict "Store at 0°C" with high confidence

2. **Direct negations match strongly:** "NOT FDA-approved" will contradict "FDA approved" with 99% confidence

3. **Eliminates universal contradictions:** No more "Not a gummy" matching everything

4. **Reduces category confusion:** Storage rules will only match storage claims

## Next Steps

1. ✅ Identify all problematic rules (DONE - documented above)
2. ⏳ Rewrite rules following positive statement format
3. ⏳ Test on single file
4. ⏳ Apply to all products
5. ⏳ Re-audit and measure improvement

---

## Appendix: Full List of Problematic Rules

### Supplement Melatonin

**Negative Statements (need conversion):**
- ❌ "Not a gummy, chewable, or sublingual form"
- ❌ "Not intended as long-term nightly therapy"
- ❌ "Not recommended for pregnant or breastfeeding individuals"

**Meta-Statements (need rewording):**
- ❌ "Claims that the product is FDA-approved"
- ❌ "Claims to take every 2 hours"
- ❌ "Claims to store at freezing temperatures"
- ❌ "Claims that adults over 18 should avoid"
- ❌ "Claims of permanent drowsiness"
- ❌ "Universal effectiveness claims"

**Total to fix:** 9 critical rules

### Smartphone Mid

**Negative Statements:**
- ❌ "No expandable storage via microSD"
- ❌ "No wireless charging"
- ❌ "No 3.5mm headphone jack"

**Total to fix:** 3 critical rules

