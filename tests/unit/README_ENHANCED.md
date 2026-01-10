# unit

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareSourceCode",
  "name": "unit",
  "description": "Directory containing 25 code files with 155 classes and 38 functions",
  "programmingLanguage": [
    {
      "@type": "ComputerLanguage",
      "name": "Python"
    }
  ],
  "featureList": [
    "155 class definitions",
    "38 function definitions"
  ]
}
</script>

## Overview

This directory contains 25 code file(s) with extracted schemas.

## Files and Schemas

### `conftest.py` (python)

**Classes:**
- `MockFastMCP` - Line 19
  - Mock FastMCP class for testing.
  - Methods: __init__, tool, run, get
- `MCPNamespace` - Line 120

**Functions:**
- `mock_field() -> Any` - Line 41
- `mcp_main()` - Line 52
- `apply_deduplication_tool(mcp_main)` - Line 127
- `find_duplication_tool(mcp_main)` - Line 135
- `analyze_deduplication_candidates_tool(mcp_main)` - Line 143
- `benchmark_deduplication_tool(mcp_main)` - Line 151
- `rewrite_code_tool(mcp_main)` - Line 159
- `schema_client()` - Line 167
- `enforce_standards_tool(mcp_main)` - Line 174
- `list_backups_tool(mcp_main)` - Line 182
- ... and 20 more functions

**Key Imports:** `ast_grep_mcp.core`, `ast_grep_mcp.features.complexity.tools`, `ast_grep_mcp.features.deduplication.tools`, `ast_grep_mcp.features.documentation.tools`, `ast_grep_mcp.features.quality.tools` (+7 more)

### `test_analysis_config.py` (python)

**Classes:**
- `TestAnalysisConfigCreation` - Line 12
  - Test AnalysisConfig creation and initialization.
  - Methods: test_minimal_config, test_full_config
- `TestAnalysisConfigValidation` - Line 63
  - Test AnalysisConfig validation in __post_init__.
  - Methods: test_invalid_min_similarity_too_low, test_invalid_min_similarity_too_high, test_valid_min_similarity_boundaries, test_invalid_min_lines_zero, test_invalid_min_lines_negative (+4 more)
- `TestAnalysisConfigNormalization` - Line 155
  - Test AnalysisConfig normalization in __post_init__.
  - Methods: test_exclude_patterns_none_normalized_to_empty_list, test_exclude_patterns_empty_list_preserved, test_exclude_patterns_with_values_preserved
- `TestAnalysisConfigSerialization` - Line 188
  - Test AnalysisConfig to_dict() serialization.
  - Methods: test_to_dict_minimal_config, test_to_dict_full_config, test_to_dict_excludes_callback_function
- `TestAnalysisConfigEdgeCases` - Line 265
  - Test AnalysisConfig edge cases and boundary conditions.
  - Methods: test_very_high_max_candidates, test_very_high_max_workers, test_many_exclude_patterns, test_unicode_in_project_path, test_unicode_in_language
- `TestAnalysisConfigCallbackIntegration` - Line 314
  - Test AnalysisConfig integration with progress callbacks.
  - Methods: test_callback_invocation_tracking, test_no_callback_none_check

**Key Imports:** `pytest`, `src.ast_grep_mcp.features.deduplication.config`

### `test_apply_deduplication.py` (python)

**Classes:**
- `TestApplyDeduplication` - Line 35
  - Tests for apply_deduplication MCP tool.
  - Methods: test_tool_registered, test_dry_run_returns_correct_structure, test_apply_mode_returns_correct_structure, test_validates_project_folder_exists, test_validates_refactoring_plan_required (+1 more)
- `TestBackupIntegration` - Line 116
  - Tests for Phase 3.2 backup integration in apply_deduplication.
  - Methods: test_backup_created_on_apply, test_backup_metadata_contains_deduplication_info, test_backup_preserves_original_files, test_rollback_restores_original_content, test_multi_file_backup_and_rollback (+2 more)
- `TestPhase33MultiFileOrchestration` - Line 316
  - Tests for Phase 3.3 Multi-File Orchestration in apply_deduplication.
  - Methods: test_orchestration_creates_extracted_function_file, test_orchestration_creates_file_before_updates, test_orchestration_atomic_rollback_on_failure, test_orchestration_appends_to_existing_file, test_orchestration_handles_multiple_files_atomically
- `TestOrchestrationHelperFunctions` - Line 481
  - Tests for Phase 3.3 orchestration helper functions.
  - Methods: test_plan_file_modification_order_basic, test_add_import_to_content_python, test_add_import_to_content_python_no_existing_imports, test_add_import_to_content_typescript, test_add_import_to_content_skips_duplicate (+1 more)

**Key Imports:** `ast_grep_mcp.features.deduplication.applicator`, `ast_grep_mcp.features.rewrite.backup`, `json`, `os`, `pytest` (+3 more)

### `test_batch_coverage.py` (python)

**Classes:**
- `TestBatchCoverageOptimization` - Line 17
  - Tests for batch test coverage optimization.
  - Methods: temp_project, detector, test_find_all_test_files_python, test_find_all_test_files_empty_project, test_has_test_coverage_optimized_with_test (+5 more)
- `TestBatchVsSequentialEquivalence` - Line 173
  - Tests verifying batch and sequential methods produce same results.
  - Methods: detector, test_batch_sequential_equivalence
