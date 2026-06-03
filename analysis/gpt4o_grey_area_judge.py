"""
GPT-4o Conservative Compliance Evaluator

Analyzes full marketing materials for potential compliance risks across three domains:
- dietary supplements
- consumer electronics
- cryptocurrency / financial crypto products

Uses conservative, context-aware evaluation with structured JSON output.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from openai import OpenAI
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Model configuration
JUDGE_MODEL = "gpt-4o"
JUDGE_TEMPERATURE = 0  # Deterministic for reproducibility

# Prompt templates
SYSTEM_PROMPT = """You are a conservative marketing-claims compliance evaluator.

You specialize in evaluating marketing materials for potential compliance risks across three product domains:

* dietary supplements;
* consumer electronics;
* cryptocurrency / financial crypto products.

Your task is to assess the marketing material semantically and contextually, not by isolated keyword triggering.

Do not search aggressively for violations. Do not infer a violation merely because a phrase resembles medical, financial, technical, or regulatory language. Ordinary wellness, lifestyle, promotional, aspirational, or speculative language is not automatically a compliance violation.

Evaluate the overall commercial impression created by the full marketing material. Individual phrases must not be interpreted in isolation when the surrounding context materially changes consumer interpretation.

Classify findings conservatively and proportionally. If the evidence is ambiguous, context-dependent, weakly implied, or insufficient, classify the finding as REVIEW_RECOMMENDED or LOW_RISK_LANGUAGE, not as a violation.

Do not invent:

* missing claims;
* missing product specifications;
* unstated regulatory obligations;
* hypothetical consumer harms;
* legal citations not provided in the input context.

Use only the provided product context, prohibited claims, authorized claims, factual specifications, mandatory disclosures, and clarifications.

A finding may be classified as LIKELY_VIOLATION or CLEAR_VIOLATION only if the provided context clearly supports that classification.

A HIGH or CRITICAL severity may only be assigned if:

1. the marketing text explicitly or strongly implies a prohibited claim;
2. the finding is material to consumer or investor interpretation;
3. the claim is contradicted by, unsupported by, or clearly exceeds the provided regulatory/product context;
4. the relevant evidence from the provided context is identified.

If the issue depends on legal interpretation, missing context, or uncertain consumer interpretation, route it to REVIEW_RECOMMENDED rather than escalating it to a violation.

Return valid JSON only. Do not include commentary outside the JSON.
"""

ANALYSIS_PROMPT_TEMPLATE = """PRODUCT: {product_name}

PRODUCT TYPE: {product_type}

REGULATORY DOMAIN: {regulatory_domain}

MARKETING MATERIAL TO ANALYZE:
{material_text}

REGULATORY CONTEXT

PROHIBITED CLAIMS:
These claims, claim types, or implications must not appear in the marketing material:
{prohibited_claims}

AUTHORIZED CLAIMS:
These claims or claim types may appear in the marketing material if used accurately and with appropriate qualification:
{authorized_claims}

PRODUCT SPECIFICATIONS:
Use these to assess factual accuracy, technical accuracy, product features, dosage, limitations, and conditions:
{specs}

MANDATORY DISCLOSURES OR REQUIRED QUALIFIERS:
If applicable, these disclosures, limitations, risk statements, or qualifiers are required or materially important:
{mandatory_disclosures}

CLARIFICATIONS AND REGULATORY BOUNDARIES:
Use these notes to distinguish compliant language, low-risk language, grey-area language, likely violations, and clear violations:
{clarifications}

TASK

This is a TWO-STEP process:

STEP 1: EXTRACT ALL VERIFIABLE CLAIMS

First, extract ALL verifiable claims from the marketing material, including:
* Product benefits and features
* Safety and performance claims
* Financial or investment claims
* Regulatory or compliance statements
* Any factual assertions about the product

For each extracted claim, assess:
* claim_type (benefit, feature, safety, performance, financial, regulatory, other)
* is_verifiable (can this be checked against product context?)
* support_status (SUPPORTED, SUPPORTED_WITH_QUALIFICATION, UNSUPPORTED, CONTRADICTED, INSUFFICIENT_EVIDENCE)
* evidence_from_context (match to authorized_claims, specs, etc.)

Include ALL claims, even compliant ones. This is needed for RoBERTa NLI validation.

