"""Unit tests for call site replacement in the code generation engine.

Tests for:
- generate_replacement_call
- preserve_call_site_indentation
- format_arguments_for_call

Phase 2, Task 2.3: Call site replacement tests.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ast_grep_mcp.models.deduplication import ParameterInfo
from main import (
    format_arguments_for_call,
    preserve_call_site_indentation,
)

from ast_grep_mcp.features.deduplication.generator import CodeGenerator


class TestGenerateReplacementCall:
    """Tests for generate_replacement_call function."""

    # Basic function calls
    def test_simple_python_call(self, code_generator):
        """Test basic Python function call."""
        result = code_generator.generate_replacement_call("process_data", ["items", "config"], "python")
        assert result == "process_data(items, config)"

    def test_simple_javascript_call(self, code_generator):
        """Test basic JavaScript function call."""
        result = code_generator.generate_replacement_call("fetchData", ["url", "options"], "javascript")
        assert result == "fetchData(url, options)"

    def test_simple_typescript_call(self, code_generator):
        """Test basic TypeScript function call."""
        result = code_generator.generate_replacement_call("getData", ["id"], "typescript")
        assert result == "getData(id)"

    def test_empty_arguments(self, code_generator):
        """Test function call with no arguments."""
        result = code_generator.generate_replacement_call("getData", [], "python")
        assert result == "getData()"

    def test_single_argument(self, code_generator):
        """Test function call with single argument."""
        result = code_generator.generate_replacement_call("process", ["value"], "python")
        assert result == "process(value)"

    # Method calls
    def test_method_call_with_this(self, code_generator):
        """Test method call with 'this' object."""
        result = code_generator.generate_replacement_call(
            "fetch", ["url"], "typescript", is_method=True, object_name="this"
        )
        assert result == "this.fetch(url)"

    def test_method_call_with_self(self, code_generator):
        """Test method call with 'self' object."""
        result = code_generator.generate_replacement_call(
            "process", ["data"], "python", is_method=True, object_name="self"
        )
        assert result == "self.process(data)"

    def test_method_call_with_instance(self, code_generator):
        """Test method call with custom instance name."""
        result = code_generator.generate_replacement_call(
            "save", ["record"], "java", is_method=True, object_name="repository"
        )
        assert result == "repository.save(record)"

    def test_method_call_no_args(self, code_generator):
        """Test method call with no arguments."""
        result = code_generator.generate_replacement_call(
            "reset", [], "typescript", is_method=True, object_name="this"
        )
        assert result == "this.reset()"

    # Language-specific behaviors
    def test_go_call(self, code_generator):
        """Test Go function call."""
        result = code_generator.generate_replacement_call("ProcessData", ["items"], "go")
        assert result == "ProcessData(items)"

    def test_rust_call(self, code_generator):
        """Test Rust function call."""
        result = code_generator.generate_replacement_call("process_data", ["items"], "rust")
        assert result == "process_data(items)"

    def test_java_call(self, code_generator):
        """Test Java function call."""
        result = code_generator.generate_replacement_call("processData", ["items", "config"], "java")
        assert result == "processData(items, config)"

    def test_ruby_call_with_args(self, code_generator):
        """Test Ruby function call with arguments."""
        result = code_generator.generate_replacement_call("process_data", ["items"], "ruby")
        assert result == "process_data(items)"

    def test_ruby_call_no_args(self, code_generator):
        """Test Ruby function call without arguments (no parentheses)."""
        result = code_generator.generate_replacement_call("get_data", [], "ruby")
        assert result == "get_data"

    def test_scala_call_with_args(self, code_generator):
        """Test Scala function call with arguments."""
        result = code_generator.generate_replacement_call("processData", ["items"], "scala")
        assert result == "processData(items)"

    def test_scala_call_no_args(self, code_generator):
        """Test Scala function call without arguments (no parentheses)."""
        result = code_generator.generate_replacement_call("getData", [], "scala")
        assert result == "getData"

    def test_kotlin_call(self, code_generator):
        """Test Kotlin function call."""
        result = code_generator.generate_replacement_call("processData", ["items"], "kotlin")
        assert result == "processData(items)"

    def test_swift_call(self, code_generator):
        """Test Swift function call."""
        result = code_generator.generate_replacement_call("processData", ["items"], "swift")
        assert result == "processData(items)"

    def test_c_call(self, code_generator):
        """Test C function call."""
        result = code_generator.generate_replacement_call("process_data", ["items", "count"], "c")
        assert result == "process_data(items, count)"

    def test_cpp_call(self, code_generator):
        """Test C++ function call."""
        result = code_generator.generate_replacement_call("processData", ["items"], "cpp")
        assert result == "processData(items)"

    def test_unknown_language_defaults(self, code_generator):
        """Test unknown language falls back to standard syntax."""
        result = code_generator.generate_replacement_call("process", ["data"], "unknown_lang")
        assert result == "process(data)"

    # Edge cases
    def test_complex_argument_expressions(self, code_generator):
        """Test with complex argument expressions."""
        result = code_generator.generate_replacement_call(
            "compute",
            ["arr[0]", "obj.prop", "func(x)", "a + b"],
            "python"
        )
        assert result == "compute(arr[0], obj.prop, func(x), a + b)"

    def test_string_literal_arguments(self, code_generator):
        """Test with string literal arguments."""
        result = code_generator.generate_replacement_call(
            "log",
            ['"message"', "'value'"],
            "javascript"
        )
        assert result == 'log("message", \'value\')'

    def test_method_flag_without_object_name(self, code_generator):
        """Test is_method=True without object_name uses function syntax."""
        result = code_generator.generate_replacement_call(
            "process", ["data"], "python", is_method=True, object_name=None
        )
        assert result == "process(data)"


class TestPreserveCallSiteIndentation:
    """Tests for preserve_call_site_indentation function."""

    # Basic indentation preservation
    def test_spaces_indentation(self):
        """Test preserving space-based indentation."""
        result = preserve_call_site_indentation("    x = 1", "process_data()")
        assert result == "    process_data()"

    def test_tabs_indentation(self):
        """Test preserving tab-based indentation."""
        result = preserve_call_site_indentation("\t\tx = 1", "process_data()")
        assert result == "\t\tprocess_data()"

    def test_two_space_indentation(self):
        """Test preserving 2-space indentation."""
        result = preserve_call_site_indentation("  result = compute()", "helper()")
        assert result == "  helper()"

    def test_no_indentation(self):
        """Test code with no indentation."""
        result = preserve_call_site_indentation("x = 1", "process_data()")
        assert result == "process_data()"

    # Multi-line replacements
    def test_multiline_replacement_with_spaces(self):
        """Test multi-line replacement preserves indentation on all lines."""
        original = "  result = compute()"
        replacement = "helper(\n    arg1,\n    arg2\n)"
        result = preserve_call_site_indentation(original, replacement)
        expected = "  helper(\n      arg1,\n      arg2\n  )"
        assert result == expected

    def test_multiline_replacement_with_tabs(self):
        """Test multi-line replacement with tab indentation."""
        original = "\t\tif True:"
        replacement = "check_condition(\n    value)"
        result = preserve_call_site_indentation(original, replacement)
        assert result.startswith("\t\tcheck_condition(")
        assert "\t\t    value)" in result

    def test_multiline_with_empty_lines(self):
        """Test multi-line replacement preserves empty lines."""
        original = "    code = here"
        replacement = "func(\n\n    arg)"
        result = preserve_call_site_indentation(original, replacement)
        lines = result.split('\n')
        assert lines[0] == "    func("
        assert lines[1] == ""  # Empty line preserved
        assert lines[2] == "        arg)"

    # Edge cases
    def test_empty_original_code(self):
        """Test with empty original code."""
        result = preserve_call_site_indentation("", "process_data()")
        assert result == "process_data()"

    def test_empty_replacement(self):
        """Test with empty replacement."""
        result = preserve_call_site_indentation("    x = 1", "")
        assert result == ""

    def test_both_empty(self):
        """Test with both inputs empty."""
        result = preserve_call_site_indentation("", "")
        assert result == ""

    def test_whitespace_only_original(self):
        """Test original code that is only whitespace."""
        result = preserve_call_site_indentation("   ", "process_data()")
        assert result == "process_data()"

    def test_multiline_original_uses_first_line_indent(self):
        """Test that indentation is taken from first non-empty line."""
        original = "    first_line\n        second_line"
        replacement = "call()"
        result = preserve_call_site_indentation(original, replacement)
        assert result == "    call()"

    def test_mixed_space_tab_original(self):
        """Test original with mixed spaces and tabs preserves exactly."""
        original = "\t  mixed_indent"
        replacement = "call()"
        result = preserve_call_site_indentation(original, replacement)
        assert result == "\t  call()"

    def test_deep_nesting(self):
        """Test deeply nested indentation."""
        original = "            deeply_nested = True"
        replacement = "process()"
        result = preserve_call_site_indentation(original, replacement)
        assert result == "            process()"


class TestFormatArgumentsForCall:
    """Tests for format_arguments_for_call function."""

    def _create_params(self, *specs):
        """Helper to create ParameterInfo objects from specs.

        Each spec is (name, python_type, default_value, is_optional)
        or just (name,) for simple params.
        """
        params = []
        for spec in specs:
            if len(spec) == 1:
                params.append(ParameterInfo(spec[0]))
            elif len(spec) == 2:
                params.append(ParameterInfo(spec[0], python_type=spec[1]))
            elif len(spec) == 4:
                params.append(ParameterInfo(
                    spec[0],
                    python_type=spec[1],
                    default_value=spec[2],
                    is_optional=spec[3]
                ))
            else:
                params.append(ParameterInfo(spec[0]))
        return params

    # Positional style tests
    def test_positional_simple(self):
        """Test simple positional arguments."""
        params = self._create_params(("name", "str"), ("age", "int"))
        result = format_arguments_for_call(params, ['"Alice"', "25"], "python", "positional")
        assert result == '"Alice", 25'

    def test_positional_single_arg(self):
        """Test single positional argument."""
        params = self._create_params(("name",))
        result = format_arguments_for_call(params, ['"Bob"'], "python", "positional")
        assert result == '"Bob"'

    def test_positional_empty_params(self):
        """Test with no parameters."""
        result = format_arguments_for_call([], [], "python", "positional")
        assert result == ""

    def test_positional_fewer_values_than_params(self):
        """Test positional with fewer values (optional params omitted)."""
        params = self._create_params(
            ("name", "str", None, False),
            ("age", "int", "0", True)
        )
        result = format_arguments_for_call(params, ['"Alice"'], "python", "positional")
        assert result == '"Alice"'

    # Python named style tests
    def test_python_named_style(self):
        """Test Python keyword arguments."""
        params = self._create_params(
            ("name", "str", None, False),
            ("age", "int", None, False)
        )
        result = format_arguments_for_call(params, ['"Alice"', "25"], "python", "named")
        assert result == 'name="Alice", age=25'

    def test_python_named_skips_defaults(self):
        """Test that named style skips default values."""
        params = self._create_params(
            ("name", "str", None, False),
            ("age", "int", "0", True)
        )
        result = format_arguments_for_call(params, ['"Alice"', "0"], "python", "named")
        assert result == 'name="Alice"'  # age=0 skipped as it matches default

    def test_python_named_required_without_value(self):
        """Test required param without value gets placeholder."""
        params = self._create_params(
            ("name", "str", None, False),
            ("age", "int", None, False)
        )
        result = format_arguments_for_call(params, ['"Alice"'], "python", "named")
        assert "name=" in result
        assert "age=..." in result

    # TypeScript/JavaScript named style tests
    def test_typescript_named_object_style(self):
        """Test TypeScript object destructuring style."""
        params = self._create_params(
            ("name", "str", None, False),
            ("age", "int", None, False)
        )
        result = format_arguments_for_call(params, ['"Bob"', "30"], "typescript", "named")
        assert result == '{ name: "Bob", age: 30 }'

    def test_javascript_named_object_style(self):
        """Test JavaScript object destructuring style."""
        params = self._create_params(("id",), ("value",))
        result = format_arguments_for_call(params, ["123", '"test"'], "javascript", "named")
        assert result == '{ id: 123, value: "test" }'

    def test_typescript_named_skips_defaults(self):
        """Test TypeScript named skips default values."""
        params = self._create_params(
            ("name", "str", None, False),
            ("active", "bool", "true", True)
        )
        result = format_arguments_for_call(params, ['"Test"', "true"], "typescript", "named")
        assert result == '{ name: "Test" }'

    def test_typescript_named_empty_result(self):
        """Test TypeScript named with all defaults skipped."""
        params = self._create_params(
            ("flag", "bool", "false", True)
        )
        result = format_arguments_for_call(params, ["false"], "typescript", "named")
        assert result == "{}"

    def test_typescript_required_without_value(self):
        """Test TypeScript required param without value."""
        params = self._create_params(
            ("id", "number", None, False)
        )
        result = format_arguments_for_call(params, [], "typescript", "named")
        assert result == "{ id: undefined }"

    # Java tests
    def test_java_named_falls_back_to_positional(self):
        """Test Java doesn't support named args, falls back to positional."""
        params = self._create_params(("name",), ("age",))
        result = format_arguments_for_call(params, ['"Alice"', "25"], "java", "named")
        assert result == '"Alice", 25'

    # Mixed style tests (Python only)
    def test_python_mixed_style(self):
        """Test Python mixed positional/named style."""
        params = self._create_params(
            ("name", "str", None, False),  # required -> positional
            ("age", "int", "0", True)      # optional -> named
        )
        result = format_arguments_for_call(params, ['"Alice"', "25"], "python", "mixed")
        assert result == '"Alice", age=25'

    def test_python_mixed_skips_default_values(self):
        """Test mixed style skips optional params with default values."""
        params = self._create_params(
            ("name", "str", None, False),
            ("active", "bool", "True", True)
        )
        result = format_arguments_for_call(params, ['"Bob"', "True"], "python", "mixed")
        assert result == '"Bob"'  # active=True skipped

    def test_python_mixed_all_required(self):
        """Test mixed style with all required params (all positional)."""
        params = self._create_params(
            ("a", "int", None, False),
            ("b", "int", None, False)
        )
        result = format_arguments_for_call(params, ["1", "2"], "python", "mixed")
        assert result == "1, 2"

    def test_typescript_mixed_falls_back(self):
        """Test non-Python mixed style falls back to positional."""
        params = self._create_params(("a",), ("b",))
        result = format_arguments_for_call(params, ["1", "2"], "typescript", "mixed")
        assert result == "1, 2"

    # Edge cases
    def test_unknown_style_falls_back(self):
        """Test unknown style falls back to positional."""
        params = self._create_params(("a",), ("b",))
        result = format_arguments_for_call(params, ["1", "2"], "python", "unknown_style")
        assert result == "1, 2"

    def test_unknown_language_uses_positional(self):
        """Test unknown language uses positional for named style."""
        params = self._create_params(("a",), ("b",))
        result = format_arguments_for_call(params, ["1", "2"], "unknown", "named")
        assert result == "1, 2"

    def test_complex_values(self):
        """Test with complex value expressions."""
        params = self._create_params(("data",), ("callback",))
        values = ['{"key": "value"}', "() => console.log('done')"]
        result = format_arguments_for_call(params, values, "javascript", "positional")
        assert result == '{"key": "value"}, () => console.log(\'done\')'

    def test_many_arguments(self):
        """Test with many arguments."""
        params = [ParameterInfo(f"arg{i}") for i in range(10)]
        values = [str(i) for i in range(10)]
        result = format_arguments_for_call(params, values, "python", "positional")
        assert result == "0, 1, 2, 3, 4, 5, 6, 7, 8, 9"


