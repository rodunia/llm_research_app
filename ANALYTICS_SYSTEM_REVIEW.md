# Analytics System Review & Upgrade Analysis
## Current State, Improvement Opportunities, Model Upgrade Risks

**Date:** February 18, 2026
**Reviewer:** Claude Code
**Context:** Post-validation comparison study (Glass Box vs LLM Direct)

---

## 1. Current Analytics Architecture

### 1.1 System Components

**Glass Box Audit Pipeline (`analysis/glass_box_audit.py`):**
- **Stage 1 (Extraction):** GPT-4o-mini (temp=0) for atomic claim extraction
- **Stage 2 (Validation):** cross-encoder/nli-roberta-base (DeBERTa) for NLI verification
- **Threshold:** 90% contradiction confidence (recently lowered from 93%)
- **Knowledge Base:** Product YAMLs with authorized_claims, specifications, prohibited_claims, clarifications

**Supporting Modules:**
- `deberta_verify_claims.py` - Batch DeBERTa verification
- `premise_builder.py` - Constructs premise from YAML for NLI
- `claim_extractor.py` - LLM-based atomic claim extraction
- `deberta_nli.py` - NLI model wrapper
- `evaluate.py` - Performance metrics
- `reporting.py` - Result reporting
- `metrics.py` - Analytics metrics

**Current Performance (Validated on 30 Ground Truth Errors):**
- **Overall Detection:** 26/30 (87%)
- **By Product:** Smartphone 100%, Melatonin 100%, CoreCoin 60%
- **False Positive Rate:** ~95% (24 violations/file average)
- **Extraction Success:** 30/30 (100%)
- **Validation Bottleneck:** CoreCoin (40% miss rate)

---

## 2. What We Have (Strengths)

### 2.1 Strong Two-Stage Architecture

✅ **Separation of Concerns:**
- Extraction layer (LLM) handles decomposition → 100% success
- Validation layer (NLI) handles contradiction detection → 87% success
- Clear bottleneck identification: validation, not extraction

✅ **Structured Knowledge Base:**
- YAML-based product specifications
- Explicit authorized_claims, prohibited_claims, clarifications
- Version-controlled, human-readable, easily auditable

✅ **High Recall (87%):**
- Catches most factual errors, numerical drift, feature hallucinations
- Perfect performance on consumer electronics (Smartphone 100%)
- Perfect performance on dietary supplements (Melatonin 100%)

✅ **Deterministic Extraction:**
- GPT-4o-mini at temp=0 ensures reproducibility
- JSON mode forces structured output
- Automatic retries with exponential backoff

✅ **Production-Ready Features:**
- Checkpoint/resume capability for long runs
- Error logging and recovery
- CSV output for easy analysis
- Device detection (CUDA/MPS/CPU)

### 2.2 Comprehensive Validation Infrastructure

✅ **Ground Truth Validation:**
- 30 files with intentional errors documented
- Error type taxonomy (numerical, feature, logical, factual)
- Per-domain error analysis (Smartphone, Melatonin, CoreCoin)

✅ **Comparison Framework:**
- LLM Direct vs Glass Box comparison completed
- Precision-recall trade-off analysis
- Method disagreement tracking
- Visualization pipeline (5 plots)

✅ **Pilot Study Methodology:**
- Academically rigorous validation protocol
- Confidence score analysis
- False positive rate measurement
- Domain-specific performance benchmarks

---

## 3. What Can Be Improved

### 3.1 False Positive Rate (~95%)

**Problem:** System flags ~24 violations per file, only 1 is true positive

**Root Causes:**
1. **Non-selective comparison:** Every extracted claim × every YAML rule → NLI score
   - 30 claims × 25 rules = 750 comparisons per file
   - No semantic pre-filtering

2. **NLI model limitations:**
   - DeBERTa cross-encoder treats all rules equally
   - No awareness of rule relevance (e.g., comparing storage claim against FDA approval rule)
   - Semantic drift causes false contradictions

3. **Threshold tuning insufficient:**
   - 90% threshold still flags too many
   - No confidence calibration across rule types

**Impact:** Manual review burden of 23 false positives per true positive

**Improvement Opportunities:**

**Option 1: Semantic Filtering (Low-Effort, High-Impact)**
- Use embedding similarity to pre-filter relevant rules before NLI
- Compare claim embedding against rule embeddings
- Only run NLI on top 5 most similar rules
- **Expected FP reduction:** 60-80% (from 95% → 40-60%)
- **Cost:** Minimal (embedding inference fast)
- **Risk:** Low (recall likely maintained)

