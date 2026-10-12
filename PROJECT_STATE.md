# Project State: BTE Careers (ATS)

**Last Updated:** 2026-10-12
**Status:** Admin UI Redesigned & Admin API Wired

## Infrastructure & Environment
- **Host:** ansible-srv (10.0.10.37)
- **Directory:** `~/bte_webapp`
- **Containers Running:**
  - `bte_careers_db` (Postgres 15 Alpine, Port 5432) - Resource Limits: 1.0 vCPU / 512MB RAM
  - `bte_careers_web` (FastAPI + Uvicorn, Port 8000) - Resource Limits: 0.5 vCPU / 256MB RAM
- **Resume Storage Path:** `./data/resumes/` (mounted at `/app/data/resumes`)

## Verified Active Endpoints
- `GET /health` -> 200 OK
- `GET /careers` -> 200 OK
- `GET /apply` -> 200 OK
- `GET /admin` -> 200 OK (renders `admin.html` with dark mode redesign)
- `GET /api/v1/admin/metadata/sidebar` -> 200 OK
- `GET /api/v1/admin/dashboard/summary` -> 200 OK
- `GET /api/v1/admin/dashboard/tally` -> 200 OK

## Key Technical Decisions & Fixes
- Async database stack using `sqlalchemy[asyncio]` and `greenlet`.
- Server-rendered Jinja2 templates using Starlette-compliant `TemplateResponse`.
- Admin UI driven by vanilla JS `fetch()` polling to dedicated async API endpoints, strictly avoiding hardcoded business data.
- Admin dashboard styled with custom CSS matching the dark mode visual reference.

## Next Steps
- Handoff to **Structure / API Gem** to finalize the cross-app schema (such as question ordering and slug support) and implement the public job board and one-question-at-a-time apply wizard.
