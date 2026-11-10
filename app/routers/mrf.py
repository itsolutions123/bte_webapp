"""MRF portal endpoints (docs/API_CONTRACT.md section 5, /api/v1/mrf).

Sign-up only so far. Mounted in app/main.py WITHOUT get_current_user: sign-up is public, and the
portal never uses the admin session. Login, logout and the portal session guard come in later steps."""
import time
from typing import Dict, List

from email_validator import validate_email, EmailNotValidError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import MrfUser
from app.mrf_lists import ALLOWED_EMAIL_DOMAINS, DEPARTMENTS, POSITIONS
from app.password_rules import validate_sign_up_password
from app.routers.auth import pwd_context
from app.schemas import MrfSignupRequest

router = APIRouter()

NAME_MAX_CHARS = 100  # first_name and last_name are String(100) in mrf_users
EMAIL_MAX_CHARS = 254

# Own in-memory cache, separate from LOGIN_RATE_LIMIT_CACHE. Every sign-up attempt counts, success or not.
# Per process: it resets when the server restarts.
SIGNUP_RATE_LIMIT_MAX = 5
SIGNUP_RATE_LIMIT_WINDOW_SECONDS = 60
SIGNUP_RATE_LIMIT_CACHE: Dict[str, List[float]] = {}


def check_and_record_signup_attempt(client_ip: str):
    now = time.time()
    for ip, timestamps in list(SIGNUP_RATE_LIMIT_CACHE.items()):
        recent = [ts for ts in timestamps if now - ts < SIGNUP_RATE_LIMIT_WINDOW_SECONDS]
        if recent:
            SIGNUP_RATE_LIMIT_CACHE[ip] = recent
        else:
            del SIGNUP_RATE_LIMIT_CACHE[ip]

    attempts = SIGNUP_RATE_LIMIT_CACHE.get(client_ip, [])
    if len(attempts) >= SIGNUP_RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Too many sign-up attempts from this IP. Please try again later.")
    attempts.append(now)
    SIGNUP_RATE_LIMIT_CACHE[client_ip] = attempts


@router.post("/signup", status_code=201)
async def signup(
    payload: MrfSignupRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"
    check_and_record_signup_attempt(client_ip)

    first_name = payload.first_name.strip()
    last_name = payload.last_name.strip()
    email = payload.email.strip().lower()
    department = payload.department.strip()
    position = payload.position.strip()

    if not first_name or not last_name or not email:
        raise HTTPException(status_code=422, detail="first_name, last_name and email must not be empty")
    if len(first_name) > NAME_MAX_CHARS or len(last_name) > NAME_MAX_CHARS:
        raise HTTPException(status_code=422, detail="first_name and last_name must be at most 100 characters")
    if len(email) > EMAIL_MAX_CHARS:
        raise HTTPException(status_code=422, detail="email must be at most 254 characters")
    try:
        validate_email(email, check_deliverability=False)
    except EmailNotValidError:
        raise HTTPException(status_code=422, detail="email is not valid")
    if email.rpartition("@")[2] not in ALLOWED_EMAIL_DOMAINS:
        raise HTTPException(status_code=422, detail="email domain is not allowed")
    if department not in DEPARTMENTS:
        raise HTTPException(status_code=422, detail="department is not allowed")
    if position not in POSITIONS:
        raise HTTPException(status_code=422, detail="position is not allowed")
    rule_error = validate_sign_up_password(payload.password)
    if rule_error:
        raise HTTPException(status_code=422, detail=rule_error)

    existing = await db.execute(select(MrfUser.id).where(MrfUser.email == email).limit(1))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    password_hash = await run_in_threadpool(pwd_context.hash, payload.password)
    db.add(
        MrfUser(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password_hash=password_hash,
            position=position,
            department=department,
        )
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")

    return Response(status_code=201, headers={"Cache-Control": "no-store"})
