#!/usr/bin/env python3
"""Transport and tourism lists of government agencies (BIWTA, Ministry of Shipping, city corporations, Parjatan, MoCAT,
Tourism Board, Forest Department), split by division.

Usage:
  python3 fetch.py [--division rajshahi|rangpur|dhaka|chattogram|khulna|barishal|sylhet|mymensingh] [--out DIR]
  python3 fetch.py --all-divisions            # fetch every national list once, write all 8 division folders
  options: --only biwta_river_ports,…  (subset of lists)   --http-cache DIR (development: reuse raw HTTP responses)

Keys TRANSPORT_TOURISM_<CODE>_2026 in folders transport_tourism_<code>_2026 (DIVISIONS.md), kind "transport_tourism",
source_type government_portal, trust level 4. Each row names its agency and list in extra_json.organisation / .list.
Requires poppler's `pdftotext` for the two BIWTA PDFs. Descriptions are never copied; no staff names or personal numbers.
"""
# --- polite HTTP helper (stdlib + requests only) -----------------------------------------------------------------
# Several hosts send only their leaf certificate. Like a browser, we fetch the missing intermediates from the CAs'
# published AIA URLs and add them to certifi's bundle. TLS verification stays ON everywhere.
import os, re, time, tempfile, urllib.parse
import requests

UA = "Elaka360-data-pipeline (research; contact via repository)"
INTERMEDIATES = [
    "http://crt.sectigo.com/SectigoPublicServerAuthenticationCADVR36.crt",   # bdbl/kb/pkb.gov.bd, teletalk
    "http://crt.sectigo.com/SectigoPublicServerAuthenticationCAOVR36.crt",
    "http://secure.globalsign.com/cacert/gsrsaovsslca2018.crt",              # rakub.org.bd
    "http://cacerts.geotrust.com/GeoTrustTLSRSACAG1.crt",                    # krishibank.gov.bd
    "http://cacerts.rapidssl.com/RapidSSLTLSRSACAG1.crt",                    # ers.pallisanchaybank.gov.bd
]
MIN_DELAY = 1.2

_last, _robots, _bundle = {}, {}, None
S = requests.Session()
S.headers["User-Agent"] = UA
HTTP_CACHE = None     # development only (--http-cache)


def _der_to_pem(der):
    import base64
    b = base64.encodebytes(der).decode().replace("\n", "")
    return "-----BEGIN CERTIFICATE-----\n" + "\n".join(b[i:i + 64] for i in range(0, len(b), 64)) + "\n-----END CERTIFICATE-----\n"


def ca_bundle():
    global _bundle
    if _bundle:
        return _bundle
    import certifi
    pems = [open(certifi.where(), encoding="utf-8").read()]
    for u in INTERMEDIATES:
        try:
            r = requests.get(u, timeout=30, headers={"User-Agent": UA})
            if r.ok:
                pems.append(r.content.decode() if r.content.startswith(b"-----") else _der_to_pem(r.content))
        except requests.RequestException:
            pass
        time.sleep(0.3)
    fd, path = tempfile.mkstemp(suffix=".pem")
    with os.fdopen(fd, "w") as f:
        f.write("\n".join(pems))
    _bundle = path
    return path


def _wait(url):
    host = urllib.parse.urlsplit(url).netloc
    w = MIN_DELAY - (time.time() - _last.get(host, 0))
    if w > 0:
        time.sleep(w)
    return host


def _robots_rules(text):
    """RFC 9309: the rules of the group for our product token, else of the '*' group. [(allow, pattern)]"""
    groups, cur, in_rules = [], None, False
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        k, v = [x.strip() for x in line.split(":", 1)]
        k = k.lower()
        if k == "user-agent":
            if cur is None or in_rules:
                cur = {"agents": [], "rules": []}
                groups.append(cur)
                in_rules = False
            cur["agents"].append(v.lower())
        elif k in ("allow", "disallow") and cur is not None:
            in_rules = True
            if v:
                cur["rules"].append((k == "allow", v))
    mine = [g for g in groups if any(a != "*" and a in UA.lower() for a in g["agents"])]
    star = [g for g in groups if "*" in g["agents"]]
    return [r for g in (mine or star) for r in g["rules"]]


def _robots_match(pattern, path):
    rx = "".join(".*" if ch == "*" else ("$" if ch == "$" and i == len(pattern) - 1 else re.escape(ch)) for i, ch in enumerate(pattern))
    return re.match(rx, path) is not None