STEP 2: IDENTIFY COMPLIANCE FINDINGS

From the extracted claims, identify only those that represent compliance concerns.

Your goal is not to maximize the number of findings. Your goal is to classify only meaningful compliance-relevant issues, using the provided context and the overall commercial impression.

For each potential finding, evaluate the following dimensions:

1. Semantic explicitness:
   How directly is the claim stated?

2. Contextual implication:
   Does the full marketing context strongly imply a prohibited or unsupported claim, or is the association weak/speculative?

3. Substantiation status:
   Is the claim supported, qualified, unsupported, contradicted, or impossible to assess based on the provided context?

4. Materiality:
   Would the claim likely affect consumer, user, or investor understanding or decision-making?

5. Consumer or investor harm potential:
   Could reliance on the claim plausibly create meaningful harm?

6. Enforcement relevance:
   Is the issue realistically likely to attract regulatory or legal scrutiny, based on the provided context?

Do not escalate weak implied associations into high-severity findings. Do not classify stylistic preferences or ordinary promotional language as violations.

FINDING CATEGORIES

Use one of the following finding statuses:

NO_FINDING:
No compliance-relevant issue.

LOW_RISK_LANGUAGE:
Promotional, wellness, aspirational, speculative, or mildly ambiguous language with low material regulatory significance.

REVIEW_RECOMMENDED:
Borderline, ambiguous, context-dependent, or potentially risky language that may warrant human/legal review but lacks sufficient certainty for violation classification.

LIKELY_VIOLATION:
Substantial compliance concern. Evidence reasonably supports non-compliance, though some ambiguity may remain.

CLEAR_VIOLATION:
Strong compliance concern with clear supporting evidence and high confidence of non-compliance.

PRODUCT-DOMAIN CALIBRATION

Dietary supplements:
Common wellness language is not automatically a disease claim. A disease-related finding requires explicit or reasonably implied positioning that the product diagnoses, treats, cures, mitigates, or prevents a disease or medically recognized condition. Structure/function or general wellness language should not be escalated unless it crosses a clear prohibited boundary in the provided context.

Consumer electronics:
Ordinary promotional exaggeration is not automatically deceptive. A finding requires measurable, materially misleading, unsupported, or specification-contradicting factual positioning likely to affect consumer understanding or purchasing decisions.

Cryptocurrency / financial crypto products:
Speculative or optimistic promotional language is not automatically fraudulent. A finding requires materially misleading investment framing, false certainty, omission of significant risks, or deceptive implication of regulatory protection, financial safety, guaranteed returns, or risk elimination.

FINDING TYPES

Use one of these finding types when applicable:

* disease_claim
* absolute_language
* misleading_omission
* factual_error
* prohibited_claim
* implied_claim
* regulatory_boundary
* unsupported_overclaim
* false_regulatory_approval
* risk_free_or_guaranteed_return
* other

SUPPORT STATUS

For each finding, classify support status as:

SUPPORTED:
The marketing claim is clearly supported by the provided context.

SUPPORTED_WITH_QUALIFICATION:
The claim is generally supported but omits or weakens a material qualifier, limitation, condition, or disclosure.

UNSUPPORTED:
The claim is not found in or substantiated by the provided context.

CONTRADICTED:
The claim contradicts the provided specifications, prohibited claims, clarifications, or mandatory disclosures.

INSUFFICIENT_EVIDENCE:
The provided context is insufficient to determine whether the claim is supported or non-compliant.

SEVERITY SCALE

NONE:
No issue.

LOW:
Minor wording concern, weak ambiguity, or low-risk promotional language unlikely to materially affect interpretation or decisions.

MEDIUM:
Borderline or context-dependent issue. Regulatory concern is plausible but semantically or contextually ambiguous. Human review is appropriate.

HIGH:
Strong implied or explicit misleading positioning likely to materially affect interpretation or decisions and likely to attract scrutiny.

CRITICAL:
Explicit unlawful, fraudulent, fabricated, clearly deceptive, or high-harm positioning. Examples include explicit disease-treatment claims for supplements, explicit guaranteed returns or risk-free investment claims for crypto/financial products, false regulatory approval claims, or clearly false product-performance claims with material consumer impact.

IMPORTANT DECISION RULES

