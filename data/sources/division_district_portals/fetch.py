#!/usr/bin/env python3
"""Rajshahi Division district portals (7 districts outside Rajshahi District) -> areas.csv + facts.csv.

Source: the official a2i "National Portal" sites of the Deputy Commissioner's offices
(natore.gov.bd, naogaon.gov.bd, chapainawabganj.gov.bd, bogura.gov.bd, joypurhat.gov.bd,
pabna.gov.bd, sirajganj.gov.bd) and, where the district page has no union list or a conflict
needs checking, the upazila portals (<upazila>.<district>.gov.bd).

Usage:  python3 -I fetch.py [--cache DIR]
        --cache DIR  reuse/keep downloaded HTML in DIR (default: a temp dir, deleted afterwards)

Only stdlib + requests. Polite: identifies itself, >= 1.2 s between requests to one host.
TLS is always verified. Many *.gov.bd servers do not send the Sectigo DV R36 intermediate, so the
script downloads it from the certificate's AIA URL, converts it to PEM and appends it to the system
CA bundle in a temp file used as `verify=`. Hosts that still fail are reported as blocked.

Downloaded pages are untrusted input: they are only parsed with regexes, never executed.
Only names, counts and figures are extracted (no prose, no personal phone numbers or names).

Other divisions: python3 -I fetch.py --division <rangpur|...> [--out DIR] [--cache DIR]
  runs the generic division mode (block 'Division mode' below) and writes to the division's own folder
  (default data/sources/division_district_portals_<division>); the Rajshahi outputs in this folder are never touched. With no arguments
  (= --division rajshahi) the script behaves exactly as before; --out DIR redirects the Rajshahi outputs.
"""
import argparse, csv, hashlib, html, json, os, re, shutil, ssl, sys, tempfile, time, unicodedata
from urllib.parse import urljoin, urlparse

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE_KEY = "RAJDIV_DISTRICT_PORTALS_2026"
UA = "Elaka360-data-pipeline (research; contact via repository)"
AIA_URL = "http://crt.sectigo.com/SectigoPublicServerAuthenticationCADVR36.crt"
MIN_GAP = 1.2

# ----------------------------------------------------------------------------- http


class Fetcher:
    def __init__(self, cache_dir):
        self.cache = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.s = requests.Session()
        self.s.headers["User-Agent"] = UA
        self.last = {}
        self.bundle = None
        self.errors = {}

    def _bundle(self):
        if self.bundle:
            return self.bundle
        base = None
        try:
            import certifi  # optional
            base = certifi.where()
        except Exception:
            pass
        if not base or not os.path.isfile(base):
            p = ssl.get_default_verify_paths()
            for c in (p.cafile, p.openssl_cafile, "/etc/ssl/certs/ca-certificates.crt"):
                if c and os.path.isfile(c):
                    base = c
                    break
        der = self.s.get(AIA_URL, timeout=40).content
        pem = ssl.DER_cert_to_PEM_cert(der)
        fd, path = tempfile.mkstemp(suffix=".pem")
        with os.fdopen(fd, "w") as f:
            f.write(open(base).read())
            f.write("\n" + pem)
        self.bundle = path
        return path

    def get(self, url):
        k = hashlib.sha1(url.encode()).hexdigest()
        p = os.path.join(self.cache, k)
        if os.path.exists(p):
            return open(p, "rb").read().decode("utf-8", "replace")
        host = urlparse(url).netloc
        dt = time.time() - self.last.get(host, 0)
        if dt < MIN_GAP:
            time.sleep(MIN_GAP - dt)
        try:
            r = self.s.get(url, timeout=40, verify=self._bundle())
        except requests.exceptions.SSLError as e:
            self.errors[url] = f"TLS verification failed: {str(e)[:160]}"
            return None
        except Exception as e:
            self.errors[url] = f"{type(e).__name__}: {str(e)[:160]}"
            return None
        finally:
            self.last[host] = time.time()
        if r.status_code != 200:
            self.errors[url] = f"HTTP {r.status_code}"
            return None
        open(p, "wb").write(r.content)
        with open(p + ".url", "w") as f:
            f.write(url)
        return r.content.decode("utf-8", "replace")


# ----------------------------------------------------------------------------- parsing helpers

BN = "০১২৩৪৫৬৭৮৯"
MONTHS = {"জানুয়ারি": 1, "জানুয়ারী": 1, "ফেব্রুয়ারি": 2, "ফেব্রুয়ারী": 2, "মার্চ": 3, "এপ্রিল": 4, "মে": 5,
          "জুন": 6, "জুলাই": 7, "আগস্ট": 8, "আগষ্ট": 8, "সেপ্টেম্বর": 9, "অক্টোবর": 10, "নভেম্বর": 11,
          "ডিসেম্বর": 12}


def nfc(s):
    return unicodedata.normalize("NFC", s or "")


def asc(s):
    return "".join(str(BN.index(c)) if c in BN else c for c in s or "")


