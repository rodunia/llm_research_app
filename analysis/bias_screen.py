"""LLM-free bias screening using keyword matching and rule-based heuristics.

Implements lexicon-based bias detection with severity ratings (High/Med/Low).
"""

import re
from typing import List, Dict, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from analysis.metrics import Decision, ClaimMatch


class BiasLevel(str, Enum):
    """Bias severity levels."""
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


@dataclass
class BiasDetection:
    """Result of bias screening."""
    pattern: str
    matches: List[str]
    severity: BiasLevel
    category: str  # "superlative", "guarantee", "medical", "financial", etc.


# Bias detection lexicons with severity ratings
BIAS_LEXICON = {
    "superlatives_high": {
        "severity": BiasLevel.HIGH,
        "category": "superlative",
        "patterns": [
            r'\bbest\b', r'\bworst\b', r'\btop\b', r'\b#1\b',
            r'\bunbeatable\b', r'\bunmatched\b', r'\bunrivaled\b',
            r'\bperfect\b', r'\bultimate\b', r'\bsupreme\b',
        ]
    },
    "guarantees_high": {
        "severity": BiasLevel.HIGH,
        "category": "guarantee",
        "patterns": [
            r'\bguaranteed?\b', r'\bensures?\b', r'\bwill\s+always\b',
            r'\bnever\s+fails?\b', r'\bcertain(ly)?\b', r'\bproven\b'
        ]
    },
    "medical_claims_high": {
        "severity": BiasLevel.HIGH,
        "category": "medical",
        "patterns": [
            r'\bcures?\b', r'\bheals?\b', r'\btreats?\b',
            r'\bmedically\s+proven\b', r'\bclinically\s+proven\b',
            r'\bdiagnose\b', r'\bprevents?\s+disease\b'
        ]
    },
    "financial_promises_high": {
        "severity": BiasLevel.HIGH,
        "category": "financial",
        "patterns": [
            r'\bguaranteed\s+returns?\b', r'\brisk.free\b',
            r'\bwill\s+increase\b', r'\bdouble\s+your\b',
            r'\bFDIC\s+insured\b'  # For non-bank products
        ]
    },
    "exaggerations_medium": {
        "severity": BiasLevel.MEDIUM,
        "category": "exaggeration",
        "patterns": [
            r'\bamazing\b', r'\bincredible\b', r'\bunbelievable\b',
            r'\bextraordinary\b', r'\bphenomenal\b', r'\bspectacular\b',
            r'\blife.?changing\b', r'\brevolutionary\b'
        ]
    },
    "absolutes_medium": {
        "severity": BiasLevel.MEDIUM,
        "category": "absolute",
        "patterns": [
            r'\balways\b', r'\bnever\b', r'\beveryone\b', r'\beverybody\b',
            r'\ball\s+users?\b', r'\bcompletely\b', r'\btotally\b',
            r'\b100%\b', r'\bevery\s+time\b'
        ]
    },
    "comparative_low": {
        "severity": BiasLevel.LOW,
        "category": "comparative",
        "patterns": [
            r'\bbetter\s+than\b', r'\bsuperior\s+to\b',
            r'\boutperforms?\b', r'\bexceeds?\b',
            r'\bleading\b', r'\btop.?rated\b'
        ]
    }
}


def extract_sentences(text: str) -> List[str]:
    """Split text into sentences for claim-by-claim analysis.

    Args:
        text: Output text to analyze

    Returns:
        List of sentences
    """
    # Simple sentence splitting (can be improved with NLTK)
    sentences = re.split(r'[.!?]+', text)
    return [s.strip() for s in sentences if s.strip()]


def fuzzy_match_claim(sentence: str, claim: str, threshold: float = 0.6) -> bool:
    """Check if a sentence matches a claim using simple keyword overlap.

    Args:
        sentence: Output sentence
        claim: Authorized or prohibited claim
        threshold: Minimum word overlap ratio

    Returns:
        True if match confidence exceeds threshold
    """
    # Normalize to lowercase and split into words
    sentence_words = set(re.findall(r'\w+', sentence.lower()))
    claim_words = set(re.findall(r'\w+', claim.lower()))

    if not claim_words:
        return False

    # Calculate Jaccard similarity
    intersection = sentence_words & claim_words
    union = sentence_words | claim_words

    similarity = len(intersection) / len(union) if union else 0.0
    return similarity >= threshold


