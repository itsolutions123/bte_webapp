-- 022: MRF forms and their questions. Option A (separate mrf_* tables), contract DECIDED by the user 2026-11-12 (part 42).
-- Spec: docs/SCHEMA.md section 7 and docs/API_CONTRACT.md section 5 (Admin MRF forms API).
-- Nothing here references or alters forms, job_questions, jobs, brands or business_units. MRF forms never attach to jobs.
-- No scoring columns. Status and question type values are validated in app code (named constants), not by CHECK constraints, as in 021.
-- name is trimmed by app code; the unique index on lower(name) makes the duplicate-name 409 hold even if the endpoint check is bypassed.
-- Partial unique index: at most one classification question per form.
-- mrf_requests and mrf_request_answers are NOT in this migration; they come with the submit step.
-- Idempotent: IF NOT EXISTS throughout.
BEGIN;

CREATE TABLE IF NOT EXISTS mrf_forms (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'DRAFT',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mrf_forms_status ON mrf_forms (status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_mrf_forms_name_lower ON mrf_forms (lower(name));

CREATE TABLE IF NOT EXISTS mrf_form_questions (
    id UUID PRIMARY KEY,
    form_id UUID NOT NULL REFERENCES mrf_forms (id),
    question_type VARCHAR NOT NULL,
    question_text VARCHAR NOT NULL,
    options JSONB NULL,
    is_required BOOLEAN NOT NULL,
    is_classification BOOLEAN NOT NULL DEFAULT false,
    display_order INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_mrf_form_questions_form_id ON mrf_form_questions (form_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_mrf_form_questions_one_classification
    ON mrf_form_questions (form_id) WHERE is_classification;

COMMIT;
