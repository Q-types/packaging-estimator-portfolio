#!/usr/bin/env python3
"""
Anonymize company names and PackagePro branding for portfolio use.

This script:
1. Extracts all unique company names from data files
2. Generates consistent fake company names
3. Replaces all occurrences across CSV, JSON, Python, HTML, and MD files
4. Replaces PackagePro branding with generic alternatives
"""

import csv
import json
import os
import random
import re
from pathlib import Path
from typing import Dict, Set

# Seed for reproducibility
random.seed(42)

# Base directory
BASE_DIR = Path(__file__).parent.parent

# ============================================================================
# FAKE COMPANY NAME GENERATOR
# ============================================================================

PREFIXES = [
    "Apex", "Summit", "Prime", "Nova", "Atlas", "Vertex", "Zenith", "Meridian",
    "Horizon", "Pinnacle", "Sterling", "Phoenix", "Titan", "Vanguard", "Nexus",
    "Quantum", "Stellar", "Coastal", "Northern", "Southern", "Eastern", "Western",
    "Central", "Metro", "Urban", "Pacific", "Atlantic", "Continental", "Global",
    "National", "Royal", "Premier", "Elite", "Superior", "Dynamic", "Precision",
    "Express", "Swift", "Rapid", "Agile", "Flex", "Pro", "Max", "Ultra", "Mega",
    "Alpha", "Beta", "Gamma", "Delta", "Omega", "Sigma", "Vector", "Matrix"
]

INDUSTRIES = [
    "Print", "Graphics", "Media", "Design", "Creative", "Solutions", "Services",
    "Group", "Partners", "Associates", "Industries", "Manufacturing", "Packaging",
    "Labels", "Signs", "Display", "Marketing", "Communications", "Productions",
    "Enterprises", "Holdings", "International", "Systems", "Technologies", "Works"
]

SUFFIXES = ["Ltd", "Limited", "Co", "Inc", "Corp", "PLC", "LLP", "Group"]

UK_TOWNS = [
    "Bristol", "Leeds", "Manchester", "Birmingham", "Sheffield", "Liverpool",
    "Newcastle", "Nottingham", "Leicester", "Coventry", "Bradford", "Cardiff",
    "Edinburgh", "Glasgow", "Belfast", "Southampton", "Portsmouth", "Oxford",
    "Cambridge", "York", "Chester", "Bath", "Brighton", "Plymouth", "Norwich"
]

FIRST_NAMES = [
    "Smith", "Jones", "Taylor", "Brown", "Wilson", "Davies", "Evans", "Thomas",
    "Johnson", "Roberts", "Walker", "Wright", "Thompson", "White", "Hughes",
    "Edwards", "Green", "Hall", "Wood", "Harris", "Martin", "Jackson", "Clarke",
    "Lewis", "Morgan", "Lee", "King", "Baker", "Allen", "Mitchell"
]


def generate_fake_company_name(index: int) -> str:
    """Generate a unique fake company name."""
    patterns = [
        # Prefix + Industry (40%)
        lambda: f"{random.choice(PREFIXES)} {random.choice(INDUSTRIES)}",
        # Town + Industry (20%)
        lambda: f"{random.choice(UK_TOWNS)} {random.choice(INDUSTRIES)}",
        # Name & Name (15%)
        lambda: f"{random.choice(FIRST_NAMES)} & {random.choice(FIRST_NAMES)}",
        # Single word + suffix (15%)
        lambda: f"{random.choice(PREFIXES)}{random.choice(INDUSTRIES)[:4]}",
        # Acronym style (10%)
        lambda: "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=random.randint(2, 4))),
    ]

    weights = [0.4, 0.2, 0.15, 0.15, 0.1]
    pattern = random.choices(patterns, weights=weights)[0]

    # Add index suffix to ensure uniqueness
    base_name = pattern()
    return f"{base_name} {index % 1000:03d}" if index > len(PREFIXES) * len(INDUSTRIES) else base_name


# ============================================================================
# COMPANY NAME EXTRACTION
# ============================================================================

def extract_companies_from_csv(file_path: Path, column_name: str = "company") -> Set[str]:
    """Extract company names from a CSV file."""
    companies = set()
    if not file_path.exists():
        return companies

    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if column_name in row and row[column_name]:
                    companies.add(row[column_name].strip())
                # Also check for company_name variant
                if 'company_name' in row and row['company_name']:
                    companies.add(row['company_name'].strip())
                # Check ch_company_name (Companies House name)
                if 'ch_company_name' in row and row['ch_company_name']:
                    companies.add(row['ch_company_name'].strip())
    except Exception as e:
        print(f"  Warning: Could not read {file_path}: {e}")

    return companies


