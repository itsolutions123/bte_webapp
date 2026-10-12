# API Contract: BTE Careers
*Last verified: 2026-10-13 (on top of 9ae232a; admin forms endpoints and page route keyed by form id, still planned; public applicant routes not yet recorded)*

## Global Rules
- All `/api/v1/admin/*` endpoints require HR authentication (cookie/token).
- All list endpoints MUST include `page` and `limit` query parameters (Rule 13.2).
- **Scope (local-only):** The app runs only at `10.0.10.37:8000` on the LAN. The apply wizard is hosted in `bte_webapp` (`/apply`). Cross-app work with `bigtimeempire.com` is paused.

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
  `{ "data": [ { "id": "uuid", "question_text": "string", "display_order": int, "question_type": "YES_NO|MULTIPLE_CHOICE|OPEN_ENDED", "options": ["string"] or null } ] }`

### `POST /api/v1/public/apply`
- **Purpose:** Submit an application.
- **Content-Type:** `multipart/form-data`
- **Request:**
  * `job_id` (uuid)
  * `first_name`, `last_name`, `email`, `phone` (strings)
  * `answers` (JSON string array: `[{"question_id": "uuid", "answer": "string"}]`). Every YES_NO and MULTIPLE_CHOICE question of the job's form must be answered. Missing answers, unknown question ids or invalid JSON return 422. A job with no form returns 409. The job and form are validated BEFORE the resume is written to disk. Scoring and suggested fit follow section 3.
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

### `PATCH /api/v1/admin/applications/{application_id}/status`
- **Purpose:** Manual override of an applicant's status.
- **Request:** JSON `{ "status": "ENDORSED" }`
- **Response (200 OK):** `{ "message": "Status updated", "new_status": "string" }`

### `GET /api/v1/admin/applications/{application_id}/resume`
- **Purpose:** Download/view the applicant's PDF.
- **Request:** None
- **Response (200 OK):** Streams `application/pdf` via `FileResponse` (Rule 13.5)

### `GET /api/v1/admin/metadata/sidebar`
- **Purpose:** Fetch dynamic lists of brands and forms for the left navigation. `forms` must come from the `forms` table (PLANNED). The code currently reads the legacy `parameters` table.
- **Request:** None
- **Response (200 OK):**
  `{ "brands": [ { "id": "uuid", "name": "string", "slug": "string", "code": "string" } ], "forms": [ { "id": "uuid", "name": "string", "slug": "string" } ] }`

### `GET /api/v1/admin/dashboard/summary`
- **Purpose:** Fetch overall application totals and brand-level top match summaries.
- **Request:** Query `?date_from={YYYY-MM-DD}&date_to={YYYY-MM-DD}` (optional)
- **Response (200 OK):**
  `{ "overall_totals": { "passed": int, "failed": int, "pooling": int, "endorsed": int, "hired": int, "total_processed": int }, "brand_summaries": [ { "brand_id": "uuid", "brand_name": "string", "top_matches_count": int } ] }`

---

## 3. Admin Forms API (PLANNED - not implemented)

All endpoints require HR authentication (see Global Rules). A form is a shared template: many jobs can use one form (`jobs.form_id`), and a job uses at most one. A form's questions are its `job_questions` rows. Question type is set at creation and cannot be changed (delete and re-add instead). The answer points (the admin cheat sheet) are never returned by public endpoints. Admin form endpoints are addressed by form id (`{form_id}`), matching the page route `/admin/forms/{form_id}`; the slug is returned as a field and is used only in public paths. Every `{form_id}`, `{job_id}` and `{question_id}` must be a valid UUID (422 otherwise); an unknown id returns 404.

### `GET /api/v1/admin/forms`
- **Purpose:** Paginated list of forms for the Forms module.
- **Request:** Query `?page=1&limit=20`
- **Response (200 OK):** `{ "data": [ { "id": "uuid", "slug": "string", "name": "string", "question_count": int, "job_count": int } ], "total": int }`

### `POST /api/v1/admin/forms`
- **Purpose:** Create an empty form (the "+" button). The slug is generated server-side from the name.
- **Request:** JSON `{ "name": "string" }`
- **Response (201 Created):** `{ "id": "uuid", "slug": "string", "name": "string" }`
- **Errors:** 409 slug already taken; 422 invalid body.

