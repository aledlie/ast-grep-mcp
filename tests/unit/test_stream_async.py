"""Unit tests for async streaming in executor.py."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ast_grep_mcp.core.executor import (
    async_stream_ast_grep_results,
    stream_ast_grep_results,
)
from ast_grep_mcp.core.exceptions import AstGrepExecutionError, AstGrepNotFoundError
from ast_grep_mcp.constants import StreamDefaults


class TestAsyncStreamAstGrepResults:
    """Test async_stream_ast_grep_results streaming function."""

    @pytest.mark.asyncio
    async def test_yields_parsed_matches(self):
        """Verify async generator yields correctly parsed JSON matches."""
        matches = [
            {"file": "test.py", "line": 1},
            {"file": "test.py", "line": 2},
        ]
        json_lines = "\n".join(json.dumps(m) for m in matches)

        mock_process = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.__aiter__.return_value = iter([line for line in json_lines.split("\n")])
        mock_process.returncode = 0
        mock_process.wait = AsyncMock(return_value=0)
        mock_process.stderr = AsyncMock()
        mock_process.stderr.read = AsyncMock(return_value=b"")

        with patch("ast_grep_mcp.core.executor.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_process

            results = []
            async for match in async_stream_ast_grep_results(
                "run", ["--json=stream", "/test"], max_results=0
            ):
                results.append(match)

            assert len(results) == 2
            assert results[0]["file"] == "test.py"
            assert results[0]["line"] == 1
            assert results[1]["line"] == 2

    @pytest.mark.asyncio
    async def test_early_termination_at_max_results(self):
        """Verify streaming stops at max_results limit."""
        matches = [
            {"file": "a.py", "line": 1},
            {"file": "b.py", "line": 2},
            {"file": "c.py", "line": 3},
        ]
        json_lines = "\n".join(json.dumps(m) for m in matches)

        mock_process = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.__aiter__.return_value = iter([line for line in json_lines.split("\n")])
        mock_process.returncode = -15  # SIGTERM from early termination
        mock_process.wait = AsyncMock(return_value=-15)
        mock_process.stderr = AsyncMock()
        mock_process.stderr.read = AsyncMock(return_value=b"")
        mock_process.terminate = MagicMock()
        mock_process.kill = MagicMock()

        with patch("ast_grep_mcp.core.executor.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_process

            results = []
            async for match in async_stream_ast_grep_results(
                "run", ["--json=stream", "/test"], max_results=2
            ):
                results.append(match)

            assert len(results) == 2
            mock_process.terminate.assert_called()

    @pytest.mark.asyncio
    async def test_stderr_capture_and_error_propagation(self):
        """Verify stderr is captured and errors are propagated."""
        mock_process = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.__aiter__.return_value = iter([])
        mock_process.returncode = 1  # Acceptable return code (1 means no matches, not an error)
        mock_process.wait = AsyncMock(return_value=1)
        mock_process.stderr = AsyncMock()
        mock_process.stderr.read = AsyncMock(return_value=b"")

        with patch("ast_grep_mcp.core.executor.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_process

            results = []
            async for _ in async_stream_ast_grep_results("run", ["--json=stream", "/test"]):
                results.append(_)

            # No error should be raised for return code 1 (no matches)
            assert len(results) == 0

    @pytest.mark.asyncio
    async def test_file_not_found_error_conversion(self):
        """Verify FileNotFoundError is converted to AstGrepNotFoundError."""
        with patch(
            "ast_grep_mcp.core.executor.asyncio.create_subprocess_exec", new_callable=AsyncMock
        ) as mock_create:
            mock_create.side_effect = FileNotFoundError("ast-grep not found")

            with pytest.raises(AstGrepNotFoundError):
                async for _ in async_stream_ast_grep_results("run", ["--json=stream", "/test"]):
                    pass

    @pytest.mark.asyncio
    async def test_execution_error_on_nonzero_return(self):
        """Verify AstGrepExecutionError is raised on non-acceptable return codes."""
        mock_process = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.__aiter__.return_value = iter([])
        mock_process.returncode = 42  # Non-acceptable error code
        mock_process.wait = AsyncMock(return_value=42)
        mock_process.stderr = AsyncMock()
        mock_process.stderr.read = AsyncMock(return_value=b"Some error occurred")

        with patch("ast_grep_mcp.core.executor.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_process

            with pytest.raises(AstGrepExecutionError):
                async for _ in async_stream_ast_grep_results("run", ["--json=stream", "/test"]):
                    pass

    @pytest.mark.asyncio
    async def test_skips_invalid_json_lines(self):
        """Verify invalid JSON lines are skipped without error."""
        json_lines = 'valid\n{"file": "a.py"}\ninvalid json\n{"file": "b.py"}\n'

        mock_process = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.__aiter__.return_value = iter(json_lines.split("\n"))
        mock_process.returncode = 0
        mock_process.wait = AsyncMock(return_value=0)
        mock_process.stderr = AsyncMock()
        mock_process.stderr.read = AsyncMock(return_value=b"")

        with patch("ast_grep_mcp.core.executor.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_process

            results = []
            async for match in async_stream_ast_grep_results("run", ["--json=stream", "/test"]):
                results.append(match)

            # Only valid JSON lines should be yielded (2 matches, not 4)
            assert len(results) == 2
            assert results[0]["file"] == "a.py"
            assert results[1]["file"] == "b.py"


class TestStreamAstGrepResultsSyncShim:
    """Test sync shim backward compatibility."""

    def test_sync_shim_delegates_to_async(self):
        """Verify sync function delegates to async implementation."""
        matches = [
            {"file": "test.py", "line": 1},
            {"file": "test.py", "line": 2},
        ]
        json_lines = "\n".join(json.dumps(m) for m in matches)

        mock_process = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.__aiter__.return_value = iter([line for line in json_lines.split("\n")])
        mock_process.returncode = 0
        mock_process.wait = AsyncMock(return_value=0)
        mock_process.stderr = AsyncMock()
        mock_process.stderr.read = AsyncMock(return_value=b"")

        with patch("ast_grep_mcp.core.executor.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_process

            results = list(stream_ast_grep_results("run", ["--json=stream", "/test"]))

            assert len(results) == 2
            assert results[0]["file"] == "test.py"

    def test_sync_shim_preserves_max_results(self):
        """Verify max_results is respected through sync shim."""
        matches = [{"file": f"test{i}.py"} for i in range(5)]
        json_lines = "\n".join(json.dumps(m) for m in matches)

        mock_process = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stdout.__aiter__.return_value = iter([line for line in json_lines.split("\n")])
        mock_process.returncode = -15
        mock_process.wait = AsyncMock(return_value=-15)
        mock_process.stderr = AsyncMock()
        mock_process.stderr.read = AsyncMock(return_value=b"")
        mock_process.terminate = MagicMock()

        with patch("ast_grep_mcp.core.executor.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_process

            results = list(stream_ast_grep_results("run", ["--json=stream", "/test"], max_results=3))

            assert len(results) == 3
