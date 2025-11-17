"""Unit tests for ast-grep MCP server"""

import json
import os
import subprocess
import sys
from unittest.mock import Mock, patch

import pytest

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# Mock FastMCP to disable decoration
class MockFastMCP:
    """Mock FastMCP that returns functions unchanged"""

    def __init__(self, name):
        self.name = name
        self.tools = {}  # Store registered tools

    def tool(self, **kwargs):
        """Decorator that returns the function unchanged"""

        def decorator(func):
            # Store the function for later retrieval
            self.tools[func.__name__] = func
            return func  # Return original function without modification

        return decorator

    def run(self, **kwargs):
        """Mock run method"""
        pass


# Mock the Field function to return the default value
def mock_field(**kwargs):
    return kwargs.get("default")


# Patch the imports before loading main
with patch("mcp.server.fastmcp.FastMCP", MockFastMCP):
    with patch("pydantic.Field", mock_field):
        import main
        from main import (
            format_matches_as_text,
            run_ast_grep,
            run_command,
        )

        # Call register_mcp_tools to define the tool functions
        main.register_mcp_tools()

        # Extract the tool functions from the mocked mcp instance
        dump_syntax_tree = main.mcp.tools.get("dump_syntax_tree")
        find_code = main.mcp.tools.get("find_code")
        find_code_by_rule = main.mcp.tools.get("find_code_by_rule")
        match_code_rule = main.mcp.tools.get("test_match_code_rule")


class TestDumpSyntaxTree:
    """Test the dump_syntax_tree function"""

    @patch("main.run_ast_grep")
    def test_dump_syntax_tree_cst(self, mock_run):
        """Test dumping CST format"""
        mock_result = Mock()
        mock_result.stderr = "ROOT@0..10"
        mock_run.return_value = mock_result

        result = dump_syntax_tree("const x = 1", "javascript", "cst")

        assert result == "ROOT@0..10"
        mock_run.assert_called_once_with(
            "run",
            ["--pattern", "const x = 1", "--lang", "javascript", "--debug-query=cst"],
        )

    @patch("main.run_ast_grep")
    def test_dump_syntax_tree_pattern(self, mock_run):
        """Test dumping pattern format"""
        mock_result = Mock()
        mock_result.stderr = "pattern_node"
        mock_run.return_value = mock_result

        result = dump_syntax_tree("$VAR", "python", "pattern")

        assert result == "pattern_node"
        mock_run.assert_called_once_with(
            "run", ["--pattern", "$VAR", "--lang", "python", "--debug-query=pattern"]
        )


class TestTestMatchCodeRule:
    """Test the test_match_code_rule function"""

    @patch("main.run_ast_grep")
    def test_match_found(self, mock_run):
        """Test when matches are found"""
        mock_result = Mock()
        mock_result.stdout = '[{"text": "def foo(): pass"}]'
        mock_run.return_value = mock_result

        yaml_rule = """id: test
language: python
rule:
  pattern: 'def $NAME(): $$$'
"""
        code = "def foo(): pass"

        result = match_code_rule(code, yaml_rule)

        assert result == [{"text": "def foo(): pass"}]
        mock_run.assert_called_once_with(
            "scan", ["--inline-rules", yaml_rule, "--json", "--stdin"], input_text=code
        )

    @patch("main.run_ast_grep")
    def test_no_match(self, mock_run):
        """Test when no matches are found"""
        mock_result = Mock()
        mock_result.stdout = "[]"
        mock_run.return_value = mock_result

        yaml_rule = """id: test
language: python
rule:
  pattern: 'class $NAME'
"""
        code = "def foo(): pass"

        with pytest.raises(main.NoMatchesError, match="No matches found"):
            match_code_rule(code, yaml_rule)


