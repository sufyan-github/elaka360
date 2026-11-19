# Rangpur Divisional Commissioner portal (rangpurdiv.gov.bd)

- **Collector:** `rajshahi_divisional_portal/fetch.py --division rangpur` (generic division mode). Pages found through the
  portal menu: এক নজরে রংপুর বিভাগ, জেলার তালিকা, উপজেলার তালিকা, ইউনিয়নের তালিকা (all updated 2025-04-20). Page texts in
  `raw/`; `raw/pages.csv` lists URL, status and update date.
- Unlike Rajshahi, the union list is an HTML table (no PDF), so it is parsed, not transcribed by hand.
- **areas.csv (601):**
  - 8 districts (website = DC portal, not linked from the page);
  - 58 upazilas (`code` = list serial, `RANGDIV_LIST_SERIAL`);
  - 535 unions (`code` = "N নং" where printed, `UNION_NO_IN_UPAZILA`).
  - English district and upazila names are the project's keys, not printed.
- **facts.csv (71):**
  - division এক নজরে: area 16,374.091 km², population 17,610,956, 58 upazilas, 60 thanas, 31 pourashavas, 536 unions, 6,710 mouzas, 9,066 villages;
  - list counts;
  - one `union_count` per upazila.

| District | Upazilas | Unions listed |
|---|---|---|
| Rangpur | 8 | 76 |
| Panchagarh | 5 | 43 |
| Dinajpur | 13 | 103 |
| Lalmonirhat | 5 | 45 |
| Nilphamari | 6 | 60 |
| Gaibandha | 7 | 82 |
| Thakurgaon | 5 | 53 |
| Kurigram | 9 | 73 |

## Conflicts and caveats

- **535 vs 536 unions:** list heading ৫৩৫ টি and 535 rows; the division এক নজরে says ৫৩৬. The eight DC portals list 535.
- **Stale for Thakurgaon:** the lists (2025-04) predate the new রুহিয়া and ভূল্লী upazilas.
  - Their 11 unions are listed under ঠাকুরগাঁও সদর: 21 here vs 11 on thakurgaon.gov.bd (2026-07).
  - Only 5 Thakurgaon upazilas are listed (DC portal: 7).
  - The division's "58 upazilas" is stale for the same reason: with Ruhia and Bhulli it is 60.
- **Palashbari (Gaibandha):** 9 unions here (includes পলাশবাড়ী); 8 on the DC portal and on palashbari.gaibandha.gov.bd.
- **Badargonj:** union numbers run ৬–১৫ নং (same on the upazila portal).
- **Upazila misprints** flagged DOUBT: বালয়িাডাঙ্গী (Baliadangi), আতিদমারী (Aditmari), নাবাবগঞ্জ (Nawabganj). Also printed:
  রানীশংকৈল, সাদুল্যাপুর, রাজিবপুর (চর রাজিবপুর), and "সদর" alone for Rangpur Sadar.
- **Spelling:** 52 union names differ only in spelling from the DC portal lists (e.g. খোরাগাছ / খোড়াগাছ); kept as printed.
- **No union portal links** on these pages (`website` empty for unions).

## Licence

No licence stated. Only facts (names, counts, figures) are taken. Attribution: Office of the Divisional Commissioner,
Rangpur (rangpurdiv.gov.bd), Bangladesh National Portal.
