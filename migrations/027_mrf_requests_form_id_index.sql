-- Migration 027: index on mrf_requests.form_id (rule 18.1).
-- Used by the MRF form delete check (count of requests for a form).
-- Idempotent: safe to run more than once.
CREATE INDEX IF NOT EXISTS idx_mrf_requests_form_id ON mrf_requests (form_id);
