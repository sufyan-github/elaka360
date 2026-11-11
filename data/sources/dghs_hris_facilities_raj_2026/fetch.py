#!/usr/bin/env python3
"""DGHS / MoHFW HRIS Facility Registry — Rajshahi Division facilities.

Source: https://hris.mohfw.gov.bd/public/facility-registry/reports/organization-list (public report, no login;
robots.txt allows everything). The report offers an Excel export (`ret=excel`) of the filtered list; we request
division_id[]=3 (Rajshahi) with a fixed column set, then normalise to places.csv + facts.csv.

Usage: python3 fetch.py            # download fresh export, keep a contact-sanitised CSV copy in raw/, rebuild CSVs
       python3 fetch.py --offline  # rebuild CSVs from the committed raw/ export
Stdlib + requests only.
"""
import csv, collections, datetime, hashlib, json, os, re, sys, unicodedata, zipfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
KEY = "DGHS_HRIS_FACILITIES_RAJ_2026"
BASE = "https://hris.mohfw.gov.bd/public/facility-registry/reports/organization-list"
PROFILE = "https://hris.mohfw.gov.bd/public/facility-registry/facilities/{id}/profile"
COLUMNS = ("id,name,name_bn,code,email_1,mobile_1,official_contact_no,land_phone_1,website_url,mailing_address,"
           "latitude,longitude,facility_agency_name,facility_type_name,facility_ownership_name,facility_level_name,"
           "facility_healthcare_level_name,facility_location_type_name,division_name,district_name,"
           "city_corporation_name,upazila_name,paurasava_name,union_name,is_private,establishment_year,"
           "approved_bed_number,revenue_bed_number,latest_bed_count")
RAW = os.path.join(HERE, "raw", "hris_organization_list_rajshahi_division.csv")
# Contact columns are blanked for private/NGO rows before anything is written to disk (may be personal numbers).
PRIVATE_BLANK = ("Email", "Mobile 1", "Official Contact No", "Land Phone 1", "Website Url", "Mailing Address")

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


NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def col_idx(ref):
    letters=re.match(r'[A-Z]+',ref).group(0); n=0
    for ch in letters: n=n*26+ord(ch)-64
    return n-1
def read_xlsx(path):
    z=zipfile.ZipFile(path)
    ss=[]
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',NS):
            ss.append(''.join(t.text or '' for t in si.iter('{%s}t'%NS['m'])))
    sheet=[n for n in z.namelist() if n.startswith('xl/worksheets/sheet')][0]
    rows=[]
    for r in ET.fromstring(z.read(sheet)).iter('{%s}row'%NS['m']):
        row={}
        for c in r.findall('m:c',NS):
            t=c.get('t'); v=c.find('m:v',NS); txt=None
            if t=='s' and v is not None: txt=ss[int(v.text)]
            elif t=='inlineStr':
                txt=''.join(x.text or '' for x in c.iter('{%s}t'%NS['m']))
            elif v is not None: txt=v.text
            row[col_idx(c.get('r'))]=txt
        if row: rows.append([row.get(i) for i in range(max(row)+1)])
    return rows


