#!/usr/bin/env python3
"""City corporation portal -> areas/facts. Default: Rajshahi City Corporation (erajshahi.portal.gov.bd) -> RCC_PORTAL_2026.

Re-runnable, self-contained (stdlib + requests). Usage: python3 -I fetch.py [--division rangpur] [--out DIR]
(--division rangpur: Rangpur City Corporation, rpcc.gov.bd -> RANGPUR_CITY_CORPORATION in ../rangpur_city_corporation;
 --division dhaka [--city dhaka_north|dhaka_south|narayanganj|gazipur]: the Dhaka Division city corporations, one folder each;
 --division chattogram [--city chattogram|cumilla]: Chattogram and Cumilla City Corporations;
 --division khulna [--city khulna]: Khulna City Corporation;
 --division barishal [--city barishal]: Barishal City Corporation;
 --division sylhet [--city sylhet]: Sylhet City Corporation, scc.gov.bd;
 --division mymensingh [--city mymensingh]: Mymensingh City Corporation, mcc.gov.bd)
Writes raw/ excerpts, areas.csv, facts.csv and refreshes the file checksums in SOURCE.json.
"""
import csv
import hashlib
import html
import json
import os
import re
import ssl
import sys
import tempfile
import time
import unicodedata
import urllib.robotparser
from urllib.parse import urlparse

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'raw')
UA = 'Elaka360-data-pipeline (research; contact via repository)'
ACCESSED = '2026-11-12'
DELAY = 1.2  # seconds between requests to the same host
# Many *.gov.bd servers do not send the Sectigo DV R36 intermediate. We add it (fetched from the
# certificate's AIA URL) to the system roots; TLS verification stays fully enabled.
AIA_INTERMEDIATES = ['http://crt.sectigo.com/SectigoPublicServerAuthenticationCADVR36.crt']

AREA_COLS = ['level', 'name_en', 'name_bn', 'parent_level', 'parent_name_en', 'parent_name_bn', 'district_en',
             'upazila_en', 'code', 'code_scheme', 'website', 'lat', 'lon', 'source_key', 'source_url', 'notes']
FACT_COLS = ['entity_level', 'entity_name_en', 'district_en', 'upazila_en', 'code', 'fact', 'value', 'unit', 'basis',
             'year', 'source_key', 'source_url', 'notes']

_session = None
_last = {}
_robots = {}
WARNINGS = []


def warn(msg):
    WARNINGS.append(msg)
    print('WARNING:', msg, file=sys.stderr)


def nfc(s):
    return unicodedata.normalize('NFC', s)


def _ca_bundle():
    roots = None
    try:
        import certifi
        roots = certifi.where()
    except ImportError:
        dv = ssl.get_default_verify_paths()
        for p in (dv.cafile, dv.openssl_cafile, '/etc/ssl/certs/ca-certificates.crt', '/etc/pki/tls/certs/ca-bundle.crt'):
            if p and os.path.exists(p):
                roots = p
                break
    if not roots:
        raise SystemExit('no system CA bundle found')
    pem = open(roots, encoding='ascii', errors='ignore').read()
    for u in AIA_INTERMEDIATES:
        # Plain-HTTP AIA download is safe: the intermediate is only trusted if it chains to a system root.
        der = requests.get(u, headers={'User-Agent': UA}, timeout=60).content
        pem += '\n' + (der.decode('ascii') if der.startswith(b'-----BEGIN') else ssl.DER_cert_to_PEM_cert(der))
    f = tempfile.NamedTemporaryFile('w', suffix='.pem', delete=False)
    f.write(pem)
    f.close()
    return f.name


def session():
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers['User-Agent'] = UA
        _session.verify = _ca_bundle()
    return _session


def _allowed(url):
    p = urlparse(url)
    host = p.netloc
    if host not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = _polite(p.scheme + '://' + host + '/robots.txt', check=False)
            ctype = r.headers.get('content-type', '')
            if r.status_code == 200 and 'text/plain' in ctype:
                rp.parse(r.text.splitlines())
            else:  # no robots.txt (portal returns an HTML page) -> nothing disallowed
                rp.parse([])
        except requests.RequestException:
            rp.parse([])
        _robots[host] = rp
    return _robots[host].can_fetch(UA, url)


def _polite(url, check=True, timeout=60):
    if check and not _allowed(url):
        raise SystemExit('robots.txt disallows ' + url)
    host = urlparse(url).netloc
    dt = time.time() - _last.get(host, 0)
    if dt < DELAY:
        time.sleep(DELAY - dt)
    try:
        return session().get(url, timeout=timeout)
    finally:
        _last[host] = time.time()


def get(url, binary=False):
    r = _polite(url)
    if r.status_code != 200:
        raise RuntimeError('HTTP %s %s' % (r.status_code, url))
    return r.content if binary else r.content.decode('utf-8', 'replace')


def status(url):
    return _polite(url).status_code


BN_DIGITS = '০১২৩৪৫৬৭৮৯'
BN_MONTHS = {'জানুয়ারি': 1, 'ফেব্রুয়ারি': 2, 'মার্চ': 3, 'এপ্রিল': 4, 'মে': 5, 'জুন': 6, 'জুলাই': 7, 'আগস্ট': 8,
             'সেপ্টেম্বর': 9, 'অক্টোবর': 10, 'নভেম্বর': 11, 'ডিসেম্বর': 12}


def asc(s):
    return ''.join(str(BN_DIGITS.index(c)) if c in BN_DIGITS else c for c in s)


def to_text(fragment):
    s = re.sub(r'<script.*?</script>|<style.*?</style>', '', fragment, flags=re.S)
    s = re.sub(r'<br\s*/?>|</p>|</tr>|</li>|</h\d>|</div>', '\n', s)
    s = re.sub(r'</td>|</th>', ' | ', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s).replace('\xa0', ' ')
    return nfc('\n'.join(re.sub(r'[ \t]+', ' ', l).strip() for l in s.split('\n') if l.strip()))


def page(url):
    """Fetch a National-Portal static page; return title, ISO update date, text, attachment URLs."""
    t = get(url)
    i = t.find('data-widget_name="ContentViewerWidget"')
    if i < 0:
        raise RuntimeError('no ContentViewerWidget in ' + url)
    seg = t[i:]
    j = seg.find('এই কনটেন্টটি শেয়ার')
    if j > 0:
        seg = seg[:j]
    m = re.search(r'content-update-block">\s*<p>\s*(.*?)</p>', seg, re.S)
    upd = nfc(html.unescape(m.group(1)).strip()) if m else ''
    m2 = re.search(r'(\S+) (\S+), (\S+) এ (\S+) ([AP]M)', upd)
    iso = ''
    if m2:
        d, mon, y, hm, ap = m2.groups()
        hh, mm = (int(x) for x in asc(hm).split(':'))
        hh = hh % 12 + (12 if ap == 'PM' else 0)
        iso = '%s-%02d-%02d %02d:%02d' % (asc(y), BN_MONTHS.get(mon, 0), int(asc(d)), hh, mm)
    m = re.search(r'<h2>(.*?)</h2>', seg, re.S)
    title = to_text(m.group(1)) if m else ''
    atts = sorted(set(re.findall(r'(https?://[^"\' ]+\.(?:pdf|xlsx?|docx?|csv))', seg)))
    seg = re.sub(r'encoded-content="[^"]*"', '', seg)
    txt = to_text(seg)
    txt = txt[txt.find('কন্টেন্ট: পাতা') + len('কন্টেন্ট: পাতা'):].strip() if 'কন্টেন্ট: পাতা' in txt else txt
    return {'url': url, 'title': title, 'updated_raw': upd, 'updated': iso, 'text': txt, 'attachments': atts}


def section(txt, start=None, end=None):
    if start:
        i = txt.find(start)
        if i < 0:
            warn('section start not found: ' + start)
        else:
            txt = txt[i:]
    if end:
        j = txt.find(end)
        if j > 0:
            txt = txt[:j]
    return txt


def redact_phones(txt):
    # Never keep phone numbers in raw excerpts (Bangla or ASCII digits, 01XXX-XXXXXX style).
    return re.sub(r'[০-৯0-9]{4,5}[-‐ ]?[০-৯0-9]{6}', '[redacted]', txt)


def save_raw(name, pg, txt=None):
    os.makedirs(RAW, exist_ok=True)
    body = txt if txt is not None else pg['text']
    with open(os.path.join(RAW, name), 'w', encoding='utf-8') as f:
        f.write('URL: %s\nTITLE: %s\nPAGE UPDATED: %s (%s)\nACCESSED: %s\n\n%s\n' % (
            pg['url'], pg['title'], pg['updated'], pg['updated_raw'], ACCESSED, body))


def expect(pg, *needles):
    """Each normalised value must still be visible on the page; otherwise warn (page changed)."""
    for n in needles:
        if nfc(n) not in pg['text']:
            warn('expected text not found on %s: %r' % (pg['url'], n))


def write_csv(name, cols, rows):
    with open(os.path.join(HERE, name), 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, '') for c in cols})


