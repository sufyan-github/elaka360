"""City thanas, mouzas and villages / mahallas from the BBS Population and Housing Census 2022 (Community Reports,
table C-01), which data/sources/bbs_census_2022*/raw/c01_*.csv already hold.

Structure follows the census geocode exactly; nothing is forced into a tree it does not have:
  union or ward → mouza → village / mahalla     (C-01 nests every village code inside a mouza code)
  city corporation → thana                      (metropolitan police thanas; BBS counts city wards inside them)
A ward of a city corporation stays a child of the city corporation; its thana(s) are a separate relation
(admin_area_links, relation 'thana'), because one ward can lie in two thanas.

Names are English as BBS prints them. There is no Bangla source for these units yet, so name_bn stays empty (the site
falls back to English); no transliteration. Population is the enumerated count. No coordinates or boundaries: the
census publishes none for these levels.

Rows are written to data/seed/geo/localities/<division>.csv and db/seed/localities/<division>.sql, loaded after
reference.sql. Existing areas are never changed here.

Usage: python3 pipelines/localities.py      (standalone: reads the built data/seed/geo/admin_areas.csv)
       build_seed.py calls write_all(rows, SRC_IDS) after it writes the admin areas.
"""
import csv, json, os, re, shutil, sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from trust import nfc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = os.path.join(ROOT, "data", "sources")
CSV_DIR = os.path.join(ROOT, "data", "seed", "geo", "localities")
SQL_DIR = os.path.join(ROOT, "db", "seed", "localities")
QA = os.path.join(ROOT, "data", "seed", "qa", "localities_unplaced.csv")

THANA_ID, MOUZA_ID, VILLAGE_ID = 80001, 1_000_001, 2_000_001
PART = re.compile(r"\s*\(\s*part\s*\)?\s*", re.I)
PART_NOTE = "BBS 2022 counts this unit in more than one union or ward; the population is for this part only."
MAHALLA_NOTE = "Mahalla (urban neighbourhood) in BBS 2022."
COLS = ["id", "level", "parent_id", "name_bn", "name_en", "slug", "path", "bbs_code", "population_2022", "population_basis",
        "population_source", "verified", "production_eligible", "evidence_level", "evidence_source", "data_source", "notes"]


def slugify(s):
    s = s.lower().replace("'", "").replace("&", "and")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def clean_name(raw):
    """'Boalia (Part)*' → ('Boalia', True). The trailing * marks a mouza row in C-01."""
    n = nfc(raw).strip().rstrip("*").strip()
    part = bool(PART.search(n))
    n = PART.sub(" ", n).strip()
    return re.sub(r"\s+", " ", n), part


def census_folders():
    out = []
    for d in sorted(os.listdir(SOURCES)):
        if not d.startswith("bbs_census_2022"):
            continue
        m = json.load(open(os.path.join(SOURCES, d, "SOURCE.json"), encoding="utf-8"))
        raw = os.path.join(SOURCES, d, "raw")
        c01 = [f for f in os.listdir(raw) if f.startswith("c01_") and f.endswith(".csv")] if os.path.isdir(raw) else []
        if c01:
            out.append((m["division"], m["key"], os.path.join(raw, c01[0])))
    return out


