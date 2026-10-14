-- 006: index for the brand page job list (GET /api/v1/admin/brands/{brand_id}/jobs)
-- Spec: docs/API_CONTRACT.md GET /api/v1/admin/brands/{brand_id}/jobs; Structure decision 2026-10-14 (user: Option B).
-- Non-destructive. Adds one index only; no columns or rows are changed. jobs has 6 test rows on 2026-10-14.
-- The key matches the endpoint's ORDER BY (created_at DESC NULLS LAST, id) so the planner can read rows in order per brand.
BEGIN;

CREATE INDEX IF NOT EXISTS idx_jobs_brand_created ON jobs (brand_id, created_at DESC NULLS LAST, id);

COMMIT;
