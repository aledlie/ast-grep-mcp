# Backlog

## Complexity Refactoring Queue (2026-03-04)

> **Note (2026-03-08):** Spot-checks of CQ1–CQ9 show the highest-priority functions (e.g. `_extract_literals_with_ast_grep`, `_determine_severity`, `_suggest_parameter_name`, `_check_relational_rule_for_stopby`, `_format_diff_with_line_numbers`) have already been refactored in prior commits. Run `uv run python scripts/run_all_analysis.py` for a fresh baseline before working on specific CQ items.

Threshold baseline from `analyze_complexity` defaults: cyclomatic `>10`, cognitive `>15`, nesting `>4`, length `>50`.
Source for all items below: full quality run on **2026-03-04** (`analyze_codebase.py` / `analyze_complexity_tool`) with **434** functions exceeding thresholds.


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