def allowed(url):
    """robots.txt check with RFC 9309 semantics (longest matching rule wins; Allow wins a tie)."""
    p = urllib.parse.urlsplit(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        rules = []
        try:
            host = _wait(base)
            r = S.get(base + "/robots.txt", timeout=30, verify=ca_bundle())
            _last[host] = time.time()
            ok = r.status_code == 200 and "html" not in r.headers.get("content-type", "") and "<html" not in r.text[:500].lower()
            rules = _robots_rules(r.text) if ok else []
        except Exception:
            rules = []
        _robots[base] = rules
    path = (p.path or "/") + ("?" + p.query if p.query else "")
    best = None
    for allow, pat in _robots[base]:
        if _robots_match(pat, path) and (best is None or len(pat) > len(best[1]) or (len(pat) == len(best[1]) and allow)):
            best = (allow, pat)
    return best is None or best[0]


class _Cached:
    def __init__(self, status, content, ctype, url):
        self.status_code, self.content, self.url = status, content, url
        self.headers = {"content-type": ctype}
        self.ok = status < 400

    @property
    def text(self):
        return self.content.decode("utf-8", "replace")

    def json(self):
        import json as _j
        return _j.loads(self.content.decode("utf-8-sig"))


def http(method, url, retries=2, **kw):
    """Polite request (robots.txt, ≥1.2 s per host, UA); returns a Response or raises RuntimeError."""
    full = requests.Request(method, url, params=kw.get("params")).prepare().url
    if not allowed(full):
        raise RuntimeError("robots.txt disallows " + full)
    ck = None
    if HTTP_CACHE:
        import hashlib, pickle
        ck = os.path.join(HTTP_CACHE, hashlib.sha1(repr((method, url, kw.get("data"), kw.get("json"), kw.get("params"),
                                                             kw.get("files"))).encode()).hexdigest())
        if os.path.exists(ck):
            with open(ck, "rb") as f:
                return _Cached(*pickle.load(f))
    kw.setdefault("timeout", 120)
    kw.setdefault("verify", ca_bundle())
    err = None
    for i in range(retries + 1):
        host = _wait(url)
        try:
            r = S.request(method, url, **kw)
            if r.status_code < 500:
                if ck and r.ok:
                    import pickle
                    with open(ck, "wb") as f:
                        pickle.dump((r.status_code, r.content, r.headers.get("content-type", ""), r.url), f)
                return r
            err = f"HTTP {r.status_code}"
        except requests.RequestException as e:
            err = f"{type(e).__name__}: {str(e)[:200]}"
        finally:
            _last[host] = time.time()
        time.sleep(5 * (i + 1))
    raise RuntimeError(f"{method} {url} failed: {err}")


def get(url, **kw):
    r = http("GET", url, **kw)
    if not r.ok:
        raise RuntimeError(f"GET {url}: HTTP {r.status_code}")
    return r


def post(url, **kw):
    r = http("POST", url, **kw)
    if not r.ok:
        raise RuntimeError(f"POST {url}: HTTP {r.status_code}")
    return r
# --- end helper ----------------------------------------------------------------------------------------------------

import argparse, csv, datetime, hashlib, html as _html, json, re, sys, traceback, unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PLACE_COLS = ["source_key", "source_id", "name_bn", "name_en", "category_key", "lat", "lon", "address", "district_en",
              "upazila_en", "phone", "website", "email", "opening_hours", "operator", "ownership", "extra_json",
              "source_url", "notes"]
_BN = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def nfc(s):
    return unicodedata.normalize("NFC", s or "")


def asc(s):
    return (s or "").translate(_BN)


def txt(s):
    """HTML fragment -> one line of text."""
    s = re.sub(r"(?is)<br\s*/?>|</p>|</div>|</li>", " ", s or "")
    s = _html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\xa0", " ").replace("‌", "").replace("﻿", "")
    return nfc(re.sub(r"\s+", " ", s).strip(" ,"))


def lines(s):
    """HTML fragment -> list of non-empty text lines."""
    s = re.sub(r"(?is)<br\s*/?>|</p>|</div>|</li>|</h\d>", "\n", s or "")
    s = _html.unescape(re.sub(r"<[^>]+>", "", s)).replace("\xa0", " ")
    return [nfc(re.sub(r"[ \t]+", " ", x).strip()) for x in s.splitlines() if x.strip()]


def strip_noise(page):
    return re.sub(r"(?is)<!--.*?-->|<script\b.*?</script>|<style\b.*?</style>", "", page)


def trs(fragment):
    return re.findall(r"(?is)<tr\b[^>]*>(.*?)</tr>", fragment)


def tds(tr, tag="td"):
    return re.findall(r"(?is)<%s\b[^>]*>(.*?)</%s>" % (tag, tag), tr)


def table_by_id(page, tid):
    m = re.search(r'(?is)<table[^>]*id="%s".*?</table>' % re.escape(tid), page)
    return m.group(0) if m else ""


def tables_with_header(page, first):
    """[(header, [row cells…])] of each <table> whose first header cell equals `first` (comments stripped)."""
    out = []
    for tb in re.findall(r"(?is)<table.*?</table>", strip_noise(page)):
        rows = trs(tb)
        if not rows:
            continue
        head = [txt(c) for c in re.findall(r"(?is)<t[hd]\b[^>]*>(.*?)</t[hd]>", rows[0])]
        if head[:1] == [first]:
            out.append((head, rows[1:]))
    return out


def fnum(v):
    try:
        x = float(re.sub(r"[^\d.\-]", "", str(v))) if v not in (None, "") else None
    except ValueError:
        return None
    return x


def xj(d):
    d = {k: v for k, v in d.items() if v not in (None, "", [], {})}
    return json.dumps(d, ensure_ascii=False, separators=(",", ":"), sort_keys=True) if d else ""


MOBILE = re.compile(r"(?:\+?88)?0?1[3-9]\d{2}[-\s]?\d{3}[-\s]?\d{3}")


def phones(s, keep_mobiles=True):
    """ASCII phone list '; '-joined. Labels such as 'Phone:' are dropped; mobiles dropped when keep_mobiles=False."""
    s = asc(s or "")
    s = re.sub(r"\(\s*(\+?\d{2,6})\s*\)\s*", r" \1-", s)        # '(0821) 716127' -> '0821-716127'
    s = re.sub(r"(?i)\b(phone|tel|telephone|mobile|mob|cell|fax|ip phone|hotline|ext|pabx|t&t)\b\.?\s*(no\.?)?\s*[:#.\-]?", " ", s)
    s = re.sub(r"(?u)[^\d+\-,;/()\s]", " ", s)
    out = []
    for p in re.split(r"[,;/]|\s{2,}", s):
        p = re.sub(r"\s+", " ", p).strip(" -()")
        d = re.sub(r"\D", "", p)
        if len(d) < 5:
            continue
        if not keep_mobiles and re.match(r"(88)?01[3-9]", d):
            continue
        if p not in out:
            out.append(p)
    return "; ".join(out)


def emails(s):
    found = []
    for e in re.findall(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", s or ""):
        e = e.strip(".").lower()
        if e not in found:
            found.append(e)
    return "; ".join(found)


def sid_hash(*parts):
    return hashlib.sha1("|".join(nfc(p or "").lower() for p in parts).encode("utf-8")).hexdigest()[:12]


# ---------------------------------------------------------------- gazetteer (seed districts / upazilas / polygons)
DIVISIONS = {"rajshahi": "raj", "rangpur": "rang", "dhaka": "dhk", "chattogram": "ctg", "khulna": "khl",
             "barishal": "bar", "sylhet": "syl", "mymensingh": "mym"}
EN_ALIASES = {  # spelling -> seed district name_en (keys compared by skeleton())
    "Chittagong": "Chattogram", "Chattagram": "Chattogram", "Ctg": "Chattogram", "Chottogram": "Chattogram",
    "Jessore": "Jashore", "Jasore": "Jashore", "Barisal": "Barishal", "Borishal": "Barishal",
    "Chapai Nawabganj": "Chapainawabganj", "Chapai Nawabgonj": "Chapainawabganj", "Chapai Nababganj": "Chapainawabganj",
    "Chapainababganj": "Chapainawabganj", "C.Nawabganj": "Chapainawabganj", "C Nawabganj": "Chapainawabganj",
    "Ch.Nawabganj": "Chapainawabganj", "Chapai": "Chapainawabganj", "Laksmipur": "Lakshmipur", "Gaibanda": "Gaibandha",
    "Jhalakati": "Jhalokathi", "Jhalokati": "Jhalokathi", "Jhalakathi": "Jhalokathi", "Jhalkathi": "Jhalokathi",
    "Laxmipur": "Lakshmipur", "Lakhsmipur": "Lakshmipur", "Lakhmipur": "Lakshmipur", "Luxmipur": "Lakshmipur",
    "B.Baria": "Brahmanbaria", "B Baria": "Brahmanbaria", "Bbaria": "Brahmanbaria", "Bramhanbaria": "Brahmanbaria",
    "Brahmanbaria": "Brahmanbaria", "Brahmonbaria": "Brahmanbaria",
    "Narshingdi": "Narsingdi", "Narsindi": "Narsingdi", "Norsingdi": "Narsingdi",
    "Panchagar": "Panchagarh", "Panchagor": "Panchagarh", "Panchghar": "Panchagarh",
    "Mymensing": "Mymensingh", "Moymonsingh": "Mymensingh", "Maymansingh": "Mymensingh",
    "Kustia": "Kushtia", "Kustiya": "Kushtia", "Kishorgonj": "Kishoreganj",
    "Netrakona": "Netrokona", "Netrokuna": "Netrokona", "Khagrachari": "Khagrachhari", "Khagrachori": "Khagrachhari",
    "Coxsbazar": "Cox's Bazar", "Cox Bazar": "Cox's Bazar", "Coxs Bazar": "Cox's Bazar",
    "Moulvibazar": "Moulvibazar", "Maulvibazar": "Moulvibazar", "Moulovibazar": "Moulvibazar", "Moulavibazar": "Moulvibazar",
    "Habigonj": "Habiganj", "Hobigonj": "Habiganj", "Hobiganj": "Habiganj",
    "Sirajgonj": "Sirajganj", "Shirajganj": "Sirajganj", "Gopalgonj": "Gopalganj", "Munshigonj": "Munshiganj",
    "Narayangonj": "Narayanganj", "Naraynganj": "Narayanganj", "N.Ganj": "Narayanganj",
    "Rangamati": "Rangamati", "Rangamaty": "Rangamati", "Bandarbon": "Bandarban",
    "Joypurhat": "Joypurhat", "Jaipurhat": "Joypurhat", "Thakurgaon": "Thakurgaon", "Thakurgao": "Thakurgaon",
    "Nilphamary": "Nilphamari", "Lalmonirhat": "Lalmonirhat", "Sunamgonj": "Sunamganj", "Manikgonj": "Manikganj",
    "Comilla": "Cumilla", "Kumilla": "Cumilla", "Bogra": "Bogura", "Naogan": "Naogaon", "Noagaon": "Naogaon",
    "Chuadanga": "Chuadanga", "Chuadange": "Chuadanga", "Jhenaidaha": "Jhenaidah", "Jhenidah": "Jhenaidah",
    "Jhinaidah": "Jhenaidah", "Jhenaidaha": "Jhenaidah", "Shariatpur": "Shariatpur", "Sariatpur": "Shariatpur",
    "Pirojpur": "Pirojpur", "Perojpur": "Pirojpur", "Patuakhali": "Patuakhali", "Meherpur": "Meherpur",
}
BN_ALIASES = {"চট্টগ্রাম": "Chattogram", "কুমিল্লা": "Cumilla", "যশোর": "Jashore", "যশোহর": "Jashore", "বরিশাল": "Barishal",
              "চাঁপাইনবাবগঞ্জ": "Chapainawabganj", "চাঁপাই নবাবগঞ্জ": "Chapainawabganj", "নবাবগঞ্জ": None,
              "কক্সবাজার": "Cox's Bazar", "কক্সবাজার": "Cox's Bazar", "মৌলভীবাজার": "Moulvibazar", "ঝালকাঠি": "Jhalokathi",
              "ঝালকাঠী": "Jhalokathi", "নেত্রকোণা": "Netrokona", "নেত্রকোনা": "Netrokona", "খাগড়াছড়ি": "Khagrachhari",
              "লক্ষ্মীপুর": "Lakshmipur", "লক্ষীপুর": "Lakshmipur", "ব্রাহ্মণবাড়িয়া": "Brahmanbaria", "বি-বাড়িয়া": "Brahmanbaria",
              "মুন্সীগঞ্জ": "Munshiganj", "মুন্সিগঞ্জ": "Munshiganj", "নারায়ণগঞ্জ": "Narayanganj", "নারায়নগঞ্জ": "Narayanganj",
              "বগুড়া": "Bogura", "বগুরা": "Bogura", "ময়মনসিংহ": "Mymensingh", "রাঙ্গামাটি": "Rangamati", "রাঙামাটি": "Rangamati",
              "নরসিংদী": "Narsingdi", "হবিগঞ্জ": "Habiganj", "সুনামগঞ্জ": "Sunamganj", "পঞ্চগড়": "Panchagarh",
              "ঠাকুরগাঁও": "Thakurgaon", "জয়পুরহাট": "Joypurhat", "সিরাজগঞ্জ": "Sirajganj", "কিশোরগঞ্জ": "Kishoreganj",
              "চট্রগ্রাম": "Chattogram", "চট্টগ্রাম": "Chattogram", "ঝিনাইদাহ": "Jhenaidah", "ঝিনাইদহ": "Jhenaidah",
              "নারায়ানগঞ্জ": "Narayanganj", "নারায়াণগঞ্জ": "Narayanganj", "নারাযনগঞ্জ": "Narayanganj", "চাপাইনবাবগঞ্জ": "Chapainawabganj"}
# Well-known metropolitan localities that are not upazilas in the seed (fallback only, when nothing else names a district)
LOCALITIES = {
    "Dhaka": ["Motijheel", "Dilkusha", "Gulshan", "Banani", "Mirpur", "Uttara", "Dhanmondi", "Mohammadpur", "Badda", "Bashundhara",
              "Moghbazar", "Mogbazar", "Malibagh", "Shantinagar", "Paltan", "Purana Paltan", "Kakrail", "Farmgate", "Tejgaon",
              "Karwan Bazar", "Kawran Bazar", "Panthapath", "Shyamoli", "Lalmatia", "Elephant Road", "New Market", "Azimpur",
              "Lalbagh", "Gopibag", "Wari", "Jatrabari", "Demra", "Khilgaon", "Rampura", "Banasree", "Banashree", "Aftabnagar",
              "Shewrapara", "Kafrul", "Pallabi", "Khilkhet", "Nikunja", "Baridhara", "Mohakhali", "Ashkona", "Dakshinkhan",
              "Uttarkhan", "Kamrangirchar", "Hazaribagh", "Hazaribag", "Jigatola", "Kalabagan", "Green Road", "Segunbagicha",
              "Shahbagh", "Sadarghat", "Islampur", "Nawabpur", "Gulistan", "Fakirapool", "Fakirerpool", "Arambagh", "Mugda",
              "Basabo", "Sabujbagh", "Tikatuli", "Gendaria", "Postogola", "Shyampur", "Ashulia", "Hemayetpur", "Amin Bazar",
              "Aminbazar", "Agargaon", "Sher-e-Bangla Nagar", "Kawranbazar", "Bangshal", "Kotwali Dhaka", "Shahjahanpur",
              "Mohakhali DOHS", "Banani DOHS", "Mirpur DOHS", "Kuril", "Vatara", "Bhatara", "Rayer Bazar", "Adabor", "Adabar",
              "Kallyanpur", "Gabtoli", "Nayapaltan", "Naya Paltan", "Mirpur-1", "Bijoynagar", "Topkhana", "Eskaton", "Dhaka Cantonment"],
    "Gazipur": ["Tongi", "Joydebpur", "Konabari", "Board Bazar", "Chandra", "Bhogra", "Gazipur Chowrasta"],
    "Narayanganj": ["Chashara", "Siddhirganj", "Fatullah", "Bhulta", "Kanchpur", "Madanpur", "Signboard"],
    "Chattogram": ["Agrabad", "Nasirabad", "Pachlaish", "Panchlaish", "Halishahar", "Khulshi", "Muradpur", "GEC", "Bahaddarhat",
                   "Oxygen", "Patenga", "Bayezid", "Bayazid", "Khatunganj", "Anderkilla", "Jubilee Road", "Sholoshahar", "Sholoshohor",
                   "Kalurghat", "Chandgaon", "Double Mooring", "Akbar Shah", "Akbarshah", "KEPZ", "CEPZ", "Lalkhan Bazar", "Kazir Dewri",
                   "Chawkbazar Chattogram", "Reazuddin Bazar", "Bakalia", "Pahartali", "Dewanhat", "Andarkilla"],
    "Khulna": ["Sonadanga", "Daulatpur Khulna", "Khalishpur", "Boyra", "Gollamari"],
    "Sylhet": ["Zindabazar", "Amberkhana", "Subid Bazar", "Bandar Bazar", "Chowhatta", "Uposhohor", "Upashahar", "Shahjalal Uposhohor"],
    "Rajshahi": ["Shaheb Bazar", "Saheb Bazar", "Laxmipur Rajshahi", "Uposhohor Rajshahi", "Binodpur", "Kazla", "Talaimari", "Rajpara",
                 "Boalia", "Motihar"],
    "Barishal": ["Nathullabad", "Rupatali", "Band Road", "Sadar Road Barishal"],
}
UPZ_ALIASES = {"Ishwardi": "Ishurdi", "Iswardi": "Ishurdi", "Chandnais": "Chandanaish", "Chandanaish": "Chandanaish",
               "Benapole": "Sharsha", "Raypur": "Raipur", "Debider": "Debidwar", "Debiddar": "Debidwar", "Kosba": "Kasba",
               "Saidpur": "Syedpur", "Sayedpur": "Syedpur", "Borhanuddin": "Borhan Sddin", "Burhanuddin": "Borhan Sddin",
               "Charfasson": "Charfesson", "Daulatkhan": "Doulatkhan"}
VOWELS = set("aeiouy")
ROADISH = {"road", "rd", "highway", "hwy", "sarak", "sharak", "sarani", "sharani", "bypass", "more", "mor", "gate", "tower", "plaza",
           "bhaban", "bhabon", "market", "college", "school", "hospital", "university", "court", "railway", "station", "bus",
           "রোড", "সড়ক", "মহাসড়ক", "মোড়", "গেট", "টাওয়ার", "প্লাজা", "ভবন", "মার্কেট", "কলেজ", "স্কুল", "হাসপাতাল"}


def skeleton(s):
    """Latin spelling key: lower-case letters, vowels dropped, doubles collapsed ('Comilla'=='Cumilla', 'Bogra'=='Bogura')."""
    s = unicodedata.normalize("NFKD", s or "").lower()
    s = s.replace("gonj", "ganj").replace("gong", "ganj").replace("nagor", "nagar").replace("pore", "pur")
    s = re.sub(r"[^a-z]", "", s)
    if not s:
        return ""
    out = s[0]
    for ch in s[1:]:
        if ch in VOWELS:
            continue
        if ch != out[-1]:
            out += ch
    return out


def bkey(s):
    """Bangla spelling key: NFC, no spaces/joiners/candrabindu, long vowels and ণ folded."""
    s = nfc(s or "")
    s = re.sub(r"[\s‌‍\-.,।]", "", s)
    for a, b in (("ঁ", ""), ("ী", "ি"), ("ূ", "ু"), ("ণ", "ন"), ("য়", "য"), ("ড়", "ড"), ("ঢ়", "ঢ"), ("ন্জ", "ঞ্জ"), ("ট্র", "ট্ট")):
        s = s.replace(a, b)
    return s


class Gazetteer:
    def __init__(self):
        rows = list(csv.DictReader(open(REPO / "data/seed/geo/admin_areas.csv", encoding="utf-8-sig")))
        self.by_id = {r["id"]: r for r in rows}
        self.div_of = {}          # district name_en -> division name lower
        self.dist_bn = {}
        self.upz = {}             # district -> [(name_en, skel, bkey)]
        dist_ids = {}
        for r in rows:
            if r["level"] == "district":
                dv = self.by_id[r["parent_id"]]["name_en"].lower()
                self.div_of[r["name_en"]] = dv
                self.dist_bn[r["name_en"]] = r["name_bn"]
                dist_ids[r["id"]] = r["name_en"]
        for r in rows:
            if r["level"] == "upazila" and r["parent_id"] in dist_ids:
                self.upz.setdefault(dist_ids[r["parent_id"]], []).append((r["name_en"], skeleton(r["name_en"]), bkey(r["name_bn"])))
        for alias, canon in UPZ_ALIASES.items():      # common spellings the seed (nuhil) writes differently
            for dname, lst in list(self.upz.items()):
                if any(u == canon for u, _, _ in lst):
                    lst.append((canon, skeleton(alias), "~" + alias))
        # district lookup keys
        self.en = {}
        amb = set()
        for name in self.div_of:
            for k in {skeleton(name)}:
                if k in self.en and self.en[k] != name:
                    amb.add(k)
                self.en[k] = name
        for a, name in EN_ALIASES.items():
            self.en.setdefault(skeleton(a), name)
        for k in amb:
            self.en.pop(k, None)
        self.bn = {bkey(v): k for k, v in self.dist_bn.items()}
        for a, name in BN_ALIASES.items():
            if name:
                self.bn[bkey(a)] = name
            else:
                self.bn.pop(bkey(a), None)
        self.exact = {n.lower().replace("'", ""): n for n in self.div_of}
        self.exact.update({a.lower().replace("'", ""): n for a, n in EN_ALIASES.items()})
        # polygons
        # every seed upazila name -> its districts (for addresses that name only an upazila)
        self.upz_all = {}
        for dname, lst in self.upz.items():
            for u, sk, b in lst:
                for key in (sk, "bn:" + b):
                    if len(key) >= (6 if key.startswith("bn:") else 4) and not re.search(r"sdr$", key):
                        self.upz_all.setdefault(key, set()).add((dname, u))
        self.upz_exact = {}
        for dname, lst in self.upz.items():
            for u, sk, b in lst:
                if not u.lower().endswith("sadar") and len(u) >= 4:
                    self.upz_exact.setdefault(u.lower().replace(" ", ""), set()).add((dname, u))
        self.loc = {}
        for dname, names in LOCALITIES.items():
            for n in names:
                self.loc.setdefault(skeleton(n), set()).add(dname)
        # postcodes from Bangladesh Post's booklet (the bdpost_postcodes_* collected sources)
        self.postcode = {}
        for f in sorted((REPO / "data/sources").glob("bdpost_postcodes_*_2026/places.csv")):
            for r in csv.DictReader(open(f, encoding="utf-8")):
                pc = (json.loads(r["extra_json"] or "{}")).get("postcode")
                if pc and r.get("district_en"):
                    self.postcode.setdefault(pc, set()).add(r["district_en"])
        g = json.load(open(REPO / "data/seed/geo/districts.geojson", encoding="utf-8"))
        self.polys = []
        for f in g["features"]:
            geom = f["geometry"]
            polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
            for poly in polys:
                xs = [p[0] for p in poly[0]]
                ys = [p[1] for p in poly[0]]
                self.polys.append((min(xs), min(ys), max(xs), max(ys), poly, f["properties"]["name_en"]))

    def district(self, s):
        """A district field (any spelling, en or bn) -> seed name_en or None."""
        s = nfc(s or "").strip()
        if not s:
            return None
        s = re.sub(r"(?i)\b(district|dist|zila|zilla|division|region|regional|zone|zonal|office|area|north|south|east|west|sadar|city|"
                   r"corporation|metro)\b\.?|\((north|south|east|west|[nsew])\)|-\s*\d+$|\d+", " ", s)
        s = re.sub(r"(জেলা|বিভাগ|সদর|উত্তর|দক্ষিণ|পূর্ব|পশ্চিম)", " ", s).strip(" ,.-()")
        if re.search(r"[ঀ-৿]", s):
            return self.bn.get(bkey(s))
        k = skeleton(s)
        return self.en.get(k) if len(k) >= 2 else None

    def _tokens(self, text):
        t = asc(nfc(text or ""))
        t = re.sub(r"(?i)\b(dist|zila|zilla|district|upazila|upazilla|thana|p\.?s|p\.?o|post|sadar)\b\.?", " , ", t)
        t = re.sub(r"(জেলা|উপজেলা|থানা|পোস্ট|ডাকঘর)\s*[:\-ঃ]?", " , ", t)
        return [w for w in re.split(r"[\s,;:/()\[\]|।\-–_#&.\"'’]+", t) if w]

    def find_districts(self, text):
        """Districts named in free text, in order of appearance (n-grams up to 3 words)."""
        words = self._tokens(text)
        hits = []
        i = 0
        while i < len(words):
            found = None
            for n in (3, 2, 1):
                if i + n > len(words):
                    continue
                chunk = words[i:i + n]
                if re.search(r"[ঀ-৿]", chunk[0]):
                    d = self.bn.get(bkey("".join(chunk)))
                else:
                    joined = "".join(chunk)
                    k = skeleton(joined)
                    d = self.exact.get(joined.lower()) or (self.en.get(k) if len(k) >= 3 else None)
                nxt = words[i + n].lower() if i + n < len(words) else ""
                if d and nxt in ROADISH:      # 'Dhaka Road', 'Rajshahi Court', 'রাজশাহী রোড' name a road / building, not the district
                    d = None
                if d:
                    found = (d, n)
                    break
            if found:
                hits.append(found[0])
                i += found[1]
            else:
                i += 1
        return hits

    def upazila(self, dist, s):
        """An upazila / thana name (field) inside a known district -> seed name_en or None."""
        if not dist or not s:
            return None
        s = nfc(s)
        s = re.sub(r"(?i)\b(upazila|upazilla|thana|p\.?s|sadar|model)\b\.?", lambda m: " sadar " if m.group(1).lower() == "sadar" else " ", s)
        cands = self.upz.get(dist, [])
        if re.search(r"[ঀ-৿]", s):
            k = bkey(re.sub(r"(উপজেলা|থানা)", "", s))
            hit = [u for u, _, b in cands if b == k]
        else:
            k = skeleton(s)
            hit = [u for u, sk, _ in cands if sk == k]
            if not hit and "sadar" in s.lower():   # 'Sadar' alone / 'Bogura Sadar' / 'Comilla Sadar Dakshin'
                k2 = skeleton(dist + " sadar")
                hit = [u for u, sk, _ in cands if sk == k2 or sk == skeleton(s.replace(dist, "") + dist + "sadar")]
        return hit[0] if len(hit) == 1 else None

    def find_upazila(self, dist, text):
        """Last seed upazila of `dist` named in free text (n-grams up to 3 words; skeleton length >= 4)."""
        cands = self.upz.get(dist, [])
        if not cands or not text:
            return None
        words = self._tokens(re.sub(r"(?i)\bsadar\b", " sadar ", text))
        sk = {}
        for u, s, b in cands:
            sk.setdefault(s, set()).add(u)
            sk.setdefault("bn:" + b, set()).add(u)
            sk.setdefault("=" + u.lower().replace(" ", ""), set()).add(u)
        last = None
        for i in range(len(words)):
            for n in (3, 2, 1):
                chunk = words[i:i + n]
                if len(chunk) < n:
                    continue
                if re.search(r"[ঀ-৿]", chunk[0]):
                    key = "bn:" + bkey("".join(chunk))
                    ok = len(key) >= 6
                else:
                    key = skeleton("".join(chunk))
                    ok = len(key) >= 4
                    if not (ok and key in sk) and len("".join(chunk)) >= 4:
                        key, ok = "=" + "".join(chunk).lower(), True
                if ok and key in sk and len(sk[key]) == 1:
                    last = next(iter(sk[key]))
                    break
        return last

    def _ngrams(self, text):
        words = self._tokens(text)
        for i in range(len(words)):
            for n in (3, 2, 1):
                chunk = words[i:i + n]
                if len(chunk) < n:
                    continue
                if re.search(r"[\u0980-\u09FF]", chunk[0]):
                    yield i, "bn:" + bkey("".join(chunk))
                else:
                    yield i, skeleton("".join(chunk))
                    yield i, "=" + "".join(chunk).lower()

    def by_upazila(self, text):
        """(district, upazila) of the last seed upazila named in the text whose name is unique in the country."""
        last = None
        for i, k in self._ngrams(text):
            hit = self.upz_exact.get(k[1:]) if k.startswith("=") else self.upz_all.get(k)
            if hit and len(hit) == 1:
                last = next(iter(hit))
        return last

    def by_locality(self, text):
        last = None
        for i, k in self._ngrams(text):
            hit = self.loc.get(k)
            if hit and len(hit) == 1 and len(k) >= 3:
                last = next(iter(hit))
        return last

    def by_postcode(self, text):
        t = asc(nfc(text or ""))
        last = None
        for m in re.finditer(r"[A-Za-z\u0980-\u09FF.]\s*[-–,]?\s*(\d{4})\b(?!\s*[/\-]?\s*\d)(?!\s*/)", t):
            hit = self.postcode.get(m.group(1))
            if hit and len(hit) == 1:
                last = next(iter(hit))
        return last

    def point(self, lat, lon):
        for x0, y0, x1, y1, poly, name in self.polys:
            if x0 <= lon <= x1 and y0 <= lat <= y1 and _in_poly(lon, lat, poly):
                return name
        return None


def _in_ring(x, y, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj_, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj_ - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def _in_poly(x, y, poly):
    return _in_ring(x, y, poly[0]) and not any(_in_ring(x, y, h) for h in poly[1:])




# SutonnyMJ / Bijoy ANSI -> Unicode (best-effort; copied from doa_protected_monuments_raj_2026, with 'Ý' read as ন্স)
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
 "Ý":"ন্স","Þ":"ন্ম","ß":"প্ত","à":"প্ট","á":"প্প","â":"প্ল","ã":"ব্দ","ä":"ব্জ","å":"ব্ধ","ç":"ভ্র","è":"ম্ন",
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


# ---------------------------------------------------------------- record model
GAZ = None
BD_BOX = (20.5, 26.75, 88.0, 92.75)
TODAY = datetime.date.today().isoformat()
LISTS = []       # filled by @source (in the order they are collected)
FACTS = []       # route facts (BIWTA / Ministry of Shipping speedboat fares)
SKIPPED = []     # (source, url, why) checked and not used; filled below
OBJ = "https://objectstorage.ap-dcc-gazipur-1.oraclecloud15.com/n/axvjbnqprylg/b/V2Ministry/o/"


def source(slug, organisation, organisation_bn, list_name, urls):
    def deco(fn):
        LISTS.append(dict(slug=slug, organisation=organisation, organisation_bn=organisation_bn, list=list_name, urls=urls, fn=fn))
        return fn
    return deco


def R(sid, url, **kw):
    """One place before placement. district: published district text (bn/en); district_en: already resolved seed name."""
    d = dict(sid=str(sid), url=url, name_bn="", name_en="", category="", address="", district="", district_en="", upazila="",
             upazila_en="", lat=None, lon=None, phone="", email="", website="", hours="", operator="", ownership="public",
             extra={}, notes=[], text="")
    d.update({k: v for k, v in kw.items() if v is not None})
    return d


def upz_from_address(dist, addr):
    """Seed upazila named in an address, ignoring road names ('শেরপুর রোড', 'Sherpur Road')."""
    if not dist or not addr:
        return ""
    a = re.sub(r"(?i)\S+\s+(রোড|সড়ক|road|rd\.?)\b", " ", addr)
    return GAZ.find_upazila(dist, a) or ""


def portal_content(page):
    """The content HTML of a national-portal (v2) page: the visible <rt-renderer> block(s)."""
    blocks = re.findall(r"(?s)<rt-renderer\b[^>]*>(.*?)</rt-renderer>", page)
    return "\n".join(blocks)


def portal_title(page):
    m = re.search(r"(?s)<title>(.*?)</title>", page)
    return txt(m.group(1).split("|")[0]) if m else ""


def pdf_text(content, layout=True):
    """Text layer of a PDF via poppler's pdftotext (required for the BIWTA lists)."""
    exe = shutil.which("pdftotext")
    if not exe:
        raise RuntimeError("pdftotext (poppler-utils) is not installed")
    with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
        f.write(content)
        f.flush()
        return subprocess.run([exe] + (["-layout"] if layout else []) + [f.name, "-"], capture_output=True, text=True,
                              timeout=300).stdout


import shutil, subprocess

# ================================================================ 1. BIWTA — inland river ports
BIWTA_PORTS_PAGE = "https://biwta.gov.bd/pages/static-pages/6922dce3933eb65569e12937"   # বন্দর ও পরিবহন
# Rows the PDF's text layer gets wrong: rows 48-54 and a few district cells are typed in a Unicode font whose text layer is
# broken (e.g. 'রোজ োহী', 'ক শলট'), row 32 mixes Unicode and Bijoy, and three Bijoy glyphs come out wrong. The values
# below were read from the rendered PDF page and are used only where the converted text matches the broken form.
PORT_NAME_FIX = {"32": "মেঘাইঘাট-নাটুয়ারপাড়া নদী বন্দর", "48": "মংলা ঘষিয়াখালী নদী বন্দর", "49": "রাজশাহী নদী বন্দর",
                 "50": "ভোলাগঞ্জ নদী বন্দর", "51": "গোয়াইনঘাট নদী বন্দর", "52": "সিলেট নদী বন্দর",
                 "53": "সন্দ্বীপ উপকূলীয় নদী বন্দর", "54": "হাতিয়া উপকূলীয় নদী বন্দর",
                 "22": "কক্সবাজার (কস্তুরাঘাট) নদী বন্দর"}
PORT_DIST_FIX = {"17": "ব্রাক্ষণবাড়িয়া, কিশোরগঞ্জ", "24": "নরসিংদী, নারায়ণগঞ্জ, গাজীপুর", "28": "লক্ষ্মীপুর",
                 "46": "ব্রাক্ষনবাড়িয়া, নরসিংদী, নারায়ণগঞ্জ", "48": "বাগেরহাট", "50": "সিলেট, সুনামগঞ্জ",
                 "51": "সিলেট, সুনামগঞ্জ", "52": "সিলেট, সুনামগঞ্জ", "53": "চট্টগ্রাম", "54": "নোয়াখালী"}
PORTS = {}   # serial -> record (speedboat routes are attached to these)


@source("biwta_river_ports", "Bangladesh Inland Water Transport Authority (BIWTA)", "বাংলাদেশ অভ্যন্তরীণ নৌ-পরিবহন কর্তৃপক্ষ",
        "অভ্যন্তরীণ নদী বন্দর সমূহের তালিকা (গেজেট বিজ্ঞপ্তি দ্বারা জারীকৃত নদী বন্দর)", [BIWTA_PORTS_PAGE])
def biwta_river_ports():
    page = get(BIWTA_PORTS_PAGE).text
    pdf_url = None
    for a in re.finditer(r'<a href="(https://objectstorage[^"]+\.pdf)">(.*?)</a>', page, flags=re.S):
        if "নদী বন্দর" in txt(a.group(2)) or "৪।" in txt(a.group(2)):
            pdf_url = a.group(1)
    if not pdf_url:
        raise RuntimeError("river-port list link not found on " + BIWTA_PORTS_PAGE)
    text = pdf_text(get(pdf_url).content)
    save_raw("biwta_river_ports.txt", text)
    if "54" not in asc(bijoy2uni(text.splitlines()[0] if text else "")) and "৫৪" not in bijoy2uni(text[:400]):
        print("WARNING: river-port list heading no longer says 54 ports")
    out, cur = [], None
    for line in text.splitlines():
        m = re.match(r"^\s*([0-9০-৯]{1,2})[.\s]\s+(\S.*)$", line)
        if m:
            serial = asc(m.group(1))
            cols = [c for c in re.split(r"\s{3,}", m.group(2).strip()) if c]
            cur = dict(serial=serial, cells=[cols], raw=[line])
            out.append(cur)
        elif cur is not None and line.strip():
            cur["cells"].append([c for c in re.split(r"\s{3,}", line.strip()) if c])
            cur["raw"].append(line)
    recs = []
    for p in out:
        first = p["cells"][0]
        name = bijoy2uni(first[0]).strip(" ,")
        dists = bijoy2uni(first[1]).strip(" ,") if len(first) > 1 else ""
        # continuation lines: a second name line ('বন্দর') and district overflow ('গাজীপুর', 'সুনামগঞ্জ', 'নারায়ণগঞ্জ')
        for c in p["cells"][1:]:
            u = [bijoy2uni(x).strip() for x in c]
            if u and u[0] == "বন্দর":
                name += " বন্দর"
            elif u and re.fullmatch(r"[ঀ-৿ ]{3,20}", u[0]) and not re.search("বন্দর|পরবর্তী|সীমানা|আইন|করা", u[0]) and len(c) == 1 \
                    and len(p["raw"][p["cells"].index(c)]) - len(p["raw"][p["cells"].index(c)].lstrip()) > 30:
                dists += ", " + u[0]
        name, dists = nfc(re.sub(r"\s+", " ", name)), nfc(re.sub(r"\s+", " ", dists))
        name = name.replace("মুন্বিগঞ্জ", "মুন্সিগঞ্জ")
        dists = dists.replace("মুন্বিগঞ্জ", "মুন্সিগঞ্জ")
        notes = []
        if p["serial"] in PORT_NAME_FIX and PORT_NAME_FIX[p["serial"]] != name:
            notes.append(f"Name read from the rendered PDF (text layer gives '{name}').")
            name = PORT_NAME_FIX[p["serial"]]
        if p["serial"] in PORT_DIST_FIX and PORT_DIST_FIX[p["serial"]] != dists:
            notes.append(f"District cell read from the rendered PDF (text layer gives '{dists}').")
            dists = PORT_DIST_FIX[p["serial"]]
        gazette = []
        dates = []
        for c in p["cells"]:
            for x in c:
                u = bijoy2uni(x)
                for d in re.findall(r"[0-9০-৯]{2}-[0-9০-৯]{2}-[0-9০-৯]{4}", u):
                    dates.append(asc(d))
                if re.search(r"(এস|Notification|এল/|আইন/)", u):
                    gazette.append(re.sub(r"\s+", " ", re.sub(r"ঘড়ঃরভরপধঃরড়হ ঘড়\.\s*ঐঞউ", "Notification No. HTD", u)).strip())
        names_d = [s.strip() for s in re.split(r"[,،]", dists) if s.strip()]
        resolved = [GAZ.district(s) for s in names_d]
        if not resolved or not resolved[0]:
            print("  river port without a district:", p["serial"], name, dists)
            continue
        ex = {"serial": int(p["serial"]), "districts_published": dists, "gazette_notification": "; ".join(gazette),
              "gazette_dates": dates, "proposed_category": "transport.river_port"}
        if len(resolved) > 1:
            ex["other_districts"] = [d for d in resolved[1:] if d]
            notes.append("The port limits span several districts (" + dists + "); the row is filed under the first one.")
        rec = R(f"port:{p['serial']}", pdf_url, name_bn=name, category="transport", district_en=resolved[0],
                operator="বাংলাদেশ অভ্যন্তরীণ নৌ-পরিবহন কর্তৃপক্ষ (BIWTA)", extra=ex,
                notes=(["Name as printed ('ভৈবর' for ভৈরব)."] if "ভৈবর" in name else []) + ["Gazetted inland river port (an area under BIWTA's port limits, not a single ghat); no coordinates published."] + notes)
        PORTS[p["serial"]] = rec
        recs.append(rec)
    if len(recs) < 50:
        raise RuntimeError(f"only {len(recs)} river ports parsed")
    return recs


# ================================================================ 1b. Speedboat routes and fares (Ministry of Shipping notice on BIWTA)
BIWTA_FARE_PAGE = "https://biwta.gov.bd/pages/static-pages/6922dc80933eb65569e10b43"     # ভাড়াসূচি
# The notice's text layer drops conjuncts (wkhtmltopdf + Nikosh), so the route names below were read from the rendered PDF
# (24-09-2026 notice, no. 18.00.0000.000.019.99.0019.26.333). fetch.py re-checks them against the PDF: the fares (digits survive)
# must appear in the same order, and the river-port headings must still be there, otherwise the run stops.
SPEEDBOAT = [  # (river port as printed, route as printed, fare Tk, class)
    ("আরিচা", "আরিচা-কাজীরহাট", 255, "শান্ত"), ("আরিচা", "পাটুরিয়া-দৌলতদিয়া", 50, "শান্ত"),
    ("আরিচা", "কাজীরহাট-দৌলতদিয়া", 235, "শান্ত"), ("আরিচা", "শিমুলিয়া-কাঠালবাড়ী", 145, "শান্ত"),
    ("আরিচা", "চর ভদ্রাসন-মৈনট", 165, "শান্ত"), ("আরিচা", "আরিচা-নরাদহ", 175, "শান্ত"),
    ("আরিচা", "আরিচা-নাজিরগঞ্জ", 435, "শান্ত"), ("আরিচা", "আরিচা-ধাওয়াপাড়া", 375, "শান্ত"),
    ("নাজিরগঞ্জ", "নাজিরগঞ্জ-ধাওয়াপাড়া", 105, "শান্ত"),
    ("বরিশাল", "বরিশাল-ভেদুরিয়া", 355, "শান্ত"), ("বরিশাল", "লাহারহাট-ভেদুরিয়া", 175, "শান্ত"),
    ("বরিশাল", "সায়েস্তাবাদ-পাতারহাট", 255, "শান্ত"), ("বরিশাল", "আমতলী-পুরাকাটা", 50, "শান্ত"),
    ("ভোলা", "ভেলুমিয়া-ধূলিয়া", 185, "শান্ত"), ("ভোলা", "ঘোষেরহাট-দশমিনা", 235, "শান্ত"),
    ("পটুয়াখালী", "বোয়ালিয়া স্লুইস গেট-কোড়ালিয়া স্লুইস গেট", 165, "শান্ত"), ("পটুয়াখালী", "পানপট্টি-পায়রা বন্দর", 250, "শান্ত"),
    ("পটুয়াখালী", "পানপট্টি-বাহের চর", 165, "শান্ত"), ("পটুয়াখালী", "পানপট্টি-আমরা গাছিয়া", 225, "শান্ত"),
    ("পটুয়াখালী", "পানপট্টি-চরমোন্তাজ", 260, "শান্ত"), ("পটুয়াখালী", "পানপট্টি-চরবৃষ্টিন", 290, "শান্ত"),
    ("পটুয়াখালী", "পানপট্টি-চরমন্ডল", 295, "শান্ত"), ("পটুয়াখালী", "চরকাজল-বন্যাতলী", 120, "শান্ত"),
    ("পটুয়াখালী", "পানপট্টি-কোড়ালিয়া", 155, "শান্ত"), ("পটুয়াখালী", "গলাচিপা-রাঙ্গাবালী", 415, "শান্ত"),
    ("পটুয়াখালী", "গলাচিপা-ফেলাবুনিয়া", 355, "শান্ত"), ("পটুয়াখালী", "চরমন্ডল-গৈনখালী", 120, "শান্ত"),
    ("চাঁদপুর", "নরসিংদী-সলিমগঞ্জ", 255, "শান্ত"), ("চাঁদপুর", "নরসিংদী-মরিচাকান্দি", 175, "শান্ত"),
    ("আশুগঞ্জ-ভৈরব", "ভৈরববাজার-নবীনগর", 295, "শান্ত"), ("বাঘাবাড়ী", "মেঘাইঘাট-নাটুয়ারপাড়া", 165, "শান্ত"),
    ("চট্টগ্রাম", "রাঙ্গামাটি-ফিশারীঘাট-মারিশ্যা", 935, "শান্ত"), ("চট্টগ্রাম", "রাঙ্গামাটি-ফিশারীঘাট-মাইনি", 530, "শান্ত"),
    ("চট্টগ্রাম", "রাঙ্গামাটি-ফিশারীঘাট-জুড়াইছড়ি", 375, "শান্ত"), ("চট্টগ্রাম", "রাঙ্গামাটি-ফিশারীঘাট-বরকল", 385, "শান্ত"),
    ("পটুয়াখালী", "কলাপাড়া-মৌডুবি", 295, "অশান্ত"), ("পটুয়াখালী", "চরমোন্তাজ-পানপট্টি", 445, "অশান্ত"),
    ("চাঁদপুর", "চাঁদপুর-চেয়ারম্যানঘাট (শরীয়তপুর)", 225, "অশান্ত"), ("চাঁদপুর", "মজুচৌধুরীর হাট-ইলিশা ঘাট (ভোলা)", 355, "অশান্ত"),
    ("চট্টগ্রাম", "কুমিরা-গুপ্তছড়া", 285, "অশান্ত"), ("চট্টগ্রাম", "কক্সবাজার ৬ নং ঘাট-মহেশখালী", 105, "অশান্ত"),
    ("চট্টগ্রাম", "বয়ারচর (চেয়ারম্যানঘাট)-নলছিরা, হাতিয়া", 355, "অশান্ত"),
    ("চট্টগ্রাম", "মগনামা-বড়ঘোপ (কুতুবদিয়া)", 95, "অশান্ত"), ("চট্টগ্রাম", "মগনামা-দরবারহাট (কুতুবদিয়া)", 95, "অশান্ত"),
]
# river-port heading -> (district of the BIWTA port office, river-port serial in the gazetted list or None)
SPEEDBOAT_PORT = {"আরিচা": ("Manikganj", "9"), "নাজিরগঞ্জ": ("Pabna", "43"), "বরিশাল": ("Barishal", "4"),
                  "ভোলা": ("Bhola", "13"), "পটুয়াখালী": ("Patuakhali", "7"), "চাঁদপুর": ("Chandpur", "5"),
                  "আশুগঞ্জ-ভৈরব": ("Brahmanbaria", "17"), "বাঘাবাড়ী": ("Sirajganj", "8"), "চট্টগ্রাম": ("Chattogram", None)}


@source("mos_speedboat_fares", "Ministry of Shipping (notice published by BIWTA)", "নৌপরিবহন মন্ত্রণালয়",
        "স্পিডবোটের সর্বশেষ যাত্রীভাড়া প্রজ্ঞাপন (নৌরুট ও ভাড়া)", [BIWTA_FARE_PAGE])
def mos_speedboat_fares():
    page = get(BIWTA_FARE_PAGE).text
    url = None
    for a in re.finditer(r'<a href="(https://objectstorage[^"]+\.pdf)"[^>]*>(.*?)</a>', page, flags=re.S):
        if "স্পিডবোট" in txt(a.group(2)):
            url = a.group(1)
    if not url:
        raise RuntimeError("speedboat fare notice not linked on " + BIWTA_FARE_PAGE)
    text = pdf_text(get(url).content)
    save_raw("mos_speedboat_fares.txt", text)
    body = text.split("(ক)", 1)[-1].split("০২।", 1)[0]
    fares = [int(asc(x)) for x in re.findall(r"\s([০-৯]{2,3})\s*$", body, flags=re.M)]
    if fares != [f for _, _, f, _ in SPEEDBOAT]:
        raise RuntimeError(f"speedboat notice changed: fares {fares} differ from the transcribed table; re-read the PDF")
    if "২৪-০৯-২০২৬" not in text:
        raise RuntimeError("speedboat notice is not the 24-09-2026 one the transcription was made from")
    for i, (port, route, fare, cls) in enumerate(SPEEDBOAT, 1):
        dist, serial = SPEEDBOAT_PORT[port]
        FACTS.append(dict(entity_level="route", entity_name_en="", district_en=dist, upazila_en="", code=f"speedboat:{i}",
                          fact="speedboat_fare", value=fare, unit="BDT per passenger", basis="notified", year=2026,
                          source_url=url,
                          notes=f"Speedboat route '{route}' under the {port} river port ({cls} নৌরুট, "
                                f"{'calm' if cls == 'শান্ত' else 'rough'} waterway); maximum fare per passenger, effective 24-09-2026. "
                                f"district_en is the river port's district (BIWTA port office), not necessarily both ends of the route. "
                                f"Route names read from the rendered PDF (its text layer drops conjuncts)."))
        if serial and serial in PORTS:
            PORTS[serial]["extra"].setdefault("speedboat_routes", []).append({"route": route, "fare_bdt": fare, "waterway": cls})
    return []


# ================================================================ 2. City corporations' bus-terminal pages
DSCC_TERMINALS = "https://dscc.gov.bd/pages/static-pages/6922e0b0933eb65569e28300"
MCC_TERMINALS = "https://mcc.gov.bd/pages/static-pages/6922dc66933eb65569e1024c"


def _maps_center(html_frag):
    m = re.search(r"!2d([0-9.]+)!3d([0-9.]+)", html_frag)
    return f"{float(m.group(2)):.6f},{float(m.group(1)):.6f}" if m else ""


@source("dscc_bus_terminals", "Dhaka South City Corporation", "ঢাকা দক্ষিণ সিটি কর্পোরেশন", "বাস টার্মিনাল", [DSCC_TERMINALS])
def dscc_bus_terminals():
    c = portal_content(get(DSCC_TERMINALS).text)
    out = []
    for h in re.findall(r"(?s)<h\d[^>]*>(.*?)</h\d>", c):
        name = txt(h)
        if "টার্মিনাল" in name:
            out.append(R("dscc:" + sid_hash(name), DSCC_TERMINALS, name_bn=name, category="transport.bus_terminal",
                         district_en="Dhaka", operator="ঢাকা দক্ষিণ সিটি কর্পোরেশন",
                         extra={"city_corporation": "Dhaka South City Corporation"},
                         notes=["The page names the terminal only (photos, no address)."]))
    return out


@source("mcc_bus_terminals", "Mymensingh City Corporation", "ময়মনসিংহ সিটি কর্পোরেশন", "বাস টার্মিনাল সমূহ", [MCC_TERMINALS])
def mcc_bus_terminals():
    c = portal_content(get(MCC_TERMINALS).text)
    out = []
    for tr in trs(c):
        cells = tds(tr)
        if not cells:
            continue
        name = txt(cells[0])
        if "টার্মিনাল" not in name and "র্টামিনাল" not in name:
            continue
        ex = {"city_corporation": "Mymensingh City Corporation"}
        mc = _maps_center(tr)
        if mc:
            ex["map_embed_center"] = mc
        q = re.search(r"!2s([^!]+)!5e", tr)
        if q:
            ex["map_embed_label"] = urllib.parse.unquote_plus(q.group(1)).split(":")[-1] if "%3A" not in q.group(1) else ""
        out.append(R("mcc:" + sid_hash(name), MCC_TERMINALS, name_bn=name, category="transport.bus_terminal",
                     district_en="Mymensingh", operator="ময়মনসিংহ সিটি কর্পোরেশন", extra=ex,
                     notes=["Name as printed ('বাসর্টামিনাল' is the page's spelling). The page embeds a Google map; its centre "
                            "is kept in extra_json.map_embed_center and not used as the location."]))
    return out


# ================================================================ 3. Bangladesh Parjatan Corporation — own hotels, motels, restaurants
PARJATAN = "https://parjatan.gov.bd/"
# menu headings that are places, not districts
PARJATAN_HEADING = {"টেকনাফ": "Cox's Bazar", "কুয়াকাটা": "Patuakhali", "বেনাপোল": "Jashore", "মাধবকুণ্ডু": "Moulvibazar"}


def _unit_category(name):
    if re.search("রেস্তোরাঁ|রেস্টুরেন্ট|ক্যাফেটেরিয়া|ক্যাফে", name):
        return "business.restaurant", None
    if re.search("পিকনিক|পর্যটন কেন্দ্র", name):
        return "tourism", None
    return "business", "business.hotel"


@source("parjatan_units", "Bangladesh Parjatan Corporation", "বাংলাদেশ পর্যটন করপোরেশন",
        "অধীনস্থ হোটেল/মোটেল ও রেস্তোরাঁ", [PARJATAN])
def parjatan_units():
    home = get(PARJATAN).text
    i = home.find("অধীনস্থ হোটেল/মোটেল")
    j = home.find("অনলাইন হোটেল-মোটেল বুকিং", i)
    menu = home[i:j]
    out, seen = [], set()
    for grp in re.findall(r"(?s)<h6\b[^>]*>(.*?)</ul>", menu):
        heading = txt(re.split(r"(?s)</h6>", grp)[0])
        for href, label in re.findall(r'(?s)<li\b[^>]*>\s*<a\b[^>]*?href="([^"]+)"[^>]*>(.*?)</a>', grp):
            label = txt(label)
            if not href.startswith("/pages/") or href in seen:
                if href == "#":
                    SKIPPED.append((f"Parjatan unit '{label}' ({heading})", "", "listed in the menu without a page"))
                continue
            seen.add(href)
            url = urllib.parse.urljoin(PARJATAN, href)
            page = get(url).text
            h2 = re.search(r"(?s)<h2[^>]*>(.*?)</h2>", page)
            title = txt(h2.group(1)) if h2 else portal_title(page)
            if not title or title == "পাতা":
                title = label if heading in label else f"{label}, {heading}"
            c = strip_noise(portal_content(page))
            c = re.sub(r"(?s)<!--.*?-->|<!\[if.*?<!\[endif\]>", "", c)
            body = " ".join(x for x in lines(c) if not re.search(r"mso-|Normal\s+0|MicrosoftInternetExplorer|table\.Mso", x))
            body_nolink = re.sub(r"হোটেল\s+বুকিং এর জন্য ক্লিক করুন", "", body)
            body_nolink = re.sub(r"^\s*(?:যোগাযোগ\s*[:ঃ]\s*)?(?:ঠিকানা\s*[:ঃ]\s*)?", "", body_nolink)
            addr = re.split(r"(?:ফোন|মোবাইল|ই-?মেইল|টেলিফোন|ফ্যাক্স|যোগাযোগ)", body_nolink)[0].strip(" ,।:ঃ")
            addr = re.sub(r"[\w.+-]+@[\w.-]+", "", addr).strip(" ,।")
            contact = body_nolink
            contact = re.split(r"ভাড়া|টাকা", contact)[0]          # some pages go on with room tariffs
            ph_all = [p for p in phones(contact).split("; ") if 7 <= len(re.sub(r"\D", "", p)) <= 15]
            # landlines and the corporation's own 01991-139xxx mobile series only; other mobiles may be managers' phones
            ph_keep = [p for p in ph_all if not re.match(r"(?:88)?01[3-9]", re.sub(r"\D", "", p)) or
                       re.match(r"(?:88)?01991139", re.sub(r"\D", "", p))]
            ph = "; ".join(ph_keep)
            if addr == title:
                addr = ""
            em = emails(body_nolink)
            booking = re.search(r'href="(https://hotels\.gov\.bd/[^"]+)"', c)
            cat, proposed = _unit_category(title)
            dist = None
            hits = GAZ.find_districts(addr)
            if hits:
                dist = hits[-1]
            if not dist:
                dist = PARJATAN_HEADING.get(heading) or GAZ.district(heading)
            ex = {"menu_group": heading, "published_name_menu": label if label != title else "",
                  "booking_url": booking.group(1) if booking else "", "proposed_category": proposed or ""}
            if len(ph_keep) < len(ph_all):
                ex["mobiles_not_collected"] = len(ph_all) - len(ph_keep)
            out.append(R("unit:" + href.rsplit("/", 1)[-1], url, name_bn=title, category=cat, address=addr,
                         district_en=dist or "", upazila_en=upz_from_address(dist, addr), phone=ph,
                         email=em, operator="বাংলাদেশ পর্যটন করপোরেশন", ownership="public", extra=ex,
                         notes=(["District from the address on the unit's page."] if hits else
                                ["District from the corporation's menu heading (the page gives no district)."])))
    return out


# ================================================================ 4. Ministry of Civil Aviation and Tourism — star-rated hotels
MOCAT_HOTELS = {"5": "https://mocat.gov.bd/pages/static-pages/6940329735ce18e1c055efda",
                "4": "https://mocat.gov.bd/pages/static-pages/694032a135ce18e1c055fad8",
                "3": "https://mocat.gov.bd/pages/static-pages/6940329335ce18e1c055ecbd"}


@source("mocat_star_hotels", "Ministry of Civil Aviation and Tourism (Hotel & Restaurant Cell)", "বেসামরিক বিমান পরিবহন ও পর্যটন মন্ত্রণালয়",
        "তারকা মানের হোটেলের তালিকা (পাঁচ/চার/তিন তারকা)", ["https://mocat.gov.bd/pages/static-pages/694032da35ce18e1c05636ee"] + list(MOCAT_HOTELS.values()))
def mocat_star_hotels():
    out = []
    for star, url in MOCAT_HOTELS.items():
        ls = [x.replace("\xad", "") for x in lines(portal_content(get(url).text))]
        k = 0
        while k < len(ls):
            m = re.match(r"^([০-৯0-9]+)\s*[.।]\s*(.+)$", ls[k])
            if m:
                name = nfc(re.sub(r"\s+", " ", m.group(2))).strip()
                addr = ls[k + 1] if k + 1 < len(ls) and not re.match(r"^[০-৯0-9]+\s*[.।]", ls[k + 1]) else ""
                hits = GAZ.find_districts(addr) or GAZ.find_districts(name)
                dist = hits[-1] if hits else None
                upz = upz_from_address(dist, addr)
                out.append(R(f"star{star}:{asc(m.group(1))}", url, name_bn=name, category="business", address=addr.strip(" ,।"),
                             district_en=dist or "", upazila_en=upz or "", ownership="private",
                             extra={"star_rating": int(star), "serial": int(asc(m.group(1))), "proposed_category": "business.hotel"},
                             notes=["Star-rated hotel as listed by the ministry's Hotel & Restaurant Cell; district from the address."]))
                k += 2 if addr else 1
            else:
                k += 1
    return out


# ================================================================ 5. Parjatan district pages — tourist attractions
PARJATAN_DIVS = ["6922df8a933eb65569e22a62", "6922df6c933eb65569e21e50", "6922e039933eb65569e26125", "6922de17933eb65569e182d5",
                 "6922df5e933eb65569e21874", "6922de03933eb65569e1798e", "6922dce6933eb65569e12a3a", "6922dfd2933eb65569e24255"]


def _section_category(sec):
    if re.search("ধর্মীয়", sec):
        return "tourism.religious_site"
    if re.search("প্রত্নতাত্ত্বিক|ঐতিহাসিক|স্থাপত্য|ঐতিহ্য", sec):
        return "tourism.historical"
    if re.search("প্রাকৃতিক|নৈসর্গিক|প্রকৃতি", sec):
        return "tourism.natural"
    if re.search("বিনোদন|পার্ক", sec):
        return "tourism.park"
    return "tourism"


def _name_category(name, base):
    if re.search("মার্কেট|বাজার$|পল্লী$", name) and base in ("tourism", "tourism.park"):
        return "business.market"
    if re.search("জাদুঘর|মিউজিয়াম|সংগ্রহশালা", name):
        return "tourism.museum"
    if re.search("সমুদ্র ?সৈকত|সী ?বীচ|বীচ", name):
        return "tourism.beach"
    if re.search("ঝর্ণা|ঝরনা|জলপ্রপাত", name):
        return "tourism.waterfall"
    if re.search("চা ?বাগান", name):
        return "tourism.tea_garden"
    if re.search("হাওর|বিল\\b|নদী|বাঁওড়", name) and base in ("tourism", "tourism.natural"):
        return "tourism.river_haor"
    if re.search("পার্ক|উদ্যান|চিড়িয়াখানা", name) and base in ("tourism", "tourism.natural", "tourism.park"):
        return "tourism.park"
    if re.search("মসজিদ|মন্দির|মাজার|দরগাহ|গির্জা|প্যাগোডা|বিহার|আখড়া|ক্যাথেড্রাল", name) and base in ("tourism", "tourism.natural"):
        return "tourism.religious_site"
    return base


SECTION_RX = re.compile(r"^\s*(?:[ক-হ]|[০-৯0-9]{1,2})\s*[)৷.।]\s*(.{3,80}?)\s*[:ঃ]?\s*$")
ITEM_RX = re.compile(r"^\s*([০-৯0-9]{1,2})\s*[.।)]\s*(.{2,90}?)\s*[:ঃ]+\s*$")
UNNUMBERED_RX = re.compile(r"^()([^\d০-৯:ঃ]{2,60}?)\s*[:ঃ]+\s*$")   # 'তাজহাট জমিদার বাড়িঃ' (Rangpur-style pages)
# festivals, foods, crafts, boat trips and peoples are listed as 'tourism products' on these pages; they are not places
NOT_A_PLACE_SECTION = re.compile("উৎসব|গ্রামীণ|কৃষি|খাদ্য")
NOT_A_PLACE_NAME = re.compile("মেলা|উৎসব|ঊৎসব|জয়ন্তী|জন্মোৎসব|উদযাপন|অনুষ্ঠান|ভ্রমণ|নৌ-?বিহার|নৌবিহার|নৌ-পরিবহন|বাইচ|লড়াই|"
                              "মিষ্টি|ঢাকাইয়া খানা|তেহারী|বাকরখানি|মন্ডা|পাতক্ষীরা|শিল্প$|^(?!.*(জাদুঘর|যাদুঘর)).*উপজাত|বসবাস|"
                              "রথযাত্রা|ফুল$|বলী খেলা|স্নান$|উপজেলা$|বর্ষারবণ")
GENERIC_NAMES = {"মন্দির", "মসজিদ", "জমিদার বাড়ী", "জমিদার বাড়ি", "বনাঞ্চল", "চরাঞ্চল", "হাওর ও বিল", "ইকোপার্ক", "নদী",
                 "প্রাচীন আমলের স্থাপনাসমূহ", "ঈদ গাহ"}


PARJATAN_DROPPED = []


@source("parjatan_attractions", "Bangladesh Parjatan Corporation", "বাংলাদেশ পর্যটন করপোরেশন",
        "জেলাভিত্তিক পর্যটন আকর্ষণ (বিভাগ → জেলা পাতা)", [urllib.parse.urljoin(PARJATAN, "/pages/static-pages/" + p) for p in PARJATAN_DIVS])
def parjatan_attractions():
    out, dropped = [], []
    for pid in PARJATAN_DIVS:
        durl = urllib.parse.urljoin(PARJATAN, "/pages/static-pages/" + pid)
        dpage = portal_content(get(durl).text)
        for href, label in re.findall(r'(?s)<a href="(/pages/static-pages/[^"]+)"[^>]*>(.*?)</a>', dpage):
            label = txt(label)
            label = re.sub(r"^[০-৯0-9]+\s*[।.)]\s*", "", label)
            if not label:
                continue
            dist = GAZ.district(re.sub("জেলা", "", label))
            url = urllib.parse.urljoin(PARJATAN, href)
            if not dist:
                print("  parjatan: district not recognised:", label)
                SKIPPED.append((f"Parjatan district page '{label}'", url, "district name not recognised"))
                continue
            try:
                c = portal_content(get(url).text)
            except RuntimeError as e:
                SKIPPED.append((f"Parjatan district page '{label}'", url, str(e).split(": ")[-1]))
                continue
            sec, n = "", 0
            for ln in lines(c):
                ln = ln.replace("‌", "").strip()
                if re.match(r"^\s*[ক-হ]\s*[)৷.।]", ln) and len(ln) < 90:
                    sec = ln
                    continue
                m = ITEM_RX.match(ln) or UNNUMBERED_RX.match(ln)
                if not m or not sec:
                    continue
                name = nfc(m.group(2)).strip(" ,-–")
                if len(name) < 2 or re.search("নাম ও বর্ণনা|যাতায়াত|যাবেন|অবস্থান|দূরত্ব|ভাড়া|খরচ|থাকা|খাওয়া|সময়|যোগাযোগ|পর্যটন আকর্ষণ", name):
                    continue
                if NOT_A_PLACE_SECTION.search(sec):
                    dropped.append(name)
                    continue
                if NOT_A_PLACE_NAME.search(name) or name in GENERIC_NAMES:
                    dropped.append(name)
                    continue
                n += 1
                base = _section_category(sec)
                out.append(R(f"attr:{href.rsplit('/', 1)[-1]}:{n}", url, name_bn=name, category=_name_category(name, base),
                             district_en=dist, upazila_en=GAZ.find_upazila(dist, name) or "",
                             extra={"section": re.sub(r"\s*[:ঃ]\s*$", "", sec), "serial_in_section": int(asc(m.group(1))) if m.group(1) else None,
                                    "district_page": label},
                             notes=["Attraction named on the corporation's district page; description not copied; no coordinates."]))
            if n == 0:
                print("  parjatan: no attractions parsed on", label, url)
    print(f"  parjatan: {len(dropped)} festivals/foods/crafts/boat trips/generic entries left out:", "; ".join(dropped))
    PARJATAN_DROPPED[:] = dropped
    return out


# ================================================================ 6. Bangladesh Tourism Board — beautifulbangladesh.gov.bd destinations
BTB = "https://beautifulbangladesh.gov.bd/"
BTB_PAGES = ["loc/" + d for d in ("dhaka", "chattogram", "khulna", "rajshahi", "rangpur", "mymensingh", "barishal", "sylhet")] + \
            ["cat/" + c for c in ("heritage", "green-zone", "landmarks", "hill-tracts-waterfalls", "land-of-rivers", "island", "sea-beaches")]
BTB_FOOD = []    # 'tasty-food' entries (dishes, not places) left out
BTB_CAT = {"heritage": "tourism.historical", "green-zone": "tourism.natural", "land-of-rivers": "tourism.river_haor",
           "island": "tourism.natural", "sea-beaches": "tourism.beach"}


def _btb_category(cat, name):
    n = name.lower()
    if cat == "luxury":
        return "business"
    if re.search(r"museum|jadughar", n):
        return "tourism.museum"
    if re.search(r"mosque|masjid|temple|mondir|mandir|church|pagoda|shrine|mazar|dargah|monastery|bihar|vihara|kyang", n) \
            and cat != "heritage":
        return "tourism.religious_site"
    if cat == "hill-tracts-waterfalls":
        return "tourism.waterfall" if re.search(r"fall|jharna|jhorna|khum", n) else "tourism.hill"
    if re.search(r"tea (garden|estate)", n):
        return "tourism.tea_garden"
    if re.search(r"beach|sea", n) and cat not in BTB_CAT:
        return "tourism.beach"
    if re.search(r"haor|river|beel|lake", n) and cat not in BTB_CAT:
        return "tourism.river_haor"
    if re.search(r"park|garden|zoo|eco", n) and cat not in BTB_CAT:
        return "tourism.park"
    return BTB_CAT.get(cat, "tourism")


@source("btb_destinations", "Bangladesh Tourism Board", "বাংলাদেশ ট্যুরিজম বোর্ড",
        "Beautiful Bangladesh — tourist attractions by division and category", [BTB + p for p in BTB_PAGES])
def btb_destinations():
    found = {}
    for p in BTB_PAGES:
        page = get(BTB + p).text
        for card in re.findall(r'(?s)<div class="single-item".*?<div class="like-share">', page):
            a = re.search(r'href="(https://beautifulbangladesh\.gov\.bd/district-destination/([^/"]+)/([^/"]+)/(\d+))"\s*>\s*<h5>(.*?)</h5>', card)
            if not a:
                continue
            url, dslug, cat, did, name = a.groups()
            loc = re.search(r'href="https://www\.google\.com/maps\?q=([-0-9.]+),([-0-9.]+)"[^>]*>(?:\s*<i[^>]*></i>)?\s*(.*?)</a>', card, flags=re.S)
            rec = found.setdefault(did, dict(url=url, dslug=dslug, cat=cat, name=txt(name), lat=None, lon=None, loc="", lists=[]))
            if loc:
                rec["lat"], rec["lon"], rec["loc"] = fnum(loc.group(1)), fnum(loc.group(2)), txt(loc.group(3))
            rec["lists"].append(p)
    # the sitemap names every destination page; those not on any list page are reported, not fetched one by one
    try:
        sm = get(BTB + "storage/backend/file/sitemap.xml").text
        all_ids = set(re.findall(r"district-destination/[^/<]+/[^/<]+/(\d+)", sm))
        missing = sorted(all_ids - set(found), key=int)
        if missing:
            print(f"  btb: {len(missing)} destination pages are in the sitemap but on no list page: fetching them")
            for did in missing:
                u = next(m for m in re.findall(r"(https://beautifulbangladesh\.gov\.bd/district-destination/[^<\s]+/%s)(?=<|\s)" % did, sm))
                dslug, cat = u.split("/")[-3], u.split("/")[-2]
                page = get(u).text
                h = re.search(r"(?s)<h[12][^>]*>(.*?)</h[12]>", strip_noise(page).split("</header>", 1)[-1])
                title = re.search(r"(?s)<title>(.*?)</title>", page)
                name = txt(h.group(1)) if h else (txt(title.group(1)).split("|")[0].strip() if title else "")
                mm = re.search(r"google\.com/maps\?q=([-0-9.]+),([-0-9.]+)", page)
                found[did] = dict(url=u, dslug=dslug, cat=cat, name=name, lat=fnum(mm.group(1)) if mm else None,
                                  lon=fnum(mm.group(2)) if mm else None, loc="", lists=["detail page"])
    except RuntimeError as e:
        print("  btb sitemap:", e)
    out = []
    for did, r in sorted(found.items(), key=lambda kv: int(kv[0])):
        dist = GAZ.district(r["dslug"].replace("-", " "))
        notes, ex = [], {"btb_id": int(did), "category_slug": r["cat"], "location_label": r["loc"], "district_slug": r["dslug"]}
        lat, lon = r["lat"], r["lon"]
        inside = lambda a, b: BD_BOX[0] <= a <= BD_BOX[1] and BD_BOX[2] <= b <= BD_BOX[3]
        if lat is not None and not inside(lat, lon) and inside(lon, lat):
            lat, lon = lon, lat
            notes.append("Published latitude/longitude were swapped; corrected.")
        if lat is not None and not inside(lat, lon):
            ex["published_latlon"] = f"{r['lat']},{r['lon']}"
            notes.append("Published map point is outside Bangladesh; not used.")
            lat = lon = None
        if lat is not None:
            pt = GAZ.point(lat, lon)
            label_in_pt = pt and r["loc"] and (GAZ.upazila(pt, r["loc"]) or GAZ.find_upazila(pt, r["loc"]) or GAZ.district(r["loc"]) == pt)
            label_in_dist = dist and r["loc"] and (GAZ.upazila(dist, r["loc"]) or GAZ.find_upazila(dist, r["loc"]) or GAZ.district(r["loc"]) == dist)
            if dist and pt != dist and pt and label_in_pt and not label_in_dist:
                notes.append(f"The page URL files it under {dist}, but its map point and location label ('{r['loc']}') are in "
                             f"{pt}; {pt} used.")
                dist = pt
            elif dist and pt != dist:
                ex["published_latlon"] = f"{lat},{lon}"
                notes.append(f"Published map point falls in {pt or 'no district'}, not {dist}; not used.")
                lat = lon = None
            elif not dist:
                dist = pt
        if r["cat"] == "tasty-food":
            BTB_FOOD.append(r["name"])
            continue
        if not r["name"]:
            continue
        upz = GAZ.upazila(dist, r["loc"]) if dist and r["loc"] else None
        if r["loc"] and not upz and dist:
            upz = GAZ.find_upazila(dist, r["loc"])
        if r["cat"] == "luxury":
            ex["proposed_category"] = "business.hotel"
        out.append(R(f"btb:{did}", r["url"], name_en=r["name"], category=_btb_category(r["cat"], r["name"]), district_en=dist or "",
                     upazila_en=upz or "", lat=lat, lon=lon, extra=ex,
                     notes=["Destination listed by the Bangladesh Tourism Board; location label and map point as published "
                            "(Google Maps link on the list card); description not copied."] + notes))
    return out


# ================================================================ 7. Forest Department — protected areas
BF_LIST = "https://bforest.gov.bd/pages/static-pages/6922e13b933eb65569e2b006"       # রক্ষিত এলাকা: ভূমিকা ও তালিকা
BF_EXTRA = ["https://bforest.gov.bd/pages/static-pages/6922df42933eb65569e20eaa",      # ইকোপার্ক (other eco-parks)
            "https://bforest.gov.bd/pages/static-pages/6922dd7f933eb65569e15420"]      # কুঞ্জবন
NON_DISTRICT = {"বঙ্গোপসাগর", "দক্ষিণ বঙ্গোপসাগর", "পূর্বাচল", "পার্বত্যচট্টগ্রাম", "পার্বত্য চট্টগ্রাম জেলা"}


def _pa_category(name):
    if re.search("জাতীয় উদ্যান|ইকো ?পার্ক|উদ্ভিদ উদ্যান|বোটানিক|সাফারী|কুঞ্জবন|গার্ডেন", name):
        return "tourism.park"
    return "tourism.natural"


def _pa_kind(name):
    for k, v in (("জাতীয় উদ্যান", "national_park"), ("ডলফিন", "dolphin_sanctuary"), ("জলাভূমি নির্ভর", "wetland_wildlife_sanctuary"),
                 ("বন্যপ্রাণী অভয়ারণ্য", "wildlife_sanctuary"), ("মেরিন", "marine_protected_area"), ("ইকো", "eco_park"),
                 ("উদ্ভিদ উদ্যান", "botanical_garden"), ("বোটানিক", "botanical_garden"), ("জীববৈচিত্র্য", "special_biodiversity_area"),
                 ("কুঞ্জবন", "kunjaban"), ("অভয়ারণ্য", "wildlife_sanctuary")):
        if k in name:
            return v
    return ""


def _pa_rows(url, master):
    page = get(url).text
    c = portal_content(page)
    out = []
    for tr in trs(c):
        cells = [txt(x) for x in tds(tr)]
        if master:
            if len(cells) < 4 or not re.fullmatch(r"[০-৯0-9]+", cells[0]):
                continue
            serial, name, loc, area, notif = cells[0], cells[1], cells[2], cells[3], cells[4] if len(cells) > 4 else ""
        else:
            if len(cells) < 3 or cells[0] in ("নাম", "") or "অবস্থান" in cells[1]:
                continue
            serial, name, loc, area, notif = "", cells[0], cells[1], cells[2], cells[3] if len(cells) > 3 else ""
        name = re.sub(r"\(\s*ছবি দেখার জন্য এখানে ক্লিক করুন\s*\)", "", name).strip()
        out.append(dict(serial=asc(serial), name=nfc(name), loc=loc, area=asc(area).replace(",", ""), notif=asc(notif), url=url))
    return out


@source("bforest_protected_areas", "Bangladesh Forest Department", "বন অধিদপ্তর",
        "বন অধিদপ্তরের রক্ষিত এলাকার তালিকা (+ ইকোপার্ক, কুঞ্জবন পাতা)", [BF_LIST] + BF_EXTRA)
def bforest_protected_areas():
    rows = _pa_rows(BF_LIST, True)
    if len(rows) < 50:
        raise RuntimeError(f"only {len(rows)} protected areas parsed")
    names = {bkey(r["name"]) for r in rows}
    for u in BF_EXTRA:
        for r in _pa_rows(u, False):
            k = bkey(r["name"])
            if k in names or any(k[:6] == n[:6] and (k in n or n in k) for n in names):
                continue
            names.add(k)
            rows.append(r)
    out = []
    for r in rows:
        loc = r["loc"]
        parts = [p.strip() for p in re.split(r"[,،]| এবং ", re.sub(r"\(.*?\)", "", loc)) if p.strip()]
        upz_hint = re.search(r"\((.*?)\)", loc)
        dists = [GAZ.district(p) for p in parts if p not in NON_DISTRICT]
        dists = [d for d in dists if d]
        if not dists and any(p in NON_DISTRICT for p in parts):
            SKIPPED.append((f"Forest Department protected area '{r['name']}'", r["url"], f"location '{loc}' is not a district"))
            continue
        if not dists:
            # 'তানোর, রাজশাহী' style (upazila, district) or 'যমুনা সেতুর পশ্চিম পাড় বাঁধ, পাবনা'
            hits = GAZ.find_districts(loc)
            dists = hits[-1:] if hits else []
        if not dists:
            SKIPPED.append((f"Forest Department protected area '{r['name']}'", r["url"], f"location '{loc}' is not a district"))
            continue
        dist = dists[0]
        upz = None
        if upz_hint:
            upz = GAZ.upazila(dist, upz_hint.group(1))
        if not upz:
            upz = GAZ.find_upazila(dist, loc)
        ex = {"protected_area_type": _pa_kind(r["name"]), "area_ha": fnum(r["area"]), "notification": r["notif"],
              "location_published": loc, "serial": int(r["serial"]) if r["serial"] else None,
              "other_districts": dists[1:]}
        notes = ["Protected area as listed by the Forest Department; no coordinates published."]
        if len(dists) > 1:
            notes.append("Spans several districts (" + loc + "); filed under the first one.")
        out.append(R(("pa:" + r["serial"]) if r["serial"] else "pa:" + sid_hash(r["name"]), r["url"], name_bn=r["name"],
                     category=_pa_category(r["name"]), district_en=dist, upazila_en=upz or "",
                     operator="বন অধিদপ্তর", extra=ex, notes=notes))
    return out


# ---------------------------------------------------------------- sources checked and not used
SKIPPED += [
    ("BIWTA ghat-wise launch passenger fare lists (অভ্যন্তরীণ নৌপথের ঘাট ভিত্তিক যাত্রীভাড়ার তালিকা, 154 + 26 pages)",
     BIWTA_FARE_PAGE, "scanned images without a text layer; no OCR is used, so the launch routes and ghats in them are not collected"),
    ("BIWTA launch-fare notice (যাত্রীবাহী নৌযানের সর্বশেষ যাত্রীভাড়া প্রজ্ঞাপন)", BIWTA_FARE_PAGE,
     "per-km fare rates only (no routes or ghats)"),
    ("BIWTA land register (ভূ-সম্পত্তির বিবরণ, 93 pages)", "https://biwta.gov.bd/pages/static-pages/6922dd00933eb65569e131c2",
     "land parcels by mouza/dag (terminals, ghats, offices mixed with plots), multi-line Bijoy layout; not a facility list"),
    ("BIWTA hotline numbers (জরুরি হট লাইন নাম্বার)", "https://biwta.gov.bd/pages/static-pages/6922e0a7933eb65569e28077",
     "published as images only"),
    ("BIWTA statistics / proactive-disclosure PDFs", "https://biwta.gov.bd/pages/static-pages/6922db7a933eb65569e0a52f",
     "scanned (CamScanner / Canon) PDFs without a text layer"),
    ("BIWTA pontoon management system", "https://pontoon.biwta.gov.bd/", "an application (JavaScript app for staff), no public list"),
    ("Bangladesh Railway station list", "https://railway.gov.bd/pages/files/6919975c933eb65569ddc4da",
     "no station register is published: the Information Book 2023-24 has district-wise station counts only (already in "
     "bd_railway_*), the station reservation-charge file is a scan, fare/timetable files list stops without district, class "
     "or code; eticket.railway.gov.bd is disallowed by robots.txt and not used"),
    ("BRTA bus fares (আন্তঃজেলা ও দূরপাল্লার রুট, ঢাকা/চট্টগ্রাম মেট্রো)", "https://brta.gov.bd/pages/static-pages/6922de1b933eb65569e184a9",
     "fare charts for routes, no terminal list"),
    ("BRTC", "https://brtc.gov.bd/", "only the depot list, already collected as brtc_depots_*"),
    ("Roads and Highways Department", "https://rhd.gov.bd/OnlineRoadNetwork/Default.asp",
     "road/bridge database; no published bus-terminal or ferry-ghat list found"),
    ("Dhaka Transport Coordination Authority", "https://dtca.gov.bd/",
     "no terminal list; the MRT Line-6 page is a 2015 project note with proposed stations; the bus-route list is a draft"),
    ("City corporations' portals (DNCC, CCC, Rajshahi, Khulna, Sylhet, Barishal, Rangpur, Cumilla, Narayanganj, Gazipur)", "",
     "no bus/truck-terminal page found in their menus (khulnacity.gov.bd did not resolve); DSCC and Mymensingh used"),
    ("MoCAT district-wise tourist spots", "https://mocat.gov.bd/pages/static-pages/694032c735ce18e1c0562385",
     "links to the district portals' tourist-spot pages, already collected as portal_tourist_spots_*"),
    ("hotels.gov.bd (Parjatan booking site)", "https://hotels.gov.bd/", "same units as the Parjatan menu; booking links kept in extra_json"),
    ("Tourism GIS map", "https://gis.beautifulbangladesh.gov.bd/", "JavaScript application without a documented public data service"),
    ("CAAB airports", "", "already collected (caab_airports_*)"),
]


# ---------------------------------------------------------------- output
EXTRA_BN_DISTRICTS = {"ব্রাক্ষণবাড়িয়া": "Brahmanbaria", "ব্রাক্ষনবাড়িয়া": "Brahmanbaria", "ব্রাক্ষ্মণবাড়িয়া": "Brahmanbaria",
                      "টাংগাইল": "Tangail", "মাদারিপুর": "Madaripur", "সাতক্ষিরা": "Satkhira", "চট্রগ্রাম": "Chattogram",
                      "শরিয়তপুর": "Shariatpur", "নেত্রকোণা": "Netrokona", "নারায়গঞ্জ": "Narayanganj", "রাজরাড়ী": "Rajbari", "কক্রবাজার": "Cox's Bazar"}


def keyname(div):
    return f"TRANSPORT_TOURISM_{DIVISIONS[div].upper()}_2026"


def folder(div):
    return f"transport_tourism_{DIVISIONS[div]}_2026"


RAW_FILES = {}


def save_raw(name, text):
    RAW_FILES[name] = text


def build(recs_by_list):
    by_div, unplaced = {}, {}
    for L in LISTS:
        for r in recs_by_list.get(L["slug"], []):
            dist = r["district_en"] or (GAZ.district(r["district"]) if r["district"] else None)
            if not dist or dist not in GAZ.div_of:
                unplaced.setdefault(L["slug"], []).append(r["name_bn"] or r["name_en"])
                continue
            div = GAZ.div_of[dist]
            ex = dict(r["extra"])
            ex.update(organisation=L["organisation"], organisation_bn=L["organisation_bn"], list=L["list"], list_slug=L["slug"])
            by_div.setdefault(div, []).append(dict(
                source_key=keyname(div), source_id=f"{L['slug']}:{r['sid']}", name_bn=nfc(r["name_bn"]), name_en=nfc(r["name_en"]),
                category_key=r["category"], lat=f"{r['lat']:.6f}" if r["lat"] is not None else "",
                lon=f"{r['lon']:.6f}" if r["lon"] is not None else "", address=nfc(r["address"]), district_en=dist,
                upazila_en=r["upazila_en"] or "", phone=r["phone"], website=r["website"], email=r["email"],
                opening_hours=r["hours"], operator=r["operator"], ownership=r["ownership"], extra_json=xj(ex),
                source_url=r["url"], notes=" ".join(r["notes"])))
    return by_div, unplaced


FACT_COLS = ["entity_level", "entity_name_en", "district_en", "upazila_en", "code", "fact", "value", "unit", "basis", "year",
             "source_key", "source_url", "notes"]


def write_division(div, rows, out, results, unplaced):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rows = sorted(rows, key=lambda r: r["source_id"])
    seen = set()
    for r in rows:
        assert r["source_id"] not in seen, r["source_id"]
        seen.add(r["source_id"])
    with open(out / "places.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=PLACE_COLS)
        w.writeheader()
        w.writerows(rows)
    facts = [dict(fr, source_key=keyname(div)) for fr in FACTS if GAZ.div_of.get(fr["district_en"]) == div]
    with open(out / "facts.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FACT_COLS)
        w.writeheader()
        w.writerows(facts)
    files = ["places.csv", "facts.csv"]
    used = [L for L in LISTS if results.get(L["slug"], {}).get("status") == "ok"]
    urls = []
    for L in used:
        for u in L["urls"] + results[L["slug"]].get("extra_urls", []):
            if u not in urls:
                urls.append(u)
    meta = dict(
        key=keyname(div), division=div, kind="transport_tourism",
        name=f"Transport and tourism lists of government agencies — {div.title()} Division",
        organization="Various government agencies (each row's agency in extra_json.organisation, its list in extra_json.list)",
        source_type="government_portal", trust_level=4, urls=urls, accessed=TODAY, publication_date=None,
        license=None, license_url=None,
        attribution="BIWTA, Ministry of Shipping, DSCC, Mymensingh City Corporation, Bangladesh Parjatan Corporation, "
                    "Ministry of Civil Aviation and Tourism, Bangladesh Tourism Board, Bangladesh Forest Department",
        notes=("National lists collected once and split by division (district normalised to data/seed/geo/admin_areas.csv). "
               "Names as published; descriptions are never copied. Coordinates only where the agency publishes them "
               "(Tourism Board map links) and they fall inside the row's district. Office phones/e-mails only. No licence is "
               "stated by any of the sites. Checked and not used: " + "; ".join(f"{n} ({why})" for n, u, why in SKIPPED) + "."),
        files={p: hashlib.sha256((out / p).read_bytes()).hexdigest() for p in files})
    (out / "SOURCE.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(div, rows, facts, out, results, unplaced)
    print(f"{div}: {len(rows)} places, {len(facts)} facts -> {out}")


def write_report(div, rows, facts, out, results, unplaced):
    by_list, by_cat = {}, {}
    for r in rows:
        s = json.loads(r["extra_json"])["list_slug"]
        by_list.setdefault(s, {}).setdefault(r["category_key"], 0)
        by_list[s][r["category_key"]] += 1
        by_cat[r["category_key"]] = by_cat.get(r["category_key"], 0) + 1
    with_pt = sum(1 for r in rows if r["lat"])
    with_upz = sum(1 for r in rows if r["upazila_en"])
    L = [f"# {keyname(div)} — transport and tourism lists of government agencies, {div.title()} Division", "",
         f"Generated by `fetch.py` on {TODAY} (`--division {div}` / `--all-divisions`). Source type `government_portal`, trust "
         "level 4. Each national list is fetched once and split by division; the agency and list are named on every row "
         "(`extra_json.organisation`, `extra_json.list`).", "",
         f"**{len(rows)} places**: " + (", ".join(f"{k} {v}" for k, v in sorted(by_cat.items())) or "none") +
         f". {with_pt} with coordinates, {with_upz} with an upazila. **{len(facts)} facts** (speedboat route fares).", "",
         "## By list", "", "| Agency — list | Rows here | By category | National result |", "|---|---|---|---|"]
    for Lst in LISTS:
        res = results.get(Lst["slug"])
        if not res:
            continue
        c = by_list.get(Lst["slug"], {})
        nat = (f"{res['n']} rows; {len(unplaced.get(Lst['slug'], []))} without a district" if res["status"] == "ok"
               else "failed: " + res["error"])
        if Lst["slug"] == "mos_speedboat_fares" and res["status"] == "ok":
            nat = f"{len(FACTS)} route fares (facts.csv)"
            c = {"facts": len(facts)} if facts else {}
        L.append(f"| {Lst['organisation']} — {Lst['list']} | {sum(c.values())} | "
                 f"{', '.join(f'{k} {v}' for k, v in sorted(c.items())) or '—'} | {nat} |")
    L += ["", "## How rows were made", "",
          "- **BIWTA river ports** (`transport`, proposed `transport.river_port`): the 54 gazetted inland river ports from the PDF "
          "linked on BIWTA's 'বন্দর ও পরিবহন' page. The PDF is typed in Bijoy (SutonnyMJ); its text layer is converted to Unicode. "
          "Rows 48–54, row 32, row 22's name and a few district cells use a font whose text layer is broken; those values were read "
          "from the rendered page and are applied only where the converted text has the known broken form (noted on the row). "
          "A port spanning several districts is filed under the first district listed (all in `extra_json`). Gazette notification "
          "numbers and dates are kept. River ports are port-limit areas, not single ghats.",
          "- **Speedboat routes** (`facts.csv`, and `extra_json.speedboat_routes` on the river-port row): Ministry of Shipping notice "
          "of 24-09-2026 (linked on BIWTA's ভাড়াসূচি page). The PDF's text layer drops conjuncts, so the 44 route names were "
          "read from the rendered page; `fetch.py` checks that the fares in the PDF still match the transcription in order and "
          "stops otherwise. `district_en` of a route fact is the district of the BIWTA river port it is listed under.",
          "- **Bus terminals**: Dhaka South City Corporation's and Mymensingh City Corporation's 'বাস টার্মিনাল' pages "
          "(names only; Mymensingh's embedded map centres kept in `extra_json.map_embed_center`, not used as coordinates).",
          "- **Parjatan units**: every unit page linked under 'অধীনস্থ হোটেল/মোটেল' on parjatan.gov.bd: name, address, the "
          "unit's landlines / corporate mobiles and mailbox as printed (no staff names), booking link. Hotels/motels/holiday "
          "complexes use the top-level `business` key with proposed `business.hotel`; restaurants `business.restaurant`; "
          "tourist centres/picnic spots `tourism`.",
          "- **Star-rated hotels**: Ministry of Civil Aviation and Tourism (Hotel & Restaurant Cell) five/four/three-star lists: "
          "name, address, star rating; district from the address. `business` (proposed `business.hotel`).",
          "- **Parjatan attractions**: the corporation's district pages (division page → district page). Only the attraction "
          "headings are taken (numbered, or on some pages a short line ending in a colon); the section heading (historical/archaeological, religious, natural, cultural …) sets "
          "the category, refined by words in the name (museum, beach, waterfall, tea garden, park, mosque/temple …). "
          "Descriptions are not copied. Festivals, foods, crafts, boat trips, peoples and one-word generic entries listed as "
          "'tourism products' are left out (" + str(len(PARJATAN_DROPPED)) + " nationally).",
          "- **Tourism Board destinations**: beautifulbangladesh.gov.bd division and category list pages (plus any destination in "
          "the site's sitemap that no list page shows): English name, district (URL), location label, and the map point of the "
          "card's Google Maps link. A point outside the row's district is dropped (kept in `extra_json.published_latlon`); where "
          "the point and the location label agree on another district than the URL, that district is used (noted). "
          "'tasty-food' entries (dishes) are left out; 'luxury' hotels use `business` (proposed `business.hotel`).",
          "- **Forest Department protected areas**: the 58-row 'রক্ষিত এলাকার তালিকা' (national parks, wildlife and dolphin "
          "sanctuaries, eco-parks, special biodiversity areas, marine protected areas, botanical garden) plus the other eco-park "
          "and kunjaban pages (deduplicated by name); area (ha) and notification kept. National parks, eco-parks, gardens → "
          "`tourism.park`; sanctuaries and other areas → `tourism.natural`. Marine protected areas in the Bay of Bengal and "
          "Purbachal's area (no district) are not placed.",
          "- District/upazila: normalised to the seed's English names; the published value is kept in `extra_json` where it "
          "differs (`districts_published`, `location_published`, `location_label`).",
          "", "## Not placed (no district)", ""]
    any_un = False
    for s, names in unplaced.items():
        if names:
            any_un = True
            L.append(f"- {s}: {len(names)} — " + ", ".join(names[:12]) + (" …" if len(names) > 12 else ""))
    if not any_un:
        L.append("- none")
    L += ["", "## Checked and not used", ""]
    L += [f"- **{n}**: {why}" + (f" ({u})" if u else "") for n, u, why in SKIPPED]
    L += ["", "## Proposed taxonomy keys", "",
          "`transport.river_port` (BIWTA river ports, now `transport`), `business.hotel` (hotels, motels, resorts; now `business`), "
          "`tourism.protected_area` (wildlife sanctuaries, special biodiversity areas; now `tourism.natural`), "
          "`transport.ferry_ghat` and `transport.metro_station` (no rows yet).",
          "", "## Data-quality notes", "",
          "- The river-port list is as of 02-06-2025 (last notification); BIWTA's page was checked on " + TODAY + ".",
          "- Parjatan unit phones: landlines and the corporation's own 01991-139xxx mobile series are kept; other mobile "
          "numbers on the unit pages (possibly managers' phones) are not collected (`extra_json.mobiles_not_collected` counts "
          "them). The units' own mailboxes (some on gmail) are kept as printed.",
          "- Tourism Board map points are Google Maps links chosen by the site editors, not surveyed positions.",
          "- Parjatan attraction pages mix tourist sites with institutions (universities, colleges) listed as attractions; "
          "they are kept as published under `tourism` and may duplicate rows from UGC/BANBEIS/DoA sources.",
          "", "## Licence", "", "No site states a licence. Only facts (names, addresses, codes, contacts, coordinates, fares) "
          "are taken.", ""]
    (out / "REPORT.md").write_text("\n".join(L), encoding="utf-8")


def main():
    global GAZ, HTTP_CACHE
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().split("\n")[0])
    ap.add_argument("--division", default="rajshahi", choices=list(DIVISIONS))
    ap.add_argument("--all-divisions", action="store_true")
    ap.add_argument("--out", help="output folder (single division only)")
    ap.add_argument("--only", help="comma-separated list slugs")
    ap.add_argument("--http-cache", help="development: folder for raw HTTP responses")
    a = ap.parse_args()
    if a.all_divisions and a.out:
        raise SystemExit("--out works with a single --division")
    if a.http_cache:
        HTTP_CACHE = a.http_cache
        os.makedirs(HTTP_CACHE, exist_ok=True)
    GAZ = Gazetteer()
    for alias, d in EXTRA_BN_DISTRICTS.items():      # spellings in these lists that the shared gazetteer lacks
        GAZ.bn[bkey(alias)] = d
    only = set(a.only.split(",")) if a.only else None
    recs, results = {}, {}
    for Lst in LISTS:
        if only and Lst["slug"] not in only:
            continue
        print("fetching", Lst["slug"], flush=True)
        try:
            got = Lst["fn"]()
            recs[Lst["slug"]] = got
            results[Lst["slug"]] = dict(status="ok", n=len(got))
            print(f"  {Lst['slug']}: {len(got)}", flush=True)
        except Exception as e:
            results[Lst["slug"]] = dict(status="failed", error=str(e)[:300], n=0)
            print(f"  {Lst['slug']} FAILED: {e}", flush=True)
            traceback.print_exc(limit=3)
    by_div, unplaced = build(recs)
    divs = list(DIVISIONS) if a.all_divisions else [a.division]
    for div in divs:
        out = a.out if a.out else (HERE if div == "rajshahi" else HERE.parent / folder(div))
        write_division(div, by_div.get(div, []), out, results, unplaced)
    for s, names in unplaced.items():
        print("without district:", s, len(names), names[:20])


if __name__ == "__main__":
    main()
