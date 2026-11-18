# DGHS HRIS Facility Registry — Khulna Division

- **Source:** MoHFW HRIS Facility Registry public report "Organization List" (https://hris.mohfw.gov.bd/public/facility-registry/reports/organization-list), filtered to Khulna Division (`division_id[]=5`; every row's Division column is "Khulna"). No login; robots.txt allows all. Licence: none stated.
- **Method:** the Rajshahi collector, run as `python3 ../dghs_hris_facilities_raj_2026/fetch.py --division khulna` (accessed 2026-11-18). It is one Excel export request, so there is no partial state to resume. `raw/` holds the export (1.7 MB) with contact and address columns blanked for private and NGO rows, and non-`*.gov.bd` e-mails blanked for the other rows (see Contacts); `--division khulna --offline` rebuilds from it. Each row links to `/public/facility-registry/facilities/<id>/profile`. No file is near 20 MB (`places.csv` 2.9 MB), so nothing is split.

## Counts

4,821 active rows; 4,815 kept; 3,519 have coordinates (73%). Ownership: 2,646 public, 2,111 private, 44 government-autonomous, 7 international development agency, 7 government-semi-autonomous (source spells "semi-auonomous").

6 rows of types not in the existing mapping were left out (mapping unchanged): Port Health Office 1 (Khulna Port Health Office, hris:1801); Other 5 (Jessore ORS Program, hris:13004; four "DIC (Swajan-24 … 27) … FSW, SCI" drop-in centres in Jashore, Khulna and Satkhira, hris:24283, 24295, 24301, 24308).

| District | Total | Community clinic | Clinic | Diagnostic | Hospital | UHC | MCH | Other | With coords |
|---|---|---|---|---|---|---|---|---|---|
| Khulna | 815 | 216 | 286 | 205 | 74 | 9 | 1 | 24 | 577 (71%) |
| Jashore | 792 | 283 | 274 | 144 | 62 | 7 | 1 | 21 | 559 (71%) |
| Satkhira | 595 | 232 | 207 | 102 | 35 | 6 | 1 | 12 | 433 (73%) |
| Kushtia | 554 | 203 | 157 | 121 | 50 | 5 | 1 | 17 | 410 (74%) |
| Jhenaidah | 484 | 186 | 105 | 102 | 70 | 5 | 0 | 16 | 367 (76%) |
| Bagerhat | 476 | 211 | 140 | 87 | 22 | 8 | 0 | 8 | 374 (79%) |
| Chuadanga | 343 | 120 | 101 | 92 | 17 | 3 | 0 | 10 | 266 (78%) |
| Magura | 290 | 97 | 83 | 68 | 33 | 3 | 1 | 5 | 216 (74%) |
| Narail | 255 | 97 | 70 | 55 | 21 | 2 | 0 | 10 | 151 (59%) |
| Meherpur | 209 | 72 | 61 | 57 | 10 | 2 | 0 | 7 | 166 (79%) |
| (no district) | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 0 |

District names are kept as the registry spells them; all ten match the seed.

By category: 1,717 community clinic, 1,485 clinic, 1,033 diagnostic, 394 hospital, 50 UHC, 5 MCH; "Other": government 43, pourashava office 36, training 27, medical college 11, civil surgeon 10, technical (IHT) 3, city corporation office 1.

MCH = `health.medical_college_hospital`: Khulna MCH (hris:1800, 500 approved / 1,097 revenue beds, 22.829621, 89.537136), Jashore MCH, Kushtia MCH, Magura MCH and Satkhira MCH (500 approved beds each). Only Khulna and Kushtia MCH have coordinates.

UHCs: 50; 49 have coordinates (not Lohagara, Narail).

Khulna District by upazila or thana: upazilas Paikgachha 97, Dumuria 93, Koyra 55, Batiaghata 45, Dacope 45, Dighalia 39, Rupsa 37, Phultala 32, Terokhada 31; city thanas Khulna Sadar 172, Sonadanga 93, Khalishpur 30, Daulatpur 22, Khan Jahan Ali 10; none 14. 52 rows in the division have no upazila. `facts.csv` has 355 rows: counts of listed records by type per district, and per upazila or thana in Khulna District.

## Mapping

Same as for Rajshahi (see `../dghs_hris_facilities_raj_2026/REPORT.md`).

Upazila names are kept as the registry spells them except where they differ from the BANBEIS/IPEMIS Khulna outputs: Monirampur → Manirampur, Paikgacha → Paikgachha, Jhikargacha → Jhikargachha, Chaugacha → Chaugachha (original in `upazila_src`, 367 rows).

**Khulna city:** the registry's Upazila field is a Khulna Metropolitan Police thana for the city rows (Khulna Sadar, Sonadanga, Khalishpur, Daulatpur, Khan Jahan Ali; the newer KMP thanas Harintana, Labanchara and Aranghata do not occur). These stay in `upazila_en` as given and carry `admin_unit: metropolitan_thana` and the note "registry upazila field is a Khulna Metropolitan Police thana, kept as given (not an upazila)" (327 rows). Daulatpur is also an upazila of Kushtia: the thana rule applies only to rows in Khulna District, so Kushtia's Daulatpur (120 rows) stays an upazila (new `METRO_DISTRICT` setting in the collector; no effect on other divisions).

The registry's City Corporation field is kept in `extra_json.city_corporation`: Khulna City Corporation 292 rows (Khulna Sadar 158, Sonadanga 74, Khalishpur 30, Daulatpur 21, Khan Jahan Ali 8, no upazila 1). No row names a city corporation outside the division. Values "Upazilas of …" are not city corporations and are left out. Among them, 5 private rows name a district of another division, apparently mixed up with same-named upazilas there: "Upazilas of Gazipur" for 4 rows in Kaliganj, Jhenaidah (hris:21834, 21962, 34608, 35177) and "Upazilas of Manikganj" for 1 row in Daulatpur, Kushtia (hris:28069). They are not flagged in `notes` (rule unchanged).

No camps or special areas in this division.

## Contacts

Phones as before: only for non-private facilities (1,973 rows). E-mails: only `*.gov.bd` mailboxes of non-private facilities (2,242 rows, all `*.dghs.gov.bd`, mostly `cc.dghs.gov.bd` and `union.dghs.gov.bd`). As for Chattogram, 176 non-`*.gov.bd` addresses of non-private rows (free-mail, often a person's name, and misspelt domains) are not copied and are blanked in `raw/` too — they look like staff members' own mailboxes. 219 rows have a website. Private/NGO contacts and addresses are blanked in `raw/` and not collected; facility-head names are never collected.

## Data quality (flagged in `notes`)

- 88 rows had coordinates outside the generous division box (lat 21.5–24.3, lon 88.0–90.1) → dropped, original in notes; 1 row had unparseable coordinates → dropped.
- District check: `hdx_cod_ab_bgd_khulna` did not exist at run time, so the collector used the seed's Khulna district polygons (`data/seed/geo/districts.geojson`, division 10003).
  - 162 rows fall in another district than the registry gives. Most: registry Kushtia, point in Jhenaidah 63 (community clinics of Khoksa and Kumarkhali whose points lie well south of those upazilas); Jhenaidah → Satkhira 24; Satkhira → Khulna 8; Khulna → Bagerhat 7.
  - 215 fall outside the division polygons, mostly in border upazilas: Daulatpur (Kushtia) 44, Meherpur Sadar 31, Bheramara 19, Chuadanga Sadar 16. A few points lie in India, e.g. near lon 88.37.
  - All are kept and flagged "check". A re-run after the HDX Khulna folder exists will use its polygons and may give other counts.
- 317 rows look like duplicate registrations (same name, district and upazila; 313 of them private).
- 904 non-private rows lack coordinates, incl. 3 of the 5 MCHs.
- 2 raw rows have no district (HTC Khulna SMC USAID, NGO, hris:23042; College of Nursing, Khulna, hris:35925; both kept, flagged).
- Mobile numbers of public community clinics are kept as before (the registry contact of the clinic); some may be the health-care provider's own phone.
- Live, self-reported registry: re-runs will differ.

- **E-mail addresses in free-text fields (2026-11-18):** the registry also puts staff mailboxes in "Mailing Address" (and once in "Website Url"). Every non-`*.gov.bd` e-mail address is removed from those fields, in `places.csv` and in `raw/`; the rest of the text is kept (`strip_non_gov_mail` in `../dghs_hris_facilities_raj_2026/fetch.py`).
