"""Comprehensive error assessment for claim extraction and validation pipelines.

This script analyzes three datasets:
1. Glass Box Audit violations (final_audit_results.csv)
2. Golden dataset labels (deberta_gold_train.csv)
3. Claim extraction quality (all_claims_review.csv)
"""

import pandas as pd
import yaml
from pathlib import Path
from collections import Counter
import random

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
RESULTS_DIR = PROJECT_ROOT / "results"
PRODUCTS_DIR = PROJECT_ROOT / "products"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

# Input files
FINAL_AUDIT_CSV = RESULTS_DIR / "final_audit_results.csv"
GOLD_TRAIN_CSV = RESULTS_DIR / "deberta_gold_train.csv"
ALL_CLAIMS_CSV = RESULTS_DIR / "all_claims_review.csv"

# Output report
REPORT_PATH = RESULTS_DIR / "error_assessment_report.md"


def assess_glass_box_violations():
    """Assess Glass Box Audit violations for false positives."""
    print("\n" + "="*70)
    print("ASSESSMENT 1: GLASS BOX AUDIT VIOLATIONS")
    print("="*70)

    df = pd.read_csv(FINAL_AUDIT_CSV)

    # Filter only FAIL rows
    violations = df[df['Status'] == 'FAIL'].copy()

    print(f"\nTotal violations detected: {len(violations)}")
    print(f"Total runs audited: {len(df)}")
    print(f"Violation rate: {len(violations)/len(df)*100:.1f}%")

    # Analyze violation patterns
    print("\n" + "-"*70)
    print("VIOLATION PATTERNS")
    print("-"*70)

    # Most common violated rules
    violated_rules = violations['Violated_Rule'].value_counts()
    print(f"\nMost Frequently Violated Rules (Top 10):")
    for rule, count in violated_rules.head(10).items():
        print(f"  {count:3d}x | {rule[:70]}")

    # Most common extracted claims flagged
    flagged_claims = violations['Extracted_Claim'].value_counts()
    print(f"\nMost Common Claims Flagged as Violations (Top 10):")
    for claim, count in flagged_claims.head(10).items():
        print(f"  {count:3d}x | {claim[:70]}")

    # Confidence score analysis
    avg_confidence = violations['Confidence_Score'].astype(float).mean()
    min_confidence = violations['Confidence_Score'].astype(float).min()
    max_confidence = violations['Confidence_Score'].astype(float).max()

    print(f"\nConfidence Score Statistics:")
    print(f"  Average: {avg_confidence:.4f}")
    print(f"  Min: {min_confidence:.4f}")
    print(f"  Max: {max_confidence:.4f}")

    # ERROR ANALYSIS: Common patterns
    print("\n" + "-"*70)
    print("ERROR ANALYSIS")
    print("-"*70)

    # Pattern 1: Disclaimers contradicting marketing claims
    disclaimer_keywords = ['may vary', 'may decline', 'may degrade', 'depends on', 'speeds vary']
    disclaimer_violations = violations[
        violations['Extracted_Claim'].str.contains('|'.join(disclaimer_keywords), case=False, na=False)
    ]

    print(f"\n1. Disclaimer vs Marketing Claims:")
    print(f"   {len(disclaimer_violations)} violations ({len(disclaimer_violations)/len(violations)*100:.1f}%)")
    print(f"   Assessment: These are EXPECTED contradictions (disclaimers hedge absolute claims)")
    print(f"   Error Type: FALSE POSITIVE (functionally correct)")

    # Pattern 2: AI features contradicting "zero bloatware"
    ai_violations = violations[
        violations['Extracted_Claim'].str.contains('AI|cloud processing|internet connection', case=False, na=False) &
        violations['Violated_Rule'].str.contains('bloatware', case=False, na=False)
    ]

    print(f"\n2. AI Features vs 'Zero Bloatware' Claims:")
    print(f"   {len(ai_violations)} violations ({len(ai_violations)/len(violations)*100:.1f}%)")
    print(f"   Assessment: AI features requiring cloud != bloatware")
    print(f"   Error Type: FALSE POSITIVE (semantic misunderstanding)")

    # Pattern 3: Security approach contradicting "clean experience"
    security_violations = violations[
        violations['Extracted_Claim'].str.contains('security approach|multi-layer', case=False, na=False) &
        violations['Violated_Rule'].str.contains('bloatware|clean', case=False, na=False)
    ]

    print(f"\n3. Security Features vs 'Clean Experience':")
    print(f"   {len(security_violations)} violations ({len(security_violations)/len(violations)*100:.1f}%)")
    print(f"   Assessment: Security features != bloatware")
    print(f"   Error Type: FALSE POSITIVE (semantic misunderstanding)")

    # Pattern 4: Update guarantees with caveats
    update_violations = violations[
        (violations['Violated_Rule'].str.contains('7 years|seven years', case=False, na=False)) &
        (violations['Extracted_Claim'].str.contains('Not all|may vary', case=False, na=False))
    ]

    print(f"\n4. Update Guarantees with Limitations:")
    print(f"   {len(update_violations)} violations ({len(update_violations)/len(violations)*100:.1f}%)")
    print(f"   Assessment: Caveats about feature support != contradicting update promise")
    print(f"   Error Type: MIXED (some legitimate, some false positives)")

    # Sample violations for manual review
    print("\n" + "-"*70)
    print("SAMPLE VIOLATIONS FOR MANUAL REVIEW")
    print("-"*70)

    samples = violations.sample(min(5, len(violations)))
    for idx, row in samples.iterrows():
        print(f"\nSample {idx}:")
        print(f"  Violated Rule: {row['Violated_Rule']}")
        print(f"  Extracted Claim: {row['Extracted_Claim']}")
        print(f"  Confidence: {row['Confidence_Score']}")

    return violations


