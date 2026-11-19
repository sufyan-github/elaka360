# Data reconciliation: seed vs Consolidated Master v3.0

The master dataset is the project's own reconciliation workspace for Rajshahi Division (8 districts). It is a source of evidence, not an authority: its production gate is BLOCKED and every record in it is non-production. Nothing from it is published automatically.

## What is in the repository

- `data/sources/master_v3/`: the CSV/JSON working files from `Elaka360_Consolidated_Master_v3.0` (district reconciliation registers, conflict registers, the regional crosswalk, validation outputs) and `Rajshahi_Union_Data_Reconciliation_v1.7`. The 238 MB zip and its nested archives are **not** in git (`.gitignore`: `*.zip`, `Elaka360/`). The zip's SHA-256 is `beac0391f221a239c191da7f52fcb78571f199db8506701500f8f91df3663c71`.
- `pipelines/reconcile.py`: compares the seed with the master by district, by upazila and by union name. Names are matched after NFC, Banglish-key and fuzzy normalisation, and spelling variants are paired.
- Outputs, regenerated with the seed: `data/seed/qa/seed_vs_master_districts.csv`, `…_upazilas.csv`, `…_union_names.csv` and `unresolved_conflicts.csv`, plus [UNRESOLVED_CONFLICTS.md](UNRESOLVED_CONFLICTS.md).

## Rules

- A count match is not enough. Where the master has names, they are compared too, and every unmatched name must be a tracked conflict.
- Every difference must appear in `refdata.KNOWN_MASTER_DIFFS` with the master's conflict id. `validate_seed.py` fails on an untracked difference **and** on a tracked difference that no longer exists, so the list cannot go stale.
- Neither side is silently preferred. The seed changes only when the master cites an official source for the change.

## Changes applied to the seed

| Change | Evidence |
|---|---|
| 5 unions moved from Natore Sadar to Naldanga upazila (Brahmapur, Madhnagar, Khajura, Piprul, Biprobelghoria) | Natore District Administration: Natore Sadar 7, Naldanga 5 (master sources SRC-NAT-GLANCE-2026, SRC-NAT-DIST-UP-2025) |
| 3 duplicate unions removed (Awajpur, Charfesson; Talimpur, Barlekha; Bhojoanpur, Tetulia) | Identical rows in nuhil; the third had a Gazipur website |
| 5 junk names cleaned (`1nomohadevpur`, `Mariaup`, `Maijchar9`, `১গোপালনগর`, `আমদিয়া ২`) | Artefacts of website slugs; only the stray number or "up" suffix removed |
| All Bangla text NFC-normalised | The seed mixed precomposed and decomposed ড়/য় |
| 3 source links moved from a third-party Wikipedia mirror to wikipedia.org | `data/seed/qa/reconciliation_changes.csv` |

## Results (Rajshahi Division)

| District | Seed | Master selected 2026 | BBS 2011 | Status |
|---|---|---|---|---|
| Rajshahi | 71 | 71 | 71 | Counts match; Bagha 6 vs 7 open (Chakrajapur), RAJ-001/002 |
| Natore | 52 | 52 | 52 | Matches after the Naldanga fix |
| Naogaon | 99 | 99 | 99 | Matches; 2 spelling variants, 1 tracked name difference |
| Joypurhat | 32 | 32 | 32 | Matches |
| Chapainawabganj | 45 | 45 | 45 | Counts match; 5 names differ each way, and the master register repeats names across upazilas (CNB-003) |
| Bogura | 108 | 108 | 108 | Gabtali 11 vs 12 and Sonatala 7 vs 6 (BOG-005); Mokamtala upazila not adopted (BOG-002) |
| Pabna | 73 | 73 | 73 | Matches the crosswalk; master registers hold 74 rows (PAB-001) |
| Sirajganj | 82 | 83 | 82 | Ullapara 13 vs 14; the 83rd union is not identified (SIR-001) |

## Problems in the master itself (to raise with the data lead)

- `05_VALIDATION/validate_rajshahi_v3_0.py` uses `parents[2]` and crashes; `parents[1]` fixes it.
- The crosswalk totals 563 (Pabna 73), but the registers hold 564 rows (Pabna 74).
- Natore's secondary-atlas counts sum to 56 while its conflict register says 52.
- The Chapainawabganj register repeats 4 names across upazilas with copied geocode suffixes.
- 58 registry entries carry no licence field; 9 have bare-domain URLs and 4 are Google search links. v1.7 cites AI-chat tokens as evidence.
- README titled v2.5; the pipeline note says v1.9; each zip embeds all earlier zips (size doubles per release).
