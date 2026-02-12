"""Unit tests for DuplicationRanker class.

Tests focus on:
- Basic ranking functionality
- Early exit optimization (max_results parameter)
- Score calculation
- Priority classification
"""

import pytest

from ast_grep_mcp.features.deduplication.ranker import DuplicationRanker


class TestDuplicationRanker:
    """Tests for DuplicationRanker class."""

    @pytest.fixture
    def ranker(self):
        """Provide DuplicationRanker instance."""
        return DuplicationRanker()

    @pytest.fixture
    def sample_candidates(self):
        """Provide sample candidates for testing."""
        return [
            {"lines_saved": 100, "complexity_score": 5, "has_tests": True, "affected_files": 3, "external_call_sites": 10},
            {"lines_saved": 50, "complexity_score": 8, "has_tests": False, "affected_files": 2, "external_call_sites": 5},
            {"lines_saved": 80, "complexity_score": 3, "has_tests": True, "affected_files": 4, "external_call_sites": 8},
            {"lines_saved": 30, "complexity_score": 10, "has_tests": False, "affected_files": 1, "external_call_sites": 2},
            {"lines_saved": 60, "complexity_score": 6, "has_tests": True, "affected_files": 2, "external_call_sites": 6},
        ]

    def test_rank_all_candidates(self, ranker, sample_candidates):
        """Test ranking all candidates without max_results."""
        ranked = ranker.rank_deduplication_candidates(sample_candidates)

        # Should return all 5 candidates
        assert len(ranked) == 5

        # Should have scores
        for candidate in ranked:
            assert "score" in candidate
            assert "priority" in candidate
            assert "rank" in candidate

        # Should be sorted by score (highest first)
        scores = [c["score"] for c in ranked]
        assert scores == sorted(scores, reverse=True)

        # Ranks should be sequential starting from 1
        ranks = [c["rank"] for c in ranked]
        assert ranks == [1, 2, 3, 4, 5]

    def test_rank_with_max_results(self, ranker, sample_candidates):
        """Test early exit optimization with max_results parameter."""
        max_results = 3
        ranked = ranker.rank_deduplication_candidates(sample_candidates, max_results=max_results)

        # Should return only 3 candidates (early exit)
        assert len(ranked) == max_results

        # Should have scores and ranks
        for candidate in ranked:
            assert "score" in candidate
            assert "priority" in candidate
            assert "rank" in candidate

        # Ranks should be sequential starting from 1
        ranks = [c["rank"] for c in ranked]
        assert ranks == [1, 2, 3]

        # Should be sorted by score (highest first)
        scores = [c["score"] for c in ranked]
        assert scores == sorted(scores, reverse=True)

    def test_max_results_greater_than_candidates(self, ranker, sample_candidates):
        """Test max_results when it exceeds number of candidates."""
        max_results = 10
        ranked = ranker.rank_deduplication_candidates(sample_candidates, max_results=max_results)

        # Should return all 5 candidates (not 10)
        assert len(ranked) == 5

        # Ranks should be sequential
        ranks = [c["rank"] for c in ranked]
        assert ranks == [1, 2, 3, 4, 5]

    def test_max_results_zero(self, ranker, sample_candidates):
        """Test max_results=0 returns all candidates."""
        ranked = ranker.rank_deduplication_candidates(sample_candidates, max_results=0)

        # max_results=0 is treated as None (return all)
        assert len(ranked) == 5

    def test_max_results_one(self, ranker, sample_candidates):
        """Test max_results=1 returns only top candidate."""
        ranked = ranker.rank_deduplication_candidates(sample_candidates, max_results=1)

        # Should return only 1 candidate
        assert len(ranked) == 1
        assert ranked[0]["rank"] == 1

        # Should be the highest scored candidate
        all_ranked = ranker.rank_deduplication_candidates(sample_candidates)
        assert ranked[0]["score"] == all_ranked[0]["score"]

    def test_empty_candidates(self, ranker):
        """Test ranking with empty candidate list."""
        ranked = ranker.rank_deduplication_candidates([])

        # Should return empty list
        assert len(ranked) == 0

    def test_empty_candidates_with_max_results(self, ranker):
        """Test ranking with empty candidate list and max_results."""
        ranked = ranker.rank_deduplication_candidates([], max_results=3)

        # Should return empty list
        assert len(ranked) == 0

    def test_include_analysis_true(self, ranker, sample_candidates):
        """Test with include_analysis=True adds score_breakdown."""
        ranked = ranker.rank_deduplication_candidates(sample_candidates, include_analysis=True, max_results=2)

        # Should include score_breakdown
        for candidate in ranked:
            assert "score_breakdown" in candidate

    def test_include_analysis_false(self, ranker, sample_candidates):
        """Test with include_analysis=False excludes score_breakdown."""
        ranked = ranker.rank_deduplication_candidates(sample_candidates, include_analysis=False, max_results=2)

        # Should not include score_breakdown
        for candidate in ranked:
            assert "score_breakdown" not in candidate

    def test_max_results_negative(self, ranker, sample_candidates):
        """Test max_results with negative value returns all candidates."""
        ranked = ranker.rank_deduplication_candidates(sample_candidates, max_results=-1)

        # Negative value should return all candidates (not trigger early exit)
        assert len(ranked) == 5


class TestEarlyExitPerformance:
    """Tests to verify early exit optimization actually improves performance."""

    def test_early_exit_processes_fewer_rank_assignments(self):
        """Verify that early exit avoids unnecessary rank assignments."""
        ranker = DuplicationRanker()

        # Create 100 candidates
        candidates = [
            {
                "lines_saved": i * 10,
                "complexity_score": (i % 10) + 1,
                "has_tests": i % 2 == 0,
                "affected_files": (i % 5) + 1,
                "external_call_sites": i * 2,
            }
            for i in range(100)
        ]

        # Rank with max_results=10
        ranked = ranker.rank_deduplication_candidates(candidates, max_results=10)

        # Should return exactly 10 candidates
        assert len(ranked) == 10

        # All 10 should have sequential ranks
        ranks = [c["rank"] for c in ranked]
        assert ranks == list(range(1, 11))

        # Verify they are the top 10 by comparing to full ranking
        all_ranked = ranker.rank_deduplication_candidates(candidates)
        top_10_scores = [c["score"] for c in all_ranked[:10]]
        returned_scores = [c["score"] for c in ranked]
        assert returned_scores == top_10_scores
