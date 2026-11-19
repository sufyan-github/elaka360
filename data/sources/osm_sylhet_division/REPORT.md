# OpenStreetMap points of interest — all 8 divisions (OSM_*_2026)

This report covers all eight `osm_<division>_division` folders. They are built by one collector
(`osm_rajshahi_division/fetch.py --division <name>|all`) from one copy of the OSM data. Each folder has the same report.

- **Source:** OpenStreetMap, from Geofabrik's Bangladesh extract `bangladesh-latest.osm.pbf`. The file was
  `bangladesh-261117.osm.pbf`, 356,120,580 bytes, md5 `a6674376d933fdbd1fc2a0abd9255000`, downloaded 2026-11-18.
- **OSM data timestamp:** `2026-11-17T21:24:30Z`, replication sequence 4942 (from the .pbf header).
- **Licence:** ODbL-1.0. Attribution: "© OpenStreetMap contributors". ODbL is share-alike: if we publish a database
  built from these rows, it must be offered under ODbL with attribution.
- **Trust:** `community_dataset`, trust level 1. No row is verified, and none may be marked `verified` or
  `production_eligible`.
- **Not committed:** the .pbf and the parsed national candidate list. `fetch.py` downloads the file again and checks
  the md5. The extract was parsed locally with pyosmium 4.3.2. Only one HTTP download was made. No Overpass queries
  were run.

## Rows per division

| Division | Folder | Key | Rows | Business | Religious | Education | Transport | Health | Finance | Government | Other | Tourism | Emergency | Agriculture | Phone | Website | Email | Dropped: outside division polygon¹ | Duplicates merged | No upazila² | places.csv bytes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Rajshahi | osm_rajshahi_division | OSM_RAJ_2026 | 9,983 | 3,296 | 1,850 | 1,579 | 793 | 594 | 537 | 434 | 383 | 252 | 125 | 140 | 95 | 96 | 44 | 1,139 | 161 | 989 | 3,416,278 |
| Rangpur | osm_rangpur_division | OSM_RANG_2026 | 7,142 | 2,216 | 1,425 | 1,097 | 543 | 571 | 402 | 310 | 255 | 135 | 82 | 106 | 72 | 54 | 19 | 950 | 86 | 1,049 | 2,596,205 |
| Dhaka | osm_dhaka_division | OSM_DHK_2026 | 40,047 | 19,569 | 3,803 | 4,377 | 2,153 | 3,523 | 2,713 | 1,017 | 1,359 | 634 | 774 | 125 | 1,321 | 1,072 | 409 | 10,929 | 1,273 | 27,358 | 15,265,219 |
| Chattogram | osm_chattogram_division | OSM_CTG_2026 | 17,143 | 6,648 | 2,426 | 2,428 | 1,322 | 1,014 | 1,169 | 580 | 731 | 420 | 215 | 190 | 272 | 209 | 109 | 4,566 | 397 | 6,515 | 6,100,055 |
| Khulna | osm_khulna_division | OSM_KHL_2026 | 7,118 | 2,010 | 1,328 | 1,440 | 421 | 531 | 319 | 281 | 332 | 175 | 232 | 49 | 129 | 62 | 30 | 3,507 | 230 | 568 | 2,321,635 |
| Barishal | osm_barishal_division | OSM_BAR_2026 | 5,018 | 920 | 1,048 | 1,111 | 221 | 178 | 120 | 220 | 178 | 96 | 794 | 132 | 29 | 30 | 15 | 303 | 129 | 374 | 1,573,861 |
| Sylhet | osm_sylhet_division | OSM_SYL_2026 | 3,740 | 1,200 | 744 | 648 | 308 | 215 | 266 | 123 | 113 | 66 | 47 | 10 | 75 | 78 | 30 | 1,041 | 42 | 831 | 1,264,385 |
| Mymensingh | osm_mymensingh_division | OSM_MYM_2026 | 5,547 | 1,977 | 1,011 | 951 | 256 | 379 | 267 | 310 | 209 | 64 | 63 | 60 | 57 | 37 | 23 | 3,009 | 61 | 971 | 2,046,445 |
| **Total** | | | **95,738** | 37,836 | 13,635 | 13,631 | 6,017 | 7,005 | 5,793 | 3,275 | 3,560 | 1,842 | 2,332 | 812 | 2,050 | 1,638 | 679 | | 2,379 | | |

¹ This counts features that lie inside the division's bounding box but outside its HDX polygon. Most of them belong
to a neighbouring division, which includes them, or to India, Myanmar or the sea. Nationally, 121,254 candidates were
parsed. Of these, 368 are in no division polygon (210 named, 158 unnamed): they are in neighbouring countries, at sea,
or in slivers between simplified borders. No feature was assigned to two divisions.

² These rows have no upazila because they lie inside a city corporation polygon, which HDX COD-AB keeps separate from
upazilas. Such a row keeps its district, carries `extra_json.city_corporation`, and has the note
"inside <X> City Corporation (no upazila polygon)". Three rows (Dhaka 2, Barishal 1) fall in a boundary sliver
between upazilas and keep only their district. No row is missing a district.

