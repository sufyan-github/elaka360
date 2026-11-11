#!/usr/bin/env python3
"""Tourist spots ('দর্শনীয় স্থান') listed on the national-portal district and upazila sites of Rajshahi Division.

Re-runnable: python3 fetch.py  (stdlib + requests). Optional: ELAKA_CACHE=<dir> caches pages."""
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
    txt = strip_tags(t)
    lines = [nfc(x) for x in txt.split("\n")]
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


# --- PORTAL_TOURIST_SPOTS_RAJ_2026 --------------------------------------------------------------------------
# "দর্শনীয় স্থান" (/pages/tourist-spot) lists of the 8 district portals and all upazila portals of Rajshahi Division.
SOURCE_KEY = "PORTAL_TOURIST_SPOTS_RAJ_2026"
OUT = os.path.dirname(os.path.abspath(__file__))

JUNK = re.compile(r"(জেলার দর্শনীয়|জেলার ইতিহাস|দর্শনীয় স্থান(সমূহ)?$|^দর্শনীয়|^পর্যটন স্পট$|^test)", re.I)


def category(name):
    n = name
    if re.search(r"বিশ্ববিদ্যালয়", n):
        return "education.university"
    if re.search(r"মেডিকেল কলেজ", n):
        return "education.medical_college"
    if re.search(r"কলেজ", n) and not re.search(r"কলেজিয়েট", n):
        return "education.college"
    if re.search(r"জাদুঘর|যাদুঘর|মিউজিয়াম|সংগ্রহশালা|জাদুঘর", n):
        return "tourism.museum"
    if re.search(r"মাজার|দরগা|দরগাহ|সমাধি", n):
        return "religious.mazar"
    if re.search(r"ঢিবি|ধাপ|প্রত্ন|ধ্বংসাবশেষ|মহাবিহার|বৌদ্ধ বিহার|জয় ?স্তম্ভ|পিলার|গড়$|দুর্গ|মাউন্ড|পান্টি", n):
        return "tourism.archaeological"
    if re.search(r"রাজবাড়ী|রাজবাড়ি|জমিদার|প্রাসাদ|কুঠি|কাচারী|কাচারি|ভবন|মহল|হাওয়াখানা|হাওয়া খানা|শহীদ মিনার|স্মৃতি|বধ্যভূমি|বাংলো|ঐতিহাসিক|প্রাচীন|গ্রন্থাগার|লাইব্রেরি|রেলওয়ে|ব্রিজ|সেতু|তোরণ", n):
        return "tourism.historical"
    if re.search(r"মসজিদ|মন্দির|মঠ|গির্জা|চার্চ|আশ্রম|আখড়া|বিহার|ঈদগাহ|তীর্থ", n):
        return "tourism.religious_site"
    if re.search(r"পার্ক|উদ্যান|চিড়িয়াখানা|ইকো|রিসোর্ট|বিনোদন|শিশু|গার্ডেন|বাগান|লেক", n):
        return "tourism.park"
    if re.search(r"বিমানবন্দর|একাডেমি|একাডেমী|স্টেডিয়াম", n):
        return "tourism"
    if re.search(r"নদী|পদ্মা|যমুনা|করতোয়া|আত্রাই নদ|বিল|হাওর|চর|ঘাট|বাঁধ|পাড়|তীর|নদীবন্দর|স্লুইস", n):
        return "tourism.river_haor"
    if re.search(r"দিঘী|দিঘি|দীঘি|দীঘী|পুকুর|সাগর|জলাশয়|বন$|বনভূমি|পাখি|অভয়ারণ্য|বরেন্দ্র", n):
        return "tourism.natural"
    return "tourism"


def clean_name(title, district):
    """Drop a trailing ', <upazila/district>' qualifier that some portals append to titles."""
    t = nfc(title)
    t = re.sub(r"^\s*[০-৯0-9]{1,2}\s*[.।)]\s*", "", t).rstrip(" :ঃ,.।-")
    parts = [p.strip(" :ঃ") for p in re.split(r"\s*,\s*", t)]
    if len(parts) > 1:
        tail = parts[-1]
        names = [bn for ups in UPAZILAS.values() for _, bns, _ in ups for bn in bns] + list(DISTRICTS)
        if any(tail.startswith(n) or n.startswith(tail) and len(tail) > 2 for n in names) or re.search(r"(সদর|উপজেলা|জেলা)$", tail):
            return ", ".join(parts[:-1]), tail
    return t, None


