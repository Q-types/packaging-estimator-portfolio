"""
Company Explorer Page
Search and drill down into individual company profiles
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Company Explorer", page_icon="🏢", layout="wide")

from services.data_loader import (
    load_cluster_profiles, load_company_data, load_cluster_assignments,
    get_company_details, get_companies_by_segment, SEGMENT_COLORS
)
from services.segment_service import (
    search_companies, get_top_companies_by_segment
)


def main():
    st.title("🏢 Company Explorer")
    st.markdown("Search for companies and view detailed profiles.")

    profiles = load_cluster_profiles()
    companies = load_company_data()
    assignments = load_cluster_assignments()

    if companies.empty:
        st.error("Company data not loaded.")
        return

    # Sidebar filters
    with st.sidebar:
        st.subheader("Filters")

        # Segment filter
        segment_options = {"All Segments": None}
        segment_options.update({
            profiles.get(str(i), {}).get('name', f'Segment {i}'): i
            for i in sorted(assignments['ads_cluster'].unique()) if not pd.isna(i)
        })
        selected_segment_name = st.selectbox("Segment", list(segment_options.keys()))
        selected_segment = segment_options[selected_segment_name]

        # Sort options
        sort_options = {
            "Revenue (High to Low)": ("monetary_total", False),
            "Revenue (Low to High)": ("monetary_total", True),
            "Frequency (High to Low)": ("frequency", False),
            "Recency (Recent First)": ("recency_days", True),
            "Company Name (A-Z)": ("company", True)
        }
        sort_choice = st.selectbox("Sort By", list(sort_options.keys()))
        sort_col, sort_asc = sort_options[sort_choice]

    # Main content tabs
    tab1, tab2 = st.tabs(["🔍 Search & Browse", "📋 Company Details"])

    with tab1:
        render_search_browse(companies, assignments, profiles, selected_segment, sort_col, sort_asc)

    with tab2:
        render_company_details(companies, assignments, profiles)


def render_search_browse(companies, assignments, profiles, segment_filter, sort_col, sort_asc):
    """Render search and browse interface"""

    # Search box
    search_query = st.text_input("🔍 Search Companies", placeholder="Enter company name...")

    # Get filtered data
    merged = companies.merge(assignments, on='company', how='left')

    if segment_filter is not None:
        merged = merged[merged['ads_cluster'] == segment_filter]

    if search_query:
        merged = merged[merged['company'].str.contains(search_query, case=False, na=False)]

    # Add segment names
    merged['Segment'] = merged['ads_cluster'].apply(
        lambda x: profiles.get(str(int(x)), {}).get('name', f'Segment {int(x)}') if pd.notna(x) else 'Unknown'
    )

    # Sort
    if sort_col in merged.columns:
        merged = merged.sort_values(sort_col, ascending=sort_asc)

    # Display count
    st.markdown(f"**Showing {len(merged):,} companies**")

    # Column selection for display
    display_cols = ['company', 'Segment']
    optional_cols = ['monetary_total', 'frequency', 'recency_days', 'tenure_days', 'monetary_mean']
    display_cols.extend([c for c in optional_cols if c in merged.columns])

    # Paginated table
    page_size = 25
    total_pages = max(1, len(merged) // page_size + (1 if len(merged) % page_size else 0))

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        page = st.number_input("Page", min_value=1, max_value=total_pages, value=1)

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size

    display_df = merged[display_cols].iloc[start_idx:end_idx].copy()

    # Format columns
    format_dict = {}
    if 'monetary_total' in display_df.columns:
        format_dict['monetary_total'] = '£{:,.0f}'
    if 'monetary_mean' in display_df.columns:
        format_dict['monetary_mean'] = '£{:,.0f}'
    if 'recency_days' in display_df.columns:
        format_dict['recency_days'] = '{:.0f} days'
    if 'tenure_days' in display_df.columns:
        format_dict['tenure_days'] = '{:.0f} days'

    # Add color coding for segments
    def color_segment(val):
        segment_id = None
        for sid, profile in profiles.items():
            if profile.get('name') == val:
                segment_id = int(sid)
                break
        if segment_id is not None:
            color = SEGMENT_COLORS.get(segment_id, '#666')
            return f'background-color: {color}22; color: {color}; font-weight: bold;'
        return ''

    styled_df = display_df.style
    if format_dict:
        styled_df = styled_df.format(format_dict)
    styled_df = styled_df.applymap(color_segment, subset=['Segment'])

    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    st.caption(f"Page {page} of {total_pages}")


def render_company_details(companies, assignments, profiles):
    """Render detailed company profile view"""

    # Company selector
    merged = companies.merge(assignments, on='company', how='left')
    company_list = sorted(merged['company'].dropna().unique().tolist())

    selected_company = st.selectbox(
        "Select Company",
        company_list,
        index=0 if company_list else None
    )

    if not selected_company:
        st.info("Select a company to view details.")
        return

    # Get company details
    details = get_company_details(selected_company)

    if not details:
        st.error(f"Could not load details for {selected_company}")
        return

    # Header with segment badge
    segment_id = details.get('cluster_id', 0)
    segment_name = details.get('cluster_name', 'Unknown')
    segment_color = SEGMENT_COLORS.get(segment_id, '#666')

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"## {selected_company}")
    with col2:
        st.markdown(f"""
        <div style="background: {segment_color}22; color: {segment_color}; padding: 0.5rem 1rem;
                    border-radius: 20px; text-align: center; font-weight: bold; border: 2px solid {segment_color};">
            {segment_name}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        value = details.get('monetary_total', 0)
        st.metric("Total Revenue", f"£{value:,.0f}")

    with col2:
        value = details.get('frequency', 0)
        st.metric("Order Frequency", f"{value:.0f}")

    with col3:
        value = details.get('recency_days', 0)
        st.metric("Days Since Last Order", f"{value:.0f}")

    with col4:
        value = details.get('tenure_days', 0)
        st.metric("Tenure (Days)", f"{value:.0f}")

    st.markdown("---")

    # Detailed metrics in columns
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Order Metrics")
        metrics_order = [
            ('frequency', 'Order Frequency'),
            ('monetary_total', 'Total Revenue'),
            ('monetary_mean', 'Average Order Value'),
            ('monetary_median', 'Median Order Value'),
            ('estimates_per_year', 'Estimates Per Year'),
        ]

        for key, label in metrics_order:
            if key in details:
                value = details[key]
                if 'monetary' in key or 'revenue' in key.lower():
                    st.markdown(f"**{label}:** £{value:,.2f}")
                else:
                    st.markdown(f"**{label}:** {value:,.2f}")

    with col2:
        st.subheader("📅 Timeline Metrics")
        metrics_time = [
            ('recency_days', 'Days Since Last Order'),
            ('tenure_days', 'Customer Tenure (Days)'),
            ('first_order_days_ago', 'First Order (Days Ago)'),
            ('avg_days_between_orders', 'Avg Days Between Orders'),
        ]

        for key, label in metrics_time:
            if key in details:
                value = details[key]
                st.markdown(f"**{label}:** {value:,.0f}")

    st.markdown("---")

    # Segment context
    st.subheader("🎯 Segment Context")
    profile = details.get('cluster_profile', {})

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**Segment:** {segment_name}")
        st.markdown(f"**Risk Level:** {profile.get('risk_level', 'N/A')}")
        st.markdown(f"**Description:** {profile.get('description', 'N/A')}")

    with col2:
        st.markdown("**Recommended Actions:**")
        for action in profile.get('recommended_actions', [])[:5]:
            st.markdown(f"- {action}")

    # Visual comparison with segment
    st.markdown("---")
    st.subheader("📈 Comparison with Segment Average")

    segment_data = get_companies_by_segment(segment_id)
    if not segment_data.empty:
        comparison_metrics = ['monetary_total', 'frequency', 'recency_days', 'tenure_days']
        available_metrics = [m for m in comparison_metrics if m in segment_data.columns and m in details]

        if available_metrics:
            comparison_data = []
            for metric in available_metrics:
                company_val = details.get(metric, 0)
                segment_avg = segment_data[metric].mean()
                comparison_data.append({
                    'Metric': metric.replace('_', ' ').title(),
                    'Company': company_val,
                    'Segment Avg': segment_avg,
                    'Difference': ((company_val - segment_avg) / segment_avg * 100) if segment_avg else 0
                })

            comp_df = pd.DataFrame(comparison_data)

            fig = go.Figure()
            fig.add_trace(go.Bar(
                name=selected_company,
                x=comp_df['Metric'],
                y=comp_df['Company'],
                marker_color='#1976D2'
            ))
            fig.add_trace(go.Bar(
                name='Segment Average',
                x=comp_df['Metric'],
                y=comp_df['Segment Avg'],
                marker_color='#E0E0E0'
            ))

            fig.update_layout(barmode='group', title='Company vs Segment Average')
            st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
