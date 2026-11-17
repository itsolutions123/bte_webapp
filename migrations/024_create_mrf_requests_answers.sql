-- 024: MRF requests and their answers (part 66 step 1).
-- Contract DECIDED by the user 2026-11-17 (parts 64 and 65).
-- Spec: docs/SCHEMA.md section 7 and docs/API_CONTRACT.md section 5.
-- Status is the one value list checked in the database: Pending,
-- Approved, Rejected. Keep in step with MRF_REQUEST_STATUSES in
-- app/mrf_lists.py.
-- The remarks cap (500) and the answer cap (1000) are enforced in app
-- code (MRF_REMARKS_MAX_LENGTH, MRF_ANSWER_MAX_LENGTH), not here.
-- No ON DELETE on any foreign key, as in 022. The answered-question
-- 409 on question DELETE is app code.
-- Idempotent: IF NOT EXISTS throughout.
BEGIN;

CREATE TABLE IF NOT EXISTS mrf_requests (
    id UUID PRIMARY KEY,
    form_id UUID NOT NULL REFERENCES mrf_forms (id),
    user_id UUID NOT NULL REFERENCES mrf_users (id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    classification VARCHAR NOT NULL,
    department VARCHAR NULL,
    assignment VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'Pending',
    remarks TEXT NULL,
    decided_by_user_id UUID NULL REFERENCES users (id),
    decided_at TIMESTAMPTZ NULL,
    CONSTRAINT ck_mrf_requests_status
        CHECK (status IN ('Pending', 'Approved', 'Rejected'))
);

CREATE INDEX IF NOT EXISTS idx_mrf_requests_status
    ON mrf_requests (status);
CREATE INDEX IF NOT EXISTS idx_mrf_requests_classification
    ON mrf_requests (classification);
CREATE INDEX IF NOT EXISTS idx_mrf_requests_department
    ON mrf_requests (department);
CREATE INDEX IF NOT EXISTS idx_mrf_requests_created_at
    ON mrf_requests (created_at);
CREATE INDEX IF NOT EXISTS idx_mrf_requests_user_id
    ON mrf_requests (user_id);

CREATE TABLE IF NOT EXISTS mrf_request_answers (
    id UUID PRIMARY KEY,
    request_id UUID NOT NULL REFERENCES mrf_requests (id),
    question_id UUID NOT NULL REFERENCES mrf_form_questions (id),
    answer TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_mrf_request_answers_request_question
    ON mrf_request_answers (request_id, question_id);
CREATE INDEX IF NOT EXISTS idx_mrf_request_answers_question_id
    ON mrf_request_answers (question_id);

COMMIT;
