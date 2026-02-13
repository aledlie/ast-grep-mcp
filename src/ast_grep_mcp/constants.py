"""Shared constants across the ast-grep-mcp codebase.

This module centralizes magic numbers and configuration values
to improve maintainability and reduce code duplication.
"""

import os


class ComplexityDefaults:
    """Default thresholds for complexity analysis."""

    CYCLOMATIC_THRESHOLD = 10
    COGNITIVE_THRESHOLD = 15
    NESTING_THRESHOLD = 4
    LENGTH_THRESHOLD = 50


class ParallelProcessing:
    """Parallel processing configuration."""

    DEFAULT_WORKERS = 4
    MAX_WORKERS = 16

    # Timeout configuration for parallel operations
    DEFAULT_TIMEOUT_PER_CANDIDATE_SECONDS = 30  # 30 seconds per candidate
    MAX_TIMEOUT_SECONDS = 300  # 5 minutes max total timeout

    @staticmethod
    def get_optimal_workers(max_threads: int = 0) -> int:
        """Calculate optimal worker count based on CPU cores.

        Args:
            max_threads: Maximum threads to use (0 = auto-detect)

        Returns:
            Optimal number of worker threads (1 to MAX_WORKERS)
        """
        if max_threads > 0:
            return min(max_threads, ParallelProcessing.MAX_WORKERS)

        cpu_count = os.cpu_count() or 4
        # Reserve 1 core for system, cap at MAX_WORKERS
        return max(1, min(cpu_count - 1, ParallelProcessing.MAX_WORKERS))


class CacheDefaults:
    """Cache configuration defaults."""

    TTL_SECONDS = 3600  # 1 hour
    MAX_SIZE_MB = 100
    CLEANUP_INTERVAL_SECONDS = 300  # 5 minutes
    DEFAULT_CACHE_SIZE = 100  # Number of cached items
    CACHE_KEY_LENGTH = 16  # Length of truncated SHA256 hash for cache keys


class FilePatterns:
    """Common file patterns for analysis."""

    DEFAULT_EXCLUDE = [
        "**/node_modules/**",
        "**/__pycache__/**",
        "**/venv/**",
        "**/.venv/**",
        "**/site-packages/**",
        "**/dist/**",
        "**/build/**",
        "**/.git/**",
        "**/coverage/**",
    ]

    TEST_EXCLUDE = [
        "**/test*/**",
        "**/*test*",
        "**/tests/**",
        "**/*_test.py",
        "**/test_*.py",
    ]


class StreamDefaults:
    """Defaults for streaming operations."""

    DEFAULT_TIMEOUT_MS = 120000  # 2 minutes
    MAX_TIMEOUT_MS = 600000  # 10 minutes
    PROGRESS_INTERVAL = 100  # Log progress every N matches
    SIGTERM_RETURN_CODE = -15  # Return code for SIGTERM signal


class ValidationDefaults:
    """Defaults for validation operations."""

    MAX_FILE_SIZE_MB = 10  # Skip files larger than this
    SYNTAX_CHECK_TIMEOUT_SECONDS = 5


class FileConstants:
    """Constants for file operations."""

    BYTES_PER_KB = 1024
    BYTES_PER_MB = 1024 * 1024
    BYTES_PER_GB = 1024 * 1024 * 1024
    LINE_PREVIEW_LENGTH = 100  # Maximum characters to show in line preview


class DeduplicationDefaults:
    """Defaults for deduplication analysis."""

    MIN_SIMILARITY = 0.8  # Minimum similarity threshold (0-1)
    MIN_LINES = 5  # Minimum lines to consider for duplication

    # Scoring weights (must sum to 1.0)
    SAVINGS_WEIGHT = 0.40
    COMPLEXITY_WEIGHT = 0.20
    RISK_WEIGHT = 0.25
    EFFORT_WEIGHT = 0.15

    # Regression thresholds for performance benchmarks
    REGRESSION_PATTERN_ANALYSIS = 0.15  # 15% slowdown allowed
    REGRESSION_CODE_GENERATION = 0.10  # 10% slowdown allowed
    REGRESSION_FULL_WORKFLOW = 0.20  # 20% slowdown allowed
    REGRESSION_SCORING = 0.05  # 5% slowdown allowed
    REGRESSION_TEST_COVERAGE = 0.15  # 15% slowdown allowed


