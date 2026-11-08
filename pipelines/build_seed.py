"""Build the Elaka360 seed dataset from vendored sources + curated reference data.

Usage: python3 pipelines/build_seed.py
Outputs: data/seed/** and db/seed/seed.sql
"""
import csv, json, math, os, re, shutil, sys
sys.path.insert(0, os.path.dirname(__file__))
from refdata import *

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(ROOT, "data", "sources", "nuhil")
OUT = os.path.join(ROOT, "data", "seed")
SQL_OUT = os.path.join(ROOT, "db", "seed", "seed.sql")
shutil.rmtree(OUT, ignore_errors=True)
for d in ["geo", "taxonomy", "reference", "pilot_rajshahi", "qa"]:
    os.makedirs(f"{OUT}/{d}", exist_ok=True)

def rd(f):
    return [[c.strip() for c in r] for r in csv.reader(open(f"{SRC_DIR}/{f}", encoding="utf-8"))]

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
                production_eligible=True, data_source="NUHIL", notes=None)
    base.update(r); rows.append(base); return base

rows.append(dict(id=1, level="country", parent_id=None, name_bn="বাংলাদেশ", name_en="Bangladesh", slug="bangladesh", path="bangladesh",
                 bbs_code=None, source_ref=None, website=None, lat=None, lon=None, area_km2=None, area_basis=None,
                 population_2022=sum(DIVISION_POP.values()), population_basis="adjusted", population_source="CITYPOP_ADJ",
                 wards_count=None, established=None, verified=True, production_eligible=True, data_source="CITYPOP_ADJ", notes=None))

div_map, dis_map, upz_map = {}, {}, {}
for r in dv:
    i, en, bn, web = r
    fx = DIVISION_FIX[i]
    s = slugify(fx["name_en"])
    div_map[i] = add(id=10000 + int(i), level="division", parent_id=1, name_bn=bn, name_en=fx["name_en"], slug=s, path=s,
                     bbs_code=fx["bbs_code"], source_ref=f"nuhil:division:{i}", website=url(web),
                     population_2022=DIVISION_POP[fx["name_en"]], population_basis="adjusted", population_source="CITYPOP_ADJ",
                     verified=True)

for r in ds:
    i, did, en, bn, lat, lon, web = r
    name = DISTRICT_NAME_FIX.get(en, en)
    s = slugify(name)
    feat = geo_by_name.get(en)
    area = round(geom_area(feat["geometry"]), 1) if feat else None
    dis_map[i] = add(id=20000 + int(i), level="district", parent_id=div_map[did]["id"], name_bn=bn, name_en=name, slug=s,
                     path=f"{div_map[did]['slug']}/{s}", source_ref=f"nuhil:district:{i}", website=url(web),
                     lat=float(lat), lon=float(lon), area_km2=area, area_basis="computed_from_polygon" if area else None,
                     population_2022=DISTRICT_POP[en], population_basis="adjusted", population_source="CITYPOP_ADJ", verified=True)
    dis_map[i]["_src_en"] = en
    if feat:
        feat["properties"].update(district_id=20000 + int(i), name_en=name, name_bn=bn, division_id=div_map[did]["id"])

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
        upz_map[i].update(population_2022=RAJ_UPZ_POP[en], population_basis="enumerated", population_source="CITYPOP_RAJ")

# Add Shayestaganj upazila (missing from source)
hab = next(d for d in dis_map.values() if d["_src_en"] == "Habiganj")
shay = add(id=30495, level="upazila", parent_id=hab["id"], name_bn="শায়েস্তাগঞ্জ", name_en="Shayestaganj", slug="shayestaganj",
           path=uniq(f"{hab['path']}/shayestaganj"), area_km2=39.55, area_basis="official", population_2022=97408,
           population_basis="enumerated", population_source="WIKI_SHAY", established="2017-11-20", verified=True,
           data_source="WIKI_SHAY", notes="Missing from nuhil source; added. Unions: Brahmandura, Nurpur, Shayestaganj + Shayestaganj pourashava (9 wards).")

