# API Contract: BTE Careers
*Last verified: 2026-10-14 (bbb9c70 + this commit: POST /api/v1/admin/brands implemented and verified live (create, duplicate 409, blank and symbols-only 422), Add brand modal wired, sidebar brand links open /admin/brands/{id} and highlight the current brand; sidebar response still returns `code` in the code (removal pending); 422 also returned when the name has no letters or numbers; earlier in the same series: brands contract recorded -- POST /api/v1/admin/brands, sidebar brands response without `code`, brand page route by `{brand_id}`, Sidebar rule; UNVERIFIED pending code + live test. Previous entry: 6228423 + this commit: MULTIPLE_CHOICE contract changed from a fixed 4-option, letter-keyed (A-D) scheme to a variable-length (3 or more), server-assigned-id-keyed scheme — options now `[{"id","text"}]` for MULTIPLE_CHOICE in question create/update/GET responses and the public questions endpoint; answer_points.answer_value and applicant answers use that id; admin application detail resolves applicant_answer back to option text. UNVERIFIED pending code + live test — see section 17 rule text and SCHEMA.md column comments)*

## Global Rules
- All `/api/v1/admin/*` endpoints require HR authentication (cookie/token).
- All list endpoints MUST include `page` and `limit` query parameters (Rule 13.2).
- **Scope (local-only):** The app runs only at `10.0.10.37:8000` on the LAN. The apply wizard is hosted in `bte_webapp` (`/apply`). Cross-app work with `bigtimeempire.com` is paused.
- **Sidebar rule (decided 2026-10-14):** The existing admin sidebar (`app/templates/_sidebar.html`, filled by `app/static/admin-sidebar.js` from `GET /api/v1/admin/metadata/sidebar`) is the ONLY admin sidebar and is the default for every admin page. It never changes structurally -- only its contents change (brand and form lists). Never create, propose or ask about a different or second sidebar; new admin pages include the shared `_sidebar.html`.

---

## 1. Public Endpoints (Careers Board)

### `GET /api/v1/public/jobs`
- **Purpose:** List active jobs for the public board.
- **Request:** Query `?brand_id={uuid}&page=1&limit=20`
- **Response (200 OK):**
  `{ "data": [ { "id": "uuid", "slug": "string", "title": "string", "brand_id": "uuid", "brand_name": "string", "brand_slug": "string" } ], "total": int }`

### `GET /api/v1/public/jobs/{job_id}/questions`
- **Purpose:** Fetch the questions of the form the job uses (`jobs.form_id`), in `display_order`. Never returns answer points or which choice is "wrong". A job with no form returns `{ "data": [] }` (UNVERIFIED assumption, see apply rules).
- **Request:** None
- **Response (200 OK):**
  `{ "data": [ { "id": "uuid", "question_text": "string", "display_order": int, "question_type": "YES_NO|MULTIPLE_CHOICE|OPEN_ENDED", "options": ["string"] (YES_NO) or [{"id": "string", "text": "string"}] (MULTIPLE_CHOICE, 3 or more) or null (OPEN_ENDED) } ] }`

