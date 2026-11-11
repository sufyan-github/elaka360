#!/usr/bin/env python3
"""BBS Population and Housing Census 2022 — Rajshahi Division (8 districts).

Downloads from bbs.gov.bd (Census 2022 publication page) and rebuilds:

  raw/c01_rajshahi_division.csv            Community Report Table C-01 rows (all 8 districts, every geocoded unit
                                           down to village/mahalla) — filtered excerpt of the BBS Excel files
  raw/district_report_key_findings.txt     "Key Findings" excerpt (administrative units, area, population, density)
                                           of each District Report PDF, with PDF page numbers
  raw/union_statistics_D01.txt             Table D01 rows for Rajshahi Division from the "Union Statistics" PDF
  areas.csv, facts.csv                     normalised output (see data/sources/COLLECTION_FORMAT.md)

Big downloads (≈ 300 MB: 8 district-report PDFs, 8 community Excel files, the Union Statistics PDF) are kept in a
cache directory outside the repository (--cache). `--offline` rebuilds areas.csv / facts.csv from raw/ only.

Only stdlib + requests. PDF text needs `pdftotext` (poppler); without it the committed raw/ excerpts are used.

Many *.gov.bd servers do not send the Sectigo intermediate certificate. Instead of disabling verification we download
the intermediate from the URL in the server certificate's Authority Information Access extension and append it to
the normal CA bundle in a temporary file. The intermediate is only accepted by TLS if it chains to a trusted root.
"""
import argparse, atexit, csv, hashlib, html, io, json, os, re, shutil, ssl, subprocess, sys, tempfile, time, zipfile
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
KEY = "BBS_CENSUS_2022"
UA = "Elaka360-data-pipeline (research; contact via repository)"
DELAY = 1.3  # seconds between requests to the same host
AIA_INTERMEDIATE = "http://crt.sectigo.com/SectigoPublicServerAuthenticationCADVR36.crt"
LISTING = "https://bbs.gov.bd/pages/static-pages/6922e073933eb65569e27220"  # "জনশুমারি ও গৃহগণনা ২০২২" page
DIVISION_CODE = "50"
DIVISION = "Rajshahi"

# (name used in outputs, label on the BBS page, 2022 district geocode)
DISTRICTS = [
    ("Rajshahi", "RAJSHAHI", "81"), ("Natore", "NATORE", "69"), ("Naogaon", "NAOGAON", "64"),
    ("Pabna", "PABNA", "76"), ("Sirajganj", "SIRAJGANJ", "88"), ("Bogura", "BOGURA", "10"),
    ("Chapainawabganj", "CHAPAI NAWABGANJ", "70"), ("Joypurhat", "JOYPURHAT", "38"),
]

# URLs as resolved on 2026-11-12; used when the listing page cannot be parsed.
OS = "https://objectstorage.ap-dcc-gazipur-1.oraclecloud15.com/n/axvjbnqprylg/b/V2Ministry/o/office-bbs/"
PINNED = {
    "union_statistics": OS + "2024/12/f376ca7e7ee5405f8311de650415b9d8.pdf",
    "community_xlsx": {
        "Rajshahi": OS + "2024/12/3c3b94e632604786bfc0b4a3a4872208.xlsx",
        "Natore": OS + "2024/12/e0349f833a4a45baafa46d1bb562b908.xlsx",
        "Naogaon": OS + "2024/12/34e059e2210243cbbbbdd3142b882ba1.xlsx",
        "Pabna": OS + "2024/12/0b82f91e54084e6ab16100f6bf808c19.xlsx",
        "Sirajganj": OS + "2024/12/b351a354bf3949dab5b3d936c55c60ce.xlsx",
        "Bogura": OS + "2024/12/b63c65a7d6c24ee3b854881f0a8d506d.xlsx",
        "Chapainawabganj": OS + "2024/12/9fd9b896e2da4e1b9fc7d163490ba81d.xlsx",
        "Joypurhat": OS + "2024/12/98d23819d1764f3da7dc257e1f498a34.xlsx",
    },
    "district_page": {
        "Rajshahi": "https://bbs.gov.bd/pages/files/6a097f27af5b16b9ec4060f9",
        "Natore": "https://bbs.gov.bd/pages/files/6a097f68f570c41f02eb7470",
        "Naogaon": "https://bbs.gov.bd/pages/files/6a7050df33abb83ff10d065a",
        "Pabna": "https://bbs.gov.bd/pages/files/6a097fb604d89a37d7fa434f",
        "Sirajganj": "https://bbs.gov.bd/pages/files/6a097ffbfa5a21e711e53b6b",
        "Bogura": "https://bbs.gov.bd/pages/files/6a0980679da92ab7e499678b",
        "Chapainawabganj": "https://bbs.gov.bd/pages/files/6a0980c1ad0e9a31cc2598ae",
        "Joypurhat": "https://bbs.gov.bd/pages/files/6a098145af5b16b9ec40632d",
    },
    "district_pdf": {
        "Rajshahi": OS + "2026/4/c712cc05-e861-40c1-8a1f-ae765cec9f78.pdf",
        "Natore": OS + "2026/4/9818a50f-aa97-4183-9914-6b63de820ec4.pdf",
        "Naogaon": OS + "2026/7/d3ce217c-1df1-4a3a-b968-be2cff37b01f.pdf",
        "Pabna": OS + "2026/4/6112b236-698c-4a44-9b54-0f23e04a803c.pdf",
        "Sirajganj": OS + "2026/4/846d588b-a88f-4e17-b951-d81ae5bbf53f.pdf",
        "Bogura": OS + "2026/4/3d8572c6-d763-467a-a050-99ebfa7b4cdb.pdf",
        "Chapainawabganj": OS + "2026/4/ca335923-8434-424e-a0f0-b166e5ec6e81.pdf",
        "Joypurhat": OS + "2026/4/bfd5f614-0469-4518-aab7-6d1fa6775622.pdf",
    },
}


