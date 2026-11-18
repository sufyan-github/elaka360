# Bangladesh Post postcode booklet — Mymensingh Division

- **Source:** the same undated, image-only postcode booklet on post.rajshahi.gov.bd as the earlier division runs. bdpost.gov.bd publishes no office list.
- **Pages:** Mymensingh Division is in the booklet's Dhaka region. Only these pages were transcribed:
  - p. 12 (PDF page 8, left half): "জামালপুর জেলা ২০০০-২০৯৯", "শেরপুর জেলা ২১০০-২১৯৯" and "ময়মনসিংহ জেলা ২২০০-২২৯৯", up to "কিশোরগঞ্জ জেলা ২৩০০-২৩৯৯" (Dhaka Division, already collected).
  - p. 13 (PDF page 8, right half, first column): "নেত্রকোনা জেলা ২৪০০-২৪৯৯".
- **Method:** transcribed by hand from `raw/postcode_booklet_pp12-13.png`, PDF page 8 at its native 150 dpi, rotated (the same file as in the Sylhet folder). `fetch.py --division mymensingh` checks that the PDF's sha256 is unchanged (it was) and writes the transcription. Accessed 2026-11-18.
- **Licence:** none stated.

## Counts: 78 offices (government.post_office)

| District | Offices |
|---|---|
| Mymensingh | 36 |
| Jamalpur | 21 |
| Netrokona | 14 |
| Sherpur | 7 |

- **Types:** SO 34, UPO 30, EDSO 10, HO 4.
- **`extra_json`:** postcode, office type, booklet page.
- **`facts.csv`:** 34 rows of offices per postal group.

## Gaps and doubts

- **All 78 codes are legible.** Faint codes, flagged:
  - 2040 (মাদারগঞ্জ, last digit);
  - 2430 (কলমাকান্দা), 2440 (বারহাট্টা), 2446 (মোহনগঞ্জ), 2460 (খালিয়াজুরী), 2462 (শালদিঘা).
- **Uncertain name readings, flagged:** যমুনা সার কারখানা (2055, "কারখানা"), বৌখরহাটি (2401), শ্যামগঞ্জ (2411), সাকুয়াই (2417).
- **Offices printed under another district:**
  - বকশীগঞ্জ ইউ, পি, ও (2140) is printed under Sherpur; Bokshiganj upazila is in Jamalpur, so `district_en = Jamalpur`.
  - ধোবাউরা ইউ, পি, ও (2416) and সাকুয়াই (2417) are printed under Netrokona; Dhobaura upazila is in Mymensingh, so `district_en = Mymensingh`.
  - All three rows carry a note.
- **Left out (Sylhet Division):** ধরমপাশা ইউ,, পি, ও (2450) and মধ্যনগর ইউ, পি, ও (2456) are printed in the Netrokona section but belong to Sunamganj District. They fill a gap noted in the Sylhet report; the Sylhet folder was not changed.
- **Postal groups shown as printed:**
  - **Head-office groups are given as the Sadar upazila:** Mymensingh (9 offices) → Mymensingh Sadar; Jamalpur, Sherpur and Netrokona → their Sadar upazilas.
  - Phulpur group: তারাকান্দা এস, ও (2252); Tarakanda is now its own upazila.
  - ধলা এস, ও (2223) is printed without an indent after the Trishal group; kept in it.
  - সুসং ইউ, পি, ও (2420): upazila inferred as Durgapur (Susang Durgapur, the upazila seat; no thana printed).
- **No postal group printed** for Dhobaura in the Mymensingh section, and none for Tarakanda.
- **Booklet spellings kept:** "নালিতাবাড়", "ঝিনাইগাত", "ধোবাউরা", "ইউ, পি,ও". Office types are matched ignoring punctuation.
- **Not in the booklet:** branch offices, coordinates and contacts.
