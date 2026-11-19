# Upazila portals of Khulna Division

- **Collector:** `rajshahi_upazila_portals/fetch.py --division khulna`. Scope is the whole division: 59 upazila portals, all reached.
  - Subdomains come from the national portal's office registry: Jashore on jashore.gov.bd, Mirpur `mirpur.kushtia.gov.bd`, Dakop `dacope.khulna.gov.bd`.
- Each portal's title is checked; then the menu items for the union list, এক নজরে and pourashava pages are used. 197 pages (192 ok; `raw/pages.csv`; texts in `raw/`; `raw/warnings.txt`).
- **areas.csv (558):** 535 unions (160 with a portal website where linked) and 23 pourashavas.
- **facts.csv (341):**
  - upazila: union count 99, village 43, mouza 43, area km² 37, population 37, household 32, pourashava count 25, area in other units 2;
  - pourashava pages: wards 7, area 6+1, population 6, mouzas 3;
  - 2 values flagged DOUBT (Tala population 2,990,400; Narail Sadar population 778).

| District | Unions per upazila portal |
|---|---|
| Khulna | Paikgasa 10, Fultola 4, Digholia 6, Rupsha 5, Dumuria 14, Botiaghata 7, Dakop 9, Koyra 7; Terokhada – |
| Jashore | Manirampur 17, Abhaynagar 8, Bagherpara 9, Chougachha 11, Jhikargacha 10, Keshabpur 11, Jessore Sadar 15, Sharsha 11 |
| Satkhira | Assasuni 11, Kalaroa 12, Satkhira Sadar 14, Shyamnagar 12, Tala 12, Kaliganj 12; Debhata – |
| Meherpur | Mujibnagar 4, Gangni 9; Meherpur Sadar – |
| Narail | Narail Sadar 13, Lohagara 12, Kalia 14 |
| Chuadanga | Chuadanga Sadar 10, Alamdanga 15, Damurhuda 8, Jibannagar 8 |
| Kushtia | Kushtia Sadar 13, Kumarkhali 11, Khoksa 9, Mirpur 13, Daulatpur 14, Bheramara 6 |
| Magura | Shalikha 7, Sreepur 8, Mohammadpur 8; Magura Sadar – |
| Bagerhat | Fakirhat 8, Bagerhat Sadar 10, Sarankhola 4, Rampal 10, Morrelganj 16, Kachua 7, Chitalmari 7; Mollahat, Mongla – |
| Jhenaidah | Jhenaidah Sadar 17, Shailkupa 14, Harinakundu 8, Kaliganj 11, Kotchandpur 2, Moheshpur 12 |

"–" means no usable union list, on 7 portals:
- **The page also names people** (chairmen with mobiles, secretaries' e-mails, or UDC entrepreneurs): Terokhada, Debhata, Meherpur Sadar, Mongla. Not used, and raw text not saved.
- **No union list menu item:** Mollahat.
- **No union rows parsed:** Magura Sadar.

## Conflicts and caveats

- **Jhikargacha:** the page lists villages under "N নং X ইউনিয়নঃ" headings. Only the 10 union headings are used (the 3rd is printed "শিমুলিয়া ইউনিয়নঃআজমপুর, …"), and the village lists are skipped. The registry and DC have 11; শিমুলিয়া is missing because its heading runs into the village list.
- **Kotchandpur:** the page is prose about how to reach each union. Only দোড়া and কুশনা are parsed (DC and registry: 5).
- **Koyra:** the page has a table "ইউনিয়নের নাম ও জিও কোড | আয়তন (একর)". The geocode after each name is dropped; spellings are as in that table (আমাদি, বাগালি).
- **Chuadanga Sadar:** lists 10, including নেহালপুর (DC 9, seed 7).
- **Tala:** the page is dated 2014-06-20; its header row "ক্র. ন." is skipped.
- **Spelling:** names such as "সুন্দরপুর-দূর্গাপুর", "শিমলা-রোকনপুর", "কে ডি কে", "চিতলমারী সদর পরিষদ" are kept as printed.
- **Pourashavas:** 23 rows, from menu items, এক নজরে পৌরসভা pages and links.
  - 7 pourashava pages print no name (Paikgasa, Meherpur Sadar, Alamdanga, Kushtia Sadar, Khoksa, Shailkupa, Harinakundu; Khoksa and Harinakundu are named by menu links instead).
  - Mohammadpur's এক নজরে returned HTTP 404.
- **Facts:**
  - many এক নজরে pages are old and quote the 2001 or 2011 census;
  - population years printed: none 29, 2011 ×5, 2001 ×5, 2022 ×3, 2021 ×1;
  - prefer BBS 2022.
- Phone numbers and e-mails are redacted in `raw/`.

## Licence

No licence stated; facts only. Attribution: উপজেলা প্রশাসন, খুলনা বিভাগ — জাতীয় তথ্য বাতায়ন (<upazila>.<district>.gov.bd).
