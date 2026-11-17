# Upazila portals of Rangpur Division

- **Collector:** `rajshahi_upazila_portals/fetch.py --division rangpur`. Scope is the whole division (60 upazila
  portals, incl. new Ruhia and Bhulli), not only the head district.
- Each portal's title is checked; then the menu items for the union list, এক নজরে and pourashava pages are used.
  186 pages, all fetched (`raw/pages.csv`; texts in `raw/`; `raw/warnings.txt`).
- **areas.csv (491):** 477 unions (with portal website where linked: 235), 14 pourashavas.
- **facts.csv (317):**
  - label-matched এক নজরে figures: area, population, and union, pourashava, mouza, village and household counts;
  - the printed label and value are in `notes`;
  - implausible values get a DOUBT note (for example, Sadullapur's area "23012").

| District | Unions per upazila portal |
|---|---|
| Rangpur | Rangpur Sadar 5, Gangachara 9, Taragonj 5, Badargonj 10, Mithapukur 17, Pirgonj 15, Kaunia 6, Pirgacha 9 |
| Panchagarh | Panchagarh Sadar 10, Debiganj 10, Boda 10, Atwari 6, Tetulia 7 |
| Dinajpur | Nawabganj 9, Birganj 11, Ghoraghat 4, Birampur 7, Parbatipur 10, Bochaganj 6, Kaharol 6, Fulbari 7, Dinajpur Sadar 10, Hakimpur 3, Birol 12, Chirirbandar 12, Khansama – |
| Lalmonirhat | Lalmonirhat Sadar 9, Kaliganj 8, Patgram 8, Aditmari 8, Hatibandha – |
| Nilphamari | Syedpur 5, Domar 10, Dimla 10, Kishorganj 9, Nilphamari Sadar 15, Jaldhaka – |
| Gaibandha | Sadullapur 11, Gaibandha Sadar 13, Palashbari 8, Saghata 10, Gobindaganj 17, Sundarganj 15, Phulchari – |
| Thakurgaon | Pirganj 10, Ranisankail 8, Baliadangi 8, Ruhia 6, Thakurgaon Sadar –, Haripur –, Bhulli – |
| Kurigram | Kurigram Sadar 8, Nageshwari 14, Bhurungamari 10, Phulbari 6, Rajarhat 7, Ulipur 13, Chilmari 6, Rowmari 6, Charrajibpur 3 |

"–" = no union-list menu item on that portal (7 portals).

## Conflicts and caveats

- Every union count that could be parsed agrees with the DC portal lists.
- 62 names differ only in spelling from the DC lists. One is garbled: Kishorganj's "নিতা্উই নিয়ন" (DC list: নিতাই).
- **Pourashavas** from upazila pages: বদরগঞ্জ, পঞ্চগড়, দেবীগঞ্জ, বোদা, সেতাবগঞ্জ (Bochaganj; DC list says বোচাগঞ্জ),
  ফুলবাড়ী, লালমনিরহাট, পাটগ্রাম, সৈয়দপুর, জলঢাকা, গাইবান্ধা, গোবিন্দগঞ্জ, ঠাকুরগাঁও, উলিপুর.
  - Seven "এক নজরে পৌরসভা" pages print no name (Kaunia, Fulbari, Hakimpur, Birol, Lalmonirhat Sadar, Nilphamari Sadar,
    Sundarganj) and were not turned into rows.
- Most এক নজরে pages are old (2012–2023) and quote the 2011 census; the year is recorded where printed.
- Some pages give union names with distances, chairmen or populations in extra columns; only the name is kept.
  Chairmen's names and phone numbers are not stored and are redacted in `raw/`.

## Licence

No licence stated; facts only. Attribution: উপজেলা প্রশাসন, রংপুর বিভাগ — জাতীয় তথ্য বাতায়ন (<upazila>.<district>.gov.bd).
