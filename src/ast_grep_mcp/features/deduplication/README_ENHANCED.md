# deduplication

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareSourceCode",
  "name": "deduplication",
  "description": "Directory containing 24 code files with 36 classes and 44 functions",
  "programmingLanguage": [
    {
      "@type": "ComputerLanguage",
      "name": "Python"
    }
  ],
  "featureList": [
    "36 class definitions",
    "44 function definitions"
  ]
}
</script>

## Overview

This directory contains 24 code file(s) with extracted schemas.

## Files and Schemas

### `analysis_orchestrator.py` (python)

**Classes:**
- `DeduplicationAnalysisOrchestrator` - Line 24
  - Orchestrates the complete deduplication candidate analysis workflow.
  - Methods: __init__, detector, detector, ranker, ranker (+23 more)

**Key Imports:** `concurrent.futures`, `config`, `constants`, `core.logging`, `coverage` (+5 more)

### `analyzer.py` (python)

**Classes:**
- `PatternAnalyzer` - Line 20
  - Analyzes patterns and variations in duplicate code.
  - Methods: __init__, identify_varying_literals, _extract_literals_with_ast_grep, analyze_duplicate_group_literals, classify_variation (+21 more)

**Functions:**
- `detect_conditional_variations(code1, code2, language) -> List[...]` - Line 861
- `_detect_nested_function_call(code, identifier, language) -> Optional[...]` - Line 880
- `classify_variations(code1, code2, language) -> Dict[...]` - Line 901
- `identify_varying_identifiers(code1, code2, language) -> List[...]` - Line 991
- `_extract_identifiers_from_code(code, language) -> Dict[...]` - Line 1029

**Key Imports:** `core.logging`, `json`, `models.deduplication`, `os`, `re` (+4 more)

### `applicator.py` (python)

**Classes:**
- `DeduplicationApplicator` - Line 16
  - Applies deduplication refactoring with backup and validation.
  - Methods: __init__, apply_deduplication, _validate_and_prepare_plan, _extract_plan_components, _perform_pre_validation (+13 more)

**Functions:**
- `_get_applicator() -> Any` - Line 638
- `_plan_file_modification_order(files_to_modify, generated_code, extract_to_file, project_folder, language) -> Dict[...]` - Line 646
- `_add_import_to_content(content, import_statement, language) -> str` - Line 655
- `_generate_import_for_extracted_function(source_file, target_file, function_name, language, project_folder) -> str` - Line 662

**Key Imports:** `applicator_backup`, `applicator_executor`, `applicator_post_validator`, `applicator_validator`, `core.logging` (+3 more)

### `applicator_backup.py` (python)

**Classes:**
- `DeduplicationBackupManager` - Line 18
  - Manages backups for deduplication operations.
  - Methods: __init__, create_backup, rollback, cleanup_old_backups, get_file_hash (+1 more)

**Key Imports:** `core.logging`, `datetime`, `hashlib`, `json`, `os` (+3 more)

### `applicator_executor.py` (python)

**Classes:**
- `RefactoringExecutor` - Line 13
  - Executes the actual code modifications for refactoring.
  - Methods: __init__, apply_changes, _create_files, _update_files, _find_python_import_location (+7 more)

**Key Imports:** `core.logging`, `os`, `typing`

### `applicator_post_validator.py` (python)

**Classes:**
- `PostValidationResult` - Line 14
  - Result of post-validation operation.
  - Methods: __init__, to_dict
- `RefactoringPostValidator` - Line 36
  - Validates files after refactoring modifications.
  - Methods: __init__, validate_modified_files, _validate_file_syntax, _validate_file_structure, _validate_python_structure (+2 more)

**Key Imports:** `core.logging`, `os`, `rewrite.service`, `typing`, `utils.syntax_validation`

### `applicator_validator.py` (python)

**Classes:**
- `ValidationResult` - Line 14
  - Result of validation operation.
  - Methods: __init__, to_dict
- `RefactoringPlanValidator` - Line 32
  - Validates refactoring plans before application.
  - Methods: __init__, validate_plan, _validate_required_fields, _validate_files_exist, _validate_code_syntax

**Key Imports:** `core.logging`, `pathlib`, `typing`, `utils.syntax_validation`

### `benchmark.py` (python)

**Classes:**
- `DeduplicationBenchmark` - Line 12
  - Runs performance benchmarks for deduplication functions.
  - Methods: __init__, benchmark_deduplication

**Functions:**
- `benchmark_deduplication(iterations, save_baseline, check_regression) -> Dict[...]` - Line 80

**Key Imports:** `benchmark_executor`, `benchmark_reporter`, `core.logging`, `regression_detector`, `time` (+1 more)

### `benchmark_executor.py` (python)

**Classes:**
- `BenchmarkExecutor` - Line 17
  - Executes timed benchmarks and collects statistics.
  - Methods: __init__, run_timed_benchmark, benchmark_scoring, benchmark_pattern_analysis, benchmark_code_generation (+2 more)

**Key Imports:** `core.logging`, `ranker`, `recommendations`, `reporting`, `statistics` (+2 more)

