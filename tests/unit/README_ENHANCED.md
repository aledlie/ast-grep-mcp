# unit

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareSourceCode",
  "name": "unit",
  "description": "Directory containing 8 code files with 58 classes and 6 functions",
  "programmingLanguage": [
    {
      "@type": "ComputerLanguage",
      "name": "Python"
    }
  ],
  "featureList": [
    "58 class definitions",
    "6 function definitions"
  ]
}
</script>

## Overview

This directory contains 8 code file(s) with extracted schemas.

## Files and Schemas

### `test_batch.py` (python)

**Classes:**
- `MockFastMCP` - Line 24
  - Methods: __init__, tool, run
- `TestBatchSearchBasic` - Line 52
  - Basic tests for batch_search tool.
  - Methods: setup_method, teardown_method, test_batch_search_tool_registered, test_batch_search_single_query, test_batch_search_multiple_queries_parallel (+3 more)
- `TestBatchSearchAggregation` - Line 170
  - Tests for result aggregation and deduplication.
  - Methods: setup_method, teardown_method, test_batch_search_deduplication, test_batch_search_no_deduplication, test_batch_search_sorts_results (+1 more)
- `TestBatchSearchConditional` - Line 272
  - Tests for conditional execution.
  - Methods: setup_method, teardown_method, test_conditional_if_matches_executes, test_conditional_if_matches_skips, test_conditional_if_no_matches_executes (+1 more)
- `TestBatchSearchErrorHandling` - Line 401
  - Tests for error handling in batch operations.
  - Methods: setup_method, teardown_method, test_batch_search_continues_on_query_error, test_batch_search_auto_assigns_query_ids, test_batch_search_text_output_format (+1 more)

**Functions:**
- `mock_field() -> Any` - Line 39

**Key Imports:** `main`, `os`, `pytest`, `shutil`, `sys` (+3 more)

### `test_cache.py` (python)

**Classes:**
- `MockFastMCP` - Line 13
  - Methods: __init__, tool, run
- `TestQueryCache` - Line 39
  - Test QueryCache class functionality
  - Methods: test_cache_initialization, test_cache_put_and_get, test_cache_miss, test_cache_ttl_expiration, test_cache_lru_eviction (+5 more)
- `TestCacheIntegration` - Line 184
  - Test cache integration with find_code and find_code_by_rule
  - Methods: setup_method, teardown_method, test_find_code_cache_miss_then_hit, test_find_code_by_rule_cache_miss_then_hit, test_cache_disabled (+2 more)
- `TestCacheClearAndStats` - Line 312
  - Tests for cache.clear() and cache.get_stats() methods
  - Methods: test_clear_empty_cache, test_clear_populated_cache, test_clear_resets_stats, test_get_stats_initial_state, test_get_stats_after_operations (+6 more)

**Functions:**
- `mock_field() -> Any` - Line 28

**Key Imports:** `main`, `os`, `sys`, `time`, `typing` (+1 more)

### `test_duplication.py` (python)

**Classes:**
- `MockFastMCP` - Line 15
  - Methods: __init__, tool, run
- `TestNormalizeCode` - Line 52
  - Test code normalization for comparison
  - Methods: test_removes_whitespace, test_removes_blank_lines, test_removes_comments, test_preserves_code_structure
- `TestCalculateSimilarity` - Line 82
  - Test similarity calculation between code snippets
  - Methods: test_identical_code, test_completely_different_code, test_similar_code, test_empty_code, test_whitespace_differences_normalized
- `TestGroupDuplicates` - Line 120
  - Test grouping of duplicate code matches
  - Methods: test_groups_identical_matches, test_min_lines_filter, test_min_similarity_threshold, test_no_duplicates_returns_empty, test_empty_matches_returns_empty
- `TestGenerateRefactoringSuggestions` - Line 174
  - Test generation of refactoring suggestions
  - Methods: test_function_definition_suggestions, test_class_definition_suggestions, test_includes_locations, test_calculates_line_savings
- `TestFindDuplicationTool` - Line 263
  - Test the find_duplication MCP tool
  - Methods: test_finds_duplicate_functions, test_no_duplicates_found, test_no_constructs_found, test_custom_similarity_threshold, test_invalid_similarity_threshold (+6 more)

**Functions:**
- `mock_field() -> Any` - Line 30

**Key Imports:** `main`, `os`, `pytest`, `sys`, `typing` (+1 more)

### `test_edge_cases.py` (python)

**Classes:**
- `MockFastMCP` - Line 18
  - Mock FastMCP that returns functions unchanged
  - Methods: __init__, tool, run
- `TestConfigValidationErrorPaths` - Line 47
  - Test configuration validation error handling with sys.exit.
  - Methods: test_parse_args_with_invalid_config_flag, test_parse_args_with_invalid_config_env_var
