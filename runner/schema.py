"""Pydantic schemas for product validation."""

from typing import List
from pydantic import BaseModel, Field


class Product(BaseModel):
    """Product specification schema."""

    product_id: str = Field(..., description="Unique product identifier")
    name: str = Field(..., description="Product display name")
    region: str = Field(..., description="Geographic region (e.g., US)")
    specs: List[str] = Field(..., description="Technical specifications")
    authorized_claims: List[str] = Field(..., description="Approved marketing claims")
    prohibited_or_unsupported_claims: List[str] = Field(
        ..., description="Claims that must not be made"
    )
    disclaimers: List[str] = Field(..., description="Required disclaimers")
    units_notes: List[str] = Field(default_factory=list, description="Unit documentation")

    class Config:
        extra = "forbid"  # Reject unknown fields
