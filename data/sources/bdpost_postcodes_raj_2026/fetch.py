#!/usr/bin/env python3
"""Bangladesh Post postcode booklet (scanned PDF on post.rajshahi.gov.bd): post offices of Rajshahi Division with postcodes.

Re-runnable: python3 fetch.py [--division rajshahi|rangpur] [--out DIR]  (stdlib + requests; default: Rajshahi into this
folder, DIVISIONS.md). Optional: ELAKA_CACHE=<dir> caches pages."""
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
    r = get(url)
    if r is None or r.status_code != 200:
        print("  !", r.status_code if r is not None else "ERR", url, file=sys.stderr)
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


# --- division selection (data/sources/DIVISIONS.md) ---------------------------------------------------------
import argparse
DIVISION_CODES = {"rajshahi": "raj", "rangpur": "rang", "dhaka": "dhk", "chattogram": "ctg", "khulna": "khl",
                  "barishal": "bar", "sylhet": "syl", "mymensingh": "mym"}


def division_setup(here, base_key, configured, extra_args=()):
    """Parse --division/--out -> (args, out_dir, source_key). Rajshahi (default) keeps this folder and key; another
    division writes to its own folder named per DIVISIONS.md and never touches the Rajshahi files."""
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().split("\n")[0])
    ap.add_argument("--division", default="rajshahi", choices=list(DIVISION_CODES))
    ap.add_argument("--out", help="output folder (default: this folder for rajshahi, the division's own folder otherwise)")
    for name, kw in extra_args:
        ap.add_argument(name, **kw)
    args = ap.parse_args()
    if args.division not in configured:
        ap.error("division %r is not configured in this collector yet (configured: %s)" % (args.division, ", ".join(configured)))
    here = os.path.abspath(str(here))
    folder = os.path.basename(here)
    if args.division == "rajshahi":
        name, key = folder, base_key
    else:
        code = DIVISION_CODES[args.division]
        name = folder.replace("_raj_", "_%s_" % code) if "_raj_" in folder else "%s_%s" % (folder, args.division)
        key = base_key.replace("_RAJ_", "_%s_" % code.upper()) if "_RAJ_" in base_key else "%s_%s" % (base_key, args.division.upper())
    out = os.path.abspath(args.out) if args.out else (here if args.division == "rajshahi" else os.path.join(os.path.dirname(here), name))
    if args.division != "rajshahi" and out == here:
        ap.error("refusing to write another division's output into the Rajshahi folder")
    os.makedirs(out, exist_ok=True)
    return args, out, key
# --- end division selection ---------------------------------------------------------------------------------

# --- BDPOST_POSTCODES_RAJ_2026 ------------------------------------------------------------------------------
# Bangladesh Post "পোস্ট কোড" booklet, published as a scanned PDF (no text layer) on the Rajshahi DPMG portal
# (post.rajshahi.gov.bd -> "পোস্ট কোডসমূহ"). bdpost.gov.bd itself publishes no post-office list (its "পোস্টকোড" menu
# links to ekdak.com). The Rajshahi Division pages (booklet pp. 21-23) were transcribed by hand from the page images
# because the PDF has no usable text; fetch.py re-downloads the PDF, checks that it is still the transcribed file
# (sha256) and writes the CSV from the transcription below. If the hash changes, re-check the transcription.
SOURCE_KEY = "BDPOST_POSTCODES_RAJ_2026"
OUT = os.path.dirname(os.path.abspath(__file__))
PAGE_URL = "http://post.rajshahi.gov.bd/pages/static-pages/697f894d35ce18e1c06b96af"
PDF_URL = ("https://objectstorage.ap-dcc-gazipur-1.oraclecloud15.com/n/axvjbnqprylg/b/V2Ministry/o/"
           "office-post-rajshahi/2024/12/e548300c14de4897aa9516b65816e29f.pdf")
PDF_SHA256 = "93f5e6649a8881096262e05a19f15e69c8332158da22416ec9222182e26042e1"
TYPES = {"হেড অফিস": ("HO", "Head Post Office"), "জিপিও": ("GPO", "General Post Office"),
         "ইউ, পি, ও": ("UPO", "Upazila Post Office"), "টি, এস, ও": ("TSO", "Town Sub Post Office"),
         "টি. এস, ও": ("TSO", "Town Sub Post Office"), "ই, ডি, এস, ও": ("EDSO", "Extra-Departmental Sub Post Office"),
         "আর, এস, ই, ডি, এস, ও": ("EDSO", "Extra-Departmental Sub Post Office"), "এস, ও": ("SO", "Sub Post Office")}

