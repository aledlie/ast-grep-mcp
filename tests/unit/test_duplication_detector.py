"""Tests for DuplicationDetector - core duplication detection functionality.

Tests cover:
- Initialization with different similarity modes
- Parameter validation
- Construct pattern generation for multiple languages
- Similarity calculation (hybrid, minhash, sequence_matcher)
- Code normalization
- Duplicate grouping and bucket creation
- Group merging
- Refactoring suggestion generation
- Statistics calculation
- Result formatting
"""

import tempfile
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from ast_grep_mcp.features.deduplication.detector import (
    DuplicationDetector,
)


class TestDuplicationDetectorInit:
    """Tests for DuplicationDetector initialization."""

    def test_init_default_values(self):
        """Test initialization with default values."""
        detector = DuplicationDetector()

        assert detector.language == "python"
        assert detector.similarity_mode == "hybrid"
        assert detector.use_minhash is True
        assert detector.logger is not None

    def test_init_with_language(self):
        """Test initialization with specific language."""
        detector = DuplicationDetector(language="javascript")

        assert detector.language == "javascript"

    def test_init_with_minhash_mode(self):
        """Test initialization with minhash mode."""
        detector = DuplicationDetector(similarity_mode="minhash")

        assert detector.similarity_mode == "minhash"
        assert detector.use_minhash is True

    def test_init_with_sequence_matcher_mode(self):
        """Test initialization with sequence_matcher mode."""
        detector = DuplicationDetector(similarity_mode="sequence_matcher")

        assert detector.similarity_mode == "sequence_matcher"
        assert detector.use_minhash is False

    def test_init_legacy_use_minhash_false(self):
        """Test that legacy use_minhash=False sets sequence_matcher mode."""
        detector = DuplicationDetector(use_minhash=False)

        assert detector.similarity_mode == "sequence_matcher"
        assert detector.use_minhash is False

    def test_init_creates_similarity_calculators(self):
        """Test that similarity calculators are created."""
        detector = DuplicationDetector()

        assert detector._minhash is not None
        assert detector._hybrid is not None
        assert detector._structure_hash is not None


class TestValidateParameters:
    """Tests for _validate_parameters method."""

    def test_valid_parameters(self):
        """Test that valid parameters pass validation."""
        detector = DuplicationDetector()

        # Should not raise
        detector._validate_parameters(0.8, 5, 100)

    def test_min_similarity_below_zero(self):
        """Test that min_similarity below 0 raises ValueError."""
        detector = DuplicationDetector()

        with pytest.raises(ValueError, match="min_similarity must be between"):
            detector._validate_parameters(-0.1, 5, 100)

    def test_min_similarity_above_one(self):
        """Test that min_similarity above 1 raises ValueError."""
        detector = DuplicationDetector()

        with pytest.raises(ValueError, match="min_similarity must be between"):
            detector._validate_parameters(1.5, 5, 100)

    def test_min_lines_below_one(self):
        """Test that min_lines below 1 raises ValueError."""
        detector = DuplicationDetector()

        with pytest.raises(ValueError, match="min_lines must be at least"):
            detector._validate_parameters(0.8, 0, 100)

    def test_max_constructs_negative(self):
        """Test that negative max_constructs raises ValueError."""
        detector = DuplicationDetector()

        with pytest.raises(ValueError, match="max_constructs must be"):
            detector._validate_parameters(0.8, 5, -1)

    def test_max_constructs_zero_allowed(self):
        """Test that max_constructs=0 (unlimited) is allowed."""
        detector = DuplicationDetector()

        # Should not raise
        detector._validate_parameters(0.8, 5, 0)


