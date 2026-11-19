#!/usr/bin/env python3
"""Fetch the DPE IPEMIS primary-school directory for one division, default Rajshahi (stdlib + requests only).

Usage: python3 fetch.py [--offline]   (--offline rebuilds the CSVs from raw/ and keeps previously fetched live statistics).
       python3 fetch.py --division rangpur [--out DIR] [--offline] [--resume]
           another division (see ../DIVISIONS.md); default output is the sibling folder dpe_ipemis_primary_<code>_2026,
           the Rajshahi files are never touched.
       --resume  reuse the JSON responses cached in <out>/.partial/ by an interrupted run (every successful response
                 is cached there during a run; the folder is deleted when the run completes)."""
import argparse as _argparse
# division -> (code from DIVISIONS.md, IPEMIS divisionId from the search page's division <select>)
DIVISIONS = {"rajshahi": ("raj", 1), "khulna": ("khl", 2), "dhaka": ("dhk", 3), "chattogram": ("ctg", 4),
             "barishal": ("bar", 5), "sylhet": ("syl", 6), "rangpur": ("rang", 7), "mymensingh": ("mym", 8)}
_ap = _argparse.ArgumentParser()
_ap.add_argument("--division", default="rajshahi", choices=sorted(DIVISIONS))
_ap.add_argument("--out", default=None, help="output folder (default: this folder for Rajshahi, else the sibling folder)")
_ap.add_argument("--offline", action="store_true", help="rebuild from raw/ in the output folder without network")
_ap.add_argument("--resume", action="store_true", help="reuse responses cached in <out>/.partial/ by an interrupted run")
ARGS = _ap.parse_args()
DIV = ARGS.division
DIVT = DIV.title()
CODE, DIVISION_ID = DIVISIONS[DIV]  # DIVISION_ID: IPEMIS id of the division
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

# --- admin-name normalisation (source spellings -> standard English names) ------------------------------
import re as _re
_RAJ_DISTRICTS = ["Rajshahi", "Natore", "Naogaon", "Chapainawabganj", "Bogura", "Joypurhat", "Pabna", "Sirajganj"]
_RAJ_DISTRICT_ALIASES = {
    "rajshahi": "Rajshahi", "natore": "Natore", "naogaon": "Naogaon", "chapainawabganj": "Chapainawabganj",
    "chapainawabgonj": "Chapainawabganj", "nawabganj": "Chapainawabganj", "bogura": "Bogura", "bogra": "Bogura",
    "joypurhat": "Joypurhat", "jaipurhat": "Joypurhat", "pabna": "Pabna", "sirajganj": "Sirajganj", "sirajgonj": "Sirajganj",
}
# metropolitan thanas of Rajshahi City (not upazilas)
_RAJ_METRO_THANAS = {"Boalia", "Rajpara", "Motihar", "Shah Makhdum"}
_RAJ_UPAZILA_ALIASES = {
    # Rajshahi
    "bagha": "Bagha", "baghmara": "Bagmara", "bagmara": "Bagmara", "charghat": "Charghat", "durgapur": "Durgapur",
    "godagari": "Godagari", "mohanpur": "Mohanpur", "mohonpur": "Mohanpur", "paba": "Paba", "puthia": "Puthia",
    "tanore": "Tanore", "boalia": "Boalia", "boaliasadar": "Boalia", "rajpara": "Rajpara", "matihar": "Motihar",
    "motihar": "Motihar", "shahmakhdum": "Shah Makhdum",
    # Bogura
    "adamdighi": "Adamdighi", "bograsadar": "Bogura Sadar", "bogurasadar": "Bogura Sadar", "dhunat": "Dhunat",
    "dhunut": "Dhunat", "dhupchanchia": "Dhupchanchia", "dhupchachia": "Dhupchanchia", "gabtali": "Gabtali",
    "gabtoli": "Gabtali", "kahaloo": "Kahaloo", "nandigram": "Nandigram", "sariakandi": "Sariakandi",
    "shariakandi": "Sariakandi", "shajahanpur": "Shajahanpur", "sherpur": "Sherpur", "shibganj": "Shibganj",
    "shibgonj": "Shibganj", "sonatola": "Sonatala", "sonatala": "Sonatala", "shonatola": "Sonatala",
    # Joypurhat
    "akkelpur": "Akkelpur", "joypurhatsadar": "Joypurhat Sadar", "jaipurhatsadar": "Joypurhat Sadar", "kalai": "Kalai",
    "khetlal": "Khetlal", "panchbibi": "Panchbibi", "pachbibi": "Panchbibi",
    # Naogaon
    "atrai": "Atrai", "badalgachhi": "Badalgachhi", "dhamoirhat": "Dhamoirhat", "dhamurhat": "Dhamoirhat",
    "mahadebpur": "Mohadevpur", "mohadebpur": "Mohadevpur", "mohadevpur": "Mohadevpur", "manda": "Manda",
    "naogaonsadar": "Naogaon Sadar", "niamatpur": "Niamatpur", "patnitala": "Patnitala", "porsha": "Porsha",
    "raninagar": "Raninagar", "sapahar": "Sapahar", "shapahar": "Sapahar",
    # Natore
    "bagatipara": "Bagatipara", "baraigram": "Baraigram", "gurudaspur": "Gurudaspur", "gurudashpur": "Gurudaspur",
    "lalpur": "Lalpur", "naldanga": "Naldanga", "natoresadar": "Natore Sadar", "singra": "Singra", "shingra": "Singra",
    # Chapainawabganj
    "bholahat": "Bholahat", "chapainawabganjsadar": "Chapainawabganj Sadar",
    "chapainawabgonjsadar": "Chapainawabganj Sadar", "gomastapur": "Gomastapur", "nachole": "Nachole",
    "nachol": "Nachole",
    # Pabna
    "atgharia": "Atgharia", "bera": "Bera", "bhangura": "Bhangura", "chatmohar": "Chatmohar", "chatmahar": "Chatmohar",
    "faridpur": "Faridpur", "ishwardi": "Ishwardi", "pabnasadar": "Pabna Sadar", "santhia": "Santhia",
    "sujanagar": "Sujanagar",
    # Sirajganj
    "belkuchi": "Belkuchi", "chauhali": "Chauhali", "chowhali": "Chauhali", "kamarkhanda": "Kamarkhanda",
    "kazipur": "Kazipur", "royganj": "Raiganj", "raygonj": "Raiganj", "raiganj": "Raiganj",
    "shahjadpur": "Shahjadpur", "shajadpur": "Shahjadpur", "sirajganjsadar": "Sirajganj Sadar",
    "sirajgonjsadar": "Sirajganj Sadar", "tarash": "Tarash", "ullahpara": "Ullahpara", "ullapara": "Ullahpara",
}
# Rangpur Division (keys are _key() of the spellings seen in the BANBEIS / IPEMIS / HRIS lists)
_RANG_DISTRICTS = ["Rangpur", "Dinajpur", "Gaibandha", "Kurigram", "Lalmonirhat", "Nilphamari", "Panchagarh", "Thakurgaon"]
_RANG_DISTRICT_ALIASES = {
    "rangpur": "Rangpur", "dinajpur": "Dinajpur", "gaibandha": "Gaibandha", "kurigram": "Kurigram",
    "lalmonirhat": "Lalmonirhat", "nilphamari": "Nilphamari", "panchagarh": "Panchagarh", "thakurgaon": "Thakurgaon",
}
# metropolitan thanas of Rangpur City (Rangpur Metropolitan Police)
_RANG_METRO_THANAS = {"Kotwali", "Tajhat", "Mahiganj", "Haragach", "Parshuram", "Hajirhat"}
_RANG_UPAZILA_ALIASES = {
    # Dinajpur
    "biral": "Biral", "birol": "Biral", "birampur": "Birampur", "birganj": "Birganj", "birgonj": "Birganj",
    "bochaganj": "Bochaganj", "bochagonj": "Bochaganj", "chirirbandar": "Chirirbandar", "dinajpursadar": "Dinajpur Sadar",
    "fulbari": "Fulbari", "ghoraghat": "Ghoraghat", "hakimpur": "Hakimpur", "kaharole": "Kaharole", "kaharol": "Kaharole",
    "khansama": "Khansama", "khanshama": "Khansama", "nawabganj": "Nawabganj", "nawabgonj": "Nawabganj",
    "parbatipur": "Parbatipur", "parbotipur": "Parbatipur",
    # Gaibandha
    "fulchhari": "Fulchhari", "fulchari": "Fulchhari", "phulchari": "Fulchhari", "phulchhari": "Fulchhari",
    "gaibandhasadar": "Gaibandha Sadar", "gobindaganj": "Gobindaganj", "gobindogonj": "Gobindaganj",
    "gobindagonj": "Gobindaganj", "palashbari": "Palashbari", "sadullapur": "Sadullapur", "shadullapur": "Sadullapur",
    "saghata": "Saghata", "shaghata": "Saghata", "sundarganj": "Sundarganj", "sundargonj": "Sundarganj",
    "shundorgonj": "Sundarganj",
    # Kurigram ("Fulbari" of Kurigram is Phulbari; district-qualified key)
    "bhurungamari": "Bhurungamari", "charrajibpur": "Char Rajibpur", "rajibpur": "Char Rajibpur", "chilmari": "Chilmari",
    "kurigramsadar": "Kurigram Sadar", "nageshwari": "Nageshwari", "nageswari": "Nageshwari", "phulbari": "Phulbari",
    "kurigram/fulbari": "Phulbari", "rajarhat": "Rajarhat", "raumari": "Raumari", "rowmari": "Raumari", "ulipur": "Ulipur",
    # Lalmonirhat
    "aditmari": "Aditmari", "hatibandha": "Hatibandha", "kaliganj": "Kaliganj", "kaligonj": "Kaliganj",
    "lalmonirhatsadar": "Lalmonirhat Sadar", "patgram": "Patgram",
    # Nilphamari
    "dimla": "Dimla", "domar": "Domar", "jaldhaka": "Jaldhaka", "kishoreganj": "Kishoreganj", "kishoregonj": "Kishoreganj",
    "kishorganj": "Kishoreganj", "nilphamarisadar": "Nilphamari Sadar", "nilphamarisadarupaz": "Nilphamari Sadar",
    "saidpur": "Saidpur", "syedpur": "Saidpur",
    # Panchagarh
    "atwari": "Atwari", "boda": "Boda", "debiganj": "Debiganj", "debigonj": "Debiganj",
    "panchagarhsadar": "Panchagarh Sadar", "tentulia": "Tentulia", "tetulia": "Tentulia",
    # Rangpur
    "badarganj": "Badarganj", "badargonj": "Badarganj", "gangachara": "Gangachara", "gangachhara": "Gangachara",
    "kaunia": "Kaunia", "kawnia": "Kaunia", "mithapukur": "Mithapukur", "pirgachha": "Pirgachha", "pirgacha": "Pirgachha",
    "pirganj": "Pirganj", "pirgonj": "Pirganj", "rangpursadar": "Rangpur Sadar", "taraganj": "Taraganj",
    "taragonj": "Taraganj",
    "kotwali": "Kotwali", "tajhat": "Tajhat", "mahiganj": "Mahiganj", "haragach": "Haragach", "parshuram": "Parshuram",
    "hajirhat": "Hajirhat",
    # Thakurgaon (Ruhia and Bhulli are thanas that IPEMIS lists as separate units)
    "baliadangi": "Baliadangi", "haripur": "Haripur", "horipur": "Haripur", "ranisankail": "Ranisankail",
    "ranishonkoil": "Ranisankail", "thakurgaonsadar": "Thakurgaon Sadar", "ruhia": "Ruhia", "bhulli": "Bhulli",
    "vulli": "Bhulli",
}
# thanas that a source lists as if they were upazilas (not metropolitan)
_RANG_OTHER_THANAS = {"Ruhia", "Bhulli"}
# Dhaka Division (keys are _key() of the spellings seen in the BANBEIS / IPEMIS lists)
_DHK_DISTRICTS = ["Dhaka", "Faridpur", "Gazipur", "Gopalganj", "Kishoreganj", "Madaripur", "Manikganj", "Munshiganj",
                  "Narayanganj", "Narsingdi", "Rajbari", "Shariatpur", "Tangail"]
