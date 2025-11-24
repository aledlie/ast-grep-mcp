"""Unit tests for Phase 4.5: Recommendation Engine for Deduplication Analysis."""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from main import generate_deduplication_recommendation, _generate_refactoring_strategies


class TestGenerateDeduplicationRecommendation:
    """Tests for the main recommendation generation function."""

    def test_high_value_recommendation(self):
        """Score > 80 should generate high value recommendation."""
        result = generate_deduplication_recommendation(
            score=85,
            complexity=5,
            lines_saved=20,
            has_tests=True,
            affected_files=3
        )

        assert result["recommendation_text"] == "High Value: Extract to shared utility"
        assert result["priority"] == "high"
        assert "strategies" in result
        assert len(result["strategies"]) == 3
        assert result["effort_value_ratio"] > 0

    def test_medium_value_recommendation(self):
        """Score 50-80 should generate medium value recommendation."""
        result = generate_deduplication_recommendation(
            score=65,
            complexity=7,
            lines_saved=15,
            has_tests=True,
            affected_files=2
        )

        assert result["recommendation_text"] == "Medium Value: Consider refactoring"
        assert result["priority"] == "medium"

    def test_low_value_recommendation(self):
        """Score < 50 should generate low value recommendation."""
        result = generate_deduplication_recommendation(
            score=35,
            complexity=3,
            lines_saved=5,
            has_tests=False,
            affected_files=1
        )

        assert result["recommendation_text"] == "Low Value: May not be worth refactoring"
        assert result["priority"] == "low"

    def test_boundary_score_80(self):
        """Score of exactly 80 should be medium value."""
        result = generate_deduplication_recommendation(
            score=80,
            complexity=5,
            lines_saved=10,
            has_tests=True,
            affected_files=2
        )

        assert result["priority"] == "medium"

    def test_boundary_score_50(self):
        """Score of exactly 50 should be medium value."""
        result = generate_deduplication_recommendation(
            score=50,
            complexity=5,
            lines_saved=10,
            has_tests=True,
            affected_files=2
        )

        assert result["priority"] == "medium"

    def test_boundary_score_49(self):
        """Score of 49 should be low value."""
        result = generate_deduplication_recommendation(
            score=49,
            complexity=5,
            lines_saved=10,
            has_tests=True,
            affected_files=2
        )

        assert result["priority"] == "low"

    def test_effort_value_ratio_increases_with_value(self):
        """Higher lines_saved and affected_files should increase ratio."""
        low_value = generate_deduplication_recommendation(
            score=60, complexity=5, lines_saved=5, has_tests=True, affected_files=1
        )
        high_value = generate_deduplication_recommendation(
            score=60, complexity=5, lines_saved=50, has_tests=True, affected_files=5
        )

        assert high_value["effort_value_ratio"] > low_value["effort_value_ratio"]

    def test_no_tests_increases_effort(self):
        """Missing tests should reduce effort/value ratio."""
        with_tests = generate_deduplication_recommendation(
            score=60, complexity=5, lines_saved=20, has_tests=True, affected_files=2
        )
        without_tests = generate_deduplication_recommendation(
            score=60, complexity=5, lines_saved=20, has_tests=False, affected_files=2
        )

        assert with_tests["effort_value_ratio"] > without_tests["effort_value_ratio"]

    def test_strategies_sorted_by_suitability(self):
        """Strategies should be sorted by suitability_score descending."""
        result = generate_deduplication_recommendation(
            score=75, complexity=5, lines_saved=15, has_tests=True, affected_files=3
        )

        strategies = result["strategies"]
        scores = [s["suitability_score"] for s in strategies]
        assert scores == sorted(scores, reverse=True)

    def test_return_structure(self):
        """Return value should have all required keys."""
        result = generate_deduplication_recommendation(
            score=60, complexity=5, lines_saved=10, has_tests=True, affected_files=2
        )

        assert "recommendation_text" in result
        assert "strategies" in result
        assert "priority" in result
        assert "effort_value_ratio" in result
        assert isinstance(result["strategies"], list)
        assert isinstance(result["effort_value_ratio"], float)


