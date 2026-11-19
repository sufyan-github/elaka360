# Chattogram City Corporation (ccc.gov.bd)

- **Site:** ccc.gov.bd (ccc.org.bd serves the same portal; www.ccc.gov.bd fails TLS). Key CHATTOGRAM_CITY_CORPORATION, `"city": 50003`, accessed 2026-11-18. Licence: none stated.
- **fetch.py (`rcc/fetch.py`):** new `--division chattogram [--city chattogram|cumilla]` (`main_ccc`, `main_cocc`). No arguments still runs Rajshahi (outputs checked identical).
- **Pages:**
  - এক নজরে চসিক (updated 2025-12-07): 41 wards, 6 zones, 60 sq miles, population "৭০ লক্ষ (আনু.)", holdings 2,18,579.
  - ইতিহাস.
  - ওয়ার্ডভিত্তিক মানচিত্র: names of wards 1–41; the maps themselves are attachments and are not copied.
  - যোগাযোগ: Nagar Bhaban (temporary), Batali Hill, Tiger Pass.
- **areas.csv:**
  - 1 city corporation;
  - 41 wards (`Ward N`, code = number, `CCC_WARD_NO`); the ward names CCC gives are in the notes and in facts.csv `ward_name`.
- **facts (49):**
  - wards 41; zones 6;
  - area 60 sq mile (no km² figure published);
  - population 7,000,000 (`estimate`, no year or basis);
  - holdings 218,579;
  - municipality 22 Jun 1863; municipal corporation Sep 1982; city corporation 31 Jul 1990;
  - 41 ward names.

## Gaps and doubts
- **No census population** on the portal. The DC portal gives "চট্টগ্রাম মহানগর" 42,84,249 (census 2022), which is for the metropolitan area, not the city corporation; not used here.
- **Municipal corporation date:** the history text says 16 Sep 1982, its own table says 23 Sep 1982; only the month is kept.
- **Not published:** no ward-to-zone list, no thana list.
- Ward officers' and ward secretaries' lists (names, mobiles) are not copied. The raw history excerpt leaves out officials' names.