def text(fragment):
    s = re.sub(r"<script.*?</script>|<style.*?</style>", "", fragment, flags=re.S)
    s = re.sub(r"<br\s*/?>|</p>|</tr>|</li>|</h\d>|</div>", "\n", s)
    s = re.sub(r"</td>|</th>", " | ", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("\xa0", " ").replace("‌", "").replace("‍", "")
    return nfc("\n".join(re.sub(r"[ \t]+", " ", l).strip() for l in s.split("\n") if l.strip()))


def content(page):
    """Main content of an a2i portal page: update date, title, html, text."""
    i = page.find('data-widget_name="ContentViewerWidget"')
    if i < 0:
        return None
    seg = page[i:]
    j = seg.find("এই কনটেন্টটি শেয়ার")
    if j > 0:
        seg = seg[:j]
    m = re.search(r'content-update-block">\s*<p>\s*(.*?)</p>', seg, re.S)
    upd = nfc(html.unescape(m.group(1)).strip()) if m else ""
    m = re.search(r"<h2>(.*?)</h2>", seg, re.S)
    title = text(m.group(1)) if m else ""
    seg = re.sub(r'encoded-content="[^"]*"', "", seg)
    body = seg
    k = body.find("</h2>")
    if k > 0:
        body = body[k + 5:]
    return dict(updated=upd, updated_iso=bn_date(upd), title=title, html=seg, text=text(body))


def bn_date(s):
    m = re.search(r"(\S+), (\S+) (\S+), (\S+) এ", s or "")
    if not m:
        return ""
    d, mon, y = asc(m.group(2)), m.group(3), asc(m.group(4))
    if mon not in MONTHS or not d.isdigit() or not y.isdigit():
        return ""
    return f"{int(y):04d}-{MONTHS[mon]:02d}-{int(d):02d}"


def links(fragment, base=""):
    out = []
    for h, x in re.findall(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', fragment, flags=re.S):
        h = html.unescape(h).strip()
        out.append((urljoin(base, h) if base else h, text(x)))
    return out


def flat(t):
    """Text with ASCII digits, no thousands separators, '|' and newlines as spaces."""
    t = asc(t)
    t = re.sub(r"(?<=\d),(?=\d)", "", t)
    t = t.replace("|", " ").replace("\n", " ")
    return re.sub(r"\s+", " ", t)


def tokens(t):
    return [x.strip() for x in re.split(r"\||\n", t) if x.strip()]


def clean_name(s):
    s = nfc(s).strip(" |।,.;:-")
    s = re.sub(r"\s+", " ", s)
    return s


def strip_up(s):
    """'০১ নং সাঁড়া ইউনিয়ন পরিষদ' -> ('সাঁড়া', '01')."""
    s = clean_name(s)
    no = ""
    m = re.match(r"^([০-৯0-9]+)\s*নং\s*(.*)$", s)
    if m:
        no, s = asc(m.group(1)).zfill(2), m.group(2)
    s = re.sub(r"\s*ইউ\s*,?\s*পি\s*$|\s*ইউপি\s*$", "", s)
    s = re.sub(r"\s*ইউনিয়ন\s*পরিষদ\s*$|\s*ইউনিয়ন\s*$", "", s)
    return clean_name(s), no


# ----------------------------------------------------------------------------- reference names

# Bangla upazila name (any spelling seen on the portals) -> English name used in the project seed.
UPZ_EN = {
    "Natore": {"নাটোর সদর": "Natore Sadar", "সিংড়া": "Singra", "গুরুদাসপুর": "Gurudaspur", "বড়াইগ্রাম": "Baraigram",
               "লালপুর": "Lalpur", "বাগাতিপাড়া": "Bagatipara", "নলডাঙ্গা": "Naldanga"},
    "Naogaon": {"নওগাঁ সদর": "Naogaon Sadar", "আত্রাই": "Atrai", "নিয়ামতপুর": "Niamatpur", "মহাদেবপুর": "Mohadevpur",
                "বদলগাছী": "Badalgachi", "বদলগাছি": "Badalgachi", "সাপাহার": "Sapahar", "ধামইরহাট": "Dhamoirhat",
                "পত্নীতলা": "Patnitala", "পোরশা": "Porsha", "রাণীনগর": "Raninagar", "মান্দা": "Manda"},
    "Chapainawabganj": {"চাঁপাইনবাবগঞ্জ সদর": "Chapainawabganj Sadar", "শিবগঞ্জ": "Shibganj", "গোমস্তাপুর": "Gomostapur",
                        "নাচোল": "Nachol", "ভোলাহাট": "Bholahat"},
    "Bogura": {"বগুড়া সদর": "Bogra Sadar", "শেরপুর": "Sherpur", "ধুনট": "Dhunot", "নন্দীগ্রাম": "Nondigram",
               "নন্দিগ্রাম": "Nondigram", "কাহালু": "Kahaloo", "আদমদীঘি": "Adamdighi", "আদমদিঘি": "Adamdighi",
               "দুপচাঁচিয়া": "Dupchanchia", "সারিয়াকান্দি": "Shariakandi", "গাবতলী": "Gabtali", "শিবগঞ্জ": "Shibganj",
               "সোনাতলা": "Sonatala", "শাজাহানপুর": "Shajahanpur", "মোকামতলা": "Mokamtala"},
    "Joypurhat": {"জয়পুরহাট সদর": "Joypurhat Sadar", "পাঁচবিবি": "Panchbibi", "কালাই": "Kalai", "আক্কেলপুর": "Akkelpur",
                  "ক্ষেতলাল": "Khetlal"},
    "Pabna": {"পাবনা সদর": "Pabna Sadar", "ঈশ্বরদী": "Ishurdi", "আটঘরিয়া": "Atghoria", "বেড়া": "Bera",
              "ভাঙ্গুড়া": "Bhangura", "চাটমোহর": "Chatmohar", "ফরিদপুর": "Faridpur", "সাঁথিয়া": "Santhia",
              "সুজানগর": "Sujanagar"},
    "Sirajganj": {"সিরাজগঞ্জ সদর": "Sirajganj Sadar", "কাজিপুর": "Kazipur", "কামারখন্দ": "Kamarkhand",
                  "শাহজাদপুর": "Shahjadpur", "উল্লাপাড়া": "Ullapara", "রায়গঞ্জ": "Raigonj", "তাড়াশ": "Tarash",
                  "বেলকুচি": "Belkuchi", "চৌহালি": "Chauhali"},
}
DIST_BN = {"Natore": "নাটোর", "Naogaon": "নওগাঁ", "Chapainawabganj": "চাঁপাইনবাবগঞ্জ", "Bogura": "বগুড়া",
           "Joypurhat": "জয়পুরহাট", "Pabna": "পাবনা", "Sirajganj": "সিরাজগঞ্জ"}
DIST_HOST = {"Natore": "natore.gov.bd", "Naogaon": "naogaon.gov.bd", "Chapainawabganj": "chapainawabganj.gov.bd",
             "Bogura": "bogura.gov.bd", "Joypurhat": "joypurhat.gov.bd", "Pabna": "pabna.gov.bd",
             "Sirajganj": "sirajganj.gov.bd"}


def upz_en(district, bn):
    return UPZ_EN[district].get(nfc(bn).strip(), "")


# ----------------------------------------------------------------------------- page catalogue

S = "/pages/static-pages/"
DISTRICT_PAGES = {
    # district: {role: path}
    "Natore": {"glance": S + "697fbb1d35ce18e1c06cc346", "geo": S + "697fbb1d35ce18e1c06cc353",
               "unions": S + "697f803335ce18e1c06b765c"},
    "Naogaon": {"glance": S + "697fd8d335ce18e1c06d6af8", "upazilas": S + "697f79ca35ce18e1c06b5996",
                "unions": S + "697f893c35ce18e1c06b8f47"},
    "Chapainawabganj": {"glance": S + "697fb33635ce18e1c06cb20f", "unions": S + "697f79ad35ce18e1c06b4c52"},
    "Bogura": {"glance": S + "697f93e935ce18e1c06bfc1a", "upazilas": S + "697f93f135ce18e1c06bffbd",
               "unions": S + "697fbb3f35ce18e1c06cd351"},
    "Joypurhat": {"glance": S + "697f896835ce18e1c06ba361", "upazilas": S + "697f79a235ce18e1c06b477e",
                  "unions": S + "697f804135ce18e1c06b7c38", "pourashavas": S + "697fbb1a35ce18e1c06cc16e"},
    "Pabna": {"glance": S + "697fbb1e35ce18e1c06cc3cd"},
    "Sirajganj": {"glance": S + "697fbb0c35ce18e1c06cbb77", "upazilas": S + "698b0bfea351b354e38b7506",
                  "unions": S + "698b0df7e53fc25e0c1a7453", "pourashavas": S + "6a016019897ae53f2213d749"},
}

# Upazila-portal union pages. 'primary' = the union rows for that upazila come from here (district page
# has no list); otherwise the page is a cross-check and only yields a union_count fact + notes.
UPAZILA_UNION_PAGES = [
    # Pabna: the district portal has no union list.
    ("Pabna", "পাবনা সদর", "https://pabnasadar.pabna.gov.bd" + S + "697fbb2035ce18e1c06cc49c", "pabna_sadar", True),
    ("Pabna", "ঈশ্বরদী", "https://ishurdi.pabna.gov.bd" + S + "697f802035ce18e1c06b6d82", "no_list", True),
    ("Pabna", "আটঘরিয়া", "https://atghoria.pabna.gov.bd" + S + "697fb30835ce18e1c06c9b5f", "atghoria", True),
    ("Pabna", "বেড়া", "https://bera.pabna.gov.bd" + S + "697f8d9835ce18e1c06bdebd", "bera", True),
    ("Pabna", "ভাঙ্গুড়া", "https://bhangura.pabna.gov.bd" + S + "697f895335ce18e1c06b99ac", "bhangura", True),
    ("Pabna", "চাটমোহর", "https://chatmohar.pabna.gov.bd" + S + "697fbb2435ce18e1c06cc64b", "dot_list", True),
    ("Pabna", "ফরিদপুর", "https://faridpur.pabna.gov.bd" + S + "697f898335ce18e1c06bafe3", "no_list", True),
    ("Pabna", "সাঁথিয়া", "https://santhia.pabna.gov.bd" + S + "697fb31e35ce18e1c06ca62f", "santhia", True),
    ("Pabna", "সুজানগর", "https://sujanagar.pabna.gov.bd" + S + "697fbb2135ce18e1c06cc534", "dari_list", True),
    # Cross-checks for open conflicts.
    ("Bogura", "গাবতলী", "https://gabtali.bogra.gov.bd" + S + "697fe59635ce18e1c06dc02c", "up_words", False),
    ("Bogura", "সোনাতলা", "https://sonatala.bogra.gov.bd" + S + "69800a0335ce18e1c06e4abe", "paren_list", False),
    ("Bogura", "শিবগঞ্জ", "https://shibganj.bogra.gov.bd" + S + "697fa61a35ce18e1c06c662a", "dari_list", False),
    ("Naogaon", "নিয়ামতপুর", "https://niamatpur.naogaon.gov.bd" + S + "697fb2f335ce18e1c06c91e0", "dari_list", False),
    ("Naogaon", "রাণীনগর", "https://raninagar.naogaon.gov.bd" + S + "697f804935ce18e1c06b7fae", "no_list", False),
    ("Naogaon", "বদলগাছী", "https://badalgachi.naogaon.gov.bd" + S + "697fb2f235ce18e1c06c9164", "paren_num", False),
    ("Sirajganj", "উল্লাপাড়া", "https://ullapara.sirajganj.gov.bd" + S + "697ff45a35ce18e1c06de445", "ullapara", False),
    ("Joypurhat", "কালাই", "https://kalai.joypurhat.gov.bd" + S + "union-uefrue-6a534fb4e38fd9e9177aeef6", "kalai", False),
    ("Chapainawabganj", "গোমস্তাপুর", "https://gomostapur.chapainawabganj.gov.bd" + S + "69800a0835ce18e1c06e4c6c", "dari_list", False),
    ("Natore", "সিংড়া", "https://singra.natore.gov.bd" + S + "697fbb2335ce18e1c06cc5fd", "no_list", False),
    ("Natore", "লালপুর", "https://lalpur.natore.gov.bd" + S + "697fa5e435ce18e1c06c4d0f", "no_list", False),
    ("Natore", "গুরুদাসপুর", "https://gurudaspur.natore.gov.bd" + S + "697fbb5135ce18e1c06cdb38", "paren_num", False),
    ("Natore", "বাগাতিপাড়া", "https://bagatipara.natore.gov.bd" + S + "697fe57235ce18e1c06dafd5", "no_list", False),
]

# Upazila "at a glance" pages: stated union count (and other headline counts) only.
UPAZILA_GLANCE_PAGES = [
    ("Bogura", "গাবতলী", "https://gabtali.bogra.gov.bd" + S + "697fe55d35ce18e1c06da5e3"),
    ("Bogura", "সোনাতলা", "https://sonatala.bogra.gov.bd" + S + "6a940fc8df1fe8071fd8e020"),
    ("Bogura", "মোকামতলা", "https://mokamtala.bogra.gov.bd" + S + "about-mokamtala-3kq4ps-6a7ab5810d40e295f00b2df2"),
    ("Pabna", "ভাঙ্গুড়া", "https://bhangura.pabna.gov.bd" + S + "697f897d35ce18e1c06bad15"),
    ("Pabna", "বেড়া", "https://bera.pabna.gov.bd" + S + "697fbb2035ce18e1c06cc4c8"),
    ("Pabna", "আটঘরিয়া", "https://atghoria.pabna.gov.bd" + S + "697fb30a35ce18e1c06c9c92"),
    ("Sirajganj", "উল্লাপাড়া", "https://ullapara.sirajganj.gov.bd" + S + "697fbb0e35ce18e1c06cbc48"),
    ("Joypurhat", "কালাই", "https://kalai.joypurhat.gov.bd" + S + "kalai-upazila-at-a-glance-speyse-6a535264ae43f9166fa94458"),
]

# Pourashava pages on upazila portals: (district, upazila_bn, url, name regex, ward regex, class regex)
POURASHAVA_PAGES = [
    ("Natore", "সিংড়া", "https://singra.natore.gov.bd" + S + "697fbb2f35ce18e1c06ccba8",
     r"নাম ঃ (সিংড়া পৌরসভা)", r"ওয়ার্ড সংখ্যা ঃ (\d+)টি", r"শ্রেনী ঃ ‘(\S)’"),
    ("Natore", "লালপুর", "https://lalpur.natore.gov.bd" + S + "697f8d5d35ce18e1c06bc3f5",
     r"পৌরসভার নামঃ (গোপালপুর পৌরসভা)", r"ওয়ার্ড সংখ্যা (\d+) টি", None),
    ("Natore", "বাগাতিপাড়া", "https://bagatipara.natore.gov.bd" + S + "6980024435ce18e1c06e205a",
     r"এক নজরে (বাগাতিপাড়া পৌরসভা)", r"ওয়ার্ড সংখ্যা ঃ (\d+) টি", r"শ্রেনী ঃ (\S) শ্রেনী"),
    ("Naogaon", "নওগাঁ সদর", "https://naogaonsadar.naogaon.gov.bd" + S + "697fd8e335ce18e1c06d72ad",
     r"পৌরসভা নাম ঃ (নওগাঁ পৌরসভা)", r"ওয়ার্ড= (\d+)", None),
    ("Bogura", "ধুনট", "https://dhunot.bogra.gov.bd" + S + "697ffd9835ce18e1c06e1405",
     r"একনজরে (ধুনট পৌরসভা)", None, None),
    ("Bogura", "কাহালু", "https://kahaloo.bogra.gov.bd" + S + "697f804f35ce18e1c06b8261",
     r"এক নজরে (কাহালু পৌরসভা)", None, None),
    ("Bogura", "আদমদীঘি", "https://adamdighi.bogra.gov.bd" + S + "697f894d35ce18e1c06b970e",
     r"পৌরসভা : (সান্তাহার)", None, None),
    ("Bogura", "দুপচাঁচিয়া", "https://dupchanchia.bogra.gov.bd" + S + "697fe57735ce18e1c06db203",
     r"(দুপচাঁচিয়া পৌরসভা) গঠনের তারিখ", None, None),
    ("Bogura", "দুপচাঁচিয়া", "https://dupchanchia.bogra.gov.bd" + S + "697f93fa35ce18e1c06c03d6",
     r"পৌরসভার নামঃ- (তালোড়া পৌরসভা)", None, None),
    ("Bogura", "সোনাতলা", "https://sonatala.bogra.gov.bd" + S + "6a940fc8df1fe8071fd8e020",
     r"(সোনাতলা পৌরসভা) \d+টি ওয়ার্ড", r"সোনাতলা পৌরসভা (\d+)টি ওয়ার্ড", None),
    ("Pabna", "পাবনা সদর", "https://pabnasadar.pabna.gov.bd" + S + "697fbb3335ce18e1c06ccdd9",
     r"একনজরে (পাবনা পৌরসভা)", None, None),
    ("Pabna", "ঈশ্বরদী", "https://ishurdi.pabna.gov.bd" + S + "697fbb2535ce18e1c06cc709",
     r"পৌরসভার নাম: (ঈশ্বরদী)", r"মোট ওয়ার্ড সংখ্যা: (\d+) টি", None),
    ("Pabna", "বেড়া", "https://bera.pabna.gov.bd" + S + "697fa62035ce18e1c06c6927",
     r"পৌরসভার নামঃ-(বেড়া পৌরসভা)", r"মোট ওয়ার্ড সংখ্যাঃ- (\d+)", None),
    ("Pabna", "চাটমোহর", "https://chatmohar.pabna.gov.bd" + S + "697fa61d35ce18e1c06c67c0",
     r"নাম (চাটমোহর পৌরসভা)", None, None),
    ("Pabna", "সাঁথিয়া", "https://santhia.pabna.gov.bd" + S + "697fa5e335ce18e1c06c4cbd",
     r"পৌরসভার নামঃ (সাঁথিয়া পৌরসভা)", None, None),
    ("Pabna", "সুজানগর", "https://sujanagar.pabna.gov.bd" + S + "697fa60335ce18e1c06c5b8d",
     r"এক নজরে (সুজানগর পৌরসভা)", r"ওয়ার্ড সংখ্যা : (\d+)টি", None),
    ("Pabna", "আটঘরিয়া", "https://atghoria.pabna.gov.bd" + S + "697fc1ea35ce18e1c06cea0b",
     r"এক নজরে (আটঘরিয়া পৌরসভা)", r"ওয়ার্ড সংখ্যা (\d+)টি", None),
]

# District "at a glance" figures: fact -> (regex on flat() text, unit, basis, year, note)
GLANCE = {
    "Natore": [
        ("area", r"আয়তন (\d+(?:\.\d+)?) বর্গ কিলোমিটার জনসংখ্যা", "km2", "as stated", "", ""),
        ("population", r"\(2022 সালের আদমশুমারী অনুযায়ী\) (\d+) জন", "persons", "census", "2022", ""),
        ("upazila_count", r"উপজেলা 0?(\d+)টি", "count", "as stated", "", ""),
        ("thana_count", r"থানা 0?(\d+)টি", "count", "as stated", "", ""),
        ("pourashava_count", r"পৌরসভা 0?(\d+)টি", "count", "as stated", "", ""),
        ("union_count", r"ইউনিয়ন (\d+)টি", "count", "as stated", "", ""),
        ("village_count", r"গ্রাম (\d+)টি", "count", "as stated", "", ""),
        ("mouza_count", r"মৌজা (\d+)টি", "count", "as stated", "", ""),
    ],
    "Naogaon": [
        ("area", r"আয়তন (\d+(?:\.\d+)?) বঃকিঃ", "km2", "as stated", "", "prose on same page also says 3435.65 km2"),
        ("population", r"লোক সংখ্যা (\d+) জন", "persons", "census", "2022", "page: 2022 সনের আদম শুমারী অনুযায়ী"),
        ("upazila_count", r"উপজেলা সংখ্যা (\d+)টি", "count", "as stated", "", ""),
        ("pourashava_count", r"পৌর সভার সংখ্যা 0?(\d+)টি", "count", "as stated", "", "prose names নওগাঁ, নজিপুর, ধামইরহাট পৌরসভা"),
        ("union_count", r"ইউনিয়ন পরিষদের সংখ্যা (\d+)টি", "count", "as stated", "", ""),
        ("village_count", r"গ্রামের সংখ্যা (\d+)টি", "count", "as stated", "", ""),
    ],
    "Chapainawabganj": [
        ("area", r"আয়তন (\d+(?:\.\d+)?) বর্গকিলোমিটার", "km2", "as stated", "", ""),
        ("population", r"জনসংখ্যা (\d+) জন \(জনশুমারি ও গৃহগণনা 2022\)", "persons", "census", "2022", ""),
        ("upazila_count", r"উপজেলা 0?(\d+) টি", "count", "as stated", "", ""),
        ("pourashava_count", r"পৌরসভা 0?(\d+) টি", "count", "as stated", "", ""),
        ("union_count", r"ইউনিয়ন (\d+) টি", "count", "as stated", "", ""),
        ("mouza_count", r"মৌজা (\d+) টি", "count", "as stated", "", ""),
        ("village_count", r"গ্রাম (\d+) টি", "count", "as stated", "", ""),
    ],
    "Bogura": [
        ("area", r"আয়তন \(বর্গ কিমি\) (\d+)", "km2", "as stated", "", ""),
        ("population", r"জনসংখ্যা মোট: (\d+) জন", "persons", "as stated", "", "year/basis not stated on page"),
        ("upazila_count", r"মোট (\d+) টি উপজেলার নাম", "count", "as stated", "", "list includes মোকামতলা"),
    ],
    "Joypurhat": [
        ("area", r"জেলার আয়তনঃ (\d+(?:\.\d+)?) বর্গ কিলোমিটার", "km2", "as stated", "", ""),
        ("population", r"মোট লোকসংখ্যাঃ (\d+) জন", "persons", "census", "2022",
         "census table on the same page shows 956431"),
        ("upazila_count", r"মোট উপজেলার সংখ্যাঃ 0?(\d+) টি", "count", "as stated", "", ""),
        ("pourashava_count", r"মোট পৌরসভার সংখ্যাঃ 0?(\d+) টি", "count", "as stated", "", "04 'ক' class, 01 'খ' class"),
        ("union_count", r"মোট ইউনিয়নের সংখ্যাঃ (\d+) টি", "count", "as stated", "", ""),
        ("village_count", r"মোট গ্রামের সংখ্যাঃ (\d+) টি", "count", "as stated", "", ""),
        ("mouza_count", r"মোট মৌজার সংখ্যাঃ (\d+) টি", "count", "as stated", "", ""),
    ],
    "Pabna": [
        ("area", r"আয়তনঃ (\d+(?:\.\d+)?) বর্গ কিঃ মিঃ", "km2", "as stated", "", ""),
        ("population", r"লোকসংখ্যাঃ (\d+)", "persons", "as stated", "", "year/basis not stated on page"),
        ("upazila_count", r"উপজেলার সংখ্যাঃ (\d+) টি", "count", "as stated", "", ""),
        ("thana_count", r"থানার সংখ্যাঃ (\d+) টি", "count", "as stated", "", ""),
        ("pourashava_count", r"পৌরসভার সংখ্যাঃ (\d+) টি", "count", "as stated", "", "page: আটঘরিয়া পৌরসভা-নবগঠিত"),
        ("union_count", r"ইউনিয়নের সংখ্যাঃ (\d+) টি", "count", "as stated", "", ""),
        ("village_count", r"গ্রামের সংখ্যাঃ (\d+) টি", "count", "as stated", "", ""),
        ("mouza_count", r"মৌজার সংখ্যাঃ (\d+) টি", "count", "as stated", "", ""),
    ],
    "Sirajganj": [
        ("area", r"আয়তন (\d+(?:\.\d+)?) বর্গ কিলোমিটার", "km2", "as stated", "", ""),
        ("population", r"মোট = (\d+) জন", "persons", "as stated", "", "year/basis not stated on page"),
        ("upazila_count", r"উপজেলার সংখ্যা 0?(\d+) টি", "count", "as stated", "", ""),
        ("thana_count", r"থানার সংখ্যা (\d+) টি", "count", "as stated", "", ""),
        ("pourashava_count", r"পৌরসভার সংখ্যা 0?(\d+) টি", "count", "as stated", "", ""),
        ("union_count", r"ইউনিয়নের সংখ্যা (\d+) টি", "count", "as stated", "", ""),
        ("mouza_count", r"মৌজার সংখ্যা (\d+) টি", "count", "as stated", "", ""),
        ("village_count", r"গ্রামের সংখ্যা (\d+) টি", "count", "as stated", "", ""),
    ],
}
GEO_EXTRA = [("Natore", "geo", "area", r"নাটোর জেলার আয়তন (\d+(?:\.\d+)?) বর্গকিলোমিটার", "km2",
              "ভৌগোলিক পরিচিতি page; differs from এক নজরে (1896.05)")]

# ----------------------------------------------------------------------------- district union-list parsers
# Each returns a list of dicts: upazila_bn, name_bn, name_en, website, serial, union_no, note


def p_natore(c):
    out, cur = [], None
    for l in c["text"].split("\n"):
        m = re.match(r"^(\S.*?) - (https?://\S+)$", l)
        if m:
            cur = clean_name(m.group(1))
            continue
        m = re.match(r"^([০-৯]+)\.\s*\|\s*(.+?)\s*\|\s*(https?://\S+)", l)
        if m and cur:
            out.append(dict(upazila_bn=cur, name_bn=clean_name(m.group(2)), name_en="", website=m.group(3).strip(),
                            serial=asc(m.group(1))))
    return out


def p_naogaon(c):
    href = {}
    for h, x in links(c["html"]):
        href.setdefault(clean_name(re.sub(r"^[০-৯]+।?\s*", "", x)), h)
    out, cur = [], None
    for l in c["text"].split("\n"):
        m = re.match(r"^([০-৯]+)।\s*([^|]+?)\s*\|\s*(.*)$", l)
        if m and m.group(3).strip():  # "১। নওগাঁ সদর | ১।বর্ষাইল |"
            cur = clean_name(m.group(2))
            l = m.group(3)
        m = re.match(r"^([০-৯]+)।?\s*([^|০-৯][^|]*?)\s*\|?$", l.strip())
        if m and cur:
            nm = clean_name(m.group(2))
            if nm and not re.match(r"^পাতা\s*-", nm):  # page-break markers like "পাতা-২"
                out.append(dict(upazila_bn=cur, name_bn=nm, name_en="", website=href.get(nm, ""),
                                serial=asc(m.group(1))))
        elif cur and l.strip() == "|":
            pass
    # the Niamatpur block skips serial 2 (an empty cell); record it as a gap
    return out


def p_chapai(c):
    t = c["text"]
    head, _, body = t.partition("ইউনিয়ন সমূহের নাম")
    ups = [clean_name(x) for x in head.split("\n") if x.startswith("|") and clean_name(x)]
    cells = [x for x in re.split(r"\n\|", "\n" + body) if x.strip(" |\n")]
    href = {clean_name(x): h for h, x in links(c["html"])}
    out = []
    for u, cell in zip(ups, cells):
        for i, nm in enumerate([clean_name(x) for x in cell.split("\n") if clean_name(x)], 1):
            out.append(dict(upazila_bn=u, name_bn=nm, name_en="", website=href.get(nm, ""), serial=str(i)))
    return out


def p_bogura(c):
    tk = [x.strip().replace("\n", " ") for x in c["text"].split("|") if x.strip()]
    out, cur, i = [], None, 0
    while i < len(tk):
        t = tk[i]
        m = re.match(r"^(.+?)\s*\((.+)\)$", t)
        if m and m.group(1) != "বগুড়া" and "ইউনিয়নের নাম" not in t:
            cur = (clean_name(m.group(1)), m.group(2).strip())
            i += 1
            continue
        if re.fullmatch(r"[০-৯]+", t) and cur and i + 2 < len(tk) and not re.fullmatch(r"[০-৯]+", tk[i + 1]):
            out.append(dict(upazila_bn=cur[0], upazila_en_src=cur[1], name_bn=clean_name(tk[i + 1]),
                            name_en=tk[i + 2].strip(), website="", serial=asc(t)))
            i += 3
            continue
        i += 1
    return out


def p_joypurhat(c):
    href = {}
    for h, x in links(c["html"]):
        href.setdefault(clean_name(re.sub(r"^[০-৯]+\.\s*", "", x)), h)
    out, cur = [], None
    tk = tokens(c["text"])
    for i, t in enumerate(tk):
        if re.fullmatch(r"[০-৯]+", t) and i + 1 < len(tk) and not re.match(r"^[০-৯]+\.", tk[i + 1]):
            cur = clean_name(tk[i + 1])
            continue
        m = re.match(r"^([০-৯]+)\.\s*(.+)$", t)
        if m and cur:
            nm = clean_name(m.group(2))
            out.append(dict(upazila_bn=cur, name_bn=nm, name_en="", website=href.get(nm, ""), serial=asc(m.group(1))))
    return out


def p_sirajganj(c):
    t = c["text"].split("উপজেলার নাম", 1)[-1]
    tk = tokens(t)
    out, cur, i = [], None, 0
    while i < len(tk):
        if re.fullmatch(r"[০-৯]+", tk[i]) and i + 1 < len(tk):
            nm = clean_name(tk[i + 1])
            serial = asc(tk[i])
            j = i + 2
            if serial == "1" and j < len(tk) and not re.fullmatch(r"[০-৯]+", tk[j]):
                cur = clean_name(tk[j])
                j += 1
            out.append(dict(upazila_bn=cur, name_bn=nm, name_en="", website="", serial=serial))
            i = j
            continue
        i += 1
    return out


DISTRICT_PARSERS = {"Natore": p_natore, "Naogaon": p_naogaon, "Chapainawabganj": p_chapai, "Bogura": p_bogura,
                    "Joypurhat": p_joypurhat, "Sirajganj": p_sirajganj}

# ----------------------------------------------------------------------------- upazila union-page parsers


def u_pabna_sadar(c):
    tk = tokens(c["text"])
    out = []
    for i, t in enumerate(tk):
        if re.fullmatch(r"[০-৯]+", t) and i + 2 < len(tk) and tk[i + 2].startswith("http"):
            nm, no = strip_up(tk[i + 1])
            out.append(dict(name_bn=nm, website=tk[i + 2], serial=asc(t), union_no=""))
    return out


def u_no_list(c):
    """'০১ নং সাঁড়া ইউনিয়ন পরিষদ' / '১ নং লালপুর ইউনিয়ন পরিষদ' / '১নং খট্টেশ্বর ... | https://…'"""
    t = c["text"]
    out = []
    for m in re.finditer(r"([০-৯]+)\s*নং\s*([^|\n০-৯]+?)\s*ইউ(?:নিয়ন|,?\s*পি)", t):
        nm = clean_name(m.group(2).replace("ইউনিয়ন", ""))
        rest = t[m.end():m.end() + 160]
        w = re.search(r"(https?://[^\s|]+)", rest.split("\n")[0] + " " + " ".join(rest.split("\n")[1:2]))
        out.append(dict(name_bn=nm, website=w.group(1) if w else "", serial="", union_no=asc(m.group(1)).zfill(2)))
    if not out:  # "১ নং পাঁকা, ২নং জামনগর, ..."
        for m in re.finditer(r"([০-৯]+)\s*নং\s*([^,০-৯\n|]+)", t):
            out.append(dict(name_bn=clean_name(m.group(2)), website="", serial="", union_no=asc(m.group(1)).zfill(2)))
    return out


def u_atghoria(c):
    tk = tokens(c["text"])
    out = []
    for i, t in enumerate(tk):
        if re.fullmatch(r"[০-৯]+", t) and i + 1 < len(tk):
            nm = clean_name(tk[i + 1])
            w = next((x for x in tk[i + 1:i + 4] if x.startswith("http")), "")
            out.append(dict(name_bn=nm, website=w, serial=asc(t), union_no=""))
    return out


def u_bera(c):
    return []  # page states the count in words only (see facts)


def u_bhangura(c):
    tk = tokens(c["text"])
    out = []
    for i, t in enumerate(tk[:-1]):
        if re.fullmatch(r"[০-৯]{4,6}", tk[i + 1]) and re.fullmatch(r"[ঀ-৿ ]+", t) and "ঠিকানা" not in t:
            out.append(dict(name_bn=clean_name(t), website="", serial=str(len(out) + 1), union_no=""))
    return out


def u_dot_list(c):
    t = c["text"].split("ইউনিয়ন ডিজিটাল সেন্টার")[0]
    return [dict(name_bn=strip_up(m.group(2))[0], website="", serial=asc(m.group(1)), union_no="")
            for m in re.finditer(r"^([০-৯]+)\.\s*(.+?)$", t, re.M)]


def u_santhia(c):
    tk = tokens(c["text"])
    out = []
    for i, t in enumerate(tk):
        if re.fullmatch(r"[০-৯]+", t) and i + 2 < len(tk):
            out.append(dict(name_bn=strip_up(tk[i + 1])[0], name_en=re.sub(r"\s*Union\s*Parishad$", "", tk[i + 2]).strip(),
                            website="", serial=asc(t), union_no=""))
    return out


def u_dari_list(c):
    """'০১। ভায়না | ০৬। সাগরকান্দি |' or '১। ময়দানহাটা ( http://… )' or '১। হাজীনগর ইউনিয়ন,'"""
    out = []
    for m in re.finditer(r"([০-৯]+)।\s*([^|।,(\n০-৯]+?)\s*(?:\(\s*(https?://[^\s)]+)\s*\))?\s*(?=[|,\n]|[০-৯]+।|$)", c["text"]):
        out.append(dict(name_bn=strip_up(m.group(2))[0], website=m.group(3) or "", serial=asc(m.group(1)), union_no=""))
    return sorted(out, key=lambda r: int(r["serial"]))


def u_paren_num(c):
    """'১)বদলগাছী ২)মথুরাপুর' / '১) নাজিরপুর, ২) বিয়াঘাট'"""
    return [dict(name_bn=strip_up(m.group(2))[0], website="", serial=asc(m.group(1)), union_no="")
            for m in re.finditer(r"([০-৯]+)\)\s*([^,০-৯\n|]+)", c["text"])]


def u_paren_list(c):
    """'(১) সোনাতলা ইউনিয়ন পরিষদ।'"""
    return [dict(name_bn=strip_up(m.group(2))[0], website="", serial=asc(m.group(1)), union_no="")
            for m in re.finditer(r"\(([০-৯]+)\)\s*([^।(]+)", c["text"])]


def u_up_words(c):
    return [dict(name_bn=strip_up(m.group(1))[0], website="", serial=str(i), union_no="")
            for i, m in enumerate(re.finditer(r"([ঀ-৿]+) ইউনিয়ন পরিষদ", c["text"]), 1)]


def u_ullapara(c):
    out = []
    for m in re.finditer(r"([০-৯]+)\s*\|\s*([^|]+?)\s*ইউ,?পি\s*\|\s*(https?://\S+)?", c["text"]):
        out.append(dict(name_bn=clean_name(m.group(2)), website=(m.group(3) or "").strip(" |"),
                        serial=asc(m.group(1)), union_no=""))
    return out


def u_kalai(c):
    t = c["text"]
    m = re.search(r"ইউনিয়ন রয়েছে\s*(.+?)(?:ফাইল|$)", t, re.S)
    names = re.findall(r"([ঀ-৿]+) ইউনিয়ন", m.group(1)) if m else []
    return [dict(name_bn=n, website="", serial=str(i), union_no="") for i, n in enumerate(names, 1)]


UPZ_PARSERS = {"pabna_sadar": u_pabna_sadar, "no_list": u_no_list, "atghoria": u_atghoria, "bera": u_bera,
               "bhangura": u_bhangura, "dot_list": u_dot_list, "santhia": u_santhia, "dari_list": u_dari_list,
               "paren_num": u_paren_num, "paren_list": u_paren_list, "up_words": u_up_words,
               "ullapara": u_ullapara, "kalai": u_kalai}

# Counts stated in words/figures on upazila pages: (regex on flat text) -> union_count
STATED_UNION_COUNT = [
    r"ইউনিয়ন সংখ্যা[- ]+(\d+) ?টি", r"মোট ইউনিয়ন সংখ্যা-(\d+) টি", r"ইউনিয়ন- (\d+)টি", r"ইউনিয়ন 0?(\d+) ?টি",
    r"ইউনিয়নের সংখ্যা মোট (\d+)", r"(\d+)টি ইউনিয়ন পরিষদ", r"0?(\d+)টি ইউনিয়ন", r"ইউনিয়ন পরিষদ (\d+)টি",
    r"উপজেলার (\d+)টি ইউনিয়ন", r"রয়েছে (\d+) টি ইউনিয়ন",
]
WORD_NUM = {"এক": 1, "দুই": 2, "তিন": 3, "চার": 4, "পাঁচ": 5, "ছয়": 6, "সাত": 7, "আট": 8, "নয়": 9, "দশ": 10,
            "এগার": 11, "বার": 12, "তের": 13, "চৌদ্দ": 14}


def stated_union_count(t):
    f = flat(t)
    for rx in STATED_UNION_COUNT:
        m = re.search(rx, f)
        if m:
            return int(m.group(1)), m.group(0)
    m = re.search(r"(এক|দুই|তিন|চার|পাঁচ|ছয়|সাত|আট|নয়|দশ|এগার|বার|তের|চৌদ্দ)টি ইউনিয়ন", f)
    if m:
        return WORD_NUM[m.group(1)], m.group(0)
    return None, ""


# ----------------------------------------------------------------------------- output

AREA_COLS = ["level", "name_en", "name_bn", "parent_level", "parent_name_en", "parent_name_bn", "district_en",
             "upazila_en", "code", "code_scheme", "website", "lat", "lon", "source_key", "source_url", "notes"]
FACT_COLS = ["entity_level", "entity_name_en", "district_en", "upazila_en", "code", "fact", "value", "unit", "basis",
             "year", "source_key", "source_url", "notes"]



# ===========================================================================
# Division mode: generic a2i National Portal collector used by `--division <name>` for divisions other than
# Rajshahi. Identical block in rajshahi_district_portal, division_district_portals, rajshahi_upazila_portals,
# rajshahi_union_portals and rajshahi_divisional_portal fetch.py. Pages are found through the portals' own menus
# and links (no hard-coded page ids); names, counts and figures are parsed from the pages, never typed in.
# English names of districts/upazilas are the project's keys (data/seed), not printed on the pages.
# ===========================================================================
import argparse, csv, hashlib, html, json, os, re, ssl, sys, tempfile, time, unicodedata  # noqa: E401,F811
import concurrent.futures as _dv_cf
import threading as _dv_threading
import urllib.robotparser as _dv_robotparser
from urllib.parse import urljoin, urlparse  # noqa: F811

import requests  # noqa: F811

DV_UA = "Elaka360-data-pipeline (research; contact via repository)"
DV_GAP = 1.2  # seconds between two requests to the same host
DV_AIA = "http://crt.sectigo.com/SectigoPublicServerAuthenticationCADVR36.crt"
DV_AREAS_H = ["level", "name_en", "name_bn", "parent_level", "parent_name_en", "parent_name_bn", "district_en",
              "upazila_en", "code", "code_scheme", "website", "lat", "lon", "source_key", "source_url", "notes"]
DV_FACTS_H = ["entity_level", "entity_name_en", "district_en", "upazila_en", "code", "fact", "value", "unit", "basis",
              "year", "source_key", "source_url", "notes"]

# name_en, name_bn, DC portal host, upazilas [(name_en, name_bn, portal subdomain, other spellings seen on portals)];
# a spelling starting with '~' is an evident misprint (matched, and flagged DOUBT where it is printed)
DV_DIVISIONS = {
    "rangpur": dict(
        code="rang", name_en="Rangpur", name_bn="রংপুর", portal="rangpurdiv.gov.bd", head="Rangpur",
        districts=[
            ("Rangpur", "রংপুর", "rangpur.gov.bd", [
                ("Rangpur Sadar", "রংপুর সদর", "rangpursadar", []), ("Gangachara", "গংগাচড়া", "gangachara", []),
                ("Taragonj", "তারাগঞ্জ", "taragonj", []), ("Badargonj", "বদরগঞ্জ", "badargonj", []),
                ("Mithapukur", "মিঠাপুকুর", "mithapukur", []), ("Pirgonj", "পীরগঞ্জ", "pirgonj", []),
                ("Kaunia", "কাউনিয়া", "kaunia", []), ("Pirgacha", "পীরগাছা", "pirgacha", [])]),
            ("Panchagarh", "পঞ্চগড়", "panchagarh.gov.bd", [
                ("Panchagarh Sadar", "পঞ্চগড় সদর", "panchagarhsadar", []), ("Debiganj", "দেবীগঞ্জ", "debiganj", []),
                ("Boda", "বোদা", "boda", []), ("Atwari", "আটোয়ারী", "atwari", []),
                ("Tetulia", "তেতুলিয়া", "tetulia", [])]),
            ("Dinajpur", "দিনাজপুর", "dinajpur.gov.bd", [
                ("Nawabganj", "নবাবগঞ্জ", "nawabganj", ["~নাবাবগঞ্জ"]), ("Birganj", "বীরগঞ্জ", "birganj", []),
                ("Ghoraghat", "ঘোড়াঘাট", "ghoraghat", []), ("Birampur", "বিরামপুর", "birampur", []),
                ("Parbatipur", "পার্বতীপুর", "parbatipur", []), ("Bochaganj", "বোচাগঞ্জ", "bochaganj", []),
                ("Kaharol", "কাহারোল", "kaharol", []), ("Fulbari", "ফুলবাড়ী", "fulbari", []),
                ("Dinajpur Sadar", "দিনাজপুর সদর", "dinajpursadar", []), ("Hakimpur", "হাকিমপুর", "hakimpur", ["হিলি"]),
                ("Khansama", "খানসামা", "khansama", []), ("Birol", "বিরল", "birol", []),
                ("Chirirbandar", "চিরিরবন্দর", "chirirbandar", [])]),
            ("Lalmonirhat", "লালমনিরহাট", "lalmonirhat.gov.bd", [
                ("Lalmonirhat Sadar", "লালমনিরহাট সদর", "sadar", []), ("Kaliganj", "কালীগঞ্জ", "kaliganj", []),
                ("Hatibandha", "হাতীবান্ধা", "hatibandha", []), ("Patgram", "পাটগ্রাম", "patgram", []),
                ("Aditmari", "আদিতমারী", "aditmari", ["~আতিদমারী"])]),
            ("Nilphamari", "নীলফামারী", "nilphamari.gov.bd", [
                ("Syedpur", "সৈয়দপুর", "syedpur", ["সৈদপুর"]), ("Domar", "ডোমার", "domar", []),
                ("Dimla", "ডিমলা", "dimla", []), ("Jaldhaka", "জলঢাকা", "jaldhaka", []),
                ("Kishorganj", "কিশোরগঞ্জ", "kishorganj", ["কিশোরীগঞ্জ"]),
                ("Nilphamari Sadar", "নীলফামারী সদর", "nilphamarisadar", [])]),
            ("Gaibandha", "গাইবান্ধা", "gaibandha.gov.bd", [
                ("Sadullapur", "সাদুল্লাপুর", "sadullapur", ["সাদুল্যাপুর"]),
                ("Gaibandha Sadar", "গাইবান্ধা সদর", "gaibandhasadar", []),
                ("Palashbari", "পলাশবাড়ী", "palashbari", []), ("Saghata", "সাঘাটা", "saghata", []),
                ("Gobindaganj", "গোবিন্দগঞ্জ", "gobindaganj", []), ("Sundarganj", "সুন্দরগঞ্জ", "sundarganj", []),
                ("Phulchari", "ফুলছড়ি", "phulchari", [])]),
            ("Thakurgaon", "ঠাকুরগাঁও", "thakurgaon.gov.bd", [
                ("Thakurgaon Sadar", "ঠাকুরগাঁও সদর", "thakurgaonsadar", []), ("Pirganj", "পীরগঞ্জ", "pirganj", []),
                ("Ranisankail", "রাণীশংকৈল", "ranisankail", []), ("Haripur", "হরিপুর", "haripur", []),
                ("Baliadangi", "বালিয়াডাঙ্গী", "baliadangi", ["~বালয়িাডাঙ্গী"]),
                ("Ruhia", "রুহিয়া", "ruhia", []), ("Bhulli", "ভূল্লী", "bhulli", [])]),
            ("Kurigram", "কুড়িগ্রাম", "kurigram.gov.bd", [
                ("Kurigram Sadar", "কুড়িগ্রাম সদর", "kurigramsadar", []),
                ("Nageshwari", "নাগেশ্বরী", "nageshwari", []), ("Bhurungamari", "ভুরুঙ্গামারী", "bhurungamari", []),
                ("Phulbari", "ফুলবাড়ী", "phulbari", []), ("Rajarhat", "রাজারহাট", "rajarhat", []),
                ("Ulipur", "উলিপুর", "ulipur", []), ("Chilmari", "চিলমারী", "chilmari", []),
                ("Rowmari", "রৌমারী", "rowmari", []), ("Charrajibpur", "চর রাজিবপুর", "charrajibpur", ["রাজিবপুর"])]),
        ]),
}

# Upazilas listed on the portals in 2026 that the project seed does not have yet: English key is a transliteration
# of the portal subdomain, not printed on the pages.
DV_NEW_UPAZILAS = {("rangpur", "Ruhia"), ("rangpur", "Bhulli")}
DV_BN = "০১২৩৪৫৬৭৮৯"
DV_MONTHS = {"জানুয়ারি": 1, "জানুয়ারী": 1, "ফেব্রুয়ারি": 2, "ফেব্রুয়ারী": 2, "মার্চ": 3, "এপ্রিল": 4, "মে": 5,
             "জুন": 6, "জুলাই": 7, "আগস্ট": 8, "আগষ্ট": 8, "সেপ্টেম্বর": 9, "অক্টোবর": 10, "নভেম্বর": 11,
             "ডিসেম্বর": 12}


def dv_nfc(s):
    return unicodedata.normalize("NFC", s or "")


def dv_asc(s):
    return "".join(str(DV_BN.index(c)) if c in DV_BN else c for c in (s or ""))


class DvFetcher:
    """GET with optional on-disk cache, robots.txt, >= DV_GAP s per host, TLS always verified."""

    def __init__(self, cache=None):
        self.cache = cache
        self.s = requests.Session()
        self.s.headers["User-Agent"] = DV_UA
        self.lock = _dv_threading.Lock()
        self.host_locks, self.last, self.robots = {}, {}, {}
        self.bundle = None
        self.errors = {}
        self.requests = 0

    def _bundle(self):
        with self.lock:
            if self.bundle:
                return self.bundle
            try:
                import certifi
                base = certifi.where()
            except ImportError:
                base = ssl.get_default_verify_paths().cafile or "/etc/ssl/certs/ca-certificates.crt"
            pem = open(base, encoding="utf-8").read()
            r = requests.get(DV_AIA, headers={"User-Agent": DV_UA}, timeout=30)
            r.raise_for_status()
            pem += "\n" + (r.text if r.content.startswith(b"-----BEGIN") else ssl.DER_cert_to_PEM_cert(r.content))
            f = tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False)
            f.write(pem)
            f.close()
            self.bundle = f.name
            return self.bundle

    def _raw(self, url, timeout):
        host = urlparse(url).netloc.lower()
        with self.lock:
            hl = self.host_locks.setdefault(host, _dv_threading.Lock())
        with hl:
            dt = time.time() - self.last.get(host, 0)
            if dt < DV_GAP:
                time.sleep(DV_GAP - dt)
            try:
                self.requests += 1
                return self.s.get(url, timeout=timeout, verify=self._bundle())
            finally:
                self.last[host] = time.time()

    def allowed(self, url):
        p = urlparse(url)
        root = f"{p.scheme}://{p.netloc.lower()}"
        if root not in self.robots:
            rp = _dv_robotparser.RobotFileParser()
            try:
                r = self._raw(root + "/robots.txt", 30)
                rp.parse(r.text.splitlines() if r.status_code == 200 else [])
            except requests.RequestException:
                rp.parse([])
            self.robots[root] = rp
        return self.robots[root].can_fetch(DV_UA, url)

    def get(self, url, timeout=45):
        """Page text, or None (reason in self.errors[url])."""
        key = hashlib.sha1(url.encode()).hexdigest()
        if self.cache:
            p = os.path.join(self.cache, key)
            if os.path.exists(p):
                return open(p, encoding="utf-8", errors="replace").read()
        try:
            if not self.allowed(url):
                self.errors[url] = "robots.txt disallows"
                return None
            r = self._raw(url, timeout)
        except requests.exceptions.SSLError as e:
            self.errors[url] = f"TLS error: {str(e)[:120]}"
            return None
        except requests.RequestException as e:
            self.errors[url] = f"{type(e).__name__}: {str(e)[:120]}"
            return None
        if r.status_code != 200:
            self.errors[url] = f"HTTP {r.status_code}"
            return None
        t = r.content.decode("utf-8", "replace")
        if self.cache:
            os.makedirs(self.cache, exist_ok=True)
            open(os.path.join(self.cache, key), "w", encoding="utf-8").write(t)
        return t


def dv_text(fragment):
    s = re.sub(r"<script.*?</script>|<style.*?</style>", "", fragment, flags=re.S)
    s = re.sub(r"<br\s*/?>|</p>|</tr>|</li>|</h\d>|</div>", "\n", s)
    s = re.sub(r"</td>|</th>", " | ", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("\xa0", " ").replace("‌", "").replace("‍", "")
    return dv_nfc("\n".join(re.sub(r"[ \t]+", " ", l).strip() for l in s.split("\n") if l.strip()))


def dv_date(upd):
    m = re.search(r"([০-৯0-9]{1,2})\s+(\S+),\s*([০-৯0-9]{4})", dv_nfc(upd or ""))
    if not m:
        return ""
    mon = {dv_nfc(k): v for k, v in DV_MONTHS.items()}.get(dv_nfc(m.group(2)))
    d, y = dv_asc(m.group(1)), dv_asc(m.group(3))
    return f"{int(y):04d}-{mon:02d}-{int(d):02d}" if mon else ""


def dv_content(t):
    """Main content block of an a2i portal page: dict(updated, date, title, html, text) or None."""
    if not t:
        return None
    i = t.find('data-widget_name="ContentViewerWidget"')
    if i < 0:
        return None
    seg = t[i:]
    j = seg.find("এই কনটেন্টটি শেয়ার")
    if j > 0:
        seg = seg[:j]
    m = re.search(r'content-update-block">\s*<p>\s*(.*?)</p>', seg, re.S)
    upd = dv_nfc(html.unescape(m.group(1)).strip()) if m else ""
    m = re.search(r"<h2>(.*?)</h2>", seg, re.S)
    title = dv_text(m.group(1)) if m else ""
    seg = re.sub(r'encoded-content="[^"]*"', "", seg)
    seg = seg[seg.find(">") + 1:]
    k = seg.find("</h2>")
    body = seg[k + 5:] if k > 0 else seg
    return dict(updated=upd, date=dv_date(upd), title=title, html=body, text=dv_text(body))


def dv_links(fragment, base=""):
    out = []
    for h, x in re.findall(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', fragment or "", flags=re.S):
        h = html.unescape(h).strip()
        out.append((urljoin(base, h) if base else h, dv_text(x)))
    return out


def dv_site(u):
    """Normalise a website (link or printed domain) to https://host/ ; '' if none."""
    u = (u or "").strip().strip("|").strip().replace("http://http://", "http://").replace("https://http://", "http://")
    if not u or u in ("-", "#"):
        return ""
    p = urlparse(u if "://" in u else "http://" + u)
    host = p.netloc.lower().strip(".")
    return f"https://{host}/" if host and "." in host else ""


def dv_redact(s):
    s = re.sub(r"(?:\+?৮৮|\+?88)?[০0][১1][৩-৯3-9](?:[\s\-]?[০-৯0-9]){8}", "[phone]", s)
    return re.sub(r"[\w.\-]+@[\w.\-]+\.\w+", "[email]", s)


def dv_loose(s):
    """Spelling-tolerant key for matching district/upazila names (never used for output)."""
    s = dv_nfc(s)
    s = re.sub(r"উপজেলা(র)?|পরিষদ|জেলা(র)?|[\s:ঃ\-–.,।()]", "", s)
    for a, b in (("ঁ", ""), ("ী", "ি"), ("ূ", "ু"), ("ণ", "ন"), ("ঙ্গ", "ংগ"), ("ঙ", "ং"), ("ৈ", "ৈ"), ("য়", "য়")):
        s = s.replace(a, b)
    return s


class DvDivision:
    def __init__(self, name):
        if name not in DV_DIVISIONS:
            raise SystemExit(f"unknown division {name!r}; configured: {', '.join(sorted(DV_DIVISIONS))}")
        self.key = name
        self.cfg = c = DV_DIVISIONS[name]
        self.code, self.name_en, self.name_bn, self.head = c["code"], c["name_en"], c["name_bn"], c["head"]
        self.districts = {d: dict(name_en=d, name_bn=bn, host=h, upazilas=u) for d, bn, h, u in c["districts"]}
        self.d_key = {dv_loose(v["name_bn"]): d for d, v in self.districts.items()}
        self.u_key, self.misprints = {}, set()
        for d, v in self.districts.items():
            m = self.u_key[d] = {}
            for en, bn, sub, alt in v["upazilas"]:
                for s in [bn] + alt:
                    m[dv_loose(s.lstrip("~"))] = en
                    if s.startswith("~"):
                        self.misprints.add(dv_nfc(s[1:]))
            sadar = [en for en, bn, _, _ in v["upazilas"] if bn.endswith("সদর")]
            if sadar:
                m[dv_loose("সদর")] = sadar[0]

    def district(self, s):
        return self.d_key.get(dv_loose(s))

    def upazila(self, d, s):
        return self.u_key.get(d, {}).get(dv_loose(s))

    def upz_bn(self, d, en):
        return next((bn for e, bn, _, _ in self.districts[d]["upazilas"] if e == en), "")

    def upz_sub(self, d, en):
        return next((s for e, _, s, _ in self.districts[d]["upazilas"] if e == en), "")


DV_SERIAL = r"^[(.]?(?:[০-৯0-9]{1,4}|[ক-হ])\s*[.।)\]:]*\s*$"
DV_HEADER = r"(নাম|নম্বর|ক্রম|ওয়েবসাইট|লিংক|লিঙ্ক)\s*$|^(জেলা|উপজেলা|ইউনিয়ন|ইউিনয়ন|নং|ক্রমিক)$|^ক্র(মিক|ঃ|:|\.)?\s*(নং|নম্বর)$"
DV_UNION_SUFFIX = r"\s*(ইউ\S{0,5}ন\s*পরিষ\S?|ইউ\S{0,5}ন|উনিয়ন|ইউপি|ইউ\.?\s*পি\.?)\s*[।.,]*\s*$"


DV_PERSON = r"মোঃ|মো:|মো\.|জনাব|মোছাঃ|মোসাঃ|বেগম|আলহাজ্ব|চেয়ারম্যান"


def dv_clean_union(s):
    """'০১। ১ নং চওড়া বড়গাছা ইউনিয়ন' -> ('চওড়া বড়গাছা', '01')."""
    s = dv_nfc(s).strip(" |।,.;:-")
    s = re.sub(r"\s*(https?://)?[\w.-]+\.gov\.bd/?\S*", "", s)              # printed portal address
    s = re.sub(r"\s*[-–]?\s*[A-Za-z][A-Za-z .()'-]*$", "", s)                 # 'ভোমরাদহ ইউপি- Bhomradaha'
    s = s.strip(" |।,.;:-")
    s = re.sub(r"^[(]?[০-৯0-9]{1,3}\s*[.।)]\s*", "", s)              # list serial '০১।'
    no = ""
    m = re.match(r"^([০-৯0-9]{1,2})\s*(?:নং|নম্বর|no\.?|ন(?=\s))\s*(.*)$", s)
    if m:
        no, s = dv_asc(m.group(1)).zfill(2), m.group(2)
    s = re.split(r"\s*[।;,]\s*", s)[0]                          # 'X ইউনিয়ন। এ ইউনিয়নের বিস্তারিত ...'
    s = re.sub(DV_UNION_SUFFIX, "", s)
    s = re.sub(r"\s+ও$", "", s)                                       # last-but-one item of 'a, b ও'
    return re.sub(r"\s+", " ", s).strip(" |।,.;:-"), no


DV_JUNK = (r"(?<![ঀ-৿])(মোট|হলো|হলোঃ|যথা|যথাঃ|শূন্য|ভাড়া)(?![ঀ-৿])|উপজেলা|সমূহ|সমুহ|তালিকা|রয়েছে|নিম্নরূপ|বিস্তারিত|"
           r"উল্লেখ্য|যোগাযোগ|কন্টেন্ট|ডাউনলোড|ফাইল|[()]|"
           r"ইউনিয়েনর নাম|ইউনিয়নের নাম|পরিষদের নাম|এখানে|ক্লিক|অন্তর্ভুক্ত|পৌরসভা|সর্বমোট")


def dv_expand_inline(rows):
    """'... যথাঃ ১ নং ধর্মগড় ২ নং নেকমরদ ... ও ৮ নং নন্দুয়ার' -> one row per item."""
    out = []
    for cells in rows:
        if len(cells) == 1 and len(re.findall(r"[০-৯0-9]{1,2}\s*নং", cells[0][0])) >= 3:
            t = cells[0][0]
            m = re.search(r"([০-৯0-9]+)\s*টি\s*ইউনিয়ন", t)
            if m:
                out.append([(f"{m.group(1)}টি", [])])
            for no, nm in re.findall(r"([০-৯0-9]{1,2})\s*নং\s*(.+?)(?=\s*(?:,|ও)?\s*[০-৯0-9]{1,2}\s*নং|[।]|$)", t):
                out.append([(f"{no} নং {nm}", [])])
        else:
            out.append(cells)
    return out


def dv_rows(c):
    """Rows of a list page: table rows (cells + links) or, without tables, one row per text line."""
    rows = []
    trs = re.findall(r"<tr.*?</tr>", c["html"], flags=re.S)
    if trs:
        for tr in trs:
            cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.S)
            rows.append([(dv_text(x).replace("\n", " ").strip(), dv_links(x)) for x in cells])
    else:
        frag = re.sub(r"<br\s*/?>", "</p><p>", c["html"])
        for blk in re.split(r"</p>|</li>|</div>|</h\d>", frag):
            t = dv_text(blk).replace("\n", " ").strip()
            if t and not re.match(r"^(কন্টেন্ট|কনটেন্টটি)", t):
                rows.append([(t, dv_links(blk))])
    return rows


def dv_union_list(c, div, district=None, upazila=None):
    """Parse a union list page. district/upazila fix the context when the page has no such column.
    Returns (rows, stated) — rows: dict(district_en, upazila_en, upazila_printed, name_bn, printed, no, website);
    stated: {(district_en, upazila_en): (count, printed)} for per-upazila counts printed in the list."""
    out, stated = [], {}
    cur_d, cur_u, cur_u_printed = district, upazila, div.upz_bn(district, upazila) if district and upazila else ""
    for cells in dv_expand_inline(dv_rows(c)):
        texts = [t for t, _ in cells]
        if any(re.search(DV_HEADER, t) for t in texts if t):
            continue
        if len(texts) == 1 and (m := re.search(r"মোট\s*([০-৯0-9]{1,3})\s*টি\s*ইউনিয়ন|([০-৯0-9]{1,3})\s*টি\s*ইউনিয়ন", texts[0])) \
                and cur_u and upazila:
            stated[(cur_d, cur_u)] = (str(int(dv_asc(m.group(1) or m.group(2)))), m.group(0))
        names, site, count = [], "", None
        for t, ls in cells:
            if not t or re.fullmatch(r"[:ঃ\-|–]+", t):
                continue
            if re.fullmatch(DV_SERIAL, t):
                continue
            m = re.fullmatch(r"([০-৯0-9]{1,3})\s*(টি|টি।)?\s*(\(.*\))?", t)
            if m and m.group(2):
                count = (dv_asc(m.group(1)), t)
                continue
            if re.search(r"\.gov\.bd|https?://|www\.", t, re.I) and not re.search(r"[ঀ-৿]", t):
                site = dv_site(t)
                continue
            if not re.search(r"[ঀ-৿]", t) or re.fullmatch(r"[০-৯0-9.,\s()%]+", t):
                continue                                                    # figures in extra columns
            names.append((t, ls))
        if names:
            nd = div.district(names[0][0])
            if nd and (district is None or nd == district) and (len(names) >= 2 or cur_d is None) \
                    and not (nd == cur_d and len(names) == 1):
                if nd != cur_d:
                    cur_d, cur_u = nd, upazila
                names = names[1:]
        if not names or cur_d is None:
            continue
        first = names[0][0]
        fu = div.upazila(cur_d, re.sub(r"\s*উপজেলা.*$", "", first))
        head = fu and (len(names) >= 2 or "উপজেলা" in first or (fu != cur_u and not upazila))
        if head and upazila and "উপজেলা" not in first and (
                dv_nfc(first).strip() not in {dv_nfc(x.lstrip("~")) for e, b, _, al in div.districts[cur_d]["upazilas"]
                                              if e == upazila for x in [b] + al}
                or any(re.search(DV_PERSON, t) for t, _ in names[1:2])):
            head = False                         # a union named like its upazila, followed by other columns
        if head:
            cur_u, cur_u_printed = fu, re.sub(r"\s*উপজেলা.*$", "", dv_nfc(first)).strip(" :ঃ")
            if count:
                stated[(cur_d, cur_u)] = (str(int(count[0])), count[1])
            names = names[1:]
            if not names:
                continue
        elif upazila and "উপজেলা" in first and len(names) == 1:
            continue                                                        # heading / prose on an upazila page
        elif re.search(r"উপজেলা\s*[:ঃ]?$", first) or ("উপজেলা" in first and len(names) == 1) or \
                (len(names) >= 2 and not upazila):
            out.append(dict(warning=f"unknown upazila heading {first!r}"))
            cur_u = None
            continue
        if cur_u is None:
            out.append(dict(warning=f"union before any upazila heading: {first!r}"))
            continue
        printed, ls = names[0] if upazila else names[-1]       # upazila pages: extra columns (chairman, notes) follow
        name, no = dv_clean_union(printed)
        if not name or re.search(DV_JUNK, name) or len(name.split()) > 4:
            continue
        if not site:
            for h, _ in ls:
                if re.search(r"\.gov\.bd", h) and dv_site(h).split("/")[2].split(".")[0] not in ("www",):
                    site = dv_site(h)
        prev = next((r for r in out if r.get("upazila_en") == cur_u and r.get("district_en") == cur_d
                     and r["name_bn"] == name and r["no"] == no), None)
        if prev:
            prev["dup"] = prev.get("dup", 1) + 1
            continue
        out.append(dict(district_en=cur_d, upazila_en=cur_u, upazila_printed=cur_u_printed, name_bn=name,
                        printed=dv_nfc(printed), no=no, website=site))
    return out, stated


def dv_menu(home, base):
    seen, out = set(), []
    for h, x in dv_links(home, base):
        if (h, x) not in seen and x:
            seen.add((h, x))
            out.append((dv_nfc(x).strip(" ■•"), h))
    return out


def dv_pick(menu, include, exclude=None, host=None):
    for x, h in menu:
        if re.search(include, x) and not (exclude and re.search(exclude, x)) and \
                (host is None or urlparse(h).netloc.lower() == host) and "/pages/static-pages/" in h:
            return x, h
    return None


DV_FACT_LABELS = [  # (fact, include regex on label, exclude regex on label, unit)
    ("area_km2", r"আয়তন", r"পৌর|জমি|ভূমি|বন|অবস্থান", "km2"),
    ("population", r"জনসংখ্যা|লোকসংখ্যা|লোক সংখ্যা", r"ঘনত্ব|বৃদ্ধি|হার|পুরুষ|মহিলা|ভোটার|পৌর|শিক্ষিত|উপজাতী|আদিবাসী|ভিত্তিক|পেশা|ধর্ম", "persons"),
    ("upazila_count", r"উপজেলা", r"ভূমি|অফিস|স্বাস্থ্য|দূরত্ব|দুরত্ব|নির্বাহী|পরিষদ|নাম|হেড|সদর|কমপ্লেক্স", "count"),
    ("thana_count", r"থানা", r"নাম|পুলিশ|দূরত্ব|দুরত্ব", "count"),
    ("city_corporation_count", r"সিটি\s*কর্পোরেশন", r"ওয়ার্ড|নাম", "count"),
    ("pourashava_count", r"পৌরসভা|পৌর সভা", r"ওয়ার্ড|মৌজা|নাম|আয়তন|জনসংখ্যা|হোল্ডিং", "count"),
    ("union_count", r"ইউনিয়ন", r"ভূমি|অফিস|ভবন|নাম|ডিজিটাল|তথ্য|কমপ্লেক্স|ওয়ার্ড|দূরত্ব|দুরত্ব|স্বাস্থ্য|কেন্দ্র|কল্যাণ|সাব|ক্লিনিক|উদ্যোক্তা|সচিব|চেয়ারম্যান|সদস্য", "count"),
    ("ward_count", r"ওয়ার্ড|ওয়ার্ড|ওযার্ড|ওয়াড", r"সদস্য|মেম্বার|কাউন্সিলর|নাম|পৌর|নং|ভিত্তিক|সিটি", "count"),
    ("mouza_count", r"মৌজা", r"পৌর|নাম", "count"),
    ("village_count", r"গ্রাম", r"গুচ্ছ|আদর্শ|ভিত্তিক|পৌর|নাম|সংসদ|গ্রামীণ|পুলিশ|চৌকিদার|আশ্রয়|রক্ষা", "count"),
    ("household_count", r"পরিবার সংখ্যা|পরিবারের সংখ্যা|মোট পরিবার|খানার সংখ্যা|খানা সংখ্যা|^\W*খানা\W*$|মোট খানা",
     r"পায়খানা|এতিম|কৃষক|পরিকল্পনা|কল্যাণ|উপজাতি|আদিবাসী", "households"),
]


def dv_number(s, dot_thousands=True, skip_year=False):
    s = dv_asc(s)
    ms = [m.group(0).rstrip(".,") for m in re.finditer(r"\d[\d,\.]*", s)]
    if skip_year:                       # '(২০২২ সালের আদমশুমারি) ১,২৩,৪৫৬' -> skip the year
        while ms and re.fullmatch(r"(19|20)\d\d", ms[0]):
            ms = ms[1:]                 # a lone year is not a figure
    if not ms:
        return "", ""
    raw = ms[0]
    note = ""
    if dot_thousands and re.fullmatch(r"\d{1,3}(\.\d{3})+", raw):
        note, raw = f"'{raw}' read as thousands separator", raw.replace(".", "")
    return raw.replace(",", ""), note


def dv_kv_pairs(c):
    pairs = []
    for cells in dv_rows(c):
        cs = [t.strip(" |") for t, _ in cells]
        cs = [t for t in cs if t and not re.fullmatch(r"[:ঃ=\-–]+", t)]
        while cs and re.fullmatch(DV_SERIAL, cs[0]):
            cs = cs[1:]
        if len(cs) >= 2:
            pairs.append((cs[0], cs[1]))
    for line in c["text"].split("\n"):
        m = re.match(r"^\s*(?:[(]?[০-৯0-9ক-হ]{1,2}\s*[।\.\)]\s*)?([^:ঃ|=]{2,60}?)\s*[:ঃ=]\s*(.+)$", line)
        if m:
            pairs.append((m.group(1).strip(" -•"), m.group(2).strip()))
    return pairs


DV_BOUNDS = {  # plausible ranges per level; counts outside are dropped, areas/populations get a DOUBT note
    "division": dict(area_km2=(1000, 40000), population=(1e6, 1e8), upazila_count=(5, 200), thana_count=(5, 200),
                     union_count=(50, 2000), pourashava_count=(1, 200), mouza_count=(100, 30000),
                     village_count=(100, 40000), city_corporation_count=(0, 10), ward_count=(0, 1e5),
                     household_count=(1e5, 2e7)),
    "district": dict(area_km2=(300, 10000), population=(2e5, 2e7), upazila_count=(2, 20), thana_count=(2, 40),
                     union_count=(10, 250), pourashava_count=(1, 20), mouza_count=(50, 5000), village_count=(50, 10000),
                     household_count=(1e4, 5e6), city_corporation_count=(0, 3)),
    "upazila": dict(area_km2=(10, 1500), population=(5000, 2e6), union_count=(2, 25), pourashava_count=(0, 3),
                    mouza_count=(5, 1000), village_count=(5, 1500), household_count=(1000, 5e5)),
    "union": dict(area_km2=(0.5, 200), population=(1000, 2e5), mouza_count=(1, 150), village_count=(1, 200),
                  ward_count=(3, 15), household_count=(100, 5e4)),
    "pourashava": dict(area_km2=(1, 200), population=(1000, 1e6), ward_count=(3, 30), mouza_count=(1, 100),
                       household_count=(100, 2e5)),
}


def dv_facts(c, wanted=None, div=None, own=(), level=None):
    """Label matcher: [dict(fact, value, unit, year, label, raw, note)], first match per fact. Count labels that name
    a place of the division (e.g. 'পীরগঞ্জ উপজেলা | ১০টি' in a per-upazila table) are skipped."""
    out, seen = [], set()
    places = set()
    if div:
        places = {k for m in div.u_key.values() for k in m if len(k) > 3} | {k for k in div.d_key if len(k) > 3}
        places -= {dv_loose(x) for x in own}
    for label, value in dv_kv_pairs(c):
        lab = re.sub(r"^\s*[(]?[০-৯0-9ক-হ]{1,2}\s*[।\.\)]\s*", "", dv_nfc(label))
        for fact, inc, exc, unit in DV_FACT_LABELS:
            if (wanted and fact not in wanted) or fact in seen or not re.search(inc, lab) or re.search(exc, lab):
                continue
            if len(lab) > 45:
                continue
            v, note = dv_number(value, dot_thousands=(fact != "area_km2"), skip_year=(fact == "population"))
            if not v:
                continue
            y = re.search(r"(?<![\d.,])(19|20)\d\d(?![\d.,])", dv_asc(value))
            year = y.group(0) if y else ""
            if fact == "population" and re.match(r"^\W*(\([কখ]\))?\s*(পুরুষ|নারী|মহিলা)", value) and "মোট" not in value:
                continue
            if fact.endswith("_count") and places and any(p in dv_loose(lab) for p in places):
                continue
            if fact == "population" and re.search(r"মোট\s*(জনসংখ্যা|লোকসংখ্যা)?[\s:ঃ\-–\.]*[০-৯0-9]", value):
                tail = re.split(r"মোট\s*(?:জনসংখ্যা|লোকসংখ্যা)?[\s:ঃ\-–\.]*(?=[০-৯0-9])", value)[-1]
                v, note = dv_number(tail)
                note = (note + "; " if note else "") + "took the figure after 'মোট' (total)"
            u = unit
            if fact == "area_km2":
                after = dv_asc(value)[re.search(r"\d", dv_asc(value)).start():][:40]
                if re.search(r"^[\d,\.\s]*(বর্গ\s*)?মাইল|^[\d,\.\s]*sq\.?\s*mile", after, re.I):
                    u = "sq_miles"
                elif re.search(r"^[\d,\.\s]*(বর্গ\s*)?একর", after):
                    u = "acres"
                elif re.search(r"^[\d,\.\s]*হেক্টর", after):
                    u = "hectares"
                elif not re.search(r"^[\d,\.\s\(\)]*(বর্গ\s*কি|বগ\s*কি|বঃ\s*কি|ব\s*[:\.]\s*কি|ব\.কি|বর্গকি|কিঃ|কি\.\s*মি|কিলো|km|sq\s*km|কিমি)", after, re.I):
                    u = "unstated"
            if u in ("count", "persons", "households"):
                if not re.fullmatch(r"\d+", v):
                    continue
                v = str(int(v))
            if level and fact in DV_BOUNDS.get(level, {}) and not (fact == "area_km2" and u != "km2"):
                lo, hi = DV_BOUNDS[level][fact]
                if not lo <= float(v) <= hi:
                    if u in ("count", "households"):
                        continue                                    # label/value misaligned: drop
                    note = (note + "; " if note else "") + f"DOUBT: {v} is implausible for a {level}"
            elif level and fact not in DV_BOUNDS.get(level, {fact: 0}):
                continue
            seen.add(fact)
            out.append(dict(fact=fact if not (fact == "area_km2" and u != "km2") else "area", value=v, unit=u,
                            year=year, label=lab, raw=dv_nfc(value)[:160], note=note))
    # inline 'উপজেলা ও থানা - ০৮, ... পৌরসভা -৩ (...), ইউনিয়ন-৭৬' inside a longer cell
    for fact, rx in (("upazila_count", r"উপজেলা(?: ও থানা)?"), ("union_count", r"ইউনিয়ন"),
                     ("pourashava_count", r"পৌরসভা"), ("mouza_count", r"মৌজা")):
        if fact in seen or (wanted and fact not in wanted):
            continue
        m = re.search(r"(?<![ঀ-৿])(" + rx + r")\s*[-–]\s*([০-৯0-9]{1,4})(?![০-৯0-9.,])", c["text"])
        if m and level and fact in DV_BOUNDS.get(level, {}) and not \
                DV_BOUNDS[level][fact][0] <= int(dv_asc(m.group(2))) <= DV_BOUNDS[level][fact][1]:
            continue
        if m and (not level or fact in DV_BOUNDS.get(level, {})):
            seen.add(fact)
            out.append(dict(fact=fact, value=str(int(dv_asc(m.group(2)))), unit="count", year="", label=m.group(1),
                            raw=m.group(0), note="inline in a longer cell"))
    return out


def dv_write_csv(path, header, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=header, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in header})


def dv_save_raw(out, name, url, c):
    if not out:
        return
    os.makedirs(os.path.join(out, "raw"), exist_ok=True)
    with open(os.path.join(out, "raw", name), "w", encoding="utf-8") as f:
        f.write(f"URL: {url}\nUPDATED: {c['updated']}\nTITLE: {c['title']}\nACCESSED: {time.strftime('%Y-%m-%d')}\n\n"
                f"{dv_redact(c['text'])}\n")


def dv_manifest(out, template):
    """Write SOURCE.json: template fields (kept from an existing manifest if present) + file checksums."""
    p = os.path.join(out, "SOURCE.json")
    m = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}
    for k, v in template.items():
        if k not in m or k in ("urls", "division", "kind"):
            m[k] = v
    files = {}
    for root, _, fs in os.walk(out):
        for f in sorted(fs):
            rel = os.path.relpath(os.path.join(root, f), out).replace(os.sep, "/")
            if rel in ("SOURCE.json", "fetch.py", "REPORT.md") or "__pycache__" in rel:
                continue
            files[rel] = hashlib.sha256(open(os.path.join(root, f), "rb").read()).hexdigest()
    m["files"] = dict(sorted(files.items()))
    m["accessed"] = time.strftime("%Y-%m-%d")
    order = ["key", "name", "organization", "source_type", "trust_level", "division", "kind", "urls", "accessed",
             "publication_date", "license", "license_url", "attribution", "files", "notes"]
    m = {k: m[k] for k in order if k in m} | {k: v for k, v in m.items() if k not in order}
    with open(p, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)
        f.write("\n")


