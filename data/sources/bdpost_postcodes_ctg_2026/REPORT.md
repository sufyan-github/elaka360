# Bangladesh Post postcode booklet — Chattogram Division

- **Source:** the same undated, image-only postcode booklet on post.rajshahi.gov.bd as the Rajshahi, Rangpur and Dhaka runs. bdpost.gov.bd publishes no office list.
- **Pages:** Chattogram Division is in the booklet's "চট্টগ্রাম রিজিয়ন". Only these pages were transcribed; the Sylhet-Division districts on pp. 14–15 are left out.
  - p. 15 (PDF page 9, right half): Brahmanbaria, Cumilla
  - pp. 16–17 (PDF page 10): Chandpur, Lakshmipur, Noakhali, Feni, then "চট্টগ্রাম জি, পি, ও ৪০০০", the port head office and the city offices 4202–4221
  - pp. 18–19 (PDF page 11, left half and the first column of the right half, up to "রাজশাহী রিজিয়ন"): city offices 4222–4226, Chattogram district, Khagrachhari, Rangamati, Bandarban, Cox's Bazar
- **Method:** transcribed by hand from the page images in `raw/` (PDF pages 9, 10 and 11, rotated). `fetch.py --division chattogram` checks that the PDF's sha256 is unchanged (it was) and writes the transcription. Accessed 2026-11-17.
- **Licence:** none stated.

## Counts: 349 offices (government.post_office)

| District | Offices |
|---|---|
| Chattogram | 102 (27 Chattogram city: GPO 4000, port HO 4100, 25 town offices) |
| Noakhali | 61 |
| Cumilla | 42 |
| Brahmanbaria | 28 |
| Chandpur | 26 |
| Lakshmipur | 26 |
| Feni | 20 |
| Rangamati | 14 |
| Cox's Bazar | 14 |
| Khagrachhari | 8 |
| Bandarban | 8 |

- **Types:** SO 169, UPO 74, EDSO 68, TSO 23, HO 13, GPO 1. One row has no type: "বি,আই, টি পোস্ট অফিস চট্টগ্রামএস, ও" (4349).
- **`extra_json`:** postcode, office type, booklet page.
- **`facts.csv`:** 88 rows of offices per postal group. "Chattogram City" covers 4000, 4100 and 4202–4226; no upazila is given for these.

## Gaps and doubts

- **Uncertain readings of the name (flagged):** বান্দের হাট (3805), মৃধ্যার হাট (3806), চাপরাশির হাট (3811), জমিদার হাট (3825).
- **Codes partly faint (flagged):** 3827, 3828, 3829 (first digits faint) and 4450 মাটিরাংগা (second digit illegible). Read using the printed district ranges ("৩৮০০-৩৮৯৯", "৪৪০০-৪৪৯৯").
- **Upazila inferred (flagged):** the group printed "(মতলব থানা)" (3640–3643) → Matlab Dakshin. Matlab thana is now Matlab Dakshin and Matlab Uttar.
- **Postal groups shown as printed:**
  - Ashuganj (3402, 3403) under Brahmanbaria Sadar.
  - Kabirhat (3807) under Noakhali Sadar.
  - Sonaimuri (3827) under Begumganj.
  - Fulgazi (3942) under Parshuram.
  - Eidgaon (4702) under Cox's Bazar Sadar.
  - The Cumilla head-office group (3500–3505, the old Comilla Sadar) → Cumilla Adarsha Sadar.
- **Printed notes kept:**
  - Sandwip was given 4300 as an exception.
  - Boalkhali (4366) uses the Rangunia series ("পোস্ট কোড সংখ্যা কম হওয়ায় রাংগুনিয়া টিপিও-এর সংখ্যা দেওয়া হইল").
  - Jalaldi (4390) is printed "(বাশখালী থানা)", Kalampati (4510) "(কাউখালী থানা)", Marishya (4590) "(বাগাইছড়ি থানা)", Gorakghata (4710) "(মহেশখালী)", Chiringa (4740) "চকরিয়া থানা)".
- **Booklet spellings and punctuation kept** (e.g. "ব্রাহ্মণবাড়ীয়া", "ফেণী", "বড়ুরা", "মিরশ্বরাই", "জরাছড়ি"). Office types are matched ignoring punctuation.
- **Juldia Marine Academy (4206)** is listed among the city offices; it is kept there as printed.
- **Not in the booklet:** branch offices, coordinates and contacts. Newer upazilas (e.g. Lalmai, Titas, Bijoynagar, Karnaphuli, Guimara, Kamalnagar, Subarnachar, Pekua) have no postal group of their own.
