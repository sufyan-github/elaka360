#!/usr/bin/env python3
"""DGHS "Bangladesh GeoCodes" FHIR CodeSystem (BBS geo-codes as republished by DGHS) -> one division (default Rajshahi).

The official BBS geo-code page (bbs.gov.bd) could not be fetched from here (TLS certificate error / redirect to the
home page), so this uses the machine-readable list in the DGHS Bangladesh Core FHIR Implementation Guide:
https://fhir.dghs.gov.bd/core/CodeSystem-bd-geocodes.html (publisher DGHS, MoHFW; IG licence CC0-1.0).

Code layout seen in the list (not documented by DGHS; inferred from the data, see REPORT.md):
  2 digits  division                       50
  4 digits  district                       5081
  6 digits  district + city corporation    508166 (Rajshahi City Corporation); "<district>00 ... N/A" = none
  8 digits  upazila / city thana           50810010 Bagha, 50816622 Boalia (thana of CC 66)
  10 digits 8-digit unit + 2-digit paurashava / city-corporation part; "...99 Unions Of X Upazila" = union group

Writes: raw/bd-geocodes_<division>.json, areas.csv (code_scheme BBS_GEOCODE), crosswalk.csv, SOURCE.json.
Dependencies: stdlib + requests; crosswalk helpers imported from ../hdx_cod_ab_bgd/fetch.py.
Run: python3 -I data/sources/dghs_bd_geocodes/fetch.py [--division rajshahi] [--out DIR]
Default (no arguments): Rajshahi Division (code 50) into this folder. Another division writes to
../dghs_bd_geocodes_<division>/ with key DGHS_BD_GEOCODES_<DIVISION> (data/sources/DIVISIONS.md).
"""
import argparse, datetime, importlib.util, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("hdx_fetch", os.path.join(os.path.dirname(HERE), "hdx_cod_ab_bgd", "fetch.py"))
sys.dont_write_bytecode = True
H = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(H)

KEY = "DGHS_BD_GEOCODES"
JSON_URL = "https://fhir.dghs.gov.bd/core/CodeSystem-bd-geocodes.json"
PAGE = "https://fhir.dghs.gov.bd/core/CodeSystem-bd-geocodes.html"
IG_URL = "https://fhir.dghs.gov.bd/core/ImplementationGuide-bd.fhir.core.json"
KIND = "dghs_geocodes"

