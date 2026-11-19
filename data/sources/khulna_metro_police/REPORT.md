# Khulna Metropolitan Police (KMP)

- **Sites:**
  - the KMP national-portal site police.khulnadiv.gov.bd (title "পুলিশ কমিশনার"; এক নজরে updated 2024-12-04);
  - the Khulna DC portal "ভৌগলিক পরিচিতি" (8 "মেট্রোপলিটন থানা");
  - KMP's own site kmp.police.gov.bd (linked from the divisional portal) answered HTTP 500.
- Key KHULNA_METRO_POLICE, `"city": 50004`, accessed 2026-11-18. Licence: none stated.
- **fetch.py (`rmp/fetch.py`):** new `--division khulna [--city khulna]` (`main_kmp`). No arguments still runs Rajshahi (outputs checked identical).
- **8 thanas** in areas.csv, Bangla as on the DC portal:
  - দৌলতপুর (Daulatpur), খালিশপুর (Khalishpur), খানজাহানআলী (Khan Jahan Ali), সোনাডাঙ্গা (Sonadanga) — HDX COD-AB 2020 English;
  - কোতয়ালী (Khulna Sadar — HDX/BBS name; KMP calls it "খুলনা থানা");
  - আড়ংঘাটা (Aranghata), হড়িণটানা (Harintana; KMP "হরিণটানা"), লবনচড়া (Labanchara; KMP "লবণচরা") — not in HDX, English transliterated.
  - KMP's names are in the notes.
- **City corporation: 0 of 8 placed.** KMP says its area includes all 31 KCC wards and 5 unions, but no source places individual thanas in KCC, and KCC's site could not be read. (BBS 2022 lists 5 of them — Daulatpur, Khalishpur, Khan Jahan Ali, Khulna Sadar, Sonadanga — inside Khulna City Corporation's census code; see BBS_CENSUS_2022_KHULNA.)
- **facts (13):**
  - established 12 Dec 1984 (government notification); operations from 1 Jun 1986;
  - area 127 km²; population about 32 lakh (estimate, no year);
  - 2 crime divisions (দক্ষিণ, উত্তর);
  - 4 zones (officer cards: দৌলতপুর, খুলনা, সোনাডাঙ্গা, খালিশপুর জোন);
  - 8 thanas; 15 outposts; 3 camps; 9 police boxes;
  - 5 unions and 31 KCC wards in its jurisdiction;
  - jurisdiction text.
- **Phones** are in KHULNA_METRO_POLICE_THANAS_2026.

## Doubts
- The DC portal's thana spellings (হড়িণটানা, লবনচড়া, খানজাহানআলী) differ from KMP's own list; both are kept.
- No thana-to-zone or thana-to-division list is published.
- The এক নজরে figures are undated.
