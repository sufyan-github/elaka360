#!/usr/bin/env python3
"""Haat-bazaar (market) lists on the national-portal DC and upazila sites of a division (default Rajshahi).

Re-runnable: python3 fetch.py [--division rajshahi|rangpur|dhaka|chattogram|khulna|barishal|sylhet|mymensingh|all] [--out DIR]
[--workers N]  (stdlib + requests). Optional: ELAKA_CACHE=<dir> caches pages. Lease values and lessees are never stored."""
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


# --- shared by the haat-bazaar / shelter / fuel-station collectors -------------------------------------------
import datetime, shutil, subprocess
from concurrent.futures import ThreadPoolExecutor

DIV_CODES = {"rajshahi": "raj", "rangpur": "rang", "dhaka": "dhk", "chattogram": "ctg", "khulna": "khl", "barishal": "bar",
             "sylhet": "syl", "mymensingh": "mym"}
DIV_TABLES = {  # division -> (DISTRICTS bn->en, DISTRICT_HOSTS, UPAZILAS, extra TLS intermediates)
    "rajshahi": (DISTRICTS, DISTRICT_HOSTS, UPAZILAS, []),
    "rangpur": (RANGPUR_DISTRICTS, RANGPUR_DISTRICT_HOSTS, RANGPUR_UPAZILAS, []),
    "dhaka": (DHAKA_DISTRICTS, DHAKA_DISTRICT_HOSTS, DHAKA_UPAZILAS, []),
    "chattogram": (CHATTOGRAM_DISTRICTS, CHATTOGRAM_DISTRICT_HOSTS, CHATTOGRAM_UPAZILAS, []),
    "khulna": (KHULNA_DISTRICTS, KHULNA_DISTRICT_HOSTS, KHULNA_UPAZILAS, []),
    "barishal": (BARISHAL_DISTRICTS, BARISHAL_DISTRICT_HOSTS, BARISHAL_UPAZILAS, []),
    "sylhet": (SYLHET_DISTRICTS, SYLHET_DISTRICT_HOSTS, SYLHET_UPAZILAS, SYLHET_INTERMEDIATES),
    "mymensingh": (MYMENSINGH_DISTRICTS, MYMENSINGH_DISTRICT_HOSTS, MYMENSINGH_UPAZILAS, []),
}
HERE = os.path.dirname(os.path.abspath(__file__))
TODAY = datetime.date.today().isoformat()


def parse_args(extra=None):
    """--division <name>|all (default rajshahi), --out DIR (single division only), --workers N."""
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().split("\n")[0])
    ap.add_argument("--division", default="rajshahi", choices=DIVISION_CHOICES + ("all",))
    ap.add_argument("--out", help="output folder (single division; default: this folder for rajshahi, ../<folder> otherwise)")
    ap.add_argument("--workers", type=int, default=4, help="portals fetched in parallel (each portal is its own host)")
    for a in (extra or []):
        ap.add_argument(*a[0], **a[1])
    a = ap.parse_args()
    if a.division == "all" and a.out:
        raise SystemExit("--out works with a single --division only")
    return a


def out_dir(division, folder_raj, override=None):
    """Rajshahi -> this folder; others -> sibling folder with '_raj_' replaced by '_<code>_'. Never another division into here."""
    folder = folder_raj.replace("_raj_", "_%s_" % DIV_CODES[division])
    out = os.path.abspath(override or os.path.join(HERE, "..", folder))
    if division != "rajshahi" and os.path.realpath(out) == os.path.realpath(HERE):
        raise SystemExit("refusing to write %s output into the Rajshahi folder %s" % (division, HERE))
    os.makedirs(out, exist_ok=True)
    return out


def source_key(prefix, division):
    return "%s_%s_2026" % (prefix, DIV_CODES[division].upper())


# --- seed names: district / upazila English names as data/seed/geo/admin_areas.csv spells them ----------------
_SEED = None
SEED_ALIASES = {("Kurigram", "রাজিবপুর"): "চর রাজিবপুর"}  # the seed's Bangla name of Rajibpur upazila


