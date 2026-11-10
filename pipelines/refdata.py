# Reference data assembled for the Elaka360 seed dataset.
# Every record carries a source and a verified flag. verified=True means the
# values were checked against the cited source during this build (Nov 2026).

SRC = {
    "NUHIL": ("nuhil/bangladesh-geocode (GitHub, MIT)", "https://github.com/nuhil/bangladesh-geocode"),
    "CITYPOP_ADJ": ("BBS Census 2022 (adjusted) via citypopulation.de", "https://citypopulation.de/en/bangladesh/"),
    "CITYPOP_RAJ": ("BBS Census 2022 (enumerated) via citypopulation.de, Rajshahi district page", "https://citypopulation.de/en/bangladesh/admin/81__rajshahi/"),
    "WIKI_RAJ": ("Wikipedia: Rajshahi District", "https://en.wikipedia.org/wiki/Rajshahi_District"),
    "WIKI_CC": ("Wikipedia: List of city corporations in Bangladesh (Mar 2026 snapshot)", "https://en.wikipedia.org/wiki/List_of_city_corporations_in_Bangladesh"),
    "WIKI_ADMIN": ("Wikipedia: Administrative geography of Bangladesh (Mar 2026 snapshot)", "https://en.wikipedia.org/wiki/Administrative_geography_of_Bangladesh"),
    "FE_BOGURA": ("The Financial Express, 15 May 2026: Bogura becomes city corporation", "https://today.thefinancialexpress.com.bd/last-page/bogura-becomes-city-corporation-1778866247"),
    "WIKI_SHAY": ("Wikipedia: Shayestaganj Upazila", "https://en.wikipedia.org/wiki/Shayestaganj_Upazila"),
    "FE_102": ("The Financial Express, 6 Jun 2024: Fire service launches new hotline 102", "https://thefinancialexpress.com.bd/national/fire-service-launches-new-hotline-number-102"),
    "WIKI_TEL": ("Wikipedia: Telephone numbers in Bangladesh", "https://en.wikipedia.org/wiki/Telephone_numbers_in_Bangladesh"),
    "WIKI_RU": ("Wikipedia: University of Rajshahi", "https://en.wikipedia.org/wiki/University_of_Rajshahi"),
    "WIKI_RUET": ("Wikipedia: RUET (Mar 2026 snapshot)", "https://en.wikipedia.org/wiki/Rajshahi_University_of_Engineering_%26_Technology"),
    "WIKI_RMC": ("Wikipedia: Rajshahi Medical College", "https://en.wikipedia.org/wiki/Rajshahi_Medical_College"),
    "WIKI_PUTHIA": ("Wikipedia: Puthia Rajbari", "https://en.wikipedia.org/wiki/Puthia_Rajbari"),
    "BANGLAPEDIA_PUTHIA": ("Banglapedia: Puthia", "https://en.banglapedia.org/index.php/Puthia"),
    "WIKI_VRM": ("Wikipedia: Varendra Research Museum", "https://en.wikipedia.org/wiki/Varendra_Research_Museum"),
    "RU_VRM": ("University of Rajshahi: Varendra Research Museum", "https://www.ru.ac.bd/facilities/varendra-research-museum/"),
    "MOCKUP": ("Elaka360 UI mockups (design placeholder, not a fact source)", ""),
    "UNVERIFIED": ("General knowledge — not checked against a primary source in this build", ""),
    "NATORE_DC_2026": ("Natore District Administration: এক নজরে নাটোর (52 unions; Naldanga 5)", "https://natore.gov.bd/pages/static-pages/697fbb1d35ce18e1c06cc346"),
    "MASTER_V3": ("Elaka360 Consolidated Master v3.0 (project reconciliation package, non-production)", ""),
}

