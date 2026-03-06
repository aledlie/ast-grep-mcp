# Backlog

## Complexity Refactoring Queue (2026-03-04)

Threshold baseline from `analyze_complexity` defaults: cyclomatic `>10`, cognitive `>15`, nesting `>4`, length `>50`.
Source for all items below: full quality run on **2026-03-04** (`analyze_codebase.py` / `analyze_complexity_tool`) with **434** functions exceeding thresholds.

#### C1: Split file-migration orchestration in `migrate_file` — **Done** (commit 70f78ef)
**Priority**: P1 | **Hotspot**: `scripts/migrate_print_to_logger.py:238-321` | **Metrics**: cyclomatic 26, cognitive 76, nesting 9, length 84
Current scope mixes six responsibilities: read file content, backup creation, import detection, reverse-order replacement of statements, import insertion (including shebang/docstring scanning), and conditional write. Refactor into focused helpers such as `_load_file_lines`, `_create_backup_if_needed`, `_replace_print_statements`, `_ensure_import_present`, and `_persist_changes_if_needed`.
Acceptance criteria: main orchestrator is linear and branch-light; helper units have targeted tests for docstring/shebang import insertion, reverse replacement line stability, dry-run behavior, and backup behavior.
Validation: keep migration output and modified file text identical for representative fixtures before/after refactor.

#### C2: Replace brittle orphan-import repair flow in `fix_file` — **Done** (commit 63d5873)
**Priority**: P1 | **Hotspot**: `scripts/fix_migration_errors.py:10-73` | **Metrics**: cyclomatic 29, cognitive 56, nesting 6, length 64
Current implementation combines detection, lookahead scanning, and in-loop index/skip state management (`skip_next`, manual `j` traversal), which is high risk for off-by-one and skipped-line bugs. Split into explicit phases: detect candidate orphan ranges, validate each range, then rebuild output by range exclusion.
Acceptance criteria: no in-loop index mutation for primary traversal; deterministic range-removal logic; tests for EOF orphan ranges, nested/adjacent orphan regions, and false-positive guardrails.
Validation: run script on current fixture set and assert same files are fixed with no syntax regressions.

#### C3: Decompose end-to-end analytics script `analyze_project` — **Done** (commit fb4bf17)
**Priority**: P1 | **Hotspot**: `scripts/analyze_analyticsbot.py:21-140` | **Metrics**: cyclomatic 19, cognitive 49, nesting 5, length 120
This function orchestrates complexity, smell, and security scans, each with custom aggregation and logging. Extract scan-specific steps into `_run_complexity_scan`, `_run_smell_scan`, `_run_security_scan`, plus `_format_*_summary` helpers, and keep `analyze_project` as a coordinator.
Acceptance criteria: each scan helper returns typed/structured results; coordinator only sequences steps and merges outputs; output payload keys and console summary remain backward-compatible.
Validation: snapshot test current JSON output shape and major log blocks.

#### C4: Split reporting + summary extraction in `generate_summary_report` — **Done** (commit 2794f06)
**Priority**: P2 | **Hotspot**: `analyze_codebase.py:317-366` | **Metrics**: cyclomatic 14, cognitive 43, nesting 7, length 50
Function bundles enforcement run, markdown report generation, summary section extraction, error handling, and optional fix application. Extract `_run_enforcement`, `_generate_markdown_report`, `_print_report_summary`, and keep fix application as a dedicated post-step.
Acceptance criteria: simplified happy-path flow; summary extraction logic isolated and testable; no behavior change to generated report path and output messages.
Validation: compare emitted summary block text against current output for same repo input.

