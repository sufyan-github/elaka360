# SYLHET_METRO_POLICE_THANAS_2026 — SMP thanas and official numbers

**Source** (trust level 4, accessed 2026-11-18):
- police.sylhetdiv.gov.bd: "এক নজরে" (thana list), "যোগাযোগ" (HQ address, control room, hotline), officer cards;
- smp.police.gov.bd: home page (Bangla thana names) and "যোগাযোগ" (same numbers).

`"city": 50006`. Licence: none stated.

**fetch.py (`rmp_thanas_2026/fetch.py`):** new `--division sylhet [--city sylhet]` (`main_smp`), with the Let's Encrypt intermediates for this force.

## Collected: 8 places, 2 facts
- **6 × `emergency.police_station`** (`upazila_en` holds the SMP thana): কোতোয়ালী মডেল থানা, জালালাবাদ থানা, এয়ারপোর্ট থানা, দক্ষিণ সুরমা থানা, মোগলাবাজার থানা, শাহপরান থানা.
  - **No phone or e-mail:** SMP publishes no thana numbers. Its officer cards cover the Commissioner, deputy/additional commissioners and zone ACs, with no OC cards; zone AC numbers are not thana contacts and are not used.
- **1 × `government.sp_office`:** সিলেট মেট্রোপলিটন পুলিশ হেডকোয়ার্টার্স, বাড়ি নং-২২৮, সড়ক নং-১/এ, ব্লক-এফ শাহজালাল উপশহর, সিলেট. Commissioner's office 02997700789 and the Commissioner post's official mobile 01320067000; pcsmp@police.gov.bd.
- **1 × `emergency`:** এসএমপি কন্ট্রোল রুম 01320069998; hotline 01320069999.
- **facts:**
  - police_stations = 6;
  - police_stations_placed_in_city_corporation = 0. No official source places an SMP thana in SCC: SMP's area covers 27 (old count) SCC wards plus 18 unions, with no breakdown. `area_en` is empty on every row.

## Gaps
- Thana numbers are missing. The smp.police.gov.bd "সদর বিভাগ" page is a scanned PDF and is not used.
- The thana sub-sites x.sylhetsadar.sylhet.gov.bd fail TLS (hostname mismatch) and were skipped.
- Officers' names are not copied.
