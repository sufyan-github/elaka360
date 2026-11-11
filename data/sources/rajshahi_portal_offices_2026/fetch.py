#!/usr/bin/env python3
"""Government offices listed on the national-portal sites (Divisional Commissioner, Rajshahi DC portal and its upazila portals; DC and UNO offices of the other Rajshahi Division districts).

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
        if os.path.exists(fn + ".fail"):
            return ""
    r = get(url, retries=1, timeout=25)
    if r is None or r.status_code != 200:
        print("  !", r.status_code if r is not None else "ERR", url, file=sys.stderr)
        if fn:
            open(fn + ".fail", "w").write(str(r.status_code if r is not None else "ERR"))
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


def host_of(u):
    return urllib.parse.urlsplit(u).netloc.lower().split(":")[0]


def norm_url(u):
    u = u.strip()
    if not re.match(r"https?://", u):
        return None
    p = urllib.parse.urlsplit(u)
    return "https://%s/" % p.netloc.lower()


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
    if not home:
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
    from concurrent.futures import ThreadPoolExecutor
    places, seen, jobs = [], set(), []

    def add(r):
        if isinstance(r, Job):
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
    add(Job("বিভাগীয় কমিশনারের কার্যালয়, রাজশাহী", div, "Rajshahi", None, "division", None, div,
                      "government.divisional_commissioner", True))
    divhome = fetch_text(div)
    for top, grp, ttl, href in menu_entries(divhome):
        if OFFICE_TOPS.search(top) and norm_url(href) and host_of(href).endswith(".gov.bd") and host_of(href) != DIV_HOST:
            add(Job(ttl, href, "Rajshahi", None, "division", grp, div))

    # 2) Rajshahi District: DC portal + its office menu + local government; 9 upazila portals + their office menus
    for dist, dhost in DISTRICT_HOSTS.items():
        dbase = "https://%s/" % dhost
        add(Job("জেলা প্রশাসকের কার্যালয়, " + [k for k, v in DISTRICTS.items() if v == dist][0], dbase, dist, None,
                          "district", None, dbase, "government.dc_office", True))
        dhome = fetch_text(dbase)
        if dist == "Rajshahi":
            for top, grp, ttl, href in menu_entries(dhome):
                if (OFFICE_TOPS.search(top) or "স্থানীয় সরকার" in top) and norm_url(href) and host_of(href) != dhost:
                    if re.search(r"\.(?:gov\.bd|portal\.gov\.bd)$", host_of(href)) or "pourashava" in host_of(href):
                        up = None
                        for en, _, sub in UPAZILAS[dist]:
                            if host_of(href).endswith(".%s.%s" % (sub, dhost)):
                                up = en
                        add(Job(ttl, href, dist, up, "district", grp, dbase))
        for en, bns, sub in UPAZILAS[dist]:
            ubase = "https://%s.%s/" % (sub, dhost)
            add(Job("উপজেলা নির্বাহী অফিসারের কার্যালয়, " + bns[0], ubase, dist, en, "upazila", None, dbase,
                              "government.uno_office", True))
            if dist != "Rajshahi":
                continue
            uhome = fetch_text(ubase)
            for top, grp, ttl, href in menu_entries(uhome):
                if (OFFICE_TOPS.search(top) or "পৌরসভা" in top) and norm_url(href) and host_of(href) != host_of(ubase):
                    h = host_of(href)
                    if h.endswith(".gov.bd") and not h.endswith("." + host_of(ubase)) and "পৌরসভা" not in top + ttl:
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

    # 3) Rajshahi District local-government lists (names only, from the DC portal static pages)
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
    for r in places:
        if r["district_en"] == "Rajshahi" and not r["upazila_en"]:
            for bn, th in CITY_THANAS.items():
                if bn in r["name_bn"] and th not in ("Paba",):
                    r["upazila_en"] = th
                    r["notes"] = "; ".join(x for x in [r.get("notes"), "upazila_en holds a Rajshahi metropolitan thana"] if x)
                    break
    write_csv(os.path.join(OUT, "places.csv"), PLACE_COLS, places)
    print(len(places), "places", file=sys.stderr)


if __name__ == "__main__":
    main()