# BBS geocodes for divisions (keyed by nuhil division id)
DIVISION_FIX = {
    "1": dict(name_en="Chattogram", bbs_code="20", hq="Chattogram"),
    "2": dict(name_en="Rajshahi", bbs_code="50", hq="Rajshahi"),
    "3": dict(name_en="Khulna", bbs_code="40", hq="Khulna"),
    "4": dict(name_en="Barishal", bbs_code="10", hq="Barishal"),
    "5": dict(name_en="Sylhet", bbs_code="60", hq="Sylhet"),
    "6": dict(name_en="Dhaka", bbs_code="30", hq="Dhaka"),
    "7": dict(name_en="Rangpur", bbs_code="55", hq="Rangpur"),
    "8": dict(name_en="Mymensingh", bbs_code="45", hq="Mymensingh"),
}
DIVISION_POP = {  # adjusted 2022
    "Barishal": 9325820, "Chattogram": 34178612, "Dhaka": 45644586, "Khulna": 17813218,
    "Mymensingh": 12637472, "Rajshahi": 20794019, "Rangpur": 18020071, "Sylhet": 11415113,
}
DISTRICT_NAME_FIX = {"Coxsbazar": "Cox's Bazar", "Barisal": "Barishal", "Jhalakathi": "Jhalokathi"}
# citypopulation adjusted 2022 district population, keyed by nuhil English name
DISTRICT_POP = {
    "Dhaka": 15210851, "Faridpur": 2232772, "Gazipur": 5433538, "Gopalganj": 1336907, "Kishoreganj": 3373219,
    "Madaripur": 1334811, "Manikganj": 1608372, "Munshiganj": 1677941, "Narayanganj": 4035461, "Narsingdi": 2667968,
    "Rajbari": 1228267, "Shariatpur": 1336396, "Tangail": 4168083,
    "Bagerhat": 1649874, "Chuadanga": 1262205, "Jashore": 3146317, "Jhenaidah": 2051607, "Khulna": 2673002,
    "Kushtia": 2198731, "Magura": 1056683, "Meherpur": 721447, "Narail": 806662, "Satkhira": 2246691,
    "Jamalpur": 2583984, "Mymensingh": 6097814, "Netrokona": 2403205, "Sherpur": 1552469,
    "Bogura": 3815192, "Chapainawabganj": 1875290, "Joypurhat": 977150, "Naogaon": 2844921, "Natore": 1900213,
    "Pabna": 2972654, "Rajshahi": 2978156, "Sirajganj": 3430443,
    "Barguna": 1035596, "Barisal": 2634203, "Bhola": 1980452, "Jhalakathi": 677559, "Patuakhali": 1770096, "Pirojpur": 1227915,
    "Dinajpur": 3392251, "Gaibandha": 2621756, "Kurigram": 2383268, "Lalmonirhat": 1461589, "Nilphamari": 2141180,
    "Panchagarh": 1207252, "Rangpur": 3243247, "Thakurgaon": 1569529,
    "Bandarban": 495252, "Brahmanbaria": 3403786, "Chandpur": 2713247, "Chattogram": 9439076, "Cumilla": 6394875,
    "Coxsbazar": 2906281, "Feni": 1697379, "Khagrachhari": 735116, "Lakshmipur": 1994930, "Noakhali": 3732042, "Rangamati": 666627,
    "Habiganj": 2440151, "Moulvibazar": 2196601, "Sunamganj": 2788358, "Sylhet": 3990003,
}
GEOJSON_NAME_FIX = {"Bogra": "Bogura", "Brahamanbaria": "Brahmanbaria", "Chittagong": "Chattogram", "Comilla": "Cumilla",
                    "Cox's Bazar": "Coxsbazar", "Jessore": "Jashore", "Jhalokati": "Jhalakathi", "Maulvibazar": "Moulvibazar",
                    "Nawabganj": "Chapainawabganj", "Netrakona": "Netrokona"}

# Rajshahi district upazila populations (enumerated, 2022) keyed by nuhil English name
RAJ_UPZ_POP = {"Bagha": 195888, "Bagmara": 373970, "Charghat": 224845, "Durgapur": 197713, "Godagari": 376386,
               "Mohonpur": 186904, "Paba": 368889, "Puthia": 224143, "Tanore": 212983}

CITY_CORPORATIONS = [
    # name_en, name_bn, district (nuhil EN), area_km2, pop_2022, wards, established, est_note, verified-flag source
    ("Dhaka North City Corporation", "ঢাকা উত্তর সিটি কর্পোরেশন", "Dhaka", 196.22, 5979537, None, 2011, "split from Dhaka City Corporation (2011)"),
    ("Dhaka South City Corporation", "ঢাকা দক্ষিণ সিটি কর্পোরেশন", "Dhaka", 109.25, 4299345, None, 2011, "split from Dhaka City Corporation (2011)"),
    ("Chattogram City Corporation", "চট্টগ্রাম সিটি কর্পোরেশন", "Chattogram", 168.07, 3227246, None, None, ""),
    ("Khulna City Corporation", "খুলনা সিটি কর্পোরেশন", "Khulna", 91.315, 718735, None, None, ""),
    ("Rajshahi City Corporation", "রাজশাহী সিটি কর্পোরেশন", "Rajshahi", 96.72, 552791, 30, 1987, "municipal corporation 13 Aug 1987 (Wikipedia); full city corporation later — confirm year with RCC; 30 wards per mockups (confirm)"),
    ("Sylhet City Corporation", "সিলেট সিটি কর্পোরেশন", "Sylhet", 79.50, 532426, None, None, ""),
    ("Barishal City Corporation", "বরিশাল সিটি কর্পোরেশন", "Barisal", 58.0, 419351, None, None, ""),
    ("Rangpur City Corporation", "রংপুর সিটি কর্পোরেশন", "Rangpur", 203.63, 708384, None, None, ""),
    ("Cumilla City Corporation", "কুমিল্লা সিটি কর্পোরেশন", "Cumilla", 53.04, 439414, None, None, ""),
    ("Narayanganj City Corporation", "নারায়ণগঞ্জ সিটি কর্পোরেশন", "Narayanganj", 72.43, 967724, None, None, ""),
    ("Gazipur City Corporation", "গাজীপুর সিটি কর্পোরেশন", "Gazipur", 329.53, 2674697, None, None, ""),
    ("Mymensingh City Corporation", "ময়মনসিংহ সিটি কর্পোরেশন", "Mymensingh", 91.06, 471858, None, None, ""),
    ("Bogura City Corporation", "বগুড়া সিটি কর্পোরেশন", "Bogura", 69.90, 540000, 21, 2026, "gazette issued May 2026 (Financial Express, 15 May 2026); 21 wards; population is an estimate"),
]

