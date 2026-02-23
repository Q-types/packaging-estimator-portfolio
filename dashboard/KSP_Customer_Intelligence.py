"""
KSP Customer Intelligence Command Center
Unified dashboard combining customer analytics, prospect pipeline, and revenue opportunities
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file (local development)
# For Streamlit Cloud, use secrets.toml instead
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    # Try parent directory as fallback
    env_path_parent = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(env_path_parent)

import streamlit as st

# Page configuration - MUST be first Streamlit command
st.set_page_config(
    page_title="KSP Intelligence Center",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from services.unified_data_service import (
    get_daily_priorities,
    get_segment_summary,
    get_prospect_pipeline,
    load_segment_profiles,
    get_data_snapshot_info
)

# =============================================================================
# CUSTOM STYLING
# =============================================================================

st.markdown("""
<style>
    /* Main header styling */
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        color: #1E3A5F;
        margin-bottom: 0.25rem;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        margin-bottom: 1.5rem;
    }

    /* Priority cards */
    .priority-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.25rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .priority-card h3 {
        font-size: 2rem;
        margin: 0;
        font-weight: 700;
    }
    .priority-card p {
        margin: 0.25rem 0 0 0;
        opacity: 0.9;
        font-size: 0.85rem;
    }

    /* Alert cards */
    .alert-card {
        border-left: 4px solid #C62828;
        background: #FFF5F5;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 0.75rem;
        color: #1a1a1a !important;
    }
    .alert-card strong {
        color: #000000 !important;
        font-size: 1rem;
    }
    .alert-card small {
        color: #333333 !important;
        line-height: 1.4;
    }
    .alert-card.warning {
        border-left-color: #F57C00;
        background: #FFF8E1;
    }
    .alert-card.success {
        border-left-color: #2E7D32;
        background: #E8F5E9;
    }

    /* Action button styling */
    .action-row {
        display: flex;
        gap: 0.5rem;
        margin-top: 0.5rem;
    }

    /* Segment pills */
    .segment-pill {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        color: white;
    }

    /* Table styling */
    .dataframe {
        font-size: 0.9rem;
    }

    /* Navigation tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SIDEBAR NAVIGATION
# =============================================================================

with st.sidebar:
    st.markdown("## 📦 KSP Intelligence")
    st.markdown("---")

    page = st.radio(
        "Select View",
        ["🎯 Action Center", "💰 Revenue Opportunities", "🔍 Prospect Pipeline", "📊 Customer Explorer", "🔎 Company Search", "📧 Marketing Playbook"],
        label_visibility="collapsed"
    )

    st.markdown("---")

    # Quick stats
    priorities = get_daily_priorities()
    metrics = priorities.get('metrics', {})

    st.markdown("### Quick Stats")
    st.metric("Active Customers", f"{metrics.get('active_customers', 0):,}")
    st.metric("Win-Back Targets", f"{metrics.get('winback_candidates', 0):,}")
    st.metric("Hot Prospects", f"{metrics.get('hot_prospects_count', 0):,}")

    st.markdown("---")

    # Data freshness warning
    snapshot = get_data_snapshot_info()
    st.warning(f"📅 **Data: {snapshot['date_str']}**")
    st.caption("Recency metrics are relative to this snapshot date, not today.")

    st.markdown("---")
    st.markdown("### 🔬 Analysis Tools")
    st.caption("Use the page selector above for detailed analysis:")
    st.markdown("""
    - **Segment Overview** - Charts & visualizations
    - **Company Explorer** - Deep company profiles
    - **Segment Predictor** - Predict new customer segments
    - **Marketing Playbook** - Original strategies
    """)


# =============================================================================
# ACTION CENTER PAGE
# =============================================================================

def render_action_center():
    """Render the Action-First Sales Command Center"""
    st.markdown('<p class="main-header">🎯 Action Center</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Your daily priority queue - what needs attention today</p>', unsafe_allow_html=True)

    # Data freshness notice
    snapshot = get_data_snapshot_info()
    st.info(f"📅 **Data Snapshot: {snapshot['date_str']}** — 'Days since last order' and activity metrics are relative to this date.")

    priorities = get_daily_priorities()
    metrics = priorities.get('metrics', {})

    # Priority metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div class="priority-card" style="background: linear-gradient(135deg, #2E7D32 0%, #1B5E20 100%);">
            <h3>{metrics.get('high_value_count', 0)}</h3>
            <p>⭐ High-Value Regulars</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="priority-card" style="background: linear-gradient(135deg, #1976D2 0%, #0D47A1 100%);">
            <h3>{metrics.get('growth_potential_count', 0)}</h3>
            <p>📈 Growth Potential</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="priority-card" style="background: linear-gradient(135deg, #C62828 0%, #B71C1C 100%);">
            <h3>{metrics.get('winback_candidates', 0)}</h3>
            <p>🔴 Win-Back Priority</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="priority-card" style="background: linear-gradient(135deg, #7B1FA2 0%, #6A1B9A 100%);">
            <h3>{metrics.get('hot_prospects_count', 0)}</h3>
            <p>🔥 Hot Prospects</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Three columns for priority lists
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 🔴 Win-Back Priority")
        st.caption("Lapsed Regulars & High-Value Dormant - best recovery ROI")

        at_risk = priorities.get('at_risk', [])
        profiles = load_segment_profiles()
        if at_risk:
            for customer in at_risk[:5]:
                days_ago = customer.get('recency_days', 0)
                years_ago = days_ago / 365
                seg_id = customer.get('ads_cluster', 0)
                seg_name = profiles.get(int(seg_id), {}).get('name', 'Unknown')
                with st.container():
                    st.markdown(f"""
                    <div class="alert-card warning">
                        <strong>{customer['company']}</strong><br/>
                        <small>
                            {seg_name}<br/>
                            Lifetime: £{customer['monetary_total']:,.0f} | {customer['frequency']:.0f} orders<br/>
                            Last order: {years_ago:.1f} years ago
                        </small>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No win-back candidates identified")

    with col2:
        st.markdown("### 🔥 Hot Prospects")
        st.caption("Ready for outreach")

        hot_prospects = priorities.get('hot_prospects', [])
        if hot_prospects:
            for prospect in hot_prospects[:5]:
                with st.container():
                    st.markdown(f"""
                    <div class="alert-card success">
                        <strong>{prospect['company_name']}</strong><br/>
                        <small>
                            Score: {prospect['prospect_score']:.0f} |
                            {prospect['industry_sector']}<br/>
                            {prospect['region']} | Packaging: {prospect['packaging_need']}
                        </small>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No hot prospects available")

    with col3:
        st.markdown("### 📈 Expansion Opportunities")
        st.caption("Customers with growth potential")

        expansion = priorities.get('expansion', [])
        if expansion:
            for customer in expansion[:5]:
                profiles = load_segment_profiles()
                seg_name = profiles.get(customer['ads_cluster'], {}).get('name', 'Unknown')
                st.markdown(f"""
                <div class="alert-card warning">
                    <strong>{customer['company']}</strong><br/>
                    <small>
                        {seg_name}<br/>
                        Current: £{customer['monetary_total']:,.0f} |
                        Potential: +£{customer['expansion_potential']:,.0f}
                    </small>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No expansion opportunities identified")


# =============================================================================
# REVENUE OPPORTUNITIES PAGE
# =============================================================================

def render_revenue_opportunities():
    """Render the Revenue Opportunities view"""
    from services.unified_data_service import (
        get_revenue_leakage, get_expansion_opportunities, get_market_gaps
    )

    st.markdown('<p class="main-header">💰 Revenue Opportunities</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Identify and capture revenue - prevent leakage, expand accounts, enter new markets</p>', unsafe_allow_html=True)

    # Summary metrics
    leakage_df = get_revenue_leakage()
    expansion_df = get_expansion_opportunities()

    total_at_risk = leakage_df['revenue_at_stake'].sum() if not leakage_df.empty else 0
    total_expansion = expansion_df['potential_uplift'].sum() if not expansion_df.empty else 0

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Revenue at Risk", f"£{total_at_risk:,.0f}", delta="-requires action", delta_color="inverse")
    with col2:
        st.metric("Expansion Potential", f"£{total_expansion:,.0f}", delta="+opportunity")
    with col3:
        st.metric("Total Opportunity", f"£{total_at_risk + total_expansion:,.0f}")

    st.markdown("---")

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["💸 Revenue Leakage", "📈 Expansion Opportunities", "🗺️ Market Gaps"])

    with tab1:
        st.markdown("### Customers at Risk of Churning")
        st.caption("Prioritized by revenue at stake - take action to retain")

        if not leakage_df.empty:
            # Summary chart
            fig = px.bar(
                leakage_df.head(10),
                x='company',
                y='revenue_at_stake',
                color='churn_risk',
                color_continuous_scale='Reds',
                title='Top 10 Accounts by Revenue at Risk'
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

            # Detailed table
            st.dataframe(
                leakage_df.head(20).style.format({
                    'monetary_total': '£{:,.0f}',
                    'revenue_at_stake': '£{:,.0f}',
                    'churn_risk': '{:.0f}%',
                    'recency_days': '{:.0f} days'
                }).background_gradient(subset=['churn_risk'], cmap='Reds'),
                use_container_width=True,
                hide_index=True
            )

            # Export button
            csv = leakage_df.to_csv(index=False)
            st.download_button(
                "📥 Export At-Risk List",
                csv,
                "at_risk_customers.csv",
                "text/csv"
            )
        else:
            st.info("No significant revenue leakage identified")

    with tab2:
        st.markdown("### Accounts with Growth Potential")
        st.caption("Customers performing below their segment average - opportunity to expand")

        if not expansion_df.empty:
            # Chart
            fig = px.bar(
                expansion_df.head(10),
                x='company',
                y=['current_revenue', 'potential_uplift'],
                title='Top 10 Expansion Opportunities',
                barmode='stack',
                color_discrete_map={'current_revenue': '#1976D2', 'potential_uplift': '#4CAF50'}
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

            # Table
            st.dataframe(
                expansion_df.style.format({
                    'current_revenue': '£{:,.0f}',
                    'segment_avg': '£{:,.0f}',
                    'potential_uplift': '£{:,.0f}'
                }),
                use_container_width=True,
                hide_index=True
            )

            csv = expansion_df.to_csv(index=False)
            st.download_button(
                "📥 Export Expansion List",
                csv,
                "expansion_opportunities.csv",
                "text/csv"
            )
        else:
            st.info("No significant expansion opportunities identified")

    with tab3:
        st.markdown("### Underserved Markets")
        st.caption("Industries and regions with high potential where you're underrepresented")

        gaps_df = get_market_gaps()
        if not gaps_df.empty:
            fig = px.scatter(
                gaps_df,
                x='prospect_count',
                y='avg_score',
                size='high_need_count',
                color='opportunity_score',
                hover_name='industry',
                title='Market Opportunity Analysis',
                labels={
                    'prospect_count': 'Number of Prospects',
                    'avg_score': 'Average ICP Score',
                    'opportunity_score': 'Opportunity'
                }
            )
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(gaps_df, use_container_width=True, hide_index=True)
        else:
            st.info("Unable to analyze market gaps - check prospect data")


# =============================================================================
# PROSPECT PIPELINE PAGE
# =============================================================================

def render_prospect_pipeline():
    """Render the Prospect Pipeline view"""
    from services.unified_data_service import get_best_fit_prospects, load_prospect_data

    st.markdown('<p class="main-header">🔍 Prospect Pipeline</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Manage your prospect funnel - prioritize high-fit opportunities</p>', unsafe_allow_html=True)

    pipeline = get_prospect_pipeline()
    funnel = pipeline.get('funnel', {})
    prospects_df = pipeline.get('prospects', pd.DataFrame())

    # Funnel visualization
    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("### Prospect Funnel")

        tier_colors = {'Hot': '#C62828', 'Warm': '#F57C00', 'Cool': '#1976D2', 'Cold': '#9E9E9E'}

        for tier in ['Hot', 'Warm', 'Cool', 'Cold']:
            data = funnel.get(tier, {'count': 0, 'avg_score': 0})
            color = tier_colors.get(tier, '#666')
            st.markdown(f"""
            <div style="background: {color}; color: white; padding: 1rem; border-radius: 8px; margin-bottom: 0.5rem; text-align: center;">
                <div style="font-size: 1.5rem; font-weight: bold;">{data['count']}</div>
                <div>{tier} Prospects</div>
                <small>Avg Score: {data['avg_score']:.0f}</small>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        # Industry breakdown
        by_industry = pipeline.get('by_industry', [])
        if by_industry:
            industry_df = pd.DataFrame(by_industry)
            fig = px.bar(
                industry_df.nlargest(10, 'count'),
                x='industry',
                y='count',
                color='avg_score',
                color_continuous_scale='Greens',
                title='Prospects by Industry'
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Tabs for different views
    tab1, tab2 = st.tabs(["⭐ Best-Fit Prospects", "📋 Full Pipeline"])

    with tab1:
        st.markdown("### Best-Fit Prospects")
        st.caption("High packaging need + high ICP score = best opportunities")

        best_fit = get_best_fit_prospects(20)
        if not best_fit.empty:
            # Rename columns for clarity
            display_df = best_fit.rename(columns={
                'company_name': 'Company',
                'industry_sector': 'Industry',
                'region': 'Region',
                'prospect_score': 'ICP Score',
                'priority_tier': 'Tier',
                'packaging_need': 'Pkg Need',
                'industry_score': 'Ind.',
                'age_score': 'Age',
                'size_score': 'Size'
            })

            st.dataframe(
                display_df.style.format({
                    'ICP Score': '{:.0f}',
                    'Ind.': '{:.0f}',
                    'Age': '{:.0f}',
                    'Size': '{:.0f}'
                }).background_gradient(subset=['ICP Score'], cmap='Greens'),
                use_container_width=True,
                hide_index=True
            )

            # Score explanation
            with st.expander("Score Breakdown Explained"):
                st.markdown("""
                - **ICP Score**: Overall fit (0-100) combining all factors
                - **Ind.**: Industry match to KSP's ideal sectors (packaging-intensive)
                - **Age**: Company maturity (7-29 years optimal)
                - **Size**: Business size indicators (officers, filings)
                - **Pkg Need**: HIGH = manufacturing/retail, MEDIUM = services, LOW = other
                """)

            csv = best_fit.to_csv(index=False)
            st.download_button(
                "📥 Export Best-Fit List",
                csv,
                "best_fit_prospects.csv",
                "text/csv"
            )
        else:
            st.info("No best-fit prospects identified")

    with tab2:
        st.markdown("### Full Prospect Pipeline")
        prospect_count = len(prospects_df) if not prospects_df.empty else 0
        st.caption(f"Filter and search all {prospect_count:,} pre-scored prospects")

        # Filters in 4 columns
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            tier_filter = st.multiselect("Tier", ['Hot', 'Warm', 'Cool', 'Cold'], default=['Hot', 'Warm'])
        with col2:
            need_filter = st.multiselect("Packaging Need", ['HIGH', 'MEDIUM', 'LOW'], default=['HIGH', 'MEDIUM'])
        with col3:
            # Get unique industries
            if not prospects_df.empty:
                industries = ['All'] + sorted(prospects_df['industry_sector'].dropna().unique().tolist())
                industry_filter = st.selectbox("Industry", industries)
            else:
                industry_filter = 'All'
        with col4:
            min_score = st.slider("Min ICP Score", 0, 100, 50)

        # Search box
        search_term = st.text_input("Search company name", placeholder="Type to search...")

        if not prospects_df.empty:
            filtered = prospects_df.copy()

            if tier_filter:
                filtered = filtered[filtered['priority_tier'].isin(tier_filter)]
            if need_filter:
                filtered = filtered[filtered['packaging_need'].isin(need_filter)]
            if industry_filter != 'All':
                filtered = filtered[filtered['industry_sector'] == industry_filter]
            if search_term:
                filtered = filtered[filtered['company_name'].str.contains(search_term, case=False, na=False)]
            filtered = filtered[filtered['prospect_score'] >= min_score]

            # Display with more score columns
            display_cols = ['company_name', 'industry_sector', 'region', 'prospect_score',
                          'priority_tier', 'packaging_need', 'industry_score', 'geo_score', 'web_score']
            available_cols = [c for c in display_cols if c in filtered.columns]

            st.dataframe(
                filtered[available_cols].sort_values('prospect_score', ascending=False).head(100).style.format({
                    'prospect_score': '{:.0f}',
                    'industry_score': '{:.0f}',
                    'geo_score': '{:.0f}',
                    'web_score': '{:.0f}'
                }),
                use_container_width=True,
                hide_index=True
            )

            st.caption(f"Showing {min(len(filtered), 100)} of {len(filtered)} matches ({len(prospects_df)} total)")

            # Export filtered results
            if len(filtered) > 0:
                csv = filtered.to_csv(index=False)
                st.download_button(
                    "📥 Export Filtered List",
                    csv,
                    "filtered_prospects.csv",
                    "text/csv"
                )


# =============================================================================
# CUSTOMER EXPLORER PAGE
# =============================================================================

def render_customer_explorer():
    """Render the Customer Explorer view"""
    from services.unified_data_service import (
        search_customers, get_customer_360, get_segment_summary, load_segment_profiles
    )

    st.markdown('<p class="main-header">📊 Customer Explorer</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Deep dive into customer segments and individual profiles</p>', unsafe_allow_html=True)

    # Data freshness notice
    snapshot = get_data_snapshot_info()
    st.info(f"📅 **Data Snapshot: {snapshot['date_str']}** — All recency and activity metrics are relative to this date, not today.")

    # Segment summary
    summary_df = get_segment_summary()
    profiles = load_segment_profiles()

    if not summary_df.empty:
        st.markdown("### All 8 Segments Overview")

        # Show segments in 2 rows of 4
        # Row 1: Dormant segments (0-3)
        st.markdown("**Dormant Segments** (Win-back & Re-engagement)")
        cols1 = st.columns(4)
        dormant_segments = summary_df[summary_df['segment_id'].isin([0, 1, 2, 3, 4])].head(4)
        for col, (_, row) in zip(cols1, dormant_segments.iterrows()):
            with col:
                color = row['color']
                st.markdown(f"""
                <div style="border-left: 4px solid {color}; padding: 0.75rem; background: white; border-radius: 4px; margin-bottom: 0.5rem;">
                    <div style="font-size: 0.85rem; color: {color}; font-weight: bold;">{row['icon']} {row['name']}</div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: #1a1a1a;">{row['count']}</div>
                    <div style="font-size: 0.7rem; color: #555;">{row['pct']:.1f}% | £{row['total_revenue']:,.0f}</div>
                    <div style="font-size: 0.65rem; color: #888; margin-top: 0.25rem;">{row['risk_level']}</div>
                </div>
                """, unsafe_allow_html=True)

        # Row 2: Active segments (4-7)
        st.markdown("**Active Segments** (Protect & Grow)")
        cols2 = st.columns(4)
        active_segments = summary_df[summary_df['segment_id'].isin([4, 5, 6, 7])].tail(4)
        for col, (_, row) in zip(cols2, active_segments.iterrows()):
            with col:
                color = row['color']
                st.markdown(f"""
                <div style="border-left: 4px solid {color}; padding: 0.75rem; background: white; border-radius: 4px; margin-bottom: 0.5rem;">
                    <div style="font-size: 0.85rem; color: {color}; font-weight: bold;">{row['icon']} {row['name']}</div>
                    <div style="font-size: 1.5rem; font-weight: bold; color: #1a1a1a;">{row['count']}</div>
                    <div style="font-size: 0.7rem; color: #555;">{row['pct']:.1f}% | £{row['total_revenue']:,.0f}</div>
                    <div style="font-size: 0.65rem; color: #888; margin-top: 0.25rem;">{row['risk_level']}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")

        # Segment comparison chart
        fig = px.bar(
            summary_df,
            x='name',
            y='total_revenue',
            color='name',
            color_discrete_map={row['name']: row['color'] for _, row in summary_df.iterrows()},
            title='Revenue by Segment'
        )
        fig.update_layout(showlegend=False, xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Search and filter
    st.markdown("### Find Customers")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search_query = st.text_input("Search by company name", placeholder="Enter company name...")
    with col2:
        segment_options = {f"{row['icon']} {row['name']}": row['segment_id'] for _, row in summary_df.iterrows()}
        segment_options = {"All Segments": None} | segment_options
        selected_segment = st.selectbox("Filter by Segment", list(segment_options.keys()))
        segment_filter = segment_options[selected_segment]
    with col3:
        sort_options = {'Revenue (High)': 'monetary_total', 'Frequency': 'frequency', 'Recency': 'recency_days', 'Risk': 'churn_risk'}
        sort_by = st.selectbox("Sort by", list(sort_options.keys()))

    # Search results
    results = search_customers(search_query, segment_filter, sort_options[sort_by])

    if not results.empty:
        st.dataframe(
            results.style.format({
                'monetary_total': '£{:,.0f}',
                'churn_risk': '{:.0f}%'
            }),
            use_container_width=True,
            hide_index=True
        )

        # Customer detail view
        st.markdown("---")
        st.markdown("### Customer 360 View")

        company_list = results['company'].tolist()
        selected_company = st.selectbox("Select customer for details", company_list)

        if selected_company:
            profile = get_customer_360(selected_company)

            if profile:
                col1, col2 = st.columns([1, 2])

                with col1:
                    color = profile['segment_color']
                    st.markdown(f"""
                    <div style="border: 2px solid {color}; border-radius: 12px; padding: 1.5rem; background: white;">
                        <h3 style="color: {color}; margin-top: 0;">{profile['company']}</h3>
                        <span class="segment-pill" style="background: {color};">{profile['segment_name']}</span>
                        <p style="margin-top: 1rem; color: #1a1a1a;"><strong>Risk Level:</strong> {profile['risk_level']}</p>
                        <hr style="border-color: #ddd;"/>
                        <p style="color: #1a1a1a;"><strong>Lifetime Value:</strong> £{profile['lifetime_value']:,.0f}</p>
                        <p style="color: #1a1a1a;"><strong>Churn Risk:</strong> {profile['churn_risk']:.0f}%</p>
                        <p style="color: #1a1a1a;"><strong>Revenue at Stake:</strong> £{profile['revenue_at_stake']:,.0f}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown("**Recommended Actions:**")
                    for action in profile['recommended_actions']:
                        st.markdown(f"- {action}")

                with col2:
                    # Metrics
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Total Revenue", f"£{profile['total_revenue']:,.0f}")
                    m2.metric("Orders", f"{profile['order_count']:.0f}")
                    m3.metric("Avg Order", f"£{profile['avg_order_value']:,.0f}")
                    m4.metric("Last Order", f"{profile['recency_days']:.0f} days ago")

                    # Engagement chart
                    engagement_data = {
                        'Metric': ['Recency', 'Frequency', 'Monetary', 'Tenure'],
                        'Value': [
                            max(0, 100 - profile['recency_days'] / 3.65),  # Scale to 0-100
                            min(100, profile['order_count'] * 5),
                            min(100, profile['total_revenue'] / 500),
                            min(100, profile['tenure_days'] / 10)
                        ]
                    }
                    fig = px.bar(
                        engagement_data,
                        x='Metric',
                        y='Value',
                        title='Engagement Scores',
                        color='Value',
                        color_continuous_scale='Blues'
                    )
                    fig.update_layout(showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No customers found. Try adjusting your search criteria.")


# =============================================================================
# COMPANY SEARCH PAGE (Companies House)
# =============================================================================

def render_company_search():
    """Render the Companies House search page"""
    import requests
    import os

    st.markdown('<p class="main-header">🔎 Company Search</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Search Companies House to find and score new prospects</p>', unsafe_allow_html=True)

    # Check for API key - try Streamlit secrets first, then environment variable
    api_key = ''
    try:
        api_key = st.secrets.get('COMPANIES_HOUSE_API_KEY', '')
    except Exception:
        pass
    if not api_key:
        api_key = os.environ.get('COMPANIES_HOUSE_API_KEY', '')

    if not api_key:
        st.warning("""
        **Companies House API Key Required**

        To search Companies House, you need an API key:
        1. Register at [Companies House Developer Hub](https://developer.company-information.service.gov.uk/)
        2. Create an application and get your API key
        3. Add to Streamlit secrets or set environment variable

        For now, you can search the existing prospect database below.
        """)

    st.markdown("---")

    # Search interface
    col1, col2 = st.columns([3, 1])
    with col1:
        search_term = st.text_input("Search company name", placeholder="e.g., Acme Packaging Ltd")
    with col2:
        search_type = st.selectbox("Search in", ["Existing Prospects", "Companies House (API)"])

    if search_term:
        if search_type == "Existing Prospects":
            # Search in existing prospect data
            from services.unified_data_service import load_prospect_data
            prospects = load_prospect_data()

            if not prospects.empty:
                matches = prospects[
                    prospects['company_name'].str.contains(search_term, case=False, na=False)
                ].head(20)

                if not matches.empty:
                    st.success(f"Found {len(matches)} matches in existing prospects")

                    st.dataframe(
                        matches[['company_name', 'industry_sector', 'region', 'prospect_score',
                                'priority_tier', 'packaging_need']].style.format({
                            'prospect_score': '{:.0f}'
                        }),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("No matches in existing prospect database. Try Companies House search.")
            else:
                st.error("Could not load prospect data")

        elif search_type == "Companies House (API)" and api_key:
            # Live Companies House search
            with st.spinner("Searching Companies House..."):
                try:
                    response = requests.get(
                        f"https://api.company-information.service.gov.uk/search/companies",
                        params={"q": search_term, "items_per_page": 20},
                        auth=(api_key, ''),
                        timeout=10
                    )

                    if response.status_code == 200:
                        data = response.json()
                        items = data.get('items', [])

                        if items:
                            st.success(f"Found {data.get('total_results', len(items))} companies")

                            # Display results
                            for item in items:
                                with st.expander(f"**{item.get('title', 'Unknown')}** - {item.get('company_number', '')}"):
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.write(f"**Status:** {item.get('company_status', 'Unknown')}")
                                        st.write(f"**Type:** {item.get('company_type', 'Unknown')}")
                                        st.write(f"**Created:** {item.get('date_of_creation', 'Unknown')}")

                                    with col2:
                                        address = item.get('address', {})
                                        addr_parts = [
                                            address.get('address_line_1', ''),
                                            address.get('locality', ''),
                                            address.get('region', ''),
                                            address.get('postal_code', '')
                                        ]
                                        st.write(f"**Address:** {', '.join(p for p in addr_parts if p)}")

                                        sic_codes = item.get('sic_codes', [])
                                        if sic_codes:
                                            st.write(f"**SIC Codes:** {', '.join(sic_codes)}")

                                    # Score button (placeholder)
                                    if st.button(f"Add to Prospects", key=f"add_{item.get('company_number')}"):
                                        st.info("To add and score prospects, run the backend API service.")
                        else:
                            st.warning("No companies found matching your search")
                    elif response.status_code == 401:
                        st.error("Invalid API key. Please check your COMPANIES_HOUSE_API_KEY.")
                    else:
                        st.error(f"API error: {response.status_code}")

                except requests.exceptions.Timeout:
                    st.error("Request timed out. Please try again.")
                except Exception as e:
                    st.error(f"Search failed: {str(e)}")

        elif search_type == "Companies House (API)" and not api_key:
            st.error("Please set COMPANIES_HOUSE_API_KEY environment variable to use Companies House search.")

    # Industry filter for existing prospects
    st.markdown("---")
    st.markdown("### Browse by Industry")

    from services.unified_data_service import load_prospect_data
    prospects = load_prospect_data()

    if not prospects.empty:
        industries = sorted(prospects['industry_sector'].dropna().unique().tolist())
        selected_industry = st.selectbox("Select industry to browse", ["Select..."] + industries)

        if selected_industry != "Select...":
            industry_prospects = prospects[prospects['industry_sector'] == selected_industry]
            industry_prospects = industry_prospects.sort_values('prospect_score', ascending=False)

            st.write(f"**{len(industry_prospects)} prospects** in {selected_industry}")

            st.dataframe(
                industry_prospects[['company_name', 'region', 'prospect_score', 'priority_tier',
                                   'packaging_need', 'company_age_years']].head(50).style.format({
                    'prospect_score': '{:.0f}',
                    'company_age_years': '{:.1f} yrs'
                }),
                use_container_width=True,
                hide_index=True
            )


# =============================================================================
# MARKETING PLAYBOOK PAGE
# =============================================================================

def render_marketing_playbook():
    """Render the Marketing Playbook with segment-specific strategies and email templates"""

    st.markdown('<p class="main-header">📧 Marketing Playbook</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Segment-specific marketing strategies and ready-to-use email templates</p>', unsafe_allow_html=True)

    # Marketing Agent Definitions - segment-specific motions based on cluster analysis
    # Key insight: Don't lump segments together - each has distinct behavior patterns
    MARKETING_AGENTS = {
        0: {
            "name": "Early-Churn Friction Remover",
            "persona": "Onboarding specialist focused on identifying and removing friction points",
            "strategy": "These customers had a short tenure (~59 days) but HIGH activity burst (8.5 days between orders, 20.6 estimates/year) then churned. This indicates ONBOARDING FRICTION - spec complexity, lead times, MOQ, or quality issues. Automated nurture with friction-removal CTA. Only escalate top-value subset.",
            "timing": "Automated flow + escalate top 10% by value",
            "channel": "Email automation with friction survey; phone only for top-value",
            "tone": "Helpful, solution-focused, acknowledge past experience",
            "kpi": "Friction point identification rate; Top-value re-engagement > 10%",
            "action_label": "Early-Churn Burst"
        },
        1: {
            "name": "Lapsed Regular Diagnostician",
            "persona": "Relationship investigator focused on understanding WHY loyal customers left",
            "strategy": "HIGH PRIORITY. These were regular customers who stopped. DIAGNOSIS FIRST - avoid discount-first default. Personal outreach to understand why they left. Was it service? Quality? Pricing? Competition? Tailored win-back based on their specific issue.",
            "timing": "Personal outreach within 1 week",
            "channel": "Phone call first (diagnosis), then tailored follow-up",
            "tone": "Curious, empathetic, no assumptions",
            "kpi": "Diagnosis completion rate > 60%; Win-back rate > 15%",
            "action_label": "Lapsed Regular"
        },
        2: {
            "name": "High-Cadence Win-back Specialist",
            "persona": "Win-back specialist for historically high-cadence customers now lapsed",
            "strategy": "HIGH PRIORITY. Highest historical activity (18.7 orders/year median) - these customers were highly engaged before going dormant (84% now inactive). Worth win-back effort: fast re-quote, barrier removal, review historical patterns for personalization.",
            "timing": "Proactive outreach within 1 week of identification",
            "channel": "Phone + fast email re-quote",
            "tone": "Efficient, barrier-removing, 'let's make this easy'",
            "kpi": "Win-back rate > 15%; Re-quote response > 25%",
            "action_label": "High-Cadence Lapsed"
        },
        3: {
            "name": "Project Re-quote Manager",
            "persona": "Project-cycle relationship manager for infrequent high-AOV buyers",
            "strategy": "Higher AOV (£6,826) with infrequent, project-based ordering. Semi-personal outreach - maintain awareness for when projects arise. Case studies, capability updates, quick response when they're ready.",
            "timing": "Quarterly semi-personal touchpoints",
            "channel": "Email with phone follow-up for engaged prospects",
            "tone": "Consultative, project-aware, ready to respond fast",
            "kpi": "Project inquiry rate > 15%; Response time when contacted < 4hrs",
            "action_label": "Project Re-quote"
        },
        4: {
            "name": "VIP Executive Recovery Director",
            "persona": "C-level relationship manager for highest-value at-risk accounts",
            "strategy": "CRITICAL - £91,587 avg revenue, £10.7M total opportunity. TIERED EXECUTIVE WIN-BACK with reason-coded churn. Offer ladder: 1) Service fix first, 2) Commercial terms, 3) Incentive last. Senior leadership involvement required.",
            "timing": "URGENT - Executive contact within 48 hours",
            "channel": "Senior/executive phone call → face-to-face meeting → account review",
            "tone": "Executive-to-executive, partnership restoration, premium service",
            "kpi": "Recovery rate > 30%; Revenue recovered £ tracking; Churn reason coded",
            "action_label": "Win-back VIP"
        },
        5: {
            "name": "Long-Tenure Relationship Director",
            "persona": "Key account manager for long-tenure relationship-heavy customers",
            "strategy": "PROTECT. Long-tenure cohort (1722d avg tenure). 40% currently active (2/5). Relationship-heavy segment - dedicated account management, loyalty recognition, cross-sell/upsell. Do NOT treat as re-engagement targets.",
            "timing": "Proactive monthly touchpoints; quarterly business reviews",
            "channel": "Dedicated account manager; their preferred channel",
            "tone": "Partnership, appreciation, growth-focused",
            "kpi": "Retention rate > 95%; Account growth > 10% YoY; NPS > 50",
            "action_label": "Protect Relationship"
        },
        6: {
            "name": "Dormant Mid-Range Reactivator",
            "persona": "Re-engagement specialist for mid-tenure dormant accounts",
            "strategy": "84% dormant, mid-value customers. Moderate investment - quarterly nudge campaigns with relevant offers. Worth some effort but not top priority. 'We miss you' positioning.",
            "timing": "Quarterly campaigns",
            "channel": "Email sequence; phone for responsive ones only",
            "tone": "Friendly reminder, value-focused, welcome back",
            "kpi": "Reactivation rate > 8%; Response rate > 10%",
            "action_label": "Dormant Mid-Tenure"
        },
        7: {
            "name": "Archive Batch Manager",
            "persona": "Efficient batch campaign manager for archive-tier accounts",
            "strategy": "LOWEST value (£1,393 avg), near-zero recent_12m_revenue, 90% dormant. True archive tier - minimal investment only. Seasonal batch inclusion but never personal outreach. Consider for write-off if no engagement after 2 campaigns.",
            "timing": "Seasonal batch only (2x per year)",
            "channel": "Batch email only - zero personal investment",
            "tone": "Generic promotional, no personalization",
            "kpi": "Cost per contact < £0.50; Archive after 2 no-response campaigns",
            "action_label": "Archive"
        }
    }

    # Email Templates - segment-specific messaging based on behavioral analysis
    EMAIL_TEMPLATES = {
        0: {
            "subject": "Quick question about your KSP experience",
            "body": """Hi {company_name},

I noticed you worked with us intensively for a short period, then we lost touch. I'd love to understand what happened.

**Quick feedback request (30 seconds):**
Was it something about:
• Lead times - too long for your needs?
• Minimum order quantities - too high?
• Specification process - too complex?
• Something else entirely?

We've made improvements in all these areas and I'd genuinely value your input.

If you reply with just a few words about what didn't work, I'll personally ensure your next experience is smoother.

Thanks,
{sales_rep_name}
KSP Packaging

P.S. If you'd prefer, just reply with a number: 1=lead times, 2=MOQs, 3=specs, 4=other"""
        },
        1: {
            "subject": "{company_name} - can we talk?",
            "body": """Dear {contact_name},

I noticed {company_name} was a regular customer with us, and then things stopped. I'd genuinely like to understand what happened.

I'm not calling to sell you anything - I'm calling to listen.

**I'd like to understand:**
• Did we let you down somehow?
• Did your business needs change?
• Did you find a better solution elsewhere?

Your honest feedback helps us improve, regardless of whether we work together again.

Could I call you for 5 minutes this week? I promise: no sales pitch, just listening.

Regards,
{sales_rep_name}
Account Manager, KSP Packaging
{phone_number}

P.S. If you prefer email, just reply and I'll respond the same day."""
        },
        2: {
            "subject": "Let's make your next order easier - {company_name}",
            "body": """Hi {company_name},

I can see you've requested several quotes from us but orders haven't followed. I want to fix whatever's getting in the way.

**Let me remove the barriers:**
• Need faster turnaround? We can prioritize your orders
• MOQs too high? Let's discuss flexible quantities
• Spec process too complex? I'll personally handle it
• Pricing not right? Let's talk about what works for you

Reply to this email with what's holding you back, and I'll get back to you within 4 hours with a solution.

Or if it's easier, just tell me which quote you'd like me to revisit and I'll send a simplified version today.

{sales_rep_name}
KSP Packaging
{phone_number}"""
        },
        3: {
            "subject": "When's your next project? - KSP check-in",
            "body": """Hi {company_name},

Hope you're well. I know you tend to work with us on a project basis, so I wanted to check in and see what's on the horizon.

**Since we last worked together, we've added:**
• Faster production - 5-day express available
• New sustainable options (FSC, recycled materials)
• Enhanced finishing capabilities

If you have any projects coming up - even early-stage - I'd be happy to provide indicative pricing to help with your planning.

Just reply with a rough brief and I'll turn around a quote within 24 hours.

Best,
{sales_rep_name}
KSP Packaging"""
        },
        4: {
            "subject": "Personal message from our Managing Director - {company_name}",
            "body": """Dear {contact_name},

I'm writing personally because {company_name} represents one of our most valued business relationships, and I'm concerned that we've lost touch.

Before we discuss any commercial matters, I need to understand: did we fail you in some way?

**I would like to:**
1. Arrange a call or meeting at your convenience to understand what happened
2. Address any outstanding concerns you may have
3. Discuss how we can rebuild our partnership

If service failed, we'll fix it. If terms weren't competitive, we'll review them. If something else happened, I want to know.

Your account would receive dedicated senior oversight going forward, with priority access and improved terms.

May I call you this week?

Sincerely,
{senior_name}
{senior_title}, KSP Packaging
{direct_line}"""
        },
        5: {
            "subject": "Thank you for your continued partnership - {company_name}",
            "body": """Dear {contact_name},

I wanted to personally thank you for your ongoing business with KSP. Customers like {company_name} are the foundation of what we do.

**As a valued regular customer, you have access to:**
• {rep_name} as your dedicated account manager (direct: {phone_number})
• Priority production scheduling
• Early access to new products and materials
• Quarterly business reviews (let me know if you'd like to schedule one)

Is there anything we could be doing better for you? Your feedback directly shapes how we operate.

I'd also love to explore if there are product areas we haven't discussed - we've expanded significantly and there may be opportunities to consolidate your packaging with us.

Best regards,
{sales_rep_name}
Account Director, KSP Packaging"""
        },
        6: {
            "subject": "We miss working with you - {company_name}",
            "body": """Hi {company_name},

It's been a while since we heard from you, and we'd love to reconnect.

**What's new at KSP:**
• Improved lead times across all products
• New competitive pricing structure
• Extended eco-friendly range

As a returning customer, you'd receive preferential pricing on your next order.

If you have any upcoming needs, or just want to catch up on what's new, I'd be happy to chat.

Best regards,
The KSP Team"""
        },
        7: {
            "subject": "Seasonal offer from KSP Packaging",
            "body": """Hi {company_name},

Quick update: we're running a seasonal promotion with special pricing.

• Selected product discounts
• Free delivery on qualifying orders
• Fast turnaround available

Visit [link] or reply for a quote.

KSP Packaging"""
        }
    }

    # Import segment configuration from centralized source
    from services.data_loader import SEGMENT_CONFIG, SEGMENT_COLORS, SEGMENT_NAMES, SEGMENT_PRIORITY_ORDER

    # Segment names for display - from centralized config
    # Segments 0-4: ADS core recluster (subclusters of initial mixed cluster 0)
    # Segments 5-7: Original primary clusters 1, 2, 3 (remapped)
    # Key insight: Segment 5 is TRUE REGULARS (low recency, high tenure) - PROTECT
    #              Segment 0 is Early-Churn Burst (short tenure, high activity burst)
    #              Segment 4 is Win-back VIP (£91K avg, CRITICAL)

    # Tab selection
    tab1, tab2, tab3 = st.tabs(["📋 Strategy Overview", "📧 Email Templates", "🎯 Segment Deep Dive"])

    with tab1:
        st.markdown("### Marketing Strategy by Segment")
        st.markdown("""
        Each segment requires a **distinct approach** based on their behavioral patterns.
        Don't lump segments together - the motions are segment-specific.
        """)

        # Use centralized priority order
        # Priority: CRITICAL (4, 5), HIGH (1, 2), MEDIUM (0, 3), LOW (6, 7)
        priority_order = SEGMENT_PRIORITY_ORDER

        for seg_id in priority_order:
            agent = MARKETING_AGENTS[seg_id]
            config = SEGMENT_CONFIG[seg_id]
            color = SEGMENT_COLORS[seg_id]

            # Show priority badge
            priority_badge = f"[{config['priority']}]"
            motion_badge = f"Motion: {config['motion']}"

            with st.expander(f"**{priority_badge} {SEGMENT_NAMES[seg_id]}** - {agent['name']}", expanded=(seg_id in [4, 5, 2])):
                # Motion header with color coding
                st.markdown(f"""
                <div style="display: flex; gap: 10px; margin-bottom: 10px;">
                    <span style="background: {color}; color: white; padding: 4px 12px; border-radius: 4px; font-weight: bold;">
                        {config['motion']}
                    </span>
                    <span style="background: #f0f0f0; color: #333; padding: 4px 12px; border-radius: 4px;">
                        Action: {config['action_label']}
                    </span>
                </div>
                """, unsafe_allow_html=True)

                col1, col2 = st.columns([2, 1])

                with col1:
                    st.markdown(f"**Strategy:** {agent['strategy']}")
                    st.markdown(f"**Tone:** {agent['tone']}")

                with col2:
                    st.markdown(f"**Timing:** {agent['timing']}")
                    st.markdown(f"**Channel:** {agent['channel']}")
                    st.markdown(f"**KPIs:** {agent['kpi']}")

    with tab2:
        st.markdown("### Ready-to-Use Email Templates")
        st.markdown("Select a segment to view and copy the email template:")

        selected_segment = st.selectbox(
            "Select Segment",
            options=list(SEGMENT_NAMES.keys()),
            format_func=lambda x: f"{SEGMENT_NAMES[x]}"
        )

        if selected_segment is not None:
            template = EMAIL_TEMPLATES[selected_segment]
            agent = MARKETING_AGENTS[selected_segment]

            st.markdown(f"#### {SEGMENT_NAMES[selected_segment]}")
            st.markdown(f"*{agent['persona']}*")

            st.markdown("---")

            st.markdown(f"**Subject Line:**")
            st.code(template['subject'], language=None)

            st.markdown(f"**Email Body:**")
            st.code(template['body'], language=None)

            # Copy buttons
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "📥 Download Template",
                    f"Subject: {template['subject']}\n\n{template['body']}",
                    f"email_template_{SEGMENT_NAMES[selected_segment].lower().replace(' ', '_')}.txt",
                    "text/plain"
                )

            st.markdown("---")
            st.markdown("**Personalization Variables:**")
            st.markdown("""
            Replace these placeholders before sending:
            - `{company_name}` - Customer company name
            - `{contact_name}` - Contact person's name
            - `{sales_rep_name}` - Your name
            - `{phone_number}` - Your contact number
            - `{order_number}` - Relevant order number
            """)

    with tab3:
        st.markdown("### Segment Deep Dive")

        from services.unified_data_service import get_segment_summary, load_customer_data

        summary_df = get_segment_summary()
        customers = load_customer_data()

        if not summary_df.empty:
            selected_deep_dive = st.selectbox(
                "Select segment for detailed view",
                options=list(SEGMENT_NAMES.keys()),
                format_func=lambda x: f"{SEGMENT_NAMES[x]}",
                key="deep_dive_select"
            )

            if selected_deep_dive is not None:
                seg_data = summary_df[summary_df['segment_id'] == selected_deep_dive]
                agent = MARKETING_AGENTS[selected_deep_dive]

                if not seg_data.empty:
                    row = seg_data.iloc[0]

                    col1, col2, col3 = st.columns(3)
                    col1.metric("Customers", f"{row['count']:,}")
                    col2.metric("Total Revenue", f"£{row['total_revenue']:,.0f}")
                    col3.metric("Avg Recency", f"{row['avg_recency']:.0f} days")

                st.markdown("---")
                st.markdown(f"### Marketing Agent: {agent['name']}")
                st.markdown(f"*{agent['persona']}*")

                st.markdown(f"""
                **Full Strategy Brief:**

                {agent['strategy']}

                **Execution Details:**
                - **Timing:** {agent['timing']}
                - **Primary Channel:** {agent['channel']}
                - **Communication Tone:** {agent['tone']}
                - **Success Metric:** {agent['kpi']}
                """)

                # Show sample customers from this segment
                if not customers.empty and 'ads_cluster' in customers.columns:
                    seg_customers = customers[customers['ads_cluster'] == selected_deep_dive].head(10)
                    if not seg_customers.empty:
                        st.markdown("---")
                        st.markdown("**Sample Customers in This Segment:**")
                        display_cols = ['company', 'monetary_total', 'frequency', 'recency_days']
                        available = [c for c in display_cols if c in seg_customers.columns]
                        st.dataframe(
                            seg_customers[available].style.format({
                                'monetary_total': '£{:,.0f}',
                                'recency_days': '{:.0f} days'
                            }),
                            use_container_width=True,
                            hide_index=True
                        )


# =============================================================================
# MAIN ROUTING
# =============================================================================

def main():
    if page == "🎯 Action Center":
        render_action_center()
    elif page == "💰 Revenue Opportunities":
        render_revenue_opportunities()
    elif page == "🔍 Prospect Pipeline":
        render_prospect_pipeline()
    elif page == "📊 Customer Explorer":
        render_customer_explorer()
    elif page == "🔎 Company Search":
        render_company_search()
    elif page == "📧 Marketing Playbook":
        render_marketing_playbook()


if __name__ == "__main__":
    main()
