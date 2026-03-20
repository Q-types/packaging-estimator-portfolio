#!/usr/bin/env python3
"""
Tests for the Prospect Scorer module.

Run with:
    pytest tests/test_prospect_scorer.py -v
"""

import json
import pytest
import tempfile
from pathlib import Path

import pandas as pd
import numpy as np

# Add scripts to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from prospect_scorer import (
    ICPAnalyzer,
    ICPProfile,
    ProspectScorer,
    CompaniesHouseLoader,
    sic_to_sector,
    IndustryProfile,
    CompanyAgeProfile,
    CompanySizeProfile,
    GeographicProfile,
    WebPresenceProfile
)


class TestSicToSector:
    """Tests for SIC code to sector mapping."""

    def test_manufacturing_sic(self):
        assert sic_to_sector('18129') == 'Manufacturing'
        assert sic_to_sector('22290') == 'Manufacturing'
        assert sic_to_sector('17230') == 'Manufacturing'

    def test_wholesale_retail_sic(self):
        assert sic_to_sector('47910') == 'Wholesale & Retail'
        assert sic_to_sector('46180') == 'Wholesale & Retail'

    def test_professional_services_sic(self):
        assert sic_to_sector('74100') == 'Professional Services'
        assert sic_to_sector('70100') == 'Professional Services'

    def test_multiple_sic_codes(self):
        # Should take first SIC code
        assert sic_to_sector('18129,82990') == 'Manufacturing'

    def test_empty_sic(self):
        assert sic_to_sector('') == 'Unknown'
        assert sic_to_sector(None) == 'Unknown'

    def test_invalid_sic(self):
        assert sic_to_sector('invalid') == 'Unknown'


class TestICPProfile:
    """Tests for ICP Profile data class."""

    @pytest.fixture
    def sample_icp(self):
        """Create a sample ICP profile for testing."""
        return ICPProfile(
            created_at='2024-01-01T00:00:00',
            total_customers=100,
            high_value_count=30,
            high_value_threshold='High-Value Regulars',
            industry_profiles={
                'Manufacturing': IndustryProfile(
                    sector='Manufacturing',
                    customer_count=50,
                    customer_pct=50.0,
                    high_value_count=20,
                    high_value_pct=66.7,
                    lift_ratio=1.5,
                    avg_monetary=25000,
                    avg_frequency=10,
                    score_weight=100
                )
            },
            company_age=CompanyAgeProfile(
                optimal_min_years=7,
                optimal_max_years=29,
                high_value_median=16,
                high_value_mean=20,
                high_value_std=10,
                all_customer_median=14
            ),
            company_size=CompanySizeProfile(
                optimal_officer_count_min=2,
                optimal_officer_count_max=7,
                optimal_filing_count_min=14,
                optimal_filing_count_max=89,
                high_value_officer_median=4,
                high_value_filing_median=40,
                has_charges_rate=0.4
            ),
            geography=GeographicProfile(
                top_regions=['London', 'Leeds'],
                region_scores={'London': 80, 'Leeds': 90},
                high_value_region_pct={'London': 15, 'Leeds': 5}
            ),
            web_presence=WebPresenceProfile(
                has_website_rate=0.8,
                has_https_rate=0.6,
                high_value_website_rate=0.9,
                website_score_boost=1.12
            ),
            feature_weights={'company_age_years': 100, 'filing_count': 50},
            top_sic_codes=[{'sic_code': '18129', 'lift_ratio': 1.5}],
            model_metrics={'cv_auc_mean': 0.6}
        )

    def test_to_dict(self, sample_icp):
        """Test ICP to dictionary conversion."""
        d = sample_icp.to_dict()
        assert d['total_customers'] == 100
        assert d['high_value_count'] == 30
        assert 'Manufacturing' in d['industry_profiles']

    def test_save_and_load(self, sample_icp):
        """Test saving and loading ICP profile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / 'test_icp.json'
            sample_icp.save(path)

            # Load it back
            loaded = ICPProfile.load(path)

            assert loaded.total_customers == sample_icp.total_customers
            assert loaded.high_value_count == sample_icp.high_value_count
            assert 'Manufacturing' in loaded.industry_profiles


class TestProspectScorer:
    """Tests for the ProspectScorer class."""

    @pytest.fixture
    def scorer(self):
        """Create a scorer with the generated ICP profile."""
        icp_path = Path(__file__).parent.parent / 'models' / 'prospect_scorer' / 'icp_profile.json'
        if not icp_path.exists():
            pytest.skip("ICP profile not found - run build-icp first")
        return ProspectScorer(icp_path=str(icp_path))

    def test_score_manufacturing_company(self, scorer):
        """Test scoring a typical manufacturing company."""
        prospect = {
            'company_name': 'Test Print Ltd',
            'industry_sector': 'Manufacturing',
            'sic_codes': '18129',
            'company_age_years': 15,
            'officer_count': 4,
            'filing_count': 45,
            'has_charges': True,
            'region': 'Leeds',
            'has_website': True,
            'has_https': True
        }

        result = scorer.score_prospect(prospect)

        assert 'prospect_score' in result
        assert 'priority_tier' in result
        assert 'component_scores' in result
        assert 'score_reasons' in result

        # This should be a high-scoring prospect
        assert result['prospect_score'] > 50
        assert result['priority_tier'] in ['Hot', 'Warm']

    def test_score_poor_fit_company(self, scorer):
        """Test scoring a company that's a poor ICP fit."""
        prospect = {
            'company_name': 'New Arts Ltd',
            'industry_sector': 'Arts & Entertainment',
            'company_age_years': 1,
            'officer_count': 1,
            'filing_count': 2,
            'has_charges': False,
            'region': 'Unknown',
            'has_website': False,
            'has_https': False
        }

        result = scorer.score_prospect(prospect)

        # This should be a low-scoring prospect
        assert result['prospect_score'] < 50
        assert result['priority_tier'] in ['Cool', 'Cold']

    def test_score_with_missing_fields(self, scorer):
        """Test that scoring handles missing fields gracefully."""
        prospect = {
            'company_name': 'Minimal Ltd',
            'industry_sector': 'Manufacturing'
        }

        result = scorer.score_prospect(prospect)

        assert 'prospect_score' in result
        # Should still get a reasonable score
        assert 0 <= result['prospect_score'] <= 100

    def test_batch_scoring(self, scorer):
        """Test batch scoring of multiple prospects."""
        prospects = pd.DataFrame([
            {'company_name': 'A Ltd', 'industry_sector': 'Manufacturing', 'company_age_years': 20},
            {'company_name': 'B Ltd', 'industry_sector': 'Retail', 'company_age_years': 5},
            {'company_name': 'C Ltd', 'industry_sector': 'Construction', 'company_age_years': 10},
        ])

        scored = scorer.score_batch(prospects)

        assert len(scored) == 3
        assert 'prospect_score' in scored.columns
        assert 'priority_tier' in scored.columns
        # Should be sorted by score descending
        assert scored['prospect_score'].iloc[0] >= scored['prospect_score'].iloc[1]

    def test_score_industry(self, scorer):
        """Test industry scoring component."""
        score, reason = scorer.score_industry('Manufacturing', '18129')
        assert score > 50  # Manufacturing should score well
        assert 'Manufacturing' in reason or '18129' in reason

    def test_score_company_age(self, scorer):
        """Test company age scoring component."""
        # Optimal age
        score, _ = scorer.score_company_age(16)
        assert score == 100

        # Too young
        score, _ = scorer.score_company_age(2)
        assert score < 100

        # Very old
        score, _ = scorer.score_company_age(60)
        assert score < 100


