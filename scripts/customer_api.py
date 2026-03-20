#!/usr/bin/env python3
"""
PackagePro Customer API

A FastAPI-based REST API providing access to customer segmentation,
prospect scoring, and customer insights.

Endpoints:
    GET  /customer/{name}    - Get customer profile and segment
    GET  /segment/{id}       - Get segment details
    POST /score              - Score a new prospect
    GET  /at-risk            - List at-risk customers
    GET  /opportunities      - List upsell opportunities
    GET  /health             - API health check

Usage:
    # Start the server
    python customer_api.py

    # Or with uvicorn for development
    uvicorn customer_api:app --reload --port 8000

Author: PackagePro Analytics Team
Version: 1.0.0
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

# =============================================================================
# Path Configuration
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "companies"
OUTPUTS_DIR = BASE_DIR / "outputs"
SEGMENTATION_DIR = OUTPUTS_DIR / "segmentation"
MODELS_DIR = BASE_DIR / "models" / "prospect_scorer"

# =============================================================================
# Pydantic Models
# =============================================================================

class ProspectInput(BaseModel):
    """Input model for prospect scoring."""
    name: str = Field(..., description="Company name")
    sic_code: Optional[str] = Field(None, description="SIC code")
    company_age_years: Optional[float] = Field(None, description="Company age in years")
    region: Optional[str] = Field(None, description="Region/location")
    officer_count: Optional[int] = Field(None, description="Number of officers")
    has_website: Optional[bool] = Field(False, description="Whether company has a website")


class ScoreResult(BaseModel):
    """Result model for prospect scoring."""
    name: str
    overall_score: float
    priority_tier: str
    component_scores: Dict[str, float]
    reasons: Dict[str, str]
    recommendation: str


class CustomerProfile(BaseModel):
    """Customer profile response model."""
    company: str
    segment: str
    cluster_id: int
    rfm_metrics: Dict[str, Any]
    activity_status: str
    company_info: Dict[str, Any]
    recommendations: List[str]


class SegmentInfo(BaseModel):
    """Segment information response model."""
    segment_id: int
    name: str
    size: int
    percentage: float
    characteristics: str
    recommended_actions: str
    metrics: Dict[str, float]


class AtRiskCustomer(BaseModel):
    """At-risk customer model."""
    company: str
    segment: str
    total_revenue: float
    days_since_order: int
    total_orders: int
    risk_score: float


class UpsellOpportunity(BaseModel):
    """Upsell opportunity model."""
    company: str
    segment: str
    avg_order_value: float
    target_value: float
    gap: float
    total_orders: int
    industry: str
    opportunity_score: float


# =============================================================================
# Data Management
# =============================================================================

class DataManager:
    """Manages data loading and caching."""

    def __init__(self):
        self._customers: Optional[pd.DataFrame] = None
        self._segments: Optional[pd.DataFrame] = None
        self._insights: Optional[pd.DataFrame] = None
        self._icp: Optional[Dict] = None
        self._merged: Optional[pd.DataFrame] = None
        self._last_load: Optional[datetime] = None
        self._cache_minutes = 5  # Refresh every 5 minutes

    def _should_refresh(self) -> bool:
        if self._last_load is None:
            return True
        elapsed = (datetime.now() - self._last_load).total_seconds() / 60
        return elapsed > self._cache_minutes

    def _load_all(self):
        """Load all data sources."""
        self._customers = pd.read_csv(DATA_DIR / "company_features.csv")
        self._segments = pd.read_csv(SEGMENTATION_DIR / "cluster_assignments.csv")
        self._insights = pd.read_csv(SEGMENTATION_DIR / "cluster_insights.csv")
        with open(MODELS_DIR / "icp_profile.json", 'r') as f:
            self._icp = json.load(f)
        self._merged = self._customers.merge(self._segments, on='company', how='left')
        self._last_load = datetime.now()

    @property
    def customers(self) -> pd.DataFrame:
        if self._should_refresh():
            self._load_all()
        return self._customers

    @property
    def segments(self) -> pd.DataFrame:
        if self._should_refresh():
            self._load_all()
        return self._segments

    @property
    def insights(self) -> pd.DataFrame:
        if self._should_refresh():
            self._load_all()
        return self._insights

    @property
    def icp(self) -> Dict:
        if self._should_refresh():
            self._load_all()
        return self._icp

    @property
    def merged(self) -> pd.DataFrame:
        if self._should_refresh():
            self._load_all()
        return self._merged


# Initialize data manager
data = DataManager()

# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="PackagePro Customer API",
    description="REST API for customer segmentation and prospect scoring",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/health")
async def health_check():
    """API health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "data_loaded": data._last_load.isoformat() if data._last_load else None,
        "total_customers": len(data.merged) if data._merged is not None else 0
    }


@app.get("/customer/{name}", response_model=CustomerProfile)
async def get_customer(name: str):
    """
    Look up a customer by name.

    Returns customer profile including segment, RFM metrics, and recommendations.
    Supports partial matching (case-insensitive).
    """
    df = data.merged
    matches = df[df['company'].str.lower().str.contains(name.lower(), na=False)]

    if len(matches) == 0:
        raise HTTPException(status_code=404, detail=f"No customer found matching '{name}'")

    if len(matches) > 1:
        # Return first exact match if exists, otherwise first partial match
        exact = matches[matches['company'].str.lower() == name.lower()]
        if len(exact) > 0:
            customer = exact.iloc[0]
        else:
            customer = matches.iloc[0]
    else:
        customer = matches.iloc[0]

    # Determine activity status
    recency = customer.get('recency_days', 999)
    if recency <= 30:
        status = "active"
    elif recency <= 90:
        status = "recent"
    elif recency <= 180:
        status = "cooling"
    else:
        status = "at_risk"

    # Generate recommendations
    recommendations = []
    segment = str(customer.get('business_segment', ''))

    if 'High-Value' in segment:
        recommendations = [
            "Schedule quarterly business review",
            "Offer VIP early access to new products",
            "Consider volume discount incentives"
        ]
    elif 'Growth' in segment:
        recommendations = [
            "Re-engage with personalized outreach",
            "Offer targeted promotions",
            "Understand barriers to purchasing"
        ]
    elif recency > 180:
        recommendations = [
            "Urgent: Win-back campaign needed",
            "Personal call to understand situation",
            "Consider special re-activation offer"
        ]
    else:
        recommendations = [
            "Maintain regular engagement",
            "Look for upsell opportunities",
            "Cross-sell complementary products"
        ]

    return CustomerProfile(
        company=customer['company'],
        segment=str(customer.get('business_segment', 'Unknown')),
        cluster_id=int(customer.get('cluster', -1)),
        rfm_metrics={
            "recency_days": int(customer.get('recency_days', 0)),
            "frequency": int(customer.get('frequency', 0)),
            "monetary_total": float(customer.get('monetary_total', 0)),
            "monetary_mean": float(customer.get('monetary_mean', 0))
        },
        activity_status=status,
        company_info={
            "industry_sector": str(customer.get('industry_sector', 'Unknown')),
            "company_age_years": float(customer.get('company_age_years', 0)) if pd.notna(customer.get('company_age_years')) else None,
            "region": str(customer.get('region', 'Unknown'))
        },
        recommendations=recommendations
    )


@app.get("/customers/search")
async def search_customers(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results")
):
    """Search for customers by name."""
    df = data.merged
    matches = df[df['company'].str.lower().str.contains(q.lower(), na=False)]

    results = []
    for _, row in matches.head(limit).iterrows():
        results.append({
            "company": row['company'],
            "segment": str(row.get('business_segment', 'Unknown')),
            "total_revenue": float(row.get('monetary_total', 0)),
            "last_order_days": int(row.get('recency_days', 0))
        })

    return {"query": q, "count": len(matches), "results": results}


@app.get("/segment/{segment_id}", response_model=SegmentInfo)
async def get_segment(segment_id: int):
    """
    Get segment details by cluster ID.

    Returns segment information including size, characteristics, and recommended actions.
    """
    insights = data.insights
    df = data.merged

    if segment_id not in insights['Cluster'].values:
        raise HTTPException(status_code=404, detail=f"Segment {segment_id} not found")

    segment_info = insights[insights['Cluster'] == segment_id].iloc[0]
    segment_data = df[df['cluster'] == segment_id]

    total_customers = len(df)
    segment_size = len(segment_data)

    # Calculate metrics
    metrics = {
        "total_revenue": float(segment_data['monetary_total'].sum()),
        "avg_revenue": float(segment_data['monetary_total'].mean()),
        "avg_frequency": float(segment_data['frequency'].mean()),
        "avg_recency": float(segment_data['recency_days'].mean())
    }

    return SegmentInfo(
        segment_id=segment_id,
        name=segment_info['Business Name'],
        size=segment_size,
        percentage=segment_size / total_customers * 100,
        characteristics=segment_info['Key Characteristics'],
        recommended_actions=segment_info['Recommended Actions'],
        metrics=metrics
    )


