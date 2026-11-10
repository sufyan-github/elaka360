"""Build the Elaka360 seed dataset from vendored sources + curated reference data.

Usage: python3 pipelines/build_seed.py
Outputs: data/seed/** and db/seed/seed.sql
"""
import csv, json, math, os, re, shutil, sys
sys.path.insert(0, os.path.dirname(__file__))
from refdata import *
from trust import nfc, eligible, check_row
import reconcile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "data", "sources", "nuhil")
OUT = os.path.join(ROOT, "data", "seed")
SQL_OUT = os.path.join(ROOT, "db", "seed", "seed.sql")
shutil.rmtree(OUT, ignore_errors=True)
for d in ["geo", "taxonomy", "reference", "pilot_rajshahi", "qa"]:
    os.makedirs(f"{OUT}/{d}", exist_ok=True)

def rd(f):
    return [[nfc(c.strip()) for c in r] for r in csv.reader(open(f"{SRC_DIR}/{f}", encoding="utf-8"))]

def nfc_dict(d):
    return {k: nfc(v) for k, v in d.items()}

def clean(v):
    v = (v or "").strip()
    return None if v in ("", "null", "NULL") else v

def slugify(s):
    s = s.lower().replace("'", "").replace("&", "and")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")

def url(u):
    u = clean(u)
    if not u: return None
    return u if u.startswith("http") else "http://" + u

SRC_IDS = {k: i + 1 for i, k in enumerate(SRC)}

dv, ds, up, un = rd("divisions.csv"), rd("districts.csv"), rd("upazilas.csv"), rd("unions.csv")

# ---------- polygon areas (spherical approximation) ----------
R = 6371.0088
def ring_area(ring):
    a = 0.0
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        a += math.radians(x2 - x1) * (2 + math.sin(math.radians(y1)) + math.sin(math.radians(y2)))
    return abs(a * R * R / 2)
def geom_area(g):
    polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    return sum(ring_area(p[0]) - sum(ring_area(h) for h in p[1:]) for p in polys)

gj = json.load(open(f"{SRC_DIR}/districts.geojson"))
geo_by_name = {}
for f in gj["features"]:
    n = f["properties"]["ADM2_EN"]
    geo_by_name[GEOJSON_NAME_FIX.get(n, n)] = f

rows = []          # unified admin_areas
def add(**r):
    base = dict(id=None, level=None, parent_id=None, name_bn=None, name_en=None, slug=None, path=None, bbs_code=None,
                source_ref=None, website=None, lat=None, lon=None, area_km2=None, area_basis=None, population_2022=None,
                population_basis=None, population_source=None, wards_count=None, established=None, verified=False,
                production_eligible=True, data_source="NUHIL", notes=None, evidence_level="community", evidence_source=None)
    base.update(r)
    base["_before"] = (base["verified"], base["production_eligible"])   # flags as the v0.1 seed set them
    rows.append(base); return base

rows.append(dict(id=1, level="country", parent_id=None, name_bn="বাংলাদেশ", name_en="Bangladesh", slug="bangladesh", path="bangladesh",
                 bbs_code=None, source_ref=None, website=None, lat=None, lon=None, area_km2=None, area_basis=None,
                 population_2022=sum(DIVISION_POP.values()), population_basis="adjusted", population_source="CITYPOP_ADJ",
                 wards_count=None, established=None, verified=True, production_eligible=True, data_source="CITYPOP_ADJ", notes=None,
                 evidence_level="secondary", evidence_source="CITYPOP_ADJ", _before=(True, True)))

div_map, dis_map, upz_map = {}, {}, {}
for r in dv:
    i, en, bn, web = r
    fx = DIVISION_FIX[i]
    s = slugify(fx["name_en"])
    div_map[i] = add(id=10000 + int(i), level="division", parent_id=1, name_bn=bn, name_en=fx["name_en"], slug=s, path=s,
                     bbs_code=fx["bbs_code"], source_ref=f"nuhil:division:{i}", website=url(web),
                     population_2022=DIVISION_POP[fx["name_en"]], population_basis="adjusted", population_source="CITYPOP_ADJ",
                     verified=True, evidence_level="secondary", evidence_source="CITYPOP_ADJ")

