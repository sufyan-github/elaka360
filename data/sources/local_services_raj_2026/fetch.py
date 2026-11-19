#!/usr/bin/env python3
"""Local public-service offices (electricity, water, gas, engineering, social services, cooperatives, fisheries …) from the
organisations' own government / state-utility websites, split by division.

Usage:
  python3 fetch.py [--division rajshahi|rangpur|dhaka|chattogram|khulna|barishal|sylhet|mymensingh] [--out DIR]
  python3 fetch.py --all-divisions            # fetch every national list once, write all 8 division folders
  options: --only reb,desco …  (subset of organisations)   --cache DIR  (reuse/keep normalised national lists)
           --http-cache DIR (development: reuse raw HTTP responses)   --no-pbs-offices (skip the 80 PBS sites' office pages)

Keys: LOCAL_SERVICES_RAJ_2026, LOCAL_SERVICES_RANG_2026, LOCAL_SERVICES_DHK_2026, LOCAL_SERVICES_CTG_2026,
LOCAL_SERVICES_KHL_2026, LOCAL_SERVICES_BAR_2026, LOCAL_SERVICES_SYL_2026, LOCAL_SERVICES_MYM_2026
(folders local_services_<code>_2026, kind "local_services", source_type government_portal, trust level 4).
Every row is an office as listed by its own organisation (named in extra_json.organisation). Officers' names, officers'
mobiles and personal / non-official e-mails are never written: only office names, addresses, office landlines,
published complaint-centre / hotline / customer-service numbers, and official e-mails on the organisation's own domain.
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




# ---------------------------------------------------------------- page helpers (national-portal 2026 framework)
def cv(page):
    """The page's ContentViewerWidget fragment (comments/scripts stripped), else the whole page."""
    page = strip_noise(page)
    i = page.find('data-widget_name="ContentViewerWidget"')
    if i < 0:
        return page
    j = page.find("এই কনটেন্টটি শেয়ার করতে", i)
    return page[i:j if j > 0 else len(page)]


def cells(tr):
    return re.findall(r"(?is)<t[hd]\b[^>]*>(.*?)</t[hd]>", tr)


def table_rows(fragment):
    """[[cell html, …], …] of every <tr> of every table in the fragment."""
    out = []
    for tb in re.findall(r"(?is)<table.*?</table>", fragment):
        out += [cells(tr) for tr in trs(tb)]
    return out


def menu_links(page):
    out, seen = [], set()
    for m in re.finditer(r'(?is)<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', page):
        h, t = _html.unescape(m.group(1)).strip(), txt(m.group(2))
        if (h, t) not in seen:
            seen.add((h, t))
            out.append((h, t))
    return out


def landlines(s):
    """Fixed-line numbers only (mobiles dropped), ASCII, '; '-joined."""
    return phones(s, keep_mobiles=False)


def any_phones(s):
    """All numbers incl. mobiles: only for numbers the organisation labels as a complaint centre / hotline / service centre."""
    return phones(s, keep_mobiles=True)


def org_emails(s, domains):
    """Official e-mails only: on *.gov.bd or one of the organisation's own domains."""
    s = asc(s or "").replace("[at]", "@").replace("(at)", "@")
    keep = []
    for e in emails(re.sub(r"\s+@\s*|\s*@\s+", "@", s)).split("; "):
        if e and (e.endswith(".gov.bd") or any(e.endswith("@" + d) or e.endswith("." + d) for d in domains)):
            keep.append(e)
    return "; ".join(dict.fromkeys(keep))


def labelled(text, labels, stop):
    """Value after the first of `labels` in text, up to the next of `stop` (regex alternations)."""
    m = re.search(r"(?:%s)\s*[:ঃ\-]*\s*(.*?)(?=(?:%s)|$)" % (labels, stop), text, re.S)
    return m.group(1).strip(" ,;/") if m else ""


def host_of(u):
    return urllib.parse.urlsplit(u if "//" in u else "http://" + u).netloc.lower().split(":")[0].removeprefix("www.")


def portal_place(url):
    """(district, upazila) from a national-portal host: <office>.<upazila>.<district>.gov.bd / <office>.<district>.gov.bd."""
    h = host_of(url or "")
    if not h.endswith(".gov.bd"):
        return None, None
    parts = h[:-len(".gov.bd")].split(".")
    if len(parts) < 2:
        return None, None
    d = GAZ.district(parts[-1])
    if parts[-1].endswith("div") or not d:
        return None, None
    u = upz_match(d, parts[-2]) if len(parts) >= 3 else None
    return d, u


def get_page(url):
    return get(url).content.decode("utf-8", "replace")      # every site used here serves UTF-8


# ---------------------------------------------------------------- spelling-tolerant upazila match (English)
_SUBS = (("chh", "c"), ("ph", "f"), ("bh", "b"), ("kh", "k"), ("gh", "g"), ("th", "t"), ("dh", "d"), ("sh", "s"), ("ch", "c"),
         ("c", "k"), ("z", "j"), ("w", ""), ("x", "ks"), ("q", "k"), ("v", "b"), ("y", "i"), ("gonj", "ganj"), ("gong", "ganj"))


def _fkey(s):
    s = unicodedata.normalize("NFKD", s or "").lower()
    s = re.sub(r"\(\s*n\s*\)|\bnorth\b", " uttar ", s)
    s = re.sub(r"\(\s*s\s*\)|\bsouth\b|^south(?=[a-z]{4})", " dakshin ", s)
    s = re.sub(r"^north(?=[a-z]{4})", " uttar ", s)
    s = re.sub(r"[^a-z]", "", s)
    for a, b in _SUBS:
        s = s.replace(a, b)
    if not s:
        return ""
    out = s[0]
    for ch in s[1:]:
        if ch in "aeiou" or ch == "h":
            continue
        if ch != out[-1]:
            out += ch
    return out


def _lev1(a, b):
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) <= 1
    if len(a) > len(b):
        a, b = b, a
    return any(b[:i] + b[i + 1:] == a for i in range(len(b)))


def upz_match(dist, name):
    """Seed upazila of `dist` for an English or Bangla name: exact skeleton (GAZ.upazila), else a spelling-tolerant key
    (ph/f, sh/s, z/j, North/(N) …), else one edit away on that key; None when not unique."""
    if not dist or not name:
        return None
    m = re.match(r"(?i)^\s*(.+?)\s+sadar\b", name)
    if m and GAZ.district(m.group(1)) not in (None, dist):
        return None        # 'Barishal Sadar' is not the Sadar upazila of another district
    if m and name[m.end():].strip(" -()"):
        return None        # 'Comilla Sadar Dakshin': a second Sadar upazila; not guessed
    if m and GAZ.district(m.group(1)) == dist:
        return next((u for u, _, b in GAZ.upz.get(dist, []) if u.lower().endswith("sadar") and not b.startswith("~")
                     and GAZ.district(re.sub(r"(?i)\s*sadar.*$", "", u)) == dist), None) or GAZ.upazila(dist, name)
    u = GAZ.upazila(dist, name)
    if u or re.search(r"[ঀ-৿]", name):
        return u
    k = _fkey(name)
    if len(k) < 2:
        return None
    lst = [u for u, _, b in GAZ.upz.get(dist, []) if not b.startswith("~")]
    hit = sorted({u for u in lst if _fkey(u) == k})
    if len(hit) == 1:
        return hit[0]
    if len(k) >= 4:
        hit = sorted({u for u in lst if _lev1(_fkey(u), k)})
        if len(hit) == 1:
            return hit[0]
    return None


# ---------------------------------------------------------------- record model
def R(org, kind, sid, url, **kw):
    """One normalised record before placement. Fields: name_en name_bn category address district upazila lat lon phone email
    website hours extra notes text (free text used only for placement) host (portal URL used for placement) prefer
    proposed (proposed taxonomy key)."""
    d = dict(org=org, kind=kind, sid=str(sid), url=url, name_en="", name_bn="", category="government", address="",
             district="", upazila="", lat=None, lon=None, phone="", email="", website="", hours="", extra={}, notes="",
             text="", host="", prefer="field", proposed="", parent=None, prefix=None, how="")
    d.update({k: v for k, v in kw.items() if v is not None})
    return d


ORGS = []   # filled by @org (in the order of the brief)


def org(slug, name_en, name_bn, group, urls, domains=(), prefix_en="", prefix_bn="", ownership="public", area=(), area_default="",
        ordered=False):
    """area: the districts of a utility's published service area (Bangla metropolitan localities are looked up there, and a
    placement outside it is rejected); area_default: the district used when the row names no place and the service area has
    one main district; ordered: the list is ordered by area, so ambiguous upazila names may be resolved by their neighbours."""
    def deco(fn):
        ORGS.append(dict(slug=slug, name_en=name_en, name_bn=name_bn, group=group, urls=urls, fn=fn, domains=tuple(domains),
                         prefix_en=prefix_en or name_en, prefix_bn=prefix_bn or name_bn, ownership=ownership, area=tuple(area),
                         area_default=area_default, ordered=ordered))
        return fn
    return deco


PBS_OFFICES = True
UTIL = "government.utility_office"        # proposed taxonomy keys (not yet in categories.csv): kept in extra_json


