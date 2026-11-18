# KHULNA_METRO_POLICE_THANAS_2026 — Khulna Metropolitan Police

**Source** (trust level 4, accessed 2026-11-18; `"city": 50004`):
- KMP portal police.khulnadiv.gov.bd:
  - "যোগাযোগ": a 3-page PDF of KMP mobile numbers by post, typed in the legacy SutonnyMJ font; sha256 in `raw/kmp_thana_numbers.txt`;
  - "ডাক যোগাযোগ": HQ address, phone, fax, control room, e-mail;
  - the Police Commissioner's officer card.
- Khulna DC portal "ভৌগলিক পরিচিতি": the list of 8 metropolitan thanas.
- kmp.police.gov.bd answered HTTP 500.

**fetch.py (`rmp_thanas_2026/fetch.py`):** new `--city khulna` (`main_kmp`, `kmp_pdf_numbers`). No arguments still runs Rajshahi (outputs checked identical).
- The PDF is read with `pdftotext -layout`.
- The thana labels are matched by their legacy-font spelling and transcribed to Unicode in the `KMP_THANAS` table.

## Collected: 10 rows (all Khulna District)
- **8 × `emergency.police_station`:** খুলনা, সোনাডাঙ্গা মডেল, লবণচরা, হরিণটানা, খালিশপুর, দৌলতপুর, আড়ংঘাটা, খানজাহান আলী থানা (KMP's names).
  - Phone = the OC's and duty officer's police official mobiles (01320-058xxx), on all 8.
  - `extra_json`: DC portal spelling, legacy label, `area_en` (empty).
  - `upazila_en` holds the metropolitan thana.
- **1 × `government.sp_office`:** খুলনা মেট্রোপলিটন পুলিশ হেডকোয়ার্টার্স, "১৮৯, খানজাহান আলী রোড, খুলনা" (landmark গ্লাক্সো মোড়).
  - Phones: 0244112564 (printed "০২৪ ৪১১২৫৬৪-৬৫", first number kept), the Commissioner's office 02477721162, the Commissioner post mobile 01320058000.
  - E-mail: pckmp@police.gov.bd. Fax 02477721358 in `extra_json`.
- **1 × `emergency`:** কেএমপি কন্ট্রোল রুম — 01320060998 (control room), 01320060999 (KMP hotline).
- **facts:** 8 police stations; 0 placed in a city corporation.

## City corporation
**0 of 8 thanas placed** (`area_en` empty) by this source. KMP covers all 31 KCC wards plus 5 unions (এক নজরে), but no KMP, DC or KCC page gives a thana-to-ward or thana-to-city-corporation list, and KCC's site could not be read.

## Doubts
- **Transcription:** the thana names are a transcription of legacy-font labels. If the PDF changes or pdftotext is missing, fetch.py prints a warning and leaves the numbers empty.
- **Name variants:** KMP's "খুলনা থানা" is the DC portal's "কোতয়ালী থানা" (HDX/BBS: Khulna Sadar).
- **Not copied:** inspectors', ACs' and other officers' mobiles in the PDF; officers' names; the other KMP e-mails.

## Licence
None stated → `null`.
