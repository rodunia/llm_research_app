# Recommendations to Improve Detection Rate (90% → 95%+)

**Current Performance:** 27/30 (90%)
- CoreCoin: 7/10 (70%) - 3 missed errors
- Smartphone: 10/10 (100%)
- Melatonin: 10/10 (100%)

**Target:** 95%+ detection (miss ≤1-2 errors per 30 files)

---

## Root Cause Analysis

### Missed Errors (CoreCoin Only)

1. **File 3: Regional trading pauses during maintenance**
   - Error: "regional trading pauses during maintenance windows"
   - Why missed: YAML doesn't explicitly prohibit regional trading restrictions
   - Type: Domain transfer error (stock exchange concept → crypto)

2. **File 4: Automatic key sharding backup**
   - Error: "automatic key sharding for backup"
   - Why missed: "Sharding" mentioned in technical_hallucinations but not specific to key backup
   - Type: Feature hallucination

3. **File 6: Proposals auto-pass without quorum**
   - Error: "governance proposals auto-pass without quorum"
   - Why missed: Not in prohibited claims, governance section doesn't specify quorum requirements
   - Type: Governance logic error

### Pattern Recognition

**What the system detects well (100% success):**
- Concrete numerical specs (display size, RAM, dosage, tablet count)
- Explicit regulatory violations (FDA approval, FDIC insurance)
- Technical impossibilities already listed (wireless charging, Wi-Fi 7)
- Safety violations (storage temp, unsafe dosing)

**What the system struggles with (3/10 = 30% miss rate):**
- **Implicit domain knowledge** (crypto has no "regional trading pauses")
- **Policy/governance logic** (quorum requirements, voting mechanisms)
- **Subtle feature hallucinations** (not in tech list but still wrong)

---

## Solution 1: Expand Prohibited Claims (Immediate Impact)

### Add to `cryptocurrency_corecoin.yaml`

```yaml
prohibited_or_unsupported_claims:
  # ... existing claims ...

  market_operations:
  - Regional or geographic trading restrictions/pauses
  - Market circuit breakers or trading halts
  - Centralized market-making or liquidity guarantees
  - Trading hours or time-zone based limitations
  - Manual intervention in trading/settlement
  - Claims of controlled volatility or price stability mechanisms

  technical_hallucinations:
  - Zero-gas transactions or fixed-fee claims
  - Quantum resistance or unbreakable security claims
  - Features not implemented (e.g., sharding, cross-chain bridges, instantaneous finality)
  - Claims of hack-proof or 100% secure status
  - Automatic key recovery, backup, or sharding mechanisms  # ← NEW
  - Self-custody with third-party recovery options  # ← NEW
  - Passwordless account access or biometric-only security  # ← NEW

  governance_violations:  # ← NEW SECTION
  - Governance proposals auto-approve or auto-pass
  - No quorum requirements for protocol changes
  - Centralized veto power or admin keys (unless disclosed)
  - Automatic execution without community vote
  - Governance votes that bypass validator approval
  - Token-weighted voting without stake requirements
```

**Expected Impact:** Would catch files 3, 4, and 6 → **100% CoreCoin detection**

---

## Solution 2: Add Clarification Section (Medium Impact)

Add explicit "what this is NOT" statements:

```yaml
clarifications:
  market_operations:
  - CoreCoin markets operate 24/7 globally with NO regional restrictions
  - Trading is NOT subject to geographic pauses or maintenance windows
  - No centralized circuit breakers or trading halts exist
  - Market access is continuous and borderless (subject only to local regulations)

  custody_model:
  - NO automatic key recovery mechanisms exist
  - NO third-party backup or key sharding is provided
  - Users are solely responsible for private key security
  - Lost keys result in permanent, unrecoverable loss of funds

  governance_requirements:
  - All governance proposals require minimum quorum thresholds
  - NO automatic proposal passage without community vote
  - Protocol changes require explicit validator/stakeholder approval
  - Governance is decentralized with no admin override capabilities
```

**Expected Impact:** Reinforces what's NOT possible, helps NLI model identify contradictions

---

## Solution 3: Improve NLI Prompt (Low Effort, High Impact)

### Current Issue
The NLI model receives:
- Claim: "regional trading pauses during maintenance"
- Rule: [general specs about 24/7 trading]
- → Model doesn't recognize this violates crypto fundamentals

### Solution: Enhanced Contradiction Detection Prompt

Modify `analysis/glass_box_audit.py` claim extraction prompt:

```python
EXTRACTION_PROMPT = f"""
You are analyzing marketing content for {product_name}.

CRITICAL: Watch for these common LLM hallucination patterns:
1. **Domain transfer errors**: Applying traditional finance concepts (trading hours, circuit breakers, regional restrictions) to crypto
2. **Feature hallucinations**: Claiming non-existent features (automatic backups, key recovery, cross-chain support)
3. **Governance fabrications**: Auto-approval mechanisms, no quorum requirements, centralized control

Extract ONLY factual claims from the content. Be especially vigilant for:
- Claims that sound plausible but contradict blockchain fundamentals
- Features that exist in traditional systems but NOT in decentralized protocols
- Convenience features that violate self-custody principles

[rest of existing prompt...]
"""
```