def plines(fragment):
    """Text lines of a content fragment (cells, paragraphs and line breaks split), without the framework's banner lines."""
    s = re.sub(r"(?is)<br\s*/?>|</p>|</div>|</li>|</h\d>|</t[dh]>|</tr>", "\n", fragment or "")
    s = _html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\xa0", " ").replace("​", "").replace("‌", "")
    out = []
    for x in s.splitlines():
        x = nfc(re.sub(r"\s+", " ", x).strip())
        if x and not re.search(r"হাল-নাগাদ করা হয়েছে|^কন্টেন্ট:|^data-widget_name", x):
            out.append(x)
    return out


PERSONISH = re.compile(r"ম্যানেজার|প্রকৌ|জনাব|মোঃ|মো\.|মোছাঃ|কর্মকর্তা|প্রকৌশলী|ইঞ্জিনিয়ার|সুপারভাইজার|ইনচার্জ|ইন-চার্জ|মোবাইল|ফোন|"
                       r"ই-মেইল|ইমেইল|e-mail|email|Mobile|Phone|Engr|Md\.", re.I)


def place_line(line):
    """A short address line made only of place names ('দূর্গাপুর, রাজশাহী।'), else ''."""
    if not line or PERSONISH.search(line) or len(line) > 90 or re.search(r"\d{5,}", asc(line)):
        return ""
    parts = [p.strip(" ।.") for p in re.split(r"[,،]", line) if p.strip(" ।.")]
    if len(parts) < 2 or any(len(p.split()) > 4 for p in parts):
        return ""
    return line.strip(" ।") if GAZ.find_districts(line) else ""


# ================================================================ 1. electricity
PBS_DISTRICT_ALIASES = {"jalampur": "Jamalpur", "kurgram lalmonirhat": "Kurigram", "kurgram - lalmonirhat": "Kurigram",
                        "kur-lalmoni": "Kurigram", "kur lalmoni": "Kurigram", "moulivibazar": "Moulvibazar",
                        "brahman baria": "Brahmanbaria", "chittagong": "Chattogram", "comilla": "Cumilla"}


def _pbs_key(name):
    n = nfc(name).replace("‐", "-").replace("–", "-").replace("—", "-")
    n = re.sub(r"(?i)\bpbss?\b|palli bidyut samity", " ", n).strip()
    m = re.search(r"(\d)\s*$", n)
    num = m.group(1) if m else ""
    base = re.sub(r"[-\s]*\d\s*$", "", n).strip(" -")
    d = PBS_DISTRICT_ALIASES.get(re.sub(r"\s+", " ", base.lower())) or GAZ.district(base)
    return d, num


ZONAL = re.compile(r"(সাব[-\s]?জোনাল|জোনাল|এরিয়া)\s*(অফিস|কার্যালয়)")


def _zonal_name(t):
    """'বোনারপাড়া জোনাল অফিস' -> the office name if the label names one place, else ''."""
    t = re.sub(r"^\s*[০-৯\d]{1,2}\s*[.)।]\s*", "", nfc(t)).strip(" :-।")     # list numbering '2. আড়পাড়া জোনাল অফিস'
    m = ZONAL.search(t)
    if not m or len(t) > 60:
        return ""
    pre = t[:m.start()].strip(" ,-")
    if not pre or len(pre.split()) > 4 or re.search(r"সকল|সমূহ|সমুহ|তালিকা|ও$|এবং|^\d+$|কর্মকর্তা|অধীন|আওতাধীন", pre) or t[m.end():].strip(" ,-।"):
        return ""
    return t


def _pbs_offices(pbs, base, home, dist):
    """Zonal / sub-zonal / area offices named in a PBS site's menu or on its office-list pages."""
    out, seen = [], set()
    pages = []
    for h, t in menu_links(home):
        u = urllib.parse.urljoin(base, h)
        if "/pages/static-pages/" not in u or host_of(u) != host_of(base):
            continue
        one = _zonal_name(t)
        if one:
            pages.append((u, one))
        elif re.search(r"জোনাল|উপজেলা কার্যালয়|উপজেলা অফিস|এরিয়া অফিস", t) and not re.search(r"কর্মকর্তা|জিআরএস|আপিল", t):
            pages.append((u, ""))
    done = set()
    for u, one in pages:
        if u in done:
            continue
        done.add(u)
        try:
            ls = plines(cv(get_page(u)))
        except RuntimeError as e:
            print("   ", pbs["name_en"], "office page failed:", str(e)[:120])
            continue
        if one:
            blocks = [(one, ls)]
        else:
            blocks, cur = [], None
            for x in ls:
                nm = _zonal_name(x)
                if nm:
                    cur = (nm, [])
                    blocks.append(cur)
                elif cur:
                    cur[1].append(x)
        for nm, blk in blocks:
            key = re.sub(r"\s+", "", nm)
            if key in seen:
                continue
            seen.add(key)
            addr = next((place_line(x) for x in blk[:4] if place_line(x)), "")
            body = " ".join(blk)
            ph = landlines(" ".join(x for x in blk if re.search(r"টেলিফোন|ফোন|Phone|Tel", x) and not re.search(r"মোবাইল|Mobile", x)))
            em = org_emails(body, ("reb.gov.bd",))
            kind = "sub_zonal_office" if re.search(r"সাব[-\s]?জোনাল", nm) else ("area_office" if "এরিয়া" in nm else "zonal_office")
            out.append(R("reb", kind, f"{host_of(base)}:{sid_hash(nm)}", u, name_bn=nm, category="government", proposed=UTIL,
                         address=addr, text=nm + " , " + addr, phone=ph, email=em, parent=dist, prefer="text",
                         prefix=(pbs["name_bn"] or pbs["name_en"]), extra={"pbs": pbs["name_en"], "pbs_website": base}))
    return out


@org("reb", "Bangladesh Rural Electrification Board (Palli Bidyut Samities)", "বাংলাদেশ পল্লী বিদ্যুতায়ন বোর্ড (পল্লী বিদ্যুৎ সমিতি)",
     "electricity", ["https://reb.gov.bd/pages/static-pages/6922dfe0933eb65569e24707",
                     "https://reb.gov.bd/pages/static-pages/6922e14b933eb65569e2b5d7"],      # + the 80 PBS sites it links
     domains=("reb.gov.bd",), prefix_en="REB", prefix_bn="পল্লী বিদ্যুৎ")
def reb():
    u_web = "https://reb.gov.bd/pages/static-pages/6922dfe0933eb65569e24707"
    u_hot = "https://reb.gov.bd/pages/static-pages/6922e14b933eb65569e2b5d7"
    hot = {}
    for c in table_rows(cv(get_page(u_hot))):
        c = [txt(x) for x in c]
        if len(c) >= 3 and asc(c[0]).strip(". ").isdigit():
            hot[_pbs_key(c[1])] = (c[1], any_phones(c[2]))      # col 4 (GM's mobile) is not used
    sites = []
    for c in table_rows(cv(get_page(u_web))):
        for i in range(0, len(c) - 1, 2):
            if not asc(txt(c[i])).strip(". ").isdigit():
                continue
            h = re.search(r'href="([^"]+)"', c[i + 1])
            if h:
                sites.append((txt(c[i + 1]), h.group(1).strip()))
    out = []
    for name, href in sites:
        base = "https://" + host_of(href) + "/"
        d_host = portal_place(base)[0]
        d_name, num = _pbs_key(name)
        hk = (d_host or d_name, num)
        hot_name, hotline = hot.get(hk, ("", ""))
        rec = R("reb", "pbs_head_office", host_of(base), u_web, name_en=name, category="government", proposed=UTIL,
                district=d_host or d_name or "", website=base, phone=hotline, text=name,
                extra={"hotline": hotline, "hotline_source": u_hot if hotline else None,
                       "name_on_hotline_list": hot_name if hot_name and hot_name != name else None})
        if not hotline:
            rec["notes"] = "Not found on REB's hotline list."
        try:
            home = get_page(base)
            t = re.search(r"(?is)<title>(.*?)</title>", home)
            title = nfc(_html.unescape(t.group(1))).split("|")[-1].strip() if t else ""
            if "পল্লী বিদ্যুৎ" in title:
                rec["name_bn"] = title
            rec["extra"]["site_title"] = title or None
            if PBS_OFFICES:
                out += _pbs_offices(rec, base, home, rec["district"])
        except RuntimeError as e:
            rec["notes"] = (rec["notes"] + " " if rec["notes"] else "") + "PBS website not reachable at collection time."
            print("   PBS site failed:", base, str(e)[:120])
        out.append(rec)
    return out


NESCO_AREA = ("Rajshahi", "Natore", "Naogaon", "Chapainawabganj", "Pabna", "Sirajganj", "Bogura", "Joypurhat", "Rangpur",
              "Dinajpur", "Thakurgaon", "Panchagarh", "Nilphamari", "Lalmonirhat", "Kurigram", "Gaibandha")


@org("bpdb", "Bangladesh Power Development Board", "বাংলাদেশ বিদ্যুৎ উন্নয়ন বোর্ড", "electricity",
     ["https://bpdb.gov.bd/pages/static-pages/6922df5d933eb65569e217db"], domains=("bpdb.gov.bd",), prefix_en="BPDB",
     prefix_bn="বিউবো")
def bpdb():
    """The distribution-zone page names the zones only (no addresses / offices); its office contacts are a PDF of officers'
    mobiles. Only the zone names are recorded, as facts for the report; no places are written."""
    u = "https://bpdb.gov.bd/pages/static-pages/6922df5d933eb65569e217db"
    ls = plines(cv(get_page(u)))
    i = next((k for k, x in enumerate(ls) if "Distribution Zones of BPDB" in x), None)
    zones = ls[i + 1:i + 8] if i is not None else []
    print("   BPDB zones named (not written as places):", zones)
    return []


