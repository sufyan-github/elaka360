# Khulna City Corporation

- **KCC's own site could not be read:**
  - khulnacity.gov.bd, linked from the divisional and DC portals, does not resolve; the .gov.bd registry delegates it to BTCL parking name servers.
  - www.khulnacity.org answers HTTP 403 "Missing Authentication Token" to every request.
  - Neither was worked around; both results are in `raw/kcc_site_reachability.txt`.
- Key KHULNA_CITY_CORPORATION, `"city": 50004`, accessed 2026-11-18. Licence: none stated.
- **fetch.py (`rcc/fetch.py`):** new `--division khulna [--city khulna]` (`main_kcc`). No arguments still runs Rajshahi (outputs checked identical).
- **Pages used:**
  - KMP portal এক নজরে (police.khulnadiv.gov.bd, updated 2024-12-04): "৩১টি সিটি কর্পোরেশন ওয়ার্ড এর অন্তর্ভূক্ত";
  - Khulna DC portal "জেলার পটভূমি" (updated 2026-09-15): "১৮৮৪ - খুলনা পৌরসভা প্রতিষ্ঠা" and "৯টি উপজেলা ও একটি সিটি কর্পোরেশন".
- **areas.csv:**
  - 1 city corporation;
  - 31 wards (`Ward N`, code = number, `KCC_WARD_NO`), numbered from the ward count; no ward names or ward list could be read.
- **facts (2):**
  - wards 31 (KMP portal; BBS 2022 also gives 31);
  - municipality established 1884.

## Gaps and doubts
- **Not published on any reachable official page:** area, population, zones, ward names, thana list, KCC address.
- **Population:** the census figure is in BBS_CENSUS_2022_KHULNA (Khulna City Corporation, BBS geocode 40-47-33: 719,557 persons, 2022, enumerated). It is not repeated here.
- **Area:** HDX_COD_AB_BGD_KHULNA has a polygon area of 46.62 km². It is computed by HDX, not an official figure, and not used.
- The ward count comes from a police page that says KMP's area includes the 31 KCC wards; it is not a KCC publication.
