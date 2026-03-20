# B2B Lead Scoring System for PackagePro

## Executive Summary

This document describes a comprehensive lead scoring system that identifies prospects most likely to become high-value customers for PackagePro. The system uses **Ideal Customer Profile (ICP) analysis** to find "lookalike" companies that share characteristics with PackagePro's best existing customers.

**Key Insight**: We score prospects using only pre-purchase characteristics (industry, company age, size, location) - enabling scoring of any UK company before they've ever ordered.

---

## 1. Ideal Customer Profile (ICP) Analysis

Based on analysis of **867 existing customers**, with **330 classified as high-value** (38% of customer base), we've identified the following patterns:

### 1.1 Industry Characteristics

**Top Industries by Lift Ratio** (likelihood to become high-value vs baseline):

| Industry | Lift Ratio | % of HV Customers | Score Weight |
|----------|------------|-------------------|--------------|
| Agriculture | 1.75x | 0.6% | 100 |
| Real Estate | 1.37x | 3.6% | 78 |
| Health & Social | 1.31x | 2.1% | 75 |
| Transport & Storage | 1.31x | 1.5% | 75 |
| Administrative Services | 1.22x | 7.9% | 70 |
| Manufacturing | 1.18x | 30.6% | 67 |
| Wholesale & Retail | 1.08x | 13.0% | 61 |

**Key Finding**: While Manufacturing has the highest *volume* of high-value customers (30.6%), industries like Real Estate and Administrative Services have higher *lift ratios*, meaning a prospect in those industries is more likely to become high-value.

### 1.2 Top SIC Codes (Specific Industries)

The following SIC codes show the strongest correlation with high-value customers:

| SIC Code | Description | Lift Ratio | Count |
|----------|-------------|------------|-------|
| 46180 | Wholesale of other machinery/equipment | 2.63x | 3 |
| 7487 | Other business activities | 2.10x | 5 |
| 22290 | Manufacture of other plastic products | 2.04x | 9 |
| 17230 | Manufacture of paper stationery | 2.04x | 9 |
| 18129 | Other printing | 1.26x | 131 |
| 82990 | Other business support services | 1.12x | 47 |

**Recommendation**: Prioritize prospects with SIC codes in manufacturing (17xxx, 18xxx, 22xxx) and business services (82xxx).

### 1.3 Company Age Profile

**Optimal Age Range**: 7-29 years

| Age Bracket | Score Multiplier |
|-------------|-----------------|
| < 5 years | 0.5 (too young, unproven) |
| 5-10 years | 0.7 (emerging) |
| **10-30 years** | **1.0 (optimal)** |
| 30-50 years | 0.9 (mature, established) |
| > 50 years | 0.7 (very mature) |

**High-Value Customer Stats**:
- Median age: 16.6 years
- Mean age: 21.7 years

### 1.4 Company Size Indicators

**Optimal Ranges**:

| Indicator | Optimal Range | HV Median |
|-----------|---------------|-----------|
| Officer Count | 2-7 | 4 |
| Filing Count | 14-89 | 40 |
| Has Charges | 39% rate | - |

**Interpretation**:
- Small-medium businesses (2-7 officers) are the sweet spot
- Filing count is a proxy for company maturity and activity
- Having charges (bank loans/overdrafts) indicates established credit - a positive signal

### 1.5 Geographic Patterns

**Top Regions by Lift** (over-representation of high-value customers):

1. Gloucestershire (100% score)
2. Derbyshire (100% score)
3. Buckinghamshire (94%)
4. Leeds (80%)
5. West Yorkshire (78%)
6. Warwickshire (77%)
7. Oxford (75%)
8. Liverpool (75%)
9. Berkshire (75%)
10. Cornwall (75%)

**Volume Leaders** (most HV customers by count):
1. London (13%)
2. Surrey (3.6%)
3. Oxfordshire (3.6%)
4. Buckinghamshire (2.7%)

### 1.6 Web Presence

| Metric | All Customers | High-Value | Boost Factor |
|--------|---------------|------------|--------------|
| Has Website | 79.5% | 89.4% | 1.12x |
| Has HTTPS | 57.4% | Higher | Positive signal |

**Takeaway**: Having a professional web presence correlates with being a high-value customer.

---

## 2. Lookalike Model Architecture

### 2.1 Model Design

The system uses a **hybrid scoring approach**:

1. **Rule-Based Scoring** (70% weight): Explicit scores based on ICP characteristics
2. **ML Model** (30% weight): Gradient Boosting classifier trained on customer data

### 2.2 Feature Importance (from ML model)

| Feature | Importance |
|---------|------------|
| Company Age | 42% |
| Filing Count | 24% |
| Officer Count | 13% |
| Has Website | 11% |
| Industry Dummies | 10% |

### 2.3 Scoring Formula

```
Final Score = (Industry Score * 0.30) +
              (Company Age Score * 0.20) +
              (Company Size Score * 0.25) +
              (Geography Score * 0.10) +
              (Web Presence Score * 0.15)
```

