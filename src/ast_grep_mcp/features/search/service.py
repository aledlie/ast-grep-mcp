"""Search feature service - implements the core search functionality."""

import json
import re
import time
from typing import Any, Dict, List, Literal, Optional, Union, cast

import sentry_sdk
import yaml

from ast_grep_mcp.constants import CodeAnalysisDefaults, DisplayDefaults, FormattingDefaults
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
from ast_grep_mcp.models.pattern_debug import (
    AstComparison,
    IssueCategory,
    IssueSeverity,
    MatchAttempt,
    MetavariableInfo,
    PatternDebugResult,
    PatternIssue,
)
from ast_grep_mcp.models.pattern_develop import (
    CodeAnalysis,
    PatternDevelopResult,
    PatternSuggestion,
    RefinementStep,
    SuggestionType,
)
from ast_grep_mcp.utils.formatters import format_matches_as_text


def dump_syntax_tree_impl(code: str, language: str, format: DumpFormat = "cst") -> str:
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

    logger.info("dump_syntax_tree_started", language=language, format=format, code_length=len(code))

    try:
        result = run_ast_grep("run", ["--pattern", code, "--lang", language, f"--debug-query={format}"])
        output = result.stderr.strip()

        execution_time = time.time() - start_time
        logger.info(
            "dump_syntax_tree_completed",
            execution_time_seconds=round(execution_time, FormattingDefaults.ROUNDING_PRECISION),
            output_length=len(output),
            status="success",
        )

        return output
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            "dump_syntax_tree_failed",
            execution_time_seconds=round(execution_time, FormattingDefaults.ROUNDING_PRECISION),
            error=str(e)[: DisplayDefaults.ERROR_OUTPUT_PREVIEW_LENGTH],
            status="failed",
        )
        sentry_sdk.capture_exception(
            e,
            extras={
                "function": "dump_syntax_tree_impl",
                "language": language,
                "format": format,
                "code_length": len(code),
                "execution_time_seconds": round(execution_time, FormattingDefaults.ROUNDING_PRECISION),
            },
        )
        raise


def test_match_code_rule_impl(code: str, yaml_rule: str) -> List[Dict[str, Any]]:
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
        if "id" not in parsed_yaml:
            raise InvalidYAMLError("Missing required field 'id'", yaml_rule)
        if "language" not in parsed_yaml:
            raise InvalidYAMLError("Missing required field 'language'", yaml_rule)
        if "rule" not in parsed_yaml:
            raise InvalidYAMLError("Missing required field 'rule'", yaml_rule)
    except yaml.YAMLError as e:
        raise InvalidYAMLError(f"YAML parsing failed: {e}", yaml_rule) from e

    logger.info(
        "test_match_code_rule_started",
        rule_id=parsed_yaml.get("id"),
        language=parsed_yaml.get("language"),
        code_length=len(code),
        yaml_length=len(yaml_rule),
    )

    try:
        result = run_ast_grep("scan", ["--inline-rules", yaml_rule, "--json", "--stdin"], input_text=code)
        matches = cast(List[Dict[str, Any]], json.loads(result.stdout.strip()))

        execution_time = time.time() - start_time
        logger.info(
            "test_match_code_rule_completed",
            execution_time_seconds=round(execution_time, FormattingDefaults.ROUNDING_PRECISION),
            match_count=len(matches),
            status="success",
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
            execution_time_seconds=round(execution_time, FormattingDefaults.ROUNDING_PRECISION),
            error=str(e)[: DisplayDefaults.ERROR_OUTPUT_PREVIEW_LENGTH],
            status="failed",
        )
        sentry_sdk.capture_exception(
            e,
            extras={
                "function": "test_match_code_rule_impl",
                "rule_id": parsed_yaml.get("id") if "parsed_yaml" in locals() else None,
                "language": parsed_yaml.get("language") if "parsed_yaml" in locals() else None,
                "code_length": len(code),
                "execution_time_seconds": round(execution_time, FormattingDefaults.ROUNDING_PRECISION),
            },
        )
        raise


def _prepare_search_targets(project_folder: str, max_file_size_mb: int, language: str, logger: Any) -> List[str]:
    """
    Prepare search targets with optional file size filtering.

    Returns:
        List of search targets (directories or filtered files)
    """
    if max_file_size_mb <= 0:
        return [project_folder]

    files_to_search, skipped_files = filter_files_by_size(
        project_folder, max_size_mb=max_file_size_mb, language=language if language else None
    )

    if files_to_search:
        logger.info(
            "file_size_filtering_applied",
            files_to_search=len(files_to_search),
            files_skipped=len(skipped_files),
            max_size_mb=max_file_size_mb,
        )
        return files_to_search

    if skipped_files:
        logger.warning("all_files_skipped_by_size", total_files=len(skipped_files), max_size_mb=max_file_size_mb)
        return []  # All files exceeded size limit

    # No files found at all, continue with directory search
    return [project_folder]


def _build_search_args(pattern: str, language: str, workers: int, search_targets: List[str]) -> List[str]:
    """Build ast-grep command arguments."""
    args = ["--pattern", pattern]
    if language:
        args.extend(["--lang", language])
    if workers > 0:
        args.extend(["--threads", str(workers)])

    return args + ["--json=stream"] + search_targets


def _format_cached_results(matches: List[Dict[str, Any]], output_format: str) -> Union[str, List[Dict[str, Any]]]:
    """
    Format cached search results based on output format.

    Returns:
        Formatted results (string for text, list for json)
    """
    if output_format == "text":
        if not matches:
            return "No matches found"
        text_output = format_matches_as_text(matches)
        header = f"Found {len(matches)} matches"
        return header + ":\n\n" + text_output

    return matches


