"""Admin Recruiters metrics endpoints (docs/API_CONTRACT.md, /api/v1/admin/metrics). Mounted in app/main.py with the session check.

Feature F2: the scoring points per assignment and classification (GET for SUPERADMIN and MANAGER, PUT for SUPERADMIN only)."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import MrfRecruiterPoints, User
from app.mrf_lists import MRF_ASSIGNMENTS, MRF_CLASSIFICATION_OPTIONS
from app.roles import ROLE_MANAGER, ROLE_SUPERADMIN
from app.routers.auth import require_roles
from app.schemas import RecruiterPointsItem, RecruiterPointsListResponse, RecruiterPointsUpdate

router = APIRouter()

# Recruiter points (docs/API_CONTRACT.md, GET and PUT /api/v1/admin/metrics/recruiter-points, CONTRACTED 2026-11-27, migration 033).
# Keep the maximum in step with the CHECK ck_mrf_recruiter_points_points in migrations/033_mrf_recruiter_points.sql.
MRF_RECRUITER_POINTS_MAX = 100
MRF_RECRUITER_POINTS_PAIRS_INVALID = "Send every assignment and classification pair exactly once."
MRF_RECRUITER_POINTS_VALUE_INVALID = f"Points must be whole numbers from 0 to {MRF_RECRUITER_POINTS_MAX}."


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