- `TestBatchCoverageIntegration` - Line 229
  - Integration tests for batch coverage in orchestrator.
  - Methods: mock_detector, test_orchestrator_uses_batch_method, test_orchestrator_deduplicates_files

**Key Imports:** `ast_grep_mcp.features.deduplication.analysis_orchestrator`, `ast_grep_mcp.features.deduplication.coverage`, `os`, `pathlib`, `pytest` (+2 more)

### `test_code_smells.py` (python)

**Classes:**
- `TestParameterCount` - Line 17
  - Test parameter counting in functions.
  - Methods: test_no_parameters, test_single_parameter, test_multiple_parameters, test_self_excluded, test_cls_excluded (+7 more)
- `TestMagicNumbers` - Line 106
  - Test magic number detection.
  - Methods: test_no_magic_numbers, test_simple_magic_number, test_allowed_values_excluded, test_comments_excluded, test_float_magic_numbers (+2 more)
- `TestClassExtraction` - Line 171
  - Test class extraction from files.
  - Methods: test_extract_simple_class, test_extract_no_classes
- `TestCodeSmellDetection` - Line 215
  - Integration tests for code smell detection.
  - Methods: test_long_function_detection, test_parameter_bloat_detection
- `TestEdgeCases` - Line 237
  - Test edge cases for code smell detection.
  - Methods: test_empty_function, test_lambda_not_counted, test_nested_parentheses_in_params, test_no_magic_in_strings

**Key Imports:** `ast_grep_mcp.features.quality.smells_detectors`, `os`, `sys`, `tempfile`

### `test_complexity.py` (python)

**Classes:**
- `TestCyclomaticComplexity` - Line 29
  - Test cyclomatic complexity calculation.
  - Methods: test_simple_function, test_single_if, test_if_elif_else, test_for_loop, test_while_loop (+9 more)
- `TestCognitiveComplexity` - Line 209
  - Test cognitive complexity calculation.
  - Methods: test_simple_function, test_single_if, test_nested_if_penalty, test_deeply_nested, test_logical_operators_add
- `TestNestingDepth` - Line 271
  - Test nesting depth calculation.
  - Methods: test_no_nesting, test_single_level, test_two_levels, test_deep_nesting, test_loop_nesting
- `TestComplexityPatterns` - Line 332
  - Test language pattern retrieval.
  - Methods: test_python_patterns, test_typescript_patterns, test_javascript_patterns, test_java_patterns, test_unknown_language_defaults_to_python (+1 more)
- `TestComplexityDataClasses` - Line 371
  - Test complexity data classes.
  - Methods: test_complexity_metrics, test_complexity_metrics_defaults, test_function_complexity, test_complexity_thresholds, test_custom_thresholds
- `TestComplexityStorage` - Line 435
  - Test SQLite storage for complexity results.
  - Methods: test_storage_initialization, test_get_or_create_project, test_store_analysis_run, test_get_project_trends
- `TestAnalyzeFileComplexity` - Line 521
  - Test file complexity analysis.
  - Methods: test_analyze_empty_file, test_analyze_simple_function
- `TestEdgeCases` - Line 561
  - Test edge cases and boundary conditions.
  - Methods: test_empty_code, test_code_with_only_comments, test_multiline_string, test_very_long_function, test_tabs_vs_spaces
- `TestBenchmark` - Line 628
  - Performance benchmark tests for complexity analysis.
  - Methods: _generate_function, test_cyclomatic_1000_functions, test_cognitive_1000_functions, test_nesting_depth_1000_functions, test_all_metrics_1000_functions (+1 more)

**Key Imports:** `ast_grep_mcp.features.complexity.analyzer`, `ast_grep_mcp.features.complexity.metrics`, `ast_grep_mcp.features.complexity.storage`, `ast_grep_mcp.models.complexity`, `ast_grep_mcp.utils.console_logger` (+6 more)

### `test_conftest_fixtures.py` (python)

**Classes:**
- `TestCacheFixtures` - Line 12
  - Test cache-related fixtures.
  - Methods: test_initialized_cache, test_cache_with_tools
- `TestProjectFixtures` - Line 35
  - Test project and file fixtures.
  - Methods: test_temp_project_with_files, test_sample_py_content, test_duplicate_files_similar
- `TestMCPToolFixtures` - Line 77
  - Test MCP tool access fixtures.
  - Methods: test_mcp_tools_accessor, test_mcp_tools_error_handling
- `TestComplexityFixtures` - Line 97
  - Test complexity analysis fixtures.
  - Methods: test_sample_complexity_thresholds, test_sample_function_code
- `TestCodeQualityFixtures` - Line 126
  - Test code quality and linting fixtures.
  - Methods: test_sample_linting_rule, test_sample_rule_templates
- `TestBackupFixtures` - Line 153
  - Test backup management fixtures.
  - Methods: test_backup_dir
- `TestCoverageFixtures` - Line 169
  - Test test coverage fixtures.
  - Methods: test_sample_test_paths
- `TestLanguageCodeFixtures` - Line 184
  - Test multi-language code fixtures.
  - Methods: test_sample_python_code, test_sample_typescript_code, test_sample_javascript_code, test_sample_java_code
