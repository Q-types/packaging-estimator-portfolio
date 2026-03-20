"""
Extract company names from PackagePro legacy Excel file names.

File naming patterns observed in PackagePro legacy data:
    1. ID DATE COMPANY PRODUCT.xlsx        - most common
    2. ID A/B DATE COMPANY PRODUCT.xlsx    - versioned estimates (A, B, C suffix)
    3. ID COMPANY.xlsx                     - no date
    4. ID DATE COMPANY.xlsx                - no product description

Company names are typically:
    - Personal names: FIRSTNAME LASTNAME (e.g., "TERRY SIMMONDS", "ANDY HALL")
    - Business names: 1-3 words, often ending in LTD/LIMITED/PACKAGING/PRINT etc.

Product keywords that mark the END of company name:
    - Packaging: BOX, BOXES, TRAY, TRAYS, BINDER, BINDERS, SLIPCASE, SLIPCASES
    - Signage: SIGN, SIGNS, PANEL, PANELS, DISPLAY, STICKER
    - Labels: LABEL, LABELS, TAPE
    - Materials: POLYCARB, PVC, FOAM, FLUTE, RIGID
    - Sizes: A3, A4, A5, A6, B5
    - Quantities: OR followed by number, TO followed by number
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class FilenameMetadata:
    """Extracted metadata from a PackagePro estimate filename."""
    estimate_id: Optional[str] = None
    version: Optional[str] = None  # A, B, C etc.
    date: Optional[datetime] = None
    date_str: Optional[str] = None  # ISO format
    company_name: Optional[str] = None
    product_description: Optional[str] = None
    raw_filename: str = ""
    parse_confidence: float = 0.0
    parse_notes: list = None

    def __post_init__(self):
        if self.parse_notes is None:
            self.parse_notes = []


# Product keywords that mark the START of product description (end of company name)
# These are words that would not appear in a company name
PRODUCT_BOUNDARY_PATTERNS = [
    # Size indicators (A4, A5, etc.) - but not at start of name
    r"\bA[2-6]\b",
    r"\bB[4-5]\b",

    # Product types (strongest signals)
    r"\bBINDER(?:S)?\b",
    r"\bBOX(?:ES)?\b",
    r"\bTRAY(?:S)?\b",
    r"\bSLIPCASE(?:S)?\b",
    r"\bFOLDER(?:S)?\b",
    r"\bCOVER(?:S)?\b",
    r"\bJACKET(?:S)?\b",
    r"\bPANEL(?:S)?\b",
    r"\bSIGN(?:S)?\b",
    r"\bSTICKER(?:S)?\b",
    r"\bLABEL(?:S)?\b",
    r"\bTAPE\b",
    r"\bBAG(?:S)?\b",
    r"\bPOSTER(?:S)?\b",
    r"\bCARD(?:S)?\b",
    r"\bMENUSTAND(?:S)?\b",
    r"\bDISPLAY\b",
    r"\bHANGER(?:S)?\b",
    r"\bMEASURE(?:S)?\b",
    r"\bTOPPER(?:S)?\b",  # CAR TOPPERS
    r"\bVISOR(?:S)?\b",  # VISORS
    r"\bRAC\s+APPROVED\b",  # RAC APPROVED certification
    r"\bDEALER\b",  # DEALER products
    r"\bWARRANTY\b",  # WARRANTY products

    # Material/construction terms
    r"\bPOB\b",  # Paper Over Board
    r"\bRIGID\b",
    r"\bFOAM\b",
    r"\bPVC\b",
    r"\bPOLYCARB\b",
    r"\bFLUTE\b",  # B FLUTE, E FLUTE etc.
    r"\b[BEF]\s+FLUTE\b",
    r"\bCAKE\b",  # CAKE BOXES

    # Quantity patterns in description
    r"\b\d+\s*(?:OR|TO)\s*\d+\b",  # "1000 OR 2000", "50-100"
    r"\b\d{3,}(?:xlsx)?\b",  # Quantities like 1000, 5000 (with typo xlsx)

    # Process/spec terms
    r"\bPROOF\b",
    r"\bPRODUCTION\b",
    r"\bTRADE\s+PRICES?\b",
    r"\bWRAP\s*AROUND\b",
    r"\bWINDOW\b",
    r"\bSHOP\b",  # SHOP SIGNS
    r"\bOIL\b",  # OIL BAGS
    r"\bPRINTED\b",  # PRINTED PLYWOOD, PRINTED SHEETS etc.
    r"\bPLYWOOD\b",  # PLYWOOD PANELS
    r"\bSHIPPING\b",  # SHIPPING BOXES
    r"\b\d+\s+SHEETS?\b",  # 51 SHEETS, 100 SHEET
    r"\bSINGLE\b",  # SINGLE LECTERN etc.
    r"\bLECTERN\b",  # LECTERN HEADER
    r"\bHEADER(?:S)?\b",  # HEADER, HEADERS
    r"\bFREE\s+ISSUE\b",  # FREE ISSUE materials
    r"\bCAD\s+CUT\b",  # CAD CUT shapes
    r"\bHEXAGONAL\b",  # HEXAGONAL SHAPES
    r"\b\d+\s*MM\b",  # Dimensions like "455MM"
    r"\bSETS?\s+OF\b",  # SETS OF, SET OF
    r"\b\d+\s+SETS?\b",  # 2 SETS, 3 SET
    r"\bPIECE\b",  # 2 PIECE BASE
    r"\b\d+\s+PIECE\b",  # 2 PIECE
    r"\bGENERIC\b",  # GENERIC PRICING

    # Miscellaneous product markers
    r"\bMUD\s*&\s*BLOOM\b",  # Brand/product line
]

# Compile product boundary patterns
PRODUCT_BOUNDARY_RE = re.compile(
    "|".join(f"({p})" for p in PRODUCT_BOUNDARY_PATTERNS),
    re.IGNORECASE
)

# Known company name suffixes (helps identify company names)
# These are TERMINAL suffixes - they mark the END of a company name
COMPANY_TERMINAL_SUFFIXES = [
    r"\bLTD\.?$",
    r"\bLIMITED$",
    r"\bPLC$",
    r"\bLLP$",
    r"\bINC\.?$",
]

# These suffixes can appear in company names but don't necessarily end them
COMPANY_INTERIOR_SUFFIXES = [
    r"\bGROUP\b",
    r"\bPACKAGING\b",
    r"\bPRINT(?:ING|ERS?)?\b",
    r"\bSERVICES\b",
    r"\bDIRECT\b",
]

# Words that commonly appear as the SECOND word in a two-word company name
# e.g., "RIGHT SIGNS", "BINDERS PLUS", "FOAM ENGINEERS", "BOX AND SEAL"
COMPANY_NAME_CONTINUATIONS = {
    "SIGNS", "PLUS", "ENGINEERS", "SEAL", "AND", "MEDIA", "CREATIVE",
    "DESIGN", "SOLUTIONS", "SYSTEMS", "GRAPHICS", "UK", "INTERNATIONAL",
    "EUROPE", "GLOBAL", "DIGITAL", "TECH", "PRODUCTS", "HOLDINGS",
}

COMPANY_TERMINAL_RE = re.compile(
    "|".join(f"({p})" for p in COMPANY_TERMINAL_SUFFIXES),
    re.IGNORECASE
)

COMPANY_SUFFIX_RE = re.compile(
    "|".join(f"({p})" for p in COMPANY_TERMINAL_SUFFIXES + COMPANY_INTERIOR_SUFFIXES),
    re.IGNORECASE
)

# Common first names for detecting personal name patterns (FIRSTNAME LASTNAME)
COMMON_FIRST_NAMES = {
    "ANDY", "ANDREW", "CHRIS", "CHRISTOPHER", "DAVE", "DAVID", "GARY", "GEORGE",
    "HENRY", "JAMES", "JOHN", "MARK", "MARTIN", "MICHAEL", "MIKE", "NICK",
    "PAUL", "PETER", "PHIL", "PHILIP", "PHILIPS", "PRIYA", "RICHARD", "ROB",
    "ROBERT", "SIMON", "STEVE", "STEVEN", "STUART", "TERRY", "TOM", "TONY",
    "ADAM", "ALAN", "ALEX", "ALEXANDER", "BEN", "BENJAMIN", "BRIAN", "CARL",
    "CHARLIE", "COLIN", "CRAIG", "DAN", "DANIEL", "DEAN", "DEREK", "DOUG",
    "DOUGLAS", "ED", "EDWARD", "ERIC", "FRANK", "FRED", "GRAHAM", "GRANT",
    "GUY", "HARRY", "IAN", "JACK", "JAKE", "JIM", "JOE", "JOSEPH", "JOSH",
    "KEITH", "KEN", "KENNETH", "KEVIN", "LAWRENCE", "LEE", "LEWIS", "LUKE",
    "MALCOLM", "MATT", "MATTHEW", "MAX", "NEIL", "NIGEL", "OLIVER", "OSCAR",
    "PATRICK", "RAY", "RAYMOND", "ROGER", "ROY", "RUSSELL", "RYAN", "SAM",
    "SAMUEL", "SCOTT", "SEAN", "SHAUN", "STEPHEN", "TIM", "TIMOTHY", "TREVOR",
    "VICTOR", "WAYNE", "WILL", "WILLIAM",
    # Female names
    "ALICE", "AMY", "ANGELA", "ANN", "ANNA", "ANNE", "BARBARA", "CAROL",
    "CAROLINE", "CATHERINE", "CHARLOTTE", "CLARE", "CLAIRE", "DEBBIE", "DIANA",
    "DIANE", "DONNA", "DOROTHY", "ELAINE", "ELIZABETH", "EMILY", "EMMA", "EVE",
    "FIONA", "FRANCES", "GRACE", "HANNAH", "HELEN", "JANE", "JANET", "JENNIFER",
    "JENNY", "JESSICA", "JOAN", "JOANNE", "JULIA", "JULIE", "KAREN", "KATE",
    "KATHERINE", "KATIE", "KELLY", "KIM", "LAURA", "LAUREN", "LINDA", "LISA",
    "LOUISE", "LUCY", "LYNN", "MARGARET", "MARIA", "MARIE", "MARY", "MICHELLE",
    "NATALIE", "NICOLA", "OLIVIA", "PAMELA", "PATRICIA", "PAULA", "RACHEL",
    "REBECCA", "ROSE", "RUTH", "SALLY", "SAMANTHA", "SANDRA", "SARAH", "SHARON",
    "SOPHIE", "STEPHANIE", "SUSAN", "SUZANNE", "TINA", "TRACEY", "TRACY",
    "VICTORIA", "WENDY",
}


def _clean_filename(filename: str) -> str:
    """Remove extension and clean up the filename."""
    # Remove xlsx/xls extension (handle typos like "1000xlsx.xlsx")
    name = re.sub(r"\.xlsx?$", "", filename, flags=re.IGNORECASE)
    # Remove embedded xlsx typos (e.g., "5000xlsx" -> "5000")
    name = re.sub(r"xlsx", "", name, flags=re.IGNORECASE)
    # Normalize whitespace
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _parse_date_ddmmyy(date_str: str) -> Optional[datetime]:
    """Parse a 5 or 6-digit DDMMYY or DMMYY/DDMYY date string."""
    if not date_str or not date_str.isdigit():
        return None

    # Handle 5-digit dates: could be DMMYY (day single digit) or DDMYY (month single digit)
    if len(date_str) == 5:
        # Try DDMYY first (month single digit): 22118 -> 22/1/18
        try:
            day = int(date_str[0:2])
            month = int(date_str[2:3])
            year = int(date_str[3:5]) + 2000
            if 1 <= day <= 31 and 1 <= month <= 12:
                return datetime(year, month, day)
        except (ValueError, OverflowError):
            pass

        # Try DMMYY (day single digit): 12318 -> 1/23/18 - invalid month, skip
        # Actually try: 21218 -> 2/12/18 (2nd Dec 2018)
        try:
            day = int(date_str[0:1])
            month = int(date_str[1:3])
            year = int(date_str[3:5]) + 2000
            if 1 <= day <= 31 and 1 <= month <= 12:
                return datetime(year, month, day)
        except (ValueError, OverflowError):
            pass

        return None

    elif len(date_str) != 6:
        return None

    try:
        day = int(date_str[0:2])
        month = int(date_str[2:4])
        year = int(date_str[4:6])
        # Assume 2000s for 2-digit years
        year += 2000 if year < 100 else 0
        return datetime(year, month, day)
    except (ValueError, OverflowError):
        return None


def _is_likely_first_name(word: str) -> bool:
    """Check if a word is likely a first name."""
    return word.upper() in COMMON_FIRST_NAMES


def _find_product_boundary(text: str) -> Optional[int]:
    """Find the position where product description starts."""
    words = text.split()
    if not words:
        return None

    # FIRST: Check for three-word company names like "BOX AND SEAL ..."
    # This must be checked before two-word patterns since "AND" is also a continuation word
    if len(words) >= 3 and words[1].upper() == "AND":
        # Company is first three words (e.g., "BOX AND SEAL")
        company_end = len(words[0]) + 1 + len(words[1]) + 1 + len(words[2])
        if len(words) > 3:
            return company_end + 1
        return None

    # SECOND: Check for two-word company names with continuation
    # e.g., "RIGHT SIGNS ...", "BINDERS PLUS ...", "FOAM ENGINEERS ..."
    if len(words) >= 2 and words[1].upper() in COMPANY_NAME_CONTINUATIONS:
        # Company is likely first two words
        # Find position after second word (including the space)
        company_end = len(words[0]) + 1 + len(words[1])
        if len(words) > 2:
            # There's more content after the company name
            # The boundary is right after company_end (the space after word 2)
            return company_end + 1
        return None

    # Standard boundary detection
    match = PRODUCT_BOUNDARY_RE.search(text)
    if match:
        return match.start()

    return None


def _has_company_suffix(text: str) -> bool:
    """Check if text contains a company name suffix."""
    return bool(COMPANY_SUFFIX_RE.search(text))


def _fix_typos(text: str) -> str:
    """Fix common typos in names from PackagePro data."""
    # Semicolon used instead of letter (likely OCR or keyboard error)
    # L;ING -> LING (not LIING)
    text = re.sub(r";+", "", text)  # Remove semicolons entirely
    # Double letters that look wrong
    text = re.sub(r"([A-Z])\1{2,}", r"\1\1", text, flags=re.IGNORECASE)  # Max 2 of same letter
    return text


def _extract_personal_name(words: list[str]) -> tuple[Optional[str], list[str]]:
    """
    Try to extract a personal name (FIRSTNAME LASTNAME) from the start of words.

    Returns (name, remaining_words) or (None, words) if no personal name found.
    """
    if len(words) < 2:
        return None, words

    # Check if first word looks like a first name
    if _is_likely_first_name(words[0]):
        # Take first name + second word as last name
        lastname = _fix_typos(words[1])

        name = f"{words[0]} {lastname}"
        remaining = words[2:]
        return name, remaining

    return None, words


def _extract_company_with_suffix(words: list[str]) -> tuple[Optional[str], list[str]]:
    """
    Try to extract a company name that ends with LTD/LIMITED/etc.

    Returns (name, remaining_words) or (None, words) if no such pattern found.
    """
    text = " ".join(words)

    # First, look for terminal suffixes (LTD, LIMITED, PLC) which definitively end the name
    terminal_match = COMPANY_TERMINAL_RE.search(text)
    if terminal_match:
        # Find where the suffix ends
        end_pos = terminal_match.end()
        # Find which word this corresponds to
        current_pos = 0
        for i, word in enumerate(words):
            word_end = current_pos + len(word)
            if word_end >= end_pos:
                # Company name is words 0 through i (inclusive)
                company = " ".join(words[:i + 1])
                remaining = words[i + 1:]
                return company, remaining
            current_pos = word_end + 1  # +1 for space

    # If no terminal suffix, only match if there's an interior suffix at the very end
    # AND no product boundary pattern follows it
    if len(words) >= 1:
        # Check if an interior suffix is at the end of the text
        for suffix_pattern in COMPANY_INTERIOR_SUFFIXES:
            pattern = suffix_pattern.replace(r"\b", "") + r"\s*$"
            if re.search(pattern, text, re.IGNORECASE):
                # The entire remaining text is the company name
                return text.strip(), []

    return None, words


def extract_company_from_filename(filename: str) -> FilenameMetadata:
    """
    Extract company name and metadata from a PackagePro estimate filename.

    Handles these patterns:
    - ID DATE COMPANY PRODUCT.xlsx
    - ID A/B DATE COMPANY PRODUCT.xlsx (versioned)
    - ID COMPANY.xlsx (no date)
    - ID DATE COMPANY.xlsx (no product)

    Args:
        filename: The Excel filename (with or without path)

    Returns:
        FilenameMetadata with extracted fields and confidence score
    """
    result = FilenameMetadata(raw_filename=filename)

    # Extract just the filename if path is included
    if "/" in filename or "\\" in filename:
        filename = filename.replace("\\", "/").split("/")[-1]

    # Clean filename
    name = _clean_filename(filename)
    if not name:
        result.parse_notes.append("Empty filename after cleaning")
        return result

    # Split into parts
    parts = name.split()
    if not parts:
        result.parse_notes.append("No parts after splitting")
        return result

    idx = 0  # Current position in parts

    # Step 1: Extract estimate ID (leading numeric)
    if parts[idx].isdigit():
        result.estimate_id = parts[idx]
        idx += 1
        result.parse_confidence += 0.2
    else:
        result.parse_notes.append("No numeric estimate ID found")

    if idx >= len(parts):
        return result

    # Step 2: Check for version suffix (A, B, C)
    if len(parts[idx]) == 1 and parts[idx].upper() in "ABCDEFGH":
        result.version = parts[idx].upper()
        idx += 1
        result.parse_confidence += 0.1

    if idx >= len(parts):
        return result

    # Step 3: Check for date (5-6 digits DDMMYY or DMMYY)
    date_candidate = parts[idx]
    parsed_date = _parse_date_ddmmyy(date_candidate)
    if parsed_date:
        result.date = parsed_date
        result.date_str = parsed_date.isoformat()[:10]
        idx += 1
        result.parse_confidence += 0.2
    else:
        result.parse_notes.append(f"No date found at position {idx}")

    if idx >= len(parts):
        return result

    # Step 3.5: Skip separator dash if present (e.g., "50143 150524 - ROBERT WELCH...")
    if parts[idx] == "-":
        idx += 1
        if idx >= len(parts):
            return result

    # Step 4: Extract company name and product description
    remaining = parts[idx:]
    remaining_text = " ".join(remaining)

    # Pre-check: Look for "X & Y" company name pattern (e.g., "BOXES & PACKAGING")
    # These should be treated as company names, not split at the "&"
    ampersand_company_match = re.match(
        r"^([A-Z]+)\s*&\s*([A-Z]+(?:\s+(?:LTD|LIMITED|PLC|LLP|SERVICES|GROUP))?)\b",
        remaining_text,
        re.IGNORECASE
    )
    if ampersand_company_match:
        company_candidate = ampersand_company_match.group(0).strip()
        # Check if what follows looks like a product description
        after_company = remaining_text[len(company_candidate):].strip()
        if after_company:
            # Check if the next part starts with a number or product keyword
            if re.match(r"^\d+|^[A-Z]\d|^POB|^RIGID|^FOAM", after_company, re.IGNORECASE):
                result.company_name = company_candidate
                result.product_description = after_company
                result.parse_confidence += 0.3
                result.parse_notes.append("Extracted ampersand company pattern")
                # Post-processing and return
                if result.company_name:
                    result.company_name = result.company_name.strip(" .,;:-")
                    result.company_name = _fix_typos(result.company_name)
                result.parse_confidence = min(result.parse_confidence, 1.0)
                return result

    # Strategy 1: Look for product boundary to split company from product
    product_start = _find_product_boundary(remaining_text)

    if product_start is not None and product_start > 0:
        # Split at product boundary
        company_text = remaining_text[:product_start].strip()
        product_text = remaining_text[product_start:].strip()

        # Validate company text
        if company_text:
            result.company_name = company_text
            result.product_description = product_text
            result.parse_confidence += 0.3
            result.parse_notes.append(f"Split at product boundary: '{product_text[:20]}...'")
        else:
            # Product boundary was at start - try other strategies
            product_start = None

    if product_start is None or not result.company_name:
        # Strategy 2: Try to extract company with suffix FIRST (X LTD, Y PACKAGING)
        # This takes priority over personal names to avoid "PRINT" being treated as a name
        company_with_suffix, after_company = _extract_company_with_suffix(remaining)
        if company_with_suffix:
            result.company_name = company_with_suffix
            if after_company:
                result.product_description = " ".join(after_company)
            result.parse_confidence += 0.3
            result.parse_notes.append("Extracted company with suffix")
        else:
            # Strategy 3: Try to extract personal name (FIRSTNAME LASTNAME)
            personal_name, after_name = _extract_personal_name(remaining)
            if personal_name:
                result.company_name = personal_name
                if after_name:
                    result.product_description = " ".join(after_name)
                result.parse_confidence += 0.25
                result.parse_notes.append("Extracted personal name")
            else:
                # Strategy 4: Fallback - first 1-2 words as company
                if len(remaining) == 1:
                    result.company_name = remaining[0]
                    result.parse_confidence += 0.1
                    result.parse_notes.append("Single word company name")
                elif len(remaining) >= 2:
                    # Take first word, or first two if second is short (likely part of name)
                    if len(remaining[1]) <= 3 and not remaining[1].isdigit():
                        result.company_name = f"{remaining[0]} {remaining[1]}"
                        result.product_description = " ".join(remaining[2:]) if len(remaining) > 2 else None
                    else:
                        result.company_name = remaining[0]
                        result.product_description = " ".join(remaining[1:])
                    result.parse_confidence += 0.15
                    result.parse_notes.append("Fallback: used first word(s) as company")

    # Post-processing: Clean up company name
    if result.company_name:
        # Remove trailing/leading punctuation
        result.company_name = result.company_name.strip(" .,;:-")
        # Fix common typos
        result.company_name = _fix_typos(result.company_name)

    # Validate confidence
    result.parse_confidence = min(result.parse_confidence, 1.0)

    return result


def parse_filename(filename: str) -> dict[str, Optional[str]]:
    """
    Parse estimate filename for metadata.

    This is a drop-in replacement for the original _parse_filename function
    but with improved company name extraction.

    Pattern: [ESTIMATE_ID] [VERSION?] [DDMMYY?] [COMPANY] [DESCRIPTION].xlsx

    Returns:
        dict with keys: estimate_id, date, company_name, description
    """
    meta = extract_company_from_filename(filename)

    return {
        "estimate_id": meta.estimate_id,
        "date": meta.date_str,
        "company_name": meta.company_name,
        "description": meta.product_description,
        "version": meta.version,
        "parse_confidence": meta.parse_confidence,
    }


# Convenience function for testing
def test_extraction(filenames: list[str]) -> None:
    """Test the extraction on a list of filenames and print results."""
    print(f"{'Filename':<70} | {'Company':<30} | {'Product':<40} | Conf")
    print("-" * 150)

    for fn in filenames:
        meta = extract_company_from_filename(fn)
        fn_short = fn[:67] + "..." if len(fn) > 70 else fn
        company = (meta.company_name or "")[:27] + "..." if meta.company_name and len(meta.company_name) > 30 else (meta.company_name or "")
        product = (meta.product_description or "")[:37] + "..." if meta.product_description and len(meta.product_description) > 40 else (meta.product_description or "")
        print(f"{fn_short:<70} | {company:<30} | {product:<40} | {meta.parse_confidence:.2f}")


if __name__ == "__main__":
    # Test with the failed extractions
    test_files = [
        "45938 150119 TERRY SIMMONDS TAPE MEASURES.xlsx",
        "46286 A 310519 ANDY HALL POLYCARB LABELS PROOF RUN.xlsx",
        "46286 B 310519 ANDY HALL POLYCARB LABELS PRODUCTION RUN.xlsx",
        "46294 040619 STUART GASKELL.xlsx",
        "47358 130421 SEACOURT A5 POB BINDERS 1000xlsx.xlsx",
        "47358 130921 SEACOURT A5 POB BINDERS 5000 OR 10000 MUD & BLOOM.xlsx",
        "47358 141220 SEACOURT A5 POB BINDERS 5000xlsx.xlsx",
        "47358 160921 SEACOURT A5 POB BINDERS 1000 TO 3000 MUD & BLOOM.xlsx",
        "47573 151220 PAUL BRENNAN SHOP SIGNS.xlsx",
        "47575 151220 PRIYA ANDREAS B FLUTE CAKE BOXES.xlsx",
        "47706 090321 PHILIPS DIRECT TRADE PRICES A4 25MM 4Dxlsx.xlsx",
        "47706 290321 PHILIPS DIRECT TRADE PRICES A4 25MM 4Dxlsx.xlsx",
        "48159 CURTIS PACKAGING .xlsx",
        "48429 040522 GARY WILLIAMS RIGID BOX TRAYS + WRAP AROUND COVERS.xlsx",
        "48431 040522 GARY WILLIAMS RIGID BOX TRAYS + WRAP AROUND COVERS 50-100.xlsx",
        "48716 120922 GARY WILLIAMS RIGID BOX TRAYS + WRAP AROUND COVERS.xlsx",
        "48730 150922 HENRY L;ING 3000 OR 4000 SLIPCASES.xlsx",
        "48928 150124 APT T6 WINDOW DISPLAY PANELS 2 COATS OF BLACK, WHITE & CAD CUT 3M 467 AND RECOVER.xlsx",
        "48981 240123 CHRIS NELSON OIL BAGS.xlsx",
        "48981 240123 PRINT & PACKAGING SERVICES LTD.xlsx",
        # Additional test cases
        "50439 300924 BOXES & PACKAGING 4 PIECE JACKET WITH TRAY.xlsx",
        "50100 150623 ACME A4 BOX.xlsx",
    ]

    test_extraction(test_files)
