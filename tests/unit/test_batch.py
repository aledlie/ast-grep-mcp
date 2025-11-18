"""Unit tests for batch search operations (Task 15).

Tests cover:
- batch_search tool basic functionality
- Parallel execution of multiple queries
- Result aggregation and deduplication
- Conditional execution (if_matches, if_no_matches)
- Error handling in batch operations
"""

import os
import sys
import tempfile
from unittest.mock import Mock, patch

import pytest

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# Mock FastMCP before importing main
class MockFastMCP:
    def __init__(self, name):
        self.name = name
        self.tools = {}

    def tool(self, **kwargs):
        def decorator(func):
            self.tools[func.__name__] = func
            return func
        return decorator

    def run(self, **kwargs):
        pass


def mock_field(**kwargs):
    return kwargs.get("default")


# Import with mocked decorators
with patch("mcp.server.fastmcp.FastMCP", MockFastMCP):
    with patch("pydantic.Field", mock_field):
        import main

        # Call register_mcp_tools to define the tool functions
        main.register_mcp_tools()


class TestBatchSearchBasic:
    """Basic tests for batch_search tool."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.project_folder = self.temp_dir

        # Get tool function
        self.batch_search = main.mcp.tools.get("batch_search")
        assert self.batch_search is not None, "batch_search tool not registered"

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_batch_search_tool_registered(self) -> None:
        """Test that batch_search tool is registered."""
        assert "batch_search" in main.mcp.tools
        assert callable(main.mcp.tools["batch_search"])

    @patch("main.stream_ast_grep_results")
    def test_batch_search_single_query(self, mock_stream: Mock) -> None:
        """Test batch_search with a single pattern query."""
        # stream_ast_grep_results returns an iterator of match dicts
        mock_stream.return_value = iter([
            {"file": "test.py", "text": "match1", "range": {"start": {"line": 1}}}
        ])

        queries = [
            {
                "id": "query1",
                "type": "pattern",
                "pattern": "def $FUNC",
                "language": "python"
            }
        ]

        result = self.batch_search(
            project_folder=self.project_folder,
            queries=queries
        )

        assert result["total_queries"] == 1
        assert result["total_matches"] == 1
        assert "query1" in result["queries_executed"]
        assert result["per_query_stats"]["query1"]["match_count"] == 1

    @patch("main.stream_ast_grep_results")
    def test_batch_search_multiple_queries_parallel(self, mock_stream: Mock) -> None:
        """Test batch_search executes multiple queries in parallel."""
        # Mock different results for each call
        mock_stream.side_effect = [
            iter([{"file": "test1.py", "text": "match1", "range": {"start": {"line": 1}}}]),
            iter([{"file": "test2.py", "text": "match2", "range": {"start": {"line": 2}}}]),
        ]

        queries = [
            {"id": "query1", "type": "pattern", "pattern": "def $FUNC", "language": "python"},
            {"id": "query2", "type": "pattern", "pattern": "class $CLASS", "language": "python"}
        ]

        result = self.batch_search(
            project_folder=self.project_folder,
            queries=queries
        )

        assert result["total_queries"] == 2
        assert result["total_matches"] == 2
        assert len(result["queries_executed"]) == 2
        assert mock_stream.call_count == 2

    def test_batch_search_missing_type_field(self) -> None:
        """Test batch_search fails when query missing 'type' field."""
        queries = [
            {"pattern": "def $FUNC", "language": "python"}  # Missing 'type'
        ]

        with pytest.raises(ValueError, match="'type' field is required"):
            self.batch_search(project_folder=self.project_folder, queries=queries)

    def test_batch_search_invalid_type(self) -> None:
        """Test batch_search fails with invalid query type."""
        queries = [
            {"type": "invalid", "pattern": "test"}
        ]

        with pytest.raises(ValueError, match="type must be"):
            self.batch_search(project_folder=self.project_folder, queries=queries)

    @patch("main.stream_ast_grep_results")
    def test_batch_search_rule_query(self, mock_stream: Mock) -> None:
        """Test batch_search with YAML rule query."""
        mock_stream.return_value = iter([
            {"file": "test.py", "text": "match", "range": {"start": {"line": 1}}}
        ])

        yaml_rule = """
id: test-rule
language: python
rule:
  pattern: def $FUNC
