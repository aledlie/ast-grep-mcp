"""Configuration management for ast-grep MCP server."""

import argparse
import os
import sys
from typing import Any, Optional

import yaml

from ast_grep_mcp.constants import CacheDefaults
from ast_grep_mcp.core.exceptions import ConfigurationError
from ast_grep_mcp.core.logging import configure_logging, get_logger
from ast_grep_mcp.models.config import AstGrepConfig

# Global variable for config path (will be set by parse_args_and_get_config)
CONFIG_PATH: Optional[str] = None

# Global cache configuration (set by parse_args_and_get_config)
CACHE_ENABLED: bool = True
CACHE_SIZE: int = CacheDefaults.DEFAULT_CACHE_SIZE
CACHE_TTL: int = CacheDefaults.TTL_SECONDS

# Global cache instance (will be set after cache.py is extracted)
_query_cache: Optional[Any] = None


def _load_yaml_config(config_path: str) -> dict:
    if not os.path.exists(config_path):
        raise ConfigurationError(config_path, "File does not exist")
    if not os.path.isfile(config_path):
        raise ConfigurationError(config_path, "Path is not a file")
    try:
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigurationError(config_path, f"YAML parsing failed: {e}") from e
    except OSError as e:
        raise ConfigurationError(config_path, f"Failed to read file: {e}") from e
    if config_data is None:
        raise ConfigurationError(config_path, "Config file is empty")
    if not isinstance(config_data, dict):
        raise ConfigurationError(config_path, "Config must be a YAML dictionary")
    return config_data


def validate_config_file(config_path: str) -> AstGrepConfig:
    """Validate sgconfig.yaml file structure.

    Args:
        config_path: Path to sgconfig.yaml file

    Returns:
        Validated AstGrepConfig model

    Raises:
        ConfigurationError: If config file is invalid
    """
    config_data = _load_yaml_config(config_path)
    try:
        return AstGrepConfig(**config_data)
    except Exception as e:
        raise ConfigurationError(config_path, f"Validation failed: {e}") from e


def _add_cache_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--no-cache", action="store_true", help="Disable result caching for queries. Can also be set via CACHE_DISABLED=1 env var."
    )
    parser.add_argument(
        "--cache-size",
        type=int,
        metavar="N",
        default=None,
        help=(f"Maximum cached query results (default: {CacheDefaults.DEFAULT_CACHE_SIZE}). Also settable via CACHE_SIZE env var."),
    )
    parser.add_argument(
        "--cache-ttl",
        type=int,
        metavar="SECONDS",
        default=None,
        help=(f"Cache TTL in seconds (default: {CacheDefaults.TTL_SECONDS}). Also settable via CACHE_TTL env var."),
    )


def _create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.

    Returns:
        Configured ArgumentParser instance.
    """
    prog = "python main.py" if sys.argv[0].endswith("main.py") else None
    parser = argparse.ArgumentParser(
        prog=prog,
        description="ast-grep MCP Server - Provides structural code search capabilities via Model Context Protocol",
        epilog="""
environment variables:
  AST_GREP_CONFIG    Path to sgconfig.yaml file (overridden by --config flag)
  LOG_LEVEL          Logging level: DEBUG, INFO, WARNING, ERROR (default: INFO)
  LOG_FILE           Path to log file (logs to stderr by default)

For more information, see: https://github.com/ast-grep/ast-grep-mcp
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config",
        type=str,
        metavar="PATH",
        help="Path to sgconfig.yaml file for customizing ast-grep behavior (language mappings, rule directories, etc.)",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=None,
        metavar="LEVEL",
        help="Logging level (DEBUG, INFO, WARNING, ERROR). Can also be set via LOG_LEVEL env var. Default: INFO",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        metavar="PATH",
        default=None,
        help="Path to log file (logs to stderr by default). Can also be set via LOG_FILE env var.",
    )
    _add_cache_arguments(parser)
    return parser


def _try_validate_config(config_path: str) -> None:
    try:
        validate_config_file(config_path)
    except ConfigurationError as e:
        get_logger("config").error("config_validation_failed", config_path=config_path, error=str(e))
        sys.exit(1)


def _resolve_and_validate_config_path(args: argparse.Namespace) -> Optional[str]:
    """Resolve and validate config file path from args or environment.

    Precedence: --config flag > AST_GREP_CONFIG env > None

    Args:
        args: Parsed command-line arguments.

    Returns:
        Path to config file or None if not specified.

    Note:
        Calls sys.exit(1) if validation fails.
    """
    if args.config:
        _try_validate_config(args.config)
        return args.config
    if env_config := os.environ.get("AST_GREP_CONFIG"):
        _try_validate_config(env_config)
        return env_config
    return None


def _configure_logging_from_args(args: argparse.Namespace) -> None:
    """Configure logging based on command-line arguments and environment.

    Precedence: --log-level/--log-file flags > env vars > defaults

    Args:
        args: Parsed command-line arguments.
    """
    # Determine log level with precedence: --log-level flag > LOG_LEVEL env > INFO
    log_level = args.log_level or os.environ.get("LOG_LEVEL", "INFO")

    # Determine log file with precedence: --log-file flag > LOG_FILE env > None (stderr)
    log_file = args.log_file or os.environ.get("LOG_FILE")

    # Configure logging
    configure_logging(log_level=log_level, log_file=log_file)


def _resolve_int_from_env(env_key: str, default: int, warn_key: str) -> int:
    raw = os.environ.get(env_key)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        get_logger("cache.init").warning(warn_key, using_default=default)
        return default


def _configure_cache_from_args(args: argparse.Namespace) -> tuple[bool, int, int]:
    """Configure cache settings from command-line arguments and environment.

    Precedence: command-line flags > env vars > defaults

    Args:
        args: Parsed command-line arguments.

    Returns:
        Tuple of (cache_enabled, cache_size, cache_ttl).
    """
    cache_logger = get_logger("cache.init")

    cache_enabled = not (args.no_cache or bool(os.environ.get("CACHE_DISABLED")))

    if args.cache_size is not None:
        cache_size = args.cache_size
    else:
        cache_size = _resolve_int_from_env("CACHE_SIZE", CacheDefaults.DEFAULT_CACHE_SIZE, "invalid_cache_size_env")

    if args.cache_ttl is not None:
        cache_ttl = args.cache_ttl
    else:
        cache_ttl = _resolve_int_from_env("CACHE_TTL", CacheDefaults.CLEANUP_INTERVAL_SECONDS, "invalid_cache_ttl_env")

    cache_logger.info("cache_config", cache_enabled=cache_enabled, cache_size=cache_size, cache_ttl=cache_ttl)

    return cache_enabled, cache_size, cache_ttl


def parse_args_and_get_config() -> None:
    """Parse command-line arguments and determine config path."""
    global CONFIG_PATH, CACHE_ENABLED, CACHE_SIZE, CACHE_TTL

    # Parse arguments
    parser = _create_argument_parser()
    args = parser.parse_args()

    # Resolve and validate config
    CONFIG_PATH = _resolve_and_validate_config_path(args)

    # Configure logging
    _configure_logging_from_args(args)

    # Configure cache
    CACHE_ENABLED, CACHE_SIZE, CACHE_TTL = _configure_cache_from_args(args)
