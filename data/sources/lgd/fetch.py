#!/usr/bin/env python3
"""Local Government Division portal (lgd.gov.bd), Rajshahi Division -> LGD_2026.

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
# Local Government Division portal (lgd.gov.bd). What exists for Rajshahi Division as of 2026-11-12:
#  - "উপজেলা পরিষদের তালিকা" (upazila names per district, page updated 2023-05-31)
#  - "ইউনিয়ন পরিষদ" (national total of union parishads only, page updated 2023-05-15)
#  - The menu pages "সিটি কর্পোরেশন", "পৌরসভা", "জেলা পরিষদ", "উপজেলা পরিষদ" return HTTP 404.
#  - No downloadable pourashava / union list (Excel/PDF) was found on the portal.
# ---------------------------------------------------------------------------------------------------------------
KEY = 'LGD_2026'
B = 'https://lgd.gov.bd/pages/static-pages/'
U_UPZ = B + '6941401ec4774958d7b54a3f'
U_UP = B + '69414021c4774958d7b54bea'
MENU_404 = {'সিটি কর্পোরেশন': B + '6941401ec4774958d7b54a60', 'পৌরসভা': B + '69414020c4774958d7b54b38',
            'জেলা পরিষদ': B + '6941401fc4774958d7b54ab9', 'উপজেলা পরিষদ': B + '6941401fc4774958d7b54ac7'}

DISTRICTS = {'সিরাজগঞ্জ': 'Sirajganj', 'পাবনা': 'Pabna', 'বগুড়া': 'Bogura', 'রাজশাহী': 'Rajshahi', 'নাটোর': 'Natore',
             'জয়পুরহাট': 'Joypurhat', 'চাঁপাইনবাবগঞ্জ': 'Chapainawabganj', 'নওগাঁ': 'Naogaon'}
# LGD spelling (suffix " উপজেলা" removed for lookup) -> English name used in the seed
UPZ_EN = {
    'বেলকুচি': 'Belkuchi', 'চৌহালি': 'Chauhali', 'কামারখন্দ': 'Kamarkhand', 'কাজীপুর': 'Kazipur', 'রায়গঞ্জ': 'Raigonj',
    'শাহজাদপুর': 'Shahjadpur', 'সিরাজগঞ্জ': 'Sirajganj Sadar', 'তাড়াশ': 'Tarash', 'উল্লাপাড়া': 'Ullapara',
    'সুজানগর': 'Sujanagar', 'ঈশ্বরদী': 'Ishurdi', 'ভাঙ্গুড়া': 'Bhangura', 'পাবনা সদর': 'Pabna Sadar', 'বেড়া': 'Bera',
    'আটঘরিয়া': 'Atghoria', 'চাটমোহর': 'Chatmohar', 'সাঁথিয়া': 'Santhia', 'ফরিদপুর': 'Faridpur',
    'কাহালু': 'Kahaloo', 'বগুড়া সদর': 'Bogra Sadar', 'সারিয়াকান্দি': 'Shariakandi', 'শাজাহানপুর': 'Shajahanpur',
    'দুপচাচিঁয়া': 'Dupchanchia', 'আদমদিঘি': 'Adamdighi', 'নন্দিগ্রাম': 'Nondigram', 'সোনাতলা': 'Sonatala',
    'ধুনট': 'Dhunot', 'গাবতলী': 'Gabtali', 'শেরপুর': 'Sherpur', 'শিবগঞ্জ': 'Shibganj',
    'পবা': 'Paba', 'দুর্গাপুর': 'Durgapur', 'মোহনপুর': 'Mohonpur', 'চারঘাট': 'Charghat', 'পুঠিয়া': 'Puthia',
    'বাঘা': 'Bagha', 'গোদাগাড়ী': 'Godagari', 'তানোর': 'Tanore', 'বাগমারা': 'Bagmara',
    'নাটোর সদর': 'Natore Sadar', 'সিংড়া': 'Singra', 'বড়াইগ্রাম': 'Baraigram', 'বাগাতিপাড়া': 'Bagatipara',
    'লালপুর': 'Lalpur', 'গুরুদাসপুর': 'Gurudaspur', 'নলডাঙ্গা': 'Naldanga',
    'আক্কেলপুর': 'Akkelpur', 'কালাই': 'Kalai', 'ক্ষেতলাল': 'Khetlal', 'পাঁচবিবি': 'Panchbibi', 'জয়পুরহাট সদর': 'Joypurhat Sadar',
    'চাঁপাইনবাবগঞ্জ সদর': 'Chapainawabganj Sadar', 'গোমস্তাপুর': 'Gomostapur', 'নাচোল': 'Nachol', 'ভোলাহাট': 'Bholahat',
    'মহাদেবপুর': 'Mohadevpur', 'বদলগাছী': 'Badalgachi', 'পত্নিতলা': 'Patnitala', 'ধামইরহাট': 'Dhamoirhat',
    'নিয়ামতপুর': 'Niamatpur', 'মান্দা': 'Manda', 'আত্রাই': 'Atrai', 'রাণীনগর': 'Raninagar', 'নওগাঁ সদর': 'Naogaon Sadar',
    'পোরশা': 'Porsha', 'সাপাহার': 'Sapahar',
}


def main():
    upz = page(U_UPZ)
    up = page(U_UP)
    block = section(upz['text'], 'রাজশাহী বিভাগ', 'খুলনা বিভাগ')
    save_raw('upazila_list_rajshahi_division.txt', upz, block)
    save_raw('union_parishad_page.txt', up, section(up['text'], None, None))
    status_lines = []
    for label, u in MENU_404.items():
        st = status(u)
        status_lines.append('%s\t%s\tHTTP %s' % (label, u, st))
        if st == 200:
            warn('LGD menu page now exists, re-check for a list: %s %s' % (label, u))
    with open(os.path.join(RAW, 'menu_page_status.txt'), 'w', encoding='utf-8') as fh:
        fh.write('Accessed %s. LGD main-menu pages under "স্থানীয় সরকার প্রতিষ্ঠান":\n%s\n' % (ACCESSED, '\n'.join(status_lines)))

    # parse "district\n| u1, u2, ...\n|" pairs in the Rajshahi block
    lines = [l.strip() for l in block.split('\n')]
    areas, facts = [], []
    note = 'LGD "উপজেলা পরিষদের তালিকা", page updated %s' % upz['updated']
    i = 0
    while i < len(lines):
        if lines[i] in DISTRICTS and i + 1 < len(lines) and lines[i + 1].startswith('|'):
            dbn = lines[i]
            den = DISTRICTS[dbn]
            names = [nfc(x.strip()) for x in lines[i + 1].strip('| ').split(',') if x.strip()]
            for n in names:
                base = n[:-len(' উপজেলা')] if n.endswith(' উপজেলা') else n
                en = UPZ_EN.get(base, '')
                if not en:
                    warn('unmapped upazila ' + n)
                areas.append(dict(level='upazila', name_en=en, name_bn=n, parent_level='district', parent_name_en=den,
                                  parent_name_bn=dbn, district_en=den, upazila_en=en, source_key=KEY, source_url=U_UPZ,
                                  notes=('Printed as "%s" (sadar upazila). ' % n if n == 'সিরাজগঞ্জ' else '') +
                                  'English name from the seed, not from LGD. ' + note))
            facts.append(dict(entity_level='district', entity_name_en=den, district_en=den, fact='upazila_count',
                              value=str(len(names)), unit='upazilas', basis='official', year='2023', source_key=KEY,
                              source_url=U_UPZ, notes=note + '; predates Mokamtala (Bogura) upazila.'))
            i += 2
            continue
        i += 1
    if len(areas) != 67:
        warn('expected 67 upazilas for Rajshahi Division on the LGD list, got %d' % len(areas))
    expect(up, '৪৫৭১')
    facts.append(dict(entity_level='country', entity_name_en='Bangladesh', fact='union_parishad_count', value='4571',
                      unit='union_parishads', basis='official', year='2023', source_key=KEY, source_url=U_UP,
                      notes='National total (chairman count 4571 x 1) on LGD "ইউনিয়ন পরিষদ" page updated %s; no per-district '
                            'breakdown or union names; district names link to district portals.' % up['updated']))
    write_csv('areas.csv', AREA_COLS, areas)
    write_csv('facts.csv', FACT_COLS, facts)
    finish()


if __name__ == '__main__':
    main()
