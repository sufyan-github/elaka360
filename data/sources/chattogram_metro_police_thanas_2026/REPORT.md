# CHATTOGRAM_METRO_POLICE_THANAS_2026 — Chattogram Metropolitan Police

**Source** (trust level 4, accessed 2026-11-18; `"city": 50003`):
- cmp.gov.bd:
  - "Information Of Police Station": English addresses;
  - contact directory pages of the South, North, West and Port divisions: OC and duty-officer numbers;
  - "Head Quater": Commissioner post;
  - "Emergency Helpline": control room.
- The CMP portal (police.chittagongdiv.gov.bd): এক নজরে thana list; যোগাযোগ for the HQ address, phone and e-mail.

**fetch.py (`rmp_thanas_2026/fetch.py`):** new `--city chattogram` (`main_cmp`, parser for the label/number contact pages). No arguments still runs Rajshahi (outputs checked identical).

## Collected: 18 rows (all Chattogram District)
- **16 × `emergency.police_station`:**
  - Phone = the OC's and duty officer's police official mobiles (01320-05xxxx), on all 16.
  - Address in English as printed, on all 16.
  - `extra_json`: crime division, OC/duty mobiles, directions, `area_en` (empty).
  - `upazila_en` holds the metropolitan thana; "Karnaphuli" is also the upazila where that station stands.
- **1 × `government.sp_office`:** চট্টগ্রাম মেট্রোপলিটন পুলিশ সদর দপ্তর — 031-624100, Commissioner post mobile 01320052000, pccmp@police.gov.bd; address "দামপাড়া পুলিশ লাইন্স, দামপাড়া, চট্টগ্রাম চট্টগ্রাম-৪০০০" (as printed).
- **1 × `emergency`:** CMP Police Control Room — 01320057998, 01676123456, 0241360912. Ranges printed "-99" and "-14" are kept as the first number; the full text is in `extra_json`. Traffic control numbers are in `extra_json`.
- **facts:** 16 police stations; 0 placed in a city corporation.

## City corporation
**0 of 16 thanas placed** (`area_en` empty) by this source: CMP covers "most of" CCC and no CMP or CCC page gives a thana-to-city-corporation list (see CHATTOGRAM_METRO_POLICE).

## Doubts
- cmp.gov.bd pages are undated. The e-mails there are obfuscated and are not decoded or copied. CMP's own spellings ("Bakolia", "Karnophuli", "Panclaish circle") are kept in `name_en` and addresses.
- Not copied: inspectors' mobiles, ACs' numbers, officers' names.

## Licence
None stated → `null`.
