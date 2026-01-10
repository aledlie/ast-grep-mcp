# documentation

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareSourceCode",
  "name": "documentation",
  "description": "Directory containing 6 code files with 5 classes and 89 functions",
  "programmingLanguage": [
    {
      "@type": "ComputerLanguage",
      "name": "Python"
    }
  ],
  "featureList": [
    "5 class definitions",
    "89 function definitions"
  ]
}
</script>

## Overview

This directory contains 6 code file(s) with extracted schemas.

## Files and Schemas

### `api_docs_generator.py` (python)

**Classes:**
- `RouteParser` (extends: Protocol) - Line 125
  - Protocol for route parsers.
  - Methods: parse_file
- `ExpressRouteParser` - Line 133
  - Parse Express.js routes.
  - Methods: parse_file, _extract_path_params
- `FastAPIRouteParser` - Line 188
  - Parse FastAPI routes.
  - Methods: parse_file, _extract_path_params, _extract_params
- `FlaskRouteParser` - Line 302
  - Parse Flask routes.
  - Methods: parse_file, _extract_path_params

**Functions:**
- `_detect_js_api_framework(project_folder) -> Optional[...]` - Line 47
- `_detect_python_api_framework(project_folder) -> Optional[...]` - Line 73
- `_detect_framework(project_folder, language) -> Optional[...]` - Line 101
- `_generate_markdown_docs(routes, framework) -> str` - Line 385
- `_build_openapi_param(param) -> Dict[...]` - Line 457
- `_build_openapi_request_body(body_params) -> Dict[...]` - Line 477
- `_build_openapi_operation(route) -> Dict[...]` - Line 499
- `_generate_openapi_spec(routes, project_name) -> Dict[...]` - Line 529
- `_find_route_files(project_folder, language, framework) -> List[...]` - Line 558
- `generate_api_docs_impl(project_folder, language, framework, output_format, include_examples) -> ApiDocsResult` - Line 614

**Key Imports:** `ast_grep_mcp.core.logging`, `ast_grep_mcp.models.documentation`, `json`, `os`, `re` (+3 more)

### `changelog_generator.py` (python)

**Functions:**
- `_run_git_command(project_folder, args) -> Tuple[...]` - Line 31
- `_get_commit_range(project_folder, from_version, to_version) -> Tuple[...]` - Line 56
- `_get_commits(project_folder, from_ref, to_ref) -> List[...]` - Line 116
- `_parse_conventional_commit(subject, body) -> Dict[...]` - Line 183
- `_map_commit_type_to_change_type(commit_type) -> ChangeType` - Line 233
- `_group_commits_by_version(commits, project_folder, to_version) -> List[...]` - Line 273
- `_format_changelog_entry(entry) -> str` - Line 355
- `_format_keepachangelog_version(version) -> List[...]` - Line 390
- `_format_keepachangelog(versions, project_name) -> str` - Line 422
- `_format_conventional_entry(entry) -> str` - Line 467
- ... and 3 more functions

**Key Imports:** `ast_grep_mcp.core.logging`, `ast_grep_mcp.models.documentation`, `datetime`, `os`, `re` (+3 more)

### `docstring_generator.py` (python)

**Classes:**
- `FunctionSignatureParser` - Line 474
  - Parse function signatures from source code.
  - Methods: __init__, parse_file, _parse_python_functions, _parse_python_params, _parse_single_python_param (+6 more)

**Functions:**
- `_split_camel_case(name) -> List[...]` - Line 31
- `_split_snake_case(name) -> List[...]` - Line 47
- `_infer_description_from_name(name) -> str` - Line 59
- `_check_suffix_pattern(name) -> Optional[...]` - Line 341
- `_check_prefix_pattern(name) -> Optional[...]` - Line 350
- `_infer_parameter_description(param, function_context) -> str` - Line 359
- `_get_return_from_type(return_type) -> str` - Line 421
- `_infer_return_description(return_type, function_name) -> str` - Line 430
- `_generate_google_docstring(func) -> str` - Line 849
- `_generate_numpy_docstring(func) -> str` - Line 880
- ... and 10 more functions

**Key Imports:** `ast_grep_mcp.core.logging`, `ast_grep_mcp.models.documentation`, `glob`, `os`, `re` (+3 more)

### `readme_generator.py` (python)

**Functions:**
- `_parse_json_metadata(file_path) -> Tuple[...]` - Line 30
- `_parse_toml_metadata(file_path) -> Tuple[...]` - Line 40
- `_parse_go_mod(file_path) -> Tuple[...]` - Line 52
- `_detect_js_package_manager(project_folder) -> str` - Line 63
- `_detect_python_package_manager(project_folder) -> str` - Line 72
- `_detect_package_manager(project_folder) -> Tuple[...]` - Line 81
- `_detect_language(project_folder) -> str` - Line 129
- `_detect_js_frameworks(project_folder) -> List[...]` - Line 209
- `_get_python_deps_content(project_folder) -> str` - Line 238
- `_detect_python_frameworks(project_folder) -> List[...]` - Line 261
- ... and 16 more functions

**Key Imports:** `ast_grep_mcp.core.logging`, `ast_grep_mcp.models.documentation`, `json`, `os`, `re` (+3 more)

### `sync_checker.py` (python)

**Functions:**
- `_extract_python_docstring_params(docstring) -> List[...]` - Line 31
- `_extract_js_docstring_params(docstring) -> List[...]` - Line 67
- `_extract_docstring_params(docstring, language) -> List[...]` - Line 79
- `_extract_docstring_return(docstring, language) -> bool` - Line 96
- `_check_docstring_sync(func, language) -> List[...]` - Line 130
- `_check_markdown_links(file_path, project_folder) -> List[...]` - Line 233
- `_find_source_files(project_folder, language, include_patterns, exclude_patterns) -> List[...]` - Line 295
- `_find_markdown_files(project_folder) -> List[...]` - Line 362
- `_check_function_docstring(func, language) -> Tuple[...]` - Line 388
- `_check_docstrings_in_files(project_folder, language, include_patterns, exclude_patterns) -> Tuple[...]` - Line 421
- ... and 2 more functions

**Key Imports:** `ast_grep_mcp.core.logging`, `ast_grep_mcp.models.documentation`, `docstring_generator`, `glob`, `os` (+4 more)

### `tools.py` (python)

**Functions:**
- `generate_docstrings_tool(project_folder, file_pattern, language, style, overwrite_existing, dry_run, skip_private) -> Dict[...]` - Line 31
- `generate_readme_sections_tool(project_folder, language, sections, include_examples) -> Dict[...]` - Line 165
- `_format_route_for_output(route) -> Dict[...]` - Line 281
- `generate_api_docs_tool(project_folder, language, framework, output_format, include_examples) -> Dict[...]` - Line 300
- `generate_changelog_tool(project_folder, from_version, to_version, changelog_format, group_by) -> Dict[...]` - Line 416
- `sync_documentation_tool(project_folder, language, doc_types, check_only) -> Dict[...]` - Line 558
- `_create_mcp_field_definitions() -> Dict[...]` - Line 693
- `register_documentation_tools(mcp) -> Constant(value=None, kind=None)` - Line 737

**Key Imports:** `ast_grep_mcp.core.logging`, `ast_grep_mcp.features.documentation.api_docs_generator`, `ast_grep_mcp.features.documentation.changelog_generator`, `ast_grep_mcp.features.documentation.docstring_generator`, `ast_grep_mcp.features.documentation.readme_generator` (+7 more)

---
*Generated by Enhanced Schema Generator with schema.org markup*