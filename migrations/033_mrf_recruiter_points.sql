-- 033: mrf_recruiter_points, the points a closed MRF earns per assignment and classification (Recruiters metrics, feature F2).
-- Contract: docs/API_CONTRACT.md, GET and PUT /api/v1/admin/metrics/recruiter-points (CONTRACTED 2026-11-27, commit d2f4346).
-- Additive: one new table and 12 seed rows, no existing table changes.
-- Seed values are the mockup's numbers and are NOT confirmed by the user; the PUT endpoint can change them without a migration.
-- No CHECK on the key columns: the code validates them against MRF_ASSIGNMENTS and MRF_CLASSIFICATION_OPTIONS (app/mrf_lists.py).
-- Keep the CHECK maximum (100) in step with MRF_RECRUITER_POINTS_MAX in app/routers/admin_metrics.py.
BEGIN;

CREATE TABLE IF NOT EXISTS mrf_recruiter_points (
    assignment VARCHAR NOT NULL,
    classification VARCHAR NOT NULL,
    points INTEGER NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by_user_id UUID NULL REFERENCES users (id) ON DELETE SET NULL,
    CONSTRAINT pk_mrf_recruiter_points PRIMARY KEY (assignment, classification),
    CONSTRAINT ck_mrf_recruiter_points_points CHECK (points >= 0 AND points <= 100)
);

INSERT INTO mrf_recruiter_points (assignment, classification, points) VALUES
    ('Head Office', 'Managerial', 5), ('Head Office', 'Supervisory', 3), ('Head Office', 'Rank and File', 2),
    ('Commissary', 'Managerial', 5), ('Commissary', 'Supervisory', 3), ('Commissary', 'Rank and File', 2),
    ('Cali Beach', 'Managerial', 5), ('Cali Beach', 'Supervisory', 3), ('Cali Beach', 'Rank and File', 2),
    ('Store Operations', 'Managerial', 3), ('Store Operations', 'Supervisory', 2), ('Store Operations', 'Rank and File', 1)
ON CONFLICT (assignment, classification) DO NOTHING;

COMMIT;
