# Guide: Merge Semantic Pre-Filtering Branch & Test

**Branch:** `feature/semantic-pre-filtering` → `main`
**Status:** Ready to merge
**Important:** Pilot files were COPIED (not moved), so nothing breaks

---

## Step 1: Clean Up Temporary Files

```bash
# Remove test/debug scripts that shouldn't be committed
rm -f scripts/test_semantic_filter*.sh
rm -f scripts/find_*_errors.sh
rm -f scripts/audit_corecoin_batch_fixed.sh
rm -f scripts/audit_*_batch.sh
rm -f =8.0.0  # Junk file

# Check what remains
git status
```

---

## Step 2: Stage Changes for Commit

```bash
# Add production-ready code
git add analysis/glass_box_audit.py
git add analysis/semantic_filter.py

# Add improved analysis scripts
git add scripts/analyze_corecoin_errors.py
git add scripts/analyze_melatonin_errors.py
git add scripts/analyze_smartphone_errors.py
git add scripts/reconstruct_batch_results.sh

# Add pilot study (permanent validation dataset)
git add pilot_study/

# Add documentation
git add DEBERTA_UPGRADE_ANALYSIS.md
git add results/MODEL_COMPARISON_STATS.md

# Check staged changes
git status
```

**Expected output:**
```
Changes to be committed:
  modified:   analysis/glass_box_audit.py
  modified:   scripts/analyze_corecoin_errors.py
  new file:   analysis/semantic_filter.py
  new file:   pilot_study/...
  new file:   DEBERTA_UPGRADE_ANALYSIS.md
  new file:   results/MODEL_COMPARISON_STATS.md
  new file:   scripts/analyze_melatonin_errors.py
  new file:   scripts/analyze_smartphone_errors.py
  new file:   scripts/reconstruct_batch_results.sh
```

---

## Step 3: Commit Changes

```bash
git commit -m "feat: add semantic pre-filtering + pilot study validation

- Add SemanticFilter for 69% FP reduction (3x faster)
- Organize 30-file pilot study with ground truth
- Test & reject DeBERTa-v3-large upgrade (10x worse FP rate)
- Improve Glass Box Audit with optional pre-filtering
- Document model comparison and upgrade analysis

Results:
- 87% detection rate (26/30 errors)
- CoreCoin: 70% (7/10), Smartphone: 100% (10/10), Melatonin: 100% (10/10)
- Production-ready for analyzing 1,620 LLM outputs

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Step 4: Test BEFORE Merging (Critical!)

### Test 1: Basic Audit (Without Semantic Filter)

```bash
# Test on a single file to verify nothing broke
source .venv/bin/activate
python3 analysis/glass_box_audit.py --run-id user_corecoin_10

# Expected: Should complete successfully with ~35 violations
```

**Expected output:**
```
Loading NLI model: cross-encoder/nli-roberta-base
Auditing single run: user_corecoin_10
✓ PASS: 0 (0.0%)
✗ FAIL: 1 (100.0%)
Total violations: 35
```

### Test 2: With Semantic Pre-Filtering

```bash
# Test semantic filter (should reduce violations)
python3 analysis/glass_box_audit.py --run-id user_corecoin_10 --use-semantic-filter

# Expected: ~10 violations (69% reduction from 35)
```

**Expected output:**
```
Loading NLI model: cross-encoder/nli-roberta-base
✅ Semantic pre-filtering ENABLED
Auditing single run: user_corecoin_10
Total violations: 8-12 (varies, but should be ~70% less than baseline)
```

### Test 3: Batch Processing

```bash
# Test batch reconstruction script (processes multiple files)
bash scripts/reconstruct_batch_results.sh /tmp/test_batch.csv user_corecoin

# Expected: Should process all 10 CoreCoin files
# Check: wc -l /tmp/test_batch.csv
# Expected: ~340 lines (338 violations + 1 header + 1 for rounding)
```

### Test 4: Detection Analysis

```bash
# Test detection analysis script
cp results/pilot_baseline_corecoin_COMPLETE.csv results/final_audit_results.csv
python3 scripts/analyze_corecoin_errors.py

# Expected: Should show "Detection Rate: 7/10 (70%)"
```

**Expected output:**
```
CORECOIN INTENTIONAL ERRORS - DETECTION ANALYSIS
...
Detection Rate: 7/10 (70%)
Average violations per file: 33.8

Detection by file:
  File  1: ✅ DETECTED
  File  2: ✅ DETECTED
  File  3: ❌ MISSED
  ...
```

---

## Step 5: Merge to Main

**Only proceed if all tests pass!**

```bash
# Switch to main branch
git checkout main

# Merge feature branch
git merge feature/semantic-pre-filtering

