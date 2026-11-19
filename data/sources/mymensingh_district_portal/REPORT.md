# Mymensingh District portal (mymensingh.gov.bd)

- **Collector:** `rajshahi_district_portal/fetch.py --division mymensingh`.
- **Host:** mymensingh.gov.bd, title "হোম | ময়মনসিংহ জেলা". The divisional portal links it as www.mymensingh.gov.bd.
- **Pages** (`raw/pages.csv`, texts in `raw/`):
  - এক নজরে জেলা (updated 2026-05-04);
  - উপজেলা ও ইউনিয়নের তালিকা (2026-05-04), used as both the upazila list and the union list.
- **areas.csv (140):** district, 12 upazilas, 127 unions, 0 pourashavas.
  - **Union table:** "ক্রমিক | জেলা | উপজেলা | ইউনিয়ন", one "X ইউনিয়ন পরিষদ" per row. The district cell spans all 136 printed rows; each upazila cell spans its own rows (rowspan).
  - **Tarakanda's cell spans 10 rows, but 19 rows follow it** before Dhobaura. The 9 rows after the span (গাজিরভিটা, বিলডোড়া, নড়াইল, ধারা, ধুরাইল, আমতৈল, স্বদেশী, কৈচাপুর, হালুয়াঘাট) have no upazila on the page and are not used (`raw/warnings.txt`). The national list of union portals has them under Haluaghat, which has no cell of its own here. So there is no Haluaghat row: 12 upazilas.
  - জুগলী, the 10th row inside Tarakanda's span, is kept under Tarakanda with a DOUBT note (national list: Haluaghat).
  - The list links no upazila portals. All 12 were verified by fetching `<sub>.mymensingh.gov.bd` (titles in notes).
  - **Union websites:** none printed or linked. 121 come from the national portal's list of union portals (same district, upazila and name; noted per row).
  - 6 unions have no website: চরঈশ্বদিয়া, বাকতা, উত্থুরা, রসুলপুর and বিসকা (spelled differently on the registry), and জুগলী (registry: Haluaghat). Links were not guessed.
  - No union numbers are printed; `code` is empty.
- **Pourashavas:** none. এক নজরে says "১০ টি পৌরসভা ( ০৮টি ক শ্রেণীর, ০১টি খ শ্রেণীর, ০১টি গ শ্রেণীর)" without names, and the menu links no pourashava.
- **facts.csv (23):**
  - এক নজরে (prose): area 4,363.48 km²; population 5,899,052 ("মোট জনসংখ্যা" under the heading "জনশুমারি ও গৃহগণনা ২০২২ অনুযায়ী"; the year is in the heading only, so `year` is empty);
  - from "এটি ১৩টি উপজেলা, ১ টি সিটি করপোরেশন , ১৪টি থানা, ১০ টি পৌরসভা …, ১৪৫ টি ইউনিয়ন, ২২০১টি মৌজা, ২৭০৯টি গ্রাম নিয়ে গঠিত": 13 upazilas, 1 city corporation, 14 thanas, 10 pourashavas, 145 unions, 2,201 mouzas, 2,709 villages;
  - listed counts: 12 upazilas, 127 unions, and unions per upazila.

| Upazila | Unions | Upazila | Unions |
|---|---|---|---|
| Mymensingh Sadar | 11 | Nandail | 13 |
| Muktagacha | 10 | Iswarganj | 11 |
| Fulbaria | 13 | Gouripur | 8 |
| Trishal | 12 | Phulpur | 6 |
| Bhaluka | 11 | Tarakanda | 10 |
| Gafargaon | 15 | Dhobaura | 7 |

## Gaps and conflicts

- **127 listed against 145 stated** (এক নজরে) and 145 on the national list. Seed 146.
  - **Haluaghat** is missing (above). Registry 12.
  - **Gouripur 8:** no বোকাইনগর, ভাংনামারী (registry 10). Its cell declares rowspan 10.
  - **Phulpur 6:** no রামভদ্রপুর, ভাইটকান্দি, রহিমগঞ্জ, রূপসী (registry 10). Its cell declares rowspan 10.
  - **Tarakanda:** no গালাগাঁও; জুগলী printed instead.
- **Against the seed:** Mymensingh Sadar 11 here and on every other source (seed 13); Nandail 13 here and on the registry (seed 12).
- **Spellings kept as printed:** ফুলবাড়িয়া (upazila; registry and seed ফুলবাড়ীয়া), চরঈশ্বদিয়া, তাঁরাটি, বাশাঁটি.
- The city is under Mymensingh City Corporation; there are no city-corporation rows here.
- Raw page texts have phone numbers and e-mails redacted.

## Licence

No licence stated; facts only. Attribution: ময়মনসিংহ জেলা প্রশাসন, জাতীয় তথ্য বাতায়ন (mymensingh.gov.bd).
