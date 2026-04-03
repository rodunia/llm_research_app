# Pre-Merge Action Plan
## Step-by-Step Guide to Merge experimental/ram-category-fix → main

**Status**: Ready to execute
**Validation**: ✅ Complete (30/30 detection confirmed)
**Date**: 2026-02-25

---

## Progress Checklist

- [x] ✅ **Step 1**: Validate 30/30 detection (COMPLETE - see EXPERIMENTAL_VALIDATION_RESULTS.md)
- [x] ✅ **Step 2**: Update .gitignore (COMPLETE - added pilot_results/, logs, .docx, temp scripts)
- [ ] **Step 3**: Organize documentation (READY - commands below)
- [ ] **Step 4**: Convert .docx to markdown (READY - commands below)
- [ ] **Step 5**: Selectively commit files (READY - commands below)
- [ ] **Step 6**: Sync main with origin (OPTIONAL - see notes)
- [ ] **Step 7**: Merge experimental branch (FINAL STEP)

---

## Step 3: Organize Documentation into Subdirectories

### Create Directory Structure

```bash
mkdir -p docs/{comparison,validation,workflows,reproducibility,status,archive}
```

### Move Files to Appropriate Locations

```bash
# Key comparison documents
git mv COMPARISON_GLASSBOX_VS_GPT4O_FREEFORM.md docs/comparison/
git mv PROMPT_ENGINEERING_IMPACT_ANALYSIS.md docs/comparison/
git mv COMPARISON_REPORT_GLASSBOX_VS_GPT4O.md docs/archive/  # older version
git mv COMPARISON_REPORT_UPDATED.md docs/archive/  # older version

# Validation reports
git mv FINAL_COMPARISON_3_RUNS.md docs/validation/
git mv EXPERIMENTAL_VALIDATION_RESULTS.md docs/validation/
git mv STABILITY_REPORT_30_30.md docs/archive/  # redundant with FINAL_COMPARISON

# Workflows
git mv GPT4O_100PCT_DETECTION_WORKFLOW.md docs/workflows/

# Reproducibility
git mv GLASS_BOX_REPRODUCIBILITY_PROTOCOL.md docs/reproducibility/
git mv GLASS_BOX_STEP_BY_STEP_VALIDATION.md docs/reproducibility/

# Status documents
git mv READY_FOR_SCALE_UP.md docs/status/
git mv METADATA_CAPTURE_STATUS.md docs/status/
git mv CURRENT_IMPLEMENTATION_STATUS.md docs/status/
git mv GLASS_BOX_CURRENT_STATUS_2026.md docs/status/

# Archive older/redundant docs
git mv EXPERIMENTAL_RESULTS_30_30.md docs/archive/
git mv COST_ANALYSIS.md docs/archive/

# Keep at root (project decisions/guides)
# - TEMPORAL_STUDY_DESIGN_DECISION.md
# - TRUE_TEMPORAL_EXECUTION_GUIDE.md
# - RANDOMIZATION_IMPLEMENTATION_COMPLETE.md
# - STATISTICAL_REASONING_RANDOMIZATION.md
# - REPETITIONS_DECISION.md
# - EXPERIMENTAL_BRANCH_README.md
# - MERGE_ASSESSMENT_EXPERIMENTAL_RAM_FIX.md
# - PRE_MERGE_ACTION_PLAN.md (this file)
```

### Commit Documentation Reorganization

```bash
git add -A
git commit -m "docs: organize documentation into subdirectories

- comparison/: Glass Box vs GPT-4o comparisons
- validation/: Detection validation reports
- workflows/: Reusable workflow guides
- reproducibility/: Reproducibility protocols
- status/: Implementation status reports
- archive/: Older/superseded documentation"
```

---

## Step 4: Convert .docx Files to Markdown

### Option A: Manual Extraction (Recommended)

The .docx files contain ground truth error documentation. Manually create markdown versions:

**File**: `outputs/smartphone_errors.md`
```markdown
# Smartphone Intentional Errors (Ground Truth)

| File | Error Type | Incorrect Claim | Correct Value | Keywords |
|------|-----------|-----------------|---------------|----------|
| user_smartphone_1 | Numerical | Display 6.5" | 6.3" | 6.5, 6.3 |
| user_smartphone_2 | Numerical | Camera 48 MP | 50 MP | 48 MP, 50 MP |
| user_smartphone_3 | Feature Hallucination | 1 TB storage option | Not available | 1 TB, terabyte |
| user_smartphone_4 | Feature Hallucination | 16 GB RAM option | 8 GB or 12 GB | 16 GB RAM |
... (continue for all 10)
```

**File**: `outputs/melatonin_errors.md`
```markdown
# Melatonin Intentional Errors (Ground Truth)

| File | Error Type | Incorrect Claim | Correct Value | Keywords |
|------|-----------|-----------------|---------------|----------|
| user_melatonin_1 | Numerical | Dosage error (mg mismatch) | 3mg | mg, dosage, 5mg, 3mg |
... (continue for all 10)
```

