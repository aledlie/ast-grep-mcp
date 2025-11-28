"""Search feature service - implements the core search functionality."""

import json
import time
from typing import Any, Dict, List, Literal, Union, cast

import sentry_sdk
import yaml

from ast_grep_mcp.core.cache import get_query_cache
from ast_grep_mcp.core.config import CACHE_ENABLED
from ast_grep_mcp.core.exceptions import InvalidYAMLError, NoMatchesError
from ast_grep_mcp.core.executor import (
    filter_files_by_size,
    run_ast_grep,
    stream_ast_grep_results,
)
from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.models.base import DumpFormat
from ast_grep_mcp.utils.formatters import format_matches_as_text


def dump_syntax_tree_impl(
    code: str,
    language: str,
    format: DumpFormat = "cst"
) -> str:
    """
    Implementation of dump_syntax_tree.

    Dump code's syntax structure or dump a query's pattern structure.
    This is useful to discover correct syntax kind and syntax tree structure.

    Args:
        code: The code to dump
        language: The language of the code
        format: Code dump format (pattern, ast, or cst)

    Returns:
        The syntax tree structure as a string

    Raises:
        AstGrepError: If ast-grep command fails
    """
    logger = get_logger("search.dump_syntax_tree")
    start_time = time.time()

    logger.info(
        "dump_syntax_tree_started",
        language=language,
        format=format,
        code_length=len(code)
    )

    try:
        result = run_ast_grep("run", ["--pattern", code, "--lang", language, f"--debug-query={format}"])
        output = result.stderr.strip()

        execution_time = time.time() - start_time
        logger.info(
            "dump_syntax_tree_completed",
            execution_time_seconds=round(execution_time, 3),
            output_length=len(output),
            status="success"
        )

        return output
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            "dump_syntax_tree_failed",
            execution_time_seconds=round(execution_time, 3),
            error=str(e)[:200],
            status="failed"
        )
        sentry_sdk.capture_exception(e, extras={
            "function": "dump_syntax_tree_impl",
            "language": language,
            "format": format,
            "code_length": len(code),
            "execution_time_seconds": round(execution_time, 3)
        })
        raise


def test_match_code_rule_impl(
    code: str,
    yaml_rule: str
) -> List[Dict[str, Any]]:
    """
    Implementation of test_match_code_rule.

    Test a code against an ast-grep YAML rule.
    This is useful to test a rule before using it in a project.

    Args:
        code: The code to test against the rule
        yaml_rule: The ast-grep YAML rule to search

    Returns:
        List of matches

    Raises:
        InvalidYAMLError: If YAML is invalid
        NoMatchesError: If no matches are found
        AstGrepError: If ast-grep command fails
    """
    logger = get_logger("search.test_match_code_rule")
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
        "test_match_code_rule_started",
        rule_id=parsed_yaml.get('id'),
        language=parsed_yaml.get('language'),
        code_length=len(code),
        yaml_length=len(yaml_rule)
    )

    try:
        result = run_ast_grep("scan", ["--inline-rules", yaml_rule, "--json", "--stdin"], input_text=code)
        matches = cast(List[Dict[str, Any]], json.loads(result.stdout.strip()))

        execution_time = time.time() - start_time
        logger.info(
            "test_match_code_rule_completed",
            execution_time_seconds=round(execution_time, 3),
            match_count=len(matches),
            status="success"
        )

        if not matches:
            raise NoMatchesError("No matches found for the given code and rule")
        return matches
    except Exception as e:
        if isinstance(e, (InvalidYAMLError, NoMatchesError)):
            raise
        execution_time = time.time() - start_time
        logger.error(
            "test_match_code_rule_failed",
            execution_time_seconds=round(execution_time, 3),
            error=str(e)[:200],
            status="failed"
        )
        sentry_sdk.capture_exception(e, extras={
            "function": "test_match_code_rule_impl",
            "rule_id": parsed_yaml.get('id') if 'parsed_yaml' in locals() else None,
            "language": parsed_yaml.get('language') if 'parsed_yaml' in locals() else None,
            "code_length": len(code),
            "execution_time_seconds": round(execution_time, 3)
        })
        raise


def _prepare_search_targets(
    project_folder: str,
    max_file_size_mb: int,
    language: str,
    logger: Any
) -> List[str]:
    """
    Prepare search targets with optional file size filtering.

    Returns:
        List of search targets (directories or filtered files)
    """
    if max_file_size_mb <= 0:
        return [project_folder]

    files_to_search, skipped_files = filter_files_by_size(
        project_folder,
        max_size_mb=max_file_size_mb,
        language=language if language else None
    )

    if files_to_search:
        logger.info(
            "file_size_filtering_applied",
            files_to_search=len(files_to_search),
            files_skipped=len(skipped_files),
            max_size_mb=max_file_size_mb
        )
        return files_to_search

    if skipped_files:
        logger.warning(
            "all_files_skipped_by_size",
            total_files=len(skipped_files),
            max_size_mb=max_file_size_mb
        )
        return []  # All files exceeded size limit

    # No files found at all, continue with directory search
    return [project_folder]


