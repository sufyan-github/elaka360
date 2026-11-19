#!/usr/bin/env python3
"""Fetch metropolitan police thanas & official numbers (default Rajshahi Metropolitan Police, rmp.gov.bd, RMP_THANAS_2026).

Usage: python3 fetch.py [--division rangpur|dhaka|chattogram|khulna|barishal|sylhet] [--city dhaka|gazipur|chattogram|khulna|barishal|sylhet] [--out DIR]  (rangpur: rpmp.gov.bd ->
RANGPUR_METRO_POLICE_THANAS_2026; dhaka: dmp.gov.bd -> DHAKA_METRO_POLICE_THANAS_2026, gmp.gov.bd -> GAZIPUR_METRO_POLICE_THANAS_2026;
chattogram: cmp.gov.bd + police.chittagongdiv.gov.bd -> CHATTOGRAM_METRO_POLICE_THANAS_2026; khulna: police.khulnadiv.gov.bd ->
KHULNA_METRO_POLICE_THANAS_2026; barishal: bmp.police.gov.bd + police.barisaldiv.gov.bd -> BARISHAL_METRO_POLICE_THANAS_2026; sylhet:
police.sylhetdiv.gov.bd + smp.police.gov.bd -> SYLHET_METRO_POLICE_THANAS_2026)."""
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

# --- RMP_THANAS_2026 ----------------------------------------------------------------------------------
KEY = "RMP_THANAS_2026"
URL_UNITS = "https://rmp.gov.bd/pages/static-pages/695e3b08c4774958d7b7214e"    # সকল ইউনিটসমূহ (unit mobile numbers)
URL_CONTACT = "https://rmp.gov.bd/pages/static-pages/695e3b0ac4774958d7b721f0"  # ডাক ও টেলি যোগাযোগ (HQ)
URL_GLANCE = "https://rmp.gov.bd/pages/static-pages/695e3b09c4774958d7b72177"   # এক নজরে আরএমপি
# Standard English names of the RMP (metropolitan) thanas; the source is Bangla only.
THANA_EN = {"বোয়ালিয়া": "Boalia", "রাজপাড়া": "Rajpara", "চন্দ্রিমা": "Chandrima", "মতিহার": "Motihar",
            "কাটাখালি": "Katakhali", "কাটাখালী": "Katakhali", "বেলপুকুর": "Belpukur", "শাহমখদুম": "Shah Makhdum",
            "এয়ারপোর্ট": "Airport", "পবা": "Paba", "কাশিয়াডাঙ্গা": "Kashiadanga", "দামকুড়া": "Damkura", "কর্ণহার": "Karnahar"}


def main():
    configure()
    if DIVISION != "rajshahi":
        return SITES[DIVISION]["run"]()
    places, facts = [], []
    r = get(URL_UNITS)
    if r is not None and r.ok:
        save_raw("rmp_units.txt", "\n".join(content_text(r.text)))
        zone = ""
        for t in tables(r.text):
            for row in t:
                if len(row) < 3:
                    continue
                label, phone = row[1], phone_norm(row[2])
                m = re.match(r"উপ-পুলিশ কমিশনার, (.+?) ডিবিশন", label)
                if m:
                    zone = m.group(1)
                    continue
                m = re.match(r"অফিসার ইনচার্জ, (.+?) থানা", label)
                if not m:
                    continue
                th = nfc(m.group(1))
                places.append(dict(
                    source_key=KEY, source_id=f"rmp-thana-{THANA_EN.get(th, th).lower().replace(' ', '-')}",
                    name_bn=f"{th} থানা", name_en="", category_key="emergency.police_station",
                    district_en="Rajshahi", upazila_en=THANA_EN.get(th, ""), phone=phone,
                    operator="রাজশাহী মেট্রোপলিটন পুলিশ (আরএমপি)", ownership="public",
                    extra_json=xj({"unit": "metropolitan_thana", "police_force": "RMP", "rmp_division_bn": f"{zone} ডিবিশন" if zone else "",
                                   "phone_role": "অফিসার ইনচার্জ (OC) — official mobile", "label_in_source": label}),
                    source_url=URL_UNITS,
                    notes="upazila_en holds the RMP metropolitan thana (not an upazila). Phone is the OC's official number as published by RMP."))
    r = get(URL_CONTACT)
    if r is not None and r.ok:
        save_raw("rmp_contact.txt", "\n".join(content_text(r.text)))
        lines = content_text(r.text)
        txt = "\n".join(lines)
        ph = re.search(r"ফোন:\s*([+০-৯0-9\- ]+)", txt)
        mob = re.search(r"মোবাইল:\s*([+০-৯0-9\- ]+)", txt)
        fax = re.search(r"ফ্যাক্স:\s*([+০-৯0-9\- ]+)", txt)
        addr = next((l for l in lines if "রাজশাহী-" in l), "")
        places.append(dict(
            source_key=KEY, source_id="rmp-hq", name_bn="রাজশাহী মেট্রোপলিটন পুলিশ হেডকোয়ার্টার্স", name_en="",
            category_key="government.sp_office", address=addr, district_en="Rajshahi",
            phone="; ".join(asc(x.group(1)).replace(" ", "") for x in (ph, mob) if x), operator="বাংলাদেশ পুলিশ", ownership="public",
            extra_json=xj({"office": "পুলিশ কমিশনারের কার্যালয়", "fax": asc(fax.group(1)).replace(" ", "") if fax else ""}),
            source_url=URL_CONTACT,
            notes="Police Commissioner's office (metropolitan equivalent of an SP office) — closest taxonomy key government.sp_office."))
    r = get(URL_GLANCE)
    if r is not None and r.ok:
        txt = asc(" ".join(content_text(r.text)))
        m = re.search(r"বর্তমান আয়তন ([\d.,]+) বর্গ কিলোমিটার", txt)
        if m:
            facts.append(dict(entity_level="metropolitan_police", entity_name_en="Rajshahi Metropolitan Police area", district_en="Rajshahi",
                              fact="area_km2", value=m.group(1).replace(",", ""), unit="km2", basis="reported", year="",
                              source_key=KEY, source_url=URL_GLANCE, notes="RMP jurisdiction area ('বর্তমান আয়তন'); not the city-corporation area"))
        m = re.search(r"জনসংখ্যা ([\d,]+) জন", txt)
        if m:
            facts.append(dict(entity_level="metropolitan_police", entity_name_en="Rajshahi Metropolitan Police area", district_en="Rajshahi",
                              fact="population", value=m.group(1).replace(",", ""), unit="persons", basis="reported", year="",
                              source_key=KEY, source_url=URL_GLANCE, notes="RMP jurisdiction population as stated by RMP; year not given"))
        m = re.search(r"হয় (\d+)টি থানা", txt)
        if m:
            facts.append(dict(entity_level="metropolitan_police", entity_name_en="Rajshahi Metropolitan Police area", district_en="Rajshahi",
                              fact="police_stations", value=m.group(1), unit="thanas", basis="reported", year=2018,
                              source_key=KEY, source_url=URL_GLANCE, notes="12 thanas since 22 Feb 2018 per RMP"))
    write_csv("places.csv", PLACE_COLS, places)
    write_csv("facts.csv", FACT_COLS, facts)
    write_manifest(dict(
        key=KEY, division="rajshahi", kind="metro_police_thanas", name="Rajshahi Metropolitan Police — thanas and official numbers", organization="Rajshahi Metropolitan Police (Bangladesh Police)",
        source_type="government_portal", trust_level=4, urls=[URL_UNITS, URL_CONTACT, URL_GLANCE],
        accessed=__import__("datetime").date.today().isoformat(), publication_date=None, license=None, license_url=None,
        attribution="Rajshahi Metropolitan Police (rmp.gov.bd)",
        notes="No licence stated. Only institutional numbers (OC official mobiles, HQ phone/fax) are collected; no officer names. "
              "No addresses (except HQ) or coordinates are published for thanas."),
        ["places.csv", "facts.csv", "raw/rmp_units.txt", "raw/rmp_contact.txt"])


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


# --- Rangpur Metropolitan Police (rpmp.gov.bd, RpMP's own site) -------------------------------------------------------
RP_KEY = "RANGPUR_METRO_POLICE_THANAS_2026"
RP_UNITS = "https://rpmp.gov.bd/index.php/home/units"                      # ইউনিট ও যোগাযোগের নাম্বার সমূহ
RP_DIRECTORY = "https://rpmp.gov.bd/index.php/home/telephone_directory"    # টেলিফোন ডিরেক্টরি (Police Commissioner's office)
RP_CONTACT = "https://rpmp.rangpurdiv.gov.bd/pages/static-pages/69771cd5c4774958d7c06d89"  # অফিস যোগাযোগ (address)
RP_THANA_EN = {"কোতয়ালী": "Kotwali", "তাজহাট": "Tajhat", "মাহিগঞ্জ": "Mahiganj", "হারাগাছ": "Haragach", "পরশুরাম": "Parshuram",
               "হাজিরহাট": "Hajirhat"}
RP_OP = "রংপুর মেট্রোপলিটন পুলিশ (আরপিএমপি)"


def rp_contacts(cell):
    """'মোবাইল-০১৩২০-০৭৩৪৭৫ টেলিফোন-০২-৫৮৯৯৬১১৪৮ ইমেইল- x@police.gov.bd' -> dict (ASCII digits, source grouping)."""
    c = asc(cell)
    out = {}
    for k, lab in (("mobile", "মোবাইল"), ("telephone", "টেলিফোন"), ("fax", "ফ্যাক্স")):
        m = re.search(lab + r"\s*-\s*([+\d][\d\- ]{5,}\d)", c)
        if m and not m.group(1).rstrip("-").endswith("--"):
            out[k] = re.sub(r"\s+", "", m.group(1))
    m = re.search(r"[A-Za-z0-9][A-Za-z0-9._]*@police\.gov\.bd", c.replace(" ", ""))
    if m:
        out["email"] = m.group(0)
    return out


def rp_rows(url):
    r = get(url)
    if r is None or not r.ok:
        print("unavailable:", url)
        return []
    rows = [row for tb in tables(r.text) for row in tb if len(row) >= 2 and row[0] != "পদবী"]
    return rows


