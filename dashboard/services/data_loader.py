"""
Data Loading Service
Handles loading and caching of all data files

SEGMENT MAPPING (Single Source of Truth)
=========================================
Segments 0-4: ADS Core Recluster (subclusters of initial mixed cluster 0)
Segments 5-7: Original primary clusters 1, 2, 3 (remapped)

Final Mapping Table:
| Segment | Source           | Name                      | Median £  | Priority    | Motion               |
|---------|------------------|---------------------------|-----------|-------------|----------------------|
| 0       | core_subcluster0 | Early-Churn Burst         | £1,621    | MEDIUM      | Friction removal     |
| 1       | core_subcluster1 | Lapsed Regular            | £3,967    | HIGH        | Diagnosis-first      |
| 2       | core_subcluster2 | High-Cadence Lapsed       | £2,495    | HIGH        | Win-back             |
| 3       | core_subcluster3 | Project Re-quote          | £2,877    | MEDIUM      | Semi-personal        |
| 4       | core_subcluster4 | Win-back VIP              | £19,748   | CRITICAL    | Executive win-back   |
| 5       | initial_cluster1 | Long-Tenure Relationship  | £2,474    | PROTECT     | Retention + grow     |
| 6       | initial_cluster2 | Dormant Mid-Tenure        | £2,859    | LOW-MEDIUM  | Re-engagement        |
| 7       | initial_cluster3 | Archive/Low-Touch         | £789      | LOWEST      | Batch only           |

METRIC NOTES:
- recent_12m_revenue: Computed from orders with invoice_date in trailing 365 days from
  snapshot date (Oct 2024). May show £0 for customers with high recency_days.
- recency_days: Days since last order from snapshot date.
- estimates_per_year: Annual rate of quote requests (indicates engagement/intent).
"""
import streamlit as st
import pandas as pd
import json
from pathlib import Path

# Base paths - using local data within dashboard for standalone deployment
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data" / "companies"
MODELS_DIR = BASE_DIR / "models" / "customer_segments"
OUTPUTS_DIR = BASE_DIR / "outputs" / "segmentation"

# =============================================================================
# GLOBAL ACTIVE CUSTOMER DEFINITION
# =============================================================================
# Active = recency_days <= ACTIVE_THRESHOLD (configurable)
# This applies across ALL segments, not just Segment 5
ACTIVE_THRESHOLD_DAYS = 365  # Configurable: customers with last order within this period

# =============================================================================
# SEGMENT CONFIGURATION - SINGLE SOURCE OF TRUTH
# =============================================================================
# NOTE: is_active is computed per-customer using recency_days <= ACTIVE_THRESHOLD_DAYS
# The segment-level pct_active shows what % of each segment is currently active

