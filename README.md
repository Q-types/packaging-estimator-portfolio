# Business Intelligence Dashboard - Demo

A customer intelligence platform featuring segmentation analysis and AI-powered prospect recommendation. Built for a B2B packaging manufacturer.

## Overview

This dashboard combines two core capabilities:

### 1. Customer Segmentation & Profiling
- RFM (Recency, Frequency, Monetary) analysis across 908 companies
- 8 behavioural segments with actionable insights
- Customer lifetime value metrics and order pattern analysis

### 2. Prospect Recommendation System
- KNN-based similarity scoring against existing high-value clients
- Companies House API integration for prospect discovery
- Automated prospect ranking based on company attributes

## Live Demo

[View on Streamlit Cloud →](https://business-intelligence-dashboard-demo.streamlit.app)

## Portfolio Notice

Company names have been anonymised for confidentiality. All metrics, segments, and analytical insights are based on real business data (snapshot: September 2024).

## Tech Stack

- **Frontend**: Streamlit
- **Visualisation**: Plotly
- **Data Processing**: Pandas, NumPy
- **Machine Learning**: scikit-learn (KNN prospect scoring)
- **External API**: Companies House

## Running Locally

```bash
cd dashboard
pip install -r requirements.txt
streamlit run Customer_Intelligence.py
```

## Main File

`dashboard/Customer_Intelligence.py`
