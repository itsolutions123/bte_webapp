from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Optional
import re
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import Brand, Job, StatusCount, Parameter, Parameter, Form
from app.schemas import (
    SidebarMetadataResponse, SidebarBrandItem, SidebarFormItem, SidebarFormItem,
    AdminSummaryResponse, OverallTotals,
    AdminTallyResponse, AdminTallyItem, JobCounts,
    FormCreateRequest, FormResponse, FormArchiveResponse,
    FormListItem, FormListResponse,
)

router = APIRouter()

@router.get("/metadata/sidebar", response_model=SidebarMetadataResponse)
async def get_sidebar_metadata(db: AsyncSession = Depends(get_db)):
    brand_result = await db.execute(select(Brand))
    brands = brand_result.scalars().all()
    brand_items = [SidebarBrandItem(id=b.id, name=b.name, slug=b.slug, code=b.name[:3].upper()) for b in brands]

    form_result = await db.execute(
        select(Form)
        .where(Form.archived_at.is_(None))
        .order_by(func.lower(Form.name), Form.name)
    )
    forms = form_result.scalars().all()
    form_items = [SidebarFormItem(id=f.id, name=f.name, slug=f.slug) for f in forms]

    return SidebarMetadataResponse(brands=brand_items, forms=form_items)

@router.get("/dashboard/summary", response_model=AdminSummaryResponse)
async def get_dashboard_summary(
    date_from: Optional[str] = Query(None), 
    date_to: Optional[str] = Query(None), 
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(StatusCount.status, func.sum(StatusCount.count)).group_by(StatusCount.status))
    rows = result.all()
    
    totals = OverallTotals()
    total_processed = 0
    for status, count in rows:
        if status:
            s = status.upper()
            if s == "PASSED": totals.passed = count
            elif s == "FAILED": totals.failed = count
            elif s == "POOLING": totals.pooling = count
            elif s == "ENDORSED": totals.endorsed = count
            elif s == "HIRED": totals.hired = count
            total_processed += count
    totals.total_processed = total_processed
    
    return AdminSummaryResponse(overall_totals=totals, brand_summaries=[])

@router.get("/dashboard/tally", response_model=AdminTallyResponse)
async def get_dashboard_tally(brand_id: Optional[str] = Query(None), db: AsyncSession = Depends(get_db)):
    query = select(Job.id, Job.title, StatusCount.status, StatusCount.count).outerjoin(
        StatusCount, Job.id == StatusCount.job_id
    )
    if brand_id:
        query = query.where(Job.brand_id == brand_id)
        
    result = await db.execute(query)
    rows = result.all()
    
    job_dict = {}
    for job_id, title, status, count in rows:
        if job_id not in job_dict:
            job_dict[job_id] = {"title": title, "counts": JobCounts()}
        if status:
            s = status.upper()
            if hasattr(job_dict[job_id]["counts"], s):
                setattr(job_dict[job_id]["counts"], s, count)
                
    tally_items = [
        AdminTallyItem(job_id=jid, job_title=data["title"], counts=data["counts"])
        for jid, data in job_dict.items()
    ]

    return AdminTallyResponse(data=tally_items)

def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "form"

@router.post("/forms", response_model=FormResponse, status_code=status.HTTP_201_CREATED)
async def create_form(payload: FormCreateRequest, db: AsyncSession = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="name must not be empty")

    slug = _slugify(name)
    existing = await db.execute(select(Form).where(Form.slug == slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="slug already taken")

    form = Form(name=name, slug=slug)
    db.add(form)
    await db.commit()
    await db.refresh(form)

    return FormResponse(id=form.id, slug=form.slug, name=form.name)


@router.patch("/forms/{form_id}", response_model=FormResponse)
async def rename_form(form_id: str, payload: FormCreateRequest, db: AsyncSession = Depends(get_db)):
    try:
        form_uuid = uuid.UUID(form_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="form_id must be a valid UUID")

    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="name must not be empty")
    slug = _slugify(name)
    if not slug:
        raise HTTPException(status_code=422, detail="name must contain letters or numbers")

    result = await db.execute(select(Form).where(Form.id == form_uuid))
    form = result.scalar_one_or_none()
    if form is None:
        raise HTTPException(status_code=404, detail="form not found")
    if form.archived_at is not None:
        raise HTTPException(status_code=409, detail="form is archived and read-only")

    clash = await db.execute(
        select(Form.id).where(Form.slug == slug, Form.id != form_uuid)
    )
    if clash.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="slug already taken")

    form.name = name
    form.slug = slug
    await db.commit()
    await db.refresh(form)

    return FormResponse(id=form.id, slug=form.slug, name=form.name)


@router.post("/forms/{form_id}/archive", response_model=FormArchiveResponse)
async def archive_form(form_id: str, db: AsyncSession = Depends(get_db)):
    try:
        form_uuid = uuid.UUID(form_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="form_id must be a valid UUID")

    result = await db.execute(select(Form).where(Form.id == form_uuid))
    form = result.scalar_one_or_none()
    if form is None:
        raise HTTPException(status_code=404, detail="form not found")
    if form.archived_at is not None:
        raise HTTPException(status_code=409, detail="form is already archived")

    job_count_result = await db.execute(
        select(func.count()).select_from(Job).where(Job.form_id == form_uuid)
    )
    job_count = job_count_result.scalar_one()
    if job_count > 0:
        raise HTTPException(
            status_code=409,
            detail=f"{job_count} job(s) still use this form; detach them first",
        )

    form.archived_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(form)

    return FormArchiveResponse(
        id=form.id, slug=form.slug, name=form.name, archived_at=form.archived_at
    )


@router.get("/forms", response_model=FormListResponse)
async def list_forms(
    archived: bool = Query(False),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    if archived:
        flt = Form.archived_at.is_not(None)
        order = Form.archived_at.desc()
    else:
        flt = Form.archived_at.is_(None)
        order = Form.created_at.asc()

    total_result = await db.execute(select(func.count()).select_from(Form).where(flt))
    total = total_result.scalar_one()

    result = await db.execute(
        select(Form).where(flt).order_by(order).offset((page - 1) * limit).limit(limit)
    )
    forms = result.scalars().all()

    counts = {}
    if forms:
        count_result = await db.execute(
            select(Job.form_id, func.count())
            .where(Job.form_id.in_([f.id for f in forms]))
            .group_by(Job.form_id)
        )
        counts = {form_id: n for form_id, n in count_result.all()}

    items = [
        FormListItem(
            id=f.id,
            slug=f.slug,
            name=f.name,
            job_count=counts.get(f.id, 0),
            archived_at=f.archived_at,
        )
        for f in forms
    ]
    return FormListResponse(data=items, total=total)