MOVE_TO_SHAY = {"Nurpur", "Shayestaganj"}
habsadar = next(u for u in upz_map.values() if u["name_en"] == "Habiganj Sadar")
for r in un:
    i, uid, en, bn, web = r
    u = upz_map[uid]
    parent = u
    note = None
    if u is habsadar and en in MOVE_TO_SHAY:
        parent, note = shay, "Re-parented from Habiganj Sadar to Shayestaganj (created 2017)."
    s = slugify(en)
    add(id=40000 + int(i), level="union", parent_id=parent["id"], name_bn=bn, name_en=en, slug=s,
        path=uniq(f"{parent['path']}/{s}"), source_ref=f"nuhil:union:{i}", website=url(web), verified=True, notes=note)
add(id=44541, level="union", parent_id=shay["id"], name_bn="ব্রাহ্মণডুরা", name_en="Brahmandura", slug="brahmandura",
    path=uniq(f"{shay['path']}/brahmandura"), verified=False, production_eligible=False, data_source="WIKI_SHAY",
    notes="Added from Wikipedia union list; Bengali spelling to confirm.")

# City corporations
dis_by_src = {d["_src_en"]: d for d in dis_map.values()}
for n, (en, bn, dist, area, pop, wards, est, note) in enumerate(CITY_CORPORATIONS, 1):
    d = dis_by_src[dist]
    s = slugify(en.replace(" City Corporation", "")) + "-city-corporation"
    src = "FE_BOGURA" if dist == "Bogura" else "WIKI_CC"
    add(id=50000 + n, level="city_corporation", parent_id=d["id"], name_bn=bn, name_en=en, slug=s, path=uniq(f"{d['path']}/{s}"),
        area_km2=area, area_basis="official", population_2022=pop,
        population_basis="estimate" if dist == "Bogura" else "census", population_source=src, wards_count=wards,
        established=str(est) if est else None, verified=True, data_source=src, notes=note or None)

# Rajshahi pourashavas (unverified)
raj_upz = {u["name_en"]: u for u in upz_map.values() if u["parent_id"] == raj["id"]}
for n, (en, bn, upz) in enumerate(RAJ_POURASHAVAS, 1):
    u = raj_upz[upz]
    s = slugify(en) + "-pourashava"
    add(id=60000 + n, level="pourashava", parent_id=u["id"], name_bn=bn + " পৌরসভা", name_en=en + " Pourashava", slug=s,
        path=uniq(f"{u['path']}/{s}"), verified=False, production_eligible=False, data_source="UNVERIFIED",
        notes="Rajshahi District has 14 pourashavas (Desh Rupantor headline); names/parents from general knowledge — confirm with LGD.")

for r in rows: r.pop("_src_en", None)

# ---------- write geo files ----------
COLS = ["id", "level", "parent_id", "name_bn", "name_en", "slug", "path", "bbs_code", "source_ref", "website", "lat", "lon",
        "area_km2", "area_basis", "population_2022", "population_basis", "population_source", "wards_count", "established",
        "verified", "production_eligible", "data_source", "notes"]
def write_csv(path, data, cols):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(data)
def write_json(path, data):
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

write_csv(f"{OUT}/geo/admin_areas.csv", rows, COLS)
write_json(f"{OUT}/geo/admin_areas.json", rows)
for lvl, fn in [("division", "divisions"), ("district", "districts"), ("upazila", "upazilas"), ("union", "unions"),
                ("city_corporation", "city_corporations"), ("pourashava", "pourashavas_rajshahi_unverified")]:
    write_csv(f"{OUT}/geo/{fn}.csv", [r for r in rows if r["level"] == lvl], COLS)

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
hot = [dict(number=n, name_bn=bn, name_en=en, category=c, verified=v, source=s, source_url=SRC[s][1], notes=no, sort_order=i)
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
               source_url=SRC[p["source"]][1], verification_status="verified" if p["verified"] else "unverified")
    places.append(rec)
write_json(f"{OUT}/pilot_rajshahi/places.json", places)
pcols = ["public_id", "slug", "name_bn", "name_en", "short_name", "category", "subcategory", "ownership", "address_en", "postcode",
         "lat", "lon", "website", "established", "verified", "source", "source_url", "notes"]
