"""
Nifty 50 + Nifty Next 50 + Nifty Midcap 100 universe
with sector tags and F&O eligibility.
"""

# Symbol: (Sector, display_name)
STOCK_META = {
    # ── BANKING ──────────────────────────────────────────────────────────────
    "HDFCBANK":    ("Banking",      "HDFC Bank"),
    "ICICIBANK":   ("Banking",      "ICICI Bank"),
    "SBIN":        ("Banking",      "State Bank"),
    "AXISBANK":    ("Banking",      "Axis Bank"),
    "KOTAKBANK":   ("Banking",      "Kotak Bank"),
    "INDUSINDBK":  ("Banking",      "IndusInd Bank"),
    "BANDHANBNK":  ("Banking",      "Bandhan Bank"),
    "FEDERALBNK":  ("Banking",      "Federal Bank"),
    "AUBANK":      ("Banking",      "AU Small Finance"),
    "IDFCFIRSTB":  ("Banking",      "IDFC First Bank"),
    "PNB":         ("Banking",      "Punjab National"),
    "BANKBARODA":  ("Banking",      "Bank of Baroda"),
    "CANBK":       ("Banking",      "Canara Bank"),
    "UNIONBANK":   ("Banking",      "Union Bank"),
    "RBLBANK":     ("Banking",      "RBL Bank"),
    "YESBANK":     ("Banking",      "Yes Bank"),

    # ── FINANCE / NBFC ────────────────────────────────────────────────────────
    "BAJFINANCE":  ("Finance",      "Bajaj Finance"),
    "BAJAJFINSV":  ("Finance",      "Bajaj Finserv"),
    "SHRIRAMFIN":  ("Finance",      "Shriram Finance"),
    "CHOLAFIN":    ("Finance",      "Cholamandalam"),
    "MUTHOOTFIN":  ("Finance",      "Muthoot Finance"),
    "MANAPPURAM":  ("Finance",      "Manappuram Fin"),
    "LICHSGFIN":   ("Finance",      "LIC Housing"),
    "SBICARD":     ("Finance",      "SBI Cards"),
    "HDFCAMC":     ("Finance",      "HDFC AMC"),
    "ABCAPITAL":   ("Finance",      "Aditya Birla Cap"),
    "MFSL":        ("Finance",      "Max Financial"),
    "ICICIGI":     ("Finance",      "ICICI Lombard"),
    "ICICIPRULI":  ("Finance",      "ICICI Pru Life"),
    "SBILIFE":     ("Finance",      "SBI Life"),
    "HDFCLIFE":    ("Finance",      "HDFC Life"),
    "M&MFIN":      ("Finance",      "M&M Financial"),

    # ── IT / TECHNOLOGY ──────────────────────────────────────────────────────
    "TCS":         ("IT",           "Tata Consultancy"),
    "INFY":        ("IT",           "Infosys"),
    "HCLTECH":     ("IT",           "HCL Technologies"),
    "WIPRO":       ("IT",           "Wipro"),
    "TECHM":       ("IT",           "Tech Mahindra"),
    "LTIM":        ("IT",           "LTIMindtree"),
    "MPHASIS":     ("IT",           "Mphasis"),
    "OFSS":        ("IT",           "Oracle Fin Serv"),
    "COFORGE":     ("IT",           "Coforge"),
    "PERSISTENT":  ("IT",           "Persistent Sys"),
    "KPITTECH":    ("IT",           "KPIT Tech"),

    # ── AUTO ──────────────────────────────────────────────────────────────────
    "MARUTI":      ("Auto",         "Maruti Suzuki"),
    "TMPV":        ("Auto",         "Tata Motors PV"),
    "M&M":         ("Auto",         "Mahindra"),
    "BAJAJ-AUTO":  ("Auto",         "Bajaj Auto"),
    "HEROMOTOCO":  ("Auto",         "Hero MotoCorp"),
    "EICHERMOT":   ("Auto",         "Eicher Motors"),
    "TVSMOTOR":    ("Auto",         "TVS Motor"),
    "ASHOKLEY":    ("Auto",         "Ashok Leyland"),
    "TIINDIA":     ("Auto",         "Tube Investments"),
    "BALKRISIND":  ("Auto",         "Balkrishna Ind"),
    "MOTHERSON":   ("Auto",         "Samvardhana"),
    "MINDA":       ("Auto",         "UNO Minda"),
    "BOSCHLTD":    ("Auto",         "Bosch"),
    "BHARATFORG":  ("Auto",         "Bharat Forge"),

    # ── PHARMA / HEALTHCARE ──────────────────────────────────────────────────
    "SUNPHARMA":   ("Pharma",       "Sun Pharma"),
    "DRREDDY":     ("Pharma",       "Dr Reddy's"),
    "CIPLA":       ("Pharma",       "Cipla"),
    "APOLLOHOSP":  ("Pharma",       "Apollo Hospitals"),
    "LUPIN":       ("Pharma",       "Lupin"),
    "DIVISLAB":    ("Pharma",       "Divi's Labs"),
    "AUROPHARMA":  ("Pharma",       "Aurobindo"),
    "ALKEM":       ("Pharma",       "Alkem Labs"),
    "GLENMARK":    ("Pharma",       "Glenmark"),
    "IPCALAB":     ("Pharma",       "IPCA Labs"),
    "BIOCON":      ("Pharma",       "Biocon"),
    "LALPATHLAB":  ("Pharma",       "Dr Lal PathLabs"),
    "ZYDUSLIFE":   ("Pharma",       "Zydus Lifesciences"),
    "TORNTPHARM":  ("Pharma",       "Torrent Pharma"),
    "MAXHEALTH":   ("Pharma",       "Max Healthcare"),

    # ── FMCG / CONSUMER ──────────────────────────────────────────────────────
    "ITC":         ("FMCG",         "ITC"),
    "HINDUNILVR":  ("FMCG",         "Hindustan Unilever"),
    "NESTLEIND":   ("FMCG",         "Nestle India"),
    "BRITANNIA":   ("FMCG",         "Britannia"),
    "DABUR":       ("FMCG",         "Dabur"),
    "COLPAL":      ("FMCG",         "Colgate-Palmolive"),
    "MARICO":      ("FMCG",         "Marico"),
    "GODREJCP":    ("FMCG",         "Godrej Consumer"),
    "TATACONSUM":  ("FMCG",         "Tata Consumer"),
    "VBL":         ("FMCG",         "Varun Beverages"),
    "MCDOWELL-N":  ("FMCG",         "United Spirits"),
    "PGHH":        ("FMCG",         "P&G Hygiene"),
    "DMART":       ("FMCG",         "Avenue Supermarts"),

    # ── ENERGY / OIL ─────────────────────────────────────────────────────────
    "RELIANCE":    ("Energy",       "Reliance Industries"),
    "ONGC":        ("Energy",       "ONGC"),
    "BPCL":        ("Energy",       "BPCL"),
    "POWERGRID":   ("Energy",       "Power Grid"),
    "NTPC":        ("Energy",       "NTPC"),
    "COALINDIA":   ("Energy",       "Coal India"),
    "TATAPOWER":   ("Energy",       "Tata Power"),
    "ADANIGREEN":  ("Energy",       "Adani Green"),
    "GAIL":        ("Energy",       "GAIL"),
    "PETRONET":    ("Energy",       "Petronet LNG"),
    "OIL":         ("Energy",       "Oil India"),
    "NHPC":        ("Energy",       "NHPC"),
    "HINDPETRO":   ("Energy",       "HPCL"),
    "RECLTD":      ("Energy",       "REC Limited"),

    # ── METALS ───────────────────────────────────────────────────────────────
    "JSWSTEEL":    ("Metals",       "JSW Steel"),
    "TATASTEEL":   ("Metals",       "Tata Steel"),
    "HINDALCO":    ("Metals",       "Hindalco"),
    "VEDL":        ("Metals",       "Vedanta"),
    "SAIL":        ("Metals",       "SAIL"),
    "NMDC":        ("Metals",       "NMDC"),
    "NATIONALUM":  ("Metals",       "NALCO"),
    "HINDZINC":    ("Metals",       "Hindustan Zinc"),
    "APLAPOLLO":   ("Metals",       "APL Apollo Tubes"),
    "JINDALSTEL":  ("Metals",       "Jindal Steel"),

    # ── TELECOM ──────────────────────────────────────────────────────────────
    "BHARTIARTL":  ("Telecom",      "Bharti Airtel"),
    "IDEA":        ("Telecom",      "Vodafone Idea"),
    "INDUSTOWER":  ("Telecom",      "Indus Towers"),

    # ── CAPITAL GOODS / INFRA ────────────────────────────────────────────────
    "LT":          ("CapGoods",     "Larsen & Toubro"),
    "ABB":         ("CapGoods",     "ABB India"),
    "SIEMENS":     ("CapGoods",     "Siemens"),
    "BHEL":        ("CapGoods",     "BHEL"),
    "CUMMINSIND":  ("CapGoods",     "Cummins India"),
    "HAVELLS":     ("CapGoods",     "Havells"),
    "CROMPTON":    ("CapGoods",     "Crompton Greaves"),
    "POLYCAB":     ("CapGoods",     "Polycab"),
    "DIXON":       ("CapGoods",     "Dixon Technologies"),
    "BEL":         ("CapGoods",     "Bharat Electronics"),
    "CONCOR":      ("CapGoods",     "Container Corp"),
    "IRCTC":       ("CapGoods",     "IRCTC"),
    "GMRINFRA":    ("CapGoods",     "GMR Airports"),

    # ── CEMENT ────────────────────────────────────────────────────────────────
    "ULTRACEMCO":  ("Cement",       "UltraTech Cement"),
    "AMBUJACEM":   ("Cement",       "Ambuja Cements"),
    "DALBHARAT":   ("Cement",       "Dalmia Bharat"),
    "SHREECEM":    ("Cement",       "Shree Cement"),
    "JKCEMENT":    ("Cement",       "JK Cement"),

    # ── REAL ESTATE ──────────────────────────────────────────────────────────
    "DLF":         ("RealEstate",   "DLF"),
    "GODREJPROP":  ("RealEstate",   "Godrej Properties"),
    "OBEROIRLTY":  ("RealEstate",   "Oberoi Realty"),
    "PRESTIGE":    ("RealEstate",   "Prestige Estates"),
    "PHOENIXLTD":  ("RealEstate",   "Phoenix Mills"),
    "INDHOTEL":    ("RealEstate",   "Indian Hotels"),

    # ── CHEMICALS ────────────────────────────────────────────────────────────
    "DEEPAKNTR":   ("Chemicals",    "Deepak Nitrite"),
    "PIIND":       ("Chemicals",    "PI Industries"),
    "SRF":         ("Chemicals",    "SRF"),
    "GNFC":        ("Chemicals",    "Gujarat Narmada"),
    "AARTIIND":    ("Chemicals",    "Aarti Industries"),

    # ── ADANI GROUP ──────────────────────────────────────────────────────────
    "ADANIENT":    ("Conglomerate", "Adani Enterprises"),
    "ADANIPORTS":  ("Infrastructure","Adani Ports"),

    # ── OTHERS ───────────────────────────────────────────────────────────────
    "TITAN":       ("Consumer",     "Titan Company"),
    "ASIANPAINT":  ("Consumer",     "Asian Paints"),
    "BERGEPAINT":  ("Consumer",     "Berger Paints"),
    "PIDILITIND":  ("Consumer",     "Pidilite"),
    "GRASIM":      ("Consumer",     "Grasim"),
    "TRENT":       ("Consumer",     "Trent"),
    "NAUKRI":      ("IT",           "Info Edge (Naukri)"),
    "INDIGO":      ("Aviation",     "IndiGo"),
    "PAGEIND":     ("Consumer",     "Page Industries"),
    "MRF":         ("Auto",         "MRF"),
    "JIOFIN":      ("Finance",      "Jio Financial"),
    "PAYTM":       ("Finance",      "Paytm"),
    "BSE":         ("Finance",      "BSE"),
    "ADANIPOWER":  ("Energy",       "Adani Power"),
    "LICI":        ("Finance",      "LIC India"),
    "VOLTAS":      ("CapGoods",     "Voltas"),
    "SUPREMEIND":  ("Chemicals",    "Supreme Industries"),
    "TORNTPOWER":  ("Energy",       "Torrent Power"),
    "ASTRAL":      ("Chemicals",    "Astral Poly"),
    "LTTS":        ("IT",           "L&T Technology"),
    "JUBLFOOD":    ("FMCG",         "Jubilant FoodWorks"),
    "PVRINOX":     ("Media",        "PVR INOX"),
    "SUNTV":       ("Media",        "Sun TV Network"),
    "ABFRL":       ("Consumer",     "Aditya Birla Fashion"),
    "KAJARIACER":  ("Consumer",     "Kajaria Ceramics"),
    "CESC":        ("Energy",       "CESC"),
    "RECLTD":      ("Energy",       "REC Limited"),
    "BATAINDIA":   ("Consumer",     "Bata India"),
    "GRANULES":    ("Pharma",       "Granules India"),
    "PCBL":        ("Chemicals",    "PCBL"),

    # ── NIFTY 500 ADDITIONS ──────────────────────────────────────────────────

    # Banking / Finance (smallcap/midcap)
    "EQUITASBNK":  ("Banking",      "Equitas Small Finance"),
    "UJJIVAN":     ("Banking",      "Ujjivan Financial"),
    "KARURVYSYA":  ("Banking",      "Karur Vysya Bank"),
    "DCBBANK":     ("Banking",      "DCB Bank"),
    "SOUTHBANK":   ("Banking",      "South Indian Bank"),
    "KFINTECH":    ("Finance",      "KFin Technologies"),
    "CAMS":        ("Finance",      "CAMS"),
    "CDSL":        ("Finance",      "CDSL"),
    "ANGELONE":    ("Finance",      "Angel One"),
    "ICICISEC":    ("Finance",      "ICICI Securities"),
    "MOTILALOFS":  ("Finance",      "Motilal Oswal"),
    "IIFLWAM":     ("Finance",      "IIFL Wealth"),
    "PNBHOUSING":  ("Finance",      "PNB Housing"),
    "APTUS":       ("Finance",      "Aptus Value Housing"),
    "HOMEFIRST":   ("Finance",      "Home First Finance"),
    "CREDITACC":   ("Finance",      "CreditAccess Grameen"),
    "SPANDANA":    ("Finance",      "Spandana Sphoorty"),
    "AAVAS":       ("Finance",      "Aavas Financiers"),

    # IT / Tech
    "ZOMATO":      ("IT",           "Zomato"),
    "NYKAA":       ("Consumer",     "Nykaa"),
    "DELHIVERY":   ("Infrastructure","Delhivery"),
    "POLICYBZR":   ("Finance",      "PB Fintech"),
    "JUSTDIAL":    ("IT",           "Just Dial"),
    "ROUTE":       ("IT",           "Route Mobile"),
    "TATAELXSI":   ("IT",           "Tata Elxsi"),
    "INFY":        ("IT",           "Infosys"),        # already in meta but safe to repeat
    "TANLA":       ("IT",           "Tanla Platforms"),
    "BIRLASOFT":   ("IT",           "Birlasoft"),
    "MASTEK":      ("IT",           "Mastek"),
    "CYIENT":      ("IT",           "Cyient"),
    "HEXAWARE":    ("IT",           "Hexaware"),
    "NIITLTD":     ("IT",           "NIIT"),
    "INTELLECT":   ("IT",           "Intellect Design"),
    "NEWGEN":      ("IT",           "Newgen Software"),

    # Pharma / Healthcare
    "ABBOTINDIA":  ("Pharma",       "Abbott India"),
    "PFIZER":      ("Pharma",       "Pfizer"),
    "SANOFI":      ("Pharma",       "Sanofi India"),
    "GLAXO":       ("Pharma",       "GSK Pharma"),
    "WOCKHARDT":   ("Pharma",       "Wockhardt"),
    "NATCO":       ("Pharma",       "Natco Pharma"),
    "LAURUSLABS":  ("Pharma",       "Laurus Labs"),
    "GLAND":       ("Pharma",       "Gland Pharma"),
    "DIVISLAB":    ("Pharma",       "Divi's Laboratories"),
    "JBCHEPHARM":  ("Pharma",       "JB Chemicals"),
    "ERIS":        ("Pharma",       "Eris Lifesciences"),
    "AJANTPHARM":  ("Pharma",       "Ajanta Pharma"),
    "STRIDES":     ("Pharma",       "Strides Pharma"),
    "SEQUENT":     ("Pharma",       "Sequent Scientific"),
    "SUVEN":       ("Pharma",       "Suven Pharma"),

    # FMCG / Consumer
    "JYOTHYLAB":   ("FMCG",         "Jyothy Labs"),
    "EMAMILTD":    ("FMCG",         "Emami"),
    "RADICO":      ("FMCG",         "Radico Khaitan"),
    "MCDOWELL-N":  ("FMCG",         "United Spirits"),
    "UNITDSPR":    ("FMCG",         "United Spirits"),
    "PARAGMILK":   ("FMCG",         "Parag Milk Foods"),
    "BIKAJI":      ("FMCG",         "Bikaji Foods"),
    "PATANJALI":   ("FMCG",         "Patanjali Foods"),
    "HATSUN":      ("FMCG",         "Hatsun Agro"),
    "KRBL":        ("FMCG",         "KRBL"),
    "USHAMART":    ("FMCG",         "Usha Martin"),
    "PRATAAP":     ("FMCG",         "Prataap Snacks"),
    "GODFRYPHLP":  ("FMCG",         "Godfrey Phillips"),
    "VSTIND":      ("FMCG",         "VST Industries"),

    # Auto / Ancillary
    "APOLLOTYRE":  ("Auto",         "Apollo Tyres"),
    "CEATLTD":     ("Auto",         "CEAT"),
    "ESCORTS":     ("Auto",         "Escorts Kubota"),
    "FORCEMOT":    ("Auto",         "Force Motors"),
    "ENDURANCE":   ("Auto",         "Endurance Tech"),
    "SUPRAJIT":    ("Auto",         "Suprajit Engineering"),
    "SUNDRMFAST":  ("Auto",         "Sundram Fasteners"),
    "GABRIEL":     ("Auto",         "Gabriel India"),
    "LUMAXTECH":   ("Auto",         "Lumax Tech"),
    "CRAFTSMAN":   ("Auto",         "Craftsman Auto"),
    "SWARAJENG":   ("Auto",         "Swaraj Engines"),
    "GREENPANEL":  ("Consumer",     "Greenpanel"),
    "SONA BLW":    ("Auto",         "Sona BLW"),
    "SONACOMS":    ("Auto",         "Sona Comstar"),

    # Capital Goods / Engineering
    "THERMAX":     ("CapGoods",     "Thermax"),
    "KEC":         ("CapGoods",     "KEC International"),
    "KALPATPOWR":  ("CapGoods",     "Kalpataru Power"),
    "ENGINERSIN":  ("CapGoods",     "Engineers India"),
    "NRBBEARING":  ("CapGoods",     "NRB Bearings"),
    "RITES":       ("CapGoods",     "RITES"),
    "IRCON":       ("Infrastructure","IRCON International"),
    "BEML":        ("CapGoods",     "BEML"),
    "HAL":         ("CapGoods",     "Hindustan Aeronautics"),
    "GRSE":        ("CapGoods",     "GRSE"),
    "BDL":         ("CapGoods",     "Bharat Dynamics"),
    "MAZDA":       ("CapGoods",     "Mazda"),
    "RVNL":        ("Infrastructure","Rail Vikas Nigam"),
    "IRFC":        ("Finance",      "IRFC"),
    "PNCINFRA":    ("Infrastructure","PNC Infratech"),
    "IRB":         ("Infrastructure","IRB Infrastructure"),
    "ASHOKA":      ("Infrastructure","Ashoka Buildcon"),
    "DREDGE":      ("Infrastructure","Dredging Corp"),
    "COCHIN":      ("Infrastructure","Cochin Shipyard"),
    "RAILTEL":     ("IT",           "RailTel Corporation"),
    "MAZDOCK":     ("CapGoods",     "Mazagon Dock"),

    # Chemicals / Specialty
    "FINEORG":     ("Chemicals",    "Fine Organics"),
    "NAVINFLUOR":  ("Chemicals",    "Navin Fluorine"),
    "ROSSARI":     ("Chemicals",    "Rossari Biotech"),
    "TATACHEM":    ("Chemicals",    "Tata Chemicals"),
    "GHCL":        ("Chemicals",    "GHCL"),
    "SUDARSCHEM":  ("Chemicals",    "Sudarshan Chemical"),
    "VINATIORGA":  ("Chemicals",    "Vinati Organics"),
    "CLEAN":       ("Chemicals",    "Clean Science"),
    "NOCIL":       ("Chemicals",    "NOCIL"),
    "ALKYLAMINE":  ("Chemicals",    "Alkyl Amines"),
    "BALRAMCHIN":  ("Chemicals",    "Balrampur Chini"),
    "CHAMBLFERT":  ("Chemicals",    "Chambal Fertilisers"),
    "GNFC":        ("Chemicals",    "Gujarat Narmada"),
    "GSFC":        ("Chemicals",    "GSFC"),
    "COROMANDEL":  ("Chemicals",    "Coromandel Intl"),
    "BAYERCROP":   ("Chemicals",    "Bayer CropScience"),
    "SUMICHEM":    ("Chemicals",    "Sumitomo Chemical"),
    "RALLIS":      ("Chemicals",    "Rallis India"),

    # Cement / Construction
    "HEIDELBERG":  ("Cement",       "Heidelberg Cement"),
    "RAMCOCEM":    ("Cement",       "Ramco Cements"),
    "NCLIND":      ("Cement",       "NCL Industries"),
    "BIRLACORPN":  ("Cement",       "Birla Corporation"),
    "ORIENTCEM":   ("Cement",       "Orient Cement"),
    "STARCEMENT":  ("Cement",       "Star Cement"),

    # Real Estate
    "SOBHA":       ("RealEstate",   "Sobha Developers"),
    "MAHLIFE":     ("RealEstate",   "Mahindra Lifespace"),
    "KOLTEPATIL":  ("RealEstate",   "Kolte-Patil"),
    "SUNTECK":     ("RealEstate",   "Sunteck Realty"),
    "BRIGADE":     ("RealEstate",   "Brigade Enterprises"),
    "NESCO":       ("RealEstate",   "Nesco"),
    "MHRIL":       ("RealEstate",   "Mahindra Holidays"),

    # Metals / Mining (additional)
    "WELSPUN":     ("Metals",       "Welspun Corp"),
    "JINDALSAW":   ("Metals",       "Jindal SAW"),
    "RATNAMANI":   ("Metals",       "Ratnamani Metals"),
    "MOIL":        ("Metals",       "MOIL"),
    "GMDCLTD":     ("Metals",       "GMDC"),
    "VEDL":        ("Metals",       "Vedanta"),

    # Logistics / Infra
    "BLUEDART":    ("Infrastructure","Blue Dart Express"),
    "MAHLOG":      ("Infrastructure","Mahindra Logistics"),
    "GATI":        ("Infrastructure","Gati"),
    "AEGISLOG":    ("Infrastructure","Aegis Logistics"),
    "GPPL":        ("Infrastructure","Gujarat Pipavav Port"),

    # Consumer / Retail
    "RAYMOND":     ("Consumer",     "Raymond"),
    "RELAXO":      ("Consumer",     "Relaxo Footwears"),
    "VMART":       ("Consumer",     "V-Mart Retail"),
    "METRO":       ("Consumer",     "Metro Brands"),
    "VEDANT":      ("Consumer",     "Vedant Fashions"),
    "SAPPHIRE":    ("Consumer",     "Sapphire Foods"),
    "DEVYANI":     ("Consumer",     "Devyani International"),
    "WESTLIFE":    ("Consumer",     "Westlife Foodworld"),
    "BARBEQUE":    ("Consumer",     "Barbeque Nation"),
    "CAMPUS":      ("Consumer",     "Campus Activewear"),
    "MANYAVAR":    ("Consumer",     "Vedant Fashions"),
    "CERA":        ("Consumer",     "CERA Sanitaryware"),
    "SYMPHONY":    ("Consumer",     "Symphony"),
    "WHIRLPOOL":   ("Consumer",     "Whirlpool India"),
    "BLUESTAR":    ("CapGoods",     "Blue Star"),
    "AMBER":       ("CapGoods",     "Amber Enterprises"),
    "DIXON":       ("CapGoods",     "Dixon Technologies"),

    # Media
    "ZEEL":        ("Media",        "Zee Entertainment"),
    "TV18BRDCST":  ("Media",        "TV18 Broadcast"),
    "NTWK18":      ("Media",        "Network18"),
    "TIPS":        ("Media",        "Tips Industries"),

    # Power / Utilities
    "ADANIENSOL":  ("Energy",       "Adani Energy Solutions"),
    "TATAPOWER":   ("Energy",       "Tata Power"),
    "JSWENERGY":   ("Energy",       "JSW Energy"),
    "NTPC":        ("Energy",       "NTPC"),
    "RPOWER":      ("Energy",       "Reliance Power"),
    "CESC":        ("Energy",       "CESC"),
    "SJVN":        ("Energy",       "SJVN"),
    "IREDA":       ("Energy",       "IREDA"),
    "INDIGRID":    ("Energy",       "IndiGrid InvIT"),

    # Textiles
    "WELSPUNIND":  ("Consumer",     "Welspun India"),
    "VARDHMAN":    ("Consumer",     "Vardhman Textiles"),
    "TRIDENT":     ("Consumer",     "Trident"),
    "ARVIND":      ("Consumer",     "Arvind"),
    "PGHL":        ("Consumer",     "Procter & Gamble"),

    # Agri / Food
    "UBL":         ("FMCG",         "United Breweries"),
    "ZYDUSWELL":   ("FMCG",         "Zydus Wellness"),
    "DODLA":       ("FMCG",         "Dodla Dairy"),
    "HERITGFOOD":  ("FMCG",         "Heritage Foods"),
    "CCL":         ("FMCG",         "CCL Products"),
}