for r in ds:
    i, did, en, bn, lat, lon, web = r
    name = DISTRICT_NAME_FIX.get(en, en)
    s = slugify(name)
    feat = geo_by_name.get(en)
    area = round(geom_area(feat["geometry"]), 1) if feat else None
    dis_map[i] = add(id=20000 + int(i), level="district", parent_id=div_map[did]["id"], name_bn=bn, name_en=name, slug=s,
                     path=f"{div_map[did]['slug']}/{s}", source_ref=f"nuhil:district:{i}", website=url(web),
                     lat=float(lat), lon=float(lon), area_km2=area, area_basis="computed_from_polygon" if area else None,
                     population_2022=DISTRICT_POP[en], population_basis="adjusted", population_source="CITYPOP_ADJ", verified=True,
                     evidence_level="secondary", evidence_source="CITYPOP_ADJ")
    dis_map[i]["_src_en"] = en
    if feat:
        feat["properties"].update(district_id=20000 + int(i), name_en=name, name_bn=bn, division_id=div_map[did]["id"],
                                  path=dis_map[i]["path"])

# Rajshahi district: prefer Wikipedia official area
raj = next(d for d in dis_map.values() if d["_src_en"] == "Rajshahi")
raj.update(area_km2=2425.37, area_basis="official", bbs_code="81",
           notes="Area per Wikipedia. Population: 2,978,156 adjusted / 2,915,009 enumerated (2022).")

seen_paths = set()
def uniq(path):
    p, n = path, 2
    while p in seen_paths:
        p = f"{path}-{n}"; n += 1
    seen_paths.add(p); return p

for r in up:
    i, did, en, bn, web = r
    d = dis_map[did]
    s = slugify(en)
    upz_map[i] = add(id=30000 + int(i), level="upazila", parent_id=d["id"], name_bn=bn, name_en=en, slug=s,
                     path=uniq(f"{d['path']}/{s}"), source_ref=f"nuhil:upazila:{i}", website=url(web), verified=True)
    if d["_src_en"] == "Rajshahi" and en in RAJ_UPZ_POP:
        upz_map[i].update(population_2022=RAJ_UPZ_POP[en], population_basis="enumerated", population_source="CITYPOP_RAJ",
                          evidence_level="secondary", evidence_source="CITYPOP_RAJ")

# Add Shayestaganj upazila (missing from source)
hab = next(d for d in dis_map.values() if d["_src_en"] == "Habiganj")
shay = add(id=30495, level="upazila", parent_id=hab["id"], name_bn="শায়েস্তাগঞ্জ", name_en="Shayestaganj", slug="shayestaganj",
           path=uniq(f"{hab['path']}/shayestaganj"), area_km2=39.55, area_basis="official", population_2022=97408,
           population_basis="enumerated", population_source="WIKI_SHAY", established="2017-11-20", verified=True,
           data_source="WIKI_SHAY", evidence_level="secondary", evidence_source="WIKI_SHAY", notes="Missing from nuhil source; added. Unions: Brahmandura, Nurpur, Shayestaganj + Shayestaganj pourashava (9 wards).")

MOVE_TO_SHAY = {"Nurpur", "Shayestaganj"}
habsadar = next(u for u in upz_map.values() if u["name_en"] == "Habiganj Sadar")
changes = []   # reconciliation changes applied to the vendored source, written to qa/
for i, fix in UNION_NAME_FIXES.items():
    changes.append(dict(record=f"nuhil:union:{i}", change="name_fix", detail=fix["why"], source=fix.get("source", "")))
for i, why in UNION_DUPLICATE_DROPS.items():
    changes.append(dict(record=f"nuhil:union:{i}", change="duplicate_dropped", detail=why, source=""))
