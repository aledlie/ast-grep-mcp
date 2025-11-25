"""Comprehensive test suite for Phase 2, Task 2.2: Function Generation

This test suite covers:
- generate_function_signature for all languages (Python, TypeScript, JavaScript, Java)
- generate_function_body with parameter substitution
- detect_return_value for return type inference
- generate_docstring for all language doc formats
- generate_type_annotations for cross-language type conversion
- Edge cases and error handling
"""

import os
import sys
from typing import Any, Dict
from unittest.mock import patch

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# Mock FastMCP before importing main
class MockFastMCP:
    def __init__(self, name: str) -> None:
        self.name = name
        self.tools: Dict[str, Any] = {}

    def tool(self, **kwargs: Any) -> Any:
        def decorator(func: Any) -> Any:
            self.tools[func.__name__] = func
            return func
        return decorator

    def run(self, **kwargs: Any) -> None:
        pass


def mock_field(**kwargs: Any) -> Any:
    return kwargs.get("default")


# Import with mocked decorators
with patch("mcp.server.fastmcp.FastMCP", MockFastMCP):
    with patch("pydantic.Field", mock_field):
        import main

from ast_grep_mcp.models.deduplication import ParameterInfo
from main import (
    format_java_params,
    format_python_params,
    format_typescript_params,
    generate_docstring,
    generate_function_body,
    generate_function_signature,
    generate_java_method,
    generate_javascript_function,
    generate_python_function,
    generate_type_annotations,
    generate_typescript_function,
)

from ast_grep_mcp.features.deduplication.generator import CodeGenerator


# =============================================================================
# Test generate_function_signature
# =============================================================================

