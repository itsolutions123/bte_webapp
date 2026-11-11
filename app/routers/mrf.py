"""MRF portal endpoints (docs/API_CONTRACT.md section 5, /api/v1/mrf).

Sign-up, login and logout so far. Mounted in app/main.py WITHOUT get_current_user: sign-up, login and logout are
public, and the portal never uses the admin session. The portal session guard dependency and me are here too (me needs the mrf_session_id cookie). The page guard comes later."""
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from email_validator import validate_email, EmailNotValidError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import MrfSession, MrfUser
from app.mrf_lists import ALLOWED_EMAIL_DOMAINS, DEPARTMENTS, POSITIONS
from app.password_rules import validate_sign_up_password
from app.routers.auth import DUMMY_HASH, pwd_context
from app.schemas import MrfLoginRequest, MrfSignupRequest

router = APIRouter()

NAME_MAX_CHARS = 100  # first_name and last_name are String(100) in mrf_users
EMAIL_MAX_CHARS = 254

# Own in-memory cache, separate from LOGIN_RATE_LIMIT_CACHE. Every sign-up attempt counts, success or not.
# Per process: it resets when the server restarts.
SIGNUP_RATE_LIMIT_MAX = 5
SIGNUP_RATE_LIMIT_WINDOW_SECONDS = 60
SIGNUP_RATE_LIMIT_CACHE: Dict[str, List[float]] = {}

# Portal login (docs/API_CONTRACT.md, POST /api/v1/mrf/login, DECIDED part 37). Its own cookie and its own limiter.
MRF_SESSION_COOKIE_NAME = "mrf_session_id"
MRF_SESSION_DURATION_SECONDS = 8 * 60 * 60  # fixed hard cap, never extended; no idle timeout
MRF_STATUS_APPROVED = "approved"  # duplicates the value the admin approve endpoint writes
MRF_LOGIN_INVALID_MESSAGE = "Invalid email or password."
MRF_LOGIN_PENDING_MESSAGE = "Your account is pending approval."
MRF_LOGIN_RATE_LIMIT_MESSAGE = "Too many login attempts from this IP. Please try again later."
# Own in-memory cache, separate from LOGIN_RATE_LIMIT_CACHE and the sign-up cache. Failed attempts only.
MRF_LOGIN_RATE_LIMIT_MAX = 5
MRF_LOGIN_RATE_LIMIT_WINDOW_SECONDS = 60
MRF_LOGIN_RATE_LIMIT_CACHE: Dict[str, List[float]] = {}


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


def check_mrf_login_rate_limit(client_ip: str):
    now = time.time()
    for ip, timestamps in list(MRF_LOGIN_RATE_LIMIT_CACHE.items()):
        recent = [ts for ts in timestamps if now - ts < MRF_LOGIN_RATE_LIMIT_WINDOW_SECONDS]
        if recent:
            MRF_LOGIN_RATE_LIMIT_CACHE[ip] = recent
        else:
            del MRF_LOGIN_RATE_LIMIT_CACHE[ip]
    if len(MRF_LOGIN_RATE_LIMIT_CACHE.get(client_ip, [])) >= MRF_LOGIN_RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail=MRF_LOGIN_RATE_LIMIT_MESSAGE)


def record_mrf_login_failure(client_ip: str):
    MRF_LOGIN_RATE_LIMIT_CACHE.setdefault(client_ip, []).append(time.time())


@router.post("/login")
async def login(
    payload: MrfLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"
    check_mrf_login_rate_limit(client_ip)

    email = payload.email.strip().lower()
    user = (await db.execute(select(MrfUser).where(MrfUser.email == email))).scalar_one_or_none()

    if user is None:
        # Timing parity only, result discarded: an unknown email still pays for one bcrypt verify.
        await run_in_threadpool(pwd_context.verify, payload.password, DUMMY_HASH)
        record_mrf_login_failure(client_ip)
        raise HTTPException(status_code=401, detail=MRF_LOGIN_INVALID_MESSAGE)

    if not await run_in_threadpool(pwd_context.verify, payload.password, user.password_hash):
        record_mrf_login_failure(client_ip)
        raise HTTPException(status_code=401, detail=MRF_LOGIN_INVALID_MESSAGE)

    # Correct password, account not approved yet (only pending exists today): no cookie, no session,
    # and it does not count as a failed attempt.
    if user.status != MRF_STATUS_APPROVED:
        raise HTTPException(status_code=403, detail=MRF_LOGIN_PENDING_MESSAGE)

    now = datetime.now(timezone.utc)
    session_id = secrets.token_urlsafe(32)
    db.add(
        MrfSession(
            id=session_id,
            user_id=user.id,
            created_at=now,
            expires_at=now + timedelta(seconds=MRF_SESSION_DURATION_SECONDS),
            last_active_at=now,
        )
    )
    await db.commit()

    response = Response(status_code=200, headers={"Cache-Control": "no-store"})
    response.set_cookie(
        key=MRF_SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=False,  # LAN HTTP, no TLS (same as the admin cookie, SECURITY.md section 2)
        samesite="lax",
        max_age=MRF_SESSION_DURATION_SECONDS,
        path="/",
    )
    return response


@router.post("/logout", status_code=204, response_class=Response)
async def logout(request: Request, db: AsyncSession = Depends(get_db)):
    """Ends the current portal session only (docs/API_CONTRACT.md, POST /api/v1/mrf/logout, DECIDED part 37).
    No auth dependency on purpose: an expired or unknown session can still log out. Always 204, always clears
    the cookie. Other sessions of the same user stay valid."""
    session_id = request.cookies.get(MRF_SESSION_COOKIE_NAME)
    if session_id:
        await db.execute(delete(MrfSession).where(MrfSession.id == session_id))
        await db.commit()

    response = Response(status_code=204)
    response.headers["Cache-Control"] = "no-store"
    response.delete_cookie(
        key=MRF_SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=False,  # same as login: LAN HTTP, no TLS (SECURITY.md section 2)
        samesite="lax",
    )
    return response


async def get_current_mrf_user(request: Request, db: AsyncSession = Depends(get_db)) -> MrfUser:
    """Portal session guard (docs/API_CONTRACT.md, GET /api/v1/mrf/me, DECIDED part 37): mrf_session_id cookie ->
    mrf_sessions row -> mrf_users row. Reads only the MRF cookie, never the admin session_id. Fixed 8 h cap
    (expires_at), no idle timeout. Every failure is the same 401. The user is kept on request.state.mrf_user."""
    not_authenticated = HTTPException(status_code=401, detail="Not authenticated.")

    session_id = request.cookies.get(MRF_SESSION_COOKIE_NAME)
    if not session_id:
        raise not_authenticated

    session_row = (await db.execute(select(MrfSession).where(MrfSession.id == session_id))).scalar_one_or_none()
    if session_row is None or session_row.expires_at <= datetime.now(timezone.utc):
        raise not_authenticated

    user = (await db.execute(select(MrfUser).where(MrfUser.id == session_row.user_id))).scalar_one_or_none()
    if user is None or user.status != MRF_STATUS_APPROVED:
        raise not_authenticated

    request.state.mrf_user = user
    return user


@router.get("/me")
async def me(response: Response, user: MrfUser = Depends(get_current_mrf_user)):
    """Name for the portal footer. No email, id, position, department or status (contract)."""
    response.headers["Cache-Control"] = "no-store"
    return {"first_name": user.first_name, "last_name": user.last_name}