- `TestCacheEnvironmentVariables` - Line 80
  - Test cache configuration via environment variables.
  - Methods: test_cache_disabled_via_no_cache_flag, test_cache_disabled_via_env_var, test_cache_size_via_env_var, test_cache_size_invalid_env_var, test_cache_ttl_via_env_var (+2 more)
- `TestDuplicationSizeRatioEdgeCase` - Line 133
  - Test duplication detection size ratio filtering.
  - Methods: test_group_duplicates_skips_different_sizes
- `TestJavaScriptValidation` - Line 159
  - Test JavaScript/TypeScript syntax validation with node.
  - Methods: test_validate_syntax_javascript_node_not_found, test_validate_syntax_javascript_timeout, test_validate_syntax_javascript_invalid_code
- `TestSchemaOrgClientEdgeCases` - Line 210
  - Test Schema.org client error handling.
  - Methods: setup_method, test_schema_org_client_http_error_fallback, test_schema_org_client_empty_graph
- `TestRewriteBackupEdgeCases` - Line 239
  - Test edge cases in rewrite and backup functionality.
  - Methods: setup_method, teardown_method, test_create_backup_nonexistent_file
- `TestCommandNotFoundLogging` - Line 269
  - Test command not found error paths.
  - Methods: test_run_ast_grep_command_not_found
- `TestStreamingSubprocessCleanup` - Line 279
  - Test subprocess cleanup in streaming mode.
  - Methods: test_stream_results_early_termination_logging

**Key Imports:** `json`, `main`, `os`, `pytest`, `shutil` (+5 more)

### `test_phase2.py` (python)

**Classes:**
- `MockFastMCP` - Line 26
  - Methods: __init__, tool, run
- `TestResultStreaming` - Line 56
  - Test streaming result parsing and early termination
  - Methods: test_stream_basic_json_parsing, test_stream_early_termination, test_stream_subprocess_cleanup_sigterm, test_stream_subprocess_cleanup_sigkill, test_stream_invalid_json_line_handling (+2 more)
- `TestParallelExecution` - Line 211
  - Test parallel execution with workers parameter
  - Methods: setup_method, test_workers_parameter_default_auto, test_workers_parameter_explicit_value, test_workers_parameter_in_find_code_by_rule, test_workers_with_other_parameters
- `TestLargeFileHandling` - Line 325
  - Test file size filtering functionality
  - Methods: test_filter_files_by_size_basic, test_filter_files_by_size_no_limit, test_filter_files_by_size_language_filtering, test_filter_files_by_size_excludes_common_dirs, test_filter_files_by_size_handles_os_errors (+3 more)
- `TestPhase2Integration` - Line 516
  - Test multiple Phase 2 features working together
  - Methods: setup_method, test_streaming_with_file_filtering_and_parallel, test_all_phase2_features_with_caching

**Functions:**
- `mock_field() -> Any` - Line 41

**Key Imports:** `main`, `os`, `pathlib`, `pytest`, `sys` (+3 more)

### `test_rewrite.py` (python)

**Classes:**
- `MockFastMCP` - Line 26
  - Methods: __init__, tool, run
- `TestRewriteCode` - Line 53
  - Tests for rewrite_code MCP tool.
  - Methods: setup_method, teardown_method, test_rewrite_code_tool_registered, test_rewrite_code_dry_run_mode, test_rewrite_code_missing_fix_field (+5 more)
- `TestBackupManagement` - Line 292
  - Tests for backup creation and restoration functions.
  - Methods: setup_method, teardown_method, test_create_backup_creates_directory, test_create_backup_copies_files, test_create_backup_saves_metadata (+5 more)
- `TestRollbackRewrite` - Line 412
  - Tests for rollback_rewrite MCP tool.
  - Methods: setup_method, teardown_method, test_rollback_rewrite_tool_registered, test_rollback_rewrite_restores_files, test_rollback_rewrite_nonexistent_backup
- `TestListBackups` - Line 470
  - Tests for list_backups MCP tool.
  - Methods: setup_method, teardown_method, test_list_backups_tool_registered, test_list_backups_empty, test_list_backups_returns_all_backups
- `TestRewriteIntegration` - Line 517
  - Integration tests combining multiple rewrite features.
  - Methods: setup_method, teardown_method, test_full_rewrite_workflow, test_backup_prevents_data_loss
- `TestSyntaxValidation` - Line 644
  - Tests for syntax validation of rewritten code.
  - Methods: setup_method, teardown_method, test_validate_syntax_valid_python, test_validate_syntax_invalid_python, test_validate_syntax_mismatched_braces (+4 more)
