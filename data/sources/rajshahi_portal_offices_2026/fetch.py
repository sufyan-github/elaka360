#!/usr/bin/env python3
"""Government offices listed on the national-portal sites (Divisional Commissioner, head-district DC portal and its upazila portals; DC and UNO offices of the other districts of the division; default Rajshahi).

Re-runnable: python3 fetch.py [--division rangpur|dhaka|chattogram|khulna|barishal|sylhet|mymensingh] [--out DIR]  (stdlib + requests). Optional: ELAKA_CACHE=<dir> caches pages."""
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
FETCH_ERRORS = {}  # url -> last request exception text (used only to word the notes of offices that could not be fetched)
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
            FETCH_ERRORS[url] = str(e)[:400]
        time.sleep(3 * (i + 1))
    return None
# --- end helper ---------------------------------------------------------------------------------------

# --- national-portal (2026 framework) parsing helpers -----------------------------------------------
import csv, hashlib, html, json, re, sys, unicodedata

CACHE = os.environ.get("ELAKA_CACHE")  # optional local cache dir (speeds up re-runs; not required)


def fetch_text(url):
    """GET a page politely; returns text or '' (never raises). Uses ELAKA_CACHE if set."""
    url = urllib.parse.quote(url, safe=":/?&=%#+,;~")
    fn = None
    if CACHE:
        os.makedirs(CACHE, exist_ok=True)
        fn = os.path.join(CACHE, hashlib.md5(url.encode()).hexdigest() + ".html")
        if os.path.exists(fn):
            return open(fn, encoding="utf-8", errors="replace").read()
        if os.path.exists(fn + ".fail"):
            err = open(fn + ".fail", encoding="utf-8", errors="replace").read()
            if err.startswith("ERR "):
                FETCH_ERRORS[url] = err[4:]
            return ""
    r = get(url, retries=1, timeout=25)
    if r is None or r.status_code != 200:
        print("  !", r.status_code if r is not None else "ERR", url, file=sys.stderr)
        if fn:
            open(fn + ".fail", "w", encoding="utf-8").write(str(r.status_code) if r is not None else "ERR " + FETCH_ERRORS.get(url, ""))
        return ""
    r.encoding = r.encoding or "utf-8"
    t = r.text
    if fn:
        open(fn, "w", encoding="utf-8").write(t)
    return t


def nfc(s):
    return unicodedata.normalize("NFC", re.sub(r"\s+", " ", s or "")).strip()


def strip_tags(s):
    s = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", " ", s, flags=re.S)
    s = re.sub(r"<br\s*/?>|</p>|</div>|</li>|</tr>|</h\d>", "\n", s)
    return html.unescape(re.sub(r"<[^>]+>", " ", s))


def page_title(t):
    m = re.search(r"<title>(.*?)</title>", t, re.S)
    return nfc(html.unescape(m.group(1))) if m else ""


def widget(t, name="ContentViewerWidget"):
    i = t.find('data-widget_name="%s"' % name)
    if i < 0:
        return ""
    j = t.find('data-widget_name="', i + 30)
    return t[i:j if j > 0 else len(t)]


def links(t):
    out = []
    for m in re.finditer(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', t, re.S):
        out.append((html.unescape(m.group(1)).strip(), nfc(html.unescape(re.sub(r"<[^>]+>", " ", m.group(2))))))
    return out


def list_table(t):
    """Rows of the framework's list tables (<tr class="table-tr"> with data-column cells)."""
    rows = []
    for tr in re.findall(r'<tr class="table-tr">(.*?)</tr>', t, re.S):
        d = {}
        for m in re.finditer(r'<td class="table-td[^"]*"(?: data-column="([^"]*)")?[^>]*>(.*?)</td>', tr, re.S):
            k, v = m.group(1) or "link", m.group(2)
            if k == "link":
                l = re.search(r'href="([^"]+)"', v)
                d[k] = html.unescape(l.group(1)) if l else ""
            else:
                d[k] = nfc(strip_tags(v))
        d["_hrefs"] = [html.unescape(h) for h in re.findall(r'href="([^"]+)"', tr)
                       if "objectstorage" not in h and not h.startswith("/pages/")]
        rows.append(d)
    return rows


def html_tables(t):
    """Plain <table>s inside page content -> list of tables (list of row cell-texts)."""
    out = []
    for tb in re.findall(r"<table.*?</table>", t, re.S):
        rows = []
        for tr in re.findall(r"<tr.*?</tr>", tb, re.S):
            cells = [nfc(strip_tags(c)) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.S)]
            hrefs = re.findall(r'href="([^"]+)"', tr)
            rows.append((cells, hrefs))
        out.append(rows)
    return out


BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def ascii_digits(s):
    return (s or "").translate(BN_DIGITS)


def officer_cards(t):
    """Officer cards (HybridBrowseWidget / OfficerDetailsWidget) -> list of dicts of the labelled fields."""
    t = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", " ", t, flags=re.S)
    lines = [nfc(html.unescape(x)) for x in re.split(r"<[^>]+>", t)]
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


def office_landline(s):
    """Keep only office landlines (Bangladesh fixed-line numbers start 0 but not 01); mobiles are dropped."""
    out = []
    for p in re.split(r"[,/;]|\s{2,}", ascii_digits(s or "")):
        d = re.sub(r"[^\d+]", "", p)
        d = re.sub(r"^\+?880", "0", d)
        if len(d) >= 6 and d.startswith("0") and not d.startswith("01"):
            out.append(d)
    return "; ".join(dict.fromkeys(out))


def gov_email(s):
    s = (s or "").replace(" ", "").replace("[at]", "@").lower()
    ms = re.findall(r"[a-z0-9._-]+@[a-z0-9.-]+\.[a-z]{2,}", s)
    return "; ".join(dict.fromkeys(m for m in ms if m.endswith(".gov.bd") or m.endswith("@mopa.gov.bd")))


# Rajshahi Division names: Bangla -> standard English (HDX COD-AB spellings; brief's Rajshahi District spellings)
DISTRICTS = {"রাজশাহী": "Rajshahi", "নাটোর": "Natore", "নওগাঁ": "Naogaon", "চাঁপাইনবাবগঞ্জ": "Chapainawabganj",
             "বগুড়া": "Bogura", "জয়পুরহাট": "Joypurhat", "পাবনা": "Pabna", "সিরাজগঞ্জ": "Sirajganj"}
DISTRICT_HOSTS = {"Rajshahi": "rajshahi.gov.bd", "Natore": "natore.gov.bd", "Naogaon": "naogaon.gov.bd",
                  "Chapainawabganj": "chapainawabganj.gov.bd", "Bogura": "bogra.gov.bd", "Joypurhat": "joypurhat.gov.bd",
                  "Pabna": "pabna.gov.bd", "Sirajganj": "sirajganj.gov.bd"}
