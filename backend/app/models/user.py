"""User model for authentication and authorization."""

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from backend.app.models.estimate import Estimate
    from backend.app.models.feedback import Feedback


class UserRole(str, Enum):
    """User roles for authorization."""

    ADMIN = "admin"  # Full access
    ESTIMATOR = "estimator"  # Create/view estimates
    PRODUCTION = "production"  # Submit feedback only
    VIEWER = "viewer"  # Read-only access


class User(Base, UUIDMixin, TimestampMixin):
    """User account for authentication."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(String(50), default=UserRole.VIEWER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    estimates: Mapped[list["Estimate"]] = relationship(
        "Estimate", back_populates="user", lazy="dynamic"
    )
    feedback_submissions: Mapped[list["Feedback"]] = relationship(
        "Feedback", back_populates="submitted_by_user", lazy="dynamic"
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN

    @property
    def can_create_estimates(self) -> bool:
        """Check if user can create estimates."""
        return self.role in (UserRole.ADMIN, UserRole.ESTIMATOR)

    @property
    def can_submit_feedback(self) -> bool:
        """Check if user can submit production feedback."""
        return self.role in (UserRole.ADMIN, UserRole.ESTIMATOR, UserRole.PRODUCTION)
