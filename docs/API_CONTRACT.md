# API Contract: BTE Careers
*Last verified: 2026-10-12 (Added RA 10173 Consent)*

## Global Rules
* All `/api/v1/admin/*` endpoints require HR authentication (cookie/token).
* All list endpoints MUST include `page` and `limit` query parameters (Rule 13.2).

---

## 1. Public Endpoints (Careers Board)

### `GET /api/v1/public/jobs`
* **Purpose:** List active jobs for the public board.
* **Request:** Query `?brand_id={uuid}&page=1&limit=20`
* **Response (200 OK):** 
  `{ "data": [ { "id": "uuid", "title": "string", "brand_id": "uuid", "brand_name": "string" } ], "total": int }`

### `GET /api/v1/public/jobs/{job_id}/questions`
* **Purpose:** Fetch the dynamic parameters/questions for the application form.
* **Request:** None
* **Response (200 OK):** 
  `{ "data": [ { "id": "uuid", "question_text": "string" } ] }`

### `POST /api/v1/public/apply`
* **Purpose:** Submit an application.
* **Content-Type:** `multipart/form-data`
* **Request:** 
  * `job_id` (uuid)
  * `first_name`, `last_name`, `email`, `phone` (strings)
  * `answers` (JSON string array: `[{"question_id": "uuid", "answer": "string"}]`)
  * `resume` (File, PDF only)
  * `terms_version` (string)
  * `consent_agreed` (boolean) - Philippine Data Privacy Act (RA 10173)
* **Response (201 Created):** `{ "message": "Application submitted successfully", "application_id": "uuid" }`

---

## 2. Admin Endpoints (Dashboard & Modal)

### `GET /api/v1/admin/dashboard/tally`
* **Purpose:** Fast polling endpoint for the live pass/fail counts.
* **Request:** Query `?brand_id={uuid}` (optional, for filtering)
* **Response (200 OK):** 
  `{ "data": [ { "job_id": "uuid", "job_title": "string", "counts": { "PASSED": int, "FAILED": int, "POOLING": int, "ENDORSED": int, "HIRED": int } } ] }`

### `GET /api/v1/admin/applications`
* **Purpose:** Paginated list of applications for the data table.
* **Request:** Query `?job_id={uuid}&status={string}&search={string}&page=1&limit=50`
* **Response (200 OK):** 
  `{ "data": [ { "id": "uuid", "applicant_name": "string", "score": int, "status": "string", "has_hard_fail_flag": bool, "created_at": "timestamp" } ], "total": int }`

### `GET /api/v1/admin/applications/{application_id}`
* **Purpose:** Full detail for the per-applicant modal.
* **Request:** None
* **Response (200 OK):** 
  `{ "id": "uuid", "applicant": { "name": "string", "email": "string", "phone": "string" }, "score": int, "status": "string", "parsed_data": {}, "flags": ["string"], "answers": [ { "question": "string", "applicant_answer": "string", "is_passed": bool } ], "duplicate_applications": [ { "job_title": "string", "status": "string", "date": "timestamp" } ] }`

### `PATCH /api/v1/admin/applications/{application_id}/status`
* **Purpose:** Manual override of an applicant's status.
* **Request:** JSON `{ "status": "ENDORSED" }`
* **Response (200 OK):** `{ "message": "Status updated", "new_status": "string" }`

### `GET /api/v1/admin/applications/{application_id}/resume`
* **Purpose:** Download/view the applicant's PDF.
* **Request:** None
* **Response (200 OK):** Streams `application/pdf` via `FileResponse` (Rule 13.5)
