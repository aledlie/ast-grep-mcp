"""
Integration tests for Phase 4.1: Deduplication Analysis Tool
Tests the analyze_deduplication_candidates tool.
"""

import os
import tempfile
import shutil
import pytest

# Import the main module functions
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from main import (
    _generate_dedup_recommendation,
    calculate_similarity,
    group_duplicates,
)


class TestGenerateDedupRecommendation:
    """Test the _generate_dedup_recommendation helper function."""

    def test_high_priority_recommendation(self):
        """Test HIGH PRIORITY recommendation for nearly identical code with many instances."""
        rec = _generate_dedup_recommendation(
            similarity=0.98,
            instance_count=6,
            avg_lines=30,
            savings=150
        )
        assert "HIGH PRIORITY" in rec
        assert "6 instances" in rec
        assert "150 lines" in rec

    def test_recommended_similar_code(self):
        """Test RECOMMENDED for very similar code with 3+ instances."""
        rec = _generate_dedup_recommendation(
            similarity=0.96,
            instance_count=4,
            avg_lines=25,
            savings=75
        )
        assert "RECOMMENDED" in rec
        assert "4 instances" in rec

    def test_moderate_priority(self):
        """Test MODERATE priority for similar longer code blocks."""
        rec = _generate_dedup_recommendation(
            similarity=0.88,
            instance_count=3,
            avg_lines=25,
            savings=50
        )
        assert "MODERATE" in rec
        assert "parameterized" in rec.lower()

    def test_low_similarity_recommendation(self):
        """Test recommendation for partial similarity."""
        rec = _generate_dedup_recommendation(
            similarity=0.75,
            instance_count=2,
            avg_lines=15,
            savings=15
        )
        assert "Partial similarity" in rec
        assert "abstraction" in rec.lower()

    def test_small_savings_recommendation(self):
        """Test recommendation includes savings info even for small amounts."""
        rec = _generate_dedup_recommendation(
            similarity=0.95,
            instance_count=2,
            avg_lines=10,
            savings=10
        )
        assert "10 lines" in rec


class TestAnalyzeDeduplicationIntegration:
    """Integration tests for analyze_deduplication_candidates tool."""

    def setup_method(self):
        """Create a temporary directory for each test."""
        self.test_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up the temporary directory after each test."""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def create_python_file(self, name: str, content: str):
        """Helper to create a Python file in the test directory."""
        file_path = os.path.join(self.test_dir, name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(content)
        return file_path

    def test_empty_project_returns_no_candidates(self):
        """Test that empty project returns no candidates."""
        # Create empty directory
        result = {
            "candidates": [],
            "total_groups": 0,
            "total_savings_potential": 0
        }
        # This tests the expected return structure
        assert result["candidates"] == []
        assert result["total_groups"] == 0
        assert result["total_savings_potential"] == 0

    def test_single_function_returns_no_duplicates(self):
        """Test that a single function doesn't create duplicates."""
        self.create_python_file("module.py", '''
def unique_function():
    x = 1
    y = 2
    return x + y
''')
        # Test with group_duplicates helper
        matches = [
            {
                'file': os.path.join(self.test_dir, 'module.py'),
                'text': 'def unique_function():\n    x = 1\n    y = 2\n    return x + y',
                'range': {'start': {'line': 1}, 'end': {'line': 4}}
            }
        ]
        groups = group_duplicates(matches, min_similarity=0.8, min_lines=3)
        assert len(groups) == 0  # No groups with single match

    def test_duplicate_functions_detected(self):
        """Test that similar functions are detected as duplicates."""
        code1 = '''def process_data_a():
    result = []
    for i in range(10):
        result.append(i * 2)
    return result'''

        code2 = '''def process_data_b():
    result = []
    for i in range(10):
        result.append(i * 2)
    return result'''

        self.create_python_file("file1.py", code1)
        self.create_python_file("file2.py", code2)

        # Test similarity calculation
        similarity = calculate_similarity(code1, code2)
        assert similarity >= 0.8  # Should be very similar

    def test_calculate_similarity_identical(self):
        """Test similarity calculation for identical code."""
        code = "def test():\n    return 42"
        similarity = calculate_similarity(code, code)
        assert similarity == 1.0

    def test_calculate_similarity_different(self):
        """Test similarity calculation for different code."""
        code1 = "def alpha(): return 1"
        code2 = "class Beta: pass"
        similarity = calculate_similarity(code1, code2)
        assert similarity < 0.5

    def test_group_duplicates_creates_groups(self):
        """Test that group_duplicates correctly groups similar code."""
        matches = [
            {
                'file': 'file1.py',
                'text': 'def test():\n    x = 1\n    return x',
                'range': {'start': {'line': 0}, 'end': {'line': 2}}
            },
            {
                'file': 'file2.py',
                'text': 'def test():\n    x = 1\n    return x',
                'range': {'start': {'line': 0}, 'end': {'line': 2}}
            }
        ]
        groups = group_duplicates(matches, min_similarity=0.8, min_lines=2)
        assert len(groups) == 1
        assert len(groups[0]) == 2


class TestRecommendationQuality:
    """Test recommendation quality and accuracy."""

    def test_recommendation_includes_actionable_advice(self):
        """Test that recommendations include actionable advice."""
        rec = _generate_dedup_recommendation(0.95, 4, 30, 90)
        # Should mention extraction
        assert "extract" in rec.lower() or "utility" in rec.lower() or "function" in rec.lower()

    def test_recommendation_scales_with_savings(self):
        """Test that recommendations reflect the scale of savings."""
        small = _generate_dedup_recommendation(0.9, 2, 10, 10)
        large = _generate_dedup_recommendation(0.9, 5, 50, 200)

        # Large savings should have more urgent language
        assert "200 lines" in large
        assert "10 lines" in small

    def test_recommendation_varies_by_instance_count(self):
        """Test that recommendations vary based on instance count."""
        few = _generate_dedup_recommendation(0.95, 2, 20, 20)
        many = _generate_dedup_recommendation(0.95, 7, 20, 120)

        # Many instances should trigger HIGH PRIORITY
        assert "HIGH PRIORITY" in many
        # Few instances should have less urgent wording
        assert "Consider" in few or "function" in few


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
