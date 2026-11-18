# DGHS HRIS Facility Registry — Dhaka Division

- **Source:** MoHFW HRIS Facility Registry public report "Organization List" (https://hris.mohfw.gov.bd/public/facility-registry/reports/organization-list), filtered to Dhaka Division (`division_id[]=1`; every row's Division column is "Dhaka"). No login; robots.txt allows all. Licence: none stated.
- **Method:** the Rajshahi collector, run as `python3 ../dghs_hris_facilities_raj_2026/fetch.py --division dhaka` (accessed 2026-11-17). The host returned HTTP 502 from about 11:00 to 13:40; the export was fetched when it came back. It is one Excel export request, so there is no partial state to resume. `raw/` holds the export (3.3 MB) with contact and address columns blanked for private and NGO rows; `--division dhaka --offline` rebuilds from it. Each row links to `/public/facility-registry/facilities/<id>/profile`. No file is near 20 MB (`places.csv` 6.0 MB), so nothing is split.

## Counts

9,982 active rows; 9,891 kept; 7,108 have coordinates (72%). Ownership: 5,633 private, 4,137 public, 64 government-autonomous, 26 government-semi-autonomous (source spells "semi-auonomous"), 13 NGO, 10 international development agency, 6 private commercial, 2 private charity.

91 rows of types not in the existing mapping were left out (mapping unchanged from Rajshahi/Rangpur): Other 57, Directorate General or Directorate 6, Public Health Institution 6, Research Organization 4, Specialized Health Center 3, Private practice 3, College of Alternative Medicine 2, National Institute Of Nursing (NIN) 2, Head Office 2, Health Infrastructure Development 2, Port Health Office 1, Knowledge Management 1, TEMO 1, Project 1. Most are national bodies in Dhaka city.

| District | Total | Community clinic | Clinic | Diagnostic | Hospital | UHC | MCH | Other | With coords |
|---|---|---|---|---|---|---|---|---|---|
| Dhaka | 2,866 | 160 | 726 | 1,242 | 655 | 5 | 4 | 74 | 2,216 (77%) |
| Tangail | 1,094 | 436 | 189 | 291 | 138 | 11 | 1 | 28 | 782 (71%) |
| Gazipur | 857 | 231 | 143 | 280 | 172 | 4 | 1 | 26 | 669 (78%) |
| Kishoreganj | 726 | 324 | 162 | 147 | 55 | 12 | 1 | 25 | 478 (66%) |
| Faridpur | 615 | 206 | 129 | 174 | 76 | 8 | 1 | 21 | 452 (73%) |
| Narayanganj | 600 | 142 | 132 | 157 | 142 | 4 | 0 | 23 | 441 (74%) |
| Narsingdi | 592 | 208 | 108 | 167 | 93 | 5 | 0 | 11 | 459 (78%) |
| Manikganj | 509 | 174 | 145 | 110 | 57 | 6 | 1 | 16 | 332 (65%) |
| Gopalganj | 500 | 193 | 150 | 107 | 27 | 4 | 1 | 18 | 241 (48%) |
| Munshiganj | 462 | 120 | 129 | 142 | 56 | 5 | 0 | 10 | 316 (68%) |
| Madaripur | 395 | 145 | 96 | 84 | 53 | 4 | 0 | 13 | 258 (65%) |
| Shariatpur | 346 | 148 | 93 | 52 | 34 | 5 | 0 | 14 | 226 (65%) |
| Rajbari | 327 | 143 | 98 | 61 | 12 | 4 | 0 | 9 | 238 (73%) |
| (no district) | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 |

MCH = `health.medical_college_hospital`: Dhaka MCH (2,600 approved beds), Shaheed Suhrawardy (1,350), Sir Salimullah/Mitford (900), Mugda (500), Faridpur (1,000), Shaheed Taj Uddin Ahmad/Gazipur, Gopalganj, Shahid Syed Nazrul Islam/Kishoreganj, Manikganj, Tangail (500 each). "Other": government 110, pourashava office 62, medical college 52, training 40, civil surgeon 13, technical (IHT) 8, city corporation 4, university 1.

UHCs: 77; 74 have coordinates (not Nawabganj/Dhaka, Tungipara, Dasar).

Dhaka District by upazila or thana: upazilas Savar 257, Keraniganj 137, Dhamrai 130, Nawabganj 94, Dohar 54; Dhaka Metropolitan Police thanas e.g. Mohammadpur 168, Mirpur 167, Paltan 101, Dhanmondi 91, Jatrabari 90, Kalabagan 78, Banani 76, Gulshan 75, Tejgaon 75, Badda 74, Uttara Paschim 73 (46 thana names in all); none 98. 157 rows in the division have no upazila. `facts.csv` has 702 rows: counts of listed records by type per district, and per upazila or thana in Dhaka District.

## Mapping

Same as for Rajshahi (see `../dghs_hris_facilities_raj_2026/REPORT.md`).

Upazila names are kept as the registry spells them, except Manohardi → Monohardi, Roypura → Raipura, Serajdikhan → Sirajdikhan (as in the BANBEIS/IPEMIS outputs), doubled spaces removed ("Uttara  Paschim", "Uttara  Purba") and "Sher-e-bangla Nagar" → "Sher-e-Bangla Nagar"; the original is kept in `upazila_src`.

**Dhaka city:** the registry's Upazila field is a DMP thana for most city rows (Adabor … Wari, spelled as the registry spells them, e.g. "Lalbag", "Sabujbag", "Shahbag", "Shajahanpur"). These stay in `upazila_en` as given and carry `admin_unit: metropolitan_thana` (2,098 rows incl. 4 in Gazipur's Kashimpur, a Gazipur Metropolitan Police thana). The registry's City Corporation field is kept in `extra_json.city_corporation`: Dhaka North 835 (source spells "Corperation"), Dhaka South 799, Gazipur 331, Narayanganj 245, plus 1 "Chattogram City Corporation" and 1 "Khulna City Corporation" (registry errors).