# Rajshahi district paurashavas — list NOT verified against LGD; production_eligible = False
RAJ_POURASHAVAS = [
    ("Arani", "আড়ানী", "Bagha"), ("Bagha", "বাঘা", "Bagha"),
    ("Bhabaniganj", "ভবানীগঞ্জ", "Bagmara"), ("Taherpur", "তাহেরপুর", "Bagmara"),
    ("Charghat", "চারঘাট", "Charghat"), ("Durgapur", "দুর্গাপুর", "Durgapur"),
    ("Godagari", "গোদাগাড়ী", "Godagari"), ("Kakanhat", "কাঁকনহাট", "Godagari"),
    ("Keshorhat", "কেশরহাট", "Mohonpur"),
    ("Katakhali", "কাটাখালী", "Paba"), ("Naohata", "নওহাটা", "Paba"),
    ("Puthia", "পুঠিয়া", "Puthia"),
    ("Tanore", "তানোর", "Tanore"), ("Mundumala", "মুণ্ডুমালা", "Tanore"),
]

# ---------------- Category taxonomy (from mockups) ----------------
# key, bn, en, icon (lucide name), color, subcategories [(key,bn,en)]
CATEGORIES = [
    ("education", "শিক্ষা প্রতিষ্ঠান", "Education", "graduation-cap", "#16865B", [
        ("primary_school", "প্রাথমিক বিদ্যালয়", "Primary school"),
        ("secondary_school", "মাধ্যমিক বিদ্যালয়", "Secondary school"),
        ("college", "কলেজ", "College"),
        ("university", "বিশ্ববিদ্যালয়", "University"),
        ("medical_college", "মেডিকেল কলেজ", "Medical college"),
        ("madrasa", "মাদ্রাসা", "Madrasa"),
        ("technical", "কারিগরি প্রতিষ্ঠান", "Technical institute"),
        ("polytechnic", "পলিটেকনিক", "Polytechnic"),
        ("training_center", "ট্রেনিং সেন্টার", "Training center"),
    ]),
    ("health", "স্বাস্থ্য সেবা", "Health", "hospital", "#E5383B", [
        ("hospital", "হাসপাতাল", "Hospital"),
        ("medical_college_hospital", "মেডিকেল কলেজ হাসপাতাল", "Medical college hospital"),
        ("upazila_health_complex", "উপজেলা স্বাস্থ্য কমপ্লেক্স", "Upazila health complex"),
        ("community_clinic", "কমিউনিটি ক্লিনিক", "Community clinic"),
        ("clinic", "ক্লিনিক", "Clinic"),
        ("diagnostic_center", "ডায়াগনস্টিক সেন্টার", "Diagnostic center"),
        ("pharmacy", "ফার্মেসি", "Pharmacy"),
        ("city_health_center", "সিটি স্বাস্থ্য কেন্দ্র", "City health center"),
    ]),
    ("government", "সরকারি অফিস", "Government office", "landmark", "#1E5BD8", [
        ("divisional_commissioner", "বিভাগীয় কমিশনারের কার্যালয়", "Divisional Commissioner's office"),
        ("dc_office", "জেলা প্রশাসকের কার্যালয়", "Deputy Commissioner's office"),
        ("uno_office", "উপজেলা নির্বাহী অফিস", "Upazila Nirbahi Office"),
        ("sp_office", "পুলিশ সুপারের কার্যালয়", "Superintendent of Police office"),
        ("civil_surgeon", "সিভিল সার্জন অফিস", "Civil Surgeon office"),
        ("passport_office", "পাসপোর্ট অফিস", "Passport office"),
        ("city_corporation_office", "সিটি কর্পোরেশন কার্যালয়", "City corporation office"),
        ("pourashava_office", "পৌরসভা কার্যালয়", "Pourashava office"),
        ("union_parishad", "ইউনিয়ন পরিষদ", "Union parishad"),
        ("land_office", "ভূমি অফিস", "Land office"),
        ("post_office", "ডাকঘর", "Post office"),
        ("court", "আদালত", "Court"),
    ]),
    ("religious", "ধর্মীয় প্রতিষ্ঠান", "Religious", "church", "#7B3FC6", [
        ("mosque", "মসজিদ", "Mosque"), ("temple", "মন্দির", "Temple"), ("church", "গির্জা", "Church"),
        ("buddhist_vihara", "বৌদ্ধ বিহার / প্যাগোডা", "Buddhist vihara / pagoda"), ("mazar", "মাজার", "Mazar / shrine"),
        ("eidgah", "ঈদগাহ", "Eidgah"),
    ]),
    ("emergency", "জরুরি সেবা", "Emergency", "shield-alert", "#F2994A", [
        ("police_station", "থানা", "Police station"), ("police_outpost", "পুলিশ ফাঁড়ি", "Police outpost"),
        ("fire_station", "ফায়ার স্টেশন", "Fire station"), ("ambulance", "অ্যাম্বুলেন্স", "Ambulance"),
        ("emergency_department", "জরুরি বিভাগ", "Hospital emergency"), ("disaster_shelter", "দুর্যোগ আশ্রয়কেন্দ্র", "Disaster shelter"),
        ("rescue", "উদ্ধার সেবা", "Rescue"), ("utility_emergency", "গ্যাস/বিদ্যুৎ জরুরি সহায়তা", "Gas/electricity emergency"),
        ("water_sanitation", "পানি ও স্যানিটেশন", "Water & sanitation"),
    ]),
    ("tourism", "পর্যটন স্থান", "Tourism", "palmtree", "#16865B", [
        ("hill", "পাহাড়", "Hill"), ("beach", "সমুদ্রসৈকত", "Beach"), ("natural", "প্রাকৃতিক স্থান", "Natural site"),
        ("historical", "ঐতিহাসিক স্থান", "Historical site"), ("archaeological", "প্রত্নতাত্ত্বিক স্থান", "Archaeological site"),
        ("waterfall", "ঝর্ণা", "Waterfall"), ("river_haor", "নদী ও হাওর", "River & haor"), ("park", "পার্ক", "Park"),
        ("religious_site", "ধর্মীয় স্থান", "Religious site"), ("museum", "জাদুঘর", "Museum"), ("tea_garden", "চা বাগান", "Tea garden"),
    ]),
    ("business", "বাজার ও ব্যবসা", "Business & market", "store", "#F2994A", [
        ("shop", "দোকান", "Shop"), ("market", "বাজার", "Market"), ("restaurant", "রেস্টুরেন্ট", "Restaurant"),
        ("cafe", "ক্যাফে", "Cafe"), ("shopping", "শপিং", "Shopping"), ("supermarket", "সুপার শপ", "Supermarket"),
        ("service", "সেবা", "Service"), ("health_service", "স্বাস্থ্যসেবা", "Health service"),
        ("education_service", "শিক্ষা সেবা", "Education service"), ("home_service", "গৃহসেবা", "Home service"),
        ("vehicle_service", "গাড়ি সেবা", "Vehicle service"), ("it_service", "আইটি সেবা", "IT service"),
        ("fashion", "ফ্যাশন", "Fashion"),
    ]),
    ("transport", "পরিবহন ও রুট", "Transport", "bus", "#5B4FD6", [
        ("bus_terminal", "বাস টার্মিনাল", "Bus terminal"), ("bus_stop", "বাস স্টপ", "Bus stop"),
        ("railway_station", "রেল স্টেশন", "Railway station"), ("launch_ghat", "লঞ্চ ঘাট", "Launch ghat"),
        ("airport", "বিমানবন্দর", "Airport"), ("fuel_station", "ফিলিং স্টেশন", "Fuel station"),
    ]),
    ("agriculture", "কৃষি ও প্রাকৃতিক সম্পদ", "Agriculture & natural resources", "leaf", "#2F9E44", [
        ("agri_office", "কৃষি অফিস", "Agriculture office"), ("farm", "খামার", "Farm"), ("nursery", "নার্সারি", "Nursery"),
        ("haat", "হাট", "Haat (weekly market)"), ("cold_storage", "হিমাগার", "Cold storage"),
    ]),
    ("finance", "ব্যাংক ও আর্থিক সেবা", "Bank & finance", "banknote", "#1E5BD8", [
        ("bank", "ব্যাংক", "Bank"), ("atm", "এটিএম", "ATM"), ("mobile_banking_agent", "মোবাইল ব্যাংকিং এজেন্ট", "Mobile banking agent"),
    ]),
    ("other", "অন্যান্য", "Other", "more-horizontal", "#6B7A75", [
        ("ngo", "এনজিও", "NGO"), ("community_center", "কমিউনিটি সেন্টার", "Community center"),
    ]),
]

