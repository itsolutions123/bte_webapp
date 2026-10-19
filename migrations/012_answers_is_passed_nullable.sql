-- 012: answers.is_passed becomes nullable (capture-first apply slice, docs/API_CONTRACT.md).
-- Decision (user, 2026-10-19): the first apply rewrite stores raw answers with no scoring, so is_passed
--   stays NULL until scoring exists. OPEN_ENDED answers are never scored and stay NULL permanently
--   (docs/SCHEMA.md).
-- Non-destructive: only relaxes a constraint; existing rows keep their values. Safe to re-run.
-- Rollback: ALTER TABLE answers ALTER COLUMN is_passed SET NOT NULL; (fails while any row is NULL,
--   so those rows must be dealt with first).
-- No indexes: is_passed is not used in a WHERE, JOIN or ORDER BY (rule 18.1).
BEGIN;

ALTER TABLE answers ALTER COLUMN is_passed DROP NOT NULL;

COMMIT;