def _bkey(s):
    s = unicodedata.normalize("NFC", s or "")
    s = re.sub(r"[\s‌‍\-]", "", s)
    for a, b in (("ী", "ি"), ("ূ", "ু"), ("ঁ", ""), ("ড়", "র"), ("ঢ়", "র"), ("য়", "য"), ("ণ", "ন")):
        s = s.replace(a, b)
    return s


def _ekey(s):
    return re.sub(r"[^a-z]", "", (s or "").lower()).replace("h", "").replace("o", "u").replace("aa", "a")


def seed():
    """{district_en: [(upazila name_en, name_bn)]} from the seed (read-only)."""
    global _SEED
    if _SEED is None:
        _SEED = {}
        fn = os.path.join(HERE, "..", "..", "seed", "geo", "admin_areas.csv")
        rows = list(csv.DictReader(open(fn, encoding="utf-8-sig"))) if os.path.exists(fn) else []
        byid = {r["id"]: r for r in rows}
        for r in rows:
            if r["level"] == "district":
                _SEED.setdefault(r["name_en"], [])
        for r in rows:
            if r["level"] == "upazila" and r["parent_id"] in byid:
                _SEED.setdefault(byid[r["parent_id"]]["name_en"], []).append((r["name_en"], r["name_bn"]))
    return _SEED


def seed_upazila(district, table_en, bns=()):
    """Seed English name of an upazila given the portal-table name and its Bangla aliases (table name if no match)."""
    ups = seed().get(district, [])
    keys = {_bkey(SEED_ALIASES.get((district, b), b)) for b in bns}
    c = [en for en, bn in ups if _bkey(bn) in keys]
    if len(c) != 1:
        c = [en for en, bn in ups if _ekey(en) == _ekey(table_en)]
    return c[0] if len(c) == 1 else table_en


def portals(division):
    """[(district_en, upazila_en(seed) or None, base_url, upazila bangla names)] for the DC portals and their upazila portals."""
    dists, hosts, ups, _ = DIV_TABLES[division]
    out = []
    for dist, host in hosts.items():
        out.append((dist, None, "https://" + host, []))
        for en, bns, sub in ups[dist]:
            out.append((dist, seed_upazila(dist, en, bns), "https://%s.%s" % (sub, host), bns))
    return out


def find_upazila_div(text, division, district=None):
    """(district_en, seed upazila_en) of the first upazila whose Bangla name occurs in text (within district if given)."""
    t = nfc(text)
    best = None
    for dist, ups in DIV_TABLES[division][2].items():
        if district and dist != district:
            continue
        for en, bns, _ in ups:
            for bn in bns:
                for m in re.finditer(re.escape(bn), t):
                    i = m.start()
                    # whole word: not preceded/followed by another Bangla letter
                    if (i > 0 and re.match(r"[ঀ-৿]", t[i - 1])) or \
                            (m.end() < len(t) and re.match(r"[ঀ-৿]", t[m.end()]) and not t[m.end():].startswith(("উপজেলা", "সদর"))):
                        continue
                    if best is None or i < best[0]:
                        best = (i, dist, seed_upazila(dist, en, bns))
                    break
    return (best[1], best[2]) if best else (None, None)


def district_by_bn(text, division):
    t = nfc(text)
    for bn, en in DIV_TABLES[division][0].items():
        if bn in t:
            return en
    return None


# --- tables with rowspan/colspan expanded -------------------------------------------------------------------
def grid_tables(t):
    """Every <table> in t -> list of rows (list of cell texts), rowspan/colspan expanded (spanned cells repeated)."""
    out = []
    for tb in re.findall(r"<table.*?</table>", t, re.S | re.I):
        rows, carry = [], {}  # carry: col -> [remaining rows, text]
        for tr in re.findall(r"<tr.*?</tr>", tb, re.S | re.I):
            cells = re.findall(r"<t([hd])([^>]*)>(.*?)</t[hd]>", tr, re.S | re.I)
            row, col = [], 0
            queue = list(cells)
            while queue or any(c >= col for c in carry):
                if not queue and col not in carry:
                    row.append("")
                    col += 1
                    continue
                if col in carry:
                    n, txt = carry[col]
                    row.append(txt)
                    carry[col][0] -= 1
                    if carry[col][0] <= 0:
                        del carry[col]
                    col += 1
                    continue
                _, attrs, inner = queue.pop(0)
                txt = nfc(strip_tags(inner))
                rs = re.search(r'rowspan\s*=\s*"?(\d+)', attrs, re.I)
                cs = re.search(r'colspan\s*=\s*"?(\d+)', attrs, re.I)
                rs = min(int(rs.group(1)), 200) if rs else 1
                cs = min(int(cs.group(1)), 30) if cs else 1
                for _ in range(cs):
                    if rs > 1:
                        carry[col] = [rs - 1, txt]
                    row.append(txt)
                    col += 1
            if any(x for x in row):
                rows.append(row)
        if rows:
            out.append(rows)
    return out


