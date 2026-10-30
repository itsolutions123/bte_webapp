# Database Schema: BTE Careers

## 1. Core Tables

**`brands`**
- `id` (UUID, Primary Key)
- `slug` (String, Unique, Indexed) - e.g., "sapporo", "tsg"
- `name` (String) - e.g., "TSG", "PR", "SAPPORO"
- `archived_at` (Timestamp with time zone, Nullable, Indexed `idx_brands_archived_at`) - NULL = active; set = archived (migration 013, applied 2026-10-21). Archiving a brand cascades in one transaction: every non-archived job of that brand gets the same archive action (unlike forms, which block with 409 while jobs still use them). Archived brands are hidden from the sidebar metadata. No unarchive endpoint exists for brands or forms.

**`jobs`**
- `id` (UUID, Primary Key)
- `brand_id` (UUID, Foreign Key -> brands.id)
- `form_id` (UUID, Foreign Key -> forms.id, nullable, Indexed) - The shared form applicants answer for this job. Many jobs can use one form.
- `slug` (String, Indexed, NOT unique since migration 005) - e.g., "marketing-oic". A label only, generated from the title; the id is the job identifier and titles may repeat.
- `title` (String) - e.g., "Cashier", "Marketing OIC"
- `description` (Text, nullable) - the job description. DECIDED 2026-10-15, NOT implemented yet: it will hold cleaned HTML from a rich text editor (same column, no migration). Existing rows are plain text until converted. See API_CONTRACT.md "Job description format" and SECURITY.md section 6.
- `requirements` (Text, nullable) - the Requirements part of the public job posting (migration 005). DECIDED 2026-10-15, NOT implemented yet: it will hold cleaned HTML from a rich text editor, same as `description` (same column, no migration). Existing rows are plain text until converted. See API_CONTRACT.md "Job description format" and SECURITY.md section 6.
- `pass_threshold` (Integer) - e.g., 75 (Percentage required to pass)
- `pooling_threshold` (Integer) - e.g., 70
  - DECIDED 2026-10-14 (user): the pass/fail thresholds belong on the form, not on the job, and will be set up later. Migration 005 (applied 2026-10-14) made both columns NULLABLE so a job can be created without them. They are NOT dropped (dropping is destructive and needs explicit confirmation). UPDATED 2026-10-15 (user): the thresholds that count live on the form (see `forms`) and apply to every job that uses it; once that is implemented these job columns are never read. PROPOSED, NOT implemented: until then, scoring in `app/routers/public.py` fails on apply while they are NULL.
- `is_active` (Boolean, Nullable in the DB; the API returns false for NULL) - the publish state (decided 2026-10-14): true = published (shown on the public board); false = draft or unpublished (stored the same way). Set by the Publish / Save as draft dropdown when a job is created or edited (decided 2026-10-16, user; replaces the earlier rule that an edit forces false).
- `created_at` (Timestamp with time zone, Nullable, no default; the API returns null when empty; leading column after brand_id in `idx_jobs_brand_created`) - stored in UTC; API responses show it in PHT (+08:00), see API_CONTRACT.md Global Rules (Timestamps). The same convention applies to every timestamp column.
- `expires_at` (Timestamp with time zone, Not Null, Indexed `idx_jobs_expires_at`) - DECIDED 2026-10-16 (user): every job gets a 30-day expiry on creation (app-level: `created_at` + 30 days, not a DB default/trigger). The Renew button sets a new `expires_at` via a manual date picker (future timestamp only, 422 otherwise; see API_CONTRACT.md). Expiry hides a job from public endpoints only (`is_active = true AND expires_at > now()`) — it does NOT archive the row; the admin job list/detail keeps showing it with a computed `is_expired` flag. Migration 009 (applied 2026-10-16) added this column and backfilled all existing jobs to `created_at` + 30 days (8/8 rows verified live).
- `archived_at` (Timestamp with time zone, Nullable, Indexed `idx_jobs_archived_at`) - DECIDED 2026-10-16 (user): mirrors `forms.archived_at` exactly (migration 003) — NULL = active; set = archived. A deliberate, separate admin action from expiry (Archive button): pulls the job out of the brand's active job list into Archive, same semantics as forms. Independent of `expires_at` — a job can be expired and not archived (the default end state), or archived before or after expiring. Migration 009 (applied 2026-10-16).
- `location` (String, nullable, no index) - DECIDED 2026-10-16 (user); migration 011, applied 2026-10-16 (existing jobs are NULL). Free text for the job location, e.g. "Remote in Manila". The API trims it, stores an empty value as NULL and rejects more than 150 characters (enforced by the API, not the DB). Shown on the job list cards and in the job detail "Job details" block.
- `pay_information` (String, nullable, no index) - DECIDED 2026-10-16 (user); migration 011. Free text, same rules as `location`. A NULL shows as "Pay information not provided" on the website.
- `job_type` (String, nullable, no index) - DECIDED 2026-10-16 (user, option A); migration 011. A fixed list validated by the API: Full-time, Part-time, Onsite (see API_CONTRACT.md "Job details fields"). There is no DB CHECK on purpose, so a new value is a contract and code change, not a migration.

