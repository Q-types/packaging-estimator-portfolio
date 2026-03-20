"""
Prospect models for Companies House search and scoring.

Stores prospective clients from Companies House with ML-based scoring
and cluster assignments for targeted advertising.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.base import Base, TimestampMixin, UUIDMixin


class ProspectStatus(str, Enum):
    """Status of a prospect in the sales pipeline."""

    NEW = "new"                    # Just imported from Companies House
    SCORED = "scored"              # ML scoring complete
    QUALIFIED = "qualified"        # Manually qualified by sales
    CONTACTED = "contacted"        # Initial contact made
    INTERESTED = "interested"      # Showed interest
    PROPOSAL = "proposal"          # Proposal sent
    NEGOTIATION = "negotiation"    # In negotiation
    WON = "won"                    # Converted to customer
    LOST = "lost"                  # Did not convert
    DISQUALIFIED = "disqualified"  # Not a fit


class ProspectTier(str, Enum):
    """Priority tier based on ML scoring."""

    HOT = "hot"      # Score >= 75
    WARM = "warm"    # Score 60-74
    COOL = "cool"    # Score 45-59
    COLD = "cold"    # Score < 45


class PackagingNeed(str, Enum):
    """Estimated packaging need level based on industry."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class Prospect(Base, UUIDMixin, TimestampMixin):
    """
    Prospective client from Companies House.

    Stores company data, ML scores, and sales pipeline status.
    """

    __tablename__ = "prospects"

    # Companies House identifiers
    company_number: Mapped[str] = mapped_column(
        String(8), unique=True, index=True, nullable=False
    )
    company_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)

    # Company details
    company_status: Mapped[Optional[str]] = mapped_column(String(50))
    company_type: Mapped[Optional[str]] = mapped_column(String(100))
    date_of_creation: Mapped[Optional[datetime]] = mapped_column(DateTime)
    date_of_cessation: Mapped[Optional[datetime]] = mapped_column(DateTime)
    jurisdiction: Mapped[Optional[str]] = mapped_column(String(50))

    # Address
    address_line_1: Mapped[Optional[str]] = mapped_column(String(255))
    address_line_2: Mapped[Optional[str]] = mapped_column(String(255))
    locality: Mapped[Optional[str]] = mapped_column(String(100))
    region: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), index=True)
    country: Mapped[str] = mapped_column(String(100), default="United Kingdom")

    # Industry classification
    sic_codes: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String(10)))
    primary_sic_code: Mapped[Optional[str]] = mapped_column(String(10), index=True)
    industry_sector: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    packaging_need: Mapped[PackagingNeed] = mapped_column(
        SQLEnum(PackagingNeed, values_callable=lambda x: [e.value for e in x]),
        default=PackagingNeed.UNKNOWN
    )
    packaging_need_reason: Mapped[Optional[str]] = mapped_column(String(255))

    # Company size indicators
    officer_count: Mapped[int] = mapped_column(Integer, default=0)
    active_officer_count: Mapped[int] = mapped_column(Integer, default=0)
    filing_count: Mapped[int] = mapped_column(Integer, default=0)
    has_charges: Mapped[bool] = mapped_column(Boolean, default=False)
    has_insolvency_history: Mapped[bool] = mapped_column(Boolean, default=False)

    # Web presence (from external enrichment)
    website: Mapped[Optional[str]] = mapped_column(String(500))
    has_website: Mapped[bool] = mapped_column(Boolean, default=False)
    has_https: Mapped[bool] = mapped_column(Boolean, default=False)

    # Derived features
    company_age_years: Mapped[Optional[float]] = mapped_column(Float)

    # ML Scoring
    prospect_score: Mapped[Optional[float]] = mapped_column(Float, index=True)
    tier: Mapped[Optional[ProspectTier]] = mapped_column(
        SQLEnum(ProspectTier, values_callable=lambda x: [e.value for e in x]),
        index=True
    )

    # Score components
    industry_score: Mapped[Optional[float]] = mapped_column(Float)
    age_score: Mapped[Optional[float]] = mapped_column(Float)
    size_score: Mapped[Optional[float]] = mapped_column(Float)
    geography_score: Mapped[Optional[float]] = mapped_column(Float)
    web_presence_score: Mapped[Optional[float]] = mapped_column(Float)
    bespoke_fit_score: Mapped[Optional[float]] = mapped_column(Float)  # PackagePro bespoke fit
    ml_model_score: Mapped[Optional[float]] = mapped_column(Float)

    # Bespoke fit assessment
    bespoke_fit_reason: Mapped[Optional[str]] = mapped_column(String(500))

    # Exclusion flags (competitors/self-sufficient)
    is_excluded: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    exclusion_reason: Mapped[Optional[str]] = mapped_column(String(255))

    # Clustering
    cluster_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    cluster_name: Mapped[Optional[str]] = mapped_column(String(100))
    cluster_confidence: Mapped[Optional[float]] = mapped_column(Float)

    # Sales pipeline
    status: Mapped[ProspectStatus] = mapped_column(
        SQLEnum(ProspectStatus, values_callable=lambda x: [e.value for e in x]),
        default=ProspectStatus.NEW, index=True
    )
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )

    # Tracking
    last_enriched_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_scored_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_contacted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Notes and raw data
    notes: Mapped[Optional[str]] = mapped_column(Text)
    raw_data: Mapped[Optional[dict]] = mapped_column(JSON)  # Store full API response

    # Relationships
    scores: Mapped[list["ProspectScore"]] = relationship(
        "ProspectScore", back_populates="prospect", cascade="all, delete-orphan"
    )
    activities: Mapped[list["ProspectActivity"]] = relationship(
        "ProspectActivity", back_populates="prospect", cascade="all, delete-orphan"
    )

    # Unique constraint on company number
    __table_args__ = (
        UniqueConstraint("company_number", name="uq_prospect_company_number"),
    )

    def __repr__(self) -> str:
        return f"<Prospect {self.company_name} ({self.company_number})>"

    @property
    def full_address(self) -> str:
        """Get formatted full address."""
        parts = [
            self.address_line_1,
            self.address_line_2,
            self.locality,
            self.region,
            self.postal_code,
            self.country,
        ]
        return ", ".join(p for p in parts if p)

    @property
    def is_active_company(self) -> bool:
        """Check if company is currently active."""
        return self.company_status == "active" and not self.date_of_cessation