SEGMENT_CONFIG = {
    0: {
        "name": "Early-Churn Burst",
        "short_name": "Burst Churn",
        "source": "core_subcluster0",
        "color": "#FF7043",  # Deep Orange - onboarding friction
        "priority": "MEDIUM",
        "priority_rank": 4,  # Lower than HIGH segments
        "motion": "Friction Removal",
        "action_label": "Early-Churn Burst",
        # Computed metrics (from data):
        "pct_active": 12.0,  # 82/686 with recency <= 365
        "median_recency_days": 1432,
        "mean_recency_days": 1420,
        "median_monetary": 1621,  # Use median to avoid skew
        "mean_monetary": 10615,
        "orders_per_year_median": 1.0,  # Most are one-time
        "orders_per_year_mean": 20.6,   # Skewed by burst buyers
    },
    1: {
        "name": "Lapsed Regular",
        "short_name": "Lapsed",
        "source": "core_subcluster1",
        "color": "#AB47BC",  # Purple - diagnosis needed
        "priority": "HIGH",
        "priority_rank": 3,
        "motion": "Diagnosis-First",
        "action_label": "Lapsed Regular",
        "pct_active": 57.1,  # 4/7 with recency <= 365
        "median_recency_days": 327,
        "mean_recency_days": 716,
        "median_monetary": 3967,
        "mean_monetary": 6166,
        "orders_per_year_median": 4.84,
        "orders_per_year_mean": 4.05,
    },
    2: {
        "name": "High-Cadence Lapsed",
        "short_name": "High-Cadence",
        "source": "core_subcluster2",
        "color": "#5C6BC0",  # Indigo - high activity pattern
        "priority": "HIGH",
        "priority_rank": 3,
        "motion": "Win-back",
        "action_label": "High-Cadence Lapsed",
        "pct_active": 16.1,  # 5/31 with recency <= 365
        "median_recency_days": 1192,
        "mean_recency_days": 1190,
        "median_monetary": 2495,
        "mean_monetary": 6347,
        "orders_per_year_median": 18.73,  # HIGHEST historical activity rate
        "orders_per_year_mean": 22.04,
        # NOTE: High historical activity (18.7 orders/year) but now 84% dormant
    },
    3: {
        "name": "Project Re-quote",
        "short_name": "Project",
        "source": "core_subcluster3",
        "color": "#26A69A",  # Teal - project-based
        "priority": "MEDIUM",
        "priority_rank": 4,
        "motion": "Project Re-quote",
        "action_label": "Project Re-quote",
        "pct_active": 14.3,  # 2/14 with recency <= 365
        "median_recency_days": 1129,
        "mean_recency_days": 1288,
        "median_monetary": 2877,
        "mean_monetary": 6826,
        "orders_per_year_median": 9.34,
        "orders_per_year_mean": 8.63,
    },
    4: {
        "name": "Win-back VIP",
        "short_name": "VIP",
        "source": "core_subcluster4",
        "color": "#E53935",  # Red - CRITICAL
        "priority": "CRITICAL",
        "priority_rank": 1,  # Highest priority for win-back
        "motion": "Executive Win-back",
        "action_label": "Win-back VIP",
        "pct_active": 49.6,  # 58/117 with recency <= 365 (VERIFIED)
        "median_recency_days": 415,
        "mean_recency_days": 576,
        "median_monetary": 19748,  # Use median - less skewed
        "mean_monetary": 91587,   # Mean skewed by outliers
        "orders_per_year_median": 2.70,
        "orders_per_year_mean": 6.05,
    },
    5: {
        "name": "Long-Tenure Relationship",
        "short_name": "Relationship",
        "source": "initial_cluster1",
        "color": "#43A047",  # Green - relationship focus
        "priority": "PROTECT",
        "priority_rank": 2,  # High priority but separate from CRITICAL win-back
        "motion": "Retention + Grow",
        "action_label": "Protect Relationship",
        "pct_active": 40.0,  # 2/5 with recency <= 365
        "median_recency_days": 375,
        "mean_recency_days": 449,
        "median_monetary": 2474,
        "mean_monetary": 3856,
        "orders_per_year_median": 0.44,
        "orders_per_year_mean": 0.43,
        "mean_tenure_days": 1722,  # Long-term relationships
        # NOTE: Long tenure (1722d) - relationship-heavy cohort worth protecting
    },
    6: {
        "name": "Dormant Mid-Tenure",
        "short_name": "Mid-Dormant",
        "source": "initial_cluster2",
        "color": "#FFA726",  # Orange - re-engagement
        "priority": "LOW-MEDIUM",
        "priority_rank": 5,
        "motion": "Re-engagement",
        "action_label": "Dormant Mid-Tenure",
        "pct_active": 15.8,  # 6/38 with recency <= 365
        "median_recency_days": 840,
        "mean_recency_days": 1018,
        "median_monetary": 2859,
        "mean_monetary": 5077,
        "orders_per_year_median": 1.63,
        "orders_per_year_mean": 1.97,
    },
    7: {
        "name": "Archive/Low-Touch",
        "short_name": "Archive",
        "source": "initial_cluster3",
        "color": "#78909C",  # Blue Grey - lowest priority
        "priority": "LOWEST",
        "priority_rank": 6,
        "motion": "Batch Only",
        "action_label": "Archive",
        "pct_active": 10.0,  # 1/10 with recency <= 365
        "median_recency_days": 724,
        "mean_recency_days": 905,
        "median_monetary": 789,  # LOWEST
        "mean_monetary": 1393,
        "orders_per_year_median": 0.65,
        "orders_per_year_mean": 0.75,
    },
}

# Derived mappings for backward compatibility
SEGMENT_COLORS = {seg_id: cfg["color"] for seg_id, cfg in SEGMENT_CONFIG.items()}
SEGMENT_NAMES = {seg_id: cfg["name"] for seg_id, cfg in SEGMENT_CONFIG.items()}

