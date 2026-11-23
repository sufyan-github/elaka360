#!/usr/bin/env python3
"""OpenStreetMap villages and named roads for Bangladesh (Geofabrik extract), for the seed pipeline.

    python3 fetch.py --pbf /tmp/elaka360_osm/bangladesh-latest.osm.pbf     # parse an extract already downloaded
    python3 fetch.py --cache /tmp/elaka360_osm                              # download it first (checked against .md5)

Writes, next to this file:
  villages.csv  settlement points: place=village|hamlet|isolated_dwelling|neighbourhood|suburb|quarter with a name
                (nodes, and area centroids). Matched by pipelines/localities.py to BBS 2022 villages and mouzas of the
                same union by name; a match gives the census village a location (and a Bangla name when OSM has one).
  roads.csv     named roads (highway=motorway…residential, living_street) as points sampled every ~250 m along the way,
                so the pipeline can list each union's roads by point-in-polygon.
  stats.json    counts.
Data access: ONE download of https://download.geofabrik.de/asia/bangladesh-latest.osm.pbf (about 360 MB), the same
extract the OSM POI collectors use (approved exception in COLLECTION_FORMAT.md). Needs pyosmium (`pip install
osmium==4.3.2`) and requests. Community data (ODbL): every row is unverified.
"""
import argparse, csv, hashlib, json, math, os, re, sys, time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
PBF_URL = "https://download.geofabrik.de/asia/bangladesh-latest.osm.pbf"
PLACES = ("village", "hamlet", "isolated_dwelling", "neighbourhood", "suburb", "quarter")
ROADS = ("motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential", "living_street",
         "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link")
STEP_M = 250
BENGALI = re.compile(r"[ঀ-৿]")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def download(cache):
    import requests
    os.makedirs(cache, exist_ok=True)
    path = os.path.join(cache, "bangladesh-latest.osm.pbf")
    md5 = requests.get(PBF_URL + ".md5", timeout=60).text.split()[0]
    if not os.path.exists(path) or hashlib.md5(open(path, "rb").read()).hexdigest() != md5:
        with requests.get(PBF_URL, stream=True, timeout=(30, 600)) as r, open(path + ".part", "wb") as f:
            r.raise_for_status()
            for b in r.iter_content(1 << 20):
                f.write(b)
        os.replace(path + ".part", path)
        if hashlib.md5(open(path, "rb").read()).hexdigest() != md5:
            sys.exit("downloaded extract does not match its .md5")
    return path


def dist_m(a, b):
    kx = 111_320 * math.cos(math.radians((a[1] + b[1]) / 2))
    return math.hypot((a[0] - b[0]) * kx, (a[1] - b[1]) * 110_574)


def sample(coords):
    """Points every ~STEP_M metres along a line, always including both ends; and the line's length."""
    out, length, since = [coords[0]], 0.0, 0.0
    for a, b in zip(coords, coords[1:]):
        d = dist_m(a, b)
        length += d
        since += d
        if since >= STEP_M:
            out.append(b)
            since = 0.0
    if out[-1] != coords[-1]:
        out.append(coords[-1])
    return out, length


def names(t):
    name = (t.get("name") or "").strip()
    bn = (t.get("name:bn") or (name if BENGALI.search(name) else "")).strip()
    en = (t.get("name:en") or (name if name and not BENGALI.search(name) else "")).strip()
    return name, bn, en


