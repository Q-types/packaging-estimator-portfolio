# PackagePro Estimator - Product Design Requirements (PDR)

**Version:** 1.0
**Date:** 2026-01-20
**Status:** Draft

---

## 1. System Architecture

### 1.1 Architecture Pattern: Modular Monolith

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              NGINX (Reverse Proxy)                          │
│                                    :443                                     │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
┌─────────────────────────────────────▼───────────────────────────────────────┐
│                              FASTAPI APPLICATION                            │
│                                    :8000                                    │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                           API LAYER                                    │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │  │
│  │  │  Estimates  │  │  Materials  │  │  Feedback   │  │    Auth     │  │  │
│  │  │   Router    │  │   Router    │  │   Router    │  │   Router    │  │  │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  │  │
│  └─────────┼────────────────┼────────────────┼────────────────┼─────────┘  │
│            │                │                │                │            │
│  ┌─────────▼────────────────▼────────────────▼────────────────▼─────────┐  │
│  │                        SERVICE LAYER                                  │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │  │
│  │  │ Estimation  │  │  Material   │  │  Feedback   │  │    User     │  │  │
│  │  │  Service    │  │  Service    │  │  Service    │  │   Service   │  │  │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  │  │
│  └─────────┼────────────────┼────────────────┼────────────────┼─────────┘  │
│            │                │                │                │            │
│  ┌─────────▼────────────────▼────────────────▼────────────────▼─────────┐  │
│  │                         CORE LAYER                                    │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │                    CALCULATION ENGINE                            │  │  │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │  │  │
│  │  │  │    Safe     │  │   Wastage   │  │  Complexity │             │  │  │
│  │  │  │  Evaluator  │  │    Model    │  │    Tiers    │             │  │  │
│  │  │  └─────────────┘  └─────────────┘  └─────────────┘             │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │                     HYBRID ESTIMATOR                             │  │  │
│  │  │  ┌─────────────┐              ┌─────────────┐                   │  │  │
│  │  │  │ Rule-Based  │      +       │     ML      │                   │  │  │
│  │  │  │  Estimator  │              │  Predictor  │                   │  │  │
│  │  │  └─────────────┘              └─────────────┘                   │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                      │                                      │
└──────────────────────────────────────┼──────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                              POSTGRESQL                                     │
│                                 :5432                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  estimates  │  │  materials  │  │  feedback   │  │    users    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Technology Stack

| Layer | Technology | Justification |
|-------|------------|---------------|
| **Web Server** | Nginx | Reverse proxy, SSL termination, static files |
| **Backend** | FastAPI | Type safety, async, auto-generated OpenAPI docs |
| **Frontend** | HTMX + Alpine.js | Minimal JS, Python team friendly, fast dev |
| **Templates** | Jinja2 | Native FastAPI integration |
| **Styling** | Tailwind CSS | Utility-first, rapid prototyping |
| **Database** | PostgreSQL 15+ | Production-grade, JSON support, full-text search |
| **ORM** | SQLAlchemy 2.0 | Async support, type hints, migrations |
| **Migrations** | Alembic | SQLAlchemy native, version control |
| **ML** | scikit-learn | HistGradientBoostingRegressor, quantile regression |
| **PDF** | ReportLab | Existing solution, Python native |
| **Containerization** | Docker | Consistent environments |
| **CI/CD** | GitHub Actions | Integrated with repo |

---

## 2. Database Schema

### 2.1 Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     users       │       │    customers    │       │   materials     │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │       │ id (PK)         │
│ email           │       │ name            │       │ name            │
│ password_hash   │       │ contact_name    │       │ sku             │
│ role            │       │ email           │       │ category        │
│ created_at      │       │ phone           │       │ unit            │
│ last_login      │       │ address         │       │ current_price   │
└─────────────────┘       │ created_at      │       │ supplier_id     │
                          └────────┬────────┘       │ last_updated    │
                                   │                └────────┬────────┘
                                   │                         │
