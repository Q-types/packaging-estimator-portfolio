"""Company enrichment pipeline for ML customer segmentation.

Reads legacy_extract.json, cleans company names, engineers features from
order history, enriches via Companies House API, and outputs an ML-ready
dataset for clustering.

Usage:
    python scripts/enrich_companies.py                    # Full pipeline
    python scripts/enrich_companies.py --skip-api         # Skip Companies House
    python scripts/enrich_companies.py --stage clean      # Only run cleaning
    python scripts/enrich_companies.py --stage features   # Only run feature eng
    python scripts/enrich_companies.py --stage enrich     # Only run API enrichment
    python scripts/enrich_companies.py --stage enrich-deep # Officers, filings, charges
    python scripts/enrich_companies.py --stage web        # Web presence checks
    python scripts/enrich_companies.py --stage merge      # Only merge & output
"""

import argparse
import http.client
import json
import logging
import re
import socket
import ssl
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# ── Paths ────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LEGACY_JSON = DATA_DIR / "estimates" / "legacy_extract_refined.json"
COMPANIES_DIR = DATA_DIR / "companies"
CONFIG_DIR = BASE_DIR / "config"
API_KEY_FILE = CONFIG_DIR / "companies_key.tst"
CLEAN_MAP_PATH = COMPANIES_DIR / "name_mapping.json"
INTERNAL_FEATURES_PATH = COMPANIES_DIR / "internal_features.csv"
EXTERNAL_FEATURES_PATH = COMPANIES_DIR / "external_features.csv"
DEEP_FEATURES_PATH = COMPANIES_DIR / "deep_features.csv"
WEB_FEATURES_PATH = COMPANIES_DIR / "web_features.csv"
FINAL_DATASET_PATH = COMPANIES_DIR / "company_features.csv"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 1: Company Name Cleaning & Deduplication
# ═══════════════════════════════════════════════════════════════════════════════

# Known non-company patterns (job descriptions, products, etc.)
NON_COMPANY_PATTERNS = [
    # Dimension/quantity patterns
    r"^\d+\s*(MM|MICRON)\b",           # "750 MICRON WHITE PP DOOR HANGERS"
    r"^\d+\s+(OR|X)\s+\d+",            # "50 OR 100 DIEBOND PANELS"
    r"\d+\s*X\s*\d+\s*(MM|CM)?",       # Dimensions like "140x30"
    r"\d+\s*(COL|COLOUR|COLOR)\b",     # "1 COL BLACK LOGO"
    r"\d+\s*(COPIES|VERSIONS|PCS)\b",  # Quantity terms

    # Template/test records
    r"^(POB|A[3-5]|B5)\s+BINDER",     # "POB BINDER SPREADSHEET"
    r"^(SAMPLE|TEST|DUMMY|TEMPLATE)",  # Test records
    r"^(BUDGET|COSTING|QUOTE)\s",      # Budget/costing entries
    r"^\d{4,}\s*[-–]\s*\d",            # Numeric estimate refs
    r"^(VARIOUS|MISC|SUNDRY|GENERAL|UNKNOWN|NONE|N/?A|TBC|TBA)$",
    r"\bSPREADSHEET\b",                # Spreadsheet references

    # Product-specific terms unlikely in company names
    r"\bRIGID\s+BOX\s+TRAY",           # Product type
    r"\bWRAP\s*AROUND\s+COVER",        # Product type
    r"\bDISPLAY\s+CARD\b",             # Product type
    r"\bTAPE\s+MEASURE",               # Product type
    r"\bLECT[EU]RN\s+HEADER",          # Product type
    r"\bDOOR\s+HANGER",                # Product type
    r"\bWINDOW\s+STICKER",             # Product type
    r"\bDIEBOND\s+PANEL",              # Product type
    r"\bTRAY(S)?\s+ONLY\b",            # Part-only orders

    # Material specs in name
    r"\bFOAM\s+PVC\b",                 # Material spec
    r"\b\d+\s*MIC(RON)?\b",            # Micron measurement
]

# Known company name aliases → canonical form
KNOWN_ALIASES = {
    "4 PRINT": "4PRINT",
    "4-PRINT": "4PRINT",
    "ALL PAY CARDS": "ALLPAY",
    "ALLPAY CARDS": "ALLPAY",
    "ALLPAY LIMITED": "ALLPAY",
    "B&M": "B&M RETAIL",
    "B & M": "B&M RETAIL",
    "EASYJET": "EASYJET PLC",
    "EASY JET": "EASYJET PLC",
    "BT": "BT GROUP",
    "BRITISH TELECOM": "BT GROUP",
    "ROYAL MAIL": "ROYAL MAIL GROUP",
    "COOP": "CO-OP",
    "CO OP": "CO-OP",
    "THE CO-OPERATIVE": "CO-OP",
    "COCA COLA": "COCA-COLA",
    "COCA-COLA ENTERPRISES": "COCA-COLA",
    "MARKS AND SPENCER": "MARKS & SPENCER",
    "M&S": "MARKS & SPENCER",
    "MARKS AND SPENCERS": "MARKS & SPENCER",
}

