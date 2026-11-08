-- Elaka360 — core database schema (PostgreSQL 14+)
-- Plain lat/lon columns so it runs without extensions. If PostGIS is available,
-- run the optional block at the bottom to add geography columns + spatial indexes.

BEGIN;

CREATE TYPE admin_level AS ENUM ('country','division','district','upazila','city_corporation','pourashava','union','ward','mouza','village','thana');
CREATE TYPE verification_status AS ENUM ('unverified','pending','verified','disputed');
CREATE TYPE record_status AS ENUM ('draft','active','inactive','closed','archived');
CREATE TYPE user_role AS ENUM ('user','contributor','moderator','data_admin','national_admin','super_admin');
CREATE TYPE contribution_type AS ENUM ('new_place','new_business','new_tourist_spot','area_info','photo','correction','report');
CREATE TYPE contribution_status AS ENUM ('new','in_review','needs_changes','approved','rejected');
CREATE TYPE duplicate_status AS ENUM ('open','merged','kept_separate','needs_more_review','not_duplicate');

-- Where every fact comes from ---------------------------------------------
CREATE TABLE data_sources (
  id            serial PRIMARY KEY,
  key           text UNIQUE NOT NULL,           -- e.g. NUHIL, BBS_2022, LGD, OSM
  name          text NOT NULL,
  url           text,
  license       text,
  trust_level   smallint NOT NULL DEFAULT 2 CHECK (trust_level BETWEEN 1 AND 5),  -- 5 = official gazette
  notes         text
);