MOBILE_RE = re.compile(r"(?:\+?৮৮০|\+?880)?[০0][১1][৩-৯3-9][০-৯0-9]{2}[-\s]?[০-৯0-9]{3}[-\s]?[০-৯0-9]{3}")
PERSON_RE = re.compile(r"পিতা|পিং[-:ঃ ]|স্বামী[-:ঃ ]|সাং[-:ঃ .]|গ্রাম[-:ঃ].*ডাক|মোঃ|মো:|মোছাঃ|মোসাঃ|জনাব|মরহুম|মৃত[-ঃ ]|"
                       r"\bMr\.|\bMd\.|PROP", re.I)


def clean_cell(s):
    s = nfc(s).strip(" ,;:।ঃ-–")
    return "" if re.fullmatch(r"[-–—_.\s০0/]*", s) else s


def strip_serial(s):
    return re.sub(r"^\s*[০-৯0-9]{1,3}\s*[.।)\]:ঃ-]\s*", "", s).strip()


def internal_href(base, href):
    """Absolute URL of a menu link on this portal (relative or same host), else None."""
    href = (href or "").strip()
    if not href or href.startswith("#") or href.startswith("javascript"):
        return None
    if href.startswith("/"):
        return base + href
    p = urllib.parse.urlsplit(href)
    h = p.netloc.lower().replace("www.", "", 1)
    if h == urllib.parse.urlsplit(base).netloc:
        return base + (p.path or "/") + ("?" + p.query if p.query else "")
    return None


def list_pages(url, max_pages=40):
    """Server-rendered framework list (rows of list_table), following ?page=N up to the stated total."""
    rows, page, total = [], 1, None
    while True:
        u = url + ("" if page == 1 else ("&" if "?" in url else "?") + "page=%d" % page)
        t = fetch_text(u)
        if not t:
            break
        got = [r for r in list_table(t) if r.get("title")]
        for r in got:
            r["_list_url"] = u
        rows += got
        m = re.search(r'pagination-counts">[^<]*?মোট\s*([০-৯0-9]+)', t)
        total = int(ascii_digits(m.group(1))) if m else len(rows)
        if not got or len(rows) >= total or page >= max_pages:
            break
        page += 1
    return rows, (total or 0)


def file_links(t):
    w = widget(t) or ""
    return list(dict.fromkeys(html.unescape(h) for h in re.findall(r'href="([^"]+\.(?:pdf|docx?|xlsx?|jpe?g|png))"', w, re.I)))


def pdftotext(path):
    """Text (layout mode) via poppler's pdftotext if installed (optional dependency); None otherwise."""
    exe = shutil.which("pdftotext")
    if not exe:
        return None
    return subprocess.run([exe, "-layout", path, "-"], capture_output=True, check=True).stdout.decode("utf-8", "replace")


def use_intermediates(division):
    """Add the division's extra CA intermediates (e.g. Sylhet) and rebuild the bundle if anything was added."""
    global _bundle
    new = [u for u in DIV_TABLES[division][3] if u not in INTERMEDIATES]
    if new:
        INTERMEDIATES.extend(new)
        _bundle = None
    ca_bundle()


def write_manifest(out, meta):
    write_division_manifest(out, meta)
# --- end shared --------------------------------------------------------------------------------------------


