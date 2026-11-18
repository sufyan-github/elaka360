# UGC university register — Chattogram Division

- **Source:** all 181 universities on www.ugc.gov.bd/universities (61 public, 116 private, 3 international, 1 CBHE; page data and each `/university/<slug>`; robots.txt allows), collected with `ugc_universities_raj_2026/fetch.py --division chattogram`, accessed 2026-11-17.
- **Selection:** a university is kept if its UGC campus address names a Chattogram-Division district. When an address names several districts, the one named last decides; the districts of all other divisions are also checked. A trailing "Chattogram" after another Chattogram-Division district is read as the division. UGC's spellings "Chitagonj" (Port City International University) and "Cox’s Bazar" (curly apostrophe) are recognised; "Rangamatia" (a mouza in Bangladesh Maritime University's Chattogram address) is not read as Rangamati. When UGC gives no address, the university is kept (flagged) if its name names a district.
- **Licence:** none stated.

## Result: 28 universities (10 public, 17 private, 1 international)

| District | Universities |
|---|---|
| Chattogram (16) | 5 public: University of Chittagong (Hathazari), CUET (Raozan), Chittagong Veterinary and Animal Sciences University, Chittagong Medical University, Bangladesh Maritime University. 10 private: BGC Trust (Chandanaish), IIUC (Sitakunda), Premier, USTC, Southern, CIU, East Delta, UCTC, Port City International, Chattogram BGMEA UFT. Asian University for Women (international). |
| Cumilla (4) | Comilla University (public); BAIUST (Adarsha Sadar), Britannia, CCN UST (Sadar Dakshin) (private) |
| Chandpur | Chandpur Science and Technology University* |
| Lakshmipur | Lakshmipur Science & Technology University (UGC's address is only "Lakshmipur") |
| Noakhali | Noakhali Science & Technology University |
| Rangamati | Rangamati Science and Technology University (Rangamati Sadar) |
| Feni | Feni University (private) |
| Brahmanbaria | University of Brahmanbaria (private) |
| Cox's Bazar | Cox's Bazar International University (private) |
| Bandarban | Bandarban University (private) |
| Khagrachhari | none |

\* District taken from the name (UGC gives no address).

## Fields

- **Contacts:** phones on 19 rows (landlines and hotlines only; mobile numbers are dropped, including one printed after "Cell:" in Port City's entry), e-mails on 23, websites on 27. Officials' names are dropped.
- **Free-mail addresses kept as institutional-looking:** USTC (gmail/yahoo "ustc…"), CVASU (registrarcvasu@gmail.com), CCN UST (ccnust@gmail.com), Cox's Bazar International University (cbiu.bd@gmail.com).
- **Upazila:** set on 7 rows (Hathazari, Raozan, Chandanaish, Sitakunda, Cumilla Adarsha Sadar, Cumilla Sadar Dakshin, Rangamati Sadar). Chattogram-city metropolitan thanas are not set. No coordinates.
- **`extra_json`:** UGC category, year, campuses, postcode, fax, UGC id.

## Gaps and doubts

- **Bangladesh Maritime University:** UGC's address is "Hamidchar (Rangamatia and Bakolia Mouja), Bandar, Chittagong"; it is in Chattogram, not Rangamati.
- **Not included:** universities UGC lists without any address whose names name no district (the same national set as in the Dhaka report). The University of Comilla's only UGC address is in Uttara, Dhaka; it stays in the Dhaka extract.
- **UGC marker:** Southern University Bangladesh '(1)' (meaning in the UGC page legend).
- **Present and permanent campus differ** (address = present campus): Premier, Southern, Bandarban University.
