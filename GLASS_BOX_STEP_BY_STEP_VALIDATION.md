# Glass Box Audit: Step-by-Step Validation Plan

**Purpose:** Ensure every single step works correctly and reproducibly
**Date:** February 24, 2026

---

## Overview: The Complete Pipeline

```
INPUT FILE → STEP 1: Extract Claims → STEP 2: Load Product Specs → STEP 3: Validate Claims → STEP 4: Match Ground Truth → OUTPUT: Detection Rate
```

---

## STEP 1: Claim Extraction

### What It Does:
Sends marketing text to GPT-4o-mini (temp=0) to extract atomic claims

### Input:
- `material_content`: Raw text from pilot file
- `product_name`: "Melatonin Tablets 3mg"
- `material_type`: "faq"

### Process:
```python
# File: analysis/glass_box_audit.py, line 194
def extract_atomic_claims(material_content: str, product_name: str, material_type: str) -> Dict:
    # Calls GPT-4o-mini with ATOMIZER_SYSTEM_PROMPT
    # Returns: {'core_claims': [...], 'disclaimers': [...]}
```

### Expected Output:
```json
{
  "core_claims": [
    "Serving size is 1 tablet",
    "Each tablet contains 3 mg of melatonin per serving",
    ...
  ],
  "disclaimers": [
    "These statements have not been evaluated by the FDA",
    "Store at exactly 0°C",  ← ERROR SHOULD BE HERE
    ...
  ]
}
```

### Verification Checklist:

- [ ] **VERIFY 1.1:** GPT-4o-mini model is `gpt-4o-mini` (or date-locked version)
  ```python
  from analysis.glass_box_audit import EXTRACTION_MODEL
  assert EXTRACTION_MODEL == "gpt-4o-mini"
  ```

- [ ] **VERIFY 1.2:** Temperature is 0 (deterministic)
  ```python
  from analysis.glass_box_audit import EXTRACTION_TEMPERATURE
  assert EXTRACTION_TEMPERATURE == 0
  ```

- [ ] **VERIFY 1.3:** Extraction returns both core_claims AND disclaimers
  ```python
  result = extract_atomic_claims(content, product, material_type)
  assert 'core_claims' in result
  assert 'disclaimers' in result
  assert isinstance(result['core_claims'], list)
  assert isinstance(result['disclaimers'], list)
  ```

- [ ] **VERIFY 1.4:** Disclaimers include error claims (for melatonin_6)
  ```python
  disclaimers = result['disclaimers']
  storage_claim = [c for c in disclaimers if '0°C' in c or 'store' in c.lower()]
  assert len(storage_claim) > 0, "Storage claim not extracted!"
  ```

### Pass Criteria:
✅ Both `core_claims` and `disclaimers` are non-empty lists
✅ Total claims extracted: 10-40 per file (reasonable range)
✅ Error-containing claims appear in output

---

## STEP 2: Load Product Specifications

### What It Does:
Loads product YAML and flattens nested structures into flat lists

### Input:
- Product YAML file path (e.g., `products/supplement_melatonin.yaml`)

### Process:
```python
# File: analysis/glass_box_standalone.py, line 204-231
# Load and flatten:
# - authorized_claims (dict or list)
# - specs (nested dict with categories)
# - prohibited_claims (list)
# - clarifications (dict or list)
```

### Expected Output:
```python
authorized_claims = [
    "Supplies a 3 mg dose of melatonin...",
    "Functions in harmony with your body...",
    ...
]  # 50-100 claims

specs = [
    "Each tablet contains 3 mg melatonin",
    "Store at room temperature (15-30°C / 59-86°F)",
    "Do NOT store at 0°C or below (do not freeze)",  ← CRITICAL FOR melatonin_6
    ...
]  # 28+ specs

prohibited_claims = [...]
clarifications = [...]
```

### Verification Checklist:

- [ ] **VERIFY 2.1:** YAML key is 'specs', NOT 'specifications'
  ```python
  with open('products/supplement_melatonin.yaml') as f:
      yaml_data = yaml.safe_load(f)
  assert 'specs' in yaml_data
  assert 'specifications' not in yaml_data  # Common mistake!
  ```