### `POST /api/v1/public/apply`
- **Purpose:** Submit an application.
- **Content-Type:** `multipart/form-data`
- **Request:**
  * `job_id` (uuid)
  * `first_name`, `last_name`, `email`, `phone` (strings)
  * `answers` (JSON string array: `[{"question_id": "uuid", "answer": "string"}]`). Every YES_NO and MULTIPLE_CHOICE question of the job's form must be answered. For MULTIPLE_CHOICE, `answer` is the chosen option's `id` (from that question's `options` list), not its text or a letter. Missing answers, unknown question ids, an unknown option id, or invalid JSON return 422. A job with no form returns 409. The job and form are validated BEFORE the resume is written to disk. Scoring and suggested fit follow section 3.
  * `resume` (File, PDF only)
  * `terms_version` (string)
  * `consent_agreed` (boolean) - Philippine Data Privacy Act (RA 10173)
- **Response (201 Created):** `{ "message": "Application submitted successfully", "application_id": "uuid" }`

---

## 2. Admin API Endpoints (Dashboard & Modal)

### `GET /api/v1/admin/dashboard/tally`
- **Purpose:** Fast polling endpoint for the live pass/fail counts.
- **Request:** Query `?brand_id={uuid}` (optional, for filtering)
- **Response (200 OK):**
  `{ "data": [ { "job_id": "uuid", "job_title": "string", "counts": { "PASSED": int, "FAILED": int, "POOLING": int, "ENDORSED": int, "HIRED": int } } ] }`

### `GET /api/v1/admin/applications`
- **Purpose:** Paginated list of applications for the data table.
- **Request:** Query `?job_id={uuid}&form_id={uuid}&status={string}&search={string}&page=1&limit=50`
- **Response (200 OK):**
  `{ "data": [ { "id": "uuid", "applicant_name": "string", "job_title": "string", "score": int, "status": "string", "has_hard_fail_flag": bool, "created_at": "timestamp" } ], "total": int }`

### `GET /api/v1/admin/applications/{application_id}`
- **Purpose:** Full detail for the per-applicant modal.
- **Request:** None
- **Response (200 OK):**
  `{ "id": "uuid", "applicant": { "name": "string", "email": "string", "phone": "string" }, "score": int, "status": "string", "parsed_data": {}, "flags": ["string"], "suggested_fit": { "brands": [ { "brand_id": "uuid", "brand_name": "string", "points": int } ], "is_tie": bool } or null, "answers": [ { "question": "string", "question_type": "string", "applicant_answer": "string", "is_passed": bool or null } ], "duplicate_applications": [ { "job_title": "string", "status": "string", "date": "timestamp" } ] }`
- For `MULTIPLE_CHOICE` questions, `applicant_answer` is resolved to the chosen option's `text` (not its `id`) for admin readability.

### `PATCH /api/v1/admin/applications/{application_id}/status`
- **Purpose:** Manual override of an applicant's status.
- **Request:** JSON `{ "status": "ENDORSED" }`
- **Response (200 OK):** `{ "message": "Status updated", "new_status": "string" }`

### `GET /api/v1/admin/applications/{application_id}/resume`
- **Purpose:** Download/view the applicant's PDF.
- **Request:** None
- **Response (200 OK):** Streams `application/pdf` via `FileResponse` (Rule 13.5)

### `GET /api/v1/admin/metadata/sidebar`
- **Purpose:** Fetch dynamic lists of brands and forms for the left navigation. `code` was removed from the brands response (decided 2026-10-14: the `brands` table has no such column; verified 2026-10-14: `app/routers/admin.py` and `SidebarBrandItem` in `app/schemas.py` still return a derived `code`, removal pending; the frontend does not read it). `forms` comes from the `forms` table (implemented 2026-10-13, `app/routers/admin.py`). Archived forms (`archived_at IS NOT NULL`) are excluded (implemented 2026-10-13). Forms are ordered alphabetically by name, case-insensitive, with `name` as the tie-break, so a renamed form moves to its alphabetical position on the next sidebar refresh (decided 2026-10-13). Called by two pages: `admin.html` and `archive.html` (`/admin/archive`, added 2026-10-13); no contract change.
- **Request:** None
- **Response (200 OK):**
  `{ "brands": [ { "id": "uuid", "name": "string", "slug": "string" } ], "forms": [ { "id": "uuid", "name": "string", "slug": "string" } ] }`

### `POST /api/v1/admin/brands`
- **Purpose:** Create a brand from the sidebar BRANDS "+" Add brand modal. Contract decided 2026-10-14; backend implemented and verified live 2026-10-14 (`app/routers/admin.py`): 201 create, 409 duplicate, 422 blank or symbols-only. The Add brand modal in the shared sidebar calls it (`app/static/admin-sidebar.js`).
- **Auth:** HR authentication (see Global Rules).
- **Request:** JSON `{ "name": "string" }` -- trimmed, required, must not be blank after trimming.
- **Slug:** generated server-side from `name` (lowercase, runs of non-alphanumeric characters become a single hyphen, no leading or trailing hyphen; "TSG" becomes `tsg`). Never typed by the admin and never changes if the brand is renamed later.
- **Response (201 Created):** `{ "id": "uuid", "name": "string", "slug": "string" }`
- **Errors:**
  * `409` if the name or the generated slug already exists (compared case-insensitively; no automatic `-2` suffix). The modal shows the message.
  * `422` if `name` is missing or blank after trimming, or contains no letters or numbers (the generated slug would be empty).
- **Client:** after success the Add brand modal closes and the sidebar refreshes through the existing `refreshSidebar()`. No schema change (uses the existing `brands` columns `id`, `name`, `slug`).

### `GET /api/v1/admin/dashboard/summary`
- **Purpose:** Fetch overall application totals and brand-level top match summaries.
- **Request:** Query `?date_from={YYYY-MM-DD}&date_to={YYYY-MM-DD}` (optional)
- **Response (200 OK):**
  `{ "overall_totals": { "passed": int, "failed": int, "pooling": int, "endorsed": int, "hired": int, "total_processed": int }, "brand_summaries": [ { "brand_id": "uuid", "brand_name": "string", "top_matches_count": int } ] }`

---

## 3. Admin Forms API (PARTIALLY IMPLEMENTED -- see per-endpoint status)

All endpoints require HR authentication (see Global Rules). A form is a shared template: many jobs can use one form (`jobs.form_id`), and a job uses at most one. A form's questions are its `job_questions` rows. Question type is set at creation and cannot be changed (delete and re-add instead). The answer points (the admin cheat sheet) are never returned by public endpoints. Admin form endpoints are addressed by form id (`{form_id}`), matching the page route `/admin/forms/{form_id}`; the slug is returned as a field and is used only in public paths. Every `{form_id}`, `{job_id}` and `{question_id}` must be a valid UUID (422 otherwise); an unknown id returns 404.

### `GET /api/v1/admin/forms`
- **Purpose:** Paginated list of forms. By default returns active forms only (`archived_at IS NULL`) for the Forms module. With `archived=true` it returns archived forms only, for the Archive page (Forms category); `total` is the count shown on the right side of that category.
- **Request:** Query `?archived=false|true&page=1&limit=20` (`archived` defaults to false; `page` >= 1; `limit` 1-100, default 20; out-of-range values return 422)
- **Response (200 OK):** `{ "data": [ { "id": "uuid", "slug": "string", "name": "string", "job_count": int, "archived_at": "timestamp or null" } ], "total": int }`
- **Notes:** Every value is computed per request from the database (`total` = count of forms matching the `archived` filter; `job_count` = count of `jobs` rows with that `form_id`); nothing is static. `question_count` is intentionally omitted until `job_questions` has a `form_id` (held migration); it will be added back to this item then. Ordered by `created_at` ascending (archived list: by `archived_at` descending).
- **Status:** Implemented 2026-10-13 (`app/routers/admin.py`). Verified live: active total 3, archived total 1, `limit=0` returns 422. Call site: `archive.html` calls `?archived=true&limit=1` and renders `total` as the Forms count on `/admin/archive`. Also called by `admin_form_detail.html` (`/admin/forms/{form_id}`) with `?archived=false&limit=100`, client-side matched by `id`, to render the page title -- a temporary stand-in for the dedicated `GET /api/v1/admin/forms/{form_id}` endpoint below, which is now implemented (see below) and is called by this page's Edit button (see below); the title lookup stays as is. Known limit: if active forms ever exceed 100, this lookup can miss a match. No HR-auth check yet (existing gap; Security owns it).

### `POST /api/v1/admin/forms`
- **Purpose:** Create an empty form (the "+" button). The slug is generated server-side from the name.
- **Request:** JSON `{ "name": "string" }`
- **Response (201 Created):** `{ "id": "uuid", "slug": "string", "name": "string" }`
- **Errors:** 409 slug already taken; 422 invalid body.
- **Status:** Implemented 2026-10-13 (`app/routers/admin.py`). No HR-auth check yet -- none of the admin endpoints enforce it today (existing gap, not introduced here); Security owns closing it.

### `GET /api/v1/admin/forms/{form_id}`
- **Purpose:** Form detail for the editor: name, the jobs that use it, and all questions in order with their answer points (a form holds a small, bounded number of questions, so the list is not paginated).
- **Response (200 OK):** `{ "id": "uuid", "slug": "string", "name": "string", "jobs": [ { "id": "uuid", "slug": "string", "title": "string", "brand_name": "string" } ], "questions": [ { "id": "uuid", "display_order": int, "question_type": "YES_NO|MULTIPLE_CHOICE|OPEN_ENDED", "question_text": "string", "options": ["string"] (YES_NO) or [{"id": "string", "text": "string"}] (MULTIPLE_CHOICE) or null (OPEN_ENDED), "is_hard_requirement": bool, "answer_points": [ { "answer_value": "YES|NO|<option id for MULTIPLE_CHOICE>", "target_type": "BRAND|FAIL", "brand_id": "uuid or null", "brand_name": "string or null", "points": int } ] } ] }`
- **Errors:** 404 form not found.
- **Status:** Implemented 2026-10-13 (`app/routers/admin.py`, `get_form_detail`). `answer_points` is always `[]` in every question -- the `answer_points` table does not exist in the live DB yet (confirmed via `\dt`, SCHEMA.md held migration), so no AnswerPoint query runs. Verified live: 422 malformed id, 404 unknown id, 200 real form (`zz save check 3`: empty `jobs`, one YES_NO question with its options and `answer_points: []`). Call site: `app/static/admin-sidebar.js` (`openFormBuilderForEdit`, opened by the Edit button on `/admin/forms/{form_id}`; shows `question_text` and `options` read-only). Verified in the browser 2026-10-13: existing questions load, new ones save and appear on reopen. No HR-auth check yet (existing gap; Security owns it).

### `PATCH /api/v1/admin/forms/{form_id}`
- **Purpose:** Rename a form. The slug is regenerated from the new name; the `id` never changes. Jobs link by `jobs.form_id`, so they show the new name automatically. Any old public path using the previous slug stops resolving.
- **Request:** JSON `{ "name": "string" }`
- **Response (200 OK):** `{ "id": "uuid", "slug": "string", "name": "string" }`
- **Errors:** 404 form not found; 409 the new slug is already used by another form (archived forms keep their slug, so they count); 409 the form is archived (archived forms are read-only); 422 empty or invalid name. A name that yields the form's own current slug is allowed.
- **Status:** Implemented 2026-10-13 (`app/routers/admin.py`, `rename_form`). Verified live: 422 malformed id, 404 unknown id, 422 blank name, 409 slug clash, 200 rename (slug regenerated), 200 same-slug rename. The 409 for an archived form is untested (no archived form id was available). Call site: `app/static/admin-sidebar.js` (Save in the rename modal, shared by `/admin` and `/admin/archive`); verified in the browser on `/admin` 2026-10-13 (rename saves, toast shows, sidebar refreshes). No HR-auth check yet (existing gap; Security owns it).

### `POST /api/v1/admin/forms/{form_id}/archive`
- **Purpose:** Archive a form. Sets `forms.archived_at` to now. The form leaves the sidebar and the default forms list and appears only under Archive > Forms. It is never served on public paths.
- **Response (200 OK):** `{ "id": "uuid", "slug": "string", "name": "string", "archived_at": "timestamp" }`
- **Errors:** 404 form not found; 409 the form is already archived; 409 any job still uses the form (`jobs.form_id`), with the job count in the detail. Detach the jobs first.
- **Status:** Implemented 2026-10-13 (`app/routers/admin.py`; migration 003 applied). Verified live: 422 malformed id, 404 unknown id, 200 success, 409 already archived. The 409 for jobs still using the form is untested because no jobs exist yet. Call site: `app/static/admin-sidebar.js` (Archive confirm modal, shared by `/admin` and `/admin/archive`); verified in the browser on `/admin/archive` 2026-10-13 (archive succeeds, toast shows, sidebar refreshes, Archive page Forms count updates). No HR-auth check yet (existing gap; Security owns it).

### `DELETE /api/v1/admin/forms/{form_id}`
- **Purpose:** Delete a form.
- **Response:** 204 No Content.
- **Errors:** 409 if any job uses the form or any of its questions has applicant answers.

### `GET /api/v1/admin/jobs`
- **Purpose:** Paginated job list, used to pick jobs to attach to a form.
- **Request:** Query `?has_form=true|false&brand_id={uuid}&page=1&limit=50`
- **Response (200 OK):** `{ "data": [ { "id": "uuid", "slug": "string", "title": "string", "brand_name": "string", "form_id": "uuid or null" } ], "total": int }`

### `PUT /api/v1/admin/forms/{form_id}/jobs/{job_id}`
- **Purpose:** Attach a job to this form (sets `jobs.form_id`).
- **Response (200 OK):** `{ "message": "Job attached" }`
- **Errors:** 404 form or job not found; 409 if the job already uses a different form (detach it first).

### `DELETE /api/v1/admin/forms/{form_id}/jobs/{job_id}`
- **Purpose:** Detach a job from this form.
- **Response:** 204 No Content.
- **Errors:** 409 if the job already has applications (their answers refer to this form's questions).

### `POST /api/v1/admin/forms/{form_id}/questions`
- **Purpose:** Add a question with its answer points. `display_order` is assigned server-side as last + 1.
- **Request:** JSON `{ "question_type": "YES_NO|MULTIPLE_CHOICE|OPEN_ENDED", "question_text": "string", "options": ["Choice text 1", "Choice text 2", "Choice text 3"], "is_hard_requirement": bool, "answer_points": [ { "answer_value": "<option id>", "target_type": "BRAND", "brand_id": "uuid", "points": 1 }, { "answer_value": "<option id>", "target_type": "FAIL" } ] }` (for MULTIPLE_CHOICE, the create request sends plain option text; the server assigns a stable `id` to each option and returns it in the response. `answer_points` for MULTIPLE_CHOICE uses that server-assigned `id`, never text or a letter -- so answer_points can only reference MULTIPLE_CHOICE options on a follow-up PATCH once the create response's ids are known.)
- **Rules:**
  * `YES_NO`: optional `options` of exactly 2 non-empty, distinct label texts (e.g. ["Own a car", "Do not own a car"]). `options[0]` is the display label for `YES`, `options[1]` for `NO`; omitted or null means the labels Yes / No. `answer_value` is always "YES" or "NO" and scoring is unchanged (implemented 2026-10-13 in POST and PATCH questions).
  * `MULTIPLE_CHOICE`: at least 3 `options` (no maximum), each trimmed, non-empty, and distinct (case-insensitive). On create, the server generates a stable `id` for each option; `answer_value` in `answer_points` is that `id`, never text or a letter. On PATCH, an option object that includes an existing `id` keeps that id (and can have its `text` edited); an option object with no `id` is treated as new and gets one assigned; an existing `id` left out of the submitted list is deleted along with any `answer_points` rows that reference it.
  * `OPEN_ENDED`: no `options`, no `answer_points`, `is_hard_requirement` must be false.
  * `target_type` `BRAND` requires an existing `brand_id` and `points` of 1 or more. `FAIL` takes no `brand_id`, and its `points` value is ignored (any FAIL row marks that choice as failing).
  * One answer choice may have several rows (for example "+1 brand" and "+1 fail").
  * `is_hard_requirement` true requires at least one FAIL row on the question.
  * `answer_points` is OPTIONAL for `YES_NO` and `MULTIPLE_CHOICE` (decided 2026-10-13): omitted or an empty list stores no rows, and `is_hard_requirement` is then false. This is how the Form Builder's first Save stores questions, before an answer-points editor exists.
  * Consequence (follows from the scoring rule in docs/SCHEMA.md): a question with no answer_points rows has no FAIL row on any choice, so every answer passes it. It never fails an applicant and never adds brand points until points are added with PATCH.
  * Storage: the row is created with `form_id` set and `job_id`, `parameter_id` and `expected_answer` NULL (columns relaxed by migration 004, applied 2026-10-13).
  * Interim limit (decided 2026-10-13): until the `answer_points` table exists, a non-empty `answer_points` list returns 422 ("answer points are not supported yet"), and `is_hard_requirement` true returns 422 (it needs a FAIL row). Both lift when the answer_points migration lands.
  * Validation: `question_text` is trimmed and must be non-empty. `question_type` must be one of the three values. Option labels are trimmed and must be non-empty. For `YES_NO`, `options` is omitted/null or exactly 2 labels (an empty list is 422), and the two labels must differ case-insensitively (UNVERIFIED assumption, matches the Form Builder). Stored `options` is null when omitted.
  * `display_order` is max + 1 for the form, so the first question gets 1 (verified live 2026-10-13).
  * Status: Implemented 2026-10-13 (`app/routers/admin.py`, `create_question`; schemas `QuestionCreateRequest` and `QuestionResponse` in `app/schemas.py`; migration 004). Verified live: 201 for YES_NO with default labels (`options` stored as SQL NULL, after the `none_as_null` fix on the model) and with custom labels, `display_order` 1 then 2; 422 for labels equal ignoring case, one label, blank text, unknown type, non-empty `answer_points`, `is_hard_requirement` true, MULTIPLE_CHOICE with 2 options, malformed form id; 404 unknown form id; 409 archived form. OPEN_ENDED create verified in the browser 2026-10-13 (Form Builder Save). NOT tested: MULTIPLE_CHOICE success path, an empty option label, an empty `options` list on YES_NO. Call site: `app/static/admin-sidebar.js` (Form Builder Save: creates the form, then posts each Yes / No card in order with its name and two labels as `options`; wired 2026-10-13; verified in the browser 2026-10-13: the form is created, then its Yes / No question is stored with its labels, confirmed in `job_questions`). NOT tested: the partial-failure path (form created but a question fails, then Save retried). Open ended cards are posted with `question_type` and `question_text` only, no `options` (Form Builder Save, wired and verified in the browser 2026-10-13: saved and reloaded in order). Other element types (Multiple Choice) block Save until they have contracts. No HR-auth check yet (existing gap; Security owns it). Known limit: `display_order` is max + 1 with no unique constraint, so two simultaneous saves to one form could share a number.
- **Response (201 Created):** the created question object (same shape as in form detail); `answer_points` is `[]` for now.
- **Errors:** 404 form not found; 409 the form is archived and read-only (same rule as rename, added 2026-10-13); 422 malformed `form_id`, rule violation, or one of the interim limits above.

### `PATCH /api/v1/admin/forms/{form_id}/questions/{question_id}`
- **Purpose:** Edit a question. `question_type` cannot be changed.
- **Request:** JSON, any subset of `question_text`, `options`, `is_hard_requirement`, `answer_points`. When `answer_points` is sent it REPLACES the question's whole set. The same rules apply.
- **Response (200 OK):** the updated question object.
- **Status:** Implemented 2026-10-13 (`app/routers/admin.py`, `update_question`). Same interim limit as create: non-empty `answer_points` or `is_hard_requirement: true` returns 422 (table doesn't exist yet). `question_type` is immutable (not in the request schema). Verified live: 200 question_text update and revert (on `zz save check 3`'s real question), 404 unknown question id. `options` on YES_NO (exactly 2 distinct labels) is implemented and verified in the browser 2026-10-13 (labels edited on an existing question persisted and reload correctly). The 422 paths for `options` are enforced in code but not exercised via direct API calls; the browser editor also blocks equal labels client-side. Call site: `app/static/admin-sidebar.js` (Form Builder, Edit on a loaded Yes / No card sends `question_text` and `options`; applies immediately, not on the modal's Save). Edit on a loaded Open ended card sends `question_text` only, no `options` (added 2026-10-13; verified in the browser 2026-10-13: a saved Open ended question was renamed and the new name persisted on reopen; first live OPEN_ENDED PATCH).

### `DELETE /api/v1/admin/forms/{form_id}/questions/{question_id}`
- **Purpose:** Delete a question and its answer points.
- **Response:** 204 No Content.
- **Errors:** 409 if the question already has applicant answers.
- **Status:** Implemented 2026-10-13 (`app/routers/admin.py`, `delete_question`). Note: no archived-form check on this endpoint (unlike POST/PATCH) -- the contract's Errors list for DELETE never specified one, so none was added; flagged for confirmation. Verified live: 404 unknown question id. 204 success path not yet tested against a real row (destructive; needs a throwaway question first, not run without explicit confirmation).

### `POST /api/v1/admin/forms/{form_id}/questions/reorder`
- **Purpose:** Set the question order. The body must list every question id of this form exactly once.
- **Request:** JSON `{ "ordered_ids": ["uuid"] }`
- **Response (200 OK):** `{ "message": "Order updated" }`
- **Errors:** 422 if ids are missing, duplicated or from another form.

### Form submissions (no new endpoint)
A form's submissions are the applications for the jobs that use it: `GET /api/v1/admin/applications?form_id={form.id}` (section 2).

### Scoring and suggested fit (applies to `POST /api/v1/public/apply`)
- Answer values: `YES_NO` is "YES" or "NO", `MULTIPLE_CHOICE` is the chosen option's `id` (a string), `OPEN_ENDED` is the applicant's full free text, stored as is and never scored.
- Score: percent of scored questions (YES_NO and MULTIPLE_CHOICE) whose chosen answer has no FAIL row. OPEN_ENDED is excluded from the divisor. A hard-requirement question whose chosen answer has a FAIL row sets `has_hard_fail_flag` and status FAILED. `pass_threshold` and `pooling_threshold` work as before.
- Suggested fit: BRAND points are summed per brand and stored in `applications.brand_points`. The brands with the highest total above 0 are the suggested fit. More than one means a tie, shown to the admin as "suited for both ...". No brand points means no flag. The flag never changes the score or status.

---

## 4. HTML Server-Rendered Routes (Jinja2)

### `GET /admin` or `GET /admin/home`
- **Purpose:** Default dashboard entry point showing overall tally.
- **Response:** `text/html`

### `GET /admin/brands/{brand_id}`
- **Purpose:** Brand page (URL carries the brand id, same as forms; decided 2026-10-14): brand name, "+ Create Job" button, search, "+ Add filter" row and the brand's job cards, inside the shared sidebar layout. Shell implemented 2026-10-14 (`app/templates/admin_brand_detail.html`, route in `app/main.py`), verified in the browser with placeholder content: `brand_id` is accepted but not used yet. Name, jobs, search, filters and Create Job are not wired yet. Sidebar brand links open this route and the current brand is highlighted in the sidebar (verified in the browser 2026-10-14).
- **Response:** `text/html`

### `GET /admin/forms/{form_id}`
- **Purpose:** Form view: shows the form and its submissions (applications for the jobs that use the form), with the question editor. Page implemented 2026-10-13 (`app/templates/admin_form_detail.html`), verified in the browser: form name from the forms list, placeholder submission rows, disabled Edit button (shell). Submissions and the question editor are not wired yet.
- **Response:** `text/html`

### `GET /admin/applicants/{application_id}`
- **Purpose:** Direct deep-link to open a specific applicant's detail modal/page.
- **Response:** `text/html`
