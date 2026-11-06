from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import public

app = FastAPI(title="BTE Careers API")

# CORS: allow the local bte-website frontend to call the public API directly (local-only LAN test, 2026-10-15)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://10.0.10.37:8086"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Mount Routers
# Note: every /api/v1/admin/* router included below except auth requires a valid session (get_current_user, attached at the include; login/logout/me live in the auth router)
from app.routers import public
app.include_router(public.router, prefix="/api/v1/public", tags=["Public"])
from app.routers import admin
from app.routers.auth import get_current_user
from fastapi import Depends
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"], dependencies=[Depends(get_current_user)])
from app.routers import auth
app.include_router(auth.router, prefix="/api/v1/admin", tags=["Auth"])
from app.routers import users
app.include_router(users.router, prefix="/api/v1/admin", tags=["Users"], dependencies=[Depends(get_current_user)])

from fastapi import Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os

# Set up templates & static
base_dir = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(base_dir, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(base_dir, "static")), name="static")

from fastapi import Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

from app.roles import ROLE_SUPERADMIN, ROLE_MANAGER
from app.password_rules import RULES_LEAD_IN, RULE_PHRASES, PASSWORD_MIN_BYTES, PASSWORD_MAX_BYTES

NO_STORE = {"Cache-Control": "no-store"}

class LoginRedirect(Exception):
    """Raised by require_page_session when an /admin page is requested without a valid session."""

@app.exception_handler(LoginRedirect)
async def login_redirect_handler(request: Request, exc: LoginRedirect):
    return RedirectResponse(url="/login", status_code=302, headers=NO_STORE)

async def require_page_session(request: Request, db: AsyncSession = Depends(get_db)):
    # Same check as the admin API (get_current_user); pages redirect instead of returning 401 JSON.
    # The signed-in user is kept on request.state.user so role checks and the sidebar need no second lookup.
    try:
        request.state.user = await get_current_user(request, db)
    except HTTPException:
        raise LoginRedirect()

def require_page_roles(*allowed_roles):
    """Page-route role check. List it AFTER require_page_session in a route's dependencies.
    A signed-in user whose role is not allowed gets 403 {"detail": "Forbidden."} (API_CONTRACT.md, GET /admin/users)."""
    async def check(request: Request):
        user = getattr(request.state, "user", None)
        if user is None or user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Forbidden.")
    return check

@app.get("/apply", include_in_schema=False)
async def serve_apply_page(request: Request, job_id: str = ""):
    # We pass job_id to pre-fill the hidden input in apply.html
    return templates.TemplateResponse(
        request=request,
        name="apply.html",
        context={
            "job": {"id": job_id},
            "website_careers_url": os.environ["WEBSITE_CAREERS_URL"],
            "terms_version": os.environ.get("TERMS_VERSION", ""),
        },
    )

@app.get("/careers", include_in_schema=False)
async def serve_careers_board(request: Request):
    return templates.TemplateResponse(request=request, name="careers.html")

@app.get("/login", include_in_schema=False)
async def serve_login_page(request: Request):
    # Shell only (section 8): form is static, no auth check or submit wiring yet.
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/change-password", include_in_schema=False)
async def serve_change_password_page(request: Request):
    # No session check on purpose: a user with a temporary password never has a session
    # (SECURITY.md section 2, forced password change). The rules list comes from app/password_rules.py.
    return templates.TemplateResponse(
        request=request,
        name="change_password.html",
        context={
            "rules_lead_in": RULES_LEAD_IN,
            "rule_phrases": RULE_PHRASES,
            "password_min_bytes": PASSWORD_MIN_BYTES,
            "password_max_bytes": PASSWORD_MAX_BYTES,
        },
    )

@app.get("/admin/home", include_in_schema=False, dependencies=[Depends(require_page_session)])
async def serve_admin_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="admin.html", headers=NO_STORE)

@app.get("/admin/archive", include_in_schema=False, dependencies=[Depends(require_page_session)])
async def serve_admin_archive(request: Request):
    return templates.TemplateResponse(request=request, name="archive.html", headers=NO_STORE)

@app.get("/admin/applicants", include_in_schema=False, dependencies=[Depends(require_page_session)])
async def serve_admin_applicants(request: Request):
    # Shell only (section 8): no data is fetched yet.
    return templates.TemplateResponse(request=request, name="admin_applicants.html", headers=NO_STORE)

@app.get("/admin/forms/{form_id}", include_in_schema=False, dependencies=[Depends(require_page_session)])
async def serve_admin_form_detail(request: Request, form_id: str):
    # Shell only (section 8): form_id is accepted but not used to fetch data yet.
    return templates.TemplateResponse(request=request, name="admin_form_detail.html", headers=NO_STORE)

@app.get("/admin/brands/{brand_id}", include_in_schema=False, dependencies=[Depends(require_page_session)])
async def serve_admin_brand_detail(request: Request, brand_id: str):
    # Shell only (section 8): brand_id is accepted but not used to fetch data yet.
    return templates.TemplateResponse(request=request, name="admin_brand_detail.html", headers=NO_STORE)

@app.get("/admin/users", include_in_schema=False, dependencies=[Depends(require_page_session), Depends(require_page_roles(ROLE_SUPERADMIN, ROLE_MANAGER))])
async def serve_admin_users(request: Request):
    # Shell only (section 8): no data is fetched yet. Role check: SUPERADMIN and MANAGER allowed, RECRUITER gets 403 (API_CONTRACT.md).
    return templates.TemplateResponse(request=request, name="admin_users.html", headers=NO_STORE)

@app.get("/admin", include_in_schema=False, dependencies=[Depends(require_page_session)])
@app.get("/admin/{rest:path}", include_in_schema=False, dependencies=[Depends(require_page_session)])
async def admin_unknown_path(request: Request, rest: str = ""):
    # Signed out: redirected to /login by the dependency (does not reveal which URLs exist). Signed in: normal 404.
    raise HTTPException(status_code=404, detail="Not Found")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
