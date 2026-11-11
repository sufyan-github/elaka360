#!/usr/bin/env python3
"""DGHS "Bangladesh GeoCodes" FHIR CodeSystem (BBS geo-codes as republished by DGHS) -> Rajshahi Division.

The official BBS geo-code page (bbs.gov.bd) could not be fetched from here (TLS certificate error / redirect to the
home page), so this uses the machine-readable list in the DGHS Bangladesh Core FHIR Implementation Guide:
https://fhir.dghs.gov.bd/core/CodeSystem-bd-geocodes.html (publisher DGHS, MoHFW; IG licence CC0-1.0).

Code layout seen in the list (not documented by DGHS; inferred from the data, see REPORT.md):
  2 digits  division                       50
  4 digits  district                       5081
  6 digits  district + city corporation    508166 (Rajshahi City Corporation); "<district>00 ... N/A" = none
  8 digits  upazila / city thana           50810010 Bagha, 50816622 Boalia (thana of CC 66)
  10 digits 8-digit unit + 2-digit paurashava / city-corporation part; "...99 Unions Of X Upazila" = union group

Writes: raw/bd-geocodes_rajshahi.json, areas.csv (code_scheme BBS_GEOCODE), crosswalk.csv, SOURCE.json.
Dependencies: stdlib + requests; crosswalk helpers imported from ../hdx_cod_ab_bgd/fetch.py.
Run: python3 -I data/sources/dghs_bd_geocodes/fetch.py
"""
import datetime, importlib.util, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("hdx_fetch", os.path.join(os.path.dirname(HERE), "hdx_cod_ab_bgd", "fetch.py"))
sys.dont_write_bytecode = True
H = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(H)

KEY = "DGHS_BD_GEOCODES"
JSON_URL = "https://fhir.dghs.gov.bd/core/CodeSystem-bd-geocodes.json"
PAGE = "https://fhir.dghs.gov.bd/core/CodeSystem-bd-geocodes.html"
IG_URL = "https://fhir.dghs.gov.bd/core/ImplementationGuide-bd.fhir.core.json"


def walk(cs):
    for c in cs:
        yield c
        yield from walk(c.get("concept", []))


def main():
    os.makedirs(os.path.join(HERE, "raw"), exist_ok=True)
    cs = H.get(JSON_URL).json()
    ig = H.get(IG_URL).json()
    allc = [c for c in walk(cs.get("concept", []))]
    raj = [{"code": c["code"], "display": c.get("display")} for c in allc if c["code"].startswith("50")]
    snap = {k: cs.get(k) for k in ("url", "version", "name", "title", "status", "date", "publisher", "description", "count")}
    snap["ig_license"] = ig.get("license")
    snap["ig_version"] = ig.get("version")
    snap["concepts_rajshahi_division"] = raj
    json.dump(snap, open(os.path.join(HERE, "raw", "bd-geocodes_rajshahi.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

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
            if cc in by and "N/A" not in by[cc]:
                add("thana", code, name, "city_corporation", by[cc], dist, "", "thana of the city corporation")
            else:
                add("upazila", code, name, "district", dist, dist, name)
                units.append({"level": "upazila", "code": code, "name_en": name, "match_parent": code[:4]})
        elif n == 10:
            parent = by.get(code[:8], "")
            if re.match(r"unions of", name, re.I):
                skipped.append((code, name, "union-group placeholder, no union names in this list"))
            elif re.search(r"city corp", name, re.I):
                skipped.append((code, name, f"part of the city corporation inside thana {parent}"))
            elif re.search(r"paura|pourash", name, re.I):
                add("pourashava", code, name, "upazila", parent, dist, parent)
                units.append({"level": "pourashava", "code": code, "name_en": name, "match_parent": code[:8]})
            else:
                skipped.append((code, name, "unrecognised 10-digit entry"))
    dup = {}
    for r in areas:
        dup.setdefault((r["level"], r["district_en"], r["name_en"].lower()), []).append(r["code"])
    for r in areas:
        codes = dup[(r["level"], r["district_en"], r["name_en"].lower())]
        if len(codes) > 1:
            r["notes"] += f"; same name listed under {len(codes)} codes ({', '.join(codes)}) - duplicate or renumbering, unresolved"
    H.write_csv(os.path.join(HERE, "areas.csv"), H.AREA_COLS, areas)

    seed_rows, by_id = H.load_seed()
    xw, _ = H.build_crosswalk(units, seed_rows, by_id, "DGHS/BBS", district_key=lambda c: "BD" + c[:4])
    H.write_csv(os.path.join(HERE, "crosswalk.csv"), H.XW_COLS, xw)

    files = ["areas.csv", "crosswalk.csv", "raw/bd-geocodes_rajshahi.json"]
    manifest = {
        "key": KEY,
        "name": "Bangladesh GeoCodes CodeSystem (BBS geo-codes) in the DGHS Bangladesh Core FHIR IG, Rajshahi Division extract",
        "organization": "Directorate General of Health Services (DGHS), Ministry of Health and Family Welfare",
        "source_type": "government_portal",
        "trust_level": 4,
        "urls": [PAGE, JSON_URL, IG_URL],
        "accessed": datetime.date.today().isoformat(),
        "publication_date": (cs.get("date") or "")[:10] or None,
        "license": ig.get("license"),
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "attribution": "Directorate General of Health Services (DGHS), Bangladesh — Bangladesh Core FHIR IG; codes: BBS geo-code system",
        "files": {f: H.sha256(os.path.join(HERE, f)) for f in files},
        "notes": (f"CodeSystem {cs.get('url')} version {cs.get('version')}, status {cs.get('status')}, date {cs.get('date')}, "
                  f"{cs.get('count')} codes nationally. Divisions, districts, upazilas/city thanas, city corporations and "
                  "paurashavas only: no union-level codes (only 'Unions Of X Upazila' placeholders). The IG does not say "
                  "which BBS release the codes come from. Skipped entries: " +
                  "; ".join(f"{c} {n} ({why})" for c, n, why in skipped if "Unions Of" not in n) +
                  f"; plus {sum(1 for s in skipped if 'Unions Of' in s[1])} 'Unions Of ... Upazila' placeholders."),
    }
    json.dump(manifest, open(os.path.join(HERE, "SOURCE.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    from collections import Counter
    print("areas", Counter(a["level"] for a in areas))
    print("crosswalk", Counter((r["our_level"] or "-", r["match_method"]) for r in xw))
    print("skipped", len(skipped))


if __name__ == "__main__":
    sys.exit(main())
