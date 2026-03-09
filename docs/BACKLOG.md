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

### Remaining Offenders (live scan at `cbe5588` — 2026-03-09)

Thresholds: cyc >10, cog >15, nest >4, len >50. Refresh: `uv run python scripts/scan_complexity_offenders.py`

- [x] **CX-01** `refactoring/extractor.py:_scan_imports` — cyc=10, cog=18, nest=5 (exceeds: cog, nest). Extracted `_process_scan_line` helper; `_scan_imports` flattened to loop + break. (`040bb64`, `8ae886b`)
- [x] **CX-02** `refactoring/extractor.py:extract_function` — cyc=9, cog=12, nest=5, len=79 (exceeds: nest, len). Extracted `_perform_extraction_steps`; body reduced from 79→49 lines. (`040bb64`)
- [x] **CX-03** `deduplication/diff.py:_format_alignment_entry` — cyc=11, cog=12 (exceeds: cyc). Extracted `_format_diff_alignment` for old/new pair handling. (`040bb64`)
- [x] **CX-04** `deduplication/diff.py:generate_file_diff` — cyc=11, cog=6 (exceeds: cyc). Extracted `_ensure_trailing_newline`; main function simplified. (`040bb64`)

## scan_complexity_offenders.py Hardening (2026-03-08)

From code review of `8d4d13a`. Deferred from backlog-implementer pass (commits: `6a27e23`, `edbb9f0`, `c412c78`).

- [x] **SC-01** (High) Silent failure on wrong CWD: resolved paths via `_PROJECT_ROOT = Path(__file__).parent.parent`. (`9d88886`)
- [x] **SC-02** (Medium) `_extract_name` fragile with decorators: scan lines for `def`/`async def` first. (`9d88886`)
- [x] **SC-03** (Medium) Language hardcoded to `"python"`: changed `FILES` to `list[tuple[str, str]]` with per-entry language. (`9d88886`)
- [x] **SC-04** (Low) `FILES` lacks type annotation: added `FILES: list[tuple[str, str]]`. (`9d88886`)

## executor.py Hardening (2026-03-08)

From final code review of `9ad6a2c`–`9d7ea65`.

- [ ] **EX-01** (Medium) `_execute_subprocess` Sentry span missing `returncode` on error path: when `check=True` and `subprocess.run` raises `CalledProcessError`, `span.set_data("returncode", ...)` is never reached. Fix: wrap in try/except to set `returncode` before re-raising.
- [ ] **EX-02** (Low) `_execute_subprocess` `use_shell` should be keyword-only: add `*` before `use_shell: bool` to prevent positional misuse.
- [ ] **EX-03** (Low) `_load_custom_languages` silently swallows errors: `except Exception: pass` should log at debug level for diagnosability.

## Deferred (2026-03-08)

- [ ] **DF-01** (Low) Strategy pattern filter for deduplication — per `docs/duplicate-detector-misses.md` investigation. Only candidate (Group 5) would save ~18 lines with minor signature mismatch; over-engineering for marginal benefit.

