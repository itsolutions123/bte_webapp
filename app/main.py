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
from app.routers import admin_mrf
from app.routers import admin_metrics
app.include_router(admin_mrf.router, prefix="/api/v1/admin", tags=["Admin MRF"], dependencies=[Depends(get_current_user)])
# Recruiters metrics endpoints (docs/API_CONTRACT.md, /api/v1/admin/metrics); each endpoint sets its own role guard.
app.include_router(admin_metrics.router, prefix="/api/v1/admin", tags=["Admin Metrics"], dependencies=[Depends(get_current_user)])
# MRF portal API: its own prefix, NO get_current_user (sign-up is public; the portal never uses the admin session).
from app.routers import mrf
app.include_router(mrf.router, prefix="/api/v1/mrf", tags=["MRF"])

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

from app.roles import ROLE_SUPERADMIN, ROLE_MANAGER, ROLE_RECRUITER
from app.password_rules import RULES_LEAD_IN, RULE_PHRASES, PASSWORD_MIN_BYTES, PASSWORD_MAX_BYTES
from app.mrf_lists import DEPARTMENTS, MRF_ASSIGNMENTS, MRF_CLASSIFICATION_OPTIONS, MRF_REQUEST_STATUSES, MRF_REQUEST_STATUS_TRANSITIONS, POSITIONS
from app.routers.mrf import get_current_mrf_user

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

class MrfLoginRedirect(Exception):
    # Raised by require_mrf_page_session when an /mrf page is requested without a valid portal session.
    pass

@app.exception_handler(MrfLoginRedirect)
async def mrf_login_redirect_handler(request: Request, exc: MrfLoginRedirect):
    return RedirectResponse(url="/mrf/login", status_code=302, headers=NO_STORE)

async def require_mrf_page_session(request: Request, db: AsyncSession = Depends(get_db)):
    # Portal page guard (docs/API_CONTRACT.md, part 61): same check as the portal API (get_current_mrf_user,
    # mrf_session_id cookie only); pages redirect to /mrf/login instead of returning 401 JSON.
    # get_current_mrf_user keeps the signed-in user on request.state.mrf_user.
    try:
        await get_current_mrf_user(request, db)
    except HTTPException:
        raise MrfLoginRedirect()

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

@app.get("/mrf/login", include_in_schema=False)
async def serve_mrf_login_page(request: Request):
    # MRF portal login, SHELL only (section 8): static page, no session check and no submit wiring yet.
    # Separate from /admin: the portal has its own layout and, once wired, its own mrf_session_id cookie.
    return templates.TemplateResponse(request=request, name="mrf/login.html", headers=NO_STORE)

def mrf_footer_context(request: Request) -> dict:
    # Portal footer name and initials (API_CONTRACT.md, part 62).
    # Reads request.state.mrf_user, set by get_current_mrf_user
    # inside require_mrf_page_session. Empty name keeps placeholders.
    user = getattr(request.state, "mrf_user", None)
    first = str(getattr(user, "first_name", "") or "").strip()
    last = str(getattr(user, "last_name", "") or "").strip()
    full_name = (first + " " + last).strip()
    if full_name == "":
        return {"footer_name": "Signed-in user", "footer_initials": "--"}
    initials = (first[:1] + last[:1]).upper()
    return {
        "footer_name": full_name,
        "footer_initials": initials or "--",
    }

def admin_sidebar_context(request: Request) -> dict:
    # Admin sidebar profile pill, server-rendered (API_CONTRACT.md, GET /api/v1/admin/me
    # Call site, part 63). Reads request.state.user, set by get_current_user inside
    # require_page_session. Initials: first letters of the first and last words of
    # full_name (same rule GET /api/v1/admin/me documents); email shown as the name
    # and its first letter as the initial when full_name is empty/null.
    user = getattr(request.state, "user", None)
    full_name = str(getattr(user, "full_name", "") or "").strip()
    email = str(getattr(user, "email", "") or "").strip()
    role = str(getattr(user, "role", "") or "")
    if full_name:
        words = full_name.split()
        pill_name = full_name
        pill_initials = (words[0][:1] + words[-1][:1]).upper()
    else:
        pill_name = email
        pill_initials = email[:1].upper() if email else ""
    return {
        "pill_name": pill_name,
        "pill_initials": pill_initials,
        "pill_role": role,
    }

@app.get("/mrf/requests", include_in_schema=False, dependencies=[Depends(require_mrf_page_session)])
async def serve_mrf_requests_page(request: Request):
    # MRF portal My Requests, SHELL only (section 8): static page with placeholder content.
    # Requires a valid portal session (require_mrf_page_session); otherwise redirects to /mrf/login.
    return templates.TemplateResponse(
        request=request,
        name="mrf/requests.html",
        context=mrf_footer_context(request),
        headers=NO_STORE,
    )

