-- 013: archive support for brands (cascade: archiving a brand also archives its jobs)
-- Spec: docs/API_CONTRACT.md (POST /brands/{brand_id}/archive, new this session). docs/SCHEMA.md entry for brands.archived_at still to be added.
-- Non-destructive and idempotent: existing brands keep archived_at NULL (active).
BEGIN;

ALTER TABLE brands
    ADD COLUMN IF NOT EXISTS archived_at TIMESTAMPTZ NULL;

CREATE INDEX IF NOT EXISTS idx_brands_archived_at ON brands (archived_at);

COMMIT;
