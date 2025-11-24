"""Command execution and ast-grep interface for ast-grep MCP server."""
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, Generator, List, Optional, Tuple, cast
import yaml
import sentry_sdk

from ast_grep_mcp.core.exceptions import (
    AstGrepNotFoundError,
    AstGrepExecutionError,
)
from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.core.config import CONFIG_PATH


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