class TestGetConstructPattern:
    """Tests for _get_construct_pattern method."""

    def test_python_function_pattern(self):
        """Test Python function pattern."""
        detector = DuplicationDetector(language="python")

        pattern = detector._get_construct_pattern("function_definition")

        assert "def $NAME" in pattern

    def test_python_class_pattern(self):
        """Test Python class pattern."""
        detector = DuplicationDetector(language="python")

        pattern = detector._get_construct_pattern("class_definition")

        assert "class $NAME" in pattern

    def test_javascript_function_pattern(self):
        """Test JavaScript function pattern."""
        detector = DuplicationDetector(language="javascript")

        pattern = detector._get_construct_pattern("function_definition")

        assert "const $NAME" in pattern

    def test_typescript_function_pattern(self):
        """Test TypeScript function pattern."""
        detector = DuplicationDetector(language="typescript")

        pattern = detector._get_construct_pattern("function_definition")

        assert "const $NAME" in pattern

    def test_javascript_arrow_function_pattern(self):
        """Test JavaScript arrow function pattern."""
        detector = DuplicationDetector(language="javascript")

        pattern = detector._get_construct_pattern("arrow_function")

        assert "=>" in pattern

    def test_javascript_traditional_function_pattern(self):
        """Test JavaScript traditional function pattern."""
        detector = DuplicationDetector(language="javascript")

        pattern = detector._get_construct_pattern("traditional_function")

        assert "function $NAME" in pattern

    def test_javascript_method_pattern(self):
        """Test JavaScript method pattern."""
        detector = DuplicationDetector(language="javascript")

        pattern = detector._get_construct_pattern("method_definition")

        assert "$NAME($$$)" in pattern

    def test_java_function_pattern(self):
        """Test Java function pattern."""
        detector = DuplicationDetector(language="java")

        pattern = detector._get_construct_pattern("function_definition")

        assert "$TYPE $NAME" in pattern

    def test_csharp_function_pattern(self):
        """Test C# function pattern."""
        detector = DuplicationDetector(language="csharp")

        pattern = detector._get_construct_pattern("function_definition")

        assert "$TYPE $NAME" in pattern

    def test_unknown_construct_fallback(self):
        """Test that unknown construct type falls back to function_definition."""
        detector = DuplicationDetector(language="python")

        pattern = detector._get_construct_pattern("unknown_type")

        assert "def $NAME" in pattern

    def test_jsx_uses_javascript_patterns(self):
        """Test that JSX uses JavaScript patterns."""
        detector = DuplicationDetector(language="jsx")

        pattern = detector._get_construct_pattern("function_definition")

        assert "const $NAME" in pattern

    def test_tsx_uses_javascript_patterns(self):
        """Test that TSX uses JavaScript patterns."""
        detector = DuplicationDetector(language="tsx")

        pattern = detector._get_construct_pattern("function_definition")

        assert "const $NAME" in pattern


class TestCalculateSimilarity:
    """Tests for calculate_similarity method."""

    def test_empty_code_returns_zero(self):
        """Test that empty code returns 0.0 similarity."""
        detector = DuplicationDetector()

        assert detector.calculate_similarity("", "def func(): pass") == 0.0
        assert detector.calculate_similarity("def func(): pass", "") == 0.0
        assert detector.calculate_similarity("", "") == 0.0

    def test_identical_code_high_similarity(self):
        """Test that identical code has high similarity."""
        detector = DuplicationDetector()

        code = "def func():\n    return 42"
        similarity = detector.calculate_similarity(code, code)

        assert similarity >= 0.9

    def test_different_code_low_similarity(self):
        """Test that very different code has low similarity."""
        detector = DuplicationDetector()

        code1 = "def func1(): return 1"
        code2 = "class MyClass: pass"

        similarity = detector.calculate_similarity(code1, code2)

        assert similarity < 0.5

    def test_hybrid_mode_uses_hybrid(self):
        """Test that hybrid mode uses hybrid calculator."""
        detector = DuplicationDetector(similarity_mode="hybrid")

        with patch.object(detector._hybrid, "estimate_similarity", return_value=0.85) as mock:
            result = detector.calculate_similarity("code1", "code2")

            mock.assert_called_once_with("code1", "code2")
            assert result == 0.85

    def test_minhash_mode_uses_minhash(self):
        """Test that minhash mode uses minhash calculator."""
        detector = DuplicationDetector(similarity_mode="minhash")

        with patch.object(detector._minhash, "estimate_similarity", return_value=0.75) as mock:
            result = detector.calculate_similarity("code1", "code2")

            mock.assert_called_once_with("code1", "code2")
            assert result == 0.75

    def test_sequence_matcher_mode(self):
        """Test sequence_matcher mode uses SequenceMatcher."""
        detector = DuplicationDetector(similarity_mode="sequence_matcher")

        code1 = "def func(): return 1"
        code2 = "def func(): return 1"

        similarity = detector.calculate_similarity(code1, code2)

        assert similarity >= 0.9


