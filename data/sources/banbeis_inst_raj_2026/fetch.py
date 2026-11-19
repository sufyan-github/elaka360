#!/usr/bin/env python3
"""Fetch BANBEIS institution lists (EIIN registry, e-survey 2024) and keep one division (default Rajshahi)
(stdlib + requests only).

For Rajshahi also cross-checks EIINs against the Rajshahi Education Board public institute list (flag only).
Usage: python3 fetch.py [--offline]   (--offline rebuilds the CSVs from raw/ without network).
       python3 fetch.py --division rangpur [--out DIR] [--offline]
           another division (see ../DIVISIONS.md); default output is the sibling folder banbeis_inst_<code>_2026,
           the Rajshahi files are never touched.
       --resume  lists that an interrupted run already saved to raw/ (marked in <out>/.partial/) are not downloaded
                 again; the marker folder is deleted when the run completes."""
import argparse as _argparse
# division -> code from DIVISIONS.md
DIVISION_CODES = {"rajshahi": "raj", "rangpur": "rang", "dhaka": "dhk", "chattogram": "ctg", "khulna": "khl",
                  "barishal": "bar", "sylhet": "syl", "mymensingh": "mym"}
_ap = _argparse.ArgumentParser()
_ap.add_argument("--division", default="rajshahi", choices=sorted(DIVISION_CODES))
_ap.add_argument("--out", default=None, help="output folder (default: this folder for Rajshahi, else the sibling folder)")
_ap.add_argument("--offline", action="store_true", help="rebuild from raw/ in the output folder without network")
_ap.add_argument("--resume", action="store_true", help="skip lists already saved by an interrupted run (<out>/.partial/)")
ARGS = _ap.parse_args()
DIV = ARGS.division
DIVT = DIV.title()
CODE = DIVISION_CODES[DIV]
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
    HERE if DIV == "rajshahi" else os.path.join(os.path.dirname(HERE), f"banbeis_inst_{CODE}_2026"))


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
        "name": f"BANBEIS institution lists (EIIN registry, e-survey 2024) — {DIVT} Division",
        "organization": "Bangladesh Bureau of Educational Information and Statistics (BANBEIS), Ministry of Education",
        "source_type": "government_portal",
        "trust_level": 4,
        "urls": [BANBEIS + u for u in FILE_PAGES.values()] + ["https://institute-search.ieims.banbeis.gov.bd/"],
        "accessed": datetime.date.today().isoformat(),
        "publication_date": None,
        "license": None,
        "license_url": None,
        "attribution": "Source: BANBEIS (banbeis.gov.bd), institution lists based on e-survey 2024",
        "division": DIV,
        "kind": "banbeis",
        "notes": (f"National XLSX lists (school; college & school-and-college; madrasa; government technical; independent "
                  f"technical; public/private university; professional) published on banbeis.gov.bd file pages "
                  f"(object-store links), filtered to DIVISION_NAME={DIVT} and deduplicated by EIIN; same collector and "
                  "rules as BANBEIS_INST_RAJ_2026. Fields: division, district, thana, institute type, education level, "
                  "EIIN, name (English only), post office, e-mail, management, MPO status, for-whom, geographical "
                  "position, area status. No coordinates, no phone numbers, no Bangla names. source_url per row is the "
                  "BANBEIS Institute Search detail page for that EIIN (its /api/ is disallowed by robots.txt, not "
                  "crawled). No education-board cross-check for this division. Licence not stated on the portal."),
        "files": {},
    }
# --- end output helpers -----------------------------------------------------------------------------------

# --- BANBEIS institution lists (e-survey 2024): one division ----------------------------------------------
import sys, io, zipfile, xml.etree.ElementTree as ET
from collections import Counter

