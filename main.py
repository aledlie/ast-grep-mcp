import argparse
import asyncio
import difflib
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict, Generator, List, Literal, Optional, Tuple, cast

import httpx
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
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.SCHEMA_URL)
                response.raise_for_status()
                data = response.json()

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
                        "analysis_time_seconds": round(execution_time, 3)
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
            from collections import defaultdict

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
                    logger.warning(f"query_failed", query_id=query_id, error=str(e)[:200])
                    return (query_id, [])

            # Execute unconditional queries in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                futures = [executor.submit(execute_query, q) for q in unconditional_queries]
                for future in concurrent.futures.as_completed(futures):
                    query_id, matches = future.result()
                    results_by_id[query_id] = matches
                    queries_executed.append(query_id)

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
    backup_dir = os.path.join(project_folder, ".ast-grep-backups", backup_id)

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
    register_mcp_tools()  # tools defined *after* CONFIG_PATH is known
    mcp.run(transport="stdio")

if __name__ == "__main__":  # pragma: no cover
    run_mcp_server()