def _check_cache(
    cache: Any, stream_args: List[str], project_folder: str, max_results: int, output_format: str, logger: Any
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
    logger.info("find_code_cache_hit", cache_size=len(cache.cache), cached_results=len(matches))

    return _format_cached_results(matches, output_format)


def _execute_search(stream_args: List[str], max_results: int, cache: Any, project_folder: str, logger: Any) -> List[Dict[str, Any]]:
    """Execute the search and optionally cache results."""
    matches = list(stream_ast_grep_results("run", stream_args, max_results=max_results, progress_interval=100))

    # Store in cache if available
    if cache and max_results == 0:
        cache.put("run", stream_args, project_folder, matches)
        logger.info("find_code_cache_stored", stored_results=len(matches), cache_size=len(cache.cache))

    return matches


def _format_search_results(matches: List[Dict[str, Any]], output_format: str) -> Union[str, List[Dict[str, Any]]]:
    """Format search results based on output format."""
    if output_format == "text":
        if not matches:
            return "No matches found"
        text_output = format_matches_as_text(matches)
        header = f"Found {len(matches)} matches"
        return header + ":\n\n" + text_output

    return matches


def _is_early_return_value(value: Any) -> bool:
    """
    Check if a value represents an early return (empty results).

    Returns:
        True if value is an empty result or string message
    """
    if isinstance(value, str):
        return True
    if isinstance(value, list) and len(value) == 0:
        return True
    if isinstance(value, list) and value and not isinstance(value[0], str):
        return True
    return False


def _validate_output_format(output_format: str) -> None:
    """
    Validate output format parameter.

    Raises:
        ValueError: If output format is invalid
    """
    if output_format not in ["text", "json"]:
        raise ValueError(f"Invalid output_format: {output_format}. Must be 'text' or 'json'.")


def _handle_empty_search_targets(search_targets: List[str], output_format: str) -> Union[str, List[Any], None]:
    """
    Handle case where all files were skipped by size filtering.

    Returns:
        Empty result message/list, or None if search_targets is not empty
    """
    if not search_targets:
        return "No matches found (all files exceeded size limit)" if output_format == "text" else []
    return None


def _validate_and_prepare_search(
    project_folder: str, pattern: str, language: str, max_file_size_mb: int, output_format: str, logger: Any
) -> Union[List[str], str, List[Any]]:
    """
    Validate inputs and prepare search targets.

    Returns:
        Search targets list, or early return value (empty result) if validation fails
    """
    # Validate output format
    _validate_output_format(output_format)

    # Prepare search targets with file size filtering
    search_targets = _prepare_search_targets(project_folder, max_file_size_mb, language, logger)

    # Handle case where all files were skipped
    empty_result = _handle_empty_search_targets(search_targets, output_format)
    if empty_result is not None:
        return empty_result

    return search_targets


def find_code_impl(
    project_folder: str,
    pattern: str,
    language: str = "",
    max_results: int = 0,
    output_format: Literal["text", "json"] = "text",
    max_file_size_mb: int = 0,
    workers: int = 0,
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
        workers=workers if workers > 0 else "auto",
    )

    try:
        # Validate and prepare search
        search_targets = _validate_and_prepare_search(project_folder, pattern, language, max_file_size_mb, output_format, logger)

        # Handle early return (empty results)
        if _is_early_return_value(search_targets):
            return search_targets  # type: ignore[return-value]

        # Build ast-grep arguments
        stream_args = _build_search_args(pattern, language, workers, search_targets)  # type: ignore[arg-type]

        # Check cache first
        cache = get_query_cache()
        cached_result = _check_cache(cache, stream_args, project_folder, max_results, output_format, logger)
        if cached_result is not None:
            return cached_result

        # Execute search if not cached
        matches = _execute_search(stream_args, max_results, cache, project_folder, logger)

        # Format and return results
        result = _format_search_results(matches, output_format)

        execution_time = time.time() - start_time
        logger.info(
            "find_code_completed",
            execution_time_seconds=round(execution_time, FormattingDefaults.ROUNDING_PRECISION),
            match_count=len(matches),
            status="success",
        )

        return result

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            "find_code_failed",
            execution_time_seconds=round(execution_time, FormattingDefaults.ROUNDING_PRECISION),
            error=str(e)[: DisplayDefaults.ERROR_OUTPUT_PREVIEW_LENGTH],
            status="failed",
        )
        sentry_sdk.capture_exception(
            e,
            extras={
                "function": "find_code_impl",
                "project_folder": project_folder,
                "pattern": pattern[:100],
                "language": language,
                "execution_time_seconds": round(execution_time, FormattingDefaults.ROUNDING_PRECISION),
            },
        )
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

        required_fields = ["id", "language", "rule"]
        for field in required_fields:
            if field not in parsed_yaml:
                raise InvalidYAMLError(f"Missing required field '{field}'", yaml_rule)

        return parsed_yaml
    except yaml.YAMLError as e:
        raise InvalidYAMLError(f"YAML parsing failed: {e}", yaml_rule) from e


# Relational rules that require stopBy for deep tree traversal
RELATIONAL_RULES = ["inside", "has", "follows", "precedes"]


def _check_relational_rule_for_stopby(rule_obj: Any, path: str = "rule") -> List[str]:
    """
    Recursively check a rule object for relational rules missing stopBy.

    Args:
        rule_obj: The rule object to check
        path: Current path in the rule tree for error messages

    Returns:
        List of warning messages
    """
    warnings: List[str] = []

    if not isinstance(rule_obj, dict):
        return warnings

    for rel_rule in RELATIONAL_RULES:
        if rel_rule in rule_obj:
            rel_content = rule_obj[rel_rule]
            if isinstance(rel_content, dict):
                if "stopBy" not in rel_content:
                    warnings.append(
                        f"⚠️  Missing 'stopBy' in '{rel_rule}' at {path}.{rel_rule}. "
                        f"Default is 'neighbor' (immediate parent only). "
                        f"Add 'stopBy: end' to search the entire tree."
                    )
                # Recursively check nested rules
                warnings.extend(_check_relational_rule_for_stopby(rel_content, f"{path}.{rel_rule}"))

    # Check composite rules (all, any, not)
    for composite in ["all", "any"]:
        if composite in rule_obj and isinstance(rule_obj[composite], list):
            for i, sub_rule in enumerate(rule_obj[composite]):
                warnings.extend(_check_relational_rule_for_stopby(sub_rule, f"{path}.{composite}[{i}]"))

    if "not" in rule_obj and isinstance(rule_obj["not"], dict):
        warnings.extend(_check_relational_rule_for_stopby(rule_obj["not"], f"{path}.not"))

    return warnings


def _check_yaml_rule_for_common_mistakes(parsed_yaml: Dict[str, Any]) -> List[str]:
    """
    Check a parsed YAML rule for common mistakes.

    Args:
        parsed_yaml: The parsed YAML rule dictionary

    Returns:
        List of warning messages
    """
    warnings: List[str] = []

    rule = parsed_yaml.get("rule", {})
    if isinstance(rule, dict):
        warnings.extend(_check_relational_rule_for_stopby(rule))

    # Check for lowercase metavariables in pattern
    pattern = rule.get("pattern", "") if isinstance(rule, dict) else ""
    if isinstance(pattern, str) and re.search(r"\$[a-z]", pattern):
        warnings.append("⚠️  Pattern may contain lowercase metavariable (e.g., $name). Use UPPERCASE: $NAME, $ARGS, etc.")

    return warnings


def _execute_rule_search(
    project_folder: str, yaml_rule: str, max_results: int, output_format: str, cache: Any, logger: Any
) -> Union[str, List[Dict[str, Any]]]:
    """Execute search with YAML rule."""
    json_arg = ["--json"] if output_format == "json" else []

    if max_results > 0:
        # Use streaming for limited results
        matches = []
        for match in stream_ast_grep_results("scan", ["--inline-rules", yaml_rule, *json_arg, project_folder], max_results=max_results):
            matches.append(match)

        if output_format == "text":
            return format_matches_as_text(matches)
        return matches

    # Use non-streaming for all results
    cmd_result = run_ast_grep("scan", ["--inline-rules", yaml_rule, *json_arg, project_folder])

    if output_format == "json":
        return json.loads(cmd_result.stdout.strip()) if cmd_result.stdout.strip() else []

    return cmd_result.stdout.strip()


def _prepend_warnings_to_result(
    result: Union[str, List[Dict[str, Any]]], warnings: List[str], output_format: str
) -> Union[str, List[Dict[str, Any]], Dict[str, Any]]:
    """
    Prepend warnings to the search result.

    Args:
        result: The search result
        warnings: List of warning messages
        output_format: Output format ('text' or 'json')

    Returns:
        Result with warnings included
    """
    if not warnings:
        return result

    if output_format == "text":
        warning_block = "\n".join(warnings) + "\n\n"
        return warning_block + (result if isinstance(result, str) else "")

    # For JSON, add warnings as metadata
    if isinstance(result, list):
        return {
            "warnings": warnings,
            "matches": result,
        }
    return result


def _check_rule_cache(
    cache: Any, cache_key_parts: List[str], project_folder: str, max_results: int, logger: Any, rule_id: Optional[str]
) -> Optional[Any]:
    """Check cache for existing rule search results."""
    if not CACHE_ENABLED or not cache or max_results != 0:
        return None

    cached_result = cache.get("scan", cache_key_parts, project_folder)
    if cached_result is not None:
        logger.info("find_code_by_rule_cache_hit", rule_id=rule_id)
    return cached_result


