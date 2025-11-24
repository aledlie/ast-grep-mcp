import argparse
import asyncio
import difflib
import hashlib
import json
import os
import platform
import re
import shutil
import sqlite3
import subprocess
import sys
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Literal, Optional, Set, Tuple, cast

import httpx
import sentry_sdk
import structlog
import yaml
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sentry_sdk.integrations.anthropic import AnthropicIntegration

# Global variable for config path (will be set by parse_args_and_get_config)
CONFIG_PATH: Optional[str] = None

# Global cache configuration (set by parse_args_and_get_config)
CACHE_ENABLED: bool = True
CACHE_SIZE: int = 100
CACHE_TTL: int = 300  # seconds (5 minutes default)

# Code generation templates for Phase 2 - Code Generation Engine
# Used for extracting duplicates into reusable helper classes

PYTHON_CLASS_TEMPLATE: str = '''{decorators}class {name}{bases}:
{docstring}{class_vars}{methods}'''

# Helper functions for template formatting
def format_python_class(
    name: str,
    methods: str,
    decorators: Optional[str] = None,
    bases: Optional[List[str]] = None,
    docstring: Optional[str] = None,
    class_vars: Optional[str] = None,
) -> str:
    """Format a Python class using the template.

    Args:
        name: Class name
        methods: Formatted method definitions (already indented)
        decorators: Optional decorator strings (e.g., "@dataclass\\n")
        bases: Optional list of base classes for inheritance
        docstring: Optional class-level docstring
        class_vars: Optional class variable definitions

    Returns:
        Formatted Python class string
    """
    # Format decorators
    decorator_str = f"{decorators}\n" if decorators else ""

    # Format base classes
    bases_str = f"({', '.join(bases)})" if bases else ""

    # Format docstring with proper indentation
    docstring_str = f'    """{docstring}"""\n\n' if docstring else ""

    # Format class variables with proper indentation
    class_vars_str = f"{class_vars}\n\n" if class_vars else ""

    # Ensure methods are properly indented (4 spaces)
    if methods and not methods.startswith("    "):
        methods = "\n".join(f"    {line}" if line.strip() else line
                          for line in methods.split("\n"))

    return PYTHON_CLASS_TEMPLATE.format(
        decorators=decorator_str,
        name=name,
        bases=bases_str,
        docstring=docstring_str,
        class_vars=class_vars_str,
        methods=methods,
    )


def format_java_code(code: str) -> str:
    """Format Java code using google-java-format or basic formatting fallback.

    Attempts to use google-java-format for professional formatting. Falls back
    to basic formatting rules if the tool is not available.

    Args:
        code: Java source code string to format

    Returns:
        Formatted Java code string

    Examples:
        >>> format_java_code("public class Foo{int x;}")
        'public class Foo {\\n    int x;\\n}'
    """
    import re
    import shutil
    import subprocess
    import tempfile

    # Try google-java-format if available
    if shutil.which("google-java-format"):
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.java', delete=False
            ) as f:
                f.write(code)
                temp_path = f.name

            result = subprocess.run(
                ["google-java-format", temp_path],
                capture_output=True,
                text=True,
                timeout=30
            )

            # Clean up temp file
            try:
                os.unlink(temp_path)
            except OSError:
                pass

            if result.returncode == 0:
                return result.stdout

        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass  # Fall through to basic formatting

    # Basic formatting fallback
    lines = code.split('\n')
    formatted_lines: list[str] = []
    indent_level = 0
    import_lines: list[str] = []
    non_import_lines: list[str] = []
    in_imports = False

    # First pass: separate imports from other code
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('import '):
            import_lines.append(stripped)
            in_imports = True
        elif stripped.startswith('package '):
            non_import_lines.append(stripped)
        elif stripped:
            if in_imports and import_lines:
                in_imports = False
            non_import_lines.append(stripped)
        elif not in_imports:
            non_import_lines.append('')

    # Sort imports: java.* first, then javax.*, then others
    def import_sort_key(imp: str) -> tuple[int, str]:
        name = imp.replace('import ', '').replace('static ', '').strip().rstrip(';')
        if name.startswith('java.'):
            return (0, name)
        elif name.startswith('javax.'):
            return (1, name)
        else:
            return (2, name)

    import_lines.sort(key=import_sort_key)

    # Reconstruct with sorted imports
    all_lines: list[str] = []
    found_package = False
    for line in non_import_lines:
        if line.startswith('package '):
            all_lines.append(line)
            found_package = True
            if import_lines:
                all_lines.append('')  # Blank line after package
                all_lines.extend(import_lines)
                all_lines.append('')  # Blank line after imports
        else:
            all_lines.append(line)

    if not found_package and import_lines:
        all_lines = import_lines + [''] + all_lines

    # Second pass: apply indentation and brace formatting
    for line in all_lines:
        stripped = line.strip()
        if not stripped:
            formatted_lines.append('')
            continue

        # Decrease indent for closing braces
        if stripped.startswith('}') or stripped.startswith(')'):
            indent_level = max(0, indent_level - 1)

        # Handle lines that both close and open (e.g., "} else {")
        temp_indent = indent_level
        if stripped.startswith('}') and '{' in stripped:
            temp_indent = max(0, indent_level)

        # Apply indentation (4 spaces)
        formatted_line = '    ' * temp_indent + stripped

        # Ensure space before opening brace
        formatted_line = re.sub(r'(\S)\{', r'\1 {', formatted_line)

        formatted_lines.append(formatted_line)

        # Increase indent for opening braces
        open_braces = stripped.count('{') - stripped.count('}')
        indent_level = max(0, indent_level + open_braces)

    return '\n'.join(formatted_lines)


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


def init_sentry(service_name: str = "ast-grep-mcp") -> None:
    """Initialize Sentry with Anthropic AI integration and service tagging.

    Args:
        service_name: Unique service identifier (default: 'ast-grep-mcp')
    """
    def _tag_event(event: Any, hint: Any) -> Any:
        """Add service tags to every event for unified project."""
        event.setdefault("tags", {})
        event["tags"]["service"] = service_name
        event["tags"]["language"] = "python"
        event["tags"]["component"] = "mcp-server"
        return event

    # Only initialize if SENTRY_DSN is set
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return

    sentry_sdk.init(
        dsn=dsn,
        # Environment
        environment=os.getenv("SENTRY_ENVIRONMENT", "development"),
        # Integrations - Include Anthropic AI
        integrations=[
            AnthropicIntegration(
                include_prompts=True,  # Capture prompts and responses
            ),
        ],
        # Performance monitoring - REQUIRED for AI tracking
        traces_sample_rate=1.0 if os.getenv("SENTRY_ENVIRONMENT") == "development" else 0.1,
        profiles_sample_rate=1.0 if os.getenv("SENTRY_ENVIRONMENT") == "development" else 0.1,
        # Send PII for AI context
        send_default_pii=True,
        # Additional options
        attach_stacktrace=True,
        max_breadcrumbs=50,
        debug=os.getenv("SENTRY_ENVIRONMENT") == "development",
        # Tag every event with service name
        before_send=_tag_event,
    )

    # Set global tags for all future events
    sentry_sdk.set_tag("service", service_name)
    sentry_sdk.set_tag("language", "python")
    sentry_sdk.set_tag("component", "mcp-server")

    logger = get_logger("sentry")
    logger.info(
        "sentry_initialized",
        service=service_name,
        environment=os.getenv("SENTRY_ENVIRONMENT", "development"),
    )


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


# Code generation templates for Phase 2 (Code Generation Engine)
# These templates are used by the duplication detection system to generate
# refactored code that consolidates duplicate patterns.

TYPESCRIPT_CLASS_TEMPLATE: str = """{jsdoc}{export}{abstract}class {name}{type_params}{extends}{implements} {{
{properties}{constructor}{methods}}}
"""

def format_typescript_class(
    name: str,
    *,
    export: bool = False,
    abstract: bool = False,
    type_params: Optional[str] = None,
    extends: Optional[str] = None,
    implements: Optional[List[str]] = None,
    jsdoc: Optional[str] = None,
    properties: Optional[List[str]] = None,
    constructor: Optional[str] = None,
    methods: Optional[List[str]] = None,
) -> str:
    """Format a TypeScript class using the template.

    Args:
        name: Class name
        export: Whether to export the class
        abstract: Whether the class is abstract
        type_params: Generic type parameters (e.g., "<T, U>")
        extends: Parent class name
        implements: List of interface names to implement
        jsdoc: JSDoc comment block (without leading newline)
        properties: List of property declarations with indentation
        constructor: Constructor code with indentation
        methods: List of method implementations with indentation

    Returns:
        Formatted TypeScript class code
    """
    return TYPESCRIPT_CLASS_TEMPLATE.format(
        jsdoc=f"{jsdoc}\n" if jsdoc else "",
        export="export " if export else "",
        abstract="abstract " if abstract else "",
        name=name,
        type_params=type_params if type_params else "",
        extends=f" extends {extends}" if extends else "",
        implements=f" implements {', '.join(implements)}" if implements else "",
        properties="\n".join(properties) + "\n\n" if properties else "",
        constructor=constructor + "\n\n" if constructor else "",
        methods="\n\n".join(methods) + "\n" if methods else "",
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

# Schema.org Client for structured data tools
class SchemaOrgClient:
    """Client for fetching and querying Schema.org vocabulary."""

    def __init__(self) -> None:
        self.schema_data: Dict[str, Any] = {}
        self.initialized = False
        self.SCHEMA_URL = "https://schema.org/version/latest/schemaorg-current-https.jsonld"
        self.logger = get_logger("schema_org")

    async def initialize(self) -> None:
        """Fetch and index Schema.org data."""
        if self.initialized:
            return

        try:
            self.logger.info("fetching_schema_org_data", url=self.SCHEMA_URL)
            with sentry_sdk.start_span(op="http.client", name="Fetch Schema.org vocabulary") as span:
                span.set_data("url", self.SCHEMA_URL)
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(self.SCHEMA_URL)
                    response.raise_for_status()
                    data = response.json()
                span.set_data("status_code", response.status_code)
                span.set_data("content_length", len(str(data)))

            if not data:
                raise RuntimeError("No data received from schema.org")

            # Index all types and properties by their @id
            if data.get('@graph') and isinstance(data['@graph'], list):
                for item in data['@graph']:
                    if item and isinstance(item, dict) and item.get('@id'):
                        self.schema_data[item['@id']] = item
                        # Also index by label for easier lookup
                        label = item.get('rdfs:label')
                        if isinstance(label, str):
                            self.schema_data[f"schema:{label}"] = item
            else:
                raise RuntimeError("Invalid schema.org data format: missing @graph array")

            if not self.schema_data:
                raise RuntimeError("No schema data was loaded")

            self.initialized = True
            self.logger.info("schema_org_loaded", entry_count=len(self.schema_data))
        except Exception as e:
            self.logger.error("schema_org_load_failed", error=str(e))
            self.initialized = False
            sentry_sdk.capture_exception(e, extras={
                "url": self.SCHEMA_URL,
                "operation": "schema_org_initialize"
            })
            raise RuntimeError(f"Failed to initialize schema.org client: {e}") from e

    def _normalize_to_array(self, value: Any) -> List[Any]:
        """Normalize a value or array to a list."""
        if not value:
            return []
        return value if isinstance(value, list) else [value]

    def _extract_super_types(self, type_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract parent types from a type definition."""
        super_classes = self._normalize_to_array(type_data.get('rdfs:subClassOf'))
        result = []
        for sc in super_classes:
            if isinstance(sc, dict) and sc.get('@id'):
                super_type = self.schema_data.get(sc['@id'], {})
                label = super_type.get('rdfs:label')
                result.append({
                    'name': label if isinstance(label, str) else sc['@id'].replace('schema:', ''),
                    'id': sc['@id']
                })
        return result

    def _find_sub_types(self, type_id: str) -> List[Dict[str, str]]:
        """Find all subtypes of a given type."""
        sub_types = []
        for item in self.schema_data.values():
            if not item.get('@type'):
                continue

            types = self._normalize_to_array(item['@type'])
            if 'rdfs:Class' not in types:
                continue

            super_classes = self._normalize_to_array(item.get('rdfs:subClassOf'))
            for sc in super_classes:
                if isinstance(sc, dict) and sc.get('@id') == type_id:
                    label = item.get('rdfs:label')
                    if label:
                        sub_types.append({
                            'name': label,
                            'id': item['@id']
                        })
                    break

        return sub_types

    def _format_property(self, prop: Dict[str, Any]) -> Dict[str, Any]:
        """Format a property for output."""
        ranges = self._normalize_to_array(prop.get('schema:rangeIncludes'))
        expected_types = []
        for r in ranges:
            if isinstance(r, dict) and r.get('@id'):
                range_type = self.schema_data.get(r['@id'], {})
                label = range_type.get('rdfs:label')
                expected_types.append(label if isinstance(label, str) else r['@id'].replace('schema:', ''))

        return {
            'name': prop.get('rdfs:label', ''),
            'description': prop.get('rdfs:comment', 'No description available'),
            'id': prop.get('@id', ''),
            'expectedTypes': expected_types
        }

    def _generate_example_value(self, property_data: Dict[str, Any]) -> Any:
        """Generate an example value for a property."""
        expected_types = property_data.get('expectedTypes', [])
        if not expected_types:
            return f"Example {property_data.get('name', 'value')}"

        type_name = expected_types[0]

        if type_name == 'Text':
            return f"Example {property_data.get('name', 'text')}"
        elif type_name == 'URL':
            return 'https://example.com'
        elif type_name == 'Date':
            return '2024-01-01'
        elif type_name == 'DateTime':
            return '2024-01-01T12:00:00Z'
        elif type_name in ('Number', 'Integer'):
            return 42
        elif type_name == 'Boolean':
            return True
        elif type_name == 'ImageObject':
            return {
                '@type': 'ImageObject',
                'url': 'https://example.com/image.jpg',
                'contentUrl': 'https://example.com/image.jpg'
            }
        else:
            return f"Example {property_data.get('name', 'value')}"

    async def get_schema_type(self, type_name: str) -> Dict[str, Any]:
        """Get detailed information about a schema.org type."""
        await self.initialize()

        if not type_name or not isinstance(type_name, str):
            raise ValueError("Type name must be a non-empty string")

        type_id = type_name if type_name.startswith('schema:') else f"schema:{type_name}"
        type_data = self.schema_data.get(type_id)

        if not type_data:
            raise ValueError(f"Type '{type_name}' not found in schema.org")

        label = type_data.get('rdfs:label')
        clean_name = label if isinstance(label, str) else type_name

        return {
            'name': clean_name,
            'description': type_data.get('rdfs:comment', 'No description available'),
            'id': type_data.get('@id', ''),
            'type': type_data.get('@type'),
            'superTypes': self._extract_super_types(type_data),
            'url': f"https://schema.org/{clean_name}"
        }

    async def search_schemas(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for schema types by keyword."""
        await self.initialize()

        if not query or not isinstance(query, str):
            raise ValueError("Query must be a non-empty string")

        normalized_limit = max(1, min(limit or 10, 100))
        results = []
        query_lower = query.lower().strip()

        if not query_lower:
            raise ValueError("Query cannot be empty")

        for item in self.schema_data.values():
            if not item.get('@type'):
                continue

            types = self._normalize_to_array(item['@type'])
            if 'rdfs:Class' not in types:
                continue

            label = item.get('rdfs:label', '')
            comment = item.get('rdfs:comment', '')

            if not isinstance(label, str):
                continue

            label_lower = label.lower()
            comment_lower = comment.lower() if isinstance(comment, str) else ''

            if query_lower in label_lower or query_lower in comment_lower:
                results.append({
                    'name': label,
                    'description': comment or 'No description available',
                    'id': item.get('@id', ''),
                    'url': f"https://schema.org/{label}",
                    'relevance': 2 if query_lower in label_lower else 1
                })

            if len(results) >= normalized_limit * 2:
                break

        # Sort by relevance and limit
        results.sort(key=lambda x: x['relevance'], reverse=True)
        return [{'name': r['name'], 'description': r['description'], 'id': r['id'], 'url': r['url']}
                for r in results[:normalized_limit]]

    async def get_type_hierarchy(self, type_name: str) -> Dict[str, Any]:
        """Get the inheritance hierarchy for a type."""
        await self.initialize()

        type_id = type_name if type_name.startswith('schema:') else f"schema:{type_name}"
        type_data = self.schema_data.get(type_id)

        if not type_data:
            raise ValueError(f"Type '{type_name}' not found in schema.org")

        label = type_data.get('rdfs:label')
        return {
            'name': label if isinstance(label, str) else type_name,
            'id': type_data.get('@id', ''),
            'parents': self._extract_super_types(type_data),
            'children': self._find_sub_types(type_id)
        }

    async def get_type_properties(self, type_name: str, include_inherited: bool = True) -> List[Dict[str, Any]]:
        """Get all properties available for a type."""
        await self.initialize()

        type_id = type_name if type_name.startswith('schema:') else f"schema:{type_name}"
        properties: List[Dict[str, Any]] = []
        processed_props: set[str] = set()

        # Get direct properties
        for item in self.schema_data.values():
            item_types = item.get('@type')
            if not item_types:
                continue

            types_list = self._normalize_to_array(item_types)
            if 'rdf:Property' not in types_list:
                continue

            domains = self._normalize_to_array(item.get('schema:domainIncludes'))
            for domain in domains:
                if isinstance(domain, dict) and domain.get('@id') == type_id:
                    prop_id = item.get('@id', '')
                    if prop_id and prop_id not in processed_props:
                        processed_props.add(prop_id)
                        properties.append(self._format_property(item))
                    break

        # Get inherited properties if requested
        if include_inherited:
            type_data = self.schema_data.get(type_id)
            if type_data:
                super_types = self._extract_super_types(type_data)
                for super_type in super_types:
                    super_type_id = super_type['id']
                    for item in self.schema_data.values():
                        item_types = item.get('@type')
                        if not item_types:
                            continue

                        types_list = self._normalize_to_array(item_types)
                        if 'rdf:Property' not in types_list:
                            continue

                        domains = self._normalize_to_array(item.get('schema:domainIncludes'))
                        for domain in domains:
                            if isinstance(domain, dict) and domain.get('@id') == super_type_id:
                                prop_id = item.get('@id', '')
                                if prop_id and prop_id not in processed_props:
                                    processed_props.add(prop_id)
                                    prop = self._format_property(item)
                                    prop['inheritedFrom'] = super_type['name']
                                    properties.append(prop)
                                break

        properties.sort(key=lambda x: x['name'])
        return properties

    async def generate_example(self, type_name: str, custom_properties: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate an example JSON-LD for a type."""
        await self.initialize()

        type_info = await self.get_schema_type(type_name)
        properties = await self.get_type_properties(type_name, include_inherited=False)

        example: Dict[str, Any] = {
            '@context': 'https://schema.org',
            '@type': type_info['name']
        }

        # Add common properties
        common_props = ['name', 'description', 'url', 'identifier', 'image']

        for prop in properties:
            if prop['name'] in common_props:
                example[prop['name']] = self._generate_example_value(prop)

        # Add custom properties
        if custom_properties:
            example.update(custom_properties)

        return example

    def generate_entity_id(self, base_url: str, entity_type: str, entity_slug: Optional[str] = None) -> str:
        """Generate a proper @id value following best practices.

        Args:
            base_url: The canonical URL (e.g., 'https://example.com' or 'https://example.com/page')
            entity_type: The schema type in lowercase (e.g., 'organization', 'person', 'product')
            entity_slug: Optional specific identifier (e.g., 'john-doe', 'widget-a')

        Returns:
            Properly formatted @id like 'https://example.com/#organization' or
            'https://example.com/products/widget-a#product'

        Best practices from https://momenticmarketing.com/blog/id-schema-for-seo-llms-knowledge-graphs:
        - Use canonical URL + hash fragment
        - Keep IDs stable (no timestamps or dynamic values)
        - Use descriptive entity types for debugging clarity
        - One unchanging identifier per entity
        """
        # Remove trailing slash from base_url
        base_url = base_url.rstrip('/')

        # Normalize entity_type to lowercase
        entity_type_lower = entity_type.lower()

        # If entity_slug provided, append it to the path
        if entity_slug:
            # Remove leading slash from slug if present
            entity_slug = entity_slug.lstrip('/')
            return f"{base_url}/{entity_slug}#{entity_type_lower}"
        else:
            return f"{base_url}#{entity_type_lower}"

    def validate_entity_id(self, entity_id: str) -> Dict[str, Any]:
        """Validate an @id value against best practices.

        Args:
            entity_id: The @id value to validate

        Returns:
            Dictionary with validation results:
            - valid: bool - Overall validity
            - warnings: List[str] - Best practice warnings
            - suggestions: List[str] - Improvement suggestions
        """
        warnings = []
        suggestions = []

        # Check if it's a valid URL
        if not entity_id.startswith(('http://', 'https://')):
            warnings.append("@id should be a full URL (http:// or https://)")

        # Check for hash fragment
        if '#' not in entity_id:
            warnings.append("@id should include a hash fragment (e.g., #organization)")
            suggestions.append("Add a descriptive fragment like #organization, #person, or #product")

        # Check for problematic patterns
        if any(pattern in entity_id.lower() for pattern in ['timestamp', 'date', 'time', 'random', 'temp']):
            warnings.append("@id contains potentially unstable components (timestamp, date, random)")
            suggestions.append("Use stable, permanent identifiers")

        # Check for numeric-only fragment
        if '#' in entity_id:
            fragment = entity_id.split('#')[1]
            if fragment.isdigit():
                warnings.append("Fragment is numeric-only, consider using descriptive names")
                suggestions.append("Use descriptive fragments like #organization instead of #1")

        # Check for query parameters
        if '?' in entity_id:
            warnings.append("@id contains query parameters which may be unstable")
            suggestions.append("Use clean URLs without query strings")

        valid = len(warnings) == 0

        return {
            'valid': valid,
            'entity_id': entity_id,
            'warnings': warnings,
            'suggestions': suggestions,
            'best_practices': [
                'Use canonical URL + hash fragment',
                'Keep IDs stable (no timestamps or dynamic values)',
                'Use descriptive fragments for debugging',
                'One unchanging identifier per entity'
            ] if warnings else []
        }

    async def build_entity_graph(
        self,
        entities: List[Dict[str, Any]],
        base_url: str
    ) -> Dict[str, Any]:
        """Build a knowledge graph of related entities with proper @id references.

        Args:
            entities: List of entity definitions, each with:
                - type: Schema.org type name
                - slug: Optional URL slug
                - properties: Dict of property values
                - relationships: Optional dict of relationships to other entities
            base_url: Base canonical URL for generating @id values

        Returns:
            Complete @graph structure with all entities properly connected

        Example:
            entities = [
                {
                    'type': 'Organization',
                    'slug': None,  # Homepage entity
                    'properties': {'name': 'Acme Corp'},
                    'relationships': {'founder': 'person-john'}
                },
                {
                    'type': 'Person',
                    'slug': 'team/john',
                    'id_fragment': 'person-john',  # Custom fragment for referencing
                    'properties': {'name': 'John Doe'}
                }
            ]
        """
        await self.initialize()

        graph_entities = []
        entity_id_map = {}  # Map fragments to full @id values

        # First pass: Generate all @id values
        for entity in entities:
            entity_type = entity['type']
            slug = entity.get('slug')
            id_fragment = entity.get('id_fragment', entity_type.lower())

            # Generate @id
            entity_id = self.generate_entity_id(base_url, entity_type, slug)
            entity_id_map[id_fragment] = entity_id

        # Second pass: Build complete entity objects with relationships
        for entity in entities:
            entity_type = entity['type']
            slug = entity.get('slug')
            id_fragment = entity.get('id_fragment', entity_type.lower())
            properties = entity.get('properties', {})
            relationships = entity.get('relationships', {})

            # Get type info
            type_info = await self.get_schema_type(entity_type)

            # Build entity
            entity_obj: Dict[str, Any] = {
                '@type': type_info['name'],
                '@id': entity_id_map[id_fragment]
            }

            # Add properties
            entity_obj.update(properties)

            # Add URL if slug provided
            if slug:
                entity_obj['url'] = f"{base_url.rstrip('/')}/{slug.lstrip('/')}"

            # Add relationships using @id references
            for rel_property, target_fragments in relationships.items():
                # Handle both single values and lists
                if isinstance(target_fragments, list):
                    # Multiple relationships
                    entity_obj[rel_property] = []
                    for target_fragment in target_fragments:
                        if target_fragment in entity_id_map:
                            entity_obj[rel_property].append({'@id': entity_id_map[target_fragment]})
                        else:
                            entity_obj[rel_property].append(target_fragment)
                else:
                    # Single relationship
                    if target_fragments in entity_id_map:
                        entity_obj[rel_property] = {'@id': entity_id_map[target_fragments]}
                    else:
                        entity_obj[rel_property] = target_fragments

            graph_entities.append(entity_obj)

        return {
            '@context': 'https://schema.org',
            '@graph': graph_entities
        }


# Global schema.org client instance
_schema_org_client: Optional[SchemaOrgClient] = None

def get_schema_org_client() -> SchemaOrgClient:
    """Get or create the global schema.org client."""
    global _schema_org_client
    if _schema_org_client is None:
        _schema_org_client = SchemaOrgClient()
    return _schema_org_client


# Initialize FastMCP server
mcp = FastMCP("ast-grep-schema-org")

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
            sentry_sdk.capture_exception(e, extras={
                "tool": "dump_syntax_tree",
                "language": language,
                "format": format,
                "code_length": len(code),
                "execution_time_seconds": round(execution_time, 3)
            })
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
            sentry_sdk.capture_exception(e, extras={
                "tool": "test_match_code_rule",
                "rule_id": parsed_yaml.get('id'),
                "language": parsed_yaml.get('language'),
                "code_length": len(code),
                "execution_time_seconds": round(execution_time, 3)
            })
            raise

    @mcp.tool()
    def find_code(
        project_folder: str = Field(description = "The absolute path to the project folder. It must be absolute path."),
        pattern: str = Field(description = "The ast-grep pattern to search for. Note, the pattern must have valid AST structure."),
        language: str = Field(description = f"The language of the code. Supported: {', '.join(get_supported_languages())}. "
                                           "If not specified, will be auto-detected based on file extensions.", default = ""),
        max_results: int = Field(default = 0, description = "Maximum results to return"),
        output_format: str = Field(default = "text", description = "'text' or 'json'"),
        max_file_size_mb: int = Field(default = 0, description = "Skip files larger than this size in MB. 0 = unlimited (default). "
                                                                   "Useful for excluding large generated/minified files."),
        workers: int = Field(default = 0, description = "Number of parallel worker threads. 0 = auto (default, uses ast-grep heuristics). "
                                                         "Higher values can speed up searches on large codebases with multiple CPU cores."),
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
            output_format=output_format,
            max_file_size_mb=max_file_size_mb if max_file_size_mb > 0 else "unlimited",
            workers=workers if workers > 0 else "auto"
        )

        try:
            if output_format not in ["text", "json"]:
                raise ValueError(f"Invalid output_format: {output_format}. Must be 'text' or 'json'.")

            # Filter files by size if max_file_size_mb is set
            search_targets = [project_folder]  # Default: search entire directory
            if max_file_size_mb > 0:
                files_to_search, skipped_files = filter_files_by_size(
                    project_folder,
                    max_size_mb=max_file_size_mb,
                    language=language if language else None
                )
                if files_to_search:
                    search_targets = files_to_search
                    logger.info(
                        "file_size_filtering_applied",
                        tool="find_code",
                        files_to_search=len(files_to_search),
                        files_skipped=len(skipped_files),
                        max_size_mb=max_file_size_mb
                    )
                elif skipped_files:
                    # All files were skipped
                    logger.warning(
                        "all_files_skipped_by_size",
                        tool="find_code",
                        total_files=len(skipped_files),
                        max_size_mb=max_file_size_mb
                    )
                    # Return empty result
                    return "No matches found (all files exceeded size limit)" if output_format == "text" else []
                # If no files found at all, continue with directory search (ast-grep will handle it)

            args = ["--pattern", pattern]
            if language:
                args.extend(["--lang", language])
            if workers > 0:
                args.extend(["--threads", str(workers)])

            # Build ast-grep arguments with search targets
            stream_args = args + ["--json=stream"] + search_targets

            # Check cache first
            cache = get_query_cache()
            cached_result = None
            if cache:
                cached_result = cache.get("run", stream_args, project_folder)
                if cached_result is not None:
                    # Apply max_results limit to cached results
                    matches = cached_result[:max_results] if max_results > 0 else cached_result
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
                    stream_args,
                    max_results=max_results,
                    progress_interval=100
                ))

                # Store in cache if available
                if cache:
                    cache.put("run", stream_args, project_folder, matches)
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
            sentry_sdk.capture_exception(e, extras={
                "tool": "find_code",
                "project_folder": project_folder,
                "pattern": pattern[:100],
                "language": language,
                "output_format": output_format,
                "execution_time_seconds": round(execution_time, 3)
            })
            raise

    @mcp.tool()
    def find_code_by_rule(
        project_folder: str = Field(description = "The absolute path to the project folder. It must be absolute path."),
        yaml_rule: str = Field(description = "The ast-grep YAML rule to search. It must have id, language, rule fields."),
        max_results: int = Field(default = 0, description = "Maximum results to return"),
        output_format: str = Field(default = "text", description = "'text' or 'json'"),
        max_file_size_mb: int = Field(default = 0, description = "Skip files larger than this size in MB. 0 = unlimited (default). "
                                                                   "Useful for excluding large generated/minified files."),
        workers: int = Field(default = 0, description = "Number of parallel worker threads. 0 = auto (default, uses ast-grep heuristics). "
                                                         "Higher values can speed up searches on large codebases with multiple CPU cores."),
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
            output_format=output_format,
            max_file_size_mb=max_file_size_mb if max_file_size_mb > 0 else "unlimited",
            workers=workers if workers > 0 else "auto"
        )

        try:
            # Filter files by size if max_file_size_mb is set
            search_targets = [project_folder]  # Default: search entire directory
            if max_file_size_mb > 0:
                rule_language = parsed_yaml.get('language', '')
                files_to_search, skipped_files = filter_files_by_size(
                    project_folder,
                    max_size_mb=max_file_size_mb,
                    language=rule_language if rule_language else None
                )
                if files_to_search:
                    search_targets = files_to_search
                    logger.info(
                        "file_size_filtering_applied",
                        tool="find_code_by_rule",
                        files_to_search=len(files_to_search),
                        files_skipped=len(skipped_files),
                        max_size_mb=max_file_size_mb
                    )
                elif skipped_files:
                    # All files were skipped
                    logger.warning(
                        "all_files_skipped_by_size",
                        tool="find_code_by_rule",
                        total_files=len(skipped_files),
                        max_size_mb=max_file_size_mb
                    )
                    # Return empty result
                    return "No matches found (all files exceeded size limit)" if output_format == "text" else []
                # If no files found at all, continue with directory search (ast-grep will handle it)

            args = ["--inline-rules", yaml_rule]
            if workers > 0:
                args.extend(["--threads", str(workers)])

            # Build ast-grep arguments with search targets
            stream_args = args + ["--json=stream"] + search_targets

            # Check cache first
            cache = get_query_cache()
            cached_result = None
            if cache:
                cached_result = cache.get("scan", stream_args, project_folder)
                if cached_result is not None:
                    # Apply max_results limit to cached results
                    matches = cached_result[:max_results] if max_results > 0 else cached_result
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
                    stream_args,
                    max_results=max_results,
                    progress_interval=100
                ))

                # Store in cache if available
                if cache:
                    cache.put("scan", stream_args, project_folder, matches)
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
            sentry_sdk.capture_exception(e, extras={
                "tool": "find_code_by_rule",
                "project_folder": project_folder,
                "yaml_rule": yaml_rule[:200],
                "max_results": max_results,
                "output_format": output_format,
                "execution_time_seconds": round(execution_time, 3)
            })
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
        max_constructs: int = Field(
            default=1000,
            description=(
                "Maximum number of constructs to analyze (performance optimization). "
                "For large codebases, limiting this prevents excessive computation. "
                "Set to 0 for unlimited. Default: 1000"
            )
        ),
        exclude_patterns: List[str] = Field(
            default_factory=lambda: ["site-packages", "node_modules", ".venv", "venv", "vendor"],
            description=(
                "List of path patterns to exclude from analysis (e.g., library code). "
                "Files matching any of these patterns will be skipped. "
                "Default: ['site-packages', 'node_modules', '.venv', 'venv', 'vendor']"
            )
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
            min_lines=min_lines,
            max_constructs=max_constructs,
            exclude_patterns=exclude_patterns
        )

        try:
            # Validate parameters
            if min_similarity < 0.0 or min_similarity > 1.0:
                raise ValueError("min_similarity must be between 0.0 and 1.0")
            if min_lines < 1:
                raise ValueError("min_lines must be at least 1")
            if max_constructs < 0:
                raise ValueError("max_constructs must be 0 (unlimited) or positive")

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

            # Use streaming to get matches (limit if max_constructs set)
            stream_limit = max_constructs if max_constructs > 0 else 0
            all_matches = list(stream_ast_grep_results(
                "run",
                args + ["--json=stream", project_folder],
                max_results=stream_limit,
                progress_interval=100
            ))

            # Filter out excluded paths (e.g., library code)
            if exclude_patterns:
                matches_before = len(all_matches)
                all_matches = [
                    match for match in all_matches
                    if not any(pattern in match.get('file', '') for pattern in exclude_patterns)
                ]
                if matches_before > len(all_matches):
                    logger.info(
                        "excluded_matches",
                        total_before=matches_before,
                        total_after=len(all_matches),
                        excluded_count=matches_before - len(all_matches),
                        patterns=exclude_patterns
                    )

            # Log if we hit the limit
            if max_constructs > 0 and len(all_matches) >= max_constructs:
                logger.info(
                    "construct_limit_reached",
                    total_found=len(all_matches),
                    max_constructs=max_constructs,
                    message=f"Analysis limited to first {max_constructs} constructs for performance"
                )

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
                        "potential_line_savings": 0,
                        "files_with_imports": 0,
                        "analysis_time_seconds": round(execution_time, 3)
                    },
                    "duplication_groups": [],
                    "file_imports": {},
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

            # Extract imports from files containing duplicates
            duplicate_files = []
            for group in duplication_groups:
                for match in group:
                    file_path = match.get('file', '')
                    if file_path and file_path not in duplicate_files:
                        duplicate_files.append(file_path)

            file_imports = extract_imports_from_files(duplicate_files, language)

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
                    instance_data: Dict[str, Any] = {
                        "file": file_path,
                        "lines": f"{start_line}-{end_line}",
                        "code_preview": match.get('text', '')[:200]  # First 200 chars
                    }
                    # Add imports for this file if available
                    if file_path in file_imports:
                        instance_data["imports"] = file_imports[file_path]
                    instances.append(instance_data)

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
                    "files_with_imports": len(file_imports),
                    "analysis_time_seconds": round(execution_time, 3)
                },
                "duplication_groups": formatted_groups,
                "file_imports": file_imports,
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
            sentry_sdk.capture_exception(e, extras={
                "tool": "find_duplication",
                "project_folder": project_folder,
                "language": language,
                "construct_type": construct_type,
                "min_similarity": min_similarity,
                "execution_time_seconds": round(execution_time, 3)
            })
            raise

    # Phase 3.5: Syntax Validation Pipeline for Deduplication
    @mcp.tool()
    def apply_deduplication(
        project_folder: str = Field(description="The absolute path to the project folder"),
        group_id: int = Field(description="The duplication group ID from find_duplication results"),
        refactoring_plan: Dict[str, Any] = Field(description="The refactoring plan with generated_code, files_affected, strategy, language"),
        dry_run: bool = Field(default=True, description="Preview changes without applying (default: true for safety)"),
        backup: bool = Field(default=True, description="Create backup before applying changes (default: true)"),
        extract_to_file: Optional[str] = Field(default=None, description="Where to place extracted function (auto-detect if None)")
    ) -> Dict[str, Any]:
        """
        Apply automated deduplication refactoring with comprehensive syntax validation.

        Phase 3.5 VALIDATION PIPELINE:
        1. PRE-VALIDATION: Validate all generated code before applying
        2. APPLICATION: Create backup and apply changes
        3. POST-VALIDATION: Validate modified files
        4. AUTO-ROLLBACK: Restore from backup if validation fails

        Returns:
        - status: "preview" | "success" | "failed" | "rolled_back"
        - validation: Pre and post validation results with detailed errors
        - errors: Detailed error info with file, line, message, and suggested fix
        """
        logger = get_logger("tool.apply_deduplication")

        logger.info(
            "tool_invoked",
            tool="apply_deduplication",
            project_folder=project_folder,
            group_id=group_id,
            dry_run=dry_run,
            backup=backup
        )

        try:
            if not os.path.isdir(project_folder):
                raise ValueError(f"Project folder does not exist: {project_folder}")

            if not refactoring_plan:
                raise ValueError("refactoring_plan is required")

            files_affected = refactoring_plan.get("files_affected", [])
            generated_code = refactoring_plan.get("generated_code", {})
            language = refactoring_plan.get("language", "python")

            validation_result: Dict[str, Any] = {
                "pre_validation": {"passed": False, "errors": []},
                "post_validation": {"passed": False, "errors": []}
            }

            if not files_affected:
                return {"status": "no_changes", "message": "No files affected", "dry_run": dry_run, "validation": validation_result}

            files_to_modify = []
            for file_info in files_affected:
                file_path = file_info if isinstance(file_info, str) else file_info.get("file", "")
                if file_path and os.path.isfile(file_path):
                    files_to_modify.append(file_path)
                elif file_path and os.path.isfile(os.path.join(project_folder, file_path)):
                    files_to_modify.append(os.path.join(project_folder, file_path))

            if not files_to_modify:
                return {"status": "no_files", "message": "No valid files found", "dry_run": dry_run, "validation": validation_result}

            # Phase 3.3: Multi-File Orchestration
            # Plan file modification order for atomicity
            orchestration_plan = _plan_file_modification_order(
                files_to_modify=files_to_modify,
                generated_code=generated_code,
                extract_to_file=extract_to_file,
                project_folder=project_folder,
                language=language
            )

            logger.info(
                "orchestration_planned",
                create_files=len(orchestration_plan.get("create_files", [])),
                update_files=len(orchestration_plan.get("update_files", [])),
                import_additions=len(orchestration_plan.get("import_additions", {}))
            )

            # PRE-VALIDATION
            logger.info("pre_validation_start", stage="pre_validation")
            pre_validation_errors: List[Dict[str, Any]] = []

            extracted_function = generated_code.get("extracted_function", "")
            if extracted_function:
                is_valid, error_msg = _validate_code_for_language(extracted_function, language)
                if not is_valid:
                    pre_validation_errors.append({
                        "type": "extracted_function",
                        "file": extract_to_file or "target file",
                        "error": error_msg,
                        "code_preview": extracted_function[:200],
                        "suggestion": _suggest_syntax_fix(error_msg, language)
                    })

            replacements = generated_code.get("replacements", {})
            for file_path, replacement in replacements.items():
                new_content = replacement.get("new_content", "")
                if new_content:
                    is_valid, error_msg = _validate_code_for_language(new_content, language)
                    if not is_valid:
                        pre_validation_errors.append({
                            "type": "replacement_code",
                            "file": file_path,
                            "error": error_msg,
                            "suggestion": _suggest_syntax_fix(error_msg, language)
                        })

            validation_result["pre_validation"] = {
                "passed": len(pre_validation_errors) == 0,
                "errors": pre_validation_errors
            }

            if pre_validation_errors:
                return {
                    "status": "failed",
                    "dry_run": dry_run,
                    "message": f"Pre-validation failed with {len(pre_validation_errors)} error(s)",
                    "validation": validation_result,
                    "errors": pre_validation_errors,
                    "group_id": group_id
                }

            # DRY RUN
            strategy = refactoring_plan.get("strategy", "extract_function")
            if dry_run:
                changes_preview = []
                for fp in files_to_modify:
                    with open(fp, 'r') as f:
                        changes_preview.append({"file": fp, "lines": len(f.read().splitlines())})
                return {
                    "status": "preview",
                    "dry_run": True,
                    "message": f"Preview of changes to {len(files_to_modify)} file(s)",
                    "changes_preview": changes_preview,
                    "validation": validation_result,
                    "group_id": group_id,
                    "strategy": strategy
                }

            # APPLICATION - Phase 3.3 Enhanced Multi-File Orchestration
            backup_id: Optional[str] = None
            strategy = refactoring_plan.get("strategy", "extract_function")

            # Determine all files that will be affected (including new files)
            all_affected_files = list(files_to_modify)
            create_files = orchestration_plan.get("create_files", [])
            for create_info in create_files:
                target_path = create_info.get("path", "")
                if target_path and target_path not in all_affected_files:
                    # Only backup if file already exists
                    if os.path.exists(target_path):
                        all_affected_files.append(target_path)

            if backup:
                # Compute hashes of original files for integrity verification
                original_hashes: Dict[str, str] = {}
                for file_path in all_affected_files:
                    if os.path.exists(file_path):
                        original_hashes[file_path] = get_file_hash(file_path)

                # Create deduplication-specific backup with metadata
                backup_id = create_deduplication_backup(
                    files_to_backup=[fp for fp in all_affected_files if os.path.exists(fp)],
                    project_folder=project_folder,
                    duplicate_group_id=group_id,
                    strategy=strategy,
                    original_hashes=original_hashes
                )

            modified_files = []
            failed_files: List[Dict[str, Any]] = []

            try:
                # Step 1: Create new files for extracted functions (must be first)
                for create_info in orchestration_plan.get("create_files", []):
                    target_path = create_info.get("path", "")
                    content = create_info.get("content", "")

                    if not target_path or not content:
                        continue

                    try:
                        # Ensure directory exists
                        target_dir = os.path.dirname(target_path)
                        if target_dir and not os.path.exists(target_dir):
                            os.makedirs(target_dir, exist_ok=True)

                        # Handle append vs create
                        mode = 'a' if os.path.exists(target_path) and create_info.get("append", False) else 'w'
                        prefix = "\n\n" if mode == 'a' else ""

                        with open(target_path, mode) as f:
                            f.write(prefix + content)

                        modified_files.append(target_path)
                        logger.info("file_created", file=target_path, mode=mode)

                    except Exception as e:
                        failed_files.append({
                            "file": target_path,
                            "operation": "create",
                            "error": str(e)
                        })
                        raise  # Fail fast for atomicity

                # Step 2: Update duplicate location files with replacements and imports
                for update_info in orchestration_plan.get("update_files", []):
                    file_path = update_info.get("path", "")

                    if not file_path or not os.path.exists(file_path):
                        continue

                    try:
                        # Read current content
                        with open(file_path, 'r') as f:
                            current_content = f.read()

                        new_content = current_content

                        # Apply replacement from generated_code
                        replacement = replacements.get(file_path, {})
                        if replacement.get("new_content"):
                            new_content = replacement["new_content"]

                        # Add import statement if needed
                        import_info = orchestration_plan.get("import_additions", {}).get(file_path)
                        if import_info:
                            new_content = _add_import_to_content(
                                content=new_content,
                                import_statement=import_info.get("import_statement", ""),
                                language=language
                            )

                        # Write updated content
                        with open(file_path, 'w') as f:
                            f.write(new_content)

                        if file_path not in modified_files:
                            modified_files.append(file_path)
                        logger.info("file_updated", file=file_path)

                    except Exception as e:
                        failed_files.append({
                            "file": file_path,
                            "operation": "update",
                            "error": str(e)
                        })
                        raise  # Fail fast for atomicity

                # Step 3: Handle legacy flow for files not in orchestration plan
                for fp in files_to_modify:
                    if fp in [u.get("path") for u in orchestration_plan.get("update_files", [])]:
                        continue  # Already handled

                    replacement = replacements.get(fp, {})
                    if replacement.get("new_content"):
                        try:
                            with open(fp, 'w') as f:
                                f.write(replacement["new_content"])
                            if fp not in modified_files:
                                modified_files.append(fp)
                        except Exception as e:
                            failed_files.append({
                                "file": fp,
                                "operation": "update",
                                "error": str(e)
                            })
                            raise

            except Exception as e:
                # Atomic rollback on any failure
                if backup_id:
                    restored = restore_from_backup(backup_id, project_folder)
                    logger.warning(
                        "orchestration_rollback",
                        backup_id=backup_id,
                        files_restored=len(restored),
                        failed_files=failed_files,
                        error=str(e)
                    )
                raise

            # POST-VALIDATION
            post_validation_errors: List[Dict[str, Any]] = []
            for fp in modified_files:
                if os.path.exists(fp):
                    result = validate_syntax(fp, language)
                    if not result["valid"]:
                        post_validation_errors.append({
                            "type": "modified_file",
                            "file": fp,
                            "error": result.get("error", ""),
                            "suggestion": _suggest_syntax_fix(result.get("error"), language)
                        })

            validation_result["post_validation"] = {
                "passed": len(post_validation_errors) == 0,
                "errors": post_validation_errors
            }

            # AUTO-ROLLBACK
            if post_validation_errors and backup_id:
                restored = restore_from_backup(backup_id, project_folder)
                return {
                    "status": "rolled_back",
                    "message": f"Rolled back due to {len(post_validation_errors)} validation error(s)",
                    "files_restored": restored,
                    "backup_id": backup_id,
                    "validation": validation_result,
                    "errors": post_validation_errors,
                    "group_id": group_id
                }

            return {
                "status": "success",
                "dry_run": False,
                "message": f"Applied deduplication to {len(modified_files)} file(s)",
                "files_modified": modified_files,
                "backup_id": backup_id,
                "validation": validation_result,
                "group_id": group_id,
                "strategy": strategy,
                "rollback_command": f"rollback_rewrite(project_folder='{project_folder}', backup_id='{backup_id}')"
            }

        except Exception as e:
            logger.error("tool_failed", tool="apply_deduplication", error=str(e)[:200])
            sentry_sdk.capture_exception(e)
            raise

    # Phase 4.1: Deduplication Analysis with Prioritization
    @mcp.tool()
    def analyze_deduplication_candidates(
        project_path: str = Field(description="The absolute path to the project folder to analyze"),
        language: str = Field(description=f"The target language. Supported: {', '.join(get_supported_languages())}"),
        min_similarity: float = Field(
            default=0.8,
            description="Minimum similarity threshold (0.0-1.0) to consider as duplicate. Default: 0.8"
        ),
        include_test_coverage: bool = Field(
            default=True,
            description="Whether to check test coverage for prioritization. Default: true"
        ),
        min_lines: int = Field(
            default=5,
            description="Minimum number of lines to consider for duplication. Default: 5"
        ),
        max_candidates: int = Field(
            default=100,
            description="Maximum number of candidates to return. Default: 100"
        ),
        exclude_patterns: List[str] = Field(
            default_factory=lambda: ["site-packages", "node_modules", ".venv", "venv", "vendor", "__pycache__", ".git"],
            description="Path patterns to exclude from analysis"
        ),
    ) -> Dict[str, Any]:
        """
        Analyze a project for deduplication candidates and return ranked results.

        This tool extends find_duplication by:
        1. Scoring duplicates by complexity, frequency, and maintainability impact
        2. Optionally checking test coverage to prioritize well-tested code
        3. Ranking candidates by refactoring value (highest savings + lowest risk first)
        4. Providing actionable recommendations for each candidate group

        Returns:
        - candidates: List of duplicate groups with scores and rankings
        - total_groups: Number of duplication groups found
        - total_savings_potential: Total lines that could be saved
        - analysis_metadata: Timing and configuration info

        Example:
          analyze_deduplication_candidates(
              project_path="/path/to/project",
              language="python",
              min_similarity=0.85,
              include_test_coverage=True
          )
        """
        logger = get_logger("tool.analyze_deduplication_candidates")
        start_time = time.time()

        logger.info(
            "tool_invoked",
            tool="analyze_deduplication_candidates",
            project_path=project_path,
            language=language,
            min_similarity=min_similarity,
            include_test_coverage=include_test_coverage,
            min_lines=min_lines,
            max_candidates=max_candidates
        )

        try:
            # Validate parameters
            if not os.path.isdir(project_path):
                raise ValueError(f"Project path does not exist: {project_path}")

            if min_similarity < 0.0 or min_similarity > 1.0:
                raise ValueError("min_similarity must be between 0.0 and 1.0")

            if min_lines < 1:
                raise ValueError("min_lines must be at least 1")

            if max_candidates < 1:
                raise ValueError("max_candidates must be at least 1")

            # Map language to construct patterns
            construct_patterns = {
                "function_definition": "def $NAME($$$)",
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

            pattern = construct_patterns["function_definition"]

            logger.info(
                "searching_constructs",
                pattern=pattern,
                language=language
            )

            # Find all function constructs using ast-grep streaming
            args = ["--pattern", pattern, "--lang", language]
            all_matches = list(stream_ast_grep_results(
                "run",
                args + ["--json=stream", project_path],
                max_results=0,  # Get all matches
                progress_interval=100
            ))

            # Filter excluded paths
            if exclude_patterns:
                matches_before = len(all_matches)
                all_matches = [
                    match for match in all_matches
                    if not any(pat in match.get('file', '') for pat in exclude_patterns)
                ]
                logger.info(
                    "excluded_matches",
                    total_before=matches_before,
                    total_after=len(all_matches),
                    excluded_count=matches_before - len(all_matches)
                )

            if not all_matches:
                execution_time = time.time() - start_time
                logger.info(
                    "tool_completed",
                    tool="analyze_deduplication_candidates",
                    execution_time_seconds=round(execution_time, 3),
                    total_constructs=0,
                    status="success"
                )
                return {
                    "candidates": [],
                    "total_groups": 0,
                    "total_savings_potential": 0,
                    "analysis_metadata": {
                        "project_path": project_path,
                        "language": language,
                        "total_constructs_analyzed": 0,
                        "analysis_time_seconds": round(execution_time, 3),
                        "min_similarity": min_similarity,
                        "include_test_coverage": include_test_coverage
                    },
                    "message": "No function definitions found in the project"
                }

            # Group duplicates using existing algorithm
            logger.info(
                "analyzing_similarity",
                total_matches=len(all_matches),
                min_similarity=min_similarity
            )

            duplication_groups = group_duplicates(all_matches, min_similarity, min_lines)

            # Score and rank candidates
            candidates: List[Dict[str, Any]] = []
            total_savings = 0

            for idx, group in enumerate(duplication_groups):
                if len(group) < 2:
                    continue

                # Calculate metrics for this group
                group_lines = sum(
                    (match.get('range', {}).get('end', {}).get('line', 0) -
                     match.get('range', {}).get('start', {}).get('line', 0) + 1)
                    for match in group
                )

                avg_lines = group_lines // len(group) if group else 0
                savings = group_lines - avg_lines  # Keep one instance

                # Calculate similarity score for the group
                if len(group) >= 2:
                    similarity = calculate_similarity(
                        group[0].get('text', ''),
                        group[1].get('text', '')
                    )
                else:
                    similarity = 1.0

                # Complexity score (based on code length as proxy)
                complexity_score = min(avg_lines / 50.0, 1.0)  # Normalize to 0-1

                # Frequency score (more instances = higher value)
                frequency_score = min(len(group) / 10.0, 1.0)  # Normalize to 0-1

                # Combined priority score (higher = better candidate)
                priority_score = (
                    similarity * 0.3 +
                    complexity_score * 0.3 +
                    frequency_score * 0.2 +
                    (savings / 100.0) * 0.2  # Normalize savings contribution
                )

                # Format instances
                instances: List[Dict[str, Any]] = []
                files_affected: List[str] = []

                for match in group:
                    file_path = match.get('file', '')
                    start_line = match.get('range', {}).get('start', {}).get('line', 0) + 1
                    end_line = match.get('range', {}).get('end', {}).get('line', 0) + 1

                    instances.append({
                        "file": file_path,
                        "start_line": start_line,
                        "end_line": end_line,
                        "lines": f"{start_line}-{end_line}",
                        "code_preview": match.get('text', '')[:300]
                    })

                    if file_path not in files_affected:
                        files_affected.append(file_path)

                candidate: Dict[str, Any] = {
                    "group_id": idx + 1,
                    "priority_score": round(priority_score, 3),
                    "similarity_score": round(similarity, 3),
                    "instance_count": len(group),
                    "total_lines": group_lines,
                    "avg_lines_per_instance": avg_lines,
                    "potential_savings": savings,
                    "files_affected": files_affected,
                    "instances": instances,
                    "recommendation": _generate_dedup_recommendation(
                        similarity, len(group), avg_lines, savings
                    )
                }

                # Add test coverage info if requested
                if include_test_coverage:
                    candidate["test_coverage"] = {
                        "status": "not_implemented",
                        "note": "Test coverage analysis will be implemented in Phase 4.2"
                    }

                candidates.append(candidate)
                total_savings += savings

            # Sort by priority score (highest first) and limit results
            candidates.sort(key=lambda x: x["priority_score"], reverse=True)
            candidates = candidates[:max_candidates]

            # Add rank to each candidate
            for rank, candidate in enumerate(candidates, 1):
                candidate["rank"] = rank

            execution_time = time.time() - start_time

            logger.info(
                "tool_completed",
                tool="analyze_deduplication_candidates",
                execution_time_seconds=round(execution_time, 3),
                total_constructs=len(all_matches),
                total_groups=len(candidates),
                total_savings=total_savings,
                status="success"
            )

            return {
                "candidates": candidates,
                "total_groups": len(candidates),
                "total_savings_potential": total_savings,
                "analysis_metadata": {
                    "project_path": project_path,
                    "language": language,
                    "total_constructs_analyzed": len(all_matches),
                    "analysis_time_seconds": round(execution_time, 3),
                    "min_similarity": min_similarity,
                    "min_lines": min_lines,
                    "include_test_coverage": include_test_coverage,
                    "max_candidates": max_candidates
                },
                "message": f"Found {len(candidates)} deduplication candidate(s) with potential to save {total_savings} lines"
            }

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "tool_failed",
                tool="analyze_deduplication_candidates",
                execution_time_seconds=round(execution_time, 3),
                error=str(e)[:200],
                status="failed"
            )
            sentry_sdk.capture_exception(e, extras={
                "tool": "analyze_deduplication_candidates",
                "project_path": project_path,
                "language": language,
                "min_similarity": min_similarity,
                "execution_time_seconds": round(execution_time, 3)
            })
            raise

    # Schema.org Tools
    @mcp.tool()
    def get_schema_type(
        type_name: str = Field(description="The schema.org type name (e.g., 'Person', 'Organization', 'Article')")
    ) -> Dict[str, Any]:
        """
        Get detailed information about a schema.org type.
        Returns the type's name, description, URL, parent types, and metadata.

        Example: get_schema_type('Person') returns details about the Person type including its properties and parent types.
        """
        logger = get_logger("tool.get_schema_type")
        start_time = time.time()

        logger.info("tool_invoked", tool="get_schema_type", type_name=type_name)

        try:
            client = get_schema_org_client()
            result = asyncio.run(client.get_schema_type(type_name))

            execution_time = time.time() - start_time
            logger.info(
                "tool_completed",
                tool="get_schema_type",
                execution_time_seconds=round(execution_time, 3),
                status="success"
            )

            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "tool_failed",
                tool="get_schema_type",
                execution_time_seconds=round(execution_time, 3),
                error=str(e)[:200],
                status="failed"
            )
            sentry_sdk.capture_exception(e, extras={
                "tool": "get_schema_type",
                "type_name": type_name,
                "execution_time_seconds": round(execution_time, 3)
            })
            raise

    @mcp.tool()
    def search_schemas(
        query: str = Field(description="Search query to find schema types (searches in names and descriptions)"),
        limit: int = Field(default=10, description="Maximum number of results to return (1-100)")
    ) -> List[Dict[str, Any]]:
        """
        Search for schema.org types by keyword.
        Searches through type names and descriptions, returns matching types sorted by relevance.

        Example: search_schemas('blog') finds types like BlogPosting, Blog, etc.
        """
        logger = get_logger("tool.search_schemas")
        start_time = time.time()

        logger.info("tool_invoked", tool="search_schemas", query=query, limit=limit)

        try:
            client = get_schema_org_client()
            results = asyncio.run(client.search_schemas(query, limit))

            execution_time = time.time() - start_time
            logger.info(
                "tool_completed",
                tool="search_schemas",
                execution_time_seconds=round(execution_time, 3),
                result_count=len(results),
                status="success"
            )

            return results
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "tool_failed",
                tool="search_schemas",
                execution_time_seconds=round(execution_time, 3),
                error=str(e)[:200],
                status="failed"
            )
            sentry_sdk.capture_exception(e, extras={
                "tool": "search_schemas",
                "query": query,
                "limit": limit,
                "execution_time_seconds": round(execution_time, 3)
            })
            raise

    @mcp.tool()
    def get_type_hierarchy(
        type_name: str = Field(description="The schema.org type name")
    ) -> Dict[str, Any]:
        """
        Get the inheritance hierarchy for a schema.org type.
        Returns the type's parent types (super types) and child types (sub types).

        Example: get_type_hierarchy('NewsArticle') shows it inherits from Article, which inherits from CreativeWork, etc.
        """
        logger = get_logger("tool.get_type_hierarchy")
        start_time = time.time()

        logger.info("tool_invoked", tool="get_type_hierarchy", type_name=type_name)

        try:
            client = get_schema_org_client()
            result = asyncio.run(client.get_type_hierarchy(type_name))

            execution_time = time.time() - start_time
            logger.info(
                "tool_completed",
                tool="get_type_hierarchy",
                execution_time_seconds=round(execution_time, 3),
                status="success"
            )

            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "tool_failed",
                tool="get_type_hierarchy",
                execution_time_seconds=round(execution_time, 3),
                error=str(e)[:200],
                status="failed"
            )
            sentry_sdk.capture_exception(e, extras={
                "tool": "get_type_hierarchy",
                "type_name": type_name,
                "execution_time_seconds": round(execution_time, 3)
            })
            raise

    @mcp.tool()
    def get_type_properties(
        type_name: str = Field(description="The schema.org type name"),
        include_inherited: bool = Field(default=True, description="Include properties inherited from parent types")
    ) -> List[Dict[str, Any]]:
        """
        Get all properties available for a schema.org type.
        Returns property names, descriptions, and expected value types.

        Example: get_type_properties('Organization') returns properties like name, url, address, founder, etc.
        """
        logger = get_logger("tool.get_type_properties")
        start_time = time.time()

        logger.info("tool_invoked", tool="get_type_properties", type_name=type_name, include_inherited=include_inherited)

        try:
            client = get_schema_org_client()
            results = asyncio.run(client.get_type_properties(type_name, include_inherited))

            execution_time = time.time() - start_time
            logger.info(
                "tool_completed",
                tool="get_type_properties",
                execution_time_seconds=round(execution_time, 3),
                property_count=len(results),
                status="success"
            )

            return results
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "tool_failed",
                tool="get_type_properties",
                execution_time_seconds=round(execution_time, 3),
                error=str(e)[:200],
                status="failed"
            )
            sentry_sdk.capture_exception(e, extras={
                "tool": "get_type_properties",
                "type_name": type_name,
                "include_inherited": include_inherited,
                "execution_time_seconds": round(execution_time, 3)
            })
            raise

    @mcp.tool()
    def generate_schema_example(
        type_name: str = Field(description="The schema.org type name"),
        custom_properties: Optional[Dict[str, Any]] = Field(
            default=None,
            description="Custom property values to include in the example (JSON object)"
        )
    ) -> Dict[str, Any]:
        """
        Generate an example JSON-LD structured data for a schema.org type.
        Creates a valid schema.org JSON-LD object with common properties and any custom values provided.

        Example: generate_schema_example('Recipe', {'name': 'Chocolate Cake', 'prepTime': 'PT30M'})
        """
        logger = get_logger("tool.generate_schema_example")
        start_time = time.time()

        logger.info("tool_invoked", tool="generate_schema_example", type_name=type_name)

        try:
            client = get_schema_org_client()
            result = asyncio.run(client.generate_example(type_name, custom_properties))

            execution_time = time.time() - start_time
            logger.info(
                "tool_completed",
                tool="generate_schema_example",
                execution_time_seconds=round(execution_time, 3),
                status="success"
            )

            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "tool_failed",
                tool="generate_schema_example",
                execution_time_seconds=round(execution_time, 3),
                error=str(e)[:200],
                status="failed"
            )
            sentry_sdk.capture_exception(e, extras={
                "tool": "generate_schema_example",
                "type_name": type_name,
                "has_custom_properties": custom_properties is not None,
                "execution_time_seconds": round(execution_time, 3)
            })
            raise

    @mcp.tool()
    def generate_entity_id(
        base_url: str = Field(description="The canonical URL (e.g., 'https://example.com' or 'https://example.com/page')"),
        entity_type: str = Field(description="The Schema.org type (e.g., 'Organization', 'Person', 'Product')"),
        entity_slug: Optional[str] = Field(
            default=None,
            description="Optional URL slug for specific entity instances (e.g., 'john-doe', 'products/widget-a')"
        )
    ) -> str:
        """
        Generate a proper @id value following Schema.org and SEO best practices.

        Creates stable, unique identifiers for entities that can be referenced across your knowledge graph.
        Based on best practices from https://momenticmarketing.com/blog/id-schema-for-seo-llms-knowledge-graphs

        Examples:
        - Homepage organization: generate_entity_id('https://example.com', 'Organization')
          → 'https://example.com/#organization'

        - Specific product: generate_entity_id('https://example.com', 'Product', 'products/widget-a')
          → 'https://example.com/products/widget-a#product'

        - Team member: generate_entity_id('https://example.com', 'Person', 'team/john-doe')
          → 'https://example.com/team/john-doe#person'

        Best Practices:
        - Use canonical URLs only
        - Keep IDs stable (no timestamps or dynamic values)
        - Use descriptive entity types
        - One unchanging identifier per entity
        """
        logger = get_logger("tool.generate_entity_id")
        start_time = time.time()

        logger.info("tool_invoked", tool="generate_entity_id", base_url=base_url, entity_type=entity_type)

        try:
            client = get_schema_org_client()
            result = client.generate_entity_id(base_url, entity_type, entity_slug)

            execution_time = time.time() - start_time
            logger.info(
                "tool_completed",
                tool="generate_entity_id",
                execution_time_seconds=round(execution_time, 3),
                generated_id=result,
                status="success"
            )

            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "tool_failed",
                tool="generate_entity_id",
                execution_time_seconds=round(execution_time, 3),
                error=str(e)[:200],
                status="failed"
            )
            sentry_sdk.capture_exception(e, extras={
                "tool": "generate_entity_id",
                "base_url": base_url,
                "entity_type": entity_type,
                "has_slug": entity_slug is not None,
                "execution_time_seconds": round(execution_time, 3)
            })
            raise

    @mcp.tool()
    def validate_entity_id(
        entity_id: str = Field(description="The @id value to validate (e.g., 'https://example.com/#organization')")
    ) -> Dict[str, Any]:
        """
        Validate an @id value against Schema.org and SEO best practices.

        Checks for common issues and provides actionable suggestions for improvement.
        Based on best practices from https://momenticmarketing.com/blog/id-schema-for-seo-llms-knowledge-graphs

        Returns:
        - valid: Whether the @id follows all best practices
        - warnings: List of issues found
        - suggestions: Specific improvements to make
        - best_practices: Key principles to follow

        Example:
        validate_entity_id('https://example.com/#organization')
        → { "valid": true, "warnings": [], "suggestions": [] }

        validate_entity_id('example.com/page')
        → { "valid": false, "warnings": ["Missing protocol", "Missing hash fragment"], ... }
        """
        logger = get_logger("tool.validate_entity_id")
        start_time = time.time()

        logger.info("tool_invoked", tool="validate_entity_id", entity_id=entity_id)

        try:
            client = get_schema_org_client()
            result = client.validate_entity_id(entity_id)

            execution_time = time.time() - start_time
            logger.info(
                "tool_completed",
                tool="validate_entity_id",
                execution_time_seconds=round(execution_time, 3),
                is_valid=result['valid'],
                warning_count=len(result['warnings']),
                status="success"
            )

            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "tool_failed",
                tool="validate_entity_id",
                execution_time_seconds=round(execution_time, 3),
                error=str(e)[:200],
                status="failed"
            )
            sentry_sdk.capture_exception(e, extras={
                "tool": "validate_entity_id",
                "entity_id": entity_id,
                "execution_time_seconds": round(execution_time, 3)
            })
            raise

    @mcp.tool()
    def build_entity_graph(
        entities: List[Dict[str, Any]] = Field(
            description="List of entity definitions with type, properties, and relationships"
        ),
        base_url: str = Field(description="Base canonical URL for generating @id values")
    ) -> Dict[str, Any]:
        """
        Build a knowledge graph of related entities with proper @id references.

        Creates a complete @graph structure where entities can reference each other using @id,
        enabling you to build a relational knowledge base over time.
        Based on best practices from https://momenticmarketing.com/blog/id-schema-for-seo-llms-knowledge-graphs

        Entity Definition Format:
        {
            "type": "Organization",           # Required: Schema.org type
            "slug": "about",                  # Optional: URL path segment
            "id_fragment": "org-acme",        # Optional: Custom fragment for referencing
            "properties": {                   # Required: Entity properties
                "name": "Acme Corp",
                "url": "https://example.com"
            },
            "relationships": {                # Optional: References to other entities
                "founder": "person-john"      # References id_fragment of another entity
            }
        }

        Example:
        build_entity_graph([
            {
                "type": "Organization",
                "properties": {"name": "Acme Corp"},
                "relationships": {"founder": "person-john", "employee": "person-jane"}
            },
            {
                "type": "Person",
                "id_fragment": "person-john",
                "slug": "team/john-doe",
                "properties": {"name": "John Doe", "jobTitle": "CEO"}
            },
            {
                "type": "Person",
                "id_fragment": "person-jane",
                "slug": "team/jane-smith",
                "properties": {"name": "Jane Smith", "jobTitle": "CTO"}
            }
        ], "https://example.com")

        Returns complete JSON-LD @graph with all entities properly connected via @id references.
        """
        logger = get_logger("tool.build_entity_graph")
        start_time = time.time()

        logger.info("tool_invoked", tool="build_entity_graph", entity_count=len(entities), base_url=base_url)

        try:
            client = get_schema_org_client()
            result = asyncio.run(client.build_entity_graph(entities, base_url))

            execution_time = time.time() - start_time
            logger.info(
                "tool_completed",
                tool="build_entity_graph",
                execution_time_seconds=round(execution_time, 3),
                entity_count=len(result.get('@graph', [])),
                status="success"
            )

            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "tool_failed",
                tool="build_entity_graph",
                execution_time_seconds=round(execution_time, 3),
                error=str(e)[:200],
                status="failed"
            )
            sentry_sdk.capture_exception(e, extras={
                "tool": "build_entity_graph",
                "entity_count": len(entities),
                "base_url": base_url,
                "execution_time_seconds": round(execution_time, 3)
            })
            raise

    # Code Rewrite Tools
    @mcp.tool()
    def rewrite_code(
        project_folder: str = Field(description="The absolute path to the project folder"),
        yaml_rule: str = Field(description="YAML rule with 'fix' field for code transformation"),
        dry_run: bool = Field(default=True, description="Preview changes without applying (default: true for safety)"),
        backup: bool = Field(default=True, description="Create backup before applying changes (default: true)"),
        max_file_size_mb: int = Field(default=0, description="Skip files larger than this (0 = unlimited)"),
        workers: int = Field(default=0, description="Number of worker threads (0 = auto)")
    ) -> Dict[str, Any]:
        """
        Rewrite code using ast-grep fix rules. Apply automated code transformations safely.

        SAFETY FEATURES:
        - dry_run=True by default (preview before applying)
        - Automatic backups before changes
        - Returns diff preview or list of modified files

        Example YAML Rule:
        ```yaml
        id: replace-var-with-const
        language: javascript
        rule:
          pattern: var $NAME = $VAL
        fix: const $NAME = $VAL
        ```

        Returns:
        - dry_run=True: Preview with diffs showing proposed changes
        - dry_run=False: backup_id and list of modified files
        """
        logger = get_logger("tool.rewrite_code")
        start_time = time.time()

        logger.info(
            "tool_invoked",
            tool="rewrite_code",
            project_folder=project_folder,
            dry_run=dry_run,
            backup=backup,
            workers=workers
        )

        try:
            # Validate YAML rule
            try:
                rule_data = yaml.safe_load(yaml_rule)
            except yaml.YAMLError as e:
                raise InvalidYAMLError(f"Invalid YAML rule: {e}") from e

            if not isinstance(rule_data, dict):
                raise InvalidYAMLError("Rule must be a YAML dictionary")

            if "fix" not in rule_data:
                raise ValueError("Rule must include a 'fix' field for code rewriting")

            if "language" not in rule_data:
                raise ValueError("Rule must include a 'language' field")

            # Write rule to temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
                f.write(yaml_rule)
                rule_file = f.name

            try:
                # Build command args
                args = ["--rule", rule_file]
                if max_file_size_mb > 0:
                    files_to_search, _ = filter_files_by_size(
                        project_folder,
                        max_size_mb=max_file_size_mb,
                        language=rule_data.get("language")
                    )
                    if files_to_search:
                        search_targets = files_to_search
                    else:
                        return {"message": "No files to rewrite (all exceeded size limit)", "changes": []}
                else:
                    search_targets = [project_folder]

                if workers > 0:
                    args.extend(["--threads", str(workers)])

                args.extend(["--json=stream"] + search_targets)

                # DRY RUN MODE: Preview changes
                if dry_run:
                    matches = list(stream_ast_grep_results("scan", args, max_results=0))

                    if not matches:
                        execution_time = time.time() - start_time
                        logger.info(
                            "tool_completed",
                            tool="rewrite_code",
                            execution_time_seconds=round(execution_time, 3),
                            dry_run=True,
                            changes_found=0,
                            status="success"
                        )
                        return {
                            "dry_run": True,
                            "message": "No matches found - no changes would be applied",
                            "changes": []
                        }

                    # Format changes for preview
                    changes = []
                    for match in matches:
                        if "replacement" in match:
                            changes.append({
                                "file": match.get("file", "unknown"),
                                "line": match.get("range", {}).get("start", {}).get("line", 0),
                                "original": match.get("text", ""),
                                "replacement": match["replacement"],
                                "rule_id": match.get("ruleId", "unknown")
                            })

                    execution_time = time.time() - start_time
                    logger.info(
                        "tool_completed",
                        tool="rewrite_code",
                        execution_time_seconds=round(execution_time, 3),
                        dry_run=True,
                        changes_found=len(changes),
                        status="success"
                    )

                    return {
                        "dry_run": True,
                        "message": f"Found {len(changes)} change(s) - set dry_run=false to apply",
                        "changes": changes
                    }

                # ACTUAL REWRITE MODE: Apply changes
                else:
                    # Get list of files that will be modified (before rewrite)
                    preview_matches = list(stream_ast_grep_results("scan", args, max_results=0))
                    files_to_modify = [str(f) for f in set(m.get("file") for m in preview_matches if m.get("file"))]

                    if not files_to_modify:
                        return {
                            "dry_run": False,
                            "message": "No changes applied - no matches found",
                            "modified_files": [],
                            "backup_id": None
                        }

                    # Create backup if requested
                    backup_id: Optional[str] = None
                    if backup:
                        # Call the backup function (avoid name collision with parameter)
                        backup_id = globals()['create_backup'](files_to_modify, project_folder)
                        logger.info("backup_created", backup_id=backup_id, file_count=len(files_to_modify))

                    # Apply rewrite with --update-all
                    rewrite_args = ["--rule", rule_file, "--update-all"] + search_targets
                    if workers > 0:
                        rewrite_args.insert(0, "--threads")
                        rewrite_args.insert(1, str(workers))

                    result = run_ast_grep("scan", rewrite_args)

                    # Validate syntax of rewritten files
                    language = rule_data.get("language", "unknown")
                    validation_summary = validate_rewrites(files_to_modify, language)

                    logger.info(
                        "syntax_validation",
                        validated=validation_summary["validated"],
                        passed=validation_summary["passed"],
                        failed=validation_summary["failed"],
                        skipped=validation_summary["skipped"]
                    )

                    execution_time = time.time() - start_time
                    logger.info(
                        "tool_completed",
                        tool="rewrite_code",
                        execution_time_seconds=round(execution_time, 3),
                        dry_run=False,
                        modified_files=len(files_to_modify),
                        backup_id=backup_id,
                        validation_failed=validation_summary["failed"],
                        status="success"
                    )

                    response = {
                        "dry_run": False,
                        "message": f"Applied changes to {len(files_to_modify)} file(s)",
                        "modified_files": files_to_modify,
                        "backup_id": backup_id,
                        "output": result.stdout,
                        "validation": validation_summary
                    }

                    # Add warning if validation failed
                    if validation_summary["failed"] > 0:
                        response["warning"] = (
                            f"{validation_summary['failed']} file(s) failed syntax validation. "
                            f"Use rollback_rewrite(backup_id='{backup_id}') to restore if needed."
                        )

                    return response

            finally:
                # Clean up temporary rule file
                if os.path.exists(rule_file):
                    os.unlink(rule_file)

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "tool_failed",
                tool="rewrite_code",
                execution_time_seconds=round(execution_time, 3),
                error=str(e)[:200],
                status="failed"
            )
            sentry_sdk.capture_exception(e, extras={
                "tool": "rewrite_code",
                "project_folder": project_folder,
                "dry_run": dry_run,
                "backup_enabled": backup,
                "execution_time_seconds": round(execution_time, 3)
            })
            raise

    @mcp.tool()
    def rollback_rewrite(
        project_folder: str = Field(description="The absolute path to the project folder"),
        backup_id: str = Field(description="The backup identifier to restore from")
    ) -> Dict[str, Any]:
        """
        Rollback a previous code rewrite by restoring files from backup.

        Use list_backups() to see available backups.

        Returns list of restored files.
        """
        logger = get_logger("tool.rollback_rewrite")
        start_time = time.time()

        logger.info("tool_invoked", tool="rollback_rewrite", backup_id=backup_id)

        try:
            restored_files = restore_from_backup(backup_id, project_folder)

            execution_time = time.time() - start_time
            logger.info(
                "tool_completed",
                tool="rollback_rewrite",
                execution_time_seconds=round(execution_time, 3),
                restored_files=len(restored_files),
                status="success"
            )

            return {
                "message": f"Restored {len(restored_files)} file(s) from backup {backup_id}",
                "restored_files": restored_files,
                "backup_id": backup_id
            }

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "tool_failed",
                tool="rollback_rewrite",
                execution_time_seconds=round(execution_time, 3),
                error=str(e)[:200],
                status="failed"
            )
            sentry_sdk.capture_exception(e, extras={
                "tool": "rollback_rewrite",
                "project_folder": project_folder,
                "backup_id": backup_id,
                "execution_time_seconds": round(execution_time, 3)
            })
            raise

    @mcp.tool()
    def list_backups(
        project_folder: str = Field(description="The absolute path to the project folder")
    ) -> List[Dict[str, Any]]:
        """
        List all available backups for a project.

        Returns list of backups sorted by timestamp (newest first).
        Each backup includes: backup_id, timestamp, file_count, and list of files.
        """
        logger = get_logger("tool.list_backups")
        start_time = time.time()

        logger.info("tool_invoked", tool="list_backups", project_folder=project_folder)

        try:
            backups = list_available_backups(project_folder)

            execution_time = time.time() - start_time
            logger.info(
                "tool_completed",
                tool="list_backups",
                execution_time_seconds=round(execution_time, 3),
                backup_count=len(backups),
                status="success"
            )

            return backups

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "tool_failed",
                tool="list_backups",
                execution_time_seconds=round(execution_time, 3),
                error=str(e)[:200],
                status="failed"
            )
            sentry_sdk.capture_exception(e, extras={
                "tool": "list_backups",
                "project_folder": project_folder,
                "execution_time_seconds": round(execution_time, 3)
            })
            raise

    # Batch Operations
    @mcp.tool()
    def batch_search(
        project_folder: str = Field(description="The absolute path to the project folder"),
        queries: List[Dict[str, Any]] = Field(description="List of search specifications to execute"),
        deduplicate: bool = Field(default=True, description="Remove duplicate matches across queries"),
        max_results_per_query: int = Field(default=0, description="Limit results per query (0 = unlimited)"),
        output_format: Literal["text", "json"] = Field(default="json", description="Output format")
    ) -> Dict[str, Any]:
        """
        Execute multiple code searches in parallel and aggregate results.

        Each query in the list should have:
        - type: "pattern" or "rule" (required)
        - pattern: Search pattern (for type="pattern")
        - yaml_rule: YAML rule (for type="rule")
        - language: Programming language (for pattern searches)
        - id: Optional identifier for the query
        - condition: Optional - {"type": "if_matches"|"if_no_matches", "query_id": "id"}

        Example queries:
        ```json
        [
          {
            "id": "find_todos",
            "type": "pattern",
            "pattern": "TODO: $MSG",
            "language": "python"
          },
          {
            "id": "find_fixmes",
            "type": "pattern",
            "pattern": "FIXME: $MSG",
            "language": "python",
            "condition": {"type": "if_matches", "query_id": "find_todos"}
          }
        ]
        ```

        Returns:
        - total_queries: Number of queries executed
        - total_matches: Total matches found (after deduplication)
        - queries_executed: List of query IDs executed
        - matches: Aggregated results
        - per_query_stats: Statistics per query
        """
        logger = get_logger("tool.batch_search")
        start_time = time.time()

        logger.info(
            "tool_invoked",
            tool="batch_search",
            project_folder=project_folder,
            query_count=len(queries),
            deduplicate=deduplicate
        )

        try:
            import concurrent.futures

            # Validate queries
            for i, query in enumerate(queries):
                if "type" not in query:
                    raise ValueError(f"Query {i}: 'type' field is required")
                if query["type"] not in ["pattern", "rule"]:
                    raise ValueError(f"Query {i}: type must be 'pattern' or 'rule'")

                # Assign ID if not provided
                if "id" not in query:
                    query["id"] = f"query_{i}"

            # Separate conditional and unconditional queries
            unconditional_queries = [q for q in queries if "condition" not in q]
            conditional_queries = [q for q in queries if "condition" in q]

            # Execute unconditional queries in parallel
            results_by_id: Dict[str, List[Dict[str, Any]]] = {}
            queries_executed = []

            def execute_query(query: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
                """Execute a single query and return (query_id, results)."""
                query_id = query["id"]
                query_type = query["type"]

                try:
                    if query_type == "pattern":
                        # Pattern search
                        if "pattern" not in query:
                            raise ValueError(f"Query {query_id}: 'pattern' field required for type='pattern'")
                        if "language" not in query:
                            raise ValueError(f"Query {query_id}: 'language' field required for type='pattern'")

                        # Use find_code tool
                        result = find_code(
                            project_folder=project_folder,
                            pattern=query["pattern"],
                            language=query["language"],
                            output_format="json",
                            max_results=max_results_per_query
                        )
                        matches = json.loads(result) if isinstance(result, str) else result

                    elif query_type == "rule":
                        # Rule search
                        if "yaml_rule" not in query:
                            raise ValueError(f"Query {query_id}: 'yaml_rule' field required for type='rule'")

                        # Use find_code_by_rule tool
                        result = find_code_by_rule(
                            project_folder=project_folder,
                            yaml_rule=query["yaml_rule"],
                            output_format="json",
                            max_results=max_results_per_query
                        )
                        matches = json.loads(result) if isinstance(result, str) else result

                    else:
                        matches = []

                    # Add query_id to each match for traceability
                    for match in matches:
                        match["query_id"] = query_id

                    return (query_id, matches)

                except Exception as e:
                    logger.warning("query_failed", query_id=query_id, error=str(e)[:200])
                    return (query_id, [])

            # Execute unconditional queries in parallel
            with sentry_sdk.start_span(op="batch.parallel_search", name="Execute queries in parallel") as span:
                span.set_data("query_count", len(unconditional_queries))
                with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                    futures = [executor.submit(execute_query, q) for q in unconditional_queries]
                    for future in concurrent.futures.as_completed(futures):
                        query_id, matches = future.result()
                        results_by_id[query_id] = matches
                        queries_executed.append(query_id)
                span.set_data("results_count", len(queries_executed))

            # Execute conditional queries sequentially
            for query in conditional_queries:
                query_id = query["id"]
                condition = query["condition"]

                # Check condition
                condition_type = condition.get("type")
                condition_query_id = condition.get("query_id")

                if condition_query_id not in results_by_id:
                    logger.warning(
                        "condition_query_not_found",
                        query_id=query_id,
                        condition_query_id=condition_query_id
                    )
                    continue

                condition_results = results_by_id[condition_query_id]
                has_matches = len(condition_results) > 0

                # Evaluate condition
                should_execute = False
                if condition_type == "if_matches" and has_matches:
                    should_execute = True
                elif condition_type == "if_no_matches" and not has_matches:
                    should_execute = True

                if should_execute:
                    query_id_result, matches = execute_query(query)
                    results_by_id[query_id_result] = matches
                    queries_executed.append(query_id_result)
                else:
                    logger.info("condition_not_met", query_id=query_id, condition=condition)

            # Aggregate results
            all_matches = []
            for matches in results_by_id.values():
                all_matches.extend(matches)

            # Deduplicate if requested
            if deduplicate:
                seen = set()
                deduplicated = []
                for match in all_matches:
                    # Create key from file + line + text (or just file + line if text not available)
                    file_path = match.get("file", "")
                    line = match.get("range", {}).get("start", {}).get("line", 0)
                    text = match.get("text", "")[:100]  # Use first 100 chars for key
                    key = (file_path, line, text)

                    if key not in seen:
                        seen.add(key)
                        deduplicated.append(match)

                all_matches = deduplicated

            # Sort by file, then line
            all_matches.sort(key=lambda m: (
                m.get("file", ""),
                m.get("range", {}).get("start", {}).get("line", 0)
            ))

            # Calculate per-query statistics
            per_query_stats: Dict[str, Dict[str, Any]] = {}
            for query_id, matches in results_by_id.items():
                per_query_stats[query_id] = {
                    "match_count": len(matches),
                    "executed": True
                }

            # Add stats for non-executed conditional queries
            for query in conditional_queries:
                if query["id"] not in queries_executed:
                    per_query_stats[query["id"]] = {
                        "match_count": 0,
                        "executed": False,
                        "reason": "condition_not_met"
                    }

            execution_time = time.time() - start_time
            logger.info(
                "tool_completed",
                tool="batch_search",
                execution_time_seconds=round(execution_time, 3),
                total_queries=len(queries),
                queries_executed=len(queries_executed),
                total_matches=len(all_matches),
                status="success"
            )

            # Format output
            if output_format == "text":
                formatted_matches = format_matches_as_text(all_matches)
                return {
                    "total_queries": len(queries),
                    "queries_executed": queries_executed,
                    "total_matches": len(all_matches),
                    "per_query_stats": per_query_stats,
                    "matches": formatted_matches
                }
            else:
                return {
                    "total_queries": len(queries),
                    "queries_executed": queries_executed,
                    "total_matches": len(all_matches),
                    "per_query_stats": per_query_stats,
                    "matches": all_matches
                }

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "tool_failed",
                tool="batch_search",
                execution_time_seconds=round(execution_time, 3),
                error=str(e)[:200],
                status="failed"
            )
            sentry_sdk.capture_exception(e, extras={
                "tool": "batch_search",
                "project_folder": project_folder,
                "query_count": len(queries),
                "deduplicate": deduplicate,
                "output_format": output_format,
                "execution_time_seconds": round(execution_time, 3)
            })
            raise

    @mcp.tool()
    def analyze_complexity(
        project_folder: str = Field(description="The absolute path to the project folder to analyze"),
        language: str = Field(description="The programming language (python, typescript, javascript, java)"),
        include_patterns: List[str] = Field(
            default_factory=lambda: ["**/*"],
            description="Glob patterns for files to include (e.g., ['src/**/*.py'])"
        ),
        exclude_patterns: List[str] = Field(
            default_factory=lambda: ["**/node_modules/**", "**/__pycache__/**", "**/venv/**", "**/.venv/**", "**/site-packages/**"],
            description="Glob patterns for files to exclude"
        ),
        cyclomatic_threshold: int = Field(default=10, description="Cyclomatic complexity threshold (default: 10)"),
        cognitive_threshold: int = Field(default=15, description="Cognitive complexity threshold (default: 15)"),
        nesting_threshold: int = Field(default=4, description="Maximum nesting depth threshold (default: 4)"),
        length_threshold: int = Field(default=50, description="Function length threshold in lines (default: 50)"),
        store_results: bool = Field(default=True, description="Store results in database for trend tracking"),
        include_trends: bool = Field(default=False, description="Include historical trend data in response"),
        max_threads: int = Field(default=4, description="Number of parallel threads for analysis (default: 4)")
    ) -> Dict[str, Any]:
        """
        Analyze code complexity metrics for functions in a project.

        Calculates cyclomatic complexity, cognitive complexity, nesting depth, and function length
        for all functions in the specified project. Returns a summary with only functions that
        exceed the configured thresholds.

        Metrics:
        - Cyclomatic Complexity: McCabe's cyclomatic complexity (decision points + 1)
        - Cognitive Complexity: SonarSource cognitive complexity with nesting penalties
        - Nesting Depth: Maximum indentation depth within a function
        - Function Length: Number of lines in the function

        Example usage:
          analyze_complexity(project_folder="/path/to/project", language="python")
          analyze_complexity(project_folder="/path/to/project", language="typescript", cyclomatic_threshold=15)
        """
        logger = get_logger("tool.analyze_complexity")
        start_time = time.time()

        logger.info(
            "tool_invoked",
            tool="analyze_complexity",
            project_folder=project_folder,
            language=language,
            cyclomatic_threshold=cyclomatic_threshold,
            cognitive_threshold=cognitive_threshold,
            nesting_threshold=nesting_threshold,
            length_threshold=length_threshold,
            max_threads=max_threads
        )

        try:
            # Validate language
            supported_langs = ["python", "typescript", "javascript", "java"]
            if language.lower() not in supported_langs:
                raise ValueError(f"Unsupported language '{language}'. Supported: {', '.join(supported_langs)}")

            # Set up thresholds
            thresholds = ComplexityThresholds(
                cyclomatic=cyclomatic_threshold,
                cognitive=cognitive_threshold,
                nesting_depth=nesting_threshold,
                lines=length_threshold
            )

            # Find files to analyze
            import glob
            project_path = Path(project_folder)
            if not project_path.exists():
                raise ValueError(f"Project folder does not exist: {project_folder}")

            # Get language-specific file extensions
            lang_extensions = {
                "python": [".py"],
                "typescript": [".ts", ".tsx"],
                "javascript": [".js", ".jsx"],
                "java": [".java"]
            }
            extensions = lang_extensions.get(language.lower(), [".py"])

            # Find all matching files
            all_files: Set[str] = set()
            for pattern in include_patterns:
                for ext in extensions:
                    glob_pattern = str(project_path / pattern)
                    if not glob_pattern.endswith(ext):
                        if glob_pattern.endswith("*"):
                            glob_pattern = glob_pattern[:-1] + f"*{ext}"
                        else:
                            glob_pattern = glob_pattern + f"/**/*{ext}"
                    for file_path in glob.glob(glob_pattern, recursive=True):
                        all_files.add(file_path)

            # Filter excluded files
            files_to_analyze: List[str] = []
            for file_path in all_files:
                excluded = False
                for exclude_pattern in exclude_patterns:
                    if any(part in file_path for part in exclude_pattern.replace("**", "").replace("*", "").split("/")):
                        excluded = True
                        break
                if not excluded:
                    files_to_analyze.append(file_path)

            logger.info(
                "files_found",
                total_files=len(files_to_analyze),
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns
            )

            if not files_to_analyze:
                execution_time = time.time() - start_time
                return {
                    "summary": {
                        "total_functions": 0,
                        "total_files": 0,
                        "exceeding_threshold": 0,
                        "analysis_time_seconds": round(execution_time, 3)
                    },
                    "functions": [],
                    "message": f"No {language} files found in project matching the include patterns"
                }

            # Analyze files in parallel
            all_functions: List[FunctionComplexity] = []

            def analyze_single_file(file_path: str) -> List[FunctionComplexity]:
                return analyze_file_complexity(file_path, language.lower(), thresholds)

            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                futures = {executor.submit(analyze_single_file, f): f for f in files_to_analyze}
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        all_functions.extend(result)
                    except Exception as e:
                        file_path = futures[future]
                        logger.warning("file_analysis_failed", file=file_path, error=str(e))

            # Filter to only functions exceeding thresholds
            exceeding_functions = [f for f in all_functions if f.exceeds]

            # Sort by combined complexity score (highest first)
            exceeding_functions.sort(
                key=lambda f: f.metrics.cyclomatic + f.metrics.cognitive,
                reverse=True
            )

            # Calculate summary statistics
            total_functions = len(all_functions)
            if total_functions > 0:
                avg_cyclomatic = sum(f.metrics.cyclomatic for f in all_functions) / total_functions
                avg_cognitive = sum(f.metrics.cognitive for f in all_functions) / total_functions
                max_cyclomatic = max(f.metrics.cyclomatic for f in all_functions)
                max_cognitive = max(f.metrics.cognitive for f in all_functions)
                max_nesting = max(f.metrics.nesting_depth for f in all_functions)
            else:
                avg_cyclomatic = avg_cognitive = 0
                max_cyclomatic = max_cognitive = max_nesting = 0

            execution_time = time.time() - start_time
            duration_ms = int(execution_time * 1000)

            # Build results dict for storage
            results_data = {
                "total_functions": total_functions,
                "total_files": len(files_to_analyze),
                "avg_cyclomatic": round(avg_cyclomatic, 2),
                "avg_cognitive": round(avg_cognitive, 2),
                "max_cyclomatic": max_cyclomatic,
                "max_cognitive": max_cognitive,
                "max_nesting": max_nesting,
                "violation_count": len(exceeding_functions),
                "duration_ms": duration_ms
            }

            # Store results if requested
            run_id = None
            stored_at = None
            if store_results:
                try:
                    storage = ComplexityStorage()
                    # Get git info
                    commit_hash = None
                    branch_name = None
                    try:
                        commit_result = subprocess.run(
                            ["git", "rev-parse", "HEAD"],
                            cwd=project_folder, capture_output=True, text=True, timeout=5
                        )
                        if commit_result.returncode == 0:
                            commit_hash = commit_result.stdout.strip() or None
                        branch_result = subprocess.run(
                            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                            cwd=project_folder, capture_output=True, text=True, timeout=5
                        )
                        if branch_result.returncode == 0:
                            branch_name = branch_result.stdout.strip() or None
                    except Exception:
                        pass

                    run_id = storage.store_analysis_run(
                        project_folder, results_data, all_functions, commit_hash, branch_name
                    )
                    stored_at = str(storage.db_path)
                except Exception as e:
                    logger.warning("storage_failed", error=str(e))

            # Get trends if requested
            trends = None
            if include_trends:
                try:
                    storage = ComplexityStorage()
                    trends = storage.get_project_trends(project_folder, days=30)
                except Exception as e:
                    logger.warning("trends_failed", error=str(e))

            logger.info(
                "tool_completed",
                tool="analyze_complexity",
                execution_time_seconds=round(execution_time, 3),
                total_functions=total_functions,
                exceeding_threshold=len(exceeding_functions),
                status="success"
            )

            # Format response
            response: Dict[str, Any] = {
                "summary": {
                    "total_functions": total_functions,
                    "total_files": len(files_to_analyze),
                    "exceeding_threshold": len(exceeding_functions),
                    "avg_cyclomatic": round(avg_cyclomatic, 2),
                    "avg_cognitive": round(avg_cognitive, 2),
                    "max_cyclomatic": max_cyclomatic,
                    "max_cognitive": max_cognitive,
                    "max_nesting": max_nesting,
                    "analysis_time_seconds": round(execution_time, 3)
                },
                "thresholds": {
                    "cyclomatic": cyclomatic_threshold,
                    "cognitive": cognitive_threshold,
                    "nesting_depth": nesting_threshold,
                    "length": length_threshold
                },
                "functions": [
                    {
                        "name": f.function_name,
                        "file": f.file_path,
                        "lines": f"{f.start_line}-{f.end_line}",
                        "cyclomatic": f.metrics.cyclomatic,
                        "cognitive": f.metrics.cognitive,
                        "nesting_depth": f.metrics.nesting_depth,
                        "length": f.metrics.lines,
                        "exceeds": f.exceeds
                    }
                    for f in exceeding_functions
                ],
                "message": f"Found {len(exceeding_functions)} function(s) exceeding complexity thresholds out of {total_functions} total"
            }

            if run_id:
                response["storage"] = {
                    "run_id": run_id,
                    "stored_at": stored_at
                }

            if trends:
                response["trends"] = trends

            return response

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "tool_failed",
                tool="analyze_complexity",
                execution_time_seconds=round(execution_time, 3),
                error=str(e)[:200],
                status="failed"
            )
            sentry_sdk.capture_exception(e, extras={
                "tool": "analyze_complexity",
                "project_folder": project_folder,
                "language": language,
                "execution_time_seconds": round(execution_time, 3)
            })
            raise

    @mcp.tool()
    def detect_code_smells(
        project_folder: str = Field(description="The absolute path to the project folder to analyze"),
        language: str = Field(description="The programming language (python, typescript, javascript, java)"),
        include_patterns: List[str] = Field(
            default_factory=lambda: ["**/*"],
            description="Glob patterns for files to include (e.g., ['src/**/*.py'])"
        ),
        exclude_patterns: List[str] = Field(
            default_factory=lambda: ["**/node_modules/**", "**/__pycache__/**", "**/venv/**", "**/.venv/**", "**/site-packages/**", "**/test*/**", "**/*test*"],
            description="Glob patterns for files to exclude"
        ),
        long_function_lines: int = Field(default=50, description="Line count threshold for long function smell (default: 50)"),
        parameter_count: int = Field(default=5, description="Parameter count threshold for parameter bloat (default: 5)"),
        nesting_depth: int = Field(default=4, description="Nesting depth threshold for deep nesting smell (default: 4)"),
        class_lines: int = Field(default=300, description="Line count threshold for large class smell (default: 300)"),
        class_methods: int = Field(default=20, description="Method count threshold for large class smell (default: 20)"),
        detect_magic_numbers: bool = Field(default=True, description="Whether to detect magic number smells"),
        severity_filter: str = Field(default="all", description="Filter by severity: 'all', 'high', 'medium', 'low'"),
        max_threads: int = Field(default=4, description="Number of parallel threads for analysis (default: 4)")
    ) -> Dict[str, Any]:
        """
        Detect common code smells in a project.

        Identifies patterns that indicate potential design or maintainability issues:
        - Long Functions: Functions exceeding line count threshold
        - Parameter Bloat: Functions with too many parameters
        - Deep Nesting: Excessive nesting depth (if/for/while)
        - Large Classes: Classes with too many methods or lines
        - Magic Numbers: Hard-coded numeric/string literals (excludes 0, 1, -1)

        Each smell includes severity (high/medium/low) and actionable suggestions.

        Example usage:
          detect_code_smells(project_folder="/path/to/project", language="python")
          detect_code_smells(project_folder="/path/to/project", language="typescript", severity_filter="high")
        """
        logger = get_logger("tool.detect_code_smells")
        start_time = time.time()

        logger.info(
            "tool_invoked",
            tool="detect_code_smells",
            project_folder=project_folder,
            language=language,
        )

        try:
            # Validate project folder
            project_path = Path(project_folder)
            if not project_path.exists():
                return {"error": f"Project folder not found: {project_folder}"}
            if not project_path.is_dir():
                return {"error": f"Path is not a directory: {project_folder}"}

            # Get file extension for language
            ext_map = {
                "python": ".py",
                "typescript": ".ts",
                "javascript": ".js",
                "java": ".java"
            }
            file_ext = ext_map.get(language.lower(), ".py")

            # Find all matching files
            all_files = []
            for pattern in include_patterns:
                if not pattern.endswith(file_ext) and not pattern.endswith("*"):
                    pattern = pattern.rstrip("/") + f"/**/*{file_ext}"
                elif pattern.endswith("*") and not pattern.endswith(file_ext):
                    pattern = pattern + file_ext if pattern.endswith("*/") else pattern.rstrip("*") + f"*{file_ext}"

                matches = list(project_path.glob(pattern.lstrip("/")))
                all_files.extend([str(f) for f in matches if f.is_file()])

            # Remove duplicates
            all_files = list(set(all_files))

            # Filter by exclude patterns
            filtered_files = []
            for file_path in all_files:
                excluded = False
                rel_path = str(Path(file_path).relative_to(project_path))
                for exc_pattern in exclude_patterns:
                    from fnmatch import fnmatch
                    if fnmatch(rel_path, exc_pattern.lstrip("/")):
                        excluded = True
                        break
                if not excluded:
                    filtered_files.append(file_path)

            if not filtered_files:
                return {
                    "error": f"No {language} files found matching patterns",
                    "project_folder": project_folder,
                    "include_patterns": include_patterns,
                    "exclude_patterns": exclude_patterns
                }

            # Collect all smells
            all_smells: List[Dict[str, Any]] = []

            # Process files for code smells
            from concurrent.futures import ThreadPoolExecutor

            def analyze_file_for_smells(file_path: str) -> List[Dict[str, Any]]:
                """Analyze a single file for code smells."""
                smells = []
                try:
                    content = Path(file_path).read_text(encoding='utf-8', errors='ignore')
                    lines = content.split('\n')
                    rel_path = str(Path(file_path).relative_to(project_path))

                    # Extract functions and classes from file
                    functions = extract_functions_from_file(file_path, language)
                    classes = _extract_classes_from_file(file_path, language)

                    # Check each function for smells
                    for func in functions:
                        func_name = func.get("name", "unknown")
                        func_start = func.get("start_line", 1)
                        func_end = func.get("end_line", func_start)
                        func_code = func.get("code", "")
                        func_lines = func_end - func_start + 1

                        # 1. Long Function Detection
                        if func_lines > long_function_lines:
                            severity = "high" if func_lines > long_function_lines * 2 else "medium" if func_lines > long_function_lines * 1.5 else "low"
                            smells.append({
                                "type": "long_function",
                                "file": rel_path,
                                "name": func_name,
                                "line": func_start,
                                "severity": severity,
                                "metric": func_lines,
                                "threshold": long_function_lines,
                                "message": f"Function '{func_name}' has {func_lines} lines (threshold: {long_function_lines})",
                                "suggestion": "Consider splitting into smaller, focused functions"
                            })

                        # 2. Parameter Bloat Detection
                        param_count = _count_function_parameters(func_code, language)
                        if param_count > parameter_count:
                            severity = "high" if param_count > parameter_count * 2 else "medium" if param_count > parameter_count + 2 else "low"
                            smells.append({
                                "type": "parameter_bloat",
                                "file": rel_path,
                                "name": func_name,
                                "line": func_start,
                                "severity": severity,
                                "metric": param_count,
                                "threshold": parameter_count,
                                "message": f"Function '{func_name}' has {param_count} parameters (threshold: {parameter_count})",
                                "suggestion": "Consider using a parameter object or builder pattern"
                            })

                        # 3. Deep Nesting Detection
                        max_nesting = calculate_nesting_depth(func_code, language)
                        if max_nesting > nesting_depth:
                            severity = "high" if max_nesting > nesting_depth + 2 else "medium" if max_nesting > nesting_depth + 1 else "low"
                            smells.append({
                                "type": "deep_nesting",
                                "file": rel_path,
                                "name": func_name,
                                "line": func_start,
                                "severity": severity,
                                "metric": max_nesting,
                                "threshold": nesting_depth,
                                "message": f"Function '{func_name}' has nesting depth {max_nesting} (threshold: {nesting_depth})",
                                "suggestion": "Use early returns, extract nested logic, or apply guard clauses"
                            })

                    # Check each class for smells
                    for cls in classes:
                        cls_name = cls.get("name", "unknown")
                        cls_start = cls.get("start_line", 1)
                        cls_end = cls.get("end_line", cls_start)
                        cls_method_count = cls.get("method_count", 0)
                        cls_lines_count = cls_end - cls_start + 1

                        # 4. Large Class Detection
                        is_large = False
                        reason = ""
                        if cls_lines_count > class_lines:
                            is_large = True
                            reason = f"{cls_lines_count} lines (threshold: {class_lines})"
                        if cls_method_count > class_methods:
                            is_large = True
                            reason = f"{cls_method_count} methods (threshold: {class_methods})"

                        if is_large:
                            severity = "high" if cls_lines_count > class_lines * 1.5 or cls_method_count > class_methods * 1.5 else "medium"
                            smells.append({
                                "type": "large_class",
                                "file": rel_path,
                                "name": cls_name,
                                "line": cls_start,
                                "severity": severity,
                                "metric": {"lines": cls_lines_count, "methods": cls_method_count},
                                "threshold": {"lines": class_lines, "methods": class_methods},
                                "message": f"Class '{cls_name}' is too large: {reason}",
                                "suggestion": "Consider splitting into smaller classes following Single Responsibility Principle"
                            })

                    # 5. Magic Number Detection
                    if detect_magic_numbers:
                        magic_numbers = _find_magic_numbers(content, lines, language)
                        for magic in magic_numbers:
                            smells.append({
                                "type": "magic_number",
                                "file": rel_path,
                                "name": magic.get("value"),
                                "line": magic.get("line"),
                                "severity": "low",
                                "metric": magic.get("value"),
                                "threshold": "N/A",
                                "message": f"Magic number '{magic.get('value')}' on line {magic.get('line')}",
                                "suggestion": "Extract to a named constant with meaningful name"
                            })

                except Exception as e:
                    logger.error("file_analysis_failed", file=file_path, error=str(e))

                return smells

            # Analyze files in parallel
            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                results = list(executor.map(analyze_file_for_smells, filtered_files))

            # Flatten results
            for file_smells in results:
                all_smells.extend(file_smells)

            # Filter by severity if requested
            if severity_filter != "all":
                all_smells = [s for s in all_smells if s.get("severity") == severity_filter]

            # Sort by severity (high > medium > low) then by type
            severity_order = {"high": 0, "medium": 1, "low": 2}
            all_smells.sort(key=lambda s: (severity_order.get(s.get("severity", "low"), 3), s.get("type", "")))

            # Generate summary
            smell_counts: Dict[str, int] = {}
            severity_counts: Dict[str, int] = {"high": 0, "medium": 0, "low": 0}
            for smell in all_smells:
                smell_type = smell.get("type", "unknown")
                smell_counts[smell_type] = smell_counts.get(smell_type, 0) + 1
                severity_counts[smell.get("severity", "low")] += 1

            execution_time = time.time() - start_time

            result = {
                "project_folder": project_folder,
                "language": language,
                "files_analyzed": len(filtered_files),
                "total_smells": len(all_smells),
                "summary": {
                    "by_type": smell_counts,
                    "by_severity": severity_counts
                },
                "smells": all_smells,
                "thresholds": {
                    "long_function_lines": long_function_lines,
                    "parameter_count": parameter_count,
                    "nesting_depth": nesting_depth,
                    "class_lines": class_lines,
                    "class_methods": class_methods
                },
                "execution_time_ms": round(execution_time * 1000)
            }

            logger.info(
                "tool_completed",
                tool="detect_code_smells",
                files_analyzed=len(filtered_files),
                total_smells=len(all_smells),
                execution_time_seconds=round(execution_time, 3)
            )

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "tool_failed",
                tool="detect_code_smells",
                error=str(e),
                execution_time_seconds=round(execution_time, 3)
            )
            sentry_sdk.capture_exception(e, extras={
                "tool": "detect_code_smells",
                "project_folder": project_folder,
                "language": language,
                "execution_time_seconds": round(execution_time, 3)
            })
            raise

    @mcp.tool()
    def analyze_dependencies(
        project_folder: str = Field(description="The absolute path to the project folder to analyze"),
        language: str = Field(description="The programming language (python, typescript, javascript, java)"),
        include_patterns: List[str] = Field(
            default_factory=lambda: ["**/*"],
            description="Glob patterns for files to include (e.g., ['src/**/*.py'])"
        ),
        exclude_patterns: List[str] = Field(
            default_factory=lambda: ["**/node_modules/**", "**/__pycache__/**", "**/venv/**", "**/.venv/**", "**/site-packages/**", "**/test*/**"],
            description="Glob patterns for files to exclude"
        ),
        detect_circular: bool = Field(default=True, description="Detect circular dependencies"),
        detect_unused: bool = Field(default=True, description="Detect unused imports"),
        max_threads: int = Field(default=4, description="Number of parallel threads for analysis (default: 4)")
    ) -> Dict[str, Any]:
        """
        Analyze import dependencies in a project.

        Builds a dependency graph and identifies:
        - Import relationships between modules
        - Circular dependencies
        - Unused imports
        - Most imported modules (hubs)

        Example usage:
          analyze_dependencies(project_folder="/path/to/project", language="python")
          analyze_dependencies(project_folder="/path/to/project", language="typescript", detect_unused=False)
        """
        import re
        from collections import defaultdict

        logger = get_logger("tool.analyze_dependencies")
        start_time = time.time()

        logger.info(
            "tool_invoked",
            tool="analyze_dependencies",
            project_folder=project_folder,
            language=language,
        )

        try:
            # Validate project folder
            project_path = Path(project_folder)
            if not project_path.exists():
                return {"error": f"Project folder not found: {project_folder}"}
            if not project_path.is_dir():
                return {"error": f"Path is not a directory: {project_folder}"}

            # Get file extension for language
            ext_map = {
                "python": ".py",
                "typescript": ".ts",
                "javascript": ".js",
                "java": ".java"
            }
            file_ext = ext_map.get(language.lower(), ".py")

            # Find all matching files
            all_files = []
            for pattern in include_patterns:
                if not pattern.endswith(file_ext) and not pattern.endswith("*"):
                    pattern = pattern.rstrip("/") + f"/**/*{file_ext}"
                elif pattern.endswith("*") and not pattern.endswith(file_ext):
                    pattern = pattern + file_ext if pattern.endswith("*/") else pattern.rstrip("*") + f"*{file_ext}"

                matches = list(project_path.glob(pattern.lstrip("/")))
                all_files.extend([str(f) for f in matches if f.is_file()])

            # Remove duplicates
            all_files = list(set(all_files))

            # Filter by exclude patterns
            filtered_files = []
            for file_path in all_files:
                excluded = False
                rel_path = str(Path(file_path).relative_to(project_path))
                for exc_pattern in exclude_patterns:
                    from fnmatch import fnmatch
                    if fnmatch(rel_path, exc_pattern.lstrip("/")):
                        excluded = True
                        break
                if not excluded:
                    filtered_files.append(file_path)

            if not filtered_files:
                return {
                    "error": f"No {language} files found matching patterns",
                    "project_folder": project_folder,
                    "include_patterns": include_patterns,
                    "exclude_patterns": exclude_patterns
                }

            # Build dependency graph
            # dependencies[file] = list of modules it imports
            dependencies: Dict[str, List[str]] = {}
            # imported_by[module] = list of files that import it
            imported_by: Dict[str, List[str]] = defaultdict(list)
            # all_imports[file] = list of import statements with details
            all_imports: Dict[str, List[Dict[str, Any]]] = {}

            def extract_imports(file_path: str) -> List[Dict[str, Any]]:
                """Extract imports from a file."""
                imports = []
                try:
                    content = Path(file_path).read_text(encoding='utf-8', errors='ignore')
                    lines = content.split('\n')

                    if language.lower() == "python":
                        for line_num, line in enumerate(lines, 1):
                            stripped = line.strip()
                            # import module
                            if stripped.startswith("import "):
                                match = re.match(r'import\s+([\w.]+)', stripped)
                                if match:
                                    imports.append({
                                        "module": match.group(1),
                                        "line": line_num,
                                        "type": "import",
                                        "used": False
                                    })
                            # from module import ...
                            elif stripped.startswith("from "):
                                match = re.match(r'from\s+([\w.]+)\s+import\s+(.+)', stripped)
                                if match:
                                    module = match.group(1)
                                    imported_names = match.group(2)
                                    imports.append({
                                        "module": module,
                                        "names": imported_names,
                                        "line": line_num,
                                        "type": "from",
                                        "used": False
                                    })

                    elif language.lower() in ("typescript", "javascript"):
                        for line_num, line in enumerate(lines, 1):
                            stripped = line.strip()
                            # import ... from 'module'
                            match = re.search(r'import\s+.+\s+from\s+[\'"]([^\'"]+)[\'"]', stripped)
                            if match:
                                imports.append({
                                    "module": match.group(1),
                                    "line": line_num,
                                    "type": "import",
                                    "used": False
                                })
                            # require('module')
                            match = re.search(r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)', stripped)
                            if match:
                                imports.append({
                                    "module": match.group(1),
                                    "line": line_num,
                                    "type": "require",
                                    "used": False
                                })

                    elif language.lower() == "java":
                        for line_num, line in enumerate(lines, 1):
                            stripped = line.strip()
                            match = re.match(r'import\s+([\w.]+);', stripped)
                            if match:
                                imports.append({
                                    "module": match.group(1),
                                    "line": line_num,
                                    "type": "import",
                                    "used": False
                                })

                except Exception as e:
                    logger.warning("extract_imports_failed", file=file_path, error=str(e))

                return imports

            # Process files in parallel
            from concurrent.futures import ThreadPoolExecutor

            with ThreadPoolExecutor(max_workers=max_threads) as executor:
                results = list(executor.map(
                    lambda f: (f, extract_imports(f)),
                    filtered_files
                ))

            for file_path, imports in results:
                rel_path = str(Path(file_path).relative_to(project_path))
                all_imports[rel_path] = imports
                dependencies[rel_path] = [imp["module"] for imp in imports]

                for imp in imports:
                    imported_by[imp["module"]].append(rel_path)

            # Detect circular dependencies
            circular_deps = []
            if detect_circular:
                # Simple cycle detection using DFS
                visited = set()
                rec_stack = set()

                def find_cycles(node: str, path: List[str]) -> List[List[str]]:
                    cycles = []
                    if node in rec_stack:
                        # Found cycle
                        cycle_start = path.index(node)
                        cycle = path[cycle_start:] + [node]
                        cycles.append(cycle)
                        return cycles

                    if node in visited:
                        return cycles

                    visited.add(node)
                    rec_stack.add(node)

                    for dep in dependencies.get(node, []):
                        # Try to resolve module to file path
                        # This is simplified - real resolution would be more complex
                        cycles.extend(find_cycles(dep, path + [node]))

                    rec_stack.remove(node)
                    return cycles

                for file in dependencies.keys():
                    visited.clear()
                    rec_stack.clear()
                    cycles = find_cycles(file, [])
                    for cycle in cycles:
                        if cycle not in circular_deps:
                            circular_deps.append(cycle)

            # Detect unused imports
            unused_imports = []
            if detect_unused:
                for file_path, imports in all_imports.items():
                    try:
                        full_path = project_path / file_path
                        content = full_path.read_text(encoding='utf-8', errors='ignore')

                        for imp in imports:
                            module = imp["module"]
                            # Simple heuristic: check if module name or parts are used
                            # This is simplified - real detection would need AST analysis
                            module_parts = module.split(".")
                            base_name = module_parts[-1]

                            # Check if the imported name is used (excluding import line)
                            lines = content.split('\n')
                            import_line = imp["line"] - 1
                            other_content = '\n'.join(lines[:import_line] + lines[import_line+1:])

                            # Check for usage
                            used = False
                            if imp.get("names"):
                                # from X import Y - check for Y
                                for name in imp["names"].split(","):
                                    name = name.strip().split(" as ")[-1].strip()
                                    if re.search(rf'\b{re.escape(name)}\b', other_content):
                                        used = True
                                        break
                            else:
                                # import X - check for X
                                if re.search(rf'\b{re.escape(base_name)}\b', other_content):
                                    used = True

                            if not used:
                                unused_imports.append({
                                    "file": file_path,
                                    "module": module,
                                    "line": imp["line"],
                                    "type": imp["type"]
                                })

                    except Exception as e:
                        logger.warning("unused_detection_failed", file=file_path, error=str(e))

            # Calculate statistics
            # Most imported modules (hubs)
            hub_modules = sorted(
                imported_by.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )[:10]

            # Files with most imports
            heavy_importers = sorted(
                [(f, len(deps)) for f, deps in dependencies.items()],
                key=lambda x: x[1],
                reverse=True
            )[:10]

            execution_time = time.time() - start_time

            result = {
                "project_folder": project_folder,
                "language": language,
                "files_analyzed": len(filtered_files),
                "total_imports": sum(len(deps) for deps in dependencies.values()),
                "summary": {
                    "unique_modules": len(imported_by),
                    "circular_dependencies": len(circular_deps),
                    "unused_imports": len(unused_imports)
                },
                "hub_modules": [
                    {"module": m, "imported_by_count": len(files)}
                    for m, files in hub_modules
                ],
                "heavy_importers": [
                    {"file": f, "import_count": count}
                    for f, count in heavy_importers
                ],
                "circular_dependencies": circular_deps[:20],  # Limit output
                "unused_imports": unused_imports[:50],  # Limit output
                "execution_time_ms": round(execution_time * 1000)
            }

            logger.info(
                "tool_completed",
                tool="analyze_dependencies",
                files_analyzed=len(filtered_files),
                total_imports=result["total_imports"],
                circular=len(circular_deps),
                unused=len(unused_imports),
                execution_time_seconds=round(execution_time, 3)
            )

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "tool_failed",
                tool="analyze_dependencies",
                error=str(e),
                execution_time_seconds=round(execution_time, 3)
            )
            sentry_sdk.capture_exception(e, extras={
                "tool": "analyze_dependencies",
                "project_folder": project_folder,
                "language": language,
                "execution_time_seconds": round(execution_time, 3)
            })
            raise

    @mcp.tool()
    def test_sentry_integration(
        test_type: Literal["error", "warning", "breadcrumb", "span"] = Field(
            default="breadcrumb",
            description="Type of Sentry test: 'error' (exception), 'warning' (capture_message), 'breadcrumb', or 'span' (performance)"
        ),
        message: str = Field(default="Test message", description="Custom test message")
    ) -> Dict[str, Any]:
        """
        Test Sentry integration by triggering different event types.

        Used to verify that Sentry error tracking is properly configured and working.
        Only works when SENTRY_DSN environment variable is set.

        Test Types:
        - error: Triggers a test exception that gets captured by Sentry
        - warning: Sends a warning message to Sentry
        - breadcrumb: Adds test breadcrumbs (check Sentry dashboard for context)
        - span: Creates a performance span

        Returns information about what was sent to Sentry.
        """
        logger = get_logger("tool.test_sentry_integration")
        start_time = time.time()

        logger.info("tool_invoked", tool="test_sentry_integration", test_type=test_type)

        try:
            if not os.getenv("SENTRY_DSN"):
                return {
                    "status": "skipped",
                    "message": "Sentry not configured (SENTRY_DSN not set)",
                    "test_type": test_type
                }

            result: Dict[str, Any] = {"status": "success", "test_type": test_type}

            if test_type == "error":
                # Trigger a test exception
                try:
                    raise ValueError(f"Sentry integration test error: {message}")
                except ValueError as e:
                    sentry_sdk.capture_exception(e, extras={
                        "test": True,
                        "tool": "test_sentry_integration",
                        "message": message
                    })
                    result["message"] = "Test exception captured and sent to Sentry"
                    result["exception_type"] = "ValueError"

            elif test_type == "warning":
                sentry_sdk.capture_message(
                    f"Sentry integration test warning: {message}",
                    level="warning",
                    extras={"test": True, "tool": "test_sentry_integration"}
                )
                result["message"] = "Test warning message sent to Sentry"

            elif test_type == "breadcrumb":
                sentry_sdk.add_breadcrumb(
                    message=f"Test breadcrumb 1: {message}",
                    category="test.breadcrumb",
                    level="info",
                    data={"test": True, "sequence": 1}
                )
                sentry_sdk.add_breadcrumb(
                    message="Test breadcrumb 2: Sequence item",
                    category="test.breadcrumb",
                    level="info",
                    data={"test": True, "sequence": 2}
                )
                # Breadcrumbs only show up with events, so also send a message
                sentry_sdk.capture_message(
                    "Test breadcrumb context (check breadcrumb trail)",
                    level="info",
                    extras={"test": True, "tool": "test_sentry_integration"}
                )
                result["message"] = "Test breadcrumbs added and sent to Sentry (check breadcrumb trail in event)"
                result["breadcrumb_count"] = 2

            elif test_type == "span":
                with sentry_sdk.start_span(op="test.operation", name=f"Test span: {message}") as span:
                    span.set_data("test", True)
                    span.set_data("message", message)
                    span.set_data("tool", "test_sentry_integration")
                    # Simulate some work
                    time.sleep(0.1)
                # Spans need a transaction to show up
                sentry_sdk.capture_message(
                    "Test span completed (check performance monitoring)",
                    level="info",
                    extras={"test": True, "tool": "test_sentry_integration"}
                )
                result["message"] = "Test performance span created and sent to Sentry"

            execution_time = time.time() - start_time
            logger.info(
                "tool_completed",
                tool="test_sentry_integration",
                test_type=test_type,
                execution_time_seconds=round(execution_time, 3),
                status="success"
            )

            result["execution_time_seconds"] = round(execution_time, 3)
            result["sentry_configured"] = True
            return result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "tool_failed",
                tool="test_sentry_integration",
                execution_time_seconds=round(execution_time, 3),
                error=str(e)[:200],
                status="failed"
            )
            # For this test tool, capture the error even if it's not expected
            sentry_sdk.capture_exception(e, extras={
                "tool": "test_sentry_integration",
                "test_type": test_type,
                "execution_time_seconds": round(execution_time, 3)
            })
            raise

    @mcp.tool()
    def benchmark_deduplication(
        iterations: int = Field(
            default=10,
            description="Number of iterations per benchmark (default: 10, more gives better statistics)"
        ),
        save_baseline: bool = Field(
            default=False,
            description="Save results as new baseline for regression detection"
        ),
        check_regression: bool = Field(
            default=True,
            description="Check results against baseline for performance regressions"
        )
    ) -> Dict[str, Any]:
        """
        Run performance benchmarks for deduplication functions.

        Benchmarks the following operations:
        - **scoring**: calculate_deduplication_score (should be < 1ms)
        - **pattern_analysis**: rank_deduplication_candidates and analyze variations
        - **code_generation**: generate_deduplication_recommendation
        - **full_workflow**: create_enhanced_duplication_response

        Returns statistical analysis including mean, std dev, min, and max times.
        Can detect performance regressions against baseline metrics.

        Regression Thresholds:
        - scoring: 5%
        - pattern_analysis: 15%
        - code_generation: 10%
        - full_workflow: 20%
        - test_coverage: 15%

        Example response:
        ```json
        {
            "total_benchmarks": 4,
            "results": [
                {
                    "name": "scoring",
                    "iterations": 100,
                    "mean_seconds": 0.000012,
                    "std_dev_seconds": 0.000002,
                    "min_seconds": 0.000009,
                    "max_seconds": 0.000018
                }
            ],
            "regression_detected": false
        }
        ```
        """
        import statistics
        logger = get_logger("tool.benchmark_deduplication")
        start_time = time.time()

        logger.info(
            "tool_invoked",
            tool="benchmark_deduplication",
            iterations=iterations,
            save_baseline=save_baseline
        )

        try:
            # Regression thresholds
            THRESHOLDS = {
                "pattern_analysis": 0.15,
                "code_generation": 0.10,
                "full_workflow": 0.20,
                "scoring": 0.05,
                "test_coverage": 0.15
            }

            results: List[Dict[str, Any]] = []

            def run_timed_benchmark(
                name: str,
                func: Any,
                iters: int,
                *args: Any,
                **kwargs: Any
            ) -> Dict[str, Any]:
                """Run a benchmark and collect statistics."""
                times: List[float] = []
                for _ in range(iters):
                    t_start = time.perf_counter()
                    func(*args, **kwargs)
                    elapsed = time.perf_counter() - t_start
                    times.append(elapsed)

                return {
                    "name": name,
                    "iterations": iters,
                    "mean_seconds": round(statistics.mean(times), 6),
                    "std_dev_seconds": round(statistics.stdev(times) if len(times) > 1 else 0.0, 6),
                    "min_seconds": round(min(times), 6),
                    "max_seconds": round(max(times), 6)
                }

            # Benchmark 1: Scoring
            test_cases = [
                (100, 3, True, 2, 5),
                (10, 8, False, 10, 50),
                (50, 5, True, 5, 10),
            ]

            def run_scoring() -> None:
                for lines, complexity, has_tests, files, calls in test_cases:
                    calculate_deduplication_score(lines, complexity, has_tests, files, calls)

            results.append(run_timed_benchmark("scoring", run_scoring, iterations * 10))

            # Benchmark 2: Pattern Analysis (ranking)
            candidates = [
                {
                    "lines_saved": i * 10,
                    "complexity_score": (i % 10) + 1,
                    "has_tests": i % 2 == 0,
                    "affected_files": (i % 5) + 1,
                    "external_call_sites": i * 2
                }
                for i in range(50)
            ]

            results.append(run_timed_benchmark(
                "pattern_analysis",
                rank_deduplication_candidates,
                iterations * 5,
                candidates
            ))

            # Benchmark 3: Code Generation (recommendations)
            test_recs = [
                (85.0, 3, 100, True, 3),
                (45.0, 7, 20, False, 8),
                (25.0, 9, 5, False, 15),
            ]

            def run_recommendations() -> None:
                for score, complexity, lines, has_tests, files in test_recs:
                    generate_deduplication_recommendation(score, complexity, lines, has_tests, files)

            results.append(run_timed_benchmark(
                "code_generation",
                run_recommendations,
                iterations * 5
            ))

            # Benchmark 4: Full Workflow
            response_candidates = [
                {
                    "code": f"def helper_{i}(x, y): return x + y * {i}",
                    "function_name": f"helper_{i}",
                    "replacement": f"result = extracted_helper_{i}(x, y)",
                    "similarity": 85.0 + i,
                    "complexity": (i % 10) + 1,
                    "files": [f"file_{i}.py"]
                }
                for i in range(20)
            ]

            results.append(run_timed_benchmark(
                "full_workflow",
                create_enhanced_duplication_response,
                iterations,
                response_candidates,
                include_diffs=False,
                include_colors=False
            ))

            # Check for regressions if requested
            regression_detected = False
            regression_errors: List[str] = []
            baseline_file = "tests/dedup_benchmark_baseline.json"

            if check_regression and os.path.exists(baseline_file):
                with open(baseline_file, 'r') as f:
                    baseline_data = json.load(f)
                    baseline_map = {
                        item["name"]: item
                        for item in baseline_data.get("benchmarks", [])
                    }

                for result in results:
                    name = result["name"]
                    if name in baseline_map:
                        baseline_mean = baseline_map[name].get("mean_seconds", 0)
                        current_mean = result["mean_seconds"]
                        threshold = THRESHOLDS.get(name, 0.10)

                        if baseline_mean > 0:
                            slowdown = (current_mean - baseline_mean) / baseline_mean
                            if slowdown > threshold:
                                regression_detected = True
                                regression_errors.append(
                                    f"{name}: {slowdown*100:.1f}% slower "
                                    f"({baseline_mean:.6f}s -> {current_mean:.6f}s, "
                                    f"threshold: {threshold*100:.0f}%)"
                                )

            # Save baseline if requested
            if save_baseline:
                baseline_data = {
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "benchmarks": results
                }
                os.makedirs(os.path.dirname(baseline_file) if os.path.dirname(baseline_file) else ".", exist_ok=True)
                with open(baseline_file, 'w') as f:
                    json.dump(baseline_data, f, indent=2)

            execution_time = time.time() - start_time

            logger.info(
                "tool_completed",
                tool="benchmark_deduplication",
                total_benchmarks=len(results),
                regression_detected=regression_detected,
                execution_time_seconds=round(execution_time, 3)
            )

            return {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_benchmarks": len(results),
                "results": results,
                "regression_detected": regression_detected,
                "regression_errors": regression_errors,
                "thresholds": THRESHOLDS,
                "baseline_saved": save_baseline,
                "execution_time_seconds": round(execution_time, 3)
            }

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                "tool_failed",
                tool="benchmark_deduplication",
                execution_time_seconds=round(execution_time, 3),
                error=str(e)[:200]
            )
            sentry_sdk.capture_exception(e, extras={
                "tool": "benchmark_deduplication",
                "iterations": iterations,
                "execution_time_seconds": round(execution_time, 3)
            })
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


def _generate_dedup_recommendation(
    similarity: float,
    instance_count: int,
    avg_lines: int,
    savings: int
) -> str:
    """Generate a human-readable recommendation for a deduplication candidate.

    Args:
        similarity: Similarity score (0-1)
        instance_count: Number of duplicate instances
        avg_lines: Average lines per instance
        savings: Potential lines to save

    Returns:
        Recommendation string
    """
    if similarity >= 0.95:
        if instance_count >= 5:
            return f"HIGH PRIORITY: Nearly identical code ({instance_count} instances). Extract to shared utility - saves {savings} lines."
        elif instance_count >= 3:
            return f"RECOMMENDED: Very similar code ({instance_count} instances). Good candidate for extraction - saves {savings} lines."
        else:
            return f"Consider extracting this duplicate code to a shared function - saves {savings} lines."
    elif similarity >= 0.85:
        if avg_lines >= 20:
            return (f"MODERATE: Similar code blocks ({instance_count} instances, ~{avg_lines} lines each). "
                    f"Consider parameterized extraction - saves {savings} lines.")
        else:
            return f"Similar code detected. May benefit from extraction with parameters - saves {savings} lines."
    else:
        return f"Partial similarity detected ({instance_count} instances). Review for potential abstraction - could save {savings} lines."


# Variation Classification Types
class VariationCategory:
    """Categories for classifying variations between duplicate code blocks."""
    LITERAL = "LITERAL"        # string, number, boolean differences
    IDENTIFIER = "IDENTIFIER"  # variable/function/class name differences
    EXPRESSION = "EXPRESSION"  # operator, call, compound expression differences
    LOGIC = "LOGIC"            # control flow differences (if/else, loops)
    TYPE = "TYPE"              # type annotation differences


class VariationSeverity:
    """Severity levels for variations."""
    LOW = "low"       # Minor differences, easy to parameterize
    MEDIUM = "medium" # Moderate differences, requires some refactoring
    HIGH = "high"     # Significant differences, complex refactoring needed


def classify_variation(
    variation_type: str,
    old_value: str,
    new_value: str,
    context: Optional[str] = None
) -> Dict[str, Any]:
    """Classify a single variation between duplicate code blocks.

    Args:
        variation_type: Type hint from detector (e.g., "literal", "identifier")
        old_value: Original value in first code block
        new_value: New value in second code block
        context: Optional surrounding context

    Returns:
        Classification with category, severity, and metadata
    """
    category = _determine_category(variation_type, old_value, new_value)
    severity = _determine_severity(category, old_value, new_value)
    complexity = _calculate_variation_complexity(category, severity, old_value, new_value)

    return {
        "category": category,
        "severity": severity,
        "old_value": old_value,
        "new_value": new_value,
        "context": context,
        "parameterizable": severity in [VariationSeverity.LOW, VariationSeverity.MEDIUM],
        "suggested_param_name": _suggest_parameter_name(category, old_value, new_value),
        "complexity": complexity
    }


def _determine_category(variation_type: str, old_value: str, new_value: str) -> str:
    """Determine the category of a variation based on its characteristics."""
    variation_type_lower = variation_type.lower()

    # Direct mapping from detector hints
    if variation_type_lower in ["literal", "string", "number", "boolean"]:
        return VariationCategory.LITERAL

    if variation_type_lower in ["identifier", "name", "variable", "function", "class"]:
        return VariationCategory.IDENTIFIER

    if variation_type_lower in ["type", "annotation", "type_hint"]:
        return VariationCategory.TYPE

    if variation_type_lower in ["expression", "operator", "call"]:
        return VariationCategory.EXPRESSION

    if variation_type_lower in ["logic", "control", "flow", "condition"]:
        return VariationCategory.LOGIC

    # Content-based inference when type is unknown
    return _infer_category_from_content(old_value, new_value)


def _infer_category_from_content(old_value: str, new_value: str) -> str:
    """Infer category from the actual content when type hint is unavailable."""
    # Check for literal patterns
    if _is_literal(old_value) and _is_literal(new_value):
        return VariationCategory.LITERAL

    # Check for type annotations
    if _is_type_annotation(old_value) or _is_type_annotation(new_value):
        return VariationCategory.TYPE

    # Check for control flow keywords
    control_keywords = {"if", "else", "elif", "for", "while", "switch", "case", "try", "catch", "except"}
    if any(kw in old_value.lower() or kw in new_value.lower() for kw in control_keywords):
        return VariationCategory.LOGIC

    # Check for expression patterns (operators, function calls)
    expression_indicators = ["(", ")", "+", "-", "*", "/", "==", "!=", "&&", "||", "and", "or"]
    if any(ind in old_value or ind in new_value for ind in expression_indicators):
        return VariationCategory.EXPRESSION

    # Default to identifier (most common case for simple name changes)
    return VariationCategory.IDENTIFIER


def _is_literal(value: str) -> bool:
    """Check if a value appears to be a literal."""
    value = value.strip()

    # String literals
    if (value.startswith('"') and value.endswith('"')) or \
       (value.startswith("'") and value.endswith("'")):
        return True

    # Numeric literals
    try:
        float(value)
        return True
    except ValueError:
        pass

    # Boolean literals
    if value.lower() in ["true", "false", "none", "null", "nil"]:
        return True

    return False


def _is_type_annotation(value: str) -> bool:
    """Check if a value appears to be a type annotation."""
    type_indicators = [
        "->", ":", "Optional[", "List[", "Dict[", "Tuple[", "Set[",
        "Union[", "Any", "int", "str", "float", "bool", "None",
        "<", ">",  # Generics in other languages
    ]
    return any(ind in value for ind in type_indicators)


def _determine_severity(category: str, old_value: str, new_value: str) -> str:
    """Determine the severity of a variation."""
    # LITERAL variations are typically easy to parameterize
    if category == VariationCategory.LITERAL:
        return VariationSeverity.LOW

    # IDENTIFIER variations depend on scope
    if category == VariationCategory.IDENTIFIER:
        old_words = len(old_value.split("_")) + len(old_value.split())
        new_words = len(new_value.split("_")) + len(new_value.split())
        if abs(old_words - new_words) > 2:
            return VariationSeverity.MEDIUM
        return VariationSeverity.LOW

    # TYPE variations require careful handling
    if category == VariationCategory.TYPE:
        if "[" in old_value or "[" in new_value:
            return VariationSeverity.MEDIUM
        return VariationSeverity.LOW

    # EXPRESSION variations need analysis
    if category == VariationCategory.EXPRESSION:
        if "(" in old_value and "(" in new_value:
            return VariationSeverity.HIGH if old_value.split("(")[0] != new_value.split("(")[0] else VariationSeverity.MEDIUM
        return VariationSeverity.MEDIUM

    # LOGIC variations are the most complex
    if category == VariationCategory.LOGIC:
        return VariationSeverity.HIGH

    return VariationSeverity.MEDIUM


def _suggest_parameter_name(category: str, old_value: str, new_value: str) -> Optional[str]:
    """Suggest a parameter name for the variation."""
    if category == VariationCategory.LITERAL:
        if _is_literal(old_value):
            if any(kw in old_value.lower() for kw in ["url", "path", "file"]):
                return "target_path"
            if any(kw in old_value.lower() for kw in ["name", "id", "key"]):
                return "identifier"
            if any(char.isdigit() for char in old_value):
                return "value"
            return "text_value"
        return "literal_value"

    if category == VariationCategory.IDENTIFIER:
        return "name"

    if category == VariationCategory.TYPE:
        return "type_param"

    if category == VariationCategory.EXPRESSION:
        return "expression"

    if category == VariationCategory.LOGIC:
        return None  # Logic variations typically can't be parameterized simply

    return None


def _calculate_variation_complexity(
    category: str,
    severity: str,
    old_value: str,
    new_value: str
) -> Dict[str, Any]:
    """Calculate complexity score for a single variation.

    Complexity scores indicate refactoring difficulty on a 1-7 scale:
    - Literal changes: 1 (trivial to parameterize)
    - Identifier renames: 1-2 (simple substitution)
    - Expression changes: 3-4 (may need abstraction)
    - Type changes: 4-6 (type system considerations)
    - Conditional logic: 5-7 (structural changes required)

    Args:
        category: Variation category
        severity: Variation severity
        old_value: Original value
        new_value: New value

    Returns:
        Dictionary with score, level, and reasoning
    """
    score = 1
    reasoning = ""

    if category == VariationCategory.LITERAL:
        score = 1
        reasoning = "Simple value substitution"

    elif category == VariationCategory.IDENTIFIER:
        if severity == VariationSeverity.LOW:
            score = 1
            reasoning = "Simple identifier rename"
        else:
            score = 2
            reasoning = "Identifier with semantic differences"

    elif category == VariationCategory.EXPRESSION:
        if severity == VariationSeverity.LOW:
            score = 3
            reasoning = "Minor expression variation"
        elif severity == VariationSeverity.MEDIUM:
            score = 4
            reasoning = "Different operations or function calls"
        else:
            score = 4
            reasoning = "Significant expression restructuring"

    elif category == VariationCategory.TYPE:
        if severity == VariationSeverity.LOW:
            score = 4
            reasoning = "Simple type substitution"
        elif severity == VariationSeverity.MEDIUM:
            score = 5
            reasoning = "Generic type variation"
        else:
            score = 6
            reasoning = "Complex type system changes"

    elif category == VariationCategory.LOGIC:
        if "inserted" in str(old_value) or "deleted" in str(new_value):
            score = 7
            reasoning = "Added or removed logic branches"
        elif severity == VariationSeverity.HIGH:
            score = 7
            reasoning = "Significant control flow differences"
        else:
            score = 5
            reasoning = "Conditional logic variation"

    else:
        score = 3
        reasoning = "Unclassified variation"

    if score <= 2:
        level = "low"
    elif score <= 4:
        level = "medium"
    else:
        level = "high"

    return {
        "score": score,
        "level": level,
        "reasoning": reasoning
    }


def classify_variations(
    variations: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Classify a list of variations between duplicate code blocks.

    Takes variation data from literal/identifier/expression detectors and
    returns classified variations with category and severity.

    Args:
        variations: List of variation dictionaries with keys:
            - type: Variation type hint from detector
            - old_value: Original value
            - new_value: New value
            - context: Optional surrounding context

    Returns:
        Dictionary containing:
            - classified_variations: List of classified variations
            - summary: Summary statistics by category and severity
            - refactoring_complexity: Overall complexity assessment
            - parameterizable_count: Number of easily parameterizable variations
    """
    logger = get_logger("duplication.classifier")

    if not variations:
        return {
            "classified_variations": [],
            "summary": {
                "by_category": {},
                "by_severity": {}
            },
            "refactoring_complexity": "none",
            "parameterizable_count": 0
        }

    classified = []
    category_counts: Dict[str, int] = {}
    severity_counts: Dict[str, int] = {}
    parameterizable_count = 0
    complexity_scores: List[int] = []

    for variation in variations:
        classification = classify_variation(
            variation_type=variation.get("type", "unknown"),
            old_value=variation.get("old_value", ""),
            new_value=variation.get("new_value", ""),
            context=variation.get("context")
        )
        classified.append(classification)

        cat = classification["category"]
        sev = classification["severity"]
        category_counts[cat] = category_counts.get(cat, 0) + 1
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

        if classification["parameterizable"]:
            parameterizable_count += 1

        # Track complexity scores
        complexity_scores.append(classification["complexity"]["score"])

    # Determine overall complexity
    high_count = severity_counts.get(VariationSeverity.HIGH, 0)
    medium_count = severity_counts.get(VariationSeverity.MEDIUM, 0)
    total = len(classified)

    if high_count > total * 0.3 or VariationCategory.LOGIC in category_counts:
        complexity = "high"
    elif high_count > 0 or medium_count > total * 0.5:
        complexity = "medium"
    elif total > 0:
        complexity = "low"
    else:
        complexity = "none"

    # Aggregate complexity scores
    if complexity_scores:
        total_score = sum(complexity_scores)
        avg_score = round(total_score / len(complexity_scores), 2)
        max_score = max(complexity_scores)
    else:
        total_score = 0
        avg_score = 0.0
        max_score = 0

    # Determine aggregate complexity level from average score
    if avg_score <= 2:
        aggregate_level = "low"
    elif avg_score <= 4:
        aggregate_level = "medium"
    else:
        aggregate_level = "high"

    logger.info(
        "variations_classified",
        total_variations=total,
        parameterizable=parameterizable_count,
        complexity=complexity,
        aggregate_score=total_score,
        avg_score=avg_score,
        categories=category_counts
    )

    return {
        "classified_variations": classified,
        "summary": {
            "by_category": category_counts,
            "by_severity": severity_counts
        },
        "refactoring_complexity": complexity,
        "parameterizable_count": parameterizable_count,
        "complexity_scores": {
            "total": total_score,
            "average": avg_score,
            "max": max_score,
            "level": aggregate_level
        }
    }


def detect_variations_between_blocks(code1: str, code2: str) -> List[Dict[str, Any]]:
    """Detect variations between two code blocks using difflib.

    Args:
        code1: First code block
        code2: Second code block

    Returns:
        List of variation dictionaries
    """
    variations = []
    lines1 = code1.split('\n')
    lines2 = code2.split('\n')

    matcher = difflib.SequenceMatcher(None, lines1, lines2)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'replace':
            old_lines = lines1[i1:i2]
            new_lines = lines2[j1:j2]

            for old_line, new_line in zip(old_lines, new_lines):
                token_variations = _detect_token_variations(old_line, new_line)
                variations.extend(token_variations)

        elif tag == 'insert' or tag == 'delete':
            if tag == 'delete':
                for line in lines1[i1:i2]:
                    if line.strip():
                        variations.append({
                            "type": "logic",
                            "old_value": line.strip(),
                            "new_value": "",
                            "context": "deleted"
                        })
            else:
                for line in lines2[j1:j2]:
                    if line.strip():
                        variations.append({
                            "type": "logic",
                            "old_value": "",
                            "new_value": line.strip(),
                            "context": "inserted"
                        })

    return variations


def _detect_token_variations(line1: str, line2: str) -> List[Dict[str, Any]]:
    """Detect token-level variations between two lines."""
    import re

    variations = []
    token_pattern = r'(\w+|"[^"]*"|\'[^\']*\'|[^\w\s])'
    tokens1 = re.findall(token_pattern, line1)
    tokens2 = re.findall(token_pattern, line2)

    matcher = difflib.SequenceMatcher(None, tokens1, tokens2)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'replace':
            old_tokens = tokens1[i1:i2]
            new_tokens = tokens2[j1:j2]

            for old_tok, new_tok in zip(old_tokens, new_tokens):
                if old_tok != new_tok:
                    var_type = _infer_token_type(old_tok, new_tok)
                    variations.append({
                        "type": var_type,
                        "old_value": old_tok,
                        "new_value": new_tok,
                        "context": line1.strip()
                    })

    return variations


def _infer_token_type(token1: str, token2: str) -> str:
    """Infer the type of a token for classification."""
    # String literals
    if (token1.startswith('"') or token1.startswith("'")) and \
       (token2.startswith('"') or token2.startswith("'")):
        return "literal"

    # Numeric literals
    try:
        float(token1)
        float(token2)
        return "literal"
    except ValueError:
        pass

    # Operators
    operators = {'+', '-', '*', '/', '%', '==', '!=', '<', '>', '<=', '>=', '&&', '||', 'and', 'or'}
    if token1 in operators or token2 in operators:
        return "expression"

    # Default to identifier
    return "identifier"


def detect_conditional_variations(
    code1: str,
    code2: str,
    language: str = "python"
) -> Dict[str, Any]:
    """Detect variations in conditional (if/else) structures between two code blocks.

    Analyzes differences in:
    - Condition expressions (the test in if statements)
    - Branch bodies (code inside if/elif/else blocks)
    - Missing or added branches
    - Structural differences in conditional logic

    Args:
        code1: First code block text
        code2: Second code block text
        language: Programming language (python, javascript, typescript, etc.)

    Returns:
        Dictionary containing:
            - condition_differences: List of condition expression differences
            - branch_differences: List of branch body differences
            - structural_differences: Missing/added branches
            - summary: Overall summary of conditional variations
            - refactoring_suggestion: Suggestion for unifying the conditionals
    """
    import re
    logger = get_logger("detect_conditional_variations")

    result: Dict[str, Any] = {
        "condition_differences": [],
        "branch_differences": [],
        "structural_differences": [],
        "summary": {
            "total_differences": 0,
            "condition_changes": 0,
            "branch_changes": 0,
            "structural_changes": 0
        },
        "refactoring_suggestion": ""
    }

    # Define conditional patterns based on language
    if language in ["python"]:
        if_pattern = r'^\s*if\s+(.+?)\s*:'
        elif_pattern = r'^\s*elif\s+(.+?)\s*:'
        else_pattern = r'^\s*else\s*:'
    elif language in ["javascript", "typescript", "java", "c", "cpp", "csharp", "go", "rust"]:
        if_pattern = r'^\s*if\s*\((.+?)\)\s*\{?'
        elif_pattern = r'^\s*else\s+if\s*\((.+?)\)\s*\{?'
        else_pattern = r'^\s*else\s*\{?'
    else:
        if_pattern = r'^\s*if\s*\((.+?)\)\s*\{?'
        elif_pattern = r'^\s*else\s+if\s*\((.+?)\)\s*\{?'
        else_pattern = r'^\s*else\s*\{?'

    def extract_conditionals(code: str) -> List[Dict[str, Any]]:
        """Extract conditional statements and their components."""
        conditionals: List[Dict[str, Any]] = []
        lines = code.split('\n')
        current_conditional: Optional[Dict[str, Any]] = None
        branch_lines: List[str] = []
        indent_level = 0

        for i, line in enumerate(lines):
            if_match = re.match(if_pattern, line)
            elif_match = re.match(elif_pattern, line)
            else_match = re.match(else_pattern, line)

            if if_match:
                if current_conditional:
                    current_conditional['branches'].append({
                        'type': current_conditional['current_branch_type'],
                        'condition': current_conditional.get('current_condition', ''),
                        'body': '\n'.join(branch_lines).strip()
                    })
                    conditionals.append(current_conditional)

                condition = if_match.group(1).strip()
                indent_level = len(line) - len(line.lstrip())
                current_conditional = {
                    'start_line': i,
                    'condition': condition,
                    'branches': [],
                    'current_branch_type': 'if',
                    'current_condition': condition,
                    'indent': indent_level
                }
                branch_lines = []

            elif elif_match and current_conditional:
                current_conditional['branches'].append({
                    'type': current_conditional['current_branch_type'],
                    'condition': current_conditional.get('current_condition', ''),
                    'body': '\n'.join(branch_lines).strip()
                })
                condition = elif_match.group(1).strip()
                current_conditional['current_branch_type'] = 'elif'
                current_conditional['current_condition'] = condition
                branch_lines = []

            elif else_match and current_conditional:
                current_conditional['branches'].append({
                    'type': current_conditional['current_branch_type'],
                    'condition': current_conditional.get('current_condition', ''),
                    'body': '\n'.join(branch_lines).strip()
                })
                current_conditional['current_branch_type'] = 'else'
                current_conditional['current_condition'] = ''
                branch_lines = []

            elif current_conditional:
                line_indent = len(line) - len(line.lstrip()) if line.strip() else indent_level + 1
                if line.strip() and line_indent <= indent_level:
                    current_conditional['branches'].append({
                        'type': current_conditional['current_branch_type'],
                        'condition': current_conditional.get('current_condition', ''),
                        'body': '\n'.join(branch_lines).strip()
                    })
                    conditionals.append(current_conditional)
                    current_conditional = None
                    branch_lines = []
                else:
                    branch_lines.append(line)

        if current_conditional:
            current_conditional['branches'].append({
                'type': current_conditional['current_branch_type'],
                'condition': current_conditional.get('current_condition', ''),
                'body': '\n'.join(branch_lines).strip()
            })
            conditionals.append(current_conditional)

        return conditionals

    conds1 = extract_conditionals(code1)
    conds2 = extract_conditionals(code2)
    max_conditionals = max(len(conds1), len(conds2))

    for i in range(max_conditionals):
        cond1 = conds1[i] if i < len(conds1) else None
        cond2 = conds2[i] if i < len(conds2) else None

        if cond1 is None:
            result["structural_differences"].append({
                "type": "conditional_added",
                "block2_condition": cond2['condition'] if cond2 else '',
                "block2_branches": len(cond2['branches']) if cond2 else 0,
                "description": f"Conditional added in block 2: if {cond2['condition'] if cond2 else ''}"
            })
            result["summary"]["structural_changes"] += 1
            continue

        if cond2 is None:
            result["structural_differences"].append({
                "type": "conditional_removed",
                "block1_condition": cond1['condition'],
                "block1_branches": len(cond1['branches']),
                "description": f"Conditional removed in block 2: if {cond1['condition']}"
            })
            result["summary"]["structural_changes"] += 1
            continue

        if cond1['condition'] != cond2['condition']:
            result["condition_differences"].append({
                "type": "condition_changed",
                "block1": cond1['condition'],
                "block2": cond2['condition'],
                "conditional_index": i,
                "description": f"Condition changed: '{cond1['condition']}' -> '{cond2['condition']}'"
            })
            result["summary"]["condition_changes"] += 1

        branches1 = cond1['branches']
        branches2 = cond2['branches']
        max_branches = max(len(branches1), len(branches2))

        for j in range(max_branches):
            b1 = branches1[j] if j < len(branches1) else None
            b2 = branches2[j] if j < len(branches2) else None

            if b1 is None:
                result["structural_differences"].append({
                    "type": "branch_added",
                    "branch_type": b2['type'] if b2 else '',
                    "condition": b2['condition'] if b2 else '',
                    "conditional_index": i,
                    "description": f"Branch added: {b2['type'] if b2 else ''} {b2['condition'] if b2 else ''}"
                })
                result["summary"]["structural_changes"] += 1
                continue

            if b2 is None:
                result["structural_differences"].append({
                    "type": "branch_removed",
                    "branch_type": b1['type'],
                    "condition": b1['condition'],
                    "conditional_index": i,
                    "description": f"Branch removed: {b1['type']} {b1['condition']}"
                })
                result["summary"]["structural_changes"] += 1
                continue

            if b1['type'] == 'elif' and b2['type'] == 'elif':
                if b1['condition'] != b2['condition']:
                    result["condition_differences"].append({
                        "type": "elif_condition_changed",
                        "block1": b1['condition'],
                        "block2": b2['condition'],
                        "conditional_index": i,
                        "branch_index": j,
                        "description": f"Elif condition changed: '{b1['condition']}' -> '{b2['condition']}'"
                    })
                    result["summary"]["condition_changes"] += 1

            if b1['body'] != b2['body']:
                body_variations = _detect_token_variations(b1['body'], b2['body'])
                result["branch_differences"].append({
                    "type": "branch_body_changed",
                    "branch_type": b1['type'],
                    "conditional_index": i,
                    "branch_index": j,
                    "block1_body": b1['body'][:100] + ('...' if len(b1['body']) > 100 else ''),
                    "block2_body": b2['body'][:100] + ('...' if len(b2['body']) > 100 else ''),
                    "token_variations": body_variations[:5],
                    "description": f"Body of {b1['type']} branch differs"
                })
                result["summary"]["branch_changes"] += 1

    result["summary"]["total_differences"] = (
        result["summary"]["condition_changes"] +
        result["summary"]["branch_changes"] +
        result["summary"]["structural_changes"]
    )

    if result["summary"]["total_differences"] > 0:
        suggestions = []
        if result["summary"]["condition_changes"] > 0:
            suggestions.append(
                f"Parameterize {result['summary']['condition_changes']} condition(s) "
                "to create a unified function with threshold parameter"
            )
        if result["summary"]["branch_changes"] > 0:
            suggestions.append(
                f"Extract {result['summary']['branch_changes']} differing branch bodies "
                "into separate functions or use strategy pattern"
            )
        if result["summary"]["structural_changes"] > 0:
            suggestions.append(
                f"Review {result['summary']['structural_changes']} structural difference(s) "
                "to determine if logic should be unified or kept separate"
            )
        result["refactoring_suggestion"] = "; ".join(suggestions)
    else:
        result["refactoring_suggestion"] = "No conditional variations detected"

    logger.info(
        "conditional_variations_detected",
        condition_changes=result["summary"]["condition_changes"],
        branch_changes=result["summary"]["branch_changes"],
        structural_changes=result["summary"]["structural_changes"]
    )

    return result


@dataclass
class AlignmentSegment:
    """Represents a segment in the alignment between two code blocks."""
    segment_type: str  # 'aligned', 'divergent', 'inserted', 'deleted'
    block1_start: int  # Line number in block 1 (0-indexed, -1 if N/A)
    block1_end: int    # End line in block 1 (exclusive)
    block2_start: int  # Line number in block 2 (0-indexed, -1 if N/A)
    block2_end: int    # End line in block 2 (exclusive)
    block1_text: str   # Text from block 1
    block2_text: str   # Text from block 2
    metadata: Optional[Dict[str, Any]] = None  # Multi-line info, construct types, etc.

    def __post_init__(self) -> None:
        """Initialize metadata if not provided."""
        if self.metadata is None:
            self.metadata = {}


def detect_multiline_construct(lines: List[str], start_idx: int, end_idx: int) -> Dict[str, Any]:
    """Detect if a segment contains multi-line constructs and their types.

    Args:
        lines: Full list of lines from the code block
        start_idx: Start index (0-indexed)
        end_idx: End index (exclusive)

    Returns:
        Dictionary with multi-line metadata
    """
    if start_idx >= end_idx or start_idx >= len(lines):
        return {'is_multiline': False, 'line_count': 0}

    segment_lines = lines[start_idx:end_idx]
    text = '\n'.join(segment_lines)
    line_count = len(segment_lines)

    result: Dict[str, Any] = {
        'is_multiline': line_count > 1,
        'line_count': line_count,
        'constructs': []
    }

    # Detect Python continuation characters
    has_continuation = any(line.rstrip().endswith('\\') for line in segment_lines[:-1] if line.strip())
    if has_continuation:
        result['constructs'].append('line_continuation')
        result['has_continuation'] = True

    # Detect multi-line strings (Python triple quotes)
    triple_single = text.count("'''")
    triple_double = text.count('"""')
    if triple_single >= 2 or triple_double >= 2:
        result['constructs'].append('multiline_string')
        result['has_multiline_string'] = True
    elif triple_single == 1 or triple_double == 1:
        # Unclosed or spanning beyond segment
        result['constructs'].append('multiline_string_partial')
        result['has_multiline_string_partial'] = True

    # Detect JS template literals
    if '`' in text:
        backtick_count = text.count('`')
        if backtick_count >= 2:
            result['constructs'].append('template_literal')
            result['has_template_literal'] = True
        elif backtick_count == 1:
            result['constructs'].append('template_literal_partial')
            result['has_template_literal_partial'] = True

    # Detect block structures (if/for/while/def/class/function)
    block_patterns = [
        (r'^\s*(if|elif|else)\b', 'conditional_block'),
        (r'^\s*(for|while)\b', 'loop_block'),
        (r'^\s*def\s+\w+', 'function_block'),
        (r'^\s*class\s+\w+', 'class_block'),
        (r'^\s*(async\s+)?function\s+\w+', 'js_function_block'),
        (r'^\s*(try|except|finally|catch)\b', 'exception_block'),
        (r'^\s*with\b', 'context_manager_block'),
    ]

    for pattern, construct_name in block_patterns:
        if any(re.match(pattern, line) for line in segment_lines):
            result['constructs'].append(construct_name)
            result['is_block_construct'] = True
            break

    # Detect multi-line comments
    if '/*' in text or '*/' in text:
        result['constructs'].append('block_comment')
        result['has_block_comment'] = True

    # Check for statement spanning multiple lines (parentheses, brackets)
    open_parens = text.count('(') - text.count(')')
    open_brackets = text.count('[') - text.count(']')
    open_braces = text.count('{') - text.count('}')

    if line_count > 1 and (open_parens != 0 or open_brackets != 0 or open_braces != 0):
        result['constructs'].append('spanning_statement')
        result['is_spanning'] = True
        result['unbalanced'] = {
            'parentheses': open_parens,
            'brackets': open_brackets,
            'braces': open_braces
        }
    elif line_count > 1:
        # Check if it's a single statement split across lines
        first_line = segment_lines[0].rstrip() if segment_lines else ''
        if first_line and not first_line.endswith((':', '{', ',')):
            # Might be a continued expression
            parens_in_first = first_line.count('(') - first_line.count(')')
            if parens_in_first > 0:
                result['constructs'].append('split_statement')
                result['is_split_statement'] = True

    return result


@dataclass
class AlignmentResult:
    """Result of aligning two code blocks for comparison."""
    segments: List[AlignmentSegment]
    similarity_ratio: float
    aligned_lines: int
    divergent_lines: int
    block1_total_lines: int
    block2_total_lines: int


@dataclass
class DiffTreeNode:
    """A node in a hierarchical diff tree structure.

    Represents code differences hierarchically, allowing nested structures
    to be represented with parent-child relationships.
    """
    node_type: str  # 'aligned', 'divergent', 'inserted', 'deleted', 'container'
    content: str  # The code content for this node
    children: List['DiffTreeNode']  # Child nodes for nested structures
    metadata: Dict[str, Any]  # Additional metadata (line numbers, similarity, etc.)

    def __post_init__(self) -> None:
        """Ensure children is a mutable list."""
        if self.children is None:
            self.children = []

    def add_child(self, child: 'DiffTreeNode') -> None:
        """Add a child node."""
        self.children.append(child)

    def get_all_nodes(self) -> List['DiffTreeNode']:
        """Get all nodes in the tree (depth-first traversal)."""
        result = [self]
        for child in self.children:
            result.extend(child.get_all_nodes())
        return result

    def find_by_type(self, node_type: str) -> List['DiffTreeNode']:
        """Find all nodes of a specific type."""
        return [node for node in self.get_all_nodes() if node.node_type == node_type]

    def get_depth(self) -> int:
        """Get the maximum depth of the tree from this node."""
        if not self.children:
            return 0
        return 1 + max(child.get_depth() for child in self.children)

    def count_by_type(self) -> Dict[str, int]:
        """Count nodes by type in the subtree."""
        counts: Dict[str, int] = {}
        for node in self.get_all_nodes():
            counts[node.node_type] = counts.get(node.node_type, 0) + 1
        return counts


@dataclass
class DiffTree:
    """Hierarchical representation of code differences.

    Wraps a root DiffTreeNode and provides tree-level operations.
    """
    root: DiffTreeNode
    similarity_ratio: float
    total_aligned: int
    total_divergent: int

    def traverse_depth_first(self) -> List[DiffTreeNode]:
        """Traverse the tree depth-first."""
        return self.root.get_all_nodes()

    def traverse_breadth_first(self) -> List[DiffTreeNode]:
        """Traverse the tree breadth-first."""
        result = []
        queue = [self.root]
        while queue:
            node = queue.pop(0)
            result.append(node)
            queue.extend(node.children)
        return result

    def find_divergent_regions(self) -> List[DiffTreeNode]:
        """Find all divergent nodes in the tree."""
        return self.root.find_by_type('divergent')

    def find_aligned_regions(self) -> List[DiffTreeNode]:
        """Find all aligned nodes in the tree."""
        return self.root.find_by_type('aligned')

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the diff tree."""
        return {
            'similarity_ratio': self.similarity_ratio,
            'total_aligned': self.total_aligned,
            'total_divergent': self.total_divergent,
            'depth': self.root.get_depth(),
            'node_counts': self.root.count_by_type()
        }


def build_diff_tree(result: AlignmentResult) -> DiffTree:
    """Build a hierarchical DiffTree from a flat AlignmentResult.

    Converts the flat segment list into a tree structure where:
    - The root is a container node
    - Each segment becomes a child node
    - Nested code structures can be further broken down

    Args:
        result: AlignmentResult from align_code_blocks

    Returns:
        DiffTree with hierarchical representation of differences

    Example:
        >>> result = align_code_blocks(
        ...     "def foo():\\n    x = 1\\n    return x",
        ...     "def foo():\\n    x = 2\\n    return x"
        ... )
        >>> tree = build_diff_tree(result)
        >>> print(tree.get_summary())
        {'similarity_ratio': 0.666..., 'depth': 1, ...}
    """
    # Create root container node
    root = DiffTreeNode(
        node_type='container',
        content='',
        children=[],
        metadata={
            'block1_total_lines': result.block1_total_lines,
            'block2_total_lines': result.block2_total_lines
        }
    )

    # Convert each segment to a tree node
    for segment in result.segments:
        # Determine content based on segment type
        if segment.segment_type == 'aligned':
            content = segment.block1_text
        elif segment.segment_type == 'deleted':
            content = segment.block1_text
        elif segment.segment_type == 'inserted':
            content = segment.block2_text
        else:  # divergent
            # For divergent, combine both with marker
            content = f"<<<BLOCK1>>>\n{segment.block1_text}\n<<<BLOCK2>>>\n{segment.block2_text}"

        node = DiffTreeNode(
            node_type=segment.segment_type,
            content=content,
            children=[],
            metadata={
                'block1_start': segment.block1_start,
                'block1_end': segment.block1_end,
                'block2_start': segment.block2_start,
                'block2_end': segment.block2_end,
                'block1_text': segment.block1_text,
                'block2_text': segment.block2_text
            }
        )
        root.add_child(node)

    return DiffTree(
        root=root,
        similarity_ratio=result.similarity_ratio,
        total_aligned=result.aligned_lines,
        total_divergent=result.divergent_lines
    )


def build_nested_diff_tree(
    result: AlignmentResult,
    indent_pattern: str = r'^(\s*)'
) -> DiffTree:
    """Build a DiffTree with nesting based on code indentation.

    Analyzes indentation patterns to create parent-child relationships
    for nested code structures (functions, classes, blocks).

    Args:
        result: AlignmentResult from align_code_blocks
        indent_pattern: Regex pattern to extract indentation

    Returns:
        DiffTree with nested structure based on indentation
    """
    import re

    # First build flat tree
    flat_tree = build_diff_tree(result)

    # Now reorganize based on indentation
    def get_indent_level(text: str) -> int:
        """Get indentation level of first non-empty line."""
        for line in text.split('\n'):
            if line.strip():
                match = re.match(indent_pattern, line)
                if match:
                    return len(match.group(1))
        return 0

    # Create new root
    root = DiffTreeNode(
        node_type='container',
        content='',
        children=[],
        metadata=flat_tree.root.metadata.copy()
    )

    # Stack to track parent nodes at each indent level
    stack: List[Tuple[int, DiffTreeNode]] = [(-1, root)]

    for child in flat_tree.root.children:
        indent = get_indent_level(child.content)

        # Pop stack until we find the appropriate parent
        while stack and stack[-1][0] >= indent:
            stack.pop()

        # Add as child to current parent
        parent = stack[-1][1] if stack else root
        parent.add_child(child)

        # Push this node onto stack as potential parent
        stack.append((indent, child))

    return DiffTree(
        root=root,
        similarity_ratio=result.similarity_ratio,
        total_aligned=result.aligned_lines,
        total_divergent=result.divergent_lines
    )


def align_code_blocks(
    block1: str,
    block2: str,
    ignore_whitespace: bool = True,
    ignore_comments: bool = True
) -> AlignmentResult:
    """Align two code blocks to identify matching and divergent segments.

    Uses difflib's SequenceMatcher to find the longest contiguous matching
    subsequences, then identifies aligned (same) vs divergent (different) regions.

    Args:
        block1: First code block text
        block2: Second code block text
        ignore_whitespace: Normalize whitespace for comparison
        ignore_comments: Skip comment lines when comparing

    Returns:
        AlignmentResult with segments showing aligned and divergent regions

    Example:
        >>> result = align_code_blocks(
        ...     "def foo():\\n    x = 1\\n    return x",
        ...     "def foo():\\n    x = 2\\n    return x"
        ... )
        >>> for seg in result.segments:
        ...     print(f"{seg.segment_type}: {seg.block1_text!r} vs {seg.block2_text!r}")
        aligned: 'def foo():' vs 'def foo():'
        divergent: '    x = 1' vs '    x = 2'
        aligned: '    return x' vs '    return x'
    """
    # Split into lines
    lines1 = block1.split('\n') if block1 else []
    lines2 = block2.split('\n') if block2 else []

    # Create normalized versions for comparison
    def normalize_line(line: str) -> str:
        """Normalize a single line for comparison."""
        if ignore_whitespace:
            line = line.strip()
        if ignore_comments:
            # Skip lines that are only comments
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('//'):
                return ''
        return line

    norm1 = [normalize_line(line) for line in lines1]
    norm2 = [normalize_line(line) for line in lines2]

    # Use SequenceMatcher to find matching blocks
    matcher = difflib.SequenceMatcher(None, norm1, norm2, autojunk=False)

    segments: List[AlignmentSegment] = []
    aligned_lines = 0
    divergent_lines = 0

    # Get opcodes which describe the transformation
    # Each opcode is (tag, i1, i2, j1, j2) where:
    # - tag: 'equal', 'replace', 'insert', 'delete'
    # - i1:i2 is the slice in seq1
    # - j1:j2 is the slice in seq2
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        block1_text = '\n'.join(lines1[i1:i2]) if i1 < i2 else ''
        block2_text = '\n'.join(lines2[j1:j2]) if j1 < j2 else ''

        # Detect multi-line constructs in both blocks
        block1_multiline = detect_multiline_construct(lines1, i1, i2)
        block2_multiline = detect_multiline_construct(lines2, j1, j2)

        # Build combined metadata
        metadata: Dict[str, Any] = {
            'block1': block1_multiline,
            'block2': block2_multiline,
        }

        # Determine overall multi-line nature
        is_multiline = block1_multiline.get('is_multiline', False) or block2_multiline.get('is_multiline', False)
        metadata['is_multiline_segment'] = is_multiline

        # Collect all construct types from both blocks
        all_constructs = set(block1_multiline.get('constructs', []) + block2_multiline.get('constructs', []))
        if all_constructs:
            metadata['construct_types'] = list(all_constructs)

        # Flag specific multi-line scenarios for diff readability
        if block1_multiline.get('has_continuation') or block2_multiline.get('has_continuation'):
            metadata['has_line_continuation'] = True
        if block1_multiline.get('has_multiline_string') or block2_multiline.get('has_multiline_string'):
            metadata['has_multiline_string'] = True
        if block1_multiline.get('is_block_construct') or block2_multiline.get('is_block_construct'):
            metadata['is_block_difference'] = True
        if block1_multiline.get('is_spanning') or block2_multiline.get('is_spanning'):
            metadata['has_spanning_statement'] = True

        if tag == 'equal':
            # Lines are the same
            segments.append(AlignmentSegment(
                segment_type='aligned',
                block1_start=i1,
                block1_end=i2,
                block2_start=j1,
                block2_end=j2,
                block1_text=block1_text,
                block2_text=block2_text,
                metadata=metadata
            ))
            aligned_lines += i2 - i1

        elif tag == 'replace':
            # Lines differ between blocks
            segments.append(AlignmentSegment(
                segment_type='divergent',
                block1_start=i1,
                block1_end=i2,
                block2_start=j1,
                block2_end=j2,
                block1_text=block1_text,
                block2_text=block2_text,
                metadata=metadata
            ))
            divergent_lines += max(i2 - i1, j2 - j1)

        elif tag == 'delete':
            # Lines only in block1 (deleted in block2)
            segments.append(AlignmentSegment(
                segment_type='deleted',
                block1_start=i1,
                block1_end=i2,
                block2_start=j1,
                block2_end=j1,  # No span in block2
                block1_text=block1_text,
                block2_text='',
                metadata=metadata
            ))
            divergent_lines += i2 - i1

        elif tag == 'insert':
            # Lines only in block2 (inserted)
            segments.append(AlignmentSegment(
                segment_type='inserted',
                block1_start=i1,
                block1_end=i1,  # No span in block1
                block2_start=j1,
                block2_end=j2,
                block1_text='',
                block2_text=block2_text,
                metadata=metadata
            ))
            divergent_lines += j2 - j1

    # Calculate similarity
    total_lines = max(len(lines1), len(lines2))
    similarity_ratio = aligned_lines / total_lines if total_lines > 0 else 1.0

    return AlignmentResult(
        segments=segments,
        similarity_ratio=similarity_ratio,
        aligned_lines=aligned_lines,
        divergent_lines=divergent_lines,
        block1_total_lines=len(lines1),
        block2_total_lines=len(lines2)
    )


def _format_multiline_annotations(metadata: Dict[str, Any]) -> str:
    """Format multi-line construct annotations for diff headers.

    Args:
        metadata: Segment metadata from AlignmentSegment

    Returns:
        Formatted string with annotations (e.g., " [block, continuation]")
    """
    if not metadata:
        return ""

    annotations = []

    # Check for specific multi-line indicators
    if metadata.get('is_block_difference'):
        annotations.append('block')
    if metadata.get('has_line_continuation'):
        annotations.append('continuation')
    if metadata.get('has_multiline_string'):
        annotations.append('multiline-string')
    if metadata.get('has_spanning_statement'):
        annotations.append('spanning')

    # Add construct types if no specific indicators but still multi-line
    if not annotations and metadata.get('is_multiline_segment'):
        construct_types = metadata.get('construct_types', [])
        if construct_types:
            # Shorten construct names for display
            short_names = {
                'conditional_block': 'if',
                'loop_block': 'loop',
                'function_block': 'fn',
                'class_block': 'class',
                'js_function_block': 'fn',
                'exception_block': 'try',
                'context_manager_block': 'with',
                'block_comment': 'comment',
                'template_literal': 'template',
            }
            short = [short_names.get(c, c) for c in construct_types[:2]]  # Limit to 2
            annotations.extend(short)
        else:
            annotations.append('multiline')

    if annotations:
        return f" [{', '.join(annotations)}]"
    return ""


def format_alignment_diff(result: AlignmentResult, context_lines: int = 0) -> str:
    """Format alignment result as a human-readable diff.

    Args:
        result: AlignmentResult from align_code_blocks
        context_lines: Number of context lines to show around divergent segments

    Returns:
        Formatted diff string showing aligned and divergent regions
    """
    output_parts = []

    output_parts.append("Alignment Summary:")
    output_parts.append(f"  Similarity: {result.similarity_ratio:.1%}")
    output_parts.append(f"  Aligned lines: {result.aligned_lines}")
    output_parts.append(f"  Divergent lines: {result.divergent_lines}")
    output_parts.append(f"  Block 1: {result.block1_total_lines} lines")
    output_parts.append(f"  Block 2: {result.block2_total_lines} lines")
    output_parts.append("")

    for seg in result.segments:
        if seg.segment_type == 'aligned':
            if context_lines > 0 and seg.block1_end - seg.block1_start > 2 * context_lines:
                # Show only context around aligned sections
                lines = seg.block1_text.split('\n')
                if len(lines) > 2 * context_lines:
                    output_parts.append(f"  {seg.block1_start+1}-{seg.block1_end}: [aligned, {len(lines)} lines]")
                else:
                    for line in lines:
                        output_parts.append(f"  {line}")
            else:
                for line in seg.block1_text.split('\n'):
                    output_parts.append(f"  {line}")

        elif seg.segment_type == 'divergent':
            # Build header with multi-line construct annotations
            header_suffix = _format_multiline_annotations(seg.metadata or {})
            output_parts.append(f"--- Block 1 [{seg.block1_start+1}-{seg.block1_end}]{header_suffix} ---")
            for line in seg.block1_text.split('\n'):
                output_parts.append(f"- {line}")
            output_parts.append(f"+++ Block 2 [{seg.block2_start+1}-{seg.block2_end}]{header_suffix} +++")
            for line in seg.block2_text.split('\n'):
                output_parts.append(f"+ {line}")

        elif seg.segment_type == 'deleted':
            header_suffix = _format_multiline_annotations(seg.metadata or {})
            output_parts.append(f"--- Block 1 [{seg.block1_start+1}-{seg.block1_end}] (deleted){header_suffix} ---")
            for line in seg.block1_text.split('\n'):
                output_parts.append(f"- {line}")

        elif seg.segment_type == 'inserted':
            header_suffix = _format_multiline_annotations(seg.metadata or {})
            output_parts.append(f"+++ Block 2 [{seg.block2_start+1}-{seg.block2_end}] (inserted){header_suffix} +++")
            for line in seg.block2_text.split('\n'):
                output_parts.append(f"+ {line}")

    return '\n'.join(output_parts)


def group_duplicates(
    matches: List[Dict[str, Any]],
    min_similarity: float = 0.8,
    min_lines: int = 3
) -> List[List[Dict[str, Any]]]:
    """Group similar code matches into duplication clusters.

    Uses hash-based bucketing to reduce O(n²) comparisons for large codebases.
    Only compares functions with similar line counts (within 20% difference).

    Args:
        matches: List of code matches from ast-grep
        min_similarity: Minimum similarity threshold (0-1)
        min_lines: Minimum lines to consider for duplication

    Returns:
        List of duplication groups (each group is a list of similar matches)
    """
    logger = get_logger("duplication.grouping")

    if not matches:
        return []

    # Filter by minimum lines and enrich with metadata
    filtered_matches = []
    for match in matches:
        text = match.get('text', '')
        line_count = len([line for line in text.split('\n') if line.strip()])
        if line_count >= min_lines:
            # Add metadata for optimization
            match['_line_count'] = line_count
            match['_normalized_hash'] = hash(normalize_code(text))
            filtered_matches.append(match)

    if not filtered_matches:
        return []

    logger.info(
        "grouping_start",
        total_candidates=len(filtered_matches),
        min_similarity=min_similarity
    )

    # Hash-based bucketing by line count (reduces comparison space)
    # Group functions into buckets of similar sizes (±20% tolerance)
    size_buckets: Dict[int, List[Dict[str, Any]]] = {}
    for match in filtered_matches:
        # Bucket key is line count rounded to nearest 5
        bucket_key = (match['_line_count'] // 5) * 5
        if bucket_key not in size_buckets:
            size_buckets[bucket_key] = []
        size_buckets[bucket_key].append(match)

    logger.info(
        "bucketing_complete",
        num_buckets=len(size_buckets),
        bucket_sizes={k: len(v) for k, v in list(size_buckets.items())[:10]}  # Log first 10
    )

    # Group similar matches within and across adjacent buckets
    groups: List[List[Dict[str, Any]]] = []
    used_indices: set[int] = set()
    comparisons_made = 0
    progress_interval = 100

    for i, match1 in enumerate(filtered_matches):
        if i in used_indices:
            continue

        # Log progress for large datasets
        if i > 0 and i % progress_interval == 0:
            logger.info(
                "grouping_progress",
                processed=i,
                total=len(filtered_matches),
                groups_found=len(groups),
                comparisons=comparisons_made
            )

        group = [match1]
        used_indices.add(i)
        match1_bucket = (match1['_line_count'] // 5) * 5

        # Only compare with matches in same or adjacent buckets (±20% size difference)
        candidate_buckets = [match1_bucket - 5, match1_bucket, match1_bucket + 5]
        candidates = []
        for bucket_key in candidate_buckets:
            if bucket_key in size_buckets:
                candidates.extend(size_buckets[bucket_key])

        for j, match2 in enumerate(filtered_matches[i + 1:], start=i + 1):
            if j in used_indices:
                continue

            # Skip if not in candidate buckets (too different in size)
            if match2 not in candidates:
                continue

            # Quick hash check before expensive similarity calculation
            if match1['_normalized_hash'] == match2['_normalized_hash']:
                # Identical after normalization
                group.append(match2)
                used_indices.add(j)
                comparisons_made += 1
            else:
                # Size similarity check (must be within 50% to be worth comparing)
                size_ratio = match1['_line_count'] / max(match2['_line_count'], 1)
                if size_ratio < 0.5 or size_ratio > 2.0:
                    continue

                # Expensive similarity calculation
                similarity = calculate_similarity(
                    match1.get('text', ''),
                    match2.get('text', '')
                )
                comparisons_made += 1

                if similarity >= min_similarity:
                    group.append(match2)
                    used_indices.add(j)

        # Only include groups with 2+ items (actual duplicates)
        if len(group) >= 2:
            groups.append(group)

    logger.info(
        "grouping_complete",
        groups_found=len(groups),
        total_comparisons=comparisons_made,
        max_possible_comparisons=(len(filtered_matches) * (len(filtered_matches) - 1)) // 2
    )

    return groups


def generate_refactoring_suggestions(
    duplication_groups: List[List[Dict[str, Any]]],
    construct_type: str,
    language: str,
    file_imports: Optional[Dict[str, List[str]]] = None,
    include_enhanced_analysis: bool = True
) -> List[Dict[str, Any]]:
    """Generate refactoring suggestions for duplicate code.

    Args:
        duplication_groups: Groups of duplicate code matches
        construct_type: Type of construct (function, class, etc.)
        language: Programming language
        file_imports: Optional dict mapping file paths to their import statements
                     (used for advanced import variation analysis)
        include_enhanced_analysis: Whether to include detailed parameter, import,
                                   and complexity analysis (default True)

    Returns:
        List of refactoring suggestions with enhanced analysis including:
        - group_id: Unique identifier for this duplication group
        - type: Suggestion type (Extract Shared Function, Extract Base Class, etc.)
        - description: Human-readable description
        - suggestion: Detailed refactoring guidance
        - duplicate_count: Number of duplicate instances
        - lines_per_duplicate: Lines in each instance
        - total_duplicated_lines: Total lines across all instances
        - locations: File:line ranges for each instance
        - sample_code: First 500 chars of representative code
        - complexity_score: Estimated refactoring complexity (1-10)
        - complexity_factors: Breakdown of complexity contributors
        - parameter_analysis: Identified parameters for extracted function/class
        - import_dependencies: Common and varying imports across instances
        - estimated_effort: Time estimate for refactoring (low/medium/high)
        - parameter_details: Varying identifiers/expressions/literals (if enhanced)
        - import_analysis: Advanced import variations and overlap (if enhanced)
        - complexity: Detailed complexity score from calculate_refactoring_complexity (if enhanced)
        - refactoring_strategies: Strategy options based on complexity (if enhanced)
    """
    suggestions = []

    for group_idx, group in enumerate(duplication_groups):
        if len(group) < 2:
            continue

        # Get locations of duplicates
        locations = []
        files_in_group = []
        for match in group:
            file_path = match.get('file', '')
            start_line = match.get('range', {}).get('start', {}).get('line', 0) + 1
            end_line = match.get('range', {}).get('end', {}).get('line', 0) + 1
            locations.append(f"{file_path}:{start_line}-{end_line}")
            if file_path and file_path not in files_in_group:
                files_in_group.append(file_path)

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

        # Calculate complexity score and factors
        complexity_factors = []
        complexity_score = 1  # Base score

        # Factor: Number of duplicates
        if len(group) > 5:
            complexity_score += 2
            complexity_factors.append(f"High duplicate count ({len(group)} instances)")
        elif len(group) > 3:
            complexity_score += 1
            complexity_factors.append(f"Multiple duplicates ({len(group)} instances)")

        # Factor: Code size
        if line_count > 50:
            complexity_score += 2
            complexity_factors.append(f"Large code blocks ({line_count} lines each)")
        elif line_count > 20:
            complexity_score += 1
            complexity_factors.append(f"Medium code blocks ({line_count} lines each)")

        # Factor: Cross-file refactoring
        if len(files_in_group) > 1:
            complexity_score += 2
            complexity_factors.append(f"Cross-file refactoring ({len(files_in_group)} files)")

        # Factor: Construct type complexity
        if construct_type == "class_definition":
            complexity_score += 2
            complexity_factors.append("Class-level refactoring requires inheritance design")
        elif construct_type == "function_definition":
            complexity_score += 1
            complexity_factors.append("Function extraction with parameter identification")

        # Cap complexity score at 10
        complexity_score = min(complexity_score, 10)

        # Analyze parameters (varying identifiers between instances)
        parameter_analysis: Dict[str, Any] = {
            "identified_parameters": [],
            "common_patterns": [],
            "suggested_signature": ""
        }

        if len(group) >= 2:
            varying = identify_varying_identifiers(
                group[0].get('text', ''),
                group[1].get('text', ''),
                language
            )

            # Extract unique parameter names
            param_names: set[str] = set()
            param_types: Dict[str, int] = {}
            for v in varying:
                id1, id2 = v.get('identifier1', ''), v.get('identifier2', '')
                id_type = v.get('identifier_type', 'unknown')

                # Create generic parameter name
                param_name = f"param_{id_type}_{len(param_names) + 1}"
                param_names.add(param_name)

                parameter_analysis["identified_parameters"].append({
                    "name": param_name,
                    "type": id_type,
                    "example_values": [id1, id2],
                    "position": v.get('position', 0)
                })

                if id_type not in param_types:
                    param_types[id_type] = 0
                param_types[id_type] += 1

            # Generate suggested signature
            if parameter_analysis["identified_parameters"]:
                params = [p["name"] for p in parameter_analysis["identified_parameters"][:5]]
                if construct_type == "function_definition":
                    parameter_analysis["suggested_signature"] = f"def extracted_function({', '.join(params)})"
                elif construct_type == "class_definition":
                    parameter_analysis["suggested_signature"] = f"class BaseClass({', '.join(params)})"
                else:
                    parameter_analysis["suggested_signature"] = f"extracted({', '.join(params)})"

            # Identify common patterns
            for id_type, count in param_types.items():
                if count > 1:
                    parameter_analysis["common_patterns"].append(
                        f"Multiple {id_type} variations ({count} found)"
                    )

        # Analyze import dependencies
        import_dependencies: Dict[str, List[str]] = {
            "common_imports": [],
            "varying_imports": [],
            "suggested_imports": []
        }

        # Extract imports from each instance's file
        instance_imports: Dict[str, List[str]] = {}
        for match in group:
            file_path = match.get('file', '')
            if file_path:
                # Simple import extraction from code text
                code_text = match.get('text', '')
                imports = []
                for line in code_text.split('\n'):
                    line = line.strip()
                    if line.startswith('import ') or line.startswith('from '):
                        imports.append(line)
                    elif language in ['javascript', 'typescript']:
                        if 'require(' in line or 'import ' in line:
                            imports.append(line)
                instance_imports[file_path] = imports

        # Find common and varying imports
        if instance_imports:
            all_imports = list(instance_imports.values())
            if all_imports:
                # Common imports appear in all instances
                common = set(all_imports[0])
                for imp_list in all_imports[1:]:
                    common &= set(imp_list)
                import_dependencies["common_imports"] = list(common)

                # Varying imports appear in some but not all
                all_unique: set[str] = set()
                for imp_list in all_imports:
                    all_unique.update(imp_list)
                import_dependencies["varying_imports"] = list(all_unique - common)

                # Suggested imports for extracted code
                import_dependencies["suggested_imports"] = list(common)

        # Estimate effort based on complexity
        if complexity_score <= 3:
            estimated_effort = "low"
        elif complexity_score <= 6:
            estimated_effort = "medium"
        else:
            estimated_effort = "high"

        suggestion_entry: Dict[str, Any] = {
            "group_id": group_idx + 1,
            "type": suggestion_type,
            "description": description,
            "suggestion": suggestion_text,
            "duplicate_count": len(group),
            "lines_per_duplicate": line_count,
            "total_duplicated_lines": total_duplicated_lines,
            "locations": locations,
            "sample_code": sample_text[:500],  # First 500 chars as sample
            # Enhanced fields
            "complexity_score": complexity_score,
            "complexity_factors": complexity_factors,
            "parameter_analysis": parameter_analysis,
            "import_dependencies": import_dependencies,
            "estimated_effort": estimated_effort
        }

        # Additional enhanced analysis using new analysis functions
        if include_enhanced_analysis and len(group) >= 2:
            code1 = group[0].get('text', '')
            code2 = group[1].get('text', '')

            # Parameter details from identify_varying_* functions
            varying_expressions = identify_varying_expressions(code1, code2, language)
            varying_literals = identify_varying_literals(code1, code2, language)

            suggestion_entry["parameter_details"] = {
                "varying_identifiers": parameter_analysis.get("identified_parameters", []),
                "varying_expressions": varying_expressions,
                "varying_literals": varying_literals,
                "total_parameters_needed": len(parameter_analysis.get("identified_parameters", [])) + len(varying_literals)
            }

            # Advanced import analysis using detect_import_variations and analyze_import_overlap
            if file_imports:
                group_imports = {
                    fp: file_imports[fp]
                    for fp in files_in_group
                    if fp in file_imports
                }

                if group_imports:
                    import_variations = detect_import_variations(group_imports, language)
                    import_overlap = analyze_import_overlap(group_imports, sample_text)

                    suggestion_entry["import_analysis"] = {
                        "variations": import_variations,
                        "overlap": import_overlap
                    }

            # Calculate detailed complexity using calculate_refactoring_complexity
            # Count control flow branches in sample code
            control_flow_count = 0
            for keyword in ['if ', 'elif ', 'else:', 'for ', 'while ', 'switch', 'case ']:
                control_flow_count += sample_text.count(keyword)

            # Calculate nesting depth (heuristic based on indentation)
            lines = sample_text.split('\n')
            max_indent = 0
            for line in lines:
                if line.strip():
                    indent = len(line) - len(line.lstrip())
                    indent_level = indent // 4 if '    ' in line else indent
                    max_indent = max(max_indent, indent_level)

            # Determine cross-file dependency
            cross_file = 1 if len(files_in_group) > 1 else 0

            # Import count from analysis
            import_count = len(import_dependencies.get("suggested_imports", []))

            complexity_input = {
                "parameter_count": len(parameter_analysis.get("identified_parameters", [])) + len(varying_literals),
                "parameter_type_complexity": 1 if varying_expressions else 0,
                "control_flow_branches": control_flow_count,
                "import_count": import_count,
                "cross_file_dependency": cross_file,
                "line_count": line_count,
                "nesting_depth": max_indent,
                "return_complexity": 1 if 'return ' in sample_text else 0
            }

            detailed_complexity = calculate_refactoring_complexity(complexity_input)
            suggestion_entry["complexity"] = detailed_complexity

            # Generate refactoring strategy options based on complexity
            strategies = _generate_refactoring_strategies(
                detailed_complexity['level'],
                construct_type,
                len(group),
                len(parameter_analysis.get("identified_parameters", [])) + len(varying_literals)
            )
            suggestion_entry["refactoring_strategies"] = strategies

        suggestions.append(suggestion_entry)

    return suggestions


def _generate_refactoring_strategies(
    complexity_level: str,
    construct_type: str,
    duplicate_count: int,
    parameter_count: int
) -> List[Dict[str, Any]]:
    """Generate refactoring strategy options based on complexity analysis.

    Args:
        complexity_level: 'low', 'medium', or 'high'
        construct_type: Type of construct being refactored
        duplicate_count: Number of duplicate instances
        parameter_count: Number of parameters needed

    Returns:
        List of strategy options with name, description, and effort level
    """
    strategies: List[Dict[str, Any]] = []

    if complexity_level == 'low':
        strategies.append({
            "name": "Direct Extract",
            "description": f"Extract the common code directly into a single function with {parameter_count} parameter(s). "
                          f"This is straightforward for low-complexity duplicates.",
            "effort": "low",
            "recommended": True
        })
        if construct_type == "function_definition":
            strategies.append({
                "name": "Inline Consolidation",
                "description": "Keep one function and update all callers to use it.",
                "effort": "low",
                "recommended": False
            })

    elif complexity_level == 'medium':
        strategies.append({
            "name": "Parameterized Extract",
            "description": f"Extract with careful parameterization. Consider using default values or "
                          f"overloads to handle the {parameter_count} varying elements.",
            "effort": "medium",
            "recommended": True
        })
        strategies.append({
            "name": "Strategy Pattern",
            "description": "Extract common logic and use callbacks/strategy objects for varying behavior.",
            "effort": "medium",
            "recommended": False
        })
        if duplicate_count > 3:
            strategies.append({
                "name": "Phased Refactoring",
                "description": f"Consolidate {duplicate_count} duplicates in phases, starting with most similar pairs.",
                "effort": "medium",
                "recommended": False
            })

    else:  # high complexity
        strategies.append({
            "name": "Incremental Simplification",
            "description": "First simplify each duplicate individually, then extract common parts. "
                          "High complexity suggests the code may benefit from decomposition first.",
            "effort": "high",
            "recommended": True
        })
        strategies.append({
            "name": "Template Method Pattern",
            "description": "Create a base with template method, let variations override specific steps.",
            "effort": "high",
            "recommended": False
        })
        strategies.append({
            "name": "Partial Extraction",
            "description": "Extract only the truly common core, leaving complex variations in place. "
                          "This reduces risk while still eliminating some duplication.",
            "effort": "medium",
            "recommended": False
        })

    return strategies


def identify_varying_identifiers(
    code1: str,
    code2: str,
    language: str
) -> List[Dict[str, Any]]:
    """Identify varying identifiers (variable names, function names, etc.) between two similar code blocks.

    This function compares two code snippets and identifies identifiers that differ
    at corresponding positions, helping to parameterize duplicated code.

    Args:
        code1: First code snippet
        code2: Second code snippet
        language: Programming language for parsing

    Returns:
        List of dicts with keys:
            - position: Line number where the difference occurs
            - identifier1: Identifier from code1
            - identifier2: Identifier from code2
            - identifier_type: Type of identifier (variable, function, class, parameter, etc.)
    """
    import re

    varying_identifiers: List[Dict[str, Any]] = []

    # Split into lines for position tracking
    lines1 = code1.split('\n')
    lines2 = code2.split('\n')

    # Define identifier patterns based on language
    patterns: Dict[str, List[Tuple[str, str]]] = {
        "python": [
            (r'\bdef\s+(\w+)\s*\(', "function"),
            (r'\bclass\s+(\w+)', "class"),
            (r'(\w+)\s*=(?!=)', "variable"),
            (r'for\s+(\w+)\s+in', "loop_variable"),
            (r'def\s+\w+\s*\(([^)]+)\)', "parameter"),
            (r'import\s+(\w+)', "import"),
            (r'from\s+(\w+)', "module"),
        ],
        "javascript": [
            (r'\bfunction\s+(\w+)\s*\(', "function"),
            (r'\bclass\s+(\w+)', "class"),
            (r'\b(?:let|const|var)\s+(\w+)', "variable"),
            (r'(\w+)\s*:\s*function', "method"),
            (r'for\s*\(\s*(?:let|const|var)\s+(\w+)', "loop_variable"),
        ],
        "typescript": [
            (r'\bfunction\s+(\w+)\s*[<(]', "function"),
            (r'\bclass\s+(\w+)', "class"),
            (r'\b(?:let|const|var)\s+(\w+)', "variable"),
            (r'\binterface\s+(\w+)', "interface"),
            (r'\btype\s+(\w+)', "type_alias"),
        ],
    }

    # Get patterns for the language (default to generic)
    lang_patterns = patterns.get(language.lower(), [
        (r'\b(\w+)\s*\(', "function_call"),
        (r'(\w+)\s*=', "variable"),
        (r'\bclass\s+(\w+)', "class"),
    ])

    # Compare lines and extract identifiers
    min_lines = min(len(lines1), len(lines2))

    for i in range(min_lines):
        line1 = lines1[i]
        line2 = lines2[i]

        # Skip identical lines
        if line1.strip() == line2.strip():
            continue

        # Extract identifiers from each line
        for pattern, id_type in lang_patterns:
            matches1 = re.findall(pattern, line1)
            matches2 = re.findall(pattern, line2)

            # Handle parameter lists (comma-separated)
            if id_type == "parameter":
                if matches1:
                    matches1 = [p.strip() for p in matches1[0].split(',') if p.strip()]
                if matches2:
                    matches2 = [p.strip() for p in matches2[0].split(',') if p.strip()]

            # Compare matches at corresponding positions
            if matches1 and matches2:
                for j in range(min(len(matches1), len(matches2))):
                    id1 = matches1[j].strip() if isinstance(matches1[j], str) else str(matches1[j])
                    id2 = matches2[j].strip() if isinstance(matches2[j], str) else str(matches2[j])

                    # Clean up parameter type annotations
                    id1 = id1.split(':')[0].strip()
                    id2 = id2.split(':')[0].strip()

                    if id1 != id2 and id1 and id2:
                        # Avoid duplicates
                        existing = any(
                            v['identifier1'] == id1 and v['identifier2'] == id2 and v['position'] == i + 1
                            for v in varying_identifiers
                        )
                        if not existing:
                            varying_identifiers.append({
                                "position": i + 1,
                                "identifier1": id1,
                                "identifier2": id2,
                                "identifier_type": id_type
                            })

    # Token-level comparison for additional differences
    identifier_pattern = re.compile(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b')

    tokens1 = identifier_pattern.findall(code1)
    tokens2 = identifier_pattern.findall(code2)

    # Use SequenceMatcher to align tokens
    matcher = difflib.SequenceMatcher(None, tokens1, tokens2)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'replace':
            for k in range(min(i2 - i1, j2 - j1)):
                tok1 = tokens1[i1 + k]
                tok2 = tokens2[j1 + k]

                # Skip keywords
                keywords = {'def', 'class', 'return', 'if', 'else', 'for', 'while', 'in', 'import',
                           'from', 'as', 'try', 'except', 'with', 'and', 'or', 'not', 'is', 'True',
                           'False', 'None', 'function', 'const', 'let', 'var', 'async', 'await'}

                if tok1 in keywords or tok2 in keywords:
                    continue

                if tok1 != tok2:
                    pos = code1.find(tok1)
                    line_num = code1[:pos].count('\n') + 1 if pos != -1 else 0

                    existing = any(
                        v['identifier1'] == tok1 and v['identifier2'] == tok2
                        for v in varying_identifiers
                    )
                    if not existing and line_num > 0:
                        varying_identifiers.append({
                            "position": line_num,
                            "identifier1": tok1,
                            "identifier2": tok2,
                            "identifier_type": "identifier"
                        })

    # Sort by position
    varying_identifiers.sort(key=lambda x: (x['position'], x['identifier_type']))

    return varying_identifiers


def get_group_varying_identifiers(
    group: List[Dict[str, Any]],
    language: str
) -> List[Dict[str, Any]]:
    """Analyze a duplication group to find all varying identifiers across instances.

    Compares the first instance with all others to build a comprehensive
    list of parameterization opportunities.

    Args:
        group: List of duplicate code matches
        language: Programming language

    Returns:
        List of varying identifier analyses, one per pair comparison
    """
    if len(group) < 2:
        return []

    results = []
    base_code = group[0].get('text', '')
    base_file = group[0].get('file', '')
    base_line = group[0].get('range', {}).get('start', {}).get('line', 0) + 1

    for i, match in enumerate(group[1:], start=1):
        compare_code = match.get('text', '')
        compare_file = match.get('file', '')
        compare_line = match.get('range', {}).get('start', {}).get('line', 0) + 1

        varying = identify_varying_identifiers(base_code, compare_code, language)

        if varying:
            results.append({
                "comparison_index": i,
                "base_location": f"{base_file}:{base_line}",
                "compare_location": f"{compare_file}:{compare_line}",
                "varying_identifiers": varying,
                "parameterization_count": len(varying)
            })

    return results


def generate_parameter_name(
    values: List[str],
    literal_type: str,
    context: Optional[str] = None,
    existing_names: Optional[Set[str]] = None
) -> str:
    """Generate a descriptive parameter name from varying code values.

    Analyzes the values to create meaningful parameter names suitable for
    refactoring duplicate code into parameterized functions.

    Args:
        values: List of varying values (e.g., ["user@example.com", "admin@test.org"])
        literal_type: Type of literal ("string", "number", "identifier")
        context: Optional surrounding code context for better naming
        existing_names: Set of already-used names to avoid collisions

    Returns:
        A valid Python/JS identifier name for the parameter
    """
    import re

    if existing_names is None:
        existing_names = set()

    def make_valid_identifier(name: str) -> str:
        """Convert string to valid Python/JS identifier."""
        name = name.strip().strip('"\'')
        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        name = re.sub(r'_+', '_', name)
        name = name.strip('_')
        if name and name[0].isdigit():
            name = f"value_{name}"
        name = name.lower()
        return name if name else "param"

    def extract_meaningful_words(text: str) -> List[str]:
        """Extract meaningful words from text."""
        text = text.strip('"\'')
        words = re.split(r'[@._\-/\\:\s]+', text)
        return [w.lower() for w in words if len(w) >= 2 and not w.isdigit()]

    base_name = "param"

    if literal_type == "string":
        all_words: List[str] = []
        for value in values:
            all_words.extend(extract_meaningful_words(value))

        if all_words:
            word_counts: Dict[str, int] = {}
            for word in all_words:
                word_counts[word] = word_counts.get(word, 0) + 1

            if any('@' in v for v in values):
                base_name = "email"
            elif any(v.startswith(('http://', 'https://', 'www.')) for v in values):
                base_name = "url"
            elif any('/' in v or '\\' in v for v in values):
                base_name = "path"
            else:
                common_words = [w for w, c in word_counts.items() if c >= len(values)]
                if common_words:
                    base_name = max(common_words, key=len)
                elif all_words:
                    base_name = all_words[0]
        else:
            base_name = "text"

    elif literal_type == "number":
        try:
            nums = [float(v) for v in values]
            if all(n == int(n) for n in nums):
                if all(0 <= n <= 1 for n in nums):
                    base_name = "flag"
                elif all(n > 0 and n == int(n) for n in nums):
                    if max(nums) <= 100:
                        base_name = "count"
                    elif max(nums) > 1000:
                        base_name = "size"
                    else:
                        base_name = "limit"
                else:
                    base_name = "value"
            else:
                if all(0 <= n <= 1 for n in nums):
                    base_name = "ratio"
                else:
                    base_name = "amount"
        except (ValueError, TypeError):
            base_name = "number"

        if context:
            context_lower = context.lower()
            if 'retry' in context_lower or 'attempt' in context_lower:
                base_name = "max_retries"
            elif 'timeout' in context_lower:
                base_name = "timeout"
            elif 'port' in context_lower:
                base_name = "port"
            elif 'size' in context_lower or 'length' in context_lower:
                base_name = "size"
            elif 'index' in context_lower or 'idx' in context_lower:
                base_name = "index"
            elif 'count' in context_lower or 'num' in context_lower:
                base_name = "count"
            elif 'delay' in context_lower or 'sleep' in context_lower:
                base_name = "delay"
            elif 'width' in context_lower:
                base_name = "width"
            elif 'height' in context_lower:
                base_name = "height"

    elif literal_type == "identifier":
        common_prefix = ""
        common_suffix = ""

        if len(values) >= 2:
            for i in range(min(len(v) for v in values)):
                chars = set(v[i] for v in values)
                if len(chars) == 1:
                    common_prefix += values[0][i]
                else:
                    break

            reversed_values = [v[::-1] for v in values]
            for i in range(min(len(v) for v in reversed_values)):
                chars = set(v[i] for v in reversed_values)
                if len(chars) == 1:
                    common_suffix = reversed_values[0][i] + common_suffix
                else:
                    break

        varying_parts = []
        for value in values:
            start = len(common_prefix)
            end = len(value) - len(common_suffix) if common_suffix else len(value)
            if start < end:
                varying_parts.append(value[start:end])

        if common_prefix:
            prefix_clean = make_valid_identifier(common_prefix.rstrip('_'))
            if prefix_clean in ('get', 'set', 'fetch', 'load', 'save', 'create', 'delete', 'update'):
                base_name = "entity_name"
            elif prefix_clean:
                base_name = f"{prefix_clean}_type"
            else:
                base_name = "name"
        elif varying_parts:
            all_parts = '_'.join(varying_parts)
            base_name = make_valid_identifier(all_parts)
            if not base_name:
                base_name = "identifier"
        else:
            base_name = "name"

    elif literal_type == "boolean":
        base_name = "enabled" if context and 'enable' in context.lower() else "flag"

    base_name = make_valid_identifier(base_name)
    if not base_name:
        base_name = "param"

    final_name = base_name
    counter = 1
    while final_name in existing_names:
        counter += 1
        final_name = f"{base_name}_{counter}"

    return final_name


def generate_parameter_names_for_variations(
    varying_literals: List[Dict[str, Any]],
    varying_identifiers: List[Dict[str, Any]],
    context_lines: Optional[List[str]] = None
) -> Dict[str, str]:
    """Generate parameter names for all variations in duplicate code.

    Args:
        varying_literals: Output from identify_varying_literals
        varying_identifiers: Output from identify_varying_identifiers
        context_lines: Optional code lines for context-aware naming

    Returns:
        Dict mapping position keys to generated parameter names
    """
    existing_names: Set[str] = set()
    param_names: Dict[str, str] = {}

    for lit in varying_literals:
        pos_key = f"lit_{lit['position']}_{lit.get('column', 0)}"
        values = [lit['value1'], lit['value2']]
        context = None
        if context_lines:
            line_idx = lit['position'] - 1
            if 0 <= line_idx < len(context_lines):
                context = context_lines[line_idx]
        name = generate_parameter_name(values, lit['literal_type'], context, existing_names)
        param_names[pos_key] = name
        existing_names.add(name)

    for ident in varying_identifiers:
        pos_key = f"id_{ident['position']}"
        values = [ident['identifier1'], ident['identifier2']]
        context = None
        if context_lines:
            line_idx = ident['position'] - 1
            if 0 <= line_idx < len(context_lines):
                context = context_lines[line_idx]
        name = generate_parameter_name(values, "identifier", context, existing_names)
        param_names[pos_key] = name
        existing_names.add(name)

    return param_names


# =============================================================================
# Code Generation Templates
# =============================================================================

# Java method template with support for annotations, generics, and throws clause
JAVA_METHOD_TEMPLATE: str = """{javadoc}{annotations}{modifiers}{type_params}{return_type} {name}({params}){throws} {{
{body}
}}"""


def format_java_method(
    name: str,
    params: str,
    body: str,
    return_type: str = "void",
    modifiers: Optional[List[str]] = None,
    annotations: Optional[List[str]] = None,
    type_params: Optional[str] = None,
    throws: Optional[List[str]] = None,
    javadoc: Optional[str] = None,
) -> str:
    """Format a Java method using the template.

    Args:
        name: Method name
        params: Parameter list (e.g., "String name, int age")
        body: Method body (will be indented with 4 spaces)
        return_type: Return type (default: "void")
        modifiers: Optional list of modifiers ["public", "static", "final"]
        annotations: Optional list of annotations ["@Override", "@Deprecated"]
        type_params: Optional type parameters (e.g., "<T extends Comparable<T>>")
        throws: Optional list of exceptions ["IOException", "SQLException"]
        javadoc: Optional Javadoc comment (without /** */)

    Returns:
        Formatted Java method string
    """
    # Format annotations (each on its own line)
    annotations_str = ""
    if annotations:
        annotations_str = "\n".join(annotations) + "\n"

    # Format modifiers (space-separated)
    modifiers_str = ""
    if modifiers:
        modifiers_str = " ".join(modifiers) + " "

    # Format type parameters
    type_params_str = ""
    if type_params:
        type_params_str = type_params + " "

    # Format throws clause
    throws_str = ""
    if throws:
        throws_str = " throws " + ", ".join(throws)

    # Format Javadoc
    javadoc_str = ""
    if javadoc:
        javadoc_lines = javadoc.strip().split("\n")
        javadoc_str = "/**\n"
        for line in javadoc_lines:
            javadoc_str += f" * {line}\n"
        javadoc_str += " */\n"

    # Indent body with 4 spaces
    body_lines = body.strip().split("\n")
    indented_body = "\n".join("    " + line if line.strip() else "" for line in body_lines)

    return JAVA_METHOD_TEMPLATE.format(
        javadoc=javadoc_str,
        annotations=annotations_str,
        modifiers=modifiers_str,
        type_params=type_params_str,
        return_type=return_type,
        name=name,
        params=params,
        throws=throws_str,
        body=indented_body,
    )


def identify_varying_expressions(
    code1: str,
    code2: str,
    language: str
) -> List[Tuple[int, str, str, str]]:
    """Identify varying expressions between two duplicate code blocks.

    Analyzes structurally similar code blocks to identify expressions that differ
    at the same structural positions. This helps understand what parts need to be
    parameterized when refactoring duplicates.

    Unlike identify_varying_identifiers which focuses on variable/function names,
    this function identifies:
    - Different function calls (api.get() vs api.post())
    - Different operators (+ vs -)
    - Different compound expressions (a + b vs a * b)
    - Different literals and method chains

    Args:
        code1: First code block
        code2: Second code block
        language: Programming language for parsing

    Returns:
        List of tuples: (position, expr1, expr2, expression_type)
        - position: Line number where variation occurs
        - expr1: Expression from first code block
        - expr2: Expression from second code block
        - expression_type: Type of expression (function_call, method_call, operator, etc.)
    """
    logger = get_logger("duplication.varying_expressions")

    variations: List[Tuple[int, str, str, str]] = []

    if not code1 or not code2:
        return variations

    lines1 = code1.split('\n')
    lines2 = code2.split('\n')

    matcher = difflib.SequenceMatcher(None, lines1, lines2)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'replace':
            for offset in range(min(i2 - i1, j2 - j1)):
                line1 = lines1[i1 + offset] if i1 + offset < len(lines1) else ''
                line2 = lines2[j1 + offset] if j1 + offset < len(lines2) else ''
                expr_variations = _extract_expression_variations(
                    line1, line2, i1 + offset + 1, language
                )
                variations.extend(expr_variations)
        elif tag == 'equal':
            for offset in range(i2 - i1):
                line1 = lines1[i1 + offset]
                line2 = lines2[j1 + offset]
                if line1 != line2:
                    expr_variations = _extract_expression_variations(
                        line1, line2, i1 + offset + 1, language
                    )
                    variations.extend(expr_variations)

    logger.debug(
        "varying_expressions_identified",
        total_variations=len(variations),
        language=language
    )

    return variations


def _extract_expression_variations(
    line1: str,
    line2: str,
    position: int,
    language: str
) -> List[Tuple[int, str, str, str]]:
    """Extract and classify expression variations between two lines."""
    variations: List[Tuple[int, str, str, str]] = []

    if line1.strip() == line2.strip():
        return variations

    words1 = line1.split()
    words2 = line2.split()
    word_matcher = difflib.SequenceMatcher(None, words1, words2)

    for tag, i1, i2, j1, j2 in word_matcher.get_opcodes():
        if tag in ('replace', 'delete', 'insert'):
            expr1 = ' '.join(words1[i1:i2]) if i1 < i2 else ''
            expr2 = ' '.join(words2[j1:j2]) if j1 < j2 else ''
            if expr1 or expr2:
                expr_type = _classify_expression_type(expr1, expr2, language)
                variations.append((position, expr1, expr2, expr_type))

    return variations


def _classify_expression_type(expr1: str, expr2: str, language: str) -> str:
    """Classify the type of expression variation."""
    expr = expr1 if expr1 else expr2
    if not expr:
        return 'unknown'

    # Function/method call patterns
    if '(' in expr and ')' in expr:
        if '.' in expr.split('(')[0]:
            return 'method_call'
        return 'function_call'

    # Operator patterns (check longer operators first)
    operators = [
        ('==', 'equality_operator'), ('!=', 'inequality_operator'),
        ('<=', 'comparison_operator'), ('>=', 'comparison_operator'),
        ('&&', 'logical_operator'), ('||', 'logical_operator'),
        ('+=', 'compound_assignment'), ('-=', 'compound_assignment'),
        ('*=', 'compound_assignment'), ('/=', 'compound_assignment'),
        ('<', 'comparison_operator'), ('>', 'comparison_operator'),
        ('+', 'addition_operator'), ('-', 'subtraction_operator'),
        ('*', 'multiplication_operator'), ('/', 'division_operator'),
        ('%', 'modulo_operator'), ('and', 'logical_operator'), ('or', 'logical_operator'),
    ]
    for op, op_type in operators:
        if op in expr:
            return op_type

    # Literal patterns
    if (expr.startswith('"') and expr.endswith('"')) or \
       (expr.startswith("'") and expr.endswith("'")):
        return 'string_literal'
    if expr.replace('.', '').replace('-', '').isdigit():
        return 'numeric_literal'
    if expr.lower() in ('true', 'false'):
        return 'boolean_literal'
    if expr.lower() in ('none', 'null', 'nil'):
        return 'null_literal'

    # Access patterns
    if '[' in expr and ']' in expr:
        return 'array_access'
    if '.' in expr and '(' not in expr:
        return 'attribute_access'
    if expr.replace('_', '').isalnum():
        return 'identifier'

    return 'compound_expression'


def analyze_duplicate_variations(
    group: List[Dict[str, Any]],
    language: str
) -> Dict[str, Any]:
    """Analyze all variations within a duplication group.

    Args:
        group: List of duplicate code matches
        language: Programming language

    Returns:
        Analysis with total_variations, common_variation_types,
        parameterization_suggestions, and variations_by_position
    """
    logger = get_logger("duplication.variation_analysis")

    if len(group) < 2:
        return {
            'total_variations': 0,
            'common_variation_types': [],
            'parameterization_suggestions': [],
            'variations_by_position': {}
        }

    all_variations: List[Tuple[int, str, str, str]] = []
    variation_type_counts: Dict[str, int] = {}
    variations_by_position: Dict[int, List[Dict[str, str]]] = {}

    base_code = group[0].get('text', '')

    for i in range(1, len(group)):
        compare_code = group[i].get('text', '')
        variations = identify_varying_expressions(base_code, compare_code, language)

        for pos, expr1, expr2, expr_type in variations:
            all_variations.append((pos, expr1, expr2, expr_type))
            variation_type_counts[expr_type] = variation_type_counts.get(expr_type, 0) + 1

            if pos not in variations_by_position:
                variations_by_position[pos] = []
            variations_by_position[pos].append({
                'expr1': expr1, 'expr2': expr2, 'expression_type': expr_type
            })

    sorted_types = sorted(variation_type_counts.items(), key=lambda x: x[1], reverse=True)
    common_types = [t[0] for t in sorted_types[:5]]

    suggestions = _generate_parameterization_suggestions(variations_by_position, common_types)

    logger.info(
        "variation_analysis_complete",
        total_variations=len(all_variations),
        common_types=common_types,
        positions_with_variations=len(variations_by_position)
    )

    return {
        'total_variations': len(all_variations),
        'common_variation_types': common_types,
        'parameterization_suggestions': suggestions,
        'variations_by_position': {str(k): v for k, v in variations_by_position.items()}
    }


def _generate_parameterization_suggestions(
    variations_by_position: Dict[int, List[Dict[str, str]]],
    common_types: List[str]
) -> List[str]:
    """Generate suggestions for parameterizing duplicate code."""
    suggestions: List[str] = []

    type_suggestions = {
        'function_call': 'Consider passing the function as a callback parameter',
        'method_call': 'Consider using dependency injection or strategy pattern for the varying method',
        'string_literal': 'Extract string literals as parameters or constants',
        'numeric_literal': 'Parameterize numeric values or define as named constants',
        'identifier': 'Pass variable references as function parameters',
        'attribute_access': 'Consider using a configuration object for varying attributes',
        'comparison_operator': 'Pass a comparison function or use a predicate parameter',
        'logical_operator': 'Consider parameterizing the boolean logic or using strategy pattern',
        'array_access': 'Parameterize the index or key being accessed',
        'compound_expression': 'Break down complex expressions and parameterize sub-components',
        'addition_operator': 'Consider parameterizing the operation or using a strategy pattern',
        'subtraction_operator': 'Consider parameterizing the operation or using a strategy pattern',
        'multiplication_operator': 'Consider parameterizing the operation or using a strategy pattern',
        'division_operator': 'Consider parameterizing the operation or using a strategy pattern',
    }

    for var_type in common_types:
        if var_type in type_suggestions:
            suggestions.append(type_suggestions[var_type])

    if len(variations_by_position) == 1:
        pos = list(variations_by_position.keys())[0]
        suggestions.append(f"Single variation point at line {pos} - straightforward parameterization possible")
    elif len(variations_by_position) > 3:
        suggestions.append(
            f"Multiple variation points ({len(variations_by_position)} lines) - "
            "consider using a configuration object to group parameters"
        )

    return suggestions


def calculate_refactoring_complexity(
    analysis_results: Dict[str, Any]
) -> Dict[str, Any]:
    """Calculate complexity score for refactoring duplicate code.

    Uses weighted factors to determine how difficult it would be to
    consolidate duplicate code into a single reusable function.

    Args:
        analysis_results: Dictionary containing complexity factors:
            - parameter_count: Number of parameters needed
            - parameter_type_complexity: 0-2 scale for type complexity
            - control_flow_branches: Number of if/else/switch branches
            - import_count: Number of imports required
            - cross_file_dependency: Whether code spans files (0 or 1)
            - line_count: Number of lines in the duplicate
            - nesting_depth: Maximum nesting level
            - return_complexity: Complexity of return values (0-2)

    Returns:
        Dictionary with:
            - score: Scaled 1-10 complexity score
            - level: 'low', 'medium', or 'high'
            - breakdown: Individual factor contributions
            - raw_score: Unscaled weighted sum
    """
    # Extract factors with defaults
    parameter_count = analysis_results.get('parameter_count', 0)
    parameter_type_complexity = analysis_results.get('parameter_type_complexity', 0)
    control_flow_branches = analysis_results.get('control_flow_branches', 0)
    import_count = analysis_results.get('import_count', 0)
    cross_file_dependency = analysis_results.get('cross_file_dependency', 0)
    line_count = analysis_results.get('line_count', 0)
    nesting_depth = analysis_results.get('nesting_depth', 0)
    return_complexity = analysis_results.get('return_complexity', 0)

    # Apply weights from research formula
    breakdown = {
        'parameter_count': parameter_count * 1.5,
        'parameter_type_complexity': parameter_type_complexity * 1.0,
        'control_flow_branches': control_flow_branches * 2.5,
        'import_count': import_count * 1.0,
        'cross_file_dependency': cross_file_dependency * 2.0,
        'line_count': min(line_count, 50) * 0.1,
        'nesting_depth': nesting_depth * 1.5,
        'return_complexity': return_complexity * 1.0
    }

    raw_score = sum(breakdown.values())

    # Scale to 1-10 range
    # Calibrated bounds based on realistic scenarios:
    # - Simple literal change: raw ~1-3 -> score 1-2
    # - Multiple params, simple logic: raw ~5-12 -> score 3-5
    # - Complex conditionals, cross-file: raw ~15-30 -> score 7-10
    if raw_score <= 0:
        scaled_score = 1.0
    elif raw_score >= 30:
        scaled_score = 10.0
    else:
        # Linear scaling from 0-30 to 1-10
        scaled_score = 1.0 + (raw_score / 30.0) * 9.0

    # Round to 1 decimal place
    scaled_score = round(scaled_score, 1)

    # Determine complexity level
    complexity_info = get_complexity_level(scaled_score)

    return {
        'score': scaled_score,
        'level': complexity_info['level'],
        'description': complexity_info['description'],
        'breakdown': breakdown,
        'raw_score': round(raw_score, 2)
    }


def get_complexity_level(score: float) -> Dict[str, str]:
    """Determine complexity level from numeric score with description.

    Args:
        score: Complexity score from 1-10

    Returns:
        Dictionary with 'level' and 'description' keys
    """
    if score <= 3.0:
        return {
            'level': 'low',
            'description': 'Simple refactoring - straightforward extraction with minimal parameters'
        }
    elif score <= 6.0:
        return {
            'level': 'medium',
            'description': 'Moderate refactoring - requires careful parameter design and testing'
        }
    else:
        return {
            'level': 'high',
            'description': 'Complex refactoring - significant abstraction needed, consider incremental approach'
        }


# =============================================================================
# Code Generation Templates - Phase 2 (Code Generation Engine)
# =============================================================================

# TypeScript function declaration template
# Placeholders: {export}, {async}, {name}, {type_params}, {params}, {return_type}, {jsdoc}, {body}
TYPESCRIPT_FUNCTION_TEMPLATE: str = """{jsdoc}{export}function {name}{type_params}({params}){return_type} {{
{body}
}}"""

# TypeScript async function declaration template
TYPESCRIPT_ASYNC_FUNCTION_TEMPLATE: str = """{jsdoc}{export}async function {name}{type_params}({params}){return_type} {{
{body}
}}"""

# TypeScript arrow function template
TYPESCRIPT_ARROW_FUNCTION_TEMPLATE: str = """{jsdoc}{export}const {name} = {async}{type_params}({params}){return_type} => {{
{body}
}};"""

# JavaScript function declaration template (no type annotations)
# Placeholders: {export}, {async}, {name}, {params}, {jsdoc}, {body}
JAVASCRIPT_FUNCTION_TEMPLATE: str = """{jsdoc}{export}function {name}({params}) {{
{body}
}}"""

# JavaScript async function declaration template
JAVASCRIPT_ASYNC_FUNCTION_TEMPLATE: str = """{jsdoc}{export}async function {name}({params}) {{
{body}
}}"""

# JavaScript arrow function template
JAVASCRIPT_ARROW_FUNCTION_TEMPLATE: str = """{jsdoc}{export}const {name} = {async}({params}) => {{
{body}
}};"""


def format_typescript_function(
    name: str,
    params: List[Tuple[str, str]],
    body: str,
    return_type: str = "void",
    export: bool = False,
    is_async: bool = False,
    type_params: Optional[List[str]] = None,
    jsdoc: Optional[str] = None,
    use_arrow: bool = False
) -> str:
    """Generate a TypeScript function from template.

    Args:
        name: Function name
        params: List of (param_name, param_type) tuples
        body: Function body (will be indented)
        return_type: Return type annotation (default "void")
        export: Whether to export the function
        is_async: Whether function is async
        type_params: Optional generic type parameters (e.g., ["T", "U"])
        jsdoc: Optional JSDoc comment block
        use_arrow: Use arrow function syntax instead of declaration

    Returns:
        Formatted TypeScript function string
    """
    # Format placeholders
    export_str = "export " if export else ""
    async_str = "async " if is_async else ""

    # Format type parameters
    type_params_str = ""
    if type_params:
        type_params_str = f"<{', '.join(type_params)}>"

    # Format parameters with types
    params_str = ", ".join(f"{p[0]}: {p[1]}" for p in params)

    # Format return type
    return_type_str = f": {return_type}" if return_type else ""
    if is_async and return_type and not return_type.startswith("Promise"):
        return_type_str = f": Promise<{return_type}>"

    # Format JSDoc
    jsdoc_str = f"{jsdoc}\n" if jsdoc else ""

    # Indent body (2 spaces for JS/TS convention)
    indented_body = "\n".join(f"  {line}" if line.strip() else line
                               for line in body.split("\n"))

    if use_arrow:
        return TYPESCRIPT_ARROW_FUNCTION_TEMPLATE.format(
            jsdoc=jsdoc_str,
            export=export_str,
            name=name,
            **{"async": async_str},
            type_params=type_params_str,
            params=params_str,
            return_type=return_type_str,
            body=indented_body
        )
    elif is_async:
        return TYPESCRIPT_ASYNC_FUNCTION_TEMPLATE.format(
            jsdoc=jsdoc_str,
            export=export_str,
            name=name,
            type_params=type_params_str,
            params=params_str,
            return_type=return_type_str,
            body=indented_body
        )
    else:
        return TYPESCRIPT_FUNCTION_TEMPLATE.format(
            jsdoc=jsdoc_str,
            export=export_str,
            name=name,
            type_params=type_params_str,
            params=params_str,
            return_type=return_type_str,
            body=indented_body
        )


def format_javascript_function(
    name: str,
    params: List[str],
    body: str,
    export: bool = False,
    is_async: bool = False,
    jsdoc: Optional[str] = None,
    use_arrow: bool = False
) -> str:
    """Generate a JavaScript function from template.

    Args:
        name: Function name
        params: List of parameter names
        body: Function body (will be indented)
        export: Whether to export the function
        is_async: Whether function is async
        jsdoc: Optional JSDoc comment block
        use_arrow: Use arrow function syntax instead of declaration

    Returns:
        Formatted JavaScript function string
    """
    # Format placeholders
    export_str = "export " if export else ""
    async_str = "async " if is_async else ""

    # Format parameters (no types)
    params_str = ", ".join(params)

    # Format JSDoc
    jsdoc_str = f"{jsdoc}\n" if jsdoc else ""

    # Indent body (2 spaces for JS/TS convention)
    indented_body = "\n".join(f"  {line}" if line.strip() else line
                               for line in body.split("\n"))

    if use_arrow:
        return JAVASCRIPT_ARROW_FUNCTION_TEMPLATE.format(
            jsdoc=jsdoc_str,
            export=export_str,
            name=name,
            **{"async": async_str},
            params=params_str,
            body=indented_body
        )
    elif is_async:
        return JAVASCRIPT_ASYNC_FUNCTION_TEMPLATE.format(
            jsdoc=jsdoc_str,
            export=export_str,
            name=name,
            params=params_str,
            body=indented_body
        )
    else:
        return JAVASCRIPT_FUNCTION_TEMPLATE.format(
            jsdoc=jsdoc_str,
            export=export_str,
            name=name,
            params=params_str,
            body=indented_body
        )


def format_typescript_code(code: str) -> str:
    """Format TypeScript code using prettier-style formatting.

    Uses prettier CLI if available, otherwise falls back to basic formatting rules.
    Applies consistent styling: semicolons, single quotes, trailing commas,
    and 2-space indentation.

    Args:
        code: Raw TypeScript code string to format

    Returns:
        Formatted TypeScript code string
    """
    import shutil
    import tempfile

    logger = get_logger("format.typescript")

    # Try prettier first
    prettier_path = shutil.which("prettier")
    if prettier_path:
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.ts',
                delete=False
            ) as tmp_file:
                tmp_file.write(code)
                tmp_file_path = tmp_file.name

            try:
                result = subprocess.run(
                    [
                        prettier_path,
                        "--parser", "typescript",
                        "--single-quote",
                        "--trailing-comma", "all",
                        "--tab-width", "2",
                        "--semi",
                        tmp_file_path
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0:
                    logger.debug("formatted_with_prettier", code_length=len(code))
                    return result.stdout
                else:
                    logger.warning(
                        "prettier_failed",
                        stderr=result.stderr,
                        returncode=result.returncode
                    )
            finally:
                import os
                os.unlink(tmp_file_path)

        except subprocess.TimeoutExpired:
            logger.warning("prettier_timeout")
        except Exception as e:
            logger.warning("prettier_error", error=str(e))

    # Fallback: basic formatting
    logger.debug("using_basic_formatting", reason="prettier_unavailable")
    lines = code.split('\n')
    formatted_lines = []

    for line in lines:
        if '`' not in line:
            formatted_line = _convert_quotes_to_single(line)
        else:
            formatted_line = line

        stripped = formatted_line.rstrip()
        if stripped and not stripped.endswith(('{', '}', '(', ',', ';', ':', '//')):
            if not stripped.startswith(('if', 'else', 'for', 'while', 'switch', 'try', 'catch', 'finally', '//', '/*', '*')):
                formatted_line = stripped + ';'

        leading_spaces = len(line) - len(line.lstrip())
        if leading_spaces > 0:
            indent_level = leading_spaces // 4 if leading_spaces >= 4 else leading_spaces // 2
            if leading_spaces % 4 == 0:
                indent_level = leading_spaces // 4
            elif leading_spaces % 2 == 0:
                indent_level = leading_spaces // 2
            formatted_line = '  ' * indent_level + formatted_line.lstrip()

        formatted_lines.append(formatted_line)

    return '\n'.join(formatted_lines)


def _convert_quotes_to_single(line: str) -> str:
    """Convert double-quoted strings to single quotes in a line."""
    result = []
    i = 0
    in_string = False
    string_char = None

    while i < len(line):
        char = line[i]
        if not in_string:
            if char == '"':
                result.append("'")
                in_string = True
                string_char = '"'
            elif char == "'":
                result.append(char)
                in_string = True
                string_char = "'"
            else:
                result.append(char)
        else:
            if char == '\\' and i + 1 < len(line):
                next_char = line[i + 1]
                if next_char == string_char:
                    result.append("\\'")
                    i += 1
                else:
                    result.append(char)
            elif char == string_char:
                result.append("'" if string_char == '"' else char)
                in_string = False
                string_char = None
            else:
                result.append(char)
        i += 1

    return ''.join(result)


def identify_varying_literals(
    code1: str,
    code2: str,
    language: str = "python"
) -> List[Dict[str, Any]]:
    """Identify literals that vary between two similar code blocks.

    Uses ast-grep patterns to extract literals from code blocks and compare
    them at corresponding positions. This helps identify parameterizable
    differences when refactoring duplicate code.

    Args:
        code1: First code snippet
        code2: Second code snippet
        language: Programming language for parsing

    Returns:
        List of dicts with keys:
            - position: Line number in the code
            - value1: Literal value from code1
            - value2: Literal value from code2
            - literal_type: Type of literal (string, number, boolean)
    """
    logger = get_logger("duplication.literals")

    varying_literals: List[Dict[str, Any]] = []

    def extract_literals_with_ast_grep(code: str, literal_type: str) -> List[Dict[str, Any]]:
        """Extract literals from code using ast-grep."""
        literals: List[Dict[str, Any]] = []

        # Write code to temp file for ast-grep
        import tempfile
        ext_map = {
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "jsx": ".jsx",
            "tsx": ".tsx",
        }
        ext = ext_map.get(language, ".py")

        with tempfile.NamedTemporaryFile(mode='w', suffix=ext, delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            # Use ast-grep YAML rules to find literals by AST node kind
            if literal_type == "number":
                rule = {
                    "rule": {
                        "any": [
                            {"kind": "integer"},
                            {"kind": "float"},
                            {"kind": "number"},
                        ]
                    }
                }
            elif literal_type == "string":
                rule = {
                    "rule": {
                        "any": [
                            {"kind": "string"},
                            {"kind": "string_literal"},
                        ]
                    }
                }
            elif literal_type == "boolean":
                rule = {
                    "rule": {
                        "any": [
                            {"kind": "true"},
                            {"kind": "false"},
                            {"kind": "none"},
                            {"kind": "null"},
                        ]
                    }
                }
            else:
                return literals

            rule_yaml = yaml.dump(rule)

            result = subprocess.run(
                ["ast-grep", "scan", "--rule", "-", "--json", temp_path],
                input=rule_yaml,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                try:
                    matches = json.loads(result.stdout)
                    for match in matches:
                        line = match.get("range", {}).get("start", {}).get("line", 0)
                        col = match.get("range", {}).get("start", {}).get("column", 0)
                        text = match.get("text", "")
                        literals.append({
                            "line": line,
                            "column": col,
                            "value": text,
                            "type": literal_type
                        })
                except json.JSONDecodeError:
                    logger.warning("literal_parse_error", literal_type=literal_type)

        except subprocess.TimeoutExpired:
            logger.warning("literal_extraction_timeout", literal_type=literal_type)
        except Exception as e:
            logger.error("literal_extraction_error", error=str(e), literal_type=literal_type)
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except Exception:
                pass

        return literals

    # Extract all literals from both code blocks
    for literal_type in ["string", "number", "boolean"]:
        literals1 = extract_literals_with_ast_grep(code1, literal_type)
        literals2 = extract_literals_with_ast_grep(code2, literal_type)

        # Match literals by position (line, column)
        pos_map1: Dict[Tuple[int, int], Dict[str, Any]] = {}
        for lit in literals1:
            key = (lit["line"], lit["column"])
            pos_map1[key] = lit

        pos_map2: Dict[Tuple[int, int], Dict[str, Any]] = {}
        for lit in literals2:
            key = (lit["line"], lit["column"])
            pos_map2[key] = lit

        # Compare literals at same positions
        all_positions = set(pos_map1.keys()) | set(pos_map2.keys())
        for pos in sorted(all_positions):
            lit1 = pos_map1.get(pos)
            lit2 = pos_map2.get(pos)

            if lit1 and lit2 and lit1["value"] != lit2["value"]:
                varying_literals.append({
                    "position": pos[0] + 1,  # Convert to 1-based line number
                    "column": pos[1],
                    "value1": lit1["value"],
                    "value2": lit2["value"],
                    "literal_type": literal_type
                })

    # Sort by position
    varying_literals.sort(key=lambda x: (x["position"], x.get("column", 0)))

    logger.info(
        "varying_literals_found",
        count=len(varying_literals),
        by_type={
            t: len([v for v in varying_literals if v["literal_type"] == t])
            for t in ["string", "number", "boolean"]
        }
    )

    return varying_literals


def analyze_duplicate_group_literals(
    group: List[Dict[str, Any]],
    language: str = "python"
) -> Dict[str, Any]:
    """Analyze a group of duplicates to find all varying literals.

    Compares each pair in the group and aggregates the varying literals
    to identify parameterizable differences for refactoring.

    Args:
        group: List of duplicate code matches (each with 'text' key)
        language: Programming language

    Returns:
        Dict with:
            - total_variations: Count of varying literal positions
            - variations: List of all variations with their values across duplicates
            - suggested_parameters: Suggested parameter names based on patterns
    """
    if len(group) < 2:
        return {
            "total_variations": 0,
            "variations": [],
            "suggested_parameters": []
        }

    # Compare first item against all others to find varying positions
    base_code = group[0].get("text", "")
    all_variations: Dict[Tuple[int, int, str], List[str]] = {}  # (line, col, type) -> [values]

    # Initialize with base values
    for item in group:
        code = item.get("text", "")
        if code == base_code:
            continue

        variations = identify_varying_literals(base_code, code, language)
        for var in variations:
            key = (var["position"], var.get("column", 0), var["literal_type"])
            if key not in all_variations:
                all_variations[key] = [var["value1"]]
            if var["value2"] not in all_variations[key]:
                all_variations[key].append(var["value2"])

    # Format results
    formatted_variations: List[Dict[str, Any]] = []
    suggested_params: List[str] = []

    for (line, col, lit_type), values in sorted(all_variations.items()):
        var_info = {
            "position": line,
            "column": col,
            "literal_type": lit_type,
            "values": values,
            "occurrences": len(values)
        }
        formatted_variations.append(var_info)

        # Suggest parameter name based on type
        param_suffix = len(suggested_params) + 1
        if lit_type == "string":
            suggested_params.append(f"text_{param_suffix}")
        elif lit_type == "number":
            suggested_params.append(f"value_{param_suffix}")
        elif lit_type == "boolean":
            suggested_params.append(f"flag_{param_suffix}")

    return {
        "total_variations": len(formatted_variations),
        "variations": formatted_variations,
        "suggested_parameters": suggested_params
    }


# =============================================================================
# Phase 2: Code Generation Engine - Function Templates
# =============================================================================

@dataclass
class FunctionTemplate:
    """Template for generating extracted functions from duplicate code.

    This dataclass holds all the components needed to generate a function
    that consolidates duplicate code patterns.

    Attributes:
        name: Function name (valid Python identifier)
        parameters: List of tuples (param_name, param_type) for function signature
        body: The function body code (properly indented)
        return_type: Optional return type annotation
        docstring: Optional docstring describing the function
        decorators: Optional list of decorator strings (without @)
    """
    name: str
    parameters: List[Tuple[str, Optional[str]]]
    body: str
    return_type: Optional[str] = None
    docstring: Optional[str] = None
    decorators: Optional[List[str]] = None

    def format_params(self) -> str:
        """Format parameters for function signature.

        Returns:
            Formatted parameter string like 'param1: str, param2: int'
        """
        parts = []
        for param_name, param_type in self.parameters:
            if param_type:
                parts.append(f"{param_name}: {param_type}")
            else:
                parts.append(param_name)
        return ", ".join(parts)

    def format_decorators(self) -> str:
        """Format decorators for placement above function definition.

        Returns:
            Formatted decorator lines with @ prefix, each on own line
        """
        if not self.decorators:
            return ""
        return "\n".join(f"@{dec}" for dec in self.decorators) + "\n"

    def format_return_type(self) -> str:
        """Format return type annotation.

        Returns:
            ' -> Type' if return_type is set, empty string otherwise
        """
        if self.return_type:
            return f" -> {self.return_type}"
        return ""

    def format_docstring(self) -> str:
        """Format docstring with proper indentation.

        Returns:
            Indented docstring with triple quotes, or empty string
        """
        if not self.docstring:
            return ""
        # Format docstring with proper indentation
        lines = self.docstring.split('\n')
        if len(lines) == 1:
            return f'    """{self.docstring}"""\n'
        # Multi-line docstring
        indented_lines = [lines[0]] + [f"    {line}" if line.strip() else "" for line in lines[1:]]
        return f'    """{chr(10).join(indented_lines)}"""\n'

    def generate(self) -> str:
        """Generate the complete function code.

        Returns:
            Complete Python function as a string
        """
        decorators = self.format_decorators()
        params = self.format_params()
        return_annotation = self.format_return_type()
        docstring = self.format_docstring()

        # Ensure body is properly indented (4 spaces)
        body_lines = self.body.split('\n')
        indented_body = '\n'.join(
            f"    {line}" if line.strip() else line
            for line in body_lines
        )

        return f"{decorators}def {self.name}({params}){return_annotation}:\n{docstring}{indented_body}"


# Template string for Python function generation with placeholders
PYTHON_FUNCTION_TEMPLATE = """{decorators}def {name}({params}){return_type}:
{docstring}{body}"""


def render_python_function(
    name: str,
    params: str,
    body: str,
    return_type: Optional[str] = None,
    docstring: Optional[str] = None,
    decorators: Optional[List[str]] = None
) -> str:
    """Render a Python function using the template.

    This is a convenience function for generating Python functions without
    creating a FunctionTemplate instance.

    Args:
        name: Function name
        params: Formatted parameter string (e.g., 'x: int, y: str')
        body: Function body (will be indented if not already)
        return_type: Optional return type (without '-> ')
        docstring: Optional docstring content (without triple quotes)
        decorators: Optional list of decorator names (without @)

    Returns:
        Complete Python function as a string

    Example:
        >>> render_python_function(
        ...     name="add",
        ...     params="a: int, b: int",
        ...     body="return a + b",
        ...     return_type="int",
        ...     docstring="Add two numbers."
        ... )
        'def add(a: int, b: int) -> int:\\n    \"\"\"Add two numbers.\"\"\"\\n    return a + b'
    """
    # Format decorators
    dec_str = ""
    if decorators:
        dec_str = "\n".join(f"@{dec}" for dec in decorators) + "\n"

    # Format return type
    ret_str = f" -> {return_type}" if return_type else ""

    # Format docstring
    doc_str = ""
    if docstring:
        doc_lines = docstring.split('\n')
        if len(doc_lines) == 1:
            doc_str = f'    """{docstring}"""\n'
        else:
            indented = '\n'.join(f"    {line}" if line.strip() else "" for line in doc_lines)
            doc_str = f'    """{indented}"""\n'

    # Indent body if needed
    body_lines = body.split('\n')
    indented_body = '\n'.join(
        f"    {line}" if line.strip() and not line.startswith('    ') else line
        for line in body_lines
    )

    return PYTHON_FUNCTION_TEMPLATE.format(
        decorators=dec_str,
        name=name,
        params=params,
        return_type=ret_str,
        docstring=doc_str,
        body=indented_body
    )


def preserve_call_site_indentation(original_code: str, replacement_call: str) -> str:
    """Preserve the indentation of original code when replacing with a function call.

    Detects the indentation level (tabs or spaces) of the original duplicate code
    and applies the same indentation to the replacement call, handling both
    single-line and multi-line replacements.

    Args:
        original_code: The original duplicate code block being replaced.
            Used to detect the indentation pattern.
        replacement_call: The function call that will replace the duplicate code.
            May be single or multi-line.

    Returns:
        The replacement call with proper indentation applied to all lines.

    Examples:
        >>> preserve_call_site_indentation("    x = 1", "process_data()")
        '    process_data()'

        >>> preserve_call_site_indentation("\\t\\tif True:", "check_condition(\\n    value)")
        '\\t\\tcheck_condition(\\n\\t\\t    value)'

        >>> preserve_call_site_indentation("  result = compute()", "helper(\\n    arg1,\\n    arg2\\n)")
        '  helper(\\n      arg1,\\n      arg2\\n  )'
    """
    if not original_code or not replacement_call:
        return replacement_call

    # Extract leading whitespace from first non-empty line of original code
    indent = ""
    for line in original_code.split('\n'):
        if line.strip():  # First non-empty line
            # Get the leading whitespace (preserves tabs/spaces as-is)
            indent = line[:len(line) - len(line.lstrip())]
            break

    # If no indentation found, return replacement as-is
    if not indent:
        return replacement_call

    # Apply indentation to each line of the replacement
    replacement_lines = replacement_call.split('\n')
    indented_lines = []

    for i, line in enumerate(replacement_lines):
        if i == 0:
            # First line gets the base indentation
            indented_lines.append(indent + line.lstrip() if line.strip() else line)
        else:
            # Subsequent lines: preserve their relative indentation and add base
            if line.strip():
                # Get existing indentation of this line
                existing_indent = line[:len(line) - len(line.lstrip())]
                indented_lines.append(indent + existing_indent + line.lstrip())
            else:
                # Empty lines stay empty
                indented_lines.append(line)

    return '\n'.join(indented_lines)



def detect_import_insertion_point(file_content: str, language: str) -> int:
    """Detect the optimal line number for inserting a new import statement.

    Analyzes the file structure to find where new imports should be added,
    respecting language-specific conventions for import organization.

    Args:
        file_content: The complete content of the source file
        language: Programming language ('python', 'typescript', 'javascript', 'java')

    Returns:
        Line number (1-indexed) where the new import should be inserted.
        Returns 1 if no existing imports are found.

    Examples:
        >>> content = "import os\\nimport sys\\n\\ndef main():\\n    pass"
        >>> detect_import_insertion_point(content, "python")
        3

        >>> content = "package com.example;\\n\\nimport java.util.List;\\n\\npublic class Foo {}"
        >>> detect_import_insertion_point(content, "java")
        4
    """
    if not file_content:
        return 1

    lines = file_content.split('\n')
    language = language.lower()

    if language == "python":
        return _detect_python_import_point(lines)
    elif language in ("typescript", "javascript"):
        return _detect_js_import_point(lines)
    elif language == "java":
        return _detect_java_import_point(lines)
    else:
        # Default: find last import-like line
        return _detect_generic_import_point(lines)


def _detect_python_import_point(lines: List[str]) -> int:
    """Find import insertion point for Python files.

    Handles:
    - Module docstrings at the top
    - __future__ imports (must be first)
    - Regular imports and from imports
    - Blank lines between import groups
    """
    last_import_line = 0
    in_docstring = False
    docstring_delimiter = None

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Track docstrings
        if not in_docstring:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                docstring_delimiter = stripped[:3]
                if stripped.count(docstring_delimiter) >= 2:
                    # Single-line docstring
                    continue
                in_docstring = True
                continue
        else:
            if docstring_delimiter and docstring_delimiter in stripped:
                in_docstring = False
                docstring_delimiter = None
            continue

        # Skip comments and empty lines at the top
        if stripped.startswith('#') or not stripped:
            continue

        # Check for import statements
        if stripped.startswith('import ') or stripped.startswith('from '):
            last_import_line = i
        elif last_import_line > 0:
            # First non-import code after imports
            break

    return last_import_line + 1 if last_import_line > 0 else 1


def _detect_js_import_point(lines: List[str]) -> int:
    """Find import insertion point for TypeScript/JavaScript files.

    Handles:
    - ES6 import statements
    - CommonJS require statements
    - 'use strict' directives
    - Type imports in TypeScript
    """
    last_import_line = 0

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith('//') or stripped.startswith('/*'):
            continue

        # Skip 'use strict' directive
        if stripped in ('"use strict";', "'use strict';"):
            if last_import_line == 0:
                last_import_line = i
            continue

        # Check for import/require statements
        if (stripped.startswith('import ') or
            stripped.startswith('import{') or
            stripped.startswith('import type ') or
            'require(' in stripped and ('const ' in stripped or 'let ' in stripped or 'var ' in stripped)):
            last_import_line = i
        elif last_import_line > 0 and not stripped.startswith('export '):
            # First non-import, non-export code
            # Allow exports at top (TypeScript re-exports)
            if not stripped.startswith('export '):
                break

    return last_import_line + 1 if last_import_line > 0 else 1


def _detect_java_import_point(lines: List[str]) -> int:
    """Find import insertion point for Java files.

    Handles:
    - Package declarations
    - Import statements
    - Static imports
    """
    last_import_line = 0
    found_package = False

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith('//') or stripped.startswith('/*'):
            continue

        # Package declaration
        if stripped.startswith('package '):
            found_package = True
            if last_import_line == 0:
                last_import_line = i
            continue

        # Import statements
        if stripped.startswith('import '):
            last_import_line = i
        elif last_import_line > 0:
            # First non-import code (likely class/interface declaration)
            break

    # If we found a package but no imports, insert after package line
    if found_package and last_import_line > 0:
        return last_import_line + 1

    return last_import_line + 1 if last_import_line > 0 else 1


def _detect_generic_import_point(lines: List[str]) -> int:
    """Generic import detection for unsupported languages.

    Looks for common import patterns across languages.
    """
    last_import_line = 0

    import_patterns = [
        'import ', 'from ', 'require(', 'include ', 'using ',
        '#include', 'use ', 'load '
    ]

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if not stripped:
            continue

        # Check if line contains any import pattern
        if any(stripped.startswith(pattern) or pattern in stripped
               for pattern in import_patterns):
            last_import_line = i
        elif last_import_line > 0:
            break

    return last_import_line + 1 if last_import_line > 0 else 1


# =============================================================================
# Language Formatters - Code Style Formatting
# =============================================================================

def format_python_code(code: str, line_length: int = 88) -> str:
    """Format Python code using black-style formatting.

    Attempts to use the black library for formatting if available.
    Falls back to basic formatting rules when black is not installed.

    Args:
        code: The Python code string to format
        line_length: Maximum line length (default 88, black's default)

    Returns:
        Formatted Python code string

    Examples:
        >>> format_python_code("def foo(a,b,c): return a+b+c")
        'def foo(a, b, c):\\n    return a + b + c\\n'

        >>> format_python_code("import sys,os,re")
        'import os\\nimport re\\nimport sys\\n'
    """
    try:
        # Try to use black if available
        import black
        from black import Mode, TargetVersion

        mode = Mode(
            target_versions={TargetVersion.PY310, TargetVersion.PY311, TargetVersion.PY312},
            line_length=line_length,
            string_normalization=True,
            is_pyi=False,
            magic_trailing_comma=True,
        )

        try:
            formatted: str = black.format_str(code, mode=mode)
            return formatted
        except black.InvalidInput:
            # If black can't parse it, fall back to basic formatting
            pass
    except ImportError:
        # black not available, use basic formatting
        pass

    # Basic formatting fallback
    return _basic_python_format(code, line_length)


def _basic_python_format(code: str, line_length: int = 88) -> str:
    """Basic Python formatting when black is not available.

    Provides minimal formatting including:
    - Sorting and splitting import statements
    - Adding spaces around operators
    - Normalizing whitespace
    - Handling trailing commas in function arguments

    Args:
        code: The Python code string to format
        line_length: Maximum line length for wrapping

    Returns:
        Basically formatted Python code string
    """
    lines = code.split('\n')
    formatted_lines: List[str] = []
    import_lines: List[str] = []
    in_imports = False

    for line in lines:
        stripped = line.strip()

        # Collect imports for sorting
        if stripped.startswith('import ') or stripped.startswith('from '):
            # Handle multi-import statements (import sys, os, re)
            if stripped.startswith('import ') and ',' in stripped:
                # Split into individual imports
                modules = stripped[7:].split(',')
                for module in modules:
                    module = module.strip()
                    if module:
                        import_lines.append(f'import {module}')
            else:
                import_lines.append(stripped)
            in_imports = True
            continue
        elif in_imports and stripped:
            # End of import block, output sorted imports
            in_imports = False
            # Sort imports: standard library style (from imports after regular imports)
            regular_imports = sorted([i for i in import_lines if i.startswith('import ')])
            from_imports = sorted([i for i in import_lines if i.startswith('from ')])
            formatted_lines.extend(regular_imports)
            if regular_imports and from_imports:
                formatted_lines.append('')  # Blank line between import types
            formatted_lines.extend(from_imports)
            if import_lines:
                formatted_lines.append('')  # Blank line after imports
            import_lines = []

        if not in_imports:
            # Basic formatting for non-import lines
            formatted_line = _format_python_line(stripped, line_length)
            # Preserve indentation
            indent = len(line) - len(line.lstrip())
            if formatted_line:
                formatted_lines.append(' ' * indent + formatted_line)
            else:
                formatted_lines.append('')

    # Handle any remaining imports at end of file
    if import_lines:
        regular_imports = sorted([i for i in import_lines if i.startswith('import ')])
        from_imports = sorted([i for i in import_lines if i.startswith('from ')])
        formatted_lines.extend(regular_imports)
        if regular_imports and from_imports:
            formatted_lines.append('')
        formatted_lines.extend(from_imports)

    result = '\n'.join(formatted_lines)

    # Ensure trailing newline
    if result and not result.endswith('\n'):
        result += '\n'

    return result


def _format_python_line(line: str, line_length: int = 88) -> str:
    """Format a single line of Python code.

    Args:
        line: A single line of Python code (stripped)
        line_length: Maximum line length

    Returns:
        Formatted line
    """
    if not line:
        return ''

    # Add spaces around operators
    operators = ['==', '!=', '<=', '>=', '+=', '-=', '*=', '/=', '//=', '%=',
                 '**=', '&=', '|=', '^=', '>>=', '<<=', '->', ':=']
    for op in operators:
        # Don't add spaces if already present
        line = line.replace(f' {op} ', f'__TEMP_OP_{op}__')
        line = line.replace(op, f' {op} ')
        line = line.replace(f'__TEMP_OP_{op}__', f' {op} ')

    # Single-char operators (avoid breaking compound operators)
    for op in ['=', '+', '-', '*', '/', '%', '<', '>', '&', '|', '^']:
        # Skip if part of compound operator
        if f' {op} ' not in line and op in line:
            # Be careful not to break strings or comments
            new_line = ''
            in_string = False
            string_char = ''
            i = 0
            while i < len(line):
                char = line[i]
                if char in '"\'':
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char and (i == 0 or line[i-1] != '\\'):
                        in_string = False

                if not in_string and char == op:
                    # Check it's not part of compound operator
                    prev_char = line[i-1] if i > 0 else ''
                    next_char = line[i+1] if i < len(line) - 1 else ''

                    if prev_char not in '=!<>+-*/%&|^' and next_char not in '=':
                        if prev_char != ' ':
                            new_line += ' '
                        new_line += char
                        if next_char != ' ' and next_char:
                            new_line += ' '
                            i += 1
                            continue

                new_line += char
                i += 1
            line = new_line if new_line else line

    # Format function arguments with trailing commas
    if '(' in line and ')' in line and ',' in line:
        line = _format_function_args(line, line_length)

    # Normalize multiple spaces to single space (except indentation)
    while '  ' in line:
        line = line.replace('  ', ' ')

    return line


def _format_function_args(line: str, line_length: int = 88) -> str:
    """Format function arguments, adding trailing commas for long signatures.

    Args:
        line: Line containing function call or definition
        line_length: Maximum line length

    Returns:
        Formatted line with proper trailing commas
    """
    # Find function call/definition
    paren_start = line.find('(')
    paren_end = line.rfind(')')

    if paren_start == -1 or paren_end == -1 or paren_end <= paren_start:
        return line

    prefix = line[:paren_start + 1]
    args_str = line[paren_start + 1:paren_end]
    suffix = line[paren_end:]

    # Split arguments, respecting nested parens/brackets
    args = _split_function_args(args_str)

    if not args:
        return line

    # Format each argument
    formatted_args = [arg.strip() for arg in args]

    # Check if it fits on one line
    single_line = prefix + ', '.join(formatted_args) + suffix
    if len(single_line) <= line_length:
        return single_line

    # Multi-line format with trailing comma (black style)
    # Note: actual indentation would be handled by the caller
    formatted_args_str = ', '.join(formatted_args)
    if not formatted_args_str.endswith(','):
        formatted_args_str += ','

    return prefix + formatted_args_str + suffix


def _split_function_args(args_str: str) -> List[str]:
    """Split function arguments respecting nested structures.

    Args:
        args_str: The arguments string without outer parentheses

    Returns:
        List of individual arguments
    """
    args: List[str] = []
    current_arg = ''
    depth = 0
    in_string = False
    string_char = ''

    for i, char in enumerate(args_str):
        if char in '"\'':
            if not in_string:
                in_string = True
                string_char = char
            elif char == string_char and (i == 0 or args_str[i-1] != '\\'):
                in_string = False

        if not in_string:
            if char in '([{':
                depth += 1
            elif char in ')]}':
                depth -= 1
            elif char == ',' and depth == 0:
                args.append(current_arg)
                current_arg = ''
                continue

        current_arg += char

    if current_arg.strip():
        args.append(current_arg)

    return args


# =============================================================================
# Complex Parameter Type Inference for Extracted Functions
# =============================================================================

class ParameterType:
    """Represents an inferred type for an extracted parameter."""

    def __init__(
        self,
        name: str,
        python_type: str,
        typescript_type: str,
        is_generic: bool = False,
        is_union: bool = False,
        inner_types: Optional[List["ParameterType"]] = None
    ):
        self.name = name
        self.python_type = python_type
        self.typescript_type = typescript_type
        self.is_generic = is_generic
        self.is_union = is_union
        self.inner_types = inner_types or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "name": self.name,
            "python_type": self.python_type,
            "typescript_type": self.typescript_type,
            "is_generic": self.is_generic,
            "is_union": self.is_union,
        }
        if self.inner_types:
            result["inner_types"] = [t.to_dict() for t in self.inner_types]
        return result


def infer_parameter_type(
    values: List[str],
    language: str = "python"
) -> ParameterType:
    """Infer the type of a parameter from multiple values across variations.

    Analyzes values from different duplicate code instances to determine
    the most appropriate type for an extracted function parameter.

    Args:
        values: List of values this parameter takes across variations
        language: Programming language context

    Returns:
        ParameterType with inferred Python and TypeScript type hints
    """
    logger = get_logger("duplication.type_inference")

    if not values:
        return ParameterType("unknown", "Any", "any")

    # Infer types for each value
    inferred_types: List[Dict[str, str]] = []
    for value in values:
        inferred = _infer_single_value_type(value, language)
        inferred_types.append(inferred)

    # Check if all types are the same
    unique_types = list({t["python_type"] for t in inferred_types})

    if len(unique_types) == 1:
        # Single type - use it directly
        base_type = inferred_types[0]
        return ParameterType(
            name=base_type.get("name", "param"),
            python_type=base_type["python_type"],
            typescript_type=base_type["typescript_type"],
            is_generic=bool(base_type.get("is_generic", False)),
            is_union=False
        )
    else:
        # Multiple types - create union type
        python_union = " | ".join(sorted(unique_types))
        ts_types = list({t["typescript_type"] for t in inferred_types})
        typescript_union = " | ".join(sorted(ts_types))

        logger.debug(
            "union_type_inferred",
            types=unique_types,
            python_union=python_union
        )

        return ParameterType(
            name="param",
            python_type=python_union,
            typescript_type=typescript_union,
            is_generic=False,
            is_union=True
        )


# =============================================================================
# Nested Function Call Detection and Parameter Extraction
# =============================================================================

def _detect_nested_function_call(value: str, language: str) -> Optional[Dict[str, Any]]:
    """Detect and analyze nested function calls for parameter extraction.

    Handles patterns like:
    - process(get_user(id)) vs process(get_product(id))
    - outer(middle(inner(x))) - multiple nesting levels
    - transform(fetch_data(config))

    Args:
        value: The code string to analyze
        language: Programming language context

    Returns:
        Dict with type info if nested call detected, None otherwise
    """
    import re

    # Check for nested call pattern: func1(func2(...))
    nested_pattern = r'^(\w+)\s*\(\s*(\w+)\s*\([^)]*\)\s*\)$'
    match = re.match(nested_pattern, value.strip())

    if not match:
        # Check for deeper nesting: func1(func2(func3(...)))
        deep_nested = _parse_nested_calls(value.strip())
        if deep_nested and len(deep_nested) >= 2:
            return _infer_nested_call_type(deep_nested, language)
        return None

    outer_func = match.group(1)
    inner_func = match.group(2)

    # Infer type based on the nested call structure
    return _infer_nested_call_type([outer_func, inner_func], language)


def _parse_nested_calls(value: str) -> Optional[List[str]]:
    """Parse nested function calls and return list of function names.

    Args:
        value: Code string like "outer(middle(inner(x)))"

    Returns:
        List of function names from outermost to innermost, or None if not a nested call
    """
    import re

    functions: List[str] = []
    remaining = value.strip()

    while remaining:
        # Match function name followed by opening paren
        func_match = re.match(r'^(\w+)\s*\(', remaining)
        if not func_match:
            break

        func_name = func_match.group(1)
        functions.append(func_name)

        # Move past the function name and opening paren
        remaining = remaining[func_match.end():].strip()

        # Check if the rest is another function call or just arguments
        if not re.match(r'^\w+\s*\(', remaining):
            break

    # Verify structure is valid (has matching parens)
    if len(functions) >= 2:
        paren_count = value.count('(')
        close_count = value.count(')')
        if paren_count == close_count and paren_count == len(functions):
            return functions

    return None if len(functions) < 2 else functions


def _infer_nested_call_type(func_names: List[str], language: str) -> Dict[str, Any]:
    """Infer the type for a nested function call based on function names.

    Args:
        func_names: List of function names from outermost to innermost
        language: Programming language context

    Returns:
        Dict with python_type, typescript_type, name, and callable metadata
    """
    if not func_names:
        return {"python_type": "Any", "typescript_type": "any", "name": "nested_call", "is_generic": False}

    outer_func = func_names[0]
    inner_func = func_names[-1] if len(func_names) > 1 else func_names[0]

    # Generate parameter name based on inner function (the varying part)
    param_name = _generate_nested_call_param_name(inner_func)

    # Determine type based on common patterns
    callable_type = _infer_callable_type_from_name(inner_func, language)

    nesting_depth = len(func_names)

    return {
        "python_type": callable_type["python_type"],
        "typescript_type": callable_type["typescript_type"],
        "name": param_name,
        "is_generic": False,
        "is_nested_call": True,
        "nesting_depth": nesting_depth,
        "outer_function": outer_func,
        "inner_function": inner_func,
        "all_functions": func_names
    }


def _generate_nested_call_param_name(func_name: str) -> str:
    """Generate a parameter name for a nested function call.

    Extracts meaningful name from function like:
    - get_user -> user_getter
    - fetch_data -> data_fetcher
    - process_items -> items_processor

    Args:
        func_name: The function name to derive parameter name from

    Returns:
        Suggested parameter name
    """
    import re

    # Common prefixes that indicate the action
    action_prefixes = {
        "get_": "_getter",
        "fetch_": "_fetcher",
        "load_": "_loader",
        "read_": "_reader",
        "find_": "_finder",
        "create_": "_creator",
        "build_": "_builder",
        "make_": "_maker",
        "process_": "_processor",
        "transform_": "_transformer",
        "convert_": "_converter",
        "parse_": "_parser",
        "validate_": "_validator",
        "compute_": "_computer",
        "calculate_": "_calculator",
    }

    lower_name = func_name.lower()

    for prefix, suffix in action_prefixes.items():
        if lower_name.startswith(prefix):
            base = lower_name[len(prefix):]
            if base:
                return f"{base}{suffix}"

    # Handle camelCase (e.g., getUser -> user_getter)
    camel_match = re.match(r'^(get|fetch|load|find|create|build|process)([A-Z]\w*)', func_name)
    if camel_match:
        action = camel_match.group(1).lower()
        noun = camel_match.group(2)
        # Convert to snake_case
        snake_noun = re.sub(r'(?<!^)(?=[A-Z])', '_', noun).lower()
        suffix_map = {
            "get": "_getter", "fetch": "_fetcher", "load": "_loader",
            "find": "_finder", "create": "_creator", "build": "_builder",
            "process": "_processor"
        }
        return f"{snake_noun}{suffix_map.get(action, '_func')}"

    # Default: use function name + _func
    return f"{func_name}_func"


def _infer_callable_type_from_name(func_name: str, language: str) -> Dict[str, str]:
    """Infer the return type of a callable based on its name.

    Args:
        func_name: Name of the function
        language: Programming language context

    Returns:
        Dict with python_type and typescript_type
    """
    lower_name = func_name.lower()

    # Patterns that suggest specific return types
    type_patterns = {
        # Functions returning collections
        ("list", "all", "many", "items", "batch"):
            {"python_type": "Callable[..., List[Any]]", "typescript_type": "(...args: any[]) => any[]"},
        # Functions returning single items
        ("get", "find", "fetch", "load", "read", "one", "single", "first"):
            {"python_type": "Callable[..., Any]", "typescript_type": "(...args: any[]) => any"},
        # Functions returning booleans
        ("is", "has", "check", "validate", "verify", "can", "should"):
            {"python_type": "Callable[..., bool]", "typescript_type": "(...args: any[]) => boolean"},
        # Functions returning numbers
        ("count", "sum", "total", "calculate", "compute"):
            {"python_type": "Callable[..., int]", "typescript_type": "(...args: any[]) => number"},
        # Functions returning strings
        ("format", "stringify", "serialize", "encode", "to_string"):
            {"python_type": "Callable[..., str]", "typescript_type": "(...args: any[]) => string"},
        # Functions returning dicts/objects
        ("to_dict", "to_json", "as_dict", "to_object"):
            {"python_type": "Callable[..., Dict[str, Any]]", "typescript_type": "(...args: any[]) => Record<string, any>"},
    }

    for patterns, types in type_patterns.items():
        if any(p in lower_name for p in patterns):
            return types

    # Default callable type
    return {"python_type": "Callable[..., Any]", "typescript_type": "(...args: any[]) => any"}


def extract_nested_call_variations(
    code_samples: List[str],
    language: str = "python"
) -> List[Dict[str, Any]]:
    """Extract varying nested function calls from duplicate code samples.

    Compares code samples to identify where nested function calls differ,
    useful for parameterizing duplicates like:
    - process(get_user(id))
    - process(get_product(id))

    Args:
        code_samples: List of code strings from duplicate instances
        language: Programming language

    Returns:
        List of dicts describing the varying nested calls with:
        - position: line/column of the variation
        - variations: list of (outer_func, inner_func) tuples
        - suggested_param_name: suggested parameter name
        - callable_type: inferred type for the callable parameter
    """
    import re

    if len(code_samples) < 2:
        return []

    logger = get_logger("duplication.nested_calls")
    variations: List[Dict[str, Any]] = []

    # Pattern to match function calls with arguments
    call_pattern = r'(\w+)\s*\(\s*(\w+)\s*\([^)]*\)\s*\)'

    # Find all nested calls in each sample
    sample_calls: List[List[Dict[str, Any]]] = []
    for i, code in enumerate(code_samples):
        calls = []
        for match in re.finditer(call_pattern, code):
            calls.append({
                "outer": match.group(1),
                "inner": match.group(2),
                "start": match.start(),
                "end": match.end(),
                "full_match": match.group(0)
            })
        sample_calls.append(calls)

    if not sample_calls or not sample_calls[0]:
        return []

    # Compare calls at same positions across samples
    base_calls = sample_calls[0]

    for idx, base_call in enumerate(base_calls):
        varying_inners: List[str] = [base_call["inner"]]
        is_varying = False

        for sample_idx in range(1, len(sample_calls)):
            if idx < len(sample_calls[sample_idx]):
                other_call = sample_calls[sample_idx][idx]
                # Same outer function but different inner function
                if (other_call["outer"] == base_call["outer"] and
                    other_call["inner"] != base_call["inner"]):
                    is_varying = True
                    if other_call["inner"] not in varying_inners:
                        varying_inners.append(other_call["inner"])

        if is_varying:
            # Generate parameter info for this variation
            param_name = _generate_nested_call_param_name(base_call["inner"])
            callable_type = _infer_callable_type_from_name(base_call["inner"], language)

            variations.append({
                "position": base_call["start"],
                "outer_function": base_call["outer"],
                "varying_inner_functions": varying_inners,
                "suggested_param_name": param_name,
                "callable_type": callable_type,
                "occurrences": len(varying_inners)
            })

    logger.info(
        "nested_call_variations_found",
        count=len(variations),
        total_inner_variations=sum(v["occurrences"] for v in variations)
    )

    return variations


def _infer_single_value_type(value: str, language: str) -> Dict[str, Any]:
    """Infer the type of a single value."""
    value = value.strip()

    if value.lower() in ("none", "null", "nil"):
        return {"python_type": "None", "typescript_type": "null", "name": "value", "is_generic": False}

    if value.lower() in ("true", "false"):
        return {"python_type": "bool", "typescript_type": "boolean", "name": "flag", "is_generic": False}

    if _is_numeric(value):
        if "." in value or "e" in value.lower():
            return {"python_type": "float", "typescript_type": "number", "name": "value", "is_generic": False}
        return {"python_type": "int", "typescript_type": "number", "name": "count", "is_generic": False}

    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return {"python_type": "str", "typescript_type": "string", "name": "text", "is_generic": False}

    if value.startswith("[") and value.endswith("]"):
        inner_type = _infer_collection_inner_type(value, "list", language)
        return {
            "python_type": f"List[{inner_type['python_type']}]",
            "typescript_type": f"{inner_type['typescript_type']}[]",
            "name": "items", "is_generic": True
        }

    if value.startswith("{") and value.endswith("}"):
        if ":" in value or "=>" in value:
            key_type, val_type = _infer_dict_types(value, language)
            return {
                "python_type": f"Dict[{key_type['python_type']}, {val_type['python_type']}]",
                "typescript_type": f"Record<{key_type['typescript_type']}, {val_type['typescript_type']}>",
                "name": "mapping", "is_generic": True
            }
        return {"python_type": "Set[Any]", "typescript_type": "Set<any>", "name": "items", "is_generic": True}

    if value.startswith("(") and value.endswith(")") and "," in value:
        return {"python_type": "Tuple[Any, ...]", "typescript_type": "[any, ...any[]]", "name": "tuple_val", "is_generic": True}

    if "lambda" in value or "=>" in value:
        return {"python_type": "Callable[..., Any]", "typescript_type": "(...args: any[]) => any", "name": "callback", "is_generic": False}

    # Check for nested function calls (e.g., process(get_user(id)))
    nested_call_info = _detect_nested_function_call(value, language)
    if nested_call_info:
        return nested_call_info

    if "(" in value and ")" in value and not value.startswith("("):
        func_name = value.split("(")[0].strip()
        if func_name and func_name[0].islower():
            return {"python_type": "Callable[..., Any]", "typescript_type": "(...args: any[]) => any", "name": "func", "is_generic": False}

    if "(" in value and value.split("(")[0].strip()[0:1].isupper():
        class_name = value.split("(")[0].strip()
        return {"python_type": class_name, "typescript_type": class_name, "name": "instance", "is_generic": False}

    generic_match = _parse_generic_type(value)
    if generic_match:
        return generic_match

    if value.isidentifier() or (value.replace("_", "").isalnum() and value[0].isalpha()):
        return _infer_from_identifier_name(value)

    return {"python_type": "Any", "typescript_type": "any", "name": "value", "is_generic": False}


def _is_numeric(value: str) -> bool:
    """Check if a value string represents a number."""
    try:
        cleaned = value.lstrip("-+")
        if not cleaned:
            return False
        if cleaned.startswith(("0x", "0o", "0b")):
            return True
        float(value)
        return True
    except ValueError:
        return False


def _infer_collection_inner_type(value: str, collection_type: str, language: str) -> Dict[str, str]:
    """Infer the inner type of a collection from its contents."""
    inner = value[1:-1].strip()
    if not inner:
        return {"python_type": "Any", "typescript_type": "any"}

    elements = _split_collection_elements(inner)
    if not elements:
        return {"python_type": "Any", "typescript_type": "any"}

    element_types = [_infer_single_value_type(elem.strip(), language) for elem in elements]
    unique_python = list({t["python_type"] for t in element_types})
    unique_ts = list({t["typescript_type"] for t in element_types})

    if len(unique_python) == 1:
        return {"python_type": unique_python[0], "typescript_type": unique_ts[0]}

    return {
        "python_type": " | ".join(sorted(unique_python)),
        "typescript_type": " | ".join(sorted(unique_ts))
    }


def _split_collection_elements(inner: str) -> List[str]:
    """Split collection inner content by commas, respecting nesting."""
    elements = []
    current = ""
    depth = 0

    for char in inner:
        if char in "([{":
            depth += 1
            current += char
        elif char in ")]}":
            depth -= 1
            current += char
        elif char == "," and depth == 0:
            elements.append(current.strip())
            current = ""
        else:
            current += char

    if current.strip():
        elements.append(current.strip())

    return elements


def _infer_dict_types(value: str, language: str) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Infer key and value types for a dictionary literal."""
    inner = value[1:-1].strip()
    if not inner:
        return ({"python_type": "Any", "typescript_type": "any"}, {"python_type": "Any", "typescript_type": "any"})

    pairs = _split_collection_elements(inner)
    key_types = []
    val_types = []

    for pair in pairs:
        if ":" in pair:
            key, val = pair.split(":", 1)
        elif "=>" in pair:
            key, val = pair.split("=>", 1)
        else:
            continue
        key_types.append(_infer_single_value_type(key.strip(), language))
        val_types.append(_infer_single_value_type(val.strip(), language))

    if not key_types:
        return ({"python_type": "Any", "typescript_type": "any"}, {"python_type": "Any", "typescript_type": "any"})

    unique_key_py = list({t["python_type"] for t in key_types})
    unique_key_ts = list({t["typescript_type"] for t in key_types})
    unique_val_py = list({t["python_type"] for t in val_types})
    unique_val_ts = list({t["typescript_type"] for t in val_types})

    return (
        {"python_type": unique_key_py[0] if len(unique_key_py) == 1 else " | ".join(sorted(unique_key_py)),
         "typescript_type": unique_key_ts[0] if len(unique_key_ts) == 1 else " | ".join(sorted(unique_key_ts))},
        {"python_type": unique_val_py[0] if len(unique_val_py) == 1 else " | ".join(sorted(unique_val_py)),
         "typescript_type": unique_val_ts[0] if len(unique_val_ts) == 1 else " | ".join(sorted(unique_val_ts))}
    )


def _parse_generic_type(value: str) -> Optional[Dict[str, Any]]:
    """Parse explicit generic type annotations like List[str], Dict[str, int]."""
    import re
    generic_pattern = r'^(\w+)\[(.+)\]$'
    match = re.match(generic_pattern, value.strip())
    if not match:
        return None

    container = match.group(1)
    inner = match.group(2)

    type_mapping = {
        "List": (f"List[{inner}]", f"Array<{_py_to_ts_type(inner)}>"),
        "Dict": (f"Dict[{inner}]", f"Record<{_py_to_ts_type(inner)}>"),
        "Set": (f"Set[{inner}]", f"Set<{_py_to_ts_type(inner)}>"),
        "Tuple": (f"Tuple[{inner}]", f"[{_py_to_ts_type(inner)}]"),
        "Optional": (f"Optional[{inner}]", f"{_py_to_ts_type(inner)} | null"),
        "Callable": (f"Callable[{inner}]", f"(...args: any[]) => {_py_to_ts_type(inner.split(',')[-1].strip() if ',' in inner else 'any')}"),
        "Sequence": (f"Sequence[{inner}]", f"Array<{_py_to_ts_type(inner)}>"),
        "Mapping": (f"Mapping[{inner}]", f"Record<{_py_to_ts_type(inner)}>"),
        "Iterable": (f"Iterable[{inner}]", f"Iterable<{_py_to_ts_type(inner)}>"),
    }

    if container in type_mapping:
        py_type, ts_type = type_mapping[container]
        return {"python_type": py_type, "typescript_type": ts_type, "name": _suggest_param_name_from_type(container), "is_generic": True}

    return {"python_type": value, "typescript_type": value, "name": "value", "is_generic": True}


def _py_to_ts_type(py_type: str) -> str:
    """Convert a Python type to TypeScript equivalent."""
    mapping = {"str": "string", "int": "number", "float": "number", "bool": "boolean", "None": "null", "Any": "any", "object": "object", "bytes": "Uint8Array"}
    return mapping.get(py_type.strip(), py_type.strip())


def _suggest_param_name_from_type(type_name: str) -> str:
    """Suggest a parameter name based on its type."""
    name_mapping = {"List": "items", "Dict": "mapping", "Set": "unique_items", "Tuple": "values", "Optional": "value", "Callable": "callback", "Sequence": "sequence", "Mapping": "mapping", "Iterable": "iterable"}
    return name_mapping.get(type_name, "value")


def _infer_from_identifier_name(identifier: str) -> Dict[str, Any]:
    """Infer type from identifier naming conventions."""
    lower_id = identifier.lower()

    if any(prefix in lower_id for prefix in ["is_", "has_", "should_", "can_", "will_", "did_"]):
        return {"python_type": "bool", "typescript_type": "boolean", "name": identifier, "is_generic": False}

    if any(suffix in lower_id for suffix in ["_list", "_items", "_array", "s"]) and not lower_id.endswith("ss"):
        return {"python_type": "List[Any]", "typescript_type": "any[]", "name": identifier, "is_generic": True}

    if any(suffix in lower_id for suffix in ["_dict", "_map", "_mapping"]):
        return {"python_type": "Dict[str, Any]", "typescript_type": "Record<string, any>", "name": identifier, "is_generic": True}

    if any(suffix in lower_id for suffix in ["_set"]):
        return {"python_type": "Set[Any]", "typescript_type": "Set<any>", "name": identifier, "is_generic": True}

    if any(part in lower_id for part in ["callback", "handler", "func", "fn", "action"]):
        return {"python_type": "Callable[..., Any]", "typescript_type": "(...args: any[]) => any", "name": identifier, "is_generic": False}

    if any(part in lower_id for part in ["count", "num", "index", "size", "length", "total", "id"]):
        return {"python_type": "int", "typescript_type": "number", "name": identifier, "is_generic": False}

    if any(part in lower_id for part in ["name", "text", "str", "msg", "message", "path", "url", "key"]):
        return {"python_type": "str", "typescript_type": "string", "name": identifier, "is_generic": False}

    return {"python_type": "Any", "typescript_type": "any", "name": identifier, "is_generic": False}


def infer_extracted_function_parameters(
    varying_identifiers: List[Dict[str, Any]],
    code_samples: List[str],
    language: str = "python"
) -> List[Dict[str, Any]]:
    """Infer parameter types for an extracted function from duplicate code variations.

    Args:
        varying_identifiers: List of varying identifier dicts from identify_varying_identifiers
        code_samples: List of code strings from duplicate instances
        language: Target language for type hints

    Returns:
        List of parameter definitions with name, python_type, typescript_type, values, is_union, is_generic
    """
    logger = get_logger("duplication.parameter_inference")
    param_values: Dict[str, List[str]] = {}

    for var_id in varying_identifiers:
        base_name = var_id.get("identifier1", "param")
        if base_name not in param_values:
            param_values[base_name] = []
        param_values[base_name].append(var_id.get("identifier1", ""))
        param_values[base_name].append(var_id.get("identifier2", ""))

    parameters: List[Dict[str, Any]] = []

    for param_name, values in param_values.items():
        unique_values = []
        seen = set()
        for v in values:
            if v and v not in seen:
                unique_values.append(v)
                seen.add(v)

        if not unique_values:
            continue

        param_type = infer_parameter_type(unique_values, language)
        clean_name = _generate_parameter_name(param_name, param_type)

        parameters.append({
            "name": clean_name,
            "python_type": param_type.python_type,
            "typescript_type": param_type.typescript_type,
            "values": unique_values[:5],
            "is_union": param_type.is_union,
            "is_generic": param_type.is_generic
        })

    logger.info("parameters_inferred", parameter_count=len(parameters),
                union_types=sum(1 for p in parameters if p["is_union"]),
                generic_types=sum(1 for p in parameters if p["is_generic"]))

    return parameters


def _generate_parameter_name(original_name: str, param_type: ParameterType) -> str:
    """Generate a clean parameter name."""
    import re
    if original_name and re.match(r'^[a-z_][a-z0-9_]*$', original_name, re.IGNORECASE):
        return original_name.lower()
    type_name = param_type.name
    if type_name and re.match(r'^[a-z_][a-z0-9_]*$', type_name, re.IGNORECASE):
        return type_name.lower()
    return "param"


def generate_simple_function_signature(
    function_name: str,
    parameters: List[Dict[str, Any]],
    return_type: str = "None",
    language: str = "python"
) -> str:
    """Generate a simple function signature with inferred parameter types."""
    if language == "python":
        params = [f"{p['name']}: {p['python_type']}" for p in parameters]
        param_str = ", ".join(params)
        return f"def {function_name}({param_str}) -> {return_type}:"

    elif language in ("typescript", "javascript"):
        params = [f"{p['name']}: {p['typescript_type']}" for p in parameters]
        param_str = ", ".join(params)
        ts_return = _py_to_ts_type(return_type) if return_type != "None" else "void"
        return f"function {function_name}({param_str}): {ts_return}"

    else:
        param_str = ", ".join(p["name"] for p in parameters)
        return f"{function_name}({param_str})"


def generate_function_body(
    sample_code: str,
    parameters: List["ParameterInfo"],
    language: str = "python"
) -> str:
    """Generate function body by transforming sample code to use parameters.

    Takes sample duplicate code and replaces hardcoded literal values with
    parameter references based on the provided parameter information.

    Args:
        sample_code: The sample code to transform into a function body
        parameters: List of ParameterInfo objects with values to replace
        language: Target language for indentation (python, javascript, typescript, java)

    Returns:
        Transformed code with proper indentation and parameter substitutions

    Example:
        >>> params = [ParameterInfo("name", default_value='"John"')]
        >>> sample = 'print("Hello, John")'
        >>> generate_function_body(sample, params, "python")
        '    print(f"Hello, {name}")'
    """
    # Determine indentation based on language
    if language in ("python", "java"):
        indent = "    "  # 4 spaces
    else:  # javascript, typescript
        indent = "  "  # 2 spaces

    # Start with the sample code
    body = sample_code

    # Build mapping of literal values to parameter names
    replacements: List[tuple[str, str, str]] = []  # (literal, param_name, param_type)

    for param in parameters:
        if param.default_value is not None:
            literal = param.default_value
            param_name = param.name

            # Determine type for proper replacement syntax
            if language == "python":
                param_type = param.python_type
            elif language in ("typescript", "javascript"):
                param_type = param.typescript_type
            else:
                param_type = param.java_type

            replacements.append((literal, param_name, param_type))

    # Sort replacements by length (longest first) to avoid partial replacements
    replacements.sort(key=lambda x: len(x[0]), reverse=True)

    # Apply replacements
    for literal, param_name, param_type in replacements:
        if not literal:
            continue

        # Handle string literals
        if (literal.startswith('"') and literal.endswith('"')) or \
           (literal.startswith("'") and literal.endswith("'")):

            inner_value = literal[1:-1]  # Remove quotes
            quote_char = literal[0]

            if language == "python":
                # Replace string in f-string format or direct substitution
                # Try to replace within existing strings first
                body = body.replace(inner_value, f"{{{param_name}}}")
                # Also replace the full literal with the parameter
                body = body.replace(literal, param_name)

            elif language in ("typescript", "javascript"):
                # Use template literals
                body = body.replace(inner_value, f"${{{param_name}}}")
                body = body.replace(literal, param_name)

            else:  # java
                # Use string concatenation
                body = body.replace(literal, param_name)
        else:
            # Numeric or other literals - direct replacement
            body = body.replace(literal, param_name)

    # Handle multi-line code blocks - indent each line
    lines = body.split('\n')
    indented_lines = []

    for line in lines:
        if line.strip():  # Non-empty line
            # Preserve existing indentation relative to base
            stripped = line.lstrip()
            existing_indent = len(line) - len(stripped)

            # Add function body indentation plus any existing indentation
            if existing_indent > 0:
                # Convert existing indentation to consistent format
                relative_indent = " " * existing_indent
                indented_lines.append(indent + relative_indent + stripped)
            else:
                indented_lines.append(indent + stripped)
        else:
            # Empty line - preserve it
            indented_lines.append("")

    return '\n'.join(indented_lines)


# =============================================================================
# Phase 2: Code Generation Engine - Template Variable Substitution
# =============================================================================

class ParameterInfo:
    """Represents a parameter for code generation with type information."""

    def __init__(
        self,
        name: str,
        python_type: str = "Any",
        typescript_type: str = "any",
        java_type: str = "Object",
        default_value: Optional[str] = None,
        is_optional: bool = False,
        description: str = ""
    ):
        self.name = name
        self.python_type = python_type
        self.typescript_type = typescript_type
        self.java_type = java_type
        self.default_value = default_value
        self.is_optional = is_optional
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "python_type": self.python_type,
            "typescript_type": self.typescript_type,
            "java_type": self.java_type,
            "default_value": self.default_value,
            "is_optional": self.is_optional,
            "description": self.description
        }


def format_python_params(params: List[ParameterInfo]) -> str:
    """Format parameters for Python function signature.

    Args:
        params: List of ParameterInfo objects

    Returns:
        Formatted parameter string like "name: str, age: int = 0"
    """
    if not params:
        return ""

    formatted = []
    # Sort to put required params first, then optional
    required = [p for p in params if not p.is_optional]
    optional = [p for p in params if p.is_optional]

    for param in required:
        formatted.append(f"{param.name}: {param.python_type}")

    for param in optional:
        if param.default_value is not None:
            formatted.append(f"{param.name}: {param.python_type} = {param.default_value}")
        else:
            formatted.append(f"{param.name}: Optional[{param.python_type}] = None")

    return ", ".join(formatted)


def format_typescript_params(params: List[ParameterInfo]) -> str:
    """Format parameters for TypeScript function signature.

    Args:
        params: List of ParameterInfo objects

    Returns:
        Formatted parameter string like "name: string, age?: number"
    """
    if not params:
        return ""

    formatted = []
    # Sort to put required params first, then optional
    required = [p for p in params if not p.is_optional]
    optional = [p for p in params if p.is_optional]

    for param in required:
        formatted.append(f"{param.name}: {param.typescript_type}")

    for param in optional:
        if param.default_value is not None:
            formatted.append(f"{param.name}: {param.typescript_type} = {param.default_value}")
        else:
            formatted.append(f"{param.name}?: {param.typescript_type}")

    return ", ".join(formatted)


def format_javascript_code(code: str) -> str:
    """Format JavaScript code using prettier with babel parser.

    Attempts to use prettier for formatting JavaScript code. Falls back to
    basic indentation-preserving formatting if prettier is not available.

    Args:
        code: JavaScript code string to format

    Returns:
        Formatted JavaScript code string

    Examples:
        >>> format_javascript_code("const x=1;function foo(){return x}")
        'const x = 1;\\nfunction foo() {\\n  return x;\\n}'
    """
    import shutil

    # Try prettier first
    prettier_path = shutil.which("prettier")
    if prettier_path:
        try:
            result = subprocess.run(
                [prettier_path, "--parser", "babel", "--stdin-filepath", "input.js"],
                input=code,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.rstrip()
        except (subprocess.TimeoutExpired, OSError):
            pass  # Fall through to basic formatting

    # Basic fallback formatting
    # Add newlines after semicolons and braces for readability
    formatted = code

    # Add spaces around operators
    for op in ["=", "===", "!==", "==", "!=", ">=", "<=", "=>", "&&", "||"]:
        formatted = formatted.replace(op, f" {op} ")

    # Clean up multiple spaces
    while "  " in formatted:
        formatted = formatted.replace("  ", " ")

    # Add newlines after statement terminators (basic heuristic)
    formatted = formatted.replace(";", ";\n")
    formatted = formatted.replace("{", " {\n")
    formatted = formatted.replace("}", "\n}\n")

    # Clean up multiple newlines
    while "\n\n\n" in formatted:
        formatted = formatted.replace("\n\n\n", "\n\n")

    return formatted.strip()


def format_java_params(params: List[ParameterInfo]) -> str:
    """Format parameters for Java method signature.

    Args:
        params: List of ParameterInfo objects

    Returns:
        Formatted parameter string like "String name, int age"
    """
    if not params:
        return ""

    formatted = []
    for param in params:
        # Java doesn't support default params natively, but we can add @Nullable
        if param.is_optional:
            formatted.append(f"@Nullable {param.java_type} {param.name}")
        else:
            formatted.append(f"{param.java_type} {param.name}")

    return ", ".join(formatted)


def format_js_destructuring_args(
    parameters: List[ParameterInfo],
    values: List[str]
) -> str:
    """Generate JavaScript object destructuring pattern from parameters and values.

    Creates object destructuring syntax for JavaScript/TypeScript function calls,
    supporting default values, renamed properties, and nested destructuring.

    Args:
        parameters: List of ParameterInfo objects describing the parameters
        values: List of argument values corresponding to each parameter

    Returns:
        Formatted destructuring pattern like "{ name, age = 0 }" or
        "{ name: userName, config: { timeout } }"

    Examples:
        Basic destructuring:
        >>> params = [ParameterInfo("name"), ParameterInfo("age")]
        >>> format_js_destructuring_args(params, ['"Alice"', "25"])
        '{ name, age }'

        With default values:
        >>> params = [ParameterInfo("name"), ParameterInfo("age", default_value="0")]
        >>> format_js_destructuring_args(params, ['"Alice"', ""])
        '{ name, age = 0 }'

        With renamed properties (value contains ":"):
        >>> params = [ParameterInfo("name")]
        >>> format_js_destructuring_args(params, ["userName"])
        '{ name: userName }'

        With nested destructuring (value contains "{"):
        >>> params = [ParameterInfo("config")]
        >>> format_js_destructuring_args(params, ["{ timeout, retries }"])
        '{ config: { timeout, retries } }'
    """
    if not parameters:
        return "{ }"

    destructured = []

    for i, param in enumerate(parameters):
        value = values[i] if i < len(values) else ""

        # Handle nested destructuring (value contains curly braces)
        if value and value.strip().startswith("{"):
            destructured.append(f"{param.name}: {value.strip()}")
        # Handle renamed properties (value is a simple identifier, not a literal)
        elif value and not value.startswith('"') and not value.startswith("'") and not value.isdigit() and value != param.name:
            # Check if it's a valid identifier (not a complex expression)
            if value.replace("_", "").replace("$", "").isalnum() or value.isidentifier():
                destructured.append(f"{param.name}: {value}")
            else:
                # Complex expression - just use the parameter name
                destructured.append(param.name)
        # Handle default values
        elif not value and param.default_value:
            destructured.append(f"{param.name} = {param.default_value}")
        # Handle empty value with no default
        elif not value:
            destructured.append(param.name)
        # Simple case - just the parameter name
        else:
            destructured.append(param.name)

    return "{ " + ", ".join(destructured) + " }"


def generate_docstring(
    description: str,
    parameters: List[ParameterInfo],
    return_type: Optional[str],
    language: str
) -> str:
    """Generate documentation string for a function in the target language format.

    Creates properly formatted documentation based on the language:
    - Python: Google-style docstring with Args and Returns sections
    - TypeScript/JavaScript: JSDoc with @param and @returns tags
    - Java: Javadoc with @param and @return tags

    Args:
        description: Brief description of what the function does
        parameters: List of ParameterInfo objects describing each parameter
        return_type: Return type annotation (None for void/no return)
        language: Target language ('python', 'typescript', 'javascript', 'java')

    Returns:
        Formatted documentation string with proper indentation and syntax

    Examples:
        >>> params = [ParameterInfo("name", "str", description="User name")]
        >>> generate_docstring("Get user", params, "User", "python")
        '\"\"\"Get user.\\n\\nArgs:\\n    name: User name\\n\\nReturns:\\n    User\\n\"\"\"'
    """
    lang_lower = language.lower()

    if lang_lower == "python":
        return _generate_python_docstring(description, parameters, return_type)
    elif lang_lower in ("typescript", "javascript"):
        return _generate_jsdoc(description, parameters, return_type)
    elif lang_lower == "java":
        return _generate_javadoc(description, parameters, return_type)
    else:
        # Default to Python-style for unknown languages
        return _generate_python_docstring(description, parameters, return_type)


def _generate_python_docstring(
    description: str,
    parameters: List[ParameterInfo],
    return_type: Optional[str]
) -> str:
    """Generate Google-style Python docstring.

    Args:
        description: Function description
        parameters: List of parameter info
        return_type: Return type (None if no return)

    Returns:
        Formatted Python docstring
    """
    lines = ['"""' + description + "."]

    # Add Args section if there are parameters
    if parameters:
        lines.append("")
        lines.append("Args:")
        for param in parameters:
            # Format: name: Description
            param_line = f"    {param.name}"
            if param.description:
                param_line += f": {param.description}"
            else:
                # Include type info if no description
                type_str = param.python_type or "Any"
                if param.is_optional:
                    param_line += f" (optional): {type_str}"
                else:
                    param_line += f": {type_str}"
            lines.append(param_line)

    # Add Returns section if there's a return type
    if return_type and return_type.lower() not in ("none", "void"):
        lines.append("")
        lines.append("Returns:")
        lines.append(f"    {return_type}")

    lines.append('"""')
    return "\n".join(lines)


def _generate_jsdoc(
    description: str,
    parameters: List[ParameterInfo],
    return_type: Optional[str]
) -> str:
    """Generate JSDoc comment for TypeScript/JavaScript.

    Args:
        description: Function description
        parameters: List of parameter info
        return_type: Return type (None if no return)

    Returns:
        Formatted JSDoc comment
    """
    lines = ["/**", f" * {description}."]

    # Add @param tags
    if parameters:
        lines.append(" *")
        for param in parameters:
            type_str = param.typescript_type or "any"
            # JSDoc format: @param {type} name - Description
            if param.is_optional:
                param_tag = f" * @param {{{type_str}}} [{param.name}]"
            else:
                param_tag = f" * @param {{{type_str}}} {param.name}"

            if param.description:
                param_tag += f" - {param.description}"
            lines.append(param_tag)

    # Add @returns tag if there's a return type
    if return_type and return_type.lower() not in ("void", "undefined"):
        lines.append(f" * @returns {{{return_type}}}")

    lines.append(" */")
    return "\n".join(lines)


def _generate_javadoc(
    description: str,
    parameters: List[ParameterInfo],
    return_type: Optional[str]
) -> str:
    """Generate Javadoc comment for Java.

    Args:
        description: Method description
        parameters: List of parameter info
        return_type: Return type (None if no return)

    Returns:
        Formatted Javadoc comment
    """
    lines = ["/**", f" * {description}."]

    # Add @param tags
    if parameters:
        lines.append(" *")
        for param in parameters:
            # Javadoc format: @param name description
            param_tag = f" * @param {param.name}"
            if param.description:
                param_tag += f" {param.description}"
            elif param.java_type:
                # Use type hint as description fallback
                optional_marker = " (optional)" if param.is_optional else ""
                param_tag += f" the {param.java_type}{optional_marker}"
            lines.append(param_tag)

    # Add @return tag if there's a return type
    if return_type and return_type.lower() != "void":
        lines.append(f" * @return {return_type}")

    lines.append(" */")
    return "\n".join(lines)


def format_arguments_for_call(
    parameters: List[ParameterInfo],
    values: List[str],
    language: str,
    style: str = "positional"
) -> str:
    """Format argument values for a function/method call based on language and style.

    Generates argument strings for calling functions with different argument
    passing conventions based on the target language and preferred style.

    Args:
        parameters: List of ParameterInfo objects describing the parameters
        values: List of argument values to pass (must match parameter count for positional)
        language: Target language ('python', 'typescript', 'javascript', 'java')
        style: Argument passing style:
            - 'positional': Pass arguments by position (all languages)
            - 'named': Pass arguments by name (Python kwargs, TS/JS object)
            - 'mixed': Mix of positional and named (Python only)

    Returns:
        Formatted argument string for function call

    Examples:
        >>> params = [ParameterInfo("name", python_type="str"),
        ...           ParameterInfo("age", python_type="int", default_value="0")]
        >>> format_arguments_for_call(params, ['"Alice"', "25"], "python", "positional")
        '"Alice", 25'
        >>> format_arguments_for_call(params, ['"Alice"', "25"], "python", "named")
        'name="Alice", age=25'
        >>> format_arguments_for_call(params, ['"Alice"'], "python", "positional")
        '"Alice"'
        >>> format_arguments_for_call(params, ['"Bob"', "30"], "typescript", "named")
        '{ name: "Bob", age: 30 }'
    """
    if not parameters:
        return ""

    language_lower = language.lower()

    # Handle positional style (all languages)
    if style == "positional":
        # Only include values up to the number provided
        # This allows omitting trailing defaults
        return ", ".join(values)

    # Handle named style
    if style == "named":
        if language_lower == "python":
            # Python keyword arguments
            args = []
            for i, param in enumerate(parameters):
                if i < len(values):
                    # Skip if value matches default
                    if param.default_value is not None and values[i] == param.default_value:
                        continue
                    args.append(f"{param.name}={values[i]}")
                elif param.default_value is None and not param.is_optional:
                    # Required param without value - use placeholder
                    args.append(f"{param.name}=...")
            return ", ".join(args)

        elif language_lower in ("typescript", "javascript"):
            # TypeScript/JavaScript object destructuring pattern
            args = []
            for i, param in enumerate(parameters):
                if i < len(values):
                    # Skip if value matches default
                    if param.default_value is not None and values[i] == param.default_value:
                        continue
                    args.append(f"{param.name}: {values[i]}")
                elif param.default_value is None and not param.is_optional:
                    # Required param without value
                    args.append(f"{param.name}: undefined")
            if args:
                return "{ " + ", ".join(args) + " }"
            return "{}"

        elif language_lower == "java":
            # Java doesn't support named arguments, fall back to positional
            return ", ".join(values)

        else:
            # Unknown language, use positional
            return ", ".join(values)

    # Handle mixed style (Python only)
    if style == "mixed":
        if language_lower == "python":
            # First half positional, second half named
            # Required params positional, optional params named
            positional_args = []
            named_args = []

            for i, param in enumerate(parameters):
                if i >= len(values):
                    break

                if not param.is_optional:
                    # Required params are positional
                    positional_args.append(values[i])
                else:
                    # Optional params are named (skip defaults)
                    if param.default_value is not None and values[i] == param.default_value:
                        continue
                    named_args.append(f"{param.name}={values[i]}")

            all_args = positional_args + named_args
            return ", ".join(all_args)
        else:
            # Mixed not supported for other languages, use positional
            return ", ".join(values)

    # Unknown style, fall back to positional
    return ", ".join(values)


def format_python_keyword_args(
    parameters: List[ParameterInfo],
    values: List[str]
) -> str:
    """Format Python function call arguments with full PEP 570/3102 support.

    Handles advanced Python argument syntax including:
    - Positional-only parameters (before /)
    - Regular positional-or-keyword parameters
    - *args (variadic positional)
    - Keyword-only parameters (after *)
    - **kwargs (variadic keyword)
    - Default values

    Parameter markers are detected by special names:
    - "/" indicates end of positional-only params
    - "*" indicates start of keyword-only params (without args)
    - "*args" for variadic positional arguments
    - "**kwargs" for variadic keyword arguments

    Args:
        parameters: List of ParameterInfo objects describing parameters.
                   Special marker params have names "/", "*", "*args", "**kwargs".
        values: List of argument values to pass. Values for marker params
               like "/" and "*" should be empty strings and will be skipped.

    Returns:
        Formatted argument string for Python function call.

    Examples:
        >>> # Simple positional args
        >>> params = [ParameterInfo("x"), ParameterInfo("y")]
        >>> format_python_keyword_args(params, ["1", "2"])
        '1, 2'

        >>> # Positional-only args (before /)
        >>> params = [ParameterInfo("x"), ParameterInfo("/"), ParameterInfo("y")]
        >>> format_python_keyword_args(params, ["1", "", "2"])
        '1, y=2'

        >>> # Keyword-only args (after *)
        >>> params = [ParameterInfo("x"), ParameterInfo("*"), ParameterInfo("y")]
        >>> format_python_keyword_args(params, ["1", "", "2"])
        '1, y=2'

        >>> # With *args and **kwargs
        >>> params = [ParameterInfo("x"), ParameterInfo("*args"), ParameterInfo("y"), ParameterInfo("**kwargs")]
        >>> format_python_keyword_args(params, ["1", "*extra", "2", "**opts"])
        '1, *extra, y=2, **opts'

        >>> # With default values - skip if value matches default
        >>> params = [ParameterInfo("x", default_value="0"), ParameterInfo("y")]
        >>> format_python_keyword_args(params, ["0", "2"])
        'y=2'
    """
    if not parameters or not values:
        return ""

    result_args: List[str] = []

    # Track argument mode
    seen_positional_only_marker = False  # After "/" - remaining args can be keyword
    seen_keyword_only_marker = False  # After "*" or "*args" - must use keyword syntax

    # Collect positional-only args (before /)
    positional_only_args: List[tuple[str, str, Optional[str]]] = []
    # Collect regular args (between / and *)
    regular_args: List[tuple[str, str, Optional[str]]] = []
    # Collect keyword-only args (after *)
    keyword_only_args: List[tuple[str, str, Optional[str]]] = []
    # Track *args and **kwargs
    variadic_args: Optional[str] = None
    variadic_kwargs: Optional[str] = None

    value_idx = 0

    for param in parameters:
        if value_idx >= len(values):
            break

        value = values[value_idx]
        value_idx += 1

        # Handle special markers
        if param.name == "/":
            seen_positional_only_marker = True
            continue
        elif param.name == "*":
            seen_keyword_only_marker = True
            continue
        elif param.name == "*args" or (param.name.startswith("*") and not param.name.startswith("**")):
            seen_keyword_only_marker = True
            if value and value != "":
                variadic_args = value
            continue
        elif param.name == "**kwargs" or param.name.startswith("**"):
            if value and value != "":
                variadic_kwargs = value
            continue

        # Skip if value matches default (optimization)
        if param.default_value is not None and value == param.default_value:
            continue

        # Categorize the argument
        if not seen_positional_only_marker and not seen_keyword_only_marker:
            # Before any markers - collect for later categorization
            positional_only_args.append((param.name, value, param.default_value))
        elif seen_positional_only_marker and not seen_keyword_only_marker:
            # Between / and * - regular positional-or-keyword
            regular_args.append((param.name, value, param.default_value))
        else:
            # After * - keyword-only
            keyword_only_args.append((param.name, value, param.default_value))

    # Check if there's a / marker to determine if early args are positional-only
    has_positional_only = any(p.name == "/" for p in parameters)

    # Build the result
    if has_positional_only:
        # Args before / are passed positionally
        for name, value, default in positional_only_args:
            if value:
                result_args.append(value)
    else:
        # No / marker - use positional for these args
        for name, value, default in positional_only_args:
            if value:
                result_args.append(value)

    # Regular args (between / and *) - can be positional or keyword
    for name, value, default in regular_args:
        if value:
            if default is not None:
                # Has default - use keyword style
                result_args.append(f"{name}={value}")
            else:
                # No default - positional is fine
                result_args.append(value)

    # Add *args if present
    if variadic_args:
        result_args.append(variadic_args)

    # Keyword-only args - must use keyword syntax
    for name, value, default in keyword_only_args:
        if value:
            result_args.append(f"{name}={value}")

    # Add **kwargs if present
    if variadic_kwargs:
        result_args.append(variadic_kwargs)

    return ", ".join(result_args)


def substitute_template_variables(
    template: str,
    variables: Dict[str, str],
    strict: bool = False
) -> str:
    """Substitute variables into a code template.

    Handles variable substitution with support for:
    - Simple variables: {{variable_name}}
    - Conditional sections: {{#if condition}}content{{/if}}
    - List variables: {{#each items}}{{.}}{{/each}}
    - Optional sections that clean up whitespace when empty

    Args:
        template: Template string with {{variable}} placeholders
        variables: Dictionary mapping variable names to values
        strict: If True, raise error for missing variables; if False, use empty string

    Returns:
        Template with all variables substituted

    Raises:
        ValueError: If strict=True and a required variable is missing

    Examples:
        >>> substitute_template_variables("Hello {{name}}!", {"name": "World"})
        'Hello World!'

        >>> substitute_template_variables("{{#if show}}visible{{/if}}", {"show": "true"})
        'visible'

        >>> substitute_template_variables("{{#each items}}{{.}}, {{/each}}", {"items": "a,b,c"})
        'a, b, c, '
    """
    import re

    result = template

    # Process conditional sections first: {{#if var}}content{{/if}}
    def process_conditional(match: re.Match[str]) -> str:
        var_name = match.group(1)
        content = match.group(2)

        # Check if variable exists and is truthy
        if var_name in variables:
            value = variables[var_name]
            # Truthy check: non-empty string, not "false", not "0", not "none"
            if value and value.lower() not in ("false", "0", "none", "null", ""):
                # Recursively process the content
                return substitute_template_variables(content, variables, strict)

        return ""

    # Match {{#if var_name}}...{{/if}}
    conditional_pattern = r'\{\{#if\s+(\w+)\}\}(.*?)\{\{/if\}\}'
    result = re.sub(conditional_pattern, process_conditional, result, flags=re.DOTALL)

    # Process inverse conditionals: {{#unless var}}content{{/unless}}
    def process_unless(match: re.Match[str]) -> str:
        var_name = match.group(1)
        content = match.group(2)

        # Check if variable doesn't exist or is falsy
        if var_name not in variables:
            return substitute_template_variables(content, variables, strict)

        value = variables[var_name]
        if not value or value.lower() in ("false", "0", "none", "null", ""):
            return substitute_template_variables(content, variables, strict)

        return ""

    unless_pattern = r'\{\{#unless\s+(\w+)\}\}(.*?)\{\{/unless\}\}'
    result = re.sub(unless_pattern, process_unless, result, flags=re.DOTALL)

    # Process each loops: {{#each var}}content with {{.}}{{/each}}
    def process_each(match: re.Match[str]) -> str:
        var_name = match.group(1)
        content = match.group(2)

        if var_name not in variables:
            if strict:
                raise ValueError(f"Missing list variable: {var_name}")
            return ""

        # Split value by comma for list
        items = [item.strip() for item in variables[var_name].split(",") if item.strip()]

        if not items:
            return ""

        results = []
        for item in items:
            # Replace {{.}} with the current item
            item_content = content.replace("{{.}}", item)
            # Also support {{@index}} for index
            item_content = re.sub(r'\{\{@index\}\}', str(items.index(item)), item_content)
            results.append(item_content)

        return "".join(results)

    each_pattern = r'\{\{#each\s+(\w+)\}\}(.*?)\{\{/each\}\}'
    result = re.sub(each_pattern, process_each, result, flags=re.DOTALL)

    # Process simple variable substitution: {{var_name}}
    def process_variable(match: re.Match[str]) -> str:
        var_name = match.group(1)

        if var_name in variables:
            return variables[var_name]

        if strict:
            raise ValueError(f"Missing required variable: {var_name}")

        return ""

    # Match {{variable_name}} but not {{#...}} or {{/...}} or {{.}} or {{@...}}
    variable_pattern = r'\{\{(?!#|/|\.|\@)(\w+)\}\}'
    result = re.sub(variable_pattern, process_variable, result)

    # Clean up extra whitespace from empty optional sections
    result = _clean_template_whitespace(result)

    return result


def _clean_template_whitespace(content: str) -> str:
    """Clean up extra whitespace left by empty optional sections.

    Args:
        content: Content with potential extra whitespace

    Returns:
        Cleaned content with normalized whitespace
    """
    import re

    # Remove lines that are only whitespace (but preserve intentional blank lines)
    lines = content.split('\n')
    cleaned_lines = []
    prev_blank = False

    for line in lines:
        is_blank = not line.strip()

        # Skip consecutive blank lines
        if is_blank and prev_blank:
            continue

        cleaned_lines.append(line)
        prev_blank = is_blank

    result = '\n'.join(cleaned_lines)

    # Remove trailing whitespace from lines
    result = re.sub(r'[ \t]+$', '', result, flags=re.MULTILINE)

    # Remove multiple consecutive blank lines (more than 2)
    result = re.sub(r'\n{3,}', '\n\n', result)

    # Remove leading/trailing blank lines
    result = result.strip()

    return result


def generate_type_annotations(
    parameters: List[ParameterInfo],
    return_type: Optional[str],
    language: str
) -> Dict[str, str]:
    """Generate formatted type annotations for a given language.

    Creates properly formatted type strings for parameters and return types,
    with support for Python type hints, TypeScript types, and Java generics.

    Args:
        parameters: List of ParameterInfo objects with type information
        return_type: Return type string, or None for void/no return
        language: Target language ('python', 'typescript', 'java', 'javascript')

    Returns:
        Dictionary with 'params' and 'return' keys containing formatted type strings.
        - 'params': Formatted parameter types (e.g., "name: str, count: int")
        - 'return': Formatted return type (e.g., "-> str" for Python, ": string" for TS)

    Examples:
        >>> params = [ParameterInfo("name", "string"), ParameterInfo("count", "integer")]
        >>> generate_type_annotations(params, "string", "python")
        {'params': 'name: str, count: int', 'return': '-> str'}

        >>> generate_type_annotations(params, "string", "typescript")
        {'params': 'name: string, count: number', 'return': ': string'}

        >>> generate_type_annotations(params, None, "java")
        {'params': 'String name, int count', 'return': 'void'}
    """
    import re

    # Type mappings between languages
    python_to_typescript: Dict[str, str] = {
        "str": "string",
        "int": "number",
        "float": "number",
        "bool": "boolean",
        "None": "void",
        "list": "Array",
        "dict": "object",
        "Any": "any",
    }

    python_to_java: Dict[str, str] = {
        "str": "String",
        "int": "int",
        "float": "double",
        "bool": "boolean",
        "None": "void",
        "list": "List",
        "dict": "Map",
        "Any": "Object",
    }

    typescript_to_python: Dict[str, str] = {
        "string": "str",
        "number": "int",
        "boolean": "bool",
        "void": "None",
        "any": "Any",
        "object": "dict",
        "undefined": "None",
        "null": "None",
    }

    java_to_python: Dict[str, str] = {
        "String": "str",
        "int": "int",
        "Integer": "int",
        "long": "int",
        "Long": "int",
        "double": "float",
        "Double": "float",
        "float": "float",
        "Float": "float",
        "boolean": "bool",
        "Boolean": "bool",
        "void": "None",
        "Object": "Any",
    }

    def normalize_to_python(type_str: str) -> str:
        """Normalize a type string to Python type hint format."""
        if not type_str:
            return "Any"

        # Already Python format
        if type_str in ("str", "int", "float", "bool", "None", "Any"):
            return type_str

        # Check TypeScript mappings
        if type_str.lower() in typescript_to_python:
            return typescript_to_python[type_str.lower()]

        # Check Java mappings
        if type_str in java_to_python:
            return java_to_python[type_str]

        # Handle generic types like List<String>, Array<string>

        # TypeScript Array<T> -> list[T]
        array_match = re.match(r"Array<(.+)>", type_str)
        if array_match:
            inner = normalize_to_python(array_match.group(1))
            return f"list[{inner}]"

        # Java List<T> -> list[T]
        list_match = re.match(r"List<(.+)>", type_str)
        if list_match:
            inner = normalize_to_python(list_match.group(1))
            return f"list[{inner}]"

        # TypeScript union with undefined -> Optional
        if " | undefined" in type_str or " | null" in type_str:
            base = type_str.replace(" | undefined", "").replace(" | null", "")
            inner = normalize_to_python(base)
            return f"Optional[{inner}]"

        # Java Optional<T> -> Optional[T]
        optional_match = re.match(r"Optional<(.+)>", type_str)
        if optional_match:
            inner = normalize_to_python(optional_match.group(1))
            return f"Optional[{inner}]"

        # Handle Python list[T] format
        python_list_match = re.match(r"list\[(.+)\]", type_str)
        if python_list_match:
            inner = normalize_to_python(python_list_match.group(1))
            return f"list[{inner}]"

        # Handle Python Optional[T] format
        python_optional_match = re.match(r"Optional\[(.+)\]", type_str)
        if python_optional_match:
            inner = normalize_to_python(python_optional_match.group(1))
            return f"Optional[{inner}]"

        return type_str

    def convert_to_typescript(python_type: str) -> str:
        """Convert Python type to TypeScript type."""
        if not python_type or python_type == "Any":
            return "any"

        # Direct mapping
        if python_type in python_to_typescript:
            return python_to_typescript[python_type]

        # list[T] -> Array<T>
        list_match = re.match(r"list\[(.+)\]", python_type)
        if list_match:
            inner = convert_to_typescript(list_match.group(1))
            return f"Array<{inner}>"

        # Optional[T] -> T | undefined
        optional_match = re.match(r"Optional\[(.+)\]", python_type)
        if optional_match:
            inner = convert_to_typescript(optional_match.group(1))
            return f"{inner} | undefined"

        return python_type

    def convert_to_java(python_type: str) -> str:
        """Convert Python type to Java type."""
        if not python_type or python_type == "Any":
            return "Object"

        # Direct mapping
        if python_type in python_to_java:
            return python_to_java[python_type]

        # list[T] -> List<T>
        list_match = re.match(r"list\[(.+)\]", python_type)
        if list_match:
            inner = convert_to_java(list_match.group(1))
            return f"List<{inner}>"

        # Optional[T] -> Optional<T>
        optional_match = re.match(r"Optional\[(.+)\]", python_type)
        if optional_match:
            inner = convert_to_java(optional_match.group(1))
            return f"Optional<{inner}>"

        return python_type

    # Format parameter types
    lang = language.lower()
    param_parts: List[str] = []

    for param in parameters:
        # Get the type from ParameterInfo based on language
        if lang == "python":
            param_type = param.python_type
        elif lang in ("typescript", "javascript"):
            param_type = param.typescript_type
        elif lang == "java":
            param_type = param.java_type
        else:
            param_type = param.python_type

        # Normalize to Python first for conversion
        normalized = normalize_to_python(param_type)

        # Convert to target language
        if lang == "python":
            final_type = normalized
            if param.is_optional and not normalized.startswith("Optional"):
                final_type = f"Optional[{normalized}]"
            param_parts.append(f"{param.name}: {final_type}")
        elif lang in ("typescript", "javascript"):
            final_type = convert_to_typescript(normalized)
            opt_marker = "?" if param.is_optional else ""
            param_parts.append(f"{param.name}{opt_marker}: {final_type}")
        elif lang == "java":
            final_type = convert_to_java(normalized)
            param_parts.append(f"{final_type} {param.name}")

    # Format return type
    if return_type:
        normalized_return = normalize_to_python(return_type)
    else:
        normalized_return = "None"

    if lang == "python":
        return_str = f"-> {normalized_return}"
    elif lang in ("typescript", "javascript"):
        ts_return = convert_to_typescript(normalized_return)
        return_str = f": {ts_return}"
    elif lang == "java":
        java_return = convert_to_java(normalized_return)
        return_str = java_return
    else:
        return_str = normalized_return

    return {
        "params": ", ".join(param_parts),
        "return": return_str
    }


def generate_function_signature(
    name: str,
    parameters: List[ParameterInfo],
    return_type: Optional[str],
    language: str,
    is_async: bool = False,
    type_parameters: Optional[List[str]] = None,
    access_modifier: str = "public"
) -> str:
    """Generate a function/method signature for the specified language.

    Creates just the signature line (not the body) for a function or method,
    handling language-specific syntax including async functions and generics.

    Args:
        name: The function/method name
        parameters: List of ParameterInfo objects describing parameters
        return_type: Return type annotation (None for void/no return type)
        language: Target language ('python', 'typescript', 'javascript', 'java')
        is_async: Whether this is an async function (JS/TS only)
        type_parameters: Generic type parameters (e.g., ['T', 'K extends string'])
        access_modifier: Java access modifier ('public', 'private', 'protected')

    Returns:
        The function signature string (without body/braces)

    Raises:
        ValueError: If language is not supported

    Examples:
        >>> params = [ParameterInfo("name", python_type="str", typescript_type="string")]
        >>> generate_function_signature("greet", params, "str", "python")
        'def greet(name: str) -> str:'

        >>> generate_function_signature("greet", params, "string", "typescript", is_async=True)
        'async function greet(name: string): string'

        >>> generate_function_signature("greet", params, "String", "java")
        'public String greet(String name)'
    """
    language = language.lower()
    supported_languages = ("python", "typescript", "javascript", "java")

    if language not in supported_languages:
        raise ValueError(
            f"Unsupported language: {language}. "
            f"Supported: {', '.join(supported_languages)}"
        )

    # Format type parameters for generics
    generics_str = ""
    if type_parameters:
        generics_str = f"<{', '.join(type_parameters)}>"

    if language == "python":
        params_str = format_python_params(parameters)
        return_annotation = f" -> {return_type}" if return_type else ""
        async_prefix = "async " if is_async else ""
        return f"{async_prefix}def {name}{generics_str}({params_str}){return_annotation}:"

    elif language in ("typescript", "javascript"):
        params_str = format_typescript_params(parameters)
        async_prefix = "async " if is_async else ""

        if language == "typescript":
            return_annotation = f": {return_type}" if return_type else ": void"
            return f"{async_prefix}function {name}{generics_str}({params_str}){return_annotation}"
        else:
            # JavaScript doesn't have type annotations
            return f"{async_prefix}function {name}({params_str})"

    elif language == "java":
        params_str = format_java_params(parameters)
        return_type_str = return_type if return_type else "void"
        # Java: [modifier] [generics] return_type name(params)
        if generics_str:
            return f"{access_modifier} {generics_str} {return_type_str} {name}({params_str})"
        else:
            return f"{access_modifier} {return_type_str} {name}({params_str})"

    # Should never reach here due to earlier validation
    return ""


def generate_python_function(
    name: str,
    params: List[ParameterInfo],
    body: str,
    return_type: str = "None",
    decorators: Optional[List[str]] = None,
    docstring: Optional[str] = None,
    is_async: bool = False
) -> str:
    """Generate a complete Python function from parameters.

    Args:
        name: Function name
        params: List of ParameterInfo for parameters
        body: Function body (will be indented)
        return_type: Return type annotation
        decorators: Optional list of decorator strings (without @)
        docstring: Optional docstring content
        is_async: Whether function is async

    Returns:
        Complete Python function as string
    """
    lines = []

    # Add decorators
    if decorators:
        for dec in decorators:
            lines.append(f"@{dec}")

    # Build function signature
    async_prefix = "async " if is_async else ""
    param_str = format_python_params(params)
    lines.append(f"{async_prefix}def {name}({param_str}) -> {return_type}:")

    # Add docstring
    if docstring:
        lines.append(f'    """')
        for doc_line in docstring.split('\n'):
            lines.append(f'    {doc_line}')
        lines.append(f'    """')

    # Add body (ensure proper indentation)
    for body_line in body.split('\n'):
        if body_line.strip():
            lines.append(f'    {body_line}')
        else:
            lines.append('')

    return '\n'.join(lines)


def generate_typescript_function(
    name: str,
    params: List[ParameterInfo],
    body: str,
    return_type: str = "void",
    is_async: bool = False,
    is_export: bool = True,
    jsdoc: Optional[str] = None
) -> str:
    """Generate a complete TypeScript function from parameters.

    Args:
        name: Function name
        params: List of ParameterInfo for parameters
        body: Function body (will be indented)
        return_type: Return type annotation
        is_async: Whether function is async
        is_export: Whether to export the function
        jsdoc: Optional JSDoc comment content

    Returns:
        Complete TypeScript function as string
    """
    lines = []

    # Add JSDoc
    if jsdoc:
        lines.append('/**')
        for doc_line in jsdoc.split('\n'):
            lines.append(f' * {doc_line}')
        lines.append(' */')

    # Build function signature
    export_prefix = "export " if is_export else ""
    async_prefix = "async " if is_async else ""
    param_str = format_typescript_params(params)

    # Handle async return type
    actual_return = f"Promise<{return_type}>" if is_async and return_type != "void" else return_type

    lines.append(f"{export_prefix}{async_prefix}function {name}({param_str}): {actual_return} {{")

    # Add body (ensure proper indentation)
    for body_line in body.split('\n'):
        if body_line.strip():
            lines.append(f'  {body_line}')
        else:
            lines.append('')

    lines.append('}')

    return '\n'.join(lines)


def generate_java_method(
    name: str,
    params: List[ParameterInfo],
    body: str,
    return_type: str = "void",
    modifiers: str = "public",
    annotations: Optional[List[str]] = None,
    javadoc: Optional[str] = None,
    throws: Optional[List[str]] = None
) -> str:
    """Generate a complete Java method from parameters.

    Args:
        name: Method name
        params: List of ParameterInfo for parameters
        body: Method body (will be indented)
        return_type: Return type
        modifiers: Access modifiers (public, private, etc.)
        annotations: Optional list of annotation strings (without @)
        javadoc: Optional Javadoc comment content
        throws: Optional list of exception types

    Returns:
        Complete Java method as string
    """
    lines = []

    # Add Javadoc
    if javadoc:
        lines.append('/**')
        for doc_line in javadoc.split('\n'):
            lines.append(f' * {doc_line}')
        lines.append(' */')

    # Add annotations
    if annotations:
        for ann in annotations:
            lines.append(f"@{ann}")

    # Build method signature
    param_str = format_java_params(params)
    throws_clause = f" throws {', '.join(throws)}" if throws else ""

    lines.append(f"{modifiers} {return_type} {name}({param_str}){throws_clause} {{")

    # Add body (ensure proper indentation)
    for body_line in body.split('\n'):
        if body_line.strip():
            lines.append(f'    {body_line}')
        else:
            lines.append('')

    lines.append('}')

    return '\n'.join(lines)


def generate_javascript_function(
    name: str,
    params: List[ParameterInfo],
    body: str,
    is_async: bool = False,
    is_export: bool = True,
    jsdoc: Optional[str] = None
) -> str:
    """Generate a complete JavaScript function from parameters.

    Args:
        name: Function name
        params: List of ParameterInfo for parameters
        body: Function body (will be indented)
        is_async: Whether function is async
        is_export: Whether to export the function
        jsdoc: Optional JSDoc comment content

    Returns:
        Complete JavaScript function as string
    """
    lines = []

    # Add JSDoc
    if jsdoc:
        lines.append('/**')
        for doc_line in jsdoc.split('\n'):
            lines.append(f' * {doc_line}')
        lines.append(' */')

    # Build function signature (JS doesn't have type annotations in standard syntax)
    export_prefix = "export " if is_export else ""
    async_prefix = "async " if is_async else ""

    # Format params without types for JS
    param_names = []
    required = [p for p in params if not p.is_optional]
    optional = [p for p in params if p.is_optional]

    for param in required:
        param_names.append(param.name)

    for param in optional:
        if param.default_value is not None:
            param_names.append(f"{param.name} = {param.default_value}")
        else:
            param_names.append(param.name)

    param_str = ", ".join(param_names)

    lines.append(f"{export_prefix}{async_prefix}function {name}({param_str}) {{")

    # Add body (ensure proper indentation)
    for body_line in body.split('\n'):
        if body_line.strip():
            lines.append(f'  {body_line}')
        else:
            lines.append('')

    lines.append('}')

    return '\n'.join(lines)


def detect_return_value(code: str, language: str) -> tuple[bool, Optional[str]]:
    """Detect if code contains return statements and infer the return type.

    Analyzes code to detect explicit return statements and implicit returns
    (like last expressions in JavaScript arrow functions). Attempts to infer
    the return type from the returned expression.

    Args:
        code: The code to analyze for return values
        language: Programming language ('python', 'typescript', 'javascript', 'java')

    Returns:
        Tuple of (has_return, inferred_type) where:
        - has_return: True if code contains explicit or implicit return
        - inferred_type: Inferred type string or None if cannot be determined
    """
    if not code or not code.strip():
        return (False, None)

    lang = language.lower()
    lines = code.strip().split('\n')

    # Check for explicit return statements
    has_explicit_return = False
    returned_expression: Optional[str] = None

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('return '):
            has_explicit_return = True
            # Extract the returned expression
            returned_expression = stripped[7:].rstrip(';').strip()
            break
        elif stripped == 'return' or stripped == 'return;':
            has_explicit_return = True
            returned_expression = None
            break

    # Check for implicit returns (JS arrow functions with expression body)
    has_implicit_return = False
    if not has_explicit_return and lang in ('javascript', 'typescript'):
        # Single expression without braces is an implicit return
        # Check if we have a single line that's not a statement
        if len(lines) == 1:
            single_line = lines[0].strip()
            # Not a control structure or declaration
            if not any(single_line.startswith(kw) for kw in
                      ['if', 'for', 'while', 'switch', 'const', 'let', 'var', 'function', 'class', '{']):
                has_implicit_return = True
                returned_expression = single_line.rstrip(';')

    has_return = has_explicit_return or has_implicit_return

    # Infer type from returned expression
    inferred_type: Optional[str] = None

    if returned_expression:
        expr = returned_expression.strip()

        # Literal type inference
        if expr in ('true', 'false', 'True', 'False'):
            inferred_type = 'boolean' if lang in ('javascript', 'typescript') else 'bool'
        elif expr == 'null' or expr == 'None':
            inferred_type = 'null' if lang in ('javascript', 'typescript') else 'None'
        elif expr == 'undefined':
            inferred_type = 'undefined'
        elif expr.startswith('"') or expr.startswith("'") or expr.startswith('`'):
            inferred_type = 'string' if lang in ('javascript', 'typescript') else 'str'
        elif expr.startswith('['):
            if lang == 'python':
                inferred_type = 'list'
            elif lang == 'java':
                inferred_type = 'List'
            else:
                inferred_type = 'array'
        elif expr.startswith('{'):
            if lang == 'python':
                inferred_type = 'dict'
            elif lang == 'java':
                inferred_type = 'Map'
            else:
                inferred_type = 'object'
        elif expr.replace('.', '').replace('-', '').isdigit():
            # Numeric literal
            if '.' in expr:
                inferred_type = 'number' if lang in ('javascript', 'typescript') else 'float'
            else:
                inferred_type = 'number' if lang in ('javascript', 'typescript') else 'int'
        elif expr.startswith('new '):
            # Constructor call - extract class name
            class_match = expr[4:].split('(')[0].strip()
            if class_match:
                inferred_type = class_match
        elif expr.startswith('await '):
            # Async call - indicate it's a Promise result
            inferred_type = 'Promise'
        elif '(' in expr:
            # Function call - cannot determine type without more context
            inferred_type = None

    return (has_return, inferred_type)


def generate_replacement_call(
    function_name: str,
    arguments: list[str],
    language: str,
    is_method: bool = False,
    object_name: Optional[str] = None
) -> str:
    """Generate a function call to replace duplicate code.

    Creates the appropriate function/method call syntax for the target language
    that will replace the duplicated code block.

    Args:
        function_name: Name of the extracted function to call
        arguments: List of argument expressions to pass
        language: Target programming language
        is_method: Whether this is a method call (obj.method()) vs function call
        object_name: Object/instance name for method calls (required if is_method=True)

    Returns:
        Formatted function call string appropriate for the language

    Examples:
        >>> generate_replacement_call("processData", ["items", "config"], "python")
        'processData(items, config)'
        >>> generate_replacement_call("fetch", ["url"], "typescript", is_method=True, object_name="this")
        'this.fetch(url)'
        >>> generate_replacement_call("getData", [], "go")
        'getData()'
    """
    # Format argument list
    args_str = ", ".join(arguments)

    # Build the call based on method vs function
    if is_method and object_name:
        base_call = f"{object_name}.{function_name}"
    else:
        base_call = function_name

    # Language-specific formatting
    if language in ("python", "javascript", "typescript", "java", "go", "rust", "c", "cpp"):
        # Standard parentheses call syntax
        return f"{base_call}({args_str})"

    elif language == "ruby":
        # Ruby allows omitting parentheses for no-arg calls
        if arguments:
            return f"{base_call}({args_str})"
        else:
            return base_call

    elif language == "kotlin":
        # Kotlin standard call syntax
        return f"{base_call}({args_str})"

    elif language == "swift":
        # Swift standard call syntax
        return f"{base_call}({args_str})"

    elif language == "scala":
        # Scala allows omitting parentheses for no-arg calls
        if arguments:
            return f"{base_call}({args_str})"
        else:
            return base_call

    else:
        # Default: standard call syntax
        return f"{base_call}({args_str})"


def identify_unused_imports(
    file_content: str,
    removed_code: str,
    language: str
) -> list[str]:
    """Identify imports that were only used in removed duplicate code.

    Analyzes file content and removed code to find imports that are no longer
    needed after duplicate code removal. Uses conservative analysis to only
    flag imports that are definitely unused.

    Args:
        file_content: Full content of the file after duplicate removal
        removed_code: The code that was removed (duplicate section)
        language: Programming language ('python', 'typescript', 'javascript', 'java')

    Returns:
        List of import statements that can be safely removed

    Example:
        >>> content = "import os\\n\\ndef main():\\n    pass"
        >>> removed = "path = os.path.join('a', 'b')"
        >>> identify_unused_imports(content, removed, "python")
        ['import os']
    """
    logger = get_logger("codegen.unused_imports")

    if not file_content or not removed_code:
        return []

    lang_lower = language.lower()
    unused_imports: list[str] = []

    # Extract identifiers used in removed code
    removed_identifiers = _extract_identifiers(removed_code, lang_lower)

    if not removed_identifiers:
        return []

    # Extract identifiers used in remaining content (excluding imports)
    content_without_imports = _remove_import_lines(file_content, lang_lower)
    remaining_identifiers = _extract_identifiers(content_without_imports, lang_lower)

    # Extract import statements and their imported names
    imports_with_names = _extract_imports_with_names(file_content, lang_lower)

    for import_stmt, imported_names in imports_with_names:
        # Check if any imported name was used in removed code
        # but NOT used in remaining code
        used_in_removed = any(name in removed_identifiers for name in imported_names)
        used_in_remaining = any(name in remaining_identifiers for name in imported_names)

        if used_in_removed and not used_in_remaining:
            # Conservative check: ensure ALL names from this import are unused
            all_names_unused = all(name not in remaining_identifiers for name in imported_names)
            if all_names_unused:
                unused_imports.append(import_stmt)
                logger.debug(
                    "identified_unused_import",
                    import_stmt=import_stmt[:80],
                    imported_names=list(imported_names)[:5]
                )

    logger.info(
        "unused_imports_identified",
        language=language,
        total_imports=len(imports_with_names),
        unused_count=len(unused_imports)
    )

    return unused_imports


def _extract_identifiers(code: str, language: str) -> set[str]:
    """Extract all identifiers from code using regex patterns."""
    import re

    # Remove string literals to avoid false matches
    if language in ("python",):
        code = re.sub(r'"""[\s\S]*?"""', '', code)
        code = re.sub(r"'''[\s\S]*?'''", '', code)
        code = re.sub(r'"[^"]*"', '', code)
        code = re.sub(r"'[^']*'", '', code)
    elif language in ("typescript", "javascript", "java"):
        code = re.sub(r'`[\s\S]*?`', '', code)
        code = re.sub(r'"[^"]*"', '', code)
        code = re.sub(r"'[^']*'", '', code)

    # Remove comments
    if language == "python":
        code = re.sub(r'#.*$', '', code, flags=re.MULTILINE)
    elif language in ("typescript", "javascript", "java"):
        code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'/\*[\s\S]*?\*/', '', code)

    # Extract identifiers
    identifiers = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', code))
    return identifiers


def _remove_import_lines(content: str, language: str) -> str:
    """Remove import/require lines from content."""
    lines = content.split('\n')
    filtered_lines = []

    for line in lines:
        stripped = line.strip()
        is_import = False

        if language == "python":
            is_import = stripped.startswith('import ') or stripped.startswith('from ')
        elif language in ("typescript", "javascript"):
            is_import = (
                stripped.startswith('import ') or
                'require(' in stripped or
                stripped.startswith('export ')
            )
        elif language == "java":
            is_import = stripped.startswith('import ')

        if not is_import:
            filtered_lines.append(line)

    return '\n'.join(filtered_lines)


def _extract_imports_with_names(content: str, language: str) -> list[tuple[str, set[str]]]:
    """Extract import statements and the names they import."""
    import re

    results: list[tuple[str, set[str]]] = []

    if language == "python":
        # Pattern: import module
        for match in re.finditer(r'^(import\s+([\w.]+(?:\s+as\s+\w+)?(?:\s*,\s*[\w.]+(?:\s+as\s+\w+)?)*))\s*$', content, re.MULTILINE):
            stmt = match.group(1)
            names: set[str] = set()
            for item in re.findall(r'([\w.]+)(?:\s+as\s+(\w+))?', match.group(2)):
                module, alias = item
                names.add(alias if alias else module.split('.')[-1])
            if names:
                results.append((stmt, names))

        # Pattern: from module import names
        for match in re.finditer(r'^(from\s+[\w.]+\s+import\s+(.+?))\s*$', content, re.MULTILINE):
            stmt = match.group(1)
            names_part = match.group(2).strip('()')
            names = set()
            for item in re.findall(r'(\w+)(?:\s+as\s+(\w+))?', names_part):
                name, alias = item
                names.add(alias if alias else name)
            if names:
                results.append((stmt, names))

    elif language in ("typescript", "javascript"):
        # import name from 'source'
        for match in re.finditer(r'^(import\s+(\w+)\s+from\s+[\'"][^\'"]+[\'"])\s*;?\s*$', content, re.MULTILINE):
            results.append((match.group(1), {match.group(2)}))

        # import { names } from 'source'
        for match in re.finditer(r'^(import\s+\{([^}]+)\}\s+from\s+[\'"][^\'"]+[\'"])\s*;?\s*$', content, re.MULTILINE):
            names = set()
            for item in re.findall(r'(\w+)(?:\s+as\s+(\w+))?', match.group(2)):
                name, alias = item
                names.add(alias if alias else name)
            if names:
                results.append((match.group(1), names))

        # import * as name from 'source'
        for match in re.finditer(r'^(import\s+\*\s+as\s+(\w+)\s+from\s+[\'"][^\'"]+[\'"])\s*;?\s*$', content, re.MULTILINE):
            results.append((match.group(1), {match.group(2)}))

        # const name = require('source')
        for match in re.finditer(r'^(const\s+(\w+)\s*=\s*require\s*\([\'"][^\'"]+[\'"]\))\s*;?\s*$', content, re.MULTILINE):
            results.append((match.group(1), {match.group(2)}))

        # const { names } = require('source')
        for match in re.finditer(r'^(const\s+\{([^}]+)\}\s*=\s*require\s*\([\'"][^\'"]+[\'"]\))\s*;?\s*$', content, re.MULTILINE):
            names = set()
            for item in re.findall(r'(\w+)(?:\s*:\s*(\w+))?', match.group(2)):
                name, alias = item
                names.add(alias if alias else name)
            if names:
                results.append((match.group(1), names))

    elif language == "java":
        # import package.Class;
        for match in re.finditer(r'^(import\s+(?:static\s+)?([\w.]+))\s*;\s*$', content, re.MULTILINE):
            class_name = match.group(2).split('.')[-1]
            if class_name != '*':
                results.append((match.group(1), {class_name}))

    return results


def extract_imports_from_files(
    file_paths: List[str],
    language: str
) -> Dict[str, List[str]]:
    """Extract import statements from files containing duplicate code.

    Uses ast-grep patterns to find import statements for various languages.

    Args:
        file_paths: List of file paths to extract imports from
        language: Programming language for pattern matching

    Returns:
        Dictionary mapping file path to list of import statements
    """
    logger = get_logger("duplication.imports")

    if not file_paths:
        return {}

    # Define import patterns for each language
    import_patterns: Dict[str, List[str]] = {
        "python": [
            "import $MODULE",
            "from $MODULE import $NAMES",
            "from $MODULE import ($$$)",
        ],
        "typescript": [
            "import $NAME from '$SOURCE'",
            "import { $$$ } from '$SOURCE'",
            "import * as $NAME from '$SOURCE'",
            "import '$SOURCE'",
            "import type { $$$ } from '$SOURCE'",
        ],
        "javascript": [
            "import $NAME from '$SOURCE'",
            "import { $$$ } from '$SOURCE'",
            "import * as $NAME from '$SOURCE'",
            "import '$SOURCE'",
            "const $NAME = require('$SOURCE')",
            "const { $$$ } = require('$SOURCE')",
        ],
        "tsx": [
            "import $NAME from '$SOURCE'",
            "import { $$$ } from '$SOURCE'",
            "import * as $NAME from '$SOURCE'",
            "import '$SOURCE'",
            "import type { $$$ } from '$SOURCE'",
        ],
        "jsx": [
            "import $NAME from '$SOURCE'",
            "import { $$$ } from '$SOURCE'",
            "import * as $NAME from '$SOURCE'",
            "import '$SOURCE'",
            "const $NAME = require('$SOURCE')",
        ],
        "java": [
            "import $PACKAGE;",
            "import static $PACKAGE;",
        ],
        "csharp": [
            "using $NAMESPACE;",
            "using static $NAMESPACE;",
            "using $ALIAS = $NAMESPACE;",
        ],
        "go": [
            'import "$PACKAGE"',
            'import $ALIAS "$PACKAGE"',
        ],
        "rust": [
            "use $PATH;",
            "use $PATH as $ALIAS;",
            "use $PATH::{$$$};",
        ],
        "kotlin": [
            "import $PACKAGE",
            "import $PACKAGE as $ALIAS",
        ],
        "swift": [
            "import $MODULE",
            "import class $MODULE.$CLASS",
            "import struct $MODULE.$STRUCT",
        ],
        "ruby": [
            "require '$FILE'",
            'require "$FILE"',
            "require_relative '$FILE'",
        ],
        "php": [
            "use $NAMESPACE;",
            "use $NAMESPACE as $ALIAS;",
            "require '$FILE';",
            "require_once '$FILE';",
            "include '$FILE';",
        ],
    }

    # Get patterns for the specified language
    lang_lower = language.lower()
    patterns = import_patterns.get(lang_lower, [])

    if not patterns:
        logger.warning(
            "no_import_patterns",
            language=language,
            message=f"No import patterns defined for language: {language}"
        )
        return {}

    # Deduplicate file paths
    unique_files = list(set(file_paths))

    logger.info(
        "extracting_imports",
        file_count=len(unique_files),
        language=language,
        pattern_count=len(patterns)
    )

    file_imports: Dict[str, List[str]] = {}

    for file_path in unique_files:
        if not os.path.exists(file_path):
            logger.warning("file_not_found", file_path=file_path)
            continue

        imports: List[str] = []

        for pattern in patterns:
            try:
                # Run ast-grep to find imports
                result = subprocess.run(
                    ["ast-grep", "run", "--pattern", pattern, "--lang", language, "--json", file_path],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0 and result.stdout.strip():
                    matches = json.loads(result.stdout)
                    for match in matches:
                        import_text = match.get('text', '').strip()
                        if import_text and import_text not in imports:
                            imports.append(import_text)

            except subprocess.TimeoutExpired:
                logger.warning(
                    "import_extraction_timeout",
                    file_path=file_path,
                    pattern=pattern
                )
            except json.JSONDecodeError:
                # No matches for this pattern
                pass
            except Exception as e:
                logger.warning(
                    "import_extraction_error",
                    file_path=file_path,
                    pattern=pattern,
                    error=str(e)[:100]
                )

        if imports:
            file_imports[file_path] = sorted(imports)

    logger.info(
        "imports_extracted",
        files_with_imports=len(file_imports),
        total_imports=sum(len(v) for v in file_imports.values())
    )

    return file_imports


def detect_import_variations(
    file_imports: Dict[str, List[str]],
    language: str
) -> Dict[str, Any]:
    """Detect variations in import statements between files with duplicate code.

    Compares imports across files to identify differences that may need
    resolution when consolidating duplicates.

    Args:
        file_imports: Dictionary mapping file path to list of import statements
                     (output from extract_imports_from_files)
        language: Programming language for pattern-specific analysis

    Returns:
        Dictionary containing:
        - common_imports: Imports present in all files
        - unique_imports: Dict mapping file to imports only in that file
        - partial_imports: Imports with different specifiers (from x import a vs a,b)
        - aliasing_differences: Same module imported with different aliases
        - summary: Human-readable summary of variations
    """
    logger = get_logger("duplication.import_variations")

    if not file_imports:
        return {
            "common_imports": [],
            "unique_imports": {},
            "partial_imports": [],
            "aliasing_differences": [],
            "summary": "No imports to compare"
        }

    if len(file_imports) < 2:
        return {
            "common_imports": list(file_imports.values())[0] if file_imports else [],
            "unique_imports": {},
            "partial_imports": [],
            "aliasing_differences": [],
            "summary": "Only one file provided, no comparison possible"
        }

    logger.info(
        "detecting_import_variations",
        file_count=len(file_imports),
        language=language
    )

    # Parse imports into structured format for comparison
    def parse_import(import_str: str, lang: str) -> Dict[str, Any]:
        """Parse an import statement into structured components."""
        parsed: Dict[str, Any] = {
            "raw": import_str,
            "module": "",
            "names": [],
            "alias": None,
            "is_type_import": False,
            "is_star_import": False
        }

        lang_lower = lang.lower()

        if lang_lower == "python":
            # Handle "import x as y"
            if import_str.startswith("import ") and " as " in import_str:
                parts = import_str[7:].split(" as ")
                parsed["module"] = parts[0].strip()
                parsed["alias"] = parts[1].strip() if len(parts) > 1 else None
            # Handle "import x"
            elif import_str.startswith("import "):
                parsed["module"] = import_str[7:].strip()
            # Handle "from x import y, z" or "from x import (y, z)"
            elif import_str.startswith("from "):
                parts = import_str[5:].split(" import ")
                if len(parts) >= 2:
                    parsed["module"] = parts[0].strip()
                    names_str = parts[1].strip().strip("()")
                    # Parse individual names with potential aliases
                    for name in names_str.split(","):
                        name = name.strip()
                        if " as " in name:
                            orig, alias = name.split(" as ")
                            parsed["names"].append({"name": orig.strip(), "alias": alias.strip()})
                        else:
                            parsed["names"].append({"name": name, "alias": None})

        elif lang_lower in ("typescript", "javascript", "tsx", "jsx"):
            # Handle type imports
            if "import type" in import_str:
                parsed["is_type_import"] = True
                import_str = import_str.replace("import type", "import")

            # Handle "import * as x from 'y'"
            if "import * as " in import_str:
                parsed["is_star_import"] = True
                match = import_str.split(" as ")[1].split(" from ")
                if len(match) >= 2:
                    parsed["alias"] = match[0].strip()
                    parsed["module"] = match[1].strip().strip("'\"")
            # Handle "import { a, b } from 'x'"
            elif "{" in import_str and "}" in import_str:
                brace_start = import_str.index("{")
                brace_end = import_str.index("}")
                names_str = import_str[brace_start+1:brace_end]
                for name in names_str.split(","):
                    name = name.strip()
                    if " as " in name:
                        orig, alias = name.split(" as ")
                        parsed["names"].append({"name": orig.strip(), "alias": alias.strip()})
                    else:
                        parsed["names"].append({"name": name, "alias": None})
                # Extract module
                if " from " in import_str:
                    parsed["module"] = import_str.split(" from ")[1].strip().strip("'\"")
            # Handle "import x from 'y'"
            elif " from " in import_str:
                parts = import_str.replace("import ", "").split(" from ")
                if len(parts) >= 2:
                    parsed["alias"] = parts[0].strip()
                    parsed["module"] = parts[1].strip().strip("'\"")
            # Handle require()
            elif "require(" in import_str:
                if "= require(" in import_str:
                    parts = import_str.split("= require(")
                    name_part = parts[0].replace("const ", "").replace("let ", "").replace("var ", "").strip()
                    if "{" in name_part:
                        # Destructured require
                        names_str = name_part.strip("{}")
                        for name in names_str.split(","):
                            parsed["names"].append({"name": name.strip(), "alias": None})
                    else:
                        parsed["alias"] = name_part
                    parsed["module"] = parts[1].strip().strip("'\")")

        elif lang_lower == "go":
            # Handle 'import alias "package"'
            if import_str.startswith("import "):
                rest = import_str[7:].strip()
                if rest.startswith('"'):
                    parsed["module"] = rest.strip('"')
                else:
                    parts = rest.split(' "')
                    if len(parts) >= 2:
                        parsed["alias"] = parts[0].strip()
                        parsed["module"] = parts[1].strip('"')

        elif lang_lower == "rust":
            # Handle "use path as alias" or "use path::{a, b}"
            if import_str.startswith("use "):
                rest = import_str[4:].rstrip(";").strip()
                if " as " in rest:
                    parts = rest.split(" as ")
                    parsed["module"] = parts[0].strip()
                    parsed["alias"] = parts[1].strip()
                elif "::{" in rest:
                    parts = rest.split("::{")
                    parsed["module"] = parts[0].strip()
                    names_str = parts[1].rstrip("}")
                    for name in names_str.split(","):
                        parsed["names"].append({"name": name.strip(), "alias": None})
                else:
                    parsed["module"] = rest

        return parsed

    # Parse all imports
    parsed_imports: Dict[str, List[Dict[str, Any]]] = {}
    for file_path, imports in file_imports.items():
        parsed_imports[file_path] = [parse_import(imp, language) for imp in imports]

    # Find common imports (exact matches across all files)
    all_import_sets = [set(imports) for imports in file_imports.values()]
    common_imports = list(set.intersection(*all_import_sets)) if all_import_sets else []

    # Find unique imports per file
    unique_imports: Dict[str, List[str]] = {}
    for file_path, imports in file_imports.items():
        unique = [imp for imp in imports if imp not in common_imports]
        if unique:
            unique_imports[file_path] = unique

    # Detect partial imports (same module, different names imported)
    partial_imports: List[Dict[str, Any]] = []
    module_to_files: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}

    for file_path, parsed_list in parsed_imports.items():
        for parsed in parsed_list:
            module = parsed["module"]
            if module:
                if module not in module_to_files:
                    module_to_files[module] = []
                module_to_files[module].append((file_path, parsed))

    for module, file_parsed_list in module_to_files.items():
        if len(file_parsed_list) < 2:
            continue

        # Group by files and their imported names
        file_names: Dict[str, Set[str]] = {}
        for file_path, parsed in file_parsed_list:
            names = {n["name"] for n in parsed["names"]} if parsed["names"] else set()
            if file_path not in file_names:
                file_names[file_path] = set()
            file_names[file_path].update(names)

        # Check if different files import different names
        all_names = [names for names in file_names.values() if names]
        if len(all_names) >= 2:
            # Check for differences
            first_names = all_names[0]
            has_differences = any(names != first_names for names in all_names[1:])
            if has_differences:
                union_names = set.union(*all_names)
                intersection_names = set.intersection(*all_names)
                partial_imports.append({
                    "module": module,
                    "files": {fp: list(names) for fp, names in file_names.items() if names},
                    "common_names": list(intersection_names),
                    "all_names": list(union_names),
                    "missing_per_file": {
                        fp: list(union_names - names)
                        for fp, names in file_names.items()
                        if names and union_names - names
                    }
                })

    # Detect aliasing differences (same module, different alias)
    aliasing_differences: List[Dict[str, Any]] = []

    for module, file_parsed_list in module_to_files.items():
        if len(file_parsed_list) < 2:
            continue

        # Check for alias differences
        file_aliases: Dict[str, Optional[str]] = {}
        for file_path, parsed in file_parsed_list:
            alias = parsed["alias"]
            if file_path not in file_aliases:
                file_aliases[file_path] = alias

        # Check if there are different aliases
        unique_aliases = set(file_aliases.values())
        if len(unique_aliases) > 1:
            aliasing_differences.append({
                "module": module,
                "aliases": {fp: alias for fp, alias in file_aliases.items()},
                "recommendation": "Standardize on a single alias when consolidating"
            })

    # Generate summary
    summary_parts = []
    if common_imports:
        summary_parts.append(f"{len(common_imports)} common import(s)")
    if unique_imports:
        total_unique = sum(len(v) for v in unique_imports.values())
        summary_parts.append(f"{total_unique} unique import(s) across {len(unique_imports)} file(s)")
    if partial_imports:
        summary_parts.append(f"{len(partial_imports)} module(s) with partial import differences")
    if aliasing_differences:
        summary_parts.append(f"{len(aliasing_differences)} module(s) with aliasing differences")

    summary = "; ".join(summary_parts) if summary_parts else "No import variations detected"

    logger.info(
        "import_variations_detected",
        common_count=len(common_imports),
        unique_files=len(unique_imports),
        partial_count=len(partial_imports),
        aliasing_count=len(aliasing_differences)
    )

    return {
        "common_imports": sorted(common_imports),
        "unique_imports": unique_imports,
        "partial_imports": partial_imports,
        "aliasing_differences": aliasing_differences,
        "summary": summary
    }


def generate_import_statement(
    module_path: str,
    items: list[str],
    language: str,
    default_import: Optional[str] = None,
    use_require: bool = False
) -> str:
    """Generate an import statement for the specified language.

    Creates properly formatted import statements for various programming languages,
    supporting both named imports and default imports.

    Args:
        module_path: The module or package path to import from
        items: List of items to import (named imports)
        language: Programming language (python, typescript, javascript, java, go, rust)
        default_import: Optional default import name (for JS/TS default exports)
        use_require: If True, use CommonJS require() syntax for JavaScript

    Returns:
        Formatted import statement string for the specified language

    Examples:
        >>> generate_import_statement("os.path", ["join", "dirname"], "python")
        'from os.path import join, dirname'

        >>> generate_import_statement("react", ["useState", "useEffect"], "typescript")
        "import { useState, useEffect } from 'react'"

        >>> generate_import_statement("react", [], "typescript", default_import="React")
        "import React from 'react'"

        >>> generate_import_statement("com.example.util", ["StringUtils"], "java")
        'import com.example.util.StringUtils;'
    """
    lang_lower = language.lower()

    if lang_lower == "python":
        if not items:
            return f"import {module_path}"
        elif len(items) == 1 and items[0] == "*":
            return f"from {module_path} import *"
        else:
            items_str = ", ".join(items)
            return f"from {module_path} import {items_str}"

    elif lang_lower in ("typescript", "javascript", "tsx", "jsx"):
        if use_require and lang_lower in ("javascript", "jsx"):
            if not items and default_import:
                return f"const {default_import} = require('{module_path}')"
            elif items:
                items_str = ", ".join(items)
                return f"const {{ {items_str} }} = require('{module_path}')"
            else:
                return f"require('{module_path}')"
        else:
            parts = []
            if default_import and items:
                items_str = ", ".join(items)
                parts.append(f"import {default_import}, {{ {items_str} }} from '{module_path}'")
            elif default_import:
                parts.append(f"import {default_import} from '{module_path}'")
            elif items:
                if len(items) == 1 and items[0] == "*":
                    alias = module_path.split("/")[-1].replace("-", "_").replace(".", "_")
                    parts.append(f"import * as {alias} from '{module_path}'")
                else:
                    items_str = ", ".join(items)
                    parts.append(f"import {{ {items_str} }} from '{module_path}'")
            else:
                parts.append(f"import '{module_path}'")
            return parts[0] if parts else f"import '{module_path}'"

    elif lang_lower == "java":
        if not items or (len(items) == 1 and items[0] == "*"):
            return f"import {module_path}.*;"
        else:
            statements = [f"import {module_path}.{item};" for item in items]
            return "\n".join(statements)

    elif lang_lower == "go":
        if default_import:
            return f'import {default_import} "{module_path}"'
        else:
            return f'import "{module_path}"'

    elif lang_lower == "rust":
        if not items:
            return f"use {module_path};"
        elif len(items) == 1:
            if items[0] == "*":
                return f"use {module_path}::*;"
            else:
                return f"use {module_path}::{items[0]};"
        else:
            items_str = ", ".join(items)
            return f"use {module_path}::{{{items_str}}};"

    elif lang_lower in ("c", "cpp", "c++"):
        if module_path.startswith("<") or module_path.endswith(">"):
            return f"#include {module_path}"
        elif module_path.endswith(".h") or module_path.endswith(".hpp"):
            return f'#include "{module_path}"'
        else:
            return f"#include <{module_path}>"

    elif lang_lower == "csharp" or lang_lower == "c#":
        if items:
            statements = [f"using static {module_path}.{item};" for item in items]
            return "\n".join(statements)  # C# static imports
        else:
            return f"using {module_path};"

    else:
        if items:
            items_str = ", ".join(items)
            return f"// Import {items_str} from {module_path}"
        else:
            return f"// Import {module_path}"


def analyze_import_overlap(
    file_imports: Dict[str, List[str]],
    duplicate_code: Optional[str] = None
) -> Dict[str, Any]:
    """Analyze import overlap across files containing duplicate code.

    Identifies shared imports (common to all files), unique imports per file,
    calculates overlap statistics, and identifies imports likely needed for
    extracted duplicate code.

    Args:
        file_imports: Dictionary mapping file paths to their import statements
                     (output from extract_imports_from_files)
        duplicate_code: Optional code snippet to analyze for required imports

    Returns:
        Dictionary containing:
            - shared_imports: List of imports common to all files
            - unique_imports_by_file: Dict mapping file path to unique imports
            - overlap_percentage: Percentage of imports that are shared
            - required_imports: Imports likely needed for duplicate code
            - total_unique_imports: Count of all unique import statements
            - analysis_summary: Human-readable summary
    """
    logger = get_logger("duplication.import_analysis")

    if not file_imports:
        return {
            "shared_imports": [],
            "unique_imports_by_file": {},
            "overlap_percentage": 0.0,
            "required_imports": [],
            "total_unique_imports": 0,
            "analysis_summary": "No imports to analyze"
        }

    # Convert lists to sets for efficient operations
    import_sets: Dict[str, Set[str]] = {
        file_path: set(imports)
        for file_path, imports in file_imports.items()
    }

    # Get all unique imports across all files
    all_imports: Set[str] = set()
    for imports in import_sets.values():
        all_imports.update(imports)

    total_unique_imports = len(all_imports)

    if not all_imports:
        return {
            "shared_imports": [],
            "unique_imports_by_file": {},
            "overlap_percentage": 0.0,
            "required_imports": [],
            "total_unique_imports": 0,
            "analysis_summary": "No imports found in any file"
        }

    # Find shared imports (present in ALL files)
    if len(import_sets) == 1:
        shared_imports = sorted(list(list(import_sets.values())[0]))
    else:
        shared_imports_set = set.intersection(*import_sets.values())
        shared_imports = sorted(list(shared_imports_set))

    # Find unique imports per file (not in any other file)
    unique_imports_by_file: Dict[str, List[str]] = {}
    for file_path, file_import_set in import_sets.items():
        other_imports: Set[str] = set()
        for other_path, other_set in import_sets.items():
            if other_path != file_path:
                other_imports.update(other_set)
        unique = file_import_set - other_imports
        if unique:
            unique_imports_by_file[file_path] = sorted(list(unique))

    # Calculate overlap percentage
    overlap_percentage = (len(shared_imports) / total_unique_imports * 100) if total_unique_imports > 0 else 0.0

    # Identify imports likely required for duplicate code
    required_imports: List[str] = []
    if duplicate_code:
        required_imports = _identify_required_imports(duplicate_code, all_imports, shared_imports)

    # Generate analysis summary
    file_count = len(file_imports)
    summary_parts = [
        f"Analyzed {total_unique_imports} unique imports across {file_count} files.",
        f"{len(shared_imports)} imports shared by all files ({overlap_percentage:.1f}% overlap).",
    ]
    unique_count = sum(len(v) for v in unique_imports_by_file.values())
    if unique_count > 0:
        summary_parts.append(f"{unique_count} imports unique to specific files.")
    if required_imports:
        summary_parts.append(f"{len(required_imports)} imports likely needed for extracted function.")

    logger.info(
        "import_overlap_analyzed",
        file_count=file_count,
        total_unique_imports=total_unique_imports,
        shared_count=len(shared_imports),
        overlap_percentage=round(overlap_percentage, 1),
        required_count=len(required_imports)
    )

    return {
        "shared_imports": shared_imports,
        "unique_imports_by_file": unique_imports_by_file,
        "overlap_percentage": round(overlap_percentage, 1),
        "required_imports": required_imports,
        "total_unique_imports": total_unique_imports,
        "analysis_summary": " ".join(summary_parts)
    }


def _identify_required_imports(code: str, all_imports: Set[str], shared_imports: List[str]) -> List[str]:
    """Identify imports likely required by a code snippet."""
    import re
    required: List[str] = []
    identifiers = set(re.findall(r'\b([A-Za-z_][A-Za-z0-9_]*)\b', code))
    keywords = {
        'if', 'else', 'for', 'while', 'return', 'def', 'class', 'import', 'from', 'as',
        'try', 'except', 'finally', 'with', 'yield', 'raise', 'pass', 'break', 'continue',
        'and', 'or', 'not', 'in', 'is', 'None', 'True', 'False', 'lambda', 'global',
        'nonlocal', 'assert', 'del', 'elif', 'async', 'await', 'let', 'const', 'var',
        'function', 'new', 'this', 'self', 'super', 'static', 'public', 'private',
        'protected', 'void', 'int', 'str', 'bool', 'float', 'list', 'dict', 'set', 'tuple'
    }
    identifiers = identifiers - keywords
    checked_imports = list(shared_imports) + [imp for imp in all_imports if imp not in shared_imports]
    for import_stmt in checked_imports:
        imported_names = _extract_imported_names(import_stmt)
        if imported_names & identifiers and import_stmt not in required:
            required.append(import_stmt)
    return required


def _extract_imported_names(import_stmt: str) -> Set[str]:
    """Extract the names made available by an import statement."""
    import re
    names: Set[str] = set()

    # Python: import module
    if match := re.match(r'^import\s+([\w.]+)(?:\s+as\s+(\w+))?', import_stmt):
        names.add(match.group(2) if match.group(2) else match.group(1).split('.')[0])
        return names

    # Python: from module import names
    if match := re.match(r'^from\s+[\w.]+\s+import\s+(.+)$', import_stmt):
        for item in match.group(1).strip('()').split(','):
            item = item.strip()
            if ' as ' in item:
                names.add(item.split(' as ')[1].strip())
            elif item and item != '*':
                names.add(item.strip())
        return names

    # TypeScript/JavaScript: import name from 'source'
    if match := re.match(r'^import\s+(\w+)\s+from', import_stmt):
        names.add(match.group(1))
        return names

    # TypeScript/JavaScript: import { a, b } from 'source'
    if match := re.match(r'^import\s*(?:type\s*)?\{([^}]+)\}\s*from', import_stmt):
        for item in match.group(1).split(','):
            item = item.strip()
            names.add(item.split(' as ')[1].strip() if ' as ' in item else item)
        return names

    # TypeScript/JavaScript: import * as name from 'source'
    if match := re.match(r'^import\s*\*\s*as\s+(\w+)\s+from', import_stmt):
        names.add(match.group(1))
        return names

    # Go: import "package" or import alias "package"
    if match := re.match(r'^import\s+(?:(\w+)\s+)?"([^"]+)"', import_stmt):
        names.add(match.group(1) if match.group(1) else match.group(2).split('/')[-1])
        return names

    # Java/C#: using/import namespace
    if match := re.match(r'^(?:using|import)\s+(?:static\s+)?([\w.]+);?', import_stmt):
        names.add(match.group(1).split('.')[-1])
        return names

    # Rust: use path::name
    if match := re.match(r'^use\s+([\w:]+)(?:\s+as\s+(\w+))?;?', import_stmt):
        names.add(match.group(2) if match.group(2) else match.group(1).split('::')[-1])
        return names

    # Ruby/PHP: require 'file'
    if match := re.match(r'^(?:require|require_relative|include)\s+[\'"]([^\'"]+)[\'"]', import_stmt):
        names.add(match.group(1).split('/')[-1].rsplit('.', 1)[0])
        return names

    return names


def detect_internal_dependencies(
    code: str,
    file_path: str,
    language: str,
    file_imports: Dict[str, List[str]]
) -> Dict[str, List[str]]:
    """Detect internal dependencies (function calls) within duplicate code.

    Analyzes duplicate code blocks to identify function/method calls that would
    need to be passed as parameters or imported when extracting to a shared utility.

    Args:
        code: The duplicate code block to analyze
        file_path: Path to the file containing the code
        language: Programming language for pattern matching
        file_imports: Dictionary mapping file paths to their import statements

    Returns:
        Dictionary with three categories:
        - local_calls: Functions defined in the same file
        - imported_calls: Functions from imported modules
        - unresolved_calls: Calls that couldn't be resolved to a source
    """
    import re
    logger = get_logger("duplication.dependencies")

    result: Dict[str, List[str]] = {
        "local_calls": [],
        "imported_calls": [],
        "unresolved_calls": []
    }

    call_patterns: Dict[str, List[str]] = {
        "python": ["$FUNC($$$)", "$OBJ.$METHOD($$$)", "await $FUNC($$$)"],
        "typescript": ["$FUNC($$$)", "$OBJ.$METHOD($$$)", "await $FUNC($$$)", "new $CLASS($$$)"],
        "javascript": ["$FUNC($$$)", "$OBJ.$METHOD($$$)", "await $FUNC($$$)", "new $CLASS($$$)"],
        "tsx": ["$FUNC($$$)", "$OBJ.$METHOD($$$)", "await $FUNC($$$)", "new $CLASS($$$)"],
        "jsx": ["$FUNC($$$)", "$OBJ.$METHOD($$$)", "await $FUNC($$$)", "new $CLASS($$$)"],
        "java": ["$FUNC($$$)", "$OBJ.$METHOD($$$)", "new $CLASS($$$)"],
        "go": ["$FUNC($$$)", "$PKG.$FUNC($$$)"],
        "rust": ["$FUNC($$$)", "$OBJ.$METHOD($$$)", "$MODULE::$FUNC($$$)"],
    }

    lang_lower = language.lower()
    patterns = call_patterns.get(lang_lower, call_patterns.get("python", []))

    if not patterns:
        logger.warning("no_call_patterns", language=language)
        return result

    all_calls: List[str] = []

    for pattern in patterns:
        try:
            proc_result = subprocess.run(
                ["ast-grep", "run", "--pattern", pattern, "--lang", language, "--json"],
                input=code, capture_output=True, text=True, timeout=30
            )

            if proc_result.returncode == 0 and proc_result.stdout.strip():
                matches = json.loads(proc_result.stdout)
                for match in matches:
                    match_text = match.get('text', '').strip()
                    if match_text:
                        cleaned = re.sub(r'^(await|new)\s+', '', match_text)
                        name_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s*\(', cleaned)
                        if name_match:
                            full_name = name_match.group(1)
                            call_name = full_name.split('.')[-1] if '.' in full_name else full_name
                            if call_name and call_name not in all_calls:
                                all_calls.append(call_name)

        except subprocess.TimeoutExpired:
            logger.warning("call_detection_timeout", pattern=pattern)
        except json.JSONDecodeError:
            pass
        except Exception as e:
            logger.warning("call_detection_error", pattern=pattern, error=str(e)[:100])

    if not all_calls:
        logger.info("no_calls_detected", code_length=len(code))
        return result

    imports = file_imports.get(file_path, [])
    local_functions = _get_local_function_names(file_path, language)

    for call_name in all_calls:
        if call_name in local_functions:
            if call_name not in result["local_calls"]:
                result["local_calls"].append(call_name)
        elif _is_imported_call(call_name, imports, language):
            if call_name not in result["imported_calls"]:
                result["imported_calls"].append(call_name)
        elif not _is_builtin(call_name, language):
            if call_name not in result["unresolved_calls"]:
                result["unresolved_calls"].append(call_name)

    logger.info(
        "dependencies_detected", file=file_path,
        local_calls=len(result["local_calls"]),
        imported_calls=len(result["imported_calls"]),
        unresolved_calls=len(result["unresolved_calls"])
    )

    return result


def _get_local_function_names(file_path: str, language: str) -> List[str]:
    """Get all function/method names defined in a file."""
    logger = get_logger("duplication.local_functions")

    if not os.path.exists(file_path):
        return []

    func_patterns: Dict[str, List[str]] = {
        "python": ["def $NAME($$$):", "async def $NAME($$$):"],
        "typescript": ["function $NAME($$$)", "const $NAME = ($$$) =>"],
        "javascript": ["function $NAME($$$)", "const $NAME = ($$$) =>"],
        "tsx": ["function $NAME($$$)", "const $NAME = ($$$) =>"],
        "jsx": ["function $NAME($$$)", "const $NAME = ($$$) =>"],
        "java": ["$RET $NAME($$$) {"],
        "go": ["func $NAME($$$)", "func ($RECV) $NAME($$$)"],
        "rust": ["fn $NAME($$$)", "pub fn $NAME($$$)"],
    }

    lang_lower = language.lower()
    patterns = func_patterns.get(lang_lower, func_patterns.get("python", []))
    functions: List[str] = []

    for pattern in patterns:
        try:
            result = subprocess.run(
                ["ast-grep", "run", "--pattern", pattern, "--lang", language, "--json", file_path],
                capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0 and result.stdout.strip():
                matches = json.loads(result.stdout)
                for match in matches:
                    meta_vars = match.get('metaVariables', {})
                    name_var = meta_vars.get('single', {}).get('NAME', {})
                    func_name = name_var.get('text', '')
                    if func_name and func_name not in functions:
                        functions.append(func_name)

        except Exception as e:
            logger.debug("function_extraction_error", file_path=file_path, error=str(e)[:100])

    return functions


def _is_imported_call(call_name: str, imports: List[str], language: str) -> bool:
    """Check if a call name matches something from the imports."""
    import re

    for import_stmt in imports:
        if language.lower() == "python":
            if f"import {call_name}" in import_stmt:
                return True
            match = re.search(r'from\s+\S+\s+import\s+(.+)', import_stmt)
            if match:
                imported_names = [n.strip().split(' as ')[0] for n in match.group(1).split(',')]
                if call_name in imported_names:
                    return True
        elif language.lower() in ["javascript", "typescript", "tsx", "jsx"]:
            if f"import {call_name}" in import_stmt:
                return True
            match = re.search(r'import\s*\{([^}]+)\}', import_stmt)
            if match:
                imported_names = [n.strip().split(' as ')[0] for n in match.group(1).split(',')]
                if call_name in imported_names:
                    return True
        elif call_name in import_stmt:
            return True

    return False


def _is_builtin(name: str, language: str) -> bool:
    """Check if a name is a language builtin."""
    builtins: Dict[str, Set[str]] = {
        "python": {
            "print", "len", "range", "str", "int", "float", "list", "dict", "set",
            "tuple", "bool", "type", "isinstance", "hasattr", "getattr", "setattr",
            "open", "input", "format", "sorted", "reversed", "enumerate", "zip",
            "map", "filter", "sum", "min", "max", "abs", "round", "all", "any",
            "ord", "chr", "repr", "id", "hash", "dir", "vars", "super",
        },
        "javascript": {
            "console", "parseInt", "parseFloat", "isNaN", "eval", "Array", "Object",
            "String", "Number", "Boolean", "Date", "Math", "JSON", "Promise", "Map",
            "Set", "Error", "setTimeout", "setInterval", "clearTimeout", "fetch",
        },
        "typescript": {
            "console", "parseInt", "parseFloat", "isNaN", "eval", "Array", "Object",
            "String", "Number", "Boolean", "Date", "Math", "JSON", "Promise", "Map",
            "Set", "Error", "setTimeout", "setInterval", "clearTimeout", "fetch",
        },
        "go": {"make", "new", "len", "cap", "append", "copy", "delete", "close", "panic"},
        "rust": {"println", "print", "format", "vec", "panic", "assert"},
        "java": {"System", "String", "Integer", "Long", "Double", "Float", "Math", "Arrays"},
    }

    lang_lower = language.lower()
    lang_builtins = builtins.get(lang_lower, set())

    if lang_lower in ["tsx", "jsx"]:
        lang_builtins = builtins.get("javascript", set()) | builtins.get("typescript", set())

    return name in lang_builtins


def resolve_import_path(
    source_file: str,
    target_file: str,
    language: str,
    prefer_relative: bool = True
) -> str:
    """Calculate the import path from source file to target file.

    Generates the appropriate import path based on language conventions:
    - Python: relative (from .module import X) or absolute (from package.module import X)
    - TypeScript/JavaScript: relative (./path) or absolute (@package/path)
    - Java: always absolute (package.Class)

    Args:
        source_file: Path to the file that will contain the import
        target_file: Path to the file being imported
        language: Programming language (python, typescript, javascript, java, etc.)
        prefer_relative: If True, prefer relative imports where supported

    Returns:
        Import path string appropriate for the language

    Examples:
        >>> resolve_import_path("/src/utils/helper.py", "/src/models/user.py", "python")
        "from ..models.user import user"
        >>> resolve_import_path("/src/index.ts", "/src/utils/helper.ts", "typescript")
        "./utils/helper"
    """
    source_path = os.path.abspath(source_file)
    target_path = os.path.abspath(target_file)

    source_dir = os.path.dirname(source_path)
    target_dir = os.path.dirname(target_path)
    target_basename = os.path.splitext(os.path.basename(target_path))[0]

    lang_lower = language.lower()

    # Java always uses absolute package paths
    if lang_lower == "java":
        # Extract package from file path (e.g., src/main/java/com/example/MyClass.java)
        # Look for common Java source roots
        java_roots = ["src/main/java/", "src/test/java/", "src/", "java/"]
        package_path = target_path

        for root in java_roots:
            if root in target_path:
                package_path = target_path.split(root, 1)[-1]
                break

        # Convert path to package notation
        package_parts = package_path.replace(os.sep, "/").replace("/", ".").rsplit(".", 1)
        if len(package_parts) > 1:
            return package_parts[0]  # Remove file extension
        return target_basename

    # Python imports
    if lang_lower == "python":
        if prefer_relative:
            # Calculate relative path
            rel_path = os.path.relpath(target_dir, source_dir)

            if rel_path == ".":
                # Same directory
                return f"from .{target_basename} import {target_basename}"
            elif rel_path.startswith(".."):
                # Parent directory or sibling
                dots = rel_path.count("..") + 1
                remaining = rel_path.replace("..", "").strip(os.sep)
                if remaining:
                    module_path = remaining.replace(os.sep, ".")
                    return f"from {'.' * dots}{module_path}.{target_basename} import {target_basename}"
                else:
                    return f"from {'.' * dots}{target_basename} import {target_basename}"
            else:
                # Subdirectory
                module_path = rel_path.replace(os.sep, ".")
                return f"from .{module_path}.{target_basename} import {target_basename}"
        else:
            # Absolute import - try to find package root
            # Look for __init__.py to determine package boundaries
            package_parts = []
            current = target_dir
            while current and current != os.path.dirname(current):
                init_file = os.path.join(current, "__init__.py")
                if os.path.exists(init_file):
                    package_parts.insert(0, os.path.basename(current))
                    current = os.path.dirname(current)
                else:
                    break

            if package_parts:
                package_path = ".".join(package_parts)
                return f"from {package_path}.{target_basename} import {target_basename}"
            else:
                return f"import {target_basename}"

    # TypeScript/JavaScript imports
    if lang_lower in ["typescript", "javascript", "tsx", "jsx"]:
        if prefer_relative:
            rel_path = os.path.relpath(target_path, source_dir)
            # Normalize to forward slashes
            rel_path = rel_path.replace(os.sep, "/")
            # Remove file extension
            rel_path = os.path.splitext(rel_path)[0]
            # Ensure relative path prefix
            if not rel_path.startswith("."):
                rel_path = "./" + rel_path
            return rel_path
        else:
            # Absolute import - try to find package.json to determine package name
            # Look for common patterns like @scope/package or src/ aliases
            package_json_path = None
            current = target_dir
            while current and current != os.path.dirname(current):
                pj = os.path.join(current, "package.json")
                if os.path.exists(pj):
                    package_json_path = current
                    break
                current = os.path.dirname(current)

            if package_json_path:
                # Get relative path from package root
                rel_from_pkg = os.path.relpath(target_path, package_json_path)
                rel_from_pkg = rel_from_pkg.replace(os.sep, "/")
                rel_from_pkg = os.path.splitext(rel_from_pkg)[0]

                # Check for common path aliases (src -> @/)
                if rel_from_pkg.startswith("src/"):
                    return "@/" + rel_from_pkg[4:]

                return rel_from_pkg
            else:
                # Fall back to relative
                rel_path = os.path.relpath(target_path, source_dir)
                rel_path = rel_path.replace(os.sep, "/")
                rel_path = os.path.splitext(rel_path)[0]
                if not rel_path.startswith("."):
                    rel_path = "./" + rel_path
                return rel_path

    # Default fallback for other languages
    rel_path = os.path.relpath(target_path, source_dir)
    return rel_path.replace(os.sep, "/")


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

        with sentry_sdk.start_span(op="subprocess.run", name=f"Running {args[0]}") as span:
            span.set_data("command", sanitized_args[0])
            span.set_data("has_stdin", has_stdin)

            result = subprocess.run(
                args,
                capture_output=True,
                input=input_text,
                text=True,
                check=True,  # Raises CalledProcessError if return code is non-zero
                shell=use_shell
            )

            span.set_data("returncode", result.returncode)

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

        error = AstGrepExecutionError(
            command=args,
            returncode=e.returncode,
            stderr=stderr_msg
        )
        sentry_sdk.capture_exception(error, extras={
            "command": " ".join(args),
            "returncode": e.returncode,
            "stderr": stderr_msg[:500],
            "execution_time_seconds": round(execution_time, 3),
            "has_stdin": has_stdin
        })
        raise error from e
    except FileNotFoundError as e:
        execution_time = time.time() - start_time

        logger.error(
            "command_not_found",
            command=args[0],
            execution_time_seconds=round(execution_time, 3)
        )

        if args[0] == "ast-grep":
            not_found_error = AstGrepNotFoundError()
            sentry_sdk.capture_exception(not_found_error, extras={"command": " ".join(args)})
            raise not_found_error from e
        not_found_error = AstGrepNotFoundError(f"Command '{args[0]}' not found")
        sentry_sdk.capture_exception(not_found_error, extras={"command": " ".join(args)})
        raise not_found_error from e

def filter_files_by_size(
    directory: str,
    max_size_mb: Optional[int] = None,
    language: Optional[str] = None
) -> Tuple[List[str], List[str]]:
    """Filter files in directory by size.

    Args:
        directory: Directory to search
        max_size_mb: Maximum file size in megabytes (None = unlimited)
        language: Optional language filter for file extensions

    Returns:
        Tuple of (files_to_search, skipped_files)
        - files_to_search: List of file paths under size limit
        - skipped_files: List of file paths that were skipped
    """
    logger = get_logger("file_filter")

    if max_size_mb is None or max_size_mb <= 0:
        # No filtering needed
        return ([], [])

    max_size_bytes = max_size_mb * 1024 * 1024
    files_to_search: List[str] = []
    skipped_files: List[str] = []

    # Get language extensions if specified
    lang_extensions: Optional[List[str]] = None
    if language:
        # Common extensions by language (simplified)
        lang_map = {
            'python': ['.py', '.pyi'],
            'javascript': ['.js', '.jsx', '.mjs'],
            'typescript': ['.ts', '.tsx'],
            'java': ['.java'],
            'rust': ['.rs'],
            'go': ['.go'],
            'c': ['.c', '.h'],
            'cpp': ['.cpp', '.hpp', '.cc', '.cxx', '.h'],
            'ruby': ['.rb'],
            'php': ['.php'],
            'swift': ['.swift'],
            'kotlin': ['.kt', '.kts'],
        }
        lang_extensions = lang_map.get(language.lower())

    # Walk directory and check file sizes
    for root, dirs, files in os.walk(directory):
        # Skip hidden directories and common ignore patterns
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', '.venv', 'build', 'dist']]

        for file in files:
            # Skip hidden files
            if file.startswith('.'):
                continue

            # Check language filter
            if lang_extensions:
                if not any(file.endswith(ext) for ext in lang_extensions):
                    continue

            file_path = os.path.join(root, file)

            try:
                file_size = os.path.getsize(file_path)

                if file_size > max_size_bytes:
                    skipped_files.append(file_path)
                    logger.debug(
                        "file_skipped_size",
                        file=file_path,
                        size_mb=round(file_size / (1024 * 1024), 2),
                        max_size_mb=max_size_mb
                    )
                else:
                    files_to_search.append(file_path)

            except OSError as e:
                # Skip files we can't stat
                logger.debug("file_stat_error", file=file_path, error=str(e))
                continue

    if skipped_files:
        logger.info(
            "files_filtered_by_size",
            total_files=len(files_to_search) + len(skipped_files),
            files_to_search=len(files_to_search),
            skipped_files=len(skipped_files),
            max_size_mb=max_size_mb
        )

    return (files_to_search, skipped_files)

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
                    sentry_sdk.capture_exception(e)
                    sentry_sdk.add_breadcrumb(
                        message="JSON parse error in ast-grep stream",
                        category="ast-grep.stream",
                        level="warning",
                        data={"line_preview": line[:100]}
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

            error = AstGrepExecutionError(
                command=full_command,
                returncode=returncode,
                stderr=stderr_output
            )
            sentry_sdk.capture_exception(error, extras={
                "command": " ".join(full_command),
                "returncode": returncode,
                "stderr": stderr_output[:500],
                "execution_time_seconds": round(execution_time, 3),
                "match_count": match_count
            })
            raise error

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
            not_found_error = AstGrepNotFoundError()
            sentry_sdk.capture_exception(not_found_error, extras={"command": " ".join(full_command)})
            raise not_found_error from e
        not_found_error = AstGrepNotFoundError(f"Command '{full_command[0]}' not found")
        sentry_sdk.capture_exception(not_found_error, extras={"command": " ".join(full_command)})
        raise not_found_error from e

    finally:
        # Ensure subprocess is cleaned up
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

# ============================================================================
# Syntax Validators
# ============================================================================

def validate_python_syntax(code: str) -> tuple[bool, str | None]:
    """Validate Python code syntax using the ast module.

    Uses ast.parse() to check if the provided code is syntactically valid Python.
    This validates the code without executing it.

    Args:
        code: Python source code string to validate

    Returns:
        A tuple of (is_valid, error_message):
        - (True, None) if the code is syntactically valid
        - (False, error_message) if invalid, with detailed error including
          line number and column position

    Examples:
        >>> validate_python_syntax("x = 1")
        (True, None)
        >>> valid, err = validate_python_syntax("def foo(")
        >>> valid
        False
        >>> "line 1" in err.lower()
        True
    """
    import ast

    try:
        ast.parse(code)
        return (True, None)
    except SyntaxError as e:
        # Build detailed error message with line and column info
        line_info = f"line {e.lineno}" if e.lineno else "unknown line"
        col_info = f", column {e.offset}" if e.offset else ""
        error_msg = f"SyntaxError at {line_info}{col_info}: {e.msg}"

        # Include the problematic text if available
        if e.text:
            error_msg += f"\n  {e.text.rstrip()}"
            if e.offset:
                error_msg += f"\n  {' ' * (e.offset - 1)}^"

        return (False, error_msg)


def validate_javascript_syntax(code: str) -> tuple[bool, str | None]:
    """Validate JavaScript syntax using Node.js.

    Uses Node.js vm module to parse JavaScript code and check for syntax errors.
    Supports ES6+ syntax including modules, async/await, and modern features.

    Args:
        code: JavaScript source code to validate

    Returns:
        A tuple of (is_valid, error_message):
        - (True, None) if the code is syntactically valid
        - (False, error_message) if invalid, with detailed error including
          line number when available

    Examples:
        >>> validate_javascript_syntax("const x = 1;")
        (True, None)
        >>> valid, err = validate_javascript_syntax("const x = ")
        >>> valid
        False
    """
    try:
        # Use Node.js vm module to parse code - supports ES6+ syntax
        node_code = f"""
const vm = require('vm');
try {{
    new vm.Script({json.dumps(code)}, {{ filename: 'validate.js' }});
    process.exit(0);
}} catch(e) {{
    // Parse the error for line/column info
    const lineMatch = e.stack && e.stack.match(/:(\d+)(?::\\d+)?/);
    let errorMsg = e.message;
    if (lineMatch) {{
        errorMsg = `Line ${{lineMatch[1]}}: ${{errorMsg}}`;
    }}
    console.error(errorMsg);
    process.exit(1);
}}
"""
        result = subprocess.run(
            ["node", "-e", node_code],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return (True, None)
        else:
            error_msg = result.stderr.strip() or result.stdout.strip()
            return (False, error_msg if error_msg else "Unknown syntax error")

    except FileNotFoundError:
        return (False, "Node.js not found - install Node.js for JavaScript validation")
    except subprocess.TimeoutExpired:
        return (False, "Validation timed out")
    except Exception as e:
        return (False, f"Validation error: {str(e)}")


def validate_typescript_syntax(code: str) -> tuple[bool, str | None]:
    """Validate TypeScript syntax using tsc (TypeScript compiler).

    Uses the TypeScript compiler to check syntax without emitting output.
    Validates type annotations, interfaces, generics, and TypeScript-specific syntax.

    Args:
        code: TypeScript source code to validate

    Returns:
        A tuple of (is_valid, error_message):
        - (True, None) if the code is syntactically valid
        - (False, error_message) if invalid, with detailed error including
          line and column numbers

    Examples:
        >>> validate_typescript_syntax("const x: number = 1;")
        (True, None)
        >>> valid, err = validate_typescript_syntax("const x: = 1;")
        >>> valid
        False
    """
    import tempfile
    import re

    try:
        # Write code to a temporary file for tsc to check
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.ts',
            delete=False,
            encoding='utf-8'
        ) as tmp_file:
            tmp_file.write(code)
            tmp_path = tmp_file.name

        try:
            # Run tsc with --noEmit to check syntax without generating output
            result = subprocess.run(
                [
                    "tsc",
                    "--noEmit",
                    "--skipLibCheck",
                    "--target", "ES2020",
                    "--module", "ESNext",
                    "--moduleResolution", "node",
                    "--esModuleInterop",
                    tmp_path
                ],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return (True, None)
            else:
                # Parse tsc error output for meaningful messages
                error_output = result.stdout.strip() or result.stderr.strip()

                if not error_output:
                    return (False, "Unknown TypeScript syntax error")

                # Extract errors with line info
                # tsc format: file.ts(line,col): error TS####: message
                lines = error_output.split('\n')
                errors = []

                for line in lines:
                    # Match pattern like: validate.ts(5,10): error TS1005: ';' expected.
                    match = re.match(r'.*?\((\d+),(\d+)\):\s*error\s+TS\d+:\s*(.+)', line)
                    if match:
                        line_num, col, msg = match.groups()
                        errors.append(f"Line {line_num}, Col {col}: {msg}")
                    elif line.strip() and not line.startswith(' '):
                        # Fallback for other error formats
                        errors.append(line.strip())

                if errors:
                    # Return first few errors to keep message concise
                    return (False, "; ".join(errors[:3]))
                else:
                    return (False, error_output[:500])

        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    except FileNotFoundError:
        return (False, "TypeScript compiler (tsc) not found - install with: npm install -g typescript")
    except subprocess.TimeoutExpired:
        return (False, "Validation timed out")
    except Exception as e:
        return (False, f"Validation error: {str(e)}")


# ============================================================================
# Syntax Validation for Code Rewrites
# ============================================================================

def validate_syntax(file_path: str, language: str) -> Dict[str, Any]:
    """Validate syntax of a rewritten file.

    Args:
        file_path: Absolute path to the file to validate
        language: Programming language (python, javascript, typescript, etc.)

    Returns:
        Dict with 'valid' (bool), 'error' (str if invalid), 'language' (str)
    """
    result: Dict[str, Any] = {
        "file": file_path,
        "language": language,
        "valid": True,
        "error": None
    }

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Python syntax validation
        if language == "python":
            try:
                compile(content, file_path, 'exec')
            except SyntaxError as e:
                result["valid"] = False
                result["error"] = f"Line {e.lineno}: {e.msg}"
                return result

        # JavaScript/TypeScript validation (using external validator if available)
        elif language in ["javascript", "typescript", "tsx", "jsx"]:
            # Try using node if available
            try:
                node_code = f"""
try {{
    new Function({json.dumps(content)});
    console.log("VALID");
}} catch(e) {{
    console.log("INVALID: " + e.message);
}}
"""
                node_result = subprocess.run(
                    ["node", "-e", node_code],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if "INVALID:" in node_result.stdout:
                    result["valid"] = False
                    result["error"] = node_result.stdout.replace("INVALID: ", "").strip()
                    return result
            except (FileNotFoundError, subprocess.TimeoutExpired):
                # Node not available or timeout - skip validation
                result["error"] = f"Validation skipped (node not available for {language})"
                pass

        # For other languages, check for basic syntax patterns that indicate errors
        # This is a basic check - won't catch all syntax errors
        else:
            # Check for obviously malformed code (unmatched braces, etc.)
            if language in ["c", "cpp", "csharp", "java", "rust", "go"]:
                open_braces = content.count('{')
                close_braces = content.count('}')
                if abs(open_braces - close_braces) > 0:
                    result["valid"] = False
                    result["error"] = f"Mismatched braces: {open_braces} '{{' vs {close_braces} '}}'"
                    return result

            # If we can't validate, note it but don't fail
            result["error"] = f"Validation not supported for {language} (manual verification recommended)"

        return result

    except Exception as e:
        result["valid"] = False
        result["error"] = f"Validation error: {str(e)}"
        return result


def validate_java_syntax(code: str) -> tuple[bool, str | None]:
    """Validate Java syntax using javac compiler.

    Uses javac with syntax-only flag to check for compilation errors
    without generating class files.

    Args:
        code: Java source code to validate

    Returns:
        Tuple of (is_valid, error_message).
        Returns (True, None) if syntax is valid.
        Returns (False, error_message) if syntax is invalid.
    """
    import tempfile

    # Create temporary file for javac
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.java',
        delete=False,
        encoding='utf-8'
    ) as tmp_file:
        tmp_file.write(code)
        tmp_path = tmp_file.name

    try:
        # Run javac with -Xlint:none to suppress warnings, -proc:none to skip annotation processing
        result = subprocess.run(
            ["javac", "-Xlint:none", "-proc:none", "-d", "/dev/null", tmp_path],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            return (True, None)

        # Parse error output for detailed message
        error_output = result.stderr.strip()
        if not error_output:
            error_output = result.stdout.strip()

        if error_output:
            # Extract error details from javac output
            # Format: filename.java:line: error: message
            lines = error_output.split('\n')
            error_messages = []

            for line in lines:
                # Skip pointer lines (^ symbols) and blank lines
                if line.strip() == '^' or not line.strip():
                    continue
                # Extract the actual error message
                if '.java:' in line:
                    # Parse line number and message
                    try:
                        parts = line.split(':', 3)
                        if len(parts) >= 4:
                            line_num = parts[1]
                            msg = parts[3].strip() if len(parts) > 3 else parts[2].strip()
                            error_messages.append(f"Line {line_num}: {msg}")
                        else:
                            error_messages.append(line)
                    except (IndexError, ValueError):
                        error_messages.append(line)
                elif 'error:' in line.lower():
                    error_messages.append(line.strip())

            if error_messages:
                return (False, "; ".join(error_messages[:5]))  # Limit to first 5 errors

            return (False, error_output[:500])  # Truncate long output

        return (False, "Java compilation failed with unknown error")

    except FileNotFoundError:
        return (False, "javac not found - Java JDK required for syntax validation")
    except subprocess.TimeoutExpired:
        return (False, "Java syntax validation timed out (30s)")
    except Exception as e:
        return (False, f"Java validation error: {str(e)}")
    finally:
        # Clean up temporary file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def format_generated_code(code: str, language: str) -> str:
    """Format generated code using language-specific formatters.

    Dispatches to the appropriate formatter based on language. Returns code
    as-is if the language is unknown or formatting fails. Integrates with
    syntax validation by formatting code before validation checks.

    Args:
        code: The generated code string to format
        language: Programming language identifier (python, javascript, typescript, etc.)

    Returns:
        Formatted code string, or original code if formatting is not available
        or fails for the specified language

    Examples:
        >>> formatted = format_generated_code("x=1", "python")
        >>> formatted  # Would be "x = 1" if black available
        'x=1'
        >>> format_generated_code("const x=1;", "unknown_lang")
        'const x=1;'
    """
    logger = get_logger("format_code")
    language_lower = language.lower()

    # Dispatch to appropriate formatter based on language
    formatters: dict[str, str] = {
        "python": "black",
        "javascript": "prettier",
        "typescript": "prettier",
        "tsx": "prettier",
        "jsx": "prettier",
        "json": "prettier",
        "css": "prettier",
        "html": "prettier",
        "yaml": "prettier",
        "markdown": "prettier",
        "go": "gofmt",
        "rust": "rustfmt",
        "java": "google-java-format",
        "c": "clang-format",
        "cpp": "clang-format",
        "csharp": "dotnet-format",
    }

    formatter = formatters.get(language_lower)

    if not formatter:
        logger.debug(
            "format_skipped",
            language=language,
            reason="no_formatter_available"
        )
        return code

    try:
        # Python formatting with black
        if formatter == "black":
            result = subprocess.run(
                ["black", "--quiet", "-"],
                input=code,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(
                    "format_success",
                    language=language,
                    formatter=formatter
                )
                return result.stdout
            else:
                logger.warning(
                    "format_failed",
                    language=language,
                    formatter=formatter,
                    error=result.stderr.strip()
                )
                return code

        # JavaScript/TypeScript/JSON/CSS/HTML/YAML/Markdown formatting with prettier
        elif formatter == "prettier":
            parser_map = {
                "javascript": "babel",
                "typescript": "typescript",
                "tsx": "typescript",
                "jsx": "babel",
                "json": "json",
                "css": "css",
                "html": "html",
                "yaml": "yaml",
                "markdown": "markdown",
            }
            parser = parser_map.get(language_lower, "babel")

            result = subprocess.run(
                ["prettier", "--parser", parser],
                input=code,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(
                    "format_success",
                    language=language,
                    formatter=formatter,
                    parser=parser
                )
                return result.stdout
            else:
                logger.warning(
                    "format_failed",
                    language=language,
                    formatter=formatter,
                    error=result.stderr.strip()
                )
                return code

        # Go formatting with gofmt
        elif formatter == "gofmt":
            result = subprocess.run(
                ["gofmt"],
                input=code,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(
                    "format_success",
                    language=language,
                    formatter=formatter
                )
                return result.stdout
            else:
                logger.warning(
                    "format_failed",
                    language=language,
                    formatter=formatter,
                    error=result.stderr.strip()
                )
                return code

        # Rust formatting with rustfmt
        elif formatter == "rustfmt":
            result = subprocess.run(
                ["rustfmt"],
                input=code,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(
                    "format_success",
                    language=language,
                    formatter=formatter
                )
                return result.stdout
            else:
                logger.warning(
                    "format_failed",
                    language=language,
                    formatter=formatter,
                    error=result.stderr.strip()
                )
                return code

        # C/C++ formatting with clang-format
        elif formatter == "clang-format":
            result = subprocess.run(
                ["clang-format"],
                input=code,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(
                    "format_success",
                    language=language,
                    formatter=formatter
                )
                return result.stdout
            else:
                logger.warning(
                    "format_failed",
                    language=language,
                    formatter=formatter,
                    error=result.stderr.strip()
                )
                return code

        # Java formatting with google-java-format
        elif formatter == "google-java-format":
            result = subprocess.run(
                ["google-java-format", "-"],
                input=code,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(
                    "format_success",
                    language=language,
                    formatter=formatter
                )
                return result.stdout
            else:
                logger.warning(
                    "format_failed",
                    language=language,
                    formatter=formatter,
                    error=result.stderr.strip()
                )
                return code

        # C# formatting with dotnet-format (requires file, not stdin)
        elif formatter == "dotnet-format":
            logger.debug(
                "format_skipped",
                language=language,
                formatter=formatter,
                reason="stdin_not_supported"
            )
            return code

        else:
            logger.debug(
                "format_skipped",
                language=language,
                formatter=formatter,
                reason="formatter_not_implemented"
            )
            return code

    except FileNotFoundError:
        logger.debug(
            "format_skipped",
            language=language,
            formatter=formatter,
            reason="formatter_not_installed"
        )
        return code
    except subprocess.TimeoutExpired:
        logger.warning(
            "format_timeout",
            language=language,
            formatter=formatter,
            timeout_seconds=10
        )
        return code
    except Exception as e:
        logger.warning(
            "format_error",
            language=language,
            formatter=formatter,
            error=str(e)
        )
        return code


def format_validation_error(error: str, code: str, language: str) -> str:
    """Format a validation error with context and visual pointers.

    Args:
        error: The error message from the validator
        code: The source code that failed validation
        language: Programming language of the code

    Returns:
        Formatted error message with code snippet, pointer, and suggestions
    """
    import re

    lines = code.split('\n')
    formatted_parts: List[str] = []

    # Extract line and column from error message
    line_num: int | None = None
    col_num: int | None = None

    # Common error patterns for different languages
    patterns = [
        r'[Ll]ine (\d+)(?:, column (\d+))?',  # Line 5, column 10
        r'(\d+):(\d+)',  # 5:10
        r'at line (\d+)',  # at line 5
        r'\((\d+),\s*(\d+)\)',  # (5, 10)
    ]

    for pattern in patterns:
        match = re.search(pattern, error)
        if match:
            line_num = int(match.group(1))
            if match.lastindex and match.lastindex >= 2 and match.group(2):
                col_num = int(match.group(2))
            break

    # Build header
    formatted_parts.append(f"=== Validation Error ({language}) ===")
    formatted_parts.append(f"Error: {error}")
    formatted_parts.append("")

    # Show code snippet with context if we have line info
    if line_num and 1 <= line_num <= len(lines):
        context_before = 2
        context_after = 2

        start_line = max(1, line_num - context_before)
        end_line = min(len(lines), line_num + context_after)

        formatted_parts.append("Code snippet:")
        formatted_parts.append("-" * 40)

        for i in range(start_line, end_line + 1):
            line_content = lines[i - 1]
            marker = ">>>" if i == line_num else "   "
            formatted_parts.append(f"{marker} {i:4d} | {line_content}")

            # Add pointer to error column
            if i == line_num and col_num:
                pointer_pos = col_num - 1
                pointer_line = "   " + "     " + " " * pointer_pos + "^"
                formatted_parts.append(pointer_line)

        formatted_parts.append("-" * 40)

    # Add suggested fixes for common errors
    suggestions = _get_error_suggestions(error, language)
    if suggestions:
        formatted_parts.append("")
        formatted_parts.append("Suggested fixes:")
        for suggestion in suggestions:
            formatted_parts.append(f"  - {suggestion}")

    return '\n'.join(formatted_parts)


def _get_error_suggestions(error: str, language: str) -> List[str]:
    """Get suggested fixes for common validation errors.

    Args:
        error: The error message
        language: Programming language

    Returns:
        List of suggestion strings
    """
    suggestions: List[str] = []
    error_lower = error.lower()

    # Common Python errors
    if language == "python":
        if "unexpected indent" in error_lower:
            suggestions.append("Check indentation - use consistent spaces (4) or tabs")
            suggestions.append("Ensure previous line ends correctly (no trailing backslash)")
        elif "expected ':'" in error_lower or ("invalid syntax" in error_lower and ":" in error):
            suggestions.append("Add colon after if/for/while/def/class statements")
        elif "unterminated string" in error_lower:
            suggestions.append("Close string with matching quote character")
            suggestions.append("Use triple quotes for multi-line strings")
        elif "unmatched" in error_lower:
            suggestions.append("Check for matching parentheses, brackets, or braces")
        elif "invalid syntax" in error_lower:
            suggestions.append("Check for missing commas between list/dict items")
            suggestions.append("Verify proper operator usage (= vs ==)")

    # Common JavaScript/TypeScript errors
    elif language in ["javascript", "typescript", "jsx", "tsx"]:
        if "unexpected token" in error_lower:
            suggestions.append("Check for missing semicolons or commas")
            suggestions.append("Verify proper bracket/brace matching")
        elif "unterminated" in error_lower:
            suggestions.append("Close string literals with matching quotes")
            suggestions.append("Close template literals with backtick")
        elif "missing" in error_lower and ")" in error:
            suggestions.append("Add missing closing parenthesis")

    # Common Java errors
    elif language == "java":
        if "';' expected" in error_lower or "expected" in error_lower:
            suggestions.append("Check for missing semicolons at end of statements")
        elif "class" in error_lower and "public" in error_lower:
            suggestions.append("Ensure class name matches filename")
        elif "cannot find symbol" in error_lower:
            suggestions.append("Check import statements and variable declarations")

    # Common brace-based language errors
    if language in ["c", "cpp", "csharp", "java", "rust", "go"]:
        if "brace" in error_lower or "{" in error or "}" in error:
            suggestions.append("Check for matching opening and closing braces")
            suggestions.append("Verify all function/class/block bodies are properly closed")
        if "semicolon" in error_lower:
            suggestions.append("Add semicolon at end of statement")

    return suggestions


def validate_generated_code(code: str, language: str) -> tuple[bool, str | None]:
    """Validate generated code and return formatted error if invalid.

    Dispatcher function that validates code for different languages and
    returns a user-friendly error message on failure.

    Args:
        code: The generated source code to validate
        language: Programming language (python, javascript, typescript, java, etc.)

    Returns:
        Tuple of (is_valid, error_message). error_message is None if valid,
        otherwise contains formatted error with context and suggestions.

    Examples:
        >>> valid, err = validate_generated_code("x = 1", "python")
        >>> valid
        True
        >>> valid, err = validate_generated_code("def foo(", "python")
        >>> valid
        False
        >>> "Suggested fixes" in err
        True
    """
    # Python validation
    if language == "python":
        is_valid, error = validate_python_syntax(code)
        if not is_valid and error:
            return (False, format_validation_error(error, code, language))
        return (is_valid, error)

    # JavaScript/TypeScript validation
    elif language in ["javascript", "typescript", "tsx", "jsx"]:
        is_valid, error = validate_javascript_syntax(code)
        if not is_valid and error:
            return (False, format_validation_error(error, code, language))
        return (is_valid, error)

    # Java validation
    elif language == "java":
        is_valid, error = validate_java_syntax(code)
        if not is_valid and error:
            return (False, format_validation_error(error, code, language))
        return (is_valid, error)

    # Brace-based languages - basic validation
    elif language in ["c", "cpp", "csharp", "rust", "go"]:
        open_braces = code.count('{')
        close_braces = code.count('}')
        if open_braces != close_braces:
            error_msg = f"Mismatched braces: {open_braces} '{{' vs {close_braces} '}}'"
            formatted = format_validation_error(error_msg, code, language)
            return (False, formatted)
        return (True, None)

    # Unsupported languages - return valid with no error
    else:
        return (True, None)


def validate_rewrites(modified_files: List[str], language: str) -> Dict[str, Any]:
    """Validate syntax of all rewritten files.

    Args:
        modified_files: List of file paths that were modified
        language: Programming language

    Returns:
        Dict with validation summary and results per file
    """
    validation_results = []
    failed_count = 0
    skipped_count = 0

    for file_path in modified_files:
        result = validate_syntax(file_path, language)
        validation_results.append(result)

        if not result["valid"]:
            if result["error"] and "not supported" in result["error"]:
                skipped_count += 1
            elif result["error"] and "skipped" in result["error"]:
                skipped_count += 1
            else:
                failed_count += 1

    return {
        "validated": len(modified_files),
        "passed": len(modified_files) - failed_count - skipped_count,
        "failed": failed_count,
        "skipped": skipped_count,
        "results": validation_results
    }

# ============================================================================
# Phase 3.4: Diff Preview Generator for apply_deduplication
# ============================================================================

@dataclass
class FileDiff:
    """Represents a diff for a single file.

    Attributes:
        file_path: Absolute path to the file
        original_content: Original file content
        new_content: New content after changes
        unified_diff: Raw unified diff string
        formatted_diff: Human-readable formatted diff with colors/context
        hunks: List of individual diff hunks
        additions: Number of lines added
        deletions: Number of lines deleted
    """
    file_path: str
    original_content: str
    new_content: str
    unified_diff: str
    formatted_diff: str
    hunks: List[Dict[str, Any]]
    additions: int
    deletions: int


@dataclass
class DiffPreview:
    """Container for multi-file diff preview.

    Attributes:
        file_diffs: List of FileDiff objects for each modified file
        total_files: Number of files with changes
        total_additions: Total lines added across all files
        total_deletions: Total lines deleted across all files
        combined_diff: Single string with all diffs combined
        summary: Human-readable summary of changes
    """
    file_diffs: List[FileDiff]
    total_files: int
    total_additions: int
    total_deletions: int
    combined_diff: str
    summary: str


def generate_file_diff(
    file_path: str,
    original_content: str,
    new_content: str,
    context_lines: int = 3
) -> FileDiff:
    """Generate a unified diff for a single file.

    Args:
        file_path: Path to the file (used in diff header)
        original_content: Original file content
        new_content: New content after changes
        context_lines: Number of context lines before/after changes (default 3)

    Returns:
        FileDiff object with raw and formatted diffs
    """
    import re

    # Split content into lines
    original_lines = original_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    # Ensure lines end with newline for proper diff format
    if original_lines and not original_lines[-1].endswith('\n'):
        original_lines[-1] += '\n'
    if new_lines and not new_lines[-1].endswith('\n'):
        new_lines[-1] += '\n'

    # Generate unified diff
    diff_lines = list(difflib.unified_diff(
        original_lines,
        new_lines,
        fromfile=f"a/{os.path.basename(file_path)}",
        tofile=f"b/{os.path.basename(file_path)}",
        lineterm='',
        n=context_lines
    ))

    unified_diff = ''.join(diff_lines)

    # Parse hunks and count additions/deletions
    hunks: List[Dict[str, Any]] = []
    additions = 0
    deletions = 0
    current_hunk: Optional[Dict[str, Any]] = None

    for line in diff_lines:
        if line.startswith('@@'):
            # Parse hunk header: @@ -start,count +start,count @@
            if current_hunk:
                hunks.append(current_hunk)

            # Extract line numbers from hunk header
            match = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', line)
            if match:
                current_hunk = {
                    'header': line,
                    'old_start': int(match.group(1)),
                    'old_count': int(match.group(2)) if match.group(2) else 1,
                    'new_start': int(match.group(3)),
                    'new_count': int(match.group(4)) if match.group(4) else 1,
                    'lines': []
                }
            else:
                current_hunk = {
                    'header': line,
                    'lines': []
                }
        elif current_hunk is not None:
            current_hunk['lines'].append(line)
            if line.startswith('+') and not line.startswith('+++'):
                additions += 1
            elif line.startswith('-') and not line.startswith('---'):
                deletions += 1

    if current_hunk:
        hunks.append(current_hunk)

    # Generate formatted diff with line numbers
    formatted_diff = _format_diff_with_line_numbers(
        file_path, diff_lines, original_lines, new_lines
    )

    return FileDiff(
        file_path=file_path,
        original_content=original_content,
        new_content=new_content,
        unified_diff=unified_diff,
        formatted_diff=formatted_diff,
        hunks=hunks,
        additions=additions,
        deletions=deletions
    )


def _format_diff_with_line_numbers(
    file_path: str,
    diff_lines: List[str],
    original_lines: List[str],
    new_lines: List[str]
) -> str:
    """Format diff with line numbers for readability.

    Args:
        file_path: Path to the file
        diff_lines: Raw diff lines from unified_diff
        original_lines: Original file lines
        new_lines: New file lines

    Returns:
        Formatted diff string with line numbers and visual indicators
    """
    import re

    if not diff_lines:
        return f"No changes in {file_path}"

    output = []
    output.append(f"{'=' * 70}")
    output.append(f"File: {file_path}")
    output.append(f"{'=' * 70}")

    old_line_num = 0
    new_line_num = 0

    for line in diff_lines:
        if line.startswith('---'):
            output.append(f"--- {file_path} (original)")
        elif line.startswith('+++'):
            output.append(f"+++ {file_path} (modified)")
        elif line.startswith('@@'):
            # Parse hunk header for line numbers
            match = re.match(r'@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*)', line)
            if match:
                old_line_num = int(match.group(1)) - 1
                new_line_num = int(match.group(2)) - 1
                context = match.group(3).strip()
                output.append(f"\n{line.strip()}")
                if context:
                    output.append(f"  Context: {context}")
            else:
                output.append(f"\n{line.strip()}")
        elif line.startswith('-'):
            old_line_num += 1
            output.append(f"{old_line_num:4d}      - {line[1:].rstrip()}")
        elif line.startswith('+'):
            new_line_num += 1
            output.append(f"     {new_line_num:4d} + {line[1:].rstrip()}")
        else:
            # Context line
            old_line_num += 1
            new_line_num += 1
            output.append(f"{old_line_num:4d} {new_line_num:4d}   {line.rstrip()}")

    output.append(f"\n{'=' * 70}\n")

    return '\n'.join(output)


def generate_multi_file_diff(
    file_changes: List[Dict[str, str]],
    context_lines: int = 3
) -> DiffPreview:
    """Generate combined diff preview for multiple file changes.

    Args:
        file_changes: List of dicts with keys:
            - 'file_path': Absolute path to file
            - 'original_content': Original file content
            - 'new_content': New content after changes
        context_lines: Number of context lines (default 3)

    Returns:
        DiffPreview with all file diffs combined
    """
    file_diffs = []
    total_additions = 0
    total_deletions = 0

    for change in file_changes:
        file_diff = generate_file_diff(
            file_path=change['file_path'],
            original_content=change['original_content'],
            new_content=change['new_content'],
            context_lines=context_lines
        )
        file_diffs.append(file_diff)
        total_additions += file_diff.additions
        total_deletions += file_diff.deletions

    # Combine all formatted diffs
    combined_parts = []
    for fd in file_diffs:
        combined_parts.append(fd.formatted_diff)

    combined_diff = '\n'.join(combined_parts)

    # Generate summary
    files_with_changes = [fd for fd in file_diffs if fd.additions > 0 or fd.deletions > 0]
    summary_lines = [
        "Diff Preview Summary",
        "-" * 40,
        f"Files modified: {len(files_with_changes)}",
        f"Total additions: +{total_additions}",
        f"Total deletions: -{total_deletions}",
        "-" * 40,
    ]

    for fd in files_with_changes:
        summary_lines.append(
            f"  {os.path.basename(fd.file_path)}: +{fd.additions}/-{fd.deletions}"
        )

    summary = '\n'.join(summary_lines)

    return DiffPreview(
        file_diffs=file_diffs,
        total_files=len(files_with_changes),
        total_additions=total_additions,
        total_deletions=total_deletions,
        combined_diff=combined_diff,
        summary=summary
    )


def diff_preview_to_dict(preview: DiffPreview) -> Dict[str, Any]:
    """Convert DiffPreview to a dictionary for JSON serialization.

    Args:
        preview: DiffPreview object

    Returns:
        Dictionary representation suitable for JSON/tool output
    """
    return {
        'summary': preview.summary,
        'total_files': preview.total_files,
        'total_additions': preview.total_additions,
        'total_deletions': preview.total_deletions,
        'combined_diff': preview.combined_diff,
        'files': [
            {
                'file_path': fd.file_path,
                'additions': fd.additions,
                'deletions': fd.deletions,
                'unified_diff': fd.unified_diff,
                'formatted_diff': fd.formatted_diff,
                'hunks': fd.hunks
            }
            for fd in preview.file_diffs
        ]
    }


def generate_diff_from_file_paths(
    original_files: List[str],
    new_contents: Dict[str, str],
    context_lines: int = 3
) -> DiffPreview:
    """Generate diff preview by reading original files from disk.

    Convenience function that reads original content from file paths
    and generates a diff preview against provided new content.

    Args:
        original_files: List of absolute file paths to read
        new_contents: Dict mapping file paths to new content
        context_lines: Number of context lines (default 3)

    Returns:
        DiffPreview with all file diffs

    Raises:
        FileNotFoundError: If original file doesn't exist
    """
    file_changes = []

    for file_path in original_files:
        if file_path not in new_contents:
            continue

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Original file not found: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        file_changes.append({
            'file_path': file_path,
            'original_content': original_content,
            'new_content': new_contents[file_path]
        })

    return generate_multi_file_diff(file_changes, context_lines)


# ============================================================================
# Backup Management for Code Rewrites
# ============================================================================

def create_backup(files_to_backup: List[str], project_folder: str) -> str:
    """Create a timestamped backup of files before rewriting.

    Args:
        files_to_backup: List of absolute file paths to backup
        project_folder: Project root folder

    Returns:
        backup_id: Unique identifier for this backup (timestamp-based)
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
    backup_id = f"backup-{timestamp}"
    backup_base_dir = os.path.join(project_folder, ".ast-grep-backups")
    backup_dir = os.path.join(backup_base_dir, backup_id)

    # Handle collision by appending counter suffix
    counter = 1
    while os.path.exists(backup_dir):
        backup_id = f"backup-{timestamp}-{counter}"
        backup_dir = os.path.join(backup_base_dir, backup_id)
        counter += 1

    os.makedirs(backup_dir, exist_ok=True)

    metadata: Dict[str, Any] = {
        "backup_id": backup_id,
        "timestamp": datetime.now().isoformat(),
        "files": [],
        "project_folder": project_folder
    }

    for file_path in files_to_backup:
        if not os.path.exists(file_path):
            continue

        rel_path = os.path.relpath(file_path, project_folder)
        backup_file_path = os.path.join(backup_dir, rel_path)

        os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)
        shutil.copy2(file_path, backup_file_path)

        metadata["files"].append({
            "original": file_path,
            "relative": rel_path,
            "backup": backup_file_path
        })

    metadata_path = os.path.join(backup_dir, "backup-metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    return backup_id


def create_deduplication_backup(
    files_to_backup: List[str],
    project_folder: str,
    duplicate_group_id: int,
    strategy: str,
    original_hashes: Dict[str, str]
) -> str:
    """Create a backup with deduplication-specific metadata.

    Args:
        files_to_backup: List of absolute file paths to backup
        project_folder: Project root folder
        duplicate_group_id: ID of the duplicate group being refactored
        strategy: Deduplication strategy used (e.g., 'extract_function', 'consolidate')
        original_hashes: Dict mapping file paths to their content hashes

    Returns:
        backup_id: Unique identifier for this backup (timestamp-based)
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
    backup_id = f"dedup-backup-{timestamp}"
    backup_base_dir = os.path.join(project_folder, ".ast-grep-backups")
    backup_dir = os.path.join(backup_base_dir, backup_id)

    # Handle collision by appending counter suffix
    counter = 1
    while os.path.exists(backup_dir):
        backup_id = f"dedup-backup-{timestamp}-{counter}"
        backup_dir = os.path.join(backup_base_dir, backup_id)
        counter += 1

    os.makedirs(backup_dir, exist_ok=True)

    metadata: Dict[str, Any] = {
        "backup_id": backup_id,
        "backup_type": "deduplication",
        "timestamp": datetime.now().isoformat(),
        "files": [],
        "project_folder": project_folder,
        "deduplication_metadata": {
            "duplicate_group_id": duplicate_group_id,
            "strategy": strategy,
            "original_hashes": original_hashes,
            "affected_files": files_to_backup
        }
    }

    for file_path in files_to_backup:
        if not os.path.exists(file_path):
            continue

        rel_path = os.path.relpath(file_path, project_folder)
        backup_file_path = os.path.join(backup_dir, rel_path)

        os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)
        shutil.copy2(file_path, backup_file_path)

        metadata["files"].append({
            "original": file_path,
            "relative": rel_path,
            "backup": backup_file_path,
            "original_hash": original_hashes.get(file_path, "")
        })

    metadata_path = os.path.join(backup_dir, "backup-metadata.json")
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    return backup_id


def get_file_hash(file_path: str) -> str:
    """Calculate SHA-256 hash of a file's contents.

    Args:
        file_path: Absolute path to the file

    Returns:
        Hex digest of the file's SHA-256 hash
    """
    import hashlib
    try:
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except (OSError, IOError):
        return ""


def verify_backup_integrity(backup_id: str, project_folder: str) -> Dict[str, Any]:
    """Verify that a backup can be safely restored.

    Args:
        backup_id: The backup identifier to verify
        project_folder: Project root folder

    Returns:
        Dict with verification status and any issues found
    """
    backup_dir = os.path.join(project_folder, ".ast-grep-backups", backup_id)
    metadata_path = os.path.join(backup_dir, "backup-metadata.json")

    result: Dict[str, Any] = {
        "valid": True,
        "issues": [],
        "files_verified": 0,
        "backup_type": "unknown"
    }

    if not os.path.exists(metadata_path):
        result["valid"] = False
        result["issues"].append(f"Backup '{backup_id}' not found or invalid")
        return result

    try:
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
    except json.JSONDecodeError as e:
        result["valid"] = False
        result["issues"].append(f"Invalid metadata JSON: {str(e)}")
        return result

    result["backup_type"] = metadata.get("backup_type", "rewrite")

    for file_info in metadata.get("files", []):
        backup_file = file_info.get("backup", "")
        if not os.path.exists(backup_file):
            result["valid"] = False
            result["issues"].append(f"Missing backup file: {file_info.get('relative', 'unknown')}")
        else:
            result["files_verified"] += 1

    return result


def restore_from_backup(backup_id: str, project_folder: str) -> List[str]:
    """Restore files from a backup.

    Args:
        backup_id: The backup identifier to restore from
        project_folder: Project root folder

    Returns:
        List of restored file paths
    """
    backup_dir = os.path.join(project_folder, ".ast-grep-backups", backup_id)
    metadata_path = os.path.join(backup_dir, "backup-metadata.json")

    if not os.path.exists(metadata_path):
        raise ValueError(f"Backup '{backup_id}' not found or invalid")

    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    restored_files = []
    for file_info in metadata["files"]:
        backup_file = file_info["backup"]
        original_file = file_info["original"]

        if not os.path.exists(backup_file):
            continue

        os.makedirs(os.path.dirname(original_file), exist_ok=True)
        shutil.copy2(backup_file, original_file)
        restored_files.append(original_file)

    return restored_files


def list_available_backups(project_folder: str) -> List[Dict[str, Any]]:
    """List all available backups for a project.

    Args:
        project_folder: Project root folder

    Returns:
        List of backup metadata dictionaries
    """
    backups_root = os.path.join(project_folder, ".ast-grep-backups")

    if not os.path.exists(backups_root):
        return []

    backups = []
    for backup_dir in os.listdir(backups_root):
        metadata_path = os.path.join(backups_root, backup_dir, "backup-metadata.json")

        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
                backups.append({
                    "backup_id": metadata["backup_id"],
                    "timestamp": metadata["timestamp"],
                    "file_count": len(metadata["files"]),
                    "files": [f["relative"] for f in metadata["files"]]
                })

    backups.sort(key=lambda x: x["timestamp"], reverse=True)
    return backups


# ============================================================================
# Phase 3.3: Multi-File Orchestration Helper Functions
# ============================================================================

def _plan_file_modification_order(
    files_to_modify: List[str],
    generated_code: Dict[str, Any],
    extract_to_file: Optional[str],
    project_folder: str,
    language: str
) -> Dict[str, Any]:
    """Plan the order of file modifications for atomic deduplication.

    Determines which files need to be created vs updated, and generates
    import statements for files that will call the extracted function.

    Args:
        files_to_modify: List of files containing duplicates
        generated_code: Generated code from Phase 2 engine
        extract_to_file: Target file for extracted function (or None for auto)
        project_folder: Project root folder
        language: Programming language

    Returns:
        Orchestration plan with:
        - create_files: List of files to create (extracted function)
        - update_files: List of files to update (duplicate locations)
        - import_additions: Dict mapping files to import info
    """
    plan: Dict[str, Any] = {
        "create_files": [],
        "update_files": [],
        "import_additions": {}
    }

    extracted_function = generated_code.get("extracted_function", "")
    function_name = generated_code.get("function_name", "extracted_function")

    # Determine target file for extracted function
    target_file = extract_to_file or generated_code.get("extract_to_file")
    if not target_file and files_to_modify:
        # Auto-detect: use first file or create utilities module
        first_file = files_to_modify[0]
        file_dir = os.path.dirname(first_file)
        ext = os.path.splitext(first_file)[1]
        target_file = os.path.join(file_dir, f"_extracted_utils{ext}")

    if target_file and not os.path.isabs(target_file):
        target_file = os.path.join(project_folder, target_file)

    # Plan file creation for extracted function
    if extracted_function and target_file:
        # Check if we're appending to existing file
        append_mode = os.path.exists(target_file)

        plan["create_files"].append({
            "path": target_file,
            "content": extracted_function,
            "append": append_mode,
            "operation": "append" if append_mode else "create"
        })

    # Plan updates for duplicate location files
    for file_path in files_to_modify:
        plan["update_files"].append({
            "path": file_path,
            "operation": "replace_duplicate"
        })

        # Generate import statement if needed
        # Only add imports if there's actually an extracted function to import
        if extracted_function and target_file and file_path != target_file:
            import_stmt = _generate_import_for_extracted_function(
                source_file=file_path,
                target_file=target_file,
                function_name=function_name,
                project_folder=project_folder,
                language=language
            )

            if import_stmt:
                plan["import_additions"][file_path] = {
                    "import_statement": import_stmt,
                    "from_file": target_file,
                    "function_name": function_name
                }

    return plan


# ============================================================================
# Phase 4.4: Impact Analysis for Deduplication
# ============================================================================

def analyze_deduplication_impact(
    duplicate_group: Dict[str, Any],
    project_root: str,
    language: str
) -> Dict[str, Any]:
    """Analyze the impact of applying deduplication to a duplicate group.

    Uses ast-grep to find external references to the duplicated code and
    assesses breaking change risks.

    Args:
        duplicate_group: A duplication group from find_duplication results containing:
            - locations: List of file:line-range strings
            - sample_code: Representative code sample
            - duplicate_count: Number of instances
            - lines_per_duplicate: Lines in each instance
        project_root: Absolute path to project root
        language: Programming language

    Returns:
        Impact analysis with:
        - files_affected: Number of files that would be modified
        - lines_changed: Dict with additions and deletions estimates
        - external_call_sites: List of locations calling the duplicated code
        - breaking_change_risk: Dict with risk level and factors
    """
    logger = get_logger("duplication.impact_analysis")

    locations = duplicate_group.get("locations", [])
    sample_code = duplicate_group.get("sample_code", "")
    duplicate_count = duplicate_group.get("duplicate_count", 0)
    lines_per_duplicate = duplicate_group.get("lines_per_duplicate", 0)

    # Parse locations to get file paths and line ranges
    files_in_group = []
    for loc in locations:
        if ":" in loc:
            file_path = loc.split(":")[0]
            if file_path not in files_in_group:
                files_in_group.append(file_path)

    # Extract function/class names from sample code
    function_names = _extract_function_names_from_code(sample_code, language)

    logger.info(
        "impact_analysis_start",
        duplicate_count=duplicate_count,
        files_in_group=len(files_in_group),
        function_names=function_names[:5] if function_names else []
    )

    # Find external call sites using ast-grep
    external_call_sites = _find_external_call_sites(
        function_names=function_names,
        project_root=project_root,
        language=language,
        exclude_files=files_in_group
    )

    # Find imports of the duplicated code
    import_sites = _find_import_references(
        function_names=function_names,
        project_root=project_root,
        language=language,
        exclude_files=files_in_group
    )

    # Combine call sites and imports
    all_external_refs = external_call_sites + import_sites

    # Estimate lines changed
    lines_changed = _estimate_lines_changed(
        duplicate_count=duplicate_count,
        lines_per_duplicate=lines_per_duplicate,
        external_call_sites=len(all_external_refs)
    )

    # Assess breaking change risk
    breaking_change_risk = _assess_breaking_change_risk(
        function_names=function_names,
        files_in_group=files_in_group,
        external_call_sites=all_external_refs,
        project_root=project_root,
        language=language
    )

    # Calculate files affected
    files_affected = len(files_in_group)
    external_files = set()
    for site in all_external_refs:
        if "file" in site:
            external_files.add(site["file"])
    files_affected += len(external_files)

    result = {
        "files_affected": files_affected,
        "lines_changed": lines_changed,
        "external_call_sites": all_external_refs,
        "breaking_change_risk": breaking_change_risk
    }

    logger.info(
        "impact_analysis_complete",
        files_affected=files_affected,
        external_references=len(all_external_refs),
        risk_level=breaking_change_risk.get("level", "unknown")
    )

    return result


def _extract_function_names_from_code(code: str, language: str) -> List[str]:
    """Extract function/method/class names from code sample.

    Args:
        code: Code sample to analyze
        language: Programming language

    Returns:
        List of extracted names
    """
    names: List[str] = []

    if not code:
        return names

    lang = language.lower()

    # Language-specific patterns for extracting names
    if lang == "python":
        # Match: def function_name( or class ClassName
        import re
        func_matches = re.findall(r'\bdef\s+(\w+)\s*\(', code)
        class_matches = re.findall(r'\bclass\s+(\w+)', code)
        names.extend(func_matches)
        names.extend(class_matches)

    elif lang in ("javascript", "typescript", "jsx", "tsx"):
        import re
        # Match: function name( or const name = or name( { for methods
        func_matches = re.findall(r'\bfunction\s+(\w+)\s*\(', code)
        arrow_matches = re.findall(r'\b(?:const|let|var)\s+(\w+)\s*=\s*(?:\([^)]*\)|[^=])*=>', code)
        method_matches = re.findall(r'^\s*(\w+)\s*\([^)]*\)\s*\{', code, re.MULTILINE)
        names.extend(func_matches)
        names.extend(arrow_matches)
        names.extend(method_matches)

    elif lang in ("java", "csharp", "cpp", "c"):
        import re
        # Match: returnType methodName( or class ClassName
        method_matches = re.findall(r'\b(?:public|private|protected|static|\w+)\s+(\w+)\s*\([^)]*\)\s*\{', code)
        class_matches = re.findall(r'\bclass\s+(\w+)', code)
        names.extend(method_matches)
        names.extend(class_matches)

    elif lang == "go":
        import re
        # Match: func FunctionName( or func (r *Receiver) MethodName(
        func_matches = re.findall(r'\bfunc\s+(?:\([^)]*\)\s+)?(\w+)\s*\(', code)
        names.extend(func_matches)

    elif lang == "rust":
        import re
        # Match: fn function_name( or struct StructName
        func_matches = re.findall(r'\bfn\s+(\w+)\s*[<(]', code)
        struct_matches = re.findall(r'\bstruct\s+(\w+)', code)
        names.extend(func_matches)
        names.extend(struct_matches)

    # Deduplicate and filter common words
    filtered_names = []
    seen = set()
    common_words = {"new", "get", "set", "if", "for", "while", "return", "main", "init", "test"}

    for name in names:
        if name and name not in seen and name.lower() not in common_words:
            seen.add(name)
            filtered_names.append(name)

    return filtered_names


def _find_external_call_sites(
    function_names: List[str],
    project_root: str,
    language: str,
    exclude_files: List[str]
) -> List[Dict[str, Any]]:
    """Find call sites for functions outside the duplicate locations.

    Uses ast-grep to search for function calls.

    Args:
        function_names: Names of functions to search for
        project_root: Project root path
        language: Programming language
        exclude_files: Files to exclude (contain the duplicates)

    Returns:
        List of call site info dicts with file, line, column, context
    """
    call_sites: List[Dict[str, Any]] = []

    if not function_names:
        return call_sites

    lang = language.lower()

    for func_name in function_names[:10]:  # Limit to prevent too many searches
        # Build call pattern based on language
        if lang == "python":
            pattern = f"{func_name}($$$)"
        elif lang in ("javascript", "typescript", "jsx", "tsx"):
            pattern = f"{func_name}($$$)"
        elif lang in ("java", "csharp"):
            pattern = f"{func_name}($$$)"
        elif lang == "go":
            pattern = f"{func_name}($$$)"
        elif lang == "rust":
            pattern = f"{func_name}($$$)"
        else:
            pattern = f"{func_name}($$$)"

        try:
            # Run ast-grep to find call sites
            args = ["--pattern", pattern, "--lang", language, "--json", project_root]
            result = run_ast_grep("run", args)

            if result.returncode == 0 and result.stdout.strip():
                matches = json.loads(result.stdout)

                for match in matches:
                    file_path = match.get("file", "")

                    # Skip files containing the duplicates
                    if file_path in exclude_files:
                        continue

                    # Make path absolute if needed
                    if not os.path.isabs(file_path):
                        file_path = os.path.join(project_root, file_path)

                    call_site = {
                        "file": file_path,
                        "line": match.get("range", {}).get("start", {}).get("line", 0) + 1,
                        "column": match.get("range", {}).get("start", {}).get("column", 0),
                        "function_called": func_name,
                        "context": match.get("text", "")[:100],
                        "type": "function_call"
                    }
                    call_sites.append(call_site)

        except (json.JSONDecodeError, subprocess.SubprocessError) as e:
            # Log but continue with other function names
            logger = get_logger("duplication.impact_analysis")
            logger.debug("call_site_search_error", function=func_name, error=str(e))
            continue

    return call_sites


def _find_import_references(
    function_names: List[str],
    project_root: str,
    language: str,
    exclude_files: List[str]
) -> List[Dict[str, Any]]:
    """Find import statements that reference the duplicated code.

    Args:
        function_names: Names to search for in imports
        project_root: Project root path
        language: Programming language
        exclude_files: Files to exclude

    Returns:
        List of import reference info dicts
    """
    import_refs: List[Dict[str, Any]] = []

    if not function_names:
        return import_refs

    lang = language.lower()

    for func_name in function_names[:10]:
        # Build import pattern based on language
        if lang == "python":
            # from module import func_name or import module
            patterns = [
                f"from $MODULE import {func_name}",
                f"from $MODULE import $$$, {func_name}, $$$"
            ]
        elif lang in ("javascript", "typescript", "jsx", "tsx"):
            patterns = [
                f"import {{ {func_name} }} from $MODULE",
                f"import {{ $$$, {func_name}, $$$ }} from $MODULE"
            ]
        elif lang in ("java",):
            patterns = [f"import $$$$.{func_name}"]
        elif lang == "go":
            # Go imports are package-level, not function-level
            continue
        else:
            continue

        for pattern in patterns:
            try:
                args = ["--pattern", pattern, "--lang", language, "--json", project_root]
                result = run_ast_grep("run", args)

                if result.returncode == 0 and result.stdout.strip():
                    matches = json.loads(result.stdout)

                    for match in matches:
                        file_path = match.get("file", "")

                        if file_path in exclude_files:
                            continue

                        if not os.path.isabs(file_path):
                            file_path = os.path.join(project_root, file_path)

                        import_ref = {
                            "file": file_path,
                            "line": match.get("range", {}).get("start", {}).get("line", 0) + 1,
                            "column": match.get("range", {}).get("start", {}).get("column", 0),
                            "imported_name": func_name,
                            "context": match.get("text", "")[:100],
                            "type": "import"
                        }
                        import_refs.append(import_ref)

            except (json.JSONDecodeError, subprocess.SubprocessError):
                continue

    return import_refs


def _estimate_lines_changed(
    duplicate_count: int,
    lines_per_duplicate: int,
    external_call_sites: int
) -> Dict[str, Any]:
    """Estimate the number of lines that would change during deduplication.

    Args:
        duplicate_count: Number of duplicate instances
        lines_per_duplicate: Lines in each duplicate
        external_call_sites: Number of external references

    Returns:
        Dict with additions and deletions estimates
    """
    # Deletions: All duplicate code except one instance
    deletions = (duplicate_count - 1) * lines_per_duplicate

    # Additions:
    # - One extracted function (slightly more lines due to parameterization)
    extracted_function_lines = int(lines_per_duplicate * 1.2)

    # - Import statements for each file (1 line per file)
    import_lines = duplicate_count - 1  # minus the file with the extracted function

    # - Replacement calls (1 line each)
    replacement_calls = duplicate_count

    # - Updates to external call sites (minimal, usually 0 or 1 line each)
    external_updates = external_call_sites

    additions = extracted_function_lines + import_lines + replacement_calls + external_updates

    # Net change
    net_change = additions - deletions

    return {
        "additions": additions,
        "deletions": deletions,
        "net_change": net_change,
        "breakdown": {
            "extracted_function": extracted_function_lines,
            "new_imports": import_lines,
            "replacement_calls": replacement_calls,
            "external_call_updates": external_updates
        }
    }


def _assess_breaking_change_risk(
    function_names: List[str],
    files_in_group: List[str],
    external_call_sites: List[Dict[str, Any]],
    project_root: str,
    language: str
) -> Dict[str, Any]:
    """Assess the risk of breaking changes from deduplication.

    Args:
        function_names: Names of functions being deduplicated
        files_in_group: Files containing the duplicates
        external_call_sites: External references found
        project_root: Project root path
        language: Programming language

    Returns:
        Risk assessment with level, factors, and recommendations
    """
    risk_factors = []
    risk_score = 0

    # Factor 1: External call sites exist
    if external_call_sites:
        call_count = len([s for s in external_call_sites if s.get("type") == "function_call"])
        import_count = len([s for s in external_call_sites if s.get("type") == "import"])

        if call_count > 0:
            risk_factors.append(f"Found {call_count} external call site(s) that may need updates")
            risk_score += min(call_count, 3)  # Cap at 3

        if import_count > 0:
            risk_factors.append(f"Found {import_count} import statement(s) referencing the code")
            risk_score += min(import_count, 2)  # Cap at 2

    # Factor 2: Check if functions appear to be public API
    for name in function_names:
        # Heuristics for public API
        is_public = False

        # Python: no underscore prefix
        if language.lower() == "python" and not name.startswith("_"):
            is_public = True

        # Java/C#: typically PascalCase for public
        if language.lower() in ("java", "csharp") and name[0].isupper():
            is_public = True

        # Check if exported (for JS/TS, would need file analysis)

        if is_public:
            risk_factors.append(f"Function '{name}' appears to be public API")
            risk_score += 2
            break  # Only count once

    # Factor 3: Cross-module dependencies
    if len(files_in_group) > 1:
        # Check if files are in different directories (different modules)
        directories = set()
        for file_path in files_in_group:
            directories.add(os.path.dirname(file_path))

        if len(directories) > 1:
            risk_factors.append(f"Duplicates span {len(directories)} different modules/directories")
            risk_score += 2

    # Factor 4: Test files involved
    test_files = [f for f in files_in_group if "test" in f.lower() or "spec" in f.lower()]
    if test_files:
        risk_factors.append(f"{len(test_files)} test file(s) contain duplicates - lower risk")
        risk_score -= 1  # Reduce risk for test-only changes

    # Factor 5: Check for __init__.py or index files (re-exports)
    reexport_files = [f for f in files_in_group
                     if os.path.basename(f) in ("__init__.py", "index.ts", "index.js", "mod.rs")]
    if reexport_files:
        risk_factors.append("Code is in module export file - higher breakage risk")
        risk_score += 3

    # Determine risk level
    if risk_score <= 1:
        level = "low"
        recommendations = [
            "Safe to proceed with standard review",
            "Run tests after applying changes"
        ]
    elif risk_score <= 4:
        level = "medium"
        recommendations = [
            "Review external call sites before applying",
            "Consider updating call sites in the same commit",
            "Run comprehensive test suite after changes"
        ]
    else:
        level = "high"
        recommendations = [
            "Carefully review all external references",
            "Consider deprecating old functions instead of removing",
            "Update external call sites first",
            "May require coordinated changes across modules",
            "Consider feature flag for gradual rollout"
        ]

    return {
        "level": level,
        "score": risk_score,
        "factors": risk_factors,
        "recommendations": recommendations,
        "external_reference_count": len(external_call_sites)
    }


def _generate_import_for_extracted_function(
    source_file: str,
    target_file: str,
    function_name: str,
    project_folder: str,
    language: str
) -> str:
    """Generate import statement for an extracted function.

    Creates the appropriate import statement based on the relative path
    between source and target files.

    Args:
        source_file: File that needs the import
        target_file: File containing the extracted function
        function_name: Name of the function to import
        project_folder: Project root folder
        language: Programming language

    Returns:
        Import statement string
    """
    # Calculate relative path from source to target
    source_dir = os.path.dirname(source_file)
    target_rel = os.path.relpath(target_file, source_dir)

    # Convert path to module path
    module_path = os.path.splitext(target_rel)[0]
    module_path = module_path.replace(os.sep, ".")
    module_path = module_path.replace("/", ".")

    # Handle parent directory references
    if module_path.startswith(".."):
        # Convert ../foo to relative import
        parts = module_path.split(".")
        parent_count = sum(1 for p in parts if p == "")
        module_parts = [p for p in parts if p and p != ".."]
        module_path = "." * parent_count + ".".join(module_parts)

    # Generate import using existing function
    return generate_import_statement(
        module_path=module_path,
        items=[function_name],
        language=language
    )


def _add_import_to_content(
    content: str,
    import_statement: str,
    language: str
) -> str:
    """Add an import statement to file content.

    Inserts the import statement at the appropriate location based on
    language conventions (after existing imports, at top of file, etc.).

    Args:
        content: Current file content
        import_statement: Import statement to add
        language: Programming language

    Returns:
        Updated content with import added
    """
    if not import_statement:
        return content

    lines = content.split('\n')
    lang = language.lower()

    # Check if import already exists
    if import_statement.strip() in content:
        return content

    if lang == "python":
        # Find last import statement
        last_import_idx = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                last_import_idx = i
            elif stripped and not stripped.startswith("#") and last_import_idx >= 0:
                # Reached non-import, non-comment content
                break

        if last_import_idx >= 0:
            # Insert after last import
            lines.insert(last_import_idx + 1, import_statement)
        else:
            # No imports found, add at top (after shebang/docstring if present)
            insert_idx = 0
            if lines and (lines[0].startswith("#!") or lines[0].startswith('"""')):
                insert_idx = 1
                # Skip multi-line docstring
                if lines[0].startswith('"""') and not lines[0].endswith('"""'):
                    for i in range(1, len(lines)):
                        if '"""' in lines[i]:
                            insert_idx = i + 1
                            break
            lines.insert(insert_idx, import_statement)
            if insert_idx == 0:
                lines.insert(1, "")  # Add blank line after import

    elif lang in ("typescript", "javascript", "tsx", "jsx"):
        # Find last import statement
        last_import_idx = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("const ") and "require(" in stripped:
                last_import_idx = i

        if last_import_idx >= 0:
            lines.insert(last_import_idx + 1, import_statement)
        else:
            # Add at top
            lines.insert(0, import_statement)
            lines.insert(1, "")

    elif lang == "java":
        # Find package or last import
        package_idx = -1
        last_import_idx = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("package "):
                package_idx = i
            elif stripped.startswith("import "):
                last_import_idx = i

        if last_import_idx >= 0:
            lines.insert(last_import_idx + 1, import_statement)
        elif package_idx >= 0:
            lines.insert(package_idx + 2, import_statement)
        else:
            lines.insert(0, import_statement)

    elif lang == "go":
        # Find import block or add one
        import_block_start = -1
        for i, line in enumerate(lines):
            if line.strip().startswith("import"):
                import_block_start = i
                break

        if import_block_start >= 0:
            # Add to import block
            if "(" in lines[import_block_start]:
                # Multi-line import
                lines.insert(import_block_start + 1, f"\t{import_statement}")
            else:
                # Single import - convert to block
                old_import = lines[import_block_start]
                lines[import_block_start] = "import ("
                lines.insert(import_block_start + 1, f"\t{old_import.replace('import ', '')}")
                lines.insert(import_block_start + 2, f"\t{import_statement}")
                lines.insert(import_block_start + 3, ")")
        else:
            # Find package declaration
            for i, line in enumerate(lines):
                if line.strip().startswith("package "):
                    lines.insert(i + 2, import_statement)
                    break

    else:
        # Default: add at top
        lines.insert(0, import_statement)
        lines.insert(1, "")

    return '\n'.join(lines)


# ============================================================================
# Phase 3.5: Syntax Validation Pipeline Helper Functions
# ============================================================================

def _validate_code_for_language(code: str, language: str) -> tuple[bool, Optional[str]]:
    """Validate code syntax for a specific language.

    Args:
        code: The code to validate
        language: Programming language

    Returns:
        Tuple of (is_valid, error_message)
    """
    lang = language.lower()

    if lang == "python":
        return validate_python_syntax(code)
    elif lang in ("javascript", "js"):
        return validate_javascript_syntax(code)
    elif lang in ("typescript", "ts", "tsx"):
        return validate_typescript_syntax(code)
    elif lang == "java":
        return validate_java_syntax(code)
    else:
        return (True, f"Validation not implemented for {language}")


def _suggest_syntax_fix(error: Optional[str], language: str) -> Optional[str]:
    """Suggest a fix based on a syntax error message.

    Args:
        error: The error message
        language: Programming language

    Returns:
        Suggested fix or None
    """
    if not error:
        return None

    error_lower = error.lower()

    # Common Python errors
    if "unexpected indent" in error_lower:
        return "Check indentation - use consistent spaces (4 spaces recommended)"
    if "expected ':'" in error_lower or "expected an indented block" in error_lower:
        return "Missing colon after function/class definition or control statement"
    if "unexpected eof" in error_lower:
        return "Code appears incomplete - check for missing closing brackets or quotes"
    if "invalid syntax" in error_lower:
        return "Check for typos, missing operators, or incorrect keywords"

    # Common JS/TS errors
    if "unexpected token" in error_lower:
        return "Check for missing semicolons, brackets, or incorrect syntax"
    if "unexpected end of input" in error_lower:
        return "Code appears incomplete - check for unclosed brackets or strings"

    # Generic suggestions
    if "brace" in error_lower or "bracket" in error_lower:
        return "Check for mismatched or missing brackets/braces"
    if "quote" in error_lower or "string" in error_lower:
        return "Check for unclosed or mismatched quotes"

    return "Review the syntax around the indicated line"


# ============================================================================
# Phase 4.2: Deduplication Ranking Algorithm
# ============================================================================

def calculate_deduplication_score(
    lines_saved: int,
    complexity: int,
    has_tests: bool,
    affected_files: int,
    external_call_sites: int
) -> float:
    """Calculate a prioritization score for deduplication candidates.

    Uses a weighted formula combining multiple factors to determine the value
    and risk of refactoring a particular duplication group.

    Weights:
    - Code savings: 40% (higher is better)
    - Complexity: 20% (lower is better - inverse)
    - Risk: 25% (lower is better - inverse)
    - Effort: 15% (lower is better - inverse)

    Args:
        lines_saved: Number of lines that would be removed by refactoring
        complexity: Complexity score from Phase 1 (1-10 scale)
        has_tests: Whether the code has test coverage
        affected_files: Number of files that would be modified
        external_call_sites: Number of external call sites to update

    Returns:
        Normalized score from 0-100 (higher = better candidate for refactoring)

    Examples:
        >>> calculate_deduplication_score(100, 3, True, 2, 5)
        75.0  # High savings, low complexity, tested = excellent candidate

        >>> calculate_deduplication_score(10, 8, False, 10, 50)
        25.0  # Low savings, high complexity, untested = poor candidate
    """
    # Normalize inputs to 0-1 scale

    # 1. Code savings (0-1): Higher is better
    # Cap at 500 lines for normalization, anything above is maxed out
    max_lines = 500
    savings_score = min(lines_saved / max_lines, 1.0)

    # 2. Complexity (0-1): Lower is better (inverse)
    # Complexity is 1-10, convert to 0-1 where 1=best (low complexity)
    complexity_score = 1.0 - ((complexity - 1) / 9.0)
    complexity_score = max(0.0, min(1.0, complexity_score))

    # 3. Risk (0-1): Lower is better (inverse)
    # Risk factors: no tests, high call sites
    risk_score = 0.0

    # No test coverage adds significant risk
    if not has_tests:
        risk_score += 0.5

    # Many external call sites increase risk
    # Cap at 20 call sites for normalization
    max_call_sites = 20
    call_site_risk = min(external_call_sites / max_call_sites, 0.5)
    risk_score += call_site_risk

    # Convert to inverse (1 = lowest risk)
    risk_score = 1.0 - risk_score

    # 4. Effort (0-1): Lower is better (inverse)
    # Effort based on affected files
    # Cap at 10 files for normalization
    max_files = 10
    effort_factor = min(affected_files / max_files, 1.0)
    effort_score = 1.0 - effort_factor

    # Apply weights
    # savings: 40%, complexity: 20%, risk: 25%, effort: 15%
    weighted_score = (
        (savings_score * 0.40) +
        (complexity_score * 0.20) +
        (risk_score * 0.25) +
        (effort_score * 0.15)
    )

    # Normalize to 0-100 scale
    final_score = round(weighted_score * 100, 1)

    return final_score


def rank_deduplication_candidates(
    candidates: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Rank deduplication candidates by their calculated scores.

    Takes a list of candidate dictionaries and returns them sorted by score
    (highest first). Each candidate should have the following fields:
    - lines_saved: int
    - complexity_score: int (1-10)
    - has_tests: bool
    - affected_files: int
    - external_call_sites: int

    The function adds a 'deduplication_score' field to each candidate.

    Args:
        candidates: List of candidate dictionaries with required fields

    Returns:
        Sorted list with scores added, highest score first
    """
    scored_candidates = []

    for candidate in candidates:
        score = calculate_deduplication_score(
            lines_saved=candidate.get('lines_saved', 0),
            complexity=candidate.get('complexity_score', 5),
            has_tests=candidate.get('has_tests', False),
            affected_files=candidate.get('affected_files', 1),
            external_call_sites=candidate.get('external_call_sites', 0)
        )

        # Create a copy with the score added
        scored_candidate = {**candidate, 'deduplication_score': score}
        scored_candidates.append(scored_candidate)

    # Sort by score descending (highest first)
    scored_candidates.sort(key=lambda x: x['deduplication_score'], reverse=True)

    return scored_candidates


# ============================================================================
# Phase 4.5: Recommendation Engine for Deduplication Analysis
# ============================================================================

def generate_deduplication_recommendation(
    score: float,
    complexity: int,
    lines_saved: int,
    has_tests: bool,
    affected_files: int
) -> Dict[str, Any]:
    """Generate actionable recommendations for deduplication candidates.

    Combines scoring factors to produce prioritized recommendations with
    multiple refactoring strategy options ranked by effort/value ratio.

    Args:
        score: Overall deduplication score (0-100)
        complexity: Cyclomatic complexity of the duplicated code
        lines_saved: Number of lines that would be saved by deduplication
        has_tests: Whether the duplicated code has test coverage
        affected_files: Number of files containing the duplicate

    Returns:
        Dictionary containing:
        - recommendation_text: Human-readable recommendation
        - strategies: List of refactoring strategies with details
        - priority: Priority level (high/medium/low)
        - effort_value_ratio: Numeric ratio (higher = better value)
    """
    # Calculate effort estimate based on complexity and affected files
    base_effort = complexity * 0.3 + affected_files * 0.5
    if not has_tests:
        base_effort *= 1.5  # Higher effort without test safety net

    # Calculate value based on lines saved and affected files
    value = lines_saved * 0.4 + affected_files * 10

    # Avoid division by zero
    effort_value_ratio = value / max(base_effort, 1)

    # Generate recommendation text based on score
    if score > 80:
        recommendation_text = "High Value: Extract to shared utility"
        priority = "high"
    elif score >= 50:
        recommendation_text = "Medium Value: Consider refactoring"
        priority = "medium"
    else:
        recommendation_text = "Low Value: May not be worth refactoring"
        priority = "low"

    # Generate strategy options ranked by suitability
    strategies = _generate_dedup_refactoring_strategies(
        complexity=complexity,
        lines_saved=lines_saved,
        has_tests=has_tests,
        affected_files=affected_files,
        score=score
    )

    return {
        "recommendation_text": recommendation_text,
        "strategies": strategies,
        "priority": priority,
        "effort_value_ratio": round(effort_value_ratio, 2)
    }


def _generate_dedup_refactoring_strategies(
    complexity: int,
    lines_saved: int,
    has_tests: bool,
    affected_files: int,
    score: float
) -> List[Dict[str, Any]]:
    """Generate ranked list of refactoring strategies for a duplication candidate.

    Evaluates multiple strategies and ranks them by suitability based on
    the characteristics of the duplicated code.

    Args:
        complexity: Cyclomatic complexity
        lines_saved: Lines that would be saved
        has_tests: Whether tests exist
        affected_files: Number of affected files
        score: Overall duplication score

    Returns:
        List of strategy dictionaries with name, description, suitability_score
    """
    strategies: List[Dict[str, Any]] = []

    # Strategy 1: Extract Function
    # Best for simple, stateless duplicates
    extract_fn_score = 70.0
    if complexity <= 5:
        extract_fn_score += 20
    elif complexity > 10:
        extract_fn_score -= 20
    if lines_saved >= 10:
        extract_fn_score += 10
    if affected_files >= 3:
        extract_fn_score += 10

    strategies.append({
        "name": "extract_function",
        "description": "Extract duplicate code into a shared function",
        "suitability_score": min(100, max(0, extract_fn_score)),
        "effort": "low" if complexity <= 5 else "medium",
        "risk": "low" if has_tests else "medium",
        "best_for": "Simple, stateless duplicates with clear inputs/outputs"
    })

    # Strategy 2: Extract Class
    # Best for stateful or complex duplicates
    extract_class_score = 50.0
    if complexity > 10:
        extract_class_score += 30
    elif complexity > 5:
        extract_class_score += 15
    if lines_saved >= 20:
        extract_class_score += 15
    if affected_files >= 2:
        extract_class_score += 10
    # Penalty for very simple code
    if complexity <= 3 and lines_saved < 10:
        extract_class_score -= 20

    strategies.append({
        "name": "extract_class",
        "description": "Extract duplicate code into a shared class with state",
        "suitability_score": min(100, max(0, extract_class_score)),
        "effort": "medium" if complexity <= 10 else "high",
        "risk": "medium" if has_tests else "high",
        "best_for": "Complex duplicates with shared state or multiple related functions"
    })

    # Strategy 3: Inline (keep duplication)
    # Best when duplication is intentional or low value
    inline_score = 30.0
    if score < 40:
        inline_score += 40
    elif score < 60:
        inline_score += 20
    if affected_files == 1:
        inline_score += 20
    if lines_saved < 5:
        inline_score += 20
    # Strong penalty for high-value duplicates
    if score > 80:
        inline_score -= 30

    strategies.append({
        "name": "inline",
        "description": "Keep code duplicated (intentional duplication)",
        "suitability_score": min(100, max(0, inline_score)),
        "effort": "none",
        "risk": "none",
        "best_for": "Intentional duplication, very small code blocks, or domain-specific variations"
    })

    # Sort strategies by suitability score (highest first)
    strategies.sort(key=lambda s: s["suitability_score"], reverse=True)

    return strategies


# ============================================================================
# Phase 4.3: Test Coverage Detection for Deduplication Analysis
# ============================================================================

def find_test_file_patterns(language: str) -> list[str]:
    """Get test file patterns for a given programming language.

    Args:
        language: Programming language (python, javascript, typescript, java, etc.)

    Returns:
        List of glob patterns for test files in that language
    """
    lang = language.lower()

    if lang == "python":
        return [
            "test_*.py",
            "*_test.py",
            "tests/*.py",
            "**/tests/*.py",
            "**/test/*.py",
            "**/*_test.py",
            "**/test_*.py",
        ]
    elif lang in ("javascript", "js"):
        return [
            "*.test.js",
            "*.spec.js",
            "__tests__/*.js",
            "**/__tests__/*.js",
            "**/tests/*.js",
            "**/test/*.js",
            "**/*.test.js",
            "**/*.spec.js",
        ]
    elif lang in ("typescript", "ts", "tsx"):
        return [
            "*.test.ts",
            "*.test.tsx",
            "*.spec.ts",
            "*.spec.tsx",
            "__tests__/*.ts",
            "__tests__/*.tsx",
            "**/__tests__/*.ts",
            "**/__tests__/*.tsx",
            "**/tests/*.ts",
            "**/tests/*.tsx",
            "**/*.test.ts",
            "**/*.test.tsx",
            "**/*.spec.ts",
            "**/*.spec.tsx",
        ]
    elif lang == "java":
        return [
            "*Test.java",
            "*Tests.java",
            "**/*Test.java",
            "**/*Tests.java",
            "**/test/**/*.java",
            "src/test/**/*.java",
        ]
    elif lang == "go":
        return [
            "*_test.go",
            "**/*_test.go",
        ]
    elif lang in ("ruby", "rb"):
        return [
            "*_test.rb",
            "*_spec.rb",
            "test/*.rb",
            "spec/*.rb",
            "**/test/*.rb",
            "**/spec/*.rb",
            "**/*_test.rb",
            "**/*_spec.rb",
        ]
    elif lang in ("rust", "rs"):
        return [
            "**/tests/*.rs",
            "**/tests/**/*.rs",
        ]
    elif lang in ("csharp", "cs", "c#"):
        return [
            "*Tests.cs",
            "*Test.cs",
            "**/*Tests.cs",
            "**/*Test.cs",
            "**/Tests/**/*.cs",
        ]
    else:
        # Generic patterns for unknown languages
        return [
            "**/test*",
            "**/tests/*",
            "**/*test*",
            "**/*spec*",
        ]


def _get_potential_test_paths(file_path: str, language: str, project_root: str) -> list[str]:
    """Generate potential test file paths for a source file.

    Args:
        file_path: Path to the source file
        language: Programming language
        project_root: Root directory of the project

    Returns:
        List of potential test file paths that could contain tests for this file
    """
    # Get relative path from project root
    try:
        rel_path = os.path.relpath(file_path, project_root)
    except ValueError:
        rel_path = os.path.basename(file_path)

    # Get base name without extension
    basename = os.path.basename(file_path)
    name_without_ext = os.path.splitext(basename)[0]
    ext = os.path.splitext(basename)[1]
    dir_path = os.path.dirname(rel_path)

    potential_paths: list[str] = []
    lang = language.lower()

    if lang == "python":
        # test_<name>.py, <name>_test.py
        potential_paths.extend([
            os.path.join(project_root, dir_path, f"test_{name_without_ext}.py"),
            os.path.join(project_root, dir_path, f"{name_without_ext}_test.py"),
            os.path.join(project_root, "tests", f"test_{name_without_ext}.py"),
            os.path.join(project_root, "tests", dir_path, f"test_{name_without_ext}.py"),
            os.path.join(project_root, "test", f"test_{name_without_ext}.py"),
            os.path.join(project_root, "tests", "unit", f"test_{name_without_ext}.py"),
            os.path.join(project_root, "tests", "integration", f"test_{name_without_ext}.py"),
        ])

    elif lang in ("javascript", "js"):
        potential_paths.extend([
            os.path.join(project_root, dir_path, f"{name_without_ext}.test.js"),
            os.path.join(project_root, dir_path, f"{name_without_ext}.spec.js"),
            os.path.join(project_root, dir_path, "__tests__", f"{name_without_ext}.js"),
            os.path.join(project_root, "tests", f"{name_without_ext}.test.js"),
            os.path.join(project_root, "__tests__", f"{name_without_ext}.js"),
        ])

    elif lang in ("typescript", "ts", "tsx"):
        # Handle both .ts and .tsx
        ts_ext = ".tsx" if ext == ".tsx" else ".ts"
        potential_paths.extend([
            os.path.join(project_root, dir_path, f"{name_without_ext}.test{ts_ext}"),
            os.path.join(project_root, dir_path, f"{name_without_ext}.spec{ts_ext}"),
            os.path.join(project_root, dir_path, "__tests__", f"{name_without_ext}{ts_ext}"),
            os.path.join(project_root, "tests", f"{name_without_ext}.test{ts_ext}"),
            os.path.join(project_root, "__tests__", f"{name_without_ext}{ts_ext}"),
        ])

    elif lang == "java":
        # Convert class name: MyClass.java -> MyClassTest.java
        potential_paths.extend([
            os.path.join(project_root, dir_path, f"{name_without_ext}Test.java"),
            os.path.join(project_root, dir_path, f"{name_without_ext}Tests.java"),
            # Maven/Gradle standard: src/test/java mirrors src/main/java
            os.path.join(project_root, "src", "test", "java",
                        dir_path.replace("src/main/java/", "").replace("src\\main\\java\\", ""),
                        f"{name_without_ext}Test.java"),
        ])

    elif lang == "go":
        potential_paths.extend([
            os.path.join(project_root, dir_path, f"{name_without_ext}_test.go"),
        ])

    elif lang in ("ruby", "rb"):
        potential_paths.extend([
            os.path.join(project_root, dir_path, f"{name_without_ext}_test.rb"),
            os.path.join(project_root, dir_path, f"{name_without_ext}_spec.rb"),
            os.path.join(project_root, "test", f"{name_without_ext}_test.rb"),
            os.path.join(project_root, "spec", f"{name_without_ext}_spec.rb"),
        ])

    return [os.path.normpath(p) for p in potential_paths]


def _check_test_file_references_source(
    test_file_path: str,
    source_file_path: str,
    language: str
) -> bool:
    """Check if a test file references/imports the source file.

    Args:
        test_file_path: Path to the test file
        source_file_path: Path to the source file being tested
        language: Programming language

    Returns:
        True if the test file appears to test the source file
    """
    import re as regex_module

    if not os.path.exists(test_file_path):
        return False

    try:
        with open(test_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except (IOError, OSError):
        return False

    # Get the module/class name from source file
    source_name = os.path.splitext(os.path.basename(source_file_path))[0]
    lang = language.lower()

    # Check for imports/references based on language
    if lang == "python":
        # Check for: from <module> import, import <module>
        import_patterns = [
            f"from {source_name} import",
            f"from .{source_name} import",
            f"import {source_name}",
            f"from.*{source_name}.*import",
        ]
        for pattern in import_patterns:
            if regex_module.search(pattern, content, regex_module.IGNORECASE):
                return True

    elif lang in ("javascript", "js", "typescript", "ts", "tsx"):
        # Check for: require('<module>'), import from '<module>'
        import_patterns = [
            f"from ['\"].*{source_name}['\"]",
            f"require\\(['\"].*{source_name}['\"]\\)",
            f"import.*{source_name}",
        ]
        for pattern in import_patterns:
            if regex_module.search(pattern, content, regex_module.IGNORECASE):
                return True

    elif lang == "java":
        # Check for: import <package>.<ClassName>
        class_name = source_name
        if regex_module.search(f"import.*\\.{class_name};", content):
            return True
        # Also check if class name is directly used
        if regex_module.search(f"\\b{class_name}\\b", content):
            return True

    elif lang == "go":
        # Go test files in same directory automatically have access
        source_dir = os.path.dirname(source_file_path)
        test_dir = os.path.dirname(test_file_path)
        if os.path.normpath(source_dir) == os.path.normpath(test_dir):
            return True
        # Check for package import
        if regex_module.search(f"import.*{source_name}", content):
            return True

    elif lang in ("ruby", "rb"):
        # Check for require/require_relative
        if regex_module.search(f"require.*{source_name}", content, regex_module.IGNORECASE):
            return True

    # Fallback: check if source file name appears anywhere in test
    if source_name.lower() in content.lower():
        return True

    return False


def has_test_coverage(file_path: str, language: str, project_root: str) -> bool:
    """Check if a source file has corresponding test coverage.

    Args:
        file_path: Path to the source file
        language: Programming language
        project_root: Root directory of the project

    Returns:
        True if test coverage exists for the file
    """
    import glob as glob_module

    logger = get_logger("duplication.test_coverage")

    # Get potential test file paths
    potential_tests = _get_potential_test_paths(file_path, language, project_root)

    # Check if any potential test file exists
    for test_path in potential_tests:
        if os.path.exists(test_path):
            logger.debug(
                "found_test_file",
                source_file=file_path,
                test_file=test_path
            )
            return True

    # Also search using glob patterns for more flexible matching
    patterns = find_test_file_patterns(language)

    for pattern in patterns:
        full_pattern = os.path.join(project_root, pattern)
        try:
            matches = glob_module.glob(full_pattern, recursive=True)
            for match in matches:
                # Check if this test file references our source
                if _check_test_file_references_source(match, file_path, language):
                    logger.debug(
                        "found_test_by_reference",
                        source_file=file_path,
                        test_file=match
                    )
                    return True
        except Exception as e:
            logger.warning("glob_search_failed", pattern=pattern, error=str(e))
            continue

    logger.debug("no_test_coverage", source_file=file_path)
    return False


def get_test_coverage_for_files(
    file_paths: list[str],
    language: str,
    project_root: str
) -> dict[str, bool]:
    """Get test coverage status for multiple files.

    Args:
        file_paths: List of source file paths
        language: Programming language
        project_root: Root directory of the project

    Returns:
        Dictionary mapping file paths to their test coverage status
    """
    logger = get_logger("duplication.test_coverage_batch")

    coverage_map: dict[str, bool] = {}
    covered_count = 0

    for file_path in file_paths:
        has_coverage = has_test_coverage(file_path, language, project_root)
        coverage_map[file_path] = has_coverage
        if has_coverage:
            covered_count += 1

    logger.info(
        "test_coverage_analysis_complete",
        total_files=len(file_paths),
        files_with_coverage=covered_count,
        files_without_coverage=len(file_paths) - covered_count
    )

    return coverage_map


# =============================================================================
# Phase 5: Enhanced Reporting for Deduplication
# =============================================================================


def format_diff_with_colors(diff: str) -> str:
    """Add ANSI color codes to a unified diff for CLI display.

    Args:
        diff: Unified diff string

    Returns:
        Diff string with ANSI color codes:
        - Green for additions (+)
        - Red for deletions (-)
        - Cyan for hunk headers (@@)
        - Yellow for file headers (--- / +++)
    """
    if not diff:
        return diff

    # ANSI color codes
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    RESET = "\033[0m"

    colored_lines = []
    for line in diff.split('\n'):
        if line.startswith('+++') or line.startswith('---'):
            colored_lines.append(f"{YELLOW}{line}{RESET}")
        elif line.startswith('@@'):
            colored_lines.append(f"{CYAN}{line}{RESET}")
        elif line.startswith('+'):
            colored_lines.append(f"{GREEN}{line}{RESET}")
        elif line.startswith('-'):
            colored_lines.append(f"{RED}{line}{RESET}")
        else:
            colored_lines.append(line)

    return '\n'.join(colored_lines)


def generate_before_after_example(
    original_code: str,
    replacement_code: str,
    function_name: str
) -> Dict[str, Any]:
    """Generate before/after code examples for a duplication extraction.

    Creates readable code snippets showing the original duplicate code
    and how it looks after extraction into a reusable function.

    Args:
        original_code: The original duplicate code snippet
        replacement_code: The replacement code (function call)
        function_name: Name of the extracted function

    Returns:
        Dictionary containing:
        - before: Original code snippet with context
        - after: Code with extracted function call
        - function_definition: The extracted function's signature
        - explanation: Human-readable explanation of the change
    """
    # Clean up the code snippets
    original_lines = original_code.strip().split('\n')
    replacement_lines = replacement_code.strip().split('\n')

    # Calculate metrics
    original_line_count = len(original_lines)
    replacement_line_count = len(replacement_lines)
    lines_saved = original_line_count - replacement_line_count

    # Format the before section with line numbers
    before_formatted = []
    for i, line in enumerate(original_lines, 1):
        before_formatted.append(f"{i:3d} | {line}")

    # Format the after section with line numbers
    after_formatted = []
    for i, line in enumerate(replacement_lines, 1):
        after_formatted.append(f"{i:3d} | {line}")

    # Generate a simple function signature based on name
    function_definition = f"def {function_name}(...):"

    # Create explanation
    if lines_saved > 0:
        explanation = (
            f"Extracted {original_line_count} lines of duplicate code into "
            f"'{function_name}', reducing to {replacement_line_count} line(s). "
            f"This saves {lines_saved} line(s) per occurrence."
        )
    else:
        explanation = (
            f"Refactored code into '{function_name}' for better reusability "
            f"and maintainability."
        )

    return {
        "before": '\n'.join(before_formatted),
        "after": '\n'.join(after_formatted),
        "before_raw": original_code.strip(),
        "after_raw": replacement_code.strip(),
        "function_definition": function_definition,
        "function_name": function_name,
        "original_lines": original_line_count,
        "replacement_lines": replacement_line_count,
        "lines_saved": lines_saved,
        "explanation": explanation
    }


def visualize_complexity(score: int) -> Dict[str, Any]:
    """Create a visual complexity indicator with recommendations.

    Args:
        score: Complexity score from 1-10

    Returns:
        Dictionary containing:
        - bar: ASCII bar visualization
        - description: Text description (Low/Medium/High)
        - color_code: ANSI color code for CLI
        - recommendations: List of actionable recommendations
        - score: The input score
    """
    # Clamp score to valid range
    score = max(1, min(10, score))

    # Determine description and color based on score
    if score <= 3:
        description = "Low"
        color_code = "\033[32m"  # Green
        recommendations = [
            "Good candidate for quick refactoring",
            "Consider extracting as a simple helper function",
            "Low risk of introducing bugs during extraction"
        ]
    elif score <= 6:
        description = "Medium"
        color_code = "\033[33m"  # Yellow
        recommendations = [
            "Review the code carefully before extraction",
            "Consider adding unit tests before refactoring",
            "May benefit from breaking into smaller pieces",
            "Check for hidden dependencies or side effects"
        ]
    else:
        description = "High"
        color_code = "\033[31m"  # Red
        recommendations = [
            "High complexity - proceed with caution",
            "Strongly recommend comprehensive test coverage first",
            "Consider incremental refactoring in smaller steps",
            "Review for cyclomatic complexity and reduce branches",
            "May need architectural review before extraction"
        ]

    reset_code = "\033[0m"

    # Create ASCII bar visualization
    filled = score
    empty = 10 - score
    bar_plain = f"[{'=' * filled}{' ' * empty}] {score}/10"
    bar_colored = f"{color_code}[{'=' * filled}{' ' * empty}]{reset_code} {score}/10"

    return {
        "score": score,
        "bar": bar_plain,
        "bar_colored": bar_colored,
        "description": description,
        "color_code": color_code,
        "recommendations": recommendations,
        "formatted": f"{description} Complexity ({score}/10): {bar_plain}"
    }


@dataclass
class EnhancedDuplicationCandidate:
    """Enhanced duplication candidate with full reporting details.

    Attributes:
        id: Unique identifier for this candidate
        files: List of file paths containing the duplicate
        locations: List of (file, start_line, end_line) tuples
        original_code: The duplicate code snippet
        suggested_function_name: Suggested name for extracted function
        replacement_code: Code to replace each occurrence
        similarity_score: How similar the duplicates are (0-100)
        complexity_score: Complexity rating (1-10)
        before_after: Before/after example dict
        complexity_viz: Complexity visualization dict
        diff_preview: Diff preview for all files
        priority: Priority ranking (higher = more important)
    """
    id: str
    files: List[str]
    locations: List[Tuple[str, int, int]]
    original_code: str
    suggested_function_name: str
    replacement_code: str
    similarity_score: float
    complexity_score: int
    before_after: Dict[str, Any]
    complexity_viz: Dict[str, Any]
    diff_preview: Optional[str]
    priority: int


def create_enhanced_duplication_response(
    candidates: List[Dict[str, Any]],
    include_diffs: bool = True,
    include_colors: bool = False
) -> Dict[str, Any]:
    """Create an enhanced duplication detection response.

    This is the main entry point for Phase 5 enhanced reporting.
    Takes raw duplication candidates and enriches them with:
    - Before/after examples
    - Complexity visualizations
    - Colored diffs (optional)
    - Actionable recommendations

    Args:
        candidates: List of raw duplication candidates with keys:
            - files: List of file paths
            - locations: List of (file, start, end) tuples
            - code: The duplicate code
            - function_name: Suggested function name
            - replacement: Replacement code
            - similarity: Similarity score (0-100)
            - complexity: Complexity score (1-10)
        include_diffs: Whether to generate diff previews
        include_colors: Whether to include ANSI color codes

    Returns:
        Enhanced response dictionary with:
        - candidates: List of EnhancedDuplicationCandidate as dicts
        - summary: Overall summary statistics
        - recommendations: Global recommendations
        - metadata: Response metadata
    """
    enhanced_candidates = []
    total_lines_saveable = 0
    complexity_distribution = {"low": 0, "medium": 0, "high": 0}

    for idx, candidate in enumerate(candidates):
        # Generate before/after example
        before_after = generate_before_after_example(
            original_code=candidate.get("code", ""),
            replacement_code=candidate.get("replacement", ""),
            function_name=candidate.get("function_name", f"extracted_function_{idx}")
        )

        # Generate complexity visualization
        complexity = candidate.get("complexity", 5)
        complexity_viz = visualize_complexity(complexity)

        # Track complexity distribution
        if complexity <= 3:
            complexity_distribution["low"] += 1
        elif complexity <= 6:
            complexity_distribution["medium"] += 1
        else:
            complexity_distribution["high"] += 1

        # Generate diff preview if requested
        diff_preview = None
        if include_diffs and "files" in candidate:
            file_changes = []
            original_code = candidate.get("code", "")
            replacement = candidate.get("replacement", "")

            for file_path in candidate.get("files", []):
                # For demonstration, create a simple diff
                # In real usage, this would read actual file contents
                file_changes.append({
                    "file_path": file_path,
                    "original_content": original_code,
                    "new_content": replacement
                })

            if file_changes:
                preview = generate_multi_file_diff(file_changes, context_lines=3)
                diff_text = preview.combined_diff
                if include_colors:
                    diff_text = format_diff_with_colors(diff_text)
                diff_preview = diff_text

        # Calculate priority based on multiple factors
        occurrences = len(candidate.get("files", []))
        lines = before_after["original_lines"]
        priority = (occurrences * 10) + (lines * 2) - (complexity * 3)

        # Track total saveable lines
        total_lines_saveable += before_after["lines_saved"] * occurrences

        # Get function name with fallback
        function_name = candidate.get("function_name", "") or f"extracted_function_{idx}"

        enhanced_candidate = {
            "id": f"DUP-{idx + 1:03d}",
            "files": candidate.get("files", []),
            "locations": candidate.get("locations", []),
            "original_code": candidate.get("code", ""),
            "suggested_function_name": function_name,
            "replacement_code": candidate.get("replacement", ""),
            "similarity_score": candidate.get("similarity", 100.0),
            "complexity_score": complexity,
            "before_after": before_after,
            "complexity_viz": complexity_viz,
            "diff_preview": diff_preview,
            "priority": priority
        }

        enhanced_candidates.append(enhanced_candidate)

    # Sort by priority (highest first)
    enhanced_candidates.sort(key=lambda x: x["priority"], reverse=True)

    # Generate global recommendations
    global_recommendations = []

    if complexity_distribution["high"] > 0:
        global_recommendations.append(
            f"Found {complexity_distribution['high']} high-complexity duplicates. "
            "Consider adding tests before refactoring these."
        )

    if total_lines_saveable > 50:
        global_recommendations.append(
            f"Potential to save {total_lines_saveable} total lines of code. "
            "Prioritize candidates by their priority score."
        )

    if len(enhanced_candidates) > 5:
        global_recommendations.append(
            "Many duplicates found. Consider addressing high-priority items first "
            "to maximize impact with minimal effort."
        )

    # Build summary
    summary = {
        "total_candidates": len(enhanced_candidates),
        "total_files_affected": len(set(
            f for c in candidates for f in c.get("files", [])
        )),
        "total_lines_saveable": total_lines_saveable,
        "complexity_distribution": complexity_distribution,
        "highest_priority_id": enhanced_candidates[0]["id"] if enhanced_candidates else None
    }

    return {
        "candidates": enhanced_candidates,
        "summary": summary,
        "recommendations": global_recommendations,
        "metadata": {
            "version": "5.0",
            "includes_diffs": include_diffs,
            "includes_colors": include_colors,
            "generated_at": datetime.now().isoformat()
        }
    }


# =============================================================================
# COMPLEXITY ANALYSIS - Phase 1 (Code Analysis & Metrics)
# =============================================================================

# Complexity analysis data classes
@dataclass
class ComplexityMetrics:
    """Immutable metrics container for a single function."""
    cyclomatic: int
    cognitive: int
    nesting_depth: int
    lines: int
    parameter_count: int = 0


@dataclass
class FunctionComplexity:
    """Complete analysis result for one function."""
    file_path: str
    function_name: str
    start_line: int
    end_line: int
    metrics: ComplexityMetrics
    language: str
    exceeds: List[str] = field(default_factory=list)


@dataclass
class ComplexityThresholds:
    """Configurable thresholds with sensible defaults."""
    cyclomatic: int = 10
    cognitive: int = 15
    nesting_depth: int = 4
    lines: int = 50


# Language-specific AST patterns for complexity analysis
COMPLEXITY_PATTERNS: Dict[str, Dict[str, Any]] = {
    "python": {
        "function": "def $NAME($$$)",
        "async_function": "async def $NAME($$$)",
        "branches": [
            "if $COND:",
            "elif $COND:",
            "for $VAR in $ITER:",
            "while $COND:",
            "except $TYPE:",
            "except:",
            "with $CTX:",
            "case $PATTERN:",
        ],
        "logical_operators": [
            "$A and $B",
            "$A or $B",
        ],
        "nesting_constructs": ["if", "for", "while", "with", "try", "match"],
    },
    "typescript": {
        "function": "function $NAME($$$) { $$$ }",
        "arrow_function": "const $NAME = ($$$) => { $$$ }",
        "method": "$NAME($$$) { $$$ }",
        "branches": [
            "if ($COND) { $$$ }",
            "for ($INIT; $COND; $INC) { $$$ }",
            "for ($VAR of $ITER) { $$$ }",
            "for ($VAR in $OBJ) { $$$ }",
            "while ($COND) { $$$ }",
            "switch ($EXPR) { $$$ }",
            "case $VAL:",
            "catch ($ERR) { $$$ }",
            "$COND ? $A : $B",
        ],
        "logical_operators": [
            "$A && $B",
            "$A || $B",
            "$A ?? $B",
        ],
        "nesting_constructs": ["if", "for", "while", "switch", "try"],
    },
    "javascript": {
        "function": "function $NAME($$$) { $$$ }",
        "arrow_function": "const $NAME = ($$$) => { $$$ }",
        "method": "$NAME($$$) { $$$ }",
        "branches": [
            "if ($COND) { $$$ }",
            "for ($INIT; $COND; $INC) { $$$ }",
            "for ($VAR of $ITER) { $$$ }",
            "for ($VAR in $OBJ) { $$$ }",
            "while ($COND) { $$$ }",
            "switch ($EXPR) { $$$ }",
            "case $VAL:",
            "catch ($ERR) { $$$ }",
            "$COND ? $A : $B",
        ],
        "logical_operators": [
            "$A && $B",
            "$A || $B",
            "$A ?? $B",
        ],
        "nesting_constructs": ["if", "for", "while", "switch", "try"],
    },
    "java": {
        "function": "$TYPE $NAME($$$) { $$$ }",
        "branches": [
            "if ($COND) { $$$ }",
            "for ($INIT; $COND; $INC) { $$$ }",
            "for ($TYPE $VAR : $ITER) { $$$ }",
            "while ($COND) { $$$ }",
            "switch ($EXPR) { $$$ }",
            "case $VAL:",
            "catch ($TYPE $VAR) { $$$ }",
            "$COND ? $A : $B",
        ],
        "logical_operators": [
            "$A && $B",
            "$A || $B",
        ],
        "nesting_constructs": ["if", "for", "while", "switch", "try"],
    },
}


def get_complexity_patterns(language: str) -> Dict[str, Any]:
    """Get AST patterns for a specific language.

    Args:
        language: Programming language name

    Returns:
        Dictionary of patterns for the language
    """
    lang_lower = language.lower()
    if lang_lower in COMPLEXITY_PATTERNS:
        return COMPLEXITY_PATTERNS[lang_lower]
    # Default to Python patterns
    return COMPLEXITY_PATTERNS["python"]


def count_pattern_matches(code: str, pattern: str, language: str) -> int:
    """Count occurrences of an AST pattern in code using ast-grep.

    Args:
        code: Source code to analyze
        pattern: ast-grep pattern to search for
        language: Programming language

    Returns:
        Number of matches found
    """
    try:
        result = subprocess.run(
            ["ast-grep", "run", "--pattern", pattern, "--lang", language, "--json"],
            input=code,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            matches = json.loads(result.stdout)
            return len(matches) if isinstance(matches, list) else 0
        return 0
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return 0


def calculate_cyclomatic_complexity(code: str, language: str) -> int:
    """Calculate McCabe cyclomatic complexity.

    Cyclomatic complexity = E - N + 2P
    Simplified: 1 + number of decision points

    Args:
        code: Function source code
        language: Programming language

    Returns:
        Cyclomatic complexity score (minimum 1)
    """
    complexity = 1  # Base complexity

    # Language-specific keywords that represent decision points
    if language.lower() == "python":
        # Count decision keywords
        keywords = ['if ', 'elif ', 'for ', 'while ', 'except ', 'except:', 'with ', 'case ']
        operators = [' and ', ' or ']
    elif language.lower() in ["typescript", "javascript"]:
        keywords = ['if ', 'if(', 'for ', 'for(', 'while ', 'while(', 'switch ', 'switch(', 'case ', 'catch ', 'catch(', '? ']
        operators = [' && ', ' || ', ' ?? ']
    elif language.lower() == "java":
        keywords = ['if ', 'if(', 'for ', 'for(', 'while ', 'while(', 'switch ', 'switch(', 'case ', 'catch ', 'catch(']
        operators = [' && ', ' || ']
    else:
        # Default to Python-style
        keywords = ['if ', 'elif ', 'for ', 'while ', 'except ', 'case ']
        operators = [' and ', ' or ']

    # Count keywords
    for keyword in keywords:
        complexity += code.count(keyword)

    # Count logical operators
    for op in operators:
        complexity += code.count(op)

    return complexity


def calculate_cognitive_complexity(code: str, language: str) -> int:
    """Calculate cognitive complexity with nesting penalties.

    Based on SonarSource cognitive complexity specification:
    - +1 for each control flow break (if, for, while, catch, switch, etc.)
    - +N nesting penalty when nested (N = current nesting level)
    - +1 for each sequence of logical operators (not each operator)
    - else doesn't increment, but else if does

    Args:
        code: Function source code
        language: Programming language

    Returns:
        Cognitive complexity score
    """
    import re

    patterns = get_complexity_patterns(language)
    complexity = 0

    lines = code.split('\n')
    base_indent = None

    # Keywords that add +1 AND increase nesting level
    structural_keywords = patterns.get("nesting_constructs", [])

    # Language-specific adjustments
    if language.lower() in ("python",):
        # Python: elif is separate, else doesn't count
        control_flow = ["if", "elif", "for", "while", "except", "with"]
        # else doesn't add complexity in Python
    elif language.lower() in ("typescript", "javascript"):
        # JS/TS: catch, switch add; else if handled specially
        control_flow = ["if", "for", "while", "catch", "switch", "do"]
    elif language.lower() == "java":
        control_flow = ["if", "for", "while", "catch", "switch", "do"]
    else:
        control_flow = structural_keywords

    for line in lines:
        stripped = line.lstrip()
        if not stripped:
            continue

        # Skip comments
        if stripped.startswith('#') or stripped.startswith('//') or stripped.startswith('/*'):
            continue

        # Calculate current indentation for nesting level
        indent = len(line) - len(stripped)
        if base_indent is None and stripped:
            base_indent = indent

        # Estimate nesting level from indentation
        if base_indent is not None:
            indent_diff = indent - base_indent
            # Assume 4 spaces or 1 tab per level
            current_nesting = max(0, indent_diff // 4)
        else:
            current_nesting = 0

        # Check for control flow keywords
        keyword_found = False
        for keyword in control_flow:
            # Match keyword at start of line (after stripping)
            # Use word boundary to avoid matching 'format' when looking for 'for'
            pattern = rf'^{keyword}(?:\s|\(|:)'
            if re.match(pattern, stripped):
                # Handle else if / elif specially
                if keyword in ("elif",) or stripped.startswith("else if"):
                    # else if adds +1 but no nesting penalty (continues same branch)
                    complexity += 1
                else:
                    # Base increment + nesting penalty
                    complexity += 1
                    complexity += current_nesting
                keyword_found = True
                break

        # Handle 'else if' in C-style languages
        if not keyword_found and stripped.startswith("else if"):
            complexity += 1  # No nesting penalty for else if

        # Count logical operator sequences (not individual operators)
        # Each change from AND to OR or vice versa adds +1
        # "a && b && c" = +1, "a && b || c" = +2
        if language.lower() in ("python",):
            # Python uses 'and' and 'or'
            and_pattern = r'\band\b'
            or_pattern = r'\bor\b'
        else:
            # C-style uses && and ||
            and_pattern = r'&&'
            or_pattern = r'\|\|'

        and_matches = list(re.finditer(and_pattern, stripped))
        or_matches = list(re.finditer(or_pattern, stripped))

        if and_matches or or_matches:
            # Combine and sort by position
            all_ops = [(m.start(), 'and') for m in and_matches] + \
                      [(m.start(), 'or') for m in or_matches]
            all_ops.sort(key=lambda x: x[0])

            if all_ops:
                # Count sequences (changes in operator type)
                sequences = 1  # First sequence
                for i in range(1, len(all_ops)):
                    if all_ops[i][1] != all_ops[i-1][1]:
                        sequences += 1
                complexity += sequences

    return complexity


def calculate_nesting_depth(code: str, language: str) -> int:
    """Calculate maximum nesting depth.

    Args:
        code: Function source code
        language: Programming language

    Returns:
        Maximum nesting depth
    """
    lines = code.split('\n')
    max_depth = 0
    base_indent = None

    for line in lines:
        stripped = line.lstrip()
        if not stripped:
            continue

        indent = len(line) - len(stripped)
        if base_indent is None:
            base_indent = indent
            continue

        # Calculate depth from indentation difference
        indent_diff = indent - base_indent
        depth = max(0, indent_diff // 4)  # Assume 4 spaces per level
        max_depth = max(max_depth, depth)

    return max_depth


def extract_functions_from_file(file_path: str, language: str) -> List[Dict[str, Any]]:
    """Extract all functions from a file using ast-grep.

    Args:
        file_path: Path to source file
        language: Programming language

    Returns:
        List of function matches with metadata
    """
    patterns = get_complexity_patterns(language)
    all_functions: List[Dict[str, Any]] = []

    # Get all function patterns for this language
    function_patterns = []
    if "function" in patterns:
        function_patterns.append(patterns["function"])
    if "async_function" in patterns:
        function_patterns.append(patterns["async_function"])
    if "arrow_function" in patterns:
        function_patterns.append(patterns["arrow_function"])
    if "method" in patterns:
        function_patterns.append(patterns["method"])

    for pattern in function_patterns:
        try:
            result = subprocess.run(
                ["ast-grep", "run", "--pattern", pattern, "--lang", language, "--json", file_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                matches = json.loads(result.stdout)
                if isinstance(matches, list):
                    all_functions.extend(matches)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
            logger = get_logger("complexity.extract")
            logger.warning("extract_functions_failed", file=file_path, error=str(e))

    return all_functions


def _extract_classes_from_file(file_path: str, language: str) -> List[Dict[str, Any]]:
    """Extract all classes from a file using ast-grep.

    Args:
        file_path: Path to source file
        language: Programming language

    Returns:
        List of class info dicts with name, start_line, end_line, method_count
    """
    import re

    classes: List[Dict[str, Any]] = []

    # Define class patterns per language
    class_patterns = {
        "python": "class $NAME($$$): $$$",
        "typescript": "class $NAME { $$$ }",
        "javascript": "class $NAME { $$$ }",
        "java": "class $NAME { $$$ }"
    }

    pattern = class_patterns.get(language.lower(), class_patterns["python"])

    try:
        result = subprocess.run(
            ["ast-grep", "run", "--pattern", pattern, "--lang", language, "--json", file_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            matches = json.loads(result.stdout)
            if isinstance(matches, list):
                for match in matches:
                    # Extract class name
                    cls_name = "unknown"
                    meta_vars = match.get("metaVariables", {})
                    if "NAME" in meta_vars:
                        name_data = meta_vars["NAME"]
                        if isinstance(name_data, dict):
                            cls_name = name_data.get("text", "unknown")
                        elif isinstance(name_data, str):
                            cls_name = name_data

                    # Get line numbers
                    range_info = match.get("range", {})
                    start_line = range_info.get("start", {}).get("line", 0) + 1
                    end_line = range_info.get("end", {}).get("line", 0) + 1

                    # Count methods in class
                    code = match.get("text", "")
                    method_count = 0
                    if language.lower() == "python":
                        method_count = len(re.findall(r'^\s+def\s+', code, re.MULTILINE))
                    else:
                        # Count function/method patterns in class body
                        method_count = len(re.findall(r'^\s+\w+\s*\([^)]*\)\s*\{', code, re.MULTILINE))

                    classes.append({
                        "name": cls_name,
                        "start_line": start_line,
                        "end_line": end_line,
                        "method_count": method_count,
                        "code": code
                    })
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
        logger = get_logger("code_smell.extract_classes")
        logger.warning("extract_classes_failed", file=file_path, error=str(e))

    return classes


def _count_function_parameters(code: str, language: str) -> int:
    """Count the number of parameters in a function.

    Args:
        code: Function source code
        language: Programming language

    Returns:
        Number of parameters
    """
    import re

    # Find the parameter list
    if language.lower() == "python":
        # Match def name(params): or async def name(params):
        match = re.search(r'def\s+\w+\s*\(([^)]*)\)', code)
    else:
        # Match function name(params) { or (params) =>
        match = re.search(r'(?:function\s+\w+|\w+)\s*\(([^)]*)\)', code)

    if not match:
        return 0

    params = match.group(1).strip()
    if not params:
        return 0

    # Handle self/this as non-parameter
    if language.lower() == "python":
        # Remove 'self' and 'cls' from count
        params = re.sub(r'\bself\b\s*,?\s*', '', params)
        params = re.sub(r'\bcls\b\s*,?\s*', '', params)

    # Count commas + 1 (unless empty)
    params = params.strip()
    if not params:
        return 0

    # Handle default values and type annotations
    # Count actual parameters by splitting on commas at the right depth
    depth = 0
    param_count = 1 if params else 0
    for char in params:
        if char in '([{<':
            depth += 1
        elif char in ')]}>':
            depth -= 1
        elif char == ',' and depth == 0:
            param_count += 1

    return param_count


def _find_magic_numbers(content: str, lines: List[str], language: str) -> List[Dict[str, Any]]:
    """Find magic numbers in code.

    Magic numbers are hard-coded numeric literals that should be named constants.
    Excludes common values: 0, 1, -1, 2, 10, 100, 1000.

    Args:
        content: Full file content
        lines: List of lines in the file
        language: Programming language

    Returns:
        List of magic number findings with line and value
    """
    import re

    magic_numbers: List[Dict[str, Any]] = []

    # Common values that aren't magic
    allowed_values = {'0', '1', '-1', '2', '10', '100', '1000', '0.0', '1.0', '0.5'}

    # Patterns for different contexts to exclude
    exclude_patterns = [
        r'^\s*#',        # Python comments
        r'^\s*//',       # JS/Java comments
        r'^\s*\*',       # Multi-line comment continuation
        r'^\s*import',   # Import statements
        r'^\s*from',     # Python from imports
        r'=\s*\d+\s*$',  # Variable assignment (likely a constant definition)
        r'range\(',      # Range calls
        r'sleep\(',      # Sleep calls
        r'timeout',      # Timeout settings
        r'port\s*=',     # Port assignments
        r'version',      # Version numbers
    ]

    for line_num, line in enumerate(lines, 1):
        # Skip comments and certain patterns
        should_skip = False
        for pattern in exclude_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                should_skip = True
                break

        if should_skip:
            continue

        # Find all numeric literals in line
        # Match integers and floats, but not in string literals
        # This is a simplified approach - production would need AST
        numbers = re.findall(r'\b(\d+\.?\d*)\b', line)

        for num in numbers:
            if num not in allowed_values:
                # Check it's not in a string
                # Simple check: not between quotes
                before_num = line[:line.find(num)]
                quote_count = before_num.count('"') + before_num.count("'")
                if quote_count % 2 == 0:  # Even number of quotes = not in string
                    magic_numbers.append({
                        "line": line_num,
                        "value": num
                    })

    # Limit to avoid overwhelming output
    return magic_numbers[:50]


def analyze_file_complexity(
    file_path: str,
    language: str,
    thresholds: ComplexityThresholds
) -> List[FunctionComplexity]:
    """Analyze complexity of all functions in a file.

    Args:
        file_path: Path to source file
        language: Programming language
        thresholds: Complexity thresholds

    Returns:
        List of FunctionComplexity objects
    """
    results: List[FunctionComplexity] = []

    try:
        functions = extract_functions_from_file(file_path, language)

        for func in functions:
            code = func.get("text", "")
            if not code:
                continue

            # Extract function name from match
            # Try to get from metaVariables or parse from code
            func_name = "unknown"
            meta_vars = func.get("metaVariables", {})
            if "NAME" in meta_vars:
                name_data = meta_vars["NAME"]
                if isinstance(name_data, dict):
                    func_name = name_data.get("text", "unknown")
                elif isinstance(name_data, str):
                    func_name = name_data

            # Get line numbers
            range_info = func.get("range", {})
            start_line = range_info.get("start", {}).get("line", 0) + 1
            end_line = range_info.get("end", {}).get("line", 0) + 1

            # Calculate metrics
            cyclomatic = calculate_cyclomatic_complexity(code, language)
            cognitive = calculate_cognitive_complexity(code, language)
            nesting = calculate_nesting_depth(code, language)
            lines = len(code.split('\n'))

            # Count parameters (simple heuristic)
            param_count = 0
            if '(' in code and ')' in code:
                param_section = code[code.index('('):code.index(')')]
                if param_section.strip('()'):
                    param_count = param_section.count(',') + 1

            metrics = ComplexityMetrics(
                cyclomatic=cyclomatic,
                cognitive=cognitive,
                nesting_depth=nesting,
                lines=lines,
                parameter_count=param_count
            )

            # Check which thresholds are exceeded
            exceeds: List[str] = []
            if cyclomatic > thresholds.cyclomatic:
                exceeds.append("cyclomatic")
            if cognitive > thresholds.cognitive:
                exceeds.append("cognitive")
            if nesting > thresholds.nesting_depth:
                exceeds.append("nesting")
            if lines > thresholds.lines:
                exceeds.append("length")

            results.append(FunctionComplexity(
                file_path=file_path,
                function_name=func_name,
                start_line=start_line,
                end_line=end_line,
                metrics=metrics,
                language=language,
                exceeds=exceeds
            ))

    except Exception as e:
        logger = get_logger("complexity.analyze")
        logger.error("analyze_file_failed", file=file_path, error=str(e))

    return results


# =============================================================================
# Complexity Storage - SQLite Database
# =============================================================================

COMPLEXITY_DB_SCHEMA = '''
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_path TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analysis_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    commit_hash TEXT,
    branch_name TEXT,
    run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_functions INTEGER NOT NULL DEFAULT 0,
    total_files INTEGER NOT NULL DEFAULT 0,
    avg_cyclomatic REAL,
    avg_cognitive REAL,
    max_cyclomatic INTEGER,
    max_cognitive INTEGER,
    max_nesting INTEGER,
    threshold_violations INTEGER DEFAULT 0,
    analysis_duration_ms INTEGER,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS function_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    function_name TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    cyclomatic_complexity INTEGER NOT NULL,
    cognitive_complexity INTEGER NOT NULL,
    nesting_depth INTEGER NOT NULL,
    line_count INTEGER NOT NULL,
    parameter_count INTEGER,
    exceeds_threshold TEXT,
    FOREIGN KEY (run_id) REFERENCES analysis_runs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_runs_project_timestamp ON analysis_runs(project_id, run_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_runs_commit ON analysis_runs(commit_hash);
CREATE INDEX IF NOT EXISTS idx_function_metrics_run ON function_metrics(run_id);
CREATE INDEX IF NOT EXISTS idx_function_metrics_complexity ON function_metrics(cyclomatic_complexity DESC);
'''


class ComplexityStorage:
    """SQLite storage for complexity analysis results."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or self._get_default_db_path()
        self._init_db()

    def _get_default_db_path(self) -> Path:
        """Get default database path in user's data directory."""
        if platform.system() == "Darwin":
            base = Path.home() / "Library" / "Application Support" / "ast-grep-mcp"
        elif platform.system() == "Windows":
            base = Path(os.environ.get("APPDATA", str(Path.home()))) / "ast-grep-mcp"
        else:
            base = Path.home() / ".local" / "share" / "ast-grep-mcp"

        base.mkdir(parents=True, exist_ok=True)
        return base / "complexity.db"

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for database connections."""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.executescript(COMPLEXITY_DB_SCHEMA)

    def get_or_create_project(self, project_path: str) -> int:
        """Get or create project entry, return project ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT id FROM projects WHERE project_path = ?",
                (project_path,)
            )
            row = cursor.fetchone()
            if row:
                return int(row["id"])

            cursor = conn.execute(
                "INSERT INTO projects (project_path, name) VALUES (?, ?)",
                (project_path, Path(project_path).name)
            )
            return cursor.lastrowid or 0

    def store_analysis_run(
        self,
        project_path: str,
        results: Dict[str, Any],
        functions: List[FunctionComplexity],
        commit_hash: Optional[str] = None,
        branch_name: Optional[str] = None
    ) -> int:
        """Store complete analysis run with all metrics."""
        project_id = self.get_or_create_project(project_path)

        with self._get_connection() as conn:
            # Insert analysis run
            cursor = conn.execute('''
                INSERT INTO analysis_runs (
                    project_id, commit_hash, branch_name,
                    total_functions, total_files,
                    avg_cyclomatic, avg_cognitive,
                    max_cyclomatic, max_cognitive, max_nesting,
                    threshold_violations, analysis_duration_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                project_id, commit_hash, branch_name,
                results.get("total_functions", 0),
                results.get("total_files", 0),
                results.get("avg_cyclomatic"),
                results.get("avg_cognitive"),
                results.get("max_cyclomatic"),
                results.get("max_cognitive"),
                results.get("max_nesting"),
                results.get("violation_count", 0),
                results.get("duration_ms")
            ))
            run_id = cursor.lastrowid or 0

            # Bulk insert function metrics
            function_data = [
                (
                    run_id, f.file_path, f.function_name,
                    f.start_line, f.end_line,
                    f.metrics.cyclomatic, f.metrics.cognitive,
                    f.metrics.nesting_depth, f.metrics.lines,
                    f.metrics.parameter_count,
                    ",".join(f.exceeds) if f.exceeds else None
                )
                for f in functions
            ]

            if function_data:
                conn.executemany('''
                    INSERT INTO function_metrics (
                        run_id, file_path, function_name,
                        start_line, end_line,
                        cyclomatic_complexity, cognitive_complexity,
                        nesting_depth, line_count, parameter_count,
                        exceeds_threshold
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', function_data)

            return run_id

    def get_project_trends(
        self,
        project_path: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get complexity trends for a project over time."""
        with self._get_connection() as conn:
            cursor = conn.execute('''
                SELECT
                    ar.run_timestamp,
                    ar.commit_hash,
                    ar.branch_name,
                    ar.total_functions,
                    ar.avg_cyclomatic,
                    ar.avg_cognitive,
                    ar.max_cyclomatic,
                    ar.max_cognitive,
                    ar.threshold_violations
                FROM analysis_runs ar
                JOIN projects p ON ar.project_id = p.id
                WHERE p.project_path = ?
                    AND ar.run_timestamp >= datetime('now', ?)
                ORDER BY ar.run_timestamp ASC
            ''', (project_path, f'-{days} days'))
            return [dict(row) for row in cursor.fetchall()]


def run_mcp_server() -> None:  # pragma: no cover
    """
    Run the MCP server.
    This function is used to start the MCP server when this script is run directly.
    """
    parse_args_and_get_config()  # sets CONFIG_PATH
    init_sentry()  # Initialize Sentry error tracking (if SENTRY_DSN is set)
    register_mcp_tools()  # tools defined *after* CONFIG_PATH is known
    mcp.run(transport="stdio")

if __name__ == "__main__":  # pragma: no cover
    run_mcp_server()
