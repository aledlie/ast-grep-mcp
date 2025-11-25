"""Unit tests for linting rules (Phase 1 - Code Quality Standards)."""

import os
import sys
import tempfile
import subprocess
from pathlib import Path
from typing import Any, Dict
from unittest.mock import Mock, patch, MagicMock, mock_open

import pytest
import yaml

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# Mock FastMCP to disable decoration
class MockFastMCP:
    """Mock FastMCP that returns functions unchanged"""

    def __init__(self, name: str) -> None:
        self.name = name
        self.tools: Dict[str, Any] = {}  # Store registered tools

    def tool(self, **kwargs: Any) -> Any:
        """Decorator that returns the function unchanged"""

        def decorator(func: Any) -> Any:
            # Store the function for later retrieval
            self.tools[func.__name__] = func
            return func  # Return original function without modification

        return decorator

    def run(self, **kwargs: Any) -> None:
        """Mock run method"""
        pass


# Mock the Field function to return the default value
def mock_field(**kwargs: Any) -> Any:
    return kwargs.get("default")


# Patch the imports before loading main
with patch("mcp.server.fastmcp.FastMCP", MockFastMCP):
    with patch("pydantic.Field", mock_field):
        import main

from ast_grep_mcp.features.quality.rules import RULE_TEMPLATES
from main import (
    LintingRule,
    RuleStorageError,
    RuleTemplate,
    RuleValidationError,
    RuleValidationResult,
    _get_available_templates,
    _load_rule_from_file,
    _save_rule_to_project,
    _validate_rule_definition,
    _validate_rule_pattern,
)


class TestLintingRuleDataClass:
    """Test LintingRule data class."""

    def test_instantiation_all_fields(self):
        """Test creating LintingRule with all fields."""
        rule = LintingRule(
            id="no-console-log",
            language="typescript",
            severity="warning",
            message="Remove console.log",
            pattern="console.log($$$)",
            note="Use proper logging",
            fix="Replace with logger",
            constraints={"kind": "call_expression"}
        )

        assert rule.id == "no-console-log"
        assert rule.language == "typescript"
        assert rule.severity == "warning"
        assert rule.message == "Remove console.log"
        assert rule.pattern == "console.log($$$)"
        assert rule.note == "Use proper logging"
        assert rule.fix == "Replace with logger"
        assert rule.constraints == {"kind": "call_expression"}

    def test_instantiation_required_fields_only(self):
        """Test creating LintingRule with only required fields."""
        rule = LintingRule(
            id="test-rule",
            language="python",
            severity="error",
            message="Test message",
            pattern="test_pattern"
        )

        assert rule.id == "test-rule"
        assert rule.language == "python"
        assert rule.severity == "error"
        assert rule.message == "Test message"
        assert rule.pattern == "test_pattern"
        assert rule.note is None
        assert rule.fix is None
        assert rule.constraints is None

    def test_to_yaml_dict_all_fields(self):
        """Test converting LintingRule to YAML dict with all fields."""
        rule = LintingRule(
            id="test-rule",
            language="typescript",
            severity="warning",
            message="Test message",
            pattern="test($$$)",
            note="Test note",
            fix="Fix suggestion",
            constraints={"kind": "function"}
        )

        result = rule.to_yaml_dict()

        assert result["id"] == "test-rule"
        assert result["language"] == "typescript"
        assert result["severity"] == "warning"
        assert result["message"] == "Test message"
        assert result["rule"]["pattern"] == "test($$$)"
        assert result["note"] == "Test note"
        assert result["fix"] == "Fix suggestion"
        assert result["constraints"] == {"kind": "function"}

    def test_to_yaml_dict_optional_fields_none(self):
        """Test converting LintingRule to YAML dict with optional fields as None."""
        rule = LintingRule(
            id="test-rule",
            language="python",
            severity="error",
            message="Test message",
            pattern="test",
            note=None,
            fix=None,
            constraints=None
        )

        result = rule.to_yaml_dict()

        assert result["id"] == "test-rule"
        assert result["language"] == "python"
        assert result["severity"] == "error"
        assert result["message"] == "Test message"
        assert result["rule"]["pattern"] == "test"
        assert "note" not in result
        assert "fix" not in result
        assert "constraints" not in result

    def test_to_yaml_dict_structure(self):
        """Test YAML dict structure is correct for ast-grep."""
        rule = LintingRule(
            id="no-var",
            language="typescript",
            severity="warning",
            message="Use const or let",
            pattern="var $NAME = $$$"
        )

        result = rule.to_yaml_dict()

        assert "rule" in result
        assert isinstance(result["rule"], dict)
        assert "pattern" in result["rule"]


