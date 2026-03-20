#!/usr/bin/env python3
"""
Test script for the Companies House Prospect Search functionality.

Run this after:
1. Starting PostgreSQL: docker-compose up -d postgres
2. Running migrations: alembic upgrade head
3. Starting the API: python -m backend.app.main

Usage:
    python scripts/test_prospect_search.py
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.config import get_settings
from backend.app.services.companies_house import CompaniesHouseClient
from backend.app.services.prospect_scoring import get_scoring_service


async def test_api_connection():
    """Test Companies House API connection."""
    print("\n" + "=" * 60)
    print("COMPANIES HOUSE API CONNECTION TEST")
    print("=" * 60)

    settings = get_settings()
    if not settings.companies_house_api_key:
        print("❌ COMPANIES_HOUSE_API_KEY not configured in .env")
        return False

    print(f"✓ API key configured: {settings.companies_house_api_key[:8]}...")

    async with CompaniesHouseClient(api_key=settings.companies_house_api_key) as client:
        # Basic search test
        results = await client.search_companies("packaging", items_per_page=5)
        print(f"✓ API working: Found {results.total_results} companies for 'packaging'")

        # Test company details
        if results.items:
            company = results.items[0]
            profile = await client.get_company(company.company_number)
            if profile:
                print(f"✓ Company details: {profile.company_name} ({profile.company_status})")

    return True


async def test_scoring_service():
    """Test the prospect scoring service."""
    print("\n" + "=" * 60)
    print("PROSPECT SCORING SERVICE TEST")
    print("=" * 60)

    scoring = get_scoring_service()
    print(f"✓ Scoring service initialized (models loaded: {scoring._loaded})")

    if not scoring._loaded:
        print("  ℹ Using default ICP profile (ML models not found or incompatible)")

    # Test scoring with sample data
    result = scoring.score_prospect(
        company_number="12345678",
        company_name="Test Manufacturing Ltd",
        sic_codes=["22220"],  # Plastic packaging manufacturing
        date_of_creation=datetime(2010, 1, 1),
        region="West Midlands",
        officer_count=5,
        filing_count=50,
        has_charges=True,
        has_website=True,
        has_https=True,
    )

    print(f"\n  Sample Manufacturing Company Scoring:")
    print(f"  ├─ Total Score: {result.total_score} ({result.tier.value.upper()})")
    print(f"  ├─ Industry: {result.industry_sector} ({result.industry_score})")
    print(f"  ├─ Packaging Need: {result.packaging_need.value.upper()}")
    print(f"  ├─ Age Score: {result.age_score}")
    print(f"  ├─ Size Score: {result.size_score}")
    print(f"  ├─ Geography Score: {result.geography_score}")
    print(f"  └─ Web Presence Score: {result.web_presence_score}")

    return True


async def test_full_prospect_flow():
    """Test the complete prospect search and scoring flow."""
    print("\n" + "=" * 60)
    print("FULL PROSPECT FLOW TEST")
    print("=" * 60)

    settings = get_settings()
    scoring = get_scoring_service()

    async with CompaniesHouseClient(api_key=settings.companies_house_api_key) as client:
        # Search for packaging manufacturers
        print("\nSearching for active packaging manufacturers...")

        results = await client.search_companies("packaging manufacturer", items_per_page=10)
        print(f"Found {results.total_results} total, fetched {len(results.items)}")

        hot_prospects = []
        warm_prospects = []

        for item in results.items:
            # Enrich with full details
            enriched = await client.enrich_company(item.company_number)
            profile = enriched.get("profile")
            officers = enriched.get("officers", {})
            filings = enriched.get("filings", {})
            charges = enriched.get("charges", {})

            if not profile:
                continue

            # Parse creation date
            creation_date = None
            if profile.get("date_of_creation"):
                try:
                    creation_date = datetime.strptime(
                        profile["date_of_creation"], "%Y-%m-%d"
                    )
                except ValueError:
                    pass

            # Score the prospect
            score = scoring.score_prospect(
                company_number=item.company_number,
                company_name=item.company_name,
                sic_codes=profile.get("sic_codes"),
                date_of_creation=creation_date,
                region=(
                    profile.get("registered_office_address", {}).get("region")
                    if profile.get("registered_office_address")
                    else None
                ),
                officer_count=officers.get("total_results", 0),
                filing_count=filings.get("total_count", 0),
                has_charges=bool(charges.get("items")),
            )

            prospect_info = {
                "name": item.company_name,
                "number": item.company_number,
                "score": score.total_score,
                "tier": score.tier.value,
                "industry": score.industry_sector,
                "packaging_need": score.packaging_need.value,
            }

            if score.tier.value == "hot":
                hot_prospects.append(prospect_info)
            elif score.tier.value == "warm":
                warm_prospects.append(prospect_info)

        print(f"\n🔥 HOT Prospects ({len(hot_prospects)}):")
        for p in hot_prospects[:5]:
            print(f"   {p['name']} - Score: {p['score']} ({p['packaging_need'].upper()})")

        print(f"\n🌡️ WARM Prospects ({len(warm_prospects)}):")
        for p in warm_prospects[:5]:
            print(f"   {p['name']} - Score: {p['score']} ({p['packaging_need'].upper()})")

    return True


async def test_api_endpoints():
    """Test the FastAPI endpoints (requires running server)."""
    print("\n" + "=" * 60)
    print("API ENDPOINT TEST")
    print("=" * 60)

    try:
        import httpx

        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            # Health check
            response = await client.get("/health")
            if response.status_code == 200:
                print("✓ Health endpoint working")
            else:
                print(f"✗ Health check failed: {response.status_code}")
                return False

            # Prospects stats
            response = await client.get("/api/v1/prospects/stats")
            if response.status_code == 200:
                stats = response.json()
                print(f"✓ Prospects stats: {stats.get('total_prospects', 0)} prospects")
            else:
                print(f"ℹ Prospects endpoint returned: {response.status_code}")

    except httpx.ConnectError:
        print("ℹ Server not running - skipping endpoint tests")
        print("  Start the server with: python -m backend.app.main")
        return True
    except ImportError:
        print("ℹ httpx not installed - skipping endpoint tests")
        return True

    return True


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("PackagePro PACKAGING ESTIMATOR - PROSPECT SEARCH TESTS")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")

    tests = [
        ("API Connection", test_api_connection),
        ("Scoring Service", test_scoring_service),
        ("Full Prospect Flow", test_full_prospect_flow),
        ("API Endpoints", test_api_endpoints),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} failed with error: {e}")
            results.append((name, False))

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")

    all_passed = all(r[1] for r in results)
    print("\n" + ("✓ All tests passed!" if all_passed else "✗ Some tests failed"))

    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