SOURCE_KEY = f"BANBEIS_INST_{CODE.upper()}_2026"
# DIVISION_NAME values that the lists use for the division (old spelling accepted where it may occur)
SRC_DIVISION_NAMES = {"chattogram": ("Chattogram", "Chittagong")}.get(DIV, (DIVT,))
BANBEIS = "https://banbeis.gov.bd"
DETAIL = "https://institute-search.ieims.banbeis.gov.bd/details/{eiin}"
BOARD_LIST = "https://rajshahiboard.gov.bd/sonali/ins.php"  # JSON behind https://rajshahiboard.gov.bd/index.php/institute/
# BANBEIS file pages (each links one or more XLSX lists on the government object store)
FILE_PAGES = {
    "school": "/pages/files/69199760933eb65569ddc637",          # স্কুল-২০২৪
    "college": "/pages/files/6919975e933eb65569ddc579",         # কলেজ, স্কুল এন্ড কলেজ-২০২৪
    "madrasa": "/pages/files/69199763933eb65569ddc6e8",         # মাদ্রাসা-২০২৪
    "govt_technical": "/pages/files/69568a64a31054345f1038ee",  # সরকারি কারিগরি-২০২৪
    "technical": "/pages/files/69199762933eb65569ddc6d1",       # স্বতন্ত্র কারিগরি
    "university": "/pages/files/6919975f933eb65569ddc5ce",      # বিশ্ববিদ্যালয় (public + private)
    "professional": "/pages/files/69199761933eb65569ddc66f",    # প্রফেশনাল
}
FALLBACK_XLSX = {  # links seen on 2026-11-12, used if a file page cannot be parsed
    "school": ["5db6947e05cf4318a5bd45000f1bbcc6.xlsx"], "college": ["cb248464f0ed4f99b1e9c83d135a6e92.xlsx"],
    "madrasa": ["ecf2c7e9068c42aaa415021851be0831.xlsx"], "govt_technical": ["edff91ac6e7142c2892e285c3c59c679.xlsx"],
    "technical": ["b4abd9d741634fa8a72169154884bb3b.xlsx"],
    "university": ["e02aa2fabf4d4b70a85afa2fa3f43853.xlsx", "e9504e1e1c83496197730c5a2159901e.xlsx"],
    "professional": ["ae198d3ccdcd45b6879fdf7a2fd821b4.xlsx"],
}
OBJ = "https://objectstorage.ap-dcc-gazipur-1.oraclecloud15.com/n/axvjbnqprylg/b/V2Ministry/o/office-banbeis/2024/12/"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def read_xlsx_bytes(data):
    z = zipfile.ZipFile(io.BytesIO(data))
    ss = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
            ss.append("".join(t.text or "" for t in si.iter("{%s}t" % NS["m"])))
    sheet = sorted(n for n in z.namelist() if n.startswith("xl/worksheets/sheet"))[0]
    rows = []
    for r in ET.fromstring(z.read(sheet)).iter("{%s}row" % NS["m"]):
        row = {}
        for c in r.findall("m:c", NS):
            t, v = c.get("t"), c.find("m:v", NS)
            txt = None
            if t == "s" and v is not None:
                txt = ss[int(v.text)]
            elif t == "inlineStr":
                txt = "".join(x.text or "" for x in c.iter("{%s}t" % NS["m"]))
            elif v is not None:
                txt = v.text
            letters = _re.match(r"[A-Z]+", c.get("r")).group(0)
            idx = 0
            for ch in letters:
                idx = idx * 26 + ord(ch) - 64
            row[idx - 1] = txt
        if row:
            rows.append([row.get(i) for i in range(max(row) + 1)])
    return rows


def xlsx_links(kind):
    r = get(BANBEIS + FILE_PAGES[kind])
    links = []
    if r is not None and r.status_code == 200:
        for u in _re.findall(r"https://objectstorage[^\"'\s<>]+?\.xlsx", r.text):
            if u not in links:
                links.append(u)
    return links or [OBJ + f for f in FALLBACK_XLSX[kind]]


FREE_MAIL = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "ymail.com", "live.com", "yahoo.co.in",
             "rocketmail.com", "gmai.com", "ymai.com", "email.com", "mail.com", "googlemail.com", "icloud.com", "aol.com"}