HOTLINES = [
    # number, bn, en, category, verified, source, note
    ("999", "জাতীয় জরুরি সেবা", "National emergency service (police, fire, ambulance)", "emergency", True, "WIKI_TEL", ""),
    ("102", "ফায়ার সার্ভিস ও সিভিল ডিফেন্স", "Fire Service & Civil Defence", "fire", True, "FE_102", "Replaced 16163, which was to be discontinued after 31 Dec 2024. Mockups still show 16163."),
    ("333", "জাতীয় তথ্য ও সেবা বাতায়ন", "National helpline (information & services)", "government", True, "WIKI_TEL", ""),
    ("109", "নারী ও শিশু নির্যাতন প্রতিরোধ", "Violence against women & children helpline", "protection", True, "WIKI_TEL", ""),
    ("106", "দুর্নীতি দমন কমিশন", "Anti-Corruption Commission", "government", True, "WIKI_TEL", ""),
    ("105", "জাতীয় পরিচয়পত্র সেবা", "NID services", "government", True, "WIKI_TEL", ""),
    ("131", "বাংলাদেশ রেলওয়ে", "Bangladesh Railway", "transport", True, "WIKI_TEL", ""),
    ("16263", "স্বাস্থ্য বাতায়ন", "Shasthya Batayon (health helpline)", "health", False, "UNVERIFIED", "Shown in mockups; widely published, not checked here."),
    ("1098", "চাইল্ড হেল্পলাইন", "Child Helpline", "protection", False, "UNVERIFIED", ""),
    ("16430", "সরকারি আইনি সহায়তা", "National Legal Aid helpline", "legal", False, "UNVERIFIED", ""),
]