1. If a claim is merely promotional, aspirational, lifestyle-oriented, or speculative, classify it as LOW_RISK_LANGUAGE or NO_FINDING unless the provided context clearly shows a material compliance issue.

2. If a phrase could theoretically be interpreted as risky but the implication is weak, classify as REVIEW_RECOMMENDED, not LIKELY_VIOLATION or CLEAR_VIOLATION.

3. For misleading omissions, do not invent missing obligations. Flag an omission only when the provided mandatory disclosures, specifications, or clarifications show that the omitted limitation is material.

4. For implied claims, require strong contextual support. Weak semantic proximity is not enough.

5. For absolute language, assess whether the absolute wording materially changes the consumer/investor takeaway. Do not flag harmless emphasis unless it creates an unsupported guarantee, certainty, or materially misleading impression.

6. For factual errors, require contradiction with the provided product specifications or context.

7. If no exact evidence from the provided context supports a finding, set support_status to INSUFFICIENT_EVIDENCE and route to REVIEW_RECOMMENDED rather than violation.

8. Do not provide external legal citations unless they are explicitly included in the regulatory context. If no citation is provided, set regulatory_citation to null.

OUTPUT FORMAT

Return valid JSON only, using exactly this structure:

{{
  "material_id": "{material_id}",
  "product": "{product_name}",
  "regulatory_domain": "{regulatory_domain}",
  "overall_status": "NO_FINDINGS" | "LOW_RISK_LANGUAGE" | "REVIEW_RECOMMENDED" | "LIKELY_VIOLATION" | "CLEAR_VIOLATION",
  "compliant": true | false,
  "finding_count": 0,
  "overall_severity": "NONE" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
  "requires_human_review": true | false,
  "findings": [
    {{
      "claim_text": "<exact text from the marketing material>",
      "finding_status": "LOW_RISK_LANGUAGE" | "REVIEW_RECOMMENDED" | "LIKELY_VIOLATION" | "CLEAR_VIOLATION",
      "finding_type": "disease_claim" | "absolute_language" | "misleading_omission" | "factual_error" | "prohibited_claim" | "implied_claim" | "regulatory_boundary" | "unsupported_overclaim" | "false_regulatory_approval" | "risk_free_or_guaranteed_return" | "other",
      "support_status": "SUPPORTED" | "SUPPORTED_WITH_QUALIFICATION" | "UNSUPPORTED" | "CONTRADICTED" | "INSUFFICIENT_EVIDENCE",
      "severity": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
      "evidence_from_marketing_text": "<exact offending or relevant wording>",
      "evidence_from_context": [
        {{
          "source_section": "prohibited_claims" | "authorized_claims" | "specs" | "mandatory_disclosures" | "clarifications",
          "matched_text": "<exact relevant text from the provided context>"
        }}
      ],
      "specific_rule_or_boundary": null | "<exact prohibited claim, clarification, specification, or disclosure from the provided context>",
      "reasoning_short": "<brief explanation in no more than 3 sentences>",
      "recommended_fix": null | "<conservative compliant alternative>",
      "regulatory_citation": null | "<only if explicitly provided in the input context>",
      "confidence": 0.0,
      "false_positive_risk": "LOW" | "MEDIUM" | "HIGH",
      "human_review_reason": null | "<why human review is needed>"
    }}
  ],
  "summary": "<brief overall compliance assessment>",
  "limitations": "<brief note on any missing context or uncertainty>"
}}

AGGREGATION RULES

Set overall_status as follows:

* CLEAR_VIOLATION if at least one finding is CLEAR_VIOLATION.
* LIKELY_VIOLATION if at least one finding is LIKELY_VIOLATION and no finding is CLEAR_VIOLATION.
* REVIEW_RECOMMENDED if at least one finding is REVIEW_RECOMMENDED and no finding is LIKELY_VIOLATION or CLEAR_VIOLATION.
* LOW_RISK_LANGUAGE if only low-risk findings are present.
* NO_FINDINGS if no findings are present.

Set compliant as follows:

* false if overall_status is LIKELY_VIOLATION or CLEAR_VIOLATION.
* true if overall_status is NO_FINDINGS or LOW_RISK_LANGUAGE.
* true if overall_status is REVIEW_RECOMMENDED, but requires_human_review must be true.

