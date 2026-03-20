#!/usr/bin/env python3
"""
Refine legacy_extract.json by:
1. Extracting missing company names from file names
2. Removing template/test files
3. Removing records without valid company names

Creates: data/estimates/legacy_extract_refined.json
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.core.filename_extractor import extract_company_from_filename

# Template/test file patterns to exclude
TEMPLATE_PATTERNS = [
    r"SPREADSHEET",
    r"TEMPLATE",
    r"MASTER\s+SPREADSHEET",
    r"^1004\s*-\s*POB",  # Known template file
    r"TEST\s+FILE",
    r"EXAMPLE",
    r"SAMPLE\s+FILE",
]

TEMPLATE_RE = re.compile("|".join(TEMPLATE_PATTERNS), re.IGNORECASE)

# Non-company name patterns (job descriptions, not companies)
NON_COMPANY_PATTERNS = [
    r"^(?:PRINT(?:ED|ING)?|DIGITAL|FOIL|SCREEN)\s+(?:ONLY|SHEETS?|LABELS?|CARDS?)",
    r"^(?:CUT(?:TING)?|CREASE|LAMINATE[D]?|ASSEMBLE[D]?)\s+(?:ONLY|SHEETS?)",
    r"^\d+\s*(?:X|x)\s*\d+",  # Dimensions like "100 x 200"
    r"^(?:A[3-5]|B5)\s+",  # Paper sizes at start
    r"^(?:ONLY)\s+",  # "ONLY" prefix (but not JUST - legitimate company names like JUST DIGITAL)
    r"^(?:POB|PVC)\s+(?!LEICESTER|WIMPOLE|LTD|LIMITED|GROUP)",  # Material codes (but not PP which could be company prefix)
]

NON_COMPANY_RE = re.compile("|".join(NON_COMPANY_PATTERNS), re.IGNORECASE)


def is_template_file(filename: str) -> bool:
    """Check if file is a template/test file."""
    return bool(TEMPLATE_RE.search(filename))


def is_valid_company_name(name: str) -> bool:
    """Check if extracted name is a valid company name."""
    if not name or len(name.strip()) < 2:
        return False

    name = name.strip().upper()

    # Check against non-company patterns
    if NON_COMPANY_RE.match(name):
        return False

    # Must have at least one letter
    if not re.search(r"[A-Z]", name):
        return False

    # Reject if it's just numbers
    if re.match(r"^\d+$", name):
        return False

    return True


def looks_like_job_description(name: str) -> bool:
    """Check if name looks like a job description rather than company name."""
    if not name:
        return False

    name = name.upper()

    # Too long for a company name (> 40 chars)
    if len(name) > 40:
        return True

    # Contains product keywords that indicate job description
    job_keywords = [
        r"\bBINDER(?:S)?\b", r"\bBOX(?:ES)?\b", r"\bTRAY(?:S)?\b",
        r"\bPANEL(?:S)?\b", r"\bSHEET(?:S)?\b", r"\bCOVER(?:S)?\b",
        r"\bCARTON(?:S)?\b", r"\bHEADER(?:S)?\b", r"\bSIGN(?:S)?\b",
        r"\bVISOR(?:S)?\b", r"\bTOPPER(?:S)?\b", r"\bPRICING\b",
        r"\bWRAP\s*AROUND\b", r"\bDIGITAL(?:LY)?\s+PRINT\b",
        r"\bCAD\s+CUT\b", r"\bHEXAGONAL\b", r"\bSHAPE(?:S)?\b",
        r"\bPLAYING\b", r"\bPVC\b", r"\bFOAM\b", r"\bPOB\b",
        r"\d+\s*(?:MM|CM|X|OR)\s*\d+",  # Dimensions
        r"\bPCS\b", r"\bCOPIES\b", r"\bSETS?\b", r"\bVERSIONS?\b",
    ]
    for pattern in job_keywords:
        if re.search(pattern, name):
            return True

    return False


def normalize_company_name(name: str) -> str:
    """Normalize company name for consistency."""
    if not name:
        return ""

    name = name.strip().upper()

    # Fix common typos
    name = name.replace("L;ING", "LING")
    name = name.replace(";;", "")

    # Remove trailing punctuation
    name = re.sub(r"[,;:]+$", "", name)

    # Remove trailing numbers that are likely quantities (e.g., "JASK CREATIVE 20")
    name = re.sub(r"\s+\d{1,4}$", "", name)

    # Remove if name is just a date-like pattern (5-6 digits)
    if re.match(r"^\d{5,6}$", name):
        return ""

    # Normalize spacing
    name = re.sub(r"\s+", " ", name)

    return name.strip()


def refine_legacy_extract():
    """Process legacy_extract.json and create refined version."""

    input_path = Path("data/estimates/legacy_extract.json")
    output_path = Path("data/estimates/legacy_extract_refined.json")

    print(f"Reading {input_path}...")
    with open(input_path) as f:
        data = json.load(f)

    print(f"Total records: {len(data)}")

    # Statistics
    stats = {
        "total": len(data),
        "had_company": 0,
        "extracted_from_filename": 0,
        "templates_removed": 0,
        "invalid_company_removed": 0,
        "final_count": 0,
    }

    refined = []
    removed_templates = []
    removed_invalid = []
    extraction_log = []

    for record in data:
        file_name = record.get("file_name", "")
        original_company = record.get("company_name")

        # Check if it's a template file
        if is_template_file(file_name):
            stats["templates_removed"] += 1
            removed_templates.append(file_name)
            continue

        # Determine company name
        company = None
        used_original = False

        if original_company and str(original_company).strip():
            original_normalized = normalize_company_name(str(original_company))

            # Check if original looks like a job description
            if looks_like_job_description(original_normalized):
                # Try to extract from filename instead
                metadata = extract_company_from_filename(file_name)
                if metadata.company_name:
                    company = normalize_company_name(metadata.company_name)
                    stats["extracted_from_filename"] += 1
                    extraction_log.append({
                        "file": file_name,
                        "extracted": company,
                        "confidence": metadata.parse_confidence,
                        "replaced_original": original_normalized[:50],
                    })
                else:
                    # Keep original if extraction fails
                    company = original_normalized
                    used_original = True
            else:
                company = original_normalized
                used_original = True

            if used_original:
                stats["had_company"] += 1
        else:
            # Try to extract from filename
            metadata = extract_company_from_filename(file_name)
            if metadata.company_name:
                company = normalize_company_name(metadata.company_name)
                stats["extracted_from_filename"] += 1
                extraction_log.append({
                    "file": file_name,
                    "extracted": company,
                    "confidence": metadata.parse_confidence,
                })
            else:
                company = None

        # Validate company name
        if not company or not is_valid_company_name(company):
            stats["invalid_company_removed"] += 1
            removed_invalid.append({
                "file": file_name,
                "attempted_company": company,
            })
            continue

        # Add to refined data
        record["company_name"] = company
        refined.append(record)

    stats["final_count"] = len(refined)

    # Save refined data
    print(f"\nSaving {len(refined)} records to {output_path}...")
    with open(output_path, "w") as f:
        json.dump(refined, f, indent=2, default=str)

    # Print summary
    print("\n" + "=" * 60)
    print("REFINEMENT SUMMARY")
    print("=" * 60)
    print(f"Total input records:         {stats['total']:,}")
    print(f"Already had company name:    {stats['had_company']:,}")
    print(f"Extracted from filename:     {stats['extracted_from_filename']:,}")
    print(f"Templates removed:           {stats['templates_removed']:,}")
    print(f"Invalid company removed:     {stats['invalid_company_removed']:,}")
    print(f"Final refined records:       {stats['final_count']:,}")
    print("=" * 60)

    # Show removed templates
    if removed_templates:
        print("\nTemplate files removed:")
        for f in removed_templates[:10]:
            print(f"  - {f}")
        if len(removed_templates) > 10:
            print(f"  ... and {len(removed_templates) - 10} more")

    # Show sample extractions
    if extraction_log:
        print(f"\nSample company name extractions ({len(extraction_log)} total):")
        for e in extraction_log[:15]:
            print(f"  {e['extracted']:30} <- {e['file'][:45]}...")

    # Show invalid removals
    if removed_invalid:
        print(f"\nRecords removed (invalid company name):")
        for r in removed_invalid[:10]:
            print(f"  File: {r['file'][:50]}")
            print(f"  Attempted: {r['attempted_company']}")
            print()

    # Validate unique companies
    unique_companies = set(r["company_name"] for r in refined)
    print(f"\nUnique company names: {len(unique_companies):,}")

    return refined, stats


if __name__ == "__main__":
    refined, stats = refine_legacy_extract()
    print("\nDone!")