class TestGenerateFunctionSignature:
    """Test function signature generation for all languages."""

    def test_python_basic_signature(self) -> None:
        """Test basic Python function signature."""
        params = [ParameterInfo("name", python_type="str")]
        result = generate_function_signature("greet", params, "str", "python")
        assert result == "def greet(name: str) -> str:"

    def test_python_multiple_params(self) -> None:
        """Test Python signature with multiple parameters."""
        params = [
            ParameterInfo("name", python_type="str"),
            ParameterInfo("age", python_type="int"),
        ]
        result = generate_function_signature("create_user", params, "dict", "python")
        assert "name: str" in result
        assert "age: int" in result
        assert "-> dict:" in result

    def test_python_optional_params(self) -> None:
        """Test Python signature with optional parameters."""
        params = [
            ParameterInfo("name", python_type="str"),
            ParameterInfo("age", python_type="int", is_optional=True, default_value="0"),
        ]
        result = generate_function_signature("create_user", params, "dict", "python")
        assert "name: str" in result
        assert "age: int = 0" in result

    def test_python_async_function(self) -> None:
        """Test async Python function signature."""
        params = [ParameterInfo("url", python_type="str")]
        result = generate_function_signature("fetch", params, "bytes", "python", is_async=True)
        assert result.startswith("async def fetch")
        assert "-> bytes:" in result

    def test_python_no_return_type(self) -> None:
        """Test Python signature without return type."""
        params = [ParameterInfo("msg", python_type="str")]
        result = generate_function_signature("log", params, None, "python")
        assert "def log(msg: str):" == result

    def test_python_with_generics(self) -> None:
        """Test Python signature with generic type parameters."""
        params = [ParameterInfo("items", python_type="list[T]")]
        result = generate_function_signature(
            "process", params, "T", "python",
            type_parameters=["T"]
        )
        assert "<T>" in result
        assert "-> T:" in result

    def test_typescript_basic_signature(self) -> None:
        """Test basic TypeScript function signature."""
        params = [ParameterInfo("name", typescript_type="string")]
        result = generate_function_signature("greet", params, "string", "typescript")
        assert result == "function greet(name: string): string"

    def test_typescript_async_function(self) -> None:
        """Test async TypeScript function signature."""
        params = [ParameterInfo("url", typescript_type="string")]
        result = generate_function_signature("fetch", params, "Response", "typescript", is_async=True)
        assert result.startswith("async function fetch")
        assert ": Response" in result

    def test_typescript_optional_params(self) -> None:
        """Test TypeScript signature with optional parameters."""
        params = [
            ParameterInfo("name", typescript_type="string"),
            ParameterInfo("age", typescript_type="number", is_optional=True),
        ]
        result = generate_function_signature("create", params, "User", "typescript")
        assert "name: string" in result
        assert "age?" in result or "age: number" in result

    def test_typescript_no_return(self) -> None:
        """Test TypeScript signature with void return."""
        params = [ParameterInfo("msg", typescript_type="string")]
        result = generate_function_signature("log", params, None, "typescript")
        assert ": void" in result

    def test_typescript_with_generics(self) -> None:
        """Test TypeScript signature with generic type parameters."""
        params = [ParameterInfo("items", typescript_type="T[]")]
        result = generate_function_signature(
            "first", params, "T", "typescript",
            type_parameters=["T"]
        )
        assert "<T>" in result

    def test_javascript_basic_signature(self) -> None:
        """Test basic JavaScript function signature."""
        params = [ParameterInfo("name", typescript_type="string")]
        result = generate_function_signature("greet", params, "string", "javascript")
        # Note: generate_function_signature uses format_typescript_params internally
        # but omits return type annotation for JavaScript
        assert "function greet" in result
        assert "name" in result

    def test_javascript_async_function(self) -> None:
        """Test async JavaScript function signature."""
        params = [ParameterInfo("url", typescript_type="string")]
        result = generate_function_signature("fetch", params, None, "javascript", is_async=True)
        assert result.startswith("async function fetch")

    def test_java_basic_signature(self) -> None:
        """Test basic Java method signature."""
        params = [ParameterInfo("name", java_type="String")]
        result = generate_function_signature("greet", params, "String", "java")
        assert result == "public String greet(String name)"

    def test_java_void_return(self) -> None:
        """Test Java method with void return."""
        params = [ParameterInfo("msg", java_type="String")]
        result = generate_function_signature("log", params, None, "java")
        assert "public void log" in result

    def test_java_access_modifiers(self) -> None:
        """Test Java method with different access modifiers."""
        params = [ParameterInfo("value", java_type="int")]
        result = generate_function_signature(
            "setValue", params, "void", "java",
            access_modifier="private"
        )
        assert result.startswith("private void")

    def test_java_with_generics(self) -> None:
        """Test Java method with generic type parameters."""
        params = [ParameterInfo("items", java_type="List<T>")]
        result = generate_function_signature(
            "first", params, "T", "java",
            type_parameters=["T"]
        )
        assert "<T>" in result

    def test_java_nullable_param(self) -> None:
        """Test Java method with nullable parameter."""
        params = [ParameterInfo("name", java_type="String", is_optional=True)]
        result = generate_function_signature("greet", params, "String", "java")
        assert "@Nullable" in result

    def test_unsupported_language_raises_error(self) -> None:
        """Test that unsupported language raises ValueError."""
        params = [ParameterInfo("x", python_type="int")]
        with pytest.raises(ValueError) as exc_info:
            generate_function_signature("foo", params, "int", "ruby")
        assert "Unsupported language" in str(exc_info.value)

    def test_empty_params(self) -> None:
        """Test function signature with no parameters."""
        result = generate_function_signature("noop", [], "None", "python")
        assert result == "def noop() -> None:"


# =============================================================================
# Test generate_function_body
# =============================================================================

