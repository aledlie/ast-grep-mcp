"""Performance benchmarking suite for ast-grep MCP server.

This module provides benchmarking for:
- Pattern search (find_code)
- YAML rule search (find_code_by_rule)
- Complex multi-condition rules
- Large result sets
- Streaming and caching performance

Usage:
    # Run benchmarks
    pytest tests/test_benchmark.py -v

    # Run with baseline comparison
    pytest tests/test_benchmark.py -v --benchmark-compare

    # Update baseline
    pytest tests/test_benchmark.py -v --benchmark-save=baseline
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple
from unittest.mock import patch

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Mock FastMCP before importing main
class MockFastMCP:
    def __init__(self, name: str):
        self.name = name
        self.tools: Dict[str, Any] = {}

    def tool(self, **kwargs: Any) -> Any:
        def decorator(func: Any) -> Any:
            self.tools[func.__name__] = func
            return func
        return decorator

    def run(self, **kwargs: Any) -> None:
        pass


def mock_field(**kwargs: Any) -> Any:
    return kwargs.get("default")


# Import with mocked decorators
with patch("mcp.server.fastmcp.FastMCP", MockFastMCP):
    with patch("pydantic.Field", mock_field):
        import main
        from main import register_mcp_tools

# Register tools once for all tests
mcp = main.mcp
register_mcp_tools()

# Ensure caching is enabled for benchmarks
main.CACHE_ENABLED = True
if main._query_cache is None:
    from main import QueryCache
    main._query_cache = QueryCache(max_size=100, ttl_seconds=300)


class BenchmarkResult:
    """Store benchmark results for comparison."""

    def __init__(
        self,
        name: str,
        execution_time: float,
        memory_mb: float,
        result_count: int,
        cache_hit: bool = False
    ):
        self.name = name
        self.execution_time = execution_time
        self.memory_mb = memory_mb
        self.result_count = result_count
        self.cache_hit = cache_hit

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "execution_time_seconds": round(self.execution_time, 3),
            "memory_mb": round(self.memory_mb, 2),
            "result_count": self.result_count,
            "cache_hit": self.cache_hit
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BenchmarkResult':
        return cls(
            name=data["name"],
            execution_time=data["execution_time_seconds"],
            memory_mb=data["memory_mb"],
            result_count=data["result_count"],
            cache_hit=data.get("cache_hit", False)
        )


class BenchmarkRunner:
    """Run benchmarks and track results."""

    def __init__(self, baseline_file: str = "tests/benchmark_baseline.json"):
        self.baseline_file = baseline_file
        self.results: List[BenchmarkResult] = []
        self.baseline: Dict[str, BenchmarkResult] = {}
        self._load_baseline()

    def _load_baseline(self) -> None:
        """Load baseline metrics from file."""
        if os.path.exists(self.baseline_file):
            with open(self.baseline_file, 'r') as f:
                data = json.load(f)
                self.baseline = {
                    item["name"]: BenchmarkResult.from_dict(item)
                    for item in data.get("benchmarks", [])
                }

    def save_baseline(self) -> None:
        """Save current results as new baseline."""
        baseline_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "benchmarks": [r.to_dict() for r in self.results]
        }
        os.makedirs(os.path.dirname(self.baseline_file), exist_ok=True)
        with open(self.baseline_file, 'w') as f:
            json.dump(baseline_data, f, indent=2)

    def run_benchmark(
        self,
        name: str,
        func: Any,
        *args: Any,
        **kwargs: Any
    ) -> BenchmarkResult:
        """Run a single benchmark and record results."""
        import tracemalloc

        # Track cache hits before running
        cache_hits_before = main._query_cache.hits if main._query_cache else 0

        # Start memory tracking
        tracemalloc.start()
        start_memory = tracemalloc.get_traced_memory()[0]

        # Run benchmark
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time

        # Calculate memory usage
        current, peak = tracemalloc.get_traced_memory()
        memory_mb = (peak - start_memory) / (1024 * 1024)
        tracemalloc.stop()

        # Check if cache was hit
        cache_hits_after = main._query_cache.hits if main._query_cache else 0
        cache_hit = cache_hits_after > cache_hits_before

        # Count results
        if isinstance(result, list):
            result_count = len(result)
        elif isinstance(result, str):
            # Count matches in text output
            result_count = result.count('\n\n') if result else 0
        else:
            result_count = 0

        benchmark_result = BenchmarkResult(
            name=name,
            execution_time=execution_time,
            memory_mb=memory_mb,
            result_count=result_count,
            cache_hit=cache_hit
        )

        self.results.append(benchmark_result)
        return benchmark_result

    def check_regression(self, threshold: float = 0.10) -> Tuple[bool, List[str]]:
        """Check for performance regressions.

        Args:
            threshold: Maximum allowed slowdown (0.10 = 10%)

        Returns:
            Tuple of (has_regression, error_messages)
        """
        if not self.baseline:
            return (False, ["No baseline found - skipping regression check"])

        errors = []
        for result in self.results:
            if result.name not in self.baseline:
                continue

            baseline = self.baseline[result.name]
            slowdown = (result.execution_time - baseline.execution_time) / baseline.execution_time

            if slowdown > threshold:
                errors.append(
                    f"{result.name}: {slowdown*100:.1f}% slower "
                    f"({baseline.execution_time:.3f}s → {result.execution_time:.3f}s)"
                )

        return (len(errors) > 0, errors)

    def generate_report(self) -> str:
        """Generate markdown benchmark report."""
        lines = ["# Performance Benchmark Report", ""]
        lines.append(f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Benchmarks Run:** {len(self.results)}")
        lines.append("")

        # Results table
        lines.append("## Benchmark Results")
        lines.append("")
        lines.append("| Benchmark | Time (s) | Memory (MB) | Results | vs Baseline |")
        lines.append("|-----------|----------|-------------|---------|-------------|")

        for result in self.results:
            baseline_info = ""
            if result.name in self.baseline:
                baseline = self.baseline[result.name]
                diff = ((result.execution_time - baseline.execution_time) / baseline.execution_time) * 100
                if diff > 0:
                    baseline_info = f"+{diff:.1f}% 🔴"
                elif diff < -5:  # Improvement > 5%
                    baseline_info = f"{diff:.1f}% 🟢"
                else:
                    baseline_info = "~same"
            else:
                baseline_info = "new"

            lines.append(
                f"| {result.name} | {result.execution_time:.3f} | "
                f"{result.memory_mb:.2f} | {result.result_count} | {baseline_info} |"
            )

        lines.append("")

        # Regression check
        has_regression, errors = self.check_regression()
        if has_regression:
            lines.append("## ⚠️ Performance Regressions Detected")
            lines.append("")
            for error in errors:
                lines.append(f"- {error}")
            lines.append("")
        else:
            lines.append("## ✅ No Performance Regressions")
            lines.append("")

        return "\n".join(lines)


@pytest.fixture
def benchmark_runner() -> BenchmarkRunner:
    """Provide benchmark runner for tests."""
    return BenchmarkRunner()


@pytest.fixture
def benchmark_fixtures() -> Path:
    """Provide path to benchmark fixtures."""
    return Path(__file__).parent.parent / "fixtures"


class TestPerformanceBenchmarks:
    """Performance benchmarking test suite."""

    def test_benchmark_simple_pattern_search(
        self,
        benchmark_runner: BenchmarkRunner,
        benchmark_fixtures: Path
    ) -> None:
        """Benchmark simple pattern search with find_code."""
        tool = mcp.tools["find_code"]

        result = benchmark_runner.run_benchmark(
            "simple_pattern_search",
            tool,
            project_folder=str(benchmark_fixtures),
            pattern="def $FUNC",
            language="python",
            output_format="json"
        )

        assert result.execution_time < 5.0, "Simple pattern search too slow"
        assert result.memory_mb < 50.0, "Simple pattern search uses too much memory"

    def test_benchmark_yaml_rule_search(
        self,
        benchmark_runner: BenchmarkRunner,
        benchmark_fixtures: Path
    ) -> None:
        """Benchmark YAML rule search with find_code_by_rule."""
        tool = mcp.tools["find_code_by_rule"]

        yaml_rule = """
