-- 019: job_questions.correct_answer (per-form answer key). Decided by the user 2026-11-07 (Option A).
-- Spec: docs/SCHEMA.md (job_questions.correct_answer, "Form scoring rules") and docs/API_CONTRACT.md (form question endpoints), both PROPOSED, commit e21641f.
-- Non-destructive and idempotent: existing rows get NULL (not scored). expected_answer is left untouched (legacy, unused by scoring); dropping it needs the user's explicit confirmation.
-- Value shape is enforced by the API, not here: YES_NO "YES" or "NO", MULTIPLE_CHOICE a non-empty array of option ids, otherwise NULL.
-- No index: the key is only read together with one form's questions (idx_jq_form_order), a bounded row set (rule 18.1).
-- Number 019 follows 018; 010 was reserved by the superseded answer_points design and was never created.
BEGIN;

ALTER TABLE job_questions
    ADD COLUMN IF NOT EXISTS correct_answer JSONB NULL;

COMMIT;
