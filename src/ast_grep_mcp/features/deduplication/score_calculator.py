"""Score calculation for deduplication candidates.

This module handles calculating individual component scores
(savings, complexity, risk, effort) for duplication candidates.
"""
from typing import Any, Dict, Optional

from ...constants import DeduplicationDefaults
from ...core.logging import get_logger


class DeduplicationScoreCalculator:
    """Calculates component scores for deduplication priority."""

    # Scoring weights from constants
    WEIGHT_SAVINGS = DeduplicationDefaults.SAVINGS_WEIGHT
    WEIGHT_COMPLEXITY = DeduplicationDefaults.COMPLEXITY_WEIGHT
    WEIGHT_RISK = DeduplicationDefaults.RISK_WEIGHT
    WEIGHT_EFFORT = DeduplicationDefaults.EFFORT_WEIGHT

    def __init__(self):
        """Initialize the score calculator."""
        self.logger = get_logger("deduplication.score_calculator")

    def calculate_total_score(
        self,
        duplicate_group: Dict[str, Any],
        complexity: Optional[Dict[str, Any]] = None,
        test_coverage: Optional[float] = None,
        impact_analysis: Optional[Dict[str, Any]] = None
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

        self.logger.debug(
            "total_score_calculated",
            total_score=round(total_score, 2),
            breakdown=scores
        )

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

        self.logger.debug(
            "savings_score_calculated",
            lines_saved=lines_saved,
            raw_score=savings_score,
            weighted_score=weighted_score
        )

        return weighted_score

    def calculate_complexity_score(
        self,
        complexity: Optional[Dict[str, Any]] = None
    ) -> float:
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
            weighted_score=weighted_score
        )

        return weighted_score

    def calculate_risk_score(
        self,
        test_coverage: Optional[float] = None,
        impact_analysis: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculate risk score (25% weight).

        Based on test coverage and breaking change risk.
        Higher coverage and lower breaking risk = higher score.

        Args:
            test_coverage: Test coverage percentage (0-100)
            impact_analysis: Impact analysis results

        Returns:
            Weighted risk score
        """
        risk_score = 50  # Default

        # Test coverage component
        if test_coverage is not None:
            # Higher coverage = lower risk = higher score
            risk_score = test_coverage

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
            weighted_score=weighted_score
        )

        return weighted_score

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
        file_count = len(set(
            inst.get("file", "") for inst in duplicate_group.get("instances", [])
        ))

        # More instances and files = more effort = lower score
        effort_score = max(0, 100 - (instance_count * 5 + file_count * 10))
        weighted_score = effort_score * self.WEIGHT_EFFORT

        self.logger.debug(
            "effort_score_calculated",
            instance_count=instance_count,
            file_count=file_count,
            raw_score=effort_score,
            weighted_score=weighted_score
        )

        return weighted_score
