"""Customer model for client information."""

from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.app.models.estimate import Estimate


class Customer(Base, UUIDMixin, TimestampMixin):
    """Customer/client information."""

    __tablename__ = "customers"

    # Basic info
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    contact_name: Mapped[Optional[str]] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(50))

    # Address
    address_line1: Mapped[Optional[str]] = mapped_column(String(255))
    address_line2: Mapped[Optional[str]] = mapped_column(String(255))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    postal_code: Mapped[Optional[str]] = mapped_column(String(20))
    country: Mapped[str] = mapped_column(String(100), default="UK")

    # Additional info
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    estimates: Mapped[list["Estimate"]] = relationship(
        "Estimate", back_populates="customer", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<Customer {self.name}>"

    @property
    def full_address(self) -> str:
        """Get formatted full address."""
        parts = [
            self.address_line1,
            self.address_line2,
            self.city,
            self.postal_code,
            self.country,
        ]
        return ", ".join(p for p in parts if p)
