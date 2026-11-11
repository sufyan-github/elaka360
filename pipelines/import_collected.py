"""Merge collected official sources (data/sources/*/, see COLLECTION_FORMAT.md) into the seed.

Scope today: Rajshahi Division. Called from build_seed.py:
  register_sources(SRC, SOURCE_META)          before source ids are assigned
  apply_admin(rows, add, uniq)                after the base hierarchy is built
  build_places(rows, base_places, cat_by_key) for points of interest

Rules (docs/data/DATA_TRUST_POLICY.md): evidence comes from the source's trust level; nothing is invented;
every change is recorded in `changes` (written to data/seed/qa/collected_changes.csv).
"""
import difflib, json, os, re
from collections import defaultdict
from collected import (PolygonIndex, SOURCES, bn_key, check_manifest, en_key, en_similarity, evidence_for, haversine_m,
                       manifests, name_similarity, read_csv, romanize_bn)
from reconcile import latin_key, upazila_key
from trust import nfc

DIVISION_ID = 10002
BBS = "BBS_CENSUS_2022"
changes = []           # dicts: record, change, detail, source
problems = []          # manifest problems (reported by validate_seed.py)

_MANIFESTS = None


def _manifests():
    global _MANIFESTS
    if _MANIFESTS is None:
        _MANIFESTS = [m for m in manifests() if m["key"] not in ("NUHIL",)]
    return _MANIFESTS


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
    """Add every collected source to the data_sources registry (deterministic: sorted by folder)."""
    for m in _manifests():
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
    """Official hierarchy, codes, populations, wards and boundaries for Rajshahi Division."""
    bbs_dir = _dir(BBS)
    if not bbs_dir:
        return
    by_id = {r["id"]: r for r in rows}
    kids = defaultdict(list)
    for r in rows:
        kids[r["parent_id"]].append(r)

    bbs_areas = read_csv(os.path.join(bbs_dir, "areas.csv"))
    facts = defaultdict(dict)
    for f in read_csv(os.path.join(bbs_dir, "facts.csv")):
        if f["code"]:
            facts[f["code"]][f["fact"]] = f["value"]
    bbs_url = _url(BBS)

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
    d_of = {}
    for a in bbs_by_level["district"]:
        d = districts.get(a["name_en"])
        if not d:
            log(f"bbs:{a['code']}", "unmatched", f"BBS district {a['name_en']} not in seed", BBS)
            continue
        d_of[a["name_en"]] = d
        official(d, a["code"], f"Matched to BBS Census 2022 district {a['code']}.")
        area = facts.get(a["code"], {}).get("area_km2")
        if area:
            d.update(area_km2=float(area), area_basis="official")
    div = by_id[DIVISION_ID]
    total = sum(d["population_2022"] or 0 for d in d_of.values() if d.get("population_basis") == "enumerated")
    if len(d_of) == 8 and total:
        div.update(population_2022=total, population_basis="enumerated", population_source=BBS)
        log("division:10002", "population", f"sum of BBS 2022 enumerated district populations = {total}", BBS)

    # upazilas (+ RCC)
    upz_of = {}   # bbs upazila code -> seed row
    for dname, d in d_of.items():
        bbs_up = [a for a in bbs_by_level["upazila"] if a["district_en"] == dname]
        cands = [r for r in kids[d["id"]] if r["level"] == "upazila"]
        sim = lambda a, c: 1.0 if upazila_key(c["name_en"]) == upazila_key(a["name_en"]) else en_similarity(a["name_en"], c["name_en"])
        for i, (j, _) in _assign(bbs_up, cands, sim, 0.6).items():
            a, u = bbs_up[i], cands[j]
            upz_of[a["code"]] = u
            official(u, a["code"], f"Matched to BBS Census 2022 upazila {a['code']} ({a['name_en']}).")
        for i, a in enumerate(bbs_up):
            if a["code"] not in upz_of:
                log(f"bbs:{a['code']}", "unmatched", f"BBS upazila {a['name_en']} ({dname}) not in seed", BBS)
    rcc = next((r for r in rows if r["level"] == "city_corporation" and r["name_en"] == "Rajshahi City Corporation"), None)
    for a in bbs_by_level["city_corporation"]:
        if rcc and a["name_en"] == "Rajshahi City Corporation":
            before = rcc.get("population_2022")
            official(rcc, a["code"], "Matched to BBS Census 2022 city corporation 50-81-66.")
            rcc.update(wards_count=30)
            log("city_corporation:50005", "population", f"{before} -> {rcc['population_2022']} (BBS 2022 C-01; RCC এক নজরে agrees)", BBS)

    # Bangla names from official portals: Rajshahi District portal + the other districts' portals
    portal_rows = []
    for key, fn in (("RAJSHAHI_DC_PORTAL_2026", "areas.csv"), ("RAJDIV_DISTRICT_PORTALS_2026", "areas.csv")):
        d = _dir(key)
        if d:
            for r in read_csv(os.path.join(d, fn)):
                r["_src"] = key
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

    # unions
    next_union = max(r["id"] for r in rows if r["level"] == "union") + 1
    for code, u in sorted(upz_of.items()):
        bbs_u = sorted((a for a in bbs_by_level["union"] if a["code"].startswith(code + "-")), key=lambda a: a["code"])
        seed_u = sorted((r for r in kids[u["id"]] if r["level"] == "union"), key=lambda r: r["id"])
        match = _assign(bbs_u, seed_u, lambda a, s: en_similarity(a["name_en"], s["name_en"]), 0.72)
        # leftovers on both sides: pair them by best similarity, accepting weaker matches (same upazila, same count)
        left_b = [i for i in range(len(bbs_u)) if i not in match]
        left_s = [j for j in range(len(seed_u)) if j not in {m[0] for m in match.values()}]
        if left_b and left_s:
            extra = _assign([bbs_u[i] for i in left_b], [seed_u[j] for j in left_s], lambda a, s: en_similarity(a["name_en"], s["name_en"]), 0.45)
            for i, (j, sc) in extra.items():
                match[left_b[i]] = (left_s[j], sc)
                log(f"area:{seed_u[left_s[j]]['id']}", "weak_match", f"{seed_u[left_s[j]]['name_en']} = BBS {bbs_u[left_b[i]]['name_en']} (similarity {sc:.2f})", BBS)
            # exactly one left on each side after that: the same union under two spellings (e.g. Khatteshawr = Raninagar)
            left_b = [i for i in range(len(bbs_u)) if i not in match]
            left_s = [j for j in range(len(seed_u)) if j not in {m[0] for m in match.values()}]
            if len(left_b) == 1 and len(left_s) == 1:
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
    next_ward = 70001
    rcc_wards = {}
    for a in sorted(bbs_by_level["ward"], key=lambda a: a["code"]):
        m = re.search(r"(\d+)", a["name_en"])
        if not m:
            continue
        n = int(m.group(1))
        prefix = "-".join(a["code"].split("-")[:4])
        pop = facts.get(a["code"], {}).get("population")
        if a["code"].startswith("50-81-66") and rcc:
            if n in rcc_wards:   # a ward split across two thanas ("Part"): add the parts together
                w = rcc_wards[n]
                if pop and pop.isdigit():
                    w["population_2022"] = (w["population_2022"] or 0) + int(pop)
                w["notes"] = "Ward split across city thanas in BBS 2022; population is the sum of the parts."
                continue
            parent = rcc
        else:
            parent = paura_of.get(prefix)
            if not parent:
                continue
        r = add(id=next_ward, level="ward", parent_id=parent["id"], name_bn=f"ওয়ার্ড নং {_bn_digits(n)}", name_en=f"Ward {n}",
                slug=f"ward-{n}", path=uniq(f"{parent['path']}/ward-{n}"), source_ref=f"bbs:{a['code']}", verified=False,
                data_source=BBS, evidence_level="official", evidence_source=BBS, notes=None)
        official(r, a["code"], f"Listed in BBS Census 2022 ({a['code']}).")
        r["_before"] = (False, False)
        if parent is rcc:
            rcc_wards[n] = r
        next_ward += 1
    log("wards", "wards_added", f"{next_ward - 70001} wards (pourashavas + Rajshahi City Corporation)", BBS)

    _attach_boundaries(rows)


