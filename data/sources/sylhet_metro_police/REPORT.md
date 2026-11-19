# Sylhet Metropolitan Police (SMP)

- **Sites:**
  - SMP's national-portal site police.sylhetdiv.gov.bd (title "হোম | পুলিশ কমিশনার"): "এক নজরে" (English, updated 2022-08-27) and "যোগাযোগ";
  - SMP's own site smp.police.gov.bd: the home page's thana list (Bangla names; the list links to Wikipedia, and those links are not used).
  - smp.gov.bd does not respond.
- Key SYLHET_METRO_POLICE, `"city": 50006`, accessed 2026-11-18. Licence: none stated.
- **fetch.py (`rmp/fetch.py`):** new `--division sylhet [--city sylhet]` (`main_smp`). No arguments still runs Rajshahi (outputs checked identical).

## areas.csv: 6 thanas
কোতোয়ালী (Kotwali), জালালাবাদ (Jalalabad), এয়ারপোর্ট (Airport), দক্ষিণ সুরমা (South Surma), মোগলাবাজার (Moglabazar), শাহপরান (Shahporan). English is as in SMP's "এক নজরে"; Bangla is from SMP's home page, with "(মডেল) থানা, সিলেট" stripped.

**City corporation: 0 of 6 placed.** SMP says its area is about 518.43 km² "including 27 wards of Sylhet City Corporation, 08 Unions of Sylhet Sadar Upazila and 10 Unions of South Surma Upazilla" but gives no per-thana breakdown, and SCC (now 42 wards) names no thanas.

## facts.csv (4)
- established 2006-08-26 (offices from 26 Oct 2006; SMP ordinance 2006, Act 2009);
- area about 518.43 km²;
- 6 thanas;
- jurisdiction: 27 SCC wards + 8 Sylhet Sadar unions + 10 South Surma unions. Its area of responsibility was published 2011-05-10, with full operation from 2011-08-11.

## Doubts
- The "এক নজরে" page dates from 2022 and its "27 wards" predates SCC's 42.
- No thana pages, areas or populations are published.
- The SMP thana sub-sites on the Sylhet Sadar portal (e.g. shahporanpolice.sylhetsadar.sylhet.gov.bd) fail TLS (hostname mismatch) and were not read.
- Phone numbers are in SYLHET_METRO_POLICE_THANAS_2026.
