# cross_language

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareSourceCode",
  "name": "cross_language",
  "description": "Directory containing 7 code files with 0 classes and 71 functions",
  "programmingLanguage": [
    {
      "@type": "ComputerLanguage",
      "name": "Python"
    }
  ],
  "featureList": [
    "71 function definitions"
  ]
}
</script>

## Overview

This directory contains 7 code file(s) with extracted schemas.

## Files and Schemas

### `binding_generator.py` (python)

**Functions:**
- `_to_camel_case(name) -> str` - Line 53
- `_to_pascal_case(name) -> str` - Line 59
- `_parse_parameter(param) -> Dict[...]` - Line 70
- `_parse_request_body(operation) -> Optional[...]` - Line 81
- `_parse_responses(operation) -> Dict[...]` - Line 91
- `_parse_operation(path, method, operation) -> Optional[...]` - Line 104
- `_parse_openapi_spec(spec) -> Tuple[...]` - Line 126
- `_load_api_spec(file_path) -> Tuple[...]` - Line 147
- `_parse_spec_content(content, suffix) -> Dict[...]` - Line 164
- `_classify_parameters(parameters, type_converter) -> Tuple[...]` - Line 187
- ... and 9 more functions

**Key Imports:** `ast_grep_mcp.core.logging`, `ast_grep_mcp.models.cross_language`, `json`, `pathlib`, `re` (+3 more)

### `language_converter.py` (python)

**Functions:**
- `_apply_patterns(code, patterns) -> Tuple[...]` - Line 167
- `_extract_type_hints(code, language) -> List[...]` - Line 199
- `_convert_types(code, type_mappings) -> Tuple[...]` - Line 225
- `_add_indentation_fixes(code, to_language) -> str` - Line 256
- `_generate_warnings(source_code, from_language, to_language, applied_patterns) -> List[...]` - Line 297
- `convert_code_language_impl(code_snippet, from_language, to_language, conversion_style, include_comments) -> ConversionResult` - Line 353

**Key Imports:** `ast_grep_mcp.core.logging`, `ast_grep_mcp.features.cross_language.pattern_database`, `ast_grep_mcp.models.cross_language`, `re`, `time` (+1 more)

### `multi_language_search.py` (python)

**Functions:**
- `_detect_semantic_group(snippet) -> str` - Line 130
- `_group_by_semantic(matches, semantic_query) -> List[...]` - Line 142
- `_detect_languages(project_folder) -> List[...]` - Line 157
- `_get_ast_grep_pattern(semantic, language) -> Optional[...]` - Line 171
- `_parse_match(match_data, language) -> MultiLanguageMatch` - Line 177
- `_search_language(project_folder, language, pattern, max_results) -> List[...]` - Line 189
- `_parse_semantic_query(query) -> str` - Line 256
- `search_multi_language_impl(project_folder, semantic_pattern, languages, group_by, max_results_per_language) -> MultiLanguageSearchResult` - Line 272

**Key Imports:** `ast_grep_mcp.core.executor`, `ast_grep_mcp.core.logging`, `ast_grep_mcp.models.cross_language`, `concurrent.futures`, `json` (+4 more)

### `pattern_database.py` (python)

**Functions:**
- `get_pattern(pattern_id) -> BinOp(left=Subscript(value=Name(id='Dict', ctx=Load(...)), slice=Tuple(elts=[Name(...), Name(...)], ctx=Load(...)), ctx=Load()), op=BitOr(), right=Constant(value=None, kind=None))` - Line 631
- `search_patterns(query, category) -> List[...]` - Line 643
- `get_equivalents(pattern_id, source_language, target_languages) -> BinOp(left=Subscript(value=Name(id='Dict', ctx=Load(...)), slice=Tuple(elts=[Name(...), Name(...)], ctx=Load(...)), ctx=Load()), op=BitOr(), right=Constant(value=None, kind=None))` - Line 671
- `get_type_mapping(from_lang, to_lang) -> Dict[...]` - Line 706

**Key Imports:** `typing`

### `pattern_equivalence.py` (python)

**Functions:**
- `_create_pattern_equivalence(pattern_id, pattern_data, target_languages) -> PatternEquivalence` - Line 25
- `_fuzzy_match_pattern(query) -> List[...]` - Line 88
- `_get_suggestions(found_patterns, category) -> List[...]` - Line 126
- `find_language_equivalents_impl(pattern_description, source_language, target_languages) -> PatternEquivalenceResult` - Line 165
- `list_pattern_categories() -> List[...]` - Line 237
- `get_pattern_details(pattern_id) -> Optional[...]` - Line 265

**Key Imports:** `ast_grep_mcp.core.logging`, `ast_grep_mcp.features.cross_language.pattern_database`, `ast_grep_mcp.models.cross_language`, `time`, `typing`

### `polyglot_refactoring.py` (python)

**Functions:**
- `_find_files_with_language(project_folder, languages) -> Dict[...]` - Line 86
- `_match_pattern_type(line, patterns, symbol) -> Optional[...]` - Line 110
- `_find_symbol_occurrences(file_path, symbol, language) -> List[...]` - Line 119
- `_create_rename_change(file_path, line_number, original_line, symbol, new_name, language) -> PolyglotChange` - Line 151
- `_collect_changes_for_file(file_path, symbol_name, new_name, language) -> List[...]` - Line 172
- `_collect_all_changes(files_by_language, symbol_name, new_name) -> List[...]` - Line 187
- `_analyze_risks(changes, symbol, new_name) -> List[...]` - Line 209
- `_identify_manual_review(project_folder, symbol, languages) -> List[...]` - Line 241
- `_apply_changes_to_file(file_path, file_changes) -> bool` - Line 267
- `_apply_changes(changes) -> List[...]` - Line 287
- ... and 4 more functions

**Key Imports:** `ast_grep_mcp.core.logging`, `ast_grep_mcp.models.cross_language`, `os`, `pathlib`, `re` (+2 more)

### `tools.py` (python)

**Functions:**
- `_format_example(ex) -> Dict[...]` - Line 39
- `_format_equivalence(e) -> Dict[...]` - Line 49
- `_format_equivalents_result(result) -> Dict[...]` - Line 62
- `_format_type_mapping(t) -> Dict[...]` - Line 74
- `_format_warning(w) -> Dict[...]` - Line 79
- `_format_conversion(c) -> Dict[...]` - Line 89
- `_format_conversion_result(result) -> Dict[...]` - Line 104
- `search_multi_language_tool(project_folder, semantic_pattern, languages, group_by, max_results_per_language) -> Dict[...]` - Line 120
- `find_language_equivalents_tool(pattern_description, source_language, target_languages) -> Dict[...]` - Line 241
- `convert_code_language_tool(code_snippet, from_language, to_language, conversion_style, include_comments) -> Dict[...]` - Line 333
- ... and 4 more functions

**Key Imports:** `ast_grep_mcp.core.logging`, `ast_grep_mcp.features.cross_language.binding_generator`, `ast_grep_mcp.features.cross_language.language_converter`, `ast_grep_mcp.features.cross_language.multi_language_search`, `ast_grep_mcp.features.cross_language.pattern_equivalence` (+7 more)

---
*Generated by Enhanced Schema Generator with schema.org markup*