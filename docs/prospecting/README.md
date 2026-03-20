# Prospecting / Customer-Likeness Feature Space

## Purpose
This feature space is designed for **identifying and evaluating potential new customers**.

It answers the question:

> *Given a company in the wider market, how similar is it to companies that became good customers?*

This space supports:
- Prospect scoring
- Look-alike audience generation
- Sales prioritisation
- Market sizing and targeting

---

## What this space represents

This embedding is a **structural / firmographic similarity space**.

Each row represents a company described only by information that is:
- Available *before* any transaction
- Stable or slowly varying
- Observable for non-customers

The geometry reflects **capacity, legitimacy, scale, and sectoral alignment** — not behaviour.

---

## Included artefacts

- `X_prospect_features.npy`  
  Numerical feature matrix suitable for:
  - Supervised classification (propensity models)
  - Similarity search / nearest-neighbour analysis
  - Market segmentation

- `feature_names_prospect.json`  
  Ordered list of feature names corresponding to columns in `X_prospect_features.npy`.

- `preprocessor_prospect.joblib`  
  Fitted preprocessing pipeline (log transforms, scaling, categorical encodings).  
  Must be reused when scoring new companies.

---

## Typical modelling pattern

This space is usually paired with a binary label such as:

- `ever_customer`
- `is_active_12m`

and used in models like:
- Logistic regression
- Gradient-boosted trees
- Random forests
- Calibrated probability models

The output is typically:

\[
P(\text{company becomes customer})
\]

---

## Important constraints

### ✅ Allowed uses
- Prospect scoring
- Look-alike modelling
- Supervised classification
- Similarity search over mixed firmographic features

### ❌ Forbidden uses
- Behavioural clustering
- CRM segmentation
- Any feature that depends on orders, revenue, or engagement

This space **must not include transactional or behavioural variables**.

Violating this breaks the causal direction of the model and invalidates results.

---

## Row alignment

Rows in `X_prospect_features.npy` align **exactly** with rows in: