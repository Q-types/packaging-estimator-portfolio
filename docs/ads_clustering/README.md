# Advertising / CRM Clustering Feature Space

## Purpose
This feature space is designed for **behavioural segmentation of existing and past customers**.

It answers the question:

> *Given that a company is already a customer (or has been), how do their ordering behaviour, engagement patterns, and lifecycle position differ?*

The resulting clusters are intended to support:
- Targeted advertising
- CRM messaging
- Retention and re-activation strategies
- Offer and product mix optimisation

---

## What this space represents

This embedding is a **behavioural state space**.

Each row corresponds to a customer, embedded according to:
- Temporal behaviour (recency, tenure, order spacing)
- Engagement breadth (product diversity, operations used)
- Ordering dynamics (frequency, quantity structure)
- Revenue trajectory (recent vs historical behaviour)

The geometry reflects **how customers behave over time**, not who they are structurally.

---

## Included artefacts

- `X_ads_clustering.npy`  
  A numerical feature matrix suitable for **unsupervised clustering**  
  (e.g. K-Means, HDBSCAN, GMM).

- `feature_names_ads.json`  
  Ordered list of feature names corresponding to columns in `X_ads_clustering.npy`.

- `preprocessor_ads.joblib`  
  Fitted preprocessing pipeline (log transforms, scaling, encodings).  
  Must be reused to transform new or updated customer data.

---

## Important constraints

### ✅ Allowed uses
- Unsupervised clustering
- Cluster profiling and interpretation
- Visualisation (PCA, UMAP, t-SNE)
- Mapping clusters to marketing actions

### ❌ Forbidden uses
- Prospecting or look-alike modelling
- Scoring new companies with no transaction history
- Supervised learning against acquisition or churn labels

This space **contains post-transaction information** and therefore **cannot exist for prospects**.

Using it for acquisition modelling would cause **information leakage**.

---

## Row alignment

Rows in `X_ads_clustering.npy` align **exactly** with rows in: