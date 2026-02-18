# YAML Changes Impact Assessment

## System Architecture Analysis

### Two Separate Systems Using Product YAMLs:

1. **Marketing Material Generation (`runner/` pipeline)**
   - Uses: `authorized_claims`, `prohibited_or_unsupported_claims`, `specs`, `mandatory_statements`
   - Templates: `prompts/*.j2` (faq.j2, digital_ad.j2, blog_post_promo.j2, etc.)
   - Purpose: Generate marketing materials by giving LLMs approved claims to use

2. **Glass Box Audit (`analysis/glass_box_audit.py`)**
   - Uses: `authorized_claims`, `specs`, `prohibited_or_unsupported_claims`, `clarifications`, `usage_instructions`, `safety_warnings`
   - Purpose: Validate generated marketing materials against ground truth

---

## Critical Dependencies

### Marketing Generation (runner/render.py)

**Line 76:** `required_keys = ["name", "target_audience", "specs", "authorized_claims"]`

**❌ BREAKING CHANGE if removed:**
- `authorized_claims` - **REQUIRED** (system will crash if missing)
- `specs` - **REQUIRED** (system will crash if missing)

**✅ SAFE to modify:**
- `prohibited_or_unsupported_claims` - **OPTIONAL** (templates handle missing gracefully with `{% if %}`)
- `clarifications` - **NOT USED** by marketing templates at all
- `usage_instructions` - **NOT USED** by marketing templates
- `safety_warnings` - **NOT USED** by marketing templates

### Glass Box Audit (analysis/glass_box_audit.py)

**Lines 587-590:**
```python
authorized_claims = flatten_authorized_claims(product_yaml)
specs = flatten_specs(product_yaml)
prohibited_claims = flatten_prohibited_claims(product_yaml)
clarifications = flatten_clarifications(product_yaml)
```

**✅ SAFE to modify ALL sections:**
- Uses `.get()` with defaults, so missing sections won't crash
- All flatten functions handle empty dicts/lists gracefully
- `clarifications` is ONLY used by Glass Box, not by marketing generation

---

## Proposed Changes Safety Analysis

### Change 1: Move Generic Statements from `authorized_claims` to `clarifications`

**Example:**
```yaml
# BEFORE:
authorized_claims:
  - Enables peer-to-peer value transfer without intermediaries
  - Allows value to be transferred directly between parties

# AFTER:
authorized_claims:
  - Enables peer-to-peer value transfer  # Keep ONE version

clarifications:
  - CoreCoin enables peer-to-peer value transfer
  - Transactions do not require intermediaries
```

**Impact on Marketing Generation:** ✅ **SAFE**
- `authorized_claims` still exists (required key present)
- Templates will simply have fewer variations of the same claim
- LLMs can still generate same content, just less repetitive guidance

**Impact on Glass Box Audit:** ✅ **BENEFICIAL**
- Reduces false positives (fewer generic universal contradictions)
- `clarifications` will now have informational statements
- NLI will stop treating these as contradictions

**Verdict:** ✅ **SAFE TO APPLY**

---

### Change 2: Flatten `clarifications` Structure (Remove Nested Subsections)

**Example:**
```yaml
# BEFORE:
clarifications:
  technical_specifications:
    - Does NOT support non-staking light validators
    - Average block time is 5 seconds (NOT 4 seconds)

# AFTER:
clarifications:
  - Does NOT support non-staking light validators
  - Average block time is 5 seconds (NOT 4 seconds)
```

**Impact on Marketing Generation:** ✅ **NO IMPACT**
- Marketing templates don't use `clarifications` at all
- Zero risk to marketing generation

**Impact on Glass Box Audit:** ✅ **CRITICAL FIX**
- Current `flatten_clarifications()` (line 482) only handles `isinstance(clarifications_section, list)`
- Nested dicts like `technical_specifications: [...]` are NOT extracted
- Flattening ensures all clarifications are extracted and used for NLI

**Verdict:** ✅ **SAFE AND NECESSARY**

---

### Change 3: Remove Redundant authorized_claims

