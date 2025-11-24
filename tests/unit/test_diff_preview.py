"""Unit tests for Phase 3.4: Diff Preview Generator.

Tests for generating unified diffs for apply_deduplication preview.
"""

import os
import pytest
import tempfile
from typing import Dict, Any

# Import from main.py
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from main import (
    generate_file_diff,
    generate_multi_file_diff,
    diff_preview_to_dict,
    generate_diff_from_file_paths,
    FileDiff,
    DiffPreview,
)


class TestGenerateFileDiff:
    """Tests for generate_file_diff function."""

    def test_simple_line_change(self):
        """Test diff generation for a single line change."""
        original = "def hello():\n    print('hello')\n"
        new = "def hello():\n    print('Hello, World!')\n"

        diff = generate_file_diff("/path/to/file.py", original, new)

        assert isinstance(diff, FileDiff)
        assert diff.file_path == "/path/to/file.py"
        assert diff.additions == 1
        assert diff.deletions == 1
        assert "print('hello')" in diff.unified_diff
        assert "print('Hello, World!')" in diff.unified_diff
        assert len(diff.hunks) == 1

    def test_multiple_additions(self):
        """Test diff with multiple line additions."""
        original = "line1\nline2\n"
        new = "line1\nnew_line_a\nnew_line_b\nline2\n"

        diff = generate_file_diff("/test.txt", original, new)

        assert diff.additions == 2
        assert diff.deletions == 0

    def test_multiple_deletions(self):
        """Test diff with multiple line deletions."""
        original = "line1\nto_delete_a\nto_delete_b\nline2\n"
        new = "line1\nline2\n"

        diff = generate_file_diff("/test.txt", original, new)

        assert diff.additions == 0
        assert diff.deletions == 2

    def test_no_changes(self):
        """Test diff when content is identical."""
        content = "def foo():\n    return 42\n"

        diff = generate_file_diff("/file.py", content, content)

        assert diff.additions == 0
        assert diff.deletions == 0
        assert len(diff.hunks) == 0
        assert diff.unified_diff == ""

    def test_custom_context_lines(self):
        """Test diff with custom number of context lines."""
        original = "a\nb\nc\nd\ne\nf\ng\n"
        new = "a\nb\nc\nX\ne\nf\ng\n"

        # With 1 context line
        diff_1 = generate_file_diff("/test.txt", original, new, context_lines=1)

        # With 5 context lines
        diff_5 = generate_file_diff("/test.txt", original, new, context_lines=5)

        # More context lines = longer diff
        assert len(diff_5.unified_diff) >= len(diff_1.unified_diff)

    def test_hunk_parsing(self):
        """Test that hunks are correctly parsed from diff."""
        original = "line1\nline2\nline3\n"
        new = "line1\nmodified\nline3\n"

        diff = generate_file_diff("/test.txt", original, new)

        assert len(diff.hunks) == 1
        hunk = diff.hunks[0]
        assert 'header' in hunk
        assert 'old_start' in hunk
        assert 'new_start' in hunk
        assert 'lines' in hunk

    def test_multiple_hunks(self):
        """Test diff with changes in multiple locations creating multiple hunks."""
        # Create content with changes far apart
        lines = [f"line{i}\n" for i in range(20)]
        original = "".join(lines)

        new_lines = lines.copy()
        new_lines[2] = "changed_line2\n"
        new_lines[17] = "changed_line17\n"
        new = "".join(new_lines)

        diff = generate_file_diff("/test.txt", original, new, context_lines=1)

        # Should have 2 separate hunks
        assert len(diff.hunks) == 2

    def test_formatted_diff_contains_line_numbers(self):
        """Test that formatted diff includes line numbers."""
        original = "line1\nline2\nline3\n"
        new = "line1\nmodified\nline3\n"

        diff = generate_file_diff("/test.txt", original, new)

        # Formatted diff should contain line numbers
        assert "1" in diff.formatted_diff
        assert "2" in diff.formatted_diff

    def test_formatted_diff_contains_file_header(self):
        """Test that formatted diff has file header."""
        original = "content\n"
        new = "new content\n"

        diff = generate_file_diff("/path/to/myfile.py", original, new)

        assert "/path/to/myfile.py" in diff.formatted_diff
        assert "=" * 70 in diff.formatted_diff

    def test_empty_original_file(self):
        """Test diff when original file is empty."""
        original = ""
        new = "line1\nline2\n"

        diff = generate_file_diff("/new.txt", original, new)

        assert diff.additions == 2
        assert diff.deletions == 0

    def test_empty_new_file(self):
        """Test diff when new content is empty."""
        original = "line1\nline2\n"
        new = ""

        diff = generate_file_diff("/deleted.txt", original, new)

        assert diff.additions == 0
        assert diff.deletions == 2

    def test_stores_original_and_new_content(self):
        """Test that FileDiff stores both original and new content."""
        original = "original content\n"
        new = "new content\n"

        diff = generate_file_diff("/file.txt", original, new)

        assert diff.original_content == original
        assert diff.new_content == new


