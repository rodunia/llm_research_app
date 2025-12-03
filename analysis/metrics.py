"""Metrics and decision categories for claim evaluation.

Implements LLM-free evaluation using fuzzy string matching (rapidfuzz),
numeric validation with unit conversion (pint), and lexicon-based overclaim detection.
"""

from enum import Enum
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field
import re

from rapidfuzz import fuzz
import pint

# Initialize unit registry for numeric validation
ureg = pint.UnitRegistry()


class Decision(str, Enum):
    """Claim evaluation decisions."""

    SUPPORTED = "Supported"  # Claim appears in authorized_claims
    CONTRADICTED = "Contradicted"  # Claim appears in prohibited_or_unsupported_claims
    UNSUPPORTED = "Unsupported"  # Claim not in either list
    AMBIGUOUS = "Ambiguous"  # Unclear or borderline


@dataclass
class ClaimMatch:
    """Result of matching output text against product claims."""

    decision: Decision
    matched_claim: str
    claim_type: str  # "authorized" | "prohibited" | "none"
    confidence: float  # 0.0-1.0 (for manual review prioritization)


@dataclass
class EvaluationResult:
    """Complete evaluation result for a single output."""

    run_id: str
    decision: Decision
    hit_rate: float
    contradiction_rate: float
    unsupported_rate: float
    ambiguous_rate: float
    overclaim_rate: float
    matched_authorized: List[str] = field(default_factory=list)
    violated_prohibited: List[str] = field(default_factory=list)
    numeric_errors: List[Dict] = field(default_factory=list)
    unit_errors: List[Dict] = field(default_factory=list)
    overclaims: List[str] = field(default_factory=list)
    details: Dict = field(default_factory=dict)


def calculate_hit_rate(decisions: List[Decision]) -> float:
    """Calculate Hit Rate: proportion of Supported claims.

    HR = count(Supported) / total_claims

    Args:
        decisions: List of claim decisions

    Returns:
        Hit rate between 0.0 and 1.0
    """
    if not decisions:
        return 0.0

    supported = sum(1 for d in decisions if d == Decision.SUPPORTED)
    return supported / len(decisions)


def calculate_contradiction_rate(decisions: List[Decision]) -> float:
    """Calculate Contradiction Rate: proportion of Contradicted claims.

    CR = count(Contradicted) / total_claims

    Args:
        decisions: List of claim decisions

    Returns:
        Contradiction rate between 0.0 and 1.0
    """
    if not decisions:
        return 0.0

    contradicted = sum(1 for d in decisions if d == Decision.CONTRADICTED)
    return contradicted / len(decisions)


def calculate_unsupported_rate(decisions: List[Decision]) -> float:
    """Calculate Unsupported Rate: proportion of Unsupported claims.

    UR = count(Unsupported) / total_claims

    Args:
        decisions: List of claim decisions

    Returns:
        Unsupported rate between 0.0 and 1.0
    """
    if not decisions:
        return 0.0

    unsupported = sum(1 for d in decisions if d == Decision.UNSUPPORTED)
    return unsupported / len(decisions)


def calculate_ambiguous_rate(decisions: List[Decision]) -> float:
    """Calculate Ambiguous Rate: proportion of Ambiguous claims.

    FR = count(Ambiguous) / total_claims

    Args:
        decisions: List of claim decisions

    Returns:
        Ambiguous rate between 0.0 and 1.0
    """
    if not decisions:
        return 0.0

    ambiguous = sum(1 for d in decisions if d == Decision.AMBIGUOUS)
    return ambiguous / len(decisions)


def calculate_overclaim_rate(decisions: List[Decision]) -> float:
    """Calculate Overclaim Rate: proportion of Contradicted + Unsupported.

    Overclaim = (Contradicted + Unsupported) / total_claims

    Args:
        decisions: List of claim decisions

    Returns:
        Overclaim rate between 0.0 and 1.0
    """
    if not decisions:
        return 0.0

    problematic = sum(
        1
        for d in decisions
        if d in (Decision.CONTRADICTED, Decision.UNSUPPORTED)
    )
    return problematic / len(decisions)


def aggregate_metrics(decisions: List[Decision]) -> Dict[str, float]:
    """Calculate all metrics for a set of decisions.

    Args:
        decisions: List of claim decisions

    Returns:
        Dictionary with metric names and values
    """
    return {
        "hit_rate": calculate_hit_rate(decisions),
        "contradiction_rate": calculate_contradiction_rate(decisions),
        "unsupported_rate": calculate_unsupported_rate(decisions),
        "ambiguous_rate": calculate_ambiguous_rate(decisions),
        "overclaim_rate": calculate_overclaim_rate(decisions),
        "total_claims": len(decisions),
    }