@org("desco", "Dhaka Electric Supply Company Ltd (DESCO)", "ঢাকা ইলেকট্রিক সাপ্লাই কোম্পানি লিমিটেড (ডেসকো)", "electricity",
     ["https://desco.gov.bd/pages/static-pages/6922dd2f933eb65569e13d71",
      "https://desco.gov.bd/pages/static-pages/6922dbda933eb65569e0cfee"], domains=("desco.gov.bd", "desco.org.bd"),
     prefix_en="DESCO", prefix_bn="ডেসকো", area=("Dhaka", "Gazipur"), area_default="Dhaka")
def desco():
    out = []
    u = "https://desco.gov.bd/pages/static-pages/6922dd2f933eb65569e13d71"
    for c in table_rows(cv(get_page(u))):
        if len(c) < 3 or not re.match(r"^[০-৯\d]+\.?$", txt(c[0])):
            continue
        nl = lines(c[1])
        name, addr = nl[0], ", ".join(nl[1:])
        contact = " ".join(lines(c[-1]))
        ph = landlines(labelled(contact, r"Phone|ফোন", r"email|ই-মেইল|ইমেইল|Mobile|মোবাইল|[\w.]+@"))
        out.append(R("desco", "snd_division", "snd:" + sid_hash(name), u, name_bn=f"বিক্রয় ও বিতরণ বিভাগ, {name}", address=addr,
                     category="government", proposed=UTIL, phone=ph, email=org_emails(contact, ("desco.gov.bd",)), text=addr,
                     extra={"published_name": name, "circle": txt(c[2]) if len(c) >= 4 else None}))
    u = "https://desco.gov.bd/pages/static-pages/6922dbda933eb65569e0cfee"
    for c in table_rows(cv(get_page(u))):
        c = [txt(x) for x in c]
        if len(c) == 4 and re.match(r"^[০-৯\d]+$", c[0]):
            out.append(R("desco", "customer_service_centre", "csc:" + sid_hash(c[1]), u, name_bn=c[1], address=c[2],
                         category="emergency.utility_emergency", phone=any_phones(re.sub(r"[-\s]", "", asc(c[3]))), text=c[2],
                         extra={"desco_hotline": "16120"}))
    return out


@org("dpdc", "Dhaka Power Distribution Company Ltd (DPDC)", "ঢাকা পাওয়ার ডিস্ট্রিবিউশন কোম্পানি লিমিটেড (ডিপিডিসি)",
     "electricity", ["https://dpdc.org.bd/site/nocs/index_gov"], domains=("dpdc.gov.bd", "dpdc.org.bd"), prefix_en="DPDC",
     prefix_bn="ডিপিডিসি", area=("Dhaka", "Narayanganj"))
def dpdc():
    u = "https://dpdc.org.bd/site/nocs/index_gov"
    out = []
    for c in table_rows(strip_noise(get_page(u))):
        c = [txt(x) for x in c]
        if len(c) < 4 or not re.match(r"^\d+(\.\d+)*$", c[0]):
            continue
        num = asc(c[3])
        cr = re.findall(r"CR\s*-?\s*(\d{6,})", num)
        main = re.sub(r"CR\s*-?\s*\d{6,}", " ", num)
        out.append(R("dpdc", "nocs", "nocs:" + c[0], u, name_en=c[1], address=c[2], category="government", proposed=UTIL,
                     phone="; ".join(x for x in (landlines(main), "; ".join(cr)) if x), text=c[2],
                     extra={"list_number": c[0], "complaint_room": "; ".join(cr) or None}))
    return out


@org("nesco", "Northern Electricity Supply Company PLC (NESCO)", "নর্দান ইলেকট্রিসিটি সাপ্লাই কোম্পানি পিএলসি (নেসকো)",
     "electricity", ["https://customer.nesco.gov.bd/service-offices"], domains=("nesco.gov.bd",), prefix_en="NESCO",
     prefix_bn="নেসকো", area=NESCO_AREA, ordered=True)
def nesco():
    u = "https://customer.nesco.gov.bd/service-offices"
    out = []
    for c in table_rows(strip_noise(get_page(u))):
        if len(c) < 3 or not re.match(r"^[০-৯\d]+$", txt(c[0])):
            continue
        name = txt(c[1])
        comp = " ".join(lines(c[2]))
        cphone = "; ".join(x for x in (any_phones(labelled(comp, "মোবাইল", "ফোন|হটলাইন|ই-মেইল")),
                                         landlines(labelled(comp, "ফোন", "হটলাইন|ই-মেইল|মোবাইল"))) if x)
        one = " ".join(lines(c[3])) if len(c) > 3 else ""
        head = " ".join(lines(c[4])) if len(c) > 4 else ""
        office_ll = landlines(labelled(head, "ফোন", "ই-মেইল|মোবাইল"))
        em = org_emails(labelled(one, "ই-মেইল", "$"), ("nesco.gov.bd",))
        out.append(R("nesco", "snd_office", "office:" + sid_hash(name), u, name_bn=name, category="government", proposed=UTIL,
                     phone="; ".join(dict.fromkeys(x for x in (cphone, office_ll) if x)), email=em, text=name,
                     extra={"complaint_centre_phone": cphone or None, "hotline": "16603",
                            "complaint_email": org_emails(comp, ("nesco.gov.bd",)) or None,
                            "office_landline": office_ll or None}))
    return out


@org("wzpdco", "West Zone Power Distribution Company PLC (WZPDCO)", "ওয়েস্ট জোন পাওয়ার ডিস্ট্রিবিউশন কোম্পানি পিএলসি (ওজোপাডিকো)",
     "electricity", ["https://wzpdcl.gov.bd/pages/static-pages/6922dc49933eb65569e0f7f0"], domains=("wzpdcl.gov.bd", "wzpdcl.org.bd"),
     prefix_en="WZPDCO", prefix_bn="ওজোপাডিকো")
def wzpdco():
    u = "https://wzpdcl.gov.bd/pages/static-pages/6922dc49933eb65569e0f7f0"
    out = []
    for c in table_rows(cv(get_page(u))):
        hrefs = re.findall(r'href="(https?://[^"]+)"', "".join(c))
        c = [txt(x) for x in c]
        if len(c) < 5 or not re.match(r"^[০-৯\d]+$", c[0]):
            continue
        web = next((h for h in hrefs if "mailto" not in h), "") or (c[5] if len(c) > 5 and c[5].startswith("http") else "")
        out.append(R("wzpdco", "office", "office:" + sid_hash(c[1]), u, name_bn=c[1], category="government", proposed=UTIL,
                     phone=landlines(c[3]), email=org_emails(c[4], ("wzpdcl.gov.bd",)), website=web, host=web, text=c[1]))
    return out


# ================================================================ 2. water and gas
@org("dwasa", "Dhaka Water Supply and Sewerage Authority (Dhaka WASA)", "ঢাকা ওয়াসা", "water",
     ["https://dwasa.org.bd/pages/static-pages/মডস্-জোন-অফিসের-যোগাযোগের-তথ্য-p3iuhn-69f847ce05a019de7f02eab3",
      "https://dwasa.org.bd/pages/static-pages/রাজস্ব-জোন-অফিসের-যোগাযোগের-তথ্য-o17aho-69f8742958066bc85314903a"], domains=("dwasa.org.bd",), prefix_en="Dhaka WASA",
     prefix_bn="ঢাকা ওয়াসা")
def dwasa():
    out = []
    for kind, u in (("mods_zone", ORGS_BY["dwasa"]["urls"][0]), ("revenue_zone", ORGS_BY["dwasa"]["urls"][1])):
        for c in table_rows(cv(get_page(u))):
            c = [txt(x) for x in c]
            if len(c) >= 3 and re.search(r"জোন\s*-?\s*[০-৯\d]+", c[0]):
                # the zone's covered areas (column 2) are not the office address; officers (cols 3-5) are not used
                out.append(R("dwasa", kind, f"{kind}:{asc(re.sub(r'[^০-৯0-9]', '', c[0]))}", u,
                             name_bn=re.sub(r"\s+", " ", c[0]).replace("‌", ""),
                             category="emergency.water_sanitation" if kind == "mods_zone" else "government", proposed=UTIL,
                             district="Dhaka", extra={"areas_covered": c[1]},
                             notes="District from the authority's service area (Dhaka city); the list gives the zone's covered "
                                   "areas, not the zone office's address."))
    return out


@org("cwasa", "Chattogram Water Supply and Sewerage Authority (Chattogram WASA)", "চট্টগ্রাম ওয়াসা", "water",
     ["https://ctg-wasa.org.bd/pages/static-pages/6922dbf8933eb65569e0db79"], domains=("ctg-wasa.org.bd",),
     prefix_en="Chattogram WASA", prefix_bn="চট্টগ্রাম ওয়াসা")
def cwasa():
    u = "https://ctg-wasa.org.bd/pages/static-pages/6922dbf8933eb65569e0db79"
    ls = plines(cv(get_page(u)))
    out, cur = [], None
    for x in ls:
        if re.match(r"^মড-[০-৯\d]+.*জোন$", x):
            cur = R("cwasa", "mods_zone", "mods:" + asc(re.search(r"[০-৯\d]+", x).group(0)), u, name_bn=x,
                    category="emergency.water_sanitation", proposed=UTIL)
            out.append(cur)
        elif cur and "কার্যালয়" in x and "," in x and not cur["address"]:
            cur["address"] = x.strip(" ।")
            cur["text"] = cur["address"]
        elif cur and re.search(r"টেলিফোন", x):
            cur["phone"] = landlines(x)
    return out


