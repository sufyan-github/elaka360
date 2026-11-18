# Upazila portals of Dhaka Division

- **Collector:** `rajshahi_upazila_portals/fetch.py --division dhaka`. Scope is the whole division: 89 upazila portals.
  Subdomains come from the national portal's office registry; two differ from the seed (daulatpur, singair in
  Manikganj).
- Each portal's title is checked; then the menu items for the union list, এক নজরে and pourashava pages are used.
  296 pages, all fetched (`raw/pages.csv`; texts in `raw/`; `raw/warnings.txt`).
- **areas.csv (834):** 797 unions (373 with a portal website where linked) and 37 pourashavas.
- **facts.csv (565):**
  - label-matched এক নজরে figures: area, population, and union, pourashava, mouza, village, household and ward counts;
  - the printed label and value are in `notes`;
  - one DOUBT: Bhairab pourashava "population 12" (from "১২ টি ওয়ার্ডে বিভক্ত…").

| District | Unions per upazila portal |
|---|---|
| Narsingdi | Narsingdi Sadar 14, Palash 4, Raipura 24, Shibpur 9, Belabo –, Monohardi – |
| Gazipur | Kaliganj 7, Kaliakair 9, Kapasia 11, Gazipur Sadar 4, Sreepur 8 |
| Shariatpur | Shariatpur Sadar 11, Naria 14, Zajira 12, Gosairhat 8, Bhedarganj 13, Damudya 7 |
| Narayanganj | Araihazar 10, Bandar 5, Narayanganj Sadar 7, Sonargaon 10, Rupganj – |
| Tangail | Bhuapur 6, Delduar 8, Ghatail 14, Gopalpur 7, Madhupur 11, Mirzapur 14, Nagarpur 12, Sakhipur 10, Tangail Sadar 12, Kalihati 13, Dhanbari 7, Basail – |
| Kishoreganj | Katiadi 9, Bhairab 7, Tarail 7, Hossainpur 6, Pakundia 9, Kuliarchar 6, Kishoreganj Sadar 11, Karimgonj 11, Bajitpur 11, Austagram 8, Mithamoin 7, Nikli 7, Itna – |
| Manikganj | Harirampur 13, Saturia 9, Gior 7, Shibaloy 7, Doulatpur 8, Singiar 11, Manikganj Sadar – |
| Dhaka | Savar 12, Dhamrai 16, Keraniganj 12, Nawabganj 14, Dohar 8 |
| Munshiganj | Munshiganj Sadar 9, Sreenagar 14, Sirajdikhan 14, Gajaria 8, Tongibari 13, Louhajanj – |
| Rajbari | Rajbari Sadar 14, Goalanda 4, Baliakandi 7, Kalukhali 7, Pangsa – |
| Madaripur | Madaripur Sadar 15, Shibchar 18, Kalkini 10, Rajoir 11, Dasar 5 |
| Gopalganj | Gopalganj Sadar 21, Kashiani 14, Tungipara 5, Kotalipara 11, Muksudpur 16 |
| Faridpur | Boalmari 11, Sadarpur 9, Nagarkanda 9, Bhanga 12, Charbhadrasan 4, Madhukhali 11, Saltha 8, Faridpur Sadar –, Alfadanga – |

"–" means no usable union list, on 10 portals:
- no menu item: Belabo, Rupganj, Basail, Manikganj Sadar, Faridpur Sadar, Alfadanga;
- page not parseable: Itna, Louhajanj, Pangsa;
- chairman list only: Monohardi (not used).

## Conflicts and caveats

- Every union count agrees with the DC lists and the national list of union portals, with one exception. **Boalmari**
  has 11 here: চাঁদপুর is added, compared with the 10 stated on faridpur.gov.bd and the national list.
- **এক নজরে union counts** that disagree:
  - Kalkini 15, which predates the 5 unions now in Dasar;
  - Kotalipara 12, vs 11 listed.
- **Spelling:** 66 names differ only in spelling from the DC lists. A few look garbled:
  - Naria "মোক্তােরর চর", "ভােজশ্বর", "চর আএা";
  - "আলো্কবালী".
  Kept as printed.
- **Sakhipur** prints its unions twice (two tables). They are merged into one row each ("row printed 2 times"). Its
  গজারিয়া link points to gajariaup.munshiganj.gov.bd and is not used.
- **Pourashavas:** 37 named from menu items, এক নজরে পৌরসভা pages and links.
  - Several "এক নজরে পৌরসভা" pages print no name (e.g. Kaliakair, Naria, Damudya, Ghatail, Sakhipur, Dhanbari,
    Bajitpur, Rajoir, Muksudpur) and were not turned into rows.
  - Narayanganj's কাঞ্চন and তারাব are under Rupganj; মিরকাদিম is under Munshiganj Sadar.
- **Facts:**
  - Most এক নজরে pages are old and quote the 2011 census; the year is recorded where printed.
  - Some union pages carry chairmen's names and mobile numbers in extra columns. Only union names are kept; phone
    numbers and e-mails are redacted in `raw/`.

## Licence

No licence stated; facts only. Attribution: উপজেলা প্রশাসন, ঢাকা বিভাগ — জাতীয় তথ্য বাতায়ন (<upazila>.<district>.gov.bd).
