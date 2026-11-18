# UGC university register — Dhaka Division

- **Source:** all 181 universities on www.ugc.gov.bd/universities (page data and each `/university/<slug>`; robots.txt allows), collected with `ugc_universities_raj_2026/fetch.py --division dhaka`, accessed 2026-11-17.
- **Selection:** a university is kept if its UGC campus address names a Dhaka-Division district. When an address names several districts, the one named last decides; the districts of all other divisions are also checked ("Dhaka Road, Bara Harishpur, Natore" stays in Natore). A trailing "Dhaka" after another Dhaka-Division district is read as the division: N.P.I University, "Basta, Singair, Manikganj, Dhaka", goes to Manikganj. When UGC gives no address, the university is kept (flagged) if its name names a district.
- **Licence:** none stated.

## Result: 84 universities (20 public, 63 private, 1 international)

| District | Universities |
|---|---|
| Dhaka (66) | 10 public: University of Dhaka, BUET, Jagannath, Jahangirnagar (Savar), Sher-e-Bangla Agricultural, Bangladesh University of Textiles, Bangladesh University of Professionals, Bangladesh Medical University, Islamic Arabic University, Dhaka Central University*. 56 private. |
| Gazipur (7) | National University, Bangladesh Open University, DUET, Gazipur Agricultural University, University of Frontier Technology (Kaliakair), IUT (international), German University Bangladesh (private) |
| Kishoreganj (3) | Kishoreganj University*; Dr. Momtaz Begum University (Bhairab) and Ishakha International University (private) |
| Narayanganj (2) | Narayanganj Science and Technology University*; State University of Bangladesh (Rupganj) |
| Faridpur | Times University (private) |
| Gopalganj | Gopalganj Science & Technology University |
| Manikganj | N.P.I University of Bangladesh (Singair) |
| Munshiganj | Hamdard University Bangladesh (Gazaria) |
| Shariatpur | Shariatpur Agricultural University* |
| Tangail | Mawlana Bhashani Science & Technology University |
| Narsingdi, Rajbari, Madaripur | none |

\* District taken from the name (UGC gives no address).

## Fields

- **Contacts:** phones on 63 rows (landlines and hotlines only), e-mails on 67, websites on 79. Officials' names are dropped.
- **Free-mail addresses:** 7 universities have yahoo or gmail addresses that look institutional (Shanto-Mariam, People's University, Islamic Arabic, SAU, German University, Ishakha, Hamdard); they are kept.
- **Upazila:** set on 13 rows (Savar 7; Gazipur Sadar, Kaliakair, Bhairab, Singair, Gazaria, Rupganj). Dhaka-city metropolitan thanas are not set. No coordinates.
- **`extra_json`:** UGC category, year, campuses, postcode, fax, UGC id.

## Gaps and doubts

- **Not included:** UGC gives no address for these, and their names name no district: Microland University of Science and Technology ("academic programs have not yet started"), IBAIS University (UGC: no approved address), America Bangladesh University (UGC: closed in 2006, no approved campus) and UCSI University Malaysia (Bangladesh Campus).
- **The University of Comilla:** UGC's only address is in Uttara, Dhaka. UGC notes it was shut down in 2006 and not allowed to resume. It is kept, with UGC's marker '***'.
- **UGC markers** (meaning in the UGC page legend): BUFT '(2)', Central University of Science and Technology '**', European University '***', People's University '*', Victoria University '*'.
- **Excluded correctly:** Rajshahi Science & Technology University. Its address is "Dhaka Road, … Natore", and it is in UGC_UNIVERSITIES_RAJ_2026.