# ---------------- Rajshahi pilot places ----------------
PLACES = [
    dict(slug="university-of-rajshahi", name_bn="রাজশাহী বিশ্ববিদ্যালয়", name_en="University of Rajshahi", short_name="RU",
         category="education", subcategory="university", ownership="public", district="Rajshahi", upazila="Paba",
         address_en="Motihar, Rajshahi 6205", postcode="6205", lat=24.370, lon=88.637, website="https://www.ru.ac.bd",
         established="1953-07-06",
         attributes=dict(faculties=12, departments=59, institutes=6, residential_halls=18, students="25,000+", academic_staff="1,200+",
                         campus_acres=753, vice_chancellor="Faridul Islam (since 16 Mar 2026)"),
         verified=True, source="WIKI_RU",
         notes="Mockups show 56/58 departments, ~34,000–38,000 students and a different VC — all outdated. Inside Rajshahi City Corporation (Motihar thana)."),
    dict(slug="ruet", name_bn="রাজশাহী প্রকৌশল ও প্রযুক্তি বিশ্ববিদ্যালয়", name_en="Rajshahi University of Engineering & Technology", short_name="RUET",
         category="education", subcategory="university", ownership="public", district="Rajshahi", upazila="Paba",
         address_en="Rajshahi–Dhaka Highway, Kazla, Rajshahi 6204", postcode="6204", lat=24.3635, lon=88.6280, website="https://www.ruet.ac.bd",
         established="1964",
         attributes=dict(university_status_year=2003, departments=14, faculties=4, students=6484, academic_staff=400, vice_chancellor="S M Abdur Razzak"),
         verified=True, source="WIKI_RUET",
         notes="Founded as Rajshahi Engineering College (1964), university since Sept 2003. Phone numbers in mockups not verified."),
    dict(slug="rajshahi-medical-college-hospital", name_bn="রাজশাহী মেডিকেল কলেজ হাসপাতাল", name_en="Rajshahi Medical College Hospital", short_name="RMCH",
         category="health", subcategory="medical_college_hospital", ownership="public", district="Rajshahi", upazila="Paba",
         address_en="Laxmipur, Rajshahi", postcode="6000", lat=24.3723, lon=88.5857, website="https://rmch.gov.bd",
         established="1958",
         attributes=dict(college_established=1958, hospital_opened=1965, beds_history="530 at opening (1965); 862 after extension (Wikipedia)", emergency="24/7"),
         verified=True, source="WIKI_RMC",
         notes="Current bed count not confirmed — mockup's 1,200+ needs the hospital's own figure. College website rmc.gov.bd."),
    dict(slug="puthia-rajbari", name_bn="পুঠিয়া রাজবাড়ী", name_en="Puthia Rajbari", short_name=None,
         category="tourism", subcategory="historical", ownership="public", district="Rajshahi", upazila="Puthia",
         address_en="Puthia, Rajshahi", postcode="6260", lat=24.3633, lon=88.8355, website=None,
         established="1895",
         attributes=dict(built_by="Maharani Hemanta Kumari Devi", style="Indo-Saracenic Revival", distance_from_rajshahi_km=30,
                         complex="Puthia Temple Complex (Govinda, Shiva 1823, Jagaddhatri, Dol Mancha)"),
         verified=True, source="WIKI_PUTHIA",
         notes="Mockup says 22 km from Rajshahi; Wikipedia says ~30 km east of town. Current use differs by source (museum vs. Lashkarpur Degree College per Banglapedia)."),
    dict(slug="varendra-research-museum", name_bn="বরেন্দ্র গবেষণা জাদুঘর", name_en="Varendra Research Museum", short_name=None,
         category="tourism", subcategory="museum", ownership="public", district="Rajshahi", upazila="Paba",
         address_en="Hetem Khan, Rajshahi", postcode=None, lat=24.367106, lon=88.592382, website="https://www.ru.ac.bd/facilities/varendra-research-museum/",
         established="1910",
         attributes=dict(managed_by="University of Rajshahi (since 1964)", founded_by="Varendra Research Society"),
         verified=True, source="WIKI_VRM",
         notes="Street address not confirmed; opening hours/ticket price not found in sources."),
    dict(slug="rajshahi-college", name_bn="রাজশাহী কলেজ", name_en="Rajshahi College", short_name=None,
         category="education", subcategory="college", ownership="public", district="Rajshahi", upazila="Paba",
         address_en="Rajshahi", postcode=None, lat=None, lon=None, website=None, established="1873",
         attributes={}, verified=False, source="UNVERIFIED", notes="Founding year and location need confirmation."),
    dict(slug="bagha-mosque", name_bn="বাঘা মসজিদ", name_en="Bagha Mosque", short_name=None,
         category="tourism", subcategory="historical", ownership="public", district="Rajshahi", upazila="Bagha",
         address_en="Bagha, Rajshahi", postcode=None, lat=None, lon=None, website=None, established="1523",
         attributes={}, verified=False, source="UNVERIFIED", notes="Sultanate-era mosque; year and coordinates need confirmation."),
    dict(slug="shah-makhdum-mazar", name_bn="হযরত শাহ মখদুম (রহ.) মাজার", name_en="Shah Makhdum Shrine", short_name=None,
         category="religious", subcategory="mazar", ownership="trust", district="Rajshahi", upazila="Paba",
         address_en="Dargapara, Rajshahi", postcode=None, lat=None, lon=None, website=None, established=None,
         attributes={}, verified=False, source="UNVERIFIED", notes="Location needs confirmation."),
]