_DHK_DISTRICT_ALIASES = {
    "dhaka": "Dhaka", "faridpur": "Faridpur", "gazipur": "Gazipur", "gopalganj": "Gopalganj", "gopalgonj": "Gopalganj",
    "kishoreganj": "Kishoreganj", "kishorgonj": "Kishoreganj", "kishoregonj": "Kishoreganj", "kishorganj": "Kishoreganj",
    "madaripur": "Madaripur", "manikganj": "Manikganj", "manikgonj": "Manikganj", "munshiganj": "Munshiganj",
    "munshigonj": "Munshiganj", "narayanganj": "Narayanganj", "narayangonj": "Narayanganj", "narsingdi": "Narsingdi",
    "narshingdi": "Narsingdi", "rajbari": "Rajbari", "shariatpur": "Shariatpur", "tangail": "Tangail",
}
# Dhaka Metropolitan Police thanas inside Dhaka city, kept as the source names them (not upazilas). BANBEIS uses the
# present DMP thanas; IPEMIS uses 12 older city thana units (Mirpur, Mohammadpur, Dhanmondi, Lalbag, Kotwali, Sutrapur,
# Cantonment, Motijheel, Ramna, Tejgaon, Gulshan, Demra).
_DHK_METRO = {
    "adabor": "Adabor", "badda": "Badda", "banani": "Banani", "bangshal": "Bangshal", "bhasantek": "Bhasan Tek",
    "bhatara": "Bhatara", "bimanbandar": "Biman Bandar", "cantonment": "Cantonment", "chakbazar": "Chak Bazar",
    "dakshinkhan": "Dakshinkhan", "darussalam": "Darus Salam", "demra": "Demra", "dhanmondi": "Dhanmondi",
    "gendaria": "Gendaria", "gulshan": "Gulshan", "hazaribagh": "Hazaribagh", "jatrabari": "Jatrabari",
    "kadamtali": "Kadamtali", "kafrul": "Kafrul", "kalabagan": "Kalabagan", "kamrangirchar": "Kamrangir Char",
    "khilgaon": "Khilgaon", "khilkhet": "Khilkhet", "kotwali": "Kotwali", "lalbagh": "Lalbagh", "lalbag": "Lalbag",
    "mirpur": "Mirpur", "mohammadpur": "Mohammadpur", "motijheel": "Motijheel", "mugdapara": "Mugda Para",
    "newmarket": "New Market", "pallabi": "Pallabi", "paltan": "Paltan", "ramna": "Ramna", "rampura": "Rampura",
    "rupnagar": "Rupnagar", "sabujbagh": "Sabujbagh", "shahali": "Shah Ali", "shahbagh": "Shahbagh",
    "shahjahanpur": "Shahjahanpur", "sherebanglanagar": "Sher-E-Bangla Nagar", "shyampur": "Shyampur",
    "sutrapur": "Sutrapur", "tejgaon": "Tejgaon", "tejgaonindarea": "Tejgaon Ind. Area", "turag": "Turag",
    "uttarkhan": "Uttar Khan", "uttara": "Uttara", "uttarapaschim": "Uttara Paschim", "wari": "Wari",
}
_DHK_METRO_THANAS = set(_DHK_METRO.values())
_DHK_UPAZILA_ALIASES = dict(_DHK_METRO, **{
    # Dhaka
    "dhamrai": "Dhamrai", "dohar": "Dohar", "keraniganj": "Keraniganj", "keranigonj": "Keraniganj",
    "nawabganj": "Nawabganj", "savar": "Savar",
    # Faridpur
    "alfadanga": "Alfadanga", "alphadanga": "Alfadanga", "bhanga": "Bhanga", "boalmari": "Boalmari",
    "charbhadrasan": "Char Bhadrasan", "charbhardrason": "Char Bhadrasan", "faridpursadar": "Faridpur Sadar",
    "madhukhali": "Madhukhali", "nagarkanda": "Nagarkanda", "sadarpur": "Sadarpur", "shaltha": "Saltha",
    "saltha": "Saltha",
    # Gazipur (IPEMIS lists Tongi, a thana of Gazipur City, as its own unit)
    "gazipursadar": "Gazipur Sadar", "kaliakair": "Kaliakair", "kaliakoir": "Kaliakair", "kaliganj": "Kaliganj",
    "kaligonj": "Kaliganj", "kapasia": "Kapasia", "sreepur": "Sreepur", "tongi": "Tongi",
    # Gopalganj
    "gopalganjsadar": "Gopalganj Sadar", "gopalgonjsadar": "Gopalganj Sadar", "kashiani": "Kashiani",
    "kotalipara": "Kotalipara", "muksudpur": "Muksudpur", "maksudpur": "Muksudpur", "tungipara": "Tungipara",
    "tongipara": "Tungipara",
    # Kishoreganj
    "austagram": "Austagram", "astogram": "Austagram", "bajitpur": "Bajitpur", "bhairab": "Bhairab",
    "bhairob": "Bhairab", "hossainpur": "Hossainpur", "itna": "Itna", "karimganj": "Karimganj", "karimgonj": "Karimganj",
    "katiadi": "Katiadi", "kishoreganjsadar": "Kishoreganj Sadar", "kishoregonjsadar": "Kishoreganj Sadar",
    "kuliarchar": "Kuliarchar", "mithamain": "Mithamain", "mithamoin": "Mithamain", "nikli": "Nikli",
    "pakundia": "Pakundia", "tarail": "Tarail",
    # Madaripur
    "dasar": "Dasar", "kalkini": "Kalkini", "madaripursadar": "Madaripur Sadar", "rajoir": "Rajoir", "razoir": "Rajoir",
    "shibchar": "Shibchar",
    # Manikganj
    "daulatpur": "Daulatpur", "ghior": "Ghior", "harirampur": "Harirampur", "manikganjsadar": "Manikganj Sadar",
    "manikgonjsadar": "Manikganj Sadar", "saturia": "Saturia", "shibalaya": "Shibalaya", "shibaloy": "Shibalaya",
    "singair": "Singair",
    # Munshiganj
    "gazaria": "Gazaria", "lohajang": "Lohajang", "lowhajang": "Lohajang", "munshiganjsadar": "Munshiganj Sadar",
    "munshigonjsadar": "Munshiganj Sadar", "serajdikhan": "Sirajdikhan", "sirajdikhan": "Sirajdikhan",
    "sreenagar": "Sreenagar", "tongibari": "Tongibari",
    # Narayanganj
    "araihazar": "Araihazar", "bandar": "Bandar", "narayanganjsadar": "Narayanganj Sadar",
    "narayangonjsadar": "Narayanganj Sadar", "rupganj": "Rupganj", "rupgonj": "Rupganj", "sonargaon": "Sonargaon",
    # Narsingdi
    "belabo": "Belabo", "manohardi": "Monohardi", "monohardi": "Monohardi", "monohordi": "Monohardi", "narsingdisadar": "Narsingdi Sadar",
    "palash": "Palash", "raipura": "Raipura", "roypura": "Raipura", "raypura": "Raipura", "shibpur": "Shibpur",
    # Rajbari
    "baliakandi": "Baliakandi", "goalanda": "Goalanda", "kalukhali": "Kalukhali", "pangsha": "Pangsha",
    "rajbarisadar": "Rajbari Sadar",
    # Shariatpur
    "bhedarganj": "Bhedarganj", "bhedorganj": "Bhedarganj", "damudya": "Damudya", "damudda": "Damudya",
    "gosairhat": "Gosairhat", "goshairhat": "Gosairhat", "naria": "Naria", "shariatpursadar": "Shariatpur Sadar",
    "zanjira": "Zanjira", "jajira": "Zanjira",
    # Tangail
    "basail": "Basail", "bashail": "Basail", "bhuapur": "Bhuapur", "delduar": "Delduar", "dhanbari": "Dhanbari",
    "ghatail": "Ghatail", "gopalpur": "Gopalpur", "kalihati": "Kalihati", "madhupur": "Madhupur", "modhupur": "Madhupur",
    "mirzapur": "Mirzapur", "nagarpur": "Nagarpur", "sakhipur": "Sakhipur", "shokhipur": "Sakhipur",
    "tangailsadar": "Tangail Sadar",
})
_DHK_OTHER_THANAS = {"Tongi"}
# Chattogram Division (keys are _key() of the spellings seen in the BANBEIS / IPEMIS / HRIS lists)
_CTG_DISTRICTS = ["Chattogram", "Bandarban", "Brahmanbaria", "Chandpur", "Cox's Bazar", "Cumilla", "Feni", "Khagrachhari",
                  "Lakshmipur", "Noakhali", "Rangamati"]
