# Chattogram Metropolitan Police (CMP)

- **Sites:**
  - the CMP national-portal site police.chittagongdiv.gov.bd (title "চট্রগ্রাম মেট্রোপলিটন পুলিশ"; এক নজরে updated 2026-10-31);
  - CMP's own site cmp.gov.bd (2013 PHP framework, undated pages; robots.txt disallows only media/admin paths).
- Key CHATTOGRAM_METRO_POLICE, `"city": 50003`, accessed 2026-11-18. Licence: none stated.
- **fetch.py (`rmp/fetch.py`):** new `--city chattogram` (`--division chattogram` runs it). No arguments still runs Rajshahi (outputs checked identical).
- **16 thanas** in areas.csv, as on the CMP এক নজরে list:
  - Kotwali, Bakalia, Chawkbazar, Sadarghat — South crime division (দক্ষিণ);
  - Panchlaish, Chandgaon, Bayezid Bostami, Khulshi — North (উত্তর);
  - Double Mooring, Pahartali, Halishahar, Akbarshah — West (পশ্চিম);
  - Bandar (Port), Patenga, Karnaphuli, EPZ — Port (বন্দর).

  The divisions come from the cmp.gov.bd contact directory. English names are normalised; CMP's own spellings are in the notes.
- **City corporation (area_en): 0 of 16 placed.** CMP says "সিএমপির আওতাধীন এলাকায় চট্টগ্রাম সিটি কর্পোরেশনের অধিকাংশ এলাকা অন্তর্ভুক্ত" (most of CCC). Neither CMP nor CCC places individual thanas, and CCC publishes no thana list. (BBS 2022 lists 15 of these thanas — all but Karnaphuli — inside Chattogram City Corporation's census code; see BBS_CENSUS_2022_CHATTOGRAM.)
  - Karnaphuli's station stands at the old Char Lakshya UP building, outside the city.
  - The DC portal lists the 16 as "মহানগর" thanas, not as city-corporation thanas.
- **facts (11):**
  - established 30 Nov 1978 (Ordinance 1978);
  - 16 thanas now (6 at founding; 12 from 2000);
  - 31 outposts, 5 investigation centres, 6 police boxes;
  - 4 crime divisions;
  - area at founding 128 sq mile; population at founding about 10 lakh;
  - personnel about 6,458;
  - jurisdiction "most of CCC".
- **Cumilla:** no metropolitan police force could be confirmed on an official site. Cumilla city thanas (e.g. Kotwali Model, Sadar Dakkhin Model) appear under Cumilla District Police (police.comilla.gov.bd). No folder was created.
- **Phones** are in CHATTOGRAM_METRO_POLICE_THANAS_2026.

## Doubts
- **HQ location:** CMP's এক নজরে says the HQ is at লালদীঘির পাড়; its যোগাযোগ page gives Dampara Police Lines.
- The history page figures are undated.