UPAZILAS = {  # district -> [(english, bangla names/aliases..., portal subdomain)]
    "Rajshahi": [("Paba", ["পবা"], "paba"), ("Durgapur", ["দুর্গাপুর", "দূর্গাপুর"], "durgapur"),
                 ("Mohanpur", ["মোহনপুর"], "mohonpur"), ("Charghat", ["চারঘাট"], "charghat"),
                 ("Puthia", ["পুঠিয়া"], "puthia"), ("Bagha", ["বাঘা"], "bagha"),
                 ("Godagari", ["গোদাগাড়ী", "গোদাগাড়ি"], "godagari"), ("Tanore", ["তানোর"], "tanore"),
                 ("Bagmara", ["বাগমারা"], "bagmara")],
    "Natore": [("Natore Sadar", ["নাটোর সদর"], "natoresadar"), ("Singra", ["সিংড়া"], "singra"),
               ("Baraigram", ["বড়াইগ্রাম"], "baraigram"), ("Bagatipara", ["বাগাতিপাড়া"], "bagatipara"),
               ("Lalpur", ["লালপুর"], "lalpur"), ("Gurudaspur", ["গুরুদাসপুর"], "gurudaspur"),
               ("Naldanga", ["নলডাঙ্গা", "নলডাঙা"], "naldanga")],
    "Naogaon": [("Mahadebpur", ["মহাদেবপুর"], "mohadevpur"), ("Badalgachhi", ["বদলগাছী", "বদলগাছি"], "badalgachi"),
                ("Patnitala", ["পত্নীতলা", "পত্নিতলা"], "patnitala"), ("Dhamoirhat", ["ধামইরহাট"], "dhamoirhat"),
                ("Niamatpur", ["নিয়ামতপুর"], "niamatpur"), ("Manda", ["মান্দা"], "manda"), ("Atrai", ["আত্রাই"], "atrai"),
                ("Raninagar", ["রাণীনগর", "রানীনগর"], "raninagar"), ("Naogaon Sadar", ["নওগাঁ সদর"], "naogaonsadar"),
                ("Porsha", ["পোরশা"], "porsha"), ("Sapahar", ["সাপাহার"], "sapahar")],
    "Chapainawabganj": [("Chapainawabganj Sadar", ["চাঁপাইনবাবগঞ্জ সদর"], "chapainawabganjsadar"),
                        ("Gomastapur", ["গোমস্তাপুর"], "gomostapur"), ("Nachole", ["নাচোল"], "nachol"),
                        ("Bholahat", ["ভোলাহাট"], "bholahat"), ("Shibganj", ["শিবগঞ্জ"], "shibganj")],
    "Bogura": [("Kahaloo", ["কাহালু"], "kahaloo"), ("Bogura Sadar", ["বগুড়া সদর"], "sadar"),
               ("Sariakandi", ["সারিয়াকান্দি"], "shariakandi"), ("Shajahanpur", ["শাজাহানপুর", "শাহজাহানপুর"], "shajahanpur"),
               ("Dupchanchia", ["দুপচাঁচিয়া", "দুপচাচিঁয়া"], "dupchanchia"), ("Adamdighi", ["আদমদিঘি", "আদমদীঘি"], "adamdighi"),
               ("Nandigram", ["নন্দীগ্রাম", "নন্দিগ্রাম"], "nondigram"), ("Sonatala", ["সোনাতলা"], "sonatala"),
               ("Dhunat", ["ধুনট"], "dhunot"), ("Gabtali", ["গাবতলী"], "gabtali"), ("Sherpur", ["শেরপুর"], "sherpur"),
               ("Shibganj", ["শিবগঞ্জ"], "shibganj")],
    "Joypurhat": [("Akkelpur", ["আক্কেলপুর"], "akkelpur"), ("Kalai", ["কালাই"], "kalai"), ("Khetlal", ["ক্ষেতলাল"], "khetlal"),
                  ("Panchbibi", ["পাঁচবিবি"], "panchbibi"), ("Joypurhat Sadar", ["জয়পুরহাট সদর"], "joypurhatsadar")],
    "Pabna": [("Sujanagar", ["সুজানগর"], "sujanagar"), ("Ishwardi", ["ঈশ্বরদী"], "ishurdi"), ("Bhangura", ["ভাঙ্গুড়া", "ভাংগুড়া"], "bhangura"),
              ("Pabna Sadar", ["পাবনা সদর"], "pabnasadar"), ("Bera", ["বেড়া"], "bera"), ("Atgharia", ["আটঘরিয়া"], "atghoria"),
              ("Chatmohar", ["চাটমোহর"], "chatmohar"), ("Santhia", ["সাঁথিয়া"], "santhia"), ("Faridpur", ["ফরিদপুর"], "faridpur")],
    "Sirajganj": [("Belkuchi", ["বেলকুচি"], "belkuchi"), ("Chouhali", ["চৌহালি", "চৌহালী"], "chauhali"),
                  ("Kamarkhanda", ["কামারখন্দ"], "kamarkhand"), ("Kazipur", ["কাজীপুর"], "kazipur"),
                  ("Rayganj", ["রায়গঞ্জ"], "raigonj"), ("Shahjadpur", ["শাহজাদপুর"], "shahjadpur"),
                  ("Sirajganj Sadar", ["সিরাজগঞ্জ সদর"], "sirajganjsadar"), ("Tarash", ["তাড়াশ"], "tarash"),
                  ("Ullapara", ["উল্লাপাড়া"], "ullapara")],
}
CITY_THANAS = {"বোয়ালিয়া": "Boalia", "রাজপাড়া": "Rajpara", "মতিহার": "Motihar", "শাহ মখদুম": "Shah Makhdum",
               "চন্দ্রিমা": "Chandrima", "কাশিয়াডাঙ্গা": "Kashiadanga", "কাটাখালী": "Katakhali", "এয়ারপোর্ট": "Airport",
               "দামকুড়া": "Damkura", "বেলপুকুর": "Belpukur", "কর্ণহার": "Karnahar", "পবা": "Paba"}


def find_upazila(text, district=None):
    """First upazila (English) whose Bangla name occurs in text; restricted to district if given."""
    t = nfc(text)
    best = None
    for dist, ups in UPAZILAS.items():
        if district and dist != district:
            continue
        for en, bns, _ in ups:
            for bn in bns:
                i = t.find(bn)
                if i >= 0 and (best is None or i < best[0]):
                    best = (i, dist, en)
    return (best[1], best[2]) if best else (None, None)


# --- optional QA: point-in-polygon against HDX COD-AB upazila polygons in the repo (if present) -----------
_POLYS = None


def _load_polys():
    global _POLYS
    if _POLYS is not None:
        return _POLYS
    _POLYS = []
    here = os.path.dirname(os.path.abspath(__file__))
    fn = os.path.join(here, "..", "hdx_cod_ab_bgd", "boundaries.geojson")
    if os.path.exists(fn):
        for f in json.load(open(fn, encoding="utf-8"))["features"]:
            p = f["properties"]
            if p.get("level") in ("upazila", "city_corporation"):
                g = f["geometry"]
                polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
                _POLYS.append((p.get("district_en"), p.get("name_en"), polys))
    return _POLYS


def _inside(x, y, ring):
    c = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
            c = not c
        j = i
    return c


def locate(lat, lon):
    """(district_en, upazila_en) of the HDX polygon containing the point, or (None, None)."""
    for d, u, polys in _load_polys():
        for poly in polys:
            if _inside(lon, lat, poly[0]) and not any(_inside(lon, lat, h) for h in poly[1:]):
                return ("Chapainawabganj" if d and d.startswith("Chapai") else d), u
    return None, None


PLACE_COLS = ["source_key", "source_id", "name_bn", "name_en", "category_key", "lat", "lon", "address", "district_en",
              "upazila_en", "phone", "website", "email", "opening_hours", "operator", "ownership", "extra_json",
              "source_url", "notes"]
FACT_COLS = ["entity_level", "entity_name_en", "district_en", "upazila_en", "code", "fact", "value", "unit", "basis",
             "year", "source_key", "source_url", "notes"]


def write_csv(path, cols, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in cols})


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def jdump(d):
    return json.dumps({k: v for k, v in d.items() if v not in (None, "", [], {})}, ensure_ascii=False, separators=(",", ":"))
# --- end portal helpers --------------------------------------------------------------------------------


def menu_entries(t):
    """Main menu -> list of (top_title, group_title, link_title, href)."""
    w = widget(t, "MenusExpandableWidget") or t
    out = []
    tops = re.split(r'<li class="[^"]*menu-parent-list[^"]*">', w)
    for top in tops[1:]:
        m = re.search(r'class="menu-parent-list-link"[^>]*>(.*?)<icon', top, re.S) or re.search(r'title="([^"]*)"', top)
        ttl = nfc(html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))) if m else ""
        boxes = re.split(r'<div class="menu-child-box[^"]*">', top)
        for b in boxes[1:]:
            g = re.search(r'<h6[^>]*title="([^"]*)"', b)
            gt = nfc(html.unescape(g.group(1))) if g else ""
            for a in re.finditer(r'<a title="([^"]*)" class="menu-sub-child-link" href="([^"]*)"', b):
                out.append((ttl, gt, nfc(html.unescape(a.group(1))), html.unescape(a.group(2)).strip()))
    return out


