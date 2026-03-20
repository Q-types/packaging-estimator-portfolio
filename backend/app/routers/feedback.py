"""Feedback API router."""

from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.models.estimate import Estimate
from backend.app.models.feedback import Feedback
from backend.app.schemas.feedback import (
    AccuracyMetrics,
    EstimateFeedbackSummary,
    FeedbackCreate,
    FeedbackListResponse,
    FeedbackResponse,
    FeedbackUpdate,
)

router = APIRouter()


@router.get("", response_model=FeedbackListResponse)
async def list_feedback(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    operation: Optional[str] = None,
    validated_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """
    List feedback entries with pagination and filtering.

    - **page**: Page number (default 1)
    - **page_size**: Items per page (default 20, max 100)
    - **operation**: Filter by operation type
    - **validated_only**: Only show validated feedback
    """
    query = select(Feedback)

    if operation:
        query = query.where(Feedback.operation == operation)
    if validated_only:
        query = query.where(Feedback.is_validated == True)  # noqa: E712

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Apply pagination
    query = query.order_by(Feedback.submitted_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    feedback_entries = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return FeedbackListResponse(
        items=[FeedbackResponse.model_validate(f) for f in feedback_entries],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_feedback(
    feedback_in: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
    # user: User = Depends(get_current_user),  # TODO: Add auth
):
    """
    Submit production feedback for an estimate.

    Feedback can be submitted incrementally - one operation at a time.
    """
    # Verify estimate exists
    result = await db.execute(
        select(Estimate).where(Estimate.id == feedback_in.estimate_id)
    )
    estimate = result.scalar_one_or_none()

    if not estimate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Estimate {feedback_in.estimate_id} not found",
        )

    # Check for duplicate operation feedback
    result = await db.execute(
        select(Feedback).where(
            Feedback.estimate_id == feedback_in.estimate_id,
            Feedback.operation == feedback_in.operation,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Feedback for operation '{feedback_in.operation}' already exists",
        )

    feedback = Feedback(
        **feedback_in.model_dump(),
        # submitted_by=user.id,  # TODO: Add auth
    )

    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)

    return FeedbackResponse.model_validate(feedback)


@router.get("/estimate/{estimate_id}", response_model=EstimateFeedbackSummary)
async def get_feedback_for_estimate(
    estimate_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get all feedback for a specific estimate with summary."""
    # Verify estimate exists
    result = await db.execute(select(Estimate).where(Estimate.id == estimate_id))
    estimate = result.scalar_one_or_none()

    if not estimate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Estimate {estimate_id} not found",
        )

    # Get all feedback
    result = await db.execute(
        select(Feedback)
        .where(Feedback.estimate_id == estimate_id)
        .order_by(Feedback.operation)
    )
    feedback_entries = result.scalars().all()

    # Calculate summary
    total_estimated_time = 0
    total_actual_time = 0
    total_estimated_material = Decimal("0")
    total_actual_material = Decimal("0")
    total_yield = 0.0
    total_rework = 0
    yield_count = 0

    for f in feedback_entries:
        if f.estimated_setup_time and f.estimated_run_time:
            total_estimated_time += f.estimated_setup_time + f.estimated_run_time
        if f.actual_setup_time and f.actual_run_time:
            total_actual_time += f.actual_setup_time + f.actual_run_time
        if f.estimated_material_usage:
            total_estimated_material += Decimal(str(f.estimated_material_usage))
        if f.actual_material_usage:
            total_actual_material += Decimal(str(f.actual_material_usage))
        if f.first_pass_yield is not None:
            total_yield += f.first_pass_yield
            yield_count += 1
        if f.rework_time:
            total_rework += f.rework_time

    # Get expected operations from estimate
    expected_operations = estimate.inputs.get("operations", [])

    time_variance = (
        ((total_actual_time - total_estimated_time) / total_estimated_time * 100)
        if total_estimated_time > 0
        else 0.0
    )

    return EstimateFeedbackSummary(
        estimate_id=estimate_id,
        total_operations=len(expected_operations),
        completed_operations=len(feedback_entries),
        total_estimated_time=total_estimated_time,
        total_actual_time=total_actual_time,
        time_variance_percent=time_variance,
        total_estimated_material=total_estimated_material,
        total_actual_material=total_actual_material,
        avg_first_pass_yield=total_yield / yield_count if yield_count > 0 else 0.0,
        total_rework_time=total_rework,
        operations=[FeedbackResponse.model_validate(f) for f in feedback_entries],
    )


@router.get("/metrics", response_model=AccuracyMetrics)
async def get_accuracy_metrics(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """
    Get estimation accuracy metrics.

    Aggregated statistics comparing estimates vs actuals.
    """
    # Get all feedback with both estimated and actual values
    result = await db.execute(
        select(Feedback).where(
            Feedback.actual_setup_time.isnot(None),
            Feedback.actual_run_time.isnot(None),
        )
    )
    feedback_entries = result.scalars().all()

    if not feedback_entries:
        return AccuracyMetrics(
            total_feedback_entries=0,
            operations_covered=[],
            avg_time_variance_percent=0.0,
            time_underestimates=0,
            time_overestimates=0,
            avg_material_variance_percent=0.0,
            avg_first_pass_yield=0.0,
            by_operation={},
        )

    # Calculate metrics
    operations = set()
    time_variances = []
    material_variances = []
    yields = []
    underestimates = 0
    overestimates = 0
    by_operation: dict[str, dict] = {}

    for f in feedback_entries:
        operations.add(f.operation)

        # Time variance
        estimated_time = (f.estimated_setup_time or 0) + (f.estimated_run_time or 0)
        actual_time = (f.actual_setup_time or 0) + (f.actual_run_time or 0)

        if estimated_time > 0:
            variance = (actual_time - estimated_time) / estimated_time * 100
            time_variances.append(variance)
            if variance > 0:
                underestimates += 1
            else:
                overestimates += 1

            # By operation
            if f.operation not in by_operation:
                by_operation[f.operation] = {
                    "count": 0,
                    "total_variance": 0.0,
                    "total_yield": 0.0,
                }
            by_operation[f.operation]["count"] += 1
            by_operation[f.operation]["total_variance"] += variance

        # Material variance
        if f.estimated_material_usage and f.actual_material_usage:
            mat_variance = (
                (float(f.actual_material_usage) - float(f.estimated_material_usage))
                / float(f.estimated_material_usage)
                * 100
            )
            material_variances.append(mat_variance)

        # Yield
        if f.first_pass_yield is not None:
            yields.append(f.first_pass_yield)
            if f.operation in by_operation:
                by_operation[f.operation]["total_yield"] += f.first_pass_yield

    # Calculate averages per operation
    for op in by_operation:
        count = by_operation[op]["count"]
        by_operation[op] = {
            "avg_time_variance": by_operation[op]["total_variance"] / count,
            "avg_yield": by_operation[op]["total_yield"] / count if count > 0 else 0,
            "sample_count": count,
        }

    return AccuracyMetrics(
        total_feedback_entries=len(feedback_entries),
        operations_covered=sorted(operations),
        avg_time_variance_percent=(
            sum(time_variances) / len(time_variances) if time_variances else 0.0
        ),
        time_underestimates=underestimates,
        time_overestimates=overestimates,
        avg_material_variance_percent=(
            sum(material_variances) / len(material_variances)
            if material_variances
            else 0.0
        ),
        avg_first_pass_yield=sum(yields) / len(yields) if yields else 0.0,
        by_operation=by_operation,
    )


@router.get("/{feedback_id}", response_model=FeedbackResponse)
async def get_feedback(
    feedback_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific feedback entry by ID."""
    result = await db.execute(select(Feedback).where(Feedback.id == feedback_id))
    feedback = result.scalar_one_or_none()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feedback {feedback_id} not found",
        )

    return FeedbackResponse.model_validate(feedback)


@router.put("/{feedback_id}", response_model=FeedbackResponse)
async def update_feedback(
    feedback_id: UUID,
    feedback_in: FeedbackUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a feedback entry."""
    result = await db.execute(select(Feedback).where(Feedback.id == feedback_id))
    feedback = result.scalar_one_or_none()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feedback {feedback_id} not found",
        )

    update_data = feedback_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(feedback, field, value)

    await db.commit()
    await db.refresh(feedback)

    return FeedbackResponse.model_validate(feedback)


@router.post("/{feedback_id}/validate", response_model=FeedbackResponse)
async def validate_feedback(
    feedback_id: UUID,
    db: AsyncSession = Depends(get_db),
    # user: User = Depends(get_current_user),  # TODO: Add auth
):
    """
    Mark feedback as validated.

    Validated feedback is used for ML training.
    """
    result = await db.execute(select(Feedback).where(Feedback.id == feedback_id))
    feedback = result.scalar_one_or_none()

    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Feedback {feedback_id} not found",
        )

    from datetime import datetime

    feedback.is_validated = True
    feedback.validated_at = datetime.utcnow()
    # feedback.validated_by = user.id  # TODO: Add auth

    await db.commit()
    await db.refresh(feedback)

    return FeedbackResponse.model_validate(feedback)
