-- 011: job posting details (location, pay information, type of job)
-- Decision (user, 2026-10-16): jobs get three display fields shown on the website job list and job detail
--   ("Job details" block) and entered in the Create job / Edit job modals.
--   location and pay_information are free text; job_type is a fixed list validated server-side
--   (Full-time, Part-time, Onsite; see docs/API_CONTRACT.md). No CHECK constraint on purpose:
--   the allowed list lives in one place (the contract and the server), so a new value is not a migration.
-- Non-destructive. Existing jobs stay NULL on all three columns (no backfill).
-- No indexes: none of these columns is used in a WHERE, JOIN or ORDER BY (rule 18.1).
BEGIN;

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS location VARCHAR NULL;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS pay_information VARCHAR NULL;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS job_type VARCHAR NULL;

COMMIT;
