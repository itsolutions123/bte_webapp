-- 020: brand name and slug are unique per business unit, not globally. Decided by the user 2026-11-08 (option A).
-- Spec: docs/SCHEMA.md (brands) and docs/API_CONTRACT.md (POST and PATCH /brands, 409 rule), PROPOSED.
-- Drops the global unique index ix_brands_slug. Adds UNIQUE (business_unit_id, slug) and UNIQUE (business_unit_id, lower(name)).
-- Non-destructive to data: no rows change. The 8 live brands have no duplicates under the new rules (checked 2026-11-08, 0 rows).
-- Idempotent. idx_brands_business_unit_id is kept.
-- NULL business_unit_id never clashes in a unique index; every live brand has a unit and create_brand requires one.
BEGIN;

DROP INDEX IF EXISTS ix_brands_slug;

CREATE UNIQUE INDEX IF NOT EXISTS ux_brands_unit_slug ON brands (business_unit_id, slug);
CREATE UNIQUE INDEX IF NOT EXISTS ux_brands_unit_lower_name ON brands (business_unit_id, lower(name));

COMMIT;