- `TestSchemaFixtures` - Line 211
  - Test Schema.org fixtures.
  - Methods: test_sample_schema_types
- `TestDeduplicationFixtures` - Line 230
  - Test deduplication fixtures.
  - Methods: test_sample_deduplication_result
- `TestSubprocessFixtures` - Line 251
  - Test subprocess mocking fixtures.
  - Methods: test_mock_ast_grep_process
- `TestFixtureCombinations` - Line 263
  - Test combining multiple fixtures in realistic scenarios.
  - Methods: test_cache_with_project_files, test_tools_with_thresholds, test_backup_with_project

**Key Imports:** `pathlib`, `pytest`

### `test_deduplication_analysis.py` (python)

**Classes:**
- `TestVariationClassification` - Line 45
  - Tests for variation classification in duplicate code.
  - Methods: test_classify_variations_simple, test_classify_variations_complex, test_detect_conditional_variations, test_variation_severity_enum
- `TestParameterExtraction` - Line 90
  - Tests for parameter extraction from duplicate code.
  - Methods: test_identify_varying_identifiers, test_generate_parameter_name, test_infer_parameter_type, test_infer_single_value_type, test_infer_from_identifier_name (+2 more)
- `TestComplexityScoring` - Line 139
  - Tests for complexity scoring of duplicate code.
  - Methods: test_get_complexity_level_low, test_get_complexity_level_medium, test_get_complexity_level_high, test_complexity_boundaries

**Key Imports:** `ast_grep_mcp.features.deduplication`, `ast_grep_mcp.features.deduplication.analyzer`, `ast_grep_mcp.features.deduplication.generator`, `ast_grep_mcp.models.complexity`, `ast_grep_mcp.models.deduplication` (+2 more)

### `test_deduplication_detection.py` (python)

**Classes:**
- `TestDuplicationDetection` - Line 34
  - Tests for duplicate code detection.
  - Methods: test_calculate_similarity, test_normalize_code, test_generate_refactoring_suggestions
- `TestASTDiff` - Line 87
  - Tests for AST diff functionality.
  - Methods: test_build_diff_tree, test_build_nested_diff_tree, test_format_alignment_diff
- `TestDiffPreview` - Line 127
  - Tests for diff preview generation.
  - Methods: test_diff_preview_to_dict, test_generate_file_diff, test_generate_multi_file_diff, test_generate_diff_from_file_paths

**Key Imports:** `ast_grep_mcp.features.deduplication.diff`, `ast_grep_mcp.features.deduplication.recommendations`, `ast_grep_mcp.utils.text`, `os`, `sys` (+1 more)

### `test_deduplication_key_names.py` (python)

**Classes:**
- `TestOrchestratorKeyNames` - Line 26
  - Tests for consistent key names in orchestrator.
  - Methods: temp_project_dir, mock_detector_output, orchestrator_with_mock_detector, test_orchestrator_passes_duplication_groups_to_ranker, test_orchestrator_output_has_correct_keys (+1 more)
- `TestToolsKeyNames` - Line 160
  - Tests for consistent key names in tools module.
  - Methods: temp_project_dir, test_tool_handles_orchestrator_output_keys, test_tool_logs_with_correct_keys
- `TestScriptRecommendationHandling` - Line 207
  - Tests for recommendation dict/string handling in CLI script.
  - Methods: test_recommendation_as_dict, test_recommendation_as_string, test_recommendation_dict_without_text_key

**Key Imports:** `ast_grep_mcp.features.deduplication.analysis_orchestrator`, `ast_grep_mcp.features.deduplication.detector`, `ast_grep_mcp.features.deduplication.tools`, `pytest`, `tempfile` (+2 more)

### `test_documentation.py` (python)

**Classes:**
- `TestDataModels` - Line 20
  - Tests for documentation data models.
  - Methods: test_parameter_info_creation, test_function_signature_creation, test_generated_docstring_creation, test_api_route_creation, test_changelog_entry_creation (+1 more)
- `TestDocstringGenerator` - Line 119
  - Tests for docstring generation.
  - Methods: test_infer_description_from_name, test_infer_parameter_description, test_generate_google_docstring, test_generate_numpy_docstring, test_generate_sphinx_docstring (+2 more)
- `TestReadmeGenerator` - Line 313
  - Tests for README generation.
  - Methods: test_detect_package_manager, test_detect_language, test_generate_installation_section, test_generate_usage_section
- `TestApiDocsGenerator` - Line 394
  - Tests for API documentation generation.
  - Methods: test_express_route_parser, test_fastapi_route_parser, test_generate_markdown_docs, test_generate_openapi_spec
- `TestChangelogGenerator` - Line 527
  - Tests for changelog generation.
  - Methods: test_parse_conventional_commit
- `TestSyncChecker` - Line 563
  - Tests for documentation sync checking.
  - Methods: test_extract_docstring_params_google, test_extract_docstring_params_sphinx, test_extract_docstring_params_jsdoc, test_extract_docstring_return, test_check_docstring_sync_missing (+2 more)
- `TestToolsIntegration` - Line 720
  - Integration tests for documentation tools.
  - Methods: test_generate_docstrings_impl, test_generate_readme_sections_impl, test_sync_documentation_impl