def _store_rule_result_in_cache(cache: Any, cache_key_parts: List[str], project_folder: str, result: Any, max_results: int) -> None:
    """Store rule search result in cache if applicable."""
    if CACHE_ENABLED and cache and max_results == 0 and isinstance(result, list):
        cache.put("scan", cache_key_parts, project_folder, result)


def _log_rule_warnings(warnings: List[str], parsed_yaml: Dict[str, Any], logger: Any) -> None:
    """Log warnings about common mistakes in the YAML rule."""
    if warnings:
        logger.warning(
            "yaml_rule_warnings",
            rule_id=parsed_yaml.get("id"),
            warning_count=len(warnings),
            warnings=warnings,
        )


def find_code_by_rule_impl(
    project_folder: str, yaml_rule: str, max_results: int = 0, output_format: Literal["text", "json"] = "text"
) -> Union[str, List[Dict[str, Any]], Dict[str, Any]]:
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
        If warnings are present in JSON format, returns dict with 'warnings' and 'matches' keys

    Raises:
        InvalidYAMLError: If YAML is invalid
        AstGrepError: If ast-grep command fails
    """
    logger = get_logger("search.find_code_by_rule")
    start_time = time.time()

    # Validate YAML and check for common mistakes
    parsed_yaml = _validate_yaml_rule(yaml_rule)
    warnings = _check_yaml_rule_for_common_mistakes(parsed_yaml)
    _log_rule_warnings(warnings, parsed_yaml, logger)

    logger.info(
        "find_code_by_rule_started",
        project_folder=project_folder,
        rule_id=parsed_yaml.get("id"),
        language=parsed_yaml.get("language"),
        max_results=max_results,
        output_format=output_format,
    )

    try:
        cache = get_query_cache()
        cache_key_parts = ["scan", yaml_rule, output_format, project_folder]

        # Check cache first
        cached_result = _check_rule_cache(cache, cache_key_parts, project_folder, max_results, logger, parsed_yaml.get("id"))
        if cached_result is not None:
            return _prepend_warnings_to_result(cached_result, warnings, output_format)

        # Execute the search
        result = _execute_rule_search(project_folder, yaml_rule, max_results, output_format, cache, logger)

        # Cache the result
        _store_rule_result_in_cache(cache, cache_key_parts, project_folder, result, max_results)

        execution_time = time.time() - start_time
        match_count = len(result) if isinstance(result, list) else result.count("\n")

        logger.info(
            "find_code_by_rule_completed",
            execution_time_seconds=round(execution_time, FormattingDefaults.ROUNDING_PRECISION),
            match_count=match_count,
            status="success",
        )

        return _prepend_warnings_to_result(result, warnings, output_format)

    except Exception as e:
        if isinstance(e, InvalidYAMLError):
            raise
        execution_time = time.time() - start_time
        logger.error(
            "find_code_by_rule_failed",
            execution_time_seconds=round(execution_time, FormattingDefaults.ROUNDING_PRECISION),
            error=str(e)[: DisplayDefaults.ERROR_OUTPUT_PREVIEW_LENGTH],
            status="failed",
        )
        sentry_sdk.capture_exception(
            e,
            extras={
                "function": "find_code_by_rule_impl",
                "project_folder": project_folder,
                "rule_id": parsed_yaml.get("id"),
                "language": parsed_yaml.get("language"),
                "execution_time_seconds": round(execution_time, FormattingDefaults.ROUNDING_PRECISION),
            },
        )
        raise


# =============================================================================
# Rule Builder Implementation
# =============================================================================


def _build_relational_rule(pattern_or_kind: str, stop_by: str, is_kind: bool = False) -> Dict[str, Any]:
    """
    Build a relational rule object with proper stopBy configuration.

    Args:
        pattern_or_kind: The pattern string or kind identifier
        stop_by: The stopBy value ('neighbor', 'end', or custom)
        is_kind: If True, use 'kind' instead of 'pattern'

    Returns:
        Properly structured relational rule dict
    """
    rule: Dict[str, Any] = {"stopBy": stop_by}
    if is_kind:
        rule["kind"] = pattern_or_kind
    else:
        rule["pattern"] = pattern_or_kind
    return rule


def _add_relational_to_rule(
    rule_obj: Dict[str, Any],
    relational_type: str,
    value: Optional[str],
    stop_by: str,
) -> None:
    """
    Add a relational rule if the value is provided.

    Args:
        rule_obj: The rule object to modify
        relational_type: 'inside', 'has', 'follows', or 'precedes'
        value: The pattern for the relational rule (None to skip)
        stop_by: The stopBy configuration
    """
    if value:
        rule_obj[relational_type] = _build_relational_rule(value, stop_by)


def build_rule_impl(
    pattern: str,
    language: str,
    rule_id: Optional[str] = None,
    inside: Optional[str] = None,
    has: Optional[str] = None,
    follows: Optional[str] = None,
    precedes: Optional[str] = None,
    inside_kind: Optional[str] = None,
    has_kind: Optional[str] = None,
    stop_by: str = "end",
    message: Optional[str] = None,
    severity: Optional[str] = None,
    fix: Optional[str] = None,
) -> str:
    """
    Build a properly structured YAML rule from components.

    This helper ensures:
    - All required fields are present (id, language, rule)
    - stopBy is correctly set on all relational rules
    - YAML is properly formatted

    Args:
        pattern: The main pattern to match
        language: Target language (python, javascript, etc.)
        rule_id: Unique rule identifier (auto-generated if not provided)
        inside: Pattern that must contain the match
        has: Pattern that must be inside the match
        follows: Pattern that must precede the match
        precedes: Pattern that must follow the match
        inside_kind: Node kind that must contain the match (alternative to inside pattern)
        has_kind: Node kind that must be inside the match (alternative to has pattern)
        stop_by: stopBy value for relational rules ('neighbor', 'end', or custom)
        message: Human-readable description of what the rule finds
        severity: Rule severity (error, warning, info, hint)
        fix: Auto-fix replacement template

    Returns:
        YAML rule string ready for use with find_code_by_rule
    """
    import hashlib

    # Generate rule ID if not provided
    if not rule_id:
        hash_input = f"{pattern}{language}{inside}{has}"
        rule_id = f"rule-{hashlib.md5(hash_input.encode()).hexdigest()[:8]}"

    # Build the rule object
    rule_obj: Dict[str, Any] = {"pattern": pattern}

    # Add relational rules with patterns
    _add_relational_to_rule(rule_obj, "inside", inside, stop_by)
    _add_relational_to_rule(rule_obj, "has", has, stop_by)
    _add_relational_to_rule(rule_obj, "follows", follows, stop_by)
    _add_relational_to_rule(rule_obj, "precedes", precedes, stop_by)

    # Add kind-based relational rules (override pattern if both provided)
    if inside_kind:
        rule_obj["inside"] = _build_relational_rule(inside_kind, stop_by, is_kind=True)
    if has_kind:
        rule_obj["has"] = _build_relational_rule(has_kind, stop_by, is_kind=True)

    # Build the full YAML structure
    yaml_obj: Dict[str, Any] = {
        "id": rule_id,
        "language": language,
        "rule": rule_obj,
    }

    # Add optional fields
    if message:
        yaml_obj["message"] = message
    if severity:
        yaml_obj["severity"] = severity
    if fix is not None:  # Allow empty string for deletion fix
        yaml_obj["fix"] = fix

    # Convert to YAML string
    return yaml.dump(yaml_obj, default_flow_style=False, sort_keys=False, allow_unicode=True)


# =============================================================================
# Pattern Debugging Implementation
# =============================================================================

# Regex patterns for metavariable detection
METAVAR_SINGLE = re.compile(r"\$([A-Z][A-Z0-9_]*)")  # $NAME, $VAR1
METAVAR_MULTI = re.compile(r"\$\$\$([A-Z][A-Z0-9_]*)?")  # $$$, $$$ARGS
METAVAR_NON_CAPTURING = re.compile(r"\$_([A-Z][A-Z0-9_]*)?")  # $_, $_NAME
METAVAR_UNNAMED = re.compile(r"\$\$([A-Z][A-Z0-9_]*)")  # $$VAR

# Invalid metavariable patterns with their error messages
INVALID_METAVAR_PATTERNS = [
    (re.compile(r"\$([a-z][a-zA-Z0-9_]*)"), "lowercase", "Metavariable must use UPPERCASE"),
    (re.compile(r"\$(\d[A-Z0-9_]*)"), "digit_start", "Metavariable cannot start with digit"),
    (re.compile(r"\$([A-Z][A-Z0-9]*-[A-Z0-9_-]*)"), "hyphen", "Metavariable cannot contain hyphens"),
]


def _extract_invalid_metavariables(pattern: str) -> List[MetavariableInfo]:
    """Extract invalid metavariables from pattern.

    Args:
        pattern: The ast-grep pattern

    Returns:
        List of invalid MetavariableInfo objects
    """
    metavars: List[MetavariableInfo] = []

    for regex, error_type, base_message in INVALID_METAVAR_PATTERNS:
        for match in regex.finditer(pattern):
            name = f"${match.group(1)}"
            if error_type == "lowercase":
                issue = f"{base_message}: '{name}' should be '${match.group(1).upper()}'"
            else:
                issue = f"{base_message}: '{name}'"
            metavars.append(
                MetavariableInfo(
                    name=name,
                    type="invalid",
                    valid=False,
                    occurrences=1,
                    issue=issue,
                )
            )

    return metavars


def _add_metavar_if_new(
    display_name: str,
    mv_type: str,
    seen: Dict[str, int],
    metavars: List[MetavariableInfo],
) -> None:
    """Add metavariable if not already seen, otherwise increment count.

    Args:
        display_name: The metavariable name
        mv_type: Type of metavariable
        seen: Dictionary tracking seen metavariables
        metavars: List to append new metavariables to
    """
    if display_name in seen:
        seen[display_name] += 1
    else:
        seen[display_name] = 1
        metavars.append(
            MetavariableInfo(
                name=display_name,
                type=mv_type,
                valid=True,
                occurrences=1,
            )
        )


def _extract_multi_metavariables(pattern: str, seen: Dict[str, int], metavars: List[MetavariableInfo]) -> None:
    """Extract $$$ multi-node metavariables."""
    for match in METAVAR_MULTI.finditer(pattern):
        name = match.group(1) or ""
        display_name = f"$$${name}" if name else "$$$"
        _add_metavar_if_new(display_name, "multi", seen, metavars)


def _extract_unnamed_metavariables(pattern: str, seen: Dict[str, int], metavars: List[MetavariableInfo]) -> None:
    """Extract $$ unnamed node metavariables."""
    for match in METAVAR_UNNAMED.finditer(pattern):
        start = match.start()
        if start > 0 and pattern[start - 1] == "$":
            continue  # Skip $$$ patterns
        name = f"$${match.group(1)}"
        _add_metavar_if_new(name, "unnamed", seen, metavars)


def _extract_non_capturing_metavariables(pattern: str, seen: Dict[str, int], metavars: List[MetavariableInfo]) -> None:
    """Extract $_ non-capturing metavariables."""
    for match in METAVAR_NON_CAPTURING.finditer(pattern):
        name_part = match.group(1) or ""
        display_name = f"$_{name_part}" if name_part else "$_"
        _add_metavar_if_new(display_name, "non_capturing", seen, metavars)


def _extract_single_metavariables(pattern: str, seen: Dict[str, int], metavars: List[MetavariableInfo]) -> None:
    """Extract $NAME single-node metavariables."""
    for match in METAVAR_SINGLE.finditer(pattern):
        start = match.start()
        # Skip if part of $$$ or $$ or $_
        if start > 0 and pattern[start - 1] == "$":
            continue
        if start + 1 < len(pattern) and pattern[start + 1] == "_":
            continue
        name = f"${match.group(1)}"
        _add_metavar_if_new(name, "single", seen, metavars)


def _extract_metavariables(pattern: str) -> List[MetavariableInfo]:
    """Extract and validate all metavariables from a pattern.

    Args:
        pattern: The ast-grep pattern

    Returns:
        List of MetavariableInfo objects
    """
    metavars: List[MetavariableInfo] = []
    seen: Dict[str, int] = {}

    # Check for invalid metavariables first
    metavars.extend(_extract_invalid_metavariables(pattern))

    # Extract valid metavariables by type
    _extract_multi_metavariables(pattern, seen, metavars)
    _extract_unnamed_metavariables(pattern, seen, metavars)
    _extract_non_capturing_metavariables(pattern, seen, metavars)
    _extract_single_metavariables(pattern, seen, metavars)

    # Update occurrence counts
    for mv in metavars:
        if mv.name in seen:
            mv.occurrences = seen[mv.name]

    return metavars


# Fragment patterns that indicate incomplete code
FRAGMENT_INDICATORS = [
    (r"^\s*\.\w+", "Pattern starts with a method call - ensure full expression context"),
    (r"^\s*:\s*\w+", "Pattern starts with a type annotation - ensure full expression context"),
    (r"^\s*=\s*", "Pattern starts with assignment operator - include left-hand side"),
]


def _check_invalid_metavar_issues(metavars: List[MetavariableInfo]) -> List[PatternIssue]:
    """Check for invalid metavariable issues.

    Args:
        metavars: Extracted metavariables

    Returns:
        List of PatternIssue objects for invalid metavariables
    """
    issues: List[PatternIssue] = []

    for mv in metavars:
        if not mv.valid and mv.issue:
            if "lowercase" in (mv.issue or "").lower():
                suggestion = f"Use uppercase letters: ${mv.name[1:].upper()}"
            else:
                suggestion = "Fix the metavariable syntax"
            issues.append(
                PatternIssue(
                    severity=IssueSeverity.ERROR,
                    category=IssueCategory.METAVARIABLE,
                    message=mv.issue,
                    suggestion=suggestion,
                    location=mv.name,
                )
            )

    return issues


def _check_single_arg_metavar_issues(pattern: str) -> List[PatternIssue]:
    """Check for single metavar in function arguments that may need $$$.

    Args:
        pattern: The ast-grep pattern

    Returns:
        List of PatternIssue objects
    """
    issues: List[PatternIssue] = []

    if "(" not in pattern or ")" not in pattern:
        return issues

    paren_content = re.findall(r"\(([^)]+)\)", pattern)
    for content in paren_content:
        content = content.strip()
        if re.match(r"^\$[A-Z][A-Z0-9_]*$", content):
            issues.append(
                PatternIssue(
                    severity=IssueSeverity.INFO,
                    category=IssueCategory.BEST_PRACTICE,
                    message=f"Single metavariable '{content}' in function arguments may not match multiple arguments",
                    suggestion=f"Use '$$$ARGS' or '$$${content[1:]}' to match zero or more arguments",
                    location=content,
                )
            )

    return issues


def _check_fragment_issues(pattern: str) -> List[PatternIssue]:
    """Check for incomplete code fragment patterns.

    Args:
        pattern: The ast-grep pattern

    Returns:
        List of PatternIssue objects
    """
    issues: List[PatternIssue] = []

    for indicator_pattern, message in FRAGMENT_INDICATORS:
        if re.match(indicator_pattern, pattern):
            issues.append(
                PatternIssue(
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.SYNTAX,
                    message=message,
                    suggestion=(
                        "Patterns must be valid, parseable code. Wrap in full expression or use YAML rule with 'context' and 'selector'"
                    ),
                )
            )

    return issues


def _check_pattern_issues(pattern: str, metavars: List[MetavariableInfo]) -> List[PatternIssue]:
    """Check for common pattern issues.

    Args:
        pattern: The ast-grep pattern
        metavars: Extracted metavariables

    Returns:
        List of PatternIssue objects
    """
    issues: List[PatternIssue] = []

    issues.extend(_check_invalid_metavar_issues(metavars))
    issues.extend(_check_single_arg_metavar_issues(pattern))
    issues.extend(_check_fragment_issues(pattern))

    return issues


def _extract_root_kind(ast_output: str) -> Optional[str]:
    """Extract the root node kind from AST output.

    Args:
        ast_output: The AST dump output from ast-grep

    Returns:
        Root node kind or None if not found
    """
    # AST output format varies, try to extract first node kind
    # Pattern output: kind: identifier, text: ...
    # CST output: (identifier) or identifier [...]

    # Try pattern format first
    kind_match = re.search(r"kind:\s*(\w+)", ast_output)
    if kind_match:
        return kind_match.group(1)

    # Try CST format - look for first node type in parentheses or brackets
    cst_match = re.search(r"\((\w+)\)|\[(\w+)\]|^(\w+)\s", ast_output)
    if cst_match:
        return cst_match.group(1) or cst_match.group(2) or cst_match.group(3)

    # Try to find first word that looks like a node kind
    first_line = ast_output.split("\n")[0] if ast_output else ""
    word_match = re.search(r"^(\w+)", first_line.strip())
    if word_match:
        return word_match.group(1)

    return None


def _compare_asts(pattern_ast: str, code_ast: str) -> AstComparison:
    """Compare pattern and code ASTs to find structural differences.

    Args:
        pattern_ast: The pattern's AST structure
        code_ast: The code's AST structure

    Returns:
        AstComparison with comparison results
    """
    pattern_root = _extract_root_kind(pattern_ast)
    code_root = _extract_root_kind(code_ast)

    kinds_match = pattern_root == code_root if pattern_root and code_root else False

    differences: List[str] = []

    if pattern_root and code_root and not kinds_match:
        differences.append(f"Root node mismatch: pattern has '{pattern_root}', code has '{code_root}'")

    # Look for structural hints in the ASTs
    if "ERROR" in pattern_ast.upper():
        differences.append("Pattern contains parse errors - pattern may not be valid code")

    if "ERROR" in code_ast.upper():
        differences.append("Code contains parse errors - code may have syntax issues")

    return AstComparison(
        pattern_root_kind=pattern_root,
        code_root_kind=code_root,
        kinds_match=kinds_match,
        pattern_structure=pattern_ast[: DisplayDefaults.AST_TRUNCATION_LENGTH]
        if len(pattern_ast) > DisplayDefaults.AST_TRUNCATION_LENGTH
        else pattern_ast,
        code_structure=code_ast[: DisplayDefaults.AST_TRUNCATION_LENGTH]
        if len(code_ast) > DisplayDefaults.AST_TRUNCATION_LENGTH
        else code_ast,
        structural_differences=differences,
    )


def _attempt_match(pattern: str, code: str, language: str) -> MatchAttempt:
    """Attempt to match the pattern against the code.

    Args:
        pattern: The ast-grep pattern
        code: The code to match against
        language: The programming language

    Returns:
        MatchAttempt with match results
    """
    logger = get_logger("search.debug_pattern")

    try:
        # Create a minimal YAML rule to test matching
        yaml_rule = f"""
