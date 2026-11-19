# Upazila portals of Chattogram Division

- **Collector:** `rajshahi_upazila_portals/fetch.py --division chattogram`. Scope is the whole division: 107 upazila portals, all reached.
  - Subdomains come from the national portal's office registry. Bangara is on cumilla.gov.bd. Noakhali's Sonaimori is `sonaimuri` (the seed's sonaimori subdomain answers "Site is not available").
- Each portal's title is checked; then the menu items for the union list, এক নজরে and pourashava pages are used. 321 pages (315 ok; `raw/pages.csv`; texts in `raw/`; `raw/warnings.txt`).
- **areas.csv (738):** 711 unions (316 with a portal website where linked) and 27 pourashavas.
- **facts.csv (554):**
  - label-matched এক নজরে figures: union count 161, mouza 75, population 69, village 67, area 64+9, pourashava count 53, household 52, wards 4;
  - 4 values flagged DOUBT (Chandina "population 9", Hatia area 2,100 km², Raipur pourashava population 45, Naikhongchhari "133" persons per km²).

| District | Unions per upazila portal |
|---|---|
| Cumilla | Debidwar 15, Barura 15, Brahmanpara 7, Chauddagram 13, Daudkandi 15, Homna 9, Laksam 8, Meghna 8, Monohargonj 11, Sadarsouth 7, Titas 9, Burichang 9, Lalmai 9; Chandina, Muradnagar, Nangalkot, Comilla Sadar, Bangara – |
| Feni | Chhagalnaiya 5, Feni Sadar 12, Sonagazi 9, Fulgazi 6, Parshuram 3, Daganbhuiyan 8 |
| Brahmanbaria | Nasirnagar 13, Sarail 9, Ashuganj 8, Nabinagar 21, Bancharampur 13, Bijoynagar 10; Sadar, Kasba, Akhaura – |
| Rangamati | Sadar 6, Kaptai 5, Kawkhali 3, Barkal 5, Langadu 7, Rajasthali 3, Belaichari 4, Naniarchar 4; Baghaichari, Juraichari – |
| Noakhali | Sadar 13, Companiganj 8, Hatia 11, Subarnachar 8, Kabirhat 3, Senbug 9, Chatkhil 9, Sonaimori 10; Begumganj – |
| Chandpur | Haimchar 6, Kachua 12, Shahrasti 10, Sadar 14, Matlab South 6, Hajiganj 12, Matlab North 14, Faridgonj 15 |
| Lakshmipur | Kamalnagar 9, Raipur 10, Ramganj 10; Sadar, Ramgati, Chandraganj – |
| Chattogram | Rangunia 15, Sitakunda 9, Mirsharai 16, Patiya 15, Sandwip 15, Boalkhali 9, Chandanaish 8, Lohagara 9, Hathazari 14, Fatikchhari 18; Banshkhali, Anwara, Satkania, Raozan, Karnafuli, Fatikchhari Uttar – |
| Cox's Bazar | Sadar 5, Chakaria 12, Kutubdia 6, Ukhiya 5, Moheshkhali 8, Pekua 7, Ramu 11, Teknaf 6; Eidgaon – |
| Khagrachhari | Laxmichhari 3, Mohalchari 5, Manikchari 4, Guimara 3; Sadar, Dighinala, Panchari, Ramgarh, Matiranga – |
| Bandarban | Sadar 6, Alikadam 4, Naikhongchhari 5, Lama 7, Ruma 4, Thanchi 4; Rowangchhari – |

"–" means no usable union list, on 32 portals:
- no menu item: 24;
- PDF or image: Chandraganj, Eidgaon;
- HTTP 404: Rowangchhari;
- menu item leads to a chairman/member list or a village-police list: Chandina, Lakshmipur Sadar, Anwara, Satkania. These were not used, and their raw text was not saved because it lists private persons.

## Conflicts and caveats

- **Kawkhali's** page lists "ইউনিয়ন ও মৌজা সমূহ". Only the unions are kept (বেতবুনিয়া is not parsed). The numbered mouzas ("৮৭ নং ডাবুয়া মৌজা" …) are in `raw/`.
  - Hill upazila এক নজরে pages give mouza counts, often with headmen and karbari counts (e.g. Langadu "২৫টি (হেডম্যান পদ সংখ্যা= ২৫টি…)", Laxmichhari "১৬ টি, হেডম্যান-১৬ জন, কার্বারী-৫১ জন").
- **Fatikchhari** lists 18 unions, including খিরাম and ধর্মপুর. The registry has 17, plus Fatikchhari Uttar with none yet.
- **Hatia** lists 11 unions (the এক নজরে also says ১১); the national registry has 9.
- **Chakaria** lists 12 (the এক নজরে says ১৪). The DC list still has 18, from before Eidgaon.
- **Kabirhat** lists 3 (the এক নজরে says ৭). Brahmanpara lists 7 (the এক নজরে says ৮).
- **Lohagara** prints its unions twice; they are merged into one row each ("row printed 2 times").
- **Sonagazi** links চর মজলিশপুর to subilup.comilla.gov.bd; this link is not used.
- **Pourashavas:** 27 rows, from menu items, এক নজরে পৌরসভা pages and links.
  - 12 pourashava pages print no name (Daudkandi, Homna, Laksam, Nangalkot, Brahmanbaria Sadar, Hatia, Senbug, Chandpur Sadar, Matlab South and North, Boalkhali, Hathazari) and gave no row.
  - Kabirhat's link to paurainfo.gov.bd is kept as printed. দোহাজারী পৌরসভা is linked to dohazariup.chittagong.gov.bd (a union portal).
- **Facts:**
  - most এক নজরে pages are old (many 2013–2021) and quote the 2011 census; the year is recorded where printed;
  - population years printed: mostly none;
  - prefer BBS 2022 for population.
- Phone numbers and e-mails are redacted in `raw/`.

## Licence

No licence stated; facts only. Attribution: উপজেলা প্রশাসন, চট্টগ্রাম বিভাগ — জাতীয় তথ্য বাতায়ন (<upazila>.<district>.gov.bd).