**Option 2: Hybrid LLM-NLI Validation (High-Cost, High-Impact)**
- Replace DeBERTa with GPT-4o or Claude 3.5 Sonnet for validation
- LLM has better semantic understanding of rule relevance
- Can explain violations (interpretability gain)
- **Expected FP reduction:** 70-85% (from 95% → 15-30%)
- **Cost:** High ($0.01-0.03 per comparison vs $0.0001 for DeBERTa)
- **Risk:** Medium (latency increase, cost increase)

**Option 3: Multi-Stage Filtering (Balanced)**
- Stage 1: Embedding similarity filter (top 10 rules)
- Stage 2: DeBERTa NLI (contradiction detection)
- Stage 3: LLM final check on high-confidence violations
- **Expected FP reduction:** 75-90% (from 95% → 10-25%)
- **Cost:** Medium (LLM only for high-confidence flags)
- **Risk:** Low (gradual filtering reduces errors)

**Recommendation:** Start with Option 1 (semantic filtering), then test Option 3 if FP rate still too high.

---

### 3.2 CoreCoin Detection Rate (60%)

**Problem:** Glass Box misses 40% of CoreCoin errors vs 0% for Smartphone/Melatonin

**Missed Errors:**
- user_corecoin_1: Block time 4s vs ~5s (numerical precision)
- user_corecoin_3: Regional trading pauses (domain transfer error)
- user_corecoin_4: Automatic key sharding (feature hallucination)
- user_corecoin_10: Region-based staking tiers (regulatory fabrication)

**Root Causes:**
1. **Semantic ambiguity:** Crypto domain has overlapping terminology
   - "Staking", "validators", "governance", "consensus" have multiple meanings
   - NLI model confuses cross-chain vs native-chain, staking vs non-staking

2. **Complex compound claims:**
   - "Regional trading pauses during maintenance" embedded in long sentence
   - NLI model may not decompose properly

3. **YAML coverage gaps:**
   - Some prohibited claims too specific (e.g., "NOT region-based staking")
   - May need more granular clarifications

**Improvement Opportunities:**

**Option 1: Expand YAML Clarifications (Low-Effort)**
- Add more negative statements to CoreCoin YAML
- Examples:
  - "Block time is NOT fixed at 4 seconds (it's ~5s)"
  - "Staking rewards are NOT region-based"
  - "Key management does NOT include automatic sharding"
- **Expected improvement:** 60% → 75-80%
- **Risk:** Low (more explicit rules help NLI)

**Option 2: Domain-Specific NLI Fine-Tuning (High-Effort)**
- Fine-tune DeBERTa on cryptocurrency fact-checking dataset
- Create synthetic dataset from crypto whitepapers + violations
- **Expected improvement:** 60% → 80-90%
- **Risk:** High (requires ML expertise, data labeling, GPU resources)

**Option 3: LLM-Based NLI for Complex Domains (Medium-Effort)**
- Use LLM (GPT-4o/Claude) for CoreCoin validation only
- Keep DeBERTa for Smartphone/Melatonin (cheaper)
- **Expected improvement:** 60% → 80-85%
- **Cost:** Medium (LLM only for 1/3 of products)
- **Risk:** Low (proven LLM advantage on complex domains)

**Recommendation:** Try Option 1 first (expand YAML), then test Option 3 (LLM-based NLI for CoreCoin).

---

### 3.3 Extraction Model (GPT-4o-mini)

**Current Status:** 100% extraction success on pilot study

**Question:** Should we upgrade GPT-4o-mini → GPT-4o or Claude 3.5 Sonnet?

**Analysis:**

**Evidence AGAINST Upgrade:**
- Extraction already perfect (30/30, 100%)
- Bottleneck is validation (87%), not extraction (100%)
- GPT-4o-mini at temp=0 is deterministic and reliable
- Cost savings: GPT-4o-mini is 60x cheaper than GPT-4o

**Evidence FOR Upgrade:**
- Better claim decomposition (fewer compound claims)
- More accurate terminology preservation
- Potentially better disclaimer separation

**Cost-Benefit Analysis:**

| Model | Cost per File | Detection Gain | FP Reduction | ROI |
|-------|---------------|----------------|--------------|-----|
| **GPT-4o-mini** | $0.002 | Baseline (87%) | Baseline (95%) | N/A |
| **GPT-4o** | $0.012 | +0-5% (est.) | -5-10% (est.) | Low |
| **Claude 3.5 Sonnet** | $0.015 | +0-5% (est.) | -10-15% (est.) | Low-Medium |