# --- RAJSHAHI_PORTAL_OFFICES_2026 ---------------------------------------------------------------------------
# Government offices listed in the menus ("সরকারি অফিসসমূহ" / "সরকারী অফিস" / "স্থানীয় সরকার" / "পৌরসভা") of the national
# portal sites: Divisional Commissioner (rajshahidiv.gov.bd), Rajshahi DC portal and its 9 upazila portals; plus the
# DC office and UNO offices of the other 7 districts of the division. For every office portal we read the home page
# title and the first officer card (office head) for the office's official e-mail (*.gov.bd only) and office landline.
# Mobile numbers and personal e-mails are never copied.
SOURCE_KEY = "RAJSHAHI_PORTAL_OFFICES_2026"
OUT = os.path.dirname(os.path.abspath(__file__))
DIV_HOST = "rajshahidiv.gov.bd"
OFFICE_TOPS = re.compile(r"অফিস|দপ্তর|আরও")
HEAD = "Rajshahi"                                  # the division's head district (DC portal crawled in depth)
DIVCOM_NAME = "বিভাগীয় কমিশনারের কার্যালয়, রাজশাহী"

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


DIVISION_TABLES = {
    "rajshahi": dict(DISTRICTS=DISTRICTS, DISTRICT_HOSTS=DISTRICT_HOSTS, UPAZILAS=UPAZILAS, CITY_THANAS=CITY_THANAS,
                     HEAD="Rajshahi", DIV_HOST="rajshahidiv.gov.bd", DIVCOM_NAME="বিভাগীয় কমিশনারের কার্যালয়, রাজশাহী",
                     SOURCE_KEY="RAJSHAHI_PORTAL_OFFICES_2026", folder="rajshahi_portal_offices_2026"),
    "rangpur": dict(DISTRICTS=RANGPUR_DISTRICTS, DISTRICT_HOSTS=RANGPUR_DISTRICT_HOSTS, UPAZILAS=RANGPUR_UPAZILAS,
                    CITY_THANAS=RANGPUR_CITY_THANAS, HEAD="Rangpur", DIV_HOST="rangpurdiv.gov.bd",
                    DIVCOM_NAME="বিভাগীয় কমিশনারের কার্যালয়, রংপুর", SOURCE_KEY="RANGPUR_PORTAL_OFFICES_2026",
                    folder="rangpur_portal_offices_2026",
                    # DC portal "উপজেলা ও ইউনিয়ন" table (no pourashava list is published on rangpur.gov.bd)
                    UNION_LIST="https://rangpur.gov.bd/pages/static-pages/6977698ec4774958d7c22b0e"),
    "dhaka": dict(DISTRICTS=DHAKA_DISTRICTS, DISTRICT_HOSTS=DHAKA_DISTRICT_HOSTS, UPAZILAS=DHAKA_UPAZILAS,
                  CITY_THANAS=DHAKA_CITY_THANAS, HEAD="Dhaka", DIV_HOST="dhakadiv.gov.bd",
                  DIVCOM_NAME="বিভাগীয় কমিশনারের কার্যালয়, ঢাকা", SOURCE_KEY="DHAKA_PORTAL_OFFICES_2026",
                  folder="dhaka_portal_offices_2026",
                  # DC portal "ইউনিয়নের তালিকা" (upazila header rows, then serial | union | UP portal host as text)
                  UNION_LIST="https://dhaka.gov.bd/pages/static-pages/6995b33135ce18e1c07971c2"),
    "chattogram": dict(DISTRICTS=CHATTOGRAM_DISTRICTS, DISTRICT_HOSTS=CHATTOGRAM_DISTRICT_HOSTS, UPAZILAS=CHATTOGRAM_UPAZILAS,
                       CITY_THANAS=CHATTOGRAM_CITY_THANAS, HEAD="Chattogram", DIV_HOST="chittagongdiv.gov.bd",
                       DIVCOM_NAME="বিভাগীয় কমিশনারের কার্যালয়, চট্টগ্রাম", SOURCE_KEY="CHATTOGRAM_PORTAL_OFFICES_2026",
                       folder="chattogram_portal_offices_2026",
                       # DC portal "ইউনিয়নের তালিকা" (serial | [upazila] | 'Nনং <union>', UP portal linked)
                       UNION_LIST="https://chittagong.gov.bd/pages/static-pages/list-of-unions-12805e-6990c49335ce18e1c0715459"),
    "khulna": dict(DISTRICTS=KHULNA_DISTRICTS, DISTRICT_HOSTS=KHULNA_DISTRICT_HOSTS, UPAZILAS=KHULNA_UPAZILAS,
                   CITY_THANAS=KHULNA_CITY_THANAS, HEAD="Khulna", DIV_HOST="khulnadiv.gov.bd",
                   DIVCOM_NAME="বিভাগীয় কমিশনারের কার্যালয়, খুলনা", SOURCE_KEY="KHULNA_PORTAL_OFFICES_2026",
                   folder="khulna_portal_offices_2026",
                   # DC portal "ইউনিয়ন পরিষদসমূহের তালিকা" (serial | upazila on its first row | union; no UP portal links)
                   UNION_LIST="https://khulna.gov.bd/pages/static-pages/69810963a31054345f1d962d",
                   # the divisional portal links the Jashore DC portal as jashore.gov.bd; the Jashore portals use jessore.gov.bd
                   HOST_ALIASES={"jashore.gov.bd": "jessore.gov.bd"},
                   # Dacope's UNO portal is dakop.khulna.gov.bd but its office sub-sites are x.dacope.khulna.gov.bd
                   UPAZILA_SUB_ALIASES={"dakop.khulna.gov.bd": "dacope.khulna.gov.bd"}),
    "barishal": dict(DISTRICTS=BARISHAL_DISTRICTS, DISTRICT_HOSTS=BARISHAL_DISTRICT_HOSTS, UPAZILAS=BARISHAL_UPAZILAS,
                     CITY_THANAS=BARISHAL_CITY_THANAS, HEAD="Barishal", DIV_HOST="barisaldiv.gov.bd",
                     DIVCOM_NAME="বিভাগীয় কমিশনারের কার্যালয়, বরিশাল", SOURCE_KEY="BARISHAL_PORTAL_OFFICES_2026",
                     folder="barishal_portal_offices_2026",
                     # DC portal "ইউনিয়নের তালিকা" (serial | upazila | union count | comma-separated unions; no UP portal links)
                     UNION_LIST="https://barisal.gov.bd/pages/static-pages/6978a32135ce18e1c0672269",
                     # Wazirpur's menu links 'www.<office>.wazirpur.barisal.gov.bd' (self-signed TLS); Agailjhara has 'http://http://…'
                     CLEAN_HREFS=True),
    "sylhet": dict(DISTRICTS=SYLHET_DISTRICTS, DISTRICT_HOSTS=SYLHET_DISTRICT_HOSTS, UPAZILAS=SYLHET_UPAZILAS,
                   CITY_THANAS=SYLHET_CITY_THANAS, HEAD="Sylhet", DIV_HOST="sylhetdiv.gov.bd",
                   DIVCOM_NAME="বিভাগীয় কমিশনারের কার্যালয়, সিলেট", SOURCE_KEY="SYLHET_PORTAL_OFFICES_2026",
                   folder="sylhet_portal_offices_2026",
                   # DC portal "ইউনিয়নের তালিকা" (upazila on its first row | union | UP portal host as text, mostly also linked)
                   UNION_LIST="https://sylhet.gov.bd/pages/static-pages/696cb362c4774958d7ba0694",
                   INTERMEDIATES=SYLHET_INTERMEDIATES,
                   NOTES_EXTRA=" sylhet.gov.bd and its sub-sites send only their leaf certificate (Let's Encrypt YR1): the CA-published "
                               "intermediates are added from the AIA URLs, TLS verification stays on. The office sub-sites of the Sylhet "
                               "upazila portals (x.<upazila>.sylhet.gov.bd) serve the *.sylhet.gov.bd certificate, which does not cover a "
                               "second-level name: they were skipped (TLS hostname mismatch) and those offices are listed from the "
                               "menus without contacts (noted per row). Decorative marks in Sylhet menu titles ('*', '►►') are dropped "
                               "(title as listed in extra_json)."),
    "mymensingh": dict(DISTRICTS=MYMENSINGH_DISTRICTS, DISTRICT_HOSTS=MYMENSINGH_DISTRICT_HOSTS, UPAZILAS=MYMENSINGH_UPAZILAS,
                       CITY_THANAS=MYMENSINGH_CITY_THANAS, HEAD="Mymensingh", DIV_HOST="mymensinghdiv.gov.bd",
                       DIVCOM_NAME="বিভাগীয় কমিশনারের কার্যালয়, ময়মনসিংহ", SOURCE_KEY="MYMENSINGH_PORTAL_OFFICES_2026",
                       folder="mymensingh_portal_offices_2026",
                       # DC portal "উপজেলা ও ইউনিয়নের তালিকা" (serial | district | upazila (rowspan) | union; no UP portal links)
                       UNION_LIST="https://mymensingh.gov.bd/pages/static-pages/6973bef4c4774958d7bc1029",
                       # upazila menus link 'www.<office>.<upazila>.mymensingh.gov.bd' and the divisional menu 'www.pid.mymensinghdiv.gov.bd'
                       # / 'www.mcc.gov.bd': those www. hosts serve self-signed certificates; the offices' portals are the hosts without www.
                       CLEAN_HREFS=True, HOST_ALIASES={"www.mcc.gov.bd": "mcc.gov.bd"},
                       NOTES_EXTRA=" Union parishads: the DC portal list gives the upazila as a merged (rowspan) cell; rows outside every "
                                   "upazila cell, or whose name the upazila's own portal ('ইউনিয়ন সমূহ' page) does not list while exactly "
                                   "one other upazila portal of the district does, take the upazila from the upazila portals (noted per row, "
                                   "DC-list value kept in extra_json). Decorative marks in Mymensingh menu titles ('●', '*', '►') are "
                                   "dropped (title as listed in extra_json); a bare 'পৌরসভা' / 'থানা' title becomes '<upazila> পৌরসভা' / "
                                   "'<upazila> থানা' (noted). Menu links to 'www.<office>…gov.bd' hosts (self-signed certificates) and "
                                   "'www.mcc.gov.bd' are read as the hosts without 'www.', which serve the office portals; hosts that still "
                                   "fail TLS are skipped and noted per row. No Mymensingh Metropolitan Police exists (police.gov.bd lists "
                                   "eight metropolitan units), so no office is mapped to a metropolitan thana."),
}
DIV_PORTAL_PREFIX = {"rajshahi": "rajshahi", "rangpur": "rangpur", "dhaka": "dhaka", "chattogram": "chattogram", "khulna": "khulna",
                     "barishal": "barishal", "sylhet": "sylhet", "mymensingh": "mymensingh"}


