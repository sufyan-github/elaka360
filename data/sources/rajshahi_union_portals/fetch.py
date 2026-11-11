#!/usr/bin/env python3
"""Union Parishad portals of Rajshahi District (<name>up.rajshahi.gov.bd): the "এক নজরে" (at-a-glance) page of each union.

Usage: python3 -I fetch.py [--cache DIR]
The union list and portal links come from the district page (rajshahi.gov.bd ... 697f79bb...). For each union the
portal home page is fetched, the menu item "এক নজরে …" (not the land-office one) is followed and its label/value rows
are matched to a few facts (area, population, mouzas, villages, wards, households). The printed label and value are
kept in `notes`, so every number can be checked against the page. SKIP removes matches checked by hand and found wrong.
Phone numbers and e-mail addresses are redacted from notes and raw/*.txt.
"""
# ---------------------------------------------------------------------------
# shared helpers (identical block in each Rajshahi portal fetch.py)
# ---------------------------------------------------------------------------
import argparse, csv, hashlib, html, json, os, re, ssl, sys, tempfile, time, unicodedata
import urllib.robotparser
from urllib.parse import urljoin, urlparse
import requests

UA = "Elaka360-data-pipeline (research; contact via repository)"
HERE = os.path.dirname(os.path.abspath(__file__))
ACCESSED = time.strftime("%Y-%m-%d")
# Many *.gov.bd servers do not send the Sectigo intermediate certificate. We fetch it from the
# certificate's AIA URL and add it to the normal CA store; verification is never switched off.
AIA_INTERMEDIATES = ["http://crt.sectigo.com/SectigoPublicServerAuthenticationCADVR36.crt"]
_session = requests.Session()
_session.headers["User-Agent"] = UA
_last = {}
_robots = {}
_bundle = None
CACHE = None


def ca_bundle():
    global _bundle
    if _bundle:
        return _bundle
    try:
        import certifi
        base = certifi.where()
    except ImportError:
        base = ssl.get_default_verify_paths().cafile or "/etc/ssl/certs/ca-certificates.crt"
    pem = open(base, encoding="utf-8").read()
    for u in AIA_INTERMEDIATES:
        r = requests.get(u, headers={"User-Agent": UA}, timeout=30)
        r.raise_for_status()
        pem += "\n" + (r.text if r.content.startswith(b"-----BEGIN") else ssl.DER_cert_to_PEM_cert(r.content))
    f = tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False)
    f.write(pem)
    f.close()
    _bundle = f.name
    return _bundle


def _polite(host):
    dt = time.time() - _last.get(host, 0)
    if dt < 1.2:
        time.sleep(1.2 - dt)
    _last[host] = time.time()


def allowed(url):
    p = urlparse(url)
    root = f"{p.scheme}://{p.netloc}"
    if root not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            _polite(p.netloc)
            r = _session.get(root + "/robots.txt", timeout=30, verify=ca_bundle())
            rp.parse(r.text.splitlines() if r.status_code == 200 else [])
        except requests.RequestException:
            rp.parse([])
        _robots[root] = rp
    return _robots[root].can_fetch(UA, url)


def get(url, timeout=45):
    """GET with on-disk cache (optional), politeness and robots.txt. Returns text or raises."""
    key = hashlib.sha1(url.encode()).hexdigest()
    if CACHE:
        p = os.path.join(CACHE, key)
        if os.path.exists(p):
            return open(p, encoding="utf-8", errors="replace").read()
    if not allowed(url):
        raise RuntimeError(f"robots.txt disallows {url}")
    _polite(urlparse(url).netloc)
    r = _session.get(url, timeout=timeout, verify=ca_bundle())
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code} {url}")
    t = r.content.decode("utf-8", "replace")
    if CACHE:
        os.makedirs(CACHE, exist_ok=True)
        open(os.path.join(CACHE, key), "w", encoding="utf-8").write(t)
    return t


def nfc(s):
    return unicodedata.normalize("NFC", s or "")


