#!/usr/bin/env python3
"""Fetch SP-office / thana numbers from the district police portals of a police range (default Rajshahi Range, RAJ_RANGE_POLICE_PORTALS_2026).

Usage: python3 fetch.py [--division rangpur|dhaka|chattogram|khulna|barishal|sylhet|mymensingh] [--out DIR]. The division's head district is covered by <division>_police_2026."""
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

# --- RAJ_RANGE_POLICE_PORTALS_2026 --------------------------------------------------------------------
KEY = "RAJ_RANGE_POLICE_PORTALS_2026"
CONTACT = {  # district -> contact page on police.<district>.gov.bd (discovered from each portal's menu)
    "Natore": "https://police.natore.gov.bd/pages/static-pages/697fdcd735ce18e1c06d8427",
    "Naogaon": "https://police.naogaon.gov.bd/pages/static-pages/698009d935ce18e1c06e365e",
    "Chapainawabganj": "https://police.chapainawabganj.gov.bd/pages/static-pages/697ff42635ce18e1c06dcbf1",
    "Bogura": "https://police.bogura.gov.bd/pages/static-pages/697f895535ce18e1c06b9a85",
    "Joypurhat": "https://police.joypurhat.gov.bd/pages/static-pages/697f6db235ce18e1c06b05d0",
    "Pabna": "https://police.pabna.gov.bd/pages/static-pages/697f893635ce18e1c06b8c6a",
    "Sirajganj": "https://police.sirajganj.gov.bd/pages/static-pages/697fc88a35ce18e1c06d0e68",
}
URL_PABNA_THANAS = "https://police.pabna.gov.bd/pages/static-pages/697f6dd035ce18e1c06b19fa"
DIST_BN = {"Natore": "নাটোর", "Naogaon": "নওগাঁ", "Chapainawabganj": "চাঁপাইনবাবগঞ্জ", "Bogura": "বগুড়া", "Joypurhat": "জয়পুরহাট",
           "Pabna": "পাবনা", "Sirajganj": "সিরাজগঞ্জ"}
UPA = {"Pabna": {"পাবনা সদর": "Pabna Sadar", "ঈশ্বরদী": "Ishwardi", "আটঘরিয়া": "Atgharia", "বেড়া মডেল": "Bera", "বেড়া": "Bera",
                 "সাঁথিয়া": "Santhia", "চাটমোহর": "Chatmohar", "ভাঙ্গুড়া": "Bhangura", "ফরিদপুর": "Faridpur", "সুজানগর": "Sujanagar"},
       "Sirajganj": {"সিরাজগঞ্জ": "Sirajganj Sadar", "শাহজাদপুর": "Shahjadpur", "উল্লাপাড়া": "Ullahpara", "চৌহালী": "Chauhali",
                     "তাড়াশ": "Tarash", "কাজিপুর": "Kazipur", "কামারখন্দ": "Kamarkhanda", "রায়গঞ্জ": "Raiganj", "বেলকুচি": "Belkuchi"}}
NUM = r"(?:\+?৮৮০|\+?880)?[০-৯0-9][০-৯0-9\-]{6,}"


def nums(s):
    return [asc(x) for x in re.findall(NUM, s)]


def sp_row(dist, url, phone="", email="", address="", extra=None, notes=""):
    return dict(source_key=KEY, source_id=f"rangepol-sp-{dist.lower()}", name_bn=f"পুলিশ সুপারের কার্যালয়, {DIST_BN[dist]}", name_en="",
                category_key="government.sp_office", address=address, district_en=dist, phone=phone, email=email,
                operator=f"{DIST_BN[dist]} জেলা পুলিশ", ownership="public", extra_json=xj(extra or {}), source_url=url, notes=notes)


def ctrl_row(dist, url, phone, label, notes=""):
    return dict(source_key=KEY, source_id=f"rangepol-control-{dist.lower()}", name_bn=f"পুলিশ কন্ট্রোল রুম, {DIST_BN[dist]}", name_en="",
                category_key="emergency", district_en=dist, phone=phone, operator=f"{DIST_BN[dist]} জেলা পুলিশ", ownership="public",
                extra_json=xj({"label_in_source": label}), source_url=url, notes=notes)


def thana_rows(dist, url, rows, names_from_list=None):
    """rows: list of table rows [label, (old), new]. Builds one place per 'অফিসার ইনচার্জ' row, attaching the duty-officer row."""
    out, by_key = [], {}
    for row in rows:
        label = row[0]
        ph = [phone_norm(c) for c in row[1:] if phone_norm(c)]
        m = re.match(r"অফিসার-? ?ইনচার্জ, (.+?থানা)", label)
        if m:
            th = nfc(m.group(1))
            base = th.replace(" থানা", "")
            name = th
            if names_from_list:   # Pabna: 'সদর থানা' -> 'পাবনা সদর থানা' from the thana list page
                name = next((n for n in names_from_list if n.replace(" থানা", "").endswith(base) or base.startswith(n.replace(" থানা", ""))), th)
            key = name.replace(" মডেল", "").replace(" থানা", "")
            upa = UPA.get(dist, {}).get(key, UPA.get(dist, {}).get(name.replace(" থানা", ""), ""))
            current = ph[-1] if ph else ""
            extra = {"oc_mobile": current, "label_in_source": label}
            if len(ph) > 1:
                extra["oc_previous_number"] = ph[0]
            rec = dict(source_key=KEY, source_id=f"rangepol-{dist.lower()}-{len(out) + 1}", name_bn=name, name_en="",
                       category_key="emergency.police_station", district_en=dist, upazila_en=upa, phone=current,
                       operator=f"{DIST_BN[dist]} জেলা পুলিশ", ownership="public", _extra=extra, source_url=url,
                       notes="phone = OC official mobile as published by the district police" + ("" if upa else "; thana is not an upazila (upazila_en empty)"))
            out.append(rec)
            by_key[base.replace(" মডেল", "")] = rec
            continue
        m = re.match(r"ডিউটি অফিসার, (.+?) থানা", label)
        if m:
            base = nfc(m.group(1)).replace(" মডেল", "")
            rec = by_key.get(base) or next((v for k, v in by_key.items() if base in k or k in base or (dist == "Pabna" and base == "পাবনা" and k == "সদর")), None)
            if rec and ph:
                rec["_extra"]["duty_officer_mobile"] = ph[-1]
                rec["phone"] = rec["phone"] + "; " + ph[-1]
    for r in out:
        r["extra_json"] = xj(r.pop("_extra"))
    return out