def dv_upd(c):
    return f"page updated {c['date']}" if c and c.get("date") else "page update date not shown"


# ---------------------------------------------------------------------------------------- district portal
def dv_collect_district(F, div, d, key, log):
    """One DC portal: district row, upazilas, unions, pourashavas, এক নজরে facts. Returns dict of lists."""
    info = div.districts[d]
    base = f"https://{info['host']}/"
    areas, facts, pages = [], [], []
    res = dict(areas=areas, facts=facts, pages=pages, unions=[], stated={}, glance=None, union_url="")

    def page(kind, url):
        c = dv_content(F.get(url))
        pages.append(dict(district_en=d, kind=kind, url=url, status="ok" if c else (F.errors.get(url) or "no content block"),
                          updated=c["date"] if c else "", title=c["title"] if c else ""))
        return c

    home = F.get(base)
    if not home or dv_nfc(info["name_bn"]) not in dv_nfc(re.search(r"<title>(.*?)</title>", home, re.S).group(1) if
                                                       re.search(r"<title>(.*?)</title>", home, re.S) else ""):
        pages.append(dict(district_en=d, kind="home", url=base, status=F.errors.get(base) or "title does not name the district"))
        log(f"{d}: portal {base} unavailable")
        return res
    title = dv_nfc(re.search(r"<title>(.*?)</title>", home, re.S).group(1)).strip()
    pages.append(dict(district_en=d, kind="home", url=base, status="ok", title=title))
    menu = dv_menu(home, base)
    host = info["host"]
    areas.append(dict(level="district", name_en=d, name_bn=info["name_bn"], parent_level="division",
                      parent_name_en=div.name_en, parent_name_bn=div.name_bn, district_en=d, website=base,
                      source_url=base, source_key=key,
                      notes=f"portal title '{title}'; name_en is the project's key (not printed)"))

    # এক নজরে
    g = dv_pick(menu, r"নজরে", r"আশ্রয়|পৌরসভা|প্রকল্প|ভূমি|কৃষি|সদর হাসপাতাল", host)
    if g:
        c = page("glance", g[1])
        if c:
            res["glance"] = (g[1], c)
            for f in dv_facts(c, div=div, level="district"):
                facts.append(dict(entity_level="district", entity_name_en=d, district_en=d, fact=f["fact"],
                                  value=f["value"], unit=f["unit"], basis="as stated", year=f["year"], source_key=key,
                                  source_url=g[1], notes=dv_redact(f"label '{f['label']}' value '{f['raw']}'" +
                                                                   (f"; {f['note']}" if f["note"] else "") + f"; {dv_upd(c)}")))
    # upazilas: rows come from the union list (and the upazila list page where there is one)
    upz = {}
    ul = dv_pick(menu, r"উপজেলার তালিকা|উপজেলা পরিষদের তালিকা|উপজেলা পরিষদসমূহ", r"নির্বাহী|ভূমি", host)
    if ul:
        c = page("upazilas", ul[1])
        if c:
            n = 0
            for cells in dv_rows(c):
                for t, ls in cells:
                    u = div.upazila(d, re.sub(r"^[০-৯0-9]+\s*[.।)]?\s*|\s*উপজেলা.*$", "", t))
                    if u and u not in upz:
                        n += 1
                        site = next((dv_site(h) for h, _ in ls if f".{host}" in h), "")
                        upz[u] = dict(printed=re.sub(r"^[০-৯0-9]+\s*[.।)]?\s*|\s*উপজেলা.*$", "", t).strip(),
                                      website=site, url=ul[1], note=dv_upd(c))
            facts.append(dict(entity_level="district", entity_name_en=d, district_en=d, fact="upazila_count_listed",
                              value=str(n), unit="count", basis="count of upazilas listed", source_key=key,
                              source_url=ul[1], notes=dv_upd(c)))
    # unions
    un = dv_pick(menu, r"ইউনিয়নের তালিকা|ইউনিয়ন পরিষদের তালিকা|উপজেলা ও ইউনিয়ন|ইউনিয়ন পরিষদসমূহ",
                 r"চেয়ারম্যান|সচিব|উদ্যোক্তা|কাজি|জনপ্রতিনিধি|তথ্য ও সেবা", host)
    cands = [un] + [x for x in menu if x != un and re.search(r"উপজেলা ও ইউনিয়ন|ইউনিয়ন পরিষদসমূহ|ইউনিয়নের তালিকা", x[0])
                    and "/pages/" in x[1] and urlparse(x[1]).netloc.lower() == host] if un else []
    best = None
    for x in cands:
        c = page("unions", x[1])
        if not c:
            continue
        rows, stated = dv_union_list(c, div, district=d)
        good = [r for r in rows if "warning" not in r]
        if best is None or len(good) > len(best[1]):
            best = (x[1], good, stated, c, [r["warning"] for r in rows if "warning" in r])
    if best:
        url, rows, stated, c, warns = best
        res.update(unions=rows, stated=stated, union_url=url, union_page=c)
        for w in warns:
            log(f"{d} union list: {w}")
        per = {}
        for r in rows:
            per.setdefault(r["upazila_en"], []).append(r)
            upz.setdefault(r["upazila_en"], dict(printed=r["upazila_printed"], website="", url=url, note=dv_upd(c)))
            areas.append(dict(level="union", name_bn=r["name_bn"], parent_level="upazila", parent_name_en=r["upazila_en"],
                              parent_name_bn=r["upazila_printed"], district_en=d, upazila_en=r["upazila_en"], code=r["no"],
                              code_scheme="UNION_NO_IN_UPAZILA" if r["no"] else "", website=r["website"], source_key=key,
                              source_url=url, notes=f"printed '{r['printed']}'" + (f"; row printed {r['dup']} times on the page"
                              if r.get("dup") else "") + f"; {dv_upd(c)}; English name not printed"))
        for u, rs in per.items():
            note = dv_upd(c)
            dup = [f"{r['name_bn']} ({r['dup']}x)" for r in rs if r.get("dup")]
            if dup:
                note += f"; counted once although printed more than once: {', '.join(dup)}"
            facts.append(dict(entity_level="upazila", entity_name_en=u, district_en=d, upazila_en=u, fact="union_count",
                              value=str(len(rs)), unit="count", basis="count of unions listed", source_key=key,
                              source_url=url, notes=note))
            if (d, u) in stated:
                facts.append(dict(entity_level="upazila", entity_name_en=u, district_en=d, upazila_en=u,
                                  fact="union_count_stated", value=stated[(d, u)][0], unit="count", basis="as stated",
                                  source_key=key, source_url=url, notes=f"printed '{stated[(d, u)][1]}'; {dv_upd(c)}"))
        facts.append(dict(entity_level="district", entity_name_en=d, district_en=d, fact="union_count_listed",
                          value=str(len(rows)), unit="count", basis="count of unions listed", source_key=key,
                          source_url=url, notes=dv_upd(c)))
        m = re.search(r"মোট ইউনিয়ন\s*[:ঃ]?\s*([০-৯0-9]+)|([০-৯0-9]+)\s*টি ইউনিয়ন", c["text"])
        if m:
            facts.append(dict(entity_level="district", entity_name_en=d, district_en=d, fact="union_count",
                              value=str(int(dv_asc(m.group(1) or m.group(2)))), unit="count", basis="as stated",
                              source_key=key, source_url=url, notes=f"printed '{m.group(0)}'; {dv_upd(c)}"))
    else:
        log(f"{d}: no union list page found")
    for u, r in sorted(upz.items()):
        if not r["website"] and div.upz_sub(d, u):
            site = f"https://{div.upz_sub(d, u)}.{host}/"
            t = F.get(site)
            m = re.search(r"<title>(.*?)</title>", t or "", re.S)
            if m and dv_loose(div.upz_bn(d, u)) in dv_loose(m.group(1)) and "উপজেলা" in m.group(1):
                r["website"] = site
                r["note"] += f"; website not linked from the list, verified by fetching it (title '{dv_nfc(m.group(1)).strip()}')"
        if (div.key, u) in DV_NEW_UPAZILAS:
            r["note"] += "; upazila not in the project seed yet; name_en transliterated from the portal subdomain"
        areas.append(dict(level="upazila", name_en=u, name_bn=r["printed"], parent_level="district", parent_name_en=d,
                          parent_name_bn=info["name_bn"], district_en=d, upazila_en=u, website=r["website"],
                          source_key=key, source_url=r["url"],
                          notes=f"{r['note']}; name_en is the project's key (not printed)"))

    # pourashavas: list page, menu links named '<x> পৌরসভা', এক নজরে text
    poura = {}

    def add_p(printed, url, note, site=""):
        nm = dv_nfc(printed).strip(" |।,.")
        nm = re.sub(r"^[০-৯0-9]+\s*[.।)]?\s*", "", nm)
        nm = re.sub(r"\s*(পৌরসভার ওয়েবসাইট|এর ওয়েবসাইট|ওয়েবসাইট)$", "", nm)
        if not nm or re.search(r"তালিকা|সংখ্যা|নাম$|এক নজরে|একনজরে", nm):
            return 0
        full = nm if nm.endswith("পৌরসভা") else nm + " পৌরসভা"
        if full not in poura:
            poura[full] = dict(printed=nm, url=url, notes=[note], website=site)
        else:
            poura[full]["notes"].append(note)
            poura[full]["website"] = poura[full]["website"] or site
        return 1

    pl = dv_pick(menu, r"পৌরসভার তালিকা|পৌরসভা সমূহ|পৌরসভাসমূহ", None, host)
    if pl:
        c = page("pourashavas", pl[1])
        if c:
            n = 0
            for cells in dv_rows(c):
                nm, site = "", ""
                for t, ls in cells:
                    if not t or re.fullmatch(DV_SERIAL, t) or re.search(DV_HEADER, t) or t in ("-", "–"):
                        continue
                    if re.search(r"\.gov\.bd|https?://|\.com|www\.", t) and not re.search(r"[ঀ-৿]", t):
                        site = dv_site(t)
                    elif not nm and re.search(r"[ঀ-৿]", t):
                        nm = t
                        site = site or next((dv_site(h) for h, _ in ls if re.search(r"pourashava|paurashava|pourosova|municipality|ps\.", h, re.I)), "")
                if nm and not re.search(r"পৌরসভার তালিকা|জেলার", nm):
                    n += add_p(nm, pl[1], f"listed on '{c['title']}' ({dv_upd(c)})", site)
            facts.append(dict(entity_level="district", entity_name_en=d, district_en=d, fact="pourashava_count_listed",
                              value=str(n), unit="count", basis="count of pourashavas listed", source_key=key,
                              source_url=pl[1], notes=dv_upd(c)))
    for x, h in menu:
        if re.fullmatch(r"[ঀ-৿ ]+ পৌরসভা(র ওয়েবসাইট)?", x) and h.startswith("http") \
                and urlparse(h).netloc.lower() != host:
            if "/pages/" in h:
                add_p(x, base, f"menu link '{x}' on the district portal points to {h}")
            else:
                add_p(x, base, f"menu link '{x}' on the district portal", dv_site(h))
    if res["glance"]:
        gu, c = res["glance"]
        m = re.search(r"পৌরসভা\s*[-–:ঃ]?\s*([০-৯0-9]+)\s*(?:টি)?\s*\(([^)]*)\)", c["text"])
        if m:
            for nm in re.split(r",|\s+এবং\s+|\s+ও\s+", m.group(2)):
                nm = nm.strip()
                if nm and re.fullmatch(r"[ঀ-৿ ]+", nm):
                    add_p(nm, gu, f"named in এক নজরে ('{m.group(0)}', {dv_upd(c)})")
    for full, p in poura.items():
        base_nm = re.sub(r"\s*পৌরসভা$", "", full)
        u = div.upazila(d, base_nm) or div.upazila(d, base_nm + " সদর")
        if not u and dv_loose(base_nm) == dv_loose(info["name_bn"]):
            u = div.upazila(d, "সদর")
        note = "; ".join(dict.fromkeys(p["notes"]))
        note += "; parent upazila inferred from the same-named upazila" if u else "; parent upazila not stated"
        if p["printed"] != full:
            note += f"; printed '{p['printed']}'"
        areas.append(dict(level="pourashava", name_bn=full, parent_level="upazila" if u else "district",
                          parent_name_en=u or d, parent_name_bn=div.upz_bn(d, u) if u else info["name_bn"], district_en=d,
                          upazila_en=u or "", website=p["website"], source_key=key, source_url=p["url"], notes=note))
    res["pourashavas"] = list(poura)
    return res


