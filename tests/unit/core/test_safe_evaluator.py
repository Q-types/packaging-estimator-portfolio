"""
Comprehensive tests for SafeExpressionEvaluator.

Tests cover:
1. Basic arithmetic operations
2. Variable substitution
3. Function calls
4. Conditional expressions
5. Security - blocking dangerous patterns
6. Edge cases and error handling
"""

import math
import pytest

from backend.app.core.safe_evaluator import (
    ExpressionEvaluationError,
    ExpressionSecurityError,
    ExpressionSyntaxError,
    SafeExpressionEvaluator,
    safe_eval,
)


@pytest.fixture
def evaluator():
    """Create a fresh evaluator instance."""
    return SafeExpressionEvaluator()


class TestBasicArithmetic:
    """Test basic arithmetic operations."""

    def test_addition(self, evaluator):
        assert evaluator.evaluate("2 + 3") == 5
        assert evaluator.evaluate("0 + 0") == 0
        assert evaluator.evaluate("-5 + 10") == 5

    def test_subtraction(self, evaluator):
        assert evaluator.evaluate("10 - 3") == 7
        assert evaluator.evaluate("5 - 10") == -5
        assert evaluator.evaluate("0 - 0") == 0

    def test_multiplication(self, evaluator):
        assert evaluator.evaluate("4 * 5") == 20
        assert evaluator.evaluate("0 * 100") == 0
        assert evaluator.evaluate("-3 * 4") == -12

    def test_division(self, evaluator):
        assert evaluator.evaluate("10 / 2") == 5.0
        assert evaluator.evaluate("7 / 2") == 3.5
        assert evaluator.evaluate("-10 / 2") == -5.0

    def test_floor_division(self, evaluator):
        assert evaluator.evaluate("7 // 2") == 3
        assert evaluator.evaluate("10 // 3") == 3
        assert evaluator.evaluate("-7 // 2") == -4

    def test_modulo(self, evaluator):
        assert evaluator.evaluate("10 % 3") == 1
        assert evaluator.evaluate("15 % 5") == 0
        assert evaluator.evaluate("7 % 2") == 1

    def test_power(self, evaluator):
        assert evaluator.evaluate("2 ** 3") == 8
        assert evaluator.evaluate("3 ** 2") == 9
        assert evaluator.evaluate("2 ** 0") == 1

    def test_unary_minus(self, evaluator):
        assert evaluator.evaluate("-5") == -5
        assert evaluator.evaluate("--5") == 5
        assert evaluator.evaluate("-(-3)") == 3

    def test_unary_plus(self, evaluator):
        assert evaluator.evaluate("+5") == 5
        assert evaluator.evaluate("+-5") == -5

    def test_complex_expressions(self, evaluator):
        assert evaluator.evaluate("2 + 3 * 4") == 14  # Precedence
        assert evaluator.evaluate("(2 + 3) * 4") == 20  # Parentheses
        assert evaluator.evaluate("10 / 2 + 3 * 4 - 1") == 16.0
        assert evaluator.evaluate("2 ** 3 ** 2") == 512  # Right associative

    def test_floating_point(self, evaluator):
        assert evaluator.evaluate("1.5 + 2.5") == 4.0
        assert evaluator.evaluate("3.14159 * 2") == pytest.approx(6.28318, rel=1e-4)
        assert evaluator.evaluate("0.1 + 0.2") == pytest.approx(0.3, rel=1e-9)


class TestVariables:
    """Test variable substitution."""

    def test_single_variable(self, evaluator):
        assert evaluator.evaluate("x", {"x": 10}) == 10
        assert evaluator.evaluate("x", {"x": 0}) == 0
        assert evaluator.evaluate("x", {"x": -5}) == -5

    def test_multiple_variables(self, evaluator):
        assert evaluator.evaluate("x + y", {"x": 3, "y": 4}) == 7
        assert evaluator.evaluate("x * y * z", {"x": 2, "y": 3, "z": 4}) == 24

    def test_variable_in_expression(self, evaluator):
        assert evaluator.evaluate("2 * x + 1", {"x": 5}) == 11
        assert evaluator.evaluate("(x + y) * z", {"x": 1, "y": 2, "z": 3}) == 9

    def test_descriptive_variable_names(self, evaluator):
        """Test with realistic variable names from pricing model."""
        variables = {
            "quantity": 1000,
            "unit_price": 0.50,
            "wastage_rate": 0.05,
            "setup_cost": 25.00,
        }
        result = evaluator.evaluate(
            "quantity * unit_price * (1 + wastage_rate) + setup_cost", variables
        )
        assert result == pytest.approx(550.0)

    def test_undefined_variable(self, evaluator):
        with pytest.raises(ExpressionEvaluationError, match="Unknown variable"):
            evaluator.evaluate("x + y", {"x": 5})

    def test_variable_shadows_constant(self, evaluator):
        """User variable should take precedence over constants."""
        assert evaluator.evaluate("pi", {"pi": 3}) == 3