# --- HAAT_BAZAAR_<CODE>_2026 ----------------------------------------------------------------------------------
# Haat-bazaar (market) lists of the DC and UNO portals: the framework's structured list (/pages/hatbazar, paginated) and
# static pages linked from menu items such as 'হাটবাজার' / 'হাট-বাজার' / 'হাট বাজারের তালিকা'. Kept: market name, upazila /
# union / address and market days (হাটবার) as published; area, chandina-bhiti count and managing authority in extra_json.
# Never kept: lease (ইজারা) values, lessees' (ইজারাদার) names/addresses, informants, mobile numbers — those columns are
# dropped before anything is stored, and no page is saved to raw/ (the pages list lessees).
FOLDER = "haat_bazaar_raj_2026"
KEY_PREFIX = "HAAT_BAZAAR"
HAAT_MENU = re.compile(r"হাট\s*[-–]?\s*(ও\s*)?বাজার|হাটবাজার|হাট-বাজার|বাজারের তালিকা|^\W*বাজার\W*$")
HAAT_MENU_NOT = re.compile(r"মূল্য|মুল্য|পর্যবেক্ষ|মনিটর|কমিটি|উন্নয়ন|মিনা|পশু|অনলাইন|এক নজরে|মানচিত্র|ঐতিহ্য|পটভূমি|দুর্যোগ|ইনোভেশন")

# column roles (header text -> role); checked in this order, first match wins
DROP_COL = re.compile(r"ইজারা|ইজারাদার|মূল্য|মুল্য|টাকা|রাজস্ব|আদায়|মোবাইল|ফোন|মন্তব্য|তথ্য প্রদান|কর্মকর্তা|সভাপতি|"
                      r"স্বাক্ষর|গ্রহীতা|মালিক|দাগ নং|খতিয়ান|খাস|বকেয়া|সরকারি মূল্য|[০-৯0-9]{4}\s*(বাংলা\s*)?সন|সনের")
ROLES = [
    ("days", re.compile(r"হাটবার|হাটের\s*(বার|দিন)|বসার\s*(বার|দিন)|^বার$|^হাটের বার|সাপ্তাহিক|দিন\s*$|^বার\s|হাট বসে")),
    ("union", re.compile(r"ইউনিয়ন|ইউপি|পৌরসভা/ইউনিয়ন")),
    ("upazila", re.compile(r"উপজেলা|প্রশাসনিক এলাকা|থানা")),
    ("area", re.compile(r"আয়তন|জমির পরিমাণ|জমির পরিমান|পরিমাণ|একর")),
    ("chandina", re.compile(r"চান্দিনা")),
    ("authority", re.compile(r"পরিচালনা|কর্তৃপক্ষ|কর্তিপক্ষ")),
    ("type", re.compile(r"ধরন|ধরণ|শ্রেণী|শ্রেণি|প্রকার")),
    ("address", re.compile(r"ঠিকানা|অবস্থান|মৌজা|গ্রাম|স্থান")),
    ("list", re.compile(r"তালিকা|হাট ও বাজার|হাট-বাজারসমূহ|বাজারসমূহ|হাটসমূহ")),
    ("name", re.compile(r"নাম|হাট|বাজার")),
]
SERIAL_COL = re.compile(r"^(ক্র|ক্রম|ক্রঃ|ক্র:|নং|সংখ্যা|সিরিয়াল|ক্রমিক)")


def col_roles(header):
    roles = []
    for h in header:
        h0 = nfc(h)
        if not h0:
            roles.append(None)
        elif SERIAL_COL.search(h0) and not re.search(r"নাম", h0):
            roles.append("serial")
        elif DROP_COL.search(h0) and not re.search(r"হাট[\s-]*বাজারের নাম|হাটের নাম|বাজারের নাম", h0):
            roles.append("drop")
        else:
            roles.append(next((r for r, rx in ROLES if rx.search(h0)), None))
    # one name column only: the first 'name'; a 'list' column counts as names too
    seen = False
    for i, r in enumerate(roles):
        if r in ("name", "list"):
            if seen:
                roles[i] = "address" if r == "name" and re.search(r"ঠিকানা", header[i]) else None
            seen = True
    return roles


