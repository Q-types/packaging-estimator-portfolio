"""Feedback model for production actuals tracking."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text, Numeric, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from backend.app.models.estimate import Estimate
    from backend.app.models.user import User


class Feedback(Base, UUIDMixin):
    """Production feedback for ML training and accuracy tracking."""

    __tablename__ = "feedback"

    # Reference to estimate
    estimate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("estimates.id"), nullable=False, index=True
    )
    estimate: Mapped["Estimate"] = relationship("Estimate", back_populates="feedback")

    # Operation details
    operation: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    machine_id: Mapped[Optional[str]] = mapped_column(String(50))
    operator_id: Mapped[Optional[str]] = mapped_column(String(50))
    operator_skill_level: Mapped[Optional[int]] = mapped_column(
        Integer
    )  # 1-5 scale

    # Time tracking (in minutes)
    estimated_setup_time: Mapped[Optional[int]] = mapped_column(Integer)
    actual_setup_time: Mapped[Optional[int]] = mapped_column(Integer)
    estimated_run_time: Mapped[Optional[int]] = mapped_column(Integer)
    actual_run_time: Mapped[Optional[int]] = mapped_column(Integer)

    # Material tracking
    estimated_material_usage: Mapped[Optional[float]] = mapped_column(Numeric(10, 3))
    actual_material_usage: Mapped[Optional[float]] = mapped_column(Numeric(10, 3))
    wastage_units: Mapped[Optional[int]] = mapped_column(Integer)
    wastage_reason: Mapped[Optional[str]] = mapped_column(
        String(255)
    )  # setup, error, quality, etc.

    # Quality metrics
    first_pass_yield: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 4)
    )  # 0.0 - 1.0
    rework_time: Mapped[Optional[int]] = mapped_column(Integer)  # minutes
    defect_count: Mapped[Optional[int]] = mapped_column(Integer)

    # Environmental context (affects production time)
    batch_position: Mapped[Optional[int]] = mapped_column(
        Integer
    )  # 1st, 2nd, 3rd job of day
    shift: Mapped[Optional[str]] = mapped_column(String(20))  # morning, afternoon, night

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text)
    issues_encountered: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String))

    # Submission metadata
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    submitted_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    submitted_by_user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="feedback_submissions"
    )

    # Validation flag
    is_validated: Mapped[bool] = mapped_column(default=False)
    validated_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:
        return f"<Feedback {self.estimate_id}:{self.operation}>"

    @property
    def total_estimated_time(self) -> Optional[int]:
        """Get total estimated time (setup + run)."""
        if self.estimated_setup_time is not None and self.estimated_run_time is not None:
            return self.estimated_setup_time + self.estimated_run_time
        return None

    @property
    def total_actual_time(self) -> Optional[int]:
        """Get total actual time (setup + run)."""
        if self.actual_setup_time is not None and self.actual_run_time is not None:
            return self.actual_setup_time + self.actual_run_time
        return None

    @property
    def time_variance(self) -> Optional[int]:
        """Get variance between estimated and actual time (positive = over estimate)."""
        estimated = self.total_estimated_time
        actual = self.total_actual_time
        if estimated is not None and actual is not None:
            return actual - estimated
        return None

    @property
    def time_variance_percent(self) -> Optional[float]:
        """Get percentage variance between estimated and actual time."""
        estimated = self.total_estimated_time
        actual = self.total_actual_time
        if estimated is not None and actual is not None and estimated > 0:
            return ((actual - estimated) / estimated) * 100
        return None

    @property
    def material_variance(self) -> Optional[float]:
        """Get variance between estimated and actual material usage."""
        if self.estimated_material_usage is not None and self.actual_material_usage is not None:
            return float(self.actual_material_usage) - float(self.estimated_material_usage)
        return None
