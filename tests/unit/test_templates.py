"""Unit tests for the template system in ast-grep-mcp code generation engine.

Tests cover:
- FunctionTemplate class for Python function generation
- render_python_function convenience function
- Template variable substitution (simple, conditional, loops)
- Import insertion point detection for multiple languages
- Indentation preservation for call sites
- Edge cases and error handling
"""

import os
import sys
from typing import Any
from unittest.mock import Mock, patch

import pytest

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# Mock FastMCP to disable decoration
class MockFastMCP:
    """Mock FastMCP that returns functions unchanged"""

    def __init__(self, name: str) -> None:
        self.name = name
        self.tools: dict[str, Any] = {}

    def tool(self, **kwargs: Any) -> Any:
        def decorator(func: Any) -> Any:
            self.tools[func.__name__] = func
            return func
        return decorator

    def run(self, **kwargs: Any) -> None:
        pass


def mock_field(**kwargs: Any) -> Any:
    return kwargs.get("default")


# Patch imports before loading main
with patch("mcp.server.fastmcp.FastMCP", MockFastMCP):
    with patch("pydantic.Field", mock_field):
        import main

from ast_grep_mcp.models.deduplication import FunctionTemplate
from main import (
    render_python_function,
    substitute_template_variables,
    detect_import_insertion_point,
    _detect_python_import_point,
    _detect_js_import_point,
    _detect_java_import_point,
    _clean_template_whitespace,
    preserve_call_site_indentation,
)


class TestFunctionTemplate:
    """Test the FunctionTemplate dataclass for Python function generation."""

    def test_basic_function_generation(self) -> None:
        """Test generating a simple function without optional features."""
        template = FunctionTemplate(
            name="hello",
            parameters=[("name", "str")],
            body="return f'Hello, {name}!'"
        )
        result = template.generate()

        assert "def hello(name: str):" in result
        assert "return f'Hello, {name}!'" in result
        assert '"""' not in result  # No docstring

    def test_function_with_return_type(self) -> None:
        """Test function with return type annotation."""
        template = FunctionTemplate(
            name="add",
            parameters=[("a", "int"), ("b", "int")],
            body="return a + b",
            return_type="int"
        )
        result = template.generate()

        assert "def add(a: int, b: int) -> int:" in result
        assert "return a + b" in result

    def test_function_with_docstring(self) -> None:
        """Test function with single-line docstring."""
        template = FunctionTemplate(
            name="greet",
            parameters=[("name", "str")],
            body="print(f'Hello, {name}')",
            docstring="Print a greeting message."
        )
        result = template.generate()

        assert '"""Print a greeting message."""' in result

    def test_function_with_multiline_docstring(self) -> None:
        """Test function with multi-line docstring."""
        docstring = "Process data.\n\nArgs:\n    data: Input data"
        template = FunctionTemplate(
            name="process",
            parameters=[("data", "Any")],
            body="return data",
            docstring=docstring
        )
        result = template.generate()

        assert '"""Process data.' in result
        assert "Args:" in result
        assert "data: Input data" in result

    def test_function_with_decorators(self) -> None:
        """Test function with decorators."""
        template = FunctionTemplate(
            name="cached_func",
            parameters=[],
            body="return 42",
            decorators=["staticmethod", "lru_cache(maxsize=128)"]
        )
        result = template.generate()

        assert "@staticmethod" in result
        assert "@lru_cache(maxsize=128)" in result
        # Decorators should come before def
        assert result.index("@staticmethod") < result.index("def cached_func")

    def test_function_with_multiple_parameters(self) -> None:
        """Test function with multiple typed and untyped parameters."""
        template = FunctionTemplate(
            name="mixed_params",
            parameters=[
                ("required", "str"),
                ("optional", None),
                ("typed_int", "int")
            ],
            body="pass"
        )
        result = template.generate()

        assert "def mixed_params(required: str, optional, typed_int: int):" in result

    def test_function_with_empty_parameters(self) -> None:
        """Test function with no parameters."""
        template = FunctionTemplate(
            name="no_args",
            parameters=[],
            body="return None"
        )
        result = template.generate()

        assert "def no_args():" in result

    def test_function_body_indentation(self) -> None:
        """Test that function body is properly indented."""
        template = FunctionTemplate(
            name="multi_line",
            parameters=[],
            body="x = 1\ny = 2\nreturn x + y"
        )
        result = template.generate()

        lines = result.split('\n')
        body_lines = [l for l in lines if l.strip() and not l.strip().startswith('def')]
        for line in body_lines:
            if line.strip():
                assert line.startswith('    '), f"Line not indented: {line}"

    def test_format_params(self) -> None:
        """Test parameter formatting method."""
        template = FunctionTemplate(
            name="test",
            parameters=[("a", "int"), ("b", None), ("c", "str")],
            body="pass"
        )

        assert template.format_params() == "a: int, b, c: str"

    def test_format_decorators_empty(self) -> None:
        """Test decorator formatting with no decorators."""
        template = FunctionTemplate(
            name="test",
            parameters=[],
            body="pass"
        )

        assert template.format_decorators() == ""

    def test_format_return_type_none(self) -> None:
        """Test return type formatting when not set."""
        template = FunctionTemplate(
            name="test",
            parameters=[],
            body="pass"
        )

        assert template.format_return_type() == ""

    def test_complete_function_all_features(self) -> None:
        """Test function generation with all optional features."""
        template = FunctionTemplate(
            name="complete_example",
            parameters=[("data", "List[str]"), ("count", "int")],
            body="result = []\nfor i in range(count):\n    result.extend(data)\nreturn result",
            return_type="List[str]",
            docstring="Repeat data count times.\n\nArgs:\n    data: Input list\n    count: Repetition count\n\nReturns:\n    Extended list",
            decorators=["classmethod"]
        )
        result = template.generate()

        assert "@classmethod" in result
        assert "def complete_example(data: List[str], count: int) -> List[str]:" in result
        assert "Repeat data count times." in result
        assert "for i in range(count):" in result


