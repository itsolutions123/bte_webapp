-- 004: job_questions gets form-based columns (Form Builder question save)
-- Spec: docs/SCHEMA.md job_questions (form_id, question_type, options, idx_jq_form_order); docs/API_CONTRACT.md section 3 (POST /forms/{form_id}/questions).
-- Non-destructive and idempotent. job_questions had 0 rows on 2026-10-13, so no backfill is needed.
-- form_id and question_type stay NULLABLE for now (old job_id based public routes still read this table); the API enforces them. NOT NULL comes with the final reshape.
-- job_id, parameter_id and expected_answer are relaxed to NULLABLE so a form question can be stored without them. They are NOT dropped: the drops are held and need explicit confirmation.
BEGIN;

ALTER TABLE job_questions
    ADD COLUMN IF NOT EXISTS form_id UUID REFERENCES forms(id),
    ADD COLUMN IF NOT EXISTS question_type VARCHAR NULL,
    ADD COLUMN IF NOT EXISTS options JSONB NULL;

ALTER TABLE job_questions ALTER COLUMN job_id DROP NOT NULL;
ALTER TABLE job_questions ALTER COLUMN parameter_id DROP NOT NULL;
ALTER TABLE job_questions ALTER COLUMN expected_answer DROP NOT NULL;

CREATE INDEX IF NOT EXISTS idx_jq_form_order ON job_questions (form_id, display_order);

COMMIT;