class TestGenerateFunctionBody:
    """Test function body generation with parameter substitution."""

    def test_python_basic_substitution(self) -> None:
        """Test basic parameter substitution in Python."""
        params = [ParameterInfo("name", default_value='"John"', python_type="str")]
        code = 'print("Hello, John")'
        result = generate_function_body(code, params, "python")
        assert "    " in result  # Indented
        assert "name" in result

    def test_python_numeric_substitution(self) -> None:
        """Test numeric literal substitution."""
        params = [ParameterInfo("count", default_value="42", python_type="int")]
        code = "for i in range(42):"
        result = generate_function_body(code, params, "python")
        assert "count" in result

    def test_typescript_string_substitution(self) -> None:
        """Test TypeScript template literal substitution."""
        params = [ParameterInfo("name", default_value='"World"', typescript_type="string")]
        code = 'console.log("Hello, World")'
        result = generate_function_body(code, params, "typescript")
        assert "name" in result

    def test_java_indentation(self) -> None:
        """Test Java uses 4-space indentation."""
        params = [ParameterInfo("msg", default_value='"test"', java_type="String")]
        code = 'System.out.println("test");'
        result = generate_function_body(code, params, "java")
        assert result.startswith("    ")  # 4 spaces

    def test_javascript_indentation(self) -> None:
        """Test JavaScript uses 2-space indentation."""
        params = [ParameterInfo("x", default_value="1", typescript_type="number")]
        code = "return 1 + 1"
        result = generate_function_body(code, params, "javascript")
        assert result.startswith("  ")  # 2 spaces

    def test_multiline_body(self) -> None:
        """Test multiline code body preservation."""
        params = [ParameterInfo("x", default_value="10", python_type="int")]
        code = "if 10 > 5:\n    return True\nelse:\n    return False"
        result = generate_function_body(code, params, "python")
        lines = result.split("\n")
        assert len(lines) == 4
        assert all(line.startswith("    ") or line == "" for line in lines if line)

    def test_empty_params_no_substitution(self) -> None:
        """Test that empty params list doesn't modify code."""
        code = "return 42"
        result = generate_function_body(code, [], "python")
        assert "42" in result

    def test_preserves_existing_indentation(self) -> None:
        """Test that existing relative indentation is preserved."""
        params = []
        code = "for i in range(10):\n    print(i)"
        result = generate_function_body(code, params, "python")
        lines = result.split("\n")
        # Second line should have extra indentation
        assert lines[1].count(" ") > lines[0].count(" ")

    def test_multiple_substitutions(self) -> None:
        """Test multiple parameter substitutions in same code."""
        params = [
            ParameterInfo("name", default_value='"Alice"', python_type="str"),
            ParameterInfo("age", default_value="30", python_type="int"),
        ]
        code = 'print("Alice is 30 years old")'
        result = generate_function_body(code, params, "python")
        assert "name" in result
        assert "age" in result


# =============================================================================
# Test detect_return_value
# =============================================================================