# City corporations whose 8-digit units with a "Unions Of X Upazila" group are metro thanas, not upazilas: in Dhaka
# North / South the group holds the unions absorbed by the 2016 extension (HDX v03 and the seed have only 5 upazilas in
# Dhaka district). Khulna City Corporation (404733): Daulatpur and Khan Jahan Ali have "Unions Of ... Upazila" groups, but
# BBS 2022 has them as metro thanas of the city corporation (their unions Arangghata, Jogipol and Atra Gilatala under
# Dighalia / Phultala upazilas), and HDX v03 and the seed have 9 upazilas in Khulna district without them. Elsewhere
# (Rangpur Sadar, Gazipur Sadar, Bandar, Narayanganj Sadar) such a unit is read as an upazila.
METRO_CC_WITH_UNION_GROUPS = {"302620", "302625", "404733"}
UNION_GROUP_NOTE = {  # why the union group is not read as an upazila (default: the Dhaka case)
    "404733": "unions listed under Dighalia / Phultala upazilas in BBS 2022",
}
# City corporations that the name matcher cannot pair because of a misspelling in the list; hand-checked by code.
CC_SEED = {"302625": "50001"}  # "Dhaka North City Corperation" -> Dhaka North City Corporation
# Upazilas the name matcher cannot pair (or pairs wrongly), hand-checked against the seed's Bangla name, per division
# (passed to build_crosswalk as `pinned`). Chattogram: Matlab Dakshin/Uttar = Matlab South/North (মতলব দক্ষিণ/উত্তর; the
# fuzzy tier paired Uttar with South), Cumilla Adarsha Sadar = Comilla Sadar (কুমিল্লা সদর), Cumilla Sadar Dakshin =
# Sadarsouth (সদর দক্ষিণ), Kowkhali = Kawkhali (কাউখালী). Khulna: Dacope = Dakop (দাকোপ; no tier pairs them), Paikgacha =
# Paikgasa (পাইকগাছা; only a low fuzzy pair). Barishal: Indurkani = Zianagar (below). Sylhet: Sulla, Shantiganj (below).
UNIT_SEED_BY_DIV = {
    "chattogram": {"20130076": "30056", "20130079": "30058", "20195067": "30011", "20195033": "30014",
                   "20840025": "30035"},
    "khulna": {"40470017": "30213", "40470064": "30206"},
    # Barishal: Indurkani = seed Zianagar (জিয়ানগর, the upazila's former name); HDX's 2020 point for upazila 79-90 is named
    # Zianagar, and the seed's three Zianagar unions are BBS 2022 Indurkani unions
    "barishal": {"10790090": "30245"},
    # Sylhet: Sulla = seed Shalla (শাল্লা; BBS 2022 60-90-86 "Shalla"; only a fuzzy 0.75 candidate); Shantiganj = seed South
    # Sunamganj (দক্ষিণ সুনামগঞ্জ, the upazila's former name Dakshin Sunamganj; BBS 2022 60-90-87 Shantiganj has the seed
    # South Sunamganj's eight unions; HDX's 2020 point for it is "Dakshin Sunamganj")
    "sylhet": {"60900086": "30309", "60900087": "30301"},
}
# Upazila codes that the "listed under another division" check below would flag, but which are the correctly filed
# copy, hand-checked per code against HDX COD-AB v03 and BBS 2022 (the other division's copy keeps its "probably
# misfiled" note). Mymensingh: 45890090 Sreebardi (Sherpur) = HDX v03 BD45890090 Sreebardi and BBS 2022 45-89-90
# Sreebardi; the Dhaka copy 30260090 is the misfiled one.
FILED_CORRECTLY = {"45890090": "HDX COD-AB v03 BD45890090 and BBS 2022 45-89-90 place Sreebardi in Sherpur district"}


def walk(cs):
    for c in cs:
        yield c
        yield from walk(c.get("concept", []))


