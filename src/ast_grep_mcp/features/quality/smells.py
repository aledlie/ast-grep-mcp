"""Code smell detection implementation.

This module provides functionality to detect common code smells and anti-patterns:
- Long functions
- Parameter bloat
- Deep nesting
- Large classes
- Magic numbers

Each smell includes severity ratings and actionable suggestions.
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List

from ast_grep_mcp.core.logging import get_logger
from ast_grep_mcp.features.quality.smells_detectors import (
    DeepNestingDetector,
    LargeClassDetector,
    LongFunctionDetector,
    MagicNumberDetector,
    ParameterBloatDetector,
    SmellAnalyzer
)
from ast_grep_mcp.features.quality.smells_helpers import (
    aggregate_smell_results,
    find_smell_analysis_files,
    format_smell_detection_response,
    validate_smell_detection_inputs
)


def detect_code_smells_impl(
    project_folder: str,
    language: str,
    include_patterns: List[str],
    exclude_patterns: List[str],
    long_function_lines: int,
    parameter_count: int,
    nesting_depth: int,
    class_lines: int,
    class_methods: int,
    detect_magic_numbers: bool,
    severity_filter: str,
    max_threads: int
) -> Dict[str, Any]:
    """Detect common code smells in a project.

    This function orchestrates smell detection using modular detector classes.

    Args:
        project_folder: Absolute path to project
        language: Programming language (python, typescript, javascript, java)
        include_patterns: Glob patterns for files to include
        exclude_patterns: Glob patterns for files to exclude
        long_function_lines: Line count threshold for long function smell
        parameter_count: Parameter count threshold for parameter bloat
        nesting_depth: Nesting depth threshold for deep nesting smell
        class_lines: Line count threshold for large class smell
        class_methods: Method count threshold for large class smell
        detect_magic_numbers: Whether to detect magic number smells
        severity_filter: Filter by severity: 'all', 'high', 'medium', 'low'
        max_threads: Number of parallel threads for analysis

    Returns:
        Dictionary containing smell detection results with summary and details
    """
    logger = get_logger("detect_code_smells")

    try:
        # Step 1: Validate inputs and get normalized values
        project_path, file_ext, normalized_language = validate_smell_detection_inputs(
            project_folder, language, severity_filter
        )
    except ValueError as e:
        return {"error": str(e)}

    # Step 2: Find files to analyze
    files_to_analyze = find_smell_analysis_files(
        project_path, file_ext, include_patterns, exclude_patterns
    )

    if not files_to_analyze:
        return {
            "error": f"No {language} files found matching patterns",
            "project_folder": project_folder,
            "include_patterns": include_patterns,
            "exclude_patterns": exclude_patterns
        }

    # Step 3: Initialize smell detectors with thresholds
    detectors = _create_detectors(
        long_function_lines,
        parameter_count,
        nesting_depth,
        class_lines,
        class_methods,
        detect_magic_numbers
    )

    # Step 4: Create analyzer and analyze files in parallel
    analyzer = SmellAnalyzer(detectors)

    def analyze_file_wrapper(file_path: str) -> List[Dict[str, Any]]:
        """Wrapper for parallel execution."""
        return analyzer.analyze_file(file_path, normalized_language, project_path)

    # Execute analysis in parallel
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        file_results = list(executor.map(analyze_file_wrapper, files_to_analyze))

    # Step 5: Aggregate results from all files
    all_smells = aggregate_smell_results(file_results)

    # Step 6: Format and return response
    thresholds = {
        "long_function_lines": long_function_lines,
        "parameter_count": parameter_count,
        "nesting_depth": nesting_depth,
        "class_lines": class_lines,
        "class_methods": class_methods
    }

    return format_smell_detection_response(
        project_folder,
        language,
        len(files_to_analyze),
        all_smells,
        thresholds,
        severity_filter
    )


def _create_detectors(
    long_function_lines: int,
    parameter_count: int,
    nesting_depth: int,
    class_lines: int,
    class_methods: int,
    detect_magic_numbers: bool
) -> List[Any]:
    """Create and configure smell detectors.

    Args:
        long_function_lines: Threshold for function length
        parameter_count: Threshold for parameter count
        nesting_depth: Threshold for nesting depth
        class_lines: Threshold for class lines
        class_methods: Threshold for class methods
        detect_magic_numbers: Whether to detect magic numbers

    Returns:
        List of configured detector instances
    """
    detectors = [
        LongFunctionDetector(long_function_lines),
        ParameterBloatDetector(parameter_count),
        DeepNestingDetector(nesting_depth),
        LargeClassDetector(class_lines, class_methods)
    ]

    if detect_magic_numbers:
        detectors.append(MagicNumberDetector(enabled=True))

    return detectors

