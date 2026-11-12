#!/usr/bin/env python3
"""Rajshahi City Corporation portal (erajshahi.portal.gov.bd) -> RCC_PORTAL_2026.

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


def main():
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


if __name__ == '__main__':
    main()