def main_rangpur():
    places, facts = [], []
    rows = rp_rows(RP_UNITS)
    save_raw("rpmp_units.txt", "\n".join(" | ".join(r) for r in rows))
    cur = None
    by_thana = {}
    for label, cell in ((r[0], r[1]) for r in rows):
        c = rp_contacts(cell)
        m = re.match(r"অফিসার ইনচার্জ,\s*(.+?) থানা$", label)
        if m:
            th = nfc(m.group(1))
            cur = th
            en = RP_THANA_EN.get(th, "")
            rec = dict(source_key=RP_KEY, source_id="rpmp-thana-%s" % (en.lower() or th), name_bn="%s থানা" % th, name_en="",
                       category_key="emergency.police_station", district_en="Rangpur", upazila_en=en,
                       phone="; ".join(x for x in (c.get("mobile"), c.get("telephone")) if x), email=c.get("email", ""),
                       operator=RP_OP, ownership="public",
                       _extra={"unit": "metropolitan_thana", "police_force": "RpMP", "oc_mobile": c.get("mobile"),
                               "thana_telephone": c.get("telephone"), "label_in_source": label},
                       source_url=RP_UNITS,
                       notes="upazila_en holds the RpMP metropolitan thana (not an upazila). Phone = OC's official mobile and the thana "
                             "telephone as published by RpMP.")
            by_thana[th] = rec
            places.append(rec)
            continue
        m = re.match(r"ডিউটি অফিসার,\s*(.+?) থানা$", label)
        if m and nfc(m.group(1)) in by_thana:
            by_thana[nfc(m.group(1))]["_extra"].update(duty_officer_mobile=c.get("mobile"), duty_officer_telephone=c.get("telephone"))
            continue
        m = re.match(r"ইনচার্জ,\s*(.+?পুলিশ ফাঁড়ি)$", label)
        if m:
            places.append(dict(source_key=RP_KEY, source_id="rpmp-outpost-%d" % (sum(1 for p in places if p["category_key"] == "emergency.police_outpost") + 1),
                               name_bn=nfc(m.group(1)), name_en="", category_key="emergency.police_outpost", district_en="Rangpur",
                               upazila_en=RP_THANA_EN.get(cur, ""), phone=c.get("mobile", ""), email=c.get("email", ""), operator=RP_OP,
                               ownership="public", _extra={"police_force": "RpMP", "listed_under_thana": cur, "label_in_source": label},
                               source_url=RP_UNITS, notes="Police outpost listed under %s thana; phone = in-charge's official mobile." % cur))
            continue
        if label == "কন্ট্রোল রুম":
            places.append(dict(source_key=RP_KEY, source_id="rpmp-control-room", name_bn="আরপিএমপি কন্ট্রোল রুম", name_en="",
                               category_key="emergency", district_en="Rangpur",
                               phone="; ".join(x for x in (c.get("mobile"), c.get("telephone")) if x), operator=RP_OP, ownership="public",
                               _extra={"fax": c.get("fax"), "label_in_source": label}, source_url=RP_UNITS,
                               notes="Name composed from the 'কন্ট্রোল রুম' row of the RpMP units page."))
    hot = next((rp_contacts(r[1]).get("mobile") for r in rows if r[0].startswith("আরপিএমপি, হটলাইন")), None)
    for p in places:
        if p["source_id"] == "rpmp-control-room" and hot:
            p["_extra"]["rpmp_hotline"] = hot
    # Police Commissioner's office (HQ)
    drows = rp_rows(RP_DIRECTORY)
    pc = next((r for r in drows if r[0] == "পুলিশ কমিশনার"), None)
    addr = ""
    r = get(RP_CONTACT)
    if r is not None and r.ok:
        m = re.search(r"কাচারী বাজার, রংপুর-[০-৯]+", " ".join(content_text(r.text)))
        addr = m.group(0) if m else ""
    if pc:
        c = rp_contacts(pc[1])
        save_raw("rpmp_directory_commissioner.txt", " | ".join(pc))
        places.append(dict(source_key=RP_KEY, source_id="rpmp-hq", name_bn="রংপুর মেট্রোপলিটন পুলিশ হেডকোয়ার্টার্স", name_en="",
                           category_key="government.sp_office", address=addr, district_en="Rangpur",
                           phone="; ".join(x for x in (c.get("telephone"), c.get("mobile")) if x), email=c.get("email", ""),
                           operator="বাংলাদেশ পুলিশ", ownership="public",
                           _extra={"office": "পুলিশ কমিশনারের কার্যালয়", "fax": c.get("fax"), "address_source": RP_CONTACT if addr else None},
                           source_url=RP_DIRECTORY,
                           notes="Police Commissioner's office (metropolitan equivalent of an SP office) — closest taxonomy key "
                                 "government.sp_office. Numbers of the Police Commissioner post (telephone directory); address from "
                                 "rpmp.rangpurdiv.gov.bd 'অফিস যোগাযোগ'."))
    for p in places:
        p["extra_json"] = xj(p.pop("_extra", {}))
    n = sum(1 for p in places if p["category_key"] == "emergency.police_station")
    facts.append(dict(entity_level="metropolitan_police", entity_name_en="Rangpur Metropolitan Police area", district_en="Rangpur",
                      fact="police_stations", value=n, unit="thanas", basis="listed", year=2026, source_key=RP_KEY, source_url=RP_UNITS,
                      notes="Counted from OC rows of the RpMP units page"))
    write_csv("places.csv", PLACE_COLS, places)
    write_csv("facts.csv", FACT_COLS, facts)
    write_manifest(dict(
        key=RP_KEY, division="rangpur", kind="metro_police_thanas", name="Rangpur Metropolitan Police — thanas and official numbers",
        organization="Rangpur Metropolitan Police (Bangladesh Police)", source_type="government_portal", trust_level=4,
        urls=[RP_UNITS, RP_DIRECTORY, RP_CONTACT], accessed=__import__("datetime").date.today().isoformat(), publication_date=None,
        license=None, license_url=None, attribution="Rangpur Metropolitan Police (rpmp.gov.bd)",
        notes="No licence stated. Only institutional numbers (OC / outpost in-charge official mobiles, thana telephones, HQ and "
              "control-room numbers, *@police.gov.bd e-mails) are collected; no officer names. No thana addresses or coordinates "
              "are published (zone offices give street hints only)."),
        ["places.csv", "facts.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


# --- Dhaka Division: DMP and GMP thanas, one folder per force (DIVISIONS.md); SOURCE.json carries "city" ------------
# DMP police stations as dmp.gov.bd 'Find Your Local Police' spells them -> (Bangla name as on the Dhaka DC portal's
# city-corporation thana list, English name used elsewhere in these sources). Khilkhet is not on the DC list: its Bangla
# spelling is the locality name on DNCC's ward list. Hatirjheel is on the DC list but not on the DMP page.
DMP_THANAS = {
    "Adabor": ("আদাবর", "Adabor"), "Badda": ("বাড্ডা", "Badda"), "Banani": ("বনানী", "Banani"), "Bangshal": ("বংশাল", "Bangshal"),
    "Bimanbandar": ("বিমানবন্দর", "Biman Bandar"), "Cantonment": ("ক্যান্টনমেন্ট", "Cantonment"), "Chalkbazar": ("চকবাজার", "Chawkbazar"),
    "Dakshin Khan": ("দক্ষিণখান", "Dakshinkhan"), "Darus-Salam": ("দারুস সালাম", "Darus Salam"), "Demra": ("ডেমরা", "Demra"),
    "Dhanmondi": ("ধানমন্ডি", "Dhanmondi"), "Gandaria": ("গেন্ডারিয়া", "Gandaria"), "Gulshan": ("গুলশান", "Gulshan"),
    "Hazaribag": ("হাজারীবাগ", "Hazaribagh"), "Jattrabari": ("যাত্রাবাড়ী", "Jatrabari"), "Kafrul": ("কাফরুল", "Kafrul"),
    "Kalabagan": ("কলাবাগান", "Kalabagan"), "Kamrangirchar": ("কামরাঙ্গীরচর", "Kamrangirchar"), "Khilgoan": ("খিলগাঁও", "Khilgaon"),
    "Khilkhet": ("খিলক্ষেত", "Khilkhet"), "Kodomtali": ("কদমতলী", "Kadamtali"), "Kotwali": ("কোতোয়ালী", "Kotwali"),
    "Lalbagh": ("লালবাগ", "Lalbagh"), "Mirpur Model": ("মিরপুর", "Mirpur"), "Mohammadpur": ("মোহাম্মদপুর", "Mohammadpur"),
    "Motijheel": ("মতিঝিল", "Motijheel"), "Mugda": ("মুগদা", "Mugda"), "New Market": ("নিউমার্কেট", "New Market"),
    "Pallabi": ("পল্লবী", "Pallabi"), "Paltan": ("পল্টন", "Paltan"), "Ramna": ("রমনা", "Ramna"), "Rampura": ("রামপুরা", "Rampura"),
    "Rupnagar": ("রূপনগর", "Rupnagar"), "Sabujbag": ("সবুজবাগ", "Sabujbagh"), "Shah Ali": ("শাহআলী", "Shah Ali"),
    "Shahbag": ("শাহবাগ", "Shahbagh"), "Shahjahanpur": ("শাহজাহানপুর", "Shahjahanpur"), "Sutrapur": ("সূত্রাপুর", "Sutrapur"),
    "Shyampur": ("শ্যামপুর", "Shyampur"), "Sher e Bangla Nagar": ("শেরেবাংলা নগর", "Sher-e-Bangla Nagar"),
    "Tejgoan Industrial": ("তেজগাঁও শিল্পাঞ্চল", "Tejgaon Industrial Area"), "Tejgoan": ("তেজগাঁও", "Tejgaon"), "Turag": ("তুরাগ", "Turag"),
    "Uttara East": ("উত্তরা পূর্ব", "Uttara East"), "Uttara West": ("উত্তরা পশ্চিম", "Uttara West"), "Uttar Khan": ("উত্তরখান", "Uttar Khan"),
    "Bsahantek": ("ভাষানটেক", "Bhashantek"), "Vatara": ("ভাটারা", "Bhatara"), "Wari": ("ওয়ারী", "Wari"),
}
DMP_EXTRA = {"Hatirjheel": ("হাতিরঝিল", "Hatirjheel")}   # on the DC portal list only
DMP_LOCAL = "https://dmp.gov.bd/find-your-local-police/"
DMP_HISTORY = "https://dmp.gov.bd/history/"
DMP_UNITS = "https://dmp.gov.bd/units/"
DMP_CONTACT = "https://dmp.gov.bd/contact-us/"
DHAKA_DC_GLANCE = "https://dhaka.gov.bd/pages/static-pages/6995bedb35ce18e1c079f6b8"   # 'এক নজরে ঢাকা জেলা' (city thana list)
DMP_CC_NOTE = ("No official source found that places this DMP thana in Dhaka North or Dhaka South City Corporation (dmp.gov.bd, "
               "dncc.gov.bd, dscc.gov.bd and the Dhaka DC portal give no thana-to-city-corporation list; DSCC only gives a count of "
               "23 thanas), so area_en is left empty.")
GMP_THANAS = [  # zone_id on gmp.gov.bd, menu name, Bangla (GMP "About GMP"), English used here (menu spelling; "Sadar" -> "Gazipur Sadar"), zone, crime division
    (1, "Sadar", "গাজীপুর সদর", "Gazipur Sadar", "সদর জোন", "অপরাধ উত্তর"), (2, "Bason", "বাসন", "Bason", "সদর জোন", "অপরাধ উত্তর"),
    (3, "Konabari", "কোনাবাড়ী", "Konabari", "কোনাবাড়ী জোন", "অপরাধ উত্তর"), (4, "Kashimpur", "কাশিমপুর", "Kashimpur", "কোনাবাড়ী জোন", "অপরাধ উত্তর"),
    (5, "Gacha", "গাছা", "Gacha", "গাছা জোন", "অপরাধ দক্ষিণ"), (6, "Pubail", "পূবাইল", "Pubail", "গাছা জোন", "অপরাধ দক্ষিণ"),
    (7, "Tongi East", "টঙ্গী পূর্ব", "Tongi East", "টঙ্গী জোন", "অপরাধ দক্ষিণ"), (8, "Tongi West", "টঙ্গী পশ্চিম", "Tongi West", "টঙ্গী জোন", "অপরাধ দক্ষিণ"),
]
GMP_HISTORY = "https://gmp.gov.bd/history.php"
GMP_CONTACT = "https://gmp.gov.bd/contact-us.php"
GMP_THANA_URL = "https://gmp.gov.bd/range-units/units_details.php?zone_id=%d"
GMP_CC_NOTE = ("GMP's 'About GMP' says the metropolitan area consists of the 57 wards of Gazipur City Corporation "
               "('গাজীপুর সিটি কর্পোরেশনের ৫৭টি ওয়ার্ড নিয়ে গঠিত এই মেট্রোপলিটন এলাকা'), so every GMP thana lies in it.")


def _num(s):
    """'+88-02-9133265' -> '02-9133265'; '+8801713373183' -> '01713373183'; '' for empty/placeholder values."""
    s = asc(s or "").strip().rstrip(",.;")
    s = re.sub(r"^\+?88-?(?=0)", "", s)
    return s if re.search(r"\d{6}", re.sub(r"\D", "", s)) else ""


def page_text(url):
    r = get(url)
    if r is None or not r.ok:
        print("unavailable:", url)
        return ""
    r.encoding = r.encoding or "utf-8"
    return r.text


def main_dmp():
    places, facts = [], []
    t = page_text(DMP_LOCAL)
    lines = content_text(t)
    try:
        lines = lines[lines.index("Find Your Local Police", 1):]
    except ValueError:
        pass
    lines = lines[:next((i for i, l in enumerate(lines) if l.startswith("Comments are closed")), len(lines))]
    blocks, cur = [], None
    for l in lines:
        m = re.match(r"^(.+?) ?Police Station$", l)
        if m:
            cur = [re.sub(r"(?<=[a-z])(?=Police)", " ", m.group(1)).strip(), []]
            blocks.append(cur)
        elif cur is not None:
            cur[1].append(l)
    for en_dmp, body in blocks:
        flat = " ".join(body)
        bn, en = DMP_THANAS.get(en_dmp, ("", ""))
        addr = re.search(r"Address:\s*(.*?)\s*Duty Officer", flat)
        duty = re.search(r"Duty Officer:(.*?)(?:Officers In charge:|$)", flat)
        oc = re.search(r"Officers In charge:(.*)$", flat)
        d, o = (duty.group(1) if duty else ""), (oc.group(1) if oc else "")
        tts = [_num(x) for x in (re.search(r"T&T:\s*([+\d\-, ]+)", d) or re.search(r"^\s*([+\d\-]{8,})", d) or [None, ""])[1].split(",")]
        tt = "; ".join(dict.fromkeys(x for x in tts if x))
        label = (re.match(r"^(.+?Police Station):", body[0]) if body else None)
        dcell = _num((re.search(r"(?<!Investigation )Cell:\s*([+\d\- ]+)", d) or [None, ""])[1])
        occell = _num((re.search(r"Cell:\s*([+\d\- ]+)", o) or [None, ""])[1])
        fax = _num((re.search(r"Fax:\s*([+\d\- ]+)", o) or [None, ""])[1])
        em = re.search(r"[\w.]+@dmp\.gov\.bd", o)
        ext = (re.search(r"DMP:\s*([\d, ]+?)(?=\s*(?:T&T|Cell|$))", o) or [None, ""])[1].strip(" ,")
        places.append(dict(
            source_key=CITY["key"], source_id="dmp-thana-%s" % (en.lower().replace(" ", "-") or en_dmp.lower().replace(" ", "-")),
            name_bn=("%s থানা" % bn) if bn else "", name_en="%s Police Station" % en_dmp, category_key="emergency.police_station",
            address=(addr.group(1).strip(" ,") if addr else ""), district_en="Dhaka", upazila_en=en,
            phone="; ".join(x for x in (tt, occell) if x) or dcell, email=em.group(0) if em else "",
            operator="ঢাকা মেট্রোপলিটন পুলিশ (ডিএমপি)", ownership="public",
            extra_json=xj({"unit": "metropolitan_thana", "police_force": "DMP", "area_en": "", "duty_officer_telephone": tt,
                           "duty_officer_mobile": dcell, "oc_mobile": occell, "oc_dmp_extension": ext, "fax": fax,
                           "name_as_listed": "%s Police Station" % en_dmp,
                           "block_label_in_source": label.group(1) if label and label.group(1)[:4].lower() != en_dmp[:4].lower() else None}),
            source_url=DMP_LOCAL,
            notes="upazila_en holds the DMP metropolitan thana (not an upazila). Phone = duty officer's T&T landline and the OC's official "
                  "mobile as published by DMP (the duty officer's cell where the entry has no OC part; address in English as printed; the "
                  "listed numbers may be dated). " + ("" if oc else "The DMP entry is incomplete (no 'Officers In charge' part). ") + DMP_CC_NOTE +
                  ("" if bn else " Not in the name table; Bangla name not given.")))
    dc = page_text(DHAKA_DC_GLANCE)
    dc_txt = " ".join(content_text(dc))
    for en_x, (bn, en) in DMP_EXTRA.items():
        if bn in dc_txt:
            places.append(dict(source_key=CITY["key"], source_id="dmp-thana-%s" % en.lower(), name_bn="%s থানা" % bn, name_en="",
                               category_key="emergency.police_station", district_en="Dhaka", upazila_en=en,
                               operator="ঢাকা মেট্রোপলিটন পুলিশ (ডিএমপি)", ownership="public",
                               extra_json=xj({"unit": "metropolitan_thana", "police_force": "DMP", "area_en": ""}), source_url=DHAKA_DC_GLANCE,
                               notes="DMP thana named on the Dhaka DC portal's list of city-corporation-area thanas but not on dmp.gov.bd "
                                     "'Find Your Local Police'; no address or numbers published. " + DMP_CC_NOTE))
    # Commissioner's office and the control room ('Contact Us')
    c = page_text(DMP_CONTACT)
    rows = [r for tb in tables(c) for r in tb]
    pc = next((r for r in rows if len(r) >= 6 and r[1] == "Commissioner"), None)
    cr = next((r for r in rows if r and r[0] == "DMP Control Room"), None)
    crf = next((r for r in rows if r and r[0] == "DMP Control Room Fax"), None)
    if pc:
        emails = re.findall(r"[\w.]+@(?:dmp|police)\.gov\.bd", " ".join(pc))
        places.append(dict(source_key=CITY["key"], source_id="dmp-hq", name_bn="ঢাকা মেট্রোপলিটন পুলিশ হেডকোয়ার্টার্স", name_en="",
                           category_key="government.sp_office", district_en="Dhaka", phone="; ".join(x for x in (_num(pc[2]), _num(pc[4])) if x),
                           email="; ".join(emails), operator="বাংলাদেশ পুলিশ", ownership="public",
                           extra_json=xj({"office": "Commissioner, DMP", "dmp_extension": pc[3].strip()}), source_url=DMP_CONTACT,
                           notes="Police Commissioner's office (metropolitan equivalent of an SP office) — closest taxonomy key "
                                 "government.sp_office. Office landline (printed without the 02 area code) and official mobile of the "
                                 "Commissioner post from 'Senior Management of DMP'. No HQ address is given on the page (36 Minto Road is "
                                 "printed as the Media and Public Relations Division's contact address)."))
    if cr:
        nums = [_num(x) for x in re.split(r",", cr[1])]
        places.append(dict(source_key=CITY["key"], source_id="dmp-control-room", name_bn="ডিএমপি কন্ট্রোল রুম", name_en="DMP Control Room",
                           category_key="emergency", district_en="Dhaka", phone="; ".join(x for x in nums if x), operator="বাংলাদেশ পুলিশ",
                           ownership="public", extra_json=xj({"fax": _num(crf[1]) if crf else "", "label_in_source": cr[0]}), source_url=DMP_CONTACT,
                           notes="'DMP Control Room' row of the Hot Number table (landline printed without the 02 area code). Bangla name composed."))
    save_raw("dmp_find_your_local_police.txt", "\n".join(lines))
    save_raw("dmp_contact_hot_numbers.txt", "\n".join(" | ".join(r) for r in rows if r and r[0] in ("DMP Control Room", "DMP Control Room Fax")) +
             ("\n" + " | ".join(pc) if pc else ""))
    for p in places:
        p["extra_json"] = p["extra_json"] if isinstance(p["extra_json"], str) else xj(p["extra_json"])
    n = sum(1 for p in places if p["category_key"] == "emergency.police_station")
    facts.append(dict(entity_level="metropolitan_police", entity_name_en="Dhaka Metropolitan Police area", district_en="Dhaka",
                      fact="police_stations", value=n, unit="thanas", basis="listed", year=2026, source_key=CITY["key"], source_url=DMP_LOCAL,
                      notes="%d stations on dmp.gov.bd 'Find Your Local Police' + Hatirjheel from the Dhaka DC portal; DMP's history page says 50."
                            % len(blocks)))
    facts.append(dict(entity_level="metropolitan_police", entity_name_en="Dhaka Metropolitan Police area", district_en="Dhaka",
                      fact="police_stations_placed_in_city_corporation", value=0, unit="thanas", basis="listed", year=2026,
                      source_key=CITY["key"], source_url=DMP_LOCAL, notes=DMP_CC_NOTE))
    write_csv("places.csv", PLACE_COLS, places)
    write_csv("facts.csv", FACT_COLS, facts)
    write_manifest(dict(
        key=CITY["key"], division="dhaka", kind="metro_police_thanas", city=CITY["city"],
        name="Dhaka Metropolitan Police — thanas and official numbers", organization="Dhaka Metropolitan Police (Bangladesh Police)",
        source_type="government_portal", trust_level=4, urls=[DMP_LOCAL, DMP_CONTACT, DHAKA_DC_GLANCE],
        accessed=__import__("datetime").date.today().isoformat(), publication_date=None, license=None, license_url=None,
        attribution="Dhaka Metropolitan Police (dmp.gov.bd); Deputy Commissioner's office, Dhaka (dhaka.gov.bd)",
        notes="No licence stated. Only institutional numbers are collected: duty-officer T&T landlines, OC official mobiles, fax and PABX "
              "extensions (extra_json), @dmp.gov.bd / @police.gov.bd e-mails, the Commissioner post's office numbers and the control room. "
              "Inspector-investigation mobiles and officers' names are not copied. The 'Find Your Local Police' list is undated; many "
              "landlines are in the old 7-digit format. No thana is placed in DNCC or DSCC (area_en empty): no official thana-to-city-"
              "corporation list was found."),
        ["places.csv", "facts.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


def main_gmp():
    places, facts, raw = [], [], []
    for zid, menu, bn, en, zone, div in GMP_THANAS:
        url = GMP_THANA_URL % zid
        t = page_text(url)
        rows = [r for tb in tables(t) for r in tb if len(r) >= 3 and re.match(r"^\d+$", r[0])]
        raw += ["%s | %s | %s" % (url, r[1], r[2]) for r in rows]
        oc = next((r for r in rows if r[1].startswith("OC ")), None)
        duty = next((r for r in rows if r[1].startswith("Duty Officer")), None)
        ocm = phone_norm(oc[2]) if oc else ""
        dm = phone_norm(duty[2]) if duty else ""
        places.append(dict(source_key=CITY["key"], source_id="gmp-thana-%s" % en.lower().replace(" ", "-"), name_bn="%s থানা" % bn,
                           name_en="%s Thana" % menu, category_key="emergency.police_station", district_en="Gazipur", upazila_en=en,
                           phone="; ".join(x for x in (ocm, dm) if x), operator="গাজীপুর মেট্রোপলিটন পুলিশ (জিএমপি)", ownership="public",
                           website=url, extra_json=xj({"unit": "metropolitan_thana", "police_force": "GMP", "area_en": "Gazipur City Corporation",
                                                       "gmp_zone_bn": zone, "gmp_crime_division_bn": div + " বিভাগ", "oc_mobile": ocm,
                                                       "duty_officer_mobile": dm, "label_in_source": oc[1] if oc else ""}),
                           source_url=url,
                           notes="upazila_en holds the GMP metropolitan thana (not an upazila). Phone = OC's and duty officer's official mobiles "
                                 "as published by GMP (inspectors' numbers not copied). area_en = Gazipur City Corporation: " + GMP_CC_NOTE +
                                 " Bangla name from GMP's 'About GMP'."))
    t = page_text(GMP_CONTACT)
    txt = "\n".join(content_text(t))
    cr = re.search(r"Gmp Control Room:\s*(\d+)", txt)
    tr = re.search(r"Traffic Control Room:\s*(\d+)", txt)
    em = re.search(r"[\w.]+@police\.gov\.bd", txt)
    ad = re.search(r"GMP Headquarters,\s*\n?(.+?Gazipur)", txt)
    pc = next((r for r in [r for tb in tables(t) for r in tb] if len(r) >= 3 and r[1] == "Police Commissioner"), None)
    places.append(dict(source_key=CITY["key"], source_id="gmp-hq", name_bn="গাজীপুর মেট্রোপলিটন পুলিশ হেডকোয়ার্টার্স", name_en="GMP Headquarters",
                       category_key="government.sp_office", address=ad.group(1).strip() if ad else "", district_en="Gazipur",
                       phone=phone_norm(pc[-1]) if pc else "", email=em.group(0) if em else "", operator="বাংলাদেশ পুলিশ", ownership="public",
                       extra_json=xj({"office": "Police Commissioner, GMP", "area_en": "Gazipur City Corporation"}), source_url=GMP_CONTACT,
                       notes="Police Commissioner's office (metropolitan equivalent of an SP office) — closest taxonomy key government.sp_office. "
                             "Address and e-mail from 'Contact Us'; phone = the Police Commissioner post's official mobile. (The site footer "
                             "gives other HQ addresses: 'Joydebpur Road, Gazipur-1702' / 'Wireless Gate, Naljani'.)"))
    if cr:
        places.append(dict(source_key=CITY["key"], source_id="gmp-control-room", name_bn="জিএমপি কন্ট্রোল রুম", name_en="GMP Control Room",
                           category_key="emergency", district_en="Gazipur", phone=cr.group(1), operator="বাংলাদেশ পুলিশ", ownership="public",
                           extra_json=xj({"traffic_control_room": tr.group(1) if tr else "", "area_en": "Gazipur City Corporation"}),
                           source_url=GMP_CONTACT, notes="'Gmp Control Room' on 'Contact Us'; Bangla name composed."))
    save_raw("gmp_thana_numbers.txt", "\n".join(raw))
    save_raw("gmp_contact.txt", "\n".join(l for l in txt.split("\n") if re.search(r"Headquarters|Naljani|Control Room|@police|Police Commissioner \|", l)))
    n = sum(1 for p in places if p["category_key"] == "emergency.police_station")
    facts.append(dict(entity_level="metropolitan_police", entity_name_en="Gazipur Metropolitan Police area", district_en="Gazipur",
                      fact="police_stations", value=n, unit="thanas", basis="listed", year=2026, source_key=CITY["key"], source_url=GMP_HISTORY,
                      notes="8 thanas (About GMP and the site's thana pages); all lie in Gazipur City Corporation (area_en)."))
    write_csv("places.csv", PLACE_COLS, places)
    write_csv("facts.csv", FACT_COLS, facts)
    write_manifest(dict(
        key=CITY["key"], division="dhaka", kind="metro_police_thanas", city=CITY["city"],
        name="Gazipur Metropolitan Police — thanas and official numbers", organization="Gazipur Metropolitan Police (Bangladesh Police)",
        source_type="government_portal", trust_level=4, urls=[GMP_THANA_URL % t[0] for t in GMP_THANAS] + [GMP_CONTACT, GMP_HISTORY],
        accessed=__import__("datetime").date.today().isoformat(), publication_date=None, license=None, license_url=None,
        attribution="Gazipur Metropolitan Police (gmp.gov.bd)",
        notes="No licence stated. Only institutional numbers (OC and duty-officer official mobiles of the 01320-07xxxx police series, "
              "the Commissioner post's mobile, control rooms, pcgmp@police.gov.bd) are collected; no officer names. Thana pages give no "
              "address; their embedded Google map (viewport only) is not used as a coordinate. Every thana lies in Gazipur City "
              "Corporation (GMP's area is GCC's 57 wards): area_en in extra_json."),
        ["places.csv", "facts.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


SITES = {"rajshahi": dict(folder="rmp_thanas_2026"), "rangpur": dict(folder="rangpur_metro_police_thanas_2026", run=main_rangpur)}


# --- Chattogram Division: Chattogram Metropolitan Police (cmp.gov.bd + the CMP national-portal site) ---------------------------
# CMP thanas: Bangla as on the CMP portal's 'এক নজরে' list, English used here, English as on cmp.gov.bd 'Information Of Police
# Station', crime division (cmp.gov.bd contact directory), contact-directory page id and the thana's heading on that page.
CMP_THANAS = [
    ("কোতোয়ালী", "Kotwali", "Kotwali", "দক্ষিণ", 287, "কোতোয়ালি"), ("বাকলিয়া", "Bakalia", "Bakolia", "দক্ষিণ", 287, "বাকলিয়া"),
    ("চকবাজার", "Chawkbazar", "Chawk Bazar", "দক্ষিণ", 287, "চকবাজার"), ("সদরঘাট", "Sadarghat", "Sadarghat", "দক্ষিণ", 287, "সদরঘাট"),
    ("পাঁচলাইশ", "Panchlaish", "Panchlaish", "উত্তর", 288, "পাঁচলাইশ"), ("চান্দগাঁও", "Chandgaon", "Chandgaon", "উত্তর", 288, "চাঁন্দগাঁও"),
    ("বায়েজিদ বোস্তামী", "Bayezid Bostami", "Bayazid Bostami", "উত্তর", 288, "বায়েজীদ"), ("খুলশী", "Khulshi", "Khulshi", "উত্তর", 288, "খুলশী"),
    ("ডবলমুরিং", "Double Mooring", "Doublemooring", "পশ্চিম", 289, "ডবলমুরিং"), ("পাহাড়তলী", "Pahartali", "Pahartali", "পশ্চিম", 289, "পাহাড়তলী"),
    ("হালিশহর", "Halishahar", "Halishahar", "পশ্চিম", 289, "হালিশহর"), ("আকবরশাহ", "Akbarshah", "Akbar Shah", "পশ্চিম", 289, "আকবরশাহ"),
    ("বন্দর", "Bandar", "Port", "বন্দর", 290, "বন্দর"), ("পতেঙ্গা", "Patenga", "Patenga", "বন্দর", 290, "পতেঙ্গা"),
    ("কর্ণফুলী", "Karnaphuli", "Karnophuli", "বন্দর", 290, "কর্ণফুলি"), ("ইপিজেড", "EPZ", "EPZ", "বন্দর", 290, "ইপিজেড"),
]
CMP_SITE = "https://cmp.gov.bd/index.php?cPath=%d"        # cmp.gov.bd (CMP's own PHP site; 2013 framework, pages undated)
CMP_PORTAL_GLANCE = "https://police.chittagongdiv.gov.bd/pages/static-pages/at-a-glance-6ae2db41fd9ba07169122831"   # এক নজরে
CMP_PORTAL_CONTACT = "https://police.chittagongdiv.gov.bd/pages/static-pages/যোগাযোগ-15cb30-699124d1516a96d4de404110"  # যোগাযোগ
CMP_CC_SENTENCE = "সিএমপির আওতাধীন এলাকায় চট্টগ্রাম সিটি কর্পোরেশনের অধিকাংশ এলাকা অন্তর্ভুক্ত"
CMP_CC_NOTE = ("CMP says its area includes most of Chattogram City Corporation ('%s', CMP portal এক নজরে), but neither CMP "
               "(cmp.gov.bd, police.chittagongdiv.gov.bd) nor CCC (ccc.gov.bd publishes no thana list) places individual thanas in the "
               "city corporation, so area_en is left empty." % CMP_CC_SENTENCE)


def cmp_body(t):
    """cmp.gov.bd page HTML -> body lines (after the left menu, before the footer)."""
    s = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", " ", t or "", flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>|</p>|</div>|</li>|</tr>|</h\d>", "\n", s, flags=re.I)
    s = re.sub(r"</t[dh]>", " | ", s, flags=re.I)
    s = __import__("html").unescape(re.sub(r"<[^>]+>", " ", s))
    lines = [unicodedata.normalize("NFC", re.sub(r"\s+", " ", l)).strip() for l in s.split("\n")]
    lines = [l for l in lines if l and l not in ("|", "| |", "| | |")]
    a = max((i for i, l in enumerate(lines) if l.startswith("Emergency Helpline")), default=-1)
    b = next((i for i, l in enumerate(lines) if l.startswith("Copyright")), len(lines))
    return lines[a + 1:b]


def cmp_division_numbers(lines, shorts):
    """Contact-directory page lines -> {thana heading: {"oc": n, "duty": n}} (labels and numbers alternate; a thana block starts
    with '<thana> থানা' or '<thana>' + 'থানা' and ends at 'তদারকি কর্মকর্তা')."""
    out, cur, label = {}, None, ""
    sq = {s.replace(" ", ""): s for s in shorts}
    for i, l in enumerate(lines):
        l2 = l.replace(" ", "").strip("|")
        nxt = lines[i + 1].replace(" ", "") if i + 1 < len(lines) else ""
        hit = next((s for k, s in sq.items() if l2 == k + "থানা" or (l2 == k and nxt.startswith("থান"))), None)
        if hit:
            cur, label = hit, ""
            continue
        if l2.startswith("থান"):
            continue
        if l.startswith("তদারকি"):
            cur = None
            continue
        m = re.search(r"([০-৯0-9]{5}-?[০-৯0-9]{6})", l)
        if m:
            lab = (label + l[:m.start()]).replace(" ", "")
            num = asc(m.group(1)).replace("-", "")
            if cur and lab.startswith("ওসি"):
                out.setdefault(cur, {})["oc"] = num
            elif cur and lab.startswith("ডিউটি"):
                out.setdefault(cur, {})["duty"] = num
            label = ""
        else:
            label += l
    return out


def main_cmp():
    places, facts, raw = [], [], []
    info = " ".join(cmp_body(page_text(CMP_SITE % 295)))
    addr = {}
    for m in re.finditer(r"(?:^|\s)\d+\.\s+(.+?)\s+Police\s+Station\s+Add?ress\s+(.+?)\s+Direction\s+(.+?)(?=\s+\d+\.\s|$)", info):
        addr[re.sub(r"\s+", " ", m.group(1)).strip()] = (re.sub(r"\s+", " ", m.group(2)).strip(" ,"), re.sub(r"\s+", " ", m.group(3)).strip())
    nums, pages = {}, {}
    for pid in (287, 288, 289, 290):
        lines = cmp_body(page_text(CMP_SITE % pid))
        pages[pid] = lines
        nums.update(cmp_division_numbers(lines, [t[5] for t in CMP_THANAS if t[4] == pid]))
    glance = " ".join(content_text(page_text(CMP_PORTAL_GLANCE)))
    m = re.search(r"থানাগুলো হলো\s*—\s*(.+?)।", glance)
    listed = [x.strip() for x in re.split(r",| ও ", m.group(1))] if m else []
    for bn, en, cmp_en, dv, pid, short in CMP_THANAS:
        n = nums.get(short, {})
        oc, duty = n.get("oc", ""), n.get("duty", "")
        a, direction = addr.get(cmp_en, ("", ""))
        raw.append("%s | %s | %s | OC %s | duty officer %s | %s" % (bn, cmp_en, dv, oc or "-", duty or "-", a or "-"))
        places.append(dict(
            source_key=CITY["key"], source_id="cmp-thana-%s" % en.lower().replace(" ", "-"), name_bn="%s থানা" % bn,
            name_en="%s Police Station" % cmp_en, category_key="emergency.police_station", address=a, district_en="Chattogram",
            upazila_en=en, phone="; ".join(x for x in (oc, duty) if x), operator="চট্টগ্রাম মেট্রোপলিটন পুলিশ (সিএমপি)", ownership="public",
            extra_json=xj({"unit": "metropolitan_thana", "police_force": "CMP", "area_en": "", "cmp_crime_division_bn": dv + " বিভাগ",
                           "oc_mobile": oc, "duty_officer_mobile": duty, "direction_as_published": direction,
                           "name_as_listed": "%s Police Station" % cmp_en, "on_cmp_portal_list": bn in listed}),
            source_url=CMP_SITE % pid,
            notes="upazila_en holds the CMP metropolitan thana (not an upazila)%s. Phone = OC's and duty officer's police official mobiles "
                  "(01320-05xxxx) from the cmp.gov.bd contact directory (%s বিভাগ page); inspectors' numbers and officers' names not copied. "
                  "Address as printed in English on cmp.gov.bd 'Information Of Police Station' (undated). %s" % (
                      "; it is also the name of Karnaphuli upazila, where the station stands (old Char Lakshya UP building)"
                      if en == "Karnaphuli" else "", dv, CMP_CC_NOTE) + ("" if oc else " No OC number found on the page.")))
    # headquarters (Police Commissioner's office) and control room
    contact = " ".join(content_text(page_text(CMP_PORTAL_CONTACT)))
    hq = cmp_body(page_text(CMP_SITE % 338))
    pc = next((asc(hq[i + 1]).replace("-", "").strip(" |") for i, l in enumerate(hq[:-1]) if l.strip(" |") == "পুলিশ কমিশনার"), "")
    ad = re.search(r"চট্টগ্রাম মেট্রোপলিটন পুলিশ সদর দপ্তর,\s*(.+?চট্টগ্রাম-৪০০০)", contact)
    ph = re.search(r"ফোন\s*\+?৮৮-?([০-৯\-]+)", contact)
    em = re.findall(r"[\w.]+@police\.gov\.bd", contact)
    places.append(dict(source_key=CITY["key"], source_id="cmp-hq", name_bn="চট্টগ্রাম মেট্রোপলিটন পুলিশ সদর দপ্তর", name_en="",
                       category_key="government.sp_office", address=ad.group(1).strip() if ad else "", district_en="Chattogram",
                       phone="; ".join(x for x in (asc(ph.group(1)) if ph else "", pc if re.match(r"^01320\d{6}$", pc) else "") if x),
                       email="; ".join(dict.fromkeys(em)), operator="বাংলাদেশ পুলিশ", ownership="public",
                       extra_json=xj({"office": "Police Commissioner, CMP", "commissioner_official_mobile": pc, "area_en": ""}),
                       source_url=CMP_PORTAL_CONTACT,
                       notes="Police Commissioner's office (metropolitan equivalent of an SP office) — closest taxonomy key government.sp_office. "
                             "Address, office phone and e-mail from the CMP portal 'যোগাযোগ'; the Commissioner post's official mobile from "
                             "cmp.gov.bd 'Head Quater'. The CMP portal's এক নজরে places the HQ at 'লালদীঘির পাড়' instead (conflict kept in notes)."))
    hl = " ".join(cmp_body(page_text(CMP_SITE % 297)))
    cr = re.search(r"Police Control Room \|?\s*:?\s*(.+?)\s*Traffic\s*Control", hl)
    tc = re.search(r"Traffic\s*Control \|?\s*:?\s*(.+?)\s*e-mail", hl)
    crn = re.findall(r"\d[\d\-]{9,}", cr.group(1)) if cr else []
    places.append(dict(source_key=CITY["key"], source_id="cmp-control-room", name_bn="সিএমপি পুলিশ কন্ট্রোল রুম", name_en="CMP Police Control Room",
                       category_key="emergency", district_en="Chattogram", phone="; ".join(re.sub(r"-\d{2}$", "", x) for x in crn),
                       operator="বাংলাদেশ পুলিশ", ownership="public",
                       extra_json=xj({"numbers_as_printed": crn, "traffic_control": re.findall(r"\d{11}", tc.group(1)) if tc else [], "area_en": ""}),
                       source_url=CMP_SITE % 297,
                       notes="'Police Control Room' on cmp.gov.bd 'Emergency Helpline'; ranges such as '01320057998-99' kept as the first "
                             "number (all as printed in extra_json). Bangla name composed. The page's e-mail addresses are obfuscated and not copied."))
    save_raw("cmp_thana_numbers.txt", "\n".join(raw))
    save_raw("cmp_hq_and_control_room.txt", "HQ (CMP portal যোগাযোগ): %s\nPolice Commissioner post: %s\nControl room: %s\nTraffic control: %s" % (
        ad.group(0) if ad else "-", pc or "-", cr.group(1) if cr else "-", tc.group(1) if tc else "-"))
    n = sum(1 for p in places if p["category_key"] == "emergency.police_station")
    facts.append(dict(entity_level="metropolitan_police", entity_name_en="Chattogram Metropolitan Police area", district_en="Chattogram",
                      fact="police_stations", value=n, unit="thanas", basis="listed", year=2026, source_key=CITY["key"], source_url=CMP_PORTAL_GLANCE,
                      notes="16 thanas (CMP portal এক নজরে; cmp.gov.bd lists the same 16 with addresses)."))
    facts.append(dict(entity_level="metropolitan_police", entity_name_en="Chattogram Metropolitan Police area", district_en="Chattogram",
                      fact="police_stations_placed_in_city_corporation", value=0, unit="thanas", basis="listed", year=2026,
                      source_key=CITY["key"], source_url=CMP_PORTAL_GLANCE, notes=CMP_CC_NOTE))
    write_csv("places.csv", PLACE_COLS, places)
    write_csv("facts.csv", FACT_COLS, facts)
    write_manifest(dict(
        key=CITY["key"], division="chattogram", kind="metro_police_thanas", city=CITY["city"],
        name="Chattogram Metropolitan Police — thanas and official numbers", organization="Chattogram Metropolitan Police (Bangladesh Police)",
        source_type="government_portal", trust_level=4,
        urls=[CMP_SITE % 295] + [CMP_SITE % p for p in (287, 288, 289, 290, 338, 297)] + [CMP_PORTAL_GLANCE, CMP_PORTAL_CONTACT],
        accessed=__import__("datetime").date.today().isoformat(), publication_date=None, license=None, license_url=None,
        attribution="Chattogram Metropolitan Police (cmp.gov.bd, police.chittagongdiv.gov.bd)",
        notes="No licence stated. Only institutional numbers are collected: OC and duty-officer police official mobiles (01320-05xxxx) from "
              "the cmp.gov.bd contact directory, the Commissioner post's official mobile, the HQ office phone and pccmp@police.gov.bd, and "
              "the control-room numbers. Inspectors' mobiles and officers' names are not copied; cmp.gov.bd's obfuscated e-mails are not "
              "decoded. Addresses are cmp.gov.bd's undated English list. No thana is placed in Chattogram City Corporation (area_en "
              "empty): CMP covers 'most of' CCC and no source gives a thana-to-city-corporation list."),
        ["places.csv", "facts.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


# --- Khulna Division: Khulna Metropolitan Police (the KMP national-portal site police.khulnadiv.gov.bd) -------------------------
# kmp.police.gov.bd (linked from the divisional portal) answered HTTP 500 at access time. KMP thanas: Bangla as on the Khulna DC
# portal 'ভৌগলিক পরিচিতি' list of 8 'মেট্রোপলিটন থানা', English used here (HDX COD-AB spelling where HDX has the thana),
# KMP's own name and its label in KMP's mobile-number list (a PDF attached to the KMP portal's 'যোগাযোগ' page, typed in the
# legacy Bijoy/SutonnyMJ font; KMP's name below is a Unicode transcription of that label, spaces removed for matching).
KMP_THANAS = [
    ("দৌলতপুর", "Daulatpur", "দৌলতপুর", "‡`ŠjZcyi"), ("খালিশপুর", "Khalishpur", "খালিশপুর", "Lvwjkcyi"),
    ("খানজাহানআলী", "Khan Jahan Ali", "খানজাহান আলী", "LvbRvnvbAvjx"), ("সোনাডাঙ্গা", "Sonadanga", "সোনাডাঙ্গা মডেল", "‡mvbvWv½vg‡Wj"),
    ("কোতয়ালী", "Khulna Sadar", "খুলনা", "Lyjbv"), ("আড়ংঘাটা", "Aranghata", "আড়ংঘাটা", "AvosNvUv"),
    ("হড়িণটানা", "Harintana", "হরিণটানা", "nwiYUvbv"), ("লবনচড়া", "Labanchara", "লবণচরা", "jeYPiv"),
]
KMP_PORTAL = "https://police.khulnadiv.gov.bd/"                                          # title 'পুলিশ কমিশনার'
KMP_GLANCE = KMP_PORTAL + "pages/static-pages/6980f684a31054345f1ceb6e"                   # এক নজরে
KMP_CONTACT = KMP_PORTAL + "pages/static-pages/698101a8a31054345f1d5747"                  # যোগাযোগ (PDF: KMP mobile numbers)
KMP_POSTAL = KMP_PORTAL + "pages/static-pages/6981336635ce18e1c06fc635"                   # ডাক যোগাযোগ (HQ address, phone, e-mail)
KMP_OFFICERS = KMP_PORTAL + "pages/officers"                                              # officer cards (Commissioner's office phone)
KHULNA_DC_GEO = "https://khulna.gov.bd/pages/static-pages/69812047a31054345f1e0b98"      # DC portal 'ভৌগলিক পরিচিতি' (thana list)
KMP_CC_SENTENCE = "৩১টি সিটি কর্পোরেশন ওয়ার্ড এর অন্তর্ভূক্ত"
KMP_CC_NOTE = ("KMP's area includes the 31 wards of Khulna City Corporation and 5 unions ('৫টি ইউনিয়ন নিয়ে গঠিত। %s', KMP portal "
               "এক নজরে), but no official source places individual thanas in the city corporation (KMP's portal and the Khulna DC "
               "portal give no thana-to-ward list; KCC's own site could not be reached), so area_en is left empty." % KMP_CC_SENTENCE)


def kmp_pdf_numbers(text):
    """KMP mobile-number list (pdftotext -layout) -> ({legacy thana: {"oc": n, "duty": n}}, {label: n}) for '<serial> <label> <number>' rows."""
    out, other = {}, {}
    for l in (text or "").splitlines():
        m = re.match(r"^\s*\d+\s+(.+?)\s+(01320-?\d{6})\s*$", l)
        if not m:
            continue
        lab, num = m.group(1).replace(" ", ""), m.group(2).replace("-", "")
        m2 = re.match(r"^(AwdmviBbPvR©|wWDwUAwdmvi)\((.+?)_vbv\)$", lab)
        if m2:
            out.setdefault(m2.group(2), {})["oc" if m2.group(1).startswith("Awdmvi") else "duty"] = num
        else:
            other[lab] = num
    return out, other


def main_kmp():
    places, facts, raw, warn = [], [], [], []
    key = CITY["key"]
    geo = content_text(page_text(KHULNA_DC_GEO))
    i = next((k for k, l in enumerate(geo) if l.startswith("মেট্রোপলিটন")), None)
    listed = [re.sub(r"\s*থানা$", "", re.sub(r"^[0-9০-৯]+\.\s*", "", l)) for l in geo[i + 1:i + 9]] if i is not None else []
    if sorted(listed) != sorted(t[0] for t in KMP_THANAS):
        warn.append("DC portal thana list differs from the table: %s" % listed)
    contact = page_text(KMP_CONTACT)
    pdfs = sorted(set(re.findall(r'(https?://[^"\' ]+\.pdf)', contact)))
    nums, other, pdf_sha = {}, {}, ""
    if pdfs:
        r = get(pdfs[0])
        if r is not None and r.ok:
            pdf_sha = hashlib.sha256(r.content).hexdigest()
            fd, tmp = tempfile.mkstemp(suffix=".pdf")
            with os.fdopen(fd, "wb") as fh:
                fh.write(r.content)
            nums, other = kmp_pdf_numbers(pdftotext(tmp) or "")
            os.remove(tmp)
    if not nums:
        warn.append("KMP number list not read (PDF missing, or pdftotext not installed): %s" % (pdfs[:1] or KMP_CONTACT))
    for bn, en, kmp_bn, legacy in KMP_THANAS:
        n = nums.get(legacy, {})
        oc, duty = n.get("oc", ""), n.get("duty", "")
        raw.append("%s | %s | KMP list label (legacy font) '%s' -> %s থানা | OC %s | duty officer %s" % (bn, en, legacy, kmp_bn, oc or "-", duty or "-"))
        places.append(dict(
            source_key=key, source_id="kmp-thana-%s" % en.lower().replace(" ", "-"), name_bn="%s থানা" % kmp_bn, name_en="",
            category_key="emergency.police_station", district_en="Khulna", upazila_en=en, phone="; ".join(x for x in (oc, duty) if x),
            operator="খুলনা মেট্রোপলিটন পুলিশ (কেএমপি)", ownership="public",
            extra_json=xj({"unit": "metropolitan_thana", "police_force": "KMP", "area_en": "", "oc_mobile": oc, "duty_officer_mobile": duty,
                           "name_on_dc_portal": "%s থানা" % bn, "kmp_list_label_legacy_font": legacy, "kmp_number_list": pdfs[0] if pdfs else None,
                           "on_dc_portal_list": bn in listed}),
            source_url=KMP_CONTACT,
            notes="upazila_en holds the KMP metropolitan thana (not an upazila). name_bn is KMP's name, transcribed from the legacy-font "
                  "(SutonnyMJ) PDF mobile-number list attached to the KMP portal 'যোগাযোগ' page; the Khulna DC portal spells it '%s থানা'%s. "
                  "Phone = OC's and duty officer's police official mobiles (01320-05xxxx) from that list; inspectors' numbers and officers' "
                  "names not copied. %s" % (bn, " (and HDX/BBS name it Khulna Sadar)" if en == "Khulna Sadar" else "", KMP_CC_NOTE)
                  + ("" if oc else " No OC number found in the list.")))
    # headquarters (Police Commissioner's office) and control room
    postal = " ".join(content_text(page_text(KMP_POSTAL)))
    ad = re.search(r"খুলনা মেট্রোপলিটন পুলিশ হেডকোয়ার্টার্স\s*\(\s*গ্লাক্সো মোড়\s*\)\s*,\s*(১৮৯, খানজাহান আলী রোড, খুলনা)", postal)
    ph = re.search(r"ফোনঃ\s*([০-৯ ]+-[০-৯]+)", postal)
    fax = re.search(r"ফ্যাক্সঃ\s*([০-৯ ]+)", postal)
    cr = re.search(r"মোবাইলঃ\s*([০-৯ ]+)\s*\(\s*কন্ট্রোলরুম\s*\)", postal)
    em = re.findall(r"[\w.]+@police\.gov\.bd", postal)
    ph_first = asc(ph.group(1)).replace(" ", "").split("-")[0] if ph else ""
    cl = [nfc(_html.unescape(x)) for x in re.split(r"<[^>]+>", re.sub(r"<script.*?</script>|<style.*?</style>", " ", page_text(KMP_OFFICERS), flags=re.S))]
    cl = [x for x in cl if x]
    pc_office = ""
    for k, x in enumerate(cl):   # card fields: label line, value line; the Commissioner's card has 'পদবি' = 'পুলিশ কমিশনার'
        if x == "পুলিশ কমিশনার" and k and cl[k - 1] == "পদবি":
            ph2 = next((cl[j + 1] for j in range(k, min(k + 20, len(cl) - 1)) if cl[j] == "ফোন (অফিস)"), "")
            pc_office = re.sub(r"\D", "", asc(ph2)) if re.match(r"^[০-৯0-9\-]{10,}$", ph2 or "") else ""
            break
    pc_mob = next((v for k, v in other.items() if k == "cywjkKwgkbvi"), "")      # 'পুলিশ কমিশনার'
    cr_pdf = next((v for k, v in other.items() if k == "‡KGgwcK‡›Uªvjiæg"), "")   # 'কেএমপি কন্ট্রোল রুম'
    hot = next((v for k, v in other.items() if k == "‡KGgwcnUjvBb"), "")         # 'কেএমপি হটলাইন'
    cr_postal = asc(cr.group(1)).replace(" ", "") if cr else ""
    places.append(dict(source_key=key, source_id="kmp-hq", name_bn="খুলনা মেট্রোপলিটন পুলিশ হেডকোয়ার্টার্স", name_en="",
                       category_key="government.sp_office", address=ad.group(1) if ad else "", district_en="Khulna",
                       phone="; ".join(x for x in dict.fromkeys([ph_first, pc_office, pc_mob]) if x), email="; ".join(dict.fromkeys(em)),
                       operator="বাংলাদেশ পুলিশ", ownership="public",
                       extra_json=xj({"office": "Police Commissioner, KMP", "phone_as_printed": asc(ph.group(1)) if ph else "",
                                      "fax": asc(fax.group(1)).replace(" ", "") if fax else "", "commissioner_office_phone": pc_office,
                                      "commissioner_official_mobile": pc_mob, "landmark": "গ্লাক্সো মোড়" if ad else "", "area_en": ""}),
                       source_url=KMP_POSTAL,
                       notes="Police Commissioner's office (metropolitan equivalent of an SP office) — closest taxonomy key government.sp_office. "
                             "Address, phone ('০২৪ ৪১১২৫৬৪-৬৫': first number kept), fax and e-mail from the KMP portal 'ডাক যোগাযোগ'; the "
                             "Commissioner's office number from the portal's officer card and the Commissioner post's official mobile from KMP's "
                             "mobile-number list; officer's name not copied."))
    places.append(dict(source_key=key, source_id="kmp-control-room", name_bn="কেএমপি কন্ট্রোল রুম", name_en="KMP Control Room",
                       category_key="emergency", district_en="Khulna", phone="; ".join(x for x in dict.fromkeys([cr_postal, cr_pdf, hot]) if x),
                       operator="বাংলাদেশ পুলিশ", ownership="public",
                       extra_json=xj({"control_room_mobile": cr_postal or cr_pdf, "kmp_hotline": hot, "area_en": ""}), source_url=KMP_POSTAL,
                       notes="Control-room mobile from the KMP portal 'ডাক যোগাযোগ' ('মোবাইলঃ ০১৩২০ ০৬০৯৯৮ ( কন্ট্রোলরুম)') and KMP's mobile-number "
                             "list ('কেএমপি কন্ট্রোল রুম'); the list's 'কেএমপি হটলাইন' number is added. Name as in that list."))
    save_raw("kmp_thana_numbers.txt", "Source: %s\nPDF: %s\nsha256: %s\n\n%s" % (KMP_CONTACT, pdfs[0] if pdfs else "-", pdf_sha, "\n".join(raw)))
    save_raw("kmp_hq_and_control_room.txt", "HQ (KMP portal ডাক যোগাযোগ): %s\nPhone: %s | Fax: %s | Control room: %s | E-mail: %s\n"
             "Commissioner office phone (officer card): %s\nKMP list: পুলিশ কমিশনার %s | কেএমপি কন্ট্রোল রুম %s | কেএমপি হটলাইন %s" % (
                 ad.group(0) if ad else "-", ph.group(1) if ph else "-", fax.group(1) if fax else "-", cr.group(1) if cr else "-",
                 ", ".join(dict.fromkeys(em)) or "-", pc_office or "-", pc_mob or "-", cr_pdf or "-", hot or "-"))
    n = sum(1 for p in places if p["category_key"] == "emergency.police_station")
    facts.append(dict(entity_level="metropolitan_police", entity_name_en="Khulna Metropolitan Police area", district_en="Khulna",
                      fact="police_stations", value=n, unit="thanas", basis="listed", year=2026, source_key=key, source_url=KHULNA_DC_GEO,
                      notes="8 'মেট্রোপলিটন থানা' on the Khulna DC portal; KMP's এক নজরে says '৮ টি থানা' and its number list has the same 8 OCs."))
    facts.append(dict(entity_level="metropolitan_police", entity_name_en="Khulna Metropolitan Police area", district_en="Khulna",
                      fact="police_stations_placed_in_city_corporation", value=0, unit="thanas", basis="listed", year=2026,
                      source_key=key, source_url=KMP_GLANCE, notes=KMP_CC_NOTE))
    write_csv("places.csv", PLACE_COLS, places)
    write_csv("facts.csv", FACT_COLS, facts)
    for w in warn:
        print("WARNING:", w)
    write_manifest(dict(
        key=key, division="khulna", kind="metro_police_thanas", city=CITY["city"],
        name="Khulna Metropolitan Police — thanas and official numbers", organization="Khulna Metropolitan Police (Bangladesh Police)",
        source_type="government_portal", trust_level=4,
        urls=[KMP_CONTACT] + pdfs[:1] + [KMP_POSTAL, KMP_OFFICERS, KMP_GLANCE, KHULNA_DC_GEO],
        accessed=__import__("datetime").date.today().isoformat(), publication_date=None, license=None, license_url=None,
        attribution="Khulna Metropolitan Police (police.khulnadiv.gov.bd) and the Khulna DC portal (khulna.gov.bd)",
        notes="No licence stated. Thana list from the Khulna DC portal ('ভৌগলিক পরিচিতি', 8 metropolitan thanas); numbers from KMP's "
              "mobile-number list, a 3-page PDF in the legacy SutonnyMJ font attached to the KMP portal 'যোগাযোগ' page (thana labels "
              "transcribed to Unicode in fetch.py). Only institutional numbers are collected: OC and duty-officer police official mobiles "
              "(01320-05xxxx), the Commissioner post's official mobile and office phone, the HQ phone/e-mail from 'ডাক যোগাযোগ' and the "
              "control-room numbers. Inspectors' mobiles and officers' names are not copied. kmp.police.gov.bd (KMP's own site) answered "
              "HTTP 500. No thana is placed in Khulna City Corporation (area_en empty): KMP covers all 31 KCC wards plus 5 unions and "
              "no source gives a thana-to-city-corporation list."),
        ["places.csv", "facts.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


# --- Barishal Division: Barishal Metropolitan Police (bmp.police.gov.bd, BMP's own site; bmp.gov.bd serves the same site) ------------
# Thana list: BMP history page (4 thanas). Numbers: BMP 'যোগাযোগ' (division-wise tables of posts and police official mobiles,
# 01320-06xxxx); only the OC's and the duty officer's numbers per thana are kept (inspectors' and beat officers' numbers are not).
# HQ address/phone: BMP's national-portal site police.barisaldiv.gov.bd ('ডাক যোগাযোগ', 'অনলাইন যোগাযোগ').
BMP_B = "https://bmp.police.gov.bd/"
BMP_HISTORY = BMP_B + "history"
BMP_CONTACT = BMP_B + "contact-us"
BMP_POSTAL = "https://police.barisaldiv.gov.bd/pages/static-pages/697895a335ce18e1c066a955"   # ডাক যোগাযোগ (HQ address, phone, fax)
BMP_ONLINE = "https://police.barisaldiv.gov.bd/pages/static-pages/69789aa235ce18e1c066ba4c"   # অনলাইন যোগাযোগ (BMP mobile, e-mails)
BMP_THANAS = [  # (name in the history list, English, key in the contact list's '(…)' labels, thana page)
    ("কোতয়ালী মডেল থানা", "Kotwali", "কোতোয়ালি", BMP_B + "thana/7/kotwali-model-thana"),
    ("বন্দর থানা", "Bandar", "বন্দর", BMP_B + "thana/10/bandar-thana"),
    ("কাউনিয়া থানা", "Kaunia", "কাউনিয়া", BMP_B + "thana/9/Kaunia-thana"),
    ("এয়ারপোর্ট থানা", "Airport", "এয়ারপোর্ট", BMP_B + "thana/8/airport-thana"),
]
BMP_CC_NOTE = ("Barishal City Corporation says it consists of '৩টি থানা, ৩০টি ওয়ার্ড ও ২২৫টি মহল্লা' without naming the thanas; BMP's thana "
               "pages list (BBS 2001) BCC wards together with rural unions for Kotwali, Kaunia and Airport and only unions for Bandar, so no "
               "official source places a BMP thana wholly in the city corporation and area_en is left empty.")


def main_bmp():
    places, facts, raw, warn = [], [], [], []
    key = CITY["key"]
    hist = re.sub(r"\s+", " ", " ".join(content_text(page_text(BMP_HISTORY))))
    listed = re.findall(r"[১-৯]\s*\.\s*(\S+(?: মডেল)? থানা)", hist)
    if sorted(listed) != sorted(t[0] for t in BMP_THANAS):
        warn.append("BMP history thana list differs from the table: %s" % listed)
    ct = page_text(BMP_CONTACT)
    nums = {}   # (post, thana key) -> number
    for tb in tables(ct):
        for row in tb:
            if len(row) >= 3:
                m = re.match(r"^(অফিসার ইনচার্জ|ডিউটি অফিসার)\s*\((.+?)\)$", row[1])
                if m:
                    nums[(m.group(1), m.group(2))] = asc(row[2]).replace(" ", "")
                elif row[1] in ("পুলিশ কমিশনার", "পুলিশ কন্ট্রোলরুম, বিএমপি"):
                    nums[(row[1], "")] = asc(row[2]).replace(" ", "")
    m = re.search(r"কমান্ড এন্ড কন্ট্রোল, বিএমপি\s*</h\d>\s*(?:<[^>]+>\s*)*([০-৯0-9]{11})", ct)
    cc_num = asc(m.group(1)) if m else ""
    off = lambda n: n if re.match(r"^01320\d{6}$", n or "") else ""   # police official mobiles only
    for bn, en, ck, tu in BMP_THANAS:
        oc, duty = off(nums.get(("অফিসার ইনচার্জ", ck), "")), off(nums.get(("ডিউটি অফিসার", ck), ""))
        raw.append("%s | %s | OC %s | duty officer %s" % (bn, en, oc or "-", duty or "-"))
        places.append(dict(
            source_key=key, source_id="bmp-thana-%s" % en.lower(), name_bn=bn, name_en="", category_key="emergency.police_station",
            district_en="Barishal", upazila_en=en, phone="; ".join(x for x in (oc, duty) if x), website=tu,
            operator="বরিশাল মেট্রোপলিটন পুলিশ (বিএমপি)", ownership="public",
            extra_json=xj({"unit": "metropolitan_thana", "police_force": "BMP", "area_en": "", "oc_mobile": oc, "duty_officer_mobile": duty,
                           "label_on_contact_page": "(%s)" % ck, "on_bmp_history_list": bn in listed}),
            source_url=BMP_CONTACT,
            notes="upazila_en holds the BMP metropolitan thana (not an upazila). Name as in the BMP history page's thana list. Phone = OC's "
                  "and duty officer's police official mobiles (01320-06xxxx) from the BMP 'যোগাযোগ' page; inspectors', beat officers' "
                  "numbers and officers' names not copied. %s" % BMP_CC_NOTE + ("" if oc else " No OC number found on the contact page.")))
    postal = re.sub(r"\s+", " ", " ".join(content_text(page_text(BMP_POSTAL))))
    online = re.sub(r"\s+", " ", " ".join(content_text(page_text(BMP_ONLINE))))
    ad = re.search(r"(বান্দ রোড, দক্ষিণ আলেকান্দা, বরিশাল, ৮২০০)", postal)
    ph = re.search(r"ফোন\s*-\s*([০-৯\-]+),\s*([০-৯\-]+)", postal)
    fax = re.search(r"ফ্যাক্স\s*-\s*([০-৯\-]+)", postal)
    em = list(dict.fromkeys(re.findall(r"[\w.]+@police\.gov\.bd", online)))
    phones = [asc(x).replace("-", "") for x in (ph.groups() if ph else ())]
    good = [x for x in phones if re.match(r"^0\d{10}$", x)]
    pc = off(nums.get(("পুলিশ কমিশনার", ""), ""))
    places.append(dict(source_key=key, source_id="bmp-hq", name_bn="বরিশাল মেট্রোপলিটন পুলিশ হেডকোয়ার্টার্স", name_en="",
                       category_key="government.sp_office", address=ad.group(1) if ad else "", district_en="Barishal",
                       phone="; ".join(good + ([pc] if pc else [])), email="; ".join(em), website="https://bmp.police.gov.bd/",
                       operator="বাংলাদেশ পুলিশ", ownership="public",
                       extra_json=xj({"office": "Police Commissioner, BMP", "phones_as_printed": ", ".join(ph.groups()) if ph else "",
                                      "fax_as_printed": fax.group(1) if fax else "", "commissioner_official_mobile": pc, "area_en": ""}),
                       source_url=BMP_POSTAL,
                       notes="Police Commissioner's office (metropolitan equivalent of an SP office) — closest taxonomy key government.sp_office. "
                             "Address and phones from the BMP national-portal site 'ডাক যোগাযোগ' (one of its two numbers and the fax are printed "
                             "with 13 digits and are kept only as printed in extra_json); e-mails from 'অনলাইন যোগাযোগ'; the Commissioner post's "
                             "official mobile from the BMP 'যোগাযোগ' page; officer's name not copied."))
    cr = off(nums.get(("পুলিশ কন্ট্রোলরুম, বিএমপি", ""), ""))
    places.append(dict(source_key=key, source_id="bmp-control-room", name_bn="পুলিশ কন্ট্রোলরুম, বিএমপি", name_en="BMP Control Room",
                       category_key="emergency", district_en="Barishal", phone="; ".join(x for x in (cr, off(cc_num)) if x),
                       operator="বাংলাদেশ পুলিশ", ownership="public",
                       extra_json=xj({"control_room_mobile": cr, "command_and_control_mobile": off(cc_num), "area_en": ""}),
                       source_url=BMP_CONTACT,
                       notes="Name as on the BMP 'যোগাযোগ' page; the 'কমান্ড এন্ড কন্ট্রোল, বিএমপি' number on the same page is added. The BMP "
                             "national-portal site's 'অনলাইন যোগাযোগ' gives the same control-room number as 'BMP'."))
    save_raw("bmp_thana_numbers.txt", "Source: %s\nThana list: %s (%s)\n\n%s" % (BMP_CONTACT, BMP_HISTORY, ", ".join(listed), "\n".join(raw)))
    save_raw("bmp_hq_and_control_room.txt", "HQ (%s): %s\nPhones as printed: %s | Fax as printed: %s\nE-mail (%s): %s\n"
             "BMP contact page: পুলিশ কমিশনার %s | পুলিশ কন্ট্রোলরুম, বিএমপি %s | কমান্ড এন্ড কন্ট্রোল, বিএমপি %s" % (
                 BMP_POSTAL, ad.group(1) if ad else "-", ", ".join(ph.groups()) if ph else "-", fax.group(1) if fax else "-", BMP_ONLINE,
                 ", ".join(em) or "-", pc or "-", cr or "-", cc_num or "-"))
    n = sum(1 for p in places if p["category_key"] == "emergency.police_station")
    facts.append(dict(entity_level="metropolitan_police", entity_name_en="Barishal Metropolitan Police area", district_en="Barishal",
                      fact="police_stations", value=n, unit="thanas", basis="listed", year=2026, source_key=key, source_url=BMP_HISTORY,
                      notes="BMP history page: '০৪ টি থানা' (%s); the contact page has the same 4 thanas." % ", ".join(listed)))
    facts.append(dict(entity_level="metropolitan_police", entity_name_en="Barishal Metropolitan Police area", district_en="Barishal",
                      fact="police_stations_placed_in_city_corporation", value=0, unit="thanas", basis="listed", year=2026,
                      source_key=key, source_url=BMP_HISTORY, notes=BMP_CC_NOTE))
    write_csv("places.csv", PLACE_COLS, places)
    write_csv("facts.csv", FACT_COLS, facts)
    for w in warn:
        print("WARNING:", w)
    write_manifest(dict(
        key=key, division="barishal", kind="metro_police_thanas", city=CITY["city"],
        name="Barishal Metropolitan Police — thanas and official numbers", organization="Barishal Metropolitan Police (Bangladesh Police)",
        source_type="government_portal", trust_level=4,
        urls=[BMP_CONTACT, BMP_HISTORY, BMP_POSTAL, BMP_ONLINE] + [t[3] for t in BMP_THANAS],
        accessed=__import__("datetime").date.today().isoformat(), publication_date=None, license=None, license_url=None,
        attribution="Barishal Metropolitan Police (bmp.police.gov.bd; police.barisaldiv.gov.bd)",
        notes="No licence stated. Thana list from the BMP history page (4 thanas); OC and duty-officer police official mobiles (01320-06xxxx) "
              "from BMP's 'যোগাযোগ' page; HQ address/phone from the BMP national-portal site (police.barisaldiv.gov.bd 'ডাক যোগাযোগ') and "
              "e-mails from its 'অনলাইন যোগাযোগ'; control-room and command-and-control numbers. Inspectors', beat officers' numbers and "
              "officers' names are not copied (beat pages list officers' personal mobiles and are not used). " + BMP_CC_NOTE),
        ["places.csv", "facts.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


# --- Sylhet Division: Sylhet Metropolitan Police (national-portal site police.sylhetdiv.gov.bd, 'হোম | পুলিশ কমিশনার'; SMP's own site
# smp.police.gov.bd). Thana list: SMP 'এক নজরে' (six thanas, English) and SMP's home page (Bangla names). SMP publishes no thana numbers:
# its officer cards are for the Commissioner, deputy/additional commissioners and zone ACs (no OC cards), and smp.police.gov.bd's
# 'যোগাযোগ' gives only the HQ, control room and hotline. Thana rows therefore carry no phone.
SMP_PORTAL = "https://police.sylhetdiv.gov.bd/"
SMP_GLANCE = SMP_PORTAL + "pages/static-pages/696ca219c4774958d7b931b6"    # এক নজরে (About SMP, English)
SMP_CONTACT = SMP_PORTAL + "pages/static-pages/696cb380c4774958d7ba127a"   # যোগাযোগ (HQ address, control room, hotline)
SMP_OFFICERS = SMP_PORTAL + "pages/officers"                               # officer cards (Commissioner's office phone, e-mail)
SMP_HOME = "https://smp.police.gov.bd/"
SMP_THANAS = [  # (English as in 'এক নজরে', short English, Bangla prefix on SMP's home page)
    ("Kotwali Model Thana", "Kotwali", "কোতোয়ালী"), ("Jalalabad Thana", "Jalalabad", "জালালাবাদ"), ("Airport Thana", "Airport", "এয়ারপোর্ট"),
    ("South Surma Thana", "South Surma", "দক্ষিণ সুরমা"), ("Moglabazar Thana", "Moglabazar", "মোগলাবাজার"), ("Shahporan Thana", "Shahporan", "শাহপরান"),
]
SMP_CC_NOTE = ("SMP says its area includes '27 wards of Sylhet City Corporation, 08 Unions of Sylhet Sadar Upazila and 10 Unions of South "
               "Surma Upazilla' (SMP এক নজরে) without saying which thana covers which wards or unions, and Sylhet City Corporation "
               "(scc.gov.bd, 42 wards) names no thanas, so no official source places an SMP thana in the city corporation and area_en is "
               "left empty.")
SMP_INTERMEDIATES = ["http://yr1.i.lencr.org/", "http://yr.i.lencr.org/"]   # as for the other Sylhet sources (AIA URLs; verification on)
SMP_OFFICIAL = re.compile(r"^(01320\d{6}|017133[78]\d{4})$")                # police official mobile series


def main_smp():
    INTERMEDIATES.extend(u for u in SMP_INTERMEDIATES if u not in INTERMEDIATES)   # before the first request
    places, facts, raw, warn = [], [], [], []
    key = CITY["key"]
    gl = re.sub(r"\s+", " ", " ".join(content_text(page_text(SMP_GLANCE))))
    m = re.search(r"SMP area is divided into (\w+) Police stations as ([^.]+)\.", gl)
    listed = [x.strip() for x in re.split(r",\s*|\s+and\s+", m.group(2))] if m else []
    if sorted(listed) != sorted(t[0] for t in SMP_THANAS):
        warn.append("SMP এক নজরে thana list differs from the table: %s" % listed)
    home = page_text(SMP_HOME)
    names = {}
    for a in re.findall(r"<a[^>]*>([^<]*থানা[^<]*)</a>", home):
        a = nfc(_html.unescape(a)).strip()
        for _, en, bn in SMP_THANAS:
            if a.startswith(bn) and en not in names:
                names[en] = a
    for en_full, en, bn in SMP_THANAS:
        nm = re.sub(r",\s*সিলেট$", "", names.get(en, "%s থানা" % bn))
        raw.append("%s | %s | SMP home page: %s" % (en_full, nm, names.get(en, "-")))
        places.append(dict(
            source_key=key, source_id="smp-thana-%s" % en.lower().replace(" ", "-"), name_bn=nm, name_en="",
            category_key="emergency.police_station", district_en="Sylhet", upazila_en=en, phone="", website=SMP_HOME,
            operator="সিলেট মেট্রোপলিটন পুলিশ (এসএমপি)", ownership="public",
            extra_json=xj({"unit": "metropolitan_thana", "police_force": "SMP", "area_en": "", "name_in_smp_glance": en_full,
                           "on_smp_home_page": en in names}),
            source_url=SMP_GLANCE,
            notes="upazila_en holds the SMP metropolitan thana (not an upazila). Name as on SMP's home page (', সিলেট' dropped); thana "
                  "from SMP's 'এক নজরে'. SMP publishes no thana phone number or e-mail (no OC cards; its contact pages give only the HQ, "
                  "control room and hotline), so none is given. %s" % SMP_CC_NOTE))
    ct = re.sub(r"\s+", " ", " ".join(content_text(page_text(SMP_CONTACT))))
    ad = re.search(r"(বাড়ি নং-২২৮, সড়ক নং-১/এ, ব্লক-এফ শাহজালাল উপশহর, সিলেট)", ct)
    cr = re.search(r"এসএমপি কন্ট্রোল রুম\s*([০-৯]{5}-[০-৯]{6})", ct)
    hot = re.search(r"এসএমপি হটলাইন\s*([০-৯]{5}-[০-৯]{6})", ct)
    off = lambda x: asc(x).replace("-", "") if x and SMP_OFFICIAL.match(asc(x).replace("-", "")) else ""
    cl = [nfc(_html.unescape(x)) for x in re.split(r"<[^>]+>", re.sub(r"<script.*?</script>|<style.*?</style>", " ", page_text(SMP_OFFICERS), flags=re.S))]
    cl = [x for x in cl if x]
    pc_office, pc_mail, pc_mob = "", "", ""
    for k, x in enumerate(cl):   # card fields: label line, value line; the Commissioner's card has 'পদবি' = 'পুলিশ কমিশনার'
        if x == "পুলিশ কমিশনার" and k and cl[k - 1] == "পদবি":
            val = lambda lab: next((cl[j + 1] for j in range(k, min(k + 24, len(cl) - 1)) if cl[j] == lab), "")
            d = re.sub(r"\D", "", asc(val("ফোন (অফিস)")))
            pc_office = d if re.match(r"^0[2-9]\d{8,9}$", d) else ""
            j = next((j for j in range(k, min(k + 24, len(cl) - 2)) if cl[j] == "ইমেইল"), None)   # e-mail is split: 'pcsmp', '@police.gov.bd'
            e = (cl[j + 1] + (cl[j + 2] if cl[j + 2].startswith("@") else "")).strip().lower() if j is not None else ""
            pc_mail = e if re.match(r"^[\w.]+@police\.gov\.bd$", e) else ""
            pc_mob = off(re.sub(r"[^\d-]", "", asc(val("মোবাইল"))).replace("-", "")) if val("মোবাইল") else ""
            break
    places.append(dict(source_key=key, source_id="smp-hq", name_bn="সিলেট মেট্রোপলিটন পুলিশ হেডকোয়ার্টার্স", name_en="",
                       category_key="government.sp_office", address=ad.group(1) if ad else "", district_en="Sylhet",
                       phone="; ".join(x for x in (pc_office, pc_mob) if x), email=pc_mail, website=SMP_HOME,
                       operator="বাংলাদেশ পুলিশ", ownership="public",
                       extra_json=xj({"office": "Police Commissioner, SMP", "commissioner_office_phone": pc_office,
                                      "commissioner_official_mobile": pc_mob, "area_en": ""}),
                       source_url=SMP_CONTACT,
                       notes="Police Commissioner's office (metropolitan equivalent of an SP office) — closest taxonomy key government.sp_office. "
                             "Name and address from the SMP national-portal 'যোগাযোগ' ('সিলেট মেট্রোপলিটন পুলিশ হেডকোয়ার্টার্স'); office phone, "
                             "official e-mail and the Commissioner post's police official mobile from the Commissioner's officer card (%s); "
                             "officer's name not copied." % SMP_OFFICERS))
    places.append(dict(source_key=key, source_id="smp-control-room", name_bn="এসএমপি কন্ট্রোল রুম", name_en="SMP Control Room",
                       category_key="emergency", district_en="Sylhet",
                       phone="; ".join(x for x in (off(cr.group(1) if cr else ""), off(hot.group(1) if hot else "")) if x),
                       operator="বাংলাদেশ পুলিশ", ownership="public",
                       extra_json=xj({"control_room_mobile": off(cr.group(1) if cr else ""), "smp_hotline": off(hot.group(1) if hot else ""),
                                      "area_en": ""}), source_url=SMP_CONTACT,
                       notes="Name and numbers as on the SMP national-portal 'যোগাযোগ' ('এসএমপি কন্ট্রোল রুম', 'এসএমপি হটলাইন'; police official "
                             "mobiles); smp.police.gov.bd 'যোগাযোগ' gives the same two numbers."))
    save_raw("smp_thanas.txt", "Sources: %s (thana list); %s (Bangla names)\n\n%s" % (SMP_GLANCE, SMP_HOME, "\n".join(raw)))
    save_raw("smp_hq_and_control_room.txt", "HQ (%s): %s\nControl room: %s | Hotline: %s\nCommissioner's card (%s): office phone %s | "
             "e-mail %s | official mobile %s" % (SMP_CONTACT, ad.group(1) if ad else "-", cr.group(1) if cr else "-", hot.group(1) if hot else "-",
                                                 SMP_OFFICERS, pc_office or "-", pc_mail or "-", pc_mob or "-"))
    n = sum(1 for p in places if p["category_key"] == "emergency.police_station")
    facts.append(dict(entity_level="metropolitan_police", entity_name_en="Sylhet Metropolitan Police area", district_en="Sylhet",
                      fact="police_stations", value=n, unit="thanas", basis="listed", year=2026, source_key=key, source_url=SMP_GLANCE,
                      notes="SMP এক নজরে: 'SMP area is divided into six Police stations as %s'; SMP's home page lists the same 6." % (
                          m.group(2) if m else "-")))
    facts.append(dict(entity_level="metropolitan_police", entity_name_en="Sylhet Metropolitan Police area", district_en="Sylhet",
                      fact="police_stations_placed_in_city_corporation", value=0, unit="thanas", basis="listed", year=2026,
                      source_key=key, source_url=SMP_GLANCE, notes=SMP_CC_NOTE))
    write_csv("places.csv", PLACE_COLS, places)
    write_csv("facts.csv", FACT_COLS, facts)
    for w in warn:
        print("WARNING:", w)
    write_manifest(dict(
        key=key, division="sylhet", kind="metro_police_thanas", city=CITY["city"],
        name="Sylhet Metropolitan Police — thanas and official numbers", organization="Sylhet Metropolitan Police (Bangladesh Police)",
        source_type="government_portal", trust_level=4,
        urls=[SMP_GLANCE, SMP_HOME, SMP_CONTACT, SMP_OFFICERS, "https://smp.police.gov.bd/যোগাযোগ/"],
        accessed=__import__("datetime").date.today().isoformat(), publication_date=None, license=None, license_url=None,
        attribution="Sylhet Metropolitan Police (police.sylhetdiv.gov.bd; smp.police.gov.bd)",
        notes="No licence stated. Thana list from SMP's 'এক নজরে' (6 thanas) with the Bangla names of SMP's home page. SMP publishes no "
              "thana numbers (no OC cards; zone ACs' cards are not thana contacts), so thana rows have no phone. HQ address, control room "
              "and hotline (police official mobiles) from the SMP national-portal 'যোগাযোগ'; the Commissioner's office phone, official "
              "e-mail and official mobile from the officer card. Officers' names are not copied. " + SMP_CC_NOTE),
        ["places.csv", "facts.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))



CITIES = {  # metro police force -> collector (Dhaka Division has two, DIVISIONS.md)
    "dhaka": dict(division="dhaka", folder="dhaka_metro_police_thanas_2026", key="DHAKA_METRO_POLICE_THANAS_2026", city=[50001, 50002], run=main_dmp),
    "gazipur": dict(division="dhaka", folder="gazipur_metro_police_thanas_2026", key="GAZIPUR_METRO_POLICE_THANAS_2026", city=50011, run=main_gmp),
    "chattogram": dict(division="chattogram", folder="chattogram_metro_police_thanas_2026", key="CHATTOGRAM_METRO_POLICE_THANAS_2026",
                       city=50003, run=main_cmp),
    "khulna": dict(division="khulna", folder="khulna_metro_police_thanas_2026", key="KHULNA_METRO_POLICE_THANAS_2026", city=50004,
                   run=main_kmp),
    "barishal": dict(division="barishal", folder="barishal_metro_police_thanas_2026", key="BARISHAL_METRO_POLICE_THANAS_2026", city=50007,
                     run=main_bmp),
    "sylhet": dict(division="sylhet", folder="sylhet_metro_police_thanas_2026", key="SYLHET_METRO_POLICE_THANAS_2026", city=50006,
                   run=main_smp),
}
CITY = None


def configure():
    """--division/--out as before; multi-city divisions (Dhaka) also take --city and run each force into its own folder."""
    global DIVISION, HERE, RAW
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().split("\n")[0])
    ap.add_argument("--division", default="rajshahi", choices=DIVISION_CHOICES)
    ap.add_argument("--city", choices=sorted(CITIES), help="one force of a multi-city division (default: all of them)")
    ap.add_argument("--out", help="output folder (for a multi-city division only with a single --city)")
    a = ap.parse_args()
    if a.division in SITES and not a.city:
        DIVISION, out = parse_division_args({k: v["folder"] for k, v in SITES.items()})
        HERE = Path(out)
        RAW = HERE / "raw"
        return
    cities = [c for c, v in CITIES.items() if v["division"] == a.division and (a.city is None or c == a.city)]
    if not cities:
        raise SystemExit("no metro police collector for division %r / city %r" % (a.division, a.city))
    if a.out and len(cities) > 1:
        raise SystemExit("--out needs a single --city")
    DIVISION = a.division
    SITES[DIVISION] = dict(run=lambda: run_cities(cities, a.out))


def run_cities(cities, out):
    global HERE, RAW, CITY
    here = Path(__file__).resolve().parent
    for c in cities:
        CITY = CITIES[c]
        HERE = Path(out).resolve() if out else (here / ".." / CITY["folder"]).resolve()
        if HERE == here:
            raise SystemExit("refusing to write %s output into the Rajshahi folder" % c)
        HERE.mkdir(parents=True, exist_ok=True)
        RAW = HERE / "raw"
        print("==", c, "->", HERE, file=sys.stderr)
        CITY["run"]()


if __name__ == "__main__":
    main()