- `TestRewriteWithValidation` - Line 743
  - Test rewrite_code tool with validation integration.
  - Methods: setup_method, teardown_method, test_rewrite_includes_validation_results, test_rewrite_warns_on_validation_failure

**Functions:**
- `mock_field() -> Any` - Line 41

**Key Imports:** `json`, `main`, `os`, `pytest`, `shutil` (+4 more)

### `test_schema.py` (python)

**Classes:**
- `TestSchemaOrgClient` - Line 140
  - Tests for SchemaOrgClient class.
  - Methods: setup_method, test_normalize_to_array, test_generate_example_value_text, test_generate_example_value_url, test_generate_example_value_date (+14 more)
- `TestSchemaOrgTools` - Line 679
  - Tests for Schema.org MCP tools.
  - Methods: setup_method, test_generate_entity_id_tool, test_validate_entity_id_tool
- `TestSchemaOrgClientHelpers` - Line 822
  - Tests for SchemaOrgClient helper methods.
  - Methods: setup_method, test_extract_super_types, test_extract_super_types_multiple, test_find_sub_types, test_format_property
- `TestGetSchemaOrgClient` - Line 909
  - Tests for get_schema_org_client singleton.
  - Methods: setup_method, test_get_schema_org_client_singleton, test_get_schema_org_client_creates_instance

**Key Imports:** `httpx`, `main`, `os`, `pytest`, `sys` (+1 more)

### `test_unit.py` (python)

**Classes:**
- `MockFastMCP` - Line 16
  - Mock FastMCP that returns functions unchanged
  - Methods: __init__, tool, run
- `TestDumpSyntaxTree` - Line 63
  - Test the dump_syntax_tree function
  - Methods: test_dump_syntax_tree_cst, test_dump_syntax_tree_pattern
- `TestTestMatchCodeRule` - Line 96
  - Test the test_match_code_rule function
  - Methods: test_match_found, test_no_match
- `TestFindCode` - Line 138
  - Test the find_code function
  - Methods: setup_method, test_text_format_with_results, test_text_format_no_results, test_text_format_with_max_results, test_json_format (+2 more)
- `TestFindCodeByRule` - Line 257
  - Test the find_code_by_rule function
  - Methods: setup_method, test_text_format_with_results, test_json_format
- `TestRunCommand` - Line 321
  - Test the run_command function
  - Methods: test_successful_command, test_command_failure, test_command_not_found
- `TestFormatMatchesAsText` - Line 358
  - Test the format_matches_as_text helper function
  - Methods: test_empty_matches, test_single_line_match, test_multi_line_match, test_multiple_matches
- `TestRunAstGrep` - Line 409
  - Test the run_ast_grep function
  - Methods: test_without_config, test_with_config
- `TestConfigValidation` - Line 447
  - Test the validate_config_file function
  - Methods: test_valid_config, test_invalid_config_extensions, test_invalid_config_empty_lists, test_config_file_not_found, test_config_file_is_directory (+3 more)
- `TestGetSupportedLanguages` - Line 526
  - Test the get_supported_languages function
  - Methods: test_without_config, test_with_custom_languages, test_with_nonexistent_config, test_with_config_exception
- `TestCustomLanguageConfig` - Line 598
  - Test CustomLanguageConfig Pydantic model
  - Methods: test_empty_extensions_list, test_valid_extensions
- `TestFormatMatchesEdgeCases` - Line 622
  - Test edge cases for format_matches_as_text
  - Methods: test_missing_file_field, test_missing_range_field, test_missing_text_field
- `TestFindCodeEdgeCases` - Line 659
  - Test edge cases for find_code function
  - Methods: test_find_code_with_language, test_find_code_without_language
- `TestFindCodeByRuleEdgeCases` - Line 704
  - Test edge cases for find_code_by_rule function
  - Methods: test_find_code_by_rule_no_results_text, test_find_code_by_rule_invalid_yaml_syntax, test_find_code_by_rule_invalid_output_format, test_find_code_by_rule_yaml_not_dict, test_find_code_by_rule_missing_id (+3 more)
- `TestValidateConfigFileErrors` - Line 855
  - Test error paths in validate_config_file
  - Methods: test_config_file_read_error
- `TestYAMLValidation` - Line 869
  - Test YAML validation in tools
  - Methods: test_invalid_yaml_structure, test_missing_id_field, test_missing_language_field, test_missing_rule_field, test_yaml_syntax_error_in_test_match
- `TestParseArgsAndGetConfig` - Line 932
  - Test parse_args_and_get_config function
  - Methods: test_no_config_provided, test_with_valid_config_flag, test_with_env_var_config

**Functions:**
- `mock_field() -> Any` - Line 39

**Key Imports:** `importlib`, `main`, `os`, `pydantic`, `pytest` (+4 more)

---
*Generated by Enhanced Schema Generator with schema.org markup*