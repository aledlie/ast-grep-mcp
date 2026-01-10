# quality

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareSourceCode",
  "name": "quality",
  "description": "Directory containing 11 code files with 9 classes and 98 functions",
  "programmingLanguage": [
    {
      "@type": "ComputerLanguage",
      "name": "Python"
    }
  ],
  "featureList": [
    "9 class definitions",
    "98 function definitions"
  ]
}
</script>

## Overview

This directory contains 11 code file(s) with extracted schemas.

## Files and Schemas

### `enforcer.py` (python)

**Functions:**
- `template_to_linting_rule(template) -> LintingRule` - Line 91
- `load_custom_rules(project_folder, language) -> List[...]` - Line 112
- `_load_rules_from_templates(rule_ids, language) -> List[...]` - Line 134
- `_load_all_rules(language, logger) -> RuleSet` - Line 153
- `_load_custom_rule_set(project_folder, language, logger) -> RuleSet` - Line 173
- `_load_builtin_rule_set(rule_set_name, language, logger) -> RuleSet` - Line 189
- `load_rule_set(rule_set_name, project_folder, language) -> RuleSet` - Line 216
- `parse_match_to_violation(match, rule) -> RuleViolation` - Line 247
- `should_exclude_file(file_path, exclude_patterns) -> bool` - Line 294
- `execute_rule(rule, context) -> List[...]` - Line 317
- ... and 10 more functions

**Key Imports:** `ast_grep_mcp.core.executor`, `ast_grep_mcp.core.logging`, `ast_grep_mcp.features.quality.rules`, `ast_grep_mcp.models.standards`, `concurrent.futures` (+7 more)

### `fixer.py` (python)

**Functions:**
- `classify_fix_safety(rule_id, violation) -> FixValidation` - Line 56
- `apply_pattern_fix(file_path, violation, fix_pattern, language) -> FixResult` - Line 93
- `_apply_fix_pattern(code, fix_pattern, meta_vars) -> str` - Line 197
- `apply_removal_fix(file_path, violation, language) -> FixResult` - Line 217
- `apply_fixes_batch(violations, language, project_folder, fix_types, dry_run, create_backup_flag) -> FixBatchResult` - Line 305
- `_execute_dry_run(fixable_violations, start_time) -> FixBatchResult` - Line 353
- `_create_backup_if_needed(fixable_violations, project_folder, create_backup_flag) -> Optional[...]` - Line 394
- `_group_violations_by_file(fixable_violations) -> Dict[...]` - Line 419
- `_execute_real_run(violations_by_file, language) -> Tuple[...]` - Line 436
- `_apply_single_fix(file_path, violation, language) -> FixResult` - Line 470
- ... and 4 more functions

**Key Imports:** `ast_grep_mcp.core.logging`, `ast_grep_mcp.features.rewrite.backup`, `ast_grep_mcp.features.rewrite.service`, `ast_grep_mcp.models.standards`, `sentry_sdk` (+2 more)

### `orphan_detector.py` (python)

**Classes:**
- `OrphanDetector` - Line 27
  - Detects orphan files and functions in a codebase.
  - Methods: __init__, analyze, _build_dependency_graph, _should_exclude, _extract_python_imports (+14 more)

**Functions:**
- `detect_orphans_impl(project_folder, include_patterns, exclude_patterns, analyze_functions, verify_with_grep) -> Dict[...]` - Line 567

**Key Imports:** `ast`, `ast_grep_mcp.core.logging`, `ast_grep_mcp.models.orphan`, `fnmatch`, `pathlib` (+4 more)

### `reporter.py` (python)

**Functions:**
- `_generate_report_header(project_name, result) -> List[...]` - Line 25
- `_generate_summary_section(result) -> List[...]` - Line 44
- `_format_violation_entry(violation) -> str` - Line 66
- `_generate_rule_violations_section(rule_id, rule_violations, include_violations, max_violations_per_rule) -> List[...]` - Line 79
- `_generate_violations_by_severity_section(result, include_violations, max_violations_per_rule) -> List[...]` - Line 114
- `_get_most_common_severity(violations) -> str` - Line 151
- `_generate_top_issues_table(result) -> List[...]` - Line 164
- `_count_violations_by_severity(violations) -> tuple[...]` - Line 185
- `_generate_problematic_files_table(result) -> List[...]` - Line 200
- `_generate_recommendations_section(result) -> List[...]` - Line 228
- ... and 3 more functions

**Key Imports:** `ast_grep_mcp.core.logging`, `ast_grep_mcp.models.standards`, `datetime`, `json`, `pathlib` (+1 more)

### `rules.py` (python)

**Functions:**
- `get_available_templates(language, category) -> List[...]` - Line 309
- `create_rule_from_template(template_id, rule_id, overrides) -> LintingRule` - Line 330
- `save_rule_to_project(rule, project_folder) -> str` - Line 363
- `load_rule_from_file(file_path) -> LintingRule` - Line 407
- `load_rules_from_project(project_folder) -> List[...]` - Line 449
- `delete_rule_from_project(rule_id, project_folder) -> bool` - Line 478

**Key Imports:** `ast_grep_mcp.core.logging`, `ast_grep_mcp.models.standards`, `pathlib`, `sentry_sdk`, `typing` (+1 more)

### `security_scanner.py` (python)

