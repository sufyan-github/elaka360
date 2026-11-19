# Barishal Divisional Commissioner portal (barishaldiv.gov.bd)

- **Collector:** `rajshahi_divisional_portal/fetch.py --division barishal`. Host verified by its title "হোম | বরিশাল
  বিভাগ"; barisaldiv.gov.bd serves the same portal.
- **Pages** from the menu (`raw/pages.csv`, texts in `raw/`):
  - এক নজরে বরিশাল বিভাগ (2025-04-27, a PDF link only: no facts);
  - আওতাধীন জেলা প্রশাসন (2023-12-10);
  - বরিশাল বিভাগের উপজেলাসমূহ (2025-04-24);
  - ইউনিয়নের তালিকা (2019-07-21).
  - The menu item "জেলার তালিকা" links an old national-portal page, so it is not used.
- **areas.csv (254):**
  - **6 districts** from "জেলা প্রশাসকের কার্যালয়, <জেলা>". The name is stored without the prefix, with the printed
    text in notes. `code` is the list serial (`BARDIV_LIST_SERIAL`). Website is the DC portal; the page links it
    (www.<district>.gov.bd, barishal.gov.bd).
  - **42 upazilas.** Each district has a heading line ("পটুয়াখালী জেলায় ৮টি উপজেলা রয়েছেঃ") and then one upazila per
    line. Names are stored without "উপজেলা", with the printed text in notes. No code. Websites come from the national
    registry (not linked from this portal; `raw/national_portal_list.csv` keeps the 42 registry upazilas).
  - **206 unions** from the 2019 union page, for 3 districts only: Barishal 87, Bhola 67, Pirojpur 52. Websites are
    from the national registry where the name matches (173).
- **facts.csv (41):** district count listed (6), upazila count listed (42), upazilas stated per district, unions per
  upazila, unions stated (Barishal ৮৭, Pirojpur ৫২, per-upazila "মোট ইউনিয়নঃ"), and union count listed (206).

## Conflicts and caveats

- **Union page (2019):** a mix of layouts.
  - Barishal: "উপজেলা : X", then one union per line.
  - Bhola: an upazila line, then a comma list.
  - Patuakhali: upazila names only.
  - Pirojpur: a table with numbered unions.
  - Jhalokathi and Barguna are missing.
- **Against the DC portals (2026):**
  - Barishal 87 against 88: Mehendiganj 13 against 16, and Muladi 9 against 7 (জয়নগর and শ্রীপুর listed under
    Muladi). Babuganj has আগরপুর where the DC has জাহাঙ্গিরনগর.
  - Bhola 67 against 68 (Borhanuddin 8 against 9).
  - Pirojpur 52 against 54 (Zianagar 3 against 5).
- **Spellings kept as printed:** ইন্দুরকানী for Zianagar (the portal and registry use জিয়ানগর; Zianagar's own menu
  says "এক নজরে ইন্দুরকানী"), নেছারাবাদ (স্বরূপকাঠি), তজমুদ্দিন, ভাণ্ডারিয়া, মঠবাড়িয়া, বানারিপাড়া, মুলাদি, বেতাগি,
  কাঁঠালিয়া.
- **No division-level figures:** এক নজরে is a PDF.

## Licence

No licence stated; facts only. Attribution: Office of the Divisional Commissioner, Barishal (barishaldiv.gov.bd); upazila and union portal addresses from the Bangladesh National Portal (bangladesh.gov.bd/views/union-list).
