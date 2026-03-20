#!/usr/bin/env python3
"""
Test Prospect Scorer with Synthetic Companies House Data

This script:
1. Checks for Companies House bulk data availability
2. Creates synthetic UK company data representative of the UK business population
3. Runs the prospect scorer on the test data
4. Generates comprehensive analysis with visualizations

Author: PackagePro Analytics Team
"""

import os
import sys
from pathlib import Path
import random
import json
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

# Add parent directory to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "scripts"))

# Import the prospect scorer
from prospect_scorer import (
    ProspectScorer, ICPProfile, CompaniesHouseLoader,
    sic_to_sector, SIC_SECTOR_MAP
)

# =============================================================================
# UK Business Population Statistics (Based on ONS/Companies House data)
# =============================================================================

# SIC codes with realistic UK business distribution
# Format: (sic_code, description, weight based on UK business population)
UK_SIC_CODES = [
    # Manufacturing (10-33) - 5% of UK businesses
    ("10110", "Processing and preserving of meat", 0.3),
    ("10710", "Manufacture of bread; manufacture of fresh pastry goods", 0.4),
    ("14190", "Manufacture of other wearing apparel and accessories", 0.5),
    ("17210", "Manufacture of corrugated paper and paperboard", 0.2),
    ("17230", "Manufacture of paper stationery", 0.3),
    ("17290", "Manufacture of other articles of paper and paperboard", 0.2),
    ("18110", "Printing of newspapers", 0.2),
    ("18121", "Manufacture of printed labels", 0.3),
    ("18129", "Printing (other than printing of newspapers)", 1.5),  # High-value for packaging
    ("18130", "Pre-press and pre-media services", 0.3),
    ("18140", "Binding and related services", 0.3),
    ("22110", "Manufacture of rubber tyres and tubes", 0.1),
    ("22220", "Manufacture of plastic packing goods", 0.5),  # High-value
    ("22290", "Manufacture of other plastic products", 0.8),  # High-value
    ("25990", "Manufacture of other fabricated metal products", 0.4),
    ("27900", "Manufacture of other electrical equipment", 0.3),
    ("32990", "Other manufacturing not elsewhere classified", 0.6),
    ("33190", "Repair of other equipment", 0.3),

    # Wholesale & Retail (45-47) - 15% of UK businesses
    ("45111", "Sale of new cars and light motor vehicles", 0.8),
    ("45200", "Maintenance and repair of motor vehicles", 1.5),
    ("46110", "Agents selling agricultural raw materials", 0.3),
    ("46120", "Agents involved in sale of fuels, ores", 0.2),
    ("46180", "Agents specialising in sale of other products", 0.4),  # High-value
    ("46190", "Agents involved in sale of variety of goods", 0.5),
    ("46410", "Wholesale of textiles", 0.4),
    ("46499", "Wholesale of other household goods", 0.6),
    ("46760", "Wholesale of other intermediate products", 0.4),
    ("46900", "Non-specialised wholesale trade", 0.8),
    ("47110", "Retail sale in non-specialised stores with food", 1.2),
    ("47620", "Retail sale of newspapers and stationery", 0.5),
    ("47710", "Retail sale of clothing in specialised stores", 0.8),
    ("47910", "Retail sale via mail order or internet", 1.5),  # Growing sector
    ("47990", "Other retail sale not in stores", 0.8),

    # Professional Services (69-75) - 18% of UK businesses
    ("69102", "Accounting, and auditing activities", 1.5),
    ("69109", "Other accounting activities", 0.8),
    ("69201", "Financial accounts auditing activities", 0.3),
    ("70100", "Activities of head offices", 1.0),
    ("70210", "Public relations activities", 0.5),
    ("70229", "Management consultancy activities", 2.5),  # Very common
    ("71111", "Architectural activities", 0.8),
    ("71121", "Engineering design activities for buildings", 0.6),
    ("71122", "Engineering related technical consulting", 0.5),
    ("71200", "Technical testing and analysis", 0.4),
    ("72190", "Other research and experimental development", 0.3),
    ("73110", "Advertising agencies", 0.8),
    ("73120", "Media representation", 0.4),
    ("74100", "Specialised design activities", 1.0),  # High-value for packaging
    ("74209", "Other photographic activities", 0.5),
    ("74909", "Other professional, scientific and technical activities", 0.6),

    # Administrative Services (77-82) - 10% of UK businesses
    ("77110", "Renting and leasing of cars", 0.4),
    ("78109", "Other activities of employment agencies", 0.6),
    ("78200", "Temporary employment agency activities", 0.5),
    ("79110", "Travel agency activities", 0.4),
    ("80100", "Private security activities", 0.3),
    ("80200", "Security systems service activities", 0.2),
    ("81100", "Combined facilities support activities", 0.4),
    ("81210", "General cleaning of buildings", 1.0),
    ("81300", "Landscape service activities", 0.6),
    ("82110", "Combined office administrative activities", 0.8),
    ("82190", "Photocopying and document activities", 0.3),
    ("82200", "Activities of call centres", 0.3),
    ("82920", "Packaging activities", 0.4),  # High-value
    ("82990", "Other business support service activities", 1.5),  # Very common, high-value

    # Construction (41-43) - 12% of UK businesses
    ("41100", "Development of building projects", 0.8),
    ("41201", "Construction of commercial buildings", 0.6),
    ("41202", "Construction of domestic buildings", 1.0),
    ("42110", "Construction of roads and motorways", 0.2),
    ("42210", "Construction of utility projects for fluids", 0.3),
    ("42990", "Construction of other civil engineering projects", 0.4),
    ("43110", "Demolition", 0.2),
    ("43120", "Site preparation", 0.3),
    ("43210", "Electrical installation", 1.5),
    ("43220", "Plumbing, heat and air-conditioning", 1.2),
    ("43290", "Other construction installation", 0.8),
    ("43310", "Plastering", 0.4),
    ("43320", "Joinery installation", 0.6),
    ("43330", "Floor and wall covering", 0.4),
    ("43341", "Painting", 0.8),
    ("43390", "Other building completion and finishing", 0.6),
    ("43999", "Other specialised construction activities", 0.8),

    # Information & Communication (58-63) - 6% of UK businesses
    ("58110", "Book publishing", 0.3),
    ("58141", "Publishing of learned journals", 0.2),
    ("58142", "Publishing of consumer journals", 0.3),
    ("58190", "Other publishing activities", 0.6),  # High-value
    ("59112", "Video production activities", 0.4),
    ("59200", "Sound recording and music publishing", 0.3),
    ("62011", "Ready-made interactive software development", 0.8),
    ("62012", "Business and domestic software development", 1.5),
    ("62020", "Information technology consultancy activities", 2.0),
    ("62090", "Other information technology service activities", 0.8),
    ("63110", "Data processing and hosting", 0.5),
    ("63120", "Web portals", 0.4),
    ("63990", "Other information service activities", 0.3),

    # Other Services (94-96) - 5% of UK businesses
    ("94110", "Activities of business and employers organisations", 0.3),
    ("94120", "Activities of professional membership organisations", 0.4),
    ("94910", "Activities of religious organisations", 0.3),
    ("94990", "Activities of other membership organisations", 0.5),
    ("96020", "Hairdressing and other beauty treatment", 1.5),
    ("96040", "Physical well-being activities", 0.4),
    ("96090", "Other personal service activities", 0.8),

    # Accommodation & Food (55-56) - 6% of UK businesses
    ("55100", "Hotels and similar accommodation", 0.5),
    ("55201", "Holiday centres and villages", 0.2),
    ("55209", "Other holiday and short-stay accommodation", 0.3),
    ("55900", "Other accommodation", 0.3),
    ("56101", "Licensed restaurants", 1.0),
    ("56102", "Unlicensed restaurants and cafes", 1.2),
    ("56103", "Take-away food shops and mobile food stands", 0.8),
    ("56210", "Event catering activities", 0.5),
    ("56302", "Public houses and bars", 0.8),

    # Real Estate (68) - 4% of UK businesses
    ("68100", "Buying and selling of own real estate", 1.0),
    ("68201", "Renting and operating of Housing Association real estate", 0.3),
    ("68209", "Other renting of own or leased real estate", 1.5),
    ("68310", "Real estate agencies", 0.8),
    ("68320", "Management of real estate on a fee or contract basis", 0.6),

    # Health & Social (86-88) - 4% of UK businesses
    ("86101", "Hospital activities", 0.2),
    ("86210", "General medical practice activities", 0.5),
    ("86220", "Specialist medical practice activities", 0.4),
    ("86230", "Dental practice activities", 0.4),
    ("86900", "Other human health activities", 0.8),
    ("87100", "Residential nursing care activities", 0.3),
    ("88100", "Social work activities without accommodation", 0.4),

    # Finance & Insurance (64-66) - 3% of UK businesses
    ("64110", "Central banking", 0.05),
    ("64191", "Banks", 0.1),
    ("64209", "Activities of other holding companies", 1.0),
    ("64301", "Activities of investment trusts", 0.2),
    ("64302", "Activities of unit trusts", 0.1),
    ("64921", "Credit granting by non-deposit taking finance houses", 0.2),
    ("64999", "Other financial service activities", 0.5),
    ("65120", "Non-life insurance", 0.2),
    ("66120", "Security and commodity contracts dealing", 0.2),
    ("66190", "Other activities auxiliary to financial services", 0.4),

    # Arts, Entertainment & Recreation (90-93) - 3% of UK businesses
    ("90010", "Performing arts", 0.5),
    ("90020", "Support activities to performing arts", 0.3),
    ("90030", "Artistic creation", 0.6),
    ("91011", "Library activities", 0.1),
    ("91020", "Museum activities", 0.1),
    ("93110", "Operation of sports facilities", 0.4),
    ("93120", "Activities of sport clubs", 0.3),
    ("93130", "Fitness facilities", 0.5),
    ("93290", "Other amusement and recreation activities", 0.4),

    # Education (85) - 3% of UK businesses
    ("85100", "Pre-primary education", 0.3),
    ("85200", "Primary education", 0.2),
    ("85310", "General secondary education", 0.1),
    ("85320", "Technical and vocational secondary education", 0.2),
    ("85421", "First-degree level higher education", 0.1),
    ("85510", "Sports and recreation education", 0.3),
    ("85520", "Cultural education", 0.4),
    ("85590", "Other education", 0.6),

    # Transport & Storage (49-53) - 3% of UK businesses
    ("49100", "Passenger rail transport", 0.05),
    ("49320", "Taxi operation", 0.8),
    ("49410", "Freight transport by road", 1.0),
    ("49420", "Removal services", 0.4),
    ("50100", "Sea and coastal passenger water transport", 0.05),
    ("51101", "Scheduled passenger air transport", 0.05),
    ("52100", "Warehousing and storage", 0.5),
    ("52290", "Other transportation support activities", 0.3),
    ("53100", "Postal activities under universal service obligation", 0.1),
    ("53201", "Licensed carriers", 0.2),
    ("53202", "Unlicensed carrier activities", 0.3),

    # Agriculture (01-03) - 1.5% of UK businesses
    ("01110", "Growing of cereals", 0.3),
    ("01130", "Growing of vegetables and melons", 0.2),
    ("01210", "Growing of grapes", 0.05),
    ("01410", "Raising of dairy cattle", 0.2),
    ("01420", "Raising of other cattle and buffaloes", 0.2),
    ("01460", "Raising of swine/pigs", 0.1),
    ("01470", "Raising of poultry", 0.1),
    ("01500", "Mixed farming", 0.3),
    ("01610", "Support activities for crop production", 0.2),
    ("01620", "Support activities for animal production", 0.15),

    # International/Other (99) - Holding companies, etc
    ("99999", "Activities of extraterritorial organisations", 0.5),
]

