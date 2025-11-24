"""Unit tests for syntax validation functions in the code generation engine.

Tests for Phase 2, Task 2.6 - Syntax validation for generated code.
Tests cover Python, JavaScript, TypeScript, and Java validation,
plus error formatting and the dispatcher function.
"""

import sys
import os
from unittest.mock import patch, MagicMock
import subprocess
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import main


class TestValidatePythonSyntax:
    """Tests for validate_python_syntax function."""

    def test_valid_simple_assignment(self) -> None:
        """Test valid simple assignment."""
        is_valid, error = main.validate_python_syntax("x = 1")
        assert is_valid is True
        assert error is None

    def test_valid_function_definition(self) -> None:
        """Test valid function definition."""
        code = """def foo(x, y):
    return x + y
"""
        is_valid, error = main.validate_python_syntax(code)
        assert is_valid is True
        assert error is None

    def test_valid_class_definition(self) -> None:
        """Test valid class definition with methods."""
        code = """class MyClass:
    def __init__(self, value):
        self.value = value

    def get_value(self):
        return self.value
"""
        is_valid, error = main.validate_python_syntax(code)
        assert is_valid is True
        assert error is None

    def test_valid_multiline_code(self) -> None:
        """Test valid multiline code with imports and functions."""
        code = """import os
from typing import List

def process_files(paths: List[str]) -> int:
    count = 0
    for path in paths:
        if os.path.exists(path):
            count += 1
    return count
"""
        is_valid, error = main.validate_python_syntax(code)
        assert is_valid is True
        assert error is None

    def test_invalid_unclosed_parenthesis(self) -> None:
        """Test invalid code with unclosed parenthesis."""
        is_valid, error = main.validate_python_syntax("def foo(")
        assert is_valid is False
        assert error is not None
        assert "line" in error.lower()

    def test_invalid_missing_colon(self) -> None:
        """Test invalid code missing colon after def."""
        is_valid, error = main.validate_python_syntax("def foo()\n    pass")
        assert is_valid is False
        assert error is not None

    def test_invalid_bad_indentation(self) -> None:
        """Test invalid code with bad indentation."""
        code = """def foo():
pass
"""
        is_valid, error = main.validate_python_syntax(code)
        assert is_valid is False
        assert error is not None

    def test_invalid_unterminated_string(self) -> None:
        """Test invalid code with unterminated string."""
        is_valid, error = main.validate_python_syntax('x = "hello')
        assert is_valid is False
        assert error is not None

    def test_error_includes_line_number(self) -> None:
        """Test that error message includes line number."""
        code = """x = 1
y = 2
def broken(
"""
        is_valid, error = main.validate_python_syntax(code)
        assert is_valid is False
        assert error is not None
        assert "line" in error.lower()

    def test_error_includes_pointer(self) -> None:
        """Test that error includes visual pointer for syntax errors."""
        code = "x = (1 + 2"
        is_valid, error = main.validate_python_syntax(code)
        assert is_valid is False
        assert error is not None