# Places that appear in the mockups but are placeholders — fixtures for UI dev only.
DEMO_FIXTURES = [
    dict(name_en="Durbin Cafe & Restaurant", name_bn="ডারবিন ক্যাফে অ্যান্ড রেস্টুরেন্ট", category="business", subcategory="restaurant", area="Motihar, Rajshahi"),
    dict(name_en="Motihar Government High School", name_bn="মতিহার সরকারি উচ্চ বিদ্যালয়", category="education", subcategory="secondary_school", area="Motihar, Rajshahi"),
    dict(name_en="Motihar Pharmacy", name_bn="মতিহার ফার্মেসি", category="health", subcategory="pharmacy", area="Motihar, Rajshahi"),
    dict(name_en="City Super Shop", name_bn="সিটি সুপার শপ", category="business", subcategory="supermarket", area="Laxmipur, Rajshahi"),
    dict(name_en="TechPoint IT Solution", name_bn="টেকপয়েন্ট আইটি সলিউশন", category="business", subcategory="it_service", area="Boalia, Rajshahi"),
    dict(name_en="Rajshahi Auto Service", name_bn="রাজশাহী অটো সার্ভিস", category="business", subcategory="vehicle_service", area="Supura, Rajshahi"),
    dict(name_en="Padma Restaurant", name_bn="পদ্মা রেস্টুরেন্ট", category="business", subcategory="restaurant", area="Motihar, Rajshahi"),
    dict(name_en="Kazi Bazar", name_bn="কাজী বাজার", category="business", subcategory="market", area="Charghat, Rajshahi"),
    dict(name_en="Balapara High School", name_bn="বালাপাড়া উচ্চ বিদ্যালয়", category="education", subcategory="secondary_school", area="Bagha, Rajshahi"),
    dict(name_en="Darul Ulum Madrasa", name_bn="দারুল উলুম মাদ্রাসা", category="education", subcategory="madrasa", area="Paba, Rajshahi"),
]

# Mockup figure vs verified figure
MOCKUP_VS_VERIFIED = [
    # topic, mockup values, verified/dataset value, source key, action
    ("Total upazilas", "492+, 495, 495+, 496+, 500+", "495", "WIKI_ADMIN", "Use 495 everywhere (dataset has 495)."),
    ("Total unions", "4,500+, 4,550+, 4,554, 4,562, 4,571+, 4,600+, 8,554, 8,600+", "4,571–4,578 official; 4,541 in this dataset", "WIKI_ADMIN", "8,554/8,600+ are wrong. Read the live count from the DB, don't hard-code it."),
    ("City corporations", "12", "13 (Bogura added May 2026)", "FE_BOGURA", "Update to 13."),
    ("Pourashavas", "326, 329", "330 (Wikipedia; may be 329 after Bogura's upgrade)", "WIKI_ADMIN", "Confirm with LGD before publishing."),
    ("Fire service hotline", "16163", "102", "FE_102", "Replace 16163 with 102."),
    ("Police helpline", "100", "999 (100 is not a Bangladesh police number)", "WIKI_TEL", "Remove 100."),
    ("Rajshahi District — upazilas", "8, 9, 12", "9", "WIKI_RAJ", "Use 9."),
    ("Rajshahi District — unions", "68, 70, 86, 106", "71", "NUHIL", "Matches the v2.8 release table."),
    ("Rajshahi District — area", "2,407 / 2,407.01 / 2,679 km²", "2,425.37 km²", "WIKI_RAJ", ""),
    ("Rajshahi District — population", "25.7 lakh, 27.40 lakh, 27,66,363", "29,15,009 enumerated / 29,78,156 adjusted (2022)", "CITYPOP_RAJ", "Pick one basis (enumerated or adjusted) for the whole app."),
    ("Rajshahi District — pourashavas", "2, 4, 7", "14 (list unverified)", "UNVERIFIED", "Confirm with LGD."),
    ("Rajshahi District — BBS code", "51 (admin panel)", "81", "CITYPOP_RAJ", "Use BBS geocode 81."),
    ("'Rajshahi Sadar Upazila'", "Detail page with 12 unions", "Does not exist — the city is Rajshahi City Corporation + metropolitan thanas", "WIKI_RAJ", "Drop the screen or replace it with the RCC page."),
    ("Rajshahi Division — upazilas", "67, 70", "67", "NUHIL", ""),
    ("Rajshahi Division — population", "1,86,52,402 / ~2.0 crore", "2,07,94,019 (2022 adjusted)", "CITYPOP_ADJ", ""),
    ("Dhaka Division — upazilas", "101, 103", "89", "NUHIL", ""),
    ("Dhaka District — upazilas", "20", "5 (Savar, Dhamrai, Keraniganj, Nawabganj, Dohar)", "NUHIL", "20 counts metropolitan thanas — keep thanas separate."),
    ("Dhaka Division — population", "~4.5 / 4.6 crore", "4,56,44,586 (2022 adjusted)", "CITYPOP_ADJ", ""),
    ("Rajshahi City Corporation — established", "2014", "Municipal corporation 1987; city corporation later (confirm year)", "WIKI_RAJ", "Fix 2014."),
    ("RU — departments / students", "56–58 depts; ~34,000–38,000 students", "59 depts; 25,000+ students", "WIKI_RU", ""),
    ("RU — vice-chancellor", "Prof. Saleh Hasan Naqib", "Faridul Islam (since 16 Mar 2026)", "WIKI_RU", ""),
    ("RMCH — beds", "1,200+", "530 (1965) → 862 (Wikipedia); current figure unconfirmed", "WIKI_RMC", "Get from hospital."),
    ("Puthia Rajbari — distance", "22 km", "~30 km east of Rajshahi town", "WIKI_PUTHIA", ""),
    ("District grid — Sylhet", "Listed under Rajshahi Division", "Sylhet Division", "NUHIL", "Mockup bug."),
    ("Kantajew Temple", "Popular place in Rajshahi District", "Dinajpur District (Rangpur Division)", "UNVERIFIED", "Mockup bug."),
    ("Paba unions", "5 (Damkura, Hariyan, Parila, Naohata, Baya)", "8 in dataset; Naohata is a pourashava", "NUHIL", ""),
]

