-- 009: expiry and archive support for jobs (job detail modal — Edit/Renew/Archive buttons)
-- Spec: docs/API_CONTRACT.md (job detail modal buttons had no backend as of 2026-10-15; this adds it).
-- Decision (user, 2026-10-16): every job gets a 30-day expiry on creation (app-level, created_at + 30 days,
--   not a DB default). Renew sets a new expires_at via a manual date picker (future timestamp only).
--   Expiry hides a job from public endpoints only (is_active AND expires_at > now()) — it does NOT archive it;
--   admin keeps seeing it with an is_expired indicator. Archive is a separate, deliberate action mirroring
--   forms.archived_at exactly (see 003_add_forms_archived_at.sql) — pulls the job out of the admin's active
--   list into /admin/archive. The two states are independent: a job can be expired and not archived (default
--   end state), or archived before or after expiring.
-- Non-destructive. Existing jobs (CASHIER, CREW, Store Supervisor, etc.) are backfilled to
--   COALESCE(created_at, now()) + 30 days so none of them vanish from the public board immediately.
BEGIN;

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ NULL;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ NULL;

UPDATE jobs
SET expires_at = COALESCE(created_at, now()) + INTERVAL '30 days'
WHERE expires_at IS NULL;

ALTER TABLE jobs ALTER COLUMN expires_at SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_jobs_expires_at ON jobs (expires_at);
CREATE INDEX IF NOT EXISTS idx_jobs_archived_at ON jobs (archived_at);

COMMIT;
