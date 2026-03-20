"""Materials API router."""

from datetime import datetime
from decimal import Decimal
from io import StringIO
from typing import Optional
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_db
from backend.app.models.material import Material, MaterialPrice
from backend.app.schemas.material import (
    BulkPriceUpdate,
    BulkPriceUpdateRequest,
    MaterialCategory,
    MaterialCreate,
    MaterialListResponse,
    MaterialPriceCreate,
    MaterialPriceResponse,
    MaterialResponse,
    MaterialUpdate,
)

router = APIRouter()


@router.get("", response_model=MaterialListResponse)
async def list_materials(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: Optional[MaterialCategory] = None,
    search: Optional[str] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """
    List materials with pagination and filtering.

    - **page**: Page number (default 1)
    - **page_size**: Items per page (default 20, max 100)
    - **category**: Filter by material category
    - **search**: Search in name and SKU
    - **active_only**: Only show active materials (default true)
    """
    query = select(Material)

    if category:
        query = query.where(Material.category == category)
    if active_only:
        query = query.where(Material.is_active == True)  # noqa: E712
    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (Material.name.ilike(search_filter)) | (Material.sku.ilike(search_filter))
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Apply pagination
    query = query.order_by(Material.name)
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    materials = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size

    return MaterialListResponse(
        items=[MaterialResponse.model_validate(m) for m in materials],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("", response_model=MaterialResponse, status_code=status.HTTP_201_CREATED)
async def create_material(
    material_in: MaterialCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new material."""
    # Check for duplicate SKU
    if material_in.sku:
        result = await db.execute(
            select(Material).where(Material.sku == material_in.sku)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Material with SKU {material_in.sku} already exists",
            )

    material = Material(
        **material_in.model_dump(),
        last_price_update=datetime.utcnow(),
    )

    db.add(material)
    await db.commit()
    await db.refresh(material)

    # Create initial price history entry
    price_entry = MaterialPrice(
        material_id=material.id,
        price=material.current_price,
        effective_from=datetime.utcnow(),
        source="initial_creation",
    )
    db.add(price_entry)
    await db.commit()

    return MaterialResponse.model_validate(material)


@router.get("/by-category/{category}", response_model=list[MaterialResponse])
async def get_materials_by_category(
    category: MaterialCategory,
    db: AsyncSession = Depends(get_db),
):
    """Get all active materials in a category."""
    result = await db.execute(
        select(Material)
        .where(Material.category == category)
        .where(Material.is_active == True)  # noqa: E712
        .order_by(Material.name)
    )
    materials = result.scalars().all()
    return [MaterialResponse.model_validate(m) for m in materials]


@router.get("/{material_id}", response_model=MaterialResponse)
async def get_material(
    material_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific material by ID."""
    result = await db.execute(select(Material).where(Material.id == material_id))
    material = result.scalar_one_or_none()

    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Material {material_id} not found",
        )

    return MaterialResponse.model_validate(material)


@router.put("/{material_id}", response_model=MaterialResponse)
async def update_material(
    material_id: UUID,
    material_in: MaterialUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a material."""
    result = await db.execute(select(Material).where(Material.id == material_id))
    material = result.scalar_one_or_none()

    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Material {material_id} not found",
        )

    update_data = material_in.model_dump(exclude_unset=True)

    # Track price changes
    if "current_price" in update_data and update_data["current_price"] != material.current_price:
        price_entry = MaterialPrice(
            material_id=material.id,
            price=update_data["current_price"],
            effective_from=datetime.utcnow(),
            source="manual_update",
        )
        db.add(price_entry)
        update_data["last_price_update"] = datetime.utcnow()

    for field, value in update_data.items():
        setattr(material, field, value)

    await db.commit()
    await db.refresh(material)

    return MaterialResponse.model_validate(material)


@router.delete("/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material(
    material_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Soft delete a material (set inactive)."""
    result = await db.execute(select(Material).where(Material.id == material_id))
    material = result.scalar_one_or_none()

    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Material {material_id} not found",
        )

    material.is_active = False
    await db.commit()


@router.get("/{material_id}/price-history", response_model=list[MaterialPriceResponse])
async def get_material_price_history(
    material_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get price history for a material."""
    # Verify material exists
    result = await db.execute(select(Material).where(Material.id == material_id))
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Material {material_id} not found",
        )

    result = await db.execute(
        select(MaterialPrice)
        .where(MaterialPrice.material_id == material_id)
        .order_by(MaterialPrice.effective_from.desc())
    )
    prices = result.scalars().all()

    return [MaterialPriceResponse.model_validate(p) for p in prices]


@router.post("/{material_id}/price-history", response_model=MaterialPriceResponse)
async def add_price_history(
    material_id: UUID,
    price_in: MaterialPriceCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a price history entry for a material."""
    result = await db.execute(select(Material).where(Material.id == material_id))
    material = result.scalar_one_or_none()

    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Material {material_id} not found",
        )

    price_entry = MaterialPrice(
        material_id=material_id,
        **price_in.model_dump(),
    )
    db.add(price_entry)

    # Update current price if this is the most recent
    if price_in.effective_from <= datetime.utcnow():
        material.current_price = price_in.price
        material.last_price_update = datetime.utcnow()

    await db.commit()
    await db.refresh(price_entry)

    return MaterialPriceResponse.model_validate(price_entry)


@router.post("/import", response_model=list[BulkPriceUpdate])
async def preview_price_import(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Preview price updates from CSV/Excel file.

    Returns list of changes that would be applied.
    File must have columns: sku, price (or name, price)
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided",
        )

    # Read file
    content = await file.read()
    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(StringIO(content.decode("utf-8")))
        elif file.filename.endswith((".xlsx", ".xls")):
            df = pd.read_excel(content)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be CSV or Excel",
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error reading file: {e}",
        )

    # Normalize column names
    df.columns = df.columns.str.lower().str.strip()

    if "price" not in df.columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must have a 'price' column",
        )

    # Match materials
    updates = []
    for _, row in df.iterrows():
        # Find by SKU or name
        query = select(Material)
        if "sku" in df.columns and pd.notna(row.get("sku")):
            query = query.where(Material.sku == str(row["sku"]))
        elif "name" in df.columns and pd.notna(row.get("name")):
            query = query.where(Material.name.ilike(f"%{row['name']}%"))
        else:
            continue

        result = await db.execute(query)
        material = result.scalar_one_or_none()

        if material:
            new_price = Decimal(str(row["price"]))
            if new_price != material.current_price:
                change_percent = (
                    float((new_price - material.current_price) / material.current_price * 100)
                    if material.current_price
                    else 100.0
                )
                updates.append(
                    BulkPriceUpdate(
                        material_id=material.id,
                        material_name=material.name,
                        current_price=material.current_price,
                        new_price=new_price,
                        change_percent=change_percent,
                    )
                )

    return updates