**File**: `outputs/crypto_errors.md`
```markdown
# CoreCoin Intentional Errors (Ground Truth)

| File | Error Type | Incorrect Claim | Correct Value | Keywords |
|------|-----------|-----------------|---------------|----------|
| user_corecoin_1 | Numerical | Block time 4s | ~5s | 4 second, 4s, 5s |
... (continue for all 10)
```

### Option B: Automated with python-docx (if already installed)

```bash
python3 << 'EOF'
from docx import Document
from pathlib import Path

for docx_file in Path("outputs").glob("*.docx"):
    doc = Document(docx_file)
    md_file = docx_file.with_suffix(".md")

    with open(md_file, 'w') as f:
        f.write(f"# {docx_file.stem.replace('_', ' ').title()}\n\n")
        for para in doc.paragraphs:
            if para.text.strip():
                f.write(f"{para.text}\n\n")
        for table in doc.tables:
            # Convert table to markdown
            for i, row in enumerate(table.rows):
                cells = [cell.text for cell in row.cells]
                f.write("| " + " | ".join(cells) + " |\n")
                if i == 0:
                    f.write("|" + "|".join(["---"] * len(cells)) + "|\n")
    print(f"✓ Converted {docx_file} → {md_file}")
EOF
```

### Remove .docx Files

```bash
# After confirming markdown versions are correct
rm outputs/*.docx

git add outputs/*.md
git commit -m "docs: convert ground truth errors from .docx to markdown

- smartphone_errors.md: 10 intentional errors with keywords
- melatonin_errors.md: 10 intentional errors with keywords
- crypto_errors.md: 10 intentional errors with keywords
- Removes binary .docx files (now in .gitignore)"
```

---

## Step 5: Selectively Commit Untracked Files

### Essential Documentation (Keep)

```bash
# Commit only essential docs (now organized in docs/)
git add docs/
git add EXPERIMENTAL_VALIDATION_RESULTS.md
git add MERGE_ASSESSMENT_EXPERIMENTAL_RAM_FIX.md
git add PRE_MERGE_ACTION_PLAN.md

git commit -m "docs: add comprehensive validation and merge assessment documentation

- EXPERIMENTAL_VALIDATION_RESULTS.md: Confirms 30/30 detection
- MERGE_ASSESSMENT_EXPERIMENTAL_RAM_FIX.md: Complete merge analysis
- PRE_MERGE_ACTION_PLAN.md: Step-by-step merge guide
- docs/: Organized documentation subdirectories"
```

### Essential Scripts (Keep)

```bash
# Commit analysis and comparison scripts
git add analysis/gpt4o_baseline.py
git add analysis/glass_box_standalone.py
git add scripts/compare_glassbox_vs_gpt4o_freeform.py
git add scripts/llm_direct_gpt4o_freeform.py
git add scripts/analyze_pilot_detection.py

git commit -m "feat: add GPT-4o baseline and comparison analysis scripts

- gpt4o_baseline.py: Structured JSON detection workflow (100% validated)
- glass_box_standalone.py: Standalone audit for single files
- compare_glassbox_vs_gpt4o_freeform.py: Comparison analysis (100% vs 43%)
- llm_direct_gpt4o_freeform.py: Free-form prompt testing
- analyze_pilot_detection.py: Detection rate analysis tool"
```

### Results to Keep (Already Tracked)

```bash
# Pilot study results (allow in .gitignore exceptions)
git add results/pilot_individual_2026_run1/*.csv
git add results/pilot_individual_2026_run2/*.csv

git commit -m "results: add pilot study run 1 and run 2 validation results (30/30 detection)"
```

### Files to IGNORE (Don't Commit)

The following are now in `.gitignore` and should NOT be committed:

```bash
# Temporary results directories
pilot_results/
pilot_results_fixed/
pilot_results_verification/
pilot_results_with_specs/
results/comparison_analysis/
results/glassbox_vs_gpt4o_freeform/
results/gpt4o_baseline/
results/gpt4o_baseline_run1/
results/gpt4o_baseline_run2/
results/llm_direct_gpt4o_freeform_responses/

# Log files
glass_box_run.log
pilot_audit_log.txt
pilot_fix_test.log
pilot_fix_test_v2.log
pilot_specs_fix.log

# Temporary scripts
check_stability_status.sh
monitor_validation.sh
wait_for_completion.sh
test_critical_files.sh

# JSON results
results/stability_report.json
results/audit_errors.json
```

---

## Step 6: Sync Main with Origin (OPTIONAL)

**Status**: Main branch is 12 commits ahead of origin/main

**Decision**: This depends on whether you want to push to GitHub/remote:

### Option A: Push to Remote (Recommended if using GitHub)

```bash
# Check if remote has diverged
git fetch origin
git log main..origin/main  # Should be empty

# Push local commits to origin
git push origin main
```

### Option B: Skip (If working locally only)

If this is a local-only repository or you don't use origin, skip this step.

**Note**: If you skip this and your machine fails, the 12 unpushed commits will be lost.

---

## Step 7: Merge Experimental Branch

### Final Pre-Merge Checks