#### C5: Break up enhanced dedup response builder — **Done** (commit 16a5ac1)
**Priority**: P2 | **Hotspot**: `src/ast_grep_mcp/features/deduplication/reporting.py:212-358` (`create_enhanced_duplication_response`) | **Metrics**: cyclomatic 23, cognitive 40, nesting 6, length 147
Current method performs candidate enrichment, complexity bucketing, optional diff generation, priority scoring, summary aggregation, and recommendation synthesis in one pass. Extract dedicated steps: `_build_enhanced_candidate`, `_generate_candidate_diff_preview`, `_update_distribution`, `_build_global_recommendations`, `_build_summary`.
Acceptance criteria: no regression in candidate ordering or computed fields (`priority`, `total_lines_saveable`, distribution); easier unit-level coverage for each sub-step.
Validation: golden-output tests over representative candidate sets with and without diffs/colors.

#### C6: Simplify hybrid config validation in `__post_init__` — **Done** (commit 5e6b3de)
**Priority**: P2 | **Hotspot**: `src/ast_grep_mcp/features/deduplication/similarity.py:165-199` (`HybridSimilarityConfig.__post_init__`) | **Metrics**: cyclomatic 19, cognitive 37, nesting 5, length 35
This validator mixes semantic rebalancing, bounds checks, and weight-sum branch logic. Extract `_apply_semantic_rebalance_if_needed`, `_validate_weight_bounds`, and `_validate_weight_sum` to reduce branch stacking and improve error-message maintainability.
Acceptance criteria: identical validation semantics and exception messages for current inputs; isolated tests for legacy-default rebalance behavior and invalid weight combinations.
Validation: run existing semantic-similarity unit suite unchanged.

#### C7: Refactor Flask route parser loop in `parse_file` — **Done** (commit 6874996)
**Priority**: P2 | **Hotspot**: `src/ast_grep_mcp/features/documentation/api_docs_generator.py:306-361` (`FlaskRouteParser.parse_file`) | **Metrics**: cyclomatic 15, cognitive 37, nesting 6, length 56
Main loop combines decorator matching, method parsing, function lookup, parameter extraction, and route creation. Extract `_parse_decorator_match`, `_find_next_handler_name`, and `_build_routes_for_methods` to separate tokenization from object construction.
Acceptance criteria: parser continues to support `@app.route`/`@blueprint.route`, default GET fallback, and method list parsing; no duplicate or missing routes.
Validation: add fixture tests for multi-method decorators, no-method decorators, and intervening non-def lines.

#### C8: Decompose external call-site discovery — **Done** (commit 426b938)
**Priority**: P2 | **Hotspot**: `src/ast_grep_mcp/features/deduplication/impact.py:264-323` (`_find_external_call_sites`) | **Metrics**: cyclomatic 14, cognitive 36, nesting 7, length 60
Function currently does function-name capping, pattern building, ast-grep execution, JSON decode, path normalization, exclude filtering, call-site shaping, and exception handling in one nested flow. Extract `_search_call_sites_for_name`, `_normalize_match_file_path`, and `_to_call_site_record`.
Acceptance criteria: stable call-site payload schema and exclude-file filtering; bounded search behavior unchanged; clearer error-path logging.
Validation: deterministic unit tests with mocked `run_ast_grep` responses and malformed JSON cases.

#### C9: Replace heuristic-heavy orphan detection monolith — **Done** (commit e7a51e3)
**Priority**: P2 | **Hotspot**: `scripts/fix_import_orphans.py:12-67` (`find_orphaned_imports`) | **Metrics**: cyclomatic 23, cognitive 35, nesting 6, length 56
Current detection interleaves multiple heuristics, line-peeking, and range-finalization branches. Split into composable predicates (`_is_orphan_close_paren`, `_is_orphan_import_item_start`) and a single range scanner to reduce branching and improve readability of heuristics.
Acceptance criteria: identical detected ranges on existing migration-corruption fixtures; clearer predicate-focused tests for each heuristic branch.
Validation: run script across known affected files and compare removed line ranges pre/post refactor.

