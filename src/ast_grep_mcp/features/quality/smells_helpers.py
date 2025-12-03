"""Helper functions for code smell detection.

This module contains utility functions extracted from the main smell detection
implementation to reduce complexity and improve maintainability.
"""

from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, List

from ast_grep_mcp.core.logging import get_logger


def validate_smell_detection_inputs(project_folder: str, language: str, severity_filter: str) -> tuple[Path, str, str]:
    """Validate inputs for smell detection.

    Args:
        project_folder: Path to project directory
        language: Programming language
        severity_filter: Severity filter (all, high, medium, low)

    Returns:
        Tuple of (project_path, file_extension, normalized_language)

    Raises:
        Dict with error key if validation fails
    """
    # Validate project folder
    project_path = Path(project_folder)
    if not project_path.exists():
        raise ValueError(f"Project folder not found: {project_folder}")
    if not project_path.is_dir():
        raise ValueError(f"Path is not a directory: {project_folder}")

    # Validate and get file extension for language
    ext_map = {"python": ".py", "typescript": ".ts", "javascript": ".js", "java": ".java"}
    normalized_language = language.lower()
    if normalized_language not in ext_map:
        raise ValueError(f"Unsupported language: {language}")

    file_ext = ext_map[normalized_language]

    # Validate severity filter
    valid_severities = ["all", "high", "medium", "low"]
    if severity_filter not in valid_severities:
        raise ValueError(f"Invalid severity filter: {severity_filter}. Must be one of {valid_severities}")

    return project_path, file_ext, normalized_language


def find_smell_analysis_files(project_path: Path, file_ext: str, include_patterns: List[str], exclude_patterns: List[str]) -> List[str]:
    """Find files to analyze for code smells.

    Args:
        project_path: Path to project directory
        file_ext: File extension to search for
        include_patterns: Glob patterns for files to include
        exclude_patterns: Glob patterns for files to exclude

    Returns:
        List of file paths to analyze
    """
    logger = get_logger("smell_detection.find_files")

    # Find all matching files
    all_files = []
    for pattern in include_patterns:
        # Adjust pattern to ensure it matches the file extension
        if not pattern.endswith(file_ext) and not pattern.endswith("*"):
            pattern = pattern.rstrip("/") + f"/**/*{file_ext}"
        elif pattern.endswith("*") and not pattern.endswith(file_ext):
            pattern = pattern + file_ext if pattern.endswith("*/") else pattern.rstrip("*") + f"*{file_ext}"

        matches = list(project_path.glob(pattern.lstrip("/")))
        all_files.extend([str(f) for f in matches if f.is_file()])

    # Remove duplicates
    all_files = list(set(all_files))

    # Filter by exclude patterns
    filtered_files = []
    for file_path in all_files:
        excluded = False
        try:
            rel_path = str(Path(file_path).relative_to(project_path))
            for exc_pattern in exclude_patterns:
                if fnmatch(rel_path, exc_pattern.lstrip("/")):
                    excluded = True
                    break
        except ValueError:
            # File is outside project path, exclude it
            excluded = True

        if not excluded:
            filtered_files.append(file_path)

    logger.info("files_found", total=len(all_files), filtered=len(filtered_files))
    return filtered_files


def calculate_smell_severity(metric: float, threshold: float, smell_type: str) -> str:
    """Calculate severity level based on metric value and threshold.

    Args:
        metric: The measured value
        threshold: The threshold value
        smell_type: Type of smell for specific severity calculation

    Returns:
        Severity level: "high", "medium", or "low"
    """
    ratio = metric / threshold if threshold > 0 else float("inf")

    # Different smell types may have different severity mappings
    if smell_type in ["long_function", "large_class"]:
        if ratio > 2.0:
            return "high"
        elif ratio > 1.5:
            return "medium"
        else:
            return "low"
    elif smell_type == "parameter_bloat":
        if metric > threshold * 2:
            return "high"
        elif metric > threshold + 2:
            return "medium"
        else:
            return "low"
    elif smell_type == "deep_nesting":
        excess = metric - threshold
        if excess > 2:
            return "high"
        elif excess > 1:
            return "medium"
        else:
            return "low"
    else:  # magic_number and others
        return "low"


def format_smell_detection_response(
    project_folder: str, language: str, files_analyzed: int, smells: List[Dict[str, Any]], thresholds: Dict[str, Any], severity_filter: str
) -> Dict[str, Any]:
    """Format the final smell detection response.

    Args:
        project_folder: Path to project directory
        language: Programming language analyzed
        files_analyzed: Number of files analyzed
        smells: List of detected smells
        thresholds: Threshold values used
        severity_filter: Applied severity filter

    Returns:
        Formatted response dictionary
    """
    # Filter by severity if requested
    if severity_filter != "all":
        smells = [s for s in smells if s.get("severity") == severity_filter]

    # Sort by severity (high > medium > low) then by type
    severity_order = {"high": 0, "medium": 1, "low": 2}
    smells.sort(key=lambda s: (severity_order.get(s.get("severity", "low"), 3), s.get("type", "")))

    # Generate summary statistics
    smell_counts: Dict[str, int] = {}
    severity_counts: Dict[str, int] = {"high": 0, "medium": 0, "low": 0}

    for smell in smells:
        smell_type = smell.get("type", "unknown")
        smell_counts[smell_type] = smell_counts.get(smell_type, 0) + 1
        severity_counts[smell.get("severity", "low")] += 1

    return {
        "project_folder": project_folder,
        "language": language,
        "files_analyzed": files_analyzed,
        "total_smells": len(smells),
        "summary": {"by_type": smell_counts, "by_severity": severity_counts},
        "smells": smells,
        "thresholds": thresholds,
    }


def aggregate_smell_results(file_results: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Aggregate smell detection results from multiple files.

    Args:
        file_results: List of smell lists from individual files

    Returns:
        Flattened list of all smells
    """
    all_smells = []
    for file_smells in file_results:
        if file_smells:  # Skip empty results
            all_smells.extend(file_smells)
    return all_smells