# UK Regions with realistic company distribution
UK_REGIONS = [
    ("London", 22),
    ("South East", 15),
    ("North West", 10),
    ("West Midlands", 8),
    ("Yorkshire", 8),
    ("East of England", 8),
    ("South West", 7),
    ("Scotland", 6),
    ("East Midlands", 5),
    ("Wales", 4),
    ("North East", 3),
    ("Northern Ireland", 3),
    ("Channel Islands", 1),
]

# Postcodes by region (sampling)
REGION_POSTCODES = {
    "London": ["E1", "EC1A", "N1", "NW1", "SE1", "SW1", "W1", "WC1", "E14", "EC2", "N4", "NW3", "SE10"],
    "South East": ["BN1", "CT1", "GU1", "HP1", "KT1", "ME1", "MK1", "OX1", "RG1", "RH1", "SL1", "TN1", "TW1"],
    "North West": ["BB1", "BL1", "CH1", "CW1", "FY1", "L1", "LA1", "M1", "OL1", "PR1", "SK1", "WA1", "WN1"],
    "West Midlands": ["B1", "CV1", "DY1", "ST1", "WS1", "WV1", "HR1", "TF1", "WR1"],
    "Yorkshire": ["BD1", "DN1", "HD1", "HX1", "LS1", "S1", "WF1", "HU1", "YO1"],
    "East of England": ["CB1", "CM1", "CO1", "IP1", "NR1", "PE1", "SS1", "SG1", "LU1"],
    "South West": ["BA1", "BS1", "DT1", "EX1", "GL1", "PL1", "SN1", "SP1", "TA1", "TQ1", "TR1"],
    "Scotland": ["AB1", "DD1", "DG1", "EH1", "FK1", "G1", "IV1", "KA1", "KY1", "ML1", "PA1", "PH1"],
    "East Midlands": ["DE1", "LE1", "LN1", "NG1", "NN1"],
    "Wales": ["CF1", "LL1", "NP1", "SA1", "SY1", "LD1"],
    "North East": ["DH1", "DL1", "NE1", "SR1", "TS1"],
    "Northern Ireland": ["BT1", "BT2", "BT3", "BT4", "BT5", "BT9", "BT12"],
    "Channel Islands": ["JE1", "GY1"],
}

