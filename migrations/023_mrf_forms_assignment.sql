-- 023: MRF form Assignment (part 59). A form-level property on mrf_forms, not a question.
-- Nullable until set from the form header; the app requires it before a form can be ACTIVE.
-- The four values are a fixed MRF-only list (not business_units). Keep in step with
-- MRF_ASSIGNMENTS in app/mrf_lists.py. No index: the column is not filtered or sorted on.

BEGIN;

ALTER TABLE mrf_forms
    ADD COLUMN IF NOT EXISTS assignment VARCHAR NULL
    CONSTRAINT ck_mrf_forms_assignment
    CHECK (assignment IN ('Store Operations', 'Head Office', 'Commissary', 'Cali Beach'));

COMMIT;