class TestFunctions:
    """Test safe function calls."""

    def test_min_max(self, evaluator):
        assert evaluator.evaluate("min(3, 5)") == 3
        assert evaluator.evaluate("max(3, 5)") == 5
        assert evaluator.evaluate("min(1, 2, 3, 4)") == 1
        assert evaluator.evaluate("max(1, 2, 3, 4)") == 4

    def test_abs(self, evaluator):
        assert evaluator.evaluate("abs(-5)") == 5
        assert evaluator.evaluate("abs(5)") == 5
        assert evaluator.evaluate("abs(0)") == 0

    def test_round(self, evaluator):
        assert evaluator.evaluate("round(3.7)") == 4
        assert evaluator.evaluate("round(3.2)") == 3
        assert evaluator.evaluate("round(3.14159, 2)") == 3.14

    def test_ceil_floor(self, evaluator):
        assert evaluator.evaluate("ceil(3.1)") == 4
        assert evaluator.evaluate("floor(3.9)") == 3
        assert evaluator.evaluate("ceil(-3.1)") == -3
        assert evaluator.evaluate("floor(-3.9)") == -4

    def test_sqrt(self, evaluator):
        assert evaluator.evaluate("sqrt(16)") == 4.0
        assert evaluator.evaluate("sqrt(2)") == pytest.approx(1.41421, rel=1e-4)

    def test_pow(self, evaluator):
        assert evaluator.evaluate("pow(2, 3)") == 8
        assert evaluator.evaluate("pow(10, 2)") == 100

    def test_log(self, evaluator):
        assert evaluator.evaluate("log(e)") == pytest.approx(1.0)
        assert evaluator.evaluate("log10(100)") == pytest.approx(2.0)

    def test_trig(self, evaluator):
        assert evaluator.evaluate("sin(0)") == pytest.approx(0.0)
        assert evaluator.evaluate("cos(0)") == pytest.approx(1.0)
        assert evaluator.evaluate("sin(pi / 2)") == pytest.approx(1.0)

    def test_int_float(self, evaluator):
        assert evaluator.evaluate("int(3.7)") == 3
        assert evaluator.evaluate("float(5)") == 5.0

    def test_sum(self, evaluator):
        assert evaluator.evaluate("sum([1, 2, 3, 4])") == 10

    def test_function_with_variables(self, evaluator):
        assert evaluator.evaluate("max(x, y)", {"x": 10, "y": 5}) == 10
        assert evaluator.evaluate("round(price, 2)", {"price": 19.999}) == 20.0

    def test_nested_functions(self, evaluator):
        assert evaluator.evaluate("max(min(5, 10), 3)") == 5
        assert evaluator.evaluate("round(sqrt(2), 3)") == 1.414

    def test_disallowed_function(self, evaluator):
        with pytest.raises(ExpressionSecurityError, match="Function not allowed"):
            evaluator.evaluate("print('hello')")


class TestComparisons:
    """Test comparison operations."""

    def test_less_than(self, evaluator):
        assert evaluator.evaluate("3 < 5") is True
        assert evaluator.evaluate("5 < 3") is False
        assert evaluator.evaluate("3 < 3") is False

    def test_less_than_equal(self, evaluator):
        assert evaluator.evaluate("3 <= 5") is True
        assert evaluator.evaluate("3 <= 3") is True
        assert evaluator.evaluate("5 <= 3") is False

    def test_greater_than(self, evaluator):
        assert evaluator.evaluate("5 > 3") is True
        assert evaluator.evaluate("3 > 5") is False

    def test_greater_than_equal(self, evaluator):
        assert evaluator.evaluate("5 >= 3") is True
        assert evaluator.evaluate("3 >= 3") is True

    def test_equal(self, evaluator):
        assert evaluator.evaluate("3 == 3") is True
        assert evaluator.evaluate("3 == 4") is False

    def test_not_equal(self, evaluator):
        assert evaluator.evaluate("3 != 4") is True
        assert evaluator.evaluate("3 != 3") is False

    def test_chained_comparisons(self, evaluator):
        assert evaluator.evaluate("1 < 2 < 3") is True
        assert evaluator.evaluate("1 < 2 > 3") is False
        assert evaluator.evaluate("1 <= 1 < 2") is True


