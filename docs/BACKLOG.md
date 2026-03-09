# Backlog


## Complexity Refactoring Queue (2026-03-08 refresh)

Thresholds: cyc >10, cog >15, nest >4, len >50.

Previous baselines: **434** (2026-03-04) → **407** (2026-03-06) → **100** (2026-03-08) → **80** (2026-03-08 shared-util).

### Recently Resolved

**Shared utility extractions (`e74b8de`..`a97f344`):**

- **`FilePatterns.normalize_excludes()`** — staticmethod on `constants.py:FilePatterns`. Consolidates all `_normalize_exclude_patterns` functions across quality, complexity, deduplication, and documentation tools. Dedup migrated from substring-match to glob format. Simplified in `a97f344` to use `DEFAULT_EXCLUDE` directly as default arg, removing None-as-sentinel pattern; `_DEDUP_EXCLUDE_DEFAULTS` removed (strict subset of shared default).
- **`utils/tool_context.py`** — extracted `tool_context`/`async_tool_context` context managers (timing + error logging + Sentry capture). Adopted by complexity (3 tools), condense (6 tools), documentation (5 tools), schema (9 async tools). `status="failed"` added to error log. Optional `logger` param added (`ad109ab`) to avoid redundant `get_logger` calls. Unit tests: `tests/unit/test_tool_context.py` (8 tests).
- **`utils/text.py`** — promoted `indent_lines`, `read_file_lines`, `write_file_lines` to shared utils (`eac6227`). Replaced 7 inline open()/readlines()/writelines() patterns and 3 duplicate indent implementations. Widened to accept `PathLike`; added atomic write via temp-file-then-rename (`a97f344`).
- **`quality/tools.py`** — removed `_tool_context` (28 lines), `_normalize_exclude_patterns`, `_create_mcp_field_definitions`; `Field()` inlined into `@mcp.tool()` wrappers.
- **`complexity/tools.py`** — removed `_log_tool_error`, `_get_default_complexity_exclude_patterns`, `DisplayDefaults` import.

**Bug fixes and hardening (`ad109ab`):**

- **`schema/enhancement_service.py`** — restored `sentry_sdk.capture_exception` in `analyze_entity_graph` (was removed prematurely in `e74b8de` when async_tool_context was added at tool layer).
- **`documentation/changelog_generator.py`** — fixed `from_version` resolution asymmetry: `_get_commit_range` now uses `_resolve_version_ref` for both `from_version` and `to_version`.

**Infra and test fixes (`783f5f6`..`a5c7879`):**

- **Benchmark test stability** — replaced flaky speedup-ratio assertion with absolute ceiling (500ms) for cache-hit benchmark.
- **Repomix scripts** — fixed ROOT path, script name references, config file paths across `repomix-regen.sh`, `generate-repomix-docs.sh`, `generate-repomix-git-ranked.sh`.
- **Docs refresh** — updated test count (1,622), module count (10), sentry init location, benchmark test path; deleted stale `schema/tools.py.backup` (849 lines).

Commits `52b1f3f`..`70a4762` addressed 6 complexity hotspot areas:

- **`deduplication/applicator_executor.py`** (was cog=33) — extracted loop bodies into `_create_single_file`, `_update_single_file`, `_apply_import_addition`; removed duplicated import logic. Worst remaining: cog=16.
- **`documentation/changelog_generator.py`** (was cog=30) — extracted `_get_commits`, `_group_commits_by_version`, `_format_changelog_entry` helpers; added unit tests. Hardened with `str | None` types (`1b5f331`). Worst remaining: `_format_conventional_section` cog=18.
- **`quality/tools.py`** — extracted `_tool_context` context manager, split `register_quality_tools` into per-domain helpers (`d09f996`). Worst remaining: `create_linting_rule_tool` cog=18.
- **`complexity/analyzer.py`** — `extract_functions_from_file` cog=23→15 (`0f48536`); added `_count_docstring_lines` helper (`d09f996`). Worst remaining: `_find_magic_numbers` cog=25.
- **`refactoring/analyzer.py`** (was cog=29) — moved keyword sets to class-level frozensets; extracted `_register_variable` and `_scan_and_register_identifiers`; collapsed duplicate Java branch (`60caecf`). Worst remaining: `_find_python_base_variables` cog=25.
- **`deduplication/detector.py`** — extracted `_match_line`, `_format_instance` helpers; moved strategy tables to class-level constants (`8415bec`).

### Remaining Top Offenders (live scan)

| File | Function | Cyc | Cog | Nest | Len |
|------|----------|-----|-----|------|-----|
| `deduplication/applicator_backup.py` | `cleanup_old_backups` | 9 | 33 | 6 | 45 |
| `deduplication/applicator_backup.py` | `list_backups` | 7 | 23 | 5 | 30 |
| `deduplication/applicator_backup.py` | `create_backup` | 11 | 20 | 5 | 78 |
| `deduplication/applicator_backup.py` | `rollback` | 7 | 18 | 4 | 44 |
| `refactoring/extractor.py` | `_generate_docstring` | 13 | 31 | 5 | 53 |
| `refactoring/extractor.py` | `_generate_function_body` | 15 | 25 | 4 | 46 |
| `refactoring/extractor.py` | `_scan_imports` | 10 | 18 | 5 | 29 |
| `refactoring/extractor.py` | `_generate_signature` | 18 | 13 | 4 | 56 |
| `refactoring/extractor.py` | `_apply_extraction` | 7 | 11 | 4 | 58 |
| `core/executor.py` | `stream_ast_grep_results` | 16 | 29 | 6 | 101 |
| `core/executor.py` | `filter_files_by_size` | 19 | 18 | 4 | 52 |
| `core/executor.py` | `get_supported_languages` | 8 | 16 | 5 | 44 |
| `condense/service.py` | `condense_pack_impl` | 15 | 29 | 5 | 115 |
| `condense/service.py` | `_count_structural_braces` | 17 | 28 | 5 | 33 |
| `condense/service.py` | `_extract_python_surface` | 11 | 17 | 4 | 28 |
| `deduplication/diff.py` | `diff_preview_to_dict` | 14 | 29 | 5 | 53 |
| `deduplication/diff.py` | `build_nested_diff_tree` | 20 | 25 | 6 | 96 |
| `refactoring/analyzer.py` | `_find_python_base_variables` | 10 | 25 | 4 | 44 |
| `complexity/analyzer.py` | `_find_magic_numbers` | 13 | 25 | 5 | 61 |
| `complexity/analyzer.py` | `_find_docstring_extent` | 11 | 21 | 4 | 28 |
| `complexity/analyzer.py` | `_count_function_parameters` | 18 | 18 | 3 | 49 |

Refresh: `uv run python scripts/run_all_analysis.py`

## ~~Mypy Unused type:ignore Comments (2026-03-08)~~ (Resolved)

All 7 unused `type: ignore[misc]` comments were removed in prior refactoring that inlined `Field()` into `@mcp.tool()` wrappers and eliminated `_create_mcp_field_definitions` indirection.

## Duplicate Detection Precision (2026-03-08)

All 5 groups from latest `find_duplication` run (sim >= 0.82) are false positives or low-value. Common causes: trivial constructors, intentionally parallel APIs, thin semantic wrappers, and strategy pattern boilerplate.

See [docs/duplicate-detector-misses.md](duplicate-detector-misses.md) for full investigation and recommended detector improvements:
- Exclude short `__init__` methods
- Discount methods delegating to shared helpers
- Reduce weight for strategy pattern implementations
- Add minimum line savings threshold
- Consider excluding parallel `to_*` formatters