natore = next(d for d in dis_map.values() if d["_src_en"] == "Natore")
naldanga = next(u for u in upz_map.values() if u["parent_id"] == natore["id"] and u["name_en"] == "Naldanga")
natore_sadar = next(u for u in upz_map.values() if u["parent_id"] == natore["id"] and u["name_en"] == "Natore Sadar")
for r in un:
    i, uid, en, bn, web = r
    if i in UNION_DUPLICATE_DROPS:
        continue
    fix = UNION_NAME_FIXES.get(i, {})
    en, bn = fix.get("name_en", en), fix.get("name_bn", bn)
    u = upz_map[uid]
    parent = u
    note = fix.get("why")
    if u is habsadar and en in MOVE_TO_SHAY:
        parent, note = shay, "Re-parented from Habiganj Sadar to Shayestaganj (created 2017)."
    if u is natore_sadar and i in NALDANGA_UNION_IDS:
        parent, note = naldanga, ("Re-parented from Natore Sadar to Naldanga upazila per Natore District Administration "
                                  "(SRC-NAT-GLANCE-2026, SRC-NAT-DIST-UP-2025 in master v3.0).")
        changes.append(dict(record=f"nuhil:union:{i}", change="reparented", detail=f"{en}: Natore Sadar -> Naldanga",
                            source="NATORE_DC_2026"))
    s = slugify(en)
    add(id=40000 + int(i), level="union", parent_id=parent["id"], name_bn=bn, name_en=en, slug=s,
        path=uniq(f"{parent['path']}/{s}"), source_ref=f"nuhil:union:{i}", website=url(web), verified=True, notes=note)
add(id=44541, level="union", parent_id=shay["id"], name_bn="ব্রাহ্মণডুরা", name_en="Brahmandura", slug="brahmandura",
    path=uniq(f"{shay['path']}/brahmandura"), verified=False, production_eligible=False, data_source="WIKI_SHAY",
    evidence_level="secondary", evidence_source="WIKI_SHAY",
    notes="Added from Wikipedia union list; Bengali spelling to confirm, so held back from production.")
assert sum(1 for r in rows if r["parent_id"] == naldanga["id"]) == len(NALDANGA_UNION_IDS), "Naldanga re-parenting did not match 5 unions"

# City corporations
dis_by_src = {d["_src_en"]: d for d in dis_map.values()}
for n, (en, bn, dist, area, pop, wards, est, note) in enumerate(CITY_CORPORATIONS, 1):
    d = dis_by_src[dist]
    s = slugify(en.replace(" City Corporation", "")) + "-city-corporation"
    src = "FE_BOGURA" if dist == "Bogura" else "WIKI_CC"
    add(id=50000 + n, level="city_corporation", parent_id=d["id"], name_bn=bn, name_en=en, slug=s, path=uniq(f"{d['path']}/{s}"),
        area_km2=area, area_basis="official", population_2022=pop,
        population_basis="estimate" if dist == "Bogura" else "census", population_source=src, wards_count=wards,
        established=str(est) if est else None, verified=True, data_source=src, notes=note or None,
        evidence_level="secondary", evidence_source=src)

# Rajshahi pourashavas (unverified)
raj_upz = {u["name_en"]: u for u in upz_map.values() if u["parent_id"] == raj["id"]}
for n, (en, bn, upz) in enumerate(RAJ_POURASHAVAS, 1):
    u = raj_upz[upz]
    s = slugify(en) + "-pourashava"
    add(id=60000 + n, level="pourashava", parent_id=u["id"], name_bn=bn + " পৌরসভা", name_en=en + " Pourashava", slug=s,
        path=uniq(f"{u['path']}/{s}"), verified=False, production_eligible=False, data_source="UNVERIFIED", evidence_level="unverified",
        notes="Rajshahi District has 14 pourashavas (Desh Rupantor headline); names/parents from general knowledge — confirm with LGD.")

for r in rows:
    r.pop("_src_en", None)
    r["production_eligible"] = eligible(r["evidence_level"], r["evidence_source"], r["production_eligible"])
    r["verified"] = r["evidence_level"] == "official"   # legacy flag: true only for official evidence
    if not r["production_eligible"] and r["evidence_level"] == "community":
        r["verification_notes"] = "Community dataset only (nuhil); needs an official or secondary source before publication."
policy_errors = [(r["id"], e) for r in rows for e in check_row(r)]
assert not policy_errors, policy_errors[:5]

# ---------- write geo files ----------
COLS = ["id", "level", "parent_id", "name_bn", "name_en", "slug", "path", "bbs_code", "source_ref", "website", "lat", "lon",
        "area_km2", "area_basis", "population_2022", "population_basis", "population_source", "wards_count", "established",
        "verified", "production_eligible", "evidence_level", "evidence_source", "data_source", "notes"]
def write_csv(path, data, cols):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(data)
def write_json(path, data):
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

