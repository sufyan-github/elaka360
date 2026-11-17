#!/usr/bin/env python3
"""Metropolitan police portal -> thana areas/facts. Default: Rajshahi Metropolitan Police (rmp.gov.bd) -> RMP_PORTAL_2026.

Re-runnable, self-contained (stdlib + requests). Usage: python3 -I fetch.py [--division rangpur] [--out DIR]
(--division rangpur: Rangpur Metropolitan Police, rpmp.gov.bd -> RANGPUR_METRO_POLICE in ../rangpur_metro_police)
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
# Rajshahi Metropolitan Police portal (rmp.gov.bd)
# ---------------------------------------------------------------------------------------------------------------
KEY = 'RMP_PORTAL_2026'
U_GLANCE = 'https://rmp.gov.bd/pages/static-pages/695e3b09c4774958d7b72177'   # এক নজরে আরএমপি
U_UNITS = 'https://rmp.gov.bd/pages/static-pages/695e3b08c4774958d7b7214e'    # ইউনিটসমূহ (division -> thana list)

# (bangla as printed on the units page, bangla in the at-a-glance list, english transliteration, RMP division, thana subsite)
THANAS = [
    ('বোয়ালিয়া', 'বোয়ালিয়া', 'Boalia', 'Boalia', 'boaliaps'),
    ('রাজপাড়া', 'রাজপাড়া', 'Rajpara', 'Boalia', 'rajparaps'),
    ('চন্দ্রিমা', 'চন্দ্রিমা', 'Chandrima', 'Boalia', 'chandrimaps'),
    ('মতিহার', 'মতিহার', 'Motihar', 'Motihar', 'motiharps'),
    ('কাটাখালি', 'কাটাখালী', 'Katakhali', 'Motihar', 'katakhalips'),
    ('বেলপুকুর', 'বেলপুকুর', 'Belpukur', 'Motihar', 'belpukurps'),
    ('শাহমখদুম', 'শাহমখদুম', 'Shah Makhdum', 'Shah Makhdum', 'shahmokhdumps'),
    ('এয়ারপোর্ট', 'এয়ারপোর্ট', 'Airport', 'Shah Makhdum', 'airportps'),
    ('পবা', 'পবা', 'Paba', 'Shah Makhdum', 'pabaps'),
    ('কাশিয়াডাঙ্গা', 'কাশিয়াডাঙ্গা', 'Kashiadanga', 'Kashiadanga', 'kashiadangaps'),
    ('দামকুড়া', 'দামকুড়া', 'Damkura', 'Kashiadanga', 'damkuraps'),
    ('কর্ণহার', 'কর্ণহার', 'Karnahar', 'Kashiadanga', 'kornoharps'),
]
DIVISIONS_BN = {'Boalia': 'বোয়ালিয়া', 'Motihar': 'মতিহার', 'Shah Makhdum': 'শাহমখদুম', 'Kashiadanga': 'কাশিয়াডাঙ্গা'}


def main_rajshahi():
    glance = page(U_GLANCE)
    units = page(U_UNITS)
    expect(glance, '১৯৯২ সালের ১ জুলাই রাজপাড়া, বোয়ালিয়া, শাহমখদুম ও মতিহার থানা নিয়ে প্রতিষ্ঠিত',
           'তখন এর আয়তন ছিলো ৯২ বর্গ কিলোমিটার', '২০১৮ সালের ২২ ফেব্রুয়ারি', '১২টি থানা',
           'বোয়ালিয়া, রাজপাড়া, চন্দ্রিমা, মতিহার, কাটাখালী, বেলপুকুর, শাহমখদুম, এয়ারপোর্ট, পবা, কাশিয়াডাঙ্গা, কর্ণহার ও দামকুড়া',
           'বর্তমান আয়তন ৪৭২ বর্গ কিলোমিটার', 'জনসংখ্যা ১০,১০,০২০ জন')
    for bn, _, _, div, _ in THANAS:
        expect(units, 'অফিসার ইনচার্জ, %s থানা' % bn)
    for d in DIVISIONS_BN.values():
        expect(units, 'উপ-পুলিশ কমিশনার, %s ডিবিশন' % d)

    save_raw('ek_nojore_rmp.txt', glance, section(glance['text'], None, '১.\n'))
    # unit list: keep names only, phone numbers redacted
    save_raw('units.txt', units, redact_phones(units['text']))

    g_note = 'এক নজরে আরএমপি updated ' + glance['updated']
    u_note = 'units page updated ' + units['updated']
    areas = []
    for bn, bn2, en, div, sub in THANAS:
        n = 'Rajshahi Metropolitan Police thana; RMP division (DC zone): %s (%s). English name is a transliteration ' \
            '(RMP subsite %s.rmp.gov.bd). ' % (div, DIVISIONS_BN[div], sub)
        if bn != bn2:
            n += 'At-a-glance page spells it %s. ' % bn2
        n += 'RMP publishes no ward/union coverage per thana. ' + u_note
        areas.append(dict(level='thana', name_en=en, name_bn=bn, parent_level='district', parent_name_en='Rajshahi',
                          parent_name_bn='রাজশাহী', district_en='Rajshahi', website='https://%s.rmp.gov.bd/' % sub,
                          source_key=KEY, source_url=U_UNITS, notes=n))
    write_csv('areas.csv', AREA_COLS, areas)

    def f(fact, value, unit, basis, year, notes, url=U_GLANCE):
        return dict(entity_level='metropolitan_police', entity_name_en='Rajshahi Metropolitan Police', district_en='Rajshahi',
                    fact=fact, value=value, unit=unit, basis=basis, year=year, source_key=KEY, source_url=url, notes=notes)
    facts = [
        f('established', '1992-07-01', 'date', 'official', '1992', 'Founded with 4 thanas: Rajpara, Boalia, Shah Makhdum, Motihar. ' + g_note),
        f('area_km2_at_founding', '92', 'km2', 'official', '1992', g_note),
        f('thana_count', '12', 'thanas', 'official', '2018', '8 thanas added on 2018-02-22 (4 -> 12). ' + g_note),
        f('thana_count', '12', 'thanas', 'official', '', 'Units page lists 12 OC posts under 4 divisions (Boalia, Motihar, Shah Makhdum, Kashiadanga). ' + u_note, U_UNITS),
        f('police_division_count', '4', 'divisions', 'official', '', 'Boalia, Motihar, Shah Makhdum, Kashiadanga (DC zones). ' + u_note, U_UNITS),
        f('area_km2', '472', 'km2', 'official', '', 'Current RMP jurisdiction ("বর্তমান আয়তন"); not the City Corporation area. ' + g_note),
        f('population', '1010020', 'persons', 'official', '', 'RMP jurisdiction population as stated; year/basis not stated. ' + g_note),
        f('jurisdiction', 'RCC whole area + parts of Katakhali and Naohata pourashavas + parts of Harian, Parila, Haripur, Damkura, '
          'Baragachhi unions (Paba) + part of Yusufpur union (Charghat)', 'text', 'official', '', g_note),
    ]
    write_csv('facts.csv', FACT_COLS, facts)
    finish()


# ---------------------------------------------------------------------------------------------------------------
# Rangpur Metropolitan Police (RpMP). Official site rpmp.gov.bd (own CMS, not the national portal framework; linked as
# "রংপুর মেট্রোপলিটন পুলিশ"); the divisional portal also links the national-portal page rpmp.rangpurdiv.gov.bd (thin).
# ---------------------------------------------------------------------------------------------------------------
RP_KEY = 'RANGPUR_METRO_POLICE'
RPB = 'https://rpmp.gov.bd/index.php/home/'
RP_HISTORY = RPB + 'history'
RP_CONTACT = 'https://rpmp.rangpurdiv.gov.bd/pages/static-pages/69771cd5c4774958d7c06d89'  # অফিস যোগাযোগ (address)
# (bangla, english transliteration, zone key, page slug)
RP_THANAS = [('কোতয়ালী', 'Kotwali', 'kotwali', 'kotowali_thana'), ('তাজহাট', 'Tajhat', 'kotwali', 'tajhat_thana'),
             ('মাহিগঞ্জ', 'Mahiganj', 'mahiganj', 'mahigonj_thana'), ('হারাগাছ', 'Haragach', 'mahiganj', 'haragach_thana'),
             ('পরশুরাম', 'Parshuram', 'parshuram', 'porshuram_thana'), ('হাজিরহাট', 'Hajirhat', 'parshuram', 'hazirhat_thana')]
RP_ZONES = {'kotwali': ('কোতয়ালী জোন', 'Kotwali', 'kotwali_tajhat_zone'), 'mahiganj': ('মাহিগঞ্জ জোন', 'Mahiganj', 'haragach_mahigonj_zone'),
            'parshuram': ('পরশুরাম জোন', 'Parshuram', 'porshuram_hazirhat_zone')}
MOUZA_RE = re.compile(r'([^\d০-৯,।()]+?(?:\([^()]*\))?)\s*\(?\s*(?:জেএল|জেল|জেলা)\s*নং\s*-?\s*([০-৯0-9]+)\s*\)')


def rpmp_page(url):
    """rpmp.gov.bd page: main column (<div class="col-md-9"> ... <footer>) as text."""
    t = get(url)
    i = t.find('<div class="col-md-9">')
    if i < 0:
        raise RuntimeError('no main column in ' + url)
    seg = t[i:]
    j = seg.find('<footer')
    seg = seg[:j] if j > 0 else seg
    m = re.search(r'<h1[^>]*>(.*?)</h1>', seg, re.S)
    txt = to_text(seg)
    return {'url': url, 'title': to_text(m.group(1)) if m else '', 'updated_raw': '', 'updated': '', 'text': txt,
            'flat': re.sub(r'\s+', ' ', txt), 'attachments': []}


def main_rangpur():
    hist = rpmp_page(RP_HISTORY)
    hist_flat = hist['flat']
    for n in ('১০ ডিসেম্বর ২০১৭', '১১৮৫ জন', '১২ এপ্রিল ২০১৮', 'রংপুর মহানগরী পুলিশ আইন, ২০১৮', '১৬ সেপ্টেম্বর ২০১৮'):
        if n not in hist_flat:
            warn('expected text not found on %s: %r' % (RP_HISTORY, n))
    i = hist_flat.find('দীর্ঘ প্রশাসনিক প্রক্রিয়ার পর')
    save_raw('history_rpmp_formation.txt', hist, hist_flat[i:hist_flat.find('রংপুর নামকরণের', i)].strip() if i >= 0 else '')
    contact = page(RP_CONTACT)
    addr = re.search(r'কাচারী বাজার, রংপুর-[০-৯]+', contact['text'])
    zones = {}
    for z, (zbn, zen, slug) in RP_ZONES.items():
        zp = rpmp_page(RPB + slug)
        zones[z] = zp
        save_raw('zone_%s.txt' % z, zp, redact_phones(zp['flat']))
    areas, facts = [], []

    def f(fact, value, unit, basis, year, notes, url=RP_HISTORY, level='metropolitan_police', name='Rangpur Metropolitan Police'):
        return dict(entity_level=level, entity_name_en=name, district_en='Rangpur', fact=fact, value=value, unit=unit, basis=basis,
                    year=year, source_key=RP_KEY, source_url=url, notes=notes)
    for bn, en, z, slug in RP_THANAS:
        url = RPB + slug
        tp = rpmp_page(url)
        flat = tp['flat']
        body = flat.split('যোগাযোগ পদবী')[0]
        save_raw('thana_%s.txt' % en.lower(), tp, redact_phones(body))
        if '%s থানা' % bn not in tp['title']:
            warn('thana page title changed: %s %r' % (url, tp['title']))
        mw = re.search(r'ওয়ার্ড\S*', body)
        wpart = body[:mw.start()] if mw else ''
        wpart = wpart[wpart.find('কর্পোরেশন'):] if 'কর্পোরেশন' in wpart else ''
        wards = [int(asc(x)) for x in re.findall(r'[০-৯0-9]+', wpart)]
        mouzas = [(re.sub(r'^[\s।,]*[০-৯0-9]*\s*[।.]?\s*', '', a).strip(), int(asc(b))) for a, b in MOUZA_RE.findall(body)]
        extra = []
        if 'পৌরসভা' in body.split('মৌজাসমূহ')[0]:
            extra.append('Haragach Pourashava' if 'হারাগাছ পৌরসভা' in body else 'a pourashava')
        um = re.search(r'(\S+) থানার (?:[০-৯0-9]+নং )?(\S+) ইউনিয়ন', body)
        if um:
            extra.append('%s union (%s thana)' % (um.group(2), um.group(1)))
        loc = re.search(r'থানাটি (\S+) অবস্থিত', body)
        zbn, zen, _ = RP_ZONES[z]
        note = ('Rangpur Metropolitan Police thana; zone: %s (%s). Covers RPCC wards %s%s; %d mouzas with JL numbers listed (see facts). '
                'English name is a transliteration. Ward lists of different thanas overlap (wards split between thanas).'
                % (zen, zbn, ', '.join(map(str, wards)) or '?', (' + ' + ' + '.join(extra)) if extra else '', len(mouzas)))
        if loc:
            note += ' Location: "%s".' % loc.group(0)
        areas.append(dict(level='thana', name_en=en, name_bn=bn, parent_level='district', parent_name_en='Rangpur', parent_name_bn='রংপুর',
                          district_en='Rangpur', website=url, source_key=RP_KEY, source_url=url, notes=note))
        tname = '%s thana (RpMP)' % en
        facts.append(f('rpcc_wards_covered', ','.join(map(str, wards)), 'ward numbers', 'official', '',
                       'RPCC wards named on the thana page' + ('; also ' + ', '.join(extra) if extra else ''), url, 'thana', tname))
        facts.append(f('mouza_count', len(mouzas), 'mouzas', 'listed', '', 'Mouzas listed on the thana page', url, 'thana', tname))
        facts.append(f('mouzas', '; '.join('%s (JL %d)' % m for m in mouzas), 'text', 'listed', '',
                       'Mouza names and JL numbers as printed on the thana page (JL numbers are per upazila; spellings not corrected)',
                       url, 'thana', tname))
    write_csv('areas.csv', AREA_COLS, areas)
    facts = [
        f('organogram_gazette', '2017-12-10', 'date', 'official', '2017', 'Gazette creating 1185 posts and 123 vehicles in the RpMP organogram (history page).'),
        f('sanctioned_posts', '1185', 'posts', 'official', '2017', 'Posts created by the 10 Dec 2017 gazette (history page).'),
        f('act_passed', '2018-04-12', 'date', 'official', '2018', 'রংপুর মহানগরী পুলিশ আইন, ২০১৮ passed by parliament (history page).'),
        f('established', '2018-09-16', 'date', 'official', '2018', 'Formal inauguration of RpMP (history page).'),
        f('thana_count', str(len(RP_THANAS)), 'thanas', 'official', '', 'Kotwali, Tajhat, Mahiganj, Haragach, Parshuram, Hajirhat (site menu).', RPB + 'units'),
        f('police_division_count', str(len(RP_ZONES)), 'zones', 'official', '',
          'Zones: Kotwali (Kotwali, Tajhat), Mahiganj (Mahiganj, Haragach), Parshuram (Parshuram, Hajirhat).', RPB + RP_ZONES['kotwali'][2]),
    ] + ([f('hq_address', addr.group(0), 'text', 'official', '', 'Police Commissioner\'s office (অফিস যোগাযোগ).', RP_CONTACT)] if addr else []) + facts
    write_csv('facts.csv', FACT_COLS, facts)
    meta = {'key': RP_KEY, 'division': 'rangpur', 'kind': 'metro_police',
            'name': 'Rangpur Metropolitan Police official site (rpmp.gov.bd)', 'organization': 'Rangpur Metropolitan Police, Bangladesh Police',
            'source_type': 'government_portal', 'trust_level': 4,
            'urls': ['https://rpmp.gov.bd/', RP_HISTORY] + [RPB + t[3] for t in RP_THANAS] + [RPB + z[2] for z in RP_ZONES.values()] + [RP_CONTACT],
            'accessed': ACCESSED, 'publication_date': None, 'license': None, 'license_url': None,
            'attribution': 'Rangpur Metropolitan Police (rpmp.gov.bd)',
            'notes': 'RpMP\'s own site rpmp.gov.bd (custom CMS; pages carry no update date). 6 thanas in 3 zones; each thana page lists '
                     'the RPCC wards and mouzas (with JL numbers) it covers. Haragach thana also covers Haragach Pourashava and Sarai union '
                     '(Kaunia); Mahiganj also Kalyani union (Pirgachha). No area or population figure is published. Phone numbers are '
                     'not copied here (see RANGPUR_METRO_POLICE_THANAS_2026); raw/ excerpts have phones redacted.'}
    with open(os.path.join(HERE, 'SOURCE.json'), 'w', encoding='utf-8') as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
        fh.write('\n')
    finish()


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


SITES = {  # division -> metropolitan police collector (city, portal, output folder)
    'rajshahi': dict(city='Rajshahi', portal='https://rmp.gov.bd/', key=KEY, folder='rmp', run=main_rajshahi),
    'rangpur': dict(city='Rangpur', portal='https://rpmp.gov.bd/', key=RP_KEY, folder='rangpur_metro_police', run=main_rangpur),
}


def main():
    global DIVISION, HERE, RAW, ACCESSED
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