_CTG_DISTRICT_ALIASES = {
    "chattogram": "Chattogram", "chittagong": "Chattogram", "bandarban": "Bandarban", "brahmanbaria": "Brahmanbaria",
    "brahmonbaria": "Brahmanbaria", "brahamanbaria": "Brahmanbaria", "chandpur": "Chandpur", "coxsbazar": "Cox's Bazar", "coxbazar": "Cox's Bazar",
    "cumilla": "Cumilla", "comilla": "Cumilla", "feni": "Feni", "khagrachhari": "Khagrachhari",
    "khagrachari": "Khagrachhari", "lakshmipur": "Lakshmipur", "laxmipur": "Lakshmipur", "luxmipur": "Lakshmipur",
    "noakhali": "Noakhali", "rangamati": "Rangamati",
}
# Chattogram Metropolitan Police thanas inside Chattogram city, kept as the source spells them (not upazilas; only
# case and spacing normalised, e.g. IPEMIS "DOUBLEMURING" -> "Double Muring").
# IPEMIS uses the 6 older city thana units (Kotwali, Panchlaish, Double Mooring, Chandgaon, Pahartali, Bandar);
# BANBEIS names the port thana "Chittagong Port" (kept as given).
# Karnaphuli is an upazila (formerly a CMP thana) and is treated as one.
_CTG_METRO = {
    "akbarshah": "Akbar Shah", "bakalia": "Bakalia", "bandar": "Bandar", "bayazidbostami": "Bayazid Bostami",
    "bayejidbostami": "Bayejid Bostami", "chandgaon": "Chandgaon", "chittagongport": "Chittagong Port", "chawkbazar": "Chawkbazar", "chakbazar": "Chak Bazar",
    "doublemooring": "Double Mooring", "doublemuring": "Double Muring", "epz": "EPZ", "halishahar": "Halishahar",
    "khulshi": "Khulshi", "kotwali": "Kotwali", "pahartali": "Pahartali", "panchlaish": "Panchlaish",
    "pachlaish": "Pachlaish", "patenga": "Patenga", "sadarghat": "Sadarghat",
}
_CTG_METRO_THANAS = set(_CTG_METRO.values())
_CTG_UPAZILA_ALIASES = dict(_CTG_METRO, **{
    # Bandarban
    "alikadam": "Alikadam", "bandarbansadar": "Bandarban Sadar", "lama": "Lama", "naikhongchhari": "Naikhongchhari",
    "naikhongchari": "Naikhongchhari", "naikhangchhari": "Naikhongchhari", "naikkhongchhari": "Naikhongchhari",
    "rowangchhari": "Rowangchhari", "rowangchari": "Rowangchhari", "roangchhari": "Rowangchhari",
    "ruma": "Ruma", "thanchi": "Thanchi",
    # Brahmanbaria
    "akhaura": "Akhaura", "ashuganj": "Ashuganj", "ashugonj": "Ashuganj", "bancharampur": "Bancharampur",
    "banchharampur": "Bancharampur", "bijoynagar": "Bijoynagar", "brahmanbariasadar": "Brahmanbaria Sadar",
    "brahmonbariasadar": "Brahmanbaria Sadar", "kasba": "Kasba", "kashba": "Kasba", "nabinagar": "Nabinagar",
    "nasirnagar": "Nasirnagar", "sarail": "Sarail",
    # Chandpur (IPEMIS "MATLAB" next to "MATLAB UTTAR" is Matlab Dakshin; district-qualified key)
    "chandpursadar": "Chandpur Sadar", "faridganj": "Faridganj", "faridgonj": "Faridganj", "haimchar": "Haimchar",
    "hajiganj": "Hajiganj", "hajigonj": "Hajiganj", "kachua": "Kachua", "matlabdakshin": "Matlab Dakshin",
    "matlabdakkhin": "Matlab Dakshin", "matlabsouth": "Matlab Dakshin", "chandpur/matlab": "Matlab Dakshin",
    "matlabuttar": "Matlab Uttar", "matlabnorth": "Matlab Uttar", "shahrasti": "Shahrasti",
    # Chattogram
    "anwara": "Anwara", "anowara": "Anwara", "banshkhali": "Banshkhali", "bashkhali": "Banshkhali",
    "banskhali": "Banshkhali", "boalkhali": "Boalkhali", "chandanaish": "Chandanaish", "fatikchhari": "Fatikchhari",
    "fatikchari": "Fatikchhari", "hathazari": "Hathazari", "karnaphuli": "Karnaphuli", "karnafuli": "Karnaphuli",
    "lohagara": "Lohagara", "lohagora": "Lohagara", "mirsharai": "Mirsharai", "mirsarai": "Mirsharai",
    "mireswarai": "Mirsharai", "mirerswarai": "Mirsharai", "patiya": "Patiya", "rangunia": "Rangunia",
    "raozan": "Raozan", "rowzan": "Raozan", "sandwip": "Sandwip", "satkania": "Satkania", "sitakunda": "Sitakunda",
    "sitakundu": "Sitakunda",
    # Cox's Bazar (IPEMIS unit "COX'S BAZAR" is the Sadar upazila; "EIDGAH" is Eidgaon)
    "chakaria": "Chakaria", "chakoria": "Chakaria", "chokoria": "Chakaria", "coxsbazarsadar": "Cox's Bazar Sadar",
    "coxsbazar/coxsbazar": "Cox's Bazar Sadar", "eidgaon": "Eidgaon", "eidgah": "Eidgaon", "kutubdia": "Kutubdia",
    "maheshkhali": "Maheshkhali", "moheshkhali": "Maheshkhali", "pekua": "Pekua", "ramu": "Ramu", "teknaf": "Teknaf",
    "ukhia": "Ukhia", "ukhiya": "Ukhia",
    # Cumilla (IPEMIS "COMILLA SADAR" next to "SADAR DAKHIN" and "LALMAI" is Adarsha Sadar; district-qualified key)
    "barura": "Barura", "brahmanpara": "Brahmanpara", "burichang": "Burichang", "burichong": "Burichang",
    "chandina": "Chandina", "chauddagram": "Chauddagram", "chowddagram": "Chauddagram", "chouddagram": "Chauddagram",
    "cumillaadarshasadar": "Cumilla Adarsha Sadar", "comillaadarshasadar": "Cumilla Adarsha Sadar",
    "adarshasadar": "Cumilla Adarsha Sadar", "cumilla/comillasadar": "Cumilla Adarsha Sadar",
    "cumilla/cumillasadar": "Cumilla Adarsha Sadar", "cumillasadardakshin": "Cumilla Sadar Dakshin",
    "comillasadardakshin": "Cumilla Sadar Dakshin", "sadardakshin": "Cumilla Sadar Dakshin",
    "sadardakhin": "Cumilla Sadar Dakshin", "sadardakkhin": "Cumilla Sadar Dakshin", "sadarsouth": "Cumilla Sadar Dakshin",
    "daudkandi": "Daudkandi", "debidwar": "Debidwar", "debidhar": "Debidwar", "homna": "Homna", "laksam": "Laksam",
    "laksham": "Laksam", "lalmai": "Lalmai", "lalmi": "Lalmai", "meghna": "Meghna", "monoharganj": "Monoharganj",
    "manoharganj": "Monoharganj", "manohargong": "Monoharganj", "manohargonj": "Monoharganj",
    "monohargonj": "Monoharganj", "muradnagar": "Muradnagar", "nangalkot": "Nangalkot", "titas": "Titas",
    # Feni
    "chhagalnaiya": "Chhagalnaiya", "chagalnaiya": "Chhagalnaiya", "daganbhuiyan": "Daganbhuiyan",
    "dagonbhuiya": "Daganbhuiyan", "daganbhuiya": "Daganbhuiyan", "fenisadar": "Feni Sadar", "fulgazi": "Fulgazi",
    "phulgazi": "Fulgazi", "parshuram": "Parshuram", "parashuram": "Parshuram", "sonagazi": "Sonagazi",
    # Khagrachhari
    "dighinala": "Dighinala", "guimara": "Guimara", "khagrachharisadar": "Khagrachhari Sadar",
    "khagracharisadar": "Khagrachhari Sadar", "lakshmichhari": "Lakshmichhari", "lakshmichari": "Lakshmichhari",
    "laxmichhari": "Lakshmichhari", "luxmichhari": "Lakshmichhari", "mahalchhari": "Mahalchhari",
    "mahalchari": "Mahalchhari", "manikchhari": "Manikchhari", "manikchari": "Manikchhari", "matiranga": "Matiranga",
    "panchhari": "Panchhari", "panchari": "Panchhari", "ramgarh": "Ramgarh",
    # Lakshmipur (Chandraganj is a thana that IPEMIS lists as its own unit)
    "kamalnagar": "Kamalnagar", "lakshmipursadar": "Lakshmipur Sadar", "laxmipursadar": "Lakshmipur Sadar",
    "luxmipursadar": "Lakshmipur Sadar", "raipur": "Raipur", "raypur": "Raipur", "roypur": "Raipur", "ramganj": "Ramganj",
    "ramgonj": "Ramganj", "ramgati": "Ramgati", "chandraganj": "Chandraganj",
    # Noakhali
    "begumganj": "Begumganj", "chatkhil": "Chatkhil", "companiganj": "Companiganj", "companigonj": "Companiganj",
    "hatiya": "Hatiya", "hatia": "Hatiya", "kabirhat": "Kabirhat", "noakhalisadar": "Noakhali Sadar",
    "senbagh": "Senbagh", "senbag": "Senbagh", "sonaimuri": "Sonaimuri", "sonaimori": "Sonaimuri",
    "subarnachar": "Subarnachar",
    # Rangamati
    "baghaichhari": "Baghaichhari", "baghaichari": "Baghaichhari", "barkal": "Barkal", "belaichhari": "Belaichhari",
    "belaichari": "Belaichhari", "bilaichari": "Belaichhari", "bilaichhari": "Belaichhari", "jurachhari": "Jurachhari",
    "juraichari": "Jurachhari", "juraichhari": "Jurachhari", "kaptai": "Kaptai", "kawkhali": "Kawkhali",
    "kowkhali": "Kawkhali", "kaukhali": "Kawkhali", "langadu": "Langadu", "naniarchar": "Naniarchar",
    "rajasthali": "Rajasthali", "rangamatisadar": "Rangamati Sadar",
    # BANBEIS thana names cut off after 19 characters ("Belai Chhari  Upazi") or with a union in brackets
    "belaichhariupazi": "Belaichhari", "juraichhariupazil": "Jurachhari", "rangamatisadarup": "Rangamati Sadar",
    "kawkhalibetbunia": "Kawkhali",
})
_CTG_OTHER_THANAS = {"Chandraganj"}
# Khulna Division (keys are _key() of the spellings seen in the BANBEIS / IPEMIS / HRIS lists)
_KHL_DISTRICTS = ["Khulna", "Bagerhat", "Chuadanga", "Jashore", "Jhenaidah", "Kushtia", "Magura", "Meherpur", "Narail",
                  "Satkhira"]