class TestRuleTemplateDataClass:
    """Test RuleTemplate data class."""

    def test_instantiation_all_fields(self):
        """Test creating RuleTemplate with all fields."""
        template = RuleTemplate(
            id="no-var",
            name="No var declarations",
            description="Disallow var declarations",
            language="typescript",
            severity="warning",
            pattern="var $NAME = $$$",
            message="Use const or let",
            note="var has function scope",
            fix="Replace with const or let",
            category="style"
        )

        assert template.id == "no-var"
        assert template.name == "No var declarations"
        assert template.description == "Disallow var declarations"
        assert template.language == "typescript"
        assert template.severity == "warning"
        assert template.pattern == "var $NAME = $$$"
        assert template.message == "Use const or let"
        assert template.note == "var has function scope"
        assert template.fix == "Replace with const or let"
        assert template.category == "style"

    def test_instantiation_default_category(self):
        """Test RuleTemplate with default category."""
        template = RuleTemplate(
            id="test",
            name="Test",
            description="Test desc",
            language="python",
            severity="error",
            pattern="test",
            message="Test message"
        )

        assert template.category == "general"


class TestRuleValidationResultDataClass:
    """Test RuleValidationResult data class."""

    def test_valid_result_no_errors(self):
        """Test RuleValidationResult with valid status."""
        result = RuleValidationResult(is_valid=True, errors=[], warnings=[])

        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_invalid_result_with_errors(self):
        """Test RuleValidationResult with errors."""
        result = RuleValidationResult(
            is_valid=False,
            errors=["Error 1", "Error 2"],
            warnings=[]
        )

        assert result.is_valid is False
        assert len(result.errors) == 2
        assert "Error 1" in result.errors
        assert "Error 2" in result.errors

    def test_valid_result_with_warnings(self):
        """Test RuleValidationResult with warnings but valid."""
        result = RuleValidationResult(
            is_valid=True,
            errors=[],
            warnings=["Warning 1", "Warning 2"]
        )

        assert result.is_valid is True
        assert result.errors == []
        assert len(result.warnings) == 2

    def test_default_factory_empty_lists(self):
        """Test that default factory creates empty lists."""
        result = RuleValidationResult(is_valid=True)

        assert result.errors == []
        assert result.warnings == []


class TestErrorClasses:
    """Test error classes."""

    def test_rule_validation_error_raised(self):
        """Test RuleValidationError can be raised."""
        with pytest.raises(RuleValidationError) as exc_info:
            raise RuleValidationError("Validation failed")

        assert "Validation failed" in str(exc_info.value)

    def test_rule_storage_error_raised(self):
        """Test RuleStorageError can be raised."""
        with pytest.raises(RuleStorageError) as exc_info:
            raise RuleStorageError("Storage failed")

        assert "Storage failed" in str(exc_info.value)

    def test_error_inheritance(self):
        """Test errors inherit from Exception."""
        assert issubclass(RuleValidationError, Exception)
        assert issubclass(RuleStorageError, Exception)

    def test_error_messages_preserved(self):
        """Test error messages are preserved."""
        error_msg = "Custom error message"
        error = RuleValidationError(error_msg)
        assert str(error) == error_msg


class TestRuleTemplates:
    """Test RULE_TEMPLATES constant."""

    def test_templates_exist(self):
        """Test that RULE_TEMPLATES dictionary exists."""
        assert RULE_TEMPLATES is not None
        assert isinstance(RULE_TEMPLATES, dict)

    def test_template_count(self):
        """Test that all 24 templates are present."""
        assert len(RULE_TEMPLATES) == 24

    def test_typescript_templates(self):
        """Test TypeScript/JavaScript templates exist."""
        typescript_templates = [
            "no-var", "no-double-equals", "no-console-log",
            "prefer-const", "no-unused-vars", "no-empty-catch",
            "no-any-type", "no-magic-numbers", "no-todo-comments",
            "no-fixme-comments", "no-debugger", "no-hardcoded-credentials",
            "no-sql-injection"
        ]

        for template_id in typescript_templates:
            assert template_id in RULE_TEMPLATES
            template = RULE_TEMPLATES[template_id]
            assert template.language in ["typescript", "javascript"]

    def test_python_templates(self):
        """Test Python templates exist."""
        python_templates = [
            "no-bare-except", "no-mutable-defaults", "no-eval-exec",
            "no-print-production", "require-type-hints", "no-string-exception",
            "no-assert-production"
        ]

        for template_id in python_templates:
            assert template_id in RULE_TEMPLATES
            assert RULE_TEMPLATES[template_id].language == "python"

    def test_java_templates(self):
        """Test Java templates exist."""
        java_templates = [
            "no-system-out", "proper-exception-handling",
            "no-empty-finally", "no-instanceof-object"
        ]

        for template_id in java_templates:
            assert template_id in RULE_TEMPLATES
            assert RULE_TEMPLATES[template_id].language == "java"

    def test_template_structure_valid(self):
        """Test that all templates have required fields."""
        for template_id, template in RULE_TEMPLATES.items():
            assert template.id is not None
            assert template.name is not None
            assert template.description is not None
            assert template.language is not None
            assert template.severity is not None
            assert template.pattern is not None
            assert template.message is not None
            assert template.category is not None

    def test_template_severity_values(self):
        """Test that all templates have valid severity values."""
        valid_severities = ["error", "warning", "info"]

        for template in RULE_TEMPLATES.values():
            assert template.severity in valid_severities

    def test_template_category_values(self):
        """Test that all templates have valid category values."""
        valid_categories = ["general", "security", "performance", "style"]

        for template in RULE_TEMPLATES.values():
            assert template.category in valid_categories

    def test_no_var_template_details(self):
        """Test no-var template has correct details."""
        template = RULE_TEMPLATES["no-var"]

        assert template.id == "no-var"
        assert template.language == "typescript"
        assert template.severity == "warning"
        assert template.pattern == "var $NAME = $$$"
        assert template.category == "style"

    def test_no_bare_except_template_details(self):
        """Test no-bare-except template has correct details."""
        template = RULE_TEMPLATES["no-bare-except"]

        assert template.id == "no-bare-except"
        assert template.language == "python"
        assert template.severity == "error"
        assert template.pattern == "except:"
        assert template.category == "security"


