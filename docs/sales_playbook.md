# PackagePro Sales Playbook

A practical guide for the PackagePro sales team to leverage customer segmentation and prospect scoring effectively.

---

## Quick Reference

### Segment Quick Guide

| Segment | Characteristics | Priority | Key Action |
|---------|----------------|----------|------------|
| **High-Value Regulars** | High spend, frequent orders, loyal | Protect | VIP treatment, prevent churn |
| **Core Customers** | Steady business, medium value | Grow | Upsell, cross-sell |
| **Growth Potential** | Low activity but potential | Develop | Re-engage, nurture |

### Priority Tiers for Prospects

| Score | Tier | Meaning | Action |
|-------|------|---------|--------|
| 75+ | **Hot** | Strong ICP fit | Immediate outreach |
| 60-74 | **Warm** | Good potential | Add to nurture campaign |
| 45-59 | **Cool** | Moderate fit | Qualify further |
| <45 | **Cold** | Poor fit | Low priority |

---

## Understanding Customer Segments

### Segment 0: High-Value Regulars (38% of customers)

**Who they are:**
- Highest revenue generators
- Order frequently (16+ orders on average)
- Established companies (avg. 22 years old)
- Strong loyalty and relationship history

**Key metrics:**
- Average total spend: £51,500+
- Average recency: ~900 days (includes long-term historic customers)
- Most common industries: Manufacturing, Wholesale, Admin Services

**What they value:**
- Reliability and consistency
- Quality products
- Responsive service
- Competitive pricing for volume

**Engagement strategy:**
1. Assign dedicated account manager
2. Quarterly business reviews
3. Early access to new products
4. Volume discounts and loyalty rewards
5. Priority support when issues arise

**Warning signs of churn:**
- Order frequency declining
- Smaller order values
- Reduced communication
- Complaints about quality or service

**Talking points:**
> "Thank you for being a valued long-term customer. We'd like to schedule a review to ensure we're meeting all your packaging needs and discuss any upcoming projects."

> "As one of our VIP customers, you'll have first access to our new [product line]. Would you like me to send samples?"

---

### Segment 1: Core Customers (56% of customers)

**Who they are:**
- The backbone of the business
- Lower individual value but high collective importance
- Often newer or occasional buyers
- Diverse industries

**Key metrics:**
- Average total spend: £2,500
- Average orders: 1-2 per customer
- Average recency: ~1,400 days (many one-time)

**What they value:**
- Good value for money
- Easy ordering process
- Clear communication
- Flexible minimum orders

**Engagement strategy:**
1. Regular touchpoints (quarterly emails)
2. Educational content about products
3. Cross-sell complementary products
4. Referral incentives
5. Reactivation campaigns for dormant customers

**Growth tactics:**
- Bundle offers for larger orders
- Introduce premium product options
- Share case studies from similar companies
- Offer samples of new products

**Talking points:**
> "I noticed you ordered [product] last year. Many of our customers also use [complementary product]. Would you like me to send information?"

> "We're offering 15% off for orders over £X this month. Given your typical order size, this could save you money while building inventory."

---

### Segment 2: Growth Potential (1.5% of customers)

**Who they are:**
- Low current value but identified potential
- Recent contact but little purchase history
- Often newer companies or first-time buyers
- May have budget constraints

**Key metrics:**
- Average total spend: £967
- Higher than average recency (need re-engagement)
- Moderate company age

**What they value:**
- Flexibility and patience
- Understanding of their constraints
- Growth partnership mentality
- Guidance on product selection

**Engagement strategy:**
1. Understand their specific needs
2. Offer starter packages
3. Provide educational resources
4. Build relationship over transactions
5. Long-term nurturing approach

**Talking points:**
> "I understand you're growing your business. Let's discuss packaging solutions that can scale with you and stay within your current budget."

> "Many of our successful customers started small and grew with us. What are your goals for the next 6-12 months?"

---

## Using the Sales Tools

### 1. Sales Dashboard (CLI)

