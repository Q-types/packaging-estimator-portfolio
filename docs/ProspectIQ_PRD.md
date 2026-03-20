# ProspectIQ - Product Requirements Document

**Version**: 1.0
**Date**: 2026-02-03
**Status**: Science-Fair Level PRD

---

## 1. Executive Summary

ProspectIQ is a B2B lead generation SaaS platform purpose-built for UK packaging and printing companies. It leverages machine learning to analyze a customer's existing client base, automatically build an Ideal Customer Profile (ICP), and score the entire Companies House database (5M+ UK companies) to identify high-probability prospects. By transforming customer data into actionable sales intelligence, ProspectIQ enables printing and packaging businesses to focus their sales efforts on prospects most likely to convert, reducing customer acquisition costs and accelerating growth.

---

## 2. Problem Statement

### Pain Points with Evidence

1. **Sales teams waste time on poor-fit prospects**
   - UK B2B companies spend an average of 40% of sales time on leads that never convert
   - Traditional prospecting relies on gut feel and outdated lists
   - No data-driven way to prioritize outreach

2. **Customer data is underutilized**
   - Most companies have rich data on existing customers but don't analyze it
   - Patterns in high-value vs. low-value customers go unnoticed
   - Manual analysis is time-consuming and rarely done

3. **Generic lead generation tools don't fit the industry**
   - Tools like ZoomInfo, Apollo are generic and expensive (£500+/month)
   - Not calibrated for print/packaging industry specifics
   - Miss industry-relevant signals (SIC codes, manufacturing indicators)

4. **Companies House data is untapped**
   - 5M+ UK companies with free public data
   - Rich signals: industry, age, size, geography, filing patterns
   - But no easy way to score and prioritize

### Current Solutions and Gaps

| Solution | Gap |
|----------|-----|
| Manual prospecting | Time-consuming, inconsistent, not data-driven |
| Generic lead tools (ZoomInfo) | Expensive, not industry-specific, no ICP matching |
| LinkedIn Sales Navigator | Good for people, poor for company-level targeting |
| Industry directories | Static lists, no scoring or prioritization |
| CRM data analysis | Requires data science skills, one-off projects |

### Why Now?

1. **AI/ML adoption accelerating** - SMBs now expect data-driven tools
2. **Companies House API** - Free access to company data enables this business model
3. **Post-pandemic sales transformation** - More digital, more data-driven
4. **Print/packaging consolidation** - Competition driving need for efficiency

---

## 3. Target Users

### Primary Persona: Sales Director Sarah

**Demographics:**
- Age: 35-55
- Role: Sales Director / Commercial Director / Business Development Manager
- Company: SMB printing/packaging company (10-100 employees)
- Revenue: £1M-£20M
- Location: UK

**Behaviors:**
- Manages a team of 2-8 sales reps
- Uses a CRM (often poorly populated)
- Attends industry trade shows (Confex, PackExpo)
- Member of BPIF (British Printing Industries Federation)
- Relies heavily on referrals and existing relationships

**Needs:**
- Consistent pipeline of qualified leads
- Data to support gut instincts about prospects
- Efficiency in a competitive market
- Proof of ROI for any new tool investment

**Frustrations:**
- "We don't know who to target - we chase everyone"
- "Our best customers found us, not the other way around"
- "I know our ideal customer but can't find more like them"
- "Generic tools give us rubbish leads"

### User Journey Map

```
AWARENESS              CONSIDERATION           DECISION              ONBOARDING           SUCCESS
    |                       |                     |                      |                   |
    v                       v                     v                      v                   v
Sees ad/referral    →   Free trial signup   →   Sees own ICP      →   Uploads customers  →  First conversion
at trade show           Upload customer list    Views scored leads     Integrates CRM         from scored lead
    |                       |                     |                      |                   |
Pain: "We need        Discovery: "Wow, it     Validation: "These    Adoption: "Weekly    Growth: "ROI is
more leads"           knows our best          look like our best    reports to team"     proven, expand usage"
                      customer type"          customers"
```

---

## 4. Solution Overview

### Core Value Proposition

**"Find your next 100 best customers from 5 million UK companies."**

ProspectIQ turns your customer data into a prospect-finding machine:
1. Upload your customer list → We build your ICP automatically
2. We score 5M+ UK companies → You get ranked leads with explanations
3. You focus on hot leads → Higher conversion, faster growth

### Key Differentiators

| Differentiator | Why It Matters |
|----------------|----------------|
| **Industry-specific** | Pre-trained on print/packaging data, understands SIC codes 18129, 17230, etc. |
| **ICP-based scoring** | Uses YOUR customer data, not generic scores |
| **UK-focused** | Built on Companies House, understands UK geography and company structures |
| **Explainable AI** | Every score comes with reasons ("Manufacturing company, 15 years old, in your sweet spot") |
| **Affordable** | £299/month vs £500+ for generic tools |

---

## 5. Feature Requirements

### P0 - MVP (Must Have for Launch)

