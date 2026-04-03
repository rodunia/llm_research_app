# Experimental Branch Results: 30/30 (100%) Detection

**Branch**: `experimental/ram-category-fix`
**Date**: 2026-02-25
**Baseline**: 29/30 (96.7%) on main branch

---

## Summary

✅ **ACHIEVED 30/30 (100%) DETECTION**

- **Gained**: smartphone_4 (16 GB RAM error)
- **Maintained**: All 29 baseline detections
- **Lost**: None

---

## Detection Breakdown by Product

| Product | Detection Rate | Status |
|---------|---------------|--------|
| Melatonin | 10/10 (100%) | ✅ All detected |
| Smartphone | 10/10 (100%) | ✅ All detected (fixed smartphone_4) |
| CoreCoin | 10/10 (100%) | ✅ All detected |

---

## Key Improvements

### 1. Numerical Rule-Based Pre-Check
**Location**: `analysis/glass_box_audit.py:300-318`

Extracts numbers with units and detects contradictions before NLI:
- "16 GB" vs "8 GB or 12 GB" → Direct mismatch (1.0000 confidence)
- "60W" vs "30-45W" → Direct mismatch (1.0000 confidence)

### 2. Category-Aware Matching
**Location**: `analysis/glass_box_audit.py:353-371`

Only checks numerical contradictions within same category:
- RAM claim only compared against RAM specs (not storage)
- Prevents false matches across categories

### 3. Keyword Reordering
**Location**: `analysis/glass_box_audit.py:661-662`

Fixed category classification priority:
- Moved 'ram' before 'storage' 
- Removed 'gb' and 'memory' from storage keywords
- Prevents "16 GB RAM" from being classified as storage

---

## Critical Detection: smartphone_4

**Previously Missed (Baseline 29/30)**:
```
Claim: "Nova X5 has RAM configurations of 16 GB"
Spec:  "RAM configurations: 8 GB or 12 GB LPDDR5X"
Result: ❌ MISSED (matched against bloatware claim with NLI)
```

**Now Detected (Experimental 30/30)**:
```
Claim: "Nova X5 has RAM configurations of 16 GB"
Spec:  "RAM configurations: 8 GB or 12 GB LPDDR5X"
Result: ✅ DETECTED (numerical rule, confidence 1.0000)
Match: Correct RAM spec (not storage, not bloatware)
```

---

## All 30 Detections Verified

### Melatonin (10/10)
1. ✅ melatonin_1: Dosage 5mg vs 3mg
2. ✅ melatonin_2: 100 tablets vs 120
3. ✅ melatonin_3: Vegan + fish-derived
4. ✅ melatonin_4: Wheat + gluten-free
5. ✅ melatonin_5: Lead 5 ppm vs 0.5 ppm (NLI: 0.9966)
6. ✅ melatonin_6: Storage at 0°C
7. ✅ melatonin_7: Take every 2 hours
8. ✅ melatonin_8: FDA approval claim
9. ✅ melatonin_9: Avoid if over 18
10. ✅ melatonin_10: Permanent drowsiness

### Smartphone (10/10)
1. ✅ smartphone_1: 6.5" display vs 6.3" (numerical: 1.0000)
2. ✅ smartphone_2: 48 MP vs 50 MP (numerical: 1.0000)
3. ✅ smartphone_3: 1 TB storage option
4. ✅ smartphone_4: 16 GB RAM vs 8/12 GB (numerical: 1.0000) **← FIXED**
5. ✅ smartphone_5: Wi-Fi 7 support
6. ✅ smartphone_6: Wireless charging (numerical: 1.0000)
7. ✅ smartphone_7: Hourly antivirus
8. ✅ smartphone_8: Offline AI rendering
9. ✅ smartphone_9: 60W vs 30-45W (numerical: 1.0000)
10. ✅ smartphone_10: External SSD via SIM

### CoreCoin (10/10)
1. ✅ corecoin_1: Block time 4s vs 5s (numerical: 1.0000)
2. ✅ corecoin_2: Non-staking light validators
3. ✅ corecoin_3: Regional trading pauses
4. ✅ corecoin_4: Automatic key sharding
5. ✅ corecoin_5: Gas-free smart contracts
6. ✅ corecoin_6: Auto-pass without quorum
7. ✅ corecoin_7: RPC cross-chain simulation
8. ✅ corecoin_8: Unstaking reduces rewards (NLI: 0.9982)
9. ✅ corecoin_9: Inactivity locks governance
10. ✅ corecoin_10: Region-based staking tiers

---

## Numerical Rule Impact

**Files detected by numerical rule (1.0000 confidence)**:
- smartphone_1: 6.5" vs 6.3"
- smartphone_2: 48 MP vs 50 MP
- smartphone_4: 16 GB RAM vs 8/12 GB **← Key fix**
- smartphone_6: Wireless charging (10W)
- smartphone_9: 60W vs 30-45W
- corecoin_1: 4s vs 5s

**6 out of 30 files** benefited from numerical pre-check.

---

## Commits on Experimental Branch

1. `6c4c75a` - docs: Create experimental branch README
2. `c1e6b6c` - feat: Add numerical contradiction checking (Option B)
3. `24e8454` - fix: Add category-aware numerical checking
4. `66334bb` - fix: Reorder category keywords (RAM before storage)

**Total**: 4 commits ahead of main

---

## Files Changed

- `analysis/glass_box_audit.py`: 
  - Added `extract_numbers_with_units()` function
  - Added `check_numerical_contradiction()` function  
  - Modified `verify_claim()` to use numerical pre-check
  - Reordered category keywords in `classify_claim_category()`

---

## Validation Data

**Results location**: `results/pilot_individual_2026/`
- 30 CSV files (one per pilot file)
- Total violations detected: 1,170 across all 30 files
- Detection method tracked via confidence scores:
  - 1.0000 = Numerical rule
  - <1.0000 = NLI model

---

## Performance

- **Average time per file**: ~60-80 seconds
- **Total validation time**: ~30 minutes for 30 files
- **Model loading**: ~2 seconds (RoBERTa-base)
- **Claim extraction**: ~15-20 seconds (GPT-4o-mini API)
- **NLI inference**: ~40-60 seconds (local CPU/MPS)

---

## Status

✅ **READY FOR MERGE**

**Criteria met**:
- [x] Achieves ≥30/30 detection
- [x] No regressions (all 29 baseline detections maintained)
- [x] Clean git history (4 focused commits)
- [x] Fully tested on all 30 pilot files
- [x] Documented in this file