class TestFindCode:
    """Test the find_code function"""

    def setup_method(self):
        """Clear cache before each test to avoid test interference"""
        if main._query_cache is not None:
            main._query_cache.cache.clear()
            main._query_cache.hits = 0
            main._query_cache.misses = 0

    @patch("main.stream_ast_grep_results")
    def test_text_format_with_results(self, mock_stream):
        """Test text format output with results"""
        mock_matches = [
            {"text": "def foo():\n    pass", "file": "file.py",
             "range": {"start": {"line": 0}, "end": {"line": 1}}},
            {"text": "def bar():\n    return", "file": "file.py",
             "range": {"start": {"line": 4}, "end": {"line": 5}}}
        ]
        mock_stream.return_value = iter(mock_matches)

        result = find_code(
            project_folder="/test/path",
            pattern="def $NAME():",
            language="python",
            output_format="text",
        )

        assert "Found 2 matches:" in result
        assert "def foo():" in result
        assert "def bar():" in result
        assert "file.py:1-2" in result
        assert "file.py:5-6" in result
        mock_stream.assert_called_once_with(
            "run", ["--pattern", "def $NAME():", "--lang", "python", "--json=stream", "/test/path"],
            max_results=0, progress_interval=100
        )

    @patch("main.stream_ast_grep_results")
    def test_text_format_no_results(self, mock_stream):
        """Test text format output with no results"""
        mock_stream.return_value = iter([])

        result = find_code(
            project_folder="/test/path", pattern="nonexistent", output_format="text"
        )

        assert result == "No matches found"
        mock_stream.assert_called_once_with(
            "run", ["--pattern", "nonexistent", "--json=stream", "/test/path"],
            max_results=0, progress_interval=100
        )

    @patch("main.stream_ast_grep_results")
    def test_text_format_with_max_results(self, mock_stream):
        """Test text format with max_results limit"""
        # Only return 2 matches since streaming stops early
        mock_matches = [
            {"text": "match1", "file": "f.py", "range": {"start": {"line": 0}, "end": {"line": 0}}},
            {"text": "match2", "file": "f.py", "range": {"start": {"line": 1}, "end": {"line": 1}}},
        ]
        mock_stream.return_value = iter(mock_matches)

        result = find_code(
            project_folder="/test/path",
            pattern="pattern",
            max_results=2,
            output_format="text",
        )

        assert "Found 2 matches:" in result
        assert "match1" in result
        assert "match2" in result

    @patch("main.stream_ast_grep_results")
    def test_json_format(self, mock_stream):
        """Test JSON format output"""
        mock_matches = [
            {"text": "def foo():", "file": "test.py"},
            {"text": "def bar():", "file": "test.py"},
        ]
        mock_stream.return_value = iter(mock_matches)

        result = find_code(
            project_folder="/test/path", pattern="def $NAME():", output_format="json"
        )

        assert result == mock_matches
        mock_stream.assert_called_once_with(
            "run", ["--pattern", "def $NAME():", "--json=stream", "/test/path"],
            max_results=0, progress_interval=100
        )

    @patch("main.stream_ast_grep_results")
    def test_json_format_with_max_results(self, mock_stream):
        """Test JSON format with max_results limit"""
        # Only return 2 matches since streaming stops early
        mock_matches = [{"text": "match1"}, {"text": "match2"}]
        mock_stream.return_value = iter(mock_matches)

        result = find_code(
            project_folder="/test/path",
            pattern="pattern",
            max_results=2,
            output_format="json",
        )

        assert len(result) == 2
        assert result[0]["text"] == "match1"
        assert result[1]["text"] == "match2"

    def test_invalid_output_format(self):
        """Test with invalid output format"""
        with pytest.raises(ValueError, match="Invalid output_format"):
            find_code(
                project_folder="/test/path", pattern="pattern", output_format="invalid"
            )