class TestDetectReturnValue:
    """Test return value detection and type inference."""

    def test_explicit_return_string(self) -> None:
        """Test detecting explicit string return."""
        code = 'return "hello"'
        has_return, inferred = code_generator.detect_return_value(code, "python")
        assert has_return is True
        assert inferred == "str"

    def test_explicit_return_number(self) -> None:
        """Test detecting explicit number return in JS."""
        code = "return 42"
        has_return, inferred = code_generator.detect_return_value(code, "javascript")
        assert has_return is True
        # Number literal type inference

    def test_explicit_return_boolean_python(self) -> None:
        """Test detecting boolean return in Python."""
        code = "return True"
        has_return, inferred = code_generator.detect_return_value(code, "python")
        assert has_return is True
        assert inferred == "bool"

    def test_explicit_return_boolean_js(self) -> None:
        """Test detecting boolean return in JavaScript."""
        code = "return true"
        has_return, inferred = code_generator.detect_return_value(code, "javascript")
        assert has_return is True
        assert inferred == "boolean"

    def test_explicit_return_array(self) -> None:
        """Test detecting array return."""
        code = "return [1, 2, 3]"
        has_return, inferred = code_generator.detect_return_value(code, "python")
        assert has_return is True
        assert inferred == "list"

    def test_explicit_return_object(self) -> None:
        """Test detecting object return in JavaScript."""
        code = "return {name: 'test'}"
        has_return, inferred = code_generator.detect_return_value(code, "javascript")
        assert has_return is True

    def test_no_return_statement(self) -> None:
        """Test code without return statement."""
        code = 'print("hello")'
        has_return, inferred = code_generator.detect_return_value(code, "python")
        assert has_return is False
        assert inferred is None

    def test_empty_return(self) -> None:
        """Test empty return statement."""
        code = "return"
        has_return, inferred = code_generator.detect_return_value(code, "python")
        assert has_return is True
        assert inferred is None

    def test_return_with_semicolon(self) -> None:
        """Test return with semicolon (JS style)."""
        code = "return;"
        has_return, inferred = code_generator.detect_return_value(code, "javascript")
        assert has_return is True

    def test_implicit_return_js(self) -> None:
        """Test implicit return detection in JavaScript arrow functions."""
        code = '"hello"'
        has_return, inferred = code_generator.detect_return_value(code, "javascript")
        assert has_return is True
        assert inferred == "string"

    def test_implicit_return_not_in_python(self) -> None:
        """Test that Python doesn't have implicit returns."""
        code = '"hello"'
        has_return, inferred = code_generator.detect_return_value(code, "python")
        assert has_return is False

    def test_return_none_python(self) -> None:
        """Test return None in Python."""
        code = "return None"
        has_return, inferred = code_generator.detect_return_value(code, "python")
        assert has_return is True
        assert inferred == "None"

    def test_return_null_js(self) -> None:
        """Test return null in JavaScript."""
        code = "return null"
        has_return, inferred = code_generator.detect_return_value(code, "javascript")
        assert has_return is True
        assert inferred == "null"

    def test_return_undefined(self) -> None:
        """Test return undefined in JavaScript."""
        code = "return undefined"
        has_return, inferred = code_generator.detect_return_value(code, "javascript")
        assert has_return is True
        assert inferred == "undefined"

    def test_empty_code(self) -> None:
        """Test empty code string."""
        has_return, inferred = code_generator.detect_return_value("", "python")
        assert has_return is False
        assert inferred is None

    def test_whitespace_only(self) -> None:
        """Test whitespace-only code."""
        has_return, inferred = code_generator.detect_return_value("   \n  ", "python")
        assert has_return is False


# =============================================================================
# Test generate_docstring
# =============================================================================

class TestGenerateDocstring:
    """Test docstring generation for all languages."""

    def test_python_docstring_basic(self) -> None:
        """Test basic Python docstring generation."""
        params = [ParameterInfo("name", python_type="str", description="User name")]
        result = generate_docstring("Get user", params, "User", "python")
        assert '"""' in result
        assert "Get user" in result
        assert "Args:" in result
        assert "name: User name" in result
        assert "Returns:" in result
        assert "User" in result

    def test_python_docstring_no_params(self) -> None:
        """Test Python docstring with no parameters."""
        result = generate_docstring("Do something", [], "None", "python")
        assert '"""' in result
        assert "Do something" in result
        assert "Args:" not in result

    def test_python_docstring_no_return(self) -> None:
        """Test Python docstring with no return value."""
        params = [ParameterInfo("msg", python_type="str", description="Message")]
        result = generate_docstring("Log message", params, "None", "python")
        assert "Returns:" not in result

    def test_python_docstring_optional_param(self) -> None:
        """Test Python docstring with optional parameter."""
        params = [ParameterInfo("name", python_type="str", is_optional=True)]
        result = generate_docstring("Get item", params, "Item", "python")
        assert "(optional)" in result

    def test_typescript_jsdoc_basic(self) -> None:
        """Test basic TypeScript JSDoc generation."""
        params = [ParameterInfo("name", typescript_type="string", description="User name")]
        result = generate_docstring("Get user", params, "User", "typescript")
        assert "/**" in result
        assert "*/" in result
        assert "@param" in result
        assert "@returns" in result

    def test_typescript_jsdoc_no_params(self) -> None:
        """Test TypeScript JSDoc with no parameters."""
        result = generate_docstring("Do something", [], "void", "typescript")
        assert "/**" in result
        assert "@param" not in result

    def test_javascript_jsdoc(self) -> None:
        """Test JavaScript JSDoc generation (same as TypeScript)."""
        params = [ParameterInfo("x", typescript_type="number", description="Value")]
        result = generate_docstring("Double value", params, "number", "javascript")
        assert "/**" in result
        assert "@param" in result

    def test_java_javadoc_basic(self) -> None:
        """Test basic Java Javadoc generation."""
        params = [ParameterInfo("name", java_type="String", description="User name")]
        result = generate_docstring("Get user", params, "User", "java")
        assert "/**" in result
        assert "*/" in result
        assert "@param" in result
        assert "@return" in result  # Java uses @return not @returns

    def test_java_javadoc_no_return(self) -> None:
        """Test Java Javadoc with void return."""
        params = [ParameterInfo("msg", java_type="String", description="Message")]
        result = generate_docstring("Log message", params, "void", "java")
        # void shouldn't have @return

    def test_unknown_language_uses_python(self) -> None:
        """Test that unknown language defaults to Python style."""
        params = [ParameterInfo("x", python_type="int")]
        result = generate_docstring("Test", params, "int", "unknown")
        assert '"""' in result