# Common UK company suffixes to normalise
SUFFIX_PATTERNS = [
    (r"\s+(LIMITED|LTD|PLC|LLP|INC|CORP|GROUP|HOLDINGS?)\.?\s*$", ""),
    (r"\s+UK\s*$", ""),
    (r"\s+\(UK\)\s*$", ""),
    (r"\s+\(EUROPE\)\s*$", ""),
]


def _normalise_name(name: str) -> str:
    """Normalise a company name for deduplication matching."""
    if not name:
        return ""
    s = name.upper().strip()
    # Remove common punctuation
    s = re.sub(r"[.,;:!?'\"()]", "", s)
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _canonical_key(name: str) -> str:
    """Generate a canonical key for fuzzy matching."""
    s = _normalise_name(name)
    # Apply known aliases
    if s in KNOWN_ALIASES:
        s = KNOWN_ALIASES[s]
    # Strip common suffixes
    for pattern, repl in SUFFIX_PATTERNS:
        s = re.sub(pattern, repl, s).strip()
    # Remove "THE " prefix
    s = re.sub(r"^THE\s+", "", s)
    # Generate sort key: remove non-alphanumeric, lowercase
    return re.sub(r"[^A-Z0-9]", "", s)


def _is_non_company(name: str) -> bool:
    """Check if name is a product/job description rather than a company."""
    upper = name.upper().strip()
    for pattern in NON_COMPANY_PATTERNS:
        if re.search(pattern, upper):
            return True
    # Very short names that are likely abbreviations/codes
    if len(upper) <= 2:
        return True
    return False


def clean_company_names(records: list[dict]) -> dict:
    """Clean and deduplicate company names.

    Returns a mapping: {original_name: canonical_name} and a set of
    names flagged as non-companies.
    """
    # Collect all unique company names with their frequencies
    name_counts = Counter()
    for r in records:
        name = r.get("company_name")
        if name and name.strip():
            name_counts[name.strip()] += 1

    log.info(f"Raw unique company names: {len(name_counts)}")

    # Build canonical groups
    canonical_groups = defaultdict(list)  # key -> [(name, count)]
    non_companies = set()

    for name, count in name_counts.items():
        if _is_non_company(name):
            non_companies.add(name)
            continue
        key = _canonical_key(name)
        if not key:
            non_companies.add(name)
            continue
        canonical_groups[key].append((name, count))

    # Pick the best name for each group (most frequent, or longest if tied)
    name_mapping = {}
    for key, variants in canonical_groups.items():
        variants.sort(key=lambda x: (-x[1], -len(x[0])))
        canonical = variants[0][0]
        for name, _ in variants:
            name_mapping[name] = canonical

    # Also map non-companies to None
    for name in non_companies:
        name_mapping[name] = None

    n_groups = len(canonical_groups)
    n_merged = len(name_mapping) - len(non_companies) - n_groups
    log.info(f"Canonical companies: {n_groups}")
    log.info(f"Merged duplicates: {n_merged}")
    log.info(f"Flagged non-companies: {len(non_companies)}")

    # Report notable merges
    for key, variants in canonical_groups.items():
        if len(variants) > 1:
            names = [v[0] for v in variants]
            log.debug(f"  Merged: {names} → {names[0]}")

    return name_mapping


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 2: Internal Feature Engineering
# ═══════════════════════════════════════════════════════════════════════════════

# All known operations across templates
ALL_OPERATIONS = [
    "cutting", "creasing", "assembly", "wrapping", "liner_gluing",
    "laminating", "foil_blocking", "screen_printing", "drilling",
    "embossing", "debossing", "uv_varnishing", "die_cutting",
    "hand_finishing", "packing", "collating",
]

# Product types detected by the processor
ALL_PRODUCT_TYPES = [
    "binder", "box", "slip_case", "folder", "presentation_pack",
    "menu_cover", "ring_binder", "lever_arch", "portfolio",
]