_KHL_DISTRICT_ALIASES = {
    "khulna": "Khulna", "bagerhat": "Bagerhat", "bagherhat": "Bagerhat", "chuadanga": "Chuadanga", "jashore": "Jashore",
    "jessore": "Jashore", "jhenaidah": "Jhenaidah", "jhenaidaha": "Jhenaidah", "kushtia": "Kushtia", "magura": "Magura",
    "meherpur": "Meherpur", "narail": "Narail", "norail": "Narail", "satkhira": "Satkhira",
}
# Khulna Metropolitan Police thanas inside Khulna city, kept as the source names them (not upazilas). BANBEIS and HRIS
# use the 5 older city thanas (Khulna Sadar, Sonadanga, Khalishpur, Daulatpur, Khan Jahan Ali); IPEMIS has a single
# city unit KHULNA SADAR. Daulatpur is also an upazila of Kushtia: a thana counts as metropolitan only in Khulna
# District (METRO_DISTRICT).
_KHL_METRO = {
    "khulnasadar": "Khulna Sadar", "sonadanga": "Sonadanga", "khalishpur": "Khalishpur", "daulatpur": "Daulatpur",
    "khanjahanali": "Khan Jahan Ali", "harintana": "Harintana", "labanchara": "Labanchara", "aranghata": "Aranghata",
}
_KHL_METRO_THANAS = set(_KHL_METRO.values())
_KHL_UPAZILA_ALIASES = dict(_KHL_METRO, **{
    # Bagerhat
    "bagerhatsadar": "Bagerhat Sadar", "bagherhatsadar": "Bagerhat Sadar", "chitalmari": "Chitalmari",
    "fakirhat": "Fakirhat", "kachua": "Kachua", "mollahat": "Mollahat", "mollarhat": "Mollahat", "mongla": "Mongla",
    "morrelganj": "Morrelganj", "morelganj": "Morrelganj", "morolgonj": "Morrelganj", "rampal": "Rampal",
    "sarankhola": "Sarankhola",
    # Chuadanga
    "alamdanga": "Alamdanga", "chuadangasadar": "Chuadanga Sadar", "damurhuda": "Damurhuda", "jibannagar": "Jibannagar",
    # Jashore (BANBEIS lists Jashore town's Kotwali thana instead of Jashore Sadar; kept as a thana, see OTHER_THANAS)
    "abhaynagar": "Abhaynagar", "avoynagar": "Abhaynagar", "bagherpara": "Bagherpara", "bagarpara": "Bagherpara",
    "chaugachha": "Chaugachha", "chougachha": "Chaugachha", "chaugacha": "Chaugachha", "jashoresadar": "Jashore Sadar",
    "jessoresadar": "Jashore Sadar", "jhikargachha": "Jhikargachha", "jhikargacha": "Jhikargachha",
    "keshabpur": "Keshabpur", "manirampur": "Manirampur", "monirampur": "Manirampur", "sharsha": "Sharsha",
    "jashore/kotwali": "Kotwali",
    # Jhenaidah
    "harinakunda": "Harinakunda", "harinakundu": "Harinakunda", "horinakunda": "Harinakunda",
    "jhenaidahsadar": "Jhenaidah Sadar", "kaliganj": "Kaliganj", "kaligonj": "Kaliganj", "kotchandpur": "Kotchandpur",
    "cotchandpur": "Kotchandpur", "maheshpur": "Maheshpur", "moheshpur": "Maheshpur", "shailkupa": "Shailkupa",
    "soilkupa": "Shailkupa",
    # Khulna
    "batiaghata": "Batiaghata", "botiaghata": "Batiaghata", "dacope": "Dacope", "dakope": "Dacope", "dakop": "Dacope",
    "dighalia": "Dighalia", "dighulia": "Dighalia", "digholia": "Dighalia", "dumuria": "Dumuria", "koyra": "Koyra",
    "kayra": "Koyra", "paikgachha": "Paikgachha", "paikgacha": "Paikgachha", "paikgasa": "Paikgachha",
    "phultala": "Phultala", "fultala": "Phultala", "fultola": "Phultala", "rupsa": "Rupsa", "rupsha": "Rupsa",
    "terokhada": "Terokhada", "terakhada": "Terokhada",
    # Kushtia ("daulatpur" above: same spelling as the Khulna city thana)
    "bheramara": "Bheramara", "khoksa": "Khoksa", "khoksha": "Khoksa", "kumarkhali": "Kumarkhali",
    "kushtiasadar": "Kushtia Sadar", "mirpur": "Mirpur",
    # Magura
    "magurasadar": "Magura Sadar", "mohammadpur": "Mohammadpur", "shalikha": "Shalikha", "sreepur": "Sreepur",
    "shreepur": "Sreepur",
    # Meherpur
    "gangni": "Gangni", "meherpursadar": "Meherpur Sadar", "mujibnagar": "Mujibnagar",
    # Narail
    "kalia": "Kalia", "lohagara": "Lohagara", "narailsadar": "Narail Sadar",
    # Satkhira
    "assasuni": "Assasuni", "ashashuni": "Assasuni", "asasuni": "Assasuni", "debhata": "Debhata", "kalaroa": "Kalaroa",
    "kolaroa": "Kalaroa", "satkhirasadar": "Satkhira Sadar", "shyamnagar": "Shyamnagar", "shamnagar": "Shyamnagar",
    "tala": "Tala",
})
# BANBEIS lists Jashore's Kotwali (Jashore town police thana) as its own unit and has no Jashore Sadar unit
_KHL_OTHER_THANAS = {"Kotwali"}
# Barishal Division (keys are _key() of the spellings seen in the BANBEIS / IPEMIS / HRIS lists)
_BAR_DISTRICTS = ["Barishal", "Barguna", "Bhola", "Jhalokathi", "Patuakhali", "Pirojpur"]
_BAR_DISTRICT_ALIASES = {
    "barishal": "Barishal", "barisal": "Barishal", "barguna": "Barguna", "bhola": "Bhola", "jhalokathi": "Jhalokathi",
    "jhalokati": "Jhalokathi", "jhalakathi": "Jhalokathi", "patuakhali": "Patuakhali", "pirojpur": "Pirojpur",
}
# Barishal Metropolitan Police thanas, kept as the source names them (not upazilas); a thana counts as metropolitan
# only in Barishal District (METRO_DISTRICT). None occur in the 2026-11 lists: BANBEIS ("Barisal Sadar (Kotwali)"),
# IPEMIS (BARISAL SADAR) and HRIS (Barishal Sadar) list Barishal city under the Sadar upazila.
_BAR_METRO = {"kotwali": "Kotwali", "airport": "Airport", "kawnia": "Kawnia", "bandar": "Bandar"}
_BAR_METRO_THANAS = set(_BAR_METRO.values())
_BAR_UPAZILA_ALIASES = dict(_BAR_METRO, **{
    # Barishal
    "agailjhara": "Agailjhara", "babuganj": "Babuganj", "babugonj": "Babuganj", "bakerganj": "Bakerganj",
    "bakhergonj": "Bakerganj", "banaripara": "Banaripara", "banoripara": "Banaripara", "barishalsadar": "Barishal Sadar",
    "barisalsadar": "Barishal Sadar", "barisalsadarkotwali": "Barishal Sadar", "gaurnadi": "Gaurnadi",
    "gournadi": "Gaurnadi", "hizla": "Hizla", "hijla": "Hizla", "mehendiganj": "Mehendiganj", "mehendigonj": "Mehendiganj",
    "muladi": "Muladi", "wazirpur": "Wazirpur", "uzirpur": "Wazirpur", "ujirpur": "Wazirpur",
    # Barguna
    "amtali": "Amtali", "bamna": "Bamna", "bargunasadar": "Barguna Sadar", "betagi": "Betagi",
    "patharghata": "Patharghata", "taltali": "Taltali",
    # Bhola
    "bholasadar": "Bhola Sadar", "borhanuddin": "Borhanuddin", "burhanuddin": "Borhanuddin", "charfasson": "Char Fasson",
    "charfashion": "Char Fasson", "charfession": "Char Fasson", "daulatkhan": "Daulatkhan", "lalmohan": "Lalmohan",
    "manpura": "Manpura", "monpura": "Manpura", "tazumuddin": "Tazumuddin", "tozumuddin": "Tazumuddin",
    # Jhalokathi
    "jhalokathisadar": "Jhalokathi Sadar", "jhalokatisadar": "Jhalokathi Sadar", "kathalia": "Kathalia",
    "kanthalia": "Kathalia", "nalchity": "Nalchity", "nolchhiti": "Nalchity", "rajapur": "Rajapur",
    # Patuakhali
    "bauphal": "Bauphal", "dashmina": "Dashmina", "dumki": "Dumki", "galachipa": "Galachipa", "golachipa": "Galachipa",
    "kalapara": "Kalapara", "kolapara": "Kalapara", "mirzaganj": "Mirzaganj", "mirzagonj": "Mirzaganj",
    "patuakhalisadar": "Patuakhali Sadar", "rangabali": "Rangabali",
    # Pirojpur (IPEMIS truncates "SHORUPKATHI(NESARABA[D])" and still uses Indurkani's former name ZIANAGAR)
    "bhandaria": "Bhandaria", "indurkani": "Indurkani", "zianagar": "Indurkani", "kawkhali": "Kawkhali",
    "kaukhali": "Kawkhali", "mathbaria": "Mathbaria", "mothbaria": "Mathbaria", "nazirpur": "Nazirpur",
    "nesarabad": "Nesarabad", "nesarabadswarupkati": "Nesarabad", "shorupkathinesaraba": "Nesarabad",
    "pirojpursadar": "Pirojpur Sadar",
})
# source units that were mapped by interpretation (not only by spelling): note on each row (key: _key() of the source)
_BAR_UPAZILA_NOTES = {
    "zianagar": "source unit ZIANAGAR mapped to Indurkani (the upazila's current name, Zianagar its former name)",
    "barisalsadarkotwali": ("source unit 'Barisal Sadar (Kotwali)' (Sadar upazila incl. Barishal city / Kotwali thana) "
                            "mapped to Barishal Sadar"),
}
# Sylhet Division (keys are _key() of the spellings seen in the BANBEIS / IPEMIS / HRIS lists)
_SYL_DISTRICTS = ["Sylhet", "Habiganj", "Moulvibazar", "Sunamganj"]
_SYL_DISTRICT_ALIASES = {
    "sylhet": "Sylhet", "habiganj": "Habiganj", "habigonj": "Habiganj", "hobigonj": "Habiganj", "hobiganj": "Habiganj",
    "moulvibazar": "Moulvibazar", "maulvibazar": "Moulvibazar", "sunamganj": "Sunamganj", "sunamgonj": "Sunamganj",
}
# Sylhet Metropolitan Police thanas, kept as the source names them (not upazilas); a thana counts as metropolitan only
# in Sylhet District (METRO_DISTRICT). Dakshin Surma is both an SMP thana and an upazila of Sylhet District: a source
# unit of that name is taken as the upazila. None occur in the 2026-11 lists: BANBEIS and IPEMIS list Sylhet city under
# Sylhet Sadar (and Dakshin Surma).
_SYL_METRO = {"kotwali": "Kotwali", "jalalabad": "Jalalabad", "airport": "Airport", "shahparan": "Shahparan",
              "shahporan": "Shahparan", "moglabazar": "Moglabazar"}
