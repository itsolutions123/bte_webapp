"""Admin MRF endpoints (docs/API_CONTRACT.md, /api/v1/admin/mrf). Mounted in app/main.py with the session check.

Summary, users list and approve, plus the forms endpoints (list, create, get one, update) and the question create, update and delete endpoints. Roles: SUPERADMIN and MANAGER (decided by the user 2026-11-10); RECRUITER gets 403."""
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import MrfForm, MrfFormQuestion, MrfRequest, MrfRequestAnswer, MrfUser, User
from app.mrf_lists import (
    MRF_ASSIGNMENTS,
    MRF_CLASSIFICATION_OPTIONS,
    MRF_FORM_NAME_MAX_LENGTH,
    MRF_FORM_STATUS_ACTIVE,
    MRF_FORM_STATUS_DRAFT,
    MRF_FORM_STATUSES,
    MRF_QUESTION_TEXT_MAX_LENGTH,
    MRF_QUESTION_TYPE_MULTIPLE_CHOICE,
    MRF_QUESTION_TYPE_OPEN_ENDED,
    MRF_QUESTION_TYPE_YES_NO,
    MRF_QUESTION_TYPES,
    MRF_REQUEST_STATUS_APPROVED,
    MRF_REQUEST_STATUS_PENDING,
    MRF_REQUEST_STATUS_REJECTED,
    MRF_REQUEST_STATUSES,
)
from app.roles import ROLE_MANAGER, ROLE_SUPERADMIN
from app.routers.auth import require_roles
from app.schemas import (
    MrfFormCreate,
    MrfFormCreated,
    MrfFormDetail,
    MrfFormListItem,
    MrfFormQuestionCreate,
    MrfFormQuestionItem,
    MrfFormQuestionUpdate,
    MrfFormListResponse,
    MrfFormUpdate,
    MrfQuestionReorder,
    MrfQuestionReorderResponse,
    MrfAdminRequestListItem,
    MrfAdminRequestListResponse,
    MrfAdminRequestAnswerItem,
    MrfAdminRequestDetail,
    MrfRequestDecision,
    MrfUserListItem,
    MrfUserListResponse,
)
from app.timeutil import APP_TIMEZONE, to_app_tz

router = APIRouter()

STATUS_PENDING = "pending"  # same value as the MrfUser.status default
STATUS_APPROVED = "approved"
USER_STATUSES = (STATUS_PENDING, STATUS_APPROVED)

# Users list limits and sort names (docs/API_CONTRACT.md, GET /api/v1/admin/mrf/users, decided by the user 2026-11-10).
MRF_USERS_DEFAULT_PAGE_SIZE = 10
MRF_USERS_MAX_PAGE_SIZE = 50
MRF_USERS_SEARCH_MAX_LENGTH = 100

# Requests list limits and messages (docs/API_CONTRACT.md, GET /api/v1/admin/mrf/requests, decided by the user 2026-11-17 part 65 and 2026-11-18 part 79, option A).
MRF_REQUESTS_DEFAULT_PAGE_SIZE = 10
MRF_REQUESTS_MAX_PAGE_SIZE = 50
MRF_REQUESTS_SEARCH_MAX_LENGTH = 100
MRF_REQUESTS_STATUS_INVALID = "status must be Pending, Approved or Rejected"
MRF_REQUESTS_SEARCH_TOO_LONG = f"Search must be {MRF_REQUESTS_SEARCH_MAX_LENGTH} characters or fewer."
MRF_REQUESTS_DATE_ORDER = "Start date must not be after end date."

# Request detail (docs/API_CONTRACT.md, GET /api/v1/admin/mrf/requests/{request_id}, part 80); the decision endpoint (step G) reuses it.
MRF_REQUEST_NOT_FOUND = "Request not found."