KNOWN_GAPS = [
    ("unions", "~30–37 unions missing vs the official 4,571–4,578 (dataset has 4,541).", "Import the LGD/BBS union list and reconcile by geocode."),
    ("unions", "New upazilas Eidgaon, Madhyanagar, Dasar, Guimara and Naldanga have 0 unions; their unions still sit under the parent upazilas.", "Re-parent unions per the creation gazettes."),
    ("unions", "Shayestaganj union and Nurpur were moved to Shayestaganj Upazila; Brahmandura was added without a source id.", "Confirm against LGD."),
    ("upazilas", "No coordinates or boundaries for upazilas/unions.", "Use the BBS/HDX admin boundary sets (ADM3/ADM4)."),
    ("codes", "BBS geocodes are filled for divisions only.", "Add district/upazila/union geocodes from BBS."),
    ("pourashavas", "Only Rajshahi District's 14 pourashavas are listed, and that list is unverified.", "Import the LGD pourashava list (330)."),
    ("wards/villages", "No wards, mouzas or villages.", "BBS mouza/village lists."),
    ("area", "District areas are computed from boundary polygons (approximate).", "Replace with BBS official areas."),
    ("population", "District/division population uses the 2022 adjusted figures; Rajshahi upazilas use enumerated figures.", "Choose one basis app-wide."),
    ("places", "Only 8 pilot places; 3 are unverified and have no coordinates.", "Field verification + OSM import."),
]


# ---------------- Data trust & reconciliation (Nov 2026 audit) ----------------
# Source metadata for data_sources (type, organisation, licence, trust 1-5, access date).
# Licence is recorded only where the source states one; None means "not stated — check before redistribution".
SOURCE_META = {
    "NUHIL": dict(type="community_dataset", org="nuhil (GitHub)", license="MIT", trust=1, accessed="2026-11-09"),
    "CITYPOP_ADJ": dict(type="census_aggregator", org="citypopulation.de (BBS Census 2022)", license=None, trust=3, accessed="2026-11-09"),
    "CITYPOP_RAJ": dict(type="census_aggregator", org="citypopulation.de (BBS Census 2022)", license=None, trust=3, accessed="2026-11-09"),
    "WIKI_RAJ": dict(type="encyclopedia", org="Wikipedia", license="CC BY-SA 4.0", trust=3, accessed="2026-11-09"),
    "WIKI_CC": dict(type="encyclopedia", org="Wikipedia", license="CC BY-SA 4.0", trust=3, accessed="2026-11-11"),
    "WIKI_ADMIN": dict(type="encyclopedia", org="Wikipedia", license="CC BY-SA 4.0", trust=3, accessed="2026-11-11"),
    "FE_BOGURA": dict(type="news", org="The Financial Express", license=None, trust=3, accessed="2026-11-09"),
    "WIKI_SHAY": dict(type="encyclopedia", org="Wikipedia", license="CC BY-SA 4.0", trust=3, accessed="2026-11-09"),
    "FE_102": dict(type="news", org="The Financial Express", license=None, trust=3, accessed="2026-11-09"),
    "WIKI_TEL": dict(type="encyclopedia", org="Wikipedia", license="CC BY-SA 4.0", trust=3, accessed="2026-11-09"),
    "WIKI_RU": dict(type="encyclopedia", org="Wikipedia", license="CC BY-SA 4.0", trust=3, accessed="2026-11-09"),
    "WIKI_RUET": dict(type="encyclopedia", org="Wikipedia", license="CC BY-SA 4.0", trust=3, accessed="2026-11-11"),
    "WIKI_RMC": dict(type="encyclopedia", org="Wikipedia", license="CC BY-SA 4.0", trust=3, accessed="2026-11-09"),
    "WIKI_PUTHIA": dict(type="encyclopedia", org="Wikipedia", license="CC BY-SA 4.0", trust=3, accessed="2026-11-09"),
    "BANGLAPEDIA_PUTHIA": dict(type="encyclopedia", org="Asiatic Society of Bangladesh", license=None, trust=3, accessed="2026-11-09"),
    "WIKI_VRM": dict(type="encyclopedia", org="Wikipedia", license="CC BY-SA 4.0", trust=3, accessed="2026-11-09"),
    "RU_VRM": dict(type="institution_website", org="University of Rajshahi", license=None, trust=3, accessed="2026-11-09"),
    "MOCKUP": dict(type="design_placeholder", org="Elaka360", license=None, trust=1, accessed=None),
    "UNVERIFIED": dict(type="none", org=None, license=None, trust=1, accessed=None),
    "NATORE_DC_2026": dict(type="government_portal", org="Natore District Administration", license=None, trust=4, accessed="2026-11-04"),
    "MASTER_V3": dict(type="project_reconciliation", org="Elaka360", license=None, trust=2, accessed="2026-11-04"),
}