def engineer_internal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build features from order history for each company.

    Features include:
    - Recency/Frequency/Monetary (RFM)
    - Order pattern metrics
    - Product type distribution
    - Operations complexity
    - Pricing behaviour
    - Growth trajectory
    """
    latest_date = df["date"].max()

    features_list = []

    for company, grp in df.groupby("company_clean"):
        if pd.isna(company) or company is None:
            continue

        f = {"company": company}

        # ── RFM ──────────────────────────────────────────────────────
        dated = grp[grp["date"].notna()]
        if len(dated) > 0:
            f["recency_days"] = (latest_date - dated["date"].max()).days
            f["first_order_days_ago"] = (latest_date - dated["date"].min()).days
            f["tenure_days"] = (dated["date"].max() - dated["date"].min()).days
        else:
            f["recency_days"] = np.nan
            f["first_order_days_ago"] = np.nan
            f["tenure_days"] = 0

        f["frequency"] = len(grp)
        f["monetary_total"] = grp["total_cost"].sum()
        f["monetary_mean"] = grp["total_cost"].mean()
        f["monetary_median"] = grp["total_cost"].median()
        f["monetary_std"] = grp["total_cost"].std() if len(grp) > 1 else 0
        f["monetary_max"] = grp["total_cost"].max()
        f["monetary_min"] = grp["total_cost"].min()

        # ── Order patterns ───────────────────────────────────────────
        if len(dated) >= 2:
            order_dates = dated["date"].sort_values()
            gaps = order_dates.diff().dt.days.dropna()
            f["avg_days_between_orders"] = gaps.mean()
            f["std_days_between_orders"] = gaps.std()
            f["min_days_between_orders"] = gaps.min()
            f["max_days_between_orders"] = gaps.max()
        else:
            f["avg_days_between_orders"] = np.nan
            f["std_days_between_orders"] = np.nan
            f["min_days_between_orders"] = np.nan
            f["max_days_between_orders"] = np.nan

        # Orders per year (annualised frequency)
        if f["tenure_days"] and f["tenure_days"] > 0:
            f["orders_per_year"] = f["frequency"] / (f["tenure_days"] / 365.25)
        else:
            f["orders_per_year"] = f["frequency"]  # single point

        # ── Quantity patterns ────────────────────────────────────────
        qty = grp["quantity"].dropna()
        if len(qty) > 0:
            f["avg_quantity"] = qty.mean()
            f["median_quantity"] = qty.median()
            f["max_quantity"] = qty.max()
            f["min_quantity"] = qty.min()
            f["std_quantity"] = qty.std() if len(qty) > 1 else 0
        else:
            f["avg_quantity"] = np.nan
            f["median_quantity"] = np.nan
            f["max_quantity"] = np.nan
            f["min_quantity"] = np.nan
            f["std_quantity"] = np.nan

        # ── Unit price patterns ──────────────────────────────────────
        up = grp["unit_price"].dropna()
        if len(up) > 0:
            f["avg_unit_price"] = up.mean()
            f["median_unit_price"] = up.median()
            f["max_unit_price"] = up.max()
        else:
            f["avg_unit_price"] = np.nan
            f["median_unit_price"] = np.nan
            f["max_unit_price"] = np.nan

        # ── Profit margin patterns ───────────────────────────────────
        margin = grp["profit_margin_pct"].dropna()
        margin = margin[(margin > 0) & (margin < 100)]
        if len(margin) > 0:
            f["avg_margin"] = margin.mean()
            f["median_margin"] = margin.median()
        else:
            f["avg_margin"] = np.nan
            f["median_margin"] = np.nan

        # ── Product type distribution (one-hot proportions) ──────────
        pt_counts = grp["product_type"].value_counts()
        total_with_pt = pt_counts.sum()
        for pt in ALL_PRODUCT_TYPES:
            f[f"ptype_{pt}_pct"] = (pt_counts.get(pt, 0) / total_with_pt * 100) if total_with_pt > 0 else 0

        f["product_type_diversity"] = len(pt_counts)  # number of distinct types
        f["has_product_type_pct"] = total_with_pt / len(grp) * 100

        # ── Operations complexity ────────────────────────────────────
        f["avg_num_operations"] = grp["num_operations"].mean()
        f["max_num_operations"] = grp["num_operations"].max()

        # Operation frequency (proportion of orders using each)
        all_ops = []
        for ops_list in grp["operations"]:
            if isinstance(ops_list, list):
                all_ops.extend(ops_list)
        op_counts = Counter(all_ops)
        for op in ALL_OPERATIONS:
            f[f"op_{op}_pct"] = (op_counts.get(op, 0) / len(grp) * 100)

        f["unique_operations_used"] = len(op_counts)

        # ── Cost breakdown complexity ────────────────────────────────
        f["avg_cost_items"] = grp["num_cost_items"].mean()

        # ── Temporal patterns ────────────────────────────────────────
        if len(dated) > 0:
            month_counts = dated["date"].dt.month.value_counts()
            f["peak_month"] = month_counts.index[0]
            f["months_active"] = len(month_counts)

            # Year-over-year trend
            yearly = dated.groupby(dated["date"].dt.year)["total_cost"].sum()
            if len(yearly) >= 2:
                years = yearly.index.values
                revenues = yearly.values
                # Simple linear regression slope
                if len(years) >= 2:
                    slope = np.polyfit(years.astype(float), revenues.astype(float), 1)[0]
                    f["revenue_trend_slope"] = slope
                    f["revenue_trend_pct"] = slope / revenues.mean() * 100 if revenues.mean() > 0 else 0
                else:
                    f["revenue_trend_slope"] = 0
                    f["revenue_trend_pct"] = 0
            else:
                f["revenue_trend_slope"] = 0
                f["revenue_trend_pct"] = 0

            # Recent vs historical spending
            one_year_ago = latest_date - pd.Timedelta(days=365)
            recent = grp[grp["date"] >= one_year_ago]["total_cost"].sum()
            historical = grp[grp["date"] < one_year_ago]["total_cost"].sum()
            f["recent_12m_revenue"] = recent
            f["historical_revenue"] = historical
            f["recent_share_pct"] = (recent / f["monetary_total"] * 100) if f["monetary_total"] > 0 else 0
        else:
            f["peak_month"] = np.nan
            f["months_active"] = 0
            f["revenue_trend_slope"] = np.nan
            f["revenue_trend_pct"] = np.nan
            f["recent_12m_revenue"] = 0
            f["historical_revenue"] = f["monetary_total"]
            f["recent_share_pct"] = 0

        # ── Template era distribution ────────────────────────────────
        era_counts = grp["template_era"].value_counts()
        for era in ["2017_box", "2020_pob_master", "2024_quotation"]:
            f[f"era_{era}_pct"] = (era_counts.get(era, 0) / len(grp) * 100)

        features_list.append(f)

    features_df = pd.DataFrame(features_list)
    log.info(f"Internal features: {features_df.shape[0]} companies × {features_df.shape[1]} features")
    return features_df


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 3: Companies House API Enrichment
# ═══════════════════════════════════════════════════════════════════════════════

COMPANIES_HOUSE_SEARCH_URL = "https://api.company-information.service.gov.uk/search/companies"
COMPANIES_HOUSE_COMPANY_URL = "https://api.company-information.service.gov.uk/company"

# SIC code to industry sector mapping (top-level divisions)
SIC_DIVISIONS = {
    "01-03": "Agriculture",
    "05-09": "Mining",
    "10-33": "Manufacturing",
    "35": "Energy",
    "36-39": "Water & Waste",
    "41-43": "Construction",
    "45-47": "Wholesale & Retail",
    "49-53": "Transport & Storage",
    "55-56": "Accommodation & Food",
    "58-63": "Information & Communication",
    "64-66": "Financial Services",
    "68": "Real Estate",
    "69-75": "Professional Services",
    "77-82": "Administrative Services",
    "84": "Public Admin",
    "85": "Education",
    "86-88": "Health & Social",
    "90-93": "Arts & Entertainment",
    "94-96": "Other Services",
    "97-98": "Household Activities",
    "99": "International Organisations",
}


def _sic_to_sector(sic_code: str) -> str:
    """Map a SIC code to a broad industry sector."""
    if not sic_code:
        return "Unknown"
    try:
        code_num = int(sic_code[:2])
    except (ValueError, IndexError):
        return "Unknown"

    for range_str, sector in SIC_DIVISIONS.items():
        parts = range_str.split("-")
        if len(parts) == 2:
            if int(parts[0]) <= code_num <= int(parts[1]):
                return sector
        elif code_num == int(parts[0]):
            return sector
    return "Unknown"


def _companies_house_search(company_name: str, api_key: str) -> dict | None:
    """Search Companies House for a company by name."""
    params = urllib.parse.urlencode({"q": company_name, "items_per_page": 1})
    url = f"{COMPANIES_HOUSE_SEARCH_URL}?{params}"

    req = urllib.request.Request(url)
    # Companies House uses HTTP Basic Auth with the API key as username
    import base64
    credentials = base64.b64encode(f"{api_key}:".encode()).decode()
    req.add_header("Authorization", f"Basic {credentials}")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            items = data.get("items", [])
            if items:
                return items[0]
    except Exception as e:
        log.debug(f"  Search failed for '{company_name}': {e}")
    return None


def _companies_house_profile(company_number: str, api_key: str) -> dict | None:
    """Get full company profile from Companies House."""
    url = f"{COMPANIES_HOUSE_COMPANY_URL}/{company_number}"
    req = urllib.request.Request(url)

    import base64
    credentials = base64.b64encode(f"{api_key}:".encode()).decode()
    req.add_header("Authorization", f"Basic {credentials}")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        log.debug(f"  Profile failed for {company_number}: {e}")
    return None


def enrich_from_companies_house(
    companies: list[str], api_key: str, cache_path: Path | None = None
) -> pd.DataFrame:
    """Enrich company list from Companies House API.

    Returns a DataFrame with columns:
    - company, ch_company_name, company_number, company_type,
      company_status, sic_codes, industry_sector, incorporation_date,
      region, accounts_type, confirmation_statement_overdue
    """
    # Load cache if available
    cache = {}
    if cache_path and cache_path.exists():
        with open(cache_path) as f:
            cache = json.load(f)
        log.info(f"Loaded {len(cache)} cached Companies House results")

    results = []
    total = len(companies)

    for i, name in enumerate(companies):
        if i > 0 and i % 50 == 0:
            log.info(f"  Companies House: {i}/{total} ({100*i/total:.0f}%)")

        if name in cache:
            results.append(cache[name])
            continue

        # Rate limit: 600 requests per 5 minutes = 2/sec
        time.sleep(0.6)

        result = {
            "company": name,
            "ch_company_name": None,
            "company_number": None,
            "company_type": None,
            "company_status": None,
            "sic_codes": None,
            "industry_sector": None,
            "incorporation_date": None,
            "company_age_years": None,
            "region": None,
            "accounts_type": None,
        }

        # Search
        search_result = _companies_house_search(name, api_key)
        if search_result:
            result["ch_company_name"] = search_result.get("title")
            result["company_number"] = search_result.get("company_number")
            result["company_type"] = search_result.get("company_type")
            result["company_status"] = search_result.get("company_status")

            addr = search_result.get("address", {})
            result["region"] = addr.get("region") or addr.get("locality")

            inc_date_str = search_result.get("date_of_creation")
            if inc_date_str:
                try:
                    inc_date = datetime.strptime(inc_date_str, "%Y-%m-%d")
                    result["incorporation_date"] = inc_date_str
                    result["company_age_years"] = round(
                        (datetime.now() - inc_date).days / 365.25, 1
                    )
                except ValueError:
                    pass

            # Get full profile for SIC codes and accounts
            time.sleep(0.6)
            company_number = search_result.get("company_number")
            if company_number:
                profile = _companies_house_profile(company_number, api_key)
                if profile:
                    sic = profile.get("sic_codes", [])
                    result["sic_codes"] = ",".join(sic) if sic else None
                    result["industry_sector"] = _sic_to_sector(sic[0]) if sic else None

                    accounts = profile.get("accounts", {})
                    result["accounts_type"] = accounts.get("accounting_reference_date", {}).get(
                        "month"
                    )
                    # Use last_accounts to infer company size
                    last_acc = accounts.get("last_accounts", {})
                    result["accounts_type"] = last_acc.get("type")

        cache[name] = result
        results.append(result)

    # Save cache
    if cache_path:
        with open(cache_path, "w") as f:
            json.dump(cache, f, indent=2, default=str)
        log.info(f"Saved {len(cache)} results to cache")

    return pd.DataFrame(results)


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 3b: Companies House Deep Enrichment (Officers, Filings, Charges)
# ═══════════════════════════════════════════════════════════════════════════════


def _ch_api_get(path: str, api_key: str) -> dict | None:
    """Generic Companies House API GET request."""
    import base64

    url = f"https://api.company-information.service.gov.uk{path}"
    req = urllib.request.Request(url)
    credentials = base64.b64encode(f"{api_key}:".encode()).decode()
    req.add_header("Authorization", f"Basic {credentials}")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {}  # no data, not an error
        log.debug(f"  CH API {e.code} for {path}")
    except Exception as e:
        log.debug(f"  CH API failed for {path}: {e}")
    return None


def enrich_deep_companies_house(
    external_df: pd.DataFrame, api_key: str, cache_path: Path | None = None
) -> pd.DataFrame:
    """Pull officers, filing history, and charges for each matched company.

    Uses company_number from the basic enrichment stage.

    New features:
    - officer_count: total officers (current + resigned)
    - active_officer_count: currently active officers
    - director_count: officers with role "director"
    - secretary_count: officers with role "secretary"
    - filing_count: total filings
    - recent_filing_days: days since most recent filing
    - annual_accounts_count: number of annual account filings
    - has_charges: whether the company has any registered charges
    - charge_count: number of charges (loans/mortgages)
    - psc_count: persons with significant control
    """
    # Load cache
    cache = {}
    if cache_path and cache_path.exists():
        with open(cache_path) as f:
            cache = json.load(f)
        log.info(f"Loaded {len(cache)} cached deep results")

    matched = external_df[external_df["company_number"].notna()].copy()
    log.info(f"Deep enriching {len(matched)} companies with company numbers")

    results = []
    total = len(matched)

    for i, (_, row) in enumerate(matched.iterrows()):
        company = row["company"]
        co_num = str(row["company_number"]).strip()

        if i > 0 and i % 50 == 0:
            log.info(f"  Deep enrichment: {i}/{total} ({100*i/total:.0f}%)")

        if company in cache:
            results.append(cache[company])
            continue

        result = {
            "company": company,
            "officer_count": 0,
            "active_officer_count": 0,
            "director_count": 0,
            "secretary_count": 0,
            "filing_count": 0,
            "recent_filing_days": None,
            "annual_accounts_count": 0,
            "has_charges": False,
            "charge_count": 0,
            "psc_count": 0,
        }

        # ── Officers ─────────────────────────────────────────────
        time.sleep(0.6)
        officers_data = _ch_api_get(f"/company/{co_num}/officers?items_per_page=100", api_key)
        if officers_data:
            items = officers_data.get("items", [])
            result["officer_count"] = officers_data.get("total_results", len(items))
            result["active_officer_count"] = sum(
                1 for o in items if not o.get("resigned_on")
            )
            result["director_count"] = sum(
                1 for o in items
                if "director" in (o.get("officer_role", "") or "").lower()
                and not o.get("resigned_on")
            )
            result["secretary_count"] = sum(
                1 for o in items
                if "secretary" in (o.get("officer_role", "") or "").lower()
                and not o.get("resigned_on")
            )

        # ── Filing history ───────────────────────────────────────
        time.sleep(0.6)
        filings_data = _ch_api_get(
            f"/company/{co_num}/filing-history?items_per_page=100", api_key
        )
        if filings_data:
            items = filings_data.get("items", [])
            result["filing_count"] = filings_data.get("total_count", len(items))

            # Most recent filing date
            if items:
                dates = []
                for fi in items:
                    d = fi.get("date")
                    if d:
                        try:
                            dates.append(datetime.strptime(d, "%Y-%m-%d"))
                        except ValueError:
                            pass
                if dates:
                    most_recent = max(dates)
                    result["recent_filing_days"] = (datetime.now() - most_recent).days

            # Count annual accounts specifically
            result["annual_accounts_count"] = sum(
                1 for fi in items if fi.get("category") == "accounts"
            )

        # ── Charges (secured lending) ────────────────────────────
        time.sleep(0.6)
        charges_data = _ch_api_get(f"/company/{co_num}/charges", api_key)
        if charges_data:
            result["charge_count"] = charges_data.get("total_count", 0)
            result["has_charges"] = result["charge_count"] > 0

        # ── Persons with significant control ─────────────────────
        time.sleep(0.6)
        psc_data = _ch_api_get(
            f"/company/{co_num}/persons-with-significant-control", api_key
        )
        if psc_data:
            result["psc_count"] = psc_data.get("total_results", len(psc_data.get("items", [])))

        cache[company] = result
        results.append(result)

    # Also add rows for unmatched companies (with nulls)
    unmatched = external_df[external_df["company_number"].isna()]
    for _, row in unmatched.iterrows():
        results.append({"company": row["company"]})

    # Save cache
    if cache_path:
        with open(cache_path, "w") as f:
            json.dump(cache, f, indent=2, default=str)
        log.info(f"Saved {len(cache)} deep results to cache")

    deep_df = pd.DataFrame(results)
    log.info(f"Deep features: {deep_df.shape[0]} companies × {deep_df.shape[1]} columns")
    return deep_df


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 3c: Web Presence Checks
# ═══════════════════════════════════════════════════════════════════════════════


def _slugify_company(name: str) -> str:
    """Convert company name to a plausible domain slug."""
    s = name.lower().strip()
    # Remove common suffixes
    for suffix in [" limited", " ltd", " plc", " llp", " inc", " group", " uk"]:
        s = s.removesuffix(suffix)
    # Replace special chars
    s = re.sub(r"[&]", "and", s)
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


def _check_domain(domain: str, timeout: float = 5.0) -> dict:
    """Check if a domain resolves and has an HTTP server."""
    result = {"domain": domain, "dns_resolves": False, "http_status": None, "has_https": False}

    # DNS check
    try:
        socket.getaddrinfo(domain, 443, socket.AF_INET, socket.SOCK_STREAM)
        result["dns_resolves"] = True
    except socket.gaierror:
        return result

    # HTTPS check
    try:
        ctx = ssl.create_default_context()
        conn = http.client.HTTPSConnection(domain, timeout=timeout, context=ctx)
        conn.request("HEAD", "/")
        resp = conn.getresponse()
        result["http_status"] = resp.status
        result["has_https"] = True
        conn.close()
    except Exception:
        # Fall back to HTTP
        try:
            conn = http.client.HTTPConnection(domain, timeout=timeout)
            conn.request("HEAD", "/")
            resp = conn.getresponse()
            result["http_status"] = resp.status
            conn.close()
        except Exception:
            pass

    return result


def enrich_web_presence(
    companies: list[str], cache_path: Path | None = None
) -> pd.DataFrame:
    """Check web presence for each company.

    Tries {slug}.co.uk and {slug}.com domains.

    Features:
    - has_website: any domain responded
    - website_domain: best responding domain
    - has_https: site uses HTTPS
    - http_status: response status code
    - domain_variant: which variant matched (co.uk or .com)
    """
    cache = {}
    if cache_path and cache_path.exists():
        with open(cache_path) as f:
            cache = json.load(f)
        log.info(f"Loaded {len(cache)} cached web presence results")

    results = []
    total = len(companies)

    for i, name in enumerate(companies):
        if i > 0 and i % 50 == 0:
            log.info(f"  Web presence: {i}/{total} ({100*i/total:.0f}%)")

        if name in cache:
            results.append(cache[name])
            continue

        slug = _slugify_company(name)
        result = {
            "company": name,
            "has_website": False,
            "website_domain": None,
            "has_https": False,
            "http_status": None,
            "domain_variant": None,
        }

        if not slug or len(slug) < 2:
            cache[name] = result
            results.append(result)
            continue

        # Try domain variants in order of likelihood for UK companies
        variants = [
            (f"{slug}.co.uk", "co.uk"),
            (f"{slug}.com", "com"),
            (f"www.{slug}.co.uk", "co.uk"),
            (f"www.{slug}.com", "com"),
        ]

        for domain, variant in variants:
            check = _check_domain(domain, timeout=4.0)
            if check["dns_resolves"] and check["http_status"] and check["http_status"] < 500:
                result["has_website"] = True
                result["website_domain"] = domain
                result["has_https"] = check["has_https"]
                result["http_status"] = check["http_status"]
                result["domain_variant"] = variant
                break

        cache[name] = result
        results.append(result)

    # Save cache
    if cache_path:
        with open(cache_path, "w") as f:
            json.dump(cache, f, indent=2, default=str)
        log.info(f"Saved {len(cache)} web results to cache")

    web_df = pd.DataFrame(results)
    matched = web_df["has_website"].sum()
    log.info(f"Web presence: {matched}/{total} companies have a website ({100*matched/total:.0f}%)")
    return web_df


# ═══════════════════════════════════════════════════════════════════════════════
# STAGE 4: Merge & Output
# ═══════════════════════════════════════════════════════════════════════════════


def merge_and_output(
    internal_df: pd.DataFrame,
    external_df: pd.DataFrame | None = None,
    deep_df: pd.DataFrame | None = None,
    web_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Merge internal and external features into final dataset."""
    if external_df is not None and len(external_df) > 0:
        merged = internal_df.merge(external_df, on="company", how="left")
    else:
        merged = internal_df.copy()

    if deep_df is not None and len(deep_df) > 0:
        merged = merged.merge(deep_df, on="company", how="left")

    if web_df is not None and len(web_df) > 0:
        merged = merged.merge(web_df, on="company", how="left")

    # Derive additional computed features
    if "company_age_years" in merged.columns:
        merged["orders_per_company_year"] = np.where(
            merged["company_age_years"] > 0,
            merged["frequency"] / merged["company_age_years"],
            merged["frequency"],
        )

    # Customer value tier (quintiles of monetary_total)
    merged["value_quintile"] = pd.qcut(
        merged["monetary_total"], q=5, labels=[1, 2, 3, 4, 5], duplicates="drop"
    )

    # Frequency tier
    freq_bins = [0, 1, 3, 10, 30, float("inf")]
    freq_labels = ["one_time", "occasional", "regular", "frequent", "power_user"]
    merged["frequency_tier"] = pd.cut(
        merged["frequency"], bins=freq_bins, labels=freq_labels, right=True
    )

    # Activity status
    if "recency_days" in merged.columns:
        merged["is_active_12m"] = merged["recency_days"] <= 365
        merged["is_active_6m"] = merged["recency_days"] <= 180
        merged["is_churned"] = merged["recency_days"] > 730

    log.info(f"Final dataset: {merged.shape[0]} companies × {merged.shape[1]} features")
    return merged


