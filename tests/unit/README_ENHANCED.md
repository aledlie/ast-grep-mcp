# unit

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareSourceCode",
  "name": "unit",
  "description": "Directory containing 60 code files with 325 classes and 74 functions",
  "programmingLanguage": [
    {
      "@type": "ComputerLanguage",
      "name": "Python"
    }
  ],
  "featureList": [
    "325 class definitions",
    "74 function definitions"
  ]
}
</script>

## Overview

This directory contains 60 code file(s) with extracted schemas.

## Files and Schemas

### `conftest.py` (python)

**Classes:**
- `MockFastMCP` - Line 19
  - Mock FastMCP class for testing.
  - Methods: __init__, tool, run, get
- `MCPNamespace` - Line 122

**Functions:**
- `mock_field() -> Any` - Line 42
- `mcp_main()` - Line 54
- `apply_deduplication_tool(mcp_main)` - Line 129
- `find_duplication_tool(mcp_main)` - Line 137
- `analyze_deduplication_candidates_tool(mcp_main)` - Line 145
- `benchmark_deduplication_tool(mcp_main)` - Line 153
- `rewrite_code_tool(mcp_main)` - Line 161
- `schema_client()` - Line 169
- `enforce_standards_tool(mcp_main)` - Line 177
- `list_backups_tool(mcp_main)` - Line 185
- ... and 20 more functions

**Key Imports:** `ast_grep_mcp.core`, `ast_grep_mcp.features.complexity.tools`, `ast_grep_mcp.features.deduplication.tools`, `ast_grep_mcp.features.documentation.tools`, `ast_grep_mcp.features.quality.tools` (+7 more)

### `test_analysis_config.py` (python)

**Classes:**
- `TestAnalysisConfigCreation` - Line 13
  - Test AnalysisConfig creation and initialization.
  - Methods: test_minimal_config, test_full_config
- `TestAnalysisConfigValidation` - Line 62
  - Test AnalysisConfig validation in __post_init__.
  - Methods: test_invalid_min_similarity_too_low, test_invalid_min_similarity_too_high, test_valid_min_similarity_boundaries, test_invalid_min_lines_zero, test_invalid_min_lines_negative (+4 more)
- `TestAnalysisConfigNormalization` - Line 114
  - Test AnalysisConfig normalization in __post_init__.
  - Methods: test_exclude_patterns_none_normalized_to_empty_list, test_exclude_patterns_empty_list_preserved, test_exclude_patterns_with_values_preserved
- `TestAnalysisConfigSerialization` - Line 135
  - Test AnalysisConfig to_dict() serialization.
  - Methods: test_to_dict_minimal_config, test_to_dict_full_config, test_to_dict_excludes_callback_function
- `TestAnalysisConfigEdgeCases` - Line 207
  - Test AnalysisConfig edge cases and boundary conditions.
  - Methods: test_very_high_max_candidates, test_very_high_max_workers, test_many_exclude_patterns, test_unicode_in_project_path, test_unicode_in_language
- `TestAnalysisConfigCallbackIntegration` - Line 238
  - Test AnalysisConfig integration with progress callbacks.
  - Methods: test_callback_invocation_tracking, test_no_callback_none_check

**Key Imports:** `pytest`, `src.ast_grep_mcp.features.deduplication.config`

### `test_analysis_orchestrator.py` (python)

**Classes:**
- `TestOrchestratorInitialization` - Line 32
  - Tests for orchestrator initialization and lazy loading.
  - Methods: test_init_creates_logger, test_lazy_detector_initialization, test_lazy_ranker_initialization, test_lazy_coverage_detector_initialization, test_lazy_recommendation_engine_initialization (+1 more)
- `TestInputValidation` - Line 81
  - Tests for input validation in analyze_candidates.
  - Methods: test_validate_nonexistent_project_path, test_validate_file_instead_of_directory, test_validate_min_similarity_below_zero, test_validate_min_similarity_above_one, test_validate_min_lines_zero (+4 more)
- `TestAnalysisWorkflow` - Line 128
  - Tests for the analysis workflow.
  - Methods: mock_orchestrator, test_analyze_candidates_with_config, test_analyze_candidates_legacy_interface, test_analyze_candidates_calls_detector, test_analyze_candidates_calls_ranker
- `TestProgressCallback` - Line 226
  - Tests for progress callback functionality.
  - Methods: _empty_orchestrator, test_progress_callback_is_called, test_progress_callback_receives_stage_names
- `TestEnrichmentMethods` - Line 275
  - Tests for candidate enrichment methods.
  - Methods: test_get_top_candidates_limits_results, test_get_top_candidates_handles_fewer_than_max, test_calculate_total_savings, test_calculate_total_savings_empty_list, test_build_analysis_metadata_from_config
- `TestEnrichAndSummarize` - Line 331
  - Tests for _enrich_and_summarize methods.
  - Methods: test_enrich_empty_candidates_returns_early, test_enrich_skips_coverage_when_disabled
- `TestTestCoverageBatch` - Line 373
  - Tests for batch test coverage processing.
  - Methods: test_add_test_coverage_batch_empty_candidates, test_add_test_coverage_batch_collects_unique_files, test_add_test_coverage_batch_distributes_results
- `TestRecommendations` - Line 428
  - Tests for recommendation generation.
  - Methods: test_enrich_with_recommendation
- `TestParallelProcessing` - Line 454
  - Tests for parallel processing functionality.
  - Methods: test_parallel_enrich_sequential_for_single_candidate, test_parallel_enrich_handles_exceptions
- `TestErrorHandling` - Line 504
  - Tests for error handling in enrichment.
  - Methods: test_handle_enrichment_error_logs_and_updates_candidate, test_handle_timeout_error
- `TestLegacyMethods` - Line 543
  - Tests for legacy interface methods to ensure backward compatibility.
  - Methods: test_build_analysis_metadata_legacy, test_enrich_and_summarize_legacy, test_add_test_coverage_legacy, test_enrich_with_test_coverage_single
- `TestUnsupportedLanguageWarning` - Line 633
  - Tests for unsupported language warning.
  - Methods: test_unsupported_language_logs_warning
- `TestParallelProcessingAdvanced` - Line 641
  - Advanced tests for parallel processing with ThreadPoolExecutor.
  - Methods: test_parallel_enrich_uses_threadpool_for_multiple_candidates, test_parallel_enrich_with_timeout
- `TestParallelErrorHandling` - Line 691
  - Tests for error handling in parallel processing path.
  - Methods: test_parallel_enrich_handles_exception_in_parallel_mode, test_process_completed_future_handles_timeout
- `TestBatchCoverageEdgeCases` - Line 746
  - Edge case tests for batch coverage processing.
  - Methods: test_add_test_coverage_batch_handles_empty_files_in_candidate, test_add_test_coverage_batch_handles_missing_files_key
- `TestAnalysisConfig` - Line 785
  - Tests for AnalysisConfig validation.
  - Methods: test_config_validates_min_similarity_range, test_config_validates_min_lines, test_config_validates_max_candidates, test_config_validates_max_workers, test_config_to_dict (+1 more)

**Functions:**
- `orchestrator()` - Line 27

**Key Imports:** `ast_grep_mcp.constants`, `ast_grep_mcp.features.deduplication.analysis_orchestrator`, `ast_grep_mcp.features.deduplication.config`, `concurrent.futures`, `pytest` (+3 more)

### `test_analysis_output_helpers.py` (python)

**Functions:**
- `test_count_by_key_counts_missing_and_empty_values() -> <ast.Constant object at 0x108046c70>` - Line 4
- `test_log_count_breakdown_respects_preferred_order() -> <ast.Constant object at 0x107f51400>` - Line 20
- `test_print_section_header_with_trailing_newline() -> <ast.Constant object at 0x107f519a0>` - Line 32

**Key Imports:** `scripts.analysis_output_helpers`

### `test_applicator_backup.py` (python)

**Classes:**
- `TestDeduplicationBackupManagerInit` - Line 30
  - Tests for DeduplicationBackupManager initialization.
  - Methods: test_init_sets_project_folder, test_init_sets_backup_base_dir, test_init_creates_logger
- `TestCreateBackup` - Line 56
  - Tests for create_backup method.
  - Methods: test_creates_backup_directory, test_returns_backup_id, test_copies_files_to_backup, test_preserves_directory_structure, test_saves_metadata_file (+4 more)
- `TestRollback` - Line 241
  - Tests for rollback method.
  - Methods: test_restores_files, test_returns_restored_files_list, test_raises_for_invalid_backup_id, test_skips_missing_backup_files, test_handles_restore_error
- `TestCleanupOldBackups` - Line 338
  - Tests for cleanup_old_backups method.
  - Methods: test_removes_old_backups, test_keeps_recent_backups, test_returns_zero_when_no_backup_dir, test_skips_non_directories, test_skips_dirs_without_metadata (+2 more)
- `TestGetFileHash` - Line 464
  - Tests for get_file_hash method.
  - Methods: test_returns_sha256_hash, test_returns_empty_string_on_error, test_handles_io_error
- `TestListBackups` - Line 506
  - Tests for list_backups method.
  - Methods: test_returns_empty_list_when_no_backups, test_returns_backup_metadata, test_sorts_by_timestamp_newest_first, test_skips_non_directories, test_skips_dirs_without_metadata (+1 more)
- `TestGenerateBackupId` - Line 598
  - Tests for _generate_backup_id helper.
  - Methods: test_returns_prefixed_id, test_no_collision_suffix_when_dir_absent
- `TestComputeFileHashes` - Line 624
  - Tests for _compute_file_hashes helper.
  - Methods: test_returns_hashes_for_existing_files, test_skips_nonexistent_files, test_mixed_existing_and_missing
- `TestCopyFileToBackup` - Line 665
  - Tests for shared copy_file_to_backup utility.
  - Methods: test_returns_none_for_missing_file, test_returns_entry_dict_with_correct_keys, test_falls_back_to_empty_hash_when_missing, test_omits_hash_key_when_hashes_none