class TestCallSiteIntegration:
    """Integration tests combining multiple call site functions."""

    def test_generate_and_indent_call(self, code_generator):
        """Test generating a call and applying indentation."""
        # Generate the call
        call = code_generator.generate_replacement_call("process_data", ["items", "config"], "python")

        # Apply indentation
        original = "        result = old_code()"
        indented = preserve_call_site_indentation(original, call)

        assert indented == "        process_data(items, config)"

    def test_format_args_and_generate_call(self, code_generator):
        """Test formatting arguments then generating the call."""
        # Format arguments
        params = [
            ParameterInfo("name", python_type="str"),
            ParameterInfo("age", python_type="int", default_value="0", is_optional=True)
        ]
        args_str = format_arguments_for_call(params, ['"Alice"', "25"], "python", "named")

        # The formatted args need to be split for generate_replacement_call
        # In practice, you'd pass individual values
        call = code_generator.generate_replacement_call("create_user", ['"Alice"', "25"], "python")

        assert call == 'create_user("Alice", 25)'

    def test_method_call_with_indentation(self, code_generator):
        """Test method call generation with indentation preservation."""
        # Generate method call
        call = code_generator.generate_replacement_call(
            "fetchData", ["this.userId"], "typescript",
            is_method=True, object_name="this.service"
        )

        # Apply indentation
        original = "    const data = await fetch();"
        indented = preserve_call_site_indentation(original, call)

        assert indented == "    this.service.fetchData(this.userId)"

    def test_multiline_call_with_named_args(self):
        """Test multi-line call pattern with preserved indentation."""
        # Create a multi-line replacement (like what might come from complex args)
        replacement = "callFunction(\n    arg1,\n    arg2,\n    arg3\n)"

        original = "        old_function_call()"
        result = preserve_call_site_indentation(original, replacement)

        lines = result.split('\n')
        assert lines[0] == "        callFunction("
        assert "arg1" in lines[1]
        assert "arg2" in lines[2]