**Functions:**
- `scan_for_vulnerability(project_folder, language, patterns) -> List[...]` - Line 290
- `scan_for_secrets_regex(project_folder, language) -> List[...]` - Line 340
- `_get_language_extensions(language) -> List[...]` - Line 364
- `_should_skip_file(file_path) -> bool` - Line 377
- `_scan_files_for_secrets(project_path, ext) -> List[...]` - Line 390
- `_scan_single_file_for_secrets(file_path) -> List[...]` - Line 412
- `_scan_lines_for_pattern(lines, pattern_def, file_path) -> List[...]` - Line 439
- `_create_secret_issue(file_path, line_num, line, match, pattern_def) -> SecurityIssue` - Line 462
- `_scan_for_issue_type(issue_type, config, project_folder, language) -> List[...]` - Line 497
- `_filter_by_severity(issues, severity_threshold, max_issues) -> List[...]` - Line 531
- ... and 3 more functions

**Key Imports:** `ast_grep_mcp.core.executor`, `ast_grep_mcp.core.logging`, `ast_grep_mcp.models.standards`, `copy`, `pathlib` (+4 more)

### `smells.py` (python)

**Functions:**
- `detect_code_smells_impl(project_folder, language, include_patterns, exclude_patterns, long_function_lines, parameter_count, nesting_depth, class_lines, class_methods, detect_magic_numbers, severity_filter, max_threads) -> Dict[...]` - Line 33
- `_create_detectors(long_function_lines, parameter_count, nesting_depth, class_lines, class_methods, detect_magic_numbers) -> List[...]` - Line 116

**Key Imports:** `ast_grep_mcp.core.logging`, `ast_grep_mcp.features.quality.smells_detectors`, `ast_grep_mcp.features.quality.smells_helpers`, `concurrent.futures`, `typing`

### `smells_detectors.py` (python)

**Classes:**
- `SmellInfo` - Line 21
  - Information about a detected code smell.
  - Methods: to_dict
- `SmellDetector` (extends: ABC) - Line 49
  - Base class for smell detectors.
  - Methods: detect
- `LongFunctionDetector` (extends: SmellDetector) - Line 68
  - Detects functions that are too long.
  - Methods: __init__, detect
- `ParameterBloatDetector` (extends: SmellDetector) - Line 116
  - Detects functions with too many parameters.
  - Methods: __init__, detect, _count_parameters
- `DeepNestingDetector` (extends: SmellDetector) - Line 202
  - Detects excessive nesting depth in functions.
  - Methods: __init__, detect
- `LargeClassDetector` (extends: SmellDetector) - Line 251
  - Detects classes that are too large.
  - Methods: __init__, detect, _extract_classes, _get_class_pattern, _run_ast_grep_for_classes (+5 more)
- `MagicNumberDetector` (extends: SmellDetector) - Line 456
  - Detects magic numbers in code.
  - Methods: __init__, detect, _find_magic_numbers
- `SmellAnalyzer` - Line 548
  - Orchestrates smell detection across files.
  - Methods: __init__, analyze_file

**Key Imports:** `abc`, `ast_grep_mcp.core.logging`, `ast_grep_mcp.features.complexity.analyzer`, `ast_grep_mcp.features.quality.smells_helpers`, `dataclasses` (+5 more)

### `smells_helpers.py` (python)

**Functions:**
- `validate_smell_detection_inputs(project_folder, language, severity_filter) -> tuple[...]` - Line 14
- `find_smell_analysis_files(project_path, file_ext, include_patterns, exclude_patterns) -> List[...]` - Line 51
- `calculate_smell_severity(metric, threshold, smell_type) -> str` - Line 101
- `format_smell_detection_response(project_folder, language, files_analyzed, smells, thresholds, severity_filter) -> Dict[...]` - Line 141
- `aggregate_smell_results(file_results) -> List[...]` - Line 185

**Key Imports:** `ast_grep_mcp.core.logging`, `fnmatch`, `pathlib`, `typing`

### `tools.py` (python)

**Functions:**
- `_create_rule_from_params(rule_name, description, pattern, severity, language, suggested_fix, note, use_template) -> LintingRule` - Line 38
- `_save_rule_if_requested(rule, save_to_project, project_folder, validation_result) -> Optional[...]` - Line 67
- `_format_rule_result(rule, validation_result, saved_path) -> Dict[...]` - Line 84
- `create_linting_rule_tool(rule_name, description, pattern, severity, language, suggested_fix, note, save_to_project, project_folder, use_template) -> Dict[...]` - Line 106
- `list_rule_templates_tool(language, category) -> Dict[...]` - Line 206
- `_get_default_exclude_patterns() -> List[...]` - Line 290
- `_validate_enforcement_inputs(severity_threshold, output_format) -> Constant(value=None, kind=None)` - Line 305
- `_format_enforcement_output(result, output_format) -> Dict[...]` - Line 322
- `enforce_standards_tool(project_folder, language, rule_set, custom_rules, include_patterns, exclude_patterns, severity_threshold, max_violations, max_threads, output_format) -> Dict[...]` - Line 361
- `_convert_violations_to_objects(violations) -> List[...]` - Line 474
- ... and 11 more functions

**Key Imports:** `ast_grep_mcp.core.logging`, `ast_grep_mcp.features.quality.enforcer`, `ast_grep_mcp.features.quality.fixer`, `ast_grep_mcp.features.quality.orphan_detector`, `ast_grep_mcp.features.quality.reporter` (+11 more)

### `validator.py` (python)

**Functions:**
- `validate_rule_pattern(pattern, language) -> RuleValidationResult` - Line 20
- `validate_rule_definition(rule) -> RuleValidationResult` - Line 71
- `validate_linting_rules_impl(rules, fail_fast) -> Dict[...]` - Line 127

**Key Imports:** `ast_grep_mcp.core.executor`, `ast_grep_mcp.core.logging`, `ast_grep_mcp.models.standards`, `re`, `sentry_sdk` (+2 more)

---
*Generated by Enhanced Schema Generator with schema.org markup*