# 2026-03-08: Complexity Analysis

**98 functions** exceeding thresholds across **120 files** (1,766 total functions).

Thresholds: cyclomatic >10, cognitive >15, nesting >4, length >50.

Baselines: 434 (2026-03-04) -> 407 (2026-03-06) -> 100 (2026-03-06 post-refactor) -> **98** (2026-03-08).

## Summary

| Metric | Value |
|--------|-------|
| Total functions | 1,766 |
| Total files | 120 |
| Exceeding threshold | 98 (5.5%) |
| Avg cyclomatic | 4.36 |
| Avg cognitive | 4.56 |
| Max cyclomatic | 20 |
| Max cognitive | 33 |
| Max nesting | 6 |

## Violations by Module

### `core/executor.py` (4 violations)

| Function | Lines | Cyc | Cog | Nest | Len | Exceeds |
|----------|-------|-----|-----|------|-----|---------|
| `stream_ast_grep_results` | 489-589 | 16 | 29 | 6 | 101 | cyc, cog, nest, len |
| `filter_files_by_size` | 246-297 | 19 | 18 | 4 | 52 | cyc, cog, len |
| `run_command` | 69-159 | 10 | 11 | 4 | 91 | len |
| `get_supported_languages` | 23-66 | 8 | 16 | 5 | 44 | cog, nest |

### `core/usage_tracking.py` (1 violation)

| Function | Lines | Cyc | Cog | Nest | Len | Exceeds |
|----------|-------|-----|-----|------|-----|---------|
| `get_alerts` | 490-546 | 6 | 7 | 4 | 57 | len |

### `features/complexity/analyzer.py` (4 violations)

| Function | Lines | Cyc | Cog | Nest | Len | Exceeds |
|----------|-------|-----|-----|------|-----|---------|
| `_find_magic_numbers` | 286-346 | 13 | 25 | 5 | 61 | cyc, cog, nest, len |
| `_count_function_parameters` | 235-283 | 18 | 18 | 3 | 49 | cyc, cog |
| `extract_functions_from_file` | 35-75 | 12 | 23 | 5 | 41 | cyc, cog, nest |
| `analyze_file_complexity` | 429-471 | 4 | 9 | 5 | 43 | nest |

### `features/condense/service.py` (6 violations)

| Function | Lines | Cyc | Cog | Nest | Len | Exceeds |
|----------|-------|-----|-----|------|-----|---------|
| `condense_pack_impl` | 376-490 | 15 | 29 | 5 | 115 | cyc, cog, nest, len |
| `_count_structural_braces` | 242-274 | 17 | 28 | 5 | 33 | cyc, cog, nest |
| `_extract_python_surface` | 182-209 | 11 | 17 | 4 | 28 | cyc, cog |
| `extract_surface_impl` | 78-150 | 12 | 15 | 3 | 73 | cyc, len |
| `_extract_js_ts_surface` | 277-307 | 12 | 15 | 4 | 31 | cyc |

### `features/deduplication/analyzer.py` (2 violations)

| Function | Lines | Cyc | Cog | Nest | Len | Exceeds |
|----------|-------|-----|-----|------|-----|---------|
| `_compare_literal_maps` | 129-149 | 5 | 8 | 6 | 21 | nest |
| `_format_literal_variations` | 289-304 | 4 | 8 | 5 | 16 | nest |

### `features/deduplication/applicator.py` (7 violations)

| Function | Lines | Cyc | Cog | Nest | Len | Exceeds |
|----------|-------|-----|-----|------|-----|---------|
| `_plan_file_modification_order` | 451-505 | 19 | 26 | 6 | 55 | cyc, cog, nest, len |
| `_insert_python_import` | 559-582 | 13 | 24 | 4 | 24 | cyc, cog |
| `apply_deduplication` | 33-105 | 18 | 14 | 4 | 73 | cyc, len |
| `_extract_plan_components` | 154-207 | 8 | 14 | 4 | 54 | len |
| `_suggest_syntax_fix` | 639-653 | 11 | 13 | 4 | 15 | cyc |
| `_validate_and_prepare_plan` | 107-152 | 11 | 12 | 3 | 46 | cyc |

### `features/deduplication/applicator_backup.py` (4 violations)

| Function | Lines | Cyc | Cog | Nest | Len | Exceeds |
|----------|-------|-----|-----|------|-----|---------|
| `cleanup_old_backups` | 156-200 | 9 | 33 | 6 | 45 | cog, nest |
| `list_backups` | 218-247 | 7 | 23 | 5 | 30 | cog, nest |
| `create_backup` | 32-109 | 11 | 20 | 5 | 78 | cyc, cog, nest, len |
| `rollback` | 111-154 | 7 | 18 | 4 | 44 | cog |

### `features/deduplication/applicator_executor.py` (3 violations)

