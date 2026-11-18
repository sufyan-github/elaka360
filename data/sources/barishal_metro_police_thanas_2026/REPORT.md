# BARISHAL_METRO_POLICE_THANAS_2026 — BMP thanas and official numbers

**Source** (trust level 4, accessed 2026-11-18):
- bmp.police.gov.bd: history page (thana list) and "যোগাযোগ" (division-wise tables of posts and police official mobiles);
- police.barisaldiv.gov.bd: "ডাক যোগাযোগ" (HQ address, phones, fax) and "অনলাইন যোগাযোগ" (e-mails, control-room mobile).

`"city": 50007`. Licence: none stated.

**fetch.py (`rmp_thanas_2026/fetch.py`):** new `--division barishal [--city barishal]` (`main_bmp`).

## Collected: 6 places, 2 facts
- **4 × `emergency.police_station`** (`upazila_en` holds the BMP thana), each with the OC's and the duty officer's official mobiles (01320-06xxxx):
  - কোতয়ালী মডেল থানা 01320065826 / 01320065833;
  - বন্দর থানা 01320065496 / 01320065503;
  - কাউনিয়া থানা 01320065744 / 01320065751;
  - এয়ারপোর্ট থানা 01320065634 / 01320065641.
- **1 × `government.sp_office`:** বরিশাল মেট্রোপলিটন পুলিশ হেডকোয়ার্টার্স, বান্দ রোড, দক্ষিণ আলেকান্দা, বরিশাল, ৮২০০.
  - Phone 02478871150 and the Commissioner post's official mobile 01320064000.
  - E-mail pcbmp@police.gov.bd; dchqbmp@police.gov.bd.
- **1 × `emergency`:** পুলিশ কন্ট্রোলরুম, বিএমপি — 01320066998, plus command & control 01320066999.
- **facts:** police_stations 4; police_stations_placed_in_city_corporation 0.

**City corporation: 0 of 4 placed** (`area_en` empty). BCC names no thanas, and BMP's thana pages list BCC wards together with rural unions (Bandar: unions only).

## Doubts
- The HQ's second phone ("০২৪৭৮৮-২১৭৬১৭৬") and its fax are printed with 13 digits; they are kept only as printed in `extra_json`.
- Inspectors', beat officers' and ACs' numbers and all officers' names are not copied.
- No addresses for the thanas.