# ------------------------------------------------------------------ http

class Fetcher:
    def __init__(self, cache):
        self.cache = cache
        self.last = {}
        self.s = requests.Session()
        self.s.headers["User-Agent"] = UA
        self.verify = self._bundle()

    def _wait(self, url):
        host = urlparse(url).netloc
        dt = time.time() - self.last.get(host, 0)
        if dt < DELAY:
            time.sleep(DELAY - dt)
        self.last[host] = time.time()

    def _bundle(self):
        """System/certifi roots + the Sectigo DV R36 intermediate (fetched from its AIA URL) in a temp file."""
        try:
            import certifi
            base = certifi.where()
        except ImportError:
            p = ssl.get_default_verify_paths()
            base = p.cafile or p.openssl_cafile
            if not base or not os.path.isfile(base):
                base = "/etc/ssl/certs/ca-certificates.crt"
        try:
            self._wait(AIA_INTERMEDIATE)
            der = self.s.get(AIA_INTERMEDIATE, timeout=60).content
            pem = ssl.DER_cert_to_PEM_cert(der)
        except Exception as e:  # noqa: BLE001
            print(f"warning: could not fetch intermediate certificate ({e}); using default CA bundle", file=sys.stderr)
            return True
        fd, path = tempfile.mkstemp(prefix="bbs_ca_", suffix=".pem")
        with os.fdopen(fd, "w") as f:
            f.write(open(base).read().rstrip("\n") + "\n" + pem)
        atexit.register(lambda: os.path.exists(path) and os.remove(path))
        return path

    def text(self, url):
        self._wait(url)
        r = self.s.get(url, timeout=90, verify=self.verify)
        r.raise_for_status()
        r.encoding = "utf-8"
        return r.text

    def file(self, url, name, refresh=False):
        path = os.path.join(self.cache, name)
        if os.path.isfile(path) and not refresh:
            return path
        self._wait(url)
        with self.s.get(url, timeout=600, stream=True, verify=self.verify) as r:
            r.raise_for_status()
            with open(path + ".part", "wb") as f:
                for chunk in r.iter_content(1 << 16):
                    f.write(chunk)
        os.replace(path + ".part", path)
        print(f"downloaded {name} ({os.path.getsize(path):,} bytes)")
        return path


