"""
Activity Tracker Service
Tracks user actions, manages session state, and provides activity reports
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pathlib import Path
import json

# Activity log file path
ACTIVITY_LOG_PATH = Path(__file__).parent.parent.parent / "data" / "activity_log.json"


# =============================================================================
# SESSION STATE MANAGEMENT
# =============================================================================

def init_session_state():
    """Initialize session state for action tracking"""
    if 'actions' not in st.session_state:
        st.session_state.actions = []

    if 'session_start' not in st.session_state:
        st.session_state.session_start = datetime.now().isoformat()

    if 'current_user' not in st.session_state:
        st.session_state.current_user = "Sales Team"

    if 'viewed_customers' not in st.session_state:
        st.session_state.viewed_customers = set()

    if 'viewed_prospects' not in st.session_state:
        st.session_state.viewed_prospects = set()

    if 'filters_applied' not in st.session_state:
        st.session_state.filters_applied = {}


def get_session_stats() -> Dict:
    """Get statistics for the current session"""
    init_session_state()

    actions = st.session_state.actions
    session_start = datetime.fromisoformat(st.session_state.session_start)

    # Count by action type
    action_counts = {}
    for action in actions:
        action_type = action.get('type', 'unknown')
        action_counts[action_type] = action_counts.get(action_type, 0) + 1

    return {
        'session_duration': str(datetime.now() - session_start).split('.')[0],
        'total_actions': len(actions),
        'actions_by_type': action_counts,
        'customers_viewed': len(st.session_state.viewed_customers),
        'prospects_viewed': len(st.session_state.viewed_prospects)
    }


# =============================================================================
# ACTION LOGGING
# =============================================================================

def log_action(
    action_type: str,
    target: str,
    details: Dict = None,
    notes: str = None
) -> Dict:
    """Log a user action"""
    init_session_state()

    action = {
        'id': len(st.session_state.actions) + 1,
        'timestamp': datetime.now().isoformat(),
        'type': action_type,
        'target': target,
        'details': details or {},
        'notes': notes,
        'user': st.session_state.current_user
    }

    st.session_state.actions.append(action)

    # Also persist to file
    _persist_action(action)

    return action


def log_call(company: str, outcome: str = None, notes: str = None) -> Dict:
    """Log a customer call"""
    return log_action(
        action_type='call',
        target=company,
        details={'outcome': outcome},
        notes=notes
    )


def log_email(company: str, template: str = None, notes: str = None) -> Dict:
    """Log an email sent"""
    return log_action(
        action_type='email',
        target=company,
        details={'template': template},
        notes=notes
    )


def log_follow_up(company: str, follow_up_date: str, notes: str = None) -> Dict:
    """Log a scheduled follow-up"""
    return log_action(
        action_type='follow_up',
        target=company,
        details={'scheduled_date': follow_up_date},
        notes=notes
    )


def log_quote(company: str, value: float = None, notes: str = None) -> Dict:
    """Log a quote generated"""
    return log_action(
        action_type='quote',
        target=company,
        details={'value': value},
        notes=notes
    )


def log_view(entity_type: str, entity_name: str) -> None:
    """Log a view of customer or prospect"""
    init_session_state()

    if entity_type == 'customer':
        st.session_state.viewed_customers.add(entity_name)
    elif entity_type == 'prospect':
        st.session_state.viewed_prospects.add(entity_name)


def log_export(export_type: str, record_count: int) -> Dict:
    """Log an export action"""
    return log_action(
        action_type='export',
        target=export_type,
        details={'record_count': record_count}
    )


# =============================================================================
# ACTION RETRIEVAL
# =============================================================================

def get_recent_actions(limit: int = 10) -> List[Dict]:
    """Get most recent actions"""
    init_session_state()
    return list(reversed(st.session_state.actions[-limit:]))


def get_actions_by_type(action_type: str) -> List[Dict]:
    """Get all actions of a specific type"""
    init_session_state()
    return [a for a in st.session_state.actions if a['type'] == action_type]


def get_actions_for_company(company: str) -> List[Dict]:
    """Get all actions for a specific company"""
    init_session_state()
    return [a for a in st.session_state.actions if a['target'] == company]


def get_todays_actions() -> List[Dict]:
    """Get actions from today"""
    init_session_state()
    today = datetime.now().date()
    return [
        a for a in st.session_state.actions
        if datetime.fromisoformat(a['timestamp']).date() == today
    ]


def get_pending_follow_ups() -> List[Dict]:
    """Get scheduled follow-ups that haven't happened yet"""
    init_session_state()
    today = datetime.now().date()
    follow_ups = get_actions_by_type('follow_up')

    pending = []
    for fu in follow_ups:
        scheduled = fu['details'].get('scheduled_date')
        if scheduled:
            try:
                scheduled_date = datetime.fromisoformat(scheduled).date()
                if scheduled_date >= today:
                    pending.append(fu)
            except:
                pass

    return sorted(pending, key=lambda x: x['details'].get('scheduled_date', ''))


# =============================================================================
# ACTION SUMMARY & REPORTS
# =============================================================================

def get_action_summary() -> pd.DataFrame:
    """Get summary of all actions as DataFrame"""
    init_session_state()

    if not st.session_state.actions:
        return pd.DataFrame()

    df = pd.DataFrame(st.session_state.actions)

    # Parse timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['date'] = df['timestamp'].dt.date
    df['time'] = df['timestamp'].dt.strftime('%H:%M')

    return df[['id', 'date', 'time', 'type', 'target', 'notes']]