public_rows = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
write_csv(f"{OUT}/geo/admin_areas.csv", public_rows, COLS)
write_json(f"{OUT}/geo/admin_areas.json", public_rows)
for lvl, fn in [("division", "divisions"), ("district", "districts"), ("upazila", "upazilas"), ("union", "unions"),
                ("city_corporation", "city_corporations"), ("pourashava", "pourashavas_rajshahi_unverified")]:
    write_csv(f"{OUT}/geo/{fn}.csv", [r for r in public_rows if r["level"] == lvl], COLS)

# nested tree for the app's explorer
byp = {}
for r in rows: byp.setdefault(r["parent_id"], []).append(r)
def tree(node):
    kids = sorted(byp.get(node["id"], []), key=lambda x: (x["level"], x["name_en"]))
    out = {k: node[k] for k in ("id", "level", "name_bn", "name_en", "path")}
    if kids: out["children"] = [tree(k) for k in kids]
    return out
write_json(f"{OUT}/geo/hierarchy_tree.json", tree(rows[0]))
json.dump(gj, open(f"{OUT}/geo/districts.geojson", "w", encoding="utf-8"), ensure_ascii=False)

# ---------- simplified boundaries for the web map ----------
def _dp(pts, tol):
    """Douglas–Peucker on a list of [x, y]."""
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    norm = math.hypot(dx, dy)
    best, idx = -1.0, 0
    for k in range(1, len(pts) - 1):
        px, py = pts[k]
        d = abs(dy * px - dx * py + x2 * y1 - y2 * x1) / norm if norm else math.hypot(px - x1, py - y1)
        if d > best:
            best, idx = d, k
    if best <= tol:
        return [pts[0], pts[-1]]
    return _dp(pts[: idx + 1], tol)[:-1] + _dp(pts[idx:], tol)

def _simplify_ring(ring, tol):
    out = _dp(ring, tol)
    out = [[round(x, 4), round(y, 4)] for x, y in out]
    if out[0] != out[-1]:
        out.append(out[0])
    return out if len(out) >= 4 else None

WEB_GEO = os.path.join(ROOT, "apps", "web", "public", "geo")
os.makedirs(WEB_GEO, exist_ok=True)
web_features = []
for f in gj["features"]:
    g = f["geometry"]
    polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    kept = []
    for poly in polys:
        outer = _simplify_ring(poly[0], 0.004)
        if outer and ring_area(outer) > 2.0:   # drop specks under ~2 km² (tiny char islands)
            kept.append([outer] + [h for h in (_simplify_ring(r, 0.004) for r in poly[1:]) if h])
    if not kept:   # never drop a whole district
        kept = [[_simplify_ring(max((p[0] for p in polys), key=len), 0.001)]]
    pr = f["properties"]
    web_features.append({"type": "Feature", "id": pr["district_id"],
                         "properties": {k: pr[k] for k in ("district_id", "division_id", "name_bn", "name_en", "path")},
                         "geometry": {"type": "MultiPolygon", "coordinates": kept}})
with open(os.path.join(WEB_GEO, "districts.json"), "w", encoding="utf-8") as fh:
    json.dump({"type": "FeatureCollection", "features": web_features}, fh, ensure_ascii=False, separators=(",", ":"))

# ---------- taxonomy ----------
cats = []
cid = 0
for so, (key, bn, en, icon, color, subs) in enumerate(CATEGORIES, 1):
    cid += 1; pid = cid
    cats.append(dict(id=pid, key=key, parent_id=None, name_bn=bn, name_en=en, icon=icon, color=color, sort_order=so))
    for sso, (sk, sbn, sen) in enumerate(subs, 1):
        cid += 1
        cats.append(dict(id=cid, key=f"{key}.{sk}", parent_id=pid, name_bn=sbn, name_en=sen, icon=None, color=color, sort_order=sso))
write_csv(f"{OUT}/taxonomy/categories.csv", cats, list(cats[0].keys()))
write_json(f"{OUT}/taxonomy/categories.json",
           [dict(c, children=[s for s in cats if s["parent_id"] == c["id"]]) for c in cats if c["parent_id"] is None])
cat_by_key = {c["key"]: c for c in cats}

# ---------- reference ----------
srcs = [dict(id=SRC_IDS[k], key=k, name=v[0], url=v[1]) for k, v in SRC.items()]
write_csv(f"{OUT}/reference/data_sources.csv", srcs, ["id", "key", "name", "url"])
hot = [dict(number=n, name_bn=bn, name_en=en, category=c, verified=v, evidence_level="secondary" if v else "unverified",
            source=s, source_url=SRC[s][1], notes=no, sort_order=i)
       for i, (n, bn, en, c, v, s, no) in enumerate(HOTLINES, 1)]