class TestEdgeCasesAndErrorHandling:
    """Tests for edge cases and error handling."""

    def test_special_characters_in_function_name(self, code_generator):
        """Test function names with underscores and numbers."""
        result = code_generator.generate_replacement_call("process_data_v2", ["x"], "python")
        assert result == "process_data_v2(x)"

    def test_special_characters_in_arguments(self, code_generator):
        """Test arguments containing special characters."""
        result = code_generator.generate_replacement_call(
            "query",
            ['f"SELECT * FROM {table}"', "**kwargs"],
            "python"
        )
        assert 'f"SELECT * FROM {table}"' in result
        assert "**kwargs" in result

    def test_argument_with_newlines(self, code_generator):
        """Test argument values containing newlines."""
        arg = '"""multiline\nstring"""'
        result = code_generator.generate_replacement_call("process", [arg], "python")
        assert '"""multiline\nstring"""' in result

    def test_very_long_argument_list(self, code_generator):
        """Test with very long argument list."""
        args = [f"arg{i}" for i in range(50)]
        result = code_generator.generate_replacement_call("func", args, "python")
        assert result.count(",") == 49  # 50 args = 49 commas

    def test_nested_function_calls_as_args(self, code_generator):
        """Test nested function calls as arguments."""
        result = code_generator.generate_replacement_call(
            "outer",
            ["inner1(a, b)", "inner2(c)"],
            "python"
        )
        assert result == "outer(inner1(a, b), inner2(c))"

    def test_case_sensitivity_in_language(self):
        """Test language parameter is case-insensitive in format_arguments_for_call."""
        params = [ParameterInfo("a"), ParameterInfo("b")]
        values = ["1", "2"]

        # Test uppercase
        result_upper = format_arguments_for_call(params, values, "PYTHON", "positional")
        result_lower = format_arguments_for_call(params, values, "python", "positional")

        assert result_upper == result_lower

    def test_whitespace_variations_in_original(self):
        """Test various whitespace patterns in original code."""
        test_cases = [
            ("    code", "call()"),           # 4 spaces
            ("\tcode", "call()"),             # 1 tab
            ("\t\t\tcode", "call()"),         # 3 tabs
            ("  \t  code", "call()"),         # mixed
        ]

        for original, replacement in test_cases:
            result = preserve_call_site_indentation(original, replacement)
            # Should have same leading whitespace as original
            orig_indent = original[:len(original) - len(original.lstrip())]
            assert result.startswith(orig_indent)