class TestFindCodeByRule:
    """Test the find_code_by_rule function"""

    def setup_method(self):
        """Clear cache before each test to avoid test interference"""
        if main._query_cache is not None:
            main._query_cache.cache.clear()
            main._query_cache.hits = 0
            main._query_cache.misses = 0

    @patch("main.stream_ast_grep_results")
    def test_text_format_with_results(self, mock_stream):
        """Test text format output with results"""
        mock_matches = [
            {"text": "class Foo:\n    pass", "file": "file.py",
             "range": {"start": {"line": 0}, "end": {"line": 1}}},
            {"text": "class Bar:\n    pass", "file": "file.py",
             "range": {"start": {"line": 9}, "end": {"line": 10}}}
        ]
        mock_stream.return_value = iter(mock_matches)

        yaml_rule = """id: test
language: python
rule:
  pattern: 'class $NAME'
"""

        result = find_code_by_rule(
            project_folder="/test/path", yaml_rule=yaml_rule, output_format="text"
        )

        assert "Found 2 matches:" in result
        assert "class Foo:" in result
        assert "class Bar:" in result
        assert "file.py:1-2" in result
        assert "file.py:10-11" in result
        mock_stream.assert_called_once_with(
            "scan", ["--inline-rules", yaml_rule, "--json=stream", "/test/path"],
            max_results=0, progress_interval=100
        )

    @patch("main.stream_ast_grep_results")
    def test_json_format(self, mock_stream):
        """Test JSON format output"""
        mock_matches = [{"text": "class Foo:", "file": "test.py"}]
        mock_stream.return_value = iter(mock_matches)

        yaml_rule = """id: test
language: python
rule:
  pattern: 'class $NAME'
"""

        result = find_code_by_rule(
            project_folder="/test/path", yaml_rule=yaml_rule, output_format="json"
        )

        assert result == mock_matches
        mock_stream.assert_called_once_with(
            "scan", ["--inline-rules", yaml_rule, "--json=stream", "/test/path"],
            max_results=0, progress_interval=100
        )


