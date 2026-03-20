"""ML model registry for tracking trained models."""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, Boolean, LargeBinary
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin, UUIDMixin


class MLModel(Base, UUIDMixin, TimestampMixin):
    """
    Registry of trained ML models.

    Tracks model versions, metrics, and allows for A/B testing
    and rollback to previous versions.
    """

    __tablename__ = "ml_models"

    # Identification
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # Model type
    model_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g., "HistGradientBoostingRegressor"
    target_variable: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g., "production_time"

    # Training info
    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    training_samples: Mapped[int] = mapped_column(nullable=False)
    feature_names: Mapped[list[str]] = mapped_column(JSONB, nullable=False)

    # Performance metrics
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    """
    Expected structure:
    {
        "mae": float,  # Mean Absolute Error
        "rmse": float,  # Root Mean Square Error
        "mape": float,  # Mean Absolute Percentage Error
        "r2": float,  # R-squared
        "coverage_80": float,  # % of actuals within 80% CI
        "coverage_90": float,  # % of actuals within 90% CI
        "cv_scores": [float],  # Cross-validation scores
    }
    """

    # Hyperparameters
    hyperparameters: Mapped[Optional[dict]] = mapped_column(JSONB)
    """
    Model hyperparameters used for training.
    """

    # Model storage
    model_blob: Mapped[Optional[bytes]] = mapped_column(
        LargeBinary
    )  # Serialized model (joblib)
    model_path: Mapped[Optional[str]] = mapped_column(
        String(500)
    )  # Alternative: file path

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_production: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    deactivated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # A/B testing
    traffic_percentage: Mapped[int] = mapped_column(
        default=0
    )  # % of predictions using this model

    # Audit
    trained_by: Mapped[Optional[str]] = mapped_column(String(255))
    notes: Mapped[Optional[str]] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"<MLModel {self.name} v{self.version}>"

    @property
    def mae(self) -> Optional[float]:
        """Get Mean Absolute Error."""
        return self.metrics.get("mae")

    @property
    def coverage(self) -> Optional[float]:
        """Get 80% confidence interval coverage."""
        return self.metrics.get("coverage_80")

    def meets_quality_threshold(
        self, max_mae: float = 0.15, min_coverage: float = 0.80
    ) -> bool:
        """
        Check if model meets quality thresholds.

        Args:
            max_mae: Maximum acceptable MAE (as proportion of mean).
            min_coverage: Minimum acceptable confidence interval coverage.

        Returns:
            True if model meets all thresholds.
        """
        if self.mae is None or self.coverage is None:
            return False
        return self.mae <= max_mae and self.coverage >= min_coverage