**Key Imports:** `ast_grep_mcp.features.documentation.api_docs_generator`, `ast_grep_mcp.features.documentation.changelog_generator`, `ast_grep_mcp.features.documentation.docstring_generator`, `ast_grep_mcp.features.documentation.readme_generator`, `ast_grep_mcp.features.documentation.sync_checker` (+1 more)

### `test_enhanced_reporting.py` (python)

**Classes:**
- `TestFormatDiffWithColors` - Line 24
  - Tests for format_diff_with_colors function.
  - Methods: test_empty_diff, test_colors_additions, test_colors_deletions, test_colors_hunk_headers, test_colors_file_headers (+2 more)
- `TestGenerateBeforeAfterExample` - Line 88
  - Tests for generate_before_after_example function.
  - Methods: test_basic_example, test_line_numbers_in_before, test_line_numbers_in_after, test_raw_content_preserved, test_function_definition_generated (+3 more)
- `TestVisualizeComplexity` - Line 172
  - Tests for visualize_complexity function.
  - Methods: test_low_complexity, test_medium_complexity, test_high_complexity, test_bar_visualization, test_bar_colored_version (+4 more)
- `TestCreateEnhancedDuplicationResponse` - Line 242
  - Tests for create_enhanced_duplication_response function.
  - Methods: test_empty_candidates, test_single_candidate, test_multiple_candidates_sorted_by_priority, test_summary_statistics, test_global_recommendations_generated (+8 more)
- `TestIntegration` - Line 462
  - Integration tests combining multiple Phase 5 functions.
  - Methods: test_full_workflow, test_colored_output

**Key Imports:** `ast_grep_mcp.features.deduplication.reporting`, `ast_grep_mcp.utils.formatters`, `os`, `sys`

### `test_extract_function.py` (python)

**Classes:**
- `TestCodeSelectionAnalyzer` - Line 12
  - Tests for CodeSelectionAnalyzer.
  - Methods: test_analyze_python_simple_selection, test_detect_indentation, test_has_early_returns_python, test_has_exception_handling_python
- `TestFunctionExtractor` - Line 91
  - Tests for FunctionExtractor.
  - Methods: test_generate_function_name, test_generate_signature_python, test_generate_return_statement_python, test_generate_call_site_python
- `TestExtractFunctionTool` - Line 190
  - Integration tests for extract_function_tool.
  - Methods: test_extract_function_dry_run, test_extract_function_with_no_returns, test_extract_function_apply
- `TestJavaScriptExtraction` - Line 288
  - Tests for JavaScript/TypeScript extraction.
  - Methods: test_analyze_javascript_variables

**Functions:**
- `sample_python_code()` - Line 323
- `sample_typescript_code()` - Line 341

**Key Imports:** `ast_grep_mcp.features.refactoring.analyzer`, `ast_grep_mcp.features.refactoring.extractor`, `ast_grep_mcp.features.refactoring.tools`, `ast_grep_mcp.models.refactoring`, `pytest` (+0 more)

### `test_hybrid_similarity.py` (python)

**Classes:**
- `TestHybridSimilarityConfig` - Line 21
  - Tests for HybridSimilarityConfig validation.
  - Methods: test_default_config, test_custom_config, test_invalid_threshold_raises_error, test_invalid_weight_raises_error, test_weights_must_sum_to_one
- `TestHybridSimilarityResult` - Line 63
  - Tests for HybridSimilarityResult dataclass.
  - Methods: test_result_creation, test_result_to_dict, test_result_to_dict_with_none_ast
- `TestHybridSimilarity` - Line 118
  - Tests for HybridSimilarity calculator.
  - Methods: test_identical_code_high_similarity, test_similar_code_hybrid_verification, test_different_code_early_exit, test_empty_code_returns_zero, test_estimate_similarity_convenience_method (+1 more)
- `TestHybridSimilarityStages` - Line 233
  - Tests for individual stages of the hybrid pipeline.
  - Methods: test_stage1_minhash_threshold, test_stage2_ast_normalization, test_weighted_combination
- `TestHybridSimilarityNormalization` - Line 320
  - Tests for code normalization in AST comparison.
  - Methods: test_normalize_removes_comments, test_normalize_removes_js_comments, test_normalize_standardizes_indentation, test_normalize_skips_empty_lines
- `TestHybridSimilarityLargeCode` - Line 388
  - Tests for handling large code with simplified AST comparison.
  - Methods: test_large_code_uses_simplified_comparison, test_extract_structural_patterns
- `TestHybridSimilarityDiagnostics` - Line 423
  - Tests for diagnostic information in results.
  - Methods: test_token_count_reported, test_minhash_similarity_always_present
- `TestDetectorWithHybridMode` - Line 445
  - Integration tests for DuplicationDetector with hybrid mode.
  - Methods: test_detector_uses_hybrid_by_default, test_detector_hybrid_similarity, test_detector_detailed_similarity, test_detector_minhash_mode, test_detector_sequence_matcher_mode (+1 more)
- `TestHybridSimilarityPerformance` - Line 516
  - Performance characteristic tests.
  - Methods: test_early_exit_faster_than_full_pipeline

**Key Imports:** `ast_grep_mcp.features.deduplication.detector`, `ast_grep_mcp.features.deduplication.similarity`, `pytest`, `time` (+-1 more)

### `test_minhash_similarity.py` (python)