-- Administrative hierarchy (one table, self-referencing) -------------------
-- division → district → upazila / city_corporation → union / pourashava → ward → mouza/village
CREATE TABLE admin_areas (
  id                  bigint PRIMARY KEY,
  level               admin_level NOT NULL,
  parent_id           bigint REFERENCES admin_areas(id),
  name_bn             text NOT NULL,
  name_en             text NOT NULL,
  slug                text NOT NULL,
  path                text NOT NULL UNIQUE,        -- url path, e.g. rajshahi/rajshahi/paba/harian
  bbs_code            text,                         -- BBS geocode
  source_ref          text,                         -- id in the upstream dataset
  website             text,
  lat                 numeric(9,6),
  lon                 numeric(9,6),
  area_km2            numeric(10,2),
  area_basis          text,                         -- official | computed_from_polygon
  population_2022     integer,
  population_basis    text,                         -- enumerated | adjusted
  population_source_id int REFERENCES data_sources(id),
  wards_count         integer,
  established         text,
  status              record_status NOT NULL DEFAULT 'active',
  verified            boolean NOT NULL DEFAULT false,
  production_eligible boolean NOT NULL DEFAULT true,
  data_source_id      int REFERENCES data_sources(id),
  notes               text,
  last_verified_at    date,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX admin_areas_parent_idx ON admin_areas(parent_id);
CREATE INDEX admin_areas_level_idx  ON admin_areas(level);

-- Category taxonomy (2 levels) ----------------------------------------------
CREATE TABLE categories (
  id         serial PRIMARY KEY,
  key        text UNIQUE NOT NULL,
  parent_id  int REFERENCES categories(id),
  name_bn    text NOT NULL,
  name_en    text NOT NULL,
  icon       text,
  color      text,
  sort_order int NOT NULL DEFAULT 0
);

-- Users, levels, badges -------------------------------------------------------
CREATE TABLE users (
  id            bigserial PRIMARY KEY,
  name          text NOT NULL,
  email         text UNIQUE,
  phone         text UNIQUE,
  role          user_role NOT NULL DEFAULT 'user',
  avatar_url    text,
  home_area_id  bigint REFERENCES admin_areas(id),
  points        integer NOT NULL DEFAULT 0,
  level         smallint NOT NULL DEFAULT 1,
  profile_public boolean NOT NULL DEFAULT true,
  created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE levels (
  level      smallint PRIMARY KEY,
  name_bn    text NOT NULL,
  name_en    text NOT NULL,
  min_points integer NOT NULL
);
CREATE TABLE badges (
  id        serial PRIMARY KEY,
  key       text UNIQUE NOT NULL,
  name_bn   text NOT NULL,
  name_en   text NOT NULL,
  rule      jsonb NOT NULL DEFAULT '{}'::jsonb,   -- e.g. {"type":"approved_contributions","gte":10}
  icon      text
);
CREATE TABLE user_badges (
  user_id   bigint REFERENCES users(id) ON DELETE CASCADE,
  badge_id  int REFERENCES badges(id),
  earned_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, badge_id)
);

-- Places: institutions, businesses, tourist spots, emergency services ---------
CREATE TABLE places (
  id                  bigserial PRIMARY KEY,
  public_id           text UNIQUE NOT NULL,        -- INST-00018427 / BIZ-… / TOUR-…
  slug                text UNIQUE NOT NULL,
  name_bn             text NOT NULL,
  name_en             text,
  short_name          text,
  category_id         int NOT NULL REFERENCES categories(id),
  subcategory_id      int REFERENCES categories(id),
  ownership           text CHECK (ownership IN ('public','private','ngo','trust','autonomous')),
  division_id         bigint REFERENCES admin_areas(id),
  district_id         bigint REFERENCES admin_areas(id),
  upazila_id          bigint REFERENCES admin_areas(id),
  union_id            bigint REFERENCES admin_areas(id),
  city_corporation_id bigint REFERENCES admin_areas(id),
  address_bn          text,
  address_en          text,
  postcode            text,
  lat                 numeric(9,6),
  lon                 numeric(9,6),
  phones              text[] NOT NULL DEFAULT '{}',
  email               text,
  website             text,
  established         text,
  opening_hours       jsonb,                       -- {"mon":"09:00-17:00", "is_24_7":true}
  attributes          jsonb NOT NULL DEFAULT '{}'::jsonb,   -- beds, departments, price_range, seats…
  description_bn      text,
  description_en      text,
  status              record_status NOT NULL DEFAULT 'active',
  verification_status verification_status NOT NULL DEFAULT 'unverified',
  rating_avg          numeric(2,1),
  rating_count        integer NOT NULL DEFAULT 0,
  data_source_id      int REFERENCES data_sources(id),
  source_notes        text,
  last_verified_at    date,
  verified_by         bigint REFERENCES users(id),
  created_by          bigint REFERENCES users(id),
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX places_category_idx ON places(category_id, subcategory_id);
CREATE INDEX places_district_idx ON places(district_id);
CREATE INDEX places_upazila_idx  ON places(upazila_id);
CREATE INDEX places_latlon_idx   ON places(lat, lon);

CREATE TABLE place_media (
  id          bigserial PRIMARY KEY,
  place_id    bigint NOT NULL REFERENCES places(id) ON DELETE CASCADE,
  url         text NOT NULL,
  kind        text NOT NULL DEFAULT 'photo',
  caption     text,
  credit      text,
  license     text,
  is_cover    boolean NOT NULL DEFAULT false,
  status      contribution_status NOT NULL DEFAULT 'new',
  uploaded_by bigint REFERENCES users(id),
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE reviews (
  id         bigserial PRIMARY KEY,
  place_id   bigint NOT NULL REFERENCES places(id) ON DELETE CASCADE,
  user_id    bigint NOT NULL REFERENCES users(id),
  rating     smallint NOT NULL CHECK (rating BETWEEN 1 AND 5),
  body       text,
  status     record_status NOT NULL DEFAULT 'active',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (place_id, user_id)
);

-- Saved items & collections (offline-capable) --------------------------------
CREATE TABLE collections (
  id          bigserial PRIMARY KEY,
  user_id     bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name        text NOT NULL,
  description text,
  offline     boolean NOT NULL DEFAULT false,
  created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE saved_items (
  id            bigserial PRIMARY KEY,
  user_id       bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  collection_id bigint REFERENCES collections(id) ON DELETE SET NULL,
  place_id      bigint REFERENCES places(id) ON DELETE CASCADE,
  admin_area_id bigint REFERENCES admin_areas(id) ON DELETE CASCADE,
  created_at    timestamptz NOT NULL DEFAULT now(),
  CHECK (num_nonnulls(place_id, admin_area_id) = 1)
);

-- Community contributions & moderation ---------------------------------------
CREATE TABLE contributions (
  id                     bigserial PRIMARY KEY,
  user_id                bigint NOT NULL REFERENCES users(id),
  type                   contribution_type NOT NULL,
  target_place_id        bigint REFERENCES places(id),
  target_area_id         bigint REFERENCES admin_areas(id),
  payload                jsonb NOT NULL,          -- the submitted fields as entered
  lat                    numeric(9,6),
  lon                    numeric(9,6),
  confirmed_accurate     boolean NOT NULL DEFAULT false,  -- "I confirm this is correct" checkbox
  status                 contribution_status NOT NULL DEFAULT 'new',
  priority               text NOT NULL DEFAULT 'normal' CHECK (priority IN ('low','normal','high','urgent')),
  reviewer_id            bigint REFERENCES users(id),
  reviewer_note          text,
  points_awarded         integer NOT NULL DEFAULT 0,
  created_at             timestamptz NOT NULL DEFAULT now(),
  reviewed_at            timestamptz
);
CREATE INDEX contributions_status_idx ON contributions(status, created_at DESC);

CREATE TABLE duplicate_candidates (
  id          bigserial PRIMARY KEY,
  place_a_id  bigint NOT NULL REFERENCES places(id),
  place_b_id  bigint REFERENCES places(id),
  contribution_id bigint REFERENCES contributions(id),
  match_score numeric(5,2) NOT NULL,              -- 0–100
  match_detail jsonb,                             -- per-field similarity
  status      duplicate_status NOT NULL DEFAULT 'open',
  resolved_by bigint REFERENCES users(id),
  resolved_at timestamptz
);

CREATE TABLE data_quality_issues (
  id          bigserial PRIMARY KEY,
  place_id    bigint REFERENCES places(id) ON DELETE CASCADE,
  admin_area_id bigint REFERENCES admin_areas(id),
  issue_type  text NOT NULL CHECK (issue_type IN ('missing_gps','missing_photo','missing_required','broken_link','geo_mismatch','stale','invalid_value','possible_duplicate')),
  severity    smallint NOT NULL DEFAULT 2,
  status      text NOT NULL DEFAULT 'open',
  detected_at timestamptz NOT NULL DEFAULT now(),
  resolved_at timestamptz
);

-- Import / export pipeline & releases ----------------------------------------
CREATE TABLE import_jobs (
  id             bigserial PRIMARY KEY,
  data_source_id int REFERENCES data_sources(id),
  dataset_type   text NOT NULL,                  -- geo_union, institutions, businesses…
  filename       text,
  mode           text NOT NULL CHECK (mode IN ('simulation','live')),
  field_mapping  jsonb,
  total_records  integer, valid_records integer, warnings integer, errors integer, duplicates integer,
  status         text NOT NULL DEFAULT 'queued',
  created_by     bigint REFERENCES users(id),
  created_at     timestamptz NOT NULL DEFAULT now(),
  finished_at    timestamptz
);
CREATE TABLE releases (
  id                  serial PRIMARY KEY,
  version             text UNIQUE NOT NULL,       -- v2.8
  title               text NOT NULL,              -- "Rajshahi District"
  scope_area_id       bigint REFERENCES admin_areas(id),
  status              text NOT NULL DEFAULT 'planned',  -- planned | building | released
  file_size_bytes     bigint,
  file_count          integer,
  integrity_check     text,
  production_eligible boolean NOT NULL DEFAULT false,
  notes               text,
  released_at         timestamptz
);

-- Reference / content --------------------------------------------------------
CREATE TABLE emergency_numbers (
  number     text PRIMARY KEY,
  name_bn    text NOT NULL,
  name_en    text NOT NULL,
  category   text NOT NULL,
  verified   boolean NOT NULL DEFAULT false,
  data_source_id int REFERENCES data_sources(id),
  notes      text,
  sort_order int NOT NULL DEFAULT 0
);
CREATE TABLE content_pages (
  key        text PRIMARY KEY,                   -- about, privacy, terms, data_policy, open_data, community_guidelines
  title_bn   text NOT NULL,
  title_en   text,
  body_bn    text,
  body_en    text,
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE faqs (
  id serial PRIMARY KEY, question_bn text NOT NULL, answer_bn text, question_en text, answer_en text, sort_order int DEFAULT 0
);
CREATE TABLE contact_messages (
  id bigserial PRIMARY KEY, user_id bigint REFERENCES users(id), email text, subject text NOT NULL,
  message text NOT NULL CHECK (char_length(message) <= 1000), status text NOT NULL DEFAULT 'open',
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE local_updates (                         -- "সাম্প্রতিক সংযোজন" news-style updates
  id bigserial PRIMARY KEY, title_bn text NOT NULL, body_bn text, category_id int REFERENCES categories(id),
  admin_area_id bigint REFERENCES admin_areas(id), published_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE notifications (
  id bigserial PRIMARY KEY, user_id bigint NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  kind text NOT NULL, title text NOT NULL, body text, read_at timestamptz, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE audit_log (
  id bigserial PRIMARY KEY, actor_id bigint REFERENCES users(id), action text NOT NULL,
  entity text NOT NULL, entity_id text NOT NULL, diff jsonb, at timestamptz NOT NULL DEFAULT now()
);

COMMIT;

-- Optional: PostGIS ----------------------------------------------------------
-- CREATE EXTENSION IF NOT EXISTS postgis;
-- ALTER TABLE admin_areas ADD COLUMN boundary geography(MultiPolygon, 4326);
-- ALTER TABLE places ADD COLUMN geom geography(Point, 4326)
--   GENERATED ALWAYS AS (CASE WHEN lat IS NOT NULL THEN ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography END) STORED;
-- CREATE INDEX places_geom_gix ON places USING gist(geom);
-- Nearby query ("আশেপাশের সেবা"):
--   SELECT * FROM places WHERE ST_DWithin(geom, ST_MakePoint(:lon,:lat)::geography, 2000) ORDER BY geom <-> ST_MakePoint(:lon,:lat)::geography;
