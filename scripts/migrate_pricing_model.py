"""
Migrate legacy pricing model CSV to PricingRule and Material database records.

Reads data/materials/pricing_model.csv and converts legacy pandas df.loc[]
expressions to SafeExpressionEvaluator format using FormulaConverter.

Usage:
    # Dry run - preview what would be created:
    python -m scripts.migrate_pricing_model --dry-run

    # Generate SQL INSERT statements:
    python -m scripts.migrate_pricing_model --output sql

    # Generate JSON for review:
    python -m scripts.migrate_pricing_model --output json

    # Write directly to database:
    python -m scripts.migrate_pricing_model --output db
"""

import argparse
import csv
import json
import logging
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.formula_converter import (
    build_feature_index,
    convert_formula,
    _feature_to_var,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

CSV_PATH = PROJECT_ROOT / "data" / "materials" / "pricing_model.csv"


def _classify_category(
    feature_name: str,
    factory_const: float,
    customer_dep: float,
    customer_var: float,
    cost_rate: float,
) -> str:
    """Classify a pricing variable into a RuleCategory."""
    name_upper = feature_name.upper()

    # Customer inputs (dimensions, quantity, etc.)
    if customer_var == 1.0:
        return "customer_variable"

    # Factory constants with cost rates
    if factory_const == 1.0 and cost_rate > 0:
        # Labor/machine time operations
        if any(
            kw in name_upper
            for kw in ["HOUR", "SPEED", "TIME", "SET UP", "CLEAN UP", "MAKE READY"]
        ):
            return "labor_time"
        # Material costs
        if any(kw in name_upper for kw in ["COST", "SHEET", "MAGNET", "RIVET", "PACKING"]):
            return "material_cost"
        # Everything else with a rate is overhead
        return "overhead"

    # Factory constants without cost rates
    if factory_const == 1.0:
        return "factory_constant"

    # Customer-dependent calculated values
    if customer_dep == 1.0:
        if cost_rate > 0:
            return "material_cost"
        return "calculated"

    return "calculated"


def _extract_unit(feature_name: str) -> Optional[str]:
    """Extract unit of measure from feature name parenthetical."""
    match = re.search(r"\(([^)]+)\)$", feature_name.strip())
    if match:
        unit_text = match.group(1).lower()
        unit_map = {
            "number": "units",
            "hours": "hours",
            "per hour": "per_hour",
            "mm": "mm",
            "m^2": "sqm",
            "kg": "kg",
            "job": "per_job",
            "number per hours": "per_hour",
        }
        return unit_map.get(unit_text, unit_text)
    return None


def _extract_dependencies(
    expression: Optional[str], all_var_names: set[str]
) -> list[str]:
    """Extract variable dependencies from a converted expression."""
    if not expression:
        return []

    # Tokenize: find all identifier-like tokens
    tokens = re.findall(r"[a-z_][a-z0-9_]*", expression)
    # Filter to known variables (exclude function names)
    safe_funcs = {"ceil", "round", "floor", "sqrt", "abs", "log", "min", "max", "sum"}
    deps = []
    seen = set()
    for token in tokens:
        if token in all_var_names and token not in seen and token not in safe_funcs:
            # Also check for sum_from_ prefixed aggregations
            deps.append(token)
            seen.add(token)

    # Handle sum_from_ references (e.g., sum_from_mechanism_total)
    for match in re.finditer(r"sum_from_([a-z_][a-z0-9_]*)", expression):
        base_var = match.group(1)
        # Strip suffix like _total
        for suffix in ["_total", "_costrate", "_updated", ""]:
            candidate = base_var.rstrip("_") if not suffix else base_var.replace(suffix, "").rstrip("_")
            if candidate in all_var_names and candidate not in seen:
                deps.append(candidate)
                seen.add(candidate)

    return sorted(deps)


def parse_csv() -> list[dict]:
    """Parse the pricing model CSV and return raw records."""
    if not CSV_PATH.exists():
        logger.error(f"CSV not found: {CSV_PATH}")
        sys.exit(1)

    records = []
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            feature = row.get("Feature", "").strip()
            if not feature:
                continue
            records.append(
                {
                    "feature": feature,
                    "multiplier": float(row.get("Multiplier", 0) or 0),
                    "multiplier_expr": row.get("Equation for Multiplier", "").strip(),
                    "updated_multiplier": float(
                        row.get("Updated Multiplier", 0) or 0
                    ),
                    "factory_const": float(
                        row.get("Factory Set Constant", 0) or 0
                    ),
                    "customer_dep": float(
                        row.get("Customer Dependant Variable", 0) or 0
                    ),
                    "customer_var": float(
                        row.get("Customer Variable", 0) or 0
                    ),
                    "cost_rate": float(row.get("COST/RATE (£)", 0) or 0),
                    "total": float(row.get("TOTAL (£)", 0) or 0),
                    "total_expr": row.get("Equation for TOTAL (£)", "").strip(),
                }
            )

    logger.info(f"Parsed {len(records)} features from CSV")
    return records


def convert_to_pricing_rules(records: list[dict]) -> list[dict]:
    """Convert raw CSV records to PricingRule-compatible dicts."""
    features = [r["feature"] for r in records]
    feature_index = build_feature_index(features)
    all_var_names = set(feature_index.values())

    rules = []
    conversion_errors = []

    for rec in records:
        feature = rec["feature"]
        var_name = feature_index[feature]

        # Convert expressions
        mult_expr = convert_formula(rec["multiplier_expr"], feature_index)
        total_expr = convert_formula(rec["total_expr"], feature_index)

        if rec["multiplier_expr"] and not mult_expr:
            conversion_errors.append(
                f"  Multiplier: {feature} -> {rec['multiplier_expr']}"
            )
        if rec["total_expr"] and not total_expr:
            conversion_errors.append(
                f"  Total: {feature} -> {rec['total_expr']}"
            )

        # Classify
        category = _classify_category(
            feature,
            rec["factory_const"],
            rec["customer_dep"],
            rec["customer_var"],
            rec["cost_rate"],
        )

        # Extract dependencies from both expressions
        mult_deps = _extract_dependencies(mult_expr, all_var_names)
        total_deps = _extract_dependencies(total_expr, all_var_names)
        all_deps = sorted(set(mult_deps + total_deps))

        # For self-referential expressions (e.g., df.loc["X", "Multiplier"] = X),
        # remove self from dependencies
        all_deps = [d for d in all_deps if d != var_name]

        unit = _extract_unit(feature)

        rule = {
            "name": var_name,
            "display_name": feature,
            "description": f"Legacy variable: {feature}",
            "category": category,
            "expression": mult_expr or str(rec["multiplier"]),
            "total_expression": total_expr,
            "dependencies": all_deps if all_deps else None,
            "default_value": rec["multiplier"],
            "cost_rate": rec["cost_rate"] if rec["cost_rate"] > 0 else None,
            "default_total": rec["total"] if rec["total"] != 0 else None,
            "unit": unit,
            "version": 1,
            "is_active": True,
            "notes": f"Migrated from pricing_model.csv. "
            f"Flags: factory={int(rec['factory_const'])}, "
            f"customer_dep={int(rec['customer_dep'])}, "
            f"customer_var={int(rec['customer_var'])}",
        }
        rules.append(rule)

    if conversion_errors:
        logger.warning(
            f"{len(conversion_errors)} expression conversion failures:\n"
            + "\n".join(conversion_errors)
        )

    # Summary by category
    from collections import Counter

    cats = Counter(r["category"] for r in rules)
    logger.info("Category distribution:")
    for cat, count in cats.most_common():
        logger.info(f"  {cat}: {count}")

    return rules


def extract_materials(records: list[dict]) -> list[dict]:
    """Extract material records from pricing data."""
    materials = []

    material_patterns = {
        "COST PER SHEET OF DUTCH GREY BOARD": {
            "category": "board",
            "unit": "sheet",
            "description": "Dutch grey board sheet",
        },
        "COST PER SHEET OF LINER PAPER": {
            "category": "paper",
            "unit": "sheet",
            "description": "Liner paper sheet",
        },
        "PRINTED AND LAMINATED OUTER SHEETS": {
            "category": "paper",
            "unit": "sheet",
            "description": "Printed and laminated outer sheets",
        },
        "PRINTED AND LAMINATED INNER SHEETS": {
            "category": "paper",
            "unit": "sheet",
            "description": "Printed and laminated inner sheets",
        },
        "MECHANISM": {
            "category": "hardware",
            "unit": "unit",
            "description": "Ring mechanism / closure mechanism",
        },
        "SINGLE MAGNET COST": {
            "category": "hardware",
            "unit": "unit",
            "description": "Magnetic closure (single magnet)",
        },
        "NUMBER OF RIVETS PER BINDER": {
            "category": "hardware",
            "unit": "unit",
            "description": "Binding rivets",
        },
        "GLUE COST PER BINDER": {
            "category": "adhesive",
            "unit": "sqm",
            "description": "PVA adhesive for binding",
        },
        "CUTTING FORME COST": {
            "category": "consumable",
            "unit": "unit",
            "description": "Custom cutting forme/die",
        },
        "PACKING MATERIALS PER PALLETE": {
            "category": "consumable",
            "unit": "unit",
            "description": "Pallet packing materials (wrap, strapping)",
        },
        "DIGITAL/FOIL/SCREENPRINTING": {
            "category": "finishing",
            "unit": "unit",
            "description": "Digital printing / foil / screenprint finishing",
        },
    }

    seen_skus = set()
    for rec in records:
        feature = rec["feature"]
        for pattern, mat_info in material_patterns.items():
            if pattern in feature.upper():
                # Generate unique SKU
                base_sku = _feature_to_var(feature).upper().replace("_", "-")
                sku = base_sku[:30]
                if sku in seen_skus:
                    suffix = 2
                    while f"{sku}-{suffix}" in seen_skus:
                        suffix += 1
                    sku = f"{sku[:27]}-{suffix}"
                seen_skus.add(sku)

                materials.append(
                    {
                        "name": mat_info["description"],
                        "sku": sku,
                        "description": f"Extracted from pricing model: {feature}",
                        "category": mat_info["category"],
                        "unit": mat_info["unit"],
                        "current_price": rec["cost_rate"],
                        "is_active": True,
                        "source_feature": feature,
                    }
                )
                break

    logger.info(f"Extracted {len(materials)} material records")
    return materials


def output_dry_run(rules: list[dict], materials: list[dict]) -> None:
    """Print a summary without writing anything."""
    print(f"\n{'='*60}")
    print(f"PRICING MODEL MIGRATION - DRY RUN")
    print(f"{'='*60}\n")

    print(f"Pricing Rules: {len(rules)}")
    print(f"Materials: {len(materials)}\n")

    print("--- Pricing Rules ---")
    for r in rules:
        deps = r["dependencies"] or []
        expr_preview = (r["expression"] or "")[:60]
        print(
            f"  [{r['category']:20s}] {r['name']:45s} = {expr_preview}"
            f"  (deps: {len(deps)})"
        )

    print("\n--- Materials ---")
    for m in materials:
        print(
            f"  [{m['category']:12s}] {m['name']:40s}  £{m['current_price']:.4f}/{m['unit']}"
        )

    print(f"\n--- Expression Samples ---")
    for r in rules[:5]:
        print(f"\n  {r['display_name']}:")
        print(f"    var: {r['name']}")
        print(f"    mult_expr: {r['expression']}")
        print(f"    total_expr: {r.get('total_expression', 'N/A')}")
        print(f"    deps: {r['dependencies']}")


def output_json(rules: list[dict], materials: list[dict]) -> None:
    """Write JSON files for review."""
    out_dir = PROJECT_ROOT / "data" / "migrations"
    out_dir.mkdir(parents=True, exist_ok=True)

    rules_path = out_dir / "pricing_rules.json"
    with open(rules_path, "w") as f:
        json.dump(rules, f, indent=2, default=str)
    logger.info(f"Wrote {len(rules)} rules to {rules_path}")

    materials_path = out_dir / "materials.json"
    with open(materials_path, "w") as f:
        json.dump(materials, f, indent=2, default=str)
    logger.info(f"Wrote {len(materials)} materials to {materials_path}")


def output_sql(rules: list[dict], materials: list[dict]) -> None:
    """Generate SQL INSERT statements."""
    out_dir = PROJECT_ROOT / "data" / "migrations"
    out_dir.mkdir(parents=True, exist_ok=True)
    sql_path = out_dir / "seed_pricing_rules.sql"

    now = datetime.now(timezone.utc).isoformat()

    with open(sql_path, "w") as f:
        f.write("-- Pricing Rules seed data\n")
        f.write(f"-- Generated: {now}\n")
        f.write("-- Source: data/materials/pricing_model.csv\n\n")
        f.write("BEGIN;\n\n")

        # Materials first
        f.write("-- Materials\n")
        for mat in materials:
            mid = uuid.uuid4()
            name = mat["name"].replace("'", "''")
            desc = (mat["description"] or "").replace("'", "''")
            sku = (mat["sku"] or "").replace("'", "''")
            f.write(
                f"INSERT INTO materials (id, name, sku, description, category, unit, "
                f"current_price, is_active, created_at, updated_at) VALUES (\n"
                f"  '{mid}', '{name}', '{sku}', '{desc}', "
                f"'{mat['category']}', '{mat['unit']}', {mat['current_price']}, "
                f"true, NOW(), NOW()\n);\n\n"
            )

        # Pricing rules
        f.write("\n-- Pricing Rules\n")
        for rule in rules:
            rid = uuid.uuid4()
            name = rule["name"].replace("'", "''")
            display = (rule["display_name"] or "").replace("'", "''")
            desc = (rule["description"] or "").replace("'", "''")
            expr = (rule["expression"] or "").replace("'", "''")
            notes = (rule["notes"] or "").replace("'", "''")

            deps_sql = "NULL"
            if rule["dependencies"]:
                deps_list = ", ".join(f"'{d}'" for d in rule["dependencies"])
                deps_sql = f"ARRAY[{deps_list}]"

            default_val = rule["default_value"] if rule["default_value"] is not None else "NULL"
            unit = f"'{rule['unit']}'" if rule["unit"] else "NULL"

            f.write(
                f"INSERT INTO pricing_rules (id, name, display_name, description, "
                f"category, expression, dependencies, default_value, unit, "
                f"version, is_active, notes, created_at, updated_at) VALUES (\n"
                f"  '{rid}', '{name}', '{display}', '{desc}', "
                f"'{rule['category']}', '{expr}', {deps_sql}, {default_val}, "
                f"{unit}, 1, true, '{notes}', NOW(), NOW()\n);\n\n"
            )

        f.write("COMMIT;\n")

    logger.info(f"Wrote SQL to {sql_path}")


async def output_db(rules: list[dict], materials: list[dict]) -> None:
    """Write directly to the database using SQLAlchemy."""
    from backend.app.db.session import async_session_factory
    from backend.app.models.material import Material, MaterialCategory, UnitOfMeasure
    from backend.app.models.pricing_rule import PricingRule, RuleCategory

    unit_map = {
        "sheet": UnitOfMeasure.SHEET,
        "unit": UnitOfMeasure.UNIT,
        "sqm": UnitOfMeasure.SQM,
        "kg": UnitOfMeasure.KG,
    }

    async with async_session_factory() as session:
        async with session.begin():
            # Insert materials
            for mat in materials:
                m = Material(
                    name=mat["name"],
                    sku=mat["sku"],
                    description=mat["description"],
                    category=MaterialCategory(mat["category"]),
                    unit=unit_map.get(mat["unit"], UnitOfMeasure.UNIT),
                    current_price=mat["current_price"],
                    is_active=True,
                )
                session.add(m)

            # Insert pricing rules
            for rule in rules:
                pr = PricingRule(
                    name=rule["name"],
                    display_name=rule["display_name"],
                    description=rule["description"],
                    category=RuleCategory(rule["category"]),
                    expression=rule["expression"],
                    dependencies=rule["dependencies"],
                    default_value=rule["default_value"],
                    unit=rule["unit"],
                    version=1,
                    is_active=True,
                    notes=rule["notes"],
                )
                session.add(pr)

        logger.info(
            f"Committed {len(materials)} materials and {len(rules)} pricing rules to database"
        )


def main():
    parser = argparse.ArgumentParser(description="Migrate pricing model CSV to database format")
    parser.add_argument(
        "--output",
        choices=["dry-run", "json", "sql", "db"],
        default="dry-run",
        help="Output format (default: dry-run)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be created (shortcut for --output dry-run)",
    )
    args = parser.parse_args()

    if args.dry_run:
        args.output = "dry-run"

    # Parse and convert
    records = parse_csv()
    rules = convert_to_pricing_rules(records)
    materials = extract_materials(records)

    # Output
    if args.output == "dry-run":
        output_dry_run(rules, materials)
    elif args.output == "json":
        output_json(rules, materials)
    elif args.output == "sql":
        output_sql(rules, materials)
    elif args.output == "db":
        import asyncio

        asyncio.run(output_db(rules, materials))


if __name__ == "__main__":
    main()
