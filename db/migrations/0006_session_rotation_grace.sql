-- 0006 — Refresh-token rotation grace window.
-- Browsers fire several requests at once when an access token expires (link prefetches); each may try to
-- refresh with the same token. The previous token is accepted for a short window after rotation so that
-- this benign race does not look like token theft. Older tokens still revoke the session.
BEGIN;
ALTER TABLE sessions
  ADD COLUMN prev_refresh_hash text,
  ADD COLUMN rotated_at timestamptz;
COMMIT;