# ---------------------------------------------------------------------------------------- divisional portal
def dv_collect_division(F, div, key, log):
    """Divisional Commissioner portal: district list, upazila list, union list, এক নজরে facts."""
    base = f"https://{div.cfg['portal']}/"
    areas, facts, pages = [], [], []
    res = dict(areas=areas, facts=facts, pages=pages, unions=[], upazilas={}, districts=[], raw={})

    def page(kind, url):
        c = dv_content(F.get(url))
        pages.append(dict(kind=kind, url=url, status="ok" if c else (F.errors.get(url) or "no content block"),
                          updated=c["date"] if c else "", title=c["title"] if c else ""))
        if c:
            res["raw"][kind] = (url, c)
        return c

    home = F.get(base)
    m = re.search(r"<title>(.*?)</title>", home or "", re.S)
    if not m or dv_nfc(div.name_bn) not in dv_nfc(m.group(1)):
        log(f"divisional portal {base} unavailable: {F.errors.get(base)}")
        pages.append(dict(kind="home", url=base, status=F.errors.get(base) or "title does not name the division"))
        return res
    pages.append(dict(kind="home", url=base, status="ok", title=dv_nfc(m.group(1)).strip()))
    menu = dv_menu(home, base)
    host = div.cfg["portal"]
    g = dv_pick(menu, r"নজরে", r"আশ্রয়|প্রকল্প", host)
    if g and (c := page("glance", g[1])):
        for f in dv_facts(c, div=div, level="division"):
            facts.append(dict(entity_level="division", entity_name_en=div.name_en, fact=f["fact"], value=f["value"],
                              unit=f["unit"], basis="as stated", year=f["year"], source_key=key, source_url=g[1],
                              notes=f"label '{f['label']}' value '{f['raw']}'" + (f"; {f['note']}" if f["note"] else "")
                              + f"; {dv_upd(c)}"))
    dl = dv_pick(menu, r"জেলার তালিকা|জেলাসমূহ|জেলা সমূহ", None, host)
    if dl and (c := page("districts", dl[1])):
        for cells in dv_rows(c):
            for t, _ in cells:
                d = div.district(re.sub(r"^[০-৯0-9]+\s*[.।)]?\s*|\s*জেলা$", "", t))
                if d and d not in res["districts"]:
                    res["districts"].append(d)
                    areas.append(dict(level="district", name_en=d, name_bn=dv_nfc(t).strip(), parent_level="division",
                                      parent_name_en=div.name_en, parent_name_bn=div.name_bn, district_en=d,
                                      code=str(len(res["districts"])).zfill(2), code_scheme=f"{div.code.upper()}DIV_LIST_SERIAL",
                                      website=f"https://{div.districts[d]['host']}/", source_key=key, source_url=dl[1],
                                      notes=f"{dv_upd(c)}; name_en is the project's key (not printed); website is the DC "
                                            f"portal (not linked from this page)"))
        facts.append(dict(entity_level="division", entity_name_en=div.name_en, fact="district_count_listed",
                          value=str(len(res["districts"])), unit="count", basis="count of districts listed",
                          source_key=key, source_url=dl[1], notes=dv_upd(c)))
    ul = dv_pick(menu, r"উপজেলার তালিকা|উপজেলাসমূহ|উপজেলা সমূহ", None, host)
    if ul and (c := page("upazilas", ul[1])):
        cur_d, n = None, 0
        for cells in dv_rows(c):
            names = [t for t, _ in cells if t and not re.fullmatch(DV_SERIAL, t) and not re.search(DV_HEADER, t)]
            if not names:
                continue
            if len(names) >= 2 and div.district(names[0]):
                cur_d, names = div.district(names[0]), names[1:]
            elif cur_d is None and div.district(names[0]):
                cur_d, names = div.district(names[0]), names[1:]
            serial = next((dv_asc(t).strip(" .।") for t, _ in cells if re.fullmatch(DV_SERIAL, t or "x")), "")
            for t in names:
                u = div.upazila(cur_d, t) if cur_d else None
                if not u:
                    log(f"divisional upazila list: unknown upazila {t!r} (district {cur_d})")
                    continue
                n += 1
                res["upazilas"][(cur_d, u)] = t
                areas.append(dict(level="upazila", name_en=u, name_bn=dv_nfc(t), parent_level="district",
                                  parent_name_en=cur_d, parent_name_bn=div.districts[cur_d]["name_bn"], district_en=cur_d,
                                  upazila_en=u, code=serial.zfill(2), code_scheme=f"{div.code.upper()}DIV_LIST_SERIAL",
                                  source_key=key, source_url=ul[1],
                                  notes=f"{dv_upd(c)}; name_en is the project's key (not printed)"
                                        + ("; DOUBT: printed spelling looks like a misprint" if dv_nfc(t) in div.misprints
                                           else "")))
        m = re.search(r"মোট\s*([০-৯0-9]+)\s*টি", c["text"])
        facts.append(dict(entity_level="division", entity_name_en=div.name_en, fact="upazila_count_listed", value=str(n),
                          unit="count", basis="count of upazilas listed", source_key=key, source_url=ul[1], notes=dv_upd(c)))
        if m:
            facts.append(dict(entity_level="division", entity_name_en=div.name_en, fact="upazila_count",
                              value=str(int(dv_asc(m.group(1)))), unit="count", basis="as stated", source_key=key,
                              source_url=ul[1], notes=f"printed '{m.group(0)}' in the list heading; {dv_upd(c)}"))
    nl = dv_pick(menu, r"ইউনিয়নের তালিকা|ইউনিয়নসমূহ|ইউনিয়ন সমূহ", None, host)
    if nl and (c := page("unions", nl[1])):
        rows, stated = dv_union_list(c, div)
        for r in rows:
            if "warning" in r:
                log(f"divisional union list: {r['warning']}")
        rows = [r for r in rows if "warning" not in r]
        res["unions"] = rows
        per = {}
        for r in rows:
            per.setdefault((r["district_en"], r["upazila_en"]), []).append(r)
            note = f"printed '{r['printed']}'; upazila printed '{r['upazila_printed']}'"
            if r.get("dup"):
                note += f"; row printed {r['dup']} times"
            areas.append(dict(level="union", name_bn=r["name_bn"], parent_level="upazila", parent_name_en=r["upazila_en"],
                              parent_name_bn=r["upazila_printed"], district_en=r["district_en"], upazila_en=r["upazila_en"],
                              code=r["no"], code_scheme="UNION_NO_IN_UPAZILA" if r["no"] else "", website=r["website"],
                              source_key=key, source_url=nl[1], notes=f"{note}; {dv_upd(c)}; English name not printed"))
        for (d, u), rs in sorted(per.items()):
            facts.append(dict(entity_level="upazila", entity_name_en=u, district_en=d, upazila_en=u, fact="union_count",
                              value=str(len(rs)), unit="count", basis="count of unions listed", source_key=key,
                              source_url=nl[1], notes=dv_upd(c)))
        facts.append(dict(entity_level="division", entity_name_en=div.name_en, fact="union_count_listed",
                          value=str(len(rows)), unit="count", basis="count of unions listed", source_key=key,
                          source_url=nl[1], notes=dv_upd(c)))
        m = re.search(r"তালিকা\s*[:ঃ]\s*([০-৯0-9]+)\s*টি", c["text"])
        if m:
            facts.append(dict(entity_level="division", entity_name_en=div.name_en, fact="union_count",
                              value=str(int(dv_asc(m.group(1)))), unit="count", basis="as stated", source_key=key,
                              source_url=nl[1], notes=f"printed '{m.group(0)}' in the list heading; {dv_upd(c)}"))
    return res


