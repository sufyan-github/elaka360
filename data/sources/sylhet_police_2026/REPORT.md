# SYLHET_POLICE_2026 — Sylhet District Police

**Sources (trust level 4, accessed 2026-11-18):**
- police.sylhet.gov.bd: the SP officer card (/pages/officers) and "একনজরে" (district profile).
- The 13 upazila thana portals police.<upazila>.sylhet.gov.bd were tried.

Sylhet city is policed by SMP (SYLHET_METRO_POLICE_THANAS_2026).

**fetch.py:** new `main_sylhet()`: SP card, the "একনজরে" thana count, thana portals, and the Let's Encrypt intermediates.

## Collected (1 place, 1 fact)
- **1 × `government.sp_office`:** পুলিশ সুপারের কার্যালয়, সিলেট — 02996632425; 01320117700 (SP official mobile); spsylhet@police.gov.bd; fax 02996635002 in `extra_json`.
- **facts:** police_stations = 17 ("থানা : ১৭ টি", next to "উপজেলা : ১৩ টি"). The page does not say whether SMP's 6 metropolitan thanas are included.

## Gaps
- **No thana rows.** All 13 thana portals serve the `*.sylhet.gov.bd` certificate, which does not cover police.<upazila>.sylhet.gov.bd (TLS hostname mismatch), so they were skipped and recorded, not fetched without verification.
- The SP portal's thana menu ("সার্কেল ও থানার কর্মরত কর্মকর্তাগণ") and its contact pages are empty links.
- No address is published. No other official thana list with numbers was found; sylhetdistrict.police.gov.bd does not resolve.
- The same "একনজরে" still says "সিটি কর্পোরেশন ০১ টি (ওয়ার্ড ২৭ টি)", an outdated count (SCC: 42).
- Officers' names are not copied.

## Licence
None stated → `null`.