**`applicants`**
- `id` (UUID, Primary Key)
- `first_name` (String)
- `last_name` (String)
- `email` (String, Unique, Indexed)
- `phone` (String, Indexed) - shown as "Contact number" in the UI
- `address` (String, nullable) - migration 008, applied to the live DB 2026-10-15. A fixed field collected on step 1 of the apply flow (not a form question).
- `gender` (String, nullable) - migration 008, applied 2026-10-15. A fixed step 1 field. Sensitive: Security decides who may see it and how long it is kept (SECURITY.md update pending).
- `date_of_birth` (Date, nullable) - migration 008, applied 2026-10-15. A fixed step 1 field. Decided by the user: the date of birth is stored, not an age; the applicant page shows the age calculated from it. Sensitive PII: Security decides access and retention.
- `created_at` (Timestamp)

## 2. Forms, Questions & Points

**`forms`** (shared template: many jobs can use one form, e.g. PR and TSG jobs answer the same form)
- `id` (UUID, Primary Key)
- `slug` (String, Unique, Indexed) - e.g., "general-screening"; used in API paths such as /forms/{form_slug}/jobs/{job_id}; admin page URLs use the form id (/admin/forms/{form-UID})
- `name` (String, Not Null) - e.g., "IT Recruitment"
- `created_at` (Timestamp)
- `archived_at` (Timestamp with time zone, Nullable, Indexed `idx_forms_archived_at`) - NULL = active; set = archived (migration 003, applied 2026-10-13). Archived forms are hidden from the sidebar and the default forms list, appear only under Archive > Forms, and keep their slug reserved. A form can't be archived while any job still uses it (`jobs.form_id`).
- `pass_threshold` (Integer, nullable) - PROPOSED 2026-10-15, not migrated yet (migration 009). The percentage a job's score must reach to PASS. It applies to every job that uses this form. Range 0-100, enforced by the API.
- `pooling_threshold` (Integer, nullable) - PROPOSED 2026-10-15, not migrated yet (migration 009). A score at or above this but below `pass_threshold` is POOLING. Must not exceed `pass_threshold`.
- A form with NULL thresholds cannot score applications: applying to a job that uses it returns 409 (PROPOSED default, pending Structure confirmation).

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
- `options` (JSONB, nullable) - `MULTIPLE_CHOICE`: array of 3 or more `{"id": "string", "text": "string"}` objects; `id` is a stable, server-assigned identifier (not shown to applicants) that `answer_points.answer_value` and applicant answers reference, so it must not change when an option is edited. `YES_NO`: array of exactly 2 label texts, `options[0]` is the display label for answer `YES` and `options[1]` for `NO`; null falls back to the labels Yes / No. `OPEN_ENDED`: null
- `is_hard_requirement` (Boolean) - Must be false for `OPEN_ENDED`
- `is_required` (Boolean, Not Null) - PROPOSED 2026-10-14, not migrated yet. The applicant must answer this question to submit. Backfill for existing rows: true for `YES_NO` and `MULTIPLE_CHOICE`, false for `OPEN_ENDED`. Not the same as `is_hard_requirement` (which auto-fails a wrong answer); `is_hard_requirement` true requires `is_required` true.
- `field_key` (String, nullable) - PROPOSED 2026-10-14 (Option A, chosen by the user), not migrated yet. Marks a "standard" element: one of `address`, `gender`, `date_of_birth` (name, email and contact number stay fixed fields on apply, not form elements); NULL for ordinary questions. `question_type` is unchanged and must be `OPEN_ENDED`; `field_key` cannot change after create. A question with a `field_key` is excluded from scoring (not in the divisor, no FAIL row, `is_hard_requirement` must be false). On submit its value is saved as an ordinary answer AND copied to the matching `applicants` column. At most one question per `field_key` per form (partial unique index on (form_id, field_key) WHERE field_key IS NOT NULL, to be created in the same migration).
- `expected_answer` is REMOVED: "wrong" is now defined by FAIL points on an answer choice (see answer_points).

