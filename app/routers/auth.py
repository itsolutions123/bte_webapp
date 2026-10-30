import time
import secrets
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext

from app.database import get_db
from app.models import User, Session as SessionModel
from app.schemas import LoginRequest, LoginResponse

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Fixed dummy hash so an unknown-email login still runs a bcrypt verify,
# keeping response timing similar to a real wrong-password case (no enumeration).
DUMMY_HASH = pwd_context.hash("dummy-password-for-timing-parity")

SESSION_COOKIE_NAME = "session_id"
SESSION_DURATION_SECONDS = 8 * 60 * 60  # 8h fixed hard cap (SECURITY.md section 2, decided 2026-10-30)

# In-memory rate limiter, same pattern as app/routers/public.py's RATE_LIMIT_CACHE,
# but counts failed login attempts only (SECURITY.md section 2: 5/min/IP).
LOGIN_RATE_LIMIT_CACHE = {}

def check_login_rate_limit(client_ip: str):
    now = time.time()
    for ip, timestamps in list(LOGIN_RATE_LIMIT_CACHE.items()):
        LOGIN_RATE_LIMIT_CACHE[ip] = [ts for ts in timestamps if now - ts < 60]
        if not LOGIN_RATE_LIMIT_CACHE[ip]:
            del LOGIN_RATE_LIMIT_CACHE[ip]

    recent_failures = LOGIN_RATE_LIMIT_CACHE.get(client_ip, [])
    if len(recent_failures) >= 5:
        raise HTTPException(status_code=429, detail="Too many login attempts from this IP. Please try again later.")

def record_login_failure(client_ip: str):
    now = time.time()
    recent_failures = LOGIN_RATE_LIMIT_CACHE.get(client_ip, [])
    recent_failures.append(now)
    LOGIN_RATE_LIMIT_CACHE[client_ip] = recent_failures


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else "unknown"
    check_login_rate_limit(client_ip)

    email = payload.email.strip().lower()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    generic_error = "Invalid email or password."

    if user is None:
        pwd_context.verify(payload.password, DUMMY_HASH)  # timing parity only, result discarded
        record_login_failure(client_ip)
        raise HTTPException(status_code=401, detail=generic_error)

    if not user.is_active or not pwd_context.verify(payload.password, user.password_hash):
        record_login_failure(client_ip)
        raise HTTPException(status_code=401, detail=generic_error)

    now = datetime.now(timezone.utc)
    session_id = secrets.token_urlsafe(32)
    db.add(SessionModel(
        id=session_id,
        user_id=user.id,
        created_at=now,
        expires_at=now + timedelta(seconds=SESSION_DURATION_SECONDS),
        last_active_at=now,
    ))
    user.last_login_at = now
    await db.commit()

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        httponly=True,
        secure=False,  # dropped for now: LAN HTTP, no TLS (SECURITY.md section 2, decided 2026-10-30)
        samesite="lax",
        max_age=SESSION_DURATION_SECONDS,
        path="/",
    )

    return LoginResponse(role=user.role)
