"""Canonical schemas for evaluation results.

Defines stable, backward-compatible schemas for per-claim and per-run records.
Ensures consistent data structure across evaluation → reporting pipeline.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Literal
from datetime import datetime


# Type aliases
SeverityLevel = Literal["CRITICAL", "MAJOR", "MINOR", "NONE"]
DebertaLabel = Literal["ENTAILMENT", "CONTRADICTION", "NEUTRAL"]


@dataclass
class DebertaOutput:
    """DeBERTa model prediction output."""

    label: DebertaLabel
    probs: Dict[str, float]  # {"ENTAILMENT": 0.9, "CONTRADICTION": 0.05, "NEUTRAL": 0.05}


@dataclass
class ClaimRecord:
    """Canonical per-claim record schema.

    Represents a single extracted claim with its verification metadata.
    Used for deterministic claim extraction (LLM-free).
    """

    # Run identification
    run_id: str
    product: str
    material: str
    engine: str
    time_of_day: str
    temp: float
    rep: int

    # Claim identification
    claim_id: str  # stable id e.g. f"{run_id}::sent{sent_idx}"
    sentence: str  # exact sentence text (no paraphrase)
    sent_index: int  # sentence index in output
    char_span: tuple[int, int]  # (start, end) offsets in full output text

    # Triggers (what made this a claim candidate)
    trigger_types: List[str]  # e.g. ["numeric"], ["financial_guarantee"], ["claim_verb"]

    # Verification (optional, added by DeBERTa)
    deberta: Optional[DebertaOutput] = None
    severity: Optional[SeverityLevel] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        if self.deberta:
            result["deberta"] = {
                "label": self.deberta.label,
                "probs": self.deberta.probs
            }
        return result


@dataclass
class RunMetrics:
    """Canonical metrics for a single run."""

    # Core evaluation metrics (fuzzy matching)
    total_claims: int
    hit_rate: float  # proportion of Supported claims
    contradiction_rate: float  # proportion of Contradicted claims
    unsupported_rate: float  # proportion of Unsupported claims
    ambiguous_rate: float  # proportion of Ambiguous claims
    overclaim_rate: float  # proportion of overclaims detected

    # Error counts
    numeric_error_count: int  # numeric validation errors
    unit_error_count: int  # unit conversion errors

    # Bias metrics
    bias_score: float  # aggregate bias score
    bias_critical: int = 0  # count of critical bias triggers
    bias_major: int = 0  # count of major bias triggers
    bias_minor: int = 0  # count of minor bias triggers

    # DeBERTa metrics (optional, populated when DeBERTa verification runs)
    deberta_authorized: int = 0  # claims with ENTAILMENT
    deberta_hallucinations: int = 0  # claims with CONTRADICTION
    deberta_neutral: int = 0  # claims with NEUTRAL

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class RunRecord:
    """Canonical per-run record schema.

    Complete evaluation result for a single experimental run.
    Backward compatible with legacy flat structure.
    """

    # Run identification
    run_id: str

    # Metadata (experimental factors)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Expected keys in metadata:
    #   - engine: str
    #   - product_id: str
    #   - material_type: str
    #   - temperature: str|float
    #   - time_of_day: str
    #   - repetition_id: int
    #   - started_at: str (ISO timestamp)
    #   - completed_at: str (ISO timestamp)
    #   - session_id: str (optional)

    # Canonical metrics (nested)
    metrics: Optional[RunMetrics] = None

    # Classification labels
    labels: Dict[str, Any] = field(default_factory=dict)
    # Expected keys in labels:
    #   - decision: str ("Supported"|"Contradicted"|"Unsupported"|"Ambiguous")
    #   - critical_violation: bool (any critical-severity issues)

    # Artifacts (file paths)
    artifacts: Dict[str, str] = field(default_factory=dict)
    # Expected keys in artifacts:
    #   - output_path: str (path to generated output .txt)
    #   - prompt_path: str (optional, path to rendered prompt)
    #   - claims_path: str (optional, path to extracted claims .json)

    # Errors (if any)
    errors: List[str] = field(default_factory=list)

    # Legacy fields (backward compatibility) - populated by ensure_per_run_schema
    # These mirror metrics.* at top level for old consumers
    decision: Optional[str] = None
    hit_rate: Optional[float] = None
    contradiction_rate: Optional[float] = None
    unsupported_rate: Optional[float] = None
    ambiguous_rate: Optional[float] = None
    overclaim_rate: Optional[float] = None
    matched_authorized: Optional[List[str]] = None
    violated_prohibited: Optional[List[str]] = None
    numeric_errors: Optional[List[Dict]] = None
    unit_errors: Optional[List[Dict]] = None
    overclaims: Optional[List[str]] = None
    bias_detections: Optional[List[Dict]] = None
    bias_severity_counts: Optional[Dict] = None
    bias_score: Optional[float] = None
    details: Optional[Dict] = None
    engine: Optional[str] = None
    product_id: Optional[str] = None
    material_type: Optional[str] = None
    temperature: Optional[str] = None
    time_of_day: Optional[str] = None
    repetition_id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "run_id": self.run_id,
            "metadata": self.metadata,
            "metrics": self.metrics.to_dict() if self.metrics else None,
            "labels": self.labels,
            "artifacts": self.artifacts,
            "errors": self.errors,
        }

        # Include legacy fields if present (backward compatibility)
        if self.decision:
            result["decision"] = self.decision
        if self.hit_rate is not None:
            result["hit_rate"] = self.hit_rate
        if self.contradiction_rate is not None:
            result["contradiction_rate"] = self.contradiction_rate
        if self.unsupported_rate is not None:
            result["unsupported_rate"] = self.unsupported_rate
        if self.ambiguous_rate is not None:
            result["ambiguous_rate"] = self.ambiguous_rate
        if self.overclaim_rate is not None:
            result["overclaim_rate"] = self.overclaim_rate
        if self.matched_authorized:
            result["matched_authorized"] = self.matched_authorized
        if self.violated_prohibited:
            result["violated_prohibited"] = self.violated_prohibited
        if self.numeric_errors:
            result["numeric_errors"] = self.numeric_errors
        if self.unit_errors:
            result["unit_errors"] = self.unit_errors
        if self.overclaims:
            result["overclaims"] = self.overclaims
        if self.bias_detections:
            result["bias_detections"] = self.bias_detections
        if self.bias_severity_counts:
            result["bias_severity_counts"] = self.bias_severity_counts
        if self.bias_score is not None:
            result["bias_score"] = self.bias_score
        if self.details:
            result["details"] = self.details
        if self.engine:
            result["engine"] = self.engine
        if self.product_id:
            result["product_id"] = self.product_id
        if self.material_type:
            result["material_type"] = self.material_type
        if self.temperature:
            result["temperature"] = self.temperature
        if self.time_of_day:
            result["time_of_day"] = self.time_of_day
        if self.repetition_id is not None:
            result["repetition_id"] = self.repetition_id

        return result


def ensure_per_run_schema(record: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure per-run record conforms to canonical schema.

    Provides backward compatibility by:
    1. Adding "metrics" dict if missing (mirroring legacy top-level fields)
    2. Preserving all legacy fields
    3. Adding metadata/labels/artifacts dicts if missing

    Args:
        record: Legacy or partial per-run result dict

    Returns:
        Enhanced record with canonical schema
    """
    # If already has metrics, ensure it's complete
    if "metrics" not in record or record["metrics"] is None:
        # Build metrics from legacy top-level fields
        record["metrics"] = {
            "total_claims": record.get("total_claims", 0),
            "hit_rate": record.get("hit_rate", 0.0),
            "contradiction_rate": record.get("contradiction_rate", 0.0),
            "unsupported_rate": record.get("unsupported_rate", 0.0),
            "ambiguous_rate": record.get("ambiguous_rate", 0.0),
            "overclaim_rate": record.get("overclaim_rate", 0.0),
            "numeric_error_count": len(record.get("numeric_errors", [])),
            "unit_error_count": len(record.get("unit_errors", [])),
            "bias_score": record.get("bias_score", 0.0),
            "bias_critical": record.get("bias_severity_counts", {}).get("CRITICAL", 0),
            "bias_major": record.get("bias_severity_counts", {}).get("MAJOR", 0),
            "bias_minor": record.get("bias_severity_counts", {}).get("MINOR", 0),
        }

    # Ensure metadata dict exists
    if "metadata" not in record:
        record["metadata"] = {
            "engine": record.get("engine"),
            "product_id": record.get("product_id"),
            "material_type": record.get("material_type"),
            "temperature": record.get("temperature"),
            "time_of_day": record.get("time_of_day"),
            "repetition_id": record.get("repetition_id"),
        }

    # Ensure labels dict exists
    if "labels" not in record:
        record["labels"] = {
            "decision": record.get("decision", "Unsupported"),
            "critical_violation": False,  # to be populated later
        }

    # Ensure artifacts dict exists
    if "artifacts" not in record:
        record["artifacts"] = {}

    # Ensure errors list exists
    if "errors" not in record:
        record["errors"] = []

    # Keep legacy fields for backward compatibility (DO NOT REMOVE)
    # This ensures old consumers don't break

    return record


def get_metric_value(record: Dict[str, Any], metric_name: str) -> Any:
    """Safely get metric value from record (supports both old and new formats).

    Args:
        record: Per-run result dict (legacy or canonical)
        metric_name: Name of metric to retrieve

    Returns:
        Metric value, or None/0 if not found
    """
    # Try nested metrics first (canonical)
    if "metrics" in record and record["metrics"]:
        if metric_name in record["metrics"]:
            return record["metrics"][metric_name]

    # Fallback to top-level (legacy)
    if metric_name in record:
        return record[metric_name]

    # Special handling for count fields
    if metric_name == "numeric_error_count":
        return len(record.get("numeric_errors", []))
    elif metric_name == "unit_error_count":
        return len(record.get("unit_errors", []))
    elif metric_name == "total_claims":
        # Infer from details if available
        details = record.get("details", {})
        return details.get("total_claims", 0)

    # Default
    return 0 if metric_name.endswith("_count") or metric_name.endswith("_rate") or metric_name == "bias_score" else None
