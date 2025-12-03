"""Benchmark report generation and baseline management.

This module handles formatting benchmark results and managing
baseline files for regression detection.
"""

import json
import os
import time
from typing import Any, Dict, List

from ...core.logging import get_logger


class BenchmarkReporter:
    """Generates benchmark reports and manages baselines."""

    def __init__(self, baseline_file: str = "tests/dedup_benchmark_baseline.json") -> None:
        """Initialize the benchmark reporter.

        Args:
            baseline_file: Path to baseline file for regression detection
        """
        self.logger = get_logger("deduplication.benchmark_reporter")
        self.baseline_file = baseline_file

    def format_benchmark_report(
        self,
        results: List[Dict[str, Any]],
        regression_detected: bool,
        regression_errors: List[str],
        thresholds: Dict[str, float],
        baseline_saved: bool,
        execution_time: float,
    ) -> Dict[str, Any]:
        """Format benchmark results into final report.

        Args:
            results: List of benchmark results
            regression_detected: Whether regressions were detected
            regression_errors: List of regression error messages
            thresholds: Regression thresholds used
            baseline_saved: Whether baseline was saved
            execution_time: Total execution time in seconds

        Returns:
            Formatted report dictionary
        """
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_benchmarks": len(results),
            "results": results,
            "regression_detected": regression_detected,
            "regression_errors": regression_errors,
            "thresholds": thresholds,
            "baseline_saved": baseline_saved,
            "execution_time_seconds": round(execution_time, 3),
        }

        self.logger.info(
            "report_formatted",
            total_benchmarks=len(results),
            regression_detected=regression_detected,
            execution_time_seconds=round(execution_time, 3),
        )

        return report

    def save_baseline(self, results: List[Dict[str, Any]]) -> None:
        """Save benchmark results as new baseline.

        Args:
            results: Benchmark results to save
        """
        baseline_data = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "benchmarks": results}

        # Create directory if needed
        baseline_dir = os.path.dirname(self.baseline_file)
        if baseline_dir:
            os.makedirs(baseline_dir, exist_ok=True)

        # Write baseline file
        with open(self.baseline_file, "w") as f:
            json.dump(baseline_data, f, indent=2)

        self.logger.info("baseline_saved", file=self.baseline_file, benchmark_count=len(results))

    def load_baseline(self) -> Dict[str, Dict[str, Any]]:
        """Load baseline benchmark results.

        Returns:
            Dictionary mapping benchmark names to baseline results
        """
        if not os.path.exists(self.baseline_file):
            self.logger.warning("baseline_not_found", file=self.baseline_file)
            return {}

        try:
            with open(self.baseline_file, "r") as f:
                baseline_data = json.load(f)

            baseline_map = {item["name"]: item for item in baseline_data.get("benchmarks", [])}

            self.logger.info("baseline_loaded", file=self.baseline_file, benchmark_count=len(baseline_map))

            return baseline_map

        except (json.JSONDecodeError, KeyError) as e:
            self.logger.error("baseline_load_failed", file=self.baseline_file, error=str(e))
            return {}
