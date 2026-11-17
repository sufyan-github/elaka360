#!/usr/bin/env python3
"""Rajshahi Divisional Commissioner portal (rajshahidiv.gov.bd) -> RAJDIV_PORTAL_2026.

Re-runnable, self-contained (stdlib + requests). Usage: python3 -I fetch.py
Writes raw/ excerpts, areas.csv, facts.csv and refreshes the file checksums in SOURCE.json.

Other divisions: python3 -I fetch.py --division <rangpur|...> [--out DIR] [--cache DIR]
  runs the generic division mode (block 'Division mode' below) and writes to the division's own folder
  (default data/sources/<division>_divisional_portal); the Rajshahi outputs in this folder are never touched. With no arguments
  (= --division rajshahi) the script behaves exactly as before; --out DIR redirects the Rajshahi outputs.
"""
import argparse
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



def main_rajshahi(args):
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


KIND = "divisional_portal"


def main():
    global HERE, RAW
    ap = argparse.ArgumentParser(description="Divisional Commissioner portal collector")
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
        RAW = os.path.join(HERE, "raw")
    main_rajshahi(a)


if __name__ == '__main__':
    main()