class TestRunCommand:
    """Test the run_command function"""

    @patch("subprocess.run")
    def test_successful_command(self, mock_run):
        """Test successful command execution"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "output"
        mock_run.return_value = mock_result

        result = run_command(["echo", "test"])

        assert result.stdout == "output"
        mock_run.assert_called_once_with(
            ["echo", "test"], capture_output=True, input=None, text=True, check=True, shell=False
        )

    @patch("subprocess.run")
    def test_command_failure(self, mock_run):
        """Test command execution failure"""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["false"], stderr="error message"
        )

        with pytest.raises(main.AstGrepExecutionError, match="failed with exit code 1"):
            run_command(["false"])

    @patch("subprocess.run")
    def test_command_not_found(self, mock_run):
        """Test when command is not found"""
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(main.AstGrepNotFoundError, match="not found"):
            run_command(["nonexistent"])


class TestFormatMatchesAsText:
    """Test the format_matches_as_text helper function"""

    def test_empty_matches(self):
        """Test with empty matches list"""
        result = format_matches_as_text([])
        assert result == ""

    def test_single_line_match(self):
        """Test formatting a single-line match"""
        matches = [
            {
                "text": "const x = 1",
                "file": "test.js",
                "range": {"start": {"line": 4}, "end": {"line": 4}}
            }
        ]
        result = format_matches_as_text(matches)
        assert result == "test.js:5\nconst x = 1"

    def test_multi_line_match(self):
        """Test formatting a multi-line match"""
        matches = [
            {
                "text": "def foo():\n    return 42",
                "file": "test.py",
                "range": {"start": {"line": 9}, "end": {"line": 10}}
            }
        ]
        result = format_matches_as_text(matches)
        assert result == "test.py:10-11\ndef foo():\n    return 42"

    def test_multiple_matches(self):
        """Test formatting multiple matches"""
        matches = [
            {
                "text": "match1",
                "file": "file1.py",
                "range": {"start": {"line": 0}, "end": {"line": 0}}
            },
            {
                "text": "match2\nline2",
                "file": "file2.py",
                "range": {"start": {"line": 5}, "end": {"line": 6}}
            }
        ]
        result = format_matches_as_text(matches)
        expected = "file1.py:1\nmatch1\n\nfile2.py:6-7\nmatch2\nline2"
        assert result == expected


class TestRunAstGrep:
    """Test the run_ast_grep function"""

    @patch("main.run_command")
    @patch("main.CONFIG_PATH", None)
    def test_without_config(self, mock_run):
        """Test running ast-grep without config"""
        mock_result = Mock()
        mock_run.return_value = mock_result

        result = run_ast_grep("run", ["--pattern", "test"])

        assert result == mock_result
        mock_run.assert_called_once_with(["ast-grep", "run", "--pattern", "test"], None)

    @patch("main.run_command")
    @patch("main.CONFIG_PATH", "/path/to/config.yaml")
    def test_with_config(self, mock_run):
        """Test running ast-grep with config"""
        mock_result = Mock()
        mock_run.return_value = mock_result

        result = run_ast_grep("scan", ["--inline-rules", "rule"])

        assert result == mock_result
        mock_run.assert_called_once_with(
            [
                "ast-grep",
                "scan",
                "--config",
                "/path/to/config.yaml",
                "--inline-rules",
                "rule",
            ],
            None,
        )


class TestConfigValidation:
    """Test the validate_config_file function"""

    def test_valid_config(self):
        """Test validating a valid config file"""
        from main import validate_config_file
        fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
        config_path = os.path.join(fixtures_dir, "valid_config.yaml")

        # Should not raise an exception
        config = validate_config_file(config_path)
        assert config is not None
        assert config.ruleDirs == ["rules", "custom-rules"]
        assert config.testDirs == ["tests"]
        assert "mylang" in config.customLanguages
        assert ".ml" in config.customLanguages["mylang"].extensions

    def test_invalid_config_extensions(self):
        """Test config with invalid extensions (missing dots)"""
        from main import validate_config_file, ConfigurationError
        fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
        config_path = os.path.join(fixtures_dir, "invalid_config_extensions.yaml")

        with pytest.raises(ConfigurationError, match="must start with a dot"):
            validate_config_file(config_path)

    def test_invalid_config_empty_lists(self):
        """Test config with empty lists"""
        from main import validate_config_file, ConfigurationError
        fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
        config_path = os.path.join(fixtures_dir, "invalid_config_empty.yaml")

        with pytest.raises(ConfigurationError, match="cannot be empty"):
            validate_config_file(config_path)

    def test_config_file_not_found(self):
        """Test with non-existent config file"""
        from main import validate_config_file, ConfigurationError

        with pytest.raises(ConfigurationError, match="does not exist"):
            validate_config_file("/nonexistent/path/to/config.yaml")

    def test_config_file_is_directory(self):
        """Test with directory instead of file"""
        from main import validate_config_file, ConfigurationError
        fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")

        with pytest.raises(ConfigurationError, match="not a file"):
            validate_config_file(fixtures_dir)

    def test_config_yaml_parsing_error(self):
        """Test config with YAML syntax error"""
        from main import validate_config_file, ConfigurationError
        fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
        config_path = os.path.join(fixtures_dir, "invalid_config_yaml_error.yaml")

        with pytest.raises(ConfigurationError, match="YAML parsing failed"):
            validate_config_file(config_path)

    def test_config_empty_file(self):
        """Test config with empty file"""
        from main import validate_config_file, ConfigurationError
        fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
        config_path = os.path.join(fixtures_dir, "empty_config.yaml")

        with pytest.raises(ConfigurationError, match="empty"):
            validate_config_file(config_path)

    def test_config_not_dictionary(self):
        """Test config that is not a dictionary"""
        from main import validate_config_file, ConfigurationError
        fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
        config_path = os.path.join(fixtures_dir, "invalid_config_not_dict.yaml")

        with pytest.raises(ConfigurationError, match="must be a YAML dictionary"):
            validate_config_file(config_path)


class TestGetSupportedLanguages:
    """Test the get_supported_languages function"""

    @patch("main.CONFIG_PATH", None)
    def test_without_config(self):
        """Test getting languages without config file"""
        from main import get_supported_languages

        languages = get_supported_languages()

        # Should have all built-in languages
        assert "python" in languages
        assert "javascript" in languages
        assert "rust" in languages
        assert len(languages) >= 24  # At least 24 built-in languages

    @patch("main.CONFIG_PATH")
    def test_with_custom_languages(self, mock_config_path):
        """Test getting languages with custom languages in config"""
        from main import get_supported_languages

        fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
        config_path = os.path.join(fixtures_dir, "config_with_custom_lang.yaml")
        mock_config_path.__bool__ = lambda x: True
        mock_config_path.__str__ = lambda x: config_path

        # Mock os.path.exists to return True for the config path
        with patch("os.path.exists", return_value=True):
            # Re-import to get fresh module state
            import importlib
            import main
            importlib.reload(main)

            # Set CONFIG_PATH
            main.CONFIG_PATH = config_path

            languages = main.get_supported_languages()

            # Should have built-in plus custom languages
            assert "python" in languages
            assert "customlang1" in languages
            assert "customlang2" in languages

    @patch("main.CONFIG_PATH", "/nonexistent/path.yaml")
    @patch("os.path.exists", return_value=False)
    def test_with_nonexistent_config(self, mock_exists):
        """Test with config path that doesn't exist"""
        from main import get_supported_languages

        languages = get_supported_languages()

        # Should still return built-in languages
        assert "python" in languages
        assert len(languages) >= 24

    @patch("main.CONFIG_PATH")
    def test_with_config_exception(self, mock_config_path):
        """Test when config file reading raises exception"""
        from main import get_supported_languages

        mock_config_path.__bool__ = lambda x: True
        mock_config_path.__str__ = lambda x: "/some/path.yaml"

        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", side_effect=OSError("Permission denied")):
                languages = get_supported_languages()

                # Should gracefully handle exception and return built-in languages
                assert "python" in languages
                assert len(languages) >= 24