# Decision endpoint (docs/API_CONTRACT.md, POST /api/v1/admin/mrf/requests/{request_id}/decision, decided 2026-11-17 part 65 and 2026-11-18 part 81, option A).
MRF_REMARKS_MAX_LENGTH = 500
MRF_DECISION_ALREADY_DECIDED = "This request has already been decided."
MRF_DECISION_STATUS_INVALID = "Choose Approved or Rejected."
MRF_DECISION_REMARKS_REQUIRED = "Add remarks to reject a request."
MRF_DECISION_REMARKS_TOO_LONG = f"Remarks must be {MRF_REMARKS_MAX_LENGTH} characters or fewer."

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
MRF_FORM_UPDATE_EMPTY = "Send a name, a status or an assignment to update."
MRF_FORM_NEEDS_QUESTION = "Add at least one question before setting this form to Active."
# Assignment messages (part 59, (pC-2) and (pC-3), option A each). The invalid text is built from MRF_ASSIGNMENTS so the names have one copy here.
MRF_FORM_ASSIGNMENT_INVALID = f"assignment must be {', '.join(MRF_ASSIGNMENTS[:-1])} or {MRF_ASSIGNMENTS[-1]}"
MRF_FORM_NEEDS_ASSIGNMENT = "Set an assignment before setting this form to Active."
MRF_FORM_NEEDS_CLASSIFICATION = (
    "Add a Classification question before "
    "setting this form to Active."
)

# Create question messages (docs/API_CONTRACT.md, POST /api/v1/admin/mrf/forms/{form_id}/questions, decided by the user 2026-11-13, part 50, (z1) to (z10), option A each).
# The option messages are the same texts as the job form's create_question (admin.py), copied here on purpose (z1).
MRF_QUESTION_TEXT_REQUIRED = "question_text must not be empty"
MRF_QUESTION_TEXT_TOO_LONG = f"question_text must be at most {MRF_QUESTION_TEXT_MAX_LENGTH} characters"
MRF_QUESTION_TYPE_INVALID = "question_type must be YES_NO, MULTIPLE_CHOICE or OPEN_ENDED"
MRF_QUESTION_OPTION_EMPTY = "option labels must not be empty"
MRF_QUESTION_YES_NO_COUNT = "YES_NO options must be exactly 2 labels"
MRF_QUESTION_YES_NO_DISTINCT = "the two YES_NO labels must be different"
MRF_QUESTION_MC_MIN = "MULTIPLE_CHOICE requires at least 3 options"
MRF_QUESTION_MC_DISTINCT = "MULTIPLE_CHOICE options must be distinct"
MRF_QUESTION_OPEN_NO_OPTIONS = "OPEN_ENDED takes no options"
MRF_QUESTION_CLASSIFICATION_TYPE = "is_classification is only allowed on a MULTIPLE_CHOICE question"
MRF_QUESTION_CLASSIFICATION_OPTIONS = "a Classification question must have exactly these options: " + ", ".join(MRF_CLASSIFICATION_OPTIONS)
MRF_QUESTION_CLASSIFICATION_EXISTS = "This form already has a Classification question."

# Update question messages (docs/API_CONTRACT.md, PATCH /api/v1/admin/mrf/forms/{form_id}/questions/{question_id}, decided by the user 2026-11-13, part 51, (p1) to (p10)).
MRF_QUESTION_NOT_FOUND = "Question not found."
MRF_QUESTION_UPDATE_EMPTY = "Send question_text, options or is_required to update."
MRF_QUESTION_CLASSIFICATION_OPTIONS_LOCKED = "a Classification question's options cannot be changed"
MRF_QUESTION_CLASSIFICATION_ALWAYS_REQUIRED = "a Classification question is always required"

# Reorder question message (docs/API_CONTRACT.md, POST /api/v1/admin/mrf/forms/{form_id}/questions/reorder, decided by the user 2026-11-13, part 54, (r1) to (r10), option A each).
MRF_QUESTION_REORDER_MISMATCH = "ordered_ids must list every question of this form exactly once."

