from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from pydantic import UUID4

from app.database import get_db
from app.models import Job, Brand, JobQuestion
from app.schemas import (
    PublicJob, PublicJobsResponse, 
    PublicJobQuestion, PublicJobQuestionsResponse
)

router = APIRouter()

@router.get("/jobs", response_model=PublicJobsResponse)
async def get_public_jobs(
    brand_id: Optional[UUID4] = Query(None, description="Filter by brand"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    # Base query for active jobs, joining brand to get the brand_name
    query = select(Job, Brand.name.label("brand_name")).join(Brand).where(Job.is_active == True)
    
    if brand_id:
        query = query.where(Job.brand_id == brand_id)
        
    # Count total for pagination (Rule 13.2)
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0
    
    # Apply keyset/offset pagination
    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    rows = result.all()
    
    jobs = []
    for job_obj, brand_name in rows:
        jobs.append(PublicJob(
            id=job_obj.id,
            title=job_obj.title,
            brand_id=job_obj.brand_id,
            brand_name=brand_name
        ))
        
    return PublicJobsResponse(data=jobs, total=total)

@router.get("/jobs/{job_id}/questions", response_model=PublicJobQuestionsResponse)
async def get_job_questions(
    job_id: UUID4,
    db: AsyncSession = Depends(get_db)
):
    # Verify job exists and is active
    job_query = select(Job).where(Job.id == job_id, Job.is_active == True)
    job = await db.scalar(job_query)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Fetch dynamic parameters/questions linked to this job
    query = select(JobQuestion).where(JobQuestion.job_id == job_id)
    result = await db.execute(query)
    questions = result.scalars().all()
    
    return PublicJobQuestionsResponse(
        data=[PublicJobQuestion(id=q.id, question_text=q.question_text) for q in questions]
    )