The sales dashboard provides quick access to customer data from the command line.

#### View Segment Overview
```bash
python scripts/sales_dashboard.py segments
```
Use this to: Start your day with a portfolio overview

#### Look Up a Customer
```bash
python scripts/sales_dashboard.py customer "Artisan Print"
```
Use this to: Prepare for a call, check customer status

#### Find At-Risk Customers
```bash
python scripts/sales_dashboard.py at-risk --limit 30
```
Use this to: Identify customers needing immediate attention

#### Find Upsell Opportunities
```bash
python scripts/sales_dashboard.py upsell
```
Use this to: Plan your weekly outreach for growth

#### Score a New Prospect
```bash
python scripts/sales_dashboard.py score-prospect \
    --name "ABC Packaging Ltd" \
    --sic 18129 \
    --age 12 \
    --region "London"
```
Use this to: Prioritize new leads, prepare for prospecting calls

---

### 2. Weekly Sales Report

Generate a comprehensive weekly report:

```bash
python scripts/generate_sales_report.py
```

The report includes:
- Executive summary with key metrics
- Segment health overview
- At-risk customer alerts with priority list
- Upsell opportunities with potential value
- Industry insights
- Weekly action items checklist

**Best practice:** Generate every Monday morning and review with the team.

---

### 3. Customer API

For integration with other tools or a sales dashboard UI:

```bash
# Start the API server
python scripts/customer_api.py --port 8000
```

**Key endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/customer/{name}` | GET | Look up customer profile |
| `/customers/search?q=term` | GET | Search customers |
| `/segment/{id}` | GET | Get segment details |
| `/segments` | GET | List all segments |
| `/score` | POST | Score a prospect |
| `/at-risk` | GET | List at-risk customers |
| `/opportunities` | GET | List upsell opportunities |
| `/stats` | GET | Portfolio statistics |

**Example API calls:**

```bash
# Get customer profile
curl http://localhost:8000/customer/Artisan%20Print

# Score a prospect
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{"name": "New Co Ltd", "sic_code": "18129", "company_age_years": 10}'

