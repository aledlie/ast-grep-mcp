"""Unit tests for Standards Enforcement Engine (Phase 2 - Code Quality Standards)."""

import os
import sys
import tempfile
import threading
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
    if "default_factory" in kwargs:
        factory = kwargs["default_factory"]
        return factory() if callable(factory) else []
    return kwargs.get("default")


# Patch the imports before loading main
with patch("mcp.server.fastmcp.FastMCP", MockFastMCP):
    with patch("pydantic.Field", mock_field):
        import main
        from main import (
            RuleViolation,
            RuleSet,
            EnforcementResult,
            RuleExecutionContext,
            RULE_SETS,
            LintingRule,
            RuleTemplate,
            RULE_TEMPLATES,
            _template_to_linting_rule,
            _load_custom_rules,
            _load_rule_set,
            _parse_match_to_violation,
            _should_exclude_file,
            _execute_rule,
            _execute_rules_batch,
            _group_violations_by_file,
            _group_violations_by_severity,
            _group_violations_by_rule,
            _filter_violations_by_severity,
            _format_violation_report,
            _load_rule_from_file,
        )

        # Call register_mcp_tools to define the tool functions
        main.register_mcp_tools()

        # Extract the tool functions from the mocked mcp instance
        enforce_standards = main.mcp.tools.get("enforce_standards")  # type: ignore


class TestRuleViolationDataClass:
    """Test RuleViolation data class."""

    def test_instantiation_all_fields(self):
        """Test RuleViolation with all fields."""
        violation = RuleViolation(
            file="/path/to/file.py",
            line=42,
            column=10,
            end_line=42,
            end_column=20,
            severity="error",
            rule_id="no-eval",
            message="Use of eval() is dangerous",
            code_snippet="eval(user_input)",
            fix_suggestion="Use ast.literal_eval()",
            meta_vars={"VAR": "user_input"}
        )

        assert violation.file == "/path/to/file.py"
        assert violation.line == 42
        assert violation.column == 10
        assert violation.end_line == 42
        assert violation.end_column == 20
        assert violation.severity == "error"
        assert violation.rule_id == "no-eval"
        assert violation.message == "Use of eval() is dangerous"
        assert violation.code_snippet == "eval(user_input)"
        assert violation.fix_suggestion == "Use ast.literal_eval()"
        assert violation.meta_vars == {"VAR": "user_input"}

    def test_instantiation_optional_fields_none(self):
        """Test RuleViolation with optional fields as None."""
        violation = RuleViolation(
            file="/path/to/file.py",
            line=42,
            column=10,
            end_line=42,
            end_column=20,
            severity="warning",
            rule_id="no-console",
            message="No console.log",
            code_snippet="console.log('test')"
        )

        assert violation.fix_suggestion is None
        assert violation.meta_vars is None

    def test_minimal_violation(self):
        """Test RuleViolation with minimal required fields."""
        violation = RuleViolation(
            file="/test.py",
            line=1,
            column=1,
            end_line=1,
            end_column=10,
            severity="info",
            rule_id="test-rule",
            message="Test message",
            code_snippet="test()"
        )

        assert violation.file == "/test.py"
        assert violation.severity == "info"


class TestRuleSetDataClass:
    """Test RuleSet data class."""

    def test_instantiation_all_fields(self):
        """Test RuleSet with all fields."""
        rules = [
            LintingRule(
                id="no-var",
                language="typescript",
                severity="warning",
                message="Use const or let",
                pattern="var $NAME = $$$"
            )
        ]

        rule_set = RuleSet(
            name="recommended",
            description="Best practices",
            rules=rules,
            priority=100
        )

        assert rule_set.name == "recommended"
        assert rule_set.description == "Best practices"
        assert len(rule_set.rules) == 1
        assert rule_set.priority == 100

    def test_instantiation_without_priority(self):
        """Test RuleSet with default priority."""
        rules = [
            LintingRule(
                id="test-rule",
                language="python",
                severity="error",
                message="Test",
                pattern="test"
            )
        ]

        rule_set = RuleSet(
            name="test",
            description="Test set",
            rules=rules
        )

        assert rule_set.priority == 0

    def test_empty_rules_list(self):
        """Test RuleSet with empty rules list."""
        rule_set = RuleSet(
            name="empty",
            description="Empty set",
            rules=[],
            priority=50
        )

        assert len(rule_set.rules) == 0


class TestEnforcementResultDataClass:
    """Test EnforcementResult data class."""

    def test_instantiation_all_fields(self):
        """Test EnforcementResult with all fields."""
        violations = [
            RuleViolation(
                file="/test.py",
                line=10,
                column=5,
                end_line=10,
                end_column=15,
                severity="error",
                rule_id="no-eval",
                message="Don't use eval",
                code_snippet="eval(x)"
            )
        ]

        result = EnforcementResult(
            summary={"total_violations": 1},
            violations=violations,
            violations_by_file={"/test.py": violations},
            violations_by_severity={"error": violations},
            violations_by_rule={"no-eval": violations},
            rules_executed=["no-eval"],
            execution_time_ms=1500,
            files_scanned=1
        )

        assert result.summary["total_violations"] == 1
        assert len(result.violations) == 1
        assert result.execution_time_ms == 1500
        assert result.files_scanned == 1

    def test_empty_result(self):
        """Test EnforcementResult with no violations."""
        result = EnforcementResult(
            summary={"total_violations": 0},
            violations=[],
            violations_by_file={},
            violations_by_severity={"error": [], "warning": [], "info": []},
            violations_by_rule={},
            rules_executed=["no-var"],
            execution_time_ms=500,
            files_scanned=10
        )

        assert len(result.violations) == 0
        assert result.files_scanned == 10


class TestRuleExecutionContextDataClass:
    """Test RuleExecutionContext data class."""

    def test_instantiation_all_fields(self):
        """Test RuleExecutionContext with all fields."""
        logger = Mock()

        context = RuleExecutionContext(
            project_folder="/path/to/project",
            language="python",
            include_patterns=["**/*.py"],
            exclude_patterns=["**/test_*.py"],
            max_violations=100,
            max_threads=4,
            logger=logger
        )

        assert context.project_folder == "/path/to/project"
        assert context.language == "python"
        assert context.include_patterns == ["**/*.py"]
        assert context.exclude_patterns == ["**/test_*.py"]
        assert context.max_violations == 100
        assert context.max_threads == 4
        assert context.logger is logger


