-- Two-step apply flow: fixed personal fields on applicants (docs/API_CONTRACT.md).
-- Additive and nullable, so no backfill is needed. Rollback: DROP COLUMN x3.
ALTER TABLE applicants
    ADD COLUMN IF NOT EXISTS address VARCHAR,
    ADD COLUMN IF NOT EXISTS gender VARCHAR,
    ADD COLUMN IF NOT EXISTS date_of_birth DATE;