# Ordered universe: Nifty 50 first, then Next 50, then Midcap
NIFTY_50 = [
    "RELIANCE","HDFCBANK","BHARTIARTL","TCS","ICICIBANK",
    "SBIN","INFY","BAJFINANCE","HINDUNILVR","ITC",
    "LT","HCLTECH","KOTAKBANK","SUNPHARMA","M&M",
    "MARUTI","ULTRACEMCO","AXISBANK","NTPC","BAJAJFINSV",
    "ADANIPORTS","ONGC","BEL","TITAN","ADANIENT",
    "WIPRO","POWERGRID","TMPV","JSWSTEEL","ASIANPAINT",
    "COALINDIA","NESTLEIND","BAJAJ-AUTO","TATASTEEL","TRENT",
    "GRASIM","SBILIFE","HDFCLIFE","TECHM","EICHERMOT",
    "HINDALCO","SHRIRAMFIN","CIPLA","TATACONSUM","APOLLOHOSP",
    "DRREDDY","HEROMOTOCO","INDUSINDBK","DMART","JIOFIN",
]

NIFTY_NEXT_50 = [
    "PIDILITIND","AMBUJACEM","GODREJCP","DABUR","ICICIGI",
    "HINDZINC","SIEMENS","LTIM","CONCOR","ASTRAL",
    "ALKEM","ABB","BHARATFORG","BOSCHLTD","CUMMINSIND",
    "BERGEPAINT","DLF","VEDL","IRCTC","MUTHOOTFIN",
    "COLPAL","OFSS","JUBLFOOD","MARICO","GODREJPROP",
    "LTTS","DIXON","SBICARD","CHOLAFIN","TVSMOTOR",
    "ICICIPRULI","NMDC","BHEL","SUPREMEIND","MRF",
    "TATAPOWER","COFORGE","HDFCAMC","POLYCAB","BSE",
    "SRF","PERSISTENT","LUPIN","ASHOKLEY","TORNTPOWER",
    "AUBANK","IDFCFIRSTB","SAIL","MPHASIS","PAGEIND",
]

