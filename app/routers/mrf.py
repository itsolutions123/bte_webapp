"""MRF portal endpoints (docs/API_CONTRACT.md section 5, /api/v1/mrf).

Sign-up, login and logout so far. Mounted in app/main.py WITHOUT get_current_user: sign-up, login and logout are
public, and the portal never uses the admin session. The portal session guard dependency and me are here too (me needs the mrf_session_id cookie). The page guard comes later."""
import json
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List
from uuid import UUID, uuid4

import aiofiles
from email_validator import validate_email, EmailNotValidError
from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, Response
from fastapi.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile as StarletteUploadFile
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import (
    MrfForm,
    MrfFormQuestion,
    MrfRequest,
    MrfRequestAnswer,
    MrfSession,
    MrfUser,
)
from app.mrf_lists import (
    ALLOWED_EMAIL_DOMAINS,
    DEPARTMENTS,
    MRF_ANSWER_MAX_LENGTH,
    MRF_ATTACHMENT_CHUNK_BYTES,
    MRF_ATTACHMENT_DEFAULT_STORAGE_PATH,
    MRF_ATTACHMENT_MAX_BYTES,
    MRF_FORM_STATUS_ACTIVE,
    MRF_QUESTION_TYPE_FILE_UPLOAD,
    MRF_QUESTION_TYPE_OPEN_ENDED,
    MRF_QUESTION_TYPE_YES_NO,
    MRF_REQUEST_STATUS_PENDING,
    POSITIONS,
)
from app.password_rules import validate_sign_up_password
from app.routers.auth import DUMMY_HASH, pwd_context
from app.schemas import (
    MrfLoginRequest,
    MrfPortalFormDetail,
    MrfPortalFormListResponse,
    MrfRequestAnswerIn,
    MrfRequestListItem,
    MrfRequestListResponse,
    MrfSignupRequest,
)

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


# Portal Forms list (docs/API_CONTRACT.md, GET /api/v1/mrf/forms, DECIDED part 61).
# Portal-local copies of the admin Forms list limits (decision A, part 61); the portal router does not import admin_mrf.
MRF_PORTAL_FORMS_DEFAULT_PAGE_SIZE = 10
MRF_PORTAL_FORMS_MAX_PAGE_SIZE = 50
# Same text as MRF_FORM_NOT_FOUND in app/routers/admin_mrf.py (contract, part 65 sign-off (c3)); kept portal-local like MRF_STATUS_APPROVED.
MRF_PORTAL_FORM_NOT_FOUND = "Form not found."
# Portal Requests list (docs/API_CONTRACT.md, GET /api/v1/mrf/requests, DECIDED part 65 sign-off (d)); portal-local like the forms limits.
MRF_PORTAL_REQUESTS_DEFAULT_PAGE_SIZE = 10
MRF_PORTAL_REQUESTS_MAX_PAGE_SIZE = 50