def parse(pbf):
    import osmium
    fp = (osmium.FileProcessor(pbf).with_locations("flex_mem")
          .with_areas(osmium.filter.KeyFilter("place"))
          .with_filter(osmium.filter.KeyFilter("place", "highway")))
    stamp = fp.header.get("osmosis_replication_timestamp") or ""
    villages, roads, counts = [], [], Counter()
    for o in fp:
        t = dict(o.tags)
        if o.is_node() and t.get("place") in PLACES and o.location.valid():
            name, bn, en = names(t)
            if not name:
                continue
            villages.append(dict(osm_type="node", osm_id=o.id, place=t["place"], name=name, name_bn=bn, name_en=en,
                                 lat=round(o.location.lat, 6), lon=round(o.location.lon, 6)))
            counts["village_node"] += 1
        elif o.is_area() and t.get("place") in PLACES:
            name, bn, en = names(t)
            pts = [(n.lon, n.lat) for ring in o.outer_rings() for n in ring]
            if not name or not pts:
                continue
            villages.append(dict(osm_type="way" if o.from_way() else "relation", osm_id=o.orig_id(), place=t["place"],
                                 name=name, name_bn=bn, name_en=en, lat=round(sum(p[1] for p in pts) / len(pts), 6),
                                 lon=round(sum(p[0] for p in pts) / len(pts), 6)))
            counts["village_area"] += 1
        elif o.is_way() and t.get("highway") in ROADS:
            name, bn, en = names(t)
            ref = (t.get("ref") or "").strip()
            if not name and not ref:
                continue
            try:
                coords = [(n.lon, n.lat) for n in o.nodes if n.location.valid()]
            except osmium.InvalidLocationError:
                continue
            if len(coords) < 2:
                continue
            pts, length = sample(coords)
            roads.append(dict(osm_id=o.id, highway=t["highway"], name=name, name_bn=bn, name_en=en, ref=ref,
                              length_m=round(length), points=";".join(f"{x:.5f} {y:.5f}" for x, y in pts)))
            counts["road"] += 1
    return villages, roads, counts, stamp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pbf")
    ap.add_argument("--cache", default=os.environ.get("OSM_CACHE", "/tmp/elaka360_osm"))
    a = ap.parse_args()
    pbf = a.pbf or download(a.cache)
    t0 = time.time()
    villages, roads, counts, stamp = parse(pbf)
    villages.sort(key=lambda r: (r["osm_type"], r["osm_id"]))
    roads.sort(key=lambda r: r["osm_id"])
    for fn, rows, cols in (("villages.csv", villages, ["osm_type", "osm_id", "place", "name", "name_bn", "name_en", "lat", "lon"]),
                           ("roads.csv", roads, ["osm_id", "highway", "name", "name_bn", "name_en", "ref", "length_m", "points"])):
        with open(os.path.join(HERE, fn), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    stats = dict(counts, places=dict(Counter(v["place"] for v in villages)), highways=dict(Counter(r["highway"] for r in roads)),
                 with_bangla_name=sum(1 for v in villages if v["name_bn"]), osm_timestamp=stamp, seconds=round(time.time() - t0))
    json.dump(stats, open(os.path.join(HERE, "stats.json"), "w"), indent=1, sort_keys=True)
    manifest = {
        "key": "OSM_LOCALITIES_2026",
        "name": "OpenStreetMap contributors — villages, hamlets, neighbourhoods and named roads (Bangladesh extract)",
        "organization": "OpenStreetMap Foundation", "source_type": "community_dataset", "trust_level": 1,
        "urls": ["https://download.geofabrik.de/asia/bangladesh.html", PBF_URL, "https://www.openstreetmap.org/copyright"],
        "accessed": time.strftime("%Y-%m-%d"), "publication_date": None, "osm_data_timestamp": stamp,
        "license": "ODbL-1.0", "license_url": "https://opendatacommons.org/licenses/odbl/1-0/", "attribution": "© OpenStreetMap contributors",
        "kind": "osm_localities",
        "files": {fn: sha256(os.path.join(HERE, fn)) for fn in ("villages.csv", "roads.csv", "stats.json", "fetch.py")},
        "notes": ("Geofabrik Bangladesh extract parsed locally with pyosmium. villages.csv: named place=village|hamlet|"
                  "isolated_dwelling|neighbourhood|suburb|quarter (nodes; areas by centroid). roads.csv: named or numbered "
                  "highways from motorway to residential, sampled every ~250 m. Community data: every row is unverified; "
                  "ODbL share-alike applies to databases derived from it. The .pbf is not committed (fetch.py downloads it)."),
    }
    json.dump(manifest, open(os.path.join(HERE, "SOURCE.json"), "w"), indent=2, ensure_ascii=False)
    print(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
