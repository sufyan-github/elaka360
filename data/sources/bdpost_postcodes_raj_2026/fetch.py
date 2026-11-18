#!/usr/bin/env python3
"""Bangladesh Post postcode booklet (scanned PDF on post.rajshahi.gov.bd): post offices of Rajshahi Division with postcodes.

Re-runnable: python3 fetch.py [--division rajshahi|rangpur|dhaka|chattogram|khulna|barishal|sylhet|mymensingh] [--out DIR]  (stdlib + requests; default: Rajshahi into this
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
# Dhaka Division: the same booklet. "ঢাকা রিজিয়ন ১০০০-২৯৯৯" p. 9 (PDF page 6, right half: Dhaka city and Dhaka district,
# Narayanganj), pp. 10-11 (PDF page 7: Narayanganj, Munshiganj, Narsingdi, Gazipur, Manikganj, Tangail), pp. 12-13 (PDF
# page 8: Tangail, Kishoreganj; the Mymensingh-Division districts on these pages are left out) and, in "খুলনা রিজিয়ন",
# pp. 24-25 (PDF page 14: Rajbari, Faridpur, Madaripur, Shariatpur, Gopalganj), transcribed by hand from the page images in
# raw/. Upazila = the postal group as printed; "[inferred]" as for Rangpur; an empty code = digits not legible in the scan.
T_DHAKA = """
Dhaka||ঢাকা জি, পি, ও|1000|9|Dhaka city; printed as the line "ঢাকা জি, পি, ও ১০০০"
Dhaka||ঢাকা সদর প্রধান ডাকঘর|1100|9|Dhaka city; printed as the line "ঢাকা সদর প্রধান ডাকঘর ১১০০"
Dhaka||ওয়ারী টি, এস, ও|1203|9|Dhaka city ("ঢাকা শহরের অন্যান্য বিলিকারী অফিস ১২০০-১২৯৯")
Dhaka||গেন্ডারিয়া টি, এস, ও|1204|9|Dhaka city
Dhaka||নিউমার্কেট টি, এস, ও|1205|9|Dhaka city
Dhaka||ঢাকা ক্যান্টনমেন্ট টি, এস, ও|1206|9|Dhaka city
Dhaka||মোহাম্মদপুর হাউজিং এস্টেট টি, এস, ও|1207|9|Dhaka city
Dhaka||ঢাকা পলিটেকনিক ইন্সটিটিউট টি, এস, ও|1208|9|Dhaka city
Dhaka||জিগাতলা টি, এস, ও|1209|9|Dhaka city
Dhaka||পোস্তা টি, এস, ও|1211|9|Dhaka city
Dhaka||গুলশান মডেল টাউন টি, এস, ও|1212|9|Dhaka city
Dhaka||বনানী টি, এস, ও|1213|9|Dhaka city
Dhaka||বাসাবো টি, এস, ও|1214|9|Dhaka city
Dhaka||তেজগাঁও টি, এস, ও|1215|9|Dhaka city
Dhaka||মিরপুর টি, এস, ও|1216|9|Dhaka city
Dhaka||শান্তি নগর টি, এস, ও|1217|9|Dhaka city
Dhaka||খিলগাঁও টি, এস, ও|1219|9|Dhaka city
Dhaka||বঙ্গভবন টি, এস, ও|1222|9|Dhaka city
Dhaka||সংসদ ভবন টি, এস, ও|1225|9|Dhaka city
Dhaka||খিলক্ষেত টি, এস, ও|1229|9|Dhaka city
Dhaka||উত্তরা মডেল টাউন টি, এস, ও|1230|9|Dhaka city
Dhaka||ধনিয়া টি, এস, ও|1236|9|Dhaka city
Dhaka|Keraniganj|কেরানীগঞ্জ ইউ, পি, ও|1310|9|
Dhaka|Keraniganj|ঢাকা জুট মিলস্ এস, ও|1311|9|
Dhaka|Keraniganj|আটি ই, ডি, এস, ও|1312|9|
Dhaka|Keraniganj|কলাতিয়া এস, ও|1313|9|
Dhaka|Nawabganj|নবাবগঞ্জ ইউ, পি, ও|1320|9|
Dhaka|Nawabganj|হাসনাবাদ এস, ও|1321|9|
Dhaka|Nawabganj|দাউদপুর এস,ও|1322|9|
Dhaka|Nawabganj|আগলা ই, ডি, এস, ও|1323|9|
Dhaka|Nawabganj|খালপার ই, ডি, এস, ও|1324|9|
Dhaka|Nawabganj|চুড়াইন এস, ও|1325|9|
Dhaka|Dohar|জয়পাড়া ইউ, পি, ও|1330|9|printed "(দোহার উপজেলা)"
Dhaka|Dohar|পালামগঞ্জ এস, ও|1331|9|
Dhaka|Dohar|নারিশা ই, ডি, এস ও|1332|9|
Dhaka|Dohar|মুকশেদপুর এস, ও|1333|9|
Dhaka|Savar|সাভার ইউ, পি, ও|1340|9|
Dhaka|Savar|ডাইরী ফার্ম এস, ও|1341|9|
Dhaka|Savar|জাহাঙ্গীর নগর বিশ্ববিদ্যালয় এস, ও|1342|9|
Dhaka|Savar|সাভার পি, এ, টি, সি, এস, ও|1343|9|
Dhaka|Savar|সাভার ক্যান্টনমেন্ট এস, ও|1344|9|
Dhaka|Savar|শিমুলিয়া এস, ও|1345|9|
Dhaka|Savar|কাশেম কটন মিলস্ এস, ও|1346|9|
Dhaka|Savar|রাজফুলবাড়িয়া ই, ডি এস ও|1347|9|
Dhaka|Savar|আমিন বাজার ই ডি এস ও|1348|9|
Dhaka|Savar|ইপিজেড এস, ও|1349|9|
Dhaka|Dhamrai|ধামরাই ইউ, পি, ও|1350|9|
Dhaka|Dhamrai|কালামপুর ই, ডি,,এস ও|1351|9|
Dhaka||ডেমরা ইউ, পি, ও|1360|9|postal group ডেমরা (Demra thana, Dhaka city; not an upazila)
Dhaka||সারুলিয়া এস, ও|1361|9|postal group ডেমরা (Demra thana, Dhaka city; not an upazila)
Dhaka||মাতুয়াইল এস, ও|1362|9|postal group ডেমরা (Demra thana, Dhaka city; not an upazila)
Narayanganj|Narayanganj Sadar|নারায়নগঞ্জ হেড অফিস|1400|9|
Narayanganj|Bandar|বন্দর ইউ, পি, ও|1410|9|
Narayanganj|Bandar|ডি, সি, মিলস্ এস, ও|1411|9|
Narayanganj|Bandar|নবীগঞ্জ ই, ডি, এস, ও|1412|9|
Narayanganj|Bandar|বি, আই, ডি, সি এস, ও|1413|9|
Narayanganj|Bandar|মদনগঞ্জ এস, ও|1414|9|
Narayanganj|Narayanganj Sadar|ফতুল্লাহ ইউ, পি, ও|1420|9|[inferred] postal group ফতুল্লাহ (Fatullah thana, in Narayanganj Sadar upazila)
Narayanganj|Narayanganj Sadar|ফতুল্লাহ বাজার এস, ও|1421|9|[inferred] postal group ফতুল্লাহ (Fatullah thana, in Narayanganj Sadar upazila)
Narayanganj|Narayanganj Sadar|সিদ্দিরগঞ্জ পাওয়ার স্টেশন ইউ, পি, ও|1430|10|[inferred] postal group সিদ্দিরগঞ্জ (Siddhirganj thana, in Narayanganj Sadar upazila)
Narayanganj|Narayanganj Sadar|আদমজীনগর এস, ও|1431|10|[inferred] postal group সিদ্দিরগঞ্জ (Siddhirganj thana, in Narayanganj Sadar upazila)
Narayanganj|Narayanganj Sadar|এল, এন, মিলস্ এস, ও|1432|10|[inferred] postal group সিদ্দিরগঞ্জ (Siddhirganj thana, in Narayanganj Sadar upazila)
Narayanganj|Sonargaon|সোনারগাঁও ইউ, পি, ও|1440|10|
Narayanganj|Sonargaon|বড় নগর ই, ডি, এস, ও|1441|10|
Narayanganj|Sonargaon|বারদী এস, ও|1442|10|
Narayanganj|Araihazar|আড়াইহাজার ইউ, পি, ও|1450|10|
Narayanganj|Araihazar|গোপালদী এস, ও|1451|10|
Narayanganj|Rupganj|রুপগঞ্জ ইউ, পি, ও|1460|10|
Narayanganj|Rupganj|কাঞ্চন এস, ও|1461|10|
Narayanganj|Rupganj|ভুলতা ই,.ডি, এস, ও|1462|10|
Narayanganj|Rupganj|নাগরী ই, ডি, এস, ও|1463|10|
Narayanganj|Rupganj|মুড়াপাড়া এস, ও|1464|10|
Munshiganj|Munshiganj Sadar|মুন্সীগঞ্জ হেড অফিস|1500|10|
Munshiganj|Munshiganj Sadar|রিকাবী বাজার এস, ও|1501|10|
Munshiganj|Munshiganj Sadar|মিরকাদিম এস, ও|1502|10|
Munshiganj|Munshiganj Sadar|কাঠাখালি ই, ডি, এস, ও|1503|10|
Munshiganj|Gazaria|গজারিয়া ইউ, পি, ও|1510|10|
Munshiganj|Gazaria|হোসেনদী ই, ডি, এস, ও|1511|10|
Munshiganj|Gazaria|রসুলপুর ই, ডি, এস, ও||10|postcode not legible in the scan ("১৫" and two faint digits; listed after 1511)
Munshiganj|Tongibari|টংগীবাড়ী ইউ, পি, ও|1520|10|
Munshiganj|Tongibari|বেতকাহাট এস, ও|1521|10|
Munshiganj|Tongibari|বালিগাঁও ই, ডি, এস, ও|1522|10|
Munshiganj|Tongibari|বজ্রযোগীনী ই, ডি, এস, ও|1523|10|
Munshiganj|Tongibari|হাসাইল ই, ডি, এস, ও|1524|10|
Munshiganj|Tongibari|দিঘীরপাড় এস, ও|1525|10|
Munshiganj|Tongibari|পুরা ই, ডি, এস. ও|1527|10|
Munshiganj|Lohajang|লৌহজং ইউ, পি, ও|1530|10|
Munshiganj|Lohajang|কোরহাটি ই, ডি, এস, ও|1531|10|
Munshiganj|Lohajang|হলদিয়া এস ও|1532|10|
Munshiganj|Lohajang|হরিদিয়া ই, ডি, এস ও|1533|10|
Munshiganj|Lohajang|গৌরগঞ্জ ই, ডি, এস ও|1534|10|
Munshiganj|Lohajang|মেদিনী মন্ডল ই, ডি, এস ও|1535|10|
Munshiganj|Sirajdikhan|সিরাজদীখান ইউ, পি, ও|1540|10|
Munshiganj|Sirajdikhan|কোলা এস, ও|1541|10|
Munshiganj|Sirajdikhan|ইছাপুর এস, ও|1542|10|
Munshiganj|Sirajdikhan|মালখা নগর এস, ও|1543|10|
Munshiganj|Sirajdikhan|শেখেরনগর এস, ও|1544|10|
Munshiganj|Sreenagar|শ্রীনগর ইউ, পি, ও|1550|10|
Munshiganj|Sreenagar|বাড়ীখাল ই, ডি এস, ও|1551|10|
Munshiganj|Sreenagar|মাজপাড়া এস, ও|1552|10|
Munshiganj|Sreenagar|হাষাড়া এস, ও|1553|10|
Munshiganj|Sreenagar|কোলাপাড়া ই, ডি, এস, ও|1554|10|
Munshiganj|Sreenagar|কুমারভোগ ই, ডি এস, ও|1555|10|
Munshiganj|Sreenagar|বাঘড়া ই, ডি, এস, ও|1557|10|
Munshiganj|Sreenagar|ভাগ্যকুল এস, ও|1556|10|
Narsingdi|Narsingdi Sadar|নরসিংদী হেড অফিস|1600|10|
Narsingdi|Narsingdi Sadar|ইউ এম, সি, জুট মিলস্ এস, ও|1601|10|
Narsingdi|Narsingdi Sadar|নরসিংদী কলেজ ই, ডি, এস, ও|1602|10|
Narsingdi|Narsingdi Sadar|পাঁচদোনা এস, ও|1603|10|
Narsingdi|Narsingdi Sadar|মাধবদী এস, ও|1604|10|
Narsingdi|Narsingdi Sadar|করিমপুর এস, ও|1605|10|
Narsingdi|Palash|পলাশ ইউ, পি, ও|1610|10|
Narsingdi|Palash|ঘোড়াশাল ইউরিয়া ফ্যাক্টরী এস, ও|1611|10|
Narsingdi|Palash|চর সিন্ধুর ই, ডি, এস, ও|1612|10|
Narsingdi|Palash|ঘোড়াশাল এস, ও|1613|10|
Narsingdi|Shibpur|শিবপুর ইউ, পি,ও|1620|10|
Narsingdi|Raipura|রায়পুরা ইউ, পি, ও|1630|10|
Narsingdi|Raipura|বাজার হাসনাবাদ ই, ডি, এস, ও|1631|10|
Narsingdi|Raipura|রাধাগঞ্জ বাজার ই, ডি, এস, ও|1632|10|
Narsingdi|Belabo|বেলাবো ইউ, পি,ও|1640|10|
Narsingdi|Monohardi|মনোহরদী ইউ, পি, ও|1650|10|
Narsingdi|Monohardi|হাতির দিয়া এস, ও|1651|10|
Narsingdi|Monohardi|কাটাবাড়ীয়া এস, ও|1652|10|
Gazipur|Gazipur Sadar|জয়দেবপুর হেড অফিস (গাজীপুর)|1700|10|
Gazipur|Gazipur Sadar|বি, আর, আর. আই এস, ও|1701|10|
Gazipur|Gazipur Sadar|চন্দনা ই, ডি, এস, ও|1702|10|
Gazipur|Gazipur Sadar|বি, ও , এফ, এস, ও|1703|10|
Gazipur|Gazipur Sadar|জাতীয় বিশ্ববিদ্যালয় এস, ও|1704|10|
Gazipur|Gazipur Sadar|ই. প. সা এস ও|1706|10|
Gazipur|Gazipur Sadar|মন্নু নগর ইউ, পি, ও|1710|10|[inferred] printed "(টংগী থানা)"; Tongi is in Gazipur Sadar upazila
Gazipur|Gazipur Sadar|নিশাত নগর এস, ও|1711|10|[inferred] postal group মন্নু নগর (টংগী থানা); Tongi is in Gazipur Sadar upazila
Gazipur|Gazipur Sadar|এরশাদনগর এস, ও|1712|10|[inferred] postal group মন্নু নগর (টংগী থানা); Tongi is in Gazipur Sadar upazila
Gazipur|Kaliganj|কালিগঞ্জ ইউ, পি, ও|1720|11|
Gazipur|Kaliganj|পূবাইল ই, ডি, এস, ও|1721|11|
Gazipur|Kaliganj|সান্তানপাড়া ই, ডি, এস, ও|1722|11|
Gazipur|Kaliganj|ভাওয়াল জামালপুর ই, ডি, এস, ও|1723|11|
Gazipur|Kapasia|কাপাসিয়া ইউ, পি,ও|1730|11|
Gazipur|Sreepur|শ্রীপুর ইউ, পি, ও|1740|11|
Gazipur|Sreepur|রাজেন্দ্রপুর ই, ডি, এস, ও|1741|11|
Gazipur|Sreepur|রাজেন্দ্রপুর ক্যান্ট এস, ও|1742|11|
Gazipur|Sreepur|বরমী এস, ও|1743|11|
Gazipur|Sreepur|সাতখামাইর ই, ডি, এস, ও|1744|11|
Gazipur|Sreepur|কাওরাইদ এস, ও|1745|11|
Gazipur|Sreepur|বশেমুর কৃষি এস, ও|1747|11|
Gazipur|Sreepur|বাউবি এস ও|1748|11|
Gazipur|Kaliakair|কালিয়াকৈর ইউ, পি, ও|1750|11|
Gazipur|Kaliakair|সফিপুর এ, টি, সি|1751|11|office type printed "এ, টি, সি" (not one of the booklet's office types)
Manikganj|Manikganj Sadar|মানিকগঞ্জ হেড অফিস|1800|11|
Manikganj|Manikganj Sadar|মানিকগঞ্জ বাজার ই, ডি, এস, ও|1801|11|
Manikganj|Manikganj Sadar|গড়পাড়া ই, ডি, এস, ও|1802|11|
Manikganj|Manikganj Sadar|মহাদেবপুর ই, ডি, এস, ও|1803|11|
Manikganj|Manikganj Sadar|বরংগাইল ই, ডি, এস, ও|1804|11|
Manikganj|Saturia|সাটুরিয়া ইউ, পি, ও|1810|11|
Manikganj|Saturia|বালিয়াটি এস, ও|1811|11|
Manikganj|Singair|সিংগাইর ইউ, পি, ও|1820|11|
Manikganj|Singair|বায়রা ই, ডি, এস, ও|1821|11|
Manikganj|Singair|জয়মন্টপ ই, ডি, এস, ও|1822|11|
Manikganj|Harirampur|হরিরামপুর ইউ, পি, ও|1830|11|
Manikganj|Harirampur|ঝিটকা এস, ও|1831|11|
Manikganj|Ghior|ঘিওর ইউ, পি, ও|1840|11|
Manikganj|Shibalaya|শিবালয় ইউ, পি, ও|1850|11|
Manikganj|Shibalaya|আরিচা ঘাট এস, ও|1851|11|
Manikganj|Shibalaya|তেওতা ই, ডি, এস, ও|1852|11|
Manikganj|Shibalaya|উথলী ই, ডি, এস, ও|1853|11|
Manikganj|Daulatpur|দৌলতপুর ইউ, পি, ও|1860|11|
Tangail|Tangail Sadar|টাংগাইল হেড অফিস|1900|11|
Tangail|Tangail Sadar|কাগমারী ই, ডি, এস, ও|1901|11|
Tangail|Tangail Sadar|সন্তোষ এস, ও|1902|11|
Tangail|Tangail Sadar|করটিয়া এস, ও|1903|11|
Tangail|Tangail Sadar|পোড়াবাড়ী এস, ও|1904|11|
Tangail|Delduar|দেলদুয়ার ইউ, পি, ও|1910|11|
Tangail|Delduar|জাংগালীয়া এস, ও|1911|11|
Tangail|Delduar|পাথরাইল ই, ডি, এস, ও|1912|11|
Tangail|Delduar|এলাসিন এস, ও|1913|11|
Tangail|Delduar|হিংগা নগর ই, ডি, এস, ও|1914|11|
Tangail|Delduar|লাউহাটি ই,ডি, এস, ও|1915|11|
Tangail|Basail|বাসাইল ইউ, পি, ও|1920|11|
Tangail|Nagarpur|নাগরপুর ইউ, পি, ও|1936|11|
Tangail|Nagarpur|ধুবুড়িয়া এস, ও|1937|11|
Tangail|Nagarpur|সলিমাবাদ ই, ডি, এস, ও|1938|11|
Tangail|Mirzapur|মির্জাপুর ইউ, পি, ও|1940|11|
Tangail|Mirzapur|গোড়াই এস, ও|1941|11|
Tangail|Mirzapur|এম সি কলেজ ই, ডি, এস, ও|1942|11|
Tangail|Mirzapur|ওয়ার্সী পাইক পাড়া এস, ও|1943|11|
Tangail|Mirzapur|জামুর্কী এস, ও|1944|11|
Tangail|Mirzapur|মহেড়া এস, ও|1945|11|
Tangail|Sakhipur|সখিপুর ইউ, পি, ও|1950|11|
Tangail|Sakhipur|কচুয়া ই, ডি, এস, ও|1951|11|
Tangail|Bhuapur|ভূয়াপুর ইউ, পি, ও|1960|11|
Tangail|Kalihati|কালিহাতি ইউ, পি, ও|1970|11|
Tangail|Kalihati|রাজাফৈর ই, ডি, এস, ও|1971|11|
Tangail|Kalihati|নাগবাড়ী ই, ডি, এস, ও|1972|11|
Tangail|Kalihati|বল্লাবাজার এস, ও|1973|11|
Tangail|Kalihati|এলেংগা এস, ও|1974|11|
Tangail|Kalihati|পালিশা ই, ডি, এস, ও|1975|11|
Tangail|Kalihati|নগরবাড়ী এস, ও|1977|11|
Tangail|Ghatail|ঘাটাইল ইউ, পি, ও|1980|11|
Tangail|Ghatail|জাহিদগঞ্জ ই, ডি, এস, ও|1981|11|
Tangail|Ghatail|ডি, পাকুটিয়া ই, ডি, এস, ও|1982|11|
Tangail|Ghatail|ধলাপাড়া এস, ও|1983|11|
Tangail|Ghatail|লোহানী সাগর দীঘি, এস, ও|1984|11|
Tangail|Gopalpur|গোপালপুর ইউ, পি, ও|1990|12|
Tangail|Gopalpur|ঝাওয়াইল এস, ও|1991|12|
Tangail|Gopalpur|হেমনগর, এস, ও|1992|12|
Tangail|Madhupur|মধুপুর ইউ, পি, ও|1996|12|
Tangail|Madhupur|ধনবাড়ী এস, ও|1997|12|postal group মধুপুর (Dhanbari is now an upazila of its own)
Kishoreganj|Kishoreganj Sadar|কিশোরগঞ্জ হেড অফিস|2300|12|
Kishoreganj|Kishoreganj Sadar|কিশোরগঞ্জ এস, মিলস্ এস, ও|2301|12|
Kishoreganj|Kishoreganj Sadar|মাইজহাটি ই ,ডি, এস, ও|2302|12|
Kishoreganj|Kishoreganj Sadar|নিলগঞ্জ ই, ডি, এস, ও|2303|12|
Kishoreganj|Karimganj|করিমগঞ্জ ইউ, পি, ও|2310|12|
Kishoreganj|Tarail|তাড়াইল ইউ, পি, ও|2316|13|
Kishoreganj|Hossainpur|হোসেনপুর ইউ, পি, ও|2320|13|
Kishoreganj|Pakundia|পাকুন্দিয়া ইউ, পি, ও|2326|13|
Kishoreganj|Katiadi|কটিয়াদী ইউ, পি, ও|2330|13|
Kishoreganj|Katiadi|গছিহাটা এস, ও|2331|13|
Kishoreganj|Bajitpur|বাজিতপুর ইউ, পি, ও|2336|13|
Kishoreganj|Bajitpur|সরার চর এস, ও|2337|13|
Kishoreganj|Bajitpur|লক্ষ্মীপুর স, ও|2338|13|office type printed "স, ও"
Kishoreganj|Kuliarchar|কুলিয়ারচর ইউ, পি, ও|2340|13|
Kishoreganj|Kuliarchar|ছয়সূতী এস, ও|2341|13|
Kishoreganj|Bhairab|ভৈরব ইউ, পি, ও|2350|13|
Kishoreganj|Nikli|নিকলী দামপাড় ইউ, পি, ও|2360|13|
Kishoreganj|Mithamain|মিঠামঈন ইউ, পি, ও|2370|13|
Kishoreganj|Mithamain|আব্দুল্লাহপুর এস, ও|2371|13|
Kishoreganj|Austagram|অষ্টগ্রাম ইউ,, পি, ও|2380|13|
Kishoreganj|Itna|ইটনা ইউ, পি, ও|2390|13|
Rajbari|Rajbari Sadar|রাজবাড়ী হেড অফিস|7700|24|
Rajbari|Goalanda|গোয়ালন্দ ইউ, পি, ও|7710|24|
Rajbari|Goalanda|খানখানাপুর এস, ও|7711|24|
Rajbari|Pangsha|পাংশা ইউ, পি, ও|7720|24|
Rajbari|Pangsha|রামকোল সি. এস, ও|7721|24|
Rajbari|Pangsha|রতন দিয়া সি. এস, ও|7722|24|
Rajbari|Pangsha|মৃগীবাজার ই. ডি. এস, ও|7723|24|
Rajbari|Baliakandi|বালিয়াকান্দি ইউ, পি, ও|7730|24|
Rajbari|Baliakandi|নলিয়া সি. এস, ও||24|postcode not legible in the scan ("৭৭" and faint digits; listed after 7730)
Faridpur|Faridpur Sadar|ফরিদপুর হেড অফিস||24|postcode not legible in the scan (heading "ফরিদপুর জেলা ৭৮০০-৭৮৯৯")
Faridpur|Faridpur Sadar|কানাইপুর এস, ও|7801|24|
Faridpur|Faridpur Sadar|অম্বিকাপুর এস, ও|7802|24|
Faridpur|Faridpur Sadar|বায়তুল আমান পলিটেকনিক ইন্সটিটিঃ এস, ও|7803|24|
Faridpur|Faridpur Sadar|শ্রী অঙ্গন এস, ও|7804|24|
Faridpur|Char Bhadrasan|চরভদ্রাসন ইউ, পি, ও|7810|24|
Faridpur|Sadarpur|সদরপুর ইউ, পি, ও|7820|24|
Faridpur|Sadarpur|হাট কৃষপুর এস, ও|7821|24|
Faridpur|Sadarpur|বিশ্বজাকের মঞ্জিল এস, ও|7822|24|
Faridpur|Bhanga|ভাংগা ইউ, পি, ও|7830|24|
Faridpur|Nagarkanda|নগরকান্দা ইউ, পি, ও|7840|24|
Faridpur|Nagarkanda|তালমা এস, ও|7841|24|
Faridpur|Madhukhali|মধুখালি ইউ, পি, ও|7850|24|
Faridpur|Madhukhali|কামারখালী এস, ও|7851|24|
Faridpur|Boalmari|বোয়ালমারী ইউ, পি, ও|7860|24|
Faridpur|Boalmari|রূপাতপাত ই, ডি, এস, ও|7861|24|name read as "রূপাতপাত" (scan unclear)
Faridpur|Alfadanga|আলফাডাংগা ইউ, পি, ও|7870|24|
Madaripur|Madaripur Sadar|মাদারীপুর হেড অফিস|7900|24|
Madaripur|Madaripur Sadar|চরমুগরিয়া এস, ও|7901|24|
Madaripur|Madaripur Sadar|কুলপদ্দী ই, ডি. এস, ও|7902|24|
Madaripur|Madaripur Sadar|হবিগঞ্জ ই, ডি, এস, ও|7903|24|
Madaripur|Madaripur Sadar|মোস্তফাপুর ই, ডি, এস, ও|7904|24|
Madaripur|Rajoir|রাজৈর ইউ, পি,ও|7910|24|
Madaripur|Rajoir|খালিয়া এস, ও|7911|24|
Madaripur|Kalkini|কালকিনি ইউ, পি,ও|7920|24|
Madaripur|Kalkini|সাহেব রামপুর ই, ডি, এস, ও|7921|24|
Madaripur|Shibchar|বরহামগঞ্জ ইউ, পি,ও|7930|24|printed "(শিবচর থানা)"
Madaripur|Shibchar|নিলক্ষ্মীবন্দর এস, ও|7931|24|
Madaripur|Shibchar|বাহাদুরপুর ই, ডি, এস, ও|7932|24|
Madaripur|Shibchar|উমেদপুর ই, ডি. এস, ও|7933|24|
Shariatpur|Shariatpur Sadar|পালং হেড অফিস (শরিয়তপুর)|8000|24|
Shariatpur|Shariatpur Sadar|আংগারিয়া এস, ও|8001|24|
Shariatpur|Shariatpur Sadar|চিকন্দী এস, ও|8002|24|
Shariatpur|Zanjira|জাজিরা ইউ, পি, ও|8010|24|
Shariatpur|Naria|নরিয়া ইউ, পি, ও|8020|24|
Shariatpur|Naria|ভোজেশ্বর এস, ও|8021|24|
Shariatpur|Naria|ঘড়িসার এস, ও|8022|24|
Shariatpur|Naria|উপসী এস, ও|8023|24|
Shariatpur|Naria|কার্তিকপুর এস, ও|8024|24|
Shariatpur|Bhedarganj|ভেদরগঞ্জ ইউ, পি, ও|8030|24|
Shariatpur|Damudya|ডামুড্যা ইউ, পি, ও|8040|24|
Shariatpur|Gosairhat|গোসাইরহাট ইউ, পি, ও|8050|24|
Gopalganj|Gopalganj Sadar|গোপালগঞ্জ হেড অফিস|8100|25|
Gopalganj|Gopalganj Sadar|উলপুর এস, ও|8101|25|
Gopalganj|Gopalganj Sadar|বরফা এস, ও|8102|25|
Gopalganj|Kotalipara|কোটালীপাড়া ইউ, পি, ও|8110|25|
Gopalganj|Tungipara|টুংগীপাড়া ইউ, পি, ও|8120|25|
Gopalganj|Tungipara|পাটগাতী এস, ও|8121|25|
Gopalganj|Kashiani|কাশিয়ানী ইউ, পি, ও|8130|25|
Gopalganj|Kashiani|রামদিয়া কলেজ এস, ও|8131|25|
Gopalganj|Kashiani|রাতৈল ই, ডি, এস, ও|8132|25|
Gopalganj|Kashiani|জোনাপুর ই, ডি. এস, ও|8133|25|
Gopalganj|Muksudpur|মকসুদপুর ইউ, পি, ও|8140|25|
Gopalganj|Muksudpur|বাটকিয়ামারী এস, ও|8141|25|
Gopalganj|Muksudpur|খান্দারপাড়া এস, ও|8142|25|
"""
# Chattogram Division: the same booklet, "চট্টগ্রাম রিজিয়ন". Booklet p. 15 (PDF page 9, right half: Brahmanbaria, Cumilla;
# the Sylhet-Division districts on pp. 14-15 are left out), pp. 16-17 (PDF page 10: Chandpur, Lakshmipur, Noakhali, Feni,
# Chattogram GPO, port and city offices) and pp. 18-19 (PDF page 11, left half and the right half's first column up to
# "রাজশাহী রিজিয়ন": Chattogram city and district, Khagrachhari, Rangamati, Bandarban, Cox's Bazar), transcribed by hand
# from the page images in raw/. Upazila = the postal group as printed; "[inferred]" as for Rangpur.
T_CHATTOGRAM = """
Brahmanbaria|Brahmanbaria Sadar|ব্রাহ্মণবাড়ীয়া হেড অফিস|3400|15|spelt "ব্রাহ্মণবাড়ীয়া" in the booklet
Brahmanbaria|Brahmanbaria Sadar|তাল শহর ই, ডি, এস, ও|3401|15|
Brahmanbaria|Brahmanbaria Sadar|আশুগঞ্জ এস, ও|3402|15|postal group as printed (Ashuganj is now its own upazila)
Brahmanbaria|Brahmanbaria Sadar|আশুগঞ্জ সার কারখানা এস, ও|3403|15|postal group as printed (Ashuganj is now its own upazila)
Brahmanbaria|Brahmanbaria Sadar|পওন ই, ডি, এস, ও|3404|15|
Brahmanbaria|Nabinagar|নবীনগর ইউ, পি, ও|3410|15|
Brahmanbaria|Nabinagar|লাউর ফতেপুর ই,ডি, এস, ও|3411|15|
Brahmanbaria|Nabinagar|রসুল্লাবাদ ই,ডি, এস, ও|3412|15|
Brahmanbaria|Nabinagar|শ্যামগ্রাম এস, ও|3413|15|
Brahmanbaria|Nabinagar|রতনপুর ই,ডি, এস, ও|3414|15|
Brahmanbaria|Nabinagar|শাহাপুর এস, ও|3415|15|
Brahmanbaria|Nabinagar|কাইতলা এস, ও|3417|15|
Brahmanbaria|Nabinagar|সলিমগঞ্জ এস, ও|3418|15|
Brahmanbaria|Nabinagar|জীবনগঞ্জ বাজার ই,ডি, এস, ও|3419|15|
Brahmanbaria|Bancharampur|বাঞ্ছারামপুর ইউ, পি, ও|3420|15|
Brahmanbaria|Sarail|সরাইল ইউ, পি, ও|3430|15|
Brahmanbaria|Sarail|শাহবাজপুর এস, ও|3431|15|
Brahmanbaria|Sarail|চান্দুরা এস, ও|3432|15|
Brahmanbaria|Nasirnagar|নাছির নগর ইউ, পি, ও|3440|15|
Brahmanbaria|Nasirnagar|ফান্দাউক এস, ও|3441|15|
Brahmanbaria|Akhaura|আখাউড়া ইউ, পি, ও|3450|15|
Brahmanbaria|Akhaura|আজমপুর ই, ডি, এস, ও|3451|15|
Brahmanbaria|Akhaura|গংগা সাগর এস, ও|3452|15|
Brahmanbaria|Kasba|কসবা ইউ, পি, ও|3460|15|
Brahmanbaria|Kasba|কুটি এস, ও|3461|15|
Brahmanbaria|Kasba|চন্ডিদ্বার এস, ও|3462|15|
Brahmanbaria|Kasba|চারগাছ এস, ও|3463|15|
Brahmanbaria|Kasba|গোপীনাথপুর এস, ও|3464|15|
Cumilla|Cumilla Adarsha Sadar|কুমিল্লা হেড অফিস|3500|15|district heading printed "কুমিল্লা জেলা ৩৫০০-৩৫৯৯"; head-office group (the old Comilla Sadar thana, since split into Adarsha Sadar, Sadar Dakshin and Lalmai)
Cumilla|Cumilla Adarsha Sadar|কুমিল্লা ক্যান্ট এস, ও|3501|15|
Cumilla|Cumilla Adarsha Sadar|হালিমা নগর এস, ও|3502|15|
Cumilla|Cumilla Adarsha Sadar|কোর্টবাড়ী এস, ও|3503|15|
Cumilla|Cumilla Adarsha Sadar|সুয়াগঞ্জ ই, ডি, এস, ও|3504|15|
Cumilla|Cumilla Adarsha Sadar|শিমপুর এস, ও|3505|15|
Cumilla|Chandina|চান্দিনা ইউ, পি, ও|3510|15|
Cumilla|Chandina|মাধাইয়া বাজার ই, ডি, এস, ও|3511|15|
Cumilla|Chandina|মেঘনা এস, ও|3515|15|
Cumilla|Daudkandi|দাউদকান্দি ইউ, পি ও|3516|15|
Cumilla|Daudkandi|গৌরীপুর এস, ও|3517|15|
Cumilla|Daudkandi|দশপাড়া ই, ডি, এস, ও|3518|15|
Cumilla|Daudkandi|ইলিয়টগঞ্জ এস, ও|3519|15|
Cumilla|Burichang|বুড়িচং ইউ, পি, ও|3520|15|
Cumilla|Burichang|ময়নামতি বাজার এস, ও|3521|15|
Cumilla|Brahmanpara|ব্রাহ্মণপাড়া ইউ, পি ও|3526|15|
Cumilla|Debidwar|দেবিদ্বার ইউ, পি ও|3530|15|
Cumilla|Debidwar|গংগামন্ডল এস, ও|3531|15|
Cumilla|Debidwar|বড় শালঘর ই, ডি, এস, ও|3532|15|
Cumilla|Debidwar|ধামতী মাদ্রাসা এস, ও|3533|15|
Cumilla|Muradnagar|মুরাদ নগর ইউ, পি, ও|3540|15|
Cumilla|Muradnagar|রামচন্দ্রপুর এস, ও|3541|15|
Cumilla|Muradnagar|কোম্পানীগঞ্জ এস, ও|3542|15|
Cumilla|Muradnagar|বাংগরা এস, ও|3543|15|
Cumilla|Muradnagar|সোনাকান্দা এস, ও|3544|15|
Cumilla|Muradnagar|পনতি বাজার এস, ও|3545|15|
Cumilla|Homna|হোমনা ইউ, পি, ও|3546|15|
Cumilla|Homna|বাতাকান্দি এস, ও|3547|15|
Cumilla|Chauddagram|চৌদ্দগ্রাম ইউ, পি, ও|3550|15|
Cumilla|Chauddagram|বাতিসা ই, ডি, এস, ও|3551|15|
Cumilla|Chauddagram|চিওড়া এস, ও|3552|15|
Cumilla|Barura|বড়ুরা ইউ, পি, ও|3560|15|spelt "বড়ুরা" in the booklet
Cumilla|Barura|পয়ালগাছা এস, ও|3561|15|
Cumilla|Barura|মুর্দাফরগঞ্জ এস, ও|3562|15|
Cumilla|Laksam|লাকসাম ইউ, পি, ও|3570|15|
Cumilla|Laksam|লক্ষণপুর ই, ডি, এস, ও|3571|15|
Cumilla|Laksam|বিপুলাসার ই, ডি, এস, ও|3572|15|
Cumilla|Laksam|ছোট শরীফপুর এস, ও|3573|15|
Cumilla|Nangalkot|লাঙ্গলকোট ইউ, পি, ও|3580|15|spelt "লাঙ্গলকোট" in the booklet
Cumilla|Nangalkot|ঢালুয়া ই, ডি, এস, ও|3581|15|
Cumilla|Nangalkot|ছড়িয়া বাজার এস, ও|3582|15|
Cumilla|Nangalkot|গুণবতী এস, ও|3583|15|
Chandpur|Chandpur Sadar|চাঁদপুর হেড অফিস|3600|16|
Chandpur|Chandpur Sadar|পুরান বাজার এস, ও|3601|16|
Chandpur|Chandpur Sadar|বাবুর হাট এস, ও|3602|16|
Chandpur|Chandpur Sadar|সাহাতলী ই, ডি, এস, ও|3603|16|
Chandpur|Hajiganj|হাজীগঞ্জ ইউ, পি, ও|3610|16|
Chandpur|Hajiganj|বলাখাল এস, ও|3611|16|
Chandpur|Shahrasti|শাহরাস্তী ইউ, পি, ও|3620|16|
Chandpur|Shahrasti|খিলাবাজার ই, ডি, এস, ও|3621|16|
Chandpur|Shahrasti|পশ্চিম খেরিহর আল-জামিয়া ইসলামিয়া মাদ্রাসা এস, ও|3622|16|
Chandpur|Shahrasti|চৈতোষী এস, ও|3623|16|
Chandpur|Kachua|কচুয়া ইউ, পি, ও|3630|16|
Chandpur|Kachua|পাক শ্রীরামপুর ই, ডি, এস, ও|3631|16|
Chandpur|Kachua|রহিমা নগর এস, ও|3632|16|
Chandpur|Kachua|সাচার এস, ও|3633|16|
Chandpur|Matlab Dakshin|মতলবগঞ্জ ইউ, পি, ও|3640|16|[inferred] printed "(মতলব থানা)"; the old Matlab thana is now Matlab Dakshin (seat Matlabganj) and Matlab Uttar
Chandpur|Matlab Dakshin|মোহনপুর এস, ও|3641|16|[inferred] postal group "(মতলব থানা)" as printed; Matlab thana is now Matlab Dakshin and Matlab Uttar
Chandpur|Matlab Dakshin|কালিপুরা বাজার ই, ডি, এস, ও|3642|16|[inferred] postal group "(মতলব থানা)" as printed; Matlab thana is now Matlab Dakshin and Matlab Uttar
Chandpur|Matlab Dakshin|চেঙ্গারচর এস, ও|3643|16|[inferred] postal group "(মতলব থানা)" as printed; Matlab thana is now Matlab Dakshin and Matlab Uttar
Chandpur|Faridganj|ফরিদগঞ্জ ইউ, পি, ও|3650|16|
Chandpur|Faridganj|চন্দ্রা এস, ও|3651|16|
Chandpur|Faridganj|রুপসা এস, ও|3652|16|
Chandpur|Faridganj|গৃদকালিন্দিয়া ই, ডি, এস, ও|3653|16|
Chandpur|Faridganj|রামপুর বাজার ই, ডি,এস, ও|3654|16|
Chandpur|Faridganj|ইসলামপুর শাহ ইয়াসিন সিনিয়র মাদ্রাসা এস, ও|3655|16|
Chandpur|Haimchar|হাইমচর ইউ, পি, ও|3660|16|
Chandpur|Haimchar|গন্ডামারা এস, ও|3661|16|
Lakshmipur|Lakshmipur Sadar|লক্ষ্মীপুর হেড অফিস|3700|16|
Lakshmipur|Lakshmipur Sadar|দালাল বাজার এস, ও|3701|16|
Lakshmipur|Lakshmipur Sadar|ভবানীগঞ্জ এস, ও|3702|16|
Lakshmipur|Lakshmipur Sadar|মান্দারী এস, ও|3703|16|
Lakshmipur|Lakshmipur Sadar|কেরামতগঞ্জ এস, ও|3704|16|
Lakshmipur|Lakshmipur Sadar|রুপচরা এস, ও|3705|16|
Lakshmipur|Lakshmipur Sadar|দত্তপাড়া এস, ও|3706|16|
Lakshmipur|Lakshmipur Sadar|চৌপল্লী ই, ডি,এস, ও|3707|16|
Lakshmipur|Lakshmipur Sadar|চন্দ্রগঞ্জ এস, ও|3708|16|
Lakshmipur|Lakshmipur Sadar|আমানী লক্ষ্মীপুর ই, ডি, এস, ও|3709|16|
Lakshmipur|Raipur|রায়পুর ইউ, পি,ও|3710|16|
Lakshmipur|Raipur|রাখালিয়া বাজার এস, ও|3711|16|
Lakshmipur|Raipur|নাগের দিঘীরপাড় ই, ডি, এস, ও|3712|16|
Lakshmipur|Raipur|হায়দরগঞ্জ এস, ও|3713|16|
Lakshmipur|Raipur|ভূয়াবাড়ী ই,ডি, এস, ও|3714|16|
Lakshmipur|Ramganj|রামগঞ্জ ইউ, পি,ও|3720|16|
Lakshmipur|Ramganj|আলীপুর ই, ডি, এস, ও|3721|16|
Lakshmipur|Ramganj|পানপাড়া ই, ডি, এস, ও|3722|16|
Lakshmipur|Ramganj|কাঞ্চনপুর ই, ডি, এস, ও|3723|16|
Lakshmipur|Ramganj|নাগমুদ এস, ও|3724|16|
Lakshmipur|Ramganj|ডলটা এস, ও|3725|16|
Lakshmipur|Ramganj|ভাট্রা এস, ও|3726|16|
Lakshmipur|Ramganj|সোনাপুর বাজার এস, ও|3727|16|
Lakshmipur|Ramgati|চর আলেকজান্ডার ইউ, পি, ও|3730|16|printed "(রামগতি থানা)"
Lakshmipur|Ramgati|হাজীর হাট এস, ও|3731|16|
Lakshmipur|Ramgati|রামগতির হাট এস, ও|3732|16|
Noakhali|Noakhali Sadar|নোয়াখালী হেড অফিস|3800|16|
Noakhali|Noakhali Sadar|নোয়াখালী কলেজ এস, ও|3801|16|
Noakhali|Noakhali Sadar|সোনাপুর এস, ও|3802|16|
Noakhali|Noakhali Sadar|দিন মনির হাট ই, ডি, এস, ও|3803|16|
Noakhali|Noakhali Sadar|পাক কিশোরগঞ্জ ই, ডি, এস, ও|3804|16|
Noakhali|Noakhali Sadar|বান্দের হাট ই, ডি, এস, ও|3805|16|uncertain reading of the name (scan unclear)
Noakhali|Noakhali Sadar|মৃধ্যার হাট ই, ডি, এস, ও|3806|16|uncertain reading of the name (scan unclear)
Noakhali|Noakhali Sadar|কবির হাট এস, ও|3807|16|postal group as printed (Kabirhat is now its own upazila)
Noakhali|Noakhali Sadar|খলিফার হাট এস, ও|3808|16|
Noakhali|Noakhali Sadar|চরম টুয়া এস, ও|3809|16|
Noakhali|Noakhali Sadar|চাপরাশির হাট এস, ও|3811|16|uncertain reading of the name (scan unclear)
Noakhali|Noakhali Sadar|চর জব্বার ই, ডি, এস, ও|3812|16|
Noakhali|Noakhali Sadar|চর বাটা এস, ও|3813|16|
Noakhali|Begumganj|বেগমগঞ্জ ইউ, পি, ও|3820|16|
Noakhali|Begumganj|চৌমুহনী (এল এস জি) এস, ও|3821|16|
Noakhali|Begumganj|বাংলা বাজার এস, ও|3822|16|
Noakhali|Begumganj|মির ওয়ারিশপুর ই, ডি, এস, ও|3823|16|
Noakhali|Begumganj|বজরা এস, ও|3824|16|
Noakhali|Begumganj|জমিদার হাট এস, ও|3825|16|uncertain reading of the name (scan unclear)
Noakhali|Begumganj|সোনাইমুড়ী (এল এস জি) এস, ও|3827|16|postal group as printed (Sonaimuri is now its own upazila); first digits of the code faint in the scan; read as 38.. from the printed district range "নোয়াখালী জেলা ৩৮০০-৩৮৯৯"
Noakhali|Begumganj|গোপালপুর এস, ও|3828|16|first digits of the code faint in the scan; read as 38.. from the printed district range "নোয়াখালী জেলা ৩৮০০-৩৮৯৯"
Noakhali|Begumganj|জয়নারায়নপুর ই, ডি, এস, ও|3829|16|first digits of the code faint in the scan; read as 38.. from the printed district range "নোয়াখালী জেলা ৩৮০০-৩৮৯৯"
Noakhali|Begumganj|আলাইয়ারপুর ই, ডি, এস, ও|3831|16|
Noakhali|Begumganj|টংগীর পাড় বটিকা ই, ডি, এস, ও|3832|16|
Noakhali|Begumganj|খেলাফত বাজার এস, ও|3833|16|
Noakhali|Begumganj|রাজগঞ্জ এস, ও|3834|16|
Noakhali|Begumganj|ওয়াছেকপুর এস, ও|3835|17|
Noakhali|Begumganj|ভবানী জীবনপুর এস, ও|3837|17|
Noakhali|Begumganj|মহেশগঞ্জ ই, ডি, এস, ও|3838|17|
Noakhali|Begumganj|নদোনা ই, ডি, এস, ও|3839|17|
Noakhali|Begumganj|নানদিয়াপাড়া এস, ও|3841|17|
Noakhali|Begumganj|খালিশপুর ই, ডি, এস, ও|3842|17|
Noakhali|Begumganj|দেউটি এস, ও|3843|17|
Noakhali|Begumganj|জয়াগ এস, ও|3844|17|
Noakhali|Begumganj|থানার হাট এস, ও|3845|17|
Noakhali|Begumganj|আমিশাপাড়া এস, ও|3847|17|
Noakhali|Begumganj|দুর্গাপুর ই, ডি, এস, ও|3848|17|
Noakhali|Companiganj|বসুরহাট ইউ,, পি ও|3850|17|printed "(কোম্পানীগঞ্জ থানা)"
Noakhali|Companiganj|চরহাজারী ই, ডি, এস, ও|3851|17|
Noakhali|Senbagh|সেনবাগ ইউ, পি, ও|3860|17|
Noakhali|Senbagh|কল্যানদী ই, ডি, এস, ও|3861|17|
Noakhali|Senbagh|বীজবাগ এস, ও|3862|17|
Noakhali|Senbagh|কানকির হাট এস, ও|3863|17|
Noakhali|Senbagh|ছাতার পাইয়া এস, ও|3864|17|
Noakhali|Senbagh|টি, পি, লেমুয়া এস, ও|3865|17|
Noakhali|Chatkhil|চাটখিল ইউ, পি, ও|3870|17|
Noakhali|Chatkhil|পাল্লা ই, ডি, এস, ও|3871|17|
Noakhali|Chatkhil|খিলপাড়া এস, ও|3872|17|
Noakhali|Chatkhil|বদলকোর্ট এস, ও|3873|17|
Noakhali|Chatkhil|রেজ্জাকপুর এস, ও|3874|17|
Noakhali|Chatkhil|সোল্লা ই, ডি, এস, ও|3875|17|
Noakhali|Chatkhil|কড়ি হাটি এস, ও|3877|17|
Noakhali|Chatkhil|দশ ঘরিয়া এস, ও|3878|17|
Noakhali|Chatkhil|বানসা বাজার ই, ডি, এস, ও|3879|17|
Noakhali|Chatkhil|শাহাপুর এস, ও|3881|17|
Noakhali|Chatkhil|সামপাড়া এস, ও|3882|17|
Noakhali|Chatkhil|শিংবাহুড়া ই, ডি, এস, ও|3883|17|
Noakhali|Hatiya|হাতিয়া ইউ, পি ও|3890|17|
Noakhali|Hatiya|আফাজিয়া বাজার এস, ও|3891|17|
Noakhali|Hatiya|তমরদ্দি এস, ও|3892|17|
Noakhali|Hatiya|চৌরঙ্গী বাজার এস, ও|3893|17|
Feni|Feni Sadar|ফেণী হেড অফিস|3900|17|spelt "ফেণী" in the booklet
Feni|Feni Sadar|ফাজিলপুর এস, ও|3901|17|
Feni|Feni Sadar|শর্শদী এস, ও|3902|17|
Feni|Feni Sadar|লস্করহাট ই , ডি, এস, ও|3903|17|
Feni|Chhagalnaiya|ছাগল নাইয়া ইউ, পি, ও|3910|17|
Feni|Chhagalnaiya|মহারাজগঞ্জ এস, ও|3911|17|
Feni|Chhagalnaiya|দারোগার হাট এস, ও|3912|17|
Feni|Chhagalnaiya|পূর্ব শিলুয়া ই , ডি, এস, ও|3913|17|
Feni|Daganbhuiyan|দাগনভূইয়া ইউ, পি, ও|3920|17|
Feni|Daganbhuiyan|দুধমুখা এস, ও|3921|17|
Feni|Daganbhuiyan|ছিলোনীয়া এস, ও|3922|17|
Feni|Daganbhuiyan|রাজাপুর ই , ডি, এস, ও|3923|17|
Feni|Sonagazi|সোনাগাজী ইউ, পি, ও|3930|17|
Feni|Sonagazi|মতিগঞ্জ এস, ও|3931|17|
Feni|Sonagazi|আহম্মদপুর এস, ও|3932|17|
Feni|Sonagazi|কাজীরহাট এস, ও|3933|17|
Feni|Parshuram|পরশুরাম ইউ, পি, ও|3940|17|
Feni|Parshuram|শুয়ার বাজার এস, ও|3941|17|
Feni|Parshuram|ফুলগাজী এস, ও|3942|17|postal group as printed (Fulgazi is now its own upazila)
Feni|Parshuram|মুন্সীরহাট এস, ও|3943|17|
Chattogram||চট্টগ্রাম জি, পি, ও|4000|17|Chattogram city; printed as the section heading "চট্টগ্রাম জি, পি, ও ৪০০০"
Chattogram||চট্টগ্রাম বন্দর হেড অফিস|4100|17|Chattogram city
Chattogram||পাহাড়তলী টি, এস, ও|4202|17|Chattogram city ("চট্টগ্রাম শহরের অন্যান্য বিলিকারী অফিস ৪২০০-৪২৯৯")
Chattogram||চক বাজার টি, এস, ও|4203|17|Chattogram city
Chattogram||পতেংগা টি, এস, ও|4204|17|Chattogram city
Chattogram||চট্টগ্রাম এয়ারপোর্ট টি, এস, ও|4205|17|Chattogram city
Chattogram||জুলদিয়া মেরিন একাডেমী টি, এস, ও|4206|17|Chattogram city (listed among the city offices)
Chattogram||ফিরোজশাহ্ কলোনী টি, এস, ও|4207|17|Chattogram city
Chattogram||মোহরদ টি, এস, ও|4208|17|Chattogram city
Chattogram||চট্টগ্রাম পলিটেকনিক ইন্সটিটিউট টি, এস, ও|4209|17|Chattogram city
Chattogram||বায়েজীদ বোস্তামী টি, এস, ও|4210|17|Chattogram city
Chattogram||আমিন জুট মিলস্ টি, এস, ও|4211|17|Chattogram city
Chattogram||চাঁন্দগাও টি, এস, ও|4212|17|Chattogram city
Chattogram||ওয়াজেদীয়া মাদ্রাসা টি, এস, ও|4213|17|Chattogram city
Chattogram||জালালাবাদ টি, এস, ও|4214|17|Chattogram city
Chattogram||আনন্দবাজার ই ডি,, এস, ও|4215|17|Chattogram city
Chattogram||হালিশহর হাউজিং এস্টেট টি, এস, ও|4216|17|Chattogram city
Chattogram||নর্থ কাটলী টি, এস, ও|4217|17|Chattogram city
Chattogram||চট্টগ্রাম সেইলার্স কলোনী টি, এস, ও|4218|17|Chattogram city
Chattogram||চট্টগ্রাম কাস্টমস একাডেমী টি, এস, ও|4219|17|Chattogram city
Chattogram||চট্টগ্রাম ক্যান্টনমেন্ট টি, এস, ও|4220|17|Chattogram city
Chattogram||আল-আমিন বাড়ীয়া মাদ্রাসা ই ডি, এস, ও|4221|17|Chattogram city
Chattogram||মিডল পতেঙ্গা চৌধুরী পাড়া টি, এস, ও|4222|18|Chattogram city
Chattogram||এক্সপোর্ট প্রসেসিং জোন টি, এস, ও|4223|18|Chattogram city
Chattogram||রামপুর টি, এস, ও|4224|18|Chattogram city
Chattogram||জাকির হোসেন রোড টি, এস, ও|4225|18|Chattogram city
Chattogram||উত্তর হালিশহর টি, এস, ও|4226|18|Chattogram city
Chattogram|Sitakunda|সীতাকুন্ড ইউ, পি, ও|4310|18|district heading printed "চট্টগ্রাম জেলা ৪৩০০-৪৩৯৯"
Chattogram|Sitakunda|বারৈয়াঢালা এস, ও|4311|18|
Chattogram|Sitakunda|বাড়বকুন্ড এস, ও|4312|18|
Chattogram|Sitakunda|বাঁশবাড়ীয়া এস, ও|4313|18|
Chattogram|Sitakunda|কুমিরা এস, ও|4314|18|
Chattogram|Sitakunda|ভাটিয়ারী এস, ও|4315|18|
Chattogram|Sitakunda|ফৌজদার হাট ক্যাডেট কলেজ এস, ও|4316|18|
Chattogram|Sitakunda|জাফরাবাদ এস, ও|4317|18|
Chattogram|Sitakunda|আই, আই, ইউ, সি এস, ও|4318|18|
Chattogram|Mirsharai|মিরশ্বরাই ইউ, পি, ও|4320|18|spelt "মিরশ্বরাই" in the booklet
Chattogram|Mirsharai|আবুতোরাব এস, ও|4321|18|
Chattogram|Mirsharai|দারোগা হাট ই, ডি, এস, ও|4322|18|
Chattogram|Mirsharai|ভরদ্বাজহাট এস, ও|4323|18|
Chattogram|Mirsharai|জোয়ারগঞ্জ এস, ও|4324|18|
Chattogram|Mirsharai|আজমপুর ই, ডি, এস, ও|4325|18|
Chattogram|Mirsharai|মহাজন হাট এস, ও|4326|18|
Chattogram|Mirsharai|করের হাট এস, ও|4327|18|
Chattogram|Mirsharai|বিশ্ব দরবার এস, ও|4329|18|
Chattogram|Sandwip|সন্দীপ ইউ, পি, ও|4300|18|printed with the note that Sandwip thana was given 4300 as an exception (Chattogram district has many delivery offices)
Chattogram|Sandwip|শিবের হাট ই, ডি, এস, ও|4301|18|
Chattogram|Sandwip|উরিরচর এস, ও|4302|18|
Chattogram|Hathazari|হাটহাজারী ইউ, পি, ও|4330|18|
Chattogram|Hathazari|চট্টগ্রাম বিশ্ববিদ্যালয় এস, ও|4331|18|
Chattogram|Hathazari|গড় দুয়ারা ই, ডি, এস, ও|4332|18|
Chattogram|Hathazari|কাটিরহাট এস, ও|4333|18|
Chattogram|Hathazari|মির্জাপুর ই, ডি, এস, ও|4334|18|
Chattogram|Hathazari|ফতেহাবাদ এস, ও|4335|18|
Chattogram|Hathazari|নুরালীবাড়ী এস, ও|4337|18|
Chattogram|Hathazari|ইউনুছ নগর ই, ডি, এস, ও|4338|18|
Chattogram|Hathazari|মাদার্সা এস, ও|4339|18|
Chattogram|Raozan|রাউজান ইউ, পি, ও|4340|18|
Chattogram|Raozan|বীনাজুরী এস, ও|4341|18|
Chattogram|Raozan|কুন্ডেশ্বরী ভবন এস, ও|4342|18|
Chattogram|Raozan|গহিরা এস, ও|4343|18|
Chattogram|Raozan|জগন্নাথ হাট এস, ও|4344|18|
Chattogram|Raozan|ফতেহপুর এস, ও|4345|18|
Chattogram|Raozan|গুজরা নোয়াপাড়া এস, ও|4346|18|
Chattogram|Raozan|দেওয়ানপুর এস, ও|4347|18|
Chattogram|Raozan|মহামুনী এস, ও|4348|18|
Chattogram|Raozan|বি,আই, টি পোস্ট অফিস চট্টগ্রামএস, ও|4349|18|
Chattogram|Fatikchhari|ফটিকছড়ি ইউ, পি, ও|4350|18|
Chattogram|Fatikchhari|নানুপুর এস, ও|4351|18|
Chattogram|Fatikchhari|ভান্ডার শরীফ এস, ও|4352|18|
Chattogram|Fatikchhari|নাজির হাট এস, ও|4353|18|
Chattogram|Fatikchhari|হারুয়ালছড়ি ই,ডি, এস, ও|4354|18|
Chattogram|Fatikchhari|নারায়নহাট এস, ও|4355|18|
Chattogram|Fatikchhari|আজাদী বাজার এস, ও|4357|18|
Chattogram|Rangunia|রাংগুনিয়া ইউ, পি, ও|4360|18|printed "রাংগুনিয়া ইউ, পি, ও (ধামাইর)"
Chattogram|Rangunia|ধামাইর হাট ই, ডি, এস, ও|4361|18|
Chattogram|Boalkhali|বোয়ালখালী ইউ, পি, ও|4366|18|printed with the bracketed note "পোস্ট কোড সংখ্যা কম হওয়ায় রাংগুনিয়া টিপিও-এর সংখ্যা দেওয়া হইল" (codes from the Rangunia series)
Chattogram|Boalkhali|কানুনগোপাড়া এস, ও|4363|18|
Chattogram|Boalkhali|সারোয়াতলী এস, ও|4364|18|
Chattogram|Boalkhali|ইকবাল পার্ক এস, ও|4365|18|
Chattogram|Boalkhali|সাকপুরা এস, ও|4367|18|
Chattogram|Boalkhali|কদুরখীল ই, ডি, এস, ও|4368|18|
Chattogram|Boalkhali|চরনদ্বীপ এস, ও|4369|18|
Chattogram|Patiya|পটিয়া হেড অফিস|4370|18|printed "পটিয়া হেড অফিস পটিয়া থানা"
Chattogram|Patiya|বুধপাড়া এস, ও|4371|18|
Chattogram|Anwara|আনোয়ারা ইউ, পি, ও|4376|18|
Chattogram|Anwara|পরৈয় কোরা ই, ডি, এস, ও|4377|18|
Chattogram|Anwara|বট্তলী ই, ডি, এস, ও|4378|18|
Chattogram|Chandanaish|ইস্ট জোয়ারা ইউ, পি, ও|4380|18|printed "(চন্দনাইশ থানা)"
Chattogram|Chandanaish|গাছবাড়ীয়া এস, ও|4381|18|
Chattogram|Chandanaish|দোহাজারী এস, ও|4382|18|
Chattogram|Chandanaish|বরমা এস, ও|4383|18|
Chattogram|Satkania|সাতকানিয়া ইউ, পি, ও|4386|18|
Chattogram|Satkania|বায়তুল ইজ্জত এস, ও|4387|18|
Chattogram|Satkania|বাজালিয়া ই, ডি, এস, ও|4388|18|
Chattogram|Banshkhali|জলদী ইউ, পি, ও|4390|18|printed "(বাশখালী থানা)"
Chattogram|Banshkhali|খান বাহাদুর বাজার এস, ও|4391|18|
Chattogram|Banshkhali|গুনাগারি ই, ডি, এস, ও|4392|18|
Chattogram|Banshkhali|বানীগ্রাম এস, ও|4393|18|
Chattogram|Lohagara|লোহাগড়া ইউ, পি, ও|4396|19|
Chattogram|Lohagara|পদুয়া এস, ও|4397|19|
Chattogram|Lohagara|চুনতি ই, ডি, এস, ও|4398|19|
Khagrachhari|Khagrachhari Sadar|খাগড়াছড়ি হেড অফিস|4400|19|
Khagrachhari|Panchhari|পানছড়ি ইউ, পি, ও|4410|19|
Khagrachhari|Dighinala|দিঘীনালা ইউ, পি, ও|4420|19|
Khagrachhari|Mahalchhari|মহালছড়ি ইউ, পি, ও|4430|19|
Khagrachhari|Ramgarh|রামগড় হেড অফিস|4440|19|printed "রামগড় হেড অফিস (রামগড় থানা)"
Khagrachhari|Matiranga|মাটিরাংগা ইউ, পি, ও|4450|19|second digit of the code not legible in the scan; read as 44.. from the printed district range "খাগড়াছড়ি জেলা ৪৪০০-৪৪৯৯"
Khagrachhari|Manikchhari|মানিকছড়ি ইউ, পি, ও|4460|19|
Khagrachhari|Lakshmichhari|লক্ষ্মীছড়ি ইউ, পি, ও|4470|19|
Rangamati|Rangamati Sadar|রাঙ্গামাটি হেড অফিস|4500|19|
Rangamati|Kawkhali|কলমপতি ইউ, পি, ও|4510|19|printed "(কাউখালী থানা)"
Rangamati|Kawkhali|বেতবুনিয়া এস, ও|4511|19|
Rangamati|Naniarchar|নানিয়ারচর ইউ, পি, ও|4520|19|
Rangamati|Kaptai|কাপ্তাই ইউ, পি, ও|4530|19|
Rangamati|Kaptai|চন্দ্রঘোনা এস, ও|4531|19|
Rangamati|Kaptai|কাপ্তাই প্রজেক্ট এস, ও|4532|19|
Rangamati|Kaptai|কাপ্তাই নতুন বাজার এস, ও|4533|19|
Rangamati|Rajasthali|রাজস্থলী ইউ, পি, ও|4540|19|
Rangamati|Belaichhari|বিলাইছড়ি ইউ, পি, ও|4550|19|
Rangamati|Juraichhari|জরাছড়ি ইউ, পি, ও|4560|19|spelt "জরাছড়ি" in the booklet
Rangamati|Barkal|বরকল ইউ, পি, ও|4570|19|
Rangamati|Langadu|লংগদু ইউ, পি, ও|4580|19|
Rangamati|Baghaichhari|ম্যারিশ্যা ইউ, পি, ও|4590|19|printed "(বাগাইছড়ি থানা)"
Bandarban|Bandarban Sadar|বান্দরবান হেড অফিস|4600|19|
Bandarban|Rowangchhari|রোয়াংছড়ি ইউ, পি ,ও|4610|19|
Bandarban|Ruma|রুমা ইউ, পি, ও|4620|19|
Bandarban|Thanchi|থানচি ইউ, পি, ও|4630|19|
Bandarban|Lama|লামা এস, ও|4640|19|printed "লামা এস, ও (লামা থানা হেড কোয়ার্টার)"
Bandarban|Lama|আজিজনগর এস, ও|4641|19|
Bandarban|Alikadam|আলীকদম ইউ, পি, ও|4650|19|
Bandarban|Naikhongchhari|নাইক্ষ্যং ছড়ি ইউ, পি, ও|4660|19|
Cox's Bazar|Cox's Bazar Sadar|কক্সবাজার হেড অফিস|4700|19|
Cox's Bazar|Cox's Bazar Sadar|ঝিলনজা ই, ডি, এস, ও|4701|19|
Cox's Bazar|Cox's Bazar Sadar|ঈদগাঁ এস, ও|4702|19|postal group as printed (Eidgaon is now its own upazila)
Cox's Bazar|Maheshkhali|গোরকঘাট ইউ, পি, ও|4710|19|printed "(মহেশখালী)"
Cox's Bazar|Kutubdia|কুতুবদিয়া ইউ, পি, ও|4720|19|
Cox's Bazar|Ramu|রামু ইউ, পি, ও|4730|19|
Cox's Bazar|Chakaria|চিরিংগা কমিউনিটি সেন্টার ইউ, পি, ও|4740|19|printed "চকরিয়া থানা)"
Cox's Bazar|Chakaria|চিরিংগা এস, ও|4741|19|
Cox's Bazar|Chakaria|বদরকালী এস, ও|4742|19|
Cox's Bazar|Chakaria|মালুমঘাট হসপিটাল ই, ডি, এস, ও|4743|19|
Cox's Bazar|Ukhia|উখিয়া ইউ, পি, ও|4750|19|
Cox's Bazar|Teknaf|টেকনাফ ইউ, পি, ও|4760|19|
Cox's Bazar|Teknaf|হ্নীলা এস, ও|4761|19|
Cox's Bazar|Teknaf|সেন্ট মার্টিন দ্বীপ এস, ও|4762|19|
"""
# Khulna Division: the same booklet, "খুলনা রিজিয়ন ৭০০০-৯৯৯৯". Booklet p. 23 (PDF page 13, right half: Kushtia, Meherpur,
# Chuadanga, Jhenaidah, Jashore), p. 24 (PDF page 14, first column: Narail, Magura; the Dhaka- and Barishal-Division
# districts that follow are left out), p. 26 (PDF page 15, last column: "খুলনা জি, পি, ও ৯০০০" and the Khulna city
# offices) and p. 27 (PDF page 15, right half: Khulna district, Bagerhat, Satkhira, up to "সমাপ্ত"), transcribed by hand
# from the page images in raw/. Upazila = the postal group as printed; "[inferred]" as for Rangpur.
T_KHULNA = """
Kushtia|Kushtia Sadar|কুষ্টিয়া হেড অফিস|7000|23|
Kushtia|Kushtia Sadar|কুষ্টিয়া মোহিনী মিলস্ টি, এস, ও|7001|23|
Kushtia|Kushtia Sadar|জগতী এস, ও|7002|23|
Kushtia|Kushtia Sadar|ইসলামী বিশ্ববিদ্যালয় এস, ও|7003|23|
Kushtia|Kumarkhali|কুমারখালী ইউ, পি, ও|7010|23|
Kushtia|Kumarkhali|পান্টি ই, ডি, এস, ও|7011|23|
Kushtia|Khoksa|জানিপুর ইউ, পি, ও|7020|23|printed "(খোকসা থানা)"
Kushtia|Khoksa|খোকসা এস, ও|7021|23|
Kushtia|Mirpur|মিরপুর ইউ, পি, ও|7030|23|
Kushtia|Mirpur|পোড়াদহ এস, ও|7031|23|
Kushtia|Mirpur|আমলা সদরপুর ই, ডি, এস, ও|7032|23|
Kushtia|Bheramara|ভেড়ামারা ইউ, পি, ও|7040|23|
Kushtia|Bheramara|গ্যাঞ্জেস ভেড়ামারা এস, ও|7041|23|
Kushtia|Bheramara|আল্লার দরগা এস, ও|7042|23|postal group as printed
Kushtia|Daulatpur|রেফায়েতপুর ইউ, পি, ও|7050|23|printed "(দৌলতপুর থানা)"
Kushtia|Daulatpur|তারাগুনিয়া এস, ও|7051|23|
Kushtia|Daulatpur|খাসমথুরাপুর এস, ও|7052|23|
Meherpur|Meherpur Sadar|মেহেরপুর হেড অফিস|7100|23|
Meherpur|Meherpur Sadar|আমঝুপি এস, ও|7101|23|
Meherpur|Meherpur Sadar|মুজিব নগর কমপ্লেক্স এস, ও|7102|23|postal group as printed (Mujibnagar is now its own upazila)
Meherpur|Gangni|গাংনী ইউ, পি, ও|7110|23|
Chuadanga|Chuadanga Sadar|চুয়াডাংগা হেড অফিস|7200|23|spelt "চুয়াডাংগা" in the booklet
Chuadanga|Chuadanga Sadar|মুন্সিগঞ্জ এস, ও|7201|23|postal group as printed
Chuadanga|Alamdanga|আলমডাংগা ইউ, পি, ও|7210|23|bold print blurred in the scan; reading of the name uncertain
Chuadanga|Alamdanga|হারদী ই, ডি, এস, ও|7211|23|
Chuadanga|Damurhuda|দামুড়হুদা ইউ, পি, ও|7220|23|bold print blurred in the scan; reading of the name uncertain
Chuadanga|Damurhuda|দর্শনা (এল এস জি) এস, ও|7221|23|
Chuadanga|Damurhuda|আন্দুল বাড়ীয়া ই, ডি, এস, ও|7222|23|reading of the name uncertain (first letters faint); postal group as printed
Chuadanga|Jibannagar|দৌলতগঞ্জ ইউ, পি, ও|7230|23|printed "(জীবন নগর থানা)"; bold print blurred in the scan; reading of the name uncertain
Jhenaidah|Jhenaidah Sadar|ঝিনাইদহ হেড অফিস|7300|23|
Jhenaidah|Jhenaidah Sadar|ঝিনাইদহ ক্যাডেট কলেজ এস, ও|7301|23|
Jhenaidah|Harinakunda|হরিনাকুন্ড ইউ, পি, ও|7310|23|spelt "হরিনাকুন্ড" in the booklet
Jhenaidah|Shailkupa|শৈলকুপা ইউ, পি, ও|7320|23|
Jhenaidah|Shailkupa|কুমিরাদহ ই, ডি, এস, ও|7721|23|code printed "৭৭২১", outside the printed district range "৭৩০০-৭৩৯৯" (probably a misprint for 7321); kept as printed
Jhenaidah|Kotchandpur|কোটচাঁদপুর ইউ,, পি, ও|7330|23|
Jhenaidah|Maheshpur|মহেশপুর ইউ, পি, ও|7340|23|
Jhenaidah|Kaliganj|নলডাংগা ইউ, পি, ও|7350|23|printed "(কালিগঞ্জ থানা)"
Jhenaidah|Kaliganj|হাটবার বাজার এস, ও|7351|23|bold print blurred in the scan; reading of the name uncertain
Jashore|Jashore Sadar|যশোর হেড অফিস|7400|23|
Jashore|Jashore Sadar|যশোর উপ- শহর টি, এস, ও|7401|23|
Jashore|Jashore Sadar|চাঁচড়া ইউ, সি, টি, এস, সি, টি, এস, ও|7402|23|abbreviations after the name partly illegible in the scan
Jashore|Jashore Sadar|যশোর ক্যান্টনমেন্ট টি, এস, ও|7403|23|
Jashore|Jashore Sadar|যশোর এয়ারবেস টি, এস, ও|7404|23|
Jashore|Jashore Sadar|রুপদিয়া ই, ডি, এস, ও|7405|23|
Jashore|Jashore Sadar|বসুন্দিয়া এস, ও|7406|23|
Jashore|Jashore Sadar|চূড়ামনকাঠি এস, ও|7407|23|
Jashore|Chaugachha|চৌগাছা ইউ, পি, ও|7410|23|printed indented under the Jashore head office
Jashore|Jhikargachha|ঝিকরগাছা ইউ, পি, ও|7420|23|
Jashore|Sharsha|সারসা ইউ, পি, ও|7430|23|spelt "সারসা" in the booklet
Jashore|Sharsha|বেনাপোল এস, ও|7431|23|
Jashore|Sharsha|যাদবপুর এস, ও|7432|23|
Jashore|Sharsha|বাগ আচড়া ই, ডি, এস, ও|7433|23|
Jashore|Manirampur|মনিরামপুর ইউ, পি, ও|7440|23|
Jashore|Keshabpur|কেশবপুর ইউ, পি, ও|7450|23|
Jashore|Abhaynagar|নোয়াপাড়া ইউ, পি, ও|7460|23|printed "(অভয় নগর থানা)"
Jashore|Abhaynagar|রাজঘাট এস, ও|7461|23|
Jashore|Abhaynagar|ভূগিলহাট এস, ও|7462|23|
Jashore|Bagherpara|বাঘরপাড়া ইউ, পি, ও|7470|23|spelt "বাঘরপাড়া" in the booklet
Jashore|Bagherpara|গৌরনগর ই, ডি, এস, ও|7471|23|
Narail|Narail Sadar|নড়াইল হেড অফিস|7500|24|
Narail|Narail Sadar|রতনগঞ্জ এস, ও|7501|24|
Narail|Lohagara|লক্ষীপাশা ইউ, পি, ও|7510|24|printed "(লোহাগড়া থানা)"
Narail|Lohagara|লোহাগড়া এস, ও|7511|24|
Narail|Lohagara|ইটনা এস, ও|7512|24|
Narail|Lohagara|নলদী এস, ও|7513|24|
Narail|Lohagara|বড়দিয়া এস, ও|7514|24|postal group as printed
Narail|Kalia|কালিয় ইউ, পি, ও|7520|24|spelt "কালিয়" in the booklet
Narail|Kalia|মহাজন এস, ও|7521|24|
Magura|Magura Sadar|মাগুড়া হেড অফিস|7600|24|spelt "মাগুড়া" in the booklet
Magura|Sreepur|শ্রীপুর ইউ, পি, ও|7610|24|printed indented under the Magura head office
Magura|Sreepur|লাঙ্গলবাঁধ এস, ও|7611|24|
Magura|Sreepur|ন্যাকোল ই, ডি, এস, ও|7612|24|
Magura|Shalikha|আড়পাড়া ইউ, পি ও|7620|24|printed "(শালিখা থানা)"
Magura|Mohammadpur|মোহাম্মদপুর ইউ, পি, ও|7630|24|
Magura|Mohammadpur|বিনোদপুর ই, ডি, এস, ও|7631|24|
Magura|Mohammadpur|নহাটা এস, ও|7632|24|
Khulna||খুলনা জি, পি, ও|9000|26|Khulna city; printed as the section heading "খুলনা জি, পি, ও ৯০০০"
Khulna||খুলনা সিটি হেড অফিস|9100|26|Khulna city
Khulna||খুলনা শিপ ইয়ার্ড|9201|26|Khulna city ("খুলনা শহরের অন্যান্য বিলিকারী অফিস ও খুলনা জেলা ৯২০০-৯২৯৯"); no office type printed
Khulna||দৌলতপুর টি, এস, ও|9202|26|Khulna city
Khulna||বি, আই, টি খুলনা টি এস, ও|9203|26|Khulna city
Khulna||সিরমনি টি, এস, ও|9204|26|Khulna city
Khulna||জাহানাবাদ সেনানিবাস টি, এস, ও|9205|26|Khulna city
Khulna||সোনালী জুট মিলস্ টি, এস, ও|9206|26|Khulna city
Khulna||আটরা শিল্প এলাকা টি, এস, ও|9207|26|Khulna city
Khulna||খুলনা বিশ্ববিদ্যালয় এস, ও|9208|26|Khulna city
Khulna|Phultala|ফুলতলা ইউ, পি, ও|9210|27|
Khulna|Dighalia|দীঘলিয়া ইউ, পি, ও|9220|27|[inferred] Dighalia upazila office; printed "(দৌলতপুর থানা)" (Daulatpur is now a metropolitan thana)
Khulna|Dighalia|চন্দনী মহল এস, ও|9221|27|[inferred] postal group দীঘলিয়া, printed "(দৌলতপুর থানা)"
Khulna|Dighalia|সেনহাটী এস, ও|9222|27|[inferred] postal group দীঘলিয়া, printed "(দৌলতপুর থানা)"
Khulna|Dighalia|ঘোষঘাতি বারাকপুর ই, ডি, এস, ও|9223|27|[inferred] postal group দীঘলিয়া, printed "(দৌলতপুর থানা)"
Khulna|Dighalia|গাজীরহাট ই, ডি, এস, ও|9224|27|[inferred] postal group দীঘলিয়া, printed "(দৌলতপুর থানা)"
Khulna|Terokhada|তেরখাদা ইউ, পি, ও|9230|27|
Khulna|Terokhada|পাক বারাসাত ই, ডি, এস, ও|9231|27|
Khulna|Rupsa|আলাইপুর ইউ, পি, ও|9240|27|printed "(রুপসা থানা)"
Khulna|Rupsa|রূপসা ইষ্ট এস, ও|9241|27|
Khulna|Rupsa|বেলফুলিয়া এস, ও|9242|27|
Khulna|Dumuria|সাজিয়ারা ইউ, পি, ও|9250|27|printed "(ডুমুরিয়া থানা)"
Khulna|Dumuria|ঘোনাবান্দা ই, ডি, এস, ও|9251|27|
Khulna|Dumuria|চুকনগর এস, ও|9252|27|
Khulna|Dumuria|শাহাপুর এস, ও|9253|27|
Khulna|Batiaghata|বাটিয়াঘাট ইউ, পি, ও|9260|27|spelt "বাটিয়াঘাট" in the booklet
Khulna|Batiaghata|সুরকালী ই, ডি, এস, ও|9261|27|
Khulna|Dacope|চালনাবাজার ইউ, পি, ও|9270|27|printed "(দাকোপ থানা)"
Khulna|Dacope|দাকোপ ই, ডি, এস, ও|9271|27|
Khulna|Dacope|বাজুয়া এস, ও|9272|27|name partly covered by a mark in the scan; reading uncertain
Khulna|Dacope|নলিয়ান এস, ও|9273|27|
Khulna|Paikgachha|পাইক গাছা ইউ, পি, ও|9280|27|
Khulna|Paikgachha|গদাইপুর ই, ডি, এস, ও|9281|27|
Khulna|Paikgachha|কপিলমনি এস, ও|9282|27|
Khulna|Paikgachha|কাটিপাড়া ই, ডি, এস, ও|9283|27|
Khulna|Paikgachha|চাঁদখালী ই, ডি, এস, ও|9284|27|
Khulna|Paikgachha|গড়াইখালী এস, ও|9285|27|
Khulna|Koyra|মদিনাবাদ ইউ, পি, ও|9290|27|printed "(কয়রা থানা)"
Khulna|Koyra|আমাদী এস, ও|9291|27|
Bagerhat|Bagerhat Sadar|বাগেরহাট হেড অফিস|9300|27|
Bagerhat|Bagerhat Sadar|পি, সি, কলেজ এস, ও|9301|27|
Bagerhat|Bagerhat Sadar|রাংদিয়া কলেজ এস, ও|9302|27|
Bagerhat|Kachua|কচুয়া ইউ, পি, ও|9310|27|
Bagerhat|Kachua|সোনারকোলা এস, ও|9311|27|
Bagerhat|Morrelganj|মোরেলগঞ্জ ইউ, পি, ও|9320|27|
Bagerhat|Morrelganj|সন্ন্যাসী বাজার ই, ডি, এস, ও|9321|27|
Bagerhat|Morrelganj|তেলীসাতী এস, ও|9322|27|
Bagerhat|Sarankhola|রায়েন্দা ইউ, পি, ও|9330|27|printed "(স্বরণখোলা থানা)"
Bagerhat|Rampal|রামপাল ইউ, পি, ও|9340|27|
Bagerhat|Rampal|ফয়লাহাট এস, ও|9341|27|
Bagerhat|Rampal|সোনাতুনিয়া ই, ডি, এস, ও|9342|27|
Bagerhat|Rampal|গৌরম্ভ এস, ও|9343|27|
Bagerhat|Mongla|চালনা এ্যাংকোরেজ ইউ, পি, ও|9350|27|printed "(মংলাপোর্ট থানা)"
Bagerhat|Mongla|মংলা পোর্ট এস, ও|9351|27|
Bagerhat|Chitalmari|চিতলমারী টি, পি, ও|9360|27|office type printed "টি, পি, ও" (not used elsewhere in the booklet); type left empty
Bagerhat|Chitalmari|বড়বাড়িয়া ই, ডি, এস, ও|9361|27|
Bagerhat|Fakirhat|ফকিরহাট ইউ, পি, ও|9370|27|
Bagerhat|Fakirhat|মনসা ই, ডি, এস, ও|9371|27|
Bagerhat|Fakirhat|ভাংগনপাড় বাজার ই, ডি, এস, ও|9372|27|
Bagerhat|Mollahat|মোল্লাহাট ইউ, পি, ও|9380|27|
Bagerhat|Mollahat|কাহালপুর ই, ডি, এস, ও|9381|27|
Bagerhat|Mollahat|দাড়িয়ালা ই, ডি, এস, ও|9382|27|
Bagerhat|Mollahat|চরকুলিয়া এস, ও|9383|27|
Bagerhat|Mollahat|নগরকান্দি ই, ডি, এস, ও|9384|27|postal group as printed
Bagerhat|Mollahat|পাক গাংনী ই, ডি, এস, ও|9385|27|
Satkhira|Satkhira Sadar|সাতক্ষীরা হেড অফিস|9400|27|
Satkhira|Satkhira Sadar|সাতক্ষীরা ইসলামিয়া একাডেমী এস, ও|9401|27|
Satkhira|Satkhira Sadar|গুনাকার কাটি ই, ডি, এস, ও|9402|27|
Satkhira|Satkhira Sadar|বুধহাটা ই, ডি, এস, ও|9403|27|postal group as printed
Satkhira|Kalaroa|কলারোয়া ইউ, পি, ও|9410|27|
Satkhira|Kalaroa|মুরারীকাটি ই, ডি, এস, ও|9411|27|
Satkhira|Kalaroa|ঝাউডাংগা ই, ডি, এস, ও|9412|27|postal group as printed
Satkhira|Kalaroa|হামিদপুর ই, ডি, এস, ও|9413|27|
Satkhira|Kalaroa|খোরদো ই, ডি, এস, ও|9414|27|
Satkhira|Kalaroa|চন্দনপুর ই, ডি, এস, ও|9415|27|
Satkhira|Tala|তালা ইউ, পি, ও|9420|27|
Satkhira|Tala|পাটকেলঘাটা এস, ও|9421|27|
Satkhira|Debhata|দেবহাটা ইউ, পি, ও|9430|27|
Satkhira|Debhata|গুরুগ্রাম ই, ডি, এস, ও|9431|27|
Satkhira|Kaliganj|কালিগঞ্জ ইউ, পি, ও|9440|27|
Satkhira|Kaliganj|নলতা মোবারকনগর এস, ও|9441|27|
Satkhira|Kaliganj|রতনপুর ই, ডি, এস, ও|9442|27|
Satkhira|Shyamnagar|নকিপুর ইউ, পি, ও|9450|27|printed "(শ্যামনগর থানা)"
Satkhira|Shyamnagar|নূরনগর ই, ডি, এস, ও|9451|27|
Satkhira|Shyamnagar|নওবেকী ই, ডি, এস, ও|9452|27|reading of the name uncertain (a mark between letters in the scan)
Satkhira|Shyamnagar|বুড়ি গোয়ালিনী ই, ডি, এস, ও|9453|27|
Satkhira|Shyamnagar|গাবুরা ই, ডি, এস, ও|9454|27|
Satkhira|Shyamnagar|হরিনগর ই, ডি, এস, ও|9455|27|
Satkhira|Assasuni|আশাশুনি ইউ, পি, ও|9460|27|
Satkhira|Assasuni|বড়দল এস, ও|9461|27|
"""
# Barishal Division: the same booklet, "খুলনা রিজিয়ন ৭০০০-৯৯৯৯". Booklet p. 25 (PDF page 14, right half, from "বরিশাল জেলা
# ৮২০০-৮২৯৯": Barishal, Bhola and the Jhalokathi head-office group; the Gopalganj section above it is left out) and p. 26 (PDF
# page 15, left half: the rest of Jhalokathi, Pirojpur, Patuakhali and Barguna, up to "খুলনা জি, পি, ও ৯০০০"), transcribed by
# hand from the page images in raw/. Upazila = the postal group as printed; "[inferred]" as for Rangpur.
T_BARISHAL = """
Barishal|Barishal Sadar|বরিশাল হেড অফিস|8200|25|Barishal city; "হেড অ" partly covered by an ink mark in the scan
Barishal|Barishal Sadar|বুখাইনগর ই, ডি, এস, ও|8201|25|postal group as printed (Barishal head office)
Barishal|Barishal Sadar|সাহেবের হাট ই, ডি,এস, ও|8202|25|postal group as printed (Barishal head office)
Barishal|Barishal Sadar|সুগন্দিয়া ই, ডি, এস, ও|8203|25|postal group as printed (Barishal head office)
Barishal|Barishal Sadar|পতাং ই, ডি,এস, ও|8204|25|postal group as printed (Barishal head office)
Barishal|Barishal Sadar|কাশিপুর ই, ডি, এস, ও|8205|25|postal group as printed (Barishal head office)
Barishal|Barishal Sadar|জাগুয়ারহাট ই, ডি,এস, ও|8206|25|postal group as printed (Barishal head office)
Barishal|Barishal Sadar|রুপাতলী হাউজিং এস্টেট এস, ও|8207|25|postal group as printed (Barishal head office)
Barishal|Babuganj|বাবুগঞ্জ ইউ, পি, ও|8210|25|
Barishal|Babuganj|রহমতপুর এস, ও|8211|25|
Barishal|Babuganj|চাঁদপাশা ই, ডি, এস, ও|8212|25|
Barishal|Babuganj|মাধবপাশা ই, ডি, এস, ও|8213|25|
Barishal|Babuganj|ঠাকুর মল্লিক এস, ও|8214|25|
Barishal|Babuganj|নিজামউদ্দিন কলেজ ই, ডি, এস, ও|8215|25|
Barishal|Babuganj|বরিশাল ক্যাডেট কলেজ এস, ও|8216|25|
Barishal|Babuganj|বাবুগঞ্জ বন্দর এস, ও|8217|25|
Barishal|Wazirpur|উজিরপুর ইউ, পি, ও|8220|25|
Barishal|Wazirpur|ধামড়া এস, ও|8221|25|reading of the name uncertain (blurred print)
Barishal|Wazirpur|জুগারকান্দা এস, ও|8222|25|reading of the name uncertain (blurred print)
Barishal|Wazirpur|ডাকুয়ার হাট ই, ডি, এস, ও|8223|25|
Barishal|Wazirpur|শিকারপুর এস, ও|8224|25|
Barishal|Gaurnadi|গৌরনদী ইউ, পি, ও|8230|25|
Barishal|Gaurnadi|টরকী বন্দর এস, ও|8231|25|
Barishal|Gaurnadi|কাশেমাবাদ এস, ও|8232|25|
Barishal|Gaurnadi|বাটাজোর এস, ও|8233|25|
Barishal|Agailjhara|আগৈলঝারা ইউ, পি, ও|8240|25|spelt "আগৈলঝারা" in the booklet
Barishal|Agailjhara|গৈলা এস, ও|8241|25|
Barishal|Agailjhara|পয়সারহাট এস, ও|8242|25|
Barishal|Muladi|মুলাদী ইউ, পি, ও|8250|25|
Barishal|Muladi|কাজিরচর ই, ডি, এস, ও|8251|25|
Barishal|Muladi|চরকালেখান ই, ডি, এস, ও|8252|25|
Barishal|Hizla|বড়জালিয়া ইউ, পি, ও|8260|25|printed "(হিজলা থানা)"
Barishal|Hizla|ওসমান মঞ্জিল এস, ও|8261|25|a pen mark crosses the type in the scan
Barishal|Mehendiganj|মেহেন্দীগঞ্জ ইউ,, পি, ও|8270|25|
Barishal|Mehendiganj|লস্করপুর ই, ডি, এস, ও|8271|25|
Barishal|Mehendiganj|উলানিয়া এস, ও|8272|25|
Barishal|Mehendiganj|নলগোরা ই, ডি, এস, ও|8273|25|
Barishal|Mehendiganj|লেংগুটিয়া এস, ও|8274|25|
Barishal|Bakerganj|সাহেবগঞ্জ ইউ, পি, ও|8280|25|printed "(বাখরগঞ্জ থানা)"
Barishal|Bakerganj|চরামদ্দি ই, ডি, এস, ও|8281|25|
Barishal|Bakerganj|পাদ্রী শিবপুর এস, ও|8282|25|
Barishal|Bakerganj|শিয়ালগুনি ই, ডি, এস, ও|8283|25|
Barishal|Bakerganj|কলসকাটি এস, ও|8284|25|
Bhola|Bhola Sadar|ভোলা হেড অফিস|8300|25|
Bhola|Bhola Sadar|জয়নগর এস, ও|8301|25|
Bhola|Daulatkhan|দৌলতখান ইউ, পি, ও|8310|25|
Bhola|Daulatkhan|হাজীপুর মাদ্রাসা এস, ও|8311|25|
Bhola|Burhanuddin|বোরহানউদ্দিন ইউ, পি, ও|8320|25|
Bhola|Burhanuddin|মির্জাকালু এস, ও|8321|25|
Bhola|Lalmohan|লালমোহন ইউ, পি, ও|8330|25|
Bhola|Lalmohan|ডাউরীহাট ই, ডি, এস, ও|8331|25|
Bhola|Lalmohan|গজারিয়া এস, এ|8332|25|type printed "এস, এ" (no office type matched)
Bhola|Char Fasson|চরফ্যাশন ইউ, পি, ও|8340|25|
Bhola|Char Fasson|দুলারহাট ই, ডি, এস, ও|8341|25|
Bhola|Char Fasson|কেরামতগঞ্জ ই, ডি, এস, ও|8342|25|
Bhola|Tazumuddin|হাটশশীগঞ্জ ইউ, পি, ও|8350|25|printed "(তজমুদ্দিন থানা)"
Bhola|Manpura|হাজীরহাট ইউ, পি, ও|8360|25|printed "(মনপুরা থানা)"
Jhalokathi|Jhalokathi Sadar|ঝালকাঠি হেড অফিস|8400|25|
Jhalokathi|Jhalokathi Sadar|নবগ্রাম ই, ডি, এস, ও|8401|25|
Jhalokathi|Jhalokathi Sadar|বাউকাঠি ই, ডি, এস, ও|8402|25|
Jhalokathi|Jhalokathi Sadar|গাভা ই, ডি, এস, ও|8403|25|
Jhalokathi|Jhalokathi Sadar|শেখেরহাট ই, ডি, এস, ও|8404|25|
Jhalokathi|Rajapur|রাজাপুর ইউ, পি, ও|8410|26|
Jhalokathi|Nalchity|নলছিটি ইউ, পি, ও|8420|26|
Jhalokathi|Nalchity|বীরকাঠি এস, ও|8421|26|
Jhalokathi|Kanthalia|কাঠালিয়া ইউ, পি, ও|8430|26|
Jhalokathi|Kanthalia|আমুয়া এস, ও|8431|26|
Jhalokathi|Kanthalia|নিয়ামতী এস, এ|8432|26|type printed "এস, এ" (no office type matched)
Jhalokathi|Kanthalia|শৌলজালিয়া এস, ও|8433|26|
Pirojpur|Pirojpur Sadar|পিরোজপুর হেড অফিস|8500|26|
Pirojpur|Pirojpur Sadar|হুলারহাট এস, ও|8501|26|
Pirojpur|Pirojpur Sadar|পারেরহাট এস, ও|8502|26|
Pirojpur|Kawkhali|কাউখালি ইউ, পি, ও|8510|26|
Pirojpur|Kawkhali|কেউন্দিয়া ই, ডি, এস, ও|8511|26|
Pirojpur|Kawkhali|জয়কুল ই, ডি, এস, ও|8512|26|
Pirojpur|Kawkhali|জোলাগতি ই, ডি, এস, ও|8513|26|
Pirojpur|Nesarabad|স্বরুপকাঠি ইউ, পি, ও|8520|26|[inferred] Nesarabad upazila office; printed as postal group স্বরুপকাঠি (Swarupkathi, the upazila's former name)
Pirojpur|Nesarabad|দারুস সুন্নত এস, ও|8521|26|[inferred] postal group স্বরুপকাঠি
Pirojpur|Nesarabad|কৌড়িখাড়া এস, ও|8522|26|[inferred] postal group স্বরুপকাঠি
Pirojpur|Nesarabad|জলাবাড়ী এস, ও|8523|26|[inferred] postal group স্বরুপকাঠি
Barishal|Banaripara|বানড়ীপাড়া ইউ, পি, ও|8530|26|printed under the Pirojpur district heading (postal grouping); Banaripara upazila is in Barishal District; spelt "বানড়ীপাড়া" in the booklet
Barishal|Banaripara|চাঁখার এস, ও|8531|26|printed under the Pirojpur district heading (postal grouping), postal group বানড়ীপাড়া (Banaripara upazila, Barishal District)
Pirojpur|Nazirpur|নাজিরপুর ইউ, পি, ও|8540|26|
Pirojpur|Nazirpur|শ্রীরামকাঠি এস, ও|8541|26|
Pirojpur|Bhandaria|ভান্ডারিয়া ইউ, পি, ও|8550|26|
Pirojpur|Bhandaria|কানুদাসকাঠি ই, ডি, এস, ও|8550|26|code printed "৮৫৫০", the same as Bhandaria UPO (probably 8551); kept as printed
Pirojpur|Bhandaria|ধাওয়া ই, ডি, এস, ও|8552|26|
Pirojpur|Mathbaria|মঠবাড়িয়া ইউ, পি, ও|8560|26|
Pirojpur|Mathbaria|তুষখালী এস, ও|8561|26|
Pirojpur|Mathbaria|হলতা ই, ডি, এস, ও|8562|26|
Pirojpur|Mathbaria|গুলিশাখালী এস, ও|8563|26|
Pirojpur|Mathbaria|টিয়ারখালি এস, ও|8564|26|
Pirojpur|Mathbaria|বেতমোর নতুন হাট ই, ডি, এস, ও|8565|26|
Pirojpur|Mathbaria|শিলারগঞ্জ ই, ডি, এস, ও|8566|26|
Patuakhali|Patuakhali Sadar|পটুয়াখালী হেড অফিস|8600|26|
Patuakhali|Patuakhali Sadar|মৌকরণ এস, ও|8601|26|
Patuakhali|Patuakhali Sadar|দুমকী এস, ও|8602|26|postal group as printed (Dumki is now its own upazila)
Patuakhali|Patuakhali Sadar|রহিমাবাদ ই, ডি, এস, ও|8603|26|
Patuakhali|Mirzaganj|সুবিদখালী ইউ, পি, ও|8610|26|[inferred] Mirzaganj upazila office (Subidkhali); no thana printed
Patuakhali|Mirzaganj|কাঠালতলী বাজার এস, ও|8611|26|[inferred] postal group সুবিদখালী
Patuakhali|Bauphal|বাউফল ইউ, পি, ও|8620|26|
Patuakhali|Bauphal|বাগাবন্দর এস, ও|8621|26|
Patuakhali|Bauphal|বীরপাশা এস, ও|8522|26|code printed "৮৫২২", outside Patuakhali's printed range "৮৬০০-৮৬৯৯" and the same as Pirojpur's কৌড়িখাড়া (probably 8622); kept as printed
Patuakhali|Bauphal|কালিসড়ি এস, ও|8523|26|code printed "৮৫২৩", outside Patuakhali's printed range "৮৬০০-৮৬৯৯" and the same as Pirojpur's জলাবাড়ী (probably 8623); kept as printed
Patuakhali|Bauphal|কালাইয়া এস, ও|8624|26|[inferred] postal group বাউফল: printed without indent after the Bauphal group, code in its 862x range
Patuakhali|Dashmina|দশমিনা ইউ, পি, ও|8630|26|
Patuakhali|Galachipa|গলাচিপ ইউ, পি, ও|8640|26|spelt "গলাচিপ" in the booklet
Patuakhali|Galachipa|গাজীপুর বন্দর এস, ও|8641|26|
Patuakhali|Kalapara|খেপুপাড়া ইউ, পি, ও|8650|26|[inferred] Kalapara upazila office (Khepupara); no thana printed
Patuakhali|Kalapara|মহিপুর ই, ডি, এস, ও|8651|26|[inferred] postal group খেপুপাড়া
Barguna|Barguna Sadar|বরগুনা হেড অফিস|8700|26|
Barguna|Barguna Sadar|নলি বন্দর ই, ডি, এস, ও|8701|26|
Barguna|Amtali|আমতলী ইউ, পি, ও|8710|26|
Barguna|Patharghata|পাথরঘাটা ইউ, পি, ও|8720|26|
Barguna|Patharghata|কাকচিরা এস, ও|8721|26|
Barguna|Bamna|বামনা ইউ, পি, ও|8730|26|
Barguna|Betagi|বেতাগী ইউ, পি, ও|8740|26|
Barguna|Betagi|দারুল উলুম ই, ডি, এস, ও|8741|26|
"""
# Sylhet Division: the same booklet, "চট্টগ্রাম রিজিয়ন ৩০০০-৪৯৯৯". Booklet p. 13 (PDF page 8, right half, from "সুনামগঞ্জ জেলা
# ৩০০০-৩০৯৯": Sunamganj and the start of Sylhet; the print is faded, codes or names that cannot be read are left empty or
# the row is left out), p. 14 (PDF page 9, left half: Sylhet, Moulvibazar, Habiganj) and p. 15 (PDF page 9, right half,
# first column up to "ব্রাহ্মণবাড়ীয়া জেলা ৩৪০০-৩৪৯৯": the rest of Habiganj), transcribed by hand from the page images in
# raw/. Upazila = the postal group as printed; "[inferred]" as for Rangpur. An empty code = illegible in the scan.
T_SYLHET = """
Sunamganj|Sunamganj Sadar|সুনামগঞ্জ হেড অফিস|3000|13|
Sunamganj|Sunamganj Sadar|পাগলা এস, ও|3001|13|postal group as printed (Sunamganj head office); Pagla is now in South Sunamganj (Shantiganj) upazila
Sunamganj|Sunamganj Sadar|পাথারিয়া এস, ও|3002|13|postal group as printed (Sunamganj head office)
Sunamganj|Bishwambarpur|বিশ্বম্বরপুর ইউ, পি, ও|3010|13|spelt "বিশ্বম্বরপুর" in the booklet
Sunamganj|Jamalganj|সাচনা ইউ, পি, ও|3020|13|printed "(জামালগঞ্জ থানা)"
Sunamganj|Tahirpur|তাহিরপুর ইউ, পি, ও|3030|13|
Sunamganj|Derai|দিরাই চাঁদপুর ইউ, পি, ও|3040|13|printed "(দিরাই থানা)"
Sunamganj|Derai|জগদল ই, ডি, এস, ও|3041|13|
Sunamganj|Shalla|ঘুংগিয়ার গাও ইউ, পি, ও|3050|13|printed "(সাল্লা থানা)" on the next line; reading of the name uncertain (faded print)
Sunamganj|Jagannathpur|জগন্নাথপুর ইউ, পি, ও|3060|13|
Sunamganj|Jagannathpur|সৈয়দপুর এস, ও|3061|13|reading of the name uncertain (faded print)
Sunamganj|Jagannathpur|আতুয়াজান বরকাপন এস, ও|3062|13|reading of the name uncertain (faded print)
Sunamganj|Jagannathpur|হাসান ফাতেমাপুর এস, ও|3063|13|reading of the name uncertain (faded print)
Sunamganj|Jagannathpur|রসুলগঞ্জ এস, ও|3064|13|
Sunamganj|Jagannathpur|শ্রীরামসী এস, ও|3065|13|
Sunamganj|Dowarabazar|দুয়ারা বাজার ইউ, পি, ও|3070|13|
Sunamganj|Chhatak|ছাতক ইউ, পি, ও|3080|13|
Sunamganj|Chhatak|ছাতক সিমেন্ট ফ্যাক্টরী এস, ও|3081|13|reading of the name uncertain (faded print)
Sunamganj|Chhatak|ছাতক পেপার মিলস্ লিঃ এস, ও|3082|13|
Sunamganj|Chhatak|গোবিন্দগঞ্জ এস, ও|3083|13|
Sunamganj|Chhatak|গোবিন্দগঞ্জ নতুন বাজার এস, ও|3084|13|reading of the name uncertain (faded print)
Sunamganj|Chhatak|খুরমা ই, ডি, এস, ও||13|code printed "৩০৮" + an illegible last digit (faded print); left empty
Sylhet|Sylhet Sadar|সিলেট হেড অফিস||13|code illegible in the scan (faded print; the section heading reads "৩১০০-৩১৯৯"); left empty
Sylhet|Sylhet Sadar|সিলেট ক্যাডেট কলেজ টি, এস, ও||13|postal group as printed (Sylhet head office); code illegible in the scan (faded print); left empty
Sylhet|Sylhet Sadar|সিলেট বিমান বন্দর টি, এস, ও||13|postal group as printed (Sylhet head office); code illegible in the scan (faded print); left empty
Sylhet|Sylhet Sadar|খাদিম নগর এস, ও||13|postal group as printed (Sylhet head office); code printed "৩১০" + an illegible last digit (faded print); left empty
Sylhet|Sylhet Sadar|জালালাবাদ ক্যান্টনমেন্ট এস, ও||13|postal group as printed (Sylhet head office); code printed "৩১০" + an illegible last digit (faded print); left empty
Sylhet|Sylhet Sadar|সিলাম এস, ও|3105|13|postal group as printed (Sylhet head office)
Sylhet|Sylhet Sadar|বিরাহিমপুর এস, ও|3106|13|postal group as printed (Sylhet head office)
Sylhet|Sylhet Sadar|জালালপুর ই, ডি, এস, ও|3107|13|postal group as printed (Sylhet head office)
Sylhet|Sylhet Sadar|মোগলা বাজার এস, ও|3108|14|postal group as printed (Sylhet head office)
Sylhet|Sylhet Sadar|রেংগা হাজীগঞ্জ এস, ও|3109|14|postal group as printed (Sylhet head office)
Sylhet|Sylhet Sadar|কদমতলী এস, ও|3111|14|postal group as printed (Sylhet head office)
Sylhet|Sylhet Sadar|কামাল বাজার এস, ও|3112|14|postal group as printed (Sylhet head office)
Sylhet|Sylhet Sadar|লালা বাজার এস, ও|3113|14|postal group as printed (Sylhet head office)
Sylhet|Sylhet Sadar|শাহজালাল বিজ্ঞান ও প্রযুক্তি বিশ্ববিদ্যালয় এস, ও|3114|14|postal group as printed (Sylhet head office); name printed over two lines
Sylhet|Fenchuganj|ফেঞ্চুগঞ্জ ইউ, পি, ও|3116|14|
Sylhet|Fenchuganj|ফেঞ্চুগঞ্জ সার কারখানা এস, ও|3117|14|
Sylhet|Fenchuganj|ভাটেরা এস, ও|3118|14|
Sylhet|Balaganj|বালাগঞ্জ ইউ, পি, ও|3120|14|
Sylhet|Balaganj|করুয়া এস, ও|3121|14|
Sylhet|Balaganj|ব্রাহ্মণ শাসন এস, ও|3122|14|
Sylhet|Balaganj|তাজপুর এস, ও|3123|14|postal group as printed (Balaganj); Tajpur is now in Osmani Nagar upazila
Sylhet|Balaganj|গোয়ালা বাজার এস, ও|3124|14|postal group as printed (Balaganj); Goala Bazar is now in Osmani Nagar upazila
Sylhet|Balaganj|বেগমপুর এস, ও|3125|14|
Sylhet|Balaganj|ওমরপুর এস, ও|3126|14|
Sylhet|Balaganj|কাঁঠাল খাইড় এস, ও|3127|14|
Sylhet|Balaganj|গহরপুর এস, ও|3128|14|
Sylhet|Balaganj|নতুন বাজার এস, ও|3129|14|
Sylhet|Bishwanath|বিশ্বনাথ ইউ, পি, ও|3130|14|
Sylhet|Bishwanath|দশঘর এস, ও|3131|14|
Sylhet|Bishwanath|দৌলতপুর এস, ও|3132|14|
Sylhet|Bishwanath|দেওকলস এস, ও|3133|14|
Sylhet|Bishwanath|সিংগের কাঁচ এস, ও|3134|14|
Sylhet|Companiganj|কোম্পানীগঞ্জ নতুন বাজার ইউ, পি, ও|3140|14|printed "নতুন বাজা র" (a space inside the word) and "(কোম্পানীগঞ্জ থানা)" on the next line
Sylhet|Gowainghat|গোয়াইনঘাট ইউ, পি ও|3150|14|
Sylhet|Gowainghat|জাফলং এস, ও|3151|14|printed without indent after the Gowainghat office
Sylhet|Gowainghat|চিকনাগুল ই, ডি, এস, ও|3152|14|postal group as printed (Gowainghat)
Sylhet|Jaintiapur|জৈন্তাপুর ইউ, পি, ও|3156|14|
Sylhet|Golapganj|গোলাপগঞ্জ ইউ, পি ও|3160|14|
Sylhet|Golapganj|ঢাকা দক্ষিণ এস, ও|3161|14|
Sylhet|Golapganj|দক্ষিণ ভাদেশ্বর ই, ডি, এস, ও|3162|14|
Sylhet|Golapganj|রানাপিং এস, ও|3163|14|
Sylhet|Golapganj|বানীগ্রাম এস, ও|3164|14|
Sylhet|Golapganj|চন্দরপুর কাচ এস, ও|3165|14|
Sylhet|Beanibazar|বিয়ানীবাজার ইউ, পি ও|3170|14|the first letter is printed with a stray mark (it can read "বৈয়ানীবাজার")
Sylhet|Beanibazar|জলঢুপ এস, ও|3171|14|
Sylhet|Beanibazar|মাথিউরা বাজার এস, ও|3172|14|
Sylhet|Beanibazar|কুড়ার বাজার ই, ডি, এস, ও|3173|14|
Sylhet|Beanibazar|সেলিয়া বাজার ই, ডি, এস, ও|3174|14|
Sylhet|Beanibazar|চুরখাই এস, ও|3175|14|
Sylhet|Kanaighat|কানাইঘাট ইউ, পি ও|3180|14|
Sylhet|Kanaighat|চতুল বাজার এস, ও|3181|14|
Sylhet|Kanaighat|মানিকগঞ্জ এস, ও|3182|14|
Sylhet|Kanaighat|গাছবাড়ী এস, ও|3183|14|
Sylhet|Zakiganj|জকিগঞ্জ ইউ, পি, ও|3190|14|
Sylhet|Zakiganj|ইছামতি এস, ও|3191|14|
Moulvibazar|Moulvibazar Sadar|মৌলভী বাজার হেড অফিস|3200|14|
Moulvibazar|Moulvibazar Sadar|বড়কাপন এস, ও|3201|14|
Moulvibazar|Moulvibazar Sadar|মনুমুখ এস, ও|3202|14|
Moulvibazar|Moulvibazar Sadar|আফরোজগঞ্জ এস, ও|3203|14|
Moulvibazar|Sreemangal|শ্রীমংগল ইউ, পি, ও|3210|14|spelt "শ্রীমংগল" in the booklet
Moulvibazar|Sreemangal|নারাইন ছড়া এস, ও|3211|14|
Moulvibazar|Sreemangal|কালিঘাট এস, ও|3212|14|
Moulvibazar|Sreemangal|খেজুরী ছড়া এস, ও|3213|14|
Moulvibazar|Sreemangal|সাতগাঁও এস, ও|3214|14|
Moulvibazar|Kamalganj|কমলগঞ্জ ইউ, পি, ও|3220|14|
Moulvibazar|Kamalganj|কেরামত নগর ভানুগাছ এস, ও||14|code printed "৩২২" (a digit missing); left empty
Moulvibazar|Kamalganj|পত্রখোলা এস, ও|3222|14|
Moulvibazar|Kamalganj|সমশের নগর এস, ও|3223|14|
Moulvibazar|Kamalganj|মুন্সী বাজার এস, ও|3224|14|
Moulvibazar|Kulaura|কুলাউড়া ইউ, পি, ও|3230|14|
Moulvibazar|Kulaura|টিলাগাঁও এস, ও|3231|14|
Moulvibazar|Kulaura|লংলা এস, ও|3232|14|
Moulvibazar|Kulaura|পৃথিম পাশা এস, ও|3233|14|
Moulvibazar|Kulaura|কাজলধারা এস, ও|3234|14|
Moulvibazar|Kulaura|করিমপুর এস, ও|3235|14|
Moulvibazar|Kulaura|বরমচাল এস, ও|3237|14|
Moulvibazar|Rajnagar|রাজনগর ইউ, পি, ও|3240|14|
Moulvibazar|Barlekha|বড়লেখা ইউ, পি, ও|3250|14|"ও" partly faded
Moulvibazar|Barlekha|পূর্ব শাহবাজপুর এস, ও|3253|14|
Habiganj|Habiganj Sadar|হবিগঞ্জ হেড অফিস|3300|14|
Habiganj|Habiganj Sadar|শায়েস্তাগঞ্জ এস, ও|3301|14|postal group as printed (Habiganj head office); Shayestaganj is now its own upazila
Habiganj|Habiganj Sadar|গোপায়া ই, ডি, এস, ও|3302|14|
Habiganj|Bahubal|বাহুবল ইউ, পি, ও|3310|14|
Habiganj|Chunarughat|চুনারুঘাট ইউ, পি, ও|3320|14|
Habiganj|Chunarughat|চাঁদপুর বাগান এস, ও|3321|14|
Habiganj|Chunarughat|নরপতি ই, ডি, এস, ও|3322|14|
Habiganj|Madhabpur|মাধবপুর ইউ, পি, ও|3330|15|
Habiganj|Madhabpur|ইটাখোলা এস, ও|3331|15|
Habiganj|Madhabpur|শাহাজী বাজার এস, ও|3332|15|the last letter of "বাজার" is unclear in the print (it can read "বাজাব")
Habiganj|Madhabpur|সায়হামনগর এস, ও|3333|15|
Habiganj|Lakhai|কালাউক ইউ, পি, ও|3340|15|printed "(লাখাই থানা)"
Habiganj|Lakhai|লাখাই এস, ও|3341|15|
Habiganj|Baniachong|বানিয়াচং ইউ, পি, ও|3350|15|
Habiganj|Baniachong|যাত্রা পাশা এস, ও|3351|15|
Habiganj|Baniachong|কাদিরগঞ্জ এস, ও|3352|15|
Habiganj|Ajmiriganj|আজমিরীগঞ্জ ইউ, পি, ও|3360|15|
Habiganj|Nabiganj|নবিগঞ্জ ইউ, পি, ও|3370|15|
Habiganj|Nabiganj|গোপলার বাজার ই, ডি, এস, ও|3371|15|
Habiganj|Nabiganj|গোলডুবা ই, ডি, এস, ও|3372|15|
Habiganj|Nabiganj|দিঘলবাক এস, ও|3373|15|
Habiganj|Nabiganj|ইনাথগঞ্জ ই, ডি, এস, ও|3374|15|
"""
# Mymensingh Division: booklet p. 12 (PDF page 8, left half: "জামালপুর জেলা ২০০০-২০৯৯", "শেরপুর জেলা ২১০০-২১৯৯",
# "ময়মনসিংহ জেলা ২২০০-২২৯৯", up to "কিশোরগঞ্জ জেলা ২৩০০-২৩৯৯", Dhaka Division, already collected) and p. 13 (PDF page 8,
# right half, first column: "নেত্রকোনা জেলা ২৪০০-২৪৯৯"), transcribed by hand from raw/postcode_booklet_pp12-13.png (the
# same native-resolution image as in the Sylhet folder). Upazila = the postal group as printed; "[inferred]" as for Rangpur;
# offices printed under a district they do not belong to carry the seed's district and a note. Dharmapasha (2450) and
# Madhyanagar (2456), printed in the Netrokona section, are in Sunamganj District (Sylhet Division) and are left out here.
T_MYMENSINGH = """
Jamalpur|Jamalpur Sadar|জামালপুর হেড অফিস|2000|12|
Jamalpur|Jamalpur Sadar|নান্দিনা এস, ও|2001|12|postal group as printed (Jamalpur head office)
Jamalpur|Jamalpur Sadar|নরুন্দি এস, ও|2002|12|postal group as printed (Jamalpur head office)
Jamalpur|Melandah|মেলান্দহ বাজার ইউ, পি, ও|2010|12|
Jamalpur|Melandah|জামালপুর ই, ডি, এস, ও|2011|12|
Jamalpur|Melandah|মালঞ্চ এস, ও|2012|12|
Jamalpur|Melandah|মাহমুদপুর এস, ও|2013|12|
Jamalpur|Islampur|ইসলামপুর ইউ, পি, ও|2020|12|
Jamalpur|Islampur|দূরমুট এস, ও|2021|12|
Jamalpur|Islampur|গিলাবাড়ী এস, ও|2022|12|
Jamalpur|Dewangonj|দেওয়ানগঞ্জ ইউ, পি, ও|2030|12|
Jamalpur|Dewangonj|দেওয়ানগঞ্জ এস, মিলস, এস, ও|2031|12|
Jamalpur|Madarganj|মাদারগঞ্জ ইউ, পি, ও|2040|12|last digit of the code faint in the scan; read as 2040
Jamalpur|Madarganj|বালিঝুরি এস, ও|2041|12|
Jamalpur|Sarishabari|সরিষাবাড়ী ইউ, পি, ও|2050|12|
Jamalpur|Sarishabari|গুনেরবাড়ী এস, ও|2051|12|
Jamalpur|Sarishabari|বাউসী এস, ও|2052|12|
Jamalpur|Sarishabari|জগন্নাথ ঘাট এস, ও|2053|12|
Jamalpur|Sarishabari|পিংনা এস, ও|2054|12|
Jamalpur|Sarishabari|যমুনা সার কারখানা এস, ও|2055|12|reading of "কারখানা" uncertain (faded print)
Sherpur|Sherpur Sadar|শেরপুর হেড অফিস|2100|12|
Sherpur|Nalitabari|নালিতাবাড় ইউ, পি,ও|2110|12|spelt "নালিতাবাড়" in the booklet
Sherpur|Nalitabari|হাতিবান্দা এস, ও|2111|12|
Sherpur|Jhenaigati|ঝিনাইগাত ইউ, পি, ও|2120|12|spelt "ঝিনাইগাত" in the booklet
Sherpur|Sreebordi|শ্রীবরদী ইউ, পি, ও|2130|12|
Jamalpur|Bokshiganj|বকশীগঞ্জ ইউ, পি, ও|2140|12|printed under "শেরপুর জেলা ২১০০-২১৯৯"; Bokshiganj upazila is in Jamalpur District
Sherpur|Nokla|নকলা ইউ, পি,ও|2150|12|
Sherpur|Nokla|গনপদ্দি এস, ও|2151|12|
Mymensingh|Mymensingh Sadar|ময়মনসিংহ হেড অফিস|2200|12|
Mymensingh|Mymensingh Sadar|কেওয়াট খালী এস, ও|2201|12|postal group as printed (Mymensingh head office)
Mymensingh|Mymensingh Sadar|কৃষি বিশ্ববিদ্যালয় এস, ও|2202|12|postal group as printed (Mymensingh head office)
Mymensingh|Mymensingh Sadar|শম্ভুগঞ্জ এস, ও|2203|12|postal group as printed (Mymensingh head office)
Mymensingh|Mymensingh Sadar|বিদ্যাগঞ্জ এস, ও|2204|12|postal group as printed (Mymensingh head office)
Mymensingh|Mymensingh Sadar|পিয়ারপুর এস, ও|2205|12|postal group as printed (Mymensingh head office)
Mymensingh|Mymensingh Sadar|সানকীপাড়া কলোনী এস, ও|2206|12|postal group as printed (Mymensingh head office)
Mymensingh|Mymensingh Sadar|ময়মনসিংহ মেডিকেল কলেজ এস, ও|2207|12|postal group as printed (Mymensingh head office)
Mymensingh|Mymensingh Sadar|খাগডহর এস, ও|2208|12|postal group as printed (Mymensingh head office)
Mymensingh|Muktagacha|মুক্তাগাছা ইউ, পি, ও|2210|12|
Mymensingh|Fulbaria|ফুলবাড়ীয়া ইউ, পি, ও|2216|12|
Mymensingh|Trishal|ত্রিশাল ইউ, পি, ও|2220|12|
Mymensingh|Trishal|আহমদাবাদ ই, ডি, এস, ও|2221|12|
Mymensingh|Trishal|রাম অমৃতগঞ্জ ই, ডি, এস. ও|2222|12|
Mymensingh|Trishal|ধলা এস, ও|2223|12|printed without an indent, after the Trishal group; kept in that group
Mymensingh|Gafargaon|গফরগাঁও ইউ, পি, ও|2230|12|
Mymensingh|Gafargaon|শিবগঞ্জ ই, ডি, এস, ও|2231|12|
Mymensingh|Gafargaon|উস্তি এস, ও|2232|12|
Mymensingh|Gafargaon|কান্দিপাড়া এস, ও|2233|12|
Mymensingh|Gafargaon|দত্তেরবাজার ই, ডি, এস, ও|2234|12|
Mymensingh|Bhaluka|ভালুকা ইউ, পি, ও|2240|12|
Mymensingh|Phulpur|ফুলপুর ইউ, পি, ও|2250|12|
Mymensingh|Phulpur|বেলটিয়া বালিয়া ই, ডি, এস. ও|2251|12|
Mymensingh|Phulpur|তারাকান্দা এস, ও|2252|12|postal group as printed (Tarakanda is now its own upazila)
Mymensingh|Haluaghat|হালুয়াঘাট ইউ, পি, ও|2260|12|
Mymensingh|Haluaghat|ধারা ই, ডি, এস, ও|2261|12|
Mymensingh|Haluaghat|মুন্সিরহাট এস, ও|2262|12|
Mymensingh|Gouripur|গৌরীপুর ইউ, পি, ও|2270|12|
Mymensingh|Gouripur|রামগোপালপুর এস, ও|2271|12|
Mymensingh|Iswarganj|ঈশ্বরগঞ্জ ইউ, পি, ও|2280|12|
Mymensingh|Iswarganj|সোহাগী ই, ডি, এস, ও|2281|12|
Mymensingh|Iswarganj|আঠারবাড়ী এস, ও|2282|12|
Mymensingh|Nandail|নান্দাইল ইউ, পি, ও|2290|12|
Mymensingh|Nandail|গাংগাইল এস, ও|2291|12|
Netrokona|Netrokona Sadar|নেত্রকোনা হেড অফিস|2400|13|
Netrokona|Netrokona Sadar|বৌখরহাটি এস, ও|2401|13|postal group as printed (Netrokona head office); reading of the name uncertain (faded print)
Netrokona|Purbadhala|পূর্বধলা ইউ, পি, ও|2410|13|
Netrokona|Purbadhala|শ্যামগঞ্জ এস, ও|2411|13|reading of the name uncertain (faded print)
Netrokona|Purbadhala|জারিয়া ঝানঝাইল এস, ও|2412|13|
Mymensingh|Dhobaura|ধোবাউরা ইউ, পি, ও|2416|13|printed under "নেত্রকোনা জেলা ২৪০০-২৪৯৯"; Dhobaura upazila is in Mymensingh District; spelt "ধোবাউরা" in the booklet
Mymensingh|Dhobaura|সাকুয়াই ই, ডি, এস, ও|2417|13|postal group as printed (Dhobaura), printed under "নেত্রকোনা জেলা ২৪০০-২৪৯৯"; reading of the name uncertain (faded print)
Netrokona|Durgapur|সুসং ইউ, পি, ও|2420|13|[inferred] postal group সুসং (Susang Durgapur, the Durgapur upazila seat; thana not printed)
Netrokona|Kalmakanda|কলমাকান্দা ইউ, পি, ও|2430|13|code faint in the scan; read as 2430 (uncertain)
Netrokona|Barhatta|বারহাট্টা ইউ, পি, ও|2440|13|code faint in the scan; read as 2440 (uncertain)
Netrokona|Mohongonj|মোহনগঞ্জ ইউ, পি, ও|2446|13|code faint in the scan; read as 2446 (uncertain)
Netrokona|Khaliajuri|খালিয়াজুরী ইউ, পি, ও|2460|13|code faint in the scan; read as 2460 (uncertain)
Netrokona|Khaliajuri|শালদিঘা ই ডি. এস, ও|2462|13|code faint in the scan; read as 2462 (uncertain)
Netrokona|Atpara|আটপাড়া ইউ, পি, ও|2470|13|
Netrokona|Kendua|কেন্দুয়া ইউ, পি, ও|2480|13|
Netrokona|Madan|মদন ইউ, পি, ও|2490|13|
"""
DIVISION, HEAD = "rajshahi", "Rajshahi"
BY_DIV = {"rajshahi": dict(T=None, raw=["raw/postcode_booklet_pp21.png", "raw/postcode_booklet_pp22-23.png"]),
          "rangpur": dict(T=T_RANGPUR, raw=["raw/postcode_booklet_pp18-19.png", "raw/postcode_booklet_pp20-21.png"]),
          "dhaka": dict(T=T_DHAKA, raw=["raw/postcode_booklet_pp08-09.png", "raw/postcode_booklet_pp10-11.png",
                                        "raw/postcode_booklet_pp12-13.png", "raw/postcode_booklet_pp24-25.png"]),
          "chattogram": dict(T=T_CHATTOGRAM, raw=["raw/postcode_booklet_pp14-15.png", "raw/postcode_booklet_pp16-17.png",
                                                  "raw/postcode_booklet_pp18-19.png"]),
          "khulna": dict(T=T_KHULNA, raw=["raw/postcode_booklet_pp22-23.png", "raw/postcode_booklet_pp24-25.png",
                                          "raw/postcode_booklet_pp26-27.png"]),
          "barishal": dict(T=T_BARISHAL, raw=["raw/postcode_booklet_pp24-25.png", "raw/postcode_booklet_pp26-27.png"]),
          "sylhet": dict(T=T_SYLHET, raw=["raw/postcode_booklet_pp12-13.png", "raw/postcode_booklet_pp14-15.png"]),
          "mymensingh": dict(T=T_MYMENSINGH, raw=["raw/postcode_booklet_pp12-13.png"])}


def otype(name):
    if DIVISION != "rajshahi":  # other divisions: ignore the booklet's irregular commas/dots/spaces ("ই, ডি এস ও", "এস,ও")
        canon = lambda s: re.sub(r"[\s,.]+", ", ", s.strip(" ,."))
        n = ", " + canon(name)
        for k in sorted(TYPES, key=lambda k: len(canon(k)), reverse=True):
            if n.endswith(", " + canon(k)) or (canon(k) in n and k in ("হেড অফিস", "জিপিও")):
                return TYPES[k]
        return ("", "")
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
        TYPES.setdefault("প্রধান ডাকঘর", ("HO", "Head Post Office"))   # "ঢাকা সদর প্রধান ডাকঘর"
        TYPES.setdefault("জি, পি, ও", ("GPO", "General Post Office"))  # "ঢাকা জি, পি, ও"
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
        if not up and "postal group" not in note:
            notes.append("inside %s city; upazila/thana not given" % HEAD)
        if DIVISION != "rajshahi" and "[inferred]" in note:
            notes[-1] = note.replace("[inferred] ", "upazila inferred: ")
        sid = "postcode:%s" % code if code else "office:%s:%s" % (dist.lower(), re.sub(r"[\s,.]+", "-", nfc(name)).strip("-"))
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