┌─────────────────┐       ┌────────▼────────┐       ┌────────▼────────┐
│  ml_models      │       │    estimates    │       │ material_prices │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │       │ id (PK)         │
│ version         │       │ customer_id(FK) │       │ material_id(FK) │
│ model_type      │       │ user_id (FK)    │       │ price           │
│ metrics_json    │       │ job_name        │       │ effective_from  │
│ model_blob      │       │ status          │       │ effective_to    │
│ created_at      │       │ inputs_json     │       │ source          │
│ is_active       │       │ outputs_json    │       └─────────────────┘
└─────────────────┘       │ ml_prediction   │
                          │ confidence      │       ┌─────────────────┐
                          │ created_at      │       │    suppliers    │
                          │ quoted_at       │       ├─────────────────┤
                          └────────┬────────┘       │ id (PK)         │
                                   │                │ name            │
                          ┌────────▼────────┐       │ contact_email   │
                          │    feedback     │       │ created_at      │
                          ├─────────────────┤       └─────────────────┘
                          │ id (PK)         │
                          │ estimate_id(FK) │       ┌─────────────────┐
                          │ operation       │       │  pricing_rules  │
                          │ estimated_hours │       ├─────────────────┤
                          │ actual_hours    │       │ id (PK)         │
                          │ operator_id     │       │ name            │
                          │ machine_id      │       │ category        │
                          │ notes           │       │ expression      │
                          │ submitted_at    │       │ dependencies    │
                          └─────────────────┘       │ version         │
                                                    │ is_active       │
                                                    └─────────────────┘
```

### 2.2 Core Tables

#### estimates
```sql
CREATE TABLE estimates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id),
    user_id UUID REFERENCES users(id) NOT NULL,
    job_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'draft',  -- draft, quoted, won, lost, completed
    complexity_tier INTEGER DEFAULT 3,   -- 1-5 complexity rating

    -- Input parameters (JSONB for flexibility)
    inputs JSONB NOT NULL,
    /*
    {
        "dimensions": {
            "flat_width": 300,
            "flat_height": 400,
            "outer_wrap_width": 320,
            "outer_wrap_height": 420,
            "liner_width": 295,
            "liner_height": 395,
            "spine_depth": 25
        },
        "quantity": 1000,
        "materials": {
            "board_type": "dutch_grey_2mm",
            "outer_wrap": "buckram_cloth",
            "liner": "uncoated_paper_120gsm"
        },
        "operations": ["cutting", "wrapping", "creasing", "assembly"],
        "rush_order": false
    }
    */

    -- Calculated outputs (JSONB)
    outputs JSONB,
    /*
    {
        "material_costs": {...},
        "labor_hours": {...},
        "total_cost": 1250.00,
        "confidence_interval": [1150.00, 1380.00],
        "breakdown": {...}
    }
    */

    -- ML enhancement
    ml_prediction DECIMAL(10,2),
    ml_confidence DECIMAL(5,4),
    ml_model_version VARCHAR(50),

    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    quoted_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_estimates_customer ON estimates(customer_id);
CREATE INDEX idx_estimates_status ON estimates(status);
CREATE INDEX idx_estimates_created ON estimates(created_at DESC);
```

#### feedback
```sql
CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    estimate_id UUID REFERENCES estimates(id) NOT NULL,

    -- Operation details
    operation VARCHAR(100) NOT NULL,
    machine_id VARCHAR(50),
    operator_id VARCHAR(50),

    -- Time tracking (in minutes)
    estimated_setup_time INTEGER,
    actual_setup_time INTEGER,
    estimated_run_time INTEGER,
    actual_run_time INTEGER,

    -- Material tracking
    estimated_material_usage DECIMAL(10,3),
    actual_material_usage DECIMAL(10,3),
    wastage_units INTEGER,

    -- Quality
    first_pass_yield DECIMAL(5,4),  -- percentage
    rework_time INTEGER,  -- minutes

    -- Context
    notes TEXT,
    issues_encountered TEXT[],

    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    submitted_by UUID REFERENCES users(id)
);