# district, upazila (postal group as printed: the parent upazila post office / thana note), name as printed, postcode, booklet page
T = """
Rajshahi||রাজশাহী জিপিও|6000|21|Rajshahi city; printed as the section heading "রাজশাহী জিপিও ৬০০০"
Rajshahi||ঘোড়ামারা হেড অফিস|6100|21|Rajshahi city
Rajshahi||রাজশাহী কোর্ট টি, এস, ও|6201|21|Rajshahi city ("রাজশাহী শহর ও রাজশাহী জেলার বাকী অংশ 6200-6290")
Rajshahi||রাজশাহী ক্যান্টনমেন্ট টি, এস, ও|6202|21|Rajshahi city
Rajshahi||সপুরা টি, এস, ও|6203|21|Rajshahi city
Rajshahi||কাজলা টি, এস, ও|6204|21|Rajshahi city
Rajshahi||রাজশাহী বিশ্ববিদ্যালয় (এল, এস, জি) টি, এস, ও|6205|21|Rajshahi city
Rajshahi||বিনোদপুর বাজার টি, এস, ও|6206|21|Rajshahi city
Rajshahi||পদ্মা আবাসিক টি, এস, ও|6207|21|Rajshahi city
Rajshahi|Paba|ললিতগঞ্জ ইউ, পি, ও|6210|21|printed "(পবা থানা)"
Rajshahi|Paba|রাজশাহী সুগার মিলস এস, ও|6211|21|
Rajshahi|Paba|শ্যামপুর ই, ডি, এস, ও|6212|21|
Rajshahi|Paba|নওহাটা বাজার এস, ও|6213|21|
Rajshahi|Mohanpur|খোদ মোহনপুর ইউ, পি, ও|6220|21|printed "(মেহনপুর থানা)" [sic]
Rajshahi|Tanore|তানোর ইউ, পি, ও|6230|21|
Rajshahi|Durgapur|দুর্গাপুর ইউ, পি, ও|6240|21|
Rajshahi|Bagmara|ভবানীগঞ্জ ইউ, পি, ও|6250|21|printed "(বাঘমারা থানা)"
Rajshahi|Bagmara|তাহের পুর এস, ও|6251|21|
Rajshahi|Puthia|পুটিয়া ইউ, পি, ও|6260|21|spelt "পুটিয়া" in the booklet
Rajshahi|Charghat|চারঘাট ইউ, পি, ও|6270|21|
Rajshahi|Charghat|সারদা এস, ও|6271|21|
Rajshahi|Bagha|বাঘা ইউ, পি, ও|6280|21|
Rajshahi|Bagha|আরানী ই, ডি, এস, ও|6281|21|
Rajshahi|Godagari|গোদাগাড়ী ইউ, পি, ও|6290|21|
Rajshahi|Godagari|প্রেমতলী ই, ডি, এস, ও|6291|21|
Chapainawabganj|Chapainawabganj Sadar|চাঁপাই নবাবগঞ্জ হেড অফিস|6300|21|
Chapainawabganj|Chapainawabganj Sadar|রাজারামপুর ই, ডি, এস, ও|6301|21|
Chapainawabganj|Chapainawabganj Sadar|রামচন্দ্রপুর এস, ও|6302|21|
Chapainawabganj|Chapainawabganj Sadar|আমনুরা এস, ও|6303|21|
Chapainawabganj|Nachole|নাচোল ইউ, পি, ও|6310|21|
Chapainawabganj|Nachole|মন্ডুমালা হাট ই, ডি, এস, ও|6311|21|
Chapainawabganj|Gomastapur|রোহনপুর ইউ, পি, ও|6320|21|printed "(গোমস্তাপুর থানা)"
Chapainawabganj|Gomastapur|গোমস্তাপুর এস, ও|6321|21|
Chapainawabganj|Bholahat|ভোলাহাট ইউ, পি, ও|6330|21|
Chapainawabganj|Shibganj|শিবগঞ্জ ইউ, পি, ও|6340|21|
Chapainawabganj|Shibganj|কানসার্ট এস, ও|6341|21|
Chapainawabganj|Shibganj|মনাকশা এস, ও|6342|21|
Bogura|Bogura Sadar|বগুড়া হেড অফিস|5800|21|
Bogura|Bogura Sadar|বগুড়া ক্যান্টনমেন্ট এস, ও|5801|21|
Bogura|Shibganj|শিবগঞ্জ ইউ, পি, ও|5810|21|
Bogura|Gabtali|গাবতলী ইউ, পি, ও|5820|21|
Bogura|Gabtali|সুখানপুকুর এস, ও|5821|21|
Bogura|Sonatala|সোনাতলা ইউ, পি, ও|5826|21|
Bogura|Sariakandi|সারিয়াকান্দি ইউ, পি, ও|5830|21|
Bogura|Sariakandi|চন্দন বাইশা এস, ও|5831|21|
Bogura|Sherpur|শেরপুর ইউ, পি, ও|5840|21|
Bogura|Sherpur|চান্দাই কোনা এস, ও|5841|21|
Bogura|Sherpur|পল্লী উন্নয়ন একাডেমী এস, ও|5842|21|
Bogura|Dhunat|ধুনট ইউ, পি, ও|5850|21|
Bogura|Dhunat|গোঁসাইবাড়ী ই, ডি, এস, ও|5851|21|
Bogura|Nandigram|নন্দীগ্রাম ইউ, পি, ও|5860|21|
Bogura|Kahaloo|কাহালু ইউ, পি, ও|5870|21|
Bogura|Dupchanchia|দুপ চাচিয়া ইউ, পি, ও|5880|21|
Bogura|Dupchanchia|তালোরা এস, ও|5881|21|
Bogura|Adamdighi|আদমদীঘি ইউ, পি, ও|5890|21|
Bogura|Adamdighi|সান্তাহার (এল, এস, জি) এস, ও|5891|21|
Bogura|Adamdighi|নশরৎপুর এস, ও|5892|21|
Joypurhat|Joypurhat Sadar|জয়পুরহাট হেড অফিস|5900|21|
Joypurhat|Panchbibi|পাঁচবিবি ইউ, পি, ও|5910|21|
Joypurhat|Khetlal|ক্ষেতলাল ইউ, পি, ও|5920|21|
Joypurhat|Kalai|কালাই ইউ, পি, ও|5930|21|
Joypurhat|Akkelpur|আক্কেলপুর ইউ, পি, ও|5940|21|
Joypurhat|Akkelpur|জামালগঞ্জ এস, ও|5941|21|
Joypurhat|Akkelpur|তিলকপুর এস, ও|5942|21|
Natore|Natore Sadar|নাটোর হেড অফিস|6400|22|
Natore|Natore Sadar|দিঘাপাতিয়া এস, ও|6401|22|
Natore|Natore Sadar|বৈদ্যবেল ঘরিয়া ই, ডি, এস, ও|6402|22|
Natore|Natore Sadar|মাধনগর এস, ও|6403|22|
Natore|Bagatipara|লক্ষণ ইউ, পি, ও|6410|22|printed "(বাগতিপাড়া থানা)"
Natore|Lalpur|গোপালপুর ইউ, পি, ও|6420|22|printed "(লালপুর থানা)"
Natore|Lalpur|লালপুর এস, ও|6421|22|
Natore|Lalpur|আবদুলপুর ই, ডি, এস, ও|6422|22|
Natore|Baraigram|হারোয়া ইউ, পি, ও|6430|22|printed "(বড়াইগ্রাম থানা)"
Natore|Baraigram|দয়ারামপুর এস, ও|6431|22|
Natore|Baraigram|বড়াইগ্রাম ই, ডি, এস, ও|6432|22|
Natore|Baraigram|আহম্মদপুর বাজার এস, ও|6433|22|
Natore|Gurudaspur|হাটগুরুদাসপুর ইউ, পি, ও|6440|22|printed "(গুরুদাসপুর থানা)"
Natore|Singra|সিংরা ইউ, পি, ও|6450|22|
Naogaon|Naogaon Sadar|নওগাঁ হেড অফিস|6500|22|
Naogaon|Naogaon Sadar|নওগাঁ কোর্ট টি, এস, ও|6501|22|
Naogaon|Manda|প্রসাদপুর ইউ, পি, ও|6510|22|printed "(মান্দা থানা)"
Naogaon|Manda|মান্দা এস, ও|6511|22|
Naogaon|Manda|বলিহার ই, ডি, এস, ও|6512|22|
Naogaon|Niamatpur|নিয়ামতপুর ইউ, পি, ও|6520|22|
Naogaon|Mahadebpur|মহাদেবপুর ইউ, পি, ও|6530|22|
Naogaon|Patnitala|পত্নীতলা ইউ, পি, ও|6540|22|
Naogaon|Porsha|নিতপুর ইউ, পি, ও|6550|22|printed "(পোরসা থানা)"
Naogaon|Porsha|পোরসা ই, ডি, এস, ও|6551|22|
Naogaon|Porsha|পাংগুরিয়া ই, ডি, এস, ও|6552|22|
Naogaon|Sapahar|সাপাহার ইউ, পি, ও|6560|22|
Naogaon|Sapahar|মধুইল এস, ও|6561|22|
Naogaon|Badalgachhi|বদলগাছি ইউ, পি, ও|6570|22|
Naogaon|Dhamoirhat|ধামুইরহাট ইউ, পি, ও|6580|22|
Naogaon|Raninagar|রানীনগর ইউ, পি, ও|6590|22|
Naogaon|Raninagar|কাশিমপুর এস, ও|6591|22|
Naogaon|Atrai|আহসানগঞ্জ ইউ, পি, ও|6596|22|printed "(আত্রাই থান)" [sic]
Naogaon|Atrai|বান্দাই খাড়া এস, ও|6597|22|
Pabna|Pabna Sadar|পাবনা হেড অফিস|6600|22|
Pabna|Pabna Sadar|কেলিকো কটন মিলস্ এস, ও|6601|22|
Pabna|Pabna Sadar|হেমায়েতপুর এস, ও|6602|22|
Pabna|Atgharia|দেবত্তর ইউ, পি, ও|6610|22|printed "(আটঘরিয়া থানা)"
Pabna|Ishwardi|ঈশ্বরদী ইউ, পি, ও|6620|22|
Pabna|Ishwardi|ধাপারী ই, ডি, এস, ও|6621|22|
Pabna|Ishwardi|পাকশী এস, ও|6622|22|
Pabna|Ishwardi|রাজাপুর হাট এস, ও|6623|22|
Pabna|Chatmohar|চাটমোহর ইউ, পি, ও|6630|22|
Pabna|Bhangura|ভাংগুরা ইউ, পি, ও|6640|22|
Pabna|Faridpur|বনওয়ারীনগর ইউ, পি, ও|6650|22|printed "(ফরিদপুর থানা)"
Pabna|Sujanagar|সুজানগর ইউ, পি, ও|6660|22|
Pabna|Sujanagar|সাগরকান্দি এস, ও|6661|22|
Pabna|Santhia|সাঁথিয়া ইউ, পি, ও|6670|22|
Pabna|Bera|বেড়া ইউ, পি, ও|6680|22|
Pabna|Bera|নাকালিয়া এস, ও|6681|22|
Pabna|Bera|কাশিনাথপুর এস, ও|6682|22|
Pabna|Bera|পুরান ভারেংগা এস, ও|6683|22|
Sirajganj|Sirajganj Sadar|সিরাজগঞ্জ হেড অফিস|6700|22|
Sirajganj|Sirajganj Sadar|রায়পুর এস, ও|6701|22|
Sirajganj|Sirajganj Sadar|রশিদাবাদ ই, ডি, এস, ও|6702|22|
Sirajganj|Kazipur|কাজিপুর ইউ, পি, ও|6710|22|
Sirajganj|Kazipur|সুভগাছা ই, ডি, এস, ও|6711|22|
Sirajganj|Kazipur|গান্দাইল এস, ও|6712|22|
Sirajganj|Rayganj|ধানগড়া ইউ, পি, ও|6720|22|printed "(রায়গঞ্জ থানা)"
Sirajganj|Rayganj|মলোংগা এস, ও|6721|22|
Sirajganj|Kamarkhanda|বৈদ্য জাম তৈল ইউ, পি, ও|6730|22|printed "(কামারখন্দ থানা)"
Sirajganj|Belkuchi|বেলকুচি ইউ, পি, ও|6740|22|
Sirajganj|Belkuchi|সোহাগপুর এস, ও|6741|22|
Sirajganj|Belkuchi|রাজাপুর ই, ডি, এস, ও|6742|22|
Sirajganj|Chouhali|এনায়েতপুর ই, ডি, এস, ও|6751|22|booklet: Chauhali upazila HQ office (6750) is listed under Tangail district
Sirajganj|Chouhali|স্থল এস, ও|6752|22|booklet: Chauhali upazila HQ office (6750) is listed under Tangail district
Sirajganj|Ullapara|উল্লাপাড়া ইউ, পি, ও|6760|23|
Sirajganj|Ullapara|উল্লাপাড়া আর, এস, ই, ডি, এস, ও|6761|23|
Sirajganj|Ullapara|লাহিড়ী মোহনপুর এস, ও|6762|23|
Sirajganj|Ullapara|সলপ ই, ডি, এস, ও|6763|23|
Sirajganj|Shahjadpur|শাহজাদপুর ইউ, পি, ও|6770|23|
Sirajganj|Shahjadpur|পোরজনা ই, ডি, এস, ও|6771|23|
Sirajganj|Shahjadpur|জামিরতা এস, ও|6772|23|
Sirajganj|Shahjadpur|কৈজুরী হাট ই, ডি, এস, ও|6773|23|
Sirajganj|Tarash|তারাশ ইউ, পি, ও|6780|23|
"""

