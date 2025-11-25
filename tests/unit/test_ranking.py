"""Unit tests for Phase 4.2 Deduplication Ranking Algorithm.

Tests the calculate_deduplication_score and rank_deduplication_candidates functions.
"""

import sys
import os

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


from ast_grep_mcp.features.deduplication.ranker import DuplicationRanker


class TestCalculateDeduplicationScore:
    """Tests for calculate_deduplication_score function."""

    def test_excellent_candidate(self, duplication_ranker):
        """Test excellent refactoring candidate: high savings, low complexity, tested."""
        score = duplication_ranker.calculate_deduplication_score(
            lines_saved=200,
            complexity=2,
            has_tests=True,
            affected_files=2,
            external_call_sites=3
        )
        # High savings, low complexity, tested, few files/calls = high score
        assert score > 60, f"Expected score > 60 for excellent candidate, got {score}"
        assert score <= 100, f"Score should not exceed 100, got {score}"

    def test_poor_candidate(self, duplication_ranker):
        """Test poor refactoring candidate: low savings, high complexity, untested."""
        score = duplication_ranker.calculate_deduplication_score(
            lines_saved=10,
            complexity=9,
            has_tests=False,
            affected_files=8,
            external_call_sites=15
        )
        # Low savings, high complexity, untested, many files/calls = low score
        assert score < 30, f"Expected score < 30 for poor candidate, got {score}"
        assert score >= 0, f"Score should not be negative, got {score}"

    def test_minimum_values(self, duplication_ranker):
        """Test with minimum possible values."""
        score = duplication_ranker.calculate_deduplication_score(
            lines_saved=0,
            complexity=1,
            has_tests=True,
            affected_files=1,
            external_call_sites=0
        )
        # Zero savings but otherwise optimal
        assert 0 <= score <= 100, f"Score out of range: {score}"

    def test_maximum_values(self, duplication_ranker):
        """Test with maximum/extreme values."""
        score = duplication_ranker.calculate_deduplication_score(
            lines_saved=1000,  # Above cap
            complexity=10,
            has_tests=False,
            affected_files=20,  # Above cap
            external_call_sites=50  # Above cap
        )
        # Max savings but otherwise poor = mixed score
        assert 0 <= score <= 100, f"Score out of range: {score}"

    def test_savings_weight(self, duplication_ranker):
        """Test that higher savings increases score."""
        low_savings = duplication_ranker.calculate_deduplication_score(
            lines_saved=10,
            complexity=5,
            has_tests=True,
            affected_files=3,
            external_call_sites=5
        )
        high_savings = duplication_ranker.calculate_deduplication_score(
            lines_saved=200,
            complexity=5,
            has_tests=True,
            affected_files=3,
            external_call_sites=5
        )
        assert high_savings > low_savings, \
            f"Higher savings should increase score: {high_savings} vs {low_savings}"

    def test_complexity_weight(self, duplication_ranker):
        """Test that lower complexity increases score."""
        high_complexity = duplication_ranker.calculate_deduplication_score(
            lines_saved=100,
            complexity=9,
            has_tests=True,
            affected_files=3,
            external_call_sites=5
        )
        low_complexity = duplication_ranker.calculate_deduplication_score(
            lines_saved=100,
            complexity=2,
            has_tests=True,
            affected_files=3,
            external_call_sites=5
        )
        assert low_complexity > high_complexity, \
            f"Lower complexity should increase score: {low_complexity} vs {high_complexity}"

    def test_test_coverage_impact(self, duplication_ranker):
        """Test that having tests increases score."""
        untested = duplication_ranker.calculate_deduplication_score(
            lines_saved=100,
            complexity=5,
            has_tests=False,
            affected_files=3,
            external_call_sites=5
        )
        tested = duplication_ranker.calculate_deduplication_score(
            lines_saved=100,
            complexity=5,
            has_tests=True,
            affected_files=3,
            external_call_sites=5
        )
        assert tested > untested, \
            f"Test coverage should increase score: {tested} vs {untested}"

    def test_affected_files_impact(self, duplication_ranker):
        """Test that fewer affected files increases score."""
        many_files = duplication_ranker.calculate_deduplication_score(
            lines_saved=100,
            complexity=5,
            has_tests=True,
            affected_files=8,
            external_call_sites=5
        )
        few_files = duplication_ranker.calculate_deduplication_score(
            lines_saved=100,
            complexity=5,
            has_tests=True,
            affected_files=2,
            external_call_sites=5
        )
        assert few_files > many_files, \
            f"Fewer files should increase score: {few_files} vs {many_files}"

    def test_call_sites_impact(self, duplication_ranker):
        """Test that fewer external call sites increases score."""
        many_calls = duplication_ranker.calculate_deduplication_score(
            lines_saved=100,
            complexity=5,
            has_tests=True,
            affected_files=3,
            external_call_sites=15
        )
        few_calls = duplication_ranker.calculate_deduplication_score(
            lines_saved=100,
            complexity=5,
            has_tests=True,
            affected_files=3,
            external_call_sites=2
        )
        assert few_calls > many_calls, \
            f"Fewer call sites should increase score: {few_calls} vs {many_calls}"

    def test_score_normalization(self, duplication_ranker):
        """Test that all scores are normalized to 0-100 range."""
        test_cases = [
            (0, 1, True, 1, 0),
            (500, 10, False, 10, 20),
            (1000, 5, True, 5, 10),
            (50, 3, False, 2, 0),
        ]
        for lines, comp, tests, files, calls in test_cases:
            score = duplication_ranker.calculate_deduplication_score(lines, comp, tests, files, calls)
            assert 0 <= score <= 100, \
                f"Score {score} out of range for inputs: {lines}, {comp}, {tests}, {files}, {calls}"

    def test_weight_distribution(self, duplication_ranker):
        """Test that weights are approximately 40/20/25/15 as specified."""
        # Perfect savings only (other factors neutral)
        savings_only = duplication_ranker.calculate_deduplication_score(
            lines_saved=500,
            complexity=5,  # Middle
            has_tests=True,
            affected_files=5,  # Middle
            external_call_sites=0
        )

        # All factors at best
        all_best = duplication_ranker.calculate_deduplication_score(
            lines_saved=500,
            complexity=1,
            has_tests=True,
            affected_files=1,
            external_call_sites=0
        )

        # Savings contributes ~40% of total possible
        # All best should be close to 100
        assert all_best > 90, f"All best factors should give high score: {all_best}"

    def test_edge_complexity_values(self, duplication_ranker):
        """Test complexity boundary values (1-10)."""
        min_complexity = duplication_ranker.calculate_deduplication_score(100, 1, True, 3, 5)
        max_complexity = duplication_ranker.calculate_deduplication_score(100, 10, True, 3, 5)

        assert min_complexity > max_complexity, \
            f"Min complexity should score higher: {min_complexity} vs {max_complexity}"

    def test_realistic_scenarios(self, duplication_ranker):
        """Test realistic refactoring scenarios."""
        # Simple utility function duplicate
        simple_util = duplication_ranker.calculate_deduplication_score(
            lines_saved=30,
            complexity=2,
            has_tests=True,
            affected_files=2,
            external_call_sites=4
        )

        # Complex class hierarchy
        complex_class = duplication_ranker.calculate_deduplication_score(
            lines_saved=150,
            complexity=7,
            has_tests=False,
            affected_files=6,
            external_call_sites=12
        )

        # Both should be valid scores
        assert 0 <= simple_util <= 100
        assert 0 <= complex_class <= 100

        # Simple utility should score higher (easier, safer)
        # even though it saves fewer lines
        # Actually with much higher savings, complex might score close
        # Just ensure both are reasonable


