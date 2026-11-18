# Sylhet City Corporation (SCC)

- **Site:** scc.gov.bd (national-portal framework, title "হোম | সিলেট সিটি কর্পোরেশন"), linked from the Sylhet DC portal. sylhetcity.gov.bd does not respond.
- Key SYLHET_CITY_CORPORATION, `"city": 50006`, accessed 2026-11-18. Licence: none stated.
- **Pages used:**
  - আমাদের নগরী – এক নজরে সিসিক (updated 2026-02-25);
  - ওয়ার্ড সচিব (ward numbers only);
  - যোগাযোগ;
  - for comparison: DC portal "এক নজরে সিলেট জেলা", SP portal "একনজরে", SMP "এক নজরে".
- **fetch.py (`rcc/fetch.py`):** new `--division sylhet [--city sylhet]` (`main_scc`), with the Let's Encrypt intermediates for this city. No arguments still runs Rajshahi (outputs checked identical).

## areas.csv (43)
- **City corporation row:** website scc.gov.bd. Note: নগর ভবন, সিলেট; office telephones 02996633045, 02996633381. The page's e-mails are script-obfuscated and not collected.
- **Wards 1–42:** numbers only (`SCC_WARD_NO`; name_bn is a label), as listed on the ward-secretary page ("সাধারণ-০১" … "সাধারণ-৪২"). Secretaries' names and mobiles are not copied.

## facts.csv (6)
- **Wards:** 42 (official), the same as the DC portal.
- **Councillors:** 42 general, 14 reserved-seat.
- **Area:** 79.50 km² (no year).
- **Population:** about 10 lakh ("১০ ( লাখ আনুমানিক)"), an estimate with no year or basis.
- **Established:** 2002-07-28.

## Gaps and doubts
- No ward names, ward map text or ward-to-thana assignment is published.
- **Ward count conflict:** the SP portal (updated 2023: "ওয়ার্ড ২৭ টি") and SMP's "এক নজরে" (its 2011 jurisdiction, "27 wards") give an older count. It is noted on the wards fact.
- No census figure is published by SCC.
- Officials' names (administrator, CEO, past mayors) are not copied.
