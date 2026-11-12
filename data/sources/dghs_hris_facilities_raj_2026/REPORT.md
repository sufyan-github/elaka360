# DGHS HRIS Facility Registry — Rajshahi Division

- **Source:** MoHFW HRIS Facility Registry public report "Organization List" (https://hris.mohfw.gov.bd/public/facility-registry/reports/organization-list). No login; robots.txt allows all. The old host facilityregistry.dghs.gov.bd returned "Service Unavailable" on 2026-11-12. Licence: none stated.
- **Method:** `fetch.py` requests the Excel export filtered to the division with a fixed column set. `raw/` holds that export with contact and address columns blanked for private and NGO rows; `python3 fetch.py --offline` rebuilds from it. Each row links to `/public/facility-registry/facilities/<id>/profile`.

## Counts

5,227 active rows; 5,225 kept (2 of type "Other" left out). 3,994 have coordinates (76%). Ownership: 2,904 public, 2,321 private.

| District | Total | Community clinic | Clinic | Diagnostic | Hospital | UHC | MCH | Other | With coords |
|---|---|---|---|---|---|---|---|---|---|
| Rajshahi | 780 | 238 | 193 | 211 | 83 | 9 | 1 | 45 | 587 (75%) |
| Bogura | 1,022 | 377 | 276 | 210 | 112 | 11 | 1 | 35 | 827 (81%) |
| Chapainawabganj | 395 | 152 | 95 | 95 | 40 | 4 | 0 | 9 | 324 (82%) |
| Joypurhat | 253 | 113 | 58 | 52 | 14 | 4 | 0 | 12 | 201 (79%) |
| Naogaon | 720 | 307 | 197 | 133 | 60 | 10 | 1 | 12 | 605 (84%) |
| Natore | 528 | 204 | 108 | 135 | 60 | 6 | 0 | 15 | 419 (79%) |
| Pabna | 731 | 265 | 145 | 194 | 100 | 8 | 1 | 18 | 573 (78%) |
| Sirajganj | 793 | 374 | 130 | 156 | 103 | 8 | 1 | 21 | 458 (58%) |

"Other" covers municipal health units (government.pourashava_office 61), health and drug-administration offices (government 54), training institutes (27), medical colleges (12), civil surgeon offices (8), IHTs (5), Rajshahi Medical University and one city corporation zone.

Rajshahi District by upazila/thana: Rajpara (metro) 155, Bagmara 109, Puthia 77, Godagari 68, Paba 63, Bagha 55, Charghat 47, Boalia (metro) 46, Tanore 42, Durgapur 38, Mohanpur 38, Shah Makhdum (metro) 10, Motihar (metro) 7, Kashiadanga (metro) 1, none 24. All 9 UHCs and 217 of 238 community clinics in the district have coordinates. `facts.csv` (338 rows) counts listed records by type per district and per Rajshahi upazila/thana.

## Mapping

UHC → health.upazila_health_complex · Community Clinic → health.community_clinic · Consultancy & Diagnostic Center → health.diagnostic_center · Medical College Hospital → health.medical_college_hospital · district/general/bed-sized/specialised/jail hospitals, CMH → health.hospital · private/NGO "Hospital/Clinic" → hospital if the name says hospital, else health.clinic · UH&FWC, MCWC, sub-centres, blood banks, dispensaries → health.clinic · Medical College → education.medical_college · Medical University → education.university · IHT → education.technical · nursing/training → education.training_center · Civil Surgeon Office → government.civil_surgeon.

`extra_json`: DGHS facility code, HRIS id, type, agency, level, location type, city corporation / pourashava / union / ward, year established, approved / revenue / latest beds, private flag, `admin_unit: metropolitan_thana` where the registry stores an RMP thana as the upazila. Upazila spellings normalised (original in `upazila_src`).

## Contacts

Kept only for public facilities (phone 2,213, e-mail 2,730): DGHS-issued office numbers and `*.dghs.gov.bd` mailboxes. Private/NGO contacts and addresses are not collected (possible personal numbers); facility-head names are never collected.

## Data quality (flagged in `notes`)

- 260 rows had coordinates outside the division → dropped (original kept in notes).
- 185 rows fall in another district and 81 outside the division polygons → kept, flagged "check".
- 594 rows look like duplicate registrations (same name and upazila, different codes; mostly private) → flagged.
- 887 public rows lack coordinates (incl. Rajshahi Sadar Hospital, Rajshahi Medical University). Most DGFP UH&FWCs are absent (26 in the division).
- Live, self-reported registry: re-runs will differ.

## Pilot places

RMCH (hris:1554): DGHS code 10001560; 24.372088, 88.586359; approved beds 1,300; est. 1958. Rajshahi Medical College (hris:1553) and the Civil Surgeon office (hris:1550) are separate records.