def find_header(rows):
    for i, r in enumerate(rows[:6]):
        roles = col_roles(r)
        if any(x in ("name", "list") for x in roles) and sum(1 for x in roles if x) >= 2 and \
                not any(len(c) > 60 for c, x in zip(r, roles) if x in ("name", "list")):
            return i, roles
    return None, None


def split_list(cell):
    parts = [strip_serial(clean_cell(p)) for p in re.split(r"\s*[,،;।]\s*|\s+ও\s+(?=\S+\s*(?:হাট|বাজার))", cell)]
    return [p for p in parts if p and len(p) <= 60]


def table_records(rows, ctx):
    """Market records from one table (list of rows of cell texts)."""
    hi, roles = find_header(rows)
    if hi is None:
        return []
    out = []
    # skip sub-header / column-number rows
    body = [r for r in rows[hi + 1:] if not all(re.fullmatch(r"[\s০-৯0-9()]*", c or "") for c in r)
            and not (r and r == rows[hi])]
    last = {}
    for r in body:
        cells = r + [""] * (len(roles) - len(r))
        d = {}
        for role, c in zip(roles, cells):
            c = clean_cell(c)
            if role in (None, "serial", "drop") or not c:
                continue
            if DITTO.fullmatch(c):  # 'ঐ' = same as the row above
                if role in last:
                    d[role] = last[role]
                continue
            last[role] = c
            if role != "name" and role != "list" and (MOBILE_RE.search(c) or PERSON_RE.search(c) or "ইজারা" in c):
                d.setdefault("_dropped", []).append(role)
                continue
            d[role] = c
        if re.search(r"^মোট|সর্বমোট|^সর্ব মোট", d.get("name", "") + d.get("list", "")):
            continue
        names, flags, uhint = [], [], None
        if d.get("list"):
            names = split_list(d["list"])
            flags = ["name split from a comma-separated list cell"] if len(names) > 1 else []
        elif d.get("name"):
            names, flags, uhint = expand_names(d["name"])
        for n in names:
            if not n or len(n) > 80 or re.fullmatch(r"[\s০-৯0-9.,/-]*", n) or PERSON_RE.search(n) or MOBILE_RE.search(n) \
                    or re.search(r"(নাম|তালিকা|সমূহ)$", n) or NOT_A_MARKET.search(n):
                continue
            rec = dict(d)
            rec["name"] = n
            rec["_flags"] = flags
            if uhint and not rec.get("union"):
                rec["union"] = uhint
            out.append(rec)
    return out


DITTO = re.compile(r"[\"'“”‘’〃]+|-?\s*ঐ\s*-?|ঐ\s*ঐ")


def clean_name(n, division):
    """Drop trailing ', <upazila>, <district>' qualifiers; returns (name, title as published or None)."""
    parts = [p.strip() for p in re.split(r"\s*,\s*", n) if p.strip()]
    if len(parts) < 2:
        return n, None
    names = [b for ups in DIV_TABLES[division][2].values() for _, bns, _ in ups for b in bns] + list(DIV_TABLES[division][0])
    while len(parts) > 1 and (any(parts[-1] == b or parts[-1].startswith(b + " ") for b in names) or
                              re.search(r"(সদর|উপজেলা|জেলা|মহানগর)$", parts[-1])):
        parts.pop()
    out = ", ".join(parts)
    return (out, n) if out != n else (n, None)


def numbered_list(w):
    """'১। কুতুবপুর ২। কড়িতলা …' style text lists (no table) -> names; only when >= 3 short numbered items."""
    w = re.sub(r"<[^>]*$", " ", w)  # the widget slice ends inside the next widget's opening tag
    txt = nfc(strip_tags(re.sub(r"<table.*?</table>", " ", w, flags=re.S)))
    txt = re.sub(r"^.*?কন্টেন্ট:\s*পাতা", "", txt)
    items = re.findall(r"(?:^|\s)([০-৯]{1,3})\s*[।.)]\s*([^০-৯।.()\n]{2,40}?)(?=\s+[০-৯]{1,3}\s*[।.)]|\s*$|\s*[।\n])", txt)
    nums = [int(ascii_digits(a)) for a, _ in items]
    if len(items) < 3 or nums[:3] != [1, 2, 3]:
        return []
    out = []
    for _, n in items:
        n = clean_cell(n)
        if n and not PERSON_RE.search(n) and not MOBILE_RE.search(n) and len(n.split()) <= 5:
            out.append(n)
    return out