_SYL_METRO_THANAS = set(_SYL_METRO.values())
_SYL_UPAZILA_ALIASES = dict(_SYL_METRO, **{
    # Sylhet
    "sylhetsadar": "Sylhet Sadar", "balaganj": "Balaganj", "balagonj": "Balaganj", "beanibazar": "Beanibazar",
    "bianibazar": "Beanibazar", "bishwanath": "Bishwanath", "biswanath": "Bishwanath", "companiganj": "Companiganj",
    "companigonj": "Companiganj", "dakshinsurma": "Dakshin Surma", "dakhinsurma": "Dakshin Surma",
    "dakkhinsurma": "Dakshin Surma", "fenchuganj": "Fenchuganj", "fenchugonj": "Fenchuganj", "golapganj": "Golapganj",
    "golapgonj": "Golapganj", "gowainghat": "Gowainghat", "goainghat": "Gowainghat", "jaintiapur": "Jaintiapur",
    "jaintapur": "Jaintiapur", "kanaighat": "Kanaighat", "osmaninagar": "Osmaninagar", "zakiganj": "Zakiganj",
    "zakigonj": "Zakiganj", "jakigonj": "Zakiganj",
    # Moulvibazar
    "barlekha": "Barlekha", "baralekha": "Barlekha", "baralakha": "Barlekha", "juri": "Juri", "kamalganj": "Kamalganj",
    "kamalgonj": "Kamalganj", "kamolganj": "Kamalganj", "kulaura": "Kulaura", "moulvibazarsadar": "Moulvibazar Sadar",
    "maulvibazarsadar": "Moulvibazar Sadar", "rajnagar": "Rajnagar", "sreemangal": "Sreemangal",
    "srimangal": "Sreemangal",
    # Habiganj
    "ajmiriganj": "Ajmiriganj", "ajmirigonj": "Ajmiriganj", "azmirigonj": "Ajmiriganj", "bahubal": "Bahubal",
    "baniachong": "Baniachong", "baniachang": "Baniachong", "banichang": "Baniachong", "chunarughat": "Chunarughat",
    "habiganjsadar": "Habiganj Sadar", "habigonjsadar": "Habiganj Sadar", "hobigonjsadar": "Habiganj Sadar",
    "lakhai": "Lakhai", "madhabpur": "Madhabpur", "nabiganj": "Nabiganj", "nabigonj": "Nabiganj",
    "shayestaganj": "Shayestaganj", "shaesthagonj": "Shayestaganj", "shaistaganj": "Shayestaganj",
    # Sunamganj (BANBEIS still uses Shantiganj's former name Dakshin Sunamganj)
    "bishwambarpur": "Bishwambarpur", "biswambarpur": "Bishwambarpur", "chhatak": "Chhatak", "chatak": "Chhatak",
    "derai": "Derai", "dharmapasha": "Dharmapasha", "dharampasha": "Dharmapasha", "dowarabazar": "Dowarabazar",
    "jagannathpur": "Jagannathpur", "jamalganj": "Jamalganj", "jamalgonj": "Jamalganj", "madhyanagar": "Madhyanagar",
    "shalla": "Shalla", "sulla": "Shalla", "shantiganj": "Shantiganj", "shantigonj": "Shantiganj",
    "dakshinsunamganj": "Shantiganj", "sunamganjsadar": "Sunamganj Sadar", "sunamgonjsadar": "Sunamganj Sadar",
    "tahirpur": "Tahirpur",
})
_SYL_UPAZILA_NOTES = {
    "dakshinsunamganj": ("source unit 'Dakshin Sunamganj' mapped to Shantiganj (the upazila's current name, Dakshin "
                         "Sunamganj its former name)"),
}
# Mymensingh Division (keys are _key() of the spellings seen in the BANBEIS / IPEMIS / HRIS lists; values are the seed's
# English names, e.g. Nokla, Sreebordi, Bokshiganj, Dewangonj, Mohongonj)
_MYM_DISTRICTS = ["Mymensingh", "Jamalpur", "Netrokona", "Sherpur"]
_MYM_DISTRICT_ALIASES = {
    "mymensingh": "Mymensingh", "jamalpur": "Jamalpur", "netrokona": "Netrokona", "netrakona": "Netrokona",
    "sherpur": "Sherpur",
}
# No metropolitan thanas: the 2026-11 lists (BANBEIS, IPEMIS, HRIS) have no Mymensingh Metropolitan Police thana units
# and put Mymensingh city under the upazila Mymensingh Sadar, so _MYM_METRO_THANAS is empty and METRO_DISTRICT unset.
_MYM_METRO_THANAS = set()
_MYM_UPAZILA_ALIASES = {
    # Mymensingh
    "mymensinghsadar": "Mymensingh Sadar", "mymensingsadar": "Mymensingh Sadar", "bhaluka": "Bhaluka",
    "dhobaura": "Dhobaura", "dhubaura": "Dhobaura", "fulbaria": "Fulbaria", "phulbaria": "Fulbaria",
    "gafargaon": "Gafargaon", "gaffargaon": "Gafargaon", "gofargaon": "Gafargaon", "gouripur": "Gouripur",
    "gauripur": "Gouripur", "haluaghat": "Haluaghat", "iswarganj": "Iswarganj", "ishwarganj": "Iswarganj",
    "iswargonj": "Iswarganj", "ishwargonj": "Iswarganj", "muktagacha": "Muktagacha", "muktagachha": "Muktagacha",
    "nandail": "Nandail", "phulpur": "Phulpur", "fulpur": "Phulpur", "tarakanda": "Tarakanda", "trishal": "Trishal",
    "trisal": "Trishal",
    # Jamalpur
    "jamalpursadar": "Jamalpur Sadar", "bokshiganj": "Bokshiganj", "bakshiganj": "Bokshiganj", "bakshigonj": "Bokshiganj",
    "bokshigonj": "Bokshiganj", "dewangonj": "Dewangonj", "dewanganj": "Dewangonj", "islampur": "Islampur",
    "madarganj": "Madarganj", "madargonj": "Madarganj", "melandah": "Melandah", "melandaha": "Melandah",
    "sarishabari": "Sarishabari", "sharishabari": "Sarishabari",
    # Netrokona
    "atpara": "Atpara", "barhatta": "Barhatta", "durgapur": "Durgapur", "kalmakanda": "Kalmakanda", "kendua": "Kendua",
    "kandua": "Kendua", "khaliajuri": "Khaliajuri", "khaliajhuri": "Khaliajuri", "madan": "Madan",
    "mohongonj": "Mohongonj", "mohanganj": "Mohongonj", "mohangonj": "Mohongonj", "netrokonasadar": "Netrokona Sadar",
    "netrakonasadar": "Netrokona Sadar", "purbadhala": "Purbadhala",
    # Sherpur
    "sherpursadar": "Sherpur Sadar", "jhenaigati": "Jhenaigati", "jhinaigati": "Jhenaigati", "nalitabari": "Nalitabari",
    "nokla": "Nokla", "nakla": "Nokla", "sreebordi": "Sreebordi", "sreebardi": "Sreebordi", "sribordi": "Sreebordi",
}
_NORM = {"rajshahi": (_RAJ_DISTRICTS, _RAJ_DISTRICT_ALIASES, _RAJ_METRO_THANAS, _RAJ_UPAZILA_ALIASES),
         "rangpur": (_RANG_DISTRICTS, _RANG_DISTRICT_ALIASES, _RANG_METRO_THANAS, _RANG_UPAZILA_ALIASES),
         "dhaka": (_DHK_DISTRICTS, _DHK_DISTRICT_ALIASES, _DHK_METRO_THANAS, _DHK_UPAZILA_ALIASES),
         "chattogram": (_CTG_DISTRICTS, _CTG_DISTRICT_ALIASES, _CTG_METRO_THANAS, _CTG_UPAZILA_ALIASES),
         "khulna": (_KHL_DISTRICTS, _KHL_DISTRICT_ALIASES, _KHL_METRO_THANAS, _KHL_UPAZILA_ALIASES),
         "barishal": (_BAR_DISTRICTS, _BAR_DISTRICT_ALIASES, _BAR_METRO_THANAS, _BAR_UPAZILA_ALIASES),
         "sylhet": (_SYL_DISTRICTS, _SYL_DISTRICT_ALIASES, _SYL_METRO_THANAS, _SYL_UPAZILA_ALIASES),
         "mymensingh": (_MYM_DISTRICTS, _MYM_DISTRICT_ALIASES, _MYM_METRO_THANAS, _MYM_UPAZILA_ALIASES)}