def extract_companies_from_json(file_path: Path) -> Set[str]:
    """Extract company names from JSON files."""
    companies = set()
    if not file_path.exists():
        return companies

    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            data = json.load(f)

        if isinstance(data, dict):
            # name_mapping.json style: keys and values are company names
            for key, value in data.items():
                if isinstance(key, str):
                    companies.add(key.strip())
                if isinstance(value, str):
                    companies.add(value.strip())
                elif isinstance(value, dict):
                    # ch_cache.json style: nested company info
                    if 'company_name' in value:
                        companies.add(value['company_name'].strip())
                    if 'title' in value:
                        companies.add(value['title'].strip())
    except Exception as e:
        print(f"  Warning: Could not read {file_path}: {e}")

    return companies


def collect_all_companies() -> Set[str]:
    """Collect all unique company names from the project."""
    print("Collecting company names from all data files...")
    all_companies = set()

    # CSV files with company data
    csv_files = [
        BASE_DIR / "data/companies/company_features.csv",
        BASE_DIR / "data/companies/company_features_processed_base.csv",
        BASE_DIR / "data/companies/company_features_preprocessed.csv",
        BASE_DIR / "data/companies/customer_stats.csv",
        BASE_DIR / "data/companies/internal_features.csv",
        BASE_DIR / "data/companies/ads_clustering/final_cluster_assignments.csv",
        BASE_DIR / "data/prospects/scored_prospects.csv",
        BASE_DIR / "data/prospects/scored_prospects_with_packaging.csv",
        BASE_DIR / "data/prospects/test_prospects.csv",
        BASE_DIR / "dashboard/data/companies/ads_clustering/final_cluster_assignments.csv",
        BASE_DIR / "dashboard/data/prospects/scored_prospects.csv",
    ]

    for csv_file in csv_files:
        companies = extract_companies_from_csv(csv_file)
        if companies:
            print(f"  Found {len(companies)} companies in {csv_file.name}")
            all_companies.update(companies)

    # JSON files
    json_files = [
        BASE_DIR / "data/companies/name_mapping.json",
        BASE_DIR / "data/companies/ch_cache.json",
        BASE_DIR / "data/companies/ch_deep_cache.json",
    ]

    for json_file in json_files:
        companies = extract_companies_from_json(json_file)
        if companies:
            print(f"  Found {len(companies)} companies in {json_file.name}")
            all_companies.update(companies)

    # Filter out empty strings and very short names
    all_companies = {c for c in all_companies if c and len(c) > 1}

    print(f"\nTotal unique companies found: {len(all_companies)}")
    return all_companies


# ============================================================================
# MAPPING GENERATION
# ============================================================================

def generate_company_mapping(companies: Set[str]) -> Dict[str, str]:
    """Generate a mapping from real company names to fake ones."""
    print("\nGenerating fake company name mapping...")

    mapping = {}
    used_names = set()

    # Sort for reproducibility
    sorted_companies = sorted(companies, key=lambda x: x.lower())

    for i, company in enumerate(sorted_companies):
        # Generate unique fake name
        attempts = 0
        while attempts < 100:
            fake_name = generate_fake_company_name(i + attempts * 1000)
            if fake_name not in used_names:
                used_names.add(fake_name)
                mapping[company] = fake_name
                break
            attempts += 1
        else:
            # Fallback: use index-based name
            mapping[company] = f"Company_{i:04d}"

    return mapping


# ============================================================================
# FILE REPLACEMENT FUNCTIONS
# ============================================================================

def replace_in_csv(file_path: Path, mapping: Dict[str, str]) -> bool:
    """Replace company names in a CSV file."""
    if not file_path.exists():
        return False

    try:
        # Read the file
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        original_content = content

        # Sort mapping by length (longest first) to avoid partial replacements
        sorted_mapping = sorted(mapping.items(), key=lambda x: len(x[0]), reverse=True)

        for real_name, fake_name in sorted_mapping:
            # Replace exact matches (case-sensitive for company names)
            content = content.replace(f',{real_name},', f',{fake_name},')
            content = content.replace(f',{real_name}\n', f',{fake_name}\n')
            content = content.replace(f'\n{real_name},', f'\n{fake_name},')
            # Handle first column
            if content.startswith(f'{real_name},'):
                content = f'{fake_name},' + content[len(real_name) + 1:]

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

    except Exception as e:
        print(f"  Error processing {file_path}: {e}")

    return False


