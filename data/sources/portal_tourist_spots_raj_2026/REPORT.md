# "দর্শনীয় স্থান" lists on district and upazila portals — Rajshahi Division

- **Source:** `/pages/tourist-spot` (with `?page=N`) on the 8 district and 67 upazila portals (the old `/bn/site/view` paths are gone). Descriptions are not copied. Licence: none stated.

## Counts: 304 rows

By district: Pabna 58, Bogura 53, Rajshahi 44 (9 district portal + 35 upazila portals), Chapainawabganj 43, Naogaon 33, Natore 29, Joypurhat 22, Sirajganj 22. Rajshahi by upazila: Puthia 16, Bagha 5, Paba 4, Durgapur 4, Charghat 3, Godagari 2, Tanore 2, Bagmara 1, city/none 7. Categories (keyword rules): tourism 83, religious_site 60, historical 53, religious.mazar 34, river_haor 30, natural 17, park 10, archaeological 8, museum 6, education 3. `facts.csv`: entries per portal (75 rows).

## Gaps and cleaning

No coordinates (9 Google Maps links kept in `extra_json`, unused); no phones (the "contact" field usually holds a UNO/OC number or directions). Empty lists: Mohanpur, Badalgachhi, Kazipur, Sirajganj district portal. Leading numbering and ", upazila" suffixes stripped (original title in `extra_json`); locations over 120 characters dropped; "…জেলার ইতিহাস" entries skipped; places on both district and upazila portals flagged.

Pilot matches (no coordinates): Puthia Rajbari, Bagha Mosque ("বাঘা শাহী মসজিদ"), Shah Makhdum shrine ("শাহ্ মখদুমের মাজার"), Varendra Research Museum, University of Rajshahi, Rajshahi College.