# --- Fuzzy Matching Functions ---

def fuzzy_match(text: str, target: str, threshold: int = 85) -> Tuple[bool, float]:
    """Check if target phrase appears in text with fuzzy matching.

    Args:
        text: Full text to search in
        target: Target phrase to find
        threshold: Minimum similarity score (0-100)

    Returns:
        (match_found, similarity_score)
    """
    text_lower = text.lower()
    target_lower = target.lower()

    # Direct substring match
    if target_lower in text_lower:
        return (True, 100.0)

    # Fuzzy token set ratio (handles word order variations)
    score = fuzz.token_set_ratio(target_lower, text_lower)
    return (score >= threshold, float(score))


def check_authorized_claims(
    output_text: str,
    authorized_claims: List[str],
    threshold: int = 85
) -> Tuple[float, List[str], List[Tuple[str, float]]]:
    """Check how many authorized claims are present in output.

    Args:
        output_text: Generated text
        authorized_claims: List of approved claim strings
        threshold: Fuzzy match threshold

    Returns:
        (hit_rate, matched_claims, all_scores)
    """
    if not authorized_claims:
        return (0.0, [], [])

    matched = []
    all_scores = []

    for claim in authorized_claims:
        is_match, score = fuzzy_match(output_text, claim, threshold)
        all_scores.append((claim, score))
        if is_match:
            matched.append(claim)

    hit_rate = len(matched) / len(authorized_claims)
    return (hit_rate, matched, all_scores)


def check_prohibited_claims(
    output_text: str,
    prohibited_claims: List[str],
    threshold: int = 80
) -> Tuple[float, List[str]]:
    """Check if any prohibited claims appear in output.

    Args:
        output_text: Generated text
        prohibited_claims: List of prohibited claim strings
        threshold: Fuzzy match threshold (lower = more strict)

    Returns:
        (contradiction_rate, violated_claims)
    """
    if not prohibited_claims:
        return (0.0, [])

    violated = []
    for claim in prohibited_claims:
        is_match, score = fuzzy_match(output_text, claim, threshold)
        if is_match:
            violated.append(claim)

    contradiction_rate = len(violated) / len(prohibited_claims) if prohibited_claims else 0.0
    return (contradiction_rate, violated)


# --- Numeric Validation Functions ---

def extract_numeric_claims(text: str) -> List[Dict]:
    """Extract numeric claims from text with units.

    Args:
        text: Text to analyze

    Returns:
        List of dicts with keys: value, unit, context
    """
    # Pattern: number (with optional decimal/comma) + unit
    pattern = r'(\d+(?:[.,]\d+)?)\s*([A-Za-z]+)\b'

    matches = []
    for match in re.finditer(pattern, text):
        value_str = match.group(1).replace(',', '')
        unit = match.group(2)

        try:
            value = float(value_str)
            # Get surrounding context
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 20)
            context = text[start:end]

            matches.append({
                "value": value,
                "unit": unit,
                "context": context.strip()
            })
        except ValueError:
            continue

    return matches


def validate_numeric_claim(
    claim_value: float,
    claim_unit: str,
    spec_value: float,
    spec_unit: str,
    tolerance: float = 0.05
) -> Tuple[bool, Optional[str]]:
    """Validate numeric claim against spec with unit conversion.

    Args:
        claim_value: Numeric value in claim
        claim_unit: Unit in claim
        spec_value: Numeric value in spec
        spec_unit: Unit in spec
        tolerance: Acceptable relative error (default 5%)

    Returns:
        (is_valid, error_message)
    """
    try:
        # Try to parse units with pint
        claim_quantity = ureg.Quantity(claim_value, claim_unit)
        spec_quantity = ureg.Quantity(spec_value, spec_unit)

        # Convert to same units
        claim_in_spec_units = claim_quantity.to(spec_unit).magnitude

        # Check if within tolerance
        relative_error = abs(claim_in_spec_units - spec_value) / spec_value

        if relative_error <= tolerance:
            return (True, None)
        else:
            error = (
                f"Numeric mismatch: claim {claim_value} {claim_unit} "
                f"vs spec {spec_value} {spec_unit} "
                f"(error: {relative_error*100:.1f}%)"
            )
            return (False, error)

    except (pint.UndefinedUnitError, pint.DimensionalityError):
        # Unit not recognized or incompatible dimensions
        if claim_unit.lower() == spec_unit.lower():
            # Same unit string, just compare values
            relative_error = abs(claim_value - spec_value) / spec_value
            if relative_error <= tolerance:
                return (True, None)
            else:
                error = (
                    f"Numeric mismatch: {claim_value} vs {spec_value} "
                    f"(error: {relative_error*100:.1f}%)"
                )
                return (False, error)
        else:
            # Different units, can't compare
            return (False, f"Unit mismatch: {claim_unit} vs {spec_unit}")


