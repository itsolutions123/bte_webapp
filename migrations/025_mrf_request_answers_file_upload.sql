-- 025: FILE_UPLOAD question answers on mrf_request_answers.
-- Contract DECIDED by the user 2026-11-23 (docs/API_CONTRACT.md FILE_UPLOAD entry,
-- docs/SCHEMA.md mrf_request_answers section).
-- answer becomes nullable: a FILE_UPLOAD answer stores no text, only the three
-- new file columns below (answer_file_path/_name/_size). All three are NULL for
-- every other question_type.
-- Idempotent: IF NOT EXISTS / safe ALTER throughout.
BEGIN;

ALTER TABLE mrf_request_answers
    ALTER COLUMN answer DROP NOT NULL;

ALTER TABLE mrf_request_answers
    ADD COLUMN IF NOT EXISTS answer_file_path VARCHAR NULL,
    ADD COLUMN IF NOT EXISTS answer_file_name VARCHAR NULL,
    ADD COLUMN IF NOT EXISTS answer_file_size INTEGER NULL;

COMMIT;
