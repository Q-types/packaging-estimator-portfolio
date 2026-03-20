"""
PackagePro Estimator - Calculation Engine

Ported from legacy system with the following improvements:
1. Replaced dangerous eval() with SafeExpressionEvaluator
2. Added setup/run time separation
3. Added job complexity tier support
4. Improved wastage model
5. Type hints and better error handling
6. Database-independent design
7. Full audit trail for calculation traceability

Original: PackagePro_Functions.py (80+ interdependent variables)
"""

import logging
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Optional

import numpy as np
import pandas as pd

from backend.app.core.formula_converter import (
    build_feature_index,
    convert_formula,
)
from backend.app.core.safe_evaluator import (
    ExpressionEvaluationError,
    SafeExpressionEvaluator,
)

logger = logging.getLogger(__name__)


class ComplexityTier(Enum):
    """Job complexity tiers for risk-adjusted pricing."""

    TIER_1 = 1  # Simple, standard product
    TIER_2 = 2  # Minor customization
    TIER_3 = 3  # Standard bespoke (default)
    TIER_4 = 4  # Complex bespoke
    TIER_5 = 5  # Highly complex, prototype

    @property
    def multiplier(self) -> float:
        """Get pricing multiplier for complexity tier."""
        multipliers = {1: 1.0, 2: 1.05, 3: 1.10, 4: 1.20, 5: 1.35}
        return multipliers[self.value]

    @property
    def wastage_adjustment(self) -> float:
        """Get wastage rate adjustment for complexity tier."""
        adjustments = {1: 0.03, 2: 0.04, 3: 0.05, 4: 0.07, 5: 0.10}
        return adjustments[self.value]


@dataclass
class DimensionInputs:
    """Packaging dimension inputs."""

    flat_width: float  # mm
    flat_height: float  # mm
    outer_wrap_width: Optional[float] = None  # mm
    outer_wrap_height: Optional[float] = None  # mm
    liner_width: Optional[float] = None  # mm
    liner_height: Optional[float] = None  # mm
    spine_depth: float = 0.0  # mm


@dataclass
class MaterialInputs:
    """Material selection inputs."""

    board_type: str
    board_thickness: float = 2.0  # mm
    outer_wrap: str = "buckram_cloth"
    liner: str = "uncoated_paper_120gsm"
    additional_materials: list[str] = field(default_factory=list)


@dataclass
class EstimateInputs:
    """Complete inputs for estimate calculation."""

    dimensions: DimensionInputs
    quantity: int
    materials: MaterialInputs
    operations: list[str]
    complexity_tier: ComplexityTier = ComplexityTier.TIER_3
    rush_order: bool = False
    notes: Optional[str] = None


@dataclass
class AuditEntry:
    """Single step in the calculation audit trail."""

    step: str
    variable: str
    expression: str
    inputs_used: dict[str, Any]
    result: Any
    original_feature: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "variable": self.variable,
            "expression": self.expression,
            "inputs_used": {k: _serialize(v) for k, v in self.inputs_used.items()},
            "result": _serialize(self.result),
            "original_feature": self.original_feature,
        }


def _serialize(v: Any) -> Any:
    """Serialize a value for JSON output."""
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (np.integer, np.int64)):
        return int(v)
    if isinstance(v, (np.floating, np.float64)):
        return float(v)
    return v


@dataclass
class CostBreakdown:
    """Detailed cost breakdown with audit trail."""

    material_costs: dict[str, Decimal]
    labor_hours: dict[str, float]
    labor_cost: Decimal
    overhead_cost: Decimal
    wastage_cost: Decimal
    complexity_adjustment: Decimal
    rush_premium: Decimal
    total_cost: Decimal
    unit_cost: Decimal
    confidence_interval: tuple[Decimal, Decimal]
    confidence_level: float
    audit_trail: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "material_costs": {k: float(v) for k, v in self.material_costs.items()},
            "labor_hours": self.labor_hours,
            "labor_cost": float(self.labor_cost),
            "overhead_cost": float(self.overhead_cost),
            "wastage_cost": float(self.wastage_cost),
            "complexity_adjustment": float(self.complexity_adjustment),
            "rush_premium": float(self.rush_premium),
            "total_cost": float(self.total_cost),
            "unit_cost": float(self.unit_cost),
            "confidence_interval": [float(self.confidence_interval[0]), float(self.confidence_interval[1])],
            "confidence_level": self.confidence_level,
            "audit_trail": self.audit_trail,
        }


