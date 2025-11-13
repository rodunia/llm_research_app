"""Pydantic schemas for product validation."""

import re
from typing import List
from pydantic import BaseModel, Field, field_validator


def has_unit(spec: str) -> bool:
    """Check if a specification string contains at least one unit token.

    Recognized units: mg, g, kg, mL, L, W, V, A, km/h, mph, L/100 km, USD, %,
    ppm, count, tablet, capsule, serving, in, Hz, mAh, GB, TB, GHz, px, CRC, s, etc.

    Args:
        spec: Specification string to check

    Returns:
        True if spec contains at least one unit token, False otherwise
    """
    # Pattern matches common units (case-insensitive word boundaries)
    # Expanded to include: cryptocurrency (CRC), time (s, hours), display (in, px, Hz),
    # storage (GB, TB), frequency (GHz), battery (mAh), power (W), distance (m), etc.
    unit_pattern = r'\b(mg|g|kg|mL|L|mAh|W|V|A|km/h|mph|mpg|L/100\s*km|USD|CRC|ppm|count|tablet|capsule|serving|oz|lb|fl\s*oz|°C|°F|%|in|px|Hz|GHz|MHz|GB|TB|MB|KB|s|ms|μs|hours?|m|mm|hp)\b'
    return bool(re.search(unit_pattern, spec, re.IGNORECASE))


class Product(BaseModel):
    """Product specification schema with strict validation."""

    product_id: str = Field(..., description="Unique product identifier")
    name: str = Field(..., description="Product display name")
    region: str = Field(..., description="Geographic region (e.g., US)")
    target_audience: str = Field(
        ...,
        description="Target audience psychographic profile",
        min_length=10
    )
    specs: List[str] = Field(..., description="Technical specifications with units")
    authorized_claims: List[str] = Field(..., description="Approved marketing claims")
    prohibited_or_unsupported_claims: List[str] = Field(
        ..., description="Claims that must not be made"
    )
    disclaimers: List[str] = Field(..., description="Required disclaimers")

    model_config = {"extra": "forbid"}  # Reject unknown fields

    @field_validator('specs')
    @classmethod
    def validate_specs_have_units(cls, specs: List[str]) -> List[str]:
        """Ensure every spec contains at least one unit token."""
        for idx, spec in enumerate(specs):
            if not has_unit(spec):
                raise ValueError(
                    f"Spec at index {idx} missing unit token: '{spec}'"
                )
        return specs
