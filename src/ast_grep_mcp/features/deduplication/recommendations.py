"""Recommendation engine for deduplication refactoring."""

from typing import Any, Dict, List, cast

# Configuration-driven strategy definitions
STRATEGY_CONFIG = {
    "extract_function": {
        "base_score": 70.0,
        "description": "Extract duplicate code into a shared function",
        "scoring_rules": [
            {"condition": lambda c, ln, a, s, h: c <= 5, "adjustment": +20},
            {"condition": lambda c, ln, a, s, h: c > 10, "adjustment": -20},
            {"condition": lambda c, ln, a, s, h: ln >= 10, "adjustment": +10},
            {"condition": lambda c, ln, a, s, h: a >= 3, "adjustment": +10},
        ],
        "effort_fn": lambda c, ln, a, h: "low" if c <= 5 else "medium",
        "risk_fn": lambda c, ln, a, h: "low" if h else "medium",
        "best_for": "Simple, stateless duplicates with clear inputs/outputs",
    },
    "extract_class": {
        "base_score": 50.0,
        "description": "Extract duplicate code into a shared class with state",
        "scoring_rules": [
            {"condition": lambda c, ln, a, s, h: c > 10, "adjustment": +30},
            {"condition": lambda c, ln, a, s, h: 5 < c <= 10, "adjustment": +15},
            {"condition": lambda c, ln, a, s, h: ln >= 20, "adjustment": +15},
            {"condition": lambda c, ln, a, s, h: a >= 2, "adjustment": +10},
            {"condition": lambda c, ln, a, s, h: c <= 3 and ln < 10, "adjustment": -20},
        ],
        "effort_fn": lambda c, ln, a, h: "medium" if c <= 10 else "high",
        "risk_fn": lambda c, ln, a, h: "medium" if h else "high",
        "best_for": "Complex duplicates with shared state or multiple related functions",
    },
    "inline": {
        "base_score": 30.0,
        "description": "Keep code duplicated (intentional duplication)",
        "scoring_rules": [
            {"condition": lambda c, ln, a, s, h: s < 40, "adjustment": +40},
            {"condition": lambda c, ln, a, s, h: 40 <= s < 60, "adjustment": +20},
            {"condition": lambda c, ln, a, s, h: a == 1, "adjustment": +20},
            {"condition": lambda c, ln, a, s, h: ln < 5, "adjustment": +20},
            {"condition": lambda c, ln, a, s, h: s > 80, "adjustment": -30},
        ],
        "effort_fn": lambda c, ln, a, h: "none",
        "risk_fn": lambda c, ln, a, h: "none",
        "best_for": "Intentional duplication, very small code blocks, or domain-specific variations",
    },
}


