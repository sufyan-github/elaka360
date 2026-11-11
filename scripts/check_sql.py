#!/usr/bin/env python3
"""Prepare + execute every SQL constant in apps/api/src/**/*.sql.ts (and *_SQL constants in controllers)
against a seeded database, with sample parameters. Catches SQL typos without running the API.

Usage: DATABASE_URL=postgres://... python3 scripts/check_sql.py
"""
import os, re, subprocess, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "apps" / "api" / "src"
CONST_RE = re.compile(r"export const (\w+) = `(.*?)`;", re.S)

# sample parameters per statement (strings are SQL literals)
PARAMS = {
    # geo
    "AREA_DETAIL_SQL": ["'rajshahi/rajshahi'"],
    "AREA_BY_ID_PATH_SQL": ["20015"],
    "BREADCRUMB_SQL": ["30134"],
    "CHILDREN_SQL": ["20015", "NULL"],
    "DESCENDANT_COUNTS_SQL": ["10002"],
    "PLACE_COUNTS_SQL": ["20015"],
    "NATIONAL_PLACE_COUNTS_SQL": [],
    "LIST_SQL": ["'district'", "10002", "100", "0"],
    "NATIONAL_STATS_SQL": [],
    "TREE_SQL": ["1", "2"],
    "LOCATE_SQL": ["24.37", "88.60"],
    "BOUNDARY_LEVELS_SQL": [],
    "BOUNDARY_SQL": ["20015"],
    "CHILD_BOUNDARIES_SQL": ["20015", "'{union,pourashava}'", "0.0001"],
    # places
    "CATEGORIES_SQL": [],
    "PLACE_LIST_SQL": ["20015", "'education'", "NULL", "20", "0", "'relevance'"],
    "PLACE_COUNT_SQL": ["NULL", "NULL", "ARRAY['rajshahi','university']"],
    "PLACE_NEARBY_SQL": ["24.37", "88.60", "5000", "NULL", "30"],
    "PLACE_DETAIL_SQL": ["'university-of-rajshahi'"],
    "PLACE_GEO_SQL": ["20015", "NULL", "NULL", "NULL", "NULL", "NULL"],
    "PLACE_ID_SQL": ["'ruet'"],
    "EMERGENCY_SQL": [],
    # search
    "AREA_SEARCH_SQL": ["'rajsahi'", "'rajsahi'", "NULL", "NULL", "20"],
    "SUGGEST_SQL": ["'raj'", "'raj'", "8"],
    "AREA_DOCS_SQL": [],
    "PLACE_DOCS_SQL": [],
    # accounts
    "ME_SQL": ["1", "NULL"],
    "MY_REVIEWS_SQL": ["1"],
    "EVENTS_SQL": ["1"],
    # admin
    "ADMIN_STATS_SQL": [],
    "AUDIT_LIST_SQL": ["NULL", "NULL", "NULL", "10", "0"],
    "ADMIN_AREA_LIST_SQL": ["'union'", "NULL", "NULL", "'community'", "false", "'barishal/barguna'", "100", "0"],
    "ADMIN_AREA_SQL": ["30134"],
    "ADMIN_PLACE_LIST_SQL": ["NULL", "NULL", "NULL", "NULL", "NULL", "NULL", "50", "0"],
    "ADMIN_PLACE_SQL": ["1"],
    "ADMIN_SOURCES_SQL": [],
    "ADMIN_CONTRIBUTIONS_SQL": ["NULL", "NULL", "NULL", "50", "0"],
    "ADMIN_REVIEW_REPORTS_SQL": ["'open'"],
    "ADMIN_USERS_SQL": ["NULL", "NULL", "50", "0"],
    # quality
    "DUP_MATCH_SQL": ["'রাজশাহী বিশ্ববিদ্যালয়'", "'University of Rajshahi'", "1", "24.37", "88.637", "NULL"],
    "DUP_LIST_SQL": ["NULL", "50", "0"],
    "DUP_BLOCKING_SQL": ["1"],
    # open data
    "OD_AREAS_SQL": ["NULL", "1000", "0"],
    "OD_PLACES_SQL": ["NULL", "1000", "0"],
    "OD_SOURCES_SQL": [],
    "OD_KEYS_LIST_SQL": [],
}
EXPECT_ROWS = {  # minimum rows each statement must return on the seed (public = production-eligible only)
    "AREA_DETAIL_SQL": 1, "CHILDREN_SQL": 9, "LIST_SQL": 8, "PLACE_NEARBY_SQL": 4, "PLACE_DETAIL_SQL": 1, "EMERGENCY_SQL": 7,
    "AREA_SEARCH_SQL": 1, "CATEGORIES_SQL": 95, "BREADCRUMB_SQL": 4, "PLACE_LIST_SQL": 2, "PLACE_COUNT_SQL": 1, "AREA_DOCS_SQL": 95,
    "PLACE_GEO_SQL": 5, "PLACE_DOCS_SQL": 5, "TREE_SQL": 73, "LOCATE_SQL": 1, "BOUNDARY_SQL": 1, "CHILD_BOUNDARIES_SQL": 80, "SUGGEST_SQL": 1,
    "ADMIN_STATS_SQL": 1, "ADMIN_AREA_LIST_SQL": 8, "ADMIN_AREA_SQL": 1, "ADMIN_PLACE_LIST_SQL": 8, "ADMIN_PLACE_SQL": 1, "ADMIN_SOURCES_SQL": 20,
    "PLACE_ID_SQL": 1, "DUP_MATCH_SQL": 1, "OD_AREAS_SQL": 95, "OD_PLACES_SQL": 5, "OD_SOURCES_SQL": 5,
}

consts = {}
for f in SRC.rglob("*.ts"):
    for name, body in CONST_RE.findall(f.read_text(encoding="utf-8")):
        consts[name] = body

def expand(body, depth=0):
    return re.sub(r"\$\{(\w+)\}", lambda m: expand(consts[m.group(1)], depth + 1), body)

url = os.environ.get("DATABASE_URL", "postgres://elaka360:elaka360@localhost:5432/elaka360")
failures = 0
for name, params in PARAMS.items():
    if name not in consts:
        print(f"MISSING  {name}"); failures += 1; continue
    sql = expand(consts[name])
    exe = f"EXECUTE q({','.join(params)})" if params else "EXECUTE q"
    cmd = ["psql", url, "-v", "ON_ERROR_STOP=1", "-qAt", "-c", f"PREPARE q AS {sql}", "-c", exe]
    r = subprocess.run(cmd, capture_output=True, text=True)
    rows = [l for l in r.stdout.splitlines() if l.strip()]
    need = EXPECT_ROWS.get(name, 0)
    ok = r.returncode == 0 and len(rows) >= need
    print(f"{'OK  ' if ok else 'FAIL'}     {name:28s} rows={len(rows)}{'' if ok else ' (need ' + str(need) + ') ' + r.stderr.strip()[:300]}")
    failures += 0 if ok else 1
sys.exit(1 if failures else 0)