# Realistic postcode area to region mapping
POSTCODE_TO_REGION = {
    "E": "London", "EC": "London", "N": "London", "NW": "London",
    "SE": "London", "SW": "London", "W": "London", "WC": "London",
    "BN": "Brighton", "CT": "Kent", "DA": "Kent", "GU": "Surrey",
    "HP": "Buckinghamshire", "KT": "Surrey", "ME": "Kent", "MK": "Milton Keynes",
    "OX": "Oxford", "RG": "Reading", "RH": "Surrey", "SL": "Berkshire",
    "TN": "Kent", "TW": "Middlesex", "CB": "Cambridge", "CM": "Chelmsford",
    "CO": "Colchester", "IP": "Ipswich", "NR": "Norwich", "PE": "Peterborough",
    "SS": "Southend", "BB": "Lancashire", "BL": "Bolton", "CA": "Cumbria",
    "CH": "Cheshire", "CW": "Cheshire", "FY": "Blackpool", "L": "Liverpool",
    "LA": "Lancashire", "M": "Manchester", "OL": "Oldham", "PR": "Preston",
    "SK": "Stockport", "WA": "Warrington", "WN": "Wigan", "B": "Birmingham",
    "CV": "Coventry", "DE": "Derby", "DY": "West Midlands", "LE": "Leicester",
    "NG": "Nottingham", "NN": "Northampton", "ST": "Staffordshire",
    "WS": "West Midlands", "WV": "Wolverhampton", "BD": "Bradford",
    "DN": "Doncaster", "HD": "Huddersfield", "HX": "Halifax", "LS": "Leeds",
    "S": "Sheffield", "WF": "Wakefield", "HU": "Hull", "YO": "York",
    "DH": "Durham", "DL": "Darlington", "NE": "Newcastle", "SR": "Sunderland",
    "TS": "Teesside", "BA": "Bath", "BS": "Bristol", "DT": "Dorset",
    "EX": "Exeter", "GL": "Gloucester", "PL": "Plymouth", "SN": "Swindon",
    "SP": "Salisbury", "TA": "Taunton", "TQ": "Torquay", "TR": "Cornwall",
    "AB": "Aberdeen", "DD": "Dundee", "DG": "Dumfries", "EH": "Edinburgh",
    "FK": "Falkirk", "G": "Glasgow", "HS": "Scotland", "IV": "Inverness",
    "KA": "Kilmarnock", "KW": "Scotland", "KY": "Fife", "ML": "Motherwell",
    "PA": "Paisley", "PH": "Perth", "TD": "Scotland", "CF": "Cardiff",
    "LD": "Wales", "LL": "Wales", "NP": "Newport", "SA": "Swansea",
    "SY": "Shrewsbury", "BT": "Belfast", "JE": "Jersey", "GY": "Guernsey",
}

