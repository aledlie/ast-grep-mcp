# Backlog


## Complexity Refactoring Queue (2026-03-08 refresh)

Thresholds: cyc >10, cog >15, nest >4, len >50.

Previous baselines: **434** (2026-03-04) → **407** (2026-03-06) → **100** (2026-03-08) → **80** (2026-03-08 shared-util).

### Recently Resolved

**Shared utility extractions (2026-03-08):**

- **`FilePatterns.normalize_excludes()`** — new classmethod on `constants.py:FilePatterns`. Consolidates all `_normalize_exclude_patterns` functions across quality, complexity, deduplication, and documentation tools. Dedup migrated from substring-match to glob format (`"**/site-packages/**"` etc.) with module-local `_DEDUP_EXCLUDE_DEFAULTS`.
- **`utils/tool_context.py`** — extracted `tool_context` context manager (timing + error logging + Sentry capture) from `quality/tools.py`. Adopted by `complexity/tools.py` (replaced `_log_tool_error` + 3 manual try/except blocks) and all 6 `condense/tools.py` tool functions. Added `status="failed"` to error log. Unit tests: `tests/unit/test_tool_context.py` (8 tests). `cross_language/tools.py` kept its `_run_tool` callable wrapper (different API shape, no violations).
- **`complexity/tools.py`** — removed `_log_tool_error` (16 lines), `_get_default_complexity_exclude_patterns` (3 lines), `DisplayDefaults` import.
- **`quality/tools.py`** — removed local `_tool_context` (28 lines), `_normalize_exclude_patterns` (5 lines), `contextlib`/`Generator`/`DisplayDefaults` imports. `_create_mcp_field_definitions` and field-dict indirection removed; `Field()` inlined into `@mcp.tool()` wrappers.

Commits `52b1f3f`..`70a4762` addressed 6 hotspot areas:

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

## Mypy Unused type:ignore Comments (2026-03-08)

7 unused `type: ignore[misc]` comments flagged by mypy:
- `complexity/tools.py` lines 632, 666, 677
- `deduplication/tools.py` lines 220, 237, 258, 279

## Duplicate Detection Precision (2026-03-08)

All 5 groups from latest `find_duplication` run (sim >= 0.82) are false positives or low-value. Common causes: trivial constructors, intentionally parallel APIs, thin semantic wrappers, and strategy pattern boilerplate.

See [docs/duplicate-detector-misses.md](duplicate-detector-misses.md) for full investigation and recommended detector improvements:
- Exclude short `__init__` methods
- Discount methods delegating to shared helpers
- Reduce weight for strategy pattern implementations
- Add minimum line savings threshold
- Consider excluding parallel `to_*` formatters

## e74b8de Review Follow-ups (2026-03-08)

- **Sentry gap in `analyze_entity_graph`** — `enhancement_service.py:754` lost its inner `capture_exception` during consolidation. Currently only called from `enhance_entity_graph_tool` (which wraps with `async_tool_context`), so coverage holds. Add a comment documenting the single-caller assumption, or restore a lightweight `capture_exception` if new callers are added.
- **`_handle_tool_error` logger duplication** — `tool_context.py:16` calls `get_logger(f"tool.{tool_name}")` on every error. Caller already has a logger bound to the same name. Low severity if `get_logger` caches; document or accept logger as parameter.

## changelog_generator.py Hardening (2026-03-08)

- **`from_version` resolution asymmetry** — `_get_commit_range` only tries v-prefix for `from_version`, falling back to raw string passthrough. `to_version` uses full `_resolve_version_ref`. Fix: use `_resolve_version_ref` for both. See [KNOWN_ISSUES.md](KNOWN_ISSUES.md).