class TestCompaniesHouseLoader:
    """Tests for the Companies House data loader."""

    def test_extract_region(self):
        """Test postcode to region extraction."""
        loader = CompaniesHouseLoader()

        assert loader.extract_region('LS1 1AA') == 'Leeds'
        assert loader.extract_region('M1 1AE') == 'Manchester'
        assert loader.extract_region('B1 1AA') == 'Birmingham'
        assert loader.extract_region('') == ''

    def test_extract_region_scottish(self):
        """Test Scottish postcodes."""
        loader = CompaniesHouseLoader()

        assert loader.extract_region('EH1 1AA') == 'Edinburgh'
        assert loader.extract_region('G1 1AA') == 'Glasgow'


class TestICPAnalyzer:
    """Tests for the ICP Analyzer."""

    def test_analyzer_loads_data(self):
        """Test that the analyzer can load existing data."""
        base_dir = Path(__file__).parent.parent

        # Check if data files exist
        required_files = [
            base_dir / 'outputs' / 'segmentation' / 'cluster_assignments.csv',
            base_dir / 'data' / 'companies' / 'external_features.csv',
        ]

        for f in required_files:
            if not f.exists():
                pytest.skip(f"Required data file not found: {f}")

        analyzer = ICPAnalyzer()
        df = analyzer.load_data()

        assert len(df) > 0
        assert 'is_high_value' in df.columns


# Integration test
class TestEndToEnd:
    """End-to-end integration tests."""

    def test_full_scoring_pipeline(self):
        """Test the complete scoring pipeline."""
        base_dir = Path(__file__).parent.parent
        icp_path = base_dir / 'models' / 'prospect_scorer' / 'icp_profile.json'

        if not icp_path.exists():
            pytest.skip("ICP profile not found")

        # Load ICP
        icp = ICPProfile.load(icp_path)

        # Create scorer
        scorer = ProspectScorer(icp=icp)

        # Create sample prospects
        prospects = pd.DataFrame([
            {
                'company_name': 'Premium Print Solutions',
                'industry_sector': 'Manufacturing',
                'sic_codes': '18129',
                'company_age_years': 20,
                'officer_count': 5,
                'filing_count': 60,
                'region': 'Leeds',
                'has_website': True,
                'has_https': True
            },
            {
                'company_name': 'Budget Boxes',
                'industry_sector': 'Wholesale & Retail',
                'sic_codes': '47990',
                'company_age_years': 3,
                'officer_count': 1,
                'filing_count': 5,
                'region': 'Unknown',
                'has_website': False,
                'has_https': False
            }
        ])

        # Score
        scored = scorer.score_batch(prospects)

        # Check results
        assert len(scored) == 2
        assert scored.iloc[0]['prospect_score'] > scored.iloc[1]['prospect_score']
        assert scored.iloc[0]['priority_tier'] in ['Hot', 'Warm']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