write_csv(f"{OUT}/reference/emergency_hotlines.csv", hot, list(hot[0].keys()))

# ---------- pilot places ----------
area_by = {(r["level"], r["name_en"], r["parent_id"]): r for r in rows}
places = []
for n, p in enumerate(PLACES, 1):
    in_rcc = p["upazila"] == "Paba"   # city-area places: Rajshahi City Corporation, not an upazila
    prefix = {"education": "INST", "health": "INST", "religious": "INST", "tourism": "TOUR"}.get(p["category"], "PLC")
    rec = dict(public_id=f"{prefix}-{n:08d}", **{k: v for k, v in p.items() if k not in ("district", "upazila")},
               division_id=div_map["2"]["id"], district_id=raj["id"],
               upazila_id=None if in_rcc else raj_upz[p["upazila"]]["id"],
               city_corporation_id=50005 if in_rcc else None,
               category_id=cat_by_key[p["category"]]["id"], subcategory_id=cat_by_key[f"{p['category']}.{p['subcategory']}"]["id"],
               source_url=SRC[p["source"]][1], verification_status="verified" if p["verified"] else "unverified",
               evidence_level="secondary" if p["verified"] else "unverified",
               evidence_source=p["source"] if p["verified"] else None)
    rec["production_eligible"] = eligible(rec["evidence_level"], rec["evidence_source"])
    rec["verified"] = False   # no place has official evidence yet; see evidence_level
    assert not check_row(rec), (rec["slug"], check_row(rec))
    places.append(nfc_dict(rec))
write_json(f"{OUT}/pilot_rajshahi/places.json", places)
pcols = ["public_id", "slug", "name_bn", "name_en", "short_name", "category", "subcategory", "ownership", "address_en", "postcode",
         "lat", "lon", "website", "established", "verification_status", "evidence_level", "production_eligible", "source", "source_url", "notes"]
write_csv(f"{OUT}/pilot_rajshahi/places.csv", places, pcols)
write_json(f"{OUT}/pilot_rajshahi/mockup_demo_fixtures_NOT_REAL.json",
           dict(warning="Names taken from the UI mockups. Not verified — use only as UI/dev fixtures, never import to production.",
                items=DEMO_FIXTURES))

# ---------- QA ----------
write_csv(f"{OUT}/qa/mockup_vs_verified.csv",
          [dict(topic=t, mockup_values=m, verified_value=v, source=SRC[s][0], source_url=SRC[s][1], action=a) for t, m, v, s, a in MOCKUP_VS_VERIFIED],
          ["topic", "mockup_values", "verified_value", "source", "source_url", "action"])
write_csv(f"{OUT}/qa/known_gaps.csv", [dict(area=a, gap=g, fix=f) for a, g, f in KNOWN_GAPS], ["area", "gap", "fix"])

write_csv(f"{OUT}/qa/reconciliation_changes.csv", changes + [dict(record=f"source:{k}", change="url_fixed", detail=why, source=k)
          for k, why in SOURCE_URL_FIXES.items()], ["record", "change", "detail", "source"])

# before/after verification flags (the v0.1 seed called the nuhil hierarchy verified + production-eligible)
from collections import Counter as _C
va = _C()
for r in rows:
    b_ver, b_el = r["_before"]
    va[(r["level"], r["evidence_level"], b_ver, b_el, r["verified"], r["production_eligible"])] += 1
write_csv(f"{OUT}/qa/verification_changes.csv",
          [dict(level=k[0], evidence_level=k[1], before_verified=k[2], before_production_eligible=k[3],
                after_verified=k[4], after_production_eligible=k[5], records=n) for k, n in sorted(va.items(), key=lambda x: (x[0][0], x[0][1]))],
          ["level", "evidence_level", "before_verified", "before_production_eligible", "after_verified", "after_production_eligible", "records"])

