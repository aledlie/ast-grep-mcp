"""
Deduplication feature module.

This module provides comprehensive code deduplication detection and refactoring
capabilities for the ast-grep MCP server.

Version History:
- v1.0.0: Initial release with MinHash similarity
- v1.1.0: Added hybrid two-stage similarity pipeline (TACC-inspired)
"""

# Core detection and analysis
from ...models.deduplication import VariationCategory, VariationSeverity
from .analyzer import PatternAnalyzer
from .applicator import DeduplicationApplicator
from .benchmark import DeduplicationBenchmark, benchmark_deduplication

# Supporting modules
from .coverage import CoverageDetector, find_test_file_patterns, get_test_coverage_for_files, has_test_coverage
from .detector import DuplicationDetector
from .generator import CodeGenerator
from .impact import ImpactAnalyzer, analyze_deduplication_impact
from .ranker import DuplicationRanker
from .recommendations import RecommendationEngine, generate_deduplication_recommendation
from .reporting import (
    DuplicationReporter,
    EnhancedDuplicationCandidate,
    create_enhanced_duplication_response,
    format_diff_with_colors,
    generate_before_after_example,
    visualize_complexity,
)

# Similarity calculation
from .similarity import (
    HybridSimilarity,
    HybridSimilarityConfig,
    HybridSimilarityResult,
    MinHashSimilarity,
    SimilarityConfig,
    SimilarityResult,
)

# MCP tool wrappers
from .tools import analyze_deduplication_candidates_tool, apply_deduplication_tool, benchmark_deduplication_tool, find_duplication_tool

__all__ = [
    # Core classes
    "DuplicationDetector",
    "PatternAnalyzer",
    "CodeGenerator",
    "DuplicationRanker",
    # Similarity classes (v1.1.0)
    "HybridSimilarity",
    "HybridSimilarityConfig",
    "HybridSimilarityResult",
    "MinHashSimilarity",
    "SimilarityConfig",
    "SimilarityResult",
    # Supporting classes
    "CoverageDetector",
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
__version__ = "1.1.0"
