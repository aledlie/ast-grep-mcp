import argparse
import asyncio
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
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
    metadata: Dict[str, Any] = None  # Multi-line info, construct types, etc.

    def __post_init__(self):
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

    def __post_init__(self):
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
            header_suffix = _format_multiline_annotations(seg.metadata)
            output_parts.append(f"--- Block 1 [{seg.block1_start+1}-{seg.block1_end}]{header_suffix} ---")
            for line in seg.block1_text.split('\n'):
                output_parts.append(f"- {line}")
            output_parts.append(f"+++ Block 2 [{seg.block2_start+1}-{seg.block2_end}]{header_suffix} +++")
            for line in seg.block2_text.split('\n'):
                output_parts.append(f"+ {line}")

        elif seg.segment_type == 'deleted':
            header_suffix = _format_multiline_annotations(seg.metadata)
            output_parts.append(f"--- Block 1 [{seg.block1_start+1}-{seg.block1_end}] (deleted){header_suffix} ---")
            for line in seg.block1_text.split('\n'):
                output_parts.append(f"- {line}")

        elif seg.segment_type == 'inserted':
            header_suffix = _format_multiline_annotations(seg.metadata)
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
            is_generic=base_type.get("is_generic", False),
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


def _infer_single_value_type(value: str, language: str) -> Dict[str, str]:
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


def _parse_generic_type(value: str) -> Optional[Dict[str, str]]:
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


def _infer_from_identifier_name(identifier: str) -> Dict[str, str]:
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


def generate_function_signature(
    function_name: str,
    parameters: List[Dict[str, Any]],
    return_type: str = "None",
    language: str = "python"
) -> str:
    """Generate a function signature with inferred parameter types."""
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
        file_names: Dict[str, set] = {}
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
    import_sets: Dict[str, set] = {
        file_path: set(imports)
        for file_path, imports in file_imports.items()
    }

    # Get all unique imports across all files
    all_imports: set = set()
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
        other_imports: set = set()
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


def _identify_required_imports(code: str, all_imports: set, shared_imports: List[str]) -> List[str]:
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


def _extract_imported_names(import_stmt: str) -> set:
    """Extract the names made available by an import statement."""
    import re
    names: set = set()

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
    builtins: Dict[str, set] = {
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
