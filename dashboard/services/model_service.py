"""
ML Model Service
Handles loading and using trained ML models for segment prediction
"""
import streamlit as st
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from typing import Tuple, Optional
import json

# Base paths
BASE_DIR = Path(__file__).parent.parent.parent
MODELS_DIR = BASE_DIR / "models" / "customer_segments"
ADS_CLUSTERING_DIR = BASE_DIR / "data" / "companies" / "ads_clustering"


@st.cache_resource
def load_kmeans_model():
    """Load the KMeans clustering model"""
    model_path = ADS_CLUSTERING_DIR / "kmeans_ads.joblib"
    if model_path.exists():
        return joblib.load(model_path)

    # Try alternative path
    alt_path = MODELS_DIR / "model.joblib"
    if alt_path.exists():
        return joblib.load(alt_path)

    st.warning("KMeans model not found")
    return None


@st.cache_resource
def load_pca_model():
    """Load the PCA dimensionality reduction model"""
    pca_path = ADS_CLUSTERING_DIR / "pca_ads.joblib"
    if pca_path.exists():
        return joblib.load(pca_path)
    return None


@st.cache_resource
def load_scaler():
    """Load the feature scaler"""
    scaler_path = MODELS_DIR / "scaler.joblib"
    if scaler_path.exists():
        return joblib.load(scaler_path)

    # Try preprocessor
    preprocessor_path = ADS_CLUSTERING_DIR / "preprocessor_ads.joblib"
    if preprocessor_path.exists():
        return joblib.load(preprocessor_path)

    return None


@st.cache_resource
def load_encoder():
    """Load the categorical encoder"""
    encoder_path = MODELS_DIR / "encoder.joblib"
    if encoder_path.exists():
        return joblib.load(encoder_path)
    return None


@st.cache_data
def load_feature_config() -> dict:
    """Load feature configuration"""
    config_path = MODELS_DIR / "feature_config.json"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)

    # Default feature config based on notebook analysis
    return {
        "numerical_features": [
            "frequency", "monetary_total", "monetary_mean", "monetary_median",
            "monetary_std", "monetary_max", "recency_days", "first_order_days_ago",
            "tenure_days", "avg_days_between_orders", "recent_12m_revenue",
            "estimates_per_year", "product_type_diversity"
        ],
        "required_features": [
            "frequency", "monetary_total", "monetary_mean",
            "recency_days", "tenure_days"
        ]
    }


def predict_segment(customer_data: dict) -> Tuple[int, str, dict]:
    """
    Predict which segment a new customer belongs to

    Args:
        customer_data: Dictionary with customer features

    Returns:
        Tuple of (segment_id, segment_name, confidence_info)
    """
    from services.data_loader import load_cluster_profiles

    kmeans = load_kmeans_model()
    scaler = load_scaler()
    profiles = load_cluster_profiles()

    if kmeans is None:
        return -1, "Unknown", {"error": "Model not loaded"}

    # Prepare features
    feature_config = load_feature_config()
    required_features = feature_config.get("required_features", [])

    # Create feature vector
    feature_values = []
    missing_features = []

    for feature in required_features:
        if feature in customer_data:
            feature_values.append(float(customer_data[feature]))
        else:
            missing_features.append(feature)
            feature_values.append(0.0)  # Default value

    if missing_features:
        st.warning(f"Missing features (using defaults): {', '.join(missing_features)}")

    # Convert to numpy array
    X = np.array(feature_values).reshape(1, -1)

    # Scale if scaler available
    if scaler is not None:
        try:
            X = scaler.transform(X)
        except Exception as e:
            st.warning(f"Scaling failed, using raw values: {e}")

    # Predict
    try:
        segment_id = int(kmeans.predict(X)[0])

        # Get distances to all centroids for confidence
        distances = kmeans.transform(X)[0]
        min_distance = distances[segment_id]
        confidence = 1 / (1 + min_distance)  # Convert distance to confidence

        # Get segment name
        segment_name = profiles.get(str(segment_id), {}).get('name', f'Segment {segment_id}')

        confidence_info = {
            "confidence": float(confidence),
            "distances": {str(i): float(d) for i, d in enumerate(distances)},
            "closest_alternatives": sorted(
                [(i, d) for i, d in enumerate(distances) if i != segment_id],
                key=lambda x: x[1]
            )[:2]
        }

        return segment_id, segment_name, confidence_info

    except Exception as e:
        return -1, "Error", {"error": str(e)}


def get_segment_probability_distribution(customer_data: dict) -> dict:
    """
    Get probability distribution across all segments for a customer
    Uses distance-based soft assignment
    """
    kmeans = load_kmeans_model()
    scaler = load_scaler()

    if kmeans is None:
        return {}

    feature_config = load_feature_config()
    required_features = feature_config.get("required_features", [])

    # Create feature vector
    feature_values = [float(customer_data.get(f, 0)) for f in required_features]
    X = np.array(feature_values).reshape(1, -1)

    if scaler is not None:
        try:
            X = scaler.transform(X)
        except:
            pass

    try:
        distances = kmeans.transform(X)[0]

        # Convert distances to probabilities using softmax
        exp_neg_distances = np.exp(-distances)
        probabilities = exp_neg_distances / exp_neg_distances.sum()

        return {str(i): float(p) for i, p in enumerate(probabilities)}
    except:
        return {}


def get_feature_importance_for_segment(segment_id: int) -> dict:
    """
    Get feature importance for a specific segment
    Based on centroid values relative to overall mean
    """
    from services.data_loader import load_company_data, load_cluster_assignments

    companies = load_company_data()
    assignments = load_cluster_assignments()

    if companies.empty or assignments.empty:
        return {}

    merged = companies.merge(assignments, on='company', how='left')

    feature_config = load_feature_config()
    numerical_features = feature_config.get("numerical_features", [])
    available_features = [f for f in numerical_features if f in merged.columns]

    importance = {}
    for feature in available_features:
        overall_mean = merged[feature].mean()
        segment_mean = merged[merged['ads_cluster'] == segment_id][feature].mean()

        if overall_mean != 0:
            deviation = (segment_mean - overall_mean) / overall_mean
        else:
            deviation = 0

        importance[feature] = {
            "segment_mean": float(segment_mean),
            "overall_mean": float(overall_mean),
            "deviation_pct": float(deviation * 100),
            "is_distinctive": abs(deviation) > 0.2  # >20% deviation
        }

    # Sort by absolute deviation
    sorted_importance = dict(sorted(
        importance.items(),
        key=lambda x: abs(x[1]['deviation_pct']),
        reverse=True
    ))

    return sorted_importance