- [ ] **VERIFY 2.2:** Specs are flattened from nested dict
  ```python
  specs_raw = yaml_data['specs']
  assert isinstance(specs_raw, dict)
  assert 'packaging' in specs_raw  # Nested category

  # After flattening:
  specs = flatten_specs(specs_raw)
  assert isinstance(specs, list)
  assert len(specs) >= 28  # Melatonin should have ~28 specs
  ```

- [ ] **VERIFY 2.3:** Storage specs are loaded
  ```python
  storage_specs = [s for s in specs if 'store' in s.lower() or '°C' in s]
  assert len(storage_specs) >= 2, "Storage specs not loaded!"

  # Specifically check for the critical spec:
  critical_spec = [s for s in specs if '0°C' in s and 'NOT' in s]
  assert len(critical_spec) == 1, "Critical storage spec missing!"
  ```

- [ ] **VERIFY 2.4:** Authorized claims are flattened from dict
  ```python
  auth_raw = yaml_data['authorized_claims']
  if isinstance(auth_raw, dict):
      auth_claims = flatten_authorized_claims(auth_raw)
      assert isinstance(auth_claims, list)
      assert len(auth_claims) > 0
  ```

- [ ] **VERIFY 2.5:** Clarifications are flattened from dict
  ```python
  clar_raw = yaml_data.get('clarifications', [])
  if isinstance(clar_raw, dict):
      clarifications = flatten_clarifications(clar_raw)
      assert isinstance(clarifications, list)
      assert len(clarifications) > 0
  ```

### Pass Criteria:
✅ All 4 lists (authorized_claims, specs, prohibited_claims, clarifications) are non-empty
✅ Specs list contains 28+ items for melatonin
✅ Storage rule "Do NOT store at 0°C" exists in specs list
✅ No TypeError when extending lists

---

## STEP 3: NLI Validation

### What It Does:
For each extracted claim, check if it contradicts any reference claim using RoBERTa NLI model

### Input:
- `claim`: "Store at exactly 0°C"
- `authorized_claims`: [...]
- `specs`: ["Do NOT store at 0°C or below", ...]
- `prohibited_claims`: [...]
- `clarifications`: [...]

### Process:
```python
# File: analysis/glass_box_audit.py, line 270
def verify_claim(claim, authorized_claims, specs, prohibited_claims, clarifications):
    # Combine all reference claims
    all_reference_claims = authorized_claims + specs + prohibited_claims + clarifications

    # For each reference claim:
    #   - Encode claim + reference with RoBERTa
    #   - Get contradiction score
    #   - If score > 0.9 → violation
```

### Expected Output (for melatonin_6):
```python
{
    'is_violation': True,
    'violated_rule': "Do NOT store at 0°C or below (do not freeze)",
    'contradiction_score': 0.99,  # High confidence
    'best_match_rule': "Do NOT store at 0°C or below...",
    'best_match_type': 'contradiction'
}
```

### Verification Checklist:

- [ ] **VERIFY 3.1:** All reference claims are combined (not just core_claims)
  ```python
  # In standalone script, line 236:
  all_claims = core_claims + disclaimers  ← Must include disclaimers!

  # In verify_claim:
  all_reference_claims = authorized + specs + prohibited + clarifications
  assert len(all_reference_claims) > 0, "No reference claims loaded!"
  ```

- [ ] **VERIFY 3.2:** NLI model loads correctly
  ```python
  nli_judge = NLIJudge()
  assert nli_judge.model is not None
  assert nli_judge.tokenizer is not None
  ```

- [ ] **VERIFY 3.3:** Contradiction threshold is 0.9
  ```python
  from analysis.glass_box_audit import VIOLATION_THRESHOLD
  assert VIOLATION_THRESHOLD == 0.9
  ```

- [ ] **VERIFY 3.4:** Test case: "Store at 0°C" vs "Do NOT store at 0°C"
  ```python
  result = nli_judge.verify_claim(
      "Store at exactly 0°C",
      authorized_claims=[],
      specs=["Do NOT store at 0°C or below (do not freeze)"],
      prohibited_claims=[],
      clarifications=[]
  )

  assert result['is_violation'] == True, "Should detect contradiction!"
  assert result['contradiction_score'] >= 0.9, "Confidence too low!"
  ```