def build(rows):
    """New thana / mouza / village rows and ward–thana links from the census, given the built admin areas."""
    by_code = {r["bbs_code"]: r for r in rows if r.get("bbs_code")}
    divisions = {r["slug"]: r for r in rows if r["level"] == "division"}
    city_wards = {(r["parent_id"], int(m.group(1))): r for r in rows
                  if r["level"] == "ward" and (m := re.fullmatch(r"Ward (\d+)", r["name_en"] or ""))}
    paths = {r["path"] for r in rows}

    def uniq(path):
        p, n = path, 2
        while p in paths:
            p = f"{path}-{n}"; n += 1
        paths.add(p); return p

    thanas, mouzas, villages, links, unplaced = [], [], [], set(), Counter()
    for div_slug, key, path in census_folders():
        div = divisions[div_slug]
        dc = div["bbs_code"]
        recs = list(csv.DictReader(open(path, encoding="utf-8-sig")))

        def code(*parts):
            return "-".join([dc, *[p for p in parts if p]])

        def parent_of(r):
            """The existing union / ward a C-01 row belongs to (None when the seed has no such unit)."""
            d, cc, ut, pa, uw = (r[k] for k in ("district_code", "city_corporation_code", "upazila_thana_code",
                                                "paurashava_code", "union_ward_code"))
            if cc:
                corp = by_code.get(code(d, cc))
                return city_wards.get((corp["id"], int(uw))) if corp and uw.isdigit() else None
            return by_code.get(code(d, ut, pa, uw)) if pa else by_code.get(code(d, ut, uw))

        # city thanas (C-01: city corporation + thana code, no ward)
        for r in recs:
            if r["city_corporation_code"] and r["upazila_thana_code"] and not r["union_ward_code"] and not r["paurashava_code"]:
                corp = by_code.get(code(r["district_code"], r["city_corporation_code"]))
                if not corp:
                    unplaced[(div_slug, "thana", code(r["district_code"], r["city_corporation_code"]))] += 1
                    continue
                name, _ = clean_name(r["name"])
                thanas.append(dict(level="thana", parent=corp, name_en=name, code=code(r["district_code"], r["city_corporation_code"],
                                   r["upazila_thana_code"]), pop=r["pop_total"], src=key, notes=None))
            # wards inside a thana: one link per (ward, thana) pair
            if r["city_corporation_code"] and r["union_ward_code"] and not r["mauza_code"]:
                w = parent_of(r)
                if w:
                    links.add((w["id"], code(r["district_code"], r["city_corporation_code"], r["upazila_thana_code"]), key))

        mouza_of = {}
        for r in recs:
            if not r["mauza_code"]:
                continue
            parent = parent_of(r)
            mkey = (r["district_code"], r["city_corporation_code"], r["upazila_thana_code"], r["paurashava_code"],
                    r["union_ward_code"], r["mauza_code"])
            if not r["village_mahalla_code"]:
                if not parent:
                    unplaced[(div_slug, "mouza", code(*mkey[:5]))] += 1
                    continue
                name, part = clean_name(r["name"])
                m = dict(level="mouza", parent=parent, name_en=name, code=code(*mkey), pop=r["pop_total"], src=key,
                         notes=PART_NOTE if part else None)
                mouzas.append(m); mouza_of[mkey] = m
            else:
                m = mouza_of.get(mkey)
                if not m:
                    unplaced[(div_slug, "village", code(*mkey))] += 1
                    continue
                name, part = clean_name(r["name"])
                urban = bool(r["city_corporation_code"] or r["paurashava_code"])
                notes = " ".join(x for x in (MAHALLA_NOTE if urban else None, PART_NOTE if part else None) if x) or None
                villages.append(dict(level="village", parent=m, name_en=name, code=code(*mkey, r["village_mahalla_code"]),
                                     pop=r["pop_total"], src=key, notes=notes))

    out = []
    thana_by_code = {}
    for first, items in ((THANA_ID, thanas), (MOUZA_ID, mouzas), (VILLAGE_ID, villages)):
        items.sort(key=lambda x: x["code"])
        for i, x in enumerate(items):
            parent = x["parent"] if "id" in x["parent"] else x["parent"]["row"]
            s = slugify(x["name_en"]) or f"{x['level']}-{x['code'].split('-')[-1]}"
            pop = int(x["pop"]) if str(x["pop"]).isdigit() else None
            row = dict(id=first + i, level=x["level"], parent_id=parent["id"], name_bn="", name_en=x["name_en"], slug=s,
                       path=uniq(f"{parent['path']}/{s}"), bbs_code=x["code"], population_2022=pop,
                       population_basis="enumerated" if pop is not None else None, population_source=x["src"] if pop is not None else None,
                       verified=True, production_eligible=True, evidence_level="official", evidence_source=x["src"],
                       data_source=x["src"], notes=x["notes"], _div=parent["path"].split("/")[0])
            x["row"] = row
            out.append(row)
            if x["level"] == "thana":
                thana_by_code[x["code"]] = row
    link_rows = sorted({(w, thana_by_code[t]["id"], src) for w, t, src in links if t in thana_by_code})
    return out, link_rows, unplaced


