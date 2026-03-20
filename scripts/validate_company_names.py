"""Validate company names extracted from legacy Excel files.

Detects entries that are likely job descriptions or product details
rather than actual company names.

Usage:
    python scripts/validate_company_names.py                    # Report only
    python scripts/validate_company_names.py --fix              # Apply fixes
    python scripts/validate_company_names.py --output report.csv  # Export report
"""

import argparse
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LEGACY_JSON = DATA_DIR / "estimates" / "legacy_extract.json"
COMPANY_FEATURES = DATA_DIR / "companies" / "company_features.csv"
NAME_MAPPING = DATA_DIR / "companies" / "name_mapping.json"


# ═══════════════════════════════════════════════════════════════════════════════
# Detection Patterns
# ═══════════════════════════════════════════════════════════════════════════════

# Patterns that strongly suggest a job description, not a company name
JOB_DESCRIPTION_PATTERNS = [
    # Starts with numbers (quantities, dimensions)
    (r"^\d+\s+(OR|X|MM|MICRON|COL|PCS|COPIES)", "starts_with_quantity"),
    (r"^\d+MM\b", "starts_with_dimension"),

    # Contains measurements
    (r"\d+\s*X\s*\d+\s*(MM|CM)?", "has_dimensions"),
    (r"\d+\s*MM\s*(X|THICK|DEEP|WIDE|HIGH)", "has_measurement"),
    (r"\d+\s*MICRON", "has_micron"),

    # Contains colour/printing specs
    (r"\d+\s*(COL|COLOUR|COLOR)\b", "has_colour_count"),
    (r"\bSCREEN\s+PRINT", "has_screen_print"),
    (r"\bDIGI(TAL)?\s+PRINT", "has_digi_print"),

    # Product-specific terms that wouldn't be in a company name
    (r"\bRIGID\s+BOX\s+TRAY", "product_rigid_box_tray"),
    (r"\bWRAP\s*AROUND\s+COVER", "product_wrap_around"),
    (r"\bDISPLAY\s+CARD\b", "product_display_card"),
    (r"\bTAPE\s+MEASURE", "product_tape_measure"),
    (r"\bLECT[EU]RN\s+HEADER", "product_lectern_header"),
    (r"\bDOOR\s+HANGER", "product_door_hanger"),
    (r"\bWINDOW\s+STICKER", "product_window_sticker"),
    (r"\bSELF\s+CLING", "product_self_cling"),
    (r"\bHEXAGONAL\s+SHAPE", "product_hexagonal"),
    (r"\bDIEBOND\s+PANEL", "product_diebond"),

    # Material specifications
    (r"\bFOAM\s+PVC\b", "material_foam_pvc"),
    (r"\bECO\s+KRAFT\b", "material_eco_kraft"),
    (r"\bCLEAR\s+SELF\s+CLING", "material_clear_cling"),
    (r"\b\d+\s*MIC\b", "material_micron"),

    # Quantity/version terms
    (r"\b\d+\s*(COPIES|VERSIONS|SHEETS|PCS)\b", "has_quantity_term"),
    (r"\bTRAY(S)?\s+ONLY\b", "tray_only"),
    (r"\bSPREADSHEET\b", "spreadsheet"),
]

# Words that are OK in company names (don't trigger false positives)
LEGITIMATE_COMPANY_WORDS = {
    "PRINT", "PRINTING", "PRINTERS", "LITHO", "GRAPHICS", "DESIGN",
    "DISPLAY", "DISPLAYS", "SIGNS", "SIGNAGE", "PACKAGING", "PACK",
    "FOLDERS", "FOLDER", "BINDERS", "BINDERY", "BOX", "BOXES",
    "COLOUR", "COLOR", "CREATIVE", "MEDIA", "SOLUTIONS",
}