NOT_A_MARKET = re.compile(r"উপজেলার|জেলার|উপজেলাধীন|তথ্য|বিজ্ঞপ্তি|ইজারা|ইজরা|খাস আদায়|বঙ্গাব্দ|[০-৯0-9]{4}\s*(বাংলা\s*)?সন|সনে|সনের|"
                          r"^[০-৯0-9]+\s*টি$|তালিকা|সংক্রান্ত|বন্টন|^হাট[\s-]*বাজার$|^হাটবাজার$|খেয়াঘাট")


def expand_names(n):
    """One name cell -> (names, flags): mobile numbers removed, lease remarks in brackets removed, numbered or long comma
    lists split, captions ('… উপজেলার হাট-বাজারের তথ্য') dropped. Union hint from 'অবস্থানঃ … হাটবাজারের নামঃ …'."""
    flags, union = [], None
    if MOBILE_RE.search(n):
        n = MOBILE_RE.sub(" ", n)
        flags.append("mobile number removed from the name")
    n = re.sub(r"\([^()]*(ইজারা|ইজরা|সনে|সন\b|খাস)[^()]*\)", " ", n)
    m = re.search(r"অবস্থান\s*[ঃ:]\s*(.*?)\s*হাট\s*-?বাজারের নাম\s*[ঃ:]\s*(.*)$", n)
    if m:
        union, n = nfc(m.group(1)), m.group(2)
        union = re.sub(r"^[০-৯0-9]+\s*নং\s*", "", union).replace(" পরিষদ", "").strip()
    n = nfc(re.sub(r"\s*ইত্যাদি\s*$", "", n))
    parts = [n]
    if len(re.findall(r"(?:^|\s)[০-৯0-9]{1,2}\s*[।.)]\s*\S", n)) >= 2:
        parts = [p for p in re.split(r"(?:^|\s)[০-৯0-9]{1,2}\s*[।.)]\s*", n) if p.strip()]
        flags.append("name split from a numbered list in one cell")
    elif "," in n and len(n) > 40 and len(split_list(n)) >= 3:
        parts = split_list(n)
        flags.append("name split from a comma-separated list cell")
    out = []
    for p in parts:
        p = strip_serial(clean_cell(re.sub(r"\s{2,}", " ", p)))
        if not p or len(p) > 80 or re.fullmatch(r"[\s০-৯0-9.,/()-]*", p) or PERSON_RE.search(p) or NOT_A_MARKET.search(p):
            continue
        out.append(p)
    return out, flags, union


def category(name, days):
    return "agriculture.haat" if ("হাট" in name or days) else "business.market"


