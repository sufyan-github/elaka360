# RANG_RANGE_POLICE_PORTALS_2026 — district police portals, Rangpur Range (excl. Rangpur District)

**Source (trust level 4, accessed 2026-11-17):** police.<district>.gov.bd for Panchagarh, Dinajpur, Lalmonirhat, Nilphamari, Gaibandha, Thakurgaon, Kurigram, and each thana's own portal police.<upazila>.<district>.gov.bd (2026 national-portal framework). Rangpur District is in RANGPUR_POLICE_2026.

| District | Source | Rows |
|---|---|---|
| Kurigram | district contact table: SP, all 11 OCs (incl. ঢুষমারা, কচাকাটা), সদর ফাঁড়ি, নামাজের চর তদন্ত কেন্দ্র, control room | 15 |
| Dinajpur | SP card + 13 thana portals | 14 |
| Thakurgaon | SP card + 7 thana portals (5 upazilas + রুহিয়া, ভূল্লী from the district thana list) | 8 |
| Gaibandha | SP card + 7 thana portals | 8 |
| Nilphamari | SP card + 6 thana portals (matches the district thana list) | 7 |
| Panchagarh | SP card + 5 thana portals | 6 |
| Lalmonirhat | SP card + 5 thana portals | 6 |

Categories: 54 `emergency.police_station`, 7 `government.sp_office`, 2 `emergency.police_outpost`, 1 `emergency` (Kurigram control room).

facts (9 rows):

| District | Facts |
|---|---|
| Kurigram | 11 thanas (glance + table) |
| Dinajpur | 13 thanas |
| Lalmonirhat | 5 thanas, 2 circles, 1 outpost, 1 investigation centre |
| Nilphamari | 6 thanas listed |
| Thakurgaon | 7 thanas listed |

## Contact rule
- **SP offices:** from the Superintendent's officer card. Kept: office landline, the SP's police official mobile (01320-xxx300 series), the `*@police.gov.bd` e-mail, and fax (in `extra_json`).
- **Thanas:** from the OC card. Kept: thana office landline and the officer-in-charge's police official mobile (01320-xxxxxx, or the older 01713-37/38xxxx police CUG series). Only `*.gov.bd` e-mails are kept; most thana cards give gmail or yahoo addresses, which are not copied.
- **Not copied:** other officers' mobiles and all names.

## Coverage and doubts
- **Coverage:** phone on 56 of 64 rows, e-mail on 9; no addresses or coordinates.
- **No phone (8):** Atowari, Birganj, Dimla, Domar, Patgram, Palashbari, Haripur, Bochaganj. Their cards have no OC entry, only personal numbers, or a dummy "০০০০০০০".
- **Possibly outdated:** thana officer cards are self-maintained, and several portals show two OC cards. Dimla's officer page link is 404.
- **No upazila:** `upazila_en` is empty for the non-upazila thanas ঢুষমারা, কচাকাটা, রুহিয়া and ভূল্লী.
- **Spelling:** the Kurigram table spells "ভুরাঙ্গামারী".
- **Inference:** treating 01713-37/38xxxx as police official numbers is an inference; the Lalmonirhat SP contact page itself uses 01713373941.

## Licence
None stated → `null`.
