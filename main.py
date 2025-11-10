import argparse
import difflib
import hashlib
import json
import os
import subprocess
import sys
import time
from collections import OrderedDict
from typing import Any, Dict, Generator, List, Literal, Optional, Tuple, cast

import structlog
import yaml
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

# Global variable for config path (will be set by parse_args_and_get_config)
CONFIG_PATH: Optional[str] = None

# Global cache configuration (set by parse_args_and_get_config)
CACHE_ENABLED: bool = True
CACHE_SIZE: int = 100
CACHE_TTL: int = 300  # seconds (5 minutes default)


def configure_logging(log_level: str = "INFO", log_file: Optional[str] = None) -> None:
    """Configure structured logging with JSON output.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file path for logging (stderr by default)
    """
    # Convert log level string to int
    level_mapping = {
        "DEBUG": 10,
        "INFO": 20,
        "WARNING": 30,
        "ERROR": 40,
    }
    numeric_level = level_mapping.get(log_level.upper(), 20)  # Default to INFO

    # Configure processors for structured logging
    processors: List[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.WriteLoggerFactory(file=sys.stderr if log_file is None else open(log_file, 'a')),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> Any:
    """Get a logger instance with the given name.

    Args:
        name: Logger name (typically module or tool name)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


# Custom exception classes for better error handling
class AstGrepError(Exception):
    """Base exception for all ast-grep MCP server errors."""
    pass


class AstGrepNotFoundError(AstGrepError):
    """Raised when ast-grep binary is not found in PATH."""
    def __init__(self, message: str = "ast-grep command not found"):
        super().__init__(
            f"{message}\n\n"
            "Please install ast-grep:\n"
            "  - macOS: brew install ast-grep\n"
            "  - Linux: cargo install ast-grep --locked\n"
            "  - npm: npm install -g @ast-grep/cli\n"
            "  - See: https://ast-grep.github.io/guide/quick-start.html#installation"
        )


class InvalidYAMLError(AstGrepError):
    """Raised when YAML rule is invalid or malformed."""
    def __init__(self, message: str, yaml_content: Optional[str] = None):
        error_msg = f"Invalid YAML rule: {message}\n\n"
        error_msg += "YAML rules must include:\n"
        error_msg += "  - id: unique identifier\n"
        error_msg += "  - language: target language\n"
        error_msg += "  - rule: search pattern or conditions\n\n"
        error_msg += "Example:\n"
        error_msg += "  id: find-console-log\n"
        error_msg += "  language: javascript\n"
        error_msg += "  rule:\n"
        error_msg += "    pattern: console.log($$$)\n"
        if yaml_content:
            error_msg += f"\n\nProvided YAML:\n{yaml_content[:200]}"
        super().__init__(error_msg)


class ConfigurationError(AstGrepError):
    """Raised when configuration file is invalid."""
    def __init__(self, config_path: str, message: str):
        super().__init__(
            f"Configuration error in '{config_path}': {message}\n\n"
            "See: https://ast-grep.github.io/guide/project/project-config.html"
        )


class AstGrepExecutionError(AstGrepError):
    """Raised when ast-grep command execution fails."""
    def __init__(self, command: List[str], returncode: int, stderr: str):
        error_msg = f"ast-grep command failed with exit code {returncode}\n\n"
        error_msg += f"Command: {' '.join(command)}\n\n"
        if stderr:
            error_msg += f"Error output:\n{stderr}\n\n"
        error_msg += "Common issues:\n"
        error_msg += "  - Invalid pattern syntax\n"
        error_msg += "  - Unsupported language\n"
        error_msg += "  - File path does not exist\n"
        error_msg += "  - YAML rule missing required fields\n"
        super().__init__(error_msg)


class NoMatchesError(AstGrepError):
    """Raised when no matches are found (for test_match_code_rule only)."""
    def __init__(self, message: str = "No matches found"):
        super().__init__(
            f"{message}\n\n"
            "Tips:\n"
            "  - Verify the pattern matches the code structure\n"
            "  - Use dump_syntax_tree to inspect the AST\n"
            "  - For relational rules (inside/has), try adding 'stopBy: end'\n"
            "  - Check that the language is correct\n"
        )


# Query result cache with TTL and LRU eviction
class QueryCache:
    """Simple LRU cache with TTL for ast-grep query results.

    Caches query results to avoid redundant ast-grep executions for identical queries.
    Uses OrderedDict for LRU eviction and timestamps for TTL expiration.
    """

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        """Initialize the cache.

        Args:
            max_size: Maximum number of entries to cache
            ttl_seconds: Time-to-live for cache entries in seconds
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: OrderedDict[str, Tuple[List[Dict[str, Any]], float]] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def _make_key(self, command: str, args: List[str], project_folder: str) -> str:
        """Create a cache key from query parameters.

        Args:
            command: ast-grep command (run/scan)
            args: Command arguments
            project_folder: Project folder path

        Returns:
            Hash-based cache key
        """
        # Create a stable string representation
        key_parts = [command, project_folder] + sorted(args)
        key_str = "|".join(key_parts)
        return hashlib.sha256(key_str.encode()).hexdigest()[:16]

    def get(self, command: str, args: List[str], project_folder: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached results if available and not expired.

        Args:
            command: ast-grep command (run/scan)
            args: Command arguments
            project_folder: Project folder path

        Returns:
            Cached results if found and valid, None otherwise
        """
        key = self._make_key(command, args, project_folder)

        if key not in self.cache:
            self.misses += 1
            return None

        results, timestamp = self.cache[key]

        # Check TTL
        if time.time() - timestamp > self.ttl_seconds:
            # Expired, remove from cache
            del self.cache[key]
            self.misses += 1
            return None

        # Move to end (mark as recently used)
        self.cache.move_to_end(key)
        self.hits += 1
        return results

    def put(self, command: str, args: List[str], project_folder: str, results: List[Dict[str, Any]]) -> None:
        """Store results in cache.

        Args:
            command: ast-grep command (run/scan)
            args: Command arguments
            project_folder: Project folder path
            results: Query results to cache
        """
        key = self._make_key(command, args, project_folder)

        # Remove oldest entry if at capacity
        if len(self.cache) >= self.max_size and key not in self.cache:
            self.cache.popitem(last=False)  # Remove oldest (first) item

        # Store with current timestamp
        self.cache[key] = (results, time.time())
        # Move to end (mark as recently used)
        self.cache.move_to_end(key)

    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(hit_rate, 3),
            "ttl_seconds": self.ttl_seconds
        }


# Global cache instance (initialized after config is parsed)
_query_cache: Optional[QueryCache] = None


def get_query_cache() -> Optional[QueryCache]:
    """Get the global query cache instance if caching is enabled."""
    return _query_cache if CACHE_ENABLED else None


# Pydantic models for sgconfig.yaml validation
class CustomLanguageConfig(BaseModel):
    """Configuration for a custom language in sgconfig.yaml."""
    model_config = ConfigDict(populate_by_name=True)

    extensions: List[str]
    languageId: Optional[str] = None  # noqa: N815
    expandoChar: Optional[str] = None  # noqa: N815

    @field_validator('extensions')
    @classmethod
    def validate_extensions(cls, v: List[str]) -> List[str]:
        """Ensure extensions start with a dot."""
        if not v:
            raise ValueError("extensions list cannot be empty")
        for ext in v:
            if not ext.startswith('.'):
                raise ValueError(f"Extension '{ext}' must start with a dot (e.g., '.myext')")
        return v


class AstGrepConfig(BaseModel):
    """Pydantic model for validating sgconfig.yaml structure."""
    model_config = ConfigDict(populate_by_name=True)

    ruleDirs: Optional[List[str]] = None  # noqa: N815
    testDirs: Optional[List[str]] = None  # noqa: N815
    customLanguages: Optional[Dict[str, CustomLanguageConfig]] = None  # noqa: N815
    languageGlobs: Optional[List[Dict[str, Any]]] = None  # noqa: N815

    @field_validator('ruleDirs', 'testDirs')
    @classmethod
    def validate_dirs(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate directory lists are not empty if provided."""
        if v is not None and len(v) == 0:
            raise ValueError("Directory list cannot be empty if specified")
        return v

    @field_validator('customLanguages')
    @classmethod
    def validate_custom_languages(cls, v: Optional[Dict[str, CustomLanguageConfig]]) -> Optional[Dict[str, CustomLanguageConfig]]:
        """Validate custom languages dictionary."""
        if v is not None and len(v) == 0:
            raise ValueError("customLanguages cannot be empty if specified")
        return v


def validate_config_file(config_path: str) -> AstGrepConfig:
    """Validate sgconfig.yaml file structure.

    Args:
        config_path: Path to sgconfig.yaml file

    Returns:
        Validated AstGrepConfig model

    Raises:
        ConfigurationError: If config file is invalid
    """
    if not os.path.exists(config_path):
        raise ConfigurationError(config_path, "File does not exist")

    if not os.path.isfile(config_path):
        raise ConfigurationError(config_path, "Path is not a file")

    try:
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigurationError(config_path, f"YAML parsing failed: {e}") from e
    except OSError as e:
        raise ConfigurationError(config_path, f"Failed to read file: {e}") from e

    if config_data is None:
        raise ConfigurationError(config_path, "Config file is empty")

    if not isinstance(config_data, dict):
        raise ConfigurationError(config_path, "Config must be a YAML dictionary")

    # Validate using Pydantic model
    try:
        config = AstGrepConfig(**config_data)
        return config
    except Exception as e:
        raise ConfigurationError(config_path, f"Validation failed: {e}") from e


def parse_args_and_get_config() -> None:
    """Parse command-line arguments and determine config path."""
    global CONFIG_PATH

    # Determine how the script was invoked
    prog = None
    if sys.argv[0].endswith('main.py'):
        # Direct execution: python main.py
        prog = 'python main.py'

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        prog=prog,
        description='ast-grep MCP Server - Provides structural code search capabilities via Model Context Protocol',
        epilog='''
environment variables:
  AST_GREP_CONFIG    Path to sgconfig.yaml file (overridden by --config flag)
  LOG_LEVEL          Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)
  LOG_FILE           Path to log file (logs to stderr by default)

For more information, see: https://github.com/ast-grep/ast-grep-mcp
        ''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--config',
        type=str,
        metavar='PATH',
        help='Path to sgconfig.yaml file for customizing ast-grep behavior (language mappings, rule directories, etc.)'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default=None,
        metavar='LEVEL',
        help='Logging level (DEBUG, INFO, WARNING, ERROR). Can also be set via LOG_LEVEL env var. Default: INFO'
    )
    parser.add_argument(
        '--log-file',
        type=str,
        metavar='PATH',
        default=None,
        help='Path to log file (logs to stderr by default). Can also be set via LOG_FILE env var.'
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Disable result caching for queries. Can also be set via CACHE_DISABLED=1 env var.'
    )
    parser.add_argument(
        '--cache-size',
        type=int,
        metavar='N',
        default=None,
        help='Maximum number of cached query results (default: 100). Can also be set via CACHE_SIZE env var.'
    )
    parser.add_argument(
        '--cache-ttl',
        type=int,
        metavar='SECONDS',
        default=None,
        help='Time-to-live for cached results in seconds (default: 300). Can also be set via CACHE_TTL env var.'
    )
    args = parser.parse_args()

    # Determine config path with precedence: --config flag > AST_GREP_CONFIG env > None
    if args.config:
        CONFIG_PATH = args.config
        try:
            validate_config_file(CONFIG_PATH)
        except ConfigurationError as e:
            print(f"Error: {e}")
            sys.exit(1)
    elif os.environ.get('AST_GREP_CONFIG'):
        env_config = os.environ.get('AST_GREP_CONFIG')
        if env_config:
            CONFIG_PATH = env_config
            try:
                validate_config_file(CONFIG_PATH)
            except ConfigurationError as e:
                print(f"Error: {e}")
                sys.exit(1)

    # Determine log level with precedence: --log-level flag > LOG_LEVEL env > INFO
    log_level = args.log_level or os.environ.get('LOG_LEVEL', 'INFO')

    # Determine log file with precedence: --log-file flag > LOG_FILE env > None (stderr)
    log_file = args.log_file or os.environ.get('LOG_FILE')

    # Configure logging
    configure_logging(log_level=log_level, log_file=log_file)

    # Get logger for cache initialization
    cache_logger = get_logger("cache.init")

    # Determine cache configuration with precedence: CLI flags > env vars > defaults
    global CACHE_ENABLED, CACHE_SIZE, CACHE_TTL, _query_cache

    # Check if caching is disabled
    if args.no_cache:
        CACHE_ENABLED = False
    elif os.environ.get('CACHE_DISABLED'):
        CACHE_ENABLED = False

    # Set cache size
    if args.cache_size is not None:
        CACHE_SIZE = args.cache_size
    elif os.environ.get('CACHE_SIZE'):
        try:
            CACHE_SIZE = int(os.environ.get('CACHE_SIZE', '100'))
        except ValueError:
            print("Warning: Invalid CACHE_SIZE env var, using default (100)")
            CACHE_SIZE = 100

    # Set cache TTL
    if args.cache_ttl is not None:
        CACHE_TTL = args.cache_ttl
    elif os.environ.get('CACHE_TTL'):
        try:
            CACHE_TTL = int(os.environ.get('CACHE_TTL', '300'))
        except ValueError:
            print("Warning: Invalid CACHE_TTL env var, using default (300)")
            CACHE_TTL = 300

    # Initialize the query cache
    if CACHE_ENABLED:
        _query_cache = QueryCache(max_size=CACHE_SIZE, ttl_seconds=CACHE_TTL)
        cache_logger.info("cache_initialized",
                         cache_enabled=True,
                         cache_size=CACHE_SIZE,
                         cache_ttl=CACHE_TTL)
    else:
        _query_cache = None
        cache_logger.info("cache_initialized", cache_enabled=False)

# Initialize FastMCP server
mcp = FastMCP("ast-grep")

DumpFormat = Literal["pattern", "cst", "ast"]

def register_mcp_tools() -> None:  # pragma: no cover
    """Register all MCP tools. Tool functions are tested individually."""
    @mcp.tool()
    def dump_syntax_tree(
        code: str = Field(description = "The code you need"),
        language: str = Field(description = f"The language of the code. Supported: {', '.join(get_supported_languages())}"),
        format: DumpFormat = Field(description = "Code dump format. Available values: pattern, ast, cst", default = "cst"),
    ) -> str:
        """
        Dump code's syntax structure or dump a query's pattern structure.
        This is useful to discover correct syntax kind and syntax tree structure. Call it when debugging a rule.
        The tool requires three arguments: code, language and format. The first two are self-explanatory.
        `format` is the output format of the syntax tree.
        use `format=cst` to inspect the code's concrete syntax tree structure, useful to debug target code.
        use `format=pattern` to inspect how ast-grep interprets a pattern, useful to debug pattern rule.

        Internally calls: ast-grep run --pattern <code> --lang <language> --debug-query=<format>
        """
        logger = get_logger("tool.dump_syntax_tree")
        start_time = time.time()

        logger.info(
            "tool_invoked",
            tool="dump_syntax_tree",
            language=language,
            format=format,
            code_length=len(code)
        )

        try:
            result = run_ast_grep("run", ["--pattern", code, "--lang", language, f"--debug-query={format}"])
            output = result.stderr.strip()

            execution_time = time.time() - start_time
            logger.info(
                "tool_completed",
                tool="dump_syntax_tree",
                execution_time_seconds=round(execution_time, 3),
                output_length=len(output),
                status="success"
            )

            return output
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "tool_failed",
                tool="dump_syntax_tree",
                execution_time_seconds=round(execution_time, 3),
                error=str(e)[:200],
                status="failed"
            )
            raise

    @mcp.tool()
    def test_match_code_rule(
        code: str = Field(description = "The code to test against the rule"),
        yaml_rule: str = Field(description = "The ast-grep YAML rule to search. It must have id, language, rule fields."),
    ) -> List[dict[str, Any]]:
        """
        Test a code against an ast-grep YAML rule.
        This is useful to test a rule before using it in a project.

        Internally calls: ast-grep scan --inline-rules <yaml> --json --stdin
        """
        logger = get_logger("tool.test_match_code_rule")
        start_time = time.time()

        # Validate YAML before passing to ast-grep
        try:
            parsed_yaml = yaml.safe_load(yaml_rule)
            if not isinstance(parsed_yaml, dict):
                raise InvalidYAMLError("YAML must be a dictionary", yaml_rule)
            if 'id' not in parsed_yaml:
                raise InvalidYAMLError("Missing required field 'id'", yaml_rule)
            if 'language' not in parsed_yaml:
                raise InvalidYAMLError("Missing required field 'language'", yaml_rule)
            if 'rule' not in parsed_yaml:
                raise InvalidYAMLError("Missing required field 'rule'", yaml_rule)
        except yaml.YAMLError as e:
            raise InvalidYAMLError(f"YAML parsing failed: {e}", yaml_rule) from e

        logger.info(
            "tool_invoked",
            tool="test_match_code_rule",
            rule_id=parsed_yaml.get('id'),
            language=parsed_yaml.get('language'),
            code_length=len(code),
            yaml_length=len(yaml_rule)
        )

        try:
            result = run_ast_grep("scan", ["--inline-rules", yaml_rule, "--json", "--stdin"], input_text = code)
            matches = cast(List[dict[str, Any]], json.loads(result.stdout.strip()))

            execution_time = time.time() - start_time
            logger.info(
                "tool_completed",
                tool="test_match_code_rule",
                execution_time_seconds=round(execution_time, 3),
                match_count=len(matches),
                status="success"
            )

            if not matches:
                raise NoMatchesError("No matches found for the given code and rule")
            return matches
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "tool_failed",
                tool="test_match_code_rule",
                execution_time_seconds=round(execution_time, 3),
                error=str(e)[:200],
                status="failed"
            )
            raise

    @mcp.tool()
    def find_code(
        project_folder: str = Field(description = "The absolute path to the project folder. It must be absolute path."),
        pattern: str = Field(description = "The ast-grep pattern to search for. Note, the pattern must have valid AST structure."),
        language: str = Field(description = f"The language of the code. Supported: {', '.join(get_supported_languages())}. "
                                           "If not specified, will be auto-detected based on file extensions.", default = ""),
        max_results: int = Field(default = 0, description = "Maximum results to return"),
        output_format: str = Field(default = "text", description = "'text' or 'json'"),
    ) -> str | List[dict[str, Any]]:
        """
        Find code in a project folder that matches the given ast-grep pattern.
        Pattern is good for simple and single-AST node result.
        For more complex usage, please use YAML by `find_code_by_rule`.

        Internally calls: ast-grep run --pattern <pattern> [--json] <project_folder>

        Output formats:
        - text (default): Compact text format with file:line-range headers and complete match text
          Example:
            Found 2 matches:

            path/to/file.py:10-15
            def example_function():
                # function body
                return result

            path/to/file.py:20-22
            def another_function():
                pass

        - json: Full match objects with metadata including ranges, meta-variables, etc.

        The max_results parameter limits the number of complete matches returned (not individual lines).
        When limited, the header shows "Found X matches (showing first Y of Z)".

        Example usage:
          find_code(pattern="class $NAME", max_results=20)  # Returns text format
          find_code(pattern="class $NAME", output_format="json")  # Returns JSON with metadata
        """
        logger = get_logger("tool.find_code")
        start_time = time.time()

        logger.info(
            "tool_invoked",
            tool="find_code",
            project_folder=project_folder,
            pattern_length=len(pattern),
            language=language or "auto",
            max_results=max_results,
            output_format=output_format
        )

        try:
            if output_format not in ["text", "json"]:
                raise ValueError(f"Invalid output_format: {output_format}. Must be 'text' or 'json'.")

            args = ["--pattern", pattern]
            if language:
                args.extend(["--lang", language])

            # Check cache first
            cache = get_query_cache()
            cached_result = None
            if cache:
                cached_result = cache.get("run", args + ["--json=stream", project_folder], project_folder)
                if cached_result is not None:
                    matches = cached_result
                    logger.info(
                        "cache_hit",
                        tool="find_code",
                        cache_size=len(cache.cache),
                        cached_results=len(matches)
                    )

            # If not in cache, execute the query
            if cached_result is None:
                if cache:
                    logger.info("cache_miss", tool="find_code")

                # Use streaming to parse results line-by-line
                # This enables early termination and progress logging
                matches = list(stream_ast_grep_results(
                    "run",
                    args + ["--json=stream", project_folder],
                    max_results=max_results,
                    progress_interval=100
                ))

                # Store in cache if available
                if cache:
                    cache.put("run", args + ["--json=stream", project_folder], project_folder, matches)
                    logger.info(
                        "cache_stored",
                        tool="find_code",
                        stored_results=len(matches),
                        cache_size=len(cache.cache)
                    )

            execution_time = time.time() - start_time
            logger.info(
                "tool_completed",
                tool="find_code",
                execution_time_seconds=round(execution_time, 3),
                returned_matches=len(matches),
                output_format=output_format,
                status="success"
            )

            if output_format == "text":
                if not matches:
                    return "No matches found"
                text_output = format_matches_as_text(matches)
                header = f"Found {len(matches)} matches"
                return header + ":\n\n" + text_output
            return matches
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "tool_failed",
                tool="find_code",
                execution_time_seconds=round(execution_time, 3),
                error=str(e)[:200],
                status="failed"
            )
            raise

    @mcp.tool()
    def find_code_by_rule(
        project_folder: str = Field(description = "The absolute path to the project folder. It must be absolute path."),
        yaml_rule: str = Field(description = "The ast-grep YAML rule to search. It must have id, language, rule fields."),
        max_results: int = Field(default = 0, description = "Maximum results to return"),
        output_format: str = Field(default = "text", description = "'text' or 'json'"),
        ) -> str | List[dict[str, Any]]:
        """
        Find code using ast-grep's YAML rule in a project folder.
        YAML rule is more powerful than simple pattern and can perform complex search like find AST inside/having another AST.
        It is a more advanced search tool than the simple `find_code`.

        Tip: When using relational rules (inside/has), add `stopBy: end` to ensure complete traversal.

        Internally calls: ast-grep scan --inline-rules <yaml> [--json] <project_folder>

        Output formats:
        - text (default): Compact text format with file:line-range headers and complete match text
          Example:
            Found 2 matches:

            src/models.py:45-52
            class UserModel:
                def __init__(self):
                    self.id = None
                    self.name = None

            src/views.py:12
            class SimpleView: pass

        - json: Full match objects with metadata including ranges, meta-variables, etc.

        The max_results parameter limits the number of complete matches returned (not individual lines).
        When limited, the header shows "Found X matches (showing first Y of Z)".

        Example usage:
          find_code_by_rule(yaml_rule="id: x\\nlanguage: python\\nrule: {pattern: 'class $NAME'}", max_results=20)
          find_code_by_rule(yaml_rule="...", output_format="json")  # For full metadata
        """
        logger = get_logger("tool.find_code_by_rule")
        start_time = time.time()

        if output_format not in ["text", "json"]:
            raise ValueError(f"Invalid output_format: {output_format}. Must be 'text' or 'json'.")

        # Validate YAML before passing to ast-grep
        try:
            parsed_yaml = yaml.safe_load(yaml_rule)
            if not isinstance(parsed_yaml, dict):
                raise InvalidYAMLError("YAML must be a dictionary", yaml_rule)
            if 'id' not in parsed_yaml:
                raise InvalidYAMLError("Missing required field 'id'", yaml_rule)
            if 'language' not in parsed_yaml:
                raise InvalidYAMLError("Missing required field 'language'", yaml_rule)
            if 'rule' not in parsed_yaml:
                raise InvalidYAMLError("Missing required field 'rule'", yaml_rule)
        except yaml.YAMLError as e:
            raise InvalidYAMLError(f"YAML parsing failed: {e}", yaml_rule) from e

        logger.info(
            "tool_invoked",
            tool="find_code_by_rule",
            project_folder=project_folder,
            rule_id=parsed_yaml.get('id'),
            language=parsed_yaml.get('language'),
            yaml_length=len(yaml_rule),
            max_results=max_results,
            output_format=output_format
        )

        try:
            args = ["--inline-rules", yaml_rule]

            # Check cache first
            cache = get_query_cache()
            cached_result = None
            if cache:
                cached_result = cache.get("scan", args + ["--json=stream", project_folder], project_folder)
                if cached_result is not None:
                    matches = cached_result
                    logger.info(
                        "cache_hit",
                        tool="find_code_by_rule",
                        cache_size=len(cache.cache),
                        cached_results=len(matches)
                    )

            # If not in cache, execute the query
            if cached_result is None:
                if cache:
                    logger.info("cache_miss", tool="find_code_by_rule")

                # Use streaming to parse results line-by-line
                # This enables early termination and progress logging
                matches = list(stream_ast_grep_results(
                    "scan",
                    args + ["--json=stream", project_folder],
                    max_results=max_results,
                    progress_interval=100
                ))

                # Store in cache if available
                if cache:
                    cache.put("scan", args + ["--json=stream", project_folder], project_folder, matches)
                    logger.info(
                        "cache_stored",
                        tool="find_code_by_rule",
                        stored_results=len(matches),
                        cache_size=len(cache.cache)
                    )

            execution_time = time.time() - start_time
            logger.info(
                "tool_completed",
                tool="find_code_by_rule",
                execution_time_seconds=round(execution_time, 3),
                returned_matches=len(matches),
                output_format=output_format,
                status="success"
            )

            if output_format == "text":
                if not matches:
                    return "No matches found"
                text_output = format_matches_as_text(matches)
                header = f"Found {len(matches)} matches"
                return header + ":\n\n" + text_output
            return matches
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "tool_failed",
                tool="find_code_by_rule",
                execution_time_seconds=round(execution_time, 3),
                error=str(e)[:200],
                status="failed"
            )
            raise

    @mcp.tool()
    def find_duplication(
        project_folder: str = Field(description="The absolute path to the project folder. It must be absolute path."),
        language: str = Field(description=f"The language of the code. Supported: {', '.join(get_supported_languages())}"),
        construct_type: str = Field(
            default="function_definition",
            description=(
                "Type of code construct to check for duplication. "
                "Options: 'function_definition', 'class_definition', 'method_definition'. "
                "Default: 'function_definition'"
            )
        ),
        min_similarity: float = Field(
            default=0.8,
            description="Minimum similarity threshold (0.0-1.0) to consider code as duplicate. Higher values = more strict. Default: 0.8"
        ),
        min_lines: int = Field(
            default=5,
            description="Minimum number of lines to consider for duplication detection. Default: 5"
        ),
    ) -> Dict[str, Any]:
        """
        Detect duplicate code in a project and suggest modularization based on DRY principles.

        This tool searches for similar code constructs (functions, classes, methods) across the
        codebase and provides refactoring suggestions to eliminate duplication.

        The detection process:
        1. Uses ast-grep to find all instances of the specified construct type
        2. Compares them pairwise for structural similarity
        3. Groups similar code blocks together
        4. Generates refactoring suggestions for each duplication group

        Returns a report with:
        - Summary statistics (total constructs, duplicates found, lines duplicated)
        - Detailed duplication groups with locations
        - Specific refactoring suggestions for each group

        Example usage:
          find_duplication(project_folder="/path/to/project", language="python")
          find_duplication(project_folder="/path/to/project", language="javascript", construct_type="class_definition", min_similarity=0.85)
        """
        logger = get_logger("tool.find_duplication")
        start_time = time.time()

        logger.info(
            "tool_invoked",
            tool="find_duplication",
            project_folder=project_folder,
            language=language,
            construct_type=construct_type,
            min_similarity=min_similarity,
            min_lines=min_lines
        )

        try:
            # Validate parameters
            if min_similarity < 0.0 or min_similarity > 1.0:
                raise ValueError("min_similarity must be between 0.0 and 1.0")
            if min_lines < 1:
                raise ValueError("min_lines must be at least 1")

            # Map construct types to ast-grep patterns
            construct_patterns = {
                "function_definition": "def $NAME($$$)",  # Python/general
                "class_definition": "class $NAME",
                "method_definition": "def $NAME($$$)"
            }

            # Language-specific patterns
            if language.lower() in ["javascript", "typescript", "jsx", "tsx"]:
                construct_patterns["function_definition"] = "function $NAME($$$) { $$$ }"
                construct_patterns["method_definition"] = "$NAME($$$) { $$$ }"
            elif language.lower() in ["java", "csharp", "cpp", "c"]:
                construct_patterns["function_definition"] = "$TYPE $NAME($$$) { $$$ }"
                construct_patterns["method_definition"] = "$TYPE $NAME($$$) { $$$ }"

            pattern = construct_patterns.get(construct_type, construct_patterns["function_definition"])

            # Find all instances of the construct using ast-grep
            args = ["--pattern", pattern, "--lang", language]

            logger.info(
                "searching_constructs",
                pattern=pattern,
                language=language
            )

            # Use streaming to get all matches
            all_matches = list(stream_ast_grep_results(
                "run",
                args + ["--json=stream", project_folder],
                max_results=0,  # Get all matches
                progress_interval=100
            ))

            if not all_matches:
                execution_time = time.time() - start_time
                logger.info(
                    "tool_completed",
                    tool="find_duplication",
                    execution_time_seconds=round(execution_time, 3),
                    total_constructs=0,
                    duplicate_groups=0,
                    status="success"
                )
                return {
                    "summary": {
                        "total_constructs": 0,
                        "duplicate_groups": 0,
                        "total_duplicated_lines": 0,
                        "potential_line_savings": 0
                    },
                    "duplication_groups": [],
                    "refactoring_suggestions": [],
                    "message": f"No {construct_type} instances found in the project"
                }

            # Group duplicates
            logger.info(
                "analyzing_similarity",
                total_matches=len(all_matches),
                min_similarity=min_similarity,
                min_lines=min_lines
            )

            duplication_groups = group_duplicates(all_matches, min_similarity, min_lines)

            # Generate refactoring suggestions
            suggestions = generate_refactoring_suggestions(
                duplication_groups,
                construct_type,
                language
            )

            # Calculate summary statistics
            total_duplicated_lines = sum(s["total_duplicated_lines"] for s in suggestions)
            # Potential savings = total duplicated - (one instance per group)
            potential_savings = sum(
                s["total_duplicated_lines"] - s["lines_per_duplicate"]
                for s in suggestions
            )

            execution_time = time.time() - start_time
            logger.info(
                "tool_completed",
                tool="find_duplication",
                execution_time_seconds=round(execution_time, 3),
                total_constructs=len(all_matches),
                duplicate_groups=len(duplication_groups),
                total_duplicated_lines=total_duplicated_lines,
                potential_savings=potential_savings,
                status="success"
            )

            # Format duplication groups for output
            formatted_groups: List[Dict[str, Any]] = []
            for idx, group in enumerate(duplication_groups):
                instances: List[Dict[str, Any]] = []

                for match in group:
                    file_path = match.get('file', '')
                    start_line = match.get('range', {}).get('start', {}).get('line', 0) + 1
                    end_line = match.get('range', {}).get('end', {}).get('line', 0) + 1
                    instances.append({
                        "file": file_path,
                        "lines": f"{start_line}-{end_line}",
                        "code_preview": match.get('text', '')[:200]  # First 200 chars
                    })

                formatted_group: Dict[str, Any] = {
                    "group_id": idx + 1,
                    "similarity_score": round(
                        calculate_similarity(group[0].get('text', ''), group[1].get('text', '')),
                        3
                    ) if len(group) >= 2 else 1.0,
                    "instances": instances
                }

                formatted_groups.append(formatted_group)

            return {
                "summary": {
                    "total_constructs": len(all_matches),
                    "duplicate_groups": len(duplication_groups),
                    "total_duplicated_lines": total_duplicated_lines,
                    "potential_line_savings": potential_savings,
                    "analysis_time_seconds": round(execution_time, 3)
                },
                "duplication_groups": formatted_groups,
                "refactoring_suggestions": suggestions,
                "message": f"Found {len(duplication_groups)} duplication group(s) with potential to save {potential_savings} lines of code"
            }

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "tool_failed",
                tool="find_duplication",
                execution_time_seconds=round(execution_time, 3),
                error=str(e)[:200],
                status="failed"
            )
            raise


def format_matches_as_text(matches: List[dict[str, Any]]) -> str:
    """Convert JSON matches to LLM-friendly text format.

    Format: file:start-end followed by the complete match text.
    Matches are separated by blank lines for clarity.

    Args:
        matches: List of match dictionaries from ast-grep JSON output

    Returns:
        Formatted text string
    """
    if not matches:
        return ""

    output_blocks: List[str] = []
    for m in matches:
        file_path = m.get('file', '')
        start_line = m.get('range', {}).get('start', {}).get('line', 0) + 1
        end_line = m.get('range', {}).get('end', {}).get('line', 0) + 1
        match_text = m.get('text', '').rstrip()

        # Format: filepath:start-end (or just :line for single-line matches)
        if start_line == end_line:
            header = f"{file_path}:{start_line}"
        else:
            header = f"{file_path}:{start_line}-{end_line}"

        output_blocks.append(f"{header}\n{match_text}")

    return '\n\n'.join(output_blocks)


def normalize_code(code: str) -> str:
    """Normalize code for comparison by removing whitespace and comments.

    Args:
        code: Code string to normalize

    Returns:
        Normalized code string
    """
    lines = []
    for line in code.split('\n'):
        # Remove leading/trailing whitespace
        stripped = line.strip()
        # Skip empty lines and simple comments
        if stripped and not stripped.startswith('#') and not stripped.startswith('//'):
            lines.append(stripped)
    return '\n'.join(lines)


def calculate_similarity(code1: str, code2: str) -> float:
    """Calculate similarity ratio between two code snippets.

    Uses SequenceMatcher for structural similarity comparison.

    Args:
        code1: First code snippet
        code2: Second code snippet

    Returns:
        Similarity ratio between 0 and 1
    """
    if not code1 or not code2:
        return 0.0

    # Normalize code for comparison
    norm1 = normalize_code(code1)
    norm2 = normalize_code(code2)

    # Use difflib SequenceMatcher for similarity
    matcher = difflib.SequenceMatcher(None, norm1, norm2)
    return matcher.ratio()


def group_duplicates(
    matches: List[Dict[str, Any]],
    min_similarity: float = 0.8,
    min_lines: int = 3
) -> List[List[Dict[str, Any]]]:
    """Group similar code matches into duplication clusters.

    Args:
        matches: List of code matches from ast-grep
        min_similarity: Minimum similarity threshold (0-1)
        min_lines: Minimum lines to consider for duplication

    Returns:
        List of duplication groups (each group is a list of similar matches)
    """
    if not matches:
        return []

    # Filter by minimum lines
    filtered_matches = []
    for match in matches:
        text = match.get('text', '')
        line_count = len([line for line in text.split('\n') if line.strip()])
        if line_count >= min_lines:
            filtered_matches.append(match)

    if not filtered_matches:
        return []

    # Group similar matches
    groups: List[List[Dict[str, Any]]] = []
    used_indices: set[int] = set()

    for i, match1 in enumerate(filtered_matches):
        if i in used_indices:
            continue

        group = [match1]
        used_indices.add(i)

        for j, match2 in enumerate(filtered_matches[i + 1:], start=i + 1):
            if j in used_indices:
                continue

            similarity = calculate_similarity(
                match1.get('text', ''),
                match2.get('text', '')
            )

            if similarity >= min_similarity:
                group.append(match2)
                used_indices.add(j)

        # Only include groups with 2+ items (actual duplicates)
        if len(group) >= 2:
            groups.append(group)

    return groups


def generate_refactoring_suggestions(
    duplication_groups: List[List[Dict[str, Any]]],
    construct_type: str,
    language: str
) -> List[Dict[str, Any]]:
    """Generate refactoring suggestions for duplicate code.

    Args:
        duplication_groups: Groups of duplicate code matches
        construct_type: Type of construct (function, class, etc.)
        language: Programming language

    Returns:
        List of refactoring suggestions
    """
    suggestions = []

    for group_idx, group in enumerate(duplication_groups):
        if len(group) < 2:
            continue

        # Get locations of duplicates
        locations = []
        for match in group:
            file_path = match.get('file', '')
            start_line = match.get('range', {}).get('start', {}).get('line', 0) + 1
            end_line = match.get('range', {}).get('end', {}).get('line', 0) + 1
            locations.append(f"{file_path}:{start_line}-{end_line}")

        # Calculate total lines duplicated
        sample_text = group[0].get('text', '')
        line_count = len([line for line in sample_text.split('\n') if line.strip()])
        total_duplicated_lines = line_count * len(group)

        # Generate suggestion based on construct type
        if construct_type == "function_definition":
            suggestion_type = "Extract Shared Function"
            description = f"Extract {len(group)} similar functions into a shared utility function"
            suggestion_text = (
                f"Create a new utility function that captures the common logic. "
                f"Consider parameterizing the differences between the {len(group)} instances."
            )
        elif construct_type == "class_definition":
            suggestion_type = "Extract Base Class"
            description = f"Extract {len(group)} similar classes into a base class or mixin"
            suggestion_text = (
                f"Create a base class or mixin to capture shared behavior. "
                f"Use inheritance or composition to eliminate duplication across {len(group)} classes."
            )
        else:
            suggestion_type = "Refactor Duplicate Code"
            description = f"Refactor {len(group)} similar code blocks"
            suggestion_text = (
                f"Consider extracting this repeated pattern into a reusable component. "
                f"Identify parameters that vary between the {len(group)} instances."
            )

        suggestions.append({
            "group_id": group_idx + 1,
            "type": suggestion_type,
            "description": description,
            "suggestion": suggestion_text,
            "duplicate_count": len(group),
            "lines_per_duplicate": line_count,
            "total_duplicated_lines": total_duplicated_lines,
            "locations": locations,
            "sample_code": sample_text[:500]  # First 500 chars as sample
        })

    return suggestions


def get_supported_languages() -> List[str]:
    """Get all supported languages as a field description string."""
    languages = [  # https://ast-grep.github.io/reference/languages.html
        "bash", "c", "cpp", "csharp", "css", "elixir", "go", "haskell",
        "html", "java", "javascript", "json", "jsx", "kotlin", "lua",
        "nix", "php", "python", "ruby", "rust", "scala", "solidity",
        "swift", "tsx", "typescript", "yaml"
    ]

    # Check for custom languages in config file
    # https://ast-grep.github.io/advanced/custom-language.html#register-language-in-sgconfig-yml
    if CONFIG_PATH and os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = yaml.safe_load(f)
                if config and 'customLanguages' in config:
                    custom_langs = list(config['customLanguages'].keys())
                    languages += custom_langs
        except Exception:
            pass

    return sorted(set(languages))

def run_command(args: List[str], input_text: Optional[str] = None) -> subprocess.CompletedProcess[str]:
    """Execute a command with proper error handling.

    Args:
        args: Command arguments list
        input_text: Optional stdin input

    Returns:
        CompletedProcess instance

    Raises:
        AstGrepNotFoundError: If command binary not found
        AstGrepExecutionError: If command execution fails
    """
    logger = get_logger("subprocess")
    start_time = time.time()

    # Sanitize command for logging (don't log code content)
    sanitized_args = args.copy()
    has_stdin = input_text is not None

    logger.info(
        "executing_command",
        command=sanitized_args[0],
        args=sanitized_args[1:],
        has_stdin=has_stdin
    )

    try:
        # On Windows, if ast-grep is installed via npm, it's a batch file
        # that requires shell=True to execute properly
        use_shell = (sys.platform == "win32" and args[0] == "ast-grep")

        result = subprocess.run(
            args,
            capture_output=True,
            input=input_text,
            text=True,
            check=True,  # Raises CalledProcessError if return code is non-zero
            shell=use_shell
        )

        execution_time = time.time() - start_time
        logger.info(
            "command_completed",
            command=sanitized_args[0],
            execution_time_seconds=round(execution_time, 3),
            returncode=result.returncode
        )

        return result
    except subprocess.CalledProcessError as e:
        execution_time = time.time() - start_time
        stderr_msg = e.stderr.strip() if e.stderr else ""

        logger.error(
            "command_failed",
            command=sanitized_args[0],
            execution_time_seconds=round(execution_time, 3),
            returncode=e.returncode,
            stderr=stderr_msg[:200]  # Truncate stderr in logs
        )

        raise AstGrepExecutionError(
            command=args,
            returncode=e.returncode,
            stderr=stderr_msg
        ) from e
    except FileNotFoundError as e:
        execution_time = time.time() - start_time

        logger.error(
            "command_not_found",
            command=args[0],
            execution_time_seconds=round(execution_time, 3)
        )

        if args[0] == "ast-grep":
            raise AstGrepNotFoundError() from e
        raise AstGrepNotFoundError(f"Command '{args[0]}' not found") from e

def run_ast_grep(command: str, args: List[str], input_text: Optional[str] = None) -> subprocess.CompletedProcess[str]:
    """Execute ast-grep command with optional config.

    Args:
        command: ast-grep subcommand (run, scan, etc.)
        args: Command arguments
        input_text: Optional stdin input

    Returns:
        CompletedProcess instance
    """
    if CONFIG_PATH:
        args = ["--config", CONFIG_PATH] + args
    return run_command(["ast-grep", command] + args, input_text)

def stream_ast_grep_results(
    command: str,
    args: List[str],
    max_results: int = 0,
    progress_interval: int = 100
) -> Generator[Dict[str, Any], None, None]:
    """Stream ast-grep JSON results line-by-line with early termination support.

    This function uses subprocess.Popen to read ast-grep output incrementally,
    parsing each JSON object as it arrives. This approach:
    - Reduces memory usage for large result sets
    - Enables early termination when max_results is reached
    - Provides progress logging during long searches

    Args:
        command: ast-grep subcommand (run, scan, etc.)
        args: Command arguments (must include --json=stream flag)
        max_results: Maximum results to yield (0 = unlimited)
        progress_interval: Log progress every N matches

    Yields:
        Individual match dictionaries from ast-grep JSON output

    Raises:
        AstGrepNotFoundError: If ast-grep binary not found
        AstGrepExecutionError: If ast-grep execution fails
    """
    logger = get_logger("stream_results")
    start_time = time.time()

    # Add config if specified
    final_args = args.copy()
    if CONFIG_PATH:
        final_args = ["--config", CONFIG_PATH] + final_args

    # Build full command
    full_command = ["ast-grep", command] + final_args

    # On Windows, ast-grep may be a batch file requiring shell
    use_shell = (sys.platform == "win32" and full_command[0] == "ast-grep")

    logger.info(
        "stream_started",
        command=command,
        max_results=max_results,
        progress_interval=progress_interval
    )

    process = None
    try:
        # Start subprocess with stdout pipe
        process = subprocess.Popen(
            full_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=use_shell
        )

        match_count = 0
        last_progress_log = 0

        # Read stdout line-by-line
        if process.stdout:
            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue

                try:
                    # Parse each line as a JSON object
                    match = cast(Dict[str, Any], json.loads(line))
                    match_count += 1

                    # Log progress at intervals
                    if progress_interval > 0 and match_count - last_progress_log >= progress_interval:
                        logger.info(
                            "stream_progress",
                            matches_found=match_count,
                            execution_time_seconds=round(time.time() - start_time, 3)
                        )
                        last_progress_log = match_count

                    yield match

                    # Early termination if max_results reached
                    if max_results > 0 and match_count >= max_results:
                        logger.info(
                            "stream_early_termination",
                            matches_found=match_count,
                            max_results=max_results
                        )
                        # Terminate the subprocess
                        process.terminate()
                        try:
                            process.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
                        break

                except json.JSONDecodeError as e:
                    # Skip invalid JSON lines (shouldn't happen with ast-grep)
                    logger.warning(
                        "stream_json_parse_error",
                        line_preview=line[:100],
                        error=str(e)
                    )
                    continue

        # Wait for process to complete (if not terminated early)
        returncode = process.wait()

        # Check for errors
        if returncode != 0 and returncode != -15:  # -15 is SIGTERM from early termination
            stderr_output = process.stderr.read() if process.stderr else ""
            execution_time = time.time() - start_time

            logger.error(
                "stream_failed",
                returncode=returncode,
                stderr=stderr_output[:200],
                execution_time_seconds=round(execution_time, 3)
            )

            raise AstGrepExecutionError(
                command=full_command,
                returncode=returncode,
                stderr=stderr_output
            )

        execution_time = time.time() - start_time
        logger.info(
            "stream_completed",
            total_matches=match_count,
            execution_time_seconds=round(execution_time, 3),
            early_terminated=max_results > 0 and match_count >= max_results
        )

    except FileNotFoundError as e:
        logger.error("stream_command_not_found", command=full_command[0])
        if full_command[0] == "ast-grep":
            raise AstGrepNotFoundError() from e
        raise AstGrepNotFoundError(f"Command '{full_command[0]}' not found") from e

    finally:
        # Ensure subprocess is cleaned up
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

def run_mcp_server() -> None:  # pragma: no cover
    """
    Run the MCP server.
    This function is used to start the MCP server when this script is run directly.
    """
    parse_args_and_get_config()  # sets CONFIG_PATH
    register_mcp_tools()  # tools defined *after* CONFIG_PATH is known
    mcp.run(transport="stdio")

if __name__ == "__main__":  # pragma: no cover
    run_mcp_server()