| Function | Lines | Cyc | Cog | Nest | Len | Exceeds |
|----------|-------|-----|-----|------|-----|---------|
| `_update_single_file` | 133-161 | 7 | 16 | 4 | 29 | cog |
| `_generate_preview` | 180-200 | 7 | 16 | 4 | 21 | cog |
| `apply_changes` | 20-76 | 5 | 6 | 4 | 57 | len |

### `features/deduplication/applicator_post_validator.py` (4 violations)

| Function | Lines | Cyc | Cog | Nest | Len | Exceeds |
|----------|-------|-----|-----|------|-----|---------|
| `_validate_file_structure` | 123-161 | 6 | 12 | 5 | 39 | nest |
| `_validate_python_structure` | 163-211 | 9 | 11 | 5 | 49 | nest |
| `_validate_java_structure` | 231-263 | 8 | 10 | 5 | 33 | nest |
| `_validate_file_syntax` | 69-109 | 5 | 7 | 5 | 41 | nest |

### `features/deduplication/coverage.py` (6 violations)

| Function | Lines | Cyc | Cog | Nest | Len | Exceeds |
|----------|-------|-----|-----|------|-----|---------|
| `has_test_coverage` | 346-383 | 13 | 25 | 6 | 38 | cyc, cog, nest |
| `_check_test_file_references_source` | 306-344 | 12 | 24 | 4 | 39 | cyc, cog |
| `_process_parallel_batch` | 541-576 | 6 | 17 | 5 | 36 | cog, nest |
| `_get_potential_test_paths` | 158-257 | 18 | 11 | 6 | 100 | cyc, nest, len |
| `find_test_file_patterns` | 62-156 | 19 | 10 | 4 | 95 | cyc, len |

### `features/deduplication/detector.py` (1 violation)

| Function | Lines | Cyc | Cog | Nest | Len | Exceeds |
|----------|-------|-----|-----|------|-----|---------|
| `_format_group_instances` | 574-587 | 2 | 3 | 5 | 14 | nest |

### `features/deduplication/diff.py` (5 violations)

| Function | Lines | Cyc | Cog | Nest | Len | Exceeds |
|----------|-------|-----|-----|------|-----|---------|
| `diff_preview_to_dict` | 309-361 | 14 | 29 | 5 | 53 | cyc, cog, nest, len |
| `build_nested_diff_tree` | 15-110 | 20 | 25 | 6 | 96 | cyc, cog, nest, len |
| `_format_alignment_entry` | 181-196 | 11 | 12 | 3 | 16 | cyc |
| `generate_file_diff` | 364-390 | 11 | 6 | 2 | 27 | cyc |
| `build_diff_tree` | 144-178 | 11 | 5 | 2 | 35 | cyc |

### `features/deduplication/ranker.py` (1 violation)

| Function | Lines | Cyc | Cog | Nest | Len | Exceeds |
|----------|-------|-----|-----|------|-----|---------|
| `_build_log_data` | 449-466 | 7 | 3 | 5 | 18 | nest |

### `features/documentation/api_docs_generator.py` (3 violations)

| Function | Lines | Cyc | Cog | Nest | Len | Exceeds |
|----------|-------|-----|-----|------|-----|---------|
| `parse_file` (Flask) | 136-167 | 7 | 10 | 5 | 32 | nest |
| `parse_file` (Express) | 199-223 | 4 | 10 | 5 | 25 | nest |
| `generate_api_docs_impl` | 597-647 | 6 | 7 | 3 | 51 | len |

### `features/documentation/changelog_generator.py` (5 violations)

| Function | Lines | Cyc | Cog | Nest | Len | Exceeds |
|----------|-------|-----|-----|------|-----|---------|
| `_get_commit_range` | 57-114 | 20 | 30 | 5 | 58 | cyc, cog, nest, len |
| `_format_conventional_section` | 484-519 | 9 | 18 | 4 | 36 | cog |
| `_group_commits_by_version` | 274-342 | 10 | 16 | 3 | 69 | cog, len |
| `_format_changelog_entry` | 356-388 | 11 | 12 | 2 | 33 | cyc |
| `_get_commits` | 117-181 | 7 | 12 | 3 | 65 | len |
| `generate_changelog_impl` | 555-635 | 12 | 7 | 3 | 81 | cyc, len |

### `features/documentation/sync_checker.py` (2 violations)

| Function | Lines | Cyc | Cog | Nest | Len | Exceeds |
|----------|-------|-----|-----|------|-----|---------|
| `_check_line_links` | 204-222 | 5 | 9 | 5 | 19 | nest |
| `sync_documentation_impl` | 486-539 | 6 | 3 | 2 | 54 | len |

### `features/quality/fixer.py` (4 violations)

