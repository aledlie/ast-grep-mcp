"""Edge case tests to improve coverage for error handling paths"""

import json
import os
import subprocess
import sys
import tempfile
from unittest.mock import Mock, patch, MagicMock

import pytest

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# Mock FastMCP to disable decoration
class MockFastMCP:
    """Mock FastMCP that returns functions unchanged"""

    def __init__(self, name):
        self.name = name
        self.tools = {}

    def tool(self, **kwargs):
        """Decorator that returns the function unchanged"""
        def decorator(func):
            self.tools[func.__name__] = func
            return func
        return decorator

    def run(self, *args, **kwargs):
        """Mock run method"""
        pass


# Mock the mcp module before importing main
sys.modules['mcp'] = MagicMock()
sys.modules['mcp.server'] = MagicMock()
sys.modules['mcp.server.fastmcp'] = MagicMock()

# Replace FastMCP in the mcp module
with patch('mcp.server.fastmcp.FastMCP', MockFastMCP):
    import main


class TestConfigValidationErrorPaths:
    """Test configuration validation error handling with sys.exit."""

    def test_parse_args_with_invalid_config_flag(self):
        """Test that invalid config via --config flag triggers sys.exit."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("invalid: yaml: syntax: [}")
            invalid_config = f.name

        try:
            with patch('sys.argv', ['main.py', '--config', invalid_config]):
                with pytest.raises(SystemExit) as exc_info:
                    main.parse_args_and_get_config()
                assert exc_info.value.code == 1
        finally:
            os.unlink(invalid_config)

    def test_parse_args_with_invalid_config_env_var(self):
        """Test that invalid config via AST_GREP_CONFIG env var triggers sys.exit."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write("customLanguages:\n  - extensions: []\n")  # Invalid: empty extensions
            invalid_config = f.name

        try:
            with patch.dict(os.environ, {'AST_GREP_CONFIG': invalid_config}):
                with patch('sys.argv', ['main.py']):
                    with pytest.raises(SystemExit) as exc_info:
                        main.parse_args_and_get_config()
                    assert exc_info.value.code == 1
        finally:
            os.unlink(invalid_config)


class TestCacheEnvironmentVariables:
    """Test cache configuration via environment variables."""

    def test_cache_disabled_via_no_cache_flag(self):
        """Test CACHE_ENABLED set to False via --no-cache flag."""
        with patch('sys.argv', ['main.py', '--no-cache']):
            main.parse_args_and_get_config()
            assert main.CACHE_ENABLED is False

    def test_cache_disabled_via_env_var(self):
        """Test CACHE_ENABLED set to False via CACHE_DISABLED env var."""
        with patch.dict(os.environ, {'CACHE_DISABLED': '1'}):
            with patch('sys.argv', ['main.py']):
                main.parse_args_and_get_config()
                assert main.CACHE_ENABLED is False

    def test_cache_size_via_env_var(self):
        """Test CACHE_SIZE set via CACHE_SIZE env var."""
        with patch.dict(os.environ, {'CACHE_SIZE': '200'}):
            with patch('sys.argv', ['main.py']):
                main.parse_args_and_get_config()
                assert main.CACHE_SIZE == 200

    def test_cache_size_invalid_env_var(self):
        """Test CACHE_SIZE with invalid env var falls back to default."""
        with patch.dict(os.environ, {'CACHE_SIZE': 'invalid'}):
            with patch('sys.argv', ['main.py']):
                # Should print warning but not crash
                main.parse_args_and_get_config()
                assert main.CACHE_SIZE == 100  # Default

    def test_cache_ttl_via_env_var(self):
        """Test CACHE_TTL set via CACHE_TTL env var."""
        with patch.dict(os.environ, {'CACHE_TTL': '600'}):
            with patch('sys.argv', ['main.py']):
                main.parse_args_and_get_config()
                assert main.CACHE_TTL == 600

    def test_cache_ttl_invalid_env_var(self):
        """Test CACHE_TTL with invalid env var falls back to default."""
        with patch.dict(os.environ, {'CACHE_TTL': 'not-a-number'}):
            with patch('sys.argv', ['main.py']):
                # Should print warning but not crash
                main.parse_args_and_get_config()
                assert main.CACHE_TTL == 300  # Default

    def test_cache_none_when_disabled(self):
        """Test _query_cache is None when caching is disabled."""
        with patch('sys.argv', ['main.py', '--no-cache']):
            main.parse_args_and_get_config()
            assert main._query_cache is None


class TestDuplicationSizeRatioEdgeCase:
    """Test duplication detection size ratio filtering."""

    def test_group_duplicates_skips_different_sizes(self):
        """Test that matches with very different sizes are not compared."""
        # Create matches with very different sizes
        matches = [
            {
                "file": "test1.py",
                "text": "def small():\n    pass",
                "range": {"start": {"line": 1}, "end": {"line": 2}}
            },
            {
                "file": "test2.py",
                "text": "\n".join([f"    line {i}" for i in range(100)]),  # 100 lines
                "range": {"start": {"line": 1}, "end": {"line": 100}}
            }
        ]

        with patch('main.run_ast_grep') as mock_run:
            mock_run.return_value = (json.dumps(matches), "")
            groups = main.group_duplicates(matches, min_similarity=0.8)
            # Should not group these due to size difference
            assert len(groups) == 0