def text(fragment):
    s = re.sub(r"<script.*?</script>|<style.*?</style>", "", fragment, flags=re.S)
    s = re.sub(r"<br\s*/?>|</p>|</tr>|</li>|</h\d>|</div>", "\n", s)
    s = re.sub(r"</td>|</th>", " | ", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("\xa0", " ").replace("‌", "")
    return nfc("\n".join(re.sub(r"[ \t]+", " ", l).strip() for l in s.split("\n") if l.strip()))


BN = "০১২৩৪৫৬৭৮৯"
BN_MONTHS = {"জানুয়ারি": 1, "জানুয়ারী": 1, "ফেব্রুয়ারি": 2, "ফেব্রুয়ারী": 2, "মার্চ": 3, "এপ্রিল": 4, "মে": 5,
             "জুন": 6, "জুলাই": 7, "আগস্ট": 8, "সেপ্টেম্বর": 9, "অক্টোবর": 10, "নভেম্বর": 11, "ডিসেম্বর": 12}


def asc(s):
    return "".join(str(BN.index(c)) if c in BN else c for c in (s or ""))


def page_date(upd):
    """'কনটেন্টটি শেষ হাল-নাগাদ করা হয়েছে: সোমবার, ৯ জুলাই, ২০১৮ এ ...' -> '2018-07-09'"""
    m = re.search(r"([০-৯0-9]{1,2})\s+(\S+),\s*([০-৯0-9]{4})", nfc(upd or ""))
    if not m:
        return ""
    d, mon, y = asc(m.group(1)), nfc(m.group(2)), asc(m.group(3))
    mon = {nfc(k): v for k, v in BN_MONTHS.items()}.get(mon)
    if not (d.isdigit() and y.isdigit() and mon):
        return ""
    return f"{int(y):04d}-{mon:02d}-{int(d):02d}"


def content(t):
    """Main content of an a2i National Portal page: dict(updated, date, title, html, text) or None."""
    i = t.find('data-widget_name="ContentViewerWidget"')
    if i < 0:
        return None
    seg = t[i:]
    j = seg.find("এই কনটেন্টটি শেয়ার")
    if j > 0:
        seg = seg[:j]
    m = re.search(r'content-update-block">\s*<p>\s*(.*?)</p>', seg, re.S)
    upd = nfc(html.unescape(m.group(1)).strip()) if m else ""
    m = re.search(r"<h2>(.*?)</h2>", seg, re.S)
    title = text(m.group(1)) if m else ""
    seg = re.sub(r'encoded-content="[^"]*"', "", seg)
    seg = seg[seg.find(">") + 1:]
    return dict(updated=upd, date=page_date(upd), title=title, html=seg, text=text(seg))


def links(fragment, base=""):
    out = []
    for h, x in re.findall(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', fragment, flags=re.S):
        h = html.unescape(h).strip()
        out.append((urljoin(base, h) if base else h, text(x)))
    return out


def clean_url(u):
    u = (u or "").strip().replace("http://http://", "http://").replace("https://http://", "http://")
    if not u:
        return ""
    p = urlparse(u if "://" in u else "http://" + u)
    return f"https://{p.netloc.lower()}/" if p.netloc else ""


def table_rows(fragment):
    rows = []
    for tr in re.findall(r"<tr.*?</tr>", fragment, flags=re.S):
        cells = [text(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.S)]
        rows.append(([c for c in cells], tr))
    return rows


def first_number(s, dot_thousands=True):
    """First number in s (Bangla or ASCII digits); returns (value_str, note)."""
    s = asc(s)
    m = re.search(r"\d[\d,\.]*", s)
    if not m:
        return "", ""
    raw = m.group(0).rstrip(".,")
    note = ""
    if not dot_thousands and re.fullmatch(r"\d+,\d{2}", raw):     # '৫৭,৪৯' / '18,73' = decimal comma
        return raw.replace(",", "."), f"'{raw}' read as decimal comma"
    if dot_thousands and re.fullmatch(r"\d{1,3}(\.\d{3})+", raw):          # '২২.৩২৯ জন' = 22,329 (dot used as thousands separator)
        note = f"'{raw}' read as thousands separator"
        raw = raw.replace(".", "")
    raw = raw.replace(",", "")
    return raw, note


def kv_pairs(c):
    """(label, value) pairs from tables and 'label : value' lines of a content block."""
    pairs = []
    for cells, _ in table_rows(c["html"]):
        cells = [x.strip(" |") for x in cells if x.strip(" |")]
        while cells and re.fullmatch(r"[০-৯0-9\.\)\(।]+", cells[0]):
            cells = cells[1:]                                  # drop serial-number cells
        if len(cells) >= 2:
            pairs.append((cells[0], " ".join(cells[1:])))
    for line in c["text"].split("\n"):
        m = re.match(r"^\s*(?:[০-৯0-9]+\s*[।\.\)]\s*)?([^:ঃ|=]{2,60}?)\s*[:ঃ=]\s*(.+)$", line)
        if m:
            pairs.append((m.group(1).strip(" -•"), m.group(2).strip()))
    return pairs


FACT_LABELS = [  # (fact, include regex on label, exclude regex on label, unit)
    ("area_km2", r"আয়তন", r"পৌর|পৌরসভা|জমি", "km2"),
    ("population", r"জনসংখ্যা|লোকসংখ্যা|লোক সংখ্যা|জনসংখ্যা", r"ঘনত্ব|বৃদ্ধি|হার|পুরুষ|মহিলা|ভোটার|পৌর|শিক্ষিত|উপজাতী|আদিবাসী|গ্রাম ভিত্তিক", "persons"),
    ("mouza_count", r"মৌজা", r"পৌর|নাম", "count"),
    ("village_count", r"গ্রাম", r"গুচ্ছ|আদর্শ|ভিত্তিক|পৌর|নাম|সংসদ|গ্রামীণ|গ্রাম পুলিশ|চৌকিদার", "count"),
    ("ward_count", r"ওয়ার্ড|ওযার্ড|ওয়াড|ওয়ার্ড", r"সদস্য|মেম্বার|কাউন্সিলর|নাম|পৌর|নং|ভিত্তিক", "count"),
    ("union_count", r"ইউনিয়ন", r"ভূমি|অফিস|পরিষদ ভবন|নাম|ডিজিটাল|তথ্য|কমপ্লেক্স", "count"),
    ("pourashava_count", r"পৌরসভা", r"ওয়ার্ড|মৌজা|নাম|আয়তন|জনসংখ্যা|হোল্ডিং", "count"),
    ("household_count", r"পরিবার সংখ্যা|পরিবারের সংখ্যা|মোট পরিবার|খানার সংখ্যা|খানা সংখ্যা|^\W*খানা\W*$|মোট খানা",
     r"পায়খানা|এতিম|ইয়াতিম|কসাই|কোষাই|আদিবাসী|কৃষক|পরিকল্পনা|কল্যাণ|উপজাতি", "households"),
]


def extract_facts(c):
    """Generic label matcher; returns list of dict(fact, value, unit, year, label, raw, note)."""
    out, seen = [], set()
    for label, value in kv_pairs(c):
        lab = nfc(label)
        for fact, inc, exc, unit in FACT_LABELS:
            if fact in seen or not re.search(inc, lab) or re.search(exc, lab):
                continue
            v, note = first_number(value, dot_thousands=(fact != "area_km2"))
            if not v:
                continue
            y = re.search(r"(?<![\d.,])(19|20)\d\d(?![\d.,])", asc(value))
            year = y.group(0) if y else ""
            if fact == "population" and re.search(r"মোট\s*(জনসংখ্যা|লোকসংখ্যা)?[\s:ঃ\-–\.]*[০-৯0-9]", value):
                tail = re.split(r"মোট\s*(?:জনসংখ্যা|লোকসংখ্যা)?[\s:ঃ\-–\.]*(?=[০-৯0-9])", value)[-1]
                v, note = first_number(tail)
                note = (note + "; " if note else "") + "took the figure after 'মোট' (total)"
            if fact == "area_km2":
                after = asc(value)[re.search(r"\d", asc(value)).start():][:40]
                if re.search(r"^[\d,\.\s]*(বর্গ\s*)?মাইল|^[\d,\.\s]*sq\.?\s*mile", after, re.I):
                    unit = "sq_miles"
                elif re.search(r"^[\d,\.\s]*(বর্গ\s*)?একর", after):
                    unit = "acres"
                elif re.search(r"^[\d,\.\s]*হেক্টর", after):
                    unit = "hectares"
                elif not re.search(r"^[\d,\.\s\(\)]*(বর্গ\s*কি|বগ\s*কি|বঃ\s*কি|ব\s*[:\.]\s*কি|ব\.কি|বর্গকি|কিঃ|কি\.\s*মি|কিলো|km|sq\s*km|SQKM|কিমি)", after, re.I):
                    unit = "unstated"
            seen.add(fact)
            out.append(dict(fact=fact, value=v, unit=unit, year=year, label=lab, raw=nfc(value)[:160], note=note))
    return out


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})