GAS_DOMAINS = ("titasgas.org.bd", "titasgas.gov.bd")
TITAS_AREA = ("Dhaka", "Gazipur", "Narayanganj", "Narsingdi", "Munshiganj", "Manikganj", "Tangail", "Kishoreganj", "Mymensingh",
              "Netrokona", "Jamalpur", "Sherpur")


@org("titas", "Titas Gas Transmission and Distribution PLC", "তিতাস গ্যাস ট্রান্সমিশন অ্যান্ড ডিস্ট্রিবিউশন পিএলসি", "gas",
     ["https://titasgas.gov.bd/pages/static-pages/6922dc33933eb65569e0ef2f"], domains=GAS_DOMAINS, prefix_en="Titas Gas",
     prefix_bn="তিতাস গ্যাস", area=TITAS_AREA)
def titas():
    """Sales / revenue divisions (with address) and their branches, zonal sales offices (জোবিঅ) and emergency units. Officers'
    names and mobiles are not used; a division's e-mail is its head's post address on the company domain."""
    u = ORGS_BY["titas"]["urls"][0]
    out, cur = [], None
    for c in table_rows(cv(get_page(u))):
        if len(c) >= 5:
            if "দায়িত্বপ্রাপ্ত" in txt(c[0]):
                continue
            dl = lines(c[1])
            name = re.sub(r"\s+", " ", dl[0]) if dl else ""
            abbr = next((x.strip("()") for x in dl[1:] if x.startswith("(")), "")
            addr = next((re.sub(r"^ঠিকানা\s*[-:ঃ]\s*", "", x) for x in dl if x.startswith("ঠিকানা")), "")
            cur = R("titas", "division_office", "div:" + sid_hash(name), u, name_bn=name, address=addr.strip(" ।"),
                    category="government", proposed=UTIL, email=org_emails(" ".join(lines(c[0])), GAS_DOMAINS),
                    text=addr or name, extra={"abbreviation": abbr})
            out.append(cur)
            br = txt(c[2])
        elif len(c) == 3 and cur:
            br = txt(c[0])
        else:
            continue
        if not br:
            continue
        emerg = re.match(r"^জর[ুূ]রী", br)
        # the same branch name appears under a sales and a revenue division: the division is added to the name
        par = cur["extra"].get("abbreviation") or cur["name_bn"]
        out.append(R("titas", "emergency_unit" if emerg else "branch", "br:" + sid_hash(cur["name_bn"], br), u,
                     name_bn=f"{br} ({par})", category="emergency.utility_emergency" if emerg else "government", proposed="" if emerg else UTIL,
                     text=br, parent=cur["sid"], extra={"parent_office": cur["name_bn"], "branch_name": br}))
    return out


def _contact_blocks(u, domains, org_slug, heads):
    """Head office / liaison / regional offices from a gas company's contact page (label lines followed by address lines)."""
    ls = plines(cv(get_page(u)))
    out, cur, label = [], None, ""
    for x in ls:
        hm = re.match(r"^(%s)\s*[:ঃ]?\s*(.*)$" % heads, x)
        if hm:
            if not (cur and cur["name_bn"] == hm.group(1).strip() and not cur["address"]):
                cur = R(org_slug, "office", "office:" + sid_hash(hm.group(1)), u, name_bn=hm.group(1).strip(),
                        category="government", proposed=UTIL)
                out.append(cur)
            x = hm.group(2).strip(" ,")
            if not x:
                continue
        if not cur:
            continue
        lm = re.match(r"^(অফিসের ঠিকানা|ইমেইল|ই-মেইল|টেলিফোন|ফোন|ফ্যাক্স নং|ফ্যাক্স)\s*[:ঃ]\s*$", x)
        if lm:
            label = lm.group(1)
            continue
        if label:
            if label.startswith("ফ্যাক্স"):
                label = ""
                continue
            x = f"{label}: {x}" if label != "অফিসের ঠিকানা" else x
            label = ""
        x = re.sub(r"^অফিসের ঠিকানা\s*[:ঃ]\s*", "", x)
        if re.search(r"ফোন|টেলিফোন|Phone|ফ্যাক্স|ইমেইল|ই-মেইল|e-mail|ওয়েব", x, re.I):
            m = re.search(r"(?:ফোন|টেলিফোন|Phone)\s*(?:নং)?\s*[:ঃ]?\s*([+০-৯0-9\-\s,]+)", x)
            if m:
                cur["phone"] = "; ".join(dict.fromkeys(p for p in (cur["phone"], landlines(m.group(1))) if p))
            e = org_emails(x, domains)
            if e:
                cur["email"] = "; ".join(dict.fromkeys(p for p in (cur["email"], e) if p))
            pre = re.split(r"ইমেইল|ই-মেইল|e-mail|টেলিফোন|ফোন", x)[0].strip(" ,")
            if pre and len(cur["address"]) < 150 and not re.search(r"\d{6,}", asc(pre)):
                cur["address"] = (cur["address"] + ", " + pre).strip(", ")
        elif len(cur["address"]) < 150 and not re.match(r"^(বাংলাদেশ|Bangladesh)$", x):
            cur["address"] = (cur["address"] + ", " + x).strip(", ")
        cur["text"] = cur["address"]
    for r in out:
        r["address"] = re.sub(r"\s*,\s*", ", ", r["address"]).strip(" ,।")
    return out


@org("bgdcl", "Bakhrabad Gas Distribution Company Ltd", "বাখরাবাদ গ্যাস ডিস্ট্রিবিউশন কোম্পানী লিমিটেড", "gas",
     ["https://bgdcl.gov.bd/pages/static-pages/6922ddd9933eb65569e16a1c"], domains=("bgdcl.gov.bd", "bgdcl.org.bd"),
     prefix_en="Bakhrabad Gas", prefix_bn="বাখরাবাদ গ্যাস")
def bgdcl():
    return _contact_blocks(ORGS_BY["bgdcl"]["urls"][0], ("bgdcl.gov.bd", "bgdcl.org.bd"), "bgdcl", r"প্রধান কার্যালয়|ঢাকা লিয়াজোঁ অফিস")


@org("jgtdsl", "Jalalabad Gas Transmission and Distribution System PLC", "জালালাবাদ গ্যাস ট্রান্সমিশন অ্যান্ড ডিস্ট্রিবিউশন সিস্টেম পিএলসি",
     "gas", ["https://jgtdsl.gov.bd/pages/static-pages/6922dde4933eb65569e16eed"],
     domains=("jgtdsl.gov.bd", "jalalabadgas.org.bd"), prefix_en="Jalalabad Gas", prefix_bn="জালালাবাদ গ্যাস")
def jgtdsl():
    return _contact_blocks(ORGS_BY["jgtdsl"]["urls"][0], ("jgtdsl.gov.bd", "jalalabadgas.org.bd"), "jgtdsl",
                           r"প্রধান কার্যালয়|ঢাকা লিয়াজোঁ অফিস(?: \(ডিএলও\))?")


@org("kgdcl", "Karnaphuli Gas Distribution Company Ltd", "কর্ণফুলী গ্যাস ডিস্ট্রিবিউশন কোম্পানী লিমিটেড", "gas",
     ["https://kgdcl.gov.bd/pages/static-pages/6922dcb0933eb65569e118eb"], domains=("kgdcl.gov.bd",),
     prefix_en="Karnaphuli Gas", prefix_bn="কর্ণফুলী গ্যাস")
def kgdcl():
    return _contact_blocks(ORGS_BY["kgdcl"]["urls"][0], ("kgdcl.gov.bd",), "kgdcl", r"প্রধান কার্যালয়|ঢাকা লিয়াজোঁ অফিস")


@org("pgcl", "Pashchimanchal Gas Company Ltd", "পশ্চিমাঞ্চল গ্যাস কোম্পানী লিমিটেড", "gas",
     ["https://pgcl.gov.bd/pages/static-pages/6922dc62933eb65569e100b7"], domains=("pgcl.gov.bd", "pgcl.org.bd"),
     prefix_en="Pashchimanchal Gas", prefix_bn="পশ্চিমাঞ্চল গ্যাস")
def pgcl():
    u = ORGS_BY["pgcl"]["urls"][0]
    out = []
    for c in table_rows(cv(get_page(u))):
        if len(c) != 3 or txt(c[0]) == "অফিস":
            continue
        nl = lines(c[0])
        name = nl[0]
        cover = next((re.sub(r"^অধিভূক্ত অঞ্চলঃ?\s*", "", x) for x in nl[1:] if "অধিভূক্ত" in x), "")
        ct = " ".join(lines(c[2]))
        ph = landlines(re.sub(r"\((বিক্রয়|রাজস্ব|জরুরী সেবা)\)", " ", labelled(ct, "ফোন", "ইমেইল|ই-মেইল")))
        out.append(R("pgcl", "office", "office:" + sid_hash(name), u, name_bn=name, address=txt(c[1]).strip(" ।."),
                     category="government", proposed=UTIL, phone=ph, email=org_emails(ct, ("pgcl.gov.bd", "pgcl.org.bd")),
                     text=txt(c[1]) + " , " + name, extra={"area_covered": cover or None, "hotline": "16514",
                                                            "phone_labels": re.findall(r"\((বিক্রয়|রাজস্ব|জরুরী সেবা)\)", ct) or None}))
    return out