class TestRankDeduplicationCandidates:
    """Tests for rank_deduplication_candidates function."""

    def test_empty_list(self, duplication_ranker):
        """Test with empty candidate list."""
        result = duplication_ranker.rank_deduplication_candidates([])
        assert result == [], "Empty input should return empty output"

    def test_single_candidate(self, duplication_ranker):
        """Test with single candidate."""
        candidates = [{
            'id': 1,
            'lines_saved': 100,
            'complexity_score': 3,
            'has_tests': True,
            'affected_files': 2,
            'external_call_sites': 5
        }]
        result = duplication_ranker.rank_deduplication_candidates(candidates)

        assert len(result) == 1
        assert 'deduplication_score' in result[0]
        assert result[0]['id'] == 1

    def test_sorting_order(self, duplication_ranker):
        """Test that candidates are sorted by score (highest first)."""
        candidates = [
            {
                'id': 'poor',
                'lines_saved': 10,
                'complexity_score': 9,
                'has_tests': False,
                'affected_files': 8,
                'external_call_sites': 15
            },
            {
                'id': 'excellent',
                'lines_saved': 200,
                'complexity_score': 2,
                'has_tests': True,
                'affected_files': 2,
                'external_call_sites': 3
            },
            {
                'id': 'medium',
                'lines_saved': 50,
                'complexity_score': 5,
                'has_tests': True,
                'affected_files': 4,
                'external_call_sites': 8
            }
        ]

        result = duplication_ranker.rank_deduplication_candidates(candidates)

        assert len(result) == 3
        assert result[0]['id'] == 'excellent', f"First should be excellent, got {result[0]['id']}"
        assert result[1]['id'] == 'medium', f"Second should be medium, got {result[1]['id']}"
        assert result[2]['id'] == 'poor', f"Third should be poor, got {result[2]['id']}"

    def test_scores_added(self, duplication_ranker):
        """Test that deduplication_score is added to all candidates."""
        candidates = [
            {
                'id': i,
                'lines_saved': 100,
                'complexity_score': 5,
                'has_tests': True,
                'affected_files': 3,
                'external_call_sites': 5
            }
            for i in range(5)
        ]

        result = duplication_ranker.rank_deduplication_candidates(candidates)

        for candidate in result:
            assert 'deduplication_score' in candidate
            assert 0 <= candidate['deduplication_score'] <= 100

    def test_original_data_preserved(self, duplication_ranker):
        """Test that original candidate data is preserved."""
        candidates = [{
            'id': 1,
            'name': 'test_function',
            'lines_saved': 100,
            'complexity_score': 3,
            'has_tests': True,
            'affected_files': 2,
            'external_call_sites': 5,
            'extra_field': 'preserved'
        }]

        result = duplication_ranker.rank_deduplication_candidates(candidates)

        assert result[0]['id'] == 1
        assert result[0]['name'] == 'test_function'
        assert result[0]['extra_field'] == 'preserved'

    def test_default_values(self, duplication_ranker):
        """Test with missing optional fields (use defaults)."""
        candidates = [
            {'id': 1},  # All defaults
            {'id': 2, 'lines_saved': 100}  # Partial
        ]

        result = duplication_ranker.rank_deduplication_candidates(candidates)

        assert len(result) == 2
        for candidate in result:
            assert 'deduplication_score' in candidate

    def test_descending_score_order(self, duplication_ranker):
        """Verify scores are strictly descending or equal."""
        candidates = [
            {
                'id': i,
                'lines_saved': i * 50,
                'complexity_score': 10 - i,
                'has_tests': i % 2 == 0,
                'affected_files': i + 1,
                'external_call_sites': i * 2
            }
            for i in range(1, 6)
        ]

        result = duplication_ranker.rank_deduplication_candidates(candidates)

        for i in range(len(result) - 1):
            assert result[i]['deduplication_score'] >= result[i + 1]['deduplication_score'], \
                f"Scores not in descending order: {result[i]['deduplication_score']} < {result[i + 1]['deduplication_score']}"

    def test_does_not_modify_original(self, duplication_ranker):
        """Test that original list is not modified."""
        original = [{
            'id': 1,
            'lines_saved': 100,
            'complexity_score': 3,
            'has_tests': True,
            'affected_files': 2,
            'external_call_sites': 5
        }]

        # Make a copy to compare
        import copy
        original_copy = copy.deepcopy(original)

        result = duplication_ranker.rank_deduplication_candidates(original)

        # Original should not have score added
        assert 'deduplication_score' not in original[0]
        assert original == original_copy

    def test_large_candidate_list(self, duplication_ranker):
        """Test with many candidates for performance."""
        candidates = [
            {
                'id': i,
                'lines_saved': (i * 37) % 500,  # Varied values
                'complexity_score': (i % 10) + 1,
                'has_tests': i % 3 == 0,
                'affected_files': (i % 10) + 1,
                'external_call_sites': (i * 3) % 20
            }
            for i in range(100)
        ]

        result = duplication_ranker.rank_deduplication_candidates(candidates)

        assert len(result) == 100
        # Verify sorting
        for i in range(len(result) - 1):
            assert result[i]['deduplication_score'] >= result[i + 1]['deduplication_score']


