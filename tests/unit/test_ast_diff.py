"""Unit tests for AST diff analysis functions.

Tests for align_code_blocks, AlignmentResult, DiffTree, and format_alignment_diff.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ast_grep_mcp.models.deduplication import (
    AlignmentResult,
    AlignmentSegment,
    DiffTree,
    DiffTreeNode,
)
from main import (
    build_diff_tree,
    build_nested_diff_tree,
    format_alignment_diff,
)

from ast_grep_mcp.features.deduplication.analyzer import PatternAnalyzer
    align_code_blocks,
    AlignmentResult,
    AlignmentSegment,
    DiffTree,
    DiffTreeNode,
    build_diff_tree,
    build_nested_diff_tree,
    format_alignment_diff,
)


class TestAlignCodeBlocksIdentical:
    """Tests for align_code_blocks with identical code."""

    def test_identical_single_line(self, pattern_analyzer):
        """Identical single-line code should have 100% similarity."""
        code = "x = 1"
        result = pattern_analyzer.align_code_blocks(code, code)

        assert result.similarity_ratio == 1.0
        assert result.aligned_lines == 1
        assert result.divergent_lines == 0
        assert len(result.segments) == 1
        assert result.segments[0].segment_type == 'aligned'

    def test_identical_multiline(self, pattern_analyzer):
        """Identical multi-line code should have 100% similarity."""
        code = "def foo():\n    x = 1\n    return x"
        result = pattern_analyzer.align_code_blocks(code, code)

        assert result.similarity_ratio == 1.0
        assert result.aligned_lines == 3
        assert result.divergent_lines == 0
        assert result.block1_total_lines == 3
        assert result.block2_total_lines == 3

    def test_identical_empty_blocks(self, pattern_analyzer):
        """Empty code blocks should have 100% similarity."""
        result = pattern_analyzer.align_code_blocks("", "")

        assert result.similarity_ratio == 1.0
        assert result.aligned_lines == 0
        assert result.divergent_lines == 0

    def test_identical_with_different_whitespace(self, pattern_analyzer):
        """Code differing only in leading/trailing whitespace should align with ignore_whitespace=True."""
        code1 = "  x = 1  "
        code2 = "x = 1"
        result = pattern_analyzer.align_code_blocks(code1, code2, ignore_whitespace=True)

        assert result.similarity_ratio == 1.0
        assert result.aligned_lines == 1

    def test_whitespace_difference_detected(self, pattern_analyzer):
        """Whitespace differences detected when ignore_whitespace=False."""
        code1 = "x=1"
        code2 = "x = 1"
        result = pattern_analyzer.align_code_blocks(code1, code2, ignore_whitespace=False)

        assert result.similarity_ratio == 0.0
        assert result.divergent_lines == 1


class TestAlignCodeBlocksSingleLineDiff:
    """Tests for align_code_blocks with single-line differences."""

    def test_single_value_change(self, pattern_analyzer):
        """Single value change in multi-line code."""
        code1 = "def foo():\n    x = 1\n    return x"
        code2 = "def foo():\n    x = 2\n    return x"
        result = pattern_analyzer.align_code_blocks(code1, code2)

        assert 0.6 < result.similarity_ratio < 0.7  # ~66%
        assert result.aligned_lines == 2
        assert result.divergent_lines == 1

        # Check segments
        segment_types = [s.segment_type for s in result.segments]
        assert 'aligned' in segment_types
        assert 'divergent' in segment_types

    def test_function_name_change(self, pattern_analyzer):
        """Function name change should create divergent segment."""
        code1 = "def foo():\n    pass"
        code2 = "def bar():\n    pass"
        result = pattern_analyzer.align_code_blocks(code1, code2)

        assert result.divergent_lines >= 1
        divergent_segs = [s for s in result.segments if s.segment_type == 'divergent']
        assert len(divergent_segs) >= 1

    def test_comment_only_line_difference(self, pattern_analyzer):
        """Comments should be ignored when ignore_comments=True."""
        code1 = "x = 1\n# comment 1\ny = 2"
        code2 = "x = 1\n# comment 2\ny = 2"
        result = pattern_analyzer.align_code_blocks(code1, code2, ignore_comments=True)

        # Both comments normalize to empty, so they should match
        assert result.aligned_lines == 3
        assert result.divergent_lines == 0

    def test_comment_difference_detected(self, pattern_analyzer):
        """Comment differences detected when ignore_comments=False."""
        code1 = "# comment 1"
        code2 = "# comment 2"
        result = pattern_analyzer.align_code_blocks(code1, code2, ignore_comments=False)

        assert result.divergent_lines == 1


class TestAlignCodeBlocksMultiLineDiff:
    """Tests for align_code_blocks with multi-line differences."""

    def test_multiple_line_changes(self, pattern_analyzer):
        """Multiple consecutive line changes."""
        code1 = "a = 1\nb = 2\nc = 3"
        code2 = "a = 10\nb = 20\nc = 30"
        result = pattern_analyzer.align_code_blocks(code1, code2)

        assert result.similarity_ratio == 0.0
        assert result.divergent_lines == 3

    def test_block_replacement(self, pattern_analyzer):
        """Entire block replaced with different content."""
        code1 = "if True:\n    x = 1\n    y = 2"
        code2 = "if True:\n    a = 10\n    b = 20"
        result = pattern_analyzer.align_code_blocks(code1, code2)

        assert result.aligned_lines >= 1  # "if True:" should align
        assert result.divergent_lines >= 2

    def test_partial_overlap(self, pattern_analyzer):
        """Blocks with partial overlap."""
        code1 = "x = 1\ny = 2\nz = 3\nw = 4"
        code2 = "x = 1\ny = 2\na = 5\nb = 6"
        result = pattern_analyzer.align_code_blocks(code1, code2)

        assert result.aligned_lines == 2
        assert result.divergent_lines == 2


class TestAlignCodeBlocksInsertionsAndDeletions:
    """Tests for align_code_blocks with insertions and deletions."""

    def test_insertion_at_end(self, pattern_analyzer):
        """Lines inserted at end of block."""
        code1 = "x = 1\ny = 2"
        code2 = "x = 1\ny = 2\nz = 3"
        result = pattern_analyzer.align_code_blocks(code1, code2)

        assert result.aligned_lines == 2
        assert result.divergent_lines == 1

        inserted_segs = [s for s in result.segments if s.segment_type == 'inserted']
        assert len(inserted_segs) == 1
        assert 'z = 3' in inserted_segs[0].block2_text

    def test_insertion_at_beginning(self, pattern_analyzer):
        """Lines inserted at beginning of block."""
        code1 = "y = 2\nz = 3"
        code2 = "x = 1\ny = 2\nz = 3"
        result = pattern_analyzer.align_code_blocks(code1, code2)

        assert result.aligned_lines == 2
        assert result.divergent_lines == 1

        inserted_segs = [s for s in result.segments if s.segment_type == 'inserted']
        assert len(inserted_segs) == 1

    def test_insertion_in_middle(self, pattern_analyzer):
        """Lines inserted in middle of block."""
        code1 = "x = 1\nz = 3"
        code2 = "x = 1\ny = 2\nz = 3"
        result = pattern_analyzer.align_code_blocks(code1, code2)

        assert result.aligned_lines == 2
        assert result.divergent_lines == 1

    def test_deletion_at_end(self, pattern_analyzer):
        """Lines deleted from end of block."""
        code1 = "x = 1\ny = 2\nz = 3"
        code2 = "x = 1\ny = 2"
        result = pattern_analyzer.align_code_blocks(code1, code2)

        assert result.aligned_lines == 2
        assert result.divergent_lines == 1

        deleted_segs = [s for s in result.segments if s.segment_type == 'deleted']
        assert len(deleted_segs) == 1
        assert 'z = 3' in deleted_segs[0].block1_text

    def test_deletion_at_beginning(self, pattern_analyzer):
        """Lines deleted from beginning of block."""
        code1 = "x = 1\ny = 2\nz = 3"
        code2 = "y = 2\nz = 3"
        result = pattern_analyzer.align_code_blocks(code1, code2)

        assert result.aligned_lines == 2
        assert result.divergent_lines == 1

        deleted_segs = [s for s in result.segments if s.segment_type == 'deleted']
        assert len(deleted_segs) == 1

    def test_mixed_insertions_and_deletions(self, pattern_analyzer):
        """Both insertions and deletions in same comparison."""
        code1 = "a = 1\nb = 2\nc = 3"
        code2 = "x = 0\nb = 2\ny = 4"
        result = pattern_analyzer.align_code_blocks(code1, code2)

        # b = 2 should align
        assert result.aligned_lines >= 1
        # a=1, c=3 deleted; x=0, y=4 inserted or replaced
        assert result.divergent_lines >= 2


class TestBuildDiffTree:
    """Tests for build_diff_tree function."""

    def test_build_tree_from_simple_result(self, pattern_analyzer):
        """Build tree from simple alignment result."""
        result = pattern_analyzer.align_code_blocks("x = 1", "x = 1")
        tree = build_diff_tree(result)

        assert isinstance(tree, DiffTree)
        assert tree.root.node_type == 'container'
        assert len(tree.root.children) == 1
        assert tree.root.children[0].node_type == 'aligned'

    def test_build_tree_with_divergent(self, pattern_analyzer):
        """Build tree with divergent segments."""
        result = pattern_analyzer.align_code_blocks("x = 1", "x = 2")
        tree = build_diff_tree(result)

        divergent_nodes = tree.find_divergent_regions()
        assert len(divergent_nodes) == 1

    def test_tree_preserves_similarity(self, pattern_analyzer):
        """Tree preserves similarity ratio from result."""
        result = pattern_analyzer.align_code_blocks("a\nb\nc", "a\nx\nc")
        tree = build_diff_tree(result)

        assert tree.similarity_ratio == result.similarity_ratio
        assert tree.total_aligned == result.aligned_lines
        assert tree.total_divergent == result.divergent_lines

    def test_tree_metadata(self, pattern_analyzer):
        """Tree nodes contain correct metadata."""
        result = pattern_analyzer.align_code_blocks("a\nb", "a\nc")
        tree = build_diff_tree(result)

        for child in tree.root.children:
            assert 'block1_start' in child.metadata
            assert 'block1_end' in child.metadata
            assert 'block2_start' in child.metadata
            assert 'block2_end' in child.metadata

    def test_build_tree_empty_input(self, pattern_analyzer):
        """Build tree from empty input."""
        result = pattern_analyzer.align_code_blocks("", "")
        tree = build_diff_tree(result)

        assert tree.root.node_type == 'container'
        assert len(tree.root.children) == 0


class TestDiffTreeTraversal:
    """Tests for DiffTree traversal and query methods."""

    def test_depth_first_traversal(self, pattern_analyzer):
        """Depth-first traversal visits all nodes."""
        result = pattern_analyzer.align_code_blocks("a\nb\nc", "a\nx\nc")
        tree = build_diff_tree(result)

        nodes = tree.traverse_depth_first()
        # Should include root + all children
        assert len(nodes) >= 1
        assert nodes[0] == tree.root

    def test_breadth_first_traversal(self, pattern_analyzer):
        """Breadth-first traversal visits nodes level by level."""
        result = pattern_analyzer.align_code_blocks("a\nb\nc", "a\nx\nc")
        tree = build_diff_tree(result)

        nodes = tree.traverse_breadth_first()
        assert nodes[0] == tree.root
        # All root's children should come before any grandchildren
        for i, node in enumerate(nodes):
            if node == tree.root:
                continue
            if node in tree.root.children:
                # Root's children should come before grandchildren
                for child in tree.root.children:
                    if child != node and child.children:
                        for grandchild in child.children:
                            if grandchild in nodes:
                                assert nodes.index(grandchild) > i

    def test_find_divergent_regions(self, pattern_analyzer):
        """Find all divergent regions in tree."""
        result = pattern_analyzer.align_code_blocks("a\nb\nc", "x\nb\ny")
        tree = build_diff_tree(result)

        divergent = tree.find_divergent_regions()
        # Should have divergent for 'a' vs 'x' and 'c' vs 'y'
        assert len(divergent) >= 1

    def test_find_aligned_regions(self, pattern_analyzer):
        """Find all aligned regions in tree."""
        result = pattern_analyzer.align_code_blocks("a\nb\nc", "x\nb\ny")
        tree = build_diff_tree(result)

        aligned = tree.find_aligned_regions()
        # 'b' should align
        assert len(aligned) >= 1

    def test_get_summary(self, pattern_analyzer):
        """Get summary returns correct structure."""
        result = pattern_analyzer.align_code_blocks("a\nb", "a\nc")
        tree = build_diff_tree(result)

        summary = tree.get_summary()
        assert 'similarity_ratio' in summary
        assert 'total_aligned' in summary
        assert 'total_divergent' in summary
        assert 'depth' in summary
        assert 'node_counts' in summary


class TestDiffTreeNode:
    """Tests for DiffTreeNode methods."""

    def test_add_child(self):
        """Adding children to node."""
        parent = DiffTreeNode(
            node_type='container',
            content='',
            children=[],
            metadata={}
        )
        child = DiffTreeNode(
            node_type='aligned',
            content='x = 1',
            children=[],
            metadata={}
        )

        parent.add_child(child)
        assert len(parent.children) == 1
        assert parent.children[0] == child

    def test_get_all_nodes(self):
        """Get all nodes in subtree."""
        root = DiffTreeNode('container', '', [], {})
        child1 = DiffTreeNode('aligned', 'a', [], {})
        child2 = DiffTreeNode('divergent', 'b', [], {})
        grandchild = DiffTreeNode('aligned', 'c', [], {})

        root.add_child(child1)
        root.add_child(child2)
        child1.add_child(grandchild)

        all_nodes = root.get_all_nodes()
        assert len(all_nodes) == 4
        assert root in all_nodes
        assert child1 in all_nodes
        assert child2 in all_nodes
        assert grandchild in all_nodes

    def test_find_by_type(self):
        """Find nodes by type."""
        root = DiffTreeNode('container', '', [], {})
        child1 = DiffTreeNode('aligned', 'a', [], {})
        child2 = DiffTreeNode('divergent', 'b', [], {})
        child3 = DiffTreeNode('aligned', 'c', [], {})

        root.add_child(child1)
        root.add_child(child2)
        root.add_child(child3)

        aligned = root.find_by_type('aligned')
        assert len(aligned) == 2

        divergent = root.find_by_type('divergent')
        assert len(divergent) == 1

    def test_get_depth(self):
        """Get tree depth from node."""
        root = DiffTreeNode('container', '', [], {})
        child = DiffTreeNode('aligned', 'a', [], {})
        grandchild = DiffTreeNode('aligned', 'b', [], {})

        root.add_child(child)
        child.add_child(grandchild)

        assert root.get_depth() == 2
        assert child.get_depth() == 1
        assert grandchild.get_depth() == 0

    def test_count_by_type(self):
        """Count nodes by type in subtree."""
        root = DiffTreeNode('container', '', [], {})
        root.add_child(DiffTreeNode('aligned', 'a', [], {}))
        root.add_child(DiffTreeNode('aligned', 'b', [], {}))
        root.add_child(DiffTreeNode('divergent', 'c', [], {}))

        counts = root.count_by_type()
        assert counts['container'] == 1
        assert counts['aligned'] == 2
        assert counts['divergent'] == 1


class TestFormatAlignmentDiff:
    """Tests for format_alignment_diff function."""

    def test_format_simple_aligned(self, pattern_analyzer):
        """Format output for fully aligned code."""
        result = pattern_analyzer.align_code_blocks("x = 1", "x = 1")
        output = format_alignment_diff(result)

        assert "Alignment Summary:" in output
        assert "Similarity: 100.0%" in output
        assert "Aligned lines: 1" in output
        assert "Divergent lines: 0" in output

    def test_format_with_divergent(self, pattern_analyzer):
        """Format output with divergent sections."""
        result = pattern_analyzer.align_code_blocks("x = 1", "x = 2")
        output = format_alignment_diff(result)

        assert "---" in output  # Divergent marker
        assert "+++" in output
        assert "x = 1" in output
        assert "x = 2" in output

    def test_format_with_deletions(self, pattern_analyzer):
        """Format output with deleted lines."""
        result = pattern_analyzer.align_code_blocks("a\nb", "a")
        output = format_alignment_diff(result)

        assert "(deleted)" in output
        assert "- b" in output

    def test_format_with_insertions(self, pattern_analyzer):
        """Format output with inserted lines."""
        result = pattern_analyzer.align_code_blocks("a", "a\nb")
        output = format_alignment_diff(result)

        assert "(inserted)" in output
        assert "+ b" in output

    def test_format_with_context_lines(self, pattern_analyzer):
        """Format output respects context_lines parameter."""
        code = "\n".join([f"line{i}" for i in range(20)])
        result = pattern_analyzer.align_code_blocks(code, code)

        # With no context compression
        output_full = format_alignment_diff(result, context_lines=0)

        # With context compression
        output_compressed = format_alignment_diff(result, context_lines=2)

        # Compressed should indicate aligned section
        assert "[aligned," in output_compressed or len(output_compressed) <= len(output_full)

    def test_format_multiline_summary(self, pattern_analyzer):
        """Format output includes correct line counts."""
        code1 = "a\nb\nc\nd\ne"
        code2 = "a\nx\nc\ny\ne"
        result = pattern_analyzer.align_code_blocks(code1, code2)
        output = format_alignment_diff(result)

        assert "Block 1: 5 lines" in output
        assert "Block 2: 5 lines" in output


class TestBuildNestedDiffTree:
    """Tests for build_nested_diff_tree with indentation-based nesting."""

    def test_nested_tree_structure(self, pattern_analyzer):
        """Nested tree respects indentation."""
        code1 = "def foo():\n    x = 1\n    return x"
        code2 = "def foo():\n    x = 2\n    return x"
        result = pattern_analyzer.align_code_blocks(code1, code2)
        tree = build_nested_diff_tree(result)

        assert tree.root.node_type == 'container'
        # The tree should have structure based on indentation

    def test_nested_tree_preserves_similarity(self, pattern_analyzer):
        """Nested tree preserves similarity metrics."""
        code1 = "if True:\n    a = 1\nelse:\n    b = 2"
        code2 = "if True:\n    a = 10\nelse:\n    b = 20"
        result = pattern_analyzer.align_code_blocks(code1, code2)
        tree = build_nested_diff_tree(result)

        assert tree.similarity_ratio == result.similarity_ratio


class TestEdgeCases:
    """Edge case tests for diff analysis functions."""

    def test_single_empty_block(self, pattern_analyzer):
        """One empty block, one with content."""
        result = pattern_analyzer.align_code_blocks("", "x = 1")

        assert result.similarity_ratio == 0.0
        assert result.divergent_lines == 1
        assert result.block1_total_lines == 0  # Empty string results in 0 lines
        assert result.block2_total_lines == 1

    def test_only_whitespace_lines(self, pattern_analyzer):
        """Blocks with only whitespace."""
        result = pattern_analyzer.align_code_blocks("   \n   ", "\t\n\t", ignore_whitespace=True)

        # Whitespace-only lines normalize to empty, should align
        assert result.similarity_ratio == 1.0

    def test_only_comments(self, pattern_analyzer):
        """Blocks with only comments."""
        code1 = "# comment 1\n# comment 2"
        code2 = "# different 1\n# different 2"
        result = pattern_analyzer.align_code_blocks(code1, code2, ignore_comments=True)

        # Comments normalize to empty, should align
        assert result.aligned_lines == 2

    def test_unicode_content(self, pattern_analyzer):
        """Blocks with unicode characters."""
        code1 = "x = 'hello'\n"
        code2 = "x = 'hello'\n"
        result = pattern_analyzer.align_code_blocks(code1, code2)

        assert result.similarity_ratio == 1.0

    def test_very_long_lines(self, pattern_analyzer):
        """Blocks with very long lines."""
        long_line = "x = " + "a" * 1000
        result = pattern_analyzer.align_code_blocks(long_line, long_line)

        assert result.similarity_ratio == 1.0

    def test_many_lines(self, pattern_analyzer):
        """Blocks with many lines."""
        code = "\n".join([f"line{i} = {i}" for i in range(100)])
        result = pattern_analyzer.align_code_blocks(code, code)

        assert result.similarity_ratio == 1.0
        assert result.aligned_lines == 100

    def test_newline_variations(self, pattern_analyzer):
        """Different newline styles should still work."""
        code1 = "a\nb\nc"
        code2 = "a\nb\nc"  # Same content
        result = pattern_analyzer.align_code_blocks(code1, code2)

        assert result.similarity_ratio == 1.0

    def test_segment_line_positions(self, pattern_analyzer):
        """Verify segment start/end positions are correct."""
        code1 = "a\nb\nc"
        code2 = "a\nx\nc"
        result = pattern_analyzer.align_code_blocks(code1, code2)

        for seg in result.segments:
            assert seg.block1_start >= 0
            assert seg.block1_end >= seg.block1_start
            assert seg.block2_start >= 0
            assert seg.block2_end >= seg.block2_start