- `TestRestoreSingleFile` - Line 726
  - Tests for _restore_single_file helper.
  - Methods: test_returns_path_on_success, test_returns_none_when_backup_missing, test_returns_none_on_copy_error
- `TestTryCleanupBackup` - Line 772
  - Tests for _try_cleanup_backup helper.
  - Methods: test_returns_false_for_no_metadata, test_returns_false_for_empty_timestamp, test_returns_false_for_malformed_timestamp, test_returns_false_for_recent_backup, test_returns_true_and_removes_old_backup
- `TestCreateBackupEdgeCases` - Line 845
  - Edge case tests for create_backup.
  - Methods: test_empty_file_list
- `TestRollbackEdgeCases` - Line 863
  - Edge case tests for rollback.
  - Methods: test_empty_files_in_metadata
- `TestCleanupMultiple` - Line 878
  - Tests for cleanup_old_backups with multiple backups.
  - Methods: test_removes_multiple_old_keeps_recent
- `TestIntegration` - Line 914
  - Integration tests for backup workflow.
  - Methods: test_full_backup_and_restore_workflow, test_backup_list_and_cleanup

**Key Imports:** `ast_grep_mcp.features.deduplication.applicator_backup`, `ast_grep_mcp.utils.backup`, `datetime`, `hashlib`, `json` (+6 more)

### `test_applicator_executor.py` (python)

**Classes:**
- `TestRefactoringExecutorInit` - Line 26
  - Tests for RefactoringExecutor initialization.
  - Methods: test_init_creates_logger
- `TestApplyChangesDryRun` - Line 35
  - Tests for apply_changes in dry run mode.
  - Methods: test_dry_run_returns_preview, test_dry_run_preview_contains_file_info
- `TestApplyChangesActual` - Line 79
  - Tests for apply_changes in actual (non-dry-run) mode.
  - Methods: test_creates_new_file, test_creates_directory_if_needed, test_updates_existing_file, test_adds_import_to_updated_file
- `TestCreateFiles` - Line 164
  - Tests for _create_files method.
  - Methods: test_creates_file_with_content, test_skips_empty_path, test_skips_empty_content, test_append_mode, test_write_mode_overwrites (+1 more)
- `TestUpdateFiles` - Line 248
  - Tests for _update_files method.
  - Methods: test_updates_file_content, test_skips_nonexistent_file, test_skips_empty_path, test_adds_import_statement, test_raises_on_read_error
- `TestAddImportToContent` - Line 325
  - Tests for _add_import_to_content method.
  - Methods: test_empty_import_returns_unchanged, test_existing_import_not_duplicated, test_python_import_added, test_javascript_import_added, test_typescript_import_added (+4 more)
- `TestGeneratePreview` - Line 394
  - Tests for _generate_preview method.
  - Methods: test_preview_empty_plan, test_preview_includes_create_files, test_preview_includes_update_files, test_preview_skips_empty_paths
- `TestApplyChangesErrorHandling` - Line 455
  - Tests for error handling in apply_changes.
  - Methods: test_propagates_exception
- `TestIntegration` - Line 477
  - Integration tests for RefactoringExecutor.
  - Methods: test_full_refactoring_workflow

**Key Imports:** `ast_grep_mcp.features.deduplication.applicator`, `ast_grep_mcp.features.deduplication.applicator_executor`, `os`, `pytest`, `tempfile` (+1 more)

### `test_apply_deduplication.py` (python)

**Classes:**
- `TestApplyDeduplication` - Line 33
  - Tests for apply_deduplication MCP tool.
  - Methods: test_tool_registered, test_dry_run_returns_correct_structure, test_apply_mode_returns_correct_structure, test_validates_project_folder_exists, test_validates_refactoring_plan_required (+1 more)
- `TestBackupIntegration` - Line 88
  - Tests for Phase 3.2 backup integration in apply_deduplication.
  - Methods: test_backup_created_on_apply, test_backup_metadata_contains_deduplication_info, test_backup_preserves_original_files, test_rollback_restores_original_content, test_multi_file_backup_and_rollback (+2 more)
- `TestPhase33MultiFileOrchestration` - Line 240
  - Tests for Phase 3.3 Multi-File Orchestration in apply_deduplication.
  - Methods: test_orchestration_creates_extracted_function_file, test_orchestration_creates_file_before_updates, test_orchestration_atomic_rollback_on_failure, test_orchestration_appends_to_existing_file, test_orchestration_handles_multiple_files_atomically
- `TestOrchestrationHelperFunctions` - Line 383
  - Tests for Phase 3.3 orchestration helper functions.
  - Methods: test_plan_file_modification_order_basic, test_add_import_to_content_python, test_add_import_to_content_python_no_existing_imports, test_add_import_to_content_typescript, test_add_import_to_content_skips_duplicate (+1 more)

**Key Imports:** `ast_grep_mcp.features.deduplication.applicator`, `ast_grep_mcp.features.rewrite.backup`, `json`, `os`, `pytest` (+1 more)

### `test_batch_coverage.py` (python)

**Classes:**
- `TestBatchCoverageOptimization` - Line 18
  - Tests for batch test coverage optimization.
  - Methods: temp_project, detector, test_find_all_test_files_python, test_find_all_test_files_empty_project, test_has_test_coverage_optimized_with_test (+5 more)
- `TestBatchVsSequentialEquivalence` - Line 143
  - Tests verifying batch and sequential methods produce same results.
  - Methods: detector, test_batch_sequential_equivalence
- `TestBatchCoverageIntegration` - Line 183
  - Integration tests for batch coverage in orchestrator.
  - Methods: mock_detector, test_orchestrator_uses_batch_method, test_orchestrator_deduplicates_files

**Key Imports:** `ast_grep_mcp.constants`, `ast_grep_mcp.features.deduplication.analysis_orchestrator`, `ast_grep_mcp.features.deduplication.coverage`, `os`, `pathlib` (+3 more)

### `test_cache_ttl_config.py` (python)

**Classes:**
- `TestCacheTTLConfig` - Line 7
  - Methods: test_cache_ttl_uses_ttl_seconds, test_cache_ttl_not_cleanup_interval, test_ttl_is_one_hour

**Key Imports:** `ast_grep_mcp.constants`, `ast_grep_mcp.core.config`

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
- `TestComplexityStorage` - Line 419
  - Test SQLite storage for complexity results.
  - Methods: test_storage_initialization, test_get_or_create_project, test_store_analysis_run, test_get_project_trends
- `TestAnalyzeFileComplexity` - Line 503
  - Test file complexity analysis.
  - Methods: test_analyze_empty_file, test_analyze_simple_function
- `TestEdgeCases` - Line 543
  - Test edge cases and boundary conditions.
  - Methods: test_empty_code, test_code_with_only_comments, test_multiline_string, test_very_long_function, test_tabs_vs_spaces
- `TestBenchmark` - Line 605
  - Performance benchmark tests for complexity analysis.
  - Methods: _generate_function, test_cyclomatic_1000_functions, test_cognitive_1000_functions, test_nesting_depth_1000_functions, test_all_metrics_1000_functions (+1 more)

**Key Imports:** `ast_grep_mcp.features.complexity.analyzer`, `ast_grep_mcp.features.complexity.metrics`, `ast_grep_mcp.features.complexity.storage`, `ast_grep_mcp.models.complexity`, `ast_grep_mcp.utils.console_logger` (+6 more)

### `test_config_validation_helpers.py` (python)

**Classes:**
- `TestValidateWeightBounds` - Line 8
  - Test _validate_weight_bounds data-driven validation.
  - Methods: test_valid_config_passes, test_negative_minhash_weight, test_ast_weight_above_one, test_semantic_stage_threshold_negative
- `TestValidateWeightSum` - Line 46
  - Test _validate_weight_sum for 2-stage and 3-stage modes.
  - Methods: test_two_stage_valid_sum, test_two_stage_invalid_sum, test_three_stage_valid_sum, test_three_stage_invalid_sum
- `TestApplySemanticRebalance` - Line 80
  - Test _apply_semantic_rebalance_if_needed preserves or rebalances.
  - Methods: test_rebalance_on_legacy_defaults_with_semantic, test_no_rebalance_when_custom_weights

**Key Imports:** `ast_grep_mcp.features.deduplication.similarity`, `pytest`

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

### `test_coverage_detector.py` (python)

**Classes:**
- `TestHelperFunctions` - Line 26
  - Tests for helper pattern functions.
  - Methods: test_get_javascript_patterns, test_get_ruby_patterns
- `TestCoverageDetectorInit` - Line 47
  - Tests for CoverageDetector initialization.
  - Methods: test_init_creates_logger
- `TestFindTestFilePatterns` - Line 56
  - Tests for find_test_file_patterns method.
  - Methods: test_python_patterns, test_javascript_patterns, test_js_shorthand_patterns, test_typescript_patterns, test_ts_shorthand_patterns (+12 more)
- `TestGetPotentialTestPaths` - Line 192
  - Tests for _get_potential_test_paths method.
  - Methods: test_python_potential_paths, test_javascript_potential_paths, test_typescript_potential_paths, test_tsx_potential_paths, test_java_potential_paths (+3 more)
- `TestReadFileContent` - Line 291
  - Tests for _read_file_content method.
  - Methods: test_read_existing_file, test_read_nonexistent_file, test_read_file_with_encoding_errors
- `TestCheckImportPatterns` - Line 334
  - Tests for _check_import_patterns method.
  - Methods: test_matching_pattern, test_no_matching_pattern, test_case_insensitive_matching
- `TestCheckGoSameDirectory` - Line 362
  - Tests for _check_go_same_directory method.
  - Methods: test_same_directory, test_different_directory
- `TestCheckTestFileReferencesSource` - Line 382
  - Tests for _check_test_file_references_source method.
  - Methods: test_python_import_detected, test_javascript_import_detected, test_javascript_require_detected, test_go_same_directory_detected, test_go_import_detected (+5 more)
- `TestHasTestCoverage` - Line 514
  - Tests for has_test_coverage method.
  - Methods: test_coverage_found_by_potential_path, test_no_coverage_found, test_coverage_found_by_reference