class TestGenerateMultiFileDiff:
    """Tests for generate_multi_file_diff function."""

    def test_single_file_change(self):
        """Test multi-file diff with one file."""
        changes = [{
            'file_path': '/file1.py',
            'original_content': 'old\n',
            'new_content': 'new\n'
        }]

        preview = generate_multi_file_diff(changes)

        assert isinstance(preview, DiffPreview)
        assert preview.total_files == 1
        assert preview.total_additions == 1
        assert preview.total_deletions == 1
        assert len(preview.file_diffs) == 1

    def test_multiple_file_changes(self):
        """Test multi-file diff with multiple files."""
        changes = [
            {
                'file_path': '/file1.py',
                'original_content': 'a\n',
                'new_content': 'b\n'
            },
            {
                'file_path': '/file2.py',
                'original_content': 'x\n',
                'new_content': 'y\nz\n'
            }
        ]

        preview = generate_multi_file_diff(changes)

        assert preview.total_files == 2
        assert preview.total_additions == 3  # 1 + 2
        assert preview.total_deletions == 2  # 1 + 1
        assert len(preview.file_diffs) == 2

    def test_combined_diff_includes_all_files(self):
        """Test that combined_diff contains all file diffs."""
        changes = [
            {
                'file_path': '/file1.py',
                'original_content': 'a\n',
                'new_content': 'b\n'
            },
            {
                'file_path': '/file2.py',
                'original_content': 'x\n',
                'new_content': 'y\n'
            }
        ]

        preview = generate_multi_file_diff(changes)

        assert '/file1.py' in preview.combined_diff
        assert '/file2.py' in preview.combined_diff

    def test_summary_format(self):
        """Test that summary has correct format."""
        changes = [{
            'file_path': '/utils/helper.py',
            'original_content': 'old\n',
            'new_content': 'new\n'
        }]

        preview = generate_multi_file_diff(changes)

        assert "Diff Preview Summary" in preview.summary
        assert "Files modified: 1" in preview.summary
        assert "+1" in preview.summary
        assert "-1" in preview.summary
        assert "helper.py" in preview.summary

    def test_file_with_no_changes_excluded_from_count(self):
        """Test that files with no changes don't count in total_files."""
        changes = [
            {
                'file_path': '/changed.py',
                'original_content': 'a\n',
                'new_content': 'b\n'
            },
            {
                'file_path': '/unchanged.py',
                'original_content': 'same\n',
                'new_content': 'same\n'
            }
        ]

        preview = generate_multi_file_diff(changes)

        assert preview.total_files == 1
        assert len(preview.file_diffs) == 2

    def test_empty_changes_list(self):
        """Test multi-file diff with no changes."""
        preview = generate_multi_file_diff([])

        assert preview.total_files == 0
        assert preview.total_additions == 0
        assert preview.total_deletions == 0
        assert len(preview.file_diffs) == 0

    def test_custom_context_lines(self):
        """Test multi-file diff with custom context lines."""
        changes = [{
            'file_path': '/file.py',
            'original_content': 'a\nb\nc\nd\ne\n',
            'new_content': 'a\nb\nX\nd\ne\n'
        }]

        preview_1 = generate_multi_file_diff(changes, context_lines=1)
        preview_5 = generate_multi_file_diff(changes, context_lines=5)

        # More context = longer combined diff
        assert len(preview_5.combined_diff) >= len(preview_1.combined_diff)