# Company type distribution
COMPANY_TYPES = [
    ("ltd", 85),               # Private Limited Company
    ("private-limited-guarant-nsc", 5),  # Private Limited by Guarantee
    ("llp", 4),                # Limited Liability Partnership
    ("plc", 1),                # Public Limited Company
    ("private-unlimited", 0.5),
    ("other", 4.5),
]

# Company name prefixes and suffixes for generating realistic names
NAME_PREFIXES = [
    "Alpha", "Beta", "Global", "United", "Premier", "Elite", "Pro", "First",
    "Prime", "Dynamic", "Apex", "Summit", "Peak", "Crown", "Royal", "Sterling",
    "Phoenix", "Atlas", "Titan", "Nova", "Quantum", "Matrix", "Nexus", "Vertex",
    "Core", "Tech", "Digital", "Smart", "Cyber", "Data", "Info", "Net", "Cloud",
    "Green", "Eco", "Blue", "Red", "Golden", "Silver", "Diamond", "Crystal",
    "Express", "Direct", "Rapid", "Swift", "Quick", "Fast", "Speedy", "Instant",
    "North", "South", "East", "West", "Central", "Metro", "Urban", "City",
]

NAME_MIDS = [
    "Solutions", "Services", "Systems", "Group", "Industries", "Enterprises",
    "Partners", "Associates", "Consulting", "Logistics", "Properties", "Holdings",
    "Innovations", "Technologies", "Creative", "Design", "Media", "Print",
    "Engineering", "Manufacturing", "Construction", "Trading", "Marketing",
    "Communications", "Management", "Development", "Resources", "Capital",
]

NAME_SUFFIXES = ["Ltd", "Limited", "LLP", "PLC", "Group", "& Co", "UK", "International"]


def generate_company_name(sic_code: str) -> str:
    """Generate a realistic company name based on sector."""
    sector = sic_to_sector(sic_code)

    # Use sector-specific naming patterns
    name_style = random.choice(["prefix_mid", "prefix_suffix", "full_name", "initials"])

    if name_style == "prefix_mid":
        return f"{random.choice(NAME_PREFIXES)} {random.choice(NAME_MIDS)}"
    elif name_style == "prefix_suffix":
        return f"{random.choice(NAME_PREFIXES)} {random.choice(NAME_SUFFIXES)}"
    elif name_style == "full_name":
        # Use British surnames
        surnames = ["Smith", "Jones", "Williams", "Brown", "Taylor", "Davies", "Wilson",
                   "Evans", "Thomas", "Roberts", "Johnson", "Walker", "Wright", "Thompson"]
        return f"{random.choice(surnames)} & {random.choice(surnames)} {random.choice(NAME_MIDS)}"
    else:
        # Initials
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        return f"{''.join(random.sample(letters, 3))} {random.choice(NAME_MIDS)}"