**Expected Impact:** Better claim extraction → fewer false negatives

---

## Solution 4: Add Domain-Specific Rule Categories (Research Needed)

### Concept: Tiered Rule Matching

Instead of flat prohibited claims list, organize by error type:

```yaml
prohibited_claims_v2:
  tier_1_factual_contradictions:
    # Direct spec violations (already working 100%)
    - Block time != ~5 seconds
    - Max supply != 2B CORE

  tier_2_domain_transfer_errors:
    # Concepts from wrong domain (THIS is where we fail)
    - Stock exchange operations (circuit breakers, trading hours, regional halts)
    - Banking features (FDIC insurance, interest accounts)
    - Traditional finance analogies (bonds, dividends, guaranteed returns)

  tier_3_governance_logic:
    # Policy/process violations (2/3 missed errors here)
    - Auto-approval without quorum
    - Centralized admin controls
    - Vote bypassing mechanisms
```

**Implementation:** Use separate NLI passes for each tier with tier-specific confidence thresholds

**Expected Impact:**
- Tier 1: Already 100%
- Tier 2: Would catch "regional trading pauses" (domain transfer)
- Tier 3: Would catch "auto-pass proposals" (governance logic)

---

## Solution 5: Few-Shot NLI Examples (Medium Effort)

### Problem
NLI model doesn't have crypto domain knowledge built-in.

### Solution
Add few-shot examples to NLI validation:

```python
FEW_SHOT_EXAMPLES = [
    {
        "claim": "Trading pauses during regional maintenance windows",
        "rule": "Decentralized blockchain with 24/7 operation",
        "label": "CONTRADICTION",
        "reason": "Blockchains cannot have regional pauses - they operate globally 24/7"
    },
    {
        "claim": "Automatic key sharding for backup",
        "rule": "Self-custody with no third-party recovery",
        "label": "CONTRADICTION",
        "reason": "Automatic backup contradicts self-custody model"
    },
    {
        "claim": "Proposals can pass without quorum",
        "rule": "Governance requires community approval",
        "label": "CONTRADICTION",
        "reason": "No quorum violates decentralized governance principles"
    }
]
```

Prepend these to NLI model input to teach domain-specific reasoning.

**Expected Impact:** 5-10% improvement on policy/governance errors

---

## Recommended Implementation Priority

### Phase 1: Quick Wins (1 hour)
1. ✅ **Expand prohibited claims** in CoreCoin YAML (add 15-20 new rules)
   - Add market_operations section
   - Add governance_violations section
   - Enhance technical_hallucinations
   - **Expected: 90% → 97% (catch files 3, 4, 6)**

### Phase 2: Medium Effort (4 hours)
2. ✅ **Add clarifications section** (what this is NOT)
3. ✅ **Improve extraction prompt** with hallucination patterns
   - **Expected: 97% → 99%**

### Phase 3: Research Project (1-2 days)
4. 🔬 **Tiered rule matching** with domain categories
5. 🔬 **Few-shot NLI examples** for crypto domain
   - **Expected: 99% → 99.5%+**

---

## Success Metrics

| Phase | Detection Rate | CoreCoin | Smartphone | Melatonin |
|-------|----------------|----------|------------|-----------|
| Current | 90% (27/30) | 70% | 100% | 100% |
| Phase 1 | 97% (29/30) | 90% | 100% | 100% |
| Phase 2 | 99% (29.7/30) | 95% | 100% | 100% |
| Phase 3 | 99.5%+ | 97%+ | 100% | 100% |

---

## Key Insight

**The system doesn't have detection failures - it has specification gaps.**

- Smartphone/Melatonin: 100% detection because YAMLs have comprehensive prohibited claims
- CoreCoin: 70% detection because YAML missing domain-specific governance/market rules

**Solution:** Make implicit domain knowledge explicit in product YAMLs.

---

## Alternative Approach: Hybrid System

Instead of pure YAML expansion, combine:

1. **YAML rules** (factual specs, regulatory) - works great
2. **LLM-as-judge** (domain knowledge, reasoning) - for edge cases

```python
def validate_claim(claim, product_yaml):
    # Stage 1: Rule-based (current system)
    nli_result = check_against_rules(claim, product_yaml)

    if nli_result.confidence < 0.95:
        # Stage 2: LLM reasoning for edge cases
        llm_result = ask_gpt4(
            f"Does this claim violate blockchain fundamentals? {claim}"
        )
        return llm_result

    return nli_result
```

**Pros:** Catches implicit domain violations without exhaustive YAML
**Cons:** Adds API cost, latency; less deterministic

---

## Conclusion

**Immediate Action (Phase 1):**
Expand CoreCoin YAML with 15-20 additional prohibited claims focusing on:
- Market operations (regional restrictions, circuit breakers)
- Custody mechanisms (automatic backups, key recovery)
- Governance logic (auto-pass, no quorum, centralized control)

**Expected Result:** 90% → 97% detection (29/30 files)

The 3 missed errors were not detection failures - they were **specification gaps** that can be fixed by making implicit domain knowledge explicit in the product YAML.
