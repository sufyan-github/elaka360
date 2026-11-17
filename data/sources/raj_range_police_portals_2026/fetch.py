#!/usr/bin/env python3
"""Fetch SP-office / thana numbers from the district police portals of a police range (default Rajshahi Range, RAJ_RANGE_POLICE_PORTALS_2026).

Usage: python3 fetch.py [--division rangpur] [--out DIR]. The division's head district is covered by <division>_police_2026."""
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


def sp_office_row(key, dist, dist_bn, sid):
    """SP office from the office head's officer card on police.<district>.gov.bd."""
    base = "https://police.%s.gov.bd/" % dist.lower()
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
    if len(parts) >= 2 and parts[0] == "থানা":
        name = parts[1] + " থানা"
    elif len(parts) >= 2 and parts[1] == "থানা":
        name = parts[0] + " থানা"
    elif parts and "থানা" in parts[0]:
        name = parts[0]
    if name and name.startswith("সদর "):
        name = dist_bn + " " + name
    return nfc(name) if name else None


def thana_row_from_portal(key, dist, dist_bn, upa_en, upa_bn, host, sid, listed_on=None):
    base = "https://%s/" % host
    home = fetch_html(base)
    if not home:
        return None, "portal %s did not respond" % host
    title = page_title(home)
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


RANGES = {"rajshahi": dict(folder="raj_range_police_portals_2026"),
          "rangpur": dict(folder="rang_range_police_portals_2026", run=main_rangpur)}


def configure():
    global DIVISION, HERE, RAW
    DIVISION, out = parse_division_args({k: v["folder"] for k, v in RANGES.items()})
    HERE = Path(out)
    RAW = HERE / "raw"


if __name__ == "__main__":
    main()
