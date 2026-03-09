"""Scan complexity offenders and output a markdown table for BACKLOG.md.

Usage:
    uv run python scripts/scan_complexity_offenders.py [--all]

By default only prints functions exceeding thresholds (cyc>10, cog>15, nest>4, len>50).
With --all, prints every function from the scanned files.
"""

import sys

from ast_grep_mcp.features.complexity.metrics import (
    calculate_cognitive_complexity,
    calculate_cyclomatic_complexity,
    calculate_nesting_depth,
)
from ast_grep_mcp.features.complexity.analyzer import extract_functions_from_file

FILES = [
    "src/ast_grep_mcp/features/deduplication/applicator_backup.py",
    "src/ast_grep_mcp/features/refactoring/extractor.py",
    "src/ast_grep_mcp/core/executor.py",
    "src/ast_grep_mcp/features/condense/service.py",
    "src/ast_grep_mcp/features/deduplication/diff.py",
    "src/ast_grep_mcp/features/refactoring/analyzer.py",
    "src/ast_grep_mcp/features/complexity/analyzer.py",
]

CYC_THRESHOLD = 10
COG_THRESHOLD = 15
NEST_THRESHOLD = 4
LEN_THRESHOLD = 50


def _short_path(path: str) -> str:
    return path.replace("src/ast_grep_mcp/features/", "").replace("src/ast_grep_mcp/", "")


def _extract_name(code: str) -> str:
    if "(" in code:
        return code.split("(")[0].split()[-1]
    return "unknown"


def main() -> None:
    show_all = "--all" in sys.argv

    print("| File | Function | Cyc | Cog | Nest | Len |")
    print("|------|----------|-----|-----|------|-----|")

    for path in FILES:
        short = _short_path(path)
        funcs = extract_functions_from_file(path, "python")
        for f in funcs:
            code = f["text"]
            cyc = calculate_cyclomatic_complexity(code, "python")
            cog = calculate_cognitive_complexity(code, "python")
            nest = calculate_nesting_depth(code, "python")
            lines = code.count("\n") + 1
            name = _extract_name(code)

            exceeds = (
                cyc > CYC_THRESHOLD
                or cog > COG_THRESHOLD
                or nest > NEST_THRESHOLD
                or lines > LEN_THRESHOLD
            )

            if show_all or exceeds:
                print(f"| `{short}` | `{name}` | {cyc} | {cog} | {nest} | {lines} |")


if __name__ == "__main__":
    main()
