#!/usr/bin/env python3
"""
Prospect Scorer for PackagePro Estimator

A B2B lead scoring system that uses Ideal Customer Profile (ICP) analysis to score
prospects from Companies House data. Scores companies on their likelihood to become
high-value customers based on characteristics of existing best customers.

The key insight: We use ONLY pre-purchase characteristics (industry, age, size, location)
to predict customer value - enabling scoring of prospects who have never ordered.

Example Usage:
    from prospect_scorer import ProspectScorer, ICPAnalyzer

    # Step 1: Analyze existing customers to build ICP
    analyzer = ICPAnalyzer(
        customer_data_path='data/companies/company_features.csv',
        segment_assignments_path='outputs/segmentation/cluster_assignments.csv'
    )
    icp_profile = analyzer.build_icp()

    # Step 2: Score prospects
    scorer = ProspectScorer(icp_profile)
    prospects = scorer.load_companies_house_data('data/prospects/uk_companies.csv')
    scored = scorer.score_all(prospects)

    # Get top 100 prospects
    top_prospects = scored.nlargest(100, 'prospect_score')

CLI Usage:
    # Build ICP from existing customers
    python prospect_scorer.py build-icp --output models/icp_profile.json

    # Score a batch of prospects
    python prospect_scorer.py score --icp models/icp_profile.json --prospects data/prospects.csv --output scored_leads.csv

    # Full pipeline
    python prospect_scorer.py pipeline --prospects data/prospects.csv --top-n 500 --output hot_leads.csv

Author: PackagePro Analytics Team
Version: 1.0.0
"""

import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import classification_report, roc_auc_score
import joblib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================================================================
# Path Configuration
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
COMPANIES_DIR = DATA_DIR / "companies"
OUTPUTS_DIR = BASE_DIR / "outputs"
MODELS_DIR = BASE_DIR / "models"

# =============================================================================
# SIC Code Mappings (UK Standard Industrial Classification)
# =============================================================================

# High-level industry sectors from SIC codes
SIC_SECTOR_MAP = {
    # Agriculture
    range(1, 4): "Agriculture",
    # Mining
    range(5, 10): "Mining",
    # Manufacturing (KEY sector for packaging)
    range(10, 34): "Manufacturing",
    # Utilities
    range(35, 40): "Utilities",
    # Construction
    range(41, 44): "Construction",
    # Wholesale & Retail (KEY sector)
    range(45, 48): "Wholesale & Retail",
    # Transportation
    range(49, 54): "Transportation",
    # Accommodation & Food
    range(55, 57): "Accommodation & Food",
    # Information & Communication
    range(58, 64): "Information & Communication",
    # Finance
    range(64, 67): "Finance",
    # Real Estate
    range(68, 69): "Real Estate",
    # Professional Services (KEY sector)
    range(69, 76): "Professional Services",
    # Administrative Services
    range(77, 83): "Administrative Services",
    # Public Administration
    range(84, 85): "Public Administration",
    # Education
    range(85, 86): "Education",
    # Health
    range(86, 89): "Health",
    # Arts & Entertainment
    range(90, 94): "Arts & Entertainment",
    # Other Services
    range(94, 97): "Other Services",
    # Household Activities
    range(97, 99): "Household Activities",
}

# =============================================================================
# PACKAGING NEED CLASSIFICATION
# =============================================================================
# Critical filter: Only target companies that actually NEED packaging solutions

PACKAGING_NEED_HIGH = {
    # Manufacturing - products need packaging
    range(10, 34): "Products need packaging for distribution",
    # Printing - resell packaging to their clients
    range(18, 19): "Printers resell packaging solutions",
    # Wholesale & Retail - distribution/shipping
    range(45, 48): "Shipping and distribution packaging",
}

PACKAGING_NEED_MEDIUM = {
    # Food & Beverage - takeaway, catering packaging
    range(55, 57): "Food service packaging",
    # Advertising/Marketing - marketing materials, folders
    range(73, 74): "Marketing materials, presentation folders",
    # Professional Services with products
    range(74, 75): "Design services, presentations",
    # Administrative/Business Support - fulfillment, packaging services
    range(82, 83): "Fulfillment and business support",
    # Publishing - book packaging, materials
    range(58, 59): "Publishing materials",
}

PACKAGING_NEED_LOW = {
    # Pure services - accountants, lawyers, consultants
    range(69, 72): "Pure services - minimal packaging need",
    # Real estate - limited need
    range(68, 69): "Real estate - limited need",
    # Finance - minimal products
    range(64, 67): "Financial services - minimal need",
    # Education - limited
    range(85, 86): "Education - limited need",
    # Public admin
    range(84, 85): "Public admin - limited need",
}


def get_packaging_need(sic_code: str) -> tuple[str, str]:
    """
    Classify a company's packaging need based on SIC code.

    Returns:
        (need_level, reason): 'HIGH', 'MEDIUM', or 'LOW' with explanation
    """
    if pd.isna(sic_code) or sic_code == '':
        return "UNKNOWN", "No SIC code available"

    # Handle multiple SIC codes (take first)
    if ',' in str(sic_code):
        sic_code = str(sic_code).split(',')[0].strip()

    try:
        sic_int = int(float(str(sic_code)[:2]))

        # Check HIGH need first
        for sic_range, reason in PACKAGING_NEED_HIGH.items():
            if sic_int in sic_range:
                return "HIGH", reason

        # Check MEDIUM need
        for sic_range, reason in PACKAGING_NEED_MEDIUM.items():
            if sic_int in sic_range:
                return "MEDIUM", reason

        # Check LOW need
        for sic_range, reason in PACKAGING_NEED_LOW.items():
            if sic_int in sic_range:
                return "LOW", reason

        # Default: unknown/moderate
        return "MEDIUM", "Industry may have packaging needs"

    except (ValueError, TypeError):
        return "UNKNOWN", "Could not parse SIC code"


def sic_to_sector(sic_code: str) -> str:
    """Convert a SIC code to its industry sector."""
    if pd.isna(sic_code) or sic_code == '':
        return "Unknown"

    # Handle multiple SIC codes (take first)
    if ',' in str(sic_code):
        sic_code = str(sic_code).split(',')[0].strip()

    try:
        sic_int = int(float(str(sic_code)[:2]))  # First 2 digits
        for sic_range, sector in SIC_SECTOR_MAP.items():
            if sic_int in sic_range:
                return sector
        return "Other"
    except (ValueError, TypeError):
        return "Unknown"


# =============================================================================
# Data Classes for ICP Profile
# =============================================================================