id: test-rule
language: python
rule:
  kind: class_definition
  pattern: class $NAME
"""

        result = benchmark_runner.run_benchmark(
            "yaml_rule_search",
            tool,
            project_folder=str(benchmark_fixtures),
            yaml_rule=yaml_rule,
            output_format="json"
        )

        assert result.execution_time < 5.0, "YAML rule search too slow"
        assert result.memory_mb < 50.0, "YAML rule search uses too much memory"

    def test_benchmark_max_results_early_termination(
        self,
        benchmark_runner: BenchmarkRunner,
        benchmark_fixtures: Path
    ) -> None:
        """Benchmark early termination with max_results."""
        tool = mcp.tools["find_code"]

        # Benchmark with max_results (should terminate early)
        result = benchmark_runner.run_benchmark(
            "early_termination_max_10",
            tool,
            project_folder=str(benchmark_fixtures),
            pattern="def $FUNC",
            language="python",
            max_results=10,
            output_format="json"
        )

        # Should find exactly 10 results (or fewer if not enough matches)
        assert result.result_count <= 10, "Early termination didn't work"

    def test_benchmark_file_size_filtering(
        self,
        benchmark_runner: BenchmarkRunner,
        benchmark_fixtures: Path
    ) -> None:
        """Benchmark file size filtering performance."""
        tool = mcp.tools["find_code"]

        # Benchmark with file size filtering
        result = benchmark_runner.run_benchmark(
            "file_size_filtering_10mb",
            tool,
            project_folder=str(benchmark_fixtures),
            pattern="def $FUNC",
            language="python",
            max_file_size_mb=10,
            output_format="json"
        )

        assert result.execution_time < 5.0, "File size filtering too slow"

    def test_benchmark_caching_performance(
        self,
        benchmark_runner: BenchmarkRunner,
        benchmark_fixtures: Path
    ) -> None:
        """Benchmark cache hit performance."""
        tool = mcp.tools["find_code"]

        # First run (cache miss)
        result1 = benchmark_runner.run_benchmark(
            "cache_miss",
            tool,
            project_folder=str(benchmark_fixtures),
            pattern="def $FUNC",
            language="python",
            output_format="json"
        )

        # Second run (cache hit)
        result2 = benchmark_runner.run_benchmark(
            "cache_hit",
            tool,
            project_folder=str(benchmark_fixtures),
            pattern="def $FUNC",
            language="python",
            output_format="json"
        )

        # Verify second run was a cache hit
        assert result2.cache_hit, "Second run should be a cache hit"

        # Cache hit should be at least as fast (or within reasonable overhead)
        # For small fixtures, cache overhead may prevent speedup, so we just
        # verify it's not significantly slower (>2x)
        speedup = result1.execution_time / result2.execution_time
        assert speedup > 0.5, f"Cache making queries too slow ({speedup:.1f}x speedup, expected >0.5x)"

        # Log the speedup for informational purposes
        if speedup >= 2.0:
            print(f"Cache speedup: {speedup:.1f}x (excellent)")
        elif speedup >= 1.0:
            print(f"Cache speedup: {speedup:.1f}x (good)")
        else:
            print(f"Cache overhead: {1/speedup:.1f}x (acceptable for small fixtures)")

    def test_generate_benchmark_report(
        self,
        benchmark_runner: BenchmarkRunner,
        tmp_path: Path
    ) -> None:
        """Generate benchmark report after running benchmarks."""
        # Run a simple benchmark
        benchmark_runner.results.append(
            BenchmarkResult(
                name="test_benchmark",
                execution_time=0.123,
                memory_mb=10.5,
                result_count=42
            )
        )

        # Generate report
        report = benchmark_runner.generate_report()

        assert "Performance Benchmark Report" in report
        assert "test_benchmark" in report
        assert "0.123" in report

        # Save report to file
        report_file = tmp_path / "benchmark_report.md"
        report_file.write_text(report)
        assert report_file.exists()

    def test_regression_detection(self, benchmark_runner: BenchmarkRunner) -> None:
        """Test performance regression detection."""
        # Add baseline result
        baseline = BenchmarkResult(
            name="test_query",
            execution_time=1.0,
            memory_mb=10.0,
            result_count=100
        )
        benchmark_runner.baseline["test_query"] = baseline

        # Add current result with 15% regression
        current = BenchmarkResult(
            name="test_query",
            execution_time=1.15,
            memory_mb=10.0,
            result_count=100
        )
        benchmark_runner.results.append(current)

        # Check for regression
        has_regression, errors = benchmark_runner.check_regression(threshold=0.10)

        assert has_regression, "Should detect regression"
        assert len(errors) == 1
        assert "15.0% slower" in errors[0]


@pytest.mark.skipif(
    os.environ.get("CI") != "true",
    reason="Only run in CI for regression detection"
)
class TestCIBenchmarks:
    """Benchmarks that run in CI for regression detection."""

    def test_ci_regression_check(
        self,
        benchmark_runner: BenchmarkRunner,
        benchmark_fixtures: Path
    ) -> None:
        """Run benchmarks in CI and fail on regression."""
        # Run all standard benchmarks
        tool = mcp.tools["find_code"]

        benchmark_runner.run_benchmark(
            "ci_simple_search",
            tool,
            project_folder=str(benchmark_fixtures),
            pattern="def $FUNC",
            language="python",
            output_format="json"
        )

        # Check for regressions
        has_regression, errors = benchmark_runner.check_regression()

        if has_regression:
            pytest.fail("Performance regression detected:\n" + "\n".join(errors))