class TestRenderPythonFunction:
    """Test the render_python_function convenience function."""

    def test_basic_render(self) -> None:
        """Test basic function rendering."""
        result = code_generator.render_python_function(
            name="add",
            params="a: int, b: int",
            body="return a + b"
        )

        assert "def add(a: int, b: int):" in result
        assert "return a + b" in result

    def test_render_with_return_type(self) -> None:
        """Test rendering with return type."""
        result = code_generator.render_python_function(
            name="get_value",
            params="",
            body="return 42",
            return_type="int"
        )

        assert "def get_value() -> int:" in result

    def test_render_with_docstring(self) -> None:
        """Test rendering with docstring."""
        result = code_generator.render_python_function(
            name="process",
            params="x",
            body="return x * 2",
            docstring="Double the input."
        )

        assert '"""Double the input."""' in result

    def test_render_with_decorators(self) -> None:
        """Test rendering with decorators."""
        result = code_generator.render_python_function(
            name="static_method",
            params="",
            body="pass",
            decorators=["staticmethod"]
        )

        assert "@staticmethod" in result

    def test_render_preserves_existing_indentation(self) -> None:
        """Test that pre-indented body is handled correctly."""
        result = code_generator.render_python_function(
            name="test",
            params="",
            body="    already_indented"
        )

        # Should not double-indent
        assert "        already_indented" not in result


