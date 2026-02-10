"""
Ranking module for deduplication candidates.

This module provides functionality for scoring, classifying, and ranking
duplicate code based on refactoring value, complexity, and impact.
"""

import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

from ...constants import DeduplicationDefaults
from ...core.logging import get_logger


class DeduplicationScoreCalculator:
    """Calculates component scores for deduplication priority."""

    # Scoring weights from constants
    WEIGHT_SAVINGS = DeduplicationDefaults.SAVINGS_WEIGHT
    WEIGHT_COMPLEXITY = DeduplicationDefaults.COMPLEXITY_WEIGHT
    WEIGHT_RISK = DeduplicationDefaults.RISK_WEIGHT
    WEIGHT_EFFORT = DeduplicationDefaults.EFFORT_WEIGHT

    def __init__(self) -> None:
        """Initialize the score calculator."""
        self.logger = get_logger("deduplication.score_calculator")

    def calculate_total_score(
        self,
        duplicate_group: Dict[str, Any],
        complexity: Optional[Dict[str, Any]] = None,
        test_coverage: Optional[float] = None,
        impact_analysis: Optional[Dict[str, Any]] = None,
    ) -> tuple[float, Dict[str, float]]:
        """
        Calculate total deduplication score with component breakdown.

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
            Tuple of (total_score, score_breakdown)
        """
        scores = {}

        # Calculate each component score
        scores["savings"] = self.calculate_savings_score(duplicate_group)
        scores["complexity"] = self.calculate_complexity_score(complexity)
        scores["risk"] = self.calculate_risk_score(test_coverage, impact_analysis)
        scores["effort"] = self.calculate_effort_score(duplicate_group)

        # Calculate total
        total_score = sum(scores.values())

        self.logger.debug("total_score_calculated", total_score=round(total_score, 2), breakdown=scores)

        return round(total_score, 2), scores

    def calculate_savings_score(self, duplicate_group: Dict[str, Any]) -> float:
        """Calculate savings score (40% weight).

        Args:
            duplicate_group: Group of duplicate code

        Returns:
            Weighted savings score
        """
        lines_saved = duplicate_group.get("potential_line_savings", 0)
        # Normalize to 0-100 (cap at 500 lines for max score)
        savings_score = min(lines_saved / 5, 100)
        weighted_score = savings_score * self.WEIGHT_SAVINGS

        self.logger.debug("savings_score_calculated", lines_saved=lines_saved, raw_score=savings_score, weighted_score=weighted_score)

        return float(weighted_score)

    def calculate_complexity_score(self, complexity: Optional[Dict[str, Any]] = None) -> float:
        """Calculate complexity score (20% weight).

        Lower complexity is better.

        Args:
            complexity: Complexity analysis results

        Returns:
            Weighted complexity score
        """
        if complexity:
            complexity_value = complexity.get("complexity_score", 5)
            # Invert: 1 = 100, 7 = 0
            complexity_score = max(0, 100 - (complexity_value - 1) * 16.67)
        else:
            complexity_score = 50  # Default middle score

        weighted_score = complexity_score * self.WEIGHT_COMPLEXITY

        self.logger.debug(
            "complexity_score_calculated",
            complexity_value=complexity.get("complexity_score") if complexity else None,
            raw_score=complexity_score,
            weighted_score=weighted_score,
        )

        return float(weighted_score)

    def calculate_risk_score(self, test_coverage: Optional[float] = None, impact_analysis: Optional[Dict[str, Any]] = None) -> float:
        """Calculate risk score (25% weight).

        Based on test coverage and breaking change risk.
        Higher coverage and lower breaking risk = higher score.

        Args:
            test_coverage: Test coverage percentage (0-100)
            impact_analysis: Impact analysis results

        Returns:
            Weighted risk score
        """
        risk_score: float = 50.0  # Default

        # Test coverage component
        if test_coverage is not None:
            # Higher coverage = lower risk = higher score
            risk_score = float(test_coverage)

        # Breaking change risk component
        if impact_analysis:
            breaking_risk = impact_analysis.get("breaking_change_risk", "medium")
            risk_multipliers = {"low": 1.0, "medium": 0.7, "high": 0.3}
            risk_score *= risk_multipliers.get(breaking_risk, 0.7)

        weighted_score = risk_score * self.WEIGHT_RISK

        self.logger.debug(
            "risk_score_calculated",
            test_coverage=test_coverage,
            breaking_risk=impact_analysis.get("breaking_change_risk") if impact_analysis else None,
            raw_score=risk_score,
            weighted_score=weighted_score,
        )

        return float(weighted_score)

    def calculate_effort_score(self, duplicate_group: Dict[str, Any]) -> float:
        """Calculate effort score (15% weight).

        Based on number of files and instances.
        More instances and files = more effort = lower score.

        Args:
            duplicate_group: Group of duplicate code

        Returns:
            Weighted effort score
        """
        instance_count = len(duplicate_group.get("instances", []))
        file_count = len(set(inst.get("file", "") for inst in duplicate_group.get("instances", [])))

        # More instances and files = more effort = lower score
        effort_score = max(0, 100 - (instance_count * 5 + file_count * 10))
        weighted_score = effort_score * self.WEIGHT_EFFORT

        self.logger.debug(
            "effort_score_calculated",
            instance_count=instance_count,
            file_count=file_count,
            raw_score=effort_score,
            weighted_score=weighted_score,
        )

        return float(weighted_score)


