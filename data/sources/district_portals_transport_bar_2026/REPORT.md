# DISTRICT_PORTALS_TRANSPORT_BAR_2026 — launch ghats, stands and airport named on Barishal Division portals

**Source** (trust level 4, accessed 2026-11-18):
- the "যোগাযোগ ব্যবস্থা" pages of the barisal, jhalakathi, patuakhali, pirojpur and bhola DC portals (Barguna links none);
- the "যোগাযোগ" pages of the upazila portals that name a ghat or stand: Bakerganj, Banaripara, Gaurnadi, Agailjhara, Kathalia, Bauphal, Bhandaria, Bhola Sadar, Tazumuddin. 24 of the 42 upazila portals link such a page; all 24 were read.

Licence: none stated → `null`. No portal publishes a terminal register. Rows are names the pages state explicitly, re-checked against the live text. `raw/` keeps only the lines carrying the matched phrases.

**fetch.py:** a `barishal` entry in `SITES`, plus an optional per-division `facts` list (regex on page text) that is unused for the other divisions.

## Collected (15)

| District | Category | Name |
|---|---|---|
| Barishal | bus_terminal | নথুল্লাবাদ বাসস্ট্যান্ড; রূপাতলী বাস স্টেশন (composed from "বাস স্টেশন (রূপাতলী, বরিশাল)"); বানারীপাড়া বাস স্ট্যান্ড (Banaripara); গৌরনদী বাসস্ট্যান্ড (Gaurnadi) |
| Barishal | bus_stop | বাকেরগঞ্জ বাসষ্ট্যান্ড (Bakerganj) |
| Barishal | airport | বরিশাল বিমানবন্দর |
| Barishal | launch_ghat | বরিশাল লঞ্চঘাট (Bhola Sadar page; Gaurnadi's says "লঞ্চঘাট, বরিশাল") |
| Jhalokathi | launch_ghat | আমুয়া নদী বন্দর (Kathalia) |
| Patuakhali | launch_ghat | বগা লঞ্চঘাট |
| Pirojpur | launch_ghat | হুলারহাট লঞ্চ ঘাট (DC and Bhandaria pages) |
| Bhola | launch_ghat | ভোলা খেয়াঘাট; ভেদুরিয়া লঞ্চঘাট; ভোলা লঞ্চ ঘাট |
| Bhola | bus_terminal | ভোলা কেন্দ্রিয় বাস ষ্টেশন (name composed) |
| Bhola | transport | তজুমদ্দিন টেম্পু ষ্টেশন (Tazumuddin) |

**Facts (2):**
- Barishal–Dhaka launch route: 22 vessels (Barishal DC page);
- Hularhat–Dhaka Sadarghat: 11 launches (Pirojpur DC page).

No coordinates, addresses or contacts. Launch and bus company counter numbers are not copied.

## Gaps
- Route headings that name no ghat are not rows: ইলিশা-ঢাকা, লালমোহন-ঢাকা, বেতুয়া-ঢাকা, হাতিয়া-মনপুরা-ইলিশা-ঢাকা (Bhola); "ঝালকাঠি সদরঘাট-ঢাকা" (Jhalokathi).
- Dhaka-side terminals (Sadarghat, Gabtali, Sayedabad) are not rows. Kalapara's "ঢাকা-পটুয়াখালী লঞ্চঘাট" is ambiguous and is not a row.
- Patuakhali's DC page names no terminal; Barguna has no transport page.

## Doubts
- "ভোলা লঞ্চ ঘাট" and "ভোলা খেয়াঘাট" may be the same ghat.
- The airport also appears in the CAAB source.
- Most rows have no upazila because the pages do not state one.
