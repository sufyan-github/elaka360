# Dhaka Metropolitan Police (dmp.gov.bd)

- **Site:** dmp.gov.bd (WordPress; pages carry no update date; robots.txt only disallows /wp-admin/). Key DHAKA_METRO_POLICE, `"city": [50001, 50002]`, accessed 2026-11-17.
- **fetch.py (`rmp/fetch.py`):** new `--city dhaka|gazipur` option; `--division dhaka` without `--city` runs DMP and GMP into their own folders. No arguments still runs Rajshahi (outputs checked identical).
- **50 thanas** in areas.csv: the 49 stations of "Find Your Local Police" plus Hatirjheel, which only the Dhaka DC portal's city-thana list names. DMP's history page says "50 police stations".
  - Bangla names from the Dhaka DC portal list ("এক নজরে ঢাকা জেলা"); Khilkhet is not on that list, so its Bangla spelling is the DNCC ward-area spelling. English names as DMP spells them.
  - The DC list has 51 entries with two duplicates (লালবাগ, কাফরুল) and lacks Khilkhet.
- **City corporation (area_en): 0 of 50 placed.** DMP's jurisdiction is DNCC + DSCC, but no official source found places individual thanas in either: DMP gives no list, DNCC and DSCC publish none (DSCC gives only a count of 23), the Dhaka DC portal lists the 50 without a city corporation, and DMP's beat-map PDF (2020) is in a legacy font with beat officers only. Every thana row says so in its notes.
- **facts:** established 1 Feb 1976 with 12 police stations; 50 thanas now; 8 crime divisions (Gulshan, Lalbag, Mirpur, Motijheel, Ramna, Tejgaon, Uttara, Wari; no thana-to-division list); population "almost 2.0 cores" (sic, about 20 million; `estimate`); about 34,000 personnel, sanctioned 32,987.
- **Phones** are in DHAKA_METRO_POLICE_THANAS_2026.
- Licence: none stated.