class DeduplicationPriorityClassifier:
    """Classifies deduplication candidates by priority and generates recommendations."""

    # Priority thresholds
    THRESHOLD_CRITICAL = 80
    THRESHOLD_HIGH = 60
    THRESHOLD_MEDIUM = 40
    THRESHOLD_LOW = 20

    def __init__(self) -> None:
        """Initialize the priority classifier."""
        self.logger = get_logger("deduplication.priority_classifier")

    def get_priority_label(self, score: float) -> str:
        """Get priority label from score.

        Priority levels:
        - critical: score >= 80
        - high: score >= 60
        - medium: score >= 40
        - low: score >= 20
        - minimal: score < 20

        Args:
            score: Total deduplication score (0-100)

        Returns:
            Priority label string
        """
        if score >= self.THRESHOLD_CRITICAL:
            return "critical"
        elif score >= self.THRESHOLD_HIGH:
            return "high"
        elif score >= self.THRESHOLD_MEDIUM:
            return "medium"
        elif score >= self.THRESHOLD_LOW:
            return "low"
        else:
            return "minimal"

    def get_score_breakdown(self, candidate: Dict[str, Any], total_score: float, score_components: Dict[str, float]) -> Dict[str, Any]:
        """Get detailed score breakdown with factors and recommendation.

        Args:
            candidate: Deduplication candidate
            total_score: Total score (0-100)
            score_components: Individual component scores

        Returns:
            Detailed breakdown dictionary
        """
        lines_saved = candidate.get("potential_line_savings", 0)
        instance_count = len(candidate.get("instances", []))

        breakdown = {
            "total_score": total_score,
            "components": score_components,
            "factors": {
                "lines_saved": lines_saved,
                "instance_count": instance_count,
                "complexity": candidate.get("complexity_analysis", {}).get("complexity_score", "N/A"),
                "test_coverage": candidate.get("test_coverage", "N/A"),
                "breaking_risk": candidate.get("impact_analysis", {}).get("breaking_change_risk", "N/A"),
            },
            "recommendation": self.get_recommendation(total_score, lines_saved, instance_count),
        }

        self.logger.debug("score_breakdown_generated", total_score=total_score, priority=self.get_priority_label(total_score))

        return breakdown

    def get_recommendation(self, score: float, lines_saved: int, instance_count: int) -> str:
        """Generate recommendation based on score and metrics.

        Args:
            score: Total deduplication score (0-100)
            lines_saved: Number of lines that would be saved
            instance_count: Number of duplicate instances

        Returns:
            Recommendation text
        """
        if score >= self.THRESHOLD_CRITICAL:
            return f"Immediate refactoring recommended. Will save {lines_saved} lines across {instance_count} instances."
        elif score >= self.THRESHOLD_HIGH:
            return "High-value refactoring opportunity. Consider prioritizing in next sprint."
        elif score >= self.THRESHOLD_MEDIUM:
            return "Moderate refactoring value. Include in technical debt backlog."
        else:
            return "Low priority. Consider deferring unless part of larger refactoring."

    def classify_batch(self, candidates: list[Dict[str, Any]], scores: list[float]) -> Dict[str, list[Dict[str, Any]]]:
        """Classify multiple candidates by priority level.

        Args:
            candidates: List of deduplication candidates
            scores: Corresponding scores for each candidate

        Returns:
            Dictionary mapping priority labels to candidate lists
        """
        classified: Dict[str, list[Dict[str, Any]]] = {"critical": [], "high": [], "medium": [], "low": [], "minimal": []}

        for candidate, score in zip(candidates, scores):
            priority = self.get_priority_label(score)
            classified[priority].append({**candidate, "score": score, "priority": priority})

        self.logger.info(
            "batch_classified",
            total_candidates=len(candidates),
            critical=len(classified["critical"]),
            high=len(classified["high"]),
            medium=len(classified["medium"]),
            low=len(classified["low"]),
            minimal=len(classified["minimal"]),
        )

        return classified


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
