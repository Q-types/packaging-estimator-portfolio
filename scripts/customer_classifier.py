#!/usr/bin/env python3
"""
Customer Classifier for PackagePro Estimator

A production-ready customer segmentation model using K-Means clustering.
Classifies customers into segments based on RFM metrics, Companies House data,
and web presence features.

Example Usage:
    # In Python code:
    from customer_classifier import CustomerClassifier, train_model

    # Train a new model
    train_model(
        data_path='data/companies/company_features_preprocessed.csv',
        output_path='models/customer_segments/',
        n_clusters=5
    )

    # Load and use the classifier
    classifier = CustomerClassifier(model_path='models/customer_segments/')

    # Classify a single customer
    customer_data = {
        'recency_days': 30,
        'frequency': 12,
        'monetary_total': 50000,
        'company_age_years': 10,
        'industry_sector': 'Manufacturing'
    }
    result = classifier.predict(customer_data)
    print(f"Segment: {result['segment_name']}")

    # Batch classification
    import pandas as pd
    df = pd.read_csv('new_customers.csv')
    results = classifier.predict_batch(df)

CLI Usage:
    # Train a new model
    python customer_classifier.py train --data path/to/data.csv --output model/ --clusters 5

    # Predict for a single customer (JSON input)
    python customer_classifier.py predict --model model/ --input customer.json

    # Batch prediction
    python customer_classifier.py batch --model model/ --input customers.csv --output results.csv

Author: PackagePro Analytics Team
Version: 1.0.0
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# Segment Profile Definitions
# =============================================================================

SEGMENT_PROFILES: Dict[int, Dict[str, Any]] = {
    0: {
        "name": "High-Value Regulars",
        "description": "Premium customers with high order frequency and substantial spend. "
                       "These are your most valuable accounts with consistent ordering patterns.",
        "characteristics": {
            "monetary_range": "Top 20% (>£20,000 total)",
            "frequency_range": "10+ orders",
            "recency_range": "<180 days",
            "typical_industries": ["Manufacturing", "Wholesale & Retail", "Professional Services"]
        },
        "recommended_actions": [
            "Assign dedicated account manager",
            "Offer volume discounts and loyalty rewards",
            "Prioritize for new product launches",
            "Conduct quarterly business reviews",
            "Provide premium support SLA"
        ],
        "engagement_strategy": "Retain and grow - these customers drive profitability",
        "risk_level": "Low churn risk",
        "color": "#2E7D32"  # Green
    },
    1: {
        "name": "Growth Potential",
        "description": "Customers with moderate spend but showing growth trajectory. "
                       "Recent increases in order frequency or value indicate expansion potential.",
        "characteristics": {
            "monetary_range": "Mid-range (£5,000-£20,000 total)",
            "frequency_range": "3-10 orders",
            "recency_range": "<365 days",
            "typical_industries": ["Construction", "Administrative Services", "Information & Communication"]
        },
        "recommended_actions": [
            "Schedule business development call",
            "Offer product range expansion consultation",
            "Provide case studies from similar companies",
            "Implement cross-sell campaigns",
            "Monitor for upsell opportunities"
        ],
        "engagement_strategy": "Nurture and develop - invest in relationship building",
        "risk_level": "Medium churn risk",
        "color": "#1976D2"  # Blue
    },
    2: {
        "name": "Occasional Buyers",
        "description": "Infrequent purchasers with sporadic ordering patterns. "
                       "Typically project-based or seasonal needs.",
        "characteristics": {
            "monetary_range": "Variable (£1,000-£10,000 total)",
            "frequency_range": "1-3 orders",
            "recency_range": "180-730 days",
            "typical_industries": ["Real Estate", "Accommodation & Food", "Other Services"]
        },
        "recommended_actions": [
            "Implement re-engagement email campaigns",
            "Offer incentives for repeat orders",
            "Survey for feedback on why orders stopped",
            "Add to seasonal promotion lists",
            "Simplify reordering process"
        ],
        "engagement_strategy": "Re-activate - understand barriers and reduce friction",
        "risk_level": "High churn risk",
        "color": "#F57C00"  # Orange
    },
    3: {
        "name": "New Prospects",
        "description": "Recently acquired customers with limited order history. "
                       "Potential for development based on initial engagement.",
        "characteristics": {
            "monetary_range": "Low (£500-£5,000 total)",
            "frequency_range": "1-2 orders",
            "recency_range": "<90 days (first order recent)",
            "typical_industries": ["Various - newly onboarded"]
        },
        "recommended_actions": [
            "Send onboarding welcome sequence",
            "Schedule introductory consultation",
            "Provide product catalog and capabilities overview",
            "Assign to nurture campaign",
            "Track early engagement signals"
        ],
        "engagement_strategy": "Onboard effectively - strong first impressions drive retention",
        "risk_level": "Unknown - too early to assess",
        "color": "#7B1FA2"  # Purple
    },
    4: {
        "name": "At-Risk Dormant",
        "description": "Previously active customers who have significantly reduced "
                       "or stopped ordering. Require intervention to prevent churn.",
        "characteristics": {
            "monetary_range": "Historical (£2,000+ but declining)",
            "frequency_range": "Previous regular orders, now dormant",
            "recency_range": ">365 days since last order",
            "typical_industries": ["Various - formerly active accounts"]
        },
        "recommended_actions": [
            "Initiate win-back campaign",
            "Offer special return incentive",
            "Conduct exit survey if possible",
            "Review past orders for personalized outreach",
            "Flag for account manager intervention"
        ],
        "engagement_strategy": "Win-back - understand why they left and address concerns",
        "risk_level": "Critical - likely to churn without action",
        "color": "#C62828"  # Red
    }
}


# =============================================================================
# Feature Configuration
# =============================================================================

# Core RFM features (required for prediction)
CORE_FEATURES = [
    'recency_days',
    'frequency',
    'monetary_total',
    'monetary_mean',
    'tenure_days',
    'orders_per_year'
]

# Extended features for better clustering
EXTENDED_FEATURES = [
    # Monetary metrics
    'monetary_median', 'monetary_std', 'monetary_max', 'monetary_min',
    # Timing metrics
    'first_order_days_ago', 'avg_days_between_orders',
    # Order characteristics
    'avg_quantity', 'avg_unit_price', 'avg_margin',
    # Product mix
    'product_type_diversity', 'has_product_type_pct',
    'ptype_binder_pct', 'ptype_box_pct',
    # Operations complexity
    'avg_num_operations', 'unique_operations_used',
    # Revenue patterns
    'recent_12m_revenue', 'recent_share_pct',
    # Company data
    'company_age_years', 'officer_count', 'filing_count'
]

# Categorical features
CATEGORICAL_FEATURES = [
    'industry_sector',
    'frequency_tier',
    'value_quintile'
]

# Features that commonly have missing values (need imputation)
FEATURES_WITH_MISSING = [
    'avg_days_between_orders', 'std_days_between_orders',
    'avg_quantity', 'avg_unit_price', 'avg_margin',
    'company_age_years', 'officer_count', 'filing_count'
]


# =============================================================================
# CustomerClassifier Class
# =============================================================================

class CustomerClassifier:
    """
    Classify new customers into segments based on trained K-Means model.

    This classifier handles:
    - Loading pre-trained model artifacts
    - Preprocessing new customer data
    - Generating predictions with confidence scores
    - Batch processing for multiple customers

    Attributes:
        model_path (str): Path to the model directory
        model: Trained KMeans model
        scaler: StandardScaler for numeric features
        encoder: OneHotEncoder for categorical features
        feature_config: Configuration for feature processing
        cluster_profiles: Segment descriptions and metadata

    Example:
        >>> classifier = CustomerClassifier('models/customer_segments/')
        >>> result = classifier.predict({'recency_days': 30, 'frequency': 5})
        >>> print(result['segment_name'])
        'Growth Potential'
    """

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the classifier by loading model artifacts.

        Args:
            model_path: Path to directory containing model artifacts.
                       If None, uses default path.

        Raises:
            FileNotFoundError: If model artifacts are not found.
            ValueError: If model artifacts are corrupted or incompatible.
        """
        if model_path is None:
            # Default to a standard location
            model_path = os.path.join(
                os.path.dirname(__file__),
                '..', 'models', 'customer_segments'
            )

        self.model_path = Path(model_path)
        self._load_model_artifacts()
        logger.info(f"CustomerClassifier initialized from {self.model_path}")

    def _load_model_artifacts(self) -> None:
        """Load all model artifacts from the model directory."""
        try:
            # Load KMeans model
            model_file = self.model_path / 'model.joblib'
            if not model_file.exists():
                raise FileNotFoundError(f"Model file not found: {model_file}")
            self.model = joblib.load(model_file)
            logger.debug(f"Loaded model with {self.model.n_clusters} clusters")

            # Load scaler
            scaler_file = self.model_path / 'scaler.joblib'
            if not scaler_file.exists():
                raise FileNotFoundError(f"Scaler file not found: {scaler_file}")
            self.scaler = joblib.load(scaler_file)

            # Load encoder (optional - may not exist if no categorical features)
            encoder_file = self.model_path / 'encoder.joblib'
            if encoder_file.exists():
                self.encoder = joblib.load(encoder_file)
            else:
                self.encoder = None
                logger.debug("No encoder found - assuming no categorical features")

            # Load feature config
            config_file = self.model_path / 'feature_config.json'
            if not config_file.exists():
                raise FileNotFoundError(f"Feature config not found: {config_file}")
            with open(config_file, 'r') as f:
                self.feature_config = json.load(f)

            # Load cluster profiles
            profiles_file = self.model_path / 'cluster_profiles.json'
            if profiles_file.exists():
                with open(profiles_file, 'r') as f:
                    self.cluster_profiles = json.load(f)
            else:
                # Use default profiles
                self.cluster_profiles = {str(k): v for k, v in SEGMENT_PROFILES.items()}
                logger.warning("Using default cluster profiles")

            logger.info("Successfully loaded all model artifacts")

        except Exception as e:
            logger.error(f"Failed to load model artifacts: {e}")
            raise

    def preprocess(self, customer_data: Dict[str, Any]) -> np.ndarray:
        """
        Preprocess a single customer's data for prediction.

        Handles:
        - Feature selection (uses only trained features)
        - Missing value imputation (uses training medians)
        - Numeric scaling (StandardScaler)
        - Categorical encoding (OneHotEncoder)

        Args:
            customer_data: Dictionary with customer features.
                          Keys should match feature names from training.

        Returns:
            Preprocessed feature array ready for model prediction.

        Raises:
            ValueError: If required features are missing and cannot be imputed.
        """
        # Get feature names and imputation values from config
        numeric_features = self.feature_config.get('numeric_features', [])
        categorical_features = self.feature_config.get('categorical_features', [])
        imputation_values = self.feature_config.get('imputation_values', {})

        # Build feature vector
        numeric_values = []
        for feat in numeric_features:
            if feat in customer_data and customer_data[feat] is not None:
                value = customer_data[feat]
            elif feat in imputation_values:
                value = imputation_values[feat]
                logger.debug(f"Imputed {feat} with {value}")
            else:
                logger.warning(f"Missing feature {feat}, using 0")
                value = 0
            numeric_values.append(float(value))

        # Scale numeric features
        numeric_array = np.array(numeric_values).reshape(1, -1)
        scaled_numeric = self.scaler.transform(numeric_array)

        # Handle categorical features
        if categorical_features and self.encoder is not None:
            cat_values = []
            for feat in categorical_features:
                if feat in customer_data and customer_data[feat] is not None:
                    cat_values.append(str(customer_data[feat]))
                else:
                    # Use most common category or 'Unknown'
                    default = imputation_values.get(f"{feat}_default", 'Unknown')
                    cat_values.append(default)

            cat_array = np.array(cat_values).reshape(1, -1)
            encoded_cat = self.encoder.transform(cat_array)
            # Handle both sparse and dense outputs from encoder
            if hasattr(encoded_cat, 'toarray'):
                encoded_cat = encoded_cat.toarray()

            # Combine numeric and categorical
            preprocessed = np.hstack([scaled_numeric, encoded_cat])
        else:
            preprocessed = scaled_numeric

        return preprocessed

    def predict(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict cluster and return detailed segment information.

        Args:
            customer_data: Dictionary with customer features.

        Returns:
            Dictionary containing:
            - cluster_id: Integer cluster assignment (0 to n_clusters-1)
            - segment_name: Human-readable segment name
            - segment_description: Detailed description
            - confidence_score: Float 0-1 indicating prediction confidence
            - distance_to_centroid: Euclidean distance to cluster center
            - recommended_actions: List of suggested actions
            - all_distances: Distances to all cluster centroids

        Example:
            >>> result = classifier.predict({'recency_days': 30, 'frequency': 5})
            >>> print(result['segment_name'])
            'Growth Potential'
            >>> print(result['confidence_score'])
            0.85
        """
        # Preprocess the input
        preprocessed = self.preprocess(customer_data)

        # Get prediction
        cluster_id = int(self.model.predict(preprocessed)[0])

        # Calculate distances to all centroids
        centroids = self.model.cluster_centers_
        distances = np.linalg.norm(centroids - preprocessed, axis=1)
        distance_to_assigned = distances[cluster_id]

        # Calculate confidence score (inverse of relative distance)
        # Higher confidence when distance to assigned cluster is much smaller than others
        min_distance = distances.min()
        sorted_distances = np.sort(distances)
        if len(sorted_distances) > 1:
            # Confidence based on ratio of best to second-best distance
            confidence = 1 - (min_distance / (sorted_distances[1] + 1e-10))
            confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
        else:
            confidence = 1.0

        # Get segment profile
        profile = self.cluster_profiles.get(str(cluster_id), SEGMENT_PROFILES.get(cluster_id, {}))

        return {
            'cluster_id': cluster_id,
            'segment_name': profile.get('name', f'Segment {cluster_id}'),
            'segment_description': profile.get('description', ''),
            'confidence_score': round(confidence, 3),
            'distance_to_centroid': round(float(distance_to_assigned), 4),
            'recommended_actions': profile.get('recommended_actions', []),
            'engagement_strategy': profile.get('engagement_strategy', ''),
            'risk_level': profile.get('risk_level', 'Unknown'),
            'all_distances': {str(i): round(float(d), 4) for i, d in enumerate(distances)},
            'characteristics': profile.get('characteristics', {}),
            'color': profile.get('color', '#808080')
        }

    def predict_batch(self, customers_df: pd.DataFrame) -> pd.DataFrame:
        """
        Classify multiple customers efficiently.

        Args:
            customers_df: DataFrame with customer features.
                         Each row is a customer, columns are features.

        Returns:
            DataFrame with original data plus:
            - cluster_id: Assigned cluster
            - segment_name: Human-readable segment name
            - confidence_score: Prediction confidence
            - distance_to_centroid: Distance to cluster center

        Example:
            >>> df = pd.read_csv('customers.csv')
            >>> results = classifier.predict_batch(df)
            >>> results.to_csv('classified_customers.csv')
        """
        logger.info(f"Batch classifying {len(customers_df)} customers")

        results = []
        for idx, row in customers_df.iterrows():
            customer_data = row.to_dict()
            try:
                prediction = self.predict(customer_data)
                results.append({
                    'index': idx,
                    'cluster_id': prediction['cluster_id'],
                    'segment_name': prediction['segment_name'],
                    'confidence_score': prediction['confidence_score'],
                    'distance_to_centroid': prediction['distance_to_centroid'],
                    'risk_level': prediction['risk_level']
                })
            except Exception as e:
                logger.warning(f"Failed to classify customer at index {idx}: {e}")
                results.append({
                    'index': idx,
                    'cluster_id': -1,
                    'segment_name': 'Classification Error',
                    'confidence_score': 0.0,
                    'distance_to_centroid': float('inf'),
                    'risk_level': 'Unknown'
                })

        results_df = pd.DataFrame(results).set_index('index')

        # Merge with original data
        output_df = customers_df.copy()
        for col in ['cluster_id', 'segment_name', 'confidence_score',
                    'distance_to_centroid', 'risk_level']:
            output_df[col] = results_df[col]

        logger.info(f"Batch classification complete. Distribution: "
                   f"{output_df['segment_name'].value_counts().to_dict()}")

        return output_df

    def get_segment_profile(self, cluster_id: int) -> Dict[str, Any]:
        """
        Get the detailed profile/description of a segment.

        Args:
            cluster_id: Integer cluster ID (0 to n_clusters-1)

        Returns:
            Dictionary with segment profile including:
            - name, description, characteristics
            - recommended_actions, engagement_strategy
            - risk_level, color

        Raises:
            ValueError: If cluster_id is out of range.
        """
        if cluster_id < 0 or cluster_id >= self.model.n_clusters:
            raise ValueError(
                f"cluster_id must be between 0 and {self.model.n_clusters - 1}"
            )

        return self.cluster_profiles.get(str(cluster_id),
                                         SEGMENT_PROFILES.get(cluster_id, {}))

    def get_all_profiles(self) -> Dict[int, Dict[str, Any]]:
        """
        Get profiles for all segments.

        Returns:
            Dictionary mapping cluster_id to segment profile.
        """
        return {int(k): v for k, v in self.cluster_profiles.items()}


# =============================================================================
# Model Training Function
# =============================================================================

def train_model(
    data_path: str,
    output_path: str,
    n_clusters: int = 5,
    feature_subset: Optional[List[str]] = None,
    random_state: int = 42
) -> Tuple[KMeans, Dict[str, Any]]:
    """
    Train and save the clustering model with all artifacts.

    This function:
    1. Loads and validates input data
    2. Selects and prepares features
    3. Handles missing values
    4. Fits StandardScaler and KMeans model
    5. Generates cluster profiles based on data characteristics
    6. Saves all artifacts for deployment

    Args:
        data_path: Path to CSV file with company features.
        output_path: Directory to save model artifacts.
        n_clusters: Number of clusters for K-Means (default: 5).
        feature_subset: Optional list of features to use.
                       If None, uses CORE_FEATURES + EXTENDED_FEATURES.
        random_state: Random seed for reproducibility.

    Returns:
        Tuple of (trained_model, training_metrics)

    Raises:
        FileNotFoundError: If data_path doesn't exist.
        ValueError: If data is invalid or insufficient.

    Example:
        >>> model, metrics = train_model(
        ...     'data/companies/company_features_preprocessed.csv',
        ...     'models/customer_segments/',
        ...     n_clusters=5
        ... )
        >>> print(f"Inertia: {metrics['inertia']}")
    """
    logger.info(f"Starting model training with {n_clusters} clusters")

    # Load data
    data_path = Path(data_path)
    if not data_path.exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")

    df = pd.read_csv(data_path)
    logger.info(f"Loaded {len(df)} companies from {data_path}")

    # Determine features to use
    if feature_subset is None:
        # Use core + extended features that exist in the data
        all_potential_features = CORE_FEATURES + EXTENDED_FEATURES
        numeric_features = [f for f in all_potential_features if f in df.columns]
    else:
        numeric_features = [f for f in feature_subset if f in df.columns]

    # Check for categorical features
    categorical_features = [f for f in CATEGORICAL_FEATURES if f in df.columns]

    logger.info(f"Using {len(numeric_features)} numeric features")
    logger.info(f"Using {len(categorical_features)} categorical features")

    # Prepare numeric data
    X_numeric = df[numeric_features].copy()

    # Calculate imputation values (medians) before imputation
    imputation_values = {}
    for col in numeric_features:
        median_val = X_numeric[col].median()
        if pd.isna(median_val):
            median_val = 0.0
        imputation_values[col] = float(median_val)

    # Impute missing values with median
    for col in numeric_features:
        X_numeric[col] = X_numeric[col].fillna(imputation_values[col])

    # Scale numeric features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_numeric)

    # Handle categorical features
    encoder = None
    if categorical_features:
        X_cat = df[categorical_features].fillna('Unknown').astype(str)
        encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
        X_encoded = encoder.fit_transform(X_cat)

        # Store default categories for imputation
        for feat in categorical_features:
            mode_val = df[feat].mode()
            imputation_values[f"{feat}_default"] = str(mode_val.iloc[0]) if len(mode_val) > 0 else 'Unknown'

        # Combine features
        X_final = np.hstack([X_scaled, X_encoded])
        logger.info(f"Final feature matrix shape: {X_final.shape}")
    else:
        X_final = X_scaled

    # Train K-Means model
    logger.info(f"Training K-Means with {n_clusters} clusters...")
    model = KMeans(
        n_clusters=n_clusters,
        random_state=random_state,
        n_init=10,
        max_iter=300
    )
    model.fit(X_final)

    # Get cluster assignments
    labels = model.labels_

    # Calculate training metrics
    inertia = model.inertia_

    # Calculate silhouette score if sklearn has it
    try:
        from sklearn.metrics import silhouette_score
        silhouette = silhouette_score(X_final, labels)
    except Exception:
        silhouette = None

    logger.info(f"Training complete. Inertia: {inertia:.2f}")
    if silhouette:
        logger.info(f"Silhouette Score: {silhouette:.3f}")

    # Generate cluster profiles based on data characteristics
    cluster_profiles = _generate_cluster_profiles(df, labels, numeric_features, n_clusters)

    # Create output directory
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    # Save artifacts
    logger.info(f"Saving model artifacts to {output_path}")

    # Save model
    joblib.dump(model, output_path / 'model.joblib')

    # Save scaler
    joblib.dump(scaler, output_path / 'scaler.joblib')

    # Save encoder
    if encoder is not None:
        joblib.dump(encoder, output_path / 'encoder.joblib')

    # Save feature config
    feature_config = {
        'numeric_features': numeric_features,
        'categorical_features': categorical_features,
        'imputation_values': imputation_values,
        'n_clusters': n_clusters,
        'training_date': datetime.now().isoformat(),
        'training_samples': len(df)
    }
    with open(output_path / 'feature_config.json', 'w') as f:
        json.dump(feature_config, f, indent=2)

    # Save cluster profiles
    with open(output_path / 'cluster_profiles.json', 'w') as f:
        json.dump(cluster_profiles, f, indent=2)

    # Save cluster distribution
    cluster_dist = pd.Series(labels).value_counts().sort_index().to_dict()

    # Create metrics summary
    metrics = {
        'n_clusters': n_clusters,
        'n_samples': len(df),
        'n_features': X_final.shape[1],
        'inertia': float(inertia),
        'silhouette_score': float(silhouette) if silhouette else None,
        'cluster_distribution': cluster_dist,
        'training_date': datetime.now().isoformat()
    }

    with open(output_path / 'training_metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)

    logger.info("Model training and artifact saving complete!")
    return model, metrics


def _generate_cluster_profiles(
    df: pd.DataFrame,
    labels: np.ndarray,
    numeric_features: List[str],
    n_clusters: int
) -> Dict[str, Dict[str, Any]]:
    """
    Generate cluster profiles based on data characteristics.

    Analyzes each cluster to determine its characteristics and
    assigns appropriate segment names and descriptions.
    """
    df_with_clusters = df.copy()
    df_with_clusters['cluster'] = labels

    # Calculate cluster statistics
    cluster_stats = {}
    for cluster_id in range(n_clusters):
        cluster_data = df_with_clusters[df_with_clusters['cluster'] == cluster_id]
        stats = {}

        # Key metrics for characterization
        if 'monetary_total' in df.columns:
            stats['avg_monetary'] = cluster_data['monetary_total'].mean()
            stats['median_monetary'] = cluster_data['monetary_total'].median()
        if 'frequency' in df.columns:
            stats['avg_frequency'] = cluster_data['frequency'].mean()
        if 'recency_days' in df.columns:
            stats['avg_recency'] = cluster_data['recency_days'].mean()
        if 'is_churned' in df.columns:
            stats['churn_rate'] = cluster_data['is_churned'].mean()
        if 'is_active_12m' in df.columns:
            stats['active_rate'] = cluster_data['is_active_12m'].mean()

        stats['count'] = len(cluster_data)
        cluster_stats[cluster_id] = stats

    # Rank clusters by key metrics to assign profiles
    # Sort by monetary value to identify high vs low value segments
    sorted_by_monetary = sorted(
        cluster_stats.items(),
        key=lambda x: x[1].get('avg_monetary', 0),
        reverse=True
    )

    profiles = {}
    profile_assignments = {}

    # Assign profiles based on characteristics
    for rank, (cluster_id, stats) in enumerate(sorted_by_monetary):
        avg_monetary = stats.get('avg_monetary', 0)
        avg_frequency = stats.get('avg_frequency', 1)
        avg_recency = stats.get('avg_recency', 365)
        active_rate = stats.get('active_rate', 0.5)

        # Determine segment based on characteristics
        if avg_monetary > 15000 and avg_frequency > 5:
            profile_idx = 0  # High-Value Regulars
        elif avg_recency > 500 and active_rate < 0.3:
            profile_idx = 4  # At-Risk Dormant
        elif avg_frequency <= 2 and avg_recency < 200:
            profile_idx = 3  # New Prospects
        elif avg_frequency <= 3:
            profile_idx = 2  # Occasional Buyers
        else:
            profile_idx = 1  # Growth Potential

        # Avoid duplicate assignments
        while profile_idx in profile_assignments.values():
            profile_idx = (profile_idx + 1) % 5

        profile_assignments[cluster_id] = profile_idx

    # Build final profiles
    for cluster_id in range(n_clusters):
        profile_idx = profile_assignments.get(cluster_id, cluster_id % 5)
        base_profile = SEGMENT_PROFILES.get(profile_idx, SEGMENT_PROFILES[0]).copy()

        # Add cluster-specific statistics
        stats = cluster_stats.get(cluster_id, {})
        base_profile['cluster_stats'] = {
            'count': stats.get('count', 0),
            'avg_monetary': round(stats.get('avg_monetary', 0), 2),
            'avg_frequency': round(stats.get('avg_frequency', 0), 2),
            'avg_recency_days': round(stats.get('avg_recency', 0), 1)
        }

        profiles[str(cluster_id)] = base_profile

    return profiles


# =============================================================================
# Validation Utilities
# =============================================================================

def validate_customer_data(
    customer_data: Dict[str, Any],
    required_features: Optional[List[str]] = None
) -> Tuple[bool, List[str]]:
    """
    Validate that customer data contains required fields.

    Args:
        customer_data: Dictionary with customer features.
        required_features: List of required feature names.
                          Defaults to CORE_FEATURES.

    Returns:
        Tuple of (is_valid, list_of_missing_features)
    """
    if required_features is None:
        required_features = CORE_FEATURES

    missing = []
    for feat in required_features:
        if feat not in customer_data or customer_data[feat] is None:
            missing.append(feat)

    return len(missing) == 0, missing


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Customer Segmentation Classifier',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Train a new model:
    python customer_classifier.py train --data data/companies/company_features_preprocessed.csv --output models/

  Predict for a single customer:
    python customer_classifier.py predict --model models/ --input customer.json

  Batch prediction:
    python customer_classifier.py batch --model models/ --input customers.csv --output results.csv
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Train command
    train_parser = subparsers.add_parser('train', help='Train a new model')
    train_parser.add_argument(
        '--data', '-d', required=True,
        help='Path to training data CSV'
    )
    train_parser.add_argument(
        '--output', '-o', required=True,
        help='Output directory for model artifacts'
    )
    train_parser.add_argument(
        '--clusters', '-c', type=int, default=5,
        help='Number of clusters (default: 5)'
    )
    train_parser.add_argument(
        '--seed', type=int, default=42,
        help='Random seed for reproducibility'
    )

    # Predict command
    predict_parser = subparsers.add_parser('predict', help='Predict for a single customer')
    predict_parser.add_argument(
        '--model', '-m', required=True,
        help='Path to model directory'
    )
    predict_parser.add_argument(
        '--input', '-i', required=True,
        help='Path to JSON file with customer data'
    )
    predict_parser.add_argument(
        '--output', '-o',
        help='Output JSON file (optional, prints to stdout if not specified)'
    )

    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Batch prediction')
    batch_parser.add_argument(
        '--model', '-m', required=True,
        help='Path to model directory'
    )
    batch_parser.add_argument(
        '--input', '-i', required=True,
        help='Path to input CSV file'
    )
    batch_parser.add_argument(
        '--output', '-o', required=True,
        help='Path to output CSV file'
    )

    # Profile command
    profile_parser = subparsers.add_parser('profile', help='Get segment profile')
    profile_parser.add_argument(
        '--model', '-m', required=True,
        help='Path to model directory'
    )
    profile_parser.add_argument(
        '--cluster', '-c', type=int,
        help='Cluster ID to get profile for (optional, shows all if not specified)'
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # Execute command
    if args.command == 'train':
        logger.info("Starting training...")
        try:
            model, metrics = train_model(
                data_path=args.data,
                output_path=args.output,
                n_clusters=args.clusters,
                random_state=args.seed
            )
            print(f"\nTraining complete!")
            print(f"  Samples: {metrics['n_samples']}")
            print(f"  Features: {metrics['n_features']}")
            print(f"  Clusters: {metrics['n_clusters']}")
            print(f"  Inertia: {metrics['inertia']:.2f}")
            if metrics['silhouette_score']:
                print(f"  Silhouette: {metrics['silhouette_score']:.3f}")
            print(f"\nCluster distribution:")
            for k, v in metrics['cluster_distribution'].items():
                print(f"  Cluster {k}: {v} companies")
            print(f"\nModel saved to: {args.output}")
        except Exception as e:
            logger.error(f"Training failed: {e}")
            sys.exit(1)

    elif args.command == 'predict':
        try:
            # Load customer data
            with open(args.input, 'r') as f:
                customer_data = json.load(f)

            # Initialize classifier
            classifier = CustomerClassifier(args.model)

            # Make prediction
            result = classifier.predict(customer_data)

            # Output
            output_json = json.dumps(result, indent=2)
            if args.output:
                with open(args.output, 'w') as f:
                    f.write(output_json)
                print(f"Result saved to: {args.output}")
            else:
                print(output_json)

        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            sys.exit(1)

    elif args.command == 'batch':
        try:
            # Load data
            df = pd.read_csv(args.input)
            logger.info(f"Loaded {len(df)} customers from {args.input}")

            # Initialize classifier
            classifier = CustomerClassifier(args.model)

            # Batch predict
            results = classifier.predict_batch(df)

            # Save results
            results.to_csv(args.output, index=False)
            print(f"\nBatch classification complete!")
            print(f"  Input: {len(df)} customers")
            print(f"  Output saved to: {args.output}")
            print(f"\nSegment distribution:")
            for name, count in results['segment_name'].value_counts().items():
                print(f"  {name}: {count}")

        except Exception as e:
            logger.error(f"Batch prediction failed: {e}")
            sys.exit(1)

    elif args.command == 'profile':
        try:
            classifier = CustomerClassifier(args.model)

            if args.cluster is not None:
                profile = classifier.get_segment_profile(args.cluster)
                print(json.dumps({args.cluster: profile}, indent=2))
            else:
                profiles = classifier.get_all_profiles()
                print(json.dumps(profiles, indent=2))

        except Exception as e:
            logger.error(f"Failed to get profile: {e}")
            sys.exit(1)


# =============================================================================
# Tests
# =============================================================================

def run_tests():
    """Run basic tests for key functions."""
    import tempfile

    print("Running tests...")

    # Test 1: Validation
    print("\n[Test 1] validate_customer_data")
    test_data = {'recency_days': 30, 'frequency': 5}
    is_valid, missing = validate_customer_data(test_data, ['recency_days', 'frequency'])
    assert is_valid, f"Validation failed: {missing}"
    print("  PASS: Valid data recognized")

    is_valid, missing = validate_customer_data(test_data, ['recency_days', 'monetary_total'])
    assert not is_valid, "Should have detected missing field"
    assert 'monetary_total' in missing
    print("  PASS: Missing field detected")

    # Test 2: Training (with synthetic data)
    print("\n[Test 2] train_model")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create synthetic data
        np.random.seed(42)
        n_samples = 100
        synthetic_df = pd.DataFrame({
            'company': [f'Company_{i}' for i in range(n_samples)],
            'recency_days': np.random.randint(1, 1000, n_samples),
            'frequency': np.random.randint(1, 50, n_samples),
            'monetary_total': np.random.uniform(100, 100000, n_samples),
            'monetary_mean': np.random.uniform(100, 5000, n_samples),
            'tenure_days': np.random.randint(0, 2000, n_samples),
            'orders_per_year': np.random.uniform(0.1, 10, n_samples)
        })

        data_path = os.path.join(tmpdir, 'test_data.csv')
        synthetic_df.to_csv(data_path, index=False)

        model_path = os.path.join(tmpdir, 'model')

        model, metrics = train_model(
            data_path=data_path,
            output_path=model_path,
            n_clusters=3
        )

        assert model is not None
        assert metrics['n_clusters'] == 3
        assert os.path.exists(os.path.join(model_path, 'model.joblib'))
        print("  PASS: Model trained and saved")

        # Test 3: Prediction
        print("\n[Test 3] CustomerClassifier.predict")
        classifier = CustomerClassifier(model_path)

        result = classifier.predict({
            'recency_days': 30,
            'frequency': 10,
            'monetary_total': 50000,
            'monetary_mean': 5000,
            'tenure_days': 500,
            'orders_per_year': 5
        })

        assert 'cluster_id' in result
        assert 'segment_name' in result
        assert 'confidence_score' in result
        assert 0 <= result['confidence_score'] <= 1
        print(f"  PASS: Prediction returned cluster {result['cluster_id']}")

        # Test 4: Batch prediction
        print("\n[Test 4] CustomerClassifier.predict_batch")
        batch_results = classifier.predict_batch(synthetic_df.head(10))
        assert 'cluster_id' in batch_results.columns
        assert 'segment_name' in batch_results.columns
        assert len(batch_results) == 10
        print("  PASS: Batch prediction complete")

    print("\n" + "="*50)
    print("All tests passed!")
    print("="*50)


if __name__ == "__main__":
    # Check for test flag
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        run_tests()
    else:
        main()
