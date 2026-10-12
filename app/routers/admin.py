from fastapi import APIRouter, Depends, Query
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models import Brand, Job, StatusCount
from app.schemas import (
    SidebarMetadataResponse, SidebarBrandItem, 
    AdminSummaryResponse, OverallTotals, 
    AdminTallyResponse, AdminTallyItem, JobCounts
)

router = APIRouter()

@router.get("/metadata/sidebar", response_model=SidebarMetadataResponse)
async def get_sidebar_metadata(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Brand))
    brands = result.scalars().all()
    brand_items = [SidebarBrandItem(id=b.id, name=b.name, code=b.name[:3].upper()) for b in brands]
    return SidebarMetadataResponse(brands=brand_items, forms=[])

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
