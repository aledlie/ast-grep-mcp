"""
Complexity analysis MCP tools.

This module provides MCP tool definitions for code complexity analysis
and Sentry integration testing.
"""

import os
import time
from typing import Any, Dict, List, Literal

import sentry_sdk
from pydantic import Field

from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.models.complexity import ComplexityThresholds

from .complexity_analyzer import ParallelComplexityAnalyzer
from .complexity_file_finder import ComplexityFileFinder
from .complexity_statistics import ComplexityStatisticsAggregator

# Note: detect_code_smells_impl is imported inside detect_code_smells_tool()
# to avoid circular import (quality.smells imports from complexity.analyzer)


# Helper functions extracted from analyze_complexity_tool

def _validate_inputs(language: str) -> None:
    """Validate input parameters for complexity analysis.

    Args:
        language: The programming language to validate

    Raises:
        ValueError: If the language is not supported
    """
    supported_langs = ["python", "typescript", "javascript", "java"]
    if language.lower() not in supported_langs:
        raise ValueError(f"Unsupported language '{language}'. Supported: {', '.join(supported_langs)}")


def _find_files_to_analyze(
    project_folder: str,
    language: str,
    include_patterns: List[str],
    exclude_patterns: List[str],
    logger: Any
) -> tuple[List[str], ComplexityFileFinder]:
    """Find files to analyze based on patterns.

    Args:
        project_folder: The project folder to analyze
        language: The programming language
        include_patterns: Glob patterns for files to include
        exclude_patterns: Glob patterns for files to exclude
        logger: Logger instance

    Returns:
        Tuple of (files to analyze, file finder instance)
    """
    file_finder = ComplexityFileFinder()
    files_to_analyze = file_finder.find_files(
        project_folder,
        language,
        include_patterns,
        exclude_patterns
    )

    logger.info(
        "files_found",
        total_files=len(files_to_analyze),
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns
    )

    return files_to_analyze, file_finder


def _analyze_files_parallel(
    files_to_analyze: List[str],
    language: str,
    thresholds: ComplexityThresholds,
    max_threads: int
) -> tuple[List[Any], List[Any], ParallelComplexityAnalyzer]:
    """Analyze files in parallel for complexity metrics.

    Args:
        files_to_analyze: List of files to analyze
        language: The programming language
        thresholds: Complexity thresholds
        max_threads: Number of parallel threads

    Returns:
        Tuple of (all functions, exceeding functions, analyzer instance)
    """
    analyzer = ParallelComplexityAnalyzer()

    # Analyze files in parallel
    all_functions = analyzer.analyze_files(
        files_to_analyze,
        language,
        thresholds,
        max_threads
    )

    # Filter exceeding functions
    exceeding_functions = analyzer.filter_exceeding_functions(all_functions)

    return all_functions, exceeding_functions, analyzer


def _calculate_summary_statistics(
    all_functions: List[Any],
    exceeding_functions: List[Any],
    total_files: int,
    execution_time: float
) -> tuple[Dict[str, Any], ComplexityStatisticsAggregator]:
    """Calculate summary statistics from analysis results.

    Args:
        all_functions: All analyzed functions
        exceeding_functions: Functions exceeding thresholds
        total_files: Total number of files analyzed
        execution_time: Analysis execution time

    Returns:
        Tuple of (summary dictionary, statistics instance)
    """
    statistics = ComplexityStatisticsAggregator()
    summary = statistics.calculate_summary(
        all_functions,
        exceeding_functions,
        total_files,
        execution_time
    )

    return summary, statistics