def resolve(fx):
    """Current download URLs from the BBS Census 2022 page; falls back to PINNED per item."""
    out = json.loads(json.dumps(PINNED))
    try:
        page = fx.text(LISTING)
    except Exception as e:  # noqa: BLE001
        print(f"warning: listing page failed ({e}); using pinned URLs", file=sys.stderr)
        return out
    body = " ".join(re.findall(r"<rt-renderer[^>]*>(.*?)</rt-renderer>", page, re.S))
    anchors = [(m.group(1), " ".join(html.unescape(re.sub(r"<[^>]+>", " ", m.group(2))).split()))
               for m in re.finditer(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', body, re.S)]
    for href, txt in anchors:
        if txt.strip().lower() == "population and housing census 2022 : union statistics":
            out["union_statistics"] = href
    flat = re.sub(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
                  lambda m: " {%s|%s} " % (re.sub(r"<[^>]+>", "", m.group(2)).strip(), m.group(1)), body)
    flat = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", flat)).split())
    for name, label, _ in DISTRICTS:
        m = re.search(re.escape(label) + r"\s*:\s*\{PDF\|([^}]+)\}\s*,\s*\{Excel\|([^}]+)\}", flat)
        if m:
            out["community_xlsx"][name] = m.group(2)
        for href, txt in anchors:  # district series: anchor text is exactly the label
            if txt == label and "/pages/files/" in href:
                out["district_page"][name] = href
                break
    for name, _, _ in DISTRICTS:
        try:
            t = fx.text(out["district_page"][name])
            seg = t[t.find("content-files"):][:6000]
            links = re.findall(r'href="(https://objectstorage[^"]+\.pdf)"', seg)
            if links:
                out["district_pdf"][name] = links[0]
        except Exception as e:  # noqa: BLE001
            print(f"warning: district page {name} failed ({e}); using pinned PDF URL", file=sys.stderr)
    return out


# ------------------------------------------------------------------ xlsx (stdlib)

NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}


def _col(ref):
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group(0):
        n = n * 26 + ord(ch) - 64
    return n - 1


def read_sheet(path, sheet):
    z = zipfile.ZipFile(path)
    ss = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
            ss.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    rels = {r.get("Id"): r.get("Target") for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))}
    for sh in wb.find("m:sheets", NS):
        if sh.get("name") != sheet:
            continue
        tgt = rels[sh.get("{%s}id" % NS["r"])].lstrip("/")
        tgt = tgt if tgt.startswith("xl/") else "xl/" + tgt
        rows = []
        for row in ET.fromstring(z.read(tgt)).iter("{%s}row" % NS["m"]):
            vals = {}
            for c in row.findall("m:c", NS):
                v, t = c.find("m:v", NS), c.get("t")
                if t == "inlineStr":
                    val = "".join(x.text or "" for x in c.iter("{%s}t" % NS["m"]))
                elif v is None:
                    continue
                elif t == "s":
                    val = ss[int(v.text)]
                else:
                    val = v.text
                vals[_col(c.get("r"))] = val
            if vals:
                rows.append([vals.get(i, "") for i in range(max(vals) + 1)])
        return rows
    raise KeyError(sheet)


C01_COLS = ["district_code", "city_corporation_code", "upazila_thana_code", "paurashava_code", "union_ward_code",
            "mauza_code", "village_mahalla_code", "name", "hh_total", "hh_general", "hh_institutional", "hh_others",
            "pop_total", "pop_male", "pop_female", "pop_hijra", "sex_ratio"]


def c01_rows(path):
    """Table C-01 as dicts with C01_COLS keys (header-driven; Rajshahi's sheet has an extra City Corporation column)."""
    rows = read_sheet(path, "C-01")
    hi = next(i for i, r in enumerate(rows) if "District" in [c.strip() for c in r])
    h = [c.strip() for c in rows[hi]]
    idx = {"district_code": h.index("District"),
           "city_corporation_code": h.index("City Corporation") if "City Corporation" in h else None,
           "upazila_thana_code": h.index("Upazila/Thana"), "paurashava_code": h.index("Paurashava"),
           "union_ward_code": h.index("Union/Ward"), "mauza_code": h.index("Mauza"),
           "village_mahalla_code": h.index("Village/Mahalla")}
    nm = next(i for i, c in enumerate(h) if c.startswith("Administrative Unit"))
    out = []
    for r in rows[hi + 3:]:
        r = [str(x).strip() for x in r] + [""] * (nm + 10)
        if not r[idx["district_code"]]:
            continue
        d = {k: (r[i] if i is not None else "") for k, i in idx.items()}
        d["name"] = r[nm]
        for j, k in enumerate(C01_COLS[8:], start=1):
            d[k] = r[nm + j]
        out.append(d)
    return out


# ------------------------------------------------------------------ pdf text

