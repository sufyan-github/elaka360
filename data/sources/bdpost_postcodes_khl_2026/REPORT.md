# Bangladesh Post postcode booklet — Khulna Division

- **Source:** the same undated, image-only postcode booklet on post.rajshahi.gov.bd as the Rajshahi, Rangpur, Dhaka and Chattogram runs. bdpost.gov.bd publishes no office list.
- **Pages:** Khulna Division is in the booklet's "খুলনা রিজিয়ন ৭০০০-৯৯৯৯". Only these pages were transcribed; the Dhaka- and Barishal-Division districts that the region also lists (Rajbari, Faridpur, Madaripur, Shariatpur, Gopalganj, Barishal …) are left out.
  - p. 23 (PDF page 13, right half): Kushtia, Meherpur, Chuadanga, Jhenaidah, Jashore
  - p. 24 (PDF page 14, first column): Narail, Magura
  - p. 26 (PDF page 15, last column): "খুলনা জি, পি, ও ৯০০০", Khulna City head office 9100 and the city offices 9201–9208
  - p. 27 (PDF page 15, right half, up to "সমাপ্ত"): Khulna district, Bagerhat, Satkhira
- **Method:** transcribed by hand from the page images in `raw/` (PDF pages 13, 14 and 15, rotated). `fetch.py --division khulna` checks that the PDF's sha256 is unchanged (it was) and writes the transcription. Accessed 2026-11-18.
- **Licence:** none stated.

## Counts: 166 offices (government.post_office)

| District | Offices |
|---|---|
| Khulna | 39 (10 Khulna city: GPO 9000, City HO 9100, 9201–9208) |
| Bagerhat | 26 |
| Satkhira | 25 |
| Jashore | 21 |
| Kushtia | 17 |
| Jhenaidah | 9 |
| Narail | 9 |
| Chuadanga | 8 |
| Magura | 8 |
| Meherpur | 4 |

- **Types:** SO 52, UPO 48, EDSO 42, TSO 11, HO 10, GPO 1. No type on two rows: খুলনা শিপ ইয়ার্ড (9201, none printed) and চিতলমারী টি, পি, ও (9360, type printed "টি, পি, ও").
- **`extra_json`:** postcode, office type, booklet page.
- **`facts.csv`:** 59 rows of offices per postal group. "Khulna City" covers 9000, 9100 and 9201–9208; no upazila is given for these.

## Gaps and doubts

- **Uncertain readings (flagged):**
  - বাজুয়া (9272): partly covered by a mark.
  - আলমডাংগা (7210), দামুড়হুদা (7220), দৌলতগঞ্জ (7230), হাটবার বাজার (7351): bold print blurred.
  - আন্দুল বাড়ীয়া (7222): first letters faint.
  - নওবেকী (9452): a mark between letters.
  - চাঁচড়া (7402): abbreviations after the name partly illegible.
- **Code outside its range:** কুমিরাদহ ই, ডি, এস, ও is printed "৭৭২১" (7721), outside Jhenaidah's printed range "৭৩০০-৭৩৯৯" (probably 7321). Kept as printed.
- **Upazila inferred (flagged):** the group printed "(দৌলতপুর থানা)" (9220–9224) → Dighalia. Daulatpur is now a metropolitan thana; Dighalia is its own upazila.
- **Postal groups shown as printed:**
  - Mujibnagar Complex (7102) under Meherpur Sadar.
  - Munshiganj (7201) under Chuadanga Sadar.
  - Allar Dargah (7042) under Bheramara.
  - Baradia (7514) under Lohagara.
  - Budhhata (9403) under Satkhira Sadar.
  - Jhaudanga (9412) under Kalaroa.
  - Nagarkandi (9384) under Mollahat.
  - Chaugachha (7410) printed indented under the Jashore head office; Sreepur (7610) under the Magura head office.
- **Printed thana notes kept:** (খোকসা থানা), (দৌলতপুর থানা) for Refayetpur, (জীবন নগর থানা), (কালিগঞ্জ থানা), (অভয় নগর থানা), (লোহাগড়া থানা), (শালিখা থানা), (রুপসা থানা), (ডুমুরিয়া থানা), (দাকোপ থানা), (কয়রা থানা), (স্বরণখোলা থানা), (মংলাপোর্ট থানা), (শ্যামনগর থানা).
- **Booklet spellings kept** (e.g. "চুয়াডাংগা", "মাগুড়া", "কালিয়", "সারসা", "বাঘরপাড়া", "বাটিয়াঘাট", "হরিনাকুন্ড"). Office types are matched ignoring punctuation.
- **Not in the booklet:** branch offices, coordinates and contacts.