# Priority order for display
# CRITICAL (Seg 4) first, then PROTECT (Seg 5), then HIGH, MEDIUM, LOW
# This keeps win-back and retention visually separated in UI
SEGMENT_PRIORITY_ORDER = sorted(
    SEGMENT_CONFIG.keys(),
    key=lambda x: (SEGMENT_CONFIG[x]["priority_rank"], -x)
)
# Result: [4, 5, 1, 2, 0, 3, 6, 7]

# Metric tooltips for UI - clarified definitions
METRIC_TOOLTIPS = {
    "monetary_total": (
        "Total historic revenue per company (all-time). "
        "UI displays MEDIAN by default to avoid outlier skew."
    ),
    "recent_12m_revenue": (
        "Revenue from orders with invoice_date in trailing 365 days from Oct 2024 snapshot. "
        "Will be £0 for companies with recency_days > 365 (no orders in window)."
    ),
    "recency_days": (
        "Days since last order (from Oct 2024 snapshot). "
        f"Active customer = recency_days ≤ {ACTIVE_THRESHOLD_DAYS}."
    ),
    "pct_active": (
        f"Percentage of segment with recency_days ≤ {ACTIVE_THRESHOLD_DAYS}. "
        "Computed from actual data, not assumed."
    ),
    "orders_per_year": (
        "Annualized order frequency. When mean >> median, indicates skewed distribution "
        "(few high-activity customers pulling up average)."
    ),
    "avg_days_between_orders": (
        "Average gap between orders. Low value + short tenure = "
        "burst ordering pattern (high activity, then churn)."
    ),
    "tenure_days": (
        "Days between first and last order. "
        "Short tenure + high orders_per_year = burst pattern."
    ),
}


def get_active_customers(df, threshold=None):
    """
    Get active customers (recency_days <= threshold) from dataframe.

    Args:
        df: DataFrame with 'recency_days' column
        threshold: Days threshold (default: ACTIVE_THRESHOLD_DAYS)

    Returns:
        DataFrame of active customers only
    """
    if threshold is None:
        threshold = ACTIVE_THRESHOLD_DAYS
    if 'recency_days' not in df.columns:
        return df
    return df[df['recency_days'] <= threshold]


def get_active_count_by_segment(df, threshold=None):
    """
    Get active customer count per segment.

    Returns dict: {segment_id: (active_count, total_count, pct_active)}
    """
    if threshold is None:
        threshold = ACTIVE_THRESHOLD_DAYS

    results = {}
    if 'ads_cluster' not in df.columns or 'recency_days' not in df.columns:
        return results

    for seg_id in df['ads_cluster'].dropna().unique():
        seg_data = df[df['ads_cluster'] == seg_id]
        total = len(seg_data)
        active = (seg_data['recency_days'] <= threshold).sum()
        pct = (active / total * 100) if total > 0 else 0
        results[int(seg_id)] = (active, total, pct)

    return results