# Default hourly rates (loaded from database in production)
DEFAULT_HOURLY_RATES: dict[str, float] = {
    "guillotine": 50.0,
    "pob_machine": 100.0,
    "pob_machine_setup": 40.0,
    "pob_machine_cleanup": 40.0,
    "creasing": 70.0,
    "drilling": 40.0,
    "platten": 40.0,
    "riveting": 30.0,
    "packing": 35.0,
    "admin": 5.0,
    "mac_time": 40.0,
    "finishing": 35.0,
    "default": 40.0,
}

# Default machine speeds (units per hour)
DEFAULT_MACHINE_SPEEDS: dict[str, float] = {
    "cutting": 500,
    "wrapping": 1000,
    "creasing": 240,
    "drilling": 180,
    "laminating": 200,
    "foil_blocking": 150,
    "screen_printing": 100,
    "assembly": 50,
    "liner_gluing": 1000,
    "platten": 360,
}

# Default setup times (hours)
DEFAULT_SETUP_TIMES: dict[str, float] = {
    "cutting": 1 / 60 * 5,  # 5 minutes
    "wrapping": 3.0,
    "creasing": 0.5,
    "drilling": 1.0,
    "laminating": 0.5,
    "foil_blocking": 1.0,
    "screen_printing": 1.5,
    "assembly": 0.5,
    "liner_gluing": 3.0,
    "platten": 0.0,
}


