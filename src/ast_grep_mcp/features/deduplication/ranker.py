"""
Ranking module for deduplication candidates.

This module provides functionality for scoring and ranking duplicate code
based on refactoring value, complexity, and impact.
"""

import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

from ...core.logging import get_logger
from .priority_classifier import DeduplicationPriorityClassifier
from .score_calculator import DeduplicationScoreCalculator


class DuplicationRanker:
    """Ranks duplication candidates by refactoring value with score caching."""

    def __init__(self, enable_cache: bool = True) -> None:
        """Initialize the ranker.

        Args:
            enable_cache: Whether to enable score caching (default: True)
        """
        self.logger = get_logger("deduplication.ranker")
        self.score_calculator = DeduplicationScoreCalculator()
        self.priority_classifier = DeduplicationPriorityClassifier()
        self.enable_cache = enable_cache
        self._score_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}

    def _generate_cache_key(self, candidate: Dict[str, Any]) -> str:
        """Generate a stable hash key for caching candidate scores.

        Args:
            candidate: Candidate dictionary

        Returns:
            SHA256 hash string for cache lookup
        """
        # Extract key fields that affect scoring
        cache_data = {
            "similarity": candidate.get("similarity", 0),
            "files": sorted(candidate.get("files", [])),
            "lines_saved": candidate.get("lines_saved", 0),
            "potential_line_savings": candidate.get("potential_line_savings", 0),
            "instances": len(candidate.get("instances", [])),
            "complexity": candidate.get("complexity_analysis"),
            "test_coverage": candidate.get("test_coverage"),
            "impact_analysis": candidate.get("impact_analysis"),
        }

        # Create deterministic JSON representation
        cache_str = json.dumps(cache_data, sort_keys=True, default=str)

        # Generate hash
        return hashlib.sha256(cache_str.encode()).hexdigest()

    def clear_cache(self) -> None:
        """Clear the score cache."""
        self._score_cache.clear()
        self.logger.debug("score_cache_cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with cache_size
        """
        return {"cache_size": len(self._score_cache), "cache_enabled": self.enable_cache}

    def calculate_deduplication_score(
        self,
        duplicate_group: Dict[str, Any],
        complexity: Optional[Dict[str, Any]] = None,
        test_coverage: Optional[float] = None,
        impact_analysis: Optional[Dict[str, Any]] = None,
    ) -> float:
        """
        Calculate a score for deduplication priority.

        Scoring weights:
        - Code savings: 40% (lines saved)
        - Complexity: 20% (inverse - simpler is better)
        - Risk: 25% (inverse - lower risk is better)
        - Effort: 15% (inverse - less effort is better)

        Args:
            duplicate_group: Group of duplicate code
            complexity: Complexity analysis results
            test_coverage: Test coverage percentage (0-100)
            impact_analysis: Impact analysis results

        Returns:
            Score from 0-100, higher is better for refactoring
        """
        # Delegate to score calculator
        total_score, score_components = self.score_calculator.calculate_total_score(
            duplicate_group, complexity, test_coverage, impact_analysis
        )

        # Log the result
        lines_saved = duplicate_group.get("potential_line_savings", 0)
        instance_count = len(duplicate_group.get("instances", []))

        self.logger.info(
            "deduplication_score_calculated",
            total_score=total_score,
            breakdown=score_components,
            lines_saved=lines_saved,
            instance_count=instance_count,
        )

        return total_score

    def rank_deduplication_candidates(
        self, candidates: List[Dict[str, Any]], include_analysis: bool = True, max_results: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Rank deduplication candidates by priority with score caching.

        Args:
            candidates: List of deduplication candidates
            include_analysis: Whether to include detailed analysis
            max_results: Maximum number of results to return (early exit optimization)

        Returns:
            Ranked list of candidates with scores
        """
        ranked = []
        cache_hits = 0
        cache_misses = 0

        for candidate in candidates:
            # Try to get score from cache
            cache_key = None
            if self.enable_cache:
                cache_key = self._generate_cache_key(candidate)
                if cache_key in self._score_cache:
                    total_score, score_components = self._score_cache[cache_key]
                    cache_hits += 1
                else:
                    cache_misses += 1
                    total_score, score_components = self.score_calculator.calculate_total_score(
                        candidate,
                        complexity=candidate.get("complexity_analysis"),
                        test_coverage=candidate.get("test_coverage"),
                        impact_analysis=candidate.get("impact_analysis"),
                    )
                    # Store in cache
                    self._score_cache[cache_key] = (total_score, score_components)
            else:
                # No caching
                total_score, score_components = self.score_calculator.calculate_total_score(
                    candidate,
                    complexity=candidate.get("complexity_analysis"),
                    test_coverage=candidate.get("test_coverage"),
                    impact_analysis=candidate.get("impact_analysis"),
                )

            # Get priority label
            priority = self.priority_classifier.get_priority_label(total_score)

            # Build ranked candidate
            ranked_candidate = {**candidate, "score": total_score, "priority": priority}

            # Add detailed breakdown if requested
            if include_analysis:
                ranked_candidate["score_breakdown"] = self.priority_classifier.get_score_breakdown(candidate, total_score, score_components)

            ranked.append(ranked_candidate)

        # Sort by score (highest first)
        ranked.sort(key=lambda x: x["score"], reverse=True)

        # Early exit if max_results specified - only process top N candidates
        if max_results is not None and max_results > 0:
            ranked = ranked[:max_results]

        # Add rank numbers only to returned candidates
        for i, candidate in enumerate(ranked):
            candidate["rank"] = i + 1

        # Log ranking results with cache statistics
        log_data = {
            "total_candidates": len(ranked),
            "top_score": ranked[0]["score"] if ranked else 0,
            "average_score": sum(c["score"] for c in ranked) / len(ranked) if ranked else 0,
        }

        # Add cache statistics if caching is enabled
        if self.enable_cache:
            log_data.update(
                {
                    "cache_hits": cache_hits,
                    "cache_misses": cache_misses,
                    "cache_hit_rate": cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0,
                    "cache_size": len(self._score_cache),
                }
            )

        self.logger.info("candidates_ranked", **log_data)

        return ranked


# Standalone functions for backward compatibility and convenience
_ranker_instance = None


def get_ranker() -> DuplicationRanker:
    """Get or create singleton DuplicationRanker instance."""
    global _ranker_instance
    if _ranker_instance is None:
        _ranker_instance = DuplicationRanker()
    return _ranker_instance


# Note: calculate_deduplication_score is now a method on DuplicationRanker class
# Use get_ranker().calculate_deduplication_score() or create a DuplicationRanker instance


def rank_deduplication_candidates(candidates: List[Dict[str, Any]], max_results: int = 10) -> List[Dict[str, Any]]:
    """Rank deduplication candidates using singleton ranker.

    Args:
        candidates: List of deduplication candidates
        max_results: Maximum number of results to return

    Returns:
        Ranked and enriched candidates
    """
    return get_ranker().rank_deduplication_candidates(candidates, include_analysis=True)[:max_results]
