"""Estimate model for packaging cost estimates."""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import String, Text, Numeric, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.app.models.user import User
    from backend.app.models.customer import Customer
    from backend.app.models.feedback import Feedback


class EstimateStatus(str, Enum):
    """Status of an estimate."""

    DRAFT = "draft"  # Being created
    QUOTED = "quoted"  # Quote sent to customer
    WON = "won"  # Customer accepted
    LOST = "lost"  # Customer declined
    COMPLETED = "completed"  # Job finished
    CANCELLED = "cancelled"  # Cancelled


class Estimate(Base, UUIDMixin, TimestampMixin):
    """Cost estimate for a packaging job."""

    __tablename__ = "estimates"

    # Reference
    reference_number: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    job_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[EstimateStatus] = mapped_column(
        String(50), default=EstimateStatus.DRAFT, nullable=False, index=True
    )

    # Complexity tier (1-5, affects pricing)
    complexity_tier: Mapped[int] = mapped_column(Integer, default=3)

    # Relations
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), index=True
    )
    customer: Mapped[Optional["Customer"]] = relationship(
        "Customer", back_populates="estimates"
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    user: Mapped["User"] = relationship("User", back_populates="estimates")

    # Input parameters (JSONB for flexibility)
    inputs: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    """
    Expected structure:
    {
        "dimensions": {
            "flat_width": float,
            "flat_height": float,
            "outer_wrap_width": float,
            "outer_wrap_height": float,
            "liner_width": float,
            "liner_height": float,
            "spine_depth": float
        },
        "quantity": int,
        "materials": {
            "board_type": str,
            "board_thickness": float,
            "outer_wrap": str,
            "liner": str,
            "additional": [str]
        },
        "operations": [str],
        "rush_order": bool,
        "notes": str
    }
    """

    # Calculated outputs (JSONB)
    outputs: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, default=None)
    """
    Expected structure:
    {
        "material_costs": {
            "board": float,
            "outer_wrap": float,
            "liner": float,
            "adhesive": float,
            "additional": float,
            "total": float
        },
        "labor_hours": {
            "cutting": float,
            "wrapping": float,
            "creasing": float,
            ...
            "total": float
        },
        "labor_cost": float,
        "overhead_cost": float,
        "wastage_cost": float,
        "total_cost": float,
        "unit_cost": float,
        "breakdown": {...}  # Detailed calculation breakdown
    }
    """

    # Confidence interval
    confidence_low: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    confidence_high: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    confidence_level: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 4)
    )  # 0.0 - 1.0

    # ML enhancement
    ml_prediction: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    ml_confidence: Mapped[Optional[float]] = mapped_column(Numeric(5, 4))
    ml_model_version: Mapped[Optional[str]] = mapped_column(String(50))
    ml_enhanced: Mapped[bool] = mapped_column(default=False)

    # Final pricing
    total_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    quoted_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    margin_percent: Mapped[Optional[float]] = mapped_column(Numeric(5, 2))

    # Status timestamps
    calculated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    quoted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Notes
    internal_notes: Mapped[Optional[str]] = mapped_column(Text)
    customer_notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    feedback: Mapped[list["Feedback"]] = relationship(
        "Feedback", back_populates="estimate", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<Estimate {self.reference_number}>"

    @property
    def quantity(self) -> int:
        """Get quantity from inputs."""
        return self.inputs.get("quantity", 0)

    @property
    def dimensions(self) -> dict:
        """Get dimensions from inputs."""
        return self.inputs.get("dimensions", {})

    @property
    def operations(self) -> list[str]:
        """Get operations from inputs."""
        return self.inputs.get("operations", [])

    @property
    def has_feedback(self) -> bool:
        """Check if any feedback has been submitted."""
        return self.feedback.count() > 0

    @property
    def confidence_interval(self) -> Optional[tuple[Decimal, Decimal]]:
        """Get confidence interval as tuple."""
        if self.confidence_low is not None and self.confidence_high is not None:
            return (self.confidence_low, self.confidence_high)
        return None

    def generate_reference(self) -> str:
        """Generate a unique reference number."""
        import random
        import string

        date_part = datetime.now().strftime("%Y%m%d")
        random_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"EST-{date_part}-{random_part}"
