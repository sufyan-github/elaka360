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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default=None)
    a = ap.parse_args()
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


if __name__ == "__main__":
    main()
