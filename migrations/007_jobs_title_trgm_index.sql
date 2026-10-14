-- 007: typo-tolerant title search for the brand page job list (GET /api/v1/admin/brands/{brand_id}/jobs, query param q)
-- Spec: Structure decision 2026-10-14 (user): title-only search, trigram similarity plus substring match, date order kept, no caching.
-- Non-destructive. Adds the pg_trgm extension and one GIN index; no columns or rows are changed.
-- word_similarity (<%) and ILIKE can both use this index.
BEGIN;

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_jobs_title_trgm ON jobs USING gin (title gin_trgm_ops);

COMMIT;