# ---------------------------------------------------------------------------------------- upazila portals
DV_UNION_MENU_EX = r"কমিটি|বাল্যবিবাহ|শ্রমিক|ইজিপিপি|কর্মসূচ|তথ্য ও সেবা|চেয়ারম্যান|সচিব|উদ্যোক্তা|কাজি|জনপ্রতিনিধি|ভূমি|ডিজিটাল|কার্যালয়|সদস্য|নির্বাচন|বাজেট|প্রকল্প|হট ?লাইন"


def dv_title(t):
    m = re.search(r"<title>(.*?)</title>", t or "", re.S)
    return dv_nfc(html.unescape(m.group(1))).strip() if m else ""


def dv_collect_upazila(F, div, d, u, key, out, site=None):
    """One upazila portal: union list, এক নজরে facts, pourashava pages."""
    host_d = div.districts[d]["host"]
    site = site or (f"https://{div.upz_sub(d, u)}.{host_d}/" if div.upz_sub(d, u) else "")
    u_bn = div.upz_bn(d, u)
    res = dict(areas=[], facts=[], pages=[], unions=[], log=[], site=site, ok=False)
    if not site:
        res["pages"].append(dict(district_en=d, upazila_en=u, kind="home", url="", status="no portal address known"))
        return res
    home = F.get(site)
    title = dv_title(home)
    if not home or dv_loose(u_bn) not in dv_loose(title):
        res["pages"].append(dict(district_en=d, upazila_en=u, kind="home", url=site,
                                 status=F.errors.get(site) or f"title '{title}' does not name the upazila"))
        return res
    res["ok"] = True
    res["pages"].append(dict(district_en=d, upazila_en=u, kind="home", url=site, status="ok", title=title))
    host = urlparse(site).netloc.lower()
    menu = dv_menu(home, site)
    sub = host.split(".")[0]

    def page(kind, url):
        c = dv_content(F.get(url))
        res["pages"].append(dict(district_en=d, upazila_en=u, kind=kind, url=url,
                                 status="ok" if c else (F.errors.get(url) or "no content block"),
                                 updated=c["date"] if c else "", title=c["title"] if c else ""))
        if c:
            dv_save_raw(out, f"{d.lower()}_{sub}_{kind}.txt", url, c)
        return c

    def fact(level, name, f, url, c, extra=""):
        res["facts"].append(dict(entity_level=level, entity_name_en=name, district_en=d, upazila_en=u, fact=f["fact"],
                                 value=f["value"], unit=f["unit"], basis="as stated", year=f["year"], source_key=key,
                                 source_url=url, notes=dv_redact(f"{extra}label '{f['label']}' value '{f['raw']}'" +
                                                                 (f"; {f['note']}" if f["note"] else "") + f"; {dv_upd(c)}")))

    un = dv_pick(menu, r"ইউনিয়ন\s*(সমূহ|সমুহ|পরিষদ\s*সমূহ|পরিষদসমূহ|তালিকা|এর তালিকা|পরিষদের তালিকা)|ইউনিয়নসমূহ",
                 DV_UNION_MENU_EX, host) or dv_pick(menu, r"ইউনিয়ন", DV_UNION_MENU_EX, host)
    if un and (c := page("unions", un[1])):
        rows, stated = dv_union_list(c, div, district=d, upazila=u)
        res["log"] += [f"{d}/{u}: {r['warning']}" for r in rows if "warning" in r]
        rows = [r for r in rows if "warning" not in r and r["upazila_en"] == u]
        res["unions"] = rows
        for r in rows:
            res["areas"].append(dict(level="union", name_bn=r["name_bn"], parent_level="upazila", parent_name_en=u,
                                     parent_name_bn=u_bn, district_en=d, upazila_en=u, code=r["no"],
                                     code_scheme="UNION_NO_IN_UPAZILA" if r["no"] else "", website=r["website"],
                                     source_key=key, source_url=un[1],
                                     notes=f"printed '{r['printed']}'" + (f"; row printed {r['dup']} times" if r.get("dup") else "")
                                     + f"; {dv_upd(c)}; English name not printed"))
        res["facts"].append(dict(entity_level="upazila", entity_name_en=u, district_en=d, upazila_en=u, fact="union_count",
                                 value=str(len(rows)), unit="count", basis="count of unions listed", source_key=key,
                                 source_url=un[1], notes=f"unions listed on '{c['title']}'; {dv_upd(c)}"))
        if not rows:
            res["log"].append(f"{d}/{u}: no union rows parsed from {un[1]}")
    else:
        res["log"].append(f"{d}/{u}: no union list menu item")
    g = dv_pick(menu, r"নজরে", r"আশ্রয়|পৌরসভা|প্রকল্প|ভূমি|ইউনিয়ন", host)
    if g and (c := page("glance", g[1])):
        for f in dv_facts(c, div=div, own=[u_bn] + [a.lstrip("~") for e, b, _, al in div.districts[d]["upazilas"]
                                                     if e == u for a in al], level="upazila"):
            fact("upazila", u, f, g[1], c)
    poura = {}                                  # name -> area row
    for x, h in menu:
        m = re.fullmatch(r"(?:এক ?নজরে\s*)?([ঀ-৿]+(?: [ঀ-৿]+)?)?\s*পৌরসভা(?:র ওয়েবসাইট| কার্যালয়| পোর্টাল| ওয়েবসাইট)?", x)
        if not m:
            continue
        p_host = urlparse(h).netloc.lower()
        nm = m.group(1)
        if p_host == host and "/pages/static-pages/" in h:
            c = page("poura", h)
            if not c:
                continue
            if not nm:                                   # 'এক নজরে পৌরসভা': name from the page title / text
                cands = [x for x in re.findall(r"([ঀ-৿]+) পৌরসভা(?![ঀ-৿])", c["text"][:600])
                         if not re.match(r"নজর|এক|একনজর|শ্রেণী|উক্ত|এই|প্রথম|মোট|নং", x)] if "নজরে" in c["title"] else []
                nm = cands[0] if cands else ""
            if not nm:
                res["log"].append(f"{d}/{u}: pourashava page without a name: {h}")
                continue
            nm = dv_nfc(nm) + " পৌরসভা"
            row = poura.setdefault(nm, dict(level="pourashava", name_bn=nm, parent_level="upazila", parent_name_en=u,
                                            parent_name_bn=u_bn, district_en=d, upazila_en=u, website="", source_key=key,
                                            source_url=h, notes=""))
            row["source_url"] = h
            row["notes"] = f"menu item '{x}' on the {u_bn} upazila portal; {dv_upd(c)}" + row["notes"]
            for f in dv_facts(c, level="pourashava"):
                fact("pourashava", nm, f, h, c, "entity_name_en holds the Bangla name (no English on page); ")
        elif nm and h.startswith("http") and p_host != host and "/pages/" not in h:
            nm = dv_nfc(nm) + " পৌরসভা"
            row = poura.setdefault(nm, dict(level="pourashava", name_bn=nm, parent_level="upazila", parent_name_en=u,
                                            parent_name_bn=u_bn, district_en=d, upazila_en=u, website="", source_key=key,
                                            source_url=site, notes=""))
            row["website"] = row["website"] or dv_site(h)
            row["notes"] += f"; website from menu link '{x}'"
    for row in poura.values():
        row["notes"] = row["notes"].lstrip("; ")
        res["areas"].append(row)
    return res