Every places.csv is a single file under 20 MB, so no places_2.csv was needed. The largest is Dhaka at 15.3 MB.
`stats.json` in each folder has the full counts: categories, upazilas, drop reasons and the tag combinations behind
top-level keys. SOURCE.json lists each file with its sha256.

## What was kept

- **Elements:** named nodes. Ways are placed at their area centroid (closed ways) or the mean of their nodes (open
  ways). Multipolygon relations are placed at their area centroid. Every non-node row says which in
  `extra_json.geometry`.
- **Tags selected:** `amenity`, `shop`, `office`, `healthcare`, `tourism`, `historic`, `leisure`, `craft`,
  `emergency`, plus:
  - `railway=station|halt` and `public_transport=station`;
  - named `highway=bus_stop`;
  - `aeroway=aerodrome`;
  - named `man_made` features (`works`, `water_tower`, `water_works`, `lighthouse` …);
  - named `landuse=cemetery`;
  - named institutional or commercial buildings;
  - names containing "cold storage" or "হিমাগার".
- **Unnamed features kept:** only ATMs, fuel stations, police, fire, ambulance and disaster shelters, plus toilets and
  drinking water tagged with a public `access=yes|public|permissive|customers`.
  - Unnamed rows total 1,267 and are flagged "unnamed in OSM". They are mostly ATMs (about 700) and fuel stations.
- **Dropped:** 22,769 classified candidates in total. The main reasons:
  - Unnamed features: toilets (3,584, mostly Rohingya-camp latrines in Teknaf and Ukhiya), places of worship (1,688),
    schools (969), drinking water (666), shops, restaurants and pitches.
  - Furniture: benches, waste baskets, waste disposal.
  - Hostels and student messes (494).
  - Campus sub-buildings (439).
- **Private residences and private persons:** dropped.
  - Building-only features, and `tourism=apartment` (166, mostly residential blocks).
  - `office=yes` or bare buildings named as a house (*bari*, *basa*, *villa*, *manzil* …), 221. Circuit houses, rest
    houses and warehouses are excepted.
  - Named `leisure=garden` plots (808; mostly "Betel nut garden of <person>"). Gardens named as a park or eco-park are
    kept, and nurseries go to `agriculture.nursery`.
  - Family graveyards and `access=private` leisure, toilets and water.
- **Names:**
  - `name_bn` takes `name:bn`, else `name` when that is in Bangla script.
  - `name_en` takes `name:en`, else `name` when that is in Latin script.
  - A mixed "Latin বাংলা" name is split into the two fields when the split is clean. Otherwise it is kept whole in
    the field of its first script.
  - All names are NFC-normalised.
  - The original `name` is kept in `extra_json.name` when it differs.
- **Contacts and address:** `phone`, `website` and `email` are copied as published on the feature. Phone comes from
  `contact:phone`, `phone`, `contact:mobile` or `mobile`. Website comes from `contact:website`, `website`, `url` or
  `contact:facebook`. `address` is built from the `addr:*` tags. These contacts belong to businesses and
  organisations, but some doctors' chambers (`amenity=doctors`) carry a doctor's own name.
- **extra_json:** OSM type and id, the main tags, `operator:type`, `brand`, `brand:wikidata`, `wikidata`, `religion`,
  `cuisine`, `fuel:*`, alternative names, and ids merged into the row. `opening_hours` and `operator` have their own
  columns. `ownership` comes from `operator:type`.
- **source_url:** `https://www.openstreetmap.org/<type>/<id>`.
- **District and upazila:** by point-in-polygon against the HDX COD-AB polygons already in the repository
  (`hdx_cod_ab_bgd/` for Rajshahi, `hdx_cod_ab_bgd_<division>/` for the others). The seed's English names come from
  that folder's `crosswalk.csv`, for example "Bogra Sadar" and "Mohonpur". Every HDX district, upazila and city
  corporation code mapped to a seed name.
- **Duplicates within OSM:** 2,379 merged in total. The same element can only appear once.
  - Two features are merged when they have the same normalised name and the same category, and lie within the
    area's half-diagonal (50–500 m) for a node + way/relation, or within 50 m otherwise.
  - The feature with the most tags is kept. The merged ids go in `extra_json.merged_osm` and in a note.
  - Dhaka has 883 node + node merges: mostly identical names within 50 m, such as bank booths and repeated chain
    shops.

## Proposed new subcategories

Rows that fit no sub-category were given the closest top-level key. The counts below are for all divisions together;
`stats.json` has the counts for each division.