CREATE INDEX idx_feedback_estimate ON feedback(estimate_id);
CREATE INDEX idx_feedback_operation ON feedback(operation);
CREATE INDEX idx_feedback_submitted ON feedback(submitted_at DESC);
```

#### pricing_rules
```sql
CREATE TABLE pricing_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(50) NOT NULL,  -- factory_constant, customer_variable, calculated

    -- Expression (parsed by SafeExpressionEvaluator)
    expression TEXT NOT NULL,
    /*
    Examples:
    - "quantity * 0.05 + 50"  (wastage calculation)
    - "board_area * board_price_per_sqm"
    - "setup_time + (quantity / machine_speed)"
    */

    -- Dependencies for evaluation order
    dependencies TEXT[],  -- ["quantity", "board_area"]

    -- Versioning
    version INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,

    -- Metadata
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_pricing_rules_category ON pricing_rules(category);
CREATE INDEX idx_pricing_rules_active ON pricing_rules(is_active);
```

---

## 3. API Design

### 3.1 API Structure

```
/api/v1/
├── /auth/
│   ├── POST   /login          # Authenticate user
│   ├── POST   /logout         # End session
│   └── POST   /refresh        # Refresh JWT token
│
├── /estimates/
│   ├── GET    /               # List estimates (paginated)
│   ├── POST   /               # Create new estimate
│   ├── GET    /{id}           # Get estimate details
│   ├── PUT    /{id}           # Update estimate
│   ├── DELETE /{id}           # Delete estimate
│   ├── POST   /{id}/calculate # Recalculate estimate
│   ├── POST   /{id}/quote     # Generate PDF quote
│   └── POST   /{id}/duplicate # Duplicate estimate
│
├── /feedback/
│   ├── GET    /               # List feedback entries
│   ├── POST   /               # Submit feedback
│   ├── GET    /estimate/{id}  # Get feedback for estimate
│   └── GET    /metrics        # Accuracy metrics
│
├── /materials/
│   ├── GET    /               # List materials
│   ├── POST   /               # Add material
│   ├── PUT    /{id}           # Update material
│   ├── DELETE /{id}           # Delete material
│   ├── POST   /import         # Bulk import from CSV
│   └── GET    /export         # Export to CSV
│
├── /customers/
│   ├── GET    /               # List customers
│   ├── POST   /               # Add customer
│   ├── PUT    /{id}           # Update customer
│   └── DELETE /{id}           # Delete customer
│
├── /analytics/
│   ├── GET    /accuracy       # Estimation accuracy report
│   ├── GET    /trends         # Cost/margin trends
│   └── GET    /dashboard      # Dashboard summary
│
└── /admin/
    ├── GET    /users          # List users
    ├── POST   /users          # Create user
    ├── PUT    /users/{id}     # Update user
    ├── GET    /pricing-rules  # List pricing rules
    ├── PUT    /pricing-rules  # Update pricing rule
    └── POST   /ml/retrain     # Trigger ML retraining
```

### 3.2 Key Schemas

#### EstimateCreate (Input)
```python
class EstimateCreate(BaseModel):
    customer_id: Optional[UUID]
    job_name: str

    dimensions: DimensionsInput
    quantity: int = Field(ge=1, le=100000)
    materials: MaterialsInput
    operations: List[OperationType]
    rush_order: bool = False
    complexity_tier: Optional[int] = Field(ge=1, le=5)

class DimensionsInput(BaseModel):
    flat_width: float = Field(ge=10, le=2000)  # mm
    flat_height: float = Field(ge=10, le=2000)
    outer_wrap_width: Optional[float]
    outer_wrap_height: Optional[float]
    liner_width: Optional[float]
    liner_height: Optional[float]
    spine_depth: Optional[float] = Field(ge=0, le=200)
```

#### EstimateResponse (Output)
```python
class EstimateResponse(BaseModel):
    id: UUID
    job_name: str
    status: str

    # Costs
    material_cost: Decimal
    labor_cost: Decimal
    overhead_cost: Decimal
    wastage_cost: Decimal
    total_cost: Decimal

    # Confidence
    confidence_interval: Tuple[Decimal, Decimal]
    confidence_level: float  # 0.0 - 1.0
    ml_enhanced: bool

    # Breakdown
    breakdown: CostBreakdown

    # Metadata
    created_at: datetime
    calculated_at: datetime
```

---

## 4. Core Components

### 4.1 SafeExpressionEvaluator

Replaces `eval()` with AST-based safe evaluation.

```python
# backend/core/safe_evaluator.py

import ast
import operator
from typing import Dict, Any

class SafeExpressionEvaluator:
    """
    Safely evaluate mathematical expressions without eval().

    Supports:
    - Arithmetic: +, -, *, /, //, %, **
    - Comparison: <, <=, >, >=, ==, !=
    - Conditionals: if/else expressions
    - Functions: min, max, round, abs, ceil, floor
    - Variables: referenced by name

    Example:
        evaluator = SafeExpressionEvaluator()
        result = evaluator.evaluate(
            "quantity * unit_price * (1 + wastage_rate)",
            {"quantity": 1000, "unit_price": 0.50, "wastage_rate": 0.05}
        )
        # result = 525.0
    """

    SAFE_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
    }

    SAFE_FUNCTIONS = {
        'min': min,
        'max': max,
        'round': round,
        'abs': abs,
        'ceil': math.ceil,
        'floor': math.floor,
    }

    def evaluate(self, expression: str, variables: Dict[str, Any]) -> Any:
        """Evaluate expression with given variables."""
        tree = ast.parse(expression, mode='eval')
        return self._eval_node(tree.body, variables)

    def _eval_node(self, node: ast.AST, variables: Dict[str, Any]) -> Any:
        # Implementation handles all AST node types safely
        ...
```

### 4.2 Hybrid Estimator

```python
# backend/core/hybrid_estimator.py