# ---------------------------------------------------------------------------------------- union portals
DV_UNION_FACTS = {"area_km2", "population", "mouza_count", "village_count", "ward_count", "household_count"}


def dv_collect_union(F, div, u, key, out):
    """One union portal: menu item 'এক নজরে' -> facts. u: dict(district_en, upazila_en, name_bn, no, website, list_url)."""
    row = dict(district_en=u["district_en"], upazila_en=u["upazila_en"], union_no=u["no"], union_bn=u["name_bn"],
               portal=u["website"], list_url=u.get("list_url", ""))
    facts = []
    if not u["website"]:
        return dict(row, status="no portal link found"), facts
    home = F.get(u["website"])
    if not home:
        return dict(row, status=f"portal error: {F.errors.get(u['website'])}"), facts
    title = dv_title(home)
    row["portal_title"] = title
    check = "" if dv_loose(u["name_bn"])[:4] in dv_loose(title) else f"; portal title '{title}' does not repeat the union name"
    host = urlparse(u["website"]).netloc.lower()
    cands = [(x, h) for x, h in dv_menu(home, u["website"])
             if "নজরে" in x and "ভূমি" not in x and "/pages/" in h and urlparse(h).netloc.lower() == host]
    if not cands:
        return dict(row, status="no এক নজরে menu item" + check), facts
    url = cands[0][1]
    c = dv_content(F.get(url))
    if not c or len(c["text"]) < 80:
        return dict(row, url=url, status=("page error: " + F.errors[url]) if url in F.errors else "empty page"), facts
    dv_save_raw(out, f"{host.split('.')[0]}_glance.txt", url, c)
    got = dv_facts(c, wanted=DV_UNION_FACTS, level="union")
    for f in got:
        facts.append(dict(entity_level="union", entity_name_en="", district_en=u["district_en"], upazila_en=u["upazila_en"],
                          code=u["no"], fact=f["fact"], value=f["value"], unit=f["unit"], basis="as stated", year=f["year"],
                          source_key=key, source_url=url,
                          notes=dv_redact(f"union {u['name_bn']}" + (f" (no. {u['no']})" if u["no"] else "") +
                                          f"; label '{f['label']}' value '{f['raw']}'" + (f"; {f['note']}" if f["note"] else "")
                                          + check + f"; {dv_upd(c)}")))
    return dict(row, url=url, status="ok" + check, updated=c["date"], title=c["title"], facts=len(got)), facts