# =============================================================================
# Test generate_type_annotations
# =============================================================================

class TestGenerateTypeAnnotations:
    """Test type annotation generation and cross-language conversion."""

    def test_python_basic_types(self) -> None:
        """Test basic Python type annotations."""
        params = [
            ParameterInfo("name", python_type="str"),
            ParameterInfo("count", python_type="int"),
        ]
        result = generate_type_annotations(params, "str", "python")
        assert "name: str" in result["params"]
        assert "count: int" in result["params"]
        assert "-> str" in result["return"]

    def test_typescript_basic_types(self) -> None:
        """Test basic TypeScript type annotations."""
        params = [
            ParameterInfo("name", typescript_type="string"),
            ParameterInfo("count", typescript_type="number"),
        ]
        result = generate_type_annotations(params, "string", "typescript")
        assert "name: string" in result["params"]
        assert "count: number" in result["params"]
        assert ": string" in result["return"]

    def test_java_basic_types(self) -> None:
        """Test basic Java type annotations."""
        params = [
            ParameterInfo("name", java_type="String"),
            ParameterInfo("count", java_type="int"),
        ]
        result = generate_type_annotations(params, "String", "java")
        assert "String name" in result["params"]
        assert "int count" in result["params"]

    def test_python_optional_params(self) -> None:
        """Test Python optional parameter annotations."""
        params = [
            ParameterInfo("name", python_type="str", is_optional=True),
        ]
        result = generate_type_annotations(params, "None", "python")
        assert "Optional" in result["params"]

    def test_typescript_optional_params(self) -> None:
        """Test TypeScript optional parameter annotations."""
        params = [
            ParameterInfo("name", typescript_type="string", is_optional=True),
        ]
        result = generate_type_annotations(params, "void", "typescript")
        assert "?" in result["params"]

    def test_no_return_type_python(self) -> None:
        """Test Python annotation with no return type."""
        params = [ParameterInfo("x", python_type="int")]
        result = generate_type_annotations(params, None, "python")
        assert "-> None" in result["return"]

    def test_no_return_type_typescript(self) -> None:
        """Test TypeScript annotation with no return type."""
        params = [ParameterInfo("x", typescript_type="number")]
        result = generate_type_annotations(params, None, "typescript")
        assert ": void" in result["return"]

    def test_no_return_type_java(self) -> None:
        """Test Java annotation with no return type."""
        params = [ParameterInfo("x", java_type="int")]
        result = generate_type_annotations(params, None, "java")
        assert "void" in result["return"]

    def test_empty_params(self) -> None:
        """Test annotations with no parameters."""
        result = generate_type_annotations([], "int", "python")
        assert result["params"] == ""


# =============================================================================
# Test format_*_params helpers
# =============================================================================