class CalculationEngine:
    """
    Core calculation engine for packaging cost estimation.

    Uses SafeExpressionEvaluator for all formula calculations,
    replacing the dangerous eval() from the legacy system.

    Every calculation step is logged to an audit trail for full traceability.
    """

    def __init__(
        self,
        pricing_rules: Optional[pd.DataFrame] = None,
        hourly_rates: Optional[dict[str, float]] = None,
        machine_speeds: Optional[dict[str, float]] = None,
        setup_times: Optional[dict[str, float]] = None,
    ):
        self.evaluator = SafeExpressionEvaluator()
        self.pricing_rules = pricing_rules
        self.hourly_rates = hourly_rates or DEFAULT_HOURLY_RATES
        self.machine_speeds = machine_speeds or DEFAULT_MACHINE_SPEEDS
        self.setup_times = setup_times or DEFAULT_SETUP_TIMES
        self._feature_index: dict[str, str] = {}
        self._audit_trail: list[AuditEntry] = []
        self._aggregation_totals: set[str] = set()  # _total vars that are sum aggregations

        if pricing_rules is not None:
            self._build_feature_index()

    def load_pricing_rules(self, rules_df: pd.DataFrame) -> None:
        """Load pricing rules from DataFrame."""
        self.pricing_rules = rules_df.copy()
        self._build_feature_index()
        self._audit_trail.clear()

    def _build_feature_index(self) -> None:
        """Build feature name to variable name mapping."""
        if self.pricing_rules is not None:
            features = list(self.pricing_rules.index)
            self._feature_index = build_feature_index(features)

    def calculate(self, inputs: EstimateInputs) -> CostBreakdown:
        """
        Calculate complete cost estimate with full audit trail.

        Args:
            inputs: EstimateInputs with all job parameters.

        Returns:
            CostBreakdown with itemized costs and audit trail.
        """
        self._audit_trail = []
        self._aggregation_totals.clear()

        # Build variable context from inputs
        context = self._build_context(inputs)

        if self.pricing_rules is not None:
            # Update multipliers using pricing rule expressions
            self._update_multipliers(context)
            # Calculate totals using pricing rule expressions
            self._update_totals(context)

        # Build and return breakdown
        return self._build_breakdown(inputs, context)

    def _build_context(self, inputs: EstimateInputs) -> dict[str, Any]:
        """Build variable context from inputs."""
        # Outer wrap defaults to flat + 40mm (20mm each side)
        ow_width = inputs.dimensions.outer_wrap_width or inputs.dimensions.flat_width + 40
        ow_height = inputs.dimensions.outer_wrap_height or inputs.dimensions.flat_height + 40
        # Liner defaults to flat - 5mm
        liner_width = inputs.dimensions.liner_width or inputs.dimensions.flat_width - 5
        liner_height = inputs.dimensions.liner_height or inputs.dimensions.flat_height - 5

        context: dict[str, Any] = {
            # Dimensions
            "flat_width": inputs.dimensions.flat_width,
            "flat_height": inputs.dimensions.flat_height,
            "outer_wrap_width": ow_width,
            "outer_wrap_height": ow_height,
            "liner_width": liner_width,
            "liner_height": liner_height,
            "spine_depth": inputs.dimensions.spine_depth,
            # Quantity
            "quantity": inputs.quantity,
            # Complexity and rush
            "complexity_tier": inputs.complexity_tier.value,
            "complexity_multiplier": inputs.complexity_tier.multiplier,
            "wastage_rate": inputs.complexity_tier.wastage_adjustment,
            "rush_order": inputs.rush_order,
            "rush_multiplier": 1.5 if inputs.rush_order else 1.0,
            # Operations (as flags)
            **{f"op_{op}": 1 for op in inputs.operations},
            # Materials
            "board_type": inputs.materials.board_type,
            "board_thickness": inputs.materials.board_thickness,
            "outer_wrap_material": inputs.materials.outer_wrap,
            "liner_material": inputs.materials.liner,
        }

        # Derived dimensions (areas in m²)
        context["flat_area_sqm"] = (context["flat_width"] * context["flat_height"]) / 1_000_000
        context["outer_wrap_area_sqm"] = (ow_width * ow_height) / 1_000_000
        context["liner_area_sqm"] = (liner_width * liner_height) / 1_000_000
        context["total_glue_area_sqm"] = context["outer_wrap_area_sqm"] + context["liner_area_sqm"]

        # Wastage calculation
        base_wastage = 50  # Fixed minimum wastage units
        percentage_wastage = int(context["quantity"] * context["wastage_rate"])
        context["wastage_units"] = base_wastage + percentage_wastage
        context["quantity_with_overs"] = context["quantity"] + context["wastage_units"]

        # Board yield calculation
        board_sheet_area = 1.0  # m² per sheet (standard)
        context["yield_per_sheet"] = max(1, int(board_sheet_area / context["flat_area_sqm"])) if context["flat_area_sqm"] > 0 else 1
        context["grey_board_sheets"] = int(np.ceil(context["quantity_with_overs"] / context["yield_per_sheet"]))

        # Pile depths for guillotine time calculation
        context["liner_pile_depth_mm"] = context["quantity_with_overs"] * 0.15  # 0.15mm per liner sheet
        context["board_pile_depth_mm"] = context["grey_board_sheets"] * context["board_thickness"]

        # Map context to pricing rule variable names
        if self._feature_index:
            self._map_inputs_to_pricing_vars(context, inputs)

        self._audit("context_build", "all_inputs", "from_inputs", context, context)
        return context

    def _map_inputs_to_pricing_vars(self, context: dict[str, Any], inputs: EstimateInputs) -> None:
        """Map input values to the variable names used by pricing rules."""
        # Map standard inputs to legacy variable names
        legacy_mapping = {
            "quantity_required_by_customer": inputs.quantity,
            "quantity_including_overs": context["quantity_with_overs"],
            "one_item": 1.0,
            "flat_size_length": inputs.dimensions.flat_width,
            "flat_size_width": inputs.dimensions.flat_height,
            "flat_size_area": context["flat_area_sqm"],
            "outer_wrap_size_length": context["outer_wrap_width"],
            "outer_wrap_size_width": context["outer_wrap_height"],
            "outer_wrap_size_area": context["outer_wrap_area_sqm"],
            "liner_size_length": context["liner_width"],
            "liner_size_width": context["liner_height"],
            "liner_size_area": context["liner_area_sqm"],
            "total_area_for_glue": context["total_glue_area_sqm"],
            "thickness_of_dutch_grey_board": inputs.materials.board_thickness,
            "area_of_dutch_grey_board": 1.0,
            "yield_per_sheet_of_dutch_grey_board": context["yield_per_sheet"],
            "grey_board_sheets": context["grey_board_sheets"],
            "liner_total_pile_depth": context["liner_pile_depth_mm"],
            "dutch_grey_total_pile_depth": context["board_pile_depth_mm"],
            "unit_weight_for_carriage": 0.2,
        }
        context.update(legacy_mapping)

    def _update_multipliers(self, context: dict[str, Any]) -> None:
        """
        Update multiplier values based on expressions.
        Replaces legacy eval() with SafeExpressionEvaluator.
        """
        if self.pricing_rules is None:
            return

        # Pre-seed context with initial multiplier values from CSV
        # This handles self-referencing formulas like df.loc["X", "Multiplier"]
        for index, row in self.pricing_rules.iterrows():
            feature_name = str(index)
            var_name = self._feature_index.get(feature_name, feature_name)
            initial_val = row.get("Multiplier", 0)
            if var_name not in context and initial_val is not None:
                context[var_name] = initial_val
            # Also seed the cost rate for total calculations
            cost_rate = row.get("COST/RATE (£)", 0)
            if cost_rate is not None:
                context[f"{var_name}_costrate"] = cost_rate

        for index, row in self.pricing_rules.iterrows():
            feature_name = str(index)
            var_name = self._feature_index.get(feature_name, feature_name)

            # Skip if manually updated
            if row.get("Updated Multiplier", 0) == 1:
                context[var_name] = row.get("Multiplier", 0)
                continue

            raw_expression = row.get("Equation for Multiplier", "")
            if not raw_expression or pd.isna(raw_expression):
                context[var_name] = row.get("Multiplier", 0)
                continue

            # Convert legacy formula to safe format
            converted = convert_formula(str(raw_expression), self._feature_index)
            if converted is None:
                context[var_name] = row.get("Multiplier", 0)
                continue

            try:
                new_value = self.evaluator.evaluate(converted, context)
                self.pricing_rules.at[index, "Multiplier"] = new_value
                context[var_name] = new_value
                self._audit("multiplier", var_name, converted,
                           {k: context.get(k) for k in self._get_expr_deps(converted, context)},
                           new_value, feature_name)
            except ZeroDivisionError:
                self.pricing_rules.at[index, "Multiplier"] = 0
                context[var_name] = 0
                logger.warning(f"Division by zero in multiplier for {feature_name}")
            except ExpressionEvaluationError as e:
                logger.warning(f"Error evaluating multiplier for {feature_name}: {e} (expr: {converted})")
                context[var_name] = row.get("Multiplier", 0)

    def _update_totals(self, context: dict[str, Any]) -> None:
        """
        Calculate total costs using expressions.
        Processes top to bottom, building up sum aggregates.
        """
        if self.pricing_rules is None:
            return

        # First pass: compute individual totals
        for index, row in self.pricing_rules.iterrows():
            feature_name = str(index)
            var_name = self._feature_index.get(feature_name, feature_name)
            total_var = f"{var_name}_total"

            raw_expression = row.get("Equation for TOTAL (£)", "")
            if not raw_expression or pd.isna(raw_expression):
                context[total_var] = 0
                continue

            # Add current row's multiplier and cost to context
            context["multiplier"] = row.get("Multiplier", 0)
            context["cost_rate"] = row.get("COST/RATE (£)", 0)

            converted = convert_formula(str(raw_expression), self._feature_index)
            if converted is None:
                context[total_var] = 0
                continue

            # Handle sum_from_ aggregation references
            if converted.startswith("sum_from_"):
                # Defer - will be calculated after all individual totals
                context[total_var] = 0
                continue

            try:
                new_value = self.evaluator.evaluate(converted, context)
                self.pricing_rules.at[index, "TOTAL (£)"] = new_value
                context[total_var] = new_value
                self._audit("total", var_name, converted,
                           {k: context.get(k) for k in self._get_expr_deps(converted, context)},
                           new_value, feature_name)
            except ZeroDivisionError:
                self.pricing_rules.at[index, "TOTAL (£)"] = 0
                context[total_var] = 0
            except ExpressionEvaluationError as e:
                logger.warning(f"Error calculating total for {feature_name}: {e} (expr: {converted})")
                context[total_var] = 0

        # Second pass: compute sum aggregations
        self._compute_sum_aggregates(context)

    def _compute_sum_aggregates(self, context: dict[str, Any]) -> None:
        """Compute sum_from_ aggregation variables."""
        if self.pricing_rules is None:
            return

        features = list(self.pricing_rules.index)
        for i, feature_name in enumerate(features):
            var_name = self._feature_index.get(str(feature_name), str(feature_name))
            total_var = f"{var_name}_total"

            raw_expression = self.pricing_rules.at[feature_name, "Equation for TOTAL (£)"]
            if pd.isna(raw_expression):
                continue

            converted = convert_formula(str(raw_expression), self._feature_index)
            if converted and converted.startswith("sum_from_"):
                # Sum all _total values from the referenced feature downward
                ref_var = converted.replace("sum_from_", "").replace("_total", "")
                # Find the starting feature index
                start_idx = None
                for j, f in enumerate(features):
                    fv = self._feature_index.get(str(f), str(f))
                    if fv == ref_var:
                        start_idx = j
                        break

                if start_idx is not None:
                    total = sum(
                        context.get(f"{self._feature_index.get(str(features[k]), str(features[k]))}_total", 0)
                        for k in range(start_idx, len(features))
                    )
                    context[total_var] = total
                    self._aggregation_totals.add(total_var)
                    self.pricing_rules.at[feature_name, "TOTAL (£)"] = total
                    self._audit("aggregate_sum", var_name, converted,
                               {"range": f"rows {start_idx} to {len(features) - 1}"},
                               total, str(feature_name))

    def _build_breakdown(
        self, inputs: EstimateInputs, context: dict[str, Any]
    ) -> CostBreakdown:
        """Build cost breakdown from calculated values."""

        # Material costs from pricing rules or estimated
        material_costs = self._calculate_material_costs(inputs, context)

        # Labor hours per operation (informational, always computed)
        labor_hours = {}
        for op in inputs.operations:
            setup = self._get_setup_time(op)
            run = self._get_run_time(op, context["quantity_with_overs"])
            labor_hours[op] = round(setup + run, 4)
            self._audit("labor", op, f"setup({setup:.4f}h) + run({context['quantity_with_overs']}/{self.machine_speeds.get(op, 100):.0f})",
                        {"setup": setup, "quantity_with_overs": context["quantity_with_overs"],
                         "speed": self.machine_speeds.get(op, 100)},
                        labor_hours[op])

        total_labor_hours = sum(labor_hours.values())

        # Determine effective total from pricing rules or fallback
        pricing_rules_total = Decimal("0")
        has_pricing_total = False
        if self.pricing_rules is not None and self._aggregation_totals:
            # Use aggregation totals computed by _compute_sum_aggregates().
            # These correctly sum only leaf cost rows (from MECHANISM downward)
            # without double-counting aggregation or per-unit derived rows.
            agg_values = [
                context.get(var, 0) for var in self._aggregation_totals
                if isinstance(context.get(var, 0), (int, float)) and context.get(var, 0) > 0
            ]
            if agg_values:
                pricing_rules_total = Decimal(str(max(agg_values)))
                has_pricing_total = True

        if has_pricing_total:
            # Pricing rules already include materials, labor, overhead, and
            # wastage (via quantity_including_overs). Don't double-count.
            effective_total = pricing_rules_total
            labor_cost = Decimal("0")
            overhead_cost = Decimal("0")
            wastage_cost = Decimal("0")

            self._audit("base_total", "base_total", "aggregation_total(sum_from_*)",
                        {"source": "pricing_rules_aggregation",
                         "note": "uses sum_from_ to avoid double-counting"},
                        float(effective_total))
        else:
            # Fallback: compute from components independently
            material_total = sum(material_costs.values())
            default_rate = Decimal(str(self.hourly_rates.get("default", 40.0)))
            labor_cost = Decimal(str(total_labor_hours)) * default_rate
            wastage_pct = Decimal(str(inputs.complexity_tier.wastage_adjustment))
            wastage_cost = material_total * wastage_pct
            overhead_cost = labor_cost * Decimal("0.10")
            effective_total = material_total + labor_cost + wastage_cost

            self._audit("base_total", "base_total", "material + labor + wastage",
                        {"material": float(material_total), "labor": float(labor_cost),
                         "wastage": float(wastage_cost)},
                        float(effective_total))
            self._audit("wastage", "wastage_cost", "material_total * wastage_rate",
                        {"material_total": float(material_total),
                         "wastage_rate": float(wastage_pct)},
                        float(wastage_cost))

        # Complexity adjustment (risk premium on top of base)
        complexity_adjustment = effective_total * Decimal(
            str(inputs.complexity_tier.multiplier - 1)
        )

        # Rush premium
        rush_premium = (
            effective_total * Decimal("0.5") if inputs.rush_order else Decimal("0")
        )

        total_cost = effective_total + complexity_adjustment + rush_premium + overhead_cost
        unit_cost = (total_cost / inputs.quantity).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP) if inputs.quantity > 0 else Decimal("0")

        # Confidence interval
        confidence_low = (total_cost * Decimal("0.90")).quantize(Decimal("0.01"))
        confidence_high = (total_cost * Decimal("1.15")).quantize(Decimal("0.01"))
        confidence_level = 0.80

        self._audit("final", "total_cost",
                    "effective_total + complexity_adjustment + rush_premium + overhead",
                    {"effective_total": float(effective_total),
                     "complexity_adjustment": float(complexity_adjustment),
                     "rush_premium": float(rush_premium),
                     "overhead": float(overhead_cost)},
                    float(total_cost))

        return CostBreakdown(
            material_costs=material_costs,
            labor_hours=labor_hours,
            labor_cost=labor_cost.quantize(Decimal("0.01")),
            overhead_cost=overhead_cost.quantize(Decimal("0.01")),
            wastage_cost=wastage_cost.quantize(Decimal("0.01")),
            complexity_adjustment=complexity_adjustment.quantize(Decimal("0.01")),
            rush_premium=rush_premium.quantize(Decimal("0.01")),
            total_cost=total_cost.quantize(Decimal("0.01")),
            unit_cost=unit_cost,
            confidence_interval=(confidence_low, confidence_high),
            confidence_level=confidence_level,
            audit_trail=[e.to_dict() for e in self._audit_trail],
        )

    def _calculate_material_costs(
        self, inputs: EstimateInputs, context: dict[str, Any]
    ) -> dict[str, Decimal]:
        """Calculate material costs from pricing rules or defaults."""
        qty_overs = context["quantity_with_overs"]

        # Try to get from pricing rules
        if self.pricing_rules is not None:
            costs = {}
            cost_features = {
                "board": "cost_per_sheet_of_dutch_grey_board",
                "liner": "cost_per_sheet_of_liner_paper",
                "glue": "glue_cost_per_binder",
                "printed_outer": "printed_and_laminated_outer_sheets",
                "printed_inner": "printed_and_laminated_inner_sheets",
                "mechanism": "mechanism",
                "pockets": "pockets",
                "magnets": "single_magnet_cost_gbp0_10_pence_each",
                "rivets": "number_of_rivets_per_binder",
                "packing": "packing_materials_per_pallete",
                "pallets": "number_of_pallets",
                "digital_foil_screen": "digital_foil_screenprinting",
                "breakage_charges": "any_breakage_charges",
                "cutting_forme": "cutting_forme_cost_if_required",
                "carriage_charges": "minimum_order_carriage_charges",
            }

            for label, var_name in cost_features.items():
                total_var = f"{var_name}_total"
                val = context.get(total_var, 0)
                if val and val != 0:
                    costs[label] = Decimal(str(val)).quantize(Decimal("0.01"))

            if costs:
                return costs

        # Fallback: estimate from material prices per sqm
        board_prices = {
            "dutch_grey_2mm": Decimal("1.30"),
            "dutch_grey_3mm": Decimal("1.80"),
            "greyboard_1.5mm": Decimal("0.90"),
            "greyboard_2mm": Decimal("1.10"),
        }
        wrap_prices = {
            "buckram_cloth": Decimal("15.00"),
            "book_cloth": Decimal("12.00"),
            "coated_paper": Decimal("6.00"),
            "leather_effect": Decimal("25.00"),
        }
        liner_prices = {
            "uncoated_paper_120gsm": Decimal("0.18"),
            "uncoated_paper_150gsm": Decimal("0.22"),
            "coated_paper_150gsm": Decimal("0.30"),
            "velvet_paper": Decimal("0.50"),
        }

        board_price = board_prices.get(inputs.materials.board_type, Decimal("1.30"))
        wrap_price = wrap_prices.get(inputs.materials.outer_wrap, Decimal("15.00"))
        liner_price = liner_prices.get(inputs.materials.liner, Decimal("0.18"))

        board_area = Decimal(str(context["flat_area_sqm"]))
        wrap_area = Decimal(str(context["outer_wrap_area_sqm"]))
        liner_area = Decimal(str(context["liner_area_sqm"]))
        glue_area = Decimal(str(context["total_glue_area_sqm"]))
        qty = Decimal(str(qty_overs))
        yield_per_sheet = Decimal(str(context["yield_per_sheet"]))
        sheets_needed = (qty / yield_per_sheet).quantize(Decimal("1"), rounding=ROUND_HALF_UP)

        return {
            "board": (sheets_needed * board_price).quantize(Decimal("0.01")),
            "outer_wrap": (qty * wrap_area * wrap_price).quantize(Decimal("0.01")),
            "liner": (qty * liner_price).quantize(Decimal("0.01")),
            "glue": (qty * glue_area * Decimal("0.10")).quantize(Decimal("0.01")),
            "additional": Decimal("0.00"),
        }

    def _fallback_total(
        self,
        inputs: EstimateInputs,
        context: dict[str, Any],
        material_costs: dict[str, Decimal],
        total_labor_hours: float,
    ) -> Decimal:
        """Calculate total when pricing rules aren't available."""
        material_total = sum(material_costs.values())
        default_rate = Decimal(str(self.hourly_rates.get("default", 40.0)))
        labor_cost = Decimal(str(total_labor_hours)) * default_rate
        wastage_cost = material_total * Decimal(str(inputs.complexity_tier.wastage_adjustment))
        return material_total + labor_cost + wastage_cost

    def _get_setup_time(self, operation: str) -> float:
        """Get setup time for an operation in hours."""
        return self.setup_times.get(operation, 0.5)

    def _get_run_time(self, operation: str, quantity: int) -> float:
        """Get run time for an operation in hours."""
        speed = self.machine_speeds.get(operation, 100)
        return quantity / speed if speed > 0 else 0

    def _get_expr_deps(self, expression: str, context: dict[str, Any]) -> list[str]:
        """Get variable names referenced in an expression that exist in context."""
        try:
            vars_in_expr = self.evaluator.get_variables(expression)
            return [v for v in vars_in_expr if v in context]
        except Exception:
            return []

    def _audit(
        self, step: str, variable: str, expression: str,
        inputs_used: dict[str, Any], result: Any,
        original_feature: Optional[str] = None,
    ) -> None:
        """Record an audit trail entry."""
        self._audit_trail.append(AuditEntry(
            step=step,
            variable=variable,
            expression=str(expression),
            inputs_used=inputs_used,
            result=result,
            original_feature=original_feature,
        ))

    def update_customer_inputs(self, updates: dict[str, Any]) -> None:
        """Apply customer-specific variable updates."""
        if self.pricing_rules is None:
            raise ValueError("Pricing rules not loaded")

        for key, value in updates.items():
            if key in self.pricing_rules.index:
                self.pricing_rules.at[key, "Multiplier"] = value
                self.pricing_rules.at[key, "Updated Multiplier"] = 1
                logger.info(f"Updated {key} to {value}")

    def get_variable(self, name: str) -> Any:
        """Get current value of a pricing variable."""
        if self.pricing_rules is None:
            raise ValueError("Pricing rules not loaded")
        if name in self.pricing_rules.index:
            return self.pricing_rules.at[name, "Multiplier"]
        raise KeyError(f"Variable not found: {name}")

    def get_total(self, name: str) -> Decimal:
        """Get calculated total for a pricing variable."""
        if self.pricing_rules is None:
            raise ValueError("Pricing rules not loaded")
        if name in self.pricing_rules.index:
            return Decimal(str(self.pricing_rules.at[name, "TOTAL (£)"]))
        raise KeyError(f"Variable not found: {name}")


def create_estimate(
    inputs: EstimateInputs,
    pricing_rules_df: Optional[pd.DataFrame] = None,
) -> CostBreakdown:
    """
    Convenience function to create an estimate.

    Args:
        inputs: EstimateInputs with all job parameters.
        pricing_rules_df: DataFrame with pricing rules (optional).

    Returns:
        CostBreakdown with itemized costs.
    """
    engine = CalculationEngine(pricing_rules_df)
    return engine.calculate(inputs)
