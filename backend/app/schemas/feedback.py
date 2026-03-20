"""Pydantic schemas for feedback."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FeedbackCreate(BaseModel):
    """Schema for creating feedback."""

    estimate_id: UUID
    operation: str = Field(min_length=1, max_length=100)
    machine_id: Optional[str] = Field(None, max_length=50)
    operator_id: Optional[str] = Field(None, max_length=50)
    operator_skill_level: Optional[int] = Field(None, ge=1, le=5)

    # Time tracking (in minutes)
    estimated_setup_time: Optional[int] = Field(None, ge=0)
    actual_setup_time: Optional[int] = Field(None, ge=0)
    estimated_run_time: Optional[int] = Field(None, ge=0)
    actual_run_time: Optional[int] = Field(None, ge=0)

    # Material tracking
    estimated_material_usage: Optional[Decimal] = Field(None, ge=0)
    actual_material_usage: Optional[Decimal] = Field(None, ge=0)
    wastage_units: Optional[int] = Field(None, ge=0)
    wastage_reason: Optional[str] = Field(None, max_length=255)

    # Quality metrics
    first_pass_yield: Optional[float] = Field(None, ge=0, le=1)
    rework_time: Optional[int] = Field(None, ge=0)
    defect_count: Optional[int] = Field(None, ge=0)

    # Context
    batch_position: Optional[int] = Field(None, ge=1)
    shift: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None
    issues_encountered: Optional[list[str]] = None


class FeedbackUpdate(BaseModel):
    """Schema for updating feedback."""

    actual_setup_time: Optional[int] = Field(None, ge=0)
    actual_run_time: Optional[int] = Field(None, ge=0)
    actual_material_usage: Optional[Decimal] = Field(None, ge=0)
    wastage_units: Optional[int] = Field(None, ge=0)
    wastage_reason: Optional[str] = Field(None, max_length=255)
    first_pass_yield: Optional[float] = Field(None, ge=0, le=1)
    rework_time: Optional[int] = Field(None, ge=0)
    defect_count: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None
    issues_encountered: Optional[list[str]] = None


class FeedbackResponse(BaseModel):
    """Schema for feedback response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    estimate_id: UUID
    operation: str
    machine_id: Optional[str]
    operator_id: Optional[str]
    operator_skill_level: Optional[int]

    # Time tracking
    estimated_setup_time: Optional[int]
    actual_setup_time: Optional[int]
    estimated_run_time: Optional[int]
    actual_run_time: Optional[int]

    # Material tracking
    estimated_material_usage: Optional[Decimal]
    actual_material_usage: Optional[Decimal]
    wastage_units: Optional[int]
    wastage_reason: Optional[str]

    # Quality metrics
    first_pass_yield: Optional[float]
    rework_time: Optional[int]
    defect_count: Optional[int]

    # Context
    batch_position: Optional[int]
    shift: Optional[str]
    notes: Optional[str]
    issues_encountered: Optional[list[str]]

    # Validation
    is_validated: bool
    validated_by: Optional[UUID]
    validated_at: Optional[datetime]

    # Timestamps
    submitted_at: datetime
    submitted_by: Optional[UUID]


class FeedbackListResponse(BaseModel):
    """Schema for paginated feedback list."""

    items: list[FeedbackResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AccuracyMetrics(BaseModel):
    """Schema for estimation accuracy metrics."""

    total_feedback_entries: int
    operations_covered: list[str]

    # Time accuracy
    avg_time_variance_percent: float
    time_underestimates: int
    time_overestimates: int

    # Material accuracy
    avg_material_variance_percent: float

    # Quality metrics
    avg_first_pass_yield: float

    # By operation
    by_operation: dict[str, dict[str, float]]


class EstimateFeedbackSummary(BaseModel):
    """Summary of all feedback for an estimate."""

    estimate_id: UUID
    total_operations: int
    completed_operations: int

    total_estimated_time: int  # minutes
    total_actual_time: int  # minutes
    time_variance_percent: float

    total_estimated_material: Decimal
    total_actual_material: Decimal

    avg_first_pass_yield: float
    total_rework_time: int

    operations: list[FeedbackResponse]