**`answer_points`** (the admin cheat sheet: what each answer choice is worth)
- `id` (UUID, Primary Key)
- `question_id` (UUID, Foreign Key -> job_questions.id, Not Null, Indexed)
- `answer_value` (String, Not Null) - `YES` or `NO` for YES_NO; the chosen option's `id` (from `job_questions.options`) for MULTIPLE_CHOICE
- `job_id` (UUID, Foreign Key -> jobs.id, Not Null) - PROPOSED 2026-10-15, not migrated yet (migration 010 creates the table). The job this row applies to. Pass/fail is set PER JOB (decided 2026-10-15): the same answer can fail one job and pass another. The job must use the question's form (`jobs.form_id` = `job_questions.form_id`), enforced by the API.
- `target_type` (String, Not Null) - `FAIL` is the only value for now (the column stays so other targets can be added later). A FAIL row marks that answer choice as failing for that job.
- The BRAND target, `brand_id` and `points` are dropped from the design (2026-10-15): the score is the percent of scored questions with no FAIL row for the job, so weighted points would have no effect. They can be added later if wanted.
- One answer choice may have several rows, one per job it fails (e.g. fails Cashier but passes Store Supervisor). A unique key on (question_id, answer_value, job_id) is PROPOSED.
- `OPEN_ENDED` questions have no rows: the applicant's full text is stored and never scored.

Scoring rules (enforced by the API, recorded in API_CONTRACT.md):
- `calculated_score` = percent of scored questions (YES_NO and MULTIPLE_CHOICE) whose chosen answer has no FAIL row for the job applied to (PROPOSED 2026-10-15, NOT implemented). OPEN_ENDED is excluded from the divisor. The form's `pass_threshold` and `pooling_threshold` (see `forms`) decide the status.
- `is_hard_requirement`: if the chosen answer has a FAIL row for the job applied to, the application gets `has_hard_fail_flag` and status FAILED.
- Suggested fit (PROPOSED 2026-10-15, replaces the brand-level fit, NOT implemented): at submit, the same answers are scored once for every other job that uses the same form and has at least one `answer_points` row (a job with no rows would score 100 and always look like a better fit, so it is not compared). If another job scores higher than the job applied to AND the answers hit no hard fail for that job (a hard-requirement question whose chosen answer has a FAIL row for that job; decided 2026-10-15, hard-requirement questions are non-negotiable), one `application_fits` row is stored for it. A job the applicant hard-fails is never stored or shown as a fit. The flag only informs the admin, for example 76/100 on Store Supervisor and 80/100 on Operations Manager, and never changes the score or status. Fit rows are computed once at submit and read from storage afterwards, never rescored in list views. Only jobs on the applicant's own form are compared, because the applicant answered only that form's questions.
- Required answers (PROPOSED 2026-10-14, target behaviour, NOT what the code does today): a question with `is_required` true must be answered to submit, and the API rejects a missing or blank required answer. An unanswered optional scored question is excluded from the divisor. The older claim that every scored question is always required was never enforced by the code.
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
- `brand_points` (JSONB, nullable) - RETIRED 2026-10-15: job-level fit (see `application_fits`) replaces brand-level fit. If the column exists in the live DB it is unused; it is not dropped without your explicit confirmation (UNVERIFIED whether it exists).
- `has_hard_fail_flag` (Boolean) - True if any hard requirement was missed
- `status` (String, Indexed) - e.g., "NEW", "POOLING", "PASSED", "FAILED", "ENDORSED", "HIRED". Since 2026-10-19 the capture-first apply writes every new application as "NEW" (score NULL, no hard-fail flag) and increments `status_counts` (job, "NEW"). The dashboard cards and tally have no NEW column yet.
- `is_manual_override` (Boolean) - True if status was changed by admin
- `overridden_by_id` (UUID, nullable)
- `overridden_at` (Timestamp, nullable)
- `created_at` (Timestamp, Indexed)