def _store_and_generate_trends(
    store_results: bool,
    include_trends: bool,
    project_folder: str,
    summary: Dict[str, Any],
    all_functions: List[Any],
    statistics: ComplexityStatisticsAggregator
) -> tuple[Any, Any, Any]:
    """Store results and generate trends if requested.

    Args:
        store_results: Whether to store results
        include_trends: Whether to include trends
        project_folder: The project folder
        summary: Summary statistics
        all_functions: All analyzed functions
        statistics: Statistics aggregator instance

    Returns:
        Tuple of (run_id, stored_at, trends)
    """
    run_id = None
    stored_at = None
    trends = None

    if store_results:
        run_id, stored_at = statistics.store_results(
            project_folder,
            summary,
            all_functions
        )

    if include_trends:
        trends = statistics.get_trends(project_folder, days=30)

    return run_id, stored_at, trends


def _format_response(
    summary: Dict[str, Any],
    thresholds_dict: Dict[str, int],
    exceeding_functions: List[Any],
    run_id: Any,
    stored_at: Any,
    trends: Any,
    statistics: ComplexityStatisticsAggregator
) -> Dict[str, Any]:
    """Format the final response dictionary.

    Args:
        summary: Summary statistics
        thresholds_dict: Complexity thresholds used
        exceeding_functions: Functions exceeding thresholds
        run_id: Storage run ID
        stored_at: Storage location
        trends: Trend data
        statistics: Statistics aggregator instance

    Returns:
        Formatted response dictionary
    """
    return statistics.format_response(
        summary,
        thresholds_dict,
        exceeding_functions,
        run_id,
        stored_at,
        trends
    )


def _handle_no_files_found(language: str, execution_time: float) -> Dict[str, Any]:
    """Handle the case when no files are found to analyze.

    Args:
        language: The programming language
        execution_time: Time taken for the analysis attempt

    Returns:
        Response dictionary for no files found case
    """
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


def _create_thresholds_dict(
    cyclomatic_threshold: int,
    cognitive_threshold: int,
    nesting_threshold: int,
    length_threshold: int
) -> Dict[str, int]:
    """Create thresholds dictionary for response.

    Args:
        cyclomatic_threshold: Cyclomatic complexity threshold
        cognitive_threshold: Cognitive complexity threshold
        nesting_threshold: Maximum nesting depth threshold
        length_threshold: Function length threshold in lines

    Returns:
        Dictionary of threshold values
    """
    return {
        "cyclomatic": cyclomatic_threshold,
        "cognitive": cognitive_threshold,
        "nesting_depth": nesting_threshold,
        "length": length_threshold
    }


def _execute_analysis(
    project_folder: str,
    language: str,
    thresholds: ComplexityThresholds,
    files_to_analyze: List[str],
    store_results: bool,
    include_trends: bool,
    max_threads: int,
    start_time: float,
    logger: Any
) -> Dict[str, Any]:
    """Execute the main analysis workflow.

    Args:
        project_folder: Project folder to analyze
        language: Programming language
        thresholds: Complexity thresholds
        files_to_analyze: List of files to analyze
        store_results: Whether to store results
        include_trends: Whether to include trends
        max_threads: Number of parallel threads
        start_time: Analysis start time
        logger: Logger instance

    Returns:
        Analysis response dictionary
    """
    # Analyze files in parallel
    all_functions, exceeding_functions, analyzer = _analyze_files_parallel(
        files_to_analyze,
        language,
        thresholds,
        max_threads
    )

    # Calculate summary statistics
    execution_time = time.time() - start_time
    summary, statistics = _calculate_summary_statistics(
        all_functions,
        exceeding_functions,
        len(files_to_analyze),
        execution_time
    )

    # Store results and generate trends
    run_id, stored_at, trends = _store_and_generate_trends(
        store_results,
        include_trends,
        project_folder,
        summary,
        all_functions,
        statistics
    )

    logger.info(
        "tool_completed",
        tool="analyze_complexity",
        execution_time_seconds=round(execution_time, 3),
        total_functions=summary["total_functions"],
        exceeding_threshold=len(exceeding_functions),
        status="success"
    )

    # Create thresholds dict from the thresholds object
    thresholds_dict = {
        "cyclomatic": thresholds.cyclomatic,
        "cognitive": thresholds.cognitive,
        "nesting_depth": thresholds.nesting_depth,
        "length": thresholds.lines
    }

    # Format and return response
    return _format_response(
        summary,
        thresholds_dict,
        exceeding_functions,
        run_id,
        stored_at,
        trends,
        statistics
    )


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
        # Validate inputs
        _validate_inputs(language)

        # Set up thresholds
        thresholds = ComplexityThresholds(
            cyclomatic=cyclomatic_threshold,
            cognitive=cognitive_threshold,
            nesting_depth=nesting_threshold,
            lines=length_threshold
        )

        # Find files to analyze
        files_to_analyze, file_finder = _find_files_to_analyze(
            project_folder,
            language,
            include_patterns,
            exclude_patterns,
            logger
        )

        # Handle no files found case
        if not files_to_analyze:
            execution_time = time.time() - start_time
            return _handle_no_files_found(language, execution_time)

        # Execute the main analysis workflow
        return _execute_analysis(
            project_folder,
            language,
            thresholds,
            files_to_analyze,
            store_results,
            include_trends,
            max_threads,
            start_time,
            logger
        )

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