def generate_company_number() -> str:
    """Generate a realistic Companies House company number."""
    # UK company numbers are 8 characters
    # Can be: 0-9 (England & Wales), SC (Scotland), NI (N Ireland), NC (obsolete)
    prefix_type = random.choices(
        ["numeric", "SC", "NI", "FC"],
        weights=[85, 8, 5, 2]
    )[0]

    if prefix_type == "numeric":
        return str(random.randint(1000000, 15999999)).zfill(8)
    elif prefix_type == "SC":
        return f"SC{random.randint(100000, 999999)}"
    elif prefix_type == "NI":
        return f"NI{random.randint(100000, 999999)}"
    else:
        return f"FC{random.randint(100000, 999999)}"


def generate_incorporation_date() -> datetime:
    """Generate a realistic incorporation date."""
    # Company age distribution (years):
    # 0-5: 35%, 5-10: 25%, 10-20: 20%, 20-40: 15%, 40+: 5%
    age_years = random.choices(
        [random.uniform(0, 5), random.uniform(5, 10), random.uniform(10, 20),
         random.uniform(20, 40), random.uniform(40, 100)],
        weights=[35, 25, 20, 15, 5]
    )[0]

    incorporation_date = datetime.now() - timedelta(days=int(age_years * 365.25))
    return incorporation_date


def generate_officer_count(company_age: float, company_type: str) -> int:
    """Generate realistic officer count based on company characteristics."""
    # Base count depends on company type
    if company_type == "plc":
        base = random.randint(3, 20)
    elif company_type == "llp":
        base = random.randint(2, 8)
    else:
        base = random.randint(1, 5)

    # Older companies tend to have more historical officers
    age_factor = 1 + (company_age / 30)  # More officers as company ages

    return max(1, int(base * age_factor))


def generate_filing_count(company_age: float) -> int:
    """Generate realistic filing count based on company age."""
    # Companies typically file 2-4 documents per year
    base_filings = max(1, int(company_age * random.uniform(2, 4)))

    # Add some variation
    return max(1, base_filings + random.randint(-3, 5))


def generate_accounts_type(company_age: float, officer_count: int) -> str:
    """Generate accounts type based on company size."""
    # Distribution based on UK data
    # Smaller/younger companies more likely to be dormant or micro
    if officer_count <= 1:
        return random.choices(
            ["dormant", "micro-entity", "total-exemption-full", "total-exemption-small"],
            weights=[10, 40, 35, 15]
        )[0]
    elif officer_count <= 3:
        return random.choices(
            ["micro-entity", "total-exemption-full", "total-exemption-small", "small"],
            weights=[30, 40, 20, 10]
        )[0]
    else:
        return random.choices(
            ["total-exemption-full", "small", "medium", "full"],
            weights=[40, 35, 15, 10]
        )[0]


def has_website(sic_code: str, company_age: float) -> tuple:
    """Determine if company has website and its characteristics."""
    sector = sic_to_sector(sic_code)

    # Base rate varies by sector
    sector_rates = {
        "Information & Communication": 0.90,
        "Professional Services": 0.80,
        "Wholesale & Retail": 0.75,
        "Manufacturing": 0.70,
        "Administrative Services": 0.65,
        "Real Estate": 0.60,
        "Construction": 0.55,
        "Accommodation & Food": 0.65,
        "Health": 0.60,
        "Finance": 0.70,
        "Arts & Entertainment": 0.70,
        "Education": 0.65,
        "Transport & Storage": 0.50,
        "Agriculture": 0.40,
        "Other Services": 0.55,
    }

    base_rate = sector_rates.get(sector, 0.60)

    # Younger companies more likely to have modern web presence
    age_factor = 1.0 if company_age < 10 else 0.9 if company_age < 20 else 0.8

    has_site = random.random() < (base_rate * age_factor)

    if has_site:
        # HTTPS adoption (increasing over time, younger companies more likely)
        https_rate = 0.85 if company_age < 5 else 0.70 if company_age < 15 else 0.55
        has_https = random.random() < https_rate
        return True, has_https

    return False, False


