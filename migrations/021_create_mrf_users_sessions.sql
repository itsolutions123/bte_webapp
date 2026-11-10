-- 021: MRF portal accounts and sessions. Option A (separate mrf_* tables), confirmed by the user 2026-11-10.
-- Spec: docs/SCHEMA.md section 7 and docs/API_CONTRACT.md section 5, both PROPOSED.
-- Nothing here references or alters users, sessions, forms or job_questions, except approved_by_user_id, which points at the admin who approved.
-- IDs and the lowercase email are set by app code, as with users. Position and department lists are validated in app code (app/mrf_lists.py), not by constraints.
-- status has no CHECK on purpose: rejected/disabled are not answered yet, so adding them later should not need a migration.
-- Idempotent: IF NOT EXISTS throughout. Other mrf_* tables follow in later migrations, one at a time.
BEGIN;

CREATE TABLE IF NOT EXISTS mrf_users (
    id UUID PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR NOT NULL,
    password_hash VARCHAR NOT NULL,
    position VARCHAR NOT NULL,
    department VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at TIMESTAMPTZ NULL,
    approved_by_user_id UUID NULL REFERENCES users (id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_mrf_users_email ON mrf_users (email);
CREATE INDEX IF NOT EXISTS idx_mrf_users_status ON mrf_users (status);

CREATE TABLE IF NOT EXISTS mrf_sessions (
    id VARCHAR PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES mrf_users (id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    last_active_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mrf_sessions_user_id ON mrf_sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_mrf_sessions_expires_at ON mrf_sessions (expires_at);

COMMIT;