class TestCustomLanguageConfig:
    """Test CustomLanguageConfig Pydantic model"""

    def test_empty_extensions_list(self):
        """Test that empty extensions list raises error"""
        from main import CustomLanguageConfig
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="extensions list cannot be empty"):
            CustomLanguageConfig(extensions=[])

    def test_valid_extensions(self):
        """Test valid extensions"""
        from main import CustomLanguageConfig

        config = CustomLanguageConfig(
            extensions=[".ml", ".mli"],
            languageId="mylang"
        )
        assert config.extensions == [".ml", ".mli"]
        assert config.languageId == "mylang"


class TestFormatMatchesEdgeCases:
    """Test edge cases for format_matches_as_text"""

    def test_missing_file_field(self):
        """Test match with missing file field"""
        from main import format_matches_as_text

        matches = [{
            "range": {"start": {"line": 0}, "end": {"line": 0}},
            "text": "test"
        }]
        result = format_matches_as_text(matches)
        assert ":1\ntest" in result

    def test_missing_range_field(self):
        """Test match with missing range field"""
        from main import format_matches_as_text

        matches = [{
            "file": "test.py",
            "text": "test"
        }]
        result = format_matches_as_text(matches)
        assert "test.py:1\ntest" in result

    def test_missing_text_field(self):
        """Test match with missing text field"""
        from main import format_matches_as_text

        matches = [{
            "file": "test.py",
            "range": {"start": {"line": 5}, "end": {"line": 5}}
        }]
        result = format_matches_as_text(matches)
        assert "test.py:6" in result


class TestFindCodeEdgeCases:
    """Test edge cases for find_code function"""

    @patch("main.stream_ast_grep_results")
    def test_find_code_with_language(self, mock_stream):
        """Test find_code with language specified"""
        mock_stream.return_value = iter([])

        result = find_code(
            project_folder="/test",
            pattern="test",
            language="python",
            output_format="text"
        )

        assert result == "No matches found"
        # Verify --lang flag was passed
        call_args = mock_stream.call_args[0][1]
        assert "--lang" in call_args
        assert "python" in call_args

    @patch("main.stream_ast_grep_results")
    def test_find_code_without_language(self, mock_stream):
        """Test find_code without language (auto-detect)"""
        mock_matches = [{
            "file": "test.py",
            "range": {"start": {"line": 0}, "end": {"line": 0}},
            "text": "test"
        }]
        mock_stream.return_value = iter(mock_matches)

        result = find_code(
            project_folder="/test",
            pattern="test",
            language="",
            output_format="json"
        )

        # Should return results
        assert len(result) == 1
        # Verify --lang flag was NOT passed
        call_args = mock_stream.call_args[0][1]
        assert "--lang" not in call_args