AREAS_H = ["level", "name_en", "name_bn", "parent_level", "parent_name_en", "parent_name_bn", "district_en", "upazila_en",
           "code", "code_scheme", "website", "lat", "lon", "source_key", "source_url", "notes"]
FACTS_H = ["entity_level", "entity_name_en", "district_en", "upazila_en", "code", "fact", "value", "unit", "basis", "year",
           "source_key", "source_url", "notes"]


def redact(s):
    """Remove phone numbers and e-mail addresses (many pages list officials' personal mobiles)."""
    s = re.sub(r"(?:\+?৮৮|\+?88)?[০0][১1][৩-৯3-9](?:[\s\-]?[০-৯0-9]){8}", "[phone]", s)
    s = re.sub(r"[\w.\-]+@[\w.\-]+\.\w+", "[email]", s)
    return s


def save_raw(name, url, c):
    os.makedirs(os.path.join(HERE, "raw"), exist_ok=True)
    with open(os.path.join(HERE, "raw", name), "w", encoding="utf-8") as f:
        f.write(f"URL: {url}\nUPDATED: {c['updated']}\nTITLE: {c['title']}\nACCESSED: {ACCESSED}\n\n{redact(c['text'])}\n")


def squash(s):
    return re.sub(r"[\s|]+", "", nfc(s))