## Contacts

Same policy as before: phones and e-mails only for non-private facilities (2,963 rows with a phone, 3,783 with an e-mail, 236 with a website). Private/NGO contacts and addresses are blanked in `raw/` and not collected; facility-head names never collected.

## Data quality (flagged in `notes`)

- 211 rows had coordinates outside the generous division box (lat 22.9–25.0, lon 89.2–91.3) → dropped, original in notes.
- District check used `../hdx_cod_ab_bgd_dhaka/boundaries.geojson` (13 Dhaka districts). 485 rows fall in another district than the registry gives (most: registry Gazipur, point in Dhaka 160; Faridpur → Manikganj 33) and 179 fall outside the division polygons → kept, flagged "check". Example: Tangail Medical College Hospital (hris:24181) has 23.7245, 90.3929, which is in Dhaka city.
- 3 rows give an upazila of another division, flagged: Senbagh (Noakhali) for Ad-din Women's Medical College Hospital (hris:28157), Sreebardi (Sherpur) for "Sreebardi Paurashava" (hris:40435), Madhabpur (Habiganj) for Asia Hospital, Tangail (hris:29008).
- 2,104 rows look like duplicate registrations (same name, district and upazila; 2,083 of them private; 907 in Dhaka District).
- 1,786 non-private rows lack coordinates, incl. Gopalganj MCH.
- 7 raw rows have no district (2 kept).
- Live, self-reported registry: re-runs will differ.

## E-mail scrub (2026-11-18)

Non-`*.gov.bd` e-mail addresses were blanked in `places.csv` (152 rows) and in the raw export (164 rows), as the Chattogram run does: they were mostly gmail/yahoo mailboxes that look like staff members' own, plus misspelt domains (e.g. `cc.dghs.gpv.bd`, `gamil.com`). Only the e-mail column changed; the seed never used these addresses. Earlier Git commits still contain them.

- **E-mail addresses in free-text fields (2026-11-18):** the registry also puts staff mailboxes in "Mailing Address" (and once in "Website Url"). Every non-`*.gov.bd` e-mail address is removed from those fields, in `places.csv` and in `raw/`; the rest of the text is kept (`strip_non_gov_mail` in `../dghs_hris_facilities_raj_2026/fetch.py`).
