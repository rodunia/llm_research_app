# Merge Assessment: experimental/ram-category-fix → main
## Branch Review and Future Problem Analysis

**Date**: 2026-02-25
**Branch**: `experimental/ram-category-fix`
**Base**: `main` at commit `974357d`
**Assessment Type**: Pre-merge technical review

---

## Executive Summary

**Merge Status**: ✅ **CLEAN - No conflicts detected**

**Key Findings**:
1. ✅ No Git conflicts - automatic merge succeeds
2. ✅ Only 2 tracked files changed (+210 lines, -2 lines)
3. ⚠️ **Huge number of untracked files** (50+ documentation/result files)
4. ⚠️ **Experimental changes not validated** - No evidence RAM fix achieved 30/30
5. ⚠️ **Main branch 12 commits ahead of origin** - Sync issue

**Recommendation**: **DO NOT MERGE YET** - Need validation testing first

---

## 1. Branch Comparison Analysis

### Common Ancestor
- **Merge base**: `974357d` (main branch)
- **Divergence**: 4 commits on experimental branch
- **Branch age**: Recent (created from latest main)

### Commit History on experimental/ram-category-fix

```
66334bb - fix: reorder category keywords - RAM before storage to prevent GB keyword conflict
24e8454 - fix: add category-aware numerical checking to match correct specs (RAM vs RAM, not RAM vs storage)
c1e6b6c - experiment: add numerical contradiction checking (Option B) to detect number mismatches
6c4c75a - docs: create experimental branch for RAM category fix attempts
```

**Analysis**:
- 4 focused commits addressing RAM detection issue
- Progressive refinement: numerical checking → category-aware → keyword ordering
- Good commit messages with clear intent

---

## 2. File Changes Analysis

### Tracked Files Modified (2 files)

#### `analysis/glass_box_audit.py` (+87 lines, -2 lines)

**Changes Added**:

1. **New Function: `extract_numbers_with_units(text: str)`** (lines 244-265)
   - Extracts numbers with units using regex
   - Pattern: `(\d+(?:\.\d+)?)\s*(GB|MB|TB|inch|"|mAh|MP|Hz|W|mm|grams?|kg|℃|°C|C)\b`
   - Normalizes units ("gram"→"grams", "C"→"℃")
   - **Purpose**: Parse numerical specifications for comparison

2. **New Function: `check_numerical_contradiction(claim: str, spec: str)`** (lines 268-299)
   - Compares numbers with same units between claim and spec
   - Returns `(is_contradiction: bool, explanation: str)`
   - **Example**: "16 GB RAM" vs "8 GB or 12 GB RAM" → contradiction detected
   - **Purpose**: Rule-based numerical validation (catches NLI misses)

3. **Modified: `NLIJudge.verify_claim()` Method** (lines 349-371)
   - **Added**: Category-aware numerical pre-check before NLI
   - **Logic**:
     ```python
     if spec_category == claim_category or spec_category == 'general':
         is_contradiction, explanation = check_numerical_contradiction(claim, spec)
         if is_contradiction:
             return {'is_violation': True, 'contradiction_score': 1.0, ...}
     ```
   - **Purpose**: Fast rule-based detection before expensive NLI inference

4. **Modified: `classify_claim_category()` Keyword Order** (lines 661-662)
   - **OLD**:
     ```python
     'storage': ['storage', 'gb', 'tb', 'memory', 'space', 'ufs', 'expandable', 'microsd'],
     'ram': ['ram', 'lpddr', 'memory'],
     ```
   - **NEW**:
     ```python
     'ram': ['ram', 'lpddr'],  # Check RAM before storage (more specific)
     'storage': ['storage', 'ufs', 'expandable', 'microsd'],  # Removed 'gb', 'memory' to avoid conflicts
     ```
   - **Purpose**: Prevent "GB" keyword in "16 GB RAM" from matching storage category

**Code Quality Assessment**:
- ✅ Well-documented with docstrings
- ✅ Type hints included
- ✅ Clear variable names
- ✅ Follows project conventions
- ✅ No obvious bugs or security issues
- ⚠️ **No unit tests** for new functions
- ⚠️ **No validation that 30/30 detection achieved**

#### `EXPERIMENTAL_BRANCH_README.md` (+125 lines)

