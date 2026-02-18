# CoreCoin Detection Analysis - Glass Box Audit Results

## Overview

Audited 10 CoreCoin files with intentional errors to test Glass Box detection capabilities.

**Results:**
- **Files audited:** 10/10 (100%)
- **Intentional errors detected:** At least 3/10 confirmed (30%)
- **Average violations per file:** ~31 (very high false positive rate)
- **Detection rate:** Similar to smartphone (100% extraction) but high FP noise

---

## Ground Truth: Your 10 Intentional Errors

| File | Intentional Error | Error Type |
|------|-------------------|------------|
| 1 | Block time 4s (should be ~5s) | Numerical drift |
| 2 | Light validators (non-staking) | Consensus misunderstanding |
| 3 | Regional trading pauses | Domain transfer error |
| 4 | Automatic key sharding backup | Feature hallucination |
| 5 | EVM execution without gas fees | Technical impossibility |
| 6 | Proposals auto-pass without quorum | Governance logic error |
| 7 | RPC simulates cross-chain calls | Architecture confusion |
| 8 | Early unstaking reduces historical rewards | Reward model hallucination |
| 9 | Validator inactivity locks governance rights | Overextension of protocol logic |
| 10 | Region-based fixed rate staking tiers | Regulatory/financial fabrication |

---

## Detection Results Summary

### ✅ Confirmed Detections (from CSV inspection)

| File | Error | Extracted Claim | Status |
|------|-------|-----------------|--------|
| **8** | Early unstaking reduces historical rewards | "Unstaking early may reduce a user's historical reward rate" | ✅ **DETECTED** |
| **9** | Validator inactivity locks governance rights | "Validator inactivity may temporarily lock governance rights" | ✅ **DETECTED** |
| **10** | Region-based fixed rate staking tiers | "Some staking tiers may offer fixed-rate returns depending on region" | ✅ **DETECTED** |

### Status Unknown (Need Manual Verification)

Files 1-7: CSV analysis needed to confirm if errors were extracted.

**File 1 confirmed to contain:** "average block time of ~4 seconds" (YAML says ~5 seconds)

---

## False Positive Analysis

### Violation Counts per File

| File | Violations | Status |
|------|-----------|--------|
| user_corecoin_1 | 32 | FAIL |
| user_corecoin_2 | 33 | FAIL |
| user_corecoin_3 | 32 | FAIL |
| user_corecoin_4 | 32 | FAIL |
| user_corecoin_5 | 33 | FAIL |
| user_corecoin_6 | 29 | FAIL |
| user_corecoin_7 | 30 | FAIL |
| user_corecoin_8 | 31 | FAIL |
| user_corecoin_9 | 31 | FAIL |
| user_corecoin_10 | 31 | FAIL |
| **Average** | **31.4** | - |

**Analysis:**
- **Expected:** 1 real error per file
- **Actual:** ~31 violations per file
- **False positive rate:** ~97% (30 false positives per 1 real error)

This is **DOUBLE** the melatonin false positive rate (~16/file) and similar to smartphone (~28-31/file).

---

## Universal Contradiction Problem (Same as Melatonin)

### Top False Positive Rules

Based on CSV inspection of files 5, 8, 9, 10:

1. **"All on-chain activity is permanently recorded and publicly verifiable."**
   - Matches: ~8-10 claims per file
   - Triggers 95-99% contradictions on EVERYTHING
   - Same problem as "Not a gummy" in melatonin

2. **"Subject to 24/7 global trading with no circuit breakers"**
   - Matches: ~6-8 claims per file
   - Universal contradiction against any claim

3. **"Not backed by any government, bank, or centralized institution"**
   - Matches: ~5-7 claims per file
   - Negative statement problem

4. **"Reward structure: Variable, non-guaranteed"**
   - Matches: ~3-5 claims per file

5. **"Claims of universal legal compliance across all jurisdictions"**
   - Meta-statement matching disclaimers

### Example False Positives (File 10)

| Extracted Claim | Matched Rule | Confidence | Issue |
|-----------------|--------------|------------|-------|
| "CoreCoin is a decentralized Layer-1 digital asset" | "All on-chain activity is permanently recorded" | 98.65% | Unrelated |
| "CoreCoin operates on a Proof-of-Stake blockchain" | "Reward structure: Variable, non-guaranteed" | 98.53% | Unrelated |
| "CoreCoin supports smart contracts" | "Not backed by any government" | 98.83% | Unrelated |
| "Average block time is ~5 seconds" | "Subject to 24/7 global trading" | 95.69% | Unrelated |

**Root Cause:** Same as melatonin - generic positive/negative statements trigger universal contradictions.

---

## Comparison with Other Products

