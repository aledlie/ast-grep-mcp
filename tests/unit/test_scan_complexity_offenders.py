"""Tests for scripts/scan_complexity_offenders.py."""

import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.scan_complexity_offenders import _extract_name, _short_path, main


class TestExtractName:
    def test_simple_def(self):
        assert _extract_name("def foo(x, y):\n    return x + y") == "foo"

    def test_async_def(self):
        assert _extract_name("async def fetch_data(url):\n    pass") == "fetch_data"

    def test_decorated_function(self):
        code = "@cache\ndef compute(n):\n    return n * 2"
        assert _extract_name(code) == "compute"

    def test_decorated_async(self):
        code = "@lru_cache(maxsize=128)\nasync def resolve(key):\n    return key"
        assert _extract_name(code) == "resolve"

    def test_indented_method(self):
        code = "class Foo:\n    def bar(self):\n        pass"
        assert _extract_name(code) == "bar"

    def test_no_def_returns_unknown(self):
        assert _extract_name("x = 1\ny = 2") == "unknown"

    def test_empty_string(self):
        assert _extract_name("") == "unknown"


class TestShortPath:
    def test_feature_path(self):
        result = _short_path("src/ast_grep_mcp/features/complexity/analyzer.py")
        assert result == "complexity/analyzer.py"

    def test_core_path(self):
        result = _short_path("src/ast_grep_mcp/core/executor.py")
        assert result == "core/executor.py"

    def test_unrecognized_path_unchanged(self):
        result = _short_path("other/path/file.py")
        assert result == "other/path/file.py"


class TestProjectRoot:
    def test_project_root_is_absolute(self):
        from scripts.scan_complexity_offenders import _PROJECT_ROOT
        assert _PROJECT_ROOT.is_absolute()

    def test_project_root_exists(self):
        from scripts.scan_complexity_offenders import _PROJECT_ROOT
        assert _PROJECT_ROOT.exists()

    def test_project_root_cwd_independent(self, tmp_path, monkeypatch):
        """_PROJECT_ROOT must resolve correctly regardless of CWD."""
        monkeypatch.chdir(tmp_path)
        from scripts.scan_complexity_offenders import _PROJECT_ROOT
        assert _PROJECT_ROOT.exists()
        assert (_PROJECT_ROOT / "src").exists()


class TestMain:
    def _capture_main(self, extra_args: list[str] | None = None) -> str:
        argv = ["scan_complexity_offenders.py"] + (extra_args or [])
        with patch.object(sys, "argv", argv):
            buf = StringIO()
            with patch("sys.stdout", buf):
                main()
        return buf.getvalue()

    def test_outputs_markdown_table_header(self):
        output = self._capture_main()
        assert "| File | Function | Cyc | Cog | Nest | Len |" in output
        assert "|------|----------|-----|-----|------|-----|" in output

    def test_all_flag_produces_more_rows(self):
        default_output = self._capture_main()
        all_output = self._capture_main(["--all"])
        default_rows = [l for l in default_output.splitlines() if l.startswith("|") and "File" not in l and "---" not in l]
        all_rows = [l for l in all_output.splitlines() if l.startswith("|") and "File" not in l and "---" not in l]
        assert len(all_rows) >= len(default_rows)

    def test_default_only_shows_offenders(self):
        output = self._capture_main()
        # Each data row: | `path` | `name` | cyc | cog | nest | len |
        for line in output.splitlines():
            if not line.startswith("|") or "File" in line or "---" in line:
                continue
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) >= 4:
                cyc, cog, nest, length = int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])
                assert cyc > 10 or cog > 15 or nest > 4 or length > 50