class HybridSimilarityDefaults:
    """Defaults for hybrid two-stage similarity pipeline.

    Scientific basis: TACC (Token and AST-based Code Clone detector)
    from ICSE 2023 demonstrates that combining MinHash filtering with
    AST verification yields optimal precision/recall balance.
    """

    # Stage 1: MinHash filter threshold for early exit
    # Code pairs below this threshold skip Stage 2 (AST verification)
    MINHASH_EARLY_EXIT_THRESHOLD = 0.5

    # Stage 2 weights for combining MinHash and AST similarity
    # Must sum to 1.0. AST gets higher weight due to structural precision.
    MINHASH_WEIGHT = 0.4
    AST_WEIGHT = 0.6

    # Minimum token count to use hybrid approach
    # Very short code snippets may not benefit from AST analysis
    MIN_TOKENS_FOR_AST = 10

    # Maximum code length (lines) for AST analysis
    # Very long code may be too expensive for detailed AST comparison
    MAX_LINES_FOR_FULL_AST = 500

    # AST tree edit distance normalization factor
    # Used to convert raw edit distance to 0-1 similarity score
    TREE_EDIT_DISTANCE_NORMALIZATION = 100


class SemanticSimilarityDefaults:
    """Defaults for CodeBERT-based semantic similarity (Phase 5).

    Scientific basis: GraphCodeBERT (2024) produces 768-dimensional
    embeddings capturing semantic meaning for Type-4 clone detection.

    Note: Semantic similarity is OPTIONAL and requires:
    - transformers library
    - torch (PyTorch)
    - GPU recommended for performance

    Install with: pip install ast-grep-mcp[semantic]
    """

    # Whether semantic similarity is enabled by default
    # Set to False to require explicit opt-in
    ENABLE_SEMANTIC = False

    # Weight for semantic similarity in three-stage hybrid score
    # When enabled, weights are rebalanced: MinHash (0.2), AST (0.5), Semantic (0.3)
    SEMANTIC_WEIGHT = 0.3

    # Rebalanced weights when semantic is enabled (must sum to 1.0)
    MINHASH_WEIGHT_WITH_SEMANTIC = 0.2
    AST_WEIGHT_WITH_SEMANTIC = 0.5

    # Minimum similarity from Stage 2 (AST) to proceed to Stage 3 (Semantic)
    # This provides a second early-exit point to avoid expensive model inference
    SEMANTIC_STAGE_THRESHOLD = 0.6

    # Default model for CodeBERT embeddings
    MODEL_NAME = "microsoft/codebert-base"

    # Maximum token length for CodeBERT input
    MAX_TOKEN_LENGTH = 512

    # Device selection: 'auto', 'cpu', 'cuda', or 'mps'
    DEFAULT_DEVICE = "auto"

    # Whether to cache embeddings for repeated comparisons
    CACHE_EMBEDDINGS = True

    # Whether to L2-normalize embeddings (recommended for cosine similarity)
    NORMALIZE_EMBEDDINGS = True


class SecurityScanDefaults:
    """Defaults for security scanning."""

    MAX_ISSUES = 100  # Maximum issues to return
    DEFAULT_SEVERITY_THRESHOLD = "low"  # Minimum severity to report

    # Confidence thresholds
    HIGH_CONFIDENCE = 0.9
    MEDIUM_CONFIDENCE = 0.7
    LOW_CONFIDENCE = 0.5


class CodeQualityDefaults:
    """Defaults for code quality analysis."""

    # Code smell thresholds
    LONG_FUNCTION_LINES = 50
    PARAMETER_COUNT = 5
    NESTING_DEPTH = 4
    CLASS_LINES = 300
    CLASS_METHODS = 20

    # Magic numbers to ignore
    ALLOWED_MAGIC_NUMBERS = {0, 1, -1, 2, 10, 100, 1000}


class LoggingDefaults:
    """Logging configuration defaults."""

    DEFAULT_LEVEL = "INFO"
    MAX_LOG_SIZE_MB = 10
    BACKUP_COUNT = 5  # Number of log files to keep
    MAX_BREADCRUMBS = 50  # Maximum Sentry breadcrumbs to keep


# Language-specific extensions mapping
LANGUAGE_EXTENSIONS = {
    "python": [".py"],
    "typescript": [".ts", ".tsx"],
    "javascript": [".js", ".jsx"],
    "java": [".java"],
    "kotlin": [".kt", ".kts"],
    "go": [".go"],
    "rust": [".rs"],
    "ruby": [".rb"],
    "php": [".php"],
    "c": [".c", ".h"],
    "cpp": [".cpp", ".cc", ".cxx", ".hpp", ".hxx"],
    "csharp": [".cs"],
    "swift": [".swift"],
}

# Schema.org constants
SCHEMA_ORG_BASE_URL = "https://schema.org"
SCHEMA_ORG_CONTEXT = "https://schema.org"

