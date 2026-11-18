#!/usr/bin/env python3
"""Organisations' own branch / outlet lists (banks, operators, couriers, health and retail chains, NGOs), split by division.

Usage:
  python3 fetch.py [--division rajshahi|rangpur|dhaka|chattogram|khulna|barishal|sylhet|mymensingh] [--out DIR]
  python3 fetch.py --all-divisions            # fetch every national list once, write all 8 division folders
  options: --only sonali,janata …  (subset of organisations)   --cache DIR  (reuse/keep normalised national lists)
           --http-cache DIR (development: reuse raw HTTP responses)   --no-details (skip the slow per-branch detail pages)

Keys: ORG_BRANCHES_RAJ_2026, ORG_BRANCHES_RANG_2026, ORG_BRANCHES_DHK_2026, ORG_BRANCHES_CTG_2026, ORG_BRANCHES_KHL_2026,
ORG_BRANCHES_BAR_2026, ORG_BRANCHES_SYL_2026, ORG_BRANCHES_MYM_2026 (folders org_branches_<code>_2026, kind "org_branches").
Every row is a place as published by the organisation on its own website (not independently verified); the organisation is
named in extra_json.organisation. Staff names, managers' / agents' mobiles and personal e-mails are never written.
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


# ---------------------------------------------------------------- record model
def R(org, kind, sid, url, **kw):
    """One normalised record before placement. Fields: name_en name_bn category address district upazila division
    lat lon phone email hours code routing extra notes parent text (extra free text used only for placement)."""
    d = dict(org=org, kind=kind, sid=str(sid), url=url, name_en="", name_bn="", category="finance.bank", address="",
             district="", upazila="", division="", lat=None, lon=None, phone="", email="", hours="", code="", routing="",
             extra={}, notes="", parent="", text="", prefer="field")
    d.update({k: v for k, v in kw.items() if v is not None})
    return d


ORGS = []   # filled by @org


def org(slug, name_en, name_bn, group, urls, operator_type="private"):
    def deco(fn):
        ORGS.append(dict(slug=slug, name_en=name_en, name_bn=name_bn, group=group, urls=urls, fn=fn, ownership=operator_type))
        return fn
    return deco


DETAILS = True


# ================================================================ a. banks — state-owned and specialised
@org("sonali", "Sonali Bank PLC", "সোনালী ব্যাংক পিএলসি", "bank",
     ["https://www.sonalibank.com.bd/atm_location.php", "https://www.sonalibank.com.bd/ad_branch.php"], "public")
def sonali():
    # The full branch list (inland_branch.php) is an iframe of /feedback/…, which robots.txt disallows: not used.
    u = "https://www.sonalibank.com.bd/atm_location.php"
    out = []
    for tr in re.findall(r"(?s)<tr>(<td>\d+</td>.*?)</tr>", get(u).text):
        c = [txt(x) for x in re.findall(r"(?s)<td>(.*?)</td>", tr)]
        ll = re.search(r"maps\?q=(-?[\d.]+),(-?[\d.]+)", tr)
        # the page's column headings 'DIVISION' / 'CITY' hold the district / the division
        out.append(R("sonali", "atm", "atm:" + c[1], u, name_en=c[2], category="finance.atm", district=c[4], division=c[5],
                     lat=ll and fnum(ll[1]), lon=ll and fnum(ll[2]), code=c[1], parent=c[3], text=c[3] + " , " + c[2],
                     extra={"atm_code": c[1], "related_branch": c[3]}))
    u = "https://www.sonalibank.com.bd/ad_branch.php"
    for tr in trs(strip_noise(get(u).text)):
        c = [txt(x) for x in tds(tr)]
        if len(c) == 6 and c[0].isdigit():
            out.append(R("sonali", "ad_branch", "ad:" + c[5] if c[5] else "ad:" + sid_hash(c[1]), u, name_en=c[1].title(),
                         district=c[2], address=c[3], phone=phones(c[4]), text=c[3],
                         extra={"swift": c[5], "branch_type": "Authorised Dealer (AD) branch"}))
    return out


@org("janata", "Janata Bank PLC", "জনতা ব্যাংক পিএলসি", "bank",
     ["https://pmis.janatabank-bd.com/branchinfo.aspx", "https://www.jb.com.bd/services/atm_list"], "public")
def janata():
    u = "https://pmis.janatabank-bd.com/branchinfo.aspx"
    first = get(u).text
    f = dict(re.findall(r'name="(__\w+)" id="\w+" value="([^"]*)"', first))
    f.update(__EVENTTARGET="cboBranchCategory", __EVENTARGUMENT="", cboBranchCategory="01")   # 01 = all branches
    page = post(u, data=f).text
    out = []
    for tr in trs(page[page.find('id="gvList"'):]):
        c = tds(tr)
        if len(c) != 10:
            continue
        c0 = [txt(x) for x in c]
        if not c0[0].isdigit():
            continue
        nm = lines(c[2])
        en, bn = nm[0], (nm[1] if len(nm) > 1 else "")
        out.append(R("janata", "branch", "br:" + c0[1], u, name_en=en, name_bn=bn, code=c0[1], routing=c0[3], address=c0[4],
                     phone=phones(c0[7]), email=emails(c0[8]), text=" , ".join([en.split(",")[-1], bn.split(",")[-1], c0[4]]),
                     prefer="text", extra={"swift": c0[9], "jb_division": c0[5], "jb_area": c0[6]}))
    u2 = "https://www.jb.com.bd/services/atm_list"
    for tr in re.findall(r"(?s)<tr>(.*?)</tr>", get(u2).text):
        c = [txt(x) for x in tds(tr)]
        if len(c) == 4 and c[0].isdigit():
            m = re.findall(r"!3d(-?[\d.]+)!4d(-?[\d.]+)", tr) or re.findall(r"@(-?[\d.]+),(-?[\d.]+)", tr)
            out.append(R("janata", "atm", "atm:" + sid_hash(c[1], c[2]), u2, name_en=c[1] + " ATM", category="finance.atm",
                         address=c[2], text=c[2], parent=c[1], lat=fnum(m[-1][0]) if m else None, lon=fnum(m[-1][1]) if m else None,
                         extra={"related_branch": c[1]}))
    return out


@org("agrani", "Agrani Bank PLC", "অগ্রণী ব্যাংক পিএলসি", "bank",
     ["https://www.agranibank.org/index.php/locator/branch_type", "https://www.agranibank.org/index.php/home/agents_list"], "public")
def agrani():
    u = "https://www.agranibank.org/index.php/locator/branch_type"
    # the locator page's own request: empty CSRF field exactly as its script sends it
    page = post(u, data={"ci_csrf_token": "", "branch_type": "ALL", "District": "", "Upazila": ""}).text
    out = []
    for tr in re.findall(r"(?s)<tr>(.*?)</tr>", page):
        c = tds(tr)
        if len(c) != 10:
            continue
        ph = lines(c[6])
        em = emails(" ".join(ph))
        # c[7], c[8]: branch manager's name, mobile, e-mail and photo -> never read
        code = asc(txt(c[4]))
        out.append(R("agrani", "branch", "br:" + code, u, name_bn=txt(c[2]), district=txt(c[1]), address=txt(c[3]), code=code,
                     routing=asc(txt(c[5])), phone=phones(" , ".join(p for p in ph if "@" not in p)), email=em, text=txt(c[3])))
    u2 = "https://www.agranibank.org/index.php/home/agents_list"
    for tr in trs(strip_noise(get(u2).text)):
        c = [txt(x) for x in tds(tr)]
        if len(c) == 10 and c[0].isdigit():
            # c[6] trade name, c[7] agent's mobile, c[8] agent's e-mail: the agent's own contacts -> not written
            out.append(R("agrani", "agent_outlet", "agent:" + sid_hash(c[4], c[5]), u2, name_en=c[4], district=c[2],
                         upazila=c[3], address=c[5], parent=c[9],
                         extra={"outlet_type": "agent banking outlet", "agrani_circle": c[1], "parent_branch": c[9]}))
    return out


@org("rupali", "Rupali Bank PLC", "রূপালী ব্যাংক পিএলসি", "bank",
     ["https://www.rupalibank.com.bd/on_branch.php", "https://www.rupalibank.com.bd/details.php",
      "https://www.rupalibank.com.bd/sub_branch.php", "https://www.rupalibank.com.bd/atm_location.php"], "public")
def rupali():
    B = "https://www.rupalibank.com.bd/"

    def rows(path):
        page = strip_noise(get(B + path).text)
        for tr in re.findall(r'(?s)<tr class="notice_tr">(.*?)</tr>', page):
            yield [txt(x) for x in tds(tr)], tr     # the '#' column is a <th>: cells start with the name
    out = []
    for c, tr in rows("on_branch.php"):
        m = re.search(r'id="(\d+)" tbl="(\w+)"', tr)
        r = R("rupali", "branch", "br:" + c[1], B + "on_branch.php", name_en=c[0], code=c[1], address=c[2], phone=phones(c[3]),
              text=c[0].split(",")[-1] + " , " + c[2], prefer="text")
        if DETAILS and m:
            d = lines(post(B + "details.php", data={"id": m[1], "tbl": m[2]}).text)
            kv = {}
            keys = ("Branch Name", "Branch Code", "Address", "Phone", "Mobile", "Email", "IP Phone", "Routing Number", "In Charge")
            for i, k in enumerate(d):
                if k in keys and i + 1 < len(d) and d[i + 1] not in keys:
                    kv[k] = d[i + 1]
            # 'In Charge' is a person -> not written. 'Mobile' is listed as the branch's number.
            r["routing"] = asc(kv.get("Routing Number", "")).strip()
            r["email"] = emails(kv.get("Email", ""))
            r["phone"] = phones("; ".join(x for x in (c[3], kv.get("Mobile", ""), kv.get("IP Phone", "")) if x))
            r["url"] = B + "details.php"
            r["extra"]["details_id"] = m[1]
        out.append(r)
    for c, tr in rows("sub_branch.php"):
        out.append(R("rupali", "sub_branch", "sub:" + sid_hash(c[0], c[1]), B + "sub_branch.php", name_en=c[0], address=c[2],
                     phone=phones(c[3]), parent=c[1], text=c[0].split(",")[-1] + " , " + c[2], prefer="text",
                     extra={"branch_type": "sub-branch", "controlling_branch": c[1]}))
    for c, tr in rows("atm_location.php"):
        m = re.search(r"maps/dir//(-?[\d.]+),(-?[\d.]+)", tr)
        out.append(R("rupali", "atm", "atm:" + sid_hash(c[0], c[1]), B + "atm_location.php", name_en=c[0] + " ATM",
                     category="finance.atm", address=c[1], text=c[0].split(",")[-1] + " , " + c[1], parent=c[0], prefer="text",
                     lat=m and fnum(m[1]), lon=m and fnum(m[2])))
    return out


@org("bkb", "Bangladesh Krishi Bank", "বাংলাদেশ কৃষি ব্যাংক", "bank",
     ["https://krishibank.gov.bd/pages/static-pages/6922e13f933eb65569e2b193"], "public")
def bkb():
    # krishibank.org.bd answered HTTP 503 (Nov 2026); the bank's national-portal site carries the same list.
    u = "https://krishibank.gov.bd/pages/static-pages/6922e13f933eb65569e2b193"
    out = []
    tb = re.findall(r"(?is)<table.*?</table>", strip_noise(get(u).text))[0]
    for tr in trs(tb)[1:]:
        c = [txt(x) for x in tds(tr)]
        if len(c) < 7 or not c[1]:
            continue
        out.append(R("bkb", "branch", "br:" + asc(c[1]), u, name_en=c[2].title() + " Branch", code=asc(c[1]), district=c[3],
                     phone=phones(c[4]), email=emails(c[5]), address=c[6], text=c[6], extra={"bkb_region": c[3]}))
    return out


@org("rakub", "Rajshahi Krishi Unnayan Bank", "রাজশাহী কৃষি উন্নয়ন ব্যাংক", "bank", ["https://www.rakub.org.bd/branchlive.php"], "public")
def rakub():
    u = "https://www.rakub.org.bd/branchlive.php"
    page = get(u).text
    tb = page[page.find('id="brTbl"'):]
    tb = tb[:tb.find("</table>")]
    out = []
    for tr in re.findall(r'(?s)<tr class="\w*"[^>]*>(.*?)</tr>', tb):
        c = [txt(x) for x in tds(tr)]
        if len(c) < 8:
            continue
        # c[3] = manager's name -> not written. Mobiles: only the bank's 01708806xxx branch series is kept.
        mob = "; ".join(p for p in phones(c[6]).split("; ") if re.sub(r"\D", "", p)[-11:].startswith("01708806"))
        out.append(R("rakub", "branch", "br:" + sid_hash(c[1], c[2]), u, name_en=c[2] + " Branch", district=c[1], address=c[4],
                     phone="; ".join(x for x in (phones(c[5]), mob) if x), email=emails(c[7].replace(" ", "")),
                     text=c[4], extra={"rakub_zone": c[1]}))
    return out


@org("basic", "BASIC Bank PLC", "বেসিক ব্যাংক পিএলসি", "bank", ["https://basicbankplc.com/en/location-page"], "public")
def basic():
    u = "https://basicbankplc.com/en/location-page"
    j = get(u, params=dict(draw=1, start=0, length=1000, branch_type_id=0, division_id=0, district_id=0),
            headers={"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"}).json()
    out = []
    for x in j["data"]:
        x = {k: (_html.unescape(v) if isinstance(v, str) else v) for k, v in x.items()}
        typ = x.get("branch_type_id") or ""
        cat = "finance.atm" if typ == "ATM" else "finance.bank"
        addr = re.split(r"(?i)\b(mob|mobile|phone|tel|e-?mail)\b", txt(x.get("branch_address")))[0].strip(" ,.")
        ph = phones(" ".join(re.findall(r"(?i)(?:mob|mobile|phone|tel)\w*\s*[:.]?\s*([\d\-+, ]+)", txt(x.get("branch_address")))))
        out.append(R("basic", typ.lower().replace(" ", "_") or "branch", f"{x.get('branch_id')}", u, name_en=x.get("branch_name"),
                     name_bn=x.get("branch_name_bn"), category=cat, address=addr, district=x.get("district_id"),
                     division=x.get("division_id"), routing=x.get("router_no") or "", lat=fnum(x.get("lat")), lon=fnum(x.get("long")),
                     phone=ph, email=emails(x.get("branch_email_address")), code=str(x.get("branch_id") or ""),
                     extra={"branch_type": typ, "address_bn": txt(x.get("branch_address_bn"))}))
    return out


def _portal_table(url):
    return re.findall(r"(?is)<table.*?</table>", strip_noise(get(url).text))


@org("bdbl", "Bangladesh Development Bank PLC", "বাংলাদেশ ডেভেলপমেন্ট ব্যাংক পিএলসি", "bank",
     ["https://bdbl.com.bd/pages/static-pages/6922e06a933eb65569e26efe"], "public")
def bdbl():
    u = "https://bdbl.com.bd/pages/static-pages/6922e06a933eb65569e26efe"
    out, zone = [], ""
    for tr in trs(_portal_table(u)[0]):
        for cell in tds(tr):
            ls = lines(cell)
            if not ls:
                continue
            if "জোনাল অফিস" in ls[0] and "আওতাধীন" in ls[0]:
                zone = ls[0].split(" এর")[0]
                continue
            if not (re.match(r"^[০-৯0-9]+\)", ls[0]) or ls[0].startswith("প্রিন্সিপাল")):
                continue
            name = re.sub(r"^[০-৯0-9]+\)\s*", "", ls[0]).rstrip(": ")
            d = {"phone": [], "email": "", "routing": ""}
            addr = ls[1] if len(ls) > 1 else ""
            for ln in ls[2:]:
                k, _, v = ln.partition(":")
                k = k.strip()
                if k in ("টেলিফোন", "ফোন", "সেল ফোন", "মোবাইল"):
                    d["phone"].append(v.strip(" ।"))
                elif k in ("ইমেইল", "ই-মেইল"):
                    d["email"] = v.strip(" ।")
                elif k.startswith("রাউটিং"):
                    d["routing"] = asc(v).strip(" ।")
                # 'ব্রাঞ্চ ম্যানেজার' (name) and 'পদবী' (designation) -> not written
            out.append(R("bdbl", "branch", "br:" + (d["routing"] or sid_hash(name)), u, name_bn=name, address=addr, text=addr,
                         phone=phones(", ".join(d["phone"])), email=emails(d["email"]), routing=d["routing"],
                         extra={"bdbl_zone": zone}))
    return out


@org("pkb", "Probashi Kallyan Bank", "প্রবাসী কল্যাণ ব্যাংক", "bank", ["https://pkb.gov.bd/pages/static-pages/6922e0de933eb65569e28f0c"], "public")
def pkb():
    u = "https://pkb.gov.bd/pages/static-pages/6922e0de933eb65569e28f0c"
    seen, out = set(), []
    for tb in _portal_table(u):     # the page carries the same table twice
        for tr in trs(tb):
            for cell in tds(tr):
                ls = lines(cell)
                if len(ls) < 2:
                    continue
                if ls[0].endswith(","):
                    ls = [ls[0] + " " + ls[1]] + ls[2:]
                if "শাখা" not in ls[0] and "বুথ" not in ls[0]:
                    continue
                if ls[0] in seen:
                    continue
                seen.add(ls[0])
                rest = [re.sub(r"^(ব্যবস্থাপক|ইনচার্জ)\s*", "", x) for x in ls[1:]]
                rest = [x for x in rest if x]
                btype = rest.pop(0).strip("()") if rest and rest[0].startswith("(") else ""
                addr = " ".join(x for x in rest if not re.match(r"^(ফোন|মোবা|ই-?মেইল|টেলি)", x))
                tel = " , ".join(x for x in rest if re.match(r"^(ফোন|মোবা|টেলি)", x))
                out.append(R("pkb", "booth" if "বুথ" in ls[0] else "branch", "br:" + sid_hash(ls[0]), u, name_bn=ls[0], address=addr,
                             text=ls[0].split(",")[-1] + " , " + addr, phone=phones(re.sub(r"[ঃ:]", " ", tel)), prefer="text",
                             extra={"branch_type_bn": btype}))
    return out


@org("kb", "Karmasangsthan Bank", "কর্মসংস্থান ব্যাংক", "bank", ["https://kb.gov.bd/pages/static-pages/6af979ea4dd0494621a57610"], "public")
def kb():
    u = "https://kb.gov.bd/pages/static-pages/6af979ea4dd0494621a57610"
    out, div = [], ""
    for tr in trs(_portal_table(u)[0]):
        cells = [lines(c) for c in tds(tr)]
        if len(cells) == 1 and len(cells[0]) == 1 and cells[0][0].endswith("বিভাগ"):
            div = cells[0][0]
            continue
        for ls in cells:
            if not ls or "শাখা" not in ls[0]:
                continue          # regional offices (আঞ্চলিক কার্যালয়) are not branches
            name, _, dist = ls[0].partition(",")
            ph = [x for x in ls[1:] if x.startswith("ফোন")]
            addr = " ".join(x for x in ls[1:] if not x.startswith("ফোন"))
            out.append(R("kb", "branch", "br:" + sid_hash(ls[0], addr), u, name_bn=ls[0].strip(), district=dist.strip(), address=addr,
                         text=addr, phone=phones(ph[0].split("-", 1)[-1] if ph else ""), division=div))
    return out


@org("psb", "Palli Sanchay Bank", "পল্লী সঞ্চয় ব্যাংক", "bank", ["https://ers.pallisanchaybank.gov.bd/ords/f?p=101:80"], "public")
def psb():
    u = "https://ers.pallisanchaybank.gov.bd/ords/f?p=101:80"
    page = strip_noise(get(u).text)
    tb = max(re.findall(r"(?s)<table.*?</table>", page), key=len)
    out = []
    for tr in trs(tb):
        c = [txt(x) for x in tds(tr)]
        if len(c) == 7 and c[0].isdigit():
            m = re.match(r"(.*?)\s*-\s*(\d+)$", c[1])
            name, code = (m[1], m[2]) if m else (c[1], "")
            # c[2] = designated officer (name + staff id) -> not written; c[3] is the branch's official mobile
            out.append(R("psb", "branch", "br:" + (code or sid_hash(c[1])), u, name_en=name + " Branch", code=code,
                         phone=phones(c[3]), email=emails(c[4]), division=c[5], district=c[6]))
    return out


# ================================================================ a. banks — private commercial
@org("ibbl", "Islami Bank Bangladesh PLC", "ইসলামী ব্যাংক বাংলাদেশ পিএলসি", "bank",
     ["https://www.islamibankbd.com/branch", "https://www.islamibankbd.com/sub-branch", "https://www.islamibankbd.com/atm-branch",
      "https://www.islamibankbd.com/crm-booth", "https://www.islamibankbd.com/agent-banking"])
def ibbl():
    B = "https://www.islamibankbd.com/"
    out = []
    specs = {"branch": ["district", "name", "code", "address", "mobile"],
             "sub-branch": ["district", "name", "parent", "address", "mobile"],
             "atm-branch": ["address", "upazila", "parent", "crm"],
             "crm-booth": ["address"],
             "agent-banking": ["district", "upazila", "address", "parent", "agent_name"]}
    for page, cols in specs.items():
        tb = table_by_id(get(B + page).text, "example")
        for i, tr in enumerate(trs(tb)[1:]):
            c = [txt(x) for x in tds(tr)]
            if len(c) < len(cols):
                continue
            d = dict(zip(cols, c[1:]))
            u = B + page
            if page == "branch":
                out.append(R("ibbl", "branch", "br:" + d["code"], u, name_en=d["name"], code=d["code"], district=d["district"],
                             address=d["address"], phone=phones(d["mobile"]), text=d["address"]))
            elif page == "sub-branch":
                out.append(R("ibbl", "sub_branch", "sub:" + sid_hash(d["name"], d["parent"]), u, name_en=d["name"],
                             district=d["district"], address=d["address"], phone=phones(d["mobile"]), parent=d["parent"],
                             text=d["address"], extra={"branch_type": "sub-branch", "controlling_branch": d["parent"]}))
            elif page == "atm-branch":
                ll = re.search(r"[?&]ll=([-\d.]+),([-\d.]+)", tr)
                crm = "no.png" not in tr
                out.append(R("ibbl", "atm", "atm:" + sid_hash(d["address"], d["parent"]), u, name_en=d["address"] + " ATM",
                             category="finance.atm", address=d["address"], upazila=d["upazila"], parent=d["parent"], text=d["address"],
                             lat=ll and fnum(ll[1]), lon=ll and fnum(ll[2]),
                             extra={"controlling_branch": d["parent"], "crm": crm}))
            elif page == "crm-booth":
                a = d["address"].replace("Â", "").strip()
                out.append(R("ibbl", "crm_booth", "crm:" + sid_hash(a), u, name_en=a + " CRM booth", category="finance.atm",
                             address=a, text=a, extra={"machine": "CRM (cash recycling machine) booth"}))
            else:
                # 'Agent Name' can be a person: not written
                out.append(R("ibbl", "agent_outlet", "agent:" + sid_hash(d["address"], d["parent"]), u,
                             name_en="Agent banking outlet, " + d["address"], district=d["district"], upazila=d["upazila"],
                             address=d["address"], parent=d["parent"], text=d["address"],
                             extra={"outlet_type": "agent banking outlet", "controlling_branch": d["parent"]}))
    return out


@org("dbbl", "Dutch-Bangla Bank PLC", "ডাচ্-বাংলা ব্যাংক পিএলসি", "bank",
     ["https://app.dutchbanglabank.com/DBBLWeb/BranchLocation", "https://www.dutchbanglabank.com/sub-branch/sub-branch-list.html",
      "https://app.dutchbanglabank.com/dbblwebapp/atmCrmListCrmViewAction"])
def dbbl():
    out = []
    u = "https://app.dutchbanglabank.com/DBBLWeb/BranchLocation"
    t = get(u).text
    for head, tb in re.findall(r"(?s)<h5>([^<]+)</h5>\s*(<table.*?</table>)", t):
        dist, _, div = txt(head).partition("-")
        for tr in trs(tb):
            c = [txt(x) for x in tds(tr)]
            if len(c) < 5 or not c[2]:
                continue
            out.append(R("dbbl", "sme_unit" if head.startswith("SME") else "branch", "br:" + c[2], u, name_en=c[3], code=c[2],
                         district=dist.strip(), division=(div or dist).strip(), address=c[4], text=c[4]))
    u = "https://www.dutchbanglabank.com/sub-branch/sub-branch-list.html"
    for tr in trs(get(u).text):
        c = [txt(x) for x in tds(tr)]
        if len(c) >= 5 and c[0].isdigit():
            out.append(R("dbbl", "sub_branch", "sub:" + c[1], u, name_en=c[2], code=c[1], address=c[4], parent=c[3], text=c[4],
                         prefer="text", extra={"branch_type": "sub-branch", "mother_branch": c[3]}))
    u = "https://app.dutchbanglabank.com/dbblwebapp/atmCrmListCrmViewAction"
    for tr in trs(get(u, timeout=300, retries=3).text):
        c = tds(tr)
        if len(c) < 9:
            continue
        cc = [txt(x).replace("¿", "") for x in c]
        q = re.search(r"maps\?q=([-\d.]+),([-\d.]+)", c[8])
        kind = cc[1].lower()
        if kind not in ("atm", "crm"):
            continue
        out.append(R("dbbl", kind, f"{kind}:" + sid_hash(cc[2], cc[7]), u, name_en=cc[2], category="finance.atm", parent=cc[3],
                     division=cc[4], district=cc[5], upazila=cc[6], address=cc[7], text=cc[7],
                     lat=q and fnum(q[1]), lon=q and fnum(q[2]),
                     extra={"machine": cc[1], "branch": cc[3], "upazila_or_city_published": cc[6]}))
    return out


@org("bracbank", "BRAC Bank PLC", "ব্র্যাক ব্যাংক পিএলসি", "bank", ["https://www.bracbank.com/en/our-location"])
def bracbank():
    u = "https://www.bracbank.com/en/our-location"
    t = get(u).text
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)</script>', t, re.S)
    flight = "".join(json.loads('"' + c + '"') for c in chunks)
    obj, _ = json.JSONDecoder().raw_decode(flight, flight.index('{"data":[{"id":'))
    out = []
    for grp in obj["data"]:
        label = grp.get("label") or ""
        for d in grp.get("content") or []:
            c = d.get("coordinates") or {}
            lat, lon = fnum(c.get("lat")), fnum(c.get("lng"))
            lk = label.upper()
            cat = "finance.atm" if lk in ("ATM", "CRM", "RCDM") else "finance.bank"
            kind = {"AGENT BANKING": "agent_outlet", "SUB BRANCH": "sub_branch", "BRANCH": "branch"}.get(lk, lk.lower().replace(" ", "_"))
            phone = "" if kind == "agent_outlet" else phones(d.get("phone"))   # agent outlet numbers are the agent's own
            out.append(R("bracbank", kind, str(d.get("id")), u, name_en=d.get("title"), category=cat, address=txt(d.get("address")),
                         district=d.get("district") or "", division=d.get("division") or "", lat=lat, lon=lon, phone=phone,
                         routing=d.get("routing_number") or "", text=txt(d.get("address")) + " , " + (d.get("area") or ""),
                         prefer="text", extra={"location_type": label, "area": d.get("area")}))
    return out


@org("ebl", "Eastern Bank PLC", "ইস্টার্ন ব্যাংক পিএলসি", "bank",
     ["https://www.ebl.com.bd/locator/branches", "https://www.ebl.com.bd/locator/sub-branch", "https://www.ebl.com.bd/locator/ebl365",
      "https://www.ebl.com.bd/locator/ebl365PLUS"])
def ebl():
    def cfemail(h):
        k = int(h[:2], 16)
        return "".join(chr(int(h[i:i + 2], 16) ^ k) for i in range(2, len(h), 2))
    out = []
    pages = {"branches": ("branch", ["district", "name", "address", "routing", "contact"]),
             "sub-branch": ("sub_branch", ["district", "name", "address", "routing", "contact"]),
             "ebl365": ("atm_booth", ["division", "name", "address", "availability"]),
             "ebl365PLUS": ("crm_booth", ["division", "name", "address", "availability"])}
    for p, (kind, cols) in pages.items():
        u = "https://www.ebl.com.bd/locator/" + p
        body = re.search(r"(?s)<tbody>(.*?)</tbody>", get(u).text).group(1)
        for tr in trs(body):
            c = tds(tr)
            d = dict(zip(cols, (txt(x) for x in c[1:])))
            if not d.get("name"):
                continue
            em = re.findall(r'data-cfemail="([0-9a-f]+)"', tr)
            atm = kind in ("atm_booth", "crm_booth")
            out.append(R("ebl", kind, f"{kind}:" + sid_hash(d["name"], d.get("address")), u, name_en=d["name"],
                         category="finance.atm" if atm else "finance.bank", address=d.get("address", ""), district=d.get("district", ""),
                         division=d.get("division", ""), routing=d.get("routing", ""), text=d.get("address", ""),
                         phone=phones(re.sub(r"\[email\s*protected\]", "", d.get("contact", ""))),
                         email="; ".join(cfemail(h) for h in em), hours=d.get("availability", "") if atm else "",
                         extra={"branch_type": "sub-branch"} if kind == "sub_branch" else {}))
    return out


@org("ucb", "United Commercial Bank PLC", "ইউনাইটেড কমার্শিয়াল ব্যাংক পিএলসি", "bank",
     ["https://www.ucb.com.bd/branch-atm-locator/", "https://www.ucb.com.bd/api/query/agentOutlet"])
def ucb():
    u = "https://www.ucb.com.bd/branch-atm-locator/"
    t = get(u).text
    out = []
    for it in t.split('<div class="atm-search-item">')[1:]:
        it = it.split("RESULT ITEM")[0]
        a = dict(re.findall(r'data-(id|type|district|name|area|address)="([^"]*)"', it))
        typ = (a.get("type") or "").lower()
        if typ in ("closed", "atmcancle"):
            continue
        ps = [txt(p) for p in re.findall(r"(?s)<p>(.*?)</p>", it)]
        geo = re.search(r"GetLoacation\(\s*this,\s*'([-\d.]*)',\s*'([-\d.]*)'", it)
        rout = re.search(r"Routing number:\s*</strong>\s*(\d+)", it)
        swift = re.search(r"SWIFT Code:\s*</strong>\s*(\w+)", it)
        nm = re.search(r'(?s)atm-name">\s*(.*?)\s*</div>', it)
        contact = " ".join(p for p in ps[1:] if not re.match(r"(?i)(swift|routing|\[geo)", p))
        # officer mobiles are tagged (HOB) / (OM) / (BM): those numbers are dropped
        contact = re.sub(r"(?i)[\d+\-\s]{7,}\s*\((HOB|OM|BM|SM|manager)\)", " ", contact)
        atm = typ == "atm"
        out.append(R("ucb", {"uposhakha": "sub_branch", "": "location"}.get(typ, typ), "loc:" + (a.get("id") or sid_hash(nm and nm[1])), u,
                     name_en=txt(nm[1]) if nm else "", category="finance.atm" if atm else "finance.bank", address=ps[0] if ps else "",
                     text=ps[0] if ps else "", prefer="text",     # data-area is unreliable (often the division): kept in extra only
                     routing=rout[1] if rout else "", lat=geo and fnum(geo[1]), lon=geo and fnum(geo[2]),
                     phone="" if atm else phones(contact), email="" if atm else emails(contact),
                     extra={"location_type": typ, "swift": swift[1] if swift else "", "area": a.get("area"),
                            "district_hint": a.get("district")}))   # data-district is often only a division-level hint
    u2 = "https://www.ucb.com.bd/api/query/agentOutlet"
    for d in post(u2, data={"division": "all", "district": "", "upazila": ""},
                  headers={"X-Requested-With": "XMLHttpRequest", "Referer": "https://www.ucb.com.bd/banking/agent-banking/agent-outlets"}).json():
        if str(d.get("status", "1")).lower() in ("0", "inactive", "closed"):
            continue
        # agentName (proprietor's business), phone and e-mail are the agent's own contacts -> not written
        out.append(R("ucb", "agent_outlet", f"agent:{d.get('id')}", u2, name_en="UCB agent banking outlet, " + (d.get("agentPoint") or ""),
                     address=d.get("address") or "", district=d.get("district") or "", upazila=d.get("upazilla") or "",
                     division=d.get("division") or "", parent=d.get("linkedBranch") or "", text=d.get("address") or "",
                     extra={"outlet_type": "agent banking outlet", "linked_branch": d.get("linkedBranch")}))
    return out


@org("ab", "AB Bank PLC", "এবি ব্যাংক পিএলসি", "bank",
     ["https://abbl.com/ablocatorupdate/api/branches.php", "https://abbl.com/ablocatorupdate/api/atm.php", "https://abbl.com/find-branch-and-atm/"])
def ab():
    out = []
    for kind, ep in (("branch", "branches"), ("atm", "atm")):
        u = f"https://abbl.com/ablocatorupdate/api/{ep}.php"
        for d in get(u).json()["data"]:
            desc = txt(d.get("description") or "")
            m = re.search(r"Routing Number:\s*(\d+)", desc)
            c = re.search(r"Code:\s*(\d+)", desc)
            op = re.search(r"Date of Opening:\s*([\w ,.-]+?\d{4})", desc)
            out.append(R("ab", kind, f"{kind}:{d.get('id')}", u, name_en=txt(d.get("name")), category="finance.atm" if kind == "atm" else "finance.bank",
                         address=txt(d.get("address")), text=txt(d.get("address")), lat=fnum(d.get("latitude")), lon=fnum(d.get("longitude")),
                         phone=phones(d.get("telephone")) if kind == "branch" else "", email=emails(d.get("email")) if kind == "branch" else "",
                         routing=m[1] if m else "", code=c[1] if c else "", extra={"opening_date": op[1] if op else ""}))
    u = "https://abbl.com/find-branch-and-atm/"
    page = strip_noise(get(u).text)   # closed rows are commented out
    for tid, kind in (("sub-branch-table", "sub_branch"), ("aget-outlet-table", "agent_outlet")):
        for tr in trs(table_by_id(page, tid))[1:]:
            c = [txt(x) for x in tds(tr)]
            if len(c) < 3:
                continue
            q = re.search(r"place\?q=([-\d.]+),([-\d.]+)", tr)
            if kind == "sub_branch":
                out.append(R("ab", kind, "sub:" + sid_hash(c[0]), u, name_en=c[0], division=c[2], district=c[3], address=c[4], text=c[4],
                             parent=c[1], lat=q and fnum(q[1]), lon=q and fnum(q[2]),
                             extra={"branch_type": "sub-branch", "controlling_branch": c[1], "opening_date": c[5] if len(c) > 5 else ""}))
            else:
                out.append(R("ab", kind, "agent:" + sid_hash(c[0], c[2]), u, name_en=c[0], division=c[1], district=c[2],
                             lat=q and fnum(q[1]), lon=q and fnum(q[2]), extra={"outlet_type": "agent banking outlet"}))
    return out


@org("dhakabank", "Dhaka Bank PLC", "ঢাকা ব্যাংক পিএলসি", "bank",
     ["https://dhakabank.com.bd/wp-content/themes/dhakabankupdate/js/branch.json",
      "https://dhakabank.com.bd/wp-content/themes/dhakabankupdate/js/sub-branch.json",
      "https://dhakabank.com.bd/wp-content/themes/dhakabankupdate/js/atm.json",
      "https://dhakabank.com.bd/wp-content/themes/dhakabankupdate/js/edm.json"])
def dhakabank():
    B = "https://dhakabank.com.bd/wp-content/themes/dhakabankupdate/js/"
    out = []
    for kind in ("branch", "sub-branch", "atm", "edm"):    # crm.json is commented out on the locator page: not used
        u = B + kind + ".json"
        for d in json.loads(get(u).content.decode("utf-8-sig"))["data"]:
            atm = kind in ("atm", "edm")
            k = {"sub-branch": "sub_branch", "edm": "adm"}.get(kind, kind)
            addr = txt(d.get("address"))
            out.append(R("dhakabank", k, f"{k}:{d.get('id') or sid_hash(d.get('name'))}", u, name_en=txt(d.get("name")),
                         category="finance.atm" if atm else "finance.bank", address=addr, text=addr,
                         lat=fnum(d.get("latitude")), lon=fnum(d.get("longitude")),
                         phone="" if atm else phones(re.split(r"(?i)fax", txt(d.get("telephone")))[0]),
                         email="" if atm else emails(d.get("email")), parent=txt(d.get("host_branch")),
                         extra={"description": txt(d.get("description")), "host_branch": txt(d.get("host_branch")),
                                "record_modified": d.get("modified")}))
    return out


@org("mtb", "Mutual Trust Bank PLC", "মিউচুয়াল ট্রাস্ট ব্যাংক পিএলসি", "bank",
     ["https://www.mutualtrustbank.com/wp-admin/admin-ajax.php?action=search_branch",
      "https://www.mutualtrustbank.com/wp-admin/admin-ajax.php?action=search_atm", "https://www.mutualtrustbank.com/branch-atm-location/"])
def mtb():
    out = []
    A = "https://www.mutualtrustbank.com/wp-admin/admin-ajax.php?action="
    atm_ll = {}
    for kind in ("branch", "atm"):
        u = A + "search_" + kind
        for d in get(u).json()["data"]:
            parts = re.split(r"(?i)<br\s*/?>", d.get("address") or "")
            extra = txt(" ".join(parts[1:]))
            if kind == "atm":
                atm_ll[txt(d["name"]).lower()] = (fnum(d.get("lat")), fnum(d.get("long")))
                continue
            k = "sub_branch" if re.search(r"(?i)sub[\s-]?branch", d["name"]) else "branch"
            ph = re.search(r"(?i)Phone\s*:?\s*(.*?)(?:Fax|E-?mail|$)", extra)
            out.append(R("mtb", k, k + ":" + sid_hash(d["name"]), u, name_en=txt(d["name"]), address=txt(parts[0]), text=txt(parts[0]),
                         division=d.get("division") or "", lat=fnum(d.get("lat")), lon=fnum(d.get("long")),
                         phone=phones(ph[1]) if ph else "", email=emails(extra)))
    u = "https://www.mutualtrustbank.com/branch-atm-location/"
    t = get(u, timeout=300).text      # ~60 MB (mostly whitespace): the only list with districts, CRMs and agent outlets
    for tb in re.findall(r'(?s)<table id="dtBasicExample".*?</table>', t):
        rows = trs(tb)
        if not rows:
            continue
        head = [txt(c) for c in re.findall(r"(?s)<t[hd][^>]*>(.*?)</t[hd]>", rows[0])]
        if head[:1] not in (["ATM Name"], ["MTB Agent Banking Centre Name"]):
            continue
        for tr in rows[1:]:
            c = [txt(x) for x in tds(tr)]
            if len(c) < 4:
                continue
            if head[0] == "ATM Name":
                crm = bool(re.search(r"\bCRM\b", c[0]))
                ll = atm_ll.get(c[0].lower(), (None, None))
                out.append(R("mtb", "crm" if crm else "atm", "atm:" + sid_hash(c[0], c[1]), u, name_en=c[0], category="finance.atm",
                             address=c[1], division=c[2], district=c[3], text=c[1], lat=ll[0], lon=ll[1]))
            else:   # the heading says District, Division but the columns are Division, District
                out.append(R("mtb", "agent_outlet", "agent:" + sid_hash(c[0], c[1]), u, name_en=c[0], address=c[1], division=c[2],
                             district=c[3], text=c[1], extra={"outlet_type": "agent banking outlet"}))
    return out


@org("trust", "Trust Bank PLC", "ট্রাস্ট ব্যাংক পিএলসি", "bank",
     ["https://www.tblbd.com/locator/api/search/?q=&urban_rural=&page_size=all"])
def trust():
    u = "https://www.tblbd.com/locator/api/search/?q=&urban_rural=&page_size=all"
    out = []
    for d in get(u, headers={"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"}).json()["results"]:
        lt = (d.get("location_type") or "").upper()
        atm = lt in ("ATM", "CDM", "CRM")
        g = d.get("geo") or {}
        kind = {"SUB_BRANCH": "sub_branch"}.get(lt, lt.lower())
        out.append(R("trust", kind, f"{kind}:{d.get('id')}", u, name_en=d.get("name_en") or "", name_bn=d.get("name_bn") or "",
                     category="finance.atm" if atm else "finance.bank", address=txt(d.get("address_en")), text=txt(d.get("address_en")),
                     routing=d.get("routing_no") or "", lat=fnum(g.get("lat")), lon=fnum(g.get("lon")),
                     phone="" if atm else phones(d.get("phone")), email="" if atm else emails(d.get("email")),
                     extra={"location_type": lt, "address_bn": txt(d.get("address_bn")), "postcode": d.get("postcode"),
                            "swift": d.get("swift_code"), "urban_rural": d.get("urban_rural"), "opened_on": d.get("opened_on"),
                            "landmark": d.get("landmark")}))
    return out


@org("ific", "IFIC Bank PLC", "আইএফআইসি ব্যাংক পিএলসি", "bank",
     ["https://ificbank.com.bd/branch", "https://ificbank.com.bd/uposhakha", "https://ificbank.com.bd/atm"])
def ific():
    out = []
    for kind, u in (("branch", "https://ificbank.com.bd/branch"), ("sub_branch", "https://ificbank.com.bd/uposhakha"),
                    ("atm", "https://ificbank.com.bd/atm")):
        for head, rows in tables_with_header(get(u).text, "SL"):
            for tr in rows:
                c = tds(tr)
                if len(c) < len(head) - 1:
                    continue
                d = dict(zip(head, (txt(x) for x in c)))
                name = d.get("Branch Name") or d.get("Uposhakha Name") or d.get("Name") or d.get("ATM Name") or ""
                if not name:
                    name = next((v for k, v in d.items() if "name" in k.lower()), "")
                addr = d.get("Address", "")
                out.append(R("ific", kind, f"{kind}:" + sid_hash(name, addr), u, name_en=name,
                             category="finance.atm" if kind == "atm" else "finance.bank", address=addr, text=addr,
                             district=d.get("District", ""), division=d.get("Division", ""), routing=d.get("Routing No.", ""),
                             phone="" if kind == "atm" else phones(d.get("Contact", "")),
                             prefer="text" if kind == "atm" else "field", parent=d.get("Controlling Branch", ""),
                             extra={"controlling_branch": d.get("Controlling Branch"),
                                    "branch_type": "uposhakha (sub-branch)" if kind == "sub_branch" else ""}))
    return out


@org("bankasia", "Bank Asia PLC", "ব্যাংক এশিয়া পিএলসি", "bank",
     ["https://www.bankasia-bd.com/locator/branches", "https://www.bankasia-bd.com/locator/atms"])
def bankasia():
    out = []
    for kind, u in (("branch", "https://www.bankasia-bd.com/locator/branches"), ("atm", "https://www.bankasia-bd.com/locator/atms")):
        for head, rows in tables_with_header(get(u).text, "SL."):
            for tr in rows:
                d = dict(zip(head, (txt(x) for x in tds(tr))))
                name = d.get("Branch") or d.get("Name") or d.get("ATM") or ""
                if not name:
                    continue
                ph = d.get("Phone", "")
                # 'Br. Manager' / 'OP. Manager' / 'R. Manager' mobiles are staff numbers -> dropped
                ph = re.split(r"(?i)[\w.]*\s*manager", ph)[0]
                out.append(R("bankasia", kind, f"{kind}:" + sid_hash(name, d.get("Address")), u, name_en=name,
                             category="finance.atm" if kind == "atm" else "finance.bank", address=d.get("Address", ""),
                             district=d.get("District", ""), division=d.get("Division", ""), text=d.get("Address", ""),
                             phone="" if kind == "atm" else phones(ph), extra={"area": d.get("Area")}))
    return out


@org("prime", "Prime Bank PLC", "প্রাইম ব্যাংক পিএলসি", "bank",
     ["https://www.primebank.com.bd/branch", "https://www.primebank.com.bd/atms"])
def prime():
    out = []
    for kind, u in (("branch", "https://www.primebank.com.bd/branch"), ("atm", "https://www.primebank.com.bd/atms")):
        j = get(u, params={"draw": 1, "start": 0, "length": 1000, "filter_division": ""},
                headers={"X-Requested-With": "XMLHttpRequest", "Accept": "application/json"}).json()
        for d in j.get("data") or []:
            name = txt(d.get("name"))
            atm = kind == "atm"
            addr = txt(d.get("address"))
            out.append(R("prime", kind, f"{kind}:{d.get('id') or sid_hash(name, addr)}", u, name_en=name.title() if name.isupper() else name,
                         category="finance.atm" if atm else "finance.bank", address=addr, text=addr, division=txt(d.get("division")),
                         code=str(d.get("branch_code") or ""), routing=str(d.get("routing_no") or ""),
                         lat=fnum(d.get("lat")), lon=fnum(d.get("long")),
                         phone="" if atm else phones("; ".join(str(d.get(k) or "") for k in ("phone", "mobile"))),
                         email="" if atm else emails(str(d.get("email") or "")), prefer="text",
                         extra={"swift": d.get("swift_code")}))
    return out


@org("uttara", "Uttara Bank PLC", "উত্তরা ব্যাংক পিএলসি", "bank", ["https://www.uttarabank-bd.com/locations"])
def uttara():
    u = "https://www.uttarabank-bd.com/locations"
    t = get(u).text
    i = t.index("window.locationData = ") + len("window.locationData = ")
    data, _ = json.JSONDecoder().raw_decode(t, i)
    out = []
    for kind, items in data.items():
        for d in items:
            atm = kind == "atm"
            lat, lon = fnum(d.get("latitude")), fnum(d.get("longitude"))
            if not lat:
                m = re.search(r"!2d(-?[\d.]+)!3d(-?[\d.]+)", d.get("map") or "")
                lat, lon = (fnum(m[2]), fnum(m[1])) if m else (None, None)
            name = txt(d.get("name"))
            out.append(R("uttara", kind, f"{kind}:{d.get('id') or sid_hash(name)}", u, name_en=name,
                         category="finance.atm" if atm else "finance.bank", address=txt(d.get("address")), text=txt(d.get("address")),
                         district=d.get("district") or "", division=d.get("division") or "", upazila=d.get("upazila") or "",
                         routing=str(d.get("routing_no") or ""), lat=lat, lon=lon, prefer="text",
                         phone="" if atm else phones("; ".join(str(d.get(k) or "") for k in ("phone", "mobile"))),
                         email="" if atm else emails(d.get("email")),
                         extra={"branch_point": d.get("branch_point"), "branch_type": "sub-branch" if kind == "sub_branch" else ""}))
    return out


@org("jamuna", "Jamuna Bank PLC", "যমুনা ব্যাংক পিএলসি", "bank", ["https://jamunabankbd.com/branch-list/"])
def jamuna():
    u = "https://jamunabankbd.com/branch-list/"     # carries the branch table and the sub-branch table
    out = []
    for tb in re.findall(r"(?is)<table.*?</table>", strip_noise(get(u).text)):
        rows = trs(tb)
        if not rows:
            continue
        head = [txt(c) for c in re.findall(r"(?is)<t[hd]\b[^>]*>(.*?)</t[hd]>", rows[0])]
        if "Branch Name" in head:
            kind = "branch"
        elif "Sub Branch Name" in head:
            kind = "sub_branch"
        else:
            continue
        for tr in rows[1:]:
            d = dict(zip(head, (txt(x) for x in tds(tr))))
            name = d.get("Branch Name") or d.get("Sub Branch Name") or ""
            if not name:
                continue
            addr = d.get("Address", "")
            suffix = name.rsplit(",", 1)[1].strip() if "," in name else ""
            parent = d.get("Controlling Branch", "")
            out.append(R("jamuna", kind, f"{kind}:" + (d.get("Routing") or sid_hash(name, addr)), u, name_en=name, address=addr,
                         district=suffix, text=addr or name, division=d.get("Division") or d.get("Name of the Division") or "",
                         routing=asc(d.get("Routing", "")), phone=phones(re.sub(r"(?i)ex-?\s*\d+", "", d.get("Contract Number", ""))),
                         parent=parent, extra={"controlling_branch": parent, "jamuna_zone": d.get("Name of Zone"),
                                               "branch_type": "sub-branch" if kind == "sub_branch" else ""}))
    return out


@org("scb", "Standard Chartered Bank Bangladesh", "স্ট্যান্ডার্ড চার্টার্ড ব্যাংক বাংলাদেশ", "bank",
     ["https://www.sc.com/bd/data/atm-branch/v2/all-atms-branches.json"], "foreign")
def scb():
    u = "https://www.sc.com/bd/data/atm-branch/v2/all-atms-branches.json"
    out = []
    for d in get(u).json().get("locations") or []:
        a = d.get("address") or {}
        types = [t if isinstance(t, str) else (t.get("name") or t.get("label") or "") for t in (d.get("types") or [])]
        atm = all("atm" in t.lower() for t in types) and types
        addr = ", ".join(x for x in (a.get("addressLines") or []) if x)
        out.append(R("scb", "atm" if atm else "branch", sid_hash(d.get("name"), addr), u, name_en=txt(d.get("name")),
                     category="finance.atm" if atm else "finance.bank", address=addr, text=addr + " , " + (a.get("city") or ""),
                     lat=fnum(a.get("latitude")), lon=fnum(a.get("longitude")), prefer="text",
                     hours="24 hours" if d.get("is-24-hours") else "", extra={"types": types, "status": d.get("status")}))
    return out


# ================================================================ b. mobile operators
@org("banglalink", "Banglalink Digital Communications Ltd", "বাংলালিংক", "telecom",
     ["https://www.banglalink.net/en/store-finder", "https://web-api.banglalink.net/api/v1/sales-service/districts",
      "https://web-api.banglalink.net/api/v1/sales-service/thana-by-district",
      "https://web-api.banglalink.net/api/v1/sales-service/search-results"])
def banglalink():
    B = "https://web-api.banglalink.net/api/v1"
    dists = get(B + "/sales-service/districts").json()["data"]
    found = {}
    for d in dists:
        thanas = post(B + "/sales-service/thana-by-district", json={"district": d["district"]}).json().get("data") or []
        for th in sorted({t["thana"] for t in thanas}):
            for x in post(B + "/sales-service/search-results", json={"district": d["district"], "thana": th}).json().get("data") or []:
                found[x["retail_code"]] = x
    out = []
    for x in found.values():
        cc = str(x.get("retail_code", "")).startswith("CC")
        hours = " - ".join(v for v in (x.get("opening_time"), x.get("closing_time")) if v)
        if x.get("holiday") and x.get("holiday") != "N/A":
            hours += f"; closed: {x['holiday']}"
        out.append(R("banglalink", "care_centre" if cc else "service_point", x["retail_code"], B + "/sales-service/search-results",
                     name_en="Banglalink " + (x.get("retailer_name") or ""), category="business.service",
                     address=txt(x.get("address")), district=x.get("district") or "", upazila=x.get("thana") or "",
                     lat=fnum(x.get("latitude")), lon=fnum(x.get("longitude")), hours=hours, code=x["retail_code"],
                     extra={"outlet_type": "Banglalink Customer Care centre" if cc else "Banglalink Service Point (limited services)",
                            "address_bn": txt(x.get("address_bn")), "thana_bn": x.get("thana_bn"), "district_bn": x.get("district_bn"),
                            "additional_info": txt(x.get("additional_info"))}))
    return out


@org("teletalk", "Teletalk Bangladesh Ltd", "টেলিটক বাংলাদেশ লিমিটেড", "telecom",
     ["https://www.teletalk.com.bd/bn/customer-care-center", "https://www.teletalk.com.bd/bn/customer-care-point"], "public")
def teletalk():
    out = []
    for path, kind in (("customer-care-center", "care_centre"), ("customer-care-point", "care_point")):
        u = "https://www.teletalk.com.bd/bn/" + path
        page = get(u).text
        tabs = dict(re.findall(r'(?s)href="#(service\d+_pane)"[^>]*>(.*?)</a>', page))
        for pane, body in re.findall(r'(?s)<div[^>]*id="(service\d+_pane)"[^>]*>(.*?)</table>', page):
            if pane == "service09_pane":       # 'all' tab repeats the division tabs
                continue
            rows = trs(body)
            if not rows:
                continue
            head = [txt(c) for c in re.findall(r"(?s)<t[hd][^>]*>(.*?)</t[hd]>", rows[0])]
            for tr in rows[1:]:
                c = [txt(x) for x in tds(tr)]
                if len(c) != len(head):
                    continue
                d = dict(zip(head, c))
                hl = asc(d.get("হেল্পলাইন", ""))
                hot = re.findall(r"(?:হটলাইন|Hotline)\s*[-:]?\s*([\d\-]{9,})", hl)   # 'ইনচার্জ' (officer in charge) number dropped
                addr = d.get("ঠিকানা", "")
                st = d.get("স্টেশন", "")
                th = d.get("থানা/উপজেলা", "")
                pt = d.get("পয়েন্ট", "")
                name = ("টেলিটক কাস্টমার কেয়ার সেন্টার, " + (th or st)) if kind == "care_centre" else ("টেলিটক কাস্টমার কেয়ার পয়েন্ট, " + pt)
                hol = d.get("ছুটি", "")
                out.append(R("teletalk", kind, f"{kind}:" + sid_hash(st, th, pt, addr), u, name_bn=name, category="business.service",
                             address=addr, district=st, upazila=th, text=pt + " , " + addr, prefer="field" if st else "text",
                             phone="; ".join(hot), hours=("ছুটি: " + hol) if hol else "", division=txt(tabs.get(pane, "")),
                             extra={"outlet_type": "Teletalk customer care centre" if kind == "care_centre" else "Teletalk customer care point",
                                    "station_bn": st, "thana_upazila_bn": th, "point_bn": pt},
                             notes="Name composed from the operator and the station/upazila columns of the list."))
    return out


# ================================================================ c. couriers
@org("sundarban", "Sundarban Courier Service (Pvt) Ltd", "সুন্দরবন কুরিয়ার সার্ভিস", "courier",
     ["https://www.sundarbancourierltd.com/Home/Coverage"])
def sundarban():
    u = "https://www.sundarbancourierltd.com/Home/Coverage"
    out = []
    tb = re.search(r"(?s)<table.*?</table>", get(u).text).group(0)
    for tr in trs(tb)[1:]:
        c = [txt(x) for x in tds(tr)]
        if len(c) == 3 and c[1]:
            booth = bool(re.search(r"(?i)\bb?\.?\s*booth\b", c[1]))
            out.append(R("sundarban", "booth" if booth else "branch", sid_hash(c[1], c[2]), u, name_en="Sundarban Courier, " + c[1],
                         category="business.service", address=c[2], text=c[1] + " , " + c[2], prefer="text",
                         extra={"outlet_type": "booking booth" if booth else "branch / booking point", "list_no": c[0]}))
    return out


@org("saparibahan", "S.A. Paribahan (Pvt) Ltd", "এস. এ. পরিবহন", "courier", ["https://www.saparibahan.com/branches.php"])
def saparibahan():
    u = "https://www.saparibahan.com/branches.php"
    out = []
    for div, b in re.findall(r'(?s)<div class="[^"]*branch-item" data-division="([^"]*)">(.*?)</a>', get(u).text):
        ps = [txt(p) for p in re.findall(r"(?s)<p[^>]*>(.*?)</p>", b)]
        name = txt((re.search(r"(?s)<h4[^>]*>(.*?)</h4>", b) or [None, ""])[1])
        lab = txt((re.search(r"(?s)<small[^>]*>(.*?)</small>", b) or [None, ""])[1])
        addr = next((p.replace("📍", "").strip() for p in ps if p.startswith("📍")), "")
        ph = next((p.replace("📞", "").strip() for p in ps if p.startswith("📞")), "")
        out.append(R("saparibahan", "branch", sid_hash(name, addr), u, name_en="S.A. Paribahan, " + name, category="business.service",
                     address=addr, division=div, text=name + " , " + addr, prefer="text", phone=phones(ph),
                     extra={"label": lab, "outlet_type": "courier branch"}))
    return out


@org("steadfast", "Steadfast Courier Ltd", "স্টেডফাস্ট কুরিয়ার", "courier",
     ["https://steadfast.com.bd/coverage", "https://steadfast.com.bd/public/hub/search"])
def steadfast():
    u = "https://steadfast.com.bd/coverage"
    t = get(u).text
    tok = re.search(r'<meta name="csrf-token" content="([^"]+)"', t).group(1)   # the page's own form token (same session)
    hubs = {}
    for q in "aeiou":      # the page's hub search matches substrings; the vowels together cover the list
        r = post("https://steadfast.com.bd/public/hub/search", files={"search_text": (None, q)},
                 headers={"X-CSRF-TOKEN": tok, "X-Requested-With": "XMLHttpRequest", "Accept": "application/json", "Referer": u})
        for h in r.json().get("data") or []:
            hubs[h["id"]] = h
    out = []
    for h in hubs.values():
        name = txt(h.get("name"))
        paren = re.findall(r"\(([^)]*)\)", name)
        out.append(R("steadfast", "hub", h["id"], u, name_en="Steadfast Courier hub, " + name, category="business.service",
                     address=txt(h.get("address")), prefer="text",
                     text=" , ".join([re.sub(r"\(.*?\)", "", name)] + paren[::-1] + [txt(h.get("address"))]),
                     phone=phones("; ".join(str(h.get(k) or "") for k in ("phone", "secondary_phone"))),
                     extra={"outlet_type": "delivery hub", "hub_name": name}))
    return out


@org("ecourier", "eCourier Ltd", "ই-কুরিয়ার", "courier", ["https://ecourier.com.bd/contact-us/"])
def ecourier():
    u = "https://ecourier.com.bd/contact-us/"
    t = get(u).text
    m = re.search(r'\$\("#map\d+"\)\.maps\(', t)
    obj, _ = json.JSONDecoder().raw_decode(t, m.end())
    out = []
    for p in obj.get("places") or []:
        loc = p.get("location") or {}
        out.append(R("ecourier", "branch", p.get("id"), u, name_en="eCourier " + txt(p.get("title")), category="business.service",
                     address=txt(p.get("address")), district=loc.get("city") or "", text=txt(p.get("address")),
                     lat=fnum(loc.get("lat")), lon=fnum(loc.get("lng")),
                     extra={"outlet_type": "courier branch", "group": [c.get("name") for c in p.get("categories") or []],
                            "postal_code": loc.get("postal_code")}))
    return out


@org("janani", "Janani Express Parcel Service", "জননী এক্সপ্রেস পার্সেল সার্ভিস", "courier",
     ["https://jananiexpress.com/branches", "https://jananiexpress.com/api/branch-list"])
def janani():
    u = "https://jananiexpress.com/api/branch-list"
    out = []
    for d in get(u).json().get("details") or []:
        if d.get("isDeleted") or d.get("isActive") is False:
            continue
        en = (d.get("branchName") or "").strip()
        # branchEmail values are gmail addresses (possibly personal): not written
        out.append(R("janani", "branch", f"{d.get('_id') or d.get('branchId')}:{d.get('branchCode')}", u,
                     name_en=("Janani Express, " + en.title()) if en else "", name_bn=("জননী এক্সপ্রেস, " + nfc(d.get("branchNameBangla") or "")) if d.get("branchNameBangla") else "",
                     category="business.service", address=txt(d.get("branchAddress")), division=d.get("division") or "",
                     text=txt(d.get("branchAddress")) + " , " + en, prefer="text", phone=phones(d.get("branchMobile")),
                     code=str(d.get("branchCode") or ""), extra={"outlet_type": "parcel branch", "branch_location": d.get("branchLocation")}))
    return out


# ================================================================ d. health
@org("popular", "Popular Diagnostic Centre Ltd", "পপুলার ডায়াগনস্টিক সেন্টার", "health", ["https://www.populardiagnostic.com/"])
def popular():
    # The branch list is a static array in the site's public JavaScript bundle (the separate API needs a key: not used).
    home = get("https://www.populardiagnostic.com/").text
    js_url = "https://www.populardiagnostic.com" + re.search(r'src="(/assets/index-[\w-]+\.js)"', home).group(1)
    js = get(js_url, timeout=300).text
    i = js.index("const branch = [")
    body = js[i: js.index("\n];", i)]
    out = []
    for blk in re.split(r"\n  \{\n", body)[1:]:
        d = {k: v.strip() for k, v in re.findall(r'(\w+):\s*\n?\s*"((?:[^"\\]|\\.)*)"', blk)}
        bid = re.search(r"branchID:\s*(\d+)", blk)
        ll = re.search(r"(?:!2d|q=)(-?\d+\.\d+)(?:!3d|,)(-?\d+\.\d+)", d.get("location", ""))
        lat = lon = None
        if ll:
            a, b = float(ll.group(1)), float(ll.group(2))
            lat, lon = (b, a) if a > 80 else (a, b)
        # braManName / braManDesignation (branch manager) -> not written
        out.append(R("popular", "branch", bid[1] if bid else sid_hash(d.get("name")), "https://www.populardiagnostic.com/",
                     name_en=d.get("name") or ("Popular Diagnostic Centre, " + d.get("heading", "")), category="health.diagnostic_center",
                     address=d.get("address", ""), district=d.get("braCity", ""), text=d.get("address", ""), lat=lat, lon=lon,
                     phone=phones(d.get("Hotline", "")), email=emails(d.get("Email", "")),
                     extra={"branch_short_name": d.get("heading"), "bundle": js_url.rsplit("/", 1)[-1]}))
    return out


@org("labaid", "Labaid Group", "ল্যাবএইড", "health", ["https://labaid.com.bd/en/diagnostics"])
def labaid():
    u = "https://labaid.com.bd/en/diagnostics"
    out = []
    for link in dict.fromkeys(re.findall(r"https://labaid\.com\.bd/en/diagnostic/[\w().-]+", get(u).text)):
        h = strip_noise(get(link).text)
        x = _html.unescape(re.sub(r"<[^>]+>", "\n", h)).replace("\xa0", " ").replace("\r", "")
        x = re.sub(r"\n\s*\n+", "\n", re.sub(r"[ \t]+", " ", x))
        blk = x[:x.find("\nGet Us")].rsplit("-->\n", 1)[-1]
        ls = [l.strip(" 📍📞") for l in blk.split("\n") if l.strip(" 📍📞")]
        flat = " | ".join(ls[1:])
        addr = re.search(r"(?:Address\s*:|House\s*:)\s*\|?\s*([^|]+)", flat)
        ph = re.search(r"(?:Contact Number\s*:|Mob\s*:)\s*\|?\s*([^|]+)", flat)
        if not ls:
            continue
        # staff e-mails shown on some pages are not written
        out.append(R("labaid", "diagnostic", link.rsplit("/", 1)[-1], link, name_en=ls[0], category="health.diagnostic_center",
                     address=addr[1].strip() if addr else "", text=(addr[1] if addr else flat) + " , " + ls[0],
                     prefer="text", phone=phones(ph[1]) if ph else ""))
    return out


@org("ibf_hospitals", "Islami Bank Foundation (Islami Bank Hospitals)", "ইসলামী ব্যাংক ফাউন্ডেশন", "health",
     ["https://ibfbd.org/", "https://ibfbd.org:9359/fapi/hospitals/hospital-list"], "trust")
def ibf_hospitals():
    u = "https://ibfbd.org:9359/fapi/hospitals/hospital-list"
    out = []
    cats = {101: "Islami Bank Hospital", 102: "Islami Bank Community Hospital"}
    for d in get(u).json()["data"]["rows"]:
        if d.get("isActive") is False:
            continue
        ph = "; ".join(str(d.get(k) or "") for k in ("telephone", "phone_1", "phone_2"))
        out.append(R("ibf_hospitals", "hospital", d.get("id") or sid_hash(d.get("hospitalTitle")), "https://ibfbd.org/",
                     name_en=txt(d.get("hospitalTitle")), category="health.hospital", address=txt(d.get("address")),
                     text=txt(d.get("address")) + " , " + txt(d.get("branchName")), prefer="text", phone=phones(ph),
                     email=emails(d.get("email")), extra={"hospital_type": cats.get(d.get("hospCatId")), "ambulance": phones(d.get("ambulanceNo")),
                                                          "website": d.get("websiteLink")}))
    return out


@org("lazz", "Lazz Pharma Ltd", "লাজ ফার্মা", "health",
     ["https://lazzpharma.com/BranchLocation", "https://client.lazzpharma.com/FindStoreArea/FindStore/Get"])
def lazz():
    u = "https://client.lazzpharma.com/FindStoreArea/FindStore/Get"
    out = []
    for d in post(u, json={"filter": [], "pageNumber": 1, "pageSize": 1000}).json()["Data"]["Data"]:
        info = txt(d.get("ShortInformation"))
        soon = "coming soon" in (info + " " + txt(d.get("Name"))).lower()
        lat, lon = fnum(d.get("Lat")), fnum(d.get("Lng"))
        out.append(R("lazz", "pharmacy", d.get("Id"), "https://lazzpharma.com/BranchLocation", name_en="Lazz Pharma, " + txt(d.get("Name")),
                     category="health.pharmacy", address=txt(d.get("Location")), text=txt(d.get("Location")) + " , " + txt(d.get("Name")),
                     prefer="text", lat=lat, lon=lon, phone=phones(d.get("Mobile")),
                     email=emails(d.get("BranchEmail")), extra={"status": "coming soon" if soon else "", "info": info},
                     notes="Listed as 'coming soon'." if soon else ""))
    return out


@org("tamanna", "Tamanna Pharmacy", "তামান্না ফার্মেসি", "health", ["https://tamannapharmacy.com/all-branchs/"])
def tamanna():
    u = "https://tamannapharmacy.com/all-branchs/"
    out = []
    for tr in re.findall(r"(?s)<tr>(.*?)</tr>", get(u).text):
        c = tds(tr)
        if len(c) < 3 or not txt(c[0]).isdigit():
            continue
        a = re.split(r",?\s*Cell\s*:\s*\.?", txt(c[2]), maxsplit=1)
        out.append(R("tamanna", "pharmacy", sid_hash(txt(c[1]), a[0]), u, name_en="Tamanna Pharmacy, " + txt(c[1]), category="health.pharmacy",
                     address=a[0].strip(" ,"), text=a[0], prefer="text", phone=phones(a[1]) if len(a) > 1 else ""))
    return out


# ================================================================ e. supermarkets
@org("agora", "Agora (Rahimafrooz Superstores Ltd)", "আগোরা", "supermarket", ["https://agorasuperstores.com/outlets"])
def agora():
    u = "https://agorasuperstores.com/outlets"
    out = []
    for slug, card in re.findall(r'(?s)class="col-md-4 mb-4 outlet-card"\s+data-city="([^"]*)">(.*?)</div>\s*</div>\s*</div>', get(u).text):
        name = txt(re.search(r"(?s)<h5[^>]*>(.*?)</h5>", card).group(1))
        d = {k.lower(): txt(v) for k, v in re.findall(r"(?s)<strong>(\w+):</strong>(.*?)</p>", card)}
        out.append(R("agora", "outlet", sid_hash(name, d.get("address")), u, name_en="Agora, " + name, category="business.supermarket",
                     address=d.get("address", ""), text=name + " , " + d.get("address", ""), prefer="text", phone=phones(d.get("phone", "")),
                     extra={"agora_city_group": d.get("city") or slug}))
    return out


@org("meenabazar", "Meena Bazar (Gemcon Group)", "মীনা বাজার", "supermarket",
     ["https://meenabazaronline.com/", "https://mbonlineapi.com/api/front/outlet/list"])
def meenabazar():
    u = "https://mbonlineapi.com/api/front/outlet/list"
    out = []
    r = http("GET", u)
    for d in r.json()["data"]:
        addr = txt(d.get("SubUnitAddress"))
        out.append(R("meenabazar", "outlet", d.get("SubUnitId"), "https://meenabazaronline.com/", name_en="Meena Bazar, " + txt(d.get("SubUnitName")),
                     category="business.supermarket", address=addr, text=addr, prefer="text",
                     extra={"meenabazar_region": d.get("DivisionName"), "outlet_external_id": d.get("SubUnitExternalId")}))
    return out


# ================================================================ f. NGOs / microfinance
@org("brac", "BRAC", "ব্র্যাক", "ngo",
     ["https://explore.brac.net/program/branch-locations/", "https://explore.brac.net/templates/saga/branch/datatable.php"], "ngo")
def brac():
    u = "https://explore.brac.net/templates/saga/branch/datatable.php"
    hdr = {"Referer": "https://explore.brac.net/program/branch-locations/", "X-Requested-With": "XMLHttpRequest"}
    rows, start, total = [], 0, None
    while total is None or start < total:
        data = {"draw": 1, "start": start, "length": 500, "search[value]": "", "search[regex]": "false",
                "order[0][column]": 0, "order[0][dir]": "asc"}
        for i, c in enumerate(["district", "upazilla", "address", "contact"]):
            data[f"columns[{i}][data]"] = c
            data[f"columns[{i}][searchable]"] = "true"
            data[f"columns[{i}][orderable]"] = "true"
        j = json.loads(post(u, data=data, headers=hdr).content.decode("utf-8-sig"))
        total = int(j["iTotalRecords"])
        if not j["aaData"]:
            break
        rows += j["aaData"]
        start += len(j["aaData"])
    out = []
    for d in rows:
        addr = txt(d.get("address"))
        addr_only = re.sub(r"[\w.+-]+@[\w.-]+", "", addr)
        # some addresses carry the area / branch manager's mobile ('AM Mobi No 017…'): label and number removed
        addr_only = re.sub(r"(?i)((area|branch)\s*manager|\bAM\b|\bBM\b)?\s*(mob\w*|cell|contact|phone)?\s*(no\.?)?\s*[:\-]?\s*"
                           r"(\+?88)?0?1[3-9]\d{2}[-\s]?\d{3}[-\s]?\d{3}", " ", asc(addr_only))
        addr_only = re.sub(r"(?i)[\s.,]*\b(AM|BM)?\s*mob(ile|i)?\s*(no\.?)?\s*[:\-]?\s*$", "", re.sub(r"\s+", " ", addr_only)).strip(" ,;.-")
        area = bool(re.search(r"(?i)area office", addr))
        # 'contact' is one mobile per office, most likely the branch manager's own: not written
        out.append(R("brac", "area_office" if area else "branch_office", sid_hash(d.get("district"), d.get("upazilla"), addr),
                     "https://explore.brac.net/program/branch-locations/", name_en=("BRAC Area Office" if area else "BRAC Branch Office"),
                     category="other.ngo", address=addr_only, district=d.get("district") or "", upazila=d.get("upazilla") or "",
                     text=addr_only, extra={"programme": "BRAC microfinance", "district_published": d.get("district"),
                                            "upazila_published": d.get("upazilla")},
                     notes="Name composed as 'BRAC Branch/Area Office' (the list gives no office name; the address names the place)."))
    return out


@org("buro", "BURO Bangladesh", "বুরো বাংলাদেশ", "ngo",
     ["https://www.burobd.org/location", "https://www.burobd.org/thana-data", "https://www.burobd.org/branch-data"], "ngo")
def buro():
    def items(t, flag):
        return [{k: _html.unescape(v) for k, v in re.findall(r'data-([\w-]+)="([^"]*)"', tag)}
                for tag in re.findall(r'<div ([^>]*data-%s-item="true"[^>]*)>' % flag, t)]
    loc = get("https://www.burobd.org/location").text
    div = {d.get("division-slug"): d.get("division-name") for d in items(loc, "division")}
    dist = {d.get("district-slug"): d for d in items(loc, "district")}
    thana = {t.get("thana-slug"): t for t in items(get("https://www.burobd.org/thana-data").text, "thana")}
    out = []
    u = "https://www.burobd.org/branch-data"
    for b in items(get(u).text, "branch"):
        th = thana.get(b.get("thana-slug"), {})
        di = dist.get(th.get("district-slug"), {})
        # bm-number, am-number, ba-number, merchant (staff mobiles) and bm-email, am-email -> not written
        out.append(R("buro", "branch", b.get("br-code") or b.get("branch-slug"), "https://www.burobd.org/location",
                     name_en="BURO Bangladesh, " + (b.get("branch-name") or "") + " Branch", category="other.ngo",
                     address=b.get("branch-address") or "", district=di.get("district-name") or "", upazila=th.get("thana-name") or "",
                     division=div.get(di.get("division-slug")) or "", code=b.get("br-code") or "", text=b.get("branch-address") or "",
                     extra={"postal_code": re.sub(r"\D", "", b.get("postal-code") or ""), "buro_area": b.get("area-name"),
                            "buro_zone": b.get("zone"), "thana_published": th.get("thana-name")}))
    return out


@org("asa", "ASA", "আশা", "ngo", ["https://asa.org.bd/", "https://asa.org.bd/branchcoordinates/division-coordinates"], "ngo")
def asa():
    B = "https://asa.org.bd/branchcoordinates/"
    out = []
    for dv in get(B + "division-coordinates").json():
        out.append(R("asa", "divisional_office", f"div:{dv['Id']}", B + "division-coordinates", name_en=f"ASA Divisional Office, {dv.get('Division')}",
                     category="other.ngo", address=txt(dv.get("Address")), lat=fnum(dv.get("Latitude")), lon=fnum(dv.get("Logitude")),
                     text=txt(dv.get("Address")), prefer="point", extra={"asa_division": dv.get("Division")}))
        for ds in get(B + f"district-coordinates?DivisionId={dv['Id']}").json():
            out.append(R("asa", "district_office", f"dist:{ds['Id']}", B + "district-coordinates", name_en=f"ASA District Office, {ds.get('District')}",
                         category="other.ngo", address=txt(ds.get("Address")), lat=fnum(ds.get("Latitude")), lon=fnum(ds.get("Logitude")),
                         text=txt(ds.get("Address")), prefer="point", district=ds.get("District") or "", extra={"asa_division": dv.get("Division"), "asa_district": ds.get("District")}))
            for rg in get(B + f"region-coordinates?DistrictId={ds['Id']}").json():
                out.append(R("asa", "regional_office", f"reg:{rg['Id']}", B + "region-coordinates", name_en=f"ASA Regional Office, {rg.get('Region')}",
                             category="other.ngo", address=txt(rg.get("Address")), lat=fnum(rg.get("Latitude")), lon=fnum(rg.get("Logitude")),
                             text=txt(rg.get("Address")), prefer="point", district=ds.get("District") or "",
                             extra={"asa_division": dv.get("Division"), "asa_district": ds.get("District"), "asa_region": rg.get("Region")}))
                for br in get(B + f"branch-coordinates?RegionId={rg['Id']}").json():
                    out.append(R("asa", "branch", f"br:{br['Id']}", B + "branch-coordinates", name_en=f"ASA {br.get('Branch')} Branch",
                                 category="other.ngo", address=txt(br.get("Address")), lat=fnum(br.get("Latitude")), lon=fnum(br.get("Logitude")),
                                 text=txt(br.get("Address")), prefer="point", district=ds.get("District") or "",
                                 extra={"asa_division": dv.get("Division"), "asa_district": ds.get("District"), "asa_region": rg.get("Region")}))
    return out


# ---------------------------------------------------------------- what was checked and not used (for SOURCE.json / REPORT)
SKIPPED = [
    ("Sonali Bank — branch list", "https://www.sonalibank.com.bd/inland_branch.php",
     "the list is an iframe of /feedback/index.php/branches/get_branches; robots.txt disallows /feedback/* (ATMs and AD branches used)"),
    ("Pubali Bank", "https://www.pubalibangla.com/", "Cloudflare 'Just a moment' JavaScript challenge (HTTP 403) on every URL"),
    ("The City Bank", "https://www.citybankplc.com/locator",
     "locator data come only through a Next.js server action that proxies the site's /api/, which robots.txt disallows; treated as disallowed"),
    ("Southeast Bank", "https://www.southeastbank.com.bd/", "locator data endpoint needs an anti-automation request_validator_key"),
    ("National Bank", "https://www.nblbd.com/", "TLS error (incomplete certificate chain)"),
    ("Al-Arafah Islami Bank", "https://www.aibl.com.bd/", "connection timed out (twice, www and bare host)"),
    ("Ansar-VDP Unnayan Bank", "https://ansarvdpbank.gov.bd/", "HTTP 500 with an empty body on every URL including robots.txt"),
    ("One Bank / Mercantile Bank / HSBC", "https://www.onebank.com.bd/",
     "not collected this round (One Bank's list pairs every branch with its manager; Mercantile publishes only agent outlets with owners' names; HSBC has no locator)"),
    ("Grameenphone", "https://www.grameenphone.com/terms-use",
     "terms of use prohibit 'data mining, robots or similar data gathering and extraction tools' without GP's written consent"),
    ("Robi / Airtel (Cirkle)", "https://www.robi.com.bd/en/robi-sheba-locator",
     "terms forbid reproducing or storing any part of the site without Robi's prior written permission"),
    ("bKash", "https://www.bkash.com/", "Cloudflare JavaScript challenge (HTTP 403)"),
    ("Nagad", "https://nagad.com.bd/", "Cloudflare 'Attention Required' block (HTTP 403)"),
    ("Rocket (DBBL mobile banking)", "https://www.dutchbanglabank.com/rocket/rocket.html", "no list of service centres published"),
    ("Upay", "https://www.upaybd.com/service-location", "agent/merchant locator only (individual agents are out of scope)"),
    ("Pathao", "https://pathao.com/terms/", "terms forbid robots, spiders and data mining"),
    ("RedX", "https://redx.com.bd/coverage-area", "only delivery zones; pickup points need a merchant login"),
    ("Paperfly", "https://paperfly.com.bd/coverage", "only a district list with placeholder counts; no branch list"),
    ("Continental Courier", "https://continentalcourier.com.bd/", "TLS error (expired certificate)"),
    ("Korotoa / AJR Courier", "", "no official website found"),
    ("Delivery Tiger", "https://deliverytiger.com.bd/", "connection timed out"),
    ("Ibn Sina Trust", "https://www.ibnsinatrust.com/", "HTTP 403 for every URL including robots.txt"),
    ("Medinova Medical Services", "https://medinova.com.bd/", "'coming soon' placeholder, no list"),
    ("Praava Health / Prince Bazar / Khulshi Mart / Unimart", "",
     "one or two sites each, or names only (Unimart): left for manual entry"),
    ("Shwapno", "https://www.shwapno.com/our-outlets", "outlets load from /api/outlet…, which robots.txt disallows (Disallow: /api*)"),
    ("Grameen Bank", "https://www.grameenbank.org.bd/about/offices", "only zonal-office names; no branch list or addresses"),
    ("Shakti Foundation", "https://shakti.org.bd/terms_and_conditions", "terms forbid automated systems (bots, scraping tools) without permission"),
    ("TMSS / SSS / RDRS / Proshika", "", "site unreachable (timeout / DNS / TLS errors) or no list"),
    ("Jagorani Chakra Foundation", "https://jcf.org.bd/jcf-working-area/", "working-area district markers only, no branches"),
    ("PKSF partner list", "https://pksf.org.bd/partner-organizations/", "no partner/branch address list"),
]


# ---------------------------------------------------------------- placement and output
GAZ = None
BD_BOX = (20.5, 26.75, 88.0, 92.75)


def place(rec, branch_index):
    """Resolve district / upazila / coordinates of a normalised record. Returns (district, upazila, lat, lon, notes, how)."""
    notes = []
    extra = rec["extra"]
    lat, lon = rec["lat"], rec["lon"]
    if lat is not None and lon is not None:
        if not (BD_BOX[0] <= lat <= BD_BOX[1] and BD_BOX[2] <= lon <= BD_BOX[3]) and BD_BOX[0] <= lon <= BD_BOX[1] and BD_BOX[2] <= lat <= BD_BOX[3]:
            lat, lon = lon, lat
            notes.append("Published latitude/longitude were swapped; corrected.")
        if not (BD_BOX[0] <= lat <= BD_BOX[1] and BD_BOX[2] <= lon <= BD_BOX[3]):
            if lat or lon:
                extra["published_latlon"] = f"{rec['lat']},{rec['lon']}"
                notes.append("Published coordinates are outside Bangladesh; not used.")
            lat = lon = None
    else:
        lat = lon = None
    pt = GAZ.point(lat, lon) if lat is not None else None
    field_d = GAZ.district(rec["district"]) if rec["district"] else None
    text_hits = GAZ.find_districts(rec["text"] or rec["address"])
    text_d = text_hits[-1] if text_hits else None
    how = ""
    order = {"field": [("field", field_d), ("text", text_d), ("point", pt)],
             "text": [("text", text_d), ("field", field_d), ("point", pt)],
             "point": [("point", pt), ("field", field_d), ("text", text_d)]}[rec["prefer"]]
    dist = None
    for h, v in order:
        if v:
            dist, how = v, h
            break
    blob = " , ".join(x for x in (rec["district"], rec["upazila"], rec["text"] or rec["address"]) if x)
    upz_hint = None
    if not dist:
        hit = GAZ.by_upazila(blob)
        if hit:
            (dist, upz_hint), how = hit, "upazila"
            notes.append(f"District from the upazila named in the address ({upz_hint}).")
    if not dist:
        dist = GAZ.by_postcode(blob)
        if dist:
            how = "postcode"
            notes.append("District from the postcode in the address (Bangladesh Post postcode list).")
    if not dist:
        dist = GAZ.by_locality(blob)
        if dist:
            how = "locality"
            notes.append("District from a well-known metropolitan locality named in the address.")
    if not dist and rec["parent"]:
        pd = branch_index.get((rec["org"], rec["parent"].lower().strip()))
        if pd:
            dist, how = pd, "parent"
            notes.append(f"District taken from the controlling branch '{rec['parent']}'.")
    if dist and field_d and text_d and field_d != text_d and how in ("field", "text"):
        notes.append(f"The list's district field says {field_d} but the address names {text_d}; {dist} used.")
    if rec["district"] and not field_d:
        extra.setdefault("district_published", rec["district"])
    elif rec["district"] and field_d != rec["district"]:
        extra.setdefault("district_published", rec["district"])
    if how == "point":
        notes.append("District from the published coordinates (the list names none).")
    # coordinates must agree with the district
    if lat is not None and dist and pt != dist:
        extra["published_latlon"] = f"{rec['lat']},{rec['lon']}"
        notes.append(f"Published coordinates fall in {pt or 'no district'}, not {dist}; not used.")
        lat = lon = None
    upz = upz_hint
    if dist and not upz:
        if rec["upazila"]:
            upz = GAZ.upazila(dist, rec["upazila"])
            if rec["upazila"] != upz:
                extra.setdefault("upazila_published", rec["upazila"])
        if not upz:
            upz = GAZ.find_upazila(dist, rec["address"] or rec["text"])
    return dist, upz, lat, lon, notes, how


def build_rows(recs, key, orgs_by_slug):
    """Normalised records of all organisations -> {division: [place rows]} + stats."""
    # index: (org, branch name) -> district, from branch rows placed by field/text
    bidx = {}
    placed = []
    for r in recs:
        res = place(r, {})
        placed.append([r, res])
        if res[0] and r["kind"] in ("branch", "ad_branch") and (r["name_en"] or r["name_bn"]):
            for nm in (r["name_en"], r["name_bn"]):
                if nm:
                    base = re.sub(r",.*$", "", nm).strip()
                    for k in (nm, re.sub(r"(?i)\s*branch$", "", nm), base, re.sub(r"(?i)\s*branch$", "", base)):
                        bidx[(r["org"], k.lower().strip())] = res[0]
    for p in placed:
        if not p[1][0] and p[0]["parent"]:
            par = p[0]["parent"].lower().strip()
            for k in (par, re.sub(r"(?i)\s*branch$", "", par).strip(), re.sub(r"(?i),.*$", "", par).strip()):
                if (p[0]["org"], k) in bidx:
                    p[1] = place(p[0], {(p[0]["org"], p[0]["parent"].lower().strip()): bidx[(p[0]["org"], k)]})
                    break
    by_div, unplaced, seen = {}, {}, set()
    for r, (dist, upz, lat, lon, notes, how) in placed:
        o = orgs_by_slug[r["org"]]
        if not dist:
            unplaced[r["org"]] = unplaced.get(r["org"], 0) + 1
            continue
        div = GAZ.div_of[dist]
        sid = f"{r['org']}:{r['sid']}" if ":" in r["sid"] else f"{r['org']}:{r['kind']}:{r['sid']}"
        n = 2
        base = sid
        while sid in seen:
            sid = f"{base}#{n}"
            n += 1
        seen.add(sid)
        ex = dict(r["extra"])
        ex.update(organisation=o["name_en"], organisation_bn=o["name_bn"], outlet_kind=r["kind"])
        if r["routing"]:
            ex["routing_number"] = re.sub(r"\D", "", asc(r["routing"])) or r["routing"]
        if r["code"]:
            ex["branch_code"] = asc(r["code"])
        if r["division"]:
            ex.setdefault("division_published", r["division"])
        if how:
            ex["district_from"] = how
        nm_en, nm_bn = re.sub(r"\s+", " ", r["name_en"] or "").strip(" ,"), re.sub(r"\s+", " ", r["name_bn"] or "").strip(" ,")
        short_en = o["name_en"].replace(" PLC", "").replace(" Ltd", "").replace(" (Pvt)", "")
        if nm_en and not _mentions(nm_en, o):
            ex["published_name"] = nm_en
            nm_en = f"{short_en}, {nm_en}"
        if nm_bn and not _mentions(nm_bn, o):
            ex["published_name_bn"] = nm_bn
            nm_bn = f"{o['name_bn'].replace(' পিএলসি', '')}, {nm_bn}"
        note = " ".join(["As published by the organisation on its own website; not independently verified."] + notes + ([r["notes"]] if r["notes"] else []))
        by_div.setdefault(div, []).append(dict(
            source_key=key(div), source_id=sid, name_bn=nfc(nm_bn), name_en=nfc(nm_en), category_key=r["category"],
            lat=f"{lat:.6f}" if lat is not None else "", lon=f"{lon:.6f}" if lon is not None else "",
            address=nfc(r["address"]), district_en=dist, upazila_en=upz or "", phone=r["phone"], website="",
            email=r["email"], opening_hours=r["hours"], operator=o["name_en"], ownership=o["ownership"], extra_json=xj(ex),
            source_url=r["url"], notes=note))
    return by_div, unplaced


def _mentions(name, o):
    n = name.lower()
    first = o["name_en"].split()[0].lower().strip(".,")
    return first in n or (o["name_bn"].split()[0] in name)


def keyname(div):
    return f"ORG_BRANCHES_{DIVISIONS[div].upper()}_2026"


def folder(div):
    return f"org_branches_{DIVISIONS[div]}_2026"


def write_division(div, rows, out, results, unplaced, today):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rows.sort(key=lambda r: (r["source_id"]))
    with open(out / "places.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=PLACE_COLS)
        w.writeheader()
        w.writerows(rows)
    used = [o for o in ORGS if results.get(o["slug"], {}).get("status") == "ok"]
    urls = []
    for o in used:
        for u in o["urls"]:
            if u not in urls:
                urls.append(u)
    counts = {}
    for r in rows:
        org_ = json.loads(r["extra_json"])["organisation"]
        counts.setdefault(org_, {}).setdefault(r["category_key"], 0)
        counts[org_][r["category_key"]] += 1
    meta = dict(
        key=keyname(div), division=div, kind="org_branches",
        name=f"Organisations' own branch and outlet lists — {div.title()} Division",
        organization="Various organisations (each row's organisation in extra_json.organisation)",
        source_type="institution_website", trust_level=3, urls=urls, accessed=today, publication_date=None,
        license=None, license_url=None,
        attribution="Branch / outlet lists published by the organisations on their own websites (see urls)",
        notes=("Each row is a branch, sub-branch, ATM/CRM, agent outlet, service centre, hub or office exactly as its organisation "
               "lists it; not independently verified. District/upazila normalised to the seed's English names (published values "
               "kept in extra_json). Coordinates only where the organisation publishes them and they fall inside the row's "
               "district. Staff names, managers' and agents' mobiles and personal e-mails are not collected. No licence stated "
               "by any of the sites: factual data only. Checked and not used: " +
               "; ".join(f"{n} ({why})" for n, u, why in SKIPPED) + "."),
        files={"places.csv": hashlib.sha256((out / "places.csv").read_bytes()).hexdigest()})
    (out / "SOURCE.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(div, rows, out, results, unplaced, counts, today)
    print(f"{div}: {len(rows)} rows -> {out}")


def write_report(div, rows, out, results, unplaced, counts, today):
    cat_tot = {}
    for r in rows:
        cat_tot[r["category_key"]] = cat_tot.get(r["category_key"], 0) + 1
    with_pt = sum(1 for r in rows if r["lat"])
    with_upz = sum(1 for r in rows if r["upazila_en"])
    L = [f"# {keyname(div)} — organisations' own branch / outlet lists, {div.title()} Division", "",
         f"Generated by `fetch.py` ({'--division ' + div}) on {today}. Source type `institution_website`, trust level 3. "
         "Every row is **as published by the organisation** on its own website and is **not independently verified** "
         "(`notes` says so on each row); the organisation is named in `extra_json.organisation` and `operator`.", "",
         f"**{len(rows)} places**: " + ", ".join(f"{k} {v}" for k, v in sorted(cat_tot.items())) +
         f". {with_pt} with coordinates, {with_upz} with an upazila.", "",
         "## By organisation", "", "| Organisation | Rows in this division | By category | National list |", "|---|---|---|---|"]
    for o in ORGS:
        res = results.get(o["slug"])
        if not res:
            continue
        c = counts.get(o["name_en"], {})
        nat = (f"{res['n']} rows ({', '.join(f'{k} {v}' for k, v in sorted(res['kinds'].items()))}); "
               f"{unplaced.get(o['slug'], 0)} without a district") if res["status"] == "ok" else "failed: " + res["error"]
        L.append(f"| {o['name_en']} | {sum(c.values())} | {', '.join(f'{k} {v}' for k, v in sorted(c.items())) or '—'} | {nat} |")
    L += ["", "## How rows were placed", "",
          "- District: the list's own district field where it has one (spelling normalised to `data/seed/geo/admin_areas.csv`; "
          "the published value is kept as `district_published`), else the last district named in the address, else the "
          "published coordinates (point in `districts.geojson`); then, only if none of these names a district: a seed upazila "
          "named in the address whose name is unique in the country, a postcode (Bangladesh Post list, `bdpost_postcodes_*` "
          "sources), a well-known metropolitan locality (Motijheel, Agrabad …), or the controlling branch's district. "
          "ASA publishes coordinates and village names only, so ASA rows are placed by their coordinates first (its own "
          "district-office unit is the fallback). `extra_json.district_from` says which rule placed the row (`field`, "
          "`text`, `point`, `upazila`, `postcode`, `locality`, `parent`). Rows with no district are left out (counted above as "
          "'without a district').",
          "- Upazila: the list's upazila/thana field matched within the district, else a seed upazila named in the address. "
          "Metropolitan areas (e.g. Gulshan, Kotwali) are not upazilas and stay empty.",
          "- Coordinates: only as published; swapped lat/lon corrected; points outside Bangladesh or outside the row's district "
          "are dropped (kept in `extra_json.published_latlon`, with a note).",
          "- Names: the organisation's short name is prefixed when the published name lacks it; the published name is kept in "
          "`extra_json.published_name`. Branch code, routing number, SWIFT, outlet type, controlling branch, opening dates are in "
          "`extra_json` where published.",
          "", "## Categories", "",
          "`finance.bank` branches, sub-branches, AD branches, agent-banking outlets (outlet type in `extra_json.outlet_kind`); "
          "`finance.atm` ATMs, CRMs, CDMs, ADMs and booths; `business.service` operators' care centres / service points and "
          "courier branches / hubs; `health.diagnostic_center`, `health.hospital`, `health.pharmacy`; `business.supermarket`; "
          "`other.ngo` NGO / microfinance offices.",
          "Proposed taxonomy keys (not used until added): `finance.agent_banking` (agent-banking outlets), `business.courier` "
          "(courier / parcel branches and hubs), `business.telecom_service` (mobile-operator care centres), "
          "`finance.microfinance` (NGO-MFI branch offices).",
          "", "## Privacy filters", "",
          "Not collected: managers' / officers' names and designations (Agrani, RAKUB, BDBL, Palli Sanchay, Rupali 'In Charge', "
          "Popular; IBBL's and DBBL's branch detail pages, which name managers, are not read), agent outlet owners' names, mobiles and e-mails (all banks' agent lists), "
          "officer mobiles tagged (HOB)/(OM) (UCB) or 'Manager' (Bank Asia), Teletalk 'ইনচার্জ' numbers, BRAC office mobiles "
          "(likely the branch manager's), BURO staff numbers/e-mails, Janani Express gmail addresses, Labaid staff e-mails. "
          "RAKUB mobiles are limited to the bank's 01708806xxx branch series.",
          "", "## Checked and not used", ""]
    L += [f"- **{n}**: {why}" + (f" ({u})" if u else "") for n, u, why in SKIPPED]
    L += ["", "## Data-quality notes", "",
          "- Lists are as current as each website (Nov 2026); several are old (Dhaka Bank ATM/ADM rows last edited 2015–17; "
          "DBBL sub-branch addresses are often just a building). Closed rows are skipped where the site marks them (UCB, AB Bank).",
          "- Some sources mix kinds (MTB's branch feed includes sub-branches; IBBL's ATM list flags CRMs).",
          "- A district field can be wrong (BRAC Bank, IFIC ATMs, UCB `data-district`): for those sources the address is preferred "
          "and conflicts are noted on the row.",
          "- Phone numbers are the branch / office numbers as listed (many organisations publish branch mobiles).",
          "- Bangladesh Krishi Bank has no branches in Rajshahi and Rangpur divisions (Rajshahi Krishi Unnayan Bank serves them).",
          "- `raw/` is not committed: the national lists are large (DBBL's ATM page ~6 MB, MTB's page ~60 MB, Popular's JS bundle "
          "~16 MB); `fetch.py` rebuilds everything (about 1 h, mostly Rupali's ~590 branch-detail pages and ASA's ~780 office "
          "lookups at 1.2 s per request). `--all-divisions` fetches each national list once and writes all eight folders.",
          "- Grameenphone: while scouting, about 64 store-locator requests were made before its terms of use (which forbid "
          "automated collection) were found; that data was deleted and nothing from it is used.",
          "", "## Licence", "", "No site states a licence. Only facts (names, addresses, codes, contacts, coordinates) are taken.", ""]
    (out / "REPORT.md").write_text("\n".join(L), encoding="utf-8")


def main():
    global GAZ, HTTP_CACHE, DETAILS
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().split("\n")[0])
    ap.add_argument("--division", default="rajshahi", choices=list(DIVISIONS))
    ap.add_argument("--all-divisions", action="store_true")
    ap.add_argument("--out", help="output folder (single division only)")
    ap.add_argument("--only", help="comma-separated organisation slugs")
    ap.add_argument("--cache", help="folder for normalised national lists (reused when present)")
    ap.add_argument("--http-cache", help="development: folder for raw HTTP responses")
    ap.add_argument("--no-details", action="store_true", help="skip per-branch detail pages (Rupali routing numbers)")
    a = ap.parse_args()
    DETAILS = not a.no_details
    if a.http_cache:
        HTTP_CACHE = a.http_cache
        os.makedirs(HTTP_CACHE, exist_ok=True)
    if a.all_divisions and a.out:
        raise SystemExit("--out works with a single --division")
    GAZ = Gazetteer()
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
            kinds = {}
            for r in got:
                kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
            results[o["slug"]] = dict(status="ok", n=len(got), kinds=kinds)
            recs += got
            print(f"  {o['slug']}: {len(got)} {kinds}", flush=True)
        except Exception as e:
            results[o["slug"]] = dict(status="failed", error=str(e)[:300], n=0, kinds={})
            print(f"  {o['slug']} FAILED: {e}", flush=True)
            traceback.print_exc(limit=2)
    orgs_by_slug = {o["slug"]: o for o in ORGS}
    by_div, unplaced = build_rows(recs, keyname, orgs_by_slug)
    divs = list(DIVISIONS) if a.all_divisions else [a.division]
    for div in divs:
        out = a.out if a.out else (HERE if div == "rajshahi" else HERE.parent / folder(div))
        write_division(div, by_div.get(div, []), out, results, unplaced, today)
    print("without district:", unplaced)


if __name__ == "__main__":
    main()