INST_TOKENS = ["school", "schl", "college", "colg", "madras", "madrash", "dakhil", "dakil", "alim", "fazil", "kamil",
               "inst", "poly", "tech", "academy", "vidya", "bidya", "high", "girls", "balika", "mohila", "nursing",
               "varsity", "univ", "training", "voc", "office", "info", "principal", "headmaster", "eiin", "ttc",
               "registrar", "admission"]
INST_SUFFIX = _re.compile(r"(hs|ghs|jhs|jgs|hsc|sc|dm|am|fm|km|mdm|bmc|bm|tsc|ttc|tpi|pi|dc|mc|gc|sm|hm)\d*$")


def institutional_email(email, eiin, shared):
    """BANBEIS publishes one e-mail per institution. Keep it only when it looks like the institution's own
    address (own domain, contains the EIIN, or an institution word/abbreviation); drop placeholders, addresses
    shared by several institutions and personal-looking free-mail addresses."""
    e = (email or "").strip().lower()
    if not _re.match(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", e) or e.endswith("@banbeis.gov.bd"):
        return ""
    lp, dom = e.split("@", 1)
    if shared.get(e, 0) > 1 and eiin not in lp:
        return ""
    if dom not in FREE_MAIL:
        return e
    alnum = _re.sub(r"[^a-z0-9]", "", lp)
    if eiin and eiin in alnum or any(t in alnum for t in INST_TOKENS) or INST_SUFFIX.search(alnum):
        return e
    return ""


OWN = {"GOVERNMENT": "government", "NON-GOVERNMENT": "non_government", "LOCAL GOVERNMENT": "local_government",
       "AUTONOMOUS": "autonomous", "CRISTIAN MISSIONARY": "christian_missionary", "CANTONMENT BOARD": "cantonment_board",
       "NGO": "ngo", "OTHER": "other"}


def category(kind, x):
    name = (x.get("INSTITUTE_NAME") or "").upper()
    level = (x.get("EDUCATION_LEVEL_NAME") or "").upper()
    if kind == "school":
        return "education.primary_school" if "PRIMARY" in level else "education.secondary_school"
    if kind == "college":
        return "education.college"
    if kind == "madrasa":
        return "education.madrasa"
    if kind == "university":
        return "education.university"
    if kind == "professional":
        if "MEDICAL COLLEGE" in name:
            return "education.medical_college"
        if "TRAINING" in name or "TRAINING" in level or "INSTITUTE" in level:
            return "education.training_center"
        return "education.college"
    # technical lists
    if "POLYTECHNIC" in level or _re.search(r"POLY ?T[EI]CHNIC|POLITECHNIC", name):
        return "education.polytechnic"
    if _re.search(r"TRAINING|TRANING|TRAING|PROSHIK|PROSHIKH", name) or "NATIONAL SKILL" in level:
        return "education.training_center"
    return "education.technical"


def main():
    offline = ARGS.offline
    rawdir = os.path.join(OUT, "raw")  # created only when a list is saved, so a failed run writes nothing
    records = {}  # eiin -> (kind, row dict, [files])
    file_urls = {}
    header = None
    failed = []  # lists with a failed download: nothing is written for them, the run stops before the outputs
    for kind in FILE_PAGES:
        raw_path = os.path.join(rawdir, f"banbeis_{kind}_{DIV}_division.csv")
        div_rows = []
        done_mark = os.path.join(OUT, ".partial", kind + ".done")
        if not offline and not (ARGS.resume and os.path.exists(done_mark) and os.path.exists(raw_path)):
            ok = True
            for url in xlsx_links(kind):
                r = get(url, timeout=180)
                if r is None or r.status_code != 200:
                    print("FAILED", url)
                    ok = False
                    continue
                file_urls.setdefault(kind, []).append(url)
                rows = read_xlsx_bytes(r.content)
                hi = next(i for i, rr in enumerate(rows) if "DIVISION_NAME" in rr)
                h = [c.strip() for c in rows[hi]]
                for rr in rows[hi + 1:]:
                    d = dict(zip(h, rr))
                    if (d.get("DIVISION_NAME") or "").strip() in SRC_DIVISION_NAMES:
                        d["_file"] = url.rsplit("/", 1)[-1]
                        div_rows.append(d)
            if not ok and DIV != "rajshahi":  # keep raw/ and the outputs as they were; --resume skips the saved lists
                failed.append(kind)
                div_rows = []
                continue
            if div_rows:
                cols = sorted({k for d in div_rows for k in d}, key=lambda c: (c.startswith("_"), c))
                os.makedirs(rawdir, exist_ok=True)
                with open(raw_path, "w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, fieldnames=cols)
                    w.writeheader()
                    w.writerows(div_rows)
                os.makedirs(os.path.dirname(done_mark), exist_ok=True)
                open(done_mark, "w").close()
        if not div_rows and os.path.exists(raw_path):
            div_rows = list(csv.DictReader(open(raw_path, encoding="utf-8")))
        print(kind, len(div_rows))
        for d in div_rows:
            eiin = (d.get("EIIN_NO") or "").strip()
            if not eiin:
                continue
            if eiin in records:
                records[eiin][2].append(kind)
                continue
            records[eiin] = (kind, d, [kind])

    if not records and not failed:
        sys.exit("no institutions of the division in the lists or raw/; nothing written")
    if failed:
        sys.exit(f"download failed for {failed}; nothing written for them and no outputs rebuilt (re-run with --resume)")
    board = set()
    if DIV != "rajshahi":
        pass  # the Rajshahi Education Board cross-check applies to Rajshahi Division only
    elif not offline:
        r = get(BOARD_LIST, timeout=120)
        try:
            board = {x["eiin"] for x in r.json()["aaData"]} if r is not None else set()
        except (ValueError, KeyError):
            board = set()
        if board and os.path.isdir(rawdir):  # keep only EIINs of Rajshahi-Division institutions (the board list also covers Rangpur Division)
            with open(os.path.join(rawdir, "rajshahi_board_eiin_list.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(sorted(board & set(records))) + "\n")
    elif os.path.exists(os.path.join(rawdir, "rajshahi_board_eiin_list.txt")):
        board = set(open(os.path.join(rawdir, "rajshahi_board_eiin_list.txt")).read().split())

    shared = Counter((d.get("EMAIL") or "").strip().lower() for _, d, _ in records.values())
    rows = []
    for eiin, (kind, d, kinds) in records.items():
        dist = norm_district(d.get("DISTRICT_NAME"))
        upz = norm_upazila(d.get("THANA_NAME"), d.get("DISTRICT_NAME"))
        notes = []
        if not upz:
            notes.append(f"thana '{d.get('THANA_NAME')}' not normalised")
            if DIV != "rajshahi" and nfc(d.get("THANA_NAME")):  # other divisions: keep the source spelling
                upz = nfc(d.get("THANA_NAME"))
        if not dist and DIV != "rajshahi" and nfc(d.get("DISTRICT_NAME")):
            notes.append(f"district '{d.get('DISTRICT_NAME')}' not normalised")
            dist = nfc(d.get("DISTRICT_NAME"))
        if upazila_note(d.get("THANA_NAME")):
            notes.append(upazila_note(d.get("THANA_NAME")))
        if is_metro(upz, dist):
            notes.append(f"metropolitan thana of {DIVT} City, not an upazila")
        if upz in OTHER_THANAS:
            notes.append("thana listed by the source as its own unit, not an upazila")
        cat = category(kind, d)
        if kind == "school" and cat == "education.primary_school":
            notes.append("BANBEIS level 'Govt. Primary (pre to Eight)': primary school extended to class 8")
        if kind == "college" and (d.get("INSTITUTE_TYPE_NAME") or "") == "SCHOOL & COLLEGE":
            notes.append("school & college (classes 6-12); categorised as college")
        email = institutional_email(d.get("EMAIL"), eiin, shared)
        po = (d.get("POST_OFFICE_NAME") or "").strip()
        mpo = (d.get("IS_MPO") or "").strip()
        lvl = (d.get("EDUCATION_LEVEL_NAME") or "").strip()
        extra = {
            "eiin": eiin, "institute_type": d.get("INSTITUTE_TYPE_NAME"),
            "education_level": None if lvl in ("", "None") else lvl,
            "management": d.get("MANAGEMENT_NAME"), "mpo": None if mpo in ("", "None") else mpo,
            "for_whom": d.get("INSTITUTE_FOR_WHOM"), "geographical_position": d.get("GEOGRAPHICAL_POSITION_NAME"),
            "area_status": d.get("AREA_STATUS_NAME"), "post_office": None if po in ("", "None") else nfc(po),
            "thana_src": d.get("THANA_NAME"), "district_src": d.get("DISTRICT_NAME"),
            "banbeis_survey_year": d.get("BANBEIS_SURVEY_YEAR") or "2024", "banbeis_lists": kinds,
            "admin_unit": "metropolitan_thana" if is_metro(upz, dist) else "thana" if upz in OTHER_THANAS else "upazila",
        }
        if board and kind in ("school", "college"):
            extra["rajshahi_board_listed"] = eiin in board
        rows.append({
            "source_key": SOURCE_KEY, "source_id": f"eiin:{eiin}", "name_bn": "",
            "name_en": nfc(d.get("INSTITUTE_NAME")), "category_key": cat,
            "district_en": dist, "upazila_en": upz, "email": email,
            "ownership": OWN.get((d.get("MANAGEMENT_NAME") or "").strip(), ""),
            "extra_json": cj(extra), "source_url": DETAIL.format(eiin=eiin), "notes": "; ".join(notes),
        })
    rows.sort(key=lambda r: (r["district_en"] != DIVT, r["district_en"], r["upazila_en"], r["category_key"], r["name_en"]))
    write_csv("places.csv", PLACE_COLS, rows)

    facts = []
    cnt = Counter((r["district_en"], r["upazila_en"], r["category_key"]) for r in rows)
    dcnt = Counter((r["district_en"], r["category_key"]) for r in rows)
    note = "count of institutions with EIIN in BANBEIS e-survey 2024 lists (deduplicated by EIIN)"
    for (dist, cat), n in sorted(dcnt.items()):
        facts.append({"entity_level": "district", "entity_name_en": dist, "district_en": dist, "upazila_en": "",
                      "fact": "institutions_" + cat.split(".")[1], "value": n, "unit": "institutions",
                      "basis": "count_of_listed_records", "year": 2024, "source_key": SOURCE_KEY,
                      "source_url": BANBEIS + "/pages/files/69199760933eb65569ddc637", "notes": note})
    for (dist, upz, cat), n in sorted(cnt.items()):
        facts.append({"entity_level": "thana" if is_metro(upz, dist) or upz in OTHER_THANAS else "upazila", "entity_name_en": upz,
                      "district_en": dist, "upazila_en": upz, "fact": "institutions_" + cat.split(".")[1],
                      "value": n, "unit": "institutions", "basis": "count_of_listed_records", "year": 2024,
                      "source_key": SOURCE_KEY, "source_url": BANBEIS + "/pages/files/69199760933eb65569ddc637",
                      "notes": note})
    write_csv("facts.csv", FACT_COLS, facts)
    files = ["places.csv", "facts.csv"] + [f"raw/{f}" for f in sorted(os.listdir(rawdir))]
    update_manifest(files)
    if os.path.isdir(os.path.join(OUT, ".partial")):
        import shutil
        shutil.rmtree(os.path.join(OUT, ".partial"))
    print("places", len(rows), "facts", len(facts))
    print(Counter(r["category_key"] for r in rows))
    print(Counter(r["district_en"] for r in rows))


if __name__ == "__main__":
    main()
