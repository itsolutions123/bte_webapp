"""Admin Recruiters metrics endpoints (docs/API_CONTRACT.md, /api/v1/admin/metrics). Mounted in app/main.py with the session check.

Feature F2: the scoring points per assignment and classification (GET for SUPERADMIN and MANAGER, PUT for SUPERADMIN only)."""
from datetime import date, datetime, timedelta, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import MrfRecruiterPoints, MrfRequest, User
from app.mrf_lists import (
    MRF_ASSIGNMENTS,
    MRF_CLASSIFICATION_OPTIONS,
    MRF_REQUEST_STATUS_CLOSED,
    MRF_REQUEST_STATUS_ON_GOING,
    MRF_REQUEST_STATUS_PARTIALLY_CLOSED,
)
from app.roles import ROLE_MANAGER, ROLE_RECRUITER, ROLE_SUPERADMIN
from app.routers.auth import require_roles
from app.schemas import (
    RecruiterMetricsClassification,
    RecruiterMetricsPeriod,
    RecruiterMetricsResponse,
    RecruiterMetricsRow,
    RecruiterMetricsTotals,
    RecruiterMetricsUnassigned,
    RecruiterPointsItem,
    RecruiterPointsListResponse,
    RecruiterPointsUpdate,
)
from app.timeutil import APP_TIMEZONE

router = APIRouter()

# Recruiter points (docs/API_CONTRACT.md, GET and PUT /api/v1/admin/metrics/recruiter-points, CONTRACTED 2026-11-27, migration 033).
# Keep the maximum in step with the CHECK ck_mrf_recruiter_points_points in migrations/033_mrf_recruiter_points.sql.
MRF_RECRUITER_POINTS_MAX = 100
MRF_RECRUITER_POINTS_PAIRS_INVALID = "Send every assignment and classification pair exactly once."
MRF_RECRUITER_POINTS_VALUE_INVALID = f"Points must be whole numbers from 0 to {MRF_RECRUITER_POINTS_MAX}."

# Recruiter metrics (docs/API_CONTRACT.md, GET /api/v1/admin/metrics/recruiters, CONTRACTED 2026-11-27). Same text as MRF_REQUESTS_DATE_ORDER in app/routers/admin_mrf.py.
MRF_METRICS_DATE_ORDER = "Start date must not be after end date."
MRF_METRICS_PRESET_AND_RANGE = "Use either a preset or a date range, not both."
MRF_METRICS_LAST_7_DAYS = 7
MRF_METRICS_LAST_30_DAYS = 30


async def _load_points_items(db: AsyncSession):
    """The stored rows in the documented order: assignment in MRF_ASSIGNMENTS order, then classification in MRF_CLASSIFICATION_OPTIONS order."""
    rows = (await db.execute(select(MrfRecruiterPoints))).scalars().all()
    by_key = {(r.assignment, r.classification): r.points for r in rows}
    return [
        RecruiterPointsItem(assignment=a, classification=c, points=by_key[(a, c)])
        for a in MRF_ASSIGNMENTS
        for c in MRF_CLASSIFICATION_OPTIONS
        if (a, c) in by_key
    ]


@router.get(
    "/metrics/recruiter-points",
    response_model=RecruiterPointsListResponse,
    dependencies=[Depends(require_roles(ROLE_SUPERADMIN, ROLE_MANAGER))],
)
async def list_recruiter_points(response: Response, db: AsyncSession = Depends(get_db)):
    """The full fixed set of points (12 rows today), not paginated: its size does not grow with data."""
    items = await _load_points_items(db)
    response.headers["Cache-Control"] = "no-store"
    return RecruiterPointsListResponse(data=items, total=len(items))


