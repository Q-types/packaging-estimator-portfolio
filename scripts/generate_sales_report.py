#!/usr/bin/env python3
"""
PackagePro Weekly Sales Report Generator

Generates a comprehensive weekly sales report with:
- Segment health overview
- At-risk customer alerts
- Upsell opportunities
- New customer recommendations
- Key metrics comparison

Output: Markdown report to outputs/reports/weekly_sales_report_YYYY-MM-DD.md

Usage:
    python generate_sales_report.py
    python generate_sales_report.py --output custom_report.md

Author: PackagePro Analytics Team
Version: 1.0.0
"""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np

# =============================================================================
# Path Configuration
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "companies"
OUTPUTS_DIR = BASE_DIR / "outputs"
SEGMENTATION_DIR = OUTPUTS_DIR / "segmentation"
REPORTS_DIR = OUTPUTS_DIR / "reports"
MODELS_DIR = BASE_DIR / "models" / "prospect_scorer"

# =============================================================================
# Data Loading Functions
# =============================================================================

def load_customer_data() -> pd.DataFrame:
    """Load full customer data with features."""
    path = DATA_DIR / "company_features.csv"
    return pd.read_csv(path)


def load_segment_assignments() -> pd.DataFrame:
    """Load segment assignments."""
    path = SEGMENTATION_DIR / "cluster_assignments.csv"
    return pd.read_csv(path)


def load_segment_insights() -> pd.DataFrame:
    """Load segment insights with recommendations."""
    path = SEGMENTATION_DIR / "cluster_insights.csv"
    return pd.read_csv(path)


def load_icp_profile() -> Dict[str, Any]:
    """Load the ICP profile."""
    path = MODELS_DIR / "icp_profile.json"
    with open(path, 'r') as f:
        return json.load(f)


def get_merged_data() -> pd.DataFrame:
    """Get customer data merged with segment information."""
    customers = load_customer_data()
    segments = load_segment_assignments()
    return customers.merge(segments, on='company', how='left')


# =============================================================================
# Report Generation Functions
# =============================================================================

def generate_header(report_date: datetime) -> str:
    """Generate report header."""
    week_start = report_date - timedelta(days=report_date.weekday())
    week_end = week_start + timedelta(days=6)

    return f"""# PackagePro Weekly Sales Report

**Report Date:** {report_date.strftime('%B %d, %Y')}
**Week of:** {week_start.strftime('%B %d')} - {week_end.strftime('%B %d, %Y')}
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

"""


def generate_executive_summary(df: pd.DataFrame) -> str:
    """Generate executive summary section."""
    total_customers = len(df)
    total_revenue = df['monetary_total'].sum()
    avg_order_value = df['monetary_mean'].mean()

    # Activity metrics
    active_30 = len(df[df['recency_days'] <= 30])
    active_90 = len(df[df['recency_days'] <= 90])
    at_risk = len(df[(df['recency_days'] > 180) & (df['monetary_total'] > df['monetary_total'].median())])

    # Segment breakdown
    segment_counts = df['business_segment'].value_counts()
    hv_count = segment_counts.get('High-Value Regulars', 0)

    return f"""## Executive Summary

| Metric | Value |
|--------|-------|
| Total Customers | {total_customers:,} |
| Total Lifetime Revenue | ${total_revenue:,.0f} |
| Average Order Value | ${avg_order_value:,.0f} |
| Active (Last 30 Days) | {active_30} ({active_30/total_customers*100:.1f}%) |
| Active (Last 90 Days) | {active_90} ({active_90/total_customers*100:.1f}%) |
| High-Value Customers | {hv_count} ({hv_count/total_customers*100:.1f}%) |
| At-Risk Customers | {at_risk} |

### Key Insights
- **{active_30}** customers placed orders in the last 30 days
- **{at_risk}** high-value customers are at risk (>180 days inactive)
- High-Value Regulars represent **{hv_count/total_customers*100:.1f}%** of customers but contribute the majority of revenue

"""