class TestValidateRulePattern:
    """Test _validate_rule_pattern function."""

    @patch("main.run_ast_grep")
    def test_valid_python_pattern(self, mock_run):
        """Test validating a valid Python pattern."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = _validate_rule_pattern("except:", "python")

        assert result.is_valid is True
        assert len(result.errors) == 0
        mock_run.assert_called_once()

    @patch("main.run_ast_grep")
    def test_valid_typescript_pattern(self, mock_run):
        """Test validating a valid TypeScript pattern."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = _validate_rule_pattern("console.log($$$)", "typescript")

        assert result.is_valid is True
        assert len(result.errors) == 0

    @patch("main.run_ast_grep")
    def test_invalid_pattern_syntax(self, mock_run):
        """Test validating an invalid pattern with syntax error."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "ast-grep", stderr="parse error: invalid pattern"
        )

        result = _validate_rule_pattern("invalid{{{", "python")

        assert result.is_valid is False
        assert len(result.errors) > 0
        assert "parse error" in result.errors[0].lower()

    @patch("main.run_ast_grep")
    def test_empty_pattern(self, mock_run):
        """Test validating an empty pattern."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = _validate_rule_pattern("", "python")

        # Empty pattern might be valid syntactically but should be caught elsewhere
        mock_run.assert_called_once()

    @patch("main.run_ast_grep")
    def test_malformed_pattern(self, mock_run):
        """Test validating a malformed pattern."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "ast-grep", stderr="invalid pattern: unmatched brackets"
        )

        result = _validate_rule_pattern("def func(]", "python")

        assert result.is_valid is False
        assert len(result.errors) > 0

    @patch("main.run_ast_grep")
    def test_pattern_with_metavariables(self, mock_run):
        """Test validating pattern with metavariables."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = _validate_rule_pattern("def $FUNC($ARGS):", "python")

        assert result.is_valid is True
        assert len(result.errors) == 0

    @patch("main.run_ast_grep")
    def test_pattern_with_special_characters(self, mock_run):
        """Test validating pattern with special characters."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = _validate_rule_pattern("$A == $B", "typescript")

        assert result.is_valid is True

    @patch("main.run_ast_grep")
    def test_subprocess_timeout(self, mock_run):
        """Test handling subprocess timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("ast-grep", 10)

        result = _validate_rule_pattern("pattern", "python")

        assert result.is_valid is False
        assert len(result.errors) > 0

    @patch("main.run_ast_grep")
    def test_subprocess_other_error(self, mock_run):
        """Test handling other subprocess errors."""
        mock_run.side_effect = Exception("Unexpected error")

        result = _validate_rule_pattern("pattern", "python")

        assert result.is_valid is False
        assert len(result.errors) > 0
        assert "Unexpected error" in result.errors[0]

    @patch("main.run_ast_grep")
    def test_pattern_validation_with_warnings(self, mock_run):
        """Test pattern validation that returns warnings."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "ast-grep", stderr="No matches found"
        )

        result = _validate_rule_pattern("some_pattern", "python")

        # No matches is okay for validation - might generate warning
        assert len(result.errors) == 0 or len(result.warnings) > 0


class TestValidateRuleDefinition:
    """Test _validate_rule_definition function."""

    @patch("main._validate_rule_pattern")
    def test_valid_rule_all_fields(self, mock_validate_pattern):
        """Test validating a complete valid rule."""
        mock_validate_pattern.return_value = RuleValidationResult(
            is_valid=True, errors=[], warnings=[]
        )

        rule = LintingRule(
            id="no-console-log",
            language="typescript",
            severity="warning",
            message="Remove console.log",
            pattern="console.log($$$)",
            fix="Use logger"
        )

        result = _validate_rule_definition(rule)

        assert result.is_valid is True
        assert len(result.errors) == 0

    @patch("main._validate_rule_pattern")
    def test_invalid_severity(self, mock_validate_pattern):
        """Test validating rule with invalid severity."""
        mock_validate_pattern.return_value = RuleValidationResult(
            is_valid=True, errors=[], warnings=[]
        )

        rule = LintingRule(
            id="test-rule",
            language="python",
            severity="critical",  # Invalid
            message="Test",
            pattern="test"
        )

        result = _validate_rule_definition(rule)

        assert result.is_valid is False
        assert any("severity" in err.lower() for err in result.errors)

    @patch("main._validate_rule_pattern")
    @patch("main.get_supported_languages")
    def test_invalid_language(self, mock_get_langs, mock_validate_pattern):
        """Test validating rule with unsupported language."""
        mock_get_langs.return_value = ["python", "typescript", "javascript", "java"]
        mock_validate_pattern.return_value = RuleValidationResult(
            is_valid=True, errors=[], warnings=[]
        )

        rule = LintingRule(
            id="test-rule",
            language="cobol",  # Unsupported
            severity="error",
            message="Test",
            pattern="test"
        )

        result = _validate_rule_definition(rule)

        assert result.is_valid is False
        assert any("language" in err.lower() for err in result.errors)

    @patch("main._validate_rule_pattern")
    def test_invalid_id_format_not_kebab_case(self, mock_validate_pattern):
        """Test validating rule with non-kebab-case ID."""
        mock_validate_pattern.return_value = RuleValidationResult(
            is_valid=True, errors=[], warnings=[]
        )

        test_cases = [
            "NoConsoleLog",  # PascalCase
            "no_console_log",  # snake_case
            "no console log",  # spaces
            "123-rule",  # starts with number
            "NO-CONSOLE-LOG",  # uppercase
        ]

        for invalid_id in test_cases:
            rule = LintingRule(
                id=invalid_id,
                language="typescript",
                severity="warning",
                message="Test",
                pattern="test"
            )

            result = _validate_rule_definition(rule)

            assert result.is_valid is False
            assert any("kebab-case" in err.lower() for err in result.errors)

    @patch("main._validate_rule_pattern")
    def test_valid_kebab_case_id(self, mock_validate_pattern):
        """Test validating rule with valid kebab-case ID."""
        mock_validate_pattern.return_value = RuleValidationResult(
            is_valid=True, errors=[], warnings=[]
        )

        valid_ids = [
            "no-console-log",
            "prefer-const",
            "no-var",
            "require-type-hints",
        ]

        for valid_id in valid_ids:
            rule = LintingRule(
                id=valid_id,
                language="typescript",
                severity="warning",
                message="Test",
                pattern="test",
                fix="Fix"
            )

            result = _validate_rule_definition(rule)

            assert result.is_valid is True

    @patch("main._validate_rule_pattern")
    def test_empty_message(self, mock_validate_pattern):
        """Test validating rule with empty message."""
        mock_validate_pattern.return_value = RuleValidationResult(
            is_valid=True, errors=[], warnings=[]
        )

        rule = LintingRule(
            id="test-rule",
            language="python",
            severity="error",
            message="",  # Empty
            pattern="test"
        )

        result = _validate_rule_definition(rule)

        assert result.is_valid is False
        assert any("message" in err.lower() for err in result.errors)

    @patch("main._validate_rule_pattern")
    def test_whitespace_only_message(self, mock_validate_pattern):
        """Test validating rule with whitespace-only message."""
        mock_validate_pattern.return_value = RuleValidationResult(
            is_valid=True, errors=[], warnings=[]
        )

        rule = LintingRule(
            id="test-rule",
            language="python",
            severity="error",
            message="   ",  # Whitespace only
            pattern="test"
        )

        result = _validate_rule_definition(rule)

        assert result.is_valid is False
        assert any("message" in err.lower() for err in result.errors)

    @patch("main._validate_rule_pattern")
    def test_empty_pattern(self, mock_validate_pattern):
        """Test validating rule with empty pattern."""
        rule = LintingRule(
            id="test-rule",
            language="python",
            severity="error",
            message="Test",
            pattern=""  # Empty
        )

        result = _validate_rule_definition(rule)

        assert result.is_valid is False
        assert any("pattern" in err.lower() for err in result.errors)

    @patch("main._validate_rule_pattern")
    def test_pattern_validation_integration(self, mock_validate_pattern):
        """Test that pattern validation is called and integrated."""
        mock_validate_pattern.return_value = RuleValidationResult(
            is_valid=False,
            errors=["Pattern syntax error"],
            warnings=[]
        )

        rule = LintingRule(
            id="test-rule",
            language="python",
            severity="error",
            message="Test",
            pattern="invalid{{{",
            fix="Fix"
        )

        result = _validate_rule_definition(rule)

        assert result.is_valid is False
        assert "Pattern syntax error" in result.errors
        mock_validate_pattern.assert_called_once_with("invalid{{{", "python")

    @patch("main._validate_rule_pattern")
    def test_no_fix_warning(self, mock_validate_pattern):
        """Test that missing fix generates warning."""
        mock_validate_pattern.return_value = RuleValidationResult(
            is_valid=True, errors=[], warnings=[]
        )

        rule = LintingRule(
            id="test-rule",
            language="python",
            severity="error",
            message="Test",
            pattern="test",
            fix=None  # No fix
        )

        result = _validate_rule_definition(rule)

        assert result.is_valid is True
        assert len(result.warnings) > 0
        assert any("fix" in warn.lower() for warn in result.warnings)

    @patch("main._validate_rule_pattern")
    def test_with_fix_no_warning(self, mock_validate_pattern):
        """Test that having fix doesn't generate warning."""
        mock_validate_pattern.return_value = RuleValidationResult(
            is_valid=True, errors=[], warnings=[]
        )

        rule = LintingRule(
            id="test-rule",
            language="python",
            severity="error",
            message="Test",
            pattern="test",
            fix="Use something else"
        )

        result = _validate_rule_definition(rule)

        assert result.is_valid is True
        # Should only have warnings from pattern validation, not about fix
        fix_warnings = [w for w in result.warnings if "fix" in w.lower()]
        assert len(fix_warnings) == 0

    @patch("main._validate_rule_pattern")
    def test_multiple_validation_errors(self, mock_validate_pattern):
        """Test rule with multiple validation errors."""
        mock_validate_pattern.return_value = RuleValidationResult(
            is_valid=False,
            errors=["Pattern error"],
            warnings=[]
        )

        rule = LintingRule(
            id="InvalidID",  # Not kebab-case
            language="python",
            severity="critical",  # Invalid severity
            message="",  # Empty message
            pattern="invalid"
        )

        result = _validate_rule_definition(rule)

        assert result.is_valid is False
        assert len(result.errors) >= 3  # ID, severity, message, pattern


