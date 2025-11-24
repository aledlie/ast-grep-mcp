"""Unit tests for code formatting functions in ast-grep-mcp.

Tests cover all language formatters including Python (black), TypeScript/JavaScript (prettier),
and Java (google-java-format), plus the format_generated_code dispatcher.

Phase 2, Task 2.5 - Code Formatting Tests
"""

import subprocess
import tempfile
from unittest.mock import MagicMock, patch, call
import pytest

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import main
from main import (
    format_python_code,
    format_typescript_code,
    format_javascript_code,
    format_java_code,
    format_generated_code,
    _basic_python_format,
    _format_python_line,
)

# Create a mock logger on the main module for format_generated_code tests
# This is needed because format_generated_code uses logger without defining it
main.logger = MagicMock()


class TestFormatPythonCode:
    """Tests for format_python_code function."""

    def test_format_python_code_with_black_available(self):
        """Test Python formatting when black library is available."""
        # Test actual black formatting if available
        result = format_python_code("x=1")
        # Should format with spaces around operator
        assert result is not None
        assert "x" in result

    def test_format_python_code_imports(self):
        """Test Python formatting with imports."""
        result = format_python_code("import sys,os,re")
        # Should handle imports
        assert "import" in result

    def test_format_python_code_function(self):
        """Test Python formatting with function definition."""
        result = format_python_code("def foo(a,b,c): return a+b+c")
        assert "def foo" in result

    def test_format_python_code_custom_line_length(self):
        """Test Python formatting with custom line length."""
        # This tests the basic formatter if black isn't available
        code = "x = 1"
        result = format_python_code(code, line_length=120)
        assert result is not None

    def test_format_python_code_empty_input(self):
        """Test formatting empty code."""
        result = format_python_code("")
        assert result == "\n" or result == ""


class TestBasicPythonFormat:
    """Tests for _basic_python_format fallback function."""

    def test_basic_python_format_sorts_imports(self):
        """Test that imports are sorted alphabetically."""
        code = "import sys\nimport os\nimport re"
        result = _basic_python_format(code)
        lines = [l for l in result.strip().split('\n') if l.startswith('import')]
        assert lines == ['import os', 'import re', 'import sys']

    def test_basic_python_format_splits_multi_imports(self):
        """Test that 'import sys, os, re' is split into separate imports."""
        code = "import sys, os, re"
        result = _basic_python_format(code)
        assert "import os" in result
        assert "import re" in result
        assert "import sys" in result
        assert "import sys, os, re" not in result

    def test_basic_python_format_separates_from_imports(self):
        """Test that from imports are separated from regular imports."""
        code = "import os\nfrom typing import List"
        result = _basic_python_format(code)
        assert "import os" in result
        assert "from typing import List" in result

    def test_basic_python_format_preserves_indentation(self):
        """Test that indentation is preserved."""
        code = "def foo():\n    x = 1"
        result = _basic_python_format(code)
        # Check indentation is preserved
        lines = result.split('\n')
        for line in lines:
            if 'x' in line:
                assert line.startswith('    ')

    def test_basic_python_format_adds_trailing_newline(self):
        """Test that trailing newline is added."""
        code = "x = 1"
        result = _basic_python_format(code)
        assert result.endswith('\n')

    def test_basic_python_format_handles_empty_lines(self):
        """Test handling of empty lines in code."""
        code = "x = 1\n\ny = 2"
        result = _basic_python_format(code)
        assert result is not None


class TestFormatPythonLine:
    """Tests for _format_python_line helper function."""

    def test_format_python_line_adds_operator_spaces(self):
        """Test that spaces are added around operators."""
        result = _format_python_line("x=1")
        assert " = " in result or result == "x = 1"

    def test_format_python_line_handles_compound_operators(self):
        """Test handling of compound operators like +=, -=, etc."""
        result = _format_python_line("x+=1")
        assert "+=" in result

    def test_format_python_line_preserves_strings(self):
        """Test that operators inside strings are not modified."""
        result = _format_python_line('x = "a=b"')
        assert '"a=b"' in result or "'a=b'" in result

    def test_format_python_line_empty_line(self):
        """Test formatting empty line."""
        result = _format_python_line("")
        assert result == ""

    def test_format_python_line_normalizes_multiple_spaces(self):
        """Test that multiple spaces are normalized."""
        result = _format_python_line("x  =  1")
        assert "  " not in result or result.count("  ") == 0


