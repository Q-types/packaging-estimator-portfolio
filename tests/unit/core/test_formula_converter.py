"""Tests for the formula converter module."""

import pytest

from backend.app.core.formula_converter import (
    _feature_to_var,
    build_feature_index,
    convert_formula,
    convert_pricing_model,
)


class TestFeatureToVar:
    """Test feature name to variable name conversion."""

    def test_simple_name(self):
        assert _feature_to_var("ADMIN (number)") == "admin"

    def test_multi_word(self):
        assert _feature_to_var("QUANTITY REQUIRED BY CUSTOMER (number)") == "quantity_required_by_customer"

    def test_with_units(self):
        assert _feature_to_var("FLAT SIZE Length (mm)") == "flat_size_length"

    def test_with_suffix(self):
        assert _feature_to_var("SET UP POB MACHINE (hours).1") == "set_up_pob_machine_1"

    def test_with_special_chars(self):
        result = _feature_to_var("COST/RATE (£)")
        assert "cost" in result and "rate" in result

    def test_with_caret(self):
        result = _feature_to_var("Area (m^2)")
        assert "pow" in result or "area" in result


class TestBuildFeatureIndex:
    """Test building the feature name to variable mapping."""

    def test_basic_index(self):
        features = [
            "ADMIN (number)",
            "QUANTITY REQUIRED BY CUSTOMER (number)",
            "FLAT SIZE Length (mm)",
        ]
        index = build_feature_index(features)
        assert len(index) == 3
        assert "ADMIN (number)" in index
        assert index["ADMIN (number)"] == "admin"

    def test_handles_duplicates(self):
        features = [
            "SET UP POB MACHINE (hours)",
            "SET UP POB MACHINE (hours).1",
        ]
        index = build_feature_index(features)
        assert len(index) == 2
        vars_set = set(index.values())
        assert len(vars_set) == 2  # Should be unique


class TestConvertFormula:
    """Test converting legacy df.loc expressions."""

    @pytest.fixture
    def feature_index(self):
        return build_feature_index([
            "QUANTITY REQUIRED BY CUSTOMER (number)",
            "QUANTITY INCLUDING OVERS (number)",
            "FLAT SIZE Length (mm)",
            "FLAT SIZE Width (mm)",
            "FLAT SIZE Area (m^2)",
            "MECHANISM (number)",
            "ADMIN (number)",
        ])

    def test_simple_self_reference(self, feature_index):
        expr = 'df.loc["ADMIN (number)", "Multiplier"]'
        result = convert_formula(expr, feature_index)
        assert result == "admin"

    def test_multiply_two_features(self, feature_index):
        expr = 'df.loc["FLAT SIZE Length (mm)", "Multiplier"]*df.loc["FLAT SIZE Width (mm)", "Multiplier"]/1000000'
        result = convert_formula(expr, feature_index)
        assert "flat_size_length" in result
        assert "flat_size_width" in result
        assert "1000000" in result

    def test_numpy_ceil(self, feature_index):
        expr = 'np.ceil(df.loc["QUANTITY INCLUDING OVERS (number)", "Multiplier"]/df.loc["FLAT SIZE Area (m^2)", "Multiplier"])'
        result = convert_formula(expr, feature_index)
        assert result.startswith("ceil(")
        assert "quantity_including_overs" in result

    def test_numpy_round(self, feature_index):
        expr = 'np.round(df.loc["QUANTITY REQUIRED BY CUSTOMER (number)", "Multiplier"]/1000)'
        result = convert_formula(expr, feature_index)
        assert result.startswith("round(")

    def test_cost_rate_reference(self, feature_index):
        expr = 'df.loc["ADMIN (number)", "Multiplier"]*df.loc["ADMIN (number)", "COST/RATE (£)"]'
        result = convert_formula(expr, feature_index)
        assert "admin" in result
        assert "_costrate" in result

    def test_total_reference(self, feature_index):
        expr = 'df.loc["MECHANISM (number)", "TOTAL (£)"]'
        result = convert_formula(expr, feature_index)
        assert "mechanism_total" in result

    def test_sum_from_pattern(self, feature_index):
        expr = 'df.loc["MECHANISM (number)": , "TOTAL (£)"].sum()'
        result = convert_formula(expr, feature_index)
        assert result.startswith("sum_from_")

    def test_simple_arithmetic(self, feature_index):
        expr = "1/60*3"
        result = convert_formula(expr, feature_index)
        assert result == "1/60*3"

    def test_addition_offset(self, feature_index):
        expr = 'df.loc["FLAT SIZE Length (mm)", "Multiplier"]+40'
        result = convert_formula(expr, feature_index)
        assert "flat_size_length" in result
        assert "+40" in result

    def test_none_input(self, feature_index):
        assert convert_formula(None, feature_index) is None
        assert convert_formula("", feature_index) is None

    def test_multiplier_times_constant(self, feature_index):
        expr = 'df.loc["QUANTITY REQUIRED BY CUSTOMER (number)", "Multiplier"]*1.05+50'
        result = convert_formula(expr, feature_index)
        assert "quantity_required_by_customer" in result
        assert "*1.05" in result
        assert "+50" in result