"""
        queries = [
            {"id": "rule_query", "type": "rule", "yaml_rule": yaml_rule}
        ]

        result = self.batch_search(
            project_folder=self.project_folder,
            queries=queries
        )

        assert result["total_queries"] == 1
        assert result["total_matches"] == 1
        mock_stream.assert_called_once()


class TestBatchSearchAggregation:
    """Tests for result aggregation and deduplication."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.batch_search = main.mcp.tools.get("batch_search")

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("main.stream_ast_grep_results")
    def test_batch_search_deduplication(self, mock_stream: Mock) -> None:
        """Test that duplicate matches are removed."""
        # Both queries return the same match
        duplicate_match = {"file": "test.py", "text": "duplicate", "range": {"start": {"line": 1}}}
        mock_stream.side_effect = [
            iter([duplicate_match]),
            iter([duplicate_match])  # Same match from second query
        ]

        queries = [
            {"id": "q1", "type": "pattern", "pattern": "def $FUNC", "language": "python"},
            {"id": "q2", "type": "pattern", "pattern": "function $FUNC", "language": "python"}
        ]

        result = self.batch_search(
            project_folder=self.temp_dir,
            queries=queries,
            deduplicate=True
        )

        # Should only have 1 match after deduplication
        assert result["total_matches"] == 1

    @patch("main.stream_ast_grep_results")
    def test_batch_search_no_deduplication(self, mock_stream: Mock) -> None:
        """Test that deduplication can be disabled."""
        duplicate_match = {"file": "test.py", "text": "duplicate", "range": {"start": {"line": 1}}}
        mock_stream.side_effect = [
            iter([duplicate_match]),
            iter([duplicate_match])
        ]

        queries = [
            {"id": "q1", "type": "pattern", "pattern": "def $FUNC", "language": "python"},
            {"id": "q2", "type": "pattern", "pattern": "function $FUNC", "language": "python"}
        ]

        result = self.batch_search(
            project_folder=self.temp_dir,
            queries=queries,
            deduplicate=False
        )

        # Should have 2 matches when deduplication is disabled
        assert result["total_matches"] == 2

    @patch("main.stream_ast_grep_results")
    def test_batch_search_sorts_results(self, mock_stream: Mock) -> None:
        """Test that results are sorted by file and line."""
        mock_stream.side_effect = [
            iter([{"file": "b.py", "text": "match2", "range": {"start": {"line": 2}}}]),
            iter([{"file": "a.py", "text": "match1", "range": {"start": {"line": 1}}}])
        ]

        queries = [
            {"id": "q1", "type": "pattern", "pattern": "def $FUNC", "language": "python"},
            {"id": "q2", "type": "pattern", "pattern": "class $CLASS", "language": "python"}
        ]

        result = self.batch_search(
            project_folder=self.temp_dir,
            queries=queries
        )

        matches = result["matches"]
        # Should be sorted: a.py comes before b.py
        assert matches[0]["file"] == "a.py"
        assert matches[1]["file"] == "b.py"

    @patch("main.stream_ast_grep_results")
    def test_batch_search_adds_query_id_to_matches(self, mock_stream: Mock) -> None:
        """Test that each match includes query_id for traceability."""
        mock_stream.return_value = iter([
            {"file": "test.py", "text": "match", "range": {"start": {"line": 1}}}
        ])

        queries = [
            {"id": "my_query", "type": "pattern", "pattern": "def $FUNC", "language": "python"}
        ]

        result = self.batch_search(
            project_folder=self.temp_dir,
            queries=queries
        )

        assert result["matches"][0]["query_id"] == "my_query"


class TestBatchSearchConditional:
    """Tests for conditional execution."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.batch_search = main.mcp.tools.get("batch_search")

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("main.stream_ast_grep_results")
    def test_conditional_if_matches_executes(self, mock_stream: Mock) -> None:
        """Test conditional query executes when condition matches."""
        # First query returns matches
        mock_stream.side_effect = [
            iter([{"file": "test.py", "text": "match1", "range": {"start": {"line": 1}}}]),
            iter([{"file": "test.py", "text": "match2", "range": {"start": {"line": 2}}}])
        ]

        queries = [
            {"id": "q1", "type": "pattern", "pattern": "def $FUNC", "language": "python"},
            {
                "id": "q2",
                "type": "pattern",
                "pattern": "class $CLASS",
                "language": "python",
                "condition": {"type": "if_matches", "query_id": "q1"}
            }
        ]

        result = self.batch_search(
            project_folder=self.temp_dir,
            queries=queries
        )

        # Both queries should execute
        assert len(result["queries_executed"]) == 2
        assert "q1" in result["queries_executed"]
        assert "q2" in result["queries_executed"]
        assert result["per_query_stats"]["q2"]["executed"] is True

    @patch("main.stream_ast_grep_results")
    def test_conditional_if_matches_skips(self, mock_stream: Mock) -> None:
        """Test conditional query skips when condition doesn't match."""
        # First query returns no matches
        mock_stream.return_value = iter([])

        queries = [
            {"id": "q1", "type": "pattern", "pattern": "def $FUNC", "language": "python"},
            {
                "id": "q2",
                "type": "pattern",
                "pattern": "class $CLASS",
                "language": "python",
                "condition": {"type": "if_matches", "query_id": "q1"}
            }
        ]

        result = self.batch_search(
            project_folder=self.temp_dir,
            queries=queries
        )

        # Only first query should execute
        assert len(result["queries_executed"]) == 1
        assert "q1" in result["queries_executed"]
        assert "q2" not in result["queries_executed"]
        assert result["per_query_stats"]["q2"]["executed"] is False
        assert result["per_query_stats"]["q2"]["reason"] == "condition_not_met"

    @patch("main.stream_ast_grep_results")
    def test_conditional_if_no_matches_executes(self, mock_stream: Mock) -> None:
        """Test if_no_matches condition executes when first query has no matches."""
        mock_stream.side_effect = [
            iter([]),  # First query: no matches
            iter([{"file": "test.py", "text": "match", "range": {"start": {"line": 1}}}])  # Second query
        ]

        queries = [
            {"id": "q1", "type": "pattern", "pattern": "def $FUNC", "language": "python"},
            {
                "id": "q2",
                "type": "pattern",
                "pattern": "class $CLASS",
                "language": "python",
                "condition": {"type": "if_no_matches", "query_id": "q1"}
            }
        ]

        result = self.batch_search(
            project_folder=self.temp_dir,
            queries=queries
        )

        # Both queries should execute
        assert len(result["queries_executed"]) == 2
        assert result["per_query_stats"]["q2"]["executed"] is True

    @patch("main.stream_ast_grep_results")
    def test_conditional_if_no_matches_skips(self, mock_stream: Mock) -> None:
        """Test if_no_matches condition skips when first query has matches."""
        mock_stream.return_value = iter([
            {"file": "test.py", "text": "match", "range": {"start": {"line": 1}}}
        ])

        queries = [
            {"id": "q1", "type": "pattern", "pattern": "def $FUNC", "language": "python"},
            {
                "id": "q2",
                "type": "pattern",
                "pattern": "class $CLASS",
                "language": "python",
                "condition": {"type": "if_no_matches", "query_id": "q1"}
            }
        ]

        result = self.batch_search(
            project_folder=self.temp_dir,
            queries=queries
        )

        # Only first query should execute
        assert len(result["queries_executed"]) == 1
        assert result["per_query_stats"]["q2"]["executed"] is False