class TestBooleanOperations:
    """Test boolean operations."""

    def test_and(self, evaluator):
        assert evaluator.evaluate("True and True") is True
        assert evaluator.evaluate("True and False") is False
        assert evaluator.evaluate("False and True") is False

    def test_or(self, evaluator):
        assert evaluator.evaluate("True or False") is True
        assert evaluator.evaluate("False or True") is True
        assert evaluator.evaluate("False or False") is False

    def test_not(self, evaluator):
        assert evaluator.evaluate("not True") is False
        assert evaluator.evaluate("not False") is True

    def test_combined_boolean(self, evaluator):
        assert evaluator.evaluate("True and True or False") is True
        assert evaluator.evaluate("not (True and False)") is True

    def test_comparison_with_boolean(self, evaluator):
        assert evaluator.evaluate("3 < 5 and 2 > 1") is True
        assert evaluator.evaluate("3 > 5 or 2 > 1") is True


class TestConditionals:
    """Test conditional (ternary) expressions."""

    def test_simple_conditional(self, evaluator):
        assert evaluator.evaluate("5 if True else 10") == 5
        assert evaluator.evaluate("5 if False else 10") == 10

    def test_conditional_with_comparison(self, evaluator):
        assert evaluator.evaluate("'big' if x > 10 else 'small'", {"x": 15}) == "big"
        assert evaluator.evaluate("'big' if x > 10 else 'small'", {"x": 5}) == "small"

    def test_conditional_with_calculation(self, evaluator):
        assert evaluator.evaluate("x * 2 if x > 0 else 0", {"x": 5}) == 10
        assert evaluator.evaluate("x * 2 if x > 0 else 0", {"x": -5}) == 0

    def test_nested_conditional(self, evaluator):
        expr = "1 if x < 0 else (2 if x == 0 else 3)"
        assert evaluator.evaluate(expr, {"x": -1}) == 1
        assert evaluator.evaluate(expr, {"x": 0}) == 2
        assert evaluator.evaluate(expr, {"x": 1}) == 3


class TestConstants:
    """Test mathematical constants."""

    def test_pi(self, evaluator):
        assert evaluator.evaluate("pi") == pytest.approx(math.pi)
        assert evaluator.evaluate("2 * pi") == pytest.approx(2 * math.pi)

    def test_e(self, evaluator):
        assert evaluator.evaluate("e") == pytest.approx(math.e)

    def test_true_false_none(self, evaluator):
        assert evaluator.evaluate("True") is True
        assert evaluator.evaluate("False") is False
        assert evaluator.evaluate("None") is None


class TestSecurity:
    """Test security measures against malicious expressions."""

    def test_block_eval(self, evaluator):
        with pytest.raises(ExpressionSecurityError, match="blocked pattern"):
            evaluator.evaluate("eval('1+1')")

    def test_block_exec(self, evaluator):
        with pytest.raises(ExpressionSecurityError, match="blocked pattern"):
            evaluator.evaluate("exec('print(1)')")

    def test_block_import(self, evaluator):
        with pytest.raises(ExpressionSecurityError, match="blocked pattern"):
            evaluator.evaluate("__import__('os')")

    def test_block_dunder(self, evaluator):
        with pytest.raises(ExpressionSecurityError, match="blocked pattern"):
            evaluator.evaluate("''.__class__")

    def test_block_open(self, evaluator):
        with pytest.raises(ExpressionSecurityError, match="blocked pattern"):
            evaluator.evaluate("open('/etc/passwd')")

    def test_block_os_access(self, evaluator):
        with pytest.raises(ExpressionSecurityError, match="blocked pattern"):
            evaluator.evaluate("os.system('ls')")

    def test_block_subprocess(self, evaluator):
        with pytest.raises(ExpressionSecurityError, match="blocked pattern"):
            evaluator.evaluate("subprocess.call(['ls'])")

    def test_block_globals(self, evaluator):
        with pytest.raises(ExpressionSecurityError, match="blocked pattern"):
            evaluator.evaluate("globals()")

    def test_block_getattr(self, evaluator):
        with pytest.raises(ExpressionSecurityError, match="blocked pattern"):
            evaluator.evaluate("getattr(object, '__class__')")

    def test_block_builtins(self, evaluator):
        with pytest.raises(ExpressionSecurityError, match="blocked pattern"):
            evaluator.evaluate("__builtins__")

    def test_block_attribute_access(self, evaluator):
        """Attribute access should fail at AST level."""
        with pytest.raises(ExpressionSecurityError, match="Unsupported expression"):
            evaluator.evaluate("x.y", {"x": {"y": 1}})

    def test_block_subscript(self, evaluator):
        """Subscript access should fail at AST level."""
        with pytest.raises(ExpressionSecurityError, match="Unsupported expression"):
            evaluator.evaluate("x[0]", {"x": [1, 2, 3]})

    def test_block_lambda(self, evaluator):
        """Lambda expressions should fail at AST level."""
        with pytest.raises(ExpressionSecurityError, match="Only simple function calls are allowed"):
            evaluator.evaluate("(lambda x: x + 1)(5)")

    def test_block_comprehension(self, evaluator):
        """List comprehensions should fail at AST level."""
        with pytest.raises(ExpressionSecurityError, match="Unsupported expression"):
            evaluator.evaluate("[x for x in range(10)]")

    def test_max_expression_length(self):
        """Test expression length limit."""
        evaluator = SafeExpressionEvaluator(max_expression_length=50)
        long_expr = "1 + " * 20 + "1"  # 81 characters
        with pytest.raises(ExpressionSyntaxError, match="exceeds maximum length"):
            evaluator.evaluate(long_expr)


