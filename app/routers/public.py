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
    query = select(Job, Brand.name.label("brand_name"), Brand.slug.label("brand_slug")).join(Brand).where(Job.is_active == True)
    
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
    for job_obj, brand_name, brand_slug in rows:
        jobs.append(PublicJob(
            id=job_obj.id,
            slug=job_obj.slug,
            title=job_obj.title,
            brand_id=job_obj.brand_id,
            brand_name=brand_name,
            brand_slug=brand_slug
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

    # Questions come from the form the job uses (jobs.form_id); a job with no form returns an empty list
    questions = []
    if job.form_id is not None:
        query = select(JobQuestion).where(JobQuestion.form_id == job.form_id).order_by(JobQuestion.display_order.asc())
        result = await db.execute(query)
        questions = result.scalars().all()

    return PublicJobQuestionsResponse(
        data=[
            PublicJobQuestion(
                id=q.id,
                question_text=q.question_text,
                display_order=q.display_order,
                question_type=q.question_type,
                options=q.options,
            )
            for q in questions
        ]
    )


import os
import time
import json
from fastapi import Request, Form, UploadFile, File
from fastapi.responses import JSONResponse
import aiofiles

# Simple in-memory rate limiter (Security Rule 3)
RATE_LIMIT_CACHE = {}

def check_rate_limit(client_ip: str):
    now = time.time()
    # Clean up old entries (older than 1 hour)
    for ip, timestamps in list(RATE_LIMIT_CACHE.items()):
        RATE_LIMIT_CACHE[ip] = [ts for ts in timestamps if now - ts < 3600]
        if not RATE_LIMIT_CACHE[ip]:
            del RATE_LIMIT_CACHE[ip]
            
    recent_requests = RATE_LIMIT_CACHE.get(client_ip, [])
    if len(recent_requests) >= 3:
        raise HTTPException(status_code=429, detail="Too many applications submitted from this IP. Please try again later.")
    
    recent_requests.append(now)
    RATE_LIMIT_CACHE[client_ip] = recent_requests


@router.post("/apply", status_code=201)
async def submit_application(
    request: Request,
    job_id: UUID4 = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    answers: str = Form(default="[]"),
    terms_version: str = Form(...),
    consent_agreed: bool = Form(...),
    resume: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    client_ip = request.client.host if request.client else "unknown"
    check_rate_limit(client_ip)

    if not consent_agreed:
        raise HTTPException(status_code=400, detail="Consent to RA 10173 is required.")

    # 1. Validate File constraints (Security Rule 1)
    if resume.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    magic_bytes = await resume.read(4)
    if magic_bytes != b"%PDF":
        raise HTTPException(status_code=400, detail="Invalid PDF file format")
    
    # 2. File Size & Streaming to disk
    storage_path = os.environ.get("RESUME_STORAGE_PATH", "/data/resumes")
    os.makedirs(storage_path, mode=0o700, exist_ok=True)
    
    from uuid import uuid4
    app_id = uuid4()
    file_on_disk = os.path.join(storage_path, f"{app_id}.pdf")
    
    file_size = 4
    try:
        async with aiofiles.open(file_on_disk, 'wb') as f:
            await f.write(magic_bytes)
            while chunk := await resume.read(8192):
                file_size += len(chunk)
                if file_size > 5 * 1024 * 1024:
                    raise HTTPException(status_code=413, detail="File size exceeds 5MB limit")
                await f.write(chunk)
        os.chmod(file_on_disk, 0o600)
    except HTTPException:
        if os.path.exists(file_on_disk):
            os.remove(file_on_disk)
        raise
    
    # 3. Clean string inputs
    first_name = first_name.strip()
    last_name = last_name.strip()
    email = email.strip().lower()
    phone = phone.strip()
    
    try:
        parsed_answers = json.loads(answers)
    except json.JSONDecodeError:
        parsed_answers = []

    # 4. Matching Engine Logic
    job_query = select(Job).where(Job.id == job_id, Job.is_active == True)
    job = await db.scalar(job_query)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or inactive")

    questions_query = select(JobQuestion).where(JobQuestion.job_id == job_id).order_by(JobQuestion.display_order.asc())
    questions_result = await db.execute(questions_query)
    job_questions = {str(q.id): q for q in questions_result.scalars().all()}

    has_hard_fail_flag = False
    passed_count = 0
    total_questions = len(job_questions)
    answer_records = []

    from app.models import Applicant, Application, Answer, StatusCount
    
    for ans in parsed_answers:
        q_id = str(ans.get("question_id"))
        val = str(ans.get("answer", "")).strip()
        if q_id in job_questions:
            q_obj = job_questions[q_id]
            is_passed = (val.lower() == q_obj.expected_answer.lower())
            if is_passed:
                passed_count += 1
            elif q_obj.is_hard_requirement:
                has_hard_fail_flag = True
                
            answer_records.append(Answer(
                id=uuid4(),
                application_id=app_id,
                job_question_id=q_obj.id,
                applicant_answer=val,
                is_passed=is_passed
            ))

    score = int((passed_count / total_questions) * 100) if total_questions > 0 else 100
    
    # Status Evaluation
    if has_hard_fail_flag:
        final_status = "FAILED"
    elif score >= job.pass_threshold:
        final_status = "PASSED"
    elif score >= job.pooling_threshold:
        final_status = "POOLING"
    else:
        final_status = "FAILED"

    # 5. Database Transaction
    try:
        # Applicant check/create
        applicant_query = select(Applicant).where(Applicant.email == email)
        applicant = await db.scalar(applicant_query)
        if not applicant:
            applicant = Applicant(first_name=first_name, last_name=last_name, email=email, phone=phone)
            db.add(applicant)
            await db.flush()
        
        # Application create
        application = Application(
            id=app_id,
            applicant_id=applicant.id,
            job_id=job.id,
            terms_version=terms_version,
            consent_agreed=consent_agreed,
            resume_path=file_on_disk,
            resume_filename=resume.filename,
            resume_size_bytes=file_size,
            calculated_score=score,
            has_hard_fail_flag=has_hard_fail_flag,
            status=final_status
        )
        db.add(application)
        
        # Answers add
        for arec in answer_records:
            db.add(arec)

        # StatusCount Update (Rule 13.3)
        count_query = select(StatusCount).where(
            StatusCount.job_id == job.id, StatusCount.status == final_status
        ).with_for_update()
        status_count = await db.scalar(count_query)
        if status_count:
            status_count.count += 1
        else:
            db.add(StatusCount(job_id=job.id, status=final_status, count=1))
            
        await db.commit()
    except Exception as e:
        await db.rollback()
        if os.path.exists(file_on_disk):
            os.remove(file_on_disk)
        raise HTTPException(status_code=500, detail="Database transaction failed")
        
    return JSONResponse(
        status_code=201, 
        content={"message": "Application submitted successfully", "application_id": str(app_id)}
    )
