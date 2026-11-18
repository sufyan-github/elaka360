# Bangladesh Post postcode booklet — Barishal Division

- **Source:** the same undated, image-only postcode booklet on post.rajshahi.gov.bd as the Rajshahi, Rangpur, Dhaka, Chattogram and Khulna runs. bdpost.gov.bd publishes no office list.
- **Pages:** Barishal Division is in the booklet's "খুলনা রিজিয়ন ৭০০০-৯৯৯৯". Only these pages were transcribed:
  - p. 25 (PDF page 14, right half), from the heading "বরিশাল জেলা ৮২০০-৮২৯৯": Barishal, Bhola and the Jhalokathi head-office group. The Gopalganj (Dhaka Division) section above it is left out.
  - p. 26 (PDF page 15, left half): the rest of Jhalokathi, then Pirojpur, Patuakhali and Barguna, up to the heading "খুলনা জি, পি, ও ৯০০০" (Khulna Division, already collected).
- **Method:** transcribed by hand from the page images in `raw/` (PDF pages 14 and 15, rotated; the same two images as in the Khulna folder). `fetch.py --division barishal` checks that the PDF's sha256 is unchanged (it was) and writes the transcription. Accessed 2026-11-18.
- **Licence:** none stated.

## Counts: 118 offices (government.post_office)

| District | Offices |
|---|---|
| Barishal | 45 (43 printed under Barishal, plus the 2 Banaripara offices printed under Pirojpur) |
| Pirojpur | 23 |
| Patuakhali | 16 |
| Bhola | 14 |
| Jhalokathi | 12 |
| Barguna | 8 |

- **Types:** SO 43, EDSO 35, UPO 32, HO 6. Two rows have no type: গজারিয়া (8332) and নিয়ামতী (8432), whose type is printed "এস, এ".
- **`extra_json`:** postcode, office type, booklet page.
- **`facts.csv`:** 38 rows of offices per postal group. The booklet has no postal group for Rangabali, Taltali or Indurkani.

## Gaps and doubts

- **Uncertain readings (flagged):** ধামড়া (8221) and জুগারকান্দা (8222), both blurred in the print.
- **Partly covered:** বরিশাল হেড অফিস (8200), where "হেড অ" sits under an ink mark. ওসমান মঞ্জিল এস, ও (8261) has a pen mark across its type.
- **Codes printed twice or outside their range (kept as printed, flagged):**
  - কানুদাসকাঠি (Bhandaria) is printed "৮৫৫০", the same code as Bhandaria UPO; probably 8551. Its id is `postcode:8550-pirojpur`.
  - বীরপাশা "৮৫২২" and কালিসড়ি "৮৫২৩" (Bauphal) are outside Patuakhali's printed range "৮৬০০-৮৬৯৯" and repeat two Pirojpur codes; probably 8622 and 8623. Their ids are `postcode:8522-patuakhali` and `postcode:8523-patuakhali`.
- **Banaripara (8530, 8531):** printed under the Pirojpur district heading (postal grouping). Banaripara upazila is in Barishal District, so both rows are `district_en = Barishal`, `upazila_en = Banaripara` (flagged).
- **Upazila inferred (flagged):**
  - স্বরুপকাঠি group (8520–8523) → Nesarabad. Swarupkathi is the upazila's former name.
  - সুবিদখালী group (8610–8611) → Mirzaganj.
  - খেপুপাড়া group (8650–8651) → Kalapara.
  - কালাইয়া (8624) → Bauphal. It is printed without an indent after the Bauphal group, and its code is in Bauphal's 862x range.
- **Postal groups shown as printed:**
  - The Barishal head-office group (8200–8207) is given as Barishal Sadar. The booklet has no separate Barishal-city section, so no row is left at city level.
  - দুমকী (8602) is under Patuakhali Sadar; Dumki is now its own upazila.
  - The Pirojpur head-office group (8500–8502) is given as Pirojpur Sadar. পারেরহাট (8502) may now lie in Indurkani (formerly Zianagar) upazila; not re-assigned.
- **Printed thana notes kept:** (হিজলা থানা), (বাখরগঞ্জ থানা), (তজমুদ্দিন থানা), (মনপুরা থানা).
- **Booklet spellings kept** (e.g. "আগৈলঝারা", "বানড়ীপাড়া", "গলাচিপ", "কাউখালি", "মেহেন্দীগঞ্জ ইউ,, পি, ও"). Office types are matched ignoring punctuation.
- **Not in the booklet:** branch offices, coordinates and contacts.