class TestValidateJavaScriptSyntax:
    """Tests for validate_javascript_syntax function."""

    @patch('subprocess.run')
    def test_valid_const_declaration(self, mock_run: MagicMock) -> None:
        """Test valid const declaration."""
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        is_valid, error = main.validate_javascript_syntax("const x = 1;")
        assert is_valid is True
        assert error is None
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_valid_function_expression(self, mock_run: MagicMock) -> None:
        """Test valid function expression."""
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        code = "const add = (a, b) => a + b;"
        is_valid, error = main.validate_javascript_syntax(code)
        assert is_valid is True
        assert error is None

    @patch('subprocess.run')
    def test_valid_async_function(self, mock_run: MagicMock) -> None:
        """Test valid async function."""
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        code = """async function fetchData(url) {
    const response = await fetch(url);
    return response.json();
}"""
        is_valid, error = main.validate_javascript_syntax(code)
        assert is_valid is True
        assert error is None

    @patch('subprocess.run')
    def test_invalid_missing_closing_brace(self, mock_run: MagicMock) -> None:
        """Test invalid code with missing closing brace."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Line 1: Unexpected end of input",
            stdout=""
        )
        is_valid, error = main.validate_javascript_syntax("function foo() {")
        assert is_valid is False
        assert error is not None
        assert "Unexpected" in error

    @patch('subprocess.run')
    def test_invalid_incomplete_expression(self, mock_run: MagicMock) -> None:
        """Test invalid incomplete expression."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Line 1: Unexpected end of input",
            stdout=""
        )
        is_valid, error = main.validate_javascript_syntax("const x = ")
        assert is_valid is False
        assert error is not None

    @patch('subprocess.run')
    def test_node_not_found(self, mock_run: MagicMock) -> None:
        """Test when Node.js is not installed."""
        mock_run.side_effect = FileNotFoundError()
        is_valid, error = main.validate_javascript_syntax("const x = 1;")
        assert is_valid is False
        assert error is not None
        assert "Node.js not found" in error

    @patch('subprocess.run')
    def test_timeout_expired(self, mock_run: MagicMock) -> None:
        """Test when validation times out."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="node", timeout=10)
        is_valid, error = main.validate_javascript_syntax("const x = 1;")
        assert is_valid is False
        assert error is not None
        assert "timed out" in error.lower()

    @patch('subprocess.run')
    def test_empty_error_message(self, mock_run: MagicMock) -> None:
        """Test handling of empty error message."""
        mock_run.return_value = MagicMock(returncode=1, stderr="", stdout="")
        is_valid, error = main.validate_javascript_syntax("const x = ")
        assert is_valid is False
        assert error == "Unknown syntax error"


class TestValidateTypeScriptSyntax:
    """Tests for validate_typescript_syntax function."""

    @patch('subprocess.run')
    def test_valid_typed_variable(self, mock_run: MagicMock) -> None:
        """Test valid typed variable declaration."""
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        is_valid, error = main.validate_typescript_syntax("const x: number = 1;")
        assert is_valid is True
        assert error is None

    @patch('subprocess.run')
    def test_valid_interface(self, mock_run: MagicMock) -> None:
        """Test valid interface definition."""
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        code = """interface User {
    name: string;
    age: number;
}"""
        is_valid, error = main.validate_typescript_syntax(code)
        assert is_valid is True
        assert error is None

    @patch('subprocess.run')
    def test_valid_generic_function(self, mock_run: MagicMock) -> None:
        """Test valid generic function."""
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        code = "function identity<T>(arg: T): T { return arg; }"
        is_valid, error = main.validate_typescript_syntax(code)
        assert is_valid is True
        assert error is None

    @patch('subprocess.run')
    def test_invalid_type_annotation(self, mock_run: MagicMock) -> None:
        """Test invalid type annotation syntax."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="",
            stdout="validate.ts(1,10): error TS1005: ';' expected."
        )
        is_valid, error = main.validate_typescript_syntax("const x: = 1;")
        assert is_valid is False
        assert error is not None

    @patch('subprocess.run')
    def test_tsc_not_found(self, mock_run: MagicMock) -> None:
        """Test when TypeScript compiler is not installed."""
        mock_run.side_effect = FileNotFoundError()
        is_valid, error = main.validate_typescript_syntax("const x: number = 1;")
        assert is_valid is False
        assert error is not None
        assert "tsc" in error.lower() or "typescript" in error.lower()

    @patch('subprocess.run')
    def test_multiple_errors(self, mock_run: MagicMock) -> None:
        """Test handling of multiple TypeScript errors."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="",
            stdout="file.ts(1,5): error TS1005: ')' expected.\nfile.ts(1,10): error TS1005: ';' expected.\nfile.ts(2,1): error TS1002: Unterminated string literal."
        )
        is_valid, error = main.validate_typescript_syntax("const x")
        assert is_valid is False
        assert error is not None
        # Should contain first few errors
        assert "Line" in error or "error" in error.lower()


class TestValidateJavaSyntax:
    """Tests for validate_java_syntax function."""

    @patch('subprocess.run')
    def test_valid_simple_class(self, mock_run: MagicMock) -> None:
        """Test valid simple Java class."""
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        code = """public class Hello {
    public static void main(String[] args) {
        System.out.println("Hello");
    }
}"""
        is_valid, error = main.validate_java_syntax(code)
        assert is_valid is True
        assert error is None

    @patch('subprocess.run')
    def test_valid_class_with_fields(self, mock_run: MagicMock) -> None:
        """Test valid class with fields and methods."""
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
        code = """public class Person {
    private String name;
    private int age;

    public Person(String name, int age) {
        this.name = name;
        this.age = age;
    }

    public String getName() {
        return name;
    }
}"""
        is_valid, error = main.validate_java_syntax(code)
        assert is_valid is True
        assert error is None

    @patch('subprocess.run')
    def test_invalid_missing_semicolon(self, mock_run: MagicMock) -> None:
        """Test invalid code missing semicolon."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="Test.java:3: error: ';' expected\n        int x = 1\n                 ^",
            stdout=""
        )
        code = """public class Test {
    public void test() {
        int x = 1
    }
}"""
        is_valid, error = main.validate_java_syntax(code)
        assert is_valid is False
        assert error is not None

    @patch('subprocess.run')
    def test_javac_not_found(self, mock_run: MagicMock) -> None:
        """Test when javac is not installed."""
        mock_run.side_effect = FileNotFoundError()
        is_valid, error = main.validate_java_syntax("public class Test {}")
        assert is_valid is False
        assert error is not None
        assert "javac not found" in error

    @patch('subprocess.run')
    def test_timeout(self, mock_run: MagicMock) -> None:
        """Test when Java validation times out."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="javac", timeout=30)
        is_valid, error = main.validate_java_syntax("public class Test {}")
        assert is_valid is False
        assert error is not None
        assert "timed out" in error.lower()


class TestFormatValidationError:
    """Tests for format_validation_error function."""

    def test_basic_error_formatting(self) -> None:
        """Test basic error formatting with header."""
        result = main.format_validation_error("Syntax error", "x = 1", "python")
        assert "Validation Error" in result
        assert "python" in result
        assert "Syntax error" in result

    def test_code_snippet_with_line_number(self) -> None:
        """Test that code snippet is shown for line-specific errors."""
        code = "x = 1\ny = 2\nz = ("
        error = "SyntaxError at line 3, column 5: unexpected EOF"
        result = main.format_validation_error(error, code, "python")
        assert "z = (" in result
        assert ">>>" in result  # Error line marker

    def test_suggestions_for_python_indent_error(self) -> None:
        """Test suggestions for Python indentation error."""
        error = "unexpected indent at line 2"
        result = main.format_validation_error(error, "def foo():\n  pass", "python")
        assert "Suggested fixes" in result
        assert "indent" in result.lower()

    def test_suggestions_for_javascript_error(self) -> None:
        """Test suggestions for JavaScript errors."""
        error = "Unexpected token at line 1"
        result = main.format_validation_error(error, "const x = ", "javascript")
        assert "Suggested fixes" in result

    def test_suggestions_for_java_semicolon(self) -> None:
        """Test suggestions for Java missing semicolon."""
        error = "';' expected at line 1"
        result = main.format_validation_error(error, "int x = 1", "java")
        assert "Suggested fixes" in result
        assert "semicolon" in result.lower()

    def test_pointer_to_error_column(self) -> None:
        """Test that pointer is shown for column-specific errors."""
        code = "x = (1 + 2"
        error = "Line 1, column 10: unexpected EOF"
        result = main.format_validation_error(error, code, "python")
        # Should contain the caret pointer
        assert "^" in result

    def test_context_lines_shown(self) -> None:
        """Test that context lines before/after error are shown."""
        code = "line1\nline2\nerror_line\nline4\nline5"
        error = "Error at line 3"
        result = main.format_validation_error(error, code, "python")
        assert "line2" in result
        assert "error_line" in result
        assert "line4" in result


class TestValidateGeneratedCode:
    """Tests for validate_generated_code dispatcher function."""

    def test_python_valid(self) -> None:
        """Test valid Python code through dispatcher."""
        is_valid, error = main.validate_generated_code("x = 1", "python")
        assert is_valid is True
        assert error is None

    def test_python_invalid(self) -> None:
        """Test invalid Python code through dispatcher."""
        is_valid, error = main.validate_generated_code("def foo(", "python")
        assert is_valid is False
        assert error is not None
        assert "Validation Error" in error
        assert "python" in error

    @patch('main.validate_javascript_syntax')
    def test_javascript_delegation(self, mock_js: MagicMock) -> None:
        """Test that JavaScript validation is delegated correctly."""
        mock_js.return_value = (True, None)
        is_valid, error = main.validate_generated_code("const x = 1;", "javascript")
        assert is_valid is True
        mock_js.assert_called_once()

    @patch('main.validate_javascript_syntax')
    def test_typescript_uses_javascript_validator(self, mock_js: MagicMock) -> None:
        """Test that TypeScript uses JavaScript validator."""
        mock_js.return_value = (True, None)
        main.validate_generated_code("const x: number = 1;", "typescript")
        mock_js.assert_called_once()

    @patch('main.validate_javascript_syntax')
    def test_tsx_uses_javascript_validator(self, mock_js: MagicMock) -> None:
        """Test that TSX uses JavaScript validator."""
        mock_js.return_value = (True, None)
        main.validate_generated_code("const x = <div />;", "tsx")
        mock_js.assert_called_once()

    @patch('main.validate_java_syntax')
    def test_java_delegation(self, mock_java: MagicMock) -> None:
        """Test that Java validation is delegated correctly."""
        mock_java.return_value = (True, None)
        is_valid, error = main.validate_generated_code("class Test {}", "java")
        assert is_valid is True
        mock_java.assert_called_once()

    def test_c_brace_validation(self) -> None:
        """Test C code with brace validation."""
        # Valid - matched braces
        is_valid, error = main.validate_generated_code("int main() { return 0; }", "c")
        assert is_valid is True
        assert error is None

        # Invalid - mismatched braces
        is_valid, error = main.validate_generated_code("int main() { return 0; ", "c")
        assert is_valid is False
        assert error is not None
        assert "brace" in error.lower()

    def test_cpp_brace_validation(self) -> None:
        """Test C++ code with brace validation."""
        is_valid, error = main.validate_generated_code("class Foo { };", "cpp")
        assert is_valid is True

        is_valid, error = main.validate_generated_code("class Foo { ", "cpp")
        assert is_valid is False

    def test_rust_brace_validation(self) -> None:
        """Test Rust code with brace validation."""
        is_valid, error = main.validate_generated_code("fn main() { }", "rust")
        assert is_valid is True

        is_valid, error = main.validate_generated_code("fn main() {", "rust")
        assert is_valid is False

    def test_go_brace_validation(self) -> None:
        """Test Go code with brace validation."""
        is_valid, error = main.validate_generated_code("func main() { }", "go")
        assert is_valid is True

        is_valid, error = main.validate_generated_code("func main() {", "go")
        assert is_valid is False

    def test_unsupported_language(self) -> None:
        """Test unsupported language returns valid."""
        is_valid, error = main.validate_generated_code("code here", "unknown_lang")
        assert is_valid is True
        assert error is None

    def test_error_formatting_included(self) -> None:
        """Test that error includes formatted message with suggestions."""
        is_valid, error = main.validate_generated_code("def foo(\n", "python")
        assert is_valid is False
        assert "Validation Error" in error
        assert "python" in error


class TestErrorSuggestions:
    """Tests for _get_error_suggestions helper function."""

    def test_python_indent_suggestions(self) -> None:
        """Test suggestions for Python indentation errors."""
        suggestions = main._get_error_suggestions("unexpected indent", "python")
        assert len(suggestions) > 0
        assert any("indent" in s.lower() for s in suggestions)

    def test_python_colon_suggestions(self) -> None:
        """Test suggestions for missing colon."""
        suggestions = main._get_error_suggestions("expected ':'", "python")
        assert len(suggestions) > 0
        assert any("colon" in s.lower() for s in suggestions)

    def test_python_string_suggestions(self) -> None:
        """Test suggestions for unterminated string."""
        suggestions = main._get_error_suggestions("unterminated string literal", "python")
        assert len(suggestions) > 0
        assert any("string" in s.lower() or "quote" in s.lower() for s in suggestions)

    def test_javascript_token_suggestions(self) -> None:
        """Test suggestions for unexpected token."""
        suggestions = main._get_error_suggestions("Unexpected token", "javascript")
        assert len(suggestions) > 0

    def test_java_semicolon_suggestions(self) -> None:
        """Test suggestions for Java semicolon errors."""
        suggestions = main._get_error_suggestions("';' expected", "java")
        assert len(suggestions) > 0
        assert any("semicolon" in s.lower() for s in suggestions)

    def test_brace_suggestions_for_c_languages(self) -> None:
        """Test brace suggestions for C-style languages."""
        for lang in ["c", "cpp", "csharp", "java", "rust", "go"]:
            suggestions = main._get_error_suggestions("mismatched brace", lang)
            assert len(suggestions) > 0
            assert any("brace" in s.lower() for s in suggestions)


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_code_python(self) -> None:
        """Test empty code validation."""
        is_valid, error = main.validate_python_syntax("")
        assert is_valid is True
        assert error is None

    def test_whitespace_only_python(self) -> None:
        """Test whitespace-only code."""
        is_valid, error = main.validate_python_syntax("   \n\t\n   ")
        assert is_valid is True
        assert error is None

    def test_very_long_code(self) -> None:
        """Test validation of very long code."""
        code = "x = 1\n" * 1000
        is_valid, error = main.validate_python_syntax(code)
        assert is_valid is True
        assert error is None

    def test_unicode_in_code(self) -> None:
        """Test code with unicode characters."""
        code = 'x = "Hello, 世界! 🌍"'
        is_valid, error = main.validate_python_syntax(code)
        assert is_valid is True
        assert error is None

    def test_nested_braces(self) -> None:
        """Test deeply nested braces."""
        code = "fn main() { { { { } } } }"
        is_valid, error = main.validate_generated_code(code, "rust")
        assert is_valid is True

    def test_complex_python_code(self) -> None:
        """Test complex Python code with various features."""
        code = """
from typing import List, Optional
import asyncio

class DataProcessor:
    def __init__(self, data: List[int]) -> None:
        self.data = data
        self._cache: Optional[int] = None

    async def process(self) -> int:
        result = sum(self.data)
        self._cache = result
        return result

    @property
    def cached_result(self) -> Optional[int]:
        return self._cache

async def main():
    processor = DataProcessor([1, 2, 3, 4, 5])
    result = await processor.process()
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
"""
        is_valid, error = main.validate_python_syntax(code)
        assert is_valid is True
        assert error is None

    def test_format_error_with_no_line_info(self) -> None:
        """Test error formatting when no line info is available."""
        result = main.format_validation_error("Generic error", "code", "python")
        assert "Generic error" in result
        # Should still have header
        assert "Validation Error" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
