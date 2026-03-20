"""
Prospects API Router

Endpoints for Companies House search, prospect management, and ML scoring.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.db.session import get_db
from backend.app.models.prospect import (
    PackagingNeed,
    Prospect,
    ProspectActivity,
    ProspectScore,
    ProspectSearch,
    ProspectStatus,
    ProspectTier,
)
from backend.app.schemas.prospect import (
    BatchEnrichRequest,
    BatchEnrichResponse,
    BatchScoreRequest,
    BatchScoreResponse,
    CompaniesHouseSearchRequest,
    CompaniesHouseSearchResponse,
    CompanySearchResult,
    ProspectActivityCreate,
    ProspectActivityResponse,
    ProspectCreate,
    ProspectDetailResponse,
    ProspectFilter,
    ProspectListResponse,
    ProspectResponse,
    ProspectScoreDetail,
    ProspectStats,
    ProspectUpdate,
)
from backend.app.services.companies_house import CompaniesHouseClient
from backend.app.services.prospect_scoring import get_scoring_service, sic_to_sector

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()


# =============================================================================
# Companies House Search Endpoints
# =============================================================================


@router.post("/search", response_model=CompaniesHouseSearchResponse)
async def search_companies_house(
    request: CompaniesHouseSearchRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Search Companies House and import matching companies as prospects.

    Automatically scores prospects using the ICP model if auto_score=True.
    """
    api_key = settings.companies_house_api_key
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Companies House API key not configured",
        )

    start_time = datetime.utcnow()
    results = []
    prospects_created = 0
    prospects_updated = 0

    # Create search record
    search_record = ProspectSearch(
        query=request.query,
        sic_codes=request.sic_codes,
        location=request.location,
        company_status=request.company_status,
        status="in_progress",
    )
    db.add(search_record)
    await db.flush()

    try:
        async with CompaniesHouseClient(api_key=api_key) as client:
            # Perform search
            if request.query:
                search_response = await client.search_companies(
                    query=request.query,
                    items_per_page=min(request.max_results, 100),
                )
                items = search_response.items
                total_results = search_response.total_results
            else:
                # Advanced search with filters
                search_response = await client.advanced_search(
                    company_name=request.query,
                    company_status=request.company_status,
                    company_type=request.company_type,
                    sic_codes=request.sic_codes,
                    location=request.location,
                    incorporated_from=request.incorporated_from,
                    incorporated_to=request.incorporated_to,
                    size=min(request.max_results, 100),
                )
                items = search_response.items
                total_results = search_response.total_results

            # Process results
            for item in items:
                # Check if prospect already exists
                existing = await db.execute(
                    select(Prospect).where(
                        Prospect.company_number == item.company_number
                    )
                )
                existing_prospect = existing.scalar_one_or_none()

                if existing_prospect:
                    # Update existing
                    existing_prospect.company_name = item.company_name
                    existing_prospect.company_status = item.company_status
                    existing_prospect.company_type = item.company_type
                    prospects_updated += 1
                    prospect = existing_prospect
                else:
                    # Create new prospect
                    prospect = Prospect(
                        company_number=item.company_number,
                        company_name=item.company_name,
                        company_status=item.company_status,
                        company_type=item.company_type,
                        sic_codes=item.sic_codes,
                        primary_sic_code=item.sic_codes[0] if item.sic_codes else None,
                        status=ProspectStatus.NEW,
                    )

                    # Parse address if available
                    if item.address:
                        prospect.address_line_1 = item.address.address_line_1
                        prospect.address_line_2 = item.address.address_line_2
                        prospect.locality = item.address.locality
                        prospect.region = item.address.region
                        prospect.postal_code = item.address.postal_code
                        prospect.country = item.address.country or "United Kingdom"

                    # Parse creation date
                    if item.date_of_creation:
                        try:
                            prospect.date_of_creation = datetime.strptime(
                                item.date_of_creation, "%Y-%m-%d"
                            )
                            prospect.company_age_years = (
                                datetime.utcnow() - prospect.date_of_creation
                            ).days / 365.25
                        except ValueError:
                            pass

                    # Set industry sector
                    if prospect.primary_sic_code:
                        prospect.industry_sector = sic_to_sector(
                            prospect.primary_sic_code
                        )

                    # Set default enum values (lowercase to match DB)
                    prospect.packaging_need = PackagingNeed.UNKNOWN
                    prospect.status = ProspectStatus.NEW

                    db.add(prospect)
                    prospects_created += 1

                results.append(
                    CompanySearchResult(
                        company_number=item.company_number,
                        company_name=item.company_name,
                        company_status=item.company_status,
                        company_type=item.company_type,
                        date_of_creation=item.date_of_creation,
                        sic_codes=item.sic_codes,
                    )
                )

            # Update search record
            search_record.total_results = total_results
            search_record.results_fetched = len(results)
            search_record.prospects_created = prospects_created
            search_record.prospects_updated = prospects_updated
            search_record.duration_seconds = (
                datetime.utcnow() - start_time
            ).total_seconds()
            search_record.status = "completed"

            await db.commit()

            # Score prospects in background if requested
            if request.auto_score and prospects_created > 0:
                background_tasks.add_task(
                    _background_score_prospects,
                    [r.company_number for r in results],
                )

    except Exception as e:
        search_record.status = "failed"
        search_record.error_message = str(e)
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")

    return CompaniesHouseSearchResponse(
        total_results=total_results,
        items_fetched=len(results),
        prospects_created=prospects_created,
        prospects_updated=prospects_updated,
        search_id=search_record.id,
        results=results,
    )


