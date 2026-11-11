"""Admin MRF endpoints (docs/API_CONTRACT.md, /api/v1/admin/mrf). Mounted in app/main.py with the session check.

Summary, users list and approve so far. Roles: SUPERADMIN and MANAGER (decided by the user 2026-11-10); RECRUITER gets 403."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import MrfUser, User
from app.roles import ROLE_MANAGER, ROLE_SUPERADMIN
from app.routers.auth import require_roles
from app.schemas import MrfUserListItem, MrfUserListResponse

router = APIRouter()

STATUS_PENDING = "pending"  # same value as the MrfUser.status default
STATUS_APPROVED = "approved"
USER_STATUSES = (STATUS_PENDING, STATUS_APPROVED)

# Users list limits and sort names (docs/API_CONTRACT.md, GET /api/v1/admin/mrf/users, decided by the user 2026-11-10).
MRF_USERS_DEFAULT_PAGE_SIZE = 10
MRF_USERS_MAX_PAGE_SIZE = 50
MRF_USERS_SEARCH_MAX_LENGTH = 100
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