| Function | Lines | Cyc | Cog | Nest | Len | Exceeds |
|----------|-------|-----|-----|------|-----|---------|
| `_is_variable_reassigned` | 559-594 | 14 | 27 | 4 | 36 | cyc, cog |
| `apply_pattern_fix` | 149-244 | 13 | 24 | 4 | 96 | cyc, cog, len |
| `apply_removal_fix` | 269-349 | 10 | 19 | 4 | 81 | cog, len |
| `_apply_single_fix` | 620-655 | 12 | 13 | 5 | 36 | cyc, nest |

### `features/quality/orphan_detector.py` (1 violation)

| Function | Lines | Cyc | Cog | Nest | Len | Exceeds |
|----------|-------|-----|-----|------|-----|---------|
| `_process_import_from_node` | 167-191 | 7 | 8 | 5 | 25 | nest |

### `features/quality/tools.py` (9 violations)

| Function | Lines | Cyc | Cog | Nest | Len | Exceeds |
|----------|-------|-----|-----|------|-----|---------|
| `create_linting_rule_tool` | 107-209 | 14 | 18 | 4 | 103 | cyc, cog, len |
| `list_rule_templates_tool` | 212-298 | 16 | 17 | 5 | 87 | cyc, cog, nest, len |
| `enforce_standards_tool` | 369-483 | 17 | 11 | 4 | 115 | cyc, len |
| `detect_security_issues_tool` | 875-1005 | 18 | 13 | 4 | 131 | cyc, len |
| `detect_orphans_tool` | 1008-1133 | 12 | 8 | 4 | 126 | cyc, len |
| `_create_mcp_field_definitions` | 1136-1219 | 20 | 7 | 4 | 84 | cyc, len |
| `register_quality_tools` | 1222-1360 | 3 | 0 | 3 | 139 | len |
| `generate_quality_report_tool` | 678-778 | 12 | 8 | 4 | 101 | cyc, len |
| `_dict_to_enforcement_result` | 781-838 | 6 | 13 | 3 | 58 | len |
| `apply_standards_fixes_tool` | 556-675 | 9 | 7 | 4 | 120 | len |

### `features/refactoring/analyzer.py` (8 violations)

| Function | Lines | Cyc | Cog | Nest | Len | Exceeds |
|----------|-------|-----|-----|------|-----|---------|
| `_find_python_base_variables` | 214-262 | 11 | 29 | 5 | 49 | cyc, cog, nest |
| `_analyze_js_ts_variables` | 436-530 | 8 | 18 | 5 | 95 | cog, nest, len |
| `_analyze_java_variables` | 532-638 | 8 | 18 | 5 | 107 | cog, nest, len |
| `_find_python_standalone_identifiers` | 287-326 | 10 | 17 | 5 | 40 | cog, nest |
| `_analyze_python_variables` | 328-394 | - | - | - | - | *(see below)* |
| `_get_variable_classification` | 395-434 | 13 | 13 | 3 | 40 | cyc |
| `_find_python_assignments` | 188-212 | 4 | 7 | 5 | 25 | nest |
| `analyze_selection` | 36-99 | 7 | 3 | 3 | 64 | len |

### `features/refactoring/extractor.py` (6 violations)

| Function | Lines | Cyc | Cog | Nest | Len | Exceeds |
|----------|-------|-----|-----|------|-----|---------|
| `_generate_docstring` | 215-267 | 13 | 31 | 5 | 53 | cyc, cog, nest, len |
| `_generate_function_body` | 269-314 | 15 | 25 | 4 | 46 | cyc, cog |
| `_generate_signature` | 158-213 | 18 | 13 | 4 | 56 | cyc, len |
| `_scan_imports` | 385-413 | 10 | 18 | 5 | 29 | cog, nest |
| `extract_function` | 35-113 | 9 | 12 | 5 | 79 | nest, len |
| `_apply_extraction` | 488-545 | 7 | 11 | 4 | 58 | len |

### `features/refactoring/renamer.py` (5 violations)

| Function | Lines | Cyc | Cog | Nest | Len | Exceeds |
|----------|-------|-----|-----|------|-----|---------|
| `find_symbol_references` | 37-121 | 12 | 20 | 6 | 85 | cyc, cog, nest, len |
| `check_naming_conflicts` | 502-538 | 11 | 20 | 5 | 37 | cyc, cog, nest |
| `_find_js_scope_end` | 474-500 | 8 | 19 | 5 | 27 | cog, nest |
| `_build_js_scope_tree` | 396-450 | 6 | 11 | 5 | 55 | nest, len |
| `_analyze_python_variables` *(renamer)* | 335-394 | 10 | 18 | 6 | 60 | cog, nest, len |

### `utils/formatters.py` (1 violation)

| Function | Lines | Cyc | Cog | Nest | Len | Exceeds |
|----------|-------|-----|-----|------|-----|---------|
| `_run_prettier` | 678-710 | 6 | 11 | 5 | 33 | nest |

### `utils/performance.py` (7 violations)

