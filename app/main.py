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
# Note: Admin endpoints will require HR authentication middleware (coordinated with Security Gem)
from app.routers import public
app.include_router(public.router, prefix="/api/v1/public", tags=["Public"])
from app.routers import admin
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
from app.routers import auth
app.include_router(auth.router, prefix="/api/v1/admin", tags=["Auth"])

from fastapi import Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os

# Set up templates & static
base_dir = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(base_dir, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(base_dir, "static")), name="static")

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

@app.get("/admin/home", include_in_schema=False)
async def serve_admin_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="admin.html")

@app.get("/admin/archive", include_in_schema=False)
async def serve_admin_archive(request: Request):
    return templates.TemplateResponse(request=request, name="archive.html")

@app.get("/admin/applicants", include_in_schema=False)
async def serve_admin_applicants(request: Request):
    # Shell only (section 8): no data is fetched yet.
    return templates.TemplateResponse(request=request, name="admin_applicants.html")

@app.get("/admin/forms/{form_id}", include_in_schema=False)
async def serve_admin_form_detail(request: Request, form_id: str):
    # Shell only (section 8): form_id is accepted but not used to fetch data yet.
    return templates.TemplateResponse(request=request, name="admin_form_detail.html")

@app.get("/admin/brands/{brand_id}", include_in_schema=False)
async def serve_admin_brand_detail(request: Request, brand_id: str):
    # Shell only (section 8): brand_id is accepted but not used to fetch data yet.
    return templates.TemplateResponse(request=request, name="admin_brand_detail.html")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
