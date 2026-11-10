-- 0007 — Hotlines are never shown without a source, whatever the public visibility setting.
-- An unverified phone number must not become a tap-to-call link (data trust policy), so this view no
-- longer honours elaka360.include_unverified.
BEGIN;
CREATE OR REPLACE VIEW public_emergency_numbers AS
  SELECT * FROM emergency_numbers WHERE evidence_level IN ('official', 'secondary');
COMMIT;
