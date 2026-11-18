# DPE IPEMIS public school directory — Dhaka Division

- **Source:** ipemis.dpe.gov.bd/search-school (linked from dpe.gov.bd). No login; no robots.txt (404). Licence: none stated.
- **Method:** the Rajshahi collector, run as `python3 ../dpe_ipemis_primary_raj_2026/fetch.py --division dhaka --resume` with IPEMIS `divisionId=3` (13 districts, ids 19–31), accessed 2026-11-17. It reads `/load-lite-school-list` per district, 500 rows at a time, and `api.ipemis.dpe.gov.bd/api/school-stat-public` for division, district and upazila statistics. Responses are cached in `.partial/` during a run so `--resume` can continue an interrupted run; the cache is removed on success. One re-run hit an API outage (connection timeouts); the fetcher now stops without writing in that case, and the final run was made after the API came back. `raw/` holds the division JSON (8.2 MB); `places.csv` 9.4 MB; nothing split.
- **Scope:** government, newly nationalised and experimental primary schools only (no kindergartens, NGO schools or ebtedayee madrasas).

## Counts: 10,925 schools

All rows `education.primary_school`, ownership "government"; no coordinates. By type: 7,537 government, 3,376 newly nationalised, 12 experimental.

| District | Schools | Govt | Newly nationalised | Experimental | Teachers* | Students* |
|---|---|---|---|---|---|---|
| Tangail | 1,624 | 994 | 629 | 1 | 9,469 | 221,955 |
| Kishoreganj | 1,329 | 837 | 491 | 1 | 7,521 | 247,765 |
| Dhaka | 951 | 767 | 184 | 0 | 7,757 | 241,002 |
| Faridpur | 889 | 580 | 308 | 1 | 5,103 | 154,292 |
| Gopalganj | 863 | 546 | 316 | 1 | 4,517 | 104,001 |
| Gazipur | 779 | 569 | 209 | 1 | 4,891 | 140,350 |
| Narsingdi | 774 | 601 | 172 | 1 | 4,915 | 154,802 |
| Madaripur | 721 | 461 | 259 | 1 | 3,993 | 101,534 |
| Shariatpur | 700 | 457 | 242 | 1 | 3,862 | 103,142 |
| Manikganj | 651 | 488 | 162 | 1 | 4,016 | 104,708 |
| Munshiganj | 613 | 525 | 87 | 1 | 3,582 | 107,683 |
| Narayanganj | 548 | 438 | 109 | 1 | 3,640 | 133,345 |
| Rajbari | 483 | 274 | 208 | 1 | 2,767 | 97,177 |

\* official IPEMIS live statistic. Division: 10,925 schools, 66,033 teachers, 1,911,756 students. The official school counts match the listed rows for the division, every district and every upazila/thana unit.

Dhaka District by unit: Dhamrai 171, Nawabganj 130, Keraniganj 128, Savar 121, Dohar 59; city units Demra 50, Sutrapur 48, Lalbag 43, Mirpur 42, Gulshan 38, Kotwali 32, Mohammadpur 23, Motijheel 23, Cantonment 13, Dhanmondi 11, Tejgaon 10, Ramna 9. Gazipur: Kapasia 179, Sreepur 166, Gazipur Sadar 165, Kaliganj 129, Kaliakair 122, Tongi 18.

`facts.csv` has 793 rows: 580 official statistics (schools, teachers, students per division, district and upazila/thana unit) and 213 counts of listed records by type.

## Fields and gaps

- Bangla and English names (English often abbreviated); address = union/ward, upazila, district in Bangla; `extra_json`: school code, IPEMIS id, type, union, cluster, teacher and student counts. No coordinates, phones or e-mails; head teachers' names and mobiles on the detail pages are deliberately not collected.
- Upazila names normalised to standard spellings, original in `upazila_src` (e.g. MONOHORDI → Monohardi, RAYPURA → Raipura, JAJIRA → Zanjira, RAZOIR → Rajoir, CHARBHARDRASON → Char Bhadrasan, SHOKHIPUR → Sakhipur, LOWHAJANG → Lohajang).
- **Dhaka city:** IPEMIS has 12 city thana units (Mirpur, Mohammadpur, Dhanmondi, Lalbag, Kotwali, Sutrapur, Cantonment, Motijheel, Ramna, Tejgaon, Gulshan, Demra). They are kept in `upazila_en` as given (title-cased, e.g. "Lalbag") with `admin_unit: metropolitan_thana` and a note (342 rows). DMP now has about 50 thanas, so one IPEMIS unit may cover more than the DMP thana of that name; the source does not say which city corporation.
- **Tongi (Gazipur):** IPEMIS lists TONGI (18 schools) as its own upazila unit. Tongi is a thana, not an upazila; kept as "Tongi" with `admin_unit: thana` and a note; the source gives no parent upazila.
- Dasar (Madaripur) is listed as its own upazila.
- 20 Bangla names repeat within an upazila under different codes. Live data: re-runs will differ.
