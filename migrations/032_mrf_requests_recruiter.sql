-- 032: mrf_requests gains recruiter_user_id (the recruiter credited for the MRF).
-- Contract: docs/API_CONTRACT.md, PATCH /api/v1/admin/mrf/requests/{request_id}/recruiter (CONTRACTED 2026-11-27, commit caa5c97).
-- Additive: one nullable column, no default, no data change. Every existing row stays NULL (Unassigned, scores nobody).
-- ON DELETE SET NULL like candidates.assigned_to_id: users are archived, not deleted, so this should never fire.
-- Index for the Recruiters metrics endpoint, which will group and filter on this column (rule 18.1).
BEGIN;

ALTER TABLE mrf_requests
    ADD COLUMN IF NOT EXISTS recruiter_user_id UUID NULL REFERENCES users (id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_mrf_requests_recruiter_user_id ON mrf_requests (recruiter_user_id);

COMMIT;