- `TestFindAllTestFiles` - Line 572
  - Tests for _find_all_test_files method.
  - Methods: test_finds_test_files, test_returns_set
- `TestHasTestCoverageOptimized` - Line 605
  - Tests for _has_test_coverage_optimized method.
  - Methods: test_finds_coverage_in_precomputed_set, test_finds_coverage_by_reference
- `TestGetTestCoverageForFiles` - Line 652
  - Tests for get_test_coverage_for_files method.
  - Methods: test_returns_coverage_map
- `TestGetTestCoverageForFilesBatch` - Line 683
  - Tests for get_test_coverage_for_files_batch method.
  - Methods: test_empty_file_list, test_sequential_processing, test_parallel_processing
- `TestProcessFileCoverage` - Line 729
  - Tests for _process_file_coverage method.
  - Methods: test_handles_exception
- `TestProcessParallelBatch` - Line 743
  - Tests for _process_parallel_batch method.
  - Methods: test_parallel_batch_processing
- `TestProcessSequentialBatch` - Line 765
  - Tests for _process_sequential_batch method.
  - Methods: test_sequential_batch_processing
- `TestGetFutureResult` - Line 787
  - Tests for _get_future_result method.
  - Methods: test_successful_future, test_failed_future
- `TestLogBatchResults` - Line 813
  - Tests for _log_batch_results method.
  - Methods: test_logs_results
- `TestClassMethods` - Line 824
  - Tests for CoverageDetector class methods (formerly module-level functions).
  - Methods: test_find_test_file_patterns, test_has_test_coverage, test_get_test_coverage_for_files, test_check_test_file_references_source, test_get_potential_test_paths
- `TestEdgeCases` - Line 884
  - Tests for edge cases and error handling.
  - Methods: test_glob_exception_handling, test_find_all_test_files_glob_exception, test_read_file_io_error, test_parallel_batch_with_covered_files, test_sequential_batch_with_covered_files

**Key Imports:** `ast_grep_mcp.features.deduplication.coverage`, `concurrent.futures`, `os`, `tempfile`, `unittest.mock`

### `test_deduplication_analysis.py` (python)

**Classes:**
- `TestVariationClassification` - Line 40
  - Tests for variation classification in duplicate code.
  - Methods: test_classify_variations_simple, test_classify_variations_complex, test_detect_conditional_variations, test_variation_severity_enum
- `TestParameterExtraction` - Line 85
  - Tests for parameter extraction from duplicate code.
  - Methods: test_identify_varying_identifiers, test_generate_parameter_name, test_infer_parameter_type, test_infer_single_value_type, test_infer_from_identifier_name (+2 more)
- `TestComplexityScoring` - Line 134
  - Tests for complexity scoring of duplicate code.
  - Methods: test_get_complexity_level_low, test_get_complexity_level_medium, test_get_complexity_level_high, test_complexity_boundaries

**Key Imports:** `ast_grep_mcp.features.deduplication.analyzer`, `ast_grep_mcp.features.deduplication.generator`, `ast_grep_mcp.models.complexity`, `ast_grep_mcp.models.deduplication`, `os` (+1 more)

### `test_deduplication_detection.py` (python)

**Classes:**
- `TestDuplicationDetection` - Line 35
  - Tests for duplicate code detection.
  - Methods: test_calculate_similarity, test_normalize_code, test_generate_refactoring_suggestions
- `TestASTDiff` - Line 80
  - Tests for AST diff functionality.
  - Methods: test_build_diff_tree, test_build_nested_diff_tree, test_format_alignment_diff, test_format_alignment_diff_empty_old, test_format_alignment_diff_empty_new (+1 more)
- `TestDiffPreview` - Line 148
  - Tests for diff preview generation.
  - Methods: test_diff_preview_to_dict, test_generate_file_diff, test_generate_multi_file_diff, test_generate_diff_from_file_paths
- `TestEnsureTrailingNewline` - Line 196
  - Unit tests for _ensure_trailing_newline (in-place mutation helper).
  - Methods: test_empty_list_unchanged, test_single_line_without_newline_gets_appended, test_single_line_already_has_newline_unchanged, test_multi_line_last_without_newline, test_multi_line_last_already_has_newline (+1 more)

**Key Imports:** `ast_grep_mcp.features.deduplication.diff`, `ast_grep_mcp.features.deduplication.recommendations`, `ast_grep_mcp.utils.text`, `os`, `sys` (+1 more)

### `test_deduplication_key_names.py` (python)

**Classes:**
- `TestOrchestratorKeyNames` - Line 26
  - Tests for consistent key names in orchestrator.
  - Methods: temp_project_dir, mock_detector_output, orchestrator_with_mock_detector, test_orchestrator_passes_duplication_groups_to_ranker, test_orchestrator_output_has_correct_keys (+1 more)
- `TestToolsKeyNames` - Line 158
  - Tests for consistent key names in tools module.
  - Methods: temp_project_dir, test_tool_handles_orchestrator_output_keys, test_tool_logs_with_correct_keys
- `TestScriptRecommendationHandling` - Line 205
  - Tests for recommendation dict/string handling in CLI script.
  - Methods: test_recommendation_as_dict, test_recommendation_as_string, test_recommendation_dict_without_text_key

**Key Imports:** `ast_grep_mcp.features.deduplication.analysis_orchestrator`, `ast_grep_mcp.features.deduplication.detector`, `ast_grep_mcp.features.deduplication.tools`, `pytest`, `tempfile` (+2 more)

### `test_develop_pattern.py` (python)

**Classes:**
- `TestExtractIdentifiers` - Line 19
  - Tests for identifier extraction.
  - Methods: test_extract_javascript_identifiers, test_extract_python_identifiers, test_preserve_order, test_deduplicate
- `TestExtractLiterals` - Line 55
  - Tests for literal extraction.
  - Methods: test_extract_string_literals, test_extract_number_literals, test_extract_template_literals
- `TestGenerateGeneralizedPattern` - Line 79
  - Tests for generalized pattern generation.
  - Methods: test_replace_identifiers, test_replace_literals, test_limit_replacements
- `TestGeneratePatternSuggestions` - Line 109
  - Tests for pattern suggestion generation.
  - Methods: test_generates_exact_suggestion, test_generates_generalized_suggestion, test_generates_structural_suggestion
- `TestGenerateRefinementSteps` - Line 167
  - Tests for refinement step generation.
  - Methods: test_matching_pattern_steps, test_non_matching_pattern_steps
- `TestGenerateYamlTemplate` - Line 207
  - Tests for YAML template generation.
  - Methods: test_basic_template, test_complex_template_has_suggestions
- `TestDevelopPatternImpl` - Line 242
  - Integration tests for develop_pattern_impl.
  - Methods: test_simple_javascript_code, test_simple_python_code, test_function_declaration, test_provides_yaml_template, test_provides_next_steps (+4 more)
- `TestPatternSuggestion` - Line 348
  - Tests for PatternSuggestion model.
  - Methods: test_to_dict
- `TestCodeAnalysis` - Line 368
  - Tests for CodeAnalysis model.
  - Methods: test_to_dict

**Key Imports:** `ast_grep_mcp.features.search.service`, `ast_grep_mcp.models.pattern_develop`

### `test_docs_and_rule_builder.py` (python)

**Classes:**
- `TestGetDocs` - Line 16
  - Tests for the get_docs function.
  - Methods: test_get_pattern_docs, test_get_rules_docs, test_get_relational_docs, test_get_metavariables_docs, test_get_workflow_docs (+4 more)
- `TestBuildRule` - Line 101
  - Tests for the build_rule_impl function.
  - Methods: test_build_simple_rule, test_build_rule_with_custom_id, test_build_rule_with_inside_pattern, test_build_rule_with_inside_kind, test_build_rule_with_has (+11 more)
- `TestGetPatternExamples` - Line 257
  - Tests for the get_pattern_examples function.
  - Methods: test_get_javascript_patterns, test_get_python_patterns, test_get_go_patterns, test_get_rust_patterns, test_get_typescript_patterns (+25 more)

**Key Imports:** `ast_grep_mcp.features.search.docs`, `ast_grep_mcp.features.search.service`, `yaml`

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
- `TestChangelogHelpers` - Line 527
  - Tests for changelog generator helper functions.
  - Methods: test_resolve_version_ref_head, test_resolve_version_ref_vprefixed_tag, test_resolve_version_ref_bare_ref, test_resolve_version_ref_fallback_head, test_get_first_commit_success (+12 more)
- `TestChangelogGenerator` - Line 761
  - Tests for changelog generation.
  - Methods: test_parse_conventional_commit
- `TestSyncChecker` - Line 797
  - Tests for documentation sync checking.
  - Methods: test_extract_docstring_params_google, test_extract_docstring_params_sphinx, test_extract_docstring_params_jsdoc, test_extract_docstring_return, test_check_docstring_sync_missing (+2 more)
- `TestToolsIntegration` - Line 954
  - Integration tests for documentation tools.
  - Methods: test_generate_docstrings_impl, test_generate_readme_sections_impl, test_sync_documentation_impl

**Key Imports:** `ast_grep_mcp.features.documentation.api_docs_generator`, `ast_grep_mcp.features.documentation.changelog_generator`, `ast_grep_mcp.features.documentation.docstring_generator`, `ast_grep_mcp.features.documentation.readme_generator`, `ast_grep_mcp.features.documentation.sync_checker` (+2 more)

### `test_duplication_detector.py` (python)

**Classes:**
- `TestDuplicationDetectorInit` - Line 28
  - Tests for DuplicationDetector initialization.
  - Methods: test_init_default_values, test_init_with_language, test_init_with_minhash_mode, test_init_with_sequence_matcher_mode, test_init_legacy_use_minhash_false (+1 more)
- `TestValidateParameters` - Line 76
  - Tests for _validate_parameters method.
  - Methods: test_valid_parameters, test_min_similarity_below_zero, test_min_similarity_above_one, test_min_lines_below_one, test_max_constructs_negative (+1 more)
- `TestGetConstructPattern` - Line 122
  - Tests for _get_construct_pattern method.
  - Methods: test_python_function_pattern, test_python_class_pattern, test_javascript_function_pattern, test_typescript_function_pattern, test_javascript_arrow_function_pattern (+7 more)