DIVISION_DISTRICTS, _DISTRICT_ALIASES, METRO_THANAS, _UPAZILA_ALIASES = _NORM.get(DIV, ([], {}, set(), {}))
UPAZILA_NOTES = {"barishal": _BAR_UPAZILA_NOTES, "sylhet": _SYL_UPAZILA_NOTES}.get(DIV, {})
OTHER_THANAS = {"rangpur": _RANG_OTHER_THANAS, "dhaka": _DHK_OTHER_THANAS,
                "chattogram": _CTG_OTHER_THANAS, "khulna": _KHL_OTHER_THANAS}.get(DIV, set())
# district of the metropolitan thanas where a thana name is also an upazila elsewhere in the division (else None)
METRO_DISTRICT = {"khulna": "Khulna", "barishal": "Barishal", "sylhet": "Sylhet"}.get(DIV)


def is_metro(upz, district):
    return upz in METRO_THANAS and (not METRO_DISTRICT or district == METRO_DISTRICT)


def _key(s):
    return _re.sub(r"[^a-z]", "", (s or "").lower().replace("upazila", ""))


def norm_district(s):
    return _DISTRICT_ALIASES.get(_key(s), "")


def upazila_note(s):
    """note for a source unit that was mapped by interpretation (empty for spelling-only mappings)"""
    return UPAZILA_NOTES.get(_key(s), "")