| Function | Lines | Cyc | Cog | Nest | Len | Exceeds |
|----------|-------|-----|-----|------|-----|---------|
| `monitor_performance` | 21-86 | 9 | 14 | 5 | 66 | nest, len |
| `track_slow_operations` | 207-258 | 5 | 14 | 6 | 52 | nest, len |
| `decorator` (track_slow_operations) | 222-256 | 4 | 14 | 6 | 35 | nest |
| `wrapper` (track_slow_operations) | 224-254 | 4 | 14 | 6 | 31 | nest |
| `monitor_performance_async` | 89-153 | 7 | 13 | 5 | 65 | nest, len |
| `wrapper` (monitor_performance) | 43-84 | 5 | 12 | 5 | 42 | nest |
| `wrapper` (monitor_performance_async) | 107-151 | 5 | 12 | 5 | 45 | nest |

## Violation Distribution by Type

| Violation Type | Count |
|----------------|-------|
| cognitive only | 7 |
| cyclomatic only | 10 |
| nesting only | 22 |
| length only | 15 |
| multiple | 44 |

## Hotspot Files (5+ violations)

| File | Violations | Worst Cognitive |
|------|------------|-----------------|
| `quality/tools.py` | 9 | 18 |
| `refactoring/analyzer.py` | 8 | 29 |
| `deduplication/applicator.py` | 7 | 26 |
| `utils/performance.py` | 7 | 14 |
| `deduplication/coverage.py` | 6 | 25 |
| `refactoring/extractor.py` | 6 | 31 |
| `condense/service.py` | 6 | 29 |
| `documentation/changelog_generator.py` | 5 | 30 |
| `refactoring/renamer.py` | 5 | 20 |
| `deduplication/diff.py` | 5 | 29 |

## Top 10 by Cognitive Complexity

| Function | File | Cog |
|----------|------|-----|
| `cleanup_old_backups` | applicator_backup.py | 33 |
| `_generate_docstring` | extractor.py | 31 |
| `_get_commit_range` | changelog_generator.py | 30 |
| `stream_ast_grep_results` | executor.py | 29 |
| `condense_pack_impl` | service.py | 29 |
| `diff_preview_to_dict` | diff.py | 29 |
| `_find_python_base_variables` | analyzer.py | 29 |
| `_count_structural_braces` | service.py | 28 |
| `_is_variable_reassigned` | fixer.py | 27 |
| `_plan_file_modification_order` | applicator.py | 26 |

## Change History (from gitlog-top20.txt)

Files with current violations that have been recently modified, grouped by refactoring phase.

### Complexity Refactoring (2026-03-06)

The 2026-03-06 batch refactors reduced violations from 434 to 100. Files with *remaining* violations that were touched:

| Commit | File(s) Touched (with violations) | Description |
|--------|-----------------------------------|-------------|
| `6bf92be` | `search/docs.py` | Batch 10 complexity reduction |
| `98dd5a9` | `deduplication/similarity.py`, `search/service.py` | Batch 3 complexity reduction |
| `7ec47ad` | `deduplication/analyzer.py`, `deduplication/generator.py`, `documentation/docstring_generator.py` | Batch 2 complexity reduction |
| `c12667e` | `deduplication/similarity.py` | Decompose `_normalize_for_ast` |
| `5e6b3de` | `deduplication/similarity.py` | Decompose `HybridSimilarityConfig.__post_init__` |
| `029b7b2` | `deduplication/similarity.py` | Extract `_normalize_indentation` |
| `96632cf` | `deduplication/analyzer.py`, `deduplication/similarity.py` | Fix 59 ruff errors from refactoring |
| `5a3f682` | `deduplication/analyzer.py`, `deduplication/generator.py`, `deduplication/similarity.py`, `documentation/docstring_generator.py` | Fix 38 mypy errors from refactoring |

### Bug Fixes & Type Fixes (2026-03-06 -- 2026-03-07)

| Commit | File(s) Touched (with violations) | Description |
|--------|-----------------------------------|-------------|
| `6473709` | `documentation/docstring_generator.py` | Guard depth counter in `_split_params` |
| `590b4d1` | `deduplication/similarity.py` | Adaptive indent divisor in `_normalize_for_ast` |
| `f1b587d` | `search/service.py` | Wrap `yaml.dump` return with `str()` |
| `0a5bb3e` | `deduplication/similarity.py` | Cross-env mypy suppress for `AutoModel` |
| `58e60a9` | `deduplication/similarity.py` | Stabilize `type: ignore` for cross-env mypy |

### Style & Constants (2026-03-04 -- 2026-03-08)