class TestCalculateSimilarityPrecise:
    """Tests for calculate_similarity_precise method."""

    def test_empty_code_returns_zero(self):
        """Test that empty code returns 0.0."""
        detector = DuplicationDetector()

        assert detector.calculate_similarity_precise("", "code") == 0.0
        assert detector.calculate_similarity_precise("code", "") == 0.0

    def test_identical_code_returns_one(self):
        """Test that identical code returns 1.0."""
        detector = DuplicationDetector()

        code = "def func(): return 42"

        assert detector.calculate_similarity_precise(code, code) == 1.0


class TestCalculateSimilarityDetailed:
    """Tests for calculate_similarity_detailed method."""

    def test_returns_hybrid_result(self):
        """Test that detailed calculation returns HybridSimilarityResult."""
        detector = DuplicationDetector()

        result = detector.calculate_similarity_detailed("def func1(): return 1", "def func2(): return 2")

        # Should return a result with similarity attribute
        assert hasattr(result, "similarity")
        assert 0.0 <= result.similarity <= 1.0


class TestNormalizeCode:
    """Tests for _normalize_code method."""

    def test_removes_empty_lines(self):
        """Test that empty lines are removed."""
        detector = DuplicationDetector()

        code = "def func():\n\n    return 1"
        normalized = detector._normalize_code(code)

        assert "\n\n" not in normalized

    def test_strips_trailing_whitespace(self):
        """Test that trailing whitespace is stripped."""
        detector = DuplicationDetector()

        code = "def func():   \n    return 1   "
        normalized = detector._normalize_code(code)

        assert not any(line.endswith(" ") for line in normalized.split("\n"))

    def test_normalizes_indentation(self):
        """Test that deep indentation is normalized."""
        detector = DuplicationDetector()

        code = "        deeply_indented()"
        normalized = detector._normalize_code(code)

        # Should have max 4 spaces of indentation
        indent = len(normalized) - len(normalized.lstrip())
        assert indent <= 4


class TestGroupDuplicates:
    """Tests for group_duplicates method."""

    def test_empty_matches_returns_empty(self):
        """Test that empty matches returns empty list."""
        detector = DuplicationDetector()

        result = detector.group_duplicates([], 0.8, 5)

        assert result == []

    def test_filters_by_min_lines(self):
        """Test that matches below min_lines are filtered."""
        detector = DuplicationDetector()

        matches = [
            {"text": "a\nb\nc", "file": "f1.py", "range": {"start": {"line": 1}}},  # 3 lines
            {"text": "a\nb\nc\nd\ne", "file": "f2.py", "range": {"start": {"line": 1}}},  # 5 lines
        ]

        result = detector.group_duplicates(matches, 0.8, 5)

        # Only one match >= 5 lines, so no groups
        assert result == []

    def test_groups_similar_code(self):
        """Test that similar code is grouped together."""
        detector = DuplicationDetector()

        code = "def func():\n    x = 1\n    y = 2\n    z = 3\n    return x + y + z"
        matches = [
            {"text": code, "file": "f1.py", "range": {"start": {"line": 1}}},
            {"text": code, "file": "f2.py", "range": {"start": {"line": 10}}},
        ]

        result = detector.group_duplicates(matches, 0.8, 3)

        assert len(result) == 1
        assert len(result[0]) == 2


class TestCreateHashBuckets:
    """Tests for _create_hash_buckets method."""

    def test_creates_buckets(self):
        """Test that hash buckets are created."""
        detector = DuplicationDetector()

        matches = [
            {"text": "def func1(): pass", "file": "f1.py"},
            {"text": "def func2(): pass", "file": "f2.py"},
        ]

        buckets = detector._create_hash_buckets(matches)

        assert isinstance(buckets, dict)
        # All matches should be in some bucket
        total_in_buckets = sum(len(b) for b in buckets.values())
        assert total_in_buckets == 2


class TestCalculateStructureHash:
    """Tests for _calculate_structure_hash method."""

    def test_returns_integer(self):
        """Test that hash is an integer."""
        detector = DuplicationDetector()

        hash_val = detector._calculate_structure_hash("def func(): pass")

        assert isinstance(hash_val, int)

    def test_similar_code_same_bucket(self):
        """Test that similar code gets similar hashes."""
        detector = DuplicationDetector()

        code1 = "def func1():\n    return 1"
        code2 = "def func2():\n    return 2"

        hash1 = detector._calculate_structure_hash(code1)
        hash2 = detector._calculate_structure_hash(code2)

        # Similar structure should have same hash
        assert hash1 == hash2


