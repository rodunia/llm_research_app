# CoreCoin YAML Improvements Summary

## Changes Applied

### 1. Removed Redundant authorized_claims ✅

**Functionality section** (reduced from 25 to 5 claims):
```yaml
# BEFORE: 5 variations of each claim = 25 total
- Enables peer-to-peer value transfer without intermediaries
- Facilitates direct value exchange, eliminating the need for middlemen.
- Allows value to be transferred directly between parties, bypassing intermediaries.
- Permits peer-to-peer value exchange, cutting out the middleman.
- Supports value transfer directly between users, with no intermediaries required.
# ... (repeated for 5 different claims)

# AFTER: 1 canonical version of each = 5 total
- Enables peer-to-peer value transfer
- Supports decentralized applications and programmable smart contracts
- Facilitates peer-to-peer transactions
- Provides borderless transaction capability
- Supports DeFi integration for decentralized finance applications
```

**Network_security section** (reduced from 20 to 4 claims)
**Potential_utility section** (reduced from 15 to 3 claims)
**Governance section** (reduced from 15 to 3 claims)

**Total reduction:** ~60 redundant claims removed

---

### 2. Flattened Clarifications Structure ✅

**BEFORE (nested - NOT extracted by flatten_clarifications()):**
```yaml
clarifications:
  financial_status:
    - Not a bank account, deposit, or savings product
    - NOT FDIC-insured or government-backed
  technical_specifications:
    - Average block time is approximately 5 seconds (NOT 4 seconds)
    - Does NOT support non-staking light validators
    - Trading is continuous 24/7 globally (NOT subject to regional pauses)
    # ... 8 more critical clarifications
```

**AFTER (flat list - properly extracted):**
```yaml
clarifications:
  - Not a bank account, deposit, or savings product
  - NOT FDIC-insured or government-backed
  - Average block time is approximately 5 seconds (NOT 4 seconds)
  - Does NOT support non-staking light validators
  - Trading is continuous 24/7 globally (NOT subject to regional pauses or trading hours)
  - Private keys are user-managed (NOT automatically sharded or backed up)
  - Smart contract execution requires gas fees (NOT gas-free or zero-fee)
  - Governance proposals require quorum thresholds (NOT auto-pass without approval)
  - NOT natively cross-chain compatible (RPC does NOT simulate cross-chain calls)
  - Unstaking does NOT reduce or affect historical reward calculations
  - Validator inactivity does NOT lock governance voting rights
  - Staking rewards are NOT region-based and NOT fixed-rate tiers
```

**Impact:** 32 clarifications now properly extracted (was 0 before flattening)

---

### 3. Removed FP Culprits from specs.market_characteristics ✅

**BEFORE:**
```yaml
specs:
  market_characteristics:
    - Market value is highly volatile and influenced by liquidity, market sentiment,
      and macroeconomic conditions
    - Trading volume is publicly verifiable on major exchanges  ← 9 FP violations
    - Liquidity varies by exchange and market conditions
    - Price discovery occurs through decentralized market mechanisms
    - Trades continuously 24/7 on global exchanges (no centralized circuit breakers)  ← 66 FP violations
```

**AFTER:**
```yaml
specs:
  market_characteristics:
    - Market value is highly volatile and influenced by liquidity, market sentiment,
      and macroeconomic conditions
    - Liquidity varies by exchange and market conditions
    - Price discovery occurs through decentralized market mechanisms
```

**Impact:** Removed 2 lines causing 75 false positive violations

---

## Test Results

### Marketing Generation Validation ✅
```bash
Prompt length: 15,621 characters
Clarifications count: 32
✅ YAML is valid and templates work
```

---

## Detection Results After Improvements

### File 5 Test (user_corecoin_5.txt):
- **Violations:** 35 (no reduction in count yet)
- **Gas fee error detected:** ✅ YES at 99.37% confidence (CORRECT rule)
- **"Trades continuously 24/7 on global exchanges" rule:** ❌ NO LONGER APPEARS (eliminated)

### Current Top False Positive Rules (from single file audit):
1. **"Smart contract execution requires gas fees (NOT gas-free or zero-fee)"** - 10 violations
   - 1 is real error (99.37% confidence)
   - 9 are false positives

2. **"Trading is continuous 24/7 globally (NOT subject to regional pauses or trading hours)"** - 6 violations
   - All false positives (clarification matching everything)

3. **"Not a bank account, deposit, or savings product"** - 6 violations
   - All false positives

4. **"Pump, moon, or other speculative terminology"** - 2 violations
   - All false positives

---

## Detection Analysis (Before Cleanup - OLD YAML)

Ran batch audit on 10 CoreCoin files with OLD YAML (before removing "Trades 24/7" from specs):

