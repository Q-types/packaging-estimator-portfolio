"""Tests for the customer analytics engine."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from backend.app.core.customer_analytics import (
    CustomerAnalyticsEngine,
    CustomerProfile,
    CustomerSegment,
)


@pytest.fixture
def sample_estimates():
    """Sample estimate data for testing."""
    now = datetime.now()
    return [
        # Champion customer - frequent, high value, recent
        {"company_name": "Acme Corp", "date": now - timedelta(days=10), "total_cost": 15000, "status": "won", "quantity": 5000, "product_type": "presentation_box", "complexity_tier": 4},
        {"company_name": "Acme Corp", "date": now - timedelta(days=60), "total_cost": 12000, "status": "won", "quantity": 3000, "product_type": "presentation_box", "complexity_tier": 4},
        {"company_name": "Acme Corp", "date": now - timedelta(days=120), "total_cost": 18000, "status": "won", "quantity": 7000, "product_type": "folder", "complexity_tier": 3},
        {"company_name": "Acme Corp", "date": now - timedelta(days=200), "total_cost": 8000, "status": "won", "quantity": 2000, "product_type": "presentation_box", "complexity_tier": 4},
        {"company_name": "Acme Corp", "date": now - timedelta(days=300), "total_cost": 20000, "status": "won", "quantity": 10000, "product_type": "folder", "complexity_tier": 3},
        # Loyal customer - regular orders
        {"company_name": "BigCo Ltd", "date": now - timedelta(days=30), "total_cost": 5000, "status": "won", "quantity": 1000, "product_type": "binder", "complexity_tier": 3},
        {"company_name": "BigCo Ltd", "date": now - timedelta(days=180), "total_cost": 6000, "status": "won", "quantity": 1500, "product_type": "binder", "complexity_tier": 3},
        {"company_name": "BigCo Ltd", "date": now - timedelta(days=350), "total_cost": 4000, "status": "won", "quantity": 800, "product_type": "binder", "complexity_tier": 2},
        # At-risk customer - was active, gone quiet
        {"company_name": "Dormant Inc", "date": now - timedelta(days=200), "total_cost": 3000, "status": "won", "quantity": 500, "product_type": "folder", "complexity_tier": 3},
        {"company_name": "Dormant Inc", "date": now - timedelta(days=400), "total_cost": 7000, "status": "won", "quantity": 2000, "product_type": "folder", "complexity_tier": 3},
        # One-time customer
        {"company_name": "OneShot Co", "date": now - timedelta(days=90), "total_cost": 2000, "status": "won", "quantity": 300, "product_type": "box", "complexity_tier": 2},
        # Lost prospects
        {"company_name": "LostProspect", "date": now - timedelta(days=50), "total_cost": 10000, "status": "lost", "quantity": 5000, "product_type": "presentation_box", "complexity_tier": 4},
        {"company_name": "LostProspect", "date": now - timedelta(days=100), "total_cost": 8000, "status": "lost", "quantity": 3000, "product_type": "presentation_box", "complexity_tier": 4},
        # New potential
        {"company_name": "NewCo", "date": now - timedelta(days=5), "total_cost": 4000, "status": "won", "quantity": 1000, "product_type": "folder", "complexity_tier": 3},
        {"company_name": "NewCo", "date": now - timedelta(days=20), "total_cost": 3500, "status": "won", "quantity": 800, "product_type": "folder", "complexity_tier": 3},
    ]


@pytest.fixture
def analytics_engine(sample_estimates):
    engine = CustomerAnalyticsEngine()
    engine.load_estimates(sample_estimates)
    return engine


class TestProfileBuilding:
    """Test customer profile construction."""

    def test_profiles_created(self, analytics_engine):
        profiles = analytics_engine.get_all_profiles()
        assert len(profiles) == 6  # 6 unique companies

    def test_acme_profile(self, analytics_engine):
        profiles = analytics_engine.get_all_profiles()
        acme = next(p for p in profiles if p["company_name"] == "Acme Corp")
        assert acme["total_orders"] == 5
        assert acme["total_revenue"] == 73000
        assert acme["won_orders"] == 5
        assert acme["conversion_rate"] == 1.0

    def test_one_time_customer(self, analytics_engine):
        profiles = analytics_engine.get_all_profiles()
        one = next(p for p in profiles if p["company_name"] == "OneShot Co")
        assert one["total_orders"] == 1
        assert one["segment"] == "one_time"

    def test_lost_prospect(self, analytics_engine):
        profiles = analytics_engine.get_all_profiles()
        lost = next(p for p in profiles if p["company_name"] == "LostProspect")
        assert lost["lost_orders"] == 2
        assert lost["conversion_rate"] == 0.0


class TestSegmentation:
    """Test customer segmentation."""

    def test_champion_segment(self, analytics_engine):
        profiles = analytics_engine.get_all_profiles()
        acme = next(p for p in profiles if p["company_name"] == "Acme Corp")
        assert acme["segment"] == "champion"

    def test_loyal_segment(self, analytics_engine):
        profiles = analytics_engine.get_all_profiles()
        bigco = next(p for p in profiles if p["company_name"] == "BigCo Ltd")
        assert bigco["segment"] == "loyal"

    def test_segment_summary(self, analytics_engine):
        summary = analytics_engine.get_segment_summary()
        assert isinstance(summary, dict)
        assert all(
            "count" in v and "total_revenue" in v
            for v in summary.values()
        )

    def test_all_segments_have_companies(self, analytics_engine):
        summary = analytics_engine.get_segment_summary()
        total = sum(s["count"] for s in summary.values())
        assert total == 6


class TestLeadScoring:
    """Test lead scoring system."""

    def test_scores_returned(self, analytics_engine):
        scores = analytics_engine.score_leads()
        assert len(scores) == 6

    def test_scores_sorted_descending(self, analytics_engine):
        scores = analytics_engine.score_leads()
        for i in range(len(scores) - 1):
            assert scores[i]["score"] >= scores[i + 1]["score"]

    def test_champion_has_high_score(self, analytics_engine):
        scores = analytics_engine.score_leads()
        acme = next(s for s in scores if s["company_name"] == "Acme Corp")
        assert acme["score"] >= 60  # Champions should score highly

    def test_scores_have_factors(self, analytics_engine):
        scores = analytics_engine.score_leads()
        for score in scores:
            assert "recency" in score["factors"]
            assert "frequency" in score["factors"]
            assert "monetary" in score["factors"]
            assert "conversion" in score["factors"]

    def test_scores_have_recommendations(self, analytics_engine):
        scores = analytics_engine.score_leads()
        for score in scores:
            assert len(score["recommendation"]) > 0


class TestMarketInsights:
    """Test market insight generation."""

    def test_insights_generated(self, analytics_engine):
        insights = analytics_engine.get_market_insights()
        assert len(insights) > 0

    def test_product_mix_insight(self, analytics_engine):
        insights = analytics_engine.get_market_insights()
        product_mix = next((i for i in insights if i["category"] == "product_mix"), None)
        assert product_mix is not None
        assert len(product_mix["value"]) > 0

    def test_order_stats(self, analytics_engine):
        insights = analytics_engine.get_market_insights()
        orders = next((i for i in insights if i["category"] == "orders"), None)
        assert orders is not None
        assert orders["value"]["total_estimates"] == 15
        assert orders["value"]["total_customers"] == 6


class TestSimilarCompanies:
    """Test similar company finder."""

    def test_find_similar(self, analytics_engine):
        similar = analytics_engine.find_similar_companies("Acme Corp", top_n=3)
        assert len(similar) <= 3

    def test_similar_excludes_self(self, analytics_engine):
        similar = analytics_engine.find_similar_companies("Acme Corp")
        names = [s["company_name"] for s in similar]
        assert "Acme Corp" not in names

    def test_similar_has_score(self, analytics_engine):
        similar = analytics_engine.find_similar_companies("Acme Corp")
        for s in similar:
            assert "similarity_score" in s
            assert 0 <= s["similarity_score"] <= 100

    def test_unknown_company_returns_empty(self, analytics_engine):
        similar = analytics_engine.find_similar_companies("NonExistent Ltd")
        assert similar == []


class TestAcquisitionTargets:
    """Test acquisition target identification."""

    def test_targets_returned(self, analytics_engine):
        targets = analytics_engine.get_acquisition_targets(min_score=0)
        assert len(targets) > 0

    def test_targets_sorted_by_score(self, analytics_engine):
        targets = analytics_engine.get_acquisition_targets(min_score=0)
        for i in range(len(targets) - 1):
            assert targets[i]["lead_score"] >= targets[i + 1]["lead_score"]

    def test_targets_have_action(self, analytics_engine):
        targets = analytics_engine.get_acquisition_targets(min_score=0)
        for t in targets:
            assert t["action"] in ("re-engage", "expand")

    def test_min_score_filter(self, analytics_engine):
        high = analytics_engine.get_acquisition_targets(min_score=70)
        low = analytics_engine.get_acquisition_targets(min_score=10)
        assert len(low) >= len(high)


class TestChurnRisk:
    """Test churn risk calculation."""

    def test_recent_customer_low_risk(self, analytics_engine):
        profiles = analytics_engine.get_all_profiles()
        newco = next(p for p in profiles if p["company_name"] == "NewCo")
        assert newco["churn_risk"] < 0.3

    def test_dormant_customer_higher_risk(self, analytics_engine):
        profiles = analytics_engine.get_all_profiles()
        dormant = next(p for p in profiles if p["company_name"] == "Dormant Inc")
        newco = next(p for p in profiles if p["company_name"] == "NewCo")
        assert dormant["churn_risk"] > newco["churn_risk"]


class TestLifetimeValue:
    """Test customer lifetime value estimation."""

    def test_ltv_positive(self, analytics_engine):
        profiles = analytics_engine.get_all_profiles()
        for p in profiles:
            assert p["lifetime_value"] >= 0

    def test_champion_highest_ltv(self, analytics_engine):
        profiles = analytics_engine.get_all_profiles()
        acme = next(p for p in profiles if p["company_name"] == "Acme Corp")
        # Champion should have highest LTV
        assert acme["lifetime_value"] == max(p["lifetime_value"] for p in profiles)


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_estimates(self):
        engine = CustomerAnalyticsEngine()
        engine.load_estimates([])
        assert engine.get_all_profiles() == []
        assert engine.get_segment_summary() == {}
        assert engine.score_leads() == []
        assert engine.get_market_insights() == []

    def test_missing_fields(self):
        engine = CustomerAnalyticsEngine()
        engine.load_estimates([
            {"company_name": "Minimal Co"},
        ])
        profiles = engine.get_all_profiles()
        assert len(profiles) == 1
        assert profiles[0]["total_orders"] == 1

    def test_unknown_company_filtered(self):
        engine = CustomerAnalyticsEngine()
        engine.load_estimates([
            {"total_cost": 100},  # No company name
        ])
        profiles = engine.get_all_profiles()
        assert len(profiles) == 0  # "Unknown" filtered out

    def test_case_insensitive_grouping(self):
        engine = CustomerAnalyticsEngine()
        engine.load_estimates([
            {"company_name": "ACME Corp", "total_cost": 100},
            {"company_name": "acme corp", "total_cost": 200},
            {"company_name": "Acme Corp", "total_cost": 300},
        ])
        profiles = engine.get_all_profiles()
        assert len(profiles) == 1
        assert profiles[0]["total_revenue"] == 600