**Recommendation:** **DO NOT upgrade extraction model.** Focus optimization on validation layer (false positive reduction, CoreCoin improvement). Only upgrade extraction if future domains show extraction failures.

---

### 3.4 Validation Model (DeBERTa NLI)

**Current Model:** cross-encoder/nli-roberta-base (125M parameters)

**Question:** Should we upgrade to larger/better NLI model?

**Upgrade Options:**

**Option A: DeBERTa-v3-large-mnli (435M parameters)**
- **Pros:** More parameters, better semantic understanding
- **Cons:** 3.5x slower, higher GPU memory
- **Expected gain:** +5-10% detection, -10-20% FP
- **Cost:** Minimal (still local inference)

**Option B: BART-large-mnli (406M parameters)**
- **Pros:** Strong on complex reasoning
- **Cons:** Slower inference
- **Expected gain:** +5-8% detection, -15-25% FP
- **Cost:** Minimal

**Option C: Hybrid LLM-NLI (GPT-4o or Claude 3.5 Sonnet)**
- **Pros:** Best semantic understanding, explainable, can handle nuance
- **Cons:** 100-300x cost increase, API latency
- **Expected gain:** +10-15% detection, -60-80% FP
- **Cost:** High ($0.01-0.03 per comparison)

**Recommendation:** Test Option A (DeBERTa-v3-large) first. If FP rate still >80%, consider Option C (hybrid LLM-NLI) for high-stakes validation.

---

## 4. Model Upgrade Risks & Challenges

### 4.1 Extraction Model Upgrade Risks

**Risk 1: Determinism Loss**
- **Problem:** Larger models (GPT-4o, Claude) may have more variability even at temp=0
- **Impact:** Reproducibility issues for research
- **Mitigation:** Test variance across 10 runs, measure standard deviation

**Risk 2: Cost Explosion**
- **Problem:** GPT-4o is 60x more expensive than GPT-4o-mini
- **Impact:** $0.002/file → $0.12/file (for 1,620 experiments = $194 → $11,640)
- **Mitigation:** Only upgrade if extraction failures observed

**Risk 3: Over-Decomposition**
- **Problem:** Better models may atomize claims too aggressively
- **Impact:** More claims → more comparisons → higher FP rate
- **Mitigation:** Test on pilot study first, measure claim count inflation

**Risk 4: JSON Formatting Failures**
- **Problem:** Some LLMs less reliable at JSON mode
- **Impact:** Parsing failures, missed extractions
- **Mitigation:** Use structured output guarantees (OpenAI JSON mode, Anthropic structured output)

### 4.2 Validation Model Upgrade Risks

**Risk 1: False Negative Increase (Lower Recall)**
- **Problem:** Larger NLI models may be more conservative
- **Impact:** Detection rate drops from 87% → 75-80%
- **Mitigation:** Test on ground truth pilot study first, ensure recall maintained

**Risk 2: Threshold Recalibration Required**
- **Problem:** Different NLI models have different score distributions
- **Impact:** Current 90% threshold may be too high or too low
- **Mitigation:** Rerun threshold optimization on pilot study (test 85%, 90%, 95%, 97%)

**Risk 3: GPU Memory Constraints**
- **Problem:** Larger models (DeBERTa-v3-large 435M params) may not fit on available GPUs
- **Impact:** Forced to use CPU → 10-50x slower inference
- **Mitigation:** Check GPU memory availability, batch size optimization

**Risk 4: Inference Latency**
- **Problem:** Larger models 3-5x slower per comparison
- **Impact:** 750 comparisons/file × 3x slower = hours per audit
- **Mitigation:** Semantic pre-filtering to reduce comparisons (750 → 150)

**Risk 5: LLM API Dependency (If Using Hybrid LLM-NLI)**
- **Problem:** Rate limits, API downtime, cost unpredictability
- **Impact:** Validation pipeline failures, budget overruns
- **Mitigation:** Implement retry logic, circuit breakers, cost monitoring

### 4.3 Research Validity Risks

**Risk 1: Invalidates Prior Results**
- **Problem:** Upgrading models mid-study breaks comparability
- **Impact:** Cannot compare old vs new results (different detection systems)
- **Mitigation:** Version all results, clearly document model changes, rerun pilot study

**Risk 2: Reproducibility Loss**
- **Problem:** LLM APIs change over time (model updates, deprecations)
- **Impact:** Future researchers cannot replicate exact results
- **Mitigation:** Pin model versions, archive prompts, save raw outputs

