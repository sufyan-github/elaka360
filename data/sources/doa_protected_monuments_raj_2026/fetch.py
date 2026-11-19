#!/usr/bin/env python3
"""Department of Archaeology (archaeology.gov.bd) gazetted protected monuments of Rajshahi Division, one PDF per district.

Usage: python3 fetch.py [--division rajshahi|rangpur|dhaka|chattogram|khulna|barishal|sylhet|mymensingh] [--out DIR]   (default: Rajshahi into this folder; DIVISIONS.md)

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


# Rangpur Division (DIVISIONS.md): district/upazila names, Bangla spellings as used on the portals
RANGPUR_DISTRICTS = {"পঞ্চগড়": "Panchagarh", "দিনাজপুর": "Dinajpur", "লালমনিরহাট": "Lalmonirhat", "নীলফামারী": "Nilphamari",
                     "গাইবান্ধা": "Gaibandha", "ঠাকুরগাঁও": "Thakurgaon", "রংপুর": "Rangpur", "কুড়িগ্রাম": "Kurigram"}
RANGPUR_UPAZILAS = {
    "Panchagarh": [("Panchagarh Sadar", ["পঞ্চগড় সদর"], "panchagarhsadar"), ("Atwari", ["আটোয়ারী", "আটোয়ারি"], "atwari"),
                   ("Boda", ["বোদা"], "boda"), ("Debiganj", ["দেবীগঞ্জ", "দেবিগঞ্জ"], "debiganj"),
                   ("Tetulia", ["তেঁতুলিয়া", "তেতুলিয়া"], "tetulia")],
    "Dinajpur": [("Dinajpur Sadar", ["দিনাজপুর সদর", "কোতোয়ালী"], "dinajpursadar"), ("Birampur", ["বিরামপুর"], "birampur"),
                 ("Birganj", ["বীরগঞ্জ", "বিরগঞ্জ"], "birganj"), ("Biral", ["বিরল"], "birol"),
                 ("Bochaganj", ["বোচাগঞ্জ", "সেতাবগঞ্জ"], "bochaganj"), ("Chirirbandar", ["চিরিরবন্দর"], "chirirbandar"),
                 ("Phulbari", ["ফুলবাড়ী", "ফুলবাড়ি"], "fulbari"), ("Ghoraghat", ["ঘোড়াঘাট"], "ghoraghat"),
                 ("Hakimpur", ["হাকিমপুর"], "hakimpur"), ("Kaharole", ["কাহারোল"], "kaharol"), ("Khansama", ["খানসামা"], "khansama"),
                 ("Nawabganj", ["নবাবগঞ্জ"], "nawabganj"), ("Parbatipur", ["পার্বতীপুর"], "parbatipur")],
    "Lalmonirhat": [("Lalmonirhat Sadar", ["লালমনিরহাট সদর"], "sadar"), ("Aditmari", ["আদিতমারী"], "aditmari"),
                    ("Hatibandha", ["হাতীবান্ধা", "হাতিবান্ধা"], "hatibandha"), ("Kaliganj", ["কালীগঞ্জ"], "kaliganj"),
                    ("Patgram", ["পাটগ্রাম"], "patgram")],
    "Nilphamari": [("Nilphamari Sadar", ["নীলফামারী সদর"], "nilphamarisadar"), ("Dimla", ["ডিমলা"], "dimla"),
                   ("Domar", ["ডোমার"], "domar"), ("Jaldhaka", ["জলঢাকা"], "jaldhaka"), ("Kishoreganj", ["কিশোরগঞ্জ"], "kishorganj"),
                   ("Saidpur", ["সৈয়দপুর"], "syedpur")],
    "Gaibandha": [("Gaibandha Sadar", ["গাইবান্ধা সদর"], "gaibandhasadar"), ("Phulchhari", ["ফুলছড়ি", "ফুলছড়ী"], "phulchari"),
                  ("Gobindaganj", ["গোবিন্দগঞ্জ"], "gobindaganj"), ("Palashbari", ["পলাশবাড়ী", "পলাশবাড়ি"], "palashbari"),
                  ("Sadullapur", ["সাদুল্লাপুর"], "sadullapur"), ("Saghata", ["সাঘাটা"], "saghata"),
                  ("Sundarganj", ["সুন্দরগঞ্জ"], "sundarganj")],
    "Thakurgaon": [("Thakurgaon Sadar", ["ঠাকুরগাঁও সদর"], "thakurgaonsadar"), ("Baliadangi", ["বালিয়াডাঙ্গী", "বালিয়াডাঙ্গি"], "baliadangi"),
                   ("Haripur", ["হরিপুর"], "haripur"), ("Pirganj", ["পীরগঞ্জ"], "pirganj"),
                   ("Ranisankail", ["রাণীশংকৈল", "রানীশংকৈল"], "ranisankail")],
    "Rangpur": [("Rangpur Sadar", ["রংপুর সদর"], "rangpursadar"), ("Badarganj", ["বদরগঞ্জ"], "badargonj"),
                ("Gangachara", ["গংগাচড়া", "গঙ্গাচড়া"], "gangachara"), ("Kaunia", ["কাউনিয়া"], "kaunia"),
                ("Mithapukur", ["মিঠাপুকুর"], "mithapukur"), ("Pirgachha", ["পীরগাছা"], "pirgacha"), ("Pirganj", ["পীরগঞ্জ"], "pirgonj"),
                ("Taraganj", ["তারাগঞ্জ"], "taragonj")],
    "Kurigram": [("Kurigram Sadar", ["কুড়িগ্রাম সদর"], "kurigramsadar"), ("Bhurungamari", ["ভুরুঙ্গামারী"], "bhurungamari"),
                 ("Char Rajibpur", ["চর রাজিবপুর", "রাজিবপুর"], "charrajibpur"), ("Chilmari", ["চিলমারী"], "chilmari"),
                 ("Phulbari", ["ফুলবাড়ী", "ফুলবাড়ি"], "phulbari"), ("Nageshwari", ["নাগেশ্বরী"], "nageshwari"),
                 ("Rajarhat", ["রাজারহাট"], "rajarhat"), ("Raomari", ["রৌমারী"], "rowmari"), ("Ulipur", ["উলিপুর"], "ulipur")],
}
# Rangpur Metropolitan Police thanas (city fallback when no upazila is named)
RANGPUR_CITY_THANAS = {"কোতোয়ালী": "Kotwali", "তাজহাট": "Tajhat", "মাহিগঞ্জ": "Mahiganj", "হারাগাছ": "Haragachh",
                       "পরশুরাম": "Parshuram", "হাজীরহাট": "Hajirhat"}

# Dhaka Division (DIVISIONS.md): district/upazila names, Bangla spellings and common variants
DHAKA_DISTRICTS = {"নরসিংদী": "Narsingdi", "গাজীপুর": "Gazipur", "শরীয়তপুর": "Shariatpur", "নারায়ণগঞ্জ": "Narayanganj",
                   "টাঙ্গাইল": "Tangail", "কিশোরগঞ্জ": "Kishoreganj", "মানিকগঞ্জ": "Manikganj", "ঢাকা": "Dhaka",
                   "মুন্সীগঞ্জ": "Munshiganj", "রাজবাড়ী": "Rajbari", "মাদারীপুর": "Madaripur", "গোপালগঞ্জ": "Gopalganj",
                   "ফরিদপুর": "Faridpur"}
DHAKA_UPAZILAS = {
    "Dhaka": [("Savar", ["সাভার", "আশুলিয়া"], "savar"), ("Dhamrai", ["ধামরাই"], "dhamrai"),
              ("Keraniganj", ["কেরানীগঞ্জ", "কেরাণীগঞ্জ", "কেরানিগঞ্জ"], "keraniganj"), ("Nawabganj", ["নবাবগঞ্জ"], "nawabganj"),
              ("Dohar", ["দোহার"], "dohar")],
    "Gazipur": [("Gazipur Sadar", ["গাজীপুর সদর", "জয়দেবপুর", "টঙ্গী"], "gazipursadar"), ("Kaliakair", ["কালিয়াকৈর"], "kaliakair"),
                ("Kaliganj", ["কালীগঞ্জ", "কালিগঞ্জ"], "kaliganj"), ("Kapasia", ["কাপাসিয়া"], "kapasia"), ("Sreepur", ["শ্রীপুর"], "sreepur")],
    "Narayanganj": [("Narayanganj Sadar", ["নারায়ণগঞ্জ সদর", "ফতুল্লা", "সিদ্ধিরগঞ্জ"], "narayanganjsadar"),
                    ("Araihazar", ["আড়াইহাজার"], "araihazar"), ("Bandar", ["বন্দর"], "bandar"), ("Rupganj", ["রূপগঞ্জ", "রুপগঞ্জ"], "rupganj"),
                    ("Sonargaon", ["সোনারগাঁও", "সোনারগাঁ"], "sonargaon")],
    "Narsingdi": [("Narsingdi Sadar", ["নরসিংদী সদর"], "narsingdisadar"), ("Belabo", ["বেলাবো", "বেলাব"], "belabo"),
                  ("Monohardi", ["মনোহরদী", "মনোহরদি"], "monohardi"), ("Palash", ["পলাশ"], "palash"), ("Raipura", ["রায়পুরা", "উপজেলা- রায়পুর"], "raipura"),
                  ("Shibpur", ["শিবপুর"], "shibpur")],
    "Tangail": [("Tangail Sadar", ["টাঙ্গাইল সদর"], "tangailsadar"), ("Basail", ["বাসাইল"], "basail"), ("Bhuapur", ["ভূঞাপুর", "ভুয়াপুর"], "bhuapur"),
                ("Delduar", ["দেলদুয়ার"], "delduar"), ("Dhanbari", ["ধনবাড়ী", "ধনবাড়ি"], "dhanbari"), ("Ghatail", ["ঘাটাইল"], "ghatail"),
                ("Gopalpur", ["গোপালপুর"], "gopalpur"), ("Kalihati", ["কালিহাতী", "কালিহাতি", "কালীহাতি"], "kalihati"), ("Madhupur", ["মধুপুর"], "madhupur"),
                ("Mirzapur", ["মির্জাপুর"], "mirzapur"), ("Nagarpur", ["নাগরপুর"], "nagarpur"), ("Sakhipur", ["সখিপুর", "সখীপুর"], "sakhipur")],
    "Kishoreganj": [("Kishoreganj Sadar", ["কিশোরগঞ্জ সদর"], "kishoreganjsadar"), ("Austagram", ["অষ্টগ্রাম"], "austagram"),
                    ("Bajitpur", ["বাজিতপুর"], "bajitpur"), ("Bhairab", ["ভৈরব"], "bhairab"), ("Hossainpur", ["হোসেনপুর"], "hossainpur"),
                    ("Itna", ["ইটনা"], "itna"), ("Karimganj", ["করিমগঞ্জ"], "karimganj"), ("Katiadi", ["কটিয়াদী", "কটিয়াদি"], "katiadi"),
                    ("Kuliarchar", ["কুলিয়ারচর"], "kuliarchar"), ("Mithamain", ["মিঠামইন"], "mithamain"), ("Nikli", ["নিকলী", "নিকলি"], "nikli"),
                    ("Pakundia", ["পাকুন্দিয়া"], "pakundia"), ("Tarail", ["তাড়াইল"], "tarail")],
    "Manikganj": [("Manikganj Sadar", ["মানিকগঞ্জ সদর"], "manikganjsadar"), ("Daulatpur", ["দৌলতপুর"], "daulatpur"),
                  ("Ghior", ["ঘিওর"], "ghior"), ("Harirampur", ["হরিরামপুর"], "harirampur"), ("Saturia", ["সাটুরিয়া"], "saturia"),
                  ("Shibalaya", ["শিবালয়"], "shibalaya"), ("Singair", ["সিংগাইর", "সিঙ্গাইর"], "singair")],
    "Munshiganj": [("Munshiganj Sadar", ["মুন্সীগঞ্জ সদর", "মুন্সিগঞ্জ সদর"], "munshiganjsadar"), ("Gazaria", ["গজারিয়া"], "gazaria"),
                   ("Lohajang", ["লৌহজং"], "lohajang"), ("Sirajdikhan", ["সিরাজদিখান", "সিরাজদীখান"], "sirajdikhan"),
                   ("Sreenagar", ["শ্রীনগর"], "sreenagar"), ("Tongibari", ["টংগিবাড়ী", "টঙ্গিবাড়ী", "টংগিবাড়ি", "টঙ্গীবাড়ী"], "tongibari")],
    "Rajbari": [("Rajbari Sadar", ["রাজবাড়ী সদর", "রাজবাড়ি সদর"], "rajbarisadar"), ("Baliakandi", ["বালিয়াকান্দি"], "baliakandi"),
                ("Goalanda", ["গোয়ালন্দ"], "goalanda"), ("Kalukhali", ["কালুখালী", "কালুখালি"], "kalukhali"), ("Pangsha", ["পাংশা"], "pangsha")],
    "Madaripur": [("Madaripur Sadar", ["মাদারীপুর সদর"], "madaripursadar"), ("Dasar", ["ডাসার"], "dasar"), ("Kalkini", ["কালকিনি"], "kalkini"),
                  ("Rajoir", ["রাজৈর"], "rajoir"), ("Shibchar", ["শিবচর"], "shibchar")],
    "Gopalganj": [("Gopalganj Sadar", ["গোপালগঞ্জ সদর"], "gopalganjsadar"), ("Kashiani", ["কাশিয়ানী", "কাশিয়ানি"], "kashiani"),
                  ("Kotalipara", ["কোটালীপাড়া", "কোটালিপাড়া"], "kotalipara"), ("Muksudpur", ["মুকসুদপুর", "মকসুদপুর"], "muksudpur"),
                  ("Tungipara", ["টুংগীপাড়া", "টুঙ্গিপাড়া", "টুঙ্গীপাড়া"], "tungipara")],
    "Faridpur": [("Faridpur Sadar", ["ফরিদপুর সদর"], "faridpursadar"), ("Alfadanga", ["আলফাডাঙ্গা"], "alfadanga"), ("Bhanga", ["ভাঙ্গা"], "bhanga"),
                 ("Boalmari", ["বোয়ালমারী"], "boalmari"), ("Char Bhadrasan", ["চরভদ্রাসন"], "charbhadrasan"),
                 ("Madhukhali", ["মধুখালী", "মধুখালি"], "madhukhali"), ("Nagarkanda", ["নগরকান্দা"], "nagarkanda"),
                 ("Sadarpur", ["সদরপুর"], "sadarpur"), ("Saltha", ["সালথা"], "saltha")],
    "Shariatpur": [("Shariatpur Sadar", ["শরীয়তপুর সদর", "শরিয়তপুর সদর", "পালং"], "shariatpursadar"), ("Bhedarganj", ["ভেদরগঞ্জ"], "bhedarganj"),
                   ("Damudya", ["ডামুড্যা"], "damudya"), ("Gosairhat", ["গোসাইরহাট"], "gosairhat"), ("Naria", ["নড়িয়া"], "naria"),
                   ("Zanjira", ["জাজিরা"], "zanjira")],
}
# Dhaka Metropolitan Police thanas (city fallback when no upazila is named; Dhaka district only)
DHAKA_CITY_THANAS = {"কোতোয়ালী": "Kotwali", "লালবাগ": "Lalbagh", "চকবাজার": "Chawkbazar", "সূত্রাপুর": "Sutrapur",
                     "বংশাল": "Bangshal", "গেন্ডারিয়া": "Gendaria", "ওয়ারী": "Wari", "ধানমন্ডি": "Dhanmondi", "রমনা": "Ramna",
                     "শাহবাগ": "Shahbagh", "হাজারীবাগ": "Hazaribagh", "কামরাঙ্গীরচর": "Kamrangirchar", "মোহাম্মদপুর": "Mohammadpur",
                     "তেজগাঁও": "Tejgaon", "মতিঝিল": "Motijheel", "পল্টন": "Paltan", "খিলগাঁও": "Khilgaon", "সবুজবাগ": "Sabujbagh",
                     "যাত্রাবাড়ী": "Jatrabari", "শ্যামপুর": "Shyampur", "ডেমরা": "Demra", "মিরপুর": "Mirpur", "পল্লবী": "Pallabi",
                     "কাফরুল": "Kafrul", "গুলশান": "Gulshan", "বাড্ডা": "Badda", "উত্তরা": "Uttara", "ক্যান্টনমেন্ট": "Cantonment",
                     "সেনানিবাস": "Cantonment", "কদমতলী": "Kadamtali", "শেরেবাংলা নগর": "Sher-e-Bangla Nagar", "নিউমার্কেট": "New Market"}

# Chattogram Division (DIVISIONS.md): district/upazila names, Bangla spellings and common variants
CHATTOGRAM_DISTRICTS = {"কুমিল্লা": "Cumilla", "ফেনী": "Feni", "ব্রাহ্মণবাড়িয়া": "Brahmanbaria", "রাঙ্গামাটি": "Rangamati",
                        "নোয়াখালী": "Noakhali", "চাঁদপুর": "Chandpur", "লক্ষ্মীপুর": "Lakshmipur", "চট্টগ্রাম": "Chattogram",
                        "কক্সবাজার": "Cox's Bazar", "খাগড়াছড়ি": "Khagrachhari", "বান্দরবান": "Bandarban"}
CHATTOGRAM_UPAZILAS = {
    "Chattogram": [("Anwara", ["আনোয়ারা"], "anwara"), ("Banshkhali", ["বাঁশখালী", "বাঁশখালি"], "banshkhali"),
                   ("Boalkhali", ["বোয়ালখালী", "বোয়ালখালি"], "boalkhali"), ("Chandanaish", ["চন্দনাইশ"], "chandanaish"),
                   ("Fatikchhari", ["ফটিকছড়ি"], "fatikchhari"), ("Hathazari", ["হাটহাজারী", "হাটহাজারি"], "hathazari"),
                   ("Karnaphuli", ["কর্ণফুলী"], "karnaphuli"), ("Lohagara", ["লোহাগাড়া"], "lohagara"),
                   ("Mirsharai", ["মীরসরাই", "মিরসরাই", "মীরেরসরাই"], "mirsharai"), ("Patiya", ["পটিয়া"], "patiya"),
                   ("Rangunia", ["রাঙ্গুনিয়া", "রাঙুনিয়া"], "rangunia"), ("Raozan", ["রাউজান"], "raozan"),
                   ("Sandwip", ["সন্দ্বীপ"], "sandwip"), ("Satkania", ["সাতকানিয়া"], "satkania"),
                   ("Sitakunda", ["সীতাকুণ্ড", "সীতাকুন্ড"], "sitakunda")],
    "Cumilla": [("Cumilla Sadar Dakshin", ["কুমিল্লা সদর দক্ষিণ", "সদর দক্ষিণ"], "sadarsouth"),
                ("Cumilla Adarsha Sadar", ["কুমিল্লা আদর্শ সদর", "আদর্শ সদর", "কুমিল্লা সদর", "কোতোয়ালী", "কোতয়ালী"], "adarshasadar"),
                ("Barura", ["বরুড়া"], "barura"), ("Brahmanpara", ["ব্রাহ্মণপাড়া"], "brahmanpara"),
                ("Burichang", ["বুড়িচং"], "burichang"), ("Chandina", ["চান্দিনা"], "chandina"),
                ("Chauddagram", ["চৌদ্দগ্রাম"], "chauddagram"), ("Daudkandi", ["দাউদকান্দি"], "daudkandi"),
                ("Debidwar", ["দেবিদ্বার"], "debidwar"), ("Homna", ["হোমনা"], "homna"), ("Laksam", ["লাকসাম"], "laksam"),
                ("Lalmai", ["লালমাই"], "lalmai"), ("Meghna", ["মেঘনা"], "meghna"),
                ("Manoharganj", ["মনোহরগঞ্জ"], "monohorgonj"), ("Muradnagar", ["মুরাদনগর"], "muradnagar"),
                ("Nangalkot", ["নাঙ্গলকোট"], "nangalkot"), ("Titas", ["তিতাস"], "titas")],
    "Feni": [("Feni Sadar", ["ফেনী সদর"], "fenisadar"), ("Chhagalnaiya", ["ছাগলনাইয়া"], "chhagalnaiya"),
             ("Daganbhuiyan", ["দাগনভূঞা", "দাগনভুঞা", "দাগনভূঁইয়া"], "daganbhuiyan"), ("Fulgazi", ["ফুলগাজী"], "fulgazi"),
             ("Parshuram", ["পরশুরাম"], "parshuram"), ("Sonagazi", ["সোনাগাজী"], "sonagazi")],
    "Brahmanbaria": [("Brahmanbaria Sadar", ["ব্রাহ্মণবাড়িয়া সদর"], "sadar"), ("Akhaura", ["আখাউড়া"], "akhaura"),
                     ("Ashuganj", ["আশুগঞ্জ"], "ashuganj"), ("Bancharampur", ["বাঞ্ছারামপুর"], "bancharampur"),
                     ("Bijoynagar", ["বিজয়নগর"], "bijoynagar"), ("Kasba", ["কসবা"], "kasba"), ("Nabinagar", ["নবীনগর"], "nabinagar"),
                     ("Nasirnagar", ["নাসিরনগর"], "nasirnagar"), ("Sarail", ["সরাইল"], "sarail")],
    "Rangamati": [("Rangamati Sadar", ["রাঙ্গামাটি সদর"], "sadar"), ("Baghaichhari", ["বাঘাইছড়ি"], "baghaichhari"),
                  ("Barkal", ["বরকল"], "barkal"), ("Belaichhari", ["বিলাইছড়ি"], "belaichhari"),
                  ("Juraichhari", ["জুরাছড়ি"], "juraichhari"), ("Kaptai", ["কাপ্তাই"], "kaptai"), ("Kawkhali", ["কাউখালী"], "kawkhali"),
                  ("Langadu", ["লংগদু"], "langadu"), ("Naniarchar", ["নানিয়ারচর"], "naniarchar"), ("Rajasthali", ["রাজস্থলী"], "rajasthali")],
    "Noakhali": [("Noakhali Sadar", ["নোয়াখালী সদর", "সুধারাম"], "sadar"), ("Begumganj", ["বেগমগঞ্জ"], "begumganj"),
                 ("Chatkhil", ["চাটখিল"], "chatkhil"), ("Companiganj", ["কোম্পানীগঞ্জ", "কোম্পানিগঞ্জ"], "companiganj"),
                 ("Hatiya", ["হাতিয়া"], "hatiya"), ("Kabirhat", ["কবিরহাট"], "kabirhat"), ("Senbagh", ["সেনবাগ"], "senbagh"),
                 ("Sonaimuri", ["সোনাইমুড়ী", "সোনাইমুড়ি"], "sonaimuri"), ("Subarnachar", ["সুবর্ণচর"], "subarnachar")],
    "Chandpur": [("Chandpur Sadar", ["চাঁদপুর সদর"], "sadar"), ("Faridganj", ["ফরিদগঞ্জ"], "faridganj"), ("Haimchar", ["হাইমচর"], "haimchar"),
                 ("Hajiganj", ["হাজীগঞ্জ", "হাজিগঞ্জ"], "hajiganj"), ("Kachua", ["কচুয়া"], "kachua"),
                 ("Matlab Dakshin", ["মতলব দক্ষিণ"], "matlabsouth"), ("Matlab Uttar", ["মতলব উত্তর"], "matlabnorth"),
                 ("Shahrasti", ["শাহরাস্তি"], "shahrasti")],
    "Lakshmipur": [("Lakshmipur Sadar", ["লক্ষ্মীপুর সদর"], "sadar"), ("Kamalnagar", ["কমলনগর"], "kamalnagar"),
                   ("Raipur", ["রায়পুর"], "raipur"), ("Ramganj", ["রামগঞ্জ"], "ramganj"), ("Ramgati", ["রামগতি"], "ramgati")],
    "Cox's Bazar": [("Cox's Bazar Sadar", ["কক্সবাজার সদর"], "sadar"), ("Chakaria", ["চকরিয়া"], "chakaria"),
                    ("Eidgaon", ["ঈদগাঁও"], "eidgaon"), ("Kutubdia", ["কুতুবদিয়া"], "kutubdia"),
                    ("Maheshkhali", ["মহেশখালী"], "maheshkhali"), ("Pekua", ["পেকুয়া"], "pekua"), ("Ramu", ["রামু"], "ramu"),
                    ("Teknaf", ["টেকনাফ"], "teknaf"), ("Ukhia", ["উখিয়া"], "ukhia")],
    "Khagrachhari": [("Khagrachhari Sadar", ["খাগড়াছড়ি সদর"], "sadar"), ("Dighinala", ["দীঘিনালা"], "dighinala"),
                     ("Guimara", ["গুইমারা"], "guimara"), ("Lakshmichhari", ["লক্ষ্মীছড়ি"], "lakshmichhari"),
                     ("Mahalchhari", ["মহালছড়ি"], "mahalchhari"), ("Manikchhari", ["মানিকছড়ি"], "manikchhari"),
                     ("Matiranga", ["মাটিরাঙ্গা"], "matiranga"), ("Panchhari", ["পানছড়ি"], "panchhari"), ("Ramgarh", ["রামগড়"], "ramgarh")],
    "Bandarban": [("Bandarban Sadar", ["বান্দরবান সদর"], "sadar"), ("Alikadam", ["আলীকদম"], "alikadam"), ("Lama", ["লামা"], "lama"),
                  ("Naikhongchhari", ["নাইক্ষ্যংছড়ি"], "naikhongchhari"), ("Rowangchhari", ["রোয়াংছড়ি"], "rowangchhari"),
                  ("Ruma", ["রুমা"], "ruma"), ("Thanchi", ["থানচি"], "thanchi")],
}
# Chattogram Metropolitan Police thanas (city fallback when no upazila is named; Chattogram district only)
CHATTOGRAM_CITY_THANAS = {"কোতোয়ালী": "Kotwali", "কোতয়ালী": "Kotwali", "চকবাজার": "Chawkbazar", "বাকলিয়া": "Bakalia",
                          "পাঁচলাইশ": "Panchlaish", "চান্দগাঁও": "Chandgaon", "বায়েজিদ বোস্তামী": "Bayezid Bostami",
                          "খুলশী": "Khulshi", "ডবলমুরিং": "Double Mooring", "হালিশহর": "Halishahar", "পাহাড়তলী": "Pahartali",
                          "আকবরশাহ": "Akbarshah", "বন্দর": "Bandar", "ইপিজেড": "EPZ", "পতেঙ্গা": "Patenga",
                          "সদরঘাট": "Sadarghat", "কর্ণফুলী": "Karnaphuli"}

# Khulna Division (DIVISIONS.md): district/upazila names, Bangla spellings and common variants (NFC-normalised below)
KHULNA_DISTRICTS = {"খুলনা": "Khulna", "যশোর": "Jashore", "সাতক্ষীরা": "Satkhira", "মেহেরপুর": "Meherpur", "নড়াইল": "Narail",
                    "চুয়াডাঙ্গা": "Chuadanga", "কুষ্টিয়া": "Kushtia", "মাগুরা": "Magura", "বাগেরহাট": "Bagerhat",
                    "ঝিনাইদহ": "Jhenaidah"}
KHULNA_UPAZILAS = {
    "Khulna": [("Batiaghata", ["বটিয়াঘাটা"], "batiaghata"), ("Dacope", ["দাকোপ"], "dacope"), ("Dighalia", ["দিঘলিয়া"], "dighalia"),
               ("Dumuria", ["ডুমুরিয়া"], "dumuria"), ("Koyra", ["কয়রা"], "koyra"), ("Paikgachha", ["পাইকগাছা"], "paikgachha"),
               ("Phultala", ["ফুলতলা"], "phultala"), ("Rupsa", ["রূপসা", "রুপসা"], "rupsha"), ("Terokhada", ["তেরখাদা"], "terokhada")],
    "Jashore": [("Jashore Sadar", ["যশোর সদর"], "sadar"), ("Abhaynagar", ["অভয়নগর"], "abhaynagar"),
                ("Bagherpara", ["বাঘারপাড়া"], "bagherpara"), ("Chaugachha", ["চৌগাছা"], "chougachha"),
                ("Jhikargachha", ["ঝিকরগাছা"], "jhikargachha"), ("Keshabpur", ["কেশবপুর"], "keshabpur"),
                ("Manirampur", ["মণিরামপুর", "মনিরামপুর"], "monirampur"), ("Sharsha", ["শার্শা"], "sharsha")],
    "Satkhira": [("Satkhira Sadar", ["সাতক্ষীরা সদর"], "sadar"), ("Assasuni", ["আশাশুনি"], "assasuni"), ("Debhata", ["দেবহাটা"], "debhata"),
                 ("Kalaroa", ["কলারোয়া"], "kalaroa"), ("Kaliganj", ["কালিগঞ্জ", "কালীগঞ্জ"], "kaliganj"),
                 ("Shyamnagar", ["শ্যামনগর"], "shyamnagar"), ("Tala", ["তালা"], "tala")],
    "Meherpur": [("Meherpur Sadar", ["মেহেরপুর সদর"], "sadar"), ("Gangni", ["গাংনী", "গাংনি"], "gangni"),
                 ("Mujibnagar", ["মুজিবনগর"], "mujibnagar")],
    "Narail": [("Narail Sadar", ["নড়াইল সদর"], "sadar"), ("Kalia", ["কালিয়া"], "kalia"), ("Lohagara", ["লোহাগড়া"], "lohagara")],
    "Chuadanga": [("Chuadanga Sadar", ["চুয়াডাঙ্গা সদর"], "sadar"), ("Alamdanga", ["আলমডাঙ্গা", "আলমডাঙা"], "alamdanga"),
                  ("Damurhuda", ["দামুড়হুদা"], "damurhuda"), ("Jibannagar", ["জীবননগর"], "jibannagar")],
    "Kushtia": [("Kushtia Sadar", ["কুষ্টিয়া সদর"], "sadar"), ("Bheramara", ["ভেড়ামারা"], "bheramara"),
                ("Daulatpur", ["দৌলতপুর"], "daulatpur"), ("Khoksa", ["খোকসা"], "khoksa"),
                ("Kumarkhali", ["কুমারখালী", "কুমারখালি"], "kumarkhali"), ("Mirpur", ["মিরপুর"], "mirpur")],
    "Magura": [("Magura Sadar", ["মাগুরা সদর"], "sadar"), ("Mohammadpur", ["মহম্মদপুর", "মোহাম্মদপুর", "মহাম্মদপুর"], "mohammadpur"),
               ("Shalikha", ["শালিখা"], "shalikha"), ("Sreepur", ["শ্রীপুর"], "sreepur")],
    "Bagerhat": [("Bagerhat Sadar", ["বাগেরহাট সদর"], "sadar"), ("Chitalmari", ["চিতলমারী", "চিতলমারি"], "chitalmari"),
                 ("Fakirhat", ["ফকিরহাট"], "fakirhat"), ("Kachua", ["কচুয়া"], "kachua"), ("Mollahat", ["মোল্লাহাট"], "mollahat"),
                 ("Mongla", ["মোংলা", "মংলা"], "mongla"), ("Morrelganj", ["মোড়েলগঞ্জ", "মোরেলগঞ্জ"], "morrelganj"),
                 ("Rampal", ["রামপাল"], "rampal"), ("Sarankhola", ["শরণখোলা"], "sarankhola")],
    "Jhenaidah": [("Jhenaidah Sadar", ["ঝিনাইদহ সদর"], "sadar"), ("Harinakunda", ["হরিণাকুন্ডু", "হরিণাকুণ্ডু", "হরিনাকুন্ড"], "harinakunda"),
                  ("Kaliganj", ["কালীগঞ্জ", "কালিগঞ্জ"], "kaliganj"), ("Kotchandpur", ["কোটচাঁদপুর"], "kotchandpur"),
                  ("Maheshpur", ["মহেশপুর"], "maheshpur"), ("Shailkupa", ["শৈলকুপা", "শৈলকূপা"], "shailkupa")],
}
# Khulna Metropolitan Police thanas (city fallback when no upazila is named; Khulna district only)
KHULNA_CITY_THANAS = {"কোতোয়ালী": "Khulna Sadar", "কোতয়ালী": "Khulna Sadar", "সোনাডাঙ্গা": "Sonadanga", "খালিশপুর": "Khalishpur",
                      "দৌলতপুর": "Daulatpur", "খানজাহান আলী": "Khan Jahan Ali", "লবণচরা": "Labanchara", "হরিণটানা": "Harintana",
                      "আড়ংঘাটা": "Aranghata"}
_N = lambda x: unicodedata.normalize("NFC", x)
KHULNA_DISTRICTS = {_N(k): v for k, v in KHULNA_DISTRICTS.items()}
KHULNA_UPAZILAS = {d: [(en, [_N(b) for b in bns], sub) for en, bns, sub in ups] for d, ups in KHULNA_UPAZILAS.items()}
KHULNA_CITY_THANAS = {_N(k): v for k, v in KHULNA_CITY_THANAS.items()}

# Barishal Division (DIVISIONS.md): district/upazila names, Bangla spellings and common variants (NFC-normalised below)
BARISHAL_DISTRICTS = {"বরিশাল": "Barishal", "ভোলা": "Bhola", "পটুয়াখালী": "Patuakhali", "পিরোজপুর": "Pirojpur",
                      "ঝালকাঠি": "Jhalokathi", "বরগুনা": "Barguna"}
BARISHAL_UPAZILAS = {
    "Barishal": [("Barishal Sadar", ["বরিশাল সদর"], "sadar"), ("Agailjhara", ["আগৈলঝাড়া"], "agailjhara"),
                 ("Babuganj", ["বাবুগঞ্জ"], "babuganj"), ("Bakerganj", ["বাকেরগঞ্জ"], "bakerganj"),
                 ("Banaripara", ["বানারীপাড়া", "বানারিপাড়া"], "banaripara"), ("Gaurnadi", ["গৌরনদী", "গৌরনদি"], "gaurnadi"),
                 ("Hizla", ["হিজলা"], "hizla"), ("Mehendiganj", ["মেহেন্দিগঞ্জ", "মেহেন্দীগঞ্জ"], "mehendiganj"), ("Muladi", ["মুলাদী", "মুলাদি"], "muladi"),
                 ("Wazirpur", ["উজিরপুর"], "wazirpur")],
    "Bhola": [("Bhola Sadar", ["ভোলা সদর"], "sadar"), ("Burhanuddin", ["বোরহানউদ্দিন", "বোরহানউদ্দীন", "বোরহান উদ্দিন"], "burhanuddin"),
              ("Char Fasson", ["চরফ্যাশন"], "charfasson"), ("Daulatkhan", ["দৌলতখান"], "daulatkhan"), ("Lalmohan", ["লালমোহন"], "lalmohan"),
              ("Manpura", ["মনপুরা"], "manpura"), ("Tazumuddin", ["তজুমদ্দিন", "তজুমুদ্দিন"], "tazumuddin")],
    "Jhalokathi": [("Jhalokathi Sadar", ["ঝালকাঠি সদর"], "sadar"), ("Kanthalia", ["কাঁঠালিয়া", "কাঠালিয়া"], "kanthalia"),
                   ("Nalchity", ["নলছিটি"], "nalchity"), ("Rajapur", ["রাজাপুর"], "rajapur")],
    "Patuakhali": [("Patuakhali Sadar", ["পটুয়াখালী সদর"], "sadar"), ("Bauphal", ["বাউফল"], "bauphal"), ("Dashmina", ["দশমিনা"], "dashmina"),
                   ("Dumki", ["দুমকি", "দুমকী"], "dumki"), ("Galachipa", ["গলাচিপা"], "galachipa"), ("Kalapara", ["কলাপাড়া"], "kalapara"),
                   ("Mirzaganj", ["মির্জাগঞ্জ"], "mirzaganj"), ("Rangabali", ["রাঙ্গাবালী", "রাঙাবালী"], "rangabali")],
    "Pirojpur": [("Pirojpur Sadar", ["পিরোজপুর সদর"], "sadar"), ("Bhandaria", ["ভান্ডারিয়া", "ভাণ্ডারিয়া"], "bhandaria"),
                 ("Kawkhali", ["কাউখালী", "কাউখালি"], "kawkhali"), ("Mathbaria", ["মঠবাড়িয়া", "মঠবাড়ীয়া"], "mathbaria"),
                 ("Nazirpur", ["নাজিরপুর"], "nazirpur"), ("Nesarabad", ["নেছারাবাদ", "স্বরূপকাঠি"], "nesarabad"),
                 ("Indurkani", ["ইন্দুরকানী", "জিয়ানগর"], "indurkani")],
    "Barguna": [("Barguna Sadar", ["বরগুনা সদর"], "sadar"), ("Amtali", ["আমতলী"], "amtali"), ("Bamna", ["বামনা"], "bamna"),
                ("Betagi", ["বেতাগী"], "betagi"), ("Patharghata", ["পাথরঘাটা"], "patharghata"), ("Taltali", ["তালতলী", "তালতলি"], "taltali")],
}
# Barishal Metropolitan Police thanas (city fallback when no upazila is named; Barishal district only)
BARISHAL_CITY_THANAS = {"কোতোয়ালী": "Kotwali", "কোতয়ালী": "Kotwali", "কাউনিয়া": "Kawnia", "বিমানবন্দর": "Airport"}
BARISHAL_DISTRICTS = {_N(k): v for k, v in BARISHAL_DISTRICTS.items()}
BARISHAL_UPAZILAS = {d: [(en, [_N(b) for b in bns], sub) for en, bns, sub in ups] for d, ups in BARISHAL_UPAZILAS.items()}
BARISHAL_CITY_THANAS = {_N(k): v for k, v in BARISHAL_CITY_THANAS.items()}

# Sylhet Division (DIVISIONS.md): district/upazila names, Bangla spellings and common variants (NFC-normalised below)
SYLHET_DISTRICTS = {"সিলেট": "Sylhet", "মৌলভীবাজার": "Moulvibazar", "মৌলভিবাজার": "Moulvibazar", "হবিগঞ্জ": "Habiganj",
                    "সুনামগঞ্জ": "Sunamganj"}
SYLHET_UPAZILAS = {
    "Sylhet": [("Sylhet Sadar", ["সিলেট সদর"], "sadar"), ("Balaganj", ["বালাগঞ্জ"], "balaganj"), ("Beanibazar", ["বিয়ানীবাজার", "বিয়ানিবাজার", "বিয়ানী বাজার"], "beanibazar"),
               ("Bishwanath", ["বিশ্বনাথ"], "bishwanath"), ("Companiganj", ["কোম্পানীগঞ্জ", "কোম্পানিগঞ্জ"], "companiganj"),
               ("Dakshin Surma", ["দক্ষিণ সুরমা", "দক্ষিন সুরমা"], "dakshinsurma"), ("Fenchuganj", ["ফেঞ্চুগঞ্জ"], "fenchuganj"),
               ("Golapganj", ["গোলাপগঞ্জ"], "golapganj"), ("Gowainghat", ["গোয়াইনঘাট"], "gowainghat"),
               ("Jaintiapur", ["জৈন্তাপুর", "জৈন্তিয়াপুর"], "jaintiapur"), ("Kanaighat", ["কানাইঘাট"], "kanaighat"),
               ("Osmani Nagar", ["ওসমানী নগর", "ওসমানীনগর"], "osmaninagar"), ("Zakiganj", ["জকিগঞ্জ"], "zakiganj")],
    "Moulvibazar": [("Moulvibazar Sadar", ["মৌলভীবাজার সদর"], "sadar"), ("Barlekha", ["বড়লেখা"], "barlekha"), ("Juri", ["জুড়ী", "জুড়ি"], "juri"),
                    ("Kamalganj", ["কমলগঞ্জ"], "kamalganj"), ("Kulaura", ["কুলাউড়া"], "kulaura"), ("Rajnagar", ["রাজনগর"], "rajnagar"),
                    ("Sreemangal", ["শ্রীমঙ্গল"], "sreemangal")],
    "Habiganj": [("Habiganj Sadar", ["হবিগঞ্জ সদর"], "sadar"), ("Ajmiriganj", ["আজমিরীগঞ্জ", "আজমিরিগঞ্জ"], "ajmiriganj"),
                 ("Bahubal", ["বাহুবল"], "bahubal"), ("Baniachong", ["বানিয়াচং", "বানিয়াচঙ্গ"], "baniachong"),
                 ("Chunarughat", ["চুনারুঘাট"], "chunarughat"), ("Lakhai", ["লাখাই"], "lakhai"), ("Madhabpur", ["মাধবপুর"], "madhabpur"),
                 ("Nabiganj", ["নবীগঞ্জ", "নবিগঞ্জ"], "nabiganj"), ("Shayestaganj", ["শায়েস্তাগঞ্জ"], "shayestaganj")],
    "Sunamganj": [("Sunamganj Sadar", ["সুনামগঞ্জ সদর"], "sadar"), ("Bishwambarpur", ["বিশ্বম্ভরপুর"], "bishwambarpur"),
                  ("Chhatak", ["ছাতক"], "chhatak"), ("Derai", ["দিরাই"], "derai"), ("Dharmapasha", ["ধর্মপাশা"], "dharmapasha"),
                  ("Dowarabazar", ["দোয়ারাবাজার"], "dowarabazar"), ("Jagannathpur", ["জগন্নাথপুর"], "jagannathpur"),
                  ("Jamalganj", ["জামালগঞ্জ"], "jamalganj"), ("South Sunamganj", ["দক্ষিণ সুনামগঞ্জ", "শান্তিগঞ্জ"], "southsunamganj"),
                  ("Shalla", ["শাল্লা"], "shalla"), ("Tahirpur", ["তাহিরপুর"], "tahirpur"), ("Madhyanagar", ["মধ্যনগর"], "madhyanagar")],
}
# Sylhet Metropolitan Police thanas (city fallback when no upazila is named; Sylhet district only)
SYLHET_CITY_THANAS = {"কোতোয়ালী": "Kotwali", "কোতয়ালী": "Kotwali", "জালালাবাদ": "Jalalabad", "শাহপরাণ": "Shah Poran",
                      "শাহ্‌পরাণ": "Shah Poran", "মোগলাবাজার": "Moglabazar", "বিমানবন্দর": "Airport"}
SYLHET_DISTRICTS = {_N(k): v for k, v in SYLHET_DISTRICTS.items()}
SYLHET_UPAZILAS = {d: [(en, [_N(b) for b in bns], sub) for en, bns, sub in ups] for d, ups in SYLHET_UPAZILAS.items()}
SYLHET_CITY_THANAS = {_N(k): v for k, v in SYLHET_CITY_THANAS.items()}

# Mymensingh Division (DIVISIONS.md): district/upazila names (seed English spellings), Bangla spellings and common variants
MYMENSINGH_DISTRICTS = {"ময়মনসিংহ": "Mymensingh", "জামালপুর": "Jamalpur", "শেরপুর": "Sherpur", "নেত্রকোণা": "Netrokona",
                        "নেত্রকোনা": "Netrokona"}
MYMENSINGH_UPAZILAS = {
    "Mymensingh": [("Mymensingh Sadar", ["ময়মনসিংহ সদর"], "sadar"), ("Bhaluka", ["ভালুকা"], "bhaluka"),
                   ("Dhobaura", ["ধোবাউড়া"], "dhobaura"), ("Fulbaria", ["ফুলবাড়ীয়া", "ফুলবাড়িয়া"], "fulbaria"),
                   ("Gafargaon", ["গফরগাঁও"], "gafargaon"), ("Gouripur", ["গৌরীপুর", "গৌরিপুর"], "gouripur"),
                   ("Haluaghat", ["হালুয়াঘাট"], "haluaghat"), ("Iswarganj", ["ঈশ্বরগঞ্জ"], "iswarganj"),
                   ("Muktagacha", ["মুক্তাগাছা"], "muktagacha"), ("Nandail", ["নান্দাইল"], "nandail"),
                   ("Phulpur", ["ফুলপুর"], "phulpur"), ("Tarakanda", ["তারাকান্দা"], "tarakanda"), ("Trishal", ["ত্রিশাল"], "trishal")],
    "Jamalpur": [("Jamalpur Sadar", ["জামালপুর সদর"], "sadar"), ("Bokshiganj", ["বকশীগঞ্জ", "বকশিগঞ্জ"], "bokshiganj"),
                 ("Dewangonj", ["দেওয়ানগঞ্জ"], "dewanganj"), ("Islampur", ["ইসলামপুর"], "islampur"),
                 ("Madarganj", ["মাদারগঞ্জ"], "madarganj"), ("Melandah", ["মেলান্দহ"], "melandah"),
                 ("Sarishabari", ["সরিষাবাড়ী", "সরিষাবাড়ি"], "sarishabari")],
    "Sherpur": [("Sherpur Sadar", ["শেরপুর সদর"], "sadar"), ("Jhenaigati", ["ঝিনাইগাতী", "ঝিনাইগাতি"], "jhenaigati"),
                ("Nalitabari", ["নালিতাবাড়ী", "নালিতাবাড়ি"], "nalitabari"), ("Nokla", ["নকলা"], "nakla"),
                ("Sreebordi", ["শ্রীবরদী", "শ্রীবরদি", "শ্রীবর্দী"], "sreebardi")],
    "Netrokona": [("Netrokona Sadar", ["নেত্রকোণা সদর", "নেত্রকোনা সদর"], "sadar"), ("Atpara", ["আটপাড়া"], "atpara"),
                  ("Barhatta", ["বারহাট্টা"], "barhatta"), ("Durgapur", ["দুর্গাপুর"], "durgapur"),
                  ("Kalmakanda", ["কলমাকান্দা"], "kalmakanda"), ("Kendua", ["কেন্দুয়া"], "kendua"),
                  ("Khaliajuri", ["খালিয়াজুরী", "খালিয়াজুড়ী", "খালিয়াজুরি"], "khaliajuri"), ("Madan", ["মদন"], "madan"),
                  ("Mohongonj", ["মোহনগঞ্জ"], "mohanganj"), ("Purbadhala", ["পূর্বধলা"], "purbadhala")],
}
MYMENSINGH_CITY_THANAS = {}  # no metropolitan police in Mymensingh: city sites must name their upazila
MYMENSINGH_DISTRICTS = {_N(k): v for k, v in MYMENSINGH_DISTRICTS.items()}
MYMENSINGH_UPAZILAS = {d: [(en, [_N(b) for b in bns], sub) for en, bns, sub in ups] for d, ups in MYMENSINGH_UPAZILAS.items()}


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
HDX_FOLDER = "hdx_cod_ab_bgd"  # the division's HDX COD-AB extract (hdx_cod_ab_bgd_<division> for other divisions)
HDX_DISTRICT_ALIASES = {"Netrakona": "Netrokona"}  # HDX district spelling -> the seed's


def _load_polys():
    global _POLYS
    if _POLYS is not None:
        return _POLYS
    _POLYS = []
    here = os.path.dirname(os.path.abspath(__file__))
    fn = os.path.join(here, "..", HDX_FOLDER, "boundaries.geojson")
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
                return ("Chapainawabganj" if d and d.startswith("Chapai") else HDX_DISTRICT_ALIASES.get(d, d)), u
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
DIVISION, HEAD = "rajshahi", "Rajshahi"
LAT_RANGE, LON_RANGE = (23.7, 25.5), (87.9, 90.0)
# per division: list page "<division> বিভাগের সংরক্ষিত পুরাকীর্তি", district names, upazilas, city thanas, lat/lon sanity box
BY_DIV = {
    "rajshahi": dict(list_url=LIST_URL, districts=DISTRICTS, upazilas=UPAZILAS, thanas=CITY_THANAS, head="Rajshahi",
                     lat=(23.7, 25.5), lon=(87.9, 90.0)),
    "rangpur": dict(list_url="https://archaeology.gov.bd/pages/static-pages/6922dca5933eb65569e1169f", districts=RANGPUR_DISTRICTS,
                    upazilas=RANGPUR_UPAZILAS, thanas=RANGPUR_CITY_THANAS, head="Rangpur", lat=(24.9, 26.7), lon=(87.9, 90.0)),
    "dhaka": dict(list_url="https://archaeology.gov.bd/pages/static-pages/6922dde7933eb65569e16ff2", districts=DHAKA_DISTRICTS,
                  upazilas=DHAKA_UPAZILAS, thanas=DHAKA_CITY_THANAS, head="Dhaka", lat=(22.7, 25.0), lon=(89.2, 91.4),
                  # the Dhaka PDFs: photo captions sit in the 'আলোকচিত্র' column (dropped); more header continuation lines and
                  # a group heading ('লালবাগ দুর্গ:'); Bijoy 'Õ' for the minute mark and a latitude label without its dot
                  photo_col=True, header_tail=r"^\s*g\s{2,}.*AwW©‡bU\s*$|^\s*cyivKxwZ©i bvg\s*$|^\s*jvjevM `yM©:\s*$",
                  gps_fixes={"Õ": "'", '"D ': '"D. '}),    "chattogram": dict(list_url="https://archaeology.gov.bd/pages/static-pages/6922deb6933eb65569e1cce1",
                       districts=CHATTOGRAM_DISTRICTS, upazilas=CHATTOGRAM_UPAZILAS, thanas=CHATTOGRAM_CITY_THANAS,
                       head="Chattogram", lat=(20.5, 24.3), lon=(90.4, 92.8),
                       # the Cumilla PDF repeats the header word 'নাম' (Bijoy 'bvg') on its own line on every page; several
                       # Cumilla rows print the latitude label 'D.' one column to the right, glued to the gazette text, and
                       # location words drift into the coordinate column ('gps_label_split' handles both)
                       header_tail=r"^\s*bvg\s*$", gps_label_split=True),
    "khulna": dict(list_url="https://archaeology.gov.bd/pages/static-pages/6922df45933eb65569e20fab", districts=KHULNA_DISTRICTS,
                   upazilas=KHULNA_UPAZILAS, thanas=KHULNA_CITY_THANAS, head="Khulna", lat=(21.5, 24.3), lon=(88.5, 90.1)),
    "barishal": dict(list_url="https://archaeology.gov.bd/pages/static-pages/6922e128933eb65569e2a90f", districts=BARISHAL_DISTRICTS,
                     upazilas=BARISHAL_UPAZILAS, thanas=BARISHAL_CITY_THANAS, head="Barishal", lat=(21.5, 23.2), lon=(89.7, 91.2)),
    "sylhet": dict(list_url="https://archaeology.gov.bd/pages/static-pages/6922e035933eb65569e26000", districts=SYLHET_DISTRICTS,
                   upazilas=SYLHET_UPAZILAS, thanas=SYLHET_CITY_THANAS, head="Sylhet", lat=(23.9, 25.3), lon=(90.9, 92.6),
                   photo_col=True),  # the 'আলোকচিত্র' column holds '-' where there is no photo (Sylhet-12): dropped
    # Mymensingh: the Jamalpur row has three cells, 'সংরক্ষিত পুরাকীর্তি নেই' in the count column (none_col)
    "mymensingh": dict(list_url="https://archaeology.gov.bd/pages/static-pages/6922dd39933eb65569e14024",
                       districts=MYMENSINGH_DISTRICTS, upazilas=MYMENSINGH_UPAZILAS, thanas=MYMENSINGH_CITY_THANAS,
                       head="Mymensingh", lat=(23.9, 25.5), lon=(89.5, 91.3), none_col=2),
}


def _same_upazila(a, b):
    """Rajshahi compares names exactly (as before); other divisions allow HDX spelling variants (Birol/Biral, Roumari/Raomari)."""
    if DIVISION == "rajshahi":
        return a == b
    import difflib
    k = lambda s: re.sub(r"[^a-z]", "", s.lower().replace("ph", "f").replace("w", "b").replace("sadar", "").replace("dakkhin", "dakshin"))
    x, y = k(a), k(b)
    if "citycorporation" in x + y and "sadar" in (a + b).lower():
        return True
    return x == y or x.endswith(y) or y.endswith(x) or difflib.SequenceMatcher(None, x, y).ratio() >= 0.75

HDR_KEYS = {"loc": ["Ae¯’vb", "অবস্থান"], "gps": ["wRI", "জিও"], "gaz": ["cÖÁvcb", "প্রজ্ঞাপন"], "desc": ["mswÿß", "সংক্ষিপ্ত"]}
SKIP = ["director_general", "feb, Gd-4", "ভবন, এফ-৪", "AvMviMvuI"]
ENG = re.compile(r"\b(and|in|by|of|Ref|Protected|Monuments|Mounds|Bangladesh|District|Department|Archaeology|Museums|Gazette|Notification|No)\b")
TEXT_FIXES = {"হহম্নত": "হেমন্ত"}  # PDF text-layer artefacts in Unicode rows (visible text checked on the page image)
# other divisions: Bijoy-conversion slips (reph after a vowel sign; 'Ý' read as ন্ব) checked against the rendered pages
TEXT_FIXES_BY_DIV = {"rangpur": {"সদার্রপাড়া": "সর্দারপাড়া", "চক্রবতীর্": "চক্রবর্তী", "মুন্বিবাড়ি": "মুন্সিবাড়ি"},
                     # Dhaka: Bijoy slips and broken Unicode text layers (Narsingdi-06, Munshiganj-07, Rajbari, Manikganj-04,
                     # Narayanganj-18), each replaced by the text visible on the rendered page
                     "dhaka": {"মুন্বিগঞ্জ": "মুন্সিগঞ্জ", "কতৃর্ক": "কর্তৃক", "বাণ্টা": "বাড্ডা", "নাটেশবর": "নাটেশ্বর",
                               "বায়তু ন নূ র পাড়াতলী জামে েসজজদ": "বায়তুন নূর পাড়াতলী জামে মসজিদ",
                               "উপজেলা- রায়পু র": "উপজেলা- রায়পুর",
                               "শ্যামসিসির মঠ": "শ্যামসিদ্ধির মঠ",
                               "গ্রাম- শ্যামসিসি ইউসিয়ি- শ্যামসিসি উপজেলা- শ্রীিগর": "গ্রাম- শ্যামসিদ্ধি ইউনিয়ন- শ্যামসিদ্ধি উপজেলা- শ্রীনগর",
                               "জজাড়বাাংলা মন্দির": "জোড়বাংলা মন্দির", "জিালমঞ্চ ও স্নািমঞ্চ": "দোলমঞ্চ ও স্নানমঞ্চ",
                               "উপজজলাাঃ বান্দলয়াকান্দি ইউন্দিয়িাঃ জামালপুর গ্রাম: িন্দলয়া": "উপজেলাঃ বালিয়াকান্দি ইউনিয়নঃ জামালপুর গ্রাম: নলিয়া",
                               "উপজজলাাঃ রাজবাড়ী সির ইউন্দিয়িাঃ িাি ঞ্চ গ্রামাঃ িাি ঞ্চ": "উপজেলাঃ রাজবাড়ী সদর ইউনিয়নঃ খানগঞ্জ গ্রামঃ খানগঞ্জ",
                               "কমপ্লে´ (তালপুকুরসহ) ু র": "কমপ্লেক্স (তালপুকুরসহ)", "সেতুু": "সেতু",
                               "ঢাকেশবরী": "ঢাকেশ্বরী"},
                     # Chattogram: Chandpur-04 'KPzq' + 'v' on the next line (কচুয়া)
                     # and Bijoy slips in Chattogram-07's gazette date (visible: সেপ্টেম্বর) and in the English 'District-wise'
                     "chattogram": {unicodedata.normalize("NFC", "কচুয় া"): unicodedata.normalize("NFC", "কচুয়া"),
                                    "সেন্মেম্বর": "সেপ্টেম্বর", "(District- রিংব)": "(District-wise)",
                                    "(District - রিংব)": "(District-wise)"},
                     # Khulna: Narail-09's '(in.)' makes the converter treat the segment as English (visible: ফয়জুল্লাহ (রহ.) এর);
                     # Khulna-04's u-kar printed as an en dash (visible: রাড়ুলী); Bijoy-converted 'Page' in Jashore-06
                     "khulna": {"dqRyjøvn (in.) Gi": "ফয়জুল্লাহ (রহ.) এর", unicodedata.normalize("NFC", "রাড়–লী"):
                                unicodedata.normalize("NFC", "রাড়ুলী"), "(চধমব- ": "(Page- "},
                     # Barishal: Bijoy slips (visible: সেপ্টেম্বর; Patuakhali-07 আমিরুল্লাহ মুন্সিবাড়ি) and Patuakhali-06's English
                     # gazette reference, whose words 'in', 'by', 'of', 'and' fall into the description column
                     "barishal": {"সেন্মেম্বর": "সেপ্টেম্বর", "আমিরুল্লাাহ মুন্বিবাড়ি": "আমিরুল্লাহ মুন্সিবাড়ি",
                                  "Protected Monuments and Mounds Bangladesh (District - রিংব) 1975 Department Archaeology Museums (Page- 22)":
                                  "Protected Monuments and Mounds in Bangladesh (District-wise) 1975 by Department of Archaeology and Museums (Page- 22)"},
                     # Sylhet: Bijoy 'k^' (শ্ব) and 'k^©' (র্শ্ব) come out as 'শব' / 'শের্ব'; Sylhet-05..08 (visible: জৈন্তাশ্বর,
                     # জৈন্তাশ্বও, পার্শ্বে) and the gazette dates of Sylhet-10/11 (visible: সেপ্টেম্বর)
                     "sylhet": {"জৈন্তাশবর": "জৈন্তাশ্বর", "জৈন্তাশবও": "জৈন্তাশ্বও", "পাশের্ব": "পার্শ্বে", "সেন্মেম্বর": "সেপ্টেম্বর"},
                     # Mymensingh: Bijoy 'k^' (শ্ব) comes out as 'শব' (Mymensingh-06, visible: রাজেশ্বরী); Netrokona-04's i-kar
                     # printed before a space ('Qv`w enxb', visible: ছাদবিহীন)
                     "mymensingh": {"রাজেশবরী": "রাজেশ্বরী", "ছাদি বহীন": "ছাদবিহীন"}}
# rows whose text layer is broken or that sit on a page without a table header: fields replaced by the text visible on
# the rendered page (checked by eye). 'gps' is kept as printed; 'gps_parse' (if any) is what is parsed.
ROW_FIXES_BY_DIV = {"chattogram": {
    ("Chattogram", 6): dict(
        name="হামিদিয়া মসজিদ প্রকাশ (হাম্মাদিয়া)",
        loc="গ্রাম- মসজিদিয়া ইউনিয়ন- ৭ নং কুমিরা উপজেলা- সীতাকুন্ড",
        gps="২২°৩১'৪৬.৪০\"দ. ৯১°৪২'০৪.৪৯\"উ.", gps_parse="২২°৩১'৪৬.৪০\" উ. ৯১°৪২'০৪.৪৯\" পূ.",
        gaz="বাংলাদেশ গেজেট ২২ জানুয়ারি, ২০১৫ (১ম খন্ড পৃষ্টা নং-১০৬)", desc="",
        note="broken text layer: name, location, coordinates and gazette read from the rendered page; the source labels "
             "the latitude 'দ.' and the longitude 'উ.' (read as north/east)"),
    ("Chattogram", 8): dict(
        loc="কোতয়ালী", gps="২২°২০'২৭.৯\" উ. ৯১°৫০'১২.০\" পূ.",
        gaz="বাংলাদেশ গেজেট ২৭ ডিসেম্বর, ২০১৮ (১ম খণ্ড পৃষ্ঠা নং-৮১৭)", desc="",
        note="row printed on a page without the table header: location, coordinates and gazette read from the rendered page"),
}, "khulna": {
    ("Khulna", 7): dict(
        name="কালি মন্দরের ধ্বংসাবশেষের ঢিবি",
        note="broken text layer: name read from the rendered page (spelling 'মন্দরের' as printed)"),
    ("Bagerhat", 20): dict(
        name="কালিবাড়ি ও শিববাড়ি", loc="কচুয়া গ্রামঃ মঘিয়া",
        gps="২২°৬৬'৭২.২০\" উ. ৮৯°৮৭'২৫.২\" পূ.", gaz="বাংলাদেশ গেজেট ০৯ জুলাই ২০২৬", desc="",
        note="broken text layer: name, location, coordinates and gazette read from the rendered page; the coordinates "
             "as printed have minutes/seconds above 59"),
}, "barishal": {
    ("Bhola", 1): dict(
        name="নিগামন মসজিদ", loc="উপজেলাঃ ভোলা সদর ইউনিয়নঃ দক্ষিণ দিঘলদী গ্রামঃ দক্ষিণ দিঘলদী",
        gaz="বাংলাদেশ গেজেট ০৯ জুলাই ২০২৬", desc="",
        note="broken text layer: name, location and gazette read from the rendered page (coordinates parsed as printed)"),
    ("Barishal", 6): dict(
        gps_parse="22055'25.1\" D. 90014'45.7\" c~.",
        note="longitude printed without the dot of its label ('পূ'); parsed as printed"),
    ("Pirojpur", 4): dict(
        gps_parse="22 29'18.4\" D. 90004'55.6\" c~.",
        note="coordinates printed with a stray dot and a spaced label ('.৯০°০৪'৫৫.৬\" পূ .'); parsed as printed"),
    ("Pirojpur", 6): dict(
        gps_parse="",
        note="coordinates as printed (২২°৪৬'২.৯৫৮\" উ. ৯০°০'২৪৮৫৯\" পূ.) have a malformed seconds value and are not used "
             "(kept in extra_json)"),
}}
ROW_FIXES_BY_DIV["mymensingh"] = {
    ("Mymensingh", 1): dict(
        gaz="বাংলাদেশ গেজেট 08 ফেব্রুয়ারি, 1990 (1ম খণ্ড, পৃষ্ঠা-56)",
        note="gazette date and description share text lines in the PDF: gazette reference read from the rendered page"),
    ("Mymensingh", 4): dict(
        gps_parse="",
        note="the coordinates as printed (২৪°১৫'৩৩.৭\" উ. ৯০°১২'৩৬.৫\" পূ.) fall outside Mymensingh Division, in Sakhipur, "
             "Tangail (hdx_cod_ab_bgd_dhaka polygons), about 55 km south of Muktagacha; not used (kept in extra_json)"),
    ("Mymensingh", 12): dict(
        gps="২৪°৪০'৪২২\" উ. ৯০°৫১'৬৪০\" পূ.", gps_parse="", gaz="বাংলাদেশ গেজেট ১২ ফেব্রুয়ারি ২০২৬", desc="",
        note="broken Unicode text layer: coordinates and gazette read from the rendered page; the coordinates as printed "
             "(২৪°৪০'৪২২\" উ. ৯০°৫১'৬৪০\" পূ.) have malformed seconds values and are not used (kept in extra_json); "
             "the name's closing bracket is missing in the source"),
}
ROW_FIXES = {}
GPS_LABEL_SPLIT = False  # per division (BY_DIV gps_label_split)
GPS_FIXES = {}  # per division (BY_DIV gps_fixes): applied to the coordinate text before parsing; the raw string is kept
HEADER_TAIL = None  # other divisions: the header's second line ("নাম ... AwW©‡bU") is skipped, not glued to the last row


def _segs(line):
    return [(m.start(), m.group(0)) for m in re.finditer(r"\S+(?: \S+)*", line)]


def parse_layout(txt, indent=4):
    cols, rows, cur = None, [], None
    for line in txt.splitlines():
        if not line.strip() or any(k in line for k in SKIP):
            continue
        if HEADER_TAIL and HEADER_TAIL.search(line):
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
        if m and len(m.group(1)) < indent:
            cur = {"sn": int(m.group(2)), "name": [], "loc": [], "gps": [], "gaz": [], "desc": []}
            rows.append(cur)
            line = " " * len(m.group(0)) + line[len(m.group(0)):]
        if cur is None:
            continue
        for pos, s in _segs(line):
            best = min((abs(pos - v), k) for k, v in cols.items())[1]
            if best == "name" and pos > cols.get("loc", 80) - 25:
                best = "loc"
            if GPS_LABEL_SPLIT:
                if best != "gps" and (s == "D." or s.startswith("D. ")) and cur.get("gps") and not any("D." in g for g in cur["gps"]):
                    cur["gps"].append("D.")  # latitude label printed one column to the right
                    s, pos = s[3:].strip(), pos + 3
                    if not s:
                        continue
                    best = min((abs(pos - v), k) for k, v in cols.items())[1]
                elif best == "gps" and not re.search(r"\d|D\.|c~|^-$", s):
                    best = "loc"  # a location word that drifted into the coordinate column
            cur.setdefault(best, []).append(s)
    return rows


def conv(segs_):
    s = " ".join(x if ENG.search(x) else bijoy2uni(x) for x in segs_)
    for a, b in TEXT_FIXES.items():
        s = s.replace(a, b)
    if DIVISION != "rajshahi":  # fixes are written in NFC (য় decomposed); match them on the normalised text too
        s = nfc(s)
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
    for a, b in GPS_FIXES.items():
        gps = gps.replace(a, b)
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
    global OUT, RAW, SOURCE_KEY, LIST_URL, DISTRICTS, UPAZILAS, CITY_THANAS, DIVISION, HEAD, LAT_RANGE, LON_RANGE, HDX_FOLDER
    args, OUT, SOURCE_KEY = division_setup(OUT, SOURCE_KEY, list(BY_DIV))
    DIVISION, cfg = args.division, BY_DIV[args.division]
    LIST_URL, DISTRICTS, UPAZILAS, CITY_THANAS, HEAD = cfg["list_url"], cfg["districts"], cfg["upazilas"], cfg["thanas"], cfg["head"]
    LAT_RANGE, LON_RANGE = cfg["lat"], cfg["lon"]
    if DIVISION != "rajshahi":
        global HEADER_TAIL
        HDX_FOLDER = "hdx_cod_ab_bgd_%s" % DIVISION
        TEXT_FIXES.update(TEXT_FIXES_BY_DIV.get(DIVISION, {}))
        HEADER_TAIL = re.compile(r"^\s*নাম\s*$|^\s*নাম\s{2,}.*AwW©‡bU" + ("|" + cfg["header_tail"] if cfg.get("header_tail") else ""))
        if cfg.get("photo_col"):  # photo column: captions are assigned to it and dropped
            HDR_KEYS["photo"] = ["Av‡jvKwPÎ", "আলোকচিত্র"]
        GPS_FIXES.update(cfg.get("gps_fixes", {}))
        global GPS_LABEL_SPLIT
        GPS_LABEL_SPLIT = bool(cfg.get("gps_label_split"))
        ROW_FIXES.update(ROW_FIXES_BY_DIV.get(DIVISION, {}))
    RAW = os.path.join(OUT, "raw")
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
    none_listed = []  # other divisions: districts the page lists with 'সংরক্ষিত পুরাকীর্তি নেই' (no PDF)
    for cells, hrefs in (html_tables(w)[0] if (DIVISION != "rajshahi" and html_tables(w)) else []):
        nc = cfg.get("none_col", 4)  # column holding 'সংরক্ষিত পুরাকীর্তি নেই'
        if len(cells) > nc and cells[1] in DISTRICTS and "নেই" in cells[nc] and not any(h.lower().endswith(".pdf") for h in hrefs):
            none_listed.append({"district_bn": cells[1], "district": DISTRICTS[cells[1]], "text": cells[nc]})
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
        if not rows and DIVISION != "rajshahi":  # serial numbers indented further (Munshiganj PDF)
            rows = parse_layout(txt, indent=8)
        facts.append({"entity_level": "district", "entity_name_en": d, "district_en": d, "fact": "protected_monuments_gazetted",
                      "value": e["count"], "unit": "monuments", "basis": "count stated on the DoA %s Division page" % HEAD,
                      "year": (e["published"][-4:] if e["published"] else ""), "source_key": SOURCE_KEY, "source_url": LIST_URL,
                      "notes": "list published %s; %d rows parsed from the PDF" % (e["published"], len(rows))})
        for r in rows:
            fx = ROW_FIXES.get((d, r["sn"]))
            if fx:
                r.update({k: [v] if v else [] for k, v in fx.items() if k in ("name", "loc", "gps", "gaz", "desc")})
            name = re.sub(r"\s+(ম|-)$", "", conv(r["name"])).strip()
            loc = conv(r["loc"])
            gps = " ".join(r["gps"]).strip()
            gz = gazette(conv(r["gaz"]))
            gz["construction_date_as_stated"] = construction_date(conv(r["desc"]))
            pairs = coord_pairs(fx["gps_parse"] if fx and fx.get("gps_parse") else gps)
            if fx and fx.get("gps_parse") == "":  # coordinates as printed cannot be used (the fix's note says why)
                pairs = []
            subs = [s.strip(" ;,") for s in re.split(r"\(?[কখগঘঙচছজঝঞটত]\)\s*", name)]
            parent, subs = subs[0], [s for s in subs[1:] if s]
            items = [(name, pairs[0] if pairs else None, None)]
            if subs and len(subs) == len(pairs):
                parent = re.sub(r"\(একক পুরাকীর্তি.*?\)", "", parent).strip(" :ঃ")
                items = [("%s — %s" % (parent, s), p, s) for s, p in zip(subs, pairs)]
            locs = [x for x in dict.fromkeys(loc.split(" ")) if x]
            up_d, up = find_upazila(loc, d)
            thana = None
            if not up and d == HEAD:
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
                    if lat is not None and not (LAT_RANGE[0] < lat < LAT_RANGE[1]):
                        notes.append("latitude %s outside %s Division — not used" % (lat, HEAD)); lat = None
                    if lon is not None and not (LON_RANGE[0] < lon < LON_RANGE[1]):
                        notes.append("longitude %s outside %s Division — not used" % (lon, HEAD)); lon = None
                    if lat is None or lon is None:
                        lat = lon = None
                elif fx and fx.get("gps_parse") == "":
                    pass
                elif GPS_LABEL_SPLIT and gps not in ("", "-"):
                    notes.append("coordinate text as published cannot be parsed (kept in extra_json)")
                else:
                    notes.append("no coordinate in source")
                if lat is not None:
                    qd, qu = locate(lat, lon)
                    if qd and qd != d:
                        notes.append("QA: published point falls in %s/%s (HDX COD-AB polygons), not in %s District — coordinates not used (see extra_json)" % (qd, qu, d))
                        lat = lon = None
                    elif qd and up and qu and not _same_upazila(qu, up) and not thana:
                        notes.append("QA: point falls in %s/%s (HDX COD-AB polygons), not %s as listed — check" % (qd, qu, up))
                if lat is not None:
                    k = (lat, lon)
                    if k in allcoords and allcoords[k] != nm:
                        notes.append("QA: identical coordinates to '%s'" % allcoords[k])
                    allcoords.setdefault(k, nm)
                if len(pairs) > 1 and not sub:
                    notes.append("source gives %d coordinate pairs; first used" % len(pairs))
                if thana:
                    notes.append("upazila_en holds the %s metropolitan thana (%s), not an upazila" % (HEAD, thana))
                if not up:
                    notes.append("upazila not recognised in location text")
                if fx:
                    notes.append(fx["note"])
                places.append({
                    "source_key": SOURCE_KEY,
                    "source_id": "%s-%02d%s" % (d.lower(), r["sn"], ("-%d" % (i + 1)) if sub else ""),
                    "name_bn": nm, "category_key": category(nm), "lat": lat, "lon": lon, "address": loc,
                    "district_en": d, "upazila_en": up or "", "operator": "প্রত্নতত্ত্ব অধিদপ্তর (Department of Archaeology)",
                    "ownership": "public",
                    "extra_json": jdump(dict(gz, serial=r["sn"], protected_monument=True, coordinates_as_published=gps if gps not in ("", "-") else None,
                                             group=parent if sub else None, list_published=e["published"] or None)),
                    "source_url": e["pdf"] or LIST_URL, "notes": "; ".join(notes)})
    for z in none_listed:
        facts.append({"entity_level": "district", "entity_name_en": z["district"], "district_en": z["district"],
                      "fact": "protected_monuments_gazetted", "value": 0, "unit": "monuments",
                      "basis": "count stated on the DoA %s Division page" % HEAD, "year": "", "source_key": SOURCE_KEY,
                      "source_url": LIST_URL, "notes": "the page lists the district with '%s' and no PDF" % z["text"]})
    write_csv(os.path.join(OUT, "places.csv"), PLACE_COLS, places)
    write_csv(os.path.join(OUT, "facts.csv"), FACT_COLS, facts)
    if DIVISION != "rajshahi":  # the Rajshahi SOURCE.json is maintained by hand; other divisions get theirs here
        files = ["facts.csv", "places.csv"] + sorted("raw/" + f for f in os.listdir(RAW))
        mp = os.path.join(OUT, "SOURCE.json")
        m = json.load(open(mp, encoding="utf-8")) if os.path.exists(mp) else {
            "key": SOURCE_KEY, "division": DIVISION, "kind": "doa_monuments",
            "name": "Department of Archaeology — gazetted protected monuments, %s Division (district PDF lists)" % HEAD,
            "organization": "প্রত্নতত্ত্ব অধিদপ্তর (Department of Archaeology), Ministry of Cultural Affairs",
            "source_type": "government_portal", "trust_level": 4, "urls": [LIST_URL], "accessed": None, "publication_date": None,
            "license": None, "license_url": None,
            "attribution": "প্রত্নতত্ত্ব অধিদপ্তর (Department of Archaeology), Ministry of Cultural Affairs"}
        import datetime
        m["accessed"] = datetime.date.today().isoformat()
        m["files"] = {f: sha256(os.path.join(OUT, f)) for f in files if os.path.exists(os.path.join(OUT, f))}
        with open(mp, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(m, ensure_ascii=False, indent=2) + "\n")
    print(len(places), "places", file=sys.stderr)


if __name__ == "__main__":
    main()