class TestJavaScriptValidation:
    """Test JavaScript/TypeScript syntax validation with node."""

    def test_validate_syntax_javascript_node_not_found(self):
        """Test JavaScript validation when node is not available."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write("const x = 1;")
            js_file = f.name

        try:
            with patch('subprocess.run', side_effect=FileNotFoundError("node not found")):
                result = main.validate_syntax(js_file, "javascript")
                # Should skip validation when node not available
                assert "Validation skipped" in result.get("error", "")
        finally:
            os.unlink(js_file)

    def test_validate_syntax_javascript_timeout(self):
        """Test JavaScript validation timeout."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write("const x = 1;")
            js_file = f.name

        try:
            with patch('subprocess.run', side_effect=subprocess.TimeoutExpired("node", 5)):
                result = main.validate_syntax(js_file, "javascript")
                # Should skip validation on timeout
                assert "Validation skipped" in result.get("error", "")
        finally:
            os.unlink(js_file)

    def test_validate_syntax_javascript_invalid_code(self):
        """Test JavaScript validation with invalid code."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write("const x = {")  # Unclosed brace
            js_file = f.name

        try:
            # Mock subprocess.run to simulate node detecting invalid syntax
            mock_result = Mock()
            mock_result.stdout = "INVALID: Unexpected end of input"
            mock_result.returncode = 0

            with patch('subprocess.run', return_value=mock_result):
                result = main.validate_syntax(js_file, "javascript")
                assert result["valid"] is False
                assert "Unexpected end of input" in result["error"]
        finally:
            os.unlink(js_file)


class TestSchemaOrgClientEdgeCases:
    """Test Schema.org client error handling."""

    def setup_method(self):
        """Reset schema client before each test."""
        main._schema_org_client = None

    def test_schema_org_client_http_error_fallback(self):
        """Test Schema.org client handles HTTP errors gracefully."""
        with patch('httpx.get') as mock_get:
            mock_get.side_effect = Exception("Network error")

            # get_schema_org_client should handle the error
            client = main.get_schema_org_client()

            # Client should still be created but with empty data
            assert client is not None

    def test_schema_org_client_empty_graph(self):
        """Test Schema.org client with no @graph in response."""
        mock_response = Mock()
        mock_response.json.return_value = {}  # No @graph
        mock_response.raise_for_status = Mock()

        with patch('httpx.get', return_value=mock_response):
            client = main.get_schema_org_client()
            assert client is not None


class TestRewriteBackupEdgeCases:
    """Test edge cases in rewrite and backup functionality."""

    def setup_method(self):
        """Create temp directory for tests."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up temp directory."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_create_backup_nonexistent_file(self):
        """Test create_backup skips nonexistent files."""
        nonexistent = os.path.join(self.temp_dir, "nonexistent.py")

        backup_id = main.create_backup([nonexistent], self.temp_dir)

        # Backup should be created but file list should be empty
        backup_dir = os.path.join(self.temp_dir, ".ast-grep-backups", backup_id)
        assert os.path.exists(backup_dir)

        # Check metadata (note: backup-metadata.json is the correct filename)
        metadata_file = os.path.join(backup_dir, "backup-metadata.json")
        with open(metadata_file) as f:
            metadata = json.load(f)
        assert len(metadata["files"]) == 0


class TestCommandNotFoundLogging:
    """Test command not found error paths."""

    def test_run_ast_grep_command_not_found(self):
        """Test run_ast_grep logs when ast-grep not found."""
        with patch('subprocess.run', side_effect=FileNotFoundError("ast-grep not found")):
            with pytest.raises(main.AstGrepNotFoundError):
                main.run_ast_grep("run", ["--pattern", "test"])


class TestStreamingSubprocessCleanup:
    """Test subprocess cleanup in streaming mode."""

    def test_stream_results_early_termination_logging(self):
        """Test that early termination is logged properly."""
        # Create a mock process that yields results
        mock_process = Mock()
        mock_process.stdout = [
            '{"file": "test.py", "text": "match1"}',
            '{"file": "test.py", "text": "match2"}',
            '{"file": "test.py", "text": "match3"}'
        ]
        mock_process.poll.return_value = None
        mock_process.returncode = 0  # Success after early termination
        mock_stderr = Mock()
        mock_stderr.read.return_value = ""
        mock_process.stderr = mock_stderr
        mock_process.wait.return_value = 0

        with patch('subprocess.Popen', return_value=mock_process):
            results = list(main.stream_ast_grep_results("run", ["--pattern", "test"], max_results=2))

            # Should only get 2 results due to early termination
            assert len(results) == 2

            # Process should be terminated (may be called multiple times)
            assert mock_process.terminate.called
            assert mock_process.wait.called


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