```bash
# Ensure we're on main
git branch --show-current  # Should output: main

# Ensure all commits are clean
git status  # Should show "nothing to commit, working tree clean"

# Verify experimental branch still exists
git branch -a | grep experimental/ram-category-fix
```

### Perform Merge

```bash
# Merge experimental branch
git merge experimental/ram-category-fix

# Git will open editor for merge commit message
# Suggested message:
```

**Merge Commit Message**:
```
feat: add category-aware numerical contradiction detection for RAM errors

Merges experimental/ram-category-fix branch achieving 30/30 (100%) detection.

Changes:
- Add extract_numbers_with_units() function for numerical parsing
- Add check_numerical_contradiction() function for rule-based validation
- Modify NLIJudge.verify_claim() to run category-aware numerical pre-check
- Reorder category keywords (RAM before storage) to prevent GB conflicts

Fixes: smartphone_4 detection (16 GB RAM error vs 8 GB/12 GB spec)

Validation:
- Run 1: 30/30 (100%)
- Run 2: 30/30 (100%)
- Run 3: 30/30 (100%)
- Total: 90 evaluations, 100% detection rate

See EXPERIMENTAL_VALIDATION_RESULTS.md for full validation details.

Closes #experimental-ram-category-fix

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Post-Merge Verification

```bash
# Verify merge succeeded
git log --oneline -5  # Should show merge commit + experimental commits

# Verify changes are present
grep -A 5 "def check_numerical_contradiction" analysis/glass_box_audit.py
# Should output the new function

# Delete experimental branch (now merged)
git branch -d experimental/ram-category-fix

# Push merged main to origin (if using remote)
git push origin main
```

---

## Estimated Timeline

| Step | Duration | Complexity |
|------|---------|------------|
| 1. Validation | ✅ Complete | - |
| 2. Update .gitignore | ✅ Complete | - |
| 3. Organize docs | 30 min | Low (file moves) |
| 4. Convert .docx | 20 min | Low (manual or script) |
| 5. Commit files | 15 min | Low (git add + commit) |
| 6. Sync with origin | 5 min | Low (optional) |
| 7. Merge experimental | 10 min | Low (clean merge confirmed) |
| **TOTAL** | **~80 minutes** | **Low risk** |

---

## Risk Mitigation

### Backup Before Merge

```bash
# Create backup branch (just in case)
git checkout main
git branch backup-pre-merge-$(date +%Y%m%d)

# Proceed with merge
git merge experimental/ram-category-fix
```

### Rollback Plan (If Something Goes Wrong)

```bash
# Abort merge if conflicts arise
git merge --abort

# OR: Revert merge commit after merge
git log --oneline -1  # Get merge commit hash
git revert -m 1 <merge-commit-hash>

# OR: Hard reset to backup (NUCLEAR OPTION)
git reset --hard backup-pre-merge-YYYYMMDD
```

---

## Final Checklist

Before executing Step 7 (merge), verify:

- [ ] ✅ .gitignore updated (no temp files will be committed)
- [ ] ✅ Documentation organized into docs/ subdirectories
- [ ] ✅ .docx files converted to markdown
- [ ] ✅ Essential scripts committed (gpt4o_baseline.py, compare scripts)
- [ ] ✅ Untracked files reviewed (nothing sensitive/temporary)
- [ ] ✅ Backup branch created (safety net)
- [ ] ✅ Main branch synced with origin (if using remote)
- [ ] ✅ Experimental branch validated (30/30 detection confirmed)

---

## Success Criteria

After merge, verify:

1. ✅ `grep "def check_numerical_contradiction" analysis/glass_box_audit.py` returns function
2. ✅ `git log --oneline -5` shows merge commit
3. ✅ `git branch -d experimental/ram-category-fix` deletes branch cleanly
4. ✅ No untracked files except those in .gitignore
5. ✅ `git status` shows "working tree clean"

---

## Documentation References

- **Validation Proof**: `EXPERIMENTAL_VALIDATION_RESULTS.md`
- **Merge Analysis**: `MERGE_ASSESSMENT_EXPERIMENTAL_RAM_FIX.md`
- **Branch Documentation**: `EXPERIMENTAL_BRANCH_README.md`
- **Comparison Results**: `docs/comparison/COMPARISON_GLASSBOX_VS_GPT4O_FREEFORM.md`
- **Final Validation**: `docs/validation/FINAL_COMPARISON_3_RUNS.md`

---

## Notes

- **Main is 12 commits ahead of origin** - Consider pushing before merge (Step 6)
- **Merge is clean** - No conflicts expected (tested with `--no-commit --no-ff`)
- **Detection validated** - 30/30 across 3 runs (90 total evaluations)
- **Code quality high** - Well-documented, type hints, clear logic
- **No regressions** - All 29 previous detections maintained

---

**Status**: ✅ READY TO EXECUTE

**Next Action**: Execute Steps 3-7 in sequence

**Est. Completion**: ~80 minutes of focused work

---

**Last Updated**: 2026-02-25
**Prepared By**: Claude Code (automated analysis)
