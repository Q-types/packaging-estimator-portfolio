"""
Formula Converter - Converts legacy df.loc[] pandas expressions to safe evaluator format.

The legacy pricing model CSV uses pandas DataFrame syntax like:
    df.loc["FEATURE_NAME", "Multiplier"]
    df.loc["FEATURE_NAME", "TOTAL (£)"]
    np.ceil(expr)

This module converts these to variable-reference format that
SafeExpressionEvaluator can process safely.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def _feature_to_var(feature_name: str) -> str:
    """
    Convert a feature name to a valid Python variable name.

    Examples:
        "QUANTITY REQUIRED BY CUSTOMER (number)" -> "quantity_required_by_customer"
        "FLAT SIZE Length (mm)" -> "flat_size_length"
        "COST PER SHEET OF DUTCH GREY BOARD (number)" -> "cost_per_sheet_of_dutch_grey_board"
        "SET UP POB MACHINE (hours).1" -> "set_up_pob_machine_1"
    """
    # Remove unit suffixes in parentheses
    name = re.sub(r'\s*\([^)]*\)', '', feature_name)
    # Replace .1 .2 suffixes with _1 _2
    name = re.sub(r'\.(\d+)$', r'_\1', name)
    # Replace special characters
    name = name.replace('£', 'gbp').replace('^', '_pow_').replace('&', '_and_')
    # Convert to lowercase, replace spaces and non-alphanumeric with underscores
    name = re.sub(r'[^a-z0-9]+', '_', name.lower())
    # Remove leading/trailing underscores and collapse multiples
    name = re.sub(r'_+', '_', name).strip('_')
    return name


# Map of column names to variable suffixes
_COLUMN_SUFFIX = {
    'Multiplier': '',
    'TOTAL (£)': '_total',
    'COST/RATE (£)': '_costrate',
    'Updated Multiplier': '_updated',
}


def convert_formula(expression: str, feature_index: dict[str, str]) -> Optional[str]:
    """
    Convert a legacy df.loc[] expression to SafeExpressionEvaluator format.

    Args:
        expression: The raw expression from the pricing model CSV.
        feature_index: Mapping of original feature names to variable names.

    Returns:
        Converted expression string, or None if conversion fails.

    Examples:
        >>> idx = {"QUANTITY INCLUDING OVERS (number)": "quantity_including_overs"}
        >>> convert_formula('df.loc["QUANTITY INCLUDING OVERS (number)", "Multiplier"]', idx)
        'quantity_including_overs'

        >>> convert_formula('df.loc["X", "Multiplier"]*df.loc["Y", "COST/RATE (£)"]', idx)
        'x * y__cost_rate'
    """
    if not expression or not isinstance(expression, str):
        return None

    expr = expression.strip()
    if not expr:
        return None

    # Handle simple numeric expressions (e.g., "1/60*3")
    if 'df.loc' not in expr and 'np.' not in expr:
        return expr

    converted = expr

    # Step 1: Replace numpy functions with safe equivalents
    converted = converted.replace('np.ceil', 'ceil')
    converted = converted.replace('np.round', 'round')
    converted = converted.replace('np.floor', 'floor')
    converted = converted.replace('np.sqrt', 'sqrt')
    converted = converted.replace('np.abs', 'abs')
    converted = converted.replace('np.log', 'log')

    # Step 2: Handle df.loc["A": , "Column"].sum() range patterns
    # Pattern: df.loc["FEATURE": , "TOTAL (£)"].sum()
    range_pattern = re.compile(
        r'df\.loc\["([^"]+)"\s*:\s*,\s*"([^"]+)"\]\.sum\(\)'
    )
    for match in range_pattern.finditer(converted):
        start_feature = match.group(1)
        column = match.group(2)
        suffix = _COLUMN_SUFFIX.get(column, '')
        # This is a sum of all rows from start_feature downward
        # We represent this as a special aggregation variable
        start_var = feature_index.get(start_feature, _feature_to_var(start_feature))
        replacement = f"sum_from_{start_var}{suffix}"
        converted = converted.replace(match.group(0), replacement)

    # Step 3: Replace df.loc["FEATURE", "Column"] references
    loc_pattern = re.compile(
        r'df\.loc\["([^"]+)"\s*,\s*"([^"]+)"\]'
    )
    for match in loc_pattern.finditer(converted):
        feature = match.group(1)
        column = match.group(2)
        suffix = _COLUMN_SUFFIX.get(column, '')
        var_name = feature_index.get(feature, _feature_to_var(feature))
        replacement = var_name + suffix
        converted = converted.replace(match.group(0), replacement)

    # Step 4: Clean up any remaining df references (shouldn't happen)
    if 'df.' in converted:
        logger.warning(f"Unconverted df reference in: {converted}")
        return None

    return converted


def build_feature_index(feature_names: list[str]) -> dict[str, str]:
    """
    Build a mapping from original feature names to variable names.

    Args:
        feature_names: List of feature names from the pricing model CSV.

    Returns:
        Dict mapping original names to sanitized variable names.
    """
    index = {}
    seen_vars = set()
    for name in feature_names:
        var = _feature_to_var(name)
        # Handle duplicates (e.g., "SET UP POB MACHINE (hours)" and ".1")
        if var in seen_vars:
            suffix = 1
            while f"{var}_{suffix}" in seen_vars:
                suffix += 1
            var = f"{var}_{suffix}"
        seen_vars.add(var)
        index[name] = var
    return index


def convert_pricing_model(
    features: list[str],
    multiplier_exprs: list[str],
    total_exprs: list[str],
) -> dict[str, dict[str, Optional[str]]]:
    """
    Convert all formulas in a pricing model.

    Args:
        features: List of feature names (DataFrame index).
        multiplier_exprs: List of "Equation for Multiplier" expressions.
        total_exprs: List of "Equation for TOTAL (£)" expressions.

    Returns:
        Dict mapping feature variable names to their converted expressions:
        {
            "quantity_including_overs": {
                "multiplier_expr": "quantity_required_by_customer * 1.05 + 50",
                "total_expr": "sum_from_mechanism__total",
                "original_feature": "QUANTITY INCLUDING OVERS (number)"
            }
        }
    """
    feature_index = build_feature_index(features)
    result = {}

    for feature, mult_expr, total_expr in zip(features, multiplier_exprs, total_exprs):
        var_name = feature_index[feature]
        result[var_name] = {
            'multiplier_expr': convert_formula(mult_expr, feature_index),
            'total_expr': convert_formula(total_expr, feature_index),
            'original_feature': feature,
        }

    return result