def generate_segment_health(df: pd.DataFrame, insights: pd.DataFrame) -> str:
    """Generate segment health section."""
    output = "## Segment Health Overview\n\n"

    segment_metrics = df.groupby('business_segment').agg({
        'monetary_total': ['sum', 'mean', 'count'],
        'frequency': 'mean',
        'recency_days': 'mean'
    }).round(2)

    segment_metrics.columns = ['total_revenue', 'avg_revenue', 'count', 'avg_frequency', 'avg_recency']

    output += "| Segment | Customers | Total Revenue | Avg Revenue | Avg Orders | Avg Recency |\n"
    output += "|---------|-----------|---------------|-------------|------------|-------------|\n"

    for segment in segment_metrics.index:
        metrics = segment_metrics.loc[segment]
        count = int(metrics['count'])
        total_rev = metrics['total_revenue']
        avg_rev = metrics['avg_revenue']
        avg_freq = metrics['avg_frequency']
        avg_rec = metrics['avg_recency']

        # Health indicator
        if avg_rec <= 90:
            health = ":white_check_mark:"
        elif avg_rec <= 180:
            health = ":warning:"
        else:
            health = ":x:"

        output += f"| {health} {segment} | {count} | ${total_rev:,.0f} | ${avg_rev:,.0f} | {avg_freq:.1f} | {avg_rec:.0f} days |\n"

    output += "\n**Legend:** :white_check_mark: Healthy (avg <90 days) | :warning: Monitor (90-180 days) | :x: At Risk (>180 days)\n\n"

    # Segment recommendations
    output += "### Segment-Specific Actions\n\n"
    for _, row in insights.iterrows():
        output += f"**{row['Business Name']}** ({row['Size']})\n"
        output += f"- Characteristics: {row['Key Characteristics']}\n"
        output += f"- *Recommended:* {row['Recommended Actions']}\n\n"

    return output


def generate_at_risk_section(df: pd.DataFrame) -> str:
    """Generate at-risk customers section."""
    output = "## At-Risk Customers Alert\n\n"

    monetary_threshold = df['monetary_total'].quantile(0.6)

    at_risk = df[
        (df['monetary_total'] >= monetary_threshold) &
        (df['recency_days'] > 90) &
        (df['frequency'] >= 2)
    ].copy()

    at_risk['risk_score'] = (
        at_risk['monetary_total'] / at_risk['monetary_total'].max() * 40 +
        at_risk['recency_days'] / at_risk['recency_days'].max() * 40 +
        at_risk['frequency'] / at_risk['frequency'].max() * 20
    )

    at_risk = at_risk.sort_values('risk_score', ascending=False).head(15)

    total_at_risk_value = at_risk['monetary_total'].sum()
    avg_days_inactive = at_risk['recency_days'].mean()

    output += f"> **{len(at_risk)} high-value customers** need immediate attention.\n"
    output += f"> Total value at risk: **${total_at_risk_value:,.0f}**\n\n"

    output += "### Priority List (Top 15)\n\n"
    output += "| Priority | Customer | Total Revenue | Last Order | Orders | Segment |\n"
    output += "|----------|----------|---------------|------------|--------|---------|\n"

    for i, (_, row) in enumerate(at_risk.iterrows(), 1):
        urgency = ":rotating_light:" if row['recency_days'] > 180 else ":warning:"
        name = row['company'][:30] if len(row['company']) > 30 else row['company']
        output += f"| {urgency} {i} | {name} | ${row['monetary_total']:,.0f} | {int(row['recency_days'])} days | {int(row['frequency'])} | {row['business_segment']} |\n"

    output += "\n### Recommended Actions\n"
    output += "1. **Immediate:** Personal calls to top 5 at-risk customers\n"
    output += "2. **This Week:** Email re-engagement campaign to full list\n"
    output += "3. **Ongoing:** Review service quality and delivery times\n"
    output += "4. **Consider:** Win-back offer with time-limited discount\n\n"

    return output


