"""Statistics aggregation and result formatting for complexity analysis.

This module handles calculating summary statistics, storing results,
retrieving trends, and formatting the final response.
"""

import subprocess
from typing import Any, Dict, List, Optional

from ...core.logging import get_logger
from ...models.complexity import FunctionComplexity
from .storage import ComplexityStorage


class ComplexityStatisticsAggregator:
    """Aggregates statistics and formats complexity analysis results."""

    def __init__(self) -> None:
        """Initialize the statistics aggregator."""
        self.logger = get_logger("complexity.statistics")

    def calculate_summary(
        self,
        all_functions: List[FunctionComplexity],
        exceeding_functions: List[FunctionComplexity],
        total_files: int,
        execution_time: float,
    ) -> Dict[str, Any]:
        """Calculate summary statistics from analysis results.

        Args:
            all_functions: All analyzed functions
            exceeding_functions: Functions exceeding thresholds
            total_files: Total number of files analyzed
            execution_time: Analysis execution time in seconds

        Returns:
            Summary statistics dictionary
        """
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

        return {
            "total_functions": total_functions,
            "total_files": total_files,
            "exceeding_threshold": len(exceeding_functions),
            "avg_cyclomatic": round(avg_cyclomatic, 2),
            "avg_cognitive": round(avg_cognitive, 2),
            "max_cyclomatic": max_cyclomatic,
            "max_cognitive": max_cognitive,
            "max_nesting": max_nesting,
            "analysis_time_seconds": round(execution_time, 3),
        }

    def get_git_info(self, project_folder: str) -> tuple[Optional[str], Optional[str]]:
        """Get current git commit and branch information.

        Args:
            project_folder: Project root folder

        Returns:
            Tuple of (commit_hash, branch_name) or (None, None) if not a git repo
        """
        commit_hash = None
        branch_name = None

        try:
            # Get commit hash
            commit_result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=project_folder, capture_output=True, text=True, timeout=5)
            if commit_result.returncode == 0:
                commit_hash = commit_result.stdout.strip() or None

            # Get branch name
            branch_result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=project_folder, capture_output=True, text=True, timeout=5
            )
            if branch_result.returncode == 0:
                branch_name = branch_result.stdout.strip() or None

        except Exception as e:
            self.logger.debug("git_info_failed", error=str(e))

        return commit_hash, branch_name

    def store_results(
        self, project_folder: str, summary: Dict[str, Any], all_functions: List[FunctionComplexity]
    ) -> tuple[Optional[str], Optional[str]]:
        """Store analysis results in database.

        Args:
            project_folder: Project root folder
            summary: Summary statistics
            all_functions: All analyzed functions

        Returns:
            Tuple of (run_id, stored_at) or (None, None) if storage failed
        """
        try:
            storage = ComplexityStorage()
            commit_hash, branch_name = self.get_git_info(project_folder)

            # Build results data for storage
            results_data = {
                "total_functions": summary["total_functions"],
                "total_files": summary["total_files"],
                "avg_cyclomatic": summary["avg_cyclomatic"],
                "avg_cognitive": summary["avg_cognitive"],
                "max_cyclomatic": summary["max_cyclomatic"],
                "max_cognitive": summary["max_cognitive"],
                "max_nesting": summary["max_nesting"],
                "violation_count": summary["exceeding_threshold"],
                "duration_ms": int(summary["analysis_time_seconds"] * 1000),
            }

            run_id = storage.store_analysis_run(project_folder, results_data, all_functions, commit_hash, branch_name)

            self.logger.info("results_stored", run_id=run_id)
            return str(run_id), str(storage.db_path)

        except Exception as e:
            self.logger.warning("storage_failed", error=str(e))
            return None, None

    def get_trends(self, project_folder: str, days: int = 30) -> Optional[List[Dict[str, Any]]]:
        """Get historical trend data for project.

        Args:
            project_folder: Project root folder
            days: Number of days of history to include

        Returns:
            Trend data dictionary or None if failed
        """
        try:
            storage = ComplexityStorage()
            trends = storage.get_project_trends(project_folder, days=days)
            self.logger.info("trends_retrieved", days=days)
            return trends
        except Exception as e:
            self.logger.warning("trends_failed", error=str(e))
            return None

    def format_response(
        self,
        summary: Dict[str, Any],
        thresholds: Dict[str, int],
        exceeding_functions: List[FunctionComplexity],
        run_id: Optional[str] = None,
        stored_at: Optional[str] = None,
        trends: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Format final analysis response.

        Args:
            summary: Summary statistics
            thresholds: Complexity thresholds used
            exceeding_functions: Functions exceeding thresholds
            run_id: Storage run ID (optional)
            stored_at: Storage location (optional)
            trends: Trend data (optional)

        Returns:
            Formatted response dictionary
        """
        response: Dict[str, Any] = {
            "summary": summary,
            "thresholds": thresholds,
            "functions": [
                {
                    "name": f.function_name,
                    "file": f.file_path,
                    "lines": f"{f.start_line}-{f.end_line}",
                    "cyclomatic": f.metrics.cyclomatic,
                    "cognitive": f.metrics.cognitive,
                    "nesting_depth": f.metrics.nesting_depth,
                    "length": f.metrics.lines,
                    "exceeds": f.exceeds,
                }
                for f in exceeding_functions
            ],
            "message": (
                f"Found {len(exceeding_functions)} function(s) exceeding thresholds "
                f"out of {summary['total_functions']} total"
            ),
        }

        if run_id:
            response["storage"] = {"run_id": run_id, "stored_at": stored_at}

        if trends:
            response["trends"] = trends

        return response
