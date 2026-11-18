# Overture Maps places — all 8 divisions (OVERTURE_PLACES_<CODE>_2026)

One shared report for `overture_places_{raj,rang,dhk,ctg,khl,bar,syl,mym}_2026`. Each folder's `raw/stats.json` holds that division's full counts. `raw/category_map.csv` lists every Overture category seen and the key it was given.

## Source

- **Release:** Overture `2026-10-21.0`, schema 2.0.0. It was the latest in https://stac.overturemaps.org/catalog.json on 2026-11-18.
- **Data:** `s3://overturemaps-us-west-2/release/2026-10-21.0/theme=places/type=place/`, read anonymously with DuckDB (httpfs + spatial).
  - The STAC item bounding boxes show that only file `part-00014-…` covers Bangladesh.
  - Rows whose bbox falls in lon 87.9–92.8 / lat 20.5–26.75 were kept: 588,295 rows, a 61 MB parquet, downloaded in 73 s.
  - The extract is cached outside the repo and is not committed. `python3 fetch.py --all` rebuilds it; `--offline [--extract PATH]` builds from the cache.
- **Schema change:** `categories` (primary + alternate) was removed in the September 2026 release. This release has `taxonomy` (primary, hierarchy, alternates) and `basic_category` instead. Both are used here and kept in `extra_json`.
- **Licence:** set per upstream dataset (https://docs.overturemaps.org/attribution/, Places section). Each row also carries `sources[].license`.
  - Meta, Microsoft, PinMeTo, Krick, RenderSEO, DAC, BrightQuery, Birdeye, Uberall, OpenTravel Alliance: CDLA-Permissive-2.0 (https://cdla.dev/permissive-2-0/).
  - Foursquare: Apache-2.0 plus a NOTICE that must be passed on. A copy is in `raw/FOURSQUARE_NOTICE.txt`.
  - AllThePlaces: CC0-1.0.
  - The places theme contains no OSM data, so ODbL share-alike does not apply. Overture notes that joining CDLA data to OSM may make the result an ODbL derivative database.
  - `SOURCE.json.license` is the AND of the licences present. Barishal and Mymensingh have no AllThePlaces rows.
- **Attribution (wording from the attribution page):**
  - "Overture Maps Foundation, overturemaps.org."
  - "Data from Meta, Microsoft, PinMeTo, Krick, RenderSEO, DAC, BrightQuery, Birdeye, Uberall, OpenTravel Alliance. Available under CDLA Permissive 2.0."
  - "Data from Foursquare. Copyright 2024 Foursquare Labs, Inc. All rights reserved. Available under Apache 2.0. Foursquare data was transformed to the Overture schema. Changed: 2026-03-18. NOTICE.txt."
  - "Data from AllThePlaces. Available under CC0 1.0."
- **Who supplied the rows:** meta 273,535; Microsoft 1,367; Uberall 917; Foursquare 273; AllThePlaces 75; PinMeTo 5; DAC 2.
- **source_url:** Overture documents no public per-record page; the Explorer link is only a map view. Every row therefore points to the release's STAC collection, `https://stac.overturemaps.org/2026-10-21.0/places/place/collection.json`.
  - `source_id` is `overture:<GERS id>`.
  - The upstream record ids (for Meta rows, the Facebook page id) are in `extra_json.sources`.

## Method

1. **Location.** Each point is matched to the HDX division, district, upazila and city-corporation polygons of all 8 HDX folders (`../hdx_cod_ab_bgd/`, `../hdx_cod_ab_bgd_<division>/`).
   - English names come from the seed, via each folder's `crosswalk.csv`.
   - No point fell inside two divisions. Six points fell inside two unit polygons; the lower code was used.
   - A point inside a city-corporation polygon gets `district_en` only. `upazila_en` stays empty, and the city corporation is named in `extra_json.city_corporation` and in `notes`.
2. **Confidence.** Every place is kept at every confidence; the value is in `extra_json.confidence`. Every row has one.
3. **Closed places.** Rows with `operating_status = permanently_closed` are skipped: 2, both in Dhaka. The one `temporarily_closed` row (Chattogram) is kept, with a note.
4. **Private individuals.**
   - The Bangladesh data has no person category: rows labelled `musician`, `life_coach` and similar are mostly businesses.
   - Instead, a row is dropped when its primary name is a personal-name prefix (Md/Mohammad/Muhammad/Mohd/Mst/Mosammat/মোঃ/মোহাম্মদ/মোছাঃ …) followed by 1–4 plain name words. The name must also contain no business or place word (shop, store, school, clinic, traders, bazar, দোকান, বিদ্যালয় …) and no digits or "&".
   - 318 rows were dropped. A check of 60 national samples found almost all were personal pages; a few were a residence or a "supporters' group".
   - Person pages without such a prefix cannot be detected and are kept.
5. **Contacts.** They are kept as Overture publishes them, as business-page contacts, not verified.
   - The first phone, website and email go in their columns; the rest go in `extra_json`.
   - Socials are kept only when they are URLs.
   - Phones are reduced to digits and "+".
6. **Names.**
   - A Bangla `names.primary` goes to `name_bn`. Otherwise `name_bn` comes from `names.common.bn` or a `bn` rule.
   - A Latin primary name goes to `name_en`.
   - All other names go to `extra_json.other_names`.
7. **Category.** `taxonomy.primary` is looked up first, then its hierarchy from most to least specific, against a fixed table.
   - A few refinements come from the place's own name: medical college, polytechnic, university, madrasa, high/primary school, upazila health complex, community clinic, eidgah, mazar, tea garden, cold storage.
   - `extra_json.category_fit` records how the key was chosen:

| category_fit | rows | meaning |
|---|---|---|
| exact | 195,213 | a matching key |
| approx | 42,496 | the closest key |
| top | 17,285 | only the Overture top level was available |
| none | 21,180 | no Overture category; filed under `other` |

## Per division

"Outside" counts points inside the division polygon's bounding box that fell outside the polygon itself: India, Myanmar, sea, or a neighbouring division. The figure in brackets is the part that fell in a neighbouring division.

| folder / key | rows | phone | website | email | name_bn | upazila | in city corp. | outside (other div.) | closed skipped | persons skipped |
|---|---|---|---|---|---|---|---|---|---|---|
| overture_places_raj_2026 / OVERTURE_PLACES_RAJ_2026 | 16,799 | 12,220 | 6,194 | 8,705 | 5,237 | 13,130 | 3,668 | 15,339 (2,206) | 0 | 17 |
| overture_places_rang_2026 / OVERTURE_PLACES_RANG_2026 | 9,765 | 6,859 | 3,395 | 4,807 | 3,132 | 7,388 | 2,377 | 14,957 (1,003) | 0 | 19 |
| overture_places_dhk_2026 / OVERTURE_PLACES_DHK_2026 | 159,944 | 131,152 | 79,200 | 102,386 | 24,259 | 30,919 | 129,024 | 23,472 (23,278) | 2 | 159 |
| overture_places_ctg_2026 / OVERTURE_PLACES_CTG_2026 | 45,747 | 32,422 | 14,787 | 21,898 | 14,011 | 25,970 | 19,777 | 15,622 (7,388) | 0 | 61 |
| overture_places_khl_2026 / OVERTURE_PLACES_KHL_2026 | 15,917 | 11,543 | 5,696 | 8,054 | 4,335 | 11,867 | 4,048 | 16,996 (6,191) | 0 | 21 |
| overture_places_bar_2026 / OVERTURE_PLACES_BAR_2026 | 7,154 | 4,642 | 2,219 | 3,208 | 2,553 | 4,824 | 2,329 | 1,454 (1,451) | 0 | 14 |
| overture_places_syl_2026 / OVERTURE_PLACES_SYL_2026 | 13,628 | 9,838 | 4,421 | 6,487 | 3,861 | 8,160 | 5,467 | 4,655 (1,719) | 0 | 15 |
| overture_places_mym_2026 / OVERTURE_PLACES_MYM_2026 | 7,220 | 5,031 | 2,336 | 3,356 | 2,531 | 4,826 | 2,392 | 5,422 (5,268) | 0 | 12 |
| **total** | **276,174** | 213,707 | 118,248 | 158,901 | 59,919 | 107,084 | 169,082 | | 2 | 318 |

Of the 588,295 extract rows, 276,494 fall inside one of the 8 divisions and 311,801 fall outside Bangladesh.

### By top-level category

| div | business | education | other | health | tourism | government | religious | agriculture | finance | transport | emergency |
|---|---|---|---|---|---|---|---|---|---|---|---|
| raj | 7,616 | 3,199 | 2,156 | 1,149 | 903 | 477 | 389 | 401 | 279 | 185 | 45 |
| rang | 4,187 | 1,862 | 1,242 | 659 | 665 | 357 | 254 | 188 | 174 | 132 | 45 |
| dhk | 103,636 | 14,746 | 18,720 | 7,808 | 5,199 | 2,308 | 2,161 | 1,398 | 2,527 | 1,110 | 331 |
| ctg | 22,481 | 6,977 | 5,852 | 2,766 | 2,620 | 1,210 | 1,640 | 597 | 966 | 464 | 174 |
| khl | 7,817 | 2,631 | 1,889 | 947 | 922 | 516 | 395 | 227 | 294 | 187 | 92 |
| bar | 2,962 | 1,311 | 966 | 469 | 594 | 290 | 213 | 92 | 150 | 74 | 33 |
| syl | 6,987 | 2,080 | 1,563 | 903 | 755 | 394 | 356 | 113 | 289 | 122 | 66 |
| mym | 3,154 | 1,448 | 961 | 470 | 391 | 220 | 180 | 171 | 118 | 81 | 26 |
| total | 158,840 | 34,254 | 33,349 | 15,171 | 12,049 | 5,772 | 5,588 | 3,187 | 4,797 | 2,355 | 812 |

### Confidence bands

| div | <0.2 | 0.2–0.3 | 0.3–0.4 | 0.4–0.5 | 0.5–0.6 | 0.6–0.7 | 0.7–0.8 | 0.8–0.9 | ≥0.9 |
|---|---|---|---|---|---|---|---|---|---|
| raj | 1,167 | 1,341 | 1,349 | 1,359 | 3,027 | 2,256 | 3,185 | 2,205 | 910 |
| rang | 602 | 668 | 745 | 766 | 1,792 | 1,339 | 2,010 | 1,388 | 455 |
| dhk | 19,935 | 18,009 | 14,628 | 14,029 | 28,192 | 19,591 | 21,574 | 15,973 | 8,013 |
| ctg | 2,677 | 2,906 | 3,371 | 3,558 | 8,296 | 6,424 | 9,293 | 6,421 | 2,801 |
| khl | 1,218 | 1,273 | 1,289 | 1,331 | 2,777 | 1,984 | 3,082 | 2,067 | 896 |
| bar | 398 | 440 | 507 | 560 | 1,266 | 961 | 1,571 | 1,059 | 392 |
| syl | 670 | 790 | 916 | 1,132 | 2,543 | 1,946 | 2,752 | 1,907 | 972 |
| mym | 433 | 493 | 590 | 649 | 1,364 | 991 | 1,442 | 910 | 348 |
| total | 27,100 | 25,920 | 23,395 | 23,384 | 49,257 | 35,492 | 44,909 | 31,930 | 14,787 |

## Proposed new subcategories (national counts)

| Overture category | rows | key used now | proposal |
|---|---|---|---|
| (no category) | 21,180 | other | filter at merge |
| hotel / lodging / hostel / resort | 3,083 / 1,950 / 590 / 559 | business | `business.hotel` (lodging) |
| shopping (top level only) | 6,877 | business.shopping | — |
| social_or_community_service / youth_organization | 5,027 / 344 | other | `other.social_service` |
| education (top level only) | 4,750 | education | — |
| community_and_government (top level only) | 1,927 | other | — |
| spa / gym | 1,822 / 846 | business.service | `business.beauty_wellness`, `business.gym` |
| health_care (top level only) | 1,771 | health | — |
| religious_organization | 1,464 | religious | `religious.organization` |
| manufacturer / industrial_equipment_manufacturer / clothing_company / industrial_company / textile_manufacturer / chemical_plant | 1,314 / 754 / 747 / 551 / 507 / 314 | business | `business.factory` |
| warehouse_club_store | 1,238 | business.shop | `business.wholesale` |
| building_or_construction_service / engineering_service | 1,199 / 1,035 | business.service | `business.construction` |
| arts_and_entertainment / music_venue / stadium_arena | 851 / 495 / 343 | business / other | entertainment group |
| travel_company / freight_and_cargo_service | 791 / 781 | business | `business.travel_agency`, `business.logistics` |
| travel_and_transportation (top level only) | 764 | transport | — |
| bridge | 595 | other | `transport.bridge` |
| library | 557 | education | `education.library` |
| campus_building / educational_research_institute | 514 / 504 | education | `education.research_institute` |
| sport_league | 514 | other | `sports.club` |
| political_organization | 433 | other | `other.political_office` |
| geographic_entities (top level only) | 432 | tourism.natural | — |
| telecommunications_company | 350 | business | `business.telecom` |
| military_site | 328 | government | `government.military` |

The full lists are in each folder's `raw/stats.json` (`proposed_subcategories`) and `raw/category_map.csv`.

## Files

- **Places files:**
  - raj: `places.csv` 16.1 MB
  - rang: `places.csv` 9.4 MB
  - dhk: `places.csv` to `places_8.csv` at 19.5 MB each, `places_9.csv` 9.9 MB
  - ctg: 19.5 / 19.5 / 6.7 MB
  - khl: 15.3 MB
  - bar: 6.9 MB
  - syl: 13.3 MB
  - mym: 7.1 MB
- **raw/:** `stats.json`, `category_map.csv` (114 KB or less) and `FOURSQUARE_NOTICE.txt`.
- **Not committed:** the parquet extract. `fetch.py` rebuilds it.

## Doubts and gaps

- **Quality:** about 99% of rows are Facebook business pages (Meta). Expect:
  - village, group and online-shop pages placed at district or upazila centres;
  - duplicates, because Overture's own deduplication is imperfect and the importer does not merge rows that come from the same source;
  - categories chosen by page owners; `historic_site` (7.8k nationally) is often a village or area page.

  Treat every row as `community` evidence and unverified. 76,415 rows have confidence below 0.4.
- **City corporations:** 169,082 points inside city-corporation polygons have an empty `upazila_en`. The importer uses `extra_json.city_corporation` only when `upazila_en` is set and the district has more than one city corporation.
- **Contacts:** these are the pages' own published contacts. Sole traders' pages may carry personal mobiles, and the name rule above is the only filter for that.
- **Foursquare rows (273):** redistributing them requires the NOTICE and a copy of Apache-2.0. They can be dropped at merge via `extra_json.sources[].dataset`.
- **Dependency:** `fetch.py` needs duckdb, which loads its httpfs and spatial extensions. This goes beyond the stdlib + requests rule, because Overture is published only as GeoParquet.
- **OSM:** no deduplication against OSM was done, as instructed.
