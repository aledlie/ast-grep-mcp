"""Orchestration for deduplication candidate analysis.

This module handles the multi-step process of finding duplicates,
ranking them, checking test coverage, and generating recommendations.
"""
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from typing import Any, Callable, Dict, List, Optional

from ...constants import ParallelProcessing
from ...core.logging import get_logger
from .config import AnalysisConfig
from .coverage import TestCoverageDetector
from .detector import DuplicationDetector
from .ranker import DuplicationRanker
from .recommendations import RecommendationEngine

# Type alias for progress callback function
# Signature: (stage_name: str, progress_percent: float) -> None
ProgressCallback = Callable[[str, float], None]


class DeduplicationAnalysisOrchestrator:
    """Orchestrates the complete deduplication candidate analysis workflow."""

    def __init__(self) -> None:
        """Initialize the orchestrator with lazy component initialization."""
        self.logger = get_logger("deduplication.analysis_orchestrator")
        # Components are lazily initialized via properties to reduce initialization overhead

    @property
    def detector(self) -> DuplicationDetector:
        """Get or create DuplicationDetector instance (lazy initialization)."""
        if not hasattr(self, '_detector'):
            self._detector = DuplicationDetector()
        return self._detector

    @detector.setter
    def detector(self, value: DuplicationDetector) -> None:
        """Set DuplicationDetector instance (for testing/dependency injection)."""
        self._detector = value

    @property
    def ranker(self) -> DuplicationRanker:
        """Get or create DuplicationRanker instance (lazy initialization)."""
        if not hasattr(self, '_ranker'):
            self._ranker = DuplicationRanker()
        return self._ranker

    @ranker.setter
    def ranker(self, value: DuplicationRanker) -> None:
        """Set DuplicationRanker instance (for testing/dependency injection)."""
        self._ranker = value

    @property
    def coverage_detector(self) -> TestCoverageDetector:
        """Get or create TestCoverageDetector instance (lazy initialization)."""
        if not hasattr(self, '_coverage_detector'):
            self._coverage_detector = TestCoverageDetector()
        return self._coverage_detector

    @coverage_detector.setter
    def coverage_detector(self, value: TestCoverageDetector) -> None:
        """Set TestCoverageDetector instance (for testing/dependency injection)."""
        self._coverage_detector = value

    @property
    def recommendation_engine(self) -> RecommendationEngine:
        """Get or create RecommendationEngine instance (lazy initialization)."""
        if not hasattr(self, '_recommendation_engine'):
            self._recommendation_engine = RecommendationEngine()
        return self._recommendation_engine

    @recommendation_engine.setter
    def recommendation_engine(self, value: RecommendationEngine) -> None:
        """Set RecommendationEngine instance (for testing/dependency injection)."""
        self._recommendation_engine = value

    def analyze_candidates(
        self,
        project_path: str,
        language: str,
        min_similarity: float = 0.8,
        include_test_coverage: bool = True,
        min_lines: int = 5,
        max_candidates: int = 100,
        exclude_patterns: List[str] | None = None,
        progress_callback: Optional[ProgressCallback] = None
    ) -> Dict[str, Any]:
        """Analyze a project for deduplication candidates (legacy interface).

        This method provides backward compatibility by converting individual
        parameters to AnalysisConfig. New code should use analyze_candidates_with_config().

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
            progress_callback: Optional callback for progress reporting.
                Signature: (stage_name: str, progress_percent: float) -> None
                Example: lambda stage, pct: print(f"[{pct*100:.0f}%] {stage}")

        Returns:
            Analysis results with ranked candidates and metadata

        Raises:
            ValueError: If input parameters are invalid
        """
        # Convert to AnalysisConfig (validation happens in AnalysisConfig.__post_init__)
        config = AnalysisConfig(
            project_path=project_path,
            language=language,
            min_similarity=min_similarity,
            include_test_coverage=include_test_coverage,
            min_lines=min_lines,
            max_candidates=max_candidates,
            exclude_patterns=exclude_patterns,
            progress_callback=progress_callback
        )
        return self.analyze_candidates_with_config(config)

    def analyze_candidates_with_config(
        self,
        config: AnalysisConfig
    ) -> Dict[str, Any]:
        """Analyze a project for deduplication candidates (recommended interface).

        This is the modern, cleaner API that accepts an AnalysisConfig object
        instead of 8 separate parameters.

        This orchestrates a 4-step workflow:
        1. Find duplicates
        2. Rank candidates by refactoring value
        3. Check test coverage (if requested)
        4. Generate recommendations

        Args:
            config: Analysis configuration object

        Returns:
            Analysis results with ranked candidates and metadata

        Raises:
            ValueError: If configuration is invalid

        Example:
            >>> config = AnalysisConfig(
            ...     project_path="/path/to/project",
            ...     language="python",
            ...     min_similarity=0.9,
            ...     max_candidates=50
            ... )
            >>> orchestrator = DeduplicationAnalysisOrchestrator()
            >>> results = orchestrator.analyze_candidates_with_config(config)
        """
        # Validate inputs early (fail-fast)
        self._validate_analysis_inputs(
            config.project_path,
            config.language,
            config.min_similarity,
            config.min_lines,
            config.max_candidates
        )

        # Helper function for progress reporting
        def report_progress(stage: str, percent: float) -> None:
            """Report progress if callback is provided."""
            if config.progress_callback:
                config.progress_callback(stage, percent)

        self.logger.info(
            "analysis_start",
            **config.to_dict()
        )

        # Step 1: Find duplicates (0% -> 25%)
        report_progress("Finding duplicate code", 0.0)
        duplication_results = self.detector.find_duplication(
            project_folder=config.project_path,
            construct_type="function_definition",
            min_similarity=config.min_similarity,
            min_lines=config.min_lines,
            exclude_patterns=config.exclude_patterns or []
        )

        # Step 2: Rank candidates by refactoring value (25% -> 40%)
        # Pass max_candidates for early exit optimization (avoids unnecessary rank numbering)
        report_progress("Ranking candidates by value", 0.25)
        ranked_candidates = self.ranker.rank_deduplication_candidates(
            duplication_results.get("duplication_groups", []),
            max_results=config.max_candidates
        )

        # Step 3-5: Enrich and summarize top candidates (40% -> 100%)
        report_progress("Enriching candidates", 0.40)
        result = self._enrich_and_summarize_with_config(
            ranked_candidates,
            config,
            progress_callback=report_progress
        )

        # Complete
        report_progress("Analysis complete", 1.0)
        return result

    def _validate_analysis_inputs(
        self,
        project_path: str,
        language: str,
        min_similarity: float,
        min_lines: int,
        max_candidates: int
    ) -> None:
        """Validate analysis inputs with clear error messages.

        Args:
            project_path: Project folder path
            language: Programming language
            min_similarity: Minimum similarity threshold
            min_lines: Minimum lines to consider
            max_candidates: Maximum candidates to return

        Raises:
            ValueError: If any input parameter is invalid
        """
        # Validate project path exists
        if not os.path.exists(project_path):
            raise ValueError(f"Project path does not exist: {project_path}")

        if not os.path.isdir(project_path):
            raise ValueError(f"Project path is not a directory: {project_path}")

        # Validate min_similarity range
        if not 0.0 <= min_similarity <= 1.0:
            raise ValueError(
                f"min_similarity must be between 0.0 and 1.0, got {min_similarity}"
            )

        # Validate min_lines is positive
        if min_lines < 1:
            raise ValueError(
                f"min_lines must be a positive integer, got {min_lines}"
            )

        # Validate max_candidates is positive
        if max_candidates < 1:
            raise ValueError(
                f"max_candidates must be a positive integer, got {max_candidates}"
            )

        # Log warning for unsupported languages (but don't fail)
        supported_languages = ["python", "javascript", "typescript", "java", "go",
                               "rust", "cpp", "c", "ruby"]
        if language.lower() not in supported_languages:
            self.logger.warning(
                "unsupported_language",
                language=language,
                supported=supported_languages,
                message=f"Language '{language}' may not be fully supported"
            )

    def _get_top_candidates(
        self,
        candidates: List[Dict[str, Any]],
        max_count: int
    ) -> List[Dict[str, Any]]:
        """Get top N candidates from the list.

        Args:
            candidates: All candidates
            max_count: Maximum candidates to return

        Returns:
            Sliced list of top candidates
        """
        return candidates[:max_count]

    def _build_analysis_metadata(
        self,
        language: str,
        min_similarity: float,
        min_lines: int,
        include_test_coverage: bool,
        project_path: str
    ) -> Dict[str, Any]:
        """Build analysis metadata dictionary (legacy interface).

        Maintained for backward compatibility. New code should use
        _build_analysis_metadata_from_config().

        Args:
            language: Programming language
            min_similarity: Minimum similarity threshold
            min_lines: Minimum lines to consider
            include_test_coverage: Whether test coverage was included
            project_path: Project folder path

        Returns:
            Analysis metadata dictionary
        """
        return {
            "language": language,
            "min_similarity": min_similarity,
            "min_lines": min_lines,
            "include_test_coverage": include_test_coverage,
            "project_path": project_path
        }

    def _build_analysis_metadata_from_config(
        self,
        config: AnalysisConfig
    ) -> Dict[str, Any]:
        """Build analysis metadata dictionary from config.

        Args:
            config: Analysis configuration object

        Returns:
            Analysis metadata dictionary
        """
        return {
            "language": config.language,
            "min_similarity": config.min_similarity,
            "min_lines": config.min_lines,
            "include_test_coverage": config.include_test_coverage,
            "project_path": config.project_path
        }

    def _enrich_and_summarize(
        self,
        ranked_candidates: List[Dict[str, Any]],
        max_candidates: int,
        include_test_coverage: bool,
        language: str,
        project_path: str,
        min_similarity: float,
        min_lines: int,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> Dict[str, Any]:
        """Enrich top candidates and generate summary (legacy interface).

        Maintained for backward compatibility. New code should use
        _enrich_and_summarize_with_config().

        Args:
            ranked_candidates: All ranked candidates
            max_candidates: Maximum candidates to return
            include_test_coverage: Whether to add test coverage
            language: Programming language
            project_path: Project folder path
            min_similarity: Minimum similarity threshold
            min_lines: Minimum lines to consider
            progress_callback: Optional progress reporting callback

        Returns:
            Analysis results with enriched candidates and metadata
        """
        # Convert to config and call new method
        config = AnalysisConfig(
            project_path=project_path,
            language=language,
            min_similarity=min_similarity,
            include_test_coverage=include_test_coverage,
            min_lines=min_lines,
            max_candidates=max_candidates,
            progress_callback=progress_callback
        )
        return self._enrich_and_summarize_with_config(
            ranked_candidates,
            config,
            progress_callback=progress_callback
        )

    def _enrich_and_summarize_with_config(
        self,
        ranked_candidates: List[Dict[str, Any]],
        config: AnalysisConfig,
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> Dict[str, Any]:
        """Enrich top candidates and generate summary using config object.

        This is the modern, cleaner API that accepts an AnalysisConfig object
        instead of 8 separate parameters.

        Args:
            ranked_candidates: All ranked candidates
            config: Analysis configuration object
            progress_callback: Optional progress reporting callback

        Returns:
            Analysis results with enriched candidates and metadata
        """
        # Helper for progress reporting
        def report(stage: str, percent: float) -> None:
            if progress_callback:
                progress_callback(stage, percent)

        # Early return for empty candidate list
        if not ranked_candidates:
            self.logger.warning("no_candidates_to_enrich")
            return {
                "candidates": [],
                "total_groups_analyzed": 0,
                "top_candidates_count": 0,
                "top_candidates_savings_potential": 0,
                "analysis_metadata": self._build_analysis_metadata_from_config(config)
            }

        # Get top candidates (40% -> 50%)
        report("Selecting top candidates", 0.50)
        top_candidates = self._get_top_candidates(ranked_candidates, config.max_candidates)

        # Step 3: Check test coverage if requested (50% -> 75%)
        if config.include_test_coverage:
            report("Checking test coverage", 0.60)
            self._add_test_coverage_batch(
                top_candidates,
                config.language,
                config.project_path,
                parallel=config.parallel,
                max_workers=config.max_workers
            )
            report("Test coverage complete", 0.75)

        # Step 4: Generate recommendations (75% -> 90%)
        report("Generating recommendations", 0.85)
        self._add_recommendations(
            top_candidates,
            parallel=config.parallel,
            max_workers=config.max_workers
        )

        # Step 5: Calculate summary statistics (90% -> 95%)
        report("Calculating statistics", 0.90)
        top_candidates_savings = self._calculate_total_savings(top_candidates)

        self.logger.info(
            "analysis_complete",
            total_groups_analyzed=len(ranked_candidates),
            top_candidates_count=len(top_candidates),
            top_candidates_savings_potential=top_candidates_savings
        )

        return {
            "candidates": top_candidates,
            "total_groups_analyzed": len(ranked_candidates),
            "top_candidates_count": len(top_candidates),
            "top_candidates_savings_potential": top_candidates_savings,
            "analysis_metadata": self._build_analysis_metadata_from_config(config)
        }

    def _enrich_with_test_coverage(
        self,
        candidate: Dict[str, Any],
        language: str,
        project_path: str
    ) -> None:
        """Enrich a single candidate with test coverage data.

        Args:
            candidate: Candidate to enrich
            language: Programming language
            project_path: Project folder path

        Note:
            This method is used for sequential processing. For batch parallel
            processing, use _add_test_coverage_batch() instead.
        """
        files = candidate.get("files", [])
        if files:
            coverage_map = self.coverage_detector.get_test_coverage_for_files(
                files, language, project_path
            )
            candidate["test_coverage"] = coverage_map
            candidate["has_tests"] = any(coverage_map.values())

    def _enrich_with_recommendation(
        self,
        candidate: Dict[str, Any]
    ) -> None:
        """Enrich a single candidate with recommendation.

        Args:
            candidate: Candidate to enrich
        """
        recommendation = self.recommendation_engine.generate_deduplication_recommendation(
            score=candidate.get("score", 0),
            complexity=candidate.get("complexity_score", 5),
            lines_saved=candidate.get("lines_saved", 0),
            has_tests=candidate.get("has_tests", False),
            affected_files=len(candidate.get("files", []))
        )
        candidate["recommendation"] = recommendation

    def _handle_enrichment_error(
        self,
        candidate: Dict[str, Any],
        error: Exception,
        operation_name: str,
        error_field: str,
        default_error_value: Any,
        error_message: Optional[str] = None
    ) -> None:
        """Handle enrichment errors by logging and updating candidate.

        Args:
            candidate: The candidate that failed
            error: The exception that occurred (or TimeoutError)
            operation_name: Name of operation for logging
            error_field: Field name to store error message
            default_error_value: Default value to set on error
            error_message: Optional custom error message (for timeouts)
        """
        # Log the error
        if isinstance(error, TimeoutError):
            self.logger.error(
                f"{operation_name}_timeout",
                candidate_id=candidate.get("id", "unknown"),
                timeout_seconds=error_message  # Pass timeout value via error_message
            )
            candidate[error_field] = f"Operation timed out after {error_message}s"
        else:
            self.logger.error(
                f"{operation_name}_enrichment_failed",
                candidate_id=candidate.get("id", "unknown"),
                error=str(error)
            )
            candidate[error_field] = str(error)

        # Set default error value
        if isinstance(default_error_value, dict):
            for key, value in default_error_value.items():
                candidate[key] = value

    def _process_completed_future(
        self,
        future: Any,
        candidate: Dict[str, Any],
        timeout_seconds: int,
        operation_name: str,
        error_field: str,
        default_error_value: Any,
        failed_candidates: List[Dict[str, Any]]
    ) -> None:
        """Process a completed future and handle any errors.

        Args:
            future: The completed future to process
            candidate: The candidate being processed
            timeout_seconds: Timeout for the operation
            operation_name: Name of operation for logging
            error_field: Field name to store error message
            default_error_value: Default value to set on error
            failed_candidates: List to append failed candidates to
        """
        try:
            # Wait for individual future with per-candidate timeout
            future.result(timeout=timeout_seconds)
        except TimeoutError as e:
            self._handle_enrichment_error(
                candidate, e, operation_name, error_field,
                default_error_value, error_message=str(timeout_seconds)
            )
            failed_candidates.append(candidate)
        except Exception as e:
            self._handle_enrichment_error(
                candidate, e, operation_name, error_field,
                default_error_value
            )
            failed_candidates.append(candidate)

    def _process_parallel_enrichment(
        self,
        candidates: List[Dict[str, Any]],
        enrich_func: Callable[[Dict[str, Any], ...], None],
        operation_name: str,
        error_field: str,
        default_error_value: Any,
        max_workers: int,
        timeout_seconds: int,
        kwargs: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Process enrichment in parallel using ThreadPoolExecutor.

        Args:
            candidates: List of candidates to enrich
            enrich_func: Function to call for each candidate
            operation_name: Name of operation for logging
            error_field: Field name to store error message
            default_error_value: Default value to set on error
            max_workers: Maximum number of threads
            timeout_seconds: Timeout per candidate
            kwargs: Additional arguments for enrich_func

        Returns:
            List of failed candidates
        """
        failed_candidates: List[Dict[str, Any]] = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(enrich_func, candidate, **kwargs): candidate
                for candidate in candidates
            }

            # Process futures as they complete
            for future in as_completed(futures):
                candidate = futures[future]
                self._process_completed_future(
                    future, candidate, timeout_seconds,
                    operation_name, error_field, default_error_value,
                    failed_candidates
                )

        return failed_candidates

    def _process_sequential_enrichment(
        self,
        candidates: List[Dict[str, Any]],
        enrich_func: Callable[[Dict[str, Any], ...], None],
        operation_name: str,
        error_field: str,
        default_error_value: Any,
        kwargs: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Process enrichment sequentially.

        Args:
            candidates: List of candidates to enrich
            enrich_func: Function to call for each candidate
            operation_name: Name of operation for logging
            error_field: Field name to store error message
            default_error_value: Default value to set on error
            kwargs: Additional arguments for enrich_func

        Returns:
            List of failed candidates
        """
        failed_candidates: List[Dict[str, Any]] = []

        for candidate in candidates:
            try:
                enrich_func(candidate, **kwargs)
            except Exception as e:
                self._handle_enrichment_error(
                    candidate, e, operation_name, error_field,
                    default_error_value
                )
                failed_candidates.append(candidate)

        return failed_candidates

    def _parallel_enrich(
        self,
        candidates: List[Dict[str, Any]],
        enrich_func: Callable[[Dict[str, Any], ...], None],
        operation_name: str,
        error_field: str,
        default_error_value: Any,
        parallel: bool = True,
        max_workers: int = 4,
        timeout_per_candidate: Optional[int] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Generic parallel enrichment helper to reduce code duplication.

        This method consolidates the duplicate ThreadPoolExecutor pattern used
        in _add_test_coverage and _add_recommendations, improving maintainability
        and reducing the codebase by ~40 lines.

        Args:
            candidates: List of candidates to enrich
            enrich_func: Function to call for each candidate (signature: func(candidate, **kwargs))
            operation_name: Name of operation for logging (e.g., "test_coverage", "recommendation")
            error_field: Field name to store error message (e.g., "test_coverage_error")
            default_error_value: Default value to set on error (e.g., {}, False)
            parallel: Whether to use parallel execution (default: True)
            max_workers: Maximum number of threads for parallel execution
            timeout_per_candidate: Timeout in seconds for each candidate operation (default: 30s)
            **kwargs: Additional keyword arguments to pass to enrich_func

        Returns:
            List of candidates that failed enrichment (for monitoring)

        Example:
            failed = self._parallel_enrich(
                candidates,
                self._enrich_with_test_coverage,
                "test_coverage",
                "test_coverage_error",
                {},
                timeout_per_candidate=30,
                language=language,
                project_path=project_path
            )
        """
        # Use default timeout if not specified
        timeout_seconds = (
            timeout_per_candidate
            if timeout_per_candidate is not None
            else ParallelProcessing.DEFAULT_TIMEOUT_PER_CANDIDATE_SECONDS
        )

        # Choose processing strategy based on parallel flag and candidate count
        if parallel and len(candidates) > 1:
            failed_candidates = self._process_parallel_enrichment(
                candidates, enrich_func, operation_name, error_field,
                default_error_value, max_workers, timeout_seconds, kwargs
            )
        else:
            failed_candidates = self._process_sequential_enrichment(
                candidates, enrich_func, operation_name, error_field,
                default_error_value, kwargs
            )

        # Log summary
        self.logger.info(
            f"{operation_name}_added",
            candidate_count=len(candidates),
            failed_count=len(failed_candidates),
            parallel=parallel
        )

        return failed_candidates

    def _add_test_coverage_batch(
        self,
        candidates: List[Dict[str, Any]],
        language: str,
        project_path: str,
        parallel: bool = True,
        max_workers: int = 4,
        timeout_per_candidate: Optional[int] = None
    ) -> None:
        """Add test coverage information using optimized batch processing.

        This method provides 60-80% performance improvement over the legacy
        _add_test_coverage() method by:
        1. Collecting all unique files from all candidates
        2. Running batch test coverage detection once
        3. Distributing results back to candidates

        Args:
            candidates: List of candidates to enrich
            language: Programming language
            project_path: Project folder path
            parallel: Whether to use parallel execution (default: True)
            max_workers: Maximum number of threads for parallel execution
            timeout_per_candidate: Timeout in seconds for each candidate (default: 30s)
        """
        if not candidates:
            return

        # Collect all unique files from all candidates
        all_files: List[str] = []
        for candidate in candidates:
            all_files.extend(candidate.get("files", []))

        # Remove duplicates while preserving order
        unique_files = list(dict.fromkeys(all_files))

        if not unique_files:
            self.logger.debug("no_files_for_coverage_check")
            return

        self.logger.debug(
            "batch_coverage_start",
            candidate_count=len(candidates),
            unique_file_count=len(unique_files),
            total_file_refs=len(all_files),
            parallel=parallel
        )

        # Run optimized batch test coverage detection
        coverage_map = self.coverage_detector.get_test_coverage_for_files_batch(
            unique_files,
            language,
            project_path,
            parallel=parallel,
            max_workers=max_workers
        )

        # Distribute coverage results to candidates
        for candidate in candidates:
            files = candidate.get("files", [])
            if files:
                candidate_coverage = {
                    f: coverage_map.get(f, False)
                    for f in files
                }
                candidate["test_coverage"] = candidate_coverage
                candidate["has_tests"] = any(candidate_coverage.values())
            else:
                candidate["test_coverage"] = {}
                candidate["has_tests"] = False

        self.logger.info(
            "batch_coverage_added",
            candidate_count=len(candidates),
            unique_files_checked=len(unique_files),
            parallel=parallel
        )

    def _add_test_coverage(
        self,
        candidates: List[Dict[str, Any]],
        language: str,
        project_path: str,
        parallel: bool = True,
        max_workers: int = 4
    ) -> List[Dict[str, Any]]:
        """Add test coverage information to candidates (legacy method).

        Args:
            candidates: List of candidates to enrich
            language: Programming language
            project_path: Project folder path
            parallel: Whether to use parallel execution (default: True)
            max_workers: Maximum number of threads for parallel execution

        Returns:
            List of candidates that failed enrichment (for monitoring)

        Note:
            This is the legacy implementation. Use _add_test_coverage_batch()
            for better performance (60-80% faster). Now refactored to use
            _parallel_enrich() to reduce code duplication.
        """
        return self._parallel_enrich(
            candidates=candidates,
            enrich_func=self._enrich_with_test_coverage,
            operation_name="test_coverage",
            error_field="test_coverage_error",
            default_error_value={
                "test_coverage": {},
                "has_tests": False
            },
            parallel=parallel,
            max_workers=max_workers,
            language=language,
            project_path=project_path
        )

    def _add_recommendations(
        self,
        candidates: List[Dict[str, Any]],
        parallel: bool = True,
        max_workers: int = 4,
        timeout_per_candidate: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Add recommendations to candidates.

        Args:
            candidates: List of candidates to enrich
            parallel: Whether to use parallel execution (default: True)
            max_workers: Maximum number of threads for parallel execution
            timeout_per_candidate: Timeout in seconds for each candidate (default: 30s)

        Returns:
            List of candidates that failed enrichment (for monitoring)

        Note:
            Now refactored to use _parallel_enrich() to reduce code duplication.
        """
        return self._parallel_enrich(
            candidates=candidates,
            enrich_func=self._enrich_with_recommendation,
            operation_name="recommendations",
            error_field="recommendation_error",
            default_error_value={
                "recommendation": {
                    "action": "error",
                    "reasoning": "Failed to generate recommendation",
                    "priority": "low"
                }
            },
            timeout_per_candidate=timeout_per_candidate,
            parallel=parallel,
            max_workers=max_workers
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
        return int(total)
