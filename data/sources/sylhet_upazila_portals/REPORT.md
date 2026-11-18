# Upazila portals of Sylhet Division

- **Collector:** `rajshahi_upazila_portals/fetch.py --division sylhet`. Scope is the whole division: 41 upazila portals, all reached, titles checked.
  - Subdomains come from the national portal's office registry.
  - South Sunamganj's portal is shantiganj.sunamganj.gov.bd ("হোম | শান্তিগঞ্জ উপজেলা").
- **Pages:** menu items for the union list, এক নজরে and pourashava pages. 124 pages: 115 ok, 8 name people (not used), 1 not a union list. See `raw/pages.csv`, texts in `raw/`, `raw/warnings.txt`.
- **areas.csv (228):** 220 unions and 8 pourashavas.
  - 192 unions have a website: 75 linked or printed on the page, 117 from the national registry (noted).
- **facts.csv (214):**
  - upazila: union count 56, area km² 30, population 29, mouzas 29, villages 26, households 15, pourashava count 14, area in other units 1;
  - pourashava pages: wards 3, population 3, area 3+1, mouzas 2, households 2.

| District | Unions per upazila portal |
|---|---|
| Sylhet | Sylhet Sadar 8, Balaganj 6, Beanibazar 10, Bishwanath 8, Fenchuganj 5, Golapganj 11, Kanaighat 9, Dakshinsurma 8, Osmaninagar 8; Companiganj, Gowainghat, Jaintiapur, Zakiganj – |
| Moulvibazar | Juri 6, Kamolganj 9, Kulaura 13, Rajnagar 8; Moulvibazar Sadar, Barlekha, Sreemangal – |
| Habiganj | Habiganj Sadar 8, Nabiganj 13, Bahubal 7, Baniachong 15, Chunarughat 10, Madhabpur 11, Shayestaganj 3; Ajmiriganj, Lakhai – |
| Sunamganj | Sunamganj Sadar 9, Bishwambarpur 5, Tahirpur 7, Jamalganj 6, Shalla 4, Derai 9, Madhyanagar 4; South Sunamganj, Chhatak, Jagannathpur, Dowarabazar, Dharmapasha – |

"–" means no usable union list, on 14 portals:
- **The page also names people** (chairmen, secretaries, mobiles): Jaintiapur, Zakiganj, Moulvibazar Sadar, Barlekha, Sreemangal, Ajmiriganj, Lakhai, South Sunamganj. Not used, and raw text not saved.
- **Gowainghat:** the only item, "ইউনিয়নসমূহ ও চেয়ারম্যানবৃন্দ", names chairmen and is excluded.
- **Chhatak:** "ইউনিয়ন সমূহ" leads to "ইউনিয়ন পরিষদ চেয়ারম্যান".
- **Companiganj:** the item is a file link.
- **Jagannathpur, Dowarabazar:** the item points to /pages/union, an index without content.
- **Dharmapasha:** has no union or এক নজরে menu item.

## Conflicts and caveats

- **Sylhet Sadar:** 8, with টুলটিকর (DC and registry 7).
- **Balaganj** (page 2019-08-25): lists পশ্চিম পৈলনপুর where the DC has পূর্ব পৈলনপুর. The DC and registry place পশ্চিম পৈলনপুর under Osmaninagar.
- **Habiganj Sadar:** 8 with লোকড়া, without the DC's নূরপুর and শায়েস্তাগঞ্জ.
- **Jamalganj:** 6, with জামালগঞ্জ উত্তর (DC 5).
- **Baniachong:** a trailing unnumbered "বানিয়াচং" line after the numbered list is not taken as a union (the page says ১৫).
- **Derai:** items are printed "০১। রফিনগর ইউনিয়ন (https://rafinagarup.sunamganj.gov.bd)"; the printed addresses are used as websites.
- **Sunamganj Sadar:** a numbered list inside a table cell; split per item.
- **Spellings kept as printed, without a DOUBT flag:** জায়ফরনর, পূবর্জুড়ী (Juri), ভূকশিমইলহ (Kulaura), আজমেরীগঞ্জ পৌরসভা.
- **Pourashavas (8):** from এক নজরে পৌরসভা pages (named by the page title or a "পৌরসভার নাম" row) and one menu link (Sreemangal, sreemangalmunicipality.org).
  - The Shayestaganj and Sunamganj Sadar pourashava pages print no name and are skipped.
  - Kamolganj pourashava's area of 239.14 km² is flagged implausible.
- **Facts:** many এক নজরে pages are old. Population years printed: none 26, 2011 ×3, 2001 ×2, 2022 ×1. Prefer BBS 2022.
  - Kanaighat's "২, ১৫, ২৬০ জন" is read as 215,260 (noted).
- Phone numbers and e-mails are redacted in `raw/`. Sylhet Sadar's এক নজরে names people: its facts are kept, but the raw text is not saved.

## Licence

No licence stated; facts only. Attribution: উপজেলা প্রশাসন, সিলেট বিভাগ — জাতীয় তথ্য বাতায়ন (<upazila>.<district>.gov.bd).
