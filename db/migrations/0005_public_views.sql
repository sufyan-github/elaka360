-- 0005 — Public read views. Every public API query reads these, never the base tables, so
-- production eligibility is enforced in one place (finding D2).
--
-- Setting `elaka360.include_unverified = on` for a connection (API env PUBLIC_INCLUDE_UNVERIFIED=true)
-- also returns records that are not production-eligible; the API then labels them by evidence level.
-- Admin queries use the base tables.
--
-- NOTE: views built with SELECT * freeze their column list. A migration that adds columns to these
-- tables must CREATE OR REPLACE the matching view afterwards.

BEGIN;

CREATE FUNCTION elaka_include_unverified() RETURNS boolean
LANGUAGE sql STABLE AS $$ SELECT coalesce(current_setting('elaka360.include_unverified', true), 'off') = 'on' $$;

CREATE VIEW public_admin_areas AS
  SELECT * FROM admin_areas
  WHERE status = 'active' AND (production_eligible OR elaka_include_unverified());

CREATE VIEW public_places AS
  SELECT * FROM places
  WHERE status = 'active' AND (production_eligible OR elaka_include_unverified());

CREATE VIEW public_emergency_numbers AS
  SELECT * FROM emergency_numbers
  WHERE evidence_level IN ('official', 'secondary') OR elaka_include_unverified();

CREATE VIEW public_reviews AS
  SELECT r.* FROM reviews r JOIN public_places p ON p.id = r.place_id
  WHERE r.status = 'active';

COMMIT;
