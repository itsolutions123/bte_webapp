-- 005: jobs gets the public-posting field and stops blocking inserts (Create Job modal)
-- Spec: docs/SCHEMA.md jobs; PROJECT_STATE.md OPEN Decisions 2026-10-14 (user: jobs are identified by id only, thresholds move to the form later).
-- Non-destructive. jobs had 0 rows on 2026-10-14, so no backfill is needed. No columns are dropped.
-- requirements: nullable Text, the Requirements part of the public job posting.
-- pass_threshold and pooling_threshold: relaxed to NULLABLE. NOTE: app/routers/public.py:201-203 compares against them, so scoring must handle NULL before any job without thresholds can receive applications (open with Structure).
-- slug: the unique index ix_jobs_slug is replaced by a plain index of the same name, so several jobs can share a title. The id is the only job identifier.
BEGIN;

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS requirements TEXT NULL;

ALTER TABLE jobs ALTER COLUMN pass_threshold DROP NOT NULL;
ALTER TABLE jobs ALTER COLUMN pooling_threshold DROP NOT NULL;

DROP INDEX IF EXISTS ix_jobs_slug;
CREATE INDEX ix_jobs_slug ON jobs (slug);

COMMIT;