# Known false positives - legitimate companies that match patterns
FALSE_POSITIVES = {
    "FOAM ENGINEERS",
    "FOLDERS LIMITED",
    "FOLDERS LTD",
    "SIMPLY FOLDERS",
    "RING BINDER PRODUCTS",
    "FANTASTIC MR BOX",
    "BAG N BOX MAN",
    "WRIGHT BOXES",
    "DRAWER BOX",
    "SELECTION BOX",
    "UK COVERS",
    "MERIT DISPLAY",
    "MERIT DISPLAYS",
    "DS DISPLAYS",
    "NUNEATON SIGNS",
    "RIGHT SIGNS",
    "BLUE SKY SIGNS",
    "WARWICK SIGNS",
    "GREEN ST BINDERY",
    "GREEN STREET BINDERY",
    "ABC BOX CO",
}


def _similarity(a: str, b: str) -> float:
    """Calculate similarity ratio between two strings."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.upper(), b.upper()).ratio()


def detect_issues(name: str) -> list[tuple[str, str]]:
    """Detect issues with a company name.

    Returns list of (pattern_name, matched_text) tuples.
    """
    if not name:
        return []

    # Skip known false positives
    if name.upper() in FALSE_POSITIVES:
        return []

    issues = []
    upper = name.upper()

    for pattern, issue_type in JOB_DESCRIPTION_PATTERNS:
        match = re.search(pattern, upper)
        if match:
            issues.append((issue_type, match.group()))

    return issues


def validate_ch_match(company_name: str, ch_name: str) -> dict:
    """Validate the Companies House match quality."""
    if not ch_name or pd.isna(ch_name):
        return {"match_quality": "no_match", "similarity": 0.0}

    sim = _similarity(company_name, ch_name)

    # Extract core company name (remove common suffixes)
    def core_name(n):
        n = n.upper()
        for suffix in [" LIMITED", " LTD", " PLC", " LLP", " UK", " GROUP"]:
            n = n.replace(suffix, "")
        return n.strip()

    core_sim = _similarity(core_name(company_name), core_name(ch_name))

    if core_sim >= 0.8:
        quality = "good"
    elif core_sim >= 0.5:
        quality = "partial"
    elif core_sim >= 0.3:
        quality = "weak"
    else:
        quality = "mismatch"

    return {
        "match_quality": quality,
        "similarity": round(core_sim, 2),
    }


def analyze_company_names(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze all company names and return a report DataFrame."""
    results = []

    for _, row in df.iterrows():
        name = row.get("company", "")
        ch_name = row.get("ch_company_name", "")

        issues = detect_issues(name)
        ch_match = validate_ch_match(name, ch_name)

        # Determine overall status
        if issues:
            if ch_match["match_quality"] == "mismatch":
                status = "INVALID"
                recommendation = "REMOVE"
            elif ch_match["match_quality"] == "weak":
                status = "SUSPICIOUS"
                recommendation = "REVIEW"
            else:
                status = "WARNING"
                recommendation = "CHECK"
        elif ch_match["match_quality"] == "mismatch":
            status = "CH_MISMATCH"
            recommendation = "REVIEW"
        else:
            status = "OK"
            recommendation = "KEEP"

        results.append({
            "company": name,
            "ch_company_name": ch_name,
            "ch_company_number": row.get("company_number", ""),
            "status": status,
            "recommendation": recommendation,
            "issues": "; ".join(f"{t}:{m}" for t, m in issues) if issues else "",
            "ch_match_quality": ch_match["match_quality"],
            "ch_similarity": ch_match["similarity"],
            "frequency": row.get("frequency", 0),
            "revenue": row.get("monetary_total", 0),
        })

    return pd.DataFrame(results)