| Commit | File(s) Touched (with violations) | Description |
|--------|-----------------------------------|-------------|
| `aebd562` | `search/service.py` | Derive severity prefix from lookup dict |
| `2bb7b59` | `deduplication/analyzer.py`, `deduplication/generator.py`, `deduplication/similarity.py`, `documentation/docstring_generator.py`, `search/service.py` | Ruff format 42 files |
| `92741ab` | `search/service.py` | Consolidate D1-D4 duplication fixes |
| `afdf71a` | `deduplication/similarity.py`, `documentation/docstring_generator.py`, `search/service.py` | Extract 90 magic numbers into constants |
| `0cf6cd3` | `deduplication/analyzer.py`, `deduplication/similarity.py` | Extract remaining magic numbers |
| `460722b` | `deduplication/analyzer.py`, `deduplication/similarity.py` | Slicing helper + dedup scoring enums |

### Earlier Refactors (2025-11 -- 2026-02)

| Commit | File(s) Touched (with violations) | Description |
|--------|-----------------------------------|-------------|
| `7551cba` | `deduplication/generator.py`, `quality/tools.py`, `search/service.py` | Reduce violations to zero (2025-11-29) |
| `898ff8b` | `quality/tools.py` | Simplify MCP tool definitions (2025-11-28) |
| `074c744` | `deduplication/analyzer.py` | Reduce complexity across analyzer (2025-11-28) |
| `12cfbfb` | `search/service.py` | Extract search service helpers (2025-11-28) |
| `9bdd029` | `deduplication/analyzer.py`, `deduplication/generator.py` | Resolve 6 complexity violations (2026-01-09) |
| `97fdb42` | `deduplication/analyzer.py` | Extract `_parse_conditional_matches` (2026-02-12) |
| `b0ea4b0` | `documentation/docstring_generator.py`, `search/service.py` | Extract magic numbers (2026-02-12) |
| `484fdcf` | `deduplication/similarity.py` | Extract magic numbers to constants (2026-02-28) |

### Files with Violations Never Touched in History

These violation files have no entries in gitlog-top20.txt, suggesting they haven't been refactored recently:

- `core/executor.py` (4 violations, worst cog=29)
- `core/usage_tracking.py` (1 violation)
- `features/complexity/analyzer.py` (4 violations, worst cog=25)
- `features/condense/service.py` (6 violations, worst cog=29)
- `features/deduplication/applicator.py` (7 violations, worst cog=26)
- `features/deduplication/applicator_backup.py` (4 violations, worst cog=33)
- `features/deduplication/applicator_executor.py` (3 violations)
- `features/deduplication/applicator_post_validator.py` (4 violations)
- `features/deduplication/coverage.py` (6 violations, worst cog=25)
- `features/deduplication/detector.py` (1 violation)
- `features/deduplication/diff.py` (5 violations, worst cog=29)
- `features/deduplication/ranker.py` (1 violation)
- `features/documentation/api_docs_generator.py` (3 violations)
- `features/documentation/changelog_generator.py` (5 violations, worst cog=30)
- `features/documentation/sync_checker.py` (2 violations)
- `features/quality/fixer.py` (4 violations, worst cog=27)
- `features/quality/orphan_detector.py` (1 violation)
- `features/refactoring/analyzer.py` (8 violations, worst cog=29)
- `features/refactoring/extractor.py` (6 violations, worst cog=31)
- `features/refactoring/renamer.py` (5 violations, worst cog=20)
- `utils/formatters.py` (1 violation)
- `utils/performance.py` (7 violations)

## Appendix: Extracted Helper Functions

Helper functions created during complexity refactoring, organized by module. These functions were extracted from high-complexity parents to reduce cyclomatic, cognitive, and nesting metrics.

**Total extracted helpers: 147** across 7 modules.

### `search/service.py` (72 helpers)

Primary decomposition targets: `find_code_impl`, `search_with_rule_impl`, `debug_pattern_impl`, `develop_pattern_impl`.

