"""
GPT-4o Grey Area Compliance Judge

Analyzes extracted claims for subtle regulatory violations that NLI models miss.
Uses GPT-4o at temperature=0 with structured JSON output for reproducibility.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List
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
SYSTEM_PROMPT = """You are an expert regulatory compliance analyst specializing in:
- FDA regulations for dietary supplements (DSHEA, 21 CFR Part 111)
- FTC guidelines for consumer electronics advertising
- SEC/CFTC regulations for cryptocurrency disclosures

Your task is to identify SUBTLE regulatory violations that automated systems miss. Focus on:
1. **Implied claims** (suggesting benefits without explicit statement)
2. **Absolute language** ("guaranteed", "always", "never" without hedging)
3. **Disease claims** disguised as structure/function claims
4. **Misleading omissions** (highlighting positives, hiding limitations)
5. **Regulatory boundary violations** (crossing from allowed → prohibited)

Be STRICT but FAIR. Only flag genuine compliance risks, not minor wording preferences.
"""

ANALYSIS_PROMPT_TEMPLATE = """
PRODUCT: {product_name}
PRODUCT TYPE: {product_type}
REGULATORY DOMAIN: {regulatory_domain}

CLAIM TO ANALYZE:
"{claim}"

REGULATORY CONTEXT:

PROHIBITED CLAIMS (Marketing MUST NOT make these claims):
{prohibited_claims}

AUTHORIZED CLAIMS (Marketing CAN make these claims):
{authorized_claims}

FACTUAL SPECIFICATIONS:
{specs}

CLARIFICATIONS (Regulatory boundaries):
{clarifications}

---

ANALYSIS INSTRUCTIONS:

Evaluate whether this claim violates regulations by considering:

1. **Absoluteness Check**: Does it use absolute language without hedging?
   - Prohibited: "guaranteed", "always works", "100% effective", "eliminates"
   - Allowed: "may help", "supports", "designed to", "can help reduce"

2. **Disease Claim Check**: Does it treat, cure, prevent disease?
   - Prohibited: "treats insomnia", "cures sleep disorders", "prevents jet lag"
   - Allowed: "supports healthy sleep patterns", "helps reduce time to fall asleep"

3. **Implication Check**: Does it subtly imply prohibited claims?
   - Example: "cGMP facility" implying FDA drug approval (prohibited implication)
   - Example: "third-party tested" implying medical efficacy (grey area)

4. **Omission Check**: Does it hide critical limitations?
   - Example: "Fast charging" without mentioning "adapter sold separately"
   - Example: "Secure blockchain" without mentioning "no customer support for lost keys"

5. **Regulatory Boundary**: Does it cross from structure/function → disease claim?
   - Allowed: "supports body's natural sleep-wake cycle"
   - Prohibited: "regulates your circadian rhythm" (implies physiological modification)

6. **Contextual Appropriateness**: Is the claim appropriate for this product type?
   - Supplements: Can't claim drug-like effects
   - Electronics: Can't claim features not present
   - Crypto: Must disclose risks, can't guarantee returns

---

OUTPUT FORMAT (JSON):

{{
  "claim": "<exact claim text>",
  "verdict": "COMPLIANT" | "GREY_AREA" | "VIOLATION",
  "severity": "NONE" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
  "violation_type": null | "absolute_language" | "disease_claim" | "implied_claim" | "misleading_omission" | "regulatory_boundary" | "factual_error",
  "reasoning": "<detailed explanation>",
  "specific_rule_violated": null | "<exact prohibited claim matched>",
  "recommended_fix": null | "<suggested compliant alternative>",
  "confidence": 0.0-1.0
}}

VERDICT DEFINITIONS:
- COMPLIANT: Clearly within regulations, no issues
- GREY_AREA: Technically legal but risky, could be misinterpreted, needs human review
- VIOLATION: Clear regulatory violation, must be corrected