def main():
    configure()
    if DIVISION != "rajshahi":
        return RANGES[DIVISION]["run"]()
    places, facts, missing = [], [], []
    pages = {}
    for dist, url in CONTACT.items():
        r = get(url)
        if r is None or r.status_code != 200:
            missing.append(f"{dist}: {url} -> {getattr(r, 'status_code', 'no response')}")
            continue
        pages[dist] = r.text
        save_raw(f"{dist.lower()}_police_contact.txt", "\n".join(content_text(r.text)))
    # Natore: SP office mobile + e-mail only
    if "Natore" in pages:
        txt = " ".join(content_text(pages["Natore"]))
        em = re.search(r"[\w.]+@police\.gov\.bd", txt)
        places.append(sp_row("Natore", CONTACT["Natore"], phone="; ".join(phone_norm(x) for x in nums(txt)), email=em.group(0) if em else "",
                             notes="Natore portal gives 01320-125498 for the SP office; the 2020 Police-HQ list has 01320-125498 as the Natore control room and 01320-124500 as the SP"))
    # Chapainawabganj: SP office phone/fax/e-mail + control room
    if "Chapainawabganj" in pages:
        lines = content_text(pages["Chapainawabganj"])
        txt = " ".join(lines)
        ph = re.search(r"ফোনঃ\s*(" + NUM + ")", txt)
        fx = re.search(r"ফ্যাক্সঃ\s*(" + NUM + ")", txt)
        em = re.search(r"(?:www\.)?([\w.]+@police\.gov\.bd)", txt)
        places.append(sp_row("Chapainawabganj", CONTACT["Chapainawabganj"], phone=asc(ph.group(1)) if ph else "",
                             email=em.group(1) if em else "", address="জেলা প্রশাসক কার্যালয়ের পার্শ্বে" if "জেলা প্রশাসক কার্যালয়ের পার্শ্বে" in txt else "",
                             extra={"fax": asc(fx.group(1)) if fx else ""},
                             notes="Source prints the e-mail as 'www.spchapainawabganj@police.gov.bd' (the 'www.' was dropped). Address is the portal's location hint only."))
        for t in tables(pages["Chapainawabganj"]):
            for row in t:
                if row and row[0].startswith("Telephone Number") and len(row) > 1:
                    places.append(ctrl_row("Chapainawabganj", CONTACT["Chapainawabganj"], phone_norm(row[1]),
                                           "Police Control Room (24 hours help desk)", notes="Name composed from 'Police Control Room (24 hours help desk)'"))
    # Bogura: SP office address/phone/fax/e-mail
    if "Bogura" in pages:
        txt = " ".join(content_text(pages["Bogura"]))
        ph = re.search(r"ফোন-\s*(" + NUM + ")", txt)
        fx = re.search(r"ফ্যাক্স-\s*(" + NUM + ")", txt)
        em = re.search(r"[\w.]+@police\.gov\.bd", txt)
        ad = re.search(r"পুলিশ সুপারের কার্যালয়\s+(.+?বগুড়া)", txt)
        places.append(sp_row("Bogura", CONTACT["Bogura"], phone=asc(ph.group(1)) if ph else "", email=em.group(0) if em else "",
                             address=ad.group(1) if ad else "", extra={"fax": asc(fx.group(1)) if fx else ""}))
    # Joypurhat: SP office address + numbers
    if "Joypurhat" in pages:
        txt = " ".join(content_text(pages["Joypurhat"]))
        ad = re.search(r"পুলিশ সুপারের কার্যালয়, (.+?জয়পুরহাট-[০-৯0-9]+)", txt)
        m1 = re.search(r"মোবাইল:\s*(" + NUM + ")", txt)
        m2 = re.search(r"বিকল্প মোবাইল:\s*(" + NUM + ")", txt)
        tl = re.search(r"টেলিফোন:\s*(" + NUM + ")", txt)
        phones = [asc(x.group(1)) for x in (m1, tl) if x]
        places.append(sp_row("Joypurhat", CONTACT["Joypurhat"], phone="; ".join(phones), address=ad.group(1) if ad else "",
                             extra={"alt_mobile": asc(m2.group(1)) if m2 else ""},
                             notes="Alternative mobile 01320128498 is listed as the Joypurhat control room in the 2020 Police-HQ list"))
    # Pabna: thana list + numbers
    if "Pabna" in pages:
        names = []
        r = get(URL_PABNA_THANAS)
        if r is not None and r.ok:
            save_raw("pabna_police_thanas.txt", "\n".join(content_text(r.text)))
            names = [nfc(n) for n in re.findall(r"[০-৯]+\.\s*([^০-৯.]+?থানা)", " ".join(content_text(r.text)))]
            facts.append(dict(entity_level="district", entity_name_en="Pabna", district_en="Pabna", fact="police_stations", value=len(names),
                              unit="thanas", basis="listed", year=2026, source_key=KEY, source_url=URL_PABNA_THANAS,
                              notes="থানাসমূহ: " + ", ".join(names)))
        rows = [r for t in tables(pages["Pabna"]) for r in t if len(r) >= 2]
        sp = next((r for r in rows if r[0].startswith("পুলিশ সুপার, পাবনা")), None)
        places.append(sp_row("Pabna", CONTACT["Pabna"], phone=phone_norm(sp[1]) if sp else "", notes="phone = Superintendent of Police official number"))
        cr = next((r for r in rows if r[0].startswith("পুলিশ কন্ট্রোল রুম")), None)
        if cr:
            places.append(ctrl_row("Pabna", CONTACT["Pabna"], phone_norm(cr[1]), cr[0]))
        places += thana_rows("Pabna", CONTACT["Pabna"], rows, names_from_list=names)
    # Sirajganj: SP + thanas (previous and current numbers) + control room
    if "Sirajganj" in pages:
        rows = [r for t in tables(pages["Sirajganj"]) for r in t if len(r) >= 2]
        sp = next((r for r in rows if r[0] == "পুলিশ সুপার"), None)
        places.append(sp_row("Sirajganj", CONTACT["Sirajganj"], phone=phone_norm(sp[-1]) if sp else "",
                             extra={"previous_number": phone_norm(sp[1]) if sp and len(sp) > 2 else ""},
                             notes="phone = Superintendent of Police official number ('বর্তমান নম্বর')"))
        cr = next((r for r in rows if r[0].startswith("পুলিশ কন্ট্রোল রুম")), None)
        if cr:
            places.append(ctrl_row("Sirajganj", CONTACT["Sirajganj"], "; ".join(phone_norm(c) for c in cr[1:] if phone_norm(c)), cr[0]))
        th = thana_rows("Sirajganj", CONTACT["Sirajganj"], rows)
        places += th
        facts.append(dict(entity_level="district", entity_name_en="Sirajganj", district_en="Sirajganj", fact="police_stations", value=len(th),
                          unit="thanas", basis="listed", year=2026, source_key=KEY, source_url=CONTACT["Sirajganj"],
                          notes="Counted from OC rows of the district police contact table"))
    write_csv("places.csv", PLACE_COLS, places)
    write_csv("facts.csv", FACT_COLS, facts)
    if missing:
        print("unavailable:", missing)
    write_manifest(dict(
        key=KEY, division="rajshahi", kind="range_police", name="District police portals of Rajshahi Range (Natore, Naogaon, Chapainawabganj, Bogura, Joypurhat, Pabna, Sirajganj)",
        organization="Bangladesh Police — district police units of Rajshahi Range", source_type="government_portal", trust_level=4,
        urls=list(CONTACT.values()) + [URL_PABNA_THANAS], accessed=__import__("datetime").date.today().isoformat(),
        publication_date=None, license=None, license_url=None, attribution="District police portals (police.<district>.gov.bd)",
        notes="No licence stated. Institutional numbers only, no officer names. Only Pabna and Sirajganj publish per-thana numbers; "
              "Natore, Chapainawabganj, Bogura and Joypurhat publish SP-office contacts only; Naogaon's contact page returned 404 "
              + ("(this run: " + "; ".join(missing) + ")" if missing else "") + ". Rajshahi District is in RAJSHAHI_POLICE_2026."),
        ["places.csv", "facts.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


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


# Rangpur Division names: Bangla -> English (HDX COD-AB spellings). District hosts verified by page title (Nov 2026);
# upazila portal subdomains verified by their home-page titles ("হোম | <upazila> উপজেলা").
RANGPUR_DISTRICTS = {"রংপুর": "Rangpur", "পঞ্চগড়": "Panchagarh", "দিনাজপুর": "Dinajpur", "লালমনিরহাট": "Lalmonirhat",
                     "নীলফামারী": "Nilphamari", "গাইবান্ধা": "Gaibandha", "ঠাকুরগাঁও": "Thakurgaon", "কুড়িগ্রাম": "Kurigram"}
RANGPUR_DISTRICT_HOSTS = {"Rangpur": "rangpur.gov.bd", "Panchagarh": "panchagarh.gov.bd", "Dinajpur": "dinajpur.gov.bd",
                          "Lalmonirhat": "lalmonirhat.gov.bd", "Nilphamari": "nilphamari.gov.bd", "Gaibandha": "gaibandha.gov.bd",
                          "Thakurgaon": "thakurgaon.gov.bd", "Kurigram": "kurigram.gov.bd"}
RANGPUR_UPAZILAS = {  # district -> [(english, bangla names/aliases..., portal subdomain)]
    "Rangpur": [("Badarganj", ["বদরগঞ্জ"], "badargonj"), ("Gangachara", ["গংগাচড়া", "গঙ্গাচড়া"], "gangachara"),
                ("Kaunia", ["কাউনিয়া"], "kaunia"), ("Rangpur Sadar", ["রংপুর সদর"], "rangpursadar"),
                ("Mithapukur", ["মিঠাপুকুর"], "mithapukur"), ("Pirgachha", ["পীরগাছা"], "pirgacha"),
                ("Pirganj", ["পীরগঞ্জ"], "pirgonj"), ("Taraganj", ["তারাগঞ্জ"], "taragonj")],
    "Panchagarh": [("Atowari", ["আটোয়ারী"], "atwari"), ("Boda", ["বোদা"], "boda"), ("Debiganj", ["দেবীগঞ্জ"], "debiganj"),
                   ("Panchagarh Sadar", ["পঞ্চগড় সদর"], "panchagarhsadar"), ("Tentulia", ["তেঁতুলিয়া", "তেতুলিয়া"], "tetulia")],
    "Thakurgaon": [("Baliadangi", ["বালিয়াডাঙ্গী", "বালিয়াডাংগী"], "baliadangi"), ("Haripur", ["হরিপুর"], "haripur"),
                   ("Pirganj", ["পীরগঞ্জ"], "pirganj"), ("Ranishankail", ["রাণীশংকৈল", "রানীশংকৈল"], "ranisankail"),
                   ("Thakurgaon Sadar", ["ঠাকুরগাঁও সদর"], "thakurgaonsadar")],
    "Nilphamari": [("Dimla", ["ডিমলা"], "dimla"), ("Domar", ["ডোমার"], "domar"), ("Jaldhaka", ["জলঢাকা"], "jaldhaka"),
                   ("Kishoreganj", ["কিশোরগঞ্জ"], "kishorganj"), ("Nilphamari Sadar", ["নীলফামারী সদর"], "nilphamarisadar"),
                   ("Saidpur", ["সৈয়দপুর"], "syedpur")],
    "Lalmonirhat": [("Aditmari", ["আদিতমারী"], "aditmari"), ("Hatibandha", ["হাতীবান্ধা"], "hatibandha"),
                    ("Kaliganj", ["কালীগঞ্জ"], "kaliganj"), ("Lalmonirhat Sadar", ["লালমনিরহাট সদর"], "sadar"),
                    ("Patgram", ["পাটগ্রাম"], "patgram")],
    "Gaibandha": [("Fulchhari", ["ফুলছড়ি"], "phulchari"), ("Gaibandha Sadar", ["গাইবান্ধা সদর"], "gaibandhasadar"),
                  ("Gobindaganj", ["গোবিন্দগঞ্জ"], "gobindaganj"), ("Palashbari", ["পলাশবাড়ী", "পলাশবাড়ি"], "palashbari"),
                  ("Sadullapur", ["সাদুল্লাপুর", "সাদুল্যাপুর"], "sadullapur"), ("Saghata", ["সাঘাটা"], "saghata"),
                  ("Sundarganj", ["সুন্দরগঞ্জ"], "sundarganj")],
    "Kurigram": [("Bhurungamari", ["ভূরুঙ্গামারী", "ভুরুঙ্গামারী"], "bhurungamari"), ("Rajibpur", ["রাজিবপুর", "রাজীবপুর"], "charrajibpur"),
                 ("Chilmari", ["চিলমারী"], "chilmari"), ("Phulbari", ["ফুলবাড়ী"], "phulbari"),
                 ("Kurigram Sadar", ["কুড়িগ্রাম সদর"], "kurigramsadar"), ("Nageshwari", ["নাগেশ্বরী"], "nageshwari"),
                 ("Rajarhat", ["রাজারহাট"], "rajarhat"), ("Roumari", ["রৌমারী"], "rowmari"), ("Ulipur", ["উলিপুর"], "ulipur")],
    "Dinajpur": [("Birampur", ["বিরামপুর"], "birampur"), ("Birganj", ["বীরগঞ্জ"], "birganj"), ("Birol", ["বিরল"], "birol"),
                 ("Bochaganj", ["বোচাগঞ্জ"], "bochaganj"), ("Chirirbandar", ["চিরিরবন্দর"], "chirirbandar"),
                 ("Fulbari", ["ফুলবাড়ী"], "fulbari"), ("Ghoraghat", ["ঘোড়াঘাট"], "ghoraghat"), ("Hakimpur", ["হাকিমপুর"], "hakimpur"),
                 ("Kaharole", ["কাহারোল"], "kaharol"), ("Khansama", ["খানসামা"], "khansama"),
                 ("Dinajpur Sadar", ["দিনাজপুর সদর"], "dinajpursadar"), ("Nababganj", ["নবাবগঞ্জ"], "nawabganj"),
                 ("Parbatipur", ["পার্বতীপুর"], "parbatipur")],
}
# Rangpur Metropolitan Police thanas (rpmp.gov.bd), English transliterations
RANGPUR_CITY_THANAS = {"কোতয়ালী": "Kotwali", "তাজহাট": "Tajhat", "মাহিগঞ্জ": "Mahiganj", "হারাগাছ": "Haragach",
                       "পরশুরাম": "Parshuram", "হাজিরহাট": "Hajirhat"}
# Dhaka Division names: Bangla -> English (HDX COD-AB v03 spellings). District hosts verified by page title (Nov 2026);
# upazila portal subdomains verified by their home-page titles ("হোম | <upazila> উপজেলা").
DHAKA_DISTRICTS = {"ঢাকা": "Dhaka", "নরসিংদী": "Narsingdi", "গাজীপুর": "Gazipur", "শরীয়তপুর": "Shariatpur",
                   "নারায়ণগঞ্জ": "Narayanganj", "টাঙ্গাইল": "Tangail", "কিশোরগঞ্জ": "Kishoreganj", "মানিকগঞ্জ": "Manikganj",
                   "মুন্সীগঞ্জ": "Munshiganj", "রাজবাড়ী": "Rajbari", "মাদারীপুর": "Madaripur", "গোপালগঞ্জ": "Gopalganj",
                   "ফরিদপুর": "Faridpur"}
DHAKA_DISTRICT_HOSTS = {en: "%s.gov.bd" % en.lower() for en in DHAKA_DISTRICTS.values()}
DHAKA_UPAZILAS = {  # district -> [(english, bangla names/aliases..., portal subdomain)]
    "Dhaka": [("Dhamrai", ["ধামরাই"], "dhamrai"), ("Dohar", ["দোহার"], "dohar"),
              ("Keraniganj", ["কেরাণীগঞ্জ", "কেরানীগঞ্জ"], "keraniganj"), ("Nawabganj", ["নবাবগঞ্জ"], "nawabganj"),
              ("Savar", ["সাভার"], "savar")],
    "Narsingdi": [("Belabo", ["বেলাবো", "বেলাব"], "belabo"), ("Manohardi", ["মনোহরদী", "মনোহরদি"], "monohardi"),
                  ("Narsingdi Sadar", ["নরসিংদী সদর"], "narsingdisadar"), ("Palash", ["পলাশ"], "palash"),
                  ("Raipura", ["রায়পুরা"], "raipura"), ("Shibpur", ["শিবপুর"], "shibpur")],
    "Gazipur": [("Gazipur Sadar", ["গাজীপুর সদর"], "sadar"), ("Kaliakair", ["কালিয়াকৈর"], "kaliakair"),
                ("Kaliganj", ["কালীগঞ্জ"], "kaliganj"), ("Kapasia", ["কাপাসিয়া"], "kapasia"), ("Sreepur", ["শ্রীপুর"], "sreepur")],
    "Shariatpur": [("Bhedarganj", ["ভেদরগঞ্জ"], "bhedarganj"), ("Damudya", ["ডামুড্যা"], "damudya"),
                   ("Gosairhat", ["গোসাইরহাট"], "gosairhat"), ("Naria", ["নড়িয়া"], "naria"),
                   ("Shariatpur Sadar", ["শরীয়তপুর সদর", "শরিয়তপুর সদর"], "sadar"), ("Zajira", ["জাজিরা"], "zajira")],
    "Narayanganj": [("Araihazar", ["আড়াইহাজার"], "araihazar"), ("Bandar", ["বন্দর"], "bandar"),
                    ("Narayanganj Sadar", ["নারায়ণগঞ্জ সদর", "নারায়নগঞ্জ সদর"], "narayanganjsadar"),
                    ("Rupganj", ["রূপগঞ্জ"], "rupganj"), ("Sonargaon", ["সোনারগাঁও", "সোনারগাঁ"], "sonargaon")],
    "Tangail": [("Basail", ["বাসাইল"], "basail"), ("Bhuanpur", ["ভূঞাপুর", "ভুয়াপুর", "ভূয়াপুর"], "bhuapur"),
                ("Delduar", ["দেলদুয়ার"], "delduar"), ("Dhanbari", ["ধনবাড়ী", "ধনবাড়ি"], "dhanbari"),
                ("Ghatail", ["ঘাটাইল"], "ghatail"), ("Gopalpur", ["গোপালপুর"], "gopalpur"), ("Kalihati", ["কালিহাতী"], "kalihati"),
                ("Madhupur", ["মধুপুর"], "madhupur"), ("Mirzapur", ["মির্জাপুর"], "mirzapur"), ("Nagarpur", ["নাগরপুর"], "nagarpur"),
                ("Sakhipur", ["সখিপুর", "সখীপুর"], "sakhipur"), ("Tangail Sadar", ["টাঙ্গাইল সদর"], "tangailsadar")],
    "Kishoreganj": [("Austagram", ["অষ্টগ্রাম"], "austagram"), ("Bajitpur", ["বাজিতপুর"], "bajitpur"), ("Bhairab", ["ভৈরব"], "bhairab"),
                    ("Hossainpur", ["হোসেনপুর"], "hossainpur"), ("Itna", ["ইটনা"], "itna"), ("Karimganj", ["করিমগঞ্জ"], "karimgonj"),
                    ("Katiadi", ["কটিয়াদী", "কটিয়াদি"], "katiadi"), ("Kishoreganj Sadar", ["কিশোরগঞ্জ সদর"], "kishoreganjsadar"),
                    ("Kuliarchar", ["কুলিয়ারচর"], "kuliarchar"), ("Mithamain", ["মিঠামইন"], "mithamoin"), ("Nikli", ["নিকলী", "নিকলি"], "nikli"),
                    ("Pakundia", ["পাকুন্দিয়া"], "pakundia"), ("Tarail", ["তাড়াইল"], "tarail")],
    "Manikganj": [("Daulatpur", ["দৌলতপুর"], "daulatpur"), ("Ghior", ["ঘিওর"], "gior"), ("Harirampur", ["হরিরামপুর"], "harirampur"),
                  ("Manikganj Sadar", ["মানিকগঞ্জ সদর"], "sadar"), ("Saturia", ["সাটুরিয়া"], "saturia"),
                  ("Shibalay", ["শিবালয়"], "shibaloy"), ("Singair", ["সিংগাইর", "সিঙ্গাইর"], "singair")],
    "Munshiganj": [("Gazaria", ["গজারিয়া"], "gajaria"), ("Louhajang", ["লৌহজং"], "louhajanj"),
                   ("Munshiganj Sadar", ["মুন্সীগঞ্জ সদর", "মুন্সিগঞ্জ সদর"], "sadar"), ("Sirajdikhan", ["সিরাজদিখান"], "sirajdikhan"),
                   ("Sreenagar", ["শ্রীনগর"], "sreenagar"), ("Tongibari", ["টংগিবাড়ী", "টংগীবাড়ি", "টঙ্গিবাড়ী", "টংগীবাড়ী"], "tongibari")],
    "Rajbari": [("Baliakandi", ["বালিয়াকান্দি"], "baliakandi"), ("Goalanda", ["গোয়ালন্দ"], "goalanda"),
                ("Kalukhali", ["কালুখালী", "কালুখালি"], "kalukhali"), ("Pangsha", ["পাংশা"], "pangsa"),
                ("Rajbari Sadar", ["রাজবাড়ী সদর"], "sadar")],
    "Madaripur": [("Dasar", ["ডাসার"], "dasar"), ("Kalkini", ["কালকিনি"], "kalkini"), ("Madaripur Sadar", ["মাদারীপুর সদর"], "sadar"),
                  ("Rajoir", ["রাজৈর"], "rajoir"), ("Shibchar", ["শিবচর"], "shibchar")],
    "Gopalganj": [("Gopalganj Sadar", ["গোপালগঞ্জ সদর"], "sadar"), ("Kashiani", ["কাশিয়ানী"], "kashiani"),
                  ("Kotalipara", ["কোটালীপাড়া"], "kotalipara"), ("Muksudpur", ["মুকসুদপুর"], "muksudpur"),
                  ("Tungipara", ["টুঙ্গিপাড়া", "টুংগীপাড়া"], "tungipara")],
    "Faridpur": [("Alfadanga", ["আলফাডাঙ্গা"], "alfadanga"), ("Bhanga", ["ভাঙ্গা"], "bhanga"), ("Boalmari", ["বোয়ালমারী"], "boalmari"),
                 ("Char Bhadrasan", ["চরভদ্রাসন"], "charbhadrasan"), ("Faridpur Sadar", ["ফরিদপুর সদর"], "sadar"),
                 ("Madhukhali", ["মধুখালী"], "madhukhali"), ("Nagarkanda", ["নগরকান্দা"], "nagarkanda"), ("Sadarpur", ["সদরপুর"], "sadarpur"),
                 ("Saltha", ["সালথা"], "saltha")],
}
# Dhaka Metropolitan Police thanas (Dhaka DC portal 'এক নজরে' list + Khilkhet from dmp.gov.bd), English names as DMP spells
# them where it lists them (normalised spacing). Longer names first so 'তেজগাঁও শিল্পাঞ্চল' wins over 'তেজগাঁও'.
DHAKA_CITY_THANAS = {
    "তেজগাঁও শিল্পাঞ্চল": "Tejgaon Industrial Area", "শেরেবাংলা নগর": "Sher-e-Bangla Nagar", "কামরাঙ্গীরচর": "Kamrangirchar",
    "উত্তরা পশ্চিম": "Uttara West", "উত্তরা পূর্ব": "Uttara East", "দারুস সালাম": "Darus Salam", "শাহজাহানপুর": "Shahjahanpur",
    "কোতোয়ালী": "Kotwali", "সূত্রাপুর": "Sutrapur", "বংশাল": "Bangshal", "চকবাজার": "Chawkbazar", "লালবাগ": "Lalbagh",
    "ওয়ারী": "Wari", "গেন্ডারিয়া": "Gandaria", "খিলগাঁও": "Khilgaon", "রামপুরা": "Rampura", "মতিঝিল": "Motijheel",
    "সবুজবাগ": "Sabujbagh", "মুগদা": "Mugda", "যাত্রাবাড়ী": "Jatrabari", "ডেমরা": "Demra", "শ্যামপুর": "Shyampur",
    "কদমতলী": "Kadamtali", "পল্টন": "Paltan", "শাহবাগ": "Shahbagh", "রমনা": "Ramna", "ধানমন্ডি": "Dhanmondi",
    "নিউমার্কেট": "New Market", "কলাবাগান": "Kalabagan", "হাজারীবাগ": "Hazaribagh", "মোহাম্মদপুর": "Mohammadpur",
    "আদাবর": "Adabor", "তেজগাঁও": "Tejgaon", "ভাষানটেক": "Bhashantek", "কাফরুল": "Kafrul", "মিরপুর": "Mirpur",
    "পল্লবী": "Pallabi", "শাহআলী": "Shah Ali", "রূপনগর": "Rupnagar", "বাড্ডা": "Badda", "ভাটারা": "Bhatara",
    "বনানী": "Banani", "গুলশান": "Gulshan", "ক্যান্টনমেন্ট": "Cantonment", "তুরাগ": "Turag", "উত্তরখান": "Uttar Khan",
    "দক্ষিণখান": "Dakshinkhan", "হাতিরঝিল": "Hatirjheel", "বিমানবন্দর": "Biman Bandar", "খিলক্ষেত": "Khilkhet"}


# Chattogram Division names: Bangla -> English (HDX COD-AB v03 spellings). District hosts verified by page title (Nov 2026;
# comilla.gov.bd / chittagong.gov.bd are the hosts the portals' own menus use, cumilla.gov.bd / chattogram.gov.bd serve the
# same sites); upazila portal subdomains verified by their home-page titles ("হোম | <upazila> উপজেলা").
CHATTOGRAM_DISTRICTS = {"চট্টগ্রাম": "Chattogram", "কুমিল্লা": "Cumilla", "ফেনী": "Feni", "ব্রাহ্মণবাড়িয়া": "Brahmanbaria",
                        "রাঙ্গামাটি": "Rangamati", "নোয়াখালী": "Noakhali", "চাঁদপুর": "Chandpur", "লক্ষ্মীপুর": "Lakshmipur",
                        "কক্সবাজার": "Cox's Bazar", "খাগড়াছড়ি": "Khagrachhari", "বান্দরবান": "Bandarban"}
CHATTOGRAM_DISTRICT_HOSTS = {"Chattogram": "chittagong.gov.bd", "Cumilla": "comilla.gov.bd", "Feni": "feni.gov.bd",
                             "Brahmanbaria": "brahmanbaria.gov.bd", "Rangamati": "rangamati.gov.bd", "Noakhali": "noakhali.gov.bd",
                             "Chandpur": "chandpur.gov.bd", "Lakshmipur": "lakshmipur.gov.bd", "Cox's Bazar": "coxsbazar.gov.bd",
                             "Khagrachhari": "khagrachhari.gov.bd", "Bandarban": "bandarban.gov.bd"}
CHATTOGRAM_UPAZILAS = {  # district -> [(english, bangla names/aliases..., portal subdomain)]
    "Chattogram": [("Anwara", ["আনোয়ারা"], "anwara"), ("Banshkhali", ["বাঁশখালী", "বাশখালী"], "banshkhali"),
                   ("Boalkhali", ["বোয়ালখালী"], "boalkhali"), ("Chandanaish", ["চন্দনাইশ"], "chandanaish"),
                   ("Fatikchhari", ["ফটিকছড়ি"], "fatikchhari"), ("Hathazari", ["হাটহাজারী"], "hathazari"),
                   ("Karnaphuli", ["কর্ণফুলী", "কর্ণফুলি"], "karnafuli"), ("Lohagara", ["লোহাগাড়া"], "lohagara"),
                   ("Mirsarai", ["মীরসরাই", "মিরসরাই"], "mirsharai"), ("Patiya", ["পটিয়া"], "patiya"),
                   ("Rangunia", ["রাঙ্গুনিয়া", "রাংগুনিয়া"], "rangunia"), ("Raozan", ["রাউজান"], "raozan"),
                   ("Sandwip", ["সন্দ্বীপ"], "sandwip"), ("Satkania", ["সাতকানিয়া"], "satkania"),
                   ("Sitakunda", ["সীতাকুন্ড", "সীতাকুণ্ড"], "sitakunda")],
    "Cumilla": [("Sadar Dakkhin", ["সদর দক্ষিণ", "কুমিল্লা সদর দক্ষিণ"], "sadarsouth"),
                ("Adarsha Sadar", ["আদর্শ সদর", "কুমিল্লা আদর্শ সদর", "কুমিল্লা সদর"], "comillasadar"),
                ("Barura", ["বরুড়া"], "barura"), ("Brahmanpara", ["ব্রাহ্মণপাড়া"], "brahmanpara"),
                ("Burichang", ["বুড়িচং"], "burichang"), ("Chandina", ["চান্দিনা"], "chandina"),
                ("Chauddagram", ["চৌদ্দগ্রাম"], "chauddagram"), ("Daudkandi", ["দাউদকান্দি"], "daudkandi"),
                ("Debidwar", ["দেবিদ্বার"], "debidwar"), ("Homna", ["হোমনা"], "homna"), ("Laksam", ["লাকসাম"], "laksam"),
                ("Lalmai", ["লালমাই"], "lalmai"), ("Manoharganj", ["মনোহরগঞ্জ"], "monohargonj"), ("Meghna", ["মেঘনা"], "meghna"),
                ("Muradnagar", ["মুরাদনগর"], "muradnagar"), ("Nangalkot", ["নাঙ্গলকোট"], "nangalkot"), ("Titas", ["তিতাস"], "titas")],
    "Feni": [("Chhagalnaiya", ["ছাগলনাইয়া"], "chhagalnaiya"), ("Daganbhuiyan", ["দাগনভূঞা", "দাগনভুঞা"], "daganbhuiyan"),
             ("Feni Sadar", ["ফেনী সদর"], "sadar"), ("Fulgazi", ["ফুলগাজী"], "fulgazi"), ("Parashuram", ["পরশুরাম"], "parshuram"),
             ("Sonagazi", ["সোনাগাজী"], "sonagazi")],
    "Brahmanbaria": [("Akhaura", ["আখাউড়া"], "akhaura"), ("Ashuganj", ["আশুগঞ্জ"], "ashuganj"),
                     ("Banchharampur", ["বাঞ্ছারামপুর"], "bancharampur"), ("Bijoynagar", ["বিজয়নগর"], "bijoynagar"),
                     ("Brahmanbaria Sadar", ["ব্রাহ্মণবাড়িয়া সদর"], "sadar"), ("Kasba", ["কসবা"], "kasba"),
                     ("Nabinagar", ["নবীনগর"], "nabinagar"), ("Nasirnagar", ["নাসিরনগর", "নাছিরনগর"], "nasirnagar"),
                     ("Sarail", ["সরাইল"], "sarail")],
    "Rangamati": [("Baghaichhari", ["বাঘাইছড়ি"], "baghaichari"), ("Barkal", ["বরকল"], "barkal"),
                  ("Belaichhari", ["বিলাইছড়ি"], "belaichari"), ("Jurachhari", ["জুরাছড়ি"], "juraichari"),
                  ("Kaptai", ["কাপ্তাই"], "kaptai"), ("Kawkhali", ["কাউখালী"], "kawkhali"), ("Langadu", ["লংগদু"], "langadu"),
                  ("Naniarchar", ["নানিয়ারচর"], "naniarchar"), ("Rajasthali", ["রাজস্থলী"], "rajasthali"),
                  ("Rangamati Sadar", ["রাঙ্গামাটি সদর"], "sadar")],
    "Noakhali": [("Begumganj", ["বেগমগঞ্জ"], "begumganj"), ("Chatkhil", ["চাটখিল"], "chatkhil"),
                 ("Companiganj", ["কোম্পানীগঞ্জ", "কোম্পানিগঞ্জ"], "companiganj"), ("Hatiya", ["হাতিয়া"], "hatia"),
                 ("Kabirhat", ["কবিরহাট"], "kabirhat"), ("Noakhali Sadar", ["নোয়াখালী সদর"], "sadar"), ("Senbag", ["সেনবাগ"], "senbug"),
                 ("Sonaimuri", ["সোনাইমুড়ী", "সোনাইমুড়ি"], "sonaimuri"), ("Subarnachar", ["সুবর্ণচর"], "subarnachar")],
    "Chandpur": [("Chandpur Sadar", ["চাঁদপুর সদর"], "sadar"), ("Faridganj", ["ফরিদগঞ্জ"], "faridgonj"),
                 ("Haimchar", ["হাইমচর"], "haimchar"), ("Hajiganj", ["হাজীগঞ্জ"], "hajiganj"), ("Kachua", ["কচুয়া"], "kachua"),
                 ("Matlab Dakkhin", ["মতলব দক্ষিণ"], "matlabsouth"), ("Matlab Uttar", ["মতলব উত্তর"], "matlabnorth"),
                 ("Shahrasti", ["শাহরাস্তি"], "shahrasti")],
    "Lakshmipur": [("Kamalnagar", ["কমলনগর"], "kamalnagar"), ("Lakshmipur Sadar", ["লক্ষ্মীপুর সদর"], "sadar"),
                   ("Raipur", ["রায়পুর"], "raipur"), ("Ramganj", ["রামগঞ্জ"], "ramganj"), ("Ramgati", ["রামগতি"], "ramgati")],
    "Cox's Bazar": [("Chakaria", ["চকরিয়া"], "chakaria"), ("Coxs Bazar Sadar", ["কক্সবাজার সদর"], "sadar"),
                    ("Eidgaon", ["ঈদগাঁও", "ঈদগাও"], "eidgaon"), ("Kutubdia", ["কুতুবদিয়া"], "kutubdia"),
                    ("Maheshkhali", ["মহেশখালী", "মহেশখালি"], "moheshkhali"), ("Pekua", ["পেকুয়া"], "pekua"), ("Ramu", ["রামু"], "ramu"),
                    ("Teknaf", ["টেকনাফ"], "teknaf"), ("Ukhia", ["উখিয়া"], "ukhiya")],
    "Khagrachhari": [("Dighinala", ["দীঘিনালা", "দিঘীনালা"], "dighinala"), ("Guimara", ["গুইমারা"], "guimara"),
                     ("Khagrachhari Sadar", ["খাগড়াছড়ি সদর"], "sadar"), ("Lakkhichhari", ["লক্ষ্মীছড়ি", "লক্ষীছড়ি"], "laxmichhari"),
                     ("Mahalchhari", ["মহালছড়ি"], "mohalchari"), ("Manikchhari", ["মানিকছড়ি"], "manikchari"),
                     ("Matiranga", ["মাটিরাঙ্গা", "মাটিরাংগা"], "matiranga"), ("Panchhari", ["পানছড়ি"], "panchari"),
                     ("Ramgarh", ["রামগড়"], "ramgarh")],
    "Bandarban": [("Alikadam", ["আলীকদম"], "alikadam"), ("Bandarban Sadar", ["বান্দরবান সদর"], "sadar"), ("Lama", ["লামা"], "lama"),
                  ("Naikkhongchhari", ["নাইক্ষ্যংছড়ি"], "naikhongchhari"), ("Rowangchhari", ["রোয়াংছড়ি"], "rowangchhari"),
                  ("Ruma", ["রুমা"], "ruma"), ("Thanchi", ["থানচি"], "thanchi")],
}
# Chattogram Metropolitan Police thanas (CMP 'এক নজরে' on police.chittagongdiv.gov.bd), English transliterations. 'বন্দর',
# 'ইপিজেড' and 'কর্ণফুলী' are left out here: as words they name the port, export zones and the river far more often than the thanas.
CHATTOGRAM_CITY_THANAS = {"কোতোয়ালী": "Kotwali", "বাকলিয়া": "Bakalia", "চকবাজার": "Chawkbazar", "পাঁচলাইশ": "Panchlaish",
                          "খুলশী": "Khulshi", "বায়েজিদ বোস্তামী": "Bayezid Bostami", "চান্দগাঁও": "Chandgaon", "পতেঙ্গা": "Patenga",
                          "হালিশহর": "Halishahar", "পাহাড়তলী": "Pahartali", "আকবরশাহ": "Akbarshah", "ডবলমুরিং": "Double Mooring",
                          "সদরঘাট": "Sadarghat"}
# Khulna Division names: Bangla -> English (HDX COD-AB v03 spellings). District hosts verified by page title (Nov 2026; jessore.gov.bd
# is the host the Jashore DC portal's own upazila list uses, jashore.gov.bd serves the same site); upazila portal subdomains
# verified by their home-page titles ("হোম | <upazila> উপজেলা").
KHULNA_DISTRICTS = {"খুলনা": "Khulna", "যশোর": "Jashore", "সাতক্ষীরা": "Satkhira", "মেহেরপুর": "Meherpur", "নড়াইল": "Narail",
                    "চুয়াডাঙ্গা": "Chuadanga", "কুষ্টিয়া": "Kushtia", "মাগুরা": "Magura", "বাগেরহাট": "Bagerhat", "ঝিনাইদহ": "Jhenaidah"}
KHULNA_DISTRICT_HOSTS = {"Khulna": "khulna.gov.bd", "Jashore": "jessore.gov.bd", "Satkhira": "satkhira.gov.bd", "Meherpur": "meherpur.gov.bd",
                         "Narail": "narail.gov.bd", "Chuadanga": "chuadanga.gov.bd", "Kushtia": "kushtia.gov.bd", "Magura": "magura.gov.bd",
                         "Bagerhat": "bagerhat.gov.bd", "Jhenaidah": "jhenaidah.gov.bd"}
KHULNA_UPAZILAS = {  # district -> [(english, bangla names/aliases..., portal subdomain)]
    "Khulna": [("Batiaghata", ["বটিয়াঘাটা"], "botiaghata"), ("Dacope", ["দাকোপ"], "dakop"), ("Dumuria", ["ডুমুরিয়া"], "dumuria"),
               ("Dighalia", ["দিঘলিয়া"], "digholia"), ("Koyra", ["কয়রা"], "koyra"), ("Paikgachha", ["পাইকগাছা"], "paikgasa"),
               ("Phultala", ["ফুলতলা"], "fultola"), ("Rupsa", ["রূপসা", "রুপসা"], "rupsha"), ("Terokhada", ["তেরখাদা"], "terokhada")],
    "Jashore": [("Abhaynagar", ["অভয়নগর"], "abhaynagar"), ("Bagharpara", ["বাঘারপাড়া"], "bagherpara"),
                ("Chaugachha", ["চৌগাছা"], "chougachha"), ("Jhikargachha", ["ঝিকরগাছা"], "jhikargacha"),
                ("Keshabpur", ["কেশবপুর"], "keshabpur"), ("Jashore Sadar", ["যশোর সদর"], "sadar"),
                ("Manirampur", ["মণিরামপুর", "মনিরামপুর"], "manirampur"), ("Sharsha", ["শার্শা"], "sharsha")],
    "Satkhira": [("Ashashuni", ["আশাশুনি"], "assasuni"), ("Debhata", ["দেবহাটা"], "debhata"), ("Kalaroa", ["কলারোয়া"], "kalaroa"),
                 ("Kaliganj", ["কালিগঞ্জ", "কালীগঞ্জ"], "kaliganj"), ("Satkhira Sadar", ["সাতক্ষীরা সদর"], "satkhirasadar"),
                 ("Shyamnagar", ["শ্যামনগর"], "shyamnagar"), ("Tala", ["তালা"], "tala")],
    "Meherpur": [("Gangni", ["গাংনী"], "gangni"), ("Mujibnagar", ["মুজিবনগর"], "mujibnagar"),
                 ("Meherpur Sadar", ["মেহেরপুর সদর"], "meherpursadar")],
    "Narail": [("Kalia", ["কালিয়া"], "kalia"), ("Lohagara", ["লোহাগড়া"], "lohagara"), ("Narail Sadar", ["নড়াইল সদর"], "narailsadar")],
    "Chuadanga": [("Alamdanga", ["আলমডাঙ্গা", "আলমডাঙা"], "alamdanga"), ("Chuadanga Sadar", ["চুয়াডাঙ্গা সদর"], "chuadangasadar"),
                  ("Damurhuda", ["দামুড়হুদা", "দামূড়হুদা"], "damurhuda"), ("Jibannagar", ["জীবননগর"], "jibannagar")],
    "Kushtia": [("Bheramara", ["ভেড়ামারা"], "bheramara"), ("Daulatpur", ["দৌলতপুর"], "daulatpur"), ("Khoksa", ["খোকসা"], "khoksa"),
                ("Kumarkhali", ["কুমারখালী", "কুমারখালি"], "kumarkhali"), ("Kushtia Sadar", ["কুষ্টিয়া সদর"], "kushtiasadar"),
                ("Mirpur", ["মিরপুর"], "mirpur")],
    "Magura": [("Magura Sadar", ["মাগুরা সদর"], "magurasadar"), ("Mohammadpur", ["মহম্মদপুর", "মোহাম্মদপুর"], "mohammadpur"),
               ("Shalikha", ["শালিখা"], "shalikha"), ("Sreepur", ["শ্রীপুর"], "sreepur")],
    "Bagerhat": [("Bagerhat Sadar", ["বাগেরহাট সদর"], "sadar"), ("Chitalmari", ["চিতলমারী"], "chitalmari"), ("Fakirhat", ["ফকিরহাট"], "fakirhat"),
                 ("Kachua", ["কচুয়া"], "kachua"), ("Mollahat", ["মোল্লাহাট"], "mollahat"), ("Mongla", ["মোংলা", "মংলা"], "mongla"),
                 ("Morelganj", ["মোড়েলগঞ্জ", "মোরেলগঞ্জ"], "morrelganj"), ("Rampal", ["রামপাল"], "rampal"),
                 ("Sharankhola", ["শরণখোলা"], "sarankhola")],
    "Jhenaidah": [("Harinakundu", ["হরিণাকুন্ডু", "হরিণাকুণ্ডু"], "harinakundu"), ("Jhenaidah Sadar", ["ঝিনাইদহ সদর"], "sadar"),
                  ("Kaliganj", ["কালীগঞ্জ", "কালিগঞ্জ"], "kaliganj"), ("Kotchandpur", ["কোটচাঁদপুর"], "kotchandpur"),
                  ("Maheshpur", ["মহেশপুর"], "moheshpur"), ("Shailkupa", ["শৈলকুপা"], "shailkupa")],
}
# Khulna Metropolitan Police thanas (Khulna DC portal 'ভৌগলিক পরিচিতি' list of 8 'মেট্রোপলিটন থানা'), English: HDX COD-AB spellings
# where HDX has the thana (Daulatpur, Khalishpur, Khan Jahan Ali, Khulna Sadar, Sonadanga), else a transliteration. The DC portal
# calls Khulna Sadar 'কোতয়ালী থানা' (KMP: 'খুলনা থানা'); 'খুলনা' itself is not matched.
KHULNA_CITY_THANAS = {"দৌলতপুর": "Daulatpur", "খালিশপুর": "Khalishpur", "খানজাহান আলী": "Khan Jahan Ali", "খানজাহানআলী": "Khan Jahan Ali",
                      "সোনাডাঙ্গা": "Sonadanga", "কোতয়ালী": "Khulna Sadar", "আড়ংঘাটা": "Aranghata", "হরিণটানা": "Harintana",
                      "হড়িণটানা": "Harintana", "লবণচরা": "Labanchara", "লবনচড়া": "Labanchara"}

# Barishal Division names: Bangla -> English (district names as in the seed; upazila names in common BBS/HDX-style spelling, the
# importer matches them by similarity). District hosts verified by page title (Nov 2026): barisal.gov.bd is the host the Barishal
# DC portal's own upazila list uses (barishal.gov.bd serves the same site); jhalakathi.gov.bd is the Jhalokathi DC portal
# (jhalokathi.gov.bd does not resolve). Upazila portal subdomains verified by their home-page titles ("হোম | <upazila> উপজেলা").
BARISHAL_DISTRICTS = {"বরিশাল": "Barishal", "ঝালকাঠি": "Jhalokathi", "পটুয়াখালী": "Patuakhali", "পিরোজপুর": "Pirojpur", "ভোলা": "Bhola",
                      "বরগুনা": "Barguna"}
BARISHAL_DISTRICT_HOSTS = {"Barishal": "barisal.gov.bd", "Jhalokathi": "jhalakathi.gov.bd", "Patuakhali": "patuakhali.gov.bd",
                           "Pirojpur": "pirojpur.gov.bd", "Bhola": "bhola.gov.bd", "Barguna": "barguna.gov.bd"}
BARISHAL_UPAZILAS = {  # district -> [(english, bangla names/aliases..., portal subdomain)]
    "Barishal": [("Barishal Sadar", ["বরিশাল সদর"], "barisalsadar"), ("Bakerganj", ["বাকেরগঞ্জ"], "bakerganj"),
                 ("Babuganj", ["বাবুগঞ্জ"], "babuganj"), ("Wazirpur", ["উজিরপুর"], "wazirpur"),
                 ("Banaripara", ["বানারীপাড়া", "বানারিপাড়া"], "banaripara"), ("Gaurnadi", ["গৌরনদী", "গৌরনদি"], "gournadi"),
                 ("Agailjhara", ["আগৈলঝাড়া"], "agailjhara"), ("Mehendiganj", ["মেহেন্দিগঞ্জ"], "mehendiganj"),
                 ("Muladi", ["মুলাদী", "মুলাদি"], "muladi"), ("Hizla", ["হিজলা"], "hizla")],
    "Jhalokathi": [("Jhalokathi Sadar", ["ঝালকাঠি সদর"], "sadar"), ("Kathalia", ["কাঠালিয়া", "কাঁঠালিয়া"], "kathalia"),
                   ("Nalchity", ["নলছিটি"], "nalchity"), ("Rajapur", ["রাজাপুর"], "rajapur")],
    "Patuakhali": [("Patuakhali Sadar", ["পটুয়াখালী সদর"], "sadar"), ("Bauphal", ["বাউফল"], "bauphal"), ("Dumki", ["দুমকী", "দুমকি"], "dumki"),
                   ("Dashmina", ["দশমিনা"], "dashmina"), ("Kalapara", ["কলাপাড়া"], "kalapara"), ("Mirzaganj", ["মির্জাগঞ্জ"], "mirzaganj"),
                   ("Galachipa", ["গলাচিপা"], "galachipa"), ("Rangabali", ["রাঙ্গাবালী", "রাঙাবালী", "রাঙ্গাবালি"], "rangabali")],
    "Pirojpur": [("Pirojpur Sadar", ["পিরোজপুর সদর"], "sadar"), ("Nazirpur", ["নাজিরপুর"], "nazirpur"), ("Kawkhali", ["কাউখালী", "কাউখালি"], "kawkhali"),
                 ("Zianagar", ["জিয়ানগর", "ইন্দুরকানী"], "zianagar"), ("Bhandaria", ["ভান্ডারিয়া", "ভাণ্ডারিয়া"], "bhandaria"),
                 ("Mathbaria", ["মঠবাড়ীয়া", "মঠবাড়িয়া"], "mathbaria"), ("Nesarabad", ["নেছারাবাদ", "স্বরূপকাঠি"], "nesarabad")],
    "Bhola": [("Bhola Sadar", ["ভোলা সদর"], "sadar"), ("Burhanuddin", ["বোরহানউদ্দিন", "বোরহান উদ্দিন"], "borhanuddin"),
              ("Char Fasson", ["চরফ্যাশন"], "charfesson"), ("Daulatkhan", ["দৌলতখান"], "doulatkhan"), ("Manpura", ["মনপুরা"], "monpura"),
              ("Tazumuddin", ["তজুমদ্দিন"], "tazumuddin"), ("Lalmohan", ["লালমোহন"], "lalmohan")],
    "Barguna": [("Barguna Sadar", ["বরগুনা সদর"], "sadar"), ("Amtali", ["আমতলী", "আমতলি"], "amtali"), ("Betagi", ["বেতাগী", "বেতাগি"], "betagi"),
                ("Bamna", ["বামনা"], "bamna"), ("Patharghata", ["পাথরঘাটা"], "pathorghata"), ("Taltali", ["তালতলী", "তালতলি"], "taltali")],
}
# Barishal Metropolitan Police thanas (bmp.police.gov.bd thana pages: Kotwali Model, Bandar, Kaunia, Airport). Only the unambiguous
# names are matched in office names: 'বন্দর' (also 'নদী বন্দর', river port) and 'এয়ারপোর্ট' are not.
BARISHAL_CITY_THANAS = {"কোতয়ালী": "Kotwali", "কোতোয়ালী": "Kotwali", "কোতোয়ালি": "Kotwali", "কাউনিয়া": "Kaunia"}
# Sylhet Division names: Bangla -> English (district names as in the seed; upazila names as the seed spells them, the importer
# matches them by similarity). District hosts verified by page title (Nov 2026: 'হোম | <জেলা> জেলা'). Upazila portal subdomains
# from the national portal's office registry (bangladesh.gov.bd/views/union-list), verified by their home-page titles. The new
# Shantiganj upazila (শান্তিগঞ্জ, formerly দক্ষিণ সুনামগঞ্জ) is the seed's South Sunamganj; Madhyanagar is new (2022).
SYLHET_DISTRICTS = {"সিলেট": "Sylhet", "মৌলভীবাজার": "Moulvibazar", "হবিগঞ্জ": "Habiganj", "সুনামগঞ্জ": "Sunamganj"}
SYLHET_DISTRICT_HOSTS = {"Sylhet": "sylhet.gov.bd", "Moulvibazar": "moulvibazar.gov.bd", "Habiganj": "habiganj.gov.bd",
                         "Sunamganj": "sunamganj.gov.bd"}
SYLHET_UPAZILAS = {  # district -> [(english, bangla names/aliases..., portal subdomain)]
    "Sylhet": [("Sylhet Sadar", ["সিলেট সদর"], "sylhetsadar"), ("Beanibazar", ["বিয়ানীবাজার"], "beanibazar"),
               ("Bishwanath", ["বিশ্বনাথ"], "bishwanath"), ("Companiganj", ["কোম্পানীগঞ্জ", "কোম্পানিগঞ্জ"], "companiganj"),
               ("Fenchuganj", ["ফেঞ্চুগঞ্জ"], "fenchuganj"), ("Golapganj", ["গোলাপগঞ্জ"], "golapganj"),
               ("Gowainghat", ["গোয়াইনঘাট"], "gowainghat"), ("Jaintiapur", ["জৈন্তাপুর"], "jaintiapur"),
               ("Kanaighat", ["কানাইঘাট"], "kanaighat"), ("Zakiganj", ["জকিগঞ্জ"], "zakiganj"), ("Balaganj", ["বালাগঞ্জ"], "balaganj"),
               ("Dakshinsurma", ["দক্ষিণ সুরমা"], "dakshinsurma"), ("Osmaninagar", ["ওসমানী নগর", "ওসমানীনগর"], "osmaninagar")],
    "Moulvibazar": [("Moulvibazar Sadar", ["মৌলভীবাজার সদর"], "moulvibazarsadar"), ("Barlekha", ["বড়লেখা"], "barlekha"),
                    ("Juri", ["জুড়ী", "জুড়ি"], "juri"), ("Kamolganj", ["কমলগঞ্জ"], "kamolganj"), ("Kulaura", ["কুলাউড়া"], "kulaura"),
                    ("Rajnagar", ["রাজনগর"], "rajnagar"), ("Sreemangal", ["শ্রীমঙ্গল", "শ্রীমংগল"], "sreemangal")],
    "Habiganj": [("Habiganj Sadar", ["হবিগঞ্জ সদর"], "habiganjsadar"), ("Ajmiriganj", ["আজমিরীগঞ্জ"], "ajmiriganj"),
                 ("Bahubal", ["বাহুবল"], "bahubal"), ("Baniachong", ["বানিয়াচং"], "baniachong"), ("Chunarughat", ["চুনারুঘাট"], "chunarughat"),
                 ("Lakhai", ["লাখাই"], "lakhai"), ("Madhabpur", ["মাধবপুর"], "madhabpur"), ("Nabiganj", ["নবীগঞ্জ"], "nabiganj"),
                 ("Shayestaganj", ["শায়েস্তাগঞ্জ"], "shayestaganj")],
    "Sunamganj": [("Sunamganj Sadar", ["সুনামগঞ্জ সদর"], "sadar"), ("South Sunamganj", ["শান্তিগঞ্জ", "দক্ষিণ সুনামগঞ্জ"], "shantiganj"),
                  ("Bishwambarpur", ["বিশ্বম্ভরপুর"], "bishwambarpur"), ("Chhatak", ["ছাতক"], "chhatak"), ("Derai", ["দিরাই"], "derai"),
                  ("Dharmapasha", ["ধর্মপাশা"], "dharmapasha"), ("Dowarabazar", ["দোয়ারাবাজার"], "dowarabazar"),
                  ("Jagannathpur", ["জগন্নাথপুর"], "jagannathpur"), ("Jamalganj", ["জামালগঞ্জ"], "jamalganj"), ("Shalla", ["শাল্লা"], "shalla"),
                  ("Tahirpur", ["তাহিরপুর"], "tahirpur"), ("Madhyanagar", ["মধ্যনগর"], "madhyanagar")],
}
# Sylhet Metropolitan Police thanas (smp.police.gov.bd: Kotwali Model, Jalalabad, Airport, Moglabazar, Shahparan, Dakshin Surma).
# Only Kotwali is matched in office names: জালালাবাদ and মোগলাবাজার are also union names (and Jalalabad Gas), শাহপরান names
# shrines and institutions, দক্ষিণ সুরমা is also the upazila, and 'এয়ারপোর্ট' the airport.
SYLHET_CITY_THANAS = {"কোতয়ালী": "Kotwali", "কোতোয়ালী": "Kotwali", "কোতোয়ালি": "Kotwali"}
# The Sylhet DC portal (sylhet.gov.bd and its *.sylhet.gov.bd sub-sites) sends only its leaf certificate (Let's Encrypt YR1).
# As for the Sectigo intermediates above, the CA-published intermediates (AIA 'CA Issuers' URLs: YR1, and Root YR cross-signed by
# ISRG Root X1) are added to the bundle for Sylhet runs; TLS verification stays on. Rajshahi runs keep the original bundle.
SYLHET_INTERMEDIATES = ["http://yr1.i.lencr.org/", "http://yr.i.lencr.org/"]
# Mymensingh Division names: Bangla -> English (district and upazila names as the seed spells them: Nokla, Sreebordi, Bokshiganj,
# Dewangonj, Mohongonj, Tarakanda …). District hosts verified by page title (Nov 2026: 'হোম | <জেলা> জেলা'); the 35 upazila portal
# subdomains are the seed's and were verified by their home-page titles ('হোম | <উপজেলা> উপজেলা'). The Bangla names are NFC-normalised
# here (ড়/য় are composition exclusions). The certificates of these hosts are Sectigo DV R36, whose intermediate is already above.
_MYM_UPAZILAS = {  # district -> [(english, bangla names/aliases..., portal subdomain)]
    "Mymensingh": [("Mymensingh Sadar", ["ময়মনসিংহ সদর"], "mymensinghsadar"), ("Muktagacha", ["মুক্তাগাছা"], "muktagacha"),
                   ("Fulbaria", ["ফুলবাড়ীয়া", "ফুলবাড়িয়া", "ফুলবাড়ীয়া"], "fulbaria"), ("Trishal", ["ত্রিশাল"], "trishal"),
                   ("Bhaluka", ["ভালুকা"], "bhaluka"), ("Gafargaon", ["গফরগাঁও"], "gafargaon"), ("Nandail", ["নান্দাইল"], "nandail"),
                   ("Iswarganj", ["ঈশ্বরগঞ্জ"], "iswarganj"), ("Gouripur", ["গৌরীপুর"], "gouripur"), ("Phulpur", ["ফুলপুর"], "phulpur"),
                   ("Tarakanda", ["তারাকান্দা"], "tarakanda"), ("Haluaghat", ["হালুয়াঘাট"], "haluaghat"),
                   ("Dhobaura", ["ধোবাউড়া", "ধোবাউরা"], "dhobaura")],
    "Jamalpur": [("Jamalpur Sadar", ["জামালপুর সদর"], "jamalpursadar"), ("Melandah", ["মেলান্দহ"], "melandah"),
                 ("Islampur", ["ইসলামপুর"], "islampur"), ("Dewangonj", ["দেওয়ানগঞ্জ"], "dewangonj"),
                 ("Sarishabari", ["সরিষাবাড়ী", "সরিষাবাড়ি"], "sarishabari"), ("Madarganj", ["মাদারগঞ্জ"], "madarganj"),
                 ("Bokshiganj", ["বকশীগঞ্জ", "বকশিগঞ্জ"], "bokshiganj")],
    "Sherpur": [("Sherpur Sadar", ["শেরপুর সদর"], "sherpursadar"), ("Nalitabari", ["নালিতাবাড়ী", "নালিতাবাড়ি"], "nalitabari"),
                ("Sreebordi", ["শ্রীবরদী"], "sreebordi"), ("Nokla", ["নকলা"], "nokla"), ("Jhenaigati", ["ঝিনাইগাতী"], "jhenaigati")],
    "Netrokona": [("Netrokona Sadar", ["নেত্রকোণা সদর", "নেত্রকোনা সদর"], "netrokonasadar"), ("Barhatta", ["বারহাট্টা"], "barhatta"),
                  ("Durgapur", ["দুর্গাপুর"], "durgapur"), ("Kendua", ["কেন্দুয়া"], "kendua"), ("Atpara", ["আটপাড়া"], "atpara"),
                  ("Madan", ["মদন"], "madan"), ("Khaliajuri", ["খালিয়াজুরী", "খালিয়াজুড়ি"], "khaliajuri"),
                  ("Kalmakanda", ["কলমাকান্দা"], "kalmakanda"), ("Mohongonj", ["মোহনগঞ্জ"], "mohongonj"),
                  ("Purbadhala", ["পূর্বধলা"], "purbadhala")],
}
MYMENSINGH_UPAZILAS = {d: [(en, list(dict.fromkeys(unicodedata.normalize("NFC", b) for b in bns)), sub) for en, bns, sub in ups]
                       for d, ups in _MYM_UPAZILAS.items()}
MYMENSINGH_DISTRICTS = {unicodedata.normalize("NFC", k): v for k, v in
                        {"ময়মনসিংহ": "Mymensingh", "জামালপুর": "Jamalpur", "শেরপুর": "Sherpur", "নেত্রকোণা": "Netrokona"}.items()}
MYMENSINGH_DISTRICT_HOSTS = {"Mymensingh": "mymensingh.gov.bd", "Jamalpur": "jamalpur.gov.bd", "Sherpur": "sherpur.gov.bd",
                             "Netrokona": "netrokona.gov.bd"}
# No Mymensingh Metropolitan Police: police.gov.bd lists eight metropolitan units (DMP, CMP, BMP, KMP, RMP, SMP, RPMP, GMP) and its
# Mymensingh Range page counts Kotwali among Mymensingh District's police stations. No office name is mapped to a metro thana.
MYMENSINGH_CITY_THANAS = {}

# --- national-portal police sites (Rangpur Range and later divisions) -------------------------------------
# District police portals police.<district>.gov.bd and thana portals police.<upazila>.<district>.gov.bd (2026 framework).
# Contacts kept: office landlines (fixed-line numbers), *.gov.bd e-mails and police official mobiles (01320-xxxxxx series,
# and the older 01713-37xxxx/-38xxxx police CUG series) of the office head's post. Personal e-mails (gmail etc.), other mobiles
# and officers' names are never copied.
OFFICIAL_MOBILE = re.compile(r"^(01320\d{6}|017133[78]\d{4})$")


def widget(t, name="ContentViewerWidget"):
    i = t.find('data-widget_name="%s"' % name)
    if i < 0:
        return ""
    j = t.find('data-widget_name="', i + 30)
    return t[i:j if j > 0 else len(t)]


def page_title(t):
    m = re.search(r"<title>(.*?)</title>", t, re.S)
    return clean(m.group(1)) if m else ""


def officer_cards(t):
    """Officer cards (/pages/officers) -> list of dicts of the labelled fields."""
    t = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", " ", t, flags=re.S)
    lines = [nfc(re.sub(r"\s+", " ", _html.unescape(x))) for x in re.split(r"<[^>]+>", t)]
    lines = [x for x in lines if x]
    labels = ["নাম", "পদবি", "অফিস", "ওয়েব পোর্টল", "ইমেইল", "ফোন (অফিস)", "ইন্টারকম", "কক্ষ নম্বর", "মোবাইল", "ফ্যাক্স",
              "যোগদানের তারিখ", "ব্যাচ (বিসিএস)"]
    cards, cur, key = [], None, None
    for x in lines:
        if x == "নাম":
            cur = {}
            cards.append(cur)
            key = "নাম"
            continue
        if cur is None:
            continue
        if x in labels:
            key = x
            continue
        if "ভিকার্ড" in x or x in ("•", "দেখুন"):
            key = None
            continue
        if key:
            cur[key] = (cur.get(key, "") + x) if key == "ইমেইল" else (cur.get(key, "") + " " + x).strip()
    return cards


def _digits(s):
    return re.sub(r"^\+?880", "0", re.sub(r"[^\d+]", "", asc(s or "")))


def landlines(*vals):
    out = []
    for v in vals:
        for p in re.split(r"[,/;]|\s{2,}", asc(v or "")):
            d = _digits(p)
            if re.match(r"^0[2-9]\d{5,}$", d):  # fixed line: 0 + area code; drops mobiles (01...) and dummies (000...)
                out.append(d)
    return list(dict.fromkeys(out))


def official_mobiles(*vals):
    out = []
    for v in vals:
        for p in re.split(r"[,/;]", asc(v or "")):
            d = _digits(p)
            if OFFICIAL_MOBILE.match(d):
                out.append(d)
    return list(dict.fromkeys(out))


def gov_emails(*vals):
    out = []
    for v in vals:
        s = (v or "").replace(" ", "").replace("[at]", "@").lower()
        out += [m for m in re.findall(r"[a-z0-9._-]+@[a-z0-9.-]+\.[a-z]{2,}", s) if m.endswith(".gov.bd")]
    return list(dict.fromkeys(out))


def fetch_html(url):
    r = get(url)
    if r is None or r.status_code != 200:
        print("  unavailable:", url, getattr(r, "status_code", "no response"))
        return ""
    r.encoding = r.encoding or "utf-8"
    return r.text


def head_cards(base, home):
    """Officer cards of a portal: the PersonCard (office head) link on the home page, else /pages/officers."""
    m = re.search(r'data-widget_name="PersonCardWidget".*?href="(/pages/officers/[^"]+)"', home, re.S)
    url = base.rstrip("/") + (m.group(1) if m else "/pages/officers")
    t = fetch_html(url)
    cards = officer_cards(widget(t) or widget(t, "HybridBrowseWidget") or t)
    if not cards and m:  # stale PersonCard link -> officer list
        url = base.rstrip("/") + "/pages/officers"
        t = fetch_html(url)
        cards = officer_cards(widget(t) or widget(t, "HybridBrowseWidget") or t)
    return cards, url


def is_head(card, words):
    return any(w in (card.get("পদবি") or "") for w in words)


OC_WORDS = ("ইনচার্জ", "ইন-চার্জ", "ইন চার্জ")


def sp_office_row(key, dist, dist_bn, sid, host=None):
    """SP office from the office head's officer card on police.<district>.gov.bd (or the given host)."""
    base = "https://%s/" % (host or "police.%s.gov.bd" % dist.lower())
    home = fetch_html(base)
    if not home:
        return None
    cards, curl = head_cards(base, home)
    card = next((c for c in cards if is_head(c, ("পুলিশ সুপার",)) and "অতিরিক্ত" not in c.get("পদবি", "")), {})
    lls = landlines(card.get("ফোন (অফিস)"))
    mob = official_mobiles(card.get("মোবাইল"), card.get("ফোন (অফিস)"))
    em = gov_emails(card.get("ইমেইল"))
    fax = landlines(card.get("ফ্যাক্স"))
    return dict(source_key=key, source_id=sid, name_bn="পুলিশ সুপারের কার্যালয়, %s" % dist_bn, name_en="",
                category_key="government.sp_office", district_en=dist, phone="; ".join(lls + mob), website=base,
                email="; ".join(em), operator="%s জেলা পুলিশ" % dist_bn, ownership="public",
                extra_json=xj({"portal_title": page_title(home).replace("হোম | ", ""), "head_designation": card.get("পদবি"),
                               "sp_official_mobile": "; ".join(mob), "fax": "; ".join(fax)}),
                source_url=curl, notes="Contacts from the Superintendent of Police's officer card (office landline, police official mobile, "
                                       "official e-mail); officer's name not copied.")


def thana_name(title, upa_bn, dist_bn):
    """'হোম | মিঠাপুকুর থানা, রংপুর' -> 'মিঠাপুকুর থানা'; 'থানা, তেতুলিয়া, পঞ্চগড়' -> 'তেতুলিয়া থানা'."""
    t = re.sub(r"^হোম\s*\|\s*", "", title).strip(" ।")
    parts = [p.strip(" ।") for p in re.split(r"\s*,\s*", t) if p.strip(" ।")]
    name = None
    if len(parts) >= 2 and parts[0] in ("থানা", "উপজেলা থানা"):   # 'উপজেলা থানা, নগরকান্দা, ফরিদপুর' (Dhaka Division)
        name = parts[1] + " থানা"
    elif len(parts) >= 2 and parts[1] == "থানা":
        name = parts[0] + " থানা"
    elif parts and "থানা" in parts[0] and parts[0] not in ("থানা", "Thana"):   # a bare 'থানা' title carries no name
        name = parts[0]
    elif any(p.endswith("থানা") for p in parts[1:]):            # 'বাংলাদেশ পুলিশ, গজারিয়া থানা'
        name = next(p for p in parts[1:] if p.endswith("থানা"))
    if name and name.startswith("সদর "):
        name = dist_bn + " " + name
    return nfc(name) if name else None


def thana_row_from_portal(key, dist, dist_bn, upa_en, upa_bn, host, sid, listed_on=None):
    base = "https://%s/" % host
    home = fetch_html(base)
    if not home:
        return None, "portal %s did not respond" % host
    title = page_title(home)
    if title.startswith("Site is not available"):   # framework placeholder for a portal that is not set up
        return None, "portal %s: %r" % (host, title)
    name = thana_name(title, upa_bn, dist_bn)
    notes = []
    if not name:
        name = "%s থানা" % upa_bn
        notes.append("portal title %r carries no thana name; name composed from the upazila" % title)
    cards, curl = head_cards(base, home)
    oc = next((c for c in cards if is_head(c, OC_WORDS)), None)
    lls = []
    for c in ([oc] if oc else []) + cards:
        lls = landlines(c.get("ফোন (অফিস)"))
        if lls:
            break
    mob = official_mobiles(oc.get("মোবাইল"), oc.get("ফোন (অফিস)")) if oc else []
    em = gov_emails(*[c.get("ইমেইল") for c in ([oc] if oc else cards[:1])])
    if not oc:
        notes.append("no officer-in-charge card on the thana portal; phone = office landline only")
    notes.append("Contacts from the thana portal's officer cards (office landline, OC's police official mobile, *.gov.bd e-mail); "
                 "cards may be outdated; officers' names, personal e-mails and other mobiles not copied")
    return dict(source_key=key, source_id=sid, name_bn=name, name_en="", category_key="emergency.police_station", district_en=dist,
                upazila_en=upa_en or "", phone="; ".join(lls + mob[:1]), website=base, email="; ".join(em),
                operator="%s জেলা পুলিশ" % dist_bn, ownership="public",
                extra_json=xj({"portal_title": re.sub(r"^হোম\s*\|\s*", "", title), "oc_official_mobile": mob[0] if mob else "",
                               "office_landline": "; ".join(lls), "card_designation": oc.get("পদবি") if oc else "",
                               "listed_on": listed_on}),
                source_url=curl if cards else base, notes="; ".join(notes)), None


# --- Rangpur Range (the 7 districts other than Rangpur; Rangpur District is in RANGPUR_POLICE_2026) -----------------------
RANG_KEY = "RANG_RANGE_POLICE_PORTALS_2026"
RANG_DISTRICTS = {  # district -> extra pages on police.<district>.gov.bd
    "Panchagarh": {},
    "Dinajpur": {"glance": ("https://police.dinajpur.gov.bd/pages/static-pages/69771ccfc4774958d7c06a85",
                            [(r"থানাঃ[\s|]*([০-৯0-9]+)\s*টি", "police_stations", "thanas")])},
    "Lalmonirhat": {"glance": ("https://police.lalmonirhat.gov.bd/pages/static-pages/6977242cc4774958d7c09f62",
                               [(r"([০-৯0-9]+)\s*টি থানা", "police_stations", "thanas"), (r"([০-৯0-9]+)\s*টি সার্কেল", "police_circles", "circles"),
                                (r"([০-৯0-9]+)\s*টি পুলিশ ফ\S*ড়ি", "police_outposts", "outposts"),
                                (r"([০-৯0-9]+)\s*টি তদন্ত কেন্দ্র", "police_investigation_centres", "centres")])},
    "Nilphamari": {"thana_list": "https://police.nilphamari.gov.bd/pages/static-pages/69771cbac4774958d7c060ac"},
    "Gaibandha": {},
    "Thakurgaon": {"thana_list": "https://police.thakurgaon.gov.bd/pages/static-pages/697759cfc4774958d7c1d4ce"},
    "Kurigram": {"contact": "https://police.kurigram.gov.bd/pages/static-pages/69773952c4774958d7c10c9e",
                 "glance": ("https://police.kurigram.gov.bd/pages/static-pages/6977371ec4774958d7c0cf56",
                            [(r"থানা\s*([০-৯0-9]+)\s*টি", "police_stations", "thanas")])},
}
RANG_BN = {v: k for k, v in RANGPUR_DISTRICTS.items()}


def thana_list_links(url, raw_name):
    """Thana list page -> [(name_bn, police portal host)] for entries that link a portal; plus names without a link."""
    t = fetch_html(url)
    if not t:
        return [], []
    w = widget(t)
    save_raw(raw_name, "\n".join(content_text(t)))
    linked = []
    for href, txt in re.findall(r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>', w, re.S):
        host = urllib.parse.urlsplit(href).netloc.lower()
        name = clean(re.sub(r"\(.*", "", clean(txt)))
        if re.match(r"^[a-z0-9.-]+\.gov\.bd$", host) and "থানা" in name:
            linked.append((name, host))
    names = [clean(n) for n in re.findall(r"[০-৯0-9]+\s*[।.)]?\s*([^০-৯0-9()।.]+?থানা)", " ".join(content_text(t)))]
    return linked, names


def main_rangpur():
    places, facts, missing = [], [], []
    for dist, cfg in RANG_DISTRICTS.items():
        dbn = RANG_BN[dist]
        sp = sp_office_row(RANG_KEY, dist, dbn, "rangepol-sp-%s" % dist.lower())
        if sp:
            places.append(sp)
        else:
            missing.append("%s: police.%s.gov.bd" % (dist, dist.lower()))
        ups = {en: (bns[0], sub) for en, bns, sub in RANGPUR_UPAZILAS[dist]}
        bn2en = {bn: en for en, bns, sub in RANGPUR_UPAZILAS[dist] for bn in bns}
        if "glance" in cfg:
            url, pats = cfg["glance"]
            t = fetch_html(url)
            if t:
                txt = " ".join(content_text(t))
                for pat, fact, unit in pats:
                    m = re.search(pat, txt)
                    if m:
                        facts.append(dict(entity_level="district", entity_name_en=dist, district_en=dist, fact=fact, value=int(asc(m.group(1))),
                                          unit=unit, basis="reported", year=2026, source_key=RANG_KEY, source_url=url,
                                          notes="District police 'এক নজরে' page: " + m.group(0)))
        if "contact" in cfg:  # Kurigram: one table with the SP, every OC, outposts and the control room
            url = cfg["contact"]
            t = fetch_html(url)
            if not t:
                missing.append("%s: %s" % (dist, url))
                continue
            save_raw("%s_police_contact.txt" % dist.lower(), "\n".join(content_text(t)))
            n = 0
            for row in [r for tb in tables(t) for r in tb if len(r) >= 3]:
                label = row[1]
                office, mob = landlines(*row[2:]), official_mobiles(*row[2:])
                m = re.match(r"ওসি,\s*(.+?থানা)$", label)
                if m:
                    n += 1
                    name = nfc(m.group(1))
                    base = name.replace(" থানা", "")
                    upa = bn2en.get(base) or ("Kurigram Sadar" if base == "কুড়িগ্রাম" else
                                              "Bhurungamari" if base == "ভুরাঙ্গামারী" else "")
                    places.append(dict(source_key=RANG_KEY, source_id="rangepol-%s-%d" % (dist.lower(), n), name_bn=name, name_en="",
                                       category_key="emergency.police_station", district_en=dist, upazila_en=upa,
                                       phone="; ".join(office + mob), operator="%s জেলা পুলিশ" % dbn, ownership="public",
                                       extra_json=xj({"oc_official_mobile": "; ".join(mob), "label_in_source": label}), source_url=url,
                                       notes="phone = OC official mobile as published by the district police" +
                                             ("" if upa else "; thana is not an upazila (upazila_en empty)") +
                                             ("; source spells it 'ভুরাঙ্গামারী'" if base == "ভুরাঙ্গামারী" else "")))
                elif re.search(r"ফাঁড়ি|তদন্ত কেন্দ্র", label):
                    places.append(dict(source_key=RANG_KEY, source_id="rangepol-%s-post-%d" % (dist.lower(), sum(1 for x in places if x["category_key"] == "emergency.police_outpost" and x["district_en"] == dist) + 1),
                                       name_bn="%s, %s" % (nfc(re.sub(r"^আইসি\s*[,(]\s*", "", label).rstrip(")")), dbn), name_en="",
                                       category_key="emergency.police_outpost", district_en=dist, phone="; ".join(office + mob),
                                       operator="%s জেলা পুলিশ" % dbn, ownership="public", extra_json=xj({"label_in_source": label}),
                                       source_url=url, notes="Police outpost / investigation centre; name taken from the 'আইসি' (in-charge) row"))
                elif "কন্ট্রোল" in label:
                    places.append(dict(source_key=RANG_KEY, source_id="rangepol-control-%s" % dist.lower(),
                                       name_bn="পুলিশ কন্ট্রোল রুম, %s" % dbn, name_en="", category_key="emergency", district_en=dist,
                                       phone="; ".join(office + mob), operator="%s জেলা পুলিশ" % dbn, ownership="public",
                                       extra_json=xj({"label_in_source": label}), source_url=url,
                                       notes="Name composed from the 'পুলিশ কন্ট্রোলরুম' row and the district"))
            facts.append(dict(entity_level="district", entity_name_en=dist, district_en=dist, fact="police_stations", value=n, unit="thanas",
                              basis="listed", year=2026, source_key=RANG_KEY, source_url=url,
                              notes="Counted from OC rows of the district police contact table"))
            continue
        # other districts: one police portal per thana (police.<upazila>.<district>.gov.bd), plus thanas linked from a list page
        hosts = [(en, ups[en][0], "police.%s.%s.gov.bd" % (ups[en][1], dist.lower()), None) for en in ups]
        if "thana_list" in cfg:
            linked, names = thana_list_links(cfg["thana_list"], "%s_police_thana_list.txt" % dist.lower())
            have = {h for _, _, h, _ in hosts}
            for name, host in linked:
                host = re.sub(r"^www\.", "", host)
                if host not in have:
                    hosts.append(("", name.replace(" থানা", ""), host, cfg["thana_list"]))
                    have.add(host)
            if names:
                facts.append(dict(entity_level="district", entity_name_en=dist, district_en=dist, fact="police_stations", value=len(names),
                                  unit="thanas", basis="listed", year=2026, source_key=RANG_KEY, source_url=cfg["thana_list"],
                                  notes="থানাসমূহ: " + ", ".join(names)))
        for i, (en, bn, host, listed_on) in enumerate(hosts, 1):
            rec, err = thana_row_from_portal(RANG_KEY, dist, dbn, en, bn, host, "rangepol-%s-%d" % (dist.lower(), i),
                                             listed_on or cfg.get("thana_list"))
            if rec:
                if not en:
                    rec["notes"] += "; thana is not an upazila (upazila_en empty)"
                places.append(rec)
            else:
                missing.append("%s: %s" % (dist, err))
    write_csv("places.csv", PLACE_COLS, places)
    write_csv("facts.csv", FACT_COLS, facts)
    if missing:
        print("unavailable:", missing)
    urls = ["https://police.%s.gov.bd/" % d.lower() for d in RANG_DISTRICTS] + \
           [v for cfg in RANG_DISTRICTS.values() for k, v in cfg.items() if k in ("contact", "thana_list")] + \
           [cfg["glance"][0] for cfg in RANG_DISTRICTS.values() if "glance" in cfg]
    write_manifest(dict(
        key=RANG_KEY, division="rangpur", kind="range_police",
        name="District police portals of Rangpur Range (Panchagarh, Dinajpur, Lalmonirhat, Nilphamari, Gaibandha, Thakurgaon, Kurigram)",
        organization="Bangladesh Police — district police units of Rangpur Range", source_type="government_portal", trust_level=4,
        urls=urls + ["https://police.<upazila>.<district>.gov.bd/"], accessed=__import__("datetime").date.today().isoformat(),
        publication_date=None, license=None, license_url=None,
        attribution="District and thana police portals (police.<district>.gov.bd, police.<upazila>.<district>.gov.bd)",
        notes="No licence stated. SP offices from the Superintendent's officer card; thanas from each thana's own portal officer "
              "cards (office landline, OC's police official mobile, *.gov.bd e-mail) except Kurigram, whose district contact table "
              "lists every OC. Personal e-mails, other mobiles and officers' names are not copied. Rangpur District is in "
              "RANGPUR_POLICE_2026." + (" Unavailable this run: " + "; ".join(missing) if missing else "")),
        ["places.csv", "facts.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


# --- Dhaka Range (the 12 districts other than Dhaka; Dhaka District is in DHAKA_POLICE_2026) --------------------------------
DHK_KEY = "DHK_RANGE_POLICE_PORTALS_2026"
_UNITS = [(r"\|\s*থানা\s*\|\s*([০-৯0-9]+)", "police_stations", "thanas"), (r"\|\s*সার্কেল\s*\|\s*([০-৯0-9]+)", "police_circles", "circles"),
          (r"\|\s*পুলিশ তদন্ত কেন্দ্র\s*\|\s*([০-৯0-9]+)", "police_investigation_centres", "centres"),
          (r"\|\s*পুলিশ ফাঁড়ি\s*\|\s*([০-৯0-9]+)", "police_outposts", "outposts")]
DHK_DISTRICTS = {  # district -> extra pages on police.<district>.gov.bd; host_override: upazila -> thana portal host
    "Narsingdi": {}, "Shariatpur": {}, "Tangail": {}, "Manikganj": {}, "Munshiganj": {}, "Rajbari": {}, "Madaripur": {},
    "Gopalganj": {}, "Faridpur": {},
    "Gazipur": {"thana_list": "https://police.gazipur.gov.bd/pages/static-pages/6995c8bb35ce18e1c07a52a1",
                "host_override": {"Gazipur Sadar": "joydebpurpolice.sadar.gazipur.gov.bd"}},
    "Narayanganj": {"glance": ("https://police.narayanganj.gov.bd/pages/static-pages/at-a-glance-f2b8a1-6995aa7435ce18e1c07927f3",
                               [(r"([০-৯0-9]+)টি থানা", "police_stations", "thanas"), (r"([০-৯0-9]+)টি ফাড়িঁ", "police_outposts", "outposts"),
                                (r"([০-৯0-9]+)টি তদন্ত কেন্দ্র", "police_investigation_centres", "centres"),
                                (r"([০-৯0-9]+)টি সার্কেল", "police_circles", "circles")])},
    "Kishoreganj": {"glance": ("https://police.kishoreganj.gov.bd/pages/static-pages/6995de8c35ce18e1c07aed1e", _UNITS)},
}
DHK_BN = {v: k for k, v in DHAKA_DISTRICTS.items()}


def main_dhaka():
    places, facts, missing = [], [], []
    for dist, cfg in DHK_DISTRICTS.items():
        dbn = DHK_BN[dist]
        sp = sp_office_row(DHK_KEY, dist, dbn, "rangepol-sp-%s" % dist.lower())
        if sp:
            places.append(sp)
        else:
            missing.append("%s: police.%s.gov.bd" % (dist, dist.lower()))
        if "glance" in cfg:
            url, pats = cfg["glance"]
            t = fetch_html(url)
            if t:
                txt = " ".join(content_text(t))
                for pat, fact, unit in pats:
                    m = re.search(pat, txt)
                    if m:
                        facts.append(dict(entity_level="district", entity_name_en=dist, district_en=dist, fact=fact, value=int(asc(m.group(1))),
                                          unit=unit, basis="reported", year=2026, source_key=DHK_KEY, source_url=url,
                                          notes="District police page: " + re.sub(r"\s+", " ", m.group(0)).strip(" |")))
        over = cfg.get("host_override", {})
        hosts = [(en, bns[0], over.get(en) or "police.%s.%s.gov.bd" % (sub, dist.lower()), None) for en, bns, sub in DHAKA_UPAZILAS[dist]]
        if "thana_list" in cfg:
            linked, names = thana_list_links(cfg["thana_list"], "%s_police_thana_list.txt" % dist.lower())
            have = {h for _, _, h, _ in hosts}
            for name, host in linked:
                host = re.sub(r"^www\.", "", host)
                if host not in have:
                    hosts.append(("", name.replace(" থানা", ""), host, cfg["thana_list"]))
                    have.add(host)
            if names:
                facts.append(dict(entity_level="district", entity_name_en=dist, district_en=dist, fact="police_stations", value=len(names),
                                  unit="thanas", basis="listed", year=2026, source_key=DHK_KEY, source_url=cfg["thana_list"],
                                  notes="থানাসমূহ: " + ", ".join(names) + " (district police; the Gazipur Metropolitan Police thanas are "
                                        "in GAZIPUR_METRO_POLICE_THANAS_2026)"))
        for i, (en, bn, host, listed_on) in enumerate(hosts, 1):
            rec, err = thana_row_from_portal(DHK_KEY, dist, dbn, en, bn, host, "rangepol-%s-%d" % (dist.lower(), i),
                                             listed_on or cfg.get("thana_list"))
            if rec:
                if not en:
                    rec["notes"] += "; thana is not an upazila (upazila_en empty)"
                places.append(rec)
            else:
                missing.append("%s: %s" % (dist, err))
    write_csv("places.csv", PLACE_COLS, places)
    write_csv("facts.csv", FACT_COLS, facts)
    if missing:
        print("unavailable:", missing)
    urls = ["https://police.%s.gov.bd/" % d.lower() for d in DHK_DISTRICTS] + \
           [v for cfg in DHK_DISTRICTS.values() for k, v in cfg.items() if k == "thana_list"] + \
           [cfg["glance"][0] for cfg in DHK_DISTRICTS.values() if "glance" in cfg]
    write_manifest(dict(
        key=DHK_KEY, division="dhaka", kind="range_police",
        name="District police portals of Dhaka Range (%s)" % ", ".join(DHK_DISTRICTS),
        organization="Bangladesh Police — district police units of Dhaka Range", source_type="government_portal", trust_level=4,
        urls=urls + ["https://police.<upazila>.<district>.gov.bd/"], accessed=__import__("datetime").date.today().isoformat(),
        publication_date=None, license=None, license_url=None,
        attribution="District and thana police portals (police.<district>.gov.bd, police.<upazila>.<district>.gov.bd)",
        notes="No licence stated. SP offices from the Superintendent's officer card; thanas from each thana's own portal officer "
              "cards (office landline, OC's police official mobile, *.gov.bd e-mail). Personal e-mails, other mobiles and officers' "
              "names are not copied. Dhaka District is in DHAKA_POLICE_2026; Gazipur Metropolitan Police thanas are in "
              "GAZIPUR_METRO_POLICE_THANAS_2026." + (" Unavailable this run: " + "; ".join(missing) if missing else "")),
        ["places.csv", "facts.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))

# --- Chattogram Range (the 10 districts other than Chattogram; Chattogram District is in CHATTOGRAM_POLICE_2026) -------------
CTG_KEY = "CTG_RANGE_POLICE_PORTALS_2026"
CTG_DISTRICTS = ["Cumilla", "Feni", "Brahmanbaria", "Rangamati", "Noakhali", "Chandpur", "Lakshmipur", "Cox's Bazar", "Khagrachhari",
                 "Bandarban"]
CTG_BN = {v: k for k, v in CHATTOGRAM_DISTRICTS.items()}
CTG_RANGE_DIG = "https://dig.chittagongdiv.gov.bd/"   # Range DIG's office, Chattogram Range (no district/thana list published)


def ctg_police_host(dist):
    """police.<district host>: police.comilla.gov.bd, police.coxsbazar.gov.bd, police.feni.gov.bd …"""
    return "police." + CHATTOGRAM_DISTRICT_HOSTS[dist]


def main_chattogram():
    places, facts, missing = [], [], []
    for dist in CTG_DISTRICTS:
        dbn, dhost = CTG_BN[dist], CHATTOGRAM_DISTRICT_HOSTS[dist]
        slug = re.sub(r"[^a-z]", "", dist.lower())
        sp = sp_office_row(CTG_KEY, dist, dbn, "rangepol-sp-%s" % slug, host=ctg_police_host(dist))
        if sp:
            places.append(sp)
        else:
            missing.append("%s: %s" % (dist, ctg_police_host(dist)))
        for i, (en, bns, sub) in enumerate(CHATTOGRAM_UPAZILAS[dist], 1):
            rec, err = thana_row_from_portal(CTG_KEY, dist, dbn, en, bns[0], "police.%s.%s" % (sub, dhost), "rangepol-%s-%d" % (slug, i))
            if rec:
                if rec["name_bn"].startswith("বাংলাদেশ পুলিশ "):   # 'বাংলাদেশ পুলিশ লংগদু থানা'
                    rec["name_bn"] = rec["name_bn"][len("বাংলাদেশ পুলিশ "):]
                if rec["name_bn"] == "মডেল থানা":   # title 'মডেল থানা, টেকনাফ, কক্সবাজার'
                    rec["name_bn"] = "%s মডেল থানা" % bns[0]
                    rec["notes"] += "; portal title names no thana ('মডেল থানা, …'); name composed from the upazila"
                places.append(rec)
            else:
                missing.append("%s: %s" % (dist, err))
    write_csv("places.csv", PLACE_COLS, places)
    write_csv("facts.csv", FACT_COLS, facts)
    if missing:
        print("unavailable:", missing)
    write_manifest(dict(
        key=CTG_KEY, division="chattogram", kind="range_police",
        name="District police portals of Chattogram Range (%s)" % ", ".join(CTG_DISTRICTS),
        organization="Bangladesh Police — district police units of Chattogram Range", source_type="government_portal", trust_level=4,
        urls=["https://%s/" % ctg_police_host(d) for d in CTG_DISTRICTS] + ["https://police.<upazila>.<district>.gov.bd/", CTG_RANGE_DIG],
        accessed=__import__("datetime").date.today().isoformat(), publication_date=None, license=None, license_url=None,
        attribution="District and thana police portals (police.<district>.gov.bd, police.<upazila>.<district>.gov.bd)",
        notes="No licence stated. SP offices from the Superintendent's officer card; thanas from each upazila's thana portal officer "
              "cards (office landline, OC's police official mobile, *.gov.bd e-mail). Personal e-mails, other mobiles and officers' "
              "names are not copied. Chattogram Range (Range DIG's office, dig.chittagongdiv.gov.bd) covers the 11 districts of the "
              "division; Chattogram District is in CHATTOGRAM_POLICE_2026 and Chattogram city's CMP thanas in "
              "CHATTOGRAM_METRO_POLICE_THANAS_2026. Thanas that are not upazilas have no portal here."
              + (" Unavailable this run: " + "; ".join(missing) if missing else "")),
        ["places.csv", "facts.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


# --- Khulna Range (the 9 districts other than Khulna; Khulna District is in KHULNA_POLICE_2026) --------------------------------
KHL_KEY = "KHL_RANGE_POLICE_PORTALS_2026"
KHL_DISTRICTS = ["Jashore", "Satkhira", "Meherpur", "Narail", "Chuadanga", "Kushtia", "Magura", "Bagerhat", "Jhenaidah"]
KHL_BN = {v: k for k, v in KHULNA_DISTRICTS.items()}
KHL_RANGE_DIG = "https://policedig.khulnadiv.gov.bd/"   # Range DIG's office, Khulna Range (no district/thana list published)


def main_khulna():
    places, facts, missing = [], [], []
    for dist in KHL_DISTRICTS:
        dbn, dhost = KHL_BN[dist], KHULNA_DISTRICT_HOSTS[dist]
        slug = re.sub(r"[^a-z]", "", dist.lower())
        sp = sp_office_row(KHL_KEY, dist, dbn, "rangepol-sp-%s" % slug, host="police." + dhost)
        if sp and not sp["phone"] and not sp["email"]:   # home-page person card links another officer: use the officer list
            url = "https://police.%s/pages/officers" % dhost
            ht = fetch_html(url)
            cards = officer_cards(widget(ht) or widget(ht, "HybridBrowseWidget") or ht)
            card = next((c for c in cards if is_head(c, ("পুলিশ সুপার",)) and "অতিরিক্ত" not in c.get("পদবি", "")), None)
            if card:
                mob = official_mobiles(card.get("মোবাইল"), card.get("ফোন (অফিস)"))
                ex = json.loads(sp["extra_json"] or "{}")
                ex.update({"head_designation": card.get("পদবি"), "sp_official_mobile": "; ".join(mob),
                           "fax": "; ".join(landlines(card.get("ফ্যাক্স")))})
                sp.update(phone="; ".join(landlines(card.get("ফোন (অফিস)")) + mob), email="; ".join(gov_emails(card.get("ইমেইল"))),
                          source_url=url, extra_json=xj(ex))
                sp["notes"] += " The home page's person card links another officer; the SP card was taken from the officer list."
        if sp:
            places.append(sp)
        else:
            missing.append("%s: police.%s" % (dist, dhost))
        for i, (en, bns, sub) in enumerate(KHULNA_UPAZILAS[dist], 1):
            rec, err = thana_row_from_portal(KHL_KEY, dist, dbn, en, bns[0], "police.%s.%s" % (sub, dhost), "rangepol-%s-%d" % (slug, i))
            if rec:
                if rec["name_bn"].startswith("বাংলাদেশ পুলিশ "):
                    rec["name_bn"] = rec["name_bn"][len("বাংলাদেশ পুলিশ "):]
                if rec["name_bn"] in ("মডেল থানা", "থানা"):   # title 'মডেল থানা, <upazila>, <district>'
                    rec["name_bn"] = "%s %s" % (bns[0], rec["name_bn"])
                    rec["notes"] += "; portal title names no thana; name composed from the upazila"
                elif rec["name_bn"].startswith("থানা ") and "কার্যালয়" in rec["name_bn"]:   # 'থানা অফিসার ইনচার্জ এর কার্যালয়, …'
                    rec["notes"] += "; portal title %r names the OC's office; thana name composed from the upazila" % rec["name_bn"]
                    rec["name_bn"] = "%s থানা" % bns[0]
                places.append(rec)
            else:
                missing.append("%s: %s" % (dist, err))
    write_csv("places.csv", PLACE_COLS, places)
    write_csv("facts.csv", FACT_COLS, facts)
    if missing:
        print("unavailable:", missing)
    write_manifest(dict(
        key=KHL_KEY, division="khulna", kind="range_police",
        name="District police portals of Khulna Range (%s)" % ", ".join(KHL_DISTRICTS),
        organization="Bangladesh Police — district police units of Khulna Range", source_type="government_portal", trust_level=4,
        urls=["https://police.%s/" % KHULNA_DISTRICT_HOSTS[d] for d in KHL_DISTRICTS] + ["https://police.<upazila>.<district>.gov.bd/", KHL_RANGE_DIG],
        accessed=__import__("datetime").date.today().isoformat(), publication_date=None, license=None, license_url=None,
        attribution="District and thana police portals (police.<district>.gov.bd, police.<upazila>.<district>.gov.bd)",
        notes="No licence stated. SP offices from the Superintendent's officer card; thanas from each upazila's thana portal officer "
              "cards (office landline, OC's police official mobile, *.gov.bd e-mail). Personal e-mails, other mobiles and officers' "
              "names are not copied. Khulna Range (Range DIG's office, policedig.khulnadiv.gov.bd) covers the 10 districts of the "
              "division; Khulna District is in KHULNA_POLICE_2026 and Khulna city's KMP thanas in KHULNA_METRO_POLICE_THANAS_2026. "
              "Jashore's police portals are under jessore.gov.bd (police.jashore.gov.bd serves the same site). Thanas that are not "
              "upazilas have no portal here." + (" Unavailable this run: " + "; ".join(missing) if missing else "")),
        ["places.csv", "facts.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


# --- Barishal Range (the 5 districts other than Barishal; Barishal District is in BARISHAL_POLICE_2026) ------------------------
BAR_KEY = "BAR_RANGE_POLICE_PORTALS_2026"
BAR_DISTRICTS = ["Jhalokathi", "Patuakhali", "Pirojpur", "Bhola", "Barguna"]
BAR_BN = {v: k for k, v in BARISHAL_DISTRICTS.items()}
BAR_RANGE_DIG = "https://policedig.barisaldiv.gov.bd/"   # Range DIG's office, Barishal Range (title 'উপ মহা পুলিশ পরিদর্শক এর কার্যালয়')


def main_barishal():
    """Same pattern as main_khulna: SP officer card per district + one thana portal per upazila."""
    places, facts, missing = [], [], []
    for dist in BAR_DISTRICTS:
        dbn, dhost = BAR_BN[dist], BARISHAL_DISTRICT_HOSTS[dist]
        slug = re.sub(r"[^a-z]", "", dist.lower())
        sp = sp_office_row(BAR_KEY, dist, dbn, "rangepol-sp-%s" % slug, host="police." + dhost)
        if sp and not sp["phone"] and not sp["email"]:   # home-page person card links another officer: use the officer list
            url = "https://police.%s/pages/officers" % dhost
            ht = fetch_html(url)
            cards = officer_cards(widget(ht) or widget(ht, "HybridBrowseWidget") or ht)
            card = next((c for c in cards if is_head(c, ("পুলিশ সুপার",)) and "অতিরিক্ত" not in c.get("পদবি", "")), None)
            if card:
                mob = official_mobiles(card.get("মোবাইল"), card.get("ফোন (অফিস)"))
                ex = json.loads(sp["extra_json"] or "{}")
                ex.update({"head_designation": card.get("পদবি"), "sp_official_mobile": "; ".join(mob),
                           "fax": "; ".join(landlines(card.get("ফ্যাক্স")))})
                sp.update(phone="; ".join(landlines(card.get("ফোন (অফিস)")) + mob), email="; ".join(gov_emails(card.get("ইমেইল"))),
                          source_url=url, extra_json=xj(ex))
                sp["notes"] += " The home page's person card links another officer; the SP card was taken from the officer list."
        if sp:
            places.append(sp)
        else:
            missing.append("%s: police.%s" % (dist, dhost))
        for i, (en, bns, sub) in enumerate(BARISHAL_UPAZILAS[dist], 1):
            rec, err = thana_row_from_portal(BAR_KEY, dist, dbn, en, bns[0], "police.%s.%s" % (sub, dhost), "rangepol-%s-%d" % (slug, i))
            if rec:
                if rec["name_bn"].startswith("বাংলাদেশ পুলিশ "):
                    rec["name_bn"] = rec["name_bn"][len("বাংলাদেশ পুলিশ "):]
                if rec["name_bn"] in ("মডেল থানা", "থানা"):   # title 'মডেল থানা, <upazila>, <district>'
                    rec["name_bn"] = "%s %s" % (bns[0], rec["name_bn"])
                    rec["notes"] += "; portal title names no thana; name composed from the upazila"
                elif rec["name_bn"].startswith("থানা ") and "কার্যালয়" in rec["name_bn"]:   # 'থানা অফিসার ইনচার্জ এর কার্যালয়, …'
                    rec["notes"] += "; portal title %r names the OC's office; thana name composed from the upazila" % rec["name_bn"]
                    rec["name_bn"] = "%s থানা" % bns[0]
                places.append(rec)
            else:
                missing.append("%s: %s" % (dist, err))
    write_csv("places.csv", PLACE_COLS, places)
    write_csv("facts.csv", FACT_COLS, facts)
    if missing:
        print("unavailable:", missing)
    write_manifest(dict(
        key=BAR_KEY, division="barishal", kind="range_police",
        name="District police portals of Barishal Range (%s)" % ", ".join(BAR_DISTRICTS),
        organization="Bangladesh Police — district police units of Barishal Range", source_type="government_portal", trust_level=4,
        urls=["https://police.%s/" % BARISHAL_DISTRICT_HOSTS[d] for d in BAR_DISTRICTS] + ["https://police.<upazila>.<district>.gov.bd/", BAR_RANGE_DIG],
        accessed=__import__("datetime").date.today().isoformat(), publication_date=None, license=None, license_url=None,
        attribution="District and thana police portals (police.<district>.gov.bd, police.<upazila>.<district>.gov.bd)",
        notes="No licence stated. SP offices from the Superintendent's officer card; thanas from each upazila's thana portal officer "
              "cards (office landline, OC's police official mobile, *.gov.bd e-mail). Personal e-mails, other mobiles and officers' "
              "names are not copied. Barishal Range (Range DIG's office, policedig.barisaldiv.gov.bd) covers the 6 districts of the "
              "division; Barishal District is in BARISHAL_POLICE_2026 and Barishal city's BMP thanas in BARISHAL_METRO_POLICE_THANAS_2026. "
              "Jhalokathi's police portals are under jhalakathi.gov.bd. Thanas that are not upazilas have no portal here."
              + (" Unavailable this run: " + "; ".join(missing) if missing else "")),
        ["places.csv", "facts.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


# --- Sylhet Range (the 3 districts other than Sylhet; Sylhet District is in SYLHET_POLICE_2026) ---------------------------------
SYL_KEY = "SYL_RANGE_POLICE_PORTALS_2026"
SYL_DISTRICTS = ["Moulvibazar", "Habiganj", "Sunamganj"]
SYL_BN = {v: k for k, v in SYLHET_DISTRICTS.items()}
SYL_RANGE_DIG = "https://policedig.sylhetdiv.gov.bd/"   # Range DIG's office, Sylhet Range (title 'রেঞ্জ ডিআইজি’র কার্যালয়, সিলেট')


def main_sylhet():
    """Same pattern as main_barishal: SP officer card per district + one thana portal per upazila."""
    INTERMEDIATES.extend(u for u in SYLHET_INTERMEDIATES if u not in INTERMEDIATES)   # before the first request
    places, facts, missing = [], [], []
    for dist in SYL_DISTRICTS:
        dbn, dhost = SYL_BN[dist], SYLHET_DISTRICT_HOSTS[dist]
        slug = re.sub(r"[^a-z]", "", dist.lower())
        sp = sp_office_row(SYL_KEY, dist, dbn, "rangepol-sp-%s" % slug, host="police." + dhost)
        if sp and not sp["phone"] and not sp["email"]:   # home-page person card links another officer: use the officer list
            url = "https://police.%s/pages/officers" % dhost
            ht = fetch_html(url)
            cards = officer_cards(widget(ht) or widget(ht, "HybridBrowseWidget") or ht)
            card = next((c for c in cards if is_head(c, ("পুলিশ সুপার",)) and "অতিরিক্ত" not in c.get("পদবি", "")), None)
            if card:
                mob = official_mobiles(card.get("মোবাইল"), card.get("ফোন (অফিস)"))
                ex = json.loads(sp["extra_json"] or "{}")
                ex.update({"head_designation": card.get("পদবি"), "sp_official_mobile": "; ".join(mob),
                           "fax": "; ".join(landlines(card.get("ফ্যাক্স")))})
                sp.update(phone="; ".join(landlines(card.get("ফোন (অফিস)")) + mob), email="; ".join(gov_emails(card.get("ইমেইল"))),
                          source_url=url, extra_json=xj(ex))
                sp["notes"] += " The home page's person card links another officer; the SP card was taken from the officer list."
        if sp:
            places.append(sp)
        else:
            missing.append("%s: police.%s" % (dist, dhost))
        for i, (en, bns, sub) in enumerate(SYLHET_UPAZILAS[dist], 1):
            rec, err = thana_row_from_portal(SYL_KEY, dist, dbn, en, bns[0], "police.%s.%s" % (sub, dhost), "rangepol-%s-%d" % (slug, i))
            if rec:
                if rec["name_bn"].startswith("বাংলাদেশ পুলিশ "):
                    rec["name_bn"] = rec["name_bn"][len("বাংলাদেশ পুলিশ "):]
                if rec["name_bn"] in ("মডেল থানা", "থানা"):   # title 'মডেল থানা, <upazila>, <district>'
                    rec["name_bn"] = "%s %s" % (bns[0], rec["name_bn"])
                    rec["notes"] += "; portal title names no thana; name composed from the upazila"
                elif rec["name_bn"].startswith("থানা ") and "কার্যালয়" in rec["name_bn"]:   # 'থানা অফিসার ইনচার্জ এর কার্যালয়, …'
                    rec["notes"] += "; portal title %r names the OC's office; thana name composed from the upazila" % rec["name_bn"]
                    rec["name_bn"] = "%s থানা" % bns[0]
                places.append(rec)
            else:
                missing.append("%s: %s" % (dist, err))
    write_csv("places.csv", PLACE_COLS, places)
    write_csv("facts.csv", FACT_COLS, facts)
    if missing:
        print("unavailable:", missing)
    write_manifest(dict(
        key=SYL_KEY, division="sylhet", kind="range_police",
        name="District police portals of Sylhet Range (%s)" % ", ".join(SYL_DISTRICTS),
        organization="Bangladesh Police — district police units of Sylhet Range", source_type="government_portal", trust_level=4,
        urls=["https://police.%s/" % SYLHET_DISTRICT_HOSTS[d] for d in SYL_DISTRICTS] + ["https://police.<upazila>.<district>.gov.bd/", SYL_RANGE_DIG],
        accessed=__import__("datetime").date.today().isoformat(), publication_date=None, license=None, license_url=None,
        attribution="District and thana police portals (police.<district>.gov.bd, police.<upazila>.<district>.gov.bd)",
        notes="No licence stated. SP offices from the Superintendent's officer card; thanas from each upazila's thana portal officer "
              "cards (office landline, OC's police official mobile, *.gov.bd e-mail). Personal e-mails, other mobiles and officers' "
              "names are not copied. Sylhet Range (Range DIG's office, policedig.sylhetdiv.gov.bd) covers the 4 districts of the "
              "division; Sylhet District is in SYLHET_POLICE_2026 and Sylhet city's SMP thanas in SYLHET_METRO_POLICE_THANAS_2026. "
              "Thanas that are not upazilas have no portal here."
              + (" Unavailable this run: " + "; ".join(missing) if missing else "")),
        ["places.csv", "facts.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


# --- Mymensingh Range (the 3 districts other than Mymensingh; Mymensingh District is in MYMENSINGH_POLICE_2026) ----------------
MYM_KEY = "MYM_RANGE_POLICE_PORTALS_2026"
MYM_DISTRICTS = ["Jamalpur", "Sherpur", "Netrokona"]
MYM_BN = {v: k for k, v in MYMENSINGH_DISTRICTS.items()}
MYM_RANGE_DIG = "https://policedig.mymensinghdiv.gov.bd/"   # Range DIG's office, Mymensingh Range (title 'ডি.আই.জি, ময়মনসিংহ রেঞ্জ, ময়মনসিংহ বিভাগ')
MYM_RANGE_GLANCE = MYM_RANGE_DIG + "pages/static-pages/69708f01a31054345f15c55b"   # 'এক নজরে': the range = the division's 4 districts
# Jamalpur SP portal 'এক নজরে পুলিশ সুপারের কার্যালয়': table of posts with police official mobiles and police.gov.bd e-mails (no names);
# used for the SP office and thanas whose portal card gives no contact, and for the river-police thana and the control room.
MYM_CONTACT_TABLES = {"Jamalpur": "https://police.jamalpur.gov.bd/pages/static-pages/6970a1c4a31054345f161667"}
# Netrokona's 'থানা ও ফাঁড়ির ইনচার্জদের ফোন নাম্বার' (/pages/static-pages/6973bc9ec4774958d7bc0109) is a single image: not used.
# Bangladesh Police HQ's Mymensingh Range page (English): per-district police-station counts (undated; Sherpur's paragraph gives only
# the 1984 founding count, which is not used).
MYM_PHQ_RANGE = "https://www.police.gov.bd/en/mymensingh_range"
MYM_PHQ_FACTS = [("Jamalpur", r"Jamalpur District:.*?law and order service from (\d+) police stations: ([^.]*?), \d+ outposts"),
                 ("Netrokona", r"Netrokona District:.*?district police consists of (\d+) police stations.*?The police stations are ([^.]*)\.")]


def mym_phq_facts(key, dists):
    """police_stations facts (count + names as listed) from police.gov.bd's Mymensingh Range page; raw keeps the sentences used."""
    t = fetch_html(MYM_PHQ_RANGE)
    x = re.sub(r"\s+", " ", _html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"(?s)<script.*?</script>|<style.*?</style>", " ", t or ""))))
    facts, used = [], []
    for dist, pat in MYM_PHQ_FACTS:
        if dist not in dists:
            continue
        m = re.search(pat, x)
        if not m:
            print("police.gov.bd: no station count for", dist)
            continue
        used.append("%s District: %s police stations: %s" % (dist, m.group(1), m.group(2).strip()))   # not the descriptive prose
        facts.append(dict(entity_level="district", entity_name_en=dist, district_en=dist, fact="police_stations", value=int(m.group(1)),
                          unit="thanas", basis="reported", year="", source_key=key, source_url=MYM_PHQ_RANGE,
                          notes="police.gov.bd Mymensingh Range page (undated): %s police stations: %s" % (m.group(1), m.group(2).strip())))
    if used:
        save_raw("police_gov_bd_mymensingh_range.txt", "Source: %s (sentences used)\n" % MYM_PHQ_RANGE + "\n".join(used) + "\n")
    return facts


def mym_contact_table(dist):
    """[(post, official mobiles, e-mails)] from a district's posts table (serial | post | mobile | e-mail)."""
    url = MYM_CONTACT_TABLES.get(dist)
    t = fetch_html(url) if url else ""
    out = []
    for tb in tables(widget(t) or t):
        for r in tb:
            if len(r) >= 4 and re.match(r"^[০-৯0-9]+$", r[0]):
                out.append((nfc(r[1]), official_mobiles(r[2]), gov_emails(r[3])))
    if out:
        save_raw("%s_police_posts.txt" % dist.lower(), "Source: %s (posts, police official mobiles, police.gov.bd e-mails; no names)\n"
                 % url + "\n".join("%s | %s | %s" % (p, "; ".join(m), "; ".join(e)) for p, m, e in out) + "\n")
    return url, out


def main_mymensingh():
    """Same pattern as main_sylhet (SP officer card + one thana portal per upazila); gaps filled from a district's posts table."""
    places, facts, missing = [], [], []
    for dist in MYM_DISTRICTS:
        dbn, dhost = MYM_BN[dist], MYMENSINGH_DISTRICT_HOSTS[dist]
        slug = re.sub(r"[^a-z]", "", dist.lower())
        turl, posts = mym_contact_table(dist)
        sp = sp_office_row(MYM_KEY, dist, dbn, "rangepol-sp-%s" % slug, host="police." + dhost)
        if sp and not sp["phone"] and not sp["email"]:   # home-page person card links another officer: use the officer list
            url = "https://police.%s/pages/officers" % dhost
            ht = fetch_html(url)
            cards = officer_cards(widget(ht) or widget(ht, "HybridBrowseWidget") or ht)
            card = next((c for c in cards if is_head(c, ("পুলিশ সুপার",)) and "অতিরিক্ত" not in c.get("পদবি", "")), None)
            if card:
                mob = official_mobiles(card.get("মোবাইল"), card.get("ফোন (অফিস)"))
                ex = json.loads(sp["extra_json"] or "{}")
                ex.update({"head_designation": card.get("পদবি"), "sp_official_mobile": "; ".join(mob),
                           "fax": "; ".join(landlines(card.get("ফ্যাক্স")))})
                sp.update(phone="; ".join(landlines(card.get("ফোন (অফিস)")) + mob), email="; ".join(gov_emails(card.get("ইমেইল"))),
                          source_url=url, extra_json=xj(ex))
                sp["notes"] += " The home page's person card links another officer; the SP card was taken from the officer list."
        if sp:
            row = next((x for x in posts if x[0] == "পুলিশ সুপার"), None)
            if row and not sp["phone"] and not sp["email"]:
                sp.update(phone="; ".join(row[1]), email="; ".join(row[2]), source_url=turl)
                sp["notes"] += " No contact on the officer cards; SP official mobile and e-mail from the portal's posts table."
            places.append(sp)
        else:
            missing.append("%s: police.%s" % (dist, dhost))
        for i, (en, bns, sub) in enumerate(MYMENSINGH_UPAZILAS[dist], 1):
            rec, err = thana_row_from_portal(MYM_KEY, dist, dbn, en, bns[0], "police.%s.%s" % (sub, dhost), "rangepol-%s-%d" % (slug, i))
            if not rec:
                missing.append("%s: %s" % (dist, err))
                continue
            if rec["name_bn"].startswith("বাংলাদেশ পুলিশ "):
                rec["name_bn"] = rec["name_bn"][len("বাংলাদেশ পুলিশ "):]
            if rec["name_bn"] in ("মডেল থানা", "থানা"):
                rec["name_bn"] = "%s %s" % (bns[0], rec["name_bn"])
                rec["notes"] += "; portal title names no thana; name composed from the upazila"
            if not rec["phone"] or not rec["email"]:   # posts table row 'অফিসার-ইনচার্জ <thana> থানা'
                key = rec["name_bn"].replace(" মডেল", "").replace(" সদর", "")
                cands = {b.replace(" সদর", "") for b in bns + [key.replace(" থানা", "")]}
                hit = next((x for x in posts if x[0].startswith("অফিসার-ইনচার্জ") and any(
                    re.search(r"(?:^|\s)%s\s*থানা" % re.escape(c), x[0]) for c in cands)), None)
                if hit:
                    filled = []
                    if not rec["phone"] and hit[1]:
                        rec["phone"] = "; ".join(hit[1][:1]); filled.append("OC official mobile")
                    if not rec["email"] and hit[2]:
                        rec["email"] = "; ".join(hit[2]); filled.append("e-mail")
                    if filled:
                        ex = json.loads(rec["extra_json"] or "{}")
                        ex.update({"posts_table_row": hit[0], "contacts_from_posts_table": filled})
                        rec["extra_json"] = xj(ex)
                        rec["notes"] += "; %s from the SP portal's posts table (%s)" % (" and ".join(filled), turl)
            places.append(rec)
        for post, mob, em in posts:   # rows that are neither the SP nor an upazila thana
            if "নৌ থানা" in post:
                places.append(dict(source_key=MYM_KEY, source_id="rangepol-%s-river-%d" % (slug, sum(1 for q in places if "-river-" in q["source_id"]) + 1), category_key="emergency.police_station",
                                   name_bn=re.sub(r"^ওসি\s*", "", post), name_en="", district_en=dist, upazila_en="", phone="; ".join(mob[:1]),
                                   email="; ".join(em), website="", operator="%s জেলা পুলিশ" % dbn, ownership="public",
                                   extra_json=xj({"post_as_listed": post}), source_url=turl,
                                   notes="River-police thana listed on the SP portal's posts table (OC's official mobile); upazila not "
                                         "stated there; officers' names not listed."))
            elif post == "পুলিশ কন্ট্রোল রুম":
                places.append(dict(source_key=MYM_KEY, source_id="rangepol-%s-control" % slug, category_key="emergency",
                                   name_bn="পুলিশ কন্ট্রোল রুম, %s" % dbn, name_en="", district_en=dist, upazila_en="",
                                   phone="; ".join(mob), email="; ".join(em), website="", operator="%s জেলা পুলিশ" % dbn, ownership="public",
                                   extra_json=xj({"post_as_listed": post}), source_url=turl,
                                   notes="District police control room, from the SP portal's posts table (official mobile)."))
    facts += mym_phq_facts(MYM_KEY, MYM_DISTRICTS)
    write_csv("places.csv", PLACE_COLS, places)
    write_csv("facts.csv", FACT_COLS, facts)
    if missing:
        print("unavailable:", missing)
    write_manifest(dict(
        key=MYM_KEY, division="mymensingh", kind="range_police",
        name="District police portals of Mymensingh Range (%s)" % ", ".join(MYM_DISTRICTS),
        organization="Bangladesh Police — district police units of Mymensingh Range", source_type="government_portal", trust_level=4,
        urls=["https://police.%s/" % MYMENSINGH_DISTRICT_HOSTS[d] for d in MYM_DISTRICTS] + ["https://police.<upazila>.<district>.gov.bd/"]
             + list(MYM_CONTACT_TABLES.values()) + [MYM_RANGE_DIG, MYM_RANGE_GLANCE, MYM_PHQ_RANGE],
        accessed=__import__("datetime").date.today().isoformat(), publication_date=None, license=None, license_url=None,
        attribution="District and thana police portals (police.<district>.gov.bd, police.<upazila>.<district>.gov.bd)",
        notes="No licence stated. SP offices from the Superintendent's officer card; thanas from each upazila's thana portal officer "
              "cards (office landline, OC's police official mobile, *.gov.bd e-mail); for Jamalpur, missing thana contacts, the "
              "river-police thana and the control room from the SP portal's posts table (official mobiles and police.gov.bd e-mails, "
              "no names). Personal e-mails, other mobiles and officers' names are not copied. Mymensingh Range (Range DIG's office, "
              "policedig.mymensinghdiv.gov.bd; 'এক নজরে': formed by gazette of 12 Oct 2015 from the division's 4 districts) covers "
              "Mymensingh, Jamalpur, Sherpur and Netrokona; Mymensingh District is in MYMENSINGH_POLICE_2026. There is no "
              "metropolitan police in the division. Thanas that are not upazilas have no portal here; Netrokona's thana phone list "
              "is an image and is not used. Thana counts (Jamalpur 8 incl. the Bahadurabad river-police thana, Netrokona 10) from "
              "police.gov.bd's Mymensingh Range page (undated)." + (" Unavailable this run: " + "; ".join(missing) if missing else "")),
        ["places.csv", "facts.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


RANGES = {"rajshahi": dict(folder="raj_range_police_portals_2026"),
          "rangpur": dict(folder="rang_range_police_portals_2026", run=main_rangpur),
          "dhaka": dict(folder="dhk_range_police_portals_2026", run=main_dhaka),
          "chattogram": dict(folder="ctg_range_police_portals_2026", run=main_chattogram),
          "khulna": dict(folder="khl_range_police_portals_2026", run=main_khulna),
          "barishal": dict(folder="bar_range_police_portals_2026", run=main_barishal),
          "sylhet": dict(folder="syl_range_police_portals_2026", run=main_sylhet),
          "mymensingh": dict(folder="mym_range_police_portals_2026", run=main_mymensingh)}


def configure():
    global DIVISION, HERE, RAW
    DIVISION, out = parse_division_args({k: v["folder"] for k, v in RANGES.items()})
    HERE = Path(out)
    RAW = HERE / "raw"


if __name__ == "__main__":
    main()