def lit(v):
    if v is None: return "NULL"
    if isinstance(v, bool): return "true" if v else "false"
    if isinstance(v, (int, float)): return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


SQL_COLS = ["id", "level", "parent_id", "name_bn", "name_en", "slug", "path", "bbs_code", "population_2022", "population_basis",
            "population_source_id", "verified", "production_eligible", "data_source_id", "notes", "evidence_level", "evidence_source_id"]


def write_all(rows, src_ids):
    areas, links, unplaced = build(rows)
    for d in (CSV_DIR, SQL_DIR):
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)
    by_div = defaultdict(list)
    for a in areas:
        by_div[a["_div"]].append(a)
    ward_div = {r["id"]: r["path"].split("/")[0] for r in rows if r["level"] == "ward"}
    links_by_div = defaultdict(list)
    for w, t, src in links:
        links_by_div[ward_div[w]].append((w, t, src))
    for div, items in sorted(by_div.items()):
        # parents precede children: thanas, then mouzas, then villages (ids ascend in that order)
        items.sort(key=lambda a: a["id"])
        with open(os.path.join(CSV_DIR, f"{div}.csv"), "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore"); w.writeheader(); w.writerows(items)
        with open(os.path.join(SQL_DIR, f"{div}.sql"), "w", encoding="utf-8") as f:
            f.write("-- Elaka360 seed data. Generated by pipelines/localities.py; loaded through db/seed/seed.sql.\n")
            for i in range(0, len(items), 500):
                vals = ",\n".join("(" + ",".join(lit(v) for v in (
                    a["id"], a["level"], a["parent_id"], a["name_bn"], a["name_en"], a["slug"], a["path"], a["bbs_code"],
                    a["population_2022"], a["population_basis"], src_ids.get(a["population_source"]), a["verified"],
                    a["production_eligible"], src_ids[a["data_source"]], a["notes"], a["evidence_level"],
                    src_ids[a["evidence_source"]])) + ")" for a in items[i:i + 500])
                f.write(f"INSERT INTO admin_areas({','.join(SQL_COLS)}) VALUES\n{vals};\n")
            lk = sorted(links_by_div.get(div, []))
            if lk:
                vals = ",\n".join(f"({w},{t},'thana',{src_ids[src]})" for w, t, src in lk)
                f.write(f"INSERT INTO admin_area_links(area_id,linked_area_id,relation,data_source_id) VALUES\n{vals};\n")
    with open(QA, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["division", "level", "census_parent_code", "rows"])
        for (div, lvl, c), n in sorted(unplaced.items()):
            w.writerow([div, lvl, c, n])
    counts = Counter(a["level"] for a in areas)
    return dict(counts, links=len(links), unplaced=sum(unplaced.values()), divisions=sorted(by_div))


def _load_built():
    def val(k, v):
        if v == "": return None
        if k in ("id", "parent_id"): return int(v)
        return v
    rows = [{k: val(k, v) for k, v in r.items()} for r in csv.DictReader(
        open(os.path.join(ROOT, "data", "seed", "geo", "admin_areas.csv"), encoding="utf-8-sig"))]
    src_ids = {r["key"]: int(r["id"]) for r in csv.DictReader(
        open(os.path.join(ROOT, "data", "seed", "reference", "data_sources.csv"), encoding="utf-8-sig"))}
    return rows, src_ids


if __name__ == "__main__":
    print(json.dumps(write_all(*_load_built()), indent=1))