| Top-level key used | OSM tags (count) | Proposed subcategory |
|---|---|---|
| business (4,306) | `man_made=works` 1,660, `building=industrial` 566, `building=warehouse` 32 | business.factory (factories, mills, garment works) |
| business | `tourism=hotel` 855, `tourism=guest_house` 231, `leisure=resort` 119, `building=hotel` 25, `tourism=motel` 23, `tourism=chalet` 11 | business.hotel (lodging) |
| business | `building=commercial` 580, `building=office` 56, `building=retail` 39 | none: named commercial buildings or complexes; could go to business.shopping |
| business | `amenity=bar` 27, `amenity=pub` 14, `amenity=nightclub` 6 | business.bar |
| education (3,220) | `amenity=school` 1,851, `office=educational_institution` 578, `building=school` 292 | none: these are schools whose level is not stated |
| education | `amenity=kindergarten` 210, `building=kindergarten` 11, `amenity=prep_school` 17 | education.kindergarten |
| education | `amenity=library` 179 | education.library |
| education | `office=research` 46, `amenity=research_institute` 21 | education.research_institute |
| government (1,982) | `office=government` 1,727 | none: offices whose type is not stated |
| government | `office=energy_supplier` 57, `office=water_utility` 7 | government.utility_office (Palli Bidyut, WASA …) |
| government | `amenity=prison` 57 | government.prison |
| government | `office=diplomatic` 54 | government.embassy |
| other (2,237) | `leisure=playground` 1,207, `leisure=pitch` 249, `leisure=stadium` 133, `leisure=sports_centre` 61, `leisure=swimming_pool` 40, `leisure=golf_course` 9, `leisure=sports_hall` 8, `amenity=dojo` 7 | other.sports_venue / playground (খেলার মাঠ) |
| other | `amenity=cinema` 144, `amenity=theatre` 44, `amenity=arts_centre` 29, `amenity=studio` 90 | other.culture_entertainment |
| other | `amenity=social_facility` 123, `amenity=refugee_site` 9, `amenity=animal_shelter` 6 | other.social_welfare |
| other | `office=political_party` 38, `office=cooperative` 11, `office=union` 5 | other.organisation |
| religious (485) | `amenity=grave_yard` 236, `landuse=cemetery` 109, `amenity=crematorium` 12 | religious.graveyard (কবরস্থান / শ্মশান) |
| religious | `amenity=place_of_worship` 109 | none: the religion is not stated |
| agriculture (294) | `shop=agrarian` 185, `shop=farm` 61 | agriculture.input_dealer (seed, fertiliser, feed) |
| agriculture | `amenity=veterinary` 46 | agriculture.veterinary |
| tourism (339) | `tourism=attraction` 202, `tourism=camp_site` 72, `tourism=artwork` 50, `man_made=lighthouse` 8 | tourism.attraction / monument |
| finance (182) | `office=insurance` 98, `office=financial` 28, `amenity=bureau_de_change` 22, `shop=money_lender` 21 | finance.insurance, finance.money_exchange |
| transport (197) | `amenity=parking` 64, `amenity=taxi` 55 (CNG/taxi stands), `railway=station` 21 (Dhaka metro rail) | transport.metro_station, transport.parking |
| emergency (171) | `amenity=police` 171 | none: police whose type (thana or outpost) is not stated |
| health (107) | `healthcare=yes` 77, `healthcare=blood_donation` 12 | health.blood_bank |

## Doubts and caveats

- **Robots.txt.** Geofabrik's robots.txt has `Disallow: *.osm.pbf` for `User-agent: *`. One file was downloaded,
  identified as `Elaka360-data-pipeline (research; contact via repository)`, because the project owner named this
  file. Overpass (`/api/`) and the openstreetmap.fr mirror also disallow robots. Someone should decide whether this
  fits COLLECTION_FORMAT's "honour robots.txt" rule.
- **Names with a category suffix.** Many recent features in Rajshahi (1,496), Rangpur (2,056), Mymensingh (1,871) and
  Dhaka (2,997) have names ending in an English category, such as "X, Mosque" or "Y, Government office". This style
  comes from commercial map listings. The suffix was stripped and the row flagged "provenance worth checking"; the
  original name is in `extra_json.name`.
- **Category from name keywords.** The category is guessed from name keywords for schools (primary, secondary,
  madrasa), health facilities, government offices and police. Wrong OSM tags carry through. For example, "Sonapatil
  Ground (Girls College Math)" is tagged as a college.
- **Bangla names are scarce.** Only 19,112 of 95,738 rows have `name_bn`.
- **Contacts are sparse.** 2,050 rows have a phone and 1,638 a website.
- **Doctors' chambers.** `amenity=doctors` and `amenity=dentist` rows are mapped to `business.health_service`. Some
  are named after a doctor, and their phone numbers were kept as published.
- **Cox's Bazar camps.** Unnamed latrines in the Rohingya camps (Teknaf and Ukhiya) were dropped. Named camp
  facilities, such as `amenity=refugee_site`, are kept.
- **Old Overpass files.** `query_boundaries.overpassql` and `query_pois.overpassql` in osm_rajshahi_division are left
  over from the unfinished Overpass version and are no longer used. Deleting them was refused by the tool permission
  system, so they are still there.