def norm_upazila(s, district=None):
    """district (optional) allows district-qualified aliases for names that differ by district."""
    if district:
        v = _UPAZILA_ALIASES.get(_key(district) + "/" + _key(s))
        if v:
            return v
    return _UPAZILA_ALIASES.get(_key(s), "")
# --- end normalisation -----------------------------------------------------------------------------------

# --- output helpers ---------------------------------------------------------------------------------------
import csv, json, hashlib, unicodedata, datetime

PLACE_COLS = ["source_key", "source_id", "name_bn", "name_en", "category_key", "lat", "lon", "address", "district_en",
              "upazila_en", "phone", "website", "email", "opening_hours", "operator", "ownership", "extra_json",
              "source_url", "notes"]
FACT_COLS = ["entity_level", "entity_name_en", "district_en", "upazila_en", "code", "fact", "value", "unit", "basis",
             "year", "source_key", "source_url", "notes"]
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(ARGS.out) if ARGS.out else (
    HERE if DIV == "rajshahi" else os.path.join(os.path.dirname(HERE), f"dpe_ipemis_primary_{CODE}_2026"))


def nfc(s):
    if s is None:
        return ""
    s = unicodedata.normalize("NFC", str(s)).replace("\xa0", " ")
    return _re.sub(r"\s+", " ", s).strip()


def cj(d):
    return json.dumps({k: v for k, v in d.items() if v not in (None, "", [], {})}, ensure_ascii=False, separators=(",", ":"))