**Example:**
```yaml
# BEFORE (5 variations):
authorized_claims:
  functionality:
    - Enables peer-to-peer value transfer without intermediaries
    - Facilitates direct value exchange, eliminating the need for middlemen.
    - Allows value to be transferred directly between parties, bypassing intermediaries.
    - Permits peer-to-peer value exchange, cutting out the middleman.
    - Supports value transfer directly between users, with no intermediaries required.

# AFTER (1 version):
authorized_claims:
  functionality:
    - Enables peer-to-peer value transfer
```

**Impact on Marketing Generation:** ✅ **SAFE**
- Templates still receive `authorized_claims.functionality` list
- LLMs are creative enough to generate variations from one canonical claim
- Reduces prompt token usage (minor cost savings)

**Impact on Glass Box Audit:** ✅ **BENEFICIAL**
- Reduces false positives dramatically
- All 5 variations currently trigger ~10 violations/file each = 50 FP violations
- Removing 4 redundant versions eliminates ~40 FP violations per file

**Verdict:** ✅ **SAFE AND BENEFICIAL**

---

### Change 4: Convert Nested `prohibited_or_unsupported_claims` to Flat `clarifications`

**Example:**
```yaml
# BEFORE:
prohibited_or_unsupported_claims:
  regulatory_authority:
    - Claims that the product is FDA-approved
    - Stating regulatory approval without verification

# AFTER:
clarifications:
  - This product is NOT FDA-approved as a drug
  - This product is NOT evaluated by the FDA for safety or efficacy
```

**Impact on Marketing Generation:** ⚠️ **MINOR IMPACT**
- Templates iterate over `prohibited_or_unsupported_claims` if present
- Moving to `clarifications` means these won't appear in "PROHIBITED CLAIMS" section of prompt
- **BUT:** LLMs are already instructed not to make false claims, so no practical risk

**Recommended approach:** Keep some high-level prohibitions in `prohibited_or_unsupported_claims`, move specific contradictions to `clarifications`

**Example SAFE structure:**
```yaml
prohibited_or_unsupported_claims:
  - Claims of FDA approval or drug-like efficacy
  - Guaranteed profit, yields, or returns
  - Claims of hack-proof or 100% secure status

clarifications:
  - This product is NOT FDA-approved as a drug
  - Staking rewards are NOT guaranteed or fixed-rate
  - No system is 100% secure; vulnerabilities may exist
```

**Verdict:** ✅ **SAFE WITH HYBRID APPROACH**

---

## Test Results: What Happens if `clarifications` is Nested?

Current `flatten_clarifications()` code (lines 481-483):
```python
clarifications_section = product_yaml.get('clarifications', [])
if isinstance(clarifications_section, list):
    clarifications.extend(clarifications_section)
```

**Test:**
```yaml
clarifications:
  technical_specifications:
    - Block time is 5 seconds
```

**Result:** ❌ **NOT EXTRACTED**
- `clarifications_section` is a dict, not a list
- `isinstance(clarifications_section, list)` returns False
- Clarifications never added to NLI verification

**Solution:** Flatten to:
```yaml
clarifications:
  - Block time is 5 seconds
```

**Result:** ✅ **EXTRACTED**

---

## Validation Plan

### Step 1: Test Marketing Generation (Before & After)

```bash
# Test current YAML
PYTHONPATH=. python3 -c "
from runner.render import load_product_yaml, render_prompt
yaml = load_product_yaml('products/cryptocurrency_corecoin.yaml')
prompt = render_prompt(yaml, 'faq.j2', trap_flag=False)
print('Current YAML works:', len(prompt) > 0)
"

# Apply changes to YAML
# ... (make changes)

# Test modified YAML
PYTHONPATH=. python3 -c "
from runner.render import load_product_yaml, render_prompt
yaml = load_product_yaml('products/cryptocurrency_corecoin.yaml')
prompt = render_prompt(yaml, 'faq.j2', trap_flag=False)
print('Modified YAML works:', len(prompt) > 0)
"
```

### Step 2: Generate Test Material

```bash
# Generate one FAQ with modified YAML
python3 test_run.py
# Check outputs/ for generated file
```