# ═══════════════════════════════════════════════════════════════════════════════
# Main Pipeline
# ═══════════════════════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(description="Company enrichment pipeline")
    parser.add_argument("--skip-api", action="store_true", help="Skip Companies House API")
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Companies House API key (or set COMPANIES_HOUSE_API_KEY env var)",
    )
    parser.add_argument(
        "--stage",
        choices=["clean", "features", "enrich", "enrich-deep", "web", "merge", "all"],
        default="all",
        help="Run only a specific stage",
    )
    args = parser.parse_args()

    import os
    api_key = args.api_key or os.environ.get("COMPANIES_HOUSE_API_KEY")
    if not api_key and API_KEY_FILE.exists():
        for line in API_KEY_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith("COMPANIES_HOUSE_API_KEY="):
                api_key = line.split("=", 1)[1].strip()
                break

    # ── Load raw data ────────────────────────────────────────────────
    log.info(f"Loading {LEGACY_JSON}")
    with open(LEGACY_JSON) as f:
        raw = json.load(f)
    log.info(f"Loaded {len(raw)} records")

    # ── Stage 1: Clean company names ─────────────────────────────────
    if args.stage in ("clean", "all"):
        log.info("=" * 60)
        log.info("STAGE 1: Cleaning company names")
        log.info("=" * 60)

        name_mapping = clean_company_names(raw)

        # Save mapping
        COMPANIES_DIR.mkdir(parents=True, exist_ok=True)
        with open(CLEAN_MAP_PATH, "w") as f:
            json.dump(name_mapping, f, indent=2, ensure_ascii=False)
        log.info(f"Saved name mapping to {CLEAN_MAP_PATH}")

    # Load name mapping (may have been saved in a previous run)
    if CLEAN_MAP_PATH.exists():
        with open(CLEAN_MAP_PATH) as f:
            name_mapping = json.load(f)
    else:
        log.error("Name mapping not found. Run --stage clean first.")
        sys.exit(1)

    # ── Build DataFrame with cleaned names ───────────────────────────
    rows = []
    for r in raw:
        orig_name = (r.get("company_name") or "").strip()
        clean_name = name_mapping.get(orig_name, orig_name) if orig_name else None

        # Skip non-companies (mapped to null)
        if clean_name is None and orig_name:
            continue
        if not clean_name:
            continue

        row = {
            "company_clean": clean_name,
            "company_original": orig_name,
            "date": r.get("date"),
            "total_cost": r.get("total_cost"),
            "quantity": r.get("quantities", [None])[0] if r.get("quantities") else None,
            "unit_price": r.get("unit_prices", [None])[0] if r.get("unit_prices") else None,
            "profit_margin_pct": r.get("profit_margin_pct"),
            "product_type": r.get("product_type"),
            "num_operations": len(r.get("operations", [])),
            "operations": r.get("operations", []),
            "num_cost_items": len(r.get("cost_breakdown", {})),
            "template_era": r.get("template_era"),
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True)
    # Filter to records with valid cost
    df = df[df["total_cost"].notna() & (df["total_cost"] > 0)]
    log.info(f"Working dataset: {len(df)} records, {df['company_clean'].nunique()} companies")

    # ── Stage 2: Internal features ───────────────────────────────────
    if args.stage in ("features", "all"):
        log.info("=" * 60)
        log.info("STAGE 2: Engineering internal features")
        log.info("=" * 60)

        internal_df = engineer_internal_features(df)
        internal_df.to_csv(INTERNAL_FEATURES_PATH, index=False)
        log.info(f"Saved to {INTERNAL_FEATURES_PATH}")

    # ── Stage 3: Companies House enrichment ──────────────────────────
    external_df = None
    if args.stage in ("enrich", "all") and not args.skip_api:
        log.info("=" * 60)
        log.info("STAGE 3: Companies House API enrichment")
        log.info("=" * 60)

        if not api_key:
            log.warning(
                "No API key provided. Get a free key at "
                "https://developer.company-information.service.gov.uk/\n"
                "Set COMPANIES_HOUSE_API_KEY env var or use --api-key flag.\n"
                "Skipping API enrichment."
            )
        else:
            companies = sorted(df["company_clean"].unique().tolist())
            cache_path = COMPANIES_DIR / "ch_cache.json"
            external_df = enrich_from_companies_house(companies, api_key, cache_path)
            external_df.to_csv(EXTERNAL_FEATURES_PATH, index=False)
            log.info(f"Saved to {EXTERNAL_FEATURES_PATH}")

    elif args.stage in ("enrich-deep", "web", "merge", "all"):
        # Try loading previously saved external features
        if EXTERNAL_FEATURES_PATH.exists():
            external_df = pd.read_csv(EXTERNAL_FEATURES_PATH)
            log.info(f"Loaded external features: {len(external_df)} companies")

    # ── Stage 3b: Companies House deep enrichment ────────────────────
    deep_df = None
    if args.stage in ("enrich-deep", "all") and not args.skip_api:
        log.info("=" * 60)
        log.info("STAGE 3b: Companies House deep enrichment (officers, filings, charges)")
        log.info("=" * 60)

        if not api_key:
            log.warning("No API key — skipping deep enrichment.")
        elif external_df is None:
            log.warning("No basic CH data — run --stage enrich first.")
        else:
            deep_cache_path = COMPANIES_DIR / "ch_deep_cache.json"
            deep_df = enrich_deep_companies_house(external_df, api_key, deep_cache_path)
            deep_df.to_csv(DEEP_FEATURES_PATH, index=False)
            log.info(f"Saved to {DEEP_FEATURES_PATH}")

    elif args.stage in ("merge", "all"):
        if DEEP_FEATURES_PATH.exists():
            deep_df = pd.read_csv(DEEP_FEATURES_PATH)
            log.info(f"Loaded deep features: {len(deep_df)} companies")

    # ── Stage 3c: Web presence checks ────────────────────────────────
    web_df = None
    if args.stage in ("web", "all"):
        log.info("=" * 60)
        log.info("STAGE 3c: Web presence checks")
        log.info("=" * 60)

        companies = sorted(df["company_clean"].unique().tolist())
        web_cache_path = COMPANIES_DIR / "web_cache.json"
        web_df = enrich_web_presence(companies, web_cache_path)
        web_df.to_csv(WEB_FEATURES_PATH, index=False)
        log.info(f"Saved to {WEB_FEATURES_PATH}")

    elif args.stage in ("merge",):
        if WEB_FEATURES_PATH.exists():
            web_df = pd.read_csv(WEB_FEATURES_PATH)
            log.info(f"Loaded web features: {len(web_df)} companies")

    # ── Stage 4: Merge & output ──────────────────────────────────────
    if args.stage in ("merge", "all"):
        log.info("=" * 60)
        log.info("STAGE 4: Merging and outputting final dataset")
        log.info("=" * 60)

        # Load internal features if not already in memory
        if args.stage == "merge":
            if INTERNAL_FEATURES_PATH.exists():
                internal_df = pd.read_csv(INTERNAL_FEATURES_PATH)
            else:
                log.error("Internal features not found. Run --stage features first.")
                sys.exit(1)

        final_df = merge_and_output(internal_df, external_df, deep_df, web_df)
        final_df.to_csv(FINAL_DATASET_PATH, index=False)
        log.info(f"Final dataset saved to {FINAL_DATASET_PATH}")

        # Summary stats
        log.info("\n" + "=" * 60)
        log.info("PIPELINE SUMMARY")
        log.info("=" * 60)
        log.info(f"Companies:     {len(final_df)}")
        log.info(f"Features:      {len(final_df.columns)}")
        log.info(f"Output:        {FINAL_DATASET_PATH}")

        # Feature completeness
        completeness = final_df.notna().mean()
        full = (completeness == 1.0).sum()
        partial = ((completeness > 0) & (completeness < 1.0)).sum()
        empty = (completeness == 0).sum()
        log.info(f"Completeness:  {full} full, {partial} partial, {empty} empty columns")

        # Value distribution
        if "value_quintile" in final_df.columns:
            print("\nValue distribution:")
            for q, count in final_df["value_quintile"].value_counts().sort_index().items():
                print(f"  Q{q}: {count} companies")

        if "frequency_tier" in final_df.columns:
            print("\nFrequency tiers:")
            for tier, count in final_df["frequency_tier"].value_counts().items():
                print(f"  {tier}: {count}")


if __name__ == "__main__":
    main()