async def _background_score_prospects(company_numbers: list[str]):
    """Background task to score prospects."""
    # This would need proper async DB session handling
    logger.info(f"Background scoring {len(company_numbers)} prospects")


# =============================================================================
# Prospect CRUD Endpoints
# =============================================================================


@router.get("", response_model=ProspectListResponse)
async def list_prospects(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: Optional[list[ProspectStatus]] = Query(None),
    tier: Optional[list[ProspectTier]] = Query(None),
    packaging_need: Optional[list[PackagingNeed]] = Query(None),
    region: Optional[str] = Query(None),
    industry_sector: Optional[str] = Query(None),
    min_score: Optional[float] = Query(None, ge=0, le=100),
    max_score: Optional[float] = Query(None, ge=0, le=100),
    min_bespoke_fit: Optional[float] = Query(None, ge=0, le=100, description="Minimum bespoke fit score"),
    exclude_competitors: bool = Query(True, description="Exclude packaging manufacturers/competitors"),
    search: Optional[str] = Query(None),
    sort_by: str = Query("prospect_score", pattern="^(prospect_score|created_at|company_name|bespoke_fit_score)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
):
    """
    List prospects with filtering, sorting, and pagination.

    By default, excludes competitors (packaging manufacturers).
    Use exclude_competitors=false to see all prospects.
    """
    # Build query
    query = select(Prospect)

    # Apply exclusion filter (default: exclude competitors)
    if exclude_competitors:
        query = query.where(Prospect.is_excluded == False)

    # Apply bespoke fit filter
    if min_bespoke_fit is not None:
        query = query.where(Prospect.bespoke_fit_score >= min_bespoke_fit)

    # Apply filters
    if status:
        query = query.where(Prospect.status.in_(status))
    if tier:
        query = query.where(Prospect.tier.in_(tier))
    if packaging_need:
        query = query.where(Prospect.packaging_need.in_(packaging_need))
    if region:
        query = query.where(Prospect.region.ilike(f"%{region}%"))
    if industry_sector:
        query = query.where(Prospect.industry_sector == industry_sector)
    if min_score is not None:
        query = query.where(Prospect.prospect_score >= min_score)
    if max_score is not None:
        query = query.where(Prospect.prospect_score <= max_score)
    if search:
        query = query.where(
            or_(
                Prospect.company_name.ilike(f"%{search}%"),
                Prospect.company_number.ilike(f"%{search}%"),
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply sorting
    sort_column = getattr(Prospect, sort_by)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc().nulls_last())
    else:
        query = query.order_by(sort_column.asc().nulls_last())

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    # Execute
    result = await db.execute(query)
    prospects = result.scalars().all()

    # Get aggregations
    tier_counts = {}
    status_counts = {}
    avg_score = None

    tier_query = select(
        Prospect.tier, func.count(Prospect.id)
    ).group_by(Prospect.tier)
    tier_result = await db.execute(tier_query)
    for tier_val, count in tier_result:
        if tier_val:
            tier_counts[tier_val.value] = count

    status_query = select(
        Prospect.status, func.count(Prospect.id)
    ).group_by(Prospect.status)
    status_result = await db.execute(status_query)
    for status_val, count in status_result:
        status_counts[status_val.value] = count

    avg_query = select(func.avg(Prospect.prospect_score))
    avg_result = await db.execute(avg_query)
    avg_score = avg_result.scalar()

    return ProspectListResponse(
        items=[ProspectResponse.model_validate(p) for p in prospects],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
        by_tier=tier_counts,
        by_status=status_counts,
        average_score=round(avg_score, 2) if avg_score else None,
    )


@router.get("/stats", response_model=ProspectStats)
async def get_prospect_stats(db: AsyncSession = Depends(get_db)):
    """Get prospect statistics and aggregations."""
    # Total count
    total_result = await db.execute(select(func.count(Prospect.id)))
    total = total_result.scalar()

    # By status
    status_query = select(
        Prospect.status, func.count(Prospect.id)
    ).group_by(Prospect.status)
    status_result = await db.execute(status_query)
    by_status = {s.value: c for s, c in status_result}

    # By tier
    tier_query = select(
        Prospect.tier, func.count(Prospect.id)
    ).group_by(Prospect.tier)
    tier_result = await db.execute(tier_query)
    by_tier = {t.value if t else "unscored": c for t, c in tier_result}

    # By packaging need
    need_query = select(
        Prospect.packaging_need, func.count(Prospect.id)
    ).group_by(Prospect.packaging_need)
    need_result = await db.execute(need_query)
    by_packaging_need = {n.value: c for n, c in need_result}

    # Scores
    avg_query = select(func.avg(Prospect.prospect_score))
    avg_result = await db.execute(avg_query)
    avg_score = avg_result.scalar()

    # Top industries
    industry_query = (
        select(Prospect.industry_sector, func.count(Prospect.id).label("count"))
        .where(Prospect.industry_sector.isnot(None))
        .group_by(Prospect.industry_sector)
        .order_by(func.count(Prospect.id).desc())
        .limit(10)
    )
    industry_result = await db.execute(industry_query)
    top_industries = [{"sector": s, "count": c} for s, c in industry_result]

    # Top regions
    region_query = (
        select(Prospect.region, func.count(Prospect.id).label("count"))
        .where(Prospect.region.isnot(None))
        .group_by(Prospect.region)
        .order_by(func.count(Prospect.id).desc())
        .limit(10)
    )
    region_result = await db.execute(region_query)
    top_regions = [{"region": r, "count": c} for r, c in region_result]

    # Recent searches
    search_count_query = select(func.count(ProspectSearch.id))
    search_result = await db.execute(search_count_query)
    recent_searches = search_result.scalar()

    return ProspectStats(
        total_prospects=total,
        by_status=by_status,
        by_tier=by_tier,
        by_packaging_need=by_packaging_need,
        average_score=round(avg_score, 2) if avg_score else None,
        median_score=None,  # Would need window function
        top_industries=top_industries,
        top_regions=top_regions,
        recent_searches=recent_searches or 0,
        searches_this_week=0,  # Would need date filter
    )


@router.get("/{prospect_id}", response_model=ProspectDetailResponse)
async def get_prospect(
    prospect_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed prospect information including scoring breakdown."""
    result = await db.execute(
        select(Prospect).where(Prospect.id == prospect_id)
    )
    prospect = result.scalar_one_or_none()

    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    # Get latest score
    score_result = await db.execute(
        select(ProspectScore)
        .where(ProspectScore.prospect_id == prospect_id)
        .order_by(ProspectScore.created_at.desc())
        .limit(1)
    )
    latest_score = score_result.scalar_one_or_none()

    # Get recent activities
    activities_result = await db.execute(
        select(ProspectActivity)
        .where(ProspectActivity.prospect_id == prospect_id)
        .order_by(ProspectActivity.created_at.desc())
        .limit(10)
    )
    activities = activities_result.scalars().all()

    response = ProspectDetailResponse.model_validate(prospect)

    if latest_score:
        response.score_detail = ProspectScoreDetail(
            total_score=latest_score.total_score,
            tier=latest_score.tier,
            industry_score=latest_score.industry_score,
            age_score=latest_score.age_score,
            size_score=latest_score.size_score,
            geography_score=latest_score.geography_score,
            web_presence_score=latest_score.web_presence_score,
            ml_model_score=latest_score.ml_model_score,
            ml_model_version=latest_score.ml_model_version,
            packaging_need=prospect.packaging_need,
            packaging_need_reason=prospect.packaging_need_reason,
            cluster_id=prospect.cluster_id,
            cluster_name=prospect.cluster_name,
            scored_at=latest_score.created_at,
        )

    response.recent_activities = [
        {
            "type": a.activity_type,
            "description": a.description,
            "created_at": a.created_at.isoformat(),
        }
        for a in activities
    ]

    return response


@router.patch("/{prospect_id}", response_model=ProspectResponse)
async def update_prospect(
    prospect_id: UUID,
    update: ProspectUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update prospect status, assignment, or notes."""
    result = await db.execute(
        select(Prospect).where(Prospect.id == prospect_id)
    )
    prospect = result.scalar_one_or_none()

    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    # Track changes for activity log
    changes = []

    if update.status and update.status != prospect.status:
        old_status = prospect.status
        prospect.status = update.status
        changes.append(f"Status changed from {old_status.value} to {update.status.value}")

    if update.assigned_to is not None:
        prospect.assigned_to = update.assigned_to
        changes.append("Assignment updated")

    if update.notes is not None:
        prospect.notes = update.notes
        changes.append("Notes updated")

    if update.website:
        prospect.website = update.website
        prospect.has_website = True
        prospect.has_https = update.website.startswith("https://")

    # Log activity
    if changes:
        activity = ProspectActivity(
            prospect_id=prospect_id,
            activity_type="update",
            description="; ".join(changes),
        )
        db.add(activity)

    await db.commit()
    await db.refresh(prospect)

    return ProspectResponse.model_validate(prospect)


# =============================================================================
# Scoring Endpoints
# =============================================================================


@router.post("/score", response_model=BatchScoreResponse)
async def score_prospects(
    request: BatchScoreRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Score prospects using the ICP model.

    If prospect_ids is None, scores all unscored prospects.
    """
    scoring_service = get_scoring_service()

    # Build query
    query = select(Prospect)

    if request.prospect_ids:
        query = query.where(Prospect.id.in_(request.prospect_ids))
    elif not request.rescore:
        query = query.where(Prospect.prospect_score.is_(None))

    query = query.limit(request.max_batch_size)

    result = await db.execute(query)
    prospects = result.scalars().all()

    scored_count = 0
    tier_counts = {"hot": 0, "warm": 0, "cool": 0, "cold": 0}
    total_score = 0.0
    top_prospects = []

    for prospect in prospects:
        # Score the prospect
        score_result = scoring_service.score_prospect(
            company_number=prospect.company_number,
            company_name=prospect.company_name,
            sic_codes=prospect.sic_codes,
            date_of_creation=prospect.date_of_creation,
            region=prospect.region,
            officer_count=prospect.officer_count,
            filing_count=prospect.filing_count,
            has_charges=prospect.has_charges,
            has_website=prospect.has_website,
            has_https=prospect.has_https,
        )

        # Update prospect
        prospect.prospect_score = score_result.total_score
        prospect.tier = score_result.tier
        prospect.industry_score = score_result.industry_score
        prospect.age_score = score_result.age_score
        prospect.size_score = score_result.size_score
        prospect.geography_score = score_result.geography_score
        prospect.web_presence_score = score_result.web_presence_score
        prospect.bespoke_fit_score = score_result.bespoke_fit_score
        prospect.ml_model_score = score_result.ml_model_score
        prospect.packaging_need = score_result.packaging_need
        prospect.packaging_need_reason = score_result.packaging_need_reason
        prospect.bespoke_fit_reason = score_result.bespoke_fit_reason
        prospect.is_excluded = score_result.is_excluded
        prospect.exclusion_reason = score_result.exclusion_reason
        prospect.cluster_id = score_result.cluster_id
        prospect.cluster_name = score_result.cluster_name
        prospect.cluster_confidence = score_result.cluster_confidence
        prospect.industry_sector = score_result.industry_sector
        prospect.last_scored_at = datetime.utcnow()

        # Set status based on exclusion
        if score_result.is_excluded:
            prospect.status = ProspectStatus.DISQUALIFIED
        else:
            prospect.status = ProspectStatus.SCORED

        # Create score record
        score_record = ProspectScore(
            prospect_id=prospect.id,
            total_score=score_result.total_score,
            tier=score_result.tier,
            industry_score=score_result.industry_score,
            age_score=score_result.age_score,
            size_score=score_result.size_score,
            geography_score=score_result.geography_score,
            web_presence_score=score_result.web_presence_score,
            ml_model_score=score_result.ml_model_score,
            ml_model_version=score_result.ml_model_version,
        )
        db.add(score_record)

        # Update counters
        scored_count += 1
        tier_counts[score_result.tier.value] += 1
        total_score += score_result.total_score

    await db.commit()

    # Get top prospects
    top_query = (
        select(Prospect)
        .where(Prospect.prospect_score.isnot(None))
        .order_by(Prospect.prospect_score.desc())
        .limit(10)
    )
    top_result = await db.execute(top_query)
    top_prospects = [
        ProspectResponse.model_validate(p) for p in top_result.scalars().all()
    ]

    return BatchScoreResponse(
        total_scored=scored_count,
        by_tier=tier_counts,
        average_score=round(total_score / scored_count, 2) if scored_count else 0,
        top_prospects=top_prospects,
    )


@router.post("/{prospect_id}/score", response_model=ProspectScoreDetail)
async def score_single_prospect(
    prospect_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Score or rescore a single prospect."""
    result = await db.execute(
        select(Prospect).where(Prospect.id == prospect_id)
    )
    prospect = result.scalar_one_or_none()

    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    scoring_service = get_scoring_service()

    score_result = scoring_service.score_prospect(
        company_number=prospect.company_number,
        company_name=prospect.company_name,
        sic_codes=prospect.sic_codes,
        date_of_creation=prospect.date_of_creation,
        region=prospect.region,
        officer_count=prospect.officer_count,
        filing_count=prospect.filing_count,
        has_charges=prospect.has_charges,
        has_website=prospect.has_website,
        has_https=prospect.has_https,
    )

    # Update prospect
    prospect.prospect_score = score_result.total_score
    prospect.tier = score_result.tier
    prospect.industry_score = score_result.industry_score
    prospect.age_score = score_result.age_score
    prospect.size_score = score_result.size_score
    prospect.geography_score = score_result.geography_score
    prospect.web_presence_score = score_result.web_presence_score
    prospect.bespoke_fit_score = score_result.bespoke_fit_score
    prospect.ml_model_score = score_result.ml_model_score
    prospect.packaging_need = score_result.packaging_need
    prospect.packaging_need_reason = score_result.packaging_need_reason
    prospect.bespoke_fit_reason = score_result.bespoke_fit_reason
    prospect.is_excluded = score_result.is_excluded
    prospect.exclusion_reason = score_result.exclusion_reason
    prospect.cluster_id = score_result.cluster_id
    prospect.cluster_name = score_result.cluster_name
    prospect.industry_sector = score_result.industry_sector
    prospect.last_scored_at = datetime.utcnow()

    # Set status based on exclusion
    if score_result.is_excluded:
        prospect.status = ProspectStatus.DISQUALIFIED
    else:
        prospect.status = ProspectStatus.SCORED

    # Create score record
    score_record = ProspectScore(
        prospect_id=prospect.id,
        total_score=score_result.total_score,
        tier=score_result.tier,
        industry_score=score_result.industry_score,
        age_score=score_result.age_score,
        size_score=score_result.size_score,
        geography_score=score_result.geography_score,
        web_presence_score=score_result.web_presence_score,
        ml_model_score=score_result.ml_model_score,
        ml_model_version=score_result.ml_model_version,
    )
    db.add(score_record)

    await db.commit()

    return ProspectScoreDetail(
        total_score=score_result.total_score,
        tier=score_result.tier,
        industry_score=score_result.industry_score,
        age_score=score_result.age_score,
        size_score=score_result.size_score,
        geography_score=score_result.geography_score,
        web_presence_score=score_result.web_presence_score,
        bespoke_fit_score=score_result.bespoke_fit_score,
        ml_model_score=score_result.ml_model_score,
        ml_model_version=score_result.ml_model_version,
        packaging_need=score_result.packaging_need,
        packaging_need_reason=score_result.packaging_need_reason,
        bespoke_fit_reason=score_result.bespoke_fit_reason,
        is_excluded=score_result.is_excluded,
        exclusion_reason=score_result.exclusion_reason,
        cluster_id=score_result.cluster_id,
        cluster_name=score_result.cluster_name,
        scored_at=datetime.utcnow(),
    )


# =============================================================================
# Enrichment Endpoints
# =============================================================================


@router.post("/enrich", response_model=BatchEnrichResponse)
async def enrich_prospects(
    request: BatchEnrichRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Enrich prospects with additional data from Companies House.

    Fetches officers, filings, and charges for each prospect.
    """
    api_key = settings.companies_house_api_key
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Companies House API key not configured",
        )

    # Build query
    query = select(Prospect)

    if request.prospect_ids:
        query = query.where(Prospect.id.in_(request.prospect_ids))
    else:
        query = query.where(Prospect.last_enriched_at.is_(None))

    query = query.limit(request.max_batch_size)

    result = await db.execute(query)
    prospects = result.scalars().all()

    start_time = datetime.utcnow()
    api_calls = 0

    async with CompaniesHouseClient(api_key=api_key) as client:
        for prospect in prospects:
            try:
                # Get enriched data
                enriched = await client.enrich_company(prospect.company_number)
                api_calls += 4  # profile + officers + filings + charges

                # Update prospect
                profile = enriched.get("profile")
                if profile:
                    prospect.company_status = profile.get("company_status")
                    prospect.has_charges = profile.get("has_charges", False)
                    prospect.has_insolvency_history = profile.get(
                        "has_insolvency_history", False
                    )

                    if profile.get("registered_office_address"):
                        addr = profile["registered_office_address"]
                        prospect.address_line_1 = addr.get("address_line_1")
                        prospect.address_line_2 = addr.get("address_line_2")
                        prospect.locality = addr.get("locality")
                        prospect.region = addr.get("region")
                        prospect.postal_code = addr.get("postal_code")

                officers = enriched.get("officers", {})
                prospect.officer_count = officers.get("total_results", 0)
                prospect.active_officer_count = officers.get("active_count", 0)

                filings = enriched.get("filings", {})
                prospect.filing_count = filings.get("total_count", 0)

                prospect.raw_data = enriched
                prospect.last_enriched_at = datetime.utcnow()

            except Exception as e:
                logger.warning(
                    f"Failed to enrich {prospect.company_number}: {e}"
                )

    await db.commit()

    duration = (datetime.utcnow() - start_time).total_seconds()

    return BatchEnrichResponse(
        total_enriched=len(prospects),
        api_calls_made=api_calls,
        duration_seconds=round(duration, 2),
    )


# =============================================================================
# Activity Endpoints
# =============================================================================


@router.post("/{prospect_id}/activities", response_model=ProspectActivityResponse)
async def create_activity(
    prospect_id: UUID,
    activity: ProspectActivityCreate,
    db: AsyncSession = Depends(get_db),
):
    """Log an activity for a prospect."""
    result = await db.execute(
        select(Prospect).where(Prospect.id == prospect_id)
    )
    prospect = result.scalar_one_or_none()

    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")

    new_activity = ProspectActivity(
        prospect_id=prospect_id,
        activity_type=activity.activity_type,
        description=activity.description,
        extra_data=activity.extra_data,
    )
    db.add(new_activity)
    await db.commit()
    await db.refresh(new_activity)

    return ProspectActivityResponse.model_validate(new_activity)


@router.get("/{prospect_id}/activities", response_model=list[ProspectActivityResponse])
async def list_activities(
    prospect_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List activities for a prospect."""
    result = await db.execute(
        select(ProspectActivity)
        .where(ProspectActivity.prospect_id == prospect_id)
        .order_by(ProspectActivity.created_at.desc())
        .limit(limit)
    )
    activities = result.scalars().all()

    return [ProspectActivityResponse.model_validate(a) for a in activities]
