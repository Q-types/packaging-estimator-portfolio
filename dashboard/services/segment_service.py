"""
Segment Service
Business logic for segment analysis and insights
"""
import streamlit as st
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from services.data_loader import (
    load_cluster_profiles,
    load_company_data,
    load_cluster_assignments,
    get_feature_stats
)


def get_segment_summary() -> pd.DataFrame:
    """Get summary statistics for all segments"""
    companies = load_company_data()
    assignments = load_cluster_assignments()
    profiles = load_cluster_profiles()

    if companies.empty or assignments.empty:
        return pd.DataFrame()

    merged = companies.merge(assignments, on='company', how='left')

    summary_data = []
    for seg_id in sorted(merged['ads_cluster'].unique()):
        seg_data = merged[merged['ads_cluster'] == seg_id]
        profile = profiles.get(str(int(seg_id)), {})

        summary_data.append({
            'Segment ID': int(seg_id),
            'Name': profile.get('name', f'Segment {seg_id}'),
            'Count': len(seg_data),
            'Percentage': len(seg_data) / len(merged) * 100,
            'Avg Revenue': seg_data['monetary_total'].mean() if 'monetary_total' in seg_data else 0,
            'Avg Frequency': seg_data['frequency'].mean() if 'frequency' in seg_data else 0,
            'Avg Recency (days)': seg_data['recency_days'].mean() if 'recency_days' in seg_data else 0,
            'Risk Level': profile.get('risk_level', 'Unknown')
        })

    return pd.DataFrame(summary_data)


def get_segment_comparison(feature: str) -> pd.DataFrame:
    """Compare a specific feature across all segments"""
    companies = load_company_data()
    assignments = load_cluster_assignments()
    profiles = load_cluster_profiles()

    if companies.empty or assignments.empty or feature not in companies.columns:
        return pd.DataFrame()

    merged = companies.merge(assignments, on='company', how='left')

    comparison = merged.groupby('ads_cluster')[feature].agg([
        'mean', 'median', 'std', 'min', 'max', 'count'
    ]).reset_index()

    comparison['segment_name'] = comparison['ads_cluster'].apply(
        lambda x: profiles.get(str(int(x)), {}).get('name', f'Segment {x}')
    )

    return comparison


def get_rfm_analysis() -> Dict[str, pd.DataFrame]:
    """Get RFM (Recency, Frequency, Monetary) analysis by segment"""
    companies = load_company_data()
    assignments = load_cluster_assignments()
    profiles = load_cluster_profiles()

    if companies.empty or assignments.empty:
        return {}

    merged = companies.merge(assignments, on='company', how='left')

    rfm_cols = ['recency_days', 'frequency', 'monetary_total']
    available_rfm = [c for c in rfm_cols if c in merged.columns]

    if not available_rfm:
        return {}

    rfm_by_segment = merged.groupby('ads_cluster')[available_rfm].agg(['mean', 'median'])

    # Flatten column names
    rfm_by_segment.columns = ['_'.join(col).strip() for col in rfm_by_segment.columns]
    rfm_by_segment = rfm_by_segment.reset_index()

    # Add segment names
    rfm_by_segment['segment_name'] = rfm_by_segment['ads_cluster'].apply(
        lambda x: profiles.get(str(int(x)), {}).get('name', f'Segment {x}')
    )

    return {
        'summary': rfm_by_segment,
        'raw': merged[['company', 'ads_cluster'] + available_rfm]
    }


