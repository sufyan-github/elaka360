#!/usr/bin/env python3
"""Fetch SP-office / thana numbers from the district police portals of Rajshahi Range (RAJ_RANGE_POLICE_PORTALS_2026)."""
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
        key=KEY, name="District police portals of Rajshahi Range (Natore, Naogaon, Chapainawabganj, Bogura, Joypurhat, Pabna, Sirajganj)",
        organization="Bangladesh Police — district police units of Rajshahi Range", source_type="government_portal", trust_level=4,
        urls=list(CONTACT.values()) + [URL_PABNA_THANAS], accessed=__import__("datetime").date.today().isoformat(),
        publication_date=None, license=None, license_url=None, attribution="District police portals (police.<district>.gov.bd)",
        notes="No licence stated. Institutional numbers only, no officer names. Only Pabna and Sirajganj publish per-thana numbers; "
              "Natore, Chapainawabganj, Bogura and Joypurhat publish SP-office contacts only; Naogaon's contact page returned 404 "
              + ("(this run: " + "; ".join(missing) + ")" if missing else "") + ". Rajshahi District is in RAJSHAHI_POLICE_2026."),
        ["places.csv", "facts.csv"] + sorted(f"raw/{p.name}" for p in RAW.glob("*.txt")))


if __name__ == "__main__":
    main()