**Classes:**
- `TestMinHashSimilarity` - Line 16
  - Tests for MinHash similarity calculation.
  - Methods: test_identical_code_high_similarity, test_similar_code_moderate_similarity, test_different_code_low_similarity, test_empty_code_returns_zero, test_minhash_signature_caching (+1 more)
- `TestMinHashLSH` - Line 117
  - Tests for LSH-based candidate retrieval.
  - Methods: test_build_lsh_index, test_query_similar, test_find_all_similar_pairs
- `TestSimilarityConfig` - Line 191
  - Tests for similarity configuration.
  - Methods: test_default_config, test_custom_config
- `TestSimilarityResult` - Line 214
  - Tests for similarity result dataclass.
  - Methods: test_result_creation
- `TestEnhancedStructureHash` - Line 230
  - Tests for improved structure hash algorithm.
  - Methods: test_similar_structure_same_hash, test_different_call_patterns_different_hash, test_different_structure_different_hash, test_create_buckets, test_control_flow_detection
- `TestEnhancedStructureHashNodeSequence` - Line 349
  - Tests for AST-like node sequence extraction.
  - Methods: test_extract_node_sequence_basic, test_extract_node_sequence_order_preserved, test_extract_node_sequence_ignores_comments, test_extract_node_sequence_class_and_methods
- `TestEnhancedStructureHashComplexity` - Line 424
  - Tests for control flow complexity calculation.
  - Methods: test_complexity_simple_function, test_complexity_with_conditionals, test_complexity_with_loops, test_complexity_with_exception_handling
- `TestEnhancedStructureHashCallSignature` - Line 462
  - Tests for function call signature extraction.
  - Methods: test_call_signature_basic, test_call_signature_no_calls, test_call_signature_consistent, test_call_signature_filters_keywords
- `TestEnhancedStructureHashNestingDepth` - Line 528
  - Tests for nesting depth estimation.
  - Methods: test_nesting_depth_flat, test_nesting_depth_nested
- `TestEnhancedStructureHashLogarithmicBucket` - Line 557
  - Tests for logarithmic size bucketing.
  - Methods: test_logarithmic_bucket_small, test_logarithmic_bucket_medium, test_logarithmic_bucket_large, test_logarithmic_bucket_max
- `TestEnhancedStructureHashBucketDistribution` - Line 591
  - Tests for bucket distribution quality.
  - Methods: test_bucket_distribution_diverse_code
- `TestDetectorIntegration` - Line 650
  - Integration tests for detector with MinHash.
  - Methods: test_detector_uses_minhash_by_default, test_detector_can_use_sequence_matcher, test_detector_similarity_calculation, test_detector_similarity_with_sequence_matcher, test_detector_structure_hash
- `TestDetectorMinHashRegressions` - Line 713
  - Regression tests to prevent detector/MinHash integration issues.
  - Methods: test_detector_identical_code_high_similarity, test_detector_consistent_with_direct_minhash, test_detector_multiline_identical_code, test_detector_different_code_low_similarity, test_detector_empty_code_returns_zero (+1 more)
- `TestPerformanceCharacteristics` - Line 827
  - Tests to verify performance characteristics.
  - Methods: test_minhash_scales_linearly
- `TestSmallCodeFallback` - Line 858
  - Tests for SequenceMatcher fallback for small code snippets.
  - Methods: test_small_code_fallback_accuracy, test_large_code_uses_minhash, test_small_code_different_gets_low_similarity, test_fallback_can_be_disabled, test_small_code_threshold_configurable (+4 more)

**Key Imports:** `ast_grep_mcp.features.deduplication.detector`, `ast_grep_mcp.features.deduplication.similarity`, `time` (+-2 more)

### `test_orchestrator_optimizations.py` (python)

**Classes:**
- `TestComponentInstanceCaching` - Line 20
  - Tests for lazy component initialization optimization (1.2).
  - Methods: test_components_not_initialized_on_construction, test_detector_lazy_initialization, test_ranker_lazy_initialization, test_coverage_detector_lazy_initialization, test_recommendation_engine_lazy_initialization (+2 more)
- `TestInputValidation` - Line 122
  - Tests for input validation optimization (3.1).
  - Methods: temp_project_dir, test_invalid_project_path_not_exists, test_invalid_project_path_not_directory, test_invalid_min_similarity_too_low, test_invalid_min_similarity_too_high (+6 more)
- `TestNamingConsistency` - Line 272
  - Tests for naming consistency optimization (2.4).
  - Methods: test_result_structure_has_clear_naming, test_top_candidates_count_reflects_actual_count, test_savings_calculated_from_top_candidates_only, test_logging_uses_consistent_naming
- `TestParallelEnrichUtility` - Line 410
  - Tests for parallel execution utility optimization (1.3).
  - Methods: test_parallel_enrich_sequential_mode, test_parallel_enrich_parallel_mode, test_parallel_enrich_single_candidate_uses_sequential, test_parallel_enrich_error_handling_sequential, test_parallel_enrich_error_handling_parallel (+15 more)

**Key Imports:** `ast_grep_mcp.constants`, `ast_grep_mcp.features.deduplication.analysis_orchestrator`, `inspect`, `os`, `pathlib` (+4 more)

### `test_progress_callbacks.py` (python)

