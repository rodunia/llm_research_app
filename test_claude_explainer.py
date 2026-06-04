"""
Test Claude explainer on one pilot file
"""
import sys
from pathlib import Path
from analysis.glass_box_audit import NLIJudge, audit_single_run

# Test on melatonin_1 (has 5mg dosage error)
txt_file = Path('pilot_study/melatonin/files/melatonin_1.txt')
material_id = 'melatonin_1'
product_id = 'supplement_melatonin'

# Create run metadata
run_metadata = {
    'run_id': material_id,
    'product_id': product_id,
    'material_type': 'pilot_material',
    'output_path': str(txt_file),
    'use_claude_explainer': True  # Enable Claude
}

print("Initializing NLI Judge...")
judge = NLIJudge(use_semantic_filter=False)

print(f"\nAuditing {material_id} with Claude explanations...")
result = audit_single_run(material_id, run_metadata, judge)

print(f"\n{'='*80}")
print(f"Status: {result['status']}")
print(f"Violations: {result['violation_count']}")
print(f"{'='*80}\n")

# Show first 3 violations with Claude explanations
for i, violation in enumerate(result['violations'][:3], 1):
    print(f"VIOLATION {i}:")
    print(f"  Claim: {violation['claim']}")
    print(f"  Rule: {violation['violated_rule']}")
    print(f"  NLI Score: {violation['contradiction_score']:.3f}")
    print(f"  Claude Severity: {violation.get('severity_assessment', 'N/A')}")
    print(f"  Recommended Action: {violation.get('recommended_action', 'N/A')}")
    print(f"  Explanation: {violation.get('claude_explanation', 'N/A')}")
    print()
