"""Merge collected official sources (data/sources/*/, see COLLECTION_FORMAT.md) into the seed.

Scope today: Rajshahi Division. Called from build_seed.py:
  register_sources(SRC, SOURCE_META)          before source ids are assigned
  apply_admin(rows, add, uniq)                after the base hierarchy is built
  build_places(rows, base_places, cat_by_key) for points of interest

Rules (docs/data/DATA_TRUST_POLICY.md): evidence comes from the source's trust level; nothing is invented;
every change is recorded in `changes` (written to data/seed/qa/collected_changes.csv).
"""
import difflib, json, math, os, re
from collections import defaultdict
from collected import (PolygonIndex, _polys, SOURCES, bn_key, check_manifest, en_key, en_similarity, evidence_for, haversine_m,
                       manifests, name_similarity, read_csv, romanize_bn)
from reconcile import latin_key, upazila_key
from trust import nfc

# Divisions in processing order: a division added later never changes the ids or slugs of earlier ones.
# See data/sources/DIVISIONS.md.
DIVISIONS = [
    dict(name="rajshahi", id=10002, head=20015),
    dict(name="rangpur", id=10007, head=20059),
    dict(name="dhaka", id=10006, head=20047),
    dict(name="chattogram", id=10001, head=20008),
    dict(name="khulna", id=10003, head=20027),
    dict(name="barishal", id=10004, head=20033),
    dict(name="sylhet", id=10005, head=20036),
    dict(name="mymensingh", id=10008, head=20062),
]
DIVISION_ID = 10002       # Rajshahi: the first division collected (pilot places, metro-thana tables)
BBS = "BBS_CENSUS_2022"
# kind of the Rajshahi folders that predate the "kind" field in SOURCE.json
FOLDER_KIND = {
    "bbs_census_2022": "bbs_census", "hdx_cod_ab_bgd": "hdx_cod_ab", "geoboundaries_bgd_adm4": "geoboundaries_adm4",
    "dghs_bd_geocodes": "dghs_geocodes", "lgd": "lgd", "rajshahi_district_portal": "district_portal_main",
    "division_district_portals": "district_portals", "rajshahi_upazila_portals": "upazila_portals",
    "rajshahi_union_portals": "union_portals", "rajshahi_divisional_portal": "divisional_portal", "rcc": "city_corporation",
    "rmp": "metro_police", "rmp_thanas_2026": "metro_police_thanas", "rajshahi_police_2026": "district_police",
    "raj_range_police_portals_2026": "range_police", "bd_police_contacts_2020": "police_hq_2020",
    "fscd_stations_raj_2026": "fscd", "dghs_hris_facilities_raj_2026": "dghs_hris", "banbeis_inst_raj_2026": "banbeis",
    "dpe_ipemis_primary_raj_2026": "dpe_ipemis", "ugc_universities_raj_2026": "ugc", "dgme_medical_colleges_raj_2026": "dgme",
    "doa_protected_monuments_raj_2026": "doa_monuments", "bdpost_postcodes_raj_2026": "bdpost", "bd_railway_raj_2026": "railway",
    "caab_airports_raj_2026": "caab", "brtc_depots_raj_2026": "brtc", "bb_scheduled_banks_raj_2026": "bb_banks",
    "district_portal_banks_raj_2026": "district_banks", "district_portals_transport_raj_2026": "district_transport",
    "portal_tourist_spots_raj_2026": "tourist_spots", "rajshahi_portal_offices_2026": "portal_offices",
    "osm_rajshahi_division": "osm",
}
changes = []           # dicts: record, change, detail, source
problems = []          # manifest problems (reported by validate_seed.py)

_MANIFESTS = None


def _manifests():
    global _MANIFESTS
    if _MANIFESTS is None:
        _MANIFESTS = [m for m in manifests() if m["key"] not in ("NUHIL",)]
    return _MANIFESTS


def division_of(m):
    return m.get("division") or "rajshahi"


def kind_of(m):
    return m.get("kind") or FOLDER_KIND.get(os.path.basename(m["_dir"]))


def sources(division, kind):
    """Manifests of one kind collected for one division (sorted by key)."""
    return [m for m in _manifests() if division_of(m) == division and kind_of(m) == kind]


def place_files(m):
    """places.csv plus its continuation files places_2.csv, places_3.csv … (large sources split under 20 MB)."""
    first = os.path.join(m["_dir"], "places.csv")
    if not os.path.isfile(first):
        return []
    more = sorted((f for f in os.listdir(m["_dir"]) if re.fullmatch(r"places_\d+\.csv", f)), key=lambda f: int(re.sub(r"\D", "", f)))
    return [first] + [os.path.join(m["_dir"], f) for f in more]


def source(division, kind):
    found = sources(division, kind)
    return found[0] if found else None


def _dir(key):
    for m in _manifests():
        if m["key"] == key:
            return m["_dir"]
    return None


def _url(key):
    for m in _manifests():
        if m["key"] == key:
            return (m.get("urls") or [""])[0]
    return ""


def trust_of(key):
    for m in _manifests():
        if m["key"] == key:
            return int(m.get("trust_level") or 1)
    return 1


def register_sources(SRC, SOURCE_META):
    """Add every collected source to the data_sources registry. Ids follow DIVISIONS order, then folder name, so a new
    division only appends ids: earlier divisions' seed files stay byte-identical."""
    div_index = {d["name"]: i for i, d in enumerate(DIVISIONS)}
    # the non-government sources added after all eight divisions get ids after every government source, in the same order
    for m in sorted(_manifests(), key=lambda m: (SOURCE_BATCH.get(kind_of(m), 0), div_index.get(division_of(m), len(div_index)),
                                                 os.path.basename(m["_dir"]))):
        problems.extend(check_manifest(m))
        k = m["key"]
        if k in SRC:
            continue
        SRC[k] = (m["name"], (m.get("urls") or [""])[0])
        SOURCE_META[k] = dict(type=m.get("source_type", "unknown"), org=m.get("organization"), license=m.get("license"),
                              trust=int(m.get("trust_level") or 1), accessed=m.get("accessed"))


def log(record, change, detail, source=""):
    changes.append(dict(record=record, change=change, detail=detail, source=source))


# ------------------------------------------------------------------ matching helpers

def _best(target_en, candidates, key=lambda c: c["name_en"], threshold=0.72):
    """Best candidate by Banglish-normalised English similarity (exact key first)."""
    t = en_key(target_en)
    best, score = None, 0.0
    for c in candidates:
        k = en_key(key(c))
        s = 1.0 if k == t else difflib.SequenceMatcher(None, k, t).ratio()
        if s > score:
            best, score = c, s
    return (best, score) if score >= threshold else (None, score)


_DIRS = {"uttar": "N", "uttor": "N", "north": "N", "dakkhin": "S", "dakshin": "S", "dakshhin": "S", "dakhin": "S",
         "dokkhin": "S", "south": "S", "purba": "E", "purbo": "E", "east": "E", "paschim": "W", "pashchim": "W",
         "poschim": "W", "pashim": "W", "pachim": "W", "west": "W", "madhya": "M", "maddho": "M",
         "dakkin": "S", "dakshi": "S", "nourth": "N"}
_DIR_GLUED = re.compile(r"^(%s)([a-z]{3,})$|^([a-z]{3,}?)(%s)$" % ("|".join(_DIRS), "|".join(_DIRS)))


def _dir_split(n):
    """Direction words of a romanised name and the rest; also inside one word ('Eastjuri', 'Chitoshiwest')."""
    words = []
    for w in re.findall(r"[a-z]+", (n or "").lower()):
        m = None if w in _DIRS else _DIR_GLUED.match(w)
        words += [x for x in m.groups() if x] if m else [w]
    return {_DIRS[w] for w in words if w in _DIRS}, " ".join(w for w in words if w not in _DIRS)


def moved_union_similarity(a, b):
    """en_similarity with direction words compared as a set: 'Uttar Bangshikunda' = 'Bongshikunda North' only."""
    (da, ra), (db, rb) = _dir_split(a), _dir_split(b)
    return en_similarity(ra, rb) if da == db and ra and rb else 0.0


def _letter_dir(name, other_rest):
    """Seed names abbreviate a direction to a last letter ('Akhauran', 'Nabinagarw'): read it only when dropping the
    letter makes the name closer to the other name without its direction word."""
    w = re.sub(r"[^a-z]", "", (name or "").lower())
    if len(w) > 4 and w[-1] in "nsew" and other_rest and \
            en_similarity(w[:-1], other_rest) > en_similarity(w, other_rest):
        return {w[-1].upper()}
    return set()


def dir_similarity(a, b, boost=True):
    """en_similarity, but 0 when both names carry direction words and they differ (Matlab Uttar != Matlab South)."""
    (da, ra), (db, rb) = _dir_split(a), _dir_split(b)
    if da and not db:
        db = _letter_dir(b, ra)
    elif db and not da:
        da = _letter_dir(a, rb)
    if da and db:
        # same direction words: compare the rest too ('Uttar Hamchadi' / 'Hamsadi (North)')
        return 0.0 if da != db else max(en_similarity(a, b), en_similarity(ra, rb) if boost and ra and rb else 0.0)
    return en_similarity(a, b)


