# Bangladesh Post postcode booklet — Dhaka Division

- **Source:** the same undated, image-only postcode booklet on post.rajshahi.gov.bd as the Rajshahi and Rangpur runs. bdpost.gov.bd publishes no office list.
- **Pages:** Dhaka Division is in two regions of the booklet. Only these districts were transcribed; the Mymensingh-Division districts on pp. 12–13 are left out.
  - "ঢাকা রিজিয়ন ১০০০-২৯৯৯":
    - p. 9: Dhaka city, Dhaka district, Narayanganj
    - pp. 10–11: Narayanganj, Munshiganj, Narsingdi, Gazipur, Manikganj, Tangail
    - pp. 12–13: Tangail, Kishoreganj
  - "খুলনা রিজিয়ন", pp. 24–25: Rajbari, Faridpur, Madaripur, Shariatpur, Gopalganj
- **Method:** transcribed by hand from the page images in `raw/` (PDF pages 6, 7, 8 and 14, rotated). `fetch.py --division dhaka` checks that the PDF's sha256 is unchanged (it was) and writes the transcription. Accessed 2026-11-17.
- **Licence:** none stated.

## Counts: 291 offices (government.post_office)

| District | Offices |
|---|---|
| Dhaka | 51 (24 Dhaka city incl. Demra group) |
| Tangail | 41 |
| Munshiganj | 33 |
| Gazipur | 24 |
| Narayanganj | 21 |
| Kishoreganj | 21 |
| Narsingdi | 18 |
| Manikganj | 18 |
| Faridpur | 17 |
| Madaripur | 13 |
| Gopalganj | 13 |
| Shariatpur | 12 |
| Rajbari | 9 |

- **Types:** SO 110, UPO 77, EDSO 68, TSO 20, HO 13, GPO 1. Two rows have no type: সফিপুর "এ, টি, সি" and লক্ষ্মীপুর "স, ও".
- **`extra_json`:** postcode, office type, booklet page.
- **`facts.csv`:** 86 rows of offices per postal group. "Dhaka City" covers GPO 1000, Sadar HO 1100, the 1200-series town offices and the Demra group (1360–1362), for which no upazila is given.

## Gaps and doubts

- **Postcodes not legible (left empty; id `office:<district>:<name>`):** রসুলপুর ই, ডি, এস, ও (Munshiganj, after 1511), নলিয়া সি. এস, ও (Rajbari, after 7730) and ফরিদপুর হেড অফিস (the code column shows only a mark).
- **Uncertain reading:** "রূপাতপাত ই, ডি, এস, ও" (7861).
- **Upazila inferred** (the postal group is a thana, flagged): Fatullah and Siddhirganj → Narayanganj Sadar; মন্নু নগর (টংগী থানা) group → Gazipur Sadar.
- **Postal groups shown as printed:** ধনবাড়ী এস, ও is under Madhupur (Dhanbari is now its own upazila); রাজেন্দ্রপুর is in the Sreepur group.
- **Left out:** খাস কাউলিয়া ইউ, পি, ও (1930) is printed under Tangail with "(সিরাজগঞ্জ জেলার চৌহালী থানা)". Chauhali is in Sirajganj, Rajshahi Division.
- **Booklet spellings and punctuation kept** (e.g. "এস,ও", "ই, ডি এস ও"); office types are matched ignoring them.
- **Not in the booklet:** branch offices, coordinates and contacts. Kalukhali, Dasar and other newer upazilas have no office.
