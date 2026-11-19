# Barishal City Corporation (BCC)

- **Site:** barishalcity.gov.bd, linked from the Barishal DC portal. It is not on the national-portal framework (pages are /info/<slug>). bcc.gov.bd is the Bangladesh Computer Council, not BCC.
- Key BARISHAL_CITY_CORPORATION, `"city": 50007`, accessed 2026-11-18. Licence: none stated.
- **Pages used:**
  - এক নজরে বরিশাল সিটি (published 2024-03-27);
  - ইতিহাস;
  - লোকেশন (ওয়ার্ড ভিত্তিক) — one JPG, no text;
  - যোগাযোগ;
  - the 4 BMP thana pages (which wards each thana lists).
- **fetch.py (`rcc/fetch.py`):** new `--division barishal [--city barishal]` (`main_bcc`, `bcc_page`, `bmp_thana_wards`). No arguments still runs Rajshahi (outputs checked identical).

## areas.csv (31)
- **City corporation row:** website barishalcity.gov.bd. Note: Nagar Bhaban, ফজলুল হক এভিনিউ; phone 02478864015; contact@barishalcity.gov.bd.
- **Wards 1–30:** numbers only (`BCC_WARD_NO`; name_bn is a label), from "৩০টি ওয়ার্ড". Each ward notes which BMP thana page lists it (BBS 2001): Kotwali 6, 8–26; Kaunia 1–5, 7; Airport 27–30.

## facts.csv (26)
- **Wards:** 30 (official; 30 general + 10 reserved-seat councillors).
- **Area:** 58 km² (no year).
- **Population:**
  - about 5 lakh (500,000; estimate, "বর্তমানে", no year or basis);
  - 2011 census as quoted by BCC: 328,278 (male 169,475, female 158,803), 72,709 households, literacy 75.3%;
  - BCC's population table: 1872–2001 (12 rows).
- **Mahallas:** 225. **Thanas:** 3 (not named).
- **History:**
  - town committee 1869; municipality 1876; first-class pourashava 1985;
  - city corporation 2002-07-25 (after the বরিশাল সিটি কর্পোরেশন আইন, ২০০১ and its 2002 amendment).

## Gaps and doubts
- No ward names or ward list as text (the ward page is an image).
- BCC's "৩টি থানা" conflicts with BMP's 4 thanas. BMP's pages suggest the 3 that contain wards are Kotwali, Kaunia and Airport, but BCC does not name them, so no thana is placed.
- BMP's ward lists are from BBS 2001 (pre-2002 pourashava wards), so the ward numbering may have changed since.
- Officials' names (administrator, CEO, past chairmen and mayors) are not copied.
