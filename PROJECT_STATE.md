# Project State: BTE Careers (ATS)

**Last Updated:** 2026-10-13
**Status:** Admin UI Redesigned & Admin API Wired -- Form creation (name-only) live end-to-end

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
- `POST /api/v1/admin/forms` -> 201 Created (verified 2026-10-13)

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
- Admin page routes (decided 2026-10-12): Dashboard `/admin/home`; Applicants list `/admin/applicants` and detail `/admin/applicants/{applicant-UID}`; Brands `/admin/brands/{brand-UID}`; Forms `/admin/forms/{form-UID}`. Page URLs use UIDs, not names or slugs; slug columns stay. This replaces `{brand-name}`/`{form-name}` from the v4 preamble and the `{form_slug}`/`{application_id}` page-route text in the docs (the contract's forms page route was reconciled on 2026-10-13; the brand and applicant page routes still say `{brand_slug}` and `{application_id}`).
- Applicants list shows full name, address, age and gender; every other form field shows only when the admin opens an applicant. One "Full Name" column is assumed (the wireframe shows first and last name).
- Applicants module stays a placeholder shell for now. Its fields come from form answers once forms exist; `Applicant` has only first_name, last_name, email and phone.
- Forms creation is built first so it can be tested. The Applicants page waits.

## Decisions Recorded (2026-10-13)
- Schema-change mechanism: option A. Plain SQL files in `migrations/NNN_*.sql`, applied with docker exec into bte_careers_db, non-destructive and idempotent where possible. Applied so far: 001 (`forms` table with unique `ix_forms_slug`) and 002 (nullable `jobs.form_id`, FK to `forms`, `idx_jobs_form_id`).
- Admin Forms page URL uses the form id: `/admin/forms/{form-UID}` (confirmed again 2026-10-13).
- Applicant flow, served by bte_webapp on :8000 for now: job landing page `/careers/jobs/{job-UID}` (job UID is `jobs.id`) shows the instructions; the form page is `/careers/jobs/{job-UID}/forms/{form-UID}`. The job travels in the path because many jobs share a form, and the server must check that the form belongs to that job (`jobs.form_id`). These routes are not yet in API_CONTRACT.md.
- Deployment layout: website on 10.0.10.37:8086 and webapp on 10.0.10.37:8000 (same VM, separate containers). Later plan, OUT OF SCOPE while local-only: website at bigtimeempire.com fetching job data from the webapp, webapp admin at ats.bigtimeempire.com/admin. The apply flow uses relative URLs so that move needs no code change.
- Security incident (2026-10-12/13): GitGuardian flagged the fallback DB password in docker-compose.yml. Cause: `DB_PASSWORD` was unset in `.env`, so the live DB ran on the stock default, and Postgres 5432 was published on all interfaces. Fixed: DB role password rotated; `DB_PASSWORD` is required in docker-compose.yml (no fallback); `app/database.py` has no `DATABASE_URL` fallback; 5432 is bound to 127.0.0.1. Committed in ab9bae3. Postgres trusts loopback connections inside its container, so password checks must go over the network (`-h db`). Remaining: mark the GitGuardian alert resolved from its dashboard, and add `DB_PASSWORD` to `.env.example`.
- Admin forms endpoints are keyed by form id (`/api/v1/admin/forms/{form_id}/...`) and the page route is `/admin/forms/{form_id}`; recorded in API_CONTRACT.md on 2026-10-13 (section 3 still PLANNED). The slug stays a response field and is used only in public paths.
- Row counts 2026-10-13: jobs, job_questions, applications and answers are all empty, so the `job_questions` reshape needs no backfill. Remaining schema work is HELD until the question editor step: migration 003 (job_questions: form_id, question_type, options, nullable parameter_id, idx_jq_form_order), 004 (answer_points and its index), 005 (applications.brand_points, answers.is_passed nullable, idx_answers_application_id), and dropping `job_id` and `expected_answer` last with explicit confirmation. The drop breaks `GET /api/v1/public/jobs/{job_id}/questions` and `POST /apply` until they are rewritten for forms.
- Form Builder modal shipped (admin.html, FORMS "+", committed cab1a44): editable form name, drag-and-drop element palette (Yes/No, Open-ended, Multiple Choice -- Checkbox excluded by decision), drop zone is visual-only for now (dragged elements are not yet persisted as questions -- no question-text/options/answer-points UI exists yet). Save calls `POST /api/v1/admin/forms` with the name, shows a Bootstrap toast on success, and refreshes the sidebar.
- Bug found and fixed 2026-10-13: the inline `<script>` in admin.html originally ran before the modal/toast markup existed in the DOM (script tag preceded that markup in source order), so `document.getElementById(...).addEventListener` threw on page load and silently broke the Save button after a fresh reload. Fixed by wrapping the modal-dependent JS in a `DOMContentLoaded` listener.
- `GET /api/v1/admin/metadata/sidebar` now reads the `forms` table instead of the legacy `parameters` table (resolves the Known Mismatch recorded 2026-10-12, see below).

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
- First forms slice: the `forms` table (001) and `jobs.form_id` (002) are live (2026-10-13). Form list and create (contract, then shell, then wiring) come next. The `job_questions` migration is a clean reshape (no data), with the `job_id` and `expected_answer` drops last and explicitly confirmed. Row counts are all 0 (2026-10-13), so no backfill is needed; the reshape is held until the question editor step.
- Admin form endpoints: DECIDED 2026-10-13, keyed by form id (see Decisions Recorded 2026-10-13).
- Public applicant routes and the form-questions endpoint by form id still need recording in API_CONTRACT.md (Structure handoff pending).
- Which form questions feed the Applicants list columns (full name, address, age, gender).

## Known Mismatches (verified 2026-10-12)
- The `forms` table and `jobs.form_id` are live (migrations 001 and 002, applied 2026-10-13). `answer_points` does not exist yet, and `job_questions` still has the old shape (`job_id`, `expected_answer`, NOT NULL `parameter_id`; no `form_id`, `question_type` or `options`). Until the questions move, a "form" in practice is the set of `job_questions` rows under one job.
- `app/models.py` JobQuestion still has `job_id`, a NOT NULL `parameter_id` and a NOT NULL `expected_answer`, and no `question_type` or `options`.
- The matching engine in `POST /apply` (app/routers/public.py, lines 98-258) scores with `expected_answer` (line 182). It must be rewritten for answer points, required answers and brand points, as its own contract-first step.
- `GET /api/v1/public/jobs/{job_id}/questions` returns no question type or options.
- `app/main.py` serves `/admin` and `/admin/archive` (static shell, added 2026-10-13). `/admin/home`, `/admin/brands/...`, `/admin/forms/...` and `/admin/applicants/...` are not implemented.
- The contract lists admin application endpoints (list, detail, status patch, resume) that are not in `app/routers/admin.py`.
- Route param naming differs: the v4 preamble says `{UID}`, the contract says `{application_id}`.
- RESOLVED 2026-10-13: the sidebar `forms` list now reads the `forms` table (app/routers/admin.py), not the legacy `parameters` table.
- Bugs in `POST /apply` (not fixed): a rejected job lookup leaves an orphaned PDF on disk; an unanswered hard-requirement question never sets the fail flag; invalid `answers` JSON and unknown question ids are silently ignored. The contract now requires 422 for these.
- Hardcodes: brand `code` is `name[:3].upper()` with a "BTE" schema default; `consent_agreed` defaults True and `terms_version` defaults "v1.0" in app/models.py; in `POST /apply` the 5 MB limit, the default `/data/resumes` path (docker-compose.yml:27 mounts `./data/resumes` to `/app/data/resumes`; whether an env var overrides the default is UNVERIFIED), the 8192 chunk size, the status strings, and a score of 100 for a form with no questions.
- Cosmetic duplicates (committed in 2451ad7): `Parameter, Parameter` and `SidebarFormItem, SidebarFormItem` imports in admin.py; `slug: str` twice in SidebarBrandItem and SidebarFormItem in schemas.py.
- Indexes in SCHEMA.md but not in app/models.py: `idx_jq_form_order`, `idx_jobs_form_id`, `idx_answer_points_question_id`, `idx_answers_application_id`.
- Dashboard (app/templates/admin.html): the Dashboard, Applicants, brand and form sidebar links are still `href="#"`. The FORMS "+" now opens the Form Builder modal (2026-10-13); the BRANDS "+" is still a plain span, so nothing opens there yet.
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
   Done 2026-10-13: schema-change mechanism decided (option A), migrations 001 and 002 applied, DB password incident fixed (committed in ab9bae3). Forms-creation slice DONE: Form Builder modal shell, `POST /api/v1/admin/forms`, sidebar switched to the `forms` table, Save-success toast (committed cab1a44 and this session's follow-up commit). Next: turn the dropped elements into real persisted questions (needs question-text/options/answer-points UI and `POST /api/v1/admin/forms/{form_id}/questions`), then the `/admin/forms/{form_id}` page itself.
2. Security: decide admin auth and review the Open ended sensitive-data example.
3. Design: build the Brands and Forms page shells with "+" buttons using placeholder content only, plus the apply wizard layouts (Yes/No, A-D, Open ended).
4. Structure/API: migration plan for forms, answer_points and `jobs.form_id` (contract-first, destructive steps confirmed).
5. Wire one feature at a time: form create DONE; next is the question editor (persisting dropped elements as real `job_questions` rows with text/options/answer points), then answer points, attach jobs, submissions, then the matching engine rewrite.

## Session Log 2026-10-13 (sidebar 3-dot menu and Archive page shells)
- Forms sidebar: each form row has a 3-dot button with a floating menu (edit/rename icon, archive icon). SHELL ONLY: the icons do nothing. Rename and archive are not wired. (Update 2026-10-13: Rename and Archive are now wired.)
- Archive page: new route `GET /admin/archive` (app/main.py) serving `app/templates/archive.html`, plus an "Archive" link under Forms in the admin.html sidebar. Static shell: "Archive Assets" with three cards (Forms, Applicants, Brands), counts are placeholder dashes. Card list DECIDED: Forms, Applicants and Brands. The page route is a decided design, not an API endpoint.
- No new API endpoint. `archive.html` reuses `GET /api/v1/admin/metadata/sidebar` for the sidebar lists, rendered with `textContent` (no unescaped innerHTML).
- Open (Structure handoff): archive field for forms (archived_at vs is_archived), applicants and brands (brands and applicants tables not checked for an archive field, UNVERIFIED); rename and archive endpoints; archive count and list endpoints; the sidebar query must exclude archived forms (`select(Form)` in admin.py has no filter today). Add `/admin/archive` to the v4 preamble section 3 route list.
- Hardcodes and flags: sidebar CSS and markup are now shared (see Admin layout rules below) but still duplicated in admin.html until its switch-over; Bootstrap CDN URLs and fixed `/api/v1/admin/...` paths repeated; unescaped `${f.name}` in the admin.html sidebar render was REMOVED 2026-10-13 (admin.html now uses the shared sidebar); the sidebar endpoint is unbounded (18.2).

## Admin layout rules (decided 2026-10-13)
- Every admin module uses the shared sidebar. No page composes its own sidebar markup, sidebar CSS or sidebar JS.
- Shared files: `app/templates/_sidebar.html` (nav), `app/templates/_form_builder.html` (Form Builder modal and created toast), `app/static/admin-sidebar.css` (palette tokens, body, sidebar and form-row styles), `app/static/admin-sidebar.js` (sidebar render via `textContent`, `refreshSidebar()`, 3-dot menu open/close, Form Builder modal save).
- A page sets `{% set active_page = 'dashboard' %}` or `'archive'` before including `_sidebar.html`. New modules add their own value and a matching `{% if %}` in `_sidebar.html`.
- Page wrapper for every module: `div.container-fluid.p-0` > `div.row.g-0` > `_sidebar.html` + `main.col-md-10.px-4.pb-5`. A plain `container-fluid` adds 12px side padding and shifts the page (found on Archive, fixed).
- Page load order: Bootstrap 5.3.0 CSS, Nunito font, `/static/admin-sidebar.css`, page-only CSS; at the end of body: `_form_builder.html`, Bootstrap 5.3.0 bundle, `/static/admin-sidebar.js`, page script. Page scripts call `refreshSidebar()` and must not define their own sidebar loaders.

## Session Log 2026-10-13 (shared sidebar consolidation, step 1 of 3)
- DONE: four shared files created; `archive.html` switched to them (own sidebar CSS, nav markup and `fillList`/`loadSidebar` removed; Bootstrap JS bundle added; wrapper changed to `container-fluid p-0`). Archive now shows "+" buttons, kebab menus and the Form Builder modal like the Dashboard.
- Archive Forms count is wired to `GET /api/v1/admin/forms?archived=true&limit=1` (`data.total`). Applicants and Brands counts are still placeholder dashes.
- Step 2 (DONE 2026-10-13, see the next session log): switch `admin.html` to the shared files, removing its sidebar, kebab, modal and toast code while keeping the dashboard summary and tally code. The modal save handler there calls `fetchDashboardData()`; shared JS calls `refreshSidebar()` instead. admin.html's unescaped `innerHTML` sidebar render goes away at that step. Consider a shared base template for the wrapper at the same time.
- Step 3: Rename and Archive both DONE 2026-10-13 (wired once in `admin-sidebar.js`).
- Other pending: migration 003 (`forms.archived_at`) applied; held reshape plan shifts to 004-006; `Form.archived_at` and `Job.form_id` mapped in models; dev runs with `--reload` and a bind mount; throwaway archived row `zz archive test` exists in forms; jobs-409 untested; `/admin` vs `/admin/home` mismatch (v4 section 3) still open; shared CSS differences vs the old copies were whitespace noise plus the archive-only `.archive-card` rules (kept in archive.html).

## Session Log 2026-10-13 (form rename backend + admin.html moved to the shared sidebar)
- DONE (backend, step 1 of 3 for form rename): `PATCH /api/v1/admin/forms/{form_id}` implemented in `app/routers/admin.py` (`rename_form`; body reuses `FormCreateRequest`). Verified live: 422 bad id, 404 unknown id, 422 blank name, 409 slug clash, 200 rename (slug regenerated), 200 same-slug rename. The archived-form 409 is untested. `docs/API_CONTRACT.md` updated (status line and Last verified).
- DONE (shared sidebar consolidation, step 2 of 3): `admin.html` now uses `admin-sidebar.css`, `_sidebar.html` (`active_page = 'dashboard'`), `_form_builder.html` and `admin-sidebar.js`. Removed from admin.html: 99 duplicate CSS lines, 30 nav lines, and 148 lines of inline kebab handler, sidebar fetch, create/drag logic, modal and toast. Dashboard summary, tally and the 10-second refresh are kept. The shared Dashboard link now points to `/admin`. Sidebar form names render via `textContent`.
- DONE (step 3 of 3): Rename and Archive are both wired, see the session logs below.
- OPEN: the remaining `innerHTML` uses in admin.html dashboard code (summary cards, brand cards, tally rows) are not yet reviewed for unescaped database values (Security). `GET /api/v1/admin/metadata/sidebar` has no ORDER BY, so form order shifts after a rename (order by `created_at` like the forms list; needs a contract note). `/admin` vs `/admin/home` mismatch (v4 section 3) still open.
- Direction from the user: prefer server-side Python/Jinja rendering over static or JS-built HTML where it fits. Sidebar brand/form lists could be passed from the route into `_sidebar.html`, keeping the JS refresh only for updates after a change.
- Test data: `test 1` was renamed and restored during the PATCH test; its slug is `test-1`.

## Session Log 2026-10-13 (form rename UI)
- DONE: Rename is wired end to end. The Edit (pencil) button in a form's 3-dot menu opens a small centered Bootstrap modal (`#renameFormModal`, added to the shared `app/templates/_form_builder.html`, so every admin page that includes it gets it). The name input opens pre-filled and selected; Enter or Save calls `PATCH /api/v1/admin/forms/{form_id}`, then closes the modal, shows the toast ("Form renamed to ...") and calls `refreshSidebar()`. Handler lives once in `app/static/admin-sidebar.js`. An unchanged name closes the modal without a request. Inline errors: blank name (client side), 409 name already used or form archived, 404 form gone (also refreshes the sidebar), 422 invalid name, network failure.
- Verified in the browser on `/admin` (modal opens with the name selected, rename saves, toast and sidebar update). The 409 and archive paths were not re-tested in the browser. `/admin/archive` uses the same shared files; a separate browser check there was not reported.
- RESOLVED (see the next session log): `GET /api/v1/admin/metadata/sidebar` had no ORDER BY, so a renamed form moved to the bottom of the sidebar.
- OPEN: the remaining `innerHTML` uses in admin.html dashboard code are not reviewed (Security); the archived-form 409 on PATCH is untested.
- Test data: forms currently in the sidebar are `Store Assessment Form`, `test 1`, `test 23` and `test 212312312` (formerly `test 2`). These are throwaway test rows.

## Session Log 2026-10-13 (sidebar alphabetical order and form archive UI)
- DONE (backend, small): `get_sidebar_metadata` in `app/routers/admin.py` now orders forms by `func.lower(Form.name), Form.name` (alphabetical, case-insensitive). Decided by the user so a renamed form re-sorts automatically: `refreshSidebar()` re-fetches after a rename, so no JS change was needed. Contract updated (sidebar entry and Last verified). Verified live (curl and screenshot: Store Assessment Form, test 1, test 23, test abcd, Z). This is a plain database sort, not a natural numeric sort (`test 212312312` sorts before `test 23`); natural sort can be done in Python later if wanted. Brands in the sidebar are still unordered (not requested).
- DONE (Archive UI, shared by Dashboard and Archive pages): `#archiveFormModal` added to `app/templates/_form_builder.html`; handler in `app/static/admin-sidebar.js` opens it from the kebab's archive icon with the form name set via `textContent`, then calls `POST /api/v1/admin/forms/{form_id}/archive`. On success: modal closes, toast ("Form ... archived."), `refreshSidebar()`, and a `forms:changed` event that `archive.html` listens for to reload the Forms count. Inline errors: 409 jobs still use the form (shows the server message with the job count), 409 already archived, 404, network failure. A confirm step was added because no unarchive endpoint exists yet. No contract change to the archive endpoint; call-site note added.
- Verified in the browser on `/admin/archive` (confirm modal shows the form name, archiving `Z` removed it from the sidebar, toast showed, Forms count went 1 to 2). Not re-tested: the Cancel path, the `/admin` page, and the jobs-still-use-the-form 409 (no jobs exist).
- OPEN: no unarchive/restore endpoint or UI (archived forms are only counted on the Archive page, not listed); the remaining `innerHTML` uses in admin.html dashboard code (Security review); brands sidebar order; `/admin` vs `/admin/home` mismatch (v4 section 3) still open.
- Test data: active forms are `Store Assessment Form`, `test 1`, `test 23`, `test abcd`; archived are `zz archive test` and `Z`. All are throwaway test rows.
