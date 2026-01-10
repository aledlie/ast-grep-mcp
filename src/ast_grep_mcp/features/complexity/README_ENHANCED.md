# complexity

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareSourceCode",
  "name": "complexity",
  "description": "Directory containing 7 code files with 4 classes and 49 functions",
  "programmingLanguage": [
    {
      "@type": "ComputerLanguage",
      "name": "Python"
    }
  ],
  "featureList": [
    "4 class definitions",
    "49 function definitions"
  ]
}
</script>

## Overview

This directory contains 7 code file(s) with extracted schemas.

## Files and Schemas

### `analyzer.py` (python)

**Functions:**
- `extract_functions_from_file(file_path, language) -> List[...]` - Line 34
- `_extract_classes_from_file(file_path, language) -> List[...]` - Line 77
- `_get_class_extraction_pattern(language) -> str` - Line 98
- `_execute_ast_grep_for_classes(file_path, language, pattern) -> List[...]` - Line 116
- `_process_class_match_results(matches, language) -> List[...]` - Line 139
- `_extract_single_class_info(match, language) -> Dict[...]` - Line 156
- `_extract_class_name_from_match(match) -> str` - Line 174
- `_extract_class_line_range(match) -> Tuple[...]` - Line 199
- `_count_class_methods(code, language) -> int` - Line 214
- `_count_function_parameters(code, language) -> int` - Line 231
- ... and 6 more functions

**Key Imports:** `ast_grep_mcp.core.logging`, `ast_grep_mcp.models.complexity`, `json`, `metrics`, `re` (+2 more)

### `complexity_analyzer.py` (python)

**Classes:**
- `ParallelComplexityAnalyzer` - Line 15
  - Analyzes files in parallel for complexity metrics.
  - Methods: __init__, analyze_files, filter_exceeding_functions

**Key Imports:** `analyzer`, `concurrent.futures`, `core.logging`, `models.complexity`, `typing`

### `complexity_file_finder.py` (python)

**Classes:**
- `ComplexityFileFinder` - Line 14
  - Finds and filters files for complexity analysis.
  - Methods: __init__, find_files, _get_language_extensions, _find_matching_files, _filter_excluded_files

**Key Imports:** `core.logging`, `glob`, `pathlib`, `typing`

### `complexity_statistics.py` (python)

**Classes:**
- `ComplexityStatisticsAggregator` - Line 15
  - Aggregates statistics and formats complexity analysis results.
  - Methods: __init__, calculate_summary, get_git_info, store_results, get_trends (+1 more)

**Key Imports:** `core.logging`, `models.complexity`, `storage`, `subprocess`, `typing`

### `metrics.py` (python)

**Functions:**
- `get_complexity_patterns(language) -> Dict[...]` - Line 124
- `count_pattern_matches(code, pattern, language) -> int` - Line 140
- `_get_cyclomatic_config(language) -> Dict[...]` - Line 163
- `_count_occurrences(code, items) -> int` - Line 179
- `calculate_cyclomatic_complexity(code, language) -> int` - Line 195
- `_get_control_flow_keywords(language, patterns) -> List[...]` - Line 225
- `_calculate_line_indentation(line, base_indent) -> Tuple[...]` - Line 251
- `_is_comment_line(stripped) -> bool` - Line 278
- `_match_control_flow_keyword(stripped, control_flow) -> Optional[...]` - Line 290
- `_calculate_keyword_complexity(keyword, stripped, current_nesting) -> int` - Line 309
- ... and 7 more functions

**Key Imports:** `json`, `re`, `subprocess`, `typing`

### `storage.py` (python)

**Classes:**
- `ComplexityStorage` - Line 76
  - SQLite storage for complexity analysis results.
  - Methods: __init__, _get_default_db_path, _get_connection, _init_db, get_or_create_project (+2 more)

**Key Imports:** `ast_grep_mcp.models.complexity`, `contextlib`, `os`, `pathlib`, `platform` (+2 more)

### `tools.py` (python)

**Functions:**
- `_validate_inputs(language) -> Constant(value=None, kind=None)` - Line 29
- `_find_files_to_analyze(project_folder, language, include_patterns, exclude_patterns, logger) -> tuple[...]` - Line 43
- `_analyze_files_parallel(files_to_analyze, language, thresholds, max_threads) -> tuple[...]` - Line 66
- `_calculate_summary_statistics(all_functions, exceeding_functions, total_files, execution_time) -> tuple[...]` - Line 91
- `_store_and_generate_trends(store_results, include_trends, project_folder, summary, all_functions, statistics) -> tuple[...]` - Line 111
- `_format_response(summary, thresholds_dict, exceeding_functions, run_id, stored_at, trends, statistics) -> Dict[...]` - Line 145
- `_handle_no_files_found(language, execution_time) -> Dict[...]` - Line 171
- `_create_thresholds_dict(cyclomatic_threshold, cognitive_threshold, nesting_threshold, length_threshold) -> Dict[...]` - Line 188
- `_execute_analysis(project_folder, language, thresholds, files_to_analyze, store_results, include_trends, max_threads, start_time, logger) -> Dict[...]` - Line 210
- `analyze_complexity_tool(project_folder, language, include_patterns, exclude_patterns, cyclomatic_threshold, cognitive_threshold, nesting_threshold, length_threshold, store_results, include_trends, max_threads) -> Dict[...]` - Line 270
- ... and 6 more functions

**Key Imports:** `ast_grep_mcp.core.logging`, `ast_grep_mcp.features.quality.smells`, `ast_grep_mcp.models.complexity`, `complexity_analyzer`, `complexity_file_finder` (+6 more)

---
*Generated by Enhanced Schema Generator with schema.org markup*