#### C10: Modularize normalization pipeline in `_normalize_for_ast` — **Done** (commit 029b7b2)
**Priority**: P2 | **Hotspot**: `src/ast_grep_mcp/features/deduplication/similarity.py:1070-1126` | **Metrics**: cyclomatic 16, cognitive 35, nesting 5, length 57
Normalization currently performs trimming, blank/comment filtering, inline comment stripping, and indentation normalization inline in one loop. Extract per-line transforms (`_strip_inline_python_comment`, `_strip_inline_js_comment`, `_normalize_indentation`) and compose them in a small pipeline.
Acceptance criteria: normalized output remains identical for current fixtures and semantic-similarity tests; line-filtering behavior unchanged for quoted/comment edge cases.
Validation: add table-driven tests for strings containing `#`/`//`, mixed indentation, and blank/comment-only lines.

## Low Priority (P3)

#### L1: `cost-estimation.ts` complexity exceeds thresholds
**Priority**: P3 | **Source**: analyze_codebase.py run (2026-02-28)
`cost-estimation.ts` has cyclomatic 44 / cognitive 59 / 258 lines — significantly above thresholds (20/30/150). Consider extracting sub-functions. -- `observability-toolkit/src/lib/cost/cost-estimation.ts`

#### L2: `health-check.ts` complexity exceeds thresholds
**Priority**: P3 | **Source**: analyze_codebase.py run (2026-02-28)
`health-check.ts` has cyclomatic 31 / cognitive 44 / 174 lines. Consider decomposing the main function. -- `observability-toolkit/src/tools/health-check.ts`

## Medium Priority (P2)

#### M1: Handle JS/TS brace counter edge cases — **Done** (commit 10f757c)
**Priority**: P2 | **Source**: condense feature session (9e65f55)
Improve brace counter for JavaScript/TypeScript to handle template literals and regex patterns correctly. Currently counts braces inside template strings and regex patterns as structural braces. -- `src/ast_grep_mcp/features/condense/strip.py` (implementation limitation documented in code review)

#### M2: Add tool-layer integration tests for condense tools — **Done** (pre-existing, 28 tests passing)
**Priority**: P2 | **Source**: condense feature session (9e65f55)
Create integration tests for condense MCP tools that test the full tool interface (tool wrapper + impl + mocking patterns). Current tests only cover impl layer. -- `tests/unit/features/condense/` (test gaps identified)

#### CR1: Commit 565aaea (ast-grep-mcp) — Parser Fixes — **Done** (commit 6473709)

  ┌──────────┬───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │ Severity │                                                                        Finding                                                                        │
  ├──────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ High     │ _split_params: > in => arrow-function defaults corrupts depth counter (goes negative). Fix: guard if depth > 0 before decrementing                    │
  ├──────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ High     │ rstrip("?") strips ALL trailing ? chars — could produce empty string on malformed input. Fix: use p.name[:-1] if p.name.endswith("?") else p.name     │
  ├──────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Medium   │ JSDoc nested brace regex only handles 2 levels — 3+ levels ({{ error: { message: string } }}) still fail. Pre-existing limitation partially addressed │
  ├──────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Medium   │ No tests added for new code paths (_split_params, updated regex, rstrip change)                                                                       │
  ├──────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Low      │ _split_params whitespace-only input returns ['   '] — safe due to caller guard but inconsistent contract                                              │
  └──────────┴───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

## Code Review Findings (2026-03-06)

Bugs and design issues identified in code review of most heavily-edited modules (constants.py, logging.py, executor.py, standards.py, exceptions.py, config.py). Some fixed in same session (noted below), others deferred for future work.

#### BR1: Fix indentation normalization for 4-space code — **Done** (commits 590b4d1, 029b7b2)
**Priority**: P1 | **Source**: 2026-03-06 code review | **Status**: Fixed
`NORMALIZATION_DIVISOR = 2` in `IndentationDefaults` causes 4-space-indented code to normalize incorrectly in `_normalize_for_ast`, doubling instead of canonicalizing. Two identical functions in 4-space and 2-space styles won't compare as similar. The codebase already has the correct adaptive approach at line 1547-1549 in the same file — either use that or set `NORMALIZATION_DIVISOR = 4`. -- `src/ast_grep_mcp/constants.py:537` + `src/ast_grep_mcp/features/deduplication/similarity.py:1121`