def pdf_pages(path):
    if not shutil.which("pdftotext"):
        raise RuntimeError("pdftotext not installed")
    txt = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, check=True).stdout
    return txt.decode("utf-8", "replace").split("\f")


def key_findings_excerpt(pages, district):
    """Lines of the Key Findings table from 'Administrative Units' to 'Sex Ratio', with PDF page markers."""
    out, state, cur = [], 0, None  # state 0 = not started, 1 = inside, 2 = done
    for pno, p in enumerate(pages, 1):
        if state == 2:
            break
        for ln in p.splitlines():
            if state == 0 and re.match(r"^\s*0?1\s+Administrative Units?\s*$", ln):
                state = 1
            if state == 1 and cur != pno:
                cur = pno
                out.append(f"## PDF page {pno}")
            if state == 1:
                if ln.strip():
                    out.append(ln.rstrip())
                if re.match(r"^\s*12\s+Sex Ratio", ln):
                    state = 2
                    break
    # narrative "The total area of the district is X square kilometer"
    for pno, p in enumerate(pages, 1):
        flat = " ".join(re.sub(r"[^\x20-\x7e]", " ", p).split())
        m = re.search(r"total area of the district is ([\d,\.]+) square", flat)
        if m:
            out.append(f"## PDF page {pno} (narrative): total area of the district is {m.group(1)} square kilometer")
            break
    return out


def union_statistics_d01(pages):
    out, seen = [], False
    for pno, p in enumerate(pages, 1):
        if re.search(r"Table D01\.\s+Administrative Unit", p) and "Geo Code" in p:
            seen = True
        if not seen:
            continue
        for ln in p.splitlines():
            if re.match(r"^\s*50\s+(\d\d\s+)?\S", ln):
                out.append(f"p{pno}\t{' '.join(ln.split())}")
        if len(out) >= 9:
            break
    return out


# ------------------------------------------------------------------ build

def strip_generic(name):
    return re.sub(r"\s+(Union|Upazila|Paurashava)$", "", name.strip())


def classify(r):
    if r["village_mahalla_code"]:
        return "village"
    if r["mauza_code"]:
        return "mouza"
    if r["union_ward_code"]:
        if r["paurashava_code"] or r["city_corporation_code"]:
            return "ward"
        # Bogura Cantonment is printed in the Union/Ward column (code 998) but is not a union parishad
        return "cantonment" if "cantonment" in r["name"].lower() else "union"
    if r["paurashava_code"]:
        return "pourashava"
    if r["upazila_thana_code"]:
        return "thana" if r["city_corporation_code"] else "upazila"
    if r["city_corporation_code"]:
        return "city_corporation"
    return "district"


def geocode(r):
    parts = [DIVISION_CODE, r["district_code"], r["city_corporation_code"], r["upazila_thana_code"],
             r["paurashava_code"], r["union_ward_code"], r["mauza_code"]]
    return "-".join(p for p in parts if p)