def dv_parallel(fn, items, workers=6):
    with _dv_cf.ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(fn, items))


# ---------------------------------------------------------------------------------------- runners
DV_YEAR = "2026"  # collection campaign in the source keys (Rajshahi keys carry 2026 too)
DV_KINDS = {  # kind: (Rajshahi folder, folder/key pattern for other divisions)
    "district_portal_main": ("rajshahi_district_portal", "{div}_district_portal", "{DIV}_DC_PORTAL_{Y}"),
    "district_portals": ("division_district_portals", "division_district_portals_{div}", "{CODE}DIV_DISTRICT_PORTALS_{Y}"),
    "upazila_portals": ("rajshahi_upazila_portals", "{div}_upazila_portals", "{DIV}_UPAZILA_PORTALS_{Y}"),
    "union_portals": ("rajshahi_union_portals", "{div}_union_portals", "{DIV}_UNION_PORTALS_{Y}"),
    "divisional_portal": ("rajshahi_divisional_portal", "{div}_divisional_portal", "{CODE}DIV_PORTAL_{Y}"),
}


def dv_names(kind, div):
    _, folder, key = DV_KINDS[kind]
    f = dict(div=div.key, DIV=div.key.upper(), CODE=div.code.upper(), Y=DV_YEAR)
    return folder.format(**f), key.format(**f)


def dv_template(kind, div, key, urls):
    head = div.head
    hb = div.districts[head]["name_bn"]
    others = [d for d in div.districts if d != head]
    t = {
        "district_portal_main": (
            f"{head} District Administration portal — upazila/union list, pourashavas, district at-a-glance",
            f"Office of the Deputy Commissioner, {head} (Government of Bangladesh, a2i National Portal)",
            f"{hb} জেলা প্রশাসন, জাতীয় তথ্য বাতায়ন ({div.districts[head]['host']})"),
        "district_portals": (
            f"District administration portals — {', '.join(others)}",
            "Deputy Commissioner's offices, Government of Bangladesh (a2i National Portal)",
            f"জেলা প্রশাসন, {div.name_bn} বিভাগ — জাতীয় তথ্য বাতায়ন (<district>.gov.bd)"),
        "upazila_portals": (
            f"Upazila Administration portals of {div.name_en} Division — union lists, এক নজরে, pourashava pages",
            f"Upazila Nirbahi Officers' offices, {div.name_en} Division (Government of Bangladesh, a2i National Portal)",
            f"উপজেলা প্রশাসন, {div.name_bn} বিভাগ — জাতীয় তথ্য বাতায়ন (<upazila>.<district>.gov.bd)"),
        "union_portals": (
            f"Union Parishad portals of {div.name_en} Division — এক নজরে (at-a-glance) pages",
            f"Union Parishads of {div.name_en} Division (Government of Bangladesh, a2i National Portal)",
            f"ইউনিয়ন পরিষদ পোর্টাল, {div.name_bn} বিভাগ — জাতীয় তথ্য বাতায়ন (<union>.<district>.gov.bd)"),
        "divisional_portal": (
            f"{div.name_en} Divisional Commissioner portal ({div.cfg['portal']})",
            f"Office of the Divisional Commissioner, {div.name_en}",
            f"Office of the Divisional Commissioner, {div.name_en} ({div.cfg['portal']}), Bangladesh National Portal"),
    }[kind]
    return {"key": key, "name": t[0], "organization": t[1], "source_type": "government_portal", "trust_level": 4,
            "division": div.key, "kind": kind, "urls": urls, "publication_date": None, "license": None,
            "license_url": None, "attribution": t[2],
            "notes": "Collected by the generic division mode of the a2i portal collectors (pages found through the "
                     "portals' menus, names and figures parsed from the pages). No licence stated; only facts (names, "
                     "counts, figures) are extracted. English district/upazila names are the project's keys, not printed."}


def dv_pages_csv(out, pages, cols=("district_en", "upazila_en", "kind", "url", "status", "updated", "title")):
    seen, rows = set(), []
    for p in pages:
        k = (p.get("kind"), p.get("url"))
        if k not in seen:
            seen.add(k)
            rows.append(p)
    dv_write_csv(os.path.join(out, "raw", "pages.csv"), list(cols), rows)


def dv_save_district_raw(out, r, prefix):
    if r.get("glance"):
        dv_save_raw(out, f"{prefix}_glance.txt", r["glance"][0], r["glance"][1])
    if r.get("union_page"):
        dv_save_raw(out, f"{prefix}_unions.txt", r["union_url"], r["union_page"])


