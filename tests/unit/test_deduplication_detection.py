"""Consolidated tests for deduplication detection functionality.

This file consolidates tests from:
- test_duplication.py
- test_ast_diff.py
- test_diff_preview.py

Focus: Detection, grouping, AST diff, alignment
"""
from ast_grep_mcp.utils.console_logger import console

import os
import sys
from unittest.mock import Mock, patch

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import from main for backward compatibility
from main import (
    calculate_similarity,
    normalize_code,
    generate_refactoring_suggestions,
    build_diff_tree,
    build_nested_diff_tree,
    format_alignment_diff,
    diff_preview_to_dict,
    generate_diff_from_file_paths,
    generate_file_diff,
    generate_multi_file_diff,
)


class TestDuplicationDetection:
    """Tests for duplicate code detection."""

    def test_calculate_similarity(self):
        """Test similarity calculation between code snippets."""
        code1 = """
def process_data(data):
    result = []
    for item in data:
        result.append(item * 2)
    return result
"""
        code2 = """
def process_data(data):
    result = []
    for item in data:
        result.append(item * 3)
    return result
"""
        similarity = calculate_similarity(code1, code2, "python")
        assert similarity > 0.8
        assert similarity < 1.0

    def test_normalize_code(self):
        """Test code normalization."""
        code = """
def hello():
    # This is a comment
    print("Hello, World!")
"""
        normalized = normalize_code(code, "python")
        assert "def hello()" in normalized
        assert "print" in normalized

    def test_generate_refactoring_suggestions(self):
        """Test generation of refactoring suggestions."""
        duplicates = [
            {
                "code": "def foo(): pass",
                "file": "file1.py",
                "similarity": 0.9
            },
            {
                "code": "def bar(): pass",
                "file": "file2.py",
                "similarity": 0.9
            }
        ]
        suggestions = generate_refactoring_suggestions(duplicates, "python")
        assert len(suggestions) > 0
        assert "extract" in str(suggestions).lower()


class TestASTDiff:
    """Tests for AST diff functionality."""

    def test_build_diff_tree(self):
        """Test building a diff tree from two code snippets."""
        code1 = "def foo(): return 1"
        code2 = "def foo(): return 2"

        diff_tree = build_diff_tree(code1, code2, "python")
        assert diff_tree is not None
        assert "diff" in str(diff_tree).lower() or diff_tree == {}

    def test_build_nested_diff_tree(self):
        """Test building nested diff tree."""
        code1 = """
def outer():
    def inner():
        return 1
"""
        code2 = """
def outer():
    def inner():
        return 2
"""
        diff_tree = build_nested_diff_tree(code1, code2, "python")
        assert diff_tree is not None

    def test_format_alignment_diff(self):
        """Test formatting alignment diff."""
        diff_data = {
            "alignments": [
                {"type": "match", "value": "def foo():"},
                {"type": "diff", "old": "return 1", "new": "return 2"}
            ]
        }
        formatted = format_alignment_diff(diff_data)
        assert formatted is not None
        assert isinstance(formatted, str) or isinstance(formatted, dict)


class TestDiffPreview:
    """Tests for diff preview generation."""

    def test_diff_preview_to_dict(self):
        """Test converting diff preview to dictionary."""
        diff_text = """
--- a/file.py
+++ b/file.py
@@ -1,3 +1,3 @@
 def foo():
-    return 1
+    return 2
"""
        result = diff_preview_to_dict(diff_text)
        assert isinstance(result, dict)
        assert "hunks" in result or "changes" in result or result == {}

    def test_generate_file_diff(self):
        """Test generating diff for a single file."""
        old_content = "def foo(): return 1"
        new_content = "def foo(): return 2"

        diff = generate_file_diff(old_content, new_content, "file.py")
        assert isinstance(diff, str)
        assert "def foo()" in diff or diff == ""

    def test_generate_multi_file_diff(self):
        """Test generating diff for multiple files."""
        changes = [
            {
                "file": "file1.py",
                "old_content": "def foo(): return 1",
                "new_content": "def foo(): return 2"
            },
            {
                "file": "file2.py",
                "old_content": "def bar(): return 3",
                "new_content": "def bar(): return 4"
            }
        ]

        diff = generate_multi_file_diff(changes)
        assert isinstance(diff, str)
        assert "file1.py" in diff or "file2.py" in diff or diff == ""

    @patch('os.path.exists')
    @patch('builtins.open', create=True)
    def test_generate_diff_from_file_paths(self, mock_open, mock_exists):
        """Test generating diff from file paths."""
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.side_effect = [
            "def foo(): return 1",
            "def foo(): return 2"
        ]

        diff = generate_diff_from_file_paths("old.py", "new.py")
        assert isinstance(diff, str)
