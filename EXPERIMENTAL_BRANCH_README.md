# Experimental Branch: ram-category-fix

**Branch**: `experimental/ram-category-fix`
**Base**: `main` at commit `974357d`
**Goal**: Attempt to achieve 30/30 (100%) detection on pilot study

---

## Baseline on Main Branch

- **Detection**: 29/30 (96.7%) ✅
- **Status**: Production-ready
- **Commit**: `fadccdc` (checkpointed)
- **Documentation**: `GLASS_BOX_BASELINE_29_30.md`

---

## Experimental Goals

### **Primary Goal**
Achieve 30/30 (100%) detection by fixing the smartphone_4 miss (16 GB RAM error).

### **Success Criteria**
- ✅ Must detect smartphone_4 (30/30 total)
- ✅ Must NOT break any of the existing 29 detections
- ✅ Must pass on all 30 pilot files

### **Merge Criteria**
- If **≥30/30**: Merge to main via PR
- If **29/30** (same as baseline): Optional merge if code quality improved
- If **<29/30** (regression): Delete branch, stay on main

---

## Experiments to Try

### **Experiment 1: Word Boundaries (Option 3)**
- Already tested: commit `ff9737f` (reverted)
- Result: Reduced pollution but didn't solve NLI cross-category matching
- Status: ❌ Didn't achieve 30/30

### **Experiment 2: Apply Category Filtering to Authorized Claims**
- Hypothesis: Category filter currently only applies to specs, not authorized claims
- Change: Filter authorized claims by category before NLI comparison
- Risk: Medium - might break existing detections if claims are too narrowly filtered

### **Experiment 3: Semantic Filtering**
- Use `--use-semantic-filter` flag
- Leverage sentence embeddings instead of keyword categories
- Risk: Low - already implemented, just needs testing

### **Experiment 4: Hybrid Approach**
- Combine word boundaries + semantic filtering
- Risk: Medium - multiple changes at once

### **Experiment 5: Adjust NLI Threshold**
- Lower contradiction threshold (e.g., 0.85 instead of 0.90)
- Risk: High - might increase false positives across all 30 files

---

## Testing Protocol

### **Before any change:**
```bash
# Ensure we're on experimental branch
git branch --show-current  # Should show: experimental/ram-category-fix

# Test single file (smartphone_4)
python3 analysis/glass_box_audit.py --run-id user_smartphone_4 --clean

# Check if RAM error detected correctly
grep "16 GB" results/final_audit_results.csv
```

### **After each change:**
```bash
# Commit the change
git add -A
git commit -m "experiment: [description]"

# Test all 30 files
bash scripts/rerun_pilot_audits_fixed.sh

# Check detection rate
python3 scripts/analyze_pilot_detection.py
```

### **If successful (≥30/30):**
```bash
# Switch to main
git checkout main

# Merge experimental branch
git merge experimental/ram-category-fix

# Push to remote
git push origin main
```

### **If failed (<29/30):**
```bash
# Switch to main
git checkout main

# Delete experimental branch
git branch -D experimental/ram-category-fix
```

---

## Commit Log

Track experiments here:

- `974357d` - Base commit (main branch with 29/30 documentation)
- [Add experiment commits as they happen]

---

## Notes

- **Safe to experiment**: Main branch is protected at 29/30 baseline
- **No pressure**: Can abandon experiments at any time
- **Learn from failures**: Document what didn't work for future reference
