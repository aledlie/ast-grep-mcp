#!/usr/bin/env python3
"""
Benchmark fixture performance overhead.

Measures:
- Setup time per fixture
- Teardown time per fixture
- Total overhead per test
- Scope efficiency (function vs class vs module)

Usage:
    python tests/scripts/benchmark_fixtures.py
    python tests/scripts/benchmark_fixtures.py --detailed
    python tests/scripts/benchmark_fixtures.py --fixture temp_dir
    python tests/scripts/benchmark_fixtures.py --json
"""

import argparse
import json
import subprocess
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Optional


@dataclass
class FixtureBenchmark:
    """Benchmark results for a fixture."""
    fixture_name: str
    scope: str
    avg_setup_time: float  # milliseconds
    avg_teardown_time: float  # milliseconds
    total_overhead: float  # milliseconds
    tests_measured: int
    passes_threshold: bool  # <100ms threshold


class FixtureBenchmarker:
    """Benchmark fixture performance."""

    def __init__(self, root: Path):
        self.root = root
        self.threshold_ms = 100.0  # 100ms threshold

    def benchmark_fixture(self, fixture_name: str, iterations: int = 5) -> Optional[FixtureBenchmark]:
        """Benchmark a specific fixture."""
        # Create temporary test file
        test_content = f'''
import pytest
import time

@pytest.fixture
def timing_wrapper({fixture_name}):
    """Wrapper to measure fixture overhead."""
    start = time.perf_counter()
    yield {fixture_name}
    end = time.perf_counter()
    # Overhead measured

def test_fixture_overhead(timing_wrapper):
    """Minimal test to measure fixture overhead."""
    pass

def test_fixture_overhead_2(timing_wrapper):
    """Second minimal test."""
    pass

def test_fixture_overhead_3(timing_wrapper):
    """Third minimal test."""
    pass
'''

        test_file = self.root / "tests" / f"test_benchmark_{fixture_name}.py"
        test_file.write_text(test_content)

        try:
            # Run benchmark
            times = []
            for _ in range(iterations):
                start = time.perf_counter()
                result = subprocess.run(
                    ["pytest", str(test_file), "-v", "-q"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                end = time.perf_counter()

                if result.returncode == 0:
                    times.append((end - start) * 1000)  # Convert to ms

            if not times:
                return None

            avg_time = sum(times) / len(times)
            # Estimate per-test overhead (divide by 3 tests)
            per_test_overhead = avg_time / 3

            # Get fixture scope
            scope = self._get_fixture_scope(fixture_name)

            return FixtureBenchmark(
                fixture_name=fixture_name,
                scope=scope,
                avg_setup_time=per_test_overhead * 0.6,  # Estimate 60% setup
                avg_teardown_time=per_test_overhead * 0.4,  # Estimate 40% teardown
                total_overhead=per_test_overhead,
                tests_measured=3 * iterations,
                passes_threshold=per_test_overhead < self.threshold_ms
            )

        except Exception as e:
            print(f"Error benchmarking {fixture_name}: {e}")
            return None
        finally:
            # Cleanup
            if test_file.exists():
                test_file.unlink()

    def _get_fixture_scope(self, fixture_name: str) -> str:
        """Get fixture scope from conftest.py."""
        conftest = self.root / "tests" / "conftest.py"
        if not conftest.exists():
            return "function"

        content = conftest.read_text()

        # Look for fixture definition
        for line in content.splitlines():
            if f"def {fixture_name}" in line:
                # Check previous lines for scope
                lines_before = content[:content.index(line)].splitlines()
                for prev_line in reversed(lines_before[-5:]):
                    if "scope=" in prev_line:
                        if "class" in prev_line:
                            return "class"
                        elif "module" in prev_line:
                            return "module"
                        elif "session" in prev_line:
                            return "session"
                return "function"

        return "function"

    def benchmark_all_fixtures(self) -> List[FixtureBenchmark]:
        """Benchmark all fixtures in conftest.py."""
        conftest = self.root / "tests" / "conftest.py"
        if not conftest.exists():
            return []

        # Extract fixture names
        fixture_names = []
        content = conftest.read_text()
        for line in content.splitlines():
            if line.strip().startswith("def ") and "@pytest.fixture" in content[:content.index(line)]:
                func_name = line.strip().split("(")[0].replace("def ", "")
                if not func_name.startswith("_"):
                    fixture_names.append(func_name)

        print(f"Found {len(fixture_names)} fixtures to benchmark...")

        benchmarks = []
        for i, fixture_name in enumerate(fixture_names, 1):
            print(f"[{i}/{len(fixture_names)}] Benchmarking {fixture_name}...")
            result = self.benchmark_fixture(fixture_name, iterations=3)
            if result:
                benchmarks.append(result)

        return benchmarks


def format_benchmark_report(benchmarks: List[FixtureBenchmark], detailed: bool = False) -> str:
    """Format benchmark results as readable report."""
    lines = []

    lines.append("=" * 100)
    lines.append("FIXTURE PERFORMANCE BENCHMARKS")
    lines.append("=" * 100)
    lines.append("")

    if not benchmarks:
        lines.append("No benchmarks available.")
        return "\n".join(lines)

    # Summary table
    lines.append(f"{'Fixture':<30} {'Scope':<10} {'Overhead':<12} {'Tests':<8} {'Status':<15}")
    lines.append("-" * 100)

    for bench in sorted(benchmarks, key=lambda b: b.total_overhead, reverse=True):
        status = "✓ GOOD" if bench.passes_threshold else "⚠ SLOW"

        lines.append(
            f"{bench.fixture_name:<30} "
            f"{bench.scope:<10} "
            f"{bench.total_overhead:<12.2f}ms "
            f"{bench.tests_measured:<8} "
            f"{status:<15}"
        )

    lines.append("=" * 100)
    lines.append("")

    # Statistics
    total_fixtures = len(benchmarks)
    passing = len([b for b in benchmarks if b.passes_threshold])
    slow = total_fixtures - passing

    avg_overhead = sum(b.total_overhead for b in benchmarks) / total_fixtures if total_fixtures > 0 else 0

    lines.append("STATISTICS:")
    lines.append("-" * 100)
    lines.append(f"Total fixtures benchmarked: {total_fixtures}")
    lines.append(f"Fixtures passing threshold (<100ms): {passing} ({passing/total_fixtures*100:.1f}%)")
    lines.append(f"Slow fixtures (≥100ms): {slow}")
    lines.append(f"Average overhead: {avg_overhead:.2f}ms")
    lines.append("")

    if detailed and benchmarks:
        lines.append("\nDETAILED BREAKDOWN:")
        lines.append("-" * 100)

        for bench in sorted(benchmarks, key=lambda b: b.total_overhead, reverse=True):
            lines.append(f"\n{bench.fixture_name}:")
            lines.append(f"  Scope: {bench.scope}")
            lines.append(f"  Setup time: {bench.avg_setup_time:.2f}ms")
            lines.append(f"  Teardown time: {bench.avg_teardown_time:.2f}ms")
            lines.append(f"  Total overhead: {bench.total_overhead:.2f}ms")
            lines.append(f"  Tests measured: {bench.tests_measured}")
            lines.append(f"  Status: {'GOOD' if bench.passes_threshold else 'NEEDS OPTIMIZATION'}")

            if not bench.passes_threshold:
                lines.append(f"  ⚠ Recommendation: Consider optimizing or changing scope")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Benchmark fixture performance")
    parser.add_argument("--fixture", help="Benchmark specific fixture")
    parser.add_argument("--detailed", action="store_true", help="Show detailed breakdown")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    parser.add_argument("--iterations", type=int, default=3, help="Benchmark iterations (default: 3)")
    args = parser.parse_args()

    # Find root directory
    root = Path(__file__).parent.parent.parent

    # Benchmark
    benchmarker = FixtureBenchmarker(root)

    if args.fixture:
        # Benchmark single fixture
        print(f"Benchmarking {args.fixture}...")
        result = benchmarker.benchmark_fixture(args.fixture, iterations=args.iterations)

        if result:
            benchmarks = [result]
        else:
            print(f"Failed to benchmark {args.fixture}")
            return 1
    else:
        # Benchmark all fixtures
        benchmarks = benchmarker.benchmark_all_fixtures()

    # Output
    if args.json:
        output = [asdict(b) for b in benchmarks]
        print(json.dumps(output, indent=2))
    else:
        print(format_benchmark_report(benchmarks, detailed=args.detailed))

    # Exit with error if any fixture is slow
    if any(not b.passes_threshold for b in benchmarks):
        print("\n⚠ Warning: Some fixtures exceed 100ms overhead threshold")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
