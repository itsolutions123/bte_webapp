from fastapi import APIRouter, Depends, Query, HTTPException, status
from typing import Optional
import re
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, literal, update

from app.database import get_db
from app.timeutil import to_app_tz, APP_TIMEZONE
from app.html_clean import clean_rich_text
from app.models import Application, Applicant
from app.models import Brand, Job, StatusCount, Parameter, Parameter, Form, JobQuestion, Answer, Answer
from app.schemas import (
    SidebarMetadataResponse, SidebarBrandItem, SidebarFormItem, SidebarFormItem,
    AdminSummaryResponse, OverallTotals,
    AdminTallyResponse, AdminTallyItem, JobCounts,
    BrandCreateRequest, BrandResponse,
    JobCreateRequest, JobUpdateRequest, JobResponse, BrandJobItem, BrandJobsResponse,
    FormCreateRequest, FormResponse, FormArchiveResponse,
    BrandArchiveResponse,
    FormListItem, FormListResponse,
    QuestionCreateRequest, QuestionResponse, QuestionUpdateRequest,
    JobSummaryItem, FormDetailResponse,
    AdminApplicationListItem, AdminApplicationListResponse,
    AdminApplicantDetail, AdminAnswerDetail, AdminApplicationDetailResponse,
)

router = APIRouter()

# Brand page job search (docs/API_CONTRACT.md, Search (q)). Threshold confirmed by the user 2026-10-14;
# revisit once there are real job titles.
JOB_SEARCH_SIMILARITY_THRESHOLD = 0.5
JOB_SEARCH_MAX_LENGTH = 100

@router.get("/metadata/sidebar", response_model=SidebarMetadataResponse)
async def get_sidebar_metadata(db: AsyncSession = Depends(get_db)):
    brand_result = await db.execute(
        select(Brand)
        .where(Brand.archived_at.is_(None))
        .order_by(func.lower(Brand.name), Brand.name)
    )
    brands = brand_result.scalars().all()
    brand_items = [SidebarBrandItem(id=b.id, name=b.name, slug=b.slug) for b in brands]

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
            if s == "NEW": totals.new = count
            elif s == "PASSED": totals.passed = count
            elif s == "FAILED": totals.failed = count
            elif s == "POOLING": totals.pooling = count
            elif s == "ENDORSED": totals.endorsed = count
            elif s == "HIRED": totals.hired = count
            if s != "NEW":
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

@router.post("/brands", response_model=BrandResponse, status_code=status.HTTP_201_CREATED)
async def create_brand(payload: BrandCreateRequest, db: AsyncSession = Depends(get_db)):
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="name must not be empty")

    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        raise HTTPException(status_code=422, detail="name must contain at least one letter or number")

    existing = await db.execute(
        select(Brand).where((func.lower(Brand.name) == name.lower()) | (Brand.slug == slug)).limit(1)
    )
    if existing.scalars().first():
        raise HTTPException(status_code=409, detail="a brand with this name already exists")

    brand = Brand(name=name, slug=slug)
    db.add(brand)
    await db.commit()
    await db.refresh(brand)

    return BrandResponse(id=brand.id, name=brand.name, slug=brand.slug)

JOB_TYPES = ("Full-time", "Part-time", "Onsite")  # contract: "Job details fields"
JOB_DETAIL_MAX_LENGTH = 150


def clean_job_detail_text(value: str | None, field: str) -> str | None:
    value = (value or "").strip()
    if not value:
        return None
    if len(value) > JOB_DETAIL_MAX_LENGTH:
        raise HTTPException(status_code=422, detail=f"{field} must be at most {JOB_DETAIL_MAX_LENGTH} characters")
    return value


def clean_job_type(value: str | None) -> str | None:
    value = (value or "").strip()
    if not value:
        return None
    if value not in JOB_TYPES:
        raise HTTPException(status_code=422, detail="job_type must be one of: " + ", ".join(JOB_TYPES))
    return value


