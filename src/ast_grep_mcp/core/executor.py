"""Command execution and ast-grep interface for ast-grep MCP server."""

import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, Generator, List, Optional, Tuple, cast

import sentry_sdk
import yaml

from ast_grep_mcp.constants import FileConstants, StreamDefaults
from ast_grep_mcp.core.config import CONFIG_PATH
from ast_grep_mcp.core.exceptions import (
    AstGrepExecutionError,
    AstGrepNotFoundError,
)
from ast_grep_mcp.core.logging import get_logger


def get_supported_languages() -> List[str]:
    """Get all supported languages as a field description string."""
    languages = [  # https://ast-grep.github.io/reference/languages.html
        "bash",
        "c",
        "cpp",
        "csharp",
        "css",
        "elixir",
        "go",
        "haskell",
        "html",
        "java",
        "javascript",
        "json",
        "jsx",
        "kotlin",
        "lua",
        "nix",
        "php",
        "python",
        "ruby",
        "rust",
        "scala",
        "solidity",
        "swift",
        "tsx",
        "typescript",
        "yaml",
    ]

    # Check for custom languages in config file
    # https://ast-grep.github.io/advanced/custom-language.html#register-language-in-sgconfig-yml
    if CONFIG_PATH and os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                config = yaml.safe_load(f)
                if config and "customLanguages" in config:
                    custom_langs = list(config["customLanguages"].keys())
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

    logger.info("executing_command", command=sanitized_args[0], args=sanitized_args[1:], has_stdin=has_stdin)

    try:
        # On Windows, if ast-grep is installed via npm, it's a batch file
        # that requires shell=True to execute properly
        use_shell = sys.platform == "win32" and args[0] == "ast-grep"

        with sentry_sdk.start_span(op="subprocess.run", name=f"Running {args[0]}") as span:
            span.set_data("command", sanitized_args[0])
            span.set_data("has_stdin", has_stdin)

            result = subprocess.run(
                args,
                capture_output=True,
                input=input_text,
                text=True,
                check=True,  # Raises CalledProcessError if return code is non-zero
                shell=use_shell,
            )

            span.set_data("returncode", result.returncode)

        execution_time = time.time() - start_time
        logger.info(
            "command_completed", command=sanitized_args[0], execution_time_seconds=round(execution_time, 3), returncode=result.returncode
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
            stderr=stderr_msg[:200],  # Truncate stderr in logs
        )

        error = AstGrepExecutionError(command=args, returncode=e.returncode, stderr=stderr_msg)
        sentry_sdk.capture_exception(
            error,
            extras={
                "command": " ".join(args),
                "returncode": e.returncode,
                "stderr": stderr_msg[:500],
                "execution_time_seconds": round(execution_time, 3),
                "has_stdin": has_stdin,
            },
        )
        raise error from e
    except FileNotFoundError as e:
        execution_time = time.time() - start_time

        logger.error("command_not_found", command=args[0], execution_time_seconds=round(execution_time, 3))

        if args[0] == "ast-grep":
            not_found_error = AstGrepNotFoundError()
            sentry_sdk.capture_exception(not_found_error, extras={"command": " ".join(args)})
            raise not_found_error from e
        not_found_error = AstGrepNotFoundError(f"Command '{args[0]}' not found")
        sentry_sdk.capture_exception(not_found_error, extras={"command": " ".join(args)})
        raise not_found_error from e


def _get_language_extensions(language: str) -> Optional[List[str]]:
    """Get file extensions for a language.

    Args:
        language: Programming language name

    Returns:
        List of extensions or None if language not found
    """
    lang_map = {
        "python": [".py", ".pyi"],
        "javascript": [".js", ".jsx", ".mjs"],
        "typescript": [".ts", ".tsx"],
        "java": [".java"],
        "rust": [".rs"],
        "go": [".go"],
        "c": [".c", ".h"],
        "cpp": [".cpp", ".hpp", ".cc", ".cxx", ".h"],
        "ruby": [".rb"],
        "php": [".php"],
        "swift": [".swift"],
        "kotlin": [".kt", ".kts"],
    }
    return lang_map.get(language.lower())