### `benchmark_reporter.py` (python)

**Classes:**
- `BenchmarkReporter` - Line 15
  - Generates benchmark reports and manages baselines.
  - Methods: __init__, format_benchmark_report, save_baseline, load_baseline

**Key Imports:** `core.logging`, `json`, `os`, `time`, `typing`

### `config.py` (python)

**Classes:**
- `AnalysisConfig` - Line 12
  - Configuration for deduplication candidate analysis.
  - Methods: __post_init__, to_dict

**Key Imports:** `dataclasses`, `typing`

### `coverage.py` (python)

**Classes:**
- `CoverageDetector` - Line 61
  - Detects test coverage for source files to assess refactoring risk.
  - Methods: __init__, find_test_file_patterns, _get_potential_test_paths, _read_file_content, _check_import_patterns (+12 more)

**Functions:**
- `_get_javascript_patterns(source_name) -> List[...]` - Line 24
- `_get_ruby_patterns(source_name) -> List[...]` - Line 34
- `find_test_file_patterns(language) -> List[...]` - Line 645
- `has_test_coverage(file_path, language, project_root) -> bool` - Line 650
- `get_test_coverage_for_files(file_paths, language, project_root) -> Dict[...]` - Line 655
- `check_test_file_references_source(test_file_path, source_file_path, language) -> bool` - Line 660
- `get_potential_test_paths(file_path, language, project_root) -> List[...]` - Line 681

**Key Imports:** `concurrent.futures`, `core.logging`, `glob`, `os`, `re` (+1 more)

### `detector.py` (python)

**Classes:**
- `DuplicationDetector` - Line 38
  - Core duplication detection functionality.
  - Methods: __init__, find_duplication, _validate_parameters, _get_construct_pattern, _find_constructs (+19 more)

**Key Imports:** `core.executor`, `core.logging`, `core.usage_tracking`, `difflib`, `similarity` (+2 more)

### `diff.py` (python)

**Functions:**
- `build_nested_diff_tree(code1, code2, language) -> dict[...]` - Line 13
- `build_diff_tree(code1, code2, language) -> dict[...]` - Line 108
- `format_alignment_diff(diff_data) -> BinOp(left=Name(id='str', ctx=Load()), op=BitOr(), right=Subscript(value=Name(id='dict', ctx=Load(...)), slice=Tuple(elts=[Name(...), Name(...)], ctx=Load(...)), ctx=Load()))` - Line 158
- `diff_preview_to_dict(diff_text) -> dict[...]` - Line 228
- `generate_file_diff(old_content, new_content, filename) -> str` - Line 300
- `generate_multi_file_diff(changes) -> str` - Line 329
- `generate_diff_from_file_paths(old_path, new_path) -> str` - Line 352

**Key Imports:** `difflib`, `pathlib`, `re`, `typing`

### `generator.py` (python)

**Classes:**
- `CodeGenerator` - Line 211
  - Generates refactored code for deduplication.
  - Methods: __init__, _generate_python_function, _generate_js_ts_function, _generate_java_function, _generate_generic_function (+26 more)

**Functions:**
- `_infer_from_identifier_name(identifier, language) -> str` - Line 113
- `_infer_single_value_type(value, language) -> str` - Line 141
- `generate_parameter_name(identifier, all_identifiers) -> str` - Line 942
- `infer_parameter_type(identifier, context, language) -> str` - Line 993

**Key Imports:** `core.logging`, `models.deduplication`, `re`, `time`, `typing` (+1 more)

### `impact.py` (python)

**Classes:**
- `_RiskLevelConfig` (extends: TypedDict) - Line 20
  - Type definition for risk level configuration.
- `ImpactAnalyzer` - Line 27
  - Analyzes the impact of applying deduplication to code.
  - Methods: __init__, analyze_deduplication_impact, _extract_function_names_from_code, _get_language_patterns, _apply_extraction_patterns (+17 more)

**Functions:**
- `analyze_deduplication_impact(duplicate_group, project_root, language) -> Dict[...]` - Line 691
- `estimate_lines_changed(duplicate_count, lines_per_duplicate, external_call_sites) -> Dict[...]` - Line 697

**Key Imports:** `core`, `core.logging`, `json`, `os`, `re` (+2 more)

### `priority_classifier.py` (python)

**Classes:**
- `DeduplicationPriorityClassifier` - Line 12
  - Classifies deduplication candidates by priority and generates recommendations.
  - Methods: __init__, get_priority_label, get_score_breakdown, get_recommendation, classify_batch

**Key Imports:** `core.logging`, `typing`

### `ranker.py` (python)

**Classes:**
- `DuplicationRanker` - Line 17
  - Ranks duplication candidates by refactoring value with score caching.
  - Methods: __init__, _generate_cache_key, clear_cache, get_cache_stats, calculate_deduplication_score (+1 more)

**Functions:**
- `get_ranker() -> DuplicationRanker` - Line 211
- `rank_deduplication_candidates(candidates, max_results) -> List[...]` - Line 223