def build(urls):
    c01 = list(csv.DictReader(open(os.path.join(RAW, "c01_rajshahi_division.csv"), encoding="utf-8")))
    kf = open(os.path.join(RAW, "district_report_key_findings.txt"), encoding="utf-8").read()
    d01 = open(os.path.join(RAW, "union_statistics_D01.txt"), encoding="utf-8").read().splitlines()

    areas, facts = [], []

    def fact(level, name, dist, upz, code, f, v, unit, basis, url, notes):
        if v in ("", None):
            return
        facts.append(dict(entity_level=level, entity_name_en=name, district_en=dist, upazila_en=upz, code=code,
                          fact=f, value=v, unit=unit, basis=basis, year="2022", source_key=KEY, source_url=url,
                          notes=notes))

    # ---- Community Report Table C-01
    by_dist = {}
    for r in c01:
        by_dist.setdefault(r["district_file"], []).append(r)
    for dname, _, dcode in DISTRICTS:
        rows = by_dist[dname]
        url = urls["community_xlsx"][dname]
        src = f"Community Report {dname} 2022 (Excel), sheet C-01"
        units, last = [], None
        upz_name, cc_name, paura_names = {}, {}, {}
        for r in rows:
            if r["name"] in ("Rural", "Urban"):
                last.setdefault("loc", {})[r["name"]] = r
                continue
            r = dict(r)
            r["level"] = classify(r)
            units.append(r)
            last = r
            if r["level"] == "upazila":
                upz_name[r["upazila_thana_code"]] = strip_generic(r["name"])
            if r["level"] == "thana":
                upz_name[r["upazila_thana_code"]] = r["name"].strip()
            if r["level"] == "city_corporation":
                cc_name[r["city_corporation_code"]] = r["name"].strip()
        def ukey(x):
            return (x["city_corporation_code"], x["upazila_thana_code"], x["paurashava_code"], x["union_ward_code"])
        parent_of = {ukey(x): x for x in units if x["level"] in ("union", "ward", "cantonment")}
        # paurashavas that are split across upazilas (same code under 2 upazilas)
        pcount = {}
        for u in units:
            if u["level"] == "pourashava":
                pcount[u["paurashava_code"]] = pcount.get(u["paurashava_code"], 0) + 1

        for u in units:
            lvl = u["level"]
            if lvl == "village":
                continue
            upz = upz_name.get(u["upazila_thana_code"], "") if lvl not in ("district", "city_corporation") else ""
            name = u["name"].strip() if lvl in ("district", "city_corporation", "thana", "ward") \
                else strip_generic(u["name"])
            if lvl == "mouza":  # C-01 footnote: "Asterisk (*) denotes Mauza" — a row marker, not part of the name
                name = u["name"].strip().rstrip("*").strip()
            code = geocode(u)
            note = []
            if "(Part)" in u["name"] or "(part)" in u["name"].lower():
                note.append("unit split across parents; figures are for this part only")
            if lvl == "pourashava" and pcount.get(u["paurashava_code"], 0) > 1:
                note.append(f"paurashava listed under {pcount[u['paurashava_code']]} upazilas; figures are for the part in {upz}")
            if lvl == "cantonment":
                note.append("printed in the Union/Ward column of C-01 with a union-style code; not a union parishad "
                            "(the District Report's union total counts it, Union Statistics Table D01 does not)")
            # parent
            if lvl == "district":
                parent = ("division", DIVISION)
            elif lvl == "city_corporation":
                parent = ("district", dname)
            elif lvl == "thana":
                parent = ("city_corporation", cc_name.get(u["city_corporation_code"], ""))
            elif lvl == "upazila":
                parent = ("district", dname)
            elif lvl == "pourashava":
                parent = ("upazila", upz)
            elif lvl in ("union", "cantonment"):
                parent = ("upazila", upz)
            elif lvl == "ward":
                if u["paurashava_code"]:
                    pn = next((strip_generic(x["name"]) for x in units if x["level"] == "pourashava"
                               and x["upazila_thana_code"] == u["upazila_thana_code"]
                               and x["paurashava_code"] == u["paurashava_code"]), "")
                    parent = ("pourashava", pn)
                else:
                    parent = ("thana", upz)
            else:  # mouza
                pr = parent_of.get(ukey(u))
                parent = (pr["level"], pr["name"].strip() if pr["level"] == "ward" else strip_generic(pr["name"])) if pr else ("", "")
            areas.append(dict(level=lvl, name_en=name, name_bn="", parent_level=parent[0], parent_name_en=parent[1],
                              parent_name_bn="", district_en=dname, upazila_en=upz, code=code,
                              code_scheme="BBS_GEOCODE_2022", website="", lat="", lon="", source_key=KEY,
                              source_url=url, notes="; ".join(note + ["Table C-01"] + ([f"printed name '{u['name'].strip()}'"]
                                                                   if u["name"].strip() != name else []))))
            if lvl == "mouza":
                continue
            n = "; ".join(note + [src])
            fact(lvl, name, dname, upz, code, "population", u["pop_total"], "persons", "enumerated", url,
                 n + "; final enumerated count incl. floating population (not PEC-adjusted)")
            fact(lvl, name, dname, upz, code, "households", u["hh_total"], "households", "enumerated", url,
                 n + "; all households except floating households")
            if lvl in ("district", "city_corporation", "thana", "upazila", "pourashava", "union", "cantonment"):
                fact(lvl, name, dname, upz, code, "population_male", u["pop_male"], "persons", "enumerated", url, n)
                fact(lvl, name, dname, upz, code, "population_female", u["pop_female"], "persons", "enumerated", url, n)
                fact(lvl, name, dname, upz, code, "population_hijra", u["pop_hijra"], "persons", "enumerated", url, n)
            if lvl in ("district", "upazila", "union"):
                for loc in ("Rural", "Urban"):
                    x = (u.get("loc") or {}).get(loc)
                    if x:
                        fact(lvl, name, dname, upz, code, f"population_{loc.lower()}", x["pop_total"], "persons",
                             "enumerated", url, n + f"; '{loc}' row (2022 urban = city corp., cantonment, paurashava, "
                             "growth centre, upazila HQ)")
            # derived counts per upazila / city corporation / thana / district / paurashava
            if lvl in ("upazila", "city_corporation", "thana", "district", "pourashava"):
                def inside(x):
                    if lvl == "district":
                        return True
                    if lvl == "city_corporation":
                        return x["city_corporation_code"] == u["city_corporation_code"]
                    if lvl == "pourashava":
                        return (x["upazila_thana_code"] == u["upazila_thana_code"]
                                and x["paurashava_code"] == u["paurashava_code"])
                    return (x["upazila_thana_code"] == u["upazila_thana_code"]
                            and x["city_corporation_code"] == u["city_corporation_code"])
                sub = [x for x in units if inside(x)]
                dn = (f"{src}; counted from the geocoded rows listed (derived, not a printed total)")
                if lvl == "pourashava":
                    fact(lvl, name, dname, upz, code, "ward_count",
                         str(len([x for x in sub if x["level"] == "ward"])), "wards", "derived", url, n + "; " + dn)
                    continue
                unions = [x for x in sub if x["level"] == "union"]
                urban_mix = {(x["city_corporation_code"], x["upazila_thana_code"], x["mauza_code"])
                             for x in sub if x["level"] == "mouza"}
                vill = {(x["upazila_thana_code"], x["union_ward_code"], x["mauza_code"], x["village_mahalla_code"])
                        for x in rows if x["name"] not in ("Rural", "Urban") and x["village_mahalla_code"]
                        and not x["paurashava_code"] and not x["city_corporation_code"] and inside(x)}
                mah = {(x["city_corporation_code"], x["upazila_thana_code"], x["paurashava_code"], x["union_ward_code"],
                        x["mauza_code"], x["village_mahalla_code"])
                       for x in rows if x["name"] not in ("Rural", "Urban") and x["village_mahalla_code"]
                       and (x["paurashava_code"] or x["city_corporation_code"]) and inside(x)}
                if lvl in ("upazila", "district"):
                    fact(lvl, name, dname, upz, code, "union_count", str(len(unions)), "unions", "derived", url,
                         n + "; " + dn)
                    paur = {x["paurashava_code"] for x in sub if x["level"] == "pourashava"}
                    fact(lvl, name, dname, upz, code, "pourashava_count", str(len(paur)), "paurashavas", "derived",
                         url, n + "; " + dn + ("; includes paurashava(s) split with another upazila"
                                               if any(pcount.get(p, 0) > 1 for p in paur) else ""))
                    others = [x["name"] for x in sub if x["level"] == "cantonment"]
                    if others:
                        fact(lvl, name, dname, upz, code, "cantonment_count", str(len(others)), "cantonments",
                             "derived", url, n + "; " + dn + "; listed in the Union/Ward column: " + ", ".join(others))
                if lvl in ("city_corporation", "thana"):
                    fact(lvl, name, dname, upz, code, "ward_count",
                         str(len({x["union_ward_code"] for x in sub if x["level"] == "ward"})), "wards", "derived",
                         url, n + "; " + dn + "; wards marked (Part) are shared with another thana")
                fact(lvl, name, dname, upz, code, "mouza_count", str(len(urban_mix)), "mouzas", "derived", url,
                     n + "; " + dn + "; distinct mauza codes with a C-01 row (BBS district totals also count "
                     "depopulated mauzas, so these can be lower)")
                fact(lvl, name, dname, upz, code, "village_count", str(len(vill)), "villages", "derived", url,
                     n + "; " + dn + "; distinct village codes in rural unions")
                fact(lvl, name, dname, upz, code, "mahalla_count", str(len(mah)), "mahallas", "derived", url,
                     n + "; " + dn + "; distinct mahalla codes in paurashava / city corporation wards")

    # ---- District Report key findings
    blocks = re.split(r"^=== ", kf, flags=re.M)[1:]
    labels = {"City Corporation": ("city_corporation_count", "city corporations"),
              "Upazila": ("upazila_count", "upazilas"), "Metro Thana": ("metro_thana_count", "thanas"),
              "Paurashava": ("pourashava_count", "paurashavas"), "City Ward": ("city_ward_count", "wards"),
              "Paura Ward": ("paura_ward_count", "wards"), "Union": ("union_count", "unions"),
              "Mauza": ("mouza_count", "mouzas"), "Village": ("village_count", "villages"),
              "Mahalla": ("mahalla_count", "mahallas")}
    for b in blocks:
        head, *lines = b.splitlines()
        dname = head.split("|")[0].strip()
        url = urls["district_pdf"][dname]
        page = ""
        sec, pending = None, False
        vals = {}
        for ln in lines:
            m = re.match(r"## PDF page (\d+)", ln)
            if m and "narrative" not in ln:
                page = page or m.group(1)
                continue
            if re.match(r"^\s*\d\d\s*$", ln):  # section number printed on its own line (Bogura, Chapainawabganj)
                sec, pending = None, True
                continue
            if pending and re.match(r"^\s*[A-Za-z][A-Za-z ()\.\-]*\d?\s*$", ln):
                sec, pending = ln.strip(), False
                continue
            m = re.match(r"\s*(\d\d)\s+(.+?)\s*$", ln)
            if m and not re.search(r"\d{3,}", m.group(2)):
                sec, pending = m.group(2), False
                continue
            # label, optional footnote digit glued to it (e.g. "Mauza1"), then the 2022 value
            m = re.match(r"^\s+([A-Za-z][A-Za-z \-]*?[A-Za-z])\d?\s{2,}([\d][\d ,\.]*?)(\s{2,}|$)", ln)
            if m:
                vals.setdefault((sec, m.group(1).strip()), m.group(2).replace(" ", "").replace(",", ""))
        # does the table belong to this district? (Naogaon's report prints Jamalpur's key findings)
        own = any(k[1] == dname or (dname == "Chapainawabganj" and k[1].startswith("Chapai")) for k in vals)
        base_note = f"District Report: {dname} (June 2024), Key Findings table, PDF page {page}"
        if not own:
            print(f"warning: key findings in the {dname} report belong to another district; skipped", file=sys.stderr)
        else:
            for (sec, lab), v in vals.items():
                if sec and sec.startswith("Administrative Unit") and lab in labels:
                    f, unit = labels[lab]
                    fact("district", dname, dname, "", dcode_of(dname), f, str(int(v)), unit, "as stated", url,
                         base_note + "; 2022 column" + ("; includes populated and depopulated mauzas" if f == "mouza_count" else ""))
                if sec and sec.startswith("Area") and lab == dname:
                    fact("district", dname, dname, "", dcode_of(dname), "area_km2", v, "km2", "as stated", url, base_note)
                if sec and sec.startswith("Population Density") and lab == dname:
                    fact("district", dname, dname, "", dcode_of(dname), "population_density", v, "persons/km2",
                         "as stated", url, base_note + "; based on enumerated population")
        for ln in lines:
            m = re.match(r"## PDF page (\d+) \(narrative\): total area of the district is ([\d,\.]+)", ln)
            if m:
                fact("district", dname, dname, "", dcode_of(dname), "area_km2", m.group(2).replace(",", ""), "km2",
                     "as stated", url, f"District Report: {dname}, district profile narrative (English), PDF page "
                     f"{m.group(1)}" + ("" if own else "; key-findings table of this report shows another district"))

    # ---- Union Statistics Table D01
    us = urls["union_statistics"]
    cols = ["city_corporation_count", "metro_thana_count", "city_ward_count", "upazila_count", "pourashava_count",
            "paura_ward_count", "union_count", "mouza_count", "mahalla_count", "village_count", "households_all"]
    for ln in d01:
        if not ln.strip() or ln.startswith("#"):
            continue
        pg, row = ln.split("\t", 1)
        toks = row.split()
        if len(toks) < 3 or not re.fullmatch(r"\d\d", toks[1]):
            continue
        dc = toks[1]
        dname = next((n for n, _, c in DISTRICTS if c == dc), None)
        nums = [t for t in toks[2:] if re.fullmatch(r"[\d\.]+", t)]
        if not dname or len(nums) < 16:
            continue
        rec = dict(zip(cols, nums[:11]))
        note = (f"Population and Housing Census 2022: Union Statistics (June 2025), Table D01, PDF page {pg[1:]}"
                f"; printed district name '{' '.join(t for t in toks[2:] if not re.fullmatch(r'[\d.]+', t))}'")
        for f in ("upazila_count", "pourashava_count", "paura_ward_count", "union_count", "mouza_count",
                  "mahalla_count", "village_count"):
            unit = {"upazila_count": "upazilas", "pourashava_count": "paurashavas", "paura_ward_count": "wards",
                    "union_count": "unions", "mouza_count": "mouzas", "mahalla_count": "mahallas",
                    "village_count": "villages"}[f]
            fact("district", dname, dname, "", dcode_of(dname), f, rec[f], unit, "as stated", us, note)
        fact("district", dname, dname, "", dcode_of(dname), "households", rec["households_all"], "households",
             "enumerated", us, note + "; all households incl. floating households")
        fact("district", dname, dname, "", dcode_of(dname), "population", nums[15], "persons", "enumerated", us, note)

    write_csv(os.path.join(HERE, "areas.csv"), areas,
              ["level", "name_en", "name_bn", "parent_level", "parent_name_en", "parent_name_bn", "district_en",
               "upazila_en", "code", "code_scheme", "website", "lat", "lon", "source_key", "source_url", "notes"])
    write_csv(os.path.join(HERE, "facts.csv"), facts,
              ["entity_level", "entity_name_en", "district_en", "upazila_en", "code", "fact", "value", "unit",
               "basis", "year", "source_key", "source_url", "notes"])
    print(f"areas.csv: {len(areas)} rows; facts.csv: {len(facts)} rows")