**Risk 3: Goal Post Moving**
- **Problem:** Continuous upgrades prevent finalizing research conclusions
- **Impact:** "Just one more upgrade" syndrome delays publication
- **Mitigation:** Set clear stopping criteria (e.g., 90% detection, <50% FP)

---

## 5. Recommendation: Phased Upgrade Strategy

### Phase 1: Low-Risk, High-Impact Optimizations (Weeks 1-2)

**Focus:** False positive reduction without model changes

1. **Semantic Pre-Filtering (Priority 1)**
   - Add embedding similarity filter before NLI
   - Reduce comparisons from 750 → 150 per file
   - **Expected:** 60-80% FP reduction, no recall loss
   - **Cost:** Minimal (add sentence-transformers)

2. **Expand CoreCoin YAML (Priority 2)**
   - Add 10-15 more clarifications for missed errors
   - Target 4 missed errors from pilot study
   - **Expected:** CoreCoin 60% → 75-80%
   - **Cost:** Minimal (manual YAML editing)

3. **Threshold Optimization (Priority 3)**
   - Test 85%, 90%, 95%, 97% thresholds on pilot study
   - Plot precision-recall curve
   - **Expected:** Find optimal FP-recall trade-off
   - **Cost:** Minimal (rerun analysis)

**Validation:** Rerun pilot study, measure recall (should stay ≥87%) and FP rate (target <60%)

---

### Phase 2: Validation Model Upgrade (Weeks 3-4)

**Focus:** Improve detection on complex domains (CoreCoin)

1. **Test DeBERTa-v3-large (Priority 1)**
   - Upgrade NLI model: cross-encoder/nli-roberta-base → microsoft/deberta-v3-large-mnli
   - Rerun pilot study
   - **Success criteria:** CoreCoin 60% → 80%+, FP rate <70%
   - **Cost:** Minimal (local inference)

2. **If DeBERTa-v3-large insufficient:**
   - **Test Hybrid LLM-NLI for CoreCoin only**
   - Use GPT-4o or Claude 3.5 Sonnet for CoreCoin validation
   - Keep DeBERTa for Smartphone/Melatonin
   - **Success criteria:** CoreCoin 60% → 85%+, FP rate <50%
   - **Cost:** Medium ($0.02-0.05 per CoreCoin file)

**Validation:** Rerun pilot study, ensure no regression on Smartphone/Melatonin

---

### Phase 3: Full LLM-NLI Hybrid (Month 2, If Needed)

**Focus:** Achieve <30% false positive rate for production deployment

1. **Replace DeBERTa with LLM-based NLI across all products**
   - Use GPT-4o or Claude 3.5 Sonnet for all validation
   - Implement multi-stage filtering (embedding → DeBERTa → LLM)
   - **Success criteria:** Overall FP <30%, detection ≥85%
   - **Cost:** High ($0.60 per file → $972 for 1,620 experiments)

2. **Cost Optimization**
   - Use GPT-4o-mini for low-confidence rules (entailment likely)
   - Use GPT-4o for high-stakes rules (prohibited claims, specs)
   - Batch API for 50% cost reduction

**Validation:** Rerun pilot study + new validation set (30 more files)

---

### Phase 4: Extraction Model Upgrade (Only If Needed)

**Trigger Condition:** Extraction failures observed on new domains (medical, legal, financial)

**Upgrade Path:**
1. Test GPT-4o vs Claude 3.5 Sonnet on 30 files
2. Measure extraction accuracy, claim count, cost
3. If improvement <10%, reject upgrade
4. If improvement >10%, deploy to new domains only

**DO NOT upgrade extraction unless failures occur.**

---

## 6. Cost Analysis: Model Upgrade Impact

### Current System (Baseline)

**Per-File Cost:**
- Extraction (GPT-4o-mini): $0.002
- Validation (DeBERTa): $0.001 (GPU amortized)
- **Total:** $0.003 per file

**Full Experiment (1,620 files):**
- **Total cost:** $4.86

---

### Option A: DeBERTa-v3-large Upgrade

**Per-File Cost:**
- Extraction (GPT-4o-mini): $0.002
- Validation (DeBERTa-v3-large): $0.002 (slower, GPU amortized)
- **Total:** $0.004 per file

**Full Experiment:** $6.48 (+33% cost)
**Expected gain:** +5-10% detection, -10-20% FP

**ROI:** **High** (minimal cost increase, significant FP reduction)

---

### Option B: Hybrid LLM-NLI (CoreCoin Only)