def collect_portal(p, division, skey):
    dist, upz, base, bns = p
    level = "district" if upz is None else "upazila"
    host = urllib.parse.urlsplit(base).netloc
    home = fetch_text(base + "/")
    targets = []
    for top, grp, title, href in (menu_entries(home) if home else []):
        if not HAAT_MENU.search(title) or HAAT_MENU_NOT.search(title):
            continue
        if "objectstorage" in href:
            targets.append(("file", href, title))
            continue
        if re.search(r"hat_bazar|hatbazar|site/page/.*হাট", href):
            href = "/pages/hatbazar" if not re.search(r"/pages/hatbazar/[0-9a-f]{24}$", href) else urllib.parse.urlsplit(href).path
        u = internal_href(base, href)
        if u:
            targets.append(("page", u, title))
    if not any(t[1].rstrip("/").endswith("/pages/hatbazar") for t in targets):
        targets.append(("page", base + "/pages/hatbazar", "(structured list, not in menu)"))
    targets = list(dict.fromkeys(targets))
    recs, notes, files = [], [], []
    for kind, u, title in targets:
        if kind == "file":
            files.append(u)
            continue
        if u.rstrip("/").endswith("/pages/hatbazar"):
            rows, total = list_pages(u)
            for r in rows:
                link = r.get("link", "")
                sid = re.search(r"([0-9a-f]{24})$", link)
                rec = {"name": clean_cell(r.get("title", "")), "_src": u if not link else (base + link if link.startswith("/") else link),
                       "_sid": sid.group(1) if sid else None, "_list_url": r.get("_list_url")}
                for f, role in (("field_hat_address", "address"), ("field_hat_authority", "authority"),
                                ("field_hat_aioton", "area"), ("field_chandina_viti", "chandina")):
                    v = clean_cell(r.get(f, ""))
                    if v and not (MOBILE_RE.search(v) or PERSON_RE.search(v) or "ইজারা" in v):
                        rec[role] = v
                names, flags, uhint = expand_names(rec["name"])
                for i, n in enumerate(names):
                    rr = dict(rec, name=n, _menu=title, _flags=flags)
                    if uhint:
                        rr["union"] = uhint
                    if len(names) > 1 and rr.get("_sid"):
                        rr["_sid"] = "%s-%d" % (rr["_sid"], i + 1)
                    recs.append(rr)
            continue
        t = fetch_text(u)
        if not t:
            notes.append("page unavailable: " + u)
            continue
        w = widget(t)
        got = []
        for tb in grid_tables(w):
            for rec in table_records(tb, None):
                rec["_src"] = u
                rec["_menu"] = title
                got.append(rec)
        if not got and w:
            got = [dict(name=n, _src=u, _menu=title, _numbered=True) for n in numbered_list(w) if not NOT_A_MARKET.search(n)]
        if got:
            recs += got
        else:
            fl = file_links(t)
            if fl:
                files += fl
            elif w:
                notes.append("page has no parsable market table: " + u)
    return {"portal": p, "level": level, "host": host, "recs": recs, "files": list(dict.fromkeys(files)), "notes": notes}


def build_rows(res, division, skey):
    dist, upz, base, bns = res["portal"]
    host = res["host"]
    rows, seen = [], set()
    for rec in res["recs"]:
        name, as_pub = clean_name(rec["name"], division)
        notes, extra = [], {"name_as_published": as_pub}
        u_en = upz
        d_en = dist
        if upz is None:
            loc_text = " ".join(rec.get(k, "") for k in ("upazila", "union", "address")).strip() or (as_pub or "")
            d2, u2 = find_upazila_div(loc_text, division, dist)
            if not u2:
                d2, u2 = find_upazila_div(name, division, dist)
            if u2:
                u_en = u2
                notes.append("upazila from the row's upazila/address text on the DC portal")
            elif re.search(r"মহানগর|সিটি|শহর|পৌরসভা", loc_text + name):
                notes.append("city/pourashava area named on the DC portal; upazila not assigned")
        if rec.get("upazila"):
            extra["upazila_as_published"] = rec["upazila"]
        days = rec.get("days")
        key = (re.sub(r"\s", "", name), rec.get("union", ""), u_en)
        if key in seen:
            continue
        seen.add(key)
        if rec.get("_dropped"):
            notes.append("cell(s) naming a person or mobile number dropped: " + ", ".join(sorted(set(rec["_dropped"]))))
        if rec.get("_numbered"):
            notes.append("name from a numbered text list (no table)")
        notes += rec.get("_flags", [])
        extra.update({"union_bn": rec.get("union"), "haat_days": days, "area": rec.get("area"), "chandina_bhiti": rec.get("chandina"), "managing_authority": rec.get("authority"),
                      "market_type": rec.get("type"), "menu_title": rec.get("_menu"), "portal": host,
                      "portal_level": res["level"], "list_url": rec.get("_list_url")})
        sid = rec.get("_sid") or hashlib.sha1(("%s|%s|%s" % (name, rec.get("union", ""), rec.get("address", ""))).encode()).hexdigest()[:12]
        src = rec["_src"]
        if MOBILE_RE.search(urllib.parse.unquote(src)):  # some detail-page slugs carry a mobile number from the title
            src = rec.get("_list_url") or base + "/pages/hatbazar"
        rows.append({"source_key": skey, "source_id": "%s:%s" % (host, sid), "name_bn": name, "category_key": category(name, days),
                     "address": rec.get("address", ""), "district_en": d_en, "upazila_en": u_en or "",
                     "extra_json": jdump(extra), "source_url": src, "notes": "; ".join(notes)})
    return rows