# Get at-risk customers
curl http://localhost:8000/at-risk?limit=10
```

---

## Handling Common Situations

### Situation 1: Customer Hasn't Ordered in 6+ Months

**Approach:**
1. Check their profile: `python sales_dashboard.py customer "Company Name"`
2. Review their order history and segment
3. Prepare for outreach based on their value tier

**For High-Value customers:**
- Personal phone call from senior team member
- Acknowledge gap in orders directly
- Understand if there's an issue
- Offer to resolve any concerns

**For Core customers:**
- Email with special offer
- Highlight new products relevant to their history
- Include easy re-order link

**Script:**
> "Hi [Name], I noticed we haven't heard from you in a while. I wanted to personally check in - is there anything we could have done better? We value your business and I'd love to understand how we can help."

---

### Situation 2: Customer Asking for Big Discount

**Approach:**
1. Check their value tier and history
2. Understand total relationship value
3. Consider volume commitment in exchange

**For High-Value customers:**
- More flexibility; protect the relationship
- Offer volume-based pricing tiers
- Consider exclusive terms for commitment

**For Core customers:**
- Explain value proposition
- Offer bundle deals instead of straight discounts
- Suggest ways to achieve better pricing through volume

**Script:**
> "I understand price is important. Let me look at what we can do. If you can commit to [volume] over the next [period], I can offer [specific terms]. This gives you better pricing while helping us plan production."

---

### Situation 3: New Prospect Inquiry

**Approach:**
1. Score the prospect: `python sales_dashboard.py score-prospect ...`
2. Prioritize based on tier (Hot/Warm/Cool/Cold)
3. Tailor response based on ICP fit

**For Hot prospects (75+ score):**
- Immediate personal response
- Offer site visit or samples
- Fast-track quote process
- Senior team involvement

**For Warm prospects (60-74):**
- Response within 24 hours
- Qualify needs thoroughly
- Provide educational materials
- Add to nurture campaign

**For Cool/Cold prospects (<60):**
- Standard response time
- Automated nurture sequence
- Don't over-invest time
- Qualify harder before commitment

---

### Situation 4: Identifying Upsell Opportunity

**Approach:**
1. Run upsell report: `python sales_dashboard.py upsell`
2. Review customer's current product mix
3. Identify gaps or upgrade opportunities

**Strategies:**
1. **Product upgrade:** Suggest premium version of current orders
2. **Cross-sell:** Introduce complementary products
3. **Volume increase:** Offer better rates for larger orders
4. **New categories:** Explore unmet needs

**Script:**
> "I was reviewing your account and noticed you regularly order [product]. Many similar customers also find value in [related product]. Would you like me to send samples or pricing?"

---

## Key Performance Indicators (KPIs)

### Weekly Metrics to Track

| Metric | Target | How to Measure |
|--------|--------|----------------|
| At-risk customers contacted | 100% of top 5 | Check list weekly |
| Win-back rate | >20% | Track reactivations |
| Upsell conversations | 10+ per week | Log in CRM |
| New prospect scores | Track all leads | Use scorer |
| Customer satisfaction | >4.5/5 | Survey feedback |

### Monthly Review

1. **Segment health:** Are segments stable or shifting?
2. **Revenue by segment:** Where is growth/decline?
3. **At-risk trend:** Improving or worsening?
4. **New customer acquisition:** Quality and quantity
5. **Upsell success rate:** Conversion of opportunities

---

## Industry-Specific Notes

### Manufacturing (Highest Value Sector)

**Why they're valuable:**
- 26% of customers, 31% of high-value customers
- Lift ratio: 1.18x (18% more likely to become high-value)
- High volume, repeat needs
- Often packaging for products

**Talking points:**
- Emphasize production consistency
- Discuss just-in-time delivery options
- Highlight quality certifications
- Explore co-design opportunities

### Wholesale & Retail (12% of customers)

**Why they're valuable:**
- Product packaging for resale
- Regular ordering patterns
- Brand consciousness

**Talking points:**
- Discuss branding and customization
- Explore seasonal needs
- Offer inventory planning support

### Administrative Services (6% of customers)

**Why they're valuable:**
- Lift ratio: 1.22x (best performer)
- Often order for multiple clients
- Strong growth potential

**Talking points:**
- Explore white-label options
- Discuss referral partnerships
- Offer multi-account management

---

## Escalation Guide

### When to Escalate

| Situation | Escalate To | Timeframe |
|-----------|-------------|-----------|
| High-value customer complaint | Sales Manager | Same day |
| Lost major account | Sales Director | Immediately |
| Quality issue affecting multiple customers | Ops + Sales Manager | Same day |
| Pricing dispute >£1,000 | Sales Manager | Within 24 hours |
| Legal/contract issues | Sales Director + Legal | Immediately |

### How to Escalate

1. Document the situation clearly
2. Include customer segment and value
3. Summarize actions already taken
4. Propose recommended solution
5. Identify urgency level

---

## Quick Tips

1. **Start your day** with the at-risk report - 5 minutes can prevent losing a customer
2. **Before any call**, check the customer profile - know their segment and history
3. **Score every prospect** - don't waste time on poor fits
4. **Weekly report review** - use Monday mornings to plan the week
5. **Track everything** - notes help the next conversation
6. **High-value = high touch** - these customers deserve your time
7. **Don't ignore Core customers** - collectively they matter
8. **Ask why** - understand reasons behind decisions
9. **Follow up** - persistence pays, especially for warm prospects
10. **Celebrate wins** - share success stories with the team

---

## Contact & Support

For questions about the tools or this playbook:
- **Analytics Team:** analytics@ksp.com
- **Sales Dashboard Issues:** Create ticket in internal system
- **API Access:** Contact IT for credentials

*This playbook is updated quarterly. Last update: February 2026*
