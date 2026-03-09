# Backlog


## Complexity Refactoring Queue (2026-03-08 refresh)

Thresholds: cyc >10, cog >15, nest >4, len >50.

Previous baselines: **434** (2026-03-04) → **407** (2026-03-06) → **100** (2026-03-08) → **80** (2026-03-08 shared-util) → **25** (2026-03-08 helper-adoption).

### Recently Resolved (`0a679bb`)

- **`deduplication/applicator_backup.py`** — all 4 functions now below thresholds. Extracted `_load_backup_metadata`, `_generate_backup_id`, `_compute_file_hashes`, `_backup_single_file`, `_restore_single_file`, `_try_cleanup_backup`. `cleanup_old_backups` cog 33→below, `list_backups` cog 23→14.
- **`core/executor.py:run_command`** — wrapped with `tool_context()`, eliminated ~35 lines of manual timing + Sentry boilerplate.
- **`schema/enhancement_service.py`** — replaced hardcoded 16-entry `_EXCLUDED_DIRS` with derivation from `FilePatterns.DEFAULT_EXCLUDE`.
- **`refactoring/extractor.py`** — `_generate_docstring` (was cog=31), `_generate_function_body` (was cog=25), `_generate_signature` (was cog=13), `_apply_extraction` (was cog=11) all dropped below thresholds via further decomposition.

### Remaining Top Offenders (live scan)

| File | Function | Cyc | Cog | Nest | Len |
|------|----------|-----|-----|------|-----|
| `core/executor.py` | `stream_ast_grep_results` | 16 | 29 | 6 | 101 |
| `condense/service.py` | `condense_pack_impl` | 15 | 29 | 5 | 115 |
| `condense/service.py` | `_count_structural_braces` | 17 | 28 | 5 | 33 |
| `deduplication/diff.py` | `diff_preview_to_dict` | 14 | 29 | 5 | 53 |
| `deduplication/diff.py` | `build_nested_diff_tree` | 20 | 25 | 6 | 96 |
| `refactoring/analyzer.py` | `_find_python_base_variables` | 10 | 25 | 4 | 44 |
| `complexity/analyzer.py` | `_find_magic_numbers` | 13 | 25 | 5 | 61 |
| `complexity/analyzer.py` | `_find_docstring_extent` | 11 | 21 | 4 | 28 |
| `complexity/analyzer.py` | `_count_function_parameters` | 18 | 18 | 3 | 49 |
| `core/executor.py` | `filter_files_by_size` | 19 | 18 | 4 | 52 |
| `core/executor.py` | `run_command` | 9 | 17 | 5 | 56 |
| `refactoring/extractor.py` | `_scan_imports` | 10 | 18 | 5 | 29 |
| `condense/service.py` | `_extract_python_surface` | 11 | 17 | 4 | 28 |
| `core/executor.py` | `get_supported_languages` | 8 | 16 | 5 | 44 |
| `condense/service.py` | `extract_surface_impl` | 12 | 15 | 3 | 73 |
| `condense/service.py` | `_extract_js_ts_surface` | 12 | 15 | 4 | 31 |

Refresh: `uv run python scripts/scan_complexity_offenders.py`

## Duplicate Detection Precision (2026-03-08)

All 5 groups from latest `find_duplication` run (sim >= 0.82) are false positives or low-value. Common causes: trivial constructors, intentionally parallel APIs, thin semantic wrappers, and strategy pattern boilerplate.

See [docs/duplicate-detector-misses.md](duplicate-detector-misses.md) for full investigation and recommended detector improvements:
- Exclude short `__init__` methods
- Discount methods delegating to shared helpers
- Reduce weight for strategy pattern implementations
- Add minimum line savings threshold
- Consider excluding parallel `to_*` formatters

