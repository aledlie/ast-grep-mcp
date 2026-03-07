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

## Standards Enforcement Fixes (2026-03-06)

#### SE1: Replace `assert isinstance()` with explicit type checks — **Done**
**Priority**: P2 | **Source**: `enforce_standards` run (2026-03-06) | **Rule**: `no-assert-production`
4 `assert isinstance()` calls in production code — asserts are stripped under `-O` flag. `benchmark.py:82`: removed redundant assert (value provably float from `round(statistics.mean(...))`). `applicator.py:673,680,689`: replaced with `if not isinstance: raise TypeError`. -- `src/ast_grep_mcp/features/deduplication/benchmark.py` + `src/ast_grep_mcp/features/deduplication/applicator.py`

## Duplication Findings (2026-03-06)

6 groups found (96 duplicated lines, 48 saveable). Source: `find_duplication_tool` on `src/`.

#### D1: Consolidate `_is_python_import` / `_is_javascript_import` in renamer
**Priority**: P2 | **Verdict**: FIX | **Savings**: ~10 lines
`renamer.py:208-217` vs `renamer.py:266-275` — 100% identical implementation (`return "import" in context`). Merge into a single `_is_import(context)` method and update call sites at lines 204, 258. Private methods only, no external API impact.

#### D2: Parameterize severity-suggestion helpers in search service
**Priority**: P2 | **Verdict**: FIX | **Savings**: ~15 lines
`service.py:1229-1233` (`_add_error_suggestions`), `:1271-1275` (`_add_warning_suggestions`), `:1278-1282` (`_add_info_suggestions`) — identical loop filtering by severity enum. Replace with `_add_suggestions_by_severity(severity: IssueSeverity, prefix: str, issues, suggestions)`.

#### D3: Console logger error/warning methods
**Priority**: P3 | **Verdict**: LOW | **Savings**: ~8 lines
`console_logger.py:120-140` — `error()` vs `warning()` differ only in prefix string. Could extract `_log_to_stderr(prefix, message)`. Low value — only 2 callsites.

#### D4: Smell detector `__init__` duplication
**Priority**: P3 | **Verdict**: LOW | **Savings**: ~20 lines across 4+ detectors
`smells_detectors.py:74-81,122-129,208-215,257-266` — identical `threshold + logger` init in 4+ detector classes. Could add `__init__` to `SmellDetector` ABC. Revisit if detector count grows beyond 6.

#### D5-D6: SKIP — Intentional language-specific duplication
- `refactoring.py:75-91` — `to_python_signature` vs `to_typescript_signature`: different output syntax
- `extractor.py:27-33` vs `renamer.py:29-35` — independent class `__init__` methods

## Complexity Refactoring Queue (2026-03-06 refresh)

407 functions exceeding thresholds across 77 files (1,345 total). Thresholds: cyc >10, cog >15, nest >4, len >50.
Full data: `uv run python scripts/run_all_analysis.py` or `uv run python -c "from ast_grep_mcp.features.complexity.tools import analyze_complexity_tool; ..."`

### Top 15 Files by Total Cognitive Load

#### CQ1: `features/deduplication/analyzer.py` — 17 funcs, total_cog=331
| Function | Cyc | Cog | Nest | Len | Fix |
|----------|-----|-----|------|-----|-----|
| `_extract_literals_with_ast_grep` | 15 | 35 | 6 | 67 | Extract `ext_map` to constant; extract temp-file write/cleanup into context manager; extract JSON parsing |
| `analyze_duplicate_group_literals` | 12 | 33 | 5 | 49 | Split variation-collection loop from formatting/suggestion loop |
| `_determine_severity` | 12 | 29 | 4 | 31 | Replace if/elif with `VariationCategory -> severity` lookup dict |
| `_suggest_parameter_name` | 13 | 27 | 4 | 24 | Replace if/elif with lookup dict |
| `_analyze_conditional_difference` | 12 | 27 | 4 | 56 | Extract cond1/cond2 comparison into `_compare_conditional_pair` |
| `classify_variations` | 16 | 26 | 5 | 62 | Extract difficulty scoring into `_difficulty_from_avg_complexity` |
| `_extract_conditionals` | 10 | 25 | 7 | 71 | Share `_run_ast_grep_on_code` helper with `_extract_literals_with_ast_grep` |
| `detect_conditional_variations` | 20 | 16 | 6 | 78 | Extract 3-way comparison into helper; move summary to caller |
| `_extract_identifiers_from_code` | 13 | 15 | 4 | 146 | Split into per-language `_extract_python_identifiers` / `_extract_js_identifiers` |