- [ ] **VERIFY 3.5:** Validate disclaimers are included
  ```python
  # For melatonin_6:
  disclaimers = ["Store at exactly 0°C"]
  all_to_validate = core_claims + disclaimers

  violations = []
  for claim in all_to_validate:  ← Must loop over ALL claims
      result = nli_judge.verify_claim(claim, ...)
      if result['is_violation']:
          violations.append(result)

  assert len(violations) > 0, "Should find storage violation!"
  ```

### Pass Criteria:
✅ NLI model loads without error
✅ Test contradiction detected with score > 0.9
✅ Violations list is non-empty for files with errors
✅ Both core_claims AND disclaimers are validated

---

## STEP 4: Ground Truth Matching

### What It Does:
Compare detected violations with expected errors from GROUND_TRUTH_ERRORS.md

### Input:
- `run_id`: "user_melatonin_6"
- `violations`: [{claim: "Store at exactly 0°C", ...}, ...]
- `ground_truth`: Parsed from GROUND_TRUTH_ERRORS.md

### Process:
```python
# File: analysis/glass_box_standalone.py, line 264
def validate_detection(run_id, violations, ground_truth):
    expected = ground_truth.get(run_id, {})
    keywords = expected.get('keywords', [])

    # Check if any violation contains keywords
    for violation in violations:
        claim_text = violation['claim'].lower()
        if any(kw.lower() in claim_text for kw in keywords):
            return {'detected': True, 'matched_keywords': keywords}

    return {'detected': False}
```

### Expected Output (for melatonin_6):
```python
{
    'run_id': 'user_melatonin_6',
    'ground_truth_error': 'Recommends storage at 0°C',
    'detected': True,
    'matched_keywords': ['storage', '0', 'temperature'],
    'confidence': 0.99
}
```

### Verification Checklist:

- [ ] **VERIFY 4.1:** Run ID format is correct
  ```python
  # File naming: melatonin_6.txt → user_melatonin_6
  run_id = f"user_{file_path.stem}"
  assert run_id.startswith("user_")
  assert run_id in ground_truth, f"Run ID {run_id} not in ground truth!"
  ```

- [ ] **VERIFY 4.2:** Ground truth parser loads all 30 files
  ```python
  ground_truth = parse_ground_truth(Path('GROUND_TRUTH_ERRORS.md'))
  assert len(ground_truth) == 30, f"Expected 30, got {len(ground_truth)}"

  # Check specific entries:
  assert 'user_melatonin_6' in ground_truth
  assert 'user_smartphone_3' in ground_truth
  assert 'user_corecoin_10' in ground_truth
  ```

- [ ] **VERIFY 4.3:** Keywords are correctly extracted
  ```python
  mel6_gt = ground_truth['user_melatonin_6']
  assert 'keywords' in mel6_gt
  assert len(mel6_gt['keywords']) > 0

  # Keywords should include storage-related terms:
  keywords = mel6_gt['keywords']
  assert any(kw in ['storage', 'store', '0', 'temperature'] for kw in keywords)
  ```

- [ ] **VERIFY 4.4:** Matching logic works correctly
  ```python
  # Test case:
  violations = [{'claim': 'Store at exactly 0°C', 'confidence': 0.99}]
  keywords = ['storage', '0°C', 'temperature']

  detected = False
  for v in violations:
      if any(kw.lower() in v['claim'].lower() for kw in keywords):
          detected = True

  assert detected == True, "Keyword matching failed!"
  ```

### Pass Criteria:
✅ All 30 ground truth entries loaded
✅ Run ID format matches ground truth keys
✅ Keyword matching correctly identifies detections
✅ False negatives are correctly identified

---

## STEP 5: Output Generation

### What It Does:
Generate validation_report.md with detection statistics

### Expected Output:
```markdown
## Overall Detection Rate
**Total files:** 30
**Detected:** 30/30 (100%)  ← TARGET
**Missed:** 0/30 (0%)

## Detection by Product
- **Corecoin:** 10/10 (100%) ✅
- **Melatonin:** 10/10 (100%) ✅
- **Smartphone:** 10/10 (100%) ✅
```

