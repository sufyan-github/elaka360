# Barishal District portal (barishal.gov.bd)

- **Collector:** `rajshahi_district_portal/fetch.py --division barishal`.
- **Host:** barishal.gov.bd, title "হোম | বরিশাল জেলা". The divisional portal links the DC portal as barishal.gov.bd.
  barisal.gov.bd serves the same site (same title), and the national registry has the Barishal upazila portals on
  barisal.gov.bd.
- **Pages** (`raw/pages.csv`, texts in `raw/`):
  - এক নজরে বরিশাল (updated 2026-05-21);
  - উপজেলার তালিকা (2026-09-30);
  - ইউনিয়নের তালিকা (2026-11-16).
- **areas.csv (105):** district, 10 upazilas, 88 unions and 6 pourashavas.
  - Every upazila has its portal linked from the list.
  - The union table ("উপজেলা | ইউনিয়ন সংখ্যা | ইউনিয়নসমূহ") prints one comma list per upazila and links no union
    portal. 77 union websites come from the national portal's list of union portals (same upazila and name, noted
    per row); 11 have no match there and stay empty.
  - The list has no union numbers, so `code` is empty. The total row "সর্বমোট (১০টি উপজেলা) | ৮৮" is skipped.
- **facts.csv (19):**
  - এক নজরে: area 2,784.52 km², population 2,570,446 (no year printed), 1,001 mouzas, 1,116 villages, 10 upazilas,
    6 pourashavas;
  - listed counts: 10 upazilas, 88 unions, and unions per upazila;
  - stated: "১০টি উপজেলা এবং ৮৮ টি ইউনিয়ন".

| Upazila | Unions | Upazila | Unions |
|---|---|---|---|
| Barisal Sadar | 10 | Hizla | 6 |
| Gournadi | 7 | Wazirpur | 9 |
| Muladi | 7 | Bakerganj | 14 |
| Mehendiganj | 16 | Agailjhara | 5 |
| Babuganj | 6 | Banaripara | 8 |

## Gaps and conflicts

- **88 unions:** the registry also has 88; the seed has 85 (Mehendiganj 13).
  - Mehendiganj: the DC list has 16, including উলানিয়া উত্তর/দক্ষিণ, শ্রীপুর and আদর্শনগর. The registry has 16 with
    জয়নগর and without শ্রীপুর/আদর্শনগর.
  - Muladi: the DC prints ছবিপুর; the registry has সফিপুর.
  - Spellings without a registry match (no link taken): শায়েস্তাবাদ/সায়েস্তাবাদ, নলচিরা/নলচিড়া,
    হিজলা-গৌরবদি/হিজলা গৌরাব্দি, বড়াকোটা/বরাকোঠা, চরএক্করিয়া/চরএককরিয়া, বিদ্যানন্দপুর/বিদ্যানন্দনপুর,
    দরিরচর-খাজুরিয়া/দড়িরচর খাজুরিয়া.
- **Upazila list:** prints "আগৈলঝড়া" for আগৈলঝাড়া; kept as printed, with a DOUBT note.
- **Pourashavas:** there is no list page; the menu has only a page of mayors, which is not used.
  - The 6 come from এক নজরে: "পৌরসভা - ৬ টি | গৌরনদী, মুলাদী, বাকেরগঞ্জ, মেহেন্দিগঞ্জ, বানারীপাড়া, উজিরপুর।".
  - Parents are inferred from the same-named upazilas. No websites.
- **The city** is under Barishal City Corporation; there are no city-corporation rows here.
- Raw page texts have phone numbers and e-mails redacted.

## Licence

No licence stated; facts only. Attribution: বরিশাল জেলা প্রশাসন, জাতীয় তথ্য বাতায়ন (barishal.gov.bd).