def dcode_of(dname):
    return f"{DIVISION_CODE}-" + next(c for n, _, c in DISTRICTS if n == dname)


def write_csv(path, rows, cols):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default=os.path.join(tempfile.gettempdir(), "elaka360_bbs_census_2022"),
                    help="directory for the large downloads (not committed)")
    ap.add_argument("--offline", action="store_true", help="rebuild areas.csv/facts.csv from raw/ only")
    ap.add_argument("--refresh", action="store_true", help="re-download files already in the cache")
    a = ap.parse_args()
    os.makedirs(RAW, exist_ok=True)
    urls_path = os.path.join(RAW, "resolved_urls.json")
    if a.offline:
        build(json.load(open(urls_path, encoding="utf-8")))
        return
    os.makedirs(a.cache, exist_ok=True)
    fx = Fetcher(a.cache)
    urls = resolve(fx)

    # Community Report Excel → raw/c01_rajshahi_division.csv
    with open(os.path.join(RAW, "c01_rajshahi_division.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["district_file"] + C01_COLS, lineterminator="\n")
        w.writeheader()
        for dname, _, dcode in DISTRICTS:
            p = fx.file(urls["community_xlsx"][dname], f"xlsx_{dname}.xlsx", a.refresh)
            rows = c01_rows(p)
            assert rows and rows[0]["district_code"] == dcode, (dname, rows[:1])
            for r in rows:
                w.writerow({"district_file": dname, **r})

    have_pdftotext = bool(shutil.which("pdftotext"))
    if not have_pdftotext:
        print("warning: pdftotext missing — keeping committed raw/ PDF excerpts", file=sys.stderr)
    else:
        out = []
        for dname, _, _ in DISTRICTS:
            p = fx.file(urls["district_pdf"][dname], f"district_{dname}.pdf", a.refresh)
            out.append(f"=== {dname} | {urls['district_pdf'][dname]}")
            out += key_findings_excerpt(pdf_pages(p), dname)
        open(os.path.join(RAW, "district_report_key_findings.txt"), "w", encoding="utf-8").write("\n".join(out) + "\n")
        p = fx.file(urls["union_statistics"], "union_statistics.pdf", a.refresh)
        lines = union_statistics_d01(pdf_pages(p))
        open(os.path.join(RAW, "union_statistics_D01.txt"), "w", encoding="utf-8").write(
            f"# {urls['union_statistics']}\n# Table D01 rows for Rajshahi Division (geocode 50); pPAGE<TAB>row\n"
            + "\n".join(lines) + "\n")
    json.dump(urls, open(urls_path, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    build(urls)
    # checksums for SOURCE.json
    for rel in ["areas.csv", "facts.csv"] + ["raw/" + x for x in sorted(os.listdir(RAW))]:
        h = hashlib.sha256(open(os.path.join(HERE, rel), "rb").read()).hexdigest()
        print(f"sha256 {rel} {h}")


if __name__ == "__main__":
    main()
