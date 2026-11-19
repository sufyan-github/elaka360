# Disaster shelters (SHELTERS_<CODE>_2026)

`fetch.py` lives in `shelters_raj_2026/` and writes `shelters_<code>_2026/`. Key `SHELTERS_<CODE>_2026`, kind `shelters`, source type `government_portal`, trust 4, category `emergency.disaster_shelter`.

**Sources used.**
- DC and UNO portal menu items titled আশ্রয়কেন্দ্র / সাইক্লোন / শেল্টার / সেল্টার / কিল্লা, plus HTML disaster-plan pages ("দুর্যোগ ব্যবস্থাপনা পরিকল্পনা").
- "সরকারি আশ্রয় কেন্দ্র" items are excluded: these are social-welfare homes, not disaster shelters.
- Tables are read by their column headers. Kept: name, type (cyclone or flood, taken from the column header), union, ward, address, capacity, builder, year built, condition, and coordinates when published.
- Caretakers' names and mobiles are dropped.

**Checked, not usable.**
- **DDM (ddm.gov.bd), "বন্যা আশ্রয়কেন্দ্র".** These are project documents. The 11-page "at a glance" PDF has a shelter list, but its Bangla font has no Unicode mapping, so only digits extract. The progress PDF gives totals only: 448 flood shelters planned in 43 districts and 258 upazilas.
- **Sitakunda shelter list.** A Print-to-PDF whose Bangla conjuncts are lost when text is extracted; it also lists caretakers' names and mobiles. Counted in `facts.csv`, not parsed.
- **HDX.** No government or UN shelter list for Bangladesh. The REACH Teknaf/Ukhiya cyclone-shelter XLSX is published by an NGO initiative, and the rest is refugee-camp data. Skipped.
- **LGED / DPE.** I found no published per-shelter list (dpe.gov.bd does not resolve), and the UNOSAT shelter map service is gone (404).
- Union portals (about 4,500) were not crawled.

**Counts.**
- Khulna: 50 rows, all from the Shyamnagar portal (Satkhira): 34 cyclone and 16 flood shelters, union, builder, year and condition as published, no coordinates. 56 rows parsed, 6 duplicates removed.
- Chattogram: 0 rows; Sitakunda's list is file-only (noted in `facts.csv`).
- Rajshahi, Rangpur, Dhaka, Barishal, Sylhet, Mymensingh: 0 rows. No portal publishes a shelter table.

**Doubt.** The Shyamnagar table dates from 2012, and its condition values ("মেরামত প্রয়োজন") are that old.
