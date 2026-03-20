"""Material and supplier models for pricing management."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text, Numeric, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    pass


class MaterialCategory(str, Enum):
    """Categories of materials."""

    BOARD = "board"  # Dutch grey board, greyboard, etc.
    PAPER = "paper"  # Cover papers, liner papers
    CLOTH = "cloth"  # Buckram, book cloth
    ADHESIVE = "adhesive"  # Glue, tape
    HARDWARE = "hardware"  # Magnets, ribbons, closures
    CONSUMABLE = "consumable"  # Other consumables
    FINISHING = "finishing"  # Foil, lamination film


class UnitOfMeasure(str, Enum):
    """Units of measure for materials."""

    SQM = "sqm"  # Square meters
    LINEAR_M = "lm"  # Linear meters
    SHEET = "sheet"  # Per sheet
    KG = "kg"  # Kilograms
    LITRE = "litre"  # Litres
    UNIT = "unit"  # Per unit (magnets, etc.)
    ROLL = "roll"  # Per roll


class Supplier(Base, UUIDMixin, TimestampMixin):
    """Material supplier information."""

    __tablename__ = "suppliers"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    contact_name: Mapped[Optional[str]] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(50))
    website: Mapped[Optional[str]] = mapped_column(String(255))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    materials: Mapped[list["Material"]] = relationship(
        "Material", back_populates="supplier", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<Supplier {self.name}>"


class Material(Base, UUIDMixin, TimestampMixin):
    """Material/consumable for packaging production."""

    __tablename__ = "materials"

    # Identification
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    sku: Mapped[Optional[str]] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Classification
    category: Mapped[MaterialCategory] = mapped_column(
        String(50), nullable=False, index=True
    )
    unit: Mapped[UnitOfMeasure] = mapped_column(String(20), nullable=False)

    # Pricing (current price for quick access, history in MaterialPrice)
    current_price: Mapped[float] = mapped_column(
        Numeric(10, 4), nullable=False, default=0.0
    )

    # Supplier
    supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("suppliers.id")
    )
    supplier: Mapped[Optional["Supplier"]] = relationship(
        "Supplier", back_populates="materials"
    )

    # Specifications (varies by material type)
    specifications = mapped_column(
        JSONB, nullable=True, default=None
    )  # JSONB: thickness, gsm, color, etc.

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_price_update: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    price_history: Mapped[list["MaterialPrice"]] = relationship(
        "MaterialPrice",
        back_populates="material",
        lazy="dynamic",
        order_by="MaterialPrice.effective_from.desc()",
    )

    def __repr__(self) -> str:
        return f"<Material {self.name} ({self.sku})>"


class MaterialPrice(Base, UUIDMixin):
    """Historical price records for materials."""

    __tablename__ = "material_prices"

    # Material reference
    material_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("materials.id"), nullable=False, index=True
    )
    material: Mapped["Material"] = relationship(
        "Material", back_populates="price_history"
    )

    # Price
    price: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)

    # Validity period
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Source/audit
    source: Mapped[Optional[str]] = mapped_column(
        String(255)
    )  # e.g., "supplier_datasheet", "manual_entry"
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    def __repr__(self) -> str:
        return f"<MaterialPrice {self.material_id}: £{self.price}>"

    @property
    def is_current(self) -> bool:
        """Check if this price is currently active."""
        now = datetime.now()
        return self.effective_from <= now and (
            self.effective_to is None or self.effective_to > now
        )
