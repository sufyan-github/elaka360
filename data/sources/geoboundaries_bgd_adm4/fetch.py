#!/usr/bin/env python3
"""geoBoundaries gbOpen BGD ADM4 (union / paurashava / city-ward polygons) -> Rajshahi Division, with HDX P-codes.

COD-AB v03 on HDX has no ADM4 polygons. geoBoundaries redistributes the earlier OCHA ROAP / BBS ADM4 layer
(HDX "administrative-boundaries-of-bangladesh-as-of-2015", year represented 2020) but strips the P-codes. The HDX
bgd_adminpoints layer (valid_on 2020-11-13) still carries the ADM4 P-codes, one label point per unit; this script
puts each label point into its geoBoundaries polygon (point-in-polygon) and keeps only polygons that receive exactly
one point whose name equals the polygon name. Everything else is reported, not guessed.

Writes:  boundaries.geojson, areas.csv (centroid lat/lon), facts.csv (area_km2 computed here), SOURCE.json
Inputs:  geoBoundaries API + GitHub release file (~340 MB, cached in --cache, not committed);
         ../hdx_cod_ab_bgd/raw/bgd_adminpoints_rajshahi.geojson (run ../hdx_cod_ab_bgd/fetch.py first).
Dependencies: Python 3 standard library + requests. Geometry helpers are imported from ../hdx_cod_ab_bgd/fetch.py.
Run:  python3 -I data/sources/geoboundaries_bgd_adm4/fetch.py [--cache DIR]
"""
import argparse, datetime, importlib.util, json, os, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
HDX_DIR = os.path.join(os.path.dirname(HERE), "hdx_cod_ab_bgd")
_spec = importlib.util.spec_from_file_location("hdx_fetch", os.path.join(HDX_DIR, "fetch.py"))
sys.dont_write_bytecode = True
H = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(H)

