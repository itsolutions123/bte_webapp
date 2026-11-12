"""Admin MRF endpoints (docs/API_CONTRACT.md, /api/v1/admin/mrf). Mounted in app/main.py with the session check.

Summary, users list and approve, plus the forms endpoints (list, create, get one, update). Roles: SUPERADMIN and MANAGER (decided by the user 2026-11-10); RECRUITER gets 403."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import MrfForm, MrfFormQuestion, MrfUser, User
from app.mrf_lists import MRF_FORM_NAME_MAX_LENGTH, MRF_FORM_STATUS_ACTIVE, MRF_FORM_STATUS_DRAFT, MRF_FORM_STATUSES
from app.roles import ROLE_MANAGER, ROLE_SUPERADMIN
from app.routers.auth import require_roles
from app.schemas import (
    MrfFormCreate,
    MrfFormCreated,
    MrfFormDetail,
    MrfFormListItem,
    MrfFormQuestionItem,
    MrfFormListResponse,
    MrfFormUpdate,
    MrfUserListItem,
    MrfUserListResponse,
)
from app.timeutil import to_app_tz

router = APIRouter()

STATUS_PENDING = "pending"  # same value as the MrfUser.status default
STATUS_APPROVED = "approved"
USER_STATUSES = (STATUS_PENDING, STATUS_APPROVED)

# Users list limits and sort names (docs/API_CONTRACT.md, GET /api/v1/admin/mrf/users, decided by the user 2026-11-10).
MRF_USERS_DEFAULT_PAGE_SIZE = 10
MRF_USERS_MAX_PAGE_SIZE = 50
MRF_USERS_SEARCH_MAX_LENGTH = 100

# Forms list limits and messages (docs/API_CONTRACT.md, GET /api/v1/admin/mrf/forms, decided by the user 2026-11-12, part 43, option A).
MRF_FORMS_DEFAULT_PAGE_SIZE = 10
MRF_FORMS_MAX_PAGE_SIZE = 50
MRF_FORM_STATUS_INVALID = "status must be ACTIVE or DRAFT"

# Create form messages (docs/API_CONTRACT.md, POST /api/v1/admin/mrf/forms, decided by the user 2026-11-12, option A).
MRF_FORM_NAME_REQUIRED = "Form name is required."
MRF_FORM_NAME_TOO_LONG = f"Form name must be {MRF_FORM_NAME_MAX_LENGTH} characters or fewer."
MRF_FORM_NAME_TAKEN = "A form with this name already exists."

# Get one form message (docs/API_CONTRACT.md, GET /api/v1/admin/mrf/forms/{form_id}, decided by the user 2026-11-12, part 47, (h) option A).
MRF_FORM_NOT_FOUND = "Form not found."

# Update form messages (docs/API_CONTRACT.md, PATCH /api/v1/admin/mrf/forms/{form_id}, decided by the user 2026-11-12, part 48, (r) and (s), option A each).
MRF_FORM_UPDATE_EMPTY = "Send a name or a status to update."
MRF_FORM_NEEDS_QUESTION = "Add at least one question before setting this form to Active."
SORT_NEWEST = "newest"
SORT_FIRST_NAME_ASC = "first_name_asc"
SORT_FIRST_NAME_DESC = "first_name_desc"
USER_SORTS = (SORT_NEWEST, SORT_FIRST_NAME_ASC, SORT_FIRST_NAME_DESC)

# Approve error messages (docs/API_CONTRACT.md, POST /api/v1/admin/mrf/users/{user_id}/approve, decided by the user 2026-11-11).
MRF_USER_NOT_FOUND = "Account not found."
MRF_USER_ALREADY_APPROVED = "Account is already approved."


@router.get("/mrf/summary", dependencies=[Depends(require_roles(ROLE_SUPERADMIN, ROLE_MANAGER))])
async def mrf_summary(response: Response, db: AsyncSession = Depends(get_db)):
    """Pending MRF account count for the sidebar and Users tab badges (indexed COUNT, idx_mrf_users_status)."""
    response.headers["Cache-Control"] = "no-store"
    pending = (
        await db.execute(select(func.count()).select_from(MrfUser).where(MrfUser.status == STATUS_PENDING))
    ).scalar_one()
    return {"pending_accounts": pending}


@router.get(
    "/mrf/users",
    response_model=MrfUserListResponse,
    dependencies=[Depends(require_roles(ROLE_SUPERADMIN, ROLE_MANAGER))],
)
async def list_mrf_users(
    response: Response,
    status: str = Query(STATUS_APPROVED),
    q: Optional[str] = Query(None, max_length=MRF_USERS_SEARCH_MAX_LENGTH),
    sort: str = Query(SORT_NEWEST),
    page: int = Query(1, ge=1),
    page_size: int = Query(MRF_USERS_DEFAULT_PAGE_SIZE, ge=1, le=MRF_USERS_MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
):
    """MRF accounts of one group (pending or approved), searched, sorted and paged. Never returns password data."""
    if status not in USER_STATUSES:
        raise HTTPException(status_code=422, detail="status must be pending or approved")
    if sort not in USER_SORTS:
        raise HTTPException(status_code=422, detail="sort must be newest, first_name_asc or first_name_desc")

    flt = [MrfUser.status == status]
    term = (q or "").strip()
    if term:
        escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = "%" + escaped + "%"
        flt.append(
            or_(
                MrfUser.first_name.ilike(pattern, escape="\\"),
                MrfUser.last_name.ilike(pattern, escape="\\"),
                MrfUser.email.ilike(pattern, escape="\\"),
            )
        )

    if sort == SORT_NEWEST:
        order = (MrfUser.created_at.desc(), MrfUser.id)
    elif sort == SORT_FIRST_NAME_ASC:
        order = (func.lower(MrfUser.first_name).asc(), func.lower(MrfUser.last_name).asc(), MrfUser.id)
    else:
        order = (func.lower(MrfUser.first_name).desc(), func.lower(MrfUser.last_name).desc(), MrfUser.id)

    total = (await db.execute(select(func.count()).select_from(MrfUser).where(*flt))).scalar_one()
    rows = (
        await db.execute(
            select(MrfUser).where(*flt).order_by(*order).offset((page - 1) * page_size).limit(page_size)
        )
    ).scalars().all()

    response.headers["Cache-Control"] = "no-store"
    return MrfUserListResponse(
        data=[
            MrfUserListItem(
                id=u.id,
                first_name=u.first_name,
                last_name=u.last_name,
                email=u.email,
                department=u.department,
                position=u.position,
                status=u.status,
            )
            for u in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/mrf/forms",
    response_model=MrfFormListResponse,
    dependencies=[Depends(require_roles(ROLE_SUPERADMIN, ROLE_MANAGER))],
)
async def list_mrf_forms(
    response: Response,
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(MRF_FORMS_DEFAULT_PAGE_SIZE, ge=1, le=MRF_FORMS_MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
):
    """MRF forms, newest first, optionally one status, paged. question_count is one grouped count for the rows on the page."""
    if status is not None and status not in MRF_FORM_STATUSES:
        raise HTTPException(status_code=422, detail=MRF_FORM_STATUS_INVALID)

    flt = []
    if status is not None:
        flt.append(MrfForm.status == status)

    total = (await db.execute(select(func.count()).select_from(MrfForm).where(*flt))).scalar_one()
    forms = (
        await db.execute(
            select(MrfForm)
            .where(*flt)
            .order_by(MrfForm.created_at.desc(), MrfForm.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    counts = {}
    if forms:
        count_rows = await db.execute(
            select(MrfFormQuestion.form_id, func.count())
            .where(MrfFormQuestion.form_id.in_([f.id for f in forms]))
            .group_by(MrfFormQuestion.form_id)
        )
        counts = {form_id: n for form_id, n in count_rows.all()}

    response.headers["Cache-Control"] = "no-store"
    return MrfFormListResponse(
        data=[
            MrfFormListItem(
                id=f.id,
                name=f.name,
                status=f.status,
                question_count=counts.get(f.id, 0),
                created_at=to_app_tz(f.created_at),
            )
            for f in forms
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/mrf/forms",
    response_model=MrfFormCreated,
    status_code=201,
    dependencies=[Depends(require_roles(ROLE_SUPERADMIN, ROLE_MANAGER))],
)
async def create_mrf_form(
    payload: MrfFormCreate,
    db: AsyncSession = Depends(get_db),
):
    """Creates a DRAFT MRF form. The name is trimmed first; blank or over the limit is a 422, a duplicate (case-insensitive) is a 409.
    The unique index on lower(name) is the real guard: a lost race also returns the 409."""
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail=MRF_FORM_NAME_REQUIRED)
    if len(name) > MRF_FORM_NAME_MAX_LENGTH:
        raise HTTPException(status_code=422, detail=MRF_FORM_NAME_TOO_LONG)

    existing = await db.scalar(select(MrfForm.id).where(func.lower(MrfForm.name) == func.lower(name)))
    if existing is not None:
        raise HTTPException(status_code=409, detail=MRF_FORM_NAME_TAKEN)

    form = MrfForm(name=name, status=MRF_FORM_STATUS_DRAFT)
    db.add(form)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail=MRF_FORM_NAME_TAKEN)
    await db.refresh(form)

    return MrfFormCreated(
        id=form.id,
        name=form.name,
        status=form.status,
        created_at=to_app_tz(form.created_at),
    )


@router.patch(
    "/mrf/forms/{form_id}",
    response_model=MrfFormCreated,
    dependencies=[Depends(require_roles(ROLE_SUPERADMIN, ROLE_MANAGER))],
)
async def update_mrf_form(
    form_id: UUID,
    payload: MrfFormUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Renames a form and/or sets its status. Order of checks: 404, then the 422s, then the 409. A lost race on the name also returns the 409."""
    form = await db.scalar(select(MrfForm).where(MrfForm.id == form_id))
    if form is None:
        raise HTTPException(status_code=404, detail=MRF_FORM_NOT_FOUND)

    if payload.name is None and payload.status is None:
        raise HTTPException(status_code=422, detail=MRF_FORM_UPDATE_EMPTY)

    name = None
    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=422, detail=MRF_FORM_NAME_REQUIRED)
        if len(name) > MRF_FORM_NAME_MAX_LENGTH:
            raise HTTPException(status_code=422, detail=MRF_FORM_NAME_TOO_LONG)

    if payload.status is not None:
        if payload.status not in MRF_FORM_STATUSES:
            raise HTTPException(status_code=422, detail=MRF_FORM_STATUS_INVALID)
        if payload.status == MRF_FORM_STATUS_ACTIVE:
            question_count = await db.scalar(
                select(func.count()).select_from(MrfFormQuestion).where(MrfFormQuestion.form_id == form.id)
            )
            if not question_count:
                raise HTTPException(status_code=422, detail=MRF_FORM_NEEDS_QUESTION)

    if name is not None:
        taken = await db.scalar(
            select(MrfForm.id).where(func.lower(MrfForm.name) == func.lower(name), MrfForm.id != form.id)
        )
        if taken is not None:
            raise HTTPException(status_code=409, detail=MRF_FORM_NAME_TAKEN)
        form.name = name
    if payload.status is not None:
        form.status = payload.status

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail=MRF_FORM_NAME_TAKEN)
    await db.refresh(form)

    return MrfFormCreated(
        id=form.id,
        name=form.name,
        status=form.status,
        created_at=to_app_tz(form.created_at),
    )