def configure():
    global DIVISION, OUT, DISTRICTS, DISTRICT_HOSTS, UPAZILAS, CITY_THANAS, HEAD, DIV_HOST, DIVCOM_NAME, SOURCE_KEY, NOT_OFFICES, HOST_ALIASES, UPAZILA_SUB_ALIASES, CLEAN_HREFS
    DIVISION, OUT = parse_division_args({k: v["folder"] for k, v in DIVISION_TABLES.items()})
    t = DIVISION_TABLES[DIVISION]
    CLEAN_HREFS = t.get("CLEAN_HREFS", False)
    INTERMEDIATES.extend(u for u in t.get("INTERMEDIATES", []) if u not in INTERMEDIATES)  # before the first request
    HOST_ALIASES = t.get("HOST_ALIASES", {})
    UPAZILA_SUB_ALIASES = t.get("UPAZILA_SUB_ALIASES", {})
    DISTRICTS, DISTRICT_HOSTS, UPAZILAS, CITY_THANAS = t["DISTRICTS"], t["DISTRICT_HOSTS"], t["UPAZILAS"], t["CITY_THANAS"]
    HEAD, DIV_HOST, DIVCOM_NAME, SOURCE_KEY = t["HEAD"], t["DIV_HOST"], t["DIVCOM_NAME"], t["SOURCE_KEY"]
    if DIVISION != "rajshahi":  # offices of the other divisions' portals are skipped (Rajshahi keeps its original pattern)
        others = "|".join(v for k, v in DIV_PORTAL_PREFIX.items() if k != DIVISION)
        NOT_OFFICES = re.compile(r"^(bdlaws\.minlaw\.gov\.bd)$|(%s)div\.gov\.bd$" % others)
        if DIVISION == "mymensingh":  # Fulbaria's menu links the law database as www.bdlaws.gov.bd ('আইন ও বিধি')
            NOT_OFFICES = re.compile(NOT_OFFICES.pattern + r"|^(www\.)?bdlaws\.gov\.bd$")


def division_manifest():
    dn = DIVISION.capitalize()
    return {"key": SOURCE_KEY, "division": DIVISION, "kind": "portal_offices",
            "name": "Government offices on the national portal sites — Divisional Commissioner, %s DC & upazila portals, DC/UNO offices of %s Division" % (HEAD, dn),
            "organization": "Divisional / District / Upazila administrations (national portal framework)",
            "source_type": "government_portal", "trust_level": 4,
            "urls": ["https://%s/" % DIV_HOST, "https://%s/" % DISTRICT_HOSTS[HEAD], "https://<upazila>.%s/" % DISTRICT_HOSTS[HEAD]]
                    + ([DIVISION_TABLES[DIVISION]["UNION_LIST"]] if DIVISION_TABLES[DIVISION].get("UNION_LIST") else []),
            "accessed": __import__("datetime").date.today().isoformat(), "publication_date": None, "license": None, "license_url": None,
            "attribution": "Divisional / District / Upazila administrations (national portal framework)",
            "notes": "Office list = menu entries under 'সরকারি অফিসসমূহ' / 'সরকারী অফিস' / 'স্থানীয় সরকার' / 'পৌরসভা' plus the DC/UNO "
                     "portals themselves; union parishads from the %s DC portal's union list. Contacts = office landline and *.gov.bd "
                     "e-mail from the office head's officer card or the 'যোগাযোগ' page; mobile numbers, personal e-mails and officials' "
                     "names are not collected. No addresses/coordinates are published in a structured way. Licence: none stated on "
                     "the source; treat as government public information, cite the source." % HEAD
                     + DIVISION_TABLES[DIVISION].get("NOTES_EXTRA", "")}


def host_of(u):
    return urllib.parse.urlsplit(u).netloc.lower().split(":")[0]


def district_of_host(u):
    """Divisions after Rangpur: an office portal under another district's host (x.<district>.gov.bd) belongs to that district.
    Rajshahi and Rangpur keep their original behaviour (every menu entry in the head district)."""
    if DIVISION in ("rajshahi", "rangpur"):
        return None
    h = host_of(norm_url(u) or u)
    for d, dh in DISTRICT_HOSTS.items():
        if h == dh or h.endswith("." + dh):
            return d
    return None


HOST_ALIASES = {}  # alias host -> host used in the tables (set per division)
UPAZILA_SUB_ALIASES = {}  # upazila portal host -> second host under which its office sub-sites live (set per division)


CLEAN_HREFS = False  # set per division: repair doubled schemes ('http://http://x') and drop a leading 'www.' in menu links


def norm_url(u):
    u = u.strip()
    if CLEAN_HREFS:
        u = re.sub(r"^(https?://)+(https?://)", r"\2", u)
    if not re.match(r"https?://", u):
        return None
    p = urllib.parse.urlsplit(u)
    host = p.netloc.lower()
    if CLEAN_HREFS and host.startswith("www.") and host.endswith(".gov.bd") and host.count(".") > 3:
        host = host[4:]   # 'www.police.wazirpur.barisal.gov.bd' fails TLS (self-signed); the portal is police.wazirpur.barisal.gov.bd
    for a, c in HOST_ALIASES.items():
        if host == a or host.endswith("." + a):
            host = host[:-len(a)] + c
    return "https://%s/" % host