def assess_golden_dataset():
    """Assess golden dataset labeling quality."""
    print("\n\n" + "="*70)
    print("ASSESSMENT 2: GOLDEN DATASET LABELS")
    print("="*70)

    df = pd.read_csv(GOLD_TRAIN_CSV)

    print(f"\nTotal labeled samples: {len(df)}")

    # Label distribution
    label_counts = df['label'].value_counts().sort_index()
    label_names = {0: 'CONTRADICTION', 1: 'ENTAILMENT', 2: 'NEUTRAL'}

    print(f"\nLabel Distribution:")
    for label, count in label_counts.items():
        pct = (count / len(df)) * 100
        print(f"  {label} ({label_names.get(label, 'UNKNOWN')}): {count:3d} ({pct:.1f}%)")

    # Product distribution
    product_counts = df['product_id'].value_counts()
    print(f"\nProduct Distribution:")
    for product, count in product_counts.items():
        pct = (count / len(df)) * 100
        print(f"  {product}: {count:3d} ({pct:.1f}%)")

    # ERROR ANALYSIS
    print("\n" + "-"*70)
    print("ERROR ANALYSIS")
    print("-"*70)

    # Check for label imbalance
    if label_counts[2] > len(df) * 0.6:
        print(f"\n⚠️  WARNING: High NEUTRAL label rate ({label_counts[2]/len(df)*100:.1f}%)")
        print(f"   This may indicate:")
        print(f"   - LLM being overly conservative")
        print(f"   - Many vague marketing claims in sample")
        print(f"   - Possible labeling bias")

    if label_counts[0] < len(df) * 0.1:
        print(f"\n⚠️  WARNING: Low CONTRADICTION rate ({label_counts[0]/len(df)*100:.1f}%)")
        print(f"   This may indicate:")
        print(f"   - Marketing materials are highly compliant")
        print(f"   - LLM is too lenient on contradictions")
        print(f"   - Sample may not include problematic claims")

    # Sample contradictions for review
    print("\n" + "-"*70)
    print("SAMPLE CONTRADICTIONS (Label 0) FOR MANUAL REVIEW")
    print("-"*70)

    contradictions = df[df['label'] == 0]
    if len(contradictions) > 0:
        samples = contradictions.sample(min(5, len(contradictions)))
        for idx, row in samples.iterrows():
            print(f"\nSample {idx}:")
            print(f"  Product: {row['product_id']}")
            print(f"  Claim: {row['hypothesis_claim'][:100]}...")
            print(f"  Reasoning: {row['reasoning']}")

    # Sample entailments for review
    print("\n" + "-"*70)
    print("SAMPLE ENTAILMENTS (Label 1) FOR MANUAL REVIEW")
    print("-"*70)

    entailments = df[df['label'] == 1]
    if len(entailments) > 0:
        samples = entailments.sample(min(5, len(entailments)))
        for idx, row in samples.iterrows():
            print(f"\nSample {idx}:")
            print(f"  Product: {row['product_id']}")
            print(f"  Claim: {row['hypothesis_claim'][:100]}...")
            print(f"  Reasoning: {row['reasoning']}")

    return df