### `GET /api/v1/admin/forms/{form_id}`
- **Purpose:** Form detail for the editor: name, the jobs that use it, and all questions in order with their answer points (a form holds a small, bounded number of questions, so the list is not paginated).
- **Response (200 OK):** `{ "id": "uuid", "slug": "string", "name": "string", "jobs": [ { "id": "uuid", "slug": "string", "title": "string", "brand_name": "string" } ], "questions": [ { "id": "uuid", "display_order": int, "question_type": "YES_NO|MULTIPLE_CHOICE|OPEN_ENDED", "question_text": "string", "options": ["string"] or null, "is_hard_requirement": bool, "answer_points": [ { "answer_value": "YES|NO|A|B|C|D", "target_type": "BRAND|FAIL", "brand_id": "uuid or null", "brand_name": "string or null", "points": int } ] } ] }`
- **Errors:** 404 form not found.

### `PATCH /api/v1/admin/forms/{form_id}`
- **Purpose:** Rename a form. The slug does NOT change on rename (stable URLs).
- **Request:** JSON `{ "name": "string" }`
- **Response (200 OK):** `{ "id": "uuid", "slug": "string", "name": "string" }`

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
- **Request:** JSON `{ "question_type": "YES_NO|MULTIPLE_CHOICE|OPEN_ENDED", "question_text": "string", "options": ["A text", "B text", "C text", "D text"], "is_hard_requirement": bool, "answer_points": [ { "answer_value": "A", "target_type": "BRAND", "brand_id": "uuid", "points": 1 }, { "answer_value": "B", "target_type": "FAIL" } ] }`
- **Rules:**
  * `YES_NO`: no `options`; `answer_value` is "YES" or "NO".
  * `MULTIPLE_CHOICE`: exactly 4 `options`; `answer_value` is "A" to "D".
  * `OPEN_ENDED`: no `options`, no `answer_points`, `is_hard_requirement` must be false.
  * `target_type` `BRAND` requires an existing `brand_id` and `points` of 1 or more. `FAIL` takes no `brand_id`, and its `points` value is ignored (any FAIL row marks that choice as failing).
  * One answer choice may have several rows (for example "+1 brand" and "+1 fail").
  * `is_hard_requirement` true requires at least one FAIL row on the question.
- **Response (201 Created):** the created question object (same shape as in form detail).
- **Errors:** 404 form not found; 422 rule violation.

### `PATCH /api/v1/admin/forms/{form_id}/questions/{question_id}`
- **Purpose:** Edit a question. `question_type` cannot be changed.
- **Request:** JSON, any subset of `question_text`, `options`, `is_hard_requirement`, `answer_points`. When `answer_points` is sent it REPLACES the question's whole set. The same rules apply.
- **Response (200 OK):** the updated question object.

### `DELETE /api/v1/admin/forms/{form_id}/questions/{question_id}`
- **Purpose:** Delete a question and its answer points.
- **Response:** 204 No Content.
- **Errors:** 409 if the question already has applicant answers.

### `POST /api/v1/admin/forms/{form_id}/questions/reorder`
- **Purpose:** Set the question order. The body must list every question id of this form exactly once.
- **Request:** JSON `{ "ordered_ids": ["uuid"] }`
- **Response (200 OK):** `{ "message": "Order updated" }`
- **Errors:** 422 if ids are missing, duplicated or from another form.

### Form submissions (no new endpoint)
A form's submissions are the applications for the jobs that use it: `GET /api/v1/admin/applications?form_id={form.id}` (section 2).

### Scoring and suggested fit (applies to `POST /api/v1/public/apply`)
- Answer values: `YES_NO` is "YES" or "NO", `MULTIPLE_CHOICE` is "A" to "D", `OPEN_ENDED` is the applicant's full free text, stored as is and never scored.
- Score: percent of scored questions (YES_NO and MULTIPLE_CHOICE) whose chosen answer has no FAIL row. OPEN_ENDED is excluded from the divisor. A hard-requirement question whose chosen answer has a FAIL row sets `has_hard_fail_flag` and status FAILED. `pass_threshold` and `pooling_threshold` work as before.
- Suggested fit: BRAND points are summed per brand and stored in `applications.brand_points`. The brands with the highest total above 0 are the suggested fit. More than one means a tie, shown to the admin as "suited for both ...". No brand points means no flag. The flag never changes the score or status.

---

## 4. HTML Server-Rendered Routes (Jinja2)

### `GET /admin` or `GET /admin/home`
- **Purpose:** Default dashboard entry point showing overall tally.
- **Response:** `text/html`

### `GET /admin/brands/{brand_slug}`
- **Purpose:** Dashboard pre-filtered to a specific brand.
- **Response:** `text/html`

### `GET /admin/forms/{form_id}`
- **Purpose:** Form view: shows the form and its submissions (applications for the jobs that use the form), with the question editor. PLANNED.
- **Response:** `text/html`

### `GET /admin/applicants/{application_id}`
- **Purpose:** Direct deep-link to open a specific applicant's detail modal/page.
- **Response:** `text/html`
