# PackagePro Estimator - Product Requirements Document (PRD)

**Version:** 1.0
**Date:** 2026-01-20
**Status:** Draft

---

## 1. Overview

### 1.1 Product Summary
PackagePro Estimator is a web-based cost estimation platform for bespoke packaging manufacturers. It replaces manual spreadsheet-based estimation with an intelligent system that combines deterministic calculations with machine learning to deliver accurate, confidence-backed production cost estimates.

### 1.2 Problem Statement
Bespoke packaging manufacturers currently spend 30-60 minutes per estimate using error-prone spreadsheets. Only experienced staff can generate reliable quotes, creating a bottleneck that limits business growth and responsiveness to customer inquiries.

### 1.3 Target Users
| User Type | Primary Needs |
|-----------|---------------|
| **Estimators/Sales Staff** | Generate accurate quotes quickly |
| **Production Managers** | Track estimate accuracy, provide feedback |
| **Business Owners** | Analyze pricing strategy, monitor margins |

---

## 2. Functional Requirements

### 2.1 Estimate Generation (P0 - Must Have)

#### FR-001: Dimension-Based Input
- **Description:** Users enter packaging dimensions and the system calculates all derived measurements
- **Inputs:**
  - Flat size (width × height)
  - Outer wrap dimensions
  - Liner dimensions
  - Spine/gusset depth
  - Quantity required
- **Acceptance Criteria:**
  - All 80+ interdependent variables update automatically
  - Sub-second calculation time
  - Input validation with helpful error messages

#### FR-002: Material Selection
- **Description:** Users select materials from a managed catalog
- **Inputs:**
  - Board type (Dutch grey, etc.)
  - Board thickness
  - Outer wrap material
  - Liner material
  - Additional materials (magnets, ribbons, etc.)
- **Acceptance Criteria:**
  - Materials pull current prices from database
  - Material compatibility warnings displayed
  - Custom material entry option

#### FR-003: Operation Selection
- **Description:** Users specify manufacturing operations required
- **Operations:**
  - Cutting
  - Wrapping
  - Creasing
  - Drilling
  - Laminating
  - Foil blocking
  - Screen printing
  - Assembly
- **Acceptance Criteria:**
  - Operation times calculated based on quantity and complexity
  - Setup time separated from run time
  - Machine-specific rates applied

#### FR-004: Cost Breakdown Display
- **Description:** Show itemized cost breakdown with confidence intervals
- **Output:**
  - Material costs (itemized)
  - Labor hours (per operation)
  - Machine time
  - Overhead allocation
  - Wastage allowance
  - **Total estimate with confidence interval**
- **Acceptance Criteria:**
  - Breakdown matches legacy spreadsheet calculations (100% accuracy)
  - Confidence interval displayed (e.g., "£1,200 - £1,450")
  - Expandable/collapsible detail sections

#### FR-005: Quote Generation
- **Description:** Generate professional PDF quotes
- **Output:**
  - Company-branded PDF
  - Customer details
  - Job specification summary
  - Pricing (with/without breakdown options)
  - Terms and conditions
- **Acceptance Criteria:**
  - PDF renders correctly on all devices
  - Customizable branding/logo
  - Quote number auto-generated

### 2.2 Material Price Management (P0 - Must Have)

#### FR-006: Material Catalog
- **Description:** Maintain database of materials with pricing
- **Fields:**
  - Material name
  - SKU/code
  - Unit of measure
  - Current price
  - Supplier
  - Last updated date
- **Acceptance Criteria:**
  - CRUD operations for materials
  - Search and filter functionality
  - Price history tracking

#### FR-007: Bulk Price Updates
- **Description:** Update prices via CSV/Excel upload
- **Inputs:**
  - Supplier pricing spreadsheet
  - Column mapping configuration
- **Acceptance Criteria:**
  - Preview changes before applying
  - Automatic version history
  - Rollback capability
  - Validation errors highlighted

### 2.3 Production Feedback (P0 - Must Have)

#### FR-008: Feedback Submission
- **Description:** Record actual production data against estimates
- **Inputs:**
  - Estimate reference
  - Actual hours per operation
  - Actual material usage
  - Issues/notes
  - Operator identifier
  - Machine used
- **Acceptance Criteria:**
  - Mobile-friendly input interface
  - Partial submission allowed
  - Automatic prompts for missing feedback

#### FR-009: Accuracy Tracking
- **Description:** Display estimate vs actual comparison
- **Metrics:**
  - Percentage variance per operation
  - Cumulative accuracy over time
  - Trend visualization
- **Acceptance Criteria:**
  - Dashboard showing recent accuracy
  - Drill-down to individual estimates
  - Export capability

### 2.4 ML Enhancement (P1 - Should Have)

#### FR-010: Hybrid Estimation
- **Description:** Combine rule-based and ML predictions
- **Behavior:**
  - Rule-based calculation always executes
  - ML prediction runs when sufficient training data exists
  - Weighted combination based on confidence
- **Acceptance Criteria:**
  - ML prediction marked clearly when used
  - Confidence score displayed
  - Fallback to rules-only gracefully

