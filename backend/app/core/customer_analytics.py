"""
Customer Acquisition Analytics Engine.

Analyzes historical estimate data to identify patterns and opportunities
for customer acquisition, retention, and growth.

Key capabilities:
1. Customer segmentation (RFM: Recency, Frequency, Monetary)
2. Order pattern analysis (seasonality, trends, product mix)
3. Lead scoring based on historical conversion patterns
4. Churn risk detection
5. Customer lifetime value estimation
6. Industry/product type analysis for targeting
"""

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CustomerSegment(str, Enum):
    """Customer value segments based on RFM analysis."""

    CHAMPION = "champion"          # High value, frequent, recent
    LOYAL = "loyal"                # Regular, moderate value
    POTENTIAL = "potential"        # Recent, shows promise
    AT_RISK = "at_risk"           # Previously active, declining
    DORMANT = "dormant"           # No recent activity
    NEW = "new"                   # First-time customer
    ONE_TIME = "one_time"         # Single order, no return


@dataclass
class CustomerProfile:
    """Aggregated customer profile from historical data."""

    customer_id: Optional[str]
    company_name: str
    first_order_date: Optional[datetime] = None
    last_order_date: Optional[datetime] = None
    total_orders: int = 0
    total_revenue: Decimal = Decimal("0")
    won_orders: int = 0
    lost_orders: int = 0
    avg_order_value: Decimal = Decimal("0")
    product_types: list[str] = field(default_factory=list)
    typical_quantities: list[int] = field(default_factory=list)
    typical_complexity: int = 3
    segment: CustomerSegment = CustomerSegment.NEW
    churn_risk: float = 0.0
    lifetime_value: Decimal = Decimal("0")
    conversion_rate: float = 0.0
    avg_days_between_orders: float = 0.0

    def to_dict(self) -> dict:
        return {
            "customer_id": self.customer_id,
            "company_name": self.company_name,
            "first_order_date": self.first_order_date.isoformat() if self.first_order_date else None,
            "last_order_date": self.last_order_date.isoformat() if self.last_order_date else None,
            "total_orders": self.total_orders,
            "total_revenue": float(self.total_revenue),
            "won_orders": self.won_orders,
            "lost_orders": self.lost_orders,
            "avg_order_value": float(self.avg_order_value),
            "product_types": self.product_types,
            "typical_quantities": self.typical_quantities,
            "typical_complexity": self.typical_complexity,
            "segment": self.segment.value,
            "churn_risk": round(self.churn_risk, 3),
            "lifetime_value": float(self.lifetime_value),
            "conversion_rate": round(self.conversion_rate, 3),
            "avg_days_between_orders": round(self.avg_days_between_orders, 1),
        }


@dataclass
class LeadScore:
    """Scoring for a potential or existing customer."""

    company_name: str
    score: float  # 0-100
    factors: dict[str, float] = field(default_factory=dict)
    recommendation: str = ""

    def to_dict(self) -> dict:
        return {
            "company_name": self.company_name,
            "score": round(self.score, 1),
            "factors": {k: round(v, 2) for k, v in self.factors.items()},
            "recommendation": self.recommendation,
        }


@dataclass
class MarketInsight:
    """Aggregate market analysis insight."""

    category: str
    metric: str
    value: Any
    trend: Optional[str] = None  # "up", "down", "stable"
    detail: str = ""


class CustomerAnalyticsEngine:
    """
    Analyzes estimate data to generate customer acquisition insights.

    Works with two data sources:
    1. Database estimates (from PostgreSQL via SQLAlchemy)
    2. Legacy Excel estimates (via ExcelEstimateProcessor)
    """

    def __init__(self):
        self._profiles: dict[str, CustomerProfile] = {}
        self._estimates: list[dict] = []
        self._insights: list[MarketInsight] = []

    def load_estimates(self, estimates: list[dict]) -> None:
        """
        Load estimate records for analysis.

        Each estimate dict should have:
            - customer_name or company_name
            - date or created_at
            - total_cost or price
            - status (won/lost/quoted/draft)
            - quantity
            - product_type (optional)
            - complexity_tier (optional)
        """
        self._estimates = estimates
        self._build_profiles()

    def load_from_excel_records(self, records: list) -> None:
        """Load from ExcelEstimateProcessor EstimateRecord objects."""
        estimates = []
        for rec in records:
            estimates.append({
                "company_name": rec.company_name or "Unknown",
                "date": rec.date,
                "total_cost": max(rec.prices) if rec.prices else 0,
                "status": "won",  # Legacy estimates were executed
                "quantity": max(rec.quantities) if rec.quantities else 0,
                "product_type": rec.product_type or "unknown",
                "complexity_tier": 3,
                "job_description": rec.job_description or "",
                "estimate_id": rec.estimate_id,
            })
        self._estimates = estimates
        self._build_profiles()

    def _build_profiles(self) -> None:
        """Build customer profiles from loaded estimates."""
        grouped: dict[str, list[dict]] = defaultdict(list)
        for est in self._estimates:
            name = est.get("company_name") or est.get("customer_name") or "Unknown"
            grouped[name.strip().upper()].append(est)

        self._profiles = {}
        for company_key, orders in grouped.items():
            if company_key == "UNKNOWN":
                continue

            profile = CustomerProfile(
                customer_id=None,
                company_name=orders[0].get("company_name") or orders[0].get("customer_name", company_key),
            )

            dates = []
            revenues = []
            quantities = []
            product_types = []

            for order in orders:
                profile.total_orders += 1

                # Date
                order_date = order.get("date") or order.get("created_at")
                if isinstance(order_date, str):
                    try:
                        order_date = datetime.fromisoformat(order_date)
                    except (ValueError, TypeError):
                        order_date = None
                if order_date:
                    dates.append(order_date)

                # Revenue
                cost = order.get("total_cost") or order.get("price", 0)
                try:
                    revenue = Decimal(str(cost))
                except Exception:
                    revenue = Decimal("0")
                revenues.append(revenue)

                # Status
                status = str(order.get("status", "")).lower()
                if status in ("won", "completed"):
                    profile.won_orders += 1
                elif status in ("lost",):
                    profile.lost_orders += 1

                # Quantity
                qty = order.get("quantity", 0)
                if isinstance(qty, (int, float)) and qty > 0:
                    quantities.append(int(qty))

                # Product type
                ptype = order.get("product_type", "")
                if ptype:
                    product_types.append(ptype)

                # Complexity
                tier = order.get("complexity_tier", 3)
                if isinstance(tier, (int, float)):
                    profile.typical_complexity = int(tier)

            # Aggregate
            if dates:
                profile.first_order_date = min(dates)
                profile.last_order_date = max(dates)
                if len(dates) > 1:
                    sorted_dates = sorted(dates)
                    gaps = [(sorted_dates[i + 1] - sorted_dates[i]).days
                            for i in range(len(sorted_dates) - 1)]
                    profile.avg_days_between_orders = sum(gaps) / len(gaps) if gaps else 0

            profile.total_revenue = sum(revenues)
            if profile.total_orders > 0:
                profile.avg_order_value = profile.total_revenue / profile.total_orders
            profile.typical_quantities = sorted(set(quantities))[:5]  # Top 5 unique qtys
            profile.product_types = list(set(product_types))[:10]

            # Conversion rate
            quoted = profile.won_orders + profile.lost_orders
            profile.conversion_rate = profile.won_orders / quoted if quoted > 0 else 0.0

            # Segment
            profile.segment = self._classify_segment(profile)
            profile.churn_risk = self._calculate_churn_risk(profile)
            profile.lifetime_value = self._estimate_ltv(profile)

            self._profiles[company_key] = profile

    def _classify_segment(self, profile: CustomerProfile) -> CustomerSegment:
        """Classify customer into RFM segment."""
        now = datetime.now()

        if profile.total_orders == 0:
            return CustomerSegment.NEW

        if profile.total_orders == 1:
            return CustomerSegment.ONE_TIME

        days_since_last = (now - profile.last_order_date).days if profile.last_order_date else 999

        if days_since_last > 365:
            return CustomerSegment.DORMANT

        if days_since_last > 180:
            return CustomerSegment.AT_RISK

        if profile.total_orders >= 5 and profile.avg_order_value > Decimal("5000"):
            return CustomerSegment.CHAMPION

        if profile.total_orders >= 3:
            return CustomerSegment.LOYAL

        return CustomerSegment.POTENTIAL

    def _calculate_churn_risk(self, profile: CustomerProfile) -> float:
        """Calculate churn risk score (0.0 = safe, 1.0 = likely churned)."""
        if not profile.last_order_date:
            return 0.5

        now = datetime.now()
        days_since = (now - profile.last_order_date).days
        expected_gap = profile.avg_days_between_orders or 180

        if expected_gap <= 0:
            expected_gap = 180

        # Risk increases as days since last order exceeds expected gap
        ratio = days_since / expected_gap
        risk = min(1.0, max(0.0, (ratio - 0.5) / 2.0))
        return risk

    def _estimate_ltv(self, profile: CustomerProfile) -> Decimal:
        """Estimate customer lifetime value (simple projection)."""
        if profile.total_orders <= 1:
            return profile.total_revenue

        # Project based on average order value and frequency
        if profile.avg_days_between_orders > 0:
            orders_per_year = 365 / profile.avg_days_between_orders
        else:
            orders_per_year = 1.0

        # 3-year projection with retention decay
        retention = 1.0 - profile.churn_risk
        projected = Decimal("0")
        for year in range(1, 4):
            year_revenue = profile.avg_order_value * Decimal(str(orders_per_year)) * Decimal(str(retention ** year))
            projected += year_revenue

        return (profile.total_revenue + projected).quantize(Decimal("0.01"))

    def get_all_profiles(self) -> list[dict]:
        """Get all customer profiles sorted by revenue."""
        profiles = sorted(
            self._profiles.values(),
            key=lambda p: p.total_revenue,
            reverse=True,
        )
        return [p.to_dict() for p in profiles]

    def get_segment_summary(self) -> dict[str, dict]:
        """Get summary by customer segment."""
        segments: dict[str, list] = defaultdict(list)
        for profile in self._profiles.values():
            segments[profile.segment.value].append(profile)

        result = {}
        for seg, profiles in segments.items():
            result[seg] = {
                "count": len(profiles),
                "total_revenue": float(sum(p.total_revenue for p in profiles)),
                "avg_order_value": float(sum(p.avg_order_value for p in profiles) / len(profiles)) if profiles else 0,
                "avg_orders": sum(p.total_orders for p in profiles) / len(profiles) if profiles else 0,
                "top_companies": [p.company_name for p in sorted(profiles, key=lambda x: x.total_revenue, reverse=True)[:5]],
            }
        return result

    def score_leads(self) -> list[dict]:
        """Score all customers for re-engagement / upsell potential."""
        scores = []
        for profile in self._profiles.values():
            score = self._score_lead(profile)
            scores.append(score.to_dict())
        return sorted(scores, key=lambda x: x["score"], reverse=True)

    def _score_lead(self, profile: CustomerProfile) -> LeadScore:
        """Score a customer for re-engagement potential."""
        factors = {}

        # Recency (0-25): more recent = higher score
        if profile.last_order_date:
            days = (datetime.now() - profile.last_order_date).days
            factors["recency"] = max(0, 25 - (days / 365 * 25))
        else:
            factors["recency"] = 0

        # Frequency (0-25): more orders = higher score
        factors["frequency"] = min(25, profile.total_orders * 3)

        # Monetary (0-25): higher value = higher score
        rev = float(profile.total_revenue)
        if rev > 50000:
            factors["monetary"] = 25
        elif rev > 10000:
            factors["monetary"] = 20
        elif rev > 5000:
            factors["monetary"] = 15
        elif rev > 1000:
            factors["monetary"] = 10
        else:
            factors["monetary"] = 5

        # Conversion potential (0-25)
        if profile.conversion_rate > 0.8:
            factors["conversion"] = 25
        elif profile.conversion_rate > 0.5:
            factors["conversion"] = 20
        elif profile.conversion_rate > 0.3:
            factors["conversion"] = 15
        else:
            factors["conversion"] = max(5, profile.conversion_rate * 25)

        total = sum(factors.values())

        # Generate recommendation
        if total >= 75:
            rec = "Priority: High-value customer. Proactive outreach for new projects."
        elif total >= 50:
            rec = "Engage: Good potential. Schedule follow-up and share new capabilities."
        elif profile.segment == CustomerSegment.AT_RISK:
            rec = "Re-engage: At risk of churning. Offer special pricing or new product options."
        elif profile.segment == CustomerSegment.DORMANT:
            rec = "Win-back: Dormant customer. Send portfolio update and competitive offer."
        elif total >= 25:
            rec = "Nurture: Moderate potential. Add to newsletter and periodic check-ins."
        else:
            rec = "Monitor: Low engagement history. Include in broad marketing."

        return LeadScore(
            company_name=profile.company_name,
            score=total,
            factors=factors,
            recommendation=rec,
        )

    def get_market_insights(self) -> list[dict]:
        """Generate aggregate market insights."""
        insights = []

        if not self._estimates:
            return insights

        # Product type distribution
        product_counts = Counter(
            e.get("product_type", "unknown") for e in self._estimates
        )
        top_products = product_counts.most_common(10)
        insights.append({
            "category": "product_mix",
            "metric": "top_product_types",
            "value": [{"type": t, "count": c} for t, c in top_products],
            "detail": f"Most common product type: {top_products[0][0]} ({top_products[0][1]} orders)" if top_products else "",
        })

        # Revenue by year
        yearly_rev: dict[int, float] = defaultdict(float)
        yearly_count: dict[int, int] = defaultdict(int)
        for est in self._estimates:
            d = est.get("date") or est.get("created_at")
            if d:
                if isinstance(d, str):
                    try:
                        d = datetime.fromisoformat(d)
                    except (ValueError, TypeError):
                        continue
                year = d.year
                cost = float(est.get("total_cost") or est.get("price", 0) or 0)
                yearly_rev[year] += cost
                yearly_count[year] += 1

        if yearly_rev:
            sorted_years = sorted(yearly_rev.keys())
            insights.append({
                "category": "revenue",
                "metric": "annual_revenue",
                "value": [{"year": y, "revenue": round(yearly_rev[y], 2), "orders": yearly_count[y]} for y in sorted_years],
                "trend": "up" if len(sorted_years) >= 2 and yearly_rev[sorted_years[-1]] > yearly_rev[sorted_years[-2]] else "stable",
            })

        # Quantity distribution
        quantities = [e.get("quantity", 0) for e in self._estimates if e.get("quantity", 0) > 0]
        if quantities:
            avg_qty = sum(quantities) / len(quantities)
            insights.append({
                "category": "orders",
                "metric": "quantity_stats",
                "value": {
                    "avg_quantity": round(avg_qty),
                    "min_quantity": min(quantities),
                    "max_quantity": max(quantities),
                    "total_estimates": len(self._estimates),
                    "total_customers": len(self._profiles),
                },
            })

        # Seasonality (orders per month)
        monthly: dict[int, int] = defaultdict(int)
        for est in self._estimates:
            d = est.get("date") or est.get("created_at")
            if d:
                if isinstance(d, str):
                    try:
                        d = datetime.fromisoformat(d)
                    except (ValueError, TypeError):
                        continue
                monthly[d.month] += 1

        if monthly:
            month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            insights.append({
                "category": "seasonality",
                "metric": "orders_by_month",
                "value": [{"month": month_names[m - 1], "orders": monthly[m]} for m in range(1, 13)],
                "detail": f"Peak month: {month_names[max(monthly, key=monthly.get) - 1]}" if monthly else "",
            })

        # Customer concentration (Pareto analysis)
        sorted_profiles = sorted(
            self._profiles.values(),
            key=lambda p: p.total_revenue,
            reverse=True,
        )
        total_rev = sum(p.total_revenue for p in sorted_profiles)
        if total_rev > 0 and sorted_profiles:
            cumulative = Decimal("0")
            top_20_pct_count = max(1, len(sorted_profiles) // 5)
            top_rev = sum(p.total_revenue for p in sorted_profiles[:top_20_pct_count])
            insights.append({
                "category": "concentration",
                "metric": "revenue_concentration",
                "value": {
                    "top_20pct_customers": top_20_pct_count,
                    "top_20pct_revenue_share": round(float(top_rev / total_rev) * 100, 1),
                    "total_revenue": float(total_rev),
                },
                "detail": f"Top {top_20_pct_count} customers account for {float(top_rev / total_rev) * 100:.0f}% of revenue",
            })

        return insights

    def find_similar_companies(self, company_name: str, top_n: int = 5) -> list[dict]:
        """Find companies with similar order profiles for targeting."""
        target_key = company_name.strip().upper()
        target = self._profiles.get(target_key)
        if not target:
            return []

        similarities = []
        for key, profile in self._profiles.items():
            if key == target_key:
                continue

            # Compute similarity based on shared attributes
            score = 0.0

            # Product type overlap
            shared_types = set(target.product_types) & set(profile.product_types)
            if target.product_types:
                score += (len(shared_types) / len(target.product_types)) * 30

            # Quantity similarity
            if target.typical_quantities and profile.typical_quantities:
                t_avg = sum(target.typical_quantities) / len(target.typical_quantities)
                p_avg = sum(profile.typical_quantities) / len(profile.typical_quantities)
                if t_avg > 0:
                    qty_sim = 1 - min(1, abs(t_avg - p_avg) / t_avg)
                    score += qty_sim * 25

            # Order value similarity
            if target.avg_order_value > 0:
                val_sim = 1 - min(1, abs(float(target.avg_order_value - profile.avg_order_value)) / float(target.avg_order_value))
                score += val_sim * 25

            # Complexity match
            if target.typical_complexity == profile.typical_complexity:
                score += 20

            similarities.append({
                "company_name": profile.company_name,
                "similarity_score": round(score, 1),
                "total_orders": profile.total_orders,
                "total_revenue": float(profile.total_revenue),
                "shared_product_types": list(shared_types),
                "segment": profile.segment.value,
            })

        return sorted(similarities, key=lambda x: x["similarity_score"], reverse=True)[:top_n]

    def get_acquisition_targets(self, min_score: float = 30) -> list[dict]:
        """
        Identify acquisition targets - dormant/at-risk customers worth re-engaging,
        and high-potential customers worth expanding.
        """
        targets = []
        for profile in self._profiles.values():
            score = self._score_lead(profile)
            if score.score < min_score:
                continue

            action = "re-engage" if profile.segment in (CustomerSegment.DORMANT, CustomerSegment.AT_RISK) else "expand"
            targets.append({
                "company_name": profile.company_name,
                "action": action,
                "lead_score": round(score.score, 1),
                "segment": profile.segment.value,
                "churn_risk": round(profile.churn_risk, 3),
                "total_revenue": float(profile.total_revenue),
                "total_orders": profile.total_orders,
                "last_order": profile.last_order_date.isoformat() if profile.last_order_date else None,
                "recommendation": score.recommendation,
            })

        return sorted(targets, key=lambda x: x["lead_score"], reverse=True)