class TestFindSimilarInBucket:
    """Tests for _find_similar_in_bucket method."""

    def test_finds_similar_items(self):
        """Test finding similar items in bucket."""
        detector = DuplicationDetector()

        code = "def func():\n    x = 1\n    return x"
        bucket = [
            {"text": code, "file": "f1.py", "range": {"start": {"line": 1}}},
            {"text": code, "file": "f2.py", "range": {"start": {"line": 1}}},
        ]

        groups = detector._find_similar_in_bucket(bucket, 0.8)

        assert len(groups) == 1
        assert len(groups[0]) == 2

    def test_skips_dissimilar_items(self):
        """Test that dissimilar items are not grouped."""
        detector = DuplicationDetector()

        bucket = [
            {"text": "def func1(): pass", "file": "f1.py", "range": {"start": {"line": 1}}},
            {"text": "class MyClass:\n    x = 1\n    y = 2", "file": "f2.py", "range": {"start": {"line": 1}}},
        ]

        groups = detector._find_similar_in_bucket(bucket, 0.9)

        assert len(groups) == 0


class TestItemHelpers:
    """Tests for item helper methods."""

    def test_get_item_key(self):
        """Test _get_item_key generates unique key."""
        detector = DuplicationDetector()

        item = {"file": "/path/to/file.py", "range": {"start": {"line": 10}}}
        key = detector._get_item_key(item)

        assert key == "/path/to/file.py:10"

    def test_items_equal_same_items(self):
        """Test _items_equal returns True for same items."""
        detector = DuplicationDetector()

        item1 = {"file": "f.py", "range": {"start": {"line": 5}}}
        item2 = {"file": "f.py", "range": {"start": {"line": 5}}}

        assert detector._items_equal(item1, item2) is True

    def test_items_equal_different_items(self):
        """Test _items_equal returns False for different items."""
        detector = DuplicationDetector()

        item1 = {"file": "f.py", "range": {"start": {"line": 5}}}
        item2 = {"file": "f.py", "range": {"start": {"line": 10}}}

        assert detector._items_equal(item1, item2) is False


class TestMergeOverlappingGroups:
    """Tests for _merge_overlapping_groups method."""

    def test_empty_groups(self):
        """Test that empty groups returns empty list."""
        detector = DuplicationDetector()

        result = detector._merge_overlapping_groups([])

        assert result == []

    def test_merges_overlapping_groups(self):
        """Test that overlapping groups are merged."""
        detector = DuplicationDetector()

        item1 = {"file": "f1.py", "range": {"start": {"line": 1}}}
        item2 = {"file": "f2.py", "range": {"start": {"line": 1}}}
        item3 = {"file": "f3.py", "range": {"start": {"line": 1}}}

        # Group 1: item1, item2
        # Group 2: item2, item3
        # Should merge into one group with all three
        groups = [
            [item1, item2],
            [item2, item3],
        ]

        result = detector._merge_overlapping_groups(groups)

        assert len(result) == 1
        assert len(result[0]) == 3

    def test_keeps_separate_groups(self):
        """Test that non-overlapping groups stay separate."""
        detector = DuplicationDetector()

        groups = [
            [
                {"file": "f1.py", "range": {"start": {"line": 1}}},
                {"file": "f2.py", "range": {"start": {"line": 1}}},
            ],
            [
                {"file": "f3.py", "range": {"start": {"line": 1}}},
                {"file": "f4.py", "range": {"start": {"line": 1}}},
            ],
        ]

        result = detector._merge_overlapping_groups(groups)

        assert len(result) == 2


class TestBuildItemToGroupsMap:
    """Tests for _build_item_to_groups_map method."""

    def test_builds_mapping(self):
        """Test that mapping is built correctly."""
        detector = DuplicationDetector()

        groups = [
            [{"file": "f1.py", "range": {"start": {"line": 1}}}],
            [{"file": "f2.py", "range": {"start": {"line": 1}}}],
        ]

        mapping = detector._build_item_to_groups_map(groups)

        assert "f1.py:1" in mapping
        assert "f2.py:1" in mapping