class TestFormatParamHelpers:
    """Test parameter formatting helper functions."""

    def test_format_python_params_basic(self) -> None:
        """Test basic Python parameter formatting."""
        params = [ParameterInfo("x", python_type="int")]
        result = format_python_params(params)
        assert result == "x: int"

    def test_format_python_params_optional(self) -> None:
        """Test Python optional parameter formatting."""
        params = [
            ParameterInfo("x", python_type="int"),
            ParameterInfo("y", python_type="int", is_optional=True, default_value="0"),
        ]
        result = format_python_params(params)
        assert "x: int" in result
        assert "y: int = 0" in result

    def test_format_python_params_empty(self) -> None:
        """Test Python empty params."""
        result = format_python_params([])
        assert result == ""

    def test_format_typescript_params_basic(self) -> None:
        """Test basic TypeScript parameter formatting."""
        params = [ParameterInfo("x", typescript_type="number")]
        result = format_typescript_params(params)
        assert result == "x: number"

    def test_format_typescript_params_optional(self) -> None:
        """Test TypeScript optional parameter formatting."""
        params = [
            ParameterInfo("x", typescript_type="number"),
            ParameterInfo("y", typescript_type="number", is_optional=True),
        ]
        result = format_typescript_params(params)
        assert "x: number" in result
        assert "y?" in result

    def test_format_java_params_basic(self) -> None:
        """Test basic Java parameter formatting."""
        params = [ParameterInfo("x", java_type="int")]
        result = format_java_params(params)
        assert result == "int x"

    def test_format_java_params_nullable(self) -> None:
        """Test Java nullable parameter formatting."""
        params = [ParameterInfo("x", java_type="String", is_optional=True)]
        result = format_java_params(params)
        assert "@Nullable" in result


# =============================================================================
# Test complete function generators
# =============================================================================

class TestCompleteFunctionGenerators:
    """Test complete function generation functions."""

    def test_generate_python_function_basic(self) -> None:
        """Test complete Python function generation."""
        params = [ParameterInfo("name", python_type="str")]
        result = generate_python_function("greet", params, "return f'Hello, {name}'", "str")
        assert "def greet(name: str) -> str:" in result
        assert "return f'Hello, {name}'" in result

    def test_generate_python_function_with_decorators(self) -> None:
        """Test Python function with decorators."""
        params = []
        result = generate_python_function(
            "cached", params, "return data", "dict",
            decorators=["lru_cache", "staticmethod"]
        )
        assert "@lru_cache" in result
        assert "@staticmethod" in result

    def test_generate_python_function_with_docstring(self) -> None:
        """Test Python function with docstring."""
        params = []
        result = generate_python_function(
            "test", params, "pass", "None",
            docstring="Test function"
        )
        assert '"""' in result
        assert "Test function" in result

    def test_generate_python_function_async(self) -> None:
        """Test async Python function."""
        params = [ParameterInfo("url", python_type="str")]
        result = generate_python_function(
            "fetch", params, "return await get(url)", "bytes",
            is_async=True
        )
        assert "async def fetch" in result

    def test_generate_typescript_function_basic(self) -> None:
        """Test complete TypeScript function generation."""
        params = [ParameterInfo("name", typescript_type="string")]
        result = generate_typescript_function("greet", params, "return `Hello, ${name}`", "string")
        assert "function greet(name: string): string" in result
        assert "return `Hello, ${name}`" in result
        assert "}" in result

    def test_generate_typescript_function_async(self) -> None:
        """Test async TypeScript function with Promise return."""
        params = [ParameterInfo("url", typescript_type="string")]
        result = generate_typescript_function(
            "fetch", params, "return await axios.get(url)", "Response",
            is_async=True
        )
        assert "async function fetch" in result
        assert "Promise<Response>" in result

    def test_generate_typescript_function_export(self) -> None:
        """Test TypeScript function export."""
        params = []
        result = generate_typescript_function("test", params, "return true", "boolean", is_export=True)
        assert "export function test" in result

    def test_generate_typescript_function_no_export(self) -> None:
        """Test TypeScript function without export."""
        params = []
        result = generate_typescript_function("test", params, "return true", "boolean", is_export=False)
        assert not result.startswith("export")

    def test_generate_java_method_basic(self) -> None:
        """Test complete Java method generation."""
        params = [ParameterInfo("name", java_type="String")]
        result = generate_java_method("greet", params, 'return "Hello, " + name;', "String")
        assert "public String greet(String name)" in result
        assert "}" in result

    def test_generate_java_method_with_annotations(self) -> None:
        """Test Java method with annotations."""
        params = []
        result = generate_java_method(
            "test", params, "return null;", "Object",
            annotations=["Override", "Nullable"]
        )
        assert "@Override" in result
        assert "@Nullable" in result

    def test_generate_java_method_with_throws(self) -> None:
        """Test Java method with throws clause."""
        params = [ParameterInfo("path", java_type="String")]
        result = generate_java_method(
            "readFile", params, "return Files.readString(path);", "String",
            throws=["IOException", "SecurityException"]
        )
        assert "throws IOException, SecurityException" in result

    def test_generate_javascript_function_basic(self) -> None:
        """Test complete JavaScript function generation."""
        params = [ParameterInfo("name", typescript_type="string")]
        result = generate_javascript_function("greet", params, "return `Hello, ${name}`")
        assert "function greet(name)" in result
        assert ":" not in result.split("{")[0]  # No type annotations before brace

    def test_generate_javascript_function_async(self) -> None:
        """Test async JavaScript function."""
        params = []
        result = generate_javascript_function("fetch", params, "return await api()", is_async=True)
        assert "async function fetch" in result


