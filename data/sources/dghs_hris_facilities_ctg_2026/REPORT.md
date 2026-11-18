# DGHS HRIS Facility Registry — Chattogram Division

- **Source:** MoHFW HRIS Facility Registry public report "Organization List" (https://hris.mohfw.gov.bd/public/facility-registry/reports/organization-list), filtered to Chattogram Division (`division_id[]=2`; every row's Division column is "Chattogram"). No login; robots.txt allows all. Licence: none stated.
- **Method:** the Rajshahi collector, run as `python3 ../dghs_hris_facilities_raj_2026/fetch.py --division chattogram` (accessed 2026-11-17). It is one Excel export request, so there is no partial state to resume. `raw/` holds the export (2.7 MB) with contact and address columns blanked for private and NGO rows, and non-`*.gov.bd` e-mails blanked for the other rows (see Contacts); `--division chattogram --offline` rebuilds from it. Each row links to `/public/facility-registry/facilities/<id>/profile`. No file is near 20 MB (`places.csv` 4.6 MB), so nothing is split.

## Counts

7,485 active rows; 7,467 kept; 5,482 have coordinates (73%). Ownership: 4,177 public, 3,169 private, 70 government-autonomous, 23 international development agency, 17 government-semi-autonomous (source spells "semi-auonomous"), 8 NGO, 3 private charity.

18 rows of types not in the existing mapping were left out (mapping unchanged): Other 10, Port Health Office 3, Refugee Camp 2 (Kutupalong Refugee Camp, Ukhia, hris:40634; Noapara "Refuzee" Camp, Teknaf, hris:40635), Specialized Health Center 1, Health Infrastructure Development 1, Upazila Field Service 1.

| District | Total | Community clinic | Clinic | Diagnostic | Hospital | UHC | MCH | Other | With coords |
|---|---|---|---|---|---|---|---|---|---|
| Cumilla | 1,588 | 500 | 342 | 452 | 249 | 16 | 1 | 28 | 1,278 (80%) |
| Chattogram | 1,515 | 534 | 411 | 340 | 164 | 15 | 1 | 50 | 1,129 (75%) |
| Noakhali | 794 | 301 | 119 | 210 | 135 | 8 | 1 | 20 | 665 (84%) |
| Brahmanbaria | 766 | 262 | 128 | 243 | 113 | 8 | 0 | 12 | 595 (78%) |
| Chandpur | 705 | 247 | 129 | 202 | 104 | 7 | 1 | 15 | 517 (73%) |
| Lakshmipur | 469 | 181 | 73 | 150 | 53 | 4 | 0 | 8 | 369 (79%) |
| Cox's Bazar | 467 | 194 | 119 | 87 | 45 | 8 | 1 | 13 | 289 (62%) |
| Feni | 384 | 154 | 74 | 88 | 50 | 5 | 0 | 13 | 286 (74%) |
| Rangamati | 305 | 137 | 105 | 27 | 13 | 9 | 1 | 13 | 170 (56%) |
| Khagrachari* | 273 | 117 | 91 | 29 | 11 | 8 | 0 | 17 | 119 (44%) |
| Bandarban | 198 | 96 | 72 | 3 | 7 | 6 | 0 | 14 | 65 (33%) |
| (no district) | 3 | 0 | 2 | 0 | 0 | 0 | 0 | 1 | 0 |

\* District names are kept as the registry spells them, as for the earlier divisions; the registry writes "Khagrachari" (seed: Khagrachhari).

By category: 2,723 community clinic, 1,831 diagnostic, 1,665 clinic, 944 hospital, 94 UHC, 6 MCH; "Other": government 76, pourashava office 65, training 29, medical college 17, civil surgeon 11, technical (IHT) 3, city corporation office 2, university 1.

MCH = `health.medical_college_hospital`: Chattogram MCH (hris:751, 2,200 approved beds, 22.359108, 91.831036), Cumilla MCH (500), Chandpur MCH (500), Rangamati MCH (500), Cox's Bazar MCH and Noakhali MCH (no bed figures). Only Chattogram and Cumilla MCH have coordinates.

UHCs: 94; 90 have coordinates (not Eidgaon, Guimara, Kamalnagar, Chatkhil).

Chattogram District by upazila or thana: upazilas Fatikchhari 116, Mirsharai 102, Patiya 100, Satkania 94, Hathazari 86, Raozan 80, Banshkhali 77, Rangunia 73, Lohagara 71, Sitakunda 67, Sandwip 66, Chandanaish 59, Boalkhali 56, Anwara 53, Karnaphuli 19; city units Panchlaish 116, Kotwali 41, Chittogram Port 31, Chandgaon 30, Double Mooring 26, Khulshi 21, Halishahar 20, Pahartali 18, Bayejid Bostami 14, Patenga 8, Chak Bazar 6, Bandar 1, Sadarghat 1; none 63. 107 rows in the division have no upazila. `facts.csv` has 529 rows: counts of listed records by type per district, and per upazila or thana in Chattogram District.

## Mapping

Same as for Rajshahi (see `../dghs_hris_facilities_raj_2026/REPORT.md`).

Upazila names are kept as the registry spells them except where they differ from the BANBEIS/IPEMIS Chattogram outputs: Anowara → Anwara, Fatikchari → Fatikchhari, Lalmi → Lalmai, Banchharampur → Bancharampur, Khagrachari Sadar → Khagrachhari Sadar, Lakshmichari → Lakshmichhari, Mahalchari → Mahalchhari, Manikchari → Manikchhari, Baghaichari → Baghaichhari, Belaichari → Belaichhari, Juraichari → Jurachhari, Kowkhali → Kawkhali, Naikhongchari → Naikhongchhari, Rowangchari → Rowangchhari (original in `upazila_src`, 549 rows).

**Chattogram city:** the registry's Upazila field is a Chattogram Metropolitan Police thana for most city rows (Panchlaish, Kotwali, Chandgaon, Double Mooring, Khulshi, Halishahar, Pahartali, Bayejid Bostami, Patenga, Chak Bazar, Bandar, Sadarghat), plus the registry's own unit "Chittogram Port". These stay in `upazila_en` as given and carry `admin_unit: metropolitan_thana` and the note "registry upazila field is a Chattogram Metropolitan Police thana, kept as given (not an upazila)" (333 rows). "Chittogram Port" (31 rows) is not a CMP thana name: it holds urban dispensaries, clinics and medical colleges from several parts of the city (Halishahar, Panchlaish, Sher Shah …), so these rows are also flagged "check". Karnaphuli (19 rows) is an upazila (formerly a CMP thana) and stays one. Cumilla city rows are under Cumilla Adarsha Sadar / Cumilla Sadar Dakshin (no metro thanas in the registry).

The registry's City Corporation field is kept in `extra_json.city_corporation`: Chattogram 302, Cumilla 295, plus 3 "Dhaka South City Corporation" (hris:25212, 27831, 29851, all with points in Chattogram city) and 1 "Narayanganj City Corporation" (hris:35539, upazila "Bandar", point in Chattogram city), flagged "not in Chattogram Division — check". Values "Upazilas of …" (and "Upazilas Cox's Bazar", which the earlier rule would have kept) are not city corporations and are left out.

**Rohingya camps (Cox's Bazar):** the registry names 3 facilities as FDMN (Forcibly Displaced Myanmar Nationals) facilities: BRAC FDMN (hris:40074, Ukhia), BRAC FDMN Camp-Ukhia (hris:40234) and BRAC FDMN Camp-Teknaf (hris:40233). They are kept as given (type "NGO for Government Health Service support" → `health.clinic`, no coordinates, no contacts in the registry) with the note "registry lists this as a Rohingya (FDMN) camp facility, kept as given". The registry's two "Refugee Camp" entries are left out by the unchanged mapping (above). The registry does not list the camps' individual NGO health posts.

## Contacts

Phones as before: only for non-private facilities (2,855 rows). E-mails: only `*.gov.bd` mailboxes of non-private facilities (3,616 rows, nearly all `*.dghs.gov.bd`). New from Chattogram on: 220 free-mail addresses of public facilities (mostly gmail, many on community clinics, often a person's name plus a birth year) and a few misspelt domains are not copied, and are blanked in `raw/` too — they look like staff members' own mailboxes. The Rajshahi, Rangpur and Dhaka source outputs were built before this rule and still contain such addresses (the seed importer never used them). 250 rows have a website. Private/NGO contacts and addresses are blanked in `raw/` and not collected; facility-head names are never collected.

## Data quality (flagged in `notes`)

- 84 rows had coordinates outside the generous division box (lat 20.5–24.4, lon 90.4–92.8) → dropped, original in notes.
- District check used `../hdx_cod_ab_bgd_chattogram/boundaries.geojson` (11 districts). 150 rows fall in another district than the registry gives (most: registry Noakhali, point in Cumilla 19; Brahmanbaria → Cumilla 15; Chattogram → Khagrachhari 11; Cumilla → Noakhali 11) and 90 fall outside the division polygons → kept, flagged "check".
- 1 row gives an upazila of another division, flagged: Banaripara (Barishal) for Bancharampur Islami Hospital, Brahmanbaria (hris:28922).
- 988 rows look like duplicate registrations (same name, district and upazila; 976 of them private).
- 1,509 non-private rows lack coordinates, incl. 4 of the 6 MCHs.
- 3 raw rows have no district (all kept, flagged).
- Mobile numbers of public community clinics are kept as before (the registry contact of the clinic); some may be the health-care provider's own phone.
- Live, self-reported registry: re-runs will differ.

- **E-mail addresses in free-text fields (2026-11-18):** the registry also puts staff mailboxes in "Mailing Address" (and once in "Website Url"). Every non-`*.gov.bd` e-mail address is removed from those fields, in `places.csv` and in `raw/`; the rest of the text is kept (`strip_non_gov_mail` in `../dghs_hris_facilities_raj_2026/fetch.py`).