# seed vs Consolidated Master v3.0 (Rajshahi Division)
upz_cmp, name_cmp, dist_cmp = reconcile.compare(rows, KNOWN_MASTER_DIFFS)
write_csv(f"{OUT}/qa/seed_vs_master_upazilas.csv", upz_cmp, list(upz_cmp[0].keys()))
write_csv(f"{OUT}/qa/seed_vs_master_union_names.csv", name_cmp,
          ["district", "upazila", "side", "union_en", "union_bn", "status", "note"])
write_csv(f"{OUT}/qa/seed_vs_master_districts.csv", dist_cmp, list(dist_cmp[0].keys()))
write_csv(f"{OUT}/qa/unresolved_conflicts.csv", reconcile.conflicts(),
          ["conflict_id", "district", "topic", "status", "detail", "source_file"])

# counts summary
from collections import Counter
cnt = Counter(r["level"] for r in rows)
summary = {lvl: cnt[lvl] for lvl in ["division", "district", "upazila", "union", "city_corporation", "pourashava"]}
unions_per_upz = Counter(r["parent_id"] for r in rows if r["level"] == "union")
summary["upazilas_without_unions"] = [u["name_en"] for u in rows if u["level"] == "upazila" and unions_per_upz[u["id"]] == 0]
summary["rajshahi_district_unions_by_upazila"] = {u["name_en"]: unions_per_upz[u["id"]] for u in raj_upz.values()}
summary["rajshahi_district_unions_total"] = sum(summary["rajshahi_district_unions_by_upazila"].values())
summary["district_area_check_rajshahi_computed_km2"] = round(geom_area(geo_by_name["Rajshahi"]["geometry"]), 1)
summary["sum_district_area_km2"] = round(sum(r["area_km2"] or 0 for r in rows if r["level"] == "district"), 0)
summary["categories"] = {"top_level": sum(1 for c in cats if not c["parent_id"]), "sub": sum(1 for c in cats if c["parent_id"])}
summary["production_eligible_by_level"] = {lvl: sum(1 for r in rows if r["level"] == lvl and r["production_eligible"])
                                           for lvl in ["country", "division", "district", "upazila", "union", "city_corporation", "pourashava"]}
summary["seed_vs_master_untracked"] = sum(1 for r in upz_cmp + name_cmp if r["status"] == "UNTRACKED")
write_json(f"{OUT}/qa/counts_summary.json", summary)

# ---------- SQL seed ----------
def lit(v):
    if v is None: return "NULL"
    if isinstance(v, bool): return "true" if v else "false"
    if isinstance(v, (int, float)): return repr(v)
    if isinstance(v, (dict, list)): return "'" + json.dumps(v, ensure_ascii=False).replace("'", "''") + "'::jsonb"
    return "'" + str(v).replace("'", "''") + "'"

