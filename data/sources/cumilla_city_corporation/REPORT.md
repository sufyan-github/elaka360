# Cumilla City Corporation (cocc.portal.gov.bd)

- **Site:** cocc.portal.gov.bd, linked from the Cumilla DC portal. comillacity.gov.bd and cumillacity.gov.bd do not resolve. Key CUMILLA_CITY_CORPORATION, `"city": 50009`, accessed 2026-11-18. Licence: none stated.
- **Key page:** "এক নজরে কুমিল্লা সিটি কর্পোরেশন" is a scanned 5-page PDF ("At a glance", 2024) with no text layer.
  - Page 1, General Information, read from the image: Area 53.04 km², Ward 27, Population "08 lac", Holding 52,600.
  - `fetch.py` checks the PDF's sha256 (54492ac7…) and warns if it changes. `raw/` holds the transcription, not the 11.8 MB PDF.
- **areas.csv:** 1 city corporation and 27 wards (numbers only; no ward names are published as text).
- **facts (4):**
  - wards 27;
  - area 53.04 km²;
  - population 800,000 (`estimate`, "08 lac", no year or basis);
  - holdings 52,600.

## Gaps and doubts
- The values were transcribed by eye from a scan, not OCR'd. The other 4 pages (markets, roads, water) are not transcribed.
- No establishment date, ward names, zones or thana list are published as text. The ward-secretary list is a PDF of names and mobiles and is not used.
- No census population on the portal.