id: debug-pattern-test
language: {language}
rule:
  pattern: |
    {pattern}
"""
        result = run_ast_grep("scan", ["--inline-rules", yaml_rule, "--json", "--stdin"], input_text=code)
        matches = json.loads(result.stdout.strip()) if result.stdout.strip() else []

        return MatchAttempt(
            matched=len(matches) > 0,
            match_count=len(matches),
            matches=matches[:5],  # Limit to first 5 matches for debugging
        )
    except Exception as e:
        logger.debug("match_attempt_failed", error=str(e))
        return MatchAttempt(
            matched=False,
            match_count=0,
            partial_matches=[f"Match attempt failed: {str(e)[:100]}"],
        )


def _add_error_suggestions(issues: List[PatternIssue], suggestions: List[str]) -> None:
    """Add error-level suggestions (Priority 1)."""
    for issue in issues:
        if issue.severity == IssueSeverity.ERROR:
            suggestions.append(f"[ERROR] {issue.suggestion}")


def _add_structural_suggestions(ast_comparison: AstComparison, suggestions: List[str]) -> None:
    """Add structural mismatch suggestions (Priority 2)."""
    has_root_mismatch = not ast_comparison.kinds_match and ast_comparison.pattern_root_kind and ast_comparison.code_root_kind
    if has_root_mismatch:
        suggestions.append(
            f"[STRUCTURE] Pattern root is '{ast_comparison.pattern_root_kind}' but code root is "
            f"'{ast_comparison.code_root_kind}'. Adjust pattern to match code structure."
        )

    for diff in ast_comparison.structural_differences:
        if "ERROR" in diff:
            suggestions.append(f"[PARSE ERROR] {diff}")


def _add_debug_suggestions(
    issues: List[PatternIssue],
    ast_comparison: AstComparison,
    match_attempt: MatchAttempt,
    suggestions: List[str],
) -> None:
    """Add debugging suggestions when pattern doesn't match (Priority 3)."""
    has_errors = any(i.severity == IssueSeverity.ERROR for i in issues)

    if match_attempt.matched or has_errors:
        return

    suggestions.append(
        "[DEBUG] Pattern is valid but doesn't match. Use 'dump_syntax_tree' with format='cst' "
        "on both pattern and code to compare their AST structures."
    )

    if ast_comparison.pattern_root_kind != ast_comparison.code_root_kind:
        suggestions.append(f"[TIP] Try using 'kind: {ast_comparison.code_root_kind}' in a YAML rule instead of pattern matching.")


