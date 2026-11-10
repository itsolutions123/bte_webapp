"""Admin MRF endpoints (docs/API_CONTRACT.md, /api/v1/admin/mrf). Mounted in app/main.py with the session check.

Summary only so far. Roles: SUPERADMIN and MANAGER (decided by the user 2026-11-10); RECRUITER gets 403."""
from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import MrfUser
from app.roles import ROLE_MANAGER, ROLE_SUPERADMIN
from app.routers.auth import require_roles

router = APIRouter()

STATUS_PENDING = "pending"  # same value as the MrfUser.status default


@router.get("/mrf/summary", dependencies=[Depends(require_roles(ROLE_SUPERADMIN, ROLE_MANAGER))])
async def mrf_summary(response: Response, db: AsyncSession = Depends(get_db)):
    """Pending MRF account count for the sidebar and Users tab badges (indexed COUNT, idx_mrf_users_status)."""
    response.headers["Cache-Control"] = "no-store"
    pending = (
        await db.execute(select(func.count()).select_from(MrfUser).where(MrfUser.status == STATUS_PENDING))
    ).scalar_one()
    return {"pending_accounts": pending}