NIFTY_MIDCAP_100 = [
    "ABCAPITAL","ABFRL","BALKRISIND","BANDHANBNK","BANKBARODA",
    "BATAINDIA","BIOCON","CANBK","CESC","DEEPAKNTR",
    "FEDERALBNK","GLENMARK","GODREJPROP","GRANULES","HAVELLS",
    "HINDPETRO","IDFCFIRSTB","INDHOTEL","INDUSTOWER","IPCALAB",
    "JKCEMENT","JUBLFOOD","KAJARIACER","KPITTECH","LICHSGFIN",
    "LICI","MANAPPURAM","MFSL","MOTHERSON","M&MFIN",
    "NATIONALUM","NMDC","OBEROIRLTY","OIL","PETRONET",
    "PHOENIXLTD","PIIND","PNB","PVRINOX","RBLBANK",
    "SHREECEM","SUNTV","TIINDIA","TORNTPHARM","TVSMOTOR",
    "UNIONBANK","VBL","VOLTAS","YESBANK","ZYDUSLIFE",
    "ADANIGREEN","ADANIPOWER","DALBHARAT","GNFC","GAIL",
    "GMRINFRA","INDIGO","JINDALSTEL","LALPATHLAB","MAXHEALTH",
    "MINDA","MPHASIS","NAUKRI","NHPC","PAYTM",
    "PRESTIGE","RECLTD","SAIL","APLAPOLLO","AARTIIND",
]

