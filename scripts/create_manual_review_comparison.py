#!/usr/bin/env python3
"""
Create side-by-side comparison for manual review of Glass Box vs GPT-4o Freeform
Outputs markdown file with all violations for each method for easy comparison
"""

import csv
import json
from pathlib import Path

# Files to review (sample from each category)
REVIEW_FILES = [
    # Perfect detection (both methods)
    'errors_smartphone_1',
    'errors_melatonin_1',
    'errors_corecoin_1',

    # Both missed
    'errors_corecoin_2',
    'errors_corecoin_9',

    # Potential differences
    'errors_smartphone_5',  # Parsing bug file
    'errors_melatonin_6',   # Storage temp 0°C
    'errors_melatonin_7',   # Every 2 hours dosing
]

# Ground truth errors
GROUND_TRUTH = {
    'errors_smartphone_1': 'Display size 6.5" instead of 6.3"',
    'errors_melatonin_1': 'Dosage 5 mg instead of 3 mg',
    'errors_corecoin_1': 'Block time ~4 seconds instead of ~5 seconds',
    'errors_corecoin_2': 'Light validators don\'t stake (they must)',
    'errors_corecoin_9': 'Validator inactivity locks governance rights',
    'errors_smartphone_5': 'Wi-Fi 7 (only has Wi-Fi 6/6E)',
    'errors_melatonin_6': 'Storage temp 0°C (correct is 15-30°C)',
    'errors_melatonin_7': 'Every 2 hours instead of before bed',
}

def load_glass_box_results(file_id):
    """Load Glass Box CSV results for a file"""
    csv_path = Path(f'results/errors_analysis/glass_box/{file_id}.csv')
    if not csv_path.exists():
        return []

    violations = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            violations.append({
                'claim': row['Extracted_Claim'],
                'rule': row['Violated_Rule'],
                'confidence': float(row['Confidence_Score'])
            })
    return violations

def load_gpt4o_results(file_id):
    """Load GPT-4o freeform text results for a file"""
    txt_path = Path(f'results/errors_analysis/gpt4o_freeform/{file_id}.txt')
    if not txt_path.exists():
        return ""

    with open(txt_path, 'r') as f:
        return f.read()

def create_comparison_markdown():
    """Create markdown file with side-by-side comparison"""

    md_lines = [
        "# Manual Review: Glass Box vs GPT-4o Freeform",
        "",
        "**Purpose**: Manual comparison to determine which method catches errors better",
        "",
        "**Date**: 2026-03-07",
        "",
        "---",
        ""
    ]

    for file_id in REVIEW_FILES:
        ground_truth = GROUND_TRUTH.get(file_id, "Unknown")

        md_lines.extend([
            f"## {file_id}",
            "",
            f"**Ground Truth Error**: {ground_truth}",
            "",
            "### Glass Box Results",
            ""
        ])

        # Glass Box violations
        glass_box_violations = load_glass_box_results(file_id)

        if glass_box_violations:
            md_lines.append(f"**Total violations flagged**: {len(glass_box_violations)}")
            md_lines.append("")
            md_lines.append("| Extracted Claim | Violated Rule | Confidence |")
            md_lines.append("|-----------------|---------------|------------|")

            # Sort by confidence descending
            for v in sorted(glass_box_violations, key=lambda x: x['confidence'], reverse=True)[:10]:
                claim = v['claim'][:80] + '...' if len(v['claim']) > 80 else v['claim']
                rule = v['rule'][:60] + '...' if len(v['rule']) > 60 else v['rule']
                md_lines.append(f"| {claim} | {rule} | {v['confidence']:.3f} |")

            if len(glass_box_violations) > 10:
                md_lines.append(f"| ... ({len(glass_box_violations) - 10} more violations) | | |")
        else:
            md_lines.append("**No violations found**")

        md_lines.extend(["", "### GPT-4o Freeform Results", ""])

        # GPT-4o text
        gpt4o_text = load_gpt4o_results(file_id)

        if gpt4o_text:
            # Count errors (numbered items)
            error_count = sum(1 for line in gpt4o_text.split('\n')
                            if line.strip().startswith(tuple(f'{i}.' for i in range(1, 11))))

            md_lines.append(f"**Errors found**: {error_count}")
            md_lines.append("")
            md_lines.append("```")
            # Show first 30 lines
            all_lines = gpt4o_text.split('\n')
            lines = all_lines[:30]
            md_lines.extend(lines)
            if len(all_lines) > 30:
                remaining = len(all_lines) - 30
                md_lines.append(f"... ({remaining} more lines)")
            md_lines.append("```")
        else:
            md_lines.append("**No response available**")

        md_lines.extend([
            "",
            "### Manual Assessment",
            "",
            "- [ ] Did Glass Box catch the ground truth error?",
            "- [ ] Did GPT-4o catch the ground truth error?",
            "- [ ] Which method has fewer false positives?",
            "- [ ] Which method provides better explanations?",
            "- [ ] Overall winner for this file: ___________",
            "",
            "**Notes**:",
            "",
            "",
            "---",
            ""
        ])

    # Add summary section
    md_lines.extend([
        "## Summary Scores",
        "",
        "### Ground Truth Detection",
        "",
        "| File | Glass Box | GPT-4o | Winner |",
        "|------|-----------|--------|--------|"
    ])

    for file_id in REVIEW_FILES:
        md_lines.append(f"| {file_id} | [ ] | [ ] | |")

    md_lines.extend([
        "",
        "### Quality Assessment",
        "",
        "| Metric | Glass Box | GPT-4o | Winner |",
        "|--------|-----------|--------|--------|",
        "| False Positive Rate | | | |",
        "| Explanation Quality | N/A | | GPT-4o |",
        "| Actionability | | | |",
        "| Confidence Scores | Yes (numeric) | No (text) | Glass Box |",
        "",
        "### Final Decision",
        "",
        "**Recommended method**: ___________",
        "",
        "**Justification**:",
        "",
        "",
        "**Use cases**:",
        "- Glass Box better for: ___________",
        "- GPT-4o better for: ___________",
        ""
    ])

    # Write to file
    output_path = Path('results/errors_analysis/MANUAL_REVIEW_COMPARISON.md')
    with open(output_path, 'w') as f:
        f.write('\n'.join(md_lines))

    print(f'✓ Created manual review document: {output_path}')
    print(f'\nReview {len(REVIEW_FILES)} files to compare:')
    for file_id in REVIEW_FILES:
        print(f'  - {file_id}: {GROUND_TRUTH.get(file_id, "Unknown")}')
    print(f'\nOpen the file and fill in the manual assessment sections!')

if __name__ == '__main__':
    create_comparison_markdown()