@router.post("/import/confirm", status_code=status.HTTP_200_OK)
async def confirm_price_import(
    request: BulkPriceUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Confirm and apply bulk price updates."""
    updated_count = 0

    for update in request.updates:
        result = await db.execute(
            select(Material).where(Material.id == update.material_id)
        )
        material = result.scalar_one_or_none()

        if material:
            # Add price history
            price_entry = MaterialPrice(
                material_id=material.id,
                price=update.new_price,
                effective_from=datetime.utcnow(),
                source=request.source,
            )
            db.add(price_entry)

            # Update current price
            material.current_price = update.new_price
            material.last_price_update = datetime.utcnow()
            updated_count += 1

    await db.commit()

    return {"message": f"Updated {updated_count} material prices"}


@router.get("/export", response_class=StreamingResponse)
async def export_materials(
    category: Optional[MaterialCategory] = None,
    db: AsyncSession = Depends(get_db),
):
    """Export materials to CSV."""
    query = select(Material).where(Material.is_active == True)  # noqa: E712
    if category:
        query = query.where(Material.category == category)

    result = await db.execute(query.order_by(Material.name))
    materials = result.scalars().all()

    # Build CSV
    data = []
    for m in materials:
        data.append(
            {
                "sku": m.sku,
                "name": m.name,
                "category": m.category,
                "unit": m.unit,
                "price": float(m.current_price),
                "supplier_id": str(m.supplier_id) if m.supplier_id else "",
            }
        )

    df = pd.DataFrame(data)
    output = StringIO()
    df.to_csv(output, index=False)
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=materials.csv"},
    )
