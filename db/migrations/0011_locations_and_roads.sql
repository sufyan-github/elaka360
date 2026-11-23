-- 0011 — Where a location or a Bangla name came from when it is not the area's own source, and named roads per area.
-- Census villages and mouzas (BBS 2022) have names and populations but no coordinates: a point can come from
-- OpenStreetMap ('osm:node/123') or from a contributor's pin approved by a moderator ('contribution:45'). The area's
-- evidence level stays its census evidence; these columns say the point / Bangla name are community data.
BEGIN;
ALTER TABLE admin_areas ADD COLUMN location_source text;
ALTER TABLE admin_areas ADD COLUMN name_bn_source text;

-- Named roads per union / pourashava / city ward, from OpenStreetMap (community data, unverified)
CREATE TABLE area_roads (
  area_id        bigint NOT NULL REFERENCES admin_areas(id) ON DELETE CASCADE,
  name           text,
  name_bn        text,
  highway        text NOT NULL,
  ref            text,
  length_m       integer NOT NULL,
  osm_ids        bigint[] NOT NULL,
  data_source_id int REFERENCES data_sources(id)
);
CREATE INDEX area_roads_area_idx ON area_roads(area_id);

-- views built with SELECT * freeze their column list (0005): add the new columns
CREATE OR REPLACE VIEW public_admin_areas AS
  SELECT * FROM admin_areas
  WHERE status = 'active' AND (production_eligible OR elaka_include_unverified());
COMMIT;