# Delete question message (docs/API_CONTRACT.md, DELETE .../questions/{question_id}, part 65 sign-off (c5), option A).
# One text for a question that has rows in mrf_request_answers. Checked last, after the two 404s and the Active-form 409.
MRF_QUESTION_ANSWERED = "This question has been answered in a request and cannot be deleted."
MRF_QUESTION_ACTIVE_FORM = (
    "Set the form to Draft before deleting its last "
    "question or its Classification question."
)
SORT_NEWEST = "newest"
SORT_FIRST_NAME_ASC = "first_name_asc"
SORT_FIRST_NAME_DESC = "first_name_desc"
USER_SORTS = (SORT_NEWEST, SORT_FIRST_NAME_ASC, SORT_FIRST_NAME_DESC)

# Approve error messages (docs/API_CONTRACT.md, POST /api/v1/admin/mrf/users/{user_id}/approve, decided by the user 2026-11-11).
MRF_USER_NOT_FOUND = "Account not found."
MRF_USER_ALREADY_APPROVED = "Account is already approved."


@router.get(
    "/mrf/requests",
    response_model=MrfAdminRequestListResponse,
    dependencies=[Depends(require_roles(ROLE_SUPERADMIN, ROLE_MANAGER))],
)
async def list_mrf_requests(
    response: Response,
    classification: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    status: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(MRF_REQUESTS_DEFAULT_PAGE_SIZE, ge=1, le=MRF_REQUESTS_MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
):
    """All MRF requests (every submitter), filtered, searched and paged, newest first."""
    if status is not None and status not in MRF_REQUEST_STATUSES:
        raise HTTPException(status_code=422, detail=MRF_REQUESTS_STATUS_INVALID)
    term = (q or "").strip()
    if len(term) > MRF_REQUESTS_SEARCH_MAX_LENGTH:
        raise HTTPException(status_code=422, detail=MRF_REQUESTS_SEARCH_TOO_LONG)
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(status_code=422, detail=MRF_REQUESTS_DATE_ORDER)

    flt = []
    if status is not None:
        flt.append(MrfRequest.status == status)
    if classification is not None:
        flt.append(MrfRequest.classification == classification)
    if department is not None:
        flt.append(MrfRequest.department == department)
    if date_from is not None:
        start = datetime.combine(date_from, datetime.min.time(), tzinfo=APP_TIMEZONE)
        flt.append(MrfRequest.created_at >= start)
    if date_to is not None:
        end = datetime.combine(date_to + timedelta(days=1), datetime.min.time(), tzinfo=APP_TIMEZONE)
        flt.append(MrfRequest.created_at < end)
    if term:
        escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = "%" + escaped + "%"
        flt.append(
            or_(
                MrfUser.first_name.ilike(pattern, escape="\\"),
                MrfUser.last_name.ilike(pattern, escape="\\"),
                func.concat(MrfUser.first_name, " ", MrfUser.last_name).ilike(pattern, escape="\\"),
                MrfForm.name.ilike(pattern, escape="\\"),
            )
        )

    total = (
        await db.execute(
            select(func.count())
            .select_from(MrfRequest)
            .join(MrfUser, MrfUser.id == MrfRequest.user_id)
            .join(MrfForm, MrfForm.id == MrfRequest.form_id)
            .where(*flt)
        )
    ).scalar_one()
    rows = (
        await db.execute(
            select(MrfRequest, MrfUser.first_name, MrfUser.last_name, MrfForm.name)
            .join(MrfUser, MrfUser.id == MrfRequest.user_id)
            .join(MrfForm, MrfForm.id == MrfRequest.form_id)
            .where(*flt)
            .order_by(MrfRequest.created_at.desc(), MrfRequest.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()

    response.headers["Cache-Control"] = "no-store"
    return MrfAdminRequestListResponse(
        data=[
            MrfAdminRequestListItem(
                id=r.id,
                submitted_by=(first + " " + last).strip(),
                classification=r.classification,
                department=r.department,
                assignment=r.assignment,
                form_name=form_name,
                created_at=to_app_tz(r.created_at),
                status=r.status,
                remarks=r.remarks,
                decided_at=to_app_tz(r.decided_at),
            )
            for r, first, last, form_name in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/mrf/requests/{request_id}",
    response_model=MrfAdminRequestDetail,
    dependencies=[Depends(require_roles(ROLE_SUPERADMIN, ROLE_MANAGER))],
)
async def get_mrf_request(
    request_id: UUID,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """One MRF request for HR review: the list-row fields plus its answers in the form display order."""
    row = (
        await db.execute(
            select(MrfRequest, MrfUser.first_name, MrfUser.last_name, MrfForm.name)
            .join(MrfUser, MrfUser.id == MrfRequest.user_id)
            .join(MrfForm, MrfForm.id == MrfRequest.form_id)
            .where(MrfRequest.id == request_id)
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail=MRF_REQUEST_NOT_FOUND)
    r, first, last, form_name = row

    answers = (
        await db.execute(
            select(
                MrfFormQuestion.id,
                MrfFormQuestion.question_text,
                MrfFormQuestion.question_type,
                MrfRequestAnswer.answer,
            )
            .select_from(MrfRequestAnswer)
            .join(MrfFormQuestion, MrfFormQuestion.id == MrfRequestAnswer.question_id)
            .where(MrfRequestAnswer.request_id == request_id)
            .order_by(MrfFormQuestion.display_order, MrfFormQuestion.id)
        )
    ).all()

    response.headers["Cache-Control"] = "no-store"
    return MrfAdminRequestDetail(
        id=r.id,
        submitted_by=(first + " " + last).strip(),
        classification=r.classification,
        department=r.department,
        assignment=r.assignment,
        form_name=form_name,
        created_at=to_app_tz(r.created_at),
        status=r.status,
        remarks=r.remarks,
        decided_at=to_app_tz(r.decided_at),
        answers=[
            MrfAdminRequestAnswerItem(
                question_id=qid,
                question_text=qtext,
                question_type=qtype,
                answer=ans,
            )
            for qid, qtext, qtype, ans in answers
        ],
    )


@router.post(
    "/mrf/requests/{request_id}/decision",
    response_model=MrfAdminRequestListItem,
)
async def decide_mrf_request(
    request_id: UUID,
    payload: MrfRequestDecision,
    response: Response,
    admin: User = Depends(require_roles(ROLE_SUPERADMIN, ROLE_MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Approves or rejects one Pending MRF request, once. The row is locked while it is checked, so two admins
    deciding the same request get one 200 and one 409. Order of checks: 404, 409, then the 422s."""
    req = await db.scalar(select(MrfRequest).where(MrfRequest.id == request_id).with_for_update())
    if req is None:
        raise HTTPException(status_code=404, detail=MRF_REQUEST_NOT_FOUND)
    if req.status != MRF_REQUEST_STATUS_PENDING:
        raise HTTPException(status_code=409, detail=MRF_DECISION_ALREADY_DECIDED)

    if payload.status not in (MRF_REQUEST_STATUS_APPROVED, MRF_REQUEST_STATUS_REJECTED):
        raise HTTPException(status_code=422, detail=MRF_DECISION_STATUS_INVALID)
    remarks = (payload.remarks or "").strip()
    if payload.status == MRF_REQUEST_STATUS_REJECTED and not remarks:
        raise HTTPException(status_code=422, detail=MRF_DECISION_REMARKS_REQUIRED)
    if len(remarks) > MRF_REMARKS_MAX_LENGTH:
        raise HTTPException(status_code=422, detail=MRF_DECISION_REMARKS_TOO_LONG)

    req.status = payload.status
    req.remarks = remarks or None
    req.decided_by_user_id = admin.id
    req.decided_at = datetime.now(timezone.utc)

    first, last, form_name = (
        await db.execute(
            select(MrfUser.first_name, MrfUser.last_name, MrfForm.name)
            .select_from(MrfRequest)
            .join(MrfUser, MrfUser.id == MrfRequest.user_id)
            .join(MrfForm, MrfForm.id == MrfRequest.form_id)
            .where(MrfRequest.id == req.id)
        )
    ).one()
    item = MrfAdminRequestListItem(
        id=req.id,
        submitted_by=(first + " " + last).strip(),
        classification=req.classification,
        department=req.department,
        assignment=req.assignment,
        form_name=form_name,
        created_at=to_app_tz(req.created_at),
        status=req.status,
        remarks=req.remarks,
        decided_at=to_app_tz(req.decided_at),
    )
    await db.commit()
    response.headers["Cache-Control"] = "no-store"
    return item


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
    """Renames a form and/or sets its status and/or its assignment. Order of checks: 404, then the 422s (nothing to update, name, status value, assignment value, ACTIVE needs a question, ACTIVE needs an assignment, ACTIVE needs a Classification question), then the 409. A lost race on the name also returns the 409."""
    form = await db.scalar(select(MrfForm).where(MrfForm.id == form_id))
    if form is None:
        raise HTTPException(status_code=404, detail=MRF_FORM_NOT_FOUND)

    if payload.name is None and payload.status is None and payload.assignment is None:
        raise HTTPException(status_code=422, detail=MRF_FORM_UPDATE_EMPTY)

    name = None
    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=422, detail=MRF_FORM_NAME_REQUIRED)
        if len(name) > MRF_FORM_NAME_MAX_LENGTH:
            raise HTTPException(status_code=422, detail=MRF_FORM_NAME_TOO_LONG)

    if payload.status is not None and payload.status not in MRF_FORM_STATUSES:
        raise HTTPException(status_code=422, detail=MRF_FORM_STATUS_INVALID)

    if payload.assignment is not None and payload.assignment not in MRF_ASSIGNMENTS:
        raise HTTPException(status_code=422, detail=MRF_FORM_ASSIGNMENT_INVALID)

    if payload.status == MRF_FORM_STATUS_ACTIVE:
        question_count = await db.scalar(
            select(func.count()).select_from(MrfFormQuestion).where(MrfFormQuestion.form_id == form.id)
        )
        if not question_count:
            raise HTTPException(status_code=422, detail=MRF_FORM_NEEDS_QUESTION)
        # An assignment sent in the same request counts as set (pC-2).
        effective_assignment = payload.assignment if payload.assignment is not None else form.assignment
        if effective_assignment is None:
            raise HTTPException(status_code=422, detail=MRF_FORM_NEEDS_ASSIGNMENT)
        has_classification = await db.scalar(
            select(MrfFormQuestion.id)
            .where(
                MrfFormQuestion.form_id == form.id,
                MrfFormQuestion.is_classification.is_(True),
            )
            .limit(1)
        )
        if has_classification is None:
            raise HTTPException(status_code=422, detail=MRF_FORM_NEEDS_CLASSIFICATION)

    if name is not None:
        taken = await db.scalar(
            select(MrfForm.id).where(func.lower(MrfForm.name) == func.lower(name), MrfForm.id != form.id)
        )
        if taken is not None:
            raise HTTPException(status_code=409, detail=MRF_FORM_NAME_TAKEN)
        form.name = name
    if payload.status is not None:
        form.status = payload.status
    if payload.assignment is not None:
        form.assignment = payload.assignment

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
        assignment=form.assignment,
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
        assignment=form.assignment,
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


@router.post(
    "/mrf/forms/{form_id}/questions",
    response_model=MrfFormQuestionItem,
    status_code=201,
    dependencies=[Depends(require_roles(ROLE_SUPERADMIN, ROLE_MANAGER))],
)
async def create_mrf_question(
    form_id: UUID,
    payload: MrfFormQuestionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Adds a question to the end of a form. Order of checks (decided 2026-11-13, (z10)): 404, the text, the type, the option rules,
    the Classification rules, then the 409. The form's status does not matter ((z4)). A lost race on the Classification index also returns the 409."""
    form = await db.scalar(select(MrfForm.id).where(MrfForm.id == form_id))
    if form is None:
        raise HTTPException(status_code=404, detail=MRF_FORM_NOT_FOUND)

    text = payload.question_text.strip()
    if not text:
        raise HTTPException(status_code=422, detail=MRF_QUESTION_TEXT_REQUIRED)
    if len(text) > MRF_QUESTION_TEXT_MAX_LENGTH:
        raise HTTPException(status_code=422, detail=MRF_QUESTION_TEXT_TOO_LONG)

    qtype = payload.question_type
    if qtype not in MRF_QUESTION_TYPES:
        raise HTTPException(status_code=422, detail=MRF_QUESTION_TYPE_INVALID)

    options = None
    if payload.options is not None:
        options = [o.strip() for o in payload.options]
        if any(not o for o in options):
            raise HTTPException(status_code=422, detail=MRF_QUESTION_OPTION_EMPTY)

    if qtype == MRF_QUESTION_TYPE_YES_NO:
        if options is not None:
            if len(options) != 2:
                raise HTTPException(status_code=422, detail=MRF_QUESTION_YES_NO_COUNT)
            if options[0].lower() == options[1].lower():
                raise HTTPException(status_code=422, detail=MRF_QUESTION_YES_NO_DISTINCT)
    elif qtype == MRF_QUESTION_TYPE_MULTIPLE_CHOICE:
        if options is None or len(options) < 3:
            raise HTTPException(status_code=422, detail=MRF_QUESTION_MC_MIN)
        if len(set(o.lower() for o in options)) != len(options):
            raise HTTPException(status_code=422, detail=MRF_QUESTION_MC_DISTINCT)
    else:
        if options is not None:
            raise HTTPException(status_code=422, detail=MRF_QUESTION_OPEN_NO_OPTIONS)

    if payload.is_classification:
        if qtype != MRF_QUESTION_TYPE_MULTIPLE_CHOICE:
            raise HTTPException(status_code=422, detail=MRF_QUESTION_CLASSIFICATION_TYPE)
        if options != list(MRF_CLASSIFICATION_OPTIONS):
            raise HTTPException(status_code=422, detail=MRF_QUESTION_CLASSIFICATION_OPTIONS)
        existing = await db.scalar(
            select(MrfFormQuestion.id)
            .where(MrfFormQuestion.form_id == form_id, MrfFormQuestion.is_classification.is_(True))
            .limit(1)
        )
        if existing is not None:
            raise HTTPException(status_code=409, detail=MRF_QUESTION_CLASSIFICATION_EXISTS)

    # (z7): a Classification question is always required, whatever was sent. Otherwise the type's default (true, true, false).
    if payload.is_classification:
        is_required = True
    elif payload.is_required is not None:
        is_required = payload.is_required
    else:
        is_required = qtype != MRF_QUESTION_TYPE_OPEN_ENDED

    next_order = (
        await db.scalar(
            select(func.coalesce(func.max(MrfFormQuestion.display_order), 0)).where(MrfFormQuestion.form_id == form_id)
        )
    ) + 1

    stored_options = options
    if qtype == MRF_QUESTION_TYPE_MULTIPLE_CHOICE:
        stored_options = [{"id": uuid4().hex, "text": o} for o in options]

    question = MrfFormQuestion(
        form_id=form_id,
        question_type=qtype,
        question_text=text,
        options=stored_options,
        is_required=is_required,
        is_classification=payload.is_classification,
        display_order=next_order,
    )
    db.add(question)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        if payload.is_classification:
            raise HTTPException(status_code=409, detail=MRF_QUESTION_CLASSIFICATION_EXISTS)
        raise
    await db.refresh(question)

    return MrfFormQuestionItem(
        id=question.id,
        question_type=question.question_type,
        question_text=question.question_text,
        options=question.options,
        is_required=question.is_required,
        is_classification=question.is_classification,
        display_order=question.display_order,
    )


@router.patch(
    "/mrf/forms/{form_id}/questions/{question_id}",
    response_model=MrfFormQuestionItem,
    dependencies=[Depends(require_roles(ROLE_SUPERADMIN, ROLE_MANAGER))],
)
async def update_mrf_question(
    form_id: UUID,
    question_id: UUID,
    payload: MrfFormQuestionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Edits a question: any of question_text, options, is_required. A field sent as null counts as not sent ((p3)).
    Order of checks (decided 2026-11-13, (p8)): the form 404, the question 404, the empty body, the text, the Classification lock, the option rules.
    The option rules are a second copy of the POST's on purpose ((p10)) and run against the STORED question_type. The form's status does not matter."""
    form = await db.scalar(select(MrfForm.id).where(MrfForm.id == form_id))
    if form is None:
        raise HTTPException(status_code=404, detail=MRF_FORM_NOT_FOUND)

    question = await db.scalar(
        select(MrfFormQuestion).where(MrfFormQuestion.id == question_id, MrfFormQuestion.form_id == form_id)
    )
    if question is None:
        raise HTTPException(status_code=404, detail=MRF_QUESTION_NOT_FOUND)

    if payload.question_text is None and payload.options is None and payload.is_required is None:
        raise HTTPException(status_code=422, detail=MRF_QUESTION_UPDATE_EMPTY)

    new_text = None
    if payload.question_text is not None:
        new_text = payload.question_text.strip()
        if not new_text:
            raise HTTPException(status_code=422, detail=MRF_QUESTION_TEXT_REQUIRED)
        if len(new_text) > MRF_QUESTION_TEXT_MAX_LENGTH:
            raise HTTPException(status_code=422, detail=MRF_QUESTION_TEXT_TOO_LONG)

    if question.is_classification:
        if payload.options is not None:
            raise HTTPException(status_code=422, detail=MRF_QUESTION_CLASSIFICATION_OPTIONS_LOCKED)
        if payload.is_required is False:
            raise HTTPException(status_code=422, detail=MRF_QUESTION_CLASSIFICATION_ALWAYS_REQUIRED)

    new_options = None
    if payload.options is not None:
        labels = [o.strip() for o in payload.options]
        if any(not o for o in labels):
            raise HTTPException(status_code=422, detail=MRF_QUESTION_OPTION_EMPTY)
        qtype = question.question_type
        if qtype == MRF_QUESTION_TYPE_YES_NO:
            if len(labels) != 2:
                raise HTTPException(status_code=422, detail=MRF_QUESTION_YES_NO_COUNT)
            if labels[0].lower() == labels[1].lower():
                raise HTTPException(status_code=422, detail=MRF_QUESTION_YES_NO_DISTINCT)
            new_options = labels
        elif qtype == MRF_QUESTION_TYPE_MULTIPLE_CHOICE:
            if len(labels) < 3:
                raise HTTPException(status_code=422, detail=MRF_QUESTION_MC_MIN)
            if len(set(label.lower() for label in labels)) != len(labels):
                raise HTTPException(status_code=422, detail=MRF_QUESTION_MC_DISTINCT)
            # (p5): a label that matches a stored label (case-insensitive, after strip) keeps that option's id; any other label gets a new id.
            old_ids = {}
            for o in question.options or []:
                if isinstance(o, dict) and "id" in o and "text" in o:
                    old_ids[str(o["text"]).strip().lower()] = o["id"]
            new_options = []
            for label in labels:
                kept = old_ids.get(label.lower())
                new_options.append({"id": kept if kept is not None else uuid4().hex, "text": label})
        else:
            raise HTTPException(status_code=422, detail=MRF_QUESTION_OPEN_NO_OPTIONS)

    if new_text is not None:
        question.question_text = new_text
    if new_options is not None:
        question.options = new_options
    if payload.is_required is not None:
        question.is_required = payload.is_required
    await db.commit()
    await db.refresh(question)

    return MrfFormQuestionItem(
        id=question.id,
        question_type=question.question_type,
        question_text=question.question_text,
        options=question.options,
        is_required=question.is_required,
        is_classification=question.is_classification,
        display_order=question.display_order,
    )


@router.delete(
    "/mrf/forms/{form_id}/questions/{question_id}",
    status_code=204,
    dependencies=[Depends(require_roles(ROLE_SUPERADMIN, ROLE_MANAGER))],
)
async def delete_mrf_question(
    form_id: UUID,
    question_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Deletes a question ((d1) to (d6), decided 2026-11-13). 204 with no body. Order of checks: the form 404, then the question 404 (an unknown
    question and a question of another form share one text, (d2)). The remaining questions keep their display_order, a gap is left ((d3)).
    A Draft form is unrestricted ((d4), (d5)). On an ACTIVE form the last question and the Classification question are refused with 409 (part 64, part 65 sign-off (c4)), checked after the two 404s and before the answered-question 409.
    One DELETE statement scoped by id and form_id; zero rows removed is the question 404, so a repeated or simultaneous delete never gives a 500.
    A question with rows in mrf_request_answers is refused with 409 (part 65 sign-off (c5)): the foreign key blocks the DELETE and that is mapped here."""
    form_row = (
        await db.execute(
            select(MrfForm.id, MrfForm.status).where(MrfForm.id == form_id)
        )
    ).first()
    if form_row is None:
        raise HTTPException(status_code=404, detail=MRF_FORM_NOT_FOUND)

    question_row = (
        await db.execute(
            select(MrfFormQuestion.is_classification).where(
                MrfFormQuestion.id == question_id,
                MrfFormQuestion.form_id == form_id,
            )
        )
    ).first()
    if question_row is None:
        raise HTTPException(status_code=404, detail=MRF_QUESTION_NOT_FOUND)

    # (c4): on an ACTIVE form the last question and the Classification question stay.
    if form_row.status == MRF_FORM_STATUS_ACTIVE:
        blocked = question_row.is_classification
        if not blocked:
            question_count = await db.scalar(
                select(func.count()).select_from(MrfFormQuestion)
                .where(MrfFormQuestion.form_id == form_id)
            )
            blocked = question_count <= 1
        if blocked:
            raise HTTPException(status_code=409, detail=MRF_QUESTION_ACTIVE_FORM)

    try:
        result = await db.execute(
            delete(MrfFormQuestion).where(MrfFormQuestion.id == question_id, MrfFormQuestion.form_id == form_id)
        )
    except IntegrityError:
        # mrf_request_answers.question_id references this question with no ON DELETE (migration 024), so the
        # database refuses the delete when an answer exists. That is the answered-question 409 ((c5)).
        await db.rollback()
        raise HTTPException(status_code=409, detail=MRF_QUESTION_ANSWERED)
    if result.rowcount == 0:
        await db.rollback()
        raise HTTPException(status_code=404, detail=MRF_QUESTION_NOT_FOUND)

    await db.commit()
    return Response(status_code=204)


@router.post(
    "/mrf/forms/{form_id}/questions/reorder",
    response_model=MrfQuestionReorderResponse,
    dependencies=[Depends(require_roles(ROLE_SUPERADMIN, ROLE_MANAGER))],
)
async def reorder_mrf_question(
    form_id: UUID,
    body: MrfQuestionReorder,
    db: AsyncSession = Depends(get_db),
):
    """Reorders the questions of one form ((r1) to (r10), decided 2026-11-13). Order of checks: malformed form_id or body (FastAPI's list-style 422),
    the form 404, then the id list (422, one plain-string text for a missing, repeated, unknown or other-form id). The form row is locked first, so two
    reorders run one after the other. display_order is renumbered 1 to n in the order of ordered_ids. The form's status does not matter. Returns the
    form's questions in the new order. No Cache-Control header."""
    form = await db.scalar(select(MrfForm.id).where(MrfForm.id == form_id).with_for_update())
    if form is None:
        raise HTTPException(status_code=404, detail=MRF_FORM_NOT_FOUND)

    current_ids = (
        await db.execute(select(MrfFormQuestion.id).where(MrfFormQuestion.form_id == form_id))
    ).scalars().all()
    if len(body.ordered_ids) != len(current_ids) or set(body.ordered_ids) != set(current_ids):
        await db.rollback()
        raise HTTPException(status_code=422, detail=MRF_QUESTION_REORDER_MISMATCH)

    for position, question_id in enumerate(body.ordered_ids, start=1):
        await db.execute(
            update(MrfFormQuestion)
            .where(MrfFormQuestion.id == question_id, MrfFormQuestion.form_id == form_id)
            .values(display_order=position)
        )
    await db.commit()

    questions = (
        await db.execute(
            select(MrfFormQuestion)
            .where(MrfFormQuestion.form_id == form_id)
            .order_by(MrfFormQuestion.display_order, MrfFormQuestion.id)
        )
    ).scalars().all()
    return MrfQuestionReorderResponse(
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
        ]
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