#### CQ2: `features/documentation/docstring_generator.py` — 13 funcs, total_cog=247
| Function | Cyc | Cog | Nest | Len | Fix |
|----------|-----|-----|------|-----|-----|
| `_find_js_ts_docstring` | 11 | 35 | 5 | 43 | Extract multiline JSDoc scanning into `_scan_multiline_jsdoc` |
| `_find_python_docstring` | 12 | 28 | 5 | 37 | Extract backward docstring scan into helper |
| `_parse_python_params` | 15 | 27 | 4 | 40 | Early returns; extract default-value detection |
| `_parse_js_ts_functions` | 11 | 26 | 6 | 52 | Split regex matching from FunctionInfo construction |
| `_split_params` | 11 | 19 | 5 | 19 | Extract bracket-depth tracking into `_split_at_top_level_commas` |
| `_infer_description_from_name` | 15 | 13 | 4 | 117 | Replace if/elif with `(keyword_set, template)` lookup table |

#### CQ3: `features/deduplication/generator.py` — 12 funcs, total_cog=231
| Function | Cyc | Cog | Nest | Len | Fix |
|----------|-----|-----|------|-----|-----|
| `_skip_python_module_docstring` | 17 | 32 | 6 | 51 | State-machine enum instead of boolean flags |
| `_detect_js_import_point` | 16 | 30 | 5 | 34 | Extract shared `_detect_import_point(lines, patterns)` |
| `_detect_java_import_point` | 13 | 27 | 5 | 28 | Same — share with JS variant above |
| `render_python_function` | 9 | 21 | 4 | 55 | Extract docstring gen, param formatting, body assembly into helpers |
| `generate_parameter_name` / `_infer_parameter_type` | 14/12 | 15/15 | 3/4 | 50/28 | Replace if/elif chains with lookup dicts |

#### CQ4: `features/quality/orphan_detector.py` — 13 funcs, total_cog=223
| Function | Cyc | Cog | Nest | Len | Fix |
|----------|-----|-----|------|-----|-----|
| `_analyze_python_functions` | 11 | 27 | 6 | 40 | Extract ast-grep call + match parsing into `_find_python_function_defs` |
| `_build_dependency_graph` | 10 | 27 | 5 | 30 | Early continues; extract import-node dispatch to handler dict |
| `_is_function_called` | 10 | 22 | 5 | 32 | Extract call-site search from function discovery |
| `_should_exclude` | 7 | 20 | 5 | 13 | Pre-compiled patterns with flat `any()` |
| `_identify_entry_points` | 6 | 21 | 5 | 19 | Set comprehensions + early returns |

#### CQ5: `features/deduplication/similarity.py` — 16 funcs, total_cog=219
| Function | Cyc | Cog | Nest | Len | Fix |
|----------|-----|-----|------|-----|-----|
| `_extract_call_signature` | 19 | 28 | 5 | 107 | Module-level `_EXCLUDED` constant; extract `_find_defined_names` and `_filter_call_names` |
| `_extract_structural_patterns` | 9 | 22 | 6 | 63 | Per-pattern-type extraction helpers (loops, conditionals, assignments) |
| `_logarithmic_bucket` | 10 | 21 | 3 | 38 | Data-driven threshold list with `bisect` |
| `calculate_hybrid_similarity` | 16 | 13 | 3 | 78 | Extract weight application and bonus/penalty into helpers |

#### CQ6: `features/search/service.py` — 18 funcs, total_cog=213
| Function | Cyc | Cog | Nest | Len | Fix |
|----------|-----|-----|------|-----|-----|
| `_check_relational_rule_for_stopby` | 14 | 29 | 6 | 39 | Extract `_check_single_relational_rule` and `_check_composite_rules` |
| `test_match_code_rule_impl` | 13 | 23 | 4 | 80 | Split into prepare/execute/format helpers |
| `develop_pattern_impl` | 14 | 15 | 4 | 111 | Extract phase steps into individual helpers |
| `debug_pattern_impl` | 12 | 11 | 5 | 126 | Extract diagnostic sections into focused checkers |

#### CQ7: `features/schema/enhancement_service.py` — 11 funcs, total_cog=173
| Function | Cyc | Cog | Nest | Len | Fix |
|----------|-----|-----|------|-----|-----|
| `analyze_entity_graph` | 17 | 20 | 5 | 97 | Extract `_compute_graph_metrics`, `_detect_issues`, `_generate_suggestions` |
| `_load_entities_from_directory` | 12 | 21 | 4 | 65 | Split file discovery from entity parsing |
| `_parse_suggestion_rule` | 14 | 26 | 5 | 26 | Early returns + rule-type dispatch dict |

#### CQ8: `features/documentation/api_docs_generator.py` — 12 funcs, total_cog=172
| Function | Cyc | Cog | Nest | Len | Fix |
|----------|-----|-----|------|-----|-----|
| `_generate_markdown_docs` | 14 | 29 | 5 | 70 | Extract per-endpoint formatting into `_format_endpoint_markdown` |
| `parse_file` | 12 | 27 | 6 | 54 | Extract decorator matching from handler parsing |
| `_extract_params` | 11 | 26 | 7 | 40 | Extract type-annotation parsing; use early returns |

