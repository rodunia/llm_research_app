"""Deterministic premise builder for DeBERTa NLI verification.

Constructs a structured premise from product YAML that serves as ground truth
for verifying extracted claims. The premise includes:
- AUTHORIZED claims (approved marketing statements)
- PROHIBITED claims (policy violations)
- SPECS (technical specifications)
- DISCLAIMERS (legal/compliance statements)

The premise is deterministic: same YAML always produces same premise text.
"""

import hashlib
import yaml
from pathlib import Path
from typing import Dict, Any, List


def hash_text(text: str) -> str:
    """Generate short SHA256 hash prefix for text deduplication.

    Args:
        text: Input text to hash

    Returns:
        12-character hex prefix of SHA256 hash
    """
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]


def build_premise(product_yaml_dict: Dict[str, Any]) -> str:
    """Build deterministic NLI premise from product YAML.

    Constructs a structured text premise with explicit section headers.
    Maintains YAML list order for stability.

    Args:
        product_yaml_dict: Parsed product YAML dictionary

    Returns:
        Formatted premise string with sections:
        AUTHORIZED:\n...\nPROHIBITED:\n...\nSPECS:\n...\nDISCLAIMERS:\n...

    Example:
        >>> product = {
        ...     "authorized_claims": [
        ...         {"statement": "120 Hz display for smoother motion."}
        ...     ],
        ...     "prohibited_claims": ["Guaranteed to cure insomnia."],
        ...     "technical_specs": [
        ...         {"category": "Display", "value_with_units": "6.5 in"}
        ...     ],
        ...     "mandatory_disclaimers": [
        ...         {"statement": "Battery life varies by usage."}
        ...     ]
        ... }
        >>> premise = build_premise(product)
        >>> "AUTHORIZED:" in premise
        True
    """
    sections = []

    # Section 1: AUTHORIZED CLAIMS
    authorized = []
    authorized_claims = product_yaml_dict.get('authorized_claims', [])

    # Handle nested dict structure (current YAML format: {efficacy: [...], safety: [...]})
    if isinstance(authorized_claims, dict):
        for category, claims in authorized_claims.items():
            if isinstance(claims, list):
                for claim_text in claims:
                    if isinstance(claim_text, dict):
                        statement = claim_text.get('statement', '')
                    elif isinstance(claim_text, str):
                        statement = claim_text
                    else:
                        continue
                    if statement:
                        authorized.append(statement)
    # Handle flat list (legacy format)
    elif isinstance(authorized_claims, list):
        for claim in authorized_claims:
            if isinstance(claim, dict):
                statement = claim.get('statement', '')
            elif isinstance(claim, str):
                statement = claim
            else:
                continue
            if statement:
                authorized.append(statement)

    if authorized:
        sections.append("AUTHORIZED:\n" + "\n".join(f"- {stmt}" for stmt in authorized))
    else:
        sections.append("AUTHORIZED:\n(none)")

    # Section 2: PROHIBITED CLAIMS
    prohibited = []
    # Try new key first (with underscore), fallback to legacy key
    prohibited_claims = product_yaml_dict.get('prohibited_or_unsupported_claims') or product_yaml_dict.get('prohibited_claims', [])

    # Handle nested dict structure (current YAML format)
    if isinstance(prohibited_claims, dict):
        for category, claims in prohibited_claims.items():
            if isinstance(claims, list):
                for claim_text in claims:
                    if isinstance(claim_text, dict):
                        statement = claim_text.get('statement', '')
                    elif isinstance(claim_text, str):
                        statement = claim_text
                    else:
                        continue
                    if statement:
                        prohibited.append(statement)
    # Handle flat list (legacy format)
    elif isinstance(prohibited_claims, list):
        for claim in prohibited_claims:
            if isinstance(claim, dict):
                statement = claim.get('statement', '')
            elif isinstance(claim, str):
                statement = claim
            else:
                continue
            if statement:
                prohibited.append(statement)

    if prohibited:
        sections.append("PROHIBITED:\n" + "\n".join(f"- {stmt}" for stmt in prohibited))
    else:
        sections.append("PROHIBITED:\n(none)")

    # Section 3: SPECS
    specs = []
    specs_data = product_yaml_dict.get('specs', {})

    # Handle nested dict structure (current YAML format)
    if isinstance(specs_data, dict):
        for category, items in specs_data.items():
            if isinstance(items, list):
                for item in items:
                    specs.append(f"{category}: {item}")
            elif isinstance(items, dict):
                # Recursively handle nested dicts (e.g., camera_system with subcategories)
                for subcategory, subitems in items.items():
                    if isinstance(subitems, list):
                        for item in subitems:
                            specs.append(f"{category}.{subcategory}: {item}")
                    else:
                        specs.append(f"{category}.{subcategory}: {subitems}")
            else:
                specs.append(f"{category}: {items}")
    # Handle flat list (legacy format)
    elif isinstance(specs_data, list):
        for spec in specs_data:
            if isinstance(spec, dict):
                category = spec.get('category', '')
                value = spec.get('value_with_units', '')
                if category and value:
                    specs.append(f"{category}: {value}")
            elif isinstance(spec, str):
                specs.append(spec)

    if specs:
        sections.append("SPECS:\n" + "\n".join(f"- {spec}" for spec in specs))
    else:
        sections.append("SPECS:\n(none)")

    # Section 4: DISCLAIMERS
    disclaimers = []
    # Try new key first, fallback to legacy key
    disclaimers_data = product_yaml_dict.get('mandatory_statements') or product_yaml_dict.get('mandatory_disclaimers', [])

    for disclaimer in disclaimers_data:
        if isinstance(disclaimer, dict):
            statement = disclaimer.get('statement', '')
        elif isinstance(disclaimer, str):
            statement = disclaimer
        else:
            continue

        if statement:
            disclaimers.append(statement)

    if disclaimers:
        sections.append("DISCLAIMERS:\n" + "\n".join(f"- {stmt}" for stmt in disclaimers))
    else:
        sections.append("DISCLAIMERS:\n(none)")

    return "\n\n".join(sections)