class TestSaveRuleToProject:
    """Test _save_rule_to_project function."""

    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    @patch("yaml.dump")
    def test_save_rule_creates_directory(self, mock_yaml_dump, mock_mkdir, mock_file):
        """Test that saving rule creates .ast-grep-rules directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rule = LintingRule(
                id="test-rule",
                language="python",
                severity="error",
                message="Test",
                pattern="test"
            )

            with patch("pathlib.Path.resolve", return_value=Path(tmpdir)):
                result = _save_rule_to_project(rule, tmpdir)

            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    @patch("yaml.dump")
    def test_save_rule_writes_yaml(self, mock_yaml_dump, mock_mkdir, mock_file):
        """Test that saving rule writes YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rule = LintingRule(
                id="test-rule",
                language="python",
                severity="error",
                message="Test",
                pattern="test"
            )

            with patch("pathlib.Path.resolve", return_value=Path(tmpdir)):
                result = _save_rule_to_project(rule, tmpdir)

            mock_yaml_dump.assert_called_once()
            assert mock_yaml_dump.call_args[1]["default_flow_style"] is False
            assert mock_yaml_dump.call_args[1]["sort_keys"] is False

    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    @patch("yaml.dump")
    def test_save_rule_returns_file_path(self, mock_yaml_dump, mock_mkdir, mock_file):
        """Test that saving rule returns correct file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rule = LintingRule(
                id="test-rule",
                language="python",
                severity="error",
                message="Test",
                pattern="test"
            )

            with patch("pathlib.Path.resolve", return_value=Path(tmpdir)):
                result = _save_rule_to_project(rule, tmpdir)

            assert "test-rule.yml" in result
            assert ".ast-grep-rules" in result

    @patch("builtins.open", side_effect=OSError("Permission denied"))
    @patch("pathlib.Path.mkdir")
    def test_save_rule_permission_error(self, mock_mkdir, mock_file):
        """Test handling permission error when saving rule."""
        rule = LintingRule(
            id="test-rule",
            language="python",
            severity="error",
            message="Test",
            pattern="test"
        )

        with pytest.raises(RuleStorageError) as exc_info:
            _save_rule_to_project(rule, "/nonexistent")

        assert "Permission denied" in str(exc_info.value)

    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    @patch("yaml.dump")
    def test_save_rule_with_special_characters_in_id(self, mock_yaml_dump, mock_mkdir, mock_file):
        """Test saving rule with special characters in ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rule = LintingRule(
                id="no-console-log-prod",
                language="typescript",
                severity="warning",
                message="Test",
                pattern="test"
            )

            with patch("pathlib.Path.resolve", return_value=Path(tmpdir)):
                result = _save_rule_to_project(rule, tmpdir)

            assert "no-console-log-prod.yml" in result

    @patch("builtins.open", new_callable=mock_open)
    @patch("pathlib.Path.mkdir")
    @patch("yaml.dump")
    def test_overwrite_existing_rule(self, mock_yaml_dump, mock_mkdir, mock_file):
        """Test that saving rule can overwrite existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            rule = LintingRule(
                id="test-rule",
                language="python",
                severity="error",
                message="Updated message",
                pattern="test"
            )

            with patch("pathlib.Path.resolve", return_value=Path(tmpdir)):
                result = _save_rule_to_project(rule, tmpdir)

            # Should succeed without error even if file exists
            mock_file.assert_called()


class TestLoadRuleFromFile:
    """Test _load_rule_from_file function."""

    def test_load_rule_valid_yaml(self):
        """Test loading rule from valid YAML file."""
        yaml_content = """