#### BR2: Fix contract mismatch in `filter_files_by_size` — **Done** (commit 18a15dd)
**Priority**: P1 | **Source**: 2026-03-06 code review | **Status**: Fixed
Function docstring says `None = unlimited` and returns `([], [])` when `max_size_mb is None`. Callers have guards (`if max_size_mb <= 0: return [project_folder]`) so they don't hit the silent empty return, but any future caller will silently get zero files. Fix by either walking and returning all files when unlimited, or update docstring. -- `src/ast_grep_mcp/core/executor.py:260-262`

#### BR3: Fix `meta_vars` type annotation mismatch — **Done** (commit 77e4b2d)
**Priority**: P1 | **Source**: 2026-03-06 code review | **Status**: Fixed
`RuleViolation.meta_vars` declared as `Optional[Dict[str, str]]` but `enforcer.py:279` stores `List[str]` values for multi-capture `$$$` patterns, causing `TypeError` in `fixer.py` on `str.replace()`. Fix by widening type to `Dict[str, str | list[str]]` and guarding replacements in fixer. -- `src/ast_grep_mcp/models/standards.py:152` + `src/ast_grep_mcp/features/quality/enforcer.py:279` + `src/ast_grep_mcp/features/quality/fixer.py:262`

#### BR4: Fix column 0-indexing inconsistency in RuleViolation — **Done** (commit 81cf372)
**Priority**: P1 | **Source**: 2026-03-06 code review | **Status**: Fixed
Docstring says columns are 1-indexed but `enforcer.py:282-294` applies `+1` to lines but NOT columns, leaving columns at 0-indexed value from ast-grep. `security_scanner.py:479-481` does it correctly. Fix by adding `+1` to column assignments in enforcer. -- `src/ast_grep_mcp/features/quality/enforcer.py:282-294` + `src/ast_grep_mcp/models/standards.py:130-131`

#### BR5: Fix file handle leak in `configure_logging` — **Done** (commit 682a5f5)
**Priority**: P1 | **Source**: 2026-03-06 code review | **Status**: Fixed
Each call to `configure_logging` opens a new file descriptor inline with no close, leaking in long-running processes and test suites. Fix by opening file outside and holding module-level reference, or use context manager. -- `src/ast_grep_mcp/core/logging.py:41`

#### BR6: Fix `CACHE_TTL` semantic mismatch with `CLEANUP_INTERVAL_SECONDS` — **Done** (commit 955772c)
**Priority**: P2 | **Source**: 2026-03-06 code review | **Status**: Fixed
`CACHE_TTL` initialized from `CLEANUP_INTERVAL_SECONDS` (300s background sweep) but these are semantically different — one is entry expiry, other is sweep frequency. When they diverge, callers using `CACHE_TTL` get wrong expiry. Fix by introducing dedicated `DEFAULT_CACHE_TTL` constant. -- `src/ast_grep_mcp/core/config.py:21` + line 128

#### BR7: Fix double `os.environ.get` call in config path resolution — **Done** (commit abc9e0d)
**Priority**: P2 | **Source**: 2026-03-06 code review | **Status**: Fixed
`_resolve_and_validate_config_path` reads `AST_GREP_CONFIG` env var twice on the same condition, with dead code in between. Use walrus operator or read once. -- `src/ast_grep_mcp/core/config.py:157-160`

#### BR8: Add timeout to `kill()` + `wait()` in process cleanup (FIXED)
**Priority**: P1 | **Source**: 2026-03-06 code review | **Status**: Fixed in 99dec84
Bare `process.wait()` after `kill()` has no timeout, can block indefinitely on unkillable processes (D-state Linux, network filesystems). Both `_terminate_process` and `_cleanup_process` fixed to add 5s timeout. -- `src/ast_grep_mcp/core/executor.py:402-404` (fixed) + `:468-471` (fixed)
