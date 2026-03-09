# Backlog


## Complexity Refactoring Queue (2026-03-08 refresh)

Thresholds: cyc >10, cog >15, nest >4, len >50.

Previous baselines: **434** (2026-03-04) → **407** (2026-03-06) → **100** (2026-03-08) → **80** (2026-03-08 shared-util) → **25** (2026-03-08 helper-adoption) → **19** (2026-03-08 condense-decompose) → **18** (2026-03-08 dead-code-removal) → **17** (2026-03-08 docstring-extent-decompose) → **16** (2026-03-08 nested-diff-decompose) → **15** (2026-03-08 filter-files-decompose) → **11** (2026-03-09 analyzer-decompose).

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
- **`complexity/analyzer.py:_find_magic_numbers`** (uncommitted) — deleted dead code (was cyc=13, cog=25, nest=5, len=61). Function was never called; active implementation lives in `quality/smells_detectors.py:MagicNumberDetector._find_magic_numbers` (already well-decomposed). Removed unused `SemanticVolumeDefaults` import.
- **`complexity/analyzer.py:_find_docstring_extent`** (uncommitted) — decomposed into `_measure_docstring` + shared `utils/parsing.py` primitives (`detect_triple_quote`, `skip_blank_lines`). cyc 11→4, cog 21→3. All helpers below thresholds. DRY: `deduplication/generator.py` `_get_triple_quotes` and `_skip_blank_lines` now delegate to same shared utils.
- **`deduplication/diff.py:build_nested_diff_tree`** (`b5e9d52`) — extracted `_DiffCounts` accumulator, `_classify_diff_line`, `_parse_unified_diff_lines`, `_build_nested_structure`. cyc 20→7, cog 25→3, nest 6→2, len 96→31. All helpers below thresholds.
- **`core/executor.py:filter_files_by_size`** (uncommitted) — extracted `_walk_and_classify` for os.walk loop and file classification. cyc 19→10, cog 18→8, nest 4→3, len 52→36. Helper below thresholds.
- **`refactoring/analyzer.py`** (`e3ceabb`–`40516c1`) — all 4 offenders resolved. `_find_python_base_variables` (cog 25→7): extracted `_collect_python_identifiers` helper + `_PYTHON_BASE_VAR_PATTERNS` constant. `_get_variable_classification` (cyc 13→7): merged two MODIFIED-return branches. `_scan_and_register_identifiers` (nest 5→4): collapsed for+if into generator. `analyze_selection` (len 63→37): extracted `_build_code_selection`.

### Remaining Offenders (live scan at `40516c1`)

11 functions exceed at least one threshold. Sorted by cognitive complexity.

| File | Function | Cyc | Cog | Nest | Len | Exceeds |
|------|----------|-----|-----|------|-----|---------|
| `refactoring/extractor.py` | `_scan_imports` | 10 | 18 | 5 | 29 | cog,nest |
| `complexity/analyzer.py` | `_count_function_parameters` | 18 | 18 | 3 | 49 | cyc,cog |
| `complexity/analyzer.py` | `extract_functions_from_file` | 10 | 15 | 5 | 34 | nest |
| `refactoring/extractor.py` | `extract_function` | 9 | 12 | 5 | 79 | nest,len |
| `deduplication/diff.py` | `_format_alignment_entry` | 11 | 12 | 3 | 16 | cyc |
| `complexity/analyzer.py` | `analyze_file_complexity` | 4 | 9 | 5 | 43 | nest |
| `deduplication/diff.py` | `generate_file_diff` | 11 | 6 | 2 | 27 | cyc |
| ~~`deduplication/diff.py`~~ | ~~`build_diff_tree`~~ | ~~11~~ | ~~5~~ | ~~2~~ | ~~35~~ | ~~cyc~~ — Done `53e025a` |

**By file:** `complexity/analyzer.py` (3), `deduplication/diff.py` (3), `refactoring/extractor.py` (2) — `core/executor.py` (1 remaining: `filter_files_by_size`)

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

## executor.py Hardening (2026-03-08)

From final code review of `9ad6a2c`–`9d7ea65`:

### Medium
- **`_execute_subprocess` Sentry span missing `returncode` on error path**: When `check=True` and `subprocess.run` raises `CalledProcessError`, `span.set_data("returncode", ...)` is never reached. Pre-existing gap, now more visible after extraction. Fix: wrap `subprocess.run` in a try/except inside `_execute_subprocess` to set `returncode` before re-raising.

### Low
- **`_execute_subprocess` `use_shell` should be keyword-only**: Add `*` before `use_shell: bool` to prevent future positional misuse.
- **`_load_custom_languages` silently swallows errors**: `except Exception: pass` should log at debug level for diagnosability.

## Deferred (2026-03-08)

**scan_complexity_offenders.py Hardening** — Skipped in backlog-implementer pass; user scope "non-complexity related items" excludes complexity tooling. (Commits: `6a27e23`, `edbb9f0`, `c412c78`)
- High: Silent failure on wrong CWD (uses relative paths, needs startup guard)
- Medium: `_extract_name` fragile with decorators
- Medium: Language hardcoded to `"python"`
- Low: `FILES` lacks type annotation
- ~~Low: `run_command` documentation issue~~ (resolved — clarified in Recently Resolved section)

**Strategy pattern filter for deduplication** — Low-priority per docs/duplicate-detector-misses.md investigation notes. Only candidate (Group 5) would save ~18 lines with minor signature mismatch; over-engineering for marginal benefit.