write_csv(f"{OUT}/pilot_rajshahi/places.csv", places, pcols)
write_json(f"{OUT}/pilot_rajshahi/mockup_demo_fixtures_NOT_REAL.json",
           dict(warning="Names taken from the UI mockups. Not verified — use only as UI/dev fixtures, never import to production.",
                items=DEMO_FIXTURES))

# ---------- QA ----------
write_csv(f"{OUT}/qa/mockup_vs_verified.csv",
          [dict(topic=t, mockup_values=m, verified_value=v, source=SRC[s][0], source_url=SRC[s][1], action=a) for t, m, v, s, a in MOCKUP_VS_VERIFIED],
          ["topic", "mockup_values", "verified_value", "source", "source_url", "action"])
write_csv(f"{OUT}/qa/known_gaps.csv", [dict(area=a, gap=g, fix=f) for a, g, f in KNOWN_GAPS], ["area", "gap", "fix"])

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
        f.write(f"INSERT INTO data_sources(id,key,name,url) VALUES ({s['id']},{lit(s['key'])},{lit(s['name'])},{lit(s['url'] or None)});\n")
    f.write(f"SELECT setval('data_sources_id_seq', {len(srcs)});\n")
    acols = ["id", "level", "parent_id", "name_bn", "name_en", "slug", "path", "bbs_code", "source_ref", "website", "lat", "lon",
             "area_km2", "area_basis", "population_2022", "population_basis", "population_source_id", "wards_count", "established",
             "verified", "production_eligible", "data_source_id", "notes"]
    for r in rows:   # parents always precede children in `rows`
        vals = dict(r, population_source_id=SRC_IDS.get(r["population_source"]), data_source_id=SRC_IDS.get(r["data_source"]))
        f.write(f"INSERT INTO admin_areas({','.join(acols)}) VALUES ({','.join(lit(vals[c]) for c in acols)});\n")
    for c in cats:
        f.write(f"INSERT INTO categories(id,key,parent_id,name_bn,name_en,icon,color,sort_order) VALUES ({c['id']},{lit(c['key'])},{lit(c['parent_id'])},{lit(c['name_bn'])},{lit(c['name_en'])},{lit(c['icon'])},{lit(c['color'])},{c['sort_order']});\n")
    f.write(f"SELECT setval('categories_id_seq', {len(cats)});\n")
    for h in hot:
        f.write(f"INSERT INTO emergency_numbers(number,name_bn,name_en,category,verified,data_source_id,notes,sort_order) VALUES ({lit(h['number'])},{lit(h['name_bn'])},{lit(h['name_en'])},{lit(h['category'])},{lit(h['verified'])},{SRC_IDS[h['source']]},{lit(h['notes'] or None)},{h['sort_order']});\n")
    pc = ["public_id", "slug", "name_bn", "name_en", "short_name", "category_id", "subcategory_id", "ownership", "division_id", "district_id",
          "upazila_id", "city_corporation_id", "address_en", "postcode", "lat", "lon", "website", "established", "attributes",
          "verification_status", "data_source_id", "source_notes", "last_verified_at"]
    for p in places:
        v = dict(p, data_source_id=SRC_IDS[p["source"]], source_notes=p["notes"], last_verified_at="2026-11-09" if p["verified"] else None)
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
    f.write("INSERT INTO releases(version,title,scope_area_id,status,production_eligible,notes) VALUES "
            f"('v2.8','Rajshahi District',{raj['id']},'released',false,'71 unions; Bagha 6 vs 7 open (from admin mockup)'),"
            "('v2.9','Bogura District Deep Reconciliation',20014,'planned',false,'108 vs 109 unions; Mokamtala upazila; 2026 union renames (from admin mockup)');\n")
    f.write("COMMIT;\n")

shutil.copy(f"{SRC_DIR}/LICENSE", f"{OUT}/geo/LICENSE-nuhil-bangladesh-geocode.txt")
print(json.dumps(summary, ensure_ascii=False, indent=1))
