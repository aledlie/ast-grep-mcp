# Backlog


## Complexity Refactoring Queue (2026-03-08 refresh)

Thresholds: cyc >10, cog >15, nest >4, len >50.

Previous baselines: **434** (2026-03-04) → **407** (2026-03-06) → **100** (2026-03-08) → **80** (2026-03-08 shared-util) → **25** (2026-03-08 helper-adoption) → **19** (2026-03-08 condense-decompose).

### Recently Resolved

- **`condense/service.py`** (uncommitted) — all 5 offenders resolved. `condense_pack_impl` (was cyc=15, cog=29, nest=5, len=115) decomposed into `_accumulate_pack_results` + `_build_pack_result`. `extract_surface_impl` (was cyc=12, cog=15, len=73) extracted `_accumulate_surface_results`. `_count_structural_braces` (was cyc=17, cog=28, nest=5) simplified via `CondenseParsing.BRACE_DELTA` lookup. `_extract_python_surface` (was cog=17) and `_extract_js_ts_surface` (was cyc=12) also dropped below thresholds.
- **`deduplication/diff.py:diff_preview_to_dict`** — no longer exceeds thresholds (was cyc=14, cog=29, nest=5, len=53).
- **`constants.py`** (uncommitted) — added `CondenseParsing` class (`QUOTE_CHARS`, `BRACE_DELTA`) to replace magic brace/quote chars in condense and renamer.
- **`refactoring/renamer.py`** (uncommitted) — replaced magic `{`/`}` brace handling with `CondenseParsing.BRACE_DELTA` lookup.
- **`core/executor.py:stream_ast_grep_results`** (`0642b3f`) — extracted `_iter_stdout_matches` (yield-from delegation), `_log_stream_completion`, `_raise_not_found_error`. cyc 16→4, cog 29→2, nest 6→2, len 101→52. Note: len=52 still marginally exceeds len>50 threshold.
- **`deduplication/applicator_backup.py`** (`7880737`, `c847003`) — all 4 functions now below thresholds. Extracted helpers to class + shared `utils/backup.py` primitives (`get_file_hash`, `resolve_backup_dir`, `copy_file_to_backup`, `restore_file_from_backup`). `cleanup_old_backups` cog 33→14, `list_backups` cog 23→14, `create_backup` cog 20→10, `rollback` cog 18→15.
- **`rewrite/backup.py`** (`c847003`) — consolidated duplicate backup primitives into shared `utils/backup.py`, eliminating ~60 lines of duplication. `create_backup`, `create_deduplication_backup`, `_restore_single_file`, `_check_file_conflicts` now delegate to shared utils.
- **`core/executor.py:run_command`** (`0a679bb`) — wrapped with `tool_context()`, eliminated ~35 lines of manual timing + Sentry boilerplate. Still exceeds thresholds (cog=17, nest=5, len=56) — listed in remaining offenders table below.
- **`schema/enhancement_service.py`** (`0a679bb`) — replaced hardcoded 16-entry `_EXCLUDED_DIRS` with derivation from `FilePatterns.DEFAULT_EXCLUDE`.
- **`refactoring/extractor.py`** (`0a679bb`) — `_generate_docstring` (was cog=31), `_generate_function_body` (was cog=25), `_generate_signature` (was cog=13), `_apply_extraction` (was cog=11) all dropped below thresholds via further decomposition.

### Remaining Offenders (live scan at `5fdd930` + uncommitted)

19 functions exceed at least one threshold. Sorted by cognitive complexity.

