#!/usr/bin/env python3
"""Fetch bank branch/office phone lists from a division's district portals (default Rajshahi Division, DISTRICT_PORTAL_BANKS_RAJ_2026).

Usage: python3 fetch.py [--division rangpur|dhaka|chattogram|khulna|barishal|sylhet|mymensingh] [--out DIR]  (rangpur ->
DISTRICT_PORTAL_BANKS_RANG_2026, dhaka -> DISTRICT_PORTAL_BANKS_DHK_2026, chattogram -> DISTRICT_PORTAL_BANKS_CTG_2026, khulna ->
DISTRICT_PORTAL_BANKS_KHL_2026, barishal -> DISTRICT_PORTAL_BANKS_BAR_2026, sylhet -> DISTRICT_PORTAL_BANKS_SYL_2026, mymensingh ->
DISTRICT_PORTAL_BANKS_MYM_2026)."""
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


# --- DISTRICT_PORTAL_BANKS_DHK_2026 (Dhaka Division) -----------------------------------------------------------------
DHK_KEY = "DISTRICT_PORTAL_BANKS_DHK_2026"
DHK_URLS = {
    "Narayanganj": "https://narayanganj.gov.bd/pages/static-pages/69958381f2b99fa8d158a135",
    "Tangail": "https://tangail.gov.bd/pages/static-pages/6995976035ce18e1c07869bc",
    "Manikganj": "https://manikganj.gov.bd/pages/static-pages/6995b35d35ce18e1c0798580",
    "Rajbari": "https://rajbari.gov.bd/pages/static-pages/6995696335ce18e1c0779c6c",
    "Gopalganj": "https://gopalganj.gov.bd/pages/static-pages/6995dfac35ce18e1c07b1337",
    "Faridpur": "https://faridpur.gov.bd/pages/static-pages/6995e32935ce18e1c07b360d",
}
# Checked but not usable (kept for the report / SOURCE.json urls)
DHK_OTHER = {
    "Dhaka": "https://dhaka.gov.bd/pages/static-pages/bank-9uffnj-6a8fc2511f576f3ba28926ce",              # bank names + websites only
    "Gazipur": "https://gazipur.gov.bd/pages/static-pages/banks-o931js-6acb4285ba7fabe195e06ab1",          # bank names + websites only
    "Shariatpur": "https://shariatpur.gov.bd/pages/static-pages/6995d1c535ce18e1c07a9e97",               # bank -> upazilas with a branch, no contacts
    "Kishoreganj": "https://kishoreganj.gov.bd/pages/static-pages/6995aa7935ce18e1c07929ef",             # prose list of branches in the town, no contacts
    "Madaripur": "https://madaripur.gov.bd/pages/static-pages/6995996435ce18e1c0787c48",                 # mostly names (with NGOs)
}
DHK_BN = {"Narayanganj": "নারায়ণগঞ্জ", "Tangail": "টাঙ্গাইল", "Manikganj": "মানিকগঞ্জ", "Rajbari": "রাজবাড়ী", "Gopalganj": "গোপালগঞ্জ",
          "Faridpur": "ফরিদপুর"}


def drow(dist, n, name, phone, extra, notes, name_en=""):
    r = row(dist, "dpb-%s-%03d" % (dist.lower()[:3], n), name, phone, DHK_URLS[dist], extra, notes)
    r["source_key"], r["name_en"] = DHK_KEY, name_en
    return r


