-- 016: users.full_name for the admin profile card (GET /api/v1/admin/me).
-- Nullable on purpose: existing rows stay NULL until filled by a confirmed UPDATE.
-- No index: never used in WHERE, JOIN or ORDER BY (Rule 18.1 does not apply).
ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name VARCHAR(100);