def load_product_yaml(product_id: str, products_dir: Path = Path("products")) -> Dict[str, Any]:
    """Load product YAML by product_id.

    Args:
        product_id: Product identifier (e.g., 'smartphone_mid')
        products_dir: Directory containing product YAML files

    Returns:
        Parsed product YAML dictionary

    Raises:
        FileNotFoundError: If product YAML not found
    """
    yaml_path = products_dir / f"{product_id}.yaml"

    if not yaml_path.exists():
        raise FileNotFoundError(f"Product YAML not found: {yaml_path}")

    with open(yaml_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def build_premise_for_product(product_id: str, products_dir: Path = Path("products")) -> str:
    """Load product YAML and build premise (convenience wrapper).

    Args:
        product_id: Product identifier
        products_dir: Directory containing product YAML files

    Returns:
        Formatted premise string
    """
    product_yaml = load_product_yaml(product_id, products_dir)
    return build_premise(product_yaml)


# Self-check
if __name__ == "__main__":
    print("Premise Builder Self-Check")
    print("=" * 60)

    # Test hash function
    test_text = "120 Hz display for smoother motion."
    text_hash = hash_text(test_text)
    print(f"✓ hash_text() produces {len(text_hash)}-char hash: {text_hash}")

    # Test build_premise with mock data
    mock_product = {
        "product_id": "test_smartphone",
        "name": "Test Smartphone",
        "authorized_claims": [
            {"statement": "120 Hz display for smoother on-screen motion."},
            {"statement": "5G connectivity where available."}
        ],
        "prohibited_claims": [
            "Guaranteed to work in all conditions.",
            "Best smartphone ever made."
        ],
        "technical_specs": [
            {"category": "Display", "value_with_units": "6.5 in, 120 Hz"},
            {"category": "Battery", "value_with_units": "5000 mAh"}
        ],
        "mandatory_disclaimers": [
            {"statement": "Battery life varies by usage."},
            {"statement": "5G availability depends on carrier."}
        ]
    }

    premise = build_premise(mock_product)

    print("\n✓ build_premise() output:\n")
    print(premise)
    print()

    # Verify structure
    required_sections = ["AUTHORIZED:", "PROHIBITED:", "SPECS:", "DISCLAIMERS:"]
    for section in required_sections:
        if section in premise:
            print(f"✓ Section '{section}' present")
        else:
            print(f"✗ Section '{section}' MISSING")

    # Verify determinism
    premise2 = build_premise(mock_product)
    if premise == premise2:
        print("\n✓ Premise is deterministic (same input -> same output)")
    else:
        print("\n✗ Premise is NOT deterministic")

    # Verify order preservation
    lines = premise.split('\n')
    auth_idx = next(i for i, line in enumerate(lines) if "AUTHORIZED:" in line)
    proh_idx = next(i for i, line in enumerate(lines) if "PROHIBITED:" in line)
    spec_idx = next(i for i, line in enumerate(lines) if "SPECS:" in line)
    disc_idx = next(i for i, line in enumerate(lines) if "DISCLAIMERS:" in line)

    if auth_idx < proh_idx < spec_idx < disc_idx:
        print("✓ Section order preserved: AUTHORIZED -> PROHIBITED -> SPECS -> DISCLAIMERS")
    else:
        print("✗ Section order INCORRECT")

    print("\n" + "=" * 60)
    print("Self-check complete!")