**Per-File Cost:**
- Smartphone/Melatonin: $0.003 (baseline)
- CoreCoin: $0.025 (LLM validation)
- **Average:** $0.010 per file

**Full Experiment:** $16.20 (+233% cost)
**Expected gain:** CoreCoin 60% → 85%, overall FP -20-30%

**ROI:** **Medium** (moderate cost, targets weakest domain)

---

### Option C: Full LLM-NLI Replacement

**Per-File Cost:**
- Extraction (GPT-4o-mini): $0.002
- Validation (GPT-4o): $0.030
- **Total:** $0.032 per file

**Full Experiment:** $51.84 (+966% cost)
**Expected gain:** +10-15% detection, -60-80% FP

**ROI:** **High IF** manual review burden reduction saves >$47 in labor
- Assume manual review: $50/hour
- Current FP burden: 23 FPs per TP × 30 files = 690 FPs
- Review time: ~2 min/FP = 23 hours = $1,150
- After LLM-NLI: 5 FPs per TP × 30 files = 150 FPs = 5 hours = $250
- **Labor savings:** $900 vs cost increase $47 = **18x ROI**

**Recommendation:** Full LLM-NLI economically justified for production deployment (not pilot study)

---

## 7. Decision Matrix: When to Upgrade?

| Scenario | Recommended Action | Priority |
|----------|-------------------|----------|
| **Current Pilot Study Complete** | Phase 1 (Semantic filtering + YAML) | **DO NOW** |
| **Preparing for Production** | Phase 3 (Full LLM-NLI) | **High** |
| **Budget Constrained** | Phase 1 + Phase 2 (DeBERTa-v3-large) | **Medium** |
| **CoreCoin Detection <70%** | Phase 2 (Hybrid LLM for CoreCoin) | **High** |
| **False Positive Rate >80%** | Phase 1 → Phase 3 | **High** |
| **Extraction Failures Observed** | Phase 4 (Upgrade extraction) | **As Needed** |
| **Research Publication Goal** | Stay on Phase 1-2 (reproducible) | **Medium** |
| **Commercial Deployment** | Phase 3 (LLM-NLI for all) | **High** |

---

## 8. Key Takeaways

### What Works Well (Keep)
1. ✅ Two-stage architecture (extraction + validation)
2. ✅ YAML-based knowledge base (structured, version-controlled)
3. ✅ GPT-4o-mini extraction (100% success, cheap)
4. ✅ Checkpoint/resume system (production-ready)
5. ✅ Ground truth validation methodology

### What Needs Improvement (Prioritize)
1. 🔴 False positive rate (95% → target <30%)
2. 🔴 CoreCoin detection (60% → target 85%+)
3. 🟡 Manual review burden (23 FPs per TP)
4. 🟡 Threshold calibration (test 85-97%)

### Model Upgrade Recommendations
1. **DO NOT upgrade extraction model** (already perfect)
2. **Test DeBERTa-v3-large first** (low cost, likely FP reduction)
3. **Consider hybrid LLM-NLI for CoreCoin** (targets weakest domain)
4. **Deploy full LLM-NLI for production** (18x ROI from labor savings)

### Biggest Risks
1. **Cost explosion** (full LLM-NLI 10x more expensive)
2. **Reproducibility loss** (API model updates)
3. **False negative increase** (larger models more conservative)
4. **Scope creep** ("just one more upgrade" syndrome)

### Next Steps
1. **Week 1:** Implement semantic pre-filtering (embedding similarity)
2. **Week 2:** Expand CoreCoin YAML + threshold optimization
3. **Week 3:** Test DeBERTa-v3-large on pilot study
4. **Week 4:** Decide Phase 3 based on results

---

## 9. Conclusion

Your analytics system is **well-architected with a clear bottleneck** (validation FP rate, not extraction). The comparison study proves that **two-stage architecture >> single-stage** (87% vs 43% detection), validating your design choices.

**Do NOT upgrade extraction model** - it's already perfect. **Focus all optimization on validation layer**:
1. Semantic pre-filtering (low-hanging fruit)
2. Expand CoreCoin YAML (quick win)
3. Test larger NLI models (DeBERTa-v3-large)
4. Deploy hybrid LLM-NLI for production (justified by labor savings)

The phased approach minimizes risk while maximizing improvement. Start with Phase 1 (low-cost optimizations), validate on pilot study, then decide Phase 2-3 based on results.

**Most Important:** Don't let perfect be the enemy of good. 87% detection is already strong - focus on FP reduction (95% → 30%) before chasing 100% recall.
