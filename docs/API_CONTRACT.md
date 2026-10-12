# API Contract: BTE Careers
*Last verified: 2026-10-12 (Added semantic HTML routes and slugs)*

## Global Rules
- All `/api/v1/admin/*` endpoints require HR authentication (cookie/token).
- All list endpoints MUST include `page` and `limit` query parameters (Rule 13.2).
- **Cross-App Boundary (Apply Flow):** The apply wizard is hosted locally on `bte_webapp` (`10.0.10.37:8000/apply`). `bigtimeempire.com` links out directly to it (no cross-origin multipart proxying required for now).

---

## 1. Public Endpoints (Careers Board)

### `GET /api/v1/public/jobs`
- **Purpose:** List active jobs for the public board.
- **Request:** Query `?brand_id={uuid}&page=1&limit=20`
- **Response (200 OK):**
  `{ "data": [ { "id": "uuid", "slug": "string", "title": "string", "brand_id": "uuid", "brand_name": "string", "brand_slug": "string" } ], "total": int }`

### `GET /api/v1/public/jobs/{job_id}/questions`
- **Purpose:** Fetch the dynamic parameters/questions for the application form.
- **Request:** None
- **Response (200 OK):**
  `{ "data": [ { "id": "uuid", "question_text": "string", "display_order": int } ] }`

### `POST /api/v1/public/apply`
- **Purpose:** Submit an application.
- **Content-Type:** `multipart/form-data`
- **Request:**
  * `job_id` (uuid)
  * `first_name`, `last_name`, `email`, `phone` (strings)
  * `answers` (JSON string array: `[{"question_id": "uuid", "answer": "string"}]`)
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
- **Request:** Query `?job_id={uuid}&status={string}&search={string}&page=1&limit=50`
- **Response (200 OK):**
  `{ "data": [ { "id": "uuid", "applicant_name": "string", "score": int, "status": "string", "has_hard_fail_flag": bool, "created_at": "timestamp" } ], "total": int }`

### `GET /api/v1/admin/applications/{application_id}`
- **Purpose:** Full detail for the per-applicant modal.
- **Request:** None
- **Response (200 OK):**
  `{ "id": "uuid", "applicant": { "name": "string", "email": "string", "phone": "string" }, "score": int, "status": "string", "parsed_data": {}, "flags": ["string"], "answers": [ { "question": "string", "applicant_answer": "string", "is_passed": bool } ], "duplicate_applications": [ { "job_title": "string", "status": "string", "date": "timestamp" } ] }`

### `PATCH /api/v1/admin/applications/{application_id}/status`
- **Purpose:** Manual override of an applicant's status.
- **Request:** JSON `{ "status": "ENDORSED" }`
- **Response (200 OK):** `{ "message": "Status updated", "new_status": "string" }`

### `GET /api/v1/admin/applications/{application_id}/resume`
- **Purpose:** Download/view the applicant's PDF.
- **Request:** None
- **Response (200 OK):** Streams `application/pdf` via `FileResponse` (Rule 13.5)

### `GET /api/v1/admin/metadata/sidebar`
- **Purpose:** Fetch dynamic lists of brands and forms for the left navigation.
- **Request:** None
- **Response (200 OK):**
  `{ "brands": [ { "id": "uuid", "name": "string", "slug": "string", "code": "string" } ], "forms": [ { "id": "uuid", "name": "string", "slug": "string" } ] }`

### `GET /api/v1/admin/dashboard/summary`
- **Purpose:** Fetch overall application totals and brand-level top match summaries.
- **Request:** Query `?date_from={YYYY-MM-DD}&date_to={YYYY-MM-DD}` (optional)
- **Response (200 OK):**
  `{ "overall_totals": { "passed": int, "failed": int, "pooling": int, "endorsed": int, "hired": int, "total_processed": int }, "brand_summaries": [ { "brand_id": "uuid", "brand_name": "string", "top_matches_count": int } ] }`

---

## 3. HTML Server-Rendered Routes (Jinja2)

### `GET /admin` or `GET /admin/home`
- **Purpose:** Default dashboard entry point showing overall tally.
- **Response:** `text/html`

### `GET /admin/brands/{brand_slug}`
- **Purpose:** Dashboard pre-filtered to a specific brand.
- **Response:** `text/html`

### `GET /admin/forms/{form_slug}`
- **Purpose:** Dashboard pre-filtered to jobs using a specific global parameter/form.
- **Response:** `text/html`

### `GET /admin/applicants/{application_id}`
- **Purpose:** Direct deep-link to open a specific applicant's detail modal/page.
- **Response:** `text/html`
