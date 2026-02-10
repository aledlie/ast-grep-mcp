"""Benchmark execution for deduplication functions.

This module handles running timed benchmarks and collecting
performance statistics.
"""

import statistics
import time
from typing import Any, Callable, Dict, List

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
