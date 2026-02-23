"""
Segment Overview Page
Interactive exploration of customer segments with visualizations
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

st.set_page_config(page_title="Segment Overview", page_icon="📊", layout="wide")

# Import services
from services.data_loader import (
    load_cluster_profiles, load_company_data, load_cluster_assignments
)
from services.segment_service import (
    get_segment_summary, get_segment_comparison, get_rfm_analysis,
    get_segment_health_scores
)

# Import centralized segment colors from data_loader (single source of truth)
from services.data_loader import SEGMENT_COLORS

def main():
    st.title("📊 Segment Overview")
    st.markdown("Explore customer segments, their characteristics, and key metrics.")

    # Load data
    profiles = load_cluster_profiles()
    companies = load_company_data()
    assignments = load_cluster_assignments()

    if companies.empty or assignments.empty:
        st.error("Data not loaded. Please check data files.")
        return

    merged = companies.merge(assignments, on='company', how='left')

    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Distribution", "🔍 Segment Deep Dive", "📊 Feature Comparison", "🎯 Health Scores"])

    with tab1:
        render_distribution_tab(merged, profiles)

    with tab2:
        render_segment_deep_dive(merged, profiles)

    with tab3:
        render_feature_comparison(merged, profiles)

    with tab4:
        render_health_scores()


def render_distribution_tab(merged: pd.DataFrame, profiles: dict):
    """Render segment distribution visualizations"""
    st.subheader("Segment Distribution")

    col1, col2 = st.columns([1, 1])

    with col1:
        # Pie chart
        segment_counts = merged['ads_cluster'].value_counts().reset_index()
        segment_counts.columns = ['Segment', 'Count']
        segment_counts['Name'] = segment_counts['Segment'].apply(
            lambda x: profiles.get(str(int(x)), {}).get('name', f'Segment {x}')
        )
        segment_counts['Color'] = segment_counts['Segment'].apply(
            lambda x: SEGMENT_COLORS.get(int(x), '#666')
        )

        fig_pie = px.pie(
            segment_counts,
            values='Count',
            names='Name',
            title='Customer Segment Distribution',
            color='Name',
            color_discrete_map={row['Name']: row['Color'] for _, row in segment_counts.iterrows()}
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        # Bar chart with counts
        fig_bar = px.bar(
            segment_counts,
            x='Name',
            y='Count',
            title='Companies per Segment',
            color='Name',
            color_discrete_map={row['Name']: row['Color'] for _, row in segment_counts.iterrows()}
        )
        fig_bar.update_layout(showlegend=False, xaxis_title="Segment", yaxis_title="Number of Companies")
        st.plotly_chart(fig_bar, use_container_width=True)

    # Summary table
    st.subheader("Segment Summary")
    summary = get_segment_summary()
    if not summary.empty:
        st.dataframe(
            summary.style.format({
                'Percentage': '{:.1f}%',
                'Avg Revenue': '£{:,.0f}',
                'Avg Frequency': '{:.1f}',
                'Avg Recency (days)': '{:.0f}'
            }),
            use_container_width=True,
            hide_index=True
        )


def render_segment_deep_dive(merged: pd.DataFrame, profiles: dict):
    """Render detailed view of a selected segment"""
    st.subheader("Segment Deep Dive")

    # Segment selector
    segment_options = {
        profiles.get(str(i), {}).get('name', f'Segment {i}'): i
        for i in sorted(merged['ads_cluster'].unique())
    }

    selected_name = st.selectbox("Select Segment", list(segment_options.keys()))
    selected_id = segment_options[selected_name]

    profile = profiles.get(str(selected_id), {})
    segment_data = merged[merged['ads_cluster'] == selected_id]

    # Profile card
    col1, col2 = st.columns([1, 2])

    with col1:
        color = SEGMENT_COLORS.get(selected_id, '#666')
        st.markdown(f"""
        <div style="border-left: 5px solid {color}; padding: 1rem; background: #f8f9fa; border-radius: 5px;">
            <h3 style="color: {color}; margin-top: 0;">{profile.get('name', 'Unknown')}</h3>
            <p><strong>Risk Level:</strong> {profile.get('risk_level', 'N/A')}</p>
            <p><strong>Companies:</strong> {len(segment_data):,}</p>
            <p>{profile.get('description', 'No description available.')}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("**Characteristics:**")
        characteristics = profile.get('characteristics', {})
        for key, value in characteristics.items():
            st.markdown(f"- **{key.replace('_', ' ').title()}**: {value}")

    with col2:
        # Radar chart of key metrics
        features = ['frequency', 'monetary_total', 'monetary_mean', 'recency_days', 'tenure_days']
        available_features = [f for f in features if f in segment_data.columns]

        if available_features:
            # Normalize values for radar chart
            radar_data = []
            for feature in available_features:
                seg_mean = segment_data[feature].mean()
                overall_mean = merged[feature].mean()
                normalized = (seg_mean / overall_mean) if overall_mean != 0 else 0
                radar_data.append(min(2, max(0, normalized)))  # Cap between 0 and 2

            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=radar_data + [radar_data[0]],  # Close the loop
                theta=[f.replace('_', ' ').title() for f in available_features] + [available_features[0].replace('_', ' ').title()],
                fill='toself',
                name=selected_name,
                line_color=color,
                fillcolor=f"rgba{tuple(list(int(color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + [0.3])}"
            ))

            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 2])),
                title=f"Feature Profile (vs. Overall Average)",
                showlegend=False
            )
            st.plotly_chart(fig_radar, use_container_width=True)

    # Distribution plots for this segment
    st.markdown("---")
    st.markdown("**Key Metric Distributions**")

    metric_cols = ['monetary_total', 'frequency', 'recency_days', 'tenure_days']
    available_metrics = [m for m in metric_cols if m in segment_data.columns]

    if available_metrics:
        fig = make_subplots(rows=1, cols=len(available_metrics),
                           subplot_titles=[m.replace('_', ' ').title() for m in available_metrics])

        for i, metric in enumerate(available_metrics, 1):
            fig.add_trace(
                go.Histogram(x=segment_data[metric], name=metric, marker_color=color, opacity=0.7),
                row=1, col=i
            )

        fig.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # Recommended actions
    st.markdown("---")
    st.markdown("**Recommended Actions**")
    actions = profile.get('recommended_actions', [])
    for i, action in enumerate(actions, 1):
        st.markdown(f"{i}. {action}")