id: test-rule
language: python
severity: error
message: Test message
rule:
  pattern: test
note: Test note
fix: Test fix
"""

        with patch("builtins.open", mock_open(read_data=yaml_content)):
            result = _load_rule_from_file("/fake/path.yml")

        assert result.id == "test-rule"
        assert result.language == "python"
        assert result.severity == "error"
        assert result.message == "Test message"
        assert result.pattern == "test"
        assert result.note == "Test note"
        assert result.fix == "Test fix"

    def test_load_rule_minimal_yaml(self):
        """Test loading rule with only required fields."""
        yaml_content = """
id: test-rule
language: python
severity: error
message: Test message
rule:
  pattern: test
"""

        with patch("builtins.open", mock_open(read_data=yaml_content)):
            result = _load_rule_from_file("/fake/path.yml")

        assert result.id == "test-rule"
        assert result.note is None
        assert result.fix is None
        assert result.constraints is None

    def test_load_rule_malformed_yaml(self):
        """Test loading rule from malformed YAML."""
        yaml_content = """
id: test-rule
  invalid: indentation
"""

        with patch("builtins.open", mock_open(read_data=yaml_content)):
            with pytest.raises(RuleStorageError):
                _load_rule_from_file("/fake/path.yml")

    def test_load_rule_missing_file(self):
        """Test loading rule from non-existent file."""
        with patch("builtins.open", side_effect=FileNotFoundError("File not found")):
            with pytest.raises(RuleStorageError) as exc_info:
                _load_rule_from_file("/nonexistent/path.yml")

        assert "File not found" in str(exc_info.value)

    def test_load_rule_with_constraints(self):
        """Test loading rule with constraints field."""
        yaml_content = """
