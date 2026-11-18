# Bangladesh Post postcode booklet — Sylhet Division

- **Source:** the same undated, image-only postcode booklet on post.rajshahi.gov.bd as the earlier division runs. bdpost.gov.bd publishes no office list.
- **Pages:** Sylhet Division is at the start of the booklet's "চট্টগ্রাম রিজিয়ন ৩০০০-৪৯৯৯". Only these pages were transcribed:
  - p. 13 (PDF page 8, right half), from "সুনামগঞ্জ জেলা ৩০০০-৩০৯৯": Sunamganj and the start of the Sylhet head-office group. The print is faded.
  - p. 14 (PDF page 9, left half): Sylhet, Moulvibazar ("মৌলভী বাজার জেলা ৩২০০-৩২৯৯") and Habiganj ("হবিগঞ্জ জেলা-৩৩০০-৩৩৯৯").
  - p. 15 (PDF page 9, right half, first column): the rest of Habiganj, up to "ব্রাহ্মণবাড়ীয়া জেলা ৩৪০০-৩৪৯৯" (Chattogram Division, already collected).
- **Method:** transcribed by hand from the page images in `raw/`:
  - `postcode_booklet_pp12-13.png` is PDF page 8 at its native 150 dpi, rotated. The Dhaka folder's copy of this page is downscaled and too faint for p. 13.
  - `postcode_booklet_pp14-15.png` is the same file as in the Chattogram folder.
  - `fetch.py --division sylhet` checks that the PDF's sha256 is unchanged (it was) and writes the transcription. Accessed 2026-11-18.
- **Licence:** none stated.

## Counts: 123 offices (government.post_office)

| District | Offices |
|---|---|
| Sylhet | 55 |
| Moulvibazar | 24 |
| Sunamganj | 22 |
| Habiganj | 22 |

- **Types:** SO 75, UPO 30, EDSO 12, HO 4, TSO 2.
- **`extra_json`:** postcode, office type, booklet page.
- **`facts.csv`:** 34 rows of offices per postal group.

## Gaps and doubts

- **Codes not readable (postcode empty, id `office:…`, flagged):**
  - সিলেট হেড অফিস, সিলেট ক্যাডেট কলেজ টি, এস, ও and সিলেট বিমান বন্দর টি, এস, ও: code illegible.
  - খাদিম নগর এস, ও and জালালাবাদ ক্যান্টনমেন্ট এস, ও: "৩১০" plus an illegible digit.
  - খুরমা ই, ডি, এস, ও: "৩০৮" plus an illegible digit.
  - কেরামত নগর ভানুগাছ এস, ও: printed "৩২২", one digit missing.
- **Rows left out (cannot be read):**
  - three rows after খুরমা in the Chhatak group (p. 13, 308x range);
  - two rows in the Barlekha group (p. 14). Only "জুরি …" (code illegible) and "দক্ষি…" with code 3252 are legible.
- **Uncertain readings (faded print, flagged):**
  - ঘুংগিয়ার গাও (3050), সৈয়দপুর (3061), আতুয়াজান বরকাপন (3062), হাসান ফাতেমাপুর (3063);
  - ছাতক সিমেন্ট ফ্যাক্টরী (3081), গোবিন্দগঞ্জ নতুন বাজার (3084);
  - বিয়ানীবাজার (3170): the first letter has a stray mark;
  - শাহাজী বাজার (3332): the last letter is unclear.
- **Postal groups shown as printed:**
  - **Head-office groups are given as the Sadar upazila:** Sylhet head office (14 offices) → Sylhet Sadar, Sunamganj → Sunamganj Sadar, Moulvibazar → Moulvibazar Sadar, Habiganj → Habiganj Sadar. Several Sylhet head-office offices may now lie in Dakshin Surma upazila; they are not re-assigned.
  - Balaganj group: তাজপুর and গোয়ালা বাজার are now in Osmani Nagar.
  - Sunamganj head-office group: পাগলা is now in South Sunamganj.
  - Habiganj head-office group: শায়েস্তাগঞ্জ, now its own upazila.
  - Gowainghat group: জাফলং is printed without an indent; চিকনাগুল is in this group as printed.
- **Printed thana notes kept:** (জামালগঞ্জ থানা) on সাচনা, (দিরাই থানা) on দিরাই চাঁদপুর, (সাল্লা থানা) on ঘুংগিয়ার গাও, (কোম্পানীগঞ্জ থানা) on কোম্পানীগঞ্জ নতুন বাজার (printed "বাজা র"), and (লাখাই থানা) on কালাউক.
- **No legible postal group** for Dharmapasha, Madhyanagar, South Sunamganj, Osmani Nagar, Dakshin Surma, Shayestaganj or Juri (Juri may be the illegible 3251 row).
- **Booklet spellings kept:** "বিশ্বম্বরপুর", "শ্রীমংগল", "মৌলভী বাজার", "নবিগঞ্জ", "ইউ, পি ও". Office types are matched ignoring punctuation.
- **Not in the booklet:** branch offices, coordinates and contacts.