| Feature | Description | Acceptance Criteria |
|---------|-------------|---------------------|
| Customer data upload | CSV upload of existing customers | Support CSV/Excel, map columns, validate data |
| Automatic ICP generation | Analyze customers to build ICP | Industry, age, size, geography profiles with scores |
| Companies House integration | Access to 5M+ UK companies | Daily/weekly data refresh, SIC code mapping |
| Prospect scoring engine | Score prospects against ICP | 0-100 score, Hot/Warm/Cool/Cold tiers |
| Lead list generation | Download ranked prospect lists | CSV export, filter by industry/region/score |
| Basic dashboard | View ICP and lead summaries | Charts, top prospects, segment breakdown |

### P1 - Phase 2 (Important for Adoption)

| Feature | Description |
|---------|-------------|
| CRM integration | Sync with Salesforce, HubSpot |
| Conversion tracking | Track which leads converted, improve scoring |
| Email alerts | Daily/weekly hot lead notifications |
| Saved filters | Save and reuse search criteria |
| Team collaboration | Multiple users, shared lists |
| Enriched data | Add LinkedIn, website, contact info |

### P2 - Nice to Have (Future Roadmap)

| Feature | Description |
|---------|-------------|
| Industry benchmarking | "Companies like you target these industries" |
| Predictive churn | Alert when existing customers at risk |
| Competitor intelligence | Track companies switching from competitors |
| API access | Programmatic access for power users |
| Custom scoring models | Fine-tune weights for specific use cases |

---

## 6. User Stories

### US1: First-Time Upload
**As a** Sales Director
**I want to** upload my customer list
**So that** the system can learn my ideal customer profile

**Acceptance Criteria:**
- [ ] Can upload CSV or Excel file
- [ ] System maps columns (company name, revenue, dates)
- [ ] Enriches data via Companies House matching
- [ ] Shows ICP within 5 minutes
- [ ] Handles up to 10,000 customers

### US2: View My ICP
**As a** Sales Director
**I want to** see my Ideal Customer Profile
**So that** I understand what makes a good customer for my business

**Acceptance Criteria:**
- [ ] Shows top industries with conversion rates
- [ ] Shows optimal company age range
- [ ] Shows geographic hotspots
- [ ] Shows company size indicators
- [ ] Explains each factor with data

### US3: Get Hot Leads
**As a** Sales Rep
**I want to** see a list of hot prospects
**So that** I can prioritize my outreach

**Acceptance Criteria:**
- [ ] List sorted by score (highest first)
- [ ] Each lead shows: name, industry, age, region, score
- [ ] Each lead explains why it scored high
- [ ] Can filter by industry, region, score
- [ ] Can export to CSV

### US4: Score a Specific Company
**As a** Sales Rep
**I want to** look up a specific company
**So that** I can see if they're worth pursuing

**Acceptance Criteria:**
- [ ] Search by company name or number
- [ ] Shows full profile and ICP score
- [ ] Shows how it compares to similar customers
- [ ] Suggests talking points

### US5: Weekly Lead Report
**As a** Sales Director
**I want to** receive weekly lead reports
**So that** I can distribute leads to my team

**Acceptance Criteria:**
- [ ] Email delivered every Monday 8am
- [ ] Shows top 50 new hot leads
- [ ] Shows industry/region breakdown
- [ ] One-click to full dashboard

### US6: Track Conversions
**As a** Sales Director
**I want to** mark which leads converted
**So that** the system improves over time

**Acceptance Criteria:**
- [ ] Can mark lead as "Contacted" / "Meeting" / "Won" / "Lost"
- [ ] System learns from outcomes
- [ ] Shows conversion rate by score tier
- [ ] Adjusts ICP based on real conversions

### US7: Filter by Geography
**As a** Regional Sales Rep
**I want to** see leads in my territory
**So that** I only see relevant prospects

**Acceptance Criteria:**
- [ ] Filter by postcode area, county, or region
- [ ] Save territory as default filter
- [ ] Map visualization of leads

---

## 7. Technical Considerations

### Recommended Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Frontend** | Next.js 14 / SvelteKit | Fast, SEO-friendly, great DX |
| **Backend** | Python FastAPI | ML integration, async performance |
| **Database** | PostgreSQL + Supabase | Proven, scalable, real-time features |
| **ML Pipeline** | scikit-learn, pandas | ICP modeling, scoring engine |
| **Data Storage** | S3/R2 | Companies House bulk data |
| **Auth** | Supabase Auth / Clerk | Simple, secure |
| **Hosting** | Vercel + Railway/Render | Easy deployment, auto-scaling |

### Key Integrations

1. **Companies House API** (Free)
   - Bulk data download (monthly)
   - Real-time lookup for enrichment
   - Officer and filing data

2. **CRM Integrations** (Phase 2)
   - Salesforce (SFDC API)
   - HubSpot (Free tier available)
   - Pipedrive

3. **Email/Notifications**
   - Resend / SendGrid for alerts
   - Slack webhook for real-time

### Scalability Notes

- Companies House bulk data: ~5GB, preprocessed daily
- ICP computation: <1 minute for 10K customers
- Scoring: 1M companies/hour
- Database: Partition by customer, index by score
- Consider caching hot leads per customer

