"""Pydantic schemas for estimates."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EstimateStatus(str, Enum):
    """Status of an estimate."""

    DRAFT = "draft"
    QUOTED = "quoted"
    WON = "won"
    LOST = "lost"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DimensionsInput(BaseModel):
    """Packaging dimension inputs."""

    flat_width: float = Field(ge=10, le=2000, description="Flat width in mm")
    flat_height: float = Field(ge=10, le=2000, description="Flat height in mm")
    outer_wrap_width: Optional[float] = Field(
        None, ge=10, le=2000, description="Outer wrap width in mm"
    )
    outer_wrap_height: Optional[float] = Field(
        None, ge=10, le=2000, description="Outer wrap height in mm"
    )
    liner_width: Optional[float] = Field(
        None, ge=10, le=2000, description="Liner width in mm"
    )
    liner_height: Optional[float] = Field(
        None, ge=10, le=2000, description="Liner height in mm"
    )
    spine_depth: float = Field(
        default=0, ge=0, le=200, description="Spine/gusset depth in mm"
    )


class MaterialsInput(BaseModel):
    """Material selection inputs."""

    board_type: str = Field(description="Type of board material")
    board_thickness: float = Field(default=2.0, ge=0.5, le=10, description="Board thickness in mm")
    outer_wrap: str = Field(default="buckram_cloth", description="Outer wrap material")
    liner: str = Field(default="uncoated_paper_120gsm", description="Liner material")
    additional_materials: list[str] = Field(
        default_factory=list, description="Additional materials"
    )


class EstimateCreate(BaseModel):
    """Schema for creating a new estimate."""

    customer_id: Optional[UUID] = None
    job_name: str = Field(min_length=1, max_length=255)

    dimensions: DimensionsInput
    quantity: int = Field(ge=1, le=100000)
    materials: MaterialsInput
    operations: list[str] = Field(min_length=1)
    complexity_tier: int = Field(default=3, ge=1, le=5)
    rush_order: bool = False
    notes: Optional[str] = None


class EstimateUpdate(BaseModel):
    """Schema for updating an estimate."""

    job_name: Optional[str] = Field(None, min_length=1, max_length=255)
    customer_id: Optional[UUID] = None
    dimensions: Optional[DimensionsInput] = None
    quantity: Optional[int] = Field(None, ge=1, le=100000)
    materials: Optional[MaterialsInput] = None
    operations: Optional[list[str]] = None
    complexity_tier: Optional[int] = Field(None, ge=1, le=5)
    rush_order: Optional[bool] = None
    notes: Optional[str] = None
    status: Optional[EstimateStatus] = None
    quoted_price: Optional[Decimal] = None
    internal_notes: Optional[str] = None
    customer_notes: Optional[str] = None


class CostBreakdown(BaseModel):
    """Detailed cost breakdown."""

    material_costs: dict[str, Decimal]
    labor_hours: dict[str, float]
    labor_cost: Decimal
    overhead_cost: Decimal
    wastage_cost: Decimal
    complexity_adjustment: Decimal
    rush_premium: Decimal
    total_cost: Decimal
    unit_cost: Decimal
    confidence_interval: Optional[tuple[Decimal, Decimal]] = None
    confidence_level: Optional[float] = None
    audit_trail: Optional[list[dict[str, Any]]] = None


class EstimateResponse(BaseModel):
    """Schema for estimate response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reference_number: str
    job_name: str
    status: EstimateStatus
    complexity_tier: int

    customer_id: Optional[UUID]
    user_id: UUID

    inputs: dict[str, Any]
    outputs: Optional[dict[str, Any]]

    # Costs
    total_cost: Optional[Decimal]
    quoted_price: Optional[Decimal]
    unit_cost: Optional[Decimal] = None

    # Confidence
    confidence_low: Optional[Decimal]
    confidence_high: Optional[Decimal]
    confidence_level: Optional[float]

    # ML
    ml_enhanced: bool
    ml_prediction: Optional[Decimal]
    ml_confidence: Optional[float]
    ml_model_version: Optional[str]

    # Timestamps
    created_at: datetime
    updated_at: datetime
    calculated_at: Optional[datetime]
    quoted_at: Optional[datetime]
    completed_at: Optional[datetime]

    # Notes
    internal_notes: Optional[str]
    customer_notes: Optional[str]


class EstimateListResponse(BaseModel):
    """Schema for paginated estimate list."""

    items: list[EstimateResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class EstimateCalculateResponse(BaseModel):
    """Schema for calculate response (preview)."""

    breakdown: CostBreakdown
    confidence_interval: tuple[Decimal, Decimal]
    confidence_level: float
    ml_enhanced: bool
