#!/usr/bin/env python3
"""Fetch bank branch/office phone lists from a division's district portals (default Rajshahi Division, DISTRICT_PORTAL_BANKS_RAJ_2026).

Usage: python3 fetch.py [--division rangpur] [--out DIR]  (rangpur -> DISTRICT_PORTAL_BANKS_RANG_2026)."""
# --- polite HTTP helper (copy this block into each fetch.py; stdlib + requests only) -----------------
# Many *.gov.bd servers send only their leaf certificate and omit the intermediate CA. Browsers fetch the
# missing intermediate via the certificate's AIA URL; we do the same explicitly: download the published
# intermediates from the CA and add them to certifi's bundle. TLS verification stays ON.
import os, time, tempfile, urllib.parse, urllib.robotparser
import requests

UA = "Elaka360-data-pipeline (research; contact via repository)"
INTERMEDIATES = [  # CA-published intermediates (AIA "CA Issuers" URLs) that some gov.bd hosts fail to send
    "http://crt.sectigo.com/SectigoPublicServerAuthenticationCADVR36.crt",
    "http://crt.sectigo.com/SectigoPublicServerAuthenticationCAOVR36.crt",
    "http://crt.sectigo.com/SSL2BUYEMEARSADomainValidationSecureServerCA.crt",
]
MIN_DELAY = 1.2  # seconds between requests to the same host

_last, _robots, _bundle = {}, {}, None
S = requests.Session()
S.headers["User-Agent"] = UA


def _der_to_pem(der):
    import base64
    b = base64.encodebytes(der).decode().replace("\n", "")
    return "-----BEGIN CERTIFICATE-----\n" + "\n".join(b[i:i + 64] for i in range(0, len(b), 64)) + "\n-----END CERTIFICATE-----\n"


def ca_bundle():
    global _bundle
    if _bundle:
        return _bundle
    import certifi
    pems = [open(certifi.where(), encoding="ascii").read()]
    for u in INTERMEDIATES:
        try:
            r = requests.get(u, timeout=30, headers={"User-Agent": UA})
            if r.ok:
                pems.append(r.content.decode() if r.content.startswith(b"-----") else _der_to_pem(r.content))
        except requests.RequestException:
            pass
        time.sleep(MIN_DELAY)
    fd, path = tempfile.mkstemp(suffix=".pem")
    with os.fdopen(fd, "w") as f:
        f.write("\n".join(pems))
    _bundle = path
    return path