def manifest(division, skey, n_portals):
    dn = division.capitalize()
    head = list(DIV_TABLES[division][1].values())[0]
    return {"key": skey, "division": division, "kind": "haat_bazaar",
            "name": "Haat-bazaar (market) lists on the national portal — %s Division DC and upazila portals" % dn,
            "organization": "District / Upazila administrations (national portal framework, a2i/Cabinet Division)",
            "source_type": "government_portal", "trust_level": 4,
            "urls": ["https://%s/pages/hatbazar" % head, "https://<upazila>.<district>.gov.bd/pages/hatbazar",
                     "https://<portal>/pages/static-pages/<id> (menu 'হাটবাজার' / 'হাট-বাজার' / 'হাট বাজার')"],
            "accessed": TODAY, "publication_date": None, "license": None, "license_url": None,
            "attribution": "District / Upazila administrations (national portal framework, a2i/Cabinet Division)",
            "notes": "%d portals read (DC + UNO). Structured lists (/pages/hatbazar, ?page=N) and static pages linked from haat-bazaar "
                     "menu items; tables parsed by header (rowspan/colspan expanded). Kept: name, union, upazila, address, haat days, "
                     "area, chandina-bhiti count, managing authority as published. Dropped before storage: lease (ইজারা) values, "
                     "lessee names/addresses, informant names, mobile numbers, remarks; no page saved to raw/. No coordinates are "
                     "published. Category: agriculture.haat when the name contains 'হাট' or market days are given, else "
                     "business.market. Licence: none stated on the source; treat as government public information, cite the source."
                     % n_portals}


def run(division, override_out, workers):
    skey = source_key(KEY_PREFIX, division)
    out = out_dir(division, FOLDER, override_out)
    use_intermediates(division)
    ps = portals(division)
    with ThreadPoolExecutor(max(1, workers)) as ex:
        results = list(ex.map(lambda p: collect_portal(p, division, skey), ps))
    places, facts = [], []
    for res in results:
        dist, upz, base, _ = res["portal"]
        rows = build_rows(res, division, skey)
        places += rows
        n_note = "; ".join(res["notes"])
        if res["files"]:
            n_note = "; ".join(x for x in [n_note, "list also/only published as file(s), not parsed: " + " ".join(res["files"][:5])] if x)
        facts.append({"entity_level": res["level"], "entity_name_en": upz or dist, "district_en": dist, "upazila_en": upz or "",
                      "fact": "portal_haat_bazaar_entries", "value": len(rows), "unit": "markets",
                      "basis": "rows kept from the portal's haat-bazaar list(s)", "year": 2026, "source_key": skey,
                      "source_url": base + "/pages/hatbazar", "notes": n_note})
    # same market on the DC portal and an upazila portal: flag both (both rows kept, each is one portal's listing)
    groups = {}
    for r in places:
        groups.setdefault((r["district_en"], r["upazila_en"], re.sub(r"[\s,।ঃ:()\-]", "", r["name_bn"])), []).append(r)
    for g in groups.values():
        hosts = sorted({x["source_id"].split(":")[0] for x in g})
        if len(hosts) > 1:
            for r in g:
                others = [h for h in hosts if h != r["source_id"].split(":")[0]]
                r["notes"] = "; ".join(x for x in [r["notes"], "also listed on " + ", ".join(others)] if x)
    write_csv(os.path.join(out, "places.csv"), PLACE_COLS, places)
    write_csv(os.path.join(out, "facts.csv"), FACT_COLS, facts)
    write_manifest(out, manifest(division, skey, len(ps)))
    print(division, len(places), "markets", file=sys.stderr)
    return places, facts


def main():
    a = parse_args()
    for d in (DIVISION_CHOICES if a.division == "all" else (a.division,)):
        run(d, a.out, a.workers)


if __name__ == "__main__":
    main()