@router.get(
    "/mrf/forms/{form_id}",
    response_model=MrfFormDetail,
    dependencies=[Depends(require_roles(ROLE_SUPERADMIN, ROLE_MANAGER))],
)
async def get_mrf_form(
    form_id: UUID,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """One MRF form with its questions in display_order (ties by id). Unknown id is a 404; a malformed id is FastAPI's own 422."""
    form = await db.scalar(select(MrfForm).where(MrfForm.id == form_id))
    if form is None:
        raise HTTPException(status_code=404, detail=MRF_FORM_NOT_FOUND)

    questions = (
        await db.execute(
            select(MrfFormQuestion)
            .where(MrfFormQuestion.form_id == form.id)
            .order_by(MrfFormQuestion.display_order, MrfFormQuestion.id)
        )
    ).scalars().all()

    response.headers["Cache-Control"] = "no-store"
    return MrfFormDetail(
        id=form.id,
        name=form.name,
        status=form.status,
        created_at=to_app_tz(form.created_at),
        questions=[
            MrfFormQuestionItem(
                id=q.id,
                question_type=q.question_type,
                question_text=q.question_text,
                options=q.options,
                is_required=q.is_required,
                is_classification=q.is_classification,
                display_order=q.display_order,
            )
            for q in questions
        ],
    )


@router.post("/mrf/users/{user_id}/approve", response_model=MrfUserListItem)
async def approve_mrf_user(
    user_id: UUID,
    admin: User = Depends(require_roles(ROLE_SUPERADMIN, ROLE_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Approves one pending MRF account: sets status, approved_at (now) and approved_by_user_id (the approving admin).
    The row is locked, so two admins approving the same account get one 200 and one 409. Never returns password data."""
    account = await db.scalar(select(MrfUser).where(MrfUser.id == user_id).with_for_update())
    if account is None:
        raise HTTPException(status_code=404, detail=MRF_USER_NOT_FOUND)
    if account.status == STATUS_APPROVED:
        raise HTTPException(status_code=409, detail=MRF_USER_ALREADY_APPROVED)

    account.status = STATUS_APPROVED
    account.approved_at = datetime.now(timezone.utc)
    account.approved_by_user_id = admin.id
    item = MrfUserListItem(
        id=account.id,
        first_name=account.first_name,
        last_name=account.last_name,
        email=account.email,
        department=account.department,
        position=account.position,
        status=account.status,
    )
    await db.commit()
    return item