def generate_upsell_section(df: pd.DataFrame) -> str:
    """Generate upsell opportunities section."""
    output = "## Upsell Opportunities\n\n"

    avg_order_value = df['monetary_mean'].median()

    upsell = df[
        (df['recency_days'] <= 180) &
        (df['frequency'] >= 3) &
        (df['monetary_mean'] < avg_order_value)
    ].copy()

    upsell['opportunity_score'] = (
        (1 - upsell['recency_days'] / 365) * 30 +
        upsell['frequency'] / upsell['frequency'].max() * 40 +
        (1 - upsell['monetary_mean'] / avg_order_value) * 30
    )

    upsell = upsell.sort_values('opportunity_score', ascending=False).head(15)

    current_avg = upsell['monetary_mean'].mean()
    potential_lift = (avg_order_value - current_avg) * upsell['frequency'].sum()

    output += f"> **{len(upsell)} active customers** with below-average order values.\n"
    output += f"> Potential revenue lift: **${potential_lift:,.0f}** if brought to average\n\n"

    output += "### Top Upsell Candidates\n\n"
    output += "| Customer | Avg Order | Target | Gap | Orders | Industry |\n"
    output += "|----------|-----------|--------|-----|--------|----------|\n"

    for _, row in upsell.iterrows():
        name = row['company'][:28] if len(row['company']) > 28 else row['company']
        gap = avg_order_value - row['monetary_mean']
        industry = str(row.get('industry_sector', 'Unknown'))[:15]
        output += f"| {name} | ${row['monetary_mean']:,.0f} | ${avg_order_value:,.0f} | ${gap:,.0f} | {int(row['frequency'])} | {industry} |\n"

    output += "\n### Upsell Strategies\n"
    output += "1. **Product Bundles:** Offer package deals for related products\n"
    output += "2. **Volume Discounts:** Introduce tiered pricing for larger orders\n"
    output += "3. **Premium Options:** Highlight quality upgrades and premium finishes\n"
    output += "4. **Cross-Sell:** Analyze product mix for complementary items\n\n"

    return output


def generate_new_customer_section(df: pd.DataFrame) -> str:
    """Generate new customer insights section."""
    output = "## New Customer Analysis\n\n"

    # New customers (tenure < 365 days, fewer than 5 orders)
    new_customers = df[
        (df.get('tenure_days', 0) <= 365) |
        (df['frequency'] <= 2)
    ].copy()

    if len(new_customers) == 0:
        output += "No new customers identified in the analysis period.\n\n"
        return output

    output += f"**{len(new_customers)}** customers are relatively new (first year or few orders)\n\n"

    # Segment new customers
    new_by_segment = new_customers.groupby('business_segment').size()

    output += "### New Customer Distribution by Segment\n\n"
    output += "| Segment | New Customers | % of New |\n"
    output += "|---------|---------------|----------|\n"

    for segment, count in new_by_segment.items():
        pct = count / len(new_customers) * 100
        output += f"| {segment} | {count} | {pct:.1f}% |\n"

    output += "\n### Onboarding Recommendations\n"
    output += "- Schedule 30-day check-in calls with new customers\n"
    output += "- Send welcome sequence with product guides\n"
    output += "- Assign dedicated rep for first 3 orders\n"
    output += "- Monitor first order feedback closely\n\n"

    return output