| Helper | Line | Parent / Purpose | ~Lines |
|--------|------|------------------|--------|
| `_run_scan_against_code` | 92 | Execute ast-grep scan with error handling | 37 |
| `_prepare_search_targets` | 148 | Prepare targets with optional size filtering | 30 |
| `_build_search_args` | 179 | Build ast-grep CLI arguments | 10 |
| `_format_cached_results` | 190 | Format cached results by output format | 16 |
| `_check_cache` | 207 | Check cache before search | 23 |
| `_execute_search` | 231 | Execute search and cache results | 12 |
| `_format_search_results` | 243 | Format results by output format | 12 |
| `_is_early_return_value` | 255 | Check for empty result sentinel | 15 |
| `_validate_output_format` | 271 | Validate text/json output format | 9 |
| `_handle_empty_search_targets` | 282 | Handle all-files-skipped case | 9 |
| `_validate_and_prepare_search` | 294 | End-to-end search param validation | 21 |
| `_run_find_code_search` | 317 | Orchestrate find_code_impl | 28 |
| `_log_find_code_error` | 347 | Log + Sentry capture for find_code | 12 |
| `_validate_yaml_rule` | 406 | Validate YAML rule structure | 23 |
| `_check_relational_entry` | 435 | Check single relational rule for stopBy | 16 |
| `_check_composite_entries` | 453 | Check composite rule entries recursively | 11 |
| `_check_relational_rule_for_stopby` | 465 | Recursive stopBy checker | 19 |
| `_check_yaml_rule_for_common_mistakes` | 485 | Detect lowercase metavars, etc. | 22 |
| `_execute_rule_search` | 509 | Execute YAML rule search | 24 |
| `_prepend_warnings_to_result` | 534 | Prepend warnings to result string | 30 |
| `_check_rule_cache` | 564 | Check rule cache | 12 |
| `_store_rule_result_in_cache` | 577 | Store rule result in cache | 5 |
| `_log_rule_warnings` | 583 | Log common-mistake warnings | 10 |
| `_run_rule_search_with_cache` | 594 | Rule search with caching orchestration | 80 |
| `_build_relational_rule` | 676 | Build relational rule with stopBy | 19 |
| `_add_relational_to_rule` | 696 | Add relational constraint to rule | 18 |
| `_generate_rule_id` | 715 | Deterministic rule ID from pattern | 7 |
| `_build_rule_object` | 723 | Build rule object from pattern+constraints | 21 |
| `_build_yaml_object` | 746 | Build complete YAML object | 59 |
| `_invalid_metavar_issue` | 806 | Build MetavariableInfo for invalid metavar | 8 |
| `_extract_invalid_metavariables` | 816 | Extract invalid metavars from pattern | 7 |
| `_add_metavar_if_new` | 825 | Deduplicated metavar tracking | 16 |
| `_extract_multi_metavariables` | 853 | Extract $$$ multi-node metavars | 6 |
| `_extract_unnamed_metavariables` | 861 | Extract $$ unnamed metavars | 8 |
| `_extract_non_capturing_metavariables` | 871 | Extract $_ non-capturing metavars | 6 |
| `_extract_single_metavariables` | 879 | Extract $NAME single metavars | 11 |
| `_extract_metavariables` | 892 | Main metavar extraction orchestrator | 36 |
| `_metavar_suggestion` | 929 | Build suggestion text for metavar | 5 |
| `_check_invalid_metavar_issues` | 936 | Check for invalid metavar issues | 4 |
| `_single_arg_issue` | 951 | Build PatternIssue for single-arg metavar | 9 |
| `_check_single_arg_metavar_issues` | 962 | Check single metavar in fn args | 10 |
| `_check_fragment_issues` | 973 | Detect incomplete code fragments | 13 |
| `_check_pattern_issues` | 987 | Check common pattern issues | 17 |
| `_extract_root_kind` | 1006 | Extract root node kind from AST | 24 |
| `_truncate_ast` | 1032 | Truncate AST to display limit | 5 |
| `_collect_ast_differences` | 1039 | Collect structural AST differences | 10 |
| `_compare_asts` | 1051 | Compare pattern vs code ASTs | 23 |
| `_attempt_match` | 1076 | Attempt pattern match against code | 44 |
| `_add_suggestions_by_severity` | 1122 | Severity-based suggestion lookup dict | 15 |
| `_add_structural_suggestions` | 1138 | Structural mismatch suggestions | 10 |
| `_add_debug_suggestions` | 1152 | Debug suggestions for non-match | 19 |
| `_add_default_suggestions` | 1173 | Default guidance fallback | 16 |
| `_generate_suggestions` | 1190 | Suggestion orchestrator | 31 |
| `_get_pattern_ast` | 1223 | Get pattern AST; return (text, valid) | 14 |
| `_get_code_ast` | 1239 | Get code AST text | 14 |
| `_run_debug_analysis` | 1255 | Execute debug analysis, build result | 29 |
| `_get_identifier_pattern` | 1572 | Language identifier pattern with fallback | 3 |
| `_get_keywords` | 1577 | Language keywords with fallback | 2 |
| `_extract_identifiers` | 1582 | Extract unique identifiers from code | 14 |
| `_extract_literals` | 1597 | Extract string/number literals | 5 |
| `_count_ast_depth` | 1604 | Estimate AST depth from indentation | 9 |
| `_determine_complexity` | 1615 | Determine code complexity from AST | 11 |
| `_extract_child_kinds` | 1628 | Extract child node kinds from AST | 12 |
| `_analyze_code` | 1642 | Analyze code structure for patterns | 27 |
| `_pick_metavar_name` | 1671 | Pick unique metavar name | 11 |
| `_generate_generalized_pattern` | 1683 | Replace identifiers/literals with metavars | 18 |
| `_generate_structural_pattern` | 1703 | Generate kind-based YAML pattern | 5 |
| `_exact_confidence` | 1709 | Confidence level for exact pattern | 5 |
| `_generalized_suggestion` | 1716 | Build generalized pattern suggestion | 14 |
| `_generate_pattern_suggestions` | 1732 | Multi-pattern suggestions with scores | 32 |
| `_matched_refinement_steps` | 1766 | Refinement steps when matched | 23 |
| `_unmatched_refinement_steps` | 1791 | Refinement steps when unmatched | 24 |
| `_generate_refinement_steps` | 1817 | Refinement step dispatcher | 10 |
| `_generate_yaml_template` | 1829 | Generate YAML rule template | 42 |
| `_generate_next_steps` | 1873 | Next-step guidance | 5 |
| `_test_pattern_match` | 1879 | Test if pattern matches code | 15 |
| `_select_best_pattern` | 1896 | Select and test best pattern | 15 |
| `_build_develop_result` | 1913 | Build PatternDevelopResult | 24 |
| `_run_develop_analysis` | 1939 | Execute develop analysis | 17 |