@org("sgcl", "Sundarban Gas Company Ltd", "সুন্দরবন গ্যাস কোম্পানী লিমিটেড", "gas",
     ["https://sgcl.gov.bd/pages/static-pages/6922e0cf933eb65569e28abe"], domains=("sgcl.gov.bd", "sgcl.org.bd"),
     prefix_en="Sundarban Gas", prefix_bn="সুন্দরবন গ্যাস")
def sgcl():
    u = ORGS_BY["sgcl"]["urls"][0]
    out = []
    for c in table_rows(cv(get_page(u))):
        h = re.search(r'href="([^"]+)"', "".join(c))
        if len(c) != 3 or not h:
            continue
        name = txt(c[1])
        du = urllib.parse.urljoin(u, h.group(1))
        t = " ".join(plines(cv(get_page(du))))
        addr = labelled(t, r"অফিসের ঠিকানা", r"ইমেইল|ই-মেইল|ফোন|মোবাইল")
        ph = landlines(labelled(t, r"টেলিফোন নং", r"গ্রাহক|ইমেইল|মোবাইল|$"))
        out.append(R("sgcl", "regional_office", "office:" + sid_hash(name), du, name_bn=name, address=addr.strip(" ।"),
                     category="government", proposed=UTIL, phone=ph, email=org_emails(t, ("sgcl.gov.bd", "sgcl.org.bd")),
                     text=addr + " , " + name))
    return out


# ================================================================ 3. other public offices with district / upazila lists
def resolve_sequence(recs, key="upazila_name"):
    """Lists ordered district by district that give only an upazila's English name (LGED): a name found in one seed
    district is placed there; a name found in several is placed in the one shared with its nearest unambiguous
    neighbours in the list (district_from 'sequence'), else left without a district."""
    cand = []
    for r in recs:
        n = r["extra"].get(key) or ""
        hits = set()
        exact = {d for d in GAZ.upz if upz_match(d, n) and GAZ.upazila(d, n)}
        hits = exact or {d for d in GAZ.upz if upz_match(d, n)}
        cand.append(hits)
    for i, r in enumerate(recs):
        c = cand[i]
        if len(c) == 1:
            r["district"] = next(iter(c))
            r["upazila"] = upz_match(r["district"], r["extra"][key]) or ""
            continue
        if not c:
            continue
        near = []
        for step in (-1, 1):
            j = i + step
            while 0 <= j < len(recs) and len(cand[j]) != 1:
                j += step
            if 0 <= j < len(recs):
                near.append(next(iter(cand[j])))
        pick = [d for d in dict.fromkeys(near) if d in c]
        if len(pick) == 1:
            r["district"], r["upazila"] = pick[0], upz_match(pick[0], r["extra"][key]) or ""
            r["how"] = "sequence"
            r["notes"] = (f"'{r['extra'][key]}' is an upazila name in several districts ({', '.join(sorted(c))}); "
                          f"{pick[0]} chosen because the list is ordered by district and its neighbours are in {pick[0]}.")


@org("lged", "Local Government Engineering Department (LGED)", "স্থানীয় সরকার প্রকৌশল অধিদপ্তর (এলজিইডি)", "public_office",
     ["https://lged.gov.bd/pages/static-pages/6922e059933eb65569e26a24"], domains=("lged.gov.bd",), prefix_en="LGED",
     prefix_bn="এলজিইডি")
def lged():
    """One row per office (division, region, district, upazila); its e-mail is the head's post address (first row of the
    office, e.g. xen.<district>@lged.gov.bd, ue.<upazila>@lged.gov.bd). The post-assigned mobile numbers are not used."""
    u = ORGS_BY["lged"]["urls"][0]
    offices = {}
    for c in table_rows(cv(get_page(u))):
        c = [txt(x) for x in c]
        if len(c) < 5 or not c[0].isdigit():
            continue
        office = re.sub(r"\s+", " ", c[1]).strip()
        m = re.match(r"^(.*?)\s+(Division|Region|District|Upazila)$", office, re.I)
        if not m:
            continue
        if office not in offices:
            offices[office] = R("lged", m.group(2).lower() + "_office", m.group(2).lower() + ":" + sid_hash(office), u,
                                name_en=office, category="government", proposed="government.engineering_office",
                                email=org_emails(c[4], ("lged.gov.bd",)), extra={"head_designation": c[2]})
    recs = list(offices.values())
    upz = []
    for r in recs:
        paren = re.search(r"\(([^)]{3,})\)", r["name_en"])     # '(Thakurgaon)', '(Zianagar)'; '(N)' / '(S)' stay in the name
        place_name = r["name_en"].replace(paren.group(0), " ") if paren else r["name_en"]
        base = re.sub(r"(?i)\s+(division|region|district|upazila)$", "", re.sub(r"\s+", " ", place_name)).strip()
        if r["kind"] == "district_office":
            r["district"] = base
        elif r["kind"] == "upazila_office":
            r["extra"]["upazila_name"] = base
            if paren:   # 'Pirganj (Thakurgaon) Upazila', 'Indurkani (Zianagar) Upazila'
                d = GAZ.district(paren.group(1))
                if d:
                    r["district"] = d
                    r["upazila"] = base
                else:
                    r["extra"]["alt_name"] = paren.group(1)
            if not r["district"]:
                upz.append(r)
        elif r["kind"] == "region_office":
            r["text"] = base
            r["notes"] = "Regional office placed in the district it is named after."
        elif r["kind"] == "division_office":
            r["text"] = base
            r["notes"] = "Divisional office placed in the division's head district (named after it)."
    resolve_sequence(upz)
    return recs


DSS_PAGES = {"barishal": "6922df92933eb65569e22d72", "chattogram": "6922dd57933eb65569e149a7", "dhaka": "6922de7e933eb65569e1b036",
             "khulna": "6922df2d933eb65569e205f1", "mymensingh": "6922e060933eb65569e26bf9", "rajshahi": "6922de80933eb65569e1b142",
             "rangpur": "6922e144933eb65569e2b31a", "sylhet": "6922df14933eb65569e1fb52"}


@org("dss", "Department of Social Services", "সমাজসেবা অধিদপ্তর", "public_office",
     [f"https://dss.gov.bd/pages/static-pages/{p}" for p in DSS_PAGES.values()], domains=("dss.gov.bd",),
     prefix_en="Department of Social Services", prefix_bn="সমাজসেবা অধিদপ্তর")
def dss():
    """The 'Upazila Social Services Officer (<division>)' pages list division, district, the office's official e-mail
    (usso.<upazila>@dss.gov.bd) and a post mobile (not used). The upazila is read from the e-mail address."""
    out = []
    for div, pid in DSS_PAGES.items():
        u = f"https://dss.gov.bd/pages/static-pages/{pid}"
        frag = cv(get_page(u))
        rows = [[txt(x) for x in c] for c in table_rows(frag)]
        if not rows:   # some pages are one text run: 'Division District e-mail cell …'
            rows = [list(m) for m in re.findall(r"(\w+)\s+([A-Za-z.'\s]+?)\s+([\w.\s-]+@dss\.gov\.bd)", txt(frag))]
        for c in rows:
            em = next((x for x in c if "@" in x), "")
            if not em or len(c) < 3:
                continue
            em_c = re.sub(r"\s+", "", em).lower()
            slug = re.sub(r"^u?sso\.|@.*$", "", em_c)
            dist_pub = c[1]
            d = GAZ.district(dist_pub)
            core = slug.split(".")[0]
            for dn in (d or "", dist_pub, {"Chattogram": "chittagong", "Cumilla": "comilla", "Bogura": "bogra",
                                           "Jashore": "jessore", "Barishal": "barisal"}.get(d or "", "")):
                dn = re.sub(r"[^a-z]", "", dn.lower())
                if dn and core.endswith(dn) and len(core) > len(dn) + 2:
                    core = core[:-len(dn)]
            upz = upz_match(d, core) if d else None
            if not upz and d and core.endswith("sadar"):
                upz = upz_match(d, core[:-5] + " sadar")
            nm_en = f"Upazila Social Services Office, {upz or slug.replace('-', ' ').title()}"
            out.append(R("dss", "upazila_office", "usso:" + em_c, u, name_en=nm_en, category="government", prefix="",
                         proposed="government.social_services_office", district=dist_pub, upazila=upz or "",
                         email=em_c if em_c.endswith("@dss.gov.bd") and " " not in em else em_c,
                         extra={"email_published": em if em != em_c else None, "upazila_from_email": slug,
                                "division_published": c[0]},
                         notes="Office name composed from the list's title ('উপজেলা সমাজসেবা অফিসার') and the upazila in its "
                               "official e-mail address." + ("" if upz else " The e-mail's upazila does not match a seed upazila.")))
    return out


@org("coop", "Department of Cooperatives", "সমবায় অধিদপ্তর", "public_office",
     ["https://coop.gov.bd/", "https://coop.gov.bd/pages/static-pages/affiliated-upazila-office-ovl2i4-6a9e33d3a719514fe71e1e17"],
     domains=("coop.gov.bd",), prefix_en="Department of Cooperatives", prefix_bn="সমবায় অধিদপ্তর")