- `TestCalculateSimilarity` - Line 222
  - Tests for calculate_similarity method.
  - Methods: test_empty_code_returns_zero, test_identical_code_high_similarity, test_different_code_low_similarity, test_hybrid_mode_uses_hybrid, test_minhash_mode_uses_minhash (+1 more)
- `TestCalculateSimilarityPrecise` - Line 289
  - Tests for calculate_similarity_precise method.
  - Methods: test_empty_code_returns_zero, test_identical_code_returns_one
- `TestCalculateSimilarityDetailed` - Line 308
  - Tests for calculate_similarity_detailed method.
  - Methods: test_returns_hybrid_result
- `TestNormalizeCode` - Line 322
  - Tests for _normalize_code method.
  - Methods: test_removes_empty_lines, test_strips_trailing_whitespace, test_normalizes_indentation
- `TestGroupDuplicates` - Line 355
  - Tests for group_duplicates method.
  - Methods: test_empty_matches_returns_empty, test_filters_by_min_lines, test_groups_similar_code
- `TestCreateHashBuckets` - Line 396
  - Tests for _create_hash_buckets method.
  - Methods: test_creates_buckets
- `TestCalculateStructureHash` - Line 416
  - Tests for _calculate_structure_hash method.
  - Methods: test_returns_integer, test_similar_code_same_bucket
- `TestFindSimilarInBucket` - Line 441
  - Tests for _find_similar_in_bucket method.
  - Methods: test_finds_similar_items, test_skips_dissimilar_items
- `TestItemHelpers` - Line 473
  - Tests for item helper methods.
  - Methods: test_get_item_key, test_items_equal_same_items, test_items_equal_different_items
- `TestMergeOverlappingGroups` - Line 504
  - Tests for _merge_overlapping_groups method.
  - Methods: test_empty_groups, test_merges_overlapping_groups, test_keeps_separate_groups
- `TestBuildItemToGroupsMap` - Line 556
  - Tests for _build_item_to_groups_map method.
  - Methods: test_builds_mapping
- `TestAddUniqueItems` - Line 574
  - Tests for _add_unique_items method.
  - Methods: test_adds_unique_items, test_skips_duplicates
- `TestGenerateRefactoringSuggestions` - Line 604
  - Tests for generate_refactoring_suggestions method.
  - Methods: test_empty_groups_returns_empty, test_single_item_groups_skipped, test_generates_suggestions
- `TestDetermineRefactoringStrategy` - Line 645
  - Tests for _determine_refactoring_strategy method.
  - Methods: test_small_function_extract_utility, test_large_function_extract_module, test_class_extract_base_class, test_method_extract_method
- `TestCalculateStatistics` - Line 692
  - Tests for _calculate_statistics method.
  - Methods: test_calculates_statistics
- `TestEmptyResult` - Line 711
  - Tests for _empty_result method.
  - Methods: test_returns_empty_result_structure
- `TestFormatResult` - Line 727
  - Tests for _format_result method.
  - Methods: test_formats_result, test_formats_group_instances
- `TestFindDuplication` - Line 774
  - Tests for find_duplication method.
  - Methods: test_empty_project_returns_empty_result, test_filters_excluded_patterns, test_propagates_exceptions
- `TestProcessGroupConnections` - Line 821
  - Tests for _process_group_connections method.
  - Methods: test_processes_connections
- `TestEdgeCases` - Line 846
  - Tests for edge cases to improve coverage.
  - Methods: test_javascript_unknown_construct_default, test_group_duplicates_all_below_min_lines, test_find_similar_in_bucket_skips_used_items, test_find_constructs_logs_limit_reached, test_find_similar_in_bucket_inner_loop_continue
- `TestTrivialConstructorFilter` - Line 940
  - Tests for _is_trivial_constructor_group.
  - Methods: test_short_init_detected, test_long_init_not_filtered, test_non_init_not_filtered, test_mixed_init_and_regular, test_js_constructor (+1 more)
- `TestDelegationWrapperFilter` - Line 988
  - Tests for _is_delegation_wrapper_group.
  - Methods: test_thin_wrapper_detected, test_substantial_body_not_filtered, test_super_call_wrapper, test_chained_attribute_call_detected, test_empty_group_returns_false
- `TestParallelFormatterFilter` - Line 1027
  - Tests for _is_parallel_formatter_group.
  - Methods: test_parallel_to_formatters_detected, test_same_name_not_flagged, test_non_formatter_not_flagged
- `TestMinSavingsFilter` - Line 1056
  - Tests for _meets_min_savings.
  - Methods: test_high_savings_passes, test_low_savings_filtered, test_many_copies_increase_savings, test_empty_group, test_variable_length_members_use_sum_minus_min (+1 more)
- `TestApplyPrecisionFilters` - Line 1106
  - Integration test for _apply_precision_filters combining all filters.
  - Methods: test_all_false_positive_patterns_removed, test_legitimate_duplicates_preserved

**Functions:**
- `_make_match(code, file, line) -> Dict[...]` - Line 935

**Key Imports:** `ast_grep_mcp.constants`, `ast_grep_mcp.features.deduplication.detector`, `pytest`, `tempfile`, `typing` (+1 more)

### `test_enhanced_reporting.py` (python)

**Classes:**
- `TestFormatDiffWithColors` - Line 26
  - Tests for format_diff_with_colors function.
  - Methods: test_empty_diff, test_colors_additions, test_colors_deletions, test_colors_hunk_headers, test_colors_file_headers (+2 more)
- `TestGenerateBeforeAfterExample` - Line 90
  - Tests for generate_before_after_example function.
  - Methods: test_basic_example, test_line_numbers_in_before, test_line_numbers_in_after, test_raw_content_preserved, test_function_definition_generated (+3 more)
- `TestVisualizeComplexity` - Line 174
  - Tests for visualize_complexity function.
  - Methods: test_low_complexity, test_medium_complexity, test_high_complexity, test_bar_visualization, test_bar_colored_version (+4 more)
- `TestCreateEnhancedDuplicationResponse` - Line 244
  - Tests for create_enhanced_duplication_response function.
  - Methods: test_empty_candidates, test_single_candidate, test_multiple_candidates_sorted_by_priority, test_summary_statistics, test_global_recommendations_generated (+8 more)
- `TestIntegration` - Line 445
  - Integration tests combining multiple Phase 5 functions.
  - Methods: test_full_workflow, test_colored_output

**Key Imports:** `ast_grep_mcp.features.deduplication.reporting`, `ast_grep_mcp.utils.formatters`, `os`, `sys`

### `test_extract_function.py` (python)

**Classes:**
- `TestCodeSelectionAnalyzer` - Line 11
  - Tests for CodeSelectionAnalyzer.
  - Methods: test_analyze_python_simple_selection, test_detect_indentation, test_has_early_returns_python, test_has_exception_handling_python
- `TestFunctionExtractor` - Line 90
  - Tests for FunctionExtractor.
  - Methods: test_generate_function_name, test_generate_signature_python, test_generate_return_statement_python, test_generate_call_site_python
- `TestExtractFunctionTool` - Line 189
  - Integration tests for extract_function_tool.
  - Methods: test_extract_function_dry_run, test_extract_function_with_no_returns, test_extract_function_apply
- `TestJavaScriptExtraction` - Line 286
  - Tests for JavaScript/TypeScript extraction.
  - Methods: test_analyze_javascript_variables
- `TestProcessScanLine` - Line 356
  - Unit tests for FunctionExtractor._process_scan_line and _scan_imports.
  - Methods: setup_method, test_skip_blank_line, test_skip_comment_line, test_import_start_single_line, test_from_import_single_line (+10 more)

**Functions:**
- `sample_python_code()` - Line 321
- `sample_typescript_code()` - Line 339

**Key Imports:** `ast_grep_mcp.features.refactoring.analyzer`, `ast_grep_mcp.features.refactoring.extractor`, `ast_grep_mcp.features.refactoring.tools`, `ast_grep_mcp.models.refactoring`, `pytest` (+0 more)

### `test_fix_migration_errors.py` (python)

**Functions:**
- `_write_file(path, content) -> <ast.Constant object at 0x107c9d4c0>` - Line 7
- `test_find_orphaned_import_ranges_detects_orphan_block() -> <ast.Constant object at 0x107c9d460>` - Line 11
- `test_fix_file_removes_orphaned_block(tmp_path) -> <ast.Constant object at 0x107cacd60>` - Line 25
- `test_fix_file_no_change_without_orphan(tmp_path) -> <ast.Constant object at 0x107c9b880>` - Line 47

**Key Imports:** `pathlib`, `scripts.fix_migration_errors`, `textwrap`

### `test_fixer_list_metavars.py` (python)

**Classes:**
- `TestApplyFixPatternListMetavars` - Line 6
  - Test that list values from $$$ multi-captures are joined.
  - Methods: test_string_metavar, test_list_metavar_joined_with_space, test_empty_list_metavar, test_single_item_list, test_mixed_string_and_list_metavars

**Key Imports:** `ast_grep_mcp.features.quality.fixer`

### `test_flask_parser_helpers.py` (python)

**Classes:**
- `TestParseDecoratorMatch` - Line 8
  - Methods: _match, test_simple_route, test_route_with_methods, test_blueprint_route
- `TestFindNextHandlerName` - Line 35
  - Methods: test_finds_def_on_next_line, test_skips_decorators, test_returns_unknown_when_no_def, test_returns_unknown_at_eof
- `TestBuildRoutesForMethods` - Line 55
  - Methods: test_single_method, test_multiple_methods, test_path_params_extracted

**Key Imports:** `ast_grep_mcp.features.documentation.api_docs_generator`, `re`

### `test_hybrid_similarity.py` (python)

**Classes:**
- `TestHybridSimilarityConfig` - Line 25
  - Tests for HybridSimilarityConfig validation.
  - Methods: test_default_config, test_custom_config, test_invalid_threshold_raises_error, test_invalid_weight_raises_error, test_weights_must_sum_to_one
