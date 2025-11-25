"""
Ranking module for deduplication candidates.

This module provides functionality for scoring and ranking duplicate code
based on refactoring value, complexity, and impact.
"""

from typing import Any, Dict, List, Optional

from ...core.logging import get_logger


class DuplicationRanker:
    """Ranks duplication candidates by refactoring value."""

    def __init__(self):
        """Initialize the ranker."""
        self.logger = get_logger("deduplication.ranker")

    def calculate_deduplication_score(
        self,
        duplicate_group: Dict[str, Any],
        complexity: Optional[Dict[str, Any]] = None,
        test_coverage: Optional[float] = None,
        impact_analysis: Optional[Dict[str, Any]] = None
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
        scores = {}

        # Calculate savings score (40% weight)
        lines_saved = duplicate_group.get("potential_line_savings", 0)
        # Normalize to 0-100 (cap at 500 lines for max score)
        savings_score = min(lines_saved / 5, 100)
        scores["savings"] = savings_score * 0.4

        # Calculate complexity score (20% weight)
        # Lower complexity is better
        if complexity:
            complexity_value = complexity.get("complexity_score", 5)
            # Invert: 1 = 100, 7 = 0
            complexity_score = max(0, 100 - (complexity_value - 1) * 16.67)
        else:
            complexity_score = 50  # Default middle score
        scores["complexity"] = complexity_score * 0.2

        # Calculate risk score (25% weight)
        # Based on test coverage and breaking change risk
        risk_score = 50  # Default
        if test_coverage is not None:
            # Higher coverage = lower risk
            risk_score = test_coverage
        if impact_analysis:
            breaking_risk = impact_analysis.get("breaking_change_risk", "medium")
            risk_multipliers = {"low": 1.0, "medium": 0.7, "high": 0.3}
            risk_score *= risk_multipliers.get(breaking_risk, 0.7)
        scores["risk"] = risk_score * 0.25

        # Calculate effort score (15% weight)
        # Based on number of files and instances
        instance_count = len(duplicate_group.get("instances", []))
        file_count = len(set(inst.get("file", "") for inst in duplicate_group.get("instances", [])))
        # More instances and files = more effort
        effort_score = max(0, 100 - (instance_count * 5 + file_count * 10))
        scores["effort"] = effort_score * 0.15

        # Calculate total score
        total_score = sum(scores.values())

        self.logger.info(
            "deduplication_score_calculated",
            total_score=round(total_score, 2),
            breakdown=scores,
            lines_saved=lines_saved,
            instance_count=instance_count
        )

        return round(total_score, 2)

    def rank_deduplication_candidates(
        self,
        candidates: List[Dict[str, Any]],
        include_analysis: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Rank deduplication candidates by priority.

        Args:
            candidates: List of deduplication candidates
            include_analysis: Whether to include detailed analysis

        Returns:
            Ranked list of candidates with scores
        """
        ranked = []

        for candidate in candidates:
            # Calculate score
            score = self.calculate_deduplication_score(
                candidate,
                complexity=candidate.get("complexity_analysis"),
                test_coverage=candidate.get("test_coverage"),
                impact_analysis=candidate.get("impact_analysis")
            )

            # Add ranking info
            ranked_candidate = {
                **candidate,
                "score": score,
                "priority": self._get_priority_label(score)
            }

            if include_analysis:
                ranked_candidate["score_breakdown"] = self._get_score_breakdown(
                    candidate,
                    score
                )

            ranked.append(ranked_candidate)

        # Sort by score (highest first)
        ranked.sort(key=lambda x: x["score"], reverse=True)

        # Add rank numbers
        for i, candidate in enumerate(ranked):
            candidate["rank"] = i + 1

        self.logger.info(
            "candidates_ranked",
            total_candidates=len(ranked),
            top_score=ranked[0]["score"] if ranked else 0,
            average_score=sum(c["score"] for c in ranked) / len(ranked) if ranked else 0
        )

        return ranked

    def _get_priority_label(self, score: float) -> str:
        """Get priority label from score."""
        if score >= 80:
            return "critical"
        elif score >= 60:
            return "high"
        elif score >= 40:
            return "medium"
        elif score >= 20:
            return "low"
        else:
            return "minimal"

    def _get_score_breakdown(
        self,
        candidate: Dict[str, Any],
        total_score: float
    ) -> Dict[str, Any]:
        """Get detailed score breakdown."""
        lines_saved = candidate.get("potential_line_savings", 0)
        instance_count = len(candidate.get("instances", []))

        return {
            "total_score": total_score,
            "factors": {
                "lines_saved": lines_saved,
                "instance_count": instance_count,
                "complexity": candidate.get("complexity_analysis", {}).get("complexity_score", "N/A"),
                "test_coverage": candidate.get("test_coverage", "N/A"),
                "breaking_risk": candidate.get("impact_analysis", {}).get("breaking_change_risk", "N/A")
            },
            "recommendation": self._get_recommendation(total_score, lines_saved, instance_count)
        }

    def _get_recommendation(
        self,
        score: float,
        lines_saved: int,
        instance_count: int
    ) -> str:
        """Generate recommendation based on score and metrics."""
        if score >= 80:
            return f"Immediate refactoring recommended. Will save {lines_saved} lines across {instance_count} instances."
        elif score >= 60:
            return "High-value refactoring opportunity. Consider prioritizing in next sprint."
        elif score >= 40:
            return "Moderate refactoring value. Include in technical debt backlog."
        else:
            return "Low priority. Consider deferring unless part of larger refactoring."


# Standalone functions for backward compatibility and convenience
_ranker_instance = None


def get_ranker() -> DuplicationRanker:
    """Get or create singleton DuplicationRanker instance."""
    global _ranker_instance
    if _ranker_instance is None:
        _ranker_instance = DuplicationRanker()
    return _ranker_instance


def calculate_deduplication_score(
    lines_saved: int,
    complexity_score: int,
    has_test_coverage: bool,
    affected_files: int,
    call_sites: int
) -> float:
    """Calculate deduplication score using singleton ranker.

    Args:
        lines_saved: Number of lines that would be saved
        complexity_score: Complexity score (1-10)
        has_test_coverage: Whether code has test coverage
        affected_files: Number of files affected
        call_sites: Number of call sites

    Returns:
        Score from 0-100
    """
    return get_ranker().calculate_deduplication_score(
        lines_saved, complexity_score, has_test_coverage,
        affected_files, call_sites
    )


def rank_deduplication_candidates(
    candidates: List[Dict[str, Any]],
    max_results: int = 10
) -> List[Dict[str, Any]]:
    """Rank deduplication candidates using singleton ranker.

    Args:
        candidates: List of deduplication candidates
        max_results: Maximum number of results to return

    Returns:
        Ranked and enriched candidates
    """
    return get_ranker().rank_deduplication_candidates(candidates, max_results)