#### FR-011: Automated Retraining
- **Description:** ML model improves with feedback data
- **Triggers:**
  - New feedback batch received
  - Accuracy threshold breached
  - Manual trigger
- **Acceptance Criteria:**
  - Retraining runs without service interruption
  - Model versioning with rollback
  - A/B comparison reporting

### 2.5 User Management (P1 - Should Have)

#### FR-012: Authentication
- **Description:** Secure user login
- **Features:**
  - Email/password authentication
  - Password reset
  - Session management
- **Acceptance Criteria:**
  - Secure password storage (bcrypt)
  - JWT token-based sessions
  - Configurable session timeout

#### FR-013: Role-Based Access
- **Description:** Different permissions by role
- **Roles:**
  - Admin (full access)
  - Estimator (create/view estimates)
  - Production (submit feedback only)
  - Viewer (read-only access)
- **Acceptance Criteria:**
  - Role assignment by admin
  - Permission enforcement on all endpoints

### 2.6 Reporting (P2 - Nice to Have)

#### FR-014: Estimate History
- **Description:** Searchable history of all estimates
- **Features:**
  - Search by customer, date, job type
  - Filter by status (quoted, won, lost)
  - Duplicate estimate functionality
- **Acceptance Criteria:**
  - Pagination for large datasets
  - Export to CSV/Excel

#### FR-015: Analytics Dashboard
- **Description:** Business intelligence visualizations
- **Metrics:**
  - Quote conversion rate
  - Average margin by job type
  - Estimation accuracy trends
  - Material cost trends
- **Acceptance Criteria:**
  - Interactive charts
  - Date range filtering
  - Comparison periods

---

## 3. Non-Functional Requirements

### 3.1 Performance

| Metric | Requirement |
|--------|-------------|
| Estimate calculation | <500ms (p95) |
| Page load time | <2s |
| PDF generation | <5s |
| Concurrent users | 10 simultaneous |

### 3.2 Security

| Requirement | Implementation |
|-------------|----------------|
| No code injection | SafeExpressionEvaluator (AST-based) |
| Data encryption | HTTPS, encrypted at rest |
| Authentication | JWT with refresh tokens |
| Input validation | Server-side validation on all inputs |

### 3.3 Reliability

| Metric | Target |
|--------|--------|
| Uptime | 99.5% |
| Data backup | Daily automated backups |
| Recovery time | <4 hours |

### 3.4 Usability

- Mobile-responsive design
- Accessible (WCAG 2.1 AA)
- Works offline for viewing cached estimates
- <2 minute learning curve for basic estimation

### 3.5 Compatibility

- Browsers: Chrome, Firefox, Safari, Edge (latest 2 versions)
- Devices: Desktop, tablet, mobile
- Export formats: PDF, CSV, Excel

---

## 4. Technical Constraints

### 4.1 Must Use
- **Backend:** Python (existing calculation engine)
- **Database:** PostgreSQL (production-grade, JSON support)
- **ML:** scikit-learn (established, no over-engineering)

### 4.2 Must Avoid
- LLMs for numerical estimation (explicit requirement)
- `eval()` for equation execution (security)
- Over-engineering for scalability not yet needed

### 4.3 Migration Requirements
- 100% calculation accuracy vs legacy spreadsheet
- All historical estimates importable
- Pricing model CSV structure preserved

---

## 5. Success Criteria

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Estimate generation time | <2 minutes | User session tracking |
| Calculation accuracy | 100% vs legacy | Automated test suite |
| ML prediction MAE | <15% of actual | Feedback comparison |
| Confidence interval coverage | >80% | Statistical analysis |
| User adoption | 100% within 30 days | Usage tracking |
| Feedback collection rate | >70% of jobs | Database metrics |

---

## 6. Out of Scope (Phase 1)

- ERP/accounting system integration
- Multi-currency support
- Real-time supplier pricing APIs
- Multi-tenant/SaaS deployment
- Mobile native apps

---

## 7. Dependencies

| Dependency | Owner | Risk |
|------------|-------|------|
| Existing calculation formulas | PackagePro domain experts | Medium - may need clarification |
| Historical estimate data | PackagePro | Low - SQLite export available |
| Material pricing data | PackagePro | Low - CSV format defined |
| Production feedback data | PackagePro | High - minimal historical data |

---

## 8. Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Phase 1: Foundation | 4 weeks | FastAPI backend, DB schema, calculation engine port |
| Phase 2: Feature Parity | 4 weeks | Full API, basic UI, feedback collection |
| Phase 3: Production | 4 weeks | Docker deployment, testing, documentation |
| Phase 4: Enhancement | Ongoing | ML training, continuous improvement |

---

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **Bespoke packaging** | Custom-made presentation folders, binders, boxes |
| **Setup time** | Fixed time to prepare machine regardless of quantity |
| **Run time** | Variable time proportional to quantity |
| **Wastage** | Material lost during production (cuts, errors, setup) |
| **Confidence interval** | Range within which actual value is expected |
| **OEE** | Overall Equipment Effectiveness (machine utilization) |

---

*Document maintained by: PackagePro Estimator Development Team*