@router.post("/brands/{brand_id}/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(brand_id: uuid.UUID, payload: JobCreateRequest, db: AsyncSession = Depends(get_db)):
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="title must not be empty")

    # Label only: not unique, never used for lookups (the id is the job identifier).
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not slug:
        raise HTTPException(status_code=422, detail="title must contain at least one letter or number")

    brand = await db.get(Brand, brand_id)
    if brand is None:
        raise HTTPException(status_code=404, detail="brand not found")

    description = clean_rich_text((payload.description or "").strip() or None)
    requirements = clean_rich_text((payload.requirements or "").strip() or None)
    location = clean_job_detail_text(payload.location, "location")
    pay_information = clean_job_detail_text(payload.pay_information, "pay_information")
    job_type = clean_job_type(payload.job_type)

    job = Job(
        brand_id=brand.id,
        title=title,
        slug=slug,
        description=description,
        requirements=requirements,
        location=location,
        pay_information=pay_information,
        job_type=job_type,
        is_active=payload.is_active,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    return JobResponse(
        id=job.id,
        brand_id=job.brand_id,
        title=job.title,
        slug=job.slug,
        description=job.description,
        requirements=job.requirements,
        is_active=job.is_active,
        form_id=job.form_id,
        location=job.location,
        pay_information=job.pay_information,
        job_type=job.job_type,
        created_at=to_app_tz(job.created_at),
        expires_at=to_app_tz(job.expires_at),
        archived_at=to_app_tz(job.archived_at) if job.archived_at else None,
        is_expired=job.expires_at <= datetime.now(timezone.utc),
    )

@router.get("/brands/{brand_id}/jobs/{job_id}", response_model=JobResponse)
async def get_brand_job(brand_id: uuid.UUID, job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    brand = await db.get(Brand, brand_id)
    if brand is None:
        raise HTTPException(status_code=404, detail="brand not found")

    job = await db.get(Job, job_id)
    if job is None or job.brand_id != brand.id:
        raise HTTPException(status_code=404, detail="job not found")

    return JobResponse(
        id=job.id,
        brand_id=job.brand_id,
        title=job.title,
        slug=job.slug,
        description=job.description,
        requirements=job.requirements,
        is_active=bool(job.is_active),
        form_id=job.form_id,
        location=job.location,
        pay_information=job.pay_information,
        job_type=job.job_type,
        created_at=to_app_tz(job.created_at),
        expires_at=to_app_tz(job.expires_at),
        archived_at=to_app_tz(job.archived_at) if job.archived_at else None,
        is_expired=job.expires_at <= datetime.now(timezone.utc),
    )

@router.patch("/brands/{brand_id}/jobs/{job_id}", response_model=JobResponse)
async def update_job(brand_id: uuid.UUID, job_id: uuid.UUID, payload: JobUpdateRequest, db: AsyncSession = Depends(get_db)):
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="title must not be empty")

    # Label only: not unique, never used for lookups (the id is the job identifier).
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not slug:
        raise HTTPException(status_code=422, detail="title must contain at least one letter or number")

    brand = await db.get(Brand, brand_id)
    if brand is None:
        raise HTTPException(status_code=404, detail="brand not found")

    job = await db.get(Job, job_id)
    if job is None or job.brand_id != brand.id:
        raise HTTPException(status_code=404, detail="job not found")

    if job.archived_at is not None:
        raise HTTPException(status_code=409, detail="job is archived")

    job.title = title
    job.slug = slug
    job.description = clean_rich_text((payload.description or "").strip() or None)
    job.requirements = clean_rich_text((payload.requirements or "").strip() or None)
    job.location = clean_job_detail_text(payload.location, "location")
    job.pay_information = clean_job_detail_text(payload.pay_information, "pay_information")
    job.job_type = clean_job_type(payload.job_type)
    job.is_active = payload.is_active
    await db.commit()
    await db.refresh(job)

    return JobResponse(
        id=job.id,
        brand_id=job.brand_id,
        title=job.title,
        slug=job.slug,
        description=job.description,
        requirements=job.requirements,
        is_active=bool(job.is_active),
        form_id=job.form_id,
        location=job.location,
        pay_information=job.pay_information,
        job_type=job.job_type,
        created_at=to_app_tz(job.created_at),
        expires_at=to_app_tz(job.expires_at),
        archived_at=to_app_tz(job.archived_at) if job.archived_at else None,
        is_expired=job.expires_at <= datetime.now(timezone.utc),
    )


@router.post("/brands/{brand_id}/jobs/{job_id}/archive", response_model=JobResponse)
async def archive_job(brand_id: uuid.UUID, job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    brand = await db.get(Brand, brand_id)
    if brand is None:
        raise HTTPException(status_code=404, detail="brand not found")

    job = await db.get(Job, job_id)
    if job is None or job.brand_id != brand.id:
        raise HTTPException(status_code=404, detail="job not found")

    if job.archived_at is not None:
        raise HTTPException(status_code=409, detail="job is already archived")

    # Only archived_at changes: is_active, expires_at, form_id and created_at are untouched.
    job.archived_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(job)

    return JobResponse(
        id=job.id,
        brand_id=job.brand_id,
        title=job.title,
        slug=job.slug,
        description=job.description,
        requirements=job.requirements,
        is_active=bool(job.is_active),
        form_id=job.form_id,
        location=job.location,
        pay_information=job.pay_information,
        job_type=job.job_type,
        created_at=to_app_tz(job.created_at),
        expires_at=to_app_tz(job.expires_at),
        archived_at=to_app_tz(job.archived_at) if job.archived_at else None,
        is_expired=job.expires_at <= datetime.now(timezone.utc),
    )


@router.post("/brands/{brand_id}/archive", response_model=BrandArchiveResponse)
async def archive_brand(brand_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    brand = await db.get(Brand, brand_id)
    if brand is None:
        raise HTTPException(status_code=404, detail="brand not found")

    if brand.archived_at is not None:
        raise HTTPException(status_code=409, detail="brand is already archived")

    now = datetime.now(timezone.utc)

    # Cascade: every non-archived job under this brand is archived in the same transaction.
    result = await db.execute(
        update(Job)
        .where(Job.brand_id == brand.id, Job.archived_at.is_(None))
        .values(archived_at=now)
    )
    jobs_archived = result.rowcount or 0

    brand.archived_at = now
    await db.commit()
    await db.refresh(brand)

    return BrandArchiveResponse(
        id=brand.id,
        slug=brand.slug,
        name=brand.name,
        archived_at=to_app_tz(brand.archived_at),
        jobs_archived=jobs_archived,
    )

@router.get("/applications", response_model=AdminApplicationListResponse)
async def list_applications(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    # First slice (docs/API_CONTRACT.md): page and limit only; job_id, form_id, status, search come later.
    total_result = await db.execute(select(func.count()).select_from(Application))
    total = total_result.scalar_one()

    result = await db.execute(
        select(Application, Applicant.first_name, Applicant.last_name, Job.title)
        .join(Applicant, Applicant.id == Application.applicant_id)
        .join(Job, Job.id == Application.job_id)
        .order_by(Application.created_at.desc().nulls_last(), Application.id)
        .offset((page - 1) * limit)
        .limit(limit)
    )

    items = [
        AdminApplicationListItem(
            id=app_row.id,
            applicant_name=f"{first} {last}".strip(),
            job_title=title,
            score=app_row.calculated_score,
            status=app_row.status,
            has_hard_fail_flag=bool(app_row.has_hard_fail_flag),
            created_at=to_app_tz(app_row.created_at),
        )
        for app_row, first, last, title in result.all()
    ]
    return AdminApplicationListResponse(data=items, total=total)


@router.get("/applications/{application_id}", response_model=AdminApplicationDetailResponse)
async def get_application_detail(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    # First slice (docs/API_CONTRACT.md): id, status, score, applicant fields, answers.
    row = (
        await db.execute(
            select(Application, Applicant, Job.title)
            .join(Applicant, Applicant.id == Application.applicant_id)
            .join(Job, Job.id == Application.job_id)
            .where(Application.id == application_id)
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="application not found")
    application, applicant, job_title = row

    age = None
    if applicant.date_of_birth is not None:
        today = datetime.now(APP_TIMEZONE).date()
        dob = applicant.date_of_birth
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    answer_rows = (
        await db.execute(
            select(Answer, JobQuestion)
            .join(JobQuestion, JobQuestion.id == Answer.job_question_id)
            .where(Answer.application_id == application_id)
            .order_by(JobQuestion.display_order, Answer.id)
        )
    ).all()

    answers = []
    for ans, q in answer_rows:
        value = ans.applicant_answer
        if q.question_type == "MULTIPLE_CHOICE":
            for o in (q.options or []):
                if isinstance(o, dict) and str(o.get("id")) == value:
                    value = str(o.get("text", value))
                    break
        answers.append(
            AdminAnswerDetail(
                question=q.question_text,
                question_type=q.question_type,
                applicant_answer=value,
                is_passed=ans.is_passed,
            )
        )

    return AdminApplicationDetailResponse(
        id=application.id,
        applicant=AdminApplicantDetail(
            name=f"{applicant.first_name} {applicant.last_name}".strip(),
            email=applicant.email,
            phone=applicant.phone,
            gender=applicant.gender,
            address=applicant.address,
            age=age,
        ),
        job_title=job_title,
        score=application.calculated_score,
        status=application.status,
        answers=answers,
    )


@router.get("/brands/{brand_id}/jobs", response_model=BrandJobsResponse)
async def list_brand_jobs(
    brand_id: uuid.UUID,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    q: Optional[str] = Query(None, max_length=JOB_SEARCH_MAX_LENGTH),
    db: AsyncSession = Depends(get_db),
):
    brand = await db.get(Brand, brand_id)
    if brand is None:
        raise HTTPException(status_code=404, detail="brand not found")

    flt = [Job.brand_id == brand_id, Job.archived_at.is_(None)]
    term = (q or "").strip()
    if term:
        # is_local=true: applies to this transaction only (already open from db.get above),
        # so it covers the count and select below and cannot leak to another pooled request.
        await db.execute(
            select(func.set_config("pg_trgm.word_similarity_threshold", str(JOB_SEARCH_SIMILARITY_THRESHOLD), True))
        )
        escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        flt.append(
            or_(
                Job.title.ilike("%" + escaped + "%", escape="\\"),
                literal(term).op("<%")(Job.title),
            )
        )

    total_result = await db.execute(
        select(func.count()).select_from(Job).where(*flt)
    )
    total = total_result.scalar_one()

    result = await db.execute(
        select(Job)
        .where(*flt)
        .order_by(Job.created_at.desc().nulls_last(), Job.id)
        .offset((page - 1) * limit)
        .limit(limit)
    )
    jobs = result.scalars().all()

    items = [
        BrandJobItem(
            id=j.id,
            title=j.title,
            is_active=bool(j.is_active),
            created_at=to_app_tz(j.created_at),
        )
        for j in jobs
    ]
    return BrandJobsResponse(data=items, total=total)


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


@router.get("/forms/{form_id}", response_model=FormDetailResponse)
async def get_form_detail(form_id: str, db: AsyncSession = Depends(get_db)):
    try:
        form_uuid = uuid.UUID(form_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="form_id must be a valid UUID")

    result = await db.execute(select(Form).where(Form.id == form_uuid))
    form = result.scalar_one_or_none()
    if form is None:
        raise HTTPException(status_code=404, detail="form not found")

    jobs_result = await db.execute(
        select(Job, Brand.name)
        .join(Brand, Job.brand_id == Brand.id)
        .where(Job.form_id == form_uuid)
    )
    jobs = [
        JobSummaryItem(id=j.id, slug=j.slug, title=j.title, brand_name=brand_name)
        for j, brand_name in jobs_result.all()
    ]

    questions_result = await db.execute(
        select(JobQuestion)
        .where(JobQuestion.form_id == form_uuid)
        .order_by(JobQuestion.display_order)
    )
    questions = [
        QuestionResponse(
            id=q.id,
            display_order=q.display_order,
            question_type=q.question_type,
            question_text=q.question_text,
            options=q.options,
            is_hard_requirement=q.is_hard_requirement,
            answer_points=[],  # answer_points table does not exist yet (SCHEMA.md held migration)
        )
        for q in questions_result.scalars().all()
    ]

    return FormDetailResponse(id=form.id, slug=form.slug, name=form.name, jobs=jobs, questions=questions)


@router.put("/forms/{form_id}/jobs/{job_id}")
async def attach_job_to_form(form_id: str, job_id: str, db: AsyncSession = Depends(get_db)):
    try:
        form_uuid = uuid.UUID(form_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="form_id must be a valid UUID")
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="job_id must be a valid UUID")

    form = await db.scalar(select(Form).where(Form.id == form_uuid))
    if form is None:
        raise HTTPException(status_code=404, detail="form not found")

    job = await db.scalar(select(Job).where(Job.id == job_uuid).with_for_update())
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    if job.form_id is not None and job.form_id != form_uuid:
        raise HTTPException(status_code=409, detail="job already uses a different form; detach it first")

    job.form_id = form_uuid
    await db.commit()
    return {"message": "Job attached"}


QUESTION_TYPES = {"YES_NO", "MULTIPLE_CHOICE", "OPEN_ENDED"}


@router.post("/forms/{form_id}/questions", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
async def create_question(form_id: str, payload: QuestionCreateRequest, db: AsyncSession = Depends(get_db)):
    try:
        form_uuid = uuid.UUID(form_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="form_id must be a valid UUID")

    text = payload.question_text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="question_text must not be empty")

    qtype = payload.question_type
    if qtype not in QUESTION_TYPES:
        raise HTTPException(status_code=422, detail="question_type must be YES_NO, MULTIPLE_CHOICE or OPEN_ENDED")

    options = None
    if payload.options is not None:
        options = [o.strip() for o in payload.options]
        if any(not o for o in options):
            raise HTTPException(status_code=422, detail="option labels must not be empty")

    if qtype == "YES_NO":
        if options is not None:
            if len(options) != 2:
                raise HTTPException(status_code=422, detail="YES_NO options must be exactly 2 labels")
            if options[0].lower() == options[1].lower():
                raise HTTPException(status_code=422, detail="the two YES_NO labels must be different")
    elif qtype == "MULTIPLE_CHOICE":
        if options is None or len(options) < 3:
            raise HTTPException(status_code=422, detail="MULTIPLE_CHOICE requires at least 3 options")
        if len(set(o.lower() for o in options)) != len(options):
            raise HTTPException(status_code=422, detail="MULTIPLE_CHOICE options must be distinct")
    else:
        if options is not None:
            raise HTTPException(status_code=422, detail="OPEN_ENDED takes no options")

    if payload.answer_points:
        raise HTTPException(status_code=422, detail="answer points are not supported yet")
    if payload.is_hard_requirement:
        raise HTTPException(status_code=422, detail="is_hard_requirement needs answer points, which are not supported yet")

    result = await db.execute(select(Form).where(Form.id == form_uuid))
    form = result.scalar_one_or_none()
    if form is None:
        raise HTTPException(status_code=404, detail="form not found")
    if form.archived_at is not None:
        raise HTTPException(status_code=409, detail="form is archived and read-only")

    max_result = await db.execute(
        select(func.coalesce(func.max(JobQuestion.display_order), 0)).where(JobQuestion.form_id == form_uuid)
    )
    next_order = max_result.scalar_one() + 1

    stored_options = options
    if qtype == "MULTIPLE_CHOICE" and options is not None:
        stored_options = [{"id": uuid.uuid4().hex, "text": o} for o in options]

    question = JobQuestion(
        form_id=form_uuid,
        question_type=qtype,
        question_text=text,
        options=stored_options,
        is_hard_requirement=False,
        display_order=next_order,
    )
    db.add(question)
    await db.commit()
    await db.refresh(question)

    return QuestionResponse(
        id=question.id,
        display_order=question.display_order,
        question_type=question.question_type,
        question_text=question.question_text,
        options=question.options,
        is_hard_requirement=bool(question.is_hard_requirement),
        answer_points=[],
    )


@router.patch("/forms/{form_id}/questions/{question_id}", response_model=QuestionResponse)
async def update_question(form_id: str, question_id: str, payload: QuestionUpdateRequest, db: AsyncSession = Depends(get_db)):
    try:
        form_uuid = uuid.UUID(form_id)
        question_uuid = uuid.UUID(question_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="form_id and question_id must be valid UUIDs")

    result = await db.execute(select(Form).where(Form.id == form_uuid))
    form = result.scalar_one_or_none()
    if form is None:
        raise HTTPException(status_code=404, detail="form not found")
    if form.archived_at is not None:
        raise HTTPException(status_code=409, detail="form is archived and read-only")

    q_result = await db.execute(
        select(JobQuestion).where(JobQuestion.id == question_uuid, JobQuestion.form_id == form_uuid)
    )
    question = q_result.scalar_one_or_none()
    if question is None:
        raise HTTPException(status_code=404, detail="question not found")

    if payload.answer_points:
        raise HTTPException(status_code=422, detail="answer points are not supported yet")
    if payload.is_hard_requirement:
        raise HTTPException(status_code=422, detail="is_hard_requirement needs answer points, which are not supported yet")

    if payload.question_text is not None:
        text = payload.question_text.strip()
        if not text:
            raise HTTPException(status_code=422, detail="question_text must not be empty")
        question.question_text = text

    if payload.options is not None:
        qtype = question.question_type
        if qtype == "YES_NO":
            options = [o.strip() for o in payload.options]
            if any(not o for o in options):
                raise HTTPException(status_code=422, detail="option labels must not be empty")
            if len(options) != 2:
                raise HTTPException(status_code=422, detail="YES_NO options must be exactly 2 labels")
            if options[0].lower() == options[1].lower():
                raise HTTPException(status_code=422, detail="the two YES_NO labels must be different")
            question.options = options
        elif qtype == "MULTIPLE_CHOICE":
            existing_ids = {o["id"] for o in (question.options or [])}
            new_options = []
            seen_ids = set()
            for item in payload.options:
                if not isinstance(item, dict) or "text" not in item:
                    raise HTTPException(status_code=422, detail="MULTIPLE_CHOICE options must be objects with a text field")
                opt_text = str(item["text"]).strip()
                if not opt_text:
                    raise HTTPException(status_code=422, detail="option labels must not be empty")
                opt_id = item.get("id")
                if opt_id is not None:
                    opt_id = str(opt_id)
                    if opt_id not in existing_ids:
                        raise HTTPException(status_code=422, detail=f"unknown option id: {opt_id}")
                    if opt_id in seen_ids:
                        raise HTTPException(status_code=422, detail=f"duplicate option id in request: {opt_id}")
                    seen_ids.add(opt_id)
                else:
                    opt_id = uuid.uuid4().hex
                new_options.append({"id": opt_id, "text": opt_text})
            if len(new_options) < 3:
                raise HTTPException(status_code=422, detail="MULTIPLE_CHOICE requires at least 3 options")
            if len(set(o["text"].lower() for o in new_options)) != len(new_options):
                raise HTTPException(status_code=422, detail="MULTIPLE_CHOICE options must be distinct")
            # NOTE: once the answer_points table exists, any answer_points rows referencing an
            # option id removed here (present in existing_ids but not in new_options) must be
            # deleted in the same transaction. Dormant for now -- answer_points is not live yet.
            question.options = new_options
        else:
            raise HTTPException(status_code=422, detail="OPEN_ENDED takes no options")

    await db.commit()
    await db.refresh(question)

    return QuestionResponse(
        id=question.id,
        display_order=question.display_order,
        question_type=question.question_type,
        question_text=question.question_text,
        options=question.options,
        is_hard_requirement=bool(question.is_hard_requirement),
        answer_points=[],
    )


@router.delete("/forms/{form_id}/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(form_id: str, question_id: str, db: AsyncSession = Depends(get_db)):
    try:
        form_uuid = uuid.UUID(form_id)
        question_uuid = uuid.UUID(question_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="form_id and question_id must be valid UUIDs")

    result = await db.execute(select(Form).where(Form.id == form_uuid))
    form = result.scalar_one_or_none()
    if form is None:
        raise HTTPException(status_code=404, detail="form not found")

    q_result = await db.execute(
        select(JobQuestion).where(JobQuestion.id == question_uuid, JobQuestion.form_id == form_uuid)
    )
    question = q_result.scalar_one_or_none()
    if question is None:
        raise HTTPException(status_code=404, detail="question not found")

    answer_check = await db.execute(
        select(Answer.id).where(Answer.job_question_id == question_uuid).limit(1)
    )
    if answer_check.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="question already has applicant answers")

    await db.delete(question)
    await db.commit()
    return None
