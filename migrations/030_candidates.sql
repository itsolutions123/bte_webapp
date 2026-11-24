-- 030: candidates (applicants moved into the hiring pipeline from /admin/applicants).
-- One row per application (UNIQUE). Stage is limited by a CHECK. Additive only, no existing table changes.
CREATE TABLE IF NOT EXISTS candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id UUID NOT NULL UNIQUE REFERENCES applications(id) ON DELETE CASCADE,
    stage VARCHAR NOT NULL DEFAULT 'initial_interview',
    assigned_to_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    moved_by_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    moved_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    stage_changed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_candidates_stage CHECK (stage IN ('initial_interview','qualifiers_exam','final_interview','requirements','background_check','onboarding','onboarded'))
);
CREATE INDEX IF NOT EXISTS idx_candidates_stage ON candidates (stage);
CREATE INDEX IF NOT EXISTS idx_candidates_assigned_to_id ON candidates (assigned_to_id);
CREATE INDEX IF NOT EXISTS idx_candidates_moved_at ON candidates (moved_at);