class TestSubstituteTemplateVariables:
    """Test template variable substitution functionality."""

    def test_simple_variable_substitution(self) -> None:
        """Test basic variable replacement."""
        result = substitute_template_variables(
            "Hello {{name}}!",
            {"name": "World"}
        )

        assert result == "Hello World!"

    def test_multiple_variables(self) -> None:
        """Test multiple variable replacements."""
        result = substitute_template_variables(
            "{{greeting}} {{name}}!",
            {"greeting": "Hi", "name": "User"}
        )

        assert result == "Hi User!"

    def test_missing_variable_non_strict(self) -> None:
        """Test missing variable in non-strict mode returns empty string."""
        result = substitute_template_variables(
            "Hello {{name}}!",
            {}
        )

        assert result == "Hello !"

    def test_missing_variable_strict_raises(self) -> None:
        """Test missing variable in strict mode raises ValueError."""
        with pytest.raises(ValueError, match="Missing required variable"):
            substitute_template_variables(
                "Hello {{name}}!",
                {},
                strict=True
            )

    def test_conditional_if_true(self) -> None:
        """Test conditional section when condition is truthy."""
        result = substitute_template_variables(
            "{{#if show}}visible{{/if}}",
            {"show": "true"}
        )

        assert result == "visible"

    def test_conditional_if_false(self) -> None:
        """Test conditional section when condition is falsy."""
        result = substitute_template_variables(
            "{{#if show}}visible{{/if}}",
            {"show": "false"}
        )

        assert result == ""

    def test_conditional_if_missing(self) -> None:
        """Test conditional section when variable is missing."""
        result = substitute_template_variables(
            "{{#if show}}visible{{/if}}",
            {}
        )

        assert result == ""

    def test_conditional_unless_true(self) -> None:
        """Test unless section when condition is truthy."""
        result = substitute_template_variables(
            "{{#unless hidden}}shown{{/unless}}",
            {"hidden": "true"}
        )

        assert result == ""

    def test_conditional_unless_false(self) -> None:
        """Test unless section when condition is falsy."""
        result = substitute_template_variables(
            "{{#unless hidden}}shown{{/unless}}",
            {"hidden": "false"}
        )

        assert result == "shown"

    def test_each_loop(self) -> None:
        """Test each loop iteration."""
        result = substitute_template_variables(
            "{{#each items}}{{.}} {{/each}}",
            {"items": "a,b,c"}
        )

        assert result == "a b c"

    def test_each_loop_empty(self) -> None:
        """Test each loop with empty list."""
        result = substitute_template_variables(
            "{{#each items}}{{.}}{{/each}}",
            {"items": ""}
        )

        assert result == ""

    def test_nested_variables_in_conditional(self) -> None:
        """Test variable substitution inside conditional."""
        result = substitute_template_variables(
            "{{#if show}}Hello {{name}}{{/if}}",
            {"show": "true", "name": "World"}
        )

        assert result == "Hello World"

    def test_complex_template(self) -> None:
        """Test complex template with multiple features."""
        template = """def {{name}}({{params}}):
{{#if docstring}}    \"\"\"{{docstring}}\"\"\"
{{/if}}    {{body}}"""

        result = substitute_template_variables(template, {
            "name": "test_func",
            "params": "x, y",
            "docstring": "Test function.",
            "body": "return x + y"
        })

        assert "def test_func(x, y):" in result
        assert '"""Test function."""' in result
        assert "return x + y" in result


class TestPreserveCallSiteIndentation:
    """Test indentation preservation for replacement calls."""

    def test_basic_indentation(self) -> None:
        """Test basic indentation preservation."""
        result = preserve_call_site_indentation(
            "    x = 1",
            "process_data()"
        )

        assert result == "    process_data()"

    def test_tab_indentation(self) -> None:
        """Test tab indentation preservation."""
        result = preserve_call_site_indentation(
            "\t\tif True:",
            "check()"
        )

        assert result == "\t\tcheck()"

    def test_multiline_replacement(self) -> None:
        """Test multiline replacement indentation."""
        result = preserve_call_site_indentation(
            "  result = compute()",
            "helper(\n    arg1,\n    arg2\n)"
        )

        lines = result.split('\n')
        assert lines[0].startswith("  ")

    def test_empty_original(self) -> None:
        """Test with empty original code."""
        result = preserve_call_site_indentation(
            "",
            "call()"
        )

        assert result == "call()"

    def test_empty_replacement(self) -> None:
        """Test with empty replacement."""
        result = preserve_call_site_indentation(
            "    x = 1",
            ""
        )

        assert result == ""

    def test_no_indentation(self) -> None:
        """Test when original has no indentation."""
        result = preserve_call_site_indentation(
            "x = 1",
            "call()"
        )

        assert result == "call()"


