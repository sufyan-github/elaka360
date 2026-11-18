#!/usr/bin/env python3
"""Metropolitan police portal -> thana areas/facts. Default: Rajshahi Metropolitan Police (rmp.gov.bd) -> RMP_PORTAL_2026.

Re-runnable, self-contained (stdlib + requests). Usage: python3 -I fetch.py [--division rangpur] [--out DIR]
(--division rangpur: Rangpur Metropolitan Police, rpmp.gov.bd -> RANGPUR_METRO_POLICE in ../rangpur_metro_police;
 --division dhaka [--city dhaka|gazipur]: DMP -> ../dhaka_metro_police, GMP -> ../gazipur_metro_police;
 --division chattogram [--city chattogram]: CMP -> ../chattogram_metro_police;
 --division khulna [--city khulna]: KMP -> ../khulna_metro_police;
 --division barishal [--city barishal]: BMP -> ../barishal_metro_police;
 --division sylhet [--city sylhet]: SMP -> ../sylhet_metro_police)
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


# --- Dhaka Division: DMP and GMP, one folder per force (DIVISIONS.md); SOURCE.json carries "city" -------------------
# DMP police stations as dmp.gov.bd 'Find Your Local Police' spells them -> (Bangla name as on the Dhaka DC portal's
# city-corporation thana list, English name used elsewhere in these sources). Khilkhet is not on the DC list: its Bangla
# spelling is the locality name on DNCC's ward list. Hatirjheel is on the DC list but not on the DMP page.
DMP_THANAS = {
    "Adabor": ("আদাবর", "Adabor"), "Badda": ("বাড্ডা", "Badda"), "Banani": ("বনানী", "Banani"), "Bangshal": ("বংশাল", "Bangshal"),
    "Bimanbandar": ("বিমানবন্দর", "Biman Bandar"), "Cantonment": ("ক্যান্টনমেন্ট", "Cantonment"), "Chalkbazar": ("চকবাজার", "Chawkbazar"),
    "Dakshin Khan": ("দক্ষিণখান", "Dakshinkhan"), "Darus-Salam": ("দারুস সালাম", "Darus Salam"), "Demra": ("ডেমরা", "Demra"),
    "Dhanmondi": ("ধানমন্ডি", "Dhanmondi"), "Gandaria": ("গেন্ডারিয়া", "Gandaria"), "Gulshan": ("গুলশান", "Gulshan"),
    "Hazaribag": ("হাজারীবাগ", "Hazaribagh"), "Jattrabari": ("যাত্রাবাড়ী", "Jatrabari"), "Kafrul": ("কাফরুল", "Kafrul"),
    "Kalabagan": ("কলাবাগান", "Kalabagan"), "Kamrangirchar": ("কামরাঙ্গীরচর", "Kamrangirchar"), "Khilgoan": ("খিলগাঁও", "Khilgaon"),
    "Khilkhet": ("খিলক্ষেত", "Khilkhet"), "Kodomtali": ("কদমতলী", "Kadamtali"), "Kotwali": ("কোতোয়ালী", "Kotwali"),
    "Lalbagh": ("লালবাগ", "Lalbagh"), "Mirpur Model": ("মিরপুর", "Mirpur"), "Mohammadpur": ("মোহাম্মদপুর", "Mohammadpur"),
    "Motijheel": ("মতিঝিল", "Motijheel"), "Mugda": ("মুগদা", "Mugda"), "New Market": ("নিউমার্কেট", "New Market"),
    "Pallabi": ("পল্লবী", "Pallabi"), "Paltan": ("পল্টন", "Paltan"), "Ramna": ("রমনা", "Ramna"), "Rampura": ("রামপুরা", "Rampura"),
    "Rupnagar": ("রূপনগর", "Rupnagar"), "Sabujbag": ("সবুজবাগ", "Sabujbagh"), "Shah Ali": ("শাহআলী", "Shah Ali"),
    "Shahbag": ("শাহবাগ", "Shahbagh"), "Shahjahanpur": ("শাহজাহানপুর", "Shahjahanpur"), "Sutrapur": ("সূত্রাপুর", "Sutrapur"),
    "Shyampur": ("শ্যামপুর", "Shyampur"), "Sher e Bangla Nagar": ("শেরেবাংলা নগর", "Sher-e-Bangla Nagar"),
    "Tejgoan Industrial": ("তেজগাঁও শিল্পাঞ্চল", "Tejgaon Industrial Area"), "Tejgoan": ("তেজগাঁও", "Tejgaon"), "Turag": ("তুরাগ", "Turag"),
    "Uttara East": ("উত্তরা পূর্ব", "Uttara East"), "Uttara West": ("উত্তরা পশ্চিম", "Uttara West"), "Uttar Khan": ("উত্তরখান", "Uttar Khan"),
    "Bsahantek": ("ভাষানটেক", "Bhashantek"), "Vatara": ("ভাটারা", "Bhatara"), "Wari": ("ওয়ারী", "Wari"),
}
DMP_EXTRA = {"Hatirjheel": ("হাতিরঝিল", "Hatirjheel")}   # on the DC portal list only
DMP_LOCAL = "https://dmp.gov.bd/find-your-local-police/"
DMP_HISTORY = "https://dmp.gov.bd/history/"
DMP_UNITS = "https://dmp.gov.bd/units/"
DMP_CONTACT = "https://dmp.gov.bd/contact-us/"
DHAKA_DC_GLANCE = "https://dhaka.gov.bd/pages/static-pages/6995bedb35ce18e1c079f6b8"   # 'এক নজরে ঢাকা জেলা' (city thana list)
DMP_CC_NOTE = ("No official source found that places this DMP thana in Dhaka North or Dhaka South City Corporation (dmp.gov.bd, "
               "dncc.gov.bd, dscc.gov.bd and the Dhaka DC portal give no thana-to-city-corporation list; DSCC only gives a count of "
               "23 thanas), so area_en is left empty.")
GMP_THANAS = [  # zone_id on gmp.gov.bd, menu name, Bangla (GMP "About GMP"), English used here (menu spelling; "Sadar" -> "Gazipur Sadar"), zone, crime division
    (1, "Sadar", "গাজীপুর সদর", "Gazipur Sadar", "সদর জোন", "অপরাধ উত্তর"), (2, "Bason", "বাসন", "Bason", "সদর জোন", "অপরাধ উত্তর"),
    (3, "Konabari", "কোনাবাড়ী", "Konabari", "কোনাবাড়ী জোন", "অপরাধ উত্তর"), (4, "Kashimpur", "কাশিমপুর", "Kashimpur", "কোনাবাড়ী জোন", "অপরাধ উত্তর"),
    (5, "Gacha", "গাছা", "Gacha", "গাছা জোন", "অপরাধ দক্ষিণ"), (6, "Pubail", "পূবাইল", "Pubail", "গাছা জোন", "অপরাধ দক্ষিণ"),
    (7, "Tongi East", "টঙ্গী পূর্ব", "Tongi East", "টঙ্গী জোন", "অপরাধ দক্ষিণ"), (8, "Tongi West", "টঙ্গী পশ্চিম", "Tongi West", "টঙ্গী জোন", "অপরাধ দক্ষিণ"),
]
GMP_HISTORY = "https://gmp.gov.bd/history.php"
GMP_CONTACT = "https://gmp.gov.bd/contact-us.php"
GMP_THANA_URL = "https://gmp.gov.bd/range-units/units_details.php?zone_id=%d"
GMP_CC_NOTE = ("GMP's 'About GMP' says the metropolitan area consists of the 57 wards of Gazipur City Corporation "
               "('গাজীপুর সিটি কর্পোরেশনের ৫৭টি ওয়ার্ড নিয়ে গঠিত এই মেট্রোপলিটন এলাকা'), so every GMP thana lies in it.")


def plain_page(url, start=None, end=None):
    """Non-portal page (dmp.gov.bd WordPress, gmp.gov.bd PHP): text between two markers."""
    txt = to_text(get(url))
    if start and start in txt:
        txt = txt[txt.index(start):]
    if end and end in txt:
        txt = txt[:txt.index(end)]
    return {'url': url, 'title': '', 'updated_raw': '', 'updated': '', 'text': txt, 'flat': re.sub(r'\s+', ' ', txt), 'attachments': []}


def mp_fact(key, name, district):
    def f(fact, value, unit, basis, year, notes, url, level='metropolitan_police', ename=None):
        return dict(entity_level=level, entity_name_en=ename or name, district_en=district, fact=fact, value=value, unit=unit,
                    basis=basis, year=year, source_key=key, source_url=url, notes=notes)
    return f


def write_metro_manifest(meta):
    with open(os.path.join(HERE, 'SOURCE.json'), 'w', encoding='utf-8') as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
        fh.write('\n')
    finish()


def main_dmp():
    key = CITY['key']
    local = plain_page(DMP_LOCAL, 'Find Your Local Police\nAdabor', 'Comments are closed')
    hist = plain_page(DMP_HISTORY, 'Dhaka Metropolitan Police (DMP) came into force', 'Comments are closed')
    units = plain_page(DMP_UNITS, 'Crime Division', 'Detective Branch')
    dc = page(DHAKA_DC_GLANCE)
    hf = hist['flat']
    for n in ('came into force on February 01, 1976', '12 Police Stations along with 6,000 officers', 'almost 2.0 cores',
              'almost 34,000 officers and force', 'two city corporations – Dhaka South City Corporation (DSCC) and Dhaka North City Corporation (DNCC)',
              '50 police stations of Dhaka Metropolitan Police', 'Total sanctioned strength of DMP (all ranks and status) is 32987'):
        if n not in hf:
            warn('expected text not found on %s: %r' % (DMP_HISTORY, n))
    listed = re.findall(r'^(.+?) ?Police Station$', local['text'], flags=re.M)
    listed = [re.sub(r'(?<=[a-z])(?=Police)', ' ', x).strip() for x in listed]
    unknown = [x for x in listed if x not in DMP_THANAS]
    if unknown:
        warn('DMP stations not in the name table: %s' % unknown)
    m = re.search(r'সিটি কর্পোরেশন এলাকার থানাসমূহ:\s*(.+?)।', dc['text'].replace('\n', ' '))
    dc_list = [x.strip() for x in re.split(r',| ও ', m.group(1))] if m else []
    crime = [x for x in re.findall(r'^(\w+) Divi?s?i?on$', units['text'], flags=re.M) if x != 'Crime']
    save_raw('dmp_stations_listed.txt', local, '\n'.join(listed) + '\n(addresses and numbers: DHAKA_METRO_POLICE_THANAS_2026)')
    save_raw('history.txt', hist, '\n'.join(l for l in hist['text'].split('\n') if re.search(
        r'came into force|12 Police Stations|two city corporations|50 police stations|Total sanctioned strength|eight|08 \(Eight\)', l)))
    save_raw('crime_divisions.txt', units, units['text'])
    save_raw('dhaka_dc_city_thanas.txt', dc, m.group(0) if m else '')
    areas = []
    for en_dmp, (bn, en) in list(DMP_THANAS.items()) + list(DMP_EXTRA.items()):
        on_dmp = en_dmp in listed
        on_dc = bn in dc_list
        n = 'Dhaka Metropolitan Police thana. Listed on %s. %s. %s' % (
            ' and '.join(x for x in ['dmp.gov.bd "Find Your Local Police"' if on_dmp else '', 'the Dhaka DC portal city-thana list' if on_dc else ''] if x),
            ('English name as on dmp.gov.bd ("%s Police Station")' % en_dmp) if on_dmp else 'English name transliterated (not on dmp.gov.bd)', DMP_CC_NOTE)
        if en_dmp == 'Khilkhet':
            n += ' Bangla spelling as in DNCC\'s ward-area list (Khilkhet is not on the DC portal list).'
        areas.append(dict(level='thana', name_en=en, name_bn=bn, parent_level='district', parent_name_en='Dhaka', parent_name_bn='ঢাকা',
                          district_en='Dhaka', website='', source_key=key, source_url=DMP_LOCAL if on_dmp else DHAKA_DC_GLANCE, notes=n))
    write_csv('areas.csv', AREA_COLS, areas)
    f = mp_fact(key, 'Dhaka Metropolitan Police', 'Dhaka')
    facts = [
        f('established', '1976-02-01', 'date', 'official', '1976', '"came into force on February 01, 1976" (history).', DMP_HISTORY),
        f('thana_count_at_founding', '12', 'thanas', 'official', '1976', 'Started with 12 police stations and 6,000 officers and force.', DMP_HISTORY),
        f('thana_count', '50', 'thanas', 'official', '', '"50 police stations of Dhaka Metropolitan Police" (history). "Find Your Local Police" lists %d '
          '(no Hatirjheel); the Dhaka DC portal says 50 thanas in the city-corporation area and names %d distinct ones (no Khilkhet).'
          % (len(listed), len(set(dc_list))), DMP_HISTORY),
        f('police_stations_listed', str(len(listed)), 'thanas', 'listed', '2026', 'Stations with contacts on "Find Your Local Police".', DMP_LOCAL),
        f('crime_division_count', str(len(crime)), 'divisions', 'official', '', 'Crime divisions: %s (units page). No thana-to-division list is published.'
          % ', '.join(crime), DMP_UNITS),
        f('population', '20000000', 'persons', 'estimate', '', '"Now the population is almost 2.0 cores" (sic; about 2 crore); year and basis not stated.', DMP_HISTORY),
        f('personnel', '34000', 'persons', 'estimate', '', '"almost 34,000 officers and force"; the same page also gives a total strength of "more than 30627" '
          'and a sanctioned strength of 32987.', DMP_HISTORY),
        f('sanctioned_posts', '32987', 'posts', 'official', '', 'Total sanctioned strength (all ranks, ministerial staff included).', DMP_HISTORY),
        f('jurisdiction', 'Dhaka North City Corporation and Dhaka South City Corporation', 'text', 'official', '',
          '"Jurisdiction of DMP has already been administratively divided into two city corporations – DSCC and DNCC" (history). '
          'No thana-to-city-corporation list is published.', DMP_HISTORY),
    ]
    write_csv('facts.csv', FACT_COLS, facts)
    write_metro_manifest({'key': key, 'division': 'dhaka', 'kind': 'metro_police', 'city': CITY['city'],
                          'name': 'Dhaka Metropolitan Police official site (dmp.gov.bd)', 'organization': 'Dhaka Metropolitan Police, Bangladesh Police',
                          'source_type': 'government_portal', 'trust_level': 4, 'urls': [DMP_LOCAL, DMP_HISTORY, DMP_UNITS, DHAKA_DC_GLANCE],
                          'accessed': ACCESSED, 'publication_date': None, 'license': None, 'license_url': None,
                          'attribution': 'Dhaka Metropolitan Police (dmp.gov.bd); Deputy Commissioner\'s office, Dhaka (dhaka.gov.bd)',
                          'notes': 'dmp.gov.bd is a WordPress site (pages carry no update date). Thanas = the 49 stations of "Find Your Local '
                                   'Police" + Hatirjheel from the Dhaka DC portal list (50, as DMP\'s history states). DMP covers both Dhaka '
                                   'city corporations, but no official source places the individual thanas in DNCC or DSCC, so no thana carries '
                                   'a city corporation. Phone numbers are in DHAKA_METRO_POLICE_THANAS_2026.'})


def main_gmp():
    key = CITY['key']
    hist = plain_page(GMP_HISTORY, 'About GMP', 'Important Links')
    hf = hist['flat']
    for n in ('১৬ সেপ্টেম্বর ২০১৮', 'গাজীপুর সিটি কর্পোরেশনের ৫৭টি ওয়ার্ড নিয়ে গঠিত এই মেট্রোপলিটন এলাকা', 'প্রায় ৩৩০ বর্গ কিলোমিটার',
              'প্রায় ৬৫ লক্ষ নাগরিকের', 'মোট ৮টি থানা', 'সদর জোনের আওতায় রয়েছে গাজীপুর সদর ও বাসন থানা',
              'কোনাবাড়ী জোনের আওতায় রয়েছে কোনাবাড়ী ও কাশিমপুর থানা', 'গাছা জোনের অন্তর্ভুক্ত থানাগুলো হলো গাছা ও পূবাইল',
              'টঙ্গী জোনে টঙ্গী পূর্ব এবং টঙ্গী পশ্চিম থানা', 'গাজীপুর মেট্রোপলিটন পুলিশ অর্ডিন্যান্স, ২০১৮'):
        if n not in hf:
            warn('expected text not found on %s: %r' % (GMP_HISTORY, n))
    save_raw('about_gmp.txt', hist, '\n'.join(p for p in re.split(r'(?<=।)\s*', hf) if re.search(
        r'১৬ সেপ্টেম্বর|৫৭টি ওয়ার্ড|৩৩০ বর্গ|৬৫ লক্ষ|৮টি থানা|জোন|অর্ডিন্যান্স', p)))
    areas = []
    for zid, menu, bn, en, zone, div in GMP_THANAS:
        areas.append(dict(level='thana', name_en=en, name_bn=bn, parent_level='district', parent_name_en='Gazipur', parent_name_bn='গাজীপুর',
                          district_en='Gazipur', website=GMP_THANA_URL % zid, source_key=key, source_url=GMP_HISTORY,
                          notes='Gazipur Metropolitan Police thana; zone %s, %s বিভাগ (About GMP). English name as on the GMP menu ("%s Thana"). '
                                'area_en: Gazipur City Corporation — %s' % (zone, div, menu, GMP_CC_NOTE)))
    write_csv('areas.csv', AREA_COLS, areas)
    f = mp_fact(key, 'Gazipur Metropolitan Police', 'Gazipur')
    facts = [
        f('established', '2018-09-16', 'date', 'official', '2018', 'GMP formally started on 16 September 2018; governed by the Gazipur Metropolitan '
          'Police Ordinance, 2018 (About GMP).', GMP_HISTORY),
        f('thana_count', '8', 'thanas', 'official', '', 'গাজীপুর সদর, বাসন, কোনাবাড়ী, কাশিমপুর, গাছা, পূবাইল, টঙ্গী পূর্ব ও টঙ্গী পশ্চিম (About GMP).', GMP_HISTORY),
        f('zone_count', '4', 'zones', 'official', '', 'Crime North: Sadar zone (Gazipur Sadar, Bason), Konabari zone (Konabari, Kashimpur); '
          'Crime South: Gacha zone (Gacha, Pubail), Tongi zone (Tongi East, Tongi West).', GMP_HISTORY),
        f('area_km2', '330', 'km2', 'approximate', '', '"প্রায় ৩৩০ বর্গ কিলোমিটার" (GMP area; GCC gives 329.53 km2).', GMP_HISTORY),
        f('population', '6500000', 'persons', 'estimate', '', '"প্রায় ৬৫ লক্ষ নাগরিক"; year and basis not stated (GCC\'s own page says about 4,000,000).', GMP_HISTORY),
        f('jurisdiction', 'Gazipur City Corporation (all 57 wards)', 'text', 'official', '', GMP_CC_NOTE, GMP_HISTORY),
    ]
    write_csv('facts.csv', FACT_COLS, facts)
    write_metro_manifest({'key': key, 'division': 'dhaka', 'kind': 'metro_police', 'city': CITY['city'],
                          'name': 'Gazipur Metropolitan Police official site (gmp.gov.bd)', 'organization': 'Gazipur Metropolitan Police, Bangladesh Police',
                          'source_type': 'government_portal', 'trust_level': 4, 'urls': ['https://gmp.gov.bd/', GMP_HISTORY] + [GMP_THANA_URL % t[0] for t in GMP_THANAS],
                          'accessed': ACCESSED, 'publication_date': None, 'license': None, 'license_url': None,
                          'attribution': 'Gazipur Metropolitan Police (gmp.gov.bd)',
                          'notes': 'gmp.gov.bd is GMP\'s own PHP site (no update dates). 8 thanas in 4 zones; the metropolitan area is the 57 '
                                   'wards of Gazipur City Corporation, so each thana\'s area_en is Gazipur City Corporation. No ward/mouza '
                                   'coverage per thana is published. Phone numbers are in GAZIPUR_METRO_POLICE_THANAS_2026.'})


# --- Chattogram Division: Chattogram Metropolitan Police (cmp.gov.bd + the CMP national-portal site) ---------------------------
# CMP thanas: Bangla as on the CMP portal's 'এক নজরে' list, English used here, English as on cmp.gov.bd 'Information Of Police
# Station', crime division (cmp.gov.bd contact directory), contact-directory page id and the thana's heading on that page.
CMP_THANAS = [
    ("কোতোয়ালী", "Kotwali", "Kotwali", "দক্ষিণ", 287, "কোতোয়ালি"), ("বাকলিয়া", "Bakalia", "Bakolia", "দক্ষিণ", 287, "বাকলিয়া"),
    ("চকবাজার", "Chawkbazar", "Chawk Bazar", "দক্ষিণ", 287, "চকবাজার"), ("সদরঘাট", "Sadarghat", "Sadarghat", "দক্ষিণ", 287, "সদরঘাট"),
    ("পাঁচলাইশ", "Panchlaish", "Panchlaish", "উত্তর", 288, "পাঁচলাইশ"), ("চান্দগাঁও", "Chandgaon", "Chandgaon", "উত্তর", 288, "চাঁন্দগাঁও"),
    ("বায়েজিদ বোস্তামী", "Bayezid Bostami", "Bayazid Bostami", "উত্তর", 288, "বায়েজীদ"), ("খুলশী", "Khulshi", "Khulshi", "উত্তর", 288, "খুলশী"),
    ("ডবলমুরিং", "Double Mooring", "Doublemooring", "পশ্চিম", 289, "ডবলমুরিং"), ("পাহাড়তলী", "Pahartali", "Pahartali", "পশ্চিম", 289, "পাহাড়তলী"),
    ("হালিশহর", "Halishahar", "Halishahar", "পশ্চিম", 289, "হালিশহর"), ("আকবরশাহ", "Akbarshah", "Akbar Shah", "পশ্চিম", 289, "আকবরশাহ"),
    ("বন্দর", "Bandar", "Port", "বন্দর", 290, "বন্দর"), ("পতেঙ্গা", "Patenga", "Patenga", "বন্দর", 290, "পতেঙ্গা"),
    ("কর্ণফুলী", "Karnaphuli", "Karnophuli", "বন্দর", 290, "কর্ণফুলি"), ("ইপিজেড", "EPZ", "EPZ", "বন্দর", 290, "ইপিজেড"),
]
CMP_SITE = "https://cmp.gov.bd/index.php?cPath=%d"        # cmp.gov.bd (CMP's own PHP site; 2013 framework, pages undated)
CMP_PORTAL_GLANCE = "https://police.chittagongdiv.gov.bd/pages/static-pages/at-a-glance-6ae2db41fd9ba07169122831"   # এক নজরে
CMP_PORTAL_CONTACT = "https://police.chittagongdiv.gov.bd/pages/static-pages/যোগাযোগ-15cb30-699124d1516a96d4de404110"  # যোগাযোগ
CMP_CC_SENTENCE = "সিএমপির আওতাধীন এলাকায় চট্টগ্রাম সিটি কর্পোরেশনের অধিকাংশ এলাকা অন্তর্ভুক্ত"
CMP_CC_NOTE = ("CMP says its area includes most of Chattogram City Corporation ('%s', CMP portal এক নজরে), but neither CMP "
               "(cmp.gov.bd, police.chittagongdiv.gov.bd) nor CCC (ccc.gov.bd publishes no thana list) places individual thanas in the "
               "city corporation, so area_en is left empty." % CMP_CC_SENTENCE)


def cmp_body(t):
    """cmp.gov.bd page HTML -> body lines (after the left menu, before the footer)."""
    s = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", " ", t or "", flags=re.S | re.I)
    s = re.sub(r"<br\s*/?>|</p>|</div>|</li>|</tr>|</h\d>", "\n", s, flags=re.I)
    s = re.sub(r"</t[dh]>", " | ", s, flags=re.I)
    s = __import__("html").unescape(re.sub(r"<[^>]+>", " ", s))
    lines = [unicodedata.normalize("NFC", re.sub(r"\s+", " ", l)).strip() for l in s.split("\n")]
    lines = [l for l in lines if l and l not in ("|", "| |", "| | |")]
    a = max((i for i, l in enumerate(lines) if l.startswith("Emergency Helpline")), default=-1)
    b = next((i for i, l in enumerate(lines) if l.startswith("Copyright")), len(lines))
    return lines[a + 1:b]


def cmp_sentences(txt, *keys):
    """Only the sentences of a page that carry the cited facts."""
    parts = re.split(r'(?<=[।.])\s+|\n', txt)
    return '\n'.join(dict.fromkeys(p.strip() for p in parts if any(k in p for k in keys)))


def main_cmp():
    key = CITY['key']
    glance = page(CMP_PORTAL_GLANCE)
    hist_l = cmp_body(get(CMP_SITE % 301))
    hist = ' '.join(hist_l)
    gl = glance['text'].replace('\n', ' ')
    m = re.search(r'থানাগুলো হলো\s*—\s*(.+?)।', gl)
    listed = [x.strip() for x in re.split(r',| ও ', m.group(1))] if m else []
    if sorted(listed) != sorted(t[0] for t in CMP_THANAS):
        warn('CMP portal thana list differs from the table: %s' % listed)
    for n in ('১৯৭৮ সালের ৩০ নভেম্বর', '১৬টি থানা', CMP_CC_SENTENCE, 'লালদীঘির পাড়'):
        if n not in gl:
            warn('expected text not found on %s: %r' % (CMP_PORTAL_GLANCE, n))
    for n in ('30 November, 1978', '128 square mile', '10,00,000', 'six police stations', 'divided its six police stations into twelve',
              'At present CMP has 16 police Stations, 31 outposts, 05 IC (Investigating Centre) and 6 police box', 'about 6,458'):
        if n not in re.sub(r'\s+', ' ', hist):
            warn('expected text not found on %s: %r' % (CMP_SITE % 301, n))
    div_of = {}
    for pid, dbn in ((287, 'দক্ষিণ'), (288, 'উত্তর'), (289, 'পশ্চিম'), (290, 'বন্দর')):
        lines = cmp_body(get(CMP_SITE % pid))
        hm = re.match(r'^(.*?\))', ' '.join(lines[:8]))
        head = re.sub(r'\s+', ' ', hm.group(1) if hm else ' '.join(lines[:2]))
        for bn, en, cmp_en, d, p, short in CMP_THANAS:   # the thana's block heading on its division's page
            if p == pid and any(l.replace(' ', '').startswith(short.replace(' ', '')) for l in lines[1:]):
                div_of[bn] = (dbn, head)
    missing = [t[0] for t in CMP_THANAS if t[0] not in div_of]
    if missing:
        warn('crime division not found for %s' % missing)
    save_raw('cmp_portal_glance.txt', glance, cmp_sentences(glance['text'], '১৯৭৮ সালের', 'থানাগুলো হলো', 'সিটি কর্পোরেশনের', 'সদর দপ্তর'))
    hp = {'url': CMP_SITE % 301, 'title': 'History of Chittagong Metropolitan police', 'updated': '', 'updated_raw': '(cmp.gov.bd pages are undated)'}
    save_raw('cmp_history.txt', hp, '\n'.join(hist_l))
    save_raw('cmp_crime_divisions.txt', {'url': CMP_SITE % 280, 'title': 'Contact Directory (division headings)', 'updated': '', 'updated_raw': ''},
             '\n'.join('%s বিভাগ: %s' % (v[0], v[1]) for v in dict((v[0], v) for v in div_of.values()).values()))
    areas = []
    for bn, en, cmp_en, d, p, short in CMP_THANAS:
        dv = div_of.get(bn, (d, ''))[0]
        areas.append(dict(level='thana', name_en=en, name_bn=bn, parent_level='district', parent_name_en='Chattogram', parent_name_bn='চট্টগ্রাম',
                          district_en='Chattogram', website='', source_key=key, source_url=CMP_PORTAL_GLANCE,
                          notes='Chattogram Metropolitan Police thana (CMP portal এক নজরে list of 16). cmp.gov.bd lists it as "%s Police Station"; '
                                'CMP crime division: %s বিভাগ (cmp.gov.bd contact directory). %s%s' % (
                                    cmp_en, dv, CMP_CC_NOTE,
                                    ' The station is at the old Char Lakshya union parishad building (cmp.gov.bd), i.e. outside the city.'
                                    if en == 'Karnaphuli' else '')))
    write_csv('areas.csv', AREA_COLS, areas)
    f = mp_fact(key, 'Chattogram Metropolitan Police', 'Chattogram')
    facts = [
        f('established', '1978-11-30', 'date', 'official', '1978', '"১৯৭৮ সালের ৩০ নভেম্বর প্রতিষ্ঠিত" (CMP portal এক নজরে); cmp.gov.bd: '
          '"30 November, 1978"; governed by the Chittagong Metropolitan Police Ordinance, 1978.', CMP_PORTAL_GLANCE),
        f('thana_count', '16', 'thanas', 'official', '', 'CMP portal এক নজরে names 16 thanas; cmp.gov.bd: "At present CMP has 16 police '
          'Stations"; the Chattogram DC portal lists the same 16 as "মহানগর" thanas.', CMP_PORTAL_GLANCE),
        f('thana_count_at_founding', '6', 'thanas', 'official', '1978', 'Started with six police stations, thirty outposts and six police '
          'boxes; divided into twelve thanas in 2000 (history).', CMP_SITE % 301),
        f('police_outposts', '31', 'outposts', 'official', '', '"16 police Stations, 31 outposts, 05 IC (Investigating Centre) and 6 police box" '
          '(history, undated).', CMP_SITE % 301),
        f('police_investigation_centres', '5', 'centres', 'official', '', 'Same sentence (history, undated).', CMP_SITE % 301),
        f('police_boxes', '6', 'boxes', 'official', '', 'Same sentence (history, undated).', CMP_SITE % 301),
        f('crime_division_count', '4', 'divisions', 'official', '', 'Contact directory: দক্ষিণ (Kotwali, Bakalia, Chawkbazar, Sadarghat), '
          'উত্তর (Panchlaish, Chandgaon, Bayezid Bostami, Khulshi), পশ্চিম (Double Mooring, Pahartali, Halishahar, Akbarshah), বন্দর (Bandar, '
          'Patenga, Karnaphuli, EPZ).', CMP_SITE % 280),
        f('area_at_founding_sq_mile', '128', 'sq mile', 'official', '1978', '"the area of 128 square mile & with its population of 10,00,000" '
          '(history).', CMP_SITE % 301),
        f('population_at_founding', '1000000', 'persons', 'estimate', '1978', 'Same sentence; approximate.', CMP_SITE % 301),
        f('personnel', '6458', 'persons', 'estimate', '', '"Total employee of CMP is about 6,458" (history, undated).', CMP_SITE % 301),
        f('jurisdiction', 'Most of Chattogram City Corporation', 'text', 'official', '', CMP_CC_NOTE, CMP_PORTAL_GLANCE),
    ]
    write_csv('facts.csv', FACT_COLS, facts)
    write_metro_manifest({'key': key, 'division': 'chattogram', 'kind': 'metro_police', 'city': CITY['city'],
                          'name': 'Chattogram Metropolitan Police (police.chittagongdiv.gov.bd and cmp.gov.bd)',
                          'organization': 'Chattogram Metropolitan Police, Bangladesh Police', 'source_type': 'government_portal', 'trust_level': 4,
                          'urls': [CMP_PORTAL_GLANCE, CMP_SITE % 301, CMP_SITE % 280] + [CMP_SITE % p for p in (287, 288, 289, 290)],
                          'accessed': ACCESSED, 'publication_date': None, 'license': None, 'license_url': None,
                          'attribution': 'Chattogram Metropolitan Police (police.chittagongdiv.gov.bd, cmp.gov.bd)',
                          'notes': 'Thana list from the CMP national-portal site (police.chittagongdiv.gov.bd, title "চট্রগ্রাম মেট্রোপলিটন পুলিশ"; '
                                   'এক নজরে updated %s); history figures and crime divisions from CMP\'s own site cmp.gov.bd (undated pages). '
                                   'CMP covers "most of" Chattogram City Corporation, but no source places individual thanas in it, so no '
                                   'thana carries a city corporation. Phone numbers are in CHATTOGRAM_METRO_POLICE_THANAS_2026. No Cumilla '
                                   'metropolitan police force was found (Cumilla city is policed by Cumilla District Police).' % glance['updated']})


# --- Khulna Division: Khulna Metropolitan Police (KMP national-portal site police.khulnadiv.gov.bd + the Khulna DC portal) -------
# KMP's own site kmp.police.gov.bd (linked from the divisional portal) answered HTTP 500 at access time. Thana list: the Khulna DC
# portal 'ভৌগলিক পরিচিতি' (8 'মেট্রোপলিটন থানা'; Bangla as printed there), English used here (HDX COD-AB 2020 thana spelling for
# Daulatpur, Khalishpur, Khan Jahan Ali, Khulna Sadar, Sonadanga; transliteration otherwise) and KMP's own name (its mobile-number
# list, see KHULNA_METRO_POLICE_THANAS_2026).
KMP_THANAS = [("দৌলতপুর", "Daulatpur", "দৌলতপুর"), ("খালিশপুর", "Khalishpur", "খালিশপুর"), ("খানজাহানআলী", "Khan Jahan Ali", "খানজাহান আলী"),
              ("সোনাডাঙ্গা", "Sonadanga", "সোনাডাঙ্গা মডেল"), ("কোতয়ালী", "Khulna Sadar", "খুলনা"), ("আড়ংঘাটা", "Aranghata", "আড়ংঘাটা"),
              ("হড়িণটানা", "Harintana", "হরিণটানা"), ("লবনচড়া", "Labanchara", "লবণচরা")]
KMP_GLANCE = "https://police.khulnadiv.gov.bd/pages/static-pages/6980f684a31054345f1ceb6e"   # এক নজরে (KMP portal, title 'পুলিশ কমিশনার')
KMP_OFFICERS = "https://police.khulnadiv.gov.bd/pages/officers"                             # officer cards (zone ACs)
KHULNA_DC_GEO = "https://khulna.gov.bd/pages/static-pages/69812047a31054345f1e0b98"          # DC portal 'ভৌগলিক পরিচিতি' (thana list)
KMP_CC_SENTENCE = "৩১টি সিটি কর্পোরেশন ওয়ার্ড এর অন্তর্ভূক্ত"
KMP_CC_NOTE = ("KMP's area includes the 31 wards of Khulna City Corporation and 5 unions ('৫টি ইউনিয়ন নিয়ে গঠিত। %s', KMP portal "
               "এক নজরে), but no official source places individual thanas in the city corporation (KMP's portal and the Khulna DC portal "
               "give no thana-to-ward list; KCC's own site could not be reached), so no thana carries a city corporation." % KMP_CC_SENTENCE)


def main_kmp():
    key = CITY['key']
    glance = page(KMP_GLANCE)
    geo = page(KHULNA_DC_GEO)
    gl = glance['text'].replace('\n', ' ')
    lines = geo['text'].split('\n')
    i = next((k for k, l in enumerate(lines) if l.startswith('মেট্রোপলিটন')), None)
    listed = [re.sub(r'\s*থানা$', '', re.sub(r'^[0-9০-৯]+\.\s*', '', l)) for l in lines[i + 1:i + 9]] if i is not None else []
    if sorted(listed) != sorted(t[0] for t in KMP_THANAS):
        warn('DC portal thana list differs from the table: %s' % listed)
    needles = ('১৯৮৪ সালের ১২ ই ডিসেম্বর', '১৯৮৬ সালের ১লা জুন', 'আয়তন ১২৭ বর্গ কিলোমিটার', 'জনসংখ্যা প্রায় ৩২ লক্ষ', 'দুটি বিভাগে বিভক্ত',
               '৪ টি জোন', '৮ টি থানা', '১৫টি আউট পোস্ট', '৩টি ক্যাম্প', '৯টি বক্স', '৫টি ইউনিয়ন', KMP_CC_SENTENCE)
    for n in needles:
        if n not in gl:
            warn('expected text not found on %s: %r' % (KMP_GLANCE, n))
    # zone names: the zone ACs' officer cards ('সহকারী পুলিশ কমিশনার (<x> জোন)')
    cards = to_text(get(KMP_OFFICERS))
    zones = list(dict.fromkeys(re.findall(r'সহকারী পুলিশ কমিশনার \((\S+) জোন\)', cards)))
    save_raw('kmp_portal_glance.txt', glance)
    save_raw('khulna_dc_metro_thanas.txt', geo, '\n'.join(lines[i:i + 9]) if i is not None else '(list not found)')
    save_raw('kmp_zones.txt', {'url': KMP_OFFICERS, 'title': 'কর্মকর্তাবৃন্দ (zone assistant commissioners)', 'updated': '', 'updated_raw': ''},
             '\n'.join('%s জোন' % z for z in zones) + '\n(officers\' names and numbers not copied)')
    areas = []
    for bn, en, kmp_bn in KMP_THANAS:
        areas.append(dict(level='thana', name_en=en, name_bn=bn, parent_level='district', parent_name_en='Khulna', parent_name_bn='খুলনা',
                          district_en='Khulna', website='', source_key=key, source_url=KHULNA_DC_GEO,
                          notes='Khulna Metropolitan Police thana (Khulna DC portal \'ভৌগলিক পরিচিতি\' list of 8 metropolitan thanas; spelling as '
                                'printed there). KMP calls it "%s থানা" (KMP mobile-number list)%s. %s' % (
                                    kmp_bn, '; HDX COD-AB and BBS 2022 call it Khulna Sadar' if en == 'Khulna Sadar' else
                                    ('' if en in ('Daulatpur', 'Khalishpur', 'Khan Jahan Ali', 'Sonadanga') else
                                     '; not in HDX COD-AB\'s 2020 thana points (English transliterated here)'), KMP_CC_NOTE)))
    write_csv('areas.csv', AREA_COLS, areas)
    f = mp_fact(key, 'Khulna Metropolitan Police', 'Khulna')
    u = KMP_GLANCE
    g_note = 'KMP portal এক নজরে (updated %s).' % glance['updated']
    facts = [
        f('established', '1984-12-12', 'date', 'official', '1984', '"সরকারি প্রঞ্জাপন অনুযায়ী ১৯৮৪ সালের ১২ ই ডিসেম্বর খুলনা মেট্রোপলিটন পুলিশ, '
          'খুলনা গঠিত হয়". ' + g_note, u),
        f('operations_started', '1986-06-01', 'date', 'official', '1986', '"১৯৮৬ সালের ১লা জুন এর কার্যক্রম শুরু হয়". ' + g_note, u),
        f('area_km2', '127', 'km2', 'official', '', '"এর আয়তন ১২৭ বর্গ কিলোমিটার"; no year. ' + g_note, u),
        f('population', '3200000', 'persons', 'estimate', '', '"জনসংখ্যা প্রায় ৩২ লক্ষ" (about 32 lakh); year and basis not stated. ' + g_note, u),
        f('crime_division_count', '2', 'divisions', 'official', '', '"দুটি বিভাগে বিভক্ত ১. দক্ষিণ বিভাগ ও ২. উত্তর বিভাগ"; which thana belongs to which '
          'division is not published. ' + g_note, u),
        f('zone_count', '4', 'zones', 'official', '', '"৪ টি জোন"; the portal\'s officer cards name the zones %s (thana-to-zone list not '
          'published). ' % ', '.join(z + ' জোন' for z in zones) + g_note, u),
        f('thana_count', '8', 'thanas', 'official', '', '"৮ টি থানা"; the Khulna DC portal lists the 8 metropolitan thanas by name. ' + g_note, u),
        f('police_outposts', '15', 'outposts', 'official', '', '"১৫টি আউট পোস্ট". ' + g_note, u),
        f('police_camps', '3', 'camps', 'official', '', '"৩টি ক্যাম্প". ' + g_note, u),
        f('police_boxes', '9', 'boxes', 'official', '', '"৯টি বক্স". ' + g_note, u),
        f('unions_in_jurisdiction', '5', 'unions', 'official', '', '"৫টি ইউনিয়ন" (not named). ' + g_note, u),
        f('city_corporation_wards_in_jurisdiction', '31', 'wards', 'official', '', '"%s" (Khulna City Corporation). ' % KMP_CC_SENTENCE + g_note, u),
        f('jurisdiction', 'All 31 wards of Khulna City Corporation and 5 unions', 'text', 'official', '', KMP_CC_NOTE, u),
    ]
    write_csv('facts.csv', FACT_COLS, facts)
    write_metro_manifest({'key': key, 'division': 'khulna', 'kind': 'metro_police', 'city': CITY['city'],
                          'name': 'Khulna Metropolitan Police (police.khulnadiv.gov.bd) and the Khulna DC portal thana list',
                          'organization': 'Khulna Metropolitan Police, Bangladesh Police', 'source_type': 'government_portal', 'trust_level': 4,
                          'urls': [KMP_GLANCE, KMP_OFFICERS, KHULNA_DC_GEO, 'https://kmp.police.gov.bd/'],
                          'accessed': ACCESSED, 'publication_date': None, 'license': None, 'license_url': None,
                          'attribution': 'Khulna Metropolitan Police (police.khulnadiv.gov.bd); Deputy Commissioner\'s Office, Khulna (khulna.gov.bd)',
                          'notes': 'Figures from the KMP national-portal site (police.khulnadiv.gov.bd, title "পুলিশ কমিশনার"; এক নজরে updated %s); '
                                   'thana names from the Khulna DC portal \'ভৌগলিক পরিচিতি\' (8 metropolitan thanas, page updated %s). KMP\'s own '
                                   'site kmp.police.gov.bd answered HTTP 500. KMP covers all 31 KCC wards and 5 unions, but no source places '
                                   'individual thanas in the city corporation, so no thana carries one. Phone numbers are in '
                                   'KHULNA_METRO_POLICE_THANAS_2026.' % (glance['updated'], geo['updated'])})


# --- Barishal Division: Barishal Metropolitan Police (BMP's own site bmp.police.gov.bd; bmp.gov.bd serves the same site) ---------
# BMP's national-portal site police.barisaldiv.gov.bd (title 'পুলিশ কমিশনারের কার্যালয়, বরিশাল বিভাগ') carries only the HQ address,
# officer cards and beat-officer pages; history, thana list, thana pages and the division-wise contact list are on bmp.police.gov.bd.
# English thana names: transliterations (Kotwali, Kaunia, Airport, Bandar).
BMP_B = 'https://bmp.police.gov.bd/'
BMP_HISTORY = BMP_B + 'history'           # ইতিহাস: founding, area, the 4 thanas, 4 outposts, 1 camp
BMP_CONTACT = BMP_B + 'contact-us'        # যোগাযোগ: division-wise tables (দক্ষিণ বিভাগ: Kotwali, Bandar; উত্তর বিভাগ: Kaunia, Airport)
BMP_THANAS = [  # (Bangla as in the history list, English, thana page on bmp.police.gov.bd)
    ('কোতয়ালী মডেল থানা', 'Kotwali', BMP_B + 'thana/7/kotwali-model-thana'),
    ('বন্দর থানা', 'Bandar', BMP_B + 'thana/10/bandar-thana'),
    ('কাউনিয়া থানা', 'Kaunia', BMP_B + 'thana/9/Kaunia-thana'),
    ('এয়ারপোর্ট থানা', 'Airport', BMP_B + 'thana/8/airport-thana'),
]
BCC_GLANCE = 'https://barishalcity.gov.bd/info/এক-নজরে-বরিশাল-সিটি'   # BCC: '৩টি থানা, ৩০টি ওয়ার্ড ও ২২৫টি মহল্লা' (thanas not named)


def bmp_text(url):
    """bmp.police.gov.bd page -> text of its <main> block."""
    t = re.sub(r'<script.*?</script>|<style.*?</style>', '', get(url), flags=re.S)
    m = re.search(r'<main.*?</main>', t, re.S)
    return to_text(m.group(0) if m else t)


def bmp_thana_page(url):
    """BMP thana page -> dict(area_km2, population, population_male, population_female, wards, admin sentence, census note)."""
    t = bmp_text(url)
    one = re.sub(r'\s+', ' ', t)
    out = {}
    m = re.search(r'আয়তন\s*:\s*([০-৯0-9.]+)\s*বর্গ কিমি', one)
    out['area_km2'] = asc(m.group(1)) if m else ''
    m = re.search(r'জনসংখ্যা\s*:\s*([০-৯0-9]+)\s*;\s*পুরুষ\s*([০-৯0-9]+)\s*,\s*মহিলা\s*([০-৯0-9]+)', one)
    out['population'], out['population_male'], out['population_female'] = (asc(m.group(1)), asc(m.group(2)), asc(m.group(3))) if m else ('', '', '')
    out['wards'] = sorted({int(asc(x)) for x in re.findall(r'ওয়ার্ড\s*নং\s*([০-৯0-9]+)', one)})
    m = re.search(r'প্রশাসন\s*:?\s*(.+?।)', one)
    out['admin'] = m.group(1).strip() if m else ''
    m = re.search(r'সূত্র\s*:?\s*(আদমশুমারি রিপোর্ট ২০০১[^।]*)', one)
    out['census'] = m.group(1).strip() if m else ''
    return out


def main_bmp():
    key = CITY['key']
    hist = re.sub(r'\s+', ' ', bmp_text(BMP_HISTORY))
    hist = re.sub(r'\s+([,.।)])', r'\1', re.sub(r'([(])\s+', r'\1', hist))
    needles = ('২০০৬ সালে', 'বরিশাল মেট্রোপলিটন পুলিশ অধ্যাদেশ ২০০৯', '১০ টি ইউনিয়ন', '০৪ টি থানা', '০৪ টি ফাড়ি', 'একটি ক্যাম্প', '৪৪৭')
    for n in needles:
        if n not in hist:
            warn('expected text not found on %s: %r' % (BMP_HISTORY, n))
    listed = re.findall(r'[১-৯]\s*\.\s*(\S+(?: মডেল)? থানা)', hist)
    if sorted(listed) != sorted(b for b, _, _ in BMP_THANAS):
        warn('BMP history thana list differs from the table: %s' % listed)
    outposts = re.findall(r'[১-৯]\s*\.\s*(\S+ পুলিশ ফাড়ি)', hist)
    camps = re.findall(r'[১-৯]\s*\.\s*(\S+(?: \S+)? পুলিশ ক্যাম্প)', hist)
    area = re.search(r'প্রায়\s*([০-৯]+)\s*\.?\s*([০-৯]+)\s*বর্গ কিঃমিঃ', hist)
    area_v = '%s.%s' % (asc(area.group(1)), asc(area.group(2))) if area else ''
    juris = re.search(r'(বরিশাল সিটি কর্পোরেশন ও বরিশাল সদর উপজেলার.+?ইউনিয়নের অধাংশ\s*\))', hist)
    # division of each thana: the contact page's headings (দক্ষিণ বিভাগ / উত্তর বিভাগ) precede the thanas' tables
    ct = get(BMP_CONTACT)
    heads = [nfc(re.sub(r'<[^>]+>', '', h)).strip() for h in re.findall(r'<h\d[^>]*>(.*?)</h\d>', ct, re.S)]
    div_of, cur = {}, None
    for h in heads:
        if h.endswith('বিভাগ') and h.split()[0] in ('দক্ষিণ', 'উত্তর'):
            cur = h
        elif h.endswith('থানা') and cur:
            div_of[h] = cur
    pages = {en: bmp_thana_page(u) for _, en, u in BMP_THANAS}
    save_raw('bmp_history.txt', {'url': BMP_HISTORY, 'title': 'বরিশাল মেট্রোপলিটন পুলিশের ইতিহাস', 'updated': '', 'updated_raw': ''},
             '\n'.join(p for p in re.split(r'(?<=[।])\s+', hist) if re.search(r'প্রতিষ্ঠিত|অধ্যাদেশ|ভৌগোলিক সীমানা|বর্গ কিঃমিঃ', p)) +
             '\nথানা: %s\nফাড়ি: %s\nক্যাম্প: %s' % (', '.join(listed), ', '.join(outposts), ', '.join(camps)))
    save_raw('bmp_thana_pages.txt', {'url': ', '.join(u for _, _, u in BMP_THANAS), 'title': 'BMP thana pages', 'updated': '', 'updated_raw': ''},
             '\n'.join('%s | %s | area %s km2 | population %s (m %s, f %s) | wards %s | %s | %s' % (
                 bn, div_of.get(next((h for h in div_of if h.split()[0][:3] == bn[:3]), ''), '-'), p['area_km2'] or '-', p['population'] or '-',
                 p['population_male'] or '-', p['population_female'] or '-', ', '.join(map(str, p['wards'])) or '-', p['admin'] or '-',
                 p['census'] or '-') for (bn, en, _), p in ((t, pages[t[1]]) for t in BMP_THANAS)))
    cc_note = ('BCC says the city consists of "৩টি থানা, ৩০টি ওয়ার্ড ও ২২৫টি মহল্লা" without naming the thanas (%s). BMP\'s thana pages '
               'list, from the BBS 2001 census, the wards and unions each thana covers: Kotwali wards 6, 8-26 and Jagua union; Kaunia '
               'wards 1-5, 7 and 3 unions; Airport wards 27-30 and 5 unions (3 of them in Babuganj upazila); Bandar 4 unions and part of '
               'Dapdapia union (Nalchity), no ward. No thana lies wholly inside Barishal City Corporation, so none is placed in it '
               '(area_en empty).' % BCC_GLANCE)
    areas = []
    for bn, en, u in BMP_THANAS:
        p = pages[en]
        dv = next((v for h, v in div_of.items() if h.split()[0][:3] == bn[:3]), '')
        areas.append(dict(level='thana', name_en=en, name_bn=re.sub(r'\s*(মডেল )?থানা$', '', bn), parent_level='district',
                          parent_name_en='Barishal', parent_name_bn='বরিশাল', district_en='Barishal', website=u, source_key=key,
                          source_url=BMP_HISTORY,
                          notes='Barishal Metropolitan Police thana (BMP history page list of 4 thanas: "%s"; its thana page: %s). %s'
                                'Wards listed on the thana page (BBS 2001): %s. %s' % (
                                    bn, u, ('BMP contact page: %s. ' % dv) if dv else '', ', '.join(map(str, p['wards'])) or 'none', cc_note)))
    write_csv('areas.csv', AREA_COLS, areas)
    f = mp_fact(key, 'Barishal Metropolitan Police', 'Barishal')
    u = BMP_HISTORY
    facts = [
        f('established', '2006', 'year', 'official', '2006', '"বরিশাল মেট্রোপলিটন পুলিশ - বিএমপি ২০০৬ সালে ... প্রতিষ্ঠিত হয়"; the page '
          'also cites the "বরিশাল মেট্রোপলিটন পুলিশ অধ্যাদেশ ২০০৯". BMP history page (undated).', u),
        f('area_km2', area_v, 'km2', 'official', '', '"প্রায় ৪৪৭.০২ বর্গ কিঃমিঃ আয়তন বিশিষ্ট"; no year. BMP history page.', u),
        f('thana_count', str(len(listed)), 'thanas', 'official', '', '"০৪ টি থানা": %s. BMP history page.' % ', '.join(listed), u),
        f('police_outposts', str(len(outposts)), 'outposts', 'official', '', '"০৪ টি ফাড়ি": %s. BMP history page.' % ', '.join(outposts), u),
        f('police_camps', str(len(camps)), 'camps', 'official', '', '"একটি ক্যাম্প": %s. BMP history page.' % ', '.join(camps), u),
        f('jurisdiction', 'Barishal City Corporation, 10 unions of Barishal Sadar upazila and 2.5 unions of Babuganj upazila', 'text',
          'official', '', '"%s" (BMP history page). %s' % (juris.group(1) if juris else '-', cc_note), u),
        f('crime_division_count', str(len(set(div_of.values()))), 'divisions', 'official', '', 'BMP contact page: %s.' % '; '.join(
            '%s: %s' % (d, ', '.join(h for h, v in div_of.items() if v == d)) for d in dict.fromkeys(div_of.values())), BMP_CONTACT),
    ]
    for bn, en, tu in BMP_THANAS:
        p = pages[en]
        note = 'BMP thana page (%s); %s' % (tu, ('figures in the page\'s table are from "%s"' % p['census']) if p['census'] else 'source not stated')
        if p['area_km2']:
            facts.append(f('area_km2', p['area_km2'], 'km2', 'official', '', note + '; no year for the area.', tu, level='thana', ename=en))
        if p['population']:
            facts.append(f('population', p['population'], 'persons', 'reported', '',
                           note + '; male %s, female %s; the page gives no year for this headline figure.' % (
                               p['population_male'], p['population_female']), tu, level='thana', ename=en))
    write_csv('facts.csv', FACT_COLS, [x for x in facts if x['value']])
    write_metro_manifest({'key': key, 'division': 'barishal', 'kind': 'metro_police', 'city': CITY['city'],
                          'name': 'Barishal Metropolitan Police (bmp.police.gov.bd) — thanas, history and jurisdiction',
                          'organization': 'Barishal Metropolitan Police, Bangladesh Police', 'source_type': 'government_portal', 'trust_level': 4,
                          'urls': [BMP_HISTORY, BMP_CONTACT] + [tu for _, _, tu in BMP_THANAS] + ['https://bmp.gov.bd/', 'https://police.barisaldiv.gov.bd/', BCC_GLANCE],
                          'accessed': ACCESSED, 'publication_date': None, 'license': None, 'license_url': None,
                          'attribution': 'Barishal Metropolitan Police (bmp.police.gov.bd)',
                          'notes': 'BMP\'s own site bmp.police.gov.bd (bmp.gov.bd serves the same site; the national-portal site '
                                   'police.barisaldiv.gov.bd has no thana list). History page (undated): founded 2006, 4 thanas, 4 outposts, '
                                   '1 camp, about 447.02 km2, jurisdiction BCC + 10 unions of Barishal Sadar + 2.5 unions of Babuganj. '
                                   'Thana pages give area and BBS 2001 population and wards. No thana is placed in Barishal City '
                                   'Corporation (each spans city wards and rural unions, Bandar has none). Phone numbers are in '
                                   'BARISHAL_METRO_POLICE_THANAS_2026. Beat-officer pages (officers\' names and personal mobiles) are not used.'})


# --- Sylhet Division: Sylhet Metropolitan Police (SMP's own site smp.police.gov.bd, WordPress; national-portal site police.sylhetdiv.gov.bd,
# title 'হোম | পুলিশ কমিশনার'). The national-portal 'এক নজরে' (English text) gives founding, area, jurisdiction and the six thanas; the
# Bangla thana names are the ones on SMP's own home page (its thana list links each name to Wikipedia; those links are not used).
SMP_PORTAL = 'https://police.sylhetdiv.gov.bd/'
SMP_GLANCE = SMP_PORTAL + 'pages/static-pages/696ca219c4774958d7b931b6'     # এক নজরে (About SMP, English; updated 2022-08-27)
SMP_CONTACT = SMP_PORTAL + 'pages/static-pages/696cb380c4774958d7ba127a'    # যোগাযোগ (HQ address)
SMP_HOME = 'https://smp.police.gov.bd/'
SMP_THANAS = [  # (English as in the 'এক নজরে' list, short English used here, Bangla prefix on SMP's home page)
    ('Kotwali Model Thana', 'Kotwali', 'কোতোয়ালী'), ('Jalalabad Thana', 'Jalalabad', 'জালালাবাদ'), ('Airport Thana', 'Airport', 'এয়ারপোর্ট'),
    ('South Surma Thana', 'South Surma', 'দক্ষিণ সুরমা'), ('Moglabazar Thana', 'Moglabazar', 'মোগলাবাজার'), ('Shahporan Thana', 'Shahporan', 'শাহপরান'),
]
SCC_GLANCE = 'https://scc.gov.bd/pages/static-pages/6922df09933eb65569e1f5f4'   # SCC এক নজরে (42 wards; no thanas named)
# police.sylhetdiv.gov.bd and scc.gov.bd chain fine; the Let's Encrypt intermediates (AIA URLs) are added as for the other Sylhet sources
SMP_INTERMEDIATES = ['http://yr1.i.lencr.org/', 'http://yr.i.lencr.org/']


def main_smp():
    AIA_INTERMEDIATES.extend(u for u in SMP_INTERMEDIATES if u not in AIA_INTERMEDIATES)   # before the first request
    key = CITY['key']
    gl = page(SMP_GLANCE)
    one = re.sub(r'\s+', ' ', gl['text'])
    def grab(pat):
        m = re.search(pat, one)
        if not m:
            warn('expected text not found on %s: %r' % (SMP_GLANCE, pat))
        return m
    formed = grab(r'Sylhet Metropolitan Police \(SMP\) was formed on (\d+) (\w+) (\d{4})')
    area = grab(r'The total area of SMP is about ([0-9.]+) Sq\.km')
    juris = grab(r'(The total area of SMP is about [0-9.]+ Sq\.km including [^.]+\.)')
    six = grab(r'SMP area is divided into (\w+) Police stations as ([^.]+)\.')
    aor = grab(r'The new AOR getting all administrative approval of the government was published on (\d+) ?(?:th|st|nd|rd)? (\w+) (\d{4})')
    full = grab(r'On (\d+) ?(\w+) (\d{4}), SMP starts its full strength operation')
    listed = [x.strip() for x in re.split(r',\s*|\s+and\s+', six.group(2))] if six else []
    if sorted(listed) != sorted(e for e, _, _ in SMP_THANAS):
        warn('SMP এক নজরে thana list differs from the table: %s' % listed)
    home = get(SMP_HOME)
    names = {}
    for a in re.findall(r'<a[^>]*>([^<]*থানা[^<]*)</a>', home):
        a = nfc(html.unescape(a)).strip()
        for _, en, bn in SMP_THANAS:
            if a.startswith(bn) and en not in names:
                names[en] = a
    for _, en, bn in SMP_THANAS:
        if en not in names:
            warn('thana %s not found in the SMP home page list' % bn)
    mon = {m: i for i, m in enumerate(['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
                                       'November', 'December'], 1)}
    iso = lambda m: '%s-%02d-%02d' % (m.group(3), mon.get(m.group(2), 0), int(m.group(1))) if m and mon.get(m.group(2)) else ''
    ct = page(SMP_CONTACT)
    hq = re.search(r'(বাড়ি নং-২২৮, সড়ক নং-১/এ, ব্লক-এফ শাহজালাল উপশহর, সিলেট)', ct['text'].replace('\n', ' '))
    save_raw('smp_ek_nojore.txt', gl, '\n'.join(x for x in (formed and formed.group(0), juris and juris.group(1), six and six.group(0),
                                                            aor and aor.group(0), full and full.group(0)) if x))
    save_raw('smp_home_thanas.txt', {'url': SMP_HOME, 'title': 'এসএমপি পুলিশ (home page thana list)', 'updated': '', 'updated_raw': ''},
             '\n'.join('%s | %s' % (en, names.get(en, '-')) for _, en, _ in SMP_THANAS))
    cc_note = ('SMP says its area includes "27 wards of Sylhet City Corporation, 08 Unions of Sylhet Sadar Upazila and 10 Unions of South '
               'Surma Upazilla" (%s, updated %s) but does not say which thana covers which wards or unions; Sylhet City Corporation (now 42 '
               'wards, %s) names no thanas. No official source places an SMP thana in the city corporation, so none is placed (area_en '
               'empty).' % (SMP_GLANCE, gl['updated'] or '?', SCC_GLANCE))
    areas = []
    for en_full, en, bn in SMP_THANAS:
        nm = names.get(en, bn + ' থানা')
        areas.append(dict(level='thana', name_en=en, name_bn=re.sub(r'\s*(মডেল )?থানা(, সিলেট)?$', '', nm), parent_level='district',
                          parent_name_en='Sylhet', parent_name_bn='সিলেট', district_en='Sylhet', website=SMP_HOME, source_key=key,
                          source_url=SMP_GLANCE,
                          notes='Sylhet Metropolitan Police thana (SMP এক নজরে: "%s"; Bangla name as on SMP\'s home page: "%s"). %s' % (
                              en_full, nm, cc_note)))
    write_csv('areas.csv', AREA_COLS, areas)
    f = mp_fact(key, 'Sylhet Metropolitan Police', 'Sylhet')
    u = SMP_GLANCE
    g = 'SMP এক নজরে (police.sylhetdiv.gov.bd, updated %s).' % (gl['updated'] or '?')
    facts = [
        f('established', iso(formed), 'date', 'official', formed.group(3), '"Sylhet Metropolitan Police (SMP) was formed on %s %s %s"; office '
          'activities from 26 October 2006; legal basis SMP ordinance 2006 and the Sylhet Metropolitan Police Act 2009. %s' % (
              formed.group(1), formed.group(2), formed.group(3), g), u) if formed else None,
        f('area_km2', area.group(1), 'km2', 'official', '', '"%s"; no year. %s' % (juris.group(1) if juris else area.group(0), g), u) if area else None,
        f('thana_count', str(len(listed)), 'thanas', 'official', '', '"SMP area is divided into six Police stations as %s". %s' % (
            six.group(2) if six else '-', g), u) if listed else None,
        f('jurisdiction', '27 wards of Sylhet City Corporation, 8 unions of Sylhet Sadar upazila and 10 unions of South Surma upazila', 'text',
          'official', '2011', '"%s" The jurisdiction (AOR) was published on %s and SMP operated with its 6 thanas from %s. %s %s' % (
              juris.group(1) if juris else '-', iso(aor) or '-', iso(full) or '-', cc_note, g), u) if juris else None,
    ]
    write_csv('facts.csv', FACT_COLS, [x for x in facts if x])
    write_metro_manifest({'key': key, 'division': 'sylhet', 'kind': 'metro_police', 'city': CITY['city'],
                          'name': 'Sylhet Metropolitan Police (police.sylhetdiv.gov.bd, smp.police.gov.bd) — thanas, founding and jurisdiction',
                          'organization': 'Sylhet Metropolitan Police, Bangladesh Police', 'source_type': 'government_portal', 'trust_level': 4,
                          'urls': [SMP_GLANCE, SMP_CONTACT, SMP_HOME, SMP_PORTAL, SCC_GLANCE],
                          'accessed': ACCESSED, 'publication_date': (gl['updated'] or '')[:10] or None, 'license': None, 'license_url': None,
                          'attribution': 'Sylhet Metropolitan Police (police.sylhetdiv.gov.bd; smp.police.gov.bd)',
                          'notes': 'SMP national-portal \'এক নজরে\' (English, updated %s): formed 26 Aug 2006, about 518.43 km2 including 27 '
                                   'SCC wards + 8 unions of Sylhet Sadar + 10 unions of South Surma, 6 thanas (Kotwali Model, Jalalabad, '
                                   'Airport, South Surma, Moglabazar, Shahporan), AOR published 10 May 2011. Bangla thana names from SMP\'s '
                                   'own site (home page list). No thana page, area or ward list per thana is published, so no thana is '
                                   'placed in Sylhet City Corporation. HQ address: %s (\'যোগাযোগ\'). Numbers are in '
                                   'SYLHET_METRO_POLICE_THANAS_2026.' % (gl['updated'] or '?', hq.group(1) if hq else '-')})



CITIES = {  # metro police force -> collector (Dhaka Division has two, DIVISIONS.md)
    'dhaka': dict(division='dhaka', folder='dhaka_metro_police', key='DHAKA_METRO_POLICE', city=[50001, 50002], run=main_dmp),
    'gazipur': dict(division='dhaka', folder='gazipur_metro_police', key='GAZIPUR_METRO_POLICE', city=50011, run=main_gmp),
    'chattogram': dict(division='chattogram', folder='chattogram_metro_police', key='CHATTOGRAM_METRO_POLICE', city=50003, run=main_cmp),
    'khulna': dict(division='khulna', folder='khulna_metro_police', key='KHULNA_METRO_POLICE', city=50004, run=main_kmp),
    'barishal': dict(division='barishal', folder='barishal_metro_police', key='BARISHAL_METRO_POLICE', city=50007, run=main_bmp),
    'sylhet': dict(division='sylhet', folder='sylhet_metro_police', key='SYLHET_METRO_POLICE', city=50006, run=main_smp),
}
CITY = None


def main():
    global DIVISION, HERE, RAW, ACCESSED, CITY, WARNINGS
    ap = argparse.ArgumentParser(description='Metropolitan police collector (default: Rajshahi Metropolitan Police)')
    ap.add_argument('--division', default='rajshahi', choices=DIVISION_CHOICES)
    ap.add_argument('--city', choices=sorted(CITIES), help='one force of a multi-city division (default: all of them)')
    ap.add_argument('--out', help='output folder (for a multi-city division only with a single --city)')
    a = ap.parse_args()
    if a.division not in SITES or a.city:   # multi-city divisions (Dhaka): one folder per metropolitan police
        cities = [c for c, v in CITIES.items() if v['division'] == a.division and (a.city is None or c == a.city)]
        if not cities:
            raise SystemExit('no metro police collector for division %r / city %r' % (a.division, a.city))
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
