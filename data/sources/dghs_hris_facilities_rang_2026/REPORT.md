# DGHS HRIS Facility Registry — Rangpur Division

- **Source:** MoHFW HRIS Facility Registry public report "Organization List" (https://hris.mohfw.gov.bd/public/facility-registry/reports/organization-list), filtered to Rangpur Division (`division_id[]=4`). No login; robots.txt allows all. Licence: none stated.
- **Method:** the Rajshahi collector, run as `python3 ../dghs_hris_facilities_raj_2026/fetch.py --division rangpur` (accessed 2026-11-17). It requests the Excel export with the same fixed column set. `raw/` holds that export (1.5 MB) with contact and address columns blanked for private and NGO rows; `--division rangpur --offline` rebuilds from it. Each row links to `/public/facility-registry/facilities/<id>/profile`.

## Counts

4,026 active rows; 4,023 kept. 3 rows of type "Other" were left out: an ORS programme and two NGO drop-in centres. 2,876 rows have coordinates (71%). Ownership: 2,669 public, 1,281 private, 42 government-autonomous, 17 government-semi-autonomous (the source spells it "semi-auonomous"), 13 international development agency, 1 private commercial.

| District | Total | Community clinic | Clinic | Diagnostic | Hospital | UHC | MCH | Other | With coords |
|---|---|---|---|---|---|---|---|---|---|
| Rangpur | 765 | 312 | 173 | 149 | 99 | 7 | 1 | 24 | 532 (70%) |
| Dinajpur | 733 | 335 | 189 | 126 | 47 | 12 | 1 | 23 | 547 (75%) |
| Gaibandha | 632 | 322 | 126 | 144 | 24 | 6 | 0 | 10 | 475 (75%) |
| Kurigram | 589 | 297 | 155 | 88 | 21 | 8 | 0 | 20 | 417 (71%) |
| Lalmonirhat | 323 | 180 | 79 | 45 | 8 | 4 | 0 | 7 | 233 (72%) |
| Nilphamari | 397 | 196 | 99 | 52 | 31 | 5 | 1 | 13 | 288 (73%) |
| Panchagarh | 217 | 110 | 74 | 14 | 7 | 4 | 0 | 8 | 144 (66%) |
| Thakurgaon | 367 | 147 | 127 | 43 | 38 | 4 | 0 | 8 | 240 (65%) |

MCH means `health.medical_college_hospital`: Rangpur MCH, Dinajpur MCH and Nilphamari MCH. "Other" covers:

| Category | Rows |
|---|---|
| Health offices (`government`) | 50 |
| Municipal health units (`government.pourashava_office`) | 28 |
| Nursing and training institutes (`education.training_center`) | 17 |
| Civil surgeon offices (`government.civil_surgeon`) | 8 |
| Medical colleges (`education.medical_college`) | 7 |
| IHTs (`education.technical`) | 2 |
| City corporation (`government.city_corporation_office`) | 1 |

There is one upazila health complex (UHC) per upazila except the Sadar upazilas, which is 50 in total. 47 of the 50 have coordinates; the UHCs of Biral, Bhurungamari and Thakurgaon Pirganj do not.

Rangpur District by upazila or thana: Rangpur Sadar 334 (includes the city), Mithapukur 98, Pirganj 93, Pirgachha 60, Badarganj 52, Gangachara 49, Kaunia 35, Taraganj 27, Kotwali (metro thana) 2, none 15. 39 rows in the division have no upazila.

`facts.csv` has 270 rows: counts of listed records by type per district, and per upazila or thana in Rangpur District.

## Mapping

The mapping is the same as for Rajshahi; see `../dghs_hris_facilities_raj_2026/REPORT.md`. One type is new here: "Urban Primary Health Care Center" (4 rows) is mapped to `health.clinic`. It does not occur in the Rajshahi export.

Upazila names are kept as the registry spells them, with one exception: "Rajibpur" becomes "Char Rajibpur", and the original is kept in `upazila_src`. Rangpur Metropolitan Police thanas (Kotwali) are flagged `admin_unit: metropolitan_thana`.

## Contacts

The policy is the same as for Rajshahi. Phones and e-mails are kept only for non-private facilities: 2,057 rows have a phone and 2,519 have an e-mail. For private and NGO facilities the contacts and addresses are blanked in `raw/` and not collected. Facility-head names are never collected.

## Data quality (flagged in `notes`)

- 88 rows had coordinates outside the generous division box (lat 24.8–26.8, lon 87.9–90.1). Their coordinates were dropped and the original values kept in notes.
- There was no Rangpur `hdx_cod_ab_bgd_rangpur` folder, so the district check uses the seed's district polygons (`data/seed/geo/districts.geojson`, division 10007). With those polygons:
  - 303 rows fall in a different district than the registry gives. Most are Kurigram↔Gaibandha/Rangpur and Nilphamari/Panchagarh↔Thakurgaon/Dinajpur.
  - 350 rows fall outside the division's polygons. 247 of them are in Dinajpur: whole upazilas such as Biral and Khansama have points that lie inside India.
  - All of these are kept and flagged "check". These are registry entry errors, not polygon errors: spot checks of district towns fall inside the right polygons.
- 159 rows look like duplicate registrations (same name and upazila, different codes).
- 813 non-private rows have no coordinates. This includes 5 of the 7 medical colleges and Nilphamari MCH.
- Some coordinates are doubtful but were not flagged, because they fall inside the right district. For example, Rangpur Medical College (hris:1611) is at 25.46, 89.14, roughly 30 km south of the city. RMCH (hris:1612) is at 25.752849, 89.251713.
- The registry is live and self-reported, so re-runs will differ.

## Pilot places

- Rangpur Medical College Hospital (hris:1612): approved beds 1,000; coordinates as above.
- Dinajpur MCH (hris:2233): 500 beds.
- District hospitals of Gaibandha, Kurigram, Lalmonirhat, Nilphamari and Thakurgaon: 250 beds each.
- Panchagarh District Hospital: 100 beds.
