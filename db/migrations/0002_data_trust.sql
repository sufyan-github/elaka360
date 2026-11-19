-- 0002 — Data trust model (audit findings D1, D2, C10).
-- Additive. On a database that already holds the v0.1 seed, every record loses its publication
-- status until it is re-seeded or reviewed: nothing stays public on community evidence alone.

BEGIN;

CREATE TYPE evidence_level AS ENUM ('official', 'secondary', 'community', 'unverified');

-- Source registry metadata --------------------------------------------------
ALTER TABLE data_sources
  ADD COLUMN source_type        text NOT NULL DEFAULT 'unknown',   -- government_portal | census_aggregator | encyclopedia | news | community_dataset …
  ADD COLUMN organization       text,
  ADD COLUMN access_date        date,
  ADD COLUMN publication_date   date,
  ADD COLUMN applicable_area_id bigint REFERENCES admin_areas(id),
  ADD COLUMN evidence_notes     text,
  ADD COLUMN active             boolean NOT NULL DEFAULT true,
  ADD COLUMN updated_at         timestamptz NOT NULL DEFAULT now(),
  ADD CONSTRAINT data_sources_url_chk CHECK (url IS NULL OR url = '' OR url ~ '^https?://');

-- Admin areas ----------------------------------------------------------------
ALTER TABLE admin_areas
  ALTER COLUMN production_eligible SET DEFAULT false,
  ADD COLUMN evidence_level     evidence_level NOT NULL DEFAULT 'unverified',
  ADD COLUMN evidence_source_id int REFERENCES data_sources(id),
  ADD COLUMN verification_notes text,
  ADD COLUMN verified_by        bigint REFERENCES users(id),
  ADD COLUMN last_reviewed_at   timestamptz;

UPDATE admin_areas SET production_eligible = false, verified = false;   -- re-earned via seed or review

ALTER TABLE admin_areas
  ADD CONSTRAINT admin_areas_eligible_chk CHECK (
    NOT production_eligible OR (evidence_level IN ('official', 'secondary') AND evidence_source_id IS NOT NULL)),
  ADD CONSTRAINT admin_areas_verified_chk CHECK (NOT verified OR evidence_level = 'official'),
  ADD CONSTRAINT admin_areas_latlon_chk CHECK (
    (lat IS NULL AND lon IS NULL) OR (lat BETWEEN 20.3 AND 26.8 AND lon BETWEEN 88.0 AND 92.8));

CREATE INDEX admin_areas_public_idx ON admin_areas(level, parent_id) WHERE production_eligible;

-- Places -----------------------------------------------------------------------
ALTER TABLE places
  ADD COLUMN production_eligible boolean NOT NULL DEFAULT false,
  ADD COLUMN evidence_level      evidence_level NOT NULL DEFAULT 'unverified',
  ADD COLUMN evidence_source_id  int REFERENCES data_sources(id),
  ADD COLUMN verification_notes  text,
  ADD COLUMN last_reviewed_at    timestamptz,
  ADD CONSTRAINT places_eligible_chk CHECK (
    NOT production_eligible OR (evidence_level IN ('official', 'secondary') AND evidence_source_id IS NOT NULL)),
  ADD CONSTRAINT places_latlon_chk CHECK (
    (lat IS NULL AND lon IS NULL) OR (lat BETWEEN 20.3 AND 26.8 AND lon BETWEEN 88.0 AND 92.8));

-- Area filters OR the five FK columns; three were unindexed (finding C8).
CREATE INDEX places_division_idx ON places(division_id);
CREATE INDEX places_union_idx    ON places(union_id);
CREATE INDEX places_cc_idx       ON places(city_corporation_id);
CREATE INDEX places_public_idx   ON places(category_id) WHERE production_eligible AND status = 'active';

-- Emergency numbers --------------------------------------------------------------
ALTER TABLE emergency_numbers ADD COLUMN evidence_level evidence_level NOT NULL DEFAULT 'unverified';

COMMIT;