@dataclass
class IndustryProfile:
    """Profile of industry representation in customer segments."""
    sector: str
    customer_count: int
    customer_pct: float
    high_value_count: int
    high_value_pct: float
    lift_ratio: float  # How much more likely to be high-value vs baseline
    avg_monetary: float
    avg_frequency: float
    score_weight: float = 0.0  # Contribution to ICP score

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CompanyAgeProfile:
    """Profile of company age characteristics."""
    optimal_min_years: float
    optimal_max_years: float
    high_value_median: float
    high_value_mean: float
    high_value_std: float
    all_customer_median: float
    score_weights: Dict[str, float] = field(default_factory=dict)


@dataclass
class CompanySizeProfile:
    """Profile of company size indicators."""
    optimal_officer_count_min: int
    optimal_officer_count_max: int
    optimal_filing_count_min: int
    optimal_filing_count_max: int
    high_value_officer_median: float
    high_value_filing_median: float
    has_charges_rate: float  # % with charges (indicates established credit)


@dataclass
class GeographicProfile:
    """Profile of geographic distribution."""
    top_regions: List[str]
    region_scores: Dict[str, float]
    high_value_region_pct: Dict[str, float]


@dataclass
class WebPresenceProfile:
    """Profile of web presence characteristics."""
    has_website_rate: float
    has_https_rate: float
    high_value_website_rate: float
    website_score_boost: float


@dataclass
class ICPProfile:
    """Complete Ideal Customer Profile."""
    # Metadata
    created_at: str
    total_customers: int
    high_value_count: int
    high_value_threshold: str  # Cluster name or criteria

    # Component profiles
    industry_profiles: Dict[str, IndustryProfile]
    company_age: CompanyAgeProfile
    company_size: CompanySizeProfile
    geography: GeographicProfile
    web_presence: WebPresenceProfile

    # Scoring weights (learned from data)
    feature_weights: Dict[str, float]

    # Top SIC codes for high-value customers
    top_sic_codes: List[Dict[str, Any]]

    # Model performance metrics
    model_metrics: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        d = {
            'created_at': self.created_at,
            'total_customers': self.total_customers,
            'high_value_count': self.high_value_count,
            'high_value_threshold': self.high_value_threshold,
            'industry_profiles': {k: v.to_dict() if hasattr(v, 'to_dict') else v
                                   for k, v in self.industry_profiles.items()},
            'company_age': asdict(self.company_age) if hasattr(self.company_age, '__dataclass_fields__') else self.company_age,
            'company_size': asdict(self.company_size) if hasattr(self.company_size, '__dataclass_fields__') else self.company_size,
            'geography': asdict(self.geography) if hasattr(self.geography, '__dataclass_fields__') else self.geography,
            'web_presence': asdict(self.web_presence) if hasattr(self.web_presence, '__dataclass_fields__') else self.web_presence,
            'feature_weights': self.feature_weights,
            'top_sic_codes': self.top_sic_codes,
            'model_metrics': self.model_metrics
        }
        return d

    def save(self, path: Union[str, Path]) -> None:
        """Save ICP profile to JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
        logger.info(f"ICP profile saved to {path}")

    @classmethod
    def load(cls, path: Union[str, Path]) -> 'ICPProfile':
        """Load ICP profile from JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)

        # Reconstruct dataclasses
        industry_profiles = {}
        for k, v in data.get('industry_profiles', {}).items():
            industry_profiles[k] = IndustryProfile(**v)

        return cls(
            created_at=data['created_at'],
            total_customers=data['total_customers'],
            high_value_count=data['high_value_count'],
            high_value_threshold=data['high_value_threshold'],
            industry_profiles=industry_profiles,
            company_age=CompanyAgeProfile(**data['company_age']),
            company_size=CompanySizeProfile(**data['company_size']),
            geography=GeographicProfile(**data['geography']),
            web_presence=WebPresenceProfile(**data['web_presence']),
            feature_weights=data['feature_weights'],
            top_sic_codes=data['top_sic_codes'],
            model_metrics=data.get('model_metrics', {})
        )


# =============================================================================
# ICP Analyzer - Builds Ideal Customer Profile from Existing Data
# =============================================================================

