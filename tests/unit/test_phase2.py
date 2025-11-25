"""Comprehensive test suite for Phase 2: Performance & Scalability features

This test suite covers:
- Task 6: Result Streaming (early termination, subprocess cleanup, JSON parsing)
- Task 8: Parallel Execution (workers parameter, --threads flag)
- Task 9: Large File Handling (file size filtering, max_file_size_mb)

Note: Task 7 (Caching) is tested in test_cache.py
Note: Task 10 (Benchmarking) is tested in test_benchmark.py
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

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
from ast_grep_mcp.core.cache import QueryCache
from ast_grep_mcp.core.executor import stream_ast_grep_results
from main import filter_files_by_size


# ============================================================================
# Task 6: Result Streaming Tests
# ============================================================================

class TestResultStreaming:
    """Test streaming result parsing and early termination"""

    @patch("subprocess.Popen")
    def test_stream_basic_json_parsing(self, mock_popen: Any) -> None:
        """Test basic JSON Lines parsing from subprocess"""
        # Mock subprocess that outputs JSON Lines
        mock_process = MagicMock()
        mock_process.stdout = [
            b'{"text": "match1", "file": "test.py", "range": {"start": {"line": 1}}}\n',
            b'{"text": "match2", "file": "test.py", "range": {"start": {"line": 2}}}\n',
        ]
        mock_process.poll.return_value = None
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        # Stream results (no project_folder argument - it's in the args)
        results = list(stream_ast_grep_results("run", ["--pattern", "test", "/project"]))

        assert len(results) == 2
        assert results[0]["text"] == "match1"
        assert results[1]["text"] == "match2"

    @patch("subprocess.Popen")
    def test_stream_early_termination(self, mock_popen: Any) -> None:
        """Test that streaming stops after max_results is reached"""
        # Mock subprocess that outputs many matches
        mock_process = MagicMock()
        mock_process.stdout = [
            b'{"text": "match1", "file": "test.py", "range": {"start": {"line": 1}}}\n',
            b'{"text": "match2", "file": "test.py", "range": {"start": {"line": 2}}}\n',
            b'{"text": "match3", "file": "test.py", "range": {"start": {"line": 3}}}\n',
            b'{"text": "match4", "file": "test.py", "range": {"start": {"line": 4}}}\n',
            b'{"text": "match5", "file": "test.py", "range": {"start": {"line": 5}}}\n',
        ]
        mock_process.poll.return_value = None
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        # Stream with max_results=2
        results = list(stream_ast_grep_results(
            "run", ["--pattern", "test", "/project"], max_results=2
        ))

        # Should only get 2 results
        assert len(results) == 2
        assert results[0]["text"] == "match1"
        assert results[1]["text"] == "match2"

        # Verify subprocess was terminated
        assert mock_process.terminate.called or mock_process.kill.called

    @patch("subprocess.Popen")
    def test_stream_subprocess_cleanup_sigterm(self, mock_popen: Any) -> None:
        """Test graceful subprocess cleanup with SIGTERM"""
        mock_process = MagicMock()
        mock_process.stdout = [
            b'{"text": "match1", "file": "test.py", "range": {"start": {"line": 1}}}\n',
        ]
        mock_process.poll.side_effect = [None, 0]  # First poll: running, second: terminated
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        # Stream with max_results=1
        results = list(stream_ast_grep_results(
            "run", ["--pattern", "test", "/project"], max_results=1
        ))

        assert len(results) == 1
        # Should attempt terminate first
        assert mock_process.terminate.called

    @patch("subprocess.Popen")
    @patch("time.sleep")  # Mock sleep to speed up test
    def test_stream_subprocess_cleanup_sigkill(self, mock_sleep: Any, mock_popen: Any) -> None:
        """Test subprocess cleanup attempts terminate and optionally kill"""
        mock_process = MagicMock()
        mock_process.stdout = [
            b'{"text": "match1", "file": "test.py", "range": {"start": {"line": 1}}}\n',
        ]
        # Process terminates eventually
        mock_process.poll.side_effect = [None, 0]  # Running, then terminated
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        # Stream with max_results=1
        results = list(stream_ast_grep_results(
            "run", ["--pattern", "test", "/project"], max_results=1
        ))

        assert len(results) == 1
        # Should attempt terminate (kill may or may not be called depending on how fast process terminates)
        assert mock_process.terminate.called

    @patch("subprocess.Popen")
    def test_stream_invalid_json_line_handling(self, mock_popen: Any) -> None:
        """Test handling of invalid JSON lines during streaming"""
        mock_process = MagicMock()
        mock_process.stdout = [
            b'{"text": "match1", "file": "test.py", "range": {"start": {"line": 1}}}\n',
            b'invalid json line\n',  # Invalid JSON
            b'{"text": "match2", "file": "test.py", "range": {"start": {"line": 2}}}\n',
        ]
        mock_process.poll.return_value = None
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        # Should skip invalid JSON and continue
        results = list(stream_ast_grep_results("run", ["--pattern", "test", "/project"]))

        # Should get 2 valid results, skipping the invalid line
        assert len(results) == 2
        assert results[0]["text"] == "match1"
        assert results[1]["text"] == "match2"

    @patch("subprocess.Popen")
    def test_stream_empty_results(self, mock_popen: Any) -> None:
        """Test streaming with no matches"""
        mock_process = MagicMock()
        mock_process.stdout = []  # No output
        mock_process.poll.return_value = 0
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        results = list(stream_ast_grep_results("run", ["--pattern", "nonexistent", "/project"]))

        assert len(results) == 0

    @patch("subprocess.Popen")
    def test_stream_large_result_set(self, mock_popen: Any) -> None:
        """Test streaming handles large result sets efficiently"""
        # Generate 1000 mock matches
        mock_matches: List[Any] = [
            f'{{"text": "match{i}", "file": "test.py", "range": {{"start": {{"line": {i}}}}}}}\n'.encode()
            for i in range(1000)
        ]

        mock_process = MagicMock()
        mock_process.stdout = mock_matches
        mock_process.poll.return_value = None
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        # Stream all results
        results = list(stream_ast_grep_results("run", ["--pattern", "test", "/project"]))

        assert len(results) == 1000
        assert results[0]["text"] == "match0"
        assert results[999]["text"] == "match999"


# ============================================================================
# Task 8: Parallel Execution Tests
# ============================================================================

class TestParallelExecution:
    """Test parallel execution with workers parameter"""

    def setup_method(self) -> None:
        """Reset cache and register tools before each test"""
        main._query_cache = None
        main.CACHE_ENABLED = False
        main.register_mcp_tools()

    @patch("main.stream_ast_grep_results")
    def test_workers_parameter_default_auto(self, mock_stream: Any) -> None:
        """Test that workers=0 uses ast-grep's auto-detection (no --threads flag)"""
        mock_stream.return_value = iter([{"text": "match"}])

        find_code = main.mcp.tools.get("find_code")  # type: ignore
        find_code(
            project_folder="/project",
            pattern="test",
            language="python",
            workers=0,  # Default: auto
            output_format="json"
        )

        # Verify stream_ast_grep_results was called
        assert mock_stream.called
        call_args = mock_stream.call_args

        # The args should NOT include --threads flag
        args = call_args[0][1]  # Second positional arg is the args list
        assert "--threads" not in args

    @patch("main.stream_ast_grep_results")
    def test_workers_parameter_explicit_value(self, mock_stream: Any) -> None:
        """Test that workers>0 passes --threads flag to ast-grep"""
        mock_stream.return_value = iter([{"text": "match"}])

        find_code = main.mcp.tools.get("find_code")  # type: ignore
        find_code(
            project_folder="/project",
            pattern="test",
            language="python",
            workers=4,  # Use 4 threads
            output_format="json"
        )

        # Verify stream_ast_grep_results was called with --threads
        assert mock_stream.called
        call_args = mock_stream.call_args
        args = call_args[0][1]  # Second positional arg is the args list

        # Should include --threads 4
        assert "--threads" in args
        threads_index = args.index("--threads")
        assert args[threads_index + 1] == "4"

    @patch("main.stream_ast_grep_results")
    def test_workers_parameter_in_find_code_by_rule(self, mock_stream: Any) -> None:
        """Test workers parameter works in find_code_by_rule"""
        mock_stream.return_value = iter([{"text": "match"}])

        yaml_rule = """id: test
language: Python
rule:
  pattern: def $NAME"""

        find_code_by_rule = main.mcp.tools.get("find_code_by_rule")  # type: ignore
        find_code_by_rule(
            project_folder="/project",
            yaml_rule=yaml_rule,
            workers=8,  # Use 8 threads
            output_format="json"
        )

        # Verify --threads 8 was passed
        assert mock_stream.called
        call_args = mock_stream.call_args
        args = call_args[0][1]

        assert "--threads" in args
        threads_index = args.index("--threads")
        assert args[threads_index + 1] == "8"

    @patch("main.stream_ast_grep_results")
    def test_workers_with_other_parameters(self, mock_stream: Any) -> None:
        """Test workers parameter works alongside other parameters"""
        mock_stream.return_value = iter([{"text": "match"}])

        find_code = main.mcp.tools.get("find_code")  # type: ignore
        find_code(
            project_folder="/project",
            pattern="test",
            language="python",
            max_results=10,
            workers=4,
            output_format="json"
        )

        # Verify all parameters were passed correctly
        assert mock_stream.called
        call_args = mock_stream.call_args
        args = call_args[0][1]

        assert "--pattern" in args
        assert "test" in args
        assert "--lang" in args
        assert "python" in args
        assert "--threads" in args
        assert "4" in args


