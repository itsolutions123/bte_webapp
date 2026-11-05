"""Users endpoints (docs/API_CONTRACT.md, /api/v1/admin/users). Mounted in app/main.py with the session check."""
import secrets
from typing import Optional

from email_validator import validate_email, EmailNotValidError
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.database import get_db
from app.models import User
from app.roles import ROLE_MANAGER, ROLE_RECRUITER, ROLE_SUPERADMIN, ALL_ROLES
from app.routers.auth import pwd_context, require_roles
from app.schemas import UserCreateRequest, UserCreateResponse, UserListItem, UserListResponse
from app.timeutil import to_app_tz

router = APIRouter()

# A SUPERADMIN cannot be created from the page (decided 2026-11-05); the set comes from app/roles.py.
CREATABLE_ROLES = ALL_ROLES - {ROLE_SUPERADMIN}


@router.post("/users", status_code=201, response_model=UserCreateResponse)
async def create_user(
    payload: UserCreateRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(ROLE_SUPERADMIN, ROLE_MANAGER)),
):
    first_name = payload.first_name.strip()
    last_name = payload.last_name.strip()
    email = payload.email.strip().lower()
    role = payload.role.strip()

    if not first_name or not last_name or not email:
        raise HTTPException(status_code=422, detail="first_name, last_name and email must not be empty")
    if len(first_name) > 100 or len(last_name) > 100:
        raise HTTPException(status_code=422, detail="first_name and last_name must be at most 100 characters")
    if len(email) > 254:
        raise HTTPException(status_code=422, detail="email must be at most 254 characters")
    try:
        validate_email(email, check_deliverability=False)
    except EmailNotValidError:
        raise HTTPException(status_code=422, detail="email is not valid")
    if role not in CREATABLE_ROLES:
        raise HTTPException(status_code=422, detail="role is not allowed")

    existing = await db.execute(select(User.id).where(User.email == email).limit(1))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email already exists.")

    temporary_password = secrets.token_urlsafe(12)
    password_hash = await run_in_threadpool(pwd_context.hash, temporary_password)

    user = User(
        email=email,
        password_hash=password_hash,
        role=role,
        is_active=True,
        first_name=first_name,
        last_name=last_name,
        full_name=f"{first_name} {last_name}"[:100],
        added_by_user_id=current_user.id,
        must_change_password=True,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists.")
    await db.refresh(user)

    response.headers["Cache-Control"] = "no-store"
    return UserCreateResponse(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        role=user.role,
        temporary_password=temporary_password,
    )


USER_SEARCH_MAX_LENGTH = 100
USER_TABS = ("users", "admins", "archived")


def _added_by_name(user_added_by_id, first_name, last_name, full_name, email):
    # Decided 2026-11-05: first + last, else full_name, else email; None when there is no creator.
    if user_added_by_id is None:
        return None
    name = f"{(first_name or '').strip()} {(last_name or '').strip()}".strip()
    return name or (full_name or "").strip() or email


@router.get(
    "/users",
    response_model=UserListResponse,
    dependencies=[Depends(require_roles(ROLE_SUPERADMIN, ROLE_MANAGER))],
)
async def list_users(
    response: Response,
    tab: str = Query("users"),
    q: Optional[str] = Query(None, max_length=USER_SEARCH_MAX_LENGTH),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    if tab not in USER_TABS:
        raise HTTPException(status_code=422, detail="tab must be users, admins or archived")

    if tab == "users":
        flt = [User.role.in_([ROLE_MANAGER, ROLE_RECRUITER]), User.archived_at.is_(None)]
    elif tab == "admins":
        flt = [User.role == ROLE_SUPERADMIN, User.archived_at.is_(None)]
    else:
        flt = [User.archived_at.is_not(None)]

    term = (q or "").strip()
    if term:
        escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = "%" + escaped + "%"
        flt.append(
            or_(
                User.first_name.ilike(pattern, escape="\\"),
                User.last_name.ilike(pattern, escape="\\"),
                User.email.ilike(pattern, escape="\\"),
            )
        )

    total = (await db.execute(select(func.count()).select_from(User).where(*flt))).scalar_one()

    creator = aliased(User)
    result = await db.execute(
        select(User, creator.first_name, creator.last_name, creator.full_name, creator.email)
        .outerjoin(creator, creator.id == User.added_by_user_id)
        .where(*flt)
        .order_by(User.first_name.asc().nulls_last(), User.id)
        .offset((page - 1) * limit)
        .limit(limit)
    )

    items = [
        UserListItem(
            id=u.id,
            first_name=u.first_name,
            last_name=u.last_name,
            email=u.email,
            role=u.role,
            last_login_at=to_app_tz(u.last_login_at),
            created_at=to_app_tz(u.created_at),
            added_by_name=_added_by_name(u.added_by_user_id, c_first, c_last, c_full, c_email),
            archived_at=to_app_tz(u.archived_at),
        )
        for u, c_first, c_last, c_full, c_email in result.all()
    ]

    response.headers["Cache-Control"] = "no-store"
    return UserListResponse(data=items, total=total, page=page, limit=limit)
