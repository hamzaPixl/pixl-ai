"""Tests for PixlExpr expression evaluator."""

import pytest
from pixl.execution.expression_evaluator import PixlExprEvaluator, evaluate_condition


class TestBasicValues:
    def test_true_literal(self) -> None:
        ev = PixlExprEvaluator()
        assert ev.evaluate("True") is True

    def test_false_literal(self) -> None:
        ev = PixlExprEvaluator()
        assert ev.evaluate("False") is False

    def test_integer_truthy(self) -> None:
        ev = PixlExprEvaluator()
        assert ev.evaluate("42", {}) is True  # bool(42) = True

    def test_zero_falsy(self) -> None:
        ev = PixlExprEvaluator()
        assert ev.evaluate("0", {}) is False  # bool(0) = False

    def test_string_truthy(self) -> None:
        ev = PixlExprEvaluator()
        assert ev.evaluate("'hello'", {}) is True  # bool("hello") = True

    def test_none_falsy(self) -> None:
        ev = PixlExprEvaluator()
        assert ev.evaluate("None", {}) is False  # bool(None) = False


class TestComparisons:
    def test_equal(self) -> None:
        assert evaluate_condition("result_state == 'success'", result_state="success")

    def test_not_equal(self) -> None:
        assert evaluate_condition("result_state != 'failed'", result_state="success")

    def test_less_than(self) -> None:
        assert evaluate_condition("attempt < 3", attempt=2)

    def test_less_than_false(self) -> None:
        assert not evaluate_condition("attempt < 3", attempt=3)

    def test_greater_than(self) -> None:
        assert evaluate_condition("attempt > 0", attempt=1)

    def test_less_equal(self) -> None:
        assert evaluate_condition("attempt <= 3", attempt=3)

    def test_greater_equal(self) -> None:
        assert evaluate_condition("attempt >= 1", attempt=1)


class TestLogicalOperators:
    def test_and_true(self) -> None:
        assert evaluate_condition(
            "result_state == 'success' and attempt < 3",
            result_state="success",
            attempt=1,
        )

    def test_and_false(self) -> None:
        assert not evaluate_condition(
            "result_state == 'success' and attempt < 3",
            result_state="failed",
            attempt=1,
        )

    def test_or_true(self) -> None:
        assert evaluate_condition(
            "result_state == 'success' or attempt < 3",
            result_state="failed",
            attempt=1,
        )

    def test_or_both_false(self) -> None:
        assert not evaluate_condition(
            "result_state == 'success' or attempt < 1",
            result_state="failed",
            attempt=3,
        )

    def test_not(self) -> None:
        assert evaluate_condition(
            "not result_state == 'failed'",
            result_state="success",
        )


class TestFunctions:
    def test_result_success(self) -> None:
        assert evaluate_condition("result('success')", result_state="success")

    def test_result_failed(self) -> None:
        assert not evaluate_condition("result('success')", result_state="failed")

    def test_failure_kind_transient(self) -> None:
        assert evaluate_condition("failure_kind('transient')", failure_kind="transient")

    def test_failure_kind_none(self) -> None:
        assert not evaluate_condition("failure_kind('transient')", failure_kind=None)

    def test_attempt_comparison(self) -> None:
        assert evaluate_condition("attempt(3)", attempt=2)

    def test_attempt_at_limit(self) -> None:
        assert not evaluate_condition("attempt(3)", attempt=3)

    def test_artifact_exists_true(self) -> None:
        assert evaluate_condition("artifact_exists('plan.md')", artifacts=["plan.md", "code.ts"])

    def test_artifact_exists_false(self) -> None:
        assert not evaluate_condition("artifact_exists('missing.md')", artifacts=["plan.md"])

    def test_payload_access(self) -> None:
        ev = PixlExprEvaluator()
        ctx = {"payload": {"recommendation": "approve"}}
        assert ev.evaluate("payload('recommendation') == 'approve'", ctx) is True

    def test_payload_missing_key_falsy(self) -> None:
        ev = PixlExprEvaluator()
        ctx = {"payload": {}}
        assert ev.evaluate("payload('missing')", ctx) is False  # bool(None) = False

    def test_issues_total_count(self) -> None:
        ev = PixlExprEvaluator()
        ctx = {"payload": {"issues": [{"severity": "critical"}, {"severity": "low"}]}}
        assert ev.evaluate("issues()", ctx) is True  # bool(2) = True

    def test_issues_by_severity(self) -> None:
        ev = PixlExprEvaluator()
        ctx = {"payload": {"issues": [{"severity": "critical"}, {"severity": "low"}]}}
        assert ev.evaluate("issues('critical')", ctx) == 1

    def test_issues_empty(self) -> None:
        ev = PixlExprEvaluator()
        ctx = {"payload": {"issues": []}}
        assert ev.evaluate("issues()", ctx) == 0


class TestContextResolution:
    def test_alias_result(self) -> None:
        ev = PixlExprEvaluator()
        ctx = {"result_state": "success"}
        assert ev.evaluate("result == 'success'", ctx) is True

    def test_direct_context_key(self) -> None:
        ev = PixlExprEvaluator()
        ctx = {"custom_key": "value"}
        assert ev.evaluate("custom_key == 'value'", ctx) is True


class TestSecurity:
    def test_rejects_private_identifier(self) -> None:
        ev = PixlExprEvaluator()
        with pytest.raises(ValueError, match="private attribute"):
            ev.evaluate("_secret == 'x'", {})

    def test_rejects_dunder_identifier(self) -> None:
        ev = PixlExprEvaluator()
        with pytest.raises(ValueError, match="private attribute"):
            ev.evaluate("__class__ == 'x'", {})

    def test_rejects_private_function(self) -> None:
        ev = PixlExprEvaluator()
        with pytest.raises(ValueError, match="private function"):
            ev.evaluate("_internal()", {})

    def test_rejects_unknown_function(self) -> None:
        ev = PixlExprEvaluator()
        with pytest.raises(ValueError, match="Unknown function"):
            ev.evaluate("eval('import os')", {})


class TestEdgeCases:
    def test_empty_expression_raises(self) -> None:
        ev = PixlExprEvaluator()
        with pytest.raises(ValueError):
            ev.evaluate("", {})

    def test_parenthesized_expression(self) -> None:
        assert evaluate_condition("(attempt < 3)", attempt=2)

    def test_chained_and(self) -> None:
        assert evaluate_condition(
            "result_state == 'failed' and failure_kind == 'transient' and attempt < 3",
            result_state="failed",
            failure_kind="transient",
            attempt=1,
        )

    def test_convenience_function_defaults(self) -> None:
        assert evaluate_condition("result_state == 'success'")
