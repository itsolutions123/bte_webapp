# Database Schema: BTE Careers

## 1. Core Tables

**`brands`**
* `id` (UUID, Primary Key)
* `name` (String) - e.g., "TSG", "PR", "SAPPORO"

**`jobs`**
* `id` (UUID, Primary Key)
* `brand_id` (UUID, Foreign Key -> brands.id)
* `title` (String) - e.g., "Cashier", "Marketing OIC"
* `description` (Text)
* `pass_threshold` (Integer) - e.g., 75 (Percentage required to pass)
* `pooling_threshold` (Integer) - e.g., 70
* `is_active` (Boolean)
* `created_at` (Timestamp)

**`applicants`**
* `id` (UUID, Primary Key)
* `first_name` (String)
* `last_name` (String)
* `email` (String, Unique, Indexed)
* `phone` (String, Indexed)
* `created_at` (Timestamp)

## 2. Forms & Parameters

**`parameters`** (Global reusable filters/questions)
* `id` (UUID, Primary Key)
* `name` (String) - e.g., "Gambling History", "Years of Experience"
* `description` (Text)

**`job_questions`** (Linking parameters to jobs with expected outcomes)
* `id` (UUID, Primary Key)
* `job_id` (UUID, Foreign Key -> jobs.id)
* `parameter_id` (UUID, Foreign Key -> parameters.id)
* `question_text` (String) - e.g., "Do you gamble?"
* `expected_answer` (String) - e.g., "NO"
* `is_hard_requirement` (Boolean) - If true and failed, flags the application.

## 3. Applications & Answers

**`applications`**
* `id` (UUID, Primary Key)
* `applicant_id` (UUID, Foreign Key -> applicants.id, Indexed)
* `job_id` (UUID, Foreign Key -> jobs.id, Indexed)
- `terms_version` (String) - e.g., "v1.0" (RA 10173 consent)
- `consent_agreed` (Boolean) - Must be true
* `resume_path` (String) - Local filesystem path
* `resume_filename` (String) - Original filename
* `resume_size_bytes` (Integer)
* `parsed_data` (JSONB) - Text/skills extracted asynchronously from PDF
* `calculated_score` (Integer) - Computed percentage (e.g., 78)
* `has_hard_fail_flag` (Boolean) - True if any hard requirement was missed
* `status` (String, Indexed) - e.g., "NEW", "POOLING", "PASSED", "FAILED", "ENDORSED", "HIRED"
* `is_manual_override` (Boolean) - True if status was changed by admin
* `overridden_by_id` (UUID, nullable)
* `overridden_at` (Timestamp, nullable)
* `created_at` (Timestamp, Indexed)

**`answers`**
* `id` (UUID, Primary Key)
* `application_id` (UUID, Foreign Key -> applications.id)
* `job_question_id` (UUID, Foreign Key -> job_questions.id)
* `applicant_answer` (String)
* `is_passed` (Boolean) - Evaluated against job_questions.expected_answer

## 4. Aggregation (Live Tally)

**`status_counts`** (Incrementally updated per Rule 13.3, avoids COUNT(*) table scans)
* `job_id` (UUID, Foreign Key -> jobs.id)
* `status` (String)
* `count` (Integer)
* *Primary Key:* `(job_id, status)`

## 5. Mandatory Indexes (Rule 13.1)
* `idx_app_job_id` ON applications (job_id)
* `idx_app_status` ON applications (status)
* `idx_app_applicant_id` ON applications (applicant_id)
* `idx_app_created_at` ON applications (created_at)
* `idx_applicant_email` ON applicants (email)
