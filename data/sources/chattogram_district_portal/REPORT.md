# Chattogram District portal (chattogram.gov.bd)

- **Collector:** `rajshahi_district_portal/fetch.py --division chattogram`.
- **Host:** chattogram.gov.bd, title "হোম | চট্টগ্রাম জেলা". The national registry lists this host as the Chattogram district portal. chittagong.gov.bd serves the same site (same title and content; each page names its own host as canonical).
  - The portal's own links use *.chittagong.gov.bd, while the registry uses *.chattogram.gov.bd. Both are accepted as this district's portals.
- **Pages** (`raw/pages.csv`, texts in `raw/`):
  - এক নজরে চট্টগ্রাম (updated 2026-11-08);
  - উপজেলার তালিকা (menu "উপজেলা পরিষদ, চট্টগ্রাম", 2026-11-15);
  - ইউনিয়নের তালিকা (2026-06-21).
- **areas.csv (206):** district, 15 upazilas and 190 unions, all with website and source_url.
  - Every union links its portal. Upazila links are on chittagong.gov.bd as printed.
  - Names have "ইউনিয়ন" removed; the printed text is in `notes`.
  - Numbers like "১(ক)নং জুলধা" are kept as code "01(ক)".
- **facts.csv (25):**
  - area 5,283 km²;
  - population 9,169,465 (জনশুমারি ২০২২);
  - 190 unions, 890 mouzas, 1,267 villages;
  - "থানাঃ উপজেলা পর্যায়ে- ১৬টি" (stored as 16 thanas);
  - pourashava ১৫, upazila ১৬ (both inline);
  - unions per upazila and listed counts.

| Upazila | Unions | Upazila | Unions |
|---|---|---|---|
| Rangunia | 15 | Raozan | 14 |
| Banshkhali | 14 | Chandanaish | 9 |
| Lohagara | 9 | Mirsharai | 16 |
| Anwara | 11 | Boalkhali | 9 |
| Sandwip | 14 | Fatikchhari | 17 |
| Karnafuli | 5 | Satkania | 17 |
| Patiya | 17 | Hathazari | 14 |
| Sitakunda | 9 | | |

## Gaps and conflicts

- **15 vs 16 upazilas:** the এক নজরে says ১৬টি; the list has 15. Fatikchhari Uttar (fatikchhariuttar.chattogram.gov.bd, in the national registry) is not on the list.
- **Pourashavas:** the এক নজরে says ১৫. The portal has no pourashava list, so no pourashava rows.
- **The city** is under the Chattogram City Corporation; no city-corporation rows here.
- **Spelling:** the upazila list prints লোহাগড়া (seed and registry: লোহাগাড়া). Kept as printed.
- **ধর্মপুর (Fatikchhari)** carries a registry DOUBT note: the registry's Fatikchhari entry for dharmapurup has only the English title "Dharmapur Union" and a wrong geo name. The union exists on Fatikchhari's own portal, so the note is a false positive.
- 17 union names differ only in spelling from the registry. Kept as printed.

## Licence

No licence stated; facts only. Attribution: চট্টগ্রাম জেলা প্রশাসন, জাতীয় তথ্য বাতায়ন (chattogram.gov.bd).
