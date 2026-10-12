from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import public

app = FastAPI(title="BTE Careers API")

# Mount Routers
# Note: Admin endpoints will require HR authentication middleware (coordinated with Security Gem)
from app.routers import public
app.include_router(public.router, prefix="/api/v1/public", tags=["Public"])
from app.routers import admin
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])

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
    return templates.TemplateResponse(request=request, name="apply.html", context={"job": {"id": job_id}})

@app.get("/careers", include_in_schema=False)
async def serve_careers_board(request: Request):
    return templates.TemplateResponse(request=request, name="careers.html")

@app.get("/admin", include_in_schema=False)
async def serve_admin_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="admin.html")

@app.get("/health")
async def health_check():
    return {"status": "ok"}