def category(name, host, level):
    first = host.split(".")[0]
    n = name
    if first == DIV_HOST.split(".")[0] and host == DIV_HOST:
        return "government.divisional_commissioner"
    if re.search(r"জেলা প্রশাসকের কার্যালয়", n):
        return "government.dc_office"
    if re.search(r"উপজেলা নির্বাহী অফিসারের কার্যালয়|উপজেলা নির্বাহী অফিস", n):
        return "government.uno_office"
    if first in ("police",) and level == "upazila" or re.search(r"থানা$", n) and "শিক্ষা" not in n and "সমবায়" not in n and "রিসোর্স" not in n:
        return "emergency.police_station"
    if first == "police" or "পুলিশ সুপারের কার্যালয়" in n:
        return "government.sp_office"
    if first == "fireservice" and level == "upazila":
        return "emergency.fire_station"
    if first == "passport" or "পাসপোর্ট" in n:
        return "government.passport_office"
    if first == "cs" or "সিভিল সার্জন" in n:
        return "government.civil_surgeon"
    if first in ("acl", "acland", "landoffice") or re.search(r"ভূমি অফিস|সহকারী কমিশনার \(ভূমি\)", n):
        return "government.land_office"
    if first == "post" or re.search(r"ডাকঘর|পোস্ট অফিস|ডাক বিভাগ", n):
        return "government.post_office"
    if first == "dae" or "কৃষি অফিস" in n or "কৃষি সম্প্রসারণ" in n:
        return "agriculture.agri_office"
    if first == "health" or "উপজেলা হাসপাতাল" in n or "স্বাস্থ্য কমপ্লেক্স" in n:
        return "health.upazila_health_complex"
    if re.search(r"পৌরসভা", n) or re.search(r"pourashava|pourosova|ps\.", host):
        return "government.pourashava_office"
    if re.search(r"সিটি কর্পোরেশন", n):
        return "government.city_corporation_office"
    if re.search(r"ইউনিয়ন পরিষদ", n):
        return "government.union_parishad"
    if re.search(r"আদালত|জজ কোর্ট|কোর্ট$", n):
        return "government.court"
    if re.search(r"কলেজ", n):
        return "education.college"
    if re.search(r"প্রশিক্ষণ কেন্দ্র|প্রশিক্ষন কেন্দ্র|ট্রেনিং সেন্টার|ইনস্টিটিউট|ইন্সটিটিউট|ইন্সস্টিটিউট", n) and "মৃত্তিকা" not in n:
        return "education.training_center"
    if re.search(r"ব্যাংক", n):
        return "finance.bank"
    return "government"


def head_card(base, home):
    """Officer card of the office head: PersonCard link on the home page, else first card of /pages/officers."""
    m = re.search(r'data-widget_name="PersonCardWidget".*?href="(/pages/officers/[^"]+)"', home, re.S)
    url = base.rstrip("/") + (m.group(1) if m else "/pages/officers")
    t = fetch_text(url)
    cards = officer_cards(widget(t, "ContentViewerWidget") or widget(t, "HybridBrowseWidget") or t)
    return (cards[0] if cards else {}), url


def contact_page(base, home):
    """UNO/DC 'যোগাযোগ' static page: office phone + e-mail lines."""
    for href, txt in links(widget(home, "MenusExpandableWidget")):
        if txt == "যোগাযোগ" and href.startswith("/pages/static-pages/"):
            url = base.rstrip("/") + href
            t = strip_tags(widget(fetch_text(url)))
            return t, url
    return "", ""


NOT_OFFICES = re.compile(r"^(bdlaws\.minlaw\.gov\.bd)$|(dhaka|chattogram|khulna|barishal|sylhet|rangpur|mymensingh)div\.gov\.bd$")


def office_record(name, href, district, upazila, level, group, menu_src, extra_cat=None, contact_page_too=False):
    base = norm_url(href)
    if not base or NOT_OFFICES.search(host_of(base)):
        return None  # law database link / office of another division
    home = fetch_text(base)
    notes, ex = [], {"menu_group": group or None, "listed_on": menu_src, "office_level": level}
    rec = {"source_key": SOURCE_KEY, "source_id": host_of(base), "name_bn": nfc(name).rstrip("।. "), "website": base,
           "district_en": district, "upazila_en": upazila or "", "ownership": "public", "source_url": base}
    if DIVISION == "sylhet":
        # Sylhet upazila menus decorate titles ('*উপজেলা …' on Golapganj, '►►' elsewhere): the marks are dropped (title as listed in
        # extra_json); a bare 'থানা' (Golapganj, Zakiganj) becomes '<upazila> থানা'
        clean = re.sub(r"^[\s*►♦•\u200c\u200d]+", "", rec["name_bn"]).strip()
        if clean != rec["name_bn"]:
            ex["menu_title_as_listed"] = rec["name_bn"]
            rec["name_bn"] = clean
        if rec["name_bn"] == "থানা" and upazila:
            ub = next((bns[0] for en, bns, _ in UPAZILAS.get(district, []) if en == upazila), None)
            if ub:
                ex["menu_title_as_listed"] = ex.get("menu_title_as_listed") or rec["name_bn"]
                rec["name_bn"] = "%s থানা" % ub
                notes.append("menu title is only 'থানা'; name composed from the upazila")
    if DIVISION == "mymensingh":
        # Mymensingh menus mark titles with bullets ('● পুলিশ সুপারের কার্যালয়' on the DC portal): dropped, title as listed kept
        clean = re.sub(r"^[\s*►♦•●○◆■\u200c\u200d]+", "", rec["name_bn"]).strip().rstrip(", ")
        if clean != rec["name_bn"]:
            ex["menu_title_as_listed"] = rec["name_bn"]
            rec["name_bn"] = clean
        if rec["name_bn"] in ("পৌরসভা", "থানা") and upazila:
            ub = next((bns[0] for en, bns, _ in UPAZILAS.get(district, []) if en == upazila), None)
            if ub:
                ex["menu_title_as_listed"] = ex.get("menu_title_as_listed") or rec["name_bn"]
                notes.append("menu title is only '%s'; name composed from the upazila" % rec["name_bn"])
                rec["name_bn"] = "%s %s" % (ub, rec["name_bn"])
    if not home:
        h = host_of(base)
        if DIVISION in ("sylhet", "mymensingh") and "Hostname mismatch" in FETCH_ERRORS.get(urllib.parse.quote(base, safe=":/?&=%#+,;~"), ""):
            # e.g. x.<upazila>.sylhet.gov.bd serve the *.sylhet.gov.bd certificate, which does not cover a second-level name
            notes.append("office portal not fetched: TLS certificate hostname mismatch for %s (skipped, not fetched without "
                         "verification); listed from %s menu only" % (h, menu_src))
        elif DIVISION == "mymensingh" and "SSLError" in FETCH_ERRORS.get(urllib.parse.quote(base, safe=":/?&=%#+,;~"), ""):
            err = FETCH_ERRORS[urllib.parse.quote(base, safe=":/?&=%#+,;~")]
            why = ("self-signed certificate" if "self-signed" in err else "handshake failure" if "HANDSHAKE" in err.upper()
                   else "error")
            notes.append("office portal not fetched: TLS %s for %s (skipped, not fetched without verification); listed from %s "
                         "menu only" % (why, h, menu_src))
        else:
            notes.append("office portal did not respond at access time; listed from %s menu only" % menu_src)
        rec["source_url"] = menu_src
    else:
        ttl = page_title(home)
        ex["portal_title"] = re.sub(r"^হোম\s*\|\s*", "", ttl) or None
        card, curl = head_card(base, home)
        phone = office_landline(card.get("ফোন (অফিস)", ""))
        email = gov_email(card.get("ইমেইল", ""))
        if card.get("অফিস"):
            ex["office_name_on_officer_card"] = card.get("অফিস")
        if card.get("পদবি"):
            ex["head_designation"] = card.get("পদবি")
        if contact_page_too:
            ct, cu = contact_page(base, home)
            if ct:
                m = re.search(r"ফোন\s*[:ঃ]?\s*([০-৯0-9\-\s+]{6,20})", ct)
                p2 = office_landline(m.group(1)) if m else ""
                e2 = gov_email(ct)
                phone = phone or p2
                email = email or e2
                if p2 or e2:
                    ex["contact_page"] = cu
        if DIVISION == "mymensingh" and email:   # the Nokla UNO card prints '-unonakhla@mopa.gov.bd'
            email = "; ".join(e.lstrip("-._") for e in email.split("; "))
        rec.update({"phone": phone, "email": email})
        if phone or email:
            ex["contact_from"] = curl
    rec["category_key"] = extra_cat or category(rec["name_bn"] + " " + (ex.get("portal_title") or ""), host_of(base), level)
    rec["extra_json"] = jdump(ex)
    rec["notes"] = "; ".join(notes)
    return rec