def render_feature_comparison(merged: pd.DataFrame, profiles: dict):
    """Render feature comparison across segments"""
    st.subheader("Feature Comparison Across Segments")

    # Feature selector
    numeric_cols = merged.select_dtypes(include=[np.number]).columns.tolist()
    exclude_cols = ['ads_cluster', 'Unnamed: 0']
    feature_options = [c for c in numeric_cols if c not in exclude_cols]

    selected_feature = st.selectbox(
        "Select Feature to Compare",
        feature_options,
        index=feature_options.index('monetary_total') if 'monetary_total' in feature_options else 0
    )

    # Box plot comparison
    merged['Segment Name'] = merged['ads_cluster'].apply(
        lambda x: profiles.get(str(int(x)), {}).get('name', f'Segment {x}')
    )

    fig_box = px.box(
        merged,
        x='Segment Name',
        y=selected_feature,
        color='Segment Name',
        title=f'{selected_feature.replace("_", " ").title()} by Segment',
        color_discrete_map={
            profiles.get(str(i), {}).get('name', f'Segment {i}'): SEGMENT_COLORS.get(i, '#666')
            for i in range(5)
        }
    )
    fig_box.update_layout(showlegend=False)
    st.plotly_chart(fig_box, use_container_width=True)

    # Comparison table
    comparison = get_segment_comparison(selected_feature)
    if not comparison.empty:
        st.dataframe(comparison, use_container_width=True, hide_index=True)


def render_health_scores():
    """Render segment health score dashboard"""
    st.subheader("Segment Health Scores")

    health_df = get_segment_health_scores()

    if health_df.empty:
        st.warning("Could not calculate health scores.")
        return

    # Health score cards
    cols = st.columns(len(health_df))
    for col, (_, row) in zip(cols, health_df.iterrows()):
        with col:
            score = row['Overall Health']
            status = row['Status']
            color = '#2E7D32' if status == 'Healthy' else '#F57C00' if status == 'At Risk' else '#C62828'

            st.markdown(f"""
            <div style="text-align: center; padding: 1rem; border-radius: 10px; background: #f8f9fa;">
                <h4>{row['Segment'][:15]}...</h4>
                <div style="font-size: 2.5rem; font-weight: bold; color: {color};">{score:.0f}</div>
                <div style="color: {color}; font-weight: bold;">{status}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # Detailed breakdown
    st.markdown("**Score Breakdown**")

    fig = go.Figure()

    categories = ['Recency Score', 'Frequency Score', 'Monetary Score']
    for _, row in health_df.iterrows():
        fig.add_trace(go.Bar(
            name=row['Segment'],
            x=categories,
            y=[row['Recency Score'], row['Frequency Score'], row['Monetary Score']]
        ))

    fig.update_layout(
        barmode='group',
        title='Health Score Components by Segment',
        yaxis_title='Score (0-100)'
    )
    st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
