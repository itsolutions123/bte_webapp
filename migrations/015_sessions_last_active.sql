-- Migration 015: idle-timeout support for admin sessions
-- last_active_at tracks the idle window (10 min, enforced in app code);
-- expires_at (migration 014) stays the fixed 8h hard cap, unchanged by activity.

ALTER TABLE sessions ADD COLUMN last_active_at TIMESTAMPTZ NOT NULL DEFAULT now();
