# Sylhet Divisional Commissioner portal (sylhetdiv.gov.bd)

- **Collector:** `rajshahi_divisional_portal/fetch.py --division sylhet`. Host verified by its title "হোম | সিলেট বিভাগ".
- **Pages** from the menu (`raw/pages.csv`, texts in `raw/`):
  - এক নজরে সিলেট বিভাগ (2022-09-11);
  - জেলার তালিকা (2022-09-05);
  - সিলেট বিভাগের উপজেলাসমূহ (2022-09-05);
  - ইউনিয়নের তালিকা (2024-07-11).
  - Upazila and union portal addresses come from the national registry, which this portal does not link (`raw/national_portal_list.csv` keeps the 41 registry upazilas).
- **areas.csv (383):**
  - **4 districts.** `code` is the list serial (`SYLDIV_LIST_SERIAL`). Website is the DC portal; the page links it as www.<district>.gov.bd.
  - **41 upazilas** from a table with one column per district ("সিলেট জেলা | সুনামগঞ্জ জেলা | হবিগঞ্জ জেলা | মৌলভীবাজার জেলা"). The row serial is shared across the columns, so it is not used as a code. All 41 websites are from the registry. South Sunamganj is printed শান্তিগঞ্জ.
  - **338 unions** from four tables, each headed "জেলা: X". Each row is "upazila | comma list | count". Websites are from the registry where the name matches (300).
- **facts.csv (60):**
  - এক নজরে: 41 upazilas, 44 thanas, 1 city corporation, 20 pourashavas (Sylhet 5, Sunamganj 4, Moulvibazar 5, Habiganj 6), 338 unions (Sylhet ১০৫), population 11,034,863 (no year);
  - stated upazilas per district (13/12/9/7) and in total (৪১);
  - stated unions per district (106/88/78/67) and in total (৩৩৯);
  - listed counts: 4 districts, 41 upazilas, 338 unions, and unions per upazila.

## Conflicts and caveats

- **Listed 338 vs stated 339 on the union page** (এক নজরে says 338).
  - Bare upazila names inside the union lists are not unions: "জগন্নাথপুর", "দিরাই" and "বানিয়াচং" are dropped (the printed counts leave them out). Tahirpur prints "তাহিরপুর ইউনিয়ন" and a bare "তাহিরপুর"; counted once.
  - Gowainghat prints পূর্ব আলীরগাঁও twice; counted once (12).
  - Zakiganj lists 10 against the printed ০৯, including সিলাম, which the DC portal places under Dakshinsurma (7 here, 8 on the DC list).
- **Against the DC portals:**
  - Sylhet 105: Golapganj 11, Sylhet Sadar 7, Dakshinsurma 7, Zakiganj 10, Gowainghat 12.
  - Habiganj 77: no duplicates of নূরপুর and শায়েস্তাগঞ্জ under Sadar; Ajmiriganj 5 with কাকাইলছেও.
  - Sunamganj 88: Jamalganj 6, Madhyanagar 4, Dharmapasha 6.
  - Moulvibazar 67: Barlekha has কাটাল তলী and দক্ষিণ দক্ষিণভাগ.
- **No division area figure:** এক নজরে prints the population without a year. Prefer BBS 2022.
- The summary table at the top ("০১ | সিলেট | ১০৬ টি" …) is read for stated counts only. Its rows show up in `raw/warnings.txt` as "union before any upazila heading".

## Licence

No licence stated; facts only. Attribution: Office of the Divisional Commissioner, Sylhet (sylhetdiv.gov.bd); upazila and union portal addresses from the Bangladesh National Portal (bangladesh.gov.bd/views/union-list).