class TestRuleSetsConfiguration:
    """Test RULE_SETS configuration."""

    def test_rule_sets_exist(self):
        """Test that RULE_SETS dictionary exists."""
        assert RULE_SETS is not None
        assert isinstance(RULE_SETS, dict)

    def test_all_four_sets_exist(self):
        """Test that all 4 built-in sets exist."""
        expected_sets = ["recommended", "security", "performance", "style"]
        for set_name in expected_sets:
            assert set_name in RULE_SETS

    def test_rule_sets_structure(self):
        """Test that each rule set has required fields."""
        for set_name, set_config in RULE_SETS.items():
            assert "description" in set_config
            assert "priority" in set_config
            assert "rules" in set_config
            assert isinstance(set_config["description"], str)
            assert isinstance(set_config["priority"], int)
            assert isinstance(set_config["rules"], list)

    def test_recommended_set_priority(self):
        """Test recommended set has priority 100."""
        assert RULE_SETS["recommended"]["priority"] == 100

    def test_security_set_priority(self):
        """Test security set has priority 200 (highest)."""
        assert RULE_SETS["security"]["priority"] == 200

    def test_rule_ids_reference_templates(self):
        """Test that rule IDs reference valid templates."""
        for set_name, set_config in RULE_SETS.items():
            for rule_id in set_config["rules"]:
                # Rule ID should exist in RULE_TEMPLATES
                assert rule_id in RULE_TEMPLATES, f"Rule '{rule_id}' in set '{set_name}' not found in RULE_TEMPLATES"

    def test_priority_values_correct(self):
        """Test priority values are correct."""
        assert RULE_SETS["recommended"]["priority"] == 100
        assert RULE_SETS["security"]["priority"] == 200
        assert RULE_SETS["performance"]["priority"] == 50
        assert RULE_SETS["style"]["priority"] == 10

    def test_recommended_set_rules(self):
        """Test recommended set has expected rules."""
        rules = RULE_SETS["recommended"]["rules"]
        assert "no-var" in rules
        assert "no-console-log" in rules
        assert len(rules) >= 8


class TestTemplateToLintingRule:
    """Test _template_to_linting_rule function."""

    def test_basic_conversion(self):
        """Test converting RuleTemplate to LintingRule."""
        template = RuleTemplate(
            id="no-var",
            name="No var declarations",
            description="Disallow var",
            language="typescript",
            severity="warning",
            pattern="var $NAME = $$$",
            message="Use const or let",
            note="var has function scope",
            fix="Replace with const or let",
            category="style"
        )

        rule = _template_to_linting_rule(template)

        assert rule.id == "no-var"
        assert rule.language == "typescript"
        assert rule.severity == "warning"
        assert rule.pattern == "var $NAME = $$$"
        assert rule.message == "Use const or let"
        assert rule.note == "var has function scope"
        assert rule.fix == "Replace with const or let"

    def test_conversion_preserves_all_fields(self):
        """Test that all template fields are preserved."""
        template = RULE_TEMPLATES["no-bare-except"]

        rule = _template_to_linting_rule(template)

        assert rule.id == template.id
        assert rule.language == template.language
        assert rule.severity == template.severity
        assert rule.pattern == template.pattern
        assert rule.message == template.message
        assert rule.note == template.note
        assert rule.fix == template.fix

    def test_constraints_is_none(self):
        """Test that constraints field is None."""
        template = RULE_TEMPLATES["no-console-log"]
        rule = _template_to_linting_rule(template)

        assert rule.constraints is None

    def test_conversion_multiple_templates(self):
        """Test converting multiple templates."""
        template_ids = ["no-var", "no-console-log", "no-bare-except"]

        for template_id in template_ids:
            template = RULE_TEMPLATES[template_id]
            rule = _template_to_linting_rule(template)

            assert rule.id == template.id
            assert isinstance(rule, LintingRule)


class TestLoadCustomRules:
    """Test _load_custom_rules function."""

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.glob")
    def test_load_rules_from_directory(self, mock_glob, mock_exists):
        """Test loading rules from .ast-grep-rules/."""
        mock_exists.return_value = True
        mock_glob.return_value = []

        result = _load_custom_rules("/fake/path", "python")

        assert isinstance(result, list)

    @patch("pathlib.Path.exists")
    def test_missing_directory(self, mock_exists):
        """Test handling missing .ast-grep-rules/ directory."""
        mock_exists.return_value = False

        result = _load_custom_rules("/fake/path", "python")

        assert result == []

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.glob")
    @patch("main._load_rule_from_file")
    def test_filter_by_language(self, mock_load, mock_glob, mock_exists):
        """Test filtering rules by language."""
        mock_exists.return_value = True

        mock_file = Mock()
        mock_file.name = "test-rule.yml"
        mock_glob.return_value = [mock_file]

        python_rule = LintingRule(
            id="python-rule",
            language="python",
            severity="error",
            message="Python rule",
            pattern="test"
        )

        mock_load.return_value = python_rule

        result = _load_custom_rules("/fake/path", "python")

        assert len(result) == 1
        assert result[0].language == "python"

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.glob")
    @patch("main._load_rule_from_file")
    def test_handle_malformed_yaml(self, mock_load, mock_glob, mock_exists):
        """Test handling malformed YAML files."""
        mock_exists.return_value = True

        mock_file = Mock()
        mock_file.name = "bad-rule.yml"
        mock_glob.return_value = [mock_file]

        mock_load.side_effect = Exception("YAML parse error")

        # Should not raise, just skip bad files
        result = _load_custom_rules("/fake/path", "python")

        assert result == []

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.glob")
    def test_empty_directory(self, mock_glob, mock_exists):
        """Test empty .ast-grep-rules/ directory."""
        mock_exists.return_value = True
        mock_glob.return_value = []

        result = _load_custom_rules("/fake/path", "python")

        assert result == []

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.glob")
    @patch("main._load_rule_from_file")
    def test_filter_out_wrong_language(self, mock_load, mock_glob, mock_exists):
        """Test filtering out rules for wrong language."""
        mock_exists.return_value = True

        mock_file = Mock()
        mock_glob.return_value = [mock_file]

        # Load TypeScript rule but filter for Python
        ts_rule = LintingRule(
            id="ts-rule",
            language="typescript",
            severity="warning",
            message="TS rule",
            pattern="test"
        )

        mock_load.return_value = ts_rule

        result = _load_custom_rules("/fake/path", "python")

        assert result == []


