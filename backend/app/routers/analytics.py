"""Analytics API router for customer acquisition insights."""

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.customer_analytics import CustomerAnalyticsEngine
from backend.app.db.session import get_db
from backend.app.models.estimate import Estimate

logger = logging.getLogger(__name__)
router = APIRouter()


async def _load_analytics_engine(db: AsyncSession) -> CustomerAnalyticsEngine:
    """Load analytics engine with data from database."""
    engine = CustomerAnalyticsEngine()

    result = await db.execute(
        select(Estimate).order_by(Estimate.created_at.desc())
    )
    estimates = result.scalars().all()

    records = []
    for est in estimates:
        inputs = dict(est.inputs) if est.inputs else {}
        records.append({
            "company_name": est.job_name,  # Will use customer name when available
            "date": est.created_at,
            "total_cost": float(est.total_cost) if est.total_cost else 0,
            "status": est.status.value if est.status else "draft",
            "quantity": inputs.get("quantity", 0),
            "product_type": inputs.get("product_type", "bespoke_packaging"),
            "complexity_tier": est.complexity_tier or 3,
        })

    engine.load_estimates(records)
    return engine


@router.get("/segments")
async def get_customer_segments(db: AsyncSession = Depends(get_db)):
    """
    Get customer segmentation analysis.

    Returns customers grouped by RFM segment:
    - champion: High value, frequent, recent
    - loyal: Regular, moderate value
    - potential: Recent, shows promise
    - at_risk: Previously active, declining
    - dormant: No recent activity
    """
    engine = await _load_analytics_engine(db)
    return engine.get_segment_summary()


@router.get("/customers")
async def get_customer_profiles(
    segment: Optional[str] = None,
    min_revenue: float = 0,
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed customer profiles.

    - **segment**: Filter by segment (champion, loyal, potential, at_risk, dormant)
    - **min_revenue**: Minimum total revenue filter
    - **limit**: Max results (default 50)
    """
    engine = await _load_analytics_engine(db)
    profiles = engine.get_all_profiles()

    if segment:
        profiles = [p for p in profiles if p["segment"] == segment]

    if min_revenue > 0:
        profiles = [p for p in profiles if p["total_revenue"] >= min_revenue]

    return profiles[:limit]


@router.get("/leads")
async def get_lead_scores(
    min_score: float = Query(0, ge=0, le=100),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """
    Get lead scores for all customers.

    Higher scores indicate better re-engagement or upsell potential.
    Scoring is based on Recency, Frequency, Monetary value, and Conversion rate.
    """
    engine = await _load_analytics_engine(db)
    scores = engine.score_leads()

    if min_score > 0:
        scores = [s for s in scores if s["score"] >= min_score]

    return scores[:limit]


@router.get("/targets")
async def get_acquisition_targets(
    min_score: float = Query(30, ge=0, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Get prioritized customer acquisition targets.

    Returns customers worth re-engaging (dormant/at-risk) or expanding (active),
    sorted by lead score.
    """
    engine = await _load_analytics_engine(db)
    return engine.get_acquisition_targets(min_score=min_score)


@router.get("/insights")
async def get_market_insights(db: AsyncSession = Depends(get_db)):
    """
    Get aggregate market insights.

    Returns:
    - Product mix analysis
    - Annual revenue trends
    - Order quantity statistics
    - Seasonality patterns
    - Revenue concentration (Pareto analysis)
    """
    engine = await _load_analytics_engine(db)
    return engine.get_market_insights()


@router.get("/similar/{company_name}")
async def find_similar_companies(
    company_name: str,
    top_n: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """
    Find companies with similar order profiles.

    Useful for identifying potential target companies based on
    existing customer patterns (product types, quantities, complexity).
    """
    engine = await _load_analytics_engine(db)
    return engine.find_similar_companies(company_name, top_n=top_n)


@router.post("/import-legacy")
async def import_legacy_estimates(
    directory: str,
    max_files: int = Query(100, ge=1, le=10000),
):
    """
    Import legacy Excel estimates for analysis.

    Processes Excel files from the specified directory and returns
    analytics results without requiring a database.
    """
    from backend.app.core.excel_processor import ExcelEstimateProcessor

    dir_path = Path(directory)
    if not dir_path.exists():
        return {"error": f"Directory not found: {directory}"}

    processor = ExcelEstimateProcessor()
    records = processor.process_directory(str(dir_path), limit=max_files)

    engine = CustomerAnalyticsEngine()
    engine.load_from_excel_records(records)

    return {
        "files_processed": len(records),
        "customers_found": len(engine.get_all_profiles()),
        "segments": engine.get_segment_summary(),
        "insights": engine.get_market_insights(),
        "top_targets": engine.get_acquisition_targets(min_score=30)[:20],
        "top_leads": engine.score_leads()[:20],
    }