def _attach_boundaries(rows):
    """Union / pourashava / ward polygons (geoBoundaries 2020) and upazila polygons (HDX COD-AB v03)."""
    hdx, gb = _dir("HDX_COD_AB_BGD"), _dir("GEOBOUNDARIES_BGD_ADM4")
    if not hdx:
        return
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
            if our is None and p.get("level") == "ward" and p.get("code", "").startswith("BD5081"):
                m = re.search(r"(\d+)", p.get("name_en") or "")
                rcc = next((r for r in rows if r["level"] == "ward" and r["name_en"] == f"Ward {int(m.group(1))}"
                            and by_id[r["parent_id"]]["level"] == "city_corporation"), None) if m else None
                our = rcc["id"] if rcc else None
            r = by_id.get(our)
            if r and f.get("geometry") and r["level"] in ("upazila", "union", "pourashava", "ward", "city_corporation"):
                g = f["geometry"]
                r["_boundary"] = g if g["type"] == "MultiPolygon" else {"type": "MultiPolygon", "coordinates": [g["coordinates"]]}
                n += 1
    log("boundaries", "attached", f"{n} polygons attached (HDX COD-AB v03 upazilas, geoBoundaries 2020 unions/pourashavas/wards)",
        "HDX_COD_AB_BGD")


