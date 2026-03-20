"""Estimates API router."""

import io
import logging
import random
import string
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.core.calculation_engine import (
    CalculationEngine,
    ComplexityTier,
    DimensionInputs,
    EstimateInputs,
    MaterialInputs,
)
from backend.app.db.session import get_db
from backend.app.models.estimate import Estimate, EstimateStatus
from backend.app.schemas.estimate import (
    CostBreakdown,
    EstimateCalculateResponse,
    EstimateCreate,
    EstimateListResponse,
    EstimateResponse,
    EstimateUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _load_pricing_rules() -> Optional[pd.DataFrame]:
    """Load pricing rules CSV. Returns None if file not found."""
    settings = get_settings()
    csv_path = Path(settings.pricing_rules_csv)
    if not csv_path.exists():
        logger.warning(f"Pricing rules CSV not found: {csv_path}")
        return None
    return pd.read_csv(csv_path, index_col="Feature")


def _run_calculation(estimate_in: EstimateCreate) -> "CostBreakdownResult":
    """Run the calculation engine and return results."""
    pricing_df = _load_pricing_rules()
    engine = CalculationEngine(pricing_df)

    engine_inputs = EstimateInputs(
        dimensions=DimensionInputs(
            flat_width=estimate_in.dimensions.flat_width,
            flat_height=estimate_in.dimensions.flat_height,
            outer_wrap_width=estimate_in.dimensions.outer_wrap_width,
            outer_wrap_height=estimate_in.dimensions.outer_wrap_height,
            liner_width=estimate_in.dimensions.liner_width,
            liner_height=estimate_in.dimensions.liner_height,
            spine_depth=estimate_in.dimensions.spine_depth,
        ),
        quantity=estimate_in.quantity,
        materials=MaterialInputs(
            board_type=estimate_in.materials.board_type,
            board_thickness=estimate_in.materials.board_thickness,
            outer_wrap=estimate_in.materials.outer_wrap,
            liner=estimate_in.materials.liner,
            additional_materials=estimate_in.materials.additional_materials,
        ),
        operations=estimate_in.operations,
        complexity_tier=ComplexityTier(estimate_in.complexity_tier),
        rush_order=estimate_in.rush_order,
        notes=estimate_in.notes,
    )

    return engine.calculate(engine_inputs)


def _run_calculation_from_stored(inputs: dict) -> "CostBreakdownResult":
    """Run calculation from stored estimate inputs dict."""
    dims = inputs.get("dimensions", {})
    mats = inputs.get("materials", {})
    pricing_df = _load_pricing_rules()
    engine = CalculationEngine(pricing_df)

    engine_inputs = EstimateInputs(
        dimensions=DimensionInputs(
            flat_width=dims.get("flat_width", 300),
            flat_height=dims.get("flat_height", 400),
            outer_wrap_width=dims.get("outer_wrap_width"),
            outer_wrap_height=dims.get("outer_wrap_height"),
            liner_width=dims.get("liner_width"),
            liner_height=dims.get("liner_height"),
            spine_depth=dims.get("spine_depth", 0),
        ),
        quantity=inputs.get("quantity", 1000),
        materials=MaterialInputs(
            board_type=mats.get("board_type", "dutch_grey_2mm"),
            board_thickness=mats.get("board_thickness", 2.0),
            outer_wrap=mats.get("outer_wrap", "buckram_cloth"),
            liner=mats.get("liner", "uncoated_paper_120gsm"),
            additional_materials=mats.get("additional_materials", []),
        ),
        operations=inputs.get("operations", ["cutting"]),
        complexity_tier=ComplexityTier(inputs.get("complexity_tier", 3)),
        rush_order=inputs.get("rush_order", False),
        notes=inputs.get("notes"),
    )

    return engine.calculate(engine_inputs)


def generate_reference_number() -> str:
    """Generate a unique estimate reference number."""
    date_part = datetime.now().strftime("%Y%m%d")
    random_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"EST-{date_part}-{random_part}"


@router.post("/calculate", response_model=EstimateCalculateResponse)
async def calculate_estimate_preview(estimate_in: EstimateCreate):
    """
    Calculate an estimate without saving to the database.

    Returns the cost breakdown, confidence interval, and audit trail.
    Useful for previewing costs before creating a persisted estimate.
    """
    breakdown = _run_calculation(estimate_in)

    return EstimateCalculateResponse(
        breakdown=CostBreakdown(
            material_costs={k: v for k, v in breakdown.material_costs.items()},
            labor_hours=breakdown.labor_hours,
            labor_cost=breakdown.labor_cost,
            overhead_cost=breakdown.overhead_cost,
            wastage_cost=breakdown.wastage_cost,
            complexity_adjustment=breakdown.complexity_adjustment,
            rush_premium=breakdown.rush_premium,
            total_cost=breakdown.total_cost,
            unit_cost=breakdown.unit_cost,
            confidence_interval=breakdown.confidence_interval,
            confidence_level=breakdown.confidence_level,
            audit_trail=breakdown.audit_trail,
        ),
        confidence_interval=breakdown.confidence_interval,
        confidence_level=breakdown.confidence_level,
        ml_enhanced=False,
    )


@router.get("", response_model=EstimateListResponse)
async def list_estimates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[EstimateStatus] = None,
    customer_id: Optional[UUID] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List estimates with pagination and filtering.

    - **page**: Page number (default 1)
    - **page_size**: Items per page (default 20, max 100)
    - **status**: Filter by status
    - **customer_id**: Filter by customer
    - **search**: Search in job name and reference number
    """
    # Build query
    query = select(Estimate)

    if status:
        query = query.where(Estimate.status == status)
    if customer_id:
        query = query.where(Estimate.customer_id == customer_id)
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (Estimate.job_name.ilike(search_filter))
            | (Estimate.reference_number.ilike(search_filter))
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Apply pagination
    query = query.order_by(Estimate.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    estimates = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return EstimateListResponse(
        items=[EstimateResponse.model_validate(e) for e in estimates],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("", response_model=EstimateResponse, status_code=status.HTTP_201_CREATED)
async def create_estimate(
    estimate_in: EstimateCreate,
    db: AsyncSession = Depends(get_db),
    # user: User = Depends(get_current_user),  # TODO: Add auth
):
    """
    Create a new estimate.

    The estimate will be calculated automatically and saved as a draft.
    """
    # Build inputs dict for storage
    inputs = {
        "dimensions": estimate_in.dimensions.model_dump(),
        "quantity": estimate_in.quantity,
        "materials": estimate_in.materials.model_dump(),
        "operations": estimate_in.operations,
        "complexity_tier": estimate_in.complexity_tier,
        "rush_order": estimate_in.rush_order,
        "notes": estimate_in.notes,
    }

    # Run real calculation
    breakdown = _run_calculation(estimate_in)

    outputs = breakdown.to_dict()

    # Create estimate
    estimate = Estimate(
        reference_number=generate_reference_number(),
        job_name=estimate_in.job_name,
        customer_id=estimate_in.customer_id,
        user_id=UUID("00000000-0000-0000-0000-000000000000"),  # TODO: Get from auth
        complexity_tier=estimate_in.complexity_tier,
        inputs=inputs,
        outputs=outputs,
        total_cost=breakdown.total_cost,
        confidence_low=breakdown.confidence_interval[0],
        confidence_high=breakdown.confidence_interval[1],
        confidence_level=breakdown.confidence_level,
        calculated_at=datetime.utcnow(),
    )

    db.add(estimate)
    await db.commit()
    await db.refresh(estimate)

    return EstimateResponse.model_validate(estimate)


@router.get("/{estimate_id}", response_model=EstimateResponse)
async def get_estimate(
    estimate_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific estimate by ID."""
    result = await db.execute(select(Estimate).where(Estimate.id == estimate_id))
    estimate = result.scalar_one_or_none()

    if not estimate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Estimate {estimate_id} not found",
        )

    return EstimateResponse.model_validate(estimate)