**`answers`**
- `id` (UUID, Primary Key)
- `application_id` (UUID, Foreign Key -> applications.id)
- `job_question_id` (UUID, Foreign Key -> job_questions.id)
- `applicant_answer` (String)
- `is_passed` (Boolean, nullable) - True when the chosen answer has no FAIL row in answer_points (YES_NO and MULTIPLE_CHOICE); NULL for OPEN_ENDED (not scored). For OPEN_ENDED, `applicant_answer` holds the applicant's full text. Migration 012 (applied 2026-10-19) dropped NOT NULL on the live column and `Answer.is_passed` is `nullable=True` in the model; the capture-first apply stores NULL for every answer until scoring exists.

**`application_fits`** (PROPOSED 2026-10-15, not migrated yet, migration number TO BE RENUMBERED by Structure: 011 and 012 are taken; job-level suggested fit)
- `application_id` (UUID, Foreign Key -> applications.id, Not Null)
- `job_id` (UUID, Foreign Key -> jobs.id, Not Null) - another job on the same form that the same answers score higher on than the job applied to
- `score` (Integer, Not Null) - percent for that job, same rule as `calculated_score`
- *Primary Key:* `(application_id, job_id)`. Written once at submit and never recomputed. Read by the applicant detail page (and the job cards once wired).

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
- `idx_jobs_brand_created` ON jobs (brand_id, created_at DESC NULLS LAST, id) - serves GET /api/v1/admin/brands/{brand_id}/jobs (migration 006, applied 2026-10-14)
- `idx_jobs_title_trgm` ON jobs USING gin (title gin_trgm_ops) - typo-tolerant title search for GET /api/v1/admin/brands/{brand_id}/jobs `q` (migration 007, applied 2026-10-14; also installs extension `pg_trgm` 1.6)
- `idx_forms_archived_at` ON forms (archived_at)
- `idx_brands_archived_at` ON brands (archived_at) - brand archive filter (migration 013, applied 2026-10-21)
- `idx_answer_points_question_id` ON answer_points (question_id)
- `uq_answer_points_q_answer_job` UNIQUE ON answer_points (question_id, answer_value, job_id) - PROPOSED 2026-10-15 (migration 010)
- `idx_answers_application_id` ON answers (application_id)

## 6. Authentication
Columns below are verified against `app/models.py` (lines 140-165) on 2026-10-30; tables created by migrations 014 and 015. This section was missing from SCHEMA.md until now (the 2026-10-30 handover said it had been added with commit 8bc32cb, but that commit did not touch this file).

**users**
- `id` UUID, primary key
- `email` string, NOT NULL, unique (`idx_users_email`)
- `password_hash` string, NOT NULL (bcrypt via passlib, never returned by any endpoint)
- `role` string, NOT NULL; free text in the DB (no CHECK constraint), validated at the API layer as SUPERADMIN, MANAGER or RECRUITER
- `is_active` boolean, NOT NULL, default true
- `created_at` timestamptz
- `last_login_at` timestamptz, nullable
- `full_name` string, nullable, trimmed, max 100 characters. APPLIED and VERIFIED LIVE 2026-10-30 (migration 016: `character varying(100)`, nullable; the users table had 1 row, 0 names), and added to the `User` model in `app/models.py`. Shown on the profile card; null means the card shows no name. Existing SUPERADMIN row to be filled with one confirmed UPDATE after the migration.

**sessions**
- `id` string, primary key (the session token, `secrets.token_urlsafe(32)`)
- `user_id` UUID, NOT NULL, FK to `users.id`
- `created_at` timestamptz
- `expires_at` timestamptz, NOT NULL (fixed 8-hour hard cap from login, never extended)
- `last_active_at` timestamptz (for the planned 10-minute idle timeout, not enforced yet)