class TestDiffPreviewToDict:
    """Tests for diff_preview_to_dict function."""

    def test_basic_conversion(self):
        """Test basic conversion to dictionary."""
        changes = [{
            'file_path': '/test.py',
            'original_content': 'old\n',
            'new_content': 'new\n'
        }]

        preview = generate_multi_file_diff(changes)
        result = diff_preview_to_dict(preview)

        assert isinstance(result, dict)
        assert 'summary' in result
        assert 'total_files' in result
        assert 'total_additions' in result
        assert 'total_deletions' in result
        assert 'combined_diff' in result
        assert 'files' in result

    def test_file_details_in_dict(self):
        """Test that file details are correctly included."""
        changes = [{
            'file_path': '/myfile.py',
            'original_content': 'a\n',
            'new_content': 'b\nc\n'
        }]

        preview = generate_multi_file_diff(changes)
        result = diff_preview_to_dict(preview)

        assert len(result['files']) == 1
        file_info = result['files'][0]
        assert file_info['file_path'] == '/myfile.py'
        assert file_info['additions'] == 2
        assert file_info['deletions'] == 1
        assert 'unified_diff' in file_info
        assert 'formatted_diff' in file_info
        assert 'hunks' in file_info

    def test_hunks_included(self):
        """Test that hunks are included in the dictionary."""
        changes = [{
            'file_path': '/test.py',
            'original_content': 'line1\nline2\n',
            'new_content': 'line1\nmodified\n'
        }]

        preview = generate_multi_file_diff(changes)
        result = diff_preview_to_dict(preview)

        hunks = result['files'][0]['hunks']
        assert isinstance(hunks, list)
        assert len(hunks) >= 1

    def test_json_serializable(self):
        """Test that result is JSON serializable."""
        import json

        changes = [{
            'file_path': '/test.py',
            'original_content': 'a\n',
            'new_content': 'b\n'
        }]

        preview = generate_multi_file_diff(changes)
        result = diff_preview_to_dict(preview)

        # Should not raise
        json_str = json.dumps(result)
        parsed = json.loads(json_str)

        assert parsed['total_files'] == 1