class Job:
    def __init__(self, *a):
        self.a = a


def main():
    configure()
    from concurrent.futures import ThreadPoolExecutor
    places, seen, jobs = [], set(), []

    def add(r):
        if isinstance(r, Job):
            if CLEAN_HREFS and not nfc(r.a[0]):
                return   # menu entry without a title (Muladi lists the SFDF link twice, once untitled)
            jobs.append(r)
            places.append(r)
            return
        if r and (r["source_id"], r["district_en"]) not in seen:
            seen.add((r["source_id"], r["district_en"]))
            places.append(r)
        elif r:
            print("  dup", r["source_id"], file=sys.stderr)

    # 1) Divisional Commissioner's office + division-level offices listed on the divisional portal
    div = "https://%s/" % DIV_HOST
    add(Job(DIVCOM_NAME, div, HEAD, None, "division", None, div,
                      "government.divisional_commissioner", True))
    divhome = fetch_text(div)
    for top, grp, ttl, href in menu_entries(divhome):
        if OFFICE_TOPS.search(top) and norm_url(href) and host_of(href).endswith(".gov.bd") and host_of(href) != DIV_HOST:
            add(Job(ttl, href, district_of_host(href) or HEAD, None, "division", grp, div))

    # 2) Rajshahi District: DC portal + its office menu + local government; 9 upazila portals + their office menus
    for dist, dhost in DISTRICT_HOSTS.items():
        dbase = "https://%s/" % dhost
        add(Job("জেলা প্রশাসকের কার্যালয়, " + [k for k, v in DISTRICTS.items() if v == dist][0], dbase, dist, None,
                          "district", None, dbase, "government.dc_office", True))
        dhome = fetch_text(dbase)
        if dist == HEAD:
            for top, grp, ttl, href in menu_entries(dhome):
                if (OFFICE_TOPS.search(top) or "স্থানীয় সরকার" in top) and norm_url(href) and host_of(href) != dhost:
                    if re.search(r"\.(?:gov\.bd|portal\.gov\.bd)$", host_of(href)) or "pourashava" in host_of(href):
                        up = None
                        for en, _, sub in UPAZILAS[dist]:
                            if host_of(href).endswith(".%s.%s" % (sub, dhost)):
                                up = en
                        add(Job(ttl, href, district_of_host(href) or dist, up, "district", grp, dbase))
        for en, bns, sub in UPAZILAS[dist]:
            ubase = "https://%s.%s/" % (sub, dhost)
            add(Job("উপজেলা নির্বাহী অফিসারের কার্যালয়, " + bns[0], ubase, dist, en, "upazila", None, dbase,
                              "government.uno_office", True))
            if dist != HEAD:
                continue
            uhome = fetch_text(ubase)
            for top, grp, ttl, href in menu_entries(uhome):
                if (OFFICE_TOPS.search(top) or "পৌরসভা" in top) and norm_url(href) and host_of(href) != host_of(ubase):
                    h = host_of(href)
                    own = [host_of(ubase)] + ([UPAZILA_SUB_ALIASES[host_of(ubase)]] if host_of(ubase) in UPAZILA_SUB_ALIASES else [])
                    if h.endswith(".gov.bd") and not any(h.endswith("." + o) for o in own) and "পৌরসভা" not in top + ttl:
                        continue  # only the upazila's own sub-sites (x.<upazila>.<district>.gov.bd) and pourashavas
                    add(Job(ttl, href, dist, en, "upazila", grp or top, ubase))

    # run the office-portal lookups (different hosts in parallel; each host is still hit sequentially)
    uniq = {}
    for j in jobs:
        k = (norm_url(j.a[1]), j.a[2])
        if k not in uniq or (len(j.a) > 7 and len(uniq[k].a) <= 7):
            uniq[k] = j  # the explicit DC/UNO/Div. Commissioner entries win over menu duplicates
    with ThreadPoolExecutor(max_workers=4) as ex:
        res = dict(zip(uniq.keys(), ex.map(lambda j: office_record(*j.a), uniq.values())))
    done, out = set(), []
    for p in places:
        if isinstance(p, Job):
            k = (norm_url(p.a[1]), p.a[2])
            r = res.get(k)
            if r and k not in done:
                done.add(k)
                out.append(r)
        else:
            out.append(p)
    places[:] = out
    seen.update((r["source_id"], r["district_en"]) for r in places)

    # 3) Head-district local-government lists (names only, from the DC portal static pages)
    if DIVISION == "rangpur":
        union_list_rangpur(add)
    if DIVISION == "dhaka":
        union_list_dhaka(add)
    if DIVISION == "chattogram":
        union_list_chattogram(add)
    if DIVISION == "khulna":
        union_list_khulna(add)
    if DIVISION == "barishal":
        union_list_barishal(add)
    if DIVISION == "sylhet":
        union_list_sylhet(add)
    if DIVISION == "mymensingh":
        union_list_mymensingh(add)
    if DIVISION != "rajshahi":
        finish_places(places)
        return
    up_list = "https://rajshahi.gov.bd/pages/static-pages/697f79bb35ce18e1c06b5300"
    t = widget(fetch_text(up_list))
    cur_up = None
    for tb in html_tables(t):
        for cells, hrefs in tb:
            if not cells:
                continue
            if len(cells) >= 3 and re.search(r"টি$", cells[1] or ""):
                cur_up = find_upazila(cells[0], "Rajshahi")[1]
                cells = cells[2:]
            m = re.match(r"^([০-৯0-9][০-৯0-9 ]*?)\s*নং\s*(.+)$", cells[0]) if cells else None
            if m and cur_up:
                site = norm_url(hrefs[-1]) if hrefs else None  # first row also carries the upazila link
                add({"source_key": SOURCE_KEY, "source_id": host_of(site) if site else "up:%s:%s" % (cur_up, m.group(2)),
                     "name_bn": "%s ইউনিয়ন পরিষদ" % nfc(m.group(2)), "category_key": "government.union_parishad",
                     "district_en": "Rajshahi", "upazila_en": cur_up, "website": site or "", "ownership": "public",
                     "extra_json": jdump({"union_no": int(ascii_digits(m.group(1)).replace(" ", "")), "union_name_as_listed": cells[0]}),
                     "source_url": up_list, "notes": "listed on the DC portal union list; office contacts not collected (UP portals list elected representatives)"})
    ps_list = "https://rajshahi.gov.bd/pages/static-pages/6a706a5b3a58d2277e320df7"
    t = widget(fetch_text(ps_list))
    have = {r["name_bn"].replace(" ", "") for r in places}
    for tb in html_tables(t):
        for cells, hrefs in tb:
            if len(cells) >= 4 and "পৌরসভা" in cells[3] and cells[1] == "রাজশাহী":
                nm = nfc(cells[3])
                up_ps = find_upazila(cells[2], "Rajshahi")[1] or ""
                hit = [r for r in places if r["name_bn"].replace(" ", "") == nm.replace(" ", "")]
                if hit:
                    for r in hit:
                        r["upazila_en"] = r["upazila_en"] or up_ps
                    continue
                add({"source_key": SOURCE_KEY, "source_id": "pourashava:%s" % nm, "name_bn": nm,
                     "category_key": "government.pourashava_office", "district_en": "Rajshahi",
                     "upazila_en": up_ps, "ownership": "public",
                     "extra_json": jdump({"serial": ascii_digits(cells[0])}), "source_url": ps_list,
                     "notes": "listed on the DC portal pourashava list; no portal link given there"})
    finish_places(places)


