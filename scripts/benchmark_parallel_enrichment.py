#!/usr/bin/env python3
"""Benchmark parallel vs sequential enrichment performance."""

import time
from typing import Any, Dict, List
from ast_grep_mcp.utils.console_logger import console

# Mock data for benchmarking
def create_mock_candidates(count: int) -> List[Dict[str, Any]]:
    """Create mock candidates for benchmarking."""

    return [
        {
            "group_id": i,
            "files": [f"file_{i}_1.py", f"file_{i}_2.py"],
            "lines_saved": 50,
            "score": 75.5,
            "complexity_score": 8,
            "has_tests": False
        }
        for i in range(count)
    ]


def benchmark_enrichment():
    """Benchmark parallel vs sequential enrichment."""
    from ast_grep_mcp.features.deduplication.analysis_orchestrator import (
        DeduplicationAnalysisOrchestrator
    )

    orchestrator = DeduplicationAnalysisOrchestrator()

    # Test with different candidate counts
    candidate_counts = [10, 25, 50, 100]

    console.log("=" * 70)
    console.log("Parallel vs Sequential Enrichment Benchmark")
    console.log("=" * 70)
    console.blank()

    for count in candidate_counts:
        candidates = create_mock_candidates(count)

        # Sequential execution
        start = time.perf_counter()
        orchestrator._add_test_coverage(
            candidates.copy(),
            "python",
            "/tmp/test",
            parallel=False
        )
        orchestrator._add_recommendations(
            candidates.copy(),
            parallel=False
        )
        sequential_time = time.perf_counter() - start

        # Parallel execution
        candidates = create_mock_candidates(count)
        start = time.perf_counter()
        orchestrator._add_test_coverage(
            candidates.copy(),
            "python",
            "/tmp/test",
            parallel=True
        )
        orchestrator._add_recommendations(
            candidates.copy(),
            parallel=True
        )
        parallel_time = time.perf_counter() - start

        # Calculate speedup
        speedup = sequential_time / parallel_time if parallel_time > 0 else 0
        improvement = ((sequential_time - parallel_time) / sequential_time * 100) if sequential_time > 0 else 0

        console.log(f"Candidates: {count}")
        console.log(f"  Sequential: {sequential_time*1000:.2f}ms")
        console.log(f"  Parallel:   {parallel_time*1000:.2f}ms")
        console.log(f"  Speedup:    {speedup:.2f}x")
        console.log(f"  Improvement: {improvement:.1f}%")
        console.blank()

    console.log("=" * 70)
    console.log("Note: Actual speedup depends on I/O operations and CPU cores.")
    console.log("=" * 70)


if __name__ == "__main__":
    benchmark_enrichment()
