"""
Deduplication feature module.

This module provides comprehensive code deduplication detection and refactoring
capabilities for the ast-grep MCP server.
"""

# Core detection and analysis
from .detector import DuplicationDetector
from .analyzer import PatternAnalyzer, VariationCategory, VariationSeverity
from .generator import CodeGenerator
from .ranker import DuplicationRanker

# Supporting modules
from .coverage import TestCoverageDetector, find_test_file_patterns, has_test_coverage, get_test_coverage_for_files
from .impact import ImpactAnalyzer, analyze_deduplication_impact
from .recommendations import RecommendationEngine, generate_deduplication_recommendation
from .applicator import DeduplicationApplicator
from .reporting import (
    DuplicationReporter,
    EnhancedDuplicationCandidate,
    format_diff_with_colors,
    generate_before_after_example,
    visualize_complexity,
    create_enhanced_duplication_response
)
from .benchmark import DeduplicationBenchmark, benchmark_deduplication

# MCP tool wrappers
from .tools import (
    find_duplication_tool,
    analyze_deduplication_candidates_tool,
    apply_deduplication_tool,
    benchmark_deduplication_tool
)

__all__ = [
    # Core classes
    "DuplicationDetector",
    "PatternAnalyzer",
    "CodeGenerator",
    "DuplicationRanker",

    # Supporting classes
    "TestCoverageDetector",
    "ImpactAnalyzer",
    "RecommendationEngine",
    "DeduplicationApplicator",
    "DuplicationReporter",
    "DeduplicationBenchmark",
    "EnhancedDuplicationCandidate",

    # Constants
    "VariationCategory",
    "VariationSeverity",

    # Module-level functions
    "find_test_file_patterns",
    "has_test_coverage",
    "get_test_coverage_for_files",
    "analyze_deduplication_impact",
    "generate_deduplication_recommendation",
    "format_diff_with_colors",
    "generate_before_after_example",
    "visualize_complexity",
    "create_enhanced_duplication_response",
    "benchmark_deduplication",

    # MCP tool wrappers
    "find_duplication_tool",
    "analyze_deduplication_candidates_tool",
    "apply_deduplication_tool",
    "benchmark_deduplication_tool",
]

# Version info
__version__ = "1.0.0"