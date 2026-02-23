"""
Segment Predictor Page
Predict which segment a new customer belongs to using ML models
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Segment Predictor", page_icon="🎯", layout="wide")

from services.data_loader import load_cluster_profiles, load_company_data, SEGMENT_COLORS
from services.model_service import (
    predict_segment, get_segment_probability_distribution,
    get_feature_importance_for_segment, load_feature_config
)
from services.marketing_service import get_strategy_for_segment


def main():
    st.title("🎯 Segment Predictor")
    st.markdown("Predict which customer segment a new company belongs to based on their characteristics.")

    profiles = load_cluster_profiles()

    # Two column layout
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📝 Enter Customer Data")
        customer_data = render_input_form()

        predict_button = st.button("🔮 Predict Segment", type="primary", use_container_width=True)

    with col2:
        st.subheader("📊 Prediction Results")

        if predict_button and customer_data:
            render_prediction_results(customer_data, profiles)
        else:
            st.info("Fill in the customer data and click 'Predict Segment' to see results.")

    # Example data section
    st.markdown("---")
    with st.expander("📋 View Sample Data for Reference"):
        render_sample_data()


def render_input_form() -> dict:
    """Render the input form for customer data"""

    # Get feature config
    feature_config = load_feature_config()
    required_features = feature_config.get('required_features', [
        'frequency', 'monetary_total', 'monetary_mean', 'recency_days', 'tenure_days'
    ])

    customer_data = {}

    # Order Metrics
    st.markdown("**Order Metrics**")

    col1, col2 = st.columns(2)

    with col1:
        customer_data['frequency'] = st.number_input(
            "Order Frequency",
            min_value=1,
            max_value=500,
            value=5,
            help="Total number of orders placed"
        )

        customer_data['monetary_total'] = st.number_input(
            "Total Revenue (£)",
            min_value=0.0,
            max_value=1000000.0,
            value=10000.0,
            step=1000.0,
            help="Total revenue from this customer"
        )

    with col2:
        customer_data['monetary_mean'] = st.number_input(
            "Average Order Value (£)",
            min_value=0.0,
            max_value=100000.0,
            value=2000.0,
            step=100.0,
            help="Average value per order"
        )

        customer_data['estimates_per_year'] = st.number_input(
            "Estimates Per Year",
            min_value=0.0,
            max_value=200.0,
            value=10.0,
            step=1.0,
            help="Number of quote requests per year"
        )

    # Timeline Metrics
    st.markdown("**Timeline Metrics**")

    col1, col2 = st.columns(2)

    with col1:
        customer_data['recency_days'] = st.number_input(
            "Days Since Last Order",
            min_value=0,
            max_value=3000,
            value=90,
            help="How many days since their last order"
        )

        customer_data['tenure_days'] = st.number_input(
            "Customer Tenure (Days)",
            min_value=0,
            max_value=5000,
            value=365,
            help="How long they've been a customer"
        )

    with col2:
        customer_data['avg_days_between_orders'] = st.number_input(
            "Avg Days Between Orders",
            min_value=0.0,
            max_value=1000.0,
            value=60.0,
            step=10.0,
            help="Average gap between orders"
        )

        customer_data['first_order_days_ago'] = st.number_input(
            "First Order (Days Ago)",
            min_value=0,
            max_value=5000,
            value=400,
            help="How many days ago was their first order"
        )

    # Product Metrics
    st.markdown("**Product Metrics**")

    col1, col2 = st.columns(2)

    with col1:
        customer_data['product_type_diversity'] = st.number_input(
            "Product Type Diversity",
            min_value=0.0,
            max_value=10.0,
            value=2.0,
            step=0.5,
            help="Number of different product types ordered"
        )

    with col2:
        customer_data['recent_12m_revenue'] = st.number_input(
            "Last 12 Months Revenue (£)",
            min_value=0.0,
            max_value=500000.0,
            value=5000.0,
            step=500.0,
            help="Revenue in the last 12 months"
        )

    return customer_data


def render_prediction_results(customer_data: dict, profiles: dict):
    """Render the prediction results"""

    # Get prediction
    segment_id, segment_name, confidence_info = predict_segment(customer_data)

    if segment_id == -1:
        st.error(f"Prediction failed: {confidence_info.get('error', 'Unknown error')}")
        return

    # Main prediction result
    color = SEGMENT_COLORS.get(segment_id, '#666')
    confidence = confidence_info.get('confidence', 0) * 100

    st.markdown(f"""
    <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, {color}22, {color}11);
                border-radius: 15px; border: 3px solid {color};">
        <h2 style="color: {color}; margin: 0;">Predicted Segment</h2>
        <h1 style="color: {color}; font-size: 2.5rem; margin: 0.5rem 0;">{segment_name}</h1>
        <p style="font-size: 1.2rem; color: #666;">Confidence: <strong>{confidence:.1f}%</strong></p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")

    # Probability distribution
    probabilities = get_segment_probability_distribution(customer_data)

    if probabilities:
        st.markdown("**Probability Distribution Across Segments**")

        prob_data = []
        for seg_id, prob in probabilities.items():
            seg_name = profiles.get(seg_id, {}).get('name', f'Segment {seg_id}')
            prob_data.append({
                'Segment': seg_name,
                'Probability': prob * 100,
                'Color': SEGMENT_COLORS.get(int(seg_id), '#666')
            })

        prob_df = pd.DataFrame(prob_data).sort_values('Probability', ascending=True)

        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=prob_df['Segment'],
            x=prob_df['Probability'],
            orientation='h',
            marker_color=prob_df['Color'].tolist(),
            text=[f"{p:.1f}%" for p in prob_df['Probability']],
            textposition='outside'
        ))

        fig.update_layout(
            height=250,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title="Probability (%)",
            xaxis_range=[0, 100]
        )

        st.plotly_chart(fig, use_container_width=True)

    # Segment profile and recommendations
    st.markdown("---")

    profile = profiles.get(str(segment_id), {})

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Segment Profile**")
        st.markdown(f"**Risk Level:** {profile.get('risk_level', 'N/A')}")
        st.markdown(profile.get('description', 'No description available.'))

        st.markdown("**Characteristics:**")
        for key, value in profile.get('characteristics', {}).items():
            st.markdown(f"- {key.replace('_', ' ').title()}: {value}")

    with col2:
        st.markdown("**Recommended Actions**")
        for i, action in enumerate(profile.get('recommended_actions', []), 1):
            st.markdown(f"{i}. {action}")

        # Link to marketing playbook
        strategy = get_strategy_for_segment(segment_id)
        if strategy:
            st.markdown("---")
            st.markdown(f"**Priority:** {strategy.get('priority', 'N/A')}")
            st.markdown(f"**Objective:** {strategy.get('objective', 'N/A')}")

    # Feature importance
    st.markdown("---")
    st.markdown("**Key Distinguishing Features for This Segment**")

    importance = get_feature_importance_for_segment(segment_id)
    if importance:
        imp_data = []
        for feature, stats in list(importance.items())[:6]:
            imp_data.append({
                'Feature': feature.replace('_', ' ').title(),
                'Segment Mean': stats['segment_mean'],
                'Overall Mean': stats['overall_mean'],
                'Deviation': stats['deviation_pct'],
                'Distinctive': '✓' if stats['is_distinctive'] else ''
            })

        imp_df = pd.DataFrame(imp_data)
        st.dataframe(imp_df, use_container_width=True, hide_index=True)


def render_sample_data():
    """Render sample data for reference"""

    companies = load_company_data()

    if companies.empty:
        st.warning("Sample data not available.")
        return

    # Show a sample of companies with key metrics
    display_cols = ['company', 'frequency', 'monetary_total', 'monetary_mean',
                   'recency_days', 'tenure_days', 'product_type_diversity']
    available_cols = [c for c in display_cols if c in companies.columns]

    sample = companies[available_cols].head(10)

    st.markdown("**Sample Customer Data (for reference):**")
    st.dataframe(sample, use_container_width=True, hide_index=True)

    # Statistics
    st.markdown("**Feature Ranges in Dataset:**")

    stats_cols = ['frequency', 'monetary_total', 'recency_days', 'tenure_days']
    available_stats = [c for c in stats_cols if c in companies.columns]

    stats_data = []
    for col in available_stats:
        stats_data.append({
            'Feature': col.replace('_', ' ').title(),
            'Min': companies[col].min(),
            'Median': companies[col].median(),
            'Max': companies[col].max()
        })

    st.dataframe(pd.DataFrame(stats_data), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
