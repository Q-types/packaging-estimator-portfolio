"""Admin API router for user management, pricing rules, and ML models."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.models.ml_model import MLModel
from backend.app.models.pricing_rule import PricingRule, RuleCategory
from backend.app.models.user import User, UserRole

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: Optional[str]
    role: UserRole
    is_active: bool
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class UserCreate(BaseModel):
    email: str = Field(max_length=255)
    full_name: Optional[str] = Field(None, max_length=255)
    password: str = Field(min_length=8)
    role: UserRole = UserRole.VIEWER


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=255)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int


class PricingRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    display_name: Optional[str]
    description: Optional[str]
    category: RuleCategory
    expression: str
    dependencies: Optional[list[str]]
    default_value: Optional[float]
    unit: Optional[str]
    version: int
    is_active: bool
    effective_from: Optional[datetime]
    effective_to: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class PricingRuleCreate(BaseModel):
    name: str = Field(max_length=100)
    display_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    category: RuleCategory
    expression: str
    dependencies: Optional[list[str]] = None
    default_value: Optional[float] = None
    unit: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None


class PricingRuleUpdate(BaseModel):
    display_name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    expression: Optional[str] = None
    dependencies: Optional[list[str]] = None
    default_value: Optional[float] = None
    unit: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None
    notes: Optional[str] = None


class MLModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    version: str
    description: Optional[str]
    model_type: str
    target_variable: str
    trained_at: datetime
    training_samples: int
    feature_names: list[str]
    metrics: dict[str, Any]
    is_active: bool
    is_production: bool
    traffic_percentage: int
    trained_by: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime


class MLModelUpdate(BaseModel):
    is_active: Optional[bool] = None
    is_production: Optional[bool] = None
    traffic_percentage: Optional[int] = Field(None, ge=0, le=100)
    notes: Optional[str] = None


# ── User Management ─────────────────────────────────────────────────────────


@router.get("/users", response_model=UserListResponse)
async def list_users(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """List all users."""
    query = select(User)
    if active_only:
        query = query.where(User.is_active.is_(True))
    query = query.order_by(User.email)

    result = await db.execute(query)
    users = result.scalars().all()

    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=len(users),
    )


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new user."""
    # Check for duplicate email
    existing = await db.execute(select(User).where(User.email == user_in.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email {user_in.email} already exists",
        )

    from backend.app.routers.auth import hash_password

    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        password_hash=hash_password(user_in.password),
        role=user_in.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )
    return UserResponse.model_validate(user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a user's role or active status."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {user_id} not found",
        )

    update_data = user_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


# ── Pricing Rules Management ────────────────────────────────────────────────