class RecommendationEngine:
    """Generates actionable recommendations for deduplication candidates."""

    def generate_deduplication_recommendation(
        self, score: float, complexity: int, lines_saved: int, has_tests: bool, affected_files: int
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
            complexity=complexity, lines_saved=lines_saved, has_tests=has_tests, affected_files=affected_files, score=score
        )

        return {
            "recommendation_text": recommendation_text,
            "strategies": strategies,
            "priority": priority,
            "effort_value_ratio": round(effort_value_ratio, 2),
        }

    def _calculate_strategy_score(
        self,
        base_score: float,
        rules: List[Dict[str, Any]],
        complexity: int,
        lines_saved: int,
        affected_files: int,
        score: float,
        has_tests: bool,
    ) -> float:
        """Calculate strategy score by applying scoring rules.

        Args:
            base_score: Initial score for the strategy
            rules: List of scoring rules with conditions and adjustments
            complexity: Cyclomatic complexity
            lines_saved: Lines that would be saved
            affected_files: Number of affected files
            score: Overall duplication score
            has_tests: Whether tests exist

        Returns:
            Calculated score within range [0, 100]
        """
        current_score = base_score

        for rule in rules:
            if rule["condition"](complexity, lines_saved, affected_files, score, has_tests):
                current_score += rule["adjustment"]

        return min(100, max(0, current_score))

    def _build_strategy_dict(
        self,
        name: str,
        config: Dict[str, Any],
        suitability_score: float,
        complexity: int,
        lines_saved: int,
        affected_files: int,
        has_tests: bool,
    ) -> Dict[str, Any]:
        """Build a strategy dictionary from configuration.

        Args:
            name: Strategy name
            config: Strategy configuration
            suitability_score: Calculated suitability score
            complexity: Cyclomatic complexity
            lines_saved: Lines that would be saved
            affected_files: Number of affected files
            has_tests: Whether tests exist

        Returns:
            Complete strategy dictionary
        """
        return {
            "name": name,
            "description": config["description"],
            "suitability_score": suitability_score,
            "effort": config["effort_fn"](complexity, lines_saved, affected_files, has_tests),
            "risk": config["risk_fn"](complexity, lines_saved, affected_files, has_tests),
            "best_for": config["best_for"],
        }

    def _generate_dedup_refactoring_strategies(
        self, complexity: int, lines_saved: int, has_tests: bool, affected_files: int, score: float
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

        # Process each strategy from configuration
        for strategy_name, config in STRATEGY_CONFIG.items():
            # Calculate score using rules
            suitability_score = self._calculate_strategy_score(
                base_score=cast(float, config["base_score"]),
                rules=cast(List[Dict[str, Any]], config["scoring_rules"]),
                complexity=complexity,
                lines_saved=lines_saved,
                affected_files=affected_files,
                score=score,
                has_tests=has_tests,
            )

            # Build strategy dictionary
            strategy = self._build_strategy_dict(
                name=strategy_name,
                config=config,
                suitability_score=suitability_score,
                complexity=complexity,
                lines_saved=lines_saved,
                affected_files=affected_files,
                has_tests=has_tests,
            )

            strategies.append(strategy)

        # Sort strategies by suitability score (highest first)
        strategies.sort(key=lambda s: s["suitability_score"], reverse=True)

        return strategies


def generate_refactoring_suggestions(duplicates: List[Dict[str, Any]], language: str) -> List[Dict[str, Any]]:
    """Generate refactoring suggestions for duplicate code instances.

    Analyzes duplicate code snippets and generates appropriate refactoring
    suggestions based on the code characteristics and language.

    Args:
        duplicates: List of duplicate code instances, each containing:
            - code: The duplicate code snippet
            - file: Source file path
            - similarity: Similarity score (0-1)
        language: Programming language of the code

    Returns:
        List of refactoring suggestions with type and description
    """
    if not duplicates:
        return []

    suggestions: List[Dict[str, Any]] = []

    # Analyze the duplicates to determine best refactoring strategy
    num_duplicates = len(duplicates)
    avg_similarity = sum(d.get("similarity", 0.9) for d in duplicates) / max(num_duplicates, 1)

    # Get code characteristics from first duplicate
    first_code = duplicates[0].get("code", "") if duplicates else ""
    line_count = len(first_code.split("\n"))

    # Primary suggestion: extract to shared function
    suggestions.append({
        "type": "extract_function",
        "description": "Extract duplicate code into a shared utility function",
        "priority": "high" if avg_similarity > 0.85 else "medium",
        "estimated_savings": f"{line_count * (num_duplicates - 1)} lines",
    })

    # Additional suggestions based on characteristics
    if num_duplicates > 3:
        suggestions.append({
            "type": "extract_module",
            "description": "Consider extracting to a dedicated module for reuse across files",
            "priority": "medium",
        })

    if line_count > 20:
        suggestions.append({
            "type": "extract_class",
            "description": "Extract to a class if the code has shared state or multiple related operations",
            "priority": "low",
        })

    # Language-specific suggestions
    if language in ("python", "ruby"):
        suggestions.append({
            "type": "decorator_pattern",
            "description": f"Consider using a decorator pattern in {language} for cross-cutting concerns",
            "priority": "low",
        })
    elif language in ("javascript", "typescript"):
        suggestions.append({
            "type": "higher_order_function",
            "description": "Consider using higher-order functions for functional composition",
            "priority": "low",
        })

    return suggestions
