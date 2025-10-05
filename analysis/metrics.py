"""Metrics and decision categories for claim evaluation."""

from enum import Enum
from typing import List, Dict, Any
from dataclasses import dataclass


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
