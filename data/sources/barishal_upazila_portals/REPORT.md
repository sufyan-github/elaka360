# Upazila portals of Barishal Division

- **Collector:** `rajshahi_upazila_portals/fetch.py --division barishal`. Scope is the whole division: 42 upazila
  portals, all reached, with titles checked.
  - Subdomains come from the national portal's office registry. The Barishal district's portals are on barisal.gov.bd.
- **Pages:** menu items for the union list, এক নজরে and pourashava pages. 136 pages: 130 ok, 5 name people (not
  used), 1 HTTP 404 (Mehendiganj pourashava). See `raw/pages.csv`, texts in `raw/`, `raw/warnings.txt`.
- **areas.csv (262):** 248 unions and 14 pourashavas.
  - 237 unions have a website: linked on the page, or from the national registry (80, noted).
- **facts.csv (271):**
  - upazila: union count 67, population 36, village 33, area km² 32, mouza 32, household 23, pourashava count 22,
    area in other units 4;
  - pourashava pages: population 7, area 5+1, wards 4, households 3, mouzas 2.

| District | Unions per upazila portal |
|---|---|
| Barishal | Barisal Sadar 10, Bakerganj 14, Babuganj 6, Wazirpur 9, Banaripara 8, Gournadi 7, Agailjhara 5, Muladi 7, Hizla 6; Mehendiganj – |
| Jhalokathi | Nalchity 10; Jhalakathi Sadar, Kathalia, Rajapur – |
| Patuakhali | Bauphal 15, Patuakhali Sadar 14, Dashmina 7, Kalapara 12, Mirzaganj 6, Galachipa 12, Rangabali 5; Dumki – |
| Pirojpur | Pirojpur Sadar 7, Kawkhali 5, Zianagar 5, Bhandaria 6, Mathbaria 11; Nazirpur, Nesarabad – |
| Bhola | Doulatkhan 9, Lalmohan 10; Bhola Sadar, Borhanuddin, Charfesson, Monpura, Tazumuddin – |
| Barguna | Amtali 7, Barguna Sadar 10, Betagi 7, Bamna 4, Pathorghata 7, Taltali 7 |

"–" means no usable union list, on 12 portals:
- **The page also names people** (chairmen, secretaries, mobiles): Jhalakathi Sadar, Kathalia, Nesarabad,
  Borhanuddin, Charfesson. Not used, and raw text not saved.
- **No union list menu item:** Rajapur, Dumki, Bhola Sadar, Monpura. Nazirpur's item points to an index without
  content.
- **PDF only:** Mehendiganj, Tazumuddin.

## Conflicts and caveats

- **Galachipa:** prose ("ইউনিয়নগুলোর নাম হলো- …, গজলিয়া,ও কলাগাছিয়া এবং পৌরসভার নাম হল গলাচিপা।"), split into 12 items.
- **Lalmohan:** the list is a `/pages/union/` page. It names 10 unions, including মোতাহারনগর, which the DC list and
  the registry do not have (9).
- **Barisal Sadar:** items are printed "X ইউপি বরিশাল সদর, বরিশাল।"; the suffix is dropped and the printed text kept.
- **Kawkhali** (page 2014-11-25):
  - "০৪ নয় চিরাপাড়া" is kept as "নয় চিরাপাড়া" ("নয়" is probably a misprint of "নং");
  - "সদর" is kept as printed;
  - "আমরািজুড়ী" has a DOUBT note (malformed).
  - Bamna's "ডেীয়াতলা" also has a DOUBT note.
- **Bhandaria:** 6 (no ৬নং). **Rangabali:** 5 (DC 6).
- **Pourashavas (14):** from menu items, এক নজরে পৌরসভা pages (name from the page title or a "পৌরসভার নাম" row),
  and menu links (Bhandaria, Betagi with websites).
  - "মঠবািরয়া পৌরসভা" is kept as printed in the title, with a DOUBT; its area 239.14 km² is flagged implausible.
  - Banaripara, Muladi and Bhola Sadar এক নজরে pages print no name (Muladi is named by its menu item).
- **Facts:** many এক নজরে pages are old; population years printed: none 32, 2022 ×2, 2011 ×2. Prefer BBS 2022.
- Phone numbers and e-mails are redacted in `raw/`. Bhola Sadar's এক নজরে names people: its facts are kept, but the
  raw text is not saved.

## Licence

No licence stated; facts only. Attribution: উপজেলা প্রশাসন, বরিশাল বিভাগ — জাতীয় তথ্য বাতায়ন (<upazila>.<district>.gov.bd).