def coop():
    out = []
    home = get_page("https://coop.gov.bd/")
    for h, t in menu_links(home):
        m = re.match(r"^জেলা কার্যালয়\s*,\s*(.+)$", t)
        if m and h.startswith("http"):
            out.append(R("coop", "district_office", "dist:" + host_of(h), "https://coop.gov.bd/",
                         name_bn=f"জেলা সমবায় কার্যালয়, {m.group(1).strip()}", category="government",
                         proposed="government.cooperative_office", district=m.group(1).strip(), website=h.strip(), host=h.strip(),
                         extra={"menu_title": t}))
    u = ORGS_BY["coop"]["urls"][1]
    dist = ""
    for c in table_rows(cv(get_page(u))):
        hrefs = [h for h in re.findall(r'href="(https?://[^"]+)"', "".join(c)) if "cooparative" in h or "coop" in h]
        c = [txt(x) for x in c]
        name_i = next((i for i, x in enumerate(c) if "কার্যালয়" in x), None)
        if name_i is None:
            continue
        for x in c[:name_i]:
            if GAZ.district(x) and x != "বিভাগ":
                dist = x
        name = re.sub(r"https?://\S+", "", c[name_i]).strip()
        if name.endswith("নাম") or "তালিকা" in name:      # table headings
            continue
        web = hrefs[-1] if hrefs else ""
        hd, hu = portal_place(web)
        upz_txt = name.split(",", 1)[1].strip() if "," in name else ""
        out.append(R("coop", "upazila_office", "upz:" + (host_of(web) if web else sid_hash(dist, name)), u, name_bn=name,
                     category="government", proposed="government.cooperative_office", district=dist, upazila=upz_txt, prefer="host",
                     website=web, host=web, text=name, extra={"district_published": dist or None}))
    return out


@org("fisheries", "Department of Fisheries", "মৎস্য অধিদপ্তর", "public_office",
     ["https://fisheries.gov.bd/pages/static-pages/6922ddb4933eb65569e15f2b",
      "https://fisheries.gov.bd/pages/static-pages/6922e12e933eb65569e2ab6f"], domains=("fisheries.gov.bd",),
     prefix_en="Department of Fisheries", prefix_bn="মৎস্য অধিদপ্তর")
def fisheries():
    out = []
    u = ORGS_BY["fisheries"]["urls"][0]
    for c in table_rows(cv(get_page(u))):
        hrefs = re.findall(r'href="(https?://[^"]+)"', "".join(c))
        c = [txt(x) for x in c]
        if len(c) < 4 or c[0] == "জেলা":
            continue
        web = next((h for h in hrefs if "fisheries" in h), "") or (c[2] if c[2].startswith("http") else "")
        out.append(R("fisheries", "district_office", "dist:" + (host_of(web) or sid_hash(c[1])), u, name_bn=c[1],
                     category="agriculture", proposed="agriculture.fisheries_office", district=c[0], website=web, host=web,
                     email=org_emails(c[3], ("fisheries.gov.bd",)), text=c[1],
                     notes="Listed by the head's designation ('জেলা মৎস্য কর্মকর্তা, <district>'), i.e. the District Fisheries Office."))
    u = ORGS_BY["fisheries"]["urls"][1]
    for c in table_rows(cv(get_page(u))):
        hrefs = re.findall(r'href="(https?://[^"]+)"', "".join(c))
        c = [txt(x) for x in c]
        if len(c) < 2 or not c[0].isdigit():
            continue
        web = hrefs[0] if hrefs else (c[2] if len(c) > 2 and c[2].startswith("http") else "")
        parts = [p.strip() for p in c[1].split(",")]
        out.append(R("fisheries", "upazila_office", "upz:" + (host_of(web) or sid_hash(c[1])), u, name_bn=c[1],
                     category="agriculture", proposed="agriculture.fisheries_office",
                     district=parts[-1] if len(parts) >= 3 else "", upazila=parts[-2] if len(parts) >= 3 else "",
                     website=web, host=web, text=c[1]))
    return out


# ================================================================ checked and not used (with the reason)
SKIPPED = [
    ("BPDB distribution offices", "https://bpdb.gov.bd/pages/static-pages/6922df5d933eb65569e217db",
     "the distribution-zone page names four zones only (Chittagong, Comilla, Sylhet, Mymenshing) with no offices or addresses; "
     "the zone contact list is a PDF of officers' mobile numbers"),
    ("PBS complaint centres (অভিযোগ কেন্দ্র)", "https://pbs.rajshahi.gov.bd/pages/static-pages/697fcfb135ce18e1c06d494b",
     "each of the 80 PBS sites words them differently (free text, mixed tables, one page per zonal office listing staff); "
     "only REB's PBS hotline list and the zonal / sub-zonal offices named in the PBS sites' menus and office-list pages are used"),
    ("Rajshahi WASA", "https://rwasa.org.bd/", "domain does not resolve (rwasa.org.bd / rwasa.gov.bd), no other official site found"),
    ("Narayanganj WASA", "", "no official website found"),
    ("Khulna WASA", "https://kwasa.gov.bd/", "the site has no zone-office or contact list (menu 'যোগাযোগ' is empty)"),
    ("DPHE district / upazila offices", "https://dphe.gov.bd/", "no office list on the department's site (only the head office address)"),
    ("BRTA circle offices", "https://brta.gov.bd/pages/static-pages/6922dfea933eb65569e24a4d",
     "the divisional circle lists are PDF attachments only (stdlib + requests collector: PDFs not parsed)"),
    ("Department of Livestock Services", "https://dls.gov.bd/pages/static-pages/6922df7c933eb65569e224c0",
     "division / district / upazila office lists and domain-mail lists are PDF attachments only"),
    ("Department of Youth Development", "https://dyd.gov.bd/pages/static-pages/6922e039933eb65569e26112",
     "64 district offices and the e-mail list are PDF attachments; the 'web portal links' page links to further pages per division only"),
    ("Department of Women Affairs", "https://dwa.gov.bd/", "upazila officer / programme officer lists are PDF attachments only"),
    ("Bangladesh Election Commission", "https://ecs.gov.bd/robots.txt",
     "robots.txt blocks ClaudeBot / anthropic-ai and sets 'Content-Signal: ai-train=no'; not collected (no office list was found on "
     "the two pages read before the robots.txt was checked)"),
    ("Union Digital Centres", "https://a2i.gov.bd/", "no public national list of centre locations found (entrepreneur lists are out of scope)"),
    ("BADC", "https://badc.gov.bd/", "no office list (only officer lists and projects)"),
    ("BSCIC", "https://bscic.gov.bd/pages/static-pages/6922e141933eb65569e2b218",
     "regional / district office addresses and phones are a PDF attachment; the district-office page links only to staff lists"),
    ("NGO Affairs Bureau registered NGOs", "https://ngoab.gov.bd/pages/static-pages/6922e0d3933eb65569e28beb",
     "the list of registered NGOs is a PDF attachment only"),
    ("DESCO www host", "https://www.desco.gov.bd/", "TLS certificate does not cover www.desco.gov.bd; desco.gov.bd used instead"),
]


# ---------------------------------------------------------------- placement and output
GAZ = None
ORGS_BY = {}
NO_UPAZILA_KINDS = {"district_office", "region_office", "division_office", "pbs_head_office"}


BN_LOCALITIES = {   # metropolitan localities that are not seed upazilas (looked up only within a utility's service area)
    "Dhaka": ["মিরপুর", "কাফরুল", "পল্লবী", "উত্তরা", "গুলশান", "বারিধারা", "বাড্ডা", "খিলক্ষেত", "নিকুঞ্জ", "আগারগাঁও",
              "শের-ই-বাংলা নগর", "শেরেবাংলা নগর", "দক্ষিণখান", "উত্তরখান", "বসুন্ধরা", "রূপনগর", "শাহ আলী", "শাহআলী",
              "জোয়ারসাহারা", "বনানী", "মহাখালী", "তেজগাঁও", "মতিঝিল", "ক্যান্টনমেন্ট", "ইব্রাহীমপুর", "মণিপুর", "মনিপুর",
              "তুরাগ", "শাহ কবির", "শাহ্‌ কবির", "কল্যাণপুর", "দারুসসালাম", "ইস্টার্ন হাউজিং", "আফতাব নগর", "মোহাম্মদপুর",
              "ধানমন্ডি", "লালবাগ", "ডেমরা", "যাত্রাবাড়ী", "শ্যামপুর", "গেন্ডারিয়া", "দনিয়া", "ওয়ারী", "ওয়ারি", "রমনা",
              "টিকাটুলী", "সূত্রাপুর", "খিলগাঁও", "রামপুরা", "বাসাবো", "মগবাজার", "কাওরান বাজার", "কারওয়ানবাজার", "হাজারীবাগ",
              "কামরাঙ্গীরচর", "মিরপুর", "শ্যামলী", "আদাবর", "আজিমপুর", "চকবাজার", "কোতয়ালী", "বংশাল", "পোস্তগোলা"],
    "Gazipur": ["টঙ্গী", "জয়দেবপুর", "চন্দ্রা", "কোনাবাড়ী", "বোর্ডবাজার", "ভোগড়া"],
    "Narayanganj": ["ফতুল্লা", "সিদ্ধিরগঞ্জ", "মেঘনাঘাট", "সোনারগাঁও", "সোনারগাঁ", "চাষাড়া", "কাঁচপুর", "ভুলতা"],
    "Rajshahi": ["কাশিয়াডাঙ্গা", "বোয়ালিয়া", "রাজপাড়া", "শাহ মখদুম", "মতিহার"],
    "Bogura": ["সান্তাহার"],
}


_NEAR = {}