with open(SQL_OUT, "w", encoding="utf-8") as f:
    f.write("-- Elaka360 seed data. Generated; load after schema.sql.\nBEGIN;\n")
    for s in srcs:
        meta = SOURCE_META.get(s["key"], {})
        f.write("INSERT INTO data_sources(id,key,name,url,source_type,organization,license,trust_level,access_date) VALUES "
                f"({s['id']},{lit(s['key'])},{lit(s['name'])},{lit(s['url'] or None)},{lit(meta.get('type', 'unknown'))},"
                f"{lit(meta.get('org'))},{lit(meta.get('license'))},{meta.get('trust', 2)},{lit(meta.get('accessed'))});\n")
    f.write(f"SELECT setval('data_sources_id_seq', {len(srcs)});\n")
    acols = ["id", "level", "parent_id", "name_bn", "name_en", "slug", "path", "bbs_code", "source_ref", "website", "lat", "lon",
             "area_km2", "area_basis", "population_2022", "population_basis", "population_source_id", "wards_count", "established",
             "verified", "production_eligible", "data_source_id", "notes", "evidence_level", "evidence_source_id", "verification_notes"]
    for r in rows:   # parents always precede children in `rows`
        vals = dict(r, population_source_id=SRC_IDS.get(r["population_source"]), data_source_id=SRC_IDS.get(r["data_source"]),
                    evidence_source_id=SRC_IDS.get(r["evidence_source"]), verification_notes=r.get("verification_notes"))
        f.write(f"INSERT INTO admin_areas({','.join(acols)}) VALUES ({','.join(lit(vals[c]) for c in acols)});\n")
    for c in cats:
        f.write(f"INSERT INTO categories(id,key,parent_id,name_bn,name_en,icon,color,sort_order) VALUES ({c['id']},{lit(c['key'])},{lit(c['parent_id'])},{lit(c['name_bn'])},{lit(c['name_en'])},{lit(c['icon'])},{lit(c['color'])},{c['sort_order']});\n")
    f.write(f"SELECT setval('categories_id_seq', {len(cats)});\n")
    for h in hot:
        f.write(f"INSERT INTO emergency_numbers(number,name_bn,name_en,category,verified,evidence_level,data_source_id,notes,sort_order) VALUES ({lit(h['number'])},{lit(h['name_bn'])},{lit(h['name_en'])},{lit(h['category'])},{lit(h['verified'])},{lit(h['evidence_level'])},{SRC_IDS[h['source']]},{lit(h['notes'] or None)},{h['sort_order']});\n")
    pc = ["public_id", "slug", "name_bn", "name_en", "short_name", "category_id", "subcategory_id", "ownership", "division_id", "district_id",
          "upazila_id", "city_corporation_id", "address_en", "postcode", "lat", "lon", "website", "established", "attributes",
          "verification_status", "data_source_id", "source_notes", "last_verified_at", "evidence_level", "evidence_source_id", "production_eligible"]
    for p in places:
        v = dict(p, data_source_id=SRC_IDS[p["source"]], source_notes=p["notes"], evidence_source_id=SRC_IDS.get(p["evidence_source"]),
                 last_verified_at="2026-11-09" if p["evidence_level"] == "secondary" else None)
        f.write(f"INSERT INTO places({','.join(pc)}) VALUES ({','.join(lit(v[c]) for c in pc)});\n")
    # gamification seeds from the profile mockups (level 4 + badges); other level names are placeholders
    for lv, bn, en, pts in [(1, "নতুন অবদানকারী", "Newcomer", 0), (2, "সক্রিয় সদস্য", "Active member", 500),
                            (3, "এলাকা সহায়ক", "Area helper", 1500), (4, "এলাকা অ্যাম্বাসেডর", "Area Ambassador", 3000),
                            (5, "এলাকা বিশেষজ্ঞ", "Area Expert", 5000)]:
        f.write(f"INSERT INTO levels VALUES ({lv},{lit(bn)},{lit(en)},{pts});\n")
    for key, bn, en, rule in [("active_contributor", "সক্রিয় অবদানকারী", "Active contributor", {"type": "contributions", "gte": 10}),
                              ("photo_contributor", "ফটো কন্ট্রিবিউটর", "Photo contributor", {"type": "approved_photos", "gte": 10}),
                              ("verified_informant", "যাচাইকৃত তথ্যদাতা", "Verified informant", {"type": "approved_contributions", "gte": 10}),
                              ("local_expert", "স্থানীয় বিশেষজ্ঞ", "Local expert", {"type": "approved_in_one_area", "gte": 20}),
                              ("first_contribution", "প্রথম অবদান", "First contribution", {"type": "approved_contributions", "gte": 1})]:
        f.write(f"INSERT INTO badges(key,name_bn,name_en,rule) VALUES ({lit(key)},{lit(bn)},{lit(en)},{lit(rule)});\n")
    for feat in web_features:
        f.write(f"UPDATE admin_areas SET boundary = ST_Multi(ST_GeomFromGeoJSON({lit(json.dumps(feat['geometry'], separators=(',', ':')))}))::geography "
                f"WHERE id = {feat['properties']['district_id']};\n")
    f.write("INSERT INTO releases(version,title,scope_area_id,status,production_eligible,notes) VALUES "
            f"('v2.8','Rajshahi District',{raj['id']},'released',false,'71 unions; Bagha 6 vs 7 open (from admin mockup)'),"
            "('v2.9','Bogura District Deep Reconciliation',20014,'released',false,'108 vs 109 unions; Mokamtala upazila; 2026 union renames'),"
            "('v3.0','Rajshahi Division consolidation & quality audit',10002,'released',false,'Master v3.0: 563 selected vs 562 BBS 2011; production gate BLOCKED; compact copy in data/sources/master_v3');\n")
    f.write("COMMIT;\n")

shutil.copy(f"{SRC_DIR}/LICENSE", f"{OUT}/geo/LICENSE-nuhil-bangladesh-geocode.txt")
print(json.dumps(summary, ensure_ascii=False, indent=1))
