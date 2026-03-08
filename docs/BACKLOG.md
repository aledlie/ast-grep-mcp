# Backlog

## Complexity Refactoring Queue (2026-03-08 refresh)

100 functions exceeding thresholds across 120 files (1,770 total). Thresholds: cyc >10, cog >15, nest >4, len >50.

Previous baselines: **434** (2026-03-04) -> **407** (2026-03-06) -> **100** (2026-03-08). ~75% reduction from prior refactoring commits.

Refresh: `uv run python scripts/run_all_analysis.py`

### Top 10 Functions by Cognitive Complexity

| File | Cyc | Cog | Nest | Len |
|------|-----|-----|------|-----|
| `deduplication/applicator_executor.py` | 12 | 33 | 6 | 59 |
| `deduplication/applicator_backup.py` | 9 | 33 | 6 | 45 |
| `refactoring/extractor.py` | 13 | 31 | 5 | 53 |
| `documentation/changelog_generator.py` | 20 | 30 | 5 | 58 |
| `core/executor.py` | 16 | 29 | 6 | 101 |
| `condense/service.py` | 15 | 29 | 5 | 115 |
| `deduplication/diff.py` | 14 | 29 | 5 | 53 |
| `refactoring/analyzer.py` | 11 | 29 | 5 | 49 |
| `condense/service.py` | 17 | 28 | 5 | 33 |
| `quality/fixer.py` | 14 | 27 | 4 | 36 |

Function names unavailable in summary output (analyzer reports `unknown`). Use per-file complexity analysis for function-level detail:
`uv run python -c "from ast_grep_mcp.features.complexity.tools import analyze_complexity_tool; print(analyze_complexity_tool('/path/to/file', 'python'))"`
