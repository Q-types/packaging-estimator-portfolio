"""
Marketing Playbook Page
Segment-specific marketing strategies, campaigns, and email templates
"""
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Marketing Playbook", page_icon="📈", layout="wide")

from services.data_loader import load_cluster_profiles, load_cluster_assignments, SEGMENT_COLORS
from services.marketing_service import (
    get_marketing_strategies, get_strategy_for_segment,
    get_campaign_recommendations, get_kpis_for_segment
)

PRIORITY_COLORS = {
    "CRITICAL": "#C62828",
    "HIGH": "#F57C00",
    "PROTECT": "#2E7D32",
    "MEDIUM": "#1976D2",
    "LOW": "#666"
}


def main():
    st.title("📈 Marketing Playbook")
    st.markdown("Data-driven marketing strategies tailored to each customer segment.")

    profiles = load_cluster_profiles()
    strategies = get_marketing_strategies()
    assignments = load_cluster_assignments()

    # Calculate segment counts for context
    segment_counts = {}
    if not assignments.empty:
        segment_counts = assignments['ads_cluster'].value_counts().to_dict()

    # Tabs for navigation
    tab1, tab2, tab3 = st.tabs(["📊 Strategy Overview", "🎯 Segment Deep Dive", "📧 Email Templates"])

    with tab1:
        render_strategy_overview(profiles, strategies, segment_counts)

    with tab2:
        render_segment_strategy(profiles, strategies, segment_counts)

    with tab3:
        render_email_templates(profiles, strategies)