class FormattingDefaults:
    """Defaults for code formatting."""

    ROUNDING_PRECISION = 3  # Decimal places for execution times, hit rates
    DEFAULT_DIFF_CONTEXT_LINES = 3  # Context lines in unified diffs
    BLACK_LINE_LENGTH = 88  # Black formatter default
    PRETTIER_LINE_LENGTH = 80  # Prettier formatter default
    SEPARATOR_LENGTH = 70  # Default CLI separator line length


class DisplayDefaults:
    """Constants for display and UI elements."""

    VISUALIZATION_BAR_LENGTH = 10  # Length of ASCII score bars
    LOW_SCORE_THRESHOLD = 3  # Score <= this is "low"
    MEDIUM_SCORE_THRESHOLD = 6  # Score <= this is "medium"
    CONTENT_PREVIEW_LENGTH = 50  # Characters in content previews
    ERROR_OUTPUT_PREVIEW_LENGTH = 200  # Characters in error output previews
    AST_TRUNCATION_LENGTH = 500  # Characters for AST structure previews
    AST_PREVIEW_MAX_LINES = 15  # Lines in AST preview output
    MAX_CHILD_KINDS = 10  # Max child kinds to return in analysis
    MAX_LITERALS = 5  # Max literals to return in analysis
    MAX_IDENTIFIERS = 10  # Max identifiers to return in analysis
    MAX_PATTERN_REPLACEMENTS = 3  # Max literal replacements in patterns
    MAX_PATTERN_IDENTIFIERS = 5  # Max identifier replacements in patterns
    SHORT_IDENTIFIER_THRESHOLD = 4  # Length threshold for short identifiers


class PerformanceDefaults:
    """Defaults for performance monitoring."""

    SLOW_EXECUTION_THRESHOLD_MS = 5000  # 5 seconds
    DEFAULT_SLOW_THRESHOLD_MS = 1000  # 1 second default for track_slow_operations
    DATABASE_TIMEOUT_SECONDS = 30.0  # SQLite/HTTP connection timeout


class CodeAnalysisDefaults:
    """Defaults for code structure analysis."""

    SIMPLE_CODE_DEPTH_THRESHOLD = 3
    SIMPLE_CODE_LINES_THRESHOLD = 3
    MEDIUM_CODE_DEPTH_THRESHOLD = 6
    MEDIUM_CODE_LINES_THRESHOLD = 10
    DEFAULT_COMPLEXITY_SCORE = 5  # Default complexity when unknown


class ComplexityLevelDefaults:
    """Thresholds for classifying complexity into low/medium/high."""

    LOW_THRESHOLD = 5  # Score below this is "low"
    MEDIUM_THRESHOLD = 10  # Score below this is "medium"


class SmellSeverityDefaults:
    """Thresholds for code smell severity classification."""

    HIGH_RATIO_THRESHOLD = 2.0  # metric/threshold ratio above this is "high"
    MEDIUM_RATIO_THRESHOLD = 1.5  # metric/threshold ratio above this is "medium"


class UsageTrackingDefaults:
    """Defaults for usage tracking and alerting."""

    DAILY_CALLS_WARNING = 1000
    DAILY_CALLS_CRITICAL = 5000
    DAILY_COST_WARNING = 1.0
    DAILY_COST_CRITICAL = 5.0
    HOURLY_FAILURES_WARNING = 10
    HOURLY_FAILURES_CRITICAL = 50
    FAILURE_RATE_WARNING = 0.1  # 10%
    FAILURE_RATE_CRITICAL = 0.25  # 25%
    AVG_RESPONSE_TIME_WARNING_MS = 5000
    AVG_RESPONSE_TIME_CRITICAL_MS = 30000
    DEFAULT_PAGINATION_LIMIT = 100
    DEFAULT_STATS_LOOKBACK_DAYS = 7


class ReportingDefaults:
    """Defaults for deduplication reporting."""

    SIGNIFICANT_LINES_SAVED_THRESHOLD = 50
    MANY_DUPLICATES_THRESHOLD = 5


class SEODefaults:
    """Defaults for SEO scoring in schema enhancement."""

    BASE_SCORE = 100.0
    BONUS_INCREMENT = 5.0
    FALLBACK_AVG_ENTITY_SCORE = 50.0
    DEFAULT_PRIORITY_ORDER = 4


class SentryDefaults:
    """Defaults for Sentry monitoring configuration."""

    PRODUCTION_TRACES_SAMPLE_RATE = 0.1
    PRODUCTION_PROFILES_SAMPLE_RATE = 0.1


class DocstringDefaults:
    """Defaults for docstring generation."""

    BASIC_INFERENCE_CONFIDENCE = 0.8


# HTTP constants
DEFAULT_USER_AGENT = "ast-grep-mcp/1.0"
REQUEST_TIMEOUT_SECONDS = 30
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 1
