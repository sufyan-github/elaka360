# DISTRICT_PORTALS_TRANSPORT_RANG_2026 — terminals/stands/stations named on Rangpur Division portals

**Source** (trust level 4, accessed 2026-11-17; `raw/` keeps the extracted page text):
- "যোগাযোগ ব্যবস্থা" pages of the district portals: rangpur, panchagarh, dinajpur, lalmonirhat, nilphamari, gaibandha and kurigram `.gov.bd`.
- The Rangpur upazila portals that have one: badargonj, gangachara, kaunia, pirgonj and taragonj. Pirgacha's link is 404; mithapukur and rangpursadar have none.
- The Rangpur City Corporation "এক নজরে" page (rpcc.gov.bd, item ১৩).

**No portal publishes a bus-terminal register.** Rows are places the pages name explicitly; each is re-checked against the live page text by `fetch.py`.

## Collected (23)
| District | Category | Names |
|---|---|---|
| Gaibandha | railway_station (13) | বামনডাঙ্গা, নলডাঙ্গা, কামারপাড়া, কুপতলা, গাইবান্ধা, ত্রিমোহিনী, বাদিয়াখালী, মহিমাগঞ্জ, ভরতখালী, ফুলছড়ি (+ "রেলস্টেশন"), বালাসীঘাট রেলওয়ে ফেরী স্টেশন, বোনারপাড়া জংশন, তিস্তামুখ ঘাট রেলওয়ে স্টেশন |
| Rangpur | railway_station | কাউনিয়া রেলওয়ে জংশন, রংপুর রেলস্টেশন (Gangachara portal), বদরগঞ্জ রেলস্টেশন (Badarganj portal; name composed from "স্টেশন মাস্টার, বদরগঞ্জ") |
| Rangpur | bus_terminal | ঢাকা কোচ স্টান্ড, রংপুর কেন্দ্রীয় বাস টার্মিনাল, পীরগাছা বাস স্টান্ড (RPCC; all inside the city) |
| Dinajpur | railway_station / bus_terminal | দিনাজপুর স্টেশন, দিনাজপুর কেন্দ্রিয় বাস টার্মিনাল (Panchagarh portal travel directions) |
| Lalmonirhat | railway_station | লালমনিরহাট ষ্টেশন, বুড়িমারী ষ্টেশন (district train timetables) |

facts: Rangpur City Corporation has 4 coach/bus/truck stands (RPCC "এক নজরে").

**Gaps:**
- No coordinates, addresses or contacts. `upazila_en` is set only for Badarganj station.
- These pages name no terminal or station, only road lengths, timetables or bus companies: the Rangpur, Dinajpur, Nilphamari and Kurigram district pages, and the Kaunia, Pirganj and Taraganj pages.
- Thakurgaon has no transport page.

## Doubts
- The Gaibandha station list is in a largely historical text; the ferry stations (Balasighat, Tistamukh Ghat) may no longer operate.
- Names composed where the page gives only a place name ("<name> রেলস্টেশন", "দিনাজপুর"/"রংপুর" prefixes, "বুড়িমারী ষ্টেশন"); each note says so.
- The RPCC page is a city-corporation portal, not a district/upazila portal (wider than the Rajshahi run).
- The Badarganj station master's number (malformed mobile) and bus-company counter numbers are not copied.

## Licence
None stated → `null`.
