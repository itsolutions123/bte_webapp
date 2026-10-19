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
    query = select(Job, Brand.name.label("brand_name"), Brand.slug.label("brand_slug")).join(Brand).where(
        Job.is_active == True,
        Job.archived_at.is_(None),
        Job.expires_at > func.now(),
    )
    
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
            description=job_obj.description,
            requirements=job_obj.requirements,
            location=job_obj.location,
            pay_information=job_obj.pay_information,
            job_type=job_obj.job_type,
            brand_id=job_obj.brand_id,
            brand_name=brand_name,
            brand_slug=brand_slug
        ))
        
    return PublicJobsResponse(data=jobs, total=total)

@router.get("/jobs/{job_id}", response_model=PublicJob)
async def get_public_job(
    job_id: UUID4,
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Job, Brand.name.label("brand_name"), Brand.slug.label("brand_slug"))
        .join(Brand)
        .where(
            Job.id == job_id,
            Job.is_active == True,
            Job.archived_at.is_(None),
            Job.expires_at > func.now(),
        )
    )
    row = (await db.execute(query)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job_obj, brand_name, brand_slug = row
    return PublicJob(
        id=job_obj.id,
        slug=job_obj.slug,
        title=job_obj.title,
        description=job_obj.description,
        requirements=job_obj.requirements,
        location=job_obj.location,
        pay_information=job_obj.pay_information,
        job_type=job_obj.job_type,
        brand_id=job_obj.brand_id,
        brand_name=brand_name,
        brand_slug=brand_slug
    )

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


import logging
from datetime import date
from uuid import uuid4
from app.models import Applicant, Application, Answer, StatusCount

logger = logging.getLogger(__name__)


@router.post("/apply", status_code=201)
async def submit_application(
    request: Request,
    job_id: UUID4 = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    address: str = Form(...),
    gender: str = Form(...),
    date_of_birth: str = Form(...),
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

    # 1. Personal fields (contract: fixed, required on every job)
    first_name = first_name.strip()
    last_name = last_name.strip()
    email = email.strip().lower()
    phone = phone.strip()
    address = address.strip()
    gender = gender.strip()
    if not all([first_name, last_name, email, phone, address, gender]):
        raise HTTPException(status_code=422, detail="All personal fields are required.")

    dob_text = date_of_birth.strip()
    try:
        if len(dob_text) != 10:
            raise ValueError
        dob = date.fromisoformat(dob_text)
    except ValueError:
        raise HTTPException(status_code=422, detail="date_of_birth must be a valid YYYY-MM-DD date.")
    if dob >= date.today():
        raise HTTPException(status_code=422, detail="date_of_birth must be a past date.")

    # 2. Job: same visibility rule as GET /api/v1/public/jobs/{job_id}
    job = await db.scalar(
        select(Job).where(
            Job.id == job_id,
            Job.is_active == True,
            Job.archived_at.is_(None),
            Job.expires_at > func.now(),
        )
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.form_id is None:
        raise HTTPException(status_code=409, detail="This job has no application form.")

    # 3. Questions come from the job's form (jobs.form_id)
    q_result = await db.execute(
        select(JobQuestion).where(JobQuestion.form_id == job.form_id).order_by(JobQuestion.display_order.asc())
    )
    questions = {str(q.id): q for q in q_result.scalars().all()}

    # 4. Validate answers BEFORE anything is written to disk
    try:
        parsed_answers = json.loads(answers)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="answers must be valid JSON.")
    if not isinstance(parsed_answers, list):
        raise HTTPException(status_code=422, detail="answers must be a JSON array.")

    given = {}
    for item in parsed_answers:
        if not isinstance(item, dict):
            raise HTTPException(status_code=422, detail="Each answer must be an object.")
        q_id = str(item.get("question_id", ""))
        if q_id not in questions:
            raise HTTPException(status_code=422, detail="Unknown question id.")
        if q_id in given:
            raise HTTPException(status_code=422, detail="Duplicate answer for a question.")
        raw = item.get("answer")
        given[q_id] = "" if raw is None else str(raw).strip()

    answer_rows = []
    for q_id, q in questions.items():
        val = given.get(q_id, "")
        if q.question_type in ("YES_NO", "MULTIPLE_CHOICE"):
            if not val:
                raise HTTPException(status_code=422, detail="Every question must be answered.")
            if q.question_type == "YES_NO":
                val = val.upper()
                if val not in ("YES", "NO"):
                    raise HTTPException(status_code=422, detail="Invalid answer value.")
            else:
                option_ids = {str(o.get("id")) for o in (q.options or []) if isinstance(o, dict)}
                if val not in option_ids:
                    raise HTTPException(status_code=422, detail="Unknown option id.")
        elif not val:
            continue
        answer_rows.append((q.id, val))

    # 5. Validate the PDF, then stream it to disk (Security Rule 1)
    if resume.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    magic_bytes = await resume.read(4)
    if magic_bytes != b"%PDF":
        raise HTTPException(status_code=400, detail="Invalid PDF file format")

    storage_path = os.environ.get("RESUME_STORAGE_PATH", "/data/resumes")
    os.makedirs(storage_path, mode=0o700, exist_ok=True)

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
    except Exception:
        if os.path.exists(file_on_disk):
            os.remove(file_on_disk)
        raise

    # 6. One transaction: applicant, application, raw answers, NEW counter (no scoring in this slice)
    try:
        applicant = await db.scalar(select(Applicant).where(Applicant.email == email))
        if applicant:
            applicant.first_name = first_name
            applicant.last_name = last_name
            applicant.phone = phone
            applicant.address = address
            applicant.gender = gender
            applicant.date_of_birth = dob
        else:
            applicant = Applicant(
                first_name=first_name, last_name=last_name, email=email, phone=phone,
                address=address, gender=gender, date_of_birth=dob
            )
            db.add(applicant)
        await db.flush()

        db.add(Application(
            id=app_id,
            applicant_id=applicant.id,
            job_id=job.id,
            terms_version=terms_version,
            consent_agreed=consent_agreed,
            resume_path=file_on_disk,
            resume_filename=resume.filename or "resume.pdf",
            resume_size_bytes=file_size,
            calculated_score=None,
            has_hard_fail_flag=False,
            status="NEW"
        ))
        await db.flush()

        for question_uuid, val in answer_rows:
            db.add(Answer(
                id=uuid4(),
                application_id=app_id,
                job_question_id=question_uuid,
                applicant_answer=val,
                is_passed=None
            ))

        # status_counts increment (Rule 18.3: counter, never a recount)
        status_count = await db.scalar(
            select(StatusCount)
            .where(StatusCount.job_id == job.id, StatusCount.status == "NEW")
            .with_for_update()
        )
        if status_count:
            status_count.count += 1
        else:
            db.add(StatusCount(job_id=job.id, status="NEW", count=1))

        await db.commit()
    except Exception as e:
        await db.rollback()
        if os.path.exists(file_on_disk):
            os.remove(file_on_disk)
        logger.error("Application submit failed: %s", type(e).__name__)
        raise HTTPException(status_code=500, detail="Database transaction failed")

    return JSONResponse(
        status_code=201,
        content={"message": "Application submitted successfully", "application_id": str(app_id)}
    )