def generate_industry_insights(df: pd.DataFrame, icp: Dict) -> str:
    """Generate industry-based insights."""
    output = "## Industry Insights\n\n"

    industry_metrics = df.groupby('industry_sector').agg({
        'monetary_total': ['sum', 'mean', 'count'],
        'frequency': 'mean'
    }).round(2)

    industry_metrics.columns = ['total_revenue', 'avg_revenue', 'count', 'avg_frequency']
    industry_metrics = industry_metrics.sort_values('total_revenue', ascending=False).head(10)

    output += "### Top Industries by Revenue\n\n"
    output += "| Industry | Customers | Total Revenue | Avg Revenue | ICP Lift |\n"
    output += "|----------|-----------|---------------|-------------|----------|\n"

    icp_industries = icp.get('industry_profiles', {})

    for industry in industry_metrics.index:
        if pd.isna(industry):
            continue
        metrics = industry_metrics.loc[industry]
        lift = "N/A"
        if str(industry) in icp_industries:
            lift_val = icp_industries[str(industry)].get('lift_ratio', 1.0)
            lift = f"{lift_val:.2f}x"
        output += f"| {industry} | {int(metrics['count'])} | ${metrics['total_revenue']:,.0f} | ${metrics['avg_revenue']:,.0f} | {lift} |\n"

    output += "\n### High-Potential Industries (ICP Analysis)\n\n"

    # Sort industries by lift ratio
    sorted_industries = sorted(
        icp_industries.items(),
        key=lambda x: x[1].get('lift_ratio', 0),
        reverse=True
    )[:5]

    output += "Industries with highest likelihood of becoming high-value customers:\n\n"
    for industry, profile in sorted_industries:
        lift = profile.get('lift_ratio', 1.0)
        output += f"- **{industry}**: {lift:.2f}x more likely to become high-value\n"

    output += "\n"
    return output


def generate_action_items() -> str:
    """Generate action items section."""
    return """## This Week's Action Items

### Priority 1: At-Risk Recovery
- [ ] Call top 5 at-risk customers personally
- [ ] Send win-back email campaign to all at-risk
- [ ] Review recent service issues for patterns

### Priority 2: Upsell Execution
- [ ] Prepare bundle offers for top 10 upsell targets
- [ ] Schedule account reviews with frequent buyers
- [ ] Update pricing tiers for volume orders

### Priority 3: New Customer Success
- [ ] Complete 30-day check-ins for recent customers
- [ ] Send product education materials
- [ ] Gather feedback on first orders

### Priority 4: Prospecting
- [ ] Score new leads from trade shows
- [ ] Target Manufacturing and Wholesale sectors
- [ ] Follow up on high-score prospects

---

*Report generated automatically by PackagePro Sales Analytics*
*For questions, contact the analytics team*
"""


def generate_report(df: pd.DataFrame, insights: pd.DataFrame, icp: Dict, report_date: datetime) -> str:
    """Generate complete report."""
    report = ""
    report += generate_header(report_date)
    report += generate_executive_summary(df)
    report += generate_segment_health(df, insights)
    report += generate_at_risk_section(df)
    report += generate_upsell_section(df)
    report += generate_new_customer_section(df)
    report += generate_industry_insights(df, icp)
    report += generate_action_items()

    return report


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Generate weekly sales report for PackagePro",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='Custom output path (default: outputs/reports/weekly_sales_report_YYYY-MM-DD.md)'
    )

    parser.add_argument(
        '--date', '-d',
        type=str,
        default=None,
        help='Report date (YYYY-MM-DD format, default: today)'
    )

    args = parser.parse_args()

    # Parse date
    if args.date:
        report_date = datetime.strptime(args.date, '%Y-%m-%d')
    else:
        report_date = datetime.now()

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        output_path = REPORTS_DIR / f"weekly_sales_report_{report_date.strftime('%Y-%m-%d')}.md"

    print(f"Generating sales report for {report_date.strftime('%Y-%m-%d')}...")

    # Load data
    print("  Loading customer data...")
    df = get_merged_data()

    print("  Loading segment insights...")
    insights = load_segment_insights()

    print("  Loading ICP profile...")
    icp = load_icp_profile()

    # Generate report
    print("  Generating report sections...")
    report = generate_report(df, insights, icp, report_date)

    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(report)

    print(f"\nReport saved to: {output_path}")

    # Print summary
    print("\n--- Report Summary ---")
    print(f"  Total Customers: {len(df)}")
    print(f"  At-Risk (High Value): {len(df[(df['recency_days'] > 90) & (df['monetary_total'] > df['monetary_total'].median())])}")
    print(f"  Upsell Opportunities: {len(df[(df['recency_days'] <= 180) & (df['frequency'] >= 3) & (df['monetary_mean'] < df['monetary_mean'].median())])}")


if __name__ == '__main__':
    main()