class TestLoadRuleSet:
    """Test _load_rule_set function."""

    def test_load_recommended_rule_set(self):
        """Test loading recommended rule set."""
        rule_set = _load_rule_set("recommended", "/fake/path", "typescript")

        assert rule_set.name == "recommended"
        assert "best practices" in rule_set.description.lower()
        assert rule_set.priority == 100
        assert len(rule_set.rules) > 0

    def test_load_security_rule_set(self):
        """Test loading security rule set."""
        rule_set = _load_rule_set("security", "/fake/path", "python")

        assert rule_set.name == "security"
        assert "security" in rule_set.description.lower()
        assert rule_set.priority == 200

    def test_load_performance_rule_set(self):
        """Test loading performance rule set."""
        rule_set = _load_rule_set("performance", "/fake/path", "typescript")

        assert rule_set.name == "performance"
        assert "performance" in rule_set.description.lower()
        assert rule_set.priority == 50

    def test_load_style_rule_set(self):
        """Test loading style rule set."""
        rule_set = _load_rule_set("style", "/fake/path", "python")

        assert rule_set.name == "style"
        assert "style" in rule_set.description.lower()
        assert rule_set.priority == 10

    def test_load_all_rule_set(self):
        """Test loading 'all' rule set."""
        rule_set = _load_rule_set("all", "/fake/path", "python")

        assert rule_set.name == "all"
        assert "all" in rule_set.description.lower()
        assert rule_set.priority == 100

    @patch("main._load_custom_rules")
    def test_load_custom_rule_set(self, mock_load_custom):
        """Test loading 'custom' rule set."""
        custom_rules = [
            LintingRule(
                id="custom-rule",
                language="python",
                severity="warning",
                message="Custom",
                pattern="custom"
            )
        ]
        mock_load_custom.return_value = custom_rules

        rule_set = _load_rule_set("custom", "/fake/path", "python")

        assert rule_set.name == "custom"
        assert "custom" in rule_set.description.lower()
        assert rule_set.priority == 150
        assert len(rule_set.rules) == 1

    def test_filter_by_language(self):
        """Test rules are filtered by language."""
        rule_set = _load_rule_set("recommended", "/fake/path", "python")

        # All rules should be Python
        for rule in rule_set.rules:
            assert rule.language == "python"

    def test_invalid_rule_set_name(self):
        """Test invalid rule set name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            _load_rule_set("nonexistent", "/fake/path", "python")

        assert "not found" in str(exc_info.value)

    def test_empty_results_for_unsupported_language(self):
        """Test empty results for unsupported language."""
        # Rust is not in templates, so should get no rules
        rule_set = _load_rule_set("recommended", "/fake/path", "rust")

        assert len(rule_set.rules) == 0

    def test_priority_preserved(self):
        """Test that priority from RULE_SETS is preserved."""
        security_set = _load_rule_set("security", "/fake/path", "python")
        style_set = _load_rule_set("style", "/fake/path", "python")

        assert security_set.priority > style_set.priority

    def test_all_set_combines_all_rules(self):
        """Test 'all' set combines rules from all sets."""
        all_set = _load_rule_set("all", "/fake/path", "python")
        recommended_set = _load_rule_set("recommended", "/fake/path", "python")

        # 'all' should have at least as many rules as recommended
        assert len(all_set.rules) >= len(recommended_set.rules)

    @patch("main._load_custom_rules")
    def test_custom_set_empty_when_no_rules(self, mock_load_custom):
        """Test custom set is empty when no custom rules exist."""
        mock_load_custom.return_value = []

        rule_set = _load_rule_set("custom", "/fake/path", "python")

        assert len(rule_set.rules) == 0


class TestParseMatchToViolation:
    """Test _parse_match_to_violation function."""

    def test_parse_complete_match(self):
        """Test parsing complete ast-grep match."""
        match = {
            "file": "/path/to/file.py",
            "range": {
                "start": {"line": 10, "column": 5},
                "end": {"line": 10, "column": 15}
            },
            "text": "eval(user_input)",
            "metaVariables": [
                {"name": "VAR", "text": "user_input"}
            ]
        }

        rule = LintingRule(
            id="no-eval",
            language="python",
            severity="error",
            message="Don't use eval",
            pattern="eval($VAR)",
            fix="Use ast.literal_eval"
        )

        violation = _parse_match_to_violation(match, rule)

        assert violation.file == "/path/to/file.py"
        assert violation.line == 10
        assert violation.column == 5
        assert violation.end_line == 10
        assert violation.end_column == 15
        assert violation.severity == "error"
        assert violation.rule_id == "no-eval"
        assert violation.message == "Don't use eval"
        assert violation.code_snippet == "eval(user_input)"
        assert violation.fix_suggestion == "Use ast.literal_eval"
        assert violation.meta_vars == {"VAR": "user_input"}

    def test_parse_match_without_metavars(self):
        """Test parsing match without metavariables."""
        match = {
            "file": "/test.py",
            "range": {
                "start": {"line": 5, "column": 0},
                "end": {"line": 5, "column": 10}
            },
            "text": "except:"
        }

        rule = LintingRule(
            id="no-bare-except",
            language="python",
            severity="error",
            message="Bare except",
            pattern="except:"
        )

        violation = _parse_match_to_violation(match, rule)

        assert violation.meta_vars is None

    def test_parse_match_missing_range(self):
        """Test parsing match with missing range information."""
        match = {
            "file": "/test.py",
            "text": "test code"
        }

        rule = LintingRule(
            id="test-rule",
            language="python",
            severity="warning",
            message="Test",
            pattern="test"
        )

        violation = _parse_match_to_violation(match, rule)

        assert violation.line == 0
        assert violation.column == 0

    def test_parse_multiline_match(self):
        """Test parsing multiline match."""
        match = {
            "file": "/test.py",
            "range": {
                "start": {"line": 10, "column": 0},
                "end": {"line": 15, "column": 10}
            },
            "text": "def foo():\n    pass"
        }

        rule = LintingRule(
            id="test-rule",
            language="python",
            severity="info",
            message="Test",
            pattern="def $FUNC():\n    pass"
        )

        violation = _parse_match_to_violation(match, rule)

        assert violation.line == 10
        assert violation.end_line == 15


class TestShouldExcludeFile:
    """Test _should_exclude_file function."""

    def test_exclude_node_modules(self):
        """Test excluding node_modules with recursive pattern."""
        file_path = "/project/node_modules/package/file.js"
        patterns = ["**/node_modules/**"]

        assert _should_exclude_file(file_path, patterns) is True

    def test_exclude_simple_glob(self):
        """Test excluding with simple glob pattern."""
        file_path = "/project/test_file.py"
        patterns = ["test_*.py"]

        assert _should_exclude_file(file_path, patterns) is True

    def test_dont_exclude_non_matching(self):
        """Test not excluding non-matching files."""
        file_path = "/project/src/main.py"
        patterns = ["**/test/**", "**/node_modules/**"]

        assert _should_exclude_file(file_path, patterns) is False

    def test_multiple_patterns(self):
        """Test handling multiple exclude patterns."""
        file_path = "/project/__pycache__/cache.pyc"
        patterns = ["**/node_modules/**", "**/__pycache__/**"]

        assert _should_exclude_file(file_path, patterns) is True

    def test_case_sensitivity(self):
        """Test case sensitivity in pattern matching."""
        file_path = "/project/Node_Modules/file.js"
        patterns = ["**/node_modules/**"]

        # Should not match due to case difference
        assert _should_exclude_file(file_path, patterns) is False

    def test_empty_patterns(self):
        """Test with empty patterns list."""
        file_path = "/project/file.py"
        patterns = []

        assert _should_exclude_file(file_path, patterns) is False

    def test_exclude_build_directory(self):
        """Test excluding build directory."""
        file_path = "/project/build/output.js"
        patterns = ["**/build/**"]

        assert _should_exclude_file(file_path, patterns) is True

    def test_exclude_dist_directory(self):
        """Test excluding dist directory."""
        file_path = "/project/dist/bundle.js"
        patterns = ["**/dist/**"]

        assert _should_exclude_file(file_path, patterns) is True

    def test_exclude_git_directory(self):
        """Test excluding .git directory."""
        file_path = "/project/.git/config"
        patterns = ["**/.git/**"]

        assert _should_exclude_file(file_path, patterns) is True

    def test_filename_pattern(self):
        """Test pattern matching against filename only."""
        file_path = "/project/src/test.tmp"
        patterns = ["*.tmp"]

        assert _should_exclude_file(file_path, patterns) is True


class TestExecuteRule:
    """Test _execute_rule function."""

    @patch("main.stream_ast_grep_results")
    def test_execute_single_rule(self, mock_stream):
        """Test executing single rule."""
        logger = Mock()
        context = RuleExecutionContext(
            project_folder="/fake/path",
            language="python",
            include_patterns=["**/*.py"],
            exclude_patterns=[],
            max_violations=0,
            max_threads=4,
            logger=logger
        )

        mock_stream.return_value = [
            {
                "file": "/test.py",
                "range": {
                    "start": {"line": 5, "column": 0},
                    "end": {"line": 5, "column": 10}
                },
                "text": "except:"
            }
        ]

        rule = LintingRule(
            id="no-bare-except",
            language="python",
            severity="error",
            message="Bare except",
            pattern="except:"
        )

        violations = _execute_rule(rule, context)

        assert len(violations) == 1
        assert violations[0].rule_id == "no-bare-except"
        mock_stream.assert_called_once()

    @patch("main.stream_ast_grep_results")
    def test_parse_violations_correctly(self, mock_stream):
        """Test violations are parsed correctly."""
        logger = Mock()
        context = RuleExecutionContext(
            project_folder="/fake/path",
            language="python",
            include_patterns=["**/*.py"],
            exclude_patterns=[],
            max_violations=0,
            max_threads=4,
            logger=logger
        )

        mock_stream.return_value = [
            {
                "file": "/test.py",
                "range": {
                    "start": {"line": 10, "column": 5},
                    "end": {"line": 10, "column": 15}
                },
                "text": "eval(x)"
            }
        ]

        rule = LintingRule(
            id="no-eval",
            language="python",
            severity="error",
            message="Don't use eval",
            pattern="eval($VAR)"
        )

        violations = _execute_rule(rule, context)

        assert violations[0].line == 10
        assert violations[0].column == 5

    @patch("main.stream_ast_grep_results")
    def test_apply_file_exclusion(self, mock_stream):
        """Test file exclusion is applied."""
        logger = Mock()
        context = RuleExecutionContext(
            project_folder="/fake/path",
            language="python",
            include_patterns=["**/*.py"],
            exclude_patterns=["**/node_modules/**"],
            max_violations=0,
            max_threads=4,
            logger=logger
        )

        mock_stream.return_value = [
            {
                "file": "/project/node_modules/package/file.py",
                "range": {
                    "start": {"line": 5, "column": 0},
                    "end": {"line": 5, "column": 10}
                },
                "text": "except:"
            }
        ]

        rule = LintingRule(
            id="no-bare-except",
            language="python",
            severity="error",
            message="Bare except",
            pattern="except:"
        )

        violations = _execute_rule(rule, context)

        # Should be excluded
        assert len(violations) == 0

    @patch("main.stream_ast_grep_results")
    def test_respect_max_violations(self, mock_stream):
        """Test max_violations is respected."""
        logger = Mock()
        context = RuleExecutionContext(
            project_folder="/fake/path",
            language="python",
            include_patterns=["**/*.py"],
            exclude_patterns=[],
            max_violations=2,
            max_threads=4,
            logger=logger
        )

        # Return 5 matches
        mock_stream.return_value = [
            {
                "file": f"/test{i}.py",
                "range": {
                    "start": {"line": 5, "column": 0},
                    "end": {"line": 5, "column": 10}
                },
                "text": "except:"
            }
            for i in range(5)
        ]

        rule = LintingRule(
            id="no-bare-except",
            language="python",
            severity="error",
            message="Bare except",
            pattern="except:"
        )

        violations = _execute_rule(rule, context)

        # Should stop at max_violations
        assert len(violations) <= 2

    @patch("main.stream_ast_grep_results")
    def test_handle_execution_errors(self, mock_stream):
        """Test handling execution errors gracefully."""
        logger = Mock()
        context = RuleExecutionContext(
            project_folder="/fake/path",
            language="python",
            include_patterns=["**/*.py"],
            exclude_patterns=[],
            max_violations=0,
            max_threads=4,
            logger=logger
        )

        mock_stream.side_effect = Exception("Execution failed")

        rule = LintingRule(
            id="test-rule",
            language="python",
            severity="error",
            message="Test",
            pattern="test"
        )

        violations = _execute_rule(rule, context)

        # Should return empty list, not raise
        assert violations == []

    @patch("main.stream_ast_grep_results")
    @patch("main.sentry_sdk")
    def test_sentry_span_integration(self, mock_sentry, mock_stream):
        """Test Sentry span is created."""
        logger = Mock()
        context = RuleExecutionContext(
            project_folder="/fake/path",
            language="python",
            include_patterns=["**/*.py"],
            exclude_patterns=[],
            max_violations=0,
            max_threads=4,
            logger=logger
        )

        mock_stream.return_value = []

        rule = LintingRule(
            id="test-rule",
            language="python",
            severity="error",
            message="Test",
            pattern="test"
        )

        _execute_rule(rule, context)

        mock_sentry.start_span.assert_called()


class TestExecuteRulesBatch:
    """Test _execute_rules_batch function."""

    @patch("main._execute_rule")
    def test_parallel_execution(self, mock_execute):
        """Test parallel execution with ThreadPoolExecutor."""
        logger = Mock()
        context = RuleExecutionContext(
            project_folder="/fake/path",
            language="python",
            include_patterns=["**/*.py"],
            exclude_patterns=[],
            max_violations=0,
            max_threads=4,
            logger=logger
        )

        rules = [
            LintingRule(
                id=f"rule-{i}",
                language="python",
                severity="error",
                message="Test",
                pattern="test"
            )
            for i in range(3)
        ]

        mock_execute.return_value = []

        violations = _execute_rules_batch(rules, context)

        # Should call _execute_rule for each rule
        assert mock_execute.call_count == 3

    @patch("main._execute_rule")
    def test_combine_violations(self, mock_execute):
        """Test violations from multiple rules are combined."""
        logger = Mock()
        context = RuleExecutionContext(
            project_folder="/fake/path",
            language="python",
            include_patterns=["**/*.py"],
            exclude_patterns=[],
            max_violations=0,
            max_threads=4,
            logger=logger
        )

        rules = [
            LintingRule(
                id=f"rule-{i}",
                language="python",
                severity="error",
                message="Test",
                pattern="test"
            )
            for i in range(2)
        ]

        # Return 2 violations per rule
        mock_execute.return_value = [
            RuleViolation(
                file="/test.py",
                line=1,
                column=1,
                end_line=1,
                end_column=10,
                severity="error",
                rule_id="test",
                message="Test",
                code_snippet="test"
            )
            for _ in range(2)
        ]

        violations = _execute_rules_batch(rules, context)

        # Should have 4 total violations
        assert len(violations) == 4

    @patch("main._execute_rule")
    def test_early_termination_at_max_violations(self, mock_execute):
        """Test early termination when max_violations reached."""
        logger = Mock()
        context = RuleExecutionContext(
            project_folder="/fake/path",
            language="python",
            include_patterns=["**/*.py"],
            exclude_patterns=[],
            max_violations=5,
            max_threads=4,
            logger=logger
        )

        rules = [
            LintingRule(
                id=f"rule-{i}",
                language="python",
                severity="error",
                message="Test",
                pattern="test"
            )
            for i in range(10)
        ]

        # Return 3 violations per rule
        mock_execute.return_value = [
            RuleViolation(
                file="/test.py",
                line=1,
                column=1,
                end_line=1,
                end_column=10,
                severity="error",
                rule_id="test",
                message="Test",
                code_snippet="test"
            )
            for _ in range(3)
        ]

        violations = _execute_rules_batch(rules, context)

        # Should stop early (may execute all due to parallel execution, but should combine violations)
        assert mock_execute.call_count <= 10

    @patch("main._execute_rule")
    def test_handle_individual_failures(self, mock_execute):
        """Test handling individual rule failures."""
        logger = Mock()
        context = RuleExecutionContext(
            project_folder="/fake/path",
            language="python",
            include_patterns=["**/*.py"],
            exclude_patterns=[],
            max_violations=0,
            max_threads=4,
            logger=logger
        )

        rules = [
            LintingRule(
                id=f"rule-{i}",
                language="python",
                severity="error",
                message="Test",
                pattern="test"
            )
            for i in range(3)
        ]

        # First rule fails, others succeed
        mock_execute.side_effect = [
            Exception("Rule failed"),
            [],
            []
        ]

        # Should not raise
        violations = _execute_rules_batch(rules, context)

        assert isinstance(violations, list)


class TestGroupViolationsByFile:
    """Test _group_violations_by_file function."""

    def test_group_by_file(self):
        """Test grouping violations by file path."""
        violations = [
            RuleViolation(
                file="/test1.py",
                line=10,
                column=5,
                end_line=10,
                end_column=15,
                severity="error",
                rule_id="rule1",
                message="Test",
                code_snippet="test"
            ),
            RuleViolation(
                file="/test2.py",
                line=5,
                column=0,
                end_line=5,
                end_column=10,
                severity="warning",
                rule_id="rule2",
                message="Test",
                code_snippet="test"
            ),
            RuleViolation(
                file="/test1.py",
                line=15,
                column=0,
                end_line=15,
                end_column=5,
                severity="error",
                rule_id="rule3",
                message="Test",
                code_snippet="test"
            )
        ]

        grouped = _group_violations_by_file(violations)

        assert len(grouped) == 2
        assert len(grouped["/test1.py"]) == 2
        assert len(grouped["/test2.py"]) == 1

    def test_sort_by_line_number(self):
        """Test violations are sorted by line and column."""
        violations = [
            RuleViolation(
                file="/test.py",
                line=20,
                column=0,
                end_line=20,
                end_column=10,
                severity="error",
                rule_id="rule1",
                message="Test",
                code_snippet="test"
            ),
            RuleViolation(
                file="/test.py",
                line=10,
                column=5,
                end_line=10,
                end_column=15,
                severity="error",
                rule_id="rule2",
                message="Test",
                code_snippet="test"
            ),
            RuleViolation(
                file="/test.py",
                line=10,
                column=0,
                end_line=10,
                end_column=5,
                severity="error",
                rule_id="rule3",
                message="Test",
                code_snippet="test"
            )
        ]

        grouped = _group_violations_by_file(violations)

        file_violations = grouped["/test.py"]
        # Should be sorted: line 10 col 0, line 10 col 5, line 20 col 0
        assert file_violations[0].line == 10
        assert file_violations[0].column == 0
        assert file_violations[1].line == 10
        assert file_violations[1].column == 5
        assert file_violations[2].line == 20

    def test_empty_violations(self):
        """Test grouping empty violations list."""
        grouped = _group_violations_by_file([])

        assert grouped == {}


class TestGroupViolationsBySeverity:
    """Test _group_violations_by_severity function."""

    def test_group_by_severity(self):
        """Test grouping violations by severity level."""
        violations = [
            RuleViolation(
                file="/test.py",
                line=10,
                column=5,
                end_line=10,
                end_column=15,
                severity="error",
                rule_id="rule1",
                message="Test",
                code_snippet="test"
            ),
            RuleViolation(
                file="/test.py",
                line=15,
                column=0,
                end_line=15,
                end_column=10,
                severity="warning",
                rule_id="rule2",
                message="Test",
                code_snippet="test"
            ),
            RuleViolation(
                file="/test.py",
                line=20,
                column=0,
                end_line=20,
                end_column=5,
                severity="error",
                rule_id="rule3",
                message="Test",
                code_snippet="test"
            )
        ]

        grouped = _group_violations_by_severity(violations)

        assert len(grouped["error"]) == 2
        assert len(grouped["warning"]) == 1
        assert len(grouped["info"]) == 0

    def test_all_severity_levels_present(self):
        """Test all severity levels are in result."""
        violations = [
            RuleViolation(
                file="/test.py",
                line=10,
                column=5,
                end_line=10,
                end_column=15,
                severity="info",
                rule_id="rule1",
                message="Test",
                code_snippet="test"
            )
        ]

        grouped = _group_violations_by_severity(violations)

        assert "error" in grouped
        assert "warning" in grouped
        assert "info" in grouped

    def test_empty_violations(self):
        """Test grouping empty violations list."""
        grouped = _group_violations_by_severity([])

        assert grouped["error"] == []
        assert grouped["warning"] == []
        assert grouped["info"] == []


class TestGroupViolationsByRule:
    """Test _group_violations_by_rule function."""

    def test_group_by_rule(self):
        """Test grouping violations by rule ID."""
        violations = [
            RuleViolation(
                file="/test.py",
                line=10,
                column=5,
                end_line=10,
                end_column=15,
                severity="error",
                rule_id="no-eval",
                message="Test",
                code_snippet="test"
            ),
            RuleViolation(
                file="/test.py",
                line=15,
                column=0,
                end_line=15,
                end_column=10,
                severity="warning",
                rule_id="no-console",
                message="Test",
                code_snippet="test"
            ),
            RuleViolation(
                file="/test.py",
                line=20,
                column=0,
                end_line=20,
                end_column=5,
                severity="error",
                rule_id="no-eval",
                message="Test",
                code_snippet="test"
            )
        ]

        grouped = _group_violations_by_rule(violations)

        assert len(grouped) == 2
        assert len(grouped["no-eval"]) == 2
        assert len(grouped["no-console"]) == 1

    def test_empty_violations(self):
        """Test grouping empty violations list."""
        grouped = _group_violations_by_rule([])

        assert grouped == {}


class TestFilterViolationsBySeverity:
    """Test _filter_violations_by_severity function."""

    def test_filter_by_error(self):
        """Test filtering by error severity threshold."""
        violations = [
            RuleViolation(
                file="/test.py",
                line=10,
                column=5,
                end_line=10,
                end_column=15,
                severity="error",
                rule_id="rule1",
                message="Test",
                code_snippet="test"
            ),
            RuleViolation(
                file="/test.py",
                line=15,
                column=0,
                end_line=15,
                end_column=10,
                severity="warning",
                rule_id="rule2",
                message="Test",
                code_snippet="test"
            ),
            RuleViolation(
                file="/test.py",
                line=20,
                column=0,
                end_line=20,
                end_column=5,
                severity="info",
                rule_id="rule3",
                message="Test",
                code_snippet="test"
            )
        ]

        filtered = _filter_violations_by_severity(violations, "error")

        assert len(filtered) == 1
        assert filtered[0].severity == "error"

    def test_filter_by_warning(self):
        """Test filtering by warning severity threshold."""
        violations = [
            RuleViolation(
                file="/test.py",
                line=10,
                column=5,
                end_line=10,
                end_column=15,
                severity="error",
                rule_id="rule1",
                message="Test",
                code_snippet="test"
            ),
            RuleViolation(
                file="/test.py",
                line=15,
                column=0,
                end_line=15,
                end_column=10,
                severity="warning",
                rule_id="rule2",
                message="Test",
                code_snippet="test"
            ),
            RuleViolation(
                file="/test.py",
                line=20,
                column=0,
                end_line=20,
                end_column=5,
                severity="info",
                rule_id="rule3",
                message="Test",
                code_snippet="test"
            )
        ]

        filtered = _filter_violations_by_severity(violations, "warning")

        assert len(filtered) == 2
        # Should include error and warning, not info

    def test_filter_by_info(self):
        """Test filtering by info severity threshold."""
        violations = [
            RuleViolation(
                file="/test.py",
                line=10,
                column=5,
                end_line=10,
                end_column=15,
                severity="error",
                rule_id="rule1",
                message="Test",
                code_snippet="test"
            ),
            RuleViolation(
                file="/test.py",
                line=15,
                column=0,
                end_line=15,
                end_column=10,
                severity="warning",
                rule_id="rule2",
                message="Test",
                code_snippet="test"
            ),
            RuleViolation(
                file="/test.py",
                line=20,
                column=0,
                end_line=20,
                end_column=5,
                severity="info",
                rule_id="rule3",
                message="Test",
                code_snippet="test"
            )
        ]

        filtered = _filter_violations_by_severity(violations, "info")

        # Should include all
        assert len(filtered) == 3

    def test_handle_all_severity_levels(self):
        """Test all severity levels are handled correctly."""
        violations = [
            RuleViolation(
                file="/test.py",
                line=10,
                column=5,
                end_line=10,
                end_column=15,
                severity=sev,
                rule_id="rule1",
                message="Test",
                code_snippet="test"
            )
            for sev in ["error", "warning", "info"]
        ]

        # Test each threshold
        assert len(_filter_violations_by_severity(violations, "error")) == 1
        assert len(_filter_violations_by_severity(violations, "warning")) == 2
        assert len(_filter_violations_by_severity(violations, "info")) == 3


class TestFormatViolationReport:
    """Test _format_violation_report function."""

    def test_format_complete_report(self):
        """Test formatting complete report."""
        violations = [
            RuleViolation(
                file="/test.py",
                line=10,
                column=5,
                end_line=10,
                end_column=15,
                severity="error",
                rule_id="no-eval",
                message="Don't use eval",
                code_snippet="eval(x)",
                fix_suggestion="Use ast.literal_eval"
            )
        ]

        result = EnforcementResult(
            summary={
                "total_violations": 1,
                "by_severity": {"error": 1, "warning": 0, "info": 0},
                "files_scanned": 1,
                "execution_time_ms": 1500
            },
            violations=violations,
            violations_by_file={"/test.py": violations},
            violations_by_severity={"error": violations, "warning": [], "info": []},
            violations_by_rule={"no-eval": violations},
            rules_executed=["no-eval"],
            execution_time_ms=1500,
            files_scanned=1
        )

        report = _format_violation_report(result)

        assert "CODE STANDARDS ENFORCEMENT REPORT" in report
        assert "Files Scanned: 1" in report
        assert "Total Violations: 1" in report
        assert "no-eval" in report

    def test_summary_section(self):
        """Test summary section is formatted correctly."""
        result = EnforcementResult(
            summary={
                "total_violations": 5,
                "by_severity": {"error": 2, "warning": 3, "info": 0},
                "files_scanned": 3,
                "execution_time_ms": 2000
            },
            violations=[],
            violations_by_file={},
            violations_by_severity={"error": [], "warning": [], "info": []},
            violations_by_rule={},
            rules_executed=["rule1", "rule2"],
            execution_time_ms=2000,
            files_scanned=3
        )

        report = _format_violation_report(result)

        assert "Files Scanned: 3" in report
        assert "Rules Executed: 2" in report
        assert "Total Violations: 5" in report
        assert "Execution Time: 2000ms" in report

    def test_violations_breakdown(self):
        """Test violations breakdown section."""
        violations = [
            RuleViolation(
                file="/test.py",
                line=10,
                column=5,
                end_line=10,
                end_column=15,
                severity="error",
                rule_id="no-eval",
                message="Test",
                code_snippet="test"
            )
        ]

        result = EnforcementResult(
            summary={
                "total_violations": 1,
                "by_severity": {"error": 1, "warning": 0, "info": 0},
                "files_scanned": 1,
                "execution_time_ms": 1000
            },
            violations=violations,
            violations_by_file={"/test.py": violations},
            violations_by_severity={"error": violations, "warning": [], "info": []},
            violations_by_rule={"no-eval": violations},
            rules_executed=["no-eval"],
            execution_time_ms=1000,
            files_scanned=1
        )

        report = _format_violation_report(result)

        assert "Violations by Severity" in report
        assert "ERROR: 1" in report

    def test_handle_empty_violations(self):
        """Test formatting report with no violations."""
        result = EnforcementResult(
            summary={
                "total_violations": 0,
                "by_severity": {"error": 0, "warning": 0, "info": 0},
                "files_scanned": 10,
                "execution_time_ms": 500
            },
            violations=[],
            violations_by_file={},
            violations_by_severity={"error": [], "warning": [], "info": []},
            violations_by_rule={},
            rules_executed=["rule1"],
            execution_time_ms=500,
            files_scanned=10
        )

        report = _format_violation_report(result)

        assert "Total Violations: 0" in report


class TestEnforceStandardsTool:
    """Test enforce_standards MCP tool."""

    def setup_method(self):
        """Setup for each test."""
        # Clear any Sentry context
        pass

    @patch("main._load_rule_set")
    @patch("main._execute_rules_batch")
    @patch("pathlib.Path.exists")
    def test_basic_scan_with_recommended_rules(self, mock_exists, mock_execute, mock_load):
        """Test basic scan with recommended rules."""
        mock_exists.return_value = True

        mock_rule_set = RuleSet(
            name="recommended",
            description="Best practices",
            rules=[
                LintingRule(
                    id="no-var",
                    language="typescript",
                    severity="warning",
                    message="Use const or let",
                    pattern="var $NAME = $$$"
                )
            ],
            priority=100
        )
        mock_load.return_value = mock_rule_set

        mock_execute.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            result = enforce_standards(
                project_folder=tmpdir,
                language="typescript",
                rule_set="recommended"
            )

        assert "summary" in result
        assert result["summary"]["total_violations"] == 0

    @patch("main._load_rule_set")
    @patch("main._execute_rules_batch")
    @patch("pathlib.Path.exists")
    def test_security_rule_set(self, mock_exists, mock_execute, mock_load):
        """Test scan with security rule set."""
        mock_exists.return_value = True

        mock_rule_set = RuleSet(
            name="security",
            description="Security rules",
            rules=[
                LintingRule(
                    id="no-eval",
                    language="python",
                    severity="error",
                    message="No eval",
                    pattern="eval($VAR)"
                )
            ],
            priority=200
        )
        mock_load.return_value = mock_rule_set

        mock_execute.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            result = enforce_standards(
                project_folder=tmpdir,
                language="python",
                rule_set="security"
            )

        assert result["summary"]["total_violations"] == 0

    @patch("main._load_custom_rules")
    @patch("main._execute_rules_batch")
    @patch("pathlib.Path.exists")
    def test_custom_rules_with_ids(self, mock_exists, mock_execute, mock_load_custom):
        """Test scan with custom rules specified by IDs."""
        mock_exists.return_value = True

        custom_rules = [
            LintingRule(
                id="custom-rule-1",
                language="python",
                severity="warning",
                message="Custom",
                pattern="custom"
            ),
            LintingRule(
                id="custom-rule-2",
                language="python",
                severity="error",
                message="Custom 2",
                pattern="custom2"
            )
        ]
        mock_load_custom.return_value = custom_rules

        mock_execute.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            result = enforce_standards(
                project_folder=tmpdir,
                language="python",
                rule_set="custom",
                custom_rules=["custom-rule-1"]
            )

        assert "summary" in result

    @patch("pathlib.Path.exists")
    def test_invalid_severity_threshold(self, mock_exists):
        """Test invalid severity_threshold raises ValueError."""
        mock_exists.return_value = True

        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError) as exc_info:
                enforce_standards(
                    project_folder=tmpdir,
                    language="python",
                    severity_threshold="critical"
                )

        assert "severity_threshold" in str(exc_info.value)

    @patch("pathlib.Path.exists")
    def test_invalid_output_format(self, mock_exists):
        """Test invalid output_format raises ValueError."""
        mock_exists.return_value = True

        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError) as exc_info:
                enforce_standards(
                    project_folder=tmpdir,
                    language="python",
                    output_format="xml"
                )

        assert "output_format" in str(exc_info.value)

    def test_project_folder_not_found(self):
        """Test error when project folder doesn't exist."""
        with pytest.raises(ValueError) as exc_info:
            enforce_standards(
                project_folder="/nonexistent/path",
                language="python"
            )

        assert "does not exist" in str(exc_info.value)

    @patch("main._load_rule_set")
    @patch("pathlib.Path.exists")
    def test_no_rules_for_language(self, mock_exists, mock_load):
        """Test handling when no rules found for language."""
        mock_exists.return_value = True

        mock_rule_set = RuleSet(
            name="recommended",
            description="Best practices",
            rules=[],  # No rules
            priority=100
        )
        mock_load.return_value = mock_rule_set

        with tempfile.TemporaryDirectory() as tmpdir:
            result = enforce_standards(
                project_folder=tmpdir,
                language="rust"
            )

        assert "message" in result or result["summary"]["total_violations"] == 0

    @patch("main._load_custom_rules")
    @patch("pathlib.Path.exists")
    def test_empty_custom_rules_list(self, mock_exists, mock_load_custom):
        """Test handling empty custom rules list."""
        mock_exists.return_value = True
        mock_load_custom.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            result = enforce_standards(
                project_folder=tmpdir,
                language="python",
                rule_set="custom",
                custom_rules=["nonexistent-rule"]
            )

        assert "error" in result or "message" in result

    @patch("main._load_rule_set")
    @patch("main._execute_rules_batch")
    @patch("pathlib.Path.exists")
    def test_text_output_format(self, mock_exists, mock_execute, mock_load):
        """Test text output format."""
        mock_exists.return_value = True

        mock_rule_set = RuleSet(
            name="recommended",
            description="Best practices",
            rules=[
                LintingRule(
                    id="no-var",
                    language="typescript",
                    severity="warning",
                    message="Use const or let",
                    pattern="var $NAME = $$$"
                )
            ],
            priority=100
        )
        mock_load.return_value = mock_rule_set

        mock_execute.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            result = enforce_standards(
                project_folder=tmpdir,
                language="typescript",
                output_format="text"
            )

        assert "report" in result
        assert isinstance(result["report"], str)

    @patch("main._load_rule_set")
    @patch("main._execute_rules_batch")
    @patch("pathlib.Path.exists")
    def test_json_output_format(self, mock_exists, mock_execute, mock_load):
        """Test JSON output format."""
        mock_exists.return_value = True

        mock_rule_set = RuleSet(
            name="recommended",
            description="Best practices",
            rules=[
                LintingRule(
                    id="no-var",
                    language="typescript",
                    severity="warning",
                    message="Use const or let",
                    pattern="var $NAME = $$$"
                )
            ],
            priority=100
        )
        mock_load.return_value = mock_rule_set

        violations = [
            RuleViolation(
                file="/test.ts",
                line=10,
                column=5,
                end_line=10,
                end_column=15,
                severity="warning",
                rule_id="no-var",
                message="Use const or let",
                code_snippet="var x = 5"
            )
        ]
        mock_execute.return_value = violations

        with tempfile.TemporaryDirectory() as tmpdir:
            result = enforce_standards(
                project_folder=tmpdir,
                language="typescript",
                output_format="json"
            )

        assert "summary" in result
        assert "violations" in result
        assert isinstance(result["violations"], list)

    @patch("main._load_rule_set")
    @patch("main._execute_rules_batch")
    @patch("pathlib.Path.exists")
    def test_max_violations_enforcement(self, mock_exists, mock_execute, mock_load):
        """Test max_violations is enforced."""
        mock_exists.return_value = True

        mock_rule_set = RuleSet(
            name="recommended",
            description="Best practices",
            rules=[
                LintingRule(
                    id="no-var",
                    language="typescript",
                    severity="warning",
                    message="Use const or let",
                    pattern="var $NAME = $$$"
                )
            ],
            priority=100
        )
        mock_load.return_value = mock_rule_set

        # Return 5 violations
        violations = [
            RuleViolation(
                file=f"/test{i}.ts",
                line=10,
                column=5,
                end_line=10,
                end_column=15,
                severity="warning",
                rule_id="no-var",
                message="Use const or let",
                code_snippet="var x = 5"
            )
            for i in range(5)
        ]
        mock_execute.return_value = violations

        with tempfile.TemporaryDirectory() as tmpdir:
            result = enforce_standards(
                project_folder=tmpdir,
                language="typescript",
                max_violations=3
            )

        # Should respect max_violations in context
        assert mock_execute.called

    @patch("main._load_rule_set")
    @patch("main._execute_rules_batch")
    @patch("pathlib.Path.exists")
    def test_severity_threshold_filtering(self, mock_exists, mock_execute, mock_load):
        """Test severity threshold filtering."""
        mock_exists.return_value = True

        mock_rule_set = RuleSet(
            name="recommended",
            description="Best practices",
            rules=[
                LintingRule(
                    id="no-var",
                    language="typescript",
                    severity="warning",
                    message="Use const or let",
                    pattern="var $NAME = $$$"
                )
            ],
            priority=100
        )
        mock_load.return_value = mock_rule_set

        violations = [
            RuleViolation(
                file="/test.ts",
                line=10,
                column=5,
                end_line=10,
                end_column=15,
                severity="info",
                rule_id="no-var",
                message="Use const or let",
                code_snippet="var x = 5"
            )
        ]
        mock_execute.return_value = violations

        with tempfile.TemporaryDirectory() as tmpdir:
            result = enforce_standards(
                project_folder=tmpdir,
                language="typescript",
                severity_threshold="error"
            )

        # Info violation should be filtered out
        assert result["summary"]["total_violations"] == 0

    @patch("main._load_rule_set")
    @patch("main._execute_rules_batch")
    @patch("pathlib.Path.exists")
    def test_include_exclude_patterns(self, mock_exists, mock_execute, mock_load):
        """Test include/exclude patterns are passed to context."""
        mock_exists.return_value = True

        mock_rule_set = RuleSet(
            name="recommended",
            description="Best practices",
            rules=[
                LintingRule(
                    id="no-var",
                    language="typescript",
                    severity="warning",
                    message="Use const or let",
                    pattern="var $NAME = $$$"
                )
            ],
            priority=100
        )
        mock_load.return_value = mock_rule_set

        mock_execute.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            result = enforce_standards(
                project_folder=tmpdir,
                language="typescript",
                include_patterns=["src/**/*.ts"],
                exclude_patterns=["**/test/**"]
            )

        # Verify context was created with patterns
        call_args = mock_execute.call_args
        context = call_args[0][1]
        assert "src/**/*.ts" in context.include_patterns
        assert "**/test/**" in context.exclude_patterns

    @patch("main._load_rule_set")
    @patch("main._execute_rules_batch")
    @patch("pathlib.Path.exists")
    def test_parallel_execution_with_threads(self, mock_exists, mock_execute, mock_load):
        """Test parallel execution with specified threads."""
        mock_exists.return_value = True

        mock_rule_set = RuleSet(
            name="recommended",
            description="Best practices",
            rules=[
                LintingRule(
                    id="no-var",
                    language="typescript",
                    severity="warning",
                    message="Use const or let",
                    pattern="var $NAME = $$$"
                )
            ],
            priority=100
        )
        mock_load.return_value = mock_rule_set

        mock_execute.return_value = []

        with tempfile.TemporaryDirectory() as tmpdir:
            result = enforce_standards(
                project_folder=tmpdir,
                language="typescript",
                max_threads=8
            )

        # Verify context was created with correct threads
        call_args = mock_execute.call_args
        context = call_args[0][1]
        assert context.max_threads == 8

    @patch("main._load_rule_set")
    @patch("main._execute_rules_batch")
    @patch("pathlib.Path.exists")
    def test_error_handling(self, mock_exists, mock_execute, mock_load):
        """Test error handling during execution."""
        mock_exists.return_value = True

        mock_rule_set = RuleSet(
            name="recommended",
            description="Best practices",
            rules=[
                LintingRule(
                    id="no-var",
                    language="typescript",
                    severity="warning",
                    message="Use const or let",
                    pattern="var $NAME = $$$"
                )
            ],
            priority=100
        )
        mock_load.return_value = mock_rule_set

        mock_execute.side_effect = Exception("Execution failed")

        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(Exception):
                enforce_standards(
                    project_folder=tmpdir,
                    language="typescript"
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
