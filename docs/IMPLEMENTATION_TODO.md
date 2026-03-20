# PackagePro Estimator - Implementation TODO

**Generated:** 2026-01-20
**Status:** Active

---

## Phase 1: Foundation (Weeks 1-4)

### 1.1 Project Setup
- [x] Create project structure in Vibe environment
- [x] Migrate files from Portfolio
- [x] Create MISSION.md
- [x] Create PRD.md
- [x] Create PDR.md
- [ ] Initialize git repository
- [x] Create .gitignore
- [ ] Set up Python virtual environment
- [x] Create pyproject.toml with dependencies

### 1.2 Backend Core (Agent: Backend Architect)

#### FastAPI Application Setup
- [x] Create `backend/app/main.py` - FastAPI application entry point
- [x] Create `backend/app/config.py` - Configuration management (pydantic-settings)
- [ ] Create `backend/app/deps.py` - Dependency injection
- [x] Set up CORS middleware
- [ ] Set up exception handlers
- [x] Configure logging (structured JSON)

#### Database Layer
- [x] Create `backend/app/models/base.py` - SQLAlchemy base model
- [x] Create `backend/app/models/user.py` - User model
- [x] Create `backend/app/models/customer.py` - Customer model
- [x] Create `backend/app/models/material.py` - Material model with pricing history
- [x] Create `backend/app/models/supplier.py` - Supplier model
- [x] Create `backend/app/models/estimate.py` - Estimate model (JSONB fields)
- [x] Create `backend/app/models/feedback.py` - Feedback model
- [x] Create `backend/app/models/pricing_rule.py` - Pricing rules model
- [x] Create `backend/app/models/ml_model.py` - ML model registry
- [x] Set up Alembic for migrations
- [x] Create initial migration
- [ ] Create database seed script for pricing rules

### 1.3 Calculation Engine (Agent: Calculation Engine Specialist)

