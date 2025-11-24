"""Data models for code complexity analysis."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class ComplexityMetrics:
    """Immutable metrics container for a single function."""
    cyclomatic: int
    cognitive: int
    nesting_depth: int
    line_count: int


@dataclass
class FunctionComplexity:
    """Complete analysis result for one function."""
    name: str
    file_path: str
    line_number: int
    metrics: ComplexityMetrics
    exceeds_thresholds: bool


@dataclass
class ComplexityThresholds:
    """Configurable thresholds with sensible defaults."""
    cyclomatic: int = 10
    cognitive: int = 15
    nesting: int = 4
    length: int = 50