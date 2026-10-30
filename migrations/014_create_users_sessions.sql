-- Migration 014: users and sessions tables for RBAC admin login
-- Roles: SUPERADMIN, MANAGER, RECRUITER — validated at the API layer only,
-- no DB CHECK (same pattern as jobs.job_type, decided 2026-10-16).
-- sessions has no IP column, consistent with SECURITY.md's no-IP-logging policy.

CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR NOT NULL,
    password_hash VARCHAR NOT NULL,
    role VARCHAR NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX idx_users_email ON users (email);

CREATE TABLE sessions (
    id VARCHAR PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_sessions_user_id ON sessions (user_id);
CREATE INDEX idx_sessions_expires_at ON sessions (expires_at);