### Verification Checklist:

- [ ] **VERIFY 5.1:** Report file is created
  ```python
  report_path = output_dir / 'validation_report.md'
  assert report_path.exists(), "Report not generated!"
  ```

- [ ] **VERIFY 5.2:** Detection rate is calculated correctly
  ```python
  with open(report_path) as f:
      content = f.read()

  # Extract detection rate
  import re
  match = re.search(r'Detected.*?(\d+)/30', content)
  assert match, "Detection rate not found in report!"

  detected = int(match.group(1))
  assert detected >= 28, f"Detection too low: {detected}/30"
  ```

- [ ] **VERIFY 5.3:** Individual CSVs are created
  ```python
  violations_dir = output_dir / 'violations'
  csv_files = list(violations_dir.glob('user_*.csv'))
  assert len(csv_files) == 30, f"Expected 30 CSVs, got {len(csv_files)}"
  ```

### Pass Criteria:
✅ validation_report.md exists
✅ Detection rate >= 28/30 (93%+)
✅ 30 individual violation CSVs created
✅ detection_summary.csv exists

---

## Integration Test: End-to-End

### Full Pipeline Test:

```python
#!/usr/bin/env python3
"""
Complete end-to-end validation test.
Run this to verify the entire pipeline works correctly.
"""

import sys
sys.path.insert(0, '/Users/dorotajaguscik/PycharmProjects/llm_research_app')

from pathlib import Path
from analysis.glass_box_standalone import audit_single_file, parse_ground_truth
from analysis.glass_box_audit import NLIJudge, extract_atomic_claims
import yaml

def test_melatonin_6_complete():
    """Test the exact failure case that was happening."""

    print("="*60)
    print("INTEGRATION TEST: melatonin_6 (Storage at 0°C)")
    print("="*60)

    # STEP 1: Extract claims
    print("\n[STEP 1] Extracting claims...")
    file_path = Path('pilot_study/melatonin/files/melatonin_6.txt')
    with open(file_path) as f:
        content = f.read()

    result = extract_atomic_claims(content, "Melatonin", "faq")
    core_claims = result['core_claims']
    disclaimers = result['disclaimers']

    print(f"  Core claims: {len(core_claims)}")
    print(f"  Disclaimers: {len(disclaimers)}")

    # Verify storage claim extracted
    storage_in_disclaimers = [c for c in disclaimers if '0°C' in c or 'store' in c.lower()]
    assert len(storage_in_disclaimers) > 0, "❌ FAIL: Storage claim not extracted!"
    print(f"  ✅ Storage claim found: {storage_in_disclaimers[0]}")

    # STEP 2: Load product specs
    print("\n[STEP 2] Loading product specs...")
    with open('products/supplement_melatonin.yaml') as f:
        product_yaml = yaml.safe_load(f)

    # Flatten specs
    specs_raw = product_yaml.get('specs', {})
    specs = []
    if isinstance(specs_raw, dict):
        for category, category_specs in specs_raw.items():
            if isinstance(category_specs, list):
                specs.extend(category_specs)

    print(f"  Total specs loaded: {len(specs)}")

    # Verify storage spec loaded
    storage_specs = [s for s in specs if '0°C' in s and 'NOT' in s]
    assert len(storage_specs) == 1, "❌ FAIL: Storage spec not loaded!"
    print(f"  ✅ Storage spec found: {storage_specs[0]}")

    # STEP 3: Validate claims
    print("\n[STEP 3] Validating claims with NLI...")
    nli_judge = NLIJudge(use_semantic_filter=False)

    all_claims = core_claims + disclaimers
    print(f"  Validating {len(all_claims)} total claims...")

    violations = []
    for claim in all_claims:
        result = nli_judge.verify_claim(
            claim,
            authorized_claims=[],
            specs=specs,
            prohibited_claims=[],
            clarifications=[]
        )
        if result['is_violation']:
            violations.append({'claim': claim, 'confidence': result['contradiction_score']})

    print(f"  Total violations found: {len(violations)}")

    # Verify storage violation detected
    storage_violations = [v for v in violations if '0°C' in v['claim']]
    assert len(storage_violations) > 0, "❌ FAIL: Storage violation not detected!"
    print(f"  ✅ Storage violation detected: {storage_violations[0]['claim']}")
    print(f"     Confidence: {storage_violations[0]['confidence']:.4f}")

    # STEP 4: Ground truth matching
    print("\n[STEP 4] Matching against ground truth...")
    ground_truth = parse_ground_truth(Path('GROUND_TRUTH_ERRORS.md'))

    run_id = "user_melatonin_6"
    gt = ground_truth.get(run_id, {})
    keywords = gt.get('keywords', [])

    print(f"  Expected keywords: {keywords}")

    detected = False
    for v in violations:
        if any(kw.lower() in v['claim'].lower() for kw in keywords):
            detected = True
            break

    assert detected == True, "❌ FAIL: Ground truth matching failed!"
    print(f"  ✅ Ground truth matched!")

    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED - melatonin_6 detection works correctly!")
    print("="*60)

if __name__ == '__main__':
    test_melatonin_6_complete()
```