**Key Imports:** `core.logging`, `hashlib`, `json`, `priority_classifier`, `score_calculator` (+1 more)

### `recommendations.py` (python)

**Classes:**
- `RecommendationEngine` - Line 51
  - Generates actionable recommendations for deduplication candidates.
  - Methods: generate_deduplication_recommendation, _calculate_strategy_score, _build_strategy_dict, _generate_dedup_refactoring_strategies

**Functions:**
- `generate_deduplication_recommendation(score, complexity, lines_saved, has_tests, affected_files) -> Dict[...]` - Line 228
- `generate_refactoring_suggestions(duplicates, language) -> List[...]` - Line 236

**Key Imports:** `typing`

### `regression_detector.py` (python)

**Classes:**
- `RegressionDetector` - Line 13
  - Detects performance regressions in benchmark results.
  - Methods: __init__, check_regressions, _check_single_regression, set_threshold, get_thresholds

**Key Imports:** `constants`, `core.logging`, `typing`

### `reporting.py` (python)

**Classes:**
- `EnhancedDuplicationCandidate` - Line 11
  - Enhanced duplication candidate with full reporting details.
- `DuplicationReporter` - Line 43
  - Creates enhanced reports for code duplication findings.
  - Methods: format_diff_with_colors, generate_before_after_example, visualize_complexity, create_enhanced_duplication_response

**Functions:**
- `format_diff_with_colors(diff) -> str` - Line 360
- `generate_before_after_example(original_code, replacement_code, function_name) -> Dict[...]` - Line 365
- `visualize_complexity(score) -> Dict[...]` - Line 370
- `create_enhanced_duplication_response(candidates, include_diffs, include_colors) -> Dict[...]` - Line 375

**Key Imports:** `dataclasses`, `datetime`, `typing`, `utils.formatters`

### `score_calculator.py` (python)

**Classes:**
- `DeduplicationScoreCalculator` - Line 13
  - Calculates component scores for deduplication priority.
  - Methods: __init__, calculate_total_score, calculate_savings_score, calculate_complexity_score, calculate_risk_score (+1 more)

**Key Imports:** `constants`, `core.logging`, `typing`

### `similarity.py` (python)

**Classes:**
- `SimilarityConfig` - Line 43
  - Configuration for MinHash similarity calculation.
- `SimilarityResult` - Line 86
  - Result of a similarity calculation.
- `HybridSimilarityConfig` - Line 106
  - Configuration for hybrid two/three-stage similarity pipeline.
  - Methods: __post_init__
- `HybridSimilarityResult` - Line 179
  - Result of hybrid two/three-stage similarity calculation.
  - Methods: to_dict
- `MinHashSimilarity` - Line 245
  - MinHash-based similarity calculator for code clone detection.
  - Methods: __init__, create_minhash, estimate_similarity, calculate_similarity, build_lsh_index (+12 more)
- `HybridSimilarity` - Line 695
  - Hybrid two/three-stage similarity calculator combining MinHash, AST, and CodeBERT.
  - Methods: __init__, _get_semantic_calculator, calculate_hybrid_similarity, _calculate_with_semantic, _calculate_ast_similarity (+5 more)
- `SimilarityBucket` - Line 1176
  - A bucket of potentially similar code items.
- `EnhancedStructureHash` - Line 1184
  - Improved structure hash algorithm using AST-like node sequence patterns.
  - Methods: __init__, calculate, _extract_node_sequence, _calculate_control_flow_complexity, _extract_call_signature (+4 more)
- `SemanticSimilarityConfig` - Line 1587
  - Configuration for CodeBERT-based semantic similarity.
- `SemanticSimilarityResult` - Line 1620
  - Result of semantic similarity calculation using CodeBERT.
  - Methods: to_dict
- `SemanticSimilarity` - Line 1657
  - CodeBERT-based semantic similarity calculator for Type-4 clone detection.
  - Methods: __init__, is_available, _load_model, _select_device, get_embedding (+4 more)

**Functions:**
- `_check_transformers_available() -> bool` - Line 1562

**Key Imports:** `constants`, `core.logging`, `dataclasses`, `datasketch`, `difflib` (+5 more)

### `tools.py` (python)

**Functions:**
- `find_duplication_tool(project_folder, language, min_similarity, min_lines, exclude_patterns) -> Dict[...]` - Line 17
- `analyze_deduplication_candidates_tool(project_path, language, min_similarity, include_test_coverage, min_lines, max_candidates, exclude_patterns) -> Dict[...]` - Line 58
- `apply_deduplication_tool(project_folder, group_id, refactoring_plan, dry_run, backup, extract_to_file) -> Dict[...]` - Line 119
- `benchmark_deduplication_tool(iterations, save_baseline, check_regression) -> Dict[...]` - Line 172
- `register_deduplication_tools(mcp) -> Any` - Line 208

**Key Imports:** `analysis_orchestrator`, `applicator`, `benchmark`, `core.logging`, `detector` (+2 more)

---
*Generated by Enhanced Schema Generator with schema.org markup*