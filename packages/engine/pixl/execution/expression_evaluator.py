"""PixlExpr expression evaluator.

Restricted expression evaluator for edge conditions.
Security rule: NEVER eval Python code.

Supported syntax:
- Boolean ops: and, or, not
- Comparisons: ==, !=, <, >, <=, >=
- Functions: result(), failure_kind(), artifact_exists(), attempt(), payload()

NO: arbitrary Python execution, imports, or complex logic.
"""

import operator
import re
from pathlib import Path
from typing import Any

class PixlExprEvaluator:
    """Restricted expression evaluator for edge conditions.

    Supports a safe subset of Python expressions for evaluating
    edge traversal conditions in the workflow graph.
    """

    # Available operators
    OPERATORS = {
        "==": operator.eq,
        "!=": operator.ne,
        "<": operator.lt,
        ">": operator.gt,
        "<=": operator.le,
        ">=": operator.ge,
        "and": lambda a, b: a and b,
        "or": lambda a, b: a or b,
        "not": lambda a: not a,
    }

    def __init__(self, artifacts_dir: Path | None = None) -> None:
        """Initialize the evaluator."""
        self.artifacts_dir = artifacts_dir

    def evaluate(self, expr: str, context: dict[str, Any] | None = None) -> bool:
        """Evaluate an expression in the given context.

        Args:
            expr: Expression string (e.g., 'attempt < 3')
            context: Execution context with keys:
                - result_state: "success", "failed", "skipped"
                - failure_kind: "transient", "fatal", or None
                - attempt: Current attempt number
                - artifacts: List of artifact names

        Returns:
            True if expression evaluates to True

        Raises:
            ValueError: If expression is invalid
        """
        if context is None:
            context = {}

        try:
            # Tokenize and parse the expression
            tokens = self._tokenize(expr)
            ast = self._parse(tokens)

            # Evaluate the AST
            return bool(self._eval_ast(ast, context))
        except Exception as e:
            raise ValueError(f"Failed to evaluate expression '{expr}': {e}") from e

    def _tokenize(self, expr: str) -> list[str]:
        """Tokenize an expression string."""
        # Pattern for tokens: operators, identifiers, numbers, strings, parens
        # Order matters! Parens and operators before identifiers
        pattern = r"""
            \s*(and|or|not|==|!=|<=?|>=?)\s*|          # operators (with space trimming)
            "[^"]*"|'[^']*'|                           # strings
            \d+\.?\d*|                                 # numbers
            [(),]|                                     # parens (before identifiers!)
            [a-zA-Z_][a-zA-Z0-9_]*|                    # identifiers (without parens)
            ,                                          # comma
        """

        tokens = []
        for match in re.finditer(pattern, expr, re.VERBOSE):
            token = match.group(0).strip()
            if token:
                tokens.append(token)

        return tokens

    def _parse(self, tokens: list[str]) -> dict:
        """Parse tokens into a simple AST."""
        if not tokens:
            raise ValueError("Empty expression")

        # Single value
        if len(tokens) == 1:
            return {"type": "value", "value": self._parse_value(tokens[0])}

        # Parenthesized expression
        if tokens[0] == "(" and tokens[-1] == ")":
            return self._parse(tokens[1:-1])

        # Not operator (prefix) - HIGHEST precedence for unary operator
        if tokens[0] == "not":
            return {"type": "unary", "op": "not", "operand": self._parse(tokens[1:])}

        # Binary operation - find operators with precedence
        # Must come BEFORE function call check so expressions like
        # payload('x') == 'y' are parsed as binary comparisons.
        # Logical (and/or) lowest, then comparisons
        precedence = [("and", "or"), ("==", "!=", "<=", ">=", "<", ">")]

        for precedence_group in precedence:
            for op in precedence_group:
                # Scan right-to-left, skipping tokens inside parentheses
                depth = 0
                for i in range(len(tokens) - 1, -1, -1):
                    if tokens[i] == ")":
                        depth += 1
                    elif tokens[i] == "(":
                        depth -= 1
                    elif depth == 0 and tokens[i] == op:
                        return {
                            "type": "binary",
                            "op": op,
                            "left": self._parse(tokens[:i]),
                            "right": self._parse(tokens[i + 1 :]),
                        }

        # Function call (only when no binary operator found at top level)
        if len(tokens) >= 3 and tokens[1] == "(":
            func_name = tokens[0]
            args = []
            i = 2
            while i < len(tokens) and tokens[i] != ")":
                if tokens[i] != ",":
                    args.append(self._parse_value(tokens[i]))
                i += 1

            return {"type": "function", "name": func_name, "args": args}

        raise ValueError(f"Unable to parse expression: {' '.join(tokens)}")

    def _parse_value(self, token: str) -> Any:
        """Parse a token into a value."""
        # String literal
        if (token.startswith('"') and token.endswith('"')) or (
            token.startswith("'") and token.endswith("'")
        ):
            return token[1:-1]

        # Boolean
        if token == "True":
            return True
        if token == "False":
            return False

        # None
        if token in ("None", "null"):
            return None

        # Number
        try:
            if "." in token:
                return float(token)
            return int(token)
        except ValueError:
            pass

        # Identifier (will be resolved from context)
        return token

    # Aliases for context keys
    ALIASES = {
        "result": "result_state",
        "failure_kind": "failure_kind",
        "attempt": "attempt",
    }

    def _resolve_identifier(self, identifier: str, context: dict[str, Any]) -> tuple[Any, bool]:
        """Resolve an identifier from context, using aliases.

        Returns:
            (value, found) where found indicates if identifier was in context/aliases

        Raises:
            ValueError: If identifier starts with underscore (security)
        """
        # Security check: reject private/dunder identifiers
        if identifier.startswith("_"):
            raise ValueError(f"Access to private attribute '{identifier}' is not allowed")

        if identifier in self.ALIASES:
            context_key = self.ALIASES[identifier]
            if context_key in context:
                return context[context_key], True
            # Alias exists but key not in context - return None, True
            return None, True

        # Direct lookup in context
        if identifier in context:
            return context[identifier], True

        # Not found
        return identifier, False

    def _eval_ast(self, ast: dict, context: dict[str, Any]) -> Any:
        """Evaluate an AST node."""
        node_type = ast.get("type")

        if node_type == "value":
            value = ast["value"]
            if isinstance(value, str):
                resolved, found = self._resolve_identifier(value, context)
                if found:
                    return resolved
            return value

        if node_type == "binary":
            op = ast["op"]
            left = self._eval_ast(ast["left"], context)
            right = self._eval_ast(ast["right"], context)

            if op in ("and", "or"):
                # Logical operators - need boolean result
                return self.OPERATORS[op](bool(left), bool(right))
            if op in self.OPERATORS:
                return self.OPERATORS[op](left, right)
            raise ValueError(f"Unknown operator: {op}")

        if node_type == "unary":
            op = ast["op"]
            operand = self._eval_ast(ast["operand"], context)

            if op == "not":
                return not operand
            raise ValueError(f"Unknown unary operator: {op}")

        if node_type == "function":
            func_name = ast["name"]
            args = ast["args"]

            # Security check: reject private/dunder function names
            if func_name.startswith("_"):
                raise ValueError(f"Access to private function '{func_name}' is not allowed")

            if func_name == "artifact_exists":
                artifact_name = args[0] if args else ""
                artifacts = context.get("artifacts", [])
                return artifact_name in artifacts

            if func_name == "result":
                return context.get("result_state", "success") == (args[0] if args else "success")

            if func_name == "failure_kind":
                return context.get("failure_kind") == (args[0] if args else None)

            if func_name == "attempt":
                attempt = context.get("attempt", 0)
                if args:
                    return attempt < args[0]
                return attempt

            if func_name == "payload":
                # Usage: payload('recommendation') == 'request_changes'
                payload_data = context.get("payload", {}) or {}
                field_name = args[0] if args else ""
                return payload_data.get(field_name)

            if func_name == "issues":
                # Count issues by severity from review payload.
                # Usage: issues('critical') for specific severity, issues() for total count
                payload_data = context.get("payload", {}) or {}
                issues_list = payload_data.get("issues", [])
                if not isinstance(issues_list, list):
                    return 0
                severity = args[0] if args else None
                if severity:
                    return sum(
                        1
                        for i in issues_list
                        if isinstance(i, dict) and i.get("severity") == severity
                    )
                return len(issues_list)

            raise ValueError(f"Unknown function: {func_name}")

        raise ValueError(f"Unknown AST node type: {node_type}")

# Convenience function for direct evaluation
def evaluate_condition(
    expr: str,
    result_state: str = "success",
    failure_kind: str | None = None,
    attempt: int = 0,
    artifacts: list[str] | None = None,
) -> bool:
    """Evaluate a condition expression."""
    evaluator = PixlExprEvaluator()
    context = {
        "result_state": result_state,
        "failure_kind": failure_kind,
        "attempt": attempt,
        "artifacts": artifacts or [],
    }
    return evaluator.evaluate(expr, context)