class ICPAnalyzer:
    """
    Analyze existing customer data to build an Ideal Customer Profile.

    The ICP identifies which company characteristics correlate with becoming
    a high-value customer, enabling predictive lead scoring.

    Key Analysis:
    1. Industry sector over/under-representation
    2. Company age sweet spot
    3. Company size indicators (officers, filings)
    4. Geographic patterns
    5. Web presence correlation
    """

    def __init__(
        self,
        customer_data_path: Optional[str] = None,
        segment_assignments_path: Optional[str] = None,
        external_features_path: Optional[str] = None,
        deep_features_path: Optional[str] = None,
        web_features_path: Optional[str] = None
    ):
        """
        Initialize analyzer with paths to data files.

        Args:
            customer_data_path: Path to company_features.csv (merged dataset)
            segment_assignments_path: Path to cluster_assignments.csv
            external_features_path: Path to external_features.csv (Companies House data)
            deep_features_path: Path to deep_features.csv (officers, filings)
            web_features_path: Path to web_features.csv
        """
        # Set default paths
        self.customer_data_path = Path(customer_data_path or COMPANIES_DIR / "company_features.csv")
        self.segment_path = Path(segment_assignments_path or OUTPUTS_DIR / "segmentation" / "cluster_assignments.csv")
        self.external_path = Path(external_features_path or COMPANIES_DIR / "external_features.csv")
        self.deep_path = Path(deep_features_path or COMPANIES_DIR / "deep_features.csv")
        self.web_path = Path(web_features_path or COMPANIES_DIR / "web_features.csv")

        # Data containers
        self.customer_df: Optional[pd.DataFrame] = None
        self.segments_df: Optional[pd.DataFrame] = None
        self.external_df: Optional[pd.DataFrame] = None
        self.deep_df: Optional[pd.DataFrame] = None
        self.web_df: Optional[pd.DataFrame] = None
        self.merged_df: Optional[pd.DataFrame] = None

        # High-value customer criteria
        self.high_value_segments = ["High-Value Regulars", "VIP Champions"]

    def load_data(self) -> pd.DataFrame:
        """Load and merge all data sources."""
        logger.info("Loading customer data...")

        # Load segment assignments
        self.segments_df = pd.read_csv(self.segment_path)
        logger.info(f"  Loaded {len(self.segments_df)} segment assignments")

        # Load external features (Companies House basic)
        self.external_df = pd.read_csv(self.external_path)
        logger.info(f"  Loaded {len(self.external_df)} external feature records")

        # Load deep features (officers, filings)
        self.deep_df = pd.read_csv(self.deep_path)
        logger.info(f"  Loaded {len(self.deep_df)} deep feature records")

        # Load web features
        self.web_df = pd.read_csv(self.web_path)
        logger.info(f"  Loaded {len(self.web_df)} web feature records")

        # Load full customer features (includes RFM)
        self.customer_df = pd.read_csv(self.customer_data_path)
        logger.info(f"  Loaded {len(self.customer_df)} customer records")

        # Merge all data
        self.merged_df = self.segments_df.merge(
            self.external_df, on='company', how='left'
        ).merge(
            self.deep_df, on='company', how='left'
        ).merge(
            self.web_df, on='company', how='left'
        )

        # Add high_value flag
        self.merged_df['is_high_value'] = self.merged_df['business_segment'].isin(
            self.high_value_segments
        ).astype(int)

        logger.info(f"Merged dataset: {len(self.merged_df)} companies")
        logger.info(f"  High-value customers: {self.merged_df['is_high_value'].sum()}")

        return self.merged_df

    def analyze_industry(self) -> Dict[str, IndustryProfile]:
        """Analyze industry sector distribution and lift ratios."""
        logger.info("Analyzing industry distribution...")

        df = self.merged_df.copy()

        # Overall counts
        total = len(df)
        high_value_total = df['is_high_value'].sum()
        baseline_hv_rate = high_value_total / total if total > 0 else 0

        # Group by industry
        industry_profiles = {}

        for sector in df['industry_sector'].dropna().unique():
            sector_df = df[df['industry_sector'] == sector]
            sector_count = len(sector_df)
            sector_hv = sector_df['is_high_value'].sum()

            if sector_count == 0:
                continue

            sector_hv_rate = sector_hv / sector_count
            lift = sector_hv_rate / baseline_hv_rate if baseline_hv_rate > 0 else 1.0

            # Calculate average RFM metrics (from customer_df if available)
            avg_monetary = 0
            avg_frequency = 0
            if 'monetary_total' in self.customer_df.columns:
                matched = self.customer_df[self.customer_df['company'].isin(sector_df['company'])]
                if len(matched) > 0:
                    avg_monetary = matched['monetary_total'].mean()
                    avg_frequency = matched['frequency'].mean() if 'frequency' in matched.columns else 0

            industry_profiles[sector] = IndustryProfile(
                sector=sector,
                customer_count=sector_count,
                customer_pct=sector_count / total * 100,
                high_value_count=sector_hv,
                high_value_pct=sector_hv / high_value_total * 100 if high_value_total > 0 else 0,
                lift_ratio=lift,
                avg_monetary=avg_monetary,
                avg_frequency=avg_frequency
            )

        # Calculate score weights based on lift ratio
        max_lift = max(p.lift_ratio for p in industry_profiles.values()) if industry_profiles else 1.0
        for profile in industry_profiles.values():
            # Normalize lift to 0-100 score
            profile.score_weight = (profile.lift_ratio / max_lift) * 100 if max_lift > 0 else 50

        # Log top industries
        sorted_industries = sorted(
            industry_profiles.values(),
            key=lambda x: x.lift_ratio,
            reverse=True
        )
        logger.info("  Top industries by lift ratio:")
        for p in sorted_industries[:5]:
            logger.info(f"    {p.sector}: lift={p.lift_ratio:.2f}, count={p.customer_count}, HV%={p.high_value_pct:.1f}%")

        return industry_profiles

    def analyze_company_age(self) -> CompanyAgeProfile:
        """Analyze company age distribution for high-value customers."""
        logger.info("Analyzing company age distribution...")

        df = self.merged_df.copy()
        df = df[df['company_age_years'].notna()]

        all_ages = df['company_age_years']
        hv_ages = df[df['is_high_value'] == 1]['company_age_years']

        # Find optimal age range (interquartile range of high-value customers)
        hv_q1 = hv_ages.quantile(0.25) if len(hv_ages) > 0 else 0
        hv_q3 = hv_ages.quantile(0.75) if len(hv_ages) > 0 else 50

        profile = CompanyAgeProfile(
            optimal_min_years=float(hv_q1),
            optimal_max_years=float(hv_q3),
            high_value_median=float(hv_ages.median()) if len(hv_ages) > 0 else 15,
            high_value_mean=float(hv_ages.mean()) if len(hv_ages) > 0 else 15,
            high_value_std=float(hv_ages.std()) if len(hv_ages) > 0 else 10,
            all_customer_median=float(all_ages.median()),
            score_weights={
                'too_young': 0.5,    # <5 years
                'young': 0.7,        # 5-10 years
                'optimal': 1.0,      # 10-30 years
                'mature': 0.9,       # 30-50 years
                'very_mature': 0.7   # >50 years
            }
        )

        logger.info(f"  Optimal age range: {profile.optimal_min_years:.1f} - {profile.optimal_max_years:.1f} years")
        logger.info(f"  High-value median: {profile.high_value_median:.1f} years")

        return profile

    def analyze_company_size(self) -> CompanySizeProfile:
        """Analyze company size indicators (officers, filings)."""
        logger.info("Analyzing company size indicators...")

        df = self.merged_df.copy()
        hv_df = df[df['is_high_value'] == 1]

        # Officer count analysis
        hv_officers = hv_df['officer_count'].dropna()
        officer_q1 = hv_officers.quantile(0.25) if len(hv_officers) > 0 else 1
        officer_q3 = hv_officers.quantile(0.75) if len(hv_officers) > 0 else 10

        # Filing count analysis
        hv_filings = hv_df['filing_count'].dropna()
        filing_q1 = hv_filings.quantile(0.25) if len(hv_filings) > 0 else 10
        filing_q3 = hv_filings.quantile(0.75) if len(hv_filings) > 0 else 100

        # Charges rate (indicates credit activity = established business)
        has_charges_rate = 0.0
        if 'has_charges' in hv_df.columns:
            has_charges_rate = hv_df['has_charges'].mean()

        profile = CompanySizeProfile(
            optimal_officer_count_min=int(officer_q1),
            optimal_officer_count_max=int(officer_q3),
            optimal_filing_count_min=int(filing_q1),
            optimal_filing_count_max=int(filing_q3),
            high_value_officer_median=float(hv_officers.median()) if len(hv_officers) > 0 else 3,
            high_value_filing_median=float(hv_filings.median()) if len(hv_filings) > 0 else 50,
            has_charges_rate=float(has_charges_rate)
        )

        logger.info(f"  Optimal officer count: {profile.optimal_officer_count_min} - {profile.optimal_officer_count_max}")
        logger.info(f"  Optimal filing count: {profile.optimal_filing_count_min} - {profile.optimal_filing_count_max}")
        logger.info(f"  Has charges rate (HV): {profile.has_charges_rate:.1%}")

        return profile

    def analyze_geography(self) -> GeographicProfile:
        """Analyze geographic distribution of high-value customers."""
        logger.info("Analyzing geographic distribution...")

        df = self.merged_df.copy()

        # Get region from external features
        region_col = 'region' if 'region' in df.columns else None
        if region_col is None:
            logger.warning("No region column found")
            return GeographicProfile(
                top_regions=[],
                region_scores={},
                high_value_region_pct={}
            )

        # Calculate region statistics
        total = len(df)
        hv_total = df['is_high_value'].sum()
        baseline_rate = hv_total / total if total > 0 else 0

        region_stats = {}
        for region in df[region_col].dropna().unique():
            region_df = df[df[region_col] == region]
            region_count = len(region_df)
            region_hv = region_df['is_high_value'].sum()

            if region_count < 5:  # Skip regions with too few customers
                continue

            hv_rate = region_hv / region_count
            lift = hv_rate / baseline_rate if baseline_rate > 0 else 1.0

            region_stats[region] = {
                'count': region_count,
                'hv_count': region_hv,
                'hv_rate': hv_rate,
                'lift': lift,
                'hv_pct': region_hv / hv_total * 100 if hv_total > 0 else 0
            }

        # Sort by lift ratio
        sorted_regions = sorted(region_stats.items(), key=lambda x: x[1]['lift'], reverse=True)

        # Get top regions and scores
        top_regions = [r[0] for r in sorted_regions[:10]]
        max_lift = max(r[1]['lift'] for r in sorted_regions) if sorted_regions else 1.0

        region_scores = {
            r: stats['lift'] / max_lift * 100
            for r, stats in region_stats.items()
        }

        hv_region_pct = {
            r: stats['hv_pct']
            for r, stats in region_stats.items()
        }

        profile = GeographicProfile(
            top_regions=top_regions,
            region_scores=region_scores,
            high_value_region_pct=hv_region_pct
        )

        logger.info(f"  Top regions: {', '.join(top_regions[:5])}")

        return profile

    def analyze_web_presence(self) -> WebPresenceProfile:
        """Analyze web presence correlation with customer value."""
        logger.info("Analyzing web presence...")

        df = self.merged_df.copy()
        hv_df = df[df['is_high_value'] == 1]

        # Website presence
        has_website_all = df['has_website'].mean() if 'has_website' in df.columns else 0.5
        has_website_hv = hv_df['has_website'].mean() if 'has_website' in hv_df.columns else 0.5

        # HTTPS (security consciousness)
        has_https_all = df['has_https'].mean() if 'has_https' in df.columns else 0.3
        has_https_hv = hv_df['has_https'].mean() if 'has_https' in hv_df.columns else 0.4

        # Calculate boost factor
        website_boost = has_website_hv / has_website_all if has_website_all > 0 else 1.0

        profile = WebPresenceProfile(
            has_website_rate=float(has_website_all),
            has_https_rate=float(has_https_all),
            high_value_website_rate=float(has_website_hv),
            website_score_boost=float(website_boost)
        )

        logger.info(f"  Website rate (all): {profile.has_website_rate:.1%}")
        logger.info(f"  Website rate (HV): {profile.high_value_website_rate:.1%}")
        logger.info(f"  Website boost factor: {profile.website_score_boost:.2f}x")

        return profile

    def analyze_sic_codes(self) -> List[Dict[str, Any]]:
        """Analyze specific SIC codes over-represented in high-value customers."""
        logger.info("Analyzing SIC code distribution...")

        df = self.merged_df.copy()

        # Parse SIC codes
        def get_sic_list(sic_str):
            if pd.isna(sic_str) or sic_str == '':
                return []
            return [s.strip() for s in str(sic_str).split(',')]

        df['sic_list'] = df['sic_codes'].apply(get_sic_list)

        # Explode to one row per SIC code
        sic_df = df.explode('sic_list')
        sic_df = sic_df[sic_df['sic_list'] != '']

        # Calculate stats per SIC code
        total = len(df)
        hv_total = df['is_high_value'].sum()
        baseline_rate = hv_total / total if total > 0 else 0

        sic_stats = []
        for sic in sic_df['sic_list'].dropna().unique():
            if sic == '':
                continue

            sic_data = sic_df[sic_df['sic_list'] == sic]
            count = len(sic_data.drop_duplicates('company'))
            hv_count = sic_data[sic_data['is_high_value'] == 1]['company'].nunique()

            if count < 3:  # Skip rare SIC codes
                continue

            hv_rate = hv_count / count
            lift = hv_rate / baseline_rate if baseline_rate > 0 else 1.0

            sic_stats.append({
                'sic_code': sic,
                'sector': sic_to_sector(sic),
                'customer_count': count,
                'high_value_count': hv_count,
                'high_value_rate': hv_rate,
                'lift_ratio': lift
            })

        # Sort by lift ratio
        sic_stats.sort(key=lambda x: x['lift_ratio'], reverse=True)

        logger.info("  Top SIC codes by lift:")
        for s in sic_stats[:10]:
            logger.info(f"    {s['sic_code']} ({s['sector']}): lift={s['lift_ratio']:.2f}, count={s['customer_count']}")

        return sic_stats[:50]  # Return top 50

    def train_lookalike_model(self) -> Tuple[Any, Dict[str, float], Dict[str, float]]:
        """
        Train a classification model to predict high-value customer likelihood.

        Returns:
            model: Trained classifier
            feature_weights: Importance of each feature
            metrics: Model performance metrics
        """
        logger.info("Training lookalike classification model...")

        df = self.merged_df.copy()

        # Define features (pre-purchase characteristics only)
        feature_cols = [
            'company_age_years',
            'officer_count',
            'filing_count',
            'has_charges',
            'has_website',
            'has_https'
        ]

        # Add industry encoding
        if 'industry_sector' in df.columns:
            # Top industries to encode
            top_industries = df['industry_sector'].value_counts().head(10).index.tolist()
            for ind in top_industries:
                col_name = f'ind_{ind.lower().replace(" ", "_").replace("&", "and")}'
                df[col_name] = (df['industry_sector'] == ind).astype(int)
                feature_cols.append(col_name)

        # Prepare features
        X = df[feature_cols].copy()

        # Handle missing values
        for col in X.columns:
            if X[col].dtype == 'bool':
                X[col] = X[col].astype(int)
            X[col] = X[col].fillna(X[col].median())

        y = df['is_high_value']

        # Handle class imbalance
        logger.info(f"  Class distribution: {y.value_counts().to_dict()}")

        # Train model with cross-validation
        # Using Gradient Boosting - good for imbalanced data and interpretability
        model = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=4,
            min_samples_leaf=10,
            learning_rate=0.1,
            random_state=42
        )

        # Cross-validation
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        cv_scores = cross_val_score(model, X, y, cv=cv, scoring='roc_auc')

        logger.info(f"  Cross-validation AUC: {cv_scores.mean():.3f} (+/- {cv_scores.std()*2:.3f})")

        # Fit on full data for feature importance
        model.fit(X, y)

        # Feature importance
        feature_importance = dict(zip(feature_cols, model.feature_importances_))
        sorted_importance = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)

        logger.info("  Feature importance:")
        for feat, imp in sorted_importance[:10]:
            logger.info(f"    {feat}: {imp:.4f}")

        # Normalize to weights (0-100)
        max_imp = max(feature_importance.values())
        feature_weights = {
            k: v / max_imp * 100
            for k, v in feature_importance.items()
        }

        metrics = {
            'cv_auc_mean': float(cv_scores.mean()),
            'cv_auc_std': float(cv_scores.std()),
            'n_features': len(feature_cols),
            'n_samples': len(X),
            'positive_rate': float(y.mean())
        }

        return model, feature_weights, metrics

    def build_icp(self) -> ICPProfile:
        """
        Build complete Ideal Customer Profile.

        Returns:
            ICPProfile with all analysis components
        """
        logger.info("="*60)
        logger.info("Building Ideal Customer Profile")
        logger.info("="*60)

        # Load all data
        self.load_data()

        # Run all analyses
        industry_profiles = self.analyze_industry()
        company_age = self.analyze_company_age()
        company_size = self.analyze_company_size()
        geography = self.analyze_geography()
        web_presence = self.analyze_web_presence()
        top_sic_codes = self.analyze_sic_codes()

        # Train ML model for weights
        model, feature_weights, model_metrics = self.train_lookalike_model()

        # Save model separately
        model_path = MODELS_DIR / "prospect_scorer" / "lookalike_model.joblib"
        model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, model_path)
        logger.info(f"Lookalike model saved to {model_path}")

        # Create ICP profile
        icp = ICPProfile(
            created_at=datetime.now().isoformat(),
            total_customers=len(self.merged_df),
            high_value_count=int(self.merged_df['is_high_value'].sum()),
            high_value_threshold=", ".join(self.high_value_segments),
            industry_profiles=industry_profiles,
            company_age=company_age,
            company_size=company_size,
            geography=geography,
            web_presence=web_presence,
            feature_weights=feature_weights,
            top_sic_codes=top_sic_codes,
            model_metrics=model_metrics
        )

        logger.info("="*60)
        logger.info("ICP Profile Complete")
        logger.info(f"  Total customers analyzed: {icp.total_customers}")
        logger.info(f"  High-value customers: {icp.high_value_count}")
        logger.info(f"  Model AUC: {model_metrics['cv_auc_mean']:.3f}")
        logger.info("="*60)

        return icp


