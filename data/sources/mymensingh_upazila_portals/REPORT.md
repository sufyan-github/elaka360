# Upazila portals of Mymensingh Division

- **Collector:** `rajshahi_upazila_portals/fetch.py --division mymensingh`. Scope is the whole division: 35 upazila portals, all reached, titles checked. Subdomains come from the national portal's office registry.
- **Pages:** menu items for the union list, এক নজরে and pourashava pages. 112 pages: 108 ok, 3 name people (not used), 1 HTTP 404 (Dhobaura এক নজরে). See `raw/pages.csv`, texts in `raw/`, `raw/warnings.txt`.
- **areas.csv (278):** 267 unions and 11 pourashavas.
  - 263 unions have a website: 171 linked or printed on the page, 92 from the national registry (noted).
  - No website: রাজনগর, যোগানিয়া (Nalitabari), শ্রীবরদী সদর (Sreebordi), ঝিনাইগাতী সদর (Jhenaigati).
  - Union numbers are kept as `code` where printed (139).
- **facts.csv (211):**
  - upazila: union count 54 (listed and stated), population 27, area km² 26, mouzas 24, villages 24, households 21, pourashava count 21, area in other units 2;
  - pourashava pages: area 3, population 3, wards 3, households 2, mouzas 1.

| District | Unions per upazila portal |
|---|---|
| Mymensingh | Mymensingh Sadar 11, Muktagacha 10, Fulbaria 13, Trishal 12, Gafargaon 15, Nandail 13, Iswarganj 11, Gouripur 10, Phulpur 10, Haluaghat 12, Dhobaura 7, Tarakanda 10; Bhaluka – |
| Jamalpur | Jamalpur Sadar 15, Islampur 12, Dewangonj 8, Sarishabari 8, Madarganj 7, Bokshiganj 7; Melandah – |
| Sherpur | Nalitabari 12, Sreebordi 10, Jhenaigati 7; Sherpur Sadar, Nokla – |
| Netrokona | Netrokona Sadar 12, Barhatta 7, Durgapur 7, Khaliajuri 6, Kalmakanda 8, Mohongonj 7; Kendua, Atpara, Madan, Purbadhala – |

"–" means no usable union list, on 9 portals:
- **The page also names people** (chairmen, secretaries, UDC entrepreneurs): Melandah, Sherpur Sadar, Kendua. Not used, and raw text not saved.
- **Bhaluka:** the only "ইউনিয়ন" item is a list of schools by union (excluded).
- **Atpara:** the only item is "ইউনিয়ন স্বাস্থ্য কমপ্লেক্স" (excluded).
- **Purbadhala:** the only item is the list of UDC entrepreneurs (excluded).
- **Madan:** no union menu item.
- **Nokla:** "ইউনিয়ন সমূহ" points to /pages/union, an index without content.

## Conflicts and caveats

- **Tarakanda** (10) lists গালাগাও and not জুগলী, as the registry does. The DC list prints জুগলী under Tarakanda.
- **Gouripur and Phulpur** list 10 each, as the registry does; the DC list has 8 and 6.
- **Haluaghat** lists 12, matching the registry. The DC list gives Haluaghat no cell of its own.
- **Mymensingh Sadar** 11 (seed 13). **Nandail** 13, including বেতাগৈর and চর বেতাগৈর (seed 12).
- **Layouts:**
  - Phulpur and Tarakanda print "* ১নং X": the bullet and number are stripped, and the number is kept as `code`.
  - Mohongonj prints a line holding only "ও" between items 6 and 7; it is not taken as a union.
  - Netrokona Sadar prints the heading and a comma list on one line.
- **Pourashavas (11):**
  - From এক নজরে pourashava pages: Bhaluka, Nandail, Islampur, Madarganj, Sreebordi, Netrokona Sadar, Madan.
  - From menu links, with websites: Gafargaon (gafargaonpourashava.com), Haluaghat (ps.haluaghat.mymensingh.gov.bd), Sarishabari (sarishabaripourashava.gov.bd), Mohongonj (municipality.mohongonj.netrokona.gov.bd).
  - The Fulbaria, Iswarganj, Dewangonj, Bokshiganj and Kendua pourashava pages print no name and are skipped. Kendua's page is prose ("গ শ্রেনীর পৌরসভা"); its raw text is kept.
- **Facts:**
  - many এক নজরে pages are old. Population years printed: none 19, 2022 ×6, 2011 ×4, 2001 ×1. Prefer BBS 2022.
  - Khaliajuri's "২৯৭,৬৪ বর্গ কিমি" is read as 29,764 and flagged DOUBT (probably 297.64).
  - Sherpur Sadar "৩৫৮০০০ হেঃ, ৮৮৪২৬ একর" and Sreebordi "২৫২.৪৪ র্বগ কি:মি" are kept as area with unit "unstated".
- Phone numbers and e-mails are redacted in `raw/`. Mymensingh Sadar's এক নজরে names people: its facts are kept, but the raw text is not saved.

## Licence

No licence stated; facts only. Attribution: উপজেলা প্রশাসন, ময়মনসিংহ বিভাগ — জাতীয় তথ্য বাতায়ন (<upazila>.<district>.gov.bd).
