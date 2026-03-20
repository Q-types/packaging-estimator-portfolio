# PackagePro Estimator - Project Memory

## Project Vision
A production-ready bespoke packaging cost estimator for PackagePro & Buckingham Screen Print with:
1. **Dimension-based estimation** - Calculate costs from packaging dimensions and materials
2. **External datasheet integration** - Material prices updated from supplier data
3. **ML-powered time estimation** - Production hours learned from feedback loop
4. **Error margins** - Statistical confidence intervals on estimates

## Key Decisions

### Decision 1: No LLM-Based Estimation
- **What**: Remove LLM integration for estimates
- **Why**: LLMs produce unreliable numerical estimates; statistical ML models are more appropriate
- **Date**: 2026-01-20

### Decision 2: Deploy Within Vibe Environment
- **What**: Project structured under `/Vibe/products/packagepro-estimator/`
- **Why**: Leverage existing Vibe workspace conventions and infrastructure
- **Date**: 2026-01-20

## Technical Context

### Original System (from Portfolio)
- **Stack**: Python 3.8+, Pandas, Tkinter, SQLite, ReportLab
- **Variables**: 80+ interdependent pricing variables
- **Issues**:
  - Uses `eval()` for dynamic equations (security concern)
  - Hardcoded file paths
  - Desktop-only (Tkinter)
  - Basic feedback mechanism incomplete

### Pricing Model Structure
```
Variables CSV contains:
- Feature (variable name)
- Multiplier (current value)
- Equation for Multiplier (Python code)
- Updated Multiplier (manual override flag)
- Factory Set Constant / Customer Dependant / Customer Variable (category flags)
- COST/RATE (£) (base cost)
- TOTAL (£) (calculated total)
- Equation for TOTAL (£) (Python code)
```

### Variable Categories
1. **Customer Variables**: Quantity, dimensions (flat size, outer wrap, liner)
2. **Factory Constants**: Machine speeds, pile depths, drill specs
3. **Calculated/Dependent**: Areas, yields, pile depths, totals
4. **Cost Items**: Materials (Dutch grey board, liner paper, glue, magnets)

## Project Structure
```
packagepro-estimator/
├── backend/
│   ├── api/           # FastAPI endpoints
│   ├── core/          # Calculation engine (migrated)
│   ├── services/      # Business logic services
│   ├── models/        # SQLAlchemy models
│   └── utils/         # Utilities
├── frontend/          # Web interface (React/HTMX)
├── ml/
│   ├── training/      # Model training scripts
│   ├── inference/     # Prediction service
│   ├── data_pipeline/ # Feedback collection (migrated)
│   └── models/        # Trained model artifacts
├── docs/
│   ├── architecture/  # System design docs
│   ├── decisions/     # ADRs
│   └── api/           # API documentation
├── data/
│   ├── materials/     # Pricing model (migrated)
│   ├── feedback/      # Production feedback data
│   └── estimates/     # Historical estimates
├── config/            # Environment configs
├── tests/             # Test suite
└── scripts/           # Utility scripts
```

## Migrated Files
- `PackagePro_Functions.py` → `backend/core/calculation_engine.py`
- `Variables_EQ_GPT.csv` → `data/materials/pricing_model.csv`
- `feadback.py` → `ml/data_pipeline/feedback_collector.py`

## Session Log

### Session: 2026-01-20
- Analyzed existing codebase from Portfolio
- Created project structure in Vibe environment
- Spawned 3 advisor agents:
  1. Manufacturing Domain Expert
  2. ML/AI Systems Advisor
  3. Software Architecture Advisor
- Awaiting advisor recommendations for optimal agent team

## Documentation Created
- **MISSION.md** - Mission statement, vision, product description, core values
- **PRD.md** - Product Requirements Document (15 functional requirements)
- **PDR.md** - Product Design Requirements (architecture, schema, API design)
- **IMPLEMENTATION_TODO.md** - Comprehensive task breakdown by phase

## Next Steps
1. ~~Receive advisor recommendations~~ ✓
2. ~~Design optimal agent team structure~~ ✓
3. ~~Create implementation pipeline~~ ✓
4. **Begin Phase 1 development** ← Current

## Phase 1 Progress

### Completed
1. **SafeExpressionEvaluator** - AST-based safe expression evaluation (replaces eval())
   - File: `backend/app/core/safe_evaluator.py`
   - Tests: `tests/unit/core/test_safe_evaluator.py`
   - Supports: arithmetic, comparisons, conditionals, safe functions
   - Blocks: all dangerous patterns (import, exec, eval, dunder, etc.)

2. **Database Models** - Complete SQLAlchemy 2.0 models
   - User, Customer, Material, Supplier, Estimate, Feedback, PricingRule, MLModel
   - Location: `backend/app/models/`
   - Uses JSONB for flexible input/output storage
   - Ready for Alembic migrations

3. **Calculation Engine Port** - Core business logic
   - File: `backend/app/core/calculation_engine.py`
   - Uses SafeExpressionEvaluator (no eval)
   - Added: ComplexityTier enum, setup/run time separation
   - Added: DimensionInputs, MaterialInputs, EstimateInputs dataclasses

4. **FastAPI Application** - Entry point and configuration
   - File: `backend/app/main.py`
   - File: `backend/app/config.py`
   - Health check endpoint: `/health`
   - API info endpoint: `/api/v1`

5. **Docker Configuration**
   - Dockerfile for production
   - docker-compose.yml for development
   - PostgreSQL service with health check

6. **Project Configuration**
   - pyproject.toml with all dependencies
   - .gitignore
   - .env.example

### Pending
- Alembic migrations setup
- API routers (estimates, materials, feedback, auth)
- Frontend templates (HTMX + Alpine.js)
- ML pipeline integration