def main_dhaka():
    places, dropped, pages = [], {}, {}
    for d, u in DHK_URLS.items():
        r = get(u)
        if r is None or not r.ok:
            print("unavailable", u)
            continue
        r.encoding = r.encoding or "utf-8"
        pages[d] = r.text
        # raw/: page text with mobile numbers (possibly managers' personal numbers) redacted
        save_raw(f"{d.lower()}_banks.txt", "\n".join(re.sub(r"(?<![০-৯0-9])(?:\+?৮৮|\+?88)?[০0][১1][৩-৯3-9][০-৯0-9]{2}-?[০-৯0-9]{3}-?[০-৯0-9]{3}(?![০-৯0-9])", "[mobile redacted]", l) for l in content_text(r.text)))

    def keep(dist, s):
        ph, dr = landline_only(s)
        dropped[dist] = dropped.get(dist, 0) + dr
        return ph
    if "Narayanganj" in pages:  # '♣ <Bank>- <branch>' blocks: address lines, 'Tel:' / 'Phone:' lines (English)
        lines = content_text(pages["Narayanganj"])
        blocks, cur = [], None
        for l in lines:
            if l.startswith("♣"):
                cur = [l.lstrip("♣ ").strip()]
                blocks.append(cur)
            elif cur is not None:
                cur.append(l)
        n = 0
        for b in blocks:
            name, rest = b[0].rstrip("- "), b[1:]
            if rest and "-" not in name and not re.match(r"(?i)^(address|tel|phone)", rest[0]) and not re.search(r"\d", rest[0]):
                name = (name + " " + rest[0]).strip().rstrip(".")   # no branch in the heading: it continues on the next line (HSBC, Global Islami)
                rest = rest[1:]
            tel = [re.sub(r"(?i)^(tel|phone)\s*:\s*", "", x) for x in rest if re.match(r"(?i)^(tel|phone)\s*:", x)]
            tel = [re.split(r"(?i)mobile", x)[0] for x in tel]
            addr = [re.sub(r"(?i)^address\s*:\s*", "", x).strip(" ,") for x in rest
                    if not re.match(r"(?i)^(tel|phone|fax|e-?mail|tlx|swift|mobile)\b", x) and "@" not in x]
            ph = keep("Narayanganj", re.sub(r"\(880 2\)\s*", "02-", "; ".join(tel)))
            n += 1
            r = drow("Narayanganj", n, "", ph, {}, "From the Narayanganj DC portal bank list (English, as printed: name, address, "
                     "'Tel'/'Phone' numbers; fax, telex, e-mail and mobile numbers not copied). Undated list; old 7-digit Dhaka-area "
                     "numbers are printed without the 02 prefix.", name_en=name)
            r["address"] = ", ".join(a for a in addr if a)
            places.append(r)
    if "Tangail" in pages:
        n = 0
        for t in tables(pages["Tangail"]):
            for cells in t:
                if len(cells) >= 4 and re.match(r"^[০-৯0-9]+$", cells[0]) and "ব্যাংক" in cells[1]:
                    n += 1
                    r = drow("Tangail", n, "%s, টাঙ্গাইল" % cells[1], keep("Tangail", cells[3].replace(" ০", "; ০")), {"bank_bn": cells[1]},
                             "From the Tangail DC portal bank table (bank, address, phone); name composed as '<bank>, টাঙ্গাইল' (the "
                             "table lists one office per bank in Tangail town; branch not named). Only landlines kept.")
                    r["address"] = cells[2].rstrip("।")
                    places.append(r)
    if "Manikganj" in pages:  # '<post>, <bank>, মানিকগঞ্জ' | phone
        n = 0
        for t in tables(pages["Manikganj"]):
            for cells in t:
                if len(cells) >= 3 and re.match(r"^[০-৯0-9]+$", cells[0]) and cells[1].count(",") >= 1:
                    post, bank = [x.strip() for x in cells[1].split(",", 1)]
                    bank = re.sub(r",\s*মানিকগঞ্জ$", "", bank)
                    n += 1
                    places.append(drow("Manikganj", n, "%s, মানিকগঞ্জ" % bank, keep("Manikganj", cells[2]),
                                       {"bank_bn": bank, "post_in_source": post},
                                       "Manikganj DC portal lists the office number of the bank's manager in Manikganj; name composed "
                                       "from the bank and the district (branch not named)."))
    if "Rajbari" in pages:
        n = 0
        for t in tables(pages["Rajbari"]):
            for cells in t:
                if len(cells) >= 3 and "ব্যাংক" in cells[1] and cells[1] != "ব্যাংকের নাম":
                    name = re.sub(r"\s+,", ",", cells[1])
                    n += 1
                    places.append(drow("Rajbari", n, name if "রাজবাড়ী" in name else "%s, রাজবাড়ী" % name, keep("Rajbari", cells[2]),
                                       {"name_as_listed": cells[1]} if "রাজবাড়ী" not in name else {},
                                       "From the Rajbari DC portal bank list ('রাজবাড়ী জেলায় কার্যক্রম পরিচালনাকারী ব্যাংক সমূহ')" +
                                       ("" if "রাজবাড়ী" in name else "; ', রাজবাড়ী' added to the listed name") + ". Only landlines kept."))
    if "Gopalganj" in pages:  # 'NN। <bank> <phone>/<phone>/…' lines
        n = 0
        for l in content_text(pages["Gopalganj"]):
            m = re.match(r"^([০-৯0-9]+)।\s*(.+?ব্যাংক[^০-৯0-9/]*?)\s+([০-৯0-9][০-৯0-9\-/() A-Za-zআ-হ]*)$", l)
            if not m:
                continue
            name = m.group(2).strip(" ,")
            n += 1
            places.append(drow("Gopalganj", n, name if "গোপালগঞ্জ" in name else "%s, গোপালগঞ্জ" % name,
                               keep("Gopalganj", re.sub(r"\([^)]*\)", "", m.group(3))), {"name_as_listed": name},
                               "From the Gopalganj DC portal bank list (one line per bank: name and numbers); ', গোপালগঞ্জ' added; branch "
                               "not named. Only landlines kept."))
    if "Faridpur" in pages:  # bank heading, then a table of '<post> <branch> শাখা' | office phone | home phone (not copied)
        t = pages["Faridpur"]
        n = 0
        parts = re.split(r"(<table\b.*?</table>)", t[t.find('data-widget_name="ContentViewerWidget"'):], flags=re.S)
        bank = None
        for part in parts:
            if not part.startswith("<table"):
                txt = [x for x in (clean(y) for y in re.split(r"<br\s*/?>|</p>|</div>", part)) if x]
                for x in txt:
                    if x.endswith("ব্যাংক"):
                        bank = x
                continue
            if not bank:
                continue
            for cells in [c for tb in tables(part) for c in tb]:
                if len(cells) < 2 or cells[0] in ("নাম/পদবী", "অফিস") or not re.search(r"[০-৯0-9]{4}", cells[1]):
                    continue
                label = cells[0]
                br = re.sub(r"^(জোনাল |এরিয়া )?ম্যানেজার,?\s*", "", label).strip()
                name = "%s, %s, ফরিদপুর" % (bank, br) if br.endswith("শাখা") else "%s, ফরিদপুর" % bank
                n += 1
                places.append(drow("Faridpur", n, name, keep("Faridpur", cells[1]), {"bank_bn": bank, "label_in_source": label},
                                   "From the Faridpur DC portal bank tables (office number of the branch manager; home numbers not "
                                   "copied). Name composed from the bank heading and the row" + ("" if br.endswith("শাখা") else
                                   " (no branch named)") + ". 5-digit numbers are printed without the area code."))
    merged, by = [], {}
    for r in places:  # same composed name twice (e.g. Grameen Bank zonal/area manager in Faridpur): one row, both numbers
        k = (r["district_en"], r["name_bn"] or r["name_en"])
        if k in by:
            o = by[k]
            o["phone"] = "; ".join(x for x in dict.fromkeys((o["phone"] + "; " + r["phone"]).split("; ")) if x)
            ex = json.loads(o["extra_json"] or "{}")
            ex["also_listed_as"] = (ex.get("also_listed_as") or []) + [json.loads(r["extra_json"] or "{}").get("label_in_source", "")]
            o["extra_json"] = xj(ex)
            o["notes"] += " Listed more than once on the page; numbers merged."
            continue
        by[k] = r
        merged.append(r)
    places = merged
    write_csv("places.csv", PLACE_COLS, places)
    write_manifest(dict(
        key=DHK_KEY, division="dhaka", kind="district_banks",
        name="District portals — bank branch/office phone lists (%s)" % ", ".join(DHK_URLS),
        organization="Deputy Commissioner's offices (district portals)", source_type="government_portal", trust_level=4,
        urls=list(DHK_URLS.values()) + list(DHK_OTHER.values()), accessed=__import__("datetime").date.today().isoformat(),
        publication_date=None, license=None, license_url=None,
        attribution="District portals " + ", ".join("%s.gov.bd" % d.lower() for d in DHK_URLS),
        notes="No licence stated; lists are undated. Only landline numbers are kept (mobile numbers dropped: %s); no e-mails, "
              "routing numbers or coordinates. Dhaka and Gazipur portals list bank names and websites only; Shariatpur lists the "
              "upazilas in which each bank has a branch, without contacts; Kishoreganj gives a prose list of town branches without "
              "contacts; Madaripur lists mostly names (mixed with NGOs); Narsingdi and Munshiganj have no bank page — none used."
              % ", ".join("%s %d" % kv for kv in dropped.items())),
        ["places.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


# --- DISTRICT_PORTAL_BANKS_CTG_2026 (Chattogram Division) ------------------------------------------------------------
CTG_KEY = "DISTRICT_PORTAL_BANKS_CTG_2026"
CTG_URLS = {
    "Cumilla": "https://comilla.gov.bd/pages/static-pages/69912917516a96d4de40783c",
    "Feni": "https://feni.gov.bd/pages/static-pages/6990ef0135ce18e1c072abae",
    "Brahmanbaria": "https://brahmanbaria.gov.bd/pages/static-pages/6990f3a235ce18e1c072f52d",
    "Rangamati": "https://rangamati.gov.bd/pages/static-pages/69914374516a96d4de411143",
    "Noakhali": "https://noakhali.gov.bd/pages/static-pages/6990eefe35ce18e1c072aa4b",
    "Chandpur": "https://chandpur.gov.bd/pages/static-pages/6991384d516a96d4de40c431",
    "Chattogram": "https://chittagong.gov.bd/pages/static-pages/6990e67235ce18e1c0727b95",
    "Khagrachhari": "https://khagrachhari.gov.bd/pages/static-pages/699145a2516a96d4de413f1d",
    "Bandarban": "https://bandarban.gov.bd/pages/static-pages/69914377516a96d4de411275",
}
# Checked but not usable (kept for the report / SOURCE.json urls)
CTG_OTHER = {
    "Cox's Bazar": "https://coxsbazar.gov.bd/pages/static-pages/6991177035ce18e1c073d47d",   # bank names + websites only
    "Lakshmipur": "https://lakshmipur.gov.bd/pages/bank-financial-org",                      # 4 bank names, no branch or contacts
}
CTG_BN = {"Cumilla": "কুমিল্লা", "Feni": "ফেনী", "Brahmanbaria": "ব্রাহ্মণবাড়িয়া", "Rangamati": "রাঙ্গামাটি", "Noakhali": "নোয়াখালী",
          "Chandpur": "চাঁদপুর", "Chattogram": "চট্টগ্রাম", "Khagrachhari": "খাগড়াছড়ি", "Bandarban": "বান্দরবান"}
# upazilas named in the Brahmanbaria upazila tables / Noakhali addresses (HDX COD-AB v03 spellings)
CTG_UPA = {"Brahmanbaria": {"ব্রাহ্মণবাড়িয়া সদর": "Brahmanbaria Sadar", "সরাইল": "Sarail", "নবীনগর": "Nabinagar", "কসবা": "Kasba",
                            "আখাউড়া": "Akhaura", "আশুগঞ্জ": "Ashuganj", "বিজয়নগর": "Bijoynagar", "নাসিরনগর": "Nasirnagar",
                            "নাছিরনগর": "Nasirnagar", "বাঞ্ছারামপুর": "Banchharampur"},
           "Noakhali": {"বেগমগঞ্জ": "Begumganj", "চাটখিল": "Chatkhil", "কোম্পানিগঞ্জ": "Companiganj",
                        "কোম্পানীগঞ্জ": "Companiganj", "হাতিয়া": "Hatiya", "কবিরহাট": "Kabirhat", "সেনবাগ": "Senbag",
                        "সোনাইমুড়ী": "Sonaimuri", "সুবর্ণচর": "Subarnachar", "সদর, নোয়াখালী": "Noakhali Sadar"}}
_MOBILE_RAW = r"(?<![০-৯0-9])(?:\+?৮৮|\+?88)?[০0][১1][৩-৯3-9](?:[- ]?[০-৯0-9]){7,9}(?![০-৯0-9])"   # incl. mistyped 12-digit ones


def crow(dist, n, name, phone, extra, notes, address="", upa=""):
    r = row(dist, "dpb-%s-%03d" % (dist.lower()[:3], n), name, phone, CTG_URLS[dist], extra, notes, upa)
    r["source_key"], r["address"] = CTG_KEY, address
    return r


def ctg_upazila(dist, *texts):
    t = " ".join(texts)
    hits = [(t.find(bn), en) for bn, en in CTG_UPA.get(dist, {}).items() if bn in t]
    return min(hits)[1] if hits else ""


def main_chattogram():
    places, dropped, pages, n = [], {}, {}, {}
    for d, u in CTG_URLS.items():
        r = get(u)
        if r is None or not r.ok:
            print("unavailable", u)
            continue
        r.encoding = r.encoding or "utf-8"
        pages[d] = r.text
        # raw/: page text with mobile numbers (possibly managers' personal numbers) redacted
        save_raw(f"{d.lower()}_banks.txt", "URL: %s\n\n" % u + "\n".join(re.sub(_MOBILE_RAW, "[mobile redacted]", l) for l in content_text(r.text)))

    def keep(dist, s):   # numbers in a cell may be separated by single spaces only ('0321-52094 01711-xxxxxx')
        ph, dr = landline_only(re.sub(r"(?<=[০-৯0-9])\s+(?=[+০-৯0-9])", "; ", s or ""))
        dropped[dist] = dropped.get(dist, 0) + dr
        return ph

    def add(dist, name, phone, extra, notes, address="", upa=""):
        n[dist] = n.get(dist, 0) + 1
        places.append(crow(dist, n[dist], nfc(re.sub(r"\s+", " ", name)).strip(" ,।"), phone, extra, notes, address, upa))

    def town(dist, name):   # '<bank>' -> '<bank>, <district town>' unless the town is already in the name
        return name if CTG_BN[dist] in name else "%s, %s" % (name, CTG_BN[dist])

    def rows_of(dist, t):
        return [c for tb in tables(widget_of(t)) for c in tb]

    if "Cumilla" in pages:   # table 1: serial | bank (branch) | address | phone; table 2 is run-together text (not parsed)
        for c in rows_of("Cumilla", pages["Cumilla"]):
            if len(c) >= 4 and re.match(r"^[০-৯0-9]+$", c[0]) and "ব্যাংক" in c[1]:
                add("Cumilla", town("Cumilla", c[1]), keep("Cumilla", c[3]), {"name_as_listed": c[1]},
                    "From the Cumilla DC portal list of bank branches in Cumilla town (name, address, phone as printed; ', কুমিল্লা' "
                    "added where the name lacks it). Several numbers repeat across banks at source.", c[2].rstrip("।"))
    if "Feni" in pages:      # serial | bank | phone (5 digits, no area code)
        for c in rows_of("Feni", pages["Feni"]):
            if len(c) >= 3 and re.match(r"^[০-৯0-9]+।?$", c[0]) and c[1] != "নাম":
                parts = [p.strip() for p in c[2].split("/")]
                addr = ", ".join(p for p in parts if not re.search(r"\d|[০-৯]", p))
                add("Feni", town("Feni", c[1]), keep("Feni", c[2]), {"name_as_listed": c[1]},
                    "From the Feni DC portal list of bank branches in Feni town (name and phone as printed; 5-digit numbers without the "
                    "area code; ', ফেনী' added; branch not named). Only landlines kept.", addr)
    if "Brahmanbaria" in pages:   # town table (serial | bank, branch, town | phone) + per-upazila tables (Unicode ones only)
        cur = None
        for c in rows_of("Brahmanbaria", pages["Brahmanbaria"]):
            if not c or not re.match(r"^[০-৯0-9]+\.?$", c[0]) or len(c) < 3:
                continue
            if len(c) == 3 and "ব্যাংক" in c[1]:   # town table
                add("Brahmanbaria", c[1], keep("Brahmanbaria", c[2]), {"name_as_listed": c[1]},
                    "From the Brahmanbaria DC portal list of banks in Brahmanbaria town (name and number as printed; most numbers are "
                    "mobiles and are not copied; 5-digit numbers lack the area code).", upa="")
                continue
            body = [x for x in c[1:]]
            up = next(((CTG_UPA["Brahmanbaria"][x], x) for x in body[:1] if x in CTG_UPA["Brahmanbaria"]), None)
            if up:
                (cur, cur_bn), body = up, body[1:]
            name = next((x for x in body if "ব্যাংক" in x), "")
            if not name or not re.search(r"[অ-হ]", name) or re.search(r"[a-z]", name) or not cur:
                continue   # insurance rows, legacy-font (non-Unicode) text, or no upazila
            nm, _, addr = name.partition("ঠিকানা")
            nm = nm.strip(" ,।")
            if cur_bn not in nm and cur_bn not in addr:
                nm = "%s, %s" % (nm, cur_bn)
            add("Brahmanbaria", nm, keep("Brahmanbaria", body[-1]), {"name_as_listed": name},
                "From the Brahmanbaria DC portal per-upazila bank tables (bank/branch and address as printed; the numbers are mostly "
                "mobiles and are not copied). Upazila from the table's upazila column; ', <upazila>' added where the name has no "
                "place.", addr.strip(" :ঃ"), cur)
    if "Rangamati" in pages:   # serial | bank | address (or branch) | phone
        for c in rows_of("Rangamati", pages["Rangamati"]):
            if len(c) >= 4 and re.match(r"^[০-৯0-9]+$", c[0]) and "ব্যাংক" in c[1]:
                br = c[2] if c[2].endswith("শাখা") else ""
                add("Rangamati", "%s, %s%s" % (c[1], br + ", " if br else "", "রাঙ্গামাটি"), keep("Rangamati", c[3]),
                    {"name_as_listed": c[1], "address_or_branch_as_listed": c[2]},
                    "From the Rangamati DC portal bank tables (government and private banks; name, address and phone as printed); "
                    "', রাঙ্গামাটি' added. Number ranges such as '০৩৫১-৬১৭০১-২' are kept as printed.", "" if br else c[2])
    if "Noakhali" in pages:   # bank (row-spanning) | branch | address | phone
        bank = None
        for c in rows_of("Noakhali", pages["Noakhali"]):
            if len(c) == 4 and c[0] != "ব্যাংকের নাম":
                bank, c = c[0], c[1:]
            elif len(c) != 3 or not bank:
                continue
            branch, addr, ph = c
            if not branch.endswith("শাখা") and "শাখা" not in branch:
                continue
            add("Noakhali", "%s, %s" % (bank, branch), keep("Noakhali", ph.replace("--", "")), {"bank_bn": bank},
                "From the Noakhali DC portal list of scheduled-bank branches (bank, branch, address, phone as printed). Only landlines "
                "kept. Upazila from the address where it names one.", addr.rstrip("।"), ctg_upazila("Noakhali", addr, branch))
    if "Chandpur" in pages:   # 'N. | bank | address |' lines; Karmasangsthan Bank's cell lists its branches '1. X শাখা, চাঁদপুর'
        bank = None
        for l in content_text(pages["Chandpur"]):
            m = re.match(r"^[০-৯0-9]+\.\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|?$", l)
            if m and "ব্যাংক" in m.group(1):
                bank, addr = m.group(1), m.group(2)
                if re.match(r"^[০-৯0-9]+\.\s", addr):   # first of a numbered branch list
                    br = re.sub(r"^[০-৯0-9]+\.\s*", "", addr)
                    add("Chandpur", "%s, %s" % (bank, br), "", {"bank_bn": bank}, "From the Chandpur DC portal bank list (branch list of "
                        "the bank's cell); no phone numbers are published.")
                else:
                    add("Chandpur", town("Chandpur", bank), "", {"name_as_listed": bank}, "From the Chandpur DC portal bank list (name "
                        "and address as printed; ', চাঁদপুর' added; branch not named); no phone numbers are published.", addr.rstrip("।"))
                continue
            m = re.match(r"^[০-৯0-9]+\.\s*([^|]+শাখা[^|]*)$", l)
            if m and bank:
                add("Chandpur", "%s, %s" % (bank, m.group(1).strip()), "", {"bank_bn": bank}, "From the Chandpur DC portal bank list "
                    "(branch list of the bank's cell); no phone numbers are published.")
    if "Chattogram" in pages:   # bank | post (branch) | phone — one office per bank in Chattogram city
        for c in rows_of("Chattogram", pages["Chattogram"]):
            if len(c) >= 3 and "ব্যাংক" in c[0] and c[0] != "ব্যাংকের নাম":
                add("Chattogram", "%s, চট্টগ্রাম" % c[0], keep("Chattogram", c[2]), {"bank_bn": c[0], "post_in_source": c[1]},
                    "From the Chattogram DC portal list 'চট্টগ্রাম মহানগরের ব্যাংক সমুহ' (bank, post of the listed officer, office "
                    "number); name composed as '<bank>, চট্টগ্রাম' (branch not named). Numbers are printed without the area code; "
                    "only landlines kept.")
    if "Khagrachhari" in pages:   # serial | bank, branch | head's post | phone
        for c in rows_of("Khagrachhari", pages["Khagrachhari"]):
            if len(c) >= 4 and re.match(r"^[০-৯0-9]+$", c[0]) and "ব্যাংক" in c[1]:
                add("Khagrachhari", town("Khagrachhari", c[1]), keep("Khagrachhari", c[3]), {"name_as_listed": c[1], "post_in_source": c[2]},
                    "From the Khagrachhari DC portal bank list (bank/branch, post of the office head, office phone). Only landlines kept.")
    if "Bandarban" in pages:   # serial | '<post>, <bank>' | phone
        for c in rows_of("Bandarban", pages["Bandarban"]):
            if len(c) >= 3 and re.match(r"^[০-৯0-9]+।?$", c[0]) and "," in c[1] and "ব্যাংক" in c[1]:
                post, bank = [x.strip() for x in c[1].split(",", 1)]
                regional = "আঞ্চলিক" in post
                add("Bandarban", "%s%s, বান্দরবান" % (bank, " আঞ্চলিক কার্যালয়" if regional else ""), keep("Bandarban", c[2]),
                    {"bank_bn": bank, "post_in_source": post},
                    "Bandarban DC portal lists the office number by post ('<post>, <bank>'); name composed from the bank and the "
                    "district%s; branch not named." % (" ('আঞ্চলিক ব্যবস্থাপক' = regional manager)" if regional else ""))
    merged, by = [], {}
    for r in places:   # same composed name and address twice in a district: one row, both numbers
        k = (r["district_en"], r["name_bn"], r["address"])
        if k in by:
            o = by[k]
            o["phone"] = "; ".join(x for x in dict.fromkeys((o["phone"] + "; " + r["phone"]).split("; ")) if x)
            ex = json.loads(o["extra_json"] or "{}")
            ex["also_listed_as"] = (ex.get("also_listed_as") or []) + [json.loads(r["extra_json"] or "{}")]
            o["extra_json"] = xj(ex)
            o["notes"] += " Listed more than once on the page; numbers merged."
            continue
        by[k] = r
        merged.append(r)
    places = merged
    write_csv("places.csv", PLACE_COLS, places)
    write_manifest(dict(
        key=CTG_KEY, division="chattogram", kind="district_banks",
        name="District portals — bank branch/office lists (%s)" % ", ".join(CTG_URLS),
        organization="Deputy Commissioner's offices (district portals)", source_type="government_portal", trust_level=4,
        urls=list(CTG_URLS.values()) + list(CTG_OTHER.values()), accessed=__import__("datetime").date.today().isoformat(),
        publication_date=None, license=None, license_url=None,
        attribution="District portals " + ", ".join(urllib.parse.urlsplit(u).netloc for u in CTG_URLS.values()),
        notes="No licence stated; lists are undated. Only landline numbers are kept (mobile numbers dropped: %s); no e-mails, "
              "routing numbers or coordinates. Cox's Bazar lists bank names and websites only and Lakshmipur's bank module has 4 "
              "names without branch or contacts — not used. Cumilla's second table (run-together text) and Brahmanbaria's "
              "legacy-font (non-Unicode) upazila table and insurance table are not parsed."
              % ", ".join("%s %d" % kv for kv in dropped.items() if kv[1])),
        ["places.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


# --- DISTRICT_PORTAL_BANKS_KHL_2026 (Khulna Division) ----------------------------------------------------------------
KHL_KEY = "DISTRICT_PORTAL_BANKS_KHL_2026"
KHL_URLS = {
    "Meherpur": "https://meherpur.gov.bd/pages/static-pages/6980f68da31054345f1cefa5",     # 'সরকারী ব্যাংকসমূহ': bank | branch | phone | mobile | e-mail
    "Narail": "https://narail.gov.bd/pages/static-pages/6980fbdfa31054345f1d1684",         # serial | '<post>, <bank>, <branch>' | phone
    "Chuadanga": "https://chuadanga.gov.bd/pages/static-pages/6981416d35ce18e1c0701b40",   # serial | '<bank>, চুয়াডাঙ্গা' (no numbers)
    "Kushtia": "https://kushtia.gov.bd/pages/static-pages/69810198a31054345f1d4f4b",       # 'N. <post>, <bank>, …' lines (no numbers)
    "Magura": "https://magura.gov.bd/pages/static-pages/6980fbe6a31054345f1d1a49",         # serial | bank | address ('ঐ' = ditto)
    "Bagerhat": "https://bagerhat.gov.bd/pages/static-pages/6980f69da31054345f1cf7c6",     # bank | head | office + phone | services | type
}
# Checked but not usable (kept for the report / SOURCE.json urls)
KHL_OTHER = {
    "Khulna": "https://khulna.gov.bd/pages/static-pages/69812047a31054345f1e0bd2",        # PDF (Excel export) whose text layer is garbled
    "Satkhira": "https://satkhira.gov.bd/pages/bank-financial-org",                        # 4 entries, only 1 with a branch, no contacts
    "Jhenaidah": "https://jhenaidah.gov.bd/pages/bank-financial-org",                      # 1 test entry
    "Jashore": "https://jessore.gov.bd/pages/bank-financial-org",                          # empty; the DC menu's 'ব্যাংক' link is '#'
}
KHL_BN = {"Meherpur": "মেহেরপুর", "Narail": "নড়াইল", "Chuadanga": "চুয়াডাঙ্গা", "Kushtia": "কুষ্টিয়া", "Magura": "মাগুরা", "Bagerhat": "বাগেরহাট"}
KHL_UPA = {"Meherpur": {"গাংনী": "Gangni", "মুজিবনগর": "Mujibnagar"}}
KHL_POST = re.compile(r"^(সহকারী ম্যানেজার|আঞ্চলিক ব্যবস্থাপক|ম্যা?নেজার|ম্যনেজার|উপ-মহাব্যবস্থাপক|সহকারী মহাব্যবস্থাপক|ডেপুটি জেনারেল ম্যানেজার)[,\s]+")


def khl_row(dist, n, name, phone, extra, notes, address="", upa=""):
    r = row(dist, "dpb-%s-%03d" % (dist.lower()[:3], n), name, phone, KHL_URLS[dist], extra, notes, upa)
    r["source_key"], r["address"] = KHL_KEY, address
    return r


def main_khulna():
    places, dropped, pages, n = [], {}, {}, {}
    for d, u in KHL_URLS.items():
        r = get(u)
        if r is None or not r.ok:
            print("unavailable", u)
            continue
        r.encoding = r.encoding or "utf-8"
        pages[d] = r.text
        # raw/: page text with mobile numbers (possibly managers' personal numbers) and e-mails redacted
        lines = [re.sub(_MOBILE_RAW, "[mobile redacted]", l) for l in content_text(r.text)]
        lines = [re.sub(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", "[e-mail redacted]", l) for l in lines]
        if d == "Bagerhat":   # the head's name sits in the same cell as the mobile: keep only the office/phone column
            lines = [" | ".join(c for i, c in enumerate(l.split(" | ")) if i in (0, 2)) for l in lines]
        save_raw(f"{d.lower()}_banks.txt", "URL: %s\n\n" % u + "\n".join(dict.fromkeys(lines)))

    def keep(dist, s):
        ph, dr = landline_only(s or "")
        dropped[dist] = dropped.get(dist, 0) + dr
        return ph

    def add(dist, name, phone, extra, notes, address="", upa=""):
        n[dist] = n.get(dist, 0) + 1
        places.append(khl_row(dist, n[dist], nfc(re.sub(r"\s+", " ", name)).strip(" ,।"), phone, extra, notes, address, upa))

    def rows_of(t):
        return [c for tb in tables(widget_of(t)) for c in tb]

    def upa_of(dist, text):
        return next((en for bn, en in KHL_UPA.get(dist, {}).items() if bn in text), "")

    if "Meherpur" in pages:   # bank on its first row, then (branch, phone, mobile, e-mail) rows
        bank = None
        for c in rows_of(pages["Meherpur"]):
            if c[0] == "ব্যাংক":
                continue
            if len(c) == 5:
                bank, c = c[0], c[1:]
            if len(c) != 4 or not bank:
                continue
            branch, tel, mob = c[0], c[1], c[2]
            bank_bn = bank if "ব্যাংক" in bank else bank + " ব্যাংক"
            dropped["Meherpur"] = dropped.get("Meherpur", 0) + (1 if re.search(r"[০-৯0-9]{5}", mob) else 0)
            add("Meherpur", "%s, %s" % (bank_bn, branch), keep("Meherpur", tel.replace("-", "") if tel.strip() != "-" else ""),
                {"bank_as_listed": bank, "branch_as_listed": branch},
                "From the Meherpur DC portal 'সরকারী ব্যাংকসমূহ' (bank, branch and telephone as printed; 'ব্যাংক' added to the bank's "
                "short name; branch names are printed without spaces). Mobile numbers and the e-mail column (non-government addresses) "
                "are not copied.", upa=upa_of("Meherpur", branch))
    if "Narail" in pages:     # serial | '<post>, <bank>[, <branch>]' | phone
        for c in rows_of(pages["Narail"]):
            if len(c) < 3 or not re.match(r"^[০-৯0-9]+$", c[0]) or "ব্যাংক" not in c[1]:
                continue
            m = KHL_POST.match(c[1])
            post = m.group(1) if m else ""
            rest = c[1][m.end():] if m else c[1]
            parts = [p.strip() for p in rest.split(",") if p.strip()]
            regional = post == "আঞ্চলিক ব্যবস্থাপক"
            name = parts[0] + (" আঞ্চলিক কার্যালয়" if regional else "") + ", " + (", ".join(parts[1:]) if len(parts) > 1 else "নড়াইল")
            add("Narail", name, keep("Narail", c[2]), {"listed_as": c[1], "post_in_source": post},
                "From the Narail DC portal bank list (the office number is listed by the post '<post>, <bank>, <branch>'); name composed "
                "from the bank and branch (', নড়াইল' where no branch is given%s). The source spells Rupali Bank 'রুপালী'." % (
                    "; 'আঞ্চলিক ব্যবস্থাপক' = regional office" if regional else ""))
    if "Chuadanga" in pages:  # serial | '<bank> লিঃ, চুয়াডাঙ্গা'
        for c in rows_of(pages["Chuadanga"]):
            if len(c) >= 2 and re.match(r"^[০-৯0-9]+$", c[0]) and "ব্যাংক" in c[1]:
                add("Chuadanga", c[1], "", {"name_as_listed": c[1]},
                    "From the Chuadanga DC portal 'চুয়াডাঙ্গা জেলায় স্থাপিত ব্যাংকসমূহের তালিকা' (name and place as printed, e.g. 'সনালী'); "
                    "no branch, address or phone is published.")
    if "Kushtia" in pages:    # 'N. <post>, <bank>[, <office>][, কুষ্টিয়া]'
        for l in content_text(pages["Kushtia"]):
            m = re.match(r"^[০-৯0-9]+\.\s*(.+)$", l)
            if not m or "ব্যাংক" not in m.group(1):
                continue
            listed = m.group(1)
            pm = KHL_POST.match(listed)
            rest = listed[pm.end():] if pm else listed
            name = rest if "কুষ্টিয়া" in rest else rest + ", কুষ্টিয়া"
            add("Kushtia", name, "", {"listed_as": listed, "post_in_source": pm.group(1) if pm else None},
                "From the Kushtia DC portal bank list (addressed to the office head's post '<post>, <bank>, …'); name composed without "
                "the post (', কুষ্টিয়া' added where missing); no address or phone is published.")
    if "Magura" in pages:     # serial | bank | address ('ঐ' = same as above)
        last = ""
        for c in rows_of(pages["Magura"]):
            if len(c) >= 3 and re.match(r"^[০-৯0-9]+$", c[0]) and "ব্যাংক" in c[1]:
                place = last if c[2] == "ঐ" else c[2]
                last = place
                add("Magura", "%s, %s" % (c[1].strip(" ,"), place), "", {"name_as_listed": c[1], "address_as_listed": c[2]},
                    "From the Magura DC portal bank list (bank as printed, e.g. 'বাংলদেশ কৃষি ব্যাংক'; address 'মাগুরা', 'ঐ' = ditto); "
                    "name composed as '<bank>, মাগুরা'; no branch or phone is published.")
    if "Bagerhat" in pages:   # the page shows the same table twice
        seen = set()
        for c in rows_of(pages["Bagerhat"]):
            if len(c) < 3 or "ব্যাংক" not in c[0] or c[0] == "শিরোনাম":
                continue
            office = c[2]
            if (c[0], office) in seen:
                continue
            seen.add((c[0], office))
            m = re.search(r"ফোন\s*-\s*([০-৯0-9\- ]+)", office)
            addr = office[:m.start()].strip(" ,।") if m else office.strip(" ,।")
            seg = next((p.strip() for p in addr.split(",") if "শাখা" in p), "")
            if seg:
                name = "%s, %s" % (c[0], re.sub(r"\s*বাগেরহাট(।)?$", "", seg).strip() or seg)
            elif "রিজিওনাল অফিস" in addr:
                name = "%s রিজিওনাল অফিস, বাগেরহাট" % c[0]
            else:
                name = "%s, বাগেরহাট" % c[0]
            add("Bagerhat", name, keep("Bagerhat", m.group(1) if m else ""),
                {"bank_as_listed": c[0], "office_as_listed": addr, "type_as_listed": c[4] if len(c) > 4 else None},
                "From the Bagerhat DC portal bank table (bank, office address and office phone as printed; the table appears twice "
                "on the page and is read once). The head's name and mobile number are not copied; the services text is not copied.", addr)
    merged, by = [], {}
    for r in places:   # same composed name and address twice in a district: one row, both numbers
        k = (r["district_en"], r["name_bn"], r["address"])
        if k in by:
            o = by[k]
            o["phone"] = "; ".join(x for x in dict.fromkeys((o["phone"] + "; " + r["phone"]).split("; ")) if x)
            ex = json.loads(o["extra_json"] or "{}")
            ex["also_listed_as"] = (ex.get("also_listed_as") or []) + [json.loads(r["extra_json"] or "{}")]
            o["extra_json"] = xj(ex)
            o["notes"] += " Listed more than once on the page; numbers merged."
            continue
        by[k] = r
        merged.append(r)
    places = merged
    write_csv("places.csv", PLACE_COLS, places)
    write_manifest(dict(
        key=KHL_KEY, division="khulna", kind="district_banks",
        name="District portals — bank branch/office lists (%s)" % ", ".join(KHL_URLS),
        organization="Deputy Commissioner's offices (district portals)", source_type="government_portal", trust_level=4,
        urls=list(KHL_URLS.values()) + list(KHL_OTHER.values()), accessed=__import__("datetime").date.today().isoformat(),
        publication_date=None, license=None, license_url=None,
        attribution="District portals " + ", ".join(urllib.parse.urlsplit(u).netloc for u in KHL_URLS.values()),
        notes="No licence stated; lists are undated. Only landline numbers are kept (mobile numbers dropped: %s); no e-mails, "
              "routing numbers, managers' names or coordinates. Not used: Khulna (the bank list is a PDF exported from Excel whose text "
              "layer is garbled — Bangla glyphs extract in the wrong order), Satkhira and Jhenaidah (the portals' bank module holds 4 "
              "and 1 near-empty entries), Jashore (bank module empty; menu link '#')." % (
                  ", ".join("%s %d" % kv for kv in dropped.items() if kv[1]) or "none")),
        ["places.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


def widget_of(t):
    i = t.find('data-widget_name="ContentViewerWidget"')
    return t[i:] if i >= 0 else t


# --- DISTRICT_PORTAL_BANKS_BAR_2026 (Barishal Division) --------------------------------------------------------------
BAR_KEY = "DISTRICT_PORTAL_BANKS_BAR_2026"
BAR_URLS = {
    "Patuakhali": "https://patuakhali.gov.bd/pages/static-pages/bank-x23c5l-6a786562a3a462c02a70c42f",   # serial | bank | head's name+post | number
    "Pirojpur": "https://pirojpur.gov.bd/pages/static-pages/697887be35ce18e1c0662db3",                  # serial | '<bank>, <branch>, <address>' | office | residence
    "Bhola": "https://bhola.gov.bd/pages/static-pages/ব্যাংক-fe5520-6978a31d35ce18e1c067207e",           # serial | bank | address | phone
}
# Checked but not usable (kept for the report / SOURCE.json urls)
BAR_OTHER = {
    "Barishal": "https://barisal.gov.bd/pages/static-pages/6978a32235ce18e1c06722af",    # national list: bank name + head-office web link, no branch
    "Barguna": "https://barguna.gov.bd/pages/static-pages/6978a31535ce18e1c0671c7f",     # national list: bank name + web site, no branch
    "Jhalokathi": "https://jhalakathi.gov.bd/pages/static-pages/6978a2f535ce18e1c0670d6c",  # attachment: scanned PDF (CamScanner), no text layer
}
BAR_BN = {"Patuakhali": "পটুয়াখালী", "Pirojpur": "পিরোজপুর", "Bhola": "ভোলা"}
BAR_POST = re.compile(r"^(এজিএম|আরএম|ডিজিএম|জিএম)$")


def bar_row(dist, n, name, phone, extra, notes, address=""):
    r = row(dist, "dpb-%s-%03d" % (dist.lower()[:3], n), name, phone, BAR_URLS[dist], extra, notes)
    r["source_key"], r["address"] = BAR_KEY, address
    return r


def main_barishal():
    places, dropped, pages, n = [], {}, {}, {}
    for d, u in BAR_URLS.items():
        r = get(u)
        if r is None or not r.ok:
            print("unavailable", u)
            continue
        r.encoding = r.encoding or "utf-8"
        pages[d] = r.text
        # raw/: only the columns used here (Patuakhali's heads' names and Pirojpur's residence numbers are left out); mobiles redacted
        rows = [c for tb in tables(widget_of(r.text)) for c in tb if any(c)]
        if d == "Patuakhali":
            rows = [[x for i, x in enumerate(c) if i != 2] for c in rows]
        if d == "Pirojpur":
            rows = [c[:3] for c in rows]
        lines = [re.sub(_MOBILE_RAW, "[mobile redacted]", " | ".join(c)) for c in rows]
        save_raw(f"{d.lower()}_banks.txt", "URL: %s\n\n" % u + "\n".join(dict.fromkeys(lines)) + "\n")

    def keep(dist, s):
        ph, dr = landline_only(s or "")
        dropped[dist] = dropped.get(dist, 0) + dr
        return ph

    def add(dist, name, phone, extra, notes, address=""):
        n[dist] = n.get(dist, 0) + 1
        places.append(bar_row(dist, n[dist], nfc(re.sub(r"\s+", " ", name)).strip(" ,।|"), phone, extra, notes, address))

    def rows_of(t):
        return [c for tb in tables(widget_of(t)) for c in tb]

    if "Patuakhali" in pages:   # serial | bank | head's name and post (not copied) | one number
        for c in rows_of(pages["Patuakhali"]):
            if len(c) < 4 or not re.match(r"^[০-৯0-9]+$", c[0]) or "ব্যাংক" not in c[1]:
                continue
            bank = nfc(c[1]).strip(" |।")
            add("Patuakhali", "%s, পটুয়াখালী" % bank, keep("Patuakhali", c[3]), {"bank_as_listed": c[1]},
                "From the Patuakhali DC portal bank list (bank as printed; ', পটুয়াখালী' added: the list gives no branch or address). "
                "The list names each regional/branch head with a number; the heads' names and posts and all mobile numbers are not "
                "copied, only landlines.")
    if "Pirojpur" in pages:     # serial | '<post>, <bank>, <branch>, <address>' | office phone | residence phone (not copied)
        for c in rows_of(pages["Pirojpur"]):
            if len(c) < 3 or not re.match(r"^[০-৯0-9]+$", c[0]) or "ব্যাংক" not in c[1]:
                continue
            parts = [p.strip() for p in re.split(r"\s*,\s*", nfc(c[1])) if p.strip()]
            i = next(k for k, p in enumerate(parts) if "ব্যাংক" in p)
            pre, bank, rest = parts[:i], parts[i], parts[i + 1:]
            post = pre[0] if pre and BAR_POST.match(pre[0]) else ""
            office = ", ".join(p for p in pre if p != post)
            branch = rest[0] if rest and re.search(r"শাখা|উপজেলা কমপ্লেক্স", rest[0]) else ""
            addr = ", ".join(rest[1:] if branch else rest)
            name = bank + (", " + branch if branch else "") + (", " + office if office else "") + (" (%s কার্যালয়)" % post if post else "")
            if not branch and not office and not post:
                name = bank + ", পিরোজপুর" if "পিরোজপুর" not in addr else bank + ", পিরোজপুর"
            add("Pirojpur", name, keep("Pirojpur", c[2]),
                {"listed_as": c[1], "post_in_source": post or None},
                "From the Pirojpur DC portal bank list (one cell '<bank>, <branch>, <address>'; name composed from the bank, branch or "
                "office%s; the rest is the address). Only the office number is copied; the residence ('বাসা') column is not. The list "
                "is undated and still uses the old 0461 numbers." % ("; '%s' = the post whose office is listed" % post if post else ""),
                addr)
    if "Bhola" in pages:        # serial | bank | address | phone
        for c in rows_of(pages["Bhola"]):
            if len(c) < 4 or not re.match(r"^[০-৯0-9]+$", c[0]) or "ব্যাংক" not in c[1]:
                continue
            name = c[1] if "ভোলা" in c[1] else "%s, ভোলা" % c[1]
            add("Bhola", name, keep("Bhola", c[3]), {"bank_as_listed": c[1], "address_as_listed": c[2]},
                "From the Bhola DC portal bank list (bank, address and telephone as printed%s; spellings as printed, e.g. 'ব্রাক', "
                "'রুপালী', 'ফাস্ট')." % ("; ', ভোলা' added to the name" if "ভোলা" not in c[1] else ""), c[2])
    write_csv("places.csv", PLACE_COLS, places)
    write_manifest(dict(
        key=BAR_KEY, division="barishal", kind="district_banks",
        name="District portals — bank branch/office lists (%s)" % ", ".join(BAR_URLS),
        organization="Deputy Commissioner's offices (district portals)", source_type="government_portal", trust_level=4,
        urls=list(BAR_URLS.values()) + list(BAR_OTHER.values()), accessed=__import__("datetime").date.today().isoformat(),
        publication_date=None, license=None, license_url=None,
        attribution="District portals " + ", ".join(urllib.parse.urlsplit(u).netloc for u in BAR_URLS.values()),
        notes="No licence stated; lists are undated. Only landline numbers are kept (mobile numbers dropped: %s); no e-mails, "
              "routing numbers, managers' names, residence numbers or coordinates. Not used: Barishal and Barguna (their 'ব্যাংক' pages "
              "list banks with head-office web links, no branch in the district), Jhalokathi (the list is a scanned PDF without a "
              "text layer)." % (", ".join("%s %d" % kv for kv in dropped.items() if kv[1]) or "none")),
        ["places.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))



# --- DISTRICT_PORTAL_BANKS_SYL_2026 (Sylhet Division) ----------------------------------------------------------------
SYL_KEY = "DISTRICT_PORTAL_BANKS_SYL_2026"
SYL_URLS = {
    "Sylhet": "https://sylhet.gov.bd/pages/static-pages/696cb9a8c4774958d7ba8e13",      # bank | post, branch & address | phone | e-mail
    "Habiganj": "https://habiganj.gov.bd/pages/static-pages/banks-u7jcrx-6a054d1df570c41f02eaa7f2",  # same columns; local numbers
    "Moulvibazar": "https://moulvibazar.gov.bd/pages/static-pages/banks-apcyh3-6a09fee35d40ccedfd8e18c2",  # bank | branch/road; no numbers
}
# Checked but not usable (kept for the report / SOURCE.json urls)
SYL_OTHER = {
    "Sunamganj": "https://sunamganj.gov.bd/pages/bank-financial-org",   # bank/insurer names; every detail field (branch, address, phone) empty
}
# The Sylhet DC portal sends only its leaf certificate (Let's Encrypt YR1): the CA-published intermediates (AIA 'CA Issuers' URLs:
# YR1, and Root YR cross-signed by ISRG Root X1) are added for Sylhet runs, as the Sectigo ones above; TLS verification stays on.
SYL_INTERMEDIATES = ["http://yr1.i.lencr.org/", "http://yr.i.lencr.org/"]
# Leading post of the 'পদবী, শাখার নাম ও ঠিকানা' cell (longest first); the post itself is not part of the name
SYL_POST = re.compile(r"^(আঞ্চলিক উপ-মহাব্যবস্থাপক|আঞ্চলিক পরিচালক|আঞ্চলিক ব্যবস্থাপক|জি এম \(বিভাগীয় অফিস\)|জোনাল ম্যানেজার|"
                      r"মহাব্যবস্থাপক|ডি জি এম|ডিজিএম|এজিএম|এ জি এম|এ ভি পি \(মেইন ব্রাঞ্চ\)|এ ভি পি|ভি পি \(ম্যানেজার\)|ভি পি|ভিপি|"
                      r"ব্যবস্থাপক|ম্যানেজার)(?=[,\s]|$)[,\s]*")
SYL_OFFICE = {"আঞ্চলিক উপ-মহাব্যবস্থাপক": "আঞ্চলিক কার্যালয়", "আঞ্চলিক পরিচালক": "আঞ্চলিক কার্যালয়", "আঞ্চলিক ব্যবস্থাপক": "আঞ্চলিক কার্যালয়",
              "জি এম (বিভাগীয় অফিস)": "বিভাগীয় কার্যালয়", "জোনাল ম্যানেজার": "জোনাল অফিস", "এজিএম": "এজিএম কার্যালয়",
              "ডিজিএম": "ডিজিএম কার্যালয়"}
# Finance institutions on the lists that are not banks (top-level 'finance')
SYL_NOT_BANK = re.compile(r"^(আই ডি এল সি|আই\.সি\.বি|ন্যাশনাল ক্রেডিট লিমিটেড|শিল্প ঋণ সংস্থা)$")


def syl_row(dist, n, name, phone, extra, notes, address="", cat="finance.bank"):
    r = row(dist, "dpb-%s-%03d" % (dist.lower()[:3], n), name, phone, SYL_URLS[dist], extra, notes)
    r["source_key"], r["address"], r["category_key"] = SYL_KEY, address, cat
    return r


def main_sylhet():
    INTERMEDIATES.extend(u for u in SYL_INTERMEDIATES if u not in INTERMEDIATES)   # before the first request
    places, dropped, pages, n, skipped = [], {}, {}, {}, []
    for d, u in SYL_URLS.items():
        r = get(u)
        if r is None or not r.ok:
            print("unavailable", u)
            continue
        r.encoding = r.encoding or "utf-8"
        pages[d] = r.text
        # raw/: only the columns used (the e-mail column of Sylhet/Habiganj is left out); mobiles redacted
        rows = [c[:3] for tb in tables(widget_of(r.text)) for c in tb if any(c)]
        lines = [re.sub(_MOBILE_RAW, "[mobile redacted]", " | ".join(c)) for c in rows]
        save_raw(f"{d.lower()}_banks.txt", "URL: %s\n\n" % u + "\n".join(dict.fromkeys(lines)) + "\n")

    def keep(dist, s):
        """Landlines only: mobile numbers (also those run together with a landline) are removed first, then counted."""
        s = s or ""
        k = len(re.findall(_MOBILE_RAW, s))
        ph, dr = landline_only(re.sub(_MOBILE_RAW, " , ", s))
        dropped[dist] = dropped.get(dist, 0) + dr + k
        return ph

    def add(dist, name, phone, extra, notes, address="", cat="finance.bank"):
        n[dist] = n.get(dist, 0) + 1
        places.append(syl_row(dist, n[dist], nfc(re.sub(r"\s+", " ", name)).strip(" ,।|"), phone, extra, notes, address, cat))

    def rows_of(t):
        return [c for tb in tables(widget_of(t)) for c in tb]

    if "Sylhet" in pages:       # bank | '<post>, <place>, সিলেট' | numbers | e-mail (not copied)
        for c in rows_of(pages["Sylhet"]):
            if len(c) < 3 or c[0] in ("", "ব্যাংকের নাম"):
                continue
            bank, cell = nfc(c[0]).strip(" ।"), nfc(c[1]).strip(" ।")
            m = SYL_POST.match(cell)
            post = m.group(1) if m else ""
            rest = cell[m.end():] if m else cell
            parts = [x.strip(" ।") for x in re.split(r"\s*,\s*", rest) if x.strip(" ।")]
            place = parts[0] if parts and not re.match(r"^সিলেট(-[০-৯0-9]+)?$", parts[0]) else ""
            office = SYL_OFFICE.get(post, "")
            name = bank + (", " + place if place else ", সিলেট") + (" (%s)" % office if office else "")
            cat = "finance" if SYL_NOT_BANK.match(bank) else "finance.bank"
            add("Sylhet", name, keep("Sylhet", c[2]), {"bank_as_listed": c[0], "listed_as": c[1], "post_in_source": post or None},
                "From the Sylhet DC portal bank list (one cell '<post>, <branch/area>, সিলেট'; name = bank + the first place%s%s; the "
                "post is not part of the name). Only landlines are copied: mobile numbers and the e-mail column (mostly personal "
                "mail-provider addresses) are not. The list is undated; numbers after the first share its 0821 area code as printed."
                % (" + the office the post heads" if office else "", "; ', সিলেট' added: no place given" if not place else ""),
                ", ".join(parts), cat)
    if "Habiganj" in pages:     # bank | '<post>, <bank>' or '<bank>, <branch>' | 'অফিসঃ n বাসাঃ n' or n | e-mail (empty)
        for c in rows_of(pages["Habiganj"]):
            if len(c) < 3 or c[0] in ("", "ব্যাংকের নাম"):
                continue
            bank, cell = nfc(c[0]).strip(" ।"), nfc(c[1]).strip(" ।")
            m = SYL_POST.match(cell)
            post = m.group(1) if m else ""
            rest = cell[m.end():] if m else cell
            parts = [x.strip() for x in re.split(r"\s*,\s*", rest) if x.strip()]
            branch = next((x for x in parts if re.search(r"শাখা|শাঃ|শাখঅ", x)), "")
            # 'ডাচ্‌ বাংলা ব্যাংক লি. হবিগঞ্জ শাখা' (no comma): the branch is what follows the bank's name
            branch = re.sub(r"^.*ব্যাংক(?:\s*(?:লিমিটেড|লি\.|লিঃ))?\s*", "", branch) if "ব্যাংক" in branch else branch
            office = SYL_OFFICE.get(post, "")
            name = bank + (", " + branch if branch else ", হবিগঞ্জ") + (" (%s)" % office if office else "")
            office_no = re.sub(r"বাসা\s*[ঃ:].*$", "", asc(c[2]))
            nums = re.findall(r"\d{5,}", office_no)
            add("Habiganj", name, "", {"bank_as_listed": c[0], "listed_as": c[1], "post_in_source": post or None,
                                        "office_number_as_printed": "; ".join(nums) or None},
                "From the Habiganj DC portal bank list (name = bank + the branch named in the second cell%s). The office numbers are "
                "printed as 5-digit local numbers without an area code; they are kept in extra_json only, not as phone, and no "
                "area code is added. Residence ('বাসা') numbers are not copied." % ("; ', হবিগঞ্জ' added: no branch given" if not branch else ""))
    if "Moulvibazar" in pages:  # two tables: bank | branch or road (no numbers)
        for c in rows_of(pages["Moulvibazar"]):
            if len(c) < 2 or c[0] in ("", "নাম"):
                continue
            bank = re.sub(r"^[০-৯0-9]+\.\s*", "", nfc(c[0])).strip()
            where = nfc(c[1]).strip(" ।")
            if "/" in where or "বিভিন্ন" in where:
                skipped.append("%s (%s)" % (bank, where))
                continue
            add("Moulvibazar", "%s, %s" % (bank, where), "", {"bank_as_listed": c[0], "branch_as_listed": c[1]},
                "From the Moulvibazar DC portal bank list (bank and branch/road as printed; the list gives no numbers).",
                where if "শাখা" not in where else "")
    write_csv("places.csv", PLACE_COLS, places)
    write_manifest(dict(
        key=SYL_KEY, division="sylhet", kind="district_banks",
        name="District portals — bank branch/office lists (%s)" % ", ".join(SYL_URLS),
        organization="Deputy Commissioner's offices (district portals)", source_type="government_portal", trust_level=4,
        urls=list(SYL_URLS.values()) + list(SYL_OTHER.values()), accessed=__import__("datetime").date.today().isoformat(),
        publication_date=None, license=None, license_url=None,
        attribution="District portals " + ", ".join(urllib.parse.urlsplit(u).netloc for u in SYL_URLS.values()),
        notes="No licence stated; lists are undated. Only landline numbers are kept (mobile numbers dropped: %s); Habiganj's "
              "5-digit local office numbers (no area code printed) are kept in extra_json only; no e-mails, routing numbers, "
              "managers' names, residence numbers or coordinates. Moulvibazar rows naming several branches or 'various upazila "
              "branches' are left out (%s). Not used: Sunamganj (its bank list has names only; every branch/address/phone field "
              "is empty). sylhet.gov.bd sends only its leaf certificate: the Let's Encrypt intermediates are added from the CA's "
              "AIA URLs, TLS verification stays on." % (", ".join("%s %d" % kv for kv in dropped.items() if kv[1]) or "none",
                                                       "; ".join(skipped) or "none")),
        ["places.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


# --- DISTRICT_PORTAL_BANKS_MYM_2026 (Mymensingh Division) ------------------------------------------------------------
MYM_KEY = "DISTRICT_PORTAL_BANKS_MYM_2026"
MYM_URLS = {
    "Sherpur": "https://sherpur.gov.bd/pages/static-pages/6970a1e2a31054345f1624bd",     # '♣ <bank> - <branch>' blocks under upazila headings
    "Jamalpur": "https://jamalpur.gov.bd/pages/static-pages/69707648a31054345f15152c",   # numbered '<bank>, <branch> শাখা' lines; no numbers
    "Netrokona": "https://netrokona.gov.bd/pages/bank-financial-org",                    # framework list (bank, branch, address, phones)
}
# Checked but not usable (kept for the report / SOURCE.json urls)
MYM_OTHER = {
    "Mymensingh": "https://mymensingh.gov.bd/pages/bank-financial-org",   # empty list; the DC menu's 'ব্যাংক' entry links bb.org.bd
    "Netrokona (PDF)": "https://netrokona.gov.bd/pages/static-pages/697081d6a31054345f1560c0",  # PDF whose text layer is a legacy (non-Unicode) Bangla font
}
MYM_SHERPUR_UPA = {"শেরপুর সদর": "Sherpur Sadar", "নালিতাবাড়ি": "Nalitabari", "নালিতাবাড়ী": "Nalitabari", "ঝিনাইগাতি": "Jhenaigati",
                   "ঝিনাইগাতী": "Jhenaigati", "নকলা": "Nokla", "শ্রীবরদী": "Sreebordi"}
MYM_SHERPUR_UPA = {nfc(k): v for k, v in MYM_SHERPUR_UPA.items()}
_MYM_PHONE = r"(?<![০-৯0-9])[০0][০-৯0-9]{2,4}-[০-৯0-9]{5,7}(?:\s*,\s*[০-৯0-9]{5,6}(?![০-৯0-9]))*"   # landline '0931-61318,61403' (as printed)


def mym_row(dist, n, name, phone, url, extra, notes, address="", upa=""):
    r = row(dist, "dpb-%s-%03d" % (dist.lower()[:3], n), name, phone, url, extra, notes, upa)
    r["source_key"], r["address"] = MYM_KEY, address
    return r


def main_mymensingh():
    places, dropped, pages, n, skipped = [], {}, {}, {}, []
    for d, u in MYM_URLS.items():
        r = get(u)
        if r is None or not r.ok:
            print("unavailable", u)
            continue
        r.encoding = r.encoding or "utf-8"
        pages[d] = r.text

    def add(dist, name, phone, extra, notes, address="", upa=""):
        n[dist] = n.get(dist, 0) + 1
        nm = nfc(re.sub(r"\s+", " ", re.sub(r"\s+,", ",", name))).strip(" ,।|-")
        places.append(mym_row(dist, n[dist], nm, phone, MYM_URLS[dist], extra, notes, address, upa))

    if "Sherpur" in pages:      # '♣ <bank> , <branch>' / '♣ <bank> - <branch>' then address, phone and e-mail lines; upazila headings
        lines = [re.sub(r"[​‌‍]", "", l).strip() for l in content_text(pages["Sherpur"])]
        save_raw("sherpur_banks.txt", "URL: %s\n\n" % MYM_URLS["Sherpur"] + "\n".join(
            re.sub(_MOBILE_RAW, "[mobile redacted]", l) for l in lines if not re.search(r"@|E-mail|ইমেল", l)) + "\n")
        blocks, upa = [], ""
        for l in lines:
            h = re.match(r"^(.+?)\s*উপজেলা\s*,?$", l)
            if h and nfc(h.group(1)) in MYM_SHERPUR_UPA:
                upa = MYM_SHERPUR_UPA[nfc(h.group(1))]
                continue
            if l.startswith("♣"):
                blocks.append([upa, l.lstrip("♣ ").strip()])
            elif blocks:
                blocks[-1].append(l)
        seen = {}
        for b in blocks:
            upa, head, rest = b[0], b[1], b[2:]
            m = re.match(r"^(.*?ব্যাংক[^,\-]*?)\s*[,\-]\s*(.*)$", head)
            bank, branch = (nfc(m.group(1)), nfc(m.group(2)).strip(" ,-")) if m else (nfc(head), "")
            phones, addr, emails, mob, doubtful, extension = [], [], [], 0, [], None
            for l in rest:
                if re.search(r"@", l):
                    emails += re.findall(r"[\w.\-]+@[\w.\-]+", l)
                    continue
                mob += len(re.findall(_MOBILE_RAW, l))
                l2 = re.sub(_MOBILE_RAW, " ", l)
                for ph in re.findall(_MYM_PHONE, l2):
                    for i, part in enumerate(re.split(r"\s*,\s*", ph)):
                        if re.search(r"[০-৯]", part) and re.search(r"[0-9]", part):   # '৬১২৩৮8': Bangla and ASCII digits mixed
                            doubtful.append(part)
                            continue
                        phones.append(asc(part))
                ext = re.search(r"এক্সটেনশা?ন\s*([০-৯0-9]+)", l2)
                if ext:
                    extension = asc(ext.group(1))
                l2 = re.sub(_MYM_PHONE, " ", l2)
                l2 = re.sub(r"^(টেলিফোন|মোবাইল|ফোন)\s*[:ঃ]?", "", l2.strip()).strip(" .,:।")
                l2 = re.sub(r"\s*[\d০-৯]+\s*(এক্সটেনশা?ন\s*[০-৯0-9]+)?$", lambda x: "" if x.group(1) or not l2.strip() else x.group(0), l2)
                if re.sub(r"[\s.,:।0-9০-৯]|এক্সটেনশা?ন", "", l2):
                    addr.append(nfc(re.sub(r"\s+", " ", re.sub(r"\s+([,.।])", r"\1", l2))).strip(" .,"))
            dropped["Sherpur"] = dropped.get("Sherpur", 0) + mob
            key = tuple(emails) or None
            if key and key in seen:
                skipped.append("Sherpur: '%s' repeats the entry '%s' (same e-mail and number)" % (head, seen[key]))
                continue
            if key:
                seen[key] = head
            note_branch = ""
            if not branch and addr:
                branch, note_branch = addr[0], " The heading names no branch: the first address line is used as the place."
            add("Sherpur", bank + (", " + branch if branch else ""), "; ".join(dict.fromkeys(phones)),
                {"heading_as_listed": head, "upazila_heading": upa or None, "extension_as_printed": extension,
                 "number_not_copied_as_printed": "; ".join(doubtful) or None},
                "From the Sherpur DC portal bank page (headings '♣ <bank> - <branch>', grouped under upazila headings; upazila_en from "
                "the heading). Only landlines are copied as printed (numbers after the first share its area code); mobile numbers "
                "and the e-mail lines (bangla.net / bank-domain addresses, not government) are not." + note_branch
                + (" A number printed with Bangla and ASCII digits mixed is not copied (extra_json)." if doubtful else ""),
                ", ".join(a for a in addr if a != branch or note_branch == ""), upa)
    if "Jamalpur" in pages:     # numbered '<bank>, <branch> শাখা।' lines (one cell per row); no numbers or addresses
        rows = [c for tb in tables(widget_of(pages["Jamalpur"])) for c in tb if any(c)]
        save_raw("jamalpur_banks.txt", "URL: %s\n\n" % MYM_URLS["Jamalpur"] + "\n".join(" | ".join(c) for c in rows) + "\n")
        seen = set()
        for c in rows:
            listed = c[0]
            m = re.match(r"^([০-৯0-9]+)\s*[।.]\s*(.+)$", listed)
            if not m:
                continue
            name = re.sub(r"\s*শাখা(\s*শাখা)+", " শাখা", nfc(m.group(2))).strip(" ।")
            name = re.sub(r"(লিঃ|লিমিটেড)\s+(?=\S)", r"\1, ", name) if "," not in name else name
            name = re.sub(r",(?=\S)", ", ", name)
            if name in seen:
                skipped.append("Jamalpur: '%s' is listed twice (kept once)" % listed)
                continue
            seen.add(name)
            add("Jamalpur", name, "", {"listed_as": listed, "serial_as_listed": asc(m.group(1))},
                "From the Jamalpur DC portal bank page (numbered '<bank>, <branch> শাখা' lines; serial 9 is printed twice). The list "
                "gives no numbers or addresses.")
    if "Netrokona" in pages:    # framework list: title | type | branch_name | branch_address | head/contact phones (names not copied)
        rows = []
        for tr in re.findall(r'<tr class="table-tr">(.*?)</tr>', pages["Netrokona"], re.S):
            d = {k: clean(v) for k, v in re.findall(r'<td class="table-td[^"]*" data-column="([^"]*)"[^>]*>(.*?)</td>', tr, re.S)}
            if d.get("title"):
                rows.append(d)
        keep_cols = ("id", "title", "type", "branch_name", "branch_address", "head_phone", "contact_person_phone")
        save_raw("netrokona_banks.txt", "URL: %s\n\n" % MYM_URLS["Netrokona"] + "\n".join(
            re.sub(_MOBILE_RAW, "[mobile redacted]", " | ".join(r.get(k, "") for k in keep_cols)) for r in rows) + "\n")
        for r in rows:
            nums = []
            for k in ("head_phone", "contact_person_phone", "head_mobile", "contact_person_mobile"):
                v = r.get(k, "")
                dropped["Netrokona"] = dropped.get("Netrokona", 0) + len(re.findall(_MOBILE_RAW, v))
                if k.endswith("_phone"):
                    for ph in re.findall(r"[০0][০-৯0-9\-]{8,11}(?:\s*এক্সট-?\s*[০-৯0-9]+)?", re.sub(_MOBILE_RAW, " ", v)):
                        nums.append(re.sub(r"\s*এক্সট-?\s*", " ext ", asc(ph)))
            uniq = list(dict.fromkeys(re.sub(r"\s*ext.*$", "", x).replace("-", "") for x in nums))
            phones = []
            for u in uniq:   # keep the first spelling of each number (with its extension, if printed)
                phones.append(next(x for x in nums if re.sub(r"\s*ext.*$", "", x).replace("-", "") == u))
            add("Netrokona", "%s, %s" % (r["title"], r.get("branch_name", "")) if r.get("branch_name") else r["title"],
                "; ".join(phones), {"bank_as_listed": r["title"], "branch_as_listed": r.get("branch_name") or None,
                                     "type_as_listed": r.get("type") or None},
                "From the Netrokona DC portal list 'ব্যাংক/আর্থিক সংস্থা' (bank, branch, address, phone). Only the landline "
                "phone fields are copied ('এক্সট' = extension); mobile fields, heads' and contact persons' names are not.",
                "" if r.get("branch_address") in ("", "নাই") else r["branch_address"])
    write_csv("places.csv", PLACE_COLS, places)
    write_manifest(dict(
        key=MYM_KEY, division="mymensingh", kind="district_banks",
        name="District portals — bank branch lists (%s)" % ", ".join(d for d in MYM_URLS if d in pages),
        organization="Deputy Commissioner's offices (district portals)", source_type="government_portal", trust_level=4,
        urls=list(MYM_URLS.values()) + list(MYM_OTHER.values()), accessed=__import__("datetime").date.today().isoformat(),
        publication_date=None, license=None, license_url=None,
        attribution="District portals " + ", ".join(urllib.parse.urlsplit(u).netloc for d, u in MYM_URLS.items() if d in pages),
        notes="No licence stated; the lists are undated. Only landline numbers are kept (mobile numbers dropped: %s); no e-mails "
              "(none is a government address), managers' or contact persons' names, routing numbers or coordinates. Repeated "
              "entries left out: %s. Not used: Mymensingh (the DC portal's bank list is empty and its menu links only bb.org.bd), "
              "the Netrokona bank PDF (its text layer is a legacy non-Unicode Bangla font; the portal's own list is used instead)."
              % (", ".join("%s %d" % kv for kv in dropped.items() if kv[1]) or "none", "; ".join(skipped) or "none")),
        ["places.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


SITES = {"rajshahi": dict(folder="district_portal_banks_raj_2026"), "rangpur": dict(folder="district_portal_banks_rang_2026", run=main_rangpur),
         "dhaka": dict(folder="district_portal_banks_dhk_2026", run=main_dhaka),
         "chattogram": dict(folder="district_portal_banks_ctg_2026", run=main_chattogram),
         "khulna": dict(folder="district_portal_banks_khl_2026", run=main_khulna),
         "barishal": dict(folder="district_portal_banks_bar_2026", run=main_barishal),
         "sylhet": dict(folder="district_portal_banks_syl_2026", run=main_sylhet),
         "mymensingh": dict(folder="district_portal_banks_mym_2026", run=main_mymensingh)}


def configure():
    global DIVISION, HERE, RAW
    DIVISION, out = parse_division_args({k: v["folder"] for k, v in SITES.items()})
    HERE = Path(out)
    RAW = HERE / "raw"


if __name__ == "__main__":
    main()
