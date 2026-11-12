#!/usr/bin/env python3
"""Department of Archaeology (archaeology.gov.bd) gazetted protected monuments of Rajshahi Division, one PDF per district.

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

import re, unicodedata
# SutonnyMJ / Bijoy ANSI -> Unicode (best-effort; covers the glyphs used in the DoA lists)
_MULTI = [("Av", "আ")]
_MAP = {
 "A":"অ","B":"ই","C":"ঈ","D":"উ","E":"ঊ","F":"ঋ","G":"এ","H":"ঐ","I":"ও","J":"ঔ",
 "K":"ক","L":"খ","M":"গ","N":"ঘ","O":"ঙ","P":"চ","Q":"ছ","R":"জ","S":"ঝ","T":"ঞ","U":"ট","V":"ঠ",
 "W":"ড","X":"ঢ","Y":"ণ","Z":"ত","_":"থ","`":"দ","a":"ধ","b":"ন","c":"প","d":"ফ","e":"ব","f":"ভ",
 "g":"ম","h":"য","i":"র","j":"ল","k":"শ","l":"ষ","m":"স","n":"হ","o":"ড়","p":"ঢ়","q":"য়","r":"ৎ",
 "s":"ং","t":"ঃ","u":"ঁ",
 "v":"া","w":"ি","x":"ী","y":"ু","z":"ু","æ":"ু","~":"ূ","‚":"ূ","ƒ":"ূ","„":"ৃ","…":"ৃ",
 "‡":"ে","†":"ে","ˆ":"ৈ","‰":"ৈ","Š":"ৗ",
 "|":"।","&":"্","Ñ":"-","Ô":"‘","Õ":"’",
 # phala forms
 "Ö":"্র","ª":"্র","«":"্র","¨":"্য","¡":"্ব","¦":"্ব","Ÿ":"্ব","œ":"্ন","¥":"্ম",
 # half forms (combine with the following tail glyph)
 "¯":"স্","š":"ন্","›":"ন্","¤":"ম্","®":"ষ্","”":"চ্",
 "Í":"ত","’":"থ","‹":"ক","¢":"ভ","§":"ম","ú":"প","¿":"ত্র","‘":"তু","^":"ব",
 # ligatures
 "°":"ক্ক","±":"ক্ট","²":"ক্ষ্ম","³":"ক্ত","µ":"ক্র","¶":"ক্ষ","ÿ":"ক্ষ","·":"ক্স","¸":"গু","»":"গ্ধ",
 "¼":"ঙ্ক","½":"ঙ্গ","¾":"জ্জ","Á":"জ্ঞ","Â":"ঞ্চ","Ã":"ঞ্ছ","Ä":"ঞ্জ","Å":"ট্ট","Æ":"ট্ট","Ç":"ণ্ট","È":"ণ্ঠ",
 "Ð":"ণ্ড","Ë":"ত্ত","Ì":"ত্থ","Î":"ত্র","Ï":"দ্দ","×":"দ্ধ","Ø":"দ্ব","Ù":"দ্ম","Ú":"ধ্ব","Û":"ন্ড","Ü":"ন্ধ",
 "Ý":"ন্ব","Þ":"ন্ম","ß":"প্ত","à":"প্ট","á":"প্প","â":"প্ল","ã":"ব্দ","ä":"ব্জ","å":"ব্ধ","ç":"ভ্র","è":"ম্ন",
 "é":"ম্প","ê":"ম্ফ","ë":"ম্ব","ì":"ম্ভ","í":"ল্প","î":"ল্ক","ï":"শু","ð":"শ্চ","ñ":"শ্ছ","ò":"ষ্ণ","ó":"ষ্ট",
 "ô":"ষ্ঠ","÷":"ষ্ট","ø":"্ল","ù":"স্ক","û":"হু","ü":"হৃ","ý":"হ্ন","þ":"হ্ম",
 "©":"",
}
_C = "কখগঘঙচছজঝঞটঠডঢণতথদধনপফবভমযরলশষসহড়ঢ়য়ৎ"
_K = "[%s]\u09bc?" % _C
_CL = "((?:%s্)*%s(?:্[যরবনম])*)" % (_K, _K)


def bijoy2uni(s):
    """Convert word by word; words that already contain Unicode Bangla are left as they are."""
    return re.sub(r"\S+", lambda m: m.group(0) if re.search("[\u0980-\u09ff]", m.group(0)) else _conv(m.group(0)), s)


def _conv(s):
    for a, b in _MULTI:
        s = s.replace(a, b)
    out = []
    for ch in s:
        if "ঀ" <= ch <= "৿":
            out.append(ch)
        else:
            out.append(_MAP.get(ch, ch))
    u = "".join(out)
    u = unicodedata.normalize("NFD", u)  # ড় ঢ় য় are excluded from composition: work on base+nukta
    u = u.replace("্্", "্")
    u = re.sub("([িেৈ]?)" + _CL + "", "র্\\1\\2", u)  # reph goes before its cluster
    u = u.replace("", "র্")
    u = re.sub("([িেৈ])" + _CL, "\\2\\1", u)  # prefix vowel signs go after their cluster
    u = re.sub("(\u0981)([\u09be-\u09cc\u09d7])", "\\2\\1", u)  # chandrabindu after the vowel sign
    u = u.replace("ে" + "া", "ো").replace("ে" + "ৗ", "ৌ")
    return unicodedata.normalize("NFC", u)


# --- DOA_PROTECTED_MONUMENTS_RAJ_2026 -----------------------------------------------------------------------
# Department of Archaeology: "রাজশাহী বিভাগের সংরক্ষিত পুরাকীর্তি" page -> one PDF per district (gazetted protected
# monuments with GPS and gazette references). The PDFs are typed in Bijoy/SutonnyMJ (ANSI) with a few rows in
# Unicode, so the text layer is converted with bijoy2uni(). PDF text extraction uses poppler's `pdftotext -layout`
# when it is installed; otherwise the committed raw/*.txt extractions are used.
import shutil, subprocess

SOURCE_KEY = "DOA_PROTECTED_MONUMENTS_RAJ_2026"
OUT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(OUT, "raw")
LIST_URL = "https://archaeology.gov.bd/pages/static-pages/6922df29933eb65569e20433"

HDR_KEYS = {"loc": ["Ae¯’vb", "অবস্থান"], "gps": ["wRI", "জিও"], "gaz": ["cÖÁvcb", "প্রজ্ঞাপন"], "desc": ["mswÿß", "সংক্ষিপ্ত"]}
SKIP = ["director_general", "feb, Gd-4", "ভবন, এফ-৪", "AvMviMvuI"]
ENG = re.compile(r"\b(and|in|by|of|Ref|Protected|Monuments|Mounds|Bangladesh|District|Department|Archaeology|Museums|Gazette|Notification|No)\b")
TEXT_FIXES = {"হহম্নত": "হেমন্ত"}  # PDF text-layer artefacts in Unicode rows (visible text checked on the page image)


def _segs(line):
    return [(m.start(), m.group(0)) for m in re.finditer(r"\S+(?: \S+)*", line)]


def parse_layout(txt):
    cols, rows, cur = None, [], None
    for line in txt.splitlines():
        if not line.strip() or any(k in line for k in SKIP):
            continue
        if any(k in line for k in HDR_KEYS["gps"]) and any(k in line for k in HDR_KEYS["loc"]):
            c = {"name": 4}
            for k, keys in HDR_KEYS.items():
                for kk in keys:
                    i = line.find(kk)
                    if i >= 0:
                        c[k] = i
                        break
            if "gaz" in c:  # header labels are centred; description text starts ~20 columns after the gazette label
                c["desc"] = c["gaz"] + 22
            cols = c
            continue
        if cols is None or re.match(r"^\s*1\s+2\s+3", line) or re.match(r"^\s*0\s*$", line):
            continue
        m = re.match(r"^(\s*)(\d{1,3})\s*[.।]\s?", line)
        if m and len(m.group(1)) < 4:
            cur = {"sn": int(m.group(2)), "name": [], "loc": [], "gps": [], "gaz": [], "desc": []}
            rows.append(cur)
            line = " " * len(m.group(0)) + line[len(m.group(0)):]
        if cur is None:
            continue
        for pos, s in _segs(line):
            best = min((abs(pos - v), k) for k, v in cols.items())[1]
            if best == "name" and pos > cols.get("loc", 80) - 25:
                best = "loc"
            cur[best].append(s)
    return rows


def conv(segs_):
    s = " ".join(x if ENG.search(x) else bijoy2uni(x) for x in segs_)
    for a, b in TEXT_FIXES.items():
        s = s.replace(a, b)
    return nfc(s)


def dms(s):
    s = s.replace("°", " ").replace("’", "'").replace("”", '"').replace("''", '"')
    m = re.search(r"(\d{2})(?:\s|0(?=\d{2}))?\s*(\d{1,2})'\s*(\d{1,2}(?:\.\d+)?)\"?", s)
    if m:
        d, mi, se = int(m.group(1)), int(m.group(2)), float(m.group(3))
        if mi < 60 and se < 60:
            return round(d + mi / 60 + se / 3600, 6), None
        return None, "minutes/seconds out of range"
    m = re.search(r"(\d{2})(?:\s|0(?=\d{2}\.))?\s*(\d{1,2}\.\d+)\s*['\"]", s)
    if m:
        d, mi = int(m.group(1)), float(m.group(2))
        if mi < 60:
            return round(d + mi / 60, 6), "source gives degrees + decimal minutes"
        return None, "minutes out of range"
    m = re.search(r"(\d{2}\.\d{3,})", s)
    if m:
        return round(float(m.group(1)), 6), "source gives decimal degrees"
    return None, "no coordinate"


def coord_pairs(gps):
    g = ascii_digits(gps)
    pairs = re.findall(r"(.+?)(?:D\.|D:|উ\.)\s*(.+?)(?:c~\.|c~:|পূ\.)", g)
    if not pairs:
        m = re.findall(r"(.+?)c~\.\s*(.+?)c~\.", g)  # latitude mislabelled as east
        pairs = m
    return pairs


def gazette(text):
    t = ascii_digits(text)
    out = {"gazette_reference_as_published": text or None}
    m = re.search(r"(বাংলাদেশ গেজেট|গভর্নমেন্ট অব বেঙ্গলের প্রজ্ঞাপন|বেঙ্গল সরকার|কলকাতা গেজেট|কলিকাতা গেজেট|ঢাকা গেজেট|পূর্ব পাকিস্তান গেজেট|Calcutta Gazette|Dacca Gazette|East Pakistan Gazette|Bangladesh Gazette)", t)
    if m:
        out["gazette"] = m.group(1)
    months = "জানুয়ারি|জানুয়ারী|ফেব্রুয়ারি|ফেব্রুয়ারী|মার্চ|এপ্রিল|মে|জুন|জুলাই|আগষ্ট|আগস্ট|সেপ্টেম্বর|অক্টোবর|নভেম্বর|ডিসেম্বর"
    m = re.search(r"(\d{1,2})\s*(%s)\s*,?\s*(\d{4})" % months, t)
    if m:
        out["gazette_date_text"] = m.group(0)
    m = re.search(r"\(?\s*(\d+)\s*ম\s*খণ্ড,?\s*পৃষ্ঠা\s*নং\s*[-:]?\s*(\d+)\s*\)?", t)
    if m:
        out["gazette_part_page"] = "%s ম খণ্ড, পৃষ্ঠা %s" % (m.group(1), m.group(2))
    m = re.search(r"নম্বর\s*:?\s*([^\s].{0,30}?)\s+\d{1,2}\s*(?:%s)" % months, t)
    if m:
        out["notification_no_text"] = m.group(1).strip(" :")
    if "Mounds in Bangladesh" in t:
        pg = re.search(r"Page\s*-?\s*(\d+)", t)
        out["reference"] = "Protected Monuments and Mounds in Bangladesh (District-wise) 1975, Department of Archaeology and Museums" + (", p. %s" % pg.group(1) if pg else "")
    return out


DATE_RE = re.compile(r"(\d{3,4}\s*হিজরী\s*\(\s*\d{4}(?:\s*-\s*\d{2,4})?\s*খ্রি[^)]*\))|(\d{4}(?:\s*-\s*\d{2,4})?\s*(?:সালে|খ্রিষ্টাব্দে|খ্রিস্টাব্দে|খ্রিঃ|খ্রি\.))|(\d{1,2}\s*শতক|\d{1,2}\s*শতাব্দী|\S+\s*শতকে|\S+\s*শতাব্দীতে)")


def construction_date(desc):
    """Date phrase from the first description sentence that mentions construction (fact only; no prose kept)."""
    for sent in re.split(r"[।|]", ascii_digits(desc)):
        if re.search(r"নির্মাণ|নির্মিত", sent):
            m = DATE_RE.search(sent)
            if m:
                return nfc(m.group(0))
    return None


def category(name):
    if re.search(r"মাজার|দরগাহ|দরগা", name) and not re.search(r"মসজিদ", name):
        return "religious.mazar"
    if re.search(r"ঢিবি|ধাপ|মাউন্ড|ধ্বংসাবশেষ|প্রত্নস্থল|প্রত্নতাত্ত্বিক|বিহার|ভিটা|স্তুপ|স্তূপ|দুর্গ প্রাচীর|মহাস্থানগড়|পিলার|পান্টি|মেধ|কুণ্ড|নিশানঘাটি", name):
        return "tourism.archaeological"
    if re.search(r"জাদুঘর", name):
        return "tourism.museum"
    return "tourism.historical"


def pdf_text(pdf_path, txt_path):
    if shutil.which("pdftotext") and os.path.exists(pdf_path):
        subprocess.run(["pdftotext", "-layout", pdf_path, txt_path], check=False)
    return open(txt_path, encoding="utf-8").read() if os.path.exists(txt_path) else ""


def main():
    os.makedirs(RAW, exist_ok=True)
    t = fetch_text(LIST_URL)
    w = widget(t)
    entries = []
    for cells, hrefs in (html_tables(w)[0] if html_tables(w) else []):
        pdfs = [h for h in hrefs if h.lower().endswith(".pdf")]
        if len(cells) >= 4 and cells[1] in DISTRICTS and pdfs:
            entries.append({"district_bn": cells[1], "district": DISTRICTS[cells[1]],
                            "count": int(re.sub(r"\D", "", ascii_digits(cells[2])) or 0),
                            "published": ascii_digits(cells[3]), "pdf": pdfs[0]})
    if not entries:  # page unavailable: fall back to the PDFs already in raw/
        print("list page unavailable; using raw/", file=sys.stderr)
        for fn in sorted(os.listdir(RAW)):
            if fn.endswith(".txt"):
                d = fn[len("doa_"):-4].capitalize()
                entries.append({"district": d, "district_bn": "", "count": None, "published": "", "pdf": ""})
    places, facts = [], []
    allcoords = {}
    for e in entries:
        d = e["district"]
        base = os.path.join(RAW, "doa_%s" % d.lower())
        if e["pdf"]:
            r = get(e["pdf"], timeout=120)
            if r is not None and r.status_code == 200 and r.content[:4] == b"%PDF":
                open(base + ".pdf", "wb").write(r.content)
        txt = pdf_text(base + ".pdf", base + ".txt")
        rows = parse_layout(txt)
        facts.append({"entity_level": "district", "entity_name_en": d, "district_en": d, "fact": "protected_monuments_gazetted",
                      "value": e["count"], "unit": "monuments", "basis": "count stated on the DoA Rajshahi Division page",
                      "year": (e["published"][-4:] if e["published"] else ""), "source_key": SOURCE_KEY, "source_url": LIST_URL,
                      "notes": "list published %s; %d rows parsed from the PDF" % (e["published"], len(rows))})
        for r in rows:
            name = re.sub(r"\s+(ম|-)$", "", conv(r["name"])).strip()
            loc = conv(r["loc"])
            gps = " ".join(r["gps"]).strip()
            gz = gazette(conv(r["gaz"]))
            gz["construction_date_as_stated"] = construction_date(conv(r["desc"]))
            pairs = coord_pairs(gps)
            subs = [s.strip(" ;,") for s in re.split(r"\(?[কখগঘঙচছজঝঞটত]\)\s*", name)]
            parent, subs = subs[0], [s for s in subs[1:] if s]
            items = [(name, pairs[0] if pairs else None, None)]
            if subs and len(subs) == len(pairs):
                parent = re.sub(r"\(একক পুরাকীর্তি.*?\)", "", parent).strip(" :ঃ")
                items = [("%s — %s" % (parent, s), p, s) for s, p in zip(subs, pairs)]
            locs = [x for x in dict.fromkeys(loc.split(" ")) if x]
            up_d, up = find_upazila(loc, d)
            thana = None
            if not up and d == "Rajshahi":
                for bn, en in CITY_THANAS.items():
                    if bn in loc:
                        up = thana = en
                        break
            for i, (nm, pair, sub) in enumerate(items):
                notes = []
                lat = lon = None
                if pair:
                    lat, n1 = dms(pair[0])
                    lon, n2 = dms(pair[1])
                    for n in (n1, n2):
                        if n and n not in notes:
                            notes.append(n)
                    if lat is not None and not (23.7 < lat < 25.5):
                        notes.append("latitude %s outside Rajshahi Division — not used" % lat); lat = None
                    if lon is not None and not (87.9 < lon < 90.0):
                        notes.append("longitude %s outside Rajshahi Division — not used" % lon); lon = None
                    if lat is None or lon is None:
                        lat = lon = None
                else:
                    notes.append("no coordinate in source")
                if lat is not None:
                    qd, qu = locate(lat, lon)
                    if qd and qd != d:
                        notes.append("QA: published point falls in %s/%s (HDX COD-AB polygons), not in %s District — coordinates not used (see extra_json)" % (qd, qu, d))
                        lat = lon = None
                    elif qd and up and qu and qu != up and not thana:
                        notes.append("QA: point falls in %s/%s (HDX COD-AB polygons), not %s as listed — check" % (qd, qu, up))
                if lat is not None:
                    k = (lat, lon)
                    if k in allcoords and allcoords[k] != nm:
                        notes.append("QA: identical coordinates to '%s'" % allcoords[k])
                    allcoords.setdefault(k, nm)
                if len(pairs) > 1 and not sub:
                    notes.append("source gives %d coordinate pairs; first used" % len(pairs))
                if thana:
                    notes.append("upazila_en holds the Rajshahi metropolitan thana (%s), not an upazila" % thana)
                if not up:
                    notes.append("upazila not recognised in location text")
                places.append({
                    "source_key": SOURCE_KEY,
                    "source_id": "%s-%02d%s" % (d.lower(), r["sn"], ("-%d" % (i + 1)) if sub else ""),
                    "name_bn": nm, "category_key": category(nm), "lat": lat, "lon": lon, "address": loc,
                    "district_en": d, "upazila_en": up or "", "operator": "প্রত্নতত্ত্ব অধিদপ্তর (Department of Archaeology)",
                    "ownership": "public",
                    "extra_json": jdump(dict(gz, serial=r["sn"], protected_monument=True, coordinates_as_published=gps if gps not in ("", "-") else None,
                                             group=parent if sub else None, list_published=e["published"] or None)),
                    "source_url": e["pdf"] or LIST_URL, "notes": "; ".join(notes)})
    write_csv(os.path.join(OUT, "places.csv"), PLACE_COLS, places)
    write_csv(os.path.join(OUT, "facts.csv"), FACT_COLS, facts)
    print(len(places), "places", file=sys.stderr)


if __name__ == "__main__":
    main()
