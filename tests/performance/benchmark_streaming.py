"""Performance benchmarking for asyncio subprocess streaming (LM-05).

Measures:
- Throughput: matches/second
- Memory efficiency: streaming vs. buffering
- Early termination: latency to stop at max_results
- Error handling: overhead of error detection

Usage:
    pytest tests/performance/benchmark_streaming.py -v --benchmark-only
    pytest tests/performance/benchmark_streaming.py -v --benchmark-compare
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from ast_grep_mcp.core.executor import async_stream_ast_grep_results, stream_ast_grep_results


class TestStreamingBenchmark:
    """Benchmark async streaming implementation."""

    @pytest.mark.benchmark(group="streaming")
    def test_sync_shim_1k_matches(self, benchmark):
        """Benchmark sync shim with 1,000 matches."""
        matches = [{"file": f"test{i}.py", "line": i, "column": 0} for i in range(1000)]
        json_lines = "\n".join(json.dumps(m) for m in matches)

        mock_process = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.__aiter__.return_value = iter(json_lines.split("\n"))
        mock_process.returncode = 0
        mock_process.wait = AsyncMock(return_value=0)
        mock_process.stderr = AsyncMock()
        mock_process.stderr.read = AsyncMock(return_value=b"")

        def run_sync_stream():
            with patch("ast_grep_mcp.core.executor.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_create:
                mock_create.return_value = mock_process
                return list(stream_ast_grep_results("run", ["--json=stream", "/test"]))

        result = benchmark(run_sync_stream)
        assert len(result) == 1000

    @pytest.mark.benchmark(group="streaming")
    @pytest.mark.asyncio
    async def test_async_streaming_1k_matches(self, benchmark):
        """Benchmark async streaming with 1,000 matches."""
        matches = [{"file": f"test{i}.py", "line": i, "column": 0} for i in range(1000)]
        json_lines = "\n".join(json.dumps(m) for m in matches)

        mock_process = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.__aiter__.return_value = iter(json_lines.split("\n"))
        mock_process.returncode = 0
        mock_process.wait = AsyncMock(return_value=0)
        mock_process.stderr = AsyncMock()
        mock_process.stderr.read = AsyncMock(return_value=b"")

        async def run_async_stream():
            with patch("ast_grep_mcp.core.executor.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_create:
                mock_create.return_value = mock_process
                results = []
                async for match in async_stream_ast_grep_results("run", ["--json=stream", "/test"]):
                    results.append(match)
                return results

        result = await benchmark.pedantic(run_async_stream, rounds=5, iterations=1)
        assert len(result) == 1000

    @pytest.mark.benchmark(group="streaming")
    def test_sync_shim_early_termination_at_100(self, benchmark):
        """Benchmark early termination at max_results=100 (1K available)."""
        matches = [{"file": f"test{i}.py", "line": i} for i in range(1000)]
        json_lines = "\n".join(json.dumps(m) for m in matches)

        mock_process = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.__aiter__.return_value = iter(json_lines.split("\n"))
        mock_process.returncode = -15  # SIGTERM from early termination
        mock_process.wait = AsyncMock(return_value=-15)
        mock_process.stderr = AsyncMock()
        mock_process.stderr.read = AsyncMock(return_value=b"")
        mock_process.terminate = lambda: None

        def run_early_term():
            with patch("ast_grep_mcp.core.executor.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_create:
                mock_create.return_value = mock_process
                return list(stream_ast_grep_results("run", ["--json=stream", "/test"], max_results=100))

        result = benchmark(run_early_term)
        assert len(result) == 100

    @pytest.mark.benchmark(group="streaming")
    def test_sync_shim_invalid_json_skipping(self, benchmark):
        """Benchmark JSON parse error handling (100 valid, 100 invalid)."""
        valid = [{"file": f"test{i}.py"} for i in range(50)]
        invalid = ["invalid json"] * 50

        # Interleave valid and invalid
        json_lines_list = []
        for i in range(50):
            json_lines_list.append(json.dumps(valid[i]))
            json_lines_list.append(invalid[i])
        json_lines = "\n".join(json_lines_list)

        mock_process = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.__aiter__.return_value = iter(json_lines.split("\n"))
        mock_process.returncode = 0
        mock_process.wait = AsyncMock(return_value=0)
        mock_process.stderr = AsyncMock()
        mock_process.stderr.read = AsyncMock(return_value=b"")

        def run_with_errors():
            with patch("ast_grep_mcp.core.executor.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_create:
                mock_create.return_value = mock_process
                return list(stream_ast_grep_results("run", ["--json=stream", "/test"]))

        result = benchmark(run_with_errors)
        assert len(result) == 50

    @pytest.mark.benchmark(group="streaming")
    def test_sync_shim_memory_efficiency(self, benchmark):
        """Benchmark memory usage: streaming yields incrementally vs. buffering all."""
        matches = [{"file": f"test{i}.py", "line": i, "data": "x" * 100} for i in range(100)]
        json_lines = "\n".join(json.dumps(m) for m in matches)

        mock_process = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.__aiter__.return_value = iter(json_lines.split("\n"))
        mock_process.returncode = 0
        mock_process.wait = AsyncMock(return_value=0)
        mock_process.stderr = AsyncMock()
        mock_process.stderr.read = AsyncMock(return_value=b"")

        def iterate_streaming():
            """Iterate results (streaming), not collect all at once."""
            with patch("ast_grep_mcp.core.executor.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_create:
                mock_create.return_value = mock_process
                count = 0
                for _ in stream_ast_grep_results("run", ["--json=stream", "/test"]):
                    count += 1
                return count

        result = benchmark(iterate_streaming)
        assert result == 100
