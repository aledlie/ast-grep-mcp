# Backlog


## Complexity Refactoring Queue (2026-03-08 refresh)

Thresholds: cyc >10, cog >15, nest >4, len >50.

Previous baselines: **434** (2026-03-04) → **407** (2026-03-06) → **100** (2026-03-08).

### Recently Resolved

Commits `52b1f3f`..`751e2bc` addressed 4 of the top 10 offenders:

- **`deduplication/applicator_executor.py`** (was cog=33) — extracted loop bodies into `_create_single_file`, `_update_single_file`, `_apply_import_addition`; removed duplicated import logic. Worst remaining: cog=16.
- **`documentation/changelog_generator.py`** (was cog=30) — extracted `_get_commits`, `_group_commits_by_version`, `_format_changelog_entry` helpers; added unit tests. Worst remaining: `_format_conventional_section` cog=18.
- **`quality/tools.py`** — reduced complexity across enforcement tools. Worst remaining: `create_linting_rule_tool` cog=18, `list_rule_templates_tool` cog=17.
- **`complexity/analyzer.py`** — reduced complexity in analysis functions. `extract_functions_from_file` simplified from cog=23→15 via list comprehension (`0f48536`). Worst remaining: `_find_magic_numbers` cog=25.

### Remaining Top Offenders

| File | Function | Cyc | Cog | Nest | Len |
|------|----------|-----|-----|------|-----|
| `deduplication/applicator_backup.py` | — | 9 | 33 | 6 | 45 |
| `refactoring/extractor.py` | — | 13 | 31 | 5 | 53 |
| `core/executor.py` | — | 16 | 29 | 6 | 101 |
| `condense/service.py` | — | 15 | 29 | 5 | 115 |
| `deduplication/diff.py` | — | 14 | 29 | 5 | 53 |
| `refactoring/analyzer.py` | — | 11 | 29 | 5 | 49 |
| `condense/service.py` | — | 17 | 28 | 5 | 33 |
| `complexity/analyzer.py` | `_find_magic_numbers` | 13 | 25 | 5 | 61 |
| `complexity/analyzer.py` | `_find_docstring_extent` | 11 | 21 | 4 | 28 |

Refresh: `uv run python scripts/run_all_analysis.py`

## Duplicate Detection Precision (2026-03-08)

All 5 groups from latest `find_duplication` run (sim >= 0.82) are false positives or low-value. Common causes: trivial constructors, intentionally parallel APIs, thin semantic wrappers, and strategy pattern boilerplate.

See [docs/duplicate-detector-misses.md](duplicate-detector-misses.md) for full investigation and recommended detector improvements:
- Exclude short `__init__` methods
- Discount methods delegating to shared helpers
- Reduce weight for strategy pattern implementations
- Add minimum line savings threshold
- Consider excluding parallel `to_*` formatters

## changelog_generator.py Hardening (2026-03-08)

### Resolved
- ~~Validate `project_folder` exists in `_run_git_command`~~ — Added `os.path.isdir()` check
- ~~Replace empty string sentinel in `_get_first_commit` with `str | None`~~ — `_get_first_commit` and `_find_previous_tag` now return `str | None`

### Open
- **`from_version` resolution asymmetry** — `_get_commit_range` only tries v-prefix for `from_version`, falling back to raw string passthrough. `to_version` uses full `_resolve_version_ref`. Fix: use `_resolve_version_ref` for both. See [KNOWN_ISSUES.md](KNOWN_ISSUES.md).

## ~~Test & Documentation Quality~~ (2026-03-08, Resolved)

- ~~Per-method imports in TestChangelogHelpers~~ — Moved `from unittest.mock import patch` to module level
- ~~Add test for `_run_git_command` with invalid `cwd`~~ — Added `test_run_git_command_invalid_cwd` (passing, not xfail — bug is fixed)
- ~~KNOWN_ISSUES.md: replace hardcoded line numbers with function names~~ — Done
- ~~Clarify test name~~ — Renamed to `test_find_previous_tag_empty_tag_list`
- ~~Resolve `Optional[str]` vs `str | None` terminology~~ — Standardized on `str | None` (Python 3.13+)