def render_strategy_overview(profiles: dict, strategies: dict, segment_counts: dict):
    """Render overview of all segment strategies"""

    st.subheader("Strategy Priority Matrix")

    # Priority order for segments
    priority_order = ["CRITICAL", "HIGH", "PROTECT", "MEDIUM", "LOW"]

    for priority in priority_order:
        matching_segments = [
            (seg_id, strat) for seg_id, strat in strategies.items()
            if strat.get('priority') == priority
        ]

        if matching_segments:
            st.markdown(f"### {priority} Priority")

            for seg_id, strategy in matching_segments:
                color = SEGMENT_COLORS.get(int(seg_id), '#666')
                priority_color = PRIORITY_COLORS.get(priority, '#666')
                count = segment_counts.get(int(seg_id), 0)

                with st.container():
                    col1, col2, col3 = st.columns([2, 3, 1])

                    with col1:
                        st.markdown(f"""
                        <div style="border-left: 4px solid {color}; padding-left: 1rem;">
                            <h4 style="color: {color}; margin: 0;">{strategy.get('segment_name', f'Segment {seg_id}')}</h4>
                            <p style="color: #666; margin: 0;">{count:,} companies</p>
                        </div>
                        """, unsafe_allow_html=True)

                    with col2:
                        st.markdown(f"**Objective:** {strategy.get('objective', 'N/A')}")
                        st.markdown(f"{strategy.get('strategy_summary', 'N/A')}")

                    with col3:
                        st.markdown(f"""
                        <div style="background: {priority_color}22; color: {priority_color}; padding: 0.5rem;
                                    border-radius: 5px; text-align: center; font-weight: bold;">
                            {priority}
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown("---")

    # Budget allocation summary
    st.subheader("Budget Allocation by Segment")

    budget_data = []
    for seg_id, strategy in strategies.items():
        allocation = strategy.get('budget_allocation', {})
        budget_data.append({
            'Segment': strategy.get('segment_name', f'Segment {seg_id}'),
            'Priority': strategy.get('priority', 'N/A'),
            **{k.replace('_', ' ').title(): v for k, v in allocation.items()}
        })

    if budget_data:
        budget_df = pd.DataFrame(budget_data)
        st.dataframe(budget_df, use_container_width=True, hide_index=True)


def render_segment_strategy(profiles: dict, strategies: dict, segment_counts: dict):
    """Render detailed strategy for selected segment"""

    st.subheader("Segment Strategy Deep Dive")

    # Segment selector
    segment_options = {
        strategies[seg_id].get('segment_name', f'Segment {seg_id}'): seg_id
        for seg_id in sorted(strategies.keys(), key=int)
    }

    selected_name = st.selectbox("Select Segment", list(segment_options.keys()))
    selected_id = segment_options[selected_name]

    strategy = strategies.get(selected_id, {})
    color = SEGMENT_COLORS.get(int(selected_id), '#666')
    count = segment_counts.get(int(selected_id), 0)

    # Header
    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown(f"""
        <div style="border-left: 5px solid {color}; padding: 1rem; background: {color}11; border-radius: 5px;">
            <h2 style="color: {color}; margin: 0;">{strategy.get('segment_name', 'Unknown')}</h2>
            <p style="font-size: 1.2rem; margin: 0.5rem 0;"><strong>Objective:</strong> {strategy.get('objective', 'N/A')}</p>
            <p style="margin: 0;">{strategy.get('strategy_summary', 'N/A')}</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        priority = strategy.get('priority', 'N/A')
        priority_color = PRIORITY_COLORS.get(priority, '#666')

        st.metric("Companies", f"{count:,}")
        st.markdown(f"""
        <div style="background: {priority_color}; color: white; padding: 0.5rem 1rem;
                    border-radius: 5px; text-align: center; font-weight: bold;">
            {priority} PRIORITY
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Tactics
    st.subheader("🎯 Recommended Tactics")

    tactics = strategy.get('tactics', [])
    for i, tactic in enumerate(tactics, 1):
        with st.expander(f"**{i}. {tactic.get('name', 'Unnamed Tactic')}**", expanded=(i <= 2)):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(tactic.get('description', 'No description'))

            with col2:
                st.markdown(f"**Timeline:** {tactic.get('timeline', 'N/A')}")
                st.markdown(f"**KPI:** {tactic.get('kpi', 'N/A')}")

    st.markdown("---")

    # Budget allocation
    st.subheader("💰 Budget Allocation")

    allocation = strategy.get('budget_allocation', {})
    if allocation:
        cols = st.columns(len(allocation))
        for col, (category, percentage) in zip(cols, allocation.items()):
            with col:
                st.markdown(f"""
                <div style="text-align: center; padding: 1rem; background: #f8f9fa; border-radius: 10px;">
                    <h3 style="color: {color}; margin: 0;">{percentage}</h3>
                    <p style="margin: 0;">{category.replace('_', ' ').title()}</p>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")

    # Success metrics
    st.subheader("📊 Success Metrics")

    metrics = strategy.get('success_metrics', [])
    if metrics:
        cols = st.columns(len(metrics))
        for col, metric in zip(cols, metrics):
            with col:
                st.info(metric)


def render_email_templates(profiles: dict, strategies: dict):
    """Render email templates for each segment"""

    st.subheader("📧 Email Templates by Segment")

    # Segment selector
    segment_options = {
        strategies[seg_id].get('segment_name', f'Segment {seg_id}'): seg_id
        for seg_id in sorted(strategies.keys(), key=int)
    }

    selected_name = st.selectbox("Select Segment for Templates", list(segment_options.keys()))
    selected_id = segment_options[selected_name]

    strategy = strategies.get(selected_id, {})
    color = SEGMENT_COLORS.get(int(selected_id), '#666')
    templates = strategy.get('email_templates', [])

    if not templates:
        st.warning("No email templates available for this segment.")
        return

    st.markdown(f"**{len(templates)} template(s) available for {selected_name}**")

    for template in templates:
        with st.expander(f"📧 {template.get('name', 'Unnamed Template')}", expanded=True):

            # Subject line
            st.markdown("**Subject Line:**")
            st.code(template.get('subject', 'No subject'), language=None)

            # Preview text
            if template.get('preview'):
                st.markdown("**Preview Text:**")
                st.markdown(f"_{template.get('preview')}_")

            # Email body
            st.markdown("**Email Body:**")

            body = template.get('body', 'No body content')

            # Highlight placeholders
            highlighted_body = body.replace('[', '**[').replace(']', ']**')

            st.markdown(f"""
            <div style="background: #f8f9fa; padding: 1.5rem; border-radius: 10px;
                        border: 1px solid #e0e0e0; white-space: pre-wrap; font-family: system-ui;">
{body}
            </div>
            """, unsafe_allow_html=True)

            # Copy button (using text area as workaround)
            st.markdown("---")
            col1, col2 = st.columns([3, 1])
            with col1:
                st.caption("Placeholders to replace: [Contact Name], [Company Name], [X], etc.")
            with col2:
                if st.button(f"📋 Copy Template", key=f"copy_{selected_id}_{template.get('name')}"):
                    st.code(body)
                    st.success("Template displayed above - copy from there!")

    # Tips for personalization
    st.markdown("---")
    st.subheader("💡 Personalization Tips")

    tips = {
        "0": [
            "Reference their last order date specifically",
            "Mention products they've ordered before",
            "Acknowledge their history with the company"
        ],
        "1": [
            "Keep it welcoming and educational",
            "Don't overwhelm with too much information",
            "Focus on building trust"
        ],
        "2": [
            "Reference their growth trajectory",
            "Share relevant case studies",
            "Position as a strategic partner"
        ],
        "3": [
            "Acknowledge their VIP status",
            "Make them feel valued",
            "Offer exclusive access and benefits"
        ],
        "4": [
            "Remind them of past positive experiences",
            "Make reordering easy",
            "Understand their project-based needs"
        ]
    }

    segment_tips = tips.get(selected_id, [])
    for tip in segment_tips:
        st.markdown(f"- {tip}")


if __name__ == "__main__":
    main()