def _assign(sources, targets, sim, threshold):
    """Greedy one-to-one assignment by descending similarity."""
    pairs = sorted(((sim(s, t), i, j) for i, s in enumerate(sources) for j, t in enumerate(targets)), reverse=True)
    used_s, used_t, out = set(), set(), {}
    for score, i, j in pairs:
        if score < threshold:
            break
        if i in used_s or j in used_t:
            continue
        used_s.add(i); used_t.add(j)
        out[i] = (j, score)
    return out


def _bn_digits(n):
    return str(n).translate(str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯"))


def _slug(s):
    s = s.lower().replace("'", "").replace("&", "and")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


# ------------------------------------------------------------------ admin hierarchy

def apply_admin(rows, add, uniq):
    """Official hierarchy, codes, populations, wards and boundaries, division by division (BBS Census 2022 extracts)."""
    for div in DIVISIONS:
        m = source(div["name"], "bbs_census")
        if m:
            _apply_admin_division(rows, add, uniq, div, m)


# BBS 2022 upazila names that differ from the seed's beyond spelling; each pair checked against the seed's Bangla name
UPAZILA_ALIASES = {
    "Cumilla": {"Adarsha Sadar": "Comilla Sadar",     # seed কুমিল্লা সদর (Cumilla Adarsha Sadar)
                "Sadar Dakkhin": "Sadarsouth"},       # seed সদর দক্ষিণ (Cumilla Sadar Dakshin)
    # seed জিয়ানগর is Indurkani's former name: HDX's 2020 point for upazila 10-79-90 is named Zianagar, and the seed's
    # three Zianagar unions (Balipara, Pattashi, Parerhat) are BBS 2022 Indurkani unions
    "Pirojpur": {"Indurkani": "Zianagar"},
    # seed দক্ষিণ সুনামগঞ্জ is Shantiganj's former name (Dakshin Sunamganj): HDX's 2020 point BD609027 has that name and
    # BBS 2022 Shantiganj (60-90-87) has the seed South Sunamganj's 8 unions
    "Sunamganj": {"Shantiganj": "South Sunamganj"},
}


def _apply_admin_division(rows, add, uniq, div, bbs_manifest):
    BBS = bbs_manifest["key"]
    DIVISION_ID = div["id"]
    bbs_dir = bbs_manifest["_dir"]
    by_id = {r["id"]: r for r in rows}
    kids = defaultdict(list)
    for r in rows:
        kids[r["parent_id"]].append(r)

    bbs_areas = read_csv(os.path.join(bbs_dir, "areas.csv"))
    facts = defaultdict(dict)
    for f in read_csv(os.path.join(bbs_dir, "facts.csv")):
        if f["code"]:
            facts[f["code"]][f["fact"]] = f["value"]

    def official(r, code, note):
        r.update(bbs_code=code, evidence_level="official", evidence_source=BBS, production_eligible=True,
                 verification_notes=note)
        pop = facts.get(code, {}).get("population")
        if pop and pop.isdigit():
            r.update(population_2022=int(pop), population_basis="enumerated", population_source=BBS)

    # districts
    districts = {r["name_en"]: r for r in kids[DIVISION_ID] if r["level"] == "district"}
    bbs_by_level = defaultdict(list)
    for a in bbs_areas:
        bbs_by_level[a["level"]].append(a)
    d_of = {}   # lower-case BBS district name -> seed row (BBS prints "Cox'S Bazar" on its district row)
    districts_lc = {k.lower(): v for k, v in districts.items()}
    for a in bbs_by_level["district"]:
        # district_en carries the seed spelling where BBS prints another ("Netrakona" -> Netrokona); lower-level rows
        # are filtered by district_en too
        dkey = (a.get("district_en") or a["name_en"]).lower()
        d = districts_lc.get(dkey)
        if not d:
            log(f"bbs:{a['code']}", "unmatched", f"BBS district {a['name_en']} not in seed", BBS)
            continue
        d_of[dkey] = d
        official(d, a["code"], f"Matched to BBS Census 2022 district {a['code']}.")
        area = facts.get(a["code"], {}).get("area_km2")
        if area:
            d.update(area_km2=float(area), area_basis="official")
    total = sum(d["population_2022"] or 0 for d in d_of.values() if d.get("population_basis") == "enumerated")
    if len(d_of) == len(districts) and total:
        div_row = by_id[DIVISION_ID]
        div_row.update(population_2022=total, population_basis="enumerated", population_source=BBS)
        log(f"division:{DIVISION_ID}", "population", f"sum of BBS 2022 enumerated district populations = {total}", BBS)

    # upazilas (+ RCC)
    upz_of = {}   # bbs upazila code -> seed row
    for dname, d in d_of.items():
        bbs_up = [a for a in bbs_by_level["upazila"] if a["district_en"].lower() == dname]
        cands = [r for r in kids[d["id"]] if r["level"] == "upazila"]
        alias = UPAZILA_ALIASES.get(d["name_en"], {})
        sim = lambda a, c: 1.0 if upazila_key(c["name_en"]) == upazila_key(a["name_en"]) or alias.get(a["name_en"]) == c["name_en"] \
            else dir_similarity(a["name_en"], c["name_en"])
        for i, (j, _) in _assign(bbs_up, cands, sim, 0.6).items():
            a, u = bbs_up[i], cands[j]
            upz_of[a["code"]] = u
            official(u, a["code"], f"Matched to BBS Census 2022 upazila {a['code']} ({a['name_en']}).")
        for i, a in enumerate(bbs_up):
            if a["code"] not in upz_of:
                log(f"bbs:{a['code']}", "unmatched", f"BBS upazila {a['name_en']} ({dname}) not in seed", BBS)
    # city corporations: matched by name within their district; wards counted from the census
    cc_of = {}   # BBS city corporation code -> seed row
    for a in bbs_by_level["city_corporation"]:
        d = d_of.get(a["district_en"].lower()) or next((x for x in d_of.values() if a["code"].startswith(x.get("bbs_code") or "~")), None)
        cands = [r for r in rows if r["level"] == "city_corporation" and (d is None or r["parent_id"] == d["id"])]
        cc, _ = _best(re.sub(r"\s*city corporation", "", a["name_en"], flags=re.I), cands,
                      key=lambda r: r["name_en"].replace(" City Corporation", ""), threshold=0.8)
        if not cc:
            log(f"bbs:{a['code']}", "unmatched", f"BBS city corporation {a['name_en']} not in seed", BBS)
            continue
        before = cc.get("population_2022")
        cc_of[a["code"]] = cc
        if cc["id"] == 50005:   # Rajshahi: ward count from the RCC এক নজরে page
            official(cc, a["code"], "Matched to BBS Census 2022 city corporation 50-81-66.")
            cc.update(wards_count=30)
            log("city_corporation:50005", "population", f"{before} -> {cc['population_2022']} (BBS 2022 C-01; RCC এক নজরে agrees)", BBS)
            continue
        official(cc, a["code"], f"Matched to BBS Census 2022 city corporation {a['code']}.")
        # "Ward No. 98 (Restricted Area)" (Dhaka North, cantonment) is a census unit, not a city corporation ward
        nums = {re.search(r"(\d+)", w["name_en"]).group(1) for w in bbs_by_level["ward"]
                if w["code"].startswith(a["code"] + "-") and re.search(r"(\d+)", w["name_en"])
                and "restricted" not in w["name_en"].lower()}
        if nums:
            cc.update(wards_count=len(nums))
        log(f"city_corporation:{cc['id']}", "population", f"{before} -> {cc['population_2022']} (BBS 2022)", BBS)

    # Bangla names from official portals: Rajshahi District portal + the other districts' portals
    portal_rows = []
    for pm in sources(div["name"], "district_portal_main") + sources(div["name"], "district_portals"):
        for r in read_csv(os.path.join(pm["_dir"], "areas.csv")):
            r["_src"] = pm["key"]
            portal_rows.append(r)

    def portal_for(level, district_en, upazila_name):
        out = []
        for p in portal_rows:
            if p["level"] != level or p["district_en"] != district_en:
                continue
            if upazila_key(p["upazila_en"] or p["parent_name_en"]) == upazila_key(upazila_name) or \
               difflib.SequenceMatcher(None, upazila_key(p["upazila_en"] or ""), upazila_key(upazila_name)).ratio() > 0.85:
                out.append(p)
        return out

    # unions that moved to a newer upazila (e.g. Madhyanagar, carved out of Dharmapasha): the census lists them under the
    # new upazila, the seed still under the old one. Move a seed union when its old upazila has more seed unions than
    # census unions, the new one fewer, and the names match with the same direction words (Uttar/North ...).
    by_district = defaultdict(list)
    for code, u in sorted(upz_of.items()):
        by_district[u["parent_id"]].append((code, u))
    for _, ups in by_district.items():
        wanting, orphans = [], []
        for code, u in ups:
            bbs_u = [a for a in bbs_by_level["union"] if a["code"].startswith(code + "-")]
            seed_u = [r for r in kids[u["id"]] if r["level"] == "union"]
            m = _assign(bbs_u, seed_u, lambda a, s: dir_similarity(a["name_en"], s["name_en"]), 0.72)
            if len(bbs_u) > len(seed_u):
                wanting += [(u, a) for i, a in enumerate(bbs_u) if i not in m]
            elif len(seed_u) > len(bbs_u):
                orphans += [s for j, s in enumerate(seed_u) if j not in {x[0] for x in m.values()}]
        if not wanting or not orphans:
            continue
        mv = _assign(wanting, orphans, lambda w, s: moved_union_similarity(w[1]["name_en"], s["name_en"]), 0.85)
        for i, (j, sc) in mv.items():
            u, a = wanting[i]
            s = orphans[j]
            old = by_id[s["parent_id"]]
            kids[old["id"]].remove(s)
            s["parent_id"] = u["id"]
            kids[u["id"]].append(s)
            s["path"] = uniq(f"{u['path']}/{s['slug']}")
            s["notes"] = "; ".join(x for x in [s.get("notes"), f"Moved from {old['name_en']} to {u['name_en']}: BBS Census 2022 lists it there ({a['code']})"] if x)
            log(f"area:{s['id']}", "reparented", f"{s['name_en']}: {old['name_en']} -> {u['name_en']} (BBS {a['code']} {a['name_en']}, similarity {sc:.2f})", BBS)

    # unions
    next_union = max(r["id"] for r in rows if r["level"] == "union") + 1
    for code, u in sorted(upz_of.items()):
        bbs_u = sorted((a for a in bbs_by_level["union"] if a["code"].startswith(code + "-")), key=lambda a: a["code"])
        seed_u = sorted((r for r in kids[u["id"]] if r["level"] == "union"), key=lambda r: r["id"])
        match = _assign(bbs_u, seed_u, lambda a, s: dir_similarity(a["name_en"], s["name_en"]), 0.72)
        # leftovers on both sides: pair them by best similarity, accepting weaker matches (same upazila, same count)
        left_b = [i for i in range(len(bbs_u)) if i not in match]
        left_s = [j for j in range(len(seed_u)) if j not in {m[0] for m in match.values()}]
        if left_b and left_s:
            extra = _assign([bbs_u[i] for i in left_b], [seed_u[j] for j in left_s], lambda a, s: dir_similarity(a["name_en"], s["name_en"], boost=False), 0.45)
            for i, (j, sc) in extra.items():
                match[left_b[i]] = (left_s[j], sc)
                log(f"area:{seed_u[left_s[j]]['id']}", "weak_match", f"{seed_u[left_s[j]]['name_en']} = BBS {bbs_u[left_b[i]]['name_en']} (similarity {sc:.2f})", BBS)
            # exactly one left on each side after that: the same union under two spellings (e.g. Khatteshawr = Raninagar)
            left_b = [i for i in range(len(bbs_u)) if i not in match]
            left_s = [j for j in range(len(seed_u)) if j not in {m[0] for m in match.values()}]
            if len(left_b) == 1 and len(left_s) == 1 and dir_similarity(bbs_u[left_b[0]]["name_en"], seed_u[left_s[0]]["name_en"]) > 0:
                match[left_b[0]] = (left_s[0], 0.0)
                log(f"area:{seed_u[left_s[0]]['id']}", "paired_by_count", f"{seed_u[left_s[0]]['name_en']} = BBS {bbs_u[left_b[0]]['name_en']} (only unmatched pair in {u['name_en']})", BBS)
        district_en = by_id[u["parent_id"]]["name_en"]
        portal = portal_for("union", district_en, u["name_en"])
        # official Bangla spelling: pair portal names with seed names by Bangla similarity
        pmatch = _assign(portal, seed_u, lambda p, s: name_similarity(p["name_bn"], None, s["name_bn"], None), 0.6)
        portal_seed = {j: portal[i] for i, (j, _) in pmatch.items()}
        pscore = {j: sc for i, (j, sc) in pmatch.items()}
        for j, s in enumerate(seed_u):
            p = portal_seed.get(j)
            if p and re.search(r"[০-৯0-9]", p["name_bn"] or ""):
                # list serial left in the name ("৫ ধর্মপাল"): drop a leading number, never keep a digit in a name
                p = dict(p, name_bn=re.sub(r"^[০-৯0-9]+[\s.।)]*", "", p["name_bn"]).strip())
                if re.search(r"[০-৯0-9]", p["name_bn"]):
                    p = None
            if p and p["name_bn"] and bn_key(p["name_bn"]) != bn_key(s["name_bn"]) and pscore.get(j, 0) < 0.8:
                # not clearly the same spelling: keep ours, record the portal's for review
                log(f"area:{s['id']}", "name_bn_review", f"seed {s['name_bn']} vs portal {p['name_bn']} (similarity {pscore.get(j, 0):.2f}); not changed", p["_src"])
                p = None
            if p and p["name_bn"] and bn_key(p["name_bn"]) != bn_key(s["name_bn"]):
                log(f"area:{s['id']}", "name_bn", f"{s['name_bn']} -> {p['name_bn']} (official portal spelling)", p["_src"])
                s["notes"] = "; ".join(x for x in [s.get("notes"), f"Bangla name per official portal (was {s['name_bn']})"] if x)
                s["name_bn"] = p["name_bn"]
            if p and p.get("website"):
                s["website"] = p["website"]
        for i, a in enumerate(bbs_u):
            if i in match:
                s = seed_u[match[i][0]]
                official(s, a["code"], f"Matched to BBS Census 2022 union {a['code']} ({a['name_en']}).")
                continue
            # a union in the census that the seed lacks: add it, Bangla name from the one unpaired portal row
            free_portal = [p for k, p in enumerate(portal) if k not in pmatch and not p.get("_used")]
            n_new = sum(1 for k in range(len(bbs_u)) if k not in match)
            bn = free_portal[0]["name_bn"] if len(free_portal) == 1 and n_new == 1 else None
            if bn:
                free_portal[0]["_used"] = True
            r = add(id=next_union, level="union", parent_id=u["id"], name_bn=bn or a["name_en"], name_en=a["name_en"],
                    slug=_slug(a["name_en"]), path=uniq(f"{u['path']}/{_slug(a['name_en'])}"), source_ref=f"bbs:{a['code']}",
                    website=free_portal[0].get("website") if bn else None, verified=False,
                    data_source=BBS, evidence_level="official", evidence_source=BBS,
                    notes="Added from BBS Census 2022" + ("" if bn else "; Bangla name not published by the portals"))
            official(r, a["code"], f"Listed in BBS Census 2022 ({a['code']}) and the official union list.")
            r["_before"] = (False, False)
            kids[u["id"]].append(r)
            log(f"area:{next_union}", "union_added", f"{a['name_en']} / {bn or '—'} in {u['name_en']} ({district_en})", BBS)
            next_union += 1
        for j, s in enumerate(seed_u):
            if j not in {m[0] for m in match.values()}:
                log(f"area:{s['id']}", "union_not_in_bbs", f"{s['name_en']} ({u['name_en']}) has no BBS 2022 counterpart", BBS)

    # pourashavas: match the seed's Rajshahi list, add the rest of the division
    next_paura = max(r["id"] for r in rows if r["level"] == "pourashava") + 1
    paura_of = {}
    seed_paura = [r for r in rows if r["level"] == "pourashava"]
    for a in sorted(bbs_by_level["pourashava"], key=lambda a: a["code"]):
        upcode = "-".join(a["code"].split("-")[:3])
        u = upz_of.get(upcode)
        if not u:
            continue
        district_en = by_id[u["parent_id"]]["name_en"]
        clean = re.sub(r"\s*pourashava|\s*paurashava", "", a["name_en"], flags=re.I).strip()
        cands = [r for r in seed_paura if by_id[r["parent_id"]]["parent_id"] == u["parent_id"]]
        hit, _ = _best(clean, cands, key=lambda r: r["name_en"].replace(" Pourashava", ""), threshold=0.8)
        portal = [p for p in portal_for("pourashava", district_en, u["name_en"])]
        if hit:
            if hit["parent_id"] != u["id"]:
                log(f"area:{hit['id']}", "reparented", f"{hit['name_en']}: parent -> {u['name_en']} (BBS {a['code']})", BBS)
                hit["parent_id"] = u["id"]
            official(hit, a["code"], f"Matched to BBS Census 2022 pourashava {a['code']}.")
            if DIVISION_ID == 10002:
                hit["notes"] = "Rajshahi District portal and BBS 2022 list 14 pourashavas."
            r = hit
        else:
            bn = portal[0]["name_bn"] if len(portal) == 1 else None
            r = add(id=next_paura, level="pourashava", parent_id=u["id"], name_bn=bn or f"{clean} Pourashava",
                    name_en=f"{clean} Pourashava", slug=_slug(clean) + "-pourashava",
                    path=uniq(f"{u['path']}/{_slug(clean)}-pourashava"), source_ref=f"bbs:{a['code']}", verified=False,
                    data_source=BBS, evidence_level="official", evidence_source=BBS,
                    notes="Added from BBS Census 2022" + ("" if bn else "; Bangla name not published by the portals"))
            official(r, a["code"], f"Listed in BBS Census 2022 ({a['code']}).")
            r["_before"] = (False, False)
            log(f"area:{next_paura}", "pourashava_added", f"{r['name_en']} / {bn or '—'} in {u['name_en']}", BBS)
            next_paura += 1
        wards = facts.get(a["code"], {}).get("ward_count") or facts.get(a["code"], {}).get("paura_ward_count")
        if wards and wards.isdigit():
            r["wards_count"] = int(wards)
        paura_of[a["code"]] = r

    # wards of pourashavas and the city corporation
    first_ward = next_ward = max([r["id"] for r in rows if r["level"] == "ward"] + [70000]) + 1
    cc_wards = {}
    for a in sorted(bbs_by_level["ward"], key=lambda a: a["code"]):
        m = re.search(r"(\d+)", a["name_en"])
        if not m:
            continue
        n = int(m.group(1))
        prefix = "-".join(a["code"].split("-")[:4])
        pop = facts.get(a["code"], {}).get("population")
        cc_code = next((c for c in cc_of if a["code"].startswith(c + "-")), None)
        if cc_code:
            cc = cc_of[cc_code]
            if (cc["id"], n) in cc_wards:   # a ward split across two thanas ("Part"): add the parts together
                w = cc_wards[(cc["id"], n)]
                if pop and pop.isdigit():
                    w["population_2022"] = (w["population_2022"] or 0) + int(pop)
                w["notes"] = "Ward split across city thanas in BBS 2022; population is the sum of the parts."
                continue
            parent = cc
        else:
            parent = paura_of.get(prefix)
            if not parent:
                continue
        r = add(id=next_ward, level="ward", parent_id=parent["id"], name_bn=f"ওয়ার্ড নং {_bn_digits(n)}", name_en=f"Ward {n}",
                slug=f"ward-{n}", path=uniq(f"{parent['path']}/ward-{n}"), source_ref=f"bbs:{a['code']}", verified=False,
                data_source=BBS, evidence_level="official", evidence_source=BBS, notes=None)
        official(r, a["code"], f"Listed in BBS Census 2022 ({a['code']}).")
        if "restricted" in a["name_en"].lower():
            r["notes"] = f"BBS 2022 lists '{a['name_en']}': a census unit for the cantonment, not counted among the city corporation's wards."
        r["_before"] = (False, False)
        if parent["level"] == "city_corporation":
            cc_wards[(parent["id"], n)] = r
        next_ward += 1
    ccs = " + ".join(c["name_en"] for c in cc_of.values()) or "no city corporation"
    log("wards" if DIVISION_ID == 10002 else f"wards:{div['name']}", "wards_added",
        f"{next_ward - first_ward} wards (pourashavas + {ccs})", BBS)

    _attach_boundaries(rows, div, cc_of)


def _attach_boundaries(rows, div, cc_of):
    """Union / pourashava / ward polygons (geoBoundaries 2020) and upazila polygons (HDX COD-AB v03) for one division."""
    hm, gm = source(div["name"], "hdx_cod_ab"), source(div["name"], "geoboundaries_adm4")
    if not hm:
        return
    hdx, gb = hm["_dir"], (gm["_dir"] if gm else None)
    # city wards are matched by number inside their city corporation: HDX/geoBoundaries code prefix BD<div><district>
    # Only where a district has one city corporation: Dhaka district's North and South share a prefix, and its 2020
    # ward polygons use the old undivided Dhaka City Corporation numbers, so they are never joined by number.
    by_pre = defaultdict(list)
    for code, cc in cc_of.items():
        by_pre["BD" + "".join(code.split("-")[:2])].append(cc)
    cc_prefix = {pre: ccs[0] for pre, ccs in by_pre.items() if len(ccs) == 1}
    by_id = {r["id"]: r for r in rows}
    xwalk = {}
    for x in read_csv(os.path.join(hdx, "crosswalk.csv")):
        if x["our_id"] and x["source_code"] and x["confidence"] in ("high", "medium"):
            xwalk[x["source_code"]] = int(x["our_id"])
    n = 0
    for path in [os.path.join(hdx, "boundaries.geojson")] + ([os.path.join(gb, "boundaries.geojson")] if gb else []):
        fc = json.load(open(path, encoding="utf-8"))
        for f in fc["features"]:
            p = f["properties"]
            our = xwalk.get(p.get("code"))
            cc = next((c for pre, c in cc_prefix.items() if p.get("code", "").startswith(pre)), None)
            if our is None and p.get("level") == "ward" and cc:
                m = re.search(r"(\d+)", p.get("name_en") or "")
                hit = next((r for r in rows if r["level"] == "ward" and r["name_en"] == f"Ward {int(m.group(1))}"
                            and r["parent_id"] == cc["id"]), None) if m else None
                our = hit["id"] if hit else None
            r = by_id.get(our)
            if r and f.get("geometry") and r["level"] in ("upazila", "union", "pourashava", "ward", "city_corporation"):
                g = f["geometry"]
                r["_boundary"] = g if g["type"] == "MultiPolygon" else {"type": "MultiPolygon", "coordinates": [g["coordinates"]]}
                n += 1
    log("boundaries" if div["id"] == 10002 else f"boundaries:{div['name']}", "attached",
        f"{n} polygons attached (HDX COD-AB v03 upazilas, geoBoundaries 2020 unions/pourashavas/wards)", hm["key"])


# City-thana names that other sources write differently from BBS 2022 (beyond spelling). Lookups are always limited to
# the city corporations of the place's own district, so "Bandar" in Narayanganj still means Narayanganj's Bandar thana.
THANA_ALIASES = {"bandar": "Chattogram Port", "port": "Chattogram Port", "chittagong port": "Chattogram Port",
                 "chittogram port": "Chattogram Port", "chawkbazar": "Chalk Bazar", "chak bazar": "Chalk Bazar",
                 "pachlaish": "Panchlaish"}


def thana_key(name):
    """'Bangshal Thana' / 'Mohammadpur Model Thana' / 'Mohammadpur' -> one key."""
    n = re.sub(r"\s*(model\s+)?(police\s+station|police\s+thana|thana|p\.?s\.?)\s*$", "", name or "", flags=re.I)
    n = THANA_ALIASES.get(n.strip().lower(), n)
    n = re.sub(r"\bindustrial(\s+area)?\b|\bI/A\b", "shilpa elaka", n, flags=re.I)
    for a, b in (("east", "purba"), ("west", "paschim"), ("north", "uttar"), ("south", "dakshin")):
        n = re.sub(rf"\b{a}\b", b, n, flags=re.I)
    return latin_key(n)


# ------------------------------------------------------------------ places

# Sources merged first win on conflicting fields; later ones only fill gaps. Curated pilot places come before all.
PLACE_PRIORITY = ["ugc", "dgme", "doa_monuments", "caab", "railway", "brtc", "metro_police_thanas", "district_police",
                  "range_police", "fscd", "dghs_hris", "banbeis", "dpe_ipemis", "portal_offices", "bdpost", "district_banks",
                  "district_transport", "tourist_spots", "police_hq_2020",
                  # government lists added Nov 2026: local service offices, haat-bazaars, shelters, fuel stations,
                  # transport and tourism lists
                  "local_services", "haat_bazaar", "shelters", "fuel_stations", "transport_tourism",
                  # non-government sources (shown with their own evidence label): organisations' own branch lists,
                  # then encyclopedic, then community datasets
                  "org_branches", "wikidata", "osm", "overture"]   # by source kind (DIVISIONS.md)
PREFIX = {"education": "INST", "health": "INST", "religious": "INST", "tourism": "TOUR", "emergency": "SRV",
          "government": "GOV", "transport": "TRN", "finance": "FIN", "business": "BIZ", "agriculture": "AGR"}
# metropolitan thanas inside Rajshahi City Corporation (RMP); their places belong to the city corporation
RCC_ID = 50005
RCC_THANAS = {latin_key(n) for n in ("Boalia", "Bowalia", "Rajpara", "Rajapara", "Motihar", "Matihar", "Shah Makhdum", "Shah Mokhdum",
                                      "Shah Makdum", "Chandrima", "Airport", "Kashiadanga", "Rajshahi City", "Rajshahi Metropolitan")}
PABA_THANAS = {latin_key(n) for n in ("Belpukur", "Damkura", "Karnahar", "Karnohar", "Katakhali")}   # RMP thanas in Paba upazila
RAJSHAHI_DISTRICT_ID = 20015
DISTRICT_ALIASES = {"bogra": "bogura", "chapainawabganj": "chapainawabganj", "chapainababganj": "chapainawabganj",
                    "nawabganj": "chapainawabganj", "chapai": "chapainawabganj", "jaipurhat": "joypurhat", "joypurhat": "joypurhat",
                    "chitagong": "chatogram", "chittagong": "chatogram", "comilla": "cumila", "jesore": "jasore",
                    "barisal": "barisal", "nilphamary": "nilphamari", "lalmonirhat": "lalmonirhat", "kurigram": "kurigram",
                    "panchagar": "panchagarh", "thakurgao": "thakurgaon", "netrakona": "netrokona", "moulvibazar": "moulvibazar",
                    "maulvibazar": "moulvibazar", "brahmanbaria": "brahmanbaria", "jhalakati": "jhalokathi", "jhalokati": "jhalokathi"}
# attribute keys worth showing (source keys are kept; labels live in apps/web/messages/*.json → PlaceAttr)
ATTR_KEYS = ["eiin", "school_code", "facility_code", "institute_type", "facility_type", "school_type", "education_level",
             "management", "mpo", "for_whom", "area_status", "teachers", "students", "beds", "agency", "ugc_category",
             "protected_monument", "construction_date_as_stated", "head_designation", "postcode", "station_code", "iata", "icao"]
GROUP = {"religious": "tourism"}
# contacts: keep institutional ones only (COLLECTION_FORMAT.md)
# Large community sources merged as a separate, uncommitted seed layer (COLLECTION_FORMAT.md, "Exceptions"): they run
# after every division's committed sources, never change a committed record (a match is only counted as a duplicate),
# and their places are written apart (data/seed/layers/, db/seed/layers/), so the committed seed is the same with or
# without their files.
LAYER_KINDS = {"overture"}
COMMUNITY_KINDS = {"osm", "overture", "org_branches", "wikidata"}    # non-government sources added Nov 2026
# sources added in later batches get source ids after every earlier source, so existing ids never move
SOURCE_BATCH = {**{k: 1 for k in COMMUNITY_KINDS},
                **{k: 2 for k in ("local_services", "haat_bazaar", "shelters", "fuel_stations", "transport_tourism")}}
# SEED_SKIP_KINDS=osm,overture builds without those source kinds (to compare against an earlier seed)
SKIP_KINDS = {k for k in os.environ.get("SEED_SKIP_KINDS", "").split(",") if k}
PERSONAL_MAIL_KINDS = {"dghs_hris"}     # registry mixes office mailboxes with staff gmail
OFFICIAL_MAIL = re.compile(r"@([\w.-]+\.)?(gov\.bd|ac\.bd|edu\.bd|org\.bd|police\.gov\.bd)$", re.I)
BAD_SITE = re.compile(r"facebook\.com|blogspot\.|youtube\.com|google\.com|/edit$|^https?://[^/.]+/?$", re.I)            # a mosque can be listed as a tourist spot by one source and a shrine by another
COMPAT = [{"health.hospital", "health.medical_college_hospital"}]
_UPPER = re.compile(r"^[^a-z]*[A-Z]{3}[^a-z]*$")


def _clean(s):
    s = re.sub(r"\s+", " ", (s or "").strip())
    return re.sub(r"\s+,", ",", s)


def _title(s):
    """'ABDUL GANI COLLEGE' -> 'Abdul Gani College' (registries publish upper case; keep short abbreviations)."""
    if not s or not _UPPER.match(s):
        return s
    return " ".join(w if (len(w) <= 3 and w.isalpha() and w not in ("THE", "AND", "OF")) else w.capitalize() for w in s.split(" "))


def _hash_id(text, used):
    import hashlib
    n = int(hashlib.sha1(text.encode("utf-8")).hexdigest(), 16) % 90_000_000 + 10_000_000
    while n in used:
        n += 1
    used.add(n)
    return n


# words that say what a place is, not which one; compared names keep only the distinctive part
_GEN_EN = re.compile(r"\b(govt|government|gov|model|thana|police station|ps|primary|secondary|high|school|college|madrasa|madrasah|"
                     r"dakhil|alim|fazil|kamil|community|clinic|union|health|complex|upazila|sub|centre|center|hospital|family|"
                     r"welfare|office|the|of|and|no|registered|non|reg|rps|gps|ngps|bank|plc|branch|ltd|limited)\b\.?|\d+", re.I)
_GEN_BN = re.compile(r"সরকারি|সরকারী|বেসরকারি|রেজিঃ|রেজিস্টার্ড|প্রাথমিক|মাধ্যমিক|নিম্ন|উচ্চ|বিদ্যালয়|কলেজ|মাদ্রাসা|দাখিল|আলিম|ফাজিল|"
                     r"কামিল|কমিউনিটি|ক্লিনিক|ইউনিয়ন|স্বাস্থ্য|উপ|কেন্দ্র|কমপ্লেক্স|উপজেলা|হাসপাতাল|পরিবার|কল্যাণ|থানা|মডেল|"
                     r"কার্যালয়|অফিস|ব্যাংক|পিএলসি|শাখা|লিমিটেড|মেডিকেল|নার্সিং|ইনস্টিটিউট|বিশ্ববিদ্যালয়|অধিদপ্তর|এর|নং|[০-৯]+")
ONE_PER_UPAZILA = {"emergency.police_station", "health.upazila_health_complex", "government.uno_office", "emergency.fire_station"}
NO_CONTAINMENT = {"finance", "business"}


_AREA_EN = _AREA_BN = None     # district and upazila names (set by build_places): not distinctive in a place name


_DISTINCT = {}                 # memo for _distinct_en/_distinct_bn; cleared whenever _AREA_EN/_AREA_BN change


def _distinct_en(s):
    k = ("en", s)
    if k not in _DISTINCT:
        t = _GEN_EN.sub(" ", (s or "").replace("&", " and "))
        _DISTINCT[k] = en_key(_AREA_EN.sub(" ", t) if _AREA_EN else t)
    return _DISTINCT[k]


def _distinct_bn(s):
    k = ("bn", s)
    if k not in _DISTINCT:
        t = _GEN_BN.sub("", s or "")
        _DISTINCT[k] = bn_key(_AREA_BN.sub("", t) if _AREA_BN else t)
    return _DISTINCT[k]


def _drop_area_suffix(name):
    """'Rajshahi Govt. College, Rajshahi' -> 'Rajshahi Govt. College' (trailing district/upazila only)."""
    head, _, tail = (name or "").rpartition(",")
    return head if head and _AREA_EN and not _AREA_EN.sub("", tail).strip(" .-") else name


def _place_sim(a, b):
    """Same-place similarity of two place records, on the distinctive part of their names."""
    best = 0.0
    contain = a["category"] not in NO_CONTAINMENT
    if a["name_bn"] and b["name_bn"] and not a.get("_bn_fallback") and not b.get("_bn_fallback"):
        x, y = _distinct_bn(a["name_bn"]), _distinct_bn(b["name_bn"])
        if x and y:
            best = 1.0 if x == y else difflib.SequenceMatcher(None, x, y).ratio()
            if contain and min(len(x), len(y)) >= 6 and (x in y or y in x):
                best = max(best, 0.9)
        elif not x and not y and bn_key(a["name_bn"]) == bn_key(b["name_bn"]) and bn_key(_GEN_BN.sub("", a["name_bn"])):
            best = 1.0             # same "<area> <type>" name, e.g. রাজশাহী কলেজ
        elif not x and not y:
            best = 0.86            # both purely generic ("পবা থানা" / "থানা"); only accepted with the same upazila (see caller)
        elif difflib.SequenceMatcher(None, bn_key(a["name_bn"]), bn_key(b["name_bn"])).ratio() >= 0.93:
            best = 0.9
    if a["name_en"] and b["name_en"]:
        x, y = _distinct_en(a["name_en"]), _distinct_en(b["name_en"])
        if x and y:
            best = max(best, 1.0 if x == y else difflib.SequenceMatcher(None, x, y).ratio() - 0.03)
        else:                     # a name that is only "<district> University of …" / "Rajshahi Govt. College"
            fa, fb = (en_key(re.sub(r"\b(govt|government|gov)\b\.?", " ", _drop_area_suffix(n), flags=re.I))
                      for n in (a["name_en"], b["name_en"]))
            if fa and fb and difflib.SequenceMatcher(None, fa, fb).ratio() >= 0.92:
                best = max(best, 0.9)
    return best


def _compatible(a, b):
    ka, kb = a["_cat"], b["_cat"]
    if ka == kb or "." not in ka or "." not in kb:
        return True
    return any(ka in s and kb in s for s in COMPAT) or (ka.split(".")[0] != kb.split(".")[0])   # tourism vs religious


def build_places(rows, base_places, cat_by_key, district_features):
    """Merge collected places (data/sources/*/places.csv) with the curated pilot places, division by division.

    Returns the full place list (pilot places first, enriched in place). Every merge, skip and coordinate fix is logged.
    Divisions are processed in DIVISIONS order, so a division added later never changes earlier slugs or ids.
    """
    from trust import eligible
    global _AREA_EN, _AREA_BN
    by_id = {r["id"]: r for r in rows}
    unions_by_u = defaultdict(list)
    for r in rows:
        if r["level"] == "union":
            unions_by_u[r["parent_id"]].append(r)
    area_poly = PolygonIndex([{"type": "Feature", "geometry": r["_boundary"], "properties": {"id": r["id"]}}
                              for r in rows if r.get("_boundary") and r["level"] in ("union", "pourashava")])

    def union_from_text(u, text):
        t = re.sub(r"[০-৯0-9]+\s*নং|ইউনিয়ন|পরিষদ|ইউপি|[\s,\-।]", "", text or "")
        if not t or "পৌর" in (text or "") or "ওয়ার্ড" in (text or ""):
            return None
        best, score = None, 0.0
        for un in unions_by_u.get(u["id"], []):
            k = bn_key(un["name_bn"])
            s = 1.0 if k == t else difflib.SequenceMatcher(None, k, t).ratio()
            if s > score:
                best, score = un, s
        return best if score >= 0.85 else None

    # pilot places: give them the same working fields
    out = []
    for p in base_places:
        p.update(union_id=p.get("union_id"), address_bn=p.get("address_bn"), phones=p.get("phones") or [], email=p.get("email"))
        p["_cat"] = f"{p['category']}.{p['subcategory']}"
        p["_srcs"] = [p["source"]]
        p["_bn_fallback"] = False
        out.append(p)
    slugs = {p["slug"] for p in out}
    used_ids = {int(p["public_id"].split("-")[1]) for p in out}
    index = defaultdict(list)      # (district_id, group) -> places, in insertion order
    gorder = {}                    # group -> creation order (the order the candidate scan used before the grid)
    cells = defaultdict(list)      # (group, cell_y, cell_x) -> places with a point
    nocoord = defaultdict(lambda: defaultdict(list))   # group -> (upazila_id, city_corporation_id) -> places without a point
    by_bn = defaultdict(list)      # (district_id, bn_key of name_bn) -> places (tourism: exact-name matches across groups)
    seq = iter(range(10 ** 9))
    CELL = 0.025                   # degrees: more than 2 km on both axes in Bangladesh, the largest merge distance

    def _cellof(lat, lon):
        return int(math.floor(lat / CELL)), int(math.floor(lon / CELL))

    def _group(key):
        gorder.setdefault(key, len(gorder))
        return index[key]

    def _area(p):
        return p.get("upazila_id"), p.get("city_corporation_id")

    def _index_point(p):
        if p.get("lat") is not None:
            cells[(p["_gkey"], *_cellof(p["lat"], p["lon"]))].append(p)
        else:
            p["_area"] = _area(p)
            nocoord[p["_gkey"]][p["_area"]].append(p)

    def _index_name(p):
        p["_bnk"] = bn_key(p["name_bn"]) if p.get("name_bn") else None
        if p["_bnk"]:
            by_bn[(p["_gkey"][0], p["_bnk"])].append(p)

    def register(p, key):
        _group(key).append(p)
        p["_gkey"], p["_g"], p["_seq"] = key, gorder[key], next(seq)
        _index_point(p)
        _index_name(p)

    def reindex(p, had_point, old_bnk):
        """After a merge filled a point or a Bangla name, keep the grid and the name index current."""
        if not had_point and (p.get("lat") is not None or _area(p) != p["_area"]):
            nocoord[p["_gkey"]][p["_area"]].remove(p)
            _index_point(p)
        if p.get("name_bn") and bn_key(p["name_bn"]) != old_bnk:
            if old_bnk:
                by_bn[(p["_gkey"][0], old_bnk)].remove(p)
            _index_name(p)

    for p in out:
        register(p, (p["district_id"], GROUP.get(p["category"], p["category"])))
    order = {k: i for i, k in enumerate(PLACE_PRIORITY)}
    stats = {}

    for phase in ("base", "layer"):
        for div in DIVISIONS:
            DIVISION_ID = div["id"]
            srcs = sorted((m for m in _manifests() if division_of(m) == div["name"] and place_files(m)
                           and kind_of(m) not in SKIP_KINDS and (kind_of(m) in LAYER_KINDS) == (phase == "layer")),
                          key=lambda m: (order.get(kind_of(m), 999), m["key"]))
            if not srcs:
                continue
            names = [r for r in rows if r["level"] in ("district", "upazila") and (r["id"] == DIVISION_ID or
                     r["parent_id"] == DIVISION_ID or by_id.get(r["parent_id"], {}).get("parent_id") == DIVISION_ID)]
            en_words = sorted({w.lower() for r in names for w in [r["name_en"], r.get("_src_en") or ""] if w} |
                              {"bogra", "nawabganj", "chapai", "sadar", "city"}, key=len, reverse=True)
            _AREA_EN = re.compile(r"\b(" + "|".join(re.escape(w) for w in en_words) + r")\b", re.I)
            bn_words = sorted({r["name_bn"] for r in names if r["name_bn"]} | {"সদর", "সিটি", "বগুড়া", "চাঁপাই"},
                              key=len, reverse=True)
            _AREA_BN = re.compile("|".join(re.escape(w) for w in bn_words))
            _DISTINCT.clear()
            districts = {latin_key(r["name_en"]): r for r in rows if r["level"] == "district" and r["parent_id"] == DIVISION_ID}
            upz_by_d = defaultdict(list)
            for r in rows:
                if r["level"] == "upazila" and r["parent_id"] in {d["id"] for d in districts.values()}:
                    upz_by_d[r["parent_id"]].append(r)
            dist_poly = PolygonIndex([f for f in district_features if f["properties"].get("division_id") == DIVISION_ID])
            # city corporations by district, and metro-police thana names that belong to them (Rajshahi: fixed tables)
            cc_by_d = defaultdict(list)
            for r in rows:
                if r["level"] == "city_corporation" and r["parent_id"] in {d["id"] for d in districts.values()}:
                    cc_by_d[r["parent_id"]].append(r)
            # census thanas inside a city corporation (BBS code <div>-<district>-<cc>-<thana>); a thana listed under two
            # city corporations (Dhanmondi, Ramna, Sher-e-Bangla Nagar in Dhaka) is not assigned to either
            cc_by_code = {r["bbs_code"]: r["id"] for r in rows if r["level"] == "city_corporation" and r.get("bbs_code")}
            thana_cc = defaultdict(set)
            bm = source(div["name"], "bbs_census")
            if bm:
                for a in read_csv(os.path.join(bm["_dir"], "areas.csv")):
                    cc_id = cc_by_code.get("-".join(a["code"].split("-")[:3])) if a["level"] == "thana" else None
                    if cc_id:
                        thana_cc[thana_key(a["name_en"])].add(cc_id)
            metro_thanas = set()
            for mm in sources(div["name"], "metro_police_thanas"):
                metro_thanas |= {latin_key(x["upazila_en"]) for x in read_csv(os.path.join(mm["_dir"], "places.csv")) if x.get("upazila_en")}

            def district_of(name):
                k = latin_key(name or "")
                k = DISTRICT_ALIASES.get(k, k)
                if k in districts:
                    return districts[k]
                best = max(districts.values(), key=lambda d: en_similarity(name, d["name_en"]), default=None)
                return best if best and en_similarity(name, best["name_en"]) >= 0.8 else None

            def upazila_of(d, name):
                if not name:
                    return None
                k = upazila_key(name)
                cands = upz_by_d[d["id"]]
                for u in cands:
                    if upazila_key(u["name_en"]) == k or upazila_key(u.get("_src_en") or "") == k:
                        return u
                scored = sorted(((en_similarity(name, u["name_en"]), u["id"], u) for u in cands), reverse=True)
                return scored[0][2] if scored and scored[0][0] >= 0.8 else None

            for m in srcs:
                key, trust, kind = m["key"], int(m.get("trust_level") or 1), kind_of(m)
                personal_mail = kind_of(m) in PERSONAL_MAIL_KINDS
                st = stats.setdefault(key, dict(source=key, trust=trust, rows=0, added=0, merged=0, skipped=0, with_point=0,
                                                point_dropped=0, union_resolved=0, upazila_resolved=0))
                for r in (r for f in place_files(m) for r in read_csv(f)):
                    st["rows"] += 1
                    extra = {}
                    if r.get("extra_json"):
                        try:
                            extra = json.loads(r["extra_json"])
                        except ValueError:
                            extra = {}
                    rid = f"{key}:{r.get('source_id')}"
                    if extra.get("office_post"):                       # FSCD staff posts, not places
                        st["skipped"] += 1
                        continue
                    cat = r.get("category_key") or ""
                    if cat not in cat_by_key:
                        cat = cat.split(".")[0]
                    if cat not in cat_by_key:
                        st["skipped"] += 1
                        log(rid, "place_skipped", f"category {r.get('category_key')!r} not in taxonomy", key)
                        continue
                    top = cat.split(".")[0]
                    name_en, name_bn = _title(_clean(r.get("name_en"))), _clean(r.get("name_bn"))
                    if not (name_en or name_bn):
                        st["skipped"] += 1
                        continue
                    d = district_of(r.get("district_en"))
                    if not d:
                        st["skipped"] += 1
                        log(rid, "place_skipped", f"district {r.get('district_en')!r} not in {div['name'].title()} Division", key)
                        continue
                    lat = float(r["lat"]) if r.get("lat") else None
                    lon = float(r["lon"]) if r.get("lon") else None
                    upz, union_id, cc = None, None, None
                    thana = latin_key(r.get("upazila_en") or "")
                    if thana in RCC_THANAS and d["id"] == RAJSHAHI_DISTRICT_ID:
                        cc = RCC_ID
                    elif thana in PABA_THANAS and d["id"] == RAJSHAHI_DISTRICT_ID:
                        upz = upazila_of(d, "Paba")
                    elif r.get("upazila_en"):
                        multi_cc = len(cc_by_d[d["id"]]) > 1
                        tk0 = thana_key(r["upazila_en"])
                        if tk0 not in thana_cc and cc_by_d[d["id"]]:   # spelling variant of a census city thana (Bakolia/Bakalia)
                            own_keys = [k for k in thana_cc if thana_cc[k] & {c["id"] for c in cc_by_d[d["id"]]}]
                            close = [k for k in own_keys if en_similarity(tk0, k) >= 0.85]
                            tk0 = close[0] if len(close) == 1 else tk0
                        exact_thana = tk0 in thana_cc and not any(
                            upazila_key(u["name_en"]) == upazila_key(r["upazila_en"]) for u in upz_by_d[d["id"]])
                        # a census city thana (Demra, Bakalia) must not fall to a similar-looking upazila (Dhamrai, Boalkhali)
                        upz = None if exact_thana else upazila_of(d, r["upazila_en"])
                        if exact_thana and not multi_cc:
                            own = thana_cc[tk0] & {c["id"] for c in cc_by_d[d["id"]]}
                            cc = next(iter(own)) if len(own) == 1 else None
                        # a metro-police thana that is not an upazila: the district's only city corporation
                        if not upz and DIVISION_ID != 10002 and thana in metro_thanas and len(cc_by_d[d["id"]]) == 1 \
                                and not (any(cc_by_d[d["id"]][0]["id"] in v for v in thana_cc.values()) and not exact_thana):
                            # the district's only city corporation, unless the census lists that city corporation's thanas
                            # and this one is not among them (Khulna's Aranghata, Harintana, Labanchara)
                            cc = cc_by_d[d["id"]][0]["id"]
                        elif not upz and len(cc_by_d[d["id"]]) > 1:
                            tk = thana_key(r["upazila_en"])
                            if tk not in thana_cc:   # spelling variants (Adabor/Adabar, Hazaribag/Hazaribagh): one close match only
                                close = [k for k in thana_cc if en_similarity(tk, k) >= 0.85]
                                tk = close[0] if len(close) == 1 else tk
                            hit_cc = thana_cc.get(tk, set()) & {c["id"] for c in cc_by_d[d["id"]]}
                            if len(hit_cc) != 1 and extra.get("city_corporation"):   # the registry's own city-corporation field
                                named = [c for c in cc_by_d[d["id"]] if en_similarity(re.sub(r"(?i)\s*city\s*corp\w*", "", extra["city_corporation"]),
                                                                                       c["name_en"].replace(" City Corporation", "")) >= 0.85]
                                hit_cc = {named[0]["id"]} if len(named) == 1 else hit_cc
                            if len(hit_cc) == 1:
                                cc = next(iter(hit_cc))
                    if lat is not None:
                        hit = dist_poly.find(lon, lat)
                        if not hit or hit[0]["properties"].get("district_id") != d["id"]:
                            log(rid, "place_point_dropped", f"{lat},{lon} is not inside {d['name_en']} district", key)
                            st["point_dropped"] += 1
                            lat = lon = None
                        else:
                            st["with_point"] += 1
                            for f in area_poly.find(lon, lat):
                                a = by_id[f["properties"]["id"]]
                                pu = by_id.get(a["parent_id"])
                                if cc is None and pu and pu["level"] == "upazila" and pu["parent_id"] == d["id"]:
                                    upz = pu
                                    union_id = a["id"] if a["level"] == "union" else None
                                break
                    if cc is None and upz is None and kind in COMMUNITY_KINDS and extra.get("city_corporation"):
                        # the collector placed the point inside a city-corporation polygon (no upazila there)
                        named = [c for c in cc_by_d[d["id"]] if en_similarity(re.sub(r"(?i)\s*city\s*corp\w*", "", extra["city_corporation"]),
                                                                               c["name_en"].replace(" City Corporation", "")) >= 0.85]
                        cc = named[0]["id"] if len(named) == 1 else None
                    if upz and not union_id:
                        un = union_from_text(upz, extra.get("union_or_ward_bn") or (name_bn if cat == "government.union_parishad" else ""))
                        union_id = un["id"] if un else None
                    st["upazila_resolved"] += bool(upz or cc)
                    st["union_resolved"] += bool(union_id)
                    phones = []
                    for ph in re.split(r"[;,/]| or ", r.get("phone") or ""):
                        ph = re.sub(r"[^\d+\-]", "", ph.strip())
                        digits = re.sub(r"\D", "", ph)
                        if len(set(digits[-8:])) <= 1:     # placeholder such as 01700000000 / 01111111111 / 000000
                            if digits:
                                log(rid, "phone_dropped", f"{ph!r} looks like a placeholder", key)
                            continue
                        if len(digits) >= 5 and ph not in phones:
                            phones.append(ph)
                    email = (re.split(r"[;,\s]+", r.get("email") or "") or [""])[0] or None
                    if email and (personal_mail and not OFFICIAL_MAIL.search(email) or "@" not in email):
                        email = None          # e.g. a health worker's own gmail: not an institutional contact
                    website = r.get("website") if (r.get("website") or "").startswith("http") else None
                    if website and BAD_SITE.search(website):
                        website = None
                    addr = _clean(r.get("address"))
                    own = (r.get("ownership") or "").lower()
                    ownership = "public" if own in ("public", "government", "govt") else "private" if own in ("private", "non_government") \
                        else own if own in ("ngo", "trust", "autonomous") else None
                    attrs = {k: extra[k] for k in ATTR_KEYS if isinstance(extra.get(k), (str, int, float, bool)) and extra.get(k) != ""}
                    est = extra.get("year_of_establishment") or extra.get("established")
                    rec = dict(name_en=name_en or None, name_bn=name_bn or name_en, _bn_fallback=not name_bn, short_name=None,
                               category=top, _cat=cat, category_id=cat_by_key[top]["id"],
                               subcategory_id=cat_by_key[cat]["id"] if "." in cat else None, ownership=ownership,
                               division_id=DIVISION_ID, district_id=d["id"], upazila_id=upz["id"] if upz else None, union_id=union_id,
                               city_corporation_id=cc, address_bn=addr if re.search(r"[ঀ-৿]", addr) else None,
                               address_en=addr if addr and not re.search(r"[ঀ-৿]", addr) else None,
                               postcode=str(extra.get("postcode") or "") or None, lat=lat, lon=lon, phones=phones, email=email,
                               website=website, established=str(est) if est else None, attributes=attrs,
                               source=key, source_url=r.get("source_url") or _url(key), notes=_clean(r.get("notes")) or None,
                               _srcs=[key], _rid=rid)
                    rec["evidence_level"] = evidence_for(trust, bool(r.get("source_url")))
                    # merge with an earlier record of the same place from another source
                    gkey = (d["id"], GROUP.get(top, top))
                    group = _group(gkey)
                    best, score = None, 0.0
                    # a portal's tourist spot can be a college, office or mosque listed elsewhere: exact names only
                    others = sorted((p for p in by_bn.get((d["id"], bn_key(rec["name_bn"])), ()) if p["_gkey"] != gkey),
                                    key=lambda p: (p["_g"], p["_seq"])) if top == "tourism" and not rec["_bn_fallback"] else []
                    if rec["lat"] is not None:    # places with a point more than 2 km away can never match: skip them
                        cy, cx = _cellof(rec["lat"], rec["lon"])
                        # places without a point: those in another upazila / city corporation are skipped below anyway
                        nc = nocoord.get(gkey, {})
                        ra = (rec["upazila_id"], rec["city_corporation_id"])
                        near = (nc.get(ra, []) + nc.get((None, None), [])) if ra != (None, None) else \
                            [p for ps in nc.values() for p in ps]
                        cand = sorted(near + [p for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                                              for p in cells.get((gkey, cy + dy, cx + dx), ())],
                                      key=lambda p: p["_seq"])
                    else:
                        cand = group
                    for p in cand + others:
                        if key in p["_srcs"] or not _compatible(p, rec):
                            continue
                        if (p.get("upazila_id") or p.get("city_corporation_id")) and (rec["upazila_id"] or rec["city_corporation_id"]) and \
                                (p.get("upazila_id"), p.get("city_corporation_id")) != (rec["upazila_id"], rec["city_corporation_id"]):
                            continue
                        same_area = bool(rec["upazila_id"] and p.get("upazila_id") == rec["upazila_id"])
                        if p.get("lat") is not None and rec["lat"] is not None and haversine_m(p["lat"], p["lon"], rec["lat"], rec["lon"]) > 2000:
                            continue
                        s = _place_sim(p, rec)
                        if s == 0.86 and not same_area:
                            s = 0.0
                        # one-per-upazila services named only generically by one source ("উপজেলা স্বাস্থ্য কমপ্লেক্স")
                        # police: one record per thana, names differ by script across sources
                        if top == "emergency" and cat == p["_cat"] == "emergency.police_station" and s < 0.85:
                            pt, rt = p.get("_thana"), thana
                            if pt and rt and en_similarity(pt, rt) >= 0.9 and (not p.get("name_en") or not rec["name_en"] or s >= 0.6):
                                s = 0.86
                        if p in others:
                            s = 1.0 if p.get("lat") is None or rec["lat"] is None or haversine_m(p["lat"], p["lon"], rec["lat"], rec["lon"]) < 2000 else 0.0
                        if s > score:
                            best, score = p, s
                    rec["_thana"] = thana if cat == "emergency.police_station" else None
                    if best and score >= 0.85:
                        if phase == "layer":      # never change a committed record: count the duplicate only
                            st["merged"] += 1
                            log(best["slug"], "layer_duplicate", f"{rid} ({score:.2f})", key)
                            continue
                        had_point, old_bnk = best.get("lat") is not None, best.get("_bnk")
                        _merge(best, rec)
                        reindex(best, had_point, old_bnk)
                        st["merged"] += 1
                        log(best["slug"], "place_merged", f"{rid} ({score:.2f})", key)
                        continue
                    pid = _hash_id(rid, used_ids)
                    base = _slug(name_en or romanize_bn(name_bn))[:80].strip("-") or _slug(cat_by_key[cat]["name_en"])
                    where = _slug((upz or {}).get("name_en") or
                                  (_slug(by_id[cc]["name_en"].replace(" City Corporation", "")) + "-city" if cc else d["name_en"]))
                    slug = f"{base}-{where}" if where and not base.endswith(where) else base
                    slug_, n = slug, 2
                    while slug_ in slugs:
                        slug_, n = f"{slug}-{n}", n + 1
                    slugs.add(slug_)
                    rec.update(public_id=f"{PREFIX.get(top, 'PLC')}-{pid:08d}", slug=slug_)
                    out.append(rec)
                    if phase == "layer":
                        rec["_layer"] = kind
                    else:
                        register(rec, gkey)
                    st["added"] += 1

    _place_in_new_upazilas(out, rows)

    # finalise evidence, flags and provenance
    for p in out:
        # evidence_source: the source that confirms the record; source: where its details came from (may differ for pilots)
        src = p.get("evidence_source") or p["source"]
        p["evidence_source"] = src if p["evidence_level"] in ("official", "secondary") else None
        p["production_eligible"] = eligible(p["evidence_level"], p["evidence_source"])
        p["verification_status"] = p.get("verification_status") or "unverified"
        p["verified"] = False
        if len(p["_srcs"]) > 1:
            p["attributes"] = dict(p.get("attributes") or {}, _sources=p["_srcs"])
        if p.get("_bn_fallback"):
            p["attributes"] = dict(p.get("attributes") or {}, _name_bn_missing=True)
    return out, list(stats.values())


RANK = {"official": 3, "secondary": 2, "community": 1, "unverified": 0}

# Upazilas created after most national lists were compiled (Lalmai 2017, Karnaphuli 2016, Guimara 2014, Eidgaon 2021,
# Madhyanagar 2022, Dasar 2021): those lists still file their facilities under the parent upazila. (Zianagar is
# Indurkani's former name, not a new upazila, and has no such records.)
NEW_UPAZILAS = {("Cumilla", "Lalmai"), ("Chattogram", "Karnafuli"), ("Khagrachhari", "Guimara"), ("Cox's Bazar", "Eidgaon"),
                ("Sunamganj", "Madhyanagar"), ("Madaripur", "Dasar")}
NEW_UPAZILA_INSET_M = 300     # the point must lie this far inside the new upazila's boundary (boundary sets are approximate)


def _edge_distance_m(lon, lat, geom):
    """Shortest distance in metres from a point to the edges of a (Multi)Polygon (local equirectangular projection)."""
    kx, ky = 111_320 * math.cos(math.radians(lat)), 110_574
    best = float("inf")
    for poly in _polys(geom):
        for ring in poly:
            for (x1, y1, *_), (x2, y2, *_) in zip(ring, ring[1:]):
                ax, ay, bx, by = (x1 - lon) * kx, (y1 - lat) * ky, (x2 - lon) * kx, (y2 - lat) * ky
                dx, dy = bx - ax, by - ay
                t = max(0.0, min(1.0, -(ax * dx + ay * dy) / ((dx * dx + dy * dy) or 1e-12)))
                best = min(best, math.hypot(ax + t * dx, ay + t * dy))
    return best


def _place_in_new_upazilas(places, rows):
    """File a place under a new upazila when its point lies well inside that upazila's boundary and outside the
    upazila it is filed under. Places inside a city corporation and places without a point are left alone. Every
    move is logged (qa/collected_changes.csv); its union becomes the new upazila's union that holds the point, if any."""
    by_id = {r["id"]: r for r in rows}
    targets = [r for r in rows if r["level"] == "upazila" and r.get("_boundary")
               and (by_id[r["parent_id"]]["name_en"], r["name_en"]) in NEW_UPAZILAS]
    missing = NEW_UPAZILAS - {(by_id[r["parent_id"]]["name_en"], r["name_en"]) for r in targets}
    assert not missing, f"new upazilas without a boundary: {missing}"
    new_idx = PolygonIndex([{"type": "Feature", "geometry": r["_boundary"], "properties": {"id": r["id"]}} for r in targets])
    target_ids = {r["id"] for r in targets}
    union_idx = PolygonIndex([{"type": "Feature", "geometry": r["_boundary"], "properties": {"id": r["id"]}}
                              for r in rows if r["level"] == "union" and r.get("_boundary") and r["parent_id"] in target_ids])
    moved = 0
    for p in places:
        if p.get("lat") is None or p.get("city_corporation_id"):
            continue
        hit = new_idx.find(p["lon"], p["lat"])
        if not hit:
            continue
        b = by_id[hit[0]["properties"]["id"]]
        if p.get("upazila_id") == b["id"] or p.get("district_id") != b["parent_id"]:
            continue
        cur = by_id.get(p.get("upazila_id"))
        if cur and cur.get("_boundary") and PolygonIndex([{"type": "Feature", "geometry": cur["_boundary"], "properties": {}}]).find(p["lon"], p["lat"]):
            continue
        if _edge_distance_m(p["lon"], p["lat"], b["_boundary"]) < NEW_UPAZILA_INSET_M:
            continue
        un = union_idx.find(p["lon"], p["lat"])
        if not p.get("_layer"):     # the uncommitted layer is not logged: the committed QA files must not depend on it
            log(p["slug"], "upazila_by_point",
                f"{cur['name_en'] if cur else 'no upazila'} -> {b['name_en']} (point {NEW_UPAZILA_INSET_M}+ m inside its boundary)",
                p.get("source") or "")
            moved += 1
        p["upazila_id"] = b["id"]
        p["union_id"] = un[0]["properties"]["id"] if un else None
    log("new_upazilas", "upazila_by_point_total", f"{moved} committed places", "")


def _merge(p, rec):
    """Fill gaps in `p` from `rec`; upgrade evidence when `rec` comes from a stronger source."""
    p["_srcs"].append(rec["source"])
    if p.get("_bn_fallback") and not rec["_bn_fallback"]:
        p["name_bn"], p["_bn_fallback"] = rec["name_bn"], False
    for k in ("name_en", "address_bn", "address_en", "postcode", "email", "website", "established", "ownership",
              "upazila_id", "union_id", "city_corporation_id"):
        if not p.get(k) and rec.get(k):
            p[k] = rec[k]
    if p.get("lat") is None and rec["lat"] is not None:
        p["lat"], p["lon"] = rec["lat"], rec["lon"]
    for ph in rec["phones"]:
        if ph not in p["phones"]:
            p["phones"].append(ph)
    if "." not in p["_cat"] and "." in rec["_cat"]:
        p["_cat"], p["subcategory_id"] = rec["_cat"], rec["subcategory_id"]
    p["attributes"] = dict(rec["attributes"], **(p.get("attributes") or {}))
    if RANK[rec["evidence_level"]] > RANK[p["evidence_level"]]:
        log(p["slug"], "place_evidence", f"{p['evidence_level']} -> {rec['evidence_level']} via {rec['_rid']}", rec["source"])
        p["evidence_level"], p["evidence_source"] = rec["evidence_level"], rec["source"]
        if p["source"] in ("UNVERIFIED", None):     # nothing of the pilot record's own to credit
            p["source"], p["source_url"] = rec["source"], rec["source_url"]
        if p.get("verification_status") == "verified" and rec["evidence_level"] != "official":
            p["verification_status"] = "unverified"
