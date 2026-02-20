# Detection Analysis Process - Standard Operating Procedure

**Purpose:** Prevent false negative reporting due to faulty keyword matching.

**Problem:** Multiple instances of reporting errors as "missed" when they were actually detected, caused by:
1. Brittle keyword matching (exact string requirements)
2. No manual verification step
3. Trusting automated scripts without validation

---

## Standard Process (MANDATORY)

### Step 1: Run Robust Analysis Script

```bash
source .venv/bin/activate
python3 scripts/detection_analysis_robust.py > results/detection_analysis.txt
```

**This script provides:**
- ✅ Fuzzy/partial matching (not exact keywords)
- ✅ Shows actual matched violations with confidence scores
- ✅ Displays search terms used
- ✅ Warning about manual verification needed

### Step 2: Manual Verification of "Missed" Errors

**For EACH error reported as "missed":**

1. Open the CSV file: `results/pilot_individual/{product}_{file_num}.csv`
2. Search (Ctrl+F) for key concepts related to the error
3. Check if ANY violation mentions the error concept
4. If found → Update search terms and re-run analysis
5. If truly missing → Document why (spec gap, policy error, etc.)

**Example:**
```bash
# Error reported as "missed": Lead 5 mcg
# Manual check:
grep -i "lead" results/pilot_individual/melatonin_5.csv

# Found: "lead < 5 ppm"
# → Error WAS detected
# → Fix: Update search terms to include "ppm" variant
```

### Step 3: Document Verification

Create verification log:

```markdown
## Verification Log - [Date]

### Errors Reported as Missed: X

1. **[Product]_[File]: [Error Description]**
   - Search terms used: [list]
   - Manual check: [grep command used]
   - Result: [TRULY MISSED | FALSE NEGATIVE - detected as "..."]
   - Action: [Updated search terms | Added to spec gaps | etc.]

2. ...
```

### Step 4: Report Results Only After Verification

**DO NOT report detection rates until:**
- ✅ Robust analysis script run
- ✅ ALL "missed" errors manually verified
- ✅ Verification log created
- ✅ Search terms updated if false negatives found
- ✅ Re-run analysis to confirm

---

## Tools and Scripts

### Primary Tool: `detection_analysis_robust.py`

**Features:**
- Fuzzy text matching (handles variations)
- Shows top 3 matching violations with confidence
- Displays context around matches
- Warns when manual verification needed

**Usage:**
```bash
python3 scripts/detection_analysis_robust.py
```

**Output includes:**
```
File 4 : ✅ DETECTED      - 16 GB RAM option
         (37 violations, 2 matched)
         Best match: "Nova X5 has RAM configurations of 8 GB..." (99.24%)
```

This shows:
- ✅ Error was detected
- 37 total violations in file
- 2 violations mentioned "16 GB"
- Best match with 99.24% confidence

### Validation Tool: `validate_detection_analysis.py`

**Purpose:** Catch false negatives before reporting

**Usage:**
```bash
python3 scripts/validate_detection_analysis.py
```

**When to use:** After running initial analysis, before reporting results

**What it does:**
- Takes errors marked as "missed"
- Searches their CSV files broadly (not strict keywords)
- Identifies if error actually appears in violations
- Reports false negatives with evidence

---

## Common Pitfalls to Avoid

### ❌ Don't: Use Exact String Matching

```python
# BAD - will miss variations
if "16 GB RAM" in violation:
    detected = True
```

```python
# GOOD - allows variations
if any(term in violation.lower() for term in ["16 gb", "16gb", "16 gig"]):
    detected = True
```

### ❌ Don't: Trust First Analysis

```python
# BAD workflow
results = analyze_detection()
report_to_user(results)  # ← Missing verification!
```

```python
# GOOD workflow
results = analyze_detection_robust()
verified_results = manual_verify_missed_errors(results)
if all_verified(verified_results):
    report_to_user(verified_results)
else:
    update_search_terms()
    re_analyze()
```

### ❌ Don't: Use Product-Specific Keywords

**Problem:** Error might be phrased differently in each file

```python
# BAD - too specific
"FDA approved supplements"  # Won't match "approved by the FDA"
```

```python
# GOOD - broad concepts
["fda", "food and drug", "approved"]  # Matches any mention
```

### ❌ Don't: Ignore Unit Conversions

**Problem:** GPT-4o might normalize units during extraction

```python
# Original error: "Lead 5 mcg"
# Extracted claim: "lead < 5 ppm"
# → Need both units in search terms
search_terms = ["5 mcg", "5 ppm", "lead 5", "5.0"]
```

---

## Checklist Before Reporting

- [ ] Ran `detection_analysis_robust.py`
- [ ] For each "missed" error:
  - [ ] Opened CSV file
  - [ ] Searched for error concept
  - [ ] Documented finding in verification log
- [ ] Updated search terms if false negatives found
- [ ] Re-ran analysis after updates
- [ ] All "missed" errors confirmed as truly missed
- [ ] Created verification log file
- [ ] Ready to report

---

## Example: Full Workflow

```bash
# 1. Run robust analysis
python3 scripts/detection_analysis_robust.py > detection_report.txt

# 2. Review output
cat detection_report.txt | grep "MISSED"
# Output shows: melatonin_8 missed (FDA approved)

# 3. Manual verification
grep -i "fda" results/pilot_individual/melatonin_8.csv
# Output: "This product is approved by the FDA..."

# 4. Conclusion: FALSE NEGATIVE (was detected)

# 5. Update search terms
# Edit detection_analysis_robust.py:
# OLD: "search_terms": ["fda approved"]
# NEW: "search_terms": ["fda", "food and drug", "approved"]

# 6. Re-run
python3 scripts/detection_analysis_robust.py > detection_report_v2.txt

# 7. Verify now shows detected
cat detection_report_v2.txt | grep "melatonin_8"
# Output: "✅ DETECTED - FDA approved"

# 8. Create verification log
cat > verification_log.md << EOF
## Verification - 2026-02-20

### Initial: 1 error reported as missed
- melatonin_8: FDA approved

### Verification:
- Searched: grep -i "fda" melatonin_8.csv
- Found: "approved by the FDA for sleep regulation"
- Conclusion: FALSE NEGATIVE

### Action:
- Updated search terms to ["fda", "approved"]
- Re-run confirmed: ✅ DETECTED

### Final Result:
- Melatonin: 10/10 (100%)
EOF

# 9. NOW safe to report results
```

---

## Why This Matters

**Previous pattern:**
1. Run quick script → Report 80-85% detection
2. User challenges → Manual check → Actually 90%
3. Run again → Report 85% → User challenges → Actually 90%
4. **Wastes user's time validating my work**

**With this process:**
1. Run robust script
2. Verify all "missed" errors
3. Report accurate 90% detection
4. **User can trust the results**

---

## Success Metrics

### Before Process (Historical):
- Reported: 80-85% detection
- Actual: 90% detection
- False negative rate: ~30-50% of "missed" errors

### After Process (Target):
- Reported: 90% detection
- Actual: 90% detection
- False negative rate: <5% of "missed" errors

---

## Summary

**The Golden Rule:**

> Never report an error as "missed" without manually inspecting the CSV file to confirm it's truly absent.

**If you can't show me the CSV proving it's missing, don't report it as missed.**
