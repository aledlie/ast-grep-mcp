# core

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareSourceCode",
  "name": "core",
  "description": "Directory containing 7 code files with 17 classes and 34 functions",
  "programmingLanguage": [
    {
      "@type": "ComputerLanguage",
      "name": "Python"
    }
  ],
  "featureList": [
    "17 class definitions",
    "34 function definitions"
  ]
}
</script>

## Overview

This directory contains 7 code file(s) with extracted schemas.

## Files and Schemas

### `cache.py` (python)

**Classes:**
- `QueryCache` - Line 11
  - Simple LRU cache with TTL for ast-grep query results.
  - Methods: __init__, _make_key, get, put, clear (+1 more)

**Functions:**
- `get_query_cache() -> Optional[...]` - Line 126
- `init_query_cache(max_size, ttl_seconds) -> Constant(value=None, kind=None)` - Line 133

**Key Imports:** `ast_grep_mcp.constants`, `ast_grep_mcp.core.config`, `collections`, `hashlib`, `time` (+1 more)

### `config.py` (python)

**Functions:**
- `validate_config_file(config_path) -> AstGrepConfig` - Line 27
- `_create_argument_parser() -> argparse.ArgumentParser` - Line 67
- `_resolve_and_validate_config_path(args) -> Optional[...]` - Line 139
- `_configure_logging_from_args(args) -> Constant(value=None, kind=None)` - Line 177
- `_configure_cache_from_args(args) -> tuple[...]` - Line 195
- `parse_args_and_get_config() -> Constant(value=None, kind=None)` - Line 243

**Key Imports:** `argparse`, `ast_grep_mcp.constants`, `ast_grep_mcp.core.exceptions`, `ast_grep_mcp.core.logging`, `ast_grep_mcp.models.config` (+4 more)

### `exceptions.py` (python)

**Classes:**
- `AstGrepError` (extends: Exception) - Line 6
  - Base exception for all ast-grep MCP server errors.
- `AstGrepNotFoundError` (extends: AstGrepError) - Line 12
  - Raised when ast-grep binary is not found in PATH.
  - Methods: __init__
- `InvalidYAMLError` (extends: AstGrepError) - Line 26
  - Raised when YAML rule is invalid or malformed.
  - Methods: __init__
- `ConfigurationError` (extends: AstGrepError) - Line 45
  - Raised when configuration file is invalid.
  - Methods: __init__
- `AstGrepExecutionError` (extends: AstGrepError) - Line 54
  - Raised when ast-grep command execution fails.
  - Methods: __init__
- `NoMatchesError` (extends: AstGrepError) - Line 70
  - Raised when no matches are found (for test_match_code_rule only).
  - Methods: __init__
- `RuleValidationError` (extends: Exception) - Line 82
  - Raised when a linting rule validation fails.
- `RuleStorageError` (extends: Exception) - Line 88
  - Raised when a linting rule cannot be stored.

**Key Imports:** `typing`

### `executor.py` (python)

**Functions:**
- `get_supported_languages() -> List[...]` - Line 22
- `run_command(args, input_text) -> subprocess.CompletedProcess[...]` - Line 68
- `_get_language_extensions(language) -> Optional[...]` - Line 155
- `_should_skip_directory(dirname) -> bool` - Line 181
- `_process_file(file, root, lang_extensions, max_size_bytes, logger) -> Tuple[...]` - Line 195
- `filter_files_by_size(directory, max_size_mb, language) -> Tuple[...]` - Line 239
- `run_ast_grep(command, args, input_text) -> subprocess.CompletedProcess[...]` - Line 290
- `_prepare_stream_command(command, args) -> List[...]` - Line 306
- `_create_stream_process(full_command) -> subprocess.Popen[...]` - Line 322
- `_parse_json_line(line, logger) -> Optional[...]` - Line 338
- ... and 5 more functions

**Key Imports:** `ast_grep_mcp.constants`, `ast_grep_mcp.core.config`, `ast_grep_mcp.core.exceptions`, `ast_grep_mcp.core.logging`, `json` (+7 more)

### `logging.py` (python)

**Functions:**
- `configure_logging(log_level, log_file) -> Constant(value=None, kind=None)` - Line 9
- `get_logger(name) -> Any` - Line 45

**Key Imports:** `structlog`, `sys`, `typing`

### `sentry.py` (python)

**Functions:**
- `init_sentry(service_name) -> Constant(value=None, kind=None)` - Line 15

**Key Imports:** `ast_grep_mcp.constants`, `ast_grep_mcp.core.logging`, `os`, `sentry_sdk`, `sentry_sdk.integrations.anthropic` (+1 more)

### `usage_tracking.py` (python)

**Classes:**
- `OperationType` (extends: str, Enum) - Line 40
  - Types of operations tracked for cost estimation.
- `OperationPricing` - Line 71
  - Cost estimation for an operation type.
- `UsageLogEntry` (extends: BaseModel) - Line 184
  - A single usage log entry.
- `UsageStats` (extends: BaseModel) - Line 201
  - Aggregated usage statistics.
- `UsageAlert` (extends: BaseModel) - Line 219
  - A usage alert/warning.
- `AlertThresholds` (extends: BaseModel) - Line 230
  - Configurable alert thresholds.
- `UsageDatabase` - Line 255
  - SQLite-based usage tracking database.
  - Methods: __init__, _get_connection, _init_schema, log_usage, get_stats (+2 more)
- `_OperationTracker` - Line 781
  - Helper class for track_operation context manager.
  - Methods: _finalize

**Functions:**
- `calculate_operation_cost(operation, files_processed, lines_analyzed, matches_found) -> float` - Line 152
- `get_usage_database() -> UsageDatabase` - Line 647
- `track_usage(tool_name, operation_type) -> Callable[...]` - Line 664
- `track_operation(tool_name, operation_type, metadata) -> Generator[...]` - Line 745
- `get_usage_stats(days) -> UsageStats` - Line 829
- `get_usage_alerts(thresholds) -> List[...]` - Line 842
- `get_recent_usage(limit, tool_name, success) -> List[...]` - Line 854
- `format_usage_report(stats) -> str` - Line 876

**Key Imports:** `contextlib`, `dataclasses`, `datetime`, `enum`, `functools` (+10 more)

---
*Generated by Enhanced Schema Generator with schema.org markup*