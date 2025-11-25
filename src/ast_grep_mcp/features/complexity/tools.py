"""
Complexity analysis MCP tools.

This module provides MCP tool definitions for code complexity analysis
and Sentry integration testing.
"""

import glob
import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Literal, Set

import sentry_sdk
from pydantic import Field

from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.models.complexity import ComplexityThresholds, FunctionComplexity

from .analyzer import analyze_file_complexity
from .storage import ComplexityStorage


def analyze_complexity_tool(
    project_folder: str,
    language: str,
    include_patterns: List[str] | None = None,
    exclude_patterns: List[str] | None = None,
    cyclomatic_threshold: int = 10,
    cognitive_threshold: int = 15,
    nesting_threshold: int = 4,
    length_threshold: int = 50,
    store_results: bool = True,
    include_trends: bool = False,
    max_threads: int = 4
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

    Args:
        project_folder: The absolute path to the project folder to analyze
        language: The programming language (python, typescript, javascript, java)
        include_patterns: Glob patterns for files to include (e.g., ['src/**/*.py'])
        exclude_patterns: Glob patterns for files to exclude
        cyclomatic_threshold: Cyclomatic complexity threshold (default: 10)
        cognitive_threshold: Cognitive complexity threshold (default: 15)
        nesting_threshold: Maximum nesting depth threshold (default: 4)
        length_threshold: Function length threshold in lines (default: 50)
        store_results: Store results in database for trend tracking
        include_trends: Include historical trend data in response
        max_threads: Number of parallel threads for analysis (default: 4)

    Returns:
        Dictionary with analysis results including summary and functions exceeding thresholds

    Example usage:
        analyze_complexity_tool(project_folder="/path/to/project", language="python")
        analyze_complexity_tool(project_folder="/path/to/project", language="typescript", cyclomatic_threshold=15)
    """
    # Set defaults
    if include_patterns is None:
        include_patterns = ["**/*"]
    if exclude_patterns is None:
        exclude_patterns = ["**/node_modules/**", "**/__pycache__/**", "**/venv/**", "**/.venv/**", "**/site-packages/**"]

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


def test_sentry_integration_tool(
    test_type: Literal["error", "warning", "breadcrumb", "span"] = "breadcrumb",
    message: str = "Test message"
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

    Args:
        test_type: Type of Sentry test ('error', 'warning', 'breadcrumb', or 'span')
        message: Custom test message

    Returns:
        Information about what was sent to Sentry
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


def register_complexity_tools(mcp: Any) -> None:
    """Register complexity analysis tools with the MCP server.

    Args:
        mcp: FastMCP server instance
    """

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
        """Wrapper that calls the standalone analyze_complexity_tool function."""
        return analyze_complexity_tool(
            project_folder=project_folder,
            language=language,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            cyclomatic_threshold=cyclomatic_threshold,
            cognitive_threshold=cognitive_threshold,
            nesting_threshold=nesting_threshold,
            length_threshold=length_threshold,
            store_results=store_results,
            include_trends=include_trends,
            max_threads=max_threads
        )

    @mcp.tool()
    def test_sentry_integration(
        test_type: Literal["error", "warning", "breadcrumb", "span"] = Field(
            default="breadcrumb",
            description="Type of Sentry test: 'error' (exception), 'warning' (capture_message), 'breadcrumb', or 'span' (performance)"
        ),
        message: str = Field(default="Test message", description="Custom test message")
    ) -> Dict[str, Any]:
        """Wrapper that calls the standalone test_sentry_integration_tool function."""
        return test_sentry_integration_tool(test_type=test_type, message=message)