@app.get("/segments")
async def list_segments():
    """List all segments with summary metrics."""
    insights = data.insights
    df = data.merged

    segments = []
    for _, row in insights.iterrows():
        cluster_id = row['Cluster']
        segment_data = df[df['cluster'] == cluster_id]

        segments.append({
            "segment_id": int(cluster_id),
            "name": row['Business Name'],
            "size": len(segment_data),
            "percentage": len(segment_data) / len(df) * 100,
            "total_revenue": float(segment_data['monetary_total'].sum()),
            "avg_recency": float(segment_data['recency_days'].mean())
        })

    return {"segments": segments}


@app.post("/score", response_model=ScoreResult)
async def score_prospect(prospect: ProspectInput):
    """
    Score a new prospect based on the ICP profile.

    Returns overall score (0-100), priority tier, and detailed breakdown.
    """
    icp = data.icp

    # Map SIC to industry
    industry = "Unknown"
    if prospect.sic_code:
        try:
            sic_int = int(str(prospect.sic_code)[:2])
            if sic_int in range(10, 34):
                industry = "Manufacturing"
            elif sic_int in range(45, 48):
                industry = "Wholesale & Retail"
            elif sic_int in range(69, 76):
                industry = "Professional Services"
            elif sic_int in range(77, 83):
                industry = "Administrative Services"
            elif sic_int in range(41, 44):
                industry = "Construction"
            elif sic_int in range(58, 64):
                industry = "Information & Communication"
            else:
                industry = "Other"
        except (ValueError, TypeError):
            pass

    scores = {}
    reasons = {}

    # Industry score
    industry_profiles = icp.get('industry_profiles', {})
    if industry in industry_profiles:
        profile = industry_profiles[industry]
        scores['industry'] = profile.get('score_weight', 50)
        lift = profile.get('lift_ratio', 1.0)
        reasons['industry'] = f"{industry} sector (lift ratio: {lift:.2f}x)"
    else:
        scores['industry'] = 50
        reasons['industry'] = f"{industry} (not in ICP data)"

    # Age score
    age_profile = icp.get('company_age', {})
    optimal_min = age_profile.get('optimal_min_years', 7)
    optimal_max = age_profile.get('optimal_max_years', 29)

    if prospect.company_age_years:
        age = prospect.company_age_years
        if optimal_min <= age <= optimal_max:
            scores['age'] = 100
            reasons['age'] = f"{age} years (optimal range)"
        elif age < optimal_min:
            scores['age'] = max(40, 100 - (optimal_min - age) * 8)
            reasons['age'] = f"{age} years (young company)"
        else:
            scores['age'] = max(60, 100 - (age - optimal_max) * 2)
            reasons['age'] = f"{age} years (established)"
    else:
        scores['age'] = 50
        reasons['age'] = "Unknown age"

    # Region score
    geo_profile = icp.get('geography', {})
    region_scores = geo_profile.get('region_scores', {})

    if prospect.region and prospect.region in region_scores:
        scores['region'] = region_scores[prospect.region]
        reasons['region'] = f"{prospect.region} (known region)"
    else:
        scores['region'] = 50
        reasons['region'] = f"{prospect.region or 'Unknown'} region"

    # Web presence score
    if prospect.has_website:
        scores['web'] = 80
        reasons['web'] = "Has website"
    else:
        scores['web'] = 40
        reasons['web'] = "No website detected"

    # Calculate overall
    weights = {'industry': 0.35, 'age': 0.30, 'region': 0.20, 'web': 0.15}
    overall = sum(scores[k] * weights[k] for k in scores)

    # Determine tier
    if overall >= 75:
        tier = "Hot"
        recommendation = "Priority lead - immediate sales follow-up recommended"
    elif overall >= 60:
        tier = "Warm"
        recommendation = "Good prospect - add to nurture campaign"
    elif overall >= 45:
        tier = "Cool"
        recommendation = "Moderate fit - qualify further before pursuing"
    else:
        tier = "Cold"
        recommendation = "Low priority - may not match ICP"

    return ScoreResult(
        name=prospect.name,
        overall_score=round(overall, 2),
        priority_tier=tier,
        component_scores={k: round(v, 2) for k, v in scores.items()},
        reasons=reasons,
        recommendation=recommendation
    )