def on_page(quote, c):
    return squash(quote) in squash(c["text"])


def update_manifest():
    p = os.path.join(HERE, "SOURCE.json")
    m = json.load(open(p, encoding="utf-8"))
    files = {}
    for root, _, fs in os.walk(HERE):
        for f in sorted(fs):
            rel = os.path.relpath(os.path.join(root, f), HERE)
            if rel in ("SOURCE.json", "fetch.py", "REPORT.md") or rel.startswith("__pycache__"):
                continue
            files[rel] = hashlib.sha256(open(os.path.join(root, f), "rb").read()).hexdigest()
    m["files"] = dict(sorted(files.items()))
    m["accessed"] = ACCESSED
    json.dump(m, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open(p, "a").write("\n")


UPAZILAS = [  # (subdomain, name_en, name_bn) — subdomains as linked from rajshahi.gov.bd
    ("bagha", "Bagha", "বাঘা"), ("bagmara", "Bagmara", "বাগমারা"), ("charghat", "Charghat", "চারঘাট"),
    ("durgapur", "Durgapur", "দুর্গাপুর"), ("godagari", "Godagari", "গোদাগাড়ী"), ("mohonpur", "Mohanpur", "মোহনপুর"),
    ("paba", "Paba", "পবা"), ("puthia", "Puthia", "পুঠিয়া"), ("tanore", "Tanore", "তানোর"),
]
UPZ_BN = {nfc(b): e for _, e, b in UPAZILAS}
UPZ_BN.update({nfc("দূর্গাপুর"): "Durgapur", nfc("গোদাগাড়ি"): "Godagari"})
# ---------------------------------------------------------------------------

KEY = "RAJSHAHI_UNION_PORTALS_2026"
P_UNIONS = "https://rajshahi.gov.bd/pages/static-pages/697f79bb35ce18e1c06b5300"
FACTS_WANTED = {"area_km2", "population", "mouza_count", "village_count", "ward_count", "household_count"}
# Manual review of the automatic matches (2026-11-12):
SKIP = {  # (portal host prefix, fact): why
    ("risikulup", "population"): "label row is misaligned; value is the next row's serial number",
    ("risikulup", "household_count"): "label/value misaligned (8032 is inside the label text)",
    ("kalmaup", "mouza_count"): "line merges 'মৌজার সংখ্যা -৪০ টি। গ্রাম -৪১ টি'; correct value added in MANUAL",
    ("chanduriaup", "mouza_count"): "same merged line; correct value added in MANUAL",
    ("darsanparaup", "population"): "two figures on one line; both added in MANUAL",
}
# (host prefix, fact, value, unit, year, printed text that must be on the page, note)
MANUAL = [
    ("kalmaup", "mouza_count", "40", "count", "", "মৌজার সংখ্যা -৪০ টি", ""),
    ("chanduriaup", "mouza_count", "17", "count", "", "মৌজার সংখ্যা -১৭ টি", ""),
    ("monigramup", "mouza_count", "17", "count", "", "মোজা:১৭ টি", "printed 'মোজা'"),
    ("darsanparaup", "population", "15156", "persons", "", "১৫,১৫৬ জন", "current figure, year not stated"),
    ("darsanparaup", "population", "13256", "persons", "2011", "আদম শুমারী ২০১১ অনূযায়ী জনসংখ্যাঃ ১৩,২৫৬ জন", "census 2011 as quoted"),
]
DOUBT = {  # (host prefix, fact): note appended to the row
    ("pakriup", "area_km2"): "DOUBT: 2199 km2 is impossible for a union (Godagari upazila is 475 km2); unit probably hectares",
    ("matikataup", "area_km2"): "DOUBT: 185 km2 is implausible for one of Godagari's 9 unions (upazila 475 km2)",
    ("kalmaup", "population"): "DOUBT: 3000 persons for a 51.63 km2 union is implausible (BBS 2022 has tens of thousands)",
    ("bausaup", "area_km2"): "DOUBT: Bausa page repeats the Arani page's area, village and mouza figures (2686 acres, 7, 7)",
    ("harianup", "population"): "page cites a '২০২১ আদম শুমারী'; no census was held in 2021",
    ("ghasigramup", "area_km2"): "printed '০৮ কিঃ মিঃ' (unit as printed is km, read as km2)",
}


def union_list():
    c = content(get(P_UNIONS))
    upz, out = None, []
    for cells, tr in table_rows(c["html"]):
        cells = [x for x in cells if x.strip()]
        if len(cells) >= 3 and nfc(cells[0]) in UPZ_BN:
            upz = UPZ_BN[nfc(cells[0])]
            cells = cells[2:]
        m = re.match(r"^([০-৯]+)\s*নং\s*(.+)$", nfc(cells[0])) if cells else None
        if not (m and upz):
            continue
        hrefs = [h for h in re.findall(r'href="([^"]*)"', tr) if re.search(r"up\d*\.rajshahi", h)]
        out.append(dict(upazila_en=upz, no=asc(m.group(1)), name_bn=m.group(2).strip(), site=clean_url(hrefs[-1]) if hrefs else ""))
    return out, c["date"]


def main():
    global CACHE
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache")
    CACHE = ap.parse_args().cache
    unions, list_date = union_list()
    facts, pages = [], []
    for u in unions:
        row = dict(upazila_en=u["upazila_en"], union_bn=u["name_bn"], union_no=u["no"], portal=u["site"])
        if not u["site"]:
            pages.append(dict(row, status="no portal link on district page"))
            continue
        try:
            home = get(u["site"])
        except Exception as e:  # noqa: BLE001
            pages.append(dict(row, status=f"portal error: {e}"))
            continue
        cands = [(h, x) for h, x in links(home, u["site"])
                 if "নজরে" in x and "ভূমি" not in x and "/pages/static-pages/" in h and urlparse(h).netloc == urlparse(u["site"]).netloc]
        if not cands:
            other = [h for h, x in links(home, u["site"]) if "লোক" in x and "ভিত্তিক" in x and "/pages/static-pages/" in h]
            pages.append(dict(row, url=other[0] if other else "",
                              status="no এক নজরে menu item" + ("; has a ward-wise population page (not parsed)" if other else "")))
            continue
        url, label = cands[0]
        try:
            c = content(get(url))
        except Exception as e:  # noqa: BLE001
            pages.append(dict(row, url=url, status=f"page error: {e}"))
            continue
        if not c or len(c["text"]) < 80:
            pages.append(dict(row, url=url, status="empty page"))
            continue
        host = urlparse(u["site"]).netloc
        save_raw(f"{host.split('.')[0]}_glance.txt", url, c)
        hp = host.split(".")[0]
        got = [f for f in extract_facts(c) if f["fact"] in FACTS_WANTED and (hp, f["fact"]) not in SKIP]
        for hpm, fact, val, unit, year, quote, note in MANUAL:
            if hpm != hp:
                continue
            if on_page(quote, c):
                got.append(dict(fact=fact, value=val, unit=unit, year=year, label="(manual)", raw=quote, note=note))
            else:
                print(f"WARNING manual quote gone from {url}: {quote}", file=sys.stderr)
        for f in got:
            fact = f["fact"] if f["fact"] != "area_km2" or f["unit"] == "km2" else "area"
            extra = "; ".join(x for x in (f["note"], DOUBT.get((hp, f["fact"]), "")) if x)
            facts.append(dict(entity_level="union", entity_name_en="", district_en="Rajshahi", upazila_en=u["upazila_en"],
                              code=u["no"], fact=fact, value=f["value"], unit=f["unit"], basis="as stated", year=f["year"],
                              source_key=KEY, source_url=url,
                              notes=redact(f"union {u['name_bn']} (no. {u['no']}); label '{f['label']}' value '{f['raw']}'"
                                           + (f"; {extra}" if extra else "") + f"; page updated {c['date'] or 'n/a'}")))
        pages.append(dict(row, url=url, status="ok", updated=c["date"], title=c["title"], facts=len(got)))
    write_csv(os.path.join(HERE, "facts.csv"), FACTS_H, facts)
    write_csv(os.path.join(HERE, "raw", "coverage.csv"),
              ["upazila_en", "union_no", "union_bn", "portal", "url", "status", "updated", "title", "facts"], pages)
    update_manifest()
    ok = sum(1 for p in pages if p["status"] == "ok")
    print(f"unions {len(unions)} (district list updated {list_date}); at-a-glance pages {ok}; facts {len(facts)}")


if __name__ == "__main__":
    main()