NIFTY_200 = list(dict.fromkeys(NIFTY_50 + NIFTY_NEXT_50 + NIFTY_MIDCAP_100))

# Nifty 500 = Nifty 200 + all additional stocks in STOCK_META
NIFTY_500 = list(dict.fromkeys(NIFTY_200 + [s for s in STOCK_META if s not in NIFTY_200]))

NIFTY_MIDCAP_50 = [
    "ABCAPITAL","ABFRL","ASHOKLEY","ASTRAL","BALKRISIND",
    "BANDHANBNK","BANKBARODA","BATAINDIA","BERGEPAINT","BHARATFORG",
    "BIOCON","CANBK","CESC","COFORGE","CONCOR",
    "DEEPAKNTR","DIXON","FEDERALBNK","GLENMARK","GODREJPROP",
    "GRANULES","HAVELLS","HINDPETRO","IDFCFIRSTB","INDHOTEL",
    "INDUSTOWER","IPCALAB","JKCEMENT","KAJARIACER","KPITTECH",
    "LICHSGFIN","LICI","MANAPPURAM","MAXHEALTH","MFSL",
    "MOTHERSON","MUTHOOTFIN","NMDC","OBEROIRLTY","OIL",
    "PAGEIND","PETRONET","PHOENIXLTD","PIIND","PRESTIGE",
    "PVRINOX","RBLBANK","SHREECEM","TIINDIA","TORNTPHARM",
]

