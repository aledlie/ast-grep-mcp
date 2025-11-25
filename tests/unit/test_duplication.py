"""Tests for code duplication detection functionality"""

import os
import sys
from typing import Any, Dict, List
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
from main import (
    calculate_similarity,
    generate_refactoring_suggestions,
    normalize_code,
)

from ast_grep_mcp.features.deduplication.detector import DuplicationDetector


class TestNormalizeCode:
    """Test code normalization for comparison"""

    def test_removes_whitespace(self) -> None:
        """Test that leading/trailing whitespace is removed"""
        code = "  def foo():  \n    return 1  "
        normalized = normalize_code(code)
        assert normalized == "def foo():\nreturn 1"

    def test_removes_blank_lines(self) -> None:
        """Test that blank lines are removed"""
        code = "def foo():\n\n    return 1\n\n"
        normalized = normalize_code(code)
        assert normalized == "def foo():\nreturn 1"

    def test_removes_comments(self) -> None:
        """Test that comments are removed"""
        code = "# This is a comment\ndef foo():\n    # Another comment\n    return 1"
        normalized = normalize_code(code)
        assert "# This is a comment" not in normalized
        assert "# Another comment" not in normalized

    def test_preserves_code_structure(self) -> None:
        """Test that actual code structure is preserved"""
        code = "def foo(x, y):\n    return x + y"
        normalized = normalize_code(code)
        assert "def foo(x, y):" in normalized
        assert "return x + y" in normalized


class TestCalculateSimilarity:
    """Test similarity calculation between code snippets"""

    def test_identical_code(self) -> None:
        """Test that identical code has 1.0 similarity"""
        code1 = "def foo():\n    return 1"
        code2 = "def foo():\n    return 1"
        similarity = calculate_similarity(code1, code2)
        assert similarity == 1.0

    def test_completely_different_code(self) -> None:
        """Test that completely different code has low similarity"""
        code1 = "def foo():\n    return 1"
        code2 = "class Bar:\n    pass"
        similarity = calculate_similarity(code1, code2)
        assert similarity < 0.5

    def test_similar_code(self) -> None:
        """Test that similar code has high similarity"""
        code1 = "def foo(x):\n    return x + 1"
        code2 = "def bar(y):\n    return y + 1"
        similarity = calculate_similarity(code1, code2)
        assert similarity > 0.6

    def test_empty_code(self) -> None:
        """Test that empty code returns 0 similarity"""
        assert calculate_similarity("", "def foo():\n    pass") == 0.0
        assert calculate_similarity("def foo():\n    pass", "") == 0.0
        assert calculate_similarity("", "") == 0.0

    def test_whitespace_differences_normalized(self) -> None:
        """Test that whitespace differences are normalized"""
        code1 = "def foo():    \n    return 1"
        code2 = "def foo():\n    return 1   "
        similarity = calculate_similarity(code1, code2)
        assert similarity == 1.0