def scrape_list(base):
    rows, page, total = [], 1, None
    while True:
        url = base + "/pages/tourist-spot" + ("" if page == 1 else "?page=%d" % page)
        t = fetch_text(url)
        if not t:
            break
        got = [r for r in list_table(t) if r.get("title")]
        for r in got:
            r["_list_url"] = url
        rows += got
        m = re.search(r'pagination-counts">[^<]*?মোট\s*([০-৯0-9]+)', t)
        total = int(ascii_digits(m.group(1))) if m else len(rows)
        if not got or len(rows) >= total or page > 20:
            break
        page += 1
    return rows, total


def main():
    places, facts, seen = [], [], {}
    portals = []
    for dist, host in DISTRICT_HOSTS.items():
        portals.append((dist, None, "https://" + host))
        for en, _, sub in UPAZILAS[dist]:
            portals.append((dist, en, "https://%s.%s" % (sub, host)))
    for dist, upz, base in portals:
        rows, total = scrape_list(base)
        level = "district" if upz is None else "upazila"
        print(base, len(rows), "rows", file=sys.stderr)
        facts.append({"entity_level": level, "entity_name_en": upz or dist, "district_en": dist, "upazila_en": upz or "",
                      "fact": "portal_tourist_spot_entries", "value": total if rows else 0, "unit": "entries",
                      "basis": "listed on portal (count shown by the portal list, incl. non-place entries)",
                      "year": 2026, "source_key": SOURCE_KEY, "source_url": base + "/pages/tourist-spot",
                      "notes": "" if rows else "list empty or page unavailable at access time"})
        for r in rows:
            title = r.get("title", "")
            if JUNK.search(title):
                continue
            name, tail = clean_name(title, dist)
            loc = r.get("location", "")
            loc = "" if loc.strip() in ("0", "-", "") else loc
            if len(loc) > 120:
                loc_note = "location text omitted (long directions)"
                loc = ""
            else:
                loc_note = ""
            maps = [h for h in r.get("_hrefs", []) if re.search(r"google\.[a-z.]+/maps|maps\.app\.goo\.gl|goo\.gl/maps", h)]
            d2, u2 = find_upazila(" ".join([title, loc]), dist)
            up = upz or u2
            if dist == "Rajshahi" and not up:
                for bn, th in CITY_THANAS.items():
                    if bn in title + " " + loc:
                        up = None
                        break
            link = r.get("link", "")
            detail = (base + link) if link.startswith("/") else link
            sid = re.search(r"([0-9a-f]{24})$", link)
            notes = [loc_note] if loc_note else []
            if upz is None and up:
                notes.append("upazila inferred from the title/location text")
            if maps:
                notes.append("portal row links a Google Maps page (kept in extra_json, coordinates not taken)")
            rec = {"source_key": SOURCE_KEY, "source_id": "%s:%s" % (urllib.parse.urlsplit(base).netloc, sid.group(1) if sid else nfc(title)),
                   "name_bn": name, "category_key": category(name), "address": loc, "district_en": dist,
                   "upazila_en": up or "",
                   "extra_json": jdump({"title_as_published": title if title != name else None,
                                        "portal": urllib.parse.urlsplit(base).netloc, "portal_level": level,
                                        "map_links_as_published": maps or None}),
                   "source_url": detail or (base + "/pages/tourist-spot"), "notes": "; ".join(notes)}
            places.append(rec)
    # flag same place listed on both the district and an upazila portal (kept: each row is one portal's listing)
    key = lambda r: (r["district_en"], re.sub(r"[\s,।ঃ:()\-]", "", r["name_bn"]))
    groups = {}
    for r in places:
        groups.setdefault(key(r), []).append(r)
    for g in groups.values():
        if len(g) > 1:
            for r in g:
                others = [o["source_id"].split(":")[0] for o in g if o is not r]
                r["notes"] = "; ".join(x for x in [r["notes"], "also listed on " + ", ".join(sorted(set(others)))] if x)
    write_csv(os.path.join(OUT, "places.csv"), PLACE_COLS, places)
    write_csv(os.path.join(OUT, "facts.csv"), FACT_COLS, facts)
    print(len(places), "places", file=sys.stderr)


if __name__ == "__main__":
    main()
