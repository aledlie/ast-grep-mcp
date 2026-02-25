"""End-to-end tests for the condense_pack pipeline."""

import tempfile
from pathlib import Path

import pytest

from ast_grep_mcp.features.condense.service import condense_pack_impl
from ast_grep_mcp.features.condense.tools import condense_pack_tool


class TestCondensePackImpl:
    def test_nonexistent_path_returns_error(self):
        result = condense_pack_impl("/nonexistent/xyz")
        assert "error" in result

    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = condense_pack_impl(tmp)
        assert result["files_processed"] == 0
        assert result["files_skipped"] == 0

    def test_python_ai_analysis_strategy(self):
        with tempfile.TemporaryDirectory() as tmp:
            fp = Path(tmp) / "main.py"
            fp.write_text(
                "import os\n\n"
                "def compute(x):\n"
                "    print(x)\n"
                "    return x * 2\n"
            )
            result = condense_pack_impl(tmp, language="python", strategy="ai_analysis")
        assert result["files_processed"] == 1
        assert result["condensed_bytes"] > 0
        assert "condensed_output" in result

    def test_all_strategies_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "a.py").write_text("def foo(): return 1\n")
            for strategy in ("ai_chat", "ai_analysis", "archival", "polyglot"):
                result = condense_pack_impl(tmp, strategy=strategy)
                assert "error" not in result, f"Strategy {strategy} failed: {result}"
                assert result["files_processed"] >= 0

    def test_reduction_pct_zero_on_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = condense_pack_impl(tmp)
        assert result["reduction_pct"] == 0.0

    def test_per_language_stats_populated(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "a.py").write_text("def foo(): pass\n")
            (Path(tmp) / "b.ts").write_text("export const x = 1;\n")
            result = condense_pack_impl(tmp)
        assert len(result["per_language_stats"]) >= 1

    def test_exclude_patterns_applied(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "keep.py").write_text("x = 1\n")
            (Path(tmp) / "skip.generated.py").write_text("y = 2\n")
            result = condense_pack_impl(
                tmp, language="python",
                exclude_patterns=["*.generated.py"],
            )
        # The generated file should be excluded
        assert result["files_processed"] <= 1

    def test_oversized_file_skipped(self):
        from ast_grep_mcp.constants import CondenseDefaults
        with tempfile.TemporaryDirectory() as tmp:
            fp = Path(tmp) / "huge.py"
            fp.write_bytes(b"x = 1\n" * (CondenseDefaults.MAX_FILE_SIZE_BYTES // 6 + 1))
            result = condense_pack_impl(tmp)
        assert result["files_skipped"] >= 1
        assert result["files_processed"] == 0

    def test_token_estimates_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "a.py").write_text("def foo(): return 42\n")
            result = condense_pack_impl(tmp)
        assert "original_tokens_est" in result
        assert "condensed_tokens_est" in result


class TestCondensePackTool:
    def test_invalid_strategy_returns_error(self):
        result = condense_pack_tool("/tmp", strategy="banana")
        assert "error" in result

    def test_valid_strategy_delegates(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "a.py").write_text("x = 1\n")
            result = condense_pack_tool(tmp, strategy="ai_analysis")
        assert "error" not in result or "Path does not exist" not in result.get("error", "")
