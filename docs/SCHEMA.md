# Database Schema: BTE Careers

## 1. Core Tables

**`brands`**
- `id` (UUID, Primary Key)
- `slug` (String, Unique, Indexed) - e.g., "sapporo", "tsg"
- `name` (String) - e.g., "TSG", "PR", "SAPPORO"

**`jobs`**
- `id` (UUID, Primary Key)
- `brand_id` (UUID, Foreign Key -> brands.id)
- `form_id` (UUID, Foreign Key -> forms.id, nullable, Indexed) - The shared form applicants answer for this job. Many jobs can use one form.
- `slug` (String, Unique, Indexed) - e.g., "marketing-oic"
- `title` (String) - e.g., "Cashier", "Marketing OIC"
- `description` (Text)
- `pass_threshold` (Integer) - e.g., 75 (Percentage required to pass)
- `pooling_threshold` (Integer) - e.g., 70
- `is_active` (Boolean)
- `created_at` (Timestamp)

**`applicants`**
- `id` (UUID, Primary Key)
- `first_name` (String)
- `last_name` (String)
- `email` (String, Unique, Indexed)
- `phone` (String, Indexed)
- `created_at` (Timestamp)

## 2. Forms, Questions & Points

**`forms`** (shared template: many jobs can use one form, e.g. PR and TSG jobs answer the same form)
- `id` (UUID, Primary Key)
- `slug` (String, Unique, Indexed) - e.g., "general-screening"; used in API paths such as /forms/{form_slug}/jobs/{job_id}; admin page URLs use the form id (/admin/forms/{form-UID})
- `name` (String, Not Null) - e.g., "IT Recruitment"
- `created_at` (Timestamp)
- `archived_at` (Timestamp with time zone, Nullable, Indexed `idx_forms_archived_at`) - NULL = active; set = archived (migration 003, applied 2026-10-13). Archived forms are hidden from the sidebar and the default forms list, appear only under Archive > Forms, and keep their slug reserved. A form can't be archived while any job still uses it (`jobs.form_id`).

Each job points to at most one form through `jobs.form_id`. The applicant picks a job from the website posting and answers that job's form.

**`parameters`** (LEGACY - kept for now, no longer used by forms; retire in a separate confirmed step)
- `id` (UUID, Primary Key)
- `slug` (String, Unique, Indexed)
- `name` (String)
- `description` (Text)

**`job_questions`** (the questions of a form; table name kept for now to limit migration, a rename to form_questions is a later step)
- `id` (UUID, Primary Key)
- `form_id` (UUID, Foreign Key -> forms.id, Not Null) - REPLACES job_id
- `parameter_id` (UUID, Foreign Key -> parameters.id, **nullable**) - Legacy link, optional
- `display_order` (Integer, Not Null) - Sequence in the one-question-at-a-time wizard
- `question_type` (String, Not Null) - One of `YES_NO`, `MULTIPLE_CHOICE`, `OPEN_ENDED`
- `question_text` (String)
- `options` (JSONB, nullable) - `MULTIPLE_CHOICE`: array of exactly 4 option texts in order A-D. `YES_NO`: array of exactly 2 label texts, `options[0]` is the display label for answer `YES` and `options[1]` for `NO`; null falls back to the labels Yes / No. `OPEN_ENDED`: null
- `is_hard_requirement` (Boolean) - Must be false for `OPEN_ENDED`
- `expected_answer` is REMOVED: "wrong" is now defined by FAIL points on an answer choice (see answer_points).

**`answer_points`** (the admin cheat sheet: what each answer choice is worth)
- `id` (UUID, Primary Key)
- `question_id` (UUID, Foreign Key -> job_questions.id, Not Null, Indexed)
- `answer_value` (String, Not Null) - `YES` or `NO` for YES_NO; `A` to `D` for MULTIPLE_CHOICE
- `target_type` (String, Not Null) - `BRAND` or `FAIL`
- `brand_id` (UUID, Foreign Key -> brands.id, nullable) - Required when target_type is BRAND, null when FAIL
- `points` (Integer, Not Null, default 1) - For FAIL the amount is ignored: any FAIL row marks that choice as failing
- One answer choice may have several rows (e.g. "+1 Pares Retiro" and "+1 fail").
- `OPEN_ENDED` questions have no rows: the applicant's full text is stored and never scored.