def dv_run(kind, division, out=None, cache=None, here="."):
    div = DvDivision(division)
    folder, key = dv_names(kind, div)
    out = os.path.abspath(out or os.path.join(os.path.dirname(os.path.abspath(here)), folder))
    os.makedirs(os.path.join(out, "raw"), exist_ok=True)
    F = DvFetcher(cache)
    logs = []
    log = lambda m: (logs.append(m), print("WARNING:", m, file=sys.stderr))
    areas, facts, pages, urls = [], [], [], []
    t0 = time.time()
    if kind in ("district_portal_main", "district_portals"):
        ds = [div.head] if kind == "district_portal_main" else [d for d in div.districts if d != div.head]
        for d in ds:
            r = dv_collect_district(F, div, d, key, log)
            areas += r["areas"]
            facts += r["facts"]
            pages += r["pages"]
            urls += [p["url"] for p in r["pages"] if p["status"] == "ok"]
            dv_save_district_raw(out, r, d.lower())
            for p in r["pages"]:
                if p["status"] == "ok" and p["kind"] in ("upazilas", "pourashavas"):
                    c = dv_content(F.get(p["url"]))
                    dv_save_raw(out, f"{d.lower()}_{p['kind']}.txt", p["url"], c)
        dv_pages_csv(out, pages)
    elif kind == "upazila_portals":
        items = [(d, u) for d in div.districts for u, *_ in div.districts[d]["upazilas"]]
        rs = dv_parallel(lambda x: dv_collect_upazila(F, div, x[0], x[1], key, out), items, 6)
        for r in rs:
            areas += r["areas"]
            facts += r["facts"]
            pages += r["pages"]
            for m in r["log"]:
                log(m)
            urls += [r["site"]] if r["ok"] else []
        dv_pages_csv(out, pages)
    elif kind == "union_portals":
        unions = []
        for d in div.districts:
            r = dv_collect_district(F, div, d, key, log)
            urls += [r["union_url"]] if r["union_url"] else []
            for u in r["unions"]:
                unions.append(dict(u, list_url=r["union_url"]))
        missing = sorted({(u["district_en"], u["upazila_en"]) for u in unions if not u["website"]})
        if missing:   # look for the portal links on the upazila portals' union pages
            rs = dv_parallel(lambda x: dv_collect_upazila(F, div, x[0], x[1], key, None), missing, 6)
            for (d, up), r in zip(missing, rs):
                sites = {dv_loose(x["name_bn"]): x["website"] for x in r["unions"] if x["website"]}
                for u in unions:
                    if u["district_en"] == d and u["upazila_en"] == up and not u["website"]:
                        w = sites.get(dv_loose(u["name_bn"]))
                        if w:
                            u["website"], u["site_from"] = w, next(p["url"] for p in r["pages"] if p["kind"] == "unions")
        rs = dv_parallel(lambda u: dv_collect_union(F, div, u, key, out), unions, 8)
        cov = []
        for u, (row, fs) in zip(unions, rs):
            if u.get("site_from"):
                row["portal_link_from"] = u["site_from"]
            cov.append(row)
            facts += fs
            # one area row per union in the DC portal list; website only when the portal answered
            st = row["status"]
            reached = st.startswith(("ok", "no এক নজরে", "empty page")) and "Site is not available" not in st
            note = f"printed '{u['printed']}' on the district union list"
            if u["website"] and reached:
                note += "; portal reached" + (f" (title '{row.get('portal_title', '')}')" if row.get("portal_title") else "")
                if u.get("site_from"):
                    note += f"; portal link from {u['site_from']}"
            elif u["website"]:
                note += f"; portal {u['website']} not usable ({st.split(';')[0]})"
            else:
                note += "; no portal link found on the district or upazila portal"
            if "does not repeat" in st:
                note += "; DOUBT: " + st.split("; ", 1)[1]
            areas.append(dict(level="union", name_bn=u["name_bn"], parent_level="upazila", parent_name_en=u["upazila_en"],
                              parent_name_bn=u["upazila_printed"], district_en=u["district_en"],
                              upazila_en=u["upazila_en"], code=u["no"],
                              code_scheme="UNION_NO_IN_UPAZILA" if u["no"] else "",
                              website=u["website"] if reached else "", source_key=key,
                              source_url=row.get("url") or u.get("list_url", ""),
                              notes=note + "; English name not printed"))
        dv_write_csv(os.path.join(out, "raw", "coverage.csv"),
                     ["district_en", "upazila_en", "union_no", "union_bn", "portal", "portal_link_from", "portal_title",
                      "list_url", "url", "status", "updated", "title", "facts"], cov)
        pages = cov
    elif kind == "divisional_portal":
        r = dv_collect_division(F, div, key, log)
        areas, facts, pages = r["areas"], r["facts"], r["pages"]
        urls = [p["url"] for p in pages if p["status"] == "ok"]
        for k, (u, c) in r["raw"].items():
            dv_save_raw(out, f"{k}.txt", u, c)
        dv_write_csv(os.path.join(out, "raw", "pages.csv"), ["kind", "url", "status", "updated", "title"], pages)
    else:
        raise SystemExit(f"unknown kind {kind}")
    dv_write_csv(os.path.join(out, "areas.csv"), DV_AREAS_H, areas)
    dv_write_csv(os.path.join(out, "facts.csv"), DV_FACTS_H, facts)
    if logs:
        with open(os.path.join(out, "raw", "warnings.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(logs) + "\n")
    dv_manifest(out, dv_template(kind, div, key, list(dict.fromkeys(urls))))
    lv = {}
    for a in areas:
        lv[a["level"]] = lv.get(a["level"], 0) + 1
    print(f"{kind} {division} -> {out}: areas {lv}, facts {len(facts)}, pages {len(pages)}, "
          f"requests {F.requests}, failed {len(F.errors)}, {time.time() - t0:.0f}s")
    return out



def main_rajshahi(a):
    tmp = None
    cache = a.cache
    if not cache:
        tmp = tempfile.mkdtemp(prefix="rajdiv_portals_")
        cache = tmp
    F = Fetcher(cache)
    areas, facts, pages = [], [], []

    def page(url):
        raw = F.get(url)
        if raw is None:
            pages.append(dict(url=url, updated="", status="blocked: " + F.errors.get(url, "?")))
            return None
        c = content(raw)
        if not c:
            pages.append(dict(url=url, updated="", status="no content widget"))
            return None
        pages.append(dict(url=url, updated=c["updated_iso"], status="ok", title=c["title"]))
        return c

    def upd_note(c):
        return f"page updated {c['updated_iso']}" if c and c["updated_iso"] else "page update date not shown"

    def fact(level, name_en, d, u, f, v, unit, basis, year, url, note):
        facts.append(dict(entity_level=level, entity_name_en=name_en, district_en=d, upazila_en=u, code="", fact=f,
                          value=v, unit=unit, basis=basis, year=year, source_key=SOURCE_KEY, source_url=url,
                          notes=note))

    def area(level, name_bn, name_en, parent_level, p_en, p_bn, d, u, website, url, note):
        areas.append(dict(level=level, name_en=name_en, name_bn=name_bn, parent_level=parent_level,
                          parent_name_en=p_en, parent_name_bn=p_bn, district_en=d, upazila_en=u, code="",
                          code_scheme="", website=website, lat="", lon="", source_key=SOURCE_KEY, source_url=url,
                          notes=note))

    district_unions = {}
    upazila_rows = {}  # (district, upazila_en) -> dict
    for d, roles in DISTRICT_PAGES.items():
        host = "https://" + DIST_HOST[d]
        cg = page(host + roles["glance"])
        area("district", DIST_BN[d], d, "division", "Rajshahi", "রাজশাহী", d, "", host + "/", host + roles["glance"],
             upd_note(cg))
        if cg:
            ft = flat(cg["text"])
            for f, rx, unit, basis, year, note in GLANCE[d]:
                m = re.search(rx, ft)
                if not m:
                    print(f"WARN {d} glance: {f} not found", file=sys.stderr)
                    continue
                fact("district", d, d, "", f, m.group(1).lstrip("0") or "0", unit, basis, year, host + roles["glance"],
                     "; ".join(x for x in (note, upd_note(cg)) if x))
        for (dd, role, f, rx, unit, note) in GEO_EXTRA:
            if dd == d and role in roles:
                cgeo = page(host + roles[role])
                m = re.search(rx, flat(cgeo["text"])) if cgeo else None
                if m:
                    fact("district", d, d, "", f, m.group(1), unit, "as stated", "", host + roles[role],
                         f"{note}; {upd_note(cgeo)}")
        # upazila list
        ups = []
        if "upazilas" in roles:
            cu = page(host + roles["upazilas"])
            if cu:
                if d == "Bogura":
                    for h, x in links(cu["html"]):
                        if upz_en(d, x):
                            ups.append((clean_name(x), h))
                elif d == "Joypurhat":
                    tk = tokens(cu["text"])
                    for i, t in enumerate(tk):
                        if upz_en(d, t):
                            w = next((x for x in tk[i:i + 4] if x.endswith(".joypurhat.gov.bd")), "")
                            ups.append((t, "http://" + w + "/" if w else ""))
                else:
                    for t in tokens(cu["text"]):
                        nm = clean_name(re.sub(r"^[০-৯]+[.।]?\s*", "", t))
                        nm = re.sub(r"\s*উপজেলা পরিষদ.*$", "", nm)
                        if upz_en(d, nm):
                            ups.append((nm, ""))
                fact("district", d, d, "", "upazila_count_listed", str(len(ups)), "count", "count of listed upazilas",
                     "", host + roles["upazilas"], upd_note(cu))
                for nm, w in ups:
                    upazila_rows[(d, upz_en(d, nm))] = dict(name_bn=nm, website=w, url=host + roles["upazilas"],
                                                            note=upd_note(cu))
        # union list
        if "unions" in roles:
            cn = page(host + roles["unions"])
            if cn:
                rows = DISTRICT_PARSERS[d](cn)
                district_unions[d] = (rows, host + roles["unions"], cn)
                if d == "Natore":
                    for l in cn["text"].split("\n"):
                        m = re.match(r"^(\S.*?) - (https?://\S+)$", l)
                        if m and upz_en(d, clean_name(m.group(1))):
                            upazila_rows.setdefault((d, upz_en(d, clean_name(m.group(1)))), dict(
                                name_bn=clean_name(m.group(1)), website=m.group(2), url=host + roles["unions"],
                                note=upd_note(cn)))
                if d == "Chapainawabganj":
                    for h, x in links(cn["html"]):
                        if upz_en(d, x) and ".chapainawabganj.gov.bd" in h and "up." not in h:
                            upazila_rows.setdefault((d, upz_en(d, x)), dict(name_bn=clean_name(x), website=h,
                                                                             url=host + roles["unions"],
                                                                             note=upd_note(cn)))
                for r in rows:
                    upazila_rows.setdefault((d, upz_en(d, r["upazila_bn"])), dict(
                        name_bn=r["upazila_bn"], website="", url=host + roles["unions"], note=upd_note(cn)))
        if d == "Pabna":
            for (dd, u_bn, url, kind, primary) in UPAZILA_UNION_PAGES:
                if dd == d:
                    upazila_rows.setdefault((d, upz_en(d, u_bn)), dict(
                        name_bn=u_bn, website="https://" + urlparse(url).netloc + "/", url=url,
                        note="upazila listed from upazila portal (district portal has no upazila/union list)"))

    # ---- upazila rows
    for (d, u_en), r in sorted(upazila_rows.items()):
        note = r["note"]
        if d == "Bogura" and u_en == "Mokamtala":
            note += "; new upazila listed on the district portal (not in seed)"
        area("upazila", r["name_bn"], u_en, "district", d, DIST_BN[d], d, u_en, r["website"], r["url"], note)

    # ---- unions from district lists
    for d, (rows, url, cn) in district_unions.items():
        per = {}
        for r in rows:
            u_en = upz_en(d, r["upazila_bn"])
            if not u_en:
                print(f"WARN {d}: unknown upazila {r['upazila_bn']!r}", file=sys.stderr)
            per.setdefault(u_en, []).append(r)
            note = [upd_note(cn), f"list serial {r['serial']}"]
            if r.get("upazila_en_src"):
                note.append(f"page upazila label: {r['upazila_bn']} ({r['upazila_en_src']})")
            area("union", r["name_bn"], r.get("name_en", ""), "upazila", u_en, r["upazila_bn"], d, u_en,
                 r.get("website", ""), url, "; ".join(note))
        for u_en, rs in per.items():
            note = upd_note(cn)
            ser = sorted(int(r["serial"]) for r in rs if r["serial"].isdigit())
            gaps = [n for n in range(1, (ser[-1] if ser else 0) + 1) if n not in ser] if d != "Bogura" else []
            if gaps:
                note += f"; list serial(s) {', '.join(map(str, gaps))} blank/missing on the page"
            fact("upazila", u_en, d, u_en, "union_count", str(len(rs)), "count", "count of unions listed", "", url, note)
        fact("district", d, d, "", "union_count_listed", str(len(rows)), "count", "count of unions listed", "", url,
             upd_note(cn))

    # ---- upazila union pages
    for (d, u_bn, url, kind, primary) in UPAZILA_UNION_PAGES:
        c = page(url)
        u_en = upz_en(d, u_bn)
        if not c:
            continue
        rows = UPZ_PARSERS[kind](c)
        n_stated, phrase = stated_union_count(c["text"])
        if rows:
            fact("upazila", u_en, d, u_en, "union_count", str(len(rows)), "count", "count of unions listed (upazila portal)",
                 "", url, upd_note(c))
        if n_stated is not None:
            fact("upazila", u_en, d, u_en, "union_count_stated", str(n_stated), "count", "as stated (upazila portal)", "",
                 url, upd_note(c))
        if primary:
            for r in rows:
                note = [upd_note(c), "from upazila portal"]
                if r.get("union_no"):
                    note.append(f"union no {r['union_no']}")
                if r.get("serial"):
                    note.append(f"list serial {r['serial']}")
                area("union", r["name_bn"], r.get("name_en", ""), "upazila", u_en, u_bn, d, u_en, r.get("website", ""),
                     url, "; ".join(note))
        else:
            names = ", ".join(r["name_bn"] for r in rows)
            pages[-1]["names"] = names

    for (d, u_bn, url) in UPAZILA_GLANCE_PAGES:
        c = page(url)
        if not c:
            continue
        u_en = upz_en(d, u_bn)
        n, phrase = stated_union_count(c["text"])
        if n is not None:
            fact("upazila", u_en, d, u_en, "union_count_stated", str(n), "count", "as stated (upazila এক নজরে page)", "",
                 url, upd_note(c))
        m = re.search(r"পৌরসভা[- ]*0?(\d+) ?টি|(\d+)টি পৌরসভা|(একটি) পৌরসভা", flat(c["text"]))
        if m:
            v = next(x for x in m.groups() if x)
            fact("upazila", u_en, d, u_en, "pourashava_count_stated", "1" if v == "একটি" else str(int(v)), "count",
                 "as stated (upazila এক নজরে page)", "", url, upd_note(c))
        if d == "Bogura" and u_en == "Mokamtala":
            f = flat(c["text"])
            m = re.search(r"অন্তর্ভুক্ত ইউনিয়নগুলোর মধ্যে রয়েছে (.+?)।", f)
            if m:
                names = [clean_name(x) for x in re.split(r",| এবং ", m.group(1).replace(" ইউনিয়ন", ""))]
                pages[-1]["names"] = ", ".join(n for n in names if n)
                fact("upazila", u_en, d, u_en, "union_count", str(len([n for n in names if n])), "count",
                     "count of unions named in prose (upazila এক নজরে page)", "", url,
                     upd_note(c) + "; page says NICAR approved May 2026 and gazette published (no gazette ref given)")

    # ---- pourashavas
    def parent_by_name(d, nm):
        base = nm.replace(" পৌরসভা", "").strip()
        for bn, en in UPZ_EN[d].items():
            if bn == base or bn == base + " সদর":
                return bn, en
        return "", ""

    def add_pourashava(d, nm_bn, u_bn, u_en, url, note):
        nm = nm_bn if nm_bn.endswith("পৌরসভা") else nm_bn + " পৌরসভা"
        area("pourashava", nm, "", "upazila" if u_en else "district", u_en or d, u_bn or DIST_BN[d], d, u_en, "", url,
             note)
        return nm

    seen_p = set()
    for d, roles in DISTRICT_PAGES.items():
        host = "https://" + DIST_HOST[d]
        if d == "Natore":
            c = page(host + roles["glance"])
            m = re.search(r"পৌরসভা \| ([^|]+)\|", c["text"]) if c else None
            for nm, cls in re.findall(r"([ঀ-৿]+) \(([কখগ])-শ্রেণী\)", m.group(1) if m else ""):
                ub, ue = parent_by_name(d, nm)
                note = f"listed as '{nm}' under পৌরসভা on এক নজরে; class {cls}; {upd_note(c)}"
                note += "; parent inferred from same-named upazila" if ue else "; parent upazila not stated on district page"
                seen_p.add((d, add_pourashava(d, nm, ub, ue, host + roles["glance"], note)))
                fact("pourashava", nm + " পৌরসভা", d, ue, "pourashava_class", cls, "class", "as stated", "",
                     host + roles["glance"], upd_note(c))
        if d == "Naogaon":
            c = page(host + roles["glance"])
            if c:
                m = re.search(r"পৌরসভা রয়েছে।[^\n]*\n((?:.*পৌরসভা\n?)+)", c["text"])
                for nm in re.findall(r"^([ঀ-৿]+ পৌরসভা)$", m.group(1) if m else "", re.M):
                    ub, ue = parent_by_name(d, nm)
                    note = f"named in এক নজরে prose; {upd_note(c)}"
                    note += "; parent inferred from same-named upazila" if ue else "; parent upazila not stated"
                    seen_p.add((d, add_pourashava(d, nm, ub, ue, host + roles["glance"], note)))
        if d == "Chapainawabganj":
            c = page(host + roles["glance"])
            m = re.search(r"পৌরসভা \| ০?৪ টি \((.+?)\)", c["text"]) if c else None
            if m:
                for nm in re.split(r",\s*|\s*ও\s*", m.group(1).replace("পৌরসভা", "").replace("ওনাচোল", "ও নাচোল")):
                    nm = clean_name(nm)
                    if not nm:
                        continue
                    ub, ue = parent_by_name(d, nm)
                    note = f"listed in এক নজরে; {upd_note(c)}"
                    note += "; parent inferred from same-named upazila" if ue else "; parent upazila not stated"
                    seen_p.add((d, add_pourashava(d, nm, ub, ue, host + roles["glance"], note)))
        if "pourashavas" in roles:
            c = page(host + roles["pourashavas"])
            if c:
                names = re.findall(r"([ঀ-৿]+ পৌরসভা)", c["text"])
                for nm in names:
                    if nm.startswith("জেলার"):
                        continue
                    ub, ue = parent_by_name(d, nm)
                    note = upd_note(c) + ("; parent inferred from same-named upazila" if ue else "; parent not stated")
                    seen_p.add((d, add_pourashava(d, nm, ub, ue, host + roles["pourashavas"], note)))
                fact("district", d, d, "", "pourashava_count_listed",
                     str(len([n for n in names if not n.startswith("জেলার")])), "count", "count of listed pourashavas",
                     "", host + roles["pourashavas"], upd_note(c))

    for (d, u_bn, url, rx_n, rx_w, rx_c) in POURASHAVA_PAGES:
        c = page(url)
        if not c:
            continue
        t = re.sub(r"[\s|]+", " ", c["title"] + " " + c["text"])
        m = re.search(rx_n, t)
        if not m:
            print(f"WARN pourashava name not found {url}", file=sys.stderr)
            continue
        nm = m.group(1) if m.group(1).endswith("পৌরসভা") else m.group(1) + " পৌরসভা"
        u_en = upz_en(d, u_bn)
        prev = next((r for r in areas if r["level"] == "pourashava" and r["district_en"] == d and r["name_bn"] == nm), None)
        if prev is not None and prev["parent_level"] == "district":
            prev.update(parent_level="upazila", parent_name_en=u_en, parent_name_bn=u_bn, upazila_en=u_en)
            prev["notes"] += f"; parent upazila from {urlparse(url).netloc} pourashava page ({upd_note(c)})"
        if (d, nm) not in seen_p:
            seen_p.add((d, add_pourashava(d, nm, u_bn, u_en, url,
                                          f"from upazila portal ({urlparse(url).netloc}); {upd_note(c)}")))
        if rx_w:
            mw = re.search(rx_w, asc(t))
            if mw:
                fact("pourashava", nm, d, u_en, "wards_count", str(int(mw.group(1))), "count", "as stated (upazila portal)",
                     "", url, upd_note(c) + "; entity_name_en holds the Bangla name (no English on page)")
        if rx_c:
            mc = re.search(rx_c, t)
            if mc:
                fact("pourashava", nm, d, u_en, "pourashava_class", mc.group(1), "class", "as stated (upazila portal)",
                     "", url, upd_note(c))

    # ---- write
    def write(name, cols, rows):
        with open(os.path.join(HERE, name), "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in cols})

    write("areas.csv", AREA_COLS, areas)
    write("facts.csv", FACT_COLS, facts)
    os.makedirs(os.path.join(HERE, "raw"), exist_ok=True)
    seen, plist = set(), []
    for p in pages:
        if p["url"] not in seen:
            seen.add(p["url"])
            plist.append(p)
    write("raw/pages.csv", ["url", "updated", "status", "title", "names"], plist)
    print(f"areas={len(areas)} facts={len(facts)} pages={len(plist)} blocked={sum(1 for p in plist if p['status'] != 'ok')}")
    if F.bundle:
        os.unlink(F.bundle)
    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)


KIND = "district_portals"


def main():
    global HERE
    ap = argparse.ArgumentParser(description="Other district DC portals collector")
    ap.add_argument("--division", default="rajshahi", help="division to collect (default rajshahi)")
    ap.add_argument("--out", help="output folder (default: this folder for rajshahi, the division's own folder otherwise)")
    ap.add_argument("--cache", default=None, help="reuse/keep downloaded pages in this folder")
    a = ap.parse_args()
    if a.division != "rajshahi":
        dv_run(KIND, a.division, a.out, a.cache, HERE)
        return
    if a.out and os.path.abspath(a.out) != HERE:
        out = os.path.abspath(a.out)
        os.makedirs(out, exist_ok=True)
        if not os.path.exists(os.path.join(out, "SOURCE.json")):
            with open(os.path.join(HERE, "SOURCE.json"), encoding="utf-8") as f, \
                    open(os.path.join(out, "SOURCE.json"), "w", encoding="utf-8") as g:
                g.write(f.read())
        HERE = out
    main_rajshahi(a)


if __name__ == "__main__":
    main()
