# DISTRICT_PORTALS_TRANSPORT_MYM_2026 — terminals and stations named on Mymensingh Division portals

**Source** (trust level 4, accessed 2026-11-18):
- the "যোগাযোগ ব্যবস্থা" page of the jamalpur DC portal;
- the "যোগাযোগ ব্যবস্থা" / "যোগাযোগ" pages of the Fulbaria, Muktagacha, Iswarganj, Phulpur, Tarakanda, Dewangonj, Bokshiganj and Nalitabari upazila portals;
- Mymensingh City Corporation's "বাস টার্মিনাল" page (mcc.gov.bd).

All 4 DC and 35 upazila portals were scanned for such pages. The Mymensingh DC page gives a 2019 train timetable and bus departure places but names no terminal. The Sherpur and Netrokona DC pages name none. Licence: none stated → `null`.

**fetch.py:** a `mymensingh` entry in `SITES` (pages, entries, facts). Rows are kept only if the phrase is still on the live page. `raw/` keeps only the lines carrying the matched phrases.

## Collected (12)

| District | Category | Name |
|---|---|---|
| Mymensingh | railway_station | ময়মনসিংহ রেলওয়ে জংশন (Fulbaria "ময়মনসিং রেলওয়ে জংসন", normalised); বিসকা রেলস্টেশন (Tarakanda; composed from "বিসকা ইউনিয়নে আন্তঃজেলা রেল স্টেশন") |
| Mymensingh | bus_terminal | মাসকান্দা / টাঙ্গাইল / শম্ভগঞ্জ আন্তঃজেলা বাস টার্মিনাল (MCC; printed "বাসর্টামিনাল"; Masakanda also on the Iswarganj page); হালুয়াঘাট বাসস্ট্যান্ড (Phulpur page) |
| Jamalpur | railway_station | জামালপুর রেল স্টেশন (Bokshiganj page; the DC timetable says "জামালপুর জং"); দেওয়ানগঞ্জ রেলওয়ে স্টেশন (Dewangonj) |
| Jamalpur | bus_terminal | বাসটার্মিনাল (বিশ্ব রোড়), জামালপুর and বাসটার্মিনাল (ছনকান্দা), জামালপুর (DC bus table; composed); দেওয়ানগঞ্জ বাসস্ট্যান্ড (printed "বাস স্যান্ড"; Dewangonj) |
| Sherpur | bus_terminal | নালিতাবাড়ী বাসস্টেশন (Nalitabari) |

**Facts (1):** Iswarganj railway_stations = 3 (upazila portal, "রেল স্টেশন : ৩ টি"; stations not named).

No coordinates, addresses or contacts. The Jamalpur station-master and GRP landlines and the bus company counter numbers are not copied.

## Gaps
- **Not rows:**
  - Dhaka-side terminals (Mohakhali, Kamalapur);
  - Kaoraid station (Bhaluka page; in Gazipur, outside the division);
  - bus company counters and departure places not called a stand or terminal (পাটগুদাম, ময়লাকান্দা, স্টেডিয়াম, কাচারীঘাট, ভকেশনাল মোড়);
  - "শেরপুর বাসস্ট্যান্ড" on the Phulpur page (place unclear);
  - Bahadurabad Ghat (named only as a rail-route end);
  - Nokla's unnamed "প্রধান বাস ষ্টেশন".
- Upazila is set only where the page states it (4 rows).

## Doubts
- "বিসকা রেলস্টেশন" is composed from the union name; the station's own name is not given.
- The MCC terminals' locations within the city are not given.