# =============================================================================
# Prospect Scorer - Scores New Companies Using ICP
# =============================================================================

class ProspectScorer:
    """
    Score prospects based on their likelihood to become high-value customers.

    Uses the ICP profile to calculate composite scores based on:
    - Industry match (SIC codes)
    - Company age fit
    - Size indicators
    - Geographic location
    - Web presence

    Plus ML model predictions when available.
    """

    def __init__(
        self,
        icp: Optional[ICPProfile] = None,
        icp_path: Optional[str] = None,
        model_path: Optional[str] = None
    ):
        """
        Initialize scorer with ICP profile.

        Args:
            icp: ICPProfile object
            icp_path: Path to saved ICP profile JSON
            model_path: Path to trained lookalike model
        """
        if icp is not None:
            self.icp = icp
        elif icp_path is not None:
            self.icp = ICPProfile.load(icp_path)
        else:
            raise ValueError("Must provide either icp or icp_path")

        # Load ML model if available
        self.model = None
        model_file = Path(model_path or MODELS_DIR / "prospect_scorer" / "lookalike_model.joblib")
        if model_file.exists():
            try:
                self.model = joblib.load(model_file)
                logger.info(f"Loaded lookalike model from {model_file}")
            except Exception as e:
                logger.warning(f"Could not load ML model: {e}")
                logger.info("Proceeding with rule-based scoring only")

        # Precompute score lookups
        self._build_score_lookups()

    def _build_score_lookups(self):
        """Precompute lookup tables for fast scoring."""
        # Industry scores
        self.industry_scores = {
            k: v.score_weight
            for k, v in self.icp.industry_profiles.items()
        }
        self.default_industry_score = 50  # Neutral for unknown industries

        # SIC code scores
        self.sic_scores = {}
        max_lift = max(s['lift_ratio'] for s in self.icp.top_sic_codes) if self.icp.top_sic_codes else 1.0
        for sic in self.icp.top_sic_codes:
            score = sic['lift_ratio'] / max_lift * 100
            self.sic_scores[str(sic['sic_code'])] = score

        # Region scores
        self.region_scores = self.icp.geography.region_scores
        self.default_region_score = 50

    def score_industry(self, industry_sector: str, sic_codes: str = None) -> Tuple[float, str]:
        """
        Score a prospect based on industry.

        Returns:
            (score 0-100, explanation string)
        """
        score = self.default_industry_score
        reason = "Unknown industry"

        # Try industry sector first
        if industry_sector and industry_sector in self.industry_scores:
            score = self.industry_scores[industry_sector]
            profile = self.icp.industry_profiles.get(industry_sector)
            if profile:
                reason = f"{industry_sector}: lift ratio {profile.lift_ratio:.2f}x"

        # Boost with specific SIC codes
        if sic_codes:
            sic_list = [s.strip() for s in str(sic_codes).split(',')]
            for sic in sic_list:
                if sic in self.sic_scores:
                    sic_score = self.sic_scores[sic]
                    if sic_score > score:
                        score = sic_score
                        reason = f"SIC {sic}: high-value indicator"

        return score, reason

    def score_company_age(self, age_years: float) -> Tuple[float, str]:
        """Score based on company age."""
        if pd.isna(age_years):
            return 50, "Unknown age"

        profile = self.icp.company_age

        # Score based on distance from optimal range
        if profile.optimal_min_years <= age_years <= profile.optimal_max_years:
            score = 100
            reason = f"Optimal age: {age_years:.1f} years (target: {profile.optimal_min_years:.0f}-{profile.optimal_max_years:.0f})"
        elif age_years < profile.optimal_min_years:
            # Too young - score proportionally
            score = max(30, 100 - (profile.optimal_min_years - age_years) * 5)
            reason = f"Young company: {age_years:.1f} years"
        else:
            # Older - still valuable but slight penalty
            score = max(60, 100 - (age_years - profile.optimal_max_years) * 1)
            reason = f"Established: {age_years:.1f} years"

        return score, reason

    def score_company_size(
        self,
        officer_count: int,
        filing_count: int,
        has_charges: bool = False
    ) -> Tuple[float, str]:
        """Score based on company size indicators."""
        scores = []
        reasons = []

        profile = self.icp.company_size

        # Officer count
        if pd.notna(officer_count):
            if profile.optimal_officer_count_min <= officer_count <= profile.optimal_officer_count_max:
                scores.append(100)
                reasons.append(f"Optimal officers: {officer_count}")
            elif officer_count < profile.optimal_officer_count_min:
                score = max(40, 100 - (profile.optimal_officer_count_min - officer_count) * 10)
                scores.append(score)
                reasons.append(f"Small team: {officer_count} officers")
            else:
                score = max(70, 100 - (officer_count - profile.optimal_officer_count_max) * 2)
                scores.append(score)
                reasons.append(f"Large org: {officer_count} officers")

        # Filing count (indicates established business)
        if pd.notna(filing_count):
            if profile.optimal_filing_count_min <= filing_count <= profile.optimal_filing_count_max:
                scores.append(100)
                reasons.append(f"Good filing history: {filing_count}")
            elif filing_count < profile.optimal_filing_count_min:
                score = max(40, 100 - (profile.optimal_filing_count_min - filing_count))
                scores.append(score)
                reasons.append(f"Limited history: {filing_count} filings")
            else:
                scores.append(90)  # More is generally fine
                reasons.append(f"Extensive history: {filing_count} filings")

        # Has charges (indicates credit activity)
        if has_charges and profile.has_charges_rate > 0.3:
            scores.append(80)
            reasons.append("Has credit charges (established)")

        if not scores:
            return 50, "Insufficient size data"

        return np.mean(scores), "; ".join(reasons)

    def score_geography(self, region: str) -> Tuple[float, str]:
        """Score based on geographic location."""
        if pd.isna(region) or region == '':
            return 50, "Unknown region"

        if region in self.region_scores:
            score = self.region_scores[region]
            is_top = region in self.icp.geography.top_regions
            reason = f"Region: {region}" + (" (high-value area)" if is_top else "")
            return score, reason

        return self.default_region_score, f"Region: {region}"

    def score_web_presence(
        self,
        has_website: bool,
        has_https: bool = False
    ) -> Tuple[float, str]:
        """Score based on web presence."""
        profile = self.icp.web_presence

        if has_website:
            base_score = 70
            reason = "Has website"

            # HTTPS bonus
            if has_https:
                base_score += 20
                reason += " with HTTPS"

            # Apply boost from ICP
            score = min(100, base_score * profile.website_score_boost)
            return score, reason
        else:
            return 40, "No website detected"

    def score_prospect(self, prospect: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate composite prospect score with detailed breakdown.

        Args:
            prospect: Dictionary with prospect data

        Returns:
            Dictionary with:
            - prospect_score: Overall score 0-100
            - component_scores: Individual dimension scores
            - score_reasons: Explanations for each score
            - ml_probability: Model prediction if available
            - priority_tier: "Hot", "Warm", "Cool", "Cold"
        """
        # Extract fields
        industry = prospect.get('industry_sector', '')
        sic_codes = prospect.get('sic_codes', '')
        age = prospect.get('company_age_years')
        officers = prospect.get('officer_count')
        filings = prospect.get('filing_count')
        has_charges = prospect.get('has_charges', False)
        region = prospect.get('region', '')
        has_website = prospect.get('has_website', False)
        has_https = prospect.get('has_https', False)

        # Calculate component scores
        industry_score, industry_reason = self.score_industry(industry, sic_codes)
        age_score, age_reason = self.score_company_age(age)
        size_score, size_reason = self.score_company_size(officers, filings, has_charges)
        geo_score, geo_reason = self.score_geography(region)
        web_score, web_reason = self.score_web_presence(has_website, has_https)

        # CRITICAL: Assess packaging need based on SIC code
        packaging_need, packaging_reason = get_packaging_need(sic_codes)

        # Component weights (from ICP feature importance)
        weights = {
            'industry': 0.30,
            'company_age': 0.20,
            'company_size': 0.25,
            'geography': 0.10,
            'web_presence': 0.15
        }

        # Calculate weighted score
        composite_score = (
            industry_score * weights['industry'] +
            age_score * weights['company_age'] +
            size_score * weights['company_size'] +
            geo_score * weights['geography'] +
            web_score * weights['web_presence']
        )

        # Apply packaging need multiplier - penalize companies with low packaging need
        packaging_multipliers = {
            'HIGH': 1.0,      # Full score for high-need companies
            'MEDIUM': 0.85,   # 15% penalty for medium-need
            'LOW': 0.60,      # 40% penalty for low-need
            'UNKNOWN': 0.75   # 25% penalty for unknown
        }
        packaging_multiplier = packaging_multipliers.get(packaging_need, 0.75)
        composite_score = composite_score * packaging_multiplier

        # ML model prediction if available
        ml_probability = None
        if self.model is not None:
            try:
                # Prepare features for model
                features = self._prepare_ml_features(prospect)
                ml_probability = float(self.model.predict_proba([features])[0][1])

                # Blend with rule-based score (70% rules, 30% ML)
                composite_score = composite_score * 0.7 + ml_probability * 100 * 0.3
            except Exception as e:
                logger.debug(f"ML prediction failed: {e}")

        # Priority tier
        if composite_score >= 75:
            tier = "Hot"
        elif composite_score >= 60:
            tier = "Warm"
        elif composite_score >= 45:
            tier = "Cool"
        else:
            tier = "Cold"

        return {
            'prospect_score': round(composite_score, 2),
            'priority_tier': tier,
            'packaging_need': packaging_need,
            'packaging_reason': packaging_reason,
            'packaging_multiplier': packaging_multiplier,
            'component_scores': {
                'industry': round(industry_score, 2),
                'company_age': round(age_score, 2),
                'company_size': round(size_score, 2),
                'geography': round(geo_score, 2),
                'web_presence': round(web_score, 2)
            },
            'score_reasons': {
                'industry': industry_reason,
                'company_age': age_reason,
                'company_size': size_reason,
                'geography': geo_reason,
                'web_presence': web_reason
            },
            'ml_probability': ml_probability
        }

    def _prepare_ml_features(self, prospect: Dict[str, Any]) -> List[float]:
        """Prepare feature vector for ML model."""
        # This should match the features used in ICPAnalyzer.train_lookalike_model
        features = [
            float(prospect.get('company_age_years', 15) or 15),
            float(prospect.get('officer_count', 3) or 3),
            float(prospect.get('filing_count', 36) or 36),
            1.0 if prospect.get('has_charges', False) else 0.0,
            1.0 if prospect.get('has_website', False) else 0.0,
            1.0 if prospect.get('has_https', False) else 0.0
        ]

        # Add industry dummies (must match training)
        top_industries = [
            'Manufacturing', 'Wholesale & Retail', 'Professional Services',
            'Administrative Services', 'Construction', 'Information & Communication',
            'Other Services', 'Real Estate', 'Accommodation & Food', 'Finance'
        ]
        industry = prospect.get('industry_sector', '')
        for ind in top_industries:
            features.append(1.0 if industry == ind else 0.0)

        return features

    def score_batch(self, prospects_df: pd.DataFrame) -> pd.DataFrame:
        """
        Score a batch of prospects.

        Args:
            prospects_df: DataFrame with prospect data

        Returns:
            DataFrame with original columns plus score columns
        """
        logger.info(f"Scoring {len(prospects_df)} prospects...")

        results = []
        for idx, row in prospects_df.iterrows():
            prospect_dict = row.to_dict()
            score_result = self.score_prospect(prospect_dict)

            # Flatten nested dicts
            flat_result = {
                'prospect_score': score_result['prospect_score'],
                'priority_tier': score_result['priority_tier'],
                'ml_probability': score_result['ml_probability'],
            }
            for k, v in score_result['component_scores'].items():
                flat_result[f'score_{k}'] = v
            for k, v in score_result['score_reasons'].items():
                flat_result[f'reason_{k}'] = v

            results.append(flat_result)

        scores_df = pd.DataFrame(results)

        # Merge with original
        result_df = pd.concat([prospects_df.reset_index(drop=True), scores_df], axis=1)

        # Sort by score
        result_df = result_df.sort_values('prospect_score', ascending=False)

        logger.info(f"  Hot leads: {(result_df['priority_tier'] == 'Hot').sum()}")
        logger.info(f"  Warm leads: {(result_df['priority_tier'] == 'Warm').sum()}")
        logger.info(f"  Cool leads: {(result_df['priority_tier'] == 'Cool').sum()}")
        logger.info(f"  Cold leads: {(result_df['priority_tier'] == 'Cold').sum()}")

        return result_df


# =============================================================================
# Companies House Data Loader
# =============================================================================

class CompaniesHouseLoader:
    """
    Load and preprocess Companies House bulk data for prospect scoring.

    Data Sources:
    - Companies House free bulk data (basic company data)
    - SIC code lookup files
    - Postcode to region mapping
    """

    def __init__(self):
        self.postcode_regions = self._load_postcode_mapping()

    def _load_postcode_mapping(self) -> Dict[str, str]:
        """Load postcode area to region mapping."""
        # Basic UK postcode area to region mapping
        return {
            # London
            'E': 'London', 'EC': 'London', 'N': 'London', 'NW': 'London',
            'SE': 'London', 'SW': 'London', 'W': 'London', 'WC': 'London',
            # South East
            'BN': 'Brighton', 'CT': 'Kent', 'DA': 'Kent', 'GU': 'Surrey',
            'HP': 'Buckinghamshire', 'KT': 'Surrey', 'ME': 'Kent', 'MK': 'Milton Keynes',
            'OX': 'Oxford', 'RG': 'Reading', 'RH': 'Surrey', 'SL': 'Berkshire',
            'TN': 'Kent', 'TW': 'Middlesex',
            # Midlands
            'B': 'Birmingham', 'CV': 'Coventry', 'DE': 'Derby', 'DY': 'West Midlands',
            'LE': 'Leicester', 'NG': 'Nottingham', 'NN': 'Northampton', 'ST': 'Staffordshire',
            'WS': 'West Midlands', 'WV': 'Wolverhampton',
            # North West
            'BB': 'Lancashire', 'BL': 'Bolton', 'CA': 'Cumbria', 'CH': 'Cheshire',
            'CW': 'Cheshire', 'FY': 'Blackpool', 'L': 'Liverpool', 'LA': 'Lancashire',
            'M': 'Manchester', 'OL': 'Oldham', 'PR': 'Preston', 'SK': 'Stockport',
            'WA': 'Warrington', 'WN': 'Wigan',
            # North East
            'DH': 'Durham', 'DL': 'Darlington', 'HU': 'Hull', 'NE': 'Newcastle',
            'SR': 'Sunderland', 'TS': 'Teesside', 'YO': 'York',
            # Yorkshire
            'BD': 'Bradford', 'DN': 'Doncaster', 'HD': 'Huddersfield', 'HX': 'Halifax',
            'LS': 'Leeds', 'S': 'Sheffield', 'WF': 'Wakefield',
            # South West
            'BA': 'Bath', 'BS': 'Bristol', 'DT': 'Dorset', 'EX': 'Exeter',
            'GL': 'Gloucester', 'PL': 'Plymouth', 'SN': 'Swindon', 'SP': 'Salisbury',
            'TA': 'Taunton', 'TQ': 'Torquay', 'TR': 'Cornwall',
            # East
            'CB': 'Cambridge', 'CM': 'Chelmsford', 'CO': 'Colchester', 'IP': 'Ipswich',
            'NR': 'Norwich', 'PE': 'Peterborough', 'SS': 'Southend',
            # Wales
            'CF': 'Cardiff', 'LD': 'Wales', 'LL': 'Wales', 'NP': 'Newport',
            'SA': 'Swansea', 'SY': 'Shrewsbury',
            # Scotland
            'AB': 'Aberdeen', 'DD': 'Dundee', 'DG': 'Dumfries', 'EH': 'Edinburgh',
            'FK': 'Falkirk', 'G': 'Glasgow', 'HS': 'Scotland', 'IV': 'Inverness',
            'KA': 'Kilmarnock', 'KW': 'Scotland', 'KY': 'Fife', 'ML': 'Motherwell',
            'PA': 'Paisley', 'PH': 'Perth', 'TD': 'Scotland', 'ZE': 'Scotland',
            # Northern Ireland
            'BT': 'Belfast',
        }

    def extract_region(self, postcode: str) -> str:
        """Extract region from UK postcode."""
        if pd.isna(postcode) or postcode == '':
            return ''

        # Extract postcode area (letters at start)
        import re
        match = re.match(r'^([A-Z]{1,2})', str(postcode).upper())
        if match:
            area = match.group(1)
            return self.postcode_regions.get(area, area)
        return ''

    def load_basic_company_data(self, csv_path: str) -> pd.DataFrame:
        """
        Load Companies House basic company data CSV.

        Expected columns:
        - CompanyName
        - CompanyNumber
        - CompanyCategory (company type)
        - CompanyStatus
        - SICCode.SicText_1 through SicText_4
        - IncorporationDate
        - RegAddress.PostCode

        Returns:
            DataFrame formatted for scoring
        """
        logger.info(f"Loading Companies House data from {csv_path}")

        # Read CSV with appropriate dtypes
        df = pd.read_csv(csv_path, low_memory=False)

        logger.info(f"  Loaded {len(df)} companies")

        # Standardize column names
        col_mapping = {
            'CompanyName': 'company_name',
            ' CompanyNumber': 'company_number',
            'CompanyNumber': 'company_number',
            'CompanyCategory': 'company_type',
            'CompanyStatus': 'company_status',
            'IncorporationDate': 'incorporation_date',
            'RegAddress.PostCode': 'postcode',
            'Accounts.AccountCategory': 'accounts_type'
        }
        df = df.rename(columns={k: v for k, v in col_mapping.items() if k in df.columns})

        # Combine SIC codes
        sic_cols = [c for c in df.columns if 'SICCode' in c or 'sic' in c.lower()]
        if sic_cols:
            df['sic_codes'] = df[sic_cols].apply(
                lambda row: ','.join(str(v) for v in row if pd.notna(v) and str(v).strip()),
                axis=1
            )
            # Extract primary SIC code
            df['primary_sic'] = df['sic_codes'].str.split(',').str[0]
            df['industry_sector'] = df['primary_sic'].apply(sic_to_sector)

        # Calculate company age
        if 'incorporation_date' in df.columns:
            df['incorporation_date'] = pd.to_datetime(df['incorporation_date'], errors='coerce')
            df['company_age_years'] = (datetime.now() - df['incorporation_date']).dt.days / 365.25

        # Extract region from postcode
        if 'postcode' in df.columns:
            df['region'] = df['postcode'].apply(self.extract_region)

        # Filter to active companies
        if 'company_status' in df.columns:
            active_statuses = ['Active', 'active', 'ACTIVE']
            df = df[df['company_status'].isin(active_statuses)]
            logger.info(f"  {len(df)} active companies after filtering")

        return df

    def enrich_with_size_data(
        self,
        df: pd.DataFrame,
        officer_data_path: Optional[str] = None,
        accounts_data_path: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Enrich basic company data with size indicators.

        This would typically require additional API calls or bulk data files.
        For scoring, we can use proxy indicators from the basic data.
        """
        # Use accounts category as proxy for size
        if 'accounts_type' in df.columns:
            # Companies filing "small" or "micro" accounts are typically smaller
            size_map = {
                'DORMANT': 1,
                'MICRO-ENTITY': 2,
                'SMALL': 3,
                'MEDIUM': 4,
                'FULL': 5,
                'GROUP': 6
            }
            df['size_indicator'] = df['accounts_type'].map(size_map).fillna(3)

            # Estimate officer count based on size (rough proxy)
            officer_estimates = {1: 1, 2: 2, 3: 3, 4: 6, 5: 10, 6: 15}
            df['officer_count'] = df['size_indicator'].map(officer_estimates)

            # Estimate filing count based on age
            df['filing_count'] = (df['company_age_years'] * 3).clip(upper=100)

        return df


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="B2B Lead Scoring for PackagePro",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Build ICP from existing customers
    python prospect_scorer.py build-icp --output models/icp_profile.json

    # Score prospects from Companies House data
    python prospect_scorer.py score --icp models/icp_profile.json \\
        --prospects data/prospects/companies.csv --output scored_leads.csv

    # Full pipeline
    python prospect_scorer.py pipeline --prospects data/prospects.csv \\
        --top-n 500 --output hot_leads.csv
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Build ICP command
    build_parser = subparsers.add_parser('build-icp', help='Build ICP from existing customers')
    build_parser.add_argument('--output', '-o', default='models/prospect_scorer/icp_profile.json',
                             help='Output path for ICP profile')

    # Score command
    score_parser = subparsers.add_parser('score', help='Score a batch of prospects')
    score_parser.add_argument('--icp', required=True, help='Path to ICP profile JSON')
    score_parser.add_argument('--prospects', '-p', required=True, help='Path to prospects CSV')
    score_parser.add_argument('--output', '-o', required=True, help='Output path for scored leads')
    score_parser.add_argument('--top-n', type=int, help='Only output top N leads')

    # Full pipeline
    pipeline_parser = subparsers.add_parser('pipeline', help='Full scoring pipeline')
    pipeline_parser.add_argument('--prospects', '-p', required=True, help='Path to prospects CSV')
    pipeline_parser.add_argument('--output', '-o', required=True, help='Output path for scored leads')
    pipeline_parser.add_argument('--top-n', type=int, default=500, help='Number of top leads to output')
    pipeline_parser.add_argument('--rebuild-icp', action='store_true', help='Force rebuild ICP')

    args = parser.parse_args()

    if args.command == 'build-icp':
        # Build ICP
        analyzer = ICPAnalyzer()
        icp = analyzer.build_icp()

        # Save
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        icp.save(output_path)

        print(f"\nICP profile saved to: {output_path}")
        print(f"High-value customer criteria: {icp.high_value_threshold}")
        print(f"Total customers analyzed: {icp.total_customers}")
        print(f"High-value customers: {icp.high_value_count}")
        print(f"Model AUC: {icp.model_metrics['cv_auc_mean']:.3f}")

    elif args.command == 'score':
        # Load ICP and score
        scorer = ProspectScorer(icp_path=args.icp)

        # Load prospects
        loader = CompaniesHouseLoader()
        prospects_df = loader.load_basic_company_data(args.prospects)

        # Score
        scored_df = scorer.score_batch(prospects_df)

        # Filter to top N if requested
        if args.top_n:
            scored_df = scored_df.head(args.top_n)

        # Save
        scored_df.to_csv(args.output, index=False)
        print(f"\nScored {len(scored_df)} prospects -> {args.output}")

    elif args.command == 'pipeline':
        # Full pipeline
        icp_path = MODELS_DIR / "prospect_scorer" / "icp_profile.json"

        # Build or load ICP
        if args.rebuild_icp or not icp_path.exists():
            print("Building ICP profile...")
            analyzer = ICPAnalyzer()
            icp = analyzer.build_icp()
            icp.save(icp_path)
        else:
            print(f"Loading existing ICP from {icp_path}")
            icp = ICPProfile.load(icp_path)

        # Initialize scorer
        scorer = ProspectScorer(icp=icp)

        # Load and score prospects
        loader = CompaniesHouseLoader()
        prospects_df = loader.load_basic_company_data(args.prospects)
        scored_df = scorer.score_batch(prospects_df)

        # Get top N
        top_leads = scored_df.head(args.top_n)

        # Save
        top_leads.to_csv(args.output, index=False)

        print(f"\n{'='*60}")
        print("LEAD SCORING COMPLETE")
        print(f"{'='*60}")
        print(f"Total prospects scored: {len(scored_df)}")
        print(f"Top {args.top_n} leads saved to: {args.output}")
        print(f"\nScore distribution:")
        print(f"  Hot (75+):  {(scored_df['prospect_score'] >= 75).sum()}")
        print(f"  Warm (60-74): {((scored_df['prospect_score'] >= 60) & (scored_df['prospect_score'] < 75)).sum()}")
        print(f"  Cool (45-59): {((scored_df['prospect_score'] >= 45) & (scored_df['prospect_score'] < 60)).sum()}")
        print(f"  Cold (<45): {(scored_df['prospect_score'] < 45).sum()}")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