@router.put("/metrics/recruiter-points", response_model=RecruiterPointsListResponse)
async def update_recruiter_points(
    payload: RecruiterPointsUpdate,
    response: Response,
    admin: User = Depends(require_roles(ROLE_SUPERADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """Replaces the whole set atomically. Order of checks: 422 (pairs), 422 (a value that is not a whole number from 0 to the maximum).
    Last write wins. Editing points rescores past closed MRFs because scores are computed live from this table."""
    expected = {(a, c) for a in MRF_ASSIGNMENTS for c in MRF_CLASSIFICATION_OPTIONS}
    sent = [(i.assignment, i.classification) for i in payload.data]
    if len(sent) != len(expected) or set(sent) != expected:
        raise HTTPException(status_code=422, detail=MRF_RECRUITER_POINTS_PAIRS_INVALID)
    for i in payload.data:
        p = i.points
        if isinstance(p, bool) or not isinstance(p, int) or p < 0 or p > MRF_RECRUITER_POINTS_MAX:
            raise HTTPException(status_code=422, detail=MRF_RECRUITER_POINTS_VALUE_INVALID)

    now = datetime.now(timezone.utc)
    rows = (await db.execute(select(MrfRecruiterPoints).with_for_update())).scalars().all()
    existing = {(r.assignment, r.classification): r for r in rows}
    for i in payload.data:
        row = existing.get((i.assignment, i.classification))
        if row is None:
            db.add(MrfRecruiterPoints(
                assignment=i.assignment, classification=i.classification, points=i.points,
                updated_at=now, updated_by_user_id=admin.id,
            ))
        else:
            row.points = i.points
            row.updated_at = now
            row.updated_by_user_id = admin.id
    await db.flush()
    items = await _load_points_items(db)
    await db.commit()
    response.headers["Cache-Control"] = "no-store"
    return RecruiterPointsListResponse(data=items, total=len(items))


@router.get(
    "/metrics/recruiters",
    response_model=RecruiterMetricsResponse,
    dependencies=[Depends(require_roles(ROLE_SUPERADMIN, ROLE_MANAGER))],
)
async def get_recruiter_metrics(
    response: Response,
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    preset: Optional[Literal["today", "last_7_days", "last_30_days", "this_month"]] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Recruiter leaderboard data (docs/API_CONTRACT.md, GET /api/v1/admin/metrics/recruiters, CONTRACTED 2026-11-27).
    Earned: CLOSED MRF filtered on closed_at. Pending: ON GOING MRF and PARTIALLY CLOSED MRF filtered on created_at.
    CANCELLED MRF scores nothing. A request with no recruiter is only counted under unassigned. Points come live from
    mrf_recruiter_points; a pair with no row scores 0."""
    if preset is not None:
        if date_from is not None or date_to is not None:
            raise HTTPException(status_code=422, detail=MRF_METRICS_PRESET_AND_RANGE)
        today = datetime.now(APP_TIMEZONE).date()
        date_to = today
        if preset == "today":
            date_from = today
        elif preset == "last_7_days":
            date_from = today - timedelta(days=MRF_METRICS_LAST_7_DAYS - 1)
        elif preset == "last_30_days":
            date_from = today - timedelta(days=MRF_METRICS_LAST_30_DAYS - 1)
        else:
            date_from = today.replace(day=1)
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(status_code=422, detail=MRF_METRICS_DATE_ORDER)
    start = datetime.combine(date_from, datetime.min.time(), tzinfo=APP_TIMEZONE) if date_from is not None else None
    end = datetime.combine(date_to + timedelta(days=1), datetime.min.time(), tzinfo=APP_TIMEZONE) if date_to is not None else None

    def window(col):
        flt = []
        if start is not None:
            flt.append(col >= start)
        if end is not None:
            flt.append(col < end)
        return flt

    async def grouped(statuses, col):
        return (
            await db.execute(
                select(MrfRequest.recruiter_user_id, MrfRequest.assignment, MrfRequest.classification, func.count())
                .where(MrfRequest.status.in_(statuses), *window(col))
                .group_by(MrfRequest.recruiter_user_id, MrfRequest.assignment, MrfRequest.classification)
            )
        ).all()

    points = {
        (r.assignment, r.classification): r.points
        for r in (await db.execute(select(MrfRecruiterPoints))).scalars().all()
    }
    classes = list(MRF_CLASSIFICATION_OPTIONS)
    closed_rows = await grouped((MRF_REQUEST_STATUS_CLOSED,), MrfRequest.closed_at)
    pending_rows = await grouped((MRF_REQUEST_STATUS_ON_GOING, MRF_REQUEST_STATUS_PARTIALLY_CLOSED), MrfRequest.created_at)

    stats = {}

    def slot(rid):
        if rid not in stats:
            stats[rid] = {
                "earned": 0, "pending": 0, "closed": 0, "pending_n": 0,
                "assignments": set(), "by_class": {c: [0, 0] for c in classes},
            }
        return stats[rid]

    un_closed = 0
    un_pending = 0
    for rid, assignment, classification, n in closed_rows:
        if rid is None:
            un_closed += n
            continue
        pts = points.get((assignment, classification), 0)
        s = slot(rid)
        s["earned"] += n * pts
        s["closed"] += n
        s["assignments"].add(assignment)
        if classification in s["by_class"]:
            s["by_class"][classification][0] += n
            s["by_class"][classification][1] += n * pts
    for rid, assignment, classification, n in pending_rows:
        if rid is None:
            un_pending += n
            continue
        pts = points.get((assignment, classification), 0)
        s = slot(rid)
        s["pending"] += n * pts
        s["pending_n"] += n

    user_cols = (User.id, User.full_name, User.first_name, User.last_name, User.email)
    users = {
        r[0]: r[1:]
        for r in (
            await db.execute(
                select(*user_cols).where(
                    User.role == ROLE_RECRUITER, User.is_active.is_(True), User.archived_at.is_(None)
                )
            )
        ).all()
    }
    missing = [i for i in stats if i not in users]
    if missing:
        for r in (await db.execute(select(*user_cols).where(User.id.in_(missing)))).all():
            users[r[0]] = r[1:]

    entries = []
    for uid, (full_name, first, last, email) in users.items():
        name = full_name or f"{first or ''} {last or ''}".strip() or email
        entries.append((uid, name, stats.get(uid) or slot(uid)))
    entries.sort(key=lambda e: (-e[2]["earned"], -e[2]["pending"], e[1].lower(), str(e[0])))

    pool = sum(e[2]["earned"] for e in entries)
    data = []
    for position, (uid, name, s) in enumerate(entries, 1):
        known = [a for a in MRF_ASSIGNMENTS if a in s["assignments"]]
        extra = sorted(a for a in s["assignments"] if a not in MRF_ASSIGNMENTS)
        data.append(
            RecruiterMetricsRow(
                rank=position,
                id=uid,
                name=name,
                earned_points=s["earned"],
                pending_points=s["pending"],
                closed_count=s["closed"],
                pending_count=s["pending_n"],
                share_percent=round(s["earned"] * 100 / pool, 1) if pool > 0 else None,
                assignments=known + extra,
                by_classification=[
                    RecruiterMetricsClassification(classification=c, closed_count=s["by_class"][c][0], earned_points=s["by_class"][c][1])
                    for c in classes
                ],
            )
        )

    response.headers["Cache-Control"] = "no-store"
    return RecruiterMetricsResponse(
        period=RecruiterMetricsPeriod(
            date_from=date_from.isoformat() if date_from is not None else None,
            date_to=date_to.isoformat() if date_to is not None else None,
        ),
        classifications=classes,
        totals=RecruiterMetricsTotals(
            earned_points=pool,
            pending_points=sum(e[2]["pending"] for e in entries),
            closed_count=sum(e[2]["closed"] for e in entries),
            pending_count=sum(e[2]["pending_n"] for e in entries),
        ),
        unassigned=RecruiterMetricsUnassigned(closed_count=un_closed, pending_count=un_pending),
        data=data,
        total=len(data),
    )