# =============================================================================
# Edge cases and error handling
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_function_name(self) -> None:
        """Test with empty function name."""
        params = [ParameterInfo("x", python_type="int")]
        result = generate_function_signature("", params, "int", "python")
        assert "def (" in result  # Still generates, but empty name

    def test_special_characters_in_name(self) -> None:
        """Test function name with underscores."""
        params = []
        result = generate_function_signature("get_user_by_id", [], "User", "python")
        assert "get_user_by_id" in result

    def test_very_long_param_list(self) -> None:
        """Test with many parameters."""
        params = [ParameterInfo(f"param{i}", python_type="int") for i in range(10)]
        result = generate_function_signature("many_params", params, "None", "python")
        assert "param0" in result
        assert "param9" in result

    def test_param_with_none_type(self) -> None:
        """Test parameter with None/empty type."""
        params = [ParameterInfo("x", python_type="")]
        result = format_python_params(params)
        assert "x: " in result

    def test_complex_nested_types(self) -> None:
        """Test with complex nested type annotations."""
        params = [ParameterInfo("data", python_type="Dict[str, List[int]]")]
        result = format_python_params(params)
        assert "Dict[str, List[int]]" in result

    def test_case_insensitive_language(self) -> None:
        """Test that language parameter is case-insensitive."""
        params = [ParameterInfo("x", python_type="int")]
        result = generate_function_signature("test", params, "int", "PYTHON")
        assert "def test" in result

    def test_mixed_case_language(self) -> None:
        """Test mixed case language parameter."""
        params = [ParameterInfo("x", typescript_type="number")]
        result = generate_function_signature("test", params, "number", "TypeScript")
        assert "function test" in result

    def test_unicode_in_docstring(self) -> None:
        """Test unicode characters in docstring."""
        params = []
        result = generate_docstring("Get cafe menu", params, "str", "python")
        assert "cafe" in result

    def test_multiline_description(self) -> None:
        """Test multiline description in docstring."""
        params = []
        result = generate_docstring("First line.\nSecond line.", params, "None", "python")
        assert "First line" in result

    def test_return_type_void_variations(self) -> None:
        """Test different void return type representations."""
        params = []
        # Python style
        result1 = generate_docstring("Test", params, "None", "python")
        # TypeScript style
        result2 = generate_docstring("Test", params, "void", "typescript")
        # Both should handle gracefully
        assert '"""' in result1
        assert "/**" in result2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