def _get_default_smell_exclude_patterns() -> List[str]:
    """Get default exclude patterns for code smell detection."""
    return [
        "**/node_modules/**", "**/__pycache__/**", "**/venv/**",
        "**/.venv/**", "**/site-packages/**", "**/test*/**", "**/*test*"
    ]


def _prepare_smell_detection_params(
    include_patterns: List[str] | None,
    exclude_patterns: List[str] | None
) -> tuple[List[str], List[str]]:
    """Prepare and validate parameters for smell detection.

    Args:
        include_patterns: Glob patterns for files to include
        exclude_patterns: Glob patterns for files to exclude

    Returns:
        Tuple of (include_patterns, exclude_patterns) with defaults applied
    """
    if include_patterns is None:
        include_patterns = ["**/*"]
    if exclude_patterns is None:
        exclude_patterns = _get_default_smell_exclude_patterns()
    return include_patterns, exclude_patterns


def _process_smell_detection_result(
    result: Dict[str, Any],
    start_time: float,
    logger: Any
) -> Dict[str, Any]:
    """Add execution time and log completion metrics.

    Args:
        result: Smell detection result dictionary
        start_time: Start time of the analysis
        logger: Logger instance

    Returns:
        Result dictionary with execution_time_ms added
    """
    execution_time = time.time() - start_time
    result["execution_time_ms"] = round(execution_time * 1000)

    logger.info(
        "tool_completed",
        tool="detect_code_smells",
        files_analyzed=result.get("files_analyzed", 0),
        total_smells=result.get("total_smells", 0),
        execution_time_seconds=round(execution_time, 3)
    )

    return result


