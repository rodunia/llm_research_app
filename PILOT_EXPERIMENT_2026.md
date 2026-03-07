# Pilot Experiment - Full Pipeline Test
**Date**: 2026-03-07
**Purpose**: Validate generation → randomization → analysis pipeline before full experiment
**Status**: IN PROGRESS

---

## Pilot Configuration

### Sample Size: 54 Runs

**Design**:
```
3 products × 2 materials × 1 time × 1 temp × 3 reps × 3 engines = 54 runs
```

**Products** (3):
- smartphone_mid
- cryptocurrency_corecoin
- supplement_melatonin

**Materials** (2):
- faq.j2
- digital_ad.j2

**Time** (1):
- morning only

**Temperature** (1):
- 0.6 (medium/balanced)

**Replications** (3):
- rep1, rep2, rep3

**Engines** (3):
- openai (gpt-4o)
- google (gemini-2.0-flash-exp)
- mistral (mistral-large-2407)

---

## Pilot Objectives

### 1. Test Generation Pipeline ✅
- [x] Generate 54-run experimental matrix with randomization
- [ ] Verify all 3 engines execute successfully
- [ ] Check output file quality
- [ ] Validate prompt rendering
- [ ] Confirm metadata capture in experiments.csv

### 2. Validate Randomization ✅
- [x] Confirm runs execute in randomized order (seed=42)
- [ ] Verify products/engines/materials are mixed (not sequential)
- [ ] Document randomization effectiveness

### 3. Test Glass Box Audit
- [ ] Run Glass Box on all 54 pilot outputs
- [ ] Compare violation rates to baseline (33.4 violations/file)
- [ ] Test checkpointing/resume functionality
- [ ] Measure processing time (expect ~35-40 min for 54 files)

### 4. Validate Full Workflow
- [ ] Generation completes without errors
- [ ] All output files created successfully
- [ ] experiments.csv tracks status correctly
- [ ] Glass Box processes all outputs
- [ ] Results analyzable

---

## Execution Timeline

**Start Time**: 2026-03-07 12:02:14
**Expected Duration**:
- Generation: ~1-1.5 hours (54 runs)
- Glass Box: ~35-40 minutes (54 files)
- Total: ~2 hours

**Command Log**:
```bash
# 1. Configure pilot (config.py)
#    - Reduced to 2 materials, 1 time, 1 temp
#    - Backed up full config to config_full_experiment.py

# 2. Generate matrix with randomization
python -m runner.generate_matrix
# Output: 54 runs, randomized with seed=42

# 3. Start pilot generation
python orchestrator.py run --time-of-day morning
# Running in background (shell ID: 2cd10d)
```

---

## Randomization Verification

**Sample of first 10 runs** (from experiments.csv):

| Run | Product | Material | Engine |
|-----|---------|----------|--------|
| 1 | supplement_melatonin | faq.j2 | openai |
| 2 | cryptocurrency_corecoin | faq.j2 | openai |
| 3 | supplement_melatonin | faq.j2 | mistral |
| 4 | cryptocurrency_corecoin | digital_ad.j2 | openai |
| 5 | cryptocurrency_corecoin | faq.j2 | google |
| 6 | supplement_melatonin | digital_ad.j2 | openai |
| 7 | smartphone_mid | digital_ad.j2 | google |
| 8 | cryptocurrency_corecoin | digital_ad.j2 | google |
| 9 | cryptocurrency_corecoin | digital_ad.j2 | google |
| 10 | smartphone_mid | digital_ad.j2 | openai |

✅ **Randomization confirmed**: Mixed products, materials, and engines from the start

---

## Success Criteria

### Generation Phase
- [ ] All 54 runs complete successfully
- [ ] No API errors or timeouts
- [ ] All output files (54) created
- [ ] experiments.csv shows 54 "completed" status
- [ ] Prompt files saved to outputs/prompts/

### Glass Box Phase
- [ ] All 54 files audited successfully
- [ ] No crashes or errors
- [ ] Results saved to results/final_audit_results.csv
- [ ] Violation counts reasonable (near baseline ~33/file)

### Randomization Phase
- [ ] Run order is NOT sequential (products/engines mixed)
- [ ] Seed=42 reproducible
- [ ] No temporal patterns visible

---

## Expected Results

### Generation Metrics
- **Time**: ~1-1.5 hours (54 runs × 1-1.5 min/run)
- **Cost**: ~$3-5 (varies by engine)
- **Success rate**: 100% (all 54 runs complete)

### Glass Box Metrics
- **Violation rate**: ~33 violations/file (based on baseline)
- **Total violations**: ~1,782 (54 files × 33)
- **Processing time**: ~35-40 min (54 files × 40 sec/file)

### Quality Checks
- All 3 products represented equally (18 runs each)
- All 2 materials represented equally (27 runs each)
- All 3 engines represented equally (18 runs each)
- All 3 reps represented equally (18 runs each)

---

## Post-Pilot Actions

### If Pilot Succeeds ✅
1. Review violation rates vs baseline
2. Restore full config (`config_full_experiment.py`)
3. Expand to full experiment (729 runs)
4. Document any issues/adjustments

### If Issues Found ❌
1. Debug specific failures
2. Adjust config/code as needed
3. Re-run pilot with fixes
4. Document fixes in this file

---

## Configuration Files

**Current pilot config**: `config.py`
**Full experiment config**: `config_full_experiment.py` (backup)
**Experimental matrix**: `results/experiments.csv` (54 rows)
**Previous matrix**: `results/experiments_backup_*.csv`

**To restore full config**:
```bash
cp config_full_experiment.py config.py
```

---

## Notes

- Pilot uses ONLY morning time slot (simplifies testing)
- Pilot uses ONLY temp=0.6 (representative middle value)
- All 3 products tested (generalizability)
- All 3 engines tested (provider diversity)
- 3 replications per condition (reliability check)

**Key advantage**: 54 runs is large enough to test everything, small enough to complete quickly (~2 hours)

---

## Monitoring Commands

```bash
# Check generation progress
python orchestrator.py status

# Monitor background process
tail -f pilot_run_log.txt

# Check completed runs
grep -c "completed" results/experiments.csv

# Check output files
ls outputs/*.txt | wc -l
```

---

**Status**: Generation running (started 2026-03-07 12:02:14)
**Next**: Wait for generation to complete, then run Glass Box audit

---

## Update Log

- **2026-03-07 12:02**: Pilot started (54 runs, background execution)
- **2026-03-07 12:02**: Randomization verified from first 10 runs
- **TBD**: Generation completion time
- **TBD**: Glass Box audit results
- **TBD**: Final validation