**Purpose**: Documentation for experimental branch workflow
- Explains baseline (29/30 detection)
- Lists experimental goals and success criteria
- Provides testing protocol
- Documents merge criteria

**Assessment**:
- ✅ Good documentation practice
- ✅ Clear success/failure criteria
- ⚠️ Should this file be kept in main? (might clutter root directory)

---

## 3. Merge Conflict Analysis

### Test Merge Results
```bash
$ git merge --no-commit --no-ff experimental/ram-category-fix
Automatic merge went well; stopped before committing as requested
```

**Verdict**: ✅ **NO CONFLICTS** - Merge is clean

**Explanation**:
- Experimental branch diverged from latest main (`974357d`)
- Main has no commits since divergence that touch modified files
- Only 2 files changed: `analysis/glass_box_audit.py` + new `EXPERIMENTAL_BRANCH_README.md`
- No other developer has modified these files

---

## 4. Untracked Files Assessment (CRITICAL ISSUE)

### Untracked Files Inventory (50+ files)

**Documentation Files** (20 files):
```
COMPARISON_GLASSBOX_VS_GPT4O_FREEFORM.md  ← Just created (important)
GPT4O_100PCT_DETECTION_WORKFLOW.md        ← Just created (important)
PROMPT_ENGINEERING_IMPACT_ANALYSIS.md     ← Just created (important)
FINAL_COMPARISON_3_RUNS.md
COMPARISON_REPORT_GLASSBOX_VS_GPT4O.md
COMPARISON_REPORT_UPDATED.md
COST_ANALYSIS.md
EXPERIMENTAL_RESULTS_30_30.md
GLASS_BOX_CURRENT_STATUS_2026.md
GLASS_BOX_REPRODUCIBILITY_PROTOCOL.md
GLASS_BOX_STEP_BY_STEP_VALIDATION.md
METADATA_CAPTURE_STATUS.md
RANDOMIZATION_IMPLEMENTATION_COMPLETE.md
READY_FOR_SCALE_UP.md
REPETITIONS_DECISION.md
STABILITY_REPORT_30_30.md
STATISTICAL_REASONING_RANDOMIZATION.md
TEMPORAL_STUDY_DESIGN_DECISION.md
TRUE_TEMPORAL_EXECUTION_GUIDE.md
CURRENT_IMPLEMENTATION_STATUS.md
```

**Analysis Scripts** (7 files):
```
analysis/glass_box_standalone.py
analysis/gpt4o_baseline.py
scripts/analyze_pilot_detection.py
scripts/compare_glass_box_vs_gpt4o.py
scripts/compare_glassbox_vs_gpt4o_freeform.py
scripts/compare_three_way.py
scripts/llm_direct_gpt4o_freeform.py
```

**Shell Scripts** (4 files):
```
scripts/monitor_audit.sh
scripts/rerun_pilot_audits_fixed.sh
check_stability_status.sh
monitor_validation.sh
test_critical_files.sh
wait_for_completion.sh
```

**Results Directories** (7 directories):
```
pilot_results/
pilot_results_fixed/
pilot_results_verification/
pilot_results_verification_29_of_30_baseline/
pilot_results_with_specs/
results/comparison_analysis/
results/glassbox_vs_gpt4o_freeform/
results/gpt4o_baseline/
results/gpt4o_baseline_run1/
results/gpt4o_baseline_run2/
results/llm_direct_gpt4o_freeform_responses/
```

**Log Files** (6 files):
```
glass_box_run.log
pilot_audit_log.txt
pilot_fix_test.log
pilot_fix_test_v2.log
pilot_specs_fix.log
```

**Data Files** (3 files):
```
outputs/crypto errors.docx
outputs/melatonin errors.docx
outputs/smartphone errors.docx
results/stability_report.json
```

### Untracked Files Problems

**Problem 1: Repository Bloat** 🔴
- **50+ untracked files** will make git messy
- Many are temporary logs/test results
- Binary `.docx` files should not be committed

**Problem 2: Git Ignore Missing** 🔴
- `.gitignore` doesn't cover pilot_results/, logs, etc.
- Need to update before committing