def assess_claim_extraction():
    """Assess claim extraction quality."""
    print("\n\n" + "="*70)
    print("ASSESSMENT 3: CLAIM EXTRACTION QUALITY")
    print("="*70)

    df = pd.read_csv(ALL_CLAIMS_CSV)

    print(f"\nTotal extracted claims: {len(df):,}")
    print(f"Total runs: {df['run_id'].nunique()}")
    print(f"Products: {df['product_id'].nunique()}")

    # Match type distribution
    match_counts = df['match_type'].value_counts()
    print(f"\nMatch Type Distribution:")
    for match_type, count in match_counts.items():
        pct = (count / len(df)) * 100
        print(f"  {match_type}: {count:4d} ({pct:.1f}%)")

    # Claims needing review
    needs_review = df[df['needs_review'] == True]
    print(f"\nClaims Needing Review: {len(needs_review):,} ({len(needs_review)/len(df)*100:.1f}%)")

    # Claim type distribution
    claim_type_counts = df['claim_type'].value_counts()
    print(f"\nClaim Type Distribution:")
    for claim_type, count in claim_type_counts.head(10).items():
        pct = (count / len(df)) * 100
        print(f"  {claim_type}: {count:4d} ({pct:.1f}%)")

    # ERROR ANALYSIS
    print("\n" + "-"*70)
    print("ERROR ANALYSIS")
    print("-"*70)

    # Pattern 1: High "no match" rate
    no_matches = df[df['match_type'] == 'none']
    print(f"\n1. No Match Rate:")
    print(f"   {len(no_matches):,} claims ({len(no_matches)/len(df)*100:.1f}%)")
    if len(no_matches) / len(df) > 0.8:
        print(f"   Assessment: Very high no-match rate")
        print(f"   Possible causes:")
        print(f"   - LLMs generating creative claims beyond YAML")
        print(f"   - YAML authorized_claims are too narrow")
        print(f"   - Matching algorithm needs tuning")

    # Pattern 2: Exact matches
    exact_matches = df[df['match_type'] == 'exact']
    print(f"\n2. Exact Match Rate:")
    print(f"   {len(exact_matches):,} claims ({len(exact_matches)/len(df)*100:.1f}%)")
    if len(exact_matches) / len(df) < 0.05:
        print(f"   Assessment: Very low exact match rate")
        print(f"   This is expected - LLMs paraphrase rather than copy")

    # Pattern 3: Partial matches
    partial_matches = df[df['match_type'] == 'partial']
    print(f"\n3. Partial Match Rate:")
    print(f"   {len(partial_matches):,} claims ({len(partial_matches)/len(df)*100:.1f}%)")
    print(f"   Average confidence: {partial_matches['match_confidence'].mean():.2f}")

    # Sample no-match claims for review
    print("\n" + "-"*70)
    print("SAMPLE NO-MATCH CLAIMS FOR MANUAL REVIEW")
    print("-"*70)

    if len(no_matches) > 0:
        samples = no_matches.sample(min(10, len(no_matches)))
        for idx, row in samples.iterrows():
            print(f"\nSample {idx}:")
            print(f"  Product: {row['product_id']}")
            print(f"  Type: {row['claim_type']}")
            print(f"  Claim: {row['extracted_claim'][:80]}")

    return df


