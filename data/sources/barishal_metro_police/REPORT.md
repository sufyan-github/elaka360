# Barishal Metropolitan Police (BMP)

- **Sites:**
  - BMP's own site bmp.police.gov.bd (bmp.gov.bd serves the same site): history page, thana pages, "যোগাযোগ";
  - BMP's national-portal site police.barisaldiv.gov.bd (title "পুলিশ কমিশনারের কার্যালয়, বরিশাল বিভাগ"), which has no thana list.
- Key BARISHAL_METRO_POLICE, `"city": 50007`, accessed 2026-11-18. Licence: none stated.
- **fetch.py (`rmp/fetch.py`):** new `--division barishal [--city barishal]` (`main_bmp`). No arguments still runs Rajshahi (outputs checked identical).

## areas.csv: 4 thanas
কোতয়ালী (Kotwali), বন্দর (Bandar), কাউনিয়া (Kaunia), এয়ারপোর্ট (Airport). Bangla is from the BMP history list with "(মডেল) থানা" stripped; English is transliterated. Each row links its thana page, its crime division and the wards that page lists.

**City corporation: 0 of 4 placed.**
- Kotwali: wards 6, 8–26 + Jagua union.
- Kaunia: wards 1–5, 7 + 3 unions.
- Airport: wards 27–30 + 5 unions (3 of them in Babuganj).
- Bandar: 4 unions + part of Dapdapia (Nalchity), and no ward. Its page calls it "প্রস্তাবিত".
- No thana lies wholly in BCC, and BCC does not name its 3 thanas.

## facts.csv (15)
- established 2006 (the page also cites the "বরিশাল মেট্রোপলিটন পুলিশ অধ্যাদেশ ২০০৯");
- area about 447.02 km²;
- 4 thanas; 4 outposts (আলেকান্দা, বগুড়া, আমানতগঞ্জ, স্টীমারঘাট); 1 camp (বরিশাল বিশ্ববিদ্যালয়);
- jurisdiction: BCC + 10 unions of Barishal Sadar + 2.5 unions of Babuganj;
- 2 crime divisions (দক্ষিণ: Kotwali, Bandar; উত্তর: Kaunia, Airport — from the contact page);
- per thana, area km² and population as printed (Kotwali 40.33 / 165,050; Bandar 279.81 / 88,385; Kaunia 111.16 / 127,300; Airport 127.40 / 166,870). No year is given; the pages' tables cite the 2001 census.

## Doubts
- The history page and thana pages are undated.
- Beat-officer pages (officers' names, personal mobiles) are not used. Phones are in BARISHAL_METRO_POLICE_THANAS_2026.