class TestGenerateDiffFromFilePaths:
    """Tests for generate_diff_from_file_paths function."""

    def test_reads_file_from_disk(self):
        """Test that original content is read from disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.py")

            # Write original content
            with open(file_path, 'w') as f:
                f.write("original content\n")

            # Generate diff
            new_contents = {file_path: "new content\n"}
            preview = generate_diff_from_file_paths([file_path], new_contents)

            assert preview.total_files == 1
            assert preview.file_diffs[0].original_content == "original content\n"
            assert preview.file_diffs[0].new_content == "new content\n"

    def test_multiple_files_from_disk(self):
        """Test reading multiple files from disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "file1.py")
            file2 = os.path.join(tmpdir, "file2.py")

            with open(file1, 'w') as f:
                f.write("content1\n")
            with open(file2, 'w') as f:
                f.write("content2\n")

            new_contents = {
                file1: "new1\n",
                file2: "new2\n"
            }
            preview = generate_diff_from_file_paths([file1, file2], new_contents)

            assert preview.total_files == 2

    def test_file_not_found_error(self):
        """Test FileNotFoundError when file doesn't exist."""
        nonexistent = "/nonexistent/path/file.py"
        new_contents = {nonexistent: "content\n"}

        with pytest.raises(FileNotFoundError) as exc_info:
            generate_diff_from_file_paths([nonexistent], new_contents)

        assert "not found" in str(exc_info.value)

    def test_skips_files_not_in_new_contents(self):
        """Test that files not in new_contents are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = os.path.join(tmpdir, "file1.py")
            file2 = os.path.join(tmpdir, "file2.py")

            with open(file1, 'w') as f:
                f.write("content1\n")
            with open(file2, 'w') as f:
                f.write("content2\n")

            # Only provide new content for file1
            new_contents = {file1: "new1\n"}
            preview = generate_diff_from_file_paths([file1, file2], new_contents)

            # Only file1 should be in the diff
            assert len(preview.file_diffs) == 1
            assert preview.file_diffs[0].file_path == file1

    def test_custom_context_lines(self):
        """Test custom context lines with file paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.py")

            with open(file_path, 'w') as f:
                f.write("a\nb\nc\nd\ne\n")

            new_contents = {file_path: "a\nb\nX\nd\ne\n"}

            preview_1 = generate_diff_from_file_paths(
                [file_path], new_contents, context_lines=1
            )
            preview_5 = generate_diff_from_file_paths(
                [file_path], new_contents, context_lines=5
            )

            # More context = longer diff
            assert len(preview_5.combined_diff) >= len(preview_1.combined_diff)


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_binary_like_content(self):
        """Test handling of content with unusual characters."""
        original = "normal line\n"
        new = "normal line\nwith special: \t\r\n"

        diff = generate_file_diff("/test.txt", original, new)

        assert diff.additions >= 1

    def test_very_long_lines(self):
        """Test diff with very long lines."""
        original = "x" * 1000 + "\n"
        new = "y" * 1000 + "\n"

        diff = generate_file_diff("/test.txt", original, new)

        assert diff.additions == 1
        assert diff.deletions == 1

    def test_unicode_content(self):
        """Test diff with Unicode content."""
        original = "Hello\nWorld\n"
        new = "Hello\nWorld (multi-lingual)\n"

        diff = generate_file_diff("/test.txt", original, new)

        assert "multi-lingual" in diff.unified_diff
        assert diff.additions == 1
        assert diff.deletions == 1

    def test_mixed_line_endings(self):
        """Test handling of mixed line endings."""
        original = "line1\r\nline2\n"
        new = "line1\nline2\r\n"

        # Should not crash
        diff = generate_file_diff("/test.txt", original, new)
        assert isinstance(diff, FileDiff)

    def test_file_with_no_trailing_newline(self):
        """Test files without trailing newline."""
        original = "no newline at end"
        new = "modified without newline"

        diff = generate_file_diff("/test.txt", original, new)

        assert diff.additions == 1
        assert diff.deletions == 1

    def test_addition_at_end_of_file(self):
        """Test adding content at end of file."""
        original = "line1\nline2\n"
        new = "line1\nline2\nline3\n"

        diff = generate_file_diff("/test.txt", original, new)

        assert diff.additions == 1
        assert diff.deletions == 0

    def test_deletion_at_beginning(self):
        """Test deleting content at beginning of file."""
        original = "line1\nline2\nline3\n"
        new = "line2\nline3\n"

        diff = generate_file_diff("/test.txt", original, new)

        assert diff.additions == 0
        assert diff.deletions == 1

    def test_large_file_diff(self):
        """Test diff performance with larger files."""
        # Generate 1000 line file
        original_lines = [f"line {i}\n" for i in range(1000)]
        original = "".join(original_lines)

        # Modify some lines
        new_lines = original_lines.copy()
        new_lines[100] = "modified 100\n"
        new_lines[500] = "modified 500\n"
        new_lines[900] = "modified 900\n"
        new = "".join(new_lines)

        diff = generate_file_diff("/large.txt", original, new)

        assert diff.additions == 3
        assert diff.deletions == 3


class TestHunkStructure:
    """Tests for hunk data structure."""

    def test_hunk_header_format(self):
        """Test that hunk headers have correct format."""
        original = "a\nb\nc\n"
        new = "a\nX\nc\n"

        diff = generate_file_diff("/test.txt", original, new)

        assert len(diff.hunks) == 1
        hunk = diff.hunks[0]
        assert '@@' in hunk['header']

    def test_hunk_line_numbers(self):
        """Test that hunk line numbers are correct."""
        original = "a\nb\nc\n"
        new = "a\nX\nc\n"

        diff = generate_file_diff("/test.txt", original, new)

        hunk = diff.hunks[0]
        assert hunk['old_start'] >= 1
        assert hunk['new_start'] >= 1

    def test_hunk_lines_content(self):
        """Test that hunk lines contain the changes."""
        original = "keep\ndelete\nkeep\n"
        new = "keep\nadd\nkeep\n"

        diff = generate_file_diff("/test.txt", original, new)

        hunk = diff.hunks[0]
        lines_str = ''.join(hunk['lines'])
        assert 'delete' in lines_str or 'add' in lines_str