class TestBatchSearchErrorHandling:
    """Tests for error handling in batch operations."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.batch_search = main.mcp.tools.get("batch_search")

    def teardown_method(self) -> None:
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("main.stream_ast_grep_results")
    def test_batch_search_continues_on_query_error(self, mock_stream: Mock) -> None:
        """Test that batch_search continues when one query fails."""
        # First query raises error, second succeeds
        mock_stream.side_effect = [
            Exception("Query failed"),
            iter([{"file": "test.py", "text": "match", "range": {"start": {"line": 1}}}])
        ]

        queries = [
            {"id": "q1", "type": "pattern", "pattern": "def $FUNC", "language": "python"},
            {"id": "q2", "type": "pattern", "pattern": "class $CLASS", "language": "python"}
        ]

        result = self.batch_search(
            project_folder=self.temp_dir,
            queries=queries
        )

        # Should still execute and return results from successful query
        assert len(result["queries_executed"]) == 2
        assert result["per_query_stats"]["q1"]["match_count"] == 0  # Failed query
        assert result["per_query_stats"]["q2"]["match_count"] == 1  # Successful query

    def test_batch_search_auto_assigns_query_ids(self) -> None:
        """Test that query IDs are auto-assigned if not provided."""
        with patch("main.run_ast_grep") as mock_stream:
            mock_stream.return_value = iter([])

            queries = [
                {"type": "pattern", "pattern": "def $FUNC", "language": "python"},  # No ID
                {"type": "pattern", "pattern": "class $CLASS", "language": "python"}  # No ID
            ]

            result = self.batch_search(
                project_folder=self.temp_dir,
                queries=queries
            )

            # Should auto-assign query_0, query_1
            assert "query_0" in result["per_query_stats"]
            assert "query_1" in result["per_query_stats"]

    @patch("main.stream_ast_grep_results")
    def test_batch_search_text_output_format(self, mock_stream: Mock) -> None:
        """Test batch_search with text output format."""
        mock_stream.return_value = iter([
            {"file": "test.py", "text": "def hello():\n    pass", "range": {"start": {"line": 1}, "end": {"line": 2}}}
        ])

        queries = [
            {"id": "q1", "type": "pattern", "pattern": "def $FUNC", "language": "python"}
        ]

        result = self.batch_search(
            project_folder=self.temp_dir,
            queries=queries,
            output_format="text"
        )

        # Should return text format
        assert isinstance(result["matches"], str)
        assert "test.py" in result["matches"]

    @patch("main.stream_ast_grep_results")
    def test_batch_search_max_results_per_query(self, mock_stream: Mock) -> None:
        """Test max_results_per_query parameter."""
        mock_stream.return_value = iter([
            {"file": "test.py", "text": "match", "range": {"start": {"line": 1}}}
        ])

        queries = [
            {"id": "q1", "type": "pattern", "pattern": "def $FUNC", "language": "python"}
        ]

        self.batch_search(
            project_folder=self.temp_dir,
            queries=queries,
            max_results_per_query=5
        )

        # Verify max_results was passed through (run_ast_grep was called)
        mock_stream.assert_called_once()