def _build_search_args(
    pattern: str,
    language: str,
    workers: int,
    search_targets: List[str]
) -> List[str]:
    """Build ast-grep command arguments."""
    args = ["--pattern", pattern]
    if language:
        args.extend(["--lang", language])
    if workers > 0:
        args.extend(["--threads", str(workers)])

    return args + ["--json=stream"] + search_targets


def _check_cache(
    cache: Any,
    stream_args: List[str],
    project_folder: str,
    max_results: int,
    output_format: str,
    logger: Any
) -> Union[str, List[Dict[str, Any]], None]:
    """
    Check cache for existing results.

    Returns:
        Cached results or None if not found
    """
    if not cache or max_results != 0:
        return None

    cached_result = cache.get("run", stream_args, project_folder)
    if cached_result is None:
        logger.info("find_code_cache_miss")
        return None

    # Apply max_results limit to cached results
    matches = cached_result[:max_results] if max_results > 0 else cached_result
    logger.info(
        "find_code_cache_hit",
        cache_size=len(cache.cache),
        cached_results=len(matches)
    )

    if output_format == "text":
        if not matches:
            return "No matches found"
        text_output = format_matches_as_text(matches)
        header = f"Found {len(matches)} matches"
        return header + ":\n\n" + text_output

    return matches


def _execute_search(
    stream_args: List[str],
    max_results: int,
    cache: Any,
    project_folder: str,
    logger: Any
) -> List[Dict[str, Any]]:
    """Execute the search and optionally cache results."""
    matches = list(stream_ast_grep_results(
        "run",
        stream_args,
        max_results=max_results,
        progress_interval=100
    ))

    # Store in cache if available
    if cache and max_results == 0:
        cache.put("run", stream_args, project_folder, matches)
        logger.info(
            "find_code_cache_stored",
            stored_results=len(matches),
            cache_size=len(cache.cache)
        )

    return matches


def _format_search_results(
    matches: List[Dict[str, Any]],
    output_format: str
) -> Union[str, List[Dict[str, Any]]]:
    """Format search results based on output format."""
    if output_format == "text":
        if not matches:
            return "No matches found"
        text_output = format_matches_as_text(matches)
        header = f"Found {len(matches)} matches"
        return header + ":\n\n" + text_output

    return matches


def find_code_impl(
    project_folder: str,
    pattern: str,
    language: str = "",
    max_results: int = 0,
    output_format: Literal["text", "json"] = "text",
    max_file_size_mb: int = 0,
    workers: int = 0
) -> Union[str, List[Dict[str, Any]]]:
    """
    Implementation of find_code.

    Find code in a project folder using a pattern.
    Uses caching when enabled and supports streaming for large results.

    Args:
        project_folder: The absolute path to the project folder
        pattern: The ast-grep pattern to search for
        language: The language of the code (auto-detected if not specified)
        max_results: Maximum results to return (0 for no limit)
        output_format: Output format ('text' or 'json')
        max_file_size_mb: Maximum file size in MB to search (0 for no limit)
        workers: Number of worker threads (0 for auto)

    Returns:
        String (text format) or list of matches (json format)

    Raises:
        AstGrepError: If ast-grep command fails
    """
    logger = get_logger("search.find_code")
    start_time = time.time()

    logger.info(
        "find_code_started",
        project_folder=project_folder,
        pattern=pattern[:100],
        language=language or "auto",
        max_results=max_results,
        output_format=output_format,
        max_file_size_mb=max_file_size_mb if max_file_size_mb > 0 else "unlimited",
        workers=workers if workers > 0 else "auto"
    )

    try:
        if output_format not in ["text", "json"]:
            raise ValueError(f"Invalid output_format: {output_format}. Must be 'text' or 'json'.")

        # Prepare search targets with file size filtering
        search_targets = _prepare_search_targets(
            project_folder, max_file_size_mb, language, logger
        )

        # Handle case where all files were skipped
        if not search_targets:
            return "No matches found (all files exceeded size limit)" if output_format == "text" else []

        # Build ast-grep arguments
        stream_args = _build_search_args(pattern, language, workers, search_targets)

        # Check cache first
        cache = get_query_cache()
        cached_result = _check_cache(
            cache, stream_args, project_folder, max_results, output_format, logger
        )
        if cached_result is not None:
            return cached_result

        # Execute search if not cached
        matches = _execute_search(
            stream_args, max_results, cache, project_folder, logger
        )

        # Format and return results
        result = _format_search_results(matches, output_format)

        execution_time = time.time() - start_time
        logger.info(
            "find_code_completed",
            execution_time_seconds=round(execution_time, 3),
            match_count=len(matches),
            status="success"
        )

        return result

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            "find_code_failed",
            execution_time_seconds=round(execution_time, 3),
            error=str(e)[:200],
            status="failed"
        )
        sentry_sdk.capture_exception(e, extras={
            "function": "find_code_impl",
            "project_folder": project_folder,
            "pattern": pattern[:100],
            "language": language,
            "execution_time_seconds": round(execution_time, 3)
        })
        raise


