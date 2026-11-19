-- 0004 — Accounts, sessions, contribution workflow, review reports, tamper-proof audit log.

-- Enum additions cannot share a transaction with statements that use the new values.
ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'verifier';
ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'content_manager';
ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'analyst';
ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'readonly_staff';
ALTER TYPE contribution_status ADD VALUE IF NOT EXISTS 'draft' BEFORE 'new';

BEGIN;

-- Users -------------------------------------------------------------------------
ALTER TABLE users
  ADD COLUMN status                text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'suspended', 'deleted')),
  ADD COLUMN scope_area_id         bigint REFERENCES admin_areas(id),   -- staff: limits moderation/verification to this subtree
  ADD COLUMN last_login_at         timestamptz,
  ADD COLUMN deletion_requested_at timestamptz,
  ADD COLUMN updated_at            timestamptz NOT NULL DEFAULT now(),
  ADD CONSTRAINT users_phone_chk CHECK (phone IS NULL OR phone ~ '^\+8801[3-9][0-9]{8}$');

-- One-time passwords (stored hashed; never logged) ------------------------------------
CREATE TABLE otp_challenges (
  id          bigserial PRIMARY KEY,
  phone       text NOT NULL,
  code_hash   text NOT NULL,
  attempts    smallint NOT NULL DEFAULT 0,
  expires_at  timestamptz NOT NULL,
  consumed_at timestamptz,
  ip          inet,
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX otp_challenges_phone_idx ON otp_challenges(phone, created_at DESC);

-- Refresh-token sessions (token stored hashed; rotated on every refresh) ---------------
CREATE TABLE sessions (
  id           uuid PRIMARY KEY,
  user_id      bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  refresh_hash text NOT NULL,
  user_agent   text,
  created_at   timestamptz NOT NULL DEFAULT now(),
  last_used_at timestamptz NOT NULL DEFAULT now(),
  expires_at   timestamptz NOT NULL,
  revoked_at   timestamptz
);
CREATE INDEX sessions_user_idx ON sessions(user_id) WHERE revoked_at IS NULL;

-- Contributions: evidence + history ---------------------------------------------------
ALTER TABLE contributions
  ADD COLUMN evidence   jsonb NOT NULL DEFAULT '[]'::jsonb,   -- [{url, note}] supporting sources
  ADD COLUMN updated_at timestamptz NOT NULL DEFAULT now(),
  ADD COLUMN area_path  text;                                   -- denormalised for scoped moderation queues

CREATE TABLE contribution_events (
  id              bigserial PRIMARY KEY,
  contribution_id bigint NOT NULL REFERENCES contributions(id) ON DELETE CASCADE,
  actor_id        bigint REFERENCES users(id),
  from_status     contribution_status,
  to_status       contribution_status NOT NULL,
  note            text,
  at              timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX contribution_events_idx ON contribution_events(contribution_id, at);

-- Reviews: edits + reports ------------------------------------------------------------
ALTER TABLE reviews ADD COLUMN updated_at timestamptz NOT NULL DEFAULT now(),
                    ADD CONSTRAINT reviews_body_len_chk CHECK (body IS NULL OR char_length(body) <= 2000);
CREATE TABLE review_reports (
  id          bigserial PRIMARY KEY,
  review_id   bigint NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
  reporter_id bigint NOT NULL REFERENCES users(id),
  reason      text NOT NULL CHECK (char_length(reason) BETWEEN 3 AND 500),
  status      text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'upheld', 'dismissed')),
  created_at  timestamptz NOT NULL DEFAULT now(),
  UNIQUE (review_id, reporter_id)
);

-- Saved items: one save per user per target -----------------------------------------
CREATE UNIQUE INDEX saved_items_place_uniq ON saved_items(user_id, place_id) WHERE place_id IS NOT NULL;
CREATE UNIQUE INDEX saved_items_area_uniq  ON saved_items(user_id, admin_area_id) WHERE admin_area_id IS NOT NULL;

-- Audit log: richer records, append-only ---------------------------------------------
ALTER TABLE audit_log
  ADD COLUMN before     jsonb,
  ADD COLUMN after      jsonb,
  ADD COLUMN reason     text,
  ADD COLUMN request_id text,
  ADD COLUMN ip         inet;
CREATE INDEX audit_log_entity_idx ON audit_log(entity, entity_id, at DESC);
CREATE INDEX audit_log_actor_idx  ON audit_log(actor_id, at DESC);

CREATE FUNCTION audit_log_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'audit_log is append-only';
END $$;
CREATE TRIGGER audit_log_no_update BEFORE UPDATE OR DELETE ON audit_log
  FOR EACH ROW EXECUTE FUNCTION audit_log_append_only();

COMMIT;