# ============================================================================
# Task 9: Large File Handling Tests
# ============================================================================

class TestLargeFileHandling:
    """Test file size filtering functionality"""

    def test_filter_files_by_size_basic(self) -> None:
        """Test basic file filtering by size"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files of different sizes
            small_file = Path(tmpdir) / "small.py"
            small_file.write_text("x = 1\n")  # < 1KB

            large_file = Path(tmpdir) / "large.py"
            large_file.write_text("x = 1\n" * 100000)  # > 100KB

            # Filter with 50KB limit
            files_to_search, skipped = filter_files_by_size(
                tmpdir,
                max_size_mb=0.05,  # type: ignore  # 50KB - testing fractional MB
                language="python"
            )

            # Small file should be included, large file skipped
            assert any("small.py" in f for f in files_to_search)
            assert any("large.py" in f for f in skipped)

    def test_filter_files_by_size_no_limit(self) -> None:
        """Test that None or 0 max_size_mb returns empty lists"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("x = 1\n")

            # No filtering when max_size_mb is None
            files_to_search, skipped = filter_files_by_size(tmpdir, max_size_mb=None)
            assert len(files_to_search) == 0
            assert len(skipped) == 0

            # No filtering when max_size_mb is 0
            files_to_search, skipped = filter_files_by_size(tmpdir, max_size_mb=0)
            assert len(files_to_search) == 0
            assert len(skipped) == 0

    def test_filter_files_by_size_language_filtering(self) -> None:
        """Test that language parameter filters file extensions"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files with different extensions
            py_file = Path(tmpdir) / "test.py"
            py_file.write_text("x = 1\n")

            js_file = Path(tmpdir) / "test.js"
            js_file.write_text("var x = 1;\n")

            txt_file = Path(tmpdir) / "test.txt"
            txt_file.write_text("hello\n")

            # Filter for Python files only
            files_to_search, skipped = filter_files_by_size(
                tmpdir,
                max_size_mb=1,
                language="python"
            )

            # Only .py file should be included
            assert any("test.py" in f for f in files_to_search)
            assert not any("test.js" in f for f in files_to_search)
            assert not any("test.txt" in f for f in files_to_search)

    def test_filter_files_by_size_excludes_common_dirs(self) -> None:
        """Test that common directories are excluded from filtering"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create file in excluded directory
            node_modules = Path(tmpdir) / "node_modules"
            node_modules.mkdir()
            excluded_file = node_modules / "test.py"
            excluded_file.write_text("x = 1\n")

            # Create file in normal directory
            normal_file = Path(tmpdir) / "test.py"
            normal_file.write_text("x = 1\n")

            files_to_search, skipped = filter_files_by_size(
                tmpdir,
                max_size_mb=1,
                language="python"
            )

            # node_modules file should be excluded
            assert not any("node_modules" in f for f in files_to_search)
            assert not any("node_modules" in f for f in skipped)

            # Normal file should be included
            assert any(f.endswith("test.py") and "node_modules" not in f for f in files_to_search)

    def test_filter_files_by_size_handles_os_errors(self) -> None:
        """Test that OSError on file stat doesn't crash filtering"""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.py"
            test_file.write_text("x = 1\n")

            with patch("os.path.getsize", side_effect=OSError("Permission denied")):
                # Should not raise exception
                files_to_search, skipped = filter_files_by_size(
                    tmpdir,
                    max_size_mb=1,
                    language="python"
                )

                # Should continue despite error
                assert isinstance(files_to_search, list)
                assert isinstance(skipped, list)

    @patch("main.filter_files_by_size")
    @patch("main.stream_ast_grep_results")
    def test_max_file_size_mb_integration_with_find_code(self, mock_stream: Any, mock_filter: Any) -> None:
        """Test max_file_size_mb parameter integrates with find_code"""
        # Mock filter to return some files
        mock_filter.return_value = (["/project/small.py"], ["/project/large.py"])
        mock_stream.return_value = iter([{"text": "match"}])

        main.register_mcp_tools()
        find_code = main.mcp.tools.get("find_code")  # type: ignore

        find_code(
            project_folder="/project",
            pattern="test",
            language="python",
            max_file_size_mb=10,  # 10MB limit
            output_format="json"
        )

        # Verify filter was called with correct keyword params
        mock_filter.assert_called_once_with("/project", max_size_mb=10, language="python")

        # Verify stream was called with filtered files
        assert mock_stream.called
        call_args = mock_stream.call_args
        args = call_args[0][1]  # Args list

        # Should include the file from filter
        assert "/project/small.py" in args

    @patch("main.filter_files_by_size")
    @patch("main.stream_ast_grep_results")
    def test_max_file_size_mb_integration_with_find_code_by_rule(self, mock_stream: Any, mock_filter: Any) -> None:
        """Test max_file_size_mb parameter integrates with find_code_by_rule"""
        mock_filter.return_value = (["/project/small.py"], ["/project/large.py"])
        mock_stream.return_value = iter([{"text": "match"}])

        yaml_rule = """id: test
language: Python
rule:
  pattern: def $NAME"""

        main.register_mcp_tools()
        find_code_by_rule = main.mcp.tools.get("find_code_by_rule")  # type: ignore

        find_code_by_rule(
            project_folder="/project",
            yaml_rule=yaml_rule,
            max_file_size_mb=5,  # 5MB limit
            output_format="json"
        )

        # Verify filter was called with keyword params (language extracted from YAML)
        assert mock_filter.called
        call_kwargs = mock_filter.call_args.kwargs
        assert call_kwargs["max_size_mb"] == 5

    @patch("main.filter_files_by_size")
    @patch("main.stream_ast_grep_results")
    def test_max_file_size_mb_zero_disables_filtering(self, mock_stream: Any, mock_filter: Any) -> None:
        """Test that max_file_size_mb=0 disables file filtering"""
        mock_stream.return_value = iter([{"text": "match"}])

        main.register_mcp_tools()
        find_code = main.mcp.tools.get("find_code")  # type: ignore

        find_code(
            project_folder="/project",
            pattern="test",
            max_file_size_mb=0,  # Disabled
            output_format="json"
        )

        # filter_files_by_size should still be called but return empty lists
        # which means no file filtering is applied
        assert mock_stream.called