def detect_code_smells_tool(
    project_folder: str,
    language: str,
    include_patterns: List[str] | None = None,
    exclude_patterns: List[str] | None = None,
    long_function_lines: int = 50,
    parameter_count: int = 5,
    nesting_depth: int = 4,
    class_lines: int = 300,
    class_methods: int = 20,
    detect_magic_numbers: bool = True,
    severity_filter: str = "all",
    max_threads: int = 4
) -> Dict[str, Any]:
    """
    Detect common code smells, anti-patterns in a project.

    Identifies patterns that indicate potential design, maintainability issues:
    - Long Functions: Functions exceeding line count threshold
    - Parameter Bloat: Functions having too many parameters (>5)
    - Deep Nesting: Excessive nesting depth (>4 levels)
    - Large Classes: Classes having too many methods, lines
    - Magic Numbers: Hard-coded literals (excludes 0, 1, -1, 2, 10, 100)

    Each smell is rated by severity (high/medium/low) based on how far it exceeds thresholds,
    includes actionable suggestions to improve code.

    Args:
        project_folder: Absolute path to the project folder to analyze
        language: Programming language (python, typescript, javascript, java)
        include_patterns: Glob patterns selecting files to include (e.g., ['src/**/*.py'])
        exclude_patterns: Glob patterns selecting files to exclude
        long_function_lines: Line count threshold detecting long function smell (default: 50)
        parameter_count: Parameter count threshold detecting parameter bloat (default: 5)
        nesting_depth: Nesting depth threshold detecting deep nesting smell (default: 4)
        class_lines: Line count threshold detecting large class smell (default: 300)
        class_methods: Method count threshold detecting large class smell (default: 20)
        detect_magic_numbers: Whether to detect magic number smells
        severity_filter: Filter by severity: 'all', 'high', 'medium', 'low'
        max_threads: Number of parallel threads used in analysis (default: 4)

    Returns:
        Dictionary containing analysis results including summary, detected smells by severity

    Example usage:
        detect_code_smells_tool(project_folder="/path/to/project", language="python")
        detect_code_smells_tool(project_folder="/path/to/project", language="typescript", severity_filter="high")
    """
    # Import here to avoid circular import with quality.smells
    from ast_grep_mcp.features.quality.smells import detect_code_smells_impl

    logger = get_logger("tool.detect_code_smells")
    start_time = time.time()

    # Prepare parameters with defaults
    include_patterns, exclude_patterns = _prepare_smell_detection_params(
        include_patterns, exclude_patterns
    )

    logger.info(
        "tool_invoked",
        tool="detect_code_smells",
        project_folder=project_folder,
        language=language,
    )

    try:
        result = detect_code_smells_impl(
            project_folder=project_folder,
            language=language,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            long_function_lines=long_function_lines,
            parameter_count=parameter_count,
            nesting_depth=nesting_depth,
            class_lines=class_lines,
            class_methods=class_methods,
            detect_magic_numbers=detect_magic_numbers,
            severity_filter=severity_filter,
            max_threads=max_threads
        )

        # Process result and add execution time
        return _process_smell_detection_result(result, start_time, logger)

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


def register_complexity_tools(mcp: Any) -> None:
    """Register complexity analysis tools with the MCP server.

    Args:
        mcp: FastMCP server instance
    """

    @mcp.tool()  # type: ignore[misc]
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

    @mcp.tool()  # type: ignore[misc]
    def test_sentry_integration(
        test_type: Literal["error", "warning", "breadcrumb", "span"] = Field(
            default="breadcrumb",
            description="Type of Sentry test: 'error' (exception), 'warning' (capture_message), 'breadcrumb', or 'span' (performance)"
        ),
        message: str = Field(default="Test message", description="Custom test message")
    ) -> Dict[str, Any]:
        """Wrapper that calls the standalone test_sentry_integration_tool function."""
        return test_sentry_integration_tool(test_type=test_type, message=message)

    @mcp.tool()  # type: ignore[misc]
    def detect_code_smells(
        project_folder: str = Field(description="The absolute path to the project folder to analyze"),
        language: str = Field(description="The programming language (python, typescript, javascript, java)"),
        include_patterns: List[str] = Field(
            default_factory=lambda: ["**/*"],
            description="Glob patterns for files to include (e.g., ['src/**/*.py'])"
        ),
        exclude_patterns: List[str] = Field(
            default_factory=lambda: [
                "**/node_modules/**", "**/__pycache__/**", "**/venv/**",
                "**/.venv/**", "**/site-packages/**", "**/test*/**", "**/*test*"
            ],
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
        """Wrapper that calls the standalone detect_code_smells_tool function."""
        return detect_code_smells_tool(
            project_folder=project_folder,
            language=language,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            long_function_lines=long_function_lines,
            parameter_count=parameter_count,
            nesting_depth=nesting_depth,
            class_lines=class_lines,
            class_methods=class_methods,
            detect_magic_numbers=detect_magic_numbers,
            severity_filter=severity_filter,
            max_threads=max_threads
        )
