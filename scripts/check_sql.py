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
    "AREA_DETAIL_SQL": ["'rajshahi/rajshahi'"],
    "AREA_BY_ID_PATH_SQL": ["20015"],
    "BREADCRUMB_SQL": ["40134"],
    "CHILDREN_SQL": ["20015", "NULL"],
    "DESCENDANT_COUNTS_SQL": ["10002"],
    "PLACE_COUNTS_SQL": ["20015"],
    "NATIONAL_PLACE_COUNTS_SQL": [],
    "LIST_SQL": ["'district'", "10002", "100", "0"],
    "NATIONAL_STATS_SQL": [],
    "CATEGORIES_SQL": [],
    "PLACE_LIST_SQL": ["20015", "'education'", "NULL", "20", "0"],
    "PLACE_NEARBY_SQL": ["24.37", "88.60", "5000", "NULL", "30"],
    "PLACE_DETAIL_SQL": ["'university-of-rajshahi'"],
    "EMERGENCY_SQL": [],
    "AREA_SEARCH_SQL": ["'রাজশা'", "''"],
}
EXPECT_ROWS = {  # minimum rows each statement must return on the v0.1 seed
    "AREA_DETAIL_SQL": 1, "CHILDREN_SQL": 9, "LIST_SQL": 8, "PLACE_NEARBY_SQL": 4,
    "PLACE_DETAIL_SQL": 1, "EMERGENCY_SQL": 10, "AREA_SEARCH_SQL": 1, "CATEGORIES_SQL": 95,
    "BREADCRUMB_SQL": 5, "PLACE_LIST_SQL": 3,
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