def _should_skip_directory(dirname: str) -> bool:
    """Check if directory should be skipped.

    Args:
        dirname: Directory name

    Returns:
        True if should skip, False otherwise
    """
    if dirname.startswith("."):
        return True
    return dirname in ["node_modules", "venv", ".venv", "build", "dist"]


def _process_file(
    file: str, root: str, lang_extensions: Optional[List[str]], max_size_bytes: int, logger: Any
) -> Tuple[Optional[str], Optional[str]]:
    """Process a single file for size filtering.

    Args:
        file: File name
        root: Root directory path
        lang_extensions: Language-specific extensions
        max_size_bytes: Maximum size in bytes
        logger: Logger instance

    Returns:
        Tuple of (file_to_search, skipped_file) - only one will be non-None
    """
    # Skip hidden files
    if file.startswith("."):
        return (None, None)

    # Check language filter
    if lang_extensions and not any(file.endswith(ext) for ext in lang_extensions):
        return (None, None)

    file_path = os.path.join(root, file)

    try:
        file_size = os.path.getsize(file_path)

        if file_size > max_size_bytes:
            logger.debug(
                "file_skipped_size",
                file=file_path,
                size_mb=round(file_size / FileConstants.BYTES_PER_MB, 2),
                max_size_mb=max_size_bytes / FileConstants.BYTES_PER_MB,
            )
            return (None, file_path)

        return (file_path, None)

    except OSError as e:
        logger.debug("file_stat_error", file=file_path, error=str(e))
        return (None, None)