Scoring rules (enforced by the API, recorded in API_CONTRACT.md):
- `calculated_score` = percent of scored questions (YES_NO and MULTIPLE_CHOICE) whose chosen answer has no FAIL row. OPEN_ENDED is excluded from the divisor. `pass_threshold`, `pooling_threshold` and statuses work as before.
- `is_hard_requirement`: if the chosen answer has a FAIL row, the application gets `has_hard_fail_flag` and status FAILED.
- Brand points are summed per brand per application and drive only the suggested-fit flag. They never change the score or status. The flag is derived: brands with the highest total above 0. More than one means a tie ("suited for both ..."). If no brand has points, no flag.
- Assumption: every scored question must be answered to submit (the API rejects a submission with missing answers).
- Migration note (UNVERIFIED): existing rows have `job_id` and `expected_answer`. A migration must create a form per existing job, move its questions, convert each `expected_answer` into FAIL rows on the non-expected choices, and only then drop the old columns. Dropping them is destructive and needs your explicit confirmation.

## 3. Applications & Answers

**`applications`**
- `id` (UUID, Primary Key)
- `applicant_id` (UUID, Foreign Key -> applicants.id, Indexed)
- `job_id` (UUID, Foreign Key -> jobs.id, Indexed)
- `terms_version` (String) - e.g., "v1.0" (RA 10173 consent)
- `consent_agreed` (Boolean) - Must be true
- `resume_path` (String) - Local filesystem path
- `resume_filename` (String) - Original filename
- `resume_size_bytes` (Integer)
- `parsed_data` (JSONB) - Text/skills extracted asynchronously from PDF
- `calculated_score` (Integer) - Computed percentage (e.g., 78), over scored questions only
- `brand_points` (JSONB, nullable) - Map of brand id to summed points; source of the suggested-fit and tie flag
- `has_hard_fail_flag` (Boolean) - True if any hard requirement was missed
- `status` (String, Indexed) - e.g., "NEW", "POOLING", "PASSED", "FAILED", "ENDORSED", "HIRED"
- `is_manual_override` (Boolean) - True if status was changed by admin
- `overridden_by_id` (UUID, nullable)
- `overridden_at` (Timestamp, nullable)
- `created_at` (Timestamp, Indexed)

**`answers`**
- `id` (UUID, Primary Key)
- `application_id` (UUID, Foreign Key -> applications.id)
- `job_question_id` (UUID, Foreign Key -> job_questions.id)
- `applicant_answer` (String)
- `is_passed` (Boolean, nullable) - True when the chosen answer has no FAIL row in answer_points (YES_NO and MULTIPLE_CHOICE); NULL for OPEN_ENDED (not scored). For OPEN_ENDED, `applicant_answer` holds the applicant's full text.

## 4. Aggregation (Live Tally)

**`status_counts`** (Incrementally updated per Rule 13.3, avoids COUNT(*) table scans)
- `job_id` (UUID, Foreign Key -> jobs.id)
- `status` (String)
- `count` (Integer)
- *Primary Key:* `(job_id, status)`

## 5. Mandatory Indexes (Rule 13.1)
- `idx_app_job_id` ON applications (job_id)
- `idx_app_status` ON applications (status)
- `idx_app_applicant_id` ON applications (applicant_id)
- `idx_app_created_at` ON applications (created_at)
- `idx_applicant_email` ON applicants (email)
- `idx_jq_form_order` ON job_questions (form_id, display_order)
- `idx_jobs_form_id` ON jobs (form_id)
- `idx_forms_archived_at` ON forms (archived_at)
- `idx_answer_points_question_id` ON answer_points (question_id)
- `idx_answers_application_id` ON answers (application_id)