- `TestHybridSimilarityResult` - Line 67
  - Tests for HybridSimilarityResult dataclass.
  - Methods: test_result_creation, test_result_to_dict, test_result_to_dict_with_none_ast
- `TestHybridSimilarity` - Line 122
  - Tests for HybridSimilarity calculator.
  - Methods: test_identical_code_high_similarity, test_similar_code_hybrid_verification, test_different_code_early_exit, test_empty_code_returns_zero, test_estimate_similarity_convenience_method (+1 more)
- `TestHybridSimilarityStages` - Line 237
  - Tests for individual stages of the hybrid pipeline.
  - Methods: test_stage1_minhash_threshold, test_stage2_ast_normalization, test_weighted_combination
- `TestHybridSimilarityNormalization` - Line 324
  - Tests for code normalization in AST comparison.
  - Methods: test_normalize_removes_comments, test_normalize_removes_js_comments, test_normalize_standardizes_indentation, test_normalize_skips_empty_lines
- `TestHybridSimilarityLargeCode` - Line 392
  - Tests for handling large code with simplified AST comparison.
  - Methods: test_large_code_uses_simplified_comparison, test_extract_structural_patterns
- `TestHybridSimilarityDiagnostics` - Line 427
  - Tests for diagnostic information in results.
  - Methods: test_token_count_reported, test_minhash_similarity_always_present
- `TestDetectorWithHybridMode` - Line 449
  - Integration tests for DuplicationDetector with hybrid mode.
  - Methods: test_detector_uses_hybrid_by_default, test_detector_hybrid_similarity, test_detector_detailed_similarity, test_detector_minhash_mode, test_detector_sequence_matcher_mode (+1 more)
- `TestHybridSimilarityPerformance` - Line 520
  - Performance characteristic tests.
  - Methods: test_early_exit_faster_than_full_pipeline

**Key Imports:** `ast_grep_mcp.constants`, `ast_grep_mcp.features.deduplication.detector`, `ast_grep_mcp.features.deduplication.similarity`, `pytest`, `time` (+0 more)

### `test_impact_call_site_helpers.py` (python)

**Classes:**
- `TestToCallSiteRecord` - Line 10
  - Methods: test_absolute_path_kept, test_relative_path_joined, test_context_truncated, test_missing_range_defaults
- `TestSearchCallSitesForName` - Line 51
  - Methods: _make_analyzer, test_filters_exclude_files, test_empty_on_nonzero_return, test_empty_on_no_stdout

**Key Imports:** `ast_grep_mcp.features.deduplication.impact`, `json`, `os`, `unittest.mock`

### `test_import_helpers.py` (python)

**Functions:**
- `test_scan_import_state_detects_existing_import_and_last_index() -> <ast.Constant object at 0x107c99280>` - Line 6
- `test_compute_import_insert_index_handles_shebang_and_multiline_docstring() -> <ast.Constant object at 0x107c99c10>` - Line 21
- `test_ensure_import_present_inserts_after_last_import() -> <ast.Constant object at 0x107c99790>` - Line 33
- `test_ensure_import_present_top_insert_adds_blank_line() -> <ast.Constant object at 0x107cd83a0>` - Line 47
- `test_ensure_import_present_blank_line_only_when_needed() -> <ast.Constant object at 0x107cd8760>` - Line 60

**Key Imports:** `scripts.import_helpers`

### `test_logging_handle.py` (python)

**Classes:**
- `TestConfigureLoggingFileHandle` - Line 23
  - Test that file handles are properly managed across calls.
  - Methods: test_stderr_default_no_file_handle, test_file_log_creates_handle, test_repeated_calls_close_previous_handle, test_switch_from_file_to_stderr_keeps_handle

**Functions:**
- `_reset_logging()` - Line 14

**Key Imports:** `ast_grep_mcp.core.logging`, `pathlib`, `pytest`, `structlog`, `tempfile` (+0 more)

### `test_migrate_print_to_logger.py` (python)

**Functions:**
- `_write_file(path, content) -> <ast.Constant object at 0x10807e880>` - Line 7
- `test_migrate_file_dry_run_keeps_original_content(tmp_path) -> <ast.Constant object at 0x1080a1400>` - Line 11
- `test_migrate_file_creates_backup_and_writes_changes(tmp_path) -> <ast.Constant object at 0x10818be50>` - Line 30
- `test_import_inserted_after_last_import(tmp_path) -> <ast.Constant object at 0x108037970>` - Line 51
- `test_import_inserted_after_shebang_and_docstring(tmp_path) -> <ast.Constant object at 0x1081a4730>` - Line 73
- `test_migrate_file_replaces_multiple_statements(tmp_path) -> <ast.Constant object at 0x10805a610>` - Line 95

**Key Imports:** `pathlib`, `scripts.migrate_print_to_logger`, `textwrap`

### `test_migration_common.py` (python)

**Functions:**
- `test_remove_line_ranges_removes_and_merges_overlaps() -> <ast.Constant object at 0x107f31a60>` - Line 7
- `test_remove_line_ranges_ignores_invalid_ranges() -> <ast.Constant object at 0x107f31550>` - Line 16
- `test_migration_error_targets_contains_expected_files() -> <ast.Constant object at 0x107f88d00>` - Line 25

**Key Imports:** `scripts.migration_common`

### `test_minhash_similarity.py` (python)

**Classes:**
- `TestMinHashSimilarity` - Line 16
  - Tests for MinHash similarity calculation.
  - Methods: test_identical_code_high_similarity, test_similar_code_moderate_similarity, test_different_code_low_similarity, test_empty_code_returns_zero, test_minhash_signature_caching (+1 more)
- `TestMinHashLSH` - Line 117
  - Tests for LSH-based candidate retrieval.
  - Methods: test_build_lsh_index, test_query_similar, test_find_all_similar_pairs
- `TestSimilarityConfig` - Line 197
  - Tests for similarity configuration.
  - Methods: test_default_config, test_custom_config
- `TestSimilarityResult` - Line 220
  - Tests for similarity result dataclass.
  - Methods: test_result_creation
- `TestEnhancedStructureHash` - Line 236
  - Tests for improved structure hash algorithm.
  - Methods: test_similar_structure_same_hash, test_different_call_patterns_different_hash, test_different_structure_different_hash, test_create_buckets, test_control_flow_detection
- `TestEnhancedStructureHashNodeSequence` - Line 358
  - Tests for AST-like node sequence extraction.
  - Methods: test_extract_node_sequence_basic, test_extract_node_sequence_order_preserved, test_extract_node_sequence_ignores_comments, test_extract_node_sequence_class_and_methods
- `TestEnhancedStructureHashComplexity` - Line 431
  - Tests for control flow complexity calculation.
  - Methods: test_complexity_simple_function, test_complexity_with_conditionals, test_complexity_with_loops, test_complexity_with_exception_handling
- `TestEnhancedStructureHashCallSignature` - Line 469
  - Tests for function call signature extraction.
  - Methods: test_call_signature_basic, test_call_signature_no_calls, test_call_signature_consistent, test_call_signature_filters_keywords
- `TestEnhancedStructureHashNestingDepth` - Line 535
  - Tests for nesting depth estimation.
  - Methods: test_nesting_depth_flat, test_nesting_depth_nested
- `TestEnhancedStructureHashLogarithmicBucket` - Line 564
  - Tests for logarithmic size bucketing.
  - Methods: test_logarithmic_bucket_small, test_logarithmic_bucket_medium, test_logarithmic_bucket_large, test_logarithmic_bucket_max
- `TestEnhancedStructureHashBucketDistribution` - Line 598
  - Tests for bucket distribution quality.
  - Methods: test_bucket_distribution_diverse_code
- `TestDetectorIntegration` - Line 667
  - Integration tests for detector with MinHash.
  - Methods: test_detector_uses_minhash_by_default, test_detector_can_use_sequence_matcher, test_detector_similarity_calculation, test_detector_similarity_with_sequence_matcher, test_detector_structure_hash
- `TestDetectorMinHashRegressions` - Line 730
  - Regression tests to prevent detector/MinHash integration issues.
  - Methods: test_detector_identical_code_high_similarity, test_detector_consistent_with_direct_minhash, test_detector_multiline_identical_code, test_detector_different_code_low_similarity, test_detector_empty_code_returns_zero (+1 more)
- `TestPerformanceCharacteristics` - Line 844
  - Tests to verify performance characteristics.
  - Methods: test_minhash_scales_linearly
- `TestSmallCodeFallback` - Line 875
  - Tests for SequenceMatcher fallback for small code snippets.
  - Methods: test_small_code_fallback_accuracy, test_large_code_uses_minhash, test_small_code_different_gets_low_similarity, test_fallback_can_be_disabled, test_small_code_threshold_configurable (+4 more)

**Key Imports:** `ast_grep_mcp.constants`, `ast_grep_mcp.features.deduplication.detector`, `ast_grep_mcp.features.deduplication.similarity`, `time` (+-1 more)

### `test_normalize_helpers.py` (python)

**Classes:**
- `TestIsCommentLine` - Line 17
  - Tests for HybridSimilarity._is_comment_line.
  - Methods: test_comment_detection
- `TestStripInlineComments` - Line 40
  - Tests for HybridSimilarity._strip_inline_comments.
  - Methods: test_strips_python_inline_comment, test_strips_js_inline_comment, test_preserves_hash_inside_balanced_quotes, test_hash_inside_balanced_single_quotes_is_stripped, test_preserves_hash_with_odd_quote_count (+5 more)
- `TestNormalizeForAstEdgeCases` - Line 100
  - Edge case tests for _normalize_for_ast beyond existing coverage.
  - Methods: test_comment_only_code_returns_empty, test_blank_only_code_returns_empty, test_mixed_python_js_comments, test_inline_hash_in_balanced_quotes_stripped, test_preserves_code_structure (+2 more)
- `TestApplicatorWrapperTypeGuards` - Line 150
  - Tests for applicator module-level wrapper TypeError guards.
  - Methods: test_plan_file_modification_order_rejects_non_dict, test_add_import_to_content_rejects_non_str, test_generate_import_rejects_non_str, test_plan_file_modification_order_accepts_dict, test_add_import_to_content_accepts_str

