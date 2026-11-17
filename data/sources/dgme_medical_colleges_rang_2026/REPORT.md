# DGME medical and dental colleges — Rangpur Division

- **Sources** (dgme.gov.bd `/pages/static-pages/`):
  - medical colleges with code, year and MBBS seats (updated 18 Dec 2025);
  - dental colleges and units (20 May 2024);
  - English names and websites of government colleges.
- **Method:** collected with `dgme_medical_colleges_raj_2026/fetch.py --division rangpur`, accessed 2026-11-17. Rows are kept by the district suffix in the Bangla name; dental units go in the parent college's `extra_json`.
- **Licence:** none stated.

## Result: 7 colleges (education.medical_college)

| District | College | Type | Code | Year | Seats |
|---|---|---|---|---|---|
| Rangpur | Rangpur Medical College | govt | 17 | 1970 | 225 MBBS |
| Rangpur | Prime Medical College | | 136 | 2008 | 135 MBBS |
| Rangpur | Rangpur Community Hospital Medical College | | 137 | 2008 | 135 MBBS |
| Rangpur | Army Medical College Rangpur | armed forces | | 2014 | 50 MBBS |
| Rangpur | Rangpur Dental College | private | | 2008 | 100 BDS |
| Dinajpur | Dinajpur Medical College | govt | 20 | 1992 | 200 MBBS |
| Nilphamari | Nilphamari Medical College | govt | 46 | 2018 | 75 MBBS |

- Rangpur Medical College also has a dental unit (2012, 52 BDS seats); its English name and website (rpmc.edu.bd) come from the government page.
- There are none in Panchagarh, Thakurgaon, Lalmonirhat, Kurigram or Gaibandha.

## Gaps

- No addresses, phones, upazilas or coordinates.
- Dinajpur Medical College has no English name or website. DGME's government page spells it "Dinajpur Medical Collge" (site marmcd.edu.bd), so the district match failed; this is not corrected.
- Rangpur Medical College is the college, not the hospital (RpMCH). Link the two records; don't merge them.