def _add_warning_suggestions(issues: List[PatternIssue], suggestions: List[str]) -> None:
    """Add warning-level suggestions (Priority 4)."""
    for issue in issues:
        if issue.severity == IssueSeverity.WARNING:
            suggestions.append(f"[WARNING] {issue.suggestion}")


def _add_info_suggestions(issues: List[PatternIssue], suggestions: List[str]) -> None:
    """Add info-level suggestions (Priority 5)."""
    for issue in issues:
        if issue.severity == IssueSeverity.INFO:
            suggestions.append(f"[TIP] {issue.suggestion}")


def _add_default_suggestions(match_attempt: MatchAttempt, suggestions: List[str]) -> None:
    """Add default guidance if no specific suggestions were generated."""
    if suggestions:
        return

    if match_attempt.matched:
        suggestions.append("[SUCCESS] Pattern matches the code. No issues found.")
    else:
        suggestions.append(
            "[HELP] No obvious issues found. Consider:\n"
            "  1. Check if pattern is valid syntax for the language\n"
            "  2. Use dump_syntax_tree to compare AST structures\n"
            "  3. Try a simpler pattern and gradually add complexity\n"
            "  4. Use YAML rule with 'context' and 'selector' for sub-expressions"
        )


def _generate_suggestions(
    pattern: str,
    code: str,
    language: str,
    issues: List[PatternIssue],
    ast_comparison: AstComparison,
    match_attempt: MatchAttempt,
) -> List[str]:
    """Generate prioritized suggestions for fixing pattern issues.

    Args:
        pattern: The ast-grep pattern (unused but kept for API consistency)
        code: The code to match against (unused but kept for API consistency)
        language: The programming language (unused but kept for API consistency)
        issues: List of issues found
        ast_comparison: AST comparison results
        match_attempt: Match attempt results

    Returns:
        Prioritized list of suggestions
    """
    suggestions: List[str] = []

    _add_error_suggestions(issues, suggestions)
    _add_structural_suggestions(ast_comparison, suggestions)
    _add_debug_suggestions(issues, ast_comparison, match_attempt, suggestions)
    _add_warning_suggestions(issues, suggestions)
    _add_info_suggestions(issues, suggestions)
    _add_default_suggestions(match_attempt, suggestions)

    return suggestions