**Classes:**
- `TestProgressCallbacks` - Line 18
  - Tests for progress callback functionality (3.3).
  - Methods: temp_project_dir, orchestrator_with_mocks, test_progress_callback_is_called, test_progress_stages_in_order, test_progress_percentages_increase (+11 more)
- `TestProgressCallbackIntegration` - Line 322
  - Integration tests for progress callbacks with real workflow.
  - Methods: temp_project_dir, test_progress_percentage_distribution

**Key Imports:** `ast_grep_mcp.features.deduplication.analysis_orchestrator`, `pytest`, `tempfile`, `unittest.mock`

### `test_ranker.py` (python)

**Classes:**
- `TestDuplicationRanker` - Line 15
  - Tests for DuplicationRanker class.
  - Methods: ranker, sample_candidates, test_rank_all_candidates, test_rank_with_max_results, test_max_results_greater_than_candidates (+7 more)
- `TestEarlyExitPerformance` - Line 199
  - Tests to verify early exit optimization actually improves performance.
  - Methods: test_early_exit_processes_fewer_rank_assignments

**Key Imports:** `ast_grep_mcp.features.deduplication.ranker`, `pytest`

### `test_ranker_caching.py` (python)

**Classes:**
- `TestScoreCaching` - Line 15
  - Test score caching functionality in DuplicationRanker.
  - Methods: ranker_with_cache, ranker_without_cache, sample_candidate, test_cache_initialization, test_cache_key_generation_deterministic (+13 more)
- `TestCachePerformance` - Line 230
  - Test cache performance characteristics.
  - Methods: ranker, test_large_cache_performance, test_cache_hit_rate_with_duplicates
- `TestCacheEdgeCases` - Line 285
  - Test edge cases for score caching.
  - Methods: ranker, test_empty_candidates_list, test_candidate_with_empty_files_list, test_candidate_with_missing_optional_fields

**Key Imports:** `pytest`, `src.ast_grep_mcp.features.deduplication.ranker`, `unittest.mock`

### `test_rename_symbol.py` (python)

**Classes:**
- `TestSymbolRenamer` - Line 32
  - Tests for SymbolRenamer class.
  - Methods: test_find_symbol_references_simple, test_find_symbol_references_no_matches, test_build_scope_tree_python_simple, test_build_scope_tree_nested_functions, test_check_naming_conflicts_no_conflict (+5 more)
- `TestRenameCoordinator` - Line 271
  - Tests for RenameCoordinator class.
  - Methods: test_rename_symbol_dry_run, test_rename_symbol_no_references, test_rename_symbol_with_conflicts, test_rename_symbol_apply, test_rename_in_file_word_boundary (+1 more)
- `TestRenameSymbolTool` - Line 482
  - Tests for rename_symbol MCP tool.
  - Methods: test_rename_symbol_tool_dry_run, test_rename_symbol_tool_error_handling, test_rename_symbol_tool_with_file_filter
- `TestMultiFileRename` - Line 556
  - Integration tests for multi-file symbol renaming.
  - Methods: test_rename_across_multiple_files, test_rollback_on_failure

**Functions:**
- `python_renamer()` - Line 14
- `typescript_renamer()` - Line 21
- `python_coordinator()` - Line 27

**Key Imports:** `ast_grep_mcp.features.refactoring.rename_coordinator`, `ast_grep_mcp.features.refactoring.renamer`, `ast_grep_mcp.features.refactoring.tools`, `ast_grep_mcp.models.refactoring`, `pytest` (+1 more)

### `test_schema.py` (python)

**Classes:**
- `TestSchemaOrgClient` - Line 141
  - Tests for SchemaOrgClient class.
  - Methods: test_normalize_to_array, test_generate_example_value_text, test_generate_example_value_url, test_generate_example_value_date, test_generate_example_value_datetime (+13 more)
- `TestSchemaOrgTools` - Line 676
  - Tests for Schema.org MCP tools.
  - Methods: test_generate_entity_id_tool, test_validate_entity_id_tool
- `TestSchemaOrgClientHelpers` - Line 814
  - Tests for SchemaOrgClient helper methods.
  - Methods: test_extract_super_types, test_extract_super_types_multiple, test_find_sub_types, test_format_property
- `TestGetSchemaOrgClient` - Line 898
  - Tests for get_schema_org_client singleton.
  - Methods: test_get_schema_org_client_singleton, test_get_schema_org_client_creates_instance

**Key Imports:** `ast_grep_mcp.features.schema.client`, `httpx`, `pytest`, `unittest.mock`

### `test_schema_enhancement.py` (python)

**Classes:**
- `TestEnhancementRules` - Line 119
  - Tests for enhancement_rules.py functions.
  - Methods: test_get_property_priority_known_property, test_get_property_priority_unknown_property, test_get_property_priority_unknown_entity, test_get_rich_results_for_property, test_get_rich_results_for_property_unknown (+4 more)
- `TestGraphLoading` - Line 177
  - Tests for graph loading functions.
  - Methods: test_extract_entities_from_graph_array, test_extract_entities_from_single_entity, test_extract_entities_from_array, test_load_graph_from_file, test_load_graph_from_directory (+2 more)
- `TestEntityAnalysis` - Line 271
  - Tests for entity analysis functions.
  - Methods: test_extract_entity_type_string, test_extract_entity_type_array, test_extract_entity_type_missing, test_build_property_reason_critical, test_build_property_reason_high_no_rich_result
