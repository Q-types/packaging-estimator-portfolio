"""
Dashboard UI Components
"""
from .ui_components import (
    # Colors
    COLORS,
    SEGMENT_COLORS,
    TIER_COLORS,

    # Metric cards
    metric_card,
    simple_metric,

    # Alert cards
    alert_card,
    action_card,

    # Badges
    segment_badge,
    tier_badge,
    status_indicator,

    # Progress
    progress_bar,
    risk_gauge,

    # Cards
    info_card,
    profile_card,

    # Utilities
    format_currency,
    format_percentage,
    format_days_ago
)

__all__ = [
    'COLORS', 'SEGMENT_COLORS', 'TIER_COLORS',
    'metric_card', 'simple_metric',
    'alert_card', 'action_card',
    'segment_badge', 'tier_badge', 'status_indicator',
    'progress_bar', 'risk_gauge',
    'info_card', 'profile_card',
    'format_currency', 'format_percentage', 'format_days_ago'
]
