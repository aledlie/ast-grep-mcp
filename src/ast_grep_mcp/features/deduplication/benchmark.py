"""Performance benchmarking for deduplication functions."""

import time
from typing import Any, Dict

from ...core.logging import get_logger

from .benchmark_executor import BenchmarkExecutor
from .benchmark_reporter import BenchmarkReporter
from .regression_detector import RegressionDetector


class DeduplicationBenchmark:
    """Runs performance benchmarks for deduplication functions."""

    def __init__(self):
        """Initialize the benchmark runner."""
        self.logger = get_logger("deduplication.benchmark")

        # Initialize modules
        self.executor = BenchmarkExecutor()
        self.reporter = BenchmarkReporter()
        self.detector = RegressionDetector()

        # Keep thresholds reference for backward compatibility
        self.thresholds = self.detector.thresholds
        self.baseline_file = self.reporter.baseline_file

    def benchmark_deduplication(
        self,
        iterations: int = 10,
        save_baseline: bool = False,
        check_regression: bool = True
    ) -> Dict[str, Any]:
        """Run performance benchmarks for deduplication functions.

        Benchmarks the following operations:
        - **scoring**: calculate_deduplication_score (should be < 1ms)
        - **pattern_analysis**: rank_deduplication_candidates and analyze variations
        - **code_generation**: generate_deduplication_recommendation
        - **full_workflow**: create_enhanced_duplication_response

        Args:
            iterations: Number of iterations per benchmark (default: 10)
            save_baseline: Save results as new baseline for regression detection
            check_regression: Check results against baseline for performance regressions

        Returns:
            Dict with benchmark results, regression detection, and statistics
        """
        start_time = time.time()

        self.logger.info(
            "benchmark_start",
            iterations=iterations,
            save_baseline=save_baseline,
            check_regression=check_regression
        )

        # Step 1: Run all benchmarks
        results = self.executor.run_all_benchmarks(iterations)

        # Step 2: Check for regressions if requested
        regression_detected = False
        regression_errors = []

        if check_regression:
            baseline_map = self.reporter.load_baseline()
            regression_detected, regression_errors = self.detector.check_regressions(
                results,
                baseline_map
            )

        # Step 3: Save baseline if requested
        if save_baseline:
            self.reporter.save_baseline(results)

        # Step 4: Format final report
        execution_time = time.time() - start_time

        self.logger.info(
            "benchmark_complete",
            total_benchmarks=len(results),
            regression_detected=regression_detected,
            execution_time_seconds=round(execution_time, 3)
        )

        return self.reporter.format_benchmark_report(
            results,
            regression_detected,
            regression_errors,
            self.thresholds,
            save_baseline,
            execution_time
        )



# Module-level function for backwards compatibility
def benchmark_deduplication(
    iterations: int = 10,
    save_baseline: bool = False,
    check_regression: bool = True
) -> Dict[str, Any]:
    """Run performance benchmarks for deduplication functions."""
    benchmark = DeduplicationBenchmark()
    return benchmark.benchmark_deduplication(iterations, save_baseline, check_regression)