@st.cache_data(ttl=3600)
def load_cluster_profiles() -> dict:
    """Load cluster profiles with persona definitions"""
    profiles_path = MODELS_DIR / "cluster_profiles.json"

    if profiles_path.exists():
        with open(profiles_path, 'r') as f:
            return json.load(f)

    # Fallback profiles - 8 segments from hierarchical clustering
    # Segments 0-4: ADS core recluster (subclusters of initial mixed cluster 0)
    # Segments 5-7: Original primary clusters 1, 2, 3 (remapped)
    # CORRECTED based on boxplot validation and cluster analysis
    return {
        "0": {
            "name": "Early-Churn Burst",
            "description": "Short tenure (~59 days) but high activity burst (avg 8.5 days between orders, 20.6 estimates/year). These customers engaged intensively then churned - likely onboarding friction (spec/lead time/quality/MOQ issues).",
            "characteristics": {
                "monetary_range": "£10,614 avg",
                "frequency_range": "High burst activity",
                "tenure_range": "~59 days avg (short)",
                "estimates_per_year": "20.6 avg (high engagement)",
                "avg_days_between_orders": "8.5 days (frequent during active period)"
            },
            "recommended_actions": [
                "Automated friction-removal CTA",
                "Survey on onboarding experience",
                "Address spec/MOQ/lead time concerns",
                "Escalate only top-value subset for personal outreach"
            ],
            "risk_level": "MEDIUM - Onboarding Issue",
            "motion": "Friction Removal",
            "color": "#FF7043"
        },
        "1": {
            "name": "Lapsed Regular",
            "description": "Previously regular customers who stopped ordering. Need diagnosis before discounting - understand WHY they left before offering incentives.",
            "characteristics": {
                "monetary_range": "£6,166 avg",
                "frequency_range": "Regular historical pattern",
                "recency_range": "Dormant but recoverable"
            },
            "recommended_actions": [
                "Personal phone outreach - diagnosis first",
                "Avoid discount-first approach",
                "Understand service/quality/pricing concerns",
                "Tailored win-back based on feedback"
            ],
            "risk_level": "HIGH - Recoverable Value",
            "motion": "Diagnosis-First",
            "color": "#AB47BC"
        },
        "2": {
            "name": "High-Cadence Lapsed",
            "description": "Highest historical activity (18.7 orders/year median) but now 84% dormant. Were highly engaged when active - worth win-back effort.",
            "characteristics": {
                "monetary_range": "£2,495 median (£6,347 mean)",
                "frequency_range": "18.7 orders/year median (highest historically)",
                "recency_range": "1,192 days median (84% dormant)"
            },
            "recommended_actions": [
                "Win-back with barrier removal focus",
                "Fast re-quote with simplified process",
                "Review historical patterns for personalization"
            ],
            "risk_level": "HIGH - Win-back Priority",
            "motion": "Win-back",
            "color": "#5C6BC0"
        },
        "3": {
            "name": "Project Re-quote",
            "description": "Higher AOV (£6,826) with infrequent, project-based ordering. These customers buy for specific projects - maintain awareness and re-engage when projects arise.",
            "characteristics": {
                "monetary_range": "£6,826 avg (higher AOV)",
                "frequency_range": "Infrequent, project-based",
                "recency_range": "Project cycle dependent"
            },
            "recommended_actions": [
                "Semi-personal quarterly outreach",
                "Project planning check-ins",
                "Case study and capability updates",
                "Be ready for fast turnaround when project starts"
            ],
            "risk_level": "MEDIUM - Project Cycle",
            "motion": "Project Re-quote",
            "color": "#26A69A"
        },
        "4": {
            "name": "Win-back VIP",
            "description": "CRITICAL: Highest value (median £19,748, mean £91,587). 49.6% still active (58/117 verified with recency <= 365). Executive-level tiered win-back required.",
            "characteristics": {
                "monetary_range": "£19,748 median (£91,587 mean)",
                "frequency_range": "2.70 orders/year median",
                "recency_range": "415 days median (49.6% active)",
                "total_segment_revenue": "£10.7M opportunity"
            },
            "recommended_actions": [
                "URGENT: Executive outreach within 48 hours",
                "Tiered offer ladder: Service fix → Commercial terms → Incentive",
                "Reason-coded churn analysis for each account",
                "Account review meeting with senior leadership"
            ],
            "risk_level": "CRITICAL - Highest Revenue at Risk",
            "motion": "Executive Win-back",
            "color": "#E53935"
        },
        "5": {
            "name": "Long-Tenure Relationship",
            "description": "Long-tenure cohort (1722d avg tenure). 40% currently active. Relationship-heavy segment - protect and grow.",
            "characteristics": {
                "monetary_range": "£2,474 median (£3,856 mean)",
                "frequency_range": "0.44 orders/year median",
                "recency_range": "375 days median (40% active)",
                "tenure_days": "1,722 days avg (long relationship)"
            },
            "recommended_actions": [
                "PROTECT: Dedicated account management",
                "Cross-sell and upsell opportunities",
                "Loyalty recognition program",
                "Quarterly business reviews"
            ],
            "risk_level": "PROTECT - Relationship Value",
            "motion": "Retention + Grow",
            "color": "#43A047"
        },
        "6": {
            "name": "Dormant Mid-Tenure",
            "description": "Had relationship (mid-tenure) but now 84% dormant. Worth moderate re-engagement effort with special return offers.",
            "characteristics": {
                "monetary_range": "£5,077 avg",
                "frequency_range": "2.7 orders avg",
                "recency_range": "1,018 days avg (84% dormant)"
            },
            "recommended_actions": [
                "'We miss you' email sequence",
                "Special return customer offer",
                "Quarterly touchpoints",
                "Re-engagement campaign"
            ],
            "risk_level": "LOW-MEDIUM",
            "motion": "Re-engagement",
            "color": "#FFA726"
        },
        "7": {
            "name": "Archive/Low-Touch",
            "description": "Long-cycle, low-value (£1,393 avg), near-zero recent_12m_revenue. True dormant/archive segment - minimal marketing investment only.",
            "characteristics": {
                "monetary_range": "£1,393 avg (LOWEST)",
                "frequency_range": "2.0 orders avg",
                "recency_range": "Very high (90% dormant)",
                "recent_12m_revenue": "Near zero"
            },
            "recommended_actions": [
                "Include in batch emails only (2x/year)",
                "No personal outreach - not cost-effective",
                "Consider for archive/write-off",
                "Seasonal promotional inclusion only"
            ],
            "risk_level": "LOWEST",
            "motion": "Batch Only",
            "color": "#78909C"
        }
    }