### `documentation/docstring_generator.py` (32 helpers)

Primary decomposition targets: `generate_docstrings_impl`, `_generate_docstring_for_function`.

| Helper | Line | Parent / Purpose | ~Lines |
|--------|------|------------------|--------|
| `_split_camel_case` | 32 | Split camelCase into words | 14 |
| `_split_snake_case` | 48 | Split snake_case into words | 8 |
| `_infer_description_from_name` | 139 | Infer description from fn name prefixes | 22 |
| `_build_prefix_description` | 162 | Build description from verb prefix | 10 |
| `_check_suffix_pattern` | 335 | Check name against suffix pattern | 6 |
| `_check_prefix_pattern` | 344 | Check name against prefix pattern | 6 |
| `_infer_parameter_description` | 353 | Infer param description from name | 15 |
| `_get_return_from_type` | 401 | Return description from type annotation | 7 |
| `_apply_return_prefix_handler` | 410 | Apply return prefix template | 6 |
| `_function_name_words` | 417 | Split fn name into lowercase words | 3 |
| `_infer_return_description` | 423 | Infer return description | 20 |
| `_parse_single_python_param` | 445 | Parse Python param to ParameterInfo | 16 |
| `_split_python_params` | 462 | Split Python params respecting brackets | 22 |
| `_split_js_ts_params` | 486 | Split JS/TS params respecting brackets | 20 |
| `_non_self_params` | 845 | Filter out self/this params | 2 |
| `_has_return` | 849 | Check for meaningful return type | 2 |
| `_google_param_line` | 853 | Generate Google-style param line | 4 |
| `_generate_google_docstring` | 860 | Generate Google-style docstring | 11 |
| `_numpy_param_lines` | 873 | NumPy-style param doc lines | 4 |
| `_generate_numpy_docstring` | 878 | Generate NumPy-style docstring | 13 |
| `_sphinx_param_lines` | 893 | Sphinx-style param doc lines | 7 |
| `_generate_sphinx_docstring` | 901 | Generate Sphinx-style docstring | 13 |
| `_generate_jsdoc` | 916 | Generate JSDoc documentation | 31 |
| `_generate_javadoc` | 949 | Generate Javadoc documentation | 28 |
| `_process_file_for_docstrings` | 979 | Process single file for all fns | 45 |
| `_apply_docstrings_to_files` | 1026 | Apply generated docstrings to files | 28 |
| `_detect_project_style` | 1055 | Auto-detect docstring style | 20 |
| `_generate_docstring_for_function` | 1077 | Generate docstring for single fn | 36 |
| `_should_skip_function` | 1115 | Skip private/dunder functions | 19 |
| `_format_docstring_block` | 1136 | Format block, return (text, idx) | 14 |
| `_apply_docstring_to_file` | 1151 | Apply docstring at correct location | 33 |
| `_process_files_batch` | 1186 | Process batch of files | 34 |
| `_log_and_build_result` | 1222 | Log ops and build final result | 20 |

### `quality/tools.py` (22 helpers)

Primary decomposition targets: `enforce_standards_tool`, `detect_security_issues_tool`, `register_quality_tools`.