# The v0.1 seed linked three sources to a third-party Wikipedia mirror; they now point to wikipedia.org.
SOURCE_URL_FIXES = {
    "WIKI_CC": "wiki.krisyotam.com mirror -> https://en.wikipedia.org/wiki/List_of_city_corporations_in_Bangladesh (facts read from a Mar 2026 snapshot)",
    "WIKI_ADMIN": "wiki.krisyotam.com mirror -> https://en.wikipedia.org/wiki/Administrative_geography_of_Bangladesh",
    "WIKI_RUET": "wiki.krisyotam.com mirror -> https://en.wikipedia.org/wiki/Rajshahi_University_of_Engineering_%26_Technology",
}

# Mechanical clean-ups of nuhil union names (keyed by nuhil union id). Only artefacts of the
# source's URL-derived names are fixed: a stray number, an "up" (union parishad) suffix.
UNION_NAME_FIXES = {
    "1176": dict(name_bn="গোপালনগর", why="Bangla name had a leading digit '১' (union number) in the source"),
    "1278": dict(name_en="Maria", why="English name 'Mariaup' carried the 'up' (union parishad) suffix from its website slug"),
    "1414": dict(name_en="Mohadevpur", why="English name '1nomohadevpur' carried a '1 no.' prefix from its website slug (union No. 1)"),
    "2806": dict(name_bn="আমদিয়া", why="Bangla name had a trailing '২' not present in the English name or website slug"),
    "3177": dict(name_en="Maijchar", why="English name 'Maijchar9' carried a trailing union number from its website slug"),
}

# Exact duplicates in nuhil (same upazila, same name). The first row is kept.
UNION_DUPLICATE_DROPS = {
    "2353": "Duplicate of nuhil:union:2352 Awajpur (Charfesson): identical name, Bangla name and website",
    "2546": "Duplicate of nuhil:union:2540 Talimpur (Barlekha): identical name, Bangla name and website",
    "3686": "Duplicate of nuhil:union:3685 Bhojoanpur (Tetulia): same name and Bangla name; website points to gazipur.gov.bd",
}

# Natore: five unions listed under Natore Sadar in nuhil belong to Naldanga upazila
# (Natore District Administration: Natore Sadar 7, Naldanga 5). nuhil union ids:
NALDANGA_UNION_IDS = {"1285", "1286", "1287", "1288", "1289"}

# Known, tracked differences between the seed and Consolidated Master v3.0. The validator fails on any
# difference not listed here, and on any entry here that no longer differs (so the list stays honest).
KNOWN_MASTER_DIFFS = {
    ("count", "Sirajganj", "Ullapara"): "SIR-001/SIR-002: master selects 83 (Ullapara 14) from the district administration; BBS 2011 and the seed have 82. The 83rd union is not identified.",
    ("count", "Bogura", "Gabtali"): "BOG-005: master baseline Gabtali 12 / Sonatala 6 vs seed 11 / 7; same district total 108. A union may sit under the other upazila in nuhil.",
    ("count", "Bogura", "Sonatala"): "BOG-005: see Gabtali.",
    ("name", "Rajshahi", "Bagha", "master_only", "Chakrajapur"): "RAJ-001/RAJ-002: Bagha 6 vs 7. Chakrajapur appears in Rajshahi v1.7 from the Bagha upazila portal; not in the selected 71 baseline.",
    ("name", "Naogaon", "Raninagar", "master_only", "Khateshwar Raninagar"): "Likely spelling variant of seed 'Khatteshawr' (খট্টেশ্বর রাণীনগর); master has no Bangla name for this row.",
    ("name", "Naogaon", "Raninagar", "seed_only", "Khatteshawr"): "See 'Khateshwar Raninagar'.",
    ("name", "Chapainawabganj", "Chapainawabganj Sadar", "master_only", "Parbatipur"): "CNB-003: master register repeats this name under Gomastapur with a copied geocode suffix; register not reliable here.",
    ("name", "Chapainawabganj", "Chapainawabganj Sadar", "master_only", "Panka"): "CNB-003: master register repeats this name under Shibganj; register not reliable here.",
    ("name", "Chapainawabganj", "Chapainawabganj Sadar", "master_only", "Radhanagar"): "CNB-003: master register repeats this name under Gomastapur; register not reliable here.",
    ("name", "Chapainawabganj", "Chapainawabganj Sadar", "seed_only", "Jhilim"): "CNB-003: absent from the master register; seed keeps nuhil name until row-level evidence exists.",
    ("name", "Chapainawabganj", "Chapainawabganj Sadar", "seed_only", "Shahjahanpur"): "CNB-003: absent from the master register; seed keeps nuhil name.",
    ("name", "Chapainawabganj", "Chapainawabganj Sadar", "seed_only", "Narayanpur"): "CNB-003: absent from the master register; seed keeps nuhil name.",
    ("name", "Chapainawabganj", "Gomostapur", "master_only", "Ghorapakhia"): "CNB-002/CNB-003: master repeats this name under Shibganj; Gomastapur 8 vs 9 open.",
    ("name", "Chapainawabganj", "Gomostapur", "seed_only", "Rahanpur"): "CNB-003: absent from the master register; Rahanpur is also a pourashava name.",
    ("name", "Chapainawabganj", "Shibganj", "master_only", "Trimohoni"): "CNB-003: not in seed.",
    ("name", "Chapainawabganj", "Shibganj", "seed_only", "Ujirpur"): "CNB-003: absent from the master register.",
}