**Functions:**
- `hybrid()` - Line 96

**Key Imports:** `ast_grep_mcp.features.deduplication.applicator`, `ast_grep_mcp.features.deduplication.similarity`, `pytest`, `unittest.mock` (+-1 more)

### `test_normalize_indentation.py` (python)

**Classes:**
- `TestNormalizeIndentation` - Line 6
  - Test adaptive 4-space vs 2-space indentation normalization.
  - Methods: test_two_space_indent_normalized_to_four, test_four_space_indent_stays_four, test_eight_space_indent_four_space_style, test_six_space_indent_treated_as_two_space, test_no_indent (+1 more)

**Key Imports:** `ast_grep_mcp.features.deduplication.similarity`

### `test_orchestrator_optimizations.py` (python)

**Classes:**
- `TestComponentInstanceCaching` - Line 20
  - Tests for lazy component initialization optimization (1.2).
  - Methods: test_components_not_initialized_on_construction, test_detector_lazy_initialization, test_ranker_lazy_initialization, test_coverage_detector_lazy_initialization, test_recommendation_engine_lazy_initialization (+2 more)
- `TestInputValidation` - Line 122
  - Tests for input validation optimization (3.1).
  - Methods: temp_project_dir, test_invalid_project_path_not_exists, test_invalid_project_path_not_directory, test_invalid_min_similarity_too_low, test_invalid_min_similarity_too_high (+6 more)
- `TestNamingConsistency` - Line 238
  - Tests for naming consistency optimization (2.4).
  - Methods: test_result_structure_has_clear_naming, test_top_candidates_count_reflects_actual_count, test_savings_calculated_from_top_candidates_only, test_logging_uses_consistent_naming
- `TestParallelEnrichUtility` - Line 356
  - Tests for parallel execution utility optimization (1.3).
  - Methods: test_parallel_enrich_sequential_mode, test_parallel_enrich_parallel_mode, test_parallel_enrich_single_candidate_uses_sequential, test_parallel_enrich_error_handling_sequential, test_parallel_enrich_error_handling_parallel (+15 more)

**Key Imports:** `ast_grep_mcp.constants`, `ast_grep_mcp.features.deduplication.analysis_orchestrator`, `inspect`, `os`, `pathlib` (+4 more)

### `test_orphan_detector.py` (python)

**Classes:**
- `TestResolveJsRelativeImport` - Line 29
  - Tests for _resolve_js_relative_import edge cases.
  - Methods: test_extensionless_resolves_to_ts, test_js_extension_remaps_to_ts, test_js_extension_remaps_to_tsx, test_jsx_extension_remaps_to_tsx, test_extensionless_resolves_to_index (+3 more)
- `TestBuildDependencyGraphTwoPass` - Line 112
  - Verify two-pass build resolves edges regardless of file discovery order.
  - Methods: test_edge_resolved_when_target_discovered_after_source, test_python_cross_imports_resolved, test_all_files_collected_before_edge_extraction

**Functions:**
- `detector() -> OrphanDetector` - Line 12
- `ts_project(tmp_path) -> Path` - Line 21

**Key Imports:** `ast_grep_mcp.features.quality.orphan_detector`, `ast_grep_mcp.models.orphan`, `pathlib`, `pytest`

### `test_orphan_import_helpers.py` (python)

**Classes:**
- `TestIsOrphanCloseParen` - Line 11
  - Methods: test_close_paren_after_close_paren, test_close_paren_after_regular_line, test_non_paren_line
- `TestIsOrphanImportItemStart` - Line 22
  - Methods: test_indented_identifier_after_import_close, test_from_line_not_orphan, test_def_line_not_orphan, test_unindented_not_orphan, test_line_with_equals_not_orphan (+2 more)
- `TestScanOrphanItemRange` - Line 45
  - Methods: test_ends_at_close_paren, test_ends_at_statement_start, test_ends_at_empty_line, test_ends_at_comment, test_ends_at_eof
- `TestFindOrphanedImportsIntegration` - Line 67
  - Methods: test_no_orphans, test_orphaned_close_paren, test_orphaned_indented_block

**Key Imports:** `scripts.fix_import_orphans`

### `test_parsing_utils.py` (python)

**Classes:**
- `TestDetectTripleQuote` - Line 7
  - Methods: test_double_quote, test_single_quote, test_no_triple_quote, test_empty_string, test_single_quote_char (+2 more)
- `TestSkipBlankLines` - Line 30
  - Methods: test_no_blanks, test_skip_blanks, test_start_midway, test_all_blank, test_empty_list (+2 more)
- `TestMeasureDocstring` - Line 59
  - Methods: test_single_line_double_quote, test_single_line_single_quote, test_multi_line, test_no_docstring, test_unclosed_docstring
- `TestFindDocstringExtent` - Line 81
  - Methods: test_single_line_docstring, test_multi_line_docstring, test_no_docstring, test_skips_blank_lines, test_all_blank_after_start (+1 more)

**Key Imports:** `ast_grep_mcp.features.complexity.analyzer`, `ast_grep_mcp.utils.parsing`

### `test_pattern_debug.py` (python)

**Classes:**
- `TestExtractMetavariables` - Line 23
  - Tests for metavariable extraction and validation.
  - Methods: test_single_valid_metavariable, test_multiple_valid_metavariables, test_multi_node_metavariable, test_unnamed_multi_node, test_non_capturing_metavariable (+5 more)
- `TestCheckPatternIssues` - Line 100
  - Tests for pattern issue detection.
  - Methods: test_no_issues_for_valid_pattern, test_error_for_invalid_metavariable, test_info_for_single_arg_metavariable, test_warning_for_fragment_pattern
- `TestExtractRootKind` - Line 145
  - Tests for AST root kind extraction.
  - Methods: test_extract_kind_format, test_extract_cst_format, test_extract_first_word, test_empty_output
- `TestCompareAsts` - Line 172
  - Tests for AST comparison.
  - Methods: test_matching_roots, test_mismatched_roots, test_error_in_pattern_ast, test_truncation_of_long_ast
- `TestGenerateSuggestions` - Line 207
  - Tests for suggestion generation.
  - Methods: test_suggestions_for_errors_first, test_suggestions_for_structural_mismatch, test_success_message_when_matched
- `TestPatternDebugResult` - Line 274
  - Tests for PatternDebugResult model.
  - Methods: test_to_dict_serialization
- `TestMetavariableEdgeCases` - Line 312
  - Edge case tests for metavariable extraction.
  - Methods: test_underscore_only, test_mixed_valid_and_invalid, test_metavar_in_string_not_extracted
- `TestIssueCategories` - Line 338
  - Tests for issue categorization.
  - Methods: test_all_severity_levels, test_all_issue_categories

**Key Imports:** `ast_grep_mcp.features.search.service`, `ast_grep_mcp.models.pattern_debug`

### `test_prefer_const_reassignment.py` (python)

**Classes:**
- `TestExtractVarName` - Line 14
  - Test variable name extraction from let declarations.
  - Methods: test_simple_assignment, test_with_type_annotation, test_uninitialized, test_destructuring_array_returns_none, test_destructuring_object_returns_none (+2 more)
- `TestLineReassignsVar` - Line 39
  - Test single-line reassignment detection.
  - Methods: _pat, test_simple_assignment, test_compound_add, test_compound_sub, test_postfix_increment (+12 more)
- `TestIsVariableReassigned` - Line 98
  - Test file-level reassignment detection.
  - Methods: _write_file, test_reassigned_in_loop, test_not_reassigned, test_reassigned_with_compound_operator, test_reassigned_plain_equals (+3 more)

**Key Imports:** `ast_grep_mcp.features.quality.fixer`, `os`, `re`, `tempfile`

### `test_progress_callbacks.py` (python)

**Classes:**
- `TestProgressCallbacks` - Line 19
  - Tests for progress callback functionality (3.3).
  - Methods: temp_project_dir, orchestrator_with_mocks, test_progress_callback_is_called, test_progress_stages_in_order, test_progress_percentages_increase (+11 more)
- `TestProgressCallbackIntegration` - Line 296
  - Integration tests for progress callbacks with real workflow.
  - Methods: temp_project_dir, test_progress_percentage_distribution

**Key Imports:** `ast_grep_mcp.constants`, `ast_grep_mcp.features.deduplication.analysis_orchestrator`, `pytest`, `tempfile`, `unittest.mock`

### `test_ranker.py` (python)

**Classes:**
- `TestDuplicationRanker` - Line 15
  - Tests for DuplicationRanker class.
  - Methods: ranker, sample_candidates, test_rank_all_candidates, test_rank_with_max_results, test_max_results_greater_than_candidates (+7 more)
- `TestEarlyExitPerformance` - Line 146
  - Tests to verify early exit optimization actually improves performance.
  - Methods: test_early_exit_processes_fewer_rank_assignments
- `TestParallelScoring` - Line 182
  - Tests for parallel scoring with ThreadPoolExecutor.
  - Methods: test_parallel_scoring_produces_same_results, test_parallel_scoring_with_small_candidate_list, test_parallel_scoring_disabled_with_max_workers_zero, test_parallel_scoring_with_cache

**Key Imports:** `ast_grep_mcp.features.deduplication.ranker`, `pytest`

### `test_ranker_caching.py` (python)

**Classes:**
- `TestScoreCaching` - Line 16
  - Test score caching functionality in DuplicationRanker.
  - Methods: ranker_with_cache, ranker_without_cache, sample_candidate, test_cache_initialization, test_cache_key_generation_deterministic (+13 more)
- `TestCachePerformance` - Line 237
  - Test cache performance characteristics.
  - Methods: ranker, test_large_cache_performance, test_cache_hit_rate_with_duplicates
- `TestCacheEdgeCases` - Line 295
  - Test edge cases for score caching.
  - Methods: ranker, test_empty_candidates_list, test_candidate_with_empty_files_list, test_candidate_with_missing_optional_fields

**Key Imports:** `pytest`, `src.ast_grep_mcp.constants`, `src.ast_grep_mcp.features.deduplication.ranker`, `unittest.mock`