@router.put("/{estimate_id}", response_model=EstimateResponse)
async def update_estimate(
    estimate_id: UUID,
    estimate_in: EstimateUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update an estimate.

    Only draft estimates can have their inputs modified.
    """
    result = await db.execute(select(Estimate).where(Estimate.id == estimate_id))
    estimate = result.scalar_one_or_none()

    if not estimate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Estimate {estimate_id} not found",
        )

    # Update fields
    update_data = estimate_in.model_dump(exclude_unset=True)

    # Handle nested updates for inputs
    if any(k in update_data for k in ["dimensions", "quantity", "materials", "operations"]):
        if estimate.status != EstimateStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only modify inputs on draft estimates",
            )

        inputs = dict(estimate.inputs)
        if "dimensions" in update_data:
            inputs["dimensions"] = update_data.pop("dimensions")
        if "quantity" in update_data:
            inputs["quantity"] = update_data.pop("quantity")
        if "materials" in update_data:
            inputs["materials"] = update_data.pop("materials")
        if "operations" in update_data:
            inputs["operations"] = update_data.pop("operations")
        estimate.inputs = inputs

    # Update other fields
    for field, value in update_data.items():
        if hasattr(estimate, field):
            setattr(estimate, field, value)

    await db.commit()
    await db.refresh(estimate)

    return EstimateResponse.model_validate(estimate)


@router.delete("/{estimate_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_estimate(
    estimate_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an estimate.

    Only draft estimates can be deleted.
    """
    result = await db.execute(select(Estimate).where(Estimate.id == estimate_id))
    estimate = result.scalar_one_or_none()

    if not estimate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Estimate {estimate_id} not found",
        )

    if estimate.status != EstimateStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only delete draft estimates",
        )

    await db.delete(estimate)
    await db.commit()


