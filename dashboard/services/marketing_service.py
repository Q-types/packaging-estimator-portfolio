"""
Marketing Strategy Service
Provides segment-specific marketing recommendations backed by best practices
"""
from typing import Dict, List
from services.data_loader import load_cluster_profiles


def get_marketing_strategies() -> Dict[str, Dict]:
    """
    Get comprehensive marketing strategies for each segment
    Based on RFM analysis best practices and B2B marketing principles
    """
    profiles = load_cluster_profiles()

    strategies = {
        "0": {
            "segment_name": profiles.get("0", {}).get("name", "At-Risk Dormant"),
            "priority": "CRITICAL",
            "objective": "Win back churned customers before they're lost forever",
            "strategy_summary": "Aggressive re-engagement with personalized outreach and exclusive offers",
            "tactics": [
                {
                    "name": "Win-Back Email Sequence",
                    "description": "3-part email sequence: 'We miss you' → 'What went wrong?' → 'Exclusive return offer'",
                    "timeline": "Week 1-3",
                    "kpi": "Re-engagement rate >15%"
                },
                {
                    "name": "Personal Account Manager Call",
                    "description": "Direct phone outreach from account manager to understand reasons for disengagement",
                    "timeline": "Week 1",
                    "kpi": "Contact rate >50%"
                },
                {
                    "name": "Exclusive Return Incentive",
                    "description": "15-20% discount on next order OR free delivery for 3 months",
                    "timeline": "Week 2-4",
                    "kpi": "Redemption rate >10%"
                },
                {
                    "name": "Exit Survey",
                    "description": "Short survey to understand churn reasons for product improvement",
                    "timeline": "Week 1",
                    "kpi": "Response rate >25%"
                }
            ],
            "email_templates": [
                {
                    "name": "We Miss You",
                    "subject": "It's been a while, [Company Name] - we'd love to reconnect",
                    "preview": "We noticed you haven't ordered recently. Is there something we could do better?",
                    "body": """Hi [Contact Name],

We noticed it's been [X] months since your last order with KSP Packaging, and we wanted to check in.

Your business has been valued since [first order date], and we'd love the opportunity to serve you again.

Has something changed in your packaging needs? We're constantly expanding our capabilities and would welcome the chance to discuss how we can better support you.

I'd love to schedule a quick call to understand how we can help.

Best regards,
[Account Manager Name]
KSP Packaging Team"""
                },
                {
                    "name": "Exclusive Return Offer",
                    "subject": "[Company Name] - Your exclusive 20% welcome back offer",
                    "preview": "We've reserved a special offer just for you to welcome you back.",
                    "body": """Hi [Contact Name],

As a valued past customer, we want to make it easy for you to come back.

For your next order, enjoy:
• 20% off your entire order
• Free delivery
• Priority processing

This offer is valid for the next 30 days and is our way of saying we truly value your partnership.

Ready to order? Simply reply to this email or call [phone number].

Looking forward to working with you again,
[Account Manager Name]"""
                }
            ],
            "budget_allocation": {
                "personal_outreach": "40%",
                "incentives": "35%",
                "email_marketing": "15%",
                "research": "10%"
            },
            "success_metrics": [
                "Win-back rate: Target 15-25%",
                "Time to first re-order: <30 days",
                "Feedback collection rate: >30%"
            ]
        },

        "1": {
            "segment_name": profiles.get("1", {}).get("name", "New Prospects"),
            "priority": "HIGH",
            "objective": "Convert first-time buyers into regular customers",
            "strategy_summary": "Structured onboarding with education and relationship building",
            "tactics": [
                {
                    "name": "Welcome Sequence",
                    "description": "Automated 5-email onboarding series introducing capabilities and team",
                    "timeline": "Days 1-14",
                    "kpi": "Open rate >40%"
                },
                {
                    "name": "Capabilities Presentation",
                    "description": "Schedule video call to showcase full product range and services",
                    "timeline": "Week 2",
                    "kpi": "Meeting rate >30%"
                },
                {
                    "name": "Sample Pack",
                    "description": "Send physical sample pack of popular packaging options",
                    "timeline": "Week 1",
                    "kpi": "Sample conversion >20%"
                },
                {
                    "name": "Second Order Incentive",
                    "description": "10% discount on second order to encourage repeat purchase",
                    "timeline": "Week 3-4",
                    "kpi": "Second order rate >40%"
                }
            ],
            "email_templates": [
                {
                    "name": "Welcome Email",
                    "subject": "Welcome to KSP Packaging, [Company Name]!",
                    "preview": "Thank you for choosing us. Here's what happens next...",
                    "body": """Hi [Contact Name],

Welcome to KSP Packaging! We're thrilled to have [Company Name] as a customer.

Here's what you can expect from us:
• Dedicated account support
• Competitive pricing on custom packaging
• Fast turnaround times
• Quality guaranteed

Your account manager, [Name], will be reaching out shortly to ensure your first order exceeded expectations and to learn more about your packaging needs.

In the meantime, here's a quick guide to our capabilities: [Link]

Thank you for your trust,
The KSP Team"""
                }
            ],
            "budget_allocation": {
                "onboarding_automation": "30%",
                "sample_materials": "25%",
                "sales_outreach": "25%",
                "incentives": "20%"
            },
            "success_metrics": [
                "Second order rate: Target 40%+",
                "Time to second order: <60 days",
                "Onboarding completion: >70%"
            ]
        },

        "2": {
            "segment_name": profiles.get("2", {}).get("name", "Growth Potential"),
            "priority": "HIGH",
            "objective": "Expand wallet share and increase order frequency",
            "strategy_summary": "Consultative selling with cross-sell and upsell focus",
            "tactics": [
                {
                    "name": "Business Review Meeting",
                    "description": "Quarterly review to understand upcoming needs and growth plans",
                    "timeline": "Quarterly",
                    "kpi": "Meeting completion >60%"
                },
                {
                    "name": "Cross-Sell Campaign",
                    "description": "Introduce complementary products based on purchase history",
                    "timeline": "Monthly",
                    "kpi": "Cross-sell rate >15%"
                },
                {
                    "name": "Case Study Sharing",
                    "description": "Share success stories from similar businesses in their industry",
                    "timeline": "Bi-weekly",
                    "kpi": "Engagement rate >25%"
                },
                {
                    "name": "Volume Tier Introduction",
                    "description": "Present volume discount tiers to encourage larger orders",
                    "timeline": "Month 1",
                    "kpi": "Order size increase >20%"
                }
            ],
            "email_templates": [
                {
                    "name": "Growth Partnership",
                    "subject": "[Company Name] - Let's plan for your growth together",
                    "preview": "We've noticed your business expanding. Here's how we can support your journey.",
                    "body": """Hi [Contact Name],

We've noticed [Company Name] has been growing steadily, and we'd love to be part of your continued success.

Based on your ordering patterns, I believe there are opportunities to:
• Reduce your per-unit costs with volume pricing
• Explore additional packaging solutions that might benefit you
• Streamline your ordering process

Would you be open to a 20-minute call to discuss how we can better support your growth?

Best,
[Account Manager Name]"""
                }
            ],
            "budget_allocation": {
                "account_management": "40%",
                "content_marketing": "25%",
                "incentives": "20%",
                "events": "15%"
            },
            "success_metrics": [
                "Revenue growth: Target 25%+ YoY",
                "Product lines used: Increase by 2+",
                "Order frequency: Increase by 30%"
            ]
        },

        "3": {
            "segment_name": profiles.get("3", {}).get("name", "High-Value Regulars"),
            "priority": "PROTECT",
            "objective": "Retain and grow these premium accounts",
            "strategy_summary": "VIP treatment with dedicated support and exclusive benefits",
            "tactics": [
                {
                    "name": "Dedicated Account Manager",
                    "description": "Assign senior account manager with direct line access",
                    "timeline": "Ongoing",
                    "kpi": "CSAT >90%"
                },
                {
                    "name": "VIP Loyalty Program",
                    "description": "Exclusive tier with priority processing, free delivery, early access",
                    "timeline": "Ongoing",
                    "kpi": "Retention >95%"
                },
                {
                    "name": "Executive Relationship Building",
                    "description": "Quarterly lunch/dinner with senior leadership",
                    "timeline": "Quarterly",
                    "kpi": "Engagement maintained"
                },
                {
                    "name": "Innovation Partnership",
                    "description": "First access to new products and invite to co-development",
                    "timeline": "Ongoing",
                    "kpi": "Beta participation >50%"
                }
            ],
            "email_templates": [
                {
                    "name": "VIP Appreciation",
                    "subject": "[Company Name] - You're a VIP Partner",
                    "preview": "A special thank you and exclusive benefits for our valued partners.",
                    "body": """Dear [Contact Name],

On behalf of everyone at KSP Packaging, I want to personally thank [Company Name] for your continued partnership.

As one of our most valued customers, you're now part of our VIP Partner Program, which includes:

• Priority order processing
• Complimentary delivery on all orders
• Direct line to your dedicated account manager
• First access to new products and services
• Invitation to our annual partner appreciation event

Your success is our success, and we're committed to supporting [Company Name] in every way possible.

With gratitude,
[CEO/MD Name]
Managing Director, KSP Packaging"""
                }
            ],
            "budget_allocation": {
                "account_management": "50%",
                "loyalty_benefits": "25%",
                "relationship_events": "15%",
                "innovation_co-development": "10%"
            },
            "success_metrics": [
                "Retention rate: Target 95%+",
                "NPS score: Target 70+",
                "Revenue maintained or grown"
            ]
        },

        "4": {
            "segment_name": profiles.get("4", {}).get("name", "Occasional Buyers"),
            "priority": "MEDIUM",
            "objective": "Increase purchase frequency and reduce gaps",
            "strategy_summary": "Stay top-of-mind with regular touchpoints and seasonal offers",
            "tactics": [
                {
                    "name": "Re-engagement Triggers",
                    "description": "Automated emails triggered at 60, 90, 120 days of inactivity",
                    "timeline": "Automated",
                    "kpi": "Re-engagement rate >20%"
                },
                {
                    "name": "Seasonal Campaigns",
                    "description": "Targeted campaigns around peak packaging seasons",
                    "timeline": "Quarterly",
                    "kpi": "Response rate >10%"
                },
                {
                    "name": "Easy Re-Order System",
                    "description": "One-click reorder functionality for previous orders",
                    "timeline": "Ongoing",
                    "kpi": "Repeat order rate >30%"
                },
                {
                    "name": "Needs Assessment Survey",
                    "description": "Understand if their needs are project-based or if we're missing opportunities",
                    "timeline": "Annually",
                    "kpi": "Survey completion >40%"
                }
            ],
            "email_templates": [
                {
                    "name": "Check-In",
                    "subject": "Quick check-in from KSP Packaging",
                    "preview": "It's been a while - do you have any upcoming packaging needs?",
                    "body": """Hi [Contact Name],

Hope all is well at [Company Name]!

It's been [X] months since we last worked together, and I wanted to check in to see if you have any upcoming packaging needs we can help with.

As a reminder, we offer:
• Custom packaging solutions
• Competitive pricing
• Fast turnaround

Is there anything on the horizon? I'm happy to provide a quick quote.

Best,
[Account Manager Name]"""
                }
            ],
            "budget_allocation": {
                "automation": "35%",
                "seasonal_marketing": "30%",
                "account_outreach": "25%",
                "research": "10%"
            },
            "success_metrics": [
                "Reorder rate: Target 30%+",
                "Gap between orders: Reduce by 20%",
                "Conversion to regular: 10%"
            ]
        }
    }

    return strategies


def get_strategy_for_segment(segment_id: int) -> Dict:
    """Get marketing strategy for a specific segment"""
    strategies = get_marketing_strategies()
    return strategies.get(str(segment_id), {})


def get_email_template(segment_id: int, template_name: str) -> Dict:
    """Get a specific email template for a segment"""
    strategy = get_strategy_for_segment(segment_id)
    templates = strategy.get("email_templates", [])

    for template in templates:
        if template.get("name", "").lower() == template_name.lower():
            return template

    return templates[0] if templates else {}


def get_campaign_recommendations(segment_id: int) -> List[Dict]:
    """Get prioritized campaign recommendations for a segment"""
    strategy = get_strategy_for_segment(segment_id)
    tactics = strategy.get("tactics", [])

    # Sort by implied priority (first tactics are usually highest priority)
    return tactics


def get_kpis_for_segment(segment_id: int) -> List[str]:
    """Get KPIs to track for a segment"""
    strategy = get_strategy_for_segment(segment_id)
    return strategy.get("success_metrics", [])
