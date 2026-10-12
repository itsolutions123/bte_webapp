-- 002: link jobs to a shared form (many jobs can use one form)
-- Spec: docs/SCHEMA.md section 1 (jobs.form_id) and section 5 (idx_jobs_form_id).
-- Non-destructive and idempotent: existing jobs keep form_id NULL.
BEGIN;

ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS form_id UUID REFERENCES forms(id);

CREATE INDEX IF NOT EXISTS idx_jobs_form_id ON jobs (form_id);

COMMIT;