def near_districts(a, b, margin=0.03):
    """True when district b is a or touches it (bounding boxes of their polygons overlap, with a small margin)."""
    if a == b:
        return True
    if (a, b) not in _NEAR:
        ba = [p[:4] for p in GAZ.polys if p[5] == a]
        bb = [p[:4] for p in GAZ.polys if p[5] == b]
        _NEAR[(a, b)] = any(x0 - margin <= X1 and X0 <= x1 + margin and y0 - margin <= Y1 and Y0 <= y1 + margin
                            for x0, y0, x1, y1 in ba for X0, Y0, X1, Y1 in bb)
    return _NEAR[(a, b)]


def bn_locality(text, area):
    k = bkey(text)
    hits = [d for d, names in BN_LOCALITIES.items() if d in area and any(bkey(n) in k for n in names)]
    return hits[0] if len(set(hits)) == 1 else None


def place(rec, by_sid):
    """(district, upazila, notes, how) of a normalised record."""
    notes = []
    field_d = GAZ.district(rec["district"]) if rec["district"] else None
    host_d, host_u = portal_place(rec["host"]) if rec["host"] else (None, None)
    hits = GAZ.find_districts(rec["text"] or rec["address"] or rec["name_bn"] or rec["name_en"])
    text_d = hits[-1] if hits else None
    order = {"field": [("field", field_d), ("host", host_d), ("text", text_d)],
             "host": [("host", host_d), ("field", field_d), ("text", text_d)],
             "text": [("text", text_d), ("field", field_d), ("host", host_d)]}[rec["prefer"]]
    dist, how = None, rec.get("how") or ""
    for h, v in order:
        if v:
            dist, how = v, how or h
            break
    blob = " , ".join(x for x in (rec["upazila"], rec["text"] or rec["address"] or rec["name_bn"] or rec["name_en"]) if x)
    upz = None
    home = rec["parent"] if rec["parent"] in GAZ.div_of else None
    if not dist and home:
        u = GAZ.find_upazila(home, blob)
        if u:
            dist, upz, how = home, u, "home_district_upazila"
            notes.append(f"Placed by the upazila named ({u}) within the {home} district of its parent organisation.")
    area = ORGS_BY[rec["org"]]["area"]
    if dist and area and dist not in area and how != "field":
        notes.append(f"The name/address points to {dist}, outside the organisation's service area; not used.")
        dist, how = None, ""
    if not dist and area:
        d = bn_locality(blob, area)
        if d:
            dist, how = d, "locality"
            notes.append("District from a metropolitan locality named in the address (within the utility's service area).")
    if not dist:
        hit = GAZ.by_upazila(blob)
        if hit and home and not near_districts(home, hit[0]):
            hit = None      # a PBS office named like an upazila far away ('বাগমারা' of Cumilla PBS-2 is not Bagmara, Rajshahi)
        if hit and (not area or hit[0] in area):
            (dist, upz), how = hit, "upazila"
            notes.append(f"District from the upazila named ({upz}), whose name is unique in the country.")
    if not dist:
        d = GAZ.by_locality(blob)
        if d:
            dist, how = d, "locality"
            notes.append("District from a well-known metropolitan locality named in the address.")
    if not dist and rec["parent"] and rec["parent"] in by_sid:
        d = by_sid[rec["parent"]]
        if d:
            dist, how = d, "parent"
            notes.append("District of the office it belongs to (the list names no place for it).")
    if not dist and ORGS_BY[rec["org"]]["area_default"]:
        dist, how = ORGS_BY[rec["org"]]["area_default"], "service_area"
        notes.append(f"The address names no district; {dist} is the main district of the company's published service area.")
    if dist and field_d and text_d and field_d != text_d:
        notes.append(f"The list's district is {field_d} but the name/address names {text_d}; {dist} used.")
    if dist and field_d and host_d and field_d != host_d:
        notes.append(f"The list's district is {field_d} but the office website is under {host_d}; {dist} used.")
    if rec["district"] and (not field_d or field_d != rec["district"]):
        rec["extra"].setdefault("district_published", rec["district"])
    if dist and not upz and rec["kind"] not in NO_UPAZILA_KINDS:
        if rec["upazila"]:
            upz = upz_match(dist, rec["upazila"])
            if rec["upazila"] != upz:
                rec["extra"].setdefault("upazila_published", rec["upazila"])
        if not upz and host_u and host_d == dist:
            upz = host_u
        if not upz and rec["kind"] not in ("office",):
            upz = GAZ.find_upazila(dist, rec["text"] or rec["address"] or rec["name_bn"])
    return dist, upz, notes, how


def _mentions(name, o):
    n = name.lower()
    words = [w.lower().strip(".,()") for w in (o["prefix_en"].split()[:1] + o["prefix_bn"].split()[:1])]
    return any(w and w in n for w in words)


def build_rows(recs):
    by_div, unplaced, seen, by_sid = {}, {}, set(), {}
    placed = []
    for r in recs:
        res = place(r, by_sid)
        by_sid[r["sid"]] = res[0]
        placed.append([r, res])
    for i, (r, res) in enumerate(placed):       # ordered lists: an ambiguous upazila name takes its neighbours' district
        o = ORGS_BY[r["org"]]
        if res[0] or not o["ordered"]:
            continue
        cands = {d for d in (o["area"] or GAZ.upz) if GAZ.find_upazila(d, r["text"] or r["name_bn"])}
        near = []
        for step in (-1, 1):
            j = i + step
            while 0 <= j < len(placed) and placed[j][0]["org"] == r["org"] and not placed[j][1][0]:
                j += step
            if 0 <= j < len(placed) and placed[j][0]["org"] == r["org"]:
                near.append(placed[j][1][0])
        pick = [d for d in dict.fromkeys(near) if d in cands]
        if len(pick) == 1:
            u = GAZ.find_upazila(pick[0], r["text"] or r["name_bn"])
            placed[i][1] = (pick[0], u, res[2] + [f"'{u}' is an upazila name in several districts ({', '.join(sorted(cands))}); "
                                                  f"{pick[0]} chosen because the list is ordered by area and its neighbours are "
                                                  f"in {pick[0]}."], "sequence")
    for r, (dist, upz, notes, how) in placed:
        o = ORGS_BY[r["org"]]
        if not dist:
            unplaced.setdefault(r["org"], []).append(r["name_bn"] or r["name_en"])
            continue
        div = GAZ.div_of[dist]
        sid = f"{r['org']}:{r['sid']}"
        base, n = sid, 2
        while sid in seen:
            sid = f"{base}#{n}"
            n += 1
        seen.add(sid)
        ex = dict(r["extra"])
        ex.update(organisation=o["name_en"], organisation_bn=o["name_bn"], office_kind=r["kind"])
        if r["proposed"]:
            ex["proposed_category"] = r["proposed"]
        if how:
            ex["district_from"] = how
        nm_en, nm_bn = re.sub(r"\s+", " ", r["name_en"] or "").strip(" ,"), re.sub(r"\s+", " ", r["name_bn"] or "").strip(" ,")
        if r["prefix"] is not None:
            if r["prefix"]:
                if nm_bn:
                    ex["published_name"] = nm_bn
                    nm_bn = f"{r['prefix']}, {nm_bn}"
                if nm_en:
                    ex["published_name_en"] = nm_en
                    nm_en = f"{r['prefix']}, {nm_en}" if not re.search(r"[ঀ-৿]", r["prefix"]) else nm_en
        else:
            if nm_en and not _mentions(nm_en, o):
                ex["published_name_en"] = nm_en
                nm_en = f"{o['prefix_en']}, {nm_en}"
            if nm_bn and not _mentions(nm_bn, o):
                ex["published_name"] = nm_bn
                nm_bn = f"{o['prefix_bn']}, {nm_bn}"
        note = " ".join(["Office as listed by the organisation on its own website."] + notes + ([r["notes"]] if r["notes"] else []))
        by_div.setdefault(div, []).append(dict(
            source_key=keyname(div), source_id=sid, name_bn=nfc(nm_bn), name_en=nfc(nm_en), category_key=r["category"],
            lat="", lon="", address=nfc(r["address"]), district_en=dist, upazila_en=upz or "", phone=r["phone"],
            website=r["website"], email=r["email"], opening_hours=r["hours"], operator=o["name_en"], ownership=o["ownership"],
            extra_json=xj(ex), source_url=r["url"], notes=note))
    return by_div, unplaced


def keyname(div):
    return f"LOCAL_SERVICES_{DIVISIONS[div].upper()}_2026"


def folder(div):
    return f"local_services_{DIVISIONS[div]}_2026"


