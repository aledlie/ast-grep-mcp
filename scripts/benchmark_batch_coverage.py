#!/usr/bin/env python3
"""Benchmark batch test coverage detection performance.

This script compares the performance of:
1. Legacy sequential test coverage detection
2. Legacy parallel test coverage detection
3. Optimized batch sequential detection
4. Optimized batch parallel detection

Expected Results:
- Batch sequential: 40-50% faster than legacy sequential
- Batch parallel: 60-80% faster than legacy sequential
"""
import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List

from ast_grep_mcp.utils.console_logger import console

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ast_grep_mcp.features.deduplication.analysis_orchestrator import DeduplicationAnalysisOrchestrator
from ast_grep_mcp.features.deduplication.coverage import CoverageDetector


def create_test_candidates(file_count: int, files_per_candidate: int) -> List[Dict]:
    """Create mock candidates for benchmarking.

    Args:
        file_count: Total number of unique files
        files_per_candidate: Number of files per candidate

    Returns:
        List of candidate dictionaries
    """
    project_root_path = Path(__file__).parent.parent
    src_path = project_root_path / "src" / "ast_grep_mcp"

    # Get actual Python files from the project
    all_files = list(src_path.rglob("*.py"))[:file_count]

    if len(all_files) < file_count:
        console.warning(f"Warning: Only found {len(all_files)} files, requested {file_count}")
        file_count = len(all_files)

    # Create candidates with overlapping files (realistic scenario)
    candidates = []
    for i in range(0, file_count, files_per_candidate):
        file_slice = all_files[i:i + files_per_candidate]
        if file_slice:
            candidates.append({
                "id": f"candidate_{i}",
                "files": [str(f) for f in file_slice],
                "similarity": 0.85,
                "lines_saved": 50
            })

    return candidates


def benchmark_legacy_sequential(
    detector: CoverageDetector,
    candidates: List[Dict],
    project_path: str
) -> Dict:
    """Benchmark legacy sequential test coverage detection."""
    start = time.perf_counter()

    for candidate in candidates:
        files = candidate.get("files", [])
        if files:
            coverage_map = detector.get_test_coverage_for_files(
                files, "python", project_path
            )
            candidate["test_coverage"] = coverage_map
            candidate["has_tests"] = any(coverage_map.values())

    elapsed = time.perf_counter() - start

    return {
        "method": "legacy_sequential",
        "elapsed_seconds": elapsed,
        "candidates": len(candidates),
        "total_files": sum(len(c.get("files", [])) for c in candidates)
    }


def benchmark_legacy_parallel(
    orchestrator: DeduplicationAnalysisOrchestrator,
    candidates: List[Dict],
    project_path: str
) -> Dict:
    """Benchmark legacy parallel test coverage detection."""
    start = time.perf_counter()

    orchestrator._add_test_coverage(
        candidates,
        "python",
        project_path,
        parallel=True,
        max_workers=4
    )

    elapsed = time.perf_counter() - start

    return {
        "method": "legacy_parallel",
        "elapsed_seconds": elapsed,
        "candidates": len(candidates),
        "total_files": sum(len(c.get("files", [])) for c in candidates)
    }


def benchmark_batch_sequential(
    orchestrator: DeduplicationAnalysisOrchestrator,
    candidates: List[Dict],
    project_path: str
) -> Dict:
    """Benchmark optimized batch sequential detection."""
    start = time.perf_counter()

    orchestrator._add_test_coverage_batch(
        candidates,
        "python",
        project_path,
        parallel=False
    )

    elapsed = time.perf_counter() - start

    return {
        "method": "batch_sequential",
        "elapsed_seconds": elapsed,
        "candidates": len(candidates),
        "total_files": sum(len(c.get("files", [])) for c in candidates)
    }


def benchmark_batch_parallel(
    orchestrator: DeduplicationAnalysisOrchestrator,
    candidates: List[Dict],
    project_path: str
) -> Dict:
    """Benchmark optimized batch parallel detection."""
    start = time.perf_counter()

    orchestrator._add_test_coverage_batch(
        candidates,
        "python",
        project_path,
        parallel=True,
        max_workers=4
    )

    elapsed = time.perf_counter() - start

    return {
        "method": "batch_parallel",
        "elapsed_seconds": elapsed,
        "candidates": len(candidates),
        "total_files": sum(len(c.get("files", [])) for c in candidates)
    }


