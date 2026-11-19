# DGHS HRIS Facility Registry — Barishal Division

- **Source:** MoHFW HRIS Facility Registry public report "Organization List" (https://hris.mohfw.gov.bd/public/facility-registry/reports/organization-list), filtered to Barishal Division (`division_id[]=6`; every row's Division column is "Barishal"). No login; robots.txt allows all. Licence: none stated.
- **Method:** the Rajshahi collector, run as `python3 ../dghs_hris_facilities_raj_2026/fetch.py --division barishal` (accessed 2026-11-18). It is one Excel export request, so there is no partial state to resume. `raw/` holds the export (1.0 MB). Contact and address columns are blanked for private and NGO rows, and non-`*.gov.bd` e-mails are blanked for the other rows (108 blanked; see Contacts). `--division barishal --offline` rebuilds from it. Each row links to `/public/facility-registry/facilities/<id>/profile`. No file is near 20 MB (`places.csv` 1.7 MB), so nothing is split.

## Counts

2,885 active rows; 2,883 kept; 2,028 have coordinates (70%). Ownership: 1,637 public, 1,185 private, 29 government-semi-autonomous (source spells "semi-auonomous"), 26 government-autonomous, 3 international development agency, 2 NGO, 1 private charity.

2 rows of type "Other" were left out (mapping unchanged): Barisal Ors Program (hris:1964) and Shouljalia Fwc - Kathalia (hris:2745).

| District | Total | Community clinic | Clinic | Diagnostic | Hospital | UHC | MCH | Other | With coords |
|---|---|---|---|---|---|---|---|---|---|
| Barishal | 849 | 307 | 187 | 256 | 65 | 9 | 1 | 24 | 622 (73%) |
| Patuakhali | 591 | 238 | 126 | 163 | 40 | 7 | 1 | 16 | 423 (72%) |
| Bhola | 466 | 229 | 103 | 89 | 26 | 6 | 0 | 13 | 312 (67%) |
| Pirojpur | 448 | 174 | 124 | 109 | 26 | 6 | 0 | 9 | 280 (62%) |
| Barguna | 325 | 132 | 61 | 89 | 28 | 5 | 0 | 10 | 259 (80%) |
| Jhalokathi | 201 | 95 | 59 | 31 | 6 | 3 | 0 | 7 | 132 (66%) |
| (no district) | 2 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| Narsingdi (sic) | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |

District names are kept as the registry spells them; the six Barishal Division names match the seed.

By category: 1,175 community clinic, 738 diagnostic, 662 clinic, 191 hospital, 36 UHC, 2 MCH; "Other": government 32, pourashava office 24, training 13, civil surgeon 6, medical college 2, technical (IHT) 1, city corporation office 1.

MCH = `health.medical_college_hospital`:
- Sher-e-Bangla Medical College Hospital, Barishal (hris:1969, 1,000 approved / 600 revenue beds). Its registry coordinates 20.88, 88.1 lie outside the division and were dropped.
- Patuakhali Medical College Hospital (hris:36128, 500 / 500 beds, no coordinates).

Neither MCH has coordinates. The two medical colleges (Sher-E-Bangla Medical College, hris:1968; Patuakhali Medical College, hris:18779) are `education.medical_college`.

UHCs: 36; 33 have coordinates. The three without: Rangabali (none given), Indurkani and Nazirpur (registry points outside the division, dropped).

Barishal District by upazila: Barishal Sadar 266, Bakerganj 103, Gaurnadi 102, Wazirpur 72, Mehendiganj 66, Banaripara 58, Agailjhara 49, Muladi 49, Babuganj 40, Hizla 39; none 5. 13 rows in the division have no upazila. `facts.csv` has 247 rows: counts of listed records by type per district, and per upazila in Barishal District.

## Mapping

Same as for Rajshahi (see `../dghs_hris_facilities_raj_2026/REPORT.md`).

Upazila names are kept as the registry spells them except where they differ from the BANBEIS/IPEMIS Barishal outputs: Charfession → Char Fasson (135 rows), Kanthalia → Kathalia (35 rows); original in `upazila_src`.

**Barishal city:** the registry has no Barishal Metropolitan Police thanas in its Upazila field. The city rows are under the upazila "Barishal Sadar" with City Corporation "Barishal City Corporation", so no row has `admin_unit: metropolitan_thana`. The collector now knows the four BMP thanas (Kotwali, Airport, Kawnia, Bandar) for later runs. As for Khulna, the rule applies only to rows in Barishal District (`METRO_DISTRICT`), because Kotwali is also a town-thana name elsewhere.

The registry's City Corporation field is kept in `extra_json.city_corporation`: Barishal City Corporation 247 rows, all in Barishal Sadar. One more private row in Gaurnadi names "Cumilla City Corporation" (GREEN LIFE CLINIC & DIAGNOSTIC CENTRE, hris:21060); it is flagged "registry City Corporation 'Cumilla City Corporation' is not in Barishal Division — check". Values "Upazilas of …" are not city corporations and are left out.

One private row is registered in Barishal Division with District "Narsingdi" and Upazila "Manohardi" (LIFE CARE DIAGNOSTIC & (PVT) HOSPITAL, hris:30174). Its coordinates 24.17, 90.70 lie outside the division and were dropped. It is kept as given and flagged "Manohardi is an upazila of Narsingdi (Dhaka Division), not of Barishal Division — check".

No camps or special areas in this division.

## Contacts

Phones as before: only for non-private facilities (1,096 rows). E-mails: only `*.gov.bd` mailboxes of non-private facilities (1,477 rows, all `*.dghs.gov.bd`, mostly `cc.dghs.gov.bd` 1,068 and `union.dghs.gov.bd` 265). 108 non-`*.gov.bd` addresses of non-private rows (free-mail and misspelt domains) are not copied and are blanked in `raw/` too; they may be staff members' own mailboxes. 89 rows have a website. Private/NGO contacts and addresses are blanked in `raw/` and not collected; facility-head names are never collected.

## Data quality (flagged in `notes`)

- 122 rows had coordinates outside the generous division box (lat 21.6–23.2, lon 89.7–91.1). They were dropped, with the original in notes.
- District check: `hdx_cod_ab_bgd_barishal` did not exist at run time, so the collector used the seed's Barishal district polygons (`data/seed/geo/districts.geojson`, division 10004).
  - 80 rows fall in another district than the registry gives. Most common (registry → point): Barishal → Patuakhali 13; Pirojpur → Barguna 12; Barishal → Jhalokathi 10; Pirojpur → Jhalokathi 7. Nesarabad UHC is among them (point in Jhalokathi).
  - 36 fall outside the division polygons, e.g. Barishal Sadar 10, Bauphal 5 (incl. Bauphal UHC), Nazirpur 4, Hizla 3.
  - All are kept and flagged "check". A re-run after the HDX Barishal folder exists will use its polygons and may give other counts.
- Wazirpur UHC (hris:1988) has almost the same coordinates as Gaurnadi UHC (22.962, 90.226); the rules do not flag this.
- 291 rows look like duplicate registrations (same name, district and upazila; 285 of them private).
- 629 non-private rows lack coordinates, incl. both MCHs.
- 2 rows have no district: HTC Barisal SMC USAID (hris:23036) and DIC (Swajan-23) Barisal FSW, SCI (hris:23046). Both are NGO rows, kept and flagged.
- 11 more rows have a district but no upazila: the five district Drug Administration offices, Barishal Divisional Laboratory, RPTI Barishal, two NGO units in Barishal, Labaid Diagnostics Bhola, and Kuakata Mun.
- Mobile numbers of public community clinics are kept as before (the registry contact of the clinic); some may be the health-care provider's own phone.
- Live, self-reported registry: re-runs will differ.

- **E-mail addresses in free-text fields (2026-11-18):** the registry also puts staff mailboxes in "Mailing Address" (and once in "Website Url"). Every non-`*.gov.bd` e-mail address is removed from those fields, in `places.csv` and in `raw/`; the rest of the text is kept (`strip_non_gov_mail` in `../dghs_hris_facilities_raj_2026/fetch.py`).