class TestAddUniqueItems:
    """Tests for _add_unique_items method."""

    def test_adds_unique_items(self):
        """Test that unique items are added."""
        detector = DuplicationDetector()

        target: List[Dict[str, Any]] = []
        source = [
            {"file": "f1.py", "range": {"start": {"line": 1}}},
            {"file": "f2.py", "range": {"start": {"line": 1}}},
        ]

        detector._add_unique_items(target, source)

        assert len(target) == 2

    def test_skips_duplicates(self):
        """Test that duplicates are not added."""
        detector = DuplicationDetector()

        item = {"file": "f1.py", "range": {"start": {"line": 1}}}
        target = [item]
        source = [item, {"file": "f2.py", "range": {"start": {"line": 1}}}]

        detector._add_unique_items(target, source)

        assert len(target) == 2


class TestGenerateRefactoringSuggestions:
    """Tests for generate_refactoring_suggestions method."""

    def test_empty_groups_returns_empty(self):
        """Test that empty groups returns empty suggestions."""
        detector = DuplicationDetector()

        result = detector.generate_refactoring_suggestions([], "function_definition")

        assert result == []

    def test_single_item_groups_skipped(self):
        """Test that single-item groups are skipped."""
        detector = DuplicationDetector()

        groups = [[{"text": "def func(): pass", "file": "f.py", "range": {"start": {"line": 1}}}]]

        result = detector.generate_refactoring_suggestions(groups, "function_definition")

        assert result == []

    def test_generates_suggestions(self):
        """Test that suggestions are generated for valid groups."""
        detector = DuplicationDetector()

        code = "def func():\n    return 1"
        groups = [
            [
                {"text": code, "file": "f1.py", "range": {"start": {"line": 1}}},
                {"text": code, "file": "f2.py", "range": {"start": {"line": 10}}},
            ]
        ]

        result = detector.generate_refactoring_suggestions(groups, "function_definition")

        assert len(result) == 1
        assert result[0]["duplicate_count"] == 2
        assert result[0]["lines_per_duplicate"] == 2
        assert "refactoring_strategy" in result[0]


class TestDetermineRefactoringStrategy:
    """Tests for _determine_refactoring_strategy method."""

    def test_small_function_extract_utility(self):
        """Test that small functions suggest extract utility."""
        detector = DuplicationDetector()

        group = [{"text": "def f():\n    return 1"}]  # 2 lines

        strategy = detector._determine_refactoring_strategy(group, "function_definition")

        assert strategy["type"] == "extract_utility_function"

    def test_large_function_extract_module(self):
        """Test that large functions suggest extract module."""
        detector = DuplicationDetector()

        # Create code with 15 lines
        lines = ["def func():"] + ["    x = 1"] * 14
        code = "\n".join(lines)
        group = [{"text": code}]

        strategy = detector._determine_refactoring_strategy(group, "function_definition")

        assert strategy["type"] == "extract_module"

    def test_class_extract_base_class(self):
        """Test that classes suggest extract base class."""
        detector = DuplicationDetector()

        group = [{"text": "class MyClass:\n    pass"}]

        strategy = detector._determine_refactoring_strategy(group, "class_definition")

        assert strategy["type"] == "extract_base_class"

    def test_method_extract_method(self):
        """Test that methods suggest extract method."""
        detector = DuplicationDetector()

        group = [{"text": "def method():\n    pass"}]

        strategy = detector._determine_refactoring_strategy(group, "method_definition")

        assert strategy["type"] == "extract_method"


class TestCalculateStatistics:
    """Tests for _calculate_statistics method."""

    def test_calculates_statistics(self):
        """Test that statistics are calculated correctly."""
        detector = DuplicationDetector()

        all_matches = [{"file": "f1.py"}, {"file": "f2.py"}]
        duplication_groups = [[{}, {}]]
        suggestions = [{"total_duplicated_lines": 20, "potential_line_savings": 10}]

        stats = detector._calculate_statistics(all_matches, duplication_groups, suggestions)

        assert stats["total_constructs"] == 2
        assert stats["duplicate_groups"] == 1
        assert stats["total_duplicated_lines"] == 20
        assert stats["potential_line_savings"] == 10