def main():
    global KEY
    ap = argparse.ArgumentParser()
    ap.add_argument("--division", default="rajshahi", choices=sorted(H.DIVISIONS))
    ap.add_argument("--out", default=None, help="output folder (default: this folder for rajshahi, else ../dghs_bd_geocodes_<division>)")
    a = ap.parse_args()
    _, bbs, seed_id, div_name = H.DIVISIONS[a.division]
    KEY = H.division_key(KEY, a.division)
    OUT = H.out_dir(HERE, a.division, a.out)
    os.makedirs(os.path.join(OUT, "raw"), exist_ok=True)
    cs = H.get(JSON_URL).json()
    ig = H.get(IG_URL).json()
    allc = [c for c in walk(cs.get("concept", []))]
    raj = [{"code": c["code"], "display": c.get("display")} for c in allc if c["code"].startswith(bbs)]
    snap = {k: cs.get(k) for k in ("url", "version", "name", "title", "status", "date", "publisher", "description", "count")}
    snap["ig_license"] = ig.get("license")
    snap["ig_version"] = ig.get("version")
    snap[f"concepts_{a.division}_division"] = raj
    json.dump(snap, open(os.path.join(OUT, "raw", f"bd-geocodes_{a.division}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    by = {c["code"]: c["display"].strip() for c in raj}
    ver = f"DGHS bd-geocodes v{cs.get('version')} ({(cs.get('date') or '')[:10]})"
    areas, units, skipped = [], [], []

    def add(level, code, name, parent_level, parent_name, district, upazila, notes=""):
        areas.append({"level": level, "name_en": name, "name_bn": "", "parent_level": parent_level, "parent_name_en": parent_name,
                      "district_en": district, "upazila_en": upazila, "code": code, "code_scheme": "BBS_GEOCODE",
                      "source_key": KEY, "source_url": PAGE,
                      "notes": f"{ver}; BBS code vintage not stated by DGHS" + (f"; {notes}" if notes else "")})

    for code in sorted(by):
        name = by[code]
        n = len(code)
        dist = by.get(code[:4], "")
        if n == 2:
            add("division", code, name, "country", "Bangladesh", "", "")
        elif n == 4:
            add("district", code, name, "division", by.get(code[:2], ""), name, "")
            units.append({"level": "district", "code": code, "name_en": name, "match_parent": code})
        elif n == 6:
            if "N/A" in name:
                skipped.append((code, name, "district placeholder (no city corporation)"))
                continue
            add("city_corporation", code, name, "district", dist, dist, "")
            units.append({"level": "city_corporation", "code": code, "name_en": name, "match_parent": code[:4]})
        elif n == 8:
            cc = code[:6]
            has_unions = re.match(r"unions of", by.get(code + "99", ""), re.I)
            if cc in by and "N/A" not in by[cc] and not has_unions:
                add("thana", code, name, "city_corporation", by[cc], dist, "", "thana of the city corporation")
            elif cc in METRO_CC_WITH_UNION_GROUPS:  # Dhaka North / South metro thanas with absorbed unions
                add("thana", code, name, "city_corporation", by[cc], dist, "",
                    f"thana of the city corporation; the list also has '{by[code + '99']}' ("
                    + UNION_GROUP_NOTE.get(cc, "unions absorbed by the city corporation")
                    + "), read as a metro thana, not an upazila")
            elif cc in by and "N/A" not in by[cc]:  # e.g. 55857549 Rangpur Sadar: CC code space, but has a union group
                add("upazila", code, name, "district", dist, dist, name,
                    f"code lies under city corporation {cc} ({by[cc]}) but the list has '{by[code + '99']}', so read as an upazila")
                units.append({"level": "upazila", "code": code, "name_en": name, "match_parent": code[:4]})
            else:
                add("upazila", code, name, "district", dist, dist, name)
                units.append({"level": "upazila", "code": code, "name_en": name, "match_parent": code[:4]})
        elif n == 10:
            parent = by.get(code[:8], "")
            if re.match(r"unions of", name, re.I):
                skipped.append((code, name, "union-group placeholder, no union names in this list"))
            elif re.search(r"city corp", name, re.I):
                skipped.append((code, name, f"part of the city corporation inside thana {parent}"))
            elif re.search(r"paura|pourash|pourasab", name, re.I):  # "Pourasabha": Sreebardi (Mymensingh)
                add("pourashava", code, name, "upazila", parent, dist, parent)
                units.append({"level": "pourashava", "code": code, "name_en": name, "match_parent": code[:8]})
            else:
                skipped.append((code, name, "unrecognised 10-digit entry"))
    # 8-digit units whose number and exact name (or 'Unions Of <name> Upazila') are also listed under a district of
    # another division: probably misfiled (Dhaka: Gaffargaon, Gauripur, Sreebardi)
    nat = [(c["code"], (c.get("display") or "").strip()) for c in allc]
    for r in areas:
        if r["level"] != "upazila":
            continue
        elsewhere = sorted(c for c, d in nat if len(c) in (8, 10) and c[:2] != r["code"][:2] and c[4:8] == r["code"][4:8]
                           and re.fullmatch(r"(unions of )?" + re.escape(r["name_en"]) + r"( upazila)?", d, re.I))
        if elsewhere and r["code"] in FILED_CORRECTLY:
            r["notes"] += (f"; the same upazila number and name are also listed under another division ("
                           + ", ".join(f"{c} {dict(nat)[c]}" for c in elsewhere) + "); hand-checked: this code is the "
                           "correctly filed one (" + FILED_CORRECTLY[r["code"]] + "), the other entry is probably misfiled")
        elif elsewhere:
            r["notes"] += (f"; doubtful: the same upazila number and name are listed under another division ("
                           + ", ".join(f"{c} {dict(nat)[c]}" for c in elsewhere) + "), so this code is probably misfiled")
            for p in areas:
                if p["level"] == "pourashava" and p["code"][:8] == r["code"]:
                    p["notes"] += f"; doubtful: parent upazila code {r['code']} is probably misfiled (see that row)"
    dup = {}
    for r in areas:
        dup.setdefault((r["level"], r["district_en"], r["name_en"].lower()), []).append(r["code"])
    for r in areas:
        codes = dup[(r["level"], r["district_en"], r["name_en"].lower())]
        if len(codes) > 1:
            r["notes"] += f"; same name listed under {len(codes)} codes ({', '.join(codes)}) - duplicate or renumbering, unresolved"
    H.write_csv(os.path.join(OUT, "areas.csv"), H.AREA_COLS, areas)

    seed_rows, by_id = H.load_seed(seed_id)
    xw, _ = H.build_crosswalk(units, seed_rows, by_id, "DGHS/BBS", district_key=lambda c: "BD" + c[:4],
                              district_map=H.DISTRICT_SEED_BY_DIV.get(a.division), pinned=UNIT_SEED_BY_DIV.get(a.division))
    for code, oid in CC_SEED.items():  # hand-checked city corporations the name matcher could not pair
        hit = [r for r in xw if r["source_code"] == code and not r["our_id"]]
        if hit and oid in by_id and any(r["our_id"] == oid and r["match_method"] == "no_source_unit" for r in xw):
            o = by_id[oid]
            hit[0].update({"our_id": oid, "our_level": o["level"], "our_name_en": o["name_en"], "our_path": o["path"],
                           "match_method": "code_city_corporation", "confidence": "high",
                           "notes": f"source level city_corporation; spelling differs ({hit[0]['source_name_en']} vs "
                                    f"{o['name_en']}); matched by hand via city-corporation code {code}"})
            xw = [r for r in xw if not (r["our_id"] == oid and r["match_method"] == "no_source_unit")]
    H.write_csv(os.path.join(OUT, "crosswalk.csv"), H.XW_COLS, xw)

    files = ["areas.csv", "crosswalk.csv", f"raw/bd-geocodes_{a.division}.json"]
    manifest = {
        "key": KEY,
        "name": f"Bangladesh GeoCodes CodeSystem (BBS geo-codes) in the DGHS Bangladesh Core FHIR IG, {div_name} Division extract",
        "organization": "Directorate General of Health Services (DGHS), Ministry of Health and Family Welfare",
        "source_type": "government_portal",
        "trust_level": 4,
        "urls": [PAGE, JSON_URL, IG_URL],
        "accessed": datetime.date.today().isoformat(),
        "publication_date": (cs.get("date") or "")[:10] or None,
        "license": ig.get("license"),
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "attribution": "Directorate General of Health Services (DGHS), Bangladesh — Bangladesh Core FHIR IG; codes: BBS geo-code system",
        "files": {f: H.sha256(os.path.join(OUT, f)) for f in files},
        "notes": (f"CodeSystem {cs.get('url')} version {cs.get('version')}, status {cs.get('status')}, date {cs.get('date')}, "
                  f"{cs.get('count')} codes nationally. Divisions, districts, upazilas/city thanas, city corporations and "
                  "paurashavas only: no union-level codes (only 'Unions Of X Upazila' placeholders). The IG does not say "
                  "which BBS release the codes come from. Skipped entries: " +
                  "; ".join(f"{c} {n} ({why})" for c, n, why in skipped if "Unions Of" not in n) +
                  f"; plus {sum(1 for s in skipped if 'Unions Of' in s[1])} 'Unions Of ... Upazila' placeholders."),
        "division": a.division,
        "kind": KIND,
    }
    json.dump(manifest, open(os.path.join(OUT, "SOURCE.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    from collections import Counter
    print("areas", Counter(a["level"] for a in areas))
    print("crosswalk", Counter((r["our_level"] or "-", r["match_method"]) for r in xw))
    print("skipped", len(skipped))


if __name__ == "__main__":
    sys.exit(main())