# ------------------------------------------------------------------ places

# Sources merged first win on conflicting fields; later ones only fill gaps. Curated pilot places come before all.
PLACE_PRIORITY = ["UGC_UNIVERSITIES_RAJ_2026", "DGME_MEDICAL_COLLEGES_RAJ_2026", "DOA_PROTECTED_MONUMENTS_RAJ_2026",
                  "CAAB_AIRPORTS_RAJ_2026", "BD_RAILWAY_RAJ_2026", "BRTC_DEPOTS_RAJ_2026", "RMP_THANAS_2026",
                  "RAJSHAHI_POLICE_2026", "RAJ_RANGE_POLICE_PORTALS_2026", "FSCD_STATIONS_RAJ_2026",
                  "DGHS_HRIS_FACILITIES_RAJ_2026", "BANBEIS_INST_RAJ_2026", "DPE_IPEMIS_PRIMARY_RAJ_2026",
                  "RAJSHAHI_PORTAL_OFFICES_2026", "BDPOST_POSTCODES_RAJ_2026", "DISTRICT_PORTAL_BANKS_RAJ_2026",
                  "DISTRICT_PORTALS_TRANSPORT_RAJ_2026", "PORTAL_TOURIST_SPOTS_RAJ_2026", "BD_POLICE_CONTACTS_2020"]
PREFIX = {"education": "INST", "health": "INST", "religious": "INST", "tourism": "TOUR", "emergency": "SRV",
          "government": "GOV", "transport": "TRN", "finance": "FIN", "business": "BIZ", "agriculture": "AGR"}
# metropolitan thanas inside Rajshahi City Corporation (RMP); their places belong to the city corporation
RCC_ID = 50005
RCC_THANAS = {latin_key(n) for n in ("Boalia", "Bowalia", "Rajpara", "Rajapara", "Motihar", "Matihar", "Shah Makhdum", "Shah Mokhdum",
                                      "Shah Makdum", "Chandrima", "Airport", "Kashiadanga", "Rajshahi City", "Rajshahi Metropolitan")}
PABA_THANAS = {latin_key(n) for n in ("Belpukur", "Damkura", "Karnahar", "Karnohar", "Katakhali")}   # RMP thanas in Paba upazila
RAJSHAHI_DISTRICT_ID = 20015
DISTRICT_ALIASES = {"bogra": "bogura", "chapainawabganj": "chapainawabganj", "chapainababganj": "chapainawabganj",
                    "nawabganj": "chapainawabganj", "chapai": "chapainawabganj", "jaipurhat": "joypurhat", "joypurhat": "joypurhat"}
# attribute keys worth showing (source keys are kept; labels live in apps/web/messages/*.json → PlaceAttr)
ATTR_KEYS = ["eiin", "school_code", "facility_code", "institute_type", "facility_type", "school_type", "education_level",
             "management", "mpo", "for_whom", "area_status", "teachers", "students", "beds", "agency", "ugc_category",
             "protected_monument", "construction_date_as_stated", "head_designation", "postcode", "station_code", "iata", "icao"]
GROUP = {"religious": "tourism"}
# contacts: keep institutional ones only (COLLECTION_FORMAT.md)
PERSONAL_MAIL_SOURCES = {"DGHS_HRIS_FACILITIES_RAJ_2026"}     # registry mixes office mailboxes with staff gmail
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


def _distinct_en(s):
    s = _GEN_EN.sub(" ", (s or "").replace("&", " and "))
    return en_key(_AREA_EN.sub(" ", s) if _AREA_EN else s)