class TestEmptyResult:
    """Tests for _empty_result method."""

    def test_returns_empty_result_structure(self):
        """Test that empty result has correct structure."""
        detector = DuplicationDetector()

        result = detector._empty_result("function_definition", 1.5)

        assert result["summary"]["total_constructs"] == 0
        assert result["summary"]["duplicate_groups"] == 0
        assert result["duplication_groups"] == []
        assert result["refactoring_suggestions"] == []
        assert "function_definition" in result["message"]


class TestFormatResult:
    """Tests for _format_result method."""

    def test_formats_result(self):
        """Test that result is formatted correctly."""
        detector = DuplicationDetector()

        code = "def func(): pass"
        all_matches = [{"file": "f1.py"}]
        duplication_groups = [
            [
                {"file": "f1.py", "range": {"start": {"line": 0}, "end": {"line": 1}}, "text": code},
                {"file": "f2.py", "range": {"start": {"line": 5}, "end": {"line": 6}}, "text": code},
            ]
        ]
        suggestions = [{"group_id": 1, "potential_line_savings": 5}]
        stats = {"total_constructs": 1, "duplicate_groups": 1, "total_duplicated_lines": 10, "potential_line_savings": 5}

        result = detector._format_result(all_matches, duplication_groups, suggestions, stats, 0.5)

        assert "summary" in result
        assert "duplication_groups" in result
        assert "refactoring_suggestions" in result
        assert "message" in result
        assert result["summary"]["analysis_time_seconds"] == 0.5

    def test_formats_group_instances(self):
        """Test that group instances are formatted with file and line info."""
        detector = DuplicationDetector()

        code = "def func(): pass"
        groups = [
            [
                {"file": "/path/f1.py", "range": {"start": {"line": 9}, "end": {"line": 10}}, "text": code},
                {"file": "/path/f2.py", "range": {"start": {"line": 19}, "end": {"line": 20}}, "text": code},
            ]
        ]

        stats = {"total_constructs": 0, "duplicate_groups": 1, "total_duplicated_lines": 0, "potential_line_savings": 0}
        result = detector._format_result([], groups, [], stats, 0.1)

        assert len(result["duplication_groups"]) == 1
        assert len(result["duplication_groups"][0]["instances"]) == 2
        assert result["duplication_groups"][0]["instances"][0]["file"] == "/path/f1.py"
        assert result["duplication_groups"][0]["instances"][0]["lines"] == "10-11"


class TestFindDuplication:
    """Tests for find_duplication method."""

    def test_empty_project_returns_empty_result(self):
        """Test that empty project returns empty result."""
        detector = DuplicationDetector()

        with patch("ast_grep_mcp.features.deduplication.detector.stream_ast_grep_results") as mock_stream:
            mock_stream.return_value = iter([])

            with tempfile.TemporaryDirectory() as tmpdir:
                result = detector.find_duplication(tmpdir)

            assert result["summary"]["total_constructs"] == 0
            assert result["duplication_groups"] == []

    def test_filters_excluded_patterns(self):
        """Test that excluded patterns are filtered."""
        detector = DuplicationDetector()

        code = "def f():\n    pass\n    pass\n    pass\n    pass"
        matches = [
            {"file": "/project/src/main.py", "text": code, "range": {"start": {"line": 1}}},
            {"file": "/project/node_modules/lib.py", "text": code, "range": {"start": {"line": 1}}},
        ]

        with patch("ast_grep_mcp.features.deduplication.detector.stream_ast_grep_results") as mock_stream:
            mock_stream.return_value = iter(matches)

            with tempfile.TemporaryDirectory() as tmpdir:
                result = detector.find_duplication(tmpdir, exclude_patterns=["node_modules"])

            # node_modules file should be excluded
            assert result["summary"]["total_constructs"] == 1

    def test_propagates_exceptions(self):
        """Test that exceptions are propagated."""
        detector = DuplicationDetector()

        with patch("ast_grep_mcp.features.deduplication.detector.stream_ast_grep_results") as mock_stream:
            mock_stream.side_effect = RuntimeError("Test error")

            with pytest.raises(RuntimeError, match="Test error"):
                with tempfile.TemporaryDirectory() as tmpdir:
                    detector.find_duplication(tmpdir)


