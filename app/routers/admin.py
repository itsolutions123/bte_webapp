from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Optional
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import Brand, Job, StatusCount, Parameter, Parameter, Form
from app.schemas import (
    SidebarMetadataResponse, SidebarBrandItem, SidebarFormItem, SidebarFormItem,
    AdminSummaryResponse, OverallTotals,
    AdminTallyResponse, AdminTallyItem, JobCounts,
    FormCreateRequest, FormResponse,
)

router = APIRouter()

@router.get("/metadata/sidebar", response_model=SidebarMetadataResponse)
async def get_sidebar_metadata(db: AsyncSession = Depends(get_db)):
    brand_result = await db.execute(select(Brand))
    brands = brand_result.scalars().all()
    brand_items = [SidebarBrandItem(id=b.id, name=b.name, slug=b.slug, code=b.name[:3].upper()) for b in brands]

    param_result = await db.execute(select(Parameter))
    params = param_result.scalars().all()
    form_items = [SidebarFormItem(id=p.id, name=p.name, slug=p.slug) for p in params]

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
