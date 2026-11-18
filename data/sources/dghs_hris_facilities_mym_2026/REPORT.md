# DGHS HRIS Facility Registry — Mymensingh Division

- **Source:** MoHFW HRIS Facility Registry public report "Organization List" (https://hris.mohfw.gov.bd/public/facility-registry/reports/organization-list), filtered to Mymensingh Division (`division_id[]=8`; every row's Division column is "Mymensingh"). No login; robots.txt allows all. Licence: none stated.
- **Method:** the Rajshahi collector, run as `python3 ../dghs_hris_facilities_raj_2026/fetch.py --division mymensingh` (accessed 2026-11-18), then rebuilt with `--offline` after the Mymensingh spellings were added. It is one Excel export request, so there is no partial state to resume; on a failed export nothing is written. `raw/` holds the export (1.0 MB). Contact and address columns are blanked for private and NGO rows, and non-`*.gov.bd` e-mails are blanked for the other rows (86 blanked; see Contacts). `--division mymensingh --offline` rebuilds from it. Each row links to `/public/facility-registry/facilities/<id>/profile`. No file is near 20 MB (`places.csv` 1.7 MB), so nothing is split.

## Counts

2,791 active rows; 2,786 kept; 1,872 have coordinates (67%). Ownership of the kept rows: 1,754 public, 939 private, 87 government-autonomous, 6 government-semi-autonomous (source spells "semi-auonomous").

5 rows were left out (mapping unchanged):
- Type "Upazila Field Service", new in this division and not covered by the mapping: Upazila Family Planning Office, Melandah (hris:23368).
- Type "Other": Sherpur District Jail Hospital (hris:24887), Jamalpur District Jail Hospital (hris:24888), "Netrokona, MC&WC" (hris:24959) and "Sherpur Sadar, MC&WC" (hris:24960). The 2 rows of type "Jail Hospital" and the 5 of type "Maternal & Child Welfare Centre (MCWC)" are kept.

| District | Total | Community clinic | Clinic | Diagnostic | Hospital | UHC | MCH | Other | With coords |
|---|---|---|---|---|---|---|---|---|---|
| Mymensingh | 1,197 | 544 | 228 | 270 | 114 | 12 | 1 | 28 | 883 (74%) |
| Jamalpur | 663 | 303 | 143 | 118 | 66 | 6 | 1 | 26 | 448 (68%) |
| Netrakona\* | 506 | 249 | 121 | 82 | 33 | 9 | 1 | 11 | 319 (63%) |
| Sherpur | 419 | 171 | 109 | 90 | 31 | 4 | 0 | 14 | 222 (53%) |
| (no district) | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |

\* District names are kept as the registry spells them, as for the earlier divisions; the registry writes "Netrakona" (seed, BANBEIS and IPEMIS outputs: Netrokona). The district check treats the two spellings as the same district.

By category: 1,267 community clinic, 601 clinic, 560 diagnostic, 244 hospital, 31 UHC, 3 MCH; "Other": government 32, pourashava office 26, training 11, medical college 4, civil surgeon 4, technical (IHT) 2, city corporation office 1.

MCH = `health.medical_college_hospital`:
- Mymensingh Medical College Hospital (hris:392, 1,000 approved / 1,000 revenue beds), with coordinates.
- Jamalpur Medical College Hospital (hris:33794, 500 / 500) and Netrakona Medical College Hospital (hris:36130, 500 / 500) have no coordinates.
- No MCH row for Sherpur District.

Medical colleges (`education.medical_college`, 4, registry names): Mymensingh Medical College, Community Based Medical College (private), Jamalpur Medical College, Netrokona Medical College (no upazila given).

UHCs: 31 (Mymensingh 12, Netrakona 9, Jamalpur 6, Sherpur 4; no Sadar upazila has one); 30 have coordinates.
- Durgapur UHC (hris:2248): point 24.448, 88.769, in Rajshahi Division (where another Durgapur upazila lies), dropped.
- Kendua UHC (24.391, 90.493) and Purbadhala UHC (24.56, 90.36) points fall in Mymensingh District (flagged).

District hospitals (type "District/General Hospital"): Jamalpur 250 Beded General Hospital (hris:203), Netrokona District Hospital (hris:491), Sherpur 250 bed District Sadar Hospital (hris:571). None for Mymensingh District. Also kept as hospitals: Bhaluka Trauma Center (hris:346) and Combined Military Hospital, Mymensingh (hris:24650).

Mymensingh District by upazila: Mymensingh Sadar 304, Bhaluka 111, Gafargaon 93, Fulbaria 91, Phulpur 77, Muktagacha 76, Iswarganj 75, Trishal 75, Nandail 70, Gouripur 60, Haluaghat 57, Tarakanda 57, Dhobaura 38, none 13.

24 rows in the division have no upazila. `facts.csv` has 233 rows: counts of listed records by type for the division (1) and per district (102), and per upazila in Mymensingh District (130).

## Mapping

Same as for Rajshahi (see `../dghs_hris_facilities_raj_2026/REPORT.md`).

Upazila names are mapped to the seed's English spellings (also used by the BANBEIS/IPEMIS Mymensingh outputs); the original is in `upazila_src`:
- Melandaha → Melandah (77 rows), Ishwarganj → Iswarganj (75), Sreebardi → Sreebordi (67), Bakshiganj → Bokshiganj (60), Dewanganj → Dewangonj (53), Nakla → Nokla (53), Mohanganj → Mohongonj (41).
- The registry uses two spellings for two upazilas: Gaffargaon (24) next to Gafargaon (69), and Gauripur (12) next to Gouripur (48). Both are mapped to the seed names Gafargaon and Gouripur.
- The registry already uses Tarakanda (57 rows).
- One row has upazila "Monoharganj" in Netrakona District: Popular Diagnostic Center (hris:39818, private, point 24.879, 90.982). Monoharganj is an upazila of Cumilla. The point lies in Netrakona District and the row is probably meant for Mohanganj, but it is kept as given and flagged "Monoharganj is an upazila of Cumilla (Chattogram Division), not of Netrakona — check".

**Mymensingh city:** the registry's Upazila field has no metropolitan-police thana for Mymensingh. All values are the 35 upazilas of the division (plus the one "Monoharganj" row). So no row has `admin_unit: metropolitan_thana`, and the collector has no thana list or `METRO_DISTRICT` for this division. The city lies in the upazila Mymensingh Sadar.

The registry's City Corporation field is kept in `extra_json.city_corporation`:
- Mymensingh City Corporation: 71 rows, all in Mymensingh Sadar. They include Mymensingh Medical College and Hospital, the civil surgeon office and the City Corporation office (hris:40271).
- One row names "Khulna City Corporation": Asian General Hospital (Pvt), Jamalpur Sadar (hris:25324). It is flagged "registry City Corporation 'Khulna City Corporation' is not in Mymensingh Division — check".
- Values "Upazilas of …" are not city corporations and are left out.

No camps, tea gardens or other special areas in this division.

## Contacts

Phones as before: only for non-private facilities (1,307 rows).

E-mails: only `*.gov.bd` mailboxes of non-private facilities (1,585 rows, all `*.dghs.gov.bd`; mostly `cc.dghs.gov.bd` 1,177, `union.dghs.gov.bd` 244, `usc.dghs.gov.bd` 105, `uhfpo.dghs.gov.bd` 37). 86 non-`*.gov.bd` addresses of non-private rows (free-mail and misspelt domains) are not copied and are blanked in `raw/` too; they may be staff members' own mailboxes.

47 rows have a website. Private/NGO contacts and addresses are blanked in `raw/` and not collected; facility-head names are never collected.

## Data quality (flagged in `notes`)

- 84 rows had coordinates outside the generous division box (lat 24.0–25.5, lon 89.6–91.3). They were dropped, with the original in notes. 2 more had a latitude and no longitude (dropped).
- District check used `../hdx_cod_ab_bgd_mymensingh/boundaries.geojson` (4 districts; that folder was written by its own collector on 2026-11-18, during this run).
  - 87 rows fall in another district than the registry gives (registry → point): Netrakona → Mymensingh 63, Mymensingh → Sherpur 15, Sherpur → Jamalpur 5, and 1 each Jamalpur → Sherpur, Jamalpur → Netrakona, Jamalpur → Mymensingh, Sherpur → Mymensingh.
  - 153 fall outside the division polygons. By registry upazila: Gafargaon 30, Muktagacha 26, Bhaluka 25, Trishal 14, Fulbaria 13, Nandail 8, Mymensingh Sadar 7. Checked against the seed district polygons, 102 of them lie in Tangail and 36 in Gazipur. 135 are public facilities.
  - All are kept and flagged "check".
- 181 rows look like duplicate registrations (same name, district and upazila; 177 of them private).
- 715 non-private rows lack coordinates, incl. two of the three MCHs.
- 1 row has no district: Mymensingh Nursing College, Mymensingh (hris:35914). It is kept and flagged. A second Mymensingh Nursing College row (hris:33755) has a district.
- 23 more rows have a district but no upazila, e.g. the two Institutes of Health Technology, nursing colleges and institutes, Netrokona Medical College, the Mymensingh Divisional Office, the four district Drug Administration offices, Islampur Municipality and NGO units (SCI DICs, HTC Mymensingh).
- The registry puts Netrokona Nursing Institute (hris:35963) and Nursing and Midwifery College, Jamalpur (hris:35964) in Mymensingh District; kept as given.
- Mobile numbers of public community clinics are kept as before (the registry contact of the clinic); some may be the health-care provider's own phone.
- Live, self-reported registry: re-runs will differ.

- **E-mail addresses in free-text fields (2026-11-18):** the registry also puts staff mailboxes in "Mailing Address" (and once in "Website Url"). Every non-`*.gov.bd` e-mail address is removed from those fields, in `places.csv` and in `raw/`; the rest of the text is kept (`strip_non_gov_mail` in `../dghs_hris_facilities_raj_2026/fetch.py`).