@st.cache_data(ttl=3600)
def load_company_data() -> pd.DataFrame:
    """Load the main company features dataset"""
    data_path = DATA_DIR / "company_features_processed_base.csv"

    if data_path.exists():
        df = pd.read_csv(data_path)
        return df

    st.error(f"Company data not found at {data_path}")
    return pd.DataFrame()


@st.cache_data(ttl=3600)
def load_cluster_assignments() -> pd.DataFrame:
    """Load cluster assignments for all companies - using 8-segment hierarchical model"""
    # Use final_cluster_assignments.csv which has 8 segments from hierarchical clustering
    assignments_path = DATA_DIR / "ads_clustering" / "final_cluster_assignments.csv"

    if assignments_path.exists():
        df = pd.read_csv(assignments_path)
        # Rename to match expected column name
        if 'final_cluster' in df.columns:
            df = df.rename(columns={'final_cluster': 'ads_cluster'})
        return df

    # Fallback to old 4-cluster file
    old_path = DATA_DIR / "ads_clustering" / "ads_cluster_assignments.csv"
    if old_path.exists():
        return pd.read_csv(old_path)

    st.error("Cluster assignments not found")
    return pd.DataFrame()


@st.cache_data(ttl=3600)
def load_cluster_profiles_detailed() -> pd.DataFrame:
    """Load detailed cluster statistics"""
    profiles_path = OUTPUTS_DIR / "cluster_profiles_detailed.csv"

    if profiles_path.exists():
        return pd.read_csv(profiles_path, index_col=0, header=[0, 1])

    return pd.DataFrame()


@st.cache_data(ttl=3600)
def get_companies_by_segment(segment_id: int) -> pd.DataFrame:
    """Get all companies belonging to a specific segment"""
    companies = load_company_data()
    assignments = load_cluster_assignments()

    if companies.empty or assignments.empty:
        return pd.DataFrame()

    # Merge companies with their cluster assignments
    merged = companies.merge(assignments, on='company', how='left')

    # Filter by segment
    segment_companies = merged[merged['ads_cluster'] == segment_id]

    return segment_companies


@st.cache_data(ttl=3600)
def get_company_details(company_name: str) -> dict:
    """Get detailed information for a specific company"""
    companies = load_company_data()
    assignments = load_cluster_assignments()
    profiles = load_cluster_profiles()

    if companies.empty:
        return {}

    company_row = companies[companies['company'] == company_name]

    if company_row.empty:
        return {}

    company_data = company_row.iloc[0].to_dict()

    # Add cluster info
    if not assignments.empty:
        cluster_row = assignments[assignments['company'] == company_name]
        if not cluster_row.empty:
            cluster_id = str(cluster_row.iloc[0]['ads_cluster'])
            company_data['cluster_id'] = int(cluster_id)
            company_data['cluster_name'] = profiles.get(cluster_id, {}).get('name', 'Unknown')
            company_data['cluster_profile'] = profiles.get(cluster_id, {})

    return company_data


@st.cache_data(ttl=3600)
def get_feature_stats() -> dict:
    """Get statistics for key features across all segments"""
    companies = load_company_data()
    assignments = load_cluster_assignments()

    if companies.empty or assignments.empty:
        return {}

    merged = companies.merge(assignments, on='company', how='left')

    key_features = [
        'frequency', 'monetary_total', 'monetary_mean',
        'recency_days', 'tenure_days', 'estimates_per_year',
        'avg_days_between_orders', 'product_type_diversity'
    ]

    # Filter to existing columns
    available_features = [f for f in key_features if f in merged.columns]

    stats = {}
    for feature in available_features:
        stats[feature] = {
            'overall_mean': merged[feature].mean(),
            'overall_median': merged[feature].median(),
            'by_segment': merged.groupby('ads_cluster')[feature].agg(['mean', 'median', 'std']).to_dict()
        }

    return stats
