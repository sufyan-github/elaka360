"""Data trust policy for the Elaka360 seed (see docs/data/DATA_TRUST_POLICY.md).

Evidence levels
  official    Tier 1: government gazette / LGD / BBS primary publication, with an official identifier where one exists.
  secondary   Tier 2: reliable secondary source (Wikipedia, census aggregators, newspapers) with attribution.
  community   Tier 3: community-maintained dataset or user submission (e.g. nuhil/bangladesh-geocode).
  unverified  No usable source yet (general knowledge, mockups).

Production eligibility (shown on public surfaces, exported in open data) is allowed only for
official or secondary evidence that names a source. It is never inherited from a parent or child.
"""
import unicodedata

EVIDENCE_LEVELS = ("official", "secondary", "community", "unverified")
PUBLISHABLE = {"official", "secondary"}


def nfc(value):
    """Unicode NFC for every text value, so precomposed and decomposed Bangla compare equal."""
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    return value


def eligible(evidence_level, source_key, requested=True):
    """Production eligibility under the policy. `requested=False` keeps a publishable record back."""
    return bool(requested and evidence_level in PUBLISHABLE and source_key)


def check_row(row):
    """Return a list of policy violations for one seed row (admin area or place)."""
    errs = []
    lvl = row.get("evidence_level")
    if lvl not in EVIDENCE_LEVELS:
        errs.append(f"unknown evidence_level {lvl!r}")
    if row.get("production_eligible") and lvl not in PUBLISHABLE:
        errs.append(f"production_eligible with evidence_level={lvl}")
    if row.get("production_eligible") and not row.get("evidence_source"):
        errs.append("production_eligible without an evidence source")
    if row.get("verified") and lvl != "official":
        errs.append("verified=true requires official evidence")
    return errs
