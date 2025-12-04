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
from .analyzer import (
    PatternAnalyzer,
    _detect_nested_function_call,
    classify_variations,
    detect_conditional_variations,
    identify_varying_identifiers,
)
from .applicator import DeduplicationApplicator
from .benchmark import DeduplicationBenchmark, benchmark_deduplication

# Supporting modules
from .coverage import (
    CoverageDetector,
    _check_test_file_references_source,
    _get_potential_test_paths,
    check_test_file_references_source,
    find_test_file_patterns,
    get_potential_test_paths,
    get_test_coverage_for_files,
    has_test_coverage,
)
from .detector import DuplicationDetector
from .diff import (
    build_diff_tree,
    build_nested_diff_tree,
    diff_preview_to_dict,
    format_alignment_diff,
    generate_diff_from_file_paths,
    generate_file_diff,
    generate_multi_file_diff,
)
from .generator import (
    CodeGenerator,
    _infer_from_identifier_name,
    _infer_single_value_type,
    generate_parameter_name,
    infer_parameter_type,
)
from .impact import (
    ImpactAnalyzer,
    _estimate_lines_changed,
    analyze_deduplication_impact,
    estimate_lines_changed,
)
from .ranker import DuplicationRanker
from .recommendations import RecommendationEngine, generate_deduplication_recommendation, generate_refactoring_suggestions
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
    # Module-level functions - diff utilities
    "build_diff_tree",
    "build_nested_diff_tree",
    "diff_preview_to_dict",
    "format_alignment_diff",
    "generate_diff_from_file_paths",
    "generate_file_diff",
    "generate_multi_file_diff",
    # Module-level functions - variation analysis
    "detect_conditional_variations",
    "_detect_nested_function_call",
    "classify_variations",
    "identify_varying_identifiers",
    # Module-level functions - type inference
    "_infer_from_identifier_name",
    "_infer_single_value_type",
    # Module-level functions - parameter generation
    "generate_parameter_name",
    "infer_parameter_type",
    # Module-level functions - impact analysis
    "analyze_deduplication_impact",
    "estimate_lines_changed",
    "_estimate_lines_changed",
    # Module-level functions - coverage
    "find_test_file_patterns",
    "has_test_coverage",
    "get_test_coverage_for_files",
    "check_test_file_references_source",
    "_check_test_file_references_source",
    "get_potential_test_paths",
    "_get_potential_test_paths",
    "generate_deduplication_recommendation",
    "generate_refactoring_suggestions",
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
