"""
SafeExpressionEvaluator - AST-based safe expression evaluation.

Replaces dangerous eval() calls with a secure AST parser that only
allows mathematical operations and approved functions.

Security Features:
- No code execution (eval/exec blocked)
- No imports or module access
- No file system access
- No dunder attribute access
- Whitelist-only functions
- Variable interpolation only from provided context

Usage:
    evaluator = SafeExpressionEvaluator()
    result = evaluator.evaluate(
        "quantity * unit_price * (1 + wastage_rate)",
        {"quantity": 1000, "unit_price": 0.50, "wastage_rate": 0.05}
    )
    # result = 525.0
"""

import ast
import math
import operator
from decimal import Decimal
from typing import Any, Callable, Dict, Optional, Set, Union

Number = Union[int, float, Decimal]


class ExpressionSecurityError(Exception):
    """Raised when an expression contains potentially dangerous patterns."""

    pass


class ExpressionSyntaxError(Exception):
    """Raised when an expression has invalid syntax."""

    pass


class ExpressionEvaluationError(Exception):
    """Raised when expression evaluation fails."""

    pass


class SafeExpressionEvaluator:
    """
    Safely evaluate mathematical expressions without using eval().

    Supports:
    - Arithmetic: +, -, *, /, //, %, **
    - Unary: -, +
    - Comparison: <, <=, >, >=, ==, !=
    - Boolean: and, or, not
    - Conditionals: if/else expressions (ternary)
    - Functions: min, max, round, abs, ceil, floor, sqrt, pow
    - Constants: pi, e
    - Variables: referenced by name from context dict

    Does NOT support:
    - Function definitions
    - Class definitions
    - Imports
    - Attribute access (except for safe constants)
    - Subscript access (list/dict indexing)
    - Comprehensions
    - Lambdas
    - Assignments
    """

    # Allowed binary operators
    BINARY_OPS: Dict[type, Callable[[Any, Any], Any]] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.LShift: operator.lshift,
        ast.RShift: operator.rshift,
        ast.BitOr: operator.or_,
        ast.BitXor: operator.xor,
        ast.BitAnd: operator.and_,
    }

    # Allowed comparison operators
    COMPARE_OPS: Dict[type, Callable[[Any, Any], bool]] = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
    }

    # Allowed unary operators
    UNARY_OPS: Dict[type, Callable[[Any], Any]] = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
        ast.Not: operator.not_,
    }

    # Allowed boolean operators
    BOOL_OPS: Dict[type, Callable[[Any, Any], Any]] = {
        ast.And: lambda a, b: a and b,
        ast.Or: lambda a, b: a or b,
    }

    # Safe functions (whitelist)
    SAFE_FUNCTIONS: Dict[str, Callable] = {
        # Math functions
        "min": min,
        "max": max,
        "abs": abs,
        "round": round,
        "ceil": math.ceil,
        "floor": math.floor,
        "sqrt": math.sqrt,
        "pow": pow,
        "log": math.log,
        "log10": math.log10,
        "exp": math.exp,
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        # Type conversions
        "int": int,
        "float": float,
        # Utility
        "len": len,
        "sum": sum,
    }

    # Safe constants
    SAFE_CONSTANTS: Dict[str, Any] = {
        "pi": math.pi,
        "e": math.e,
        "True": True,
        "False": False,
        "None": None,
    }

    # Dangerous patterns to block (case-insensitive check on raw string)
    BLOCKED_PATTERNS: Set[str] = {
        "__",  # Dunder access
        "import",  # Imports
        "exec",  # Code execution
        "eval",  # Code evaluation
        "compile",  # Code compilation
        "open",  # File access
        "file",  # File objects
        "input",  # User input
        "globals",  # Global namespace
        "locals",  # Local namespace
        "vars",  # Variable introspection
        "dir",  # Directory listing
        "getattr",  # Attribute access
        "setattr",  # Attribute modification
        "delattr",  # Attribute deletion
        "hasattr",  # Attribute check
        "type",  # Type introspection
        "isinstance",  # Type checking (could leak info)
        "issubclass",  # Type checking
        "classmethod",  # Class methods
        "staticmethod",  # Static methods
        "property",  # Property access
        "super",  # Super class access
        "object",  # Base object
        "os.",  # OS module
        "sys.",  # Sys module
        "subprocess",  # Subprocess
        "shutil",  # Shell utilities
        "pathlib",  # Path operations
        "builtins",  # Builtins access
        "breakpoint",  # Debugger
        "help",  # Help system
        "credits",  # Credits
        "license",  # License
        "copyright",  # Copyright
    }

    def __init__(self, max_expression_length: int = 1000):
        """
        Initialize the evaluator.

        Args:
            max_expression_length: Maximum allowed expression length in characters.
        """
        self.max_expression_length = max_expression_length

    def validate_expression(self, expression: str) -> None:
        """
        Validate expression for dangerous patterns before parsing.

        Args:
            expression: The expression string to validate.

        Raises:
            ExpressionSecurityError: If dangerous patterns detected.
            ExpressionSyntaxError: If expression is too long or empty.
        """
        if not expression or not expression.strip():
            raise ExpressionSyntaxError("Expression cannot be empty")

        if len(expression) > self.max_expression_length:
            raise ExpressionSyntaxError(
                f"Expression exceeds maximum length of {self.max_expression_length}"
            )

        # Check for blocked patterns (case-insensitive)
        expression_lower = expression.lower()
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in expression_lower:
                raise ExpressionSecurityError(
                    f"Expression contains blocked pattern: '{pattern}'"
                )

    def evaluate(
        self,
        expression: str,
        variables: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Safely evaluate a mathematical expression.

        Args:
            expression: The expression to evaluate (e.g., "x * 2 + y").
            variables: Dictionary of variable names to values.

        Returns:
            The result of evaluating the expression.

        Raises:
            ExpressionSecurityError: If expression contains dangerous patterns.
            ExpressionSyntaxError: If expression has invalid syntax.
            ExpressionEvaluationError: If evaluation fails.

        Examples:
            >>> evaluator = SafeExpressionEvaluator()
            >>> evaluator.evaluate("2 + 2")
            4
            >>> evaluator.evaluate("x * y", {"x": 3, "y": 4})
            12
            >>> evaluator.evaluate("max(a, b) * 2", {"a": 5, "b": 3})
            10
            >>> evaluator.evaluate("price * quantity * (1 + tax_rate)",
            ...                    {"price": 100, "quantity": 5, "tax_rate": 0.2})
            600.0
        """
        variables = variables or {}

        # Validate before parsing
        self.validate_expression(expression)

        try:
            # Parse expression into AST
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as e:
            raise ExpressionSyntaxError(f"Invalid expression syntax: {e}")

        try:
            # Evaluate the AST
            return self._eval_node(tree.body, variables)
        except ExpressionSecurityError:
            raise
        except ZeroDivisionError:
            raise ExpressionEvaluationError("Division by zero")
        except (TypeError, ValueError) as e:
            raise ExpressionEvaluationError(f"Evaluation error: {e}")
        except Exception as e:
            raise ExpressionEvaluationError(f"Unexpected error: {e}")

    def _eval_node(self, node: ast.AST, variables: Dict[str, Any]) -> Any:
        """
        Recursively evaluate an AST node.

        Args:
            node: The AST node to evaluate.
            variables: Variable context dictionary.

        Returns:
            The evaluated value.
        """
        # Numeric literals
        if isinstance(node, ast.Constant):
            return node.value

        # Variable names
        if isinstance(node, ast.Name):
            name = node.id

            # Check user-provided variables first (can override constants)
            if name in variables:
                return variables[name]

            # Check safe constants
            if name in self.SAFE_CONSTANTS:
                return self.SAFE_CONSTANTS[name]

            # Check safe functions (for bare references)
            if name in self.SAFE_FUNCTIONS:
                return self.SAFE_FUNCTIONS[name]

            raise ExpressionEvaluationError(f"Unknown variable: '{name}'")

        # Binary operations (+, -, *, /, etc.)
        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in self.BINARY_OPS:
                raise ExpressionSecurityError(f"Unsupported operator: {op_type.__name__}")

            left = self._eval_node(node.left, variables)
            right = self._eval_node(node.right, variables)
            return self.BINARY_OPS[op_type](left, right)

        # Unary operations (-, +, not)
        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in self.UNARY_OPS:
                raise ExpressionSecurityError(f"Unsupported unary operator: {op_type.__name__}")

            operand = self._eval_node(node.operand, variables)
            return self.UNARY_OPS[op_type](operand)

        # Comparison operations (<, >, ==, etc.)
        if isinstance(node, ast.Compare):
            left = self._eval_node(node.left, variables)

            for op, comparator in zip(node.ops, node.comparators):
                op_type = type(op)
                if op_type not in self.COMPARE_OPS:
                    raise ExpressionSecurityError(
                        f"Unsupported comparison: {op_type.__name__}"
                    )

                right = self._eval_node(comparator, variables)
                if not self.COMPARE_OPS[op_type](left, right):
                    return False
                left = right

            return True

        # Boolean operations (and, or)
        if isinstance(node, ast.BoolOp):
            op_type = type(node.op)
            if op_type not in self.BOOL_OPS:
                raise ExpressionSecurityError(f"Unsupported boolean operator: {op_type.__name__}")

            result = self._eval_node(node.values[0], variables)
            for value in node.values[1:]:
                result = self.BOOL_OPS[op_type](result, self._eval_node(value, variables))
            return result

        # Conditional expressions (x if condition else y)
        if isinstance(node, ast.IfExp):
            condition = self._eval_node(node.test, variables)
            if condition:
                return self._eval_node(node.body, variables)
            else:
                return self._eval_node(node.orelse, variables)

        # Function calls
        if isinstance(node, ast.Call):
            # Get function name
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            else:
                raise ExpressionSecurityError("Only simple function calls are allowed")

            # Check if function is allowed
            if func_name not in self.SAFE_FUNCTIONS:
                raise ExpressionSecurityError(f"Function not allowed: '{func_name}'")

            # Evaluate arguments
            args = [self._eval_node(arg, variables) for arg in node.args]

            # Evaluate keyword arguments
            kwargs = {}
            for keyword in node.keywords:
                if keyword.arg is None:
                    raise ExpressionSecurityError("**kwargs not allowed in function calls")
                kwargs[keyword.arg] = self._eval_node(keyword.value, variables)

            # Call the function
            return self.SAFE_FUNCTIONS[func_name](*args, **kwargs)

        # Tuples (for multi-value returns like divmod)
        if isinstance(node, ast.Tuple):
            return tuple(self._eval_node(el, variables) for el in node.elts)

        # Lists (for functions like sum([1, 2, 3]))
        if isinstance(node, ast.List):
            return [self._eval_node(el, variables) for el in node.elts]

        # Reject everything else
        raise ExpressionSecurityError(f"Unsupported expression type: {type(node).__name__}")

    def get_variables(self, expression: str) -> Set[str]:
        """
        Extract variable names from an expression.

        Args:
            expression: The expression to analyze.

        Returns:
            Set of variable names used in the expression.

        Example:
            >>> evaluator.get_variables("x * y + z")
            {'x', 'y', 'z'}
        """
        self.validate_expression(expression)

        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as e:
            raise ExpressionSyntaxError(f"Invalid expression syntax: {e}")

        variables: Set[str] = set()
        self._collect_variables(tree.body, variables)
        return variables

    def _collect_variables(self, node: ast.AST, variables: Set[str]) -> None:
        """Recursively collect variable names from AST."""
        if isinstance(node, ast.Name):
            name = node.id
            # Exclude constants and functions
            if name not in self.SAFE_CONSTANTS and name not in self.SAFE_FUNCTIONS:
                variables.add(name)
        elif isinstance(node, ast.AST):
            for child in ast.iter_child_nodes(node):
                self._collect_variables(child, variables)


# Convenience function for simple evaluations
def safe_eval(expression: str, variables: Optional[Dict[str, Any]] = None) -> Any:
    """
    Convenience function for safe expression evaluation.

    Args:
        expression: Mathematical expression to evaluate.
        variables: Optional variable context.

    Returns:
        Result of evaluation.

    Example:
        >>> safe_eval("2 * (3 + 4)")
        14
        >>> safe_eval("price * qty", {"price": 10, "qty": 5})
        50
    """
    evaluator = SafeExpressionEvaluator()
    return evaluator.evaluate(expression, variables)