# ============================================================================
# Integration Tests for Combined Phase 2 Features
# ============================================================================

class TestPhase2Integration:
    """Test multiple Phase 2 features working together"""

    def setup_method(self) -> None:
        """Reset state before each test"""
        main._query_cache = None
        main.CACHE_ENABLED = False
        main.register_mcp_tools()

    @patch("main.filter_files_by_size")
    @patch("main.stream_ast_grep_results")
    def test_streaming_with_file_filtering_and_parallel(self, mock_stream: Any, mock_filter: Any) -> None:
        """Test streaming + file filtering + parallel execution together"""
        mock_filter.return_value = (["/project/file1.py", "/project/file2.py"], ["/project/huge.py"])
        mock_stream.return_value = iter([
            {"text": "match1", "file": "/project/file1.py", "range": {"start": {"line": 1}}},
            {"text": "match2", "file": "/project/file2.py", "range": {"start": {"line": 1}}},
        ])

        find_code = main.mcp.tools.get("find_code")  # type: ignore

        result = find_code(
            project_folder="/project",
            pattern="test",
            language="python",
            max_results=10,  # Streaming with early termination
            max_file_size_mb=50,  # File filtering
            workers=4,  # Parallel execution
            output_format="json"
        )

        # Verify all features were used
        assert mock_filter.called
        assert mock_stream.called

        # Check that --threads was passed
        call_args = mock_stream.call_args
        args = call_args[0][1]
        assert "--threads" in args
        assert "4" in args

        # Check results
        assert len(result) == 2

    @patch("main.filter_files_by_size")
    @patch("main.stream_ast_grep_results")
    def test_all_phase2_features_with_caching(self, mock_stream: Any, mock_filter: Any) -> None:
        """Test all Phase 2 features together including caching"""
        # Enable caching
        main._query_cache = QueryCache(max_size=10, ttl_seconds=300)
        main.CACHE_ENABLED = True

        mock_filter.return_value = (["/project/file.py"], [])
        mock_stream.return_value = iter([{"text": "match"}])

        find_code = main.mcp.tools.get("find_code")  # type: ignore

        # First call - should execute
        result1 = find_code(
            project_folder="/project",
            pattern="test",
            language="python",
            max_results=5,
            max_file_size_mb=10,
            workers=2,
            output_format="json"
        )

        assert mock_stream.call_count == 1

        # Second call - should hit cache
        result2 = find_code(
            project_folder="/project",
            pattern="test",
            language="python",
            max_results=5,
            max_file_size_mb=10,
            workers=2,
            output_format="json"
        )

        # Should NOT call stream again (cache hit)
        assert mock_stream.call_count == 1
        assert result1 == result2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
