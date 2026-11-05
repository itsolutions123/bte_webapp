-- 018: Users RBAC columns and jobs.assignee_user_id. Decided by the user 2026-11-05.
-- Spec: docs/SCHEMA.md (users, jobs) and docs/API_CONTRACT.md (admin users endpoints), both PROPOSED.
-- Non-destructive and idempotent: existing users keep NULL in the new nullable columns, must_change_password defaults to false, full_name is untouched.
-- Name columns are 100 chars, same as full_name. Archiving a user also sets is_active=false (app logic, not a constraint).
-- jobs.assignee_user_id: one nullable assignee per job. MANAGER/RECRUITER only is enforced in app code, not here.
-- Index on jobs(assignee_user_id) per rule 18.1 (recruiter filtering). No extra indexes on users: staff table, far below a few hundred rows.
BEGIN;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS first_name VARCHAR(100) NULL,
    ADD COLUMN IF NOT EXISTS last_name VARCHAR(100) NULL,
    ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ NULL,
    ADD COLUMN IF NOT EXISTS added_by_user_id UUID NULL REFERENCES users (id),
    ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS assignee_user_id UUID NULL REFERENCES users (id);

CREATE INDEX IF NOT EXISTS idx_jobs_assignee_user_id ON jobs (assignee_user_id);

COMMIT;
