"""MCP tool wrappers for deduplication features.

This module provides the high-level tool interfaces exposed via MCP.
These functions wrap the underlying deduplication modules to provide
a clean API for the MCP server.
"""

from typing import Any, Dict, List, Optional

from ...core.logging import get_logger
from .applicator import DeduplicationApplicator
from .benchmark import DeduplicationBenchmark
from .coverage import TestCoverageDetector
from .detector import DuplicationDetector
from .ranker import DuplicationRanker
from .recommendations import RecommendationEngine


def find_duplication_tool(
    project_folder: str,
    language: str,
    min_similarity: float = 0.8,
    min_lines: int = 5,
    exclude_patterns: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Find duplicate functions/classes/methods in a codebase.

    This is the main entry point for the find_duplication MCP tool.

    Args:
        project_folder: Path to the project folder
        language: Programming language
        min_similarity: Minimum similarity threshold (0-1)
        min_lines: Minimum lines to consider
        exclude_patterns: Path patterns to exclude

    Returns:
        Dictionary with duplication results
    """
    logger = get_logger("deduplication.tool.find")

    if exclude_patterns is None:
        exclude_patterns = [
            "site-packages", "node_modules", ".venv",
            "venv", "vendor", "__pycache__", ".git"
        ]

    detector = DuplicationDetector()
    results = detector.find_duplication(
        project_folder=project_folder,
        language=language,
        min_similarity=min_similarity,
        min_lines=min_lines,
        exclude_patterns=exclude_patterns
    )

    logger.info(
        "find_duplication_complete",
        duplicate_groups=results.get("duplicate_groups", 0),
        total_duplicates=results.get("total_duplicates", 0),
        total_lines_duplicated=results.get("total_lines_duplicated", 0)
    )

    return results


def analyze_deduplication_candidates_tool(
    project_path: str,
    language: str,
    min_similarity: float = 0.8,
    include_test_coverage: bool = True,
    min_lines: int = 5,
    max_candidates: int = 100,
    exclude_patterns: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Analyze a project for deduplication candidates and return ranked results.

    This tool extends find_duplication by:
    1. Scoring duplicates by complexity, frequency, and maintainability impact
    2. Optionally checking test coverage to prioritize well-tested code
    3. Ranking candidates by refactoring value (highest savings + lowest risk first)
    4. Providing actionable recommendations for each candidate group

    Args:
        project_path: The absolute path to the project folder to analyze
        language: The target language
        min_similarity: Minimum similarity threshold (0.0-1.0)
        include_test_coverage: Whether to check test coverage for prioritization
        min_lines: Minimum number of lines to consider for duplication
        max_candidates: Maximum number of candidates to return
        exclude_patterns: Path patterns to exclude from analysis

    Returns:
        Dictionary with:
        - candidates: List of duplicate groups with scores and rankings
        - total_groups: Number of duplication groups found
        - total_savings_potential: Total lines that could be saved
        - analysis_metadata: Timing and configuration info
    """
    logger = get_logger("deduplication.tool.analyze")

    if exclude_patterns is None:
        exclude_patterns = [
            "site-packages", "node_modules", ".venv",
            "venv", "vendor", "__pycache__", ".git"
        ]

    # Step 1: Find duplicates
    detector = DuplicationDetector()
    duplication_results = detector.find_duplication(
        project_folder=project_path,
        language=language,
        min_similarity=min_similarity,
        min_lines=min_lines,
        exclude_patterns=exclude_patterns
    )

    # Step 2: Analyze and rank candidates
    ranker = DuplicationRanker()
    ranked_candidates = ranker.rank_deduplication_candidates(
        duplication_results.get("duplicates", [])
    )

    # Step 3: Check test coverage if requested
    if include_test_coverage:
        coverage_detector = TestCoverageDetector()
        for candidate in ranked_candidates[:max_candidates]:
            files = candidate.get("files", [])
            if files:
                coverage_map = coverage_detector.get_test_coverage_for_files(
                    files, language, project_path
                )
                candidate["test_coverage"] = coverage_map
                candidate["has_tests"] = any(coverage_map.values())

    # Step 4: Generate recommendations
    recommendation_engine = RecommendationEngine()
    for candidate in ranked_candidates[:max_candidates]:
        recommendation = recommendation_engine.generate_deduplication_recommendation(
            score=candidate.get("score", 0),
            complexity=candidate.get("complexity_score", 5),
            lines_saved=candidate.get("lines_saved", 0),
            has_tests=candidate.get("has_tests", False),
            affected_files=len(candidate.get("files", []))
        )
        candidate["recommendation"] = recommendation

    # Calculate summary stats
    total_savings = sum(
        c.get("lines_saved", 0) * len(c.get("files", []))
        for c in ranked_candidates[:max_candidates]
    )

    logger.info(
        "analyze_candidates_complete",
        total_groups=len(ranked_candidates),
        returned_candidates=min(max_candidates, len(ranked_candidates)),
        total_savings_potential=total_savings,
        include_test_coverage=include_test_coverage
    )

    return {
        "candidates": ranked_candidates[:max_candidates],
        "total_groups": len(ranked_candidates),
        "total_savings_potential": total_savings,
        "analysis_metadata": {
            "language": language,
            "min_similarity": min_similarity,
            "min_lines": min_lines,
            "include_test_coverage": include_test_coverage,
            "project_path": project_path
        }
    }


def apply_deduplication_tool(
    project_folder: str,
    group_id: int,
    refactoring_plan: Dict[str, Any],
    dry_run: bool = True,
    backup: bool = True,
    extract_to_file: Optional[str] = None
) -> Dict[str, Any]:
    """Apply automated deduplication refactoring with comprehensive syntax validation.

    Phase 3.5 VALIDATION PIPELINE:
    1. PRE-VALIDATION: Validate all generated code before applying
    2. APPLICATION: Create backup and apply changes
    3. POST-VALIDATION: Validate modified files
    4. AUTO-ROLLBACK: Restore from backup if validation fails

    Args:
        project_folder: The absolute path to the project folder
        group_id: The duplication group ID from find_duplication results
        refactoring_plan: The refactoring plan with generated_code, files_affected, strategy, language
        dry_run: Preview changes without applying (default: true for safety)
        backup: Create backup before applying changes (default: true)
        extract_to_file: Where to place extracted function (auto-detect if None)

    Returns:
        Dictionary with:
        - status: "preview" | "success" | "failed" | "rolled_back"
        - validation: Pre and post validation results with detailed errors
        - errors: Detailed error info with file, line, message, and suggested fix
    """
    logger = get_logger("deduplication.tool.apply")

    applicator = DeduplicationApplicator()
    result = applicator.apply_deduplication(
        project_folder=project_folder,
        group_id=group_id,
        refactoring_plan=refactoring_plan,
        dry_run=dry_run,
        backup=backup,
        extract_to_file=extract_to_file
    )

    logger.info(
        "apply_deduplication_complete",
        status=result.get("status"),
        group_id=group_id,
        dry_run=dry_run,
        files_modified=len(result.get("files_modified", []))
    )

    return result


def benchmark_deduplication_tool(
    iterations: int = 10,
    save_baseline: bool = False,
    check_regression: bool = True
) -> Dict[str, Any]:
    """Run performance benchmarks for deduplication functions.

    Benchmarks the following operations:
    - **scoring**: calculate_deduplication_score (should be < 1ms)
    - **pattern_analysis**: rank_deduplication_candidates and analyze variations
    - **code_generation**: generate_deduplication_recommendation
    - **full_workflow**: create_enhanced_duplication_response

    Args:
        iterations: Number of iterations per benchmark (default: 10)
        save_baseline: Save results as new baseline for regression detection
        check_regression: Check results against baseline for performance regressions

    Returns:
        Dictionary with benchmark results including:
        - total_benchmarks: Number of benchmarks run
        - results: List of benchmark results with statistics
        - regression_detected: Whether any regressions were found
        - regression_errors: List of specific regression failures
    """
    logger = get_logger("deduplication.tool.benchmark")

    benchmark = DeduplicationBenchmark()
    results = benchmark.benchmark_deduplication(
        iterations=iterations,
        save_baseline=save_baseline,
        check_regression=check_regression
    )

    logger.info(
        "benchmark_complete",
        total_benchmarks=results.get("total_benchmarks"),
        regression_detected=results.get("regression_detected"),
        execution_time_seconds=results.get("execution_time_seconds")
    )

    return results


def register_deduplication_tools(mcp):
    """Register all deduplication tools with the MCP server.

    Args:
        mcp: FastMCP instance to register tools with
    """
    # Register the 4 deduplication tools
    mcp.tool()(find_duplication_tool)
    mcp.tool()(analyze_deduplication_candidates_tool)
    mcp.tool()(apply_deduplication_tool)
    mcp.tool()(benchmark_deduplication_tool)