# Rangpur Division: the same booklet (the old "রাজশাহী রিজিয়ন ৫০০০-৬৯৯৯" includes the Rangpur districts). Booklet p. 19
# (PDF page 11, right column: Panchagarh, Thakurgaon), p. 20 (PDF page 12, left half: Dinajpur, Nilphamari, Rangpur,
# Lalmonirhat, Kurigram) and p. 21 (PDF page 12, first column: Gaibandha), transcribed by hand from the page images in
# raw/. Upazila = the postal group as printed (parent upazila post office or printed thana note); "[inferred]" marks a
# group whose upazila is not printed and was taken from the office's known location.
T_RANGPUR = """
Panchagarh|Panchagarh Sadar|পঞ্চগড় হেড অফিস|5000|19|
Panchagarh|Boda|বোদা ইউ, পি, ও|5010|19|
Panchagarh|Debiganj|দেবীগঞ্জ ইউ, পি, ও|5020|19|
Panchagarh|Tetulia|তেতুলিয়া ইউ, পি, ও|5030|19|
Panchagarh|Atwari|ছোট ডাব ইউ, পি, ও|5040|19|printed "(থানা আটওয়ারী)"
Panchagarh|Atwari|মির্জাপুর এস, ও|5041|19|
Thakurgaon|Thakurgaon Sadar|ঠাকুরগাঁও হেড অফিস|5100|19|
Thakurgaon|Thakurgaon Sadar|ঠাকুরগাঁও রোড এস, ও|5101|19|
Thakurgaon|Thakurgaon Sadar|শিবগঞ্জ এস, ও|5102|19|
Thakurgaon|Thakurgaon Sadar|রুহিয়া এস, ও|5103|19|
Thakurgaon|Pirganj|পীরগঞ্জ ইউ, পি, ও|5110|19|
Thakurgaon|Ranisankail|রানী সংকাইল ইউ, পি, ও|5120|19|spelt "রানী সংকাইল" in the booklet
Thakurgaon|Ranisankail|নেকমরদ ই, ডি, এস, ও|5121|19|
Thakurgaon|Haripur|জীবনপুর ইউ, পি, ও|5130|19|printed "(হরিপুর থানা)"
Thakurgaon|Baliadangi|বালিয়াডাংগী ইউ, পি, ও|5140|19|
Thakurgaon|Baliadangi|লাহিড়ী ই, ডি, এস, ও|5141|19|
Dinajpur|Dinajpur Sadar|দিনাজপুর হেড অফিস|5200|20|district heading printed "৫২০০-৫২৯০"
Dinajpur|Dinajpur Sadar|দিনাজপুর রাজবাড়ী ই, ডি, এস, ও|5201|20|
Dinajpur|Biral|বিরল ইউ, পি, ও|5210|20|
Dinajpur|Bochaganj|সেতাবগঞ্জ ইউ, পি, ও|5216|20|[inferred] Setabganj is the Bochaganj upazila seat (thana not printed)
Dinajpur|Birganj|বীরগঞ্জ ইউ, পি, ও|5220|20|
Dinajpur|Kaharole|মহারাজগঞ্জ ইউ, পি, ও|5226|20|printed "(কাহালোর থানা)"
Dinajpur|Khansama|খানসামা ইউ, পি, ও|5230|20|
Dinajpur|Khansama|পাকের হাট ই, ডি, এস, ও|5231|20|
Dinajpur|Chirirbandar|চিরির বন্দর ইউ, পি, ও|5240|20|
Dinajpur|Chirirbandar|রানীর বন্দর ই, ডি, এস, ও|5241|20|
Dinajpur|Parbatipur|পার্বতীপুর ইউ, পি, ও|5250|20|
Dinajpur|Phulbari|ফুলবাড়ী ইউ, পি, ও|5260|20|
Dinajpur|Birampur|বিরামপুর ইউ, পি, ও|5266|20|
Dinajpur|Hakimpur|বাংলা হিলি ইউ, পি, ও|5270|20|printed "(হাকিমপুর থানা)"
Dinajpur|Nawabganj|নবাবগঞ্জ ইউ, পি, ও|5280|20|
Dinajpur|Nawabganj|দাউদপুর এস, ও|5281|20|
Dinajpur|Nawabganj|গোপালপুর এস, ও|5282|20|
Dinajpur|Ghoraghat|ওসমানপুর ইউ, পি, ও|5290|20|printed "(ঘোড়াঘাট থানা)"
Dinajpur|Ghoraghat|ঘোড়াঘাট এস, ও|5291|20|
Nilphamari|Nilphamari Sadar|নীলফামারী হেড অফিস|5300|20|
Nilphamari|Nilphamari Sadar|নীলফামারী সুগার মিলস্ ই, ডি, এস, ও|5301|20|
Nilphamari|Saidpur|সৈয়দপুর ইউ, পি, ও|5310|20|
Nilphamari|Saidpur|সৈয়দপুর উপ শহর এস, ও|5311|20|
Nilphamari|Kishoreganj|কিশোরীগঞ্জ ইউ, পি, ও|5320|20|spelt "কিশোরীগঞ্জ" in the booklet
Nilphamari|Jaldhaka|জল ঢাকা ইউ, পি, ও|5330|20|
Nilphamari|Domar|ডোমার ইউ, পি, ও|5340|20|
Nilphamari|Domar|চিলাহাটি এস, ও|5341|20|printed unindented after Domar UPO
Nilphamari|Dimla|ডিমলা ইউ, পি, ও|5350|20|
Nilphamari|Dimla|ঘগা খড়িবাড়ী এস, ও|5351|20|
Rangpur||রংপুর হেড অফিস|5400|20|Rangpur city
Rangpur||রংপুর উপ-শহর এস, ও|5401|20|Rangpur city
Rangpur||আলমনগর টি, এস, ও|5402|20|Rangpur city
Rangpur||মাহিগঞ্জ টি, এস, ও|5403|20|Rangpur city
Rangpur||রংপুর ক্যাডেট কলেজ টি, এস, ও|5404|20|Rangpur city
Rangpur||রংপুর কারমাইকেল টি এস ও|5405|20|Rangpur city
Rangpur|Gangachara|গংগা চড়া ইউ, পি, ও|5410|20|
Rangpur|Taraganj|তারাগঞ্জ ইউ, পি, ও|5420|20|
Rangpur|Badarganj|বদরগঞ্জ ইউ, পি, ও|5430|20|
Rangpur|Badarganj|শ্যামপুর এস, ও|5431|20|
Rangpur|Kaunia|কাউনিয়া ইউ, পি, ও|5440|20|
Rangpur|Kaunia|হারাগাছ এস, ও|5441|20|
Rangpur|Pirgachha|পীরগাছা ইউ, পি, ও|5450|20|
Rangpur|Mithapukur|মিঠাপুকুর ইউ, পি, ও|5460|20|
Rangpur|Pirganj|পীরগঞ্জ ইউ, পি, ও|5470|20|
Lalmonirhat|Lalmonirhat Sadar|লালমনিরহাট হেড অফিস|5500|20|
Lalmonirhat|Lalmonirhat Sadar|মোগলহাট এস, ও|5501|20|
Lalmonirhat|Lalmonirhat Sadar|কূলাঘাট এস, ও|5402|20|printed "৫৪০২" inside the Lalmonirhat block (5500-5599), the same code as আলমনগর টি, এস, ও (Rangpur); probably a misprint of 5502 — kept as printed
Lalmonirhat|Aditmari|আদিতমারী ইউ, পি, ও|5510|20|
Lalmonirhat|Kaliganj|তুষ ভান্ডার ইউ, পি, ও|5520|20|[inferred] Tushbhandar is the Kaliganj upazila seat (thana not printed)
Lalmonirhat|Hatibandha|হাতীবান্দা ইউ, পি, ও|5530|20|spelt "হাতীবান্দা" in the booklet
Lalmonirhat|Patgram|পাটগ্রাম ইউ, পি, ও|5540|20|
Lalmonirhat|Patgram|বাউরা এস, ও|5541|20|
Lalmonirhat|Patgram|বুড়ীমারী এস, ও|5542|20|
Kurigram|Kurigram Sadar|কুড়িগ্রাম হেড অফিস|5600|20|
Kurigram|Kurigram Sadar|পান্ডুল এস, ও|5601|20|
Kurigram|Rajarhat|রাজারহাট ইউ, পি, ও|5610|20|
Kurigram|Rajarhat|নাজিমখান এস, ও|5611|20|
Kurigram|Ulipur|উলিপুর ইউ, পি, ও|5620|20|
Kurigram|Ulipur|বজরাহাট এস, ও|5621|20|
Kurigram|Chilmari|চিলমারী ইউ, পি, ও|5630|20|
Kurigram|Chilmari|জোড়গাছ এস, ও|5631|20|
Kurigram|Raomari|রৌমারী ইউ, পি, ও|5640|20|
Kurigram|Char Rajibpur|রাজিবপুর ইউ, পি, ও|5650|20|
Kurigram|Nageshwari|নাগেশ্বর ইউ, পি, ও|5660|20|spelt "নাগেশ্বর" in the booklet
Kurigram|Bhurungamari|ভূরুংগামারী ইউ, পি, ও|5670|20|
Kurigram|Phulbari|ফুলবাড়ী ইউ, পি, ও|5680|20|
Gaibandha|Gaibandha Sadar|গাইবান্ধা হেড অফিস|5700|21|
Gaibandha|Sadullapur|সাদুল্লাপুর ইউ, পি, ও|5710|21|
Gaibandha|Sadullapur|নলডাংগা এস, ও|5711|21|
Gaibandha|Sundarganj|সুন্দরগঞ্জ ইউ, পি, ও|5720|21|
Gaibandha|Sundarganj|বামনডাঙগা এস, ও|5721|21|
Gaibandha|Palashbari|পলাশবাড় ইউ, পি, ও|5730|21|spelt "পলাশবাড়" in the booklet
Gaibandha|Gobindaganj|গোবিন্দগঞ্জ ইউ, পি, ও|5740|21|
Gaibandha|Gobindaganj|মহিমাগঞ্জ এস, ও|5741|21|
Gaibandha|Saghata|বোনারপাড়া ইউ, পি, ও|5750|21|[inferred] Bonarpara is in Saghata upazila; its group includes সাঘাটা এস, ও (thana not printed)
Gaibandha|Saghata|সাঘাটা এস, ও|5751|21|
Gaibandha|Phulchhari|ফুলছড়ি ইউ, পি, ও|5760|21|
Gaibandha|Phulchhari|ভরতখালী এস, ও|5761|21|
"""
DIVISION, HEAD = "rajshahi", "Rajshahi"
BY_DIV = {"rajshahi": dict(T=None, raw=["raw/postcode_booklet_pp21.png", "raw/postcode_booklet_pp22-23.png"]),
          "rangpur": dict(T=T_RANGPUR, raw=["raw/postcode_booklet_pp18-19.png", "raw/postcode_booklet_pp20-21.png"])}