### `test_rename_symbol.py` (python)

**Classes:**
- `TestSymbolRenamer` - Line 32
  - Tests for SymbolRenamer class.
  - Methods: test_find_symbol_references_simple, test_find_symbol_references_no_matches, test_build_scope_tree_python_simple, test_build_scope_tree_nested_functions, test_check_naming_conflicts_no_conflict (+5 more)
- `TestRenameCoordinator` - Line 271
  - Tests for RenameCoordinator class.
  - Methods: test_rename_symbol_dry_run, test_rename_symbol_no_references, test_rename_symbol_with_conflicts, test_rename_symbol_apply, test_rename_in_file_word_boundary (+1 more)
- `TestRenameSymbolTool` - Line 481
  - Tests for rename_symbol MCP tool.
  - Methods: test_rename_symbol_tool_dry_run, test_rename_symbol_tool_error_handling, test_rename_symbol_tool_with_file_filter
- `TestMultiFileRename` - Line 554
  - Integration tests for multi-file symbol renaming.
  - Methods: test_rename_across_multiple_files, test_rollback_on_failure

**Functions:**
- `python_renamer()` - Line 14
- `typescript_renamer()` - Line 21
- `python_coordinator()` - Line 27

**Key Imports:** `ast_grep_mcp.features.refactoring.rename_coordinator`, `ast_grep_mcp.features.refactoring.renamer`, `ast_grep_mcp.features.refactoring.tools`, `ast_grep_mcp.models.refactoring`, `pytest` (+1 more)

### `test_reporting_helpers.py` (python)

**Classes:**
- `TestUpdateDistribution` - Line 6
  - Methods: test_low_complexity, test_medium_complexity, test_high_complexity
- `TestBuildGlobalRecommendations` - Line 23
  - Methods: test_no_recommendations_for_clean_results, test_high_complexity_recommendation, test_many_lines_saveable_recommendation, test_many_candidates_recommendation
- `TestBuildSummary` - Line 49
  - Methods: test_summary_structure, test_summary_empty_candidates
- `TestBuildEnhancedCandidate` - Line 67
  - Methods: test_candidate_has_expected_keys, test_candidate_fallback_function_name

**Key Imports:** `ast_grep_mcp.features.deduplication.reporting`

### `test_scan_complexity_offenders.py` (python)

**Classes:**
- `TestExtractName` - Line 25
  - Methods: test_simple_def, test_async_def, test_decorated_function, test_decorated_async, test_indented_method (+2 more)
- `TestShortPath` - Line 51
  - Methods: test_feature_path, test_core_path, test_unrecognized_path_unchanged
- `TestProjectRoot` - Line 65
  - Methods: test_project_root_is_absolute, test_project_root_exists, test_project_root_uses_file_not_cwd
- `TestMain` - Line 85
  - Methods: _capture_main, test_outputs_markdown_table_header, test_all_flag_produces_more_rows, test_default_only_shows_offenders

**Key Imports:** `io`, `scripts.scan_complexity_offenders`, `sys`, `unittest.mock` (+-1 more)

### `test_schema.py` (python)

**Classes:**
- `TestSchemaOrgClient` - Line 101
  - Tests for SchemaOrgClient class.
  - Methods: test_normalize_to_array, test_generate_example_value_text, test_generate_example_value_url, test_generate_example_value_date, test_generate_example_value_datetime (+13 more)
- `TestSchemaOrgTools` - Line 681
  - Tests for Schema.org MCP tools.
  - Methods: test_generate_entity_id_tool, test_validate_entity_id_tool
- `TestSchemaOrgClientHelpers` - Line 819
  - Tests for SchemaOrgClient helper methods.
  - Methods: test_extract_super_types, test_extract_super_types_multiple, test_find_sub_types, test_format_property
- `TestGetSchemaOrgClient` - Line 886
  - Tests for get_schema_org_client singleton.
  - Methods: test_get_schema_org_client_singleton, test_get_schema_org_client_creates_instance

**Key Imports:** `ast_grep_mcp.features.schema.client`, `httpx`, `pytest`, `unittest.mock`

### `test_schema_enhancement.py` (python)

**Classes:**
- `TestEnhancementRules` - Line 121
  - Tests for enhancement_rules.py functions.
  - Methods: test_get_property_priority_known_property, test_get_property_priority_unknown_property, test_get_property_priority_unknown_entity, test_get_rich_results_for_property, test_get_rich_results_for_property_unknown (+4 more)
- `TestGraphLoading` - Line 179
  - Tests for graph loading functions.
  - Methods: test_extract_entities_from_graph_array, test_extract_entities_from_single_entity, test_extract_entities_from_array, test_load_graph_from_file, test_load_graph_from_directory (+2 more)
- `TestEntityAnalysis` - Line 265
  - Tests for entity analysis functions.
  - Methods: test_extract_entity_type_string, test_extract_entity_type_array, test_extract_entity_type_missing, test_build_property_reason_critical, test_build_property_reason_high_no_rich_result
- `TestReferenceValidation` - Line 299
  - Tests for reference validation functions.
  - Methods: test_find_id_references_simple, test_find_id_references_nested, test_validate_entity_references_valid, test_validate_entity_references_broken
- `TestMissingEntityDetection` - Line 354
  - Tests for missing entity detection functions.
  - Methods: test_parse_suggestion_rule_has, test_parse_suggestion_rule_not_has, test_parse_suggestion_rule_count, test_parse_suggestion_rule_count_not_met, test_parse_suggestion_rule_complex_and (+7 more)
- `TestSEOScoring` - Line 452
  - Tests for SEO scoring functions.
  - Methods: test_calculate_entity_seo_score_perfect, test_calculate_entity_seo_score_critical_missing, test_calculate_entity_seo_score_with_validation_issues, test_calculate_overall_seo_score, test_build_priority_summary
- `TestGraphStructureValidation` - Line 524
  - Tests for graph structure validation.
  - Methods: test_validate_graph_structure_valid, test_validate_graph_structure_missing_context, test_validate_graph_structure_invalid_context, test_validate_graph_structure_empty_graph, test_validate_graph_structure_single_entity
- `TestOutputGeneration` - Line 569
  - Tests for output generation functions.
  - Methods: test_generate_enhanced_graph, test_generate_diff, test_generate_diff_no_changes
- `TestIntegration` - Line 665
  - Integration tests with mocked Schema.org client.

**Functions:**
- `simple_organization_graph() -> List[...]` - Line 50
- `complete_organization_graph() -> List[...]` - Line 63
- `sample_entity_enhancement() -> EntityEnhancement` - Line 89

**Key Imports:** `ast_grep_mcp.constants`, `ast_grep_mcp.features.schema.enhancement_rules`, `ast_grep_mcp.features.schema.enhancement_service`, `ast_grep_mcp.models.schema_enhancement`, `json` (+6 more)

### `test_schema_html.py` (python)

**Classes:**
- `TestParseJsonldText` - Line 19
  - Methods: test_valid_json, test_valid_json_with_whitespace, test_malformed_json, test_empty_string
- `TestDetectJsonldInHtml` - Line 42
  - Methods: test_single_valid_script, test_multiple_scripts, test_malformed_jsonld, test_no_matches, test_mixed_valid_and_malformed
- `TestDetectMicrodataInHtml` - Line 88
  - Methods: test_typed_elements, test_missing_itemtype, test_no_matches
- `TestDetectRdfaInHtml` - Line 122
  - Methods: test_rdfa_properties, test_no_rdfa
- `TestValidateHtmlStructuredData` - Line 143
  - Methods: test_combined_summary
- `TestLiquidTemplateFallback` - Line 175
  - Tests for Liquid/Jekyll template handling with regex fallback.
  - Methods: test_has_liquid_tags_detects_liquid_tags, test_has_liquid_tags_ignores_regular_html, test_jsonld_with_liquid_fallback, test_microdata_with_liquid_fallback, test_rdfa_with_liquid_fallback

**Functions:**
- `_make_match(file, line, text) -> dict` - Line 38

**Key Imports:** `ast_grep_mcp.features.schema.html_service`, `os`, `tempfile`, `unittest.mock`

### `test_schema_markdown.py` (python)

**Classes:**
- `TestExtractFrontmatter` - Line 17
  - Methods: test_valid_frontmatter, test_no_frontmatter, test_empty_frontmatter, test_malformed_yaml, test_non_dict_frontmatter
- `TestGetNested` - Line 40
  - Methods: test_single_level, test_two_levels, test_missing_key, test_non_dict_intermediate
- `TestFindSchemaFields` - Line 54
  - Methods: test_direct_type, test_nested_seo_schema, test_structured_data_key, test_no_schema_fields
- `TestExtractSchemaFromFrontmatter` - Line 82
  - Methods: test_with_schema, test_without_schema, test_no_frontmatter, test_multiple_files, test_custom_globs
- `TestValidateFrontmatterSchema` - Line 126
  - Methods: test_valid_schema, test_missing_context, test_bad_context, test_unrecognized_type
- `TestSuggestFrontmatterEnhancements` - Line 152
  - Methods: test_missing_properties, test_complete_article, test_partial_completeness, test_non_string_type_skipped, test_unknown_type_no_suggestions

**Key Imports:** `ast_grep_mcp.features.schema.markdown_service`, `pytest`

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
- `TestHybridSimilarityConfigSemantic` - Line 243
  - Tests for HybridSimilarityConfig semantic options.
  - Methods: test_default_semantic_disabled, test_enable_semantic_with_rebalanced_weights, test_semantic_weights_must_sum_to_one, test_invalid_semantic_weight, test_invalid_semantic_threshold
- `TestHybridSimilarityResultSemantic` - Line 293
  - Tests for HybridSimilarityResult semantic fields.
  - Methods: test_result_with_semantic, test_result_without_semantic, test_result_to_dict_with_semantic
- `TestHybridSimilarityThreeStage` - Line 362
  - Tests for three-stage hybrid pipeline.
  - Methods: test_semantic_disabled_by_default, test_semantic_skipped_when_unavailable, test_early_exit_skips_semantic, test_empty_input_returns_zero_with_semantic_fields
