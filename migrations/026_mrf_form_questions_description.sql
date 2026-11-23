-- 026: optional description on MRF form questions.
-- Contract DECIDED 2026-11-23 (docs/API_CONTRACT.md, "Question description" bullet
-- under POST /api/v1/admin/mrf/forms/{form_id}/questions).
-- description is NULL for every existing row and for any question saved without one.
-- The 500-character limit is enforced in the application, like question_text.
-- No index: it is never filtered or sorted on.
-- Idempotent: IF NOT EXISTS.
BEGIN;

ALTER TABLE mrf_form_questions
    ADD COLUMN IF NOT EXISTS description VARCHAR NULL;

COMMIT;