class TestErrorHandling:
    """Test error handling."""

    def test_empty_expression(self, evaluator):
        with pytest.raises(ExpressionSyntaxError, match="cannot be empty"):
            evaluator.evaluate("")

    def test_whitespace_only(self, evaluator):
        with pytest.raises(ExpressionSyntaxError, match="cannot be empty"):
            evaluator.evaluate("   ")

    def test_invalid_syntax(self, evaluator):
        with pytest.raises(ExpressionSyntaxError, match="Invalid expression syntax"):
            evaluator.evaluate("2 + * 3")

    def test_unclosed_parenthesis(self, evaluator):
        with pytest.raises(ExpressionSyntaxError, match="Invalid expression syntax"):
            evaluator.evaluate("(2 + 3")

    def test_division_by_zero(self, evaluator):
        with pytest.raises(ExpressionEvaluationError, match="Division by zero"):
            evaluator.evaluate("1 / 0")

    def test_invalid_function_args(self, evaluator):
        with pytest.raises(ExpressionEvaluationError):
            evaluator.evaluate("sqrt(-1)")  # Domain error


class TestGetVariables:
    """Test variable extraction."""

    def test_simple_variables(self, evaluator):
        assert evaluator.get_variables("x + y") == {"x", "y"}

    def test_no_variables(self, evaluator):
        assert evaluator.get_variables("2 + 3") == set()

    def test_exclude_functions(self, evaluator):
        assert evaluator.get_variables("max(x, y)") == {"x", "y"}

    def test_exclude_constants(self, evaluator):
        assert evaluator.get_variables("x + pi") == {"x"}

    def test_complex_expression(self, evaluator):
        expr = "quantity * price * (1 + tax_rate)"
        assert evaluator.get_variables(expr) == {"quantity", "price", "tax_rate"}


class TestRealWorldExpressions:
    """Test expressions from actual pricing model."""

    def test_wastage_calculation(self, evaluator):
        """Wastage = quantity * 0.05 + 50"""
        expr = "quantity * 0.05 + 50"
        assert evaluator.evaluate(expr, {"quantity": 1000}) == 100.0

    def test_board_area_calculation(self, evaluator):
        """Board area = (width + 2*margin) * (height + 2*margin)"""
        expr = "(width + 2 * margin) * (height + 2 * margin)"
        result = evaluator.evaluate(expr, {"width": 300, "height": 400, "margin": 10})
        assert result == 320 * 420

    def test_machine_time_calculation(self, evaluator):
        """Time = setup_time + (quantity / machine_speed)"""
        expr = "setup_time + (quantity / machine_speed)"
        result = evaluator.evaluate(
            expr, {"setup_time": 30, "quantity": 1000, "machine_speed": 200}
        )
        assert result == 35.0

    def test_cost_with_yield(self, evaluator):
        """Cost adjusted for yield: base_cost / first_pass_yield"""
        expr = "base_cost / first_pass_yield"
        result = evaluator.evaluate(expr, {"base_cost": 100, "first_pass_yield": 0.95})
        assert result == pytest.approx(105.26, rel=0.01)

    def test_complexity_multiplier(self, evaluator):
        """Cost with complexity tier multiplier."""
        expr = "base_cost * (1 + (complexity_tier - 1) * 0.1)"
        assert evaluator.evaluate(expr, {"base_cost": 100, "complexity_tier": 1}) == 100
        assert evaluator.evaluate(expr, {"base_cost": 100, "complexity_tier": 3}) == 120
        assert evaluator.evaluate(expr, {"base_cost": 100, "complexity_tier": 5}) == 140

    def test_conditional_pricing(self, evaluator):
        """Rush order premium."""
        expr = "base_price * 1.5 if rush_order else base_price"
        assert evaluator.evaluate(expr, {"base_price": 100, "rush_order": True}) == 150
        assert evaluator.evaluate(expr, {"base_price": 100, "rush_order": False}) == 100


class TestSafeEvalFunction:
    """Test the convenience safe_eval function."""

    def test_simple_eval(self):
        assert safe_eval("2 + 2") == 4

    def test_with_variables(self):
        assert safe_eval("x * y", {"x": 3, "y": 4}) == 12

    def test_security(self):
        with pytest.raises(ExpressionSecurityError):
            safe_eval("eval('1')")
