"""
Pydantic schemas for prospect API endpoints.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# =============================================================================
# Enums (mirroring database enums)
# =============================================================================


class ProspectStatus(str, Enum):
    """Status of a prospect in the sales pipeline."""

    NEW = "new"
    SCORED = "scored"
    QUALIFIED = "qualified"
    CONTACTED = "contacted"
    INTERESTED = "interested"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    WON = "won"
    LOST = "lost"
    DISQUALIFIED = "disqualified"


class ProspectTier(str, Enum):
    """Priority tier based on ML scoring."""

    HOT = "hot"
    WARM = "warm"
    COOL = "cool"
    COLD = "cold"


class PackagingNeed(str, Enum):
    """Estimated packaging need level."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


# =============================================================================
# Search Request/Response Schemas
# =============================================================================


class CompaniesHouseSearchRequest(BaseModel):
    """Request to search Companies House."""

    query: Optional[str] = Field(None, description="Search term (company name or number)")
    sic_codes: Optional[list[str]] = Field(None, description="Filter by SIC codes")
    location: Optional[str] = Field(None, description="Location filter (postcode area)")
    company_status: Optional[str] = Field("active", description="Company status filter")
    company_type: Optional[str] = Field(None, description="Company type (ltd, plc, etc.)")
    incorporated_from: Optional[str] = Field(
        None, description="Incorporation date from (YYYY-MM-DD)"
    )
    incorporated_to: Optional[str] = Field(
        None, description="Incorporation date to (YYYY-MM-DD)"
    )
    max_results: int = Field(100, ge=1, le=1000, description="Maximum results to fetch")
    auto_score: bool = Field(True, description="Automatically score results")
    auto_enrich: bool = Field(False, description="Fetch full company details")

    model_config = ConfigDict(extra="forbid")


class CompanySearchResult(BaseModel):
    """Single company from search results."""

    company_number: str
    company_name: str
    company_status: Optional[str] = None
    company_type: Optional[str] = None
    date_of_creation: Optional[str] = None
    address_snippet: Optional[str] = None
    sic_codes: Optional[list[str]] = None


class CompaniesHouseSearchResponse(BaseModel):
    """Response from Companies House search."""

    total_results: int
    items_fetched: int
    prospects_created: int
    prospects_updated: int
    search_id: UUID
    results: list[CompanySearchResult]

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Prospect CRUD Schemas
# =============================================================================


class ProspectBase(BaseModel):
    """Base prospect fields."""

    company_number: str = Field(..., max_length=8)
    company_name: str = Field(..., max_length=500)
    company_status: Optional[str] = None
    company_type: Optional[str] = None

    # Address
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    locality: Optional[str] = None
    region: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "United Kingdom"

    # Industry
    sic_codes: Optional[list[str]] = None
    primary_sic_code: Optional[str] = None
    industry_sector: Optional[str] = None

    # Web presence
    website: Optional[str] = None

    # Notes
    notes: Optional[str] = None


class ProspectCreate(ProspectBase):
    """Schema for creating a prospect."""

    model_config = ConfigDict(extra="forbid")


class ProspectUpdate(BaseModel):
    """Schema for updating a prospect."""

    status: Optional[ProspectStatus] = None
    assigned_to: Optional[UUID] = None
    notes: Optional[str] = None
    website: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class ProspectScoreDetail(BaseModel):
    """Detailed scoring breakdown."""

    total_score: float = Field(..., ge=0, le=100)
    tier: ProspectTier

    # Component scores
    industry_score: float = Field(0, ge=0, le=100)
    age_score: float = Field(0, ge=0, le=100)
    size_score: float = Field(0, ge=0, le=100)
    geography_score: float = Field(0, ge=0, le=100)
    web_presence_score: float = Field(0, ge=0, le=100)
    bespoke_fit_score: float = Field(0, ge=0, le=100, description="Fit for PackagePro bespoke packaging")

    # ML contribution
    ml_model_score: Optional[float] = Field(None, ge=0, le=100)
    ml_model_version: Optional[str] = None

    # Packaging assessment
    packaging_need: PackagingNeed = PackagingNeed.UNKNOWN
    packaging_need_reason: Optional[str] = None

    # Bespoke fit (PackagePro specific)
    bespoke_fit_reason: Optional[str] = Field(None, description="Why they're good/bad for bespoke packaging")

    # Exclusion (competitors)
    is_excluded: bool = Field(False, description="Excluded as competitor/packaging manufacturer")
    exclusion_reason: Optional[str] = Field(None, description="Why excluded")

    # Cluster assignment
    cluster_id: Optional[int] = None
    cluster_name: Optional[str] = None

    scored_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProspectResponse(ProspectBase):
    """Full prospect response with scoring."""

    id: UUID

    # Dates
    date_of_creation: Optional[datetime] = None
    company_age_years: Optional[float] = None

    # Size indicators
    officer_count: int = 0
    active_officer_count: int = 0
    filing_count: int = 0
    has_charges: bool = False
    has_insolvency_history: bool = False
    has_website: bool = False
    has_https: bool = False

    # Scoring
    prospect_score: Optional[float] = None
    tier: Optional[ProspectTier] = None
    packaging_need: PackagingNeed = PackagingNeed.UNKNOWN
    bespoke_fit_score: Optional[float] = Field(None, description="Bespoke packaging fit score")
    bespoke_fit_reason: Optional[str] = Field(None, description="Bespoke fit explanation")

    # Exclusion
    is_excluded: bool = Field(False, description="Excluded (competitor/packaging manufacturer)")
    exclusion_reason: Optional[str] = Field(None, description="Exclusion reason")

    # Clustering
    cluster_id: Optional[int] = None
    cluster_name: Optional[str] = None

    # Pipeline
    status: ProspectStatus = ProspectStatus.NEW
    assigned_to: Optional[UUID] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime
    last_scored_at: Optional[datetime] = None
    last_contacted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProspectDetailResponse(ProspectResponse):
    """Detailed prospect response with full scoring breakdown."""

    score_detail: Optional[ProspectScoreDetail] = None
    recent_activities: list[dict] = Field(default_factory=list)
    raw_data: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Batch Operations