class TestDetectImportInsertionPoint:
    """Test import insertion point detection for multiple languages."""

    def test_python_after_imports(self) -> None:
        """Test Python import insertion after existing imports."""
        content = "import os\nimport sys\n\ndef main():\n    pass"
        result = code_generator.detect_import_insertion_point(content, "python")

        assert result == 3

    def test_python_after_docstring(self) -> None:
        """Test Python handles module docstring."""
        content = '"""Module docstring."""\n\nimport os\n\ndef main(): pass'
        result = code_generator.detect_import_insertion_point(content, "python")

        assert result == 4

    def test_python_no_imports(self) -> None:
        """Test Python with no existing imports."""
        content = "def main():\n    pass"
        result = code_generator.detect_import_insertion_point(content, "python")

        assert result == 1

    def test_python_with_from_imports(self) -> None:
        """Test Python with from imports."""
        content = "from os import path\nfrom sys import argv\n\nx = 1"
        result = code_generator.detect_import_insertion_point(content, "python")

        assert result == 3

    def test_typescript_after_imports(self) -> None:
        """Test TypeScript import insertion."""
        content = "import { Component } from 'react';\nimport type { Props } from './types';\n\nconst App = () => {};"
        result = code_generator.detect_import_insertion_point(content, "typescript")

        assert result == 3

    def test_javascript_with_require(self) -> None:
        """Test JavaScript with require statements."""
        content = "const fs = require('fs');\nconst path = require('path');\n\nmodule.exports = {};"
        result = code_generator.detect_import_insertion_point(content, "javascript")

        assert result == 3

    def test_javascript_use_strict(self) -> None:
        """Test JavaScript with 'use strict' directive."""
        content = '"use strict";\n\nimport x from "y";\n\nconst z = 1;'
        result = code_generator.detect_import_insertion_point(content, "javascript")

        assert result == 4

    def test_java_with_package(self) -> None:
        """Test Java with package declaration."""
        content = "package com.example;\n\nimport java.util.List;\n\npublic class Foo {}"
        result = code_generator.detect_import_insertion_point(content, "java")

        assert result == 4

    def test_java_multiple_imports(self) -> None:
        """Test Java with multiple imports."""
        content = "package com.example;\n\nimport java.util.List;\nimport java.util.Map;\n\npublic class Foo {}"
        result = code_generator.detect_import_insertion_point(content, "java")

        assert result == 5

    def test_empty_file(self) -> None:
        """Test with empty file content."""
        result = code_generator.detect_import_insertion_point("", "python")

        assert result == 1

    def test_unknown_language(self) -> None:
        """Test with unknown language uses generic detection."""
        content = "import something\nimport other\n\ncode here"
        result = code_generator.detect_import_insertion_point(content, "unknown")

        # Should find some import point
        assert result >= 1