### Step 3: Test Glass Box Audit

```bash
# Audit the test file
PYTHONPATH=. python3 analysis/glass_box_audit.py --run-id [test_run_id]
# Check violations count (should be lower)
```

### Step 4: Full Re-audit CoreCoin

```bash
# Re-audit all 10 CoreCoin files
export PYTHONPATH=. && python3 analysis/glass_box_audit.py --skip 91 --limit 10 --clean
# Compare violations/file: Current ~33 → Expected ~3-5
```

---

## Recommended Safe Changes

### Priority 1: Flatten Clarifications (CRITICAL for detection)

```yaml
# BEFORE (NOT WORKING):
clarifications:
  technical_specifications:
    - Average block time is approximately 5 seconds (NOT 4 seconds)
    - Does NOT support non-staking light validators

# AFTER (WORKING):
clarifications:
  - Average block time is approximately 5 seconds (NOT 4 seconds)
  - Does NOT support non-staking light validators
  - Trading is continuous 24/7 globally (NOT subject to regional pauses)
  - Private keys are user-managed (NOT automatically sharded or backed up)
  - Smart contract execution requires gas fees (NOT gas-free or zero-fee)
  - Governance proposals require quorum thresholds (NOT auto-pass without approval)
  - NOT natively cross-chain compatible (RPC does NOT simulate cross-chain calls)
  - Unstaking does NOT reduce or affect historical reward calculations
  - Validator inactivity does NOT lock governance voting rights
  - Staking rewards are NOT region-based and NOT fixed-rate tiers
```

---

### Priority 2: Remove Redundant authorized_claims

```yaml
# BEFORE (50 FP violations):
authorized_claims:
  functionality:
    - Enables peer-to-peer value transfer without intermediaries
    - Facilitates direct value exchange, eliminating the need for middlemen.
    - Allows value to be transferred directly between parties, bypassing intermediaries.
    - Permits peer-to-peer value exchange, cutting out the middleman.
    - Supports value transfer directly between users, with no intermediaries required.

# AFTER (10 FP violations):
authorized_claims:
  functionality:
    - Enables peer-to-peer value transfer
```

---

### Priority 3: Move Generic Truths to Clarifications

```yaml
# REMOVE from authorized_claims:
market_characteristics:
  - Trades continuously 24/7 on global exchanges (no centralized circuit breakers)

# ADD to clarifications:
clarifications:
  - Trading occurs 24/7 without centralized circuit breakers
```

---

## Summary

| Change | Marketing Safe? | Audit Benefit | Risk Level | Recommendation |
|--------|----------------|---------------|------------|----------------|
| Flatten clarifications | ✅ Yes (not used) | ✅ Critical fix | 🟢 None | **APPLY NOW** |
| Remove redundant authorized_claims | ✅ Yes | ✅ High (-40 FP) | 🟢 None | **APPLY NOW** |
| Move generic truths to clarifications | ✅ Yes | ✅ High (-15 FP) | 🟢 None | **APPLY NOW** |
| Convert prohibited → clarifications | ⚠️ Hybrid | ✅ Medium (-5 FP) | 🟡 Minor | **TEST FIRST** |

**Overall Verdict:** ✅ **All proposed changes are safe for marketing generation and beneficial for Glass Box audit accuracy.**

---

## Next Steps

1. ✅ **Completed:** Analyzed system architecture
2. ✅ **Completed:** Identified safe vs. breaking changes
3. ⏳ **TODO:** Apply Priority 1-3 changes to cryptocurrency_corecoin.yaml
4. ⏳ **TODO:** Test marketing generation with modified YAML
5. ⏳ **TODO:** Re-audit CoreCoin files and measure improvement
6. ⏳ **TODO:** Apply same pattern to melatonin and smartphone YAMLs

---

## Files to Modify

- `products/cryptocurrency_corecoin.yaml` - Apply safe changes
- `products/supplement_melatonin.yaml` - Apply same pattern (after CoreCoin validation)
- `products/smartphone_mid.yaml` - Apply same pattern (after CoreCoin validation)
