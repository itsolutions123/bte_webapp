# Project State: BTE Careers (ATS)

**Last Updated:** 2026-10-12
**Status:** Scaffolding & Container Infrastructure Complete

## Infrastructure & Environment
- **Host:** ansible-srv (10.0.10.37)
- **Directory:** `~/bte_webapp`
- **Containers Running:**
  - `bte_careers_db` (Postgres 15 Alpine, Port 5432) - Resource Limits: 1.0 vCPU / 512MB RAM
  - `bte_careers_web` (FastAPI + Uvicorn, Port 8000) - Resource Limits: 0.5 vCPU / 256MB RAM
- **Resume Storage Path:** `./data/resumes/` (mounted at `/app/data/resumes`)

## Verified Active Endpoints
- `GET /health` -> 200 OK (`{"status":"ok"}`)
- `GET /careers` -> 200 OK (renders `careers.html`)
- `GET /apply` -> 200 OK (renders `apply.html`)

## Key Technical Decisions & Fixes
- Async database stack using `sqlalchemy[asyncio]` and `greenlet`.
- Server-rendered Jinja2 templates using Starlette-compliant `TemplateResponse(request=request, name=...)` signature.
- Removed obsolete `version` tag from `docker-compose.yml`.

## Next Steps
- Handoff to **API Gem** to implement SQLAlchemy models (`app/models.py`) and backend endpoint logic for public apply flow and admin dashboard.
