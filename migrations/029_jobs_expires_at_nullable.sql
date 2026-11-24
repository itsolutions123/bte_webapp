-- 029: job expiry disabled (contract: "Job expiry DISABLED").
-- jobs.expires_at is kept (old dates preserved, idx_jobs_expires_at stays) but becomes nullable;
-- new jobs get NULL. Dropping the column is a separate decision.
ALTER TABLE jobs ALTER COLUMN expires_at DROP NOT NULL;