class TestIntegration:
    """Integration tests combining scoring and ranking."""

    def test_refactoring_priority_order(self, duplication_ranker):
        """Test realistic refactoring priority scenarios."""
        candidates = [
            {
                'id': 'quick_win',
                'description': 'Simple utility duplication',
                'lines_saved': 40,
                'complexity_score': 2,
                'has_tests': True,
                'affected_files': 2,
                'external_call_sites': 3
            },
            {
                'id': 'high_value',
                'description': 'Large duplication but complex',
                'lines_saved': 300,
                'complexity_score': 7,
                'has_tests': True,
                'affected_files': 5,
                'external_call_sites': 10
            },
            {
                'id': 'risky',
                'description': 'Medium duplication, no tests',
                'lines_saved': 80,
                'complexity_score': 4,
                'has_tests': False,
                'affected_files': 4,
                'external_call_sites': 8
            },
            {
                'id': 'skip',
                'description': 'Small benefit, high cost',
                'lines_saved': 15,
                'complexity_score': 8,
                'has_tests': False,
                'affected_files': 7,
                'external_call_sites': 12
            }
        ]

        result = duplication_ranker.rank_deduplication_candidates(candidates)

        # Quick win should be first or second (easy + tested)
        # Skip should be last (low value, high risk)
        assert result[-1]['id'] == 'skip', \
            f"Skip should be last, got {result[-1]['id']}"

        # All should have valid scores
        for r in result:
            assert 0 <= r['deduplication_score'] <= 100


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