@router.post("/{estimate_id}/calculate", response_model=EstimateCalculateResponse)
async def recalculate_estimate(
    estimate_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Recalculate an estimate.

    Updates the outputs and costs based on current pricing rules.
    """
    result = await db.execute(select(Estimate).where(Estimate.id == estimate_id))
    estimate = result.scalar_one_or_none()

    if not estimate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Estimate {estimate_id} not found",
        )

    # Run real calculation from stored inputs
    engine_result = _run_calculation_from_stored(dict(estimate.inputs))

    breakdown = CostBreakdown(
        material_costs={k: v for k, v in engine_result.material_costs.items()},
        labor_hours=engine_result.labor_hours,
        labor_cost=engine_result.labor_cost,
        overhead_cost=engine_result.overhead_cost,
        wastage_cost=engine_result.wastage_cost,
        complexity_adjustment=engine_result.complexity_adjustment,
        rush_premium=engine_result.rush_premium,
        total_cost=engine_result.total_cost,
        unit_cost=engine_result.unit_cost,
        confidence_interval=engine_result.confidence_interval,
        confidence_level=engine_result.confidence_level,
        audit_trail=engine_result.audit_trail,
    )

    # Update estimate in database
    estimate.outputs = engine_result.to_dict()
    estimate.total_cost = engine_result.total_cost
    estimate.confidence_low = engine_result.confidence_interval[0]
    estimate.confidence_high = engine_result.confidence_interval[1]
    estimate.confidence_level = engine_result.confidence_level
    estimate.calculated_at = datetime.utcnow()

    await db.commit()

    return EstimateCalculateResponse(
        breakdown=breakdown,
        confidence_interval=engine_result.confidence_interval,
        confidence_level=engine_result.confidence_level,
        ml_enhanced=False,
    )


@router.post("/{estimate_id}/quote")
async def generate_quote_pdf(
    estimate_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a PDF quote for an estimate.

    Returns the PDF as a downloadable file. Also updates the estimate
    status to 'quoted' and records the quote timestamp.
    """
    from fastapi.responses import StreamingResponse

    from backend.app.models.customer import Customer
    from backend.app.services.pdf_service import generate_quote_pdf as _gen_pdf

    result = await db.execute(select(Estimate).where(Estimate.id == estimate_id))
    estimate = result.scalar_one_or_none()

    if not estimate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Estimate {estimate_id} not found",
        )

    if not estimate.total_cost:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Estimate must be calculated before generating a quote",
        )

    # Load customer if linked
    customer = None
    if estimate.customer_id:
        cust_result = await db.execute(
            select(Customer).where(Customer.id == estimate.customer_id)
        )
        customer = cust_result.scalar_one_or_none()

    # Generate PDF
    pdf_bytes = _gen_pdf(estimate, customer)

    # Update estimate status
    if estimate.status == EstimateStatus.DRAFT:
        estimate.status = EstimateStatus.QUOTED
        estimate.quoted_at = datetime.utcnow()
        await db.commit()

    filename = f"Quote_{estimate.reference_number}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{estimate_id}/duplicate", response_model=EstimateResponse)
async def duplicate_estimate(
    estimate_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Duplicate an estimate.

    Creates a new draft estimate with the same inputs.
    """
    result = await db.execute(select(Estimate).where(Estimate.id == estimate_id))
    original = result.scalar_one_or_none()

    if not original:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Estimate {estimate_id} not found",
        )

    # Create duplicate
    duplicate = Estimate(
        reference_number=generate_reference_number(),
        job_name=f"{original.job_name} (Copy)",
        customer_id=original.customer_id,
        user_id=original.user_id,
        complexity_tier=original.complexity_tier,
        inputs=dict(original.inputs),
        outputs=dict(original.outputs) if original.outputs else None,
        total_cost=original.total_cost,
        confidence_low=original.confidence_low,
        confidence_high=original.confidence_high,
        confidence_level=original.confidence_level,
        calculated_at=datetime.utcnow(),
        internal_notes=f"Duplicated from {original.reference_number}",
    )

    db.add(duplicate)
    await db.commit()
    await db.refresh(duplicate)

    return EstimateResponse.model_validate(duplicate)