def write_csv(name, cols, rows):
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: ("" if r.get(c) is None else r.get(c)) for c in cols})


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def update_manifest(files):
    p = os.path.join(OUT, "SOURCE.json")
    m = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else new_manifest()
    m["accessed"] = datetime.date.today().isoformat()
    m["files"] = {f: sha256(os.path.join(OUT, f)) for f in files if os.path.exists(os.path.join(OUT, f))}
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(m, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def new_manifest():
    """SOURCE.json for a division other than Rajshahi (the Rajshahi manifest is maintained by hand)."""
    return {
        "key": SOURCE_KEY,
        "name": f"DPE IPEMIS primary school directory — {DIVT} Division",
        "organization": "Directorate of Primary Education (DPE), Ministry of Primary and Mass Education",
        "source_type": "government_portal",
        "trust_level": 4,
        "urls": [SEARCH_PAGE, SITE + "/load-lite-school-list", API + "/api/school-stat-public", "https://dpe.gov.bd/"],
        "accessed": datetime.date.today().isoformat(),
        "publication_date": None,
        "license": None,
        "license_url": None,
        "attribution": "Source: Directorate of Primary Education, IPEMIS (ipemis.dpe.gov.bd)",
        "division": DIV,
        "kind": "dpe_ipemis",
        "notes": (f"Public 'প্রাথমিক বিদ্যালয় ডিরেক্টরি' (school search) of the Integrated Primary Education Management "
                  f"Information System, linked from dpe.gov.bd. Listing endpoint used by the public page (DataTables "
                  f"JSON), queried per district of {DIVT} Division (divisionId={DIVISION_ID}); same collector and rules "
                  "as DPE_IPEMIS_PRIMARY_RAJ_2026. Covers government primary, newly nationalised and experimental "
                  "schools only (no kindergartens, NGO or ebtedayee madrasas). No coordinates; head teachers' names and "
                  "mobiles on the detail pages are deliberately NOT collected. Live data (changes daily). No robots.txt "
                  "on ipemis.dpe.gov.bd / api.ipemis.dpe.gov.bd (404). Licence not stated."),
        "files": {},
    }
# --- end output helpers -----------------------------------------------------------------------------------

# --- DPE IPEMIS primary-school directory: one division -------------------------------------------------
import sys
from collections import Counter, defaultdict

SOURCE_KEY = f"DPE_IPEMIS_PRIMARY_{CODE.upper()}_2026"
SITE = "https://ipemis.dpe.gov.bd"
API = "https://api.ipemis.dpe.gov.bd"
LIST_URL = SITE + "/load-lite-school-list?draw=1&start={start}&length=500&divisionId=%d&districtId={did}" % DIVISION_ID
DETAIL_URL = SITE + "/school-details-view/{sid}"
SEARCH_PAGE = SITE + "/search-school"
RAW_REL = f"raw/ipemis_school_list_{DIV}_division.json"
METRO_NOTE = {
    "rajshahi": "IPEMIS unit BOALIA(SADAR) = Rajshahi City Corporation area (metropolitan thana), not an upazila",
    "dhaka": ("IPEMIS thana unit inside Dhaka city (metropolitan thana), not an upazila; IPEMIS has 12 city units, so "
              "one unit may cover more than the present DMP thana of that name"),
    "chattogram": ("IPEMIS thana unit inside Chattogram city (metropolitan thana), not an upazila; IPEMIS has 6 city "
                   "units, so one unit may cover more than the present CMP thana of that name"),
    "khulna": ("IPEMIS unit KHULNA SADAR is its only unit inside Khulna city (metropolitan thana), not an upazila; it "
               "may cover more than the present KMP thana of that name"),
}.get(DIV, f"metropolitan thana of {DIVT} City, not an upazila")
RAW = os.path.join(OUT, *RAW_REL.split("/"))


PARTIAL = os.path.join(OUT, ".partial")  # response cache of the current run (for --resume); removed on success


def getjson(url):
    cache = os.path.join(PARTIAL, hashlib.sha1(url.encode()).hexdigest() + ".json")
    if ARGS.resume and os.path.exists(cache):
        return json.load(open(cache, encoding="utf-8"))
    r = get(url, headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"})
    if r is None or r.status_code != 200:
        print("FAILED", url, None if r is None else r.status_code)
        return None
    try:
        j = r.json()
    except ValueError:
        print("not JSON", url)
        return None
    os.makedirs(PARTIAL, exist_ok=True)
    with open(cache, "w", encoding="utf-8") as f:
        json.dump(j, f, ensure_ascii=False)
    return j


def main():
    offline = ARGS.offline
    districts = getjson(f"{API}/api/districts/lite/division/{DIVISION_ID}") if not offline else None
    districts = (districts or {}).get("data") or []
    if not offline and not districts:  # API unreachable: keep the previous outputs (incl. live statistics) untouched
        sys.exit("IPEMIS district list unavailable; nothing written (re-run later, or use --offline)")
    schools, incomplete = [], []
    if not offline:
        for d in districts:
            start, total, got = 0, None, 0
            while total is None or start < total:
                j = getjson(LIST_URL.format(start=start, did=d["districtId"]))
                if not j:
                    break
                total = j.get("recordsTotal", 0)
                got += len(j.get("aaData") or [])
                schools += j.get("aaData") or []
                start += 500
            print(d["name"], total)
            if total is None or got < total:
                incomplete.append(d["name"])
        if incomplete:  # keep .partial so that --resume can complete the listing; nothing is written
            sys.exit(f"listing incomplete for {incomplete}; re-run with --resume")
    if schools:
        os.makedirs(os.path.dirname(RAW), exist_ok=True)
        with open(RAW, "w", encoding="utf-8") as f:
            json.dump(schools, f, ensure_ascii=False, separators=(",", ":"))
    elif os.path.exists(RAW):
        print("using cached raw", RAW)
        schools = json.load(open(RAW, encoding="utf-8"))

    rows, seen = [], set()
    for s in schools:
        if s["schoolId"] in seen:
            continue
        seen.add(s["schoolId"])
        dist = norm_district(s.get("districtName"))
        upz = norm_upazila(s.get("upazilaName"), s.get("districtName"))
        notes = []
        if not upz:
            notes.append(f"upazila '{s.get('upazilaName')}' not normalised")
            if DIV != "rajshahi" and nfc(s.get("upazilaName")):  # other divisions: keep the source spelling
                upz = nfc(s.get("upazilaName"))
        if not dist and DIV != "rajshahi" and nfc(s.get("districtName")):
            notes.append(f"district '{s.get('districtName')}' not normalised")
            dist = nfc(s.get("districtName"))
        if upazila_note(s.get("upazilaName")):
            notes.append(upazila_note(s.get("upazilaName")))
        if is_metro(upz, dist):
            notes.append(METRO_NOTE)
        if upz in OTHER_THANAS:
            notes.append(f"IPEMIS lists {s.get('upazilaName')} as its own upazila unit; {upz} is a thana, not an upazila "
                         "(parent upazila not given by the source)")
        union = nfc(s.get("geoUnionNameLocal") or s.get("geoUnionName"))
        rows.append({
            "source_key": SOURCE_KEY,
            "source_id": f"ipemis:{s['schoolId']}",
            "name_bn": nfc(s.get("schoolNameLocal")),
            "name_en": nfc(s.get("schoolName")),
            "category_key": "education.primary_school",
            "address": ", ".join(x for x in [union, nfc(s.get("upazilaNameLocal")), nfc(s.get("districtNameLocal"))] if x),
            "district_en": dist,
            "upazila_en": upz,
            "operator": "Directorate of Primary Education",
            "ownership": "government",
            "extra_json": cj({
                "school_code": s.get("schoolCode"), "ipemis_school_id": s.get("schoolId"),
                "school_type": s.get("schoolTypeName"), "school_type_bn": nfc(s.get("schoolTypeNameLocal")),
                "union_or_ward_bn": union, "cluster": nfc(s.get("geoClusterName")),
                "cluster_bn": nfc(s.get("geoClusterNameLocal")),
                "upazila_src": s.get("upazilaName"), "district_src": s.get("districtName"),
                "teachers": s.get("totalTeacher"), "students": s.get("totalStudent"),
                "admin_unit": "metropolitan_thana" if is_metro(upz, dist) else "thana" if upz in OTHER_THANAS else "upazila",
            }),
            "source_url": DETAIL_URL.format(sid=s["schoolId"]),
            "notes": "; ".join(notes),
        })
    rows.sort(key=lambda r: (r["district_en"] != DIVT, r["district_en"], r["upazila_en"], r["name_en"]))
    write_csv("places.csv", PLACE_COLS, rows)

    # facts: official IPEMIS public statistics per division / district / upazila + listed-record counts by type
    facts = []
    year = datetime.date.today().year
    stat_fields = [("totalSchool", "primary_schools", "schools"), ("govtSchool", "govt_primary_schools", "schools"),
                   ("experimentalSchool", "experimental_schools", "schools"),
                   ("totalTeacher", "primary_teachers", "persons"), ("totalStudent", "primary_students", "persons")]

    def add_stats(level, name, dist, upz, code, params):
        url = f"{API}/api/school-stat-public?{params}"
        j = getjson(url)
        if not j or not j.get("data"):
            return
        for k, fact, unit in stat_fields:
            if j["data"].get(k) is not None:
                facts.append({"entity_level": level, "entity_name_en": name, "district_en": dist, "upazila_en": upz,
                              "code": code, "fact": fact, "value": j["data"][k], "unit": unit,
                              "basis": "official_live_statistic", "year": year, "source_key": SOURCE_KEY,
                              "source_url": SEARCH_PAGE,
                              "notes": f"IPEMIS public school statistic API ({url}); live figure on access date; "
                                       "covers schools in IPEMIS (govt, newly nationalised, experimental)"})

    if offline and os.path.exists(os.path.join(OUT, "facts.csv")):  # keep previously fetched live statistics
        facts += [r for r in csv.DictReader(open(os.path.join(OUT, "facts.csv"), encoding="utf-8"))
                  if r["basis"] == "official_live_statistic"]
    if not offline:
        add_stats("division", DIVT, "", "", f"ipemis_division:{DIVISION_ID}", f"divisionId={DIVISION_ID}")
        for d in districts:
            dist = norm_district(d["name"])
            add_stats("district", dist, dist, "", f"ipemis_district:{d['districtId']}",
                      f"divisionId={DIVISION_ID}&districtId={d['districtId']}")
            ups = getjson(f"{API}/api/upazilas/lite/district/{d['districtId']}")
            for u in (ups or {}).get("data") or []:
                upz = norm_upazila(u["name"], d["name"])
                add_stats("thana" if is_metro(upz, dist) or upz in OTHER_THANAS else "upazila", upz or u["name"], dist, upz,
                          f"ipemis_upazila:{u['upazilaId']}",
                          f"divisionId={DIVISION_ID}&districtId={d['districtId']}&upazilaId={u['upazilaId']}")
    cnt = Counter((r["district_en"], r["upazila_en"], json.loads(r["extra_json"]).get("school_type")) for r in rows)
    for (dist, upz, typ), n in sorted(cnt.items()):
        facts.append({"entity_level": "thana" if is_metro(upz, dist) or upz in OTHER_THANAS else "upazila", "entity_name_en": upz,
                      "district_en": dist, "upazila_en": upz, "code": "",
                      "fact": "primary_schools_listed_" + _re.sub(r"[^a-z]+", "_", typ.lower()).strip("_"),
                      "value": n, "unit": "schools", "basis": "count_of_listed_records", "year": year,
                      "source_key": SOURCE_KEY, "source_url": SEARCH_PAGE,
                      "notes": f"count of IPEMIS directory rows with school type '{typ}'"})
    write_csv("facts.csv", FACT_COLS, facts)
    update_manifest(["places.csv", "facts.csv", RAW_REL])
    if os.path.isdir(PARTIAL):
        import shutil
        shutil.rmtree(PARTIAL)
    print("places", len(rows), "facts", len(facts))
    print(Counter(r["district_en"] for r in rows))


if __name__ == "__main__":
    main()