KEY = "GEOBOUNDARIES_BGD_ADM4"
API = "https://www.geoboundaries.org/api/current/gbOpen/BGD/ADM4/"
PAGE = "https://www.geoboundaries.org/countryDownloads.html"
SIMPLIFY_DEG = 0.0002


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=os.path.join(tempfile.gettempdir(), "elaka360_cache"))
    a = ap.parse_args()
    os.makedirs(a.cache, exist_ok=True)
    meta = H.get(API).json()
    gpath = os.path.join(a.cache, "geoBoundaries-BGD-ADM4.geojson")
    if not os.path.isfile(gpath):
        with H.get(meta["gjDownloadURL"], stream=True) as r, open(gpath, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    pts = json.load(open(os.path.join(HDX_DIR, "raw", "bgd_adminpoints_rajshahi.geojson"), encoding="utf-8"))["features"]
    adm1 = [p for p in pts if p["properties"]["admin_level"] == 1][0]
    lv4 = [p for p in pts if p["properties"]["admin_level"] == 4]
    xs = [p["geometry"]["coordinates"][0] for p in lv4]; ys = [p["geometry"]["coordinates"][1] for p in lv4]
    B = (min(xs), min(ys), max(xs), max(ys))

    # stream the national file (one feature per line) and keep polygons whose bbox can contain a BD50 label point
    cand = []
    with open(gpath, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip().rstrip(",")
            if not line.startswith('{ "type": "Feature"'):
                continue
            f = json.loads(line)
            b = H.bbox(f["geometry"])
            if b[2] < B[0] or b[0] > B[2] or b[3] < B[1] or b[1] > B[3]:
                continue
            f["_bb"] = b
            cand.append(f)

    hits = {}
    problems = []
    for p in lv4:
        x, y = p["geometry"]["coordinates"][:2]
        h = [f for f in cand if f["_bb"][0] <= x <= f["_bb"][2] and f["_bb"][1] <= y <= f["_bb"][3]
             and H.point_in_geom(x, y, f["geometry"])]
        if len(h) != 1:
            problems.append((p["properties"]["adm4_pcode"], p["properties"]["name"], f"{len(h)} polygons"))
            continue
        hits.setdefault(h[0]["properties"]["shapeID"], []).append((p, h[0]))
    feats, areas, facts = [], [], []
    for sid, lst in sorted(hits.items(), key=lambda kv: kv[1][0][0]["properties"]["adm4_pcode"]):
        if len(lst) != 1:
            problems.append((sid, "", f"{len(lst)} label points in one polygon"))
            continue
        p, f = lst[0]
        pp = p["properties"]
        name = f["properties"]["shapeName"]
        if name.strip().lower() != pp["adm4_name"].strip().lower():
            problems.append((pp["adm4_pcode"], pp["adm4_name"], f"polygon named {name}"))
            continue
        level = H.adm4_level(name)
        is_thana = level == "ward"
        g = H.simplify_geom(f["geometry"], SIMPLIFY_DEG)
        area = H.geom_area_km2(f["geometry"])
        cx, cy = H.geom_centroid(f["geometry"])
        inside = H.point_in_geom(cx, cy, f["geometry"])
        feats.append({"type": "Feature", "properties": {
            "level": level, "name_en": name, "name_bn": "", "code": pp["adm4_pcode"], "code_scheme": "HDX_PCODE_2020",
            "parent_code": pp["adm3_pcode"], "district_en": pp["adm2_name"], "upazila_en": "" if is_thana else pp["adm3_name"],
            "source_key": KEY, "source_id": f["properties"]["shapeID"]}, "geometry": g})
        note = "lat/lon = area-weighted centroid of the full-resolution polygon"
        if not inside:
            note += " (falls OUTSIDE the polygon - irregular/multi-part shape; use the HDX label point instead)"
        if "(part)" in name.lower():
            note += "; source marks this unit as a part of a split union"
        areas.append({"level": level, "name_en": name, "name_bn": "", "parent_level": "thana" if is_thana else "upazila",
                      "parent_name_en": pp["adm3_name"], "district_en": pp["adm2_name"],
                      "upazila_en": "" if is_thana else pp["adm3_name"], "code": pp["adm4_pcode"],
                      "code_scheme": "HDX_PCODE_2020", "lat": round(cy, 5), "lon": round(cx, 5), "source_key": KEY,
                      "source_url": meta["gjDownloadURL"],
                      "notes": f"geoBoundaries shapeID {f['properties']['shapeID']}; P-code attached via HDX label point; " + note})
        facts.append({"entity_level": level, "entity_name_en": name, "district_en": pp["adm2_name"],
                      "upazila_en": "" if is_thana else pp["adm3_name"], "code": pp["adm4_pcode"], "fact": "area_km2",
                      "value": round(area, 3), "unit": "km2", "basis": "computed_from_polygon",
                      "year": meta.get("boundaryYearRepresented") or "", "source_key": KEY, "source_url": meta["gjDownloadURL"],
                      "notes": "geodesic area computed by Elaka360 from the unsimplified geoBoundaries polygon; not an official figure"})

    with open(os.path.join(HERE, "boundaries.geojson"), "w", encoding="utf-8") as fh:
        json.dump({"type": "FeatureCollection", "name": f"{KEY} Rajshahi Division (BD50) ADM4", "features": feats}, fh,
                  ensure_ascii=False, separators=(",", ":"))
    H.write_csv(os.path.join(HERE, "areas.csv"), H.AREA_COLS, areas)
    H.write_csv(os.path.join(HERE, "facts.csv"), H.FACT_COLS, facts)
    files = ["areas.csv", "boundaries.geojson", "facts.csv"]
    manifest = {
        "key": KEY,
        "name": "geoBoundaries gbOpen Bangladesh ADM4 (unions, paurashavas, city wards), Rajshahi Division extract",
        "organization": "geoBoundaries (William & Mary geoLab); original data: Bangladesh Bureau of Statistics (BBS), OCHA ROAP",
        "source_type": "humanitarian_dataset",
        "trust_level": 3,
        "urls": [API, meta["gjDownloadURL"], "https://" + meta.get("boundarySourceURL", "")],
        "accessed": datetime.date.today().isoformat(),
        "publication_date": None,
        "license": "CC-BY-IGO-3.0",
        "license_url": "https://creativecommons.org/licenses/by/3.0/igo/legalcode",
        "attribution": "geoBoundaries (Runfola et al. 2020, PLOS ONE); data: Bangladesh Bureau of Statistics (BBS), OCHA ROAP",
        "files": {f: H.sha256(os.path.join(HERE, f)) for f in files},
        "notes": (f"geoBoundaries {meta.get('boundaryID')}, year represented {meta.get('boundaryYearRepresented')}, "
                  f"source update {meta.get('sourceDataUpdateDate')}, build {meta.get('buildDate')}, licence as stated by "
                  f"geoBoundaries: {meta.get('boundaryLicense')} (licence source {meta.get('licenseSource')}). "
                  "P-codes (HDX_PCODE_2020) attached from HDX COD-AB bgd_adminpoints by point-in-polygon; "
                  f"{len(feats)} polygons kept, {len(problems)} label points/polygons not assigned. "
                  "Polygons simplified (Douglas-Peucker 0.0002 deg, 5 decimals) ring by ring."),
    }
    json.dump(manifest, open(os.path.join(HERE, "SOURCE.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    from collections import Counter
    print("kept", len(feats), Counter(f["properties"]["level"] for f in feats))
    print("problems", problems)
    print("centroid outside polygon", sum(1 for a in areas if "OUTSIDE" in a["notes"]))
    print("boundaries.geojson", os.path.getsize(os.path.join(HERE, "boundaries.geojson")), "bytes")


if __name__ == "__main__":
    sys.exit(main())
