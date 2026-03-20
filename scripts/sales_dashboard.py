#!/usr/bin/env python3
"""
PackagePro Sales Dashboard CLI Tool

A command-line interface for the sales team to access customer segmentation
data, look up customers, identify opportunities, and score prospects.

Usage:
    python sales_dashboard.py segments              # View segment summary
    python sales_dashboard.py customer "Company"   # Look up a customer
    python sales_dashboard.py at-risk              # Get at-risk customers
    python sales_dashboard.py upsell               # Get upsell opportunities
    python sales_dashboard.py score-prospect       # Score a new prospect

Author: PackagePro Analytics Team
Version: 1.0.0
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd
import numpy as np

# =============================================================================
# Path Configuration
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "companies"
OUTPUTS_DIR = BASE_DIR / "outputs"
SEGMENTATION_DIR = OUTPUTS_DIR / "segmentation"
MODELS_DIR = BASE_DIR / "models" / "prospect_scorer"

# =============================================================================
# Color Output for Terminal
# =============================================================================

class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def colored(text: str, color: str) -> str:
    """Apply color to text if terminal supports it."""
    if sys.stdout.isatty():
        return f"{color}{text}{Colors.END}"
    return text


def print_header(title: str):
    """Print a styled header."""
    print()
    print(colored("=" * 70, Colors.BLUE))
    print(colored(f"  {title}", Colors.BOLD + Colors.BLUE))
    print(colored("=" * 70, Colors.BLUE))
    print()


def print_subheader(title: str):
    """Print a styled subheader."""
    print()
    print(colored(f"--- {title} ---", Colors.CYAN))
    print()


# =============================================================================
# Data Loading Functions
# =============================================================================

def load_customer_data() -> pd.DataFrame:
    """Load full customer data with features."""
    path = DATA_DIR / "company_features.csv"
    if not path.exists():
        print(colored(f"Error: Customer data not found at {path}", Colors.RED))
        sys.exit(1)
    return pd.read_csv(path)


def load_segment_assignments() -> pd.DataFrame:
    """Load segment assignments."""
    path = SEGMENTATION_DIR / "cluster_assignments.csv"
    if not path.exists():
        print(colored(f"Error: Segment data not found at {path}", Colors.RED))
        sys.exit(1)
    return pd.read_csv(path)


def load_segment_profiles() -> pd.DataFrame:
    """Load cluster profiles."""
    path = SEGMENTATION_DIR / "cluster_profiles_detailed.csv"
    if not path.exists():
        print(colored(f"Error: Segment profiles not found at {path}", Colors.RED))
        sys.exit(1)
    return pd.read_csv(path)


def load_segment_insights() -> pd.DataFrame:
    """Load segment insights with recommendations."""
    path = SEGMENTATION_DIR / "cluster_insights.csv"
    if not path.exists():
        print(colored(f"Error: Segment insights not found at {path}", Colors.RED))
        sys.exit(1)
    return pd.read_csv(path)


def load_icp_profile() -> Dict[str, Any]:
    """Load the ICP profile."""
    path = MODELS_DIR / "icp_profile.json"
    if not path.exists():
        print(colored(f"Error: ICP profile not found at {path}", Colors.RED))
        sys.exit(1)
    with open(path, 'r') as f:
        return json.load(f)


def get_merged_customer_data() -> pd.DataFrame:
    """Get customer data merged with segment information."""
    customers = load_customer_data()
    segments = load_segment_assignments()
    return customers.merge(segments, on='company', how='left')


# =============================================================================
# Segment Summary Command
# =============================================================================

def cmd_segments():
    """Display segment summary with key metrics."""
    print_header("PackagePro Customer Segments Overview")

    insights = load_segment_insights()
    customers = get_merged_customer_data()

    # Calculate additional metrics per segment
    segment_metrics = customers.groupby('business_segment').agg({
        'monetary_total': ['sum', 'mean', 'median'],
        'frequency': ['sum', 'mean'],
        'recency_days': 'mean',
        'company': 'count'
    }).round(2)

    segment_metrics.columns = ['total_revenue', 'avg_revenue', 'median_revenue',
                                'total_orders', 'avg_orders', 'avg_recency', 'count']

    for _, row in insights.iterrows():
        segment_name = row['Business Name']
        size = row['Size']
        characteristics = row['Key Characteristics']
        actions = row['Recommended Actions']

        # Color code by segment type
        if 'High-Value' in segment_name or 'VIP' in segment_name:
            color = Colors.GREEN
        elif 'Growth' in segment_name:
            color = Colors.YELLOW
        else:
            color = Colors.CYAN

        print(colored(f"{segment_name}", Colors.BOLD + color))
        print(colored(f"  Size: {size}", color))

        # Get metrics for this segment
        if segment_name in segment_metrics.index:
            metrics = segment_metrics.loc[segment_name]
            print(f"  Total Revenue: {colored(f'${metrics.total_revenue:,.0f}', Colors.GREEN)}")
            print(f"  Avg Revenue/Customer: ${metrics.avg_revenue:,.0f}")
            print(f"  Avg Orders/Customer: {metrics.avg_orders:.1f}")
            print(f"  Avg Days Since Last Order: {metrics.avg_recency:.0f}")

        print(f"  Characteristics: {characteristics}")
        print(f"  {colored('Recommended Actions:', Colors.YELLOW)} {actions}")
        print()

    # Overall summary
    print_subheader("Portfolio Summary")
    total_customers = len(customers)
    total_revenue = customers['monetary_total'].sum()
    hv_customers = len(customers[customers['business_segment'] == 'High-Value Regulars'])

    print(f"  Total Customers: {colored(str(total_customers), Colors.BOLD)}")
    print(f"  Total Revenue: {colored(f'${total_revenue:,.0f}', Colors.GREEN)}")
    print(f"  High-Value Customers: {hv_customers} ({hv_customers/total_customers*100:.1f}%)")
    print(f"  Active in Last 90 Days: {len(customers[customers['recency_days'] <= 90])}")


# =============================================================================
# Customer Lookup Command
# =============================================================================

def cmd_customer(name: str):
    """Look up a specific customer and display their profile."""
    print_header(f"Customer Lookup: {name}")

    customers = get_merged_customer_data()

    # Search for customer (case-insensitive partial match)
    matches = customers[customers['company'].str.lower().str.contains(name.lower(), na=False)]

    if len(matches) == 0:
        print(colored(f"No customers found matching '{name}'", Colors.RED))
        print("\nTry searching with a shorter term or different spelling.")
        return

    if len(matches) > 10:
        print(colored(f"Found {len(matches)} matches. Showing first 10:", Colors.YELLOW))
        for _, row in matches.head(10).iterrows():
            print(f"  - {row['company']} ({row.get('business_segment', 'Unknown')})")
        print("\nPlease provide a more specific search term.")
        return

    if len(matches) > 1:
        print(colored(f"Found {len(matches)} matches:", Colors.YELLOW))
        for i, (_, row) in enumerate(matches.iterrows(), 1):
            print(f"  {i}. {row['company']}")
        print()

    # Display details for each match
    for _, customer in matches.iterrows():
        display_customer_profile(customer)


def display_customer_profile(customer: pd.Series):
    """Display detailed customer profile."""
    print_subheader(customer['company'])

    # Segment info
    segment = customer.get('business_segment', 'Unknown')
    if 'High-Value' in str(segment):
        segment_color = Colors.GREEN
    elif 'Growth' in str(segment):
        segment_color = Colors.YELLOW
    else:
        segment_color = Colors.CYAN

    print(f"  {colored('Segment:', Colors.BOLD)} {colored(segment, segment_color)}")

    # RFM Metrics
    print(f"\n  {colored('RFM Metrics:', Colors.BOLD)}")
    print(f"    Recency: {customer.get('recency_days', 'N/A')} days since last order")
    print(f"    Frequency: {customer.get('frequency', 'N/A')} total orders")
    print(f"    Monetary: ${customer.get('monetary_total', 0):,.2f} total revenue")
    print(f"    Average Order: ${customer.get('monetary_mean', 0):,.2f}")

    # Activity Status
    recency = customer.get('recency_days', 999)
    if recency <= 30:
        status = colored("Active (last 30 days)", Colors.GREEN)
    elif recency <= 90:
        status = colored("Recent (last 90 days)", Colors.CYAN)
    elif recency <= 180:
        status = colored("Cooling (3-6 months)", Colors.YELLOW)
    else:
        status = colored("At Risk (>6 months)", Colors.RED)
    print(f"\n  {colored('Status:', Colors.BOLD)} {status}")

    # Company Info
    print(f"\n  {colored('Company Info:', Colors.BOLD)}")
    industry = customer.get('industry_sector', 'Unknown')
    age = customer.get('company_age_years', 'N/A')
    region = customer.get('region', 'Unknown')
    print(f"    Industry: {industry}")
    print(f"    Company Age: {age} years" if age != 'N/A' else "    Company Age: Unknown")
    print(f"    Region: {region}")

    # Product Preferences
    print(f"\n  {colored('Product Preferences:', Colors.BOLD)}")
    product_cols = [col for col in customer.index if col.startswith('ptype_') and customer[col] > 0]
    if product_cols:
        for col in product_cols[:5]:
            pct = customer[col]
            ptype = col.replace('ptype_', '').replace('_', ' ').title()
            print(f"    {ptype}: {pct:.0f}%")
    else:
        print("    No product type data available")

    # Recommendations
    print(f"\n  {colored('Recommended Actions:', Colors.BOLD)}")
    if 'High-Value' in str(segment):
        print("    - Schedule a quarterly business review")
        print("    - Offer VIP early access to new products")
        print("    - Consider volume discount incentives")
    elif 'Growth' in str(segment):
        print("    - Re-engage with personalized outreach")
        print("    - Offer targeted promotions")
        print("    - Understand barriers to purchasing")
    elif recency > 180:
        print("    - Urgent: Win-back campaign needed")
        print("    - Personal call to understand situation")
        print("    - Consider special re-activation offer")
    else:
        print("    - Maintain regular engagement")
        print("    - Look for upsell opportunities")
        print("    - Cross-sell complementary products")


# =============================================================================
# At-Risk Customers Command
# =============================================================================

def cmd_at_risk(limit: int = 20):
    """Identify at-risk customers - high value but recent activity declining."""
    print_header("At-Risk Customers")

    customers = get_merged_customer_data()

    # Define at-risk criteria:
    # 1. High historical value (top 40% by monetary)
    # 2. Long time since last order (>90 days)
    # 3. Was previously active (has multiple orders)

    monetary_threshold = customers['monetary_total'].quantile(0.6)

    at_risk = customers[
        (customers['monetary_total'] >= monetary_threshold) &
        (customers['recency_days'] > 90) &
        (customers['frequency'] >= 2)
    ].copy()

    # Calculate risk score
    at_risk['risk_score'] = (
        at_risk['monetary_total'] / at_risk['monetary_total'].max() * 40 +
        at_risk['recency_days'] / at_risk['recency_days'].max() * 40 +
        at_risk['frequency'] / at_risk['frequency'].max() * 20
    )

    at_risk = at_risk.sort_values('risk_score', ascending=False).head(limit)

    print(f"Found {colored(str(len(at_risk)), Colors.RED)} at-risk high-value customers:\n")

    print(f"{'Customer':<40} {'Revenue':>12} {'Last Order':>12} {'Orders':>8} {'Segment':<20}")
    print("-" * 95)

    for _, row in at_risk.iterrows():
        name = row['company'][:38] if len(row['company']) > 38 else row['company']
        revenue = f"${row['monetary_total']:,.0f}"
        recency = f"{int(row['recency_days'])} days"
        orders = str(int(row['frequency']))
        segment = str(row.get('business_segment', 'Unknown'))[:18]

        # Color code by urgency
        if row['recency_days'] > 180:
            print(colored(f"{name:<40} {revenue:>12} {recency:>12} {orders:>8} {segment:<20}", Colors.RED))
        else:
            print(colored(f"{name:<40} {revenue:>12} {recency:>12} {orders:>8} {segment:<20}", Colors.YELLOW))

    print()
    print_subheader("Recommended Actions")
    print("  1. Prioritize personal outreach to top 5 customers")
    print("  2. Send re-engagement campaign to full list")
    print("  3. Review any service issues or complaints")
    print("  4. Consider win-back offers with limited-time incentives")
    print()

    # Summary stats
    total_at_risk_value = at_risk['monetary_total'].sum()
    avg_days_inactive = at_risk['recency_days'].mean()
    print(f"  Total Value at Risk: {colored(f'${total_at_risk_value:,.0f}', Colors.RED)}")
    print(f"  Average Days Inactive: {avg_days_inactive:.0f}")


# =============================================================================
# Upsell Opportunities Command
# =============================================================================

def cmd_upsell(limit: int = 20):
    """Identify upsell opportunities - frequent but low value customers."""
    print_header("Upsell Opportunities")

    customers = get_merged_customer_data()

    # Define upsell criteria:
    # 1. Active (recent orders)
    # 2. Frequent orderer (multiple orders)
    # 3. Below average order value
    # 4. Good relationship indicators

    avg_order_value = customers['monetary_mean'].median()

    upsell = customers[
        (customers['recency_days'] <= 180) &
        (customers['frequency'] >= 3) &
        (customers['monetary_mean'] < avg_order_value)
    ].copy()

    # Calculate opportunity score (higher = better opportunity)
    upsell['opportunity_score'] = (
        (1 - upsell['recency_days'] / 365) * 30 +  # Recent activity
        upsell['frequency'] / upsell['frequency'].max() * 40 +  # High frequency
        (1 - upsell['monetary_mean'] / avg_order_value) * 30  # Room to grow
    )

    upsell = upsell.sort_values('opportunity_score', ascending=False).head(limit)

    print(f"Found {colored(str(len(upsell)), Colors.GREEN)} upsell opportunities:\n")

    print(f"{'Customer':<35} {'Avg Order':>10} {'Orders':>8} {'Last Order':>12} {'Industry':<20}")
    print("-" * 90)

    for _, row in upsell.iterrows():
        name = row['company'][:33] if len(row['company']) > 33 else row['company']
        avg_order = f"${row['monetary_mean']:,.0f}"
        orders = str(int(row['frequency']))
        recency = f"{int(row['recency_days'])} days"
        industry = str(row.get('industry_sector', 'Unknown'))[:18]

        print(f"{name:<35} {avg_order:>10} {orders:>8} {recency:>12} {industry:<20}")

    print()
    print_subheader("Recommended Actions")
    print("  1. Analyze current product mix for cross-sell opportunities")
    print("  2. Introduce premium product options")
    print("  3. Offer bundle deals for larger orders")
    print("  4. Discuss volume pricing for commitment")
    print("  5. Identify operational efficiency gains with larger batches")
    print()

    # Summary stats
    current_avg = upsell['monetary_mean'].mean()
    target_avg = avg_order_value
    potential_lift = (target_avg - current_avg) * upsell['frequency'].sum()
    print(f"  Current Avg Order: ${current_avg:,.0f}")
    print(f"  Target Avg Order: ${target_avg:,.0f}")
    print(f"  Potential Revenue Lift: {colored(f'${potential_lift:,.0f}', Colors.GREEN)} (if brought to average)")


# =============================================================================
# Score Prospect Command
# =============================================================================

def cmd_score_prospect(name: str, sic: str, age: float, region: str):
    """Score a new prospect using the ICP profile."""
    print_header(f"Prospect Scoring: {name}")

    # Load ICP profile
    icp = load_icp_profile()

    # Map SIC to industry sector
    sic_str = str(sic)[:2] if sic else ''
    try:
        sic_int = int(sic_str)
        if sic_int in range(10, 34):
            industry = "Manufacturing"
        elif sic_int in range(45, 48):
            industry = "Wholesale & Retail"
        elif sic_int in range(69, 76):
            industry = "Professional Services"
        elif sic_int in range(77, 83):
            industry = "Administrative Services"
        elif sic_int in range(41, 44):
            industry = "Construction"
        elif sic_int in range(58, 64):
            industry = "Information & Communication"
        else:
            industry = "Other"
    except (ValueError, TypeError):
        industry = "Unknown"

    # Calculate component scores
    scores = {}
    reasons = {}

    # Industry score
    industry_profiles = icp.get('industry_profiles', {})
    if industry in industry_profiles:
        profile = industry_profiles[industry]
        scores['industry'] = profile.get('score_weight', 50)
        lift = profile.get('lift_ratio', 1.0)
        reasons['industry'] = f"{industry} sector (lift ratio: {lift:.2f}x)"
    else:
        scores['industry'] = 50
        reasons['industry'] = f"{industry} (not in ICP data)"

    # Age score
    age_profile = icp.get('company_age', {})
    optimal_min = age_profile.get('optimal_min_years', 7)
    optimal_max = age_profile.get('optimal_max_years', 29)

    if age and optimal_min <= age <= optimal_max:
        scores['age'] = 100
        reasons['age'] = f"{age} years (optimal range: {optimal_min}-{optimal_max})"
    elif age and age < optimal_min:
        scores['age'] = max(40, 100 - (optimal_min - age) * 8)
        reasons['age'] = f"{age} years (younger than optimal)"
    elif age:
        scores['age'] = max(60, 100 - (age - optimal_max) * 2)
        reasons['age'] = f"{age} years (established company)"
    else:
        scores['age'] = 50
        reasons['age'] = "Unknown age"

    # Region score
    geo_profile = icp.get('geography', {})
    region_scores = geo_profile.get('region_scores', {})
    top_regions = geo_profile.get('top_regions', [])

    if region in region_scores:
        scores['region'] = region_scores[region]
        is_top = "(high-value region)" if region in top_regions else ""
        reasons['region'] = f"{region} {is_top}"
    else:
        scores['region'] = 50
        reasons['region'] = f"{region} (not in ICP data)"

    # Calculate overall score
    weights = {'industry': 0.40, 'age': 0.35, 'region': 0.25}
    overall_score = sum(scores[k] * weights[k] for k in scores)

    # Determine tier
    if overall_score >= 75:
        tier = colored("HOT", Colors.GREEN + Colors.BOLD)
        tier_advice = "Priority lead - immediate sales follow-up recommended"
    elif overall_score >= 60:
        tier = colored("WARM", Colors.YELLOW + Colors.BOLD)
        tier_advice = "Good prospect - add to nurture campaign"
    elif overall_score >= 45:
        tier = colored("COOL", Colors.CYAN)
        tier_advice = "Moderate fit - qualify further before pursuing"
    else:
        tier = colored("COLD", Colors.RED)
        tier_advice = "Low priority - may not match ICP"

    # Display results
    print(f"  {colored('Overall Score:', Colors.BOLD)} {overall_score:.1f}/100")
    print(f"  {colored('Priority Tier:', Colors.BOLD)} {tier}")
    print()

    print_subheader("Score Breakdown")
    for component, score in scores.items():
        weight_pct = weights[component] * 100
        reason = reasons[component]

        # Color code by score
        if score >= 70:
            score_str = colored(f"{score:.0f}", Colors.GREEN)
        elif score >= 50:
            score_str = colored(f"{score:.0f}", Colors.YELLOW)
        else:
            score_str = colored(f"{score:.0f}", Colors.RED)

        print(f"  {component.title():12} {score_str:>8}/100 (weight: {weight_pct:.0f}%) - {reason}")

    print()
    print_subheader("Recommendation")
    print(f"  {tier_advice}")

    if overall_score >= 60:
        print("\n  Suggested talking points:")
        if 'Manufacturing' in industry or 'Wholesale' in industry:
            print("    - PackagePro specializes in packaging for your industry")
            print("    - Highlight our binder and box expertise")
        if age and age > 10:
            print("    - Emphasize our reliability for established businesses")
        if region in top_regions:
            print("    - Mention other successful clients in their region")


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="PackagePro Sales Dashboard - Customer Segmentation & Prospect Scoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python sales_dashboard.py segments
    python sales_dashboard.py customer "Artisan Print"
    python sales_dashboard.py at-risk --limit 30
    python sales_dashboard.py upsell
    python sales_dashboard.py score-prospect --name "ABC Ltd" --sic 18129 --age 15 --region "London"
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Segments command
    subparsers.add_parser('segments', help='View customer segment summary')

    # Customer lookup command
    customer_parser = subparsers.add_parser('customer', help='Look up a specific customer')
    customer_parser.add_argument('name', type=str, help='Customer name to search for')

    # At-risk command
    risk_parser = subparsers.add_parser('at-risk', help='List at-risk customers')
    risk_parser.add_argument('--limit', '-l', type=int, default=20, help='Number of results to show')

    # Upsell command
    upsell_parser = subparsers.add_parser('upsell', help='List upsell opportunities')
    upsell_parser.add_argument('--limit', '-l', type=int, default=20, help='Number of results to show')

    # Score prospect command
    score_parser = subparsers.add_parser('score-prospect', help='Score a new prospect')
    score_parser.add_argument('--name', '-n', type=str, required=True, help='Company name')
    score_parser.add_argument('--sic', '-s', type=str, default='', help='SIC code')
    score_parser.add_argument('--age', '-a', type=float, default=None, help='Company age in years')
    score_parser.add_argument('--region', '-r', type=str, default='', help='Region/location')

    args = parser.parse_args()

    if args.command == 'segments':
        cmd_segments()
    elif args.command == 'customer':
        cmd_customer(args.name)
    elif args.command == 'at-risk':
        cmd_at_risk(args.limit)
    elif args.command == 'upsell':
        cmd_upsell(args.limit)
    elif args.command == 'score-prospect':
        cmd_score_prospect(args.name, args.sic, args.age, args.region)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
