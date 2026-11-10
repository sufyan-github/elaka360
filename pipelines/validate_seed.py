"""Validate the generated seed (data/seed) against the data trust policy and the master dataset.

Usage: python3 pipelines/validate_seed.py        exit 1 on any failure
Checks: Unicode NFC, duplicates, parent/level consistency, junk names, stable id ranges, coordinates,
production-eligibility policy, source completeness, and seed-vs-master differences (every difference
must be a tracked conflict in refdata.KNOWN_MASTER_DIFFS, and every tracked conflict must still differ).
"""
import csv, json, os, re, sys, unicodedata
sys.path.insert(0, os.path.dirname(__file__))
from trust import check_row, EVIDENCE_LEVELS
from refdata import KNOWN_MASTER_DIFFS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = os.path.join(ROOT, "data", "seed")
failures, warnings = [], []


def fail(msg):
    failures.append(msg)


def read(rel):
    with open(os.path.join(SEED, rel), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def boolean(v):
    return str(v).strip().lower() == "true"


areas = read("geo/admin_areas.csv")
places = read("pilot_rajshahi/places.csv")
sources = {r["key"]: r for r in read("reference/data_sources.csv")}
by_id = {r["id"]: r for r in areas}

# 1. Unicode NFC everywhere
for r in areas + places:
    for k, v in r.items():
        if isinstance(v, str) and v != unicodedata.normalize("NFC", v):
            fail(f"not NFC: {r.get('id') or r.get('slug')} {k}={v!r}")

# 2. stable id ranges and parents
RANGES = {"division": (10001, 10008), "district": (20001, 20064), "upazila": (30001, 30495), "union": (40001, 44541),
          "city_corporation": (50001, 50013), "pourashava": (60001, 60999)}
PARENT_LEVEL = {"division": {"country"}, "district": {"division"}, "upazila": {"district"}, "union": {"upazila"},
                "city_corporation": {"district"}, "pourashava": {"upazila"}}
for r in areas:
    lvl = r["level"]
    if lvl in RANGES:
        lo, hi = RANGES[lvl]
        if not lo <= int(r["id"]) <= hi:
            fail(f"id {r['id']} outside {lvl} range {lo}-{hi}")
    if lvl != "country":
        p = by_id.get(r["parent_id"])
        if not p:
            fail(f"{r['id']} {r['name_en']}: missing parent {r['parent_id']}")
        elif p["level"] not in PARENT_LEVEL.get(lvl, {p["level"]}):
            fail(f"{r['id']} {r['name_en']}: {lvl} under {p['level']}")

# 3. duplicates under the same parent
seen = {}
for r in areas:
    for key in ((r["parent_id"], r["level"], r["name_en"].strip().lower()), (r["parent_id"], r["level"], "bn:" + r["name_bn"].strip())):
        if key in seen and r["level"] in ("union", "upazila"):
            other = seen[key]
            # Natai (North/South) share an English name but differ in Bangla; only flag when both names collide
            if other["name_bn"] == r["name_bn"] and other["name_en"].lower() == r["name_en"].lower():
                fail(f"duplicate {r['level']}: {r['id']} and {other['id']} ({r['name_en']})")
        seen[key] = r
paths = [r["path"] for r in areas]
if len(paths) != len(set(paths)):
    fail("duplicate paths")

# 4. junk names (digits or union-parishad suffixes carried over from website slugs)
for r in areas:
    if r["level"] in ("union", "upazila"):
        if re.search(r"[0-9০-৯]", r["name_en"] + r["name_bn"]):
            fail(f"digit in name: {r['id']} {r['name_en']} / {r['name_bn']}")
        if re.search(r"up$", r["name_en"].lower()) and r["name_en"].lower() not in {"alampur", "rampur"}:
            warnings.append(f"name ends in 'up': {r['id']} {r['name_en']}")

# 5. policy + source completeness
for r in areas:
    row = dict(evidence_level=r["evidence_level"], production_eligible=boolean(r["production_eligible"]),
               evidence_source=r["evidence_source"], verified=boolean(r["verified"]))
    for e in check_row(row):
        fail(f"policy: area {r['id']} {r['name_en']}: {e}")
    if row["production_eligible"]:
        src = sources.get(r["evidence_source"])
        if not src or not src["url"]:
            fail(f"source: area {r['id']} eligible but evidence source {r['evidence_source']!r} has no URL")
for p in places:
    row = dict(evidence_level=p["evidence_level"], production_eligible=boolean(p["production_eligible"]),
               evidence_source=p["source"] if p["evidence_level"] in ("official", "secondary") else None, verified=False)
    for e in check_row(row):
        fail(f"policy: place {p['slug']}: {e}")
    if p["evidence_level"] not in EVIDENCE_LEVELS:
        fail(f"place {p['slug']}: bad evidence level")

# 6. coordinates inside Bangladesh's bounding box
for r in areas + places:
    if r.get("lat") and r.get("lon"):
        lat, lon = float(r["lat"]), float(r["lon"])
        if not (20.5 <= lat <= 26.7 and 88.0 <= lon <= 92.7):
            fail(f"coordinates outside Bangladesh: {r.get('id') or r.get('slug')} {lat},{lon}")

# 7. seed vs master: every difference tracked, every tracked difference still real
upz = read("qa/seed_vs_master_upazilas.csv")
names = read("qa/seed_vs_master_union_names.csv")
live = set()
for r in upz:
    if r["status"] == "UNTRACKED":
        fail(f"untracked seed/master count difference: {r['district']} / {r['upazila_seed'] or r['upazila_master']}")
    if r["status"] == "known":
        live.add(("count", r["district"], r["upazila_seed"] or r["upazila_master"]))
for r in names:
    if r["status"] == "UNTRACKED":
        fail(f"untracked seed/master name difference: {r['district']} / {r['upazila']} {r['side']} {r['union_en']}")
    if r["status"] == "known":
        live.add(("name", r["district"], r["upazila"], r["side"], r["union_en"]))
for key in KNOWN_MASTER_DIFFS:
    if key not in live:
        fail(f"stale KNOWN_MASTER_DIFFS entry (no longer differs): {key}")

# 8. population: district sums vs division totals (report only — source rounding)
pop = {}
for r in areas:
    if r["level"] == "district" and r["population_2022"]:
        pop[r["parent_id"]] = pop.get(r["parent_id"], 0) + int(r["population_2022"])
for r in areas:
    if r["level"] == "division" and r["population_2022"]:
        diff = pop.get(r["id"], 0) - int(r["population_2022"])
        if diff:
            warnings.append(f"population: {r['name_en']} districts sum to {diff:+d} vs division total (source rounding)")

summary = json.load(open(os.path.join(SEED, "qa", "counts_summary.json"), encoding="utf-8"))
print(json.dumps({"failures": len(failures), "warnings": len(warnings), "production_eligible_by_level": summary["production_eligible_by_level"]},
                 ensure_ascii=False))
for w in warnings:
    print("WARN", w)
for f in failures:
    print("FAIL", f)
sys.exit(1 if failures else 0)
