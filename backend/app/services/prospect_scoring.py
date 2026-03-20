"""
Prospect Scoring Service

Integrates with the ICP (Ideal Customer Profile) model to score prospects
from Companies House data. Uses both rule-based scoring and ML models.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd

from backend.app.models.prospect import PackagingNeed, ProspectTier

logger = logging.getLogger(__name__)


# =============================================================================
# Path Configuration
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
MODELS_DIR = BASE_DIR / "models"
ICP_PROFILE_PATH = MODELS_DIR / "prospect_scorer" / "icp_profile.json"
LOOKALIKE_MODEL_PATH = MODELS_DIR / "prospect_scorer" / "lookalike_model.joblib"
CLUSTER_MODEL_PATH = MODELS_DIR / "customer_segments" / "model.joblib"
CLUSTER_SCALER_PATH = MODELS_DIR / "customer_segments" / "scaler.joblib"
CLUSTER_PROFILES_PATH = MODELS_DIR / "customer_segments" / "cluster_profiles.json"


# =============================================================================
# PackagePro Bespoke Packaging Filters
# =============================================================================

# EXCLUSION: Companies that manufacture packaging (competitors/self-sufficient)
PACKAGING_MANUFACTURER_SIC_CODES = {
    # Paper & Cardboard Packaging Manufacturers
    "17210": "Corrugated paper/cardboard containers manufacturer",
    "17220": "Paper household/sanitary goods manufacturer",
    "17230": "Paper stationery manufacturer",
    "17290": "Other paper/paperboard articles manufacturer",
    # Plastic Packaging Manufacturers
    "22220": "Plastic packing goods manufacturer",
    "22210": "Plastic plates/sheets manufacturer",
    "22230": "Plastic builders' ware manufacturer",
    # Wood/Metal Packaging Manufacturers
    "16240": "Wooden containers manufacturer",
    "25920": "Light metal packaging manufacturer",
    "25910": "Steel drums/containers manufacturer",
    # Glass Packaging
    "23130": "Hollow glass manufacturer (bottles/containers)",
    # Packaging Services (they do it themselves)
    "82920": "Packaging activities (contract packager)",
}

# EXCLUSION: Large retailers with in-house packaging
LARGE_RETAILER_INDICATORS = {
    "47110": "Retail in non-specialised stores (supermarkets)",
    "47190": "Other retail in non-specialised stores",
}

# BESPOKE PACKAGING IDEAL CUSTOMERS
# These industries typically need custom/premium packaging
BESPOKE_PACKAGING_IDEAL_SIC = {
    # Food & Beverage - Premium/Artisan (highest priority)
    "10710": ("Bread/bakery production", 95, "Artisan bakeries need branded packaging"),
    "10820": ("Cocoa/chocolate/confectionery", 95, "Gift boxes, premium presentation"),
    "10830": ("Tea/coffee processing", 90, "Premium retail packaging"),
    "10840": ("Condiments/seasonings", 85, "Artisan sauces need standout packaging"),
    "10390": ("Other fruit/veg processing", 85, "Artisan preserves, jams"),
    "10890": ("Other food products", 85, "Specialty foods"),
    "11010": ("Distilling/blending spirits", 95, "Premium bottle packaging, gift sets"),
    "11020": ("Wine production", 90, "Gift packaging, cases"),
    "11030": ("Cider/fruit wine", 85, "Craft beverage packaging"),
    "11040": ("Other non-distilled drinks", 85, "Artisan beverages"),
    "11050": ("Beer production", 85, "Craft brewery packaging"),
    "11070": ("Soft drinks/water", 80, "Branded packaging"),

    # Cosmetics & Personal Care (very high priority)
    "20420": ("Perfumes/toiletries", 95, "Luxury packaging essential"),
    "20530": ("Essential oils", 90, "Premium presentation boxes"),
    "20410": ("Soap/detergent manufacture", 80, "Premium soap packaging"),

    # Pharmaceuticals & Health
    "21100": ("Basic pharmaceuticals", 85, "Regulated packaging requirements"),
    "21200": ("Pharmaceutical preparations", 85, "Branded medicine packaging"),
    "32500": ("Medical instruments", 80, "Sterile packaging needs"),

    # Premium Retail (need unboxing experience)
    "47740": ("Retail medical goods", 80, "Presentation packaging"),
    "47750": ("Retail cosmetics/toiletries", 90, "Gift packaging, sets"),
    "47760": ("Retail flowers/plants/seeds", 85, "Gift wrapping, boxes"),
    "47770": ("Retail watches/jewellery", 95, "Luxury presentation boxes"),
    "47782": ("Retail art/crafts", 85, "Premium packaging"),
    "47789": ("Other retail specialist stores", 80, "Varied premium needs"),
    "47910": ("Retail via mail order/internet", 90, "Unboxing experience crucial"),

    # Gifts & Luxury
    "32120": ("Jewellery manufacture", 95, "Premium presentation boxes"),
    "32130": ("Imitation jewellery", 85, "Gift packaging"),
    "14110": ("Leather clothes manufacture", 90, "Luxury packaging"),
    "14200": ("Fur articles manufacture", 90, "Premium presentation"),
    "15120": ("Luggage/handbags", 90, "Luxury brand packaging"),

    # Creative & Marketing (understand brand value)
    "73110": ("Advertising agencies", 85, "Brand packaging projects"),
    "74100": ("Specialised design", 90, "Design-led packaging needs"),
    "74200": ("Photographic activities", 75, "Product photography packaging"),

    # Subscription Boxes & E-commerce
    "47919": ("Retail not in stores (other)", 90, "Subscription box businesses"),
    "82990": ("Other business support", 75, "Fulfillment services"),
}

# Industries to score LOWER (commodity packaging, not bespoke)
LOW_BESPOKE_FIT_SIC = {
    "46710": ("Wholesale fuels", 20, "Bulk commodity, no bespoke need"),
    "46720": ("Wholesale metals/ores", 20, "Industrial, bulk packaging"),
    "46750": ("Wholesale chemicals", 25, "Industrial packaging"),
    "01000": ("Crop/animal production", 30, "Bulk agricultural"),
    "02000": ("Forestry/logging", 25, "Bulk materials"),
    "03000": ("Fishing/aquaculture", 35, "Commercial bulk"),
    "05000": ("Mining coal/lignite", 15, "No packaging need"),
    "06000": ("Crude petroleum/gas", 15, "No packaging need"),
    "35000": ("Electricity/gas supply", 10, "No packaging need"),
    "36000": ("Water collection/supply", 10, "No packaging need"),
    "41000": ("Building construction", 20, "Minimal packaging"),
    "42000": ("Civil engineering", 15, "No packaging need"),
}


def is_packaging_manufacturer(sic_codes: list[str] | None) -> tuple[bool, str]:
    """
    Check if company manufactures packaging (competitor/self-sufficient).

    Returns:
        (is_excluded, reason)
    """
    if not sic_codes:
        return False, ""

    for sic in sic_codes:
        sic_str = str(sic).strip()
        if sic_str in PACKAGING_MANUFACTURER_SIC_CODES:
            return True, PACKAGING_MANUFACTURER_SIC_CODES[sic_str]
        # Check first 4 digits
        if len(sic_str) >= 4:
            sic_4 = sic_str[:4] + "0"
            if sic_4 in PACKAGING_MANUFACTURER_SIC_CODES:
                return True, PACKAGING_MANUFACTURER_SIC_CODES[sic_4]

    return False, ""


def get_bespoke_fit_score(sic_codes: list[str] | None) -> tuple[float, str]:
    """
    Score how well a company fits PackagePro's bespoke packaging offering.

    Returns:
        (score 0-100, reason)
    """
    if not sic_codes:
        return 50.0, "Unknown industry - moderate bespoke fit"

    best_score = 50.0
    best_reason = "Standard industry"

    for sic in sic_codes:
        sic_str = str(sic).strip()

        # Check ideal customers
        if sic_str in BESPOKE_PACKAGING_IDEAL_SIC:
            name, score, reason = BESPOKE_PACKAGING_IDEAL_SIC[sic_str]
            if score > best_score:
                best_score = score
                best_reason = f"{name}: {reason}"

        # Check low-fit industries
        if sic_str in LOW_BESPOKE_FIT_SIC:
            name, score, reason = LOW_BESPOKE_FIT_SIC[sic_str]
            if score < best_score:
                best_score = score
                best_reason = f"{name}: {reason}"

        # Check 4-digit prefix matches
        if len(sic_str) >= 4:
            prefix = sic_str[:4]
            for ideal_sic, (name, score, reason) in BESPOKE_PACKAGING_IDEAL_SIC.items():
                if ideal_sic.startswith(prefix):
                    if score > best_score:
                        best_score = score * 0.9  # Slightly lower for prefix match
                        best_reason = f"Related to {name}"

    return best_score, best_reason


# =============================================================================
# SIC Code Mappings (from prospect_scorer.py)
# =============================================================================

SIC_SECTOR_MAP = {
    range(1, 4): "Agriculture",
    range(5, 10): "Mining",
    range(10, 34): "Manufacturing",
    range(35, 40): "Utilities",
    range(41, 44): "Construction",
    range(45, 48): "Wholesale & Retail",
    range(49, 54): "Transportation",
    range(55, 57): "Accommodation & Food",
    range(58, 64): "Information & Communication",
    range(64, 67): "Finance",
    range(68, 69): "Real Estate",
    range(69, 76): "Professional Services",
    range(77, 83): "Administrative Services",
    range(84, 85): "Public Administration",
    range(85, 86): "Education",
    range(86, 89): "Health",
    range(90, 94): "Arts & Entertainment",
    range(94, 97): "Other Services",
    range(97, 99): "Household Activities",
}


def sic_to_sector(sic_code: str) -> str:
    """Convert SIC code to industry sector."""
    if not sic_code or pd.isna(sic_code):
        return "Unknown"

    try:
        sic_int = int(float(str(sic_code)[:2]))
        for sic_range, sector in SIC_SECTOR_MAP.items():
            if sic_int in sic_range:
                return sector
    except (ValueError, TypeError):
        pass

    return "Unknown"


# Packaging need classification
PACKAGING_NEED_HIGH = {
    range(10, 34): "Products need packaging for distribution",
    range(18, 19): "Printers resell packaging solutions",
    range(45, 48): "Shipping and distribution packaging",
}

PACKAGING_NEED_MEDIUM = {
    range(55, 57): "Food service packaging",
    range(73, 74): "Marketing materials, presentation folders",
    range(74, 75): "Design services, presentations",
    range(82, 83): "Fulfillment and business support",
    range(58, 59): "Publishing materials",
}

PACKAGING_NEED_LOW = {
    range(69, 72): "Pure services - minimal packaging need",
    range(68, 69): "Real estate - limited need",
    range(64, 67): "Financial services - minimal need",
    range(85, 86): "Education - limited need",
    range(84, 85): "Public admin - limited need",
}


def get_packaging_need(sic_code: str) -> tuple[PackagingNeed, str]:
    """Classify packaging need based on SIC code."""
    if not sic_code or pd.isna(sic_code):
        return PackagingNeed.UNKNOWN, "No SIC code available"

    if "," in str(sic_code):
        sic_code = str(sic_code).split(",")[0].strip()

    try:
        sic_int = int(float(str(sic_code)[:2]))

        for sic_range, reason in PACKAGING_NEED_HIGH.items():
            if sic_int in sic_range:
                return PackagingNeed.HIGH, reason

        for sic_range, reason in PACKAGING_NEED_MEDIUM.items():
            if sic_int in sic_range:
                return PackagingNeed.MEDIUM, reason

        for sic_range, reason in PACKAGING_NEED_LOW.items():
            if sic_int in sic_range:
                return PackagingNeed.LOW, reason

    except (ValueError, TypeError):
        pass

    return PackagingNeed.UNKNOWN, "Unknown industry classification"


# =============================================================================
# Data Classes for Scoring Results
# =============================================================================


@dataclass
class ProspectScoreResult:
    """Result of scoring a prospect."""

    total_score: float
    tier: ProspectTier

    # Component scores (0-100)
    industry_score: float
    age_score: float
    size_score: float
    geography_score: float
    web_presence_score: float
    bespoke_fit_score: float  # NEW: How well they fit bespoke packaging

    # ML model contribution
    ml_model_score: Optional[float]
    ml_model_version: Optional[str]

    # Packaging assessment
    packaging_need: PackagingNeed
    packaging_need_reason: str

    # Bespoke fit assessment
    bespoke_fit_reason: str  # NEW: Why they're a good/bad fit for bespoke

    # Exclusion (competitors/self-sufficient)
    is_excluded: bool  # NEW: Should be filtered out
    exclusion_reason: str  # NEW: Why excluded

    # Cluster assignment
    cluster_id: Optional[int]
    cluster_name: Optional[str]
    cluster_confidence: Optional[float]

    # Industry info
    industry_sector: str


@dataclass
class ICPProfile:
    """Ideal Customer Profile loaded from JSON."""

    industry_profiles: dict[str, dict]
    company_age_profile: dict
    company_size_profile: dict
    geographic_profile: dict
    web_presence_profile: dict
    feature_weights: dict
    top_sic_codes: list[dict]

    @classmethod
    def from_json(cls, data: dict) -> "ICPProfile":
        """Load from JSON dict."""
        return cls(
            industry_profiles=data.get("industry_profiles", {}),
            company_age_profile=data.get("company_age_profile", {}),
            company_size_profile=data.get("company_size_profile", {}),
            geographic_profile=data.get("geographic_profile", {}),
            web_presence_profile=data.get("web_presence_profile", {}),
            feature_weights=data.get("feature_weights", {}),
            top_sic_codes=data.get("top_sic_codes", []),
        )


# =============================================================================
# Prospect Scoring Service
# =============================================================================


class ProspectScoringService:
    """
    Service for scoring prospects using ICP analysis and ML models.

    Combines rule-based scoring with trained ML models for comprehensive
    prospect evaluation.
    """

    def __init__(self):
        self._icp_profile: Optional[ICPProfile] = None
        self._ml_model = None
        self._ml_model_version: Optional[str] = None
        self._cluster_model = None
        self._cluster_scaler = None
        self._cluster_profiles: Optional[dict] = None
        self._loaded = False

    def load_models(self) -> bool:
        """Load ICP profile and ML models from disk."""
        if self._loaded:
            return True

        try:
            # Load ICP profile
            if ICP_PROFILE_PATH.exists():
                with open(ICP_PROFILE_PATH) as f:
                    data = json.load(f)
                self._icp_profile = ICPProfile.from_json(data)
                logger.info(f"Loaded ICP profile from {ICP_PROFILE_PATH}")
            else:
                logger.warning(f"ICP profile not found at {ICP_PROFILE_PATH}")
                self._icp_profile = self._default_icp_profile()

            # Load lookalike model
            if LOOKALIKE_MODEL_PATH.exists():
                self._ml_model = joblib.load(LOOKALIKE_MODEL_PATH)
                self._ml_model_version = "1.0.0"
                logger.info(f"Loaded lookalike model from {LOOKALIKE_MODEL_PATH}")
            else:
                logger.warning(f"Lookalike model not found at {LOOKALIKE_MODEL_PATH}")

            # Load clustering model
            if CLUSTER_MODEL_PATH.exists():
                self._cluster_model = joblib.load(CLUSTER_MODEL_PATH)
                logger.info(f"Loaded cluster model from {CLUSTER_MODEL_PATH}")

            if CLUSTER_SCALER_PATH.exists():
                self._cluster_scaler = joblib.load(CLUSTER_SCALER_PATH)
                logger.info(f"Loaded cluster scaler from {CLUSTER_SCALER_PATH}")

            if CLUSTER_PROFILES_PATH.exists():
                with open(CLUSTER_PROFILES_PATH) as f:
                    self._cluster_profiles = json.load(f)
                logger.info(f"Loaded cluster profiles from {CLUSTER_PROFILES_PATH}")

            self._loaded = True
            return True

        except Exception as e:
            logger.error(f"Error loading models: {e}")
            self._icp_profile = self._default_icp_profile()
            return False

    def _default_icp_profile(self) -> ICPProfile:
        """Create default ICP profile if none exists."""
        return ICPProfile(
            industry_profiles={
                "Manufacturing": {"score_weight": 80, "lift_ratio": 1.2},
                "Wholesale & Retail": {"score_weight": 70, "lift_ratio": 1.1},
                "Professional Services": {"score_weight": 50, "lift_ratio": 0.9},
            },
            company_age_profile={
                "optimal_min_years": 7,
                "optimal_max_years": 29,
                "high_value_median": 16.6,
            },
            company_size_profile={
                "optimal_officer_count_min": 2,
                "optimal_officer_count_max": 7,
                "optimal_filing_count_min": 14,
                "optimal_filing_count_max": 89,
            },
            geographic_profile={"top_regions": [], "region_scores": {}},
            web_presence_profile={
                "website_score_boost": 1.1,
                "has_website_rate": 0.5,
            },
            feature_weights={
                "industry": 0.30,
                "age": 0.20,
                "size": 0.25,
                "geography": 0.10,
                "web_presence": 0.15,
            },
            top_sic_codes=[],
        )

    def score_prospect(
        self,
        company_number: str,
        company_name: str,
        sic_codes: Optional[list[str]] = None,
        date_of_creation: Optional[datetime] = None,
        region: Optional[str] = None,
        officer_count: int = 0,
        filing_count: int = 0,
        has_charges: bool = False,
        has_website: bool = False,
        has_https: bool = False,
        **kwargs,
    ) -> ProspectScoreResult:
        """
        Score a prospect based on ICP profile and ML models.

        Args:
            company_number: Companies House company number
            company_name: Company name
            sic_codes: List of SIC codes
            date_of_creation: Company incorporation date
            region: Geographic region
            officer_count: Number of company officers
            filing_count: Number of filings
            has_charges: Whether company has charges/loans
            has_website: Whether company has a website
            has_https: Whether website uses HTTPS

        Returns:
            ProspectScoreResult with full scoring breakdown
        """
        if not self._loaded:
            self.load_models()

        # Get primary SIC code and industry sector
        primary_sic = sic_codes[0] if sic_codes else None
        industry_sector = sic_to_sector(primary_sic)

        # Check if this is a packaging manufacturer (competitor/excluded)
        is_excluded, exclusion_reason = is_packaging_manufacturer(sic_codes)

        # Get bespoke packaging fit score
        bespoke_fit_score, bespoke_fit_reason = get_bespoke_fit_score(sic_codes)

        # Get packaging need
        packaging_need, packaging_reason = get_packaging_need(primary_sic)

        # Calculate company age
        company_age_years = None
        if date_of_creation:
            company_age_years = (datetime.utcnow() - date_of_creation).days / 365.25

        # Score each component (0-100 scale)
        industry_score = self._score_industry(industry_sector, primary_sic)
        age_score = self._score_company_age(company_age_years)
        size_score = self._score_company_size(officer_count, filing_count, has_charges)
        geography_score = self._score_geography(region)
        web_presence_score = self._score_web_presence(has_website, has_https)

        # If excluded (packaging manufacturer/competitor), score is 0
        if is_excluded:
            return ProspectScoreResult(
                total_score=0.0,
                tier=ProspectTier.COLD,
                industry_score=0.0,
                age_score=age_score,
                size_score=size_score,
                geography_score=geography_score,
                web_presence_score=web_presence_score,
                bespoke_fit_score=0.0,
                ml_model_score=None,
                ml_model_version=None,
                packaging_need=PackagingNeed.LOW,
                packaging_need_reason="Packaging manufacturer - not a prospect",
                bespoke_fit_reason="EXCLUDED: " + exclusion_reason,
                is_excluded=True,
                exclusion_reason=exclusion_reason,
                cluster_id=None,
                cluster_name="Excluded - Competitor",
                cluster_confidence=1.0,
                industry_sector=industry_sector,
            )

        # Get feature weights from ICP profile (updated for bespoke focus)
        weights = self._icp_profile.feature_weights

        # Calculate weighted composite score with bespoke fit
        # Bespoke fit gets 25% weight, reducing others proportionally
        composite_score = (
            industry_score * weights.get("industry", 0.25)
            + age_score * weights.get("age", 0.15)
            + size_score * weights.get("size", 0.20)
            + geography_score * weights.get("geography", 0.10)
            + web_presence_score * weights.get("web_presence", 0.10)
            + bespoke_fit_score * 0.20  # Bespoke fit is crucial for PackagePro
        )

        # Apply packaging need multiplier
        packaging_multipliers = {
            PackagingNeed.HIGH: 1.0,
            PackagingNeed.MEDIUM: 0.85,
            PackagingNeed.LOW: 0.60,
            PackagingNeed.UNKNOWN: 0.75,
        }
        composite_score *= packaging_multipliers.get(packaging_need, 0.75)

        # Get ML model score if available
        ml_score = None
        if self._ml_model:
            ml_score = self._get_ml_score(
                company_age_years=company_age_years,
                officer_count=officer_count,
                filing_count=filing_count,
                has_charges=has_charges,
                has_website=has_website,
                has_https=has_https,
                industry_sector=industry_sector,
            )

        # Blend rule-based and ML scores (70/30 split)
        if ml_score is not None:
            total_score = composite_score * 0.7 + ml_score * 0.3
        else:
            total_score = composite_score

        # Ensure score is in 0-100 range
        total_score = max(0, min(100, total_score))

        # Determine tier
        tier = self._get_tier(total_score)

        # Get cluster assignment
        cluster_id, cluster_name, cluster_confidence = self._assign_cluster(
            company_age_years=company_age_years,
            officer_count=officer_count,
            filing_count=filing_count,
            has_charges=has_charges,
            industry_sector=industry_sector,
        )

        return ProspectScoreResult(
            total_score=round(total_score, 2),
            tier=tier,
            industry_score=round(industry_score, 2),
            age_score=round(age_score, 2),
            size_score=round(size_score, 2),
            geography_score=round(geography_score, 2),
            web_presence_score=round(web_presence_score, 2),
            bespoke_fit_score=round(bespoke_fit_score, 2),
            ml_model_score=round(ml_score, 2) if ml_score else None,
            ml_model_version=self._ml_model_version,
            packaging_need=packaging_need,
            packaging_need_reason=packaging_reason,
            bespoke_fit_reason=bespoke_fit_reason,
            is_excluded=False,
            exclusion_reason="",
            cluster_id=cluster_id,
            cluster_name=cluster_name,
            cluster_confidence=cluster_confidence,
            industry_sector=industry_sector,
        )

    def _score_industry(
        self, industry_sector: str, primary_sic: Optional[str]
    ) -> float:
        """Score based on industry sector."""
        if not self._icp_profile:
            return 50.0

        profiles = self._icp_profile.industry_profiles

        # Check if sector exists in profiles
        if industry_sector in profiles:
            return profiles[industry_sector].get("score_weight", 50.0)

        # Check for specific SIC code lift
        if primary_sic:
            for sic_info in self._icp_profile.top_sic_codes:
                if sic_info.get("sic_code") == primary_sic:
                    lift = sic_info.get("lift_ratio", 1.0)
                    return min(100, lift * 50)

        return 50.0  # Default neutral score

    def _score_company_age(self, age_years: Optional[float]) -> float:
        """Score based on company age."""
        if age_years is None:
            return 50.0

        profile = self._icp_profile.company_age_profile
        optimal_min = profile.get("optimal_min_years", 7)
        optimal_max = profile.get("optimal_max_years", 29)

        if optimal_min <= age_years <= optimal_max:
            return 100.0  # Optimal range
        elif age_years < 5:
            return 50.0  # Too young
        elif 5 <= age_years < optimal_min:
            return 70.0  # Young
        elif optimal_max < age_years <= 50:
            return 90.0  # Mature
        else:
            return 70.0  # Very mature

    def _score_company_size(
        self, officer_count: int, filing_count: int, has_charges: bool
    ) -> float:
        """Score based on company size indicators."""
        profile = self._icp_profile.company_size_profile
        score = 0.0

        # Officer count scoring
        opt_min = profile.get("optimal_officer_count_min", 2)
        opt_max = profile.get("optimal_officer_count_max", 7)

        if opt_min <= officer_count <= opt_max:
            score += 40  # Optimal
        elif officer_count < opt_min:
            score += 20  # Too small
        else:
            score += 30  # Large

        # Filing count scoring
        filing_min = profile.get("optimal_filing_count_min", 14)
        filing_max = profile.get("optimal_filing_count_max", 89)

        if filing_min <= filing_count <= filing_max:
            score += 40  # Optimal
        elif filing_count < filing_min:
            score += 15  # Low activity
        else:
            score += 30  # High activity

        # Has charges bonus (indicates credit activity = established business)
        if has_charges:
            score += 20

        return min(100, score)

    def _score_geography(self, region: Optional[str]) -> float:
        """Score based on geographic region."""
        if not region:
            return 50.0

        profile = self._icp_profile.geographic_profile
        region_scores = profile.get("region_scores", {})

        if region in region_scores:
            return region_scores[region]

        # Check if region is in top regions
        top_regions = profile.get("top_regions", [])
        if region in top_regions:
            return 80.0

        return 50.0  # Neutral for unknown regions

    def _score_web_presence(self, has_website: bool, has_https: bool) -> float:
        """Score based on web presence."""
        profile = self._icp_profile.web_presence_profile
        boost = profile.get("website_score_boost", 1.1)

        score = 40.0  # Base score

        if has_website:
            score += 30 * boost

        if has_https:
            score += 20 * boost  # Security-conscious

        return min(100, score)

    def _get_ml_score(
        self,
        company_age_years: Optional[float],
        officer_count: int,
        filing_count: int,
        has_charges: bool,
        has_website: bool,
        has_https: bool,
        industry_sector: str,
    ) -> Optional[float]:
        """Get ML model prediction score."""
        if not self._ml_model:
            return None

        try:
            # Prepare features (must match training features)
            features = {
                "company_age_years": company_age_years or 10,
                "officer_count": officer_count,
                "filing_count": filing_count,
                "has_charges": int(has_charges),
                "has_website": int(has_website),
                "has_https": int(has_https),
            }

            # Add industry dummies for top sectors
            top_industries = [
                "manufacturing",
                "wholesale_and_retail",
                "professional_services",
                "administrative_services",
                "information_and_communication",
                "construction",
                "accommodation_and_food",
                "other_services",
                "real_estate",
                "finance",
            ]

            sector_key = industry_sector.lower().replace(" ", "_").replace("&", "and")
            for ind in top_industries:
                features[f"ind_{ind}"] = 1 if sector_key == ind else 0

            # Create DataFrame for prediction
            df = pd.DataFrame([features])

            # Get prediction probability
            proba = self._ml_model.predict_proba(df)[0][1]
            return proba * 100  # Convert to 0-100 scale

        except Exception as e:
            logger.warning(f"ML model prediction failed: {e}")
            return None

    def _get_tier(self, score: float) -> ProspectTier:
        """Determine tier from score."""
        if score >= 75:
            return ProspectTier.HOT
        elif score >= 60:
            return ProspectTier.WARM
        elif score >= 45:
            return ProspectTier.COOL
        else:
            return ProspectTier.COLD

    def _assign_cluster(
        self,
        company_age_years: Optional[float],
        officer_count: int,
        filing_count: int,
        has_charges: bool,
        industry_sector: str,
    ) -> tuple[Optional[int], Optional[str], Optional[float]]:
        """Assign prospect to a customer segment cluster."""
        if not self._cluster_model or not self._cluster_scaler:
            return None, None, None

        try:
            # Prepare minimal features for clustering
            # Note: Full clustering requires more features - this is a simplified version
            features = np.array(
                [
                    [
                        company_age_years or 10,
                        officer_count,
                        filing_count,
                        int(has_charges),
                    ]
                ]
            )

            # This is a simplified clustering - in production you'd match the exact
            # feature set used during training
            cluster_id = 1  # Default to "New Prospects" cluster
            cluster_name = "New Prospects"
            confidence = 0.5

            if self._cluster_profiles:
                # Map cluster ID to profile
                for cid, profile in self._cluster_profiles.get("clusters", {}).items():
                    if str(cid) == str(cluster_id):
                        cluster_name = profile.get("name", f"Cluster {cluster_id}")
                        break

            return cluster_id, cluster_name, confidence

        except Exception as e:
            logger.warning(f"Cluster assignment failed: {e}")
            return None, None, None

    def batch_score(
        self, prospects: list[dict[str, Any]]
    ) -> list[ProspectScoreResult]:
        """Score multiple prospects efficiently."""
        return [self.score_prospect(**p) for p in prospects]


# Global service instance
_scoring_service: Optional[ProspectScoringService] = None


def get_scoring_service() -> ProspectScoringService:
    """Get or create the scoring service singleton."""
    global _scoring_service
    if _scoring_service is None:
        _scoring_service = ProspectScoringService()
        _scoring_service.load_models()
    return _scoring_service