SEVERITY SCALE:
- NONE: No issue (verdict=COMPLIANT)
- LOW: Minor grey area, unlikely enforcement risk (e.g., could add more hedging)
- MEDIUM: Moderate risk, regulators might question (e.g., borderline disease claim)
- HIGH: Likely violation, enforcement risk (e.g., absolute guarantee without substantiation)
- CRITICAL: Serious violation, immediate legal risk (e.g., unapproved drug claim)

Be thorough. Provide specific reasoning with regulatory citations when possible.
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

    return {
        'product_name': product_yaml.get('name', 'Unknown Product'),
        'product_type': product_yaml.get('category_focus', 'Unknown'),
        'regulatory_domain': product_yaml.get('regulatory_classification', 'Unknown'),
        'authorized_claims': '\n'.join(f"  - {c}" for c in auth_list[:20]),  # Limit to 20 for token efficiency
        'prohibited_claims': '\n'.join(f"  - {c}" for c in prohib_list[:20]),
        'specs': '\n'.join(f"  - {s}" for s in specs_list[:30]),
        'clarifications': '\n'.join(f"  - {c}" for c in clarifications[:20])
    }


def judge_claim_grey_area(claim: str, product_id: str) -> Dict:
    """
    Analyze a single claim for grey area regulatory violations using GPT-4o.

    Args:
        claim: The extracted claim text to analyze
        product_id: Product identifier (for loading YAML context)

    Returns:
        Dict with verdict, severity, reasoning, etc.
    """
    # Load product context
    product_yaml = load_product_yaml(product_id)
    context = format_regulatory_context(product_yaml)

    # Format analysis prompt
    user_prompt = ANALYSIS_PROMPT_TEMPLATE.format(
        claim=claim,
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

        # Validate required fields
        required_fields = ['claim', 'verdict', 'severity', 'reasoning', 'confidence']
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
            'claim': claim,
            'verdict': 'ERROR',
            'severity': 'NONE',
            'reasoning': f'Error during analysis: {str(e)}',
            'confidence': 0.0,
            'error': str(e)
        }


def batch_judge_claims(claims: List[str], product_id: str) -> List[Dict]:
    """
    Analyze multiple claims in batch.

    Args:
        claims: List of claim texts
        product_id: Product identifier

    Returns:
        List of analysis results
    """
    results = []
    total = len(claims)

    logger.info(f"Starting grey area analysis for {total} claims...")

    for i, claim in enumerate(claims, 1):
        logger.info(f"Analyzing claim {i}/{total}")
        result = judge_claim_grey_area(claim, product_id)
        results.append(result)

        # Log verdict
        verdict = result.get('verdict', 'UNKNOWN')
        severity = result.get('severity', 'UNKNOWN')
        logger.info(f"  → {verdict} (severity: {severity})")

    # Summary statistics
    verdicts = [r.get('verdict') for r in results]
    logger.info(f"\nSummary:")
    logger.info(f"  COMPLIANT: {verdicts.count('COMPLIANT')}")
    logger.info(f"  GREY_AREA: {verdicts.count('GREY_AREA')}")
    logger.info(f"  VIOLATION: {verdicts.count('VIOLATION')}")
    logger.info(f"  ERROR: {verdicts.count('ERROR')}")

    return results


if __name__ == "__main__":
    # Example usage
    test_claims = [
        "Supports healthy sleep patterns when used as directed",
        "Guaranteed to help you fall asleep faster",
        "May help reduce the time it takes to fall asleep in adults experiencing occasional sleeplessness",
        "Manufactured in a cGMP-compliant facility",
        "This product is clinically proven to improve sleep quality"
    ]

    product_id = "supplement_melatonin"

    print("=" * 80)
    print("GPT-4O GREY AREA JUDGE - TEST RUN")
    print("=" * 80)

    results = batch_judge_claims(test_claims, product_id)

    print("\n" + "=" * 80)
    print("DETAILED RESULTS")
    print("=" * 80)

    for i, result in enumerate(results, 1):
        print(f"\n--- CLAIM {i} ---")
        print(json.dumps(result, indent=2))