#### CQ9: `utils/formatters.py` — 12 funcs, total_cog=162
| Function | Cyc | Cog | Nest | Len | Fix |
|----------|-----|-----|------|-----|-----|
| `_format_diff_with_line_numbers` | 19 | 21 | 5 | 55 | Extract `_parse_hunk_range` and `_format_numbered_line` |
| `format_javascript_code` / `format_typescript_code` / `format_java_code` | 7-9 | 19 | 5-6 | 43-58 | Extract shared `_format_c_family_code(code, lang_config)` |

#### CQ10: `features/documentation/readme_generator.py` — 10 funcs, total_cog=156
| Function | Cyc | Cog | Nest | Len | Fix |
|----------|-----|-----|------|-----|-----|
| `_generate_installation_section` | 19 | 16 | 3 | 70 | Per-language install templates in data structure |
| `_generate_usage_section` | 18 | 13 | 3 | 74 | Per-language usage templates in data structure |
| `_get_project_description` | 10 | 27 | 4 | 33 | Early returns to flatten nesting |

#### CQ11: `features/deduplication/detector.py` — 10 funcs, total_cog=133
| Function | Cyc | Cog | Nest | Len | Fix |
|----------|-----|-----|------|-----|-----|
| `find_duplication` | 14 | 22 | 5 | 98 | Split into discover/similarity/group phases |
| `_get_construct_pattern` | 16 | 12 | 4 | 40 | Nested dict lookup `PATTERNS[lang][construct]` |

#### CQ12: `core/usage_tracking.py` — 8 funcs, total_cog=129
| Function | Cyc | Cog | Nest | Len | Fix |
|----------|-----|-----|------|-----|-----|
| `get_alerts` | 18 | 24 | 6 | 136 | Extract `_check_threshold(metric, value, warn, crit) -> Optional[Alert]` |
| `get_stats` | 15 | 23 | 4 | 95 | Extract per-stat queries into helpers |
| `track_usage` decorator | 9 | 20 | 6 | 78 | Extract timing/logging into `_record_tool_invocation` |

#### CQ13: `features/documentation/sync_checker.py` — 7 funcs, total_cog=125
| Function | Cyc | Cog | Nest | Len | Fix |
|----------|-----|-----|------|-----|-----|
| `_check_markdown_links` | 12 | 27 | 6 | 55 | Extract `_resolve_markdown_link` and `_validate_link_target` |
| `_check_docstring_sync` | 19 | 14 | 4 | 96 | Split into `_compare_params`, `_compare_returns`, `_compare_raises` |

#### CQ14: `features/quality/smells_detectors.py` — 7 funcs, total_cog=122
| Function | Cyc | Cog | Nest | Len | Fix |
|----------|-----|-----|------|-----|-----|
| `detect` (LargeClassDetector) | 10 | 29 | 7 | 54 | Extract `_evaluate_class_size` helper |
| `_count_parameters` | 15 | 25 | 4 | 36 | Dict of `{language: param_pattern}` + shared loop |
| All `detect` methods (nest 6-7) | — | — | — | — | Extract `_check_single_item` to reduce nesting by 2 |

#### CQ15: `features/quality/enforcer.py` — 6 funcs, total_cog=121
| Function | Cyc | Cog | Nest | Len | Fix |
|----------|-----|-----|------|-----|-----|
| `enforce_standards_impl` | 20 | 17 | 4 | 138 | Split into rule-loading, execution, summary-building phases |
| `parse_match_to_violation` | 15 | 29 | 5 | 46 | Extract `_extract_meta_variables` |
| `execute_rule` | 15 | 23 | 5 | 62 | Split file-discovery from rule-execution |

### Files 16-77 Summary

| # | File | Funcs | Cog |
|---|------|-------|-----|
| 16 | `refactoring/extractor.py` | 6 | 110 |
| 17 | `condense/service.py` | 5 | 107 |
| 18 | `refactoring/analyzer.py` | 7 | 105 |
| 19 | `utils/performance.py` | 8 | 105 |
| 20 | `deduplication/applicator.py` | 6 | 103 |
| 21 | `quality/tools.py` | 10 | 102 |
| 22 | `deduplication/applicator_executor.py` | 5 | 98 |
| 23 | `documentation/changelog_generator.py` | 6 | 95 |
| 24 | `deduplication/applicator_backup.py` | 4 | 94 |
| 25 | `refactoring/renamer.py` | 5 | 88 |
| 26 | `deduplication/coverage.py` | 5 | 87 |
| 27 | `quality/fixer.py` | 4 | 83 |
| 28 | `deduplication/diff.py` | 5 | 77 |
| 29 | `complexity/analyzer.py` | 4 | 75 |
| 30 | `core/executor.py` | 4 | 74 |
| 31-77 | 47 more files | 1-14 each | 4-67 |