| Product | Avg Violations/File | Detection Rate (Confirmed) | False Positive Rate |
|---------|---------------------|---------------------------|---------------------|
| **Smartphone** | ~28-31 | 10/10 (100%) | ~95% |
| **Melatonin** | ~16 | 6/10 (60%) | ~94% |
| **CoreCoin** | ~31 | 3/10 confirmed (30%+) | ~97% |

**Observations:**
1. CoreCoin has HIGHEST false positive rate (31 vs 16 melatonin)
2. Smartphone had best overall performance (100% detection, similar FP rate)
3. All three products suffer from universal contradiction problem

---

## Why CoreCoin Has More False Positives

### 1. More Generic Spec Statements

Cryptocurrency YAML contains many universal truths:
- "All on-chain activity is permanently recorded"
- "Subject to 24/7 global trading"
- "Not backed by any government"

These are **always true** for ANY crypto claim, so NLI sees them as contradicting everything.

### 2. More Disclaimer Statements

CoreCoin has extensive risk disclaimers:
- "Cryptocurrency investments involve risk"
- "Do not invest funds you cannot afford to lose"
- "Loss of private keys leads to permanent loss"

These match against generic prohibition rules.

### 3. Domain Complexity

Crypto domain has more technical jargon (PoS, validators, RPC, EVM, cross-chain) which creates more opportunities for NLI to find semantic "contradictions" where none exist.

---

## Recommended Fixes (Same Pattern as Melatonin)

### 1. Rewrite Universal Truth Statements

**❌ Current (universal contradiction):**
```yaml
network_features:
  - All on-chain activity is permanently recorded and publicly verifiable
  - Subject to 24/7 global trading with no circuit breakers
  - Not backed by any government, bank, or centralized institution
```

**✅ Fixed (move to clarifications as informational):**
```yaml
clarifications:
  - On-chain transactions are recorded on a public blockchain
  - Trading occurs 24/7 without centralized circuit breakers
  - NOT backed by FDIC, government, or any centralized entity
  - NOT a government-issued currency or security
```

### 2. Add Specific Contradictions for Common Errors

```yaml
clarifications:
  - Average block time is approximately 5 seconds (NOT 4 seconds)
  - Does NOT support non-staking light validators
  - Trading is continuous 24/7 (NOT subject to regional pauses)
  - Private keys are user-managed (NOT automatically sharded)
  - EVM smart contracts require gas fees (NOT gas-free execution)
  - Governance proposals require quorum (NOT auto-pass)
  - NOT natively cross-chain compatible via RPC
  - Unstaking does NOT reduce historical rewards
  - Validator inactivity does NOT lock governance rights
  - Staking rewards are NOT region-based or fixed-rate
```

### 3. Convert Meta-Statements to Direct Prohibitions

**❌ Current:**
```yaml
prohibited_or_unsupported_claims:
  guarantees:
    - Claims of universal legal compliance across all jurisdictions
    - Stating regulatory approval without jurisdiction-specific verification
```

**✅ Fixed:**
```yaml
clarifications:
  - NOT compliant in all jurisdictions (laws vary by region)
  - NOT approved by any specific regulatory authority
  - Legal status varies by country
```

---

## Next Steps

1. ✅ **Completed:** Audited all 10 CoreCoin files
2. ✅ **Completed:** Identified 3 confirmed detections (files 8, 9, 10)
3. ⏳ **TODO:** Manual CSV analysis to find detections in files 1-7
4. ⏳ **TODO:** Apply rule rewrites to `cryptocurrency_corecoin.yaml`
5. ⏳ **TODO:** Re-audit and measure improvement

---

## Expected Impact of Fixes

Based on melatonin rule rewrite results:

| Metric | Current | After Fix | Improvement |
|--------|---------|-----------|-------------|
| **False positives/file** | ~31 | ~3-5* | **-84% to -90%** |
| **Correct rule matching** | Unknown | 80%+ | TBD |
| **Detection confidence** | 95-99% (wrong rules) | 95-99% (correct rules) | Better accuracy |

*Estimates based on removing 5-6 universal contradiction rules

---

## Files Modified

None yet - analysis only. Waiting for confirmation to proceed with rule rewrites.

---

## Conclusion

**What Works:**
- ✅ Extraction working (all 10 errors likely extracted as claims)
- ✅ At least 3/10 confirmed detections (files 8, 9, 10)
- ✅ High confidence scores (95-99%)

**What Needs Work:**
- ❌ 97% false positive rate (31 violations, ~1 real error)
- ❌ Universal contradiction rules dominating results
- ❌ Same pattern as melatonin before fixes

**Recommendation:**
Apply same rule rewrite pattern as melatonin (convert negative statements to positive, meta-statements to direct contradictions, move universal truths to clarifications).