@app.get("/mrf/signup", include_in_schema=False)
async def serve_mrf_signup_page(request: Request):
    # MRF portal sign-up, SHELL only (section 8): static page, no session check and no submit wiring yet.
    # Position and Department options come from app/mrf_lists.py (single source of truth).
    return templates.TemplateResponse(
        request=request,
        name="mrf/signup.html",
        context={"departments": DEPARTMENTS, "positions": POSITIONS},
        headers=NO_STORE,
    )

@app.get("/mrf/forms", include_in_schema=False, dependencies=[Depends(require_mrf_page_session)])
async def serve_mrf_forms_page(request: Request):
    # MRF portal Forms list, SHELL only (section 8): static page with placeholder rows.
    # Requires a valid portal session (require_mrf_page_session); otherwise redirects to /mrf/login.
    return templates.TemplateResponse(
        request=request,
        name="mrf/forms.html",
        context=mrf_footer_context(request),
        headers=NO_STORE,
    )

@app.get("/mrf/forms/{form_id}", include_in_schema=False, dependencies=[Depends(require_mrf_page_session)])
async def serve_mrf_wizard_page(request: Request, form_id: str):
    # MRF portal request wizard, SHELL only (section 8): static page with placeholder content.
    # form_id is not used yet; the wiring step fetches GET /api/v1/mrf/forms/{form_id} client-side.
    # Requires a valid portal session (require_mrf_page_session); otherwise redirects to /mrf/login.
    # mrf_user_id (API_CONTRACT.md, wizard page context key, part 75): the signed-in user's own id as text,
    # from request.state.mrf_user (set by the session guard). Empty string if there is no user.
    context = mrf_footer_context(request)
    mrf_user = getattr(request.state, "mrf_user", None)
    context["mrf_user_id"] = str(mrf_user.id) if mrf_user is not None else ""
    return templates.TemplateResponse(
        request=request,
        name="mrf/wizard.html",
        context=context,
        headers=NO_STORE,
    )

@app.get("/admin/home", include_in_schema=False, dependencies=[Depends(require_page_session)])
async def serve_admin_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="admin.html", context=admin_sidebar_context(request), headers=NO_STORE)

@app.get("/admin/archive", include_in_schema=False, dependencies=[Depends(require_page_session)])
async def serve_admin_archive(request: Request):
    return templates.TemplateResponse(request=request, name="archive.html", context=admin_sidebar_context(request), headers=NO_STORE)

@app.get("/admin/applicants", include_in_schema=False, dependencies=[Depends(require_page_session)])
async def serve_admin_applicants(request: Request):
    # Shell only (section 8): no data is fetched yet.
    return templates.TemplateResponse(request=request, name="admin_applicants.html", context=admin_sidebar_context(request), headers=NO_STORE)

@app.get("/admin/candidates", include_in_schema=False, dependencies=[Depends(require_page_session)])
async def serve_admin_candidates(request: Request):
    # Shell only (section 8): placeholder rows, no data is fetched yet.
    return templates.TemplateResponse(request=request, name="admin_candidates.html", context=admin_sidebar_context(request), headers=NO_STORE)

@app.get("/admin/forms/{form_id}", include_in_schema=False, dependencies=[Depends(require_page_session)])
async def serve_admin_form_detail(request: Request, form_id: str):
    # Shell only (section 8): form_id is accepted but not used to fetch data yet.
    return templates.TemplateResponse(request=request, name="admin_form_detail.html", context=admin_sidebar_context(request), headers=NO_STORE)

@app.get("/admin/brands/{brand_id}", include_in_schema=False, dependencies=[Depends(require_page_session)])
async def serve_admin_brand_detail(request: Request, brand_id: str):
    # Shell only (section 8): brand_id is accepted but not used to fetch data yet.
    return templates.TemplateResponse(request=request, name="admin_brand_detail.html", context=admin_sidebar_context(request), headers=NO_STORE)

@app.get("/admin/users", include_in_schema=False, dependencies=[Depends(require_page_session), Depends(require_page_roles(ROLE_SUPERADMIN, ROLE_MANAGER))])
async def serve_admin_users(request: Request):
    # Shell only (section 8): no data is fetched yet. Role check: SUPERADMIN and MANAGER allowed, RECRUITER gets 403 (API_CONTRACT.md).
    return templates.TemplateResponse(request=request, name="admin_users.html", context=admin_sidebar_context(request), headers=NO_STORE)

