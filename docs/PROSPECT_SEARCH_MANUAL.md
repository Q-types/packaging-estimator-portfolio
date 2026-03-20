# PackagePro Prospect Search - User Manual

## Overview

The PackagePro Prospect Search system helps you find potential packaging clients from the UK Companies House registry. It automatically scores companies based on their fit for PackagePro's bespoke packaging services and filters out competitors.

**Access the UI:** http://localhost:8000/prospects

---

## Quick Start

1. **Search for prospects** using company name, location, or industry codes
2. **Enrich** prospects with detailed company data
3. **Score** prospects to identify the best leads
4. **Filter** by tier (Hot/Warm/Cool/Cold) to prioritize outreach

---

## Dashboard Overview

### Stats Cards (Top of Page)

| Card | Description |
|------|-------------|
| **Total Prospects** | All prospects in the database |
| **Hot Prospects** | Score 75+ (best leads) |
| **Warm Prospects** | Score 60-74 (good leads) |
| **Avg Score** | Average score across all prospects |

---

## Searching Companies House

### Search Panel

Located at the top of the page, the search panel lets you find companies from the UK Companies House registry.

#### Search Fields

| Field | Description | Example |
|-------|-------------|---------|
| **Search Query** | Company name or keyword | `bakery`, `cosmetics` |
| **Location** | Postcode area or city | `London`, `B1`, `Manchester` |
| **SIC Codes** | Industry classification codes (comma-separated) | `10710, 20420` |
| **Company Status** | Filter by active/dissolved | `Active` (recommended) |
| **Max Results** | Number of companies to fetch | `50`, `100`, `250`, `500` |
| **Auto-score** | Automatically score results | ✓ (recommended) |

#### Recommended SIC Codes for PackagePro

| Industry | SIC Code | Bespoke Fit |
|----------|----------|-------------|
| Bakeries/Confectionery | `10710`, `10820` | 95% |
| Cosmetics/Perfumes | `20420` | 95% |
| Distilleries/Wine | `11010`, `11020` | 95% |
| Jewellery | `32120`, `47770` | 95% |
| E-commerce | `47910` | 90% |
| Coffee/Tea | `10830` | 90% |
| Artisan Foods | `10390`, `10890` | 85% |

### How to Search

1. Enter your search criteria
2. Click **"Search Companies House"**
3. Wait for results (shown in green bar)
4. Prospects are automatically added to your database

---

## Understanding Prospect Scores

### Tiers

| Tier | Score | Meaning | Action |
|------|-------|---------|--------|
| **HOT** | 75+ | Excellent fit for bespoke packaging | Contact immediately |
| **WARM** | 60-74 | Good fit, worth pursuing | Prioritize outreach |
| **COOL** | 45-59 | Moderate fit | Follow up when time permits |
| **COLD** | <45 | Low priority | Review periodically |

### Score Components

Each prospect is scored on 5 factors:

1. **Industry Score** - How well their industry matches packaging needs
2. **Company Age** - Established companies (7-29 years) score higher
3. **Company Size** - Based on officers and filing activity
4. **Geography** - Regional preferences
5. **Web Presence** - Companies with websites score higher
6. **Bespoke Fit** - Specific fit for PackagePro's custom packaging

### Packaging Need Levels

| Level | Description |
|-------|-------------|
| **HIGH** | Industries that require significant packaging (food, cosmetics) |
| **MEDIUM** | Moderate packaging needs (retail, services) |
| **LOW** | Minimal packaging needs |
| **UNKNOWN** | Industry not yet classified |

---

## Filtering Prospects

### Filter Sidebar (Left Side)

#### Tier Filter
Check boxes to show only specific tiers:
- [ ] Hot
- [ ] Warm
- [ ] Cool
- [ ] Cold

#### Packaging Need Filter
- [ ] High
- [ ] Medium
- [ ] Low

#### Min Score Slider
Drag to set minimum score threshold (0-100)

#### Search by Name
Type to filter prospects by company name

#### Buttons
- **Apply Filters** - Apply your filter selections
- **Reset** - Clear all filters

---

## Bulk Actions

### Score All Unscored
Scores all prospects that haven't been scored yet.

**When to use:** After importing new prospects from a search.

### Enrich with Details
Fetches additional data from Companies House:
- Officer count
- Filing history
- Company charges
- Detailed address

**When to use:** After scoring to get more accurate scores.

---

## Prospect List

### Table Columns

| Column | Description |
|--------|-------------|
| **Company** | Company name and number |
| **Score** | Prospect score with tier badge |
| **Industry** | Industry sector |
| **Packaging Need** | HIGH/MEDIUM/LOW/UNKNOWN |
| **Status** | Pipeline status (NEW/SCORED/etc.) |
| **Actions** | Score button, View on Companies House link |

### Sorting
Use the dropdown to sort by:
- Score (High to Low) - default
- Newest First
- Name (A-Z)

### Pagination
Use Previous/Next buttons to navigate pages.

---

## Prospect Detail Modal

Click on any prospect row to open the detail modal.

### Information Shown

- **Score** - Large display with tier
- **Industry** - Sector classification
- **Packaging Need** - Estimated need level
- **Company Status** - Active/Dissolved
- **Company Age** - Years since incorporation
- **Officers** - Number of company officers
- **Filings** - Number of official filings
- **Region** - Geographic location

### Score Breakdown
Visual bars showing each score component:
- Industry (blue)
- Company Age (green)
- Company Size (purple)
- Geography (yellow)
- Web Presence (pink)

### Actions
- **Re-Score** - Recalculate the prospect's score
- **View on Companies House** - Opens official registry page

---

## Automatic Competitor Exclusion

The system automatically excludes companies that manufacture packaging (competitors):

### Excluded SIC Codes

| SIC Code | Industry |
|----------|----------|
| 17210 | Paper/cardboard containers |
| 22220 | Plastic packaging goods |
| 82920 | Contract packaging services |
| 16240 | Wooden containers |
| 25920 | Metal packaging |

Excluded companies are marked as **DISQUALIFIED** and hidden from the default view.

To see excluded companies, use the API directly:
```
GET /api/v1/prospects?exclude_competitors=false
```

---

## Workflow Example

### Finding Artisan Bakery Leads

1. **Search:** Enter SIC code `10710` (bakeries), set Max Results to `100`
2. **Click:** Search Companies House
3. **Wait:** ~5 seconds for results
4. **Enrich:** Click "Enrich with Details" to get more data
5. **Score:** If not auto-scored, click "Score All Unscored"
6. **Filter:** Check "Hot" and "Warm" tiers
7. **Review:** Click on each prospect to see details
8. **Export:** Contact the highest-scoring prospects

---

## Tips

1. **Start with SIC codes** - More targeted than keyword searches
2. **Use Auto-score** - Saves time on bulk searches
3. **Enrich after searching** - Gets officer/filing data for better scores
4. **Focus on WARM and HOT** - These have the best conversion potential
5. **Check bespoke fit reason** - Explains why a company is a good match
6. **Ignore COLD tier** - Low scores indicate poor fit for bespoke packaging

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Companies House API key not configured" | Add `COMPANIES_HOUSE_API_KEY` to `.env` file |
| No results from search | Try broader search terms or remove location filter |
| All prospects are COLD | Search for higher-priority industries (see SIC codes above) |
| Scoring seems wrong | Click "Enrich with Details" first to get more data |

---

## Support

For technical issues, check the server logs:
```bash
tail -f /tmp/ksp_server.log
```
