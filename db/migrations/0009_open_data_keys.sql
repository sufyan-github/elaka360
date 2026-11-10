-- 0009 — Open Data API keys. Keys are stored as SHA-256 hashes; usage is counted per key per minute
-- in the database so the rate limit holds across API replicas.
BEGIN;
CREATE TABLE api_keys (
  id           serial PRIMARY KEY,
  name         text NOT NULL CHECK (char_length(name) BETWEEN 3 AND 80),
  key_prefix   text NOT NULL,                 -- first characters, shown in the admin list
  key_hash     text NOT NULL UNIQUE,
  rate_per_min integer NOT NULL DEFAULT 60 CHECK (rate_per_min BETWEEN 1 AND 6000),
  created_by   bigint REFERENCES users(id),
  created_at   timestamptz NOT NULL DEFAULT now(),
  last_used_at timestamptz,
  revoked_at   timestamptz
);
CREATE TABLE api_key_usage (
  key_id  integer NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
  minute  timestamptz NOT NULL,
  count   integer NOT NULL DEFAULT 0,
  PRIMARY KEY (key_id, minute)
);
COMMIT;
