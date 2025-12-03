"""Data models for code complexity analysis."""

from dataclasses import dataclass, field
from typing import List

from ast_grep_mcp.constants import ComplexityDefaults


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

    cyclomatic: int = ComplexityDefaults.CYCLOMATIC_THRESHOLD
    cognitive: int = ComplexityDefaults.COGNITIVE_THRESHOLD
    nesting_depth: int = ComplexityDefaults.NESTING_THRESHOLD
    lines: int = ComplexityDefaults.LENGTH_THRESHOLD