- `TestReferenceValidation` - Line 305
  - Tests for reference validation functions.
  - Methods: test_find_id_references_simple, test_find_id_references_nested, test_validate_entity_references_valid, test_validate_entity_references_broken
- `TestMissingEntityDetection` - Line 360
  - Tests for missing entity detection functions.
  - Methods: test_parse_suggestion_rule_has, test_parse_suggestion_rule_not_has, test_parse_suggestion_rule_count, test_parse_suggestion_rule_count_not_met, test_parse_suggestion_rule_complex_and (+5 more)
- `TestSEOScoring` - Line 449
  - Tests for SEO scoring functions.
  - Methods: test_calculate_entity_seo_score_perfect, test_calculate_entity_seo_score_critical_missing, test_calculate_entity_seo_score_with_validation_issues, test_calculate_overall_seo_score, test_build_priority_summary
- `TestGraphStructureValidation` - Line 525
  - Tests for graph structure validation.
  - Methods: test_validate_graph_structure_valid, test_validate_graph_structure_missing_context, test_validate_graph_structure_invalid_context, test_validate_graph_structure_empty_graph, test_validate_graph_structure_single_entity
- `TestOutputGeneration` - Line 570
  - Tests for output generation functions.
  - Methods: test_generate_enhanced_graph, test_generate_diff, test_generate_diff_no_changes
- `TestIntegration` - Line 672
  - Integration tests with mocked Schema.org client.

**Functions:**
- `simple_organization_graph() -> List[...]` - Line 48
- `complete_organization_graph() -> List[...]` - Line 61
- `sample_entity_enhancement() -> EntityEnhancement` - Line 87

**Key Imports:** `ast_grep_mcp.features.schema.enhancement_rules`, `ast_grep_mcp.features.schema.enhancement_service`, `ast_grep_mcp.models.schema_enhancement`, `json`, `os` (+5 more)

### `test_semantic_similarity.py` (python)

**Classes:**
- `TestSemanticSimilarityConfig` - Line 36
  - Tests for SemanticSimilarityConfig dataclass.
  - Methods: test_default_config, test_custom_config
- `TestSemanticSimilarityResult` - Line 68
  - Tests for SemanticSimilarityResult dataclass.
  - Methods: test_result_creation, test_result_to_dict
- `TestSemanticSimilarityAvailability` - Line 112
  - Tests for SemanticSimilarity.is_available() method.
  - Methods: test_is_available_without_transformers, test_is_available_caches_result
- `TestSemanticSimilarityInitialization` - Line 145
  - Tests for SemanticSimilarity initialization.
  - Methods: test_lazy_initialization
- `TestSemanticSimilarityMocked` - Line 159
  - Tests for SemanticSimilarity with mocked transformers.
  - Methods: mock_torch, mock_transformers, test_empty_input_returns_zero, test_config_applied, test_clear_cache (+1 more)
- `TestHybridSimilarityConfigSemantic` - Line 245
  - Tests for HybridSimilarityConfig semantic options.
  - Methods: test_default_semantic_disabled, test_enable_semantic_with_rebalanced_weights, test_semantic_weights_must_sum_to_one, test_invalid_semantic_weight, test_invalid_semantic_threshold
- `TestHybridSimilarityResultSemantic` - Line 295
  - Tests for HybridSimilarityResult semantic fields.
  - Methods: test_result_with_semantic, test_result_without_semantic, test_result_to_dict_with_semantic
- `TestHybridSimilarityThreeStage` - Line 364
  - Tests for three-stage hybrid pipeline.
  - Methods: test_semantic_disabled_by_default, test_semantic_skipped_when_unavailable, test_early_exit_skips_semantic, test_empty_input_returns_zero_with_semantic_fields
- `TestSemanticSimilarityDefaults` - Line 442
  - Tests for SemanticSimilarityDefaults constants.
  - Methods: test_default_values, test_weights_sum_to_one
- `TestSemanticSimilarityIntegration` - Line 474
  - Integration tests that require transformers and torch.
  - Methods: semantic, test_identical_code_high_similarity, test_similar_code_high_similarity, test_different_code_lower_similarity, test_embedding_caching (+1 more)
- `TestHybridThreeStageIntegration` - Line 551
  - Integration tests for three-stage hybrid pipeline.
  - Methods: hybrid_with_semantic, test_three_stage_similar_code, test_three_stage_result_format

**Key Imports:** `ast_grep_mcp.constants`, `ast_grep_mcp.features.deduplication.similarity`, `pytest`, `unittest.mock` (+-1 more)

### `test_standards_enforcement.py` (python)

**Classes:**
- `TestRuleViolationDataClass` - Line 53
  - Test RuleViolation data class.
  - Methods: test_instantiation_all_fields, test_instantiation_optional_fields_none, test_minimal_violation
- `TestRuleSetDataClass` - Line 119
  - Test RuleSet data class.
  - Methods: test_instantiation_all_fields, test_instantiation_without_priority, test_empty_rules_list
- `TestEnforcementResultDataClass` - Line 178
  - Test EnforcementResult data class.
  - Methods: test_instantiation_all_fields, test_empty_result
