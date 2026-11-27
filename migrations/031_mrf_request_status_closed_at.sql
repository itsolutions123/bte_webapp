-- 031: MRF request status becomes four values and mrf_requests gains closed_at.
-- Contract: docs/API_CONTRACT.md, PATCH /api/v1/admin/mrf/requests/{request_id}/status (CONTRACTED 2026-11-27).
-- Old to new: Pending and Approved become 'ON GOING MRF' (that distinction is lost; decided_at and decided_by_user_id still tell them apart),
-- Rejected becomes 'CANCELLED MRF' (remarks kept). closed_at stays NULL for every existing row (no old status means closed).
-- Keep the CHECK in step with MRF_REQUEST_STATUSES in app/mrf_lists.py.
BEGIN;

ALTER TABLE mrf_requests DROP CONSTRAINT IF EXISTS ck_mrf_requests_status;

UPDATE mrf_requests SET status = 'ON GOING MRF' WHERE status IN ('Pending', 'Approved');
UPDATE mrf_requests SET status = 'CANCELLED MRF' WHERE status = 'Rejected';

ALTER TABLE mrf_requests ALTER COLUMN status SET DEFAULT 'ON GOING MRF';
ALTER TABLE mrf_requests
    ADD CONSTRAINT ck_mrf_requests_status
    CHECK (status IN ('ON GOING MRF', 'PARTIALLY CLOSED MRF', 'CLOSED MRF', 'CANCELLED MRF'));

ALTER TABLE mrf_requests ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ NULL;
CREATE INDEX IF NOT EXISTS idx_mrf_requests_closed_at ON mrf_requests (closed_at);

COMMIT;