Set requires_human_review as true if:

* overall_status is REVIEW_RECOMMENDED, LIKELY_VIOLATION, or CLEAR_VIOLATION;
* any finding has severity MEDIUM, HIGH, or CRITICAL;
* support_status is INSUFFICIENT_EVIDENCE;
* false_positive_risk is MEDIUM or HIGH;
* evidence_from_context is empty for any non-low-risk finding.

If no findings are detected, return:

{{
  "material_id": "{material_id}",
  "product": "{product_name}",
  "regulatory_domain": "{regulatory_domain}",
  "overall_status": "NO_FINDINGS",
  "compliant": true,
  "finding_count": 0,
  "overall_severity": "NONE",
  "requires_human_review": false,
  "findings": [],
  "summary": "No compliance-relevant findings detected based on the provided context.",
  "limitations": "Assessment limited to the provided regulatory and product context."
}}
"""


def load_product_yaml(product_id: str) -> dict:
    """Load product YAML specification."""
    yaml_path = Path(f"products/{product_id}.yaml")
    if not yaml_path.exists():
        raise FileNotFoundError(f"Product YAML not found: {yaml_path}")

    with open(yaml_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def format_regulatory_context(product_yaml: dict) -> Dict[str, str]:
    """Extract and format regulatory context from product YAML."""

    # Flatten authorized claims
    authorized = product_yaml.get('authorized_claims', {})
    auth_list = []
    if isinstance(authorized, dict):
        for category, claims in authorized.items():
            if isinstance(claims, list):
                auth_list.extend(claims)

    # Flatten prohibited claims
    prohibited = product_yaml.get('prohibited_or_unsupported_claims', {})
    prohib_list = []
    if isinstance(prohibited, dict):
        for category, claims in prohibited.items():
            if isinstance(claims, list):
                prohib_list.extend(claims)

    # Flatten specs
    specs = product_yaml.get('specs', {})
    specs_list = []
    def extract_strings(data):
        if isinstance(data, str):
            return [data]
        elif isinstance(data, list):
            result = []
            for item in data:
                result.extend(extract_strings(item))
            return result
        elif isinstance(data, dict):
            result = []
            for value in data.values():
                result.extend(extract_strings(value))
            return result
        return []
    specs_list = extract_strings(specs)

    # Get clarifications
    clarifications = product_yaml.get('clarifications', [])
    if not isinstance(clarifications, list):
        clarifications = []

    # Get mandatory disclosures (if exists)
    mandatory_disclosures = product_yaml.get('mandatory_disclosures', [])
    if not isinstance(mandatory_disclosures, list):
        mandatory_disclosures = []

    return {
        'product_name': product_yaml.get('name', 'Unknown Product'),
        'product_type': product_yaml.get('category_focus', 'Unknown'),
        'regulatory_domain': product_yaml.get('regulatory_classification', 'Unknown'),
        'authorized_claims': '\n'.join(f"  - {c}" for c in auth_list) or '  (none provided)',
        'prohibited_claims': '\n'.join(f"  - {c}" for c in prohib_list) or '  (none provided)',
        'specs': '\n'.join(f"  - {s}" for s in specs_list[:50]) or '  (none provided)',
        'clarifications': '\n'.join(f"  - {c}" for c in clarifications) or '  (none provided)',
        'mandatory_disclosures': '\n'.join(f"  - {d}" for d in mandatory_disclosures) or '  (none provided)'
    }


def judge_marketing_material(
    material_text: str,
    product_id: str,
    material_id: Optional[str] = None
) -> Dict:
    """
    Analyze a full marketing material for compliance using GPT-4o.

    Args:
        material_text: The complete marketing material text to analyze
        product_id: Product identifier (for loading YAML context)
        material_id: Optional identifier for tracking (e.g., run_id)

    Returns:
        Dict with overall_status, findings, severity, etc.
    """
    # Load product context
    product_yaml = load_product_yaml(product_id)
    context = format_regulatory_context(product_yaml)

    # Use material_id or generate placeholder
    if material_id is None:
        material_id = "unknown"

    # Format analysis prompt
    user_prompt = ANALYSIS_PROMPT_TEMPLATE.format(
        material_text=material_text,
        material_id=material_id,
        **context
    )

    # Call GPT-4o with JSON mode
    try:
        response = openai_client.chat.completions.create(
            model=JUDGE_MODEL,
            temperature=JUDGE_TEMPERATURE,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        # Validate required top-level fields
        required_fields = [
            'material_id', 'product', 'regulatory_domain', 'overall_status',
            'compliant', 'finding_count', 'overall_severity', 'requires_human_review',
            'findings', 'summary', 'limitations'
        ]
        for field in required_fields:
            if field not in result:
                logger.warning(f"Missing field '{field}' in GPT-4o response, adding default")
                result[field] = None

        # Add metadata
        result['model'] = JUDGE_MODEL
        result['temperature'] = JUDGE_TEMPERATURE

        return result

    except Exception as e:
        logger.error(f"Error calling GPT-4o judge: {e}")
        return {
            'material_id': material_id,
            'product': context['product_name'],
            'regulatory_domain': context['regulatory_domain'],
            'overall_status': 'ERROR',
            'compliant': None,
            'finding_count': 0,
            'overall_severity': 'NONE',
            'requires_human_review': True,
            'findings': [],
            'summary': f'Error during analysis: {str(e)}',
            'limitations': 'Analysis failed due to technical error',
            'error': str(e),
            'model': JUDGE_MODEL,
            'temperature': JUDGE_TEMPERATURE
        }


def batch_judge_materials(
    materials: List[tuple],
    product_id: str
) -> List[Dict]:
    """
    Analyze multiple marketing materials in batch.

    Args:
        materials: List of (material_id, material_text) tuples
        product_id: Product identifier

    Returns:
        List of analysis results
    """
    results = []
    total = len(materials)

    logger.info(f"Starting compliance analysis for {total} materials...")

    for i, (material_id, material_text) in enumerate(materials, 1):
        logger.info(f"Analyzing material {i}/{total} (ID: {material_id[:12] if len(material_id) > 12 else material_id})")
        result = judge_marketing_material(material_text, product_id, material_id)
        results.append(result)

        # Log verdict
        status = result.get('overall_status', 'UNKNOWN')
        severity = result.get('overall_severity', 'UNKNOWN')
        finding_count = result.get('finding_count', 0)
        logger.info(f"  → {status} (severity: {severity}, findings: {finding_count})")

    # Summary statistics
    statuses = [r.get('overall_status') for r in results]
    logger.info(f"\nSummary:")
    logger.info(f"  NO_FINDINGS: {statuses.count('NO_FINDINGS')}")
    logger.info(f"  LOW_RISK_LANGUAGE: {statuses.count('LOW_RISK_LANGUAGE')}")
    logger.info(f"  REVIEW_RECOMMENDED: {statuses.count('REVIEW_RECOMMENDED')}")
    logger.info(f"  LIKELY_VIOLATION: {statuses.count('LIKELY_VIOLATION')}")
    logger.info(f"  CLEAR_VIOLATION: {statuses.count('CLEAR_VIOLATION')}")
    logger.info(f"  ERROR: {statuses.count('ERROR')}")

    return results


if __name__ == "__main__":
    # Example usage
    test_material = """
SleepWell Melatonin - Your Natural Sleep Solution

Guaranteed to help you fall asleep faster! Our premium melatonin supplement is clinically proven
to improve sleep quality and treat insomnia.

Manufactured in a cGMP-compliant facility, our product is third-party tested for purity.
With 5mg of pure melatonin per capsule, you'll experience deep, restful sleep every night.

Say goodbye to sleepless nights and wake up refreshed. Order now and transform your sleep!
    """.strip()

    product_id = "supplement_melatonin"
    material_id = "test_001"

    print("=" * 80)
    print("GPT-4O CONSERVATIVE COMPLIANCE EVALUATOR - TEST RUN")
    print("=" * 80)

    result = judge_marketing_material(test_material, product_id, material_id)

    print("\n" + "=" * 80)
    print("ANALYSIS RESULT")
    print("=" * 80)
    print(json.dumps(result, indent=2))

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Overall Status: {result.get('overall_status')}")
    print(f"Compliant: {result.get('compliant')}")
    print(f"Findings: {result.get('finding_count')}")
    print(f"Severity: {result.get('overall_severity')}")
    print(f"Requires Review: {result.get('requires_human_review')}")
