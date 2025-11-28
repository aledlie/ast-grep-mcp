"""Priority classification for deduplication candidates.

This module handles classifying deduplication candidates by priority level
and generating recommendations based on scores and metrics.
"""
from typing import Any, Dict

from ...core.logging import get_logger


class DeduplicationPriorityClassifier:
    """Classifies deduplication candidates by priority and generates recommendations."""

    # Priority thresholds
    THRESHOLD_CRITICAL = 80
    THRESHOLD_HIGH = 60
    THRESHOLD_MEDIUM = 40
    THRESHOLD_LOW = 20

    def __init__(self):
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

    def get_score_breakdown(
        self,
        candidate: Dict[str, Any],
        total_score: float,
        score_components: Dict[str, float]
    ) -> Dict[str, Any]:
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
                "breaking_risk": candidate.get("impact_analysis", {}).get("breaking_change_risk", "N/A")
            },
            "recommendation": self.get_recommendation(total_score, lines_saved, instance_count)
        }

        self.logger.debug(
            "score_breakdown_generated",
            total_score=total_score,
            priority=self.get_priority_label(total_score)
        )

        return breakdown

    def get_recommendation(
        self,
        score: float,
        lines_saved: int,
        instance_count: int
    ) -> str:
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

    def classify_batch(
        self,
        candidates: list[Dict[str, Any]],
        scores: list[float]
    ) -> Dict[str, list[Dict[str, Any]]]:
        """Classify multiple candidates by priority level.

        Args:
            candidates: List of deduplication candidates
            scores: Corresponding scores for each candidate

        Returns:
            Dictionary mapping priority labels to candidate lists
        """
        classified = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
            "minimal": []
        }

        for candidate, score in zip(candidates, scores):
            priority = self.get_priority_label(score)
            classified[priority].append({
                **candidate,
                "score": score,
                "priority": priority
            })

        self.logger.info(
            "batch_classified",
            total_candidates=len(candidates),
            critical=len(classified["critical"]),
            high=len(classified["high"]),
            medium=len(classified["medium"]),
            low=len(classified["low"]),
            minimal=len(classified["minimal"])
        )

        return classified
