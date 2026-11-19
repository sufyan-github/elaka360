-- 0010 — Relations between areas that are not parent and child. First use: the metropolitan police thana(s) a city
-- ward lies in (BBS Census 2022 counts city wards inside thanas; one ward can be split across two thanas), so the
-- administrative tree (city corporation → ward) stays as it is and the police jurisdiction sits beside it.
BEGIN;
CREATE TABLE admin_area_links (
  area_id        bigint NOT NULL REFERENCES admin_areas(id) ON DELETE CASCADE,
  linked_area_id bigint NOT NULL REFERENCES admin_areas(id) ON DELETE CASCADE,
  relation       text NOT NULL CHECK (relation IN ('thana')),
  data_source_id int REFERENCES data_sources(id),
  PRIMARY KEY (area_id, linked_area_id, relation)
);
CREATE INDEX admin_area_links_linked_idx ON admin_area_links(linked_area_id);
-- subtree lookups by path prefix (path LIKE 'rajshahi/rajshahi/%'): 175k areas once mouzas and villages are loaded
CREATE INDEX admin_areas_path_prefix_idx ON admin_areas(path text_pattern_ops);
COMMIT;