def get_segment_health_scores() -> pd.DataFrame:
    """Calculate health scores for each segment based on key metrics"""
    companies = load_company_data()
    assignments = load_cluster_assignments()
    profiles = load_cluster_profiles()

    if companies.empty or assignments.empty:
        return pd.DataFrame()

    merged = companies.merge(assignments, on='company', how='left')

    health_data = []

    for seg_id in sorted(merged['ads_cluster'].unique()):
        seg_data = merged[merged['ads_cluster'] == seg_id]
        profile = profiles.get(str(int(seg_id)), {})

        # Calculate health scores (0-100)
        recency_score = 100 - min(100, seg_data['recency_days'].mean() / 10) if 'recency_days' in seg_data else 50
        frequency_score = min(100, seg_data['frequency'].mean() * 5) if 'frequency' in seg_data else 50
        monetary_score = min(100, seg_data['monetary_total'].mean() / 500) if 'monetary_total' in seg_data else 50

        overall_health = (recency_score + frequency_score + monetary_score) / 3

        health_data.append({
            'Segment': profile.get('name', f'Segment {seg_id}'),
            'Recency Score': round(recency_score, 1),
            'Frequency Score': round(frequency_score, 1),
            'Monetary Score': round(monetary_score, 1),
            'Overall Health': round(overall_health, 1),
            'Status': 'Healthy' if overall_health >= 60 else 'At Risk' if overall_health >= 40 else 'Critical'
        })

    return pd.DataFrame(health_data)


def get_segment_trends() -> Dict[str, any]:
    """Analyze trends within segments (if temporal data available)"""
    companies = load_company_data()
    assignments = load_cluster_assignments()

    if companies.empty or assignments.empty:
        return {}

    merged = companies.merge(assignments, on='company', how='left')

    # Calculate engagement trends based on available data
    trends = {}

    if 'recent_12m_revenue' in merged.columns and 'monetary_total' in merged.columns:
        # Recent revenue as percentage of total
        merged['recent_revenue_pct'] = merged['recent_12m_revenue'] / merged['monetary_total'].replace(0, 1) * 100

        trends['engagement'] = merged.groupby('ads_cluster')['recent_revenue_pct'].mean().to_dict()
        trends['engagement_interpretation'] = {
            seg_id: 'Growing' if pct > 30 else 'Stable' if pct > 10 else 'Declining'
            for seg_id, pct in trends['engagement'].items()
        }

    return trends


def get_top_companies_by_segment(segment_id: int, n: int = 10, sort_by: str = 'monetary_total') -> pd.DataFrame:
    """Get top N companies in a segment sorted by a specific metric"""
    companies = load_company_data()
    assignments = load_cluster_assignments()

    if companies.empty or assignments.empty:
        return pd.DataFrame()

    merged = companies.merge(assignments, on='company', how='left')
    segment_companies = merged[merged['ads_cluster'] == segment_id]

    if sort_by not in segment_companies.columns:
        sort_by = 'monetary_total' if 'monetary_total' in segment_companies.columns else segment_companies.columns[1]

    display_cols = ['company']
    potential_cols = ['monetary_total', 'frequency', 'recency_days', 'tenure_days', 'monetary_mean']
    display_cols.extend([c for c in potential_cols if c in segment_companies.columns])

    return segment_companies[display_cols].sort_values(sort_by, ascending=False).head(n)


def search_companies(query: str, segment_filter: int = None) -> pd.DataFrame:
    """Search for companies by name with optional segment filter"""
    companies = load_company_data()
    assignments = load_cluster_assignments()
    profiles = load_cluster_profiles()

    if companies.empty or assignments.empty:
        return pd.DataFrame()

    merged = companies.merge(assignments, on='company', how='left')

    # Apply search filter
    mask = merged['company'].str.contains(query, case=False, na=False)

    # Apply segment filter if specified
    if segment_filter is not None:
        mask = mask & (merged['ads_cluster'] == segment_filter)

    results = merged[mask].copy()

    # Add segment name
    results['segment_name'] = results['ads_cluster'].apply(
        lambda x: profiles.get(str(int(x)), {}).get('name', f'Segment {x}')
    )

    display_cols = ['company', 'segment_name']
    potential_cols = ['monetary_total', 'frequency', 'recency_days']
    display_cols.extend([c for c in potential_cols if c in results.columns])

    return results[display_cols].head(50)