def filter_files_by_size(directory: str, max_size_mb: Optional[int] = None, language: Optional[str] = None) -> Tuple[List[str], List[str]]:
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

    max_size_bytes = max_size_mb * FileConstants.BYTES_PER_MB
    files_to_search: List[str] = []
    skipped_files: List[str] = []

    # Get language extensions if specified
    lang_extensions = _get_language_extensions(language) if language else None

    # Walk directory and check file sizes
    for root, dirs, files in os.walk(directory):
        # Filter directories in-place
        dirs[:] = [d for d in dirs if not _should_skip_directory(d)]

        for file in files:
            file_to_search, skipped_file = _process_file(file, root, lang_extensions, max_size_bytes, logger)

            if file_to_search:
                files_to_search.append(file_to_search)
            elif skipped_file:
                skipped_files.append(skipped_file)

    if skipped_files:
        logger.info(
            "files_filtered_by_size",
            total_files=len(files_to_search) + len(skipped_files),
            files_to_search=len(files_to_search),
            skipped_files=len(skipped_files),
            max_size_mb=max_size_mb,
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


def _prepare_stream_command(command: str, args: List[str]) -> List[str]:
    """Prepare the full ast-grep command with optional config.

    Args:
        command: ast-grep subcommand
        args: Command arguments

    Returns:
        Full command list
    """
    final_args = args.copy()
    if CONFIG_PATH:
        final_args = ["--config", CONFIG_PATH] + final_args
    return ["ast-grep", command] + final_args


def _create_stream_process(full_command: List[str]) -> subprocess.Popen[str]:
    """Create and start the subprocess for streaming.

    Args:
        full_command: Complete command list

    Returns:
        Started Popen process

    Raises:
        FileNotFoundError: If command not found
    """
    use_shell = sys.platform == "win32" and full_command[0] == "ast-grep"
    return subprocess.Popen(full_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=use_shell)


def _parse_json_line(line: str, logger: Any) -> Optional[Dict[str, Any]]:
    """Parse a line of JSON output.

    Args:
        line: Line to parse
        logger: Logger instance

    Returns:
        Parsed JSON dict or None if invalid
    """
    line = line.strip()
    if not line:
        return None

    try:
        return cast(Dict[str, Any], json.loads(line))
    except json.JSONDecodeError as e:
        logger.warning("stream_json_parse_error", line_preview=line[: FileConstants.LINE_PREVIEW_LENGTH], error=str(e))
        sentry_sdk.capture_exception(e)
        sentry_sdk.add_breadcrumb(
            message="JSON parse error in ast-grep stream",
            category="ast-grep.stream",
            level="warning",
            data={"line_preview": line[: FileConstants.LINE_PREVIEW_LENGTH]},
        )
        return None


def _should_log_progress(match_count: int, last_progress_log: int, progress_interval: int) -> bool:
    """Check if progress should be logged.

    Args:
        match_count: Current match count
        last_progress_log: Last logged count
        progress_interval: Interval for logging

    Returns:
        True if should log progress
    """
    if progress_interval <= 0:
        return False
    return match_count - last_progress_log >= progress_interval


def _terminate_process(process: subprocess.Popen[str], logger: Any, reason: str) -> None:
    """Terminate a process gracefully, then forcefully if needed.

    Args:
        process: Process to terminate
        logger: Logger instance
        reason: Reason for termination
    """
    logger.info(f"stream_{reason}")
    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _handle_stream_error(
    returncode: int, process: subprocess.Popen[str], full_command: List[str], start_time: float, match_count: int, logger: Any
) -> None:
    """Handle non-zero return codes from the process.

    Args:
        returncode: Process return code
        process: Process instance
        full_command: Command that was run
        start_time: Start time for execution
        match_count: Number of matches found
        logger: Logger instance

    Raises:
        AstGrepExecutionError: If process failed
    """
    # SIGTERM from early termination is not an error
    if returncode == 0 or returncode == StreamDefaults.SIGTERM_RETURN_CODE:
        return

    stderr_output = process.stderr.read() if process.stderr else ""
    execution_time = time.time() - start_time

    logger.error("stream_failed", returncode=returncode, stderr=stderr_output[:200], execution_time_seconds=round(execution_time, 3))

    error = AstGrepExecutionError(command=full_command, returncode=returncode, stderr=stderr_output)
    sentry_sdk.capture_exception(
        error,
        extras={
            "command": " ".join(full_command),
            "returncode": returncode,
            "stderr": stderr_output[:500],
            "execution_time_seconds": round(execution_time, 3),
            "match_count": match_count,
        },
    )
    raise error


def _cleanup_process(process: Optional[subprocess.Popen[str]]) -> None:
    """Ensure subprocess is properly cleaned up.

    Args:
        process: Process to cleanup (may be None)
    """
    if not process or process.poll() is not None:
        return

    process.terminate()
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def stream_ast_grep_results(
    command: str, args: List[str], max_results: int = 0, progress_interval: int = StreamDefaults.PROGRESS_INTERVAL
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

    # Prepare command
    full_command = _prepare_stream_command(command, args)

    logger.info("stream_started", command=command, max_results=max_results, progress_interval=progress_interval)

    process = None
    match_count = 0
    last_progress_log = 0

    try:
        # Start subprocess
        process = _create_stream_process(full_command)

        # Process output lines
        if process.stdout:
            for line in process.stdout:
                # Parse JSON from line
                match = _parse_json_line(line, logger)
                if not match:
                    continue

                match_count += 1

                # Log progress if needed
                if _should_log_progress(match_count, last_progress_log, progress_interval):
                    logger.info("stream_progress", matches_found=match_count, execution_time_seconds=round(time.time() - start_time, 3))
                    last_progress_log = match_count

                yield match

                # Check for early termination
                if max_results > 0 and match_count >= max_results:
                    logger.info("stream_early_termination", matches_found=match_count, max_results=max_results)
                    _terminate_process(process, logger, "early_termination")
                    break

        # Wait for process completion
        returncode = process.wait()

        # Handle any errors
        _handle_stream_error(returncode, process, full_command, start_time, match_count, logger)

        # Log completion
        execution_time = time.time() - start_time
        logger.info(
            "stream_completed",
            total_matches=match_count,
            execution_time_seconds=round(execution_time, 3),
            early_terminated=max_results > 0 and match_count >= max_results,
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
        _cleanup_process(process)
