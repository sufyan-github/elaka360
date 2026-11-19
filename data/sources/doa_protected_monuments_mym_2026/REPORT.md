# DoA protected monuments — Mymensingh Division

- **Source:** archaeology.gov.bd "ময়মনসিংহ বিভাগের সংরক্ষিত পুরাকীর্তি" (/pages/static-pages/6922dd39933eb65569e14024; total 18, "জুন ২০২৬ পর্যন্ত হালানাগাদকৃত"). It links one PDF each for Sherpur, Mymensingh and Netrokona; Jamalpur is listed as "সংরক্ষিত পুরাকীর্তি নেই" with no PDF. The PDFs and their text extractions are in `raw/`. Collected with `doa_protected_monuments_raj_2026/fetch.py --division mymensingh`, accessed 2026-11-18. Trust level 4.
- **Licence:** none stated.

## Result: 18 monuments, 4 facts

| District | Monuments (page count = rows parsed) | List published |
|---|---|---|
| Mymensingh | 12 | 25-06-2026 |
| Netrokona | 5 | 31-08-2024 |
| Sherpur | 1 | 31-08-2024 |
| Jamalpur | 0 ("সংরক্ষিত পুরাকীর্তি নেই"; fact value 0) | — |

- **Categories:**
  - tourism.historical 14;
  - tourism.archaeological 2: Buruj Dhibi and Baro Duari Dhibi (Roail Bari);
  - tourism.museum 1: Mymensingh Museum;
  - religious.mazar 1: Dengu Mia Neyamat Bibi's mazar.
- **Coordinates:** 15 rows, converted from the published DMS values. Three rows have none:
  - Mymensingh-01 (শশী লজ): the cell shows "-".
  - Mymensingh-04 (ভূঁইয়া বাড়ী জামে মসজিদ, Muktagacha): the printed point (24°15'33.7" N, 90°12'36.5" E) falls in Sakhipur, Tangail (hdx_cod_ab_bgd_dhaka), about 55 km south of Muktagacha. Not used; kept in `extra_json`.
  - Mymensingh-12 (রণ-ভাওয়াল কাছারি, added Feb 2026): printed "২৪°৪০'৪২২" উ. ৯০°৫১'৬৪০" পূ.", malformed seconds. Not used; kept in `extra_json`.
- **Upazila:** set on all 18 rows, from the location text.
- **Point-in-polygon QA:** ran against `hdx_cod_ab_bgd_mymensingh`. HDX spells the district "Netrakona"; the collector reads it as Netrokona. Every used point falls in its listed district and upazila. Mymensingh-02 and -03 fall in the Mymensingh City Corporation polygon; they are listed as Mymensingh Sadar.
- **`extra_json`:** gazette reference as published, construction-date phrase, coordinates as printed, serial, list date. Descriptions are not copied.

## Conversion fixes, checked against the rendered pages
- **Bijoy "k^" (শ্ব):** the converter gives "শব". Fixed: "(রাজেশ্বরী মন্দির)" (Mymensingh-06).
- **Netrokona-04:** the i-kar is printed before a space ("Qv`w enxb"). Fixed to "ছাদবিহীন ইমারত", as visible.
- **Mymensingh-01:** the gazette date and the description share text lines. The gazette reference is read from the page: "বাংলাদেশ গেজেট 08 ফেব্রুয়ারি, 1990 (1ম খণ্ড, পৃষ্ঠা-56)".
- **Mymensingh-12:** the row is typed in Unicode with a broken text layer. Gazette ("বাংলাদেশ গেজেট ১২ ফেব্রুয়ারি ২০২৬") and coordinates are read from the rendered page; the name and location match the page.

## Gaps and doubts

- **Mymensingh-12's name:** printed without its closing bracket ("রণ-ভাওয়াল কাছারি (মশাখালী ইউনিয়ন ভূমি অফিস সংলগ্ন"); kept as printed. Its gazette text keeps Bangla digits, unlike the other rows.
- **Netrokona-05:** the location is printed "বোয়াইল বাড়ি" (the other Roail Bari rows say "রোয়াইল বাড়ি"); kept as printed.
- **Spellings kept as printed:** "হররামেশ্বর মন্দির" (Mymensingh-06) and "ঘাগরা খান বাড়ি জামে মসজিদ" (Sherpur-01; its description spells ঘাঘড়া).
