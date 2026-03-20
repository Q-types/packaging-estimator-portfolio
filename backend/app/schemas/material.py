"""Pydantic schemas for materials."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MaterialCategory(str, Enum):
    """Categories of materials."""

    BOARD = "board"
    PAPER = "paper"
    CLOTH = "cloth"
    ADHESIVE = "adhesive"
    HARDWARE = "hardware"
    CONSUMABLE = "consumable"
    FINISHING = "finishing"


class UnitOfMeasure(str, Enum):
    """Units of measure for materials."""

    SQM = "sqm"
    LINEAR_M = "lm"
    SHEET = "sheet"
    KG = "kg"
    LITRE = "litre"
    UNIT = "unit"
    ROLL = "roll"


class MaterialCreate(BaseModel):
    """Schema for creating a material."""

    name: str = Field(min_length=1, max_length=255)
    sku: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    category: MaterialCategory
    unit: UnitOfMeasure
    current_price: Decimal = Field(ge=0)
    supplier_id: Optional[UUID] = None
    specifications: Optional[dict[str, Any]] = None


class MaterialUpdate(BaseModel):
    """Schema for updating a material."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    sku: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    category: Optional[MaterialCategory] = None
    unit: Optional[UnitOfMeasure] = None
    current_price: Optional[Decimal] = Field(None, ge=0)
    supplier_id: Optional[UUID] = None
    specifications: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class MaterialResponse(BaseModel):
    """Schema for material response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    sku: Optional[str]
    description: Optional[str]
    category: MaterialCategory
    unit: UnitOfMeasure
    current_price: Decimal
    supplier_id: Optional[UUID]
    specifications: Optional[dict[str, Any]]
    is_active: bool
    last_price_update: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class MaterialListResponse(BaseModel):
    """Schema for paginated material list."""

    items: list[MaterialResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class MaterialPriceCreate(BaseModel):
    """Schema for creating a material price history entry."""

    price: Decimal = Field(ge=0)
    effective_from: datetime
    effective_to: Optional[datetime] = None
    source: Optional[str] = None
    notes: Optional[str] = None


class MaterialPriceResponse(BaseModel):
    """Schema for material price history response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    material_id: UUID
    price: Decimal
    effective_from: datetime
    effective_to: Optional[datetime]
    source: Optional[str]
    notes: Optional[str]
    created_at: datetime


class BulkPriceUpdate(BaseModel):
    """Schema for bulk price update preview."""

    material_id: UUID
    material_name: str
    current_price: Decimal
    new_price: Decimal
    change_percent: float


class BulkPriceUpdateRequest(BaseModel):
    """Schema for confirming bulk price updates."""

    updates: list[BulkPriceUpdate]
    source: str = "manual_import"


class SupplierCreate(BaseModel):
    """Schema for creating a supplier."""

    name: str = Field(min_length=1, max_length=255)
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None


class SupplierResponse(BaseModel):
    """Schema for supplier response."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    contact_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    website: Optional[str]
    notes: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