| Helper | Line | Parent / Purpose | ~Lines |
|--------|------|------------------|--------|
| `_create_rule_from_params` | 40 | Create linting rule from params | 27 |
| `_save_rule_if_requested` | 69 | Save rule to project | 15 |
| `_format_rule_result` | 86 | Format rule creation result | 22 |
| `_tool_context` | 109 | Context manager for error handling + timing | 80 |
| `_get_default_exclude_patterns` | 283 | Default file scan exclude patterns | 3 |
| `_normalize_exclude_patterns` | 288 | Normalize excludes, enforce venv | 6 |
| `_validate_enforcement_inputs` | 295 | Validate enforce_standards inputs | 13 |
| `_format_enforcement_output` | 312 | Format enforcement result by format | 25 |
| `_convert_violations_to_objects` | 442 | Dict violations to RuleViolation objects | 19 |
| `_infer_project_folder` | 463 | Infer project folder from violations | 16 |
| `_format_fix_results` | 479 | Format fix results for output | 8 |
| `_group_violations` | 685 | Group violations by rule and file | 18 |
| `_dict_to_enforcement_result` | 705 | Dict to EnforcementResult conversion | 16 |
| `_format_security_issues` | 722 | Format security issues for output | 22 |
| `_format_issues_by_severity` | 745 | Format issues grouped by severity | 12 |
| `_linting_field_definitions` | 968 | MCP field defs for linting tools | 20 |
| `_enforcement_field_definitions` | 990 | MCP field defs for enforcement tools | 47 |
| `_scanning_field_definitions` | 1037 | MCP field defs for scanning tools | 28 |
| `_create_mcp_field_definitions` | 1066 | Top-level MCP field def dispatcher | 6 |
| `_register_linting_tools` | 1075 | Register linting tools with MCP | 36 |
| `_register_enforcement_tools` | 1114 | Register enforcement tools with MCP | 59 |
| `_register_scanning_tools` | 1177 | Register scanning tools with MCP | 50 |

### `deduplication/generator.py` (10 helpers)

Primary decomposition targets: `_infer_type_from_value`, `_generate_parameter_name`.

| Helper | Line | Parent / Purpose | ~Lines |
|--------|------|------------------|--------|
| `_infer_from_identifier_name` | 114 | Infer type from identifier naming | 26 |
| `_is_boolean_literal` | 157 | Check True/False literal | 2 |
| `_is_null_literal` | 162 | Check None/null/nil/undefined | 2 |
| `_is_quoted_string` | 167 | Check quoted string literal | 3 |
| `_is_integer_literal` | 172 | Check integer literal | 2 |
| `_try_get_float_type` | 177 | Parse and determine float type | 10 |
| `_get_collection_type` | 188 | Get collection type for literals | 8 |
| `_infer_single_value_type` | 198 | Infer type from single literal | 40 |
| `_strip_param_prefix` | 962 | Strip is_/has_ prefixes | 6 |
| `_build_param_candidates` | 970 | Build candidate param names | 5 |

### `deduplication/analyzer.py` (6 helpers)

Primary decomposition targets: `_analyze_variations`, `identify_varying_identifiers`.

| Helper | Line | Parent / Purpose | ~Lines |
|--------|------|------------------|--------|
| `_detect_nested_function_call` | 900 | Detect nested fn call identifiers | 16 |
| `_collect_all_variations` | 919 | Aggregate literal/conditional/id variations | 28 |
| `_determine_overall_severity` | 949 | Calculate severity from variation counts | 9 |
| `_get_usage_type` | 1040 | Determine usage type from context | 8 |
| `_extract_identifiers_from_code` | 1050 | Extract identifiers with position info | 30 |
| `identify_varying_identifiers` | 1004 | Public API for identifier variation | 35 |

### `search/docs.py` (4 helpers)

Primary decomposition target: `get_ast_grep_patterns`.

| Helper | Line | Parent / Purpose | ~Lines |
|--------|------|------------------|--------|
| `_resolve_language` | 1944 | Resolve language alias | 2 |
| `_resolve_categories` | 1948 | Return categories or error string | 9 |
| `_format_pattern_entry` | 1962 | Format pattern with description | 7 |
| `_build_pattern_output` | 1970 | Build output for categories | 15 |

### `deduplication/similarity.py` (1 helper)

| Helper | Line | Parent / Purpose | ~Lines |
|--------|------|------------------|--------|
| `_check_transformers_available` | 1571 | Check transformers/torch availability | 10 |

### Summary by Extraction Pattern

| Pattern | Count | Examples |
|---------|-------|---------|
| Validate/check inputs | 18 | `_validate_yaml_rule`, `_validate_enforcement_inputs`, `_check_relational_entry` |
| Format/build output | 28 | `_format_cached_results`, `_format_rule_result`, `_build_develop_result` |
| Extract/parse data | 22 | `_extract_metavariables`, `_extract_identifiers`, `_parse_single_python_param` |
| Type inference | 10 | `_is_boolean_literal`, `_infer_single_value_type`, `_infer_from_identifier_name` |
| Orchestrate sub-steps | 15 | `_run_find_code_search`, `_run_rule_search_with_cache`, `_run_develop_analysis` |
| Generate content | 19 | `_generate_google_docstring`, `_generate_yaml_template`, `_generate_suggestions` |
| Register/configure | 7 | `_register_linting_tools`, `_linting_field_definitions`, `_create_mcp_field_definitions` |
| Utility/predicate | 28 | `_non_self_params`, `_has_return`, `_is_early_return_value`, `_truncate_ast` |

## Refresh Command

```bash
uv run python -c "
import json
from ast_grep_mcp.features.complexity.tools import analyze_complexity_tool
result = analyze_complexity_tool(project_folder='$(pwd)/src', language='python')
print(json.dumps(result, indent=2))
"
```