id: test-rule
language: python
severity: error
message: Test message
rule:
  pattern: test
constraints:
  kind: function_definition
"""

        with patch("builtins.open", mock_open(read_data=yaml_content)):
            result = _load_rule_from_file("/fake/path.yml")

        assert result.constraints == {"kind": "function_definition"}


class TestGetAvailableTemplates:
    """Test _get_available_templates function."""

    def test_get_all_templates(self):
        """Test getting all templates without filters."""
        result = _get_available_templates()

        assert len(result) == 24
        assert all(isinstance(t, RuleTemplate) for t in result)

    def test_filter_by_language_typescript(self):
        """Test filtering templates by TypeScript language."""
        result = _get_available_templates(language="typescript")

        assert all(t.language == "typescript" for t in result)
        assert len(result) >= 8  # Should have multiple TS templates

    def test_filter_by_language_python(self):
        """Test filtering templates by Python language."""
        result = _get_available_templates(language="python")

        assert all(t.language == "python" for t in result)
        assert len(result) == 7

    def test_filter_by_language_java(self):
        """Test filtering templates by Java language."""
        result = _get_available_templates(language="java")

        assert all(t.language == "java" for t in result)
        assert len(result) == 4

    def test_filter_by_category_security(self):
        """Test filtering templates by security category."""
        result = _get_available_templates(category="security")

        assert all(t.category == "security" for t in result)
        assert len(result) >= 5

    def test_filter_by_category_style(self):
        """Test filtering templates by style category."""
        result = _get_available_templates(category="style")

        assert all(t.category == "style" for t in result)
        assert len(result) >= 3

    def test_filter_by_both_language_and_category(self):
        """Test filtering by both language and category."""
        result = _get_available_templates(language="python", category="security")

        assert all(t.language == "python" and t.category == "security" for t in result)
        assert len(result) >= 3

    def test_filter_no_matches(self):
        """Test filtering with no matching templates."""
        result = _get_available_templates(language="rust", category="security")

        assert len(result) == 0

    def test_filter_case_sensitive(self):
        """Test that filtering is case-sensitive."""
        result = _get_available_templates(language="PYTHON")

        assert len(result) == 0  # Should not match due to case


class TestCreateLintingRuleTool:
    """Test create_linting_rule MCP tool."""

    @patch("main._validate_rule_definition")
    def test_create_rule_from_scratch(self, mock_validate):
        """Test creating a rule from scratch."""
        mock_validate.return_value = RuleValidationResult(
            is_valid=True,
            errors=[],
            warnings=["No fix suggestion provided"]
        )

        result = create_linting_rule(
            rule_name="test-rule",
            description="Test message",
            pattern="test($$$)",
            severity="warning",
            language="python",
            suggested_fix=None,
            note=None,
            save_to_project=False,
            project_folder=None,
            use_template=None
        )

        assert result["rule"]["id"] == "test-rule"
        assert result["rule"]["language"] == "python"
        assert result["rule"]["severity"] == "warning"
        assert result["validation"]["is_valid"] is True
        assert result["saved_to"] is None
        assert "yaml" in result

    @patch("main._validate_rule_definition")
    def test_create_rule_from_template(self, mock_validate):
        """Test creating a rule from a template."""
        mock_validate.return_value = RuleValidationResult(
            is_valid=True,
            errors=[],
            warnings=[]
        )

        result = create_linting_rule(
            rule_name="my-no-var",
            description="Custom message",
            pattern="",  # Will use template pattern
            severity="",  # Will use template severity
            language="",  # Will use template language
            suggested_fix=None,
            note=None,
            save_to_project=False,
            project_folder=None,
            use_template="no-var"
        )

        assert result["rule"]["id"] == "my-no-var"
        assert result["rule"]["language"] == "typescript"
        assert result["rule"]["pattern"] == "var $NAME = $$$"
        assert result["validation"]["is_valid"] is True

    @patch("main._validate_rule_definition")
    @patch("main._save_rule_to_project")
    def test_create_and_save_rule(self, mock_save, mock_validate):
        """Test creating and saving a rule to project."""
        mock_validate.return_value = RuleValidationResult(
            is_valid=True,
            errors=[],
            warnings=[]
        )
        mock_save.return_value = "/fake/project/.ast-grep-rules/test-rule.yml"

        with tempfile.TemporaryDirectory() as tmpdir:
            result = create_linting_rule(
                rule_name="test-rule",
                description="Test message",
                pattern="test($$$)",
                severity="warning",
                language="python",
                suggested_fix="Fix it",
                note=None,
                save_to_project=True,
                project_folder=tmpdir,
                use_template=None
            )

        assert result["saved_to"] is not None
        assert "test-rule.yml" in result["saved_to"]
        mock_save.assert_called_once()

    @patch("main._validate_rule_definition")
    def test_create_rule_missing_project_folder(self, mock_validate):
        """Test creating rule with save_to_project=True but no project_folder."""
        mock_validate.return_value = RuleValidationResult(
            is_valid=True,
            errors=[],
            warnings=[]
        )

        with pytest.raises(ValueError) as exc_info:
            create_linting_rule(
                rule_name="test-rule",
                description="Test message",
                pattern="test($$$)",
                severity="warning",
                language="python",
                suggested_fix=None,
                note=None,
                save_to_project=True,
                project_folder=None,  # Missing
                use_template=None
            )

        assert "project_folder is required" in str(exc_info.value)

    @patch("main._validate_rule_definition")
    def test_create_rule_invalid_template(self, mock_validate):
        """Test creating rule with non-existent template."""
        with pytest.raises(ValueError) as exc_info:
            create_linting_rule(
                rule_name="test-rule",
                description="Test message",
                pattern="test",
                severity="warning",
                language="python",
                suggested_fix=None,
                note=None,
                save_to_project=False,
                project_folder=None,
                use_template="nonexistent-template"
            )

        assert "not found" in str(exc_info.value).lower()

    @patch("main._validate_rule_definition")
    def test_create_rule_validation_fails(self, mock_validate):
        """Test creating rule when validation fails."""
        mock_validate.return_value = RuleValidationResult(
            is_valid=False,
            errors=["Invalid severity"],
            warnings=[]
        )

        with pytest.raises(RuleValidationError):
            create_linting_rule(
                rule_name="test-rule",
                description="Test message",
                pattern="test",
                severity="critical",  # Invalid
                language="python",
                suggested_fix=None,
                note=None,
                save_to_project=True,
                project_folder="/fake",
                use_template=None
            )

    @patch("main._validate_rule_definition")
    def test_create_rule_all_parameters(self, mock_validate):
        """Test creating rule with all parameters specified."""
        mock_validate.return_value = RuleValidationResult(
            is_valid=True,
            errors=[],
            warnings=[]
        )

        result = create_linting_rule(
            rule_name="comprehensive-rule",
            description="Comprehensive test message",
            pattern="test($$$)",
            severity="error",
            language="typescript",
            suggested_fix="Fix suggestion",
            note="Additional note",
            save_to_project=False,
            project_folder=None,
            use_template=None
        )

        assert result["rule"]["id"] == "comprehensive-rule"
        assert result["rule"]["message"] == "Comprehensive test message"
        assert result["rule"]["pattern"] == "test($$$)"
        assert result["rule"]["severity"] == "error"
        assert result["rule"]["language"] == "typescript"
        assert result["rule"]["fix"] == "Fix suggestion"
        assert result["rule"]["note"] == "Additional note"

    @patch("main._validate_rule_definition")
    def test_create_rule_template_override(self, mock_validate):
        """Test creating rule from template with field overrides."""
        mock_validate.return_value = RuleValidationResult(
            is_valid=True,
            errors=[],
            warnings=[]
        )

        result = create_linting_rule(
            rule_name="my-custom-rule",
            description="Custom message",
            pattern="var $X = $Y",  # Override pattern
            severity="error",  # Override severity
            language="typescript",
            suggested_fix="Custom fix",  # Override fix
            note=None,
            save_to_project=False,
            project_folder=None,
            use_template="no-var"
        )

        assert result["rule"]["pattern"] == "var $X = $Y"
        assert result["rule"]["severity"] == "error"
        assert result["rule"]["fix"] == "Custom fix"

    @patch("main._validate_rule_definition")
    def test_create_rule_yaml_output(self, mock_validate):
        """Test that rule is converted to YAML format."""
        mock_validate.return_value = RuleValidationResult(
            is_valid=True,
            errors=[],
            warnings=[]
        )

        result = create_linting_rule(
            rule_name="test-rule",
            description="Test message",
            pattern="test",
            severity="warning",
            language="python",
            suggested_fix=None,
            note=None,
            save_to_project=False,
            project_folder=None,
            use_template=None
        )

        assert "yaml" in result
        assert isinstance(result["yaml"], str)
        assert "id: test-rule" in result["yaml"]

    @patch("main._validate_rule_definition")
    def test_create_rule_validation_result_structure(self, mock_validate):
        """Test validation result structure in response."""
        mock_validate.return_value = RuleValidationResult(
            is_valid=True,
            errors=[],
            warnings=["Warning message"]
        )

        result = create_linting_rule(
            rule_name="test-rule",
            description="Test message",
            pattern="test",
            severity="warning",
            language="python",
            suggested_fix=None,
            note=None,
            save_to_project=False,
            project_folder=None,
            use_template=None
        )

        assert "validation" in result
        assert result["validation"]["is_valid"] is True
        assert isinstance(result["validation"]["errors"], list)
        assert isinstance(result["validation"]["warnings"], list)
        assert len(result["validation"]["warnings"]) > 0


class TestListRuleTemplatesTool:
    """Test list_rule_templates MCP tool."""

    def test_list_all_templates(self):
        """Test listing all templates without filters."""
        result = list_rule_templates(language=None, category=None)

        assert "total_templates" in result
        assert result["total_templates"] == 24
        assert "languages" in result
        assert "categories" in result
        assert "templates" in result
        assert len(result["templates"]) == 24

    def test_list_templates_by_language(self):
        """Test listing templates filtered by language."""
        result = list_rule_templates(language="python", category=None)

        assert result["total_templates"] == 7
        assert all(t["language"] == "python" for t in result["templates"])

    def test_list_templates_by_category(self):
        """Test listing templates filtered by category."""
        result = list_rule_templates(language=None, category="security")

        assert all(t["category"] == "security" for t in result["templates"])
        assert result["total_templates"] >= 5

    def test_list_templates_by_both_filters(self):
        """Test listing templates with both filters."""
        result = list_rule_templates(language="python", category="security")

        assert all(
            t["language"] == "python" and t["category"] == "security"
            for t in result["templates"]
        )

    def test_list_templates_languages_field(self):
        """Test that languages field contains all available languages."""
        result = list_rule_templates(language=None, category=None)

        assert "python" in result["languages"]
        assert "typescript" in result["languages"]
        assert "java" in result["languages"]

    def test_list_templates_categories_field(self):
        """Test that categories field contains all available categories."""
        result = list_rule_templates(language=None, category=None)

        assert "general" in result["categories"]
        assert "security" in result["categories"]
        assert "style" in result["categories"]

    def test_list_templates_structure(self):
        """Test template structure in response."""
        result = list_rule_templates(language=None, category=None)

        template = result["templates"][0]
        assert "id" in template
        assert "name" in template
        assert "description" in template
        assert "language" in template
        assert "severity" in template
        assert "pattern" in template
        assert "category" in template

    def test_list_templates_invalid_language(self):
        """Test listing templates with invalid language filter."""
        result = list_rule_templates(language="cobol", category=None)

        assert result["total_templates"] == 0
        assert len(result["templates"]) == 0

    def test_list_templates_invalid_category(self):
        """Test listing templates with invalid category filter."""
        result = list_rule_templates(language=None, category="nonexistent")

        assert result["total_templates"] == 0
        assert len(result["templates"]) == 0

    def test_list_templates_response_structure(self):
        """Test complete response structure."""
        result = list_rule_templates(language=None, category=None)

        assert isinstance(result, dict)
        assert isinstance(result["total_templates"], int)
        assert isinstance(result["languages"], list)
        assert isinstance(result["categories"], list)
        assert isinstance(result["templates"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
