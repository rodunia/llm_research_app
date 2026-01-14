"""Unit tests for premise_builder module.

Tests:
- Deterministic premise construction
- Section ordering (AUTHORIZED -> PROHIBITED -> SPECS -> DISCLAIMERS)
- Hash function
- Handling of different YAML formats
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.premise_builder import build_premise, hash_text


def test_hash_text_length():
    """Test that hash_text produces 12-character hashes."""
    text = "120 Hz display for smoother motion."
    hash_val = hash_text(text)

    assert len(hash_val) == 12
    assert all(c in '0123456789abcdef' for c in hash_val)


def test_hash_text_deterministic():
    """Test that hash_text is deterministic."""
    text = "5G connectivity where available."

    hash1 = hash_text(text)
    hash2 = hash_text(text)

    assert hash1 == hash2


def test_build_premise_sections():
    """Test that build_premise includes all required sections."""
    mock_product = {
        "authorized_claims": [
            {"statement": "120 Hz display."}
        ],
        "prohibited_claims": [
            "Guaranteed results."
        ],
        "technical_specs": [
            {"category": "Display", "value_with_units": "6.5 in"}
        ],
        "mandatory_disclaimers": [
            {"statement": "Results may vary."}
        ]
    }

    premise = build_premise(mock_product)

    # Verify all sections present
    assert "AUTHORIZED:" in premise
    assert "PROHIBITED:" in premise
    assert "SPECS:" in premise
    assert "DISCLAIMERS:" in premise


def test_build_premise_section_order():
    """Test that sections appear in correct order."""
    mock_product = {
        "authorized_claims": [{"statement": "A"}],
        "prohibited_claims": ["B"],
        "technical_specs": [{"category": "C", "value_with_units": "D"}],
        "mandatory_disclaimers": [{"statement": "E"}]
    }

    premise = build_premise(mock_product)
    lines = premise.split('\n')

    # Find section indices
    auth_idx = next(i for i, line in enumerate(lines) if "AUTHORIZED:" in line)
    proh_idx = next(i for i, line in enumerate(lines) if "PROHIBITED:" in line)
    spec_idx = next(i for i, line in enumerate(lines) if "SPECS:" in line)
    disc_idx = next(i for i, line in enumerate(lines) if "DISCLAIMERS:" in line)

    # Verify order
    assert auth_idx < proh_idx < spec_idx < disc_idx


def test_build_premise_deterministic():
    """Test that build_premise is deterministic."""
    mock_product = {
        "authorized_claims": [
            {"statement": "120 Hz display."},
            {"statement": "5G connectivity."}
        ],
        "prohibited_claims": [
            "Best ever.",
            "Guaranteed."
        ],
        "technical_specs": [
            {"category": "Display", "value_with_units": "6.5 in"},
            {"category": "Battery", "value_with_units": "5000 mAh"}
        ],
        "mandatory_disclaimers": [
            {"statement": "Results vary."}
        ]
    }

    premise1 = build_premise(mock_product)
    premise2 = build_premise(mock_product)

    assert premise1 == premise2


def test_build_premise_preserves_order():
    """Test that build_premise preserves list order within sections."""
    mock_product = {
        "authorized_claims": [
            {"statement": "First claim."},
            {"statement": "Second claim."},
            {"statement": "Third claim."}
        ],
        "prohibited_claims": [],
        "technical_specs": [],
        "mandatory_disclaimers": []
    }

    premise = build_premise(mock_product)

    # Find authorized section
    lines = premise.split('\n')
    auth_idx = next(i for i, line in enumerate(lines) if "AUTHORIZED:" in line)

    # Get claim lines
    claim_lines = [lines[auth_idx + 1], lines[auth_idx + 2], lines[auth_idx + 3]]

    # Verify order
    assert "First claim" in claim_lines[0]
    assert "Second claim" in claim_lines[1]
    assert "Third claim" in claim_lines[2]


def test_build_premise_empty_sections():
    """Test that build_premise handles empty sections gracefully."""
    mock_product = {
        "authorized_claims": [],
        "prohibited_claims": [],
        "technical_specs": [],
        "mandatory_disclaimers": []
    }

    premise = build_premise(mock_product)

    # Should still have section headers
    assert "AUTHORIZED:" in premise
    assert "PROHIBITED:" in premise
    assert "SPECS:" in premise
    assert "DISCLAIMERS:" in premise

    # Should have (none) markers
    assert "(none)" in premise


def test_build_premise_mixed_formats():
    """Test that build_premise handles both dict and string list items."""
    mock_product = {
        "authorized_claims": [
            {"statement": "Claim as dict."},
            "Claim as string."
        ],
        "prohibited_claims": [
            "Prohibited string.",
            {"statement": "Prohibited dict."}
        ],
        "technical_specs": [],
        "mandatory_disclaimers": []
    }

    premise = build_premise(mock_product)

    # Both formats should appear
    assert "Claim as dict" in premise
    assert "Claim as string" in premise
    assert "Prohibited string" in premise
    assert "Prohibited dict" in premise


def test_build_premise_with_units():
    """Test that technical specs include units."""
    mock_product = {
        "authorized_claims": [],
        "prohibited_claims": [],
        "technical_specs": [
            {"category": "Display", "value_with_units": "6.5 in, 120 Hz"},
            {"category": "Battery", "value_with_units": "5000 mAh"}
        ],
        "mandatory_disclaimers": []
    }

    premise = build_premise(mock_product)

    # Verify specs with units
    assert "Display: 6.5 in, 120 Hz" in premise
    assert "Battery: 5000 mAh" in premise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
