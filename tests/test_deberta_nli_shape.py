"""Unit tests for deberta_nli module (output shape validation).

Tests:
- Output contains required keys
- Label is one of {entailment, neutral, contradiction}
- Probabilities sum to ~1.0
- Probabilities dict has all 3 labels
- Hashes are 12 characters

Note: These tests may be slow on first run (model download).
      Use pytest -k "not slow" to skip if needed.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.deberta_nli import DebertaNliVerifier


@pytest.fixture(scope="module")
def verifier():
    """Create DeBERTa verifier (module-scoped to avoid reloading)."""
    # Use smallest model for faster tests
    return DebertaNliVerifier(
        model_name="cross-encoder/nli-deberta-v3-small",
        device="cpu"
    )


@pytest.fixture
def sample_premise():
    """Sample premise for testing."""
    return """AUTHORIZED:
- 120 Hz display for smoother on-screen motion.
- 5G connectivity where available.

PROHIBITED:
- Guaranteed to work for all users.

SPECS:
- Display: 6.5 in, 120 Hz
- Battery: 5000 mAh

DISCLAIMERS:
- Battery life varies by usage."""


def test_verify_returns_dict(verifier, sample_premise):
    """Test that verify() returns a dictionary."""
    hypothesis = "Experience 120 Hz display."
    result = verifier.verify(sample_premise, hypothesis)

    assert isinstance(result, dict)


def test_verify_required_keys(verifier, sample_premise):
    """Test that result contains all required keys."""
    hypothesis = "Experience 120 Hz display."
    result = verifier.verify(sample_premise, hypothesis)

    required_keys = {"model", "label", "probs", "premise_hash", "hypothesis_hash"}
    assert required_keys.issubset(result.keys())


def test_verify_label_valid(verifier, sample_premise):
    """Test that label is one of the valid NLI labels."""
    hypothesis = "Experience 120 Hz display."
    result = verifier.verify(sample_premise, hypothesis)

    valid_labels = {"entailment", "neutral", "contradiction"}
    assert result["label"] in valid_labels


def test_verify_probs_sum_to_one(verifier, sample_premise):
    """Test that probabilities sum to ~1.0."""
    hypothesis = "Experience 120 Hz display."
    result = verifier.verify(sample_premise, hypothesis)

    prob_sum = sum(result["probs"].values())
    assert abs(prob_sum - 1.0) < 0.01  # Allow small epsilon


def test_verify_probs_has_all_labels(verifier, sample_premise):
    """Test that probs dict includes all 3 labels."""
    hypothesis = "Experience 120 Hz display."
    result = verifier.verify(sample_premise, hypothesis)

    valid_labels = {"entailment", "neutral", "contradiction"}
    assert set(result["probs"].keys()) == valid_labels


def test_verify_probs_all_positive(verifier, sample_premise):
    """Test that all probabilities are in [0, 1]."""
    hypothesis = "Experience 120 Hz display."
    result = verifier.verify(sample_premise, hypothesis)

    for label, prob in result["probs"].items():
        assert 0.0 <= prob <= 1.0


def test_verify_hash_length(verifier, sample_premise):
    """Test that hashes are 12 characters."""
    hypothesis = "Experience 120 Hz display."
    result = verifier.verify(sample_premise, hypothesis)

    assert len(result["premise_hash"]) == 12
    assert len(result["hypothesis_hash"]) == 12


def test_verify_hash_hex(verifier, sample_premise):
    """Test that hashes are hexadecimal."""
    hypothesis = "Experience 120 Hz display."
    result = verifier.verify(sample_premise, hypothesis)

    # Check all chars are hex
    assert all(c in '0123456789abcdef' for c in result["premise_hash"])
    assert all(c in '0123456789abcdef' for c in result["hypothesis_hash"])


def test_verify_model_name(verifier, sample_premise):
    """Test that model name is included."""
    hypothesis = "Experience 120 Hz display."
    result = verifier.verify(sample_premise, hypothesis)

    assert isinstance(result["model"], str)
    assert len(result["model"]) > 0


def test_verify_different_hypotheses(verifier, sample_premise):
    """Test that different hypotheses produce different hashes."""
    hyp1 = "Experience 120 Hz display."
    hyp2 = "Guaranteed to work perfectly."

    result1 = verifier.verify(sample_premise, hyp1)
    result2 = verifier.verify(sample_premise, hyp2)

    # Different hypotheses -> different hashes
    assert result1["hypothesis_hash"] != result2["hypothesis_hash"]


def test_verify_same_hypothesis_deterministic(verifier, sample_premise):
    """Test that same hypothesis produces same results."""
    hypothesis = "Experience 120 Hz display."

    result1 = verifier.verify(sample_premise, hypothesis)
    result2 = verifier.verify(sample_premise, hypothesis)

    # Same inputs -> same outputs
    assert result1["label"] == result2["label"]
    assert result1["hypothesis_hash"] == result2["hypothesis_hash"]
    assert result1["premise_hash"] == result2["premise_hash"]

    # Probs should be very close (allow tiny float diff)
    for label in ["entailment", "neutral", "contradiction"]:
        assert abs(result1["probs"][label] - result2["probs"][label]) < 1e-6


def test_verify_batch(verifier, sample_premise):
    """Test batch verification produces list of results."""
    hypotheses = [
        "Experience 120 Hz display.",
        "Guaranteed perfect results.",
        "Available in blue color."
    ]

    results = verifier.verify_batch(sample_premise, hypotheses)

    # Should return list of same length
    assert isinstance(results, list)
    assert len(results) == len(hypotheses)

    # All results should have valid schema
    for result in results:
        assert isinstance(result, dict)
        assert "label" in result
        assert "probs" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