class TestFindCodeByRuleEdgeCases:
    """Test edge cases for find_code_by_rule function"""

    @patch("main.stream_ast_grep_results")
    def test_find_code_by_rule_no_results_text(self, mock_stream):
        """Test find_code_by_rule with no results in text format"""
        mock_stream.return_value = iter([])

        yaml_rule = """
id: test
language: python
rule:
  pattern: test
"""
        result = find_code_by_rule(
            project_folder="/test",
            yaml_rule=yaml_rule,
            output_format="text"
        )

        assert result == "No matches found"

    @patch("main.run_ast_grep")
    def test_find_code_by_rule_invalid_yaml_syntax(self, mock_run):
        """Test find_code_by_rule with invalid YAML syntax"""
        from main import InvalidYAMLError

        # Invalid YAML with unclosed quote
        yaml_rule = 'id: "test\nlanguage: python'

        with pytest.raises(InvalidYAMLError, match="YAML parsing failed"):
            find_code_by_rule(
                project_folder="/test",
                yaml_rule=yaml_rule,
                output_format="text"
            )

    @patch("main.run_ast_grep")
    def test_find_code_by_rule_invalid_output_format(self, mock_run):
        """Test find_code_by_rule with invalid output format"""

        yaml_rule = """
id: test
language: python
rule:
  pattern: test
"""
        with pytest.raises(ValueError, match="Invalid output_format"):
            find_code_by_rule(
                project_folder="/test",
                yaml_rule=yaml_rule,
                output_format="invalid"
            )

    @patch("main.run_ast_grep")
    def test_find_code_by_rule_yaml_not_dict(self, mock_run):
        """Test find_code_by_rule with YAML that's not a dict"""
        from main import InvalidYAMLError

        yaml_rule = "- list\n- of\n- items"

        with pytest.raises(InvalidYAMLError, match="must be a dictionary"):
            find_code_by_rule(
                project_folder="/test",
                yaml_rule=yaml_rule,
                output_format="text"
            )

    @patch("main.run_ast_grep")
    def test_find_code_by_rule_missing_id(self, mock_run):
        """Test find_code_by_rule missing id field"""
        from main import InvalidYAMLError

        yaml_rule = """
language: python
rule:
  pattern: test
"""
        with pytest.raises(InvalidYAMLError, match="Missing required field 'id'"):
            find_code_by_rule(
                project_folder="/test",
                yaml_rule=yaml_rule,
                output_format="text"
            )

    @patch("main.run_ast_grep")
    def test_find_code_by_rule_missing_language(self, mock_run):
        """Test find_code_by_rule missing language field"""
        from main import InvalidYAMLError

        yaml_rule = """
id: test
rule:
  pattern: test
"""
        with pytest.raises(InvalidYAMLError, match="Missing required field 'language'"):
            find_code_by_rule(
                project_folder="/test",
                yaml_rule=yaml_rule,
                output_format="text"
            )

    @patch("main.run_ast_grep")
    def test_find_code_by_rule_missing_rule(self, mock_run):
        """Test find_code_by_rule missing rule field"""
        from main import InvalidYAMLError

        yaml_rule = """
id: test
language: python
"""
        with pytest.raises(InvalidYAMLError, match="Missing required field 'rule'"):
            find_code_by_rule(
                project_folder="/test",
                yaml_rule=yaml_rule,
                output_format="text"
            )

    @patch("main.stream_ast_grep_results")
    def test_find_code_by_rule_with_max_results(self, mock_stream):
        """Test find_code_by_rule with max_results limiting"""
        # Only return 3 matches since streaming stops early
        mock_matches = [
            {
                "file": f"test{i}.py",
                "range": {"start": {"line": i}, "end": {"line": i}},
                "text": f"match{i}"
            }
            for i in range(3)
        ]
        mock_stream.return_value = iter(mock_matches)

        yaml_rule = """
id: test
language: python
rule:
  pattern: test
"""
        result = find_code_by_rule(
            project_folder="/test",
            yaml_rule=yaml_rule,
            max_results=3,
            output_format="text"
        )

        # Should show 3 matches
        assert "Found 3 matches" in result
        assert "test0.py" in result
        assert "test2.py" in result


