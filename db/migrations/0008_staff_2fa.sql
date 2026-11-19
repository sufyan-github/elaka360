-- 0008 — Two-factor authentication (TOTP, RFC 6238) for staff.
-- The secret is stored encrypted (AES-256-GCM, key from AUTH_TOTP_KEY or derived from AUTH_JWT_SECRET);
-- recovery codes are stored as SHA-256 hashes and consumed on use. A session records when it passed 2FA.
BEGIN;
ALTER TABLE users
  ADD COLUMN totp_secret_enc   text,
  ADD COLUMN totp_pending_enc  text,
  ADD COLUMN totp_enabled_at   timestamptz,
  ADD COLUMN totp_last_step    bigint,                       -- last accepted time step (no code reuse)
  ADD COLUMN recovery_hashes   text[] NOT NULL DEFAULT '{}';
ALTER TABLE sessions
  ADD COLUMN mfa_at       timestamptz,
  ADD COLUMN mfa_failures smallint NOT NULL DEFAULT 0;
COMMIT;