@app.get("/admin/metrics/recruiters", include_in_schema=False, dependencies=[Depends(require_page_session), Depends(require_page_roles(ROLE_SUPERADMIN, ROLE_MANAGER))])
async def serve_admin_metrics_recruiters(request: Request):
    # Recruiters metrics, SHELL only (section 8): placeholder content, no data is fetched yet.
    # Role check: SUPERADMIN and MANAGER allowed, RECRUITER gets 403 (the same guard as /admin/mrf).
    return templates.TemplateResponse(request=request, name="admin_recruiters.html", context={**admin_sidebar_context(request), "rec_can_edit_points": getattr(getattr(request.state, "user", None), "role", "") == ROLE_SUPERADMIN}, headers=NO_STORE)

@app.get("/admin/mrf", include_in_schema=False, dependencies=[Depends(require_page_session), Depends(require_page_roles(ROLE_SUPERADMIN, ROLE_MANAGER))])
async def serve_admin_mrf(request: Request):
    # Admin MRF section, SHELL only (section 8): static page with placeholder rows, no data fetched yet.
    # Role check: SUPERADMIN and MANAGER allowed, RECRUITER gets 403 (API_CONTRACT.md section 5).
    return templates.TemplateResponse(request=request, name="admin_mrf.html", context={**MRF_ADMIN_SUBMISSIONS_CONTEXT, **admin_sidebar_context(request)}, headers=NO_STORE)

# MRF admin tab addresses (DECIDED 2026-11-12, part 42): each opens the same page with that tab selected.
# Same guard as /admin/mrf (SUPERADMIN and MANAGER, RECRUITER gets 403). Registered here, above the /admin catch-alls.
MRF_ADMIN_TABS = ("submissions", "forms", "users")

# Submissions tab filter options come from app/mrf_lists.py (single source of truth; part 79, step E).
MRF_ADMIN_SUBMISSIONS_CONTEXT = {
    "mrf_request_statuses": MRF_REQUEST_STATUSES,
    # Allowed next statuses per current status (one source of truth: app/mrf_lists.py); the review modal reads this, no rule in JS.
    "mrf_request_status_transitions": {k: list(v) for k, v in MRF_REQUEST_STATUS_TRANSITIONS.items()},
    # Role of the users the review modal can credit as recruiter (one source: app/roles.py; docs/API_CONTRACT.md PATCH .../recruiter).
    "mrf_recruiter_role": ROLE_RECRUITER,
    "mrf_classifications": MRF_CLASSIFICATION_OPTIONS,
    "mrf_departments": DEPARTMENTS,
}

def _make_mrf_tab_page(tab: str):
    async def serve_admin_mrf_tab(request: Request):
        return templates.TemplateResponse(request=request, name="admin_mrf.html", context={"initial_tab": tab, **MRF_ADMIN_SUBMISSIONS_CONTEXT, **admin_sidebar_context(request)}, headers=NO_STORE)
    return serve_admin_mrf_tab

for _mrf_tab in MRF_ADMIN_TABS:
    app.add_api_route(
        f"/admin/mrf/{_mrf_tab}",
        _make_mrf_tab_page(_mrf_tab),
        methods=["GET"],
        include_in_schema=False,
        dependencies=[Depends(require_page_session), Depends(require_page_roles(ROLE_SUPERADMIN, ROLE_MANAGER))],
    )

# MRF single-form page (DECIDED 2026-11-12, part 42; page SHELL, part 43 step 4.2, option A): form_id is accepted but not used to fetch data yet.
# Same guard as the tab addresses above. Registered here, above the /admin catch-alls.
@app.get("/admin/mrf/forms/{form_id}", include_in_schema=False, dependencies=[Depends(require_page_session), Depends(require_page_roles(ROLE_SUPERADMIN, ROLE_MANAGER))])
async def serve_admin_mrf_form(request: Request, form_id: str):
    # The Set assignment dropdown items are rendered from MRF_ASSIGNMENTS (part 59, pD-1 option B), so the page holds no copy of the names.
    return templates.TemplateResponse(request=request, name="admin_mrf_form.html", context={"assignments": MRF_ASSIGNMENTS, **admin_sidebar_context(request)}, headers=NO_STORE)

@app.get("/admin", include_in_schema=False, dependencies=[Depends(require_page_session)])
@app.get("/admin/{rest:path}", include_in_schema=False, dependencies=[Depends(require_page_session)])
async def admin_unknown_path(request: Request, rest: str = ""):
    # Signed out: redirected to /login by the dependency (does not reveal which URLs exist). Signed in: normal 404.
    raise HTTPException(status_code=404, detail="Not Found")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