def run_benchmark_suite(
    file_count: int,
    files_per_candidate: int,
    project_path: str
) -> Dict:
    """Run complete benchmark suite.

    Args:
        file_count: Number of unique files to test
        files_per_candidate: Files per candidate
        project_path: Project root path

    Returns:
        Dictionary with all benchmark results
    """
    console.log(f"\n{'='*80}")
    console.log(f"Benchmarking with {file_count} files, {files_per_candidate} files/candidate")
    console.log(f"{'='*80}\n")

    detector = CoverageDetector()
    orchestrator = DeduplicationAnalysisOrchestrator()

    results = {
        "config": {
            "file_count": file_count,
            "files_per_candidate": files_per_candidate,
            "project_path": project_path
        },
        "benchmarks": []
    }

    # Test 1: Legacy Sequential
    console.log("1. Testing legacy sequential method...")
    candidates = create_test_candidates(file_count, files_per_candidate)
    result = benchmark_legacy_sequential(detector, candidates, project_path)
    results["benchmarks"].append(result)
    console.log(f"   Time: {result['elapsed_seconds']:.3f}s")

    # Test 2: Legacy Parallel
    console.log("2. Testing legacy parallel method...")
    candidates = create_test_candidates(file_count, files_per_candidate)
    result = benchmark_legacy_parallel(orchestrator, candidates, project_path)
    results["benchmarks"].append(result)
    console.log(f"   Time: {result['elapsed_seconds']:.3f}s")

    # Test 3: Batch Sequential
    console.log("3. Testing batch sequential method...")
    candidates = create_test_candidates(file_count, files_per_candidate)
    result = benchmark_batch_sequential(orchestrator, candidates, project_path)
    results["benchmarks"].append(result)
    console.log(f"   Time: {result['elapsed_seconds']:.3f}s")

    # Test 4: Batch Parallel
    console.log("4. Testing batch parallel method...")
    candidates = create_test_candidates(file_count, files_per_candidate)
    result = benchmark_batch_parallel(orchestrator, candidates, project_path)
    results["benchmarks"].append(result)
    console.log(f"   Time: {result['elapsed_seconds']:.3f}s")

    # Calculate speedups
    baseline = results["benchmarks"][0]["elapsed_seconds"]
    console.log(f"\n{'='*80}")
    console.log("Performance Summary:")
    console.log(f"{'='*80}")
    for benchmark in results["benchmarks"]:
        speedup = baseline / benchmark["elapsed_seconds"]
        improvement = ((baseline - benchmark["elapsed_seconds"]) / baseline) * 100
        console.log(f"{benchmark['method']:25s}: {benchmark['elapsed_seconds']:6.3f}s "
              f"({speedup:.2f}x speedup, {improvement:+5.1f}% improvement)")

    results["speedups"] = {
        b["method"]: {
            "speedup": baseline / b["elapsed_seconds"],
            "improvement_percent": ((baseline - b["elapsed_seconds"]) / baseline) * 100
        }
        for b in results["benchmarks"]
    }

    return results


def main():
    """Main benchmark runner."""
    parser = argparse.ArgumentParser(
        description="Benchmark batch test coverage detection performance"
    )
    parser.add_argument(
        "--file-count",
        type=int,
        default=50,
        help="Number of unique files to test (default: 50)"
    )
    parser.add_argument(
        "--files-per-candidate",
        type=int,
        default=5,
        help="Files per candidate (default: 5)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Save results to JSON file"
    )
    parser.add_argument(
        "--compare",
        type=str,
        help="Compare with baseline JSON file"
    )

    args = parser.parse_args()

    project_path = str(Path(__file__).parent.parent)

    # Run benchmarks
    results = run_benchmark_suite(
        args.file_count,
        args.files_per_candidate,
        project_path
    )

    # Save results if requested
    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)
        console.log(f"\nResults saved to {output_path}")

    # Compare with baseline if requested
    if args.compare:
        baseline_path = Path(args.compare)
        if baseline_path.exists():
            with open(baseline_path, "r") as f:
                baseline_results = json.load(f)

            console.log(f"\n{'='*80}")
            console.log("Comparison with Baseline:")
            console.log(f"{'='*80}")

            for method in ["legacy_sequential", "batch_parallel"]:
                baseline_bench = next(
                    (b for b in baseline_results["benchmarks"] if b["method"] == method),
                    None
                )
                current_bench = next(
                    (b for b in results["benchmarks"] if b["method"] == method),
                    None
                )

                if baseline_bench and current_bench:
                    baseline_time = baseline_bench["elapsed_seconds"]
                    current_time = current_bench["elapsed_seconds"]
                    change = ((current_time - baseline_time) / baseline_time) * 100

                    console.log(f"{method:25s}: "
                          f"{baseline_time:.3f}s -> {current_time:.3f}s "
                          f"({change:+5.1f}% change)")
        else:
            console.log(f"Baseline file not found: {baseline_path}")

    # Print expected vs actual
    console.log(f"\n{'='*80}")
    console.log("Expected vs Actual Performance:")
    console.log(f"{'='*80}")

    batch_parallel = next(
        (b for b in results["benchmarks"] if b["method"] == "batch_parallel"),
        None
    )

    if batch_parallel:
        speedup = results["speedups"]["batch_parallel"]["speedup"]
        improvement = results["speedups"]["batch_parallel"]["improvement_percent"]

        console.log("Expected: 60-80% improvement")
        console.log(f"Actual:   {improvement:.1f}% improvement ({speedup:.2f}x speedup)")

        if improvement >= 60:
            console.success("✓ PASSED: Performance goal achieved!")
        elif improvement >= 40:
            console.log("⚠ PARTIAL: Good improvement, but below 60% target")
        else:
            console.error("✗ FAILED: Performance improvement below expectations")


if __name__ == "__main__":
    main()