class TestGroupDuplicates:
    """Test grouping of duplicate code matches"""

    def test_groups_identical_matches(self) -> None:
        """Test that identical matches are grouped"""
        matches = [
            {"text": "def foo():\n    return 1\n    x = 2\n    y = 3", "file": "a.py"},
            {"text": "def bar():\n    return 1\n    x = 2\n    y = 3", "file": "b.py"},
            {"text": "def baz():\n    return 1\n    x = 2\n    y = 3", "file": "c.py"},
        ]

        groups = duplication_detector.group_duplicates(matches, min_similarity=0.8, min_lines=3)
        assert len(groups) == 1
        assert len(groups[0]) == 3

    def test_min_lines_filter(self) -> None:
        """Test that matches below min_lines are filtered out"""
        matches = [
            {"text": "x = 1", "file": "a.py"},
            {"text": "y = 1", "file": "b.py"},
        ]

        groups = duplication_detector.group_duplicates(matches, min_similarity=0.8, min_lines=5)
        assert len(groups) == 0

    def test_min_similarity_threshold(self) -> None:
        """Test that similarity threshold is respected"""
        matches = [
            {"text": "def foo():\n    return 1\n    x = 2\n    y = 3", "file": "a.py"},
            {"text": "def bar():\n    return 1\n    x = 2\n    z = 3", "file": "b.py"},
            {"text": "class Baz:\n    pass\n    w = 4\n    t = 5", "file": "c.py"},
        ]

        # With high threshold, only very similar items group
        groups = duplication_detector.group_duplicates(matches, min_similarity=0.9, min_lines=3)
        # foo and bar are very similar, baz is different
        assert len(groups) <= 1

    def test_no_duplicates_returns_empty(self) -> None:
        """Test that no duplicates returns empty list"""
        matches = [
            {"text": "def foo():\n    return 1\n    x = 2\n    y = 3", "file": "a.py"},
            {"text": "class Bar:\n    pass\n    w = 4\n    t = 5", "file": "b.py"},
        ]

        groups = duplication_detector.group_duplicates(matches, min_similarity=0.95, min_lines=3)
        assert len(groups) == 0

    def test_empty_matches_returns_empty(self) -> None:
        """Test that empty matches list returns empty groups"""
        groups = duplication_detector.group_duplicates([], min_similarity=0.8, min_lines=3)
        assert len(groups) == 0


class TestGenerateRefactoringSuggestions:
    """Test generation of refactoring suggestions"""

    def test_function_definition_suggestions(self) -> None:
        """Test suggestions for function duplication"""
        groups = [[
            {
                "text": "def foo():\n    return 1",
                "file": "a.py",
                "range": {"start": {"line": 0}, "end": {"line": 1}}
            },
            {
                "text": "def bar():\n    return 1",
                "file": "b.py",
                "range": {"start": {"line": 5}, "end": {"line": 6}}
            }
        ]]

        suggestions = generate_refactoring_suggestions(groups, "function_definition", "python")

        assert len(suggestions) == 1
        assert suggestions[0]["type"] == "Extract Shared Function"
        assert suggestions[0]["duplicate_count"] == 2
        assert "utility function" in suggestions[0]["description"].lower()

    def test_class_definition_suggestions(self) -> None:
        """Test suggestions for class duplication"""
        groups = [[
            {
                "text": "class Foo:\n    pass",
                "file": "a.py",
                "range": {"start": {"line": 0}, "end": {"line": 1}}
            },
            {
                "text": "class Bar:\n    pass",
                "file": "b.py",
                "range": {"start": {"line": 0}, "end": {"line": 1}}
            }
        ]]

        suggestions = generate_refactoring_suggestions(groups, "class_definition", "python")

        assert len(suggestions) == 1
        assert suggestions[0]["type"] == "Extract Base Class"
        assert "base class" in suggestions[0]["description"].lower()

    def test_includes_locations(self) -> None:
        """Test that suggestions include file locations"""
        groups = [[
            {
                "text": "def foo():\n    return 1",
                "file": "a.py",
                "range": {"start": {"line": 0}, "end": {"line": 1}}
            },
            {
                "text": "def bar():\n    return 1",
                "file": "b.py",
                "range": {"start": {"line": 5}, "end": {"line": 6}}
            }
        ]]

        suggestions = generate_refactoring_suggestions(groups, "function_definition", "python")

        assert len(suggestions[0]["locations"]) == 2
        assert "a.py:1-2" in suggestions[0]["locations"]
        assert "b.py:6-7" in suggestions[0]["locations"]

    def test_calculates_line_savings(self) -> None:
        """Test that potential line savings are calculated"""
        groups = [[
            {
                "text": "def foo():\n    return 1\n    x = 2",
                "file": "a.py",
                "range": {"start": {"line": 0}, "end": {"line": 2}}
            },
            {
                "text": "def bar():\n    return 1\n    x = 2",
                "file": "b.py",
                "range": {"start": {"line": 0}, "end": {"line": 2}}
            }
        ]]

        suggestions = generate_refactoring_suggestions(groups, "function_definition", "python")

        # 3 lines per duplicate * 2 duplicates = 6 total duplicated lines
        assert suggestions[0]["total_duplicated_lines"] == 6
        assert suggestions[0]["lines_per_duplicate"] == 3