**Problem 3: Documentation Redundancy** 🔴
- Multiple comparison reports (COMPARISON_REPORT_GLASSBOX_VS_GPT4O.md, COMPARISON_REPORT_UPDATED.md, COMPARISON_GLASSBOX_VS_GPT4O_FREEFORM.md)
- Some files supersede others (need consolidation)

**Problem 4: Missing Validation** ⚠️
- Results show "30/30" in filenames (`pilot_individual_2026_run2`)
- But NO documented proof that experimental branch achieved 30/30
- EXPERIMENTAL_BRANCH_README.md says "Goal: Achieve 30/30" but doesn't show success

---

## 5. Future Merge Problems (CRITICAL)

### Problem A: Unvalidated Experimental Changes 🔴

**Issue**: The experimental branch adds 87 lines of code to fix RAM detection, but there's no evidence it works.

**Evidence**:
1. `results/pilot_individual_2026_run2/` contains 30 files
2. Some show "16 GB" detection (`grep "16 GB" results/pilot_individual_2026_run2/*.csv` found `smartphone_4.csv`)
3. **BUT**: These results could be from main branch (before experimental changes)
4. **No explicit test showing**: "After experimental changes, 30/30 detected"

**Problem**: If we merge and then discover the RAM fix **didn't work** or **broke other detections**, we'll have to:
- Revert the merge (messy)
- Debug in main branch (not ideal)
- Lose confidence in experimental workflow

**Required Before Merge**:
```bash
# On experimental/ram-category-fix branch
python3 analysis/glass_box_audit.py --run-id user_smartphone_4 --clean

# Verify RAM error detected
grep "16 GB" results/final_audit_results.csv

# Run all 30 files
bash scripts/rerun_pilot_audits_fixed.sh

# Check detection rate
python3 scripts/analyze_pilot_detection.py
# Expected output: "30/30 (100%)" or "Detection Rate: 100.0%"
```

### Problem B: Main Branch Out of Sync with Origin 🔴

**Issue**: Main branch is **12 commits ahead of origin/main**

```bash
$ git status  # (on main)
Your branch is ahead of 'origin/main' by 12 commits.
  (use "git push" to publish your local commits)
```

**Implications**:
1. **Local-only development** - No backup if machine fails
2. **Collaboration risk** - Other developers can't see latest work
3. **Merge complexity** - If someone else pushed to origin/main, we'll have conflicts
4. **CI/CD not running** - Automated tests (if any) haven't validated recent changes

**Timeline Analysis** (from git log):
```
974357d - docs: document 29/30 (96.7%) detection baseline as production-ready
fadccdc - checkpoint: glass_box_audit.py achieving 29/30 detection (96.7%)
dffca39 - docs: design complete 69-column metadata schema
fd5c26c - refactor: simplify to pure CSV architecture
da769a0 - feat: complete metadata schema part 2/2
1aed4d9 - feat: implement complete metadata schema part 1/2
af16852 - docs: add research context and model choice rationale
b6a81b9 - docs: update CLAUDE.md and AGENTS.md with Glass Box
ed881ac - feat: add full reproducibility for pilot study validation
24c56d2 - feat: achieve 100% pilot detection via prompt engineering
a4c7f6c - feat: improve claim extraction prompt
[... 1 more commit before origin/main]
```

**Risk**: If origin/main has diverged (someone else pushed), merging experimental branch could create conflicts.

**Required Before Merge**:
```bash
# Fetch latest from origin
git fetch origin

# Check if origin/main has new commits
git log main..origin/main

# If origin/main has changes, merge them first
git checkout main
git pull origin main

# Then merge experimental branch
git merge experimental/ram-category-fix
```

### Problem C: Documentation File Explosion 🔴

**Issue**: 20+ markdown documentation files at root level with overlapping content.

**Examples of Redundancy**:
1. **Comparison Reports** (3 files covering similar analyses):
   - `COMPARISON_REPORT_GLASSBOX_VS_GPT4O.md` (older)
   - `COMPARISON_REPORT_UPDATED.md` (updated version?)
   - `COMPARISON_GLASSBOX_VS_GPT4O_FREEFORM.md` (newest, most comprehensive)

2. **Status Reports** (multiple snapshots):
   - `GLASS_BOX_CURRENT_STATUS_2026.md`
   - `CURRENT_IMPLEMENTATION_STATUS.md`
   - `READY_FOR_SCALE_UP.md`