- `TestSemanticSimilarityDefaults` - Line 440
  - Tests for SemanticSimilarityDefaults constants.
  - Methods: test_default_values, test_weights_sum_to_one
- `TestSemanticSimilarityIntegration` - Line 472
  - Integration tests that require transformers and torch.
  - Methods: semantic, test_identical_code_high_similarity, test_similar_code_high_similarity, test_different_code_lower_similarity, test_embedding_caching (+1 more)
- `TestHybridThreeStageIntegration` - Line 549
  - Integration tests for three-stage hybrid pipeline.
  - Methods: hybrid_with_semantic, test_three_stage_similar_code, test_three_stage_result_format

**Key Imports:** `ast_grep_mcp.constants`, `ast_grep_mcp.features.deduplication.similarity`, `pytest`, `unittest.mock` (+-1 more)

### `test_splice_fixed_code.py` (python)

**Classes:**
- `TestSingleLineSplice` - Line 21
  - Single-line path: str.replace within the line preserves indent.
  - Methods: test_simple_keyword_replace, test_replace_preserves_surrounding_code, test_replace_at_zero_indent, test_replace_in_middle_of_file, test_deep_indent (+1 more)
- `TestMultiLineSplice` - Line 60
  - Multi-line path: re-applies stripped first-line indent.
  - Methods: test_bare_except_4space, test_bare_except_8space, test_bare_except_12space, test_multi_line_body_preserved, test_surrounding_lines_untouched (+4 more)
- `TestSpliceEdgeCases` - Line 143
  - Methods: test_does_not_mutate_input, test_empty_snippet_single_line, test_last_line_no_trailing_newline

**Functions:**
- `_lines(text) -> list[...]` - Line 11

**Key Imports:** `ast_grep_mcp.features.quality.fixer`

### `test_split_params_guard.py` (python)

**Classes:**
- `TestSplitParamsDepthGuard` - Line 6
  - Test that > in arrow function defaults doesn't corrupt depth.
  - Methods: test_simple_params, test_generic_type_param, test_arrow_function_default, test_nested_generics, test_empty_string (+3 more)

**Key Imports:** `ast_grep_mcp.features.documentation.docstring_generator`

### `test_standards_enforcement.py` (python)

**Classes:**
- `TestRuleViolationDataClass` - Line 65
  - Test RuleViolation data class.
  - Methods: test_instantiation_all_fields, test_instantiation_optional_fields_none, test_minimal_violation
- `TestRuleSetDataClass` - Line 131
  - Test RuleSet data class.
  - Methods: test_instantiation_all_fields, test_instantiation_without_priority, test_empty_rules_list
- `TestEnforcementResultDataClass` - Line 160
  - Test EnforcementResult data class.
  - Methods: test_instantiation_all_fields, test_empty_result
- `TestRuleExecutionContextDataClass` - Line 212
  - Test RuleExecutionContext data class.
  - Methods: test_instantiation_all_fields
- `TestRuleSetsConfiguration` - Line 238
  - Test RULE_SETS configuration.
  - Methods: test_rule_sets_exist, test_all_four_sets_exist, test_rule_sets_structure, test_recommended_set_priority, test_security_set_priority (+3 more)
- `TestTemplateToLintingRule` - Line 292
  - Test template_to_linting_rule function.
  - Methods: test_basic_conversion, test_conversion_preserves_all_fields, test_constraints_is_none, test_conversion_multiple_templates
- `TestLoadCustomRules` - Line 353
  - Test load_custom_rules function.
  - Methods: test_load_rules_from_directory, test_missing_directory, test_filter_by_language, test_handle_malformed_yaml, test_empty_directory (+1 more)
- `TestLoadRuleSet` - Line 442
  - Test load_rule_set function.
  - Methods: test_load_recommended_rule_set, test_load_security_rule_set, test_load_performance_rule_set, test_load_style_rule_set, test_load_all_rule_set (+7 more)
- `TestParseMatchToViolation` - Line 546
  - Test parse_match_to_violation function.
  - Methods: test_parse_complete_match, test_parse_match_without_metavars, test_parse_match_missing_range, test_parse_multiline_match
- `TestShouldExcludeFile` - Line 614
  - Test should_exclude_file function.
  - Methods: test_exclude_node_modules, test_exclude_simple_glob, test_dont_exclude_non_matching, test_multiple_patterns, test_case_sensitivity (+5 more)
- `TestExecuteRule` - Line 689
  - Test execute_rule function.
  - Methods: test_execute_single_rule, test_parse_violations_correctly, test_apply_file_exclusion, test_respect_max_violations, test_handle_execution_errors (+1 more)
- `TestExecuteRulesBatch` - Line 846
  - Test execute_rules_batch function.
  - Methods: test_parallel_execution, test_combine_violations, test_early_termination_at_max_violations, test_handle_individual_failures
- `TestGroupViolationsByFile` - Line 945
  - Test _group_violations_by_file function.
  - Methods: test_group_by_file, test_sort_by_line_number, test_empty_violations
- `TestGroupViolationsBySeverity` - Line 987
  - Test _group_violations_by_severity function.
  - Methods: test_group_by_severity, test_all_severity_levels_present, test_empty_violations
- `TestGroupViolationsByRule` - Line 1023
  - Test _group_violations_by_rule function.
  - Methods: test_group_by_rule, test_empty_violations
- `TestFilterViolationsBySeverity` - Line 1047
  - Test filter_violations_by_severity function.
  - Methods: _mixed_violations, test_filter_by_error, test_filter_by_warning, test_filter_by_info, test_handle_all_severity_levels
- `TestFormatViolationReport` - Line 1087
  - Test format_violation_report function.
  - Methods: test_format_complete_report, test_summary_section, test_violations_breakdown, test_handle_empty_violations
- `TestEnforceStandardsTool` - Line 1215
  - Test enforce_standards MCP tool.
  - Methods: test_basic_scan_with_recommended_rules, _recommended_rule_set, test_security_rule_set, test_custom_rules_with_ids, test_invalid_severity_threshold (+11 more)

**Functions:**
- `_make_violation(file, line, column, end_line, end_column, severity, rule_id, message, code_snippet)` - Line 38

**Key Imports:** `ast_grep_mcp.features.quality.enforcer`, `ast_grep_mcp.features.quality.rules`, `ast_grep_mcp.models.standards`, `pytest`, `unittest.mock`

### `test_stream_async.py` (python)

**Classes:**
- `TestAsyncStreamAstGrepResults` - Line 17
  - Test async_stream_ast_grep_results streaming function.
- `TestStreamAstGrepResultsSyncShim` - Line 160
  - Test sync shim backward compatibility.
  - Methods: test_sync_shim_delegates_to_async, test_sync_shim_preserves_max_results

**Key Imports:** `ast_grep_mcp.constants`, `ast_grep_mcp.core.exceptions`, `ast_grep_mcp.core.executor`, `asyncio`, `json` (+2 more)

### `test_structural_braces.py` (python)

**Classes:**
- `TestCountStructuralBraces` - Line 6
  - Test string/comment/template-literal awareness of brace counting.
  - Methods: test_plain_open_brace, test_plain_close_brace, test_balanced_braces, test_braces_in_double_quoted_string, test_braces_in_single_quoted_string (+8 more)

**Key Imports:** `ast_grep_mcp.features.condense.service`

### `test_tool_context.py` (python)

**Classes:**
- `TestToolContext` - Line 11
  - Tests for the synchronous tool_context context manager.
  - Methods: test_yields_start_time, test_reraises_exception, test_captures_to_sentry_on_error, test_no_sentry_on_success, test_logs_status_failed
- `TestAsyncToolContext` - Line 57
  - Tests for the async variant.
  - Methods: test_handle_tool_error_uses_provided_logger, test_handle_tool_error_creates_logger_when_none

**Key Imports:** `ast_grep_mcp.utils.tool_context`, `pytest`, `time`, `unittest.mock` (+-1 more)

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
- `TestTrackOperation` - Line 306
  - Tests for track_operation context manager.
  - Methods: temp_db, test_successful_operation, test_failed_operation, test_response_time_tracking, test_cost_calculation
- `TestTrackUsageDecorator` - Line 366
  - Tests for @track_usage decorator.
  - Methods: temp_db, test_decorator_logs_success, test_decorator_logs_failure, test_decorator_extracts_metrics
- `TestFormatUsageReport` - Line 429
  - Tests for usage report formatting.
  - Methods: test_basic_report, test_report_with_tools
- `TestIntegrationWithDetector` - Line 469
  - Integration tests with DuplicationDetector.
  - Methods: temp_db, test_detector_logs_usage

**Key Imports:** `ast_grep_mcp.core.usage_tracking`, `ast_grep_mcp.features.deduplication.detector`, `datetime`, `os`, `pytest` (+3 more)

### `test_venv_exclusions.py` (python)

**Functions:**
- `test_file_patterns_merge_with_venv_excludes_adds_required_patterns() -> <ast.Constant object at 0x1063574c0>` - Line 12
- `test_complexity_exclude_normalization_preserves_custom_and_adds_venv() -> <ast.Constant object at 0x10635e8b0>` - Line 20
- `test_prepare_smell_detection_params_enforces_venv_excludes() -> <ast.Constant object at 0x10635e850>` - Line 28
- `test_documentation_source_scan_excludes_venv_even_with_custom_excludes(tmp_path) -> <ast.Constant object at 0x106371250>` - Line 37
- `test_duplication_detector_enforces_venv_excludes_with_custom_patterns(monkeypatch, tmp_path) -> <ast.Constant object at 0x10634a400>` - Line 57
- `test_dedup_tools_normalization_enforces_venv_patterns() -> <ast.Constant object at 0x10634a8b0>` - Line 75

**Key Imports:** `ast_grep_mcp.constants`, `ast_grep_mcp.features.complexity.tools`, `ast_grep_mcp.features.deduplication.detector`, `ast_grep_mcp.features.documentation.sync_checker`

---
*Generated by Enhanced Schema Generator with schema.org markup*