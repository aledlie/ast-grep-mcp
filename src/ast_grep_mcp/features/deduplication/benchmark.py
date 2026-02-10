"""Performance benchmarking for deduplication functions.

Includes benchmark execution, report generation, baseline management,
and regression detection.
"""

import json
import os
import statistics
import time
from typing import Any, Callable, Dict, List

from ...constants import DeduplicationDefaults
from ...core.logging import get_logger
from .ranker import DuplicationRanker
from .recommendations import RecommendationEngine
from .reporting import DuplicationReporter


class BenchmarkExecutor:
    """Executes timed benchmarks and collects statistics."""

    def __init__(self) -> None:
        """Initialize the benchmark executor."""
        self.logger = get_logger("deduplication.benchmark_executor")

    def run_timed_benchmark(self, name: str, func: Callable[..., Any], iterations: int, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Run a benchmark and collect statistics.

        Args:
            name: Name of the benchmark
            func: Function to benchmark
            iterations: Number of iterations
            *args: Positional arguments to pass to func
            **kwargs: Keyword arguments to pass to func

        Returns:
            Dictionary with benchmark statistics
        """
        self.logger.debug("benchmark_start", name=name, iterations=iterations)

        times: List[float] = []

        for _ in range(iterations):
            t_start = time.perf_counter()
            func(*args, **kwargs)
            elapsed = time.perf_counter() - t_start
            times.append(elapsed)

        result = {
            "name": name,
            "iterations": iterations,
            "mean_seconds": round(statistics.mean(times), 6),
            "std_dev_seconds": round(statistics.stdev(times) if len(times) > 1 else 0.0, 6),
            "min_seconds": round(min(times), 6),
            "max_seconds": round(max(times), 6),
        }

        mean_seconds = result["mean_seconds"]
        assert isinstance(mean_seconds, (int, float))
        self.logger.info("benchmark_complete", name=name, mean_ms=round(mean_seconds * 1000, 3), iterations=iterations)

        return result

    def benchmark_scoring(self, iterations: int) -> Dict[str, Any]:
        """Benchmark the scoring function.

        Args:
            iterations: Number of iterations

        Returns:
            Benchmark result dictionary
        """
        ranker = DuplicationRanker()
        test_cases = [
            {  # High value candidate
                "potential_line_savings": 100,
                "instances": [{"file": "a.py", "line": 10}, {"file": "b.py", "line": 20}, {"file": "a.py", "line": 50}],
            },
            {  # Low value candidate
                "potential_line_savings": 10,
                "instances": [{"file": f"file{i}.py", "line": i * 10} for i in range(8)],
            },
            {  # Medium value candidate
                "potential_line_savings": 50,
                "instances": [{"file": f"module{i % 5}.py", "line": i * 5} for i in range(5)],
            },
        ]

        def run_scoring() -> None:
            for duplicate_group in test_cases:
                ranker.calculate_deduplication_score(duplicate_group)

        return self.run_timed_benchmark("scoring", run_scoring, iterations)

    def benchmark_pattern_analysis(self, iterations: int) -> Dict[str, Any]:
        """Benchmark pattern analysis and ranking.

        Args:
            iterations: Number of iterations

        Returns:
            Benchmark result dictionary
        """
        candidates = [
            {
                "lines_saved": i * 10,
                "complexity_score": (i % 10) + 1,
                "has_tests": i % 2 == 0,
                "affected_files": (i % 5) + 1,
                "external_call_sites": i * 2,
            }
            for i in range(50)
        ]

        ranker = DuplicationRanker()
        return self.run_timed_benchmark("pattern_analysis", ranker.rank_deduplication_candidates, iterations, candidates)

    def benchmark_code_generation(self, iterations: int) -> Dict[str, Any]:
        """Benchmark recommendation generation.

        Args:
            iterations: Number of iterations

        Returns:
            Benchmark result dictionary
        """
        test_recs = [
            (85.0, 3, 100, True, 3),
            (45.0, 7, 20, False, 8),
            (25.0, 9, 5, False, 15),
        ]

        engine = RecommendationEngine()

        def run_recommendations() -> None:
            for score, complexity, lines, has_tests, files in test_recs:
                engine.generate_deduplication_recommendation(score, complexity, lines, has_tests, files)

        return self.run_timed_benchmark("code_generation", run_recommendations, iterations)

    def benchmark_full_workflow(self, iterations: int) -> Dict[str, Any]:
        """Benchmark the full duplication response workflow.

        Args:
            iterations: Number of iterations

        Returns:
            Benchmark result dictionary
        """
        response_candidates = [
            {
                "code": f"def helper_{i}(x, y): return x + y * {i}",
                "function_name": f"helper_{i}",
                "replacement": f"result = extracted_helper_{i}(x, y)",
                "similarity": 85.0 + i,
                "complexity": (i % 10) + 1,
                "files": [f"file_{i}.py"],
            }
            for i in range(20)
        ]

        reporter = DuplicationReporter()
        return self.run_timed_benchmark(
            "full_workflow",
            reporter.create_enhanced_duplication_response,
            iterations,
            response_candidates,
            include_diffs=False,
            include_colors=False,
        )

    def run_all_benchmarks(self, iterations: int) -> List[Dict[str, Any]]:
        """Run all deduplication benchmarks.

        Args:
            iterations: Base number of iterations (multiplied per benchmark)

        Returns:
            List of benchmark results
        """
        results: List[Dict[str, Any]] = []

        # Benchmark 1: Scoring (most iterations - should be fastest)
        results.append(self.benchmark_scoring(iterations * 10))

        # Benchmark 2: Pattern Analysis (ranking)
        results.append(self.benchmark_pattern_analysis(iterations * 5))

        # Benchmark 3: Code Generation (recommendations)
        results.append(self.benchmark_code_generation(iterations * 5))

        # Benchmark 4: Full Workflow (fewest iterations - slowest)
        results.append(self.benchmark_full_workflow(iterations))

        self.logger.info("all_benchmarks_complete", total_benchmarks=len(results))

        return results


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


class DeduplicationBenchmark:
    """Runs performance benchmarks for deduplication functions."""

    def __init__(self) -> None:
        """Initialize the benchmark runner."""
        self.logger = get_logger("deduplication.benchmark")

        # Initialize modules
        self.executor = BenchmarkExecutor()
        self.reporter = BenchmarkReporter()
        self.detector = RegressionDetector()

        # Keep thresholds reference for backward compatibility
        self.thresholds = self.detector.thresholds
        self.baseline_file = self.reporter.baseline_file

    def benchmark_deduplication(self, iterations: int = 10, save_baseline: bool = False, check_regression: bool = True) -> Dict[str, Any]:
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

        self.logger.info("benchmark_start", iterations=iterations, save_baseline=save_baseline, check_regression=check_regression)

        # Step 1: Run all benchmarks
        results = self.executor.run_all_benchmarks(iterations)

        # Step 2: Check for regressions if requested
        regression_detected = False
        regression_errors: List[str] = []

        if check_regression:
            baseline_map = self.reporter.load_baseline()
            regression_detected, regression_errors = self.detector.check_regressions(results, baseline_map)

        # Step 3: Save baseline if requested
        if save_baseline:
            self.reporter.save_baseline(results)

        # Step 4: Format final report
        execution_time = time.time() - start_time

        self.logger.info(
            "benchmark_complete",
            total_benchmarks=len(results),
            regression_detected=regression_detected,
            execution_time_seconds=round(execution_time, 3),
        )

        return self.reporter.format_benchmark_report(
            results, regression_detected, regression_errors, self.thresholds, save_baseline, execution_time
        )
