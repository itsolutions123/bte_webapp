-- 003: archive support for forms (Archive module)
-- Spec: docs/API_CONTRACT.md section 3 (POST /forms/{form_id}/archive, GET /forms?archived=). docs/SCHEMA.md entry for forms.archived_at still to be added.
-- Non-destructive and idempotent: existing forms keep archived_at NULL (active).
BEGIN;

ALTER TABLE forms
    ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ NULL;

CREATE INDEX IF NOT EXISTS idx_forms_archived_at ON forms (archived_at);

COMMIT;
