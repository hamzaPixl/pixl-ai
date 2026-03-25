"""Pure-logic tests for envelope parser, validation models, stub detector,
success criteria matcher, and git diff validator.

No DB, no I/O, no heavy mocks — only in-process logic.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Imports under test
# ---------------------------------------------------------------------------
from pixl.execution.envelope import (
    _coerce_xml_like_envelope,
    _extract_tag,
    _parse_optional_json,
    _sanitize_json,
    _try_parse_json,
    extract_envelope,
)
from pixl.execution.validation.git_diff_validator import (
    check_max_diff_lines,
    check_max_files_changed,
    check_must_update_files,
)
from pixl.execution.validation.models import ContractValidationResult, ContractViolation
from pixl.execution.validation.stub_detector import detect_stubs
from pixl.execution.validation.success_criteria import extract_key_terms, verify_success_criteria

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MINIMAL_STAGE_OUTPUT_DICT = {
    "schema_version": "1.0",
    "stage_id": "test-stage",
    "status": "ok",
    "summary": ["Done"],
    "artifacts_written": [],
    "included_sources": [],
    "payload": {},
}


def _make_envelope_json(**overrides: object) -> str:
    data = {**_MINIMAL_STAGE_OUTPUT_DICT, **overrides}
    return json.dumps(data)


def _wrap(json_str: str) -> str:
    return f"<pixl_output>{json_str}</pixl_output>"


# ===========================================================================
# Section 1: envelope.py
# ===========================================================================


class TestExtractEnvelopeHappyPath:
    def test_returns_stage_output_for_valid_envelope(self) -> None:
        text = _wrap(_make_envelope_json())
        output, err = extract_envelope(text)

        assert err is None
        assert output is not None
        assert output.stage_id == "test-stage"

    def test_uses_last_envelope_when_multiple_present(self) -> None:
        first = _wrap(_make_envelope_json(stage_id="first"))
        second = _wrap(_make_envelope_json(stage_id="last"))
        text = f"Some preamble\n{first}\nMore text\n{second}\nTrailing text"

        output, err = extract_envelope(text)

        assert err is None
        assert output is not None
        assert output.stage_id == "last"

    def test_returns_summary_list(self) -> None:
        text = _wrap(_make_envelope_json(summary=["item one", "item two"]))
        output, err = extract_envelope(text)

        assert err is None
        assert output is not None
        assert output.summary == ["item one", "item two"]

    def test_accepts_status_error(self) -> None:
        text = _wrap(_make_envelope_json(status="error"))
        output, err = extract_envelope(text)

        assert err is None
        assert output is not None
        assert output.status == "error"

    def test_accepts_envelope_with_whitespace_around_json(self) -> None:
        json_str = _make_envelope_json()
        text = f"<pixl_output>\n  {json_str}\n  </pixl_output>"
        output, err = extract_envelope(text)

        assert err is None
        assert output is not None


class TestExtractEnvelopeMissingEnvelope:
    def test_returns_none_none_when_no_envelope_found(self) -> None:
        output, err = extract_envelope("plain text with no tags")

        assert output is None
        assert err is None

    def test_returns_none_none_for_empty_string(self) -> None:
        output, err = extract_envelope("")

        assert output is None
        assert err is None

    def test_returns_none_none_for_unrelated_xml_tags(self) -> None:
        output, err = extract_envelope("<foo>bar</foo>")

        assert output is None
        assert err is None


class TestExtractEnvelopeMalformedJson:
    def test_returns_error_for_pure_garbage_json(self) -> None:
        text = "<pixl_output>{ this is not json }</pixl_output>"
        output, err = extract_envelope(text)

        # May return error or attempt XML coerce — either way output should be
        # None (no valid stage_id to coerce either)
        assert output is None

    def test_returns_error_message_for_valid_json_failing_validation(self) -> None:
        # Valid JSON but missing required "stage_id" field
        text = _wrap('{"schema_version": "1.0", "status": "ok"}')
        output, err = extract_envelope(text)

        assert output is None
        assert err is not None

    def test_handles_trailing_comma_json(self) -> None:
        # json-sanitization should fix trailing commas
        raw = (
            '{"schema_version":"1.0","stage_id":"s1","status":"ok",'
            '"summary":[],"payload":{},"artifacts_written":[],"included_sources":[],}'
        )
        text = _wrap(raw)
        output, err = extract_envelope(text)

        assert err is None
        assert output is not None
        assert output.stage_id == "s1"

    def test_handles_json_with_inline_comments(self) -> None:
        raw = (
            "{\n"
            '  "schema_version": "1.0", // version\n'
            '  "stage_id": "s2",\n'
            '  "status": "ok",\n'
            '  "summary": [],\n'
            '  "payload": {},\n'
            '  "artifacts_written": [],\n'
            '  "included_sources": []\n'
            "}"
        )
        text = _wrap(raw)
        output, err = extract_envelope(text)

        assert err is None
        assert output is not None
        assert output.stage_id == "s2"


class TestExtractEnvelopeXmlLikeCoercion:
    def test_coerces_xml_like_content_with_stage_id(self) -> None:
        xml_content = (
            "<schema_version>1.0</schema_version>"
            "<stage_id>xml-stage</stage_id>"
            "<status>ok</status>"
            "<summary></summary>"
        )
        text = f"<pixl_output>{xml_content}</pixl_output>"
        output, err = extract_envelope(text)

        assert err is None
        assert output is not None
        assert output.stage_id == "xml-stage"

    def test_coerces_xml_with_completed_status(self) -> None:
        xml_content = (
            "<schema_version>1.0</schema_version>"
            "<stage_id>xml-stage</stage_id>"
            "<status>completed</status>"
        )
        text = f"<pixl_output>{xml_content}</pixl_output>"
        output, err = extract_envelope(text)

        assert output is not None
        assert output.status == "ok"


class TestExtractEnvelopeFallbackJson:
    def test_extracts_bare_json_with_stage_id_in_plain_text(self) -> None:
        stage_json = json.dumps(_MINIMAL_STAGE_OUTPUT_DICT)
        text = f"Some leading text\n\n{stage_json}\n\nSome trailing text"
        output, err = extract_envelope(text)

        assert err is None
        assert output is not None
        assert output.stage_id == "test-stage"


class TestExtractTagHelper:
    def test_extracts_simple_tag(self) -> None:
        result = _extract_tag("<foo>bar</foo>", "foo")
        assert result == "bar"

    def test_returns_none_when_tag_absent(self) -> None:
        result = _extract_tag("<other>val</other>", "missing")
        assert result is None

    def test_strips_whitespace_from_value(self) -> None:
        result = _extract_tag("<tag>  hello  </tag>", "tag")
        assert result == "hello"

    def test_case_insensitive_tag_matching(self) -> None:
        result = _extract_tag("<FOO>value</FOO>", "foo")
        assert result == "value"

    def test_extracts_multiline_content(self) -> None:
        result = _extract_tag("<summary>\nline1\nline2\n</summary>", "summary")
        assert result == "line1\nline2"


class TestParseOptionalJsonHelper:
    def test_returns_default_for_none(self) -> None:
        assert _parse_optional_json(None, []) == []

    def test_returns_default_for_empty_string(self) -> None:
        assert _parse_optional_json("", {}) == {}

    def test_parses_valid_json_list(self) -> None:
        assert _parse_optional_json('["a", "b"]', []) == ["a", "b"]

    def test_returns_default_on_invalid_json(self) -> None:
        assert _parse_optional_json("not-json", "default") == "default"


class TestSanitizeJsonHelper:
    def test_removes_single_line_comments(self) -> None:
        result = _sanitize_json('{"key": "value"} // comment')
        assert "//" not in result

    def test_removes_block_comments(self) -> None:
        result = _sanitize_json('{"key": /* block */ "value"}')
        assert "block" not in result

    def test_removes_trailing_commas_before_close_brace(self) -> None:
        result = _sanitize_json('{"a":1,}')
        assert result == '{"a":1}'

    def test_removes_trailing_commas_before_close_bracket(self) -> None:
        result = _sanitize_json('["a","b",]')
        assert result == '["a","b"]'


class TestTryParseJsonHelper:
    def test_parses_valid_json(self) -> None:
        result = _try_parse_json('{"stage_id": "s"}')
        assert result == {"stage_id": "s"}

    def test_returns_none_for_list_json(self) -> None:
        result = _try_parse_json('["a", "b"]')
        assert result is None

    def test_returns_none_for_garbage(self) -> None:
        result = _try_parse_json("definitely not json!!!!")
        assert result is None

    def test_repairs_trailing_comma_json(self) -> None:
        result = _try_parse_json('{"stage_id":"s",}')
        assert result == {"stage_id": "s"}


class TestCoerceXmlLikeEnvelope:
    def test_returns_none_when_no_xml_angle_brackets(self) -> None:
        result = _coerce_xml_like_envelope("plain text no angle brackets")
        assert result is None

    def test_returns_none_when_no_stage_id_tag(self) -> None:
        result = _coerce_xml_like_envelope("<status>ok</status>")
        assert result is None

    def test_coerces_minimal_xml_with_stage_id(self) -> None:
        body = "<stage_id>s1</stage_id><status>ok</status>"
        result = _coerce_xml_like_envelope(body)
        assert result is not None
        assert result["stage_id"] == "s1"
        assert result["status"] == "ok"

    def test_maps_completed_to_ok_status(self) -> None:
        body = "<stage_id>s</stage_id><status>completed</status>"
        result = _coerce_xml_like_envelope(body)
        assert result is not None
        assert result["status"] == "ok"

    def test_maps_failed_to_error_status(self) -> None:
        body = "<stage_id>s</stage_id><status>failed</status>"
        result = _coerce_xml_like_envelope(body)
        assert result is not None
        assert result["status"] == "error"

    def test_unknown_status_defaults_to_ok(self) -> None:
        body = "<stage_id>s</stage_id><status>mysterious</status>"
        result = _coerce_xml_like_envelope(body)
        assert result is not None
        assert result["status"] == "ok"

    def test_parses_json_array_summary(self) -> None:
        body = '<stage_id>s</stage_id><summary>["item1","item2"]</summary>'
        result = _coerce_xml_like_envelope(body)
        assert result is not None
        assert result["summary"] == ["item1", "item2"]

    def test_parses_plain_text_summary(self) -> None:
        body = "<stage_id>s</stage_id><summary>plain summary text</summary>"
        result = _coerce_xml_like_envelope(body)
        assert result is not None
        assert "plain summary text" in result["summary"]


# ===========================================================================
# Section 2: validation/stub_detector.py
# ===========================================================================


class TestDetectStubsWithTodos:
    def _write_temp_file(self, content: str) -> tuple[Path, str]:
        """Write content to a temp file; return (dir_path, filename)."""
        tmpdir = tempfile.mkdtemp()
        path = Path(tmpdir) / "code.py"
        path.write_text(content, encoding="utf-8")
        return Path(tmpdir), "code.py"

    def _make_resolver(self, base_dir: Path):
        def resolver(relative: str) -> Path:
            return base_dir / relative

        return resolver

    def test_detects_todo_comment(self) -> None:
        content = "def foo():\n    # TODO: implement this\n    pass\n"
        tmpdir, filename = self._write_temp_file(content)
        result = ContractValidationResult()

        stubs = detect_stubs([filename], self._make_resolver(tmpdir), result)

        assert len(stubs) >= 1
        assert any("TODO" in s["content"].upper() for s in stubs)

    def test_detects_fixme_comment(self) -> None:
        tmpdir, filename = self._write_temp_file("# FIXME: broken logic\nx = 1\n")
        result = ContractValidationResult()

        stubs = detect_stubs([filename], self._make_resolver(tmpdir), result)

        assert len(stubs) >= 1
        assert any("FIXME" in s["content"].upper() for s in stubs)

    def test_detects_raise_not_implemented_error(self) -> None:
        tmpdir, filename = self._write_temp_file("def foo():\n    raise NotImplementedError\n")
        result = ContractValidationResult()

        stubs = detect_stubs([filename], self._make_resolver(tmpdir), result)

        assert len(stubs) >= 1

    def test_detects_placeholder_return(self) -> None:
        tmpdir, filename = self._write_temp_file('def foo():\n    return "placeholder"\n')
        result = ContractValidationResult()

        stubs = detect_stubs([filename], self._make_resolver(tmpdir), result)

        assert len(stubs) >= 1

    def test_adds_violation_to_result_when_stubs_found(self) -> None:
        tmpdir, filename = self._write_temp_file("# TODO: finish\n")
        result = ContractValidationResult()

        detect_stubs([filename], self._make_resolver(tmpdir), result)

        assert not result.passed
        assert any(v.rule == "stub_detected" for v in result.violations)

    def test_returns_empty_list_for_clean_file(self) -> None:
        tmpdir, filename = self._write_temp_file("def foo():\n    return 42\n")
        result = ContractValidationResult()

        stubs = detect_stubs([filename], self._make_resolver(tmpdir), result)

        assert stubs == []
        assert result.passed

    def test_skips_nonexistent_files(self) -> None:
        result = ContractValidationResult()

        stubs = detect_stubs(["nonexistent.py"], lambda p: Path("/does/not/exist.py"), result)

        assert stubs == []
        assert result.passed

    def test_one_match_per_line_only(self) -> None:
        # Line has both TODO and FIXME — should count as one stub entry per line
        tmpdir, filename = self._write_temp_file("# TODO FIXME: double trouble\n")
        result = ContractValidationResult()

        stubs = detect_stubs([filename], self._make_resolver(tmpdir), result)

        assert len(stubs) == 1

    def test_custom_stub_patterns_override(self) -> None:
        tmpdir, filename = self._write_temp_file("# CUSTOM_STUB: do something\n")
        result = ContractValidationResult()

        stubs = detect_stubs(
            [filename],
            self._make_resolver(tmpdir),
            result,
            stub_patterns=[r"CUSTOM_STUB"],
        )

        assert len(stubs) == 1

    def test_violation_message_includes_file_reference(self) -> None:
        tmpdir, filename = self._write_temp_file("# TODO\n")
        result = ContractValidationResult()

        detect_stubs([filename], self._make_resolver(tmpdir), result)

        assert any(filename in v.message for v in result.violations)

    def test_detects_ellipsis_stub(self) -> None:
        tmpdir, filename = self._write_temp_file("def foo():\n    ...\n")
        result = ContractValidationResult()

        stubs = detect_stubs([filename], self._make_resolver(tmpdir), result)

        assert len(stubs) >= 1


# ===========================================================================
# Section 3: validation/success_criteria.py
# ===========================================================================


class TestExtractKeyTerms:
    def test_returns_words_of_three_or_more_chars(self) -> None:
        terms = extract_key_terms("Do the thing")
        # "the" is a stop word; "Do" becomes "Do" (2 chars < 3) — check boundary
        assert "thing" in terms

    def test_filters_stop_words(self) -> None:
        terms = extract_key_terms("the and for are but not")
        assert terms == []

    def test_returns_duplicate_terms_for_repeated_words(self) -> None:
        # NOTE: The docstring says "unique terms" but the implementation returns
        # a plain list comprehension that preserves duplicates.  This test
        # documents the *actual* behavior so regressions are caught if the
        # implementation is ever fixed to match its docs.
        terms = extract_key_terms("login login login")
        assert terms.count("login") == 3

    def test_extracts_camel_case_identifiers(self) -> None:
        terms = extract_key_terms("implement getUserById function")
        assert "getUserById" in terms
        assert "function" in terms

    def test_ignores_two_letter_words(self) -> None:
        terms = extract_key_terms("in my go if")
        # All are too short or stop words
        assert "in" not in terms
        assert "my" not in terms

    def test_returns_empty_for_all_stop_words(self) -> None:
        assert extract_key_terms("the and for") == []


class TestVerifySuccessCriteria:
    def _make_resolver(self, base_dir: Path):
        def resolver(relative: str) -> Path:
            return base_dir / relative

        return resolver

    def test_returns_true_when_terms_found_in_file(self) -> None:
        tmpdir = Path(tempfile.mkdtemp())
        (tmpdir / "impl.py").write_text("def authenticate_user():\n    pass\n", encoding="utf-8")
        result = ContractValidationResult()

        status = verify_success_criteria(
            ["authenticate user"],
            ["impl.py"],
            self._make_resolver(tmpdir),
            result,
        )

        assert status["authenticate user"] is True

    def test_returns_false_when_terms_not_found_in_any_file(self) -> None:
        tmpdir = Path(tempfile.mkdtemp())
        (tmpdir / "impl.py").write_text("def unrelated():\n    pass\n", encoding="utf-8")
        result = ContractValidationResult()

        status = verify_success_criteria(
            ["payment gateway integration"],
            ["impl.py"],
            self._make_resolver(tmpdir),
            result,
        )

        assert status["payment gateway integration"] is False

    def test_adds_violation_for_unmet_criterion(self) -> None:
        tmpdir = Path(tempfile.mkdtemp())
        (tmpdir / "impl.py").write_text("x = 1\n", encoding="utf-8")
        result = ContractValidationResult()

        verify_success_criteria(
            ["missing feature implementation"],
            ["impl.py"],
            self._make_resolver(tmpdir),
            result,
        )

        assert not result.passed
        assert any(v.rule == "success_criteria_unmet" for v in result.violations)

    def test_no_violations_when_all_criteria_met(self) -> None:
        tmpdir = Path(tempfile.mkdtemp())
        (tmpdir / "impl.py").write_text("def create_order(): pass\n", encoding="utf-8")
        result = ContractValidationResult()

        verify_success_criteria(
            ["create order"],
            ["impl.py"],
            self._make_resolver(tmpdir),
            result,
        )

        assert result.passed

    def test_handles_empty_criteria_list(self) -> None:
        result = ContractValidationResult()
        status = verify_success_criteria([], [], lambda p: Path(p), result)

        assert status == {}
        assert result.passed

    def test_skips_nonexistent_files(self) -> None:
        result = ContractValidationResult()

        status = verify_success_criteria(
            ["some criteria"],
            ["nonexistent.py"],
            lambda p: Path("/does/not/exist"),
            result,
        )

        assert status["some criteria"] is False

    def test_criterion_matched_when_half_of_key_terms_found(self) -> None:
        # "user login system" → key terms: ["user", "login", "system"]
        # file contains "user" and "login" → 2/3 ≥ 3//2 (1) → True
        tmpdir = Path(tempfile.mkdtemp())
        (tmpdir / "impl.py").write_text("user = login()\n", encoding="utf-8")
        result = ContractValidationResult()

        status = verify_success_criteria(
            ["user login system"],
            ["impl.py"],
            self._make_resolver(tmpdir),
            result,
        )

        assert status["user login system"] is True


# ===========================================================================
# Section 4: validation/models.py
# ===========================================================================


class TestContractViolation:
    def test_construction_stores_rule_and_message(self) -> None:
        v = ContractViolation(rule="test_rule", message="something failed")

        assert v.rule == "test_rule"
        assert v.message == "something failed"


class TestContractValidationResult:
    def test_passed_is_true_when_no_violations(self) -> None:
        result = ContractValidationResult()

        assert result.passed is True

    def test_passed_is_false_when_violation_present(self) -> None:
        result = ContractValidationResult()
        result.violations.append(ContractViolation(rule="r", message="m"))

        assert result.passed is False

    def test_has_warnings_is_false_when_no_warnings(self) -> None:
        result = ContractValidationResult()

        assert result.has_warnings is False

    def test_has_warnings_is_true_when_warning_present(self) -> None:
        result = ContractValidationResult()
        result.warnings.append("a warning")

        assert result.has_warnings is True

    def test_violation_messages_formats_correctly(self) -> None:
        result = ContractValidationResult()
        result.violations.append(ContractViolation(rule="my_rule", message="the message"))

        assert result.violation_messages == ["[my_rule] the message"]

    def test_warning_messages_returns_list_of_strings(self) -> None:
        result = ContractValidationResult()
        result.warnings.append("warn1")
        result.warnings.append("warn2")

        assert result.warning_messages == ["warn1", "warn2"]

    def test_default_construction_produces_empty_collections(self) -> None:
        result = ContractValidationResult()

        assert result.violations == []
        assert result.git_unavailable_checks == []
        assert result.warnings == []

    def test_multiple_violations_all_appear_in_messages(self) -> None:
        result = ContractValidationResult()
        result.violations.append(ContractViolation(rule="r1", message="m1"))
        result.violations.append(ContractViolation(rule="r2", message="m2"))

        messages = result.violation_messages
        assert len(messages) == 2
        assert "[r1] m1" in messages
        assert "[r2] m2" in messages


# ===========================================================================
# Section 5: validation/git_diff_validator.py
# ===========================================================================


class TestCheckMustUpdateFiles:
    def _make_result(self) -> ContractValidationResult:
        return ContractValidationResult()

    def test_no_violation_when_required_file_in_changed_files(self) -> None:
        result = self._make_result()

        check_must_update_files(
            must_update_files=["src/app.py"],
            result=result,
            changed_files=["src/app.py", "tests/test_app.py"],
            git_changed_files_fn=lambda r: None,
        )

        assert result.passed

    def test_violation_when_required_file_not_in_changed_files(self) -> None:
        result = self._make_result()

        check_must_update_files(
            must_update_files=["src/app.py"],
            result=result,
            changed_files=["tests/test_other.py"],
            git_changed_files_fn=lambda r: None,
        )

        assert not result.passed
        assert any(v.rule == "must_update_files" for v in result.violations)

    def test_violation_message_includes_pattern(self) -> None:
        result = self._make_result()

        check_must_update_files(
            must_update_files=["schema.sql"],
            result=result,
            changed_files=[],
            git_changed_files_fn=lambda r: None,
        )

        assert any("schema.sql" in v.message for v in result.violations)

    def test_uses_git_fn_when_changed_files_is_none(self) -> None:
        result = self._make_result()

        check_must_update_files(
            must_update_files=["app.py"],
            result=result,
            changed_files=None,
            git_changed_files_fn=lambda r: {"app.py"},
        )

        assert result.passed

    def test_skips_check_when_git_fn_returns_none(self) -> None:
        result = self._make_result()

        # git unavailable — the fn returns None
        check_must_update_files(
            must_update_files=["app.py"],
            result=result,
            changed_files=None,
            git_changed_files_fn=lambda r: None,
        )

        assert result.passed  # no violation recorded when git unavailable

    def test_glob_pattern_matches_nested_path(self) -> None:
        result = self._make_result()

        check_must_update_files(
            must_update_files=["**/*.py"],
            result=result,
            changed_files=["src/deep/nested/module.py"],
            git_changed_files_fn=lambda r: None,
        )

        assert result.passed

    def test_no_violation_for_empty_must_update_list(self) -> None:
        result = self._make_result()

        check_must_update_files(
            must_update_files=[],
            result=result,
            changed_files=[],
            git_changed_files_fn=lambda r: None,
        )

        assert result.passed


class TestCheckMaxDiffLines:
    def _make_result(self) -> ContractValidationResult:
        return ContractValidationResult()

    def test_no_violation_when_diff_within_limit(self) -> None:
        result = self._make_result()

        check_max_diff_lines(
            max_diff_lines=100,
            result=result,
            git_diff_line_count_fn=lambda r: 50,
        )

        assert result.passed

    def test_violation_when_diff_exceeds_limit(self) -> None:
        result = self._make_result()

        check_max_diff_lines(
            max_diff_lines=100,
            result=result,
            git_diff_line_count_fn=lambda r: 101,
        )

        assert not result.passed
        assert any(v.rule == "max_diff_lines" for v in result.violations)

    def test_no_violation_when_diff_equals_limit(self) -> None:
        result = self._make_result()

        check_max_diff_lines(
            max_diff_lines=100,
            result=result,
            git_diff_line_count_fn=lambda r: 100,
        )

        assert result.passed

    def test_skips_check_when_git_fn_returns_none(self) -> None:
        result = self._make_result()

        check_max_diff_lines(
            max_diff_lines=10,
            result=result,
            git_diff_line_count_fn=lambda r: None,
        )

        assert result.passed  # git unavailable

    def test_violation_message_includes_actual_and_max_counts(self) -> None:
        result = self._make_result()

        check_max_diff_lines(
            max_diff_lines=50,
            result=result,
            git_diff_line_count_fn=lambda r: 99,
        )

        msg = result.violations[0].message
        assert "99" in msg
        assert "50" in msg


class TestCheckMaxFilesChanged:
    def _make_result(self) -> ContractValidationResult:
        return ContractValidationResult()

    def test_no_violation_when_files_within_limit(self) -> None:
        result = self._make_result()

        check_max_files_changed(
            max_files_changed=5,
            result=result,
            git_changed_files_fn=lambda r: {"a.py", "b.py"},
        )

        assert result.passed

    def test_violation_when_too_many_files_changed(self) -> None:
        result = self._make_result()

        check_max_files_changed(
            max_files_changed=2,
            result=result,
            git_changed_files_fn=lambda r: {"a.py", "b.py", "c.py"},
        )

        assert not result.passed
        assert any(v.rule == "max_files_changed" for v in result.violations)

    def test_no_violation_when_files_equal_limit(self) -> None:
        result = self._make_result()

        check_max_files_changed(
            max_files_changed=3,
            result=result,
            git_changed_files_fn=lambda r: {"a.py", "b.py", "c.py"},
        )

        assert result.passed

    def test_skips_check_when_git_fn_returns_none(self) -> None:
        result = self._make_result()

        check_max_files_changed(
            max_files_changed=1,
            result=result,
            git_changed_files_fn=lambda r: None,
        )

        assert result.passed  # git unavailable

    def test_violation_message_includes_actual_and_max_counts(self) -> None:
        result = self._make_result()

        check_max_files_changed(
            max_files_changed=2,
            result=result,
            git_changed_files_fn=lambda r: {"a.py", "b.py", "c.py"},
        )

        msg = result.violations[0].message
        assert "3" in msg
        assert "2" in msg