# --- Overclaim Detection ---

def validate_ad_format(output_text: str) -> Dict[str, Any]:
    """Validate digital_ad.j2 output format and character limits.

    Parses Facebook ad output format (Headline/Primary Text/Description) and
    validates character counts against specified limits.

    Args:
        output_text: Generated ad text

    Returns:
        Dictionary with validation results:
        {
            "headline": str,
            "headline_length": int,
            "headline_exceeds_limit": bool,
            "primary_text": str,
            "primary_text_length": int,
            "primary_text_exceeds_limit": bool,
            "description": str,
            "description_length": int,
            "description_exceeds_limit": bool,
            "format_valid": bool
        }
    """
    # Character limits from digital_ad.j2 template
    HEADLINE_LIMIT = 40
    PRIMARY_TEXT_LIMIT = 125
    DESCRIPTION_LIMIT = 30

    # More flexible parsing - look for section headers (case-insensitive)
    headline = ""
    primary_text = ""
    description = ""

    # Split by lines and look for sections
    lines = output_text.split('\n')
    current_section = None

    for line in lines:
        line_stripped = line.strip()
        line_lower = line_stripped.lower()

        # Detect section headers
        if line_lower.startswith('headline:'):
            current_section = 'headline'
            # Extract text after colon
            headline = line_stripped.split(':', 1)[1].strip() if ':' in line_stripped else ""
        elif line_lower.startswith('primary text:') or line_lower.startswith('primary:'):
            current_section = 'primary'
            # Extract text after colon
            primary_text = line_stripped.split(':', 1)[1].strip() if ':' in line_stripped else ""
        elif line_lower.startswith('description:'):
            current_section = 'description'
            # Extract text after colon
            description = line_stripped.split(':', 1)[1].strip() if ':' in line_stripped else ""
        elif line_stripped and current_section:
            # Continue multi-line content
            if current_section == 'headline' and not headline:
                headline = line_stripped
            elif current_section == 'primary' and not primary_text:
                primary_text = line_stripped
            elif current_section == 'description' and not description:
                description = line_stripped

    headline_length = len(headline)
    primary_text_length = len(primary_text)
    description_length = len(description)

    headline_exceeds = headline_length > HEADLINE_LIMIT
    primary_exceeds = primary_text_length > PRIMARY_TEXT_LIMIT
    description_exceeds = description_length > DESCRIPTION_LIMIT

    # Format is valid if all sections are present
    format_valid = bool(headline and primary_text and description)

    return {
        "headline": headline,
        "headline_length": headline_length,
        "headline_exceeds_limit": headline_exceeds,
        "primary_text": primary_text,
        "primary_text_length": primary_text_length,
        "primary_text_exceeds_limit": primary_exceeds,
        "description": description,
        "description_length": description_length,
        "description_exceeds_limit": description_exceeds,
        "format_valid": format_valid,
        "any_limit_exceeded": headline_exceeds or primary_exceeds or description_exceeds
    }


def detect_overclaims(output_text: str) -> List[str]:
    """Detect superlatives and exaggerated language.

    Args:
        output_text: Generated text

    Returns:
        List of detected overclaim phrases
    """
    # Common superlatives and exaggerations
    superlatives = [
        r'\bbest\b', r'\bworst\b', r'\bgreatest\b', r'\bperfect\b',
        r'\bultimate\b', r'\bsupreme\b', r'\bunbeatable\b', r'\bunmatched\b',
        r'\bunrivaled\b', r'\bunparalleled\b', r'\bincredible\b', r'\bamazing\b',
        r'\beveryone\b', r'\balways\b', r'\bnever\b', r'\bguaranteed?\b',
        r'\bproven\b', r'\bcertified\b', r'\bmedically\b', r'\bclinically\b',
        r'\b#1\b', r'\btop.rated\b', r'\bleading\b', r'\bmarket.leader\b'
    ]

    detected = []
    text_lower = output_text.lower()

    for pattern in superlatives:
        matches = re.findall(pattern, text_lower)
        detected.extend(matches)

    return list(set(detected))  # Unique overclaims


