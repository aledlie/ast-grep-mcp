"""Recommendation engine for deduplication refactoring."""

from typing import Any, Dict, List


class RecommendationEngine:
    """Generates actionable recommendations for deduplication candidates."""

    def generate_deduplication_recommendation(
        self,
        score: float,
        complexity: int,
        lines_saved: int,
        has_tests: bool,
        affected_files: int
    ) -> Dict[str, Any]:
        """Generate actionable recommendations for deduplication candidates.

        Combines scoring factors to produce prioritized recommendations with
        multiple refactoring strategy options ranked by effort/value ratio.

        Args:
            score: Overall deduplication score (0-100)
            complexity: Cyclomatic complexity of the duplicated code
            lines_saved: Number of lines that would be saved by deduplication
            has_tests: Whether the duplicated code has test coverage
            affected_files: Number of files containing the duplicate

        Returns:
            Dictionary containing:
            - recommendation_text: Human-readable recommendation
            - strategies: List of refactoring strategies with details
            - priority: Priority level (high/medium/low)
            - effort_value_ratio: Numeric ratio (higher = better value)
        """
        # Calculate effort estimate based on complexity and affected files
        base_effort = complexity * 0.3 + affected_files * 0.5
        if not has_tests:
            base_effort *= 1.5  # Higher effort without test safety net

        # Calculate value based on lines saved and affected files
        value = lines_saved * 0.4 + affected_files * 10

        # Avoid division by zero
        effort_value_ratio = value / max(base_effort, 1)

        # Generate recommendation text based on score
        if score > 80:
            recommendation_text = "High Value: Extract to shared utility"
            priority = "high"
        elif score >= 50:
            recommendation_text = "Medium Value: Consider refactoring"
            priority = "medium"
        else:
            recommendation_text = "Low Value: May not be worth refactoring"
            priority = "low"

        # Generate strategy options ranked by suitability
        strategies = self._generate_dedup_refactoring_strategies(
            complexity=complexity,
            lines_saved=lines_saved,
            has_tests=has_tests,
            affected_files=affected_files,
            score=score
        )

        return {
            "recommendation_text": recommendation_text,
            "strategies": strategies,
            "priority": priority,
            "effort_value_ratio": round(effort_value_ratio, 2)
        }

    def _generate_dedup_refactoring_strategies(
        self,
        complexity: int,
        lines_saved: int,
        has_tests: bool,
        affected_files: int,
        score: float
    ) -> List[Dict[str, Any]]:
        """Generate ranked list of refactoring strategies for a duplication candidate.

        Evaluates multiple strategies and ranks them by suitability based on
        the characteristics of the duplicated code.

        Args:
            complexity: Cyclomatic complexity
            lines_saved: Lines that would be saved
            has_tests: Whether tests exist
            affected_files: Number of affected files
            score: Overall duplication score

        Returns:
            List of strategy dictionaries with name, description, suitability_score
        """
        strategies: List[Dict[str, Any]] = []

        # Strategy 1: Extract Function
        # Best for simple, stateless duplicates
        extract_fn_score = 70.0
        if complexity <= 5:
            extract_fn_score += 20
        elif complexity > 10:
            extract_fn_score -= 20
        if lines_saved >= 10:
            extract_fn_score += 10
        if affected_files >= 3:
            extract_fn_score += 10

        strategies.append({
            "name": "extract_function",
            "description": "Extract duplicate code into a shared function",
            "suitability_score": min(100, max(0, extract_fn_score)),
            "effort": "low" if complexity <= 5 else "medium",
            "risk": "low" if has_tests else "medium",
            "best_for": "Simple, stateless duplicates with clear inputs/outputs"
        })

        # Strategy 2: Extract Class
        # Best for stateful or complex duplicates
        extract_class_score = 50.0
        if complexity > 10:
            extract_class_score += 30
        elif complexity > 5:
            extract_class_score += 15
        if lines_saved >= 20:
            extract_class_score += 15
        if affected_files >= 2:
            extract_class_score += 10
        # Penalty for very simple code
        if complexity <= 3 and lines_saved < 10:
            extract_class_score -= 20

        strategies.append({
            "name": "extract_class",
            "description": "Extract duplicate code into a shared class with state",
            "suitability_score": min(100, max(0, extract_class_score)),
            "effort": "medium" if complexity <= 10 else "high",
            "risk": "medium" if has_tests else "high",
            "best_for": "Complex duplicates with shared state or multiple related functions"
        })

        # Strategy 3: Inline (keep duplication)
        # Best when duplication is intentional or low value
        inline_score = 30.0
        if score < 40:
            inline_score += 40
        elif score < 60:
            inline_score += 20
        if affected_files == 1:
            inline_score += 20
        if lines_saved < 5:
            inline_score += 20
        # Strong penalty for high-value duplicates
        if score > 80:
            inline_score -= 30

        strategies.append({
            "name": "inline",
            "description": "Keep code duplicated (intentional duplication)",
            "suitability_score": min(100, max(0, inline_score)),
            "effort": "none",
            "risk": "none",
            "best_for": "Intentional duplication, very small code blocks, or domain-specific variations"
        })

        # Sort strategies by suitability score (highest first)
        strategies.sort(key=lambda s: s["suitability_score"], reverse=True)

        return strategies


# Module-level function for backwards compatibility
def generate_deduplication_recommendation(
    score: float,
    complexity: int,
    lines_saved: int,
    has_tests: bool,
    affected_files: int
) -> Dict[str, Any]:
    """Generate actionable recommendations for deduplication candidates."""
    engine = RecommendationEngine()
    return engine.generate_deduplication_recommendation(
        score, complexity, lines_saved, has_tests, affected_files
    )