3. **Stability Reports** (redundant):
   - `STABILITY_REPORT_30_30.md`
   - `FINAL_COMPARISON_3_RUNS.md`

**Problem**: Root directory will have 40+ markdown files, making it hard to find relevant docs.

**Recommendation**: Organize docs before merging:
```
docs/
├── comparison/
│   └── COMPARISON_GLASSBOX_VS_GPT4O_FREEFORM.md  (keep newest only)
├── validation/
│   ├── FINAL_COMPARISON_3_RUNS.md
│   └── PROMPT_ENGINEERING_IMPACT_ANALYSIS.md
├── workflows/
│   └── GPT4O_100PCT_DETECTION_WORKFLOW.md
├── reproducibility/
│   └── GLASS_BOX_REPRODUCIBILITY_PROTOCOL.md
└── archive/
    └── [older versions]
```

### Problem D: Binary Files Committed (.docx) ⚠️

**Issue**: 3 `.docx` files in `outputs/`:
```
outputs/crypto errors.docx
outputs/melatonin errors.docx
outputs/smartphone errors.docx
```

**Problems**:
1. **Binary files don't diff well** in git (can't see changes)
2. **Repository bloat** (~50KB each)
3. **Not machine-readable** (can't grep or parse)

**Recommendation**: Convert to markdown or CSV before committing:
```markdown
# outputs/smartphone_errors.md
| File | Error Type | Description |
|------|-----------|-------------|
| smartphone_1 | RAM | 16 GB instead of 12 GB |
| smartphone_2 | Display | 6.5" instead of 6.3" |
...
```

Or extract to CSV:
```csv
file,error_type,incorrect_value,correct_value
smartphone_1,ram,16 GB,12 GB
smartphone_2,display,6.5 inch,6.3 inch
...
```

### Problem E: Git Ignore Gaps 🔴

**Issue**: Many temporary/generated files not in `.gitignore`

**Files that should be ignored**:
```
# Logs
*.log
pilot_audit_log.txt
pilot_fix_test*.log
pilot_specs_fix.log

# Temporary results
pilot_results*/
results/gpt4o_baseline*/
results/comparison_analysis/
results/llm_direct_*/

# Shell scripts (maybe - depends on if they're tools or experiments)
check_*.sh
monitor_*.sh
wait_for_*.sh
test_*.sh
```

**Required**: Update `.gitignore` before committing untracked files.

---

## 6. Merge Strategy Recommendation

### ❌ **DO NOT MERGE YET**

**Reason**: Experimental changes not validated to achieve 30/30 detection.

### ✅ **Pre-Merge Checklist** (Must Complete All)

#### 1. Validate Experimental Changes (CRITICAL)
```bash
# Switch to experimental branch
git checkout experimental/ram-category-fix

# Clean previous results
rm -rf results/final_audit_results.csv

# Test single problematic file (smartphone_4 with 16 GB RAM error)
python3 analysis/glass_box_audit.py --run-id user_smartphone_4 --clean

# Verify RAM error detected
grep -i "16 GB" results/final_audit_results.csv
# Expected: Line showing RAM contradiction

# Run all 30 pilot files
bash scripts/rerun_pilot_audits_fixed.sh
# OR manually:
for i in {1..10}; do
    python3 analysis/glass_box_audit.py --run-id user_smartphone_$i --clean
    python3 analysis/glass_box_audit.py --run-id user_melatonin_$i --clean
    python3 analysis/glass_box_audit.py --run-id user_corecoin_$i --clean
done

# Analyze detection rate
python3 scripts/analyze_pilot_detection.py
# Expected: "30/30 (100.0%)" detection rate

# Document results
echo "Experimental validation results:" > EXPERIMENTAL_VALIDATION_RESULTS.md
python3 scripts/analyze_pilot_detection.py >> EXPERIMENTAL_VALIDATION_RESULTS.md
```

**Success Criteria**:
- ✅ smartphone_4 detected (16 GB RAM error caught)
- ✅ 30/30 total detection (no regressions)
- ✅ All 29 previously detected errors still caught

**If validation FAILS**:
- Stay on main branch (29/30 is production-ready)
- Delete experimental branch
- Document what didn't work

#### 2. Sync Main Branch with Origin
```bash
# Switch to main
git checkout main

# Fetch latest
git fetch origin

# Check if origin/main has diverged
git log main..origin/main
# If empty: no divergence (safe to push)
# If commits: origin has changes (need to pull first)

# If origin has changes, merge them
git pull origin main

# Resolve any conflicts

# Push local commits to origin
git push origin main
```

#### 3. Organize Documentation Files
```bash
# Create docs structure
mkdir -p docs/{comparison,validation,workflows,reproducibility,archive}

# Move latest comprehensive docs
git mv COMPARISON_GLASSBOX_VS_GPT4O_FREEFORM.md docs/comparison/
git mv GPT4O_100PCT_DETECTION_WORKFLOW.md docs/workflows/
git mv FINAL_COMPARISON_3_RUNS.md docs/validation/
git mv PROMPT_ENGINEERING_IMPACT_ANALYSIS.md docs/validation/
git mv GLASS_BOX_REPRODUCIBILITY_PROTOCOL.md docs/reproducibility/

# Archive older versions
git mv COMPARISON_REPORT_GLASSBOX_VS_GPT4O.md docs/archive/
git mv COMPARISON_REPORT_UPDATED.md docs/archive/

# Commit reorganization
git commit -m "docs: organize documentation into subdirectories"
```

#### 4. Update .gitignore
```bash
# Add to .gitignore
cat >> .gitignore << 'EOF'

# Pilot study temporary results
pilot_results*/
pilot_*.log

# Temporary analysis results
results/gpt4o_baseline_run*/
results/comparison_analysis/
results/llm_direct_*/

# Log files
*.log
glass_box_run.log

# Temporary scripts (keep tracked scripts only)
check_*.sh
monitor_*.sh
wait_for_*.sh
test_critical_files.sh

# Binary docs (convert to markdown instead)
*.docx
EOF

git add .gitignore
git commit -m "chore: update .gitignore to exclude temp files and logs"
```

#### 5. Convert Binary Files to Markdown
```bash
# Manually extract .docx contents and create markdown
# (or use python-docx to automate)

# Example: outputs/smartphone_errors.md
cat > outputs/smartphone_errors.md << 'EOF'
# Smartphone Intentional Errors (Ground Truth)

| File | Error Type | Incorrect Claim | Correct Value |
|------|-----------|----------------|---------------|
| smartphone_1 | RAM | 16 GB | 12 GB |
| smartphone_2 | Display | 6.5" | 6.3" |
...
EOF

# Remove .docx files
rm outputs/*.docx

# Commit markdown versions
git add outputs/*.md
git commit -m "docs: convert ground truth errors to markdown"
```

#### 6. Commit Key Untracked Files (Selectively)
```bash
# Only commit essential docs (not temp results/logs)

# Essential docs
git add COMPARISON_GLASSBOX_VS_GPT4O_FREEFORM.md
git add GPT4O_100PCT_DETECTION_WORKFLOW.md
git add PROMPT_ENGINEERING_IMPACT_ANALYSIS.md
git add FINAL_COMPARISON_3_RUNS.md

# Essential scripts
git add analysis/gpt4o_baseline.py
git add scripts/compare_glassbox_vs_gpt4o_freeform.py
git add scripts/llm_direct_gpt4o_freeform.py

# Commit with clear message
git commit -m "docs: add comprehensive comparison and workflow documentation

- COMPARISON_GLASSBOX_VS_GPT4O_FREEFORM.md: Glass Box (100%) vs GPT-4o Free-Form (43%)
- GPT4O_100PCT_DETECTION_WORKFLOW.md: Structured JSON prompt workflow
- PROMPT_ENGINEERING_IMPACT_ANALYSIS.md: Isolates model vs prompt impact
- FINAL_COMPARISON_3_RUNS.md: 3-run stability validation
- Scripts for reproducibility: gpt4o_baseline.py, comparison scripts"
```

#### 7. Merge Experimental Branch (After All Above Completed)
```bash
# Ensure we're on main with all prep work committed
git checkout main

# Merge experimental branch
git merge experimental/ram-category-fix

# Update commit message to reference validation results
git commit --amend -m "feat: add category-aware numerical contradiction detection for RAM errors

Fixes smartphone_4 detection (16 GB RAM error) by:
1. Adding rule-based numerical contradiction checker
2. Category-aware comparison (RAM vs RAM, not RAM vs storage)
3. Reordering category keywords (RAM before storage)

Validation: Achieved 30/30 (100%) detection on pilot study
(see EXPERIMENTAL_VALIDATION_RESULTS.md)

Closes experimental/ram-category-fix branch"

# Push to origin
git push origin main

# Delete experimental branch (locally and remotely)
git branch -d experimental/ram-category-fix
```

---

## 7. Alternative Strategy: Keep Experimental Branch

If validation shows experimental changes **did not achieve 30/30**:

```bash
# Stay on main (production-ready 29/30)
git checkout main

# Optionally: Keep experimental branch for future work
# (Don't merge, don't delete)

# Document why merge was rejected
cat > EXPERIMENTAL_BRANCH_DECISION.md << 'EOF'
# Decision: Do Not Merge experimental/ram-category-fix

**Date**: 2026-02-25
**Validation Results**: [X/30 detection]

## Reason for Rejection
- Did not achieve 30/30 detection goal
- OR: Broke existing 29/30 detections (regressions)
- OR: Added unacceptable complexity for 1-error improvement

## Main Branch Status
- Remains at 29/30 (96.7%) detection
- Documented as production-ready
- Sufficient for research paper

## Lessons Learned
- [What we learned from this experiment]
- [Ideas for future improvements]
EOF
```

---

## 8. Risk Assessment Matrix

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| **Experimental changes don't work** | 🟡 Medium | 🔴 High | Validate 30/30 before merge |
| **Merge causes regressions** | 🟡 Medium | 🔴 High | Test all 30 files post-merge |
| **Git conflicts with origin** | 🟢 Low | 🟡 Medium | Sync with origin before merge |
| **Documentation bloat** | 🔴 High | 🟢 Low | Organize into docs/ subdirectories |
| **Binary files in repo** | 🔴 High | 🟡 Medium | Convert to markdown first |
| **Untracked files committed accidentally** | 🟡 Medium | 🟡 Medium | Update .gitignore first |
| **Can't reproduce results** | 🟡 Medium | 🟡 Medium | Document validation process |

---

## 9. Final Recommendations

### Immediate Actions (Before Any Merge)

1. ✅ **Validate experimental branch** - Prove 30/30 detection
2. ✅ **Sync main with origin** - Push 12 unpushed commits
3. ✅ **Update .gitignore** - Prevent temp file commits
4. ✅ **Organize documentation** - Move to docs/ subdirectories
5. ✅ **Convert .docx to markdown** - Avoid binary commits

### Merge Decision Tree

```
Is experimental branch validated (30/30)?
├─ YES → Proceed with merge
│   ├─ Main synced with origin? → YES → Merge
│   └─ Main synced with origin? → NO → Sync first, then merge
└─ NO → Do NOT merge
    ├─ 29/30 still achieved? → YES → Stay on main (production-ready)
    └─ <29/30 (regression)? → YES → Delete experimental branch
```

### Long-Term Improvements

1. **Add unit tests** for new functions (`extract_numbers_with_units`, `check_numerical_contradiction`)
2. **Create CI/CD pipeline** to auto-validate detection rate on each commit
3. **Document experimental workflow** in CLAUDE.md
4. **Establish branch protection rules** (require validation before merge)

---

## 10. Summary

**Current State**:
- ✅ Branch merge is **technically clean** (no conflicts)
- ⚠️ Experimental changes **not validated**
- 🔴 Main branch **12 commits ahead of origin** (not synced)
- 🔴 **50+ untracked files** need organization

**Recommended Action**: **DO NOT MERGE YET**

**Next Steps**:
1. Validate experimental branch achieves 30/30 detection
2. If YES: Follow 7-step pre-merge checklist
3. If NO: Stay on main (29/30 is production-ready)

**Timeline Estimate**:
- Validation testing: 1-2 hours (run 30 files + analyze)
- Pre-merge cleanup: 2-3 hours (docs organization + .gitignore)
- Merge execution: 30 minutes
- **Total**: 4-6 hours of focused work

**Key Insight**: The experimental branch adds **well-written code** (+87 lines, good docs, no obvious bugs), but **we have no proof it works**. The 30/30 detection claim needs validation before merging to main.

---

**End of Assessment**
