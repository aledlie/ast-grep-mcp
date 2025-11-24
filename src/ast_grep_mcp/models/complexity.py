"""Data models for code complexity analysis."""
from dataclasses import dataclass, field
from typing import List


@dataclass
class ComplexityMetrics:
    """Immutable metrics container for a single function."""
    cyclomatic: int
    cognitive: int
    nesting_depth: int
    lines: int
    parameter_count: int = 0


@dataclass
class FunctionComplexity:
    """Complete analysis result for one function."""
    file_path: str
    function_name: str
    start_line: int
    end_line: int
    metrics: ComplexityMetrics
    language: str
    exceeds: List[str] = field(default_factory=list)


@dataclass
class ComplexityThresholds:
    """Configurable thresholds with sensible defaults."""
    cyclomatic: int = 10
    cognitive: int = 15
    nesting_depth: int = 4
    lines: int = 50