# Verify merge succeeded
git log --oneline -1
# Should show your commit message

# Check files are present
ls analysis/semantic_filter.py
ls pilot_study/README.md
ls DEBERTA_UPGRADE_ANALYSIS.md
```

---

## Step 6: Push to Remote

```bash
# Push to origin (GitHub)
git push origin main

# Verify push
git log origin/main --oneline -1
```

---

## Step 7: Post-Merge Validation

### Re-run Tests on Main Branch

```bash
# Make sure you're on main
git branch
# Should show: * main

# Re-run Test 1
python3 analysis/glass_box_audit.py --run-id user_corecoin_10

# Re-run Test 2 (with semantic filter)
python3 analysis/glass_box_audit.py --run-id user_corecoin_10 --use-semantic-filter

# Both should work identically to Step 4 tests
```

---

## Important Notes About File Reorganization

### What Happened:
- **Pilot files were COPIED** from `outputs/` to `pilot_study/`
- **Original files remain** in `outputs/` (no files were moved/deleted)
- **Nothing breaks** because original paths still exist

### File Mappings:

**Original files (still exist):**
```
outputs/1.txt              → CoreCoin file 1
outputs/2.txt              → CoreCoin file 2
...
outputs/10.txt             → CoreCoin file 10
outputs/s1.txt             → Smartphone file 1
...
outputs/s10.txt            → Smartphone file 10
outputs/FAQ for Melatonin Tablets 3 mg 1.txt  → Melatonin file 1
...
```

**Pilot study copies (organized):**
```
pilot_study/corecoin/files/corecoin_1.txt      → Copy of outputs/1.txt
pilot_study/smartphone/files/smartphone_1.txt  → Copy of outputs/s1.txt
pilot_study/melatonin/files/melatonin_1.txt   → Copy of FAQ... 1.txt
```

**Why this is safe:**
- Glass Box Audit reads from `outputs/` via `experiments.csv` (unchanged)
- Pilot study is a separate validation dataset
- No code paths changed to reference `pilot_study/` (except documentation)

---

## Troubleshooting

### Issue: "Semantic filter not available"

**Symptom:**
```
⚠️  Semantic filter requested but not available (install sentence-transformers)
```

**Fix:**
```bash
pip install sentence-transformers
```

### Issue: "Module semantic_filter not found"

**Symptom:**
```
ImportError: No module named 'semantic_filter'
```

**Fix:**
```bash
# Make sure semantic_filter.py is in analysis/ directory
ls analysis/semantic_filter.py

# If missing, it wasn't staged properly
git checkout feature/semantic-pre-filtering -- analysis/semantic_filter.py
git add analysis/semantic_filter.py
git commit --amend --no-edit
```

### Issue: Different violation count than expected

**This is OK!** Slight variation (±2-3 violations) is normal because:
- GPU/CPU differences in floating point precision
- Temperature=0 for extraction (deterministic) but NLI scores can vary slightly

**Acceptable range:**
- Baseline (no filter): 30-38 violations
- With semantic filter: 8-15 violations

---

## What's Next After Merge?

### Option A: Analyze Full Experimental Dataset (1,620 Files)

Now that Glass Box Audit v2.0 is production-ready, you can analyze your full research dataset:

```bash
# Enable semantic filtering for efficiency (3x faster)
python3 orchestrator.py analyze --use-semantic-filter

# This will audit all completed runs in experiments.csv
# Output: results/final_audit_results.csv (with violation details)
```

**What this gives you:**
- Which LLM models produce the most violations
- Temperature effect on compliance
- Time-of-day patterns
- Material type (FAQ vs Digital Ad vs Blog) compliance

### Option B: Write Research Paper Analysis Script

Create `analysis/research_analysis.py`:
```python
# Analyze violations by:
# - Engine (OpenAI vs Google vs Mistral)
# - Temperature (0.2 vs 0.6 vs 1.0)
# - Material type (FAQ vs Digital Ad vs Blog)
# - Product (Smartphone vs CoreCoin vs Melatonin)

# Output: Statistical analysis, visualizations, tables for paper
```

### Option C: Run Additional Pilot Studies

Test other product/material combinations with intentional errors to validate detection across all domains.

---

## Summary Checklist

Before merging:
- [ ] Clean up temporary files
- [ ] Stage production-ready changes
- [ ] Commit with clear message
- [ ] Test 1: Basic audit works
- [ ] Test 2: Semantic filter works
- [ ] Test 3: Batch processing works
- [ ] Test 4: Detection analysis works

After merging:
- [ ] Checkout main branch
- [ ] Merge feature branch
- [ ] Push to remote
- [ ] Re-run validation tests
- [ ] Ready to analyze 1,620 files!