def get_daily_report() -> Dict:
    """Generate daily activity report"""
    actions = get_todays_actions()

    calls = [a for a in actions if a['type'] == 'call']
    emails = [a for a in actions if a['type'] == 'email']
    quotes = [a for a in actions if a['type'] == 'quote']
    follow_ups = [a for a in actions if a['type'] == 'follow_up']

    return {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'total_actions': len(actions),
        'calls_made': len(calls),
        'emails_sent': len(emails),
        'quotes_generated': len(quotes),
        'follow_ups_scheduled': len(follow_ups),
        'companies_contacted': list(set(a['target'] for a in calls + emails)),
        'pending_follow_ups': get_pending_follow_ups()
    }


def export_activity_report(format: str = 'csv') -> str:
    """Export activity report"""
    df = get_action_summary()

    if df.empty:
        return ""

    if format == 'csv':
        return df.to_csv(index=False)
    elif format == 'json':
        return df.to_json(orient='records')
    else:
        return df.to_string()


# =============================================================================
# PERSISTENCE
# =============================================================================

def _persist_action(action: Dict) -> None:
    """Persist action to file"""
    try:
        # Load existing actions
        if ACTIVITY_LOG_PATH.exists():
            with open(ACTIVITY_LOG_PATH, 'r') as f:
                all_actions = json.load(f)
        else:
            all_actions = []

        # Append new action
        all_actions.append(action)

        # Keep only last 1000 actions
        all_actions = all_actions[-1000:]

        # Save
        ACTIVITY_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(ACTIVITY_LOG_PATH, 'w') as f:
            json.dump(all_actions, f, indent=2)
    except Exception as e:
        # Silently fail - don't break the app
        pass


def load_historical_actions(days: int = 30) -> List[Dict]:
    """Load historical actions from file"""
    try:
        if not ACTIVITY_LOG_PATH.exists():
            return []

        with open(ACTIVITY_LOG_PATH, 'r') as f:
            all_actions = json.load(f)

        # Filter to recent days
        cutoff = datetime.now() - timedelta(days=days)
        recent = [
            a for a in all_actions
            if datetime.fromisoformat(a['timestamp']) >= cutoff
        ]

        return recent
    except Exception:
        return []


# =============================================================================
# UI HELPERS
# =============================================================================

def render_action_buttons(company: str, key_prefix: str = "") -> Optional[str]:
    """Render action buttons for a company and return selected action"""
    cols = st.columns(4)

    with cols[0]:
        if st.button("📞 Log Call", key=f"{key_prefix}call_{company}", use_container_width=True):
            return 'call'

    with cols[1]:
        if st.button("📧 Log Email", key=f"{key_prefix}email_{company}", use_container_width=True):
            return 'email'

    with cols[2]:
        if st.button("📅 Follow-up", key=f"{key_prefix}followup_{company}", use_container_width=True):
            return 'follow_up'

    with cols[3]:
        if st.button("📝 Add Note", key=f"{key_prefix}note_{company}", use_container_width=True):
            return 'note'

    return None


def render_action_dialog(company: str, action_type: str) -> bool:
    """Render dialog for action details"""
    with st.expander(f"📝 Log {action_type.replace('_', ' ').title()} for {company}", expanded=True):
        if action_type == 'call':
            outcome = st.selectbox(
                "Outcome",
                ["Connected - Positive", "Connected - Neutral", "Connected - Negative",
                 "Left Voicemail", "No Answer", "Wrong Number"],
                key=f"outcome_{company}"
            )
            notes = st.text_area("Notes", key=f"notes_{company}")

            if st.button("Save", key=f"save_{company}"):
                log_call(company, outcome, notes)
                st.success(f"Call logged for {company}")
                return True

        elif action_type == 'follow_up':
            follow_date = st.date_input("Follow-up Date", key=f"date_{company}")
            notes = st.text_area("Notes", key=f"notes_{company}")

            if st.button("Schedule", key=f"save_{company}"):
                log_follow_up(company, follow_date.isoformat(), notes)
                st.success(f"Follow-up scheduled for {company}")
                return True

        elif action_type == 'email':
            template = st.selectbox(
                "Template",
                ["Check-in", "Re-engagement", "Quote Follow-up", "New Product", "Custom"],
                key=f"template_{company}"
            )
            notes = st.text_area("Notes", key=f"notes_{company}")

            if st.button("Log Email", key=f"save_{company}"):
                log_email(company, template, notes)
                st.success(f"Email logged for {company}")
                return True

        elif action_type == 'note':
            notes = st.text_area("Notes", key=f"notes_{company}")

            if st.button("Save Note", key=f"save_{company}"):
                log_action('note', company, notes=notes)
                st.success(f"Note saved for {company}")
                return True

    return False


def render_activity_sidebar():
    """Render activity summary in sidebar"""
    init_session_state()

    stats = get_session_stats()
    recent = get_recent_actions(5)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Session Activity")
    st.sidebar.caption(f"Duration: {stats['session_duration']}")

    col1, col2 = st.sidebar.columns(2)
    col1.metric("Actions", stats['total_actions'])
    col2.metric("Viewed", stats['customers_viewed'])

    if recent:
        st.sidebar.markdown("**Recent:**")
        for action in recent[:3]:
            icon = {'call': '📞', 'email': '📧', 'follow_up': '📅', 'note': '📝', 'quote': '💰', 'export': '📥'}.get(action['type'], '•')
            st.sidebar.caption(f"{icon} {action['target'][:20]}")
