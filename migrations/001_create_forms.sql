-- 001: create the forms table (shared form template; many jobs can use one form)
-- Spec: docs/SCHEMA.md section 2. Non-destructive and idempotent.
BEGIN;

CREATE TABLE IF NOT EXISTS forms (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug       VARCHAR NOT NULL,
    name       VARCHAR NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_forms_slug ON forms (slug);

COMMIT;