| File | Error | Detection Status | Matched Rule | Confidence |
|------|-------|-----------------|--------------|------------|
| 2 | Light validators | ❌ Detected (wrong rule) | "Smart contract gas fees" | 95.40% |
| 3 | Regional pauses | ❌ NOT detected | - | - |
| 4 | Key sharding | ❌ NOT detected | - | - |
| 5 | Gas fees | ✅ **CORRECT** | "Smart contract gas fees" | 99.37% |
| 6 | Auto-pass quorum | ❌ NOT detected | - | - |
| 7 | RPC cross-chain | ✅ Detected (wrong rule) | "Pump, moon" | 97.40% |
| 8 | Unstaking rewards | ✅ **CORRECT** | "Unstaking does NOT reduce" | 99.82% |
| 9 | Inactivity locks | ❌ Detected (wrong rule) | "Smart contract gas fees" | 94.80% |
| 10 | Region staking | ✅ **CORRECT** | "NOT region-based tiers" | 99.81% |

**Detection rate:** 6/9 (67%)
**Correct rule matching:** 3/6 (50%) ← **IMPROVED from 1/8 (12.5%)**
**Average violations per file:** ~33
**False positive rate:** 97%

---

## Key Findings

### ✅ What Improved:
1. **Correct rule matching improved 4x:** From 12.5% to 50%
   - Gas fees: 99.37% ✅
   - Unstaking: 99.82% ✅
   - Region staking: 99.81% ✅

2. **Eliminated worst FP culprit:** "Trades continuously 24/7 on global exchanges" no longer appears

3. **Clarifications properly extracted:** 32 items now available for NLI verification

### ❌ What Still Needs Work:
1. **No reduction in violation count:** Still ~35 violations/file
2. **Clarifications causing FP:** "Trading is continuous 24/7 globally" (clarification version) still matches everything (6 FP per file)
3. **3 errors still not extracted:**
   - File 3: Regional trading pauses
   - File 4: Automatic key sharding
   - File 6: Auto-pass without quorum

---

## Root Cause Analysis: Why Clarifications Trigger FP

**Problem:** Clarifications with universal truths still act as universal contradictions

**Example:**
```yaml
clarifications:
  - Trading is continuous 24/7 globally (NOT subject to regional pauses or trading hours)
```

This matches claims like:
- "Staking CoreCoin requires locking tokens" (96.41% contradiction) ❌
- "The lockup period is governance-defined" (99.19% contradiction) ❌
- "CoreCoin is not natively cross-chain compatible" (96.09% contradiction) ❌

**Why?** NLI model sees "Trading is continuous 24/7" as a universal positive statement that contradicts ANY neutral/negative statement.

---

## Next Steps

### Option 1: Remove Universal Truths from Clarifications ⚠️
Move statements like "Trading is continuous 24/7" entirely to prohibited_or_unsupported_claims as:
```yaml
prohibited_or_unsupported_claims:
  - Claims that trading has regional pauses or downtime
```

**Risk:** LLMs won't see the positive fact, only the prohibition.

### Option 2: Keep Only Negative Clarifications ✅
Remove positive statements from clarifications, keep only:
```yaml
clarifications:
  - NOT FDIC-insured or government-backed
  - Does NOT support non-staking light validators
  - Smart contract execution requires gas fees (NOT gas-free or zero-fee)
  - Governance proposals require quorum (NOT auto-pass without approval)
  - NOT natively cross-chain compatible
  - Unstaking does NOT reduce historical reward calculations
  - Validator inactivity does NOT lock governance voting rights
  - Staking rewards are NOT region-based and NOT fixed-rate tiers
```

Remove these (contain positive statements):
```yaml
# REMOVE:
  - Trading is continuous 24/7 globally (NOT subject to regional pauses or trading hours)
  - Private keys are user-managed (NOT automatically sharded or backed up)
  - Average block time is approximately 5 seconds (NOT 4 seconds)
```

### Option 3: Improve Category Matching to Reduce Comparisons 🔬
The current category system may not be filtering enough. Need to investigate why NLI is comparing:
- "Trading is continuous 24/7" (market operations)
- vs "Lockup period is governance-defined" (staking mechanics)

These should be in different semantic categories.

---

## Expected Impact (Option 2)

| Metric | Current | After Option 2 | Improvement |
|--------|---------|----------------|-------------|
| Correct rule matching | 3/6 (50%) | 6/6 (100%) | +50% |
| Violations per file | ~35 | ~15-20 | -43% to -57% |
| False positive rate | 97% | 90-93% | -4% to -7% |

**Reasoning:** Removing 3 positive-statement clarifications will eliminate ~15-18 FP per file (6 + 4 + 5 violations respectively).

---

## Files Modified

- `products/cryptocurrency_corecoin.yaml` - Applied all 3 improvements
- `scripts/analyze_corecoin_errors.py` - Detection analysis
- `results/final_audit_results.csv` - Audit results (test file 5)