class ProspectScore(Base, UUIDMixin, TimestampMixin):
    """
    Historical record of prospect scoring.

    Tracks how scores change over time as ICP profile is refined.
    """

    __tablename__ = "prospect_scores"

    prospect_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prospects.id"), index=True
    )

    # Overall score
    total_score: Mapped[float] = mapped_column(Float, nullable=False)
    tier: Mapped[ProspectTier] = mapped_column(
        SQLEnum(ProspectTier, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )

    # Component scores (all 0-100)
    industry_score: Mapped[float] = mapped_column(Float)
    age_score: Mapped[float] = mapped_column(Float)
    size_score: Mapped[float] = mapped_column(Float)
    geography_score: Mapped[float] = mapped_column(Float)
    web_presence_score: Mapped[float] = mapped_column(Float)

    # ML model contribution
    ml_model_score: Mapped[Optional[float]] = mapped_column(Float)
    ml_model_version: Mapped[Optional[str]] = mapped_column(String(50))

    # Scoring metadata
    icp_profile_version: Mapped[Optional[str]] = mapped_column(String(50))
    scoring_config: Mapped[Optional[dict]] = mapped_column(JSON)

    # Relationship
    prospect: Mapped["Prospect"] = relationship("Prospect", back_populates="scores")

    def __repr__(self) -> str:
        return f"<ProspectScore {self.total_score:.1f} ({self.tier.value})>"


class ProspectActivity(Base, UUIDMixin, TimestampMixin):
    """
    Activity log for prospects.

    Tracks all interactions and status changes.
    """

    __tablename__ = "prospect_activities"

    prospect_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prospects.id"), index=True
    )

    # Activity details
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Who performed the activity
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )

    # Additional data
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON)

    # Relationship
    prospect: Mapped["Prospect"] = relationship("Prospect", back_populates="activities")

    def __repr__(self) -> str:
        return f"<ProspectActivity {self.activity_type}>"


class ProspectSearch(Base, UUIDMixin, TimestampMixin):
    """
    Record of Companies House searches performed.

    Tracks search parameters and results for audit and optimization.
    """

    __tablename__ = "prospect_searches"

    # Search parameters
    query: Mapped[Optional[str]] = mapped_column(String(500))
    sic_codes: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String(10)))
    location: Mapped[Optional[str]] = mapped_column(String(100))
    company_status: Mapped[Optional[str]] = mapped_column(String(50))
    incorporated_from: Mapped[Optional[datetime]] = mapped_column(DateTime)
    incorporated_to: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Results
    total_results: Mapped[int] = mapped_column(Integer, default=0)
    results_fetched: Mapped[int] = mapped_column(Integer, default=0)
    prospects_created: Mapped[int] = mapped_column(Integer, default=0)
    prospects_updated: Mapped[int] = mapped_column(Integer, default=0)

    # Performance
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float)
    api_calls_made: Mapped[int] = mapped_column(Integer, default=0)

    # Who ran the search
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )

    # Status
    status: Mapped[str] = mapped_column(String(20), default="pending")
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"<ProspectSearch {self.query or 'advanced'} ({self.total_results} results)>"