def otype(name):
    for k in sorted(TYPES, key=len, reverse=True):
        if name.endswith(k) or (k in name and k in ("হেড অফিস", "জিপিও")):
            return TYPES[k]
    return ("", "")


def main():
    global OUT, SOURCE_KEY, T, DIVISION, HEAD
    args, OUT, SOURCE_KEY = division_setup(OUT, SOURCE_KEY, list(BY_DIV))
    DIVISION, HEAD = args.division, args.division.capitalize()
    T = BY_DIV[DIVISION]["T"] or T
    if DIVISION != "rajshahi":  # this part of the booklet also prints the type without commas ("টি এস ও")
        TYPES.setdefault("টি এস ও", ("TSO", "Town Sub Post Office"))
    used = set()
    r = get(PDF_URL, timeout=180)
    pdf_ok, sha = None, None
    if r is not None and r.status_code == 200:
        sha = hashlib.sha256(r.content).hexdigest()
        pdf_ok = (sha == PDF_SHA256)
    if pdf_ok is False:
        print("WARNING: the published PDF changed (sha256 %s) — re-check the transcription" % sha, file=sys.stderr)
    places, facts = [], {}
    for line in T.strip().splitlines():
        dist, up, name, code, page, note = (line.split("|") + [""])[:6]
        code_t, type_en = otype(name)
        notes = ["transcribed by hand from the scanned booklet page %s (PDF has no text layer)" % page]
        if note:
            notes.append(note)
        if not up:
            notes.append("inside %s city; upazila/thana not given" % HEAD)
        if DIVISION != "rajshahi" and "[inferred]" in note:
            notes[-1] = note.replace("[inferred] ", "upazila inferred: ")
        sid = "postcode:%s" % code
        if sid in used:  # a code printed twice (misprint): keep both rows, the second with the district in its id
            sid = "%s-%s" % (sid, dist.lower())
        used.add(sid)
        places.append({"source_key": SOURCE_KEY, "source_id": sid, "name_bn": nfc(name),
                       "category_key": "government.post_office", "district_en": dist, "upazila_en": up,
                       "operator": "বাংলাদেশ ডাক বিভাগ (Bangladesh Post Office)", "ownership": "public",
                       "extra_json": jdump({"postcode": code, "office_type": code_t, "office_type_en": type_en,
                                            "booklet_page": int(page), "upazila_is_postal_group": bool(up)}),
                       "source_url": PDF_URL, "notes": "; ".join(notes)})
        facts.setdefault((dist, up), 0)
        facts[(dist, up)] += 1
    write_csv(os.path.join(OUT, "places.csv"), PLACE_COLS, places)
    frows = []
    for (d, u), n in sorted(facts.items()):
        frows.append({"entity_level": "upazila" if u else "city", "entity_name_en": u or "%s City" % HEAD, "district_en": d,
                      "upazila_en": u, "fact": "post_offices_with_postcode", "value": n, "unit": "post offices",
                      "basis": "listed in Bangladesh Post postcode booklet (undated scan)", "year": "",
                      "source_key": SOURCE_KEY, "source_url": PDF_URL, "notes": "postal grouping as printed"})
    write_csv(os.path.join(OUT, "facts.csv"), FACT_COLS, frows)
    if DIVISION != "rajshahi":  # the Rajshahi SOURCE.json is maintained by hand; other divisions get theirs here
        import datetime
        mp = os.path.join(OUT, "SOURCE.json")
        m = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {
            "key": SOURCE_KEY, "division": DIVISION, "kind": "bdpost",
            "name": "Bangladesh Post postcode booklet — %s Division post offices (scan on post.rajshahi.gov.bd)" % HEAD,
            "organization": "বাংলাদেশ ডাক বিভাগ (Bangladesh Post Office) — DPMG Rajshahi Division portal",
            "source_type": "government_portal", "trust_level": 4, "urls": [PAGE_URL, PDF_URL], "accessed": None,
            "publication_date": None, "license": None, "license_url": None,
            "attribution": "বাংলাদেশ ডাক বিভাগ (Bangladesh Post Office) — DPMG Rajshahi Division portal"}
        m["accessed"] = datetime.date.today().isoformat()
        files = ["facts.csv", "places.csv"] + BY_DIV[DIVISION]["raw"]
        m["files"] = {f: sha256(os.path.join(OUT, f)) for f in files if os.path.exists(os.path.join(OUT, f))}
        with open(mp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(m, ensure_ascii=False, indent=2) + "\n")
    print(len(places), "post offices; pdf sha256", sha, file=sys.stderr)


if __name__ == "__main__":
    main()
