"""Core infrastructure for ast-grep MCP server."""

from ast_grep_mcp.core.exceptions import (
    AstGrepError,
    AstGrepNotFoundError,
    InvalidYAMLError,
    ConfigurationError,
    AstGrepExecutionError,
    NoMatchesError,
    RuleValidationError,
    RuleStorageError,
)

from ast_grep_mcp.core.logging import (
    configure_logging,
    get_logger,
)

from ast_grep_mcp.core.config import (
    CONFIG_PATH,
    CACHE_ENABLED,
    CACHE_SIZE,
    CACHE_TTL,
    CustomLanguageConfig,
    AstGrepConfig,
    validate_config_file,
    parse_args_and_get_config,
)

from ast_grep_mcp.core.sentry import (
    init_sentry,
)

from ast_grep_mcp.core.cache import (
    QueryCache,
    get_query_cache,
    init_query_cache,
)

from ast_grep_mcp.core.executor import (
    get_supported_languages,
    run_command,
    filter_files_by_size,
    run_ast_grep,
    stream_ast_grep_results,
)

__all__ = [
    # Exceptions
    "AstGrepError",
    "AstGrepNotFoundError",
    "InvalidYAMLError",
    "ConfigurationError",
    "AstGrepExecutionError",
    "NoMatchesError",
    "RuleValidationError",
    "RuleStorageError",
    # Logging
    "configure_logging",
    "get_logger",
    # Config
    "CONFIG_PATH",
    "CACHE_ENABLED",
    "CACHE_SIZE",
    "CACHE_TTL",
    "CustomLanguageConfig",
    "AstGrepConfig",
    "validate_config_file",
    "parse_args_and_get_config",
    # Sentry
    "init_sentry",
    # Cache
    "QueryCache",
    "get_query_cache",
    "init_query_cache",
    # Executor
    "get_supported_languages",
    "run_command",
    "filter_files_by_size",
    "run_ast_grep",
    "stream_ast_grep_results",
]