MARKETS = {
    "nifty50":      {"name": "Nifty 50",         "symbols": NIFTY_50},
    "niftynext50":  {"name": "Nifty Next 50",     "symbols": NIFTY_NEXT_50},
    "nifty100":     {"name": "Nifty 100",         "symbols": list(dict.fromkeys(NIFTY_50 + NIFTY_NEXT_50))},
    "nifty200":     {"name": "Nifty 200",         "symbols": NIFTY_200},
    "nifty500":     {"name": "Nifty 500",         "symbols": NIFTY_500},
    "midcap50":     {"name": "Nifty Midcap 50",   "symbols": NIFTY_MIDCAP_50},
    "midcap100":    {"name": "Nifty Midcap 100",  "symbols": NIFTY_MIDCAP_100},
}

SECTOR_COLORS = {
    "Banking":    "#1f6feb",
    "Finance":    "#388bfd",
    "IT":         "#bc8cff",
    "Auto":       "#e3b341",
    "Pharma":     "#3fb950",
    "FMCG":       "#58a6ff",
    "Energy":     "#f97316",
    "Metals":     "#8b949e",
    "Telecom":    "#a78bfa",
    "CapGoods":   "#f59e0b",
    "Cement":     "#6b7280",
    "RealEstate": "#ec4899",
    "Chemicals":  "#06b6d4",
    "Consumer":       "#d97706",
    "Conglomerate":   "#ef4444",
    "Infrastructure": "#fb923c",
    "Media":          "#84cc16",
    "Aviation":       "#14b8a6",
}


