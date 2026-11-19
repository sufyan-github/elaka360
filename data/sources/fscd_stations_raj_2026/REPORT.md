# FSCD_STATIONS_RAJ_2026 — Fire Service & Civil Defence, Rajshahi Division

**Source:** Fire Service and Civil Defence Directorate (fireservice.gov.bd), trust level 4 (government portal). Accessed 2026-11-12.

- "সকল ফায়ার স্টেশনের নম্বর" page → Rajshahi-division PDF (`raw/fscd_rajshahi_division_numbers.pdf`, Word export, created 2026-08-11), "নতুন যোগাযোগ নাম্বার" for every station and office.
- Control-room page (divisional control-room numbers), "চালুকৃত ফায়ার স্টেশন ও গাড়ী/পাম্পের সংখ্যা" (station counts by class, vehicles).
- Cross-check: Rajshahi divisional FSCD portal, fireservice.rajshahi.gov.bd ("মোবাইলে ফায়ার সার্ভিস", Rajshahi District only).

## What was collected
| | Rajshahi District | Division total |
|---|---|---|
| `emergency.fire_station` | 12 | 75 |
| `government` (FSCD office posts: DD/AD/DAD with official numbers) | 3 | 12 |
| `emergency` (Rajshahi divisional control room) | 1 | 1 |

Stations per district: Rajshahi 12, Chapainawabganj 5, Natore 7, Naogaon 11, Bogura 12, Joypurhat 5, Pabna 13, Sirajganj 10.

`facts.csv` (18): stations listed per district (counted); division station counts by class (special 2, A 7, B 46, B land-cum-river 0, C 17, river 1, total 73 — page undated); FSCD pumps 204, ambulances 20, all vehicles/pumps 558 in the Rajshahi column (summary dated 20 Oct 2024).

## Coverage
- Phone: 88/88 (one official mobile per station/office; the control room has 0721 landlines + mobile).
- Coordinates: none (not published). Address: none. Station class per station: not published (only division totals).
- `upazila_en` set for 63 stations whose name is an upazila name (inferred from the name; source gives district only). Not set for
  Rajshahi, Rajshahi North, University, Nowhata, Dayarampur, Bonpara, Kashinathpur, Greencity, Rooppur, Rooppur Modern,
  Baghabari River and North West stations.
- `name_en` empty (source is Bangla only).

## Data-quality issues
- The PDF's Bangla text layer is broken (glyph mapping), so names were **transcribed by hand from the rendered pages** and keyed by
  phone number; `fetch.py` re-reads the numbers from the live PDF (needs poppler `pdftotext`) and warns if any changed.
- Station count mismatch: the PDF lists 75 stations, the national counts page says 73 for Rajshahi division (page undated; likely older).
- 01730-336655: fireservice.gov.bd gives it as the **Rajshahi divisional control room** mobile; fireservice.rajshahi.gov.bd lists it
  as a second number of **Rajshahi Fire Station**. Kept on the control-room row; noted on the station row.
- Control-room landlines: fireservice.gov.bd prints 0721-774224 / 0721-774293 (old format); the divisional portal prints
  02588-854224 / 02588-854293 / 02588-852702 / 02588-861319 / 02588-851320 (in `extra_json`).
- Spelling differences between the PDF and the divisional portal ("বিশ্ববিদ্যালয়" vs "রাজশাহী বিশ্ববিদ্যালয়", "দুর্গাপুর" vs
  "দূর্গাপুর") kept in `extra_json.name_on_divisional_portal`. Sirajganj Fire Station number printed without hyphen (01901022353).
- The division page spells Naogaon "নঁওগা"; the PDF "নওগাঁ".
- Not duplicated: national hotline 102 (already in `HOTLINES`).

## Pilot places
No match. "বিশ্ববিদ্যালয় ফায়ার স্টেশন" (Rajshahi University fire station) is related to University of Rajshahi but is a separate place.

## Licence
No licence stated on fireservice.gov.bd → `license: null`.
