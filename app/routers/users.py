"""Users endpoints (docs/API_CONTRACT.md, /api/v1/admin/users). Mounted in app/main.py with the session check."""
import secrets

from email_validator import validate_email, EmailNotValidError
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.roles import ROLE_MANAGER, ROLE_SUPERADMIN, ALL_ROLES
from app.routers.auth import pwd_context, require_roles
from app.schemas import UserCreateRequest, UserCreateResponse

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