def get_meta(symbol: str) -> dict:
    clean = symbol.replace(".NS", "")
    sector, name = STOCK_META.get(clean, ("Other", clean))
    return {
        "symbol": clean,
        "name": name,
        "sector": sector,
        "sector_color": SECTOR_COLORS.get(sector, "#6b7280"),
    }


# F&O eligible set — populated dynamically from Kite API, fallback to known list
_FO_SYMBOLS: set[str] = set()

KNOWN_FO = {
    "RELIANCE","HDFCBANK","TCS","ICICIBANK","SBIN","INFY","BAJFINANCE","HINDUNILVR",
    "ITC","LT","HCLTECH","KOTAKBANK","SUNPHARMA","M&M","MARUTI","ULTRACEMCO",
    "AXISBANK","NTPC","BAJAJFINSV","ADANIPORTS","ONGC","TITAN","ADANIENT","WIPRO",
    "POWERGRID","TMPV","JSWSTEEL","ASIANPAINT","COALINDIA","NESTLEIND",
    "BAJAJ-AUTO","TATASTEEL","TRENT","GRASIM","SBILIFE","HDFCLIFE","TECHM",
    "EICHERMOT","HINDALCO","SHRIRAMFIN","CIPLA","TATACONSUM","APOLLOHOSP","DRREDDY",
    "HEROMOTOCO","INDUSINDBK","DMART","BHARTIARTL","PIDILITIND","AMBUJACEM","GODREJCP",
    "DABUR","ICICIGI","SIEMENS","LTIM","ABB","BHARATFORG","BOSCHLTD","CUMMINSIND",
    "DLF","VEDL","IRCTC","MUTHOOTFIN","COLPAL","OFSS","MARICO","GODREJPROP",
    "DIXON","SBICARD","CHOLAFIN","TVSMOTOR","ICICIPRULI","NMDC","BHEL","MRF",
    "TATAPOWER","COFORGE","HDFCAMC","POLYCAB","SRF","PERSISTENT","LUPIN",
    "ASHOKLEY","AUBANK","IDFCFIRSTB","SAIL","MPHASIS","ABCAPITAL","BALKRISIND",
    "BANKBARODA","BIOCON","CESC","DEEPAKNTR","FEDERALBNK","GLENMARK","GRANULES",
    "HAVELLS","HINDPETRO","INDHOTEL","IPCALAB","JUBLFOOD","KPITTECH","LICHSGFIN",
    "MANAPPURAM","MOTHERSON","M&MFIN","NATIONALUM","OBEROIRLTY","PETRONET",
    "PHOENIXLTD","PIIND","PNB","PVRINOX","RBLBANK","SUNTV","TIINDIA","TORNTPHARM",
    "VBL","VOLTAS","ZYDUSLIFE","ADANIGREEN","DALBHARAT","GAIL","GMRINFRA","INDIGO",
    "LALPATHLAB","MAXHEALTH","MINDA","NAUKRI","NHPC","PRESTIGE","RECLTD","APLAPOLLO",
    "HINDZINC","BSE","BEL","CONCOR","LTTS","ASTRAL","ALKEM","SUPREMEIND","BERGEPAINT",
    "PAGEIND","CANBK","UNIONBANK","YESBANK","PAYTM","ADANIPOWER","LICI","JIOFIN",
    "TORNTPOWER","KAJARIACER","GNFC","JINDALSTEL","OIL","ABFRL","MFSL","HDFCLIFE",
}


def is_fo(symbol: str) -> bool:
    clean = symbol.replace(".NS", "")
    if _FO_SYMBOLS:
        return clean in _FO_SYMBOLS
    return clean in KNOWN_FO


def set_fo_symbols(symbols: set[str]):
    global _FO_SYMBOLS
    _FO_SYMBOLS = {s.replace(".NS", "") for s in symbols}
