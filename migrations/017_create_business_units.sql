-- 017: Business Units (parent of brands). Option B, chosen by the user 2026-11-04.
-- Spec: docs/SCHEMA.md (business_units, brands.business_unit_id) and docs/API_CONTRACT.md (POST /business-units), both PROPOSED.
-- Non-destructive and idempotent: existing brands keep business_unit_id NULL (not assigned yet), jobs are untouched.
-- id has no DB default, same as brands: the app generates the UUID.
-- slug is generated server-side from name (lowercase), so a unique index on slug also blocks case-only duplicates.
BEGIN;

CREATE TABLE IF NOT EXISTS business_units (
    id UUID PRIMARY KEY,
    slug VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    archived_at TIMESTAMPTZ NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_business_units_slug ON business_units (slug);
CREATE INDEX IF NOT EXISTS idx_business_units_archived_at ON business_units (archived_at);

ALTER TABLE brands
    ADD COLUMN IF NOT EXISTS business_unit_id UUID NULL REFERENCES business_units (id);

CREATE INDEX IF NOT EXISTS idx_brands_business_unit_id ON brands (business_unit_id);

COMMIT;