def generate_synthetic_companies(n: int = 500, seed: int = 42) -> pd.DataFrame:
    """Generate synthetic Companies House data representing UK business population."""
    random.seed(seed)
    np.random.seed(seed)

    print(f"Generating {n} synthetic UK companies...")

    # Calculate SIC code weights
    sic_codes, sic_desc, sic_weights = zip(*UK_SIC_CODES)
    total_weight = sum(sic_weights)
    normalized_weights = [w/total_weight for w in sic_weights]

    # Calculate region weights
    regions, region_weights = zip(*UK_REGIONS)

    companies = []

    for i in range(n):
        # Select SIC code
        sic_code = random.choices(sic_codes, weights=normalized_weights)[0]
        industry_sector = sic_to_sector(sic_code)

        # Select region and postcode
        region_name = random.choices(regions, weights=region_weights)[0]
        postcode_area = random.choice(REGION_POSTCODES.get(region_name, ["XX1"]))
        postcode = f"{postcode_area} {random.randint(1, 9)}{random.choice('ABCDEFGHJKLMNPRSTUVWXY')}{random.choice('ABCDEFGHJKLMNPRSTUVWXY')}"

        # Derive region from postcode for scoring
        pc_prefix = ''.join([c for c in postcode_area if c.isalpha()])
        derived_region = POSTCODE_TO_REGION.get(pc_prefix, region_name)

        # Select company type
        types, type_weights = zip(*COMPANY_TYPES)
        company_type = random.choices(types, weights=type_weights)[0]

        # Generate dates
        incorporation_date = generate_incorporation_date()
        company_age = (datetime.now() - incorporation_date).days / 365.25

        # Generate size indicators
        officer_count = generate_officer_count(company_age, company_type)
        active_officers = max(1, int(officer_count * random.uniform(0.3, 0.8)))
        director_count = min(active_officers, random.randint(1, max(1, active_officers)))
        secretary_count = 1 if random.random() < 0.3 else 0

        filing_count = generate_filing_count(company_age)
        accounts_type = generate_accounts_type(company_age, officer_count)

        # Has charges (indicates credit activity)
        has_charges = random.random() < (0.1 + (company_age / 100) * 0.3)
        charge_count = random.randint(1, 10) if has_charges else 0

        # Web presence
        has_site, has_https = has_website(sic_code, company_age)

        # Company status (most are active)
        status = random.choices(
            ["active", "dissolved", "liquidation", "administration"],
            weights=[92, 5, 2, 1]
        )[0]

        company = {
            "company_name": generate_company_name(sic_code),
            "company_number": generate_company_number(),
            "company_type": company_type,
            "company_status": status,
            "sic_codes": sic_code,
            "industry_sector": industry_sector,
            "incorporation_date": incorporation_date.strftime("%Y-%m-%d"),
            "company_age_years": round(company_age, 1),
            "postcode": postcode,
            "region": derived_region,
            "accounts_type": accounts_type,
            "officer_count": officer_count,
            "active_officer_count": active_officers,
            "director_count": director_count,
            "secretary_count": secretary_count,
            "filing_count": filing_count,
            "recent_filing_days": random.randint(10, 400),
            "annual_accounts_count": min(int(company_age), filing_count // 3),
            "has_charges": has_charges,
            "charge_count": charge_count,
            "psc_count": random.randint(1, 4),
            "has_website": has_site,
            "has_https": has_https,
        }

        companies.append(company)

    df = pd.DataFrame(companies)

    # Print statistics
    print(f"\n=== Generated Data Statistics ===")
    print(f"Total companies: {len(df)}")
    print(f"Active companies: {(df['company_status'] == 'active').sum()}")
    print(f"\nIndustry distribution:")
    print(df['industry_sector'].value_counts().head(10))
    print(f"\nRegion distribution:")
    print(df['region'].value_counts().head(10))
    print(f"\nCompany age statistics:")
    print(f"  Mean: {df['company_age_years'].mean():.1f} years")
    print(f"  Median: {df['company_age_years'].median():.1f} years")
    print(f"  Range: {df['company_age_years'].min():.1f} - {df['company_age_years'].max():.1f} years")
    print(f"\nWeb presence: {df['has_website'].mean():.1%}")
    print(f"HTTPS: {df['has_https'].mean():.1%}")

    return df


def run_prospect_scoring(prospects_df: pd.DataFrame, icp_path: str) -> pd.DataFrame:
    """Run the prospect scorer on the generated data."""
    print("\n=== Running Prospect Scorer ===")

    # Load ICP profile
    icp = ICPProfile.load(icp_path)
    print(f"Loaded ICP profile: {icp.total_customers} customers, {icp.high_value_count} high-value")

    # Initialize scorer
    scorer = ProspectScorer(icp=icp)

    # Filter to active companies only
    active_df = prospects_df[prospects_df['company_status'] == 'active'].copy()
    print(f"Scoring {len(active_df)} active companies...")

    # Score all prospects
    scored_df = scorer.score_batch(active_df)

    return scored_df


def generate_analysis_report(scored_df: pd.DataFrame, icp: ICPProfile, output_path: str):
    """Generate comprehensive analysis report."""
    print("\n=== Generating Analysis Report ===")

    # Calculate statistics
    tier_counts = scored_df['priority_tier'].value_counts()
    total = len(scored_df)

    # Get top 20 prospects
    top_20 = scored_df.head(20)

    # Industry breakdown of top prospects
    top_100 = scored_df.head(100)
    industry_breakdown = top_100['industry_sector'].value_counts()

    # Geographic breakdown
    geo_breakdown = top_100['region'].value_counts().head(15)

    # Score distribution statistics
    score_stats = {
        'mean': scored_df['prospect_score'].mean(),
        'median': scored_df['prospect_score'].median(),
        'std': scored_df['prospect_score'].std(),
        'min': scored_df['prospect_score'].min(),
        'max': scored_df['prospect_score'].max(),
    }

    # Generate markdown report
    report = f"""# Prospect Scoring Analysis Report

**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Total Prospects Scored**: {total}
**ICP Based on**: {icp.total_customers} existing customers ({icp.high_value_count} high-value)

---

## Executive Summary

The prospect scoring system evaluated {total} synthetic UK companies against the Ideal Customer Profile (ICP) derived from existing PackagePro customers. The scoring identified {tier_counts.get('Hot', 0)} hot leads ({tier_counts.get('Hot', 0)/total*100:.1f}%) and {tier_counts.get('Warm', 0)} warm leads ({tier_counts.get('Warm', 0)/total*100:.1f}%) for sales prioritization.

---

## Score Distribution

### Priority Tier Breakdown

| Tier | Count | Percentage | Score Range |
|------|-------|------------|-------------|
| **Hot** | {tier_counts.get('Hot', 0)} | {tier_counts.get('Hot', 0)/total*100:.1f}% | 75+ |
| **Warm** | {tier_counts.get('Warm', 0)} | {tier_counts.get('Warm', 0)/total*100:.1f}% | 60-74 |
| **Cool** | {tier_counts.get('Cool', 0)} | {tier_counts.get('Cool', 0)/total*100:.1f}% | 45-59 |
| **Cold** | {tier_counts.get('Cold', 0)} | {tier_counts.get('Cold', 0)/total*100:.1f}% | <45 |

### Score Statistics

- **Mean Score**: {score_stats['mean']:.1f}
- **Median Score**: {score_stats['median']:.1f}
- **Standard Deviation**: {score_stats['std']:.1f}
- **Range**: {score_stats['min']:.1f} - {score_stats['max']:.1f}

---

## Top 20 Prospects

| Rank | Company | Industry | Region | Score | Tier | Key Reasons |
|------|---------|----------|--------|-------|------|-------------|
"""

    for i, row in top_20.iterrows():
        rank = len(report.split('\n')) - report.split('| Rank |')[0].count('\n') - 2
        reasons = []
        if pd.notna(row.get('reason_industry')):
            reasons.append(row['reason_industry'][:40])
        if pd.notna(row.get('reason_company_age')):
            reasons.append(row['reason_company_age'][:30])
        reason_str = "; ".join(reasons[:2]) if reasons else "Multiple factors"

        report += f"| {rank} | {row['company_name'][:30]} | {row['industry_sector'][:20]} | {row['region'][:15]} | {row['prospect_score']:.1f} | {row['priority_tier']} | {reason_str} |\n"

    report += f"""

---

## Industry Breakdown (Top 100 Prospects)

The top 100 prospects are distributed across the following industries:

| Industry | Count | Percentage |
|----------|-------|------------|
"""

    for industry, count in industry_breakdown.items():
        report += f"| {industry} | {count} | {count/100*100:.1f}% |\n"

    report += f"""

### Key Industry Insights

Based on the ICP analysis, the highest-performing industries are:

1. **Manufacturing** - Particularly printing (SIC 18129), paper products (17230), and plastics (22290)
2. **Administrative Services** - Business support services (82990) and packaging activities (82920)
3. **Wholesale & Retail** - Agents specialising in other products (46180) and non-specialised wholesale (46900)
4. **Professional Services** - Specialised design activities (74100) and technical consulting (71122)

---

## Geographic Breakdown (Top 100 Prospects)

| Region | Count | Percentage |
|--------|-------|------------|
"""

    for region, count in geo_breakdown.items():
        report += f"| {region} | {count} | {count/100*100:.1f}% |\n"

    report += f"""

### Geographic Insights

The ICP indicates strongest customer potential in:
- **Gloucestershire** and **Derbyshire** (highest lift ratios)
- **Buckinghamshire** and **Leeds** (strong customer presence)
- **London** (high volume opportunity)

---

## Scoring Component Analysis

The prospect score is composed of five weighted components:

| Component | Weight | Description |
|-----------|--------|-------------|
| Industry Match | 30% | SIC code and sector alignment with high-value customers |
| Company Age | 20% | Optimal range: {icp.company_age.optimal_min_years:.0f}-{icp.company_age.optimal_max_years:.0f} years |
| Company Size | 25% | Officers ({icp.company_size.optimal_officer_count_min}-{icp.company_size.optimal_officer_count_max}) and filings ({icp.company_size.optimal_filing_count_min}-{icp.company_size.optimal_filing_count_max}) |
| Geography | 10% | Regional performance based on existing customer success |
| Web Presence | 15% | Website and HTTPS adoption indicators |

---

## Recommendations

### Immediate Actions (Hot Leads)

1. **Prioritize outreach** to the {tier_counts.get('Hot', 0)} hot leads identified
2. **Focus on Manufacturing** prospects, especially printing and packaging-adjacent industries
3. **Target established companies** in the 7-29 year age range
4. **Leverage regional presence** in high-performing areas (Gloucestershire, Leeds, Buckinghamshire)

### Medium-Term Strategy (Warm Leads)

1. **Nurture the {tier_counts.get('Warm', 0)} warm leads** with targeted content marketing
2. **Expand presence** in underrepresented high-potential regions
3. **Develop industry-specific** value propositions for top sectors

### Data Quality Notes

- This analysis used synthetic data representing the UK business population
- Real Companies House data would provide more accurate company-specific insights
- Consider enriching prospect data with additional indicators (company accounts, news, web presence)

---

## Technical Details

### ICP Model Performance

- **Cross-validation AUC**: {icp.model_metrics.get('cv_auc_mean', 'N/A'):.3f}
- **Feature Count**: {icp.model_metrics.get('n_features', 'N/A')}
- **Training Samples**: {icp.model_metrics.get('n_samples', 'N/A')}
- **Positive Rate**: {icp.model_metrics.get('positive_rate', 'N/A'):.1%}

### Top Predictive Features (from ICP)

"""

    # Sort features by weight
    sorted_features = sorted(icp.feature_weights.items(), key=lambda x: x[1], reverse=True)[:10]
    for feat, weight in sorted_features:
        report += f"- **{feat}**: {weight:.1f}%\n"

    report += f"""

---

*Report generated by PackagePro Prospect Scoring System v1.0*
"""

    # Write report
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        f.write(report)

    print(f"Analysis report saved to: {output_path}")

    return report


def main():
    """Main execution function."""
    print("=" * 70)
    print("PackagePro PROSPECT SCORER TEST")
    print("=" * 70)

    # Paths
    base_dir = Path(__file__).resolve().parent.parent
    icp_path = base_dir / "models" / "prospect_scorer" / "icp_profile.json"
    prospects_output = base_dir / "data" / "prospects" / "test_prospects.csv"
    scored_output = base_dir / "data" / "prospects" / "scored_prospects.csv"
    analysis_output = base_dir / "outputs" / "prospect_analysis.md"

    # Check for Companies House bulk data
    ch_data_paths = [
        base_dir / "data" / "companies_house",
        base_dir / "data" / "bulk_companies",
        Path.home() / "Downloads" / "BasicCompanyData",
    ]

    ch_data_found = False
    for path in ch_data_paths:
        if path.exists():
            print(f"Companies House bulk data found at: {path}")
            ch_data_found = True
            break

    if not ch_data_found:
        print("\nNo Companies House bulk data found.")
        print("Creating synthetic test dataset representing UK business population...")

    # Step 1: Generate synthetic data
    prospects_df = generate_synthetic_companies(n=500, seed=42)

    # Save test data
    prospects_output.parent.mkdir(parents=True, exist_ok=True)
    prospects_df.to_csv(prospects_output, index=False)
    print(f"\nTest data saved to: {prospects_output}")

    # Step 2: Run prospect scoring
    if not icp_path.exists():
        print(f"\nError: ICP profile not found at {icp_path}")
        print("Please run: python prospect_scorer.py build-icp")
        return

    scored_df = run_prospect_scoring(prospects_df, str(icp_path))

    # Save scored results
    scored_df.to_csv(scored_output, index=False)
    print(f"Scored prospects saved to: {scored_output}")

    # Step 3: Generate analysis report
    icp = ICPProfile.load(str(icp_path))
    generate_analysis_report(scored_df, icp, str(analysis_output))

    # Print summary
    print("\n" + "=" * 70)
    print("TEST COMPLETE - SUMMARY")
    print("=" * 70)

    tier_counts = scored_df['priority_tier'].value_counts()
    print(f"\nTotal prospects scored: {len(scored_df)}")
    print(f"\nPriority Tier Distribution:")
    print(f"  Hot (75+):   {tier_counts.get('Hot', 0):4d} ({tier_counts.get('Hot', 0)/len(scored_df)*100:.1f}%)")
    print(f"  Warm (60-74): {tier_counts.get('Warm', 0):4d} ({tier_counts.get('Warm', 0)/len(scored_df)*100:.1f}%)")
    print(f"  Cool (45-59): {tier_counts.get('Cool', 0):4d} ({tier_counts.get('Cool', 0)/len(scored_df)*100:.1f}%)")
    print(f"  Cold (<45):  {tier_counts.get('Cold', 0):4d} ({tier_counts.get('Cold', 0)/len(scored_df)*100:.1f}%)")

    print(f"\nTop 5 Prospects:")
    for i, row in scored_df.head(5).iterrows():
        print(f"  {row['company_name'][:35]:35s} | {row['industry_sector'][:20]:20s} | Score: {row['prospect_score']:.1f}")

    print(f"\nOutput Files:")
    print(f"  Test Data:     {prospects_output}")
    print(f"  Scored Data:   {scored_output}")
    print(f"  Analysis:      {analysis_output}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