def finish_places(places):
    for r in places:
        if r["district_en"] == HEAD and not r["upazila_en"]:
            for bn, th in CITY_THANAS.items():
                if bn in r["name_bn"] and th not in ("Paba",):
                    r["upazila_en"] = th
                    r["notes"] = "; ".join(x for x in [r.get("notes"), "upazila_en holds a %s metropolitan thana" % HEAD] if x)
                    break
    write_csv(os.path.join(OUT, "places.csv"), PLACE_COLS, places)
    print(len(places), "places", file=sys.stderr)
    if DIVISION != "rajshahi":
        write_division_manifest(OUT, division_manifest())


def union_list_rangpur(add):
    """rangpur.gov.bd 'উপজেলা ও ইউনিয়ন': rows (district, upazila, union) / (upazila, union) / (union)."""
    url = DIVISION_TABLES["rangpur"]["UNION_LIST"]
    t = widget(fetch_text(url))
    cur_up = None
    for tb in html_tables(t):
        for cells, hrefs in tb:
            cells = [c for c in cells if c]
            if not cells or cells[-1] == "ইউনিয়ন":
                continue
            if len(cells) >= 2:
                cur_up = find_upazila(cells[-2], HEAD)[1]
            if not cur_up:
                continue
            listed = cells[-1]
            m = re.match(r"^([০-৯0-9]+)\s*নং\s*(.+)$", listed)
            base = nfc(m.group(2) if m else listed)
            base = re.sub(r"\s*(ইউনিয়ন|ইউনিয়ান|ইউুনয়ন)$", "", base).strip()
            site = norm_url(hrefs[-1]) if hrefs else None
            add({"source_key": SOURCE_KEY, "source_id": host_of(site) if site else "up:%s:%s" % (cur_up, base),
                 "name_bn": "%s ইউনিয়ন পরিষদ" % base, "category_key": "government.union_parishad",
                 "district_en": HEAD, "upazila_en": cur_up, "website": site or "", "ownership": "public",
                 "extra_json": jdump({"union_no": int(ascii_digits(m.group(1))) if m else None, "union_name_as_listed": listed}),
                 "source_url": url,
                 "notes": "listed on the DC portal union list; office contacts not collected (UP portals list elected representatives)"})


def union_list_dhaka(add):
    """dhaka.gov.bd 'ইউনিয়নের তালিকা': '<upazila> উপজেলা' header rows, then (serial, union name, UP portal host as text)."""
    url = DIVISION_TABLES["dhaka"]["UNION_LIST"]
    t = widget(fetch_text(url))
    cur_up = None
    for tb in html_tables(t):
        for cells, hrefs in tb:
            cells = [c for c in cells if c]
            if len(cells) == 1 and cells[0].endswith("উপজেলা"):
                cur_up = find_upazila(cells[0], HEAD)[1]
                continue
            if len(cells) < 2 or not re.match(r"^[০-৯0-9]+$", cells[0]) or not cur_up:
                continue
            listed = cells[1]
            base = re.sub(r"\s*(ইউনিয়ন|ইউনিয়ান)( পরিষদ)?$", "", nfc(listed)).strip()
            host = (cells[2] if len(cells) > 2 else "").strip().lower()
            site = norm_url("https://" + host) if re.match(r"^[a-z0-9.-]+\.gov\.bd$", host) else (norm_url(hrefs[-1]) if hrefs else None)
            add({"source_key": SOURCE_KEY, "source_id": host_of(site) if site else "up:%s:%s" % (cur_up, base),
                 "name_bn": "%s ইউনিয়ন পরিষদ" % base, "category_key": "government.union_parishad",
                 "district_en": HEAD, "upazila_en": cur_up, "website": site or "", "ownership": "public",
                 "extra_json": jdump({"serial_on_list": int(ascii_digits(cells[0])), "union_name_as_listed": listed}),
                 "source_url": url,
                 "notes": "listed on the DC portal union list (portal host as printed, not opened); office contacts not collected "
                          "(UP portals list elected representatives)"})


def union_list_chattogram(add):
    """chittagong.gov.bd 'ইউনিয়নের তালিকা': (serial, upazila, 'Nনং <union>') on an upazila's first row, then (serial, 'Nনং <union>');
    the last link of a row is the UP portal."""
    url = DIVISION_TABLES["chattogram"]["UNION_LIST"]
    t = widget(fetch_text(url))
    cur_up = None
    for tb in html_tables(t):
        for cells, hrefs in tb:
            cells = [c for c in cells if c]
            if len(cells) < 2 or not re.match(r"^[০-৯0-9]+\.?$", cells[0]):
                continue
            if len(cells) >= 3:
                cur_up = find_upazila(cells[1], HEAD)[1]
            if not cur_up:
                continue
            listed = cells[-1]
            m = re.match(r"^([০-৯0-9]+)\s*নং\s*(.+)$", listed)
            base = re.sub(r"\s*(ইউনিয়ন|ইউনিয়ান)( পরিষদ)?$", "", nfc(m.group(2) if m else listed)).strip()
            ups = [h for h in hrefs if re.search(r"up\.[a-z]+\.gov\.bd", host_of(h))]
            site = norm_url(ups[-1]) if ups else None
            add({"source_key": SOURCE_KEY, "source_id": host_of(site) if site else "up:%s:%s" % (cur_up, base),
                 "name_bn": "%s ইউনিয়ন পরিষদ" % base, "category_key": "government.union_parishad",
                 "district_en": HEAD, "upazila_en": cur_up, "website": site or "", "ownership": "public",
                 "extra_json": jdump({"union_no": int(ascii_digits(m.group(1))) if m else None, "union_name_as_listed": listed}),
                 "source_url": url,
                 "notes": "listed on the DC portal union list (UP portal as linked there, not opened); office contacts not collected "
                          "(UP portals list elected representatives)"})



def union_list_khulna(add):
    """khulna.gov.bd 'ইউনিয়ন পরিষদসমূহের তালিকা': (serial, upazila, union) on an upazila's first row, then (serial, '', union);
    no UP portal links on this list."""
    url = DIVISION_TABLES["khulna"]["UNION_LIST"]
    t = widget(fetch_text(url))
    cur_up = None
    for tb in html_tables(t):
        for cells, hrefs in tb:
            if len(cells) < 3 or not re.match(r"^[০-৯0-9]+\.?$", cells[0]):
                continue
            if cells[1]:
                cur_up = find_upazila(cells[1], HEAD)[1]
            if not cur_up or not cells[2]:
                continue
            listed = cells[2]
            base = re.sub(r"\s*(ইউনিয়ন|ইউনিয়ান)( পরিষদ)?$", "", nfc(listed)).strip()
            add({"source_key": SOURCE_KEY, "source_id": "up:%s:%s" % (cur_up, base),
                 "name_bn": "%s ইউনিয়ন পরিষদ" % base, "category_key": "government.union_parishad",
                 "district_en": HEAD, "upazila_en": cur_up, "website": "", "ownership": "public",
                 "extra_json": jdump({"serial_on_list": int(ascii_digits(cells[0]).rstrip(".")), "union_name_as_listed": listed}),
                 "source_url": url,
                 "notes": "listed on the DC portal union list (names as printed, some without spaces); no UP portal given there; "
                          "office contacts not collected (UP portals list elected representatives)"})