### 2.4 Priority Tiers

| Tier | Score Range | Expected Quality |
|------|-------------|------------------|
| Hot | 75-100 | High conversion probability |
| Warm | 60-74 | Good fit, needs nurturing |
| Cool | 45-59 | Moderate fit |
| Cold | < 45 | Poor ICP match |

---

## 3. Prospect Data Sources

### 3.1 Free Sources

#### Companies House Bulk Data (Recommended)
- **URL**: https://www.gov.uk/guidance/companies-house-data-products
- **Content**: All UK registered companies (5M+)
- **Fields**: Company name, number, status, SIC codes, incorporation date, registered address
- **Format**: CSV/JSON
- **Update**: Monthly
- **Cost**: Free

**Download**: https://download.companieshouse.gov.uk/en_output.html

#### Companies House API
- **URL**: https://developer.company-information.service.gov.uk/
- **Rate Limit**: 600 requests/minute
- **Cost**: Free (API key required)
- **Use Case**: Enrich prospects with officer/filing data

### 3.2 Commercial Sources

| Source | Pros | Cons | Cost |
|--------|------|------|------|
| **LinkedIn Sales Navigator** | Rich profiles, direct contact | Limited export, manual | $$$ |
| **Dun & Bradstreet** | Financial data, global | Expensive, enterprise focus | $$$$ |
| **ZoomInfo** | Contact details, intent data | US-focused | $$$$ |
| **Beauhurst** | UK startups, growth companies | Startup focus | $$$ |
| **Fame (Bureau van Dijk)** | Full financials | Expensive | $$$$ |

### 3.3 Industry-Specific Sources

For PackagePro's target market (packaging buyers):

| Source | Type | Notes |
|--------|------|-------|
| **BPIF Directory** | Print industry | British Printing Industries Federation members |
| **The Packaging Federation** | Trade body | Member directory |
| **Confex/PackExpo** | Trade shows | Exhibitor/attendee lists |
| **LinkedIn Groups** | Social | "UK Packaging Professionals" etc |
| **Thomasnet UK** | Industrial directory | Manufacturers, suppliers |

### 3.4 DIY Data Collection

```python
# Example: Load Companies House basic company data
from prospect_scorer import CompaniesHouseLoader, ProspectScorer, ICPProfile

# Load ICP profile
icp = ICPProfile.load('models/prospect_scorer/icp_profile.json')

# Initialize scorer
scorer = ProspectScorer(icp=icp)

# Load Companies House data
loader = CompaniesHouseLoader()
prospects_df = loader.load_basic_company_data('data/prospects/BasicCompanyData.csv')

# Filter to target industries
target_sics = ['18129', '17230', '22290', '82990', '74100']
prospects_df = prospects_df[
    prospects_df['sic_codes'].str.contains('|'.join(target_sics), na=False)
]

# Score all prospects
scored_df = scorer.score_batch(prospects_df)

# Get top 500 hot leads
hot_leads = scored_df[scored_df['priority_tier'] == 'Hot'].head(500)
```

---

## 4. Lead Scoring Pipeline

### 4.1 Architecture

```
                                    +------------------+
                                    |   ICP Profile    |
                                    | (from existing   |
                                    |   customers)     |
                                    +--------+---------+
                                             |
+------------------+    +------------------+ |  +------------------+
| Companies House  |--->| Feature          |-+->| Prospect Scorer  |
| Bulk Data        |    | Extraction       |    | (ML + Rules)     |
+------------------+    +------------------+    +--------+---------+
                                                        |
+------------------+    +------------------+            |
| Trade Shows      |--->| Data             |            |
| Industry Lists   |    | Standardization  |------------+
+------------------+    +------------------+            |
                                                        v
                                               +------------------+
                                               | Ranked Lead List |
                                               | - Score 0-100    |
                                               | - Priority Tier  |
                                               | - Score Reasons  |
                                               +------------------+
```

### 4.2 Implementation Steps

1. **Build ICP** (one-time, refresh quarterly)
   ```bash
   python scripts/prospect_scorer.py build-icp
   ```

2. **Acquire Prospect Data**
   - Download Companies House bulk data
   - Filter to active companies
   - Optionally enrich with officer/filing data via API

3. **Score Prospects**
   ```bash
   python scripts/prospect_scorer.py score \
       --icp models/prospect_scorer/icp_profile.json \
       --prospects data/prospects/companies.csv \
       --output scored_leads.csv \
       --top-n 1000
   ```

4. **Export to CRM**
   - Upload scored leads to Salesforce/HubSpot
   - Assign to sales team based on priority tier

### 4.3 Ongoing Operations

| Task | Frequency | Description |
|------|-----------|-------------|
| ICP Refresh | Quarterly | Rebuild with latest customer data |
| Prospect Scoring | Monthly | Score new Companies House data |
| Model Validation | Quarterly | Check conversion rates by tier |
| Feature Engineering | As needed | Add new signals (web scraping, etc) |