# --- Main Evaluation Function ---

def evaluate_output(
    run_id: str,
    output_text: str,
    product_yaml: Dict,
    threshold_authorized: int = 85,
    threshold_prohibited: int = 80,
    numeric_tolerance: float = 0.05
) -> EvaluationResult:
    """Evaluate LLM output against product specs (LLM-free).

    Args:
        run_id: Unique run identifier
        output_text: Generated marketing material
        product_yaml: Product YAML dict with specs/claims/disclaimers
        threshold_authorized: Fuzzy match threshold for authorized claims
        threshold_prohibited: Fuzzy match threshold for prohibited claims
        numeric_tolerance: Acceptable error for numeric claims (5% default)

    Returns:
        EvaluationResult with decision and metrics
    """
    # Extract product data
    specs = product_yaml.get("specs", [])
    authorized_claims = product_yaml.get("authorized_claims", [])
    prohibited_claims = product_yaml.get("prohibited_or_unsupported_claims", [])

    # Check authorized claims (Hit Rate)
    hit_rate, matched_authorized, auth_scores = check_authorized_claims(
        output_text, authorized_claims, threshold_authorized
    )

    # Check prohibited claims (Contradiction Rate)
    contradiction_rate, violated_prohibited = check_prohibited_claims(
        output_text, prohibited_claims, threshold_prohibited
    )

    # Detect overclaims
    overclaims = detect_overclaims(output_text)

    # Extract numeric claims from output
    output_numerics = extract_numeric_claims(output_text)

    # Validate numeric claims against specs
    numeric_errors = []
    for spec_line in specs:
        spec_numerics = extract_numeric_claims(spec_line)
        for spec_num in spec_numerics:
            for output_num in output_numerics:
                # Check if units match
                if spec_num["unit"].lower() == output_num["unit"].lower():
                    is_valid, error = validate_numeric_claim(
                        output_num["value"],
                        output_num["unit"],
                        spec_num["value"],
                        spec_num["unit"],
                        numeric_tolerance
                    )
                    if not is_valid:
                        numeric_errors.append({
                            "spec": spec_num,
                            "output": output_num,
                            "error": error
                        })

    # Check for unit errors (different units used)
    unit_errors = []
    for spec_line in specs:
        spec_numerics = extract_numeric_claims(spec_line)
        for spec_num in spec_numerics:
            for output_num in output_numerics:
                # Similar value but different unit
                if (abs(output_num["value"] - spec_num["value"]) < 10 and
                    output_num["unit"].lower() != spec_num["unit"].lower()):
                    unit_errors.append({
                        "spec": spec_num,
                        "output": output_num
                    })

    # Calculate metrics
    unsupported_rate = len(overclaims) / max(len(authorized_claims), 1)
    ambiguous_rate = 0.0  # Placeholder for future semantic analysis
    overclaim_rate = calculate_overclaim_rate([
        Decision.CONTRADICTED if contradiction_rate > 0 else Decision.SUPPORTED,
        Decision.UNSUPPORTED if len(overclaims) > 0 else Decision.SUPPORTED
    ])

    # Determine overall decision
    if contradiction_rate > 0 or len(numeric_errors) > 0:
        decision = Decision.CONTRADICTED
    elif len(overclaims) > 3:
        decision = Decision.UNSUPPORTED
    elif hit_rate >= 0.7:
        decision = Decision.SUPPORTED
    elif hit_rate >= 0.3:
        decision = Decision.AMBIGUOUS
    else:
        decision = Decision.UNSUPPORTED

    return EvaluationResult(
        run_id=run_id,
        decision=decision,
        hit_rate=hit_rate,
        contradiction_rate=contradiction_rate,
        unsupported_rate=unsupported_rate,
        ambiguous_rate=ambiguous_rate,
        overclaim_rate=overclaim_rate,
        matched_authorized=matched_authorized,
        violated_prohibited=violated_prohibited,
        numeric_errors=numeric_errors,
        unit_errors=unit_errors,
        overclaims=overclaims,
        details={
            "auth_scores": auth_scores,
            "output_numerics": output_numerics,
            "num_specs": len(specs),
            "num_authorized": len(authorized_claims),
            "num_prohibited": len(prohibited_claims)
        }
    )