class TestGenerateRefactoringStrategies:
    """Tests for the strategy generation helper function."""

    def test_simple_code_favors_extract_function(self):
        """Low complexity should favor extract_function strategy."""
        strategies = _generate_refactoring_strategies(
            complexity=3,
            lines_saved=15,
            has_tests=True,
            affected_files=3,
            score=75
        )

        # Extract function should be ranked first for simple code
        assert strategies[0]["name"] == "extract_function"
        assert strategies[0]["suitability_score"] >= 80

    def test_complex_code_favors_extract_class(self):
        """High complexity should favor extract_class strategy."""
        strategies = _generate_refactoring_strategies(
            complexity=15,
            lines_saved=30,
            has_tests=True,
            affected_files=4,
            score=85
        )

        # Extract class should have high score for complex code
        extract_class = next(s for s in strategies if s["name"] == "extract_class")
        assert extract_class["suitability_score"] >= 70

    def test_low_score_favors_inline(self):
        """Low overall score should favor inline strategy."""
        strategies = _generate_refactoring_strategies(
            complexity=2,
            lines_saved=3,
            has_tests=True,
            affected_files=1,
            score=30
        )

        # Inline should be ranked first for low-value duplicates
        assert strategies[0]["name"] == "inline"
        assert strategies[0]["suitability_score"] >= 70

    def test_all_strategies_present(self):
        """All three strategies should always be present."""
        strategies = _generate_refactoring_strategies(
            complexity=5, lines_saved=10, has_tests=True, affected_files=2, score=60
        )

        names = [s["name"] for s in strategies]
        assert "extract_function" in names
        assert "extract_class" in names
        assert "inline" in names

    def test_strategy_has_required_fields(self):
        """Each strategy should have all required fields."""
        strategies = _generate_refactoring_strategies(
            complexity=5, lines_saved=10, has_tests=True, affected_files=2, score=60
        )

        for strategy in strategies:
            assert "name" in strategy
            assert "description" in strategy
            assert "suitability_score" in strategy
            assert "effort" in strategy
            assert "risk" in strategy
            assert "best_for" in strategy

    def test_scores_bounded_0_to_100(self):
        """Suitability scores should be bounded between 0 and 100."""
        # Test with extreme values
        strategies = _generate_refactoring_strategies(
            complexity=100, lines_saved=1000, has_tests=True, affected_files=100, score=100
        )

        for strategy in strategies:
            assert 0 <= strategy["suitability_score"] <= 100

        strategies = _generate_refactoring_strategies(
            complexity=0, lines_saved=0, has_tests=False, affected_files=0, score=0
        )

        for strategy in strategies:
            assert 0 <= strategy["suitability_score"] <= 100

    def test_effort_based_on_complexity(self):
        """Effort level should correlate with complexity."""
        low_complexity = _generate_refactoring_strategies(
            complexity=3, lines_saved=10, has_tests=True, affected_files=2, score=60
        )
        high_complexity = _generate_refactoring_strategies(
            complexity=15, lines_saved=10, has_tests=True, affected_files=2, score=60
        )

        # Find extract_function in each
        low_fn = next(s for s in low_complexity if s["name"] == "extract_function")
        high_fn = next(s for s in high_complexity if s["name"] == "extract_function")

        assert low_fn["effort"] == "low"
        assert high_fn["effort"] == "medium"

    def test_risk_based_on_tests(self):
        """Risk level should be higher without tests."""
        with_tests = _generate_refactoring_strategies(
            complexity=5, lines_saved=10, has_tests=True, affected_files=2, score=60
        )
        without_tests = _generate_refactoring_strategies(
            complexity=5, lines_saved=10, has_tests=False, affected_files=2, score=60
        )

        fn_with = next(s for s in with_tests if s["name"] == "extract_function")
        fn_without = next(s for s in without_tests if s["name"] == "extract_function")

        assert fn_with["risk"] == "low"
        assert fn_without["risk"] == "medium"

    def test_inline_always_zero_effort_and_risk(self):
        """Inline strategy should always have no effort and risk."""
        strategies = _generate_refactoring_strategies(
            complexity=10, lines_saved=20, has_tests=False, affected_files=5, score=70
        )

        inline = next(s for s in strategies if s["name"] == "inline")
        assert inline["effort"] == "none"
        assert inline["risk"] == "none"

    def test_many_affected_files_boosts_extract_function(self):
        """More affected files should increase extract_function score."""
        few_files = _generate_refactoring_strategies(
            complexity=8, lines_saved=5, has_tests=True, affected_files=1, score=60
        )
        many_files = _generate_refactoring_strategies(
            complexity=8, lines_saved=5, has_tests=True, affected_files=5, score=60
        )

        few_fn = next(s for s in few_files if s["name"] == "extract_function")
        many_fn = next(s for s in many_files if s["name"] == "extract_function")

        assert many_fn["suitability_score"] > few_fn["suitability_score"]

    def test_large_lines_saved_boosts_extract_class(self):
        """More lines saved should increase extract_class score."""
        small_save = _generate_refactoring_strategies(
            complexity=8, lines_saved=5, has_tests=True, affected_files=2, score=60
        )
        large_save = _generate_refactoring_strategies(
            complexity=8, lines_saved=30, has_tests=True, affected_files=2, score=60
        )

        small_class = next(s for s in small_save if s["name"] == "extract_class")
        large_class = next(s for s in large_save if s["name"] == "extract_class")

        assert large_class["suitability_score"] > small_class["suitability_score"]


class TestRecommendationEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_zero_values(self):
        """Function should handle zero values gracefully."""
        result = generate_deduplication_recommendation(
            score=0, complexity=0, lines_saved=0, has_tests=False, affected_files=0
        )

        assert result["priority"] == "low"
        assert result["effort_value_ratio"] >= 0
        assert len(result["strategies"]) == 3

    def test_very_high_values(self):
        """Function should handle very high values."""
        result = generate_deduplication_recommendation(
            score=100, complexity=100, lines_saved=1000, has_tests=True, affected_files=50
        )

        assert result["priority"] == "high"
        assert result["effort_value_ratio"] > 0
        assert len(result["strategies"]) == 3

    def test_minimal_improvement_case(self):
        """Test case where refactoring provides minimal improvement."""
        result = generate_deduplication_recommendation(
            score=20, complexity=1, lines_saved=2, has_tests=True, affected_files=1
        )

        assert result["priority"] == "low"
        # Inline should be recommended for minimal improvements
        assert result["strategies"][0]["name"] == "inline"

    def test_maximum_value_case(self):
        """Test case where refactoring provides maximum value."""
        result = generate_deduplication_recommendation(
            score=95, complexity=3, lines_saved=100, has_tests=True, affected_files=10
        )

        assert result["priority"] == "high"
        # Extract function should be recommended for high-value, simple code
        assert result["strategies"][0]["name"] == "extract_function"

    def test_complex_but_low_score(self):
        """Complex code with low score should still recommend inline."""
        result = generate_deduplication_recommendation(
            score=25, complexity=20, lines_saved=5, has_tests=False, affected_files=1
        )

        # Even complex code should favor inline when score is very low
        inline = next(s for s in result["strategies"] if s["name"] == "inline")
        assert inline["suitability_score"] >= 50

    def test_simple_but_high_score(self):
        """Simple code with high score should recommend extract_function."""
        result = generate_deduplication_recommendation(
            score=90, complexity=2, lines_saved=30, has_tests=True, affected_files=5
        )

        assert result["strategies"][0]["name"] == "extract_function"
        assert result["strategies"][0]["suitability_score"] >= 90
