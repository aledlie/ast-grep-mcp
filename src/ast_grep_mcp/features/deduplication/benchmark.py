"""Performance benchmarking for deduplication functions."""

import json
import os
import statistics
import time
from typing import Any, Callable, Dict, List

from ...core.logging import get_logger
from .ranker import get_ranker, rank_deduplication_candidates
from .recommendations import generate_deduplication_recommendation
from .reporting import create_enhanced_duplication_response


class DeduplicationBenchmark:
    """Runs performance benchmarks for deduplication functions."""

    def __init__(self):
        """Initialize the benchmark runner."""
        self.logger = get_logger("deduplication.benchmark")

        # Regression thresholds for different operations
        self.thresholds = {
            "pattern_analysis": 0.15,
            "code_generation": 0.10,
            "full_workflow": 0.20,
            "scoring": 0.05,
            "test_coverage": 0.15
        }

        self.baseline_file = "tests/dedup_benchmark_baseline.json"

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

        results: List[Dict[str, Any]] = []

        # Benchmark 1: Scoring
        results.append(self._benchmark_scoring(iterations * 10))

        # Benchmark 2: Pattern Analysis (ranking)
        results.append(self._benchmark_pattern_analysis(iterations * 5))

        # Benchmark 3: Code Generation (recommendations)
        results.append(self._benchmark_code_generation(iterations * 5))

        # Benchmark 4: Full Workflow
        results.append(self._benchmark_full_workflow(iterations))

        # Check for regressions if requested
        regression_detected = False
        regression_errors: List[str] = []

        if check_regression:
            regression_detected, regression_errors = self._check_regressions(results)

        # Save baseline if requested
        if save_baseline:
            self._save_baseline(results)

        execution_time = time.time() - start_time

        self.logger.info(
            "benchmark_complete",
            total_benchmarks=len(results),
            regression_detected=regression_detected,
            execution_time_seconds=round(execution_time, 3)
        )

        return {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_benchmarks": len(results),
            "results": results,
            "regression_detected": regression_detected,
            "regression_errors": regression_errors,
            "thresholds": self.thresholds,
            "baseline_saved": save_baseline,
            "execution_time_seconds": round(execution_time, 3)
        }

    def _run_timed_benchmark(
        self,
        name: str,
        func: Callable,
        iterations: int,
        *args: Any,
        **kwargs: Any
    ) -> Dict[str, Any]:
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
        times: List[float] = []

        for _ in range(iterations):
            t_start = time.perf_counter()
            func(*args, **kwargs)
            elapsed = time.perf_counter() - t_start
            times.append(elapsed)

        return {
            "name": name,
            "iterations": iterations,
            "mean_seconds": round(statistics.mean(times), 6),
            "std_dev_seconds": round(statistics.stdev(times) if len(times) > 1 else 0.0, 6),
            "min_seconds": round(min(times), 6),
            "max_seconds": round(max(times), 6)
        }

    def _benchmark_scoring(self, iterations: int) -> Dict[str, Any]:
        """Benchmark the scoring function."""
        ranker = get_ranker()
        test_cases = [
            {  # High value candidate
                "potential_line_savings": 100,
                "instances": [
                    {"file": "a.py", "line": 10},
                    {"file": "b.py", "line": 20},
                    {"file": "a.py", "line": 50}
                ]
            },
            {  # Low value candidate
                "potential_line_savings": 10,
                "instances": [
                    {"file": f"file{i}.py", "line": i * 10}
                    for i in range(8)
                ]
            },
            {  # Medium value candidate
                "potential_line_savings": 50,
                "instances": [
                    {"file": f"module{i % 5}.py", "line": i * 5}
                    for i in range(5)
                ]
            },
        ]

        def run_scoring() -> None:
            for duplicate_group in test_cases:
                ranker.calculate_deduplication_score(duplicate_group)

        return self._run_timed_benchmark("scoring", run_scoring, iterations)

    def _benchmark_pattern_analysis(self, iterations: int) -> Dict[str, Any]:
        """Benchmark pattern analysis and ranking."""
        candidates = [
            {
                "lines_saved": i * 10,
                "complexity_score": (i % 10) + 1,
                "has_tests": i % 2 == 0,
                "affected_files": (i % 5) + 1,
                "external_call_sites": i * 2
            }
            for i in range(50)
        ]

        return self._run_timed_benchmark(
            "pattern_analysis",
            rank_deduplication_candidates,
            iterations,
            candidates
        )

    def _benchmark_code_generation(self, iterations: int) -> Dict[str, Any]:
        """Benchmark recommendation generation."""
        test_recs = [
            (85.0, 3, 100, True, 3),
            (45.0, 7, 20, False, 8),
            (25.0, 9, 5, False, 15),
        ]

        def run_recommendations() -> None:
            for score, complexity, lines, has_tests, files in test_recs:
                generate_deduplication_recommendation(score, complexity, lines, has_tests, files)

        return self._run_timed_benchmark(
            "code_generation",
            run_recommendations,
            iterations
        )

    def _benchmark_full_workflow(self, iterations: int) -> Dict[str, Any]:
        """Benchmark the full duplication response workflow."""
        response_candidates = [
            {
                "code": f"def helper_{i}(x, y): return x + y * {i}",
                "function_name": f"helper_{i}",
                "replacement": f"result = extracted_helper_{i}(x, y)",
                "similarity": 85.0 + i,
                "complexity": (i % 10) + 1,
                "files": [f"file_{i}.py"]
            }
            for i in range(20)
        ]

        return self._run_timed_benchmark(
            "full_workflow",
            create_enhanced_duplication_response,
            iterations,
            response_candidates,
            include_diffs=False,
            include_colors=False
        )

    def _check_regressions(
        self,
        results: List[Dict[str, Any]]
    ) -> tuple[bool, List[str]]:
        """Check for performance regressions against baseline.

        Args:
            results: Current benchmark results

        Returns:
            Tuple of (regression_detected, list of regression errors)
        """
        if not os.path.exists(self.baseline_file):
            return False, []

        with open(self.baseline_file, 'r') as f:
            baseline_data = json.load(f)
            baseline_map = {
                item["name"]: item
                for item in baseline_data.get("benchmarks", [])
            }

        regression_detected = False
        regression_errors: List[str] = []

        for result in results:
            name = result["name"]
            if name in baseline_map:
                baseline_mean = baseline_map[name].get("mean_seconds", 0)
                current_mean = result["mean_seconds"]
                threshold = self.thresholds.get(name, 0.10)

                if baseline_mean > 0:
                    slowdown = (current_mean - baseline_mean) / baseline_mean
                    if slowdown > threshold:
                        regression_detected = True
                        regression_errors.append(
                            f"{name}: {slowdown*100:.1f}% slower "
                            f"({baseline_mean:.6f}s -> {current_mean:.6f}s, "
                            f"threshold: {threshold*100:.0f}%)"
                        )

        return regression_detected, regression_errors

    def _save_baseline(self, results: List[Dict[str, Any]]) -> None:
        """Save benchmark results as new baseline.

        Args:
            results: Benchmark results to save
        """
        baseline_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "benchmarks": results
        }

        os.makedirs(os.path.dirname(self.baseline_file) if os.path.dirname(self.baseline_file) else ".", exist_ok=True)

        with open(self.baseline_file, 'w') as f:
            json.dump(baseline_data, f, indent=2)


# Module-level function for backwards compatibility
def benchmark_deduplication(
    iterations: int = 10,
    save_baseline: bool = False,
    check_regression: bool = True
) -> Dict[str, Any]:
    """Run performance benchmarks for deduplication functions."""
    benchmark = DeduplicationBenchmark()
    return benchmark.benchmark_deduplication(iterations, save_baseline, check_regression)