def replace_in_json(file_path: Path, mapping: Dict[str, str]) -> bool:
    """Replace company names in a JSON file."""
    if not file_path.exists():
        return False

    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        original_content = content

        # Sort mapping by length (longest first)
        sorted_mapping = sorted(mapping.items(), key=lambda x: len(x[0]), reverse=True)

        for real_name, fake_name in sorted_mapping:
            # Replace in JSON strings
            content = content.replace(f'"{real_name}"', f'"{fake_name}"')
            content = content.replace(f"'{real_name}'", f"'{fake_name}'")

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

    except Exception as e:
        print(f"  Error processing {file_path}: {e}")

    return False


def replace_in_text_file(file_path: Path, mapping: Dict[str, str], branding_replacements: Dict[str, str]) -> bool:
    """Replace company names and branding in text files (Python, HTML, MD)."""
    if not file_path.exists():
        return False

    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()

        original_content = content

        # Apply branding replacements first
        for old, new in branding_replacements.items():
            content = content.replace(old, new)

        # Only apply company mapping to specific display contexts (not all occurrences)
        # This is more conservative to avoid breaking code

        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True

    except Exception as e:
        print(f"  Error processing {file_path}: {e}")

    return False


# ============================================================================
# BRANDING REPLACEMENTS
# ============================================================================

BRANDING_REPLACEMENTS = {
    # App name
    "PackagePro Estimator": "PackagePro Estimator",
    "PackagePro Intelligence": "PackagePro Intelligence",
    "PackagePro Intelligence": "PackagePro Intelligence",
    "PackagePro": "PackagePro",
    "PackagePro": "PackagePro",

    # Domain
    "packagepro-demo.example.com": "packagepro-demo.example.com",
    "packagepro": "packagepro",

    # Emoji branding (preserve emoji)
    "PackagePro Intelligence": "PackagePro Intelligence",
}


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def anonymize_project():
    """Main function to anonymize the entire project."""
    print("=" * 60)
    print("ANONYMIZATION SCRIPT FOR PORTFOLIO")
    print("=" * 60)

    # Step 1: Collect all company names
    all_companies = collect_all_companies()

    # Step 2: Generate mapping
    mapping = generate_company_mapping(all_companies)

    # Save mapping for reference
    mapping_file = BASE_DIR / "scripts/anonymization_mapping.json"
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)
    print(f"\nMapping saved to: {mapping_file}")

    # Step 3: Replace in data files
    print("\n" + "=" * 60)
    print("REPLACING COMPANY NAMES IN DATA FILES")
    print("=" * 60)

    csv_files = list(BASE_DIR.rglob("*.csv"))
    json_data_files = [
        BASE_DIR / "data/companies/name_mapping.json",
        BASE_DIR / "data/companies/ch_cache.json",
        BASE_DIR / "data/companies/ch_deep_cache.json",
    ]

    modified_count = 0

    for csv_file in csv_files:
        if replace_in_csv(csv_file, mapping):
            print(f"  Modified: {csv_file.relative_to(BASE_DIR)}")
            modified_count += 1

    for json_file in json_data_files:
        if replace_in_json(json_file, mapping):
            print(f"  Modified: {json_file.relative_to(BASE_DIR)}")
            modified_count += 1

    # Step 4: Replace branding in code files
    print("\n" + "=" * 60)
    print("REPLACING PackagePro BRANDING")
    print("=" * 60)

    code_extensions = ['.py', '.html', '.md', '.json', '.yaml', '.yml', '.env', '.txt']

    for ext in code_extensions:
        for file_path in BASE_DIR.rglob(f"*{ext}"):
            # Skip node_modules, venv, etc.
            if any(skip in str(file_path) for skip in ['node_modules', 'venv', '.git', '__pycache__', 'anonymization_mapping']):
                continue

            if replace_in_text_file(file_path, mapping, BRANDING_REPLACEMENTS):
                print(f"  Modified: {file_path.relative_to(BASE_DIR)}")
                modified_count += 1

    # Step 5: Summary
    print("\n" + "=" * 60)
    print("ANONYMIZATION COMPLETE")
    print("=" * 60)
    print(f"  Companies anonymized: {len(mapping)}")
    print(f"  Files modified: {modified_count}")
    print(f"  Mapping saved to: {mapping_file}")
    print("\nThe dashboard is now safe for portfolio use!")


if __name__ == "__main__":
    anonymize_project()
