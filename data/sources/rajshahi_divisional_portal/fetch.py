#!/usr/bin/env python3
"""Rajshahi Divisional Commissioner portal (rajshahidiv.gov.bd) -> RAJDIV_PORTAL_2026.

Re-runnable, self-contained (stdlib + requests). Usage: python3 -I fetch.py
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
# Rajshahi Divisional Commissioner portal (rajshahidiv.gov.bd)
# ---------------------------------------------------------------------------------------------------------------
KEY = 'RAJDIV_PORTAL_2026'
B = 'https://rajshahidiv.gov.bd/pages/static-pages/'
U_UPZ = B + '697fb33835ce18e1c06cb283'      # "উপজেলার তালিকা" (title "জেলা ও উপজেলাসমূহ"); earlier held the union-count table
U_UNIONS = B + '697fe5a835ce18e1c06dc8f2'   # "ইউনিয়নের তালিকা" (PDF attachment)
U_GLANCE = B + '697f79dc35ce18e1c06b6230'   # "এক নজরে রাজশাহী বিভাগ"
UNION_PDF_SHA256 = 'c264d6c3df36b934bf425a8f5bf3d5db1d583fba3a92007fbfeb69f1d17cc455'
UNION_PDF_FALLBACK = ('https://objectstorage.ap-dcc-gazipur-1.oraclecloud15.com/n/axvjbnqprylg/b/V2Ministry/o/'
                      'office-rajshahidiv/2024/12/14f1aa8d1197491d9350609897357943.pdf')

DISTRICTS = {'রাজশাহী': 'Rajshahi', 'নাটোর': 'Natore', 'নওগাঁ': 'Naogaon', 'চাঁপাইনবাবগঞ্জ': 'Chapainawabganj',
             'বগুড়া': 'Bogura', 'জয়পুরহাট': 'Joypurhat', 'পাবনা': 'Pabna', 'সিরাজগঞ্জ': 'Sirajganj'}
UPZ_EN = {
    'পবা': 'Paba', 'চারঘাট': 'Charghat', 'বাঘা': 'Bagha', 'পুঠিয়া': 'Puthia', 'তানোর': 'Tanore', 'মোহনপুর': 'Mohonpur',
    'দূর্গাপুর': 'Durgapur', 'বাগমারা': 'Bagmara', 'গোদাগাড়ী': 'Godagari',
    'নাটোর সদর': 'Natore Sadar', 'লালপুর': 'Lalpur', 'বাগাতিপাড়া': 'Bagatipara', 'বড়াইগ্রাম': 'Baraigram',
    'গুরুদাসপুর': 'Gurudaspur', 'সিংড়া': 'Singra', 'নলডাঙ্গা': 'Naldanga',
    'নওগাঁ সদর': 'Naogaon Sadar', 'আত্রাই': 'Atrai', 'রাণীনগর': 'Raninagar', 'পত্নীতলা': 'Patnitala', 'সাপাহার': 'Sapahar',
    'পোরশা': 'Porsha', 'মান্দা': 'Manda', 'মহাদেবপুর': 'Mohadevpur', 'ধামইরহাট': 'Dhamoirhat', 'বদলগাছী': 'Badalgachi',
    'নিয়ামতপুর': 'Niamatpur',
    'চাঁপাইনবাবগঞ্জ সদর': 'Chapainawabganj Sadar', 'শিবগঞ্জ': 'Shibganj', 'ভোলাহাট': 'Bholahat', 'গোমস্তাপুর': 'Gomostapur',
    'নাচোল': 'Nachol',
    'বগুড়া সদর': 'Bogra Sadar', 'শাজাহানপুর': 'Shajahanpur', 'শেরপুর': 'Sherpur', 'ধুনট': 'Dhunot',
    'সারিয়াকান্দি': 'Shariakandi', 'গাবতলী': 'Gabtali', 'সোনাতলা': 'Sonatala', 'দুপচাচিয়া': 'Dupchanchia', 'কাহালু': 'Kahaloo',
    'আদমদীঘি': 'Adamdighi', 'নন্দীগ্রাম': 'Nondigram', 'মোকামতলা': 'Mokamtala',
    'জয়পুরহাট সদর': 'Joypurhat Sadar', 'পাঁচবিবি': 'Panchbibi', 'আক্কেলপুর': 'Akkelpur', 'ক্ষেতলাল': 'Khetlal', 'কালাই': 'Kalai',
    'পাবনাসদর': 'Pabna Sadar', 'সাঁথিয়া': 'Santhia', 'সুজানগর': 'Sujanagar', 'বেড়া': 'Bera', 'ঈশ্বরদী': 'Ishurdi',
    'ভাঙ্গুড়া': 'Bhangura', 'ফরিদপুর': 'Faridpur', 'চাটমোহর': 'Chatmohar', 'আটঘড়িয়া': 'Atghoria',
    'সিরাজগঞ্জ সদর': 'Sirajganj Sadar', 'রায়গঞ্জ': 'Raigonj', 'কাজিপুর': 'Kazipur', 'তাড়াশ': 'Tarash',
    'শাহজাদপুর': 'Shahjadpur', 'উল্লাপাড়া': 'Ullapara', 'কামারখন্দ': 'Kamarkhand', 'বেলকুচি': 'Belkuchi', 'চৌহালী': 'Chauhali',
}

# Manual transcription of the union-list PDF (Word export with a broken Bangla font: its text layer is garbled, so the
# names were read from the rendered pages). One line per upazila:
# district_en|district_bn|upazila_en|upazila_bn (as printed)|first serial in PDF|unions separated by ';'
# "N নং" prefixes and " ইউনিয়ন / ইউপি / ইউনিয়ন পরিষদ" suffixes are stripped; everything else is kept as printed.
TRANSCRIPTION = """Rajshahi|রাজশাহী|Durgapur|দূর্গাপুর|1|নওপাড়া;কিসমতগণকৈড়;পানানগর;দেলুয়াবাড়ী;ঝালুকা;মাড়িয়া;জয়নগর
Rajshahi|রাজশাহী|Tanore|তানোর|8|কলমা;বাধাইড়;পাঁচন্দর;সরনজাই;তালন্দ;কামারগাঁ;চাঁন্দুড়িয়া
Rajshahi|রাজশাহী|Mohonpur|মোহনপুর|15|ধুরইল;ঘাসিগ্রাম;রায়ঘাটি;মৌগাছি;বাকশিমইল;জাহানাবাদ
Rajshahi|রাজশাহী|Charghat|চারঘাট|21|ইউসুফপুর;শলুয়া;সরদহ;নিমপাড়া;চারঘাট;ভায়ালক্ষ্মীপুর
Rajshahi|রাজশাহী|Bagmara|বাগমারা|27|গোবিন্দপাড়া;নরদাশ;দ্বীপপুর;বড়বিহানালী;আউচপাড়া;শ্রীপুর;বাসুপাড়া;কাচারীকোয়ালী পাড়া;শুভডাঙ্গা;মাড়িয়া;গণিপুর;ঝিকরা;গোয়ালকান্দি;হামিরকুৎসা;যোগীপাড়া;সোনাডাঙ্গা
Rajshahi|রাজশাহী|Godagari|গোদাগাড়ী|43|গোদাগাড়ী;মোহনপুর;পাকড়ী;রিশিকুল;গোগ্রাম;মাটিকাটা;দেওপাড়া;বাসুদেবপুর;চর আষাড়িয়াদহ
Rajshahi|রাজশাহী|Puthia|পুঠিয়া|52|পুঠিয়া;বেলপুকুরিয়া;বানেশ্বর;ভালুকগাছি;শিলমাড়িয়া;জিউপাড়া
Rajshahi|রাজশাহী|Bagha|বাঘা|58|আড়ানী;চকরাজাপুর;বাউসা;বাজুবাঘা;গড়গড়ি;পাকুড়িয়া;মনিগ্রাম
Rajshahi|রাজশাহী|Paba|পবা|65|দামকুড়া;পারিলা;হরিয়ান;হড়গ্রাম;বড়গাছী;দর্শনপাড়া;হুজুরীপাড়া;হরিপুর
Chapainawabganj|চাঁপাইনবাবগঞ্জ|Chapainawabganj Sadar|চাঁপাইনবাবগঞ্জ সদর|1|বালিয়াডাঙ্গা;গোবরাতলা;বারঘরিয়া;মহারাজপুর;রানীহাটি;চরঅনুপনগর;দেবীনগর;আলাতুলী;শাহজাহানপুর;ইসলামপুর;চরবাগডাংগা;নারায়নপুর;সুন্দরপুর;ঝিলিম
Chapainawabganj|চাঁপাইনবাবগঞ্জ|Shibganj|শিবগঞ্জ|15|ধাইনগর;চককীর্তি;নয়ালাভাঙ্গা;উজিরপুর;পাঁকা;মনাকষা;বিনোদপুর;ছত্রাজিতপুর;ঘোড়াপাখিয়া;শ্যামপুর;শাহাবাজপুর;দাইপুখুরিয়া;মোবারকপুর;কানসাট;দূর্লভপুর
Chapainawabganj|চাঁপাইনবাবগঞ্জ|Nachol|নাচোল|30|কসাব;ফতেপুর;নাচোল;নেজামপুর
Chapainawabganj|চাঁপাইনবাবগঞ্জ|Gomostapur|গোমস্তাপুর|34|গোমস্তাপুর;রহনপুর;আলিনগর;বাংগাবাড়ি;বোয়ালিয়া;চৌডালা;পার্বতীপুর;রাধানগর
Chapainawabganj|চাঁপাইনবাবগঞ্জ|Bholahat|ভোলাহাট|42|গোহালবাড়ী;ভোলাহাট;দলদলী;জামবাড়ীয়া
Natore|নাটোর|Natore Sadar|নাটোর সদর|1|ছাতনী;তেবাড়িয়া;দিঘাপতিয়া;লক্ষীপুর খোলাবাড়িয়া;বড়হরিশপুর;কাফুরিয়া;হালসা
Natore|নাটোর|Singra|সিংড়া|8|সুকাশ;ডাহিয়া;ইটালী;কলম;চামারী;হাতিয়ানদহ;লালোর;শেরকোল;তাজপুর;চৌগ্রাম;ছাতারদীঘি;রামানন্দখাজুরা
Natore|নাটোর|Baraigram|বড়াইগ্রাম|20|জোয়াড়ী;বড়াইগ্রাম;জোনাইল;নগর;মাঝগাঁও;গোপালপুর;চান্দাই
Natore|নাটোর|Gurudaspur|গুরুদাসপুর|27|নাজিরপুর;বিয়াঘাট;খুবজীপুর;মশিন্দা;ধারাবারিষা;চাপিলা
Natore|নাটোর|Lalpur|লালপুর|33|লালপুর;ঈশ্বরদী;চংধুপইল;আড়বাব;বিলমাড়িয়া;দুয়ারিয়া;ওয়ালিয়া;দুড়দুড়িয়া;অর্জুনপুর বরমহাটি;কদিমচিলান
Natore|নাটোর|Bagatipara|বাগাতিপাড়া|43|পাঁকা;জামনগর;বাগাতিপাড়া;দয়ারামপুর;ফাগুয়ারদিয়াড়
Natore|নাটোর|Naldanga|নলডাঙ্গা|48|ব্রক্ষপুর;মাধনগর;খাজুরা;পিপরুল;বিপ্রবেলঘড়িয়া
Naogaon|নওগাঁ|Sapahar|সাপাহার|1|সাপাহার;গোয়ালা;তিলনা;আইহাই;পাতাড়ী;শিরন্টি
Naogaon|নওগাঁ|Raninagar|রাণীনগর|7|খট্টেশ্বর রাণীনগর;কাশিমপুর;গোনা;পারইল;বড়গাছা;কালিগ্রাম;একডালা;মিরাট
Naogaon|নওগাঁ|Atrai|আত্রাই|15|শাহাগোলা;ভোঁপাড়া;আহসানগঞ্জ;পাঁচুপুর;বিশা;মনিয়ারী;কালিকাপুর;হাটকালুপাড়া
Naogaon|নওগাঁ|Dhamoirhat|ধামইরহাট|23|ধামইরহাট;আগ্রাদ্বিগুন;আলমপুর;উমার;আড়ানগর;জাহানপুর;ইসবপুর;খেলনা
Naogaon|নওগাঁ|Manda|মান্দা|31|ভারশো;ভালাইন;পরানপুর;মান্দা;গনেশপুর;মৈনম;প্রসাদপুর;কুশুম্বা;তেঁতুলিয়া;নূরুল্যাবাদ;কালিকাপুর;কাঁশোপাড়া;কশব;বিষ্ণুপুর
Naogaon|নওগাঁ|Badalgachi|বদলগাছী|45|বদলগাছী;মথুরাপুর;পাহাড়পুর;মিঠাপুর;কোলা;বিলাশবাড়ী;আধাইপুর;বালুভরা
Naogaon|নওগাঁ|Porsha|পোরশা|53|নিতপুর;তেঁতুলিয়া;ছাওড়;গাঙ্গুরিয়া;ঘাটনগর;মশিদপুর
Naogaon|নওগাঁ|Niamatpur|নিয়ামতপুর|59|হাজীনগর;চন্দননগর;ভাবিচা;নিয়ামতপুর;রসুলপুর;পাড়ইল;শ্রীমন্তপুর;বাহাদুরপুর
Naogaon|নওগাঁ|Naogaon Sadar|নওগাঁ সদর|67|শিকারপুর;শৈলগাছী;কীর্ত্তিপুর;বর্ষাইল;চন্ডিপুর;দুবলহাটী;হাঁসাইগাড়ী;তিলকপুর;বলিহার;হাপানিয়া;বক্তারপুর;বোয়ালিয়া
Naogaon|নওগাঁ|Patnitala|পত্নীতলা|79|পত্নীতলা;নির্মইল;দিবর;আকবরপুর;মাটিন্দর;কৃষ্ণপুর;পাটিচরা;নজিপুর;ঘোষনগর;আমাইড়;শিহাড়া
Naogaon|নওগাঁ|Mohadevpur|মহাদেবপুর|90|মহাদেবপুর সদর;হাতুড়;খাজুর;চান্দাশ;রাইগাঁ;এনায়েতপুর;সফাপুর;উত্তরগ্রাম;চেরাগপুর;ভীমপুর
Bogura|বগুড়া|Dupchanchia|দুপচাঁচিয়া|1|দুপচাঁচিয়া;চামরুল;গুনাহার;গোবিন্দপুর;জিয়ানগর;তালোড়া
Bogura|বগুড়া|Adamdighi|আদমদীঘি|7|আদমদীঘি;ছাতিয়ানগ্রাম;সান্তাহার;নশরতপুর;কুন্দগ্রাম;চাঁপাপুর
Bogura|বগুড়া|Kahaloo|কাহালু|13|কাহালু;বীরকেদার;মুরইল;কালাই;মালঞ্চা;নারহট্ট;পাইকড়;জামগ্রাম;দূর্গাপুর
Bogura|বগুড়া|Shibganj|শিবগঞ্জ|22|শিবগঞ্জ;আটমূল;বিহার;বুড়িগঞ্জ;দেউলী;কিচক;ময়দানহাট্ট;মাঝিহট্ট;পিরব;রায়নগর;সৈয়দপুর;মোকামতলা
Bogura|বগুড়া|Dhunot|ধুনট|34|ধুনট সদর;ভান্ডারবাড়ি;চৌকিবাড়ী;চিকাশী;এলাঙ্গী;গোপালনগর;গোসাইবাড়ি;কালেরপাড়া;মথুরাপুর;নিমগাছি
Bogura|বগুড়া|Shajahanpur|শাজাহানপুর|44|মাঝিড়া;আমরুল;আড়িয়া;গোহাইল;খোট্টাপাড়া;মাদলা;খরনা;আশেকপুর;চুপিনগর
Bogura|বগুড়া|Bogra Sadar|বগুড়া সদর|53|শেখেরকোলা;গোকুল;লাহেড়ীপাড়া;নামুজা;নিশিন্দারা;নুনগোলা;শাখারিয়া;ফাঁপোর;রাজাপুর;এরুলিয়া;সাবগ্রাম
Bogura|বগুড়া|Nondigram|নন্দীগ্রাম|64|নন্দীগ্রাম সদর;ভাটগ্রাম;ভাটরা;থালতামাঝগ্রাম;বুড়ইল
Bogura|বগুড়া|Gabtali|গাবতলী|69|গাবতলী সদর;বালিয়াদিঘী;দক্ষিণপাড়া;দূর্গাহাটা;কাগইল;মহিষাবান;নাড়ুয়ামালা;নশিপুর;রাশেশ্বরপুর;নেপালতলী;সোনারায়
Bogura|বগুড়া|Shariakandi|সারিয়াকান্দি|80|সারিয়াকান্দি;কামালপুর;কাজলা;কর্ণিবাড়ী;কুতুবপুর;নারচী;হাটশেরপুর;ভেলাবাড়ী;বোহাইল;চন্দনবাইশা;চালুয়াবাড়ি;ফুলবাড়ি
Bogura|বগুড়া|Sonatala|সোনাতলা|92|সোনাতলা;তেকানী চুকাইনগর;দিগদাইড়;জোড়গাছা;মধুপুর;পাকুল্লা;বালুয়া
Bogura|বগুড়া|Sherpur|শেরপুর|99|ভবানীপুর;বিশালপুর;খামারকান্দি;খানপুর;কুসুম্বি;মির্জাপুর;শাহবন্দেগী;সীমাবাড়ি;সুঘাট;গাড়িদহ
Pabna|পাবনা|Pabna Sadar|পাবনা সদর|1|মালিগাছা;মালঞ্চি;গয়েশপুর;আতাইকুলা;সাদুল্লাপুর;চরতারাপুর;দোগাছী;হিমাইতপুর;দাপুনিয়া;ভাঁড়ারা
Pabna|পাবনা|Atghoria|আটঘরিয়া|11|মাজপাড়া;চাঁদভা;দেবোত্তর;একদন্ত;লক্ষ্মীপুর
Pabna|পাবনা|Ishurdi|ঈশ্বরদী|17|সাঁড়া;পাকশী;মুলাডুলি;দাশুরিয়া;সলিমপুর;সাহাপুর;লক্ষীকুন্ডা
Pabna|পাবনা|Bera|বেড়া|24|হাটুরিয়া নাকালিয়া;নতুন ভারেঙ্গা;কৈটোলা;চাকলা;পুরান ভারেঙ্গা;জাতসাখিনী;রুপপুর;মাশুমদিয়া;ঢালারচর
Pabna|পাবনা|Santhia|সাঁথিয়া|33|নাগডেমরা;ধুলাউড়ি;ভুলবাড়ীয়া;ধোপাদহ;করমজা;কাশিনাথপুর;গৌরীগ্রাম;নন্দনপুর;ক্ষেতুপাড়া;আর/আতাইকুলা
Pabna|পাবনা|Sujanagar|সুজানগর|43|ভায়না;তাঁতিবন্দ;দুলাই;আহম্মদপুর;রাণীনগর;সাগরকান্দি;হাটখালী;নাজিরগঞ্জ;মানিকহাট;সাতবাড়ীয়া
Pabna|পাবনা|Chatmohar|চাটমোহর|53|হান্ডিয়াল;নিমাইচড়া;ছাইকোলা;গুনাইগাছা;হরিপুর;ডিবিগ্রাম;পার্শ্বডাঙ্গা;মূলগ্রাম;ফৈলজানা;মথুরাপুর;বিলচলন
Pabna|পাবনা|Faridpur|ফরিদপুর|64|বৃলাহিড়ীবাড়ী;পুংগলী;ফরিদপুর;হাদল;বনওয়ারীনগর;ডেমরা
Pabna|পাবনা|Bhangura|ভাঙ্গুড়া|70|ভাঙ্গুড়া;খানমরিচ;অষ্টমনিষা;পার-ভাঙ্গুড়া;দিলপাশার;মন্ডতোষ
Sirajganj|সিরাজগঞ্জ|Sirajganj Sadar|সিরাজগঞ্জ সদর|1|রতনকান্দি;বাগবাটি;বহুলী;শিয়ালকোল;খোকশাবাড়ী;ছোনগাছা;মেছড়া;কাওয়াকোলা;কালিয়াহরিপুর;সয়দাবাদ
Sirajganj|সিরাজগঞ্জ|Ullapara|উল্লাপাড়া|11|রামকৃষ্ণপুর;বাঙ্গালা;উধুনিয়া;বড়পাংগাশী;মোহনপুর;দুর্গানগর;পুর্নিমাগাতী;সলংগা;হাটিকুমরুল;বড়হর;উল্লাপাড়া;পঞ্চক্রোশী;সলপ;কয়ড়া
Sirajganj|সিরাজগঞ্জ|Shahjadpur|শাহজাদপুর|25|কায়েমপুর;গাড়াদহ;পোতাজিয়া;রূপবাটি;গালা;পোরজনা;হাবিবুল্লাহ নগর;বেলতৈল;খুকনী;কৈজুরী;সোনাতনী;নরিনা;জালালপুর
Sirajganj|সিরাজগঞ্জ|Raigonj|রায়গঞ্জ|38|ধামাইনগর;সোনাখাড়া;ধুবিল;ঘুড়কা;চান্দাইকোনা;ধানগড়া;নলকা;পাঙ্গাসী;ব্রহ্মগাছা
Sirajganj|সিরাজগঞ্জ|Tarash|তাড়াশ|47|তালম;বারুহাস;সগুনা;মাগুড়া বিনোদ;নওগাঁ;তাড়াশ সদর;মাধাইনগর;দেশীগ্রাম
Sirajganj|সিরাজগঞ্জ|Kazipur|কাজিপুর|55|সোনামুখী;চালিতাডাঙ্গা;মাইজবাড়ী;খাসরাজবাড়ী;গান্ধাইল;কাজিপুর;শুভগাছা;চরগিরিশ;তেকানি;নাটুয়ারপাড়া;নিশ্চিন্তপুর;মনসুর নগর
Sirajganj|সিরাজগঞ্জ|Kamarkhand|কামারখন্দ|67|ভদ্রঘাট;ঝাঐল;জামতৈল;রায়দৌলতপুর
Sirajganj|সিরাজগঞ্জ|Belkuchi|বেলকুচি|71|বেলকুচি;রাজাপুর;ভাঙ্গাবাড়ী;দৌলতপুর;ধুকুরিয়াবেড়া;বড়ধুল
Sirajganj|সিরাজগঞ্জ|Chauhali|চৌহালী|77|সদিয়া চাঁদপুর;স্থল;ঘোড়জান;উমারপুর;খাষকাউলিয়া;খাষপুকুরিয়া;বাঘুটিয়া
Joypurhat|জয়পুরহাট|Joypurhat Sadar|জয়পুরহাট সদর|1|ধলাহার;দোগাছী;ভাদসা;মোহাম্মদাবাদ;পুরানাপৈল;আমদই;বম্বু;জামালপুর;চকবরকত
Joypurhat|জয়পুরহাট|Panchbibi|পাঁচবিবি|10|বাগজানা;ধরঞ্জী;আয়মারসুলপুর;আটাপুর;মোহাম্মদপুর;কুসুম্বা;বালিঘাটা;আওলাই
Joypurhat|জয়পুরহাট|Kalai|কালাই|18|আহম্মেদাবাদ;মাত্রাই;উদয়পুর;পুনট;জিন্দারপুর
Joypurhat|জয়পুরহাট|Khetlal|ক্ষেতলাল|23|তুলশীগঙ্গা;বড়তারা;মামুদপুর;বড়াইল;আলমপুর
Joypurhat|জয়পুরহাট|Akkelpur|আক্কেলপুর|28|রুকিন্দীপুর;সোনামূখী;গোপীনাথপুর;তিলকপুর;রায়কালী"""

# Cells whose printed glyphs are Bijoy->Unicode conversion artefacts; value = what is literally printed.
PRINTED_AS = {
    ('Raninagar', 'খট্টেশ্বর রাণীনগর'): 'খট্টেশ^র রাণীনগর',
    ('Manda', 'নূরুল্যাবাদ'): 'নূরম্নল্যাবাদ',
    ('Pabna Sadar', 'সাদুল্লাপুর'): 'সাদুলস্নাপুর',
    ('Atghoria', 'একদন্ত'): 'একদমত্ম',
    ('Atghoria', 'লক্ষ্মীপুর'): 'লÿপুর (broken glyph)',
    ('Bera', 'রুপপুর'): 'রম্নপপুর',
    ('Ullapara', 'হাটিকুমরুল'): 'হাটিকুমরম্নল',
    ('Ullapara', 'উল্লাপাড়া'): 'উলস্নাপাড়া',
}
UNNUMBERED = {('Raigonj', 'সোনাখাড়া'): 'Listed between "১নং ধামাইনগর" and "২নং ধুবিল" without a union number.'}
PRINTED_AS = {(a, nfc(b)): v for (a, b), v in PRINTED_AS.items()}
UNNUMBERED = {(a, nfc(b)): v for (a, b), v in UNNUMBERED.items()}


def main():
    upz = page(U_UPZ)
    unions = page(U_UNIONS)
    glance = page(U_GLANCE)
    expect(glance, 'জেলা | ৮টি', 'সিটি কর্পোরেশনের সংখ্যা | ০২টি', 'উপজেলা | ৬৮টি', 'পৌরসভা | ৬২টি', 'ইউনিয়ন | ৫৬৭টি',
           'প্রায় ১৮,১৫৩ বর্গকিলোমিটার', 'মোট: ২০,৩৪৬,৮৬৫ জন', 'সংসদীয় আসন সংখ্যা | ৩৯টি')
    expect(upz, 'জেলারসংখ্যা: ৮টি, উপজেলার সংখ্যা: ৬৮টি', '১৩। মোকামতলা')
    save_raw('upazila_list_page.txt', upz)
    save_raw('ek_nojore_division_basic_table.txt', glance, section(glance['text'], 'মৌলিক তথ্য', 'অর্থনীতি ও ব্যবসা-বাণিজ্য'))
    save_raw('union_list_page.txt', unions, 'Attachment(s):\n' + '\n'.join(unions['attachments']))

    # union-list PDF: verify it is the file that was transcribed
    pdf_url = unions['attachments'][0] if unions['attachments'] else UNION_PDF_FALLBACK
    pdf = get(pdf_url, binary=True)
    digest = hashlib.sha256(pdf).hexdigest()
    pdf_ok = digest == UNION_PDF_SHA256
    if not pdf_ok:
        warn('union-list PDF changed (sha256 %s); the transcription below is of the old file and must be re-checked' % digest)
    with open(os.path.join(RAW, 'union_list_pdf.sha256'), 'w') as fh:
        fh.write('%s  %s\n' % (digest, pdf_url))

    areas, facts = [], []
    u_note = '"উপজেলার তালিকা" page updated %s' % upz['updated']
    # --- upazilas (68, incl. Mokamtala) -----------------------------------------------------------------------
    district = None
    for line in upz['text'].split('\n'):
        line = line.strip()
        if line in DISTRICTS:
            district = line
            continue
        m = re.match(r'^\|?\s*([০-৯]+)।\s*(.+?)\s*$', line)
        if m and district:
            name = nfc(m.group(2).strip(' |'))
            en = UPZ_EN.get(name, '')
            if not en:
                warn('unmapped upazila ' + name)
            n = 'English name from the seed (not from this page). ' + u_note
            if name == 'মোকামতলা':
                n = 'New upazila (listed as Bogura no. 13); gazette/effective date not on this page; union composition not stated. ' + n
            areas.append(dict(level='upazila', name_en=en, name_bn=name, parent_level='district', parent_name_en=DISTRICTS[district],
                              parent_name_bn=district, district_en=DISTRICTS[district], upazila_en=en, code=asc(m.group(1)),
                              code_scheme='RAJDIV_LIST_SERIAL', source_key=KEY, source_url=U_UPZ, notes=n))
    if len(areas) != 68:
        warn('expected 68 upazilas, parsed %d' % len(areas))

    # --- unions from the PDF ----------------------------------------------------------------------------------
    p_note = ('Union list PDF (Word document created 2022-10-16, uploaded under /2024/12/) attached to "ইউনিয়নের তালিকা" '
              'page updated %s; transcribed manually from the rendered pages%s.' % (unions['updated'], '' if pdf_ok else ' (PDF CHANGED - re-verify)'))
    per_district = {}
    for line in TRANSCRIPTION.strip().split('\n'):
        if line.startswith('#'):
            continue
        den, dbn, ue, ubn, first, names = line.split('|')
        names = [nfc(x) for x in names.split(';')]
        per_district[den] = per_district.get(den, 0) + len(names)
        for k, n in enumerate(names):
            notes = []
            if (ue, n) in PRINTED_AS:
                notes.append('Printed as "%s" (font-conversion artefact); name reconstructed.' % PRINTED_AS[(ue, n)])
            if (ue, n) in UNNUMBERED:
                notes.append(UNNUMBERED[(ue, n)])
            notes.append(p_note)
            areas.append(dict(level='union', name_en='', name_bn=n, parent_level='upazila', parent_name_en=ue, parent_name_bn=nfc(ubn),
                              district_en=den, upazila_en=ue, source_key=KEY, source_url=U_UNIONS, notes=' '.join(notes)))
        facts.append(dict(entity_level='upazila', entity_name_en=ue, district_en=den, upazila_en=ue, fact='union_count',
                          value=str(len(names)), unit='unions', basis='official', year='2022', source_key=KEY, source_url=U_UNIONS,
                          notes='Count of union rows in the divisional union-list PDF. ' + p_note))
    for den, n in per_district.items():
        extra = ''
        if den == 'Pabna':
            extra = ' PDF serials run to 75 but serial 16 is a column-number header row, so 74 unions.'
        facts.append(dict(entity_level='district', entity_name_en=den, district_en=den, fact='union_count', value=str(n),
                          unit='unions', basis='official', year='2022', source_key=KEY, source_url=U_UNIONS,
                          notes='Sum of union rows in the divisional union-list PDF.' + extra + ' ' + p_note))
    total = sum(per_district.values())
    g = 'এক নজরে রাজশাহী বিভাগ, page updated %s' % glance['updated']

    def dv(fact, value, unit, notes, basis='official', year=''):
        return dict(entity_level='division', entity_name_en='Rajshahi', fact=fact, value=value, unit=unit, basis=basis,
                    year=year, source_key=KEY, source_url=U_GLANCE, notes=notes)
    facts += [
        dict(entity_level='division', entity_name_en='Rajshahi', fact='union_count', value=str(total), unit='unions',
             basis='official', year='2022', source_key=KEY, source_url=U_UNIONS, notes='Sum of the union-list PDF. ' + p_note),
        dv('union_count', '567', 'unions', 'Stated on the division at-a-glance table (no per-district split). ' + g, year='2026'),
        dv('pourashava_count', '62', 'pourashavas', 'No per-district split or names on the portal. ' + g, year='2026'),
        dv('city_corporation_count', '2', 'city_corporations', 'Names not given on the page. ' + g, year='2026'),
        dv('upazila_count', '68', 'upazilas', g + '; also ' + u_note, year='2026'),
        dv('district_count', '8', 'districts', g, year='2026'),
        dv('parliamentary_seats', '39', 'seats', g, year='2026'),
        dv('area_km2', '18153', 'km2', '"প্রায়" (approximately) as stated. ' + g),
        dv('population', '20346865', 'persons', 'Year/basis not stated on the page. ' + g, basis='as_stated'),
        dv('population_male', '10079495', 'persons', g, basis='as_stated'),
        dv('population_female', '10265796', 'persons', g, basis='as_stated'),
        dv('population_hijra', '1574', 'persons', g, basis='as_stated'),
    ]
    write_csv('areas.csv', AREA_COLS, areas)
    write_csv('facts.csv', FACT_COLS, facts)
    finish()


if __name__ == '__main__':
    main()