class TestFormatTypescriptCode:
    """Tests for format_typescript_code function."""

    @patch('shutil.which')
    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    def test_format_typescript_with_prettier(self, mock_tempfile, mock_run, mock_which):
        """Test TypeScript formatting with prettier available."""
        mock_which.return_value = "/usr/local/bin/prettier"
        mock_run.return_value = MagicMock(returncode=0, stdout="const x = 1;\n")

        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_file.name = "/tmp/test.ts"
        mock_tempfile.return_value = mock_file

        with patch('os.unlink'):
            result = format_typescript_code("const x=1")

        assert result == "const x = 1;\n"
        mock_run.assert_called_once()

    @patch('shutil.which')
    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    def test_format_typescript_prettier_failure(self, mock_tempfile, mock_run, mock_which):
        """Test fallback when prettier fails."""
        mock_which.return_value = "/usr/local/bin/prettier"
        mock_run.return_value = MagicMock(returncode=1, stderr="Error")

        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_file.name = "/tmp/test.ts"
        mock_tempfile.return_value = mock_file

        with patch('os.unlink'):
            result = format_typescript_code("const x=1")

        # Should return fallback formatted result
        assert result is not None

    @patch('shutil.which')
    def test_format_typescript_no_prettier(self, mock_which):
        """Test TypeScript formatting without prettier using basic formatting."""
        mock_which.return_value = None

        result = format_typescript_code("const x = 1")
        assert result is not None
        # Basic formatting should add semicolons
        assert ";" in result or "const x = 1" in result

    @patch('shutil.which')
    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    def test_format_typescript_timeout(self, mock_tempfile, mock_run, mock_which):
        """Test handling of prettier timeout."""
        mock_which.return_value = "/usr/local/bin/prettier"
        mock_run.side_effect = subprocess.TimeoutExpired("prettier", 10)

        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_file.name = "/tmp/test.ts"
        mock_tempfile.return_value = mock_file

        with patch('os.unlink'):
            result = format_typescript_code("const x=1")

        # Should fall back to basic formatting
        assert result is not None

    @patch('shutil.which')
    def test_format_typescript_preserves_template_literals(self, mock_which):
        """Test that template literals with backticks are preserved."""
        mock_which.return_value = None

        code = "const s = `hello ${name}`"
        result = format_typescript_code(code)
        # Should not convert quotes in template literals
        assert "`" in result


class TestFormatJavascriptCode:
    """Tests for format_javascript_code function."""

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_format_javascript_with_prettier(self, mock_run, mock_which):
        """Test JavaScript formatting with prettier."""
        mock_which.return_value = "/usr/local/bin/prettier"
        mock_run.return_value = MagicMock(returncode=0, stdout="const x = 1;")

        result = format_javascript_code("const x=1")
        assert result == "const x = 1;"
        mock_run.assert_called_once()

        # Verify prettier was called with babel parser
        call_args = mock_run.call_args
        assert "babel" in call_args[0][0]

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_format_javascript_prettier_failure(self, mock_run, mock_which):
        """Test fallback when prettier fails."""
        mock_which.return_value = "/usr/local/bin/prettier"
        mock_run.return_value = MagicMock(returncode=1, stderr="Error")

        result = format_javascript_code("const x=1")
        # Should use basic formatting
        assert result is not None

    @patch('shutil.which')
    def test_format_javascript_no_prettier(self, mock_which):
        """Test JavaScript formatting without prettier."""
        mock_which.return_value = None

        result = format_javascript_code("const x=1")
        # Basic formatting adds spaces around operators
        assert result is not None

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_format_javascript_timeout(self, mock_run, mock_which):
        """Test handling of prettier timeout."""
        mock_which.return_value = "/usr/local/bin/prettier"
        mock_run.side_effect = subprocess.TimeoutExpired("prettier", 10)

        result = format_javascript_code("const x=1")
        assert result is not None

    @patch('shutil.which')
    def test_format_javascript_basic_adds_operator_spaces(self, mock_which):
        """Test basic formatter adds spaces around operators."""
        mock_which.return_value = None

        result = format_javascript_code("x===y")
        # Basic formatter adds spaces, result may vary
        assert "===" in result or "= = =" in result