def debug_pattern_impl(
    pattern: str,
    code: str,
    language: str,
) -> PatternDebugResult:
    """Debug why a pattern doesn't match code.

    This tool provides comprehensive analysis of pattern matching issues:
    - Validates metavariable syntax
    - Compares pattern and code AST structures
    - Identifies common mistakes and provides suggestions
    - Attempts to match and reports results

    Args:
        pattern: The ast-grep pattern to debug
        code: The code to match against
        language: The programming language

    Returns:
        PatternDebugResult with detailed debugging information
    """
    logger = get_logger("search.debug_pattern")
    start_time = time.time()

    logger.info(
        "debug_pattern_started",
        language=language,
        pattern_length=len(pattern),
        code_length=len(code),
    )

    try:
        # Extract and validate metavariables
        metavars = _extract_metavariables(pattern)

        # Check for pattern issues
        issues = _check_pattern_issues(pattern, metavars)

        # Get AST dumps for comparison
        pattern_valid = True
        pattern_ast = ""
        code_ast = ""

        try:
            pattern_ast = dump_syntax_tree_impl(pattern, language, "pattern")
        except Exception as e:
            pattern_valid = False
            pattern_ast = f"Error parsing pattern: {str(e)[: DisplayDefaults.ERROR_OUTPUT_PREVIEW_LENGTH]}"
            issues.append(
                PatternIssue(
                    severity=IssueSeverity.ERROR,
                    category=IssueCategory.SYNTAX,
                    message=f"Pattern failed to parse: {str(e)[:100]}",
                    suggestion="Ensure pattern is valid, parseable code for the target language",
                )
            )

        try:
            code_ast = dump_syntax_tree_impl(code, language, "cst")
        except Exception as e:
            code_ast = f"Error parsing code: {str(e)[: DisplayDefaults.ERROR_OUTPUT_PREVIEW_LENGTH]}"
            issues.append(
                PatternIssue(
                    severity=IssueSeverity.WARNING,
                    category=IssueCategory.SYNTAX,
                    message=f"Code failed to parse: {str(e)[:100]}",
                    suggestion="Check that the code is valid syntax",
                )
            )

        # Compare ASTs
        ast_comparison = _compare_asts(pattern_ast, code_ast)

        # Attempt to match
        match_attempt = _attempt_match(pattern, code, language)

        # Generate prioritized suggestions
        suggestions = _generate_suggestions(pattern, code, language, issues, ast_comparison, match_attempt)

        execution_time = time.time() - start_time

        result = PatternDebugResult(
            pattern=pattern,
            code=code,
            language=language,
            pattern_valid=pattern_valid,
            pattern_ast=pattern_ast,
            code_ast=code_ast,
            ast_comparison=ast_comparison,
            metavariables=metavars,
            issues=issues,
            suggestions=suggestions,
            match_attempt=match_attempt,
            execution_time_ms=int(execution_time * 1000),
        )

        logger.info(
            "debug_pattern_completed",
            execution_time_seconds=round(execution_time, FormattingDefaults.ROUNDING_PRECISION),
            pattern_valid=pattern_valid,
            issues_found=len(issues),
            matched=match_attempt.matched,
            status="success",
        )

        return result

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            "debug_pattern_failed",
            execution_time_seconds=round(execution_time, FormattingDefaults.ROUNDING_PRECISION),
            error=str(e)[: DisplayDefaults.ERROR_OUTPUT_PREVIEW_LENGTH],
            status="failed",
        )
        sentry_sdk.capture_exception(
            e,
            extras={
                "function": "debug_pattern_impl",
                "language": language,
                "pattern_length": len(pattern),
                "code_length": len(code),
                "execution_time_seconds": round(execution_time, FormattingDefaults.ROUNDING_PRECISION),
            },
        )
        raise


# =============================================================================
# Pattern Development Implementation
# =============================================================================

# Common identifier patterns by language
IDENTIFIER_PATTERNS: Dict[str, re.Pattern[str]] = {
    "javascript": re.compile(r"\b([a-zA-Z_$][a-zA-Z0-9_$]*)\b"),
    "typescript": re.compile(r"\b([a-zA-Z_$][a-zA-Z0-9_$]*)\b"),
    "python": re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b"),
    "go": re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b"),
    "rust": re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b"),
    "java": re.compile(r"\b([a-zA-Z_$][a-zA-Z0-9_$]*)\b"),
    "ruby": re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b"),
    "c": re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b"),
    "cpp": re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b"),
}

# Keywords by language (subset of most common)
LANGUAGE_KEYWORDS: Dict[str, set[str]] = {
    "javascript": {
        "function",
        "const",
        "let",
        "var",
        "return",
        "if",
        "else",
        "for",
        "while",
        "class",
        "async",
        "await",
        "import",
        "export",
        "from",
        "new",
        "this",
        "true",
        "false",
        "null",
        "undefined",
    },
    "typescript": {
        "function",
        "const",
        "let",
        "var",
        "return",
        "if",
        "else",
        "for",
        "while",
        "class",
        "async",
        "await",
        "import",
        "export",
        "from",
        "new",
        "this",
        "true",
        "false",
        "null",
        "undefined",
        "interface",
        "type",
        "enum",
    },
    "python": {
        "def",
        "class",
        "return",
        "if",
        "elif",
        "else",
        "for",
        "while",
        "import",
        "from",
        "as",
        "try",
        "except",
        "finally",
        "with",
        "async",
        "await",
        "True",
        "False",
        "None",
        "and",
        "or",
        "not",
        "in",
        "is",
        "lambda",
    },
    "go": {
        "func",
        "package",
        "import",
        "return",
        "if",
        "else",
        "for",
        "range",
        "switch",
        "case",
        "type",
        "struct",
        "interface",
        "var",
        "const",
        "go",
        "defer",
        "chan",
        "select",
        "true",
        "false",
        "nil",
    },
    "rust": {
        "fn",
        "let",
        "mut",
        "const",
        "return",
        "if",
        "else",
        "for",
        "while",
        "loop",
        "match",
        "struct",
        "enum",
        "impl",
        "trait",
        "use",
        "mod",
        "pub",
        "async",
        "await",
        "true",
        "false",
        "self",
        "Self",
    },
    "java": {
        "public",
        "private",
        "protected",
        "class",
        "interface",
        "void",
        "int",
        "boolean",
        "return",
        "if",
        "else",
        "for",
        "while",
        "new",
        "this",
        "static",
        "final",
        "import",
        "package",
        "try",
        "catch",
        "throw",
        "true",
        "false",
        "null",
    },
    "ruby": {
        "def",
        "end",
        "class",
        "module",
        "return",
        "if",
        "elsif",
        "else",
        "unless",
        "while",
        "for",
        "do",
        "begin",
        "rescue",
        "require",
        "include",
        "true",
        "false",
        "nil",
        "self",
    },
    "c": {
        "void",
        "int",
        "char",
        "float",
        "double",
        "return",
        "if",
        "else",
        "for",
        "while",
        "switch",
        "case",
        "struct",
        "typedef",
        "const",
        "static",
        "sizeof",
        "NULL",
    },
    "cpp": {
        "void",
        "int",
        "char",
        "float",
        "double",
        "return",
        "if",
        "else",
        "for",
        "while",
        "switch",
        "case",
        "class",
        "struct",
        "public",
        "private",
        "protected",
        "const",
        "static",
        "virtual",
        "override",
        "nullptr",
        "new",
        "delete",
        "template",
        "auto",
    },
}