def sha256(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def update_manifest():
    p = os.path.join(HERE, 'SOURCE.json')
    m = json.load(open(p, encoding='utf-8'))
    files = {}
    for root, _, names in os.walk(HERE):
        for n in sorted(names):
            full = os.path.join(root, n)
            rel = os.path.relpath(full, HERE).replace(os.sep, '/')
            if rel in ('SOURCE.json', 'fetch.py', 'REPORT.md') or '__pycache__' in rel:
                continue
            files[rel] = sha256(full)
    m['files'] = dict(sorted(files.items()))
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(m, f, ensure_ascii=False, indent=2)
        f.write('\n')


def finish():
    update_manifest()
    if WARNINGS:
        print('%d warning(s); review before importing.' % len(WARNINGS), file=sys.stderr)


# ---------------------------------------------------------------------------------------------------------------
# Rajshahi City Corporation portal (erajshahi.portal.gov.bd). rcc.gov.bd / rcc.portal.gov.bd do not resolve (DNS).
# ---------------------------------------------------------------------------------------------------------------
KEY = 'RCC_PORTAL_2026'
B = 'https://erajshahi.portal.gov.bd/pages/static-pages/'
U_DARPAN = B + '6922e12c933eb65569e2aaf0'     # রাজশাহী মহানগরী দর্পণ
U_GLANCE = B + '6922df31933eb65569e207a2'     # রাজশাহীর ইতিহাস/লোকেশন/আয়তন (contains "এক নজরে রাজশাহী সিটি কর্পোরেশন")
U_MAYORS = B + '6922dbbc933eb65569e0c30c'     # পূর্বতন মেয়র ও প্রশাসক
U_WARDS = B + '6922db93933eb65569e0af91'      # ৩০টি ওয়ার্ডের দায়িত্বপ্রাপ্ত কর্মকর্তাবৃন্দ (scanned PDF attachment)
U_WARDSEC = B + '6ae2c685e0cf99482934fec4'    # ওয়ার্ড সচিবগণের মোবাইল ও ই মেইল (scanned PDF attachment)

CC = 'Rajshahi City Corporation'


def main_rajshahi():
    darpan = page(U_DARPAN)
    glance = page(U_GLANCE)
    mayors = page(U_MAYORS)
    wards = page(U_WARDS)
    wardsec = page(U_WARDSEC)

    expect(darpan, 'মোট আয়তন ৯৬ দশমিক ৭২ বর্গ কি:মি:', '৪৮ দশমিক ০৬ বর্গ কি:মি:', '৩০টি।',
           'কাশিয়াডাঙ্গা, রাজপাড়া, বোয়ালিয়া, শাহ্ মখদুম, চন্দ্রিমা ও মতিহার', 'সর্বমোট: ৫৫৩২৮৮ জন',
           'পুরুষ: ২৮৪৮১৮', 'নারী: ২৬৮৪২৩', 'হিজড়া: ৪৭', 'ঘনত্ব: ৫৬৯৩', '৮৮.৮৮%')
    expect(glance, '১৮৬৯ সালে রামপুর বোয়ালিয়া মিউনিসিপ্যালিটির সূচনা', '১৮৮৭ সালের ১৩ আগষ্ট',
           '১৯৯০ সালে মিউনিসিপ্যাল শব্দটির পরিবর্তে সিটি', '৪,৪৯,৭৫৬ (২০১১ সালের আদামশুমারী অনুযায়ী)',
           '১৩৪ টি', '৯৬.৭২ বর্গ কিলোমিটার')
    expect(mayors, '১৩.৮.১৯৮৭-১১.৯.১৯৮৮')
    if '৩০টি ওয়ার্ডের' not in wards['title']:
        warn('ward page title changed: ' + wards['title'])
    if len(wards['attachments']) != 1 or len(wardsec['attachments']) != 1:
        warn('ward PDF attachments changed; re-check ward numbers 1-30')

    save_raw('darpan.txt', darpan)
    save_raw('ek_nojore_rcc.txt', glance, section(glance['text'], 'এক নজরে রাজশাহী সিটি কর্পোরেশন', 'এক নজরে রাজশাহী জেলা'))
    save_raw('former_mayors_first_rows.txt', mayors, '\n'.join(mayors['text'].split('\n')[:4]))
    for name, pg in (('ward_officers_page.txt', wards), ('ward_secretaries_page.txt', wardsec)):
        save_raw(name, pg, 'Attachment(s) (scanned images; personal names/phones NOT copied):\n' + '\n'.join(pg['attachments']))

    d_url, g_url = U_DARPAN, U_GLANCE
    d_note = 'page updated ' + darpan['updated']
    g_note = 'page updated ' + glance['updated']
    areas = [dict(level='city_corporation', name_en=CC, name_bn='রাজশাহী সিটি কর্পোরেশন', parent_level='district',
                  parent_name_en='Rajshahi', parent_name_bn='রাজশাহী', district_en='Rajshahi',
                  website='https://erajshahi.portal.gov.bd/', source_key=KEY, source_url=d_url,
                  notes='Official portal is erajshahi.portal.gov.bd (rcc.gov.bd does not resolve). ' + d_note)]
    # Ward numbers 1-30: ward-officer PDF (uploaded 2026-08) and ward-secretary PDF (2026-09) list wards 01..30.
    # No ward names / mahalla lists are published on the portal.
    for n in range(1, 31):
        areas.append(dict(level='ward', name_en='Ward %d' % n, name_bn='ওয়ার্ড নং ' + ''.join(BN_DIGITS[int(c)] for c in str(n)),
                          parent_level='city_corporation', parent_name_en=CC, parent_name_bn='রাজশাহী সিটি কর্পোরেশন',
                          district_en='Rajshahi', code=str(n), code_scheme='RCC_WARD_NO', source_key=KEY,
                          source_url=U_WARDS,
                          notes='Ward number only; RCC publishes no ward name or mahalla list. Numbers 1-30 appear in the scanned '
                                'ward-officer list (%s) and ward-secretary list (%s). Name_bn is a label, not an official name.'
                                % (wards['attachments'][0] if wards['attachments'] else '', wardsec['attachments'][0] if wardsec['attachments'] else '')))
    for bn, en in (('কাশিয়াডাঙ্গা', 'Kashiadanga'), ('রাজপাড়া', 'Rajpara'), ('বোয়ালিয়া', 'Boalia'),
                   ('শাহ্ মখদুম', 'Shah Makhdum'), ('চন্দ্রিমা', 'Chandrima'), ('মতিহার', 'Motihar')):
        areas.append(dict(level='thana', name_en=en, name_bn=bn, parent_level='city_corporation', parent_name_en=CC,
                          parent_name_bn='রাজশাহী সিটি কর্পোরেশন', district_en='Rajshahi', source_key=KEY, source_url=d_url,
                          notes='Listed by RCC as one of 6 thanas in the city (Rajshahi Metropolitan Police). English name is a '
                                'transliteration. RMP lists 12 thanas in total (see RMP_PORTAL_2026). ' + d_note))
    write_csv('areas.csv', AREA_COLS, areas)

    def f(fact, value, unit, basis, year, url, notes):
        return dict(entity_level='city_corporation', entity_name_en=CC, district_en='Rajshahi', fact=fact, value=value,
                    unit=unit, basis=basis, year=year, source_key=KEY, source_url=url, notes=notes)
    facts = [
        f('wards_count', '30', 'wards', 'official', '2026', d_url, 'মহানগরী দর্পণ: ওয়ার্ড সংখ্যা ৩০টি; also এক নজরে (%s) and ward-officer list. %s' % (g_note, d_note)),
        f('area_km2', '96.72', 'km2', 'official', '', d_url, 'Per Rajshahi Development Authority master plan, as stated by RCC; also এক নজরে "প্রায় ৯৬.৭২". ' + d_note),
        f('area_city_proper_km2', '48.06', 'km2', 'official', '', d_url, 'RCC: of 96.72 km2, 48.06 km2 is the actual city ("প্রকৃত মহানগরী"), the remainder "নদীগর্ভে" (in the river). ' + d_note),
        f('established', '1987-08-13', 'date', 'official', '1987', U_MAYORS,
          'Rajshahi Pourashava upgraded to Rajshahi Municipal Corporation; first administrator term starts 13.8.1987 (former mayors table, page updated %s). '
          'The এক নজরে text prints "১৮৮৭ সালের ১৩ আগষ্ট" - a typo for 1987.' % mayors['updated']),
        f('renamed_city_corporation_year', '1990', 'year', 'official', '1990', g_url, '"১৯৯০ সালে মিউনিসিপ্যাল শব্দটির পরিবর্তে সিটি" (এক নজরে). ' + g_note),
        f('municipality_established_year', '1869', 'year', 'official', '1869', g_url, 'Rampur Boalia Municipality (এক নজরে). ' + g_note),
        f('population', '553288', 'persons', 'census', '2022', d_url, 'জনশুমারি ও গৃহগণনা ২০২২ অনুযায়ী (as stated by RCC). ' + d_note),
        f('population_male', '284818', 'persons', 'census', '2022', d_url, d_note),
        f('population_female', '268423', 'persons', 'census', '2022', d_url, d_note),
        f('population_hijra', '47', 'persons', 'census', '2022', d_url, d_note),
        f('population_density', '5693', 'persons_per_km2', 'census', '2022', d_url, 'As stated; basis area not stated. ' + d_note),
        f('literacy_rate', '88.88', 'percent', 'census', '2022', d_url, d_note),
        f('population', '449756', 'persons', 'census', '2011', g_url, '২০১১ সালের আদমশুমারী অনুযায়ী (এক নজরে). ' + g_note),
        f('mahalla_count', '134', 'mahallas', 'official', '', g_url, 'No mahalla names published. ' + g_note),
        f('thana_count', '6', 'thanas', 'official', '', d_url, 'Kashiadanga, Rajpara, Boalia, Shah Makhdum, Chandrima, Motihar (city thanas only; RMP has 12). ' + d_note),
        f('parliamentary_seats', '1', 'seats', 'official', '', g_url, g_note),
    ]
    write_csv('facts.csv', FACT_COLS, facts)
    finish()


# ---------------------------------------------------------------------------------------------------------------
# Rangpur City Corporation portal (rpcc.gov.bd, linked from rangpurdiv.gov.bd and rangpur.gov.bd "স্থানীয় সরকার").
# rpcc.portal.gov.bd / erangpur.portal.gov.bd do not resolve; rpcc.gov.bd omits the Sectigo DV R36 intermediate.
# ---------------------------------------------------------------------------------------------------------------
RP = 'https://rpcc.gov.bd/pages/static-pages/'
RP_GLANCE = RP + '6922dd53933eb65569e14850'      # এক নজরে রংপুর সিটি কর্পোরেশন
RP_LOCATION = RP + '6922dce1933eb65569e12890'    # অবস্থান ও আয়তন
RP_WARDS = RP + 'রংপুর-সিটি-কর্পোরেশনের-ওয়ার্ড-সংখ্যা-নির্ধারন-এবং-ওয়ার্ড-ভিত্তিক-সীমানা-নির্ধারণ-eyz1ua-6a0c231d2a941ac3be730868'
RP_COUNCILLORS = RP + '6971de1126b92f94c28c23e1'  # কাউন্সিলর তথ্যাদি (image attachment)
RP_CC = 'Rangpur City Corporation'
RP_CC_BN = 'রংপুর সিটি কর্পোরেশন'


def main_rangpur():
    glance = page(RP_GLANCE)
    loc = page(RP_LOCATION)
    wards = page(RP_WARDS)
    councillors = page(RP_COUNCILLORS)
    expect(glance, '২৮/০৬/২০১২', '১ মে ১৮৬৯', '২৩/০৯/১৯৮৬', '৩৩ টি।', 'মৌজা ১১২ টি', 'মহল্লা ৪৪২ টি', '২০৫.৭০ বর্গ কিঃ মিঃ',
           'প্রায় ৭৯৬৫৫৬ জন', 'পুরুষ ৩৯৮২৮২ জন', 'মহিলা ৩৯৮২৭৪ জন', 'শিক্ষিতের হার ৬৫%')
    expect(loc, '২০৩.৬৩ বর্গকিলোমিটার', '১১২টি মৌজা', '১২টি ইউনিয়ন', '৭টি ইউনিয়ন পূর্ণাঙ্গ ও ৫টি আংশিক')
    if 'ওয়ার্ড সংখ্যা নির্ধারন' not in wards['title'] or len(wards['attachments']) != 1:
        warn('ward-delimitation page changed: %r %r' % (wards['title'], wards['attachments']))

    save_raw('ek_nojore_rpcc.txt', glance, redact_phones(glance['text']))
    save_raw('location_area.txt', loc)
    save_raw('ward_delimitation_page.txt', wards, 'Attachment (scanned Bangladesh Gazette, extraordinary, 9 Sep 2012; ward -> mouza '
             'lists and reserved wards; not transcribed except the reserved-ward table):\n' + '\n'.join(wards['attachments']))
    save_raw('councillors_page.txt', councillors, 'Attachment(s) (image; personal names/phones NOT copied):\n' + '\n'.join(councillors['attachments']))

    g_note = 'এক নজরে updated ' + glance['updated']
    l_note = 'অবস্থান ও আয়তন updated ' + loc['updated']
    gaz = wards['attachments'][0] if wards['attachments'] else ''
    areas = [dict(level='city_corporation', name_en=RP_CC, name_bn=RP_CC_BN, parent_level='district', parent_name_en='Rangpur',
                  parent_name_bn='রংপুর', district_en='Rangpur', website='https://rpcc.gov.bd/', source_key=RP_KEY, source_url=RP_GLANCE,
                  notes='Official portal rpcc.gov.bd. ' + g_note)]
    # 33 general wards; the 2012 LGD gazette (scanned, page 8) groups them into 11 reserved (women's) wards of 3 wards each.
    for n in range(1, 34):
        res = (n - 1) // 3 + 1
        areas.append(dict(level='ward', name_en='Ward %d' % n, name_bn='ওয়ার্ড নং ' + ''.join(BN_DIGITS[int(c)] for c in str(n)),
                          parent_level='city_corporation', parent_name_en=RP_CC, parent_name_bn=RP_CC_BN, district_en='Rangpur',
                          code=str(n), code_scheme='RPCC_WARD_NO', source_key=RP_KEY, source_url=RP_WARDS,
                          notes='Ward number only (name_bn is a label). RPCC has 33 wards (এক নজরে); the ward-delimitation gazette '
                                '(Bangladesh Gazette extraordinary, 9 Sep 2012, scanned PDF %s) lists the mouzas of each ward (not '
                                'transcribed) and puts ward %d in reserved (women\'s) ward %d. %s' % (gaz, n, res, g_note)))
    write_csv('areas.csv', AREA_COLS, areas)

    def f(fact, value, unit, basis, year, url, notes):
        return dict(entity_level='city_corporation', entity_name_en=RP_CC, district_en='Rangpur', fact=fact, value=value,
                    unit=unit, basis=basis, year=year, source_key=RP_KEY, source_url=url, notes=notes)
    facts = [
        f('wards_count', '33', 'wards', 'official', '', RP_GLANCE, 'এক নজরে: ওয়ার্ড সংখ্যা ৩৩ টি; the 2012 delimitation gazette also has 33. '
          'RpMP\'s history page says 30 wards (outdated). ' + g_note),
        f('reserved_wards_count', '11', 'wards', 'official', '2012', RP_WARDS,
          'Reserved (women\'s) wards 1-11, each covering 3 consecutive general wards (1-3 ... 31-33); read from the scanned gazette '
          'attachment, not machine-checked.'),
        f('established', '2012-06-28', 'date', 'official', '2012', RP_GLANCE,
          'City corporation established 28/06/2012 (এক নজরে). RpMP\'s history page gives 1 July 2012. ' + g_note),
        f('municipality_established_year', '1869', 'year', 'official', '1869', RP_GLANCE, 'Pourashava founded 1 May 1869 (এক নজরে). ' + g_note),
        f('pourashava_class_a_date', '1986-09-23', 'date', 'official', '1986', RP_GLANCE, 'Upgraded to class (ক) pourashava 23/09/1986. ' + g_note),
        f('area_km2', '205.70', 'km2', 'official', '', RP_GLANCE, 'এক নজরে "২০৫.৭০ বর্গ কিঃ মিঃ" (the same figure is repeated, by mistake, '
          'as the household count). The location page gives 203.63 km2. ' + g_note),
        f('area_km2', '203.63', 'km2', 'official', '', RP_LOCATION, 'অবস্থান ও আয়তন: "আয়তন এখন ২০৩.৬৩ বর্গকিলোমিটার"; conflicts with 205.70 on '
          'the এক নজরে page. ' + l_note),
        f('population', '796556', 'persons', 'official', '', RP_GLANCE, '"প্রায় ৭৯৬৫৫৬ জন" (approximate); year and basis not stated. ' + g_note),
        f('population_male', '398282', 'persons', 'official', '', RP_GLANCE, 'Year and basis not stated. ' + g_note),
        f('population_female', '398274', 'persons', 'official', '', RP_GLANCE, 'Year and basis not stated. ' + g_note),
        f('literacy_rate', '65', 'percent', 'official', '', RP_GLANCE, 'Year and basis not stated. ' + g_note),
        f('mouza_count', '112', 'mouzas', 'official', '', RP_GLANCE, 'Also on the location page. ' + g_note),
        f('mahalla_count', '442', 'mahallas', 'official', '', RP_GLANCE, 'No mahalla names published. ' + g_note),
        f('jurisdiction', '12 unions merged (10 of Rangpur Sadar, Sarai of Kaunia, Kalyani of Pirgachha): 7 whole, 5 partial, 112 mouzas; '
          'cantonment excluded', 'text', 'official', '', RP_LOCATION, l_note),
    ]
    write_csv('facts.csv', FACT_COLS, facts)
    meta = {'key': RP_KEY, 'division': 'rangpur', 'kind': 'city_corporation',
            'name': 'Rangpur City Corporation official portal (rpcc.gov.bd)', 'organization': 'Rangpur City Corporation',
            'source_type': 'government_portal', 'trust_level': 4,
            'urls': ['https://rpcc.gov.bd/', RP_GLANCE, RP_LOCATION, RP_WARDS, RP_COUNCILLORS], 'accessed': ACCESSED,
            'publication_date': None, 'license': None, 'license_url': None,
            'attribution': 'Rangpur City Corporation (rpcc.gov.bd), Bangladesh National Portal',
            'notes': 'rpcc.portal.gov.bd does not resolve; the RPCC portal is rpcc.gov.bd. Key pages: এক নজরে রংপুর সিটি কর্পোরেশন '
                     '(updated %s), অবস্থান ও আয়তন (%s), ward delimitation (scanned 2012 gazette PDF, page %s). Ward and councillor '
                     'lists are scanned images/PDFs; officials\' names and phones are not copied. No ward names or mahalla lists '
                     'are published.' % (glance['updated'], loc['updated'], wards['updated'])}
    with open(os.path.join(HERE, 'SOURCE.json'), 'w', encoding='utf-8') as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
        fh.write('\n')
    finish()


RP_KEY = 'RANGPUR_CITY_CORPORATION'
# --- division selection (see ../DIVISIONS.md) --------------------------------------------------------------
# `python3 fetch.py` = `--division rajshahi`, output into this folder (unchanged behaviour). Other divisions write into
# their own folder (default: the sibling folder named per DIVISIONS.md) and never into the Rajshahi folder.
import argparse
DIVISION_CHOICES = ("rajshahi", "rangpur", "dhaka", "chattogram", "khulna", "barishal", "sylhet", "mymensingh")
DIVISION = "rajshahi"


def parse_division_args(folders):
    """Parse --division/--out. folders: division -> default output folder name (a sibling of this folder)."""
    ap = argparse.ArgumentParser(description=(__doc__ or "").strip().split("\n")[0])
    ap.add_argument("--division", default="rajshahi", choices=DIVISION_CHOICES)
    ap.add_argument("--out", help="output folder (default: this folder for rajshahi, ../<division folder> otherwise)")
    a = ap.parse_args()
    if a.division not in folders:
        raise SystemExit("this collector has no table for division %r yet (see DIVISIONS.md)" % a.division)
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.abspath(a.out or os.path.join(here, "..", folders[a.division]))
    if a.division != "rajshahi" and os.path.realpath(out) == os.path.realpath(here):
        raise SystemExit("refusing to write %s output into the Rajshahi folder %s" % (a.division, here))
    os.makedirs(out, exist_ok=True)
    return a.division, out


def write_division_manifest(out, meta):
    """SOURCE.json for a non-default division run: meta + sha256 of every data file in the output folder."""
    import hashlib as _h, json as _j
    files = {}
    for root, _, names in os.walk(out):
        for n in sorted(names):
            full = os.path.join(root, n)
            rel = os.path.relpath(full, out).replace(os.sep, "/")
            if rel in ("SOURCE.json", "fetch.py", "REPORT.md") or "__pycache__" in rel:
                continue
            files[rel] = _h.sha256(open(full, "rb").read()).hexdigest()
    m = dict(meta)
    m["files"] = dict(sorted(files.items()))
    with open(os.path.join(out, "SOURCE.json"), "w", encoding="utf-8") as f:
        f.write(_j.dumps(m, ensure_ascii=False, indent=2) + "\n")


SITES = {  # division -> city corporation collector (city name, portal, output folder)
    'rajshahi': dict(city='Rajshahi City Corporation', portal='https://erajshahi.portal.gov.bd/', key=KEY, folder='rcc', run=main_rajshahi),
    'rangpur': dict(city=RP_CC, portal='https://rpcc.gov.bd/', key=RP_KEY, folder='rangpur_city_corporation', run=main_rangpur),
}


# ---------------------------------------------------------------------------------------------------------------
# Dhaka Division: four city corporations, one output folder each (DIVISIONS.md). SOURCE.json carries "city": seed id.
# ---------------------------------------------------------------------------------------------------------------
def bn_int(s):
    return int(re.sub(r'[^0-9]', '', asc(s)) or 0)


def bn_num(s):
    return asc(s).replace(',', '').strip()


def html_tables(fragment):
    """<table>s of a page fragment -> list of tables (list of rows of cleaned cell texts)."""
    out = []
    for tb in re.findall(r'<table\b.*?</table>', fragment, flags=re.S | re.I):
        rows = []
        for tr in re.findall(r'<tr\b.*?</tr>', tb, flags=re.S | re.I):
            cells = [nfc(re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', c)).replace('\xa0', ' ')).strip())
                     for c in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>', tr, flags=re.S | re.I)]
            if any(cells):
                rows.append(cells)
        out.append(rows)
    return out


def content_html(url):
    t = get(url)
    i = t.find('data-widget_name="ContentViewerWidget"')
    seg = t[i:] if i >= 0 else t
    j = seg.find('এই কনটেন্টটি শেয়ার')
    return seg[:j] if j > 0 else seg


def sentences(txt, *keys):
    """Only the sentences of a page that carry the cited facts (raw/ excerpts leave out officials' names)."""
    parts = re.split(r'(?<=[।.])\s+|\n', txt)
    return '\n'.join(dict.fromkeys(p.strip() for p in parts if any(k in p for k in keys)))


def write_city_manifest(meta):
    with open(os.path.join(HERE, 'SOURCE.json'), 'w', encoding='utf-8') as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
        fh.write('\n')
    finish()


def ward_rows(cc, cc_bn, key, scheme, url, numbers, note_of):
    return [dict(level='ward', name_en='Ward %d' % n, name_bn='ওয়ার্ড নং ' + ''.join(BN_DIGITS[int(c)] for c in str(n)),
                 parent_level='city_corporation', parent_name_en=cc, parent_name_bn=cc_bn, district_en=CITY['district'],
                 code=str(n), code_scheme=scheme, source_key=key, source_url=url, notes=note_of(n)) for n in numbers]


def cc_fact(key, cc, district):
    def f(fact, value, unit, basis, year, url, notes, level='city_corporation', name=None):
        return dict(entity_level=level, entity_name_en=name or cc, district_en=district, fact=fact, value=value, unit=unit,
                    basis=basis, year=year, source_key=key, source_url=url, notes=notes)
    return f


# --- Dhaka North City Corporation (dncc.gov.bd) ---------------------------------------------------------------
DN = 'https://dncc.gov.bd/pages/static-pages/'
DN_LOCATION = DN + '6922ded3933eb65569e1da8e'   # লোকেশন ও আয়তন (zones, wards and their areas)
DN_HISTORY = DN + '6922e044933eb65569e2644c'    # ইতিহাস (English text)
DN_CONTACT = DN + '6922df76933eb65569e2224e'    # যোগাযোগ (Nagar Bhaban address)


def main_dncc():
    key, cc, cc_bn = CITY['key'], 'Dhaka North City Corporation', 'ঢাকা উত্তর সিটি কর্পোরেশন'
    loc, hist, contact = page(DN_LOCATION), page(DN_HISTORY), page(DN_CONTACT)
    expect(loc, 'অঞ্চল সংখ্যাঃ ১০', 'ওয়ার্ড সংখ্যাঃ ৫৪', 'আয়তনঃ ১৯৬.২২ বর্গ কিঃ মিঃ')
    expect(hist, 'Dhaka Municipality was established on 1st August, 1864', 'has divided as Dhaka South City Corporation (DSCC) and Dhaka North City Corporation (DNCC)')
    # zone headings ("অঞ্চল-N") precede each ward table: rows (serial, ward no, areas of the ward)
    seg = content_html(DN_LOCATION)
    zone_of, areas_of, zone = {}, {}, None
    for part in re.split(r'(?=<table\b)', seg):
        m = re.match(r'<table\b.*?</table>', part, flags=re.S)
        for rows in html_tables(m.group(0)) if m else []:
            for c in rows:
                if len(c) >= 3 and re.fullmatch(r'[০-৯0-9]+', c[1] or '') and zone:
                    zone_of[bn_int(c[1])] = zone
                    areas_of[bn_int(c[1])] = c[2].rstrip(' ।|')
        hz = re.findall(r'অঞ্চল\s*-\s*([০-৯0-9]+)', re.sub(r'<[^>]+>', ' ', part[m.end():] if m else part))
        if hz:   # the heading after this table names the zone of the next one
            zone = bn_int(hz[-1])
    if sorted(zone_of) != list(range(1, 55)):
        warn('DNCC ward list is not 1-54: %s' % sorted(zone_of))
    save_raw('location_and_area.txt', loc)
    save_raw('history_split.txt', hist, sentences(hist['text'], '1st August, 1864', 'Amendment-2011'))
    save_raw('contact.txt', contact, redact_phones(contact['text']))
    note = 'লোকেশন ও আয়তন updated ' + loc['updated']
    addr = re.search(r'গুলশান সেন্টার পয়েন্ট,?\s*প্লট নং- ২৩-২৬, রোড নং- ৪৬,?\s*গুলশান-২, ঢাকা-১২১২', contact['text'].replace('\n', ' '))
    areas = [dict(level='city_corporation', name_en=cc, name_bn=cc_bn, parent_level='district', parent_name_en='Dhaka', parent_name_bn='ঢাকা',
                  district_en='Dhaka', website='https://dncc.gov.bd/', source_key=key, source_url=DN_LOCATION,
                  notes='Official portal dncc.gov.bd. Nagar Bhaban: %s (যোগাযোগ). %s' % (addr.group(0) if addr else '?', note))]
    areas += ward_rows(cc, cc_bn, key, 'DNCC_WARD_NO', DN_LOCATION, sorted(zone_of),
                       lambda n: 'Ward number (name_bn is a label); DNCC zone (অঞ্চল) %d. The areas DNCC lists for the ward are in facts.csv '
                                 '(ward_areas). %s' % (zone_of[n], note))
    write_csv('areas.csv', AREA_COLS, areas)
    f = cc_fact(key, cc, 'Dhaka')
    zones = {}
    for n, z in sorted(zone_of.items()):
        zones.setdefault(z, []).append(n)
    facts = [
        f('wards_count', '54', 'wards', 'official', '', DN_LOCATION, '"ওয়ার্ড সংখ্যাঃ ৫৪"; the ward table lists %d wards. %s' % (len(zone_of), note)),
        f('zones_count', '10', 'zones', 'official', '', DN_LOCATION, '"অঞ্চল সংখ্যাঃ ১০". ' + note),
        f('zone_wards', '; '.join('zone %d: %s' % (z, ','.join(map(str, ws))) for z, ws in sorted(zones.items())), 'text', 'official', '',
          DN_LOCATION, 'Wards per DNCC zone (অঞ্চল) as listed. ' + note),
        f('area_km2', '196.22', 'km2', 'official', '', DN_LOCATION, '"আয়তনঃ ১৯৬.২২ বর্গ কিঃ মিঃ". ' + note),
        f('extent', 'longitude 90°20′–90°28′ E, latitude 23°44′–23°54′ N', 'text', 'official', '', DN_LOCATION,
          'As printed ("দ্রাঘিমাংশঃ ৯০ o ২০’ – ৯০ o ২৮’", "অক্ষাংশঃ ২৩ o ৪৪’ – ২৩ o ৫৪"). ' + note),
        f('municipality_established', '1864-08-01', 'date', 'official', '1864', DN_HISTORY,
          'Dhaka Municipality (predecessor of DCC, split in 2011 into DNCC and DSCC); history page updated %s.' % hist['updated']),
        f('created_by', 'Local Government (City Corporation) Act 2009 (Amendment 2011): Dhaka City Corporation divided into DSCC and DNCC',
          'text', 'official', '2011', DN_HISTORY, 'DNCC history page (no date given there; DSCC\'s history gives 4 Dec 2011 / 1 Feb 2012).'),
    ] + [f('ward_areas', areas_of[n], 'text', 'listed', '', DN_LOCATION, 'Areas (mahallas/sectors) DNCC lists for ward %d, zone %d; '
           'spellings as printed. %s' % (n, zone_of[n], note), level='ward', name='Ward %d' % n) for n in sorted(areas_of)]
    write_csv('facts.csv', FACT_COLS, facts)
    write_city_manifest({'key': key, 'division': 'dhaka', 'kind': 'city_corporation', 'city': CITY['city'],
                         'name': 'Dhaka North City Corporation official portal (dncc.gov.bd)', 'organization': cc,
                         'source_type': 'government_portal', 'trust_level': 4, 'urls': ['https://dncc.gov.bd/', DN_LOCATION, DN_HISTORY, DN_CONTACT],
                         'accessed': ACCESSED, 'publication_date': None, 'license': None, 'license_url': None,
                         'attribution': 'Dhaka North City Corporation (dncc.gov.bd), Bangladesh National Portal',
                         'notes': 'Key page: লোকেশন ও আয়তন (updated %s): 10 zones, 54 wards, 196.22 km2, and the areas of each ward. '
                                  'DNCC publishes no population figure and no thana list. Ward officers\' and ward secretaries\' '
                                  'lists (names, mobiles) are not copied.' % loc['updated']})


# --- Dhaka South City Corporation (dscc.gov.bd) ---------------------------------------------------------------
DS = 'https://dscc.gov.bd/pages/static-pages/'
DS_GLANCE = DS + '6922df02933eb65569e1f260'     # এক নজরে ঢাকা দক্ষিণ
DS_HISTORY = DS + '6922defc933eb65569e1eedf'    # ইতিহাস
DS_ZONES = DS + '6922dba8933eb65569e0b9ed'      # জরুরী যোগাযোগ (zone offices and their wards)
DS_WARDLOC = DS + '6922e104933eb65569e29a09'    # লোকেশন (ওয়ার্ড ভিত্তিক): scanned PDF (zones, wards, mahallas)


def main_dscc():
    key, cc, cc_bn = CITY['key'], 'Dhaka South City Corporation', 'ঢাকা দক্ষিণ সিটি কর্পোরেশন'
    glance, hist, zonep, wardloc = page(DS_GLANCE), page(DS_HISTORY), page(DS_ZONES), page(DS_WARDLOC)
    expect(glance, '১ আগস্ট ১৮৬৪', 'প্রশাসনিক ওয়ার্ডের সংখ্যা | ৭৫', '৩৮,৮৩,৪২৩ জন (আদমশুমারী ২০১১ অনুযায়ী)', '৪৩,০৪৮৯৩ জন (জনশুমারী ২০২২ অনুযায়ী)',
           '১০৯.২৪ বর্গ কি.মি.', 'থানার সংখ্যা | ২৩টি', 'প্রশাসনিক জোনের সংখ্যা | ১০ টি', '২৩ লাখ ৬৭ হাজার ৪৮৮ জন (২০২০)')
    expect(hist, '২০১১ সালের ৪ ডিসেম্বর', '২০১২ সালের ১ ফেব্রুয়ারি', '৫৭টি ওয়ার্ড', '৯ মে, ২০১৬', '১৮টি ওয়ার্ড', '৭৫টি',
           '৩৮,৮৩,৪২৩ জন', '৪২,৯৯, ৩৪৫ জন')
    zone_of, dup = {}, []
    for rows in html_tables(content_html(DS_ZONES)):
        for c in rows:
            if len(c) >= 4 and re.fullmatch(r'[০-৯0-9]+', c[0]):
                for w in re.findall(r'[০-৯0-9]+', c[3]):
                    n = bn_int(w)
                    if n in zone_of:
                        dup.append((n, zone_of[n], bn_int(c[0])))
                    zone_of.setdefault(n, bn_int(c[0]))
    missing = [n for n in range(1, 76) if n not in zone_of]
    save_raw('ek_nojore_dscc.txt', glance, sentences(glance['text'], 'স্থাপিত') + '\n' +
             section(glance['text'], 'প্রশাসনিক ওয়ার্ডের সংখ্যা', 'অনুমোদিত স্থায়ী'))
    save_raw('history_split.txt', hist, sentences(hist['text'], '২০১১ সালের আদমশুমারী', '২৩ নভেম্বর', '৪ ডিসেম্বর', '১ ফেব্রুয়ারি',
                                                  '৫৭টি ওয়ার্ড', '৯ মে, ২০১৬', '৭৫টি', 'মোট ভোটার'))
    save_raw('zone_offices.txt', zonep, redact_phones(zonep['text']))
    save_raw('ward_location_page.txt', wardloc, 'Attachment (scanned PDF, 2021: zone -> DSCC ward -> mahallas, "সংশ্লিষ্ট গেজেট অনুযায়ী"; '
             'not transcribed):\n' + '\n'.join(a for a in wardloc['attachments'] if a.endswith('.pdf')))
    g_note, h_note, z_note = ('এক নজরে updated ' + glance['updated'], 'ইতিহাস updated ' + hist['updated'],
                              'জরুরী যোগাযোগ updated ' + zonep['updated'])
    areas = [dict(level='city_corporation', name_en=cc, name_bn=cc_bn, parent_level='district', parent_name_en='Dhaka', parent_name_bn='ঢাকা',
                  district_en='Dhaka', website='https://dscc.gov.bd/', source_key=key, source_url=DS_GLANCE,
                  notes='Official portal dscc.gov.bd. ' + g_note)]

    def wnote(n):
        z = ('DSCC zone %d per the zone-office table' % zone_of[n]) if n in zone_of else 'not in the zone-office table'
        d = [x for x in dup if x[0] == n]
        if d:
            z += ' (also listed under zone %d there)' % d[0][2]
        return 'Ward number (name_bn is a label); %s. DSCC has 75 wards (এক নজরে); no ward names are published (the scanned 2021 ' \
               'ward-location PDF lists mahallas, not transcribed). %s' % (z, g_note)
    areas += ward_rows(cc, cc_bn, key, 'DSCC_WARD_NO', DS_GLANCE, range(1, 76), wnote)
    write_csv('areas.csv', AREA_COLS, areas)
    f = cc_fact(key, cc, 'Dhaka')
    zones = {}
    for n, z in sorted(zone_of.items()):
        zones.setdefault(z, []).append(n)
    facts = [
        f('wards_count', '75', 'wards', 'official', '', DS_GLANCE, 'প্রশাসনিক ওয়ার্ডের সংখ্যা ৭৫; general-ward councillors 75, reserved-ward '
          'councillors 25. History: 57 wards at the 2011/12 split + 18 wards formed from 8 fringe unions after the NICAR decision of 9 May 2016. ' + g_note),
        f('reserved_wards_count', '25', 'wards', 'official', '', DS_GLANCE, 'ওয়ার্ড কাউন্সিলর (সংরক্ষিত ওয়ার্ড) ২৫ জন. ' + g_note),
        f('zones_count', '10', 'zones', 'official', '', DS_GLANCE, 'প্রশাসনিক জোনের সংখ্যা ১০. ' + g_note),
        f('zone_wards', '; '.join('zone %d: %s' % (z, ','.join(map(str, ws))) for z, ws in sorted(zones.items())), 'text', 'official', '',
          DS_ZONES, 'Wards per zone office as listed. %s%s %s' % (
              'Ward(s) listed under two zones: %s. ' % ', '.join('%d (zones %d and %d)' % d for d in dup) if dup else '',
              'Not listed: ward(s) %s.' % ', '.join(map(str, missing)) if missing else '', z_note)),
        f('area_km2', '109.24', 'km2', 'official', '', DS_GLANCE, 'আয়তন ১০৯.২৪ বর্গ কি.মি. ' + g_note),
        f('population', '3883423', 'persons', 'census', '2011', DS_GLANCE, '৩৮,৮৩,৪২৩ জন (আদমশুমারী ২০১১ অনুযায়ী); same figure on the history page. ' + g_note),
        f('population', '4304893', 'persons', 'census', '2022', DS_GLANCE, 'Printed "৪৩,০৪৮৯৩ জন (জনশুমারী ২০২২ অনুযায়ী)" (digit grouping as printed). '
          'Conflicts with the history page\'s 2022 figure 4,299,345. ' + g_note),
        f('population', '4299345', 'persons', 'census', '2022', DS_HISTORY, 'History page: "২০২২ সালের জনশুমারী অনুযায়ী ... ৪২,৯৯, ৩৪৫ জন". '
          'Conflicts with 4,304,893 on the এক নজরে page. ' + h_note),
        f('voters', '2367488', 'persons', 'official', '2020', DS_GLANCE, 'ভোটার ২৩ লাখ ৬৭ হাজার ৪৮৮ জন (২০২০). ' + g_note),
        f('thana_count', '23', 'thanas', 'official', '', DS_GLANCE, 'থানার সংখ্যা ২৩টি; DSCC does not name them. ' + g_note),
        f('municipality_established', '1864-08-01', 'date', 'official', '1864', DS_GLANCE, '"স্থাপিত ১ আগস্ট ১৮৬৪" (Dhaka Pourashava). ' + g_note),
        f('split_effective', '2011-12-04', 'date', 'official', '2011', DS_HISTORY, 'Dhaka City Corporation divided into two from 4 Dec 2011 '
          '(dissolved 23 Nov 2011 by the Local Government amendment). ' + h_note),
        f('established', '2012-02-01', 'date', 'official', '2012', DS_HISTORY, 'DNCC and DSCC "যাত্রা শুরু" 1 Feb 2012; DSCC began with 5 zones '
          'and 57 wards. ' + h_note),
    ]
    write_csv('facts.csv', FACT_COLS, facts)
    write_city_manifest({'key': key, 'division': 'dhaka', 'kind': 'city_corporation', 'city': CITY['city'],
                         'name': 'Dhaka South City Corporation official portal (dscc.gov.bd)', 'organization': cc,
                         'source_type': 'government_portal', 'trust_level': 4,
                         'urls': ['https://dscc.gov.bd/', DS_GLANCE, DS_HISTORY, DS_ZONES, DS_WARDLOC],
                         'accessed': ACCESSED, 'publication_date': None, 'license': None, 'license_url': None,
                         'attribution': 'Dhaka South City Corporation (dscc.gov.bd), Bangladesh National Portal',
                         'notes': 'Key pages: এক নজরে ঢাকা দক্ষিণ (updated %s), ইতিহাস (%s), জরুরী যোগাযোগ zone-office table (%s). The '
                                  'ward-location page is a scanned 2021 PDF (zones, wards, mahallas) and is not transcribed. Officials\' '
                                  'names and phones are not copied.' % (glance['updated'], hist['updated'], zonep['updated'])})


# --- Narayanganj City Corporation (ncc.gov.bd) ----------------------------------------------------------------
NC = 'https://ncc.gov.bd/pages/static-pages/'
NC_GLANCE = NC + '6922df58933eb65569e215a8'      # এক নজরে সিটি কর্পোরেশন
NC_WARDS = [(NC + '6922df18933eb65569e1fd00', 'সিদ্ধিরগঞ্জ অঞ্চল', 'Siddhirganj'), (NC + '6922ddb8933eb65569e15ff9', 'নারায়ণগঞ্জ অঞ্চল', 'Narayanganj'),
            (NC + '6922dc20933eb65569e0e861', 'কদমরসুল অঞ্চল', 'Kadam Rasul')]


def main_ncc():
    key, cc, cc_bn = CITY['key'], 'Narayanganj City Corporation', 'নারায়ণগঞ্জ সিটি কর্পোরেশন'
    glance = page(NC_GLANCE)
    expect(glance, '০৫ মে, ২০১১', '৭২.৪৩ বর্গ কি. মি.', '২৭টি', 'প্রায় ২০ লক্ষ', '৫,১৭,৩৫১')
    save_raw('ek_nojore_ncc.txt', glance, section(glance['text'], None, '৭। জনবল কাঠামো'))
    wards = {}
    for url, zbn, zen in NC_WARDS:
        pg = page(url)
        lines = []
        for rows in html_tables(content_html(url)):
            d = {}
            for c in rows:
                if len(c) >= 2:
                    d[c[0]] = c[1]
            if 'ওয়ার্ড নং' not in d:
                continue
            n = bn_int(d['ওয়ার্ড নং'])
            area = next((v for k, v in d.items() if k.startswith('আয়তন')), '')
            pop = next((v for k, v in d.items() if k.startswith('জনসংখ্যা')), '')
            wards[n] = dict(zone_bn=zbn, zone_en=zen, url=url, updated=pg['updated'], area=bn_num(area), pop=bn_num(pop),
                            places=d.get('এলাকা', ''), pop_label=next((k for k in d if k.startswith('জনসংখ্যা')), ''))
            lines.append('ওয়ার্ড %d | আয়তন %s | জনসংখ্যা %s | এলাকা: %s' % (n, area, pop, d.get('এলাকা', '')))
        save_raw('wards_%s.txt' % zen.lower().replace(' ', '_'), pg, '\n'.join(lines) + '\n(ward secretaries\' names and mobiles not copied)')
    if sorted(wards) != list(range(1, 28)):
        warn('NCC wards are not 1-27: %s' % sorted(wards))
    g_note = 'এক নজরে updated ' + glance['updated']
    areas = [dict(level='city_corporation', name_en=cc, name_bn=cc_bn, parent_level='district', parent_name_en='Narayanganj',
                  parent_name_bn='নারায়ণগঞ্জ', district_en='Narayanganj', website='https://ncc.gov.bd/', source_key=key, source_url=NC_GLANCE,
                  notes='Official portal ncc.gov.bd. ' + g_note)]
    areas += [dict(level='ward', name_en='Ward %d' % n, name_bn='ওয়ার্ড নং ' + ''.join(BN_DIGITS[int(c)] for c in str(n)),
                   parent_level='city_corporation', parent_name_en=cc, parent_name_bn=cc_bn, district_en='Narayanganj', code=str(n),
                   code_scheme='NCC_WARD_NO', source_key=key, source_url=w['url'],
                   notes='Ward number (name_bn is a label); NCC zone (অঞ্চল) %s (%s). Area and 2011 population in facts.csv. Page updated %s'
                         % (w['zone_en'], w['zone_bn'], w['updated'])) for n, w in sorted(wards.items())]
    write_csv('areas.csv', AREA_COLS, areas)
    f = cc_fact(key, cc, 'Narayanganj')
    facts = [
        f('wards_count', '27', 'wards', 'official', '', NC_GLANCE, 'ওয়ার্ড ২৭টি; 3 zones: Siddhirganj (1-9), Narayanganj (10-18), Kadam Rasul (19-27). ' + g_note),
        f('zones_count', '3', 'zones', 'official', '', NC_GLANCE, 'Holding table and ward pages: সিদ্ধিরগঞ্জ, নারায়ণগঞ্জ, কদমরসুল অঞ্চল. ' + g_note),
        f('established', '2011-05-05', 'date', 'official', '2011', NC_GLANCE, 'প্রতিষ্ঠাকাল ০৫ মে, ২০১১. ' + g_note),
        f('area_km2', '72.43', 'km2', 'official', '', NC_GLANCE, 'আয়তন ৭২.৪৩ বর্গ কি. মি. ' + g_note),
        f('population', '2000000', 'persons', 'estimate', '', NC_GLANCE, '"প্রায় ২০ লক্ষ" (about 2 million); year and basis not stated. ' + g_note),
        f('voters', '517351', 'persons', 'official', '2022', NC_GLANCE, 'NCC election 2022 schedule: male 2,59,846, female 2,57,511, hijra 4. ' + g_note),
        f('holdings', '60483', 'holdings', 'official', '', NC_GLANCE, 'Latest holding assessments (Siddhirganj and Kadam Rasul 2017-18, '
          'Narayanganj 2020-21): government 360, private 60,123. ' + g_note),
    ]
    for n, w in sorted(wards.items()):
        nm = 'Ward %d' % n
        if w['area']:
            facts.append(f('area_km2', w['area'], 'km2', 'approximate', '', w['url'], 'NCC ward page: "আয়তন (বর্গ কিলোমিটার প্রায়)"; '
                           'zone %s. Page updated %s' % (w['zone_en'], w['updated']), level='ward', name=nm))
        if w['pop']:
            facts.append(f('population', w['pop'], 'persons', 'census', '2011', w['url'], 'NCC ward page: "%s"; zone %s. Page updated %s'
                           % (w['pop_label'], w['zone_en'], w['updated']), level='ward', name=nm))
        if w['places']:
            facts.append(f('ward_areas', w['places'], 'text', 'listed', '', w['url'], 'Areas NCC lists for the ward (এলাকা); spellings as printed.',
                           level='ward', name=nm))
    write_csv('facts.csv', FACT_COLS, facts)
    write_city_manifest({'key': key, 'division': 'dhaka', 'kind': 'city_corporation', 'city': CITY['city'],
                         'name': 'Narayanganj City Corporation official portal (ncc.gov.bd)', 'organization': cc,
                         'source_type': 'government_portal', 'trust_level': 4, 'urls': ['https://ncc.gov.bd/', NC_GLANCE] + [u for u, _, _ in NC_WARDS],
                         'accessed': ACCESSED, 'publication_date': None, 'license': None, 'license_url': None,
                         'attribution': 'Narayanganj City Corporation (ncc.gov.bd), Bangladesh National Portal',
                         'notes': 'Key pages: এক নজরে সিটি কর্পোরেশন (updated %s) and the three zone ward pages (wards 1-9, 10-18, 19-27: '
                                  'areas, boundaries, approximate area, BBS 2011 population, holdings). Ward boundaries (চৌহদ্দি) are not '
                                  'copied; ward secretaries\' names and mobiles are not copied.' % glance['updated']})


# --- Gazipur City Corporation (gcc.gov.bd) --------------------------------------------------------------------
GC = 'https://gcc.gov.bd/pages/static-pages/'
GC_GLANCE = GC + '6922ddc3933eb65569e16266'      # এক নজরে গাজীপুর সিটি কর্পোরেশন (English table + zone table)
GC_HISTORY = GC + '6922db77933eb65569e0a43d'     # ইতিহাস
GC_WARDMAP = GC + 'location-and-area-imso6t-6af96b33ab933af2b0e1e94a'   # অঞ্চল ও ওয়ার্ডভিত্তিক সীমানা (PDF attachment)


def main_gcc():
    key, cc, cc_bn = CITY['key'], 'Gazipur City Corporation', 'গাজীপুর সিটি কর্পোরেশন'
    glance, hist, wmap = page(GC_GLANCE), page(GC_HISTORY), page(GC_WARDMAP)
    expect(glance, '16 January, 2013', 'Ward | 57', '76 (M-57, F-19)', '329.53 sq.km', 'Population | 4000000 | Approx.')
    expect(hist, '২০১৩ সালের ১৬ জানুয়ারি', 'টঙ্গি ও গাজীপুর পৌর এলাকা')
    zones = []
    for rows in html_tables(content_html(GC_GLANCE)):
        for c in rows:
            if len(c) >= 4 and re.fullmatch(r'[০-৯0-9]+', c[0]) and re.fullmatch(r'[০-৯0-9]+\s*-\s*[০-৯0-9]+', c[1]):
                a, b = (bn_int(x) for x in c[1].split('-'))
                zones.append((bn_int(c[0]), c[2], a, b, bn_num(c[3])))
    zone_of = {n: z for z in zones for n in range(z[2], z[3] + 1)}
    if sorted(zone_of) != list(range(1, 58)):
        warn('GCC zone table does not cover wards 1-57: %s' % sorted(zone_of))
    save_raw('ek_nojore_gcc.txt', glance, section(glance['text'], 'Establishment date', 'Educational Institution'))
    save_raw('zones.txt', glance, '\n'.join('zone %d | %s | wards %d-%d | %s km2' % z for z in zones))
    save_raw('history.txt', hist, sentences(hist['text'], '১৬ জানুয়ারি', 'টঙ্গি ও গাজীপুর'))
    save_raw('ward_boundaries_page.txt', wmap, 'Attachment (PDF; zone/ward boundaries, not transcribed):\n' +
             '\n'.join(a for a in wmap['attachments'] if a.endswith('.pdf')))
    g_note = 'এক নজরে updated ' + glance['updated']
    areas = [dict(level='city_corporation', name_en=cc, name_bn=cc_bn, parent_level='district', parent_name_en='Gazipur', parent_name_bn='গাজীপুর',
                  district_en='Gazipur', website='https://gcc.gov.bd/', source_key=key, source_url=GC_GLANCE,
                  notes='Official portal gcc.gov.bd. ' + g_note)]
    areas += ward_rows(cc, cc_bn, key, 'GCC_WARD_NO', GC_GLANCE, sorted(zone_of),
                       lambda n: 'Ward number (name_bn is a label); GCC zone (অঞ্চল) %d %s (zone table, wards %d-%d). No ward names are '
                                 'published. %s' % (zone_of[n][0], zone_of[n][1], zone_of[n][2], zone_of[n][3], g_note))
    write_csv('areas.csv', AREA_COLS, areas)
    f = cc_fact(key, cc, 'Gazipur')
    facts = [
        f('wards_count', '57', 'wards', 'official', '', GC_GLANCE, 'Ward 57; the zone table covers wards 1-57. ' + g_note),
        f('councillors', '76', 'councillors', 'official', '', GC_GLANCE, '76 (M-57, F-19): 57 general and 19 reserved-seat councillors. ' + g_note),
        f('zones_count', str(len(zones)), 'zones', 'official', '', GC_GLANCE, '; '.join('%d %s (wards %d-%d, %s km2)' % z for z in zones) + '. ' + g_note),
        f('established', '2013-01-16', 'date', 'official', '2013', GC_GLANCE, 'Gazette on 16 January 2013 as Gazipur City Corporation; formed from '
          'the Tongi and Gazipur pourashava areas (ইতিহাস). ' + g_note),
        f('area_km2', '329.53', 'km2', 'official', '', GC_GLANCE, '"329.53 sq.km"; the 8 zone areas add up to the same total. ' + g_note),
        f('population', '4000000', 'persons', 'estimate', '', GC_GLANCE, '"4000000 Approx."; year and basis not stated. ' + g_note),
    ] + [f('area_km2', z[4], 'km2', 'official', '', GC_GLANCE, 'GCC zone %d %s (wards %d-%d). %s' % (z[0], z[1], z[2], z[3], g_note),
           level='city_corporation_zone', name='Gazipur City Corporation zone %d (%s)' % (z[0], z[1])) for z in zones]
    write_csv('facts.csv', FACT_COLS, facts)
    write_city_manifest({'key': key, 'division': 'dhaka', 'kind': 'city_corporation', 'city': CITY['city'],
                         'name': 'Gazipur City Corporation official portal (gcc.gov.bd)', 'organization': cc,
                         'source_type': 'government_portal', 'trust_level': 4, 'urls': ['https://gcc.gov.bd/', GC_GLANCE, GC_HISTORY, GC_WARDMAP],
                         'accessed': ACCESSED, 'publication_date': None, 'license': None, 'license_url': None,
                         'attribution': 'Gazipur City Corporation (gcc.gov.bd), Bangladesh National Portal',
                         'notes': 'Key page: এক নজরে গাজীপুর সিটি কর্পোরেশন (updated %s; English facts table + zone table with ward ranges '
                                  'and areas). Ward/zone boundary PDF not transcribed. Counts of schools, markets etc. on the same page are '
                                  'marked "Approx." and are not copied.' % glance['updated']})


# --- Chattogram City Corporation (ccc.gov.bd) -----------------------------------------------------------------
CC_B = 'https://ccc.gov.bd/pages/static-pages/'
CC_GLANCE = CC_B + '6922dfce933eb65569e24111'     # এক নজরে চসিক
CC_HISTORY = CC_B + '6922dfee933eb65569e24b79'    # ইতিহাস
CC_WARDMAP = CC_B + '6922dfd7933eb65569e24436'    # ওয়ার্ডভিত্তিক মানচিত্র (ward numbers and names; maps as attachments)
CC_CONTACT = CC_B + '6922dbed933eb65569e0d780'    # যোগাযোগ (Nagar Bhaban address, office numbers, e-mail)


def main_ccc():
    key, cc, cc_bn = CITY['key'], 'Chattogram City Corporation', 'চট্টগ্রাম সিটি কর্পোরেশন'
    glance, hist, wmap, contact = page(CC_GLANCE), page(CC_HISTORY), page(CC_WARDMAP), page(CC_CONTACT)
    expect(glance, '২২ জুন ১৮৬৩', '৬ বর্গমাইল', '৫ টি', '৩১ জুলাই ১৯৯০', '৬০ বর্গমাইল', '৭০ লক্ষ (আনু.)', '৪১ টি', '০৬ টি', '২,১৮,৫৭৯ টি')
    expect(hist, '১৯৮২ খ্রিস্টাব্দের ১৬ই সেপ্টেম্বর কর্পোরেশনে পরিণত', '২৩-এ সেপ্টেম্বর’১৯৮২', '১৯৯০ খ্রিস্টাব্দের ৩১-এ জুলাই')
    names = {}
    for rows in html_tables(content_html(CC_WARDMAP)):
        for c in rows:
            m = re.match(r'^([০-৯0-9]+)\s*নং\s*(.+?)(?:\s*ওয়ার্ড)?$', c[0]) if c else None
            if m:
                names[bn_int(m.group(1))] = m.group(2).strip()
    if sorted(names) != list(range(1, 42)):
        warn('CCC ward list is not 1-41: %s' % sorted(names))
    save_raw('ek_nojore_ccc.txt', glance, section(glance['text'], 'প্রতিষ্ঠাকাল', 'এক নজরে প্রকৌশল বিভাগ') + '\n' +
             sentences(glance['text'], 'হোল্ডিং সংখ্যা'))
    save_raw('history.txt', hist, '\n'.join(l for l in sentences(hist['text'], '২২ জুন ১৮৬৩', '১৬ই সেপ্টেম্বর', '৩১-এ জুলাই',
                                                                   '২৩-এ সেপ্টেম্বর').split('\n')
                                            if not re.search(r'জনাব|মেয়র|প্রশাসক|চেয়ারম্যান|নিয়োগ', l)))   # no officials' names
    save_raw('ward_names.txt', wmap, '\n'.join('ওয়ার্ড %d | %s' % (n, names[n]) for n in sorted(names)) +
             '\n(ward map images are attachments, not copied)')
    save_raw('contact.txt', contact, redact_phones(contact['text']))
    g_note, w_note = 'এক নজরে updated ' + glance['updated'], 'ward map page updated ' + wmap['updated']
    ct = contact['text'].replace('\n', ' ')
    addr = re.search(r'নগর ভবন \(অস্থায়ী\)\s*বাটালী হিল, টাইগারপাস, চট্টগ্রাম', ct)
    areas = [dict(level='city_corporation', name_en=cc, name_bn=cc_bn, parent_level='district', parent_name_en='Chattogram',
                  parent_name_bn='চট্টগ্রাম', district_en='Chattogram', website='https://ccc.gov.bd/', source_key=key, source_url=CC_GLANCE,
                  notes='Official portal ccc.gov.bd (ccc.org.bd serves the same site). %s (যোগাযোগ; office numbers and info@ccc.gov.bd '
                        'on that page). %s' % (addr.group(0) if addr else 'Nagar Bhaban address not found', g_note))]
    areas += ward_rows(cc, cc_bn, key, 'CCC_WARD_NO', CC_WARDMAP, sorted(names),
                       lambda n: 'Ward number (name_bn is a label); CCC names the ward "%s" (ward map page; facts.csv ward_name). '
                                 'CCC has 41 wards and 6 zones (এক নজরে); no ward-to-zone list is published. %s' % (names[n], w_note))
    write_csv('areas.csv', AREA_COLS, areas)
    f = cc_fact(key, cc, 'Chattogram')
    facts = [
        f('wards_count', '41', 'wards', 'official', '', CC_GLANCE, 'ওয়ার্ড সংখ্যা ৪১ টি; the ward map page names wards 1-41. ' + g_note),
        f('zones_count', '6', 'zones', 'official', '', CC_GLANCE, 'অঞ্চল সংখ্যা ০৬ টি; zones not listed. ' + g_note),
        f('area_sq_mile', '60', 'sq mile', 'official', '', CC_GLANCE, 'বর্তমান আয়তন ৬০ বর্গমাইল (about 155 km2; the portal gives no km2 '
          'figure). The history page also says the area grew to 60 sq miles after 1990. ' + g_note),
        f('population', '7000000', 'persons', 'estimate', '', CC_GLANCE, 'বর্তমান জনসংখ্যা ৭০ লক্ষ (আনু.); year and basis not stated. ' + g_note),
        f('holdings', '218579', 'holdings', 'official', '', CC_GLANCE, 'হোল্ডিং সংখ্যা ২,১৮,৫৭৯ টি. ' + g_note),
        f('municipality_established', '1863-06-22', 'date', 'official', '1863', CC_GLANCE, 'প্রতিষ্ঠাকাল ২২ জুন ১৮৬৩ as চট্টগ্রাম মিউনিসিপ্যালিটি '
          '(6 sq miles, 5 wards); same date on the history page. ' + g_note),
        f('municipal_corporation', '1982-09', 'date', 'official', '1982', CC_HISTORY, 'Became চট্টগ্রাম মিউনিসিপ্যাল কর্পোরেশন in September '
          '1982: the history text says 16 Sep 1982 ("১৯৮২ খ্রিস্টাব্দের ১৬ই সেপ্টেম্বর"), its own table says 23 Sep 1982; day left out. '
          'History page updated %s.' % hist['updated']),
        f('city_corporation_established', '1990-07-31', 'date', 'official', '1990', CC_GLANCE, '"৩১ জুলাই ১৯৯০ তারিখে চট্টগ্রাম সিটি কর্পোরেশন '
          'নামকরণ করা হয়"; same date on the history page. ' + g_note),
    ] + [f('ward_name', names[n], 'text', 'listed', '', CC_WARDMAP, 'Ward name as on the CCC ward map page. ' + w_note,
           level='ward', name='Ward %d' % n) for n in sorted(names)]
    write_csv('facts.csv', FACT_COLS, facts)
    write_city_manifest({'key': key, 'division': 'chattogram', 'kind': 'city_corporation', 'city': CITY['city'],
                         'name': 'Chattogram City Corporation official portal (ccc.gov.bd)', 'organization': cc,
                         'source_type': 'government_portal', 'trust_level': 4, 'urls': ['https://ccc.gov.bd/', CC_GLANCE, CC_HISTORY, CC_WARDMAP, CC_CONTACT],
                         'accessed': ACCESSED, 'publication_date': None, 'license': None, 'license_url': None,
                         'attribution': 'Chattogram City Corporation (ccc.gov.bd), Bangladesh National Portal',
                         'notes': 'Key pages: এক নজরে চসিক (updated %s: 41 wards, 6 zones, 60 sq miles, population about 70 lakh, holdings), '
                                  'ইতিহাস, ওয়ার্ডভিত্তিক মানচিত্র (names of wards 1-41). CCC publishes no thana list and no ward-to-zone '
                                  'list. Ward officers\' and ward secretaries\' lists (names, mobiles) are not copied.' % glance['updated']})


# --- Cumilla City Corporation (cocc.portal.gov.bd) -----------------------------------------------------------
CO_B = 'https://cocc.portal.gov.bd/pages/'
CO_GLANCE = CO_B + 'files/6922db7d933eb65569e0a5f2'   # এক নজরে কুমিল্লা সিটি কর্পোরেশন: a scanned PDF attachment (images only)
# Values read from page 1 ("At a glance", General Information) of the scanned PDF; no text layer, so fetch.py checks the
# file's checksum and warns when the attachment changes.
CO_PDF_SHA256 = '54492ac73490008c7e27b0bd500efe80b8eedaf73fb538becd13774304422543'
CO_GLANCE_READ = [('Area', '53.04 Square K.M'), ('Ward', '27 Nos'), ('Population', '08 lac'), ('Holding', '52,600 Nos')]


def main_cocc():
    key, cc, cc_bn = CITY['key'], 'Cumilla City Corporation', 'কুমিল্লা সিটি কর্পোরেশন'
    glance = page(CO_GLANCE)
    pdfs = [a for a in glance['attachments'] if a.endswith('.pdf')]
    pdf_sha = hashlib.sha256(get(pdfs[0], binary=True)).hexdigest() if pdfs else ''
    if not pdfs or pdf_sha != CO_PDF_SHA256:
        warn('Cumilla CC glance PDF changed or missing (%s %s); re-read the values in CO_GLANCE_READ' % (pdfs[:1], pdf_sha))
    pdf = pdfs[0] if pdfs else ''
    save_raw('ek_nojore_cocc.txt', glance, 'Attachment (scanned PDF, 5 pages, "Cumilla City Corporation At a glance"): %s\nsha256: %s\n'
             'Read from page 1, General Information (not OCR; transcribed for this collection):\n%s' % (
                 pdf, pdf_sha, '\n'.join('%s | %s' % kv for kv in CO_GLANCE_READ)))
    g_note = 'Scanned PDF "At a glance" attached to the এক নজরে page (updated %s), page 1; values read from the image.' % glance['updated']
    areas = [dict(level='city_corporation', name_en=cc, name_bn=cc_bn, parent_level='district', parent_name_en='Cumilla',
                  parent_name_bn='কুমিল্লা', district_en='Cumilla', website='https://cocc.portal.gov.bd/', source_key=key, source_url=CO_GLANCE,
                  notes='Official portal cocc.portal.gov.bd (linked from the Cumilla DC portal; comillacity.gov.bd and cumillacity.gov.bd '
                        'do not resolve). ' + g_note)]
    areas += ward_rows(cc, cc_bn, key, 'COCC_WARD_NO', CO_GLANCE, range(1, 28),
                       lambda n: 'Ward number only (name_bn is a label): the glance PDF gives "Ward 27 Nos"; no ward names or list are '
                                 'published as text (the ward-secretary list is a PDF of names and mobiles, not used).')
    write_csv('areas.csv', AREA_COLS, areas)
    f = cc_fact(key, cc, 'Cumilla')
    facts = [
        f('wards_count', '27', 'wards', 'official', '', pdf or CO_GLANCE, '"Ward 27 Nos". ' + g_note),
        f('area_km2', '53.04', 'km2', 'official', '', pdf or CO_GLANCE, '"Area 53.04 Square K.M". ' + g_note),
        f('population', '800000', 'persons', 'estimate', '', pdf or CO_GLANCE, '"Population 08 lac" (about 800,000); year and basis not stated. ' + g_note),
        f('holdings', '52600', 'holdings', 'official', '', pdf or CO_GLANCE, '"Holding 52,600 Nos". ' + g_note),
    ]
    write_csv('facts.csv', FACT_COLS, facts)
    write_city_manifest({'key': key, 'division': 'chattogram', 'kind': 'city_corporation', 'city': CITY['city'],
                         'name': 'Cumilla City Corporation official portal (cocc.portal.gov.bd)', 'organization': cc,
                         'source_type': 'government_portal', 'trust_level': 4, 'urls': ['https://cocc.portal.gov.bd/', CO_GLANCE] + pdfs[:1],
                         'accessed': ACCESSED, 'publication_date': None, 'license': None, 'license_url': None,
                         'attribution': 'Cumilla City Corporation (cocc.portal.gov.bd), Bangladesh National Portal',
                         'notes': 'The portal\'s এক নজরে is a scanned 5-page PDF ("At a glance", 2024) without a text layer: ward count, '
                                  'area, population (approximate) and holdings were read from page 1; fetch.py checks the PDF checksum. '
                                  'No ward names, thana list or establishment date are published as text. Ward-secretary list (names, '
                                  'mobiles) not used.'})


# --- Khulna City Corporation ---------------------------------------------------------------------------------
# The divisional and DC portals link KCC as https://khulnacity.gov.bd, which did not resolve at access time (the .gov.bd registry
# delegates it to BTCL's parking name servers; SERVFAIL); www.khulnacity.org answers HTTP 403 ('Missing Authentication Token') to
# every request. Neither is worked around. KCC figures therefore come only from other official portals that state them.
KC_SITES = ['https://khulnacity.gov.bd/', 'https://www.khulnacity.org/']
KC_KMP_GLANCE = 'https://police.khulnadiv.gov.bd/pages/static-pages/6980f684a31054345f1ceb6e'   # KMP এক নজরে ('৩১টি সিটি কর্পোরেশন ওয়ার্ড')
KC_DC_HISTORY = 'https://khulna.gov.bd/pages/static-pages/6981018ba31054345f1d497d'            # DC portal 'জেলার পটভূমি' (timeline)
KC_DIV_MENU = 'https://khulnadiv.gov.bd/'                                                       # 'স্থানীয় সরকার > সিটি কর্পোরেশন' link


def main_kcc():
    key, cc, cc_bn = CITY['key'], 'Khulna City Corporation', 'খুলনা সিটি কর্পোরেশন'
    reach = []
    for u in KC_SITES:
        try:
            reach.append('%s -> HTTP %s' % (u, status(u)))
        except requests.RequestException as e:
            reach.append('%s -> %s' % (u, type(e).__name__))
    kmp = page(KC_KMP_GLANCE)
    hist = page(KC_DC_HISTORY)
    gl, ht = kmp['text'].replace('\n', ' '), hist['text']
    expect(kmp, '৩১টি সিটি কর্পোরেশন ওয়ার্ড এর অন্তর্ভূক্ত')
    expect(hist, '১৮৮৪ - খুলনা পৌরসভা প্রতিষ্ঠা', '৯টি উপজেলা ও একটি সিটি কর্পোরেশন')
    save_raw('kmp_glance_wards.txt', kmp, sentences(gl, 'সিটি কর্পোরেশন ওয়ার্ড'))
    save_raw('dc_history_timeline.txt', hist, '\n'.join(l for l in ht.split('\n') if re.search(r'পৌরসভা|সিটি কর্পোরেশন', l)))
    save_raw('kcc_site_reachability.txt', {'url': ', '.join(KC_SITES), 'title': 'KCC official site (not reachable)', 'updated': '',
                                           'updated_raw': ''}, '\n'.join(reach))
    k_note, h_note = 'KMP portal এক নজরে updated ' + kmp['updated'], 'DC portal জেলার পটভূমি updated ' + hist['updated']
    areas = [dict(level='city_corporation', name_en=cc, name_bn=cc_bn, parent_level='district', parent_name_en='Khulna',
                  parent_name_bn='খুলনা', district_en='Khulna', website='', source_key=key, source_url=KC_DC_HISTORY,
                  notes='The Khulna DC portal: "বর্তমানে ৯টি উপজেলা ও একটি সিটি কর্পোরেশন নিয়ে গঠিত খুলনা জেলা". KCC\'s own site could not be '
                        'read: %s (the divisional and DC portals link khulnacity.gov.bd). %s' % ('; '.join(reach), h_note))]
    areas += ward_rows(cc, cc_bn, key, 'KCC_WARD_NO', KC_KMP_GLANCE, range(1, 32),
                       lambda n: 'Ward number only (name_bn is a label), from the ward count: KMP\'s area includes "৩১টি সিটি কর্পোরেশন '
                                 'ওয়ার্ড" (%s). KCC\'s own ward list could not be read (site unreachable); BBS 2022 (BBS_CENSUS_2022_KHULNA) '
                                 'also gives KCC 31 wards.' % k_note)
    write_csv('areas.csv', AREA_COLS, areas)
    f = cc_fact(key, cc, 'Khulna')
    facts = [
        f('wards_count', '31', 'wards', 'official', '', KC_KMP_GLANCE, '"৩১টি সিটি কর্পোরেশন ওয়ার্ড এর অন্তর্ভূক্ত" — all KCC wards lie in '
          'KMP\'s area (KMP portal; KCC\'s own site unreachable). BBS 2022 (BBS_CENSUS_2022_KHULNA) also gives 31 wards. ' + k_note),
        f('municipality_established', '1884', 'year', 'official', '1884', KC_DC_HISTORY, '"১৮৮৪ - খুলনা পৌরসভা প্রতিষ্ঠা" (DC portal timeline). '
          + h_note),
    ]
    write_csv('facts.csv', FACT_COLS, facts)
    write_city_manifest({'key': key, 'division': 'khulna', 'kind': 'city_corporation', 'city': CITY['city'],
                         'name': 'Khulna City Corporation — figures stated on official portals (KCC\'s own site unreachable)', 'organization': cc,
                         'source_type': 'government_portal', 'trust_level': 4, 'urls': KC_SITES + [KC_KMP_GLANCE, KC_DC_HISTORY, KC_DIV_MENU],
                         'accessed': ACCESSED, 'publication_date': None, 'license': None, 'license_url': None,
                         'attribution': 'Khulna Metropolitan Police (police.khulnadiv.gov.bd); Deputy Commissioner\'s Office, Khulna (khulna.gov.bd)',
                         'notes': 'KCC\'s official site could not be read: %s. Only the ward count (31, KMP portal এক নজরে) and the '
                                  'municipality\'s founding year (1884, Khulna DC portal timeline) are published on reachable official '
                                  'pages; no area, population, zones, ward names or thana list. Census figures for KCC are in '
                                  'BBS_CENSUS_2022_KHULNA (population 719,557, 2022, enumerated).' % '; '.join(reach)})


# --- Barishal City Corporation (barishalcity.gov.bd) ------------------------------------------------------------
# BCC's own site (linked from the Barishal DC portal; title 'বরিশাল সিটি কর্পোরেশন | গণপ্রজাতন্ত্রী বাংলাদেশ সরকার') is not on the
# national-portal framework: pages are /info/<slug> with an 'article_container' and a 'প্রকাশ: <date>' line. bcc.gov.bd is the
# Bangladesh Computer Council, not the city corporation. The ward-wise location page is a single image (no ward list as text).
BC_B = 'https://barishalcity.gov.bd/info/'
BC_GLANCE = BC_B + 'এক-নজরে-বরিশাল-সিটি'          # এক নজরে বরিশাল সিটি (wards, area, population, thanas, mahallas, census table)
BC_HISTORY = BC_B + 'ইতিহাস'                       # ইতিহাস (same text block as এক নজরে)
BC_WARDLOC = BC_B + 'লোকেশন-ওয়ার্ড-ভিত্তিক'          # লোকেশন (ওয়ার্ড ভিত্তিক): one JPG, no text
BC_CONTACT = BC_B + 'যোগাযোগ'                      # যোগাযোগ (Nagar Bhaban address, phone, e-mail)
BC_BMP_THANAS = [  # BMP thana pages: which BCC wards each thana's 'প্রশাসন' line lists (BBS 2001 census table on those pages)
    ('https://bmp.police.gov.bd/thana/7/kotwali-model-thana', 'কোতোয়ালী মডেল থানা', 'Kotwali'),
    ('https://bmp.police.gov.bd/thana/9/Kaunia-thana', 'কাউনিয়া থানা', 'Kaunia'),
    ('https://bmp.police.gov.bd/thana/8/airport-thana', 'এয়ারপোর্ট থানা', 'Airport'),
    ('https://bmp.police.gov.bd/thana/10/bandar-thana', 'বন্দর থানা', 'Bandar'),
]


def bcc_page(url):
    """barishalcity.gov.bd /info/ page -> same dict as page(): title, publication date, article text."""
    t = get(url)
    i = t.find('<div class="article_container">')
    if i < 0:
        raise RuntimeError('no article_container in ' + url)
    seg = t[i:]
    j = seg.find('<div class="right_content">')
    seg = seg[:j] if j > 0 else seg
    m = re.search(r'<h1>(.*?)</h1>', seg, re.S)
    title = to_text(m.group(1)) if m else ''
    m = re.search(r'প্রকাশ:\s*([^<]+)</p>', nfc(seg))
    upd = m.group(1).strip() if m else ''
    m2 = re.match(r'(\S+) (\S+), (\S+)$', upd)
    iso = '%s-%02d-%02d' % (asc(m2.group(3)), BN_MONTHS.get(m2.group(2), 0), int(asc(m2.group(1)))) if m2 else ''
    body = seg[seg.find('article_body'):] if 'article_body' in seg else seg
    imgs = sorted(set(re.findall(r'(https?://barishalcity\.gov\.bd/storage/images/[^"\' ]+\.(?:jpe?g|png|pdf))', body)))
    return {'url': url, 'title': title, 'updated_raw': upd, 'updated': iso, 'html': seg, 'text': to_text(body.split('>', 1)[1] if '>' in body else body),
            'attachments': [x for x in imgs if not x.endswith(('chief.png', 'ceo.png', 'official-logo.png'))]}


def bmp_thana_wards(url):
    """BMP thana page -> (ward numbers of the 'ওয়ার্ড নং N' rows, the 'প্রশাসন' sentence)."""
    t = to_text(re.sub(r'<script.*?</script>|<style.*?</style>', '', get(url), flags=re.S))
    wards = sorted({bn_int(x) for x in re.findall(r'ওয়ার্ড\s*নং\s*([০-৯0-9]+)', t)})
    m = re.search(r'প্রশাসন\s*:?\s*(.+?।)', t.replace('\n', ' '))
    return wards, (re.sub(r'\s+', ' ', m.group(1)).strip() if m else '')


def main_bcc():
    key, cc, cc_bn = CITY['key'], 'Barishal City Corporation', 'বরিশাল সিটি কর্পোরেশন'
    glance, hist, wloc, contact = bcc_page(BC_GLANCE), bcc_page(BC_HISTORY), bcc_page(BC_WARDLOC), bcc_page(BC_CONTACT)
    gl = glance['text'].replace('\n', ' ')
    needles = ('১৮৬৯ সালে বরিশাল টাউন কমিটি', '১৮৭৬ সালে বরিশাল মিউনিসিপ্যালিটিতে', '১৯৮৫ সালে একে একটি প্রথম শ্রেনীর পৌরসভা',
               '২০০২ সালে', 'জনসংখ্যা প্রায় ৫ লক্ষ ও আয়তন ৫৮ বর্গ কিলোমিটার', '৩০টি ওয়ার্ড নিয়ে গঠিত',
               '৩টি থানা, ৩০টি ওয়ার্ড ও ২২৫টি মহল্লা', 'মোট জনসংখ্যা ৩,২৮,২৭৮ জন', 'পুরুষ ১,৬৯,৪৭৫ জন এবং মহিলা ১,৫৮,৮০৩ জন',
               'মোট পরিবার ৭২,৭০৯টি', '১০ জন সংরক্ষিত আসনে')
    for n in needles:
        if n not in gl:
            warn('expected text not found on %s: %r' % (BC_GLANCE, n))
    census = []
    for rows in html_tables(glance['html']):
        if rows and rows[0][:2] == ['সাল', 'জনসংখ্যা']:
            census = [(bn_int(r[0]), bn_int(r[1])) for r in rows[1:] if len(r) >= 2 and r[0]]
    ct = contact['text'].replace('\n', ' ')
    phone = re.search(r'\+?[৮8][৮8][০0]-([০-৯0-9]{4})-([০-৯0-9]{6})', ct)
    mail = re.search(r'[\w.]+@barishalcity\.gov\.bd', ct)
    addr = re.search(r'বরিশাল সিটি কর্পোরেশন,\s*ফজলুল হক এভিনিউ, বরিশাল', ct)
    thana_wards, thana_admin = {}, {}
    for u, bn, en in BC_BMP_THANAS:
        try:
            thana_wards[en], thana_admin[en] = bmp_thana_wards(u)
        except Exception as e:
            warn('BMP thana page not read: %s (%s)' % (u, type(e).__name__))
    ward_thana = {w: en for en, ws in thana_wards.items() for w in ws}
    keep = ('১৮৬৯', '১৮৭৬', '১৯৮৫', '২০০২', 'জনসংখ্যা প্রায়', '৩০টি ওয়ার্ড', '২২৫টি মহল্লা', 'আয়তন ৫৮', 'আদমশুমারি অনুযায়ী', '২৫ জুলাই',
            'পুরুষ ১,৬৯,৪৭৫', 'উপর্যুক্ত ছকে')
    save_raw('ek_nojore_bcc.txt', glance, '\n'.join(l for l in sentences(gl, *keep).split('\n')
                                                  if not re.search(r'চেয়ারম্যান|সভাপতি|জনাব|মেয়র \(', l)) +   # no officials' names
             '\n\nজনসংখ্যার পরিসংখ্যান (table):\n' + '\n'.join('%d | %d' % c for c in census))
    save_raw('contact.txt', contact, '%s\nPhone: %s\nE-mail: %s' % (addr.group(0) if addr else '-', asc(phone.group(0)) if phone else '-',
                                                                  mail.group(0) if mail else '-'))
    save_raw('ward_location_page.txt', wloc, 'The page shows one image (no ward list as text): %s' % (', '.join(wloc['attachments']) or '-'))
    save_raw('bmp_thana_wards.txt', {'url': ', '.join(u for u, _, _ in BC_BMP_THANAS), 'title': 'BMP thana pages (প্রশাসন lines)',
                                     'updated': '', 'updated_raw': ''},
             '\n'.join('%s | wards %s | %s' % (en, ', '.join(map(str, thana_wards.get(en, []))) or '-', thana_admin.get(en, '-'))
                       for _, _, en in BC_BMP_THANAS))
    g_note = 'BCC এক নজরে (published %s).' % glance['updated']
    ph = '0' + asc(phone.group(1) + phone.group(2)) if phone else ''
    areas = [dict(level='city_corporation', name_en=cc, name_bn=cc_bn, parent_level='district', parent_name_en='Barishal',
                  parent_name_bn='বরিশাল', district_en='Barishal', website='https://barishalcity.gov.bd/', source_key=key, source_url=BC_GLANCE,
                  notes='Official site barishalcity.gov.bd (linked from the Barishal DC portal; bcc.gov.bd is the Bangladesh Computer Council). '
                        'Nagar Bhaban: %s; phone %s, %s (যোগাযোগ, published %s). %s' % (
                            addr.group(0) if addr else 'address not found', ph or '-', mail.group(0) if mail else '-', contact['updated'], g_note))]
    areas += ward_rows(cc, cc_bn, key, 'BCC_WARD_NO', BC_GLANCE, range(1, 31),
                       lambda n: 'Ward number only (name_bn is a label), from BCC\'s ward count ("৩০টি ওয়ার্ড"); the ward-wise location page '
                                 'is an image without text. %s' % (
                                     'BMP\'s %s thana page lists ward %d in its BBS 2001 table (thana not set: the thana also covers '
                                     'unions outside BCC).' % (ward_thana[n], n) if n in ward_thana else 'No BMP thana page lists this ward.'))
    write_csv('areas.csv', AREA_COLS, areas)
    f = cc_fact(key, cc, 'Barishal')
    facts = [
        f('wards_count', '30', 'wards', 'official', '', BC_GLANCE, '"বর্তমানে ৩০টি ওয়ার্ড নিয়ে গঠিত" (30 general and 10 reserved-seat '
          'councillors). ' + g_note),
        f('area_km2', '58', 'km2', 'official', '', BC_GLANCE, '"আয়তন ৫৮ বর্গ কিলোমিটার"; no year. ' + g_note),
        f('population', '500000', 'persons', 'estimate', '', BC_GLANCE, '"জনসংখ্যা প্রায় ৫ লক্ষ" (about 5 lakh, "বর্তমানে"); year and basis '
          'not stated. ' + g_note),
        f('population', '328278', 'persons', 'enumerated', '2011', BC_GLANCE, '"২০১১ সালের আদমশুমারি অনুযায়ী ... মোট জনসংখ্যা ৩,২৮,২৭৮ জন" '
          '(male 169,475, female 158,803), as quoted by BCC from the 2011 census. ' + g_note),
        f('population_male', '169475', 'persons', 'enumerated', '2011', BC_GLANCE, '2011 census as quoted by BCC. ' + g_note),
        f('population_female', '158803', 'persons', 'enumerated', '2011', BC_GLANCE, '2011 census as quoted by BCC. ' + g_note),
        f('households', '72709', 'households', 'enumerated', '2011', BC_GLANCE, '"মোট পরিবার ৭২,৭০৯টি" (2011 census as quoted by BCC). ' + g_note),
        f('mahallas_count', '225', 'mahallas', 'official', '', BC_GLANCE, '"৩টি থানা, ৩০টি ওয়ার্ড ও ২২৫টি মহল্লা নিয়ে গঠিত". ' + g_note),
        f('thanas_count', '3', 'thanas', 'official', '', BC_GLANCE, '"বরিশাল সিটি কর্পোরেশন ৩টি থানা ... নিয়ে গঠিত"; the thanas are not '
          'named. BMP has 4 thanas; its Kotwali, Kaunia and Airport pages list BCC wards 6, 8-26 / 1-5, 7 / 27-30 together with '
          'rural unions, its Bandar page lists unions only. ' + g_note),
        f('town_committee_established', '1869', 'year', 'official', '1869', BC_GLANCE, '"১৮৬৯ সালে বরিশাল টাউন কমিটি হিসেবে প্রতিষ্ঠিত". ' + g_note),
        f('municipality_established', '1876', 'year', 'official', '1876', BC_GLANCE, '"১৮৭৬ সালে বরিশাল মিউনিসিপ্যালিটিতে উন্নীত". ' + g_note),
        f('city_corporation_established', '2002-07-25' if '২৫ জুলাই ২০০২' in gl else '2002', 'date' if '২৫ জুলাই ২০০২' in gl else 'year',
          'official', '2002', BC_GLANCE, '"২০০২ সালে “বরিশাল সিটি কর্পোরেশন (সংশোধন) আইন ২০০২” এর মাধ্যমে পৌরসভা বরিশাল সিটি কর্পোরেশনে উন্নীত"; '
          'the history section: "২৫ জুলাই ২০০২ সালে আনুষ্ঠানিকভাবে বরিশাল সিটি কর্পোরেশনে উন্নীত হয়" (after the বরিশাল সিটি কর্পোরেশন আইন, '
          '২০০১). ' + g_note),
        f('first_class_pourashava', '1985', 'year', 'official', '1985', BC_GLANCE, '"১৯৮৫ সালে একে একটি প্রথম শ্রেনীর পৌরসভা হিসেবে ঘোষণা করা হয়". '
          + g_note),
        f('literacy_rate', '75.3', 'percent', 'enumerated', '2011', BC_GLANCE, '"২০১১ সালের আদমশুমারি অনুযায়ী বরিশাল সিটি কর্পোরেশনের সাক্ষরতার '
          'হার ৭৫.৩%" (as quoted by BCC). ' + g_note) if 'সাক্ষরতার হার ৭৫.৩%' in gl else None,
    ] + [f('population', str(p), 'persons', 'enumerated', str(y), BC_GLANCE, 'BCC population table ("জনসংখ্যার পরিসংখ্যান"; '
           '"শুধুমাত্র বরিশাল সিটিকর্পোরেশন আওতাধীন এলাকার জনসংখ্যা"; source column empty). ' + g_note)
         for y, p in census if y != 2011]
    facts = [x for x in facts if x]
    write_csv('facts.csv', FACT_COLS, facts)
    write_city_manifest({'key': key, 'division': 'barishal', 'kind': 'city_corporation', 'city': CITY['city'],
                         'name': 'Barishal City Corporation official site (barishalcity.gov.bd)', 'organization': cc,
                         'source_type': 'government_portal', 'trust_level': 4,
                         'urls': ['https://barishalcity.gov.bd/', BC_GLANCE, BC_HISTORY, BC_WARDLOC, BC_CONTACT] + [u for u, _, _ in BC_BMP_THANAS],
                         'accessed': ACCESSED, 'publication_date': glance['updated'] or None, 'license': None, 'license_url': None,
                         'attribution': 'Barishal City Corporation (barishalcity.gov.bd); Barishal Metropolitan Police (bmp.police.gov.bd)',
                         'notes': 'Key page: এক নজরে বরিশাল সিটি (published %s): 30 wards, 58 km2, population about 5 lakh (no year), 2011 '
                                  'census 328,278, 3 thanas (not named), 225 mahallas, town committee 1869, municipality 1876, city '
                                  'corporation 2002; a population table 1872-2011. The ward-wise location page is an image only, so wards '
                                  'are numbers 1-30 from the ward count; BMP thana pages list which wards each BMP thana covers (noted per '
                                  'ward). Officials\' names (administrator, CEO, past chairmen and mayors) are not copied.' % glance['updated']})


# --- Sylhet City Corporation (scc.gov.bd, national-portal framework; title 'হোম | সিলেট সিটি কর্পোরেশন') -------------------
# Linked as 'সিলেট সিটি কর্পোরেশন' from the Sylhet DC portal's local-government menu; sylhetcity.gov.bd does not respond.
SC_B = 'https://scc.gov.bd/pages/static-pages/'
SC_GLANCE = SC_B + '6922df09933eb65569e1f5f4'      # আমাদের নগরী - এক নজরে সিসিক (established, area, wards, councillors, population)
SC_WARDSEC = SC_B + '6922e132933eb65569e2acec'     # ওয়ার্ড সচিব ('সাধারণ-০১' … 'সাধারণ-৪২'; secretaries' names and mobiles not used)
SC_CONTACT = SC_B + '6922db7b933eb65569e0a54f'     # যোগাযোগ (Nagar Bhaban; office telephones; e-mails are script-obfuscated)
SC_DC_GLANCE = 'https://sylhet.gov.bd/pages/static-pages/696cb362c4774958d7ba0691'     # DC portal 'এক নজরে সিলেট জেলা' (ওয়ার্ড ৪২ টি)
SC_SP_GLANCE = 'https://police.sylhet.gov.bd/pages/static-pages/696cafe6c4774958d7b9fb06'   # SP portal 'একনজরে' (ওয়ার্ড ২৭ টি)
SC_SMP_GLANCE = 'https://police.sylhetdiv.gov.bd/pages/static-pages/696ca219c4774958d7b931b6'  # SMP 'এক নজরে' (27 wards in SMP area)
# sylhet.gov.bd sends only its leaf certificate (Let's Encrypt YR1): the CA-published intermediates (AIA 'CA Issuers' URLs: YR1, and
# Root YR cross-signed by ISRG Root X1) are added for this city; TLS verification stays on.
SC_INTERMEDIATES = ['http://yr1.i.lencr.org/', 'http://yr.i.lencr.org/']


def main_scc():
    AIA_INTERMEDIATES.extend(u for u in SC_INTERMEDIATES if u not in AIA_INTERMEDIATES)   # before the first request
    key, cc, cc_bn = CITY['key'], 'Sylhet City Corporation', 'সিলেট সিটি কর্পোরেশন'
    glance, wsec, contact = page(SC_GLANCE), page(SC_WARDSEC), page(SC_CONTACT)
    gl_html = content_html(SC_GLANCE)
    rows = {r[0]: r[1] for t in html_tables(gl_html) for r in t if len(r) >= 2}
    def cell(label):
        v = next((v for k, v in rows.items() if label in k), '')
        if not v:
            warn('row %r not found on %s' % (label, SC_GLANCE))
        return v
    est, area, wards, gen, res, pop = (cell('স্থাপিত'), cell('আয়তন'), cell('ওয়ার্ড সংখ্যা'), cell('সাধারণ ওয়ার্ড'), cell('সংরক্ষিত ওয়ার্ড'),
                                        cell('জনসংখ্যা'))
    m = re.match(r'^([০-৯0-9]+)\s+(\S+)\s+([০-৯0-9]{4})$', est)
    est_iso = '%s-%02d-%02d' % (asc(m.group(3)), BN_MONTHS.get(m.group(2), 0), int(asc(m.group(1)))) if m and BN_MONTHS.get(m.group(2)) else ''
    area_v = re.match(r'^([০-৯0-9.]+)\s*বর্গ কিমি$', area)
    n_wards = bn_int(wards) if re.match(r'^[০-৯0-9]+$', wards) else 0
    pm = re.match(r'^([০-৯0-9]+)\s*\(\s*লাখ আনুমানিক\)$', pop)
    # ward numbers as listed on the ward-secretary page ('সাধারণ-NN'); names and mobile numbers on that page are not used
    listed = sorted({bn_int(x) for x in re.findall(r'সাধারণ-([০-৯0-9]+)', wsec['text'])})
    if n_wards and listed != list(range(1, n_wards + 1)):
        warn('ward-secretary page lists wards %s, the glance page says %d wards' % (listed, n_wards))
    ct = contact['text'].replace('\n', ' ')
    addr = 'নগর ভবন, সিলেট' if 'নগর ভবন, সিলেট' in ct else ''
    phones = []
    for x in re.findall(r'\+?[৮8][৮8][০0][-\s]?[০-৯0-9]{3,4}[-\s]?[০-৯0-9]{6,7}', ct):
        d = re.sub(r'\D', '', asc(x))
        d = '0' + d[3:] if d.startswith('880') else d
        if re.match(r'^0[2-9]\d{8,9}$', d):   # landlines only (01… mobiles are not copied)
            phones.append(d)
    phones = list(dict.fromkeys(phones))
    dc = page(SC_DC_GLANCE)
    dcm = re.search(r'সিটি কর্পোরেশন\s*\|?\s*([০-৯0-9]+ টি \(ওয়ার্ড [০-৯0-9]+ টি\))', dc['text'].replace('\n', ' '))
    sp = page(SC_SP_GLANCE)
    spm = re.search(r'সিটি কর্পোরেশন\s*\|?\s*:?\s*\|?\s*([০-৯0-9]+ টি \(ওয়ার্ড [০-৯0-9]+ টি\))', sp['text'].replace('\n', ' '))
    smp = page(SC_SMP_GLANCE)
    smpm = re.search(r'(The total area of SMP is about [0-9.]+ Sq\.km including [0-9]+ wards of Sylhet City Corporation[^.]*\.)',
                     re.sub(r'\s+', ' ', smp['text']))
    keep_rows = ('স্থাপিত', 'আয়তন', 'ওয়ার্ড সংখ্যা', 'সাধারণ ওয়ার্ড', 'সংরক্ষিত ওয়ার্ড', 'জনসংখ্যা', 'অনুমোদিত পদ')   # not the officials' rows
    save_raw('ek_nojore_scc.txt', glance, '\n'.join('%s | %s' % (k, v) for k, v in rows.items() if any(x in k for x in keep_rows)))
    save_raw('ward_numbers.txt', wsec, 'Ward numbers listed (secretaries\' names and mobile numbers not kept): %s' % ', '.join(map(str, listed)))
    save_raw('contact.txt', contact, 'Address: %s\nOffice telephones (landlines as printed, normalised): %s\n(E-mail addresses on this page are '
             'obfuscated by a script and are not collected; officials\' names and mobiles not kept.)' % (addr or '-', ', '.join(phones) or '-'))
    save_raw('ward_count_other_portals.txt', {'url': '%s ; %s ; %s' % (SC_DC_GLANCE, SC_SP_GLANCE, SC_SMP_GLANCE), 'title': 'Ward counts on '
             'other official portals', 'updated': '', 'updated_raw': ''},
             'DC portal (updated %s): সিটি কর্পোরেশন %s\nSP portal (updated %s): সিটি কর্পোরেশন %s\nSMP portal (updated %s): %s' % (
                 dc['updated'] or '?', dcm.group(1) if dcm else '-', sp['updated'] or '?', spm.group(1) if spm else '-',
                 smp['updated'] or '?', smpm.group(1) if smpm else '-'))
    g_note = 'SCC এক নজরে (page updated %s).' % (glance['updated'] or '?')
    areas = [dict(level='city_corporation', name_en=cc, name_bn=cc_bn, parent_level='district', parent_name_en='Sylhet',
                  parent_name_bn='সিলেট', district_en='Sylhet', website='https://scc.gov.bd/', source_key=key, source_url=SC_GLANCE,
                  notes='Official site scc.gov.bd (national-portal framework, linked from the Sylhet DC portal). Nagar Bhaban: %s; office '
                        'telephones %s (যোগাযোগ, updated %s; e-mails there are script-obfuscated and not collected). %s' % (
                            addr or 'address not found', ', '.join(phones) or '-', contact['updated'] or '?', g_note))]
    areas += ward_rows(cc, cc_bn, key, 'SCC_WARD_NO', SC_WARDSEC, listed,
                       lambda n: 'Ward number only (name_bn is a label), as listed on SCC\'s ward-secretary page ("সাধারণ-%s"); SCC '
                                 'publishes no ward names. No official source found that assigns this ward to an SMP thana.' % ''.join(
                                     BN_DIGITS[int(c)] for c in '%02d' % n))
    write_csv('areas.csv', AREA_COLS, areas)
    f = cc_fact(key, cc, 'Sylhet')
    facts = [
        f('city_corporation_established', est_iso or asc(est), 'date' if est_iso else 'text', 'official', est_iso[:4], SC_GLANCE,
          '"স্থাপিত: %s". %s' % (est, g_note)) if est else None,
        f('area_km2', asc(area_v.group(1)), 'km2', 'official', '', SC_GLANCE, '"আয়তন: %s"; no year. %s' % (area, g_note)) if area_v else None,
        f('wards_count', str(n_wards), 'wards', 'official', '', SC_GLANCE,
          '"ওয়ার্ড সংখ্যা: %s"; %s general and %s reserved-seat councillors; the ward-secretary page lists wards %d-%d. The DC portal '
          '\'এক নজরে সিলেট জেলা\' gives "%s"; the SP portal\'s \'একনজরে\' still gives "%s" and SMP\'s \'এক নজরে\' (2011 jurisdiction) '
          'speaks of 27 wards (older counts; the SCC and DC pages are the more recently updated). %s' % (
              wards, asc(gen), asc(res), listed[0] if listed else 0, listed[-1] if listed else 0, dcm.group(1) if dcm else '-',
              spm.group(1) if spm else '-', g_note)) if n_wards else None,
        f('councillors_general', asc(gen), 'councillors', 'official', '', SC_GLANCE, '"ওয়ার্ড কাউন্সিলর (সাধারণ ওয়ার্ড): %s". %s' % (gen, g_note)) if gen else None,
        f('councillors_reserved', asc(res), 'councillors', 'official', '', SC_GLANCE, '"ওয়ার্ড কাউন্সিলর (সংরক্ষিত ওয়ার্ড): %s". %s' % (res, g_note)) if res else None,
        f('population', str(bn_int(pm.group(1)) * 100000), 'persons', 'estimate', '', SC_GLANCE,
          '"জনসংখ্যা: %s" (about %s lakh, estimate); year and basis not stated. %s' % (pop, asc(pm.group(1)), g_note)) if pm else None,
    ]
    write_csv('facts.csv', FACT_COLS, [x for x in facts if x])
    write_city_manifest({'key': key, 'division': 'sylhet', 'kind': 'city_corporation', 'city': CITY['city'],
                         'name': 'Sylhet City Corporation official site (scc.gov.bd)', 'organization': cc,
                         'source_type': 'government_portal', 'trust_level': 4,
                         'urls': ['https://scc.gov.bd/', SC_GLANCE, SC_WARDSEC, SC_CONTACT, SC_DC_GLANCE, SC_SP_GLANCE, SC_SMP_GLANCE],
                         'accessed': ACCESSED, 'publication_date': (glance['updated'] or '')[:10] or None, 'license': None, 'license_url': None,
                         'attribution': 'Sylhet City Corporation (scc.gov.bd); Sylhet DC portal (sylhet.gov.bd)',
                         'notes': 'Key page: SCC এক নজরে (updated %s): established %s, %s, %s wards (%s general / %s reserved-seat councillors), '
                                  'population %s (estimate, no year). Ward numbers 1-%d from the ward-secretary page (names and mobiles '
                                  'there are not used). The DC portal also gives 42 wards; the SP portal (27, page updated 2023) and SMP (27, '
                                  'its 2011 jurisdiction, page updated 2022) give an older count. scc.gov.bd publishes no ward names, ward map text or '
                                  'ward-to-thana assignment. Officials\' names are not copied.' % (
                                      glance['updated'] or '?', est or '?', area or '?', wards or '?', gen or '?', res or '?', pop or '?',
                                      listed[-1] if listed else 0)})


# --- Mymensingh City Corporation (mcc.gov.bd, national-portal framework; title 'হোম | ময়মনসিংহ সিটি কর্পোরেশন') -----------------
# Linked as 'সিটি কর্পোরেশন' (https://mcc.gov.bd/) from the divisional portal's local-government menu, and as www.mcc.gov.bd from its
# office menu (www.mcc.gov.bd serves a self-signed certificate; not used). Its 'এক নজরে' page and its councillor list are scanned
# PDF attachments (no text layer). The few figures used from them were read from the scans and are hard-coded below with the
# attachment URL they come from; the run warns if a page links a different attachment. Officials' names and mobiles are not copied.
MC_B = 'https://mcc.gov.bd/pages/static-pages/'
MC_GLANCE = MC_B + '6922defd933eb65569e1efb9'       # এক নজরে ময়মনসিংহ সিটি কর্পোরেশন (scanned one-page PDF, Dec 2024)
MC_GLANCE_PDF = ('https://objectstorage.ap-dcc-gazipur-1.oraclecloud15.com/n/axvjbnqprylg/b/V2Ministry/o/office-mcc/2024/12/'
                 '43ff3cda7d0a4cbab3207cdf48f3dd97.pdf')
MC_LOCATION = MC_B + '6922dd18933eb65569e137e2'     # লোকেশন ও আয়তন (Nagar Bhaban; 'আয়তন ৯১ দশমিক ৩১৫ বর্গ কিঃমিঃ')
MC_HISTORY = MC_B + '6922de5a933eb65569e1a101'      # ইতিহাস (the pourashava's history, updated 2019)
MC_COUNCILLORS = MC_B + '6922dde3933eb65569e16e7b'  # দায়িত্বপ্রাপ্ত কাউন্সিলরগণের নাম, ওয়ার্ড নং, মোবাইল নং (scanned PDF, 18.03.2026)
MC_COUNCILLORS_PDF = ('https://objectstorage.ap-dcc-gazipur-1.oraclecloud15.com/n/axvjbnqprylg/b/V2Ministry/o/office-mcc/2026/3/'
                      'f9e9f85c-3f97-4699-a023-0dda3d30a4df.pdf')
MC_CONTACT = MC_B + '6922dcac933eb65569e11830'      # জরুরী যোগাযোগ (administrator / CEO: CEO office landline; mayor@mcc.gov.bd)
MC_DC_GLANCE = 'https://mymensingh.gov.bd/pages/static-pages/6973bc81c4774958d7bbf28c'   # DC portal 'এক নজরে জেলা' (MCC population 2022)
# Read from the scanned 'এক নজরে' PDF (MC_GLANCE_PDF, rows 2-5 and 12-14); not machine-checked.
MC_SCANNED = {'established': ('১৪ অক্টোবর ২০১৮', '2018-10-14'), 'area': '৯১.৩১৫ বর্গকি.মি.', 'wards': '৩৩টি', 'zones': '০৩টি',
              'population_2022': '৫৭৬৯২৭', 'male_2022': '২৯৩৫৮২', 'female_2022': '২৮৩৩৪৫', 'population_projected': '১২০৯৯০২'}


def main_mcc():
    key, cc, cc_bn = CITY['key'], 'Mymensingh City Corporation', 'ময়মনসিংহ সিটি কর্পোরেশন'
    glance, loc, hist, coun, contact, dc = (page(MC_GLANCE), page(MC_LOCATION), page(MC_HISTORY), page(MC_COUNCILLORS),
                                            page(MC_CONTACT), page(MC_DC_GLANCE))
    if MC_GLANCE_PDF not in glance['attachments']:
        warn('the এক নজরে page no longer links %s (links %s): re-read the scanned figures' % (MC_GLANCE_PDF, glance['attachments']))
    if MC_COUNCILLORS_PDF not in coun['attachments']:
        warn('the councillor page no longer links %s (links %s): re-check the ward list' % (MC_COUNCILLORS_PDF, coun['attachments']))
    lt = loc['text'].replace('\n', ' ')
    am = re.search(r'আয়তন\s*([০-৯0-9]+)\s*দশমিক\s*([০-৯0-9]+)\s*বর্গ\s*কিঃ\s*মিঃ', lt)
    area_txt = '%s.%s' % (asc(am.group(1)), asc(am.group(2))) if am else ''
    if not am:
        warn('area not found on %s' % MC_LOCATION)
    addr = 'নগর ভবন, সাবেক ময়মনসিংহ পৌরসভা' if 'নগর ভবন, সাবেক ময়মনসিংহ পৌরসভা' in lt else ''
    hm = re.search(r'([০-৯0-9]{4}) সালে স্থাপিত ময়মনসিংহ পৌরসভা', hist['text'])
    ct = contact['text'].replace('\n', ' ')
    phones = []
    for x in re.findall(r'([০-৯0-9]{3,4})-([০-৯0-9]{5,7})\s*\(অফিস\)', ct):   # office landline(s) only; mobiles are not copied
        d = asc(x[0] + x[1])
        if re.match(r'^0[2-9]\d{6,9}$', d):
            phones.append(d)
    phones = list(dict.fromkeys(phones))
    email = 'mayor@mcc.gov.bd' if re.search(r'm\s*ayor\s*@\s*mcc\.gov\.bd', ct) else ''   # printed 'm ayor @mcc.gov.bd'; gmail not kept
    dct = dc['text'].replace('\n', ' ')
    dpm = re.search(r'ময়মনিসংহ সিটি কর্পোরেশন জনসংখ্যা\s*([০-৯0-9,]+)', dct)
    dc_pop = bn_num(dpm.group(1)) if dpm else ''
    if not dpm:
        warn('MCC population not found on the DC portal page %s' % MC_DC_GLANCE)
    dcc = re.search(r'([০-৯0-9]+)\s*টি সিটি করপোরেশন', dct)
    save_raw('location_area.txt', loc, 'Location / area: %s\nArea (as printed): %s\n' % (addr or '-', am.group(0) if am else '-'))
    save_raw('history_pourashava.txt', hist, sentences(hist['text'], '১৮৬৯ সালে স্থাপিত'))
    save_raw('contact.txt', contact, 'Office landline(s) (as printed, normalised): %s\nE-mail: %s\n(The administrator\'s and CEO\'s mobile '
             'numbers and the CEO\'s gmail address are not kept; no names.)' % (', '.join(phones) or '-', email or '-'))
    save_raw('ek_nojore_scanned_pdf.txt', glance, 'Attachment (scanned one-page PDF, no text layer): %s\nFigures read from the scan '
             '(not machine-checked): প্রতিষ্ঠাকাল %s; আয়তন %s; ওয়ার্ড সংখ্যা %s; অঞ্চল %s; মোট জনসংখ্যা (বিবিএস শুমারী ২০২২ অনুযায়ী) %s জন '
             '(পুরুষ %s, নারী %s); বর্তমান জনসংখ্যা (বিবিএস শুমারী ২০২২ এর প্রক্ষেপণের ভিত্তিতে) %s জন\n' % (
                 ', '.join(glance['attachments']) or '-', MC_SCANNED['established'][0], MC_SCANNED['area'], MC_SCANNED['wards'],
                 MC_SCANNED['zones'], MC_SCANNED['population_2022'], MC_SCANNED['male_2022'], MC_SCANNED['female_2022'],
                 MC_SCANNED['population_projected']))
    save_raw('councillor_list_page.txt', coun, 'Attachment (scanned PDF dated 18.03.2026, titled "৩৩ টি ওয়ার্ড এর দায়িত্বপ্রাপ্ত '
             'কাউন্সিলরগণের নামের তালিকা"; officials in charge of groups of wards; names and mobiles NOT copied): %s\n'
             % (', '.join(coun['attachments']) or '-'))
    save_raw('dc_portal_population.txt', dc, 'DC portal এক নজরে জেলা: %s; "জনশুমারি ও গৃহগণনা ২০২২ অনুযায়ী ... ময়মনিসংহ সিটি কর্পোরেশন '
             'জনসংখ্যা %s"\n' % (dcc.group(0) if dcc else '-', dpm.group(1) if dpm else '-'))
    n_wards = bn_int(MC_SCANNED['wards'])
    g_note = 'MCC এক নজরে: scanned PDF %s (read from the scan, not machine-checked).' % MC_GLANCE_PDF
    areas = [dict(level='city_corporation', name_en=cc, name_bn=cc_bn, parent_level='district', parent_name_en='Mymensingh',
                  parent_name_bn='ময়মনসিংহ', district_en='Mymensingh', website='https://mcc.gov.bd/', source_key=key, source_url=MC_LOCATION,
                  notes='Official site mcc.gov.bd (national-portal framework, linked from the divisional portal). Location: %s (লোকেশন '
                        'ও আয়তন). Office landline %s and e-mail %s (জরুরী যোগাযোগ, CEO\'s office line / mayor post address); the '
                        'administrator\'s and CEO\'s mobiles and the CEO\'s gmail address are not copied.' % (
                            addr or '-', ', '.join(phones) or '-', email or '-'))]
    areas += ward_rows(cc, cc_bn, key, 'MCC_WARD_NO', MC_COUNCILLORS, range(1, n_wards + 1),
                       lambda n: 'Ward number only (name_bn is a label). MCC has %d wards (এক নজরে, scanned PDF); its councillor list '
                                 '(scanned PDF, 18.03.2026, "৩৩ টি ওয়ার্ড") assigns wards 1-%d to officials in charge (names not copied). '
                                 'MCC publishes no ward names; there is no metropolitan police, so no ward-to-thana assignment.'
                                 % (n_wards, n_wards))
    write_csv('areas.csv', AREA_COLS, areas)
    f = cc_fact(key, cc, 'Mymensingh')
    est_bn, est_iso = MC_SCANNED['established']
    pop, male, female = bn_int(MC_SCANNED['population_2022']), bn_int(MC_SCANNED['male_2022']), bn_int(MC_SCANNED['female_2022'])
    facts = [
        f('city_corporation_established', est_iso, 'date', 'official', est_iso[:4], MC_GLANCE,
          '"সিটি কর্পোরেশনের প্রতিষ্ঠাকাল: %s". %s' % (est_bn, g_note)),
        f('area_km2', area_txt, 'km2', 'official', '', MC_LOCATION,
          'লোকেশন ও আয়তন: "%s" (no year); the scanned এক নজরে gives "%s".' % (am.group(0) if am else '-', MC_SCANNED['area'])) if area_txt else None,
        f('wards_count', str(n_wards), 'wards', 'official', '', MC_GLANCE,
          '"সিটি কর্পোরেশনের ওয়ার্ড সংখ্যা: %s"; the councillor list (scanned, 18.03.2026) is titled "৩৩ টি ওয়ার্ড". %s'
          % (MC_SCANNED['wards'], g_note)),
        f('zones_count', str(bn_int(MC_SCANNED['zones'])), 'zones', 'official', '', MC_GLANCE,
          '"সিটি কর্পোরেশনের অঞ্চল: %s"; the site lists regional executive officers\' offices for অঞ্চল ১-৩. %s' % (MC_SCANNED['zones'], g_note)),
        f('population', str(pop), 'persons', 'enumerated', '2022', MC_GLANCE,
          '"সিটি কর্পোরেশনের মোট জনসংখ্যা (বিবিএস শুমারী ২০২২ অনুযায়ী): %s জন" (male %d + female %d = %d). The DC portal\'s '
          '\'এক নজরে জেলা\' gives "%s" for the same census (a different figure; not resolved here). %s'
          % (MC_SCANNED['population_2022'], male, female, male + female, dpm.group(1) if dpm else '-', g_note)),
        f('population_male', str(male), 'persons', 'enumerated', '2022', MC_GLANCE, 'BBS census 2022 as given by MCC. ' + g_note),
        f('population_female', str(female), 'persons', 'enumerated', '2022', MC_GLANCE, 'BBS census 2022 as given by MCC. ' + g_note),
        f('population_projected', str(bn_int(MC_SCANNED['population_projected'])), 'persons', 'estimate', '', MC_GLANCE,
          '"মোট জনসংখ্যা (বিবিএস শুমারী ২০২২ এর প্রক্ষেপণের ভিত্তিতে বর্তমান জনসংখ্যা): %s জন"; more than twice the census figure, '
          'method and year not stated. %s' % (MC_SCANNED['population_projected'], g_note)),
        f('municipality_established_year', asc(hm.group(1)), 'year', 'official', asc(hm.group(1)), MC_HISTORY,
          '"%s সালে স্থাপিত ময়মনসিংহ পৌরসভা" (ইতিহাস, updated %s).' % (hm.group(1), hist['updated'] or '?')) if hm else None,
    ]
    write_csv('facts.csv', FACT_COLS, [x for x in facts if x])
    write_city_manifest({'key': key, 'division': 'mymensingh', 'kind': 'city_corporation', 'city': CITY['city'],
                         'name': 'Mymensingh City Corporation official site (mcc.gov.bd)', 'organization': cc,
                         'source_type': 'government_portal', 'trust_level': 4,
                         'urls': ['https://mcc.gov.bd/', MC_GLANCE, MC_GLANCE_PDF, MC_LOCATION, MC_HISTORY, MC_COUNCILLORS,
                                  MC_COUNCILLORS_PDF, MC_CONTACT, MC_DC_GLANCE],
                         'accessed': ACCESSED, 'publication_date': None, 'license': None, 'license_url': None,
                         'attribution': 'Mymensingh City Corporation (mcc.gov.bd); Mymensingh DC portal (mymensingh.gov.bd)',
                         'notes': 'MCC\'s এক নজরে and councillor list are scanned PDFs without a text layer: established %s, %s wards, %s '
                                  'zones and the 2022 census population %s (male %s, female %s) were read from the scan (not machine-checked) '
                                  'and are hard-coded in fetch.py with the attachment URL; the run warns if the attachment changes. Area %s '
                                  'km2 from the text of লোকেশন ও আয়তন. The DC portal gives the MCC population as %s (2022 census), a '
                                  'different figure. Ward numbers 1-%d (no ward names are published). Officials\' names and mobiles are not '
                                  'copied. www.mcc.gov.bd (linked from the divisional office menu) serves a self-signed certificate and was '
                                  'not used.' % (est_iso, n_wards, bn_int(MC_SCANNED['zones']), pop, male, female, area_txt or '?',
                                                  dc_pop or '?', n_wards)})


CITIES = {  # city -> collector; Dhaka Division has four, Chattogram two (DIVISIONS.md)
    'dhaka_north': dict(division='dhaka', folder='dhaka_north_city_corporation', key='DHAKA_NORTH_CITY_CORPORATION', city=50001,
                        district='Dhaka', run=main_dncc),
    'dhaka_south': dict(division='dhaka', folder='dhaka_south_city_corporation', key='DHAKA_SOUTH_CITY_CORPORATION', city=50002,
                        district='Dhaka', run=main_dscc),
    'narayanganj': dict(division='dhaka', folder='narayanganj_city_corporation', key='NARAYANGANJ_CITY_CORPORATION', city=50010,
                        district='Narayanganj', run=main_ncc),
    'gazipur': dict(division='dhaka', folder='gazipur_city_corporation', key='GAZIPUR_CITY_CORPORATION', city=50011,
                    district='Gazipur', run=main_gcc),
    'chattogram': dict(division='chattogram', folder='chattogram_city_corporation', key='CHATTOGRAM_CITY_CORPORATION', city=50003,
                       district='Chattogram', run=main_ccc),
    'cumilla': dict(division='chattogram', folder='cumilla_city_corporation', key='CUMILLA_CITY_CORPORATION', city=50009,
                    district='Cumilla', run=main_cocc),
    'khulna': dict(division='khulna', folder='khulna_city_corporation', key='KHULNA_CITY_CORPORATION', city=50004,
                   district='Khulna', run=main_kcc),
    'barishal': dict(division='barishal', folder='barishal_city_corporation', key='BARISHAL_CITY_CORPORATION', city=50007,
                     district='Barishal', run=main_bcc),
    'sylhet': dict(division='sylhet', folder='sylhet_city_corporation', key='SYLHET_CITY_CORPORATION', city=50006,
                   district='Sylhet', run=main_scc),
    'mymensingh': dict(division='mymensingh', folder='mymensingh_city_corporation', key='MYMENSINGH_CITY_CORPORATION', city=50012,
                       district='Mymensingh', run=main_mcc),
}
CITY = None


def main():
    global DIVISION, HERE, RAW, ACCESSED, CITY, WARNINGS
    ap = argparse.ArgumentParser(description='City corporation collector (default: Rajshahi City Corporation)')
    ap.add_argument('--division', default='rajshahi', choices=DIVISION_CHOICES)
    ap.add_argument('--city', choices=sorted(CITIES), help='one city of a multi-city division (default: all of its cities)')
    ap.add_argument('--out', help='output folder (for a multi-city division only with a single --city)')
    a = ap.parse_args()
    if a.division not in SITES or a.city:   # multi-city divisions (Dhaka): one folder per city corporation
        cities = [c for c, v in CITIES.items() if v['division'] == a.division and (a.city is None or c == a.city)]
        if not cities:
            raise SystemExit('no city collector for division %r / city %r' % (a.division, a.city))
        if a.out and len(cities) > 1:
            raise SystemExit('--out needs a single --city')
        here = os.path.dirname(os.path.abspath(__file__))
        DIVISION, ACCESSED = a.division, __import__('datetime').date.today().isoformat()
        for c in cities:
            CITY = CITIES[c]
            HERE = os.path.abspath(a.out or os.path.join(here, '..', CITY['folder']))
            if os.path.realpath(HERE) == os.path.realpath(here):
                raise SystemExit('refusing to write %s output into the Rajshahi folder' % c)
            RAW, WARNINGS = os.path.join(HERE, 'raw'), []
            os.makedirs(HERE, exist_ok=True)
            print('==', c, '->', HERE, file=sys.stderr)
            CITY['run']()
        return
    DIVISION, out = parse_division_args({k: v['folder'] for k, v in SITES.items()})
    if DIVISION != 'rajshahi':
        HERE, RAW = out, os.path.join(out, 'raw')
        ACCESSED = __import__('datetime').date.today().isoformat()
    elif os.path.realpath(out) != os.path.realpath(HERE):
        HERE, RAW = out, os.path.join(out, 'raw')
        if not os.path.exists(os.path.join(HERE, 'SOURCE.json')):
            import shutil
            shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'SOURCE.json'), HERE)
    SITES[DIVISION]['run']()


if __name__ == '__main__':
    main()
