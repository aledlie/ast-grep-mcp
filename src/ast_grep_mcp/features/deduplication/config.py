"""Configuration dataclasses for deduplication analysis.

This module provides strongly-typed configuration objects that replace
excessive parameter passing throughout the deduplication workflow.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Callable


@dataclass
class AnalysisConfig:
    """Configuration for deduplication candidate analysis.

    This config object consolidates all analysis parameters into a single
    strongly-typed structure, replacing methods with 6-8 parameters.

    Examples:
        >>> # Simple usage
        >>> config = AnalysisConfig(
        ...     project_path="/path/to/project",
        ...     language="python"
        ... )

        >>> # With custom thresholds
        >>> config = AnalysisConfig(
        ...     project_path="/path/to/project",
        ...     language="python",
        ...     min_similarity=0.9,
        ...     max_candidates=50,
        ...     include_test_coverage=False
        ... )

        >>> # With progress tracking
        >>> def show_progress(stage, percent):
        ...     print(f"[{percent*100:.0f}%] {stage}")
        >>>
        >>> config = AnalysisConfig(
        ...     project_path="/path/to/project",
        ...     language="python",
        ...     progress_callback=show_progress
        ... )

    Attributes:
        project_path: Project folder path to analyze
        language: Programming language (python, javascript, typescript, etc.)
        min_similarity: Minimum similarity threshold (0.0-1.0). Default: 0.8
        include_test_coverage: Whether to check test coverage. Default: True
        min_lines: Minimum lines to consider for duplication. Default: 5
        max_candidates: Maximum candidates to return. Default: 100
        exclude_patterns: Path patterns to exclude from analysis. Default: None
        parallel: Enable parallel execution for enrichment. Default: True
        max_workers: Maximum worker threads for parallel execution. Default: 4
        progress_callback: Optional callback for progress reporting.
            Signature: (stage_name: str, progress_percent: float) -> None
    """

    # Required fields
    project_path: str
    language: str

    # Analysis thresholds with defaults
    min_similarity: float = 0.8
    include_test_coverage: bool = True
    min_lines: int = 5
    max_candidates: int = 100

    # Optional fields
    exclude_patterns: Optional[List[str]] = None

    # Parallel execution settings
    parallel: bool = True
    max_workers: int = 4

    # Progress tracking
    progress_callback: Optional[Callable[[str, float], None]] = None

    def __post_init__(self) -> None:
        """Validate configuration after initialization.

        Raises:
            ValueError: If any configuration value is invalid
        """
        # Normalize exclude_patterns to empty list if None
        if self.exclude_patterns is None:
            self.exclude_patterns = []

        # Validate ranges (detailed validation happens in orchestrator)
        if not 0.0 <= self.min_similarity <= 1.0:
            raise ValueError(
                f"min_similarity must be between 0.0 and 1.0, got {self.min_similarity}"
            )

        if self.min_lines < 1:
            raise ValueError(
                f"min_lines must be positive, got {self.min_lines}"
            )

        if self.max_candidates < 1:
            raise ValueError(
                f"max_candidates must be positive, got {self.max_candidates}"
            )

        if self.max_workers < 1:
            raise ValueError(
                f"max_workers must be positive, got {self.max_workers}"
            )

    def to_dict(self) -> dict:
        """Convert config to dictionary for logging/serialization.

        Returns:
            Dictionary representation (excludes progress_callback)
        """
        return {
            "project_path": self.project_path,
            "language": self.language,
            "min_similarity": self.min_similarity,
            "include_test_coverage": self.include_test_coverage,
            "min_lines": self.min_lines,
            "max_candidates": self.max_candidates,
            "exclude_patterns": self.exclude_patterns,
            "parallel": self.parallel,
            "max_workers": self.max_workers,
            "has_progress_callback": self.progress_callback is not None
        }