@router.get("/forms", response_model=MrfPortalFormListResponse)
async def list_portal_forms(
    response: Response,
    page: int = Query(1, ge=1),
    page_size: int = Query(MRF_PORTAL_FORMS_DEFAULT_PAGE_SIZE, ge=1, le=MRF_PORTAL_FORMS_MAX_PAGE_SIZE),
    _user: MrfUser = Depends(get_current_mrf_user),
    db: AsyncSession = Depends(get_db),
):
    # ACTIVE forms only, newest first. Rows carry id, name and assignment (no status: every row is Active).
    response.headers["Cache-Control"] = "no-store"
    flt = (MrfForm.status == MRF_FORM_STATUS_ACTIVE,)
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
    return {
        "data": [{"id": f.id, "name": f.name, "assignment": f.assignment} for f in forms],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/forms/{form_id}", response_model=MrfPortalFormDetail)
async def get_portal_form(
    form_id: UUID,
    response: Response,
    _user: MrfUser = Depends(get_current_mrf_user),
    db: AsyncSession = Depends(get_db),
):
    # ACTIVE forms only: an unknown form and a Draft form share one 404, so a requestor cannot tell them apart (contract, part 64).
    # Questions in display_order, ties by id. Options are returned as stored (part 68, option A).
    response.headers["Cache-Control"] = "no-store"
    form = await db.scalar(
        select(MrfForm).where(MrfForm.id == form_id, MrfForm.status == MRF_FORM_STATUS_ACTIVE)
    )
    if form is None:
        raise HTTPException(status_code=404, detail=MRF_PORTAL_FORM_NOT_FOUND)
    questions = (
        await db.execute(
            select(MrfFormQuestion)
            .where(MrfFormQuestion.form_id == form.id)
            .order_by(MrfFormQuestion.display_order, MrfFormQuestion.id)
        )
    ).scalars().all()
    return {
        "id": form.id,
        "name": form.name,
        "assignment": form.assignment,
        "questions": [
            {
                "id": q.id,
                "question_type": q.question_type,
                "question_text": q.question_text,
                "options": q.options,
                "is_required": q.is_required,
                "is_classification": q.is_classification,
                "display_order": q.display_order,
                "description": q.description,
            }
            for q in questions
        ],
    }


# Submit (docs/API_CONTRACT.md, POST /api/v1/mrf/requests; DECIDED parts 64, 65 and 69). Portal-local message constants.
MRF_SUBMIT_FORM_UNAVAILABLE = "This form is no longer available."
MRF_SUBMIT_UNKNOWN_QUESTION = "Unknown question."
MRF_SUBMIT_DUPLICATE_ANSWER = "Each question can be answered only once."
MRF_SUBMIT_REQUIRED = "Answer every required question."
MRF_SUBMIT_BAD_OPTION = "Choose one of the listed options."
MRF_SUBMIT_TOO_LONG = "Answers must be " + str(MRF_ANSWER_MAX_LENGTH) + " characters or fewer."
# FILE_UPLOAD texts (docs/API_CONTRACT.md, POST /api/v1/mrf/requests, multipart shape, f9).
MRF_SUBMIT_BAD_ANSWERS = "answers must be a JSON list."
MRF_SUBMIT_FILE_AS_ANSWER = "File answers must be sent as files."
MRF_SUBMIT_FILE_NOT_ALLOWED = "A file was sent for a question that does not take one."
MRF_SUBMIT_FILE_NOT_PDF = "Attachment must be a PDF."
MRF_SUBMIT_FILE_TOO_LARGE = "Attachment must be " + str(MRF_ATTACHMENT_MAX_BYTES // (1024 * 1024)) + " MB or smaller."


def question_labels(question: MrfFormQuestion) -> List[str]:
    """Current labels of a YES_NO (plain strings) or MULTIPLE_CHOICE ([{id, text}]) question."""
    if question.question_type == MRF_QUESTION_TYPE_YES_NO:
        return [str(o) for o in (question.options or [])]
    return [o["text"] for o in (question.options or [])]


@router.get("/requests", response_model=MrfRequestListResponse)
async def list_my_requests(
    response: Response,
    page: int = Query(1, ge=1),
    page_size: int = Query(MRF_PORTAL_REQUESTS_DEFAULT_PAGE_SIZE, ge=1, le=MRF_PORTAL_REQUESTS_MAX_PAGE_SIZE),
    user: MrfUser = Depends(get_current_mrf_user),
    db: AsyncSession = Depends(get_db),
):
    # The signed-in user's own requests only, newest first (contract, part 64/65). form_name is the form's CURRENT name (part 78, option A).
    response.headers["Cache-Control"] = "no-store"
    flt = (MrfRequest.user_id == user.id,)
    total = (await db.execute(select(func.count()).select_from(MrfRequest).where(*flt))).scalar_one()
    rows = (
        await db.execute(
            select(MrfRequest, MrfForm.name)
            .join(MrfForm, MrfForm.id == MrfRequest.form_id)
            .where(*flt)
            .order_by(MrfRequest.created_at.desc(), MrfRequest.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).all()
    return {
        "data": [
            {
                "id": r.id,
                "form_name": form_name,
                "assignment": r.assignment,
                "created_at": r.created_at,
                "status": r.status,
                "remarks": r.remarks,
            }
            for r, form_name in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# FILE_UPLOAD attachment file handling (same owner-only modes as the resume storage in public.py).
MRF_ATTACHMENT_FILE_MODE = 0o600
MRF_ATTACHMENT_DIR_MODE = 0o700
MRF_ATTACHMENT_NAME_MAX_LENGTH = 200
MRF_ATTACHMENT_DEFAULT_NAME = "attachment.pdf"


def _parse_answer_items(raw):
    # The multipart "answers" field: a JSON list of {question_id, answer} for non-file questions only.
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError
        items = []
        for entry in data:
            if not isinstance(entry, dict) or not isinstance(entry.get("answer"), str):
                raise ValueError
            items.append(MrfRequestAnswerIn(question_id=UUID(str(entry.get("question_id"))), answer=entry["answer"]))
        return items
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(status_code=422, detail=MRF_SUBMIT_BAD_ANSWERS)


def _remove_files(paths):
    for path in paths:
        try:
            os.remove(path)
        except OSError:
            pass


def _attachment_display_name(filename):
    name = os.path.basename((filename or "").replace("\\", "/")).strip()[:MRF_ATTACHMENT_NAME_MAX_LENGTH]
    return name or MRF_ATTACHMENT_DEFAULT_NAME


async def _save_attachment_temp(upload, storage_dir):
    # Validate (content type, %PDF magic bytes, size cap) and stream to a temporary name. Returns (path, size).
    if upload.content_type != "application/pdf":
        raise HTTPException(status_code=422, detail=MRF_SUBMIT_FILE_NOT_PDF)
    magic_bytes = await upload.read(4)
    if magic_bytes != b"%PDF":
        raise HTTPException(status_code=422, detail=MRF_SUBMIT_FILE_NOT_PDF)
    tmp_path = os.path.join(storage_dir, "tmp_" + str(uuid4()) + ".pdf")
    size = len(magic_bytes)
    try:
        async with aiofiles.open(tmp_path, "wb") as f:
            await f.write(magic_bytes)
            while chunk := await upload.read(MRF_ATTACHMENT_CHUNK_BYTES):
                size += len(chunk)
                if size > MRF_ATTACHMENT_MAX_BYTES:
                    raise HTTPException(status_code=422, detail=MRF_SUBMIT_FILE_TOO_LARGE)
                await f.write(chunk)
        os.chmod(tmp_path, MRF_ATTACHMENT_FILE_MODE)
    except BaseException:
        _remove_files([tmp_path])
        raise
    return tmp_path, size


@router.post("/requests", status_code=201, response_model=MrfRequestListItem)
async def submit_request(
    request: Request,
    response: Response,
    form_id: UUID = Form(...),
    answers: str = Form(...),
    user: MrfUser = Depends(get_current_mrf_user),
    db: AsyncSession = Depends(get_db),
):
    # One multipart POST at the end of the wizard, one transaction (request row plus one row per answer).
    response.headers["Cache-Control"] = "no-store"
    form = await db.scalar(select(MrfForm).where(MrfForm.id == form_id))
    if form is None:
        raise HTTPException(status_code=404, detail=MRF_PORTAL_FORM_NOT_FOUND)
    questions = (
        await db.execute(
            select(MrfFormQuestion)
            .where(MrfFormQuestion.form_id == form.id)
            .order_by(MrfFormQuestion.display_order, MrfFormQuestion.id)
        )
    ).scalars().all()
    classification_question = next((q for q in questions if q.is_classification), None)
    if form.status != MRF_FORM_STATUS_ACTIVE or form.assignment is None or classification_question is None:
        raise HTTPException(status_code=409, detail=MRF_SUBMIT_FORM_UNAVAILABLE)

    items = _parse_answer_items(answers)
    by_id = {q.id: q for q in questions}
    if any(item.question_id not in by_id for item in items):
        raise HTTPException(status_code=422, detail=MRF_SUBMIT_UNKNOWN_QUESTION)
    if len({item.question_id for item in items}) != len(items):
        raise HTTPException(status_code=422, detail=MRF_SUBMIT_DUPLICATE_ANSWER)
    if any(by_id[item.question_id].question_type == MRF_QUESTION_TYPE_FILE_UPLOAD for item in items):
        raise HTTPException(status_code=422, detail=MRF_SUBMIT_FILE_AS_ANSWER)

    # File parts: one per FILE_UPLOAD question, named by the raw question_id (multipart shape, f9).
    uploads = {}
    for key, value in (await request.form()).multi_items():
        if not isinstance(value, StarletteUploadFile) or not value.filename:
            continue  # a text field (form_id, answers) or an empty file input
        try:
            file_question_id = UUID(key)
        except ValueError:
            raise HTTPException(status_code=422, detail=MRF_SUBMIT_UNKNOWN_QUESTION)
        if file_question_id not in by_id:
            raise HTTPException(status_code=422, detail=MRF_SUBMIT_UNKNOWN_QUESTION)
        if by_id[file_question_id].question_type != MRF_QUESTION_TYPE_FILE_UPLOAD:
            raise HTTPException(status_code=422, detail=MRF_SUBMIT_FILE_NOT_ALLOWED)
        if file_question_id in uploads:
            raise HTTPException(status_code=422, detail=MRF_SUBMIT_DUPLICATE_ANSWER)
        uploads[file_question_id] = value

    # A blank answer counts as not answered and is never stored (part 69, option A).
    given = {item.question_id: item.answer for item in items if item.answer.strip() != ""}
    if any((q.is_required or q.is_classification) and q.id not in given and q.id not in uploads for q in questions):
        raise HTTPException(status_code=422, detail=MRF_SUBMIT_REQUIRED)

    stored = {}
    for question_id, raw in given.items():
        q = by_id[question_id]
        if q.question_type == MRF_QUESTION_TYPE_OPEN_ENDED:
            continue
        if raw not in question_labels(q):
            raise HTTPException(status_code=422, detail=MRF_SUBMIT_BAD_OPTION)
        stored[question_id] = raw
    for question_id, raw in given.items():
        q = by_id[question_id]
        if q.question_type != MRF_QUESTION_TYPE_OPEN_ENDED:
            continue
        text = raw.strip()
        if len(text) > MRF_ANSWER_MAX_LENGTH:
            raise HTTPException(status_code=422, detail=MRF_SUBMIT_TOO_LONG)
        stored[question_id] = text

    # Validate and stream every file to a temporary name before any database write (contract, f9).
    storage_dir = os.environ.get("MRF_ATTACHMENT_STORAGE_PATH", MRF_ATTACHMENT_DEFAULT_STORAGE_PATH)
    saved_files = {}
    if uploads:
        os.makedirs(storage_dir, mode=MRF_ATTACHMENT_DIR_MODE, exist_ok=True)
    try:
        for file_question_id, upload in uploads.items():
            tmp_path, size = await _save_attachment_temp(upload, storage_dir)
            saved_files[file_question_id] = (tmp_path, size, _attachment_display_name(upload.filename))
    except BaseException:
        _remove_files([entry[0] for entry in saved_files.values()])
        raise

    # Values for the response are read before the commit (no lazy loads after it).
    form_name = form.name
    assignment = form.assignment
    request_row = MrfRequest(
        form_id=form.id,
        user_id=user.id,
        classification=stored[classification_question.id],
        department=user.department,
        assignment=assignment,
        status=MRF_REQUEST_STATUS_PENDING,
    )
    db.add(request_row)
    created_paths = [entry[0] for entry in saved_files.values()]
    try:
        await db.flush()
        request_id = request_row.id
        created_at = request_row.created_at
        for question_id, value in stored.items():
            db.add(MrfRequestAnswer(request_id=request_id, question_id=question_id, answer=value))
        for file_question_id, (tmp_path, size, display_name) in saved_files.items():
            final_path = os.path.join(storage_dir, str(request_id) + "_" + str(file_question_id) + ".pdf")
            os.replace(tmp_path, final_path)
            created_paths.append(final_path)
            db.add(
                MrfRequestAnswer(
                    request_id=request_id,
                    question_id=file_question_id,
                    answer=None,
                    answer_file_path=final_path,
                    answer_file_name=display_name,
                    answer_file_size=size,
                )
            )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        _remove_files(created_paths)
        raise HTTPException(status_code=409, detail=MRF_SUBMIT_FORM_UNAVAILABLE)
    except Exception:
        await db.rollback()
        _remove_files(created_paths)
        raise

    return {
        "id": request_id,
        "form_name": form_name,
        "assignment": assignment,
        "created_at": created_at,
        "status": MRF_REQUEST_STATUS_PENDING,
        "remarks": None,
    }