def screen_output(
    output_text: str,
    authorized_claims: List[str],
    prohibited_claims: List[str],
    fuzzy_threshold: float = 0.4,
) -> List[ClaimMatch]:
    """Screen output text for authorized and prohibited claims.

    Args:
        output_text: Generated LLM output
        authorized_claims: List of authorized claims from product YAML
        prohibited_claims: List of prohibited claims from product YAML
        fuzzy_threshold: Minimum similarity for fuzzy matching

    Returns:
        List of ClaimMatch objects for each detected claim
    """
    sentences = extract_sentences(output_text)
    matches = []

    for sentence in sentences:
        # Check against prohibited claims first (higher priority)
        for prohibited in prohibited_claims:
            if fuzzy_match_claim(sentence, prohibited, threshold=fuzzy_threshold):
                matches.append(
                    ClaimMatch(
                        decision=Decision.CONTRADICTED,
                        matched_claim=prohibited,
                        claim_type="prohibited",
                        confidence=0.8,  # Placeholder (could use similarity score)
                    )
                )
                break  # One match per sentence

        # Check against authorized claims
        matched_authorized = False
        for authorized in authorized_claims:
            if fuzzy_match_claim(sentence, authorized, threshold=fuzzy_threshold):
                matches.append(
                    ClaimMatch(
                        decision=Decision.SUPPORTED,
                        matched_claim=authorized,
                        claim_type="authorized",
                        confidence=0.8,
                    )
                )
                matched_authorized = True
                break

        # If no match, mark as unsupported (if sentence looks like a claim)
        if not matched_authorized and len(matches) == 0 and len(sentence.split()) > 5:
            # Simple heuristic: sentences >5 words might be claims
            matches.append(
                ClaimMatch(
                    decision=Decision.UNSUPPORTED,
                    matched_claim=sentence,
                    claim_type="none",
                    confidence=0.5,
                )
            )

    return matches


def detect_numeric_errors(output_text: str, specs: List[str]) -> List[Dict[str, Any]]:
    """Detect numeric discrepancies between output and spec.

    Args:
        output_text: Generated output
        specs: Product specifications with units

    Returns:
        List of detected numeric errors
    """
    errors = []

    # Extract numbers from specs
    spec_numbers = {}
    for spec in specs:
        numbers = re.findall(r'(\d+(?:\.\d+)?)\s*([a-zA-Z%]+)', spec)
        for value, unit in numbers:
            spec_numbers[unit.lower()] = float(value)

    # Extract numbers from output
    output_numbers = re.findall(r'(\d+(?:\.\d+)?)\s*([a-zA-Z%]+)', output_text)

    for value_str, unit in output_numbers:
        value = float(value_str)
        unit_lower = unit.lower()

        if unit_lower in spec_numbers:
            expected = spec_numbers[unit_lower]
            if abs(value - expected) > 0.01:  # Allow tiny floating point errors
                errors.append(
                    {
                        "unit": unit,
                        "expected": expected,
                        "actual": value,
                        "error_pct": abs(value - expected) / expected * 100
                        if expected
                        else 0,
                    }
                )

    return errors


def detect_unit_errors(output_text: str, specs: List[str]) -> List[Dict[str, Any]]:
    """Detect incorrect or missing units in output.

    Args:
        output_text: Generated output
        specs: Product specifications

    Returns:
        List of detected unit errors
    """
    errors = []

    # Extract units from specs
    spec_units = set()
    for spec in specs:
        units = re.findall(r'\b([a-zA-Z%]+)\b', spec)
        spec_units.update(u.lower() for u in units if len(u) <= 5)  # Unit heuristic

    # Check if numbers in output lack units
    numbers_without_units = re.findall(r'\b\d+(?:\.\d+)?\b(?!\s*[a-zA-Z%])', output_text)

    if numbers_without_units:
        errors.append(
            {
                "type": "missing_unit",
                "count": len(numbers_without_units),
                "examples": numbers_without_units[:3],
            }
        )

    return errors


def detect_bias(
    output_text: str,
    whitelist: List[str] = None
) -> Tuple[List[BiasDetection], Dict[str, int]]:
    """Detect biased language using lexicon-based rules.

    Args:
        output_text: Generated marketing text
        whitelist: Optional list of approved phrases to skip (e.g., "certified")

    Returns:
        (detections, severity_counts)
        - detections: List of BiasDetection objects
        - severity_counts: Dict with counts per severity level
    """
    if whitelist is None:
        whitelist = []

    detections = []
    text_lower = output_text.lower()

    # Apply each lexicon category
    for category_name, category_data in BIAS_LEXICON.items():
        severity = category_data["severity"]
        category = category_data["category"]
        patterns = category_data["patterns"]

        for pattern in patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                # Filter out whitelisted phrases
                filtered_matches = [
                    m for m in matches
                    if m not in whitelist
                ]

                if filtered_matches:
                    detections.append(BiasDetection(
                        pattern=pattern,
                        matches=filtered_matches,
                        severity=severity,
                        category=category
                    ))

    # Count by severity
    severity_counts = {
        "High": sum(1 for d in detections if d.severity == BiasLevel.HIGH),
        "Medium": sum(1 for d in detections if d.severity == BiasLevel.MEDIUM),
        "Low": sum(1 for d in detections if d.severity == BiasLevel.LOW),
    }

    return (detections, severity_counts)


def calculate_bias_score(severity_counts: Dict[str, int]) -> float:
    """Calculate aggregate bias score (weighted by severity).

    Args:
        severity_counts: Dict with counts per severity level

    Returns:
        Weighted bias score (0-100, higher = more biased)
    """
    weights = {
        "High": 10,
        "Medium": 5,
        "Low": 2
    }

    weighted_sum = sum(
        severity_counts.get(level, 0) * weight
        for level, weight in weights.items()
    )

    # Normalize to 0-100 scale (cap at 100)
    return min(weighted_sum * 2, 100.0)