# ------------------------------------------------------------------ download
def download():
    import tempfile
    params = {"submit": "Run", "is_active": "1", "division_id[]": "3", "columns_csv": COLUMNS, "ret": "excel"}
    r = get(BASE, params=params, timeout=600)
    if r is None or r.status_code != 200 or not r.content.startswith(b"PK"):
        print("export download failed:", r and r.status_code, file=sys.stderr)
        return False
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as t:
        t.write(r.content)
    try:
        rows = read_xlsx(t.name)
    finally:
        os.unlink(t.name)
    head = [(h or "").strip() for h in rows[0]]
    os.makedirs(os.path.dirname(RAW), exist_ok=True)
    with open(RAW, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(head)
        for row in rows[1:]:
            d = dict(zip(head, [(c or "").strip() for c in row] + [""] * (len(head) - len(row))))
            if d.get("Private") == "1":
                for k in PRIVATE_BLANK:
                    if k in d:
                        d[k] = ""
            w.writerow([d.get(h, "") for h in head])
    print("saved", RAW, len(rows) - 1, "rows")
    return True


# ------------------------------------------------------------------ mapping
HOSPITAL_TYPES = {"10-bed Hospital", "20-bed Hospital", "25-bed Hospital", "30-bed Hospital", "31-bed Hospital",
                  "50-bed Hospital", "300-500 bed Hospital (not district hospital)", "District/General Hospital",
                  "District Level  Hospital(Not District Hospital)", "General Hospital (Non District Hospital)",
                  "Chest Disease Hospital", "Infectious Disease Hospital", "Leprosy Hospital", "Specialized Hospital",
                  "Special Purpose Hospital", "Trauma Center", "Jail Hospital", "Combined Military Hospital",
                  "Other Hospital", "Hospital of Alternative Medicine", "Postgraduate Institute & Hospital",
                  "City Corporation / Municipality Hospital", "Medical University Hospital", "Dental College Hospital"}
CLINIC_TYPES = {"Union Health Center", "Union Health Sub Center", "Union Health & Family Welfare Center (UH&FWC)",
                "Maternal & Child Welfare Centre (MCWC)", "Blood Bank", "Chest Disease Clinic", "Leprosy Clinic",
                "School Health Clinic", "Urban Dispensary", "Family Planning Clinic", "Sadar Clinic",
                "Maternal & Child Health Unit (MCH Unit)"}
TRAINING_TYPES = {"Nursing College/Nursing Institute", "Nursing College ( NC)", "Nursing Institute (NI)",
                  "Medical Assistants` Training School", "Regional Population Training Institute (RPTI)",
                  "Training Institute (TI)", "Regional Training Center (RTC)", "Regional Training Center",
                  "Institute of Population Research & Training", "Family Welfare Visitor Training Institute",
                  "Field Training Center (FTC)", "Palli Nursing Training Institute (PNTI)", "Institute of Midwifery"}
OFFICE_TYPES = {"Upazila Level Office", "District Office", "Divisional Level Office", "Divisional Office",
                "Medical Sub Depot", "Drug Testing Laboratory", "Drug Administration", "City Corporation Zone"}


def category(t, name, private):
    n = (name or "").lower()
    if t == "Upazila Health Complex":
        return "health.upazila_health_complex"
    if t == "Community Clinic":
        return "health.community_clinic"
    if t == "Consultancy & Diagnostic Center":
        return "health.diagnostic_center"
    if t == "Medical College Hospital":
        return "health.medical_college_hospital"
    if t in ("Medical College", "Dental College"):
        return "education.medical_college"
    if t == "Medical University":
        return "education.university"
    if t == "Institute of Health Technology":
        return "education.technical"
    if t in TRAINING_TYPES:
        return "education.training_center"
    if t in HOSPITAL_TYPES:
        return "health.hospital"
    if t in ("Private Hospital / Clinic", "NGO Hospital/Clinic", "NGO for Government Health Service support"):
        return "health.hospital" if "hospital" in n else "health.clinic"
    if t in CLINIC_TYPES:
        return "health.clinic"
    if t == "District Level Office":
        return "government.civil_surgeon" if "civil surgeon" in n else "government"
    if t == "City Corporation":
        return "government.city_corporation_office"
    if t == "Municipality":
        return "government.pourashava_office"
    if t in OFFICE_TYPES:
        return "government"
    return None  # "Other" etc. — left out (see REPORT.md)


def nfc(s):
    return unicodedata.normalize("NFC", re.sub(r"\s+", " ", s).strip()) if s else ""


def phone(s):
    s = re.sub(r"[^\d+]", "", s or "")
    if not s or set(s) <= {"0"} or len(s) < 6:
        return ""
    return s


UPAZILA_FIX = {"Matihar": "Motihar", "Mohonpur": "Mohanpur", "Baghmara": "Bagmara"}
METRO_THANAS = {"Boalia", "Rajpara", "Motihar", "Matihar", "Shah Makhdum", "Chandrima", "Kashiadanga", "Katakhali",
                "Belpukur", "Damkura", "Karnahar", "Airport", "Paba Metro"}
LAT, LON = (23.7, 25.5), (87.9, 90.0)  # generous Rajshahi Division bounding box


def load_district_polys():
    """Optional QA: district polygons from the sibling HDX folder (if present)."""
    p = os.path.join(HERE, "..", "hdx_cod_ab_bgd", "boundaries.geojson")
    if not os.path.isfile(p):
        return None
    g = json.load(open(p, encoding="utf-8"))
    return [(f["properties"]["name_en"], f["geometry"]) for f in g["features"] if f["properties"].get("level") == "district"]


def in_ring(x, y, ring):
    inside, j = False, len(ring) - 1
    for i in range(len(ring)):
        xi, yi, xj, yj = ring[i][0], ring[i][1], ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi:
            inside = not inside
        j = i
    return inside


DIST_ALIAS = {"chapainababganj": "chapainawabganj", "nawabganj": "chapainawabganj", "bogra": "bogura"}


def dkey(name):
    k = re.sub(r"[^a-z]", "", (name or "").lower())
    return DIST_ALIAS.get(k, k)


def district_of(polys, lon, lat):
    for name, g in polys or []:
        ps = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
        for p in ps:
            if in_ring(lon, lat, p[0]):
                return name
    return None


def build():
    with open(RAW, encoding="utf-8", newline="") as f:
        recs = [{k: (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f)]
    polys = load_district_polys()
    accessed = datetime.date.today().isoformat()
    places, skipped = [], collections.Counter()
    stats = collections.Counter()
    for r in recs:
        g = lambda k: r.get(k, "")
        private = g("Private") == "1"
        t = g("Type")
        cat = category(t, g("Name"), private)
        if not cat:
            skipped[t or "(no type)"] += 1
            continue
        notes = []
        lat = lon = ""
        try:
            la, lo = float(g("Latitude") or "x"), float(g("Longitude") or "x")
            if LAT[0] <= la <= LAT[1] and LON[0] <= lo <= LON[1]:
                lat, lon = f"{la:.6f}".rstrip("0").rstrip("."), f"{lo:.6f}".rstrip("0").rstrip(".")
                d = district_of(polys, lo, la) if polys else None
                if polys and g("District") and d and dkey(d) != dkey(g("District")):
                    notes.append(f"coordinates fall in {d} district, registry says {g('District')} — check")
                    stats["coord_district_mismatch"] += 1
                elif polys and d is None:
                    notes.append("coordinates fall outside Rajshahi Division polygons — check")
                    stats["coord_outside_division"] += 1
            else:
                notes.append(f"registry coordinates {g('Latitude')},{g('Longitude')} outside Rajshahi Division — dropped")
                stats["coord_out_of_range"] += 1
        except ValueError:
            if g("Latitude") or g("Longitude"):
                notes.append(f"unparseable coordinates {g('Latitude')!r},{g('Longitude')!r} — dropped")
        upz = g("Upazila")
        upz_n = UPAZILA_FIX.get(upz, upz)
        extra = {"facility_code": g("Code"), "hris_id": g("ID"), "facility_type": t,
                 "agency": g("Agency") or None, "level": g("Facility Level Name") or None,
                 "healthcare_level": g("Facility Healthcare Level Name") or None,
                 "location_type": g("Facility Location Type Name") or None,
                 "city_corporation": g("City Corporation") if g("City Corporation") and not g("City Corporation").startswith("Upazilas of") else None,
                 "paurasava": g("Paurasava") if g("Paurasava") and not g("Paurasava").lower().startswith("unions of") else None,
                 "union_or_ward": g("Union") or None,
                 "established": g("Establishment Year") if re.fullmatch(r"(1[89]|20)\d\d", g("Establishment Year")) else None,
                 "beds_approved": int(g("Approved Bed Number")) if g("Approved Bed Number").isdigit() and int(g("Approved Bed Number")) > 0 else None,
                 "beds_revenue": int(g("Revenue Bed Number")) if g("Revenue Bed Number").isdigit() and int(g("Revenue Bed Number")) > 0 else None,
                 "beds_latest": int(g("Latest Bed Count")) if g("Latest Bed Count").isdigit() and int(g("Latest Bed Count")) > 0 else None,
                 "private": private}
        if upz in METRO_THANAS:
            extra["admin_unit"] = "metropolitan_thana"
        if upz != upz_n:
            extra["upazila_src"] = upz
        extra = {k: v for k, v in extra.items() if v not in (None, "")}
        # Contacts: only for government / public facilities (registry-issued office numbers & DGHS mailboxes).
        # Private / NGO facilities' registered mobiles may be an owner's personal number -> not collected.
        ph = em = web = ""
        if not private:
            nums = []
            for k in ("Land Phone Number 1", "Official Contact No", "Mobile 1"):
                p = phone(g(k))
                if p and p not in nums:
                    nums.append(p)
            ph = "; ".join(nums)
            e = g("Email").lower()
            em = e if re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", e) else ""
            w = g("Website Url")
            web = w if w.startswith("http") else ""
        else:
            notes.append("private/NGO facility: contacts not collected")
        own = g("Facility Ownership Name")
        ownership = "private" if private else ("public" if own.startswith("Fully Government") or not own else own.lower())
        if not g("District"):
            notes.append("registry gives no district")
        places.append({
            "source_key": KEY, "source_id": f"hris:{g('ID')}", "name_bn": nfc(g("Name (Bangla)")), "name_en": nfc(g("Name")),
            "category_key": cat, "lat": lat, "lon": lon, "address": nfc(g("Mailing Address")) if not private else "",
            "district_en": g("District"), "upazila_en": upz_n, "phone": ph, "website": web, "email": em,
            "opening_hours": "", "operator": g("Agency"), "ownership": ownership,
            "extra_json": json.dumps(extra, ensure_ascii=False, separators=(",", ":")),
            "source_url": PROFILE.format(id=g("ID")), "notes": "; ".join(notes)})
    # flag likely duplicate registrations (same normalised English name, district and upazila)
    grp = collections.defaultdict(list)
    for p in places:
        grp[(re.sub(r"[^a-z0-9]", "", p["name_en"].lower()), p["district_en"], p["upazila_en"])].append(p)
    for v in grp.values():
        if len(v) > 1:
            stats["possible_duplicate_rows"] += len(v)
            for p in v:
                others = ",".join(x["source_id"] for x in v if x is not p)
                p["notes"] = "; ".join(filter(None, [p["notes"], f"possible duplicate registration of {others} (same name and upazila)"]))
    places.sort(key=lambda p: (p["district_en"] != "Rajshahi", p["district_en"], p["upazila_en"], p["category_key"], p["name_en"]))
    cols = "source_key,source_id,name_bn,name_en,category_key,lat,lon,address,district_en,upazila_en,phone,website,email,opening_hours,operator,ownership,extra_json,source_url,notes".split(",")
    with open(os.path.join(HERE, "places.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, cols); w.writeheader(); w.writerows(places)

    # facts: counts of listed records by facility type per district and per Rajshahi upazila/thana
    year = datetime.date.today().year
    fcols = "entity_level,entity_name_en,district_en,upazila_en,code,fact,value,unit,basis,year,source_key,source_url,notes".split(",")
    facts = []
    rep = BASE + "?submit=Run&is_active=1&division_id%5B0%5D=3"
    def add(level, name, dist, upz, fact, val, note=""):
        facts.append(dict(entity_level=level, entity_name_en=name, district_en=dist, upazila_en=upz, code="", fact=fact,
                          value=val, unit="facilities", basis="count_of_listed_records", year=year, source_key=KEY,
                          source_url=rep, notes=note))
    add("division", "Rajshahi", "", "", "health_registry_facilities_total", len(recs), "all active registry entries incl. private, offices, training institutes")
    by_d = collections.Counter(r.get("District") or "(none)" for r in recs)
    by_dt = collections.Counter((r.get("District") or "(none)", r.get("Type")) for r in recs)
    for d, n in sorted(by_d.items()):
        add("district", d, d if d != "(none)" else "", "", "health_registry_facilities_total", n)
    for (d, t), n in sorted(by_dt.items()):
        add("district", d, d if d != "(none)" else "", "", "health_registry_facilities:" + t, n)
    by_ut = collections.Counter((r.get("Upazila") or "(none)", r.get("Type")) for r in recs if r.get("District") == "Rajshahi")
    for (u, t), n in sorted(by_ut.items()):
        uu = UPAZILA_FIX.get(u, u)
        add("thana" if u in METRO_THANAS else "upazila", uu, "Rajshahi", uu if u != "(none)" else "", "health_registry_facilities:" + t, n)
    with open(os.path.join(HERE, "facts.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fcols); w.writeheader(); w.writerows(facts)

    print(f"{len(recs)} registry rows -> {len(places)} places ({sum(1 for p in places if p['lat'])} with coordinates); "
          f"{len(facts)} facts; skipped types: {dict(skipped)}; {dict(stats)}")
    update_manifest(accessed)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def update_manifest(accessed):
    p = os.path.join(HERE, "SOURCE.json")
    if not os.path.isfile(p):
        return
    m = json.load(open(p, encoding="utf-8"))
    m["files"] = {rel: sha(os.path.join(HERE, rel)) for rel in
                  ("places.csv", "facts.csv", "raw/hris_organization_list_rajshahi_division.csv")
                  if os.path.isfile(os.path.join(HERE, rel))}
    with open(p, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2); f.write("\n")


if __name__ == "__main__":
    if "--offline" not in sys.argv:
        if not download() and not os.path.isfile(RAW):
            sys.exit("no export available")
    build()