| File | Function | Cyc | Cog | Nest | Len | Exceeds |
|------|----------|-----|-----|------|-----|---------|
| `deduplication/diff.py` | `build_nested_diff_tree` | 20 | 25 | 6 | 96 | cyc,cog,nest,len |
| `refactoring/analyzer.py` | `_find_python_base_variables` | 10 | 25 | 4 | 44 | cog |
| `complexity/analyzer.py` | `_find_magic_numbers` | 13 | 25 | 5 | 61 | cyc,cog,nest,len |
| `complexity/analyzer.py` | `_find_docstring_extent` | 11 | 21 | 4 | 28 | cyc,cog |
| `core/executor.py` | `filter_files_by_size` | 19 | 18 | 4 | 52 | cyc,cog,len |
| `refactoring/extractor.py` | `_scan_imports` | 10 | 18 | 5 | 29 | cog,nest |
| `complexity/analyzer.py` | `_count_function_parameters` | 18 | 18 | 3 | 49 | cyc,cog |
| `core/executor.py` | `run_command` | 9 | 17 | 5 | 56 | cog,nest,len |
| `core/executor.py` | `get_supported_languages` | 8 | 16 | 5 | 44 | cog,nest |
| `complexity/analyzer.py` | `extract_functions_from_file` | 10 | 15 | 5 | 34 | nest |
| `refactoring/analyzer.py` | `_get_variable_classification` | 13 | 13 | 3 | 40 | cyc |
| `refactoring/extractor.py` | `extract_function` | 9 | 12 | 5 | 79 | nest,len |
| `deduplication/diff.py` | `_format_alignment_entry` | 11 | 12 | 3 | 16 | cyc |
| `refactoring/analyzer.py` | `_scan_and_register_identifiers` | 9 | 9 | 5 | 26 | nest |
| `complexity/analyzer.py` | `analyze_file_complexity` | 4 | 9 | 5 | 43 | nest |
| `deduplication/diff.py` | `generate_file_diff` | 11 | 6 | 2 | 27 | cyc |
| `deduplication/diff.py` | `build_diff_tree` | 11 | 5 | 2 | 35 | cyc |
| `core/executor.py` | `stream_ast_grep_results` | 4 | 2 | 2 | 52 | len |
| `refactoring/analyzer.py` | `analyze_selection` | 6 | 0 | 3 | 63 | len |

**By file:** `complexity/analyzer.py` (5), `deduplication/diff.py` (4), `refactoring/analyzer.py` (4), `core/executor.py` (4), `refactoring/extractor.py` (2)

Refresh: `uv run python scripts/scan_complexity_offenders.py`

## scan_complexity_offenders.py Hardening (2026-03-08)

From code review of `8d4d13a`:

### High
- **Silent failure on wrong CWD**: Uses relative paths (`src/ast_grep_mcp/...`). If run from anywhere but the project root, `extract_functions_from_file` returns `[]` and the script prints an empty table with no error. Fix: resolve paths relative to `__file__` or add a startup guard checking `pathlib.Path("src/ast_grep_mcp").is_dir()`.

### Medium
- **`_extract_name` fragile with decorators** (line 40-42): `code.split("(")[0]` can hit a decorator's `(` before `def`. Fix: scan lines for `def`/`async def` first, then split on `(`.
- **Language hardcoded to `"python"`** (line 53): Silent assumption. If a non-Python file is ever added to `FILES`, calls silently return `[]`. Add a comment or per-entry language field.

### Low
- **`FILES` lacks type annotation**: Should be `FILES: list[str] = [...]` per project conventions.
- ~~**`run_command` listed as both resolved and remaining offender**~~: Resolved — clarified that `tool_context` wrapping reduced len/boilerplate but cog/nest remain above thresholds.

## Magic Number/String Migration — Done (`4976bef`, `f79f686`)

- [x] `"ast-grep"` (6 occurrences in executor.py) → `ExecutorDefaults.AST_GREP_COMMAND`
- [x] `timeout=2` (2 occurrences in executor.py) → `StreamDefaults.PROCESS_TERMINATE_TIMEOUT_SECONDS`
- [x] `timeout=5` (3 occurrences in executor.py) → `StreamDefaults.PROCESS_KILL_TIMEOUT_SECONDS`
- [x] Backup magic strings (13 occurrences across applicator_backup.py, rewrite/backup.py) → `BackupDefaults.DIR_NAME`, `.METADATA_FILE`, `.DEDUP_PREFIX`, `.REWRITE_PREFIX` (parallel session `f79f686`)

## Deferred (2026-03-08)

**scan_complexity_offenders.py Hardening** — Skipped in backlog-implementer pass; user scope "non-complexity related items" excludes complexity tooling. (Commits: `6a27e23`, `edbb9f0`, `c412c78`)
- High: Silent failure on wrong CWD (uses relative paths, needs startup guard)
- Medium: `_extract_name` fragile with decorators
- Medium: Language hardcoded to `"python"`
- Low: `FILES` lacks type annotation
- ~~Low: `run_command` documentation issue~~ (resolved — clarified in Recently Resolved section)

**Strategy pattern filter for deduplication** — Low-priority per docs/duplicate-detector-misses.md investigation notes. Only candidate (Group 5) would save ~18 lines with minor signature mismatch; over-engineering for marginal benefit.

