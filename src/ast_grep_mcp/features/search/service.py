"""Search feature service - implements the core search functionality."""

import json
import re
import time
from typing import Any, Dict, List, Literal, Optional, Union, cast

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
from ast_grep_mcp.models.pattern_debug import (
    AstComparison,
    IssueCategory,
    IssueSeverity,
    MatchAttempt,
    MetavariableInfo,
    PatternDebugResult,
    PatternIssue,
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
            "dump_syntax_tree_completed", execution_time_seconds=round(execution_time, 3), output_length=len(output), status="success"
        )

        return output
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error("dump_syntax_tree_failed", execution_time_seconds=round(execution_time, 3), error=str(e)[:200], status="failed")
        sentry_sdk.capture_exception(
            e,
            extras={
                "function": "dump_syntax_tree_impl",
                "language": language,
                "format": format,
                "code_length": len(code),
                "execution_time_seconds": round(execution_time, 3),
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
            "test_match_code_rule_completed", execution_time_seconds=round(execution_time, 3), match_count=len(matches), status="success"
        )

        if not matches:
            raise NoMatchesError("No matches found for the given code and rule")
        return matches
    except Exception as e:
        if isinstance(e, (InvalidYAMLError, NoMatchesError)):
            raise
        execution_time = time.time() - start_time
        logger.error("test_match_code_rule_failed", execution_time_seconds=round(execution_time, 3), error=str(e)[:200], status="failed")
        sentry_sdk.capture_exception(
            e,
            extras={
                "function": "test_match_code_rule_impl",
                "rule_id": parsed_yaml.get("id") if "parsed_yaml" in locals() else None,
                "language": parsed_yaml.get("language") if "parsed_yaml" in locals() else None,
                "code_length": len(code),
                "execution_time_seconds": round(execution_time, 3),
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
        logger.info("find_code_completed", execution_time_seconds=round(execution_time, 3), match_count=len(matches), status="success")

        return result

    except Exception as e:
        execution_time = time.time() - start_time
        logger.error("find_code_failed", execution_time_seconds=round(execution_time, 3), error=str(e)[:200], status="failed")
        sentry_sdk.capture_exception(
            e,
            extras={
                "function": "find_code_impl",
                "project_folder": project_folder,
                "pattern": pattern[:100],
                "language": language,
                "execution_time_seconds": round(execution_time, 3),
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


def find_code_by_rule_impl(
    project_folder: str, yaml_rule: str, max_results: int = 0, output_format: Literal["text", "json"] = "text"
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
        rule_id=parsed_yaml.get("id"),
        language=parsed_yaml.get("language"),
        max_results=max_results,
        output_format=output_format,
    )

    try:
        # Check cache first (only for non-streaming cases)
        cache = get_query_cache()
        cache_key_parts = ["scan", yaml_rule, output_format, project_folder]

        if CACHE_ENABLED and cache and max_results == 0:
            cached_result = cache.get("scan", cache_key_parts, project_folder)
            if cached_result is not None:
                logger.info("find_code_by_rule_cache_hit", rule_id=parsed_yaml.get("id"))
                return cached_result

        # Execute the search
        result = _execute_rule_search(project_folder, yaml_rule, max_results, output_format, cache, logger)

        # Cache the result if applicable
        if CACHE_ENABLED and cache and max_results == 0 and isinstance(result, list):
            cache.put("scan", cache_key_parts, project_folder, result)

        execution_time = time.time() - start_time
        match_count = len(result) if isinstance(result, list) else result.count("\n")

        logger.info(
            "find_code_by_rule_completed", execution_time_seconds=round(execution_time, 3), match_count=match_count, status="success"
        )

        return result

    except Exception as e:
        if isinstance(e, InvalidYAMLError):
            raise
        execution_time = time.time() - start_time
        logger.error("find_code_by_rule_failed", execution_time_seconds=round(execution_time, 3), error=str(e)[:200], status="failed")
        sentry_sdk.capture_exception(
            e,
            extras={
                "function": "find_code_by_rule_impl",
                "project_folder": project_folder,
                "rule_id": parsed_yaml.get("id"),
                "language": parsed_yaml.get("language"),
                "execution_time_seconds": round(execution_time, 3),
            },
        )
        raise


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


def _extract_multi_metavariables(
    pattern: str, seen: Dict[str, int], metavars: List[MetavariableInfo]
) -> None:
    """Extract $$$ multi-node metavariables."""
    for match in METAVAR_MULTI.finditer(pattern):
        name = match.group(1) or ""
        display_name = f"$$${name}" if name else "$$$"
        _add_metavar_if_new(display_name, "multi", seen, metavars)


def _extract_unnamed_metavariables(
    pattern: str, seen: Dict[str, int], metavars: List[MetavariableInfo]
) -> None:
    """Extract $$ unnamed node metavariables."""
    for match in METAVAR_UNNAMED.finditer(pattern):
        start = match.start()
        if start > 0 and pattern[start - 1] == "$":
            continue  # Skip $$$ patterns
        name = f"$${match.group(1)}"
        _add_metavar_if_new(name, "unnamed", seen, metavars)


def _extract_non_capturing_metavariables(
    pattern: str, seen: Dict[str, int], metavars: List[MetavariableInfo]
) -> None:
    """Extract $_ non-capturing metavariables."""
    for match in METAVAR_NON_CAPTURING.finditer(pattern):
        name_part = match.group(1) or ""
        display_name = f"$_{name_part}" if name_part else "$_"
        _add_metavar_if_new(display_name, "non_capturing", seen, metavars)


def _extract_single_metavariables(
    pattern: str, seen: Dict[str, int], metavars: List[MetavariableInfo]
) -> None:
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
                        "Patterns must be valid, parseable code. "
                        "Wrap in full expression or use YAML rule with 'context' and 'selector'"
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
        pattern_structure=pattern_ast[:500] if len(pattern_ast) > 500 else pattern_ast,
        code_structure=code_ast[:500] if len(code_ast) > 500 else code_ast,
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
    has_root_mismatch = (
        not ast_comparison.kinds_match
        and ast_comparison.pattern_root_kind
        and ast_comparison.code_root_kind
    )
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
        suggestions.append(
            f"[TIP] Try using 'kind: {ast_comparison.code_root_kind}' in a YAML rule instead of pattern matching."
        )


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
            pattern_ast = f"Error parsing pattern: {str(e)[:200]}"
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
            code_ast = f"Error parsing code: {str(e)[:200]}"
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
        suggestions = _generate_suggestions(
            pattern, code, language, issues, ast_comparison, match_attempt
        )

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
            execution_time_seconds=round(execution_time, 3),
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
            execution_time_seconds=round(execution_time, 3),
            error=str(e)[:200],
            status="failed",
        )
        sentry_sdk.capture_exception(
            e,
            extras={
                "function": "debug_pattern_impl",
                "language": language,
                "pattern_length": len(pattern),
                "code_length": len(code),
                "execution_time_seconds": round(execution_time, 3),
            },
        )
        raise