# Literal patterns for string and number extraction
STRING_LITERAL_PATTERN = re.compile(r'(?:"[^"]*"|\'[^\']*\'|`[^`]*`)')
NUMBER_LITERAL_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\b")


def _get_identifier_pattern(language: str) -> re.Pattern[str]:
    """Get identifier pattern for language, with fallback."""
    return IDENTIFIER_PATTERNS.get(language, IDENTIFIER_PATTERNS["javascript"])


def _get_keywords(language: str) -> set[str]:
    """Get keywords for language, with fallback."""
    return LANGUAGE_KEYWORDS.get(language, set())


def _extract_identifiers(code: str, language: str) -> List[str]:
    """Extract unique identifiers from code, excluding keywords."""
    pattern = _get_identifier_pattern(language)
    keywords = _get_keywords(language)
    matches = pattern.findall(code)
    # Filter out keywords and deduplicate while preserving order
    seen: set[str] = set()
    result: List[str] = []
    for m in matches:
        if m not in keywords and m not in seen:
            seen.add(m)
            result.append(m)
    return result


def _extract_literals(code: str) -> List[str]:
    """Extract string and number literals from code."""
    strings = STRING_LITERAL_PATTERN.findall(code)
    numbers = NUMBER_LITERAL_PATTERN.findall(code)
    return strings + numbers


def _count_ast_depth(ast_output: str) -> int:
    """Estimate AST depth from output indentation."""
    max_indent = 0
    for line in ast_output.split("\n"):
        stripped = line.lstrip()
        if stripped:
            indent = len(line) - len(stripped)
            max_indent = max(max_indent, indent)
    return max_indent // 2  # Rough estimate


def _determine_complexity(ast_output: str, code: str) -> str:
    """Determine code complexity from AST structure."""
    depth = _count_ast_depth(ast_output)
    lines = len(code.strip().split("\n"))

    if depth <= CodeAnalysisDefaults.SIMPLE_CODE_DEPTH_THRESHOLD and lines <= CodeAnalysisDefaults.SIMPLE_CODE_LINES_THRESHOLD:
        return "simple"
    elif depth <= CodeAnalysisDefaults.MEDIUM_CODE_DEPTH_THRESHOLD and lines <= CodeAnalysisDefaults.MEDIUM_CODE_LINES_THRESHOLD:
        return "medium"
    else:
        return "complex"


def _extract_child_kinds(ast_output: str) -> List[str]:
    """Extract child node kinds from AST output."""
    # Look for kind: patterns in the AST output
    kinds = re.findall(r"kind:\s*(\w+)", ast_output)
    # Deduplicate while preserving order
    seen: set[str] = set()
    result: List[str] = []
    for k in kinds:
        if k not in seen:
            seen.add(k)
            result.append(k)
    return result[: DisplayDefaults.MAX_CHILD_KINDS]  # Limit to first 10


def _analyze_code(code: str, language: str, ast_output: str) -> CodeAnalysis:
    """Analyze code structure for pattern development."""
    root_kind = _extract_root_kind(ast_output) or "unknown"
    child_kinds = _extract_child_kinds(ast_output)
    identifiers = _extract_identifiers(code, language)
    literals = _extract_literals(code)
    keywords_found = [k for k in _get_keywords(language) if k in code.split()]
    complexity = _determine_complexity(ast_output, code)

    # Create simplified AST preview
    ast_lines = ast_output.split("\n")[: DisplayDefaults.AST_PREVIEW_MAX_LINES]
    ast_preview = "\n".join(ast_lines)
    if len(ast_output.split("\n")) > DisplayDefaults.AST_PREVIEW_MAX_LINES:
        ast_preview += "\n... (truncated)"

    return CodeAnalysis(
        root_kind=root_kind,
        child_kinds=child_kinds,
        identifiers=identifiers[: DisplayDefaults.MAX_IDENTIFIERS],
        literals=literals[: DisplayDefaults.MAX_LITERALS],
        keywords=keywords_found[: DisplayDefaults.MAX_IDENTIFIERS],
        complexity=complexity,
        ast_preview=ast_preview,
    )


def _generate_generalized_pattern(code: str, identifiers: List[str], literals: List[str]) -> str:
    """Generate pattern by replacing identifiers and literals with metavariables."""
    pattern = code

    # Replace literals first (before identifiers to avoid conflicts)
    for i, lit in enumerate(literals[: DisplayDefaults.MAX_PATTERN_REPLACEMENTS]):
        # Escape special regex characters in literal
        escaped = re.escape(lit)
        metavar = f"$LITERAL{i + 1}" if i > 0 else "$LITERAL"
        pattern = re.sub(escaped, metavar, pattern, count=1)

    # Replace identifiers with metavariables
    used_names: set[str] = set()
    for ident in identifiers[: DisplayDefaults.MAX_PATTERN_IDENTIFIERS]:
        if ident in used_names:
            continue
        # Choose a meaningful metavariable name
        if ident.lower() in ["name", "id", "value", "result", "data", "item", "obj"]:
            metavar = f"${ident.upper()}"
        elif len(ident) <= DisplayDefaults.SHORT_IDENTIFIER_THRESHOLD:
            metavar = f"${ident.upper()}"
        else:
            # Create abbreviation
            metavar = f"${ident[:3].upper()}"

        # Make unique if needed
        while metavar in used_names:
            metavar += "1"
        used_names.add(metavar)

        # Replace whole word only
        pattern = re.sub(rf"\b{re.escape(ident)}\b", metavar, pattern)

    return pattern


def _generate_structural_pattern(root_kind: str, language: str) -> str:
    """Generate a pattern based on node kind (for YAML rules)."""
    # This is guidance for using kind-based matching
    return f"kind: {root_kind}  # Use in YAML rule"


def _generate_pattern_suggestions(
    code: str,
    language: str,
    analysis: CodeAnalysis,
) -> List[PatternSuggestion]:
    """Generate pattern suggestions with varying generalization levels."""
    suggestions: List[PatternSuggestion] = []

    # 1. Exact pattern (the code itself)
    suggestions.append(
        PatternSuggestion(
            pattern=code.strip(),
            description="Exact match - matches this specific code only",
            type=SuggestionType.EXACT,
            confidence=0.9 if analysis.complexity == "simple" else 0.7,
            notes="Good for finding exact duplicates",
        )
    )

    # 2. Generalized pattern with metavariables
    if analysis.identifiers or analysis.literals:
        generalized = _generate_generalized_pattern(code.strip(), analysis.identifiers, analysis.literals)
        if generalized != code.strip():
            suggestions.append(
                PatternSuggestion(
                    pattern=generalized,
                    description="Generalized - matches similar code with different names/values",
                    type=SuggestionType.GENERALIZED,
                    confidence=0.8,
                    notes="Metavariables ($NAME) match any identifier. Use $$$ARGS for multiple items.",
                )
            )

    # 3. Structural pattern (kind-based)
    if analysis.root_kind and analysis.root_kind != "unknown":
        suggestions.append(
            PatternSuggestion(
                pattern=f"# For YAML rule: kind: {analysis.root_kind}",
                description=f"Structural - matches any '{analysis.root_kind}' node",
                type=SuggestionType.STRUCTURAL,
                confidence=0.6,
                notes="Use with find_code_by_rule. Combine with 'has' or 'inside' for precision.",
            )
        )

    return suggestions


