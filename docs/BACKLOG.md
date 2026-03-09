# Backlog


## Complexity Refactoring Queue (2026-03-08 refresh)

Thresholds: cyc >10, cog >15, nest >4, len >50.
Full analysis: [docs/COMPLEXITY-REPORT.md](COMPLEXITY-REPORT.md) (generated 2026-03-09).

> **Maintenance:** When resolving a CX-* item, update both this backlog (mark `[x]`) and the Recommendations section of `docs/COMPLEXITY-REPORT.md` to reflect the new metrics. Re-run the complexity tools to refresh the report when the remaining offender count changes significantly.

Previous baselines: **434** (2026-03-04) → **407** (2026-03-06) → **100** (2026-03-08) → **80** (2026-03-08 shared-util) → **25** (2026-03-08 helper-adoption) → **19** (2026-03-08 condense-decompose) → **18** (2026-03-08 dead-code-removal) → **17** (2026-03-08 docstring-extent-decompose) → **16** (2026-03-08 nested-diff-decompose) → **15** (2026-03-08 filter-files-decompose) → **11** (2026-03-09 analyzer-decompose) → **7** (2026-03-09 complexity-reductions) → **0** (2026-03-09 remaining-offenders).

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

### Remaining Offenders

Thresholds: cyc >10, cog >15, nest >4, len >50. All items from this section have been migrated to [2026-03-09 changelog](../changelog/2026-03-09-complexity-offender-reductions.md). Refresh: `uv run python scripts/scan_complexity_offenders.py`


## executor.py Hardening (2026-03-08)

From final code review of `9ad6a2c`–`9d7ea65`.

- [ ] **EX-01** (Medium) `_execute_subprocess` Sentry span missing `returncode` on error path: when `check=True` and `subprocess.run` raises `CalledProcessError`, `span.set_data("returncode", ...)` is never reached. Fix: wrap in try/except to set `returncode` before re-raising.
- [ ] **EX-02** (Low) `_execute_subprocess` `use_shell` should be keyword-only: add `*` before `use_shell: bool` to prevent positional misuse.
- [ ] **EX-03** (Low) `_load_custom_languages` silently swallows errors: `except Exception: pass` should log at debug level for diagnosability.

## Test Coverage Gaps (2026-03-09)

From backlog-implementer session implementing CX-01–CX-04 and SC-01–SC-04. New helpers introduced during complexity refactoring and script hardening have no direct test coverage.

- [ ] **TC-01** (Medium) `scripts/scan_complexity_offenders.py` has zero tests. No coverage for `_extract_name` (decorator/async handling from SC-02), `_PROJECT_ROOT` resolution (CWD-independence from SC-01), `FILES` language tuple unpacking (SC-03), or `main()` output format. Fix: add `tests/unit/test_scan_complexity_offenders.py` with cases for: decorated functions (`@cache\ndef foo()`), `async def`, running from wrong CWD, `--all` flag, and functions exceeding thresholds.
- [ ] **TC-02** (Medium) `FunctionExtractor._process_scan_line` (`refactoring/extractor.py:344`) — new helper from CX-01. No direct unit test. Handles 5 branches: skip blank/comment, import start, multiline continuation, post-import break, default. `_scan_imports` itself also untested — existing `test_extract_function.py` exercises end-to-end extraction but never imports. Fix: add parametrized test in `test_extract_function.py` covering multiline `from x import (\n  a,\n  b\n)`, stacked imports, `import x` vs `from x import y`, and the post-import stop condition.
- [ ] **TC-03** (Low) `_ensure_trailing_newline` (`deduplication/diff.py:391`) — new helper from CX-04. `test_generate_file_diff` exists but uses simple single-line inputs and weak assertions (`assert "def foo()" in diff or diff == ""`). Does not verify trailing newline edge cases (content already ending with `\n` vs not, empty content). Fix: add tests for `_ensure_trailing_newline` directly: empty list, single line with newline, single line without newline, multi-line.
- [ ] **TC-04** (Low) `_format_diff_alignment` (`deduplication/diff.py:193`) — new helper from CX-03. `test_format_alignment_diff` covers the `diff` alignment type but uses a weak assertion (`assert formatted is not None`). Does not verify the `- old`/`+ new` prefix formatting, empty old/new values, or both empty. Fix: strengthen `test_format_alignment_diff` to assert specific output lines, and add edge cases for empty `old`/`new` fields.

## Deferred (2026-03-08)

- [ ] **DF-01** (Low) Strategy pattern filter for deduplication — per `docs/duplicate-detector-misses.md` investigation. Only candidate (Group 5) would save ~18 lines with minor signature mismatch; over-engineering for marginal benefit.