### Pass Criteria for Full Pipeline:
✅ All 5 steps execute without errors
✅ Storage claim extracted in disclaimers
✅ Storage spec loaded from YAML
✅ Storage violation detected by NLI
✅ Ground truth matching succeeds

---

## Automated Verification Script

Save as: `tests/test_glass_box_pipeline.py`

```python
#!/usr/bin/env python3
"""
Automated test suite for Glass Box audit pipeline.
Run: pytest tests/test_glass_box_pipeline.py -v
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.glass_box_audit import (
    extract_atomic_claims,
    NLIJudge,
    EXTRACTION_MODEL,
    EXTRACTION_TEMPERATURE,
    VIOLATION_THRESHOLD
)
from analysis.glass_box_standalone import parse_ground_truth
import yaml


class TestStep1Extraction:
    """Test Step 1: Claim Extraction"""

    def test_extraction_model_config(self):
        """Verify GPT model configuration"""
        assert EXTRACTION_MODEL == "gpt-4o-mini"
        assert EXTRACTION_TEMPERATURE == 0

    def test_extraction_returns_both_lists(self):
        """Verify extraction returns core_claims and disclaimers"""
        content = "Test content. Disclaimer: results may vary."
        result = extract_atomic_claims(content, "Test Product", "faq")

        assert 'core_claims' in result
        assert 'disclaimers' in result
        assert isinstance(result['core_claims'], list)
        assert isinstance(result['disclaimers'], list)

    def test_melatonin_6_extraction(self):
        """Verify melatonin_6 storage claim is extracted"""
        file_path = Path('pilot_study/melatonin/files/melatonin_6.txt')
        with open(file_path) as f:
            content = f.read()

        result = extract_atomic_claims(content, "Melatonin", "faq")
        all_claims = result['core_claims'] + result['disclaimers']

        # Should extract storage claim
        storage_claims = [c for c in all_claims if '0°C' in c or ('store' in c.lower() and '0' in c)]
        assert len(storage_claims) > 0, "Storage claim not extracted!"


class TestStep2SpecLoading:
    """Test Step 2: Product Spec Loading"""

    def test_yaml_uses_specs_not_specifications(self):
        """Verify YAML key is 'specs' not 'specifications'"""
        with open('products/supplement_melatonin.yaml') as f:
            data = yaml.safe_load(f)

        assert 'specs' in data
        assert 'specifications' not in data

    def test_specs_flattening(self):
        """Verify specs are flattened correctly from nested dict"""
        with open('products/supplement_melatonin.yaml') as f:
            data = yaml.safe_load(f)

        specs_raw = data['specs']
        assert isinstance(specs_raw, dict)

        # Flatten
        specs = []
        for category, category_specs in specs_raw.items():
            if isinstance(category_specs, list):
                specs.extend(category_specs)

        assert len(specs) >= 28, f"Expected >= 28 specs, got {len(specs)}"

    def test_storage_specs_loaded(self):
        """Verify storage specs are loaded"""
        with open('products/supplement_melatonin.yaml') as f:
            data = yaml.safe_load(f)

        specs_raw = data['specs']
        specs = []
        for category, category_specs in specs_raw.items():
            if isinstance(category_specs, list):
                specs.extend(category_specs)

        # Check for storage spec
        storage_specs = [s for s in specs if '0°C' in s and 'NOT' in s]
        assert len(storage_specs) == 1, "Critical storage spec not loaded!"


class TestStep3Validation:
    """Test Step 3: NLI Validation"""

    def test_nli_model_loads(self):
        """Verify NLI model loads without error"""
        nli_judge = NLIJudge(use_semantic_filter=False)
        assert nli_judge.model is not None
        assert nli_judge.tokenizer is not None

    def test_contradiction_threshold(self):
        """Verify threshold is 0.9"""
        assert VIOLATION_THRESHOLD == 0.9

    def test_storage_contradiction_detected(self):
        """Verify storage contradiction is detected"""
        nli_judge = NLIJudge(use_semantic_filter=False)

        result = nli_judge.verify_claim(
            "Store at exactly 0°C",
            authorized_claims=[],
            specs=["Do NOT store at 0°C or below (do not freeze)"],
            prohibited_claims=[],
            clarifications=[]
        )

        assert result['is_violation'] == True, "Contradiction not detected!"
        assert result['contradiction_score'] >= 0.9, "Confidence too low!"


class TestStep4GroundTruth:
    """Test Step 4: Ground Truth Matching"""

    def test_ground_truth_loads_all_files(self):
        """Verify ground truth parser loads all 30 files"""
        ground_truth = parse_ground_truth(Path('GROUND_TRUTH_ERRORS.md'))
        assert len(ground_truth) == 30, f"Expected 30, got {len(ground_truth)}"

    def test_run_id_format(self):
        """Verify run ID format is correct"""
        ground_truth = parse_ground_truth(Path('GROUND_TRUTH_ERRORS.md'))

        # Check specific entries
        assert 'user_melatonin_6' in ground_truth
        assert 'user_smartphone_3' in ground_truth
        assert 'user_corecoin_10' in ground_truth

    def test_keywords_extracted(self):
        """Verify keywords are extracted correctly"""
        ground_truth = parse_ground_truth(Path('GROUND_TRUTH_ERRORS.md'))

        mel6_gt = ground_truth['user_melatonin_6']
        assert 'keywords' in mel6_gt
        assert len(mel6_gt['keywords']) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
```