def generate_markdown_report(violations_df, gold_df, claims_df):
    """Generate comprehensive markdown report."""
    report = []

    report.append("# Error Assessment Report")
    report.append(f"\nGenerated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("\n---\n")

    # Executive Summary
    report.append("## Executive Summary\n")
    report.append(f"- **Glass Box Audit**: {len(violations_df)} violations detected in {len(pd.read_csv(FINAL_AUDIT_CSV))} runs")
    report.append(f"- **Golden Dataset**: {len(gold_df)} labeled samples (Contradiction: {(gold_df['label']==0).sum()}, Entailment: {(gold_df['label']==1).sum()}, Neutral: {(gold_df['label']==2).sum()})")
    report.append(f"- **Claim Extraction**: {len(claims_df):,} claims extracted (No Match: {(claims_df['match_type']=='none').sum():,}, Partial: {(claims_df['match_type']=='partial').sum():,}, Exact: {(claims_df['match_type']=='exact').sum():,})")

    report.append("\n---\n")

    # Key Findings
    report.append("## Key Findings\n")
    report.append("### 1. Glass Box Audit Violations\n")
    report.append("**Major Issue**: High false positive rate due to disclaimers")
    report.append("- Disclaimers (e.g., 'may vary', 'depends on') are flagged as contradictions")
    report.append("- NLI model interprets hedging language as contradiction")
    report.append("- **Recommendation**: Separate disclaimer analysis from core claims\n")

    report.append("### 2. Golden Dataset Quality\n")
    if (gold_df['label'] == 2).sum() / len(gold_df) > 0.6:
        report.append(f"**Major Issue**: High NEUTRAL label rate ({(gold_df['label']==2).sum()/len(gold_df)*100:.1f}%)")
        report.append("- May indicate conservative LLM labeling")
        report.append("- **Recommendation**: Manual review of NEUTRAL samples\n")
    else:
        report.append("**Status**: Label distribution appears reasonable\n")

    report.append("### 3. Claim Extraction Quality\n")
    if (claims_df['match_type'] == 'none').sum() / len(claims_df) > 0.8:
        report.append(f"**Major Issue**: Very high no-match rate ({(claims_df['match_type']=='none').sum()/len(claims_df)*100:.1f}%)")
        report.append("- LLMs generating creative claims beyond YAML definitions")
        report.append("- **Recommendation**: Expand YAML authorized_claims or improve matching\n")

    report.append("\n---\n")

    # Detailed Statistics
    report.append("## Detailed Statistics\n")
    report.append("### Glass Box Audit\n")
    report.append(f"- Total runs audited: {len(pd.read_csv(FINAL_AUDIT_CSV))}")
    report.append(f"- Violations detected: {len(violations_df)}")
    report.append(f"- Average confidence: {violations_df['Confidence_Score'].astype(float).mean():.4f}")

    report.append("\n### Golden Dataset\n")
    for label in [0, 1, 2]:
        count = (gold_df['label'] == label).sum()
        report.append(f"- Label {label}: {count} ({count/len(gold_df)*100:.1f}%)")

    report.append("\n### Claim Extraction\n")
    for match_type in ['none', 'partial', 'exact']:
        count = (claims_df['match_type'] == match_type).sum()
        report.append(f"- {match_type.capitalize()}: {count:,} ({count/len(claims_df)*100:.1f}%)")

    # Write report
    with open(REPORT_PATH, 'w') as f:
        f.write('\n'.join(report))

    print(f"\n\n✓ Markdown report saved to: {REPORT_PATH}")


def main():
    """Run comprehensive error assessment."""
    print("="*70)
    print("COMPREHENSIVE ERROR ASSESSMENT")
    print("="*70)

    # Run assessments
    violations_df = assess_glass_box_violations()
    gold_df = assess_golden_dataset()
    claims_df = assess_claim_extraction()

    # Generate report
    generate_markdown_report(violations_df, gold_df, claims_df)

    print("\n" + "="*70)
    print("ASSESSMENT COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()