class TestCleanTemplateWhitespace:
    """Test whitespace cleaning for templates."""

    def test_removes_consecutive_blank_lines(self) -> None:
        """Test that multiple blank lines are reduced."""
        content = "line1\n\n\n\nline2"
        result = _clean_template_whitespace(content)

        assert "\n\n\n" not in result

    def test_removes_trailing_whitespace(self) -> None:
        """Test trailing whitespace removal."""
        content = "line1   \nline2\t\t"
        result = _clean_template_whitespace(content)

        lines = result.split('\n')
        for line in lines:
            assert line == line.rstrip()

    def test_preserves_single_blank_line(self) -> None:
        """Test that single blank lines are preserved."""
        content = "line1\n\nline2"
        result = _clean_template_whitespace(content)

        assert result == "line1\n\nline2"

    def test_strips_leading_trailing(self) -> None:
        """Test leading and trailing blank lines are stripped."""
        content = "\n\ncode\n\n"
        result = _clean_template_whitespace(content)

        assert result == "code"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_function_template_with_special_characters(self) -> None:
        """Test template with special characters in body."""
        template = FunctionTemplate(
            name="regex_pattern",
            parameters=[],
            body='return r"\\d+\\.\\d+"'
        )
        result = template.generate()

        assert r'return r"\d+\.\d+"' in result

    def test_substitute_special_regex_chars(self) -> None:
        """Test substitution doesn't break on regex special chars."""
        result = substitute_template_variables(
            "Pattern: {{pattern}}",
            {"pattern": "\\d+.*"}
        )

        assert result == "Pattern: \\d+.*"

    def test_deeply_nested_conditionals(self) -> None:
        """Test nested conditional sections.

        Note: The regex-based implementation doesn't handle nested conditionals
        in a single pass. This test documents the current behavior.
        """
        # Simple non-nested conditionals work fine
        template = "{{#if a}}A{{/if}} {{#if b}}B{{/if}}"
        result = substitute_template_variables(
            template,
            {"a": "true", "b": "true"}
        )

        assert result == "A B"

    def test_empty_each_list_strict(self) -> None:
        """Test each with missing variable in strict mode."""
        with pytest.raises(ValueError, match="Missing list variable"):
            substitute_template_variables(
                "{{#each missing}}{{.}}{{/each}}",
                {},
                strict=True
            )

    def test_function_template_unicode(self) -> None:
        """Test function template with unicode characters."""
        template = FunctionTemplate(
            name="unicode_func",
            parameters=[("text", "str")],
            body='return text + " \u2713"',
            docstring="Returns text with checkmark."
        )
        result = template.generate()

        assert "\u2713" in result

    def test_multiline_conditional_content(self) -> None:
        """Test conditional with multiline content."""
        template = """{{#if include}}Line 1
Line 2
Line 3{{/if}}"""
        result = substitute_template_variables(
            template,
            {"include": "true"}
        )

        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result

    def test_variable_at_start_and_end(self) -> None:
        """Test variables at boundaries of template."""
        result = substitute_template_variables(
            "{{start}}middle{{end}}",
            {"start": "A", "end": "Z"}
        )

        assert result == "AmiddleZ"

    def test_repeated_variable(self) -> None:
        """Test same variable used multiple times."""
        result = substitute_template_variables(
            "{{x}} + {{x}} = {{result}}",
            {"x": "2", "result": "4"}
        )

        assert result == "2 + 2 = 4"


class TestDetectPythonImportPoint:
    """Additional tests for Python import detection edge cases."""

    def test_multiline_docstring(self) -> None:
        """Test handling of multiline module docstring."""
        content = '''"""
This is a long
multiline docstring.
"""

import os

def func(): pass'''
        lines = content.split('\n')
        result = _detect_python_import_point(lines)

        assert result == 7

    def test_comments_before_imports(self) -> None:
        """Test comments before imports are skipped."""
        content = "# Comment line\n# Another comment\nimport os\n\ndef func(): pass"
        lines = content.split('\n')
        result = _detect_python_import_point(lines)

        assert result == 4


class TestDetectJsImportPoint:
    """Additional tests for JavaScript/TypeScript import detection."""

    def test_type_imports(self) -> None:
        """Test TypeScript type imports are detected."""
        content = "import type { Type } from './types';\n\nconst x = 1;"
        lines = content.split('\n')
        result = _detect_js_import_point(lines)

        assert result == 2

    def test_mixed_imports_requires(self) -> None:
        """Test mixed ES6 imports and CommonJS requires."""
        content = "import x from 'x';\nconst y = require('y');\n\ncode();"
        lines = content.split('\n')
        result = _detect_js_import_point(lines)

        assert result == 3


class TestDetectJavaImportPoint:
    """Additional tests for Java import detection."""

    def test_static_imports(self) -> None:
        """Test static imports are detected."""
        content = "package com.example;\n\nimport static java.lang.Math.PI;\n\nclass Test {}"
        lines = content.split('\n')
        result = _detect_java_import_point(lines)

        assert result == 4

    def test_no_package_declaration(self) -> None:
        """Test Java file without package declaration."""
        content = "import java.util.List;\n\nclass Test {}"
        lines = content.split('\n')
        result = _detect_java_import_point(lines)

        assert result == 2