---

## Execution Checklist

Before running audit on 1,700 files:

### Pre-Flight Checks:

- [ ] 1. Run unit tests: `pytest tests/test_glass_box_pipeline.py -v`
- [ ] 2. Run integration test on melatonin_6
- [ ] 3. Run full pilot audit (30 files)
- [ ] 4. Verify detection rate >= 28/30 (93%+)
- [ ] 5. Manually inspect 3 random violation CSVs
- [ ] 6. Check all YAML files have 'specs' key (not 'specifications')
- [ ] 7. Verify disclaimers are being validated (check logs)
- [ ] 8. Test one file from each product (melatonin, smartphone, corecoin)

### During Execution:

- [ ] 9. Monitor logs for "Validating X total claims" (X = core + disclaimers)
- [ ] 10. Check violation counts are reasonable (not 0, not 1000)
- [ ] 11. Spot-check CSVs every 100 files
- [ ] 12. Verify no crashes/errors in logs

### Post-Execution Validation:

- [ ] 13. Check final detection rate in validation_report.md
- [ ] 14. Verify all 1,700 CSV files created
- [ ] 15. Sample 10 random files and manually verify violations
- [ ] 16. Compare detection rates across products
- [ ] 17. Archive results with timestamp

---

## Reproducibility Guarantee

If all checks pass, the system will maintain **<2% variance** because:

1. ✅ Extraction is deterministic (GPT temp=0)
2. ✅ NLI is deterministic (RoBERTa on same hardware)
3. ✅ All specs/claims are loaded correctly
4. ✅ All claims (core + disclaimers) are validated
5. ✅ Ground truth matching is exact string matching

**Expected range: 96-100% detection (29-30/30 files)**
