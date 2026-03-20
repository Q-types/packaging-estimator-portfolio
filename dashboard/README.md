# PackagePro Intelligence Dashboard

A comprehensive customer analytics dashboard built with Streamlit for PackagePro. Features advanced customer segmentation, prospect scoring, and actionable business insights.

## Features

### Customer Segmentation (8 Segments)
- **Dormant One-Timers** - Single order customers, low win-back potential
- **Lapsed Regulars** - Previously active, best win-back candidates
- **Occasional Past** - Project-based customers
- **Moderate History** - Inactive with reactivation potential
- **High-Value Dormant** - Critical win-back priority
- **New Prospects** - Recently acquired, nurturing needed
- **Growth Potential** - Active with expansion opportunity
- **High-Value Regulars** - Premium accounts to protect

### Dashboard Views
- **Action Center** - Daily prioritised tasks and alerts
- **Revenue Opportunities** - Expansion and win-back recommendations
- **Prospect Pipeline** - KNN-scored prospect ranking
- **Customer Explorer** - Search and analyse individual companies
- **Company Search** - Companies House API integration
- **Marketing Playbook** - Segment-specific email templates and strategies

## Installation

```bash
pip install -r requirements.txt
```

## Running Locally

```bash
streamlit run PackagePro_Customer_Intelligence.py
```

Or use the included run script:
```bash
./run.sh
```

## Configuration

For Companies House API access, create a `.env` file:
```
COMPANIES_HOUSE_API_KEY=your_api_key_here
```

For Streamlit Cloud deployment, add the API key to `.streamlit/secrets.toml`.

## Data

The dashboard includes pre-processed customer data with:
- 908 companies across 8 segments
- RFM (Recency, Frequency, Monetary) analysis
- Customer lifetime value metrics
- Order pattern analysis

**Data Snapshot Date**: October 2024

## Tech Stack

- **Frontend**: Streamlit
- **Visualisation**: Plotly
- **Data Processing**: Pandas, NumPy
- **Machine Learning**: scikit-learn (KNN prospect scoring)

## Deployment

This app is configured for deployment on [Streamlit Cloud](https://streamlit.io/cloud).

## License

Proprietary - PackagePro