class TestValidateConfigFileErrors:
    """Test error paths in validate_config_file"""

    def test_config_file_read_error(self):
        """Test when file cannot be read (OSError)"""
        from main import validate_config_file, ConfigurationError
        fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
        config_path = os.path.join(fixtures_dir, "valid_config.yaml")

        with patch("builtins.open", side_effect=OSError("Permission denied")):
            with pytest.raises(ConfigurationError, match="Failed to read file"):
                validate_config_file(config_path)


class TestYAMLValidation:
    """Test YAML validation in tools"""

    @patch("main.run_ast_grep")
    def test_invalid_yaml_structure(self, mock_run):
        """Test with invalid YAML structure (not a dict)"""
        from main import InvalidYAMLError

        yaml_rule = "- this is a list"

        with pytest.raises(InvalidYAMLError, match="must be a dictionary"):
            match_code_rule("test code", yaml_rule)

    @patch("main.run_ast_grep")
    def test_missing_id_field(self, mock_run):
        """Test YAML missing id field"""
        from main import InvalidYAMLError

        yaml_rule = """
language: python
rule:
  pattern: test
"""
        with pytest.raises(InvalidYAMLError, match="Missing required field 'id'"):
            match_code_rule("test code", yaml_rule)

    @patch("main.run_ast_grep")
    def test_missing_language_field(self, mock_run):
        """Test YAML missing language field"""
        from main import InvalidYAMLError

        yaml_rule = """
id: test
rule:
  pattern: test
"""
        with pytest.raises(InvalidYAMLError, match="Missing required field 'language'"):
            match_code_rule("test code", yaml_rule)

    @patch("main.run_ast_grep")
    def test_missing_rule_field(self, mock_run):
        """Test YAML missing rule field"""
        from main import InvalidYAMLError

        yaml_rule = """
id: test
language: python
"""
        with pytest.raises(InvalidYAMLError, match="Missing required field 'rule'"):
            match_code_rule("test code", yaml_rule)

    @patch("main.run_ast_grep")
    def test_yaml_syntax_error_in_test_match(self, mock_run):
        """Test YAML syntax error in test_match_code_rule"""
        from main import InvalidYAMLError

        # Invalid YAML with syntax error
        yaml_rule = 'id: "unclosed\nlanguage: python'

        with pytest.raises(InvalidYAMLError, match="YAML parsing failed"):
            match_code_rule("test code", yaml_rule)


class TestParseArgsAndGetConfig:
    """Test parse_args_and_get_config function"""

    @patch('sys.argv', ['main.py'])
    @patch('main.CONFIG_PATH', None)
    def test_no_config_provided(self):
        """Test when no config is provided"""
        import importlib
        import main

        # Reload to reset CONFIG_PATH
        importlib.reload(main)

        # Should not raise any errors
        main.parse_args_and_get_config()
        assert main.CONFIG_PATH is None

    @patch('sys.argv', ['main.py', '--config', 'tests/fixtures/valid_config.yaml'])
    def test_with_valid_config_flag(self):
        """Test with valid --config flag"""
        import importlib
        import main

        importlib.reload(main)
        fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
        config_path = os.path.join(fixtures_dir, "valid_config.yaml")

        with patch('sys.argv', ['main.py', '--config', config_path]):
            main.parse_args_and_get_config()
            assert main.CONFIG_PATH == config_path

    @patch('os.environ.get')
    @patch('sys.argv', ['main.py'])
    def test_with_env_var_config(self, mock_env_get):
        """Test with AST_GREP_CONFIG environment variable"""
        import importlib
        import main

        fixtures_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures")
        config_path = os.path.join(fixtures_dir, "valid_config.yaml")

        # Mock environment variable
        def env_side_effect(key, default=None):
            if key == 'AST_GREP_CONFIG':
                return config_path
            return default

        mock_env_get.side_effect = env_side_effect

        importlib.reload(main)
        main.parse_args_and_get_config()
        assert main.CONFIG_PATH == config_path


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