class TestProcessGroupConnections:
    """Tests for _process_group_connections method."""

    def test_processes_connections(self):
        """Test that group connections are processed."""
        detector = DuplicationDetector()

        item1 = {"file": "f1.py", "range": {"start": {"line": 1}}}
        item2 = {"file": "f2.py", "range": {"start": {"line": 1}}}

        groups = [[item1, item2]]
        item_to_groups = {
            "f1.py:1": [0],
            "f2.py:1": [0],
        }
        used_groups: set[int] = {0}
        to_merge: list[int] = []
        merged_group: list[Dict[str, Any]] = []

        detector._process_group_connections(0, groups, item_to_groups, used_groups, to_merge, merged_group)

        # No new groups to merge since group 0 is already used
        assert len(to_merge) == 0


class TestEdgeCases:
    """Tests for edge cases to improve coverage."""

    def test_javascript_unknown_construct_default(self):
        """Test that unknown JS construct type defaults to const pattern."""
        detector = DuplicationDetector(language="javascript")

        pattern = detector._get_construct_pattern("unknown_custom_type")

        assert "const $NAME" in pattern

    def test_group_duplicates_all_below_min_lines(self):
        """Test group_duplicates when all matches are below min_lines."""
        detector = DuplicationDetector()

        # All matches have 2 lines, but min_lines is 5
        matches = [
            {"text": "line1\nline2", "file": "f1.py", "range": {"start": {"line": 1}}},
            {"text": "line1\nline2", "file": "f2.py", "range": {"start": {"line": 1}}},
        ]

        result = detector.group_duplicates(matches, 0.8, 5)

        assert result == []

    def test_find_similar_in_bucket_skips_used_items(self):
        """Test that _find_similar_in_bucket skips already used items."""
        detector = DuplicationDetector()

        code = "def func():\n    x = 1\n    y = 2\n    return x + y"
        # Create 3 items where all are similar
        bucket = [
            {"text": code, "file": "f1.py", "range": {"start": {"line": 1}}},
            {"text": code, "file": "f2.py", "range": {"start": {"line": 1}}},
            {"text": code, "file": "f3.py", "range": {"start": {"line": 1}}},
        ]

        groups = detector._find_similar_in_bucket(bucket, 0.8)

        # Should create one group with all 3 items
        assert len(groups) == 1
        assert len(groups[0]) == 3

    def test_find_constructs_logs_limit_reached(self):
        """Test that _find_constructs logs when limit is reached."""
        detector = DuplicationDetector()

        # Create exactly max_constructs matches
        matches = [{"file": f"/project/f{i}.py", "text": f"def func{i}(): pass", "range": {"start": {"line": 1}}} for i in range(5)]

        with patch("ast_grep_mcp.features.deduplication.detector.stream_ast_grep_results") as mock_stream:
            mock_stream.return_value = iter(matches)

            with tempfile.TemporaryDirectory() as tmpdir:
                result = detector._find_constructs(tmpdir, "def $NAME($$$)", 5, [])

            # Should have all 5 matches
            assert len(result) == 5

    def test_find_similar_in_bucket_inner_loop_continue(self):
        """Test that inner loop skips already used items (line 411).

        Scenario: 3 items where item1 and item3 are similar but item2 is different.
        - Processing item1 (i=0): matches item3, adds index 2 to used
        - Processing item2 (i=1): different from others, inner loop iterates to j=2
        - Since j=2 is in used, the inner loop continue (line 411) is hit
        """
        detector = DuplicationDetector()

        code_a = "def calculate():\n    x = 1\n    y = 2\n    z = 3\n    return x + y + z"
        code_b = "class Completely:\n    different = True\n    structure = False"
        code_c = "def calculate():\n    x = 1\n    y = 2\n    z = 3\n    return x + y + z"

        bucket = [
            {"text": code_a, "file": "f1.py", "range": {"start": {"line": 1}}},
            {"text": code_b, "file": "f2.py", "range": {"start": {"line": 1}}},
            {"text": code_c, "file": "f3.py", "range": {"start": {"line": 1}}},
        ]

        groups = detector._find_similar_in_bucket(bucket, 0.8)

        # Should create one group with items 1 and 3 (code_a and code_c)
        assert len(groups) == 1
        assert len(groups[0]) == 2