#### SafeExpressionEvaluator (CRITICAL - Security)
- [x] Create `backend/app/core/safe_evaluator.py`
  - [x] Implement AST parser for expressions
  - [x] Support arithmetic operators (+, -, *, /, //, %, **)
  - [x] Support comparison operators (<, <=, >, >=, ==, !=)
  - [x] Support conditional expressions (if/else)
  - [x] Support safe functions (min, max, round, abs, ceil, floor)
  - [x] Implement variable substitution
  - [x] Add security validations (block dangerous patterns)
  - [x] Write comprehensive unit tests
  - [ ] Test against all legacy equations

#### Calculation Engine Port
- [x] Create `backend/app/core/calculation_engine.py`
  - [x] Port `update_multiplier()` function (remove eval)
  - [x] Port `update_totals()` function (remove eval)
  - [x] Port `update_enquiry()` function
  - [x] Port `generate_estimate()` function
  - [x] Implement setup/run time separation
  - [x] Add job complexity tier support (1-5)
  - [x] Implement dynamic wastage model
  - [ ] Write unit tests for each function
  - [ ] Validate 100% accuracy against legacy

#### Supporting Models
- [ ] Create `backend/app/core/wastage_model.py`
  - [ ] Implement dynamic wastage calculation
  - [ ] Support complexity-based wastage rates
  - [ ] Write unit tests
- [ ] Create `backend/app/core/complexity.py`
  - [ ] Implement complexity tier classification
  - [ ] Define tier-based multipliers
  - [ ] Write unit tests

### 1.4 Data Migration (Agent: Data Migration Specialist)

#### CSV to Database Migration
- [ ] Create `scripts/migrate_pricing_model.py`
  - [ ] Parse Variables_EQ_GPT.csv
  - [ ] Convert equations to safe expression format
  - [ ] Generate pricing_rules INSERT statements
  - [ ] Validate converted expressions
- [ ] Create `scripts/migrate_materials.py`
  - [ ] Extract materials from pricing model
  - [ ] Create material categories
  - [ ] Set up initial pricing history
- [ ] Create `scripts/migrate_estimates.py`
  - [ ] Export from SQLite database
  - [ ] Transform to PostgreSQL format
  - [ ] Handle JSONB conversion
- [ ] Create `scripts/validate_migration.py`
  - [ ] Compare calculation results
  - [ ] Report discrepancies
  - [ ] Generate validation report

---

## Phase 2: Feature Parity (Weeks 5-8)

### 2.1 API Endpoints (Agent: Backend Architect)

#### Authentication
- [ ] Create `backend/app/routers/auth.py`
  - [ ] POST /auth/login - JWT authentication
  - [ ] POST /auth/logout - Session termination
  - [ ] POST /auth/refresh - Token refresh
  - [ ] Implement password hashing (bcrypt)
  - [ ] Create JWT utilities
  - [ ] Add rate limiting

#### Estimates API
- [ ] Create `backend/app/routers/estimates.py`
  - [ ] GET /estimates - List with pagination, filtering
  - [ ] POST /estimates - Create new estimate
  - [ ] GET /estimates/{id} - Get estimate details
  - [ ] PUT /estimates/{id} - Update estimate
  - [ ] DELETE /estimates/{id} - Soft delete
  - [ ] POST /estimates/{id}/calculate - Recalculate
  - [ ] POST /estimates/{id}/quote - Generate PDF
  - [ ] POST /estimates/{id}/duplicate - Clone estimate
- [ ] Create `backend/app/schemas/estimate.py` - Pydantic schemas
- [ ] Create `backend/app/services/estimate_service.py`

#### Materials API
- [ ] Create `backend/app/routers/materials.py`
  - [ ] CRUD operations
  - [ ] POST /materials/import - Bulk CSV import
  - [ ] GET /materials/export - CSV export
  - [ ] GET /materials/by-category/{category} - Filtered list
- [ ] Create `backend/app/services/material_service.py`
  - [ ] CSV parsing with validation
  - [ ] Price history tracking
  - [ ] Version management

#### Feedback API
- [ ] Create `backend/app/routers/feedback.py`
  - [ ] POST /feedback - Submit feedback
  - [ ] GET /feedback/estimate/{id} - Get for estimate
  - [ ] GET /feedback/metrics - Accuracy metrics
- [ ] Create `backend/app/services/feedback_service.py`

#### Customers API
- [ ] Create `backend/app/routers/customers.py` - Full CRUD

#### Admin API
- [ ] Create `backend/app/routers/admin.py`
  - [ ] User management
  - [ ] Pricing rules management
  - [ ] ML model management

### 2.2 PDF Generation
- [ ] Create `backend/app/services/pdf_service.py`
  - [ ] Port ReportLab quote generation
  - [ ] Update template for new branding
  - [ ] Support multiple output formats
  - [ ] Add configurable company details

### 2.3 Frontend (Agent: Frontend Developer)

#### Templates Setup
- [ ] Create `frontend/templates/base.html` - Base layout with Tailwind
- [ ] Create `frontend/templates/components/` - Reusable components
  - [ ] header.html
  - [ ] sidebar.html
  - [ ] footer.html
  - [ ] alert.html
  - [ ] modal.html
  - [ ] pagination.html
- [ ] Set up Tailwind CSS build process

#### Pages
- [ ] Create `frontend/templates/pages/dashboard.html`
  - [ ] Recent estimates list
  - [ ] Quick stats widgets
  - [ ] Quick actions
- [ ] Create `frontend/templates/pages/estimates/list.html`
  - [ ] Search and filter
  - [ ] Sortable table
  - [ ] Pagination
- [ ] Create `frontend/templates/pages/estimates/form.html`
  - [ ] HTMX live calculation
  - [ ] Material selection dropdowns
  - [ ] Operation checkboxes
  - [ ] Alpine.js for advanced sections
- [ ] Create `frontend/templates/pages/estimates/detail.html`
  - [ ] Full cost breakdown
  - [ ] Edit inline
  - [ ] Generate quote button
- [ ] Create `frontend/templates/pages/feedback/submit.html`
  - [ ] Mobile-friendly form
  - [ ] Operation-by-operation input
- [ ] Create `frontend/templates/pages/materials/list.html`
- [ ] Create `frontend/templates/pages/materials/import.html`
  - [ ] File upload
  - [ ] Preview changes
  - [ ] Confirm/cancel
- [ ] Create `frontend/templates/pages/customers/list.html`
- [ ] Create `frontend/templates/pages/analytics/dashboard.html`
  - [ ] Accuracy charts
  - [ ] Trend visualizations
- [ ] Create `frontend/templates/pages/auth/login.html`
- [ ] Create `frontend/templates/pages/admin/users.html`
- [ ] Create `frontend/templates/pages/admin/pricing-rules.html`

#### HTMX Partials
- [ ] Create partials for live updates
  - [ ] Cost preview partial
  - [ ] Material options partial
  - [ ] Estimate row partial
  - [ ] Feedback form partial

---

## Phase 3: ML & Feedback Loop (Weeks 7-10)

### 3.1 ML Pipeline (Agent: ML Pipeline Engineer)

#### Data Pipeline
- [ ] Create `ml/data_pipeline/feature_extractor.py`
  - [ ] Define feature schema
  - [ ] Implement extraction from estimate data
  - [ ] Handle categorical features
  - [ ] Normalize numerical features
- [ ] Create `ml/data_pipeline/data_loader.py`
  - [ ] Load training data from database
  - [ ] Handle missing values
  - [ ] Train/test split utilities

#### Models
- [ ] Create `ml/models/time_predictor.py`
  - [ ] HistGradientBoostingRegressor implementation
  - [ ] Quantile regression for intervals
  - [ ] fit() and predict_with_interval() methods
- [ ] Create `ml/models/model_registry.py`
  - [ ] Model versioning
  - [ ] Save/load with joblib
  - [ ] Database tracking

#### Training
- [ ] Create `ml/training/train.py`
  - [ ] Training pipeline script
  - [ ] Cross-validation
  - [ ] Metric computation (MAE, coverage)
  - [ ] Model comparison
- [ ] Create `ml/training/evaluate.py`
  - [ ] Backtesting on historical data
  - [ ] A/B comparison with rules

#### Inference
- [ ] Create `ml/inference/predictor.py`
  - [ ] Load active model
  - [ ] Feature transformation
  - [ ] Prediction with confidence
- [ ] Create `backend/app/core/hybrid_estimator.py`
  - [ ] Combine rule + ML estimates
  - [ ] Confidence weighting logic
  - [ ] Graceful ML fallback

### 3.2 Feedback Integration (Agent: Feedback Loop Integrator)

#### Data Collection
- [ ] Enhance feedback schema for ML features
  - [ ] Operator skill level
  - [ ] Machine efficiency
  - [ ] Environmental factors
- [ ] Create automated feedback prompts
  - [ ] Email reminders for pending feedback
  - [ ] Dashboard notifications

#### Retraining Pipeline
- [ ] Create `ml/training/retrain_scheduler.py`
  - [ ] Batch retraining triggers
  - [ ] Accuracy threshold monitoring
  - [ ] Automated model deployment
- [ ] Create `backend/app/services/ml_service.py`
  - [ ] Trigger retraining API
  - [ ] Model status monitoring
  - [ ] Metrics reporting

---

## Phase 4: Production (Weeks 9-12)

### 4.1 DevOps (Agent: DevOps Engineer)

#### Containerization
- [ ] Create `Dockerfile` for application
- [ ] Create `Dockerfile.nginx` for reverse proxy
- [ ] Create `docker-compose.yml` for development
- [ ] Create `docker-compose.prod.yml` for production
- [ ] Optimize image sizes
- [ ] Add health checks

#### CI/CD
- [ ] Create `.github/workflows/test.yml`
  - [ ] Run pytest on PR
  - [ ] Lint with ruff
  - [ ] Type check with mypy
- [ ] Create `.github/workflows/deploy.yml`
  - [ ] Build Docker images
  - [ ] Push to registry
  - [ ] Deploy to VPS
- [ ] Create `.github/workflows/security.yml`
  - [ ] Dependency scanning
  - [ ] SAST scanning

#### Infrastructure
- [ ] Set up VPS (4GB RAM recommended)
- [ ] Configure Nginx
  - [ ] SSL certificates (Let's Encrypt)
  - [ ] Reverse proxy config
  - [ ] Gzip compression
  - [ ] Static file serving
- [ ] Configure PostgreSQL
  - [ ] Production tuning
  - [ ] Automated backups
  - [ ] Connection pooling
- [ ] Set up monitoring
  - [ ] Health check endpoint
  - [ ] Basic metrics collection
  - [ ] Log aggregation

### 4.2 Testing (Agent: QA Engineer)

#### Unit Tests
- [ ] `tests/unit/core/test_safe_evaluator.py`
  - [ ] Valid expressions
  - [ ] Invalid/malicious expressions
  - [ ] Edge cases
- [ ] `tests/unit/core/test_calculation_engine.py`
  - [ ] All calculation functions
  - [ ] Legacy formula validation
- [ ] `tests/unit/core/test_wastage_model.py`
- [ ] `tests/unit/core/test_hybrid_estimator.py`

#### Integration Tests
- [ ] `tests/integration/test_estimates_api.py`
- [ ] `tests/integration/test_materials_api.py`
- [ ] `tests/integration/test_feedback_api.py`
- [ ] `tests/integration/test_auth.py`

#### E2E Tests
- [ ] `tests/e2e/test_estimate_workflow.py`
  - [ ] Create estimate
  - [ ] Generate quote
  - [ ] Submit feedback
- [ ] `tests/e2e/test_material_import.py`

#### Validation Tests
- [ ] `tests/validation/test_legacy_match.py`
  - [ ] 100% calculation accuracy vs spreadsheet
  - [ ] All 80+ variables
  - [ ] Edge cases from production

### 4.3 Documentation (Agent: Documentation Specialist)

- [ ] API Documentation
  - [ ] OpenAPI spec generation
  - [ ] Endpoint descriptions
  - [ ] Request/response examples
- [ ] User Guide
  - [ ] Getting started
  - [ ] Creating estimates
  - [ ] Managing materials
  - [ ] Submitting feedback
- [ ] Admin Guide
  - [ ] User management
  - [ ] Pricing rules
  - [ ] ML model monitoring
- [ ] Deployment Guide
  - [ ] Server requirements
  - [ ] Installation steps
  - [ ] Configuration options
- [ ] Architecture Decision Records (ADRs)
  - [ ] ADR-001: SafeExpressionEvaluator
  - [ ] ADR-002: Hybrid ML Approach
  - [ ] ADR-003: HTMX Frontend

---

## Implementation Priority Queue

### Immediate (Start Now)
1. **SafeExpressionEvaluator** - Security critical, blocks all equation work
2. **Database schema & migrations** - Foundation for everything
3. **Calculation engine port** - Core business logic

### Next Sprint
4. **Estimates API** - Enable basic estimation
5. **Basic frontend** - Usable interface
6. **Materials management** - Price updates

### Following Sprint
7. **Feedback collection** - Start gathering ML training data
8. **PDF generation** - Quote delivery
9. **Authentication** - Multi-user support

### Later
10. **ML pipeline** - Requires feedback data
11. **Analytics dashboard** - Nice to have
12. **Advanced features** - Complexity tiers, etc.

---

## Success Criteria Checklist

- [ ] Estimate generation <2 minutes (vs 30-60 manual)
- [ ] 100% calculation accuracy vs legacy spreadsheet
- [ ] API response time <500ms (p95)
- [ ] Zero security vulnerabilities (no eval)
- [ ] Mobile-responsive UI
- [ ] Feedback collection enabled
- [ ] ML model trainable when data available

---

*This document should be updated as tasks are completed.*