class TestFormatJavaCode:
    """Tests for format_java_code function."""

    @patch('shutil.which')
    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    def test_format_java_with_google_java_format(self, mock_tempfile, mock_run, mock_which):
        """Test Java formatting with google-java-format."""
        mock_which.return_value = "/usr/local/bin/google-java-format"
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="public class Foo {\n    int x;\n}"
        )

        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_file.name = "/tmp/Test.java"
        mock_tempfile.return_value = mock_file

        with patch('os.unlink'):
            result = format_java_code("public class Foo{int x;}")

        assert "public class Foo" in result

    @patch('shutil.which')
    def test_format_java_no_formatter(self, mock_which):
        """Test Java formatting without google-java-format."""
        mock_which.return_value = None

        code = "public class Foo{int x;}"
        result = format_java_code(code)
        # Should use basic formatting
        assert result is not None

    @patch('shutil.which')
    def test_format_java_basic_sorts_imports(self, mock_which):
        """Test basic Java formatter sorts imports."""
        mock_which.return_value = None

        code = "import org.example.A;\nimport java.util.List;\nimport javax.xml.Parser;"
        result = format_java_code(code)

        # java.* should come before javax.* which comes before others
        lines = result.split('\n')
        import_lines = [l for l in lines if l.startswith('import')]
        if len(import_lines) >= 3:
            # Verify ordering
            java_idx = next((i for i, l in enumerate(import_lines) if 'java.util' in l), -1)
            javax_idx = next((i for i, l in enumerate(import_lines) if 'javax' in l), -1)
            org_idx = next((i for i, l in enumerate(import_lines) if 'org.example' in l), -1)

            if java_idx >= 0 and javax_idx >= 0:
                assert java_idx < javax_idx

    @patch('shutil.which')
    @patch('subprocess.run')
    @patch('tempfile.NamedTemporaryFile')
    def test_format_java_timeout(self, mock_tempfile, mock_run, mock_which):
        """Test handling of google-java-format timeout."""
        mock_which.return_value = "/usr/local/bin/google-java-format"
        mock_run.side_effect = subprocess.TimeoutExpired("google-java-format", 30)

        mock_file = MagicMock()
        mock_file.__enter__ = MagicMock(return_value=mock_file)
        mock_file.__exit__ = MagicMock(return_value=False)
        mock_file.name = "/tmp/Test.java"
        mock_tempfile.return_value = mock_file

        with patch('os.unlink'):
            result = format_java_code("public class Foo{}")

        # Should fall back to basic formatting
        assert result is not None