@app.get("/at-risk", response_model=List[AtRiskCustomer])
async def get_at_risk_customers(
    limit: int = Query(20, ge=1, le=100, description="Maximum results")
):
    """
    Get list of at-risk customers.

    At-risk defined as: high value, but long time since last order.
    """
    df = data.merged

    monetary_threshold = df['monetary_total'].quantile(0.6)

    at_risk = df[
        (df['monetary_total'] >= monetary_threshold) &
        (df['recency_days'] > 90) &
        (df['frequency'] >= 2)
    ].copy()

    at_risk['risk_score'] = (
        at_risk['monetary_total'] / at_risk['monetary_total'].max() * 40 +
        at_risk['recency_days'] / at_risk['recency_days'].max() * 40 +
        at_risk['frequency'] / at_risk['frequency'].max() * 20
    )

    at_risk = at_risk.sort_values('risk_score', ascending=False).head(limit)

    results = []
    for _, row in at_risk.iterrows():
        results.append(AtRiskCustomer(
            company=row['company'],
            segment=str(row.get('business_segment', 'Unknown')),
            total_revenue=float(row['monetary_total']),
            days_since_order=int(row['recency_days']),
            total_orders=int(row['frequency']),
            risk_score=round(float(row['risk_score']), 2)
        ))

    return results


@app.get("/opportunities", response_model=List[UpsellOpportunity])
async def get_upsell_opportunities(
    limit: int = Query(20, ge=1, le=100, description="Maximum results")
):
    """
    Get list of upsell opportunities.

    Opportunities defined as: active customers with below-average order values.
    """
    df = data.merged

    avg_order_value = df['monetary_mean'].median()

    upsell = df[
        (df['recency_days'] <= 180) &
        (df['frequency'] >= 3) &
        (df['monetary_mean'] < avg_order_value)
    ].copy()

    upsell['opportunity_score'] = (
        (1 - upsell['recency_days'] / 365) * 30 +
        upsell['frequency'] / upsell['frequency'].max() * 40 +
        (1 - upsell['monetary_mean'] / avg_order_value) * 30
    )

    upsell = upsell.sort_values('opportunity_score', ascending=False).head(limit)

    results = []
    for _, row in upsell.iterrows():
        results.append(UpsellOpportunity(
            company=row['company'],
            segment=str(row.get('business_segment', 'Unknown')),
            avg_order_value=float(row['monetary_mean']),
            target_value=float(avg_order_value),
            gap=float(avg_order_value - row['monetary_mean']),
            total_orders=int(row['frequency']),
            industry=str(row.get('industry_sector', 'Unknown')),
            opportunity_score=round(float(row['opportunity_score']), 2)
        ))

    return results


@app.get("/stats")
async def get_statistics():
    """Get overall customer statistics."""
    df = data.merged

    return {
        "total_customers": len(df),
        "total_revenue": float(df['monetary_total'].sum()),
        "avg_order_value": float(df['monetary_mean'].mean()),
        "active_30_days": len(df[df['recency_days'] <= 30]),
        "active_90_days": len(df[df['recency_days'] <= 90]),
        "at_risk_count": len(df[(df['recency_days'] > 180) & (df['monetary_total'] > df['monetary_total'].median())]),
        "segment_distribution": df['business_segment'].value_counts().to_dict(),
        "industry_distribution": df['industry_sector'].value_counts().head(10).to_dict()
    }


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="PackagePro Customer API Server")
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', '-p', type=int, default=8000, help='Port to listen on')
    parser.add_argument('--reload', action='store_true', help='Enable auto-reload')

    args = parser.parse_args()

    print(f"Starting PackagePro Customer API on http://{args.host}:{args.port}")
    print(f"  API Docs: http://{args.host}:{args.port}/docs")
    print(f"  ReDoc: http://{args.host}:{args.port}/redoc")

    uvicorn.run(
        "customer_api:app" if args.reload else app,
        host=args.host,
        port=args.port,
        reload=args.reload
    )
