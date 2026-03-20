# Financial Data Analysis Summary

**Analysis Date:** February 3, 2026

## Overview

Analyzed `legacy_extract_refined.json` (8,068 records) to assess profit margin and cost data availability.

## Financial Data Completeness

| Status | Records | Percentage | Description |
|--------|---------|------------|-------------|
| **Complete** | 5,293 | 65.6% | Has both total_cost and profit_margin_pct |
| **Cost Only** | 992 | 12.3% | Has total_cost but profit=0 or missing |
| **Quote Only** | 1,783 | 22.1% | Customer-facing quotes with no cost data |

## By Template Type

### 2020_pob_master (6,469 records)
Internal production costing sheets with comprehensive data:
- **95.6%** have total_cost
- **82.2%** have profit_margin_pct > 0
- **80.5%** have both (complete financial data)

### 2024_quotation (1,486 records)
Customer-facing quotation templates:
- **0%** have cost data - these are sales quotes only
- Contains selling prices and quantities but no cost breakdown
- Cannot extract profit without separate cost data

### 2017_box (113 records)
Legacy box-specific templates:
- **86.7%** have total_cost
- **77.9%** have profit_margin_pct
- **77.0%** have both

## Profit Margin Distribution (5,316 records)

| Profit % | Count | % of Total |
|----------|-------|------------|
| 20% | 2,511 | 47.2% |
| 10% | 1,051 | 19.8% |
| 30% | 397 | 7.5% |
| 25% | 272 | 5.1% |
| 15% | 268 | 5.0% |
| 5% | 184 | 3.5% |
| 50% | 108 | 2.0% |
| 40% | 84 | 1.6% |
| Other | 441 | 8.3% |

**Key Insight:** Standard profit margins (5%, 10%, 15%, 20%, 25%, 30%) account for ~88% of all records. The 20% margin is the clear default.

## Records Without Profit Data (1,153 in 2020_pob_master)

Analysis of patterns in records with profit=0:
- **FREE ISSUE** (45 records): Customer-provided materials, legitimately no cost markup
- **PRINTED SHEETS/STRIPS**: Component work, often billed at cost
- Some records simply have the profit field blank in the source Excel

These appear to be legitimate cases where profit wasn't entered, not extraction failures.

## Recommendations

### For Pricing Models
1. **Use "complete" records** (5,293) for training cost estimation models
2. **For "cost_only" records** (992), can apply assumed 20% margin if needed
3. **Exclude "quote_only" records** (1,783) from cost-based analysis

### For Improved Extraction (if re-processing original files)
The current extractor looks for "PROFIT MARGIN" label. Could add:
- "MARGIN" or "MARK UP" patterns
- "PROFIT %" or "PROFIT PERCENTAGE"
- Check additional column positions (H-I, G-H)

### Default Margin Recommendation
For records missing profit margin, a **20% default** is statistically justified:
- 47% of all records use exactly 20%
- Median profit across all records is ~20%
- Industry standard for this type of work

## Data Quality Summary

| Metric | Value |
|--------|-------|
| Total refined records | 8,068 |
| Unique companies | 1,100 |
| Records with usable cost data | 6,285 (77.9%) |
| Records with complete financial data | 5,293 (65.6%) |
| Average profit margin | ~20% |

## Field Added

Each record now includes `financial_data_status`:
- `"complete"` - Has both cost and profit
- `"cost_only"` - Has cost, profit is 0 or missing
- `"quote_only"` - Customer quote without cost data