def main():
    parser = argparse.ArgumentParser(description="Validate company names")
    parser.add_argument("--fix", action="store_true", help="Apply fixes to name mapping")
    parser.add_argument("--fix-suspicious", action="store_true", help="Also fix SUSPICIOUS entries")
    parser.add_argument("--output", type=str, help="Export report to CSV")
    args = parser.parse_args()

    print("Loading data...")
    df = pd.read_csv(COMPANY_FEATURES)
    print(f"Loaded {len(df)} companies")

    print("\nAnalyzing company names...")
    report = analyze_company_names(df)

    # Summary stats
    print("\n" + "=" * 70)
    print("VALIDATION REPORT")
    print("=" * 70)

    status_counts = report["status"].value_counts()
    print("\nStatus distribution:")
    for status, count in status_counts.items():
        pct = 100 * count / len(report)
        print(f"  {status:15s} {count:>4}  ({pct:.1f}%)")

    rec_counts = report["recommendation"].value_counts()
    print("\nRecommendations:")
    for rec, count in rec_counts.items():
        print(f"  {rec:15s} {count:>4}")

    # Show problematic entries
    invalid = report[report["status"] == "INVALID"].sort_values("revenue", ascending=False)
    if len(invalid) > 0:
        print(f"\n{'='*70}")
        print(f"INVALID ENTRIES ({len(invalid)}) - Recommend REMOVAL")
        print("=" * 70)
        for _, row in invalid.iterrows():
            print(f"\n  Company: {row['company']}")
            print(f"  CH Match: {row['ch_company_name']} (similarity: {row['ch_similarity']:.0%})")
            print(f"  Issues: {row['issues']}")
            print(f"  Revenue: £{row['revenue']:,.0f}  Frequency: {row['frequency']}")

    suspicious = report[report["status"] == "SUSPICIOUS"].sort_values("revenue", ascending=False)
    if len(suspicious) > 0:
        print(f"\n{'='*70}")
        print(f"SUSPICIOUS ENTRIES ({len(suspicious)}) - Need REVIEW")
        print("=" * 70)
        for _, row in suspicious.head(20).iterrows():
            print(f"\n  Company: {row['company']}")
            print(f"  CH Match: {row['ch_company_name']} (similarity: {row['ch_similarity']:.0%})")
            print(f"  Issues: {row['issues']}")

    ch_mismatch = report[report["status"] == "CH_MISMATCH"].sort_values("revenue", ascending=False)
    if len(ch_mismatch) > 0:
        print(f"\n{'='*70}")
        print(f"CH MISMATCHES ({len(ch_mismatch)}) - Weak/no match to Companies House")
        print("=" * 70)
        for _, row in ch_mismatch.head(20).iterrows():
            print(f"\n  Company: {row['company']}")
            print(f"  CH Match: {row['ch_company_name']} (similarity: {row['ch_similarity']:.0%})")

    # Export report
    if args.output:
        report.to_csv(args.output, index=False)
        print(f"\nReport exported to {args.output}")

    # Apply fixes
    if args.fix:
        print("\n" + "=" * 70)
        print("APPLYING FIXES")
        print("=" * 70)

        # Load current name mapping
        with open(NAME_MAPPING) as f:
            name_mapping = json.load(f)

        # Mark invalid entries as non-companies (map to None)
        fixed = 0
        for _, row in invalid.iterrows():
            name = row["company"]
            if name in name_mapping and name_mapping[name] is not None:
                name_mapping[name] = None
                fixed += 1
                print(f"  Marked as non-company (INVALID): {name}")

        # Also fix suspicious entries if requested
        if args.fix_suspicious:
            for _, row in suspicious.iterrows():
                name = row["company"]
                if name in name_mapping and name_mapping[name] is not None:
                    name_mapping[name] = None
                    fixed += 1
                    print(f"  Marked as non-company (SUSPICIOUS): {name}")

        # Save updated mapping
        with open(NAME_MAPPING, "w") as f:
            json.dump(name_mapping, f, indent=2, ensure_ascii=False)

        print(f"\nFixed {fixed} entries in {NAME_MAPPING}")
        print("Run 'python scripts/enrich_companies.py --stage merge' to regenerate dataset")

    # Summary
    total_issues = len(report[report["status"] != "OK"])
    total_invalid = len(invalid)
    print(f"\n{'='*70}")
    print("SUMMARY")
    print("=" * 70)
    print(f"Total companies:      {len(df)}")
    print(f"Valid (OK):           {len(report[report['status'] == 'OK'])}")
    print(f"Issues detected:      {total_issues}")
    print(f"Invalid (remove):     {total_invalid}")
    print(f"Data quality:         {100 * (len(df) - total_invalid) / len(df):.1f}%")


if __name__ == "__main__":
    main()