class HybridEstimator:
    """
    Combines rule-based and ML predictions with confidence weighting.

    Strategy:
    1. Always compute rule-based estimate (baseline)
    2. If ML model available and sufficient data, compute ML prediction
    3. Blend based on ML confidence score

    Formula:
        final = (1 - ml_weight) * rule_estimate + ml_weight * ml_estimate

    Where ml_weight = f(sample_count, historical_accuracy)
    """

    def __init__(
        self,
        calculation_engine: CalculationEngine,
        ml_predictor: Optional[MLPredictor] = None,
        min_samples_for_ml: int = 50
    ):
        self.calc_engine = calculation_engine
        self.ml_predictor = ml_predictor
        self.min_samples = min_samples_for_ml

    def estimate(self, inputs: EstimateInputs) -> TimeEstimate:
        # Rule-based estimate (always)
        rule_estimate = self.calc_engine.calculate(inputs)

        # ML estimate (when available)
        if self._should_use_ml(inputs):
            ml_estimate = self.ml_predictor.predict(inputs)
            ml_weight = self._calculate_ml_weight(inputs, ml_estimate)

            return self._blend_estimates(
                rule_estimate, ml_estimate, ml_weight
            )

        return TimeEstimate(
            point=rule_estimate.total,
            interval=(rule_estimate.total * 0.85, rule_estimate.total * 1.20),
            confidence=0.7,
            ml_enhanced=False
        )
```

### 4.3 ML Pipeline

```python
# ml/models/time_predictor.py

from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler

class ProductionTimePredictor:
    """
    Predicts production time using HistGradientBoostingRegressor.

    Features:
    - Native categorical support (no manual encoding)
    - Handles missing values
    - Fast training and inference

    Outputs:
    - Point prediction
    - Confidence interval (quantile regression)
    """

    def __init__(self):
        # Main model for point prediction
        self.model = HistGradientBoostingRegressor(
            max_iter=200,
            learning_rate=0.1,
            max_depth=6,
            categorical_features='from_dtype'
        )

        # Quantile models for intervals
        self.model_low = HistGradientBoostingRegressor(
            loss='quantile',
            quantile=0.1,
            max_iter=200
        )
        self.model_high = HistGradientBoostingRegressor(
            loss='quantile',
            quantile=0.9,
            max_iter=200
        )

    def fit(self, X: pd.DataFrame, y: pd.Series):
        """Train all three models."""
        self.model.fit(X, y)
        self.model_low.fit(X, y)
        self.model_high.fit(X, y)

    def predict_with_interval(
        self, X: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return point prediction and confidence interval."""
        point = self.model.predict(X)
        low = self.model_low.predict(X)
        high = self.model_high.predict(X)
        return point, low, high
```

---

## 5. Frontend Design

### 5.1 Page Structure

```
/                       → Dashboard (recent estimates, quick stats)
/estimates              → Estimate list (search, filter, paginate)
/estimates/new          → New estimate form
/estimates/{id}         → Estimate detail + edit
/estimates/{id}/quote   → Quote preview + download

/feedback               → Feedback submission list
/feedback/submit/{id}   → Submit feedback for estimate

/materials              → Material catalog management
/materials/import       → Bulk import interface

/customers              → Customer management
/analytics              → Analytics dashboard
/settings               → User settings
/admin                  → Admin panel (users, rules)
```

### 5.2 Key UI Components

#### Estimate Form (HTMX + Alpine.js)
```html
<!-- Live calculation as user types -->
<form hx-post="/api/v1/estimates/calculate"
      hx-trigger="change delay:300ms"
      hx-target="#cost-preview"
      hx-swap="innerHTML">

    <div x-data="{ showAdvanced: false }">
        <!-- Dimensions Section -->
        <fieldset>
            <legend>Dimensions (mm)</legend>
            <div class="grid grid-cols-2 gap-4">
                <input name="flat_width" type="number" required
                       placeholder="Flat Width" />
                <input name="flat_height" type="number" required
                       placeholder="Flat Height" />
            </div>

            <button type="button" @click="showAdvanced = !showAdvanced">
                Advanced Dimensions
            </button>

            <div x-show="showAdvanced" class="mt-4">
                <!-- Outer wrap, liner, spine -->
            </div>
        </fieldset>

        <!-- Materials Section -->
        <fieldset>
            <legend>Materials</legend>
            <select name="board_type"
                    hx-get="/api/v1/materials/by-category/board"
                    hx-trigger="load">
                <!-- Options loaded via HTMX -->
            </select>
        </fieldset>

        <!-- Operations Checkboxes -->
        <fieldset>
            <legend>Operations</legend>
            <div class="grid grid-cols-2">
                <label>
                    <input type="checkbox" name="operations" value="cutting" />
                    Cutting
                </label>
                <!-- More operations -->
            </div>
        </fieldset>
    </div>
</form>

<!-- Live Cost Preview -->
<div id="cost-preview" class="sticky top-4">
    <div class="bg-white shadow rounded-lg p-6">
        <h3>Estimate Preview</h3>
        <!-- Updated via HTMX -->
        <div class="text-3xl font-bold">£1,250</div>
        <div class="text-sm text-gray-500">
            Confidence: £1,150 - £1,380
        </div>
    </div>
</div>
```

---

## 6. Deployment Architecture

### 6.1 Development Environment

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app/backend
      - ./frontend:/app/frontend
    environment:
      - DATABASE_URL=postgresql://ksp:ksp@db:5432/ksp_estimator
      - DEBUG=true
    depends_on:
      - db
    command: uvicorn backend.main:app --reload --host 0.0.0.0

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=ksp
      - POSTGRES_PASSWORD=ksp
      - POSTGRES_DB=ksp_estimator
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

### 6.2 Production Environment

```
┌─────────────────────────────────────────────────────────────┐
│                        VPS (4GB RAM)                         │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                      Docker                             │  │
│  │                                                         │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │  │
│  │  │   Nginx     │  │   FastAPI   │  │  PostgreSQL │    │  │
│  │  │   :443      │─▶│    :8000    │─▶│    :5432    │    │  │
│  │  │  (2 workers)│  │ (4 workers) │  │             │    │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘    │  │
│  │                                                         │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  Persistent volumes: /data/postgres, /data/models           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Testing Strategy

### 7.1 Test Pyramid

```
              ┌─────────┐
              │   E2E   │  5% - Critical user journeys
              │ (Playwright)
              ├─────────┤
              │         │
         ┌────┤ Integration │  25% - API, DB, services
         │    │ (pytest)    │
         │    ├─────────────┤
         │    │             │
         │    │    Unit     │  70% - Calculation engine,
         │    │  (pytest)   │        safe evaluator, ML
         │    │             │
         └────┴─────────────┘
```

### 7.2 Critical Test Cases

| Component | Test Case | Priority |
|-----------|-----------|----------|
| Calculation Engine | 100% match with legacy formulas | P0 |
| SafeExpressionEvaluator | Rejects malicious input | P0 |
| SafeExpressionEvaluator | Handles all valid expressions | P0 |
| Estimate API | Creates estimate with valid input | P0 |
| Estimate API | Rejects invalid dimensions | P0 |
| Feedback API | Records feedback correctly | P0 |
| ML Predictor | Predictions within confidence interval | P1 |
| Material Import | Handles CSV edge cases | P1 |

---

## 8. Security Considerations

### 8.1 Threat Mitigation

| Threat | Mitigation |
|--------|------------|
| Code injection via expressions | SafeExpressionEvaluator (AST-based) |
| SQL injection | SQLAlchemy ORM, parameterized queries |
| XSS | Jinja2 auto-escaping, CSP headers |
| CSRF | SameSite cookies, CSRF tokens |
| Unauthorized access | JWT auth, role-based permissions |
| Data exposure | Field-level access control |

### 8.2 SafeExpressionEvaluator Security

```python
# Blocked patterns
BLOCKED = [
    '__',           # No dunder access
    'import',       # No imports
    'exec',         # No exec
    'eval',         # No eval
    'open',         # No file access
    'os.',          # No OS access
    'sys.',         # No sys access
    'subprocess',   # No subprocess
]

def validate_expression(expression: str) -> bool:
    """Reject expressions containing dangerous patterns."""
    for pattern in BLOCKED:
        if pattern in expression.lower():
            raise SecurityError(f"Blocked pattern: {pattern}")
    return True
```

---

## 9. Monitoring & Observability

### 9.1 Key Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| API response time (p95) | <500ms | >1000ms |
| Estimate calculation time | <200ms | >500ms |
| Error rate | <1% | >5% |
| ML prediction accuracy | <15% MAE | >25% MAE |

### 9.2 Logging Strategy

```python
# Structured logging format
{
    "timestamp": "2026-01-20T10:30:00Z",
    "level": "INFO",
    "service": "estimation",
    "trace_id": "abc123",
    "user_id": "user-456",
    "action": "estimate_calculated",
    "estimate_id": "est-789",
    "duration_ms": 145,
    "ml_used": true
}
```

---

*Document Version: 1.0 | Last Updated: 2026-01-20*
