#!/usr/bin/env python3
"""Compare the edge API Worker (D1 snapshot) with the NestJS API it was exported from.

Usage: python3 scripts/edge-parity.py [nest_url] [edge_url]   (defaults: localhost:4000, 127.0.0.1:8789)
Exit 1 on any difference. Order is ignored where the API does not define one (map pins, boundary levels).
"""
import json, sys, urllib.error, urllib.request

NEST = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:4000'
EDGE = sys.argv[2] if len(sys.argv) > 2 else 'http://127.0.0.1:8789'
PATHS = [
    '/v1/stats/national', '/v1/categories', '/v1/categories/health.hospital', '/v1/categories/nope', '/v1/emergency-numbers',
    '/v1/areas?level=district&parent_id=10002', '/v1/areas?level=division', '/v1/areas/by-path', '/v1/areas/by-path?path=rajshahi',
    '/v1/areas/by-path?path=rajshahi/rajshahi', '/v1/areas/by-path?path=rajshahi/rajshahi/bagha', '/v1/areas/by-path?path=dhaka/dhaka/savar',
    '/v1/areas/by-path?path=no/such/place', '/v1/areas/by-path?path=bad%20path', '/v1/areas/20015', '/v1/areas/20015/stats',
    '/v1/areas/20015/children', '/v1/areas/20015/children?level=upazila', '/v1/areas/tree?root_id=1&depth=2',
    '/v1/areas/tree?root_id=10002&depth=2', '/v1/areas/20015/boundary', '/v1/areas/999999999999999999999',
    '/v1/geo/locate?lat=24.37&lon=88.6', '/v1/geo/locate?lat=23.8&lon=90.4', '/v1/geo/locate?lat=24.0&lon=88.95',
    '/v1/places?limit=6', '/v1/places?area_id=20015&limit=12', '/v1/places?category=education&area_id=30139&limit=30',
    '/v1/places?category=health.community_clinic&area_id=10002&limit=20&cursor=MjA', '/v1/places?category=bad!', '/v1/places?area_id=1',
    '/v1/places/rajshahi-college', '/v1/places/university-of-rajshahi', '/v1/places/shah-makhdum-mazar', '/v1/places/nope',
    '/v1/places/nearby?lat=24.37&lon=88.6&radius_m=2000', '/v1/places/nearby?lat=24.85&lon=89.37&radius_m=5000&category=health',
    '/v1/places/geojson?area_id=20015&bbox=88.5,24.3,88.7,24.45', '/v1/places/ruet/reviews',
]
UNORDERED = {'features', 'resolved_levels'}
IGNORE = {'request_id', 'instance', 'version', 'db', 'search', 'detail'}


def get(base, path):
    try:
        with urllib.request.urlopen(base + path, timeout=60) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b'null')


def norm(x, key=None):
    if isinstance(x, dict):
        return {k: norm(v, k) for k, v in x.items() if k not in IGNORE}
    if isinstance(x, list):
        items = [norm(v) for v in x]
        return sorted(items, key=lambda v: json.dumps(v, sort_keys=True, ensure_ascii=False)) if key in UNORDERED else items
    if isinstance(x, float):
        return round(x, 6)
    return x


bad = 0
for p in PATHS:
    (sa, ja), (sb, jb) = get(NEST, p), get(EDGE, p)
    if sa != sb or norm(ja) != norm(jb):
        bad += 1
        a, b = json.dumps(norm(ja), ensure_ascii=False, sort_keys=True), json.dumps(norm(jb), ensure_ascii=False, sort_keys=True)
        i = next((i for i in range(min(len(a), len(b))) if a[i] != b[i]), min(len(a), len(b)))
        print(f'DIFF {p} [{sa} vs {sb}]\n  nest: …{a[max(0, i - 60):i + 100]}\n  edge: …{b[max(0, i - 60):i + 100]}')
print(f'edge-parity: {len(PATHS) - bad}/{len(PATHS)} endpoints identical')
sys.exit(1 if bad else 0)
