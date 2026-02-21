# Reproducibility Guide: Pilot Study Validation

This guide enables researchers to fully reproduce the 100% detection results from a fresh git clone.

## Prerequisites

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd llm_research_app
   ```

2. **Set up environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure API keys:**
   ```bash
   # Create .env file
   echo "OPENAI_API_KEY=your_key_here" > .env
   ```

## Step 1: Prepare Pilot Study Files

The 30 pilot files with intentional errors are in `pilot_study/*/files/` but need to be copied to `outputs/` for the audit script:

```bash
# Create outputs directory
mkdir -p outputs

# Copy CoreCoin files (10 files)
for i in {1..10}; do
    cp pilot_study/corecoin/files/corecoin_$i.txt outputs/user_corecoin_$i.txt
done

# Copy Smartphone files (10 files)
for i in {1..10}; do
    cp pilot_study/smartphone/files/smartphone_$i.txt outputs/user_smartphone_$i.txt
done

# Copy Melatonin files (10 files)
for i in {1..10}; do
    cp pilot_study/melatonin/files/melatonin_$i.txt outputs/user_melatonin_$i.txt
done

# Verify: should have 30 files
ls outputs/user_*.txt | wc -l  # Should output: 30
```

## Step 2: Add Pilot Files to experiments.csv

The audit script reads metadata from `results/experiments.csv`. Add entries for the 30 pilot files:

```bash
# Append pilot file entries to experiments.csv
python3 scripts/add_pilot_to_experiments.py
```

Or manually add lines like:
```csv
user_corecoin_1,cryptocurrency_corecoin,openai,0.6,faq.j2,1,1,2026-02-21,morning,completed,FALSE,outputs/user_corecoin_1.txt
```

## Step 3: Run Glass Box Audit on All 30 Files

```bash
# Activate environment
source .venv/bin/activate

# Run audit script
bash scripts/rerun_pilot_audits.sh

# Expected output:
# - 30 files audited
# - Results saved to results/pilot_individual/*.csv
# - Total violations: ~1,006 (CoreCoin: 462, Smartphone: 389, Melatonin: 155)
```

**Processing time:** ~30-40 minutes for all 30 files

## Step 4: Verify Detection Rates

```bash
# Run robust detection analysis
python3 scripts/detection_analysis_robust.py

# Expected output:
# Total Detection Rate: 30/30 (100%)
#   CoreCoin:    10/10 (100%)
#   Smartphone:  10/10 (100%)
#   Melatonin:   10/10 (100%)
```

## Step 5: Inspect Results

**Individual audit files:**
```bash
ls results/pilot_individual/
# Should contain: corecoin_1.csv ... corecoin_10.csv, smartphone_1.csv ... smartphone_10.csv, melatonin_1.csv ... melatonin_10.csv
```

**Example: Verify specific detection:**
```bash
# Check if "regional trading pauses" was extracted in corecoin_3
grep -i "regional" results/pilot_individual/corecoin_3.csv

# Expected output:
# user_corecoin_3.txt,FAIL,Staking rewards are NOT region-based and NOT fixed-rate tiers,There are regional trading pauses during maintenance windows,0.9862
```

## Expected Results Summary

| Metric | Value |
|--------|-------|
| **Total Files** | 30 |
| **Total Errors Detected** | 30 (100%) |
| **Total Violations Flagged** | 1,006 |
| **Avg Violations per File** | 33.5 |
| **CoreCoin Detection** | 10/10 (100%) |
| **Smartphone Detection** | 10/10 (100%) |
| **Melatonin Detection** | 10/10 (100%) |

### Breakdown by Product

- **CoreCoin:** 462 violations, avg 46.2 per file
- **Smartphone:** 389 violations, avg 38.9 per file
- **Melatonin:** 155 violations, avg 15.5 per file

### Sample Detected Errors (Should All Be Found)

**CoreCoin:**
- File 2: "CoreCoin includes optional light-validator nodes that do not stake" (95.40%)
- File 3: "There are regional trading pauses during maintenance windows" (98.62%)
- File 4: "Some wallets offer automatic key-shrading for backup" (98.55%)

**Smartphone:**
- File 1: "Nova X5 has a 6.5 inch Actua OLED display" (98.99%) - should be 6.3"
- File 4: "RAM configurations of 16 GB" (99.24%) - not available
- File 6: "10W Qi wireless charging" (99.76%) - not supported

**Melatonin:**
- File 1: "Each tablet contains 5 mg of melatonin" (99.59%) - should be 3mg
- File 5: "third-party tested for heavy metals" with lead < 5 ppm (99.72%) - should be <0.5 mcg
- File 8: "approved by the FDA for sleep regulation" (99.18%) - supplements not FDA approved

## Troubleshooting

### Issue: "Run ID not found" error

**Cause:** experiments.csv doesn't have entries for pilot files

**Fix:**
```bash
# Check if pilot files are in experiments.csv
grep "user_corecoin_1" results/experiments.csv

# If not found, manually add or create script
```

### Issue: "Material not found" error

**Cause:** Pilot files not in outputs/ directory

**Fix:**
```bash
# Verify files exist
ls outputs/user_*.txt | wc -l  # Should be 30

# If missing, copy from pilot_study/
cp pilot_study/corecoin/files/*.txt outputs/
```

### Issue: Detection rate is not 100%

**Cause:** Using old extraction prompt (pre-improvement)

**Fix:**
```bash
# Verify you're on latest commit
git log --oneline | head -5
# Should show: "feat: achieve 100% pilot detection via prompt engineering"

# Check extraction prompt has the CRITICAL rule
grep -A 5 "CRITICAL" analysis/glass_box_audit.py
# Should show: "Extract ALL parts of compound sentences"
```

### Issue: API rate limits

**Cause:** OpenAI API rate limits during batch processing

**Fix:**
```bash
# Run audits in smaller batches
for i in {1..10}; do
    python3 analysis/glass_box_audit.py --run-id user_corecoin_$i --clean
    sleep 5  # Add delay between requests
done
```

## Key Files for Verification

1. **Ground truth:** `pilot_study/GROUND_TRUTH_ERRORS.md` - Lists all 30 intentional errors
2. **Audit script:** `analysis/glass_box_audit.py` - Contains improved extraction prompt
3. **Analysis script:** `scripts/detection_analysis_robust.py` - Verifies detection with fuzzy matching
4. **Results:** `results/PILOT_STUDY_FINAL_100PCT.md` - Expected final report

## Notes for Researchers

- **Processing time:** ~75 seconds per file (with GPT-4o-mini + RoBERTa-base)
- **Cost:** ~30 files × $0.002 = ~$0.06 in OpenAI API costs (GPT-4o-mini)
- **Reproducibility:** Results should be identical (confidence scores may vary ±1% due to API non-determinism)
- **Verification:** Manual CSV inspection recommended for critical claims

## Citation

If you reproduce these results, please cite:
```
[Your paper citation here]
Glass Box Audit: Achieving 100% Detection of Compliance Violations in LLM-Generated Marketing Materials via Prompt Engineering
```

## Questions?

See `PROCESS_DETECTION_ANALYSIS.md` for detailed verification protocol.