# =============================================================================


class BatchScoreRequest(BaseModel):
    """Request to score multiple prospects."""

    prospect_ids: Optional[list[UUID]] = Field(
        None, description="Specific prospects to score (None = all unscored)"
    )
    rescore: bool = Field(False, description="Rescore already scored prospects")
    max_batch_size: int = Field(500, ge=1, le=5000)

    model_config = ConfigDict(extra="forbid")


class BatchScoreResponse(BaseModel):
    """Response from batch scoring."""

    total_scored: int
    by_tier: dict[str, int]
    average_score: float
    top_prospects: list[ProspectResponse]

    model_config = ConfigDict(from_attributes=True)


class BatchEnrichRequest(BaseModel):
    """Request to enrich prospects with additional data."""

    prospect_ids: Optional[list[UUID]] = Field(
        None, description="Specific prospects to enrich"
    )
    max_batch_size: int = Field(100, ge=1, le=500)
    include_officers: bool = Field(True)
    include_filings: bool = Field(True)
    include_charges: bool = Field(True)

    model_config = ConfigDict(extra="forbid")


class BatchEnrichResponse(BaseModel):
    """Response from batch enrichment."""

    total_enriched: int
    api_calls_made: int
    duration_seconds: float

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# List/Filter Schemas
# =============================================================================


class ProspectFilter(BaseModel):
    """Filters for prospect list."""

    status: Optional[list[ProspectStatus]] = None
    tier: Optional[list[ProspectTier]] = None
    packaging_need: Optional[list[PackagingNeed]] = None
    cluster_id: Optional[list[int]] = None

    region: Optional[str] = None
    industry_sector: Optional[str] = None
    sic_code: Optional[str] = None

    min_score: Optional[float] = Field(None, ge=0, le=100)
    max_score: Optional[float] = Field(None, ge=0, le=100)

    company_status: Optional[str] = Field("active")
    assigned_to: Optional[UUID] = None
    unassigned_only: bool = False

    search: Optional[str] = Field(None, description="Search company name")

    model_config = ConfigDict(extra="forbid")


class ProspectListResponse(BaseModel):
    """Paginated prospect list response."""

    items: list[ProspectResponse]
    total: int
    page: int
    page_size: int
    pages: int

    # Aggregations
    by_tier: dict[str, int]
    by_status: dict[str, int]
    average_score: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Activity Schemas
# =============================================================================


class ProspectActivityCreate(BaseModel):
    """Create a prospect activity."""

    activity_type: str = Field(..., max_length=50)
    description: str
    extra_data: Optional[dict] = None

    model_config = ConfigDict(extra="forbid")


class ProspectActivityResponse(BaseModel):
    """Prospect activity response."""

    id: UUID
    activity_type: str
    description: str
    user_id: Optional[UUID] = None
    extra_data: Optional[dict] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# Statistics Schemas
# =============================================================================


class ProspectStats(BaseModel):
    """Prospect statistics."""

    total_prospects: int
    by_status: dict[str, int]
    by_tier: dict[str, int]
    by_packaging_need: dict[str, int]

    average_score: Optional[float] = None
    median_score: Optional[float] = None

    top_industries: list[dict[str, Any]]
    top_regions: list[dict[str, Any]]

    recent_searches: int
    searches_this_week: int

    model_config = ConfigDict(from_attributes=True)