@router.get("/pricing-rules", response_model=list[PricingRuleResponse])
async def list_pricing_rules(
    category: Optional[RuleCategory] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """List pricing rules with optional category filter."""
    query = select(PricingRule)
    if active_only:
        query = query.where(PricingRule.is_active.is_(True))
    if category:
        query = query.where(PricingRule.category == category)

    query = query.order_by(PricingRule.name)
    result = await db.execute(query)
    rules = result.scalars().all()
    return [PricingRuleResponse.model_validate(r) for r in rules]


@router.post(
    "/pricing-rules", response_model=PricingRuleResponse, status_code=status.HTTP_201_CREATED
)
async def create_pricing_rule(
    rule_in: PricingRuleCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new pricing rule."""
    # Validate expression safety
    from backend.app.core.safe_evaluator import SafeExpressionEvaluator

    evaluator = SafeExpressionEvaluator()
    try:
        evaluator.validate(rule_in.expression)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid expression: {e}",
        )

    # Check for duplicate name
    existing = await db.execute(
        select(PricingRule).where(PricingRule.name == rule_in.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Pricing rule '{rule_in.name}' already exists",
        )

    rule = PricingRule(**rule_in.model_dump(), version=1, is_active=True)
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return PricingRuleResponse.model_validate(rule)


@router.get("/pricing-rules/{rule_id}", response_model=PricingRuleResponse)
async def get_pricing_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific pricing rule."""
    result = await db.execute(select(PricingRule).where(PricingRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pricing rule {rule_id} not found",
        )
    return PricingRuleResponse.model_validate(rule)


@router.put("/pricing-rules/{rule_id}", response_model=PricingRuleResponse)
async def update_pricing_rule(
    rule_id: UUID,
    rule_in: PricingRuleUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update a pricing rule.

    If the expression changes, the version is incremented.
    """
    result = await db.execute(select(PricingRule).where(PricingRule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pricing rule {rule_id} not found",
        )

    update_data = rule_in.model_dump(exclude_unset=True)

    # Validate new expression if provided
    if "expression" in update_data:
        from backend.app.core.safe_evaluator import SafeExpressionEvaluator

        evaluator = SafeExpressionEvaluator()
        try:
            evaluator.validate(update_data["expression"])
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid expression: {e}",
            )
        # Bump version on expression change
        if update_data["expression"] != rule.expression:
            rule.version += 1

    for field, value in update_data.items():
        setattr(rule, field, value)

    await db.commit()
    await db.refresh(rule)
    return PricingRuleResponse.model_validate(rule)


# ── ML Model Management ─────────────────────────────────────────────────────


@router.get("/ml-models", response_model=list[MLModelResponse])
async def list_ml_models(
    active_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """List all ML models."""
    query = select(MLModel)
    if active_only:
        query = query.where(MLModel.is_active.is_(True))

    query = query.order_by(MLModel.trained_at.desc())
    result = await db.execute(query)
    models = result.scalars().all()
    return [MLModelResponse.model_validate(m) for m in models]


@router.get("/ml-models/{model_id}", response_model=MLModelResponse)
async def get_ml_model(
    model_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific ML model."""
    result = await db.execute(select(MLModel).where(MLModel.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ML model {model_id} not found",
        )
    return MLModelResponse.model_validate(model)


@router.put("/ml-models/{model_id}", response_model=MLModelResponse)
async def update_ml_model(
    model_id: UUID,
    model_in: MLModelUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update an ML model's status.

    Setting is_production=true will deactivate the current production model.
    """
    result = await db.execute(select(MLModel).where(MLModel.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ML model {model_id} not found",
        )

    update_data = model_in.model_dump(exclude_unset=True)

    # If promoting to production, demote the current production model
    if update_data.get("is_production"):
        await db.execute(
            update(MLModel)
            .where(MLModel.is_production.is_(True))
            .values(is_production=False, deactivated_at=datetime.now(timezone.utc))
        )
        model.activated_at = datetime.now(timezone.utc)
        model.is_active = True

    for field, value in update_data.items():
        setattr(model, field, value)

    await db.commit()
    await db.refresh(model)
    return MLModelResponse.model_validate(model)


# ── Dashboard Stats ──────────────────────────────────────────────────────────


@router.get("/stats")
async def get_admin_stats(db: AsyncSession = Depends(get_db)):
    """Get admin dashboard statistics."""
    from backend.app.models.customer import Customer
    from backend.app.models.estimate import Estimate
    from backend.app.models.feedback import Feedback

    user_count = await db.scalar(
        select(func.count()).select_from(User).where(User.is_active.is_(True))
    ) or 0
    customer_count = await db.scalar(
        select(func.count()).select_from(Customer).where(Customer.is_active.is_(True))
    ) or 0
    estimate_count = await db.scalar(
        select(func.count()).select_from(Estimate)
    ) or 0
    feedback_count = await db.scalar(
        select(func.count()).select_from(Feedback)
    ) or 0
    rule_count = await db.scalar(
        select(func.count())
        .select_from(PricingRule)
        .where(PricingRule.is_active.is_(True))
    ) or 0
    model_count = await db.scalar(
        select(func.count()).select_from(MLModel).where(MLModel.is_active.is_(True))
    ) or 0

    return {
        "users": user_count,
        "customers": customer_count,
        "estimates": estimate_count,
        "feedback_submissions": feedback_count,
        "pricing_rules": rule_count,
        "ml_models_active": model_count,
    }