def union_list_barishal(add):
    """barisal.gov.bd 'ইউনিয়নের তালিকা': (serial, upazila, union count, 'a, b, c'); one row per upazila, no UP portal links.
    Cells are read without inserting spaces at tag boundaries (the page splits names like 'রায়পাশা-কড়াপুর' over <span>s)."""
    url = DIVISION_TABLES["barishal"]["UNION_LIST"]
    t = widget(fetch_text(url))
    for tr in re.findall(r"<tr.*?</tr>", t, re.S):
        cells = [nfc(html.unescape(re.sub(r"<[^>]+>", "", c))) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", tr, re.S)]
        if len(cells) < 4 or not re.match(r"^[০-৯0-9]+\.?$", cells[0]):
            continue
        up = find_upazila(cells[1], HEAD)[1]
        if not up:
            print("  ! upazila not matched on union list:", cells[1], file=sys.stderr)
            continue
        names = [nfc(x) for x in re.split(r"[,،]", cells[3]) if nfc(x)]
        for i, listed in enumerate(names, 1):
            base = re.sub(r"\s*(ইউনিয়ন|ইউনিয়ান)( পরিষদ)?$", "", listed).strip()
            add({"source_key": SOURCE_KEY, "source_id": "up:%s:%s" % (up, base),
                 "name_bn": "%s ইউনিয়ন পরিষদ" % base, "category_key": "government.union_parishad",
                 "district_en": HEAD, "upazila_en": up, "website": "", "ownership": "public",
                 "extra_json": jdump({"order_on_list": i, "unions_in_upazila_on_list": int(ascii_digits(cells[2])) if ascii_digits(cells[2]).isdigit() else None,
                                      "union_name_as_listed": listed}),
                 "source_url": url,
                 "notes": "listed on the DC portal union list (one comma-separated cell per upazila, names as printed); no UP portal "
                          "given there; office contacts not collected (UP portals list elected representatives)"})


def union_list_sylhet(add):
    """sylhet.gov.bd 'ইউনিয়নের তালিকা': (upazila, union, UP portal host) on an upazila's first row, then (union, host). The host is
    printed as text and usually also linked. Numbers are printed in several ways ('১নং', '২ নং', '০১', '০২ নং'), the suffix as
    'ইউনিয়ন পরিষদ' or 'ইউ/পি'. A host printed for an earlier union of the list is not repeated (the list gives Osmaninagar's
    পশ্চিম পৈলনপুর the host of উমরপুর); rows without a host keep the website empty."""
    url = DIVISION_TABLES["sylhet"]["UNION_LIST"]
    t = widget(fetch_text(url))
    cur_up, used = None, {}
    for tb in html_tables(t):
        for cells, hrefs in tb:
            if len(cells) == 3:
                up = find_upazila(cells[0], HEAD)[1]
                if not up:
                    if cells[0] != "উপজেলার নাম":
                        print("  ! upazila not matched on union list:", cells[0], file=sys.stderr)
                    continue
                cur_up = up
                cells = cells[1:]
            if len(cells) != 2 or not cur_up or not cells[0]:
                continue
            listed = cells[0]
            m = re.match(r"^([০-৯0-9]+)\s*(?:নং)?\s*(.+)$", listed)
            base = re.sub(r"\s*(ইউনিয়ন পরিষদ|ইউনিয়ন|ইউ/পি|ইউপি)$", "", nfc(m.group(2) if m else listed)).strip()
            host = cells[1].strip().lower()
            site = norm_url("https://" + host) if re.match(r"^[a-z0-9-]+\.sylhet\.gov\.bd$", host) else None
            note = ""
            if site and host in used:
                note = "; the list prints %s here too, the host it gives %s, so no website is kept for this row" % (host, used[host])
                site = None
            elif site:
                used[host] = listed
            add({"source_key": SOURCE_KEY, "source_id": "up:%s:%s" % (cur_up, base),
                 "name_bn": "%s ইউনিয়ন পরিষদ" % base, "category_key": "government.union_parishad",
                 "district_en": HEAD, "upazila_en": cur_up, "website": site or "", "ownership": "public",
                 "extra_json": jdump({"union_no": int(ascii_digits(m.group(1))) if m else None, "union_name_as_listed": listed,
                                      "up_portal_linked": bool(hrefs) or None}),
                 "source_url": url,
                 "notes": "listed on the DC portal union list (UP portal host as printed there, not opened); office contacts not "
                          "collected (UP portals list elected representatives)" + note})



def _union_key(s):
    """Loose comparison key for union names across portals (spacing, ড়/র, ী/ি, ূ/ু, য়/য, chandrabindu)."""
    s = nfc(s).replace(" ", "").replace("\u200c", "")
    for a, b in (("\u09a1\u09bc", "র"), ("\u09a2\u09bc", "র"), ("\u09af\u09bc", "য"), ("ী", "ি"), ("ূ", "ু"), ("ঁ", ""), ("।", "")):
        s = s.replace(a, b)
    return s


def upazila_union_pages(dist):
    """Upazila portals' 'ইউনিয়ন সমূহ' pages (menu link) -> {upazila: (url, comparison text)}; pages that fail are left out."""
    out = {}
    for en, _, sub in UPAZILAS[dist]:
        ubase = "https://%s.%s/" % (sub, DISTRICT_HOSTS[dist])
        for top, grp, ttl, href in menu_entries(fetch_text(ubase)):
            if re.search(r"ইউনিয়ন\s*সমূহ|ইউনিয়নসমূহ|ইউনিয়নের তালিকা", ttl) and href.startswith("/pages/"):
                url = ubase.rstrip("/") + href
                t = widget(fetch_text(url))
                if t:
                    out[en] = (url, _union_key(strip_tags(t)))
                break
    return out


def union_list_mymensingh(add):
    """mymensingh.gov.bd 'উপজেলা ও ইউনিয়নের তালিকা': serial | district (first row) | upazila (merged cell, rowspan) | union.
    The merged upazila cells are followed by their rowspan. Rows outside every upazila cell (the list has none for nine
    Haluaghat unions), and rows whose upazila's own portal ('ইউনিয়ন সমূহ') does not list the union while exactly one other
    upazila portal of the district does (the Tarakanda cell spans জুগলী), take the upazila from the upazila portals, noted."""
    url = DIVISION_TABLES["mymensingh"]["UNION_LIST"]
    t = widget(fetch_text(url))
    pages = upazila_union_pages(HEAD)
    cur_up, left = None, 0
    for tb in re.findall(r"<table.*?</table>", t, re.S):
        for tr in re.findall(r"<tr.*?</tr>", tb, re.S):
            tds = re.findall(r"<td([^>]*)>(.*?)</td>", tr, re.S)
            cells = [(a, nfc(strip_tags(c))) for a, c in tds]
            union = next((c for a, c in cells if re.search(r"ইউনিয়ন পরিষদ$", c)), None)
            upcell = [(a, c) for a, c in cells if c and not re.search(r"ইউনিয়ন", c) and find_upazila(c, HEAD)[1]
                      and nfc(c) not in MYMENSINGH_DISTRICTS]
            if upcell:
                a, c = upcell[-1]
                cur_up = find_upazila(c, HEAD)[1]
                m = re.search(r'rowspan="?(\d+)', a)
                left = int(m.group(1)) - 1 if m else 0
            elif left > 0:
                left -= 1
            else:
                cur_up = None
            if not union:
                continue
            base = re.sub(r"\s*ইউনিয়ন পরিষদ$", "", union).strip()
            ex = {"union_name_as_listed": union}
            notes = "listed on the DC portal union list (no UP portal links there); office contacts not collected (UP portals list elected representatives)"
            k = _union_key(base)
            on = [en for en, (_, txt) in pages.items() if k in txt]
            up = cur_up
            if cur_up is None:
                ex["upazila_on_dc_list"] = None
                if len(on) == 1:
                    up = on[0]
                    notes += "; the DC list gives no upazila for this row; upazila from the %s upazila portal's union page" % up
                    ex["upazila_from"] = pages[up][0]
                else:
                    notes += "; the DC list gives no upazila for this row and no single upazila portal lists it: upazila left empty"
            elif cur_up in pages and k not in pages[cur_up][1] and len(on) == 1:
                ex["upazila_on_dc_list"] = cur_up
                up = on[0]
                notes += ("; the DC list's %s cell spans this row, but the %s upazila portal does not list it and the %s upazila "
                          "portal's union page does: upazila from there" % (cur_up, cur_up, up))
                ex["upazila_from"] = pages[up][0]
            add({"source_key": SOURCE_KEY, "source_id": "up:%s:%s" % (up or "-", base),
                 "name_bn": "%s ইউনিয়ন পরিষদ" % base, "category_key": "government.union_parishad",
                 "district_en": HEAD, "upazila_en": up or "", "website": "", "ownership": "public",
                 "extra_json": json.dumps({k2: v for k2, v in ex.items() if v != ""}, ensure_ascii=False, separators=(",", ":")),
                 "source_url": url, "notes": notes})


if __name__ == "__main__":
    main()