- `TestRuleExecutionContextDataClass` - Line 230
  - Test RuleExecutionContext data class.
  - Methods: test_instantiation_all_fields
- `TestRuleSetsConfiguration` - Line 256
  - Test RULE_SETS configuration.
  - Methods: test_rule_sets_exist, test_all_four_sets_exist, test_rule_sets_structure, test_recommended_set_priority, test_security_set_priority (+3 more)
- `TestTemplateToLintingRule` - Line 310
  - Test _template_to_linting_rule function.
  - Methods: test_basic_conversion, test_conversion_preserves_all_fields, test_constraints_is_none, test_conversion_multiple_templates
- `TestLoadCustomRules` - Line 371
  - Test _load_custom_rules function.
  - Methods: test_load_rules_from_directory, test_missing_directory, test_filter_by_language, test_handle_malformed_yaml, test_empty_directory (+1 more)
- `TestLoadRuleSet` - Line 478
  - Test _load_rule_set function.
  - Methods: test_load_recommended_rule_set, test_load_security_rule_set, test_load_performance_rule_set, test_load_style_rule_set, test_load_all_rule_set (+7 more)
- `TestParseMatchToViolation` - Line 590
  - Test _parse_match_to_violation function.
  - Methods: test_parse_complete_match, test_parse_match_without_metavars, test_parse_match_missing_range, test_parse_multiline_match
- `TestShouldExcludeFile` - Line 701
  - Test _should_exclude_file function.
  - Methods: test_exclude_node_modules, test_exclude_simple_glob, test_dont_exclude_non_matching, test_multiple_patterns, test_case_sensitivity (+5 more)
- `TestExecuteRule` - Line 776
  - Test _execute_rule function.
  - Methods: test_execute_single_rule, test_parse_violations_correctly, test_apply_file_exclusion, test_respect_max_violations, test_handle_execution_errors (+1 more)
- `TestExecuteRulesBatch` - Line 993
  - Test _execute_rules_batch function.
  - Methods: test_parallel_execution, test_combine_violations, test_early_termination_at_max_violations, test_handle_individual_failures
- `TestGroupViolationsByFile` - Line 1158
  - Test _group_violations_by_file function.
  - Methods: test_group_by_file, test_sort_by_line_number, test_empty_violations
- `TestGroupViolationsBySeverity` - Line 1260
  - Test _group_violations_by_severity function.
  - Methods: test_group_by_severity, test_all_severity_levels_present, test_empty_violations
- `TestGroupViolationsByRule` - Line 1338
  - Test _group_violations_by_rule function.
  - Methods: test_group_by_rule, test_empty_violations
- `TestFilterViolationsBySeverity` - Line 1392
  - Test _filter_violations_by_severity function.
  - Methods: test_filter_by_error, test_filter_by_warning, test_filter_by_info, test_handle_all_severity_levels
- `TestFormatViolationReport` - Line 1547
  - Test _format_violation_report function.
  - Methods: test_format_complete_report, test_summary_section, test_violations_breakdown, test_handle_empty_violations
- `TestEnforceStandardsTool` - Line 1675
  - Test enforce_standards MCP tool.
  - Methods: test_basic_scan_with_recommended_rules, test_security_rule_set, test_custom_rules_with_ids, test_invalid_severity_threshold, test_invalid_output_format (+10 more)

**Key Imports:** `ast_grep_mcp.features.quality.enforcer`, `ast_grep_mcp.features.quality.rules`, `ast_grep_mcp.models.standards`, `pytest`, `tempfile` (+1 more)

### `test_usage_tracking.py` (python)

**Classes:**
- `TestOperationPricing` - Line 32
  - Tests for operation cost calculation.
  - Methods: test_base_cost_only, test_cost_with_files, test_cost_with_lines, test_cost_with_matches, test_unknown_operation_uses_default (+1 more)
- `TestUsageLogEntry` - Line 81
  - Tests for UsageLogEntry model.
  - Methods: test_default_values, test_custom_values
- `TestUsageDatabase` - Line 113
  - Tests for SQLite usage database.
  - Methods: temp_db, test_database_creation, test_log_usage, test_log_failure, test_get_stats_empty (+3 more)
- `TestUsageAlerts` - Line 219
  - Tests for usage alert generation.
  - Methods: temp_db, test_no_alerts_when_under_threshold, test_daily_calls_warning, test_daily_calls_critical, test_failure_rate_alert (+1 more)
- `TestTrackOperation` - Line 300
  - Tests for track_operation context manager.
  - Methods: temp_db, test_successful_operation, test_failed_operation, test_response_time_tracking, test_cost_calculation
- `TestTrackUsageDecorator` - Line 360
  - Tests for @track_usage decorator.
  - Methods: temp_db, test_decorator_logs_success, test_decorator_logs_failure, test_decorator_extracts_metrics
- `TestFormatUsageReport` - Line 423
  - Tests for usage report formatting.
  - Methods: test_basic_report, test_report_with_tools
- `TestIntegrationWithDetector` - Line 463
  - Integration tests with DuplicationDetector.
  - Methods: temp_db, test_detector_logs_usage

**Key Imports:** `ast_grep_mcp.core.usage_tracking`, `ast_grep_mcp.features.deduplication.detector`, `datetime`, `os`, `pytest` (+3 more)

---
*Generated by Enhanced Schema Generator with schema.org markup*