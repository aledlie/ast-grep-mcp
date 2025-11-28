"""Orchestration for deduplication candidate analysis.

This module handles the multi-step process of finding duplicates,
ranking them, checking test coverage, and generating recommendations.
"""
from typing import Any, Dict, List

from ...core.logging import get_logger
from .coverage import TestCoverageDetector
from .detector import DuplicationDetector
from .ranker import DuplicationRanker
from .recommendations import RecommendationEngine


class DeduplicationAnalysisOrchestrator:
    """Orchestrates the complete deduplication candidate analysis workflow."""

    def __init__(self):
        """Initialize the orchestrator."""
        self.logger = get_logger("deduplication.analysis_orchestrator")
        self.detector = DuplicationDetector()
        self.ranker = DuplicationRanker()
        self.coverage_detector = TestCoverageDetector()
        self.recommendation_engine = RecommendationEngine()

    def analyze_candidates(
        self,
        project_path: str,
        language: str,
        min_similarity: float = 0.8,
        include_test_coverage: bool = True,
        min_lines: int = 5,
        max_candidates: int = 100,
        exclude_patterns: List[str] | None = None
    ) -> Dict[str, Any]:
        """Analyze a project for deduplication candidates.

        This orchestrates a 4-step workflow:
        1. Find duplicates
        2. Rank candidates by refactoring value
        3. Check test coverage (if requested)
        4. Generate recommendations

        Args:
            project_path: Project folder path
            language: Programming language
            min_similarity: Minimum similarity threshold (0.0-1.0)
            include_test_coverage: Whether to check test coverage
            min_lines: Minimum lines to consider
            max_candidates: Maximum candidates to return
            exclude_patterns: Path patterns to exclude

        Returns:
            Analysis results with ranked candidates and metadata
        """
        self.logger.info(
            "analysis_start",
            project_path=project_path,
            language=language,
            max_candidates=max_candidates
        )

        # Step 1: Find duplicates
        duplication_results = self.detector.find_duplication(
            project_folder=project_path,
            language=language,
            min_similarity=min_similarity,
            min_lines=min_lines,
            exclude_patterns=exclude_patterns or []
        )

        # Step 2: Rank candidates by refactoring value
        ranked_candidates = self.ranker.rank_deduplication_candidates(
            duplication_results.get("duplicates", [])
        )

        # Step 3: Check test coverage if requested
        if include_test_coverage:
            self._add_test_coverage(
                ranked_candidates[:max_candidates],
                language,
                project_path
            )

        # Step 4: Generate recommendations
        self._add_recommendations(ranked_candidates[:max_candidates])

        # Calculate summary statistics
        total_savings = self._calculate_total_savings(
            ranked_candidates[:max_candidates]
        )

        self.logger.info(
            "analysis_complete",
            total_groups=len(ranked_candidates),
            returned_candidates=min(max_candidates, len(ranked_candidates)),
            total_savings_potential=total_savings
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

    def _add_test_coverage(
        self,
        candidates: List[Dict[str, Any]],
        language: str,
        project_path: str
    ) -> None:
        """Add test coverage information to candidates.

        Args:
            candidates: List of candidates to enrich
            language: Programming language
            project_path: Project folder path
        """
        for candidate in candidates:
            files = candidate.get("files", [])
            if files:
                coverage_map = self.coverage_detector.get_test_coverage_for_files(
                    files, language, project_path
                )
                candidate["test_coverage"] = coverage_map
                candidate["has_tests"] = any(coverage_map.values())

        self.logger.debug(
            "test_coverage_added",
            candidate_count=len(candidates)
        )

    def _add_recommendations(
        self,
        candidates: List[Dict[str, Any]]
    ) -> None:
        """Add recommendations to candidates.

        Args:
            candidates: List of candidates to enrich
        """
        for candidate in candidates:
            recommendation = self.recommendation_engine.generate_deduplication_recommendation(
                score=candidate.get("score", 0),
                complexity=candidate.get("complexity_score", 5),
                lines_saved=candidate.get("lines_saved", 0),
                has_tests=candidate.get("has_tests", False),
                affected_files=len(candidate.get("files", []))
            )
            candidate["recommendation"] = recommendation

        self.logger.debug(
            "recommendations_added",
            candidate_count=len(candidates)
        )

    def _calculate_total_savings(
        self,
        candidates: List[Dict[str, Any]]
    ) -> int:
        """Calculate total potential line savings.

        Args:
            candidates: List of candidates

        Returns:
            Total potential lines saved
        """
        total = sum(
            c.get("lines_saved", 0) * len(c.get("files", []))
            for c in candidates
        )
        return total
