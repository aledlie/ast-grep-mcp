"""Regression detection for benchmark results.

This module handles detecting performance regressions by comparing
current benchmark results against baseline measurements.
"""

from typing import Any, Dict, List

from ...constants import DeduplicationDefaults
from ...core.logging import get_logger


class RegressionDetector:
    """Detects performance regressions in benchmark results."""

    # Default regression thresholds for different operations
    DEFAULT_THRESHOLDS = {
        "pattern_analysis": DeduplicationDefaults.REGRESSION_PATTERN_ANALYSIS,
        "code_generation": DeduplicationDefaults.REGRESSION_CODE_GENERATION,
        "full_workflow": DeduplicationDefaults.REGRESSION_FULL_WORKFLOW,
        "scoring": DeduplicationDefaults.REGRESSION_SCORING,
        "test_coverage": DeduplicationDefaults.REGRESSION_TEST_COVERAGE,
    }

    def __init__(self, thresholds: Dict[str, float] | None = None) -> None:
        """Initialize the regression detector.

        Args:
            thresholds: Custom regression thresholds (defaults to DEFAULT_THRESHOLDS)
        """
        self.logger = get_logger("deduplication.regression_detector")
        self.thresholds = thresholds if thresholds is not None else self.DEFAULT_THRESHOLDS.copy()

    def check_regressions(self, results: List[Dict[str, Any]], baseline_map: Dict[str, Dict[str, Any]]) -> tuple[bool, List[str]]:
        """Check for performance regressions against baseline.

        Args:
            results: Current benchmark results
            baseline_map: Baseline results mapped by benchmark name

        Returns:
            Tuple of (regression_detected, list of regression errors)
        """
        if not baseline_map:
            self.logger.info("no_baseline_available")
            return False, []

        regression_detected = False
        regression_errors: List[str] = []

        for result in results:
            name = result["name"]
            if name in baseline_map:
                regression_info = self._check_single_regression(name, result, baseline_map[name])

                if regression_info:
                    regression_detected = True
                    regression_errors.append(regression_info)

        self.logger.info("regression_check_complete", regression_detected=regression_detected, regression_count=len(regression_errors))

        return regression_detected, regression_errors

    def _check_single_regression(self, name: str, current_result: Dict[str, Any], baseline_result: Dict[str, Any]) -> str | None:
        """Check a single benchmark for regression.

        Args:
            name: Benchmark name
            current_result: Current benchmark result
            baseline_result: Baseline benchmark result

        Returns:
            Regression error message if regression detected, None otherwise
        """
        baseline_mean = baseline_result.get("mean_seconds", 0)
        current_mean = current_result["mean_seconds"]
        threshold = self.thresholds.get(name, 0.10)

        if baseline_mean <= 0:
            self.logger.warning("invalid_baseline_mean", name=name, baseline_mean=baseline_mean)
            return None

        # Calculate slowdown percentage
        slowdown = (current_mean - baseline_mean) / baseline_mean

        if slowdown > threshold:
            error_msg = (
                f"{name}: {slowdown * 100:.1f}% slower ({baseline_mean:.6f}s -> {current_mean:.6f}s, threshold: {threshold * 100:.0f}%)"
            )

            self.logger.warning(
                "regression_detected",
                name=name,
                slowdown_percent=round(slowdown * 100, 1),
                baseline_seconds=baseline_mean,
                current_seconds=current_mean,
                threshold_percent=threshold * 100,
            )

            return error_msg

        return None

    def set_threshold(self, name: str, threshold: float) -> None:
        """Set regression threshold for a specific benchmark.

        Args:
            name: Benchmark name
            threshold: Regression threshold (e.g., 0.15 for 15%)
        """
        self.thresholds[name] = threshold
        self.logger.debug("threshold_updated", name=name, threshold_percent=threshold * 100)

    def get_thresholds(self) -> Dict[str, float]:
        """Get current regression thresholds.

        Returns:
            Dictionary of benchmark names to threshold values
        """
        return self.thresholds.copy()
