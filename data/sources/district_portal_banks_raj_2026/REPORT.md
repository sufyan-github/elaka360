# DISTRICT_PORTAL_BANKS_RAJ_2026 — bank lists on district portals

**Source:** DC-office portals (trust level 4), accessed 2026-11-12: rajshahi.gov.bd "ব্যাংক", natore.gov.bd "ব্যাংক",
naogaon.gov.bd "ব্যাংক". `raw/` keeps the extracted table text.

## Collected (94 × `finance.bank`)
| District | Rows | Notes |
|---|---|---|
| Rajshahi | 48 | 7 bank-office rows (Bangladesh Bank Rajshahi, Sonali, Rupali, Janata, Agrani, Uttara zonal/GM offices, RAKUB HQ — numbers by post in `extra_json.office_numbers`), 16 named branches of Sonali/Rupali/Janata/Agrani/Uttara, 25 private banks listed "…, রাজশাহী" with one number (branch not specified) |
| Natore | 19 | branches in Natore town (`upazila_en = Natore Sadar`), numbers without area code |
| Naogaon | 27 | branches/regional offices in Naogaon town, 0741- numbers |

Phone 94/94; no addresses, routing numbers, opening hours or coordinates.
Branch names on the Rajshahi page are composed as "<bank>, <branch> শাখা" from the heading + row.

## Not usable
Bogura, Joypurhat, Sirajganj portals: bank **names only**; Chapainawabganj: unnamed file attachment; Pabna Sadar upazila page:
copied Google-Maps listing (not official data). Bangladesh Bank publishes no branch list (see BB_SCHEDULED_BANKS_RAJ_2026).

## Data quality
- Lists are undated and old (pre-2020 landline formats; "রম্নয়েট শাখা" is a typo, probably রুয়েট/RUET).
- Natore: "জনতা ব্যাংক লিঃ, একাডেমী শাখা" listed twice with different numbers (62277, 62314); 62314 is also given for
  "জনতা ব্যাংক লিঃ, স্টেশন বাজার". Agrani "সাহেব বাজার শাখা" shares (0721) 772393 with Agrani's AGM office.
- State Bank of India is listed under "বেসরকারী ব্যাংকসমূহ" (it is a foreign bank). Ownership left empty for the first table
  (not labelled state/private by the source).

## Pilot places
None. Related: অগ্রণী ব্যাংক "রাজশাহী বিশ্ববিদ্যালয় শাখা" (branch on the RU campus) and রূপালী ব্যাংক "রম্নয়েট শাখা" (RUET).

## Licence
None stated → `null`.
