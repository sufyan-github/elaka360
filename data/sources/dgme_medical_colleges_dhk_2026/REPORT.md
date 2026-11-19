# DGME medical and dental colleges — Dhaka Division

- **Sources** (dgme.gov.bd `/pages/static-pages/`):
  - medical colleges with code, year and MBBS seats (updated 18 Dec 2025);
  - dental colleges and units (20 May 2024);
  - English names and websites of government colleges.
- **Method:** collected with `dgme_medical_colleges_raj_2026/fetch.py --division dhaka`, accessed 2026-11-17. A row is kept when its Bangla name ends in a Dhaka-Division district, or names one. Dental units go in the parent college's `extra_json`.
- **Licence:** none stated.

## Result: 59 colleges (education.medical_college)

| | Government | Private | Total |
|---|---|---|---|
| MBBS colleges | 10 | 39 | 49 |
| Dental colleges | 2 | 8 | 10 |

| District | MBBS govt | MBBS private | Dental |
|---|---|---|---|
| Dhaka | 4 (Dhaka, Sir Salimullah, Shaheed Suhrawardy, Mugda) | 30 | 9 (Dhaka Dental College, govt; 8 private) |
| Gazipur | 1 (Shaheed Tajuddin Ahmad) | 3 | |
| Kishoreganj | 1 (Shahid Syed Nazrul Islam) | 2 | |
| Faridpur | 1 | 1 | |
| Gopalganj | 1 | | 1 (Sheikh Lutfur Rahman Dental College, govt) |
| Manikganj | 1 | 1 | |
| Tangail | 1 | 1 (Kumudini Women's) | |
| Narayanganj | | 1 (US-Bangla) | |
| Narsingdi, Munshiganj, Rajbari, Madaripur, Shariatpur | none | none | none |

Twelve MBBS colleges also have a dental unit (year and BDS seats in `extra_json`):
- The units of Sir Salimullah and Shaheed Suhrawardy are listed without a district suffix and are matched by the parent's exact name.
- Six private units are spelt differently on the dental page and were matched by hand to the parent's college code (noted per row): এম এইচ সমরিতা → এমএইচ সামারিতা (141), গ্রীন লাইফ → গ্রিন লাইফ (139), ডেলটা → ডেল্টা (131), কুমুদিনি → কুমুদিনী উইমেন্স (116), ইব্রাহীম → ইব্রাহিম (118), সমাজ ভিত্তিক, সাভার → গণস্বাস্থ্য সমাজভিত্তিক, সাভার (102).

## Gaps and doubts

- **Not included:** Armed Forces Medical College (code 48, 1999, 125 seats). DGME lists it without a place ("প্রতিরক্ষা মন্ত্রণালয়ের অধীন"). There is no Army Medical College in Dhaka Division in the private table.
- **English names and websites:** found for 6 government colleges (Faridpur, Gazipur, Gopalganj, Kishoreganj, Manikganj, Tangail), with websites for 3 of them. Names are matched by district only where the district has one government MBBS college; Dhaka district has four, so its colleges have none.
- **Faridpur Medical College:** DGME gives the website bsmmc.edu.bd (the college's former name). It is kept as published.
- **Gopalganj dental college:** the year and seat cells read "অনুমোদন | প্রাপ্ত" (approval received). This is kept as `approval_status`; there are no seats or year.
- **Not in the tables:** addresses, phones, upazilas and coordinates. City colleges are `district_en = Dhaka`, with no city corporation assigned.
- **Colleges, not hospitals:** link the college and hospital records; don't merge them.