def _validate_yaml_rule(yaml_rule: str) -> Dict[str, Any]:
    """
    Validate YAML rule structure.

    Returns:
        Parsed YAML dictionary

    Raises:
        InvalidYAMLError: If YAML is invalid
    """
    try:
        parsed_yaml = yaml.safe_load(yaml_rule)
        if not isinstance(parsed_yaml, dict):
            raise InvalidYAMLError("YAML must be a dictionary", yaml_rule)

        required_fields = ['id', 'language', 'rule']
        for field in required_fields:
            if field not in parsed_yaml:
                raise InvalidYAMLError(f"Missing required field '{field}'", yaml_rule)

        return parsed_yaml
    except yaml.YAMLError as e:
        raise InvalidYAMLError(f"YAML parsing failed: {e}", yaml_rule) from e


def _execute_rule_search(
    project_folder: str,
    yaml_rule: str,
    max_results: int,
    output_format: str,
    cache: Any,
    logger: Any
) -> Union[str, List[Dict[str, Any]]]:
    """Execute search with YAML rule."""
    json_arg = ["--json"] if output_format == "json" else []

    if max_results > 0:
        # Use streaming for limited results
        matches = []
        for match in stream_ast_grep_results(
            "scan",
            ["--inline-rules", yaml_rule, *json_arg, project_folder],
            max_results=max_results
        ):
            matches.append(match)

        if output_format == "text":
            return format_matches_as_text(matches)
        return matches

    # Use non-streaming for all results
    cmd_result = run_ast_grep(
        "scan",
        ["--inline-rules", yaml_rule, *json_arg, project_folder]
    )

    if output_format == "json":
        return json.loads(cmd_result.stdout.strip()) if cmd_result.stdout.strip() else []

    return cmd_result.stdout.strip()


def find_code_by_rule_impl(
    project_folder: str,
    yaml_rule: str,
    max_results: int = 0,
    output_format: Literal["text", "json"] = "text"
) -> Union[str, List[Dict[str, Any]]]:
    """
    Implementation of find_code_by_rule (includes scan_project functionality).

    Find code in a project folder using a YAML rule.
    This combines the functionality of find_code_by_rule and scan_project.

    Args:
        project_folder: The absolute path to the project folder
        yaml_rule: The ast-grep YAML rule to search
        max_results: Maximum results to return (0 for no limit)
        output_format: Output format ('text' or 'json')

    Returns:
        String (text format) or list of matches (json format)

    Raises:
        InvalidYAMLError: If YAML is invalid
        AstGrepError: If ast-grep command fails
    """
    logger = get_logger("search.find_code_by_rule")
    start_time = time.time()

    # Validate YAML before passing to ast-grep
    parsed_yaml = _validate_yaml_rule(yaml_rule)

    logger.info(
        "find_code_by_rule_started",
        project_folder=project_folder,
        rule_id=parsed_yaml.get('id'),
        language=parsed_yaml.get('language'),
        max_results=max_results,
        output_format=output_format
    )

    try:
        # Check cache first (only for non-streaming cases)
        cache = get_query_cache()
        cache_key_parts = ["scan", yaml_rule, output_format, project_folder]

        if CACHE_ENABLED and cache and max_results == 0:
            cached_result = cache.get("scan", cache_key_parts, project_folder)
            if cached_result is not None:
                logger.info("find_code_by_rule_cache_hit", rule_id=parsed_yaml.get('id'))
                return cached_result

        # Execute the search
        result = _execute_rule_search(
            project_folder, yaml_rule, max_results, output_format, cache, logger
        )

        # Cache the result if applicable
        if CACHE_ENABLED and cache and max_results == 0 and isinstance(result, list):
            cache.put("scan", cache_key_parts, project_folder, result)

        execution_time = time.time() - start_time
        match_count = len(result) if isinstance(result, list) else result.count('\n')

        logger.info(
            "find_code_by_rule_completed",
            execution_time_seconds=round(execution_time, 3),
            match_count=match_count,
            status="success"
        )

        return result

    except Exception as e:
        if isinstance(e, InvalidYAMLError):
            raise
        execution_time = time.time() - start_time
        logger.error(
            "find_code_by_rule_failed",
            execution_time_seconds=round(execution_time, 3),
            error=str(e)[:200],
            status="failed"
        )
        sentry_sdk.capture_exception(e, extras={
            "function": "find_code_by_rule_impl",
            "project_folder": project_folder,
            "rule_id": parsed_yaml.get('id'),
            "language": parsed_yaml.get('language'),
            "execution_time_seconds": round(execution_time, 3)
        })
        raise