class TestFindDuplicationTool:
    """Test the find_duplication MCP tool"""

    @patch("main.stream_ast_grep_results")
    def test_finds_duplicate_functions(self, mock_stream: Any) -> None:
        """Test finding duplicate functions"""
        mock_matches: List[Any] = [
            {
                "text": "def foo():\n    return 1\n    x = 2\n    y = 3",
                "file": "a.py",
                "range": {"start": {"line": 0}, "end": {"line": 3}}
            },
            {
                "text": "def bar():\n    return 1\n    x = 2\n    y = 3",
                "file": "b.py",
                "range": {"start": {"line": 5}, "end": {"line": 8}}
            }
        ]
        mock_stream.return_value = iter(mock_matches)

        result = find_duplication(
            project_folder="/test/project",
            language="python",
            construct_type="function_definition",
            min_similarity=0.8,
            min_lines=3
        )

        assert result["summary"]["total_constructs"] == 2
        assert result["summary"]["duplicate_groups"] >= 1
        assert len(result["refactoring_suggestions"]) >= 1

    @patch("main.stream_ast_grep_results")
    def test_no_duplicates_found(self, mock_stream: Any) -> None:
        """Test when no duplicates are found"""
        mock_matches: List[Any] = [
            {
                "text": "def foo():\n    return 1",
                "file": "a.py",
                "range": {"start": {"line": 0}, "end": {"line": 1}}
            },
            {
                "text": "class Bar:\n    pass",
                "file": "b.py",
                "range": {"start": {"line": 0}, "end": {"line": 1}}
            }
        ]
        mock_stream.return_value = iter(mock_matches)

        result = find_duplication(
            project_folder="/test/project",
            language="python",
            construct_type="function_definition",
            min_similarity=0.9,
            min_lines=1
        )

        assert result["summary"]["duplicate_groups"] == 0
        assert len(result["refactoring_suggestions"]) == 0

    @patch("main.stream_ast_grep_results")
    def test_no_constructs_found(self, mock_stream: Any) -> None:
        """Test when no constructs are found"""
        mock_stream.return_value = iter([])

        result = find_duplication(
            project_folder="/test/project",
            language="python",
            construct_type="function_definition"
        )

        assert result["summary"]["total_constructs"] == 0
        assert "No function_definition instances found" in result["message"]
        assert "analysis_time_seconds" in result["summary"]
        assert isinstance(result["summary"]["analysis_time_seconds"], (int, float))

    @patch("main.stream_ast_grep_results")
    def test_custom_similarity_threshold(self, mock_stream: Any) -> None:
        """Test with custom similarity threshold"""
        mock_matches: List[Any] = [
            {
                "text": "def foo():\n    return 1\n    x = 2",
                "file": "a.py",
                "range": {"start": {"line": 0}, "end": {"line": 2}}
            },
            {
                "text": "def bar():\n    return 2\n    x = 3",
                "file": "b.py",
                "range": {"start": {"line": 0}, "end": {"line": 2}}
            }
        ]
        mock_stream.return_value = iter(mock_matches)

        # With high threshold, these won't be considered duplicates
        result_strict = find_duplication(
            project_folder="/test/project",
            language="python",
            min_similarity=0.99
        )

        # With low threshold, they will be
        mock_stream.return_value = iter(mock_matches)
        result_lenient = find_duplication(
            project_folder="/test/project",
            language="python",
            min_similarity=0.5
        )

        # Lenient should find more duplicates
        assert result_lenient["summary"]["duplicate_groups"] >= result_strict["summary"]["duplicate_groups"]

    def test_invalid_similarity_threshold(self) -> None:
        """Test that invalid similarity threshold raises error"""
        with pytest.raises(ValueError, match="min_similarity must be between 0.0 and 1.0"):
            find_duplication(
                project_folder="/test/project",
                language="python",
                min_similarity=1.5
            )

    def test_invalid_min_lines(self) -> None:
        """Test that invalid min_lines raises error"""
        with pytest.raises(ValueError, match="min_lines must be at least 1"):
            find_duplication(
                project_folder="/test/project",
                language="python",
                min_lines=0
            )

    @patch("main.stream_ast_grep_results")
    def test_max_constructs_limit(self, mock_stream: Any) -> None:
        """Test that max_constructs limits the analysis scope"""
        # Create 10 mock matches
        mock_matches: List[Any] = [
            {
                "text": f"def foo{i}():\n    return {i}",
                "file": f"file{i}.py",
                "range": {"start": {"line": 0}, "end": {"line": 1}}
            }
            for i in range(10)
        ]
        mock_stream.return_value = iter(mock_matches)

        find_duplication(
            project_folder="/test/project",
            language="python",
            max_constructs=5  # Limit to 5
        )

        # stream_ast_grep_results should be called with max_results=5
        mock_stream.assert_called_once()
        call_args = mock_stream.call_args
        # Check that max_results was passed correctly
        assert call_args[1]['max_results'] == 5

    @patch("main.stream_ast_grep_results")
    def test_max_constructs_unlimited(self, mock_stream: Any) -> None:
        """Test that max_constructs=0 means unlimited"""
        mock_matches: List[Any] = []
        mock_stream.return_value = iter(mock_matches)

        find_duplication(
            project_folder="/test/project",
            language="python",
            max_constructs=0  # Unlimited
        )

        # stream_ast_grep_results should be called with max_results=0
        mock_stream.assert_called_once()
        call_args = mock_stream.call_args
        assert call_args[1]['max_results'] == 0

    def test_invalid_max_constructs(self) -> None:
        """Test that negative max_constructs raises error"""
        with pytest.raises(ValueError, match="max_constructs must be 0 \\(unlimited\\) or positive"):
            find_duplication(
                project_folder="/test/project",
                language="python",
                max_constructs=-1
            )

    @patch("main.stream_ast_grep_results")
    def test_exclude_patterns_filters_library_code(self, mock_stream: Any) -> None:
        """Test that exclude_patterns filters out library code"""
        # Create matches with some in library paths
        mock_matches: List[Any] = [
            {
                "text": "def foo():\n    return 1\n    x = 2\n    y = 3",
                "file": "/project/mycode.py",
                "range": {"start": {"line": 0}, "end": {"line": 3}}
            },
            {
                "text": "def bar():\n    return 1\n    x = 2\n    y = 3",
                "file": "/project/site-packages/lib.py",
                "range": {"start": {"line": 0}, "end": {"line": 3}}
            },
            {
                "text": "def baz():\n    return 1\n    x = 2\n    y = 3",
                "file": "/project/node_modules/lib.js",
                "range": {"start": {"line": 0}, "end": {"line": 3}}
            },
            {
                "text": "def qux():\n    return 1\n    x = 2\n    y = 3",
                "file": "/project/utils.py",
                "range": {"start": {"line": 0}, "end": {"line": 3}}
            }
        ]
        mock_stream.return_value = iter(mock_matches)

        result = find_duplication(
            project_folder="/test/project",
            language="python",
            exclude_patterns=["site-packages", "node_modules"]
        )

        # Should only analyze the 2 non-library files
        assert result["summary"]["total_constructs"] == 2

    @patch("main.stream_ast_grep_results")
    def test_exclude_patterns_empty_list(self, mock_stream: Any) -> None:
        """Test that empty exclude_patterns includes all matches"""
        mock_matches: List[Any] = [
            {
                "text": "def foo():\n    return 1\n    x = 2\n    y = 3",
                "file": "/project/mycode.py",
                "range": {"start": {"line": 0}, "end": {"line": 3}}
            },
            {
                "text": "def bar():\n    return 1\n    x = 2\n    y = 3",
                "file": "/project/site-packages/lib.py",
                "range": {"start": {"line": 0}, "end": {"line": 3}}
            }
        ]
        mock_stream.return_value = iter(mock_matches)

        result = find_duplication(
            project_folder="/test/project",
            language="python",
            exclude_patterns=[]  # No exclusions
        )

        # Should analyze both files
        assert result["summary"]["total_constructs"] == 2
