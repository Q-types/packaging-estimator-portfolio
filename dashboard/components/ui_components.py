"""
Reusable UI Components
Consistent styling and functionality across the dashboard
"""
import streamlit as st
from typing import Dict, List, Optional, Any

# Import centralized segment colors
from services.data_loader import SEGMENT_COLORS


# =============================================================================
# COLOR CONSTANTS
# =============================================================================

COLORS = {
    # Tier colors
    'hot': '#C62828',
    'warm': '#F57C00',
    'cool': '#1976D2',
    'cold': '#9E9E9E',

    # Status colors
    'critical': '#F44336',
    'warning': '#FF9800',
    'success': '#4CAF50',
    'info': '#1976D2',
    'neutral': '#666666',

    # UI colors
    'primary': '#1E3A5F',
    'secondary': '#667eea',
    'background': '#f8f9fa',
    'card_bg': '#ffffff',
    'border': '#e0e0e0'
}

# SEGMENT_COLORS imported from services.data_loader (single source of truth)

TIER_COLORS = {
    'Hot': COLORS['hot'],
    'Warm': COLORS['warm'],
    'Cool': COLORS['cool'],
    'Cold': COLORS['cold']
}


# =============================================================================
# METRIC CARDS
# =============================================================================

def metric_card(
    value: str,
    label: str,
    color: str = COLORS['primary'],
    icon: str = None,
    delta: str = None,
    delta_color: str = None
) -> None:
    """Render a styled metric card"""
    icon_html = f'<span style="font-size: 1.5rem; margin-right: 0.5rem;">{icon}</span>' if icon else ''
    delta_html = ''
    if delta:
        d_color = delta_color or (COLORS['success'] if '+' in delta else COLORS['critical'])
        delta_html = f'<div style="font-size: 0.75rem; color: {d_color}; margin-top: 0.25rem;">{delta}</div>'

    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {color} 0%, {_darken_color(color)} 100%);
        padding: 1.25rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    ">
        {icon_html}
        <div style="font-size: 2rem; font-weight: 700; margin: 0.25rem 0;">{value}</div>
        <div style="font-size: 0.85rem; opacity: 0.9;">{label}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def simple_metric(value: str, label: str, color: str = COLORS['primary']) -> None:
    """Render a simple inline metric"""
    st.markdown(f"""
    <div style="text-align: center; padding: 0.75rem;">
        <div style="font-size: 1.5rem; font-weight: bold; color: {color};">{value}</div>
        <div style="font-size: 0.75rem; color: #666;">{label}</div>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# ALERT CARDS
# =============================================================================

def alert_card(
    title: str,
    content: str,
    alert_type: str = 'info',
    action_label: str = None,
    action_key: str = None
) -> bool:
    """Render an alert card with optional action button"""
    colors = {
        'critical': (COLORS['critical'], '#FFF5F5'),
        'warning': (COLORS['warning'], '#FFF8E1'),
        'success': (COLORS['success'], '#E8F5E9'),
        'info': (COLORS['info'], '#E3F2FD')
    }
    border_color, bg_color = colors.get(alert_type, colors['info'])

    st.markdown(f"""
    <div style="
        border-left: 4px solid {border_color};
        background: {bg_color};
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 0.75rem;
    ">
        <strong style="color: {border_color};">{title}</strong><br/>
        <small style="color: #666;">{content}</small>
    </div>
    """, unsafe_allow_html=True)

    if action_label and action_key:
        return st.button(action_label, key=action_key, use_container_width=True)
    return False


def action_card(
    company: str,
    metrics: Dict[str, str],
    alert_type: str = 'info',
    actions: List[str] = None
) -> Optional[str]:
    """Render an action card for a customer/prospect"""
    colors = {
        'critical': (COLORS['critical'], '#FFF5F5'),
        'warning': (COLORS['warning'], '#FFF8E1'),
        'success': (COLORS['success'], '#E8F5E9'),
        'info': (COLORS['info'], '#E3F2FD')
    }
    border_color, bg_color = colors.get(alert_type, colors['info'])

    metrics_html = ' | '.join([f'{k}: {v}' for k, v in metrics.items()])

    st.markdown(f"""
    <div style="
        border-left: 4px solid {border_color};
        background: {bg_color};
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin-bottom: 0.75rem;
    ">
        <strong>{company}</strong><br/>
        <small style="color: #666;">{metrics_html}</small>
    </div>
    """, unsafe_allow_html=True)

    if actions:
        cols = st.columns(len(actions))
        for col, action in zip(cols, actions):
            with col:
                if st.button(action, key=f"{company}_{action}", use_container_width=True):
                    return action
    return None


# =============================================================================
# SEGMENT & TIER BADGES
# =============================================================================

def segment_badge(segment_id: int, segment_name: str) -> None:
    """Render a segment badge"""
    color = SEGMENT_COLORS.get(segment_id, COLORS['neutral'])
    st.markdown(f"""
    <span style="
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        background: {color};
        color: white;
        font-size: 0.8rem;
        font-weight: 600;
    ">{segment_name}</span>
    """, unsafe_allow_html=True)


def tier_badge(tier: str) -> None:
    """Render a prospect tier badge"""
    color = TIER_COLORS.get(tier, COLORS['neutral'])
    st.markdown(f"""
    <span style="
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        background: {color};
        color: white;
        font-size: 0.8rem;
        font-weight: 600;
    ">{tier}</span>
    """, unsafe_allow_html=True)


def status_indicator(status: str, label: str = None) -> None:
    """Render a status indicator dot"""
    status_colors = {
        'critical': COLORS['critical'],
        'warning': COLORS['warning'],
        'healthy': COLORS['success'],
        'info': COLORS['info']
    }
    color = status_colors.get(status, COLORS['neutral'])
    label_html = f'<span style="margin-left: 0.5rem;">{label}</span>' if label else ''

    st.markdown(f"""
    <span style="
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: {color};
        animation: {status == 'critical' and 'pulse 2s infinite' or 'none'};
    "></span>{label_html}
    """, unsafe_allow_html=True)


# =============================================================================
# PROGRESS & GAUGES
# =============================================================================

def progress_bar(value: float, max_value: float = 100, label: str = None, color: str = None) -> None:
    """Render a custom progress bar"""
    pct = min(100, (value / max_value) * 100) if max_value > 0 else 0

    if color is None:
        if pct >= 75:
            color = COLORS['success']
        elif pct >= 50:
            color = COLORS['warning']
        else:
            color = COLORS['critical']

    label_html = f'<div style="font-size: 0.75rem; color: #666; margin-bottom: 0.25rem;">{label}</div>' if label else ''

    st.markdown(f"""
    {label_html}
    <div style="
        background: #e0e0e0;
        border-radius: 10px;
        height: 8px;
        overflow: hidden;
    ">
        <div style="
            width: {pct}%;
            height: 100%;
            background: {color};
            border-radius: 10px;
        "></div>
    </div>
    <div style="font-size: 0.7rem; color: #666; text-align: right;">{value:.0f}/{max_value:.0f}</div>
    """, unsafe_allow_html=True)


def risk_gauge(risk_value: float, label: str = "Churn Risk") -> None:
    """Render a risk gauge"""
    if risk_value >= 75:
        color = COLORS['critical']
        status = "Critical"
    elif risk_value >= 50:
        color = COLORS['warning']
        status = "At Risk"
    elif risk_value >= 25:
        color = COLORS['info']
        status = "Moderate"
    else:
        color = COLORS['success']
        status = "Low"

    st.markdown(f"""
    <div style="text-align: center; padding: 1rem;">
        <div style="font-size: 0.85rem; color: #666; margin-bottom: 0.5rem;">{label}</div>
        <div style="
            width: 80px;
            height: 80px;
            border-radius: 50%;
            background: conic-gradient({color} {risk_value}%, #e0e0e0 {risk_value}%);
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto;
        ">
            <div style="
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background: white;
                display: flex;
                align-items: center;
                justify-content: center;
                flex-direction: column;
            ">
                <span style="font-size: 1.25rem; font-weight: bold; color: {color};">{risk_value:.0f}%</span>
            </div>
        </div>
        <div style="font-size: 0.75rem; color: {color}; font-weight: bold; margin-top: 0.5rem;">{status}</div>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# CARDS & CONTAINERS
# =============================================================================

def info_card(title: str, content: Dict[str, Any], color: str = COLORS['primary']) -> None:
    """Render an info card with key-value pairs"""
    content_html = ''.join([
        f'<div style="display: flex; justify-content: space-between; padding: 0.25rem 0; border-bottom: 1px solid #f0f0f0;"><span style="color: #666;">{k}</span><strong>{v}</strong></div>'
        for k, v in content.items()
    ])

    st.markdown(f"""
    <div style="
        border: 1px solid {COLORS['border']};
        border-top: 4px solid {color};
        border-radius: 8px;
        padding: 1rem;
        background: white;
    ">
        <h4 style="margin: 0 0 1rem 0; color: {color};">{title}</h4>
        {content_html}
    </div>
    """, unsafe_allow_html=True)


def profile_card(
    name: str,
    segment: str,
    segment_color: str,
    metrics: Dict[str, str],
    risk_level: str = None
) -> None:
    """Render a customer profile card"""
    risk_colors = {
        'Critical': COLORS['critical'],
        'High': COLORS['warning'],
        'Medium': COLORS['info'],
        'Low': COLORS['success'],
        'Unknown': COLORS['neutral']
    }
    risk_color = risk_colors.get(risk_level, COLORS['neutral'])

    metrics_html = ''.join([
        f'<div style="text-align: center;"><div style="font-size: 1.25rem; font-weight: bold;">{v}</div><div style="font-size: 0.7rem; color: #666;">{k}</div></div>'
        for k, v in metrics.items()
    ])

    st.markdown(f"""
    <div style="
        border: 2px solid {segment_color};
        border-radius: 12px;
        padding: 1.5rem;
        background: white;
    ">
        <h3 style="margin: 0 0 0.5rem 0; color: {COLORS['primary']};">{name}</h3>
        <span style="
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            background: {segment_color};
            color: white;
            font-size: 0.8rem;
            font-weight: 600;
        ">{segment}</span>
        <span style="
            display: inline-block;
            padding: 0.25rem 0.75rem;
            margin-left: 0.5rem;
            border-radius: 20px;
            background: {risk_color};
            color: white;
            font-size: 0.75rem;
        ">{risk_level or 'Unknown'} Risk</span>

        <div style="
            display: flex;
            justify-content: space-around;
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid {COLORS['border']};
        ">
            {metrics_html}
        </div>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def _darken_color(hex_color: str, factor: float = 0.2) -> str:
    """Darken a hex color by a factor"""
    hex_color = hex_color.lstrip('#')
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    darkened = tuple(int(c * (1 - factor)) for c in rgb)
    return f'#{darkened[0]:02x}{darkened[1]:02x}{darkened[2]:02x}'


def format_currency(value: float, symbol: str = '£') -> str:
    """Format a number as currency"""
    if abs(value) >= 1_000_000:
        return f"{symbol}{value/1_000_000:.1f}M"
    elif abs(value) >= 1_000:
        return f"{symbol}{value/1_000:.1f}K"
    else:
        return f"{symbol}{value:,.0f}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format a number as percentage"""
    return f"{value:.{decimals}f}%"


def format_days_ago(days: float) -> str:
    """Format days as human-readable time ago"""
    if days < 1:
        return "Today"
    elif days < 7:
        return f"{int(days)} days ago"
    elif days < 30:
        weeks = int(days / 7)
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    elif days < 365:
        months = int(days / 30)
        return f"{months} month{'s' if months > 1 else ''} ago"
    else:
        years = int(days / 365)
        return f"{years} year{'s' if years > 1 else ''} ago"
