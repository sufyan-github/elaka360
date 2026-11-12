-- 0003 — PostGIS geometry and search keys (findings C5, C9, P6).
-- Requires the postgis and pg_trgm extensions (the postgis/postgis image ships both).

BEGIN;

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Twin of packages/shared/src/search.ts latinKey(): "Rajshahi", "rajsahi", "Raj-shahi" → "rajsahi".
CREATE FUNCTION elaka_latin_key(t text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
  SELECT regexp_replace(
    replace(replace(replace(replace(replace(replace(replace(
      regexp_replace(lower(coalesce(t, '')), '[^a-z0-9]+', '', 'g'),
      'sh', 's'), 'oo', 'u'), 'ou', 'u'), 'ee', 'i'), 'ii', 'i'), 'aa', 'a'), 'w', 'o'),
    '([a-z])\1+', '\1', 'g')
$$;

-- Admin areas: boundary polygons, point, search key ---------------------------
ALTER TABLE admin_areas
  ADD COLUMN boundary geography(MultiPolygon, 4326),
  ADD COLUMN centroid geography(Point, 4326) GENERATED ALWAYS AS (
    CASE WHEN lat IS NOT NULL AND lon IS NOT NULL THEN ST_SetSRID(ST_MakePoint(lon::float8, lat::float8), 4326)::geography END) STORED,
  ADD COLUMN name_key text GENERATED ALWAYS AS (elaka_latin_key(name_en)) STORED;

CREATE INDEX admin_areas_boundary_gix ON admin_areas USING gist(boundary);
CREATE INDEX admin_areas_name_key_trgm ON admin_areas USING gin(name_key gin_trgm_ops);
CREATE INDEX admin_areas_name_bn_trgm ON admin_areas USING gin(name_bn gin_trgm_ops);
CREATE INDEX admin_areas_name_en_trgm ON admin_areas USING gin(lower(name_en) gin_trgm_ops);

-- Places: point geometry, search key -------------------------------------------
ALTER TABLE places
  ADD COLUMN geom geography(Point, 4326) GENERATED ALWAYS AS (
    CASE WHEN lat IS NOT NULL AND lon IS NOT NULL THEN ST_SetSRID(ST_MakePoint(lon::float8, lat::float8), 4326)::geography END) STORED,
  ADD COLUMN name_key text GENERATED ALWAYS AS (elaka_latin_key(coalesce(name_en, ''))) STORED;

CREATE INDEX places_geom_gix ON places USING gist(geom);
CREATE INDEX places_name_key_trgm ON places USING gin(name_key gin_trgm_ops);
CREATE INDEX places_name_bn_trgm ON places USING gin(name_bn gin_trgm_ops);

COMMIT;
