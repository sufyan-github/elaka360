# DGHS HRIS Facility Registry — Sylhet Division

- **Source:** MoHFW HRIS Facility Registry public report "Organization List" (https://hris.mohfw.gov.bd/public/facility-registry/reports/organization-list), filtered to Sylhet Division (`division_id[]=7`; every row's Division column is "Sylhet"). No login; robots.txt allows all. Licence: none stated.
- **Method:** the Rajshahi collector, run as `python3 ../dghs_hris_facilities_raj_2026/fetch.py --division sylhet` (accessed 2026-11-18), then rebuilt with `--offline` after the Sylhet spellings were added. It is one Excel export request, so there is no partial state to resume; on a failed export nothing is written. `raw/` holds the export (0.8 MB). Contact and address columns are blanked for private and NGO rows, and non-`*.gov.bd` e-mails are blanked for the other rows (59 blanked; see Contacts). `--division sylhet --offline` rebuilds from it. Each row links to `/public/facility-registry/facilities/<id>/profile`. No file is near 20 MB (`places.csv` 1.3 MB), so nothing is split.

## Counts

2,230 active rows; 2,226 kept; 1,507 have coordinates (68%). Ownership: 1,380 public, 800 private, 31 government-autonomous, 6 government-semi-autonomous (source spells "semi-auonomous"), 3 international development agency, 3 NGO, 1 private charity, 1 private commercial, 1 private personal occupational business.

4 rows were left out (mapping unchanged):
- Govt. Unani & Ayurvedic Medical College Hospital, Sylhet (hris:2194), type "College of Alternative Medicine", which the mapping does not cover. BANBEIS lists the college (EIIN 133384, `education.medical_college`).
- Type "Other": DIC (Swajan-22) Ambarkhana FSW, SCI (hris:24282); DIC (Swajan-23) Kadamtali FSW, SCI (hris:24296); Sunamganj District Jail Hospital (hris:24902). The 5 rows of type "Jail Hospital" are kept.

| District | Total | Community clinic | Clinic | Diagnostic | Hospital | UHC | MCH | Other | With coords |
|---|---|---|---|---|---|---|---|---|---|
| Sylhet | 744 | 276 | 196 | 155 | 84 | 12 | 1 | 20 | 497 (67%) |
| Sunamganj | 507 | 271 | 106 | 92 | 14 | 10 | 1 | 13 | 313 (62%) |
| Habiganj | 488 | 221 | 96 | 108 | 42 | 8 | 1 | 12 | 335 (69%) |
| Maulvibazar\* | 485 | 187 | 120 | 114 | 47 | 6 | 0 | 11 | 362 (75%) |
| (no district) | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 0 |

\* District names are kept as the registry spells them, as for the earlier divisions; the registry writes "Maulvibazar" (seed, BANBEIS and IPEMIS outputs: Moulvibazar). The district check treats the two spellings as the same district.

By category: 955 community clinic, 519 clinic, 469 diagnostic, 187 hospital, 36 UHC, 3 MCH; "Other": pourashava office 19, government 17, medical college 7, training 7, civil surgeon 4, technical (IHT) 1, city corporation office 1, university 1 (Sylhet Medical University, hris:40652, type "Medical University", no coordinates).

MCH = `health.medical_college_hospital`:
- Sylhet MAG Osmani Medical College Hospital (hris:2186, 900 approved / 630 revenue beds). Its registry coordinates are 24, 92 (whole degrees). They lie inside the generous box but outside the division polygons, so they are kept and flagged "check". They are not the hospital's location.
- Hobigonj Medical College Hospital, Habiganj (hris:35909, 500 / 500 beds) and Sunamganj Medical College Hospital (hris:40053, no beds given) have no coordinates.

Medical colleges (`education.medical_college`, 7, registry names): Sylhet MAG Osmani Medical College, Jalalabad Razib-Rabeya Medical College, North East Medical College, Sylhet Women Medical College, Parkview Medical College, Habiganj Medical College, Sunamganj Medical College.

UHCs: 36; 33 have coordinates. The three without:
- Osmani Nagar: none given.
- Companiganj (hris:2200): point 22.52, 91.16, outside the division box, dropped.
- Biswambarpur (hris:2118): point 23.77, 90.40, in Dhaka, dropped.

Fenchuganj UHC's point lies outside the division polygons (flagged).

District hospitals: Sylhet Shahid Shamsuddin Ahmed (hris:2187; its registry point 24.63, 91.52 falls in Habiganj, flagged), plus the Habiganj, Moulvibazar and Sunamganj 250-bed hospitals.

Sylhet District by upazila or thana:
- Upazilas: Sylhet Sadar 230, Beanibazar 61, Golapganj 57, Kanaighat 52, Zakiganj 50, Gowainghat 43, Dakshin Surma 38, Bishwanath 37, Osmaninagar 33, Jaintiapur 30, Balaganj 29, Companiganj 24, Fenchuganj 22.
- SMP thanas: Kotwali 7, Shahparan 4, Airport 1.
- None: 26.

37 rows in the division have no upazila. `facts.csv` has 233 rows: counts of listed records by type per district, and per upazila or thana in Sylhet District.

## Mapping

Same as for Rajshahi (see `../dghs_hris_facilities_raj_2026/REPORT.md`).

Upazila names are kept as the registry spells them, except where they differ from the BANBEIS/IPEMIS Sylhet outputs: Maulvibazar Sadar → Moulvibazar Sadar (127 rows), Dharampasha → Dharmapasha (48), Sulla → Shalla (23). The original is in `upazila_src`. The registry already uses Shantiganj (38 rows; formerly Dakshin Sunamganj). It has no Madhyanagar unit (the newer upazila split from Dharmapasha), so facilities there are probably under Dharmapasha.

**Sylhet city:** the registry's Upazila field has three Sylhet Metropolitan Police thanas in Sylhet District: Kotwali 7, Shahparan 4, Airport 1. These 12 rows include MAG Osmani Medical College and Hospital, the district hospital, the civil surgeon office, the City Corporation office and CMH Jalalabad Cantonment. They are kept as given with `admin_unit: metropolitan_thana` and the note "registry upazila field is a Sylhet Metropolitan Police thana, kept as given (not an upazila)". The rule applies only to rows in Sylhet District (`METRO_DISTRICT`). The collector also knows Jalalabad and Moglabazar (none occur).

Dakshin Surma is both an SMP thana and an upazila of Sylhet District. The registry value is kept as the upazila (38 rows, no `admin_unit`). 35 of them also carry City Corporation "Sylhet City Corporation". These are flagged "registry upazila 'Dakshin Surma' with City Corporation 'Sylhet City Corporation': may be the Sylhet Metropolitan Police thana Dakshin Surma rather than the upazila (kept as the upazila) — check".

The registry's City Corporation field is kept in `extra_json.city_corporation`: Sylhet City Corporation 56 rows (Dakshin Surma 35, Sylhet Sadar 12, Kotwali 6, Shahparan 2, Airport 1). No row names a city corporation outside the division. Values "Upazilas of …" are not city corporations and are left out.

Tea gardens: 11 community clinics are named "… Cha Bagan Community Clinic" (8 in Sreemangal; Fenchuganj, Kanaighat and Sylhet Sadar 1 each). They are kept as the registry lists them, with the same rules as other community clinics.

No camps or special areas in this division.

## Contacts

Phones as before: only for non-private facilities (915 rows).

E-mails: only `*.gov.bd` mailboxes of non-private facilities (1,281 rows, all `*.dghs.gov.bd`; mostly `cc.dghs.gov.bd` 896, `union.dghs.gov.bd` 235, `usc.dghs.gov.bd` 79). 59 non-`*.gov.bd` addresses of non-private rows (free-mail and misspelt domains) are not copied and are blanked in `raw/` too; they may be staff members' own mailboxes.

71 rows have a website. Private/NGO contacts and addresses are blanked in `raw/` and not collected; facility-head names are never collected.

## Data quality (flagged in `notes`)

- 40 rows had coordinates outside the generous division box (lat 23.9–25.3, lon 90.9–92.6). They were dropped, with the original in notes. 3 more had an unparseable latitude and no longitude (dropped).
- District check used `../hdx_cod_ab_bgd_sylhet/boundaries.geojson` (4 districts).
  - 18 rows fall in another district than the registry gives (registry → point): Maulvibazar → Habiganj 5, Sylhet → Habiganj 4, Sylhet → Sunamganj 3, Habiganj → Moulvibazar 2, Maulvibazar → Sylhet 2, Sylhet → Moulvibazar 1, Habiganj → Sunamganj 1.
  - 85 fall outside the division polygons, mostly in Habiganj: Habiganj Sadar 16, Lakhai 16, Madhabpur 16, Baniachong 6, Ajmiriganj 5, Shayestaganj 5.
  - All are kept and flagged "check".
- 87 rows look like duplicate registrations (same name, district and upazila; 85 of them private).
- 540 non-private rows lack coordinates, incl. two of the three MCHs.
- 2 rows have no district: Sylhet Nursing College, Sylhet (hris:35920) and HTC Sylhet SMC USAID (hris:23045). Both are kept and flagged. A second Sylhet Nursing College row (hris:33757) has a district.
- 35 more rows have a district but no upazila, e.g. Parkview Medical College, Sylhet Institute of Health Technology, Sylhet Divisional Health Office, the three district Drug Administration offices, Sylhet District Jail Hospital and NGO urban clinics (PHCC, BRAC, SCI units).
- Mobile numbers of public community clinics are kept as before (the registry contact of the clinic); some may be the health-care provider's own phone.
- Live, self-reported registry: re-runs will differ.

- **E-mail addresses in free-text fields (2026-11-18):** the registry also puts staff mailboxes in "Mailing Address" (and once in "Website Url"). Every non-`*.gov.bd` e-mail address is removed from those fields, in `places.csv` and in `raw/`; the rest of the text is kept (`strip_non_gov_mail` in `../dghs_hris_facilities_raj_2026/fetch.py`).