def _generate_refinement_steps(
    code: str,
    language: str,
    analysis: CodeAnalysis,
    pattern_matches: bool,
) -> List[RefinementStep]:
    """Generate steps to refine the pattern."""
    steps: List[RefinementStep] = []
    priority = 1

    if pattern_matches:
        # Pattern works, suggest ways to make it more specific or general
        if analysis.complexity != "simple":
            steps.append(
                RefinementStep(
                    action="Simplify pattern",
                    pattern="Focus on the key structural element you want to match",
                    explanation="Complex patterns may miss variations. Start simple, add constraints.",
                    priority=priority,
                )
            )
            priority += 1

        steps.append(
            RefinementStep(
                action="Add constraints with YAML rule",
                pattern="Use 'inside' with stopBy: end to limit scope",
                explanation="Wrap in YAML rule to add context (e.g., only inside functions)",
                priority=priority,
            )
        )
        priority += 1

    else:
        # Pattern doesn't match, suggest fixes
        steps.append(
            RefinementStep(
                action="Check metavariable syntax",
                pattern="Ensure $NAME uses UPPERCASE, use $$$ARGS for multiple items",
                explanation="Common mistake: lowercase metavariables don't work",
                priority=priority,
            )
        )
        priority += 1

        steps.append(
            RefinementStep(
                action="Use dump_syntax_tree",
                pattern=f'dump_syntax_tree(code="{code[:50]}...", language="{language}", format="cst")',
                explanation="Compare pattern AST with code AST to find structural mismatches",
                priority=priority,
            )
        )
        priority += 1

        steps.append(
            RefinementStep(
                action="Try kind-based matching",
                pattern=f"rule:\n  kind: {analysis.root_kind}",
                explanation="Match by node type instead of exact syntax",
                priority=priority,
            )
        )
        priority += 1

    return steps


def _generate_yaml_template(pattern: str, language: str, analysis: CodeAnalysis) -> str:
    """Generate a YAML rule template with the pattern."""
    # Escape the pattern for YAML
    if "\n" in pattern:
        pattern_yaml = f"|\n    {pattern.replace(chr(10), chr(10) + '    ')}"
    else:
        pattern_yaml = pattern

    template = f"""id: custom-pattern-rule
language: {language}
message: "Found matching code"
rule:
  pattern: {pattern_yaml}"""

    # Add inside constraint suggestion for complex patterns
    if analysis.complexity != "simple":
        template += f"""
  # Optional: Add context constraint
  # inside:
  #   stopBy: end
  #   kind: {analysis.child_kinds[0] if analysis.child_kinds else "function_declaration"}"""

    return template


def _generate_next_steps(pattern_matches: bool, analysis: CodeAnalysis) -> List[str]:
    """Generate guidance for next steps."""
    steps: List[str] = []

    if pattern_matches:
        steps.append("1. Pattern matches! Use find_code() with this pattern to search your project")
        steps.append("2. Consider using build_rule() to add constraints (inside, has, follows)")
        steps.append("3. Test with test_match_code_rule() on edge cases before deploying")
    else:
        steps.append("1. Use debug_pattern() to diagnose why the pattern doesn't match")
        steps.append("2. Check if pattern is valid parseable code for the target language")
        steps.append("3. Use dump_syntax_tree() to compare pattern and code AST structures")
        steps.append("4. Try the generalized pattern suggestion with metavariables")

    steps.append("5. For complex matching, use find_code_by_rule() with the YAML template provided")
    steps.append("6. See get_ast_grep_docs(topic='workflow') for the full development workflow")

    return steps


def _test_pattern_match(pattern: str, code: str, language: str) -> tuple[bool, int]:
    """Test if pattern matches the code."""
    try:
        yaml_rule = f"""
id: develop-pattern-test
language: {language}
rule:
  pattern: |
    {pattern}
"""
        result = run_ast_grep("scan", ["--inline-rules", yaml_rule, "--json", "--stdin"], input_text=code)
        matches = json.loads(result.stdout.strip()) if result.stdout.strip() else []
        return len(matches) > 0, len(matches)
    except Exception:
        return False, 0


def develop_pattern_impl(
    code: str,
    language: str,
    goal: Optional[str] = None,
) -> PatternDevelopResult:
    """Help develop a pattern to match the given code.

    This is a higher-level workflow tool that guides users through the
    pattern development process:
    1. Analyzes the code's AST structure
    2. Suggests starting patterns with metavariables
    3. Tests if patterns match
    4. Provides refinement guidance

    Args:
        code: Sample code you want to match
        language: The programming language
        goal: Optional description of what you're trying to find (for context)

    Returns:
        PatternDevelopResult with analysis, suggestions, and next steps
    """
    logger = get_logger("search.develop_pattern")
    start_time = time.time()

    logger.info(
        "develop_pattern_started",
        language=language,
        code_length=len(code),
        has_goal=goal is not None,
    )

    try:
        # 1. Get the code's AST structure
        code_ast = dump_syntax_tree_impl(code, language, "cst")

        # 2. Analyze the code
        analysis = _analyze_code(code, language, code_ast)

        # 3. Generate pattern suggestions
        suggestions = _generate_pattern_suggestions(code, language, analysis)

        # 4. Pick the best pattern (prefer generalized if available)
        if len(suggestions) >= 2 and suggestions[1].type == SuggestionType.GENERALIZED:
            best_pattern = suggestions[1].pattern
        else:
            best_pattern = suggestions[0].pattern

        # 5. Test if the best pattern matches
        pattern_matches, match_count = _test_pattern_match(best_pattern, code, language)

        # If generalized doesn't work, try exact
        if not pattern_matches and len(suggestions) > 0:
            exact_pattern = suggestions[0].pattern
            pattern_matches, match_count = _test_pattern_match(exact_pattern, code, language)
            if pattern_matches:
                best_pattern = exact_pattern

        # 6. Generate refinement steps
        refinement_steps = _generate_refinement_steps(code, language, analysis, pattern_matches)

        # 7. Generate YAML template
        yaml_template = _generate_yaml_template(best_pattern, language, analysis)

        # 8. Generate next steps
        next_steps = _generate_next_steps(pattern_matches, analysis)

        execution_time = time.time() - start_time

        result = PatternDevelopResult(
            code=code,
            language=language,
            code_analysis=analysis,
            suggested_patterns=suggestions,
            best_pattern=best_pattern,
            pattern_matches=pattern_matches,
            match_count=match_count,
            refinement_steps=refinement_steps,
            yaml_rule_template=yaml_template,
            next_steps=next_steps,
            execution_time_ms=int(execution_time * 1000),
        )

        logger.info(
            "develop_pattern_completed",
            execution_time_seconds=round(execution_time, FormattingDefaults.ROUNDING_PRECISION),
            pattern_matches=pattern_matches,
            suggestion_count=len(suggestions),
            status="success",
        )

        return result

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            "develop_pattern_failed",
            execution_time_seconds=round(execution_time, FormattingDefaults.ROUNDING_PRECISION),
            error=str(e)[: DisplayDefaults.ERROR_OUTPUT_PREVIEW_LENGTH],
            status="failed",
        )
        sentry_sdk.capture_exception(
            e,
            extras={
                "function": "develop_pattern_impl",
                "language": language,
                "code_length": len(code),
                "execution_time_seconds": round(execution_time, FormattingDefaults.ROUNDING_PRECISION),
            },
        )
        raise
