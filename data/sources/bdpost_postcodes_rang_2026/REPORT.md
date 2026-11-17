# Bangladesh Post postcode booklet — Rangpur Division

- **Source:** the same undated, image-only postcode booklet on post.rajshahi.gov.bd as the Rajshahi run; bdpost.gov.bd publishes no office list.
- **Pages:** the booklet's "রাজশাহী রিজিয়ন ৫০০০-৬৯৯৯" covers the Rangpur districts:
  - p. 19: Panchagarh, Thakurgaon
  - p. 20: Dinajpur, Nilphamari, Rangpur, Lalmonirhat, Kurigram
  - p. 21: Gaibandha
- **Method:** transcribed by hand from the page images in `raw/` (PDF pages 11–12, rotated). `fetch.py --division rangpur` checks that the PDF's sha256 is unchanged and writes the transcription.
- **Licence:** none stated.

## Counts: 94 offices (government.post_office)

| District | Offices |
|---|---|
| Dinajpur | 19 |
| Rangpur | 15 |
| Kurigram | 13 |
| Gaibandha | 12 |
| Thakurgaon | 10 |
| Nilphamari | 10 |
| Lalmonirhat | 9 |
| Panchagarh | 6 |

- **Types:** UPO 50, SO 26, HO 8, EDSO 6, TSO 4.
- **`extra_json`:** postcode, office type, booklet page.
- **`facts.csv`:** 58 rows of offices per postal group. "Rangpur City" covers the 6 head and town offices 5400–5405, for which no upazila is given.

## Gaps and doubts

- **Kulaghat** (কূলাঘাট এস, ও, Lalmonirhat) is printed "৫৪০২", the same code as Alamnagar TSO (Rangpur); probably a misprint of 5502. Kept as printed, id `postcode:5402-lalmonirhat`.
- **Upazila inferred** (thana not printed, flagged): Setabganj UPO → Bochaganj, Tushbhandar UPO → Kaliganj, Bonarpara UPO → Saghata.
- **Old spellings kept:** কাহালোর থানা (Kaharole), কিশোরীগঞ্জ, হাতীবান্দা, নাগেশ্বর, রানী সংকাইল, পলাশবাড়, ভূরুংগামারী.
- The Dinajpur heading prints "৫২০০-৫২৯০".
- Branch offices are not in the booklet; there are no coordinates or contacts.