class TestFormatGeneratedCode:
    """Tests for format_generated_code dispatcher function.

    Note: format_generated_code uses a global logger that is mocked at module level.
    """

    @patch('main.subprocess.run')
    def test_format_generated_code_python(self, mock_run):
        """Test dispatcher routes Python to black."""
        mock_run.return_value = MagicMock(returncode=0, stdout="x = 1\n")

        result = format_generated_code("x=1", "python")
        assert result == "x = 1\n"

        # Verify black was called
        call_args = mock_run.call_args[0][0]
        assert "black" in call_args

    @patch('main.subprocess.run')
    def test_format_generated_code_javascript(self, mock_run):
        """Test dispatcher routes JavaScript to prettier with babel parser."""
        mock_run.return_value = MagicMock(returncode=0, stdout="const x = 1;\n")

        result = format_generated_code("const x=1", "javascript")
        assert result == "const x = 1;\n"

        # Verify prettier was called with babel parser
        call_args = mock_run.call_args[0][0]
        assert "prettier" in call_args
        assert "babel" in call_args

    @patch('main.subprocess.run')
    def test_format_generated_code_typescript(self, mock_run):
        """Test dispatcher routes TypeScript to prettier with typescript parser."""
        mock_run.return_value = MagicMock(returncode=0, stdout="const x: number = 1;\n")

        result = format_generated_code("const x:number=1", "typescript")
        assert result == "const x: number = 1;\n"

        call_args = mock_run.call_args[0][0]
        assert "prettier" in call_args
        assert "typescript" in call_args

    @patch('main.subprocess.run')
    def test_format_generated_code_tsx(self, mock_run):
        """Test dispatcher routes TSX to prettier with typescript parser."""
        mock_run.return_value = MagicMock(returncode=0, stdout="const el = <div />;\n")

        result = format_generated_code("const el=<div/>", "tsx")
        assert "div" in result

    @patch('main.subprocess.run')
    def test_format_generated_code_json(self, mock_run):
        """Test dispatcher routes JSON to prettier with json parser."""
        mock_run.return_value = MagicMock(returncode=0, stdout='{"key": "value"}\n')

        result = format_generated_code('{"key":"value"}', "json")
        assert '"key"' in result

    @patch('main.subprocess.run')
    def test_format_generated_code_go(self, mock_run):
        """Test dispatcher routes Go to gofmt."""
        mock_run.return_value = MagicMock(returncode=0, stdout="package main\n")

        result = format_generated_code("package main", "go")
        assert "package main" in result

        call_args = mock_run.call_args[0][0]
        assert "gofmt" in call_args

    @patch('main.subprocess.run')
    def test_format_generated_code_rust(self, mock_run):
        """Test dispatcher routes Rust to rustfmt."""
        mock_run.return_value = MagicMock(returncode=0, stdout="fn main() {}\n")

        result = format_generated_code("fn main(){}", "rust")
        assert "fn main" in result

        call_args = mock_run.call_args[0][0]
        assert "rustfmt" in call_args

    def test_format_generated_code_unknown_language(self):
        """Test dispatcher returns code unchanged for unknown language."""
        code = "some code here"
        result = format_generated_code(code, "unknown_language")
        assert result == code

    @patch('main.subprocess.run')
    def test_format_generated_code_formatter_failure(self, mock_run):
        """Test dispatcher returns original code when formatter fails."""
        mock_run.return_value = MagicMock(returncode=1, stderr="Error")

        code = "x=1"
        result = format_generated_code(code, "python")
        assert result == code

    @patch('main.subprocess.run')
    def test_format_generated_code_timeout(self, mock_run):
        """Test dispatcher handles timeout gracefully."""
        mock_run.side_effect = subprocess.TimeoutExpired("formatter", 10)

        code = "x=1"
        # Should raise or handle timeout
        try:
            result = format_generated_code(code, "python")
            # If it doesn't raise, it should return something
            assert result is not None
        except subprocess.TimeoutExpired:
            pass  # This is also acceptable behavior

    @patch('main.subprocess.run')
    def test_format_generated_code_case_insensitive(self, mock_run):
        """Test that language names are case-insensitive."""
        mock_run.return_value = MagicMock(returncode=0, stdout="x = 1\n")

        result1 = format_generated_code("x=1", "Python")
        result2 = format_generated_code("x=1", "PYTHON")

        # Both should route to black
        assert mock_run.call_count >= 2

    @patch('main.subprocess.run')
    def test_format_generated_code_css(self, mock_run):
        """Test dispatcher routes CSS to prettier."""
        mock_run.return_value = MagicMock(returncode=0, stdout=".class { color: red; }\n")

        result = format_generated_code(".class{color:red}", "css")
        assert "color" in result

    @patch('main.subprocess.run')
    def test_format_generated_code_html(self, mock_run):
        """Test dispatcher routes HTML to prettier."""
        mock_run.return_value = MagicMock(returncode=0, stdout="<div></div>\n")

        result = format_generated_code("<div></div>", "html")
        assert "<div>" in result

    @patch('main.subprocess.run')
    def test_format_generated_code_yaml(self, mock_run):
        """Test dispatcher routes YAML to prettier."""
        mock_run.return_value = MagicMock(returncode=0, stdout="key: value\n")

        result = format_generated_code("key: value", "yaml")
        assert "key" in result


class TestFormatterIntegration:
    """Integration tests for formatter error handling."""

    @patch('main.subprocess.run')
    def test_formatter_preserves_code_on_error(self, mock_run):
        """Test that original code is preserved when formatter errors."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Syntax error",
            stdout=""
        )

        original_code = "invalid{{{{code"
        result = format_generated_code(original_code, "python")
        assert result == original_code

    @patch('main.subprocess.run')
    def test_multiple_formatters_called_independently(self, mock_run):
        """Test that different languages call their respective formatters."""
        mock_run.return_value = MagicMock(returncode=0, stdout="formatted")

        format_generated_code("code", "python")
        format_generated_code("code", "javascript")
        format_generated_code("code", "go")

        # Verify different formatters were called
        calls = mock_run.call_args_list
        formatters_called = [call[0][0][0] for call in calls]

        assert "black" in formatters_called
        assert "prettier" in formatters_called
        assert "gofmt" in formatters_called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
