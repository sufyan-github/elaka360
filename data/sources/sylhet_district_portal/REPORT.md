# Sylhet District portal (sylhet.gov.bd)

- **Collector:** `rajshahi_district_portal/fetch.py --division sylhet`.
- **Host:** sylhet.gov.bd, title "হোম | সিলেট জেলা". The divisional portal links it as www.sylhet.gov.bd.
  - The server sends its Let's Encrypt certificate (`*.sylhet.gov.bd`) with a Sectigo chain. The collectors add the Let's Encrypt YR1 intermediate from the CA's AIA address (http://yr1.i.lencr.org/), so TLS stays verified. The same applies to the upazila and union portals under sylhet.gov.bd.
- **Pages** (`raw/pages.csv`, texts in `raw/`):
  - এক নজরে সিলেট জেলা (updated 2026-09-08);
  - উপজেলার তালিকা (2026-09-20);
  - ইউনিয়নের তালিকা (2026-11-16).
- **areas.csv (125):** district, 13 upazilas, 106 unions and 5 pourashavas.
  - Every upazila's portal is linked from the upazila list.
  - **Union table layout:** each upazila is printed above its unions, one union per row, with the portal address in its own column.
  - **Union websites:**
    - 102 are as printed.
    - Osmaninagar prints umorpurup.sylhet.gov.bd for both উমরপুর and পশ্চিম পৈলনপুর. That link is not used; both websites come from the national portal's list of union portals (noted per row).
    - মধ্য জাফলং and বিছনাকন্দি (Gowainghat) print no address and have no registry match, so they have no website.
  - Union numbers are printed only for Golapganj, Zakiganj, Osmaninagar, Jaintiapur and Fenchuganj; `code` is empty for the rest.
  - "পশ্চিম গেীরীপুর" (Balaganj) is kept as printed, with a DOUBT note (malformed).
- **Pourashavas (5):** from এক নজরে: "০৫ টি (গোলাপগঞ্জ-‘ক’শ্রেণী, বিয়ানীবাজার- ‘খ’শ্রেণী, জকিগঞ্জ, কানাইঘাট ও বিশ্বনাথ- ‘গ’ শ্রেণী)".
  - The class after each name is dropped.
  - Parents are inferred from the same-named upazilas.
  - No websites: the portal does not link them.
- **facts.csv (24):**
  - এক নজরে: area 3,452.07 km², population 3,853,570 (census 2022), 13 upazilas, 17 thanas, 106 unions, 1,554 mouzas, 3,497 villages, 1 city corporation, 5 pourashavas;
  - listed counts: 13 upazilas, 106 unions, and unions per upazila.

| Upazila | Unions | Upazila | Unions |
|---|---|---|---|
| Sylhet Sadar | 7 | Gowainghat | 13 |
| Balaganj | 6 | Jaintiapur | 6 |
| Beanibazar | 10 | Kanaighat | 9 |
| Bishwanath | 8 | Zakiganj | 9 |
| Companiganj | 6 | Dakshinsurma | 8 |
| Fenchuganj | 5 | Osmaninagar | 8 |
| Golapganj | 11 | | |

## Gaps and conflicts

- **106 unions:** এক নজরে also says ১০৬. The national list of union portals has 105, the seed 104.
  - **Gowainghat 13:** the registry has 12, without মধ্য জাফলং and বিছনাকন্দি. One of its entries, পশ্চিম আলীরগাঁও, is on paschimalirgaon.gowainghat.sylhet.gov.bd. Seed 9.
  - **Golapganj 11** (seed 10). **Dakshinsurma 8** (seed 10).
  - **Sylhet Sadar 7** (seed 8). The Sylhet Sadar upazila portal lists 8, including টুলটিকর.
- **Spellings that differ from the registry** (kept as printed): বোয়ালজুড়/বোয়ালজুর, বালাগঞ্জ সদর/বালাগঞ্জ, ইসলাম পশ্চিম/ইসলামপুর পশ্চিম, চারখাই/চরখাই, কাজলসার/কাজলশার, কানাইঘাট সদর/কানাইঘাট, পশ্চিমআমুড়া/পশ্চিম আমুরা.
- **The city** is under Sylhet City Corporation; there are no city-corporation rows here.
- Raw page texts have phone numbers and e-mails redacted.

## Licence

No licence stated; facts only. Attribution: সিলেট জেলা প্রশাসন, জাতীয় তথ্য বাতায়ন (sylhet.gov.bd).