def allowed(url):
    p = urllib.parse.urlsplit(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = get_raw(base + "/robots.txt")
            rp.parse(r.text.splitlines() if (r is not None and r.status_code == 200 and "html" not in r.headers.get("content-type", "")) else [])
        except Exception:
            rp.parse([])
        _robots[base] = rp
    return _robots[base].can_fetch(UA, url)


def get_raw(url, **kw):
    host = urllib.parse.urlsplit(url).netloc
    wait = MIN_DELAY - (time.time() - _last.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    try:
        return S.get(url, timeout=kw.pop("timeout", 60), verify=ca_bundle(), **kw)
    finally:
        _last[host] = time.time()


def get(url, retries=2, **kw):
    """Polite GET; returns Response or None (never raises)."""
    if not allowed(url):
        print("robots.txt disallows", url)
        return None
    for i in range(retries + 1):
        try:
            r = get_raw(url, **kw)
            if r.status_code < 500:
                return r
        except requests.RequestException as e:
            print("fetch failed", url, e)
        time.sleep(3 * (i + 1))
    return None
# --- end helper ---------------------------------------------------------------------------------------

# --- common utilities (stdlib only) -------------------------------------------------------------------
import csv, hashlib, html as _html, json, re, shutil, subprocess, sys, unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
PLACE_COLS = ["source_key", "source_id", "name_bn", "name_en", "category_key", "lat", "lon", "address", "district_en",
              "upazila_en", "phone", "website", "email", "opening_hours", "operator", "ownership", "extra_json",
              "source_url", "notes"]
FACT_COLS = ["entity_level", "entity_name_en", "district_en", "upazila_en", "code", "fact", "value", "unit", "basis",
             "year", "source_key", "source_url", "notes"]
_BN = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def nfc(s):
    return unicodedata.normalize("NFC", s or "").strip()


def asc(s):
    """Bangla digits -> ASCII digits."""
    return (s or "").translate(_BN)


def clean(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = _html.unescape(s).replace("\xa0", " ")
    return nfc(re.sub(r"\s+", " ", s))


def tables(html_text):
    """All <table>s of a page as lists of rows (lists of cleaned cell strings)."""
    out = []
    for t in re.findall(r"<table\b.*?</table>", html_text, flags=re.S | re.I):
        rows = []
        for tr in re.findall(r"<tr\b.*?</tr>", t, flags=re.S | re.I):
            cells = [clean(c) for c in re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", tr, flags=re.S | re.I)]
            if any(cells):
                rows.append(cells)
        out.append(rows)
    return out


def content_text(html_text):
    """Main content block of a national-portal (v2) page as text lines."""
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html_text, flags=re.S | re.I)
    s = re.sub(r"</(tr|p|div|li|h\d)>|<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</t[dh]>", " | ", s, flags=re.I)
    s = _html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\xa0", " ")
    lines = [nfc(re.sub(r"[ \t]+", " ", l)) for l in s.splitlines()]
    lines = [l for l in lines if l]
    try:
        a = next(i for i, l in enumerate(lines) if l.startswith("কন্টেন্ট:"))
        b = next(i for i, l in enumerate(lines) if i > a and "এই কনটেন্টটি শেয়ার" in l)
        return lines[a + 1:b]
    except StopIteration:
        return lines


def phone_norm(s):
    """ASCII digits, keep the source's grouping; several numbers joined with '; '."""
    s = asc(s)
    parts = [p.strip(" ,;/") for p in re.split(r"[,;/]|\s{2,}", s)]
    return "; ".join(p for p in parts if re.search(r"\d{4}", p))


def save_raw(name, content):
    RAW.mkdir(exist_ok=True)
    p = RAW / name
    p.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
    return p


def pdftotext(path, first=None, last=None, layout=True):
    """Text of a PDF via poppler's pdftotext if installed (optional dependency); None otherwise."""
    exe = shutil.which("pdftotext")
    if not exe:
        return None
    cmd = [exe] + (["-layout"] if layout else []) + (["-f", str(first)] if first else []) + (["-l", str(last)] if last else []) + [str(path), "-"]
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=300).stdout
    except Exception:
        return None


def write_csv(name, cols, rows):
    with open(HERE / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="raise")
        w.writeheader()
        for r in rows:
            w.writerow({c: ("" if r.get(c) is None else r.get(c)) for c in cols})
    print(f"wrote {name}: {len(rows)} rows")


def write_manifest(meta, files):
    hashes = {}
    for rel in files:
        p = HERE / rel
        if p.exists():
            hashes[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    meta = dict(meta, files=hashes)
    (HERE / "SOURCE.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote SOURCE.json")


def xj(d):
    d = {k: v for k, v in d.items() if v not in (None, "", [], {})}
    return json.dumps(d, ensure_ascii=False, separators=(",", ":")) if d else ""
# --- end common utilities -----------------------------------------------------------------------------

# --- DISTRICT_PORTAL_BANKS_RAJ_2026 -------------------------------------------------------------------
KEY = "DISTRICT_PORTAL_BANKS_RAJ_2026"
URLS = {
    "Rajshahi": "https://rajshahi.gov.bd/pages/static-pages/697f99c635ce18e1c06c092f",
    "Natore": "https://natore.gov.bd/pages/static-pages/697f805835ce18e1c06b8698",
    "Naogaon": "https://naogaon.gov.bd/pages/static-pages/ব্যাংক-6d69cb-697f79d835ce18e1c06b6047",
}
# Checked but not usable (names only / scraped map listing / attachment): kept for the report
OTHER = {
    "Bogura": "https://bogura.gov.bd/pages/static-pages/bank-6v4e4m-6a4f327012674831010d4193",
    "Joypurhat": "https://joypurhat.gov.bd/pages/static-pages/bank-5ur527-6a8539dc2adbdef9eae8d663",
    "Sirajganj": "https://sirajganj.gov.bd/pages/static-pages/697f79c035ce18e1c06b5572",
    "Chapainawabganj": "https://chapainawabganj.gov.bd/pages/static-pages/697f8d8c35ce18e1c06bd993",
    "Pabna (Sadar upazila)": "https://pabnasadar.pabna.gov.bd/pages/static-pages/697f895b35ce18e1c06b9d78",
}
POSTS = ("মহাব্যবস্থাপক", "উপ-মহাব্যবস্থাপক", "সহকারী মহাব্যবস্থাপক", "চেয়ারম্যান", "সচিব", "বৈদেশিক মুদ্রা")


def row(dist, sid, name, phone, url, extra, notes, upa=""):
    return dict(source_key=KEY, source_id=sid, name_bn=nfc(re.sub(r"\s+,", ",", name)), name_en="", category_key="finance.bank",
                district_en=dist, upazila_en=upa, phone=phone, extra_json=xj(extra), source_url=url, notes=notes)


def main():
    configure()
    if DIVISION != "rajshahi":
        return SITES[DIVISION]["run"]()
    places, n = [], 0
    pages = {}
    for d, u in URLS.items():
        r = get(u)
        if r is None or not r.ok:
            print("unavailable", u)
            continue
        pages[d] = r.text
        save_raw(f"{d.lower()}_banks.txt", "\n".join(content_text(r.text)))
    if "Rajshahi" in pages:
        bank, office, ownership = None, None, "public"
        for t in tables(pages["Rajshahi"]):
            for cells in t:
                cells = [c for c in cells if c]
                if not cells or cells[0] in ("ব্যাংকের নাম",):
                    continue
                if len(cells) == 1 and "ব্যাংক" in cells[0]:
                    bank, office = cells[0], None
                    continue
                if cells[0].startswith("রাজশাহী জেলার বেসরকারী"):
                    ownership = "private"
                    continue
                if len(cells) == 2 and "ব্যাংক" in cells[0]:
                    # private banks: one line per bank
                    n += 1
                    places.append(row("Rajshahi", f"dpb-raj-{n:03d}", cells[0], phone_norm(cells[1]), URLS["Rajshahi"],
                                      {"ownership_group": "বেসরকারী ব্যাংক"},
                                      "Rajshahi DC portal lists the bank 'in Rajshahi' with one number under 'রাজশাহী জেলার বেসরকারী ব্যাংকসমূহ'; branch not specified.", ""))
                    places[-1]["ownership"] = "private"
                    continue
                if bank and len(cells) == 2:
                    label, ph = cells[0], phone_norm(cells[1])
                    if label.startswith(POSTS):
                        if office is None:
                            n += 1
                            office = row("Rajshahi", f"dpb-raj-{n:03d}", bank, "", URLS["Rajshahi"], {"office_numbers": {}},
                                         "Bank's Rajshahi (zonal/regional/head) office numbers by post as listed on the DC portal; not a specific branch.")
                            places.append(office)
                        ex = json.loads(office["extra_json"] or "{}")
                        ex.setdefault("office_numbers", {})[label] = ph
                        office["extra_json"] = xj(ex)
                        office["phone"] = "; ".join(p for p in [office["phone"], ph] if p)
                    elif label.endswith("শাখা"):
                        n += 1
                        bname = re.sub(r",\s*রাজশাহী$", "", bank)
                        places.append(row("Rajshahi", f"dpb-raj-{n:03d}", f"{bname}, {label}", ph, URLS["Rajshahi"],
                                          {"bank_bn": bank, "branch_bn": label},
                                          "Name composed from the bank heading and the branch row of the DC portal table." +
                                          (" 'রম্নয়েট শাখা' is printed so (likely a typing error for 'রুয়েট শাখা', i.e. RUET)" if "রম্নয়েট" in label else "")))
    if "Natore" in pages:
        seen = {}
        for t in tables(pages["Natore"]):
            for cells in t:
                if len(cells) >= 2 and "ব্যাংক" in cells[0] and re.search(r"[০-৯0-9]{4}", cells[1]):
                    name, ph = nfc(re.sub(r"\s+,", ",", cells[0])), phone_norm(cells[1])
                    if name in seen:
                        p = seen[name]
                        p["phone"] += "; " + ph
                        p["notes"] += " Listed twice on the portal with different numbers."
                        continue
                    n += 1
                    p = row("Natore", f"dpb-nat-{n:03d}", name, ph, URLS["Natore"], {},
                            "From 'নাটোর শহরে অবস্থিত সরকারী ও বেসরকারী ব্যাংক শাখার তালিকা' (branches in Natore town; upazila_en = Natore Sadar "
                            "because the list is for the town). Number printed without area code.", upa="Natore Sadar")
                    seen[name] = p
                    places.append(p)
        # flag numbers shared by different rows
        by_phone = {}
        for p in places:
            if p["district_en"] == "Natore":
                for ph in p["phone"].split("; "):
                    by_phone.setdefault(ph, []).append(p)
        for ph, ps in by_phone.items():
            if len(ps) > 1:
                for p in ps:
                    p["notes"] += f" Number {ph} is also given for another row on the same page."
    if "Naogaon" in pages:
        for t in tables(pages["Naogaon"]):
            for cells in t:
                if len(cells) >= 3 and re.match(r"^[০-৯0-9]+$", cells[0]) and "ব্যাংক" in cells[1] + ("ব্যাংক" if "ইউসিবিএল" in cells[1] else ""):
                    n += 1
                    ex = {}
                    if "আঞ্চলিক কার্যালয়" in cells[1] or "প্রিন্সিপাল অফিস" in cells[1]:
                        ex["office_type"] = "regional/principal office"
                    places.append(row("Naogaon", f"dpb-nao-{n:03d}", cells[1], phone_norm(cells[2]), URLS["Naogaon"], ex,
                                      "From the Naogaon DC portal bank list (name and number as printed)."))
    write_csv("places.csv", PLACE_COLS, places)
    write_manifest(dict(
        key=KEY, division="rajshahi", kind="district_banks", name="District portals — bank branch/office phone lists (Rajshahi, Natore, Naogaon)",
        organization="Deputy Commissioner's offices (district portals)", source_type="government_portal", trust_level=4,
        urls=list(URLS.values()) + list(OTHER.values()), accessed=__import__("datetime").date.today().isoformat(), publication_date=None,
        license=None, license_url=None, attribution="District portals rajshahi.gov.bd, natore.gov.bd, naogaon.gov.bd",
        notes="No licence stated; lists are undated and partly old (landlines in pre-2020 formats, e.g. '(০৭২১) ৭৭২২৭৪'). No addresses, "
              "routing numbers or coordinates. Bogura, Joypurhat and Sirajganj portals list bank names only (no branches/contacts); "
              "Chapainawabganj's page is an unnamed file attachment; Pabna Sadar's page is a copied Google-Maps listing — none used."),
        ["places.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


# --- division selection (see ../DIVISIONS.md) --------------------------------------------------------------
# `python3 fetch.py` = `--division rajshahi`, output into this folder (unchanged behaviour). Other divisions write into
# their own folder (default: the sibling folder named per DIVISIONS.md) and never into the Rajshahi folder.
import argparse
DIVISION_CHOICES = ("rajshahi", "rangpur", "dhaka", "chattogram", "khulna", "barishal", "sylhet", "mymensingh")
DIVISION = "rajshahi"


def parse_division_args(folders):
    """Parse --division/--out. folders: division -> default output folder name (a sibling of this folder)."""
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().split("\n")[0])
    ap.add_argument("--division", default="rajshahi", choices=DIVISION_CHOICES)
    ap.add_argument("--out", help="output folder (default: this folder for rajshahi, ../<division folder> otherwise)")
    a = ap.parse_args()
    if a.division not in folders:
        raise SystemExit("this collector has no table for division %r yet (see DIVISIONS.md)" % a.division)
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.abspath(a.out or os.path.join(here, "..", folders[a.division]))
    if a.division != "rajshahi" and os.path.realpath(out) == os.path.realpath(here):
        raise SystemExit("refusing to write %s output into the Rajshahi folder %s" % (a.division, here))
    os.makedirs(out, exist_ok=True)
    return a.division, out


def write_division_manifest(out, meta):
    """SOURCE.json for a non-default division run: meta + sha256 of every data file in the output folder."""
    import hashlib as _h, json as _j
    files = {}
    for root, _, names in os.walk(out):
        for n in sorted(names):
            full = os.path.join(root, n)
            rel = os.path.relpath(full, out).replace(os.sep, "/")
            if rel in ("SOURCE.json", "fetch.py", "REPORT.md") or "__pycache__" in rel:
                continue
            files[rel] = _h.sha256(open(full, "rb").read()).hexdigest()
    m = dict(meta)
    m["files"] = dict(sorted(files.items()))
    with open(os.path.join(out, "SOURCE.json"), "w", encoding="utf-8") as f:
        f.write(_j.dumps(m, ensure_ascii=False, indent=2) + "\n")


# --- DISTRICT_PORTAL_BANKS_RANG_2026 (Rangpur Division) ---------------------------------------------------------------
RANG_KEY = "DISTRICT_PORTAL_BANKS_RANG_2026"
RANG_URLS = {
    "Panchagarh": "https://panchagarh.gov.bd/pages/static-pages/69773725c4774958d7c0d34e",
    "Nilphamari": "https://nilphamari.gov.bd/pages/static-pages/6977535ec4774958d7c1bad7",
    "Kurigram": "https://kurigram.gov.bd/pages/static-pages/6977614ec4774958d7c215ca",
}
# Checked but not usable (kept for the report / SOURCE.json urls)
RANG_OTHER = {
    "Rangpur": "https://rangpur.gov.bd/pages/static-pages/6977242ec4774958d7c0a048",          # bank names only (+ image)
    "Gaibandha": "https://gaibandha.gov.bd/pages/static-pages/69771ca6c4774958d7c05746",      # bank names only
    "Thakurgaon": "https://thakurgaon.gov.bd/pages/static-pages/697769a8c4774958d7c23719",    # two unnamed PDF attachments
    "Dinajpur": "https://dinajpur.gov.bd/pages/static-pages/ব্যাংক-3abb1c-69774bd4c4774958d7c16c05",  # see notes
}


def landline_only(s):
    """Phone numbers of a cell, ASCII; mobiles (01...) are dropped (may be managers' personal numbers)."""
    keep, dropped = [], 0
    for p in phone_norm(s).split("; "):
        if not p:
            continue
        if re.sub(r"\D", "", p).startswith("01"):
            dropped += 1
        else:
            keep.append(p)
    return "; ".join(keep), dropped


def rrow(dist, sid, name, phone, url, extra, notes, upa=""):
    r = row(dist, sid, name, phone, url, extra, notes, upa)
    r["source_key"] = RANG_KEY
    return r


def main_rangpur():
    places, dropped = [], {}
    pages = {}
    for d, u in RANG_URLS.items():
        r = get(u)
        if r is None or not r.ok:
            print("unavailable", u)
            continue
        pages[d] = r.text
        lines = content_text(r.text)
        if d == "Panchagarh":  # keep serial + bank cell only (the manager column holds officers' names)
            lines = []
            for tr in re.findall(r"<tr\b.*?</tr>", r.text, flags=re.S):
                tds = re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", tr, flags=re.S)
                if len(tds) >= 2:
                    lines.append(clean(tds[0]) + " | " + "; ".join(x for x in (clean(y) for y in re.findall(r"<p\b[^>]*>(.*?)</p>", tds[1], flags=re.S) or [tds[1]]) if x))
        # mobile numbers (possibly managers' personal numbers) are redacted in raw/
        save_raw(f"{d.lower()}_banks.txt", "\n".join(re.sub(r"(?<![০-৯0-9])[০০]?[০0][১1][৩-৯3-9][০-৯0-9]{2}-?[০-৯0-9]{6}(?![০-৯0-9])", "[mobile redacted]", l) for l in lines))
    if "Panchagarh" in pages:  # one cell per bank: <p> name </p><p> address lines </p><p> mobile </p><p> landline </p><p> website </p>
        n = 0
        for tr in re.findall(r"<tr\b.*?</tr>", pages["Panchagarh"], flags=re.S):
            tds = re.findall(r"<td\b[^>]*>(.*?)</td>", tr, flags=re.S)
            if len(tds) < 2 or not re.search("ব্যাংক|বাংক", clean(tds[1])) or "ঠিকানা" in clean(tds[1]):
                continue
            ps = [clean(x) for x in re.findall(r"<p\b[^>]*>(.*?)</p>", tds[1], flags=re.S)]
            ps = [x for x in ps if x]
            if not ps:
                continue
            name, rest = ps[0], ps[1:]
            web = next((x for x in rest if x.startswith("http")), "")
            nums = [x for x in rest if re.fullmatch(r"[০-৯0-9\-\s]+", x)]
            addr = ", ".join(x for x in rest if x not in nums and x != web).rstrip("।")
            ph, dr = landline_only(" / ".join(nums))
            dropped["Panchagarh"] = dropped.get("Panchagarh", 0) + dr
            n += 1
            r = rrow("Panchagarh", f"dpb-pan-{n:03d}", name, ph, RANG_URLS["Panchagarh"], {"bank_website": web},
                     "From the Panchagarh DC portal bank list (name, address and landline as printed; branch mobile number and "
                     "manager's name not copied). Website as displayed (several link targets on the page point to another bank).")
            r["address"] = addr
            places.append(r)
    if "Nilphamari" in pages:
        n = 0
        for t in tables(pages["Nilphamari"]):
            for cells in t:
                if len(cells) >= 3 and re.match(r"^[০-৯0-9]+$", cells[0]) and "ব্যাংক" in cells[1] + ("ব্যাংক" if "রাকাব" in cells[1] else ""):
                    ph, dr = landline_only(cells[2])
                    dropped["Nilphamari"] = dropped.get("Nilphamari", 0) + dr
                    n += 1
                    places.append(rrow("Nilphamari", f"dpb-nil-{n:03d}", cells[1], ph, RANG_URLS["Nilphamari"],
                                       {"bank_website": cells[3] if len(cells) > 3 else ""},
                                       "From the Nilphamari DC portal bank list (name as printed, spaces missing in the source). "
                                       "Only landline numbers kept; " + ("mobile number not copied." if dr else "landline as printed (no area code where none given).")))
    if "Kurigram" in pages:  # rows: '<post>, <bank>' | landline  -> one row per bank (branch posts) / regional office
        groups = {}
        for t in tables(pages["Kurigram"]):
            for cells in t:
                if len(cells) < 2 or "," not in cells[0] or not re.search(r"[০-৯0-9]{4}", cells[1]):
                    continue
                post, bank = [x.strip() for x in cells[0].split(",", 1)]
                regional = post.startswith("আঞ্ছলিক") or post.startswith("আঞ্চলিক")
                k = (bank, regional)
                g = groups.setdefault(k, {"bank": bank, "regional": regional, "numbers": {}})
                g["numbers"][post] = phone_norm(cells[1])
        n = 0
        for (bank, regional), g in groups.items():
            n += 1
            name = "%s%s, কুড়িগ্রাম" % (bank, " আঞ্চলিক কার্যালয়" if regional else "")
            places.append(rrow("Kurigram", f"dpb-kur-{n:03d}", name, "; ".join(g["numbers"].values()), RANG_URLS["Kurigram"],
                               {"office_numbers": g["numbers"], "office_type": "regional office" if regional else ""},
                               "Kurigram DC portal lists numbers by post ('<post>, <bank>'); name composed from the bank and the district"
                               + (" ('আঞ্ছলিক ব্যাবস্থাপক' = regional manager)" if regional else "") + "; branch not named (Kurigram town)."))
    write_csv("places.csv", PLACE_COLS, places)
    write_manifest(dict(
        key=RANG_KEY, division="rangpur", kind="district_banks",
        name="District portals — bank branch/office phone lists (Panchagarh, Nilphamari, Kurigram)",
        organization="Deputy Commissioner's offices (district portals)", source_type="government_portal", trust_level=4,
        urls=list(RANG_URLS.values()) + list(RANG_OTHER.values()), accessed=__import__("datetime").date.today().isoformat(),
        publication_date=None, license=None, license_url=None,
        attribution="District portals panchagarh.gov.bd, nilphamari.gov.bd, kurigram.gov.bd",
        notes="No licence stated; lists are undated. Only landline numbers are kept (branch mobile numbers dropped: %s). No coordinates "
              "or routing numbers. Rangpur and Gaibandha portals list bank names only; Thakurgaon's page is two unnamed PDF "
              "attachments; Lalmonirhat has no bank page; Dinajpur's page gives national hotlines and alternative street names per "
              "bank (not branch data) — none used." % ", ".join("%s %d" % kv for kv in dropped.items())),
        ["places.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


SITES = {"rajshahi": dict(folder="district_portal_banks_raj_2026"), "rangpur": dict(folder="district_portal_banks_rang_2026", run=main_rangpur)}


def configure():
    global DIVISION, HERE, RAW
    DIVISION, out = parse_division_args({k: v["folder"] for k, v in SITES.items()})
    HERE = Path(out)
    RAW = HERE / "raw"


if __name__ == "__main__":
    main()