---

## 8. Success Metrics & KPIs

### North Star Metric

**Leads Converted per Month per Customer**

This measures the ultimate value: did our leads turn into revenue?

### Leading Indicators

| Metric | Target | Why It Matters |
|--------|--------|----------------|
| Weekly Active Users | 70%+ | Engagement indicates value |
| Hot Leads Viewed | 100/week/user | Are they using the data? |
| Leads Exported | 50/week/user | Taking action |
| ICP Refresh Rate | Monthly | Keeping model updated |
| Time to First Lead | <10 min | Onboarding success |

### Lagging Indicators

| Metric | Target | Why It Matters |
|--------|--------|----------------|
| Conversion Rate (Hot) | 5%+ | Lead quality |
| Customer Retention | 90%+ | Product-market fit |
| NPS | 40+ | Customer satisfaction |
| MRR Growth | 10%/month | Business health |

---

## 9. Go-to-Market Strategy

### Launch Approach

**Phase 1: Founder-Led Sales (Month 1-3)**
- Target: 10 pilot customers
- Price: £199/month (early adopter)
- Offer: White-glove onboarding
- Goal: Validate, learn, iterate

**Phase 2: Industry Launch (Month 4-6)**
- Target: 50 customers
- Channels: BPIF partnership, trade shows
- Content: Case studies from pilots
- Price: Standard £299/month

**Phase 3: Scale (Month 7-12)**
- Target: 200 customers
- Expand: Adjacent industries (labels, signs)
- Product: Self-serve onboarding
- Marketing: SEO, LinkedIn ads

### Initial Channels

| Channel | Approach | Expected CAC |
|---------|----------|--------------|
| **Trade Shows** | Booth at Confex, PackExpo | £500-1,000 |
| **BPIF Partnership** | Member discount, webinars | £200-400 |
| **LinkedIn Ads** | Target Sales Directors in print | £300-600 |
| **Content/SEO** | "Find print customers" keywords | £100-200 |
| **Referrals** | £100 credit per referral | £100 |

---

## 10. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Companies House data quality | Med | Med | Supplement with web scraping, manual verification |
| Low conversion rates | High | Med | Focus on explainability, allow ICP tuning |
| Price sensitivity | Med | High | Offer freemium tier, prove ROI quickly |
| CRM integration complexity | Med | Med | Start with CSV export, add integrations later |
| Competitor response | Low | Med | Move fast, build industry expertise moat |
| GDPR compliance | Med | Low | B2B public data is generally exempt, document process |

---

## 11. Open Questions

1. **Pricing sensitivity**: Is £299/month the right price point? Need to test with pilots.

2. **Data enrichment**: Should we add contact info (emails, phones) or stay company-level?

3. **Freemium**: Would a free tier (10 leads/month) drive adoption or devalue the product?

4. **Adjacent markets**: Which industries to expand to first? Signs? Labels? Packaging machinery?

5. **Partnership model**: Could we white-label for CRM providers or industry associations?

6. **International expansion**: Would the model work for Ireland, Germany, France (different company registries)?

---

## 12. PMF Assessment

### Quick PMF Score

| Dimension | Score | Notes |
|-----------|-------|-------|
| Problem Clarity | 8/10 | Clear pain, quantifiable waste |
| Market Size | 6/10 | 5,000 UK print companies × £300 × 12 = £18M SAM |
| Uniqueness | 7/10 | Industry-specific is key differentiator |
| Feasibility | 9/10 | Tech exists, can build MVP fast |
| Monetization | 8/10 | Clear value, comparable to alternatives |
| Timing | 8/10 | AI adoption accelerating in SMBs |
| Virality | 5/10 | B2B, limited sharing, but referrals work |
| Defensibility | 7/10 | Data moat grows with customers |
| Team Fit | 8/10 | Good for small technical team |
| Ralph Factor | 7/10 | Useful but not revolutionary |

**Average: 7.3/10** - Good foundation, focus on proving conversion rates with pilots.

---

## 13. Implementation Architecture

### Recommended Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | SvelteKit (fast, modern) |
| **Backend** | Python FastAPI + Supabase |
| **Database** | PostgreSQL (Supabase) |
| **Auth** | Supabase Auth |
| **ML** | scikit-learn, pandas |
| **Deployment** | Vercel (frontend) + Railway (backend) |

### Spawner Skills to Use

- **SvelteKit** - Frontend framework
- **Supabase Backend** - Database, auth, real-time
- **TypeScript Strict Mode** - Type safety
- **API Designer** - FastAPI endpoints
- **LLM Architect** - Explainable scoring

### Implementation Phases

**Phase 1: Foundation (2 weeks)**
- Database schema
- Auth flow
- Basic dashboard layout
- CSV upload

**Phase 2: Core Features (4 weeks)**
- ICP generation engine
- Companies House integration
- Scoring pipeline
- Lead list views

**Phase 3: Polish & Launch (2 weeks)**
- Email notifications
- Export functionality
- Onboarding flow
- Documentation

---

*PRD Generated by Ralph + Claude | PackagePro Project*
