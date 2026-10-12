# Project State: BTE Careers (ATS)

**Last Updated:** 2026-10-13
**Status:** Admin UI Redesigned & Admin API Wired

## Infrastructure & Environment
- **Host:** ansible-srv (10.0.10.37)
- **Directory:** `~/bte_webapp`
- **Containers Running:**
  - `bte_careers_db` (Postgres 15 Alpine, Port 5432, bound to 127.0.0.1 only) - Resource Limits: 1.0 vCPU / 512MB RAM
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

## Scope & Build Order (Gem Prompts v4)
- Local-only: app runs at 10.0.10.37:8000 on the LAN. The bte_website cross-app work is paused.
- Build order is UI/UX shell first (placeholder content only), then one data feature at a time.
- Dev loop (verified 2026-10-12): docker-compose.yml runs uvicorn with --reload and mounts `.:/app`, so template and code edits apply without a rebuild.
- Step 1 done (2026-10-12): removed the fake forms fallback list and `mockBrands` from app/templates/admin.html. Empty states now show "No forms yet" and "No brand data yet".

## Decisions Recorded (2026-10-12)
- Admin Brands and Forms are admin-managed modules, each with a "+" button to create entries.
- A form is a shared, named template. Many jobs can use one form (`jobs.form_id`), and a job uses at most one. This REPLACES the earlier strict 1:1 decision.
- The applicant picks a job from the posting on the website and answers that job's form.
- For now there is ONE form, the "General Form", used by the crew and store jobs. Role-specific forms (e.g. "IT Recruitment") come later; the model already supports them. Nothing is seeded: the General Form is created with the "+" button.
- Jobs are attached to a form from the form's own page (`PUT /forms/{form_slug}/jobs/{job_id}`). `jobs` has no role-category field, so "crew and store" is chosen by the admin, not automatically.
- Questions belong to the form: `job_questions.form_id` replaces `job_id` (table name kept for now).
- Components are a fixed set of field types: Yes/No, Multiple choice A-D (four options written by the admin) and Open ended (free text, collected only, never scored).
- Answer points (the admin cheat sheet): each Yes/No or A-D answer choice carries admin-set points to a BRAND (Pares Retiro, Sandwich Guy, Sapporo) or to FAIL. Stored in the new `answer_points` table.
- FAIL points REPLACE `expected_answer`. Score = percent of scored questions (Yes/No and A-D) whose chosen answer has no FAIL row. Open ended is excluded from the divisor. A hard-requirement question whose chosen answer has a FAIL row sets the fail flag and status FAILED. `pass_threshold` and `pooling_threshold` work as before.
- Suggested fit is brand-level: brand points are summed per application (`applications.brand_points`). The brand with the highest total above 0 is the suggestion. A tie shows all tied brands with a flag like "suited for both ...". No brand points means no flag. The flag never changes the score or status.
- ASSUMPTIONS awaiting confirmation: Open ended answers award no points; every scored question must be answered to submit.
- `parameters` table is kept as LEGACY and `job_questions.parameter_id` becomes nullable. Retiring it is a separate confirmed step.
- The form editor saves as you go (one call per action: create, rename, add, edit, delete, reorder question). Question type is fixed after creation. Deleting a question with applicant answers returns 409. Renaming a form keeps its slug.
- A form's submissions are the applications for the jobs that use it (`GET /api/v1/admin/applications?form_id=`).
- Resume upload stays a fixed step of every application. No File upload component in this version.
- Apply wizard layout reference: progress bar, question heading, question text, options, Previous/Next (wireframe provided by user).
- `display_order` and the `slug` columns are in SCHEMA.md and `app/models.py` and are committed (2451ad7).
- Docs are current for these decisions: docs/SCHEMA.md (119 lines) and docs/API_CONTRACT.md (183 lines, section 3 marked PLANNED).
- Admin page routes (decided 2026-10-12): Dashboard `/admin/home`; Applicants list `/admin/applicants` and detail `/admin/applicants/{applicant-UID}`; Brands `/admin/brands/{brand-UID}`; Forms `/admin/forms/{form-UID}`. Page URLs use UIDs, not names or slugs; slug columns stay. This replaces `{brand-name}`/`{form-name}` from the v4 preamble and the `{form_slug}`/`{application_id}` page-route text in the docs (the contract's page-route section is not yet reconciled).
- Applicants list shows full name, address, age and gender; every other form field shows only when the admin opens an applicant. One "Full Name" column is assumed (the wireframe shows first and last name).
- Applicants module stays a placeholder shell for now. Its fields come from form answers once forms exist; `Applicant` has only first_name, last_name, email and phone.
- Forms creation is built first so it can be tested. The Applicants page waits.

## Decisions Recorded (2026-10-13)
- Schema-change mechanism: option A. Plain SQL files in `migrations/NNN_*.sql`, applied with docker exec into bte_careers_db, non-destructive and idempotent where possible. Applied so far: 001 (`forms` table with unique `ix_forms_slug`) and 002 (nullable `jobs.form_id`, FK to `forms`, `idx_jobs_form_id`).
- Admin Forms page URL uses the form id: `/admin/forms/{form-UID}` (confirmed again 2026-10-13).
- Applicant flow, served by bte_webapp on :8000 for now: job landing page `/careers/jobs/{job-UID}` (job UID is `jobs.id`) shows the instructions; the form page is `/careers/jobs/{job-UID}/forms/{form-UID}`. The job travels in the path because many jobs share a form, and the server must check that the form belongs to that job (`jobs.form_id`). These routes are not yet in API_CONTRACT.md.
- Deployment layout: website on 10.0.10.37:8086 and webapp on 10.0.10.37:8000 (same VM, separate containers). Later plan, OUT OF SCOPE while local-only: website at bigtimeempire.com fetching job data from the webapp, webapp admin at ats.bigtimeempire.com/admin. The apply flow uses relative URLs so that move needs no code change.
- Security incident (2026-10-12/13): GitGuardian flagged the fallback DB password in docker-compose.yml. Cause: `DB_PASSWORD` was unset in `.env`, so the live DB ran on the stock default, and Postgres 5432 was published on all interfaces. Fixed: DB role password rotated; `DB_PASSWORD` is required in docker-compose.yml (no fallback); `app/database.py` has no `DATABASE_URL` fallback; 5432 is bound to 127.0.0.1. Committed in ab9bae3. Postgres trusts loopback connections inside its container, so password checks must go over the network (`-h db`). Remaining: mark the GitGuardian alert resolved from its dashboard, and add `DB_PASSWORD` to `.env.example`.

## OPEN Decisions
- `/admin` vs `/admin/home`: Dashboard is `/admin/home` (decided 2026-10-12). Assumed `/admin` stays as an alias; not yet confirmed.
- Should jobs with no form be hidden from the public jobs board? The contract currently returns an empty question list from `/questions` and 409 from `/apply`, a dead end for applicants. Only crew and store jobs will have a form for now.
- How jobs get created: no job-creation endpoint exists. The contract only adds `GET /admin/jobs` (a picker for attaching jobs to a form).
- Wireframe progress bar says 15/25 on "Question 16": does the bar count answered questions or the current position?
- Yes/No wizard layout (the wireframe only shows four options).
- Migration: existing `job_questions` rows (job_id, expected_answer) must become forms, form_id and FAIL rows. Dropping the old columns is destructive and needs explicit confirmation.
- Security: the sample Open ended question about mental health (sensitive data under RA 10173): example only, or does it need extra consent and retention rules?
- Security: `consent_agreed` defaults to True in `app/models.py`; consent should be explicit.
- Security: admin endpoints have no auth check in code (the sidebar endpoint depends only on get_db), although the contract requires HR authentication.
- Schema-change mechanism: DECIDED 2026-10-13, option A (plain SQL files in `migrations/NNN_*.sql`). The 8 original tables still have no baseline in the repo.
- First forms slice: the `forms` table (001) and `jobs.form_id` (002) are live (2026-10-13). Form list and create (contract, then shell, then wiring) come next. The `job_questions` migration is split: add nullable columns, backfill, tighten, and drop `job_id` and `expected_answer` last with explicit confirmation. Row counts of jobs, job_questions, applications and answers are still needed to decide whether a backfill is required.
- Admin form endpoints: use the form id instead of `form_slug` (`/api/v1/admin/forms/{form_id}/...`)? Recommended, not yet confirmed; needs a contract edit (API_CONTRACT.md lines 98-151).
- Public applicant routes and the form-questions endpoint by form id still need recording in API_CONTRACT.md (Structure handoff pending).
- Which form questions feed the Applicants list columns (full name, address, age, gender).

## Known Mismatches (verified 2026-10-12)
- The `forms` table and `jobs.form_id` are live (migrations 001 and 002, applied 2026-10-13). `answer_points` does not exist yet, and `job_questions` still has the old shape (`job_id`, `expected_answer`, NOT NULL `parameter_id`; no `form_id`, `question_type` or `options`). Until the questions move, a "form" in practice is the set of `job_questions` rows under one job.
- `app/models.py` JobQuestion still has `job_id`, a NOT NULL `parameter_id` and a NOT NULL `expected_answer`, and no `question_type` or `options`.
- The matching engine in `POST /apply` (app/routers/public.py, lines 98-258) scores with `expected_answer` (line 182). It must be rewritten for answer points, required answers and brand points, as its own contract-first step.
- `GET /api/v1/public/jobs/{job_id}/questions` returns no question type or options.
- `app/main.py` serves only `/admin`. `/admin/home`, `/admin/brands/...`, `/admin/forms/...` and `/admin/applicants/...` are not implemented.
- The contract lists admin application endpoints (list, detail, status patch, resume) that are not in `app/routers/admin.py`.
- Route param naming differs: the v4 preamble says `{UID}`, the contract says `{application_id}`.
- The sidebar `forms` list is filled from the legacy `parameters` table (app/routers/admin.py), not a forms table.
- Bugs in `POST /apply` (not fixed): a rejected job lookup leaves an orphaned PDF on disk; an unanswered hard-requirement question never sets the fail flag; invalid `answers` JSON and unknown question ids are silently ignored. The contract now requires 422 for these.
- Hardcodes: brand `code` is `name[:3].upper()` with a "BTE" schema default; `consent_agreed` defaults True and `terms_version` defaults "v1.0" in app/models.py; in `POST /apply` the 5 MB limit, the default `/data/resumes` path (docker-compose.yml:27 mounts `./data/resumes` to `/app/data/resumes`; whether an env var overrides the default is UNVERIFIED), the 8192 chunk size, the status strings, and a score of 100 for a form with no questions.
- Cosmetic duplicates (committed in 2451ad7): `Parameter, Parameter` and `SidebarFormItem, SidebarFormItem` imports in admin.py; `slug: str` twice in SidebarBrandItem and SidebarFormItem in schemas.py.
- Indexes in SCHEMA.md but not in app/models.py: `idx_jq_form_order`, `idx_jobs_form_id`, `idx_answer_points_question_id`, `idx_answers_application_id`.
- Dashboard (app/templates/admin.html): the Dashboard, Applicants, brand and form sidebar links are `href="#"` and the two "+" markers are plain spans, so nothing opens yet.
- Dashboard brand cards read `summaryData.brand_matches` (`name`, `matches`), but the contract says `brand_summaries` (`brand_name`, `top_matches_count`). Which side is wrong is UNVERIFIED (the dashboard/summary code in admin.py has not been read).
- Dashboard pass rate shows 0% with "0/1" while every count is 0. A denominator of 1 looks like a fallback value (UNVERIFIED, code not read).
- Security: admin.html puts brand and form names into `innerHTML` unescaped in the sidebar fetch code. This needs escaping before the "+" create buttons exist.
- Docs are ahead of code: SCHEMA.md and API_CONTRACT.md section 3 have no model or endpoint behind them yet.
- The 8 original tables (answers, applicants, applications, brands, job_questions, jobs, parameters, status_counts) were created outside the repo and have no baseline, so a fresh db still cannot be rebuilt from the repo. Changes since 2026-10-13 live in `migrations/` (001 forms, 002 jobs.form_id); `app/database.py` only builds the engine.
- RESOLVED 2026-10-13: the `DATABASE_URL` fallback in `app/database.py` and the `DB_PASSWORD` fallbacks in docker-compose.yml are removed (see the security incident under Decisions Recorded 2026-10-13). Fixed non-secret defaults remain for `DB_USER` and `DB_NAME` in compose. Still UNVERIFIED: `RESUME_STORAGE_PATH` is read in public.py line 127 (default `/data/resumes`); whether compose sets it.
- `Applicant` (models.py line 35) has only first_name, last_name, email and phone: no age, gender or address.
- Cosmetic in app/main.py: unused `CORSMiddleware` import and `from app.routers import public` imported twice.

## Next Steps
1. DONE: docs and the slug, display_order and consent code are committed (2451ad7). The admin.html mock-data removal and these doc updates are committed on 2026-10-12 after that.
   Done 2026-10-13: schema-change mechanism decided (option A), migrations 001 and 002 applied, DB password incident fixed (committed in ab9bae3). Next: check row counts, then the forms-creation slice (contract for the admin forms endpoints, id vs slug; then shell, form list, form create).
2. Security: decide admin auth and review the Open ended sensitive-data example.
3. Design: build the Brands and Forms page shells with "+" buttons using placeholder content only, plus the apply wizard layouts (Yes/No, A-D, Open ended).
4. Structure/API: migration plan for forms, answer_points and `jobs.form_id` (contract-first, destructive steps confirmed).
5. Wire one feature at a time: form list, form create, question editor, answer points, attach jobs, submissions, then the matching engine rewrite.
