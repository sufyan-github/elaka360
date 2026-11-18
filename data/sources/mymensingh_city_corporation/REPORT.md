# Mymensingh City Corporation (MCC)

- **Site:** mcc.gov.bd (national-portal framework, title "হোম | ময়মনসিংহ সিটি কর্পোরেশন"), linked as "সিটি কর্পোরেশন" from the divisional portal. The office menu's link www.mcc.gov.bd serves a self-signed certificate and was not used.
- Key MYMENSINGH_CITY_CORPORATION, `"city": 50012`, accessed 2026-11-18. Licence: none stated.
- **Pages used:**
  - এক নজরে ময়মনসিংহ সিটি কর্পোরেশন (a scanned one-page PDF, Dec 2024);
  - লোকেশন ও আয়তন;
  - ইতিহাস (2019);
  - the councillor list (scanned PDF, 18.03.2026; ward numbers only);
  - জরুরী যোগাযোগ;
  - the DC portal's "এক নজরে জেলা" (population).
- **fetch.py (`rcc/fetch.py`):** new `--division mymensingh [--city mymensingh]` (`main_mcc`). The figures read from the scanned PDF are hard-coded with the attachment URL, and the run warns if it changes (same practice as the RPCC gazette). No arguments still runs Rajshahi (outputs checked identical).

## areas.csv (34)
- **City corporation row:** website mcc.gov.bd. Note: নগর ভবন, সাবেক ময়মনসিংহ পৌরসভা; CEO office landline 09167446; mayor@mcc.gov.bd. Administrator and CEO mobiles and the CEO's gmail address are not copied.
- **Wards 1–33:** numbers only (`MCC_WARD_NO`; name_bn is a label). The councillor list is titled "৩৩ টি ওয়ার্ড"; officials' names and mobiles are not copied.

## facts.csv (9)
- **Wards:** 33 (scanned এক নজরে).
- **Zones:** 3 (scan; the site also lists zone 1–3 offices).
- **Area:** 91.315 km² (text: "৯১ দশমিক ৩১৫ বর্গ কিঃমিঃ"; the scan agrees).
- **Established:** 2018-10-14 ("১৪ অক্টোবর ২০১৮", scan).
- **Population 2022 (BBS census, as given by MCC):** 576,927 (male 293,582 + female 283,345, which sum correctly).
- **Population projected:** 1,209,902 ("current, by projection of the 2022 census"; basis estimate, method and year not stated).
- **Pourashava established:** 1869 (ইতিহাস).

## Gaps and doubts
- **Population conflict:** the DC portal's "এক নজরে জেলা" gives 5,76,722 for the MCC 2022 census; MCC gives 576,927. The seed has 471,858. The projected figure is more than twice the census figure.
- The scanned figures were read by eye, not machine-checked.
- **Established date:** the scan's 14 Oct 2018 may differ from the date of the formation gazette (not checked).
- No ward names, ward map text or ward-to-thana assignment is published. There is no metropolitan police.
- Officials' names are not copied.
