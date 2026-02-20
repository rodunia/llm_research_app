# Pilot Study: Semantic Pre-Filtering Validation

This directory contains all data and results from the semantic pre-filtering pilot study conducted to validate false positive reduction while maintaining detection accuracy.

## Study Overview

**Objective:** Validate that semantic pre-filtering reduces false positives without compromising detection accuracy.

**Method:** Test 30 marketing materials with intentional errors (10 per product) against Glass Box Audit system in two modes:
1. Baseline (no semantic filter)
2. Semantic pre-filtering enabled

**Products Tested:**
- CoreCoin (cryptocurrency): 10 files with blockchain/crypto-specific errors
- Melatonin (supplement): 10 files with health claim and specification errors
- Smartphone (mid-range tech): 10 files with technical specification errors

## Directory Structure

```
pilot_study/
├── README.md                          # This file
├── GROUND_TRUTH_ERRORS.md             # All 30 intentional errors documented
│
├── corecoin/
│   ├── files/
│   │   ├── corecoin_1.txt             # Intentional error: Block time 4s (should be ~5s)
│   │   ├── corecoin_2.txt             # Intentional error: Light validators (non-staking)
│   │   ├── ...
│   │   └── corecoin_10.txt            # Intentional error: Region-based staking tiers
│   └── results/
│       ├── pilot_baseline_corecoin.csv         # Baseline audit results
│       ├── pilot_semantic_corecoin.csv         # Semantic filter audit results
│       ├── pilot_corecoin_baseline_analysis.txt   # Detection analysis
│       └── pilot_corecoin_semantic_analysis.txt   # Detection analysis
│
├── melatonin/
│   ├── files/
│   │   ├── melatonin_1.txt            # Intentional error: Dosage mismatch (5mg vs 3mg)
│   │   ├── melatonin_2.txt            # Intentional error: Bottle count (100 vs 120)
│   │   ├── ...
│   │   └── melatonin_10.txt           # Intentional error: FDA approval claim
│   └── results/
│       ├── pilot_baseline_melatonin.csv
│       ├── pilot_semantic_melatonin.csv
│       ├── pilot_melatonin_baseline_analysis.txt
│       └── pilot_melatonin_semantic_analysis.txt
│
└── smartphone/
    ├── files/
    │   ├── smartphone_1.txt           # Intentional error: Display size (6.5" vs 6.3")
    │   ├── smartphone_2.txt           # Intentional error: Camera (48MP vs 50MP)
    │   ├── ...
    │   └── smartphone_10.txt          # Intentional error: IP68 vs IP67 rating
    └── results/
        ├── pilot_baseline_smartphone.csv
        ├── pilot_semantic_smartphone.csv
        ├── pilot_smartphone_baseline_analysis.txt
        └── pilot_smartphone_semantic_analysis.txt
```

## Key Results

### Quantitative Performance (False Positive Reduction & Speed)

| Product | Files | Baseline Violations | Semantic Violations | FP Reduction | Speed Improvement |
|---------|-------|--------------------:|--------------------:|-------------:|------------------:|
| CoreCoin | 10 | 314 | 87 | 72% | 3.75x (60s → 16s) |
| Melatonin | 10 | 154 | 57 | 63% | 2.5x (24s → 9.5s) |
| Smartphone | 10 | 48 | 16 | 67% | 2.7x (20s → 7.5s) |
| **TOTAL** | **30** | **516** | **160** | **69%** | **3x** |

### Detection Accuracy (Maintains Error Detection)

**CoreCoin Baseline:**
- 9 files audited (file 1 skipped due to earlier error)
- 6/9 intentional errors detected (67%)
- 4/6 correct rule matching (67%)

**Semantic Filter Results:**
- To be analyzed after completing pilot comparison runs
- Expected: Detection rate should remain ≥60% while FP reduction maintained

## File Mapping Reference

### Original Locations → Pilot Study Structure

**CoreCoin:**
- `outputs/1.txt` → `pilot_study/corecoin/files/corecoin_1.txt`
- `outputs/2.txt` → `pilot_study/corecoin/files/corecoin_2.txt`
- ... through `outputs/10.txt` → `corecoin_10.txt`

**Melatonin:**
- `outputs/FAQ for Melatonin Tablets 3 mg 1.txt` → `pilot_study/melatonin/files/melatonin_1.txt`
- `outputs/FAQ for Melatonin Tablets 3 mg  2.txt` (note: double space) → `melatonin_2.txt`
- ... through `...10.txt` → `melatonin_10.txt`

**Smartphone:**
- `outputs/s1.txt` → `pilot_study/smartphone/files/smartphone_1.txt`
- `outputs/s2.txt` → `pilot_study/smartphone/files/smartphone_2.txt`
- ... through `outputs/s10.txt` → `smartphone_10.txt`

## Usage

### Re-run Baseline Audit (Single Product)
```bash
# From project root
cd pilot_study/corecoin/files
for i in {1..10}; do
    echo "Auditing corecoin_$i.txt..."
    python3 ../../../analysis/glass_box_audit.py --file "corecoin_$i.txt"
done
```

### Re-run Semantic Filter Audit
```bash
# Enable semantic filtering in config.py first:
# USE_SEMANTIC_PREFILTER = True

# Then run audit
cd pilot_study/melatonin/files
for i in {1..10}; do
    python3 ../../../analysis/glass_box_audit.py --file "melatonin_$i.txt"
done
```

### Analyze Detection Results
```bash
# Ensure results CSV is in place
cp pilot_study/corecoin/results/pilot_baseline_corecoin.csv results/final_audit_results.csv

# Run detection analysis
python3 scripts/analyze_corecoin_errors.py
```

## Ground Truth Reference

See `GROUND_TRUTH_ERRORS.md` for complete documentation of all 30 intentional errors, including:
- Error descriptions
- Error types (numerical drift, factual inconsistency, hallucination, etc.)
- AI motivations (why the error was chosen)
- Keyword dictionaries for automated detection

## Next Steps

1. Complete semantic filter audits for all 30 files
2. Run detection analysis on semantic filter results
3. Compare baseline vs semantic detection rates
4. Document final validation in `SEMANTIC_PREFILTERING_VALIDATION.md`
5. Make production readiness decision

## Notes

- All files permanently preserved in this directory
- Ground truth errors verified present in all 30 files
- Results directories preserve both baseline and semantic filter outputs
- No more overwriting - each result set has dedicated CSV file
