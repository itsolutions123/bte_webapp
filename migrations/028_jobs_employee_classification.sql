-- 028: HR-only Employee Classification on jobs (contract: "Employee Classification").
-- Nullable String, no index, no CHECK: validated by the API against a fixed list
-- (Rank and File, Supervisory, Managerial), same pattern as jobs.job_type.
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS employee_classification VARCHAR;