def _distinct_bn(s):
    s = _GEN_BN.sub("", s or "")
    return bn_key(_AREA_BN.sub("", s) if _AREA_BN else s)


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
    """Merge collected places (data/sources/*/places.csv) with the curated pilot places.

    Returns the full place list (pilot places first, enriched in place). Every merge, skip and coordinate fix is logged.
    """
    from trust import eligible
    global _AREA_EN, _AREA_BN
    by_id = {r["id"]: r for r in rows}
    names = [r for r in rows if r["level"] in ("district", "upazila") and (r["id"] == DIVISION_ID or
             r["parent_id"] == DIVISION_ID or by_id.get(r["parent_id"], {}).get("parent_id") == DIVISION_ID)]
    en_words = sorted({w.lower() for r in names for w in [r["name_en"], r.get("_src_en") or ""] if w} |
                      {"bogra", "nawabganj", "chapai", "sadar", "city"}, key=len, reverse=True)
    _AREA_EN = re.compile(r"\b(" + "|".join(re.escape(w) for w in en_words) + r")\b", re.I)
    bn_words = sorted({r["name_bn"] for r in names if r["name_bn"]} | {"সদর", "সিটি", "বগুড়া", "চাঁপাই"},
                      key=len, reverse=True)
    _AREA_BN = re.compile("|".join(re.escape(w) for w in bn_words))
    districts = {latin_key(r["name_en"]): r for r in rows if r["level"] == "district" and r["parent_id"] == DIVISION_ID}
    upz_by_d = defaultdict(list)
    for r in rows:
        if r["level"] == "upazila" and r["parent_id"] in {d["id"] for d in districts.values()}:
            upz_by_d[r["parent_id"]].append(r)
    unions_by_u = defaultdict(list)
    for r in rows:
        if r["level"] == "union":
            unions_by_u[r["parent_id"]].append(r)
    dist_poly = PolygonIndex([f for f in district_features if f["properties"].get("division_id") == DIVISION_ID])
    area_poly = PolygonIndex([{"type": "Feature", "geometry": r["_boundary"], "properties": {"id": r["id"]}}
                              for r in rows if r.get("_boundary") and r["level"] in ("union", "pourashava")])

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
    index = defaultdict(list)      # (district_id, group) -> places
    for p in out:
        index[(p["district_id"], GROUP.get(p["category"], p["category"]))].append(p)

    order = {k: i for i, k in enumerate(PLACE_PRIORITY)}
    srcs = sorted((m for m in _manifests() if os.path.isfile(os.path.join(m["_dir"], "places.csv"))),
                  key=lambda m: (order.get(m["key"], 999), m["key"]))
    stats = {}
    for m in srcs:
        key, trust = m["key"], int(m.get("trust_level") or 1)
        st = stats.setdefault(key, dict(source=key, trust=trust, rows=0, added=0, merged=0, skipped=0, with_point=0,
                                        point_dropped=0, union_resolved=0, upazila_resolved=0))
        for r in read_csv(os.path.join(m["_dir"], "places.csv")):
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
                log(rid, "place_skipped", f"district {r.get('district_en')!r} not in Rajshahi Division", key)
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
                upz = upazila_of(d, r["upazila_en"])
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
            if upz and not union_id:
                un = union_from_text(upz, extra.get("union_or_ward_bn") or (name_bn if cat == "government.union_parishad" else ""))
                union_id = un["id"] if un else None
            st["upazila_resolved"] += bool(upz or cc)
            st["union_resolved"] += bool(union_id)
            phones = []
            for ph in re.split(r"[;,/]| or ", r.get("phone") or ""):
                ph = re.sub(r"[^\d+\-]", "", ph.strip())
                if len(re.sub(r"\D", "", ph)) >= 5 and ph not in phones:
                    phones.append(ph)
            email = (re.split(r"[;,\s]+", r.get("email") or "") or [""])[0] or None
            if email and (key in PERSONAL_MAIL_SOURCES and not OFFICIAL_MAIL.search(email) or "@" not in email):
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
            group = index[(d["id"], GROUP.get(top, top))]
            best, score = None, 0.0
            # a portal's tourist spot can be a college, office or mosque listed elsewhere: exact names only
            others = [p for g, ps in index.items() if g[0] == d["id"] and g != (d["id"], GROUP.get(top, top)) for p in ps
                      if top == "tourism" and not rec["_bn_fallback"] and bn_key(p["name_bn"]) == bn_key(rec["name_bn"])]
            for p in group + others:
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
                _merge(best, rec)
                st["merged"] += 1
                log(best["slug"], "place_merged", f"{rid} ({score:.2f})", key)
                continue
            pid = _hash_id(rid, used_ids)
            base = _slug(name_en or romanize_bn(name_bn))[:80].strip("-") or _slug(cat_by_key[cat]["name_en"])
            where = _slug((upz or {}).get("name_en") or ("rajshahi-city" if cc else d["name_en"]))
            slug = f"{base}-{where}" if where and not base.endswith(where) else base
            slug_, n = slug, 2
            while slug_ in slugs:
                slug_, n = f"{slug}-{n}", n + 1
            slugs.add(slug_)
            rec.update(public_id=f"{PREFIX.get(top, 'PLC')}-{pid:08d}", slug=slug_)
            out.append(rec)
            group.append(rec)
            st["added"] += 1

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
