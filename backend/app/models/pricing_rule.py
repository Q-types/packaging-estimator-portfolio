"""Pricing rule model for calculation expressions."""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import String, Text, DateTime, Integer, Boolean
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDMixin


class RuleCategory(str, Enum):
    """Categories of pricing rules."""

    FACTORY_CONSTANT = "factory_constant"  # Fixed values (machine speeds, etc.)
    CUSTOMER_VARIABLE = "customer_variable"  # User inputs (dimensions, quantity)
    CALCULATED = "calculated"  # Derived from other variables
    MATERIAL_COST = "material_cost"  # Material pricing
    LABOR_TIME = "labor_time"  # Time calculations
    OVERHEAD = "overhead"  # Overhead allocations


class PricingRule(Base, UUIDMixin, TimestampMixin):
    """
    Pricing rule defining how to calculate a variable.

    Expressions are evaluated by SafeExpressionEvaluator - NO eval().

    Example rules:
    - name: "board_area"
      expression: "(flat_width + 2 * margin) * (flat_height + 2 * margin) / 1000000"
      dependencies: ["flat_width", "flat_height", "margin"]

    - name: "wastage_units"
      expression: "quantity * 0.05 + 50"
      dependencies: ["quantity"]

    - name: "cutting_time"
      expression: "setup_time_cutting + (quantity / cutting_speed)"
      dependencies: ["setup_time_cutting", "quantity", "cutting_speed"]
    """

    __tablename__ = "pricing_rules"

    # Identification
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    display_name: Mapped[Optional[str]] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Classification
    category: Mapped[RuleCategory] = mapped_column(
        String(50), nullable=False, index=True
    )

    # Expression (parsed by SafeExpressionEvaluator)
    expression: Mapped[str] = mapped_column(Text, nullable=False)
    """
    Safe mathematical expression that can reference other variables.
    Examples:
    - "quantity * 0.05 + 50"
    - "board_area * board_price_per_sqm"
    - "max(min_setup_time, quantity / machine_speed)"
    - "base_cost * 1.5 if rush_order else base_cost"
    """

    # Dependencies for evaluation order
    dependencies: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String))
    """List of variable names this rule depends on for evaluation order."""

    # Default value (if expression fails or for constants)
    default_value: Mapped[Optional[float]] = mapped_column()

    # Unit of measure
    unit: Mapped[Optional[str]] = mapped_column(
        String(50)
    )  # e.g., "£", "hours", "sqm", "units"

    # Versioning
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    superseded_by: Mapped[Optional[str]] = mapped_column(
        String(100)
    )  # Name of replacing rule

    # Validity period (for price changes)
    effective_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Audit
    created_by: Mapped[Optional[str]] = mapped_column(String(255))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"<PricingRule {self.name} v{self.version}>"

    @property
    def is_constant(self) -> bool:
        """Check if this is a simple constant (no dependencies)."""
        return not self.dependencies or len(self.dependencies) == 0

    @property
    def is_current(self) -> bool:
        """Check if this rule is currently active."""
        if not self.is_active:
            return False
        now = datetime.now()
        if self.effective_from and now < self.effective_from:
            return False
        if self.effective_to and now > self.effective_to:
            return False
        return True
