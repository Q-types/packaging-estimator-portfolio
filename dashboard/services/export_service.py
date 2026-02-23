"""
Export Service
Generates formatted exports in various formats (CSV, Excel, PDF summary)
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
from io import BytesIO
import json


# =============================================================================
# CSV EXPORTS
# =============================================================================

def export_to_csv(df: pd.DataFrame, filename_prefix: str = "export") -> tuple:
    """Export DataFrame to CSV with proper formatting"""
    csv_data = df.to_csv(index=False)
    filename = f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    return csv_data, filename


def export_at_risk_customers(customers: List[Dict]) -> tuple:
    """Export at-risk customers with action recommendations"""
    if not customers:
        return "", "no_data.csv"

    df = pd.DataFrame(customers)

    # Add action recommendations
    df['recommended_action'] = df.apply(
        lambda r: "URGENT: Call today" if r.get('churn_risk', 0) >= 80
        else "Schedule call this week" if r.get('churn_risk', 0) >= 60
        else "Add to re-engagement campaign",
        axis=1
    )

    # Format columns
    column_order = ['company', 'churn_risk', 'revenue_at_stake', 'recency_days',
                    'frequency', 'monetary_total', 'recommended_action']
    available_cols = [c for c in column_order if c in df.columns]

    return export_to_csv(df[available_cols], "at_risk_customers")


def export_hot_prospects(prospects: List[Dict]) -> tuple:
    """Export hot prospects with outreach priorities"""
    if not prospects:
        return "", "no_data.csv"

    df = pd.DataFrame(prospects)

    # Add priority ranking
    df['priority_rank'] = range(1, len(df) + 1)

    # Add outreach suggestion
    df['outreach_suggestion'] = df.apply(
        lambda r: f"High-fit {r.get('industry_sector', 'company')} - emphasize packaging solutions",
        axis=1
    )

    return export_to_csv(df, "hot_prospects")


def export_expansion_opportunities(opportunities: List[Dict]) -> tuple:
    """Export expansion opportunities"""
    if not opportunities:
        return "", "no_data.csv"

    df = pd.DataFrame(opportunities)
    return export_to_csv(df, "expansion_opportunities")


# =============================================================================
# EXCEL EXPORTS (if openpyxl available)
# =============================================================================

def export_to_excel(dataframes: Dict[str, pd.DataFrame], filename_prefix: str = "report") -> tuple:
    """Export multiple DataFrames to Excel with formatting"""
    try:
        output = BytesIO()

        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for sheet_name, df in dataframes.items():
                if not df.empty:
                    df.to_excel(writer, sheet_name=sheet_name[:31], index=False)

        output.seek(0)
        filename = f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        return output.getvalue(), filename

    except ImportError:
        # Fall back to CSV if openpyxl not available
        combined = pd.concat(dataframes.values(), ignore_index=True)
        return export_to_csv(combined, filename_prefix)


def export_full_report(
    at_risk: List[Dict],
    prospects: List[Dict],
    expansion: List[Dict],
    segment_summary: pd.DataFrame
) -> tuple:
    """Export comprehensive report with multiple sheets"""
    dataframes = {
        'At-Risk Customers': pd.DataFrame(at_risk) if at_risk else pd.DataFrame(),
        'Hot Prospects': pd.DataFrame(prospects) if prospects else pd.DataFrame(),
        'Expansion Opps': pd.DataFrame(expansion) if expansion else pd.DataFrame(),
        'Segment Summary': segment_summary if not segment_summary.empty else pd.DataFrame()
    }

    return export_to_excel(dataframes, "ksp_intelligence_report")


# =============================================================================
# ACTION LIST EXPORTS
# =============================================================================

def export_daily_action_list(priorities: Dict) -> tuple:
    """Export formatted daily action list"""
    lines = []
    lines.append("=" * 60)
    lines.append(f"KSP DAILY ACTION LIST - {datetime.now().strftime('%A, %B %d, %Y')}")
    lines.append("=" * 60)
    lines.append("")

    # At-Risk Customers
    lines.append("🔴 AT-RISK CUSTOMERS (Call Today)")
    lines.append("-" * 40)
    at_risk = priorities.get('at_risk', [])
    if at_risk:
        for i, customer in enumerate(at_risk[:10], 1):
            lines.append(f"{i}. {customer['company']}")
            lines.append(f"   Risk: {customer.get('churn_risk', 0):.0f}% | £{customer.get('revenue_at_stake', 0):,.0f} at stake")
            lines.append(f"   Last order: {customer.get('recency_days', 0):.0f} days ago")
            lines.append("")
    else:
        lines.append("   No high-risk customers today!")
    lines.append("")

    # Hot Prospects
    lines.append("🔥 HOT PROSPECTS (Outreach Priority)")
    lines.append("-" * 40)
    prospects = priorities.get('hot_prospects', [])
    if prospects:
        for i, prospect in enumerate(prospects[:10], 1):
            lines.append(f"{i}. {prospect.get('company_name', 'Unknown')}")
            lines.append(f"   Score: {prospect.get('prospect_score', 0):.0f} | {prospect.get('industry_sector', 'N/A')}")
            lines.append(f"   Region: {prospect.get('region', 'N/A')} | Packaging: {prospect.get('packaging_need', 'N/A')}")
            lines.append("")
    else:
        lines.append("   No hot prospects available")
    lines.append("")

    # Expansion Opportunities
    lines.append("📈 EXPANSION OPPORTUNITIES")
    lines.append("-" * 40)
    expansion = priorities.get('expansion', [])
    if expansion:
        for i, customer in enumerate(expansion[:5], 1):
            lines.append(f"{i}. {customer['company']}")
            lines.append(f"   Current: £{customer.get('monetary_total', 0):,.0f} | Potential: +£{customer.get('expansion_potential', 0):,.0f}")
            lines.append("")
    else:
        lines.append("   No expansion opportunities identified")

    lines.append("")
    lines.append("=" * 60)
    lines.append(f"Generated by KSP Intelligence Dashboard")
    lines.append("=" * 60)

    content = "\n".join(lines)
    filename = f"daily_actions_{datetime.now().strftime('%Y%m%d')}.txt"

    return content, filename


def export_email_friendly_list(customers: List[Dict], list_type: str = "at_risk") -> str:
    """Generate email-friendly formatted list"""
    lines = []

    if list_type == "at_risk":
        lines.append("**Priority Customers Requiring Attention:**\n")
        for customer in customers[:10]:
            lines.append(f"• **{customer['company']}**")
            lines.append(f"  - Churn Risk: {customer.get('churn_risk', 0):.0f}%")
            lines.append(f"  - Revenue at Stake: £{customer.get('revenue_at_stake', 0):,.0f}")
            lines.append(f"  - Days Since Last Order: {customer.get('recency_days', 0):.0f}")
            lines.append("")

    elif list_type == "prospects":
        lines.append("**Top Prospects for Outreach:**\n")
        for prospect in customers[:10]:
            lines.append(f"• **{prospect.get('company_name', 'Unknown')}**")
            lines.append(f"  - ICP Score: {prospect.get('prospect_score', 0):.0f}")
            lines.append(f"  - Industry: {prospect.get('industry_sector', 'N/A')}")
            lines.append(f"  - Packaging Need: {prospect.get('packaging_need', 'N/A')}")
            lines.append("")

    return "\n".join(lines)


# =============================================================================
# JSON EXPORTS (for API/integrations)
# =============================================================================

def export_to_json(data: any, filename_prefix: str = "export") -> tuple:
    """Export data to JSON format"""
    if isinstance(data, pd.DataFrame):
        json_data = data.to_json(orient='records', indent=2)
    elif isinstance(data, (list, dict)):
        json_data = json.dumps(data, indent=2, default=str)
    else:
        json_data = json.dumps(str(data))

    filename = f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    return json_data, filename


# =============================================================================
# STREAMLIT DOWNLOAD HELPERS
# =============================================================================

def render_download_button(
    data: any,
    label: str,
    filename: str,
    mime_type: str = "text/csv",
    key: str = None
):
    """Render a styled download button"""
    st.download_button(
        label=f"📥 {label}",
        data=data,
        file_name=filename,
        mime=mime_type,
        key=key,
        use_container_width=True
    )


def render_export_options(df: pd.DataFrame, prefix: str, key_prefix: str = ""):
    """Render multiple export format options"""
    col1, col2, col3 = st.columns(3)

    with col1:
        csv_data, csv_filename = export_to_csv(df, prefix)
        render_download_button(csv_data, "CSV", csv_filename, "text/csv", f"{key_prefix}csv")

    with col2:
        json_data, json_filename = export_to_json(df, prefix)
        render_download_button(json_data, "JSON", json_filename, "application/json", f"{key_prefix}json")

    with col3:
        try:
            excel_data, excel_filename = export_to_excel({prefix: df}, prefix)
            render_download_button(excel_data, "Excel", excel_filename,
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   f"{key_prefix}excel")
        except:
            st.button("Excel (N/A)", disabled=True, key=f"{key_prefix}excel")