---

## 5. Model Validation Strategy

### 5.1 The Challenge

We can't validate in real-time because:
- Conversion happens over months/years
- Most prospects never contacted
- Sales cycle is long

### 5.2 Validation Approaches

#### A. Historical Back-testing
1. Take customers who converted in past 12 months
2. Score them using only pre-conversion data
3. Check: Did high-scorers have higher conversion rates?

#### B. A/B Testing Sales Outreach
1. Split sales team into two groups
2. Group A: Prioritize Hot leads
3. Group B: Random selection
4. Compare conversion rates after 6 months

#### C. Cohort Analysis
1. Track prospects scored this quarter
2. After 12 months, check how many converted
3. Compare conversion by score tier

#### D. Early Engagement Signals
Track leading indicators:
- Quote request rate by tier
- Sample request rate
- Website visit rate (if tracked)

### 5.3 Expected Performance

Based on the ICP analysis:

| Tier | % of Prospects | Expected Conversion | Lift vs Random |
|------|----------------|---------------------|----------------|
| Hot | ~5% | 2-3x baseline | 2-3x |
| Warm | ~15% | 1.5x baseline | 1.5x |
| Cool | ~30% | 1x baseline | 1x |
| Cold | ~50% | 0.5x baseline | 0.5x |

**Note**: The ML model AUC of 0.57 is modest because pre-purchase characteristics have limited predictive power. The real value is in **prioritization** - focusing sales effort on the most promising leads.

---

## 6. Usage Examples

### 6.1 Score a Single Prospect

```python
from prospect_scorer import ProspectScorer, ICPProfile

# Load ICP
icp = ICPProfile.load('models/prospect_scorer/icp_profile.json')
scorer = ProspectScorer(icp=icp)

# Score a prospect
prospect = {
    'company_name': 'Acme Packaging Ltd',
    'industry_sector': 'Manufacturing',
    'sic_codes': '18129,82990',
    'company_age_years': 15,
    'officer_count': 4,
    'filing_count': 45,
    'has_charges': True,
    'region': 'Leeds',
    'has_website': True,
    'has_https': True
}

result = scorer.score_prospect(prospect)

print(f"Score: {result['prospect_score']}")
print(f"Tier: {result['priority_tier']}")
print(f"Reasons:")
for dimension, reason in result['score_reasons'].items():
    print(f"  {dimension}: {reason}")
```

### 6.2 Batch Scoring with CLI

```bash
# Full pipeline - builds ICP if needed, scores prospects
python scripts/prospect_scorer.py pipeline \
    --prospects data/companies_house/BasicCompanyData.csv \
    --top-n 500 \
    --output reports/hot_leads_2026_q1.csv
```

### 6.3 Integration with CRM

```python
import pandas as pd
from prospect_scorer import ProspectScorer, ICPProfile

# Load and score
icp = ICPProfile.load('models/prospect_scorer/icp_profile.json')
scorer = ProspectScorer(icp=icp)
prospects = pd.read_csv('new_prospects.csv')
scored = scorer.score_batch(prospects)

# Format for CRM import
crm_export = scored[['company_name', 'company_number', 'prospect_score',
                      'priority_tier', 'industry_sector', 'region']]
crm_export.columns = ['Name', 'CompaniesHouseNumber', 'LeadScore',
                       'Priority', 'Industry', 'Region']
crm_export.to_csv('crm_import.csv', index=False)
```

---

## 7. Future Enhancements

### 7.1 Additional Data Sources

- **Web scraping**: Extract employee count from LinkedIn
- **News monitoring**: Track growth signals (funding, expansion)
- **Intent data**: Website visit tracking (if implemented)

### 7.2 Model Improvements

- **Conversion feedback loop**: Retrain when we have outcome data
- **Seasonal patterns**: Adjust for industry cycles
- **Recency weighting**: Score recent Companies House filings higher

### 7.3 Automation

- **Scheduled scoring**: Daily/weekly pipeline
- **CRM integration**: Direct Salesforce/HubSpot sync
- **Alerting**: Notify sales when high-score prospect identified

---

## Appendix: Files Created

| File | Description |
|------|-------------|
| `scripts/prospect_scorer.py` | Main scoring module |
| `models/prospect_scorer/icp_profile.json` | ICP profile data |
| `models/prospect_scorer/lookalike_model.joblib` | Trained ML model |
| `docs/lead_scoring_guide.md` | This documentation |

## Appendix: SIC Code Reference

Key SIC codes for packaging/print customers:

| SIC | Description |
|-----|-------------|
| 17230 | Manufacture of paper stationery |
| 17290 | Manufacture of other articles of paper |
| 18110 | Printing of newspapers |
| 18121 | Manufacture of printed labels |
| 18129 | Other printing |
| 18130 | Pre-press services |
| 18140 | Binding services |
| 22210 | Manufacture of plastic packaging |
| 22290 | Manufacture of other plastic products |
| 82990 | Other business support services |