def write_division(div, rows, out, results, unplaced, today):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rows.sort(key=lambda r: r["source_id"])
    with open(out / "places.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=PLACE_COLS)
        w.writeheader()
        w.writerows(rows)
    urls = []
    for o in ORGS:
        if results.get(o["slug"], {}).get("status") == "ok" and results[o["slug"]]["n"]:
            urls += [u for u in o["urls"] if u not in urls]
    meta = dict(
        key=keyname(div), division=div, kind="local_services",
        name=f"Local public-service offices (utilities, engineering, social services, cooperatives, fisheries) — {div.title()} Division",
        organization="Various government departments and state-owned utilities (each row's organisation in extra_json.organisation)",
        source_type="government_portal", trust_level=4, urls=urls, accessed=today, publication_date=None,
        license=None, license_url=None,
        attribution="Office lists published by the departments and state-owned utilities on their own websites (see urls)",
        notes=("REB rows also use the 80 PBS websites (pbs[N].<district>.gov.bd) linked from REB's PBS list. "
               "Each row is an office exactly as its organisation lists it (state-owned utilities' own sites counted as government). "
               "District/upazila normalised to the seed's English names (published values in extra_json). No coordinates are "
               "published by these lists. Only office names, addresses, office landlines, complaint-centre / hotline / customer-"
               "service numbers and official e-mails are kept; officers' names and mobiles are never collected. Categories are "
               "the closest existing keys; extra_json.proposed_category holds a proposed sub-key. No licence stated: factual "
               "data only. Checked and not used: " + "; ".join(f"{n} ({why})" for n, u, why in SKIPPED) + "."),
        files={"places.csv": hashlib.sha256((out / "places.csv").read_bytes()).hexdigest()})
    (out / "SOURCE.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(div, rows, out, results, unplaced, today)
    print(f"{div}: {len(rows)} rows -> {out}")


def report_text(div, rows, results, unplaced, today):
    cat_tot, org_cat = {}, {}
    for r in rows:
        cat_tot[r["category_key"]] = cat_tot.get(r["category_key"], 0) + 1
        o = json.loads(r["extra_json"])["organisation"]
        org_cat.setdefault(o, {}).setdefault(r["category_key"], 0)
        org_cat[o][r["category_key"]] += 1
    with_upz = sum(1 for r in rows if r["upazila_en"])
    with_ph = sum(1 for r in rows if r["phone"])
    with_em = sum(1 for r in rows if r["email"])
    L = [f"# {keyname(div)} — local public-service offices, {div.title()} Division", "",
         f"Generated by `fetch.py --division {div}` (or `--all-divisions`) on {today}. Source type `government_portal`, trust "
         "level 4: every row is an office **as listed by its own organisation** on its official website (government departments "
         "and state-owned utilities); the organisation is in `operator` and `extra_json.organisation`.", "",
         f"**{len(rows)} offices**: " + (", ".join(f"{k} {v}" for k, v in sorted(cat_tot.items())) or "none") +
         f". {with_upz} with an upazila, {with_ph} with a phone, {with_em} with an official e-mail; none with coordinates "
         "(no list publishes them).", "",
         "## By organisation", "", "| Organisation | Rows in this division | National list | Without a district |", "|---|---|---|---|"]
    for o in ORGS:
        res = results.get(o["slug"])
        if not res:
            continue
        c = org_cat.get(o["name_en"], {})
        nat = (f"{res['n']} records" if res["status"] == "ok" else "failed: " + res["error"])
        L.append(f"| {o['name_en']} | {sum(c.values())} ({', '.join(f'{k} {v}' for k, v in sorted(c.items())) or '—'}) | {nat} | "
                 f"{len(unplaced.get(o['slug'], []))} |")
    L += ["", "## How rows were placed", "",
          "- District: the list's own district field (spelling normalised to `data/seed/geo/admin_areas.csv`; published value "
          "kept as `district_published`), else the district of the office's national-portal host "
          "(`<office>.<upazila>.<district>.gov.bd`), else the last district named in the name / address; then, only if none "
          "names a district: an upazila of the parent organisation's district named in the office name (PBS zonal offices), "
          "a seed upazila whose name is unique in the country, a well-known metropolitan locality, or the parent office "
          "(Titas branches). LGED's upazila list gives English upazila names only: names found in several districts are "
          "placed by their neighbours in the district-ordered list (`district_from: sequence`, with a note). "
          "`extra_json.district_from` says which rule placed each row. Rows with no district are left out (counted above).",
          "- Upazila: the list's upazila field or the portal host's upazila label, matched within the district; else a seed "
          "upazila named in the office name / address. Division, region and district offices get no upazila.",
          "- Names: as published; the organisation's short name is prefixed when the published name lacks it (published "
          "name kept in `extra_json.published_name` / `published_name_en`). DESCO's sales-and-distribution rows are "
          "'বিক্রয় ও বিতরণ বিভাগ, <name>' (the table's column heading + the name). DSS rows are named from the list's "
          "title and the upazila in the office's official e-mail (see `upazila_from_email`).",
          "", "## Categories", "",
          "Existing keys only: `government` (offices), `emergency.utility_emergency` (DESCO customer-service centres, Titas "
          "emergency units), `emergency.water_sanitation` (WASA maintenance-and-operation zones), `agriculture` (fisheries "
          "offices). Proposed sub-keys, in `extra_json.proposed_category`: `government.utility_office` (electricity / gas / "
          "water offices), `government.engineering_office` (LGED), `government.social_services_office` (DSS), "
          "`government.cooperative_office`, `agriculture.fisheries_office`.",
          "", "## Privacy filters", "",
          "Not collected: officers' names and designations (DESCO, DPDC, Titas, WASA and NESCO tables, PBS zonal pages), "
          "officers' and post-assigned mobiles (REB's GM mobiles, LGED, DSS, WZPDCO, DPDC, Titas, fisheries 'corporate SIM'), "
          "and e-mails that are not on *.gov.bd or the organisation's own domain (e.g. PBS gmail addresses). Mobiles are kept "
          "only where the organisation publishes them as an office's hotline / complaint-centre / customer-service number "
          "(PBS hotlines, NESCO complaint centres, DESCO customer-service centres).",
          "", "## Checked and not used", ""]
    L += [f"- **{n}**: {why}" + (f" ({u})" if u else "") for n, u, why in SKIPPED]
    L += ["", "## Data-quality notes", "",
          "- Lists are as current as each website (Nov 2026); some pages were last edited years ago (DSS 2017, fisheries 2021, "
          "REB's hotline list 2022). LGED's mobile/e-mail list is dated March 2024.",
          "- DWASA's zone pages give the areas a zone covers (kept as `areas_covered`), not the zone office's address.",
          "- PBS zonal / sub-zonal offices are named after a bazaar, union or upazila; those whose name or address does not "
          "identify a seed district (about a quarter, e.g. 'চন্দ্রগঞ্জ জোনাল অফিস') are left out rather than given the PBS's "
          "district. A PBS head office's own address is not on REB's lists, so head offices have a district (from the PBS "
          "name / website) but no address or upazila. pbs1.sylhet.gov.bd and pbs2.sylhet.gov.bd failed TLS verification "
          "(not fetched without verification): their head offices are listed from REB's pages only.",
          "- Titas lists the same branch name under a sales and a revenue division; the division's abbreviation is added to "
          "the branch name (`branch_name` keeps the published one). Branch / zonal-office rows have no address.",
          "- `raw/` is not committed: the pages carry officers' names and mobiles. `fetch.py` rebuilds everything (≈ 15 min; "
          "the 80 PBS sites are read one after another at ≥ 1.2 s per host).",
          "", "## Licence", "", "No site states a licence. Only facts (office names, addresses, contacts, websites) are taken.", ""]
    return "\n".join(L)


def write_report(div, rows, out, results, unplaced, today):
    (Path(out) / "REPORT.md").write_text(report_text(div, rows, results, unplaced, today), encoding="utf-8")


def main():
    global GAZ, HTTP_CACHE, PBS_OFFICES, ORGS_BY
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().split("\n")[0])
    ap.add_argument("--division", default="rajshahi", choices=list(DIVISIONS))
    ap.add_argument("--all-divisions", action="store_true")
    ap.add_argument("--out", help="output folder (with --all-divisions: a parent folder for the eight division folders)")
    ap.add_argument("--only", help="comma-separated organisation slugs")
    ap.add_argument("--cache", help="folder for normalised national lists (reused when present)")
    ap.add_argument("--http-cache", help="development: folder for raw HTTP responses")
    ap.add_argument("--no-pbs-offices", action="store_true", help="skip the PBS sites' zonal-office pages")
    a = ap.parse_args()
    PBS_OFFICES = not a.no_pbs_offices
    if a.http_cache:
        HTTP_CACHE = a.http_cache
        os.makedirs(HTTP_CACHE, exist_ok=True)
    GAZ = Gazetteer()
    ORGS_BY = {o["slug"]: o for o in ORGS}
    today = datetime.date.today().isoformat()
    only = set(a.only.split(",")) if a.only else None
    recs, results = [], {}
    for o in ORGS:
        if only and o["slug"] not in only:
            continue
        cf = os.path.join(a.cache, o["slug"] + ".json") if a.cache else None
        try:
            if cf and os.path.exists(cf):
                got = json.load(open(cf, encoding="utf-8"))
            else:
                print("fetching", o["slug"], flush=True)
                got = o["fn"]()
                if cf:
                    os.makedirs(a.cache, exist_ok=True)
                    json.dump(got, open(cf, "w", encoding="utf-8"), ensure_ascii=False)
            results[o["slug"]] = dict(status="ok", n=len(got))
            recs += got
            print(f"  {o['slug']}: {len(got)}", flush=True)
        except Exception as e:
            results[o["slug"]] = dict(status="failed", error=str(e)[:300], n=0)
            print(f"  {o['slug']} FAILED: {e}", flush=True)
            traceback.print_exc(limit=3)
    by_div, unplaced = build_rows(recs)
    divs = list(DIVISIONS) if a.all_divisions else [a.division]
    for div in divs:
        if a.out:
            out = Path(a.out) / folder(div) if a.all_divisions else a.out
        else:
            out = HERE if div == "rajshahi" else HERE.parent / folder(div)
        write_division(div, by_div.get(div, []), out, results, unplaced, today)
    print("without district:", {k: len(v) for k, v in unplaced.items()})
    for k, v in unplaced.items():
        print("  ", k, v[:12])


if __name__ == "__main__":
